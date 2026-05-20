#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include <neorv32.h>

#include "../ascon_accel/ascon_accel.h"
#include "../ascon_accel/ascon_accel_benchmark.h"
#ifdef ASCON_BENCH_USE_AXIS_MMIO
#include "../ascon_accel/ascon_accel_axis_mmio_transport.h"
#endif
#include "../ascon_ref/ascon_ref_aead128.h"

/* ---------------------------------------------------------------------------
 * NEORV32 + ASCON benchmark firmware
 *
 * This image runs in three identical configurations:
 *   * Verilator co-simulation (open-source NEORV32 + ASCON CFS),
 *   * Tang Nano 9K standalone bring-up over UART, when the integrated SoC
 *     fits, and
 *   * a larger FPGA target (e.g. Xilinx Kintex with the streaming backend).
 *
 * The firmware sweeps a fixed set of payload sizes through both the C
 * reference implementation running on the simulated/real CPU, and the
 * hardware accelerator over its MMIO interface. For each (AD,PT) pair it
 * emits one machine-parsable line of the form
 *
 *   CASE name=<n> ad=<a> pt=<p> sw_enc_cy=<H>:<L> sw_dec_cy=<H>:<L>
 *        hw_enc_cy=<H>:<L> hw_dec_cy=<H>:<L>
 *        enc_ok=<0|1> dec_ok=<0|1> tag_valid=<0|1>
 *        hw_enc_err=0x<x> hw_dec_err=0x<x>
 *
 * Logs can be ingested by tools/parse_neorv32_ascon_uart_log.py to populate
 * the performance-comparison tables of the development report.
 * --------------------------------------------------------------------------- */

#define UART_BAUD              19200u
#define ACCEL_TIMEOUT_CYCLES   10000000u
#define MAX_BENCH_BYTES        32u   /* bounded MMIO backend limit */

/* Build identification banner. The cosim, Tang Nano, and Kintex builds will
 * each set different defines so the log file unambiguously records which
 * platform produced it. */
#ifndef ASCON_BENCH_BUILD_TAG
#define ASCON_BENCH_BUILD_TAG "cosim-neorv32-mmio"
#endif

/* Backend capability tag. The bounded MMIO backend supports payloads up to
 * MAX_BENCH_BYTES. The streaming backend used on Kintex extends this to 1024. */
#ifndef ASCON_BENCH_MAX_BYTES_TAG
#define ASCON_BENCH_MAX_BYTES_TAG 32
#endif

/* ---------------------------------------------------------------------------
 * NEORV32 printf does not support width modifiers (%02x is ignored). Print
 * bytes one nibble at a time via %c. */
static char ph_nib(uint8_t n) {
  return (char)((n < 10u) ? ('0' + n) : ('a' + (n - 10u)));
}
static void print_hex(const char *label, const uint8_t *data, uint32_t len) {
  neorv32_uart0_printf("%s", label);
  for (uint32_t i = 0u; i < len; ++i) {
    neorv32_uart0_printf("%c%c",
        ph_nib((uint8_t)(data[i] >> 4)),
        ph_nib((uint8_t)(data[i] & 0x0fu)));
  }
  neorv32_uart0_printf("\n");
}

static uint64_t rdcycle64(void) {
#ifdef ASCON_BENCH_NO_RDCYCLE
  return 0u;
#elif __riscv_xlen == 64
  uint64_t value;
  __asm__ volatile ("rdcycle %0" : "=r"(value));
  return value;
#else
  uint32_t hi0, lo, hi1;
  do {
    __asm__ volatile ("rdcycleh %0" : "=r"(hi0));
    __asm__ volatile ("rdcycle  %0" : "=r"(lo));
    __asm__ volatile ("rdcycleh %0" : "=r"(hi1));
  } while (hi0 != hi1);
  return ((uint64_t)hi1 << 32) | (uint64_t)lo;
#endif
}

