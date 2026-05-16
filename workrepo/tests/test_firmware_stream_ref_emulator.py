from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware" / "ascon_accel"
REF = ROOT / "firmware" / "ascon_ref"

COMMON_SOURCES = [
    FW / "ascon_accel.c",
    FW / "ascon_accel_control.c",
    FW / "ascon_accel_caps.c",
    FW / "ascon_accel_mmio_data.c",
    FW / "ascon_accel_axis_data.c",
    FW / "ascon_accel_benchmark.c",
    FW / "ascon_accel_axis_ref_emulator.c",
    REF / "ascon_ref_aead128.c",
]


def compile_and_run(tmp_path: Path, source: str) -> None:
    program = tmp_path / "stream_ref_emulator_test.c"
    binary = tmp_path / "stream_ref_emulator_test"
    program.write_text(source, encoding="utf-8")
    subprocess.run(
        [
            "gcc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(FW),
            "-I",
            str(REF),
            str(program),
            *map(str, COMMON_SOURCES),
            "-o",
            str(binary),
        ],
        check=True,
        cwd=ROOT,
    )
    subprocess.run([str(binary)], check=True, cwd=ROOT)


def test_axis_ref_emulator_exercises_firmware_encrypt_decrypt_end_to_end(tmp_path: Path) -> None:
    compile_and_run(
        tmp_path,
        r'''
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "ascon_accel.h"
#include "ascon_accel_axis_ref_emulator.h"
#include "ascon_accel_benchmark.h"
#include "ascon_ref_aead128.h"

static int run_case(const uint8_t *ad, size_t ad_len, const uint8_t *pt, size_t pt_len) {
  uint32_t regs[64] = {0};
  ascon_accel_axis_ref_emulator_ctx_t emu;
  ascon_accel_axis_ref_emulator_init(&emu, regs);

  ascon_accel_t dev;
  ascon_accel_init(&dev, (uintptr_t)regs, 10000u);
  ascon_accel_axis_transport_t transport = ascon_accel_axis_ref_emulator_transport(&emu);
  ascon_accel_set_axis_transport(&dev, &transport);
  ascon_accel_set_data_plane(&dev, ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL);

  const uint8_t key[16] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
  };
  const uint8_t nonce[16] = {
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
  };
  uint8_t ct[80] = {0};
  uint8_t ref_ct[80] = {0};
  uint8_t dec[80] = {0};
  uint8_t tag[16] = {0};
  uint8_t ref_tag[16] = {0};

  ascon_accel_aead_request_t enc = {key, nonce, ad, ad_len, pt, pt_len, ct, {0}};
  ascon_accel_benchmark_result_t bench;
  ascon_accel_benchmark_result_init(&bench);
  if (ascon_accel_benchmark_encrypt(&dev, ASCON_ACCEL_MODE_AEAD128, &enc, &bench) != ASCON_ACCEL_OK) {
    return 1;
  }
  memcpy(tag, enc.tag, sizeof(tag));
  if (bench.status != ASCON_ACCEL_OK || bench.elapsed_cycles == 0u || !bench.tag_valid) {
    return 2;
  }
  if (ascon_ref_aead128_encrypt(key, nonce, ad, ad_len, pt, pt_len, ref_ct, ref_tag) != 0) {
    return 3;
  }
  if (memcmp(ct, ref_ct, pt_len) != 0 || memcmp(tag, ref_tag, sizeof(tag)) != 0) {
    return 4;
  }
  if (emu.send_calls != 2u || emu.recv_calls != 1u || emu.completed_operations != 1u) {
    return 5;
  }

  ascon_accel_aead_request_t dec_req = {key, nonce, ad, ad_len, ct, pt_len, dec, {0}};
  memcpy(dec_req.tag, tag, sizeof(dec_req.tag));
  if (ascon_accel_decrypt(&dev, ASCON_ACCEL_MODE_AEAD128, &dec_req) != ASCON_ACCEL_OK) {
    return 6;
  }
  if (memcmp(dec, pt, pt_len) != 0 || !ascon_accel_tag_valid(&dev)) {
    return 7;
  }
  if (emu.completed_operations != 2u || emu.recv_calls != 2u) {
    return 8;
  }
  return 0;
}

int main(void) {
  const uint8_t ad1[] = {0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff};
  const uint8_t pt1[] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
    0x10, 0x11, 0x12,
  };
  const uint8_t ad2[] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
  };
  const uint8_t pt2[] = {
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
    0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f,
  };
  int status = run_case(0, 0u, 0, 0u);
  if (status != 0) {
    return status;
  }
  status = run_case(0, 0u, pt1, sizeof(pt1));
  if (status != 0) {
    return 20 + status;
  }
  status = run_case(ad1, sizeof(ad1), pt1, sizeof(pt1));
  if (status != 0) {
    return 40 + status;
  }
  status = run_case(ad2, sizeof(ad2), pt2, sizeof(pt2));
  if (status != 0) {
    return 60 + status;
  }
  return 0;
}
''',
    )


