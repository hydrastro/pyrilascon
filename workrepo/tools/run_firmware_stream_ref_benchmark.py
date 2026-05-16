#!/usr/bin/env python3
"""Run the host-side firmware benchmark against the AXI-stream reference emulator."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

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

C_PROGRAM = r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "ascon_accel.h"
#include "ascon_accel_axis_ref_emulator.h"
#include "ascon_accel_benchmark.h"
#include "ascon_ref_aead128.h"

#define MAX_BYTES 96u

static int bytes_equal(const uint8_t *a, const uint8_t *b, size_t len) {
  uint8_t diff = 0u;
  for (size_t i = 0u; i < len; ++i) {
    diff |= (uint8_t)(a[i] ^ b[i]);
  }
  return diff == 0u;
}

static int run_case(const char *name, const uint8_t *ad, size_t ad_len, const uint8_t *pt, size_t pt_len) {
  uint32_t regs[64] = {0};
  ascon_accel_axis_ref_emulator_ctx_t emu;
  ascon_accel_axis_ref_emulator_init(&emu, regs);

  ascon_accel_t dev;
  ascon_accel_init(&dev, (uintptr_t)regs, 100000u);
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

  uint8_t ct[MAX_BYTES] = {0};
  uint8_t ref_ct[MAX_BYTES] = {0};
  uint8_t dec[MAX_BYTES] = {0};
  uint8_t ref_tag[16] = {0};
  uint8_t invalid_out[MAX_BYTES];
  memset(invalid_out, 0xa5, sizeof(invalid_out));

  if (pt_len > MAX_BYTES || ad_len > MAX_BYTES) {
    return 1;
  }

  ascon_accel_aead_request_t enc = {key, nonce, ad, ad_len, pt, pt_len, ct, {0}};
  ascon_accel_benchmark_result_t enc_result;
  ascon_accel_benchmark_result_init(&enc_result);
  const ascon_accel_status_t enc_status = ascon_accel_benchmark_encrypt(
      &dev, ASCON_ACCEL_MODE_AEAD128, &enc, &enc_result);

  if (ascon_ref_aead128_encrypt(key, nonce, ad, ad_len, pt, pt_len, ref_ct, ref_tag) != 0) {
    return 2;
  }
  const int enc_ok = enc_status == ASCON_ACCEL_OK &&
                     enc_result.status == ASCON_ACCEL_OK &&
                     enc_result.elapsed_cycles != 0u &&
                     bytes_equal(ct, ref_ct, pt_len) &&
                     bytes_equal(enc.tag, ref_tag, sizeof(ref_tag));

  ascon_accel_aead_request_t dec_req = {key, nonce, ad, ad_len, ct, pt_len, dec, {0}};
  memcpy(dec_req.tag, enc.tag, sizeof(dec_req.tag));
  ascon_accel_benchmark_result_t dec_result;
  ascon_accel_benchmark_result_init(&dec_result);
  const ascon_accel_status_t dec_status = ascon_accel_benchmark_decrypt(
      &dev, ASCON_ACCEL_MODE_AEAD128, &dec_req, &dec_result);
  const int dec_ok = dec_status == ASCON_ACCEL_OK &&
                     dec_result.status == ASCON_ACCEL_OK &&
                     dec_result.elapsed_cycles != 0u &&
                     bytes_equal(dec, pt, pt_len) &&
                     ascon_accel_tag_valid(&dev);

  ascon_accel_aead_request_t bad_req = {key, nonce, ad, ad_len, ct, pt_len, invalid_out, {0}};
  memcpy(bad_req.tag, enc.tag, sizeof(bad_req.tag));
  bad_req.tag[15] ^= 0x01u;
  const uint32_t recv_before_invalid = emu.recv_calls;
  const ascon_accel_status_t invalid_status = ascon_accel_decrypt(
      &dev, ASCON_ACCEL_MODE_AEAD128, &bad_req);
  int suppressed = invalid_status == ASCON_ACCEL_ERR_TAG_INVALID &&
                   emu.recv_calls == recv_before_invalid;
  for (size_t i = 0u; i < pt_len; ++i) {
    if (invalid_out[i] != 0xa5u) {
      suppressed = 0;
    }
  }

  printf("CASE name=%s ad=%u text=%u enc_cycles=%llu dec_cycles=%llu enc_ok=%d dec_ok=%d invalid_status=%d suppressed=%d completed=%u send_calls=%u recv_calls=%u\n",
         name,
         (unsigned)ad_len,
         (unsigned)pt_len,
         (unsigned long long)enc_result.elapsed_cycles,
         (unsigned long long)dec_result.elapsed_cycles,
         enc_ok,
         dec_ok,
         (int)invalid_status,
         suppressed,
         (unsigned)emu.completed_operations,
         (unsigned)emu.send_calls,
         (unsigned)emu.recv_calls);

  return (enc_ok && dec_ok && suppressed) ? 0 : 10;
}

int main(void) {
  static const uint8_t ad_short[] = {0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff};
  static const uint8_t pt_short[] = {'h', 'e', 'l', 'l', 'o'};
  static const uint8_t pt_partial[] = {
    0x00, 0x01, 0x02, 0x03, 0x04,
    0x05, 0x06, 0x07, 0x08, 0x09,
    0x0a, 0x0b, 0x0c, 0x0d, 0x0e,
    0x0f, 0x10, 0x11, 0x12,
  };
  static const uint8_t ad_block[] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
  };
  static const uint8_t pt_2block[] = {
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
    0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f,
  };

  int status = 0;
  status |= run_case("empty", 0, 0u, 0, 0u);
  status |= run_case("short", 0, 0u, pt_short, sizeof(pt_short));
  status |= run_case("partial", ad_short, sizeof(ad_short), pt_partial, sizeof(pt_partial));
  status |= run_case("two_block", ad_block, sizeof(ad_block), pt_2block, sizeof(pt_2block));
  return status;
}
'''


def parse_case_line(line: str) -> dict[str, Any]:
    fields = line.split()[1:]
    parsed: dict[str, Any] = {}
    for field in fields:
        key, value = field.split("=", 1)
        if key == "name":
            parsed[key] = value
        else:
            parsed[key] = int(value, 0)
    return parsed


def run_benchmark(repo_root: Path, keep_artifacts: bool = False) -> dict[str, Any]:
    temp_root = repo_root / "build" / "firmware_stream_ref_benchmark" if keep_artifacts else None
    if temp_root is not None:
        temp_root.mkdir(parents=True, exist_ok=True)
        src = temp_root / "firmware_stream_ref_benchmark.c"
        binary = temp_root / "firmware_stream_ref_benchmark"
        src.write_text(C_PROGRAM, encoding="utf-8")
        cleanup = None
    else:
        cleanup = tempfile.TemporaryDirectory(prefix="firmware_stream_ref_benchmark_")
        temp = Path(cleanup.name)
        src = temp / "firmware_stream_ref_benchmark.c"
        binary = temp / "firmware_stream_ref_benchmark"
        src.write_text(C_PROGRAM, encoding="utf-8")

    try:
        compile_cmd = [
            os.environ.get("CC", "gcc"),
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(FW),
            "-I",
            str(REF),
            str(src),
            *map(str, COMMON_SOURCES),
            "-o",
            str(binary),
        ]
        subprocess.run(compile_cmd, cwd=repo_root, check=True, capture_output=True, text=True)
        completed = subprocess.run([str(binary)], cwd=repo_root, check=True, capture_output=True, text=True)
        cases = [parse_case_line(line) for line in completed.stdout.splitlines() if line.startswith("CASE ")]
        return {
            "backend": "axis_stream_ref_emulator",
            "case_count": len(cases),
            "all_passed": all(
                c["enc_ok"] == 1 and c["dec_ok"] == 1 and c["suppressed"] == 1 and c["enc_cycles"] > 0 and c["dec_cycles"] > 0
                for c in cases
            ),
            "cases": cases,
        }
    finally:
        if cleanup is not None:
            cleanup.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--keep-artifacts", action="store_true", help="keep generated C and executable under build/")
    args = parser.parse_args()

    result = run_benchmark(args.repo_root.resolve(), keep_artifacts=args.keep_artifacts)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"backend={result['backend']} cases={result['case_count']} all_passed={int(result['all_passed'])}")
        for case in result["cases"]:
            print(
                "CASE "
                f"name={case['name']} ad={case['ad']} text={case['text']} "
                f"enc_cycles={case['enc_cycles']} dec_cycles={case['dec_cycles']} "
                f"invalid_status={case['invalid_status']} suppressed={case['suppressed']}"
            )
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
