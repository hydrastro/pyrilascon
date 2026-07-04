"""The ascon_accel driver (interact-via-C path) must produce correct AEAD128
end-to-end when driven through the ref-emulator transport.

Compiles the driver core + emulator + portable reference + the C self-test and
runs it natively (no hardware). The self-test checks driver output bit-exact
against the reference in the same binary and verifies an encrypt->decrypt round
trip. Skipped only if no C compiler is available.
"""
import pathlib
import shutil
import subprocess
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ACCEL = ROOT / "firmware" / "ascon_accel"
REF = ROOT / "firmware" / "ascon_ref"
SELFTEST = ROOT / "firmware" / "host" / "driver_selftest.c"
_CC = shutil.which("gcc") or shutil.which("cc")

pytestmark = pytest.mark.skipif(_CC is None, reason="no C compiler (gcc/cc)")

DRIVER_SRCS = [
    SELFTEST,
    ACCEL / "ascon_accel.c",
    ACCEL / "ascon_accel_control.c",
    ACCEL / "ascon_accel_caps.c",
    ACCEL / "ascon_accel_mmio_data.c",
    ACCEL / "ascon_accel_axis_data.c",
    ACCEL / "ascon_accel_axis_ref_emulator.c",
    REF / "ascon_ref_aead128.c",
]


def test_driver_through_emulator_matches_reference():
    with tempfile.TemporaryDirectory() as tmp:
        exe = pathlib.Path(tmp) / "driver_selftest"
        compile_cmd = [
            _CC, "-O2", "-Wall", "-Wextra",
            "-I", str(ACCEL), "-I", str(REF),
            "-o", str(exe),
            *[str(s) for s in DRIVER_SRCS],
        ]
        comp = subprocess.run(compile_cmd, capture_output=True, text=True)
        assert comp.returncode == 0, f"driver did not compile:\n{comp.stderr}"
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0 and "PASS" in run.stdout, run.stdout + run.stderr
