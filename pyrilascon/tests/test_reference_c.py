"""The C reference (the benchmark's software baseline) must match the golden
model bit-for-bit, and round-trip correctly.

Compiles ``firmware/ascon_ref/ascon_ref_aead128.c`` into a shared library and
calls it via ctypes, comparing against ``ascon_hwmodel``'s NIST-KAT-verified
AEAD128. Skipped only if no C compiler is available.
"""
import ctypes
import os
import pathlib
import random
import shutil
import subprocess
import tempfile

import pytest

from ascon_hwmodel.aead import ascon_aead128_encrypt

REF_DIR = pathlib.Path(__file__).resolve().parents[1] / "firmware" / "ascon_ref"
_CC = shutil.which("gcc") or shutil.which("cc")

pytestmark = pytest.mark.skipif(_CC is None, reason="no C compiler (gcc/cc)")


@pytest.fixture(scope="module")
def libref():
    tmp = tempfile.mkdtemp()
    so = pathlib.Path(tmp) / "libasconref.so"
    src = REF_DIR / "ascon_ref_aead128.c"
    res = subprocess.run(
        [_CC, "-O2", "-fPIC", "-shared", "-o", str(so), str(src)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    lib = ctypes.CDLL(str(so))
    lib.ascon_ref_aead128_encrypt.restype = ctypes.c_int
    lib.ascon_ref_aead128_decrypt.restype = ctypes.c_int
    try:
        yield lib
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _buf(data: bytes):
    n = max(len(data), 1)
    arr = (ctypes.c_uint8 * n)()
    for i, b in enumerate(data):
        arr[i] = b
    return arr


def _c_encrypt(lib, key, nonce, ad, pt):
    ct = (ctypes.c_uint8 * max(len(pt), 1))()
    tag = (ctypes.c_uint8 * 16)()
    rc = lib.ascon_ref_aead128_encrypt(
        _buf(key), _buf(nonce), _buf(ad), len(ad), _buf(pt), len(pt), ct, tag
    )
    assert rc == 0
    return bytes(ct[: len(pt)]), bytes(tag)


def _c_decrypt(lib, key, nonce, ad, ct, tag):
    pt = (ctypes.c_uint8 * max(len(ct), 1))()
    valid = ctypes.c_bool(False)
    rc = lib.ascon_ref_aead128_decrypt(
        _buf(key), _buf(nonce), _buf(ad), len(ad), _buf(ct), len(ct),
        _buf(tag), pt, ctypes.byref(valid)
    )
    assert rc == 0
    return bytes(pt[: len(ct)]), valid.value


@pytest.mark.parametrize("ad_len,pt_len", [(0, 0), (0, 5), (16, 0), (7, 16), (16, 16), (33, 40), (1, 64)])
def test_c_encrypt_matches_model(libref, ad_len, pt_len):
    rng = random.Random(0xA5C0 + ad_len * 97 + pt_len)
    key = bytes(rng.getrandbits(8) for _ in range(16))
    nonce = bytes(rng.getrandbits(8) for _ in range(16))
    ad = bytes(rng.getrandbits(8) for _ in range(ad_len))
    pt = bytes(rng.getrandbits(8) for _ in range(pt_len))

    c_ct, c_tag = _c_encrypt(libref, key, nonce, ad, pt)
    model = ascon_aead128_encrypt(key, nonce, ad, pt)
    assert c_ct == model.ciphertext
    assert c_tag == model.tag


def test_c_round_trip_and_tag_rejection(libref):
    rng = random.Random(1234)
    for _ in range(25):
        key = bytes(rng.getrandbits(8) for _ in range(16))
        nonce = bytes(rng.getrandbits(8) for _ in range(16))
        ad = bytes(rng.getrandbits(8) for _ in range(rng.randint(0, 40)))
        pt = bytes(rng.getrandbits(8) for _ in range(rng.randint(0, 64)))

        ct, tag = _c_encrypt(libref, key, nonce, ad, pt)
        rec, valid = _c_decrypt(libref, key, nonce, ad, ct, tag)
        assert valid is True
        assert rec == pt

        bad = bytearray(tag)
        bad[-1] ^= 0x01
        _, valid_bad = _c_decrypt(libref, key, nonce, ad, ct, bytes(bad))
        assert valid_bad is False