static bool bytes_equal(const uint8_t *a, const uint8_t *b, uint32_t len) {
  uint8_t diff = 0u;
  for (uint32_t i = 0u; i < len; ++i) {
    diff |= (uint8_t)(a[i] ^ b[i]);
  }
  return diff == 0u;
}

/* ---------------------------------------------------------------------------
 * Test vectors. The first MAX_BENCH_BYTES of these arrays are sliced
 * for the various payload sizes in the sweep. */
static const uint8_t key[16] = {
  0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
  0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
};
static const uint8_t nonce[16] = {
  0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
  0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
};
static const uint8_t ad_pool[32] = {
  0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
  0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f,
  0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57,
  0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f,
};
static const uint8_t pt_pool[32] = {
  0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
  0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f,
  0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47,
  0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f,
};

/* Payload sizes for the sweep. Two flavours, selected at compile time by
 * the build's max-bytes tag: the bounded backend cap fits {0..32}, the
 * streaming backend cap fits the full RASD-mandated {64,256,1024}. */
typedef struct {
  const char *name;
  uint32_t    ad_len;
  uint32_t    pt_len;
} bench_case_t;

#if ASCON_BENCH_MAX_BYTES_TAG >= 1024
/* Streaming-backend sweep, used on Kintex (and any other big-FPGA build). */
static const bench_case_t SWEEP[] = {
  { "empty",       0,    0 },
  { "ad_only",    16,    0 },
  { "p64",         0,   64 },
  { "p64_ad16",   16,   64 },
  { "p256",        0,  256 },
  { "p256_ad16",  16,  256 },
  { "p1024",       0, 1024 },
};
#else
/* Bounded MMIO backend sweep (cosim and Tang Nano 9K bring-up). */
static const bench_case_t SWEEP[] = {
  { "empty",       0,  0 },
  { "ad8",         8,  0 },
  { "pt8",         0,  8 },
  { "ad8_pt8",     8,  8 },
  { "pt16",        0, 16 },
  { "pt24",        0, 24 },
  { "pt32",        0, 32 },
  { "ad16_pt32",  16, 32 },
};
#endif

#define SWEEP_LEN ((uint32_t)(sizeof(SWEEP) / sizeof(SWEEP[0])))

/* ---------------------------------------------------------------------------
 * Per-case execution.
 * Runs:
 *   - the C reference (SW) on the host CPU,
 *   - the hardware accelerator (HW) over its MMIO interface,
 *   - then verifies byte-equality of both ciphertext and recovered plaintext,
 * and emits one machine-parsable CASE line.
 * Returns true on success, false on any mismatch or HW error. */
