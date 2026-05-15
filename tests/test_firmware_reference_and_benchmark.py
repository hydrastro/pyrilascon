from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_portable_c_reference_matches_aead128_kat(tmp_path: Path) -> None:
    program = tmp_path / "test_ref.c"
    binary = tmp_path / "test_ref"
    program.write_text(
        r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "firmware/ascon_ref/ascon_ref_aead128.h"

static const uint8_t expected_ct_tag[] = {
  0x96, 0x2B, 0x80, 0x16, 0x83, 0x6C, 0x75, 0xA7, 0xD8,
  0x68, 0x66, 0x58, 0x8C, 0xA2, 0x45, 0xD8, 0x86,
};

int main(void) {
  const uint8_t key[16] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
  };
  const uint8_t nonce[16] = {
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F,
  };
  const uint8_t ad[1] = {0x30};
  const uint8_t pt[1] = {0x20};
  uint8_t ct[1] = {0};
  uint8_t tag[16] = {0};
  uint8_t decrypted[1] = {0};
  bool valid = false;

  if (ascon_ref_aead128_encrypt(key, nonce, ad, sizeof(ad), pt, sizeof(pt), ct, tag) != 0) {
    return 1;
  }
  if (ct[0] != expected_ct_tag[0] || memcmp(tag, &expected_ct_tag[1], sizeof(tag)) != 0) {
    return 2;
  }
  if (ascon_ref_aead128_decrypt(key, nonce, ad, sizeof(ad), ct, sizeof(ct), tag, decrypted, &valid) != 0) {
    return 3;
  }
  if (!valid || decrypted[0] != pt[0]) {
    return 4;
  }
  tag[15] ^= 0x01u;
  decrypted[0] = 0xAAu;
  if (ascon_ref_aead128_decrypt(key, nonce, ad, sizeof(ad), ct, sizeof(ct), tag, decrypted, &valid) != 0) {
    return 5;
  }
  if (valid || decrypted[0] != 0x00u) {
    return 6;
  }
  return 0;
}
'''
    )
    subprocess.run(
        [
            "gcc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I.",
            "firmware/ascon_ref/ascon_ref_aead128.c",
            str(program),
            "-o",
            str(binary),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run([str(binary)], check=True)


def test_neorv32_benchmark_firmware_project_files_exist() -> None:
    bench_dir = ROOT / "firmware" / "neorv32_ascon_benchmark"
    assert (bench_dir / "main.c").is_file()
    assert (bench_dir / "Makefile").is_file()
    assert (bench_dir / "README.md").is_file()
    makefile = (bench_dir / "Makefile").read_text()
    assert "../ascon_ref/ascon_ref_aead128.c" in makefile
    assert "../ascon_accel/ascon_accel_benchmark.c" in makefile
    main = (bench_dir / "main.c").read_text()
    assert "ascon_ref_aead128_encrypt" in main
    assert "ascon_accel_benchmark_encrypt" in main
    assert "hardware encryption did not beat software" in main