def test_axis_ref_emulator_suppresses_invalid_decrypt_plaintext(tmp_path: Path) -> None:
    compile_and_run(
        tmp_path,
        r'''
#include <stdint.h>
#include <string.h>
#include "ascon_accel.h"
#include "ascon_accel_axis_ref_emulator.h"

int main(void) {
  uint32_t regs[64] = {0};
  ascon_accel_axis_ref_emulator_ctx_t emu;
  ascon_accel_axis_ref_emulator_init(&emu, regs);

  ascon_accel_t dev;
  ascon_accel_init(&dev, (uintptr_t)regs, 10000u);
  ascon_accel_axis_transport_t transport = ascon_accel_axis_ref_emulator_transport(&emu);
  ascon_accel_set_axis_transport(&dev, &transport);
  ascon_accel_set_data_plane(&dev, ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL);

  const uint8_t key[16] = {0};
  const uint8_t nonce[16] = {0};
  const uint8_t plaintext[5] = {'h', 'e', 'l', 'l', 'o'};
  uint8_t ciphertext[5] = {0};
  uint8_t output[5] = {0xaa, 0xaa, 0xaa, 0xaa, 0xaa};
  ascon_accel_aead_request_t enc = {key, nonce, 0, 0u, plaintext, sizeof(plaintext), ciphertext, {0}};

  if (ascon_accel_encrypt(&dev, ASCON_ACCEL_MODE_AEAD128, &enc) != ASCON_ACCEL_OK) {
    return 1;
  }
  enc.tag[0] ^= 0x01u;
  ascon_accel_aead_request_t dec = {key, nonce, 0, 0u, ciphertext, sizeof(ciphertext), output, {0}};
  memcpy(dec.tag, enc.tag, sizeof(dec.tag));
  if (ascon_accel_decrypt(&dev, ASCON_ACCEL_MODE_AEAD128, &dec) != ASCON_ACCEL_ERR_TAG_INVALID) {
    return 2;
  }
  if (emu.recv_calls != 1u) {
    return 3;
  }
  for (size_t i = 0u; i < sizeof(output); ++i) {
    if (output[i] != 0xaau) {
      return 4;
    }
  }
  if (ascon_accel_error_code(&dev) != ASCON_ERROR_TAG_INVALID || ascon_accel_tag_valid(&dev)) {
    return 5;
  }
  return 0;
}
''',
    )


def test_axis_ref_emulator_is_documented_and_host_only() -> None:
    header = (FW / "ascon_accel_axis_ref_emulator.h").read_text(encoding="utf-8")
    source = (FW / "ascon_accel_axis_ref_emulator.c").read_text(encoding="utf-8")
    assert "Host-side AXI Stream accelerator emulator" in header
    assert "ascon_ref_aead128_encrypt" in source
    assert "ascon_ref_aead128_decrypt" in source
    assert "ASCON_ERROR_TAG_INVALID" in source