static bool run_one_case(
    ascon_accel_t *accel,
    const bench_case_t *c,
    bool emit_witness) {

  if (c->ad_len > MAX_BENCH_BYTES || c->pt_len > MAX_BENCH_BYTES) {
    neorv32_uart0_printf("CASE name=%s SKIP reason=exceeds_backend_max\n", c->name);
    return true; /* not a hard failure */
  }

  uint8_t sw_ct[MAX_BENCH_BYTES];
  uint8_t sw_tag[16];
  uint8_t sw_pt[MAX_BENCH_BYTES];
  uint8_t hw_ct[MAX_BENCH_BYTES];
  uint8_t hw_tag[16];
  uint8_t hw_pt[MAX_BENCH_BYTES];
  bool    sw_valid = false;

  memset(sw_ct,  0, sizeof(sw_ct));
  memset(sw_tag, 0, sizeof(sw_tag));
  memset(sw_pt,  0, sizeof(sw_pt));
  memset(hw_ct,  0, sizeof(hw_ct));
  memset(hw_tag, 0, sizeof(hw_tag));
  memset(hw_pt,  0, sizeof(hw_pt));

  /* ---- SW reference, timed with rdcycle around enc and dec separately. */
  const uint64_t sw_t0 = rdcycle64();
  const int sw_enc = ascon_ref_aead128_encrypt(
      key, nonce, ad_pool, c->ad_len, pt_pool, c->pt_len, sw_ct, sw_tag);
  const uint64_t sw_t1 = rdcycle64();
  const int sw_dec = ascon_ref_aead128_decrypt(
      key, nonce, ad_pool, c->ad_len, sw_ct, c->pt_len, sw_tag, sw_pt, &sw_valid);
  const uint64_t sw_t2 = rdcycle64();
  const uint64_t sw_enc_cycles = sw_t1 - sw_t0;
  const uint64_t sw_dec_cycles = sw_t2 - sw_t1;

  if (sw_enc != 0 || sw_dec != 0 || !sw_valid ||
      !bytes_equal(sw_pt, pt_pool, c->pt_len)) {
    neorv32_uart0_printf("CASE name=%s SW_ERR sw_enc=%d sw_dec=%d sw_valid=%u\n",
                         c->name, sw_enc, sw_dec, sw_valid ? 1u : 0u);
    return false;
  }

  /* ---- HW encrypt. */
  ascon_accel_aead_request_t enc_req;
  memset(&enc_req, 0, sizeof(enc_req));
  enc_req.key       = key;
  enc_req.nonce     = nonce;
  enc_req.ad        = ad_pool;
  enc_req.ad_len    = c->ad_len;
  enc_req.input     = pt_pool;
  enc_req.input_len = c->pt_len;
  enc_req.output    = hw_ct;

  ascon_accel_benchmark_result_t enc_res;
  const ascon_accel_status_t enc_status = ascon_accel_benchmark_encrypt(
      accel, ASCON_ACCEL_MODE_AEAD128, &enc_req, &enc_res);
  memcpy(hw_tag, enc_req.tag, sizeof(hw_tag));

  /* ---- HW decrypt. */
  ascon_accel_aead_request_t dec_req;
  memset(&dec_req, 0, sizeof(dec_req));
  dec_req.key       = key;
  dec_req.nonce     = nonce;
  dec_req.ad        = ad_pool;
  dec_req.ad_len    = c->ad_len;
  dec_req.input     = hw_ct;
  dec_req.input_len = c->pt_len;
  dec_req.output    = hw_pt;
  memcpy(dec_req.tag, hw_tag, sizeof(hw_tag));

  ascon_accel_benchmark_result_t dec_res;
  const ascon_accel_status_t dec_status = ascon_accel_benchmark_decrypt(
      accel, ASCON_ACCEL_MODE_AEAD128, &dec_req, &dec_res);

  const bool enc_ok = enc_status == ASCON_ACCEL_OK &&
                      bytes_equal(hw_ct, sw_ct, c->pt_len) &&
                      bytes_equal(hw_tag, sw_tag, 16);
  const bool dec_ok = dec_status == ASCON_ACCEL_OK &&
                      bytes_equal(hw_pt, pt_pool, c->pt_len);

  /* One machine-parsable line per case. */
  neorv32_uart0_printf(
      "CASE name=%s ad=%u pt=%u "
      "sw_enc_cy=%u:%u sw_dec_cy=%u:%u "
      "hw_enc_cy=%u:%u hw_dec_cy=%u:%u "
      "enc_ok=%u dec_ok=%u tag_valid=%u "
      "hw_enc_err=0x%x hw_dec_err=0x%x\n",
      c->name, c->ad_len, c->pt_len,
      (uint32_t)(sw_enc_cycles >> 32), (uint32_t)(sw_enc_cycles & 0xffffffffu),
      (uint32_t)(sw_dec_cycles >> 32), (uint32_t)(sw_dec_cycles & 0xffffffffu),
      (uint32_t)(enc_res.elapsed_cycles >> 32),
      (uint32_t)(enc_res.elapsed_cycles & 0xffffffffu),
      (uint32_t)(dec_res.elapsed_cycles >> 32),
      (uint32_t)(dec_res.elapsed_cycles & 0xffffffffu),
      enc_ok ? 1u : 0u,
      dec_ok ? 1u : 0u,
      dec_res.tag_valid ? 1u : 0u,
      enc_res.error_code,
      dec_res.error_code);

  /* Print the first byte-comparison witness once so the log retains
   * a human-readable HW-vs-SW agreement point. */
  if (emit_witness && c->pt_len > 0u) {
    print_hex("WITNESS SW CT : ", sw_ct,  c->pt_len);
    print_hex("WITNESS HW CT : ", hw_ct,  c->pt_len);
    print_hex("WITNESS SW TAG: ", sw_tag, 16);
    print_hex("WITNESS HW TAG: ", hw_tag, 16);
    print_hex("WITNESS HW PT : ", hw_pt,  c->pt_len);
  }

  return enc_ok && dec_ok;
}

int main(void) {
  neorv32_rte_setup();
  neorv32_uart0_setup(UART_BAUD, 0);

  /* Build-config banner: tells the log which firmware/target produced it. */
  neorv32_uart0_printf("pyrilascon NEORV32 ASCON benchmark\n");
  neorv32_uart0_printf("BUILD        : %s\n", ASCON_BENCH_BUILD_TAG);
  neorv32_uart0_printf("MAX_BYTES    : %u\n", (uint32_t)ASCON_BENCH_MAX_BYTES_TAG);
  neorv32_uart0_printf("SWEEP_CASES  : %u\n", SWEEP_LEN);

  ascon_accel_t accel;
  ascon_accel_init(&accel, ASCON_ACCEL_BASE_ADDR, ACCEL_TIMEOUT_CYCLES);
#ifdef ASCON_BENCH_USE_AXIS_MMIO
  ascon_accel_axis_mmio_transport_ctx_t axis_mmio_ctx;
  ascon_accel_axis_mmio_transport_init(
      &axis_mmio_ctx, ASCON_ACCEL_AXIS_MMIO_BASE_ADDR, ACCEL_TIMEOUT_CYCLES);
  ascon_accel_axis_transport_t axis_mmio_transport = ascon_accel_axis_mmio_transport(&axis_mmio_ctx);
  ascon_accel_set_data_plane(&accel, ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL);
  ascon_accel_set_axis_transport(&accel, &axis_mmio_transport);
  neorv32_uart0_printf("DATA PLANE   : AXI_STREAM_MMIO\n");
  neorv32_uart0_printf("AXIS BASE    : 0x%x\n", (uint32_t)ASCON_ACCEL_AXIS_MMIO_BASE_ADDR);
#else
  ascon_accel_set_data_plane(&accel, ASCON_ACCEL_DATA_PLANE_MMIO_WORD);
  neorv32_uart0_printf("DATA PLANE   : MMIO_WORD\n");
#endif
  ascon_accel_reset(&accel);

  const uint32_t abi  = ascon_accel_abi_version(&accel);
  const uint32_t caps = ascon_accel_capabilities(&accel);
  neorv32_uart0_printf("ABI          : 0x%x\n", abi);
  neorv32_uart0_printf("CAPS         : 0x%x\n", caps);

  if (abi != ASCON_ACCEL_ABI_VERSION) {
    neorv32_uart0_printf("FAIL: ABI mismatch\n");
    return 1;
  }
  if (!ascon_accel_supports(&accel, ASCON_ACCEL_MODE_AEAD128)) {
    neorv32_uart0_printf("FAIL: AEAD128 not supported\n");
    return 1;
  }

  uint32_t passed = 0u;
  uint32_t failed = 0u;
  for (uint32_t i = 0u; i < SWEEP_LEN; ++i) {
    /* Emit one byte-comparison witness, on the first case with pt_len>0. */
    const bool want_witness = (passed == 0u) && (failed == 0u) && (SWEEP[i].pt_len > 0u);
    if (run_one_case(&accel, &SWEEP[i], want_witness)) {
      passed++;
    } else {
      failed++;
    }
  }

  neorv32_uart0_printf("SUMMARY      : passed=%u failed=%u total=%u\n",
                       passed, failed, SWEEP_LEN);

  if (failed != 0u) {
    neorv32_uart0_printf("FAIL\n");
    return 1;
  }
  neorv32_uart0_printf("PASS\n");
  return 0;
}
