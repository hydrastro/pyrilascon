"""The Hasha/Xofa reference must reduce to the NIST-verified model at b=12.

Hasha/Xofa have no independent KAT in this model, so their generated cores are
verified against a Python reference (verify._hashxof_ref) built from the model's
verified permutation. This test grounds that reference: at b=12 it must equal the
model's Hash256/XOF128 byte-for-byte, so the only spec-supplied quantity for the
b=8 cores is the round count itself (confirmed against the Ascon specification).
"""
import random

from ascon_hwmodel.hash_xof import (
    HASH_XOF_CONFIGS,
    HashXofVariant,
    ascon_hash256,
    ascon_xof128,
)

from ascon_designspace.generator.verify import _hashxof_ref

_MSGS = [b"", b"abc", bytes(range(7)), bytes(range(8)), bytes(range(9)),
         bytes(range(17)), bytes(range(32)),
         bytes(random.Random(9).getrandbits(8) for _ in range(45))]


def test_reference_reduces_to_hash256_at_b12():
    iv = HASH_XOF_CONFIGS[HashXofVariant.NIST_HASH256].iv_bytes
    for m in _MSGS:
        assert _hashxof_ref(m, 32, iv, 12) == ascon_hash256(m)


def test_reference_reduces_to_xof128_at_b12():
    iv = HASH_XOF_CONFIGS[HashXofVariant.NIST_XOF128].iv_bytes
    for m in _MSGS:
        for out_len in (16, 32, 40):
            assert _hashxof_ref(m, out_len, iv, 12) == ascon_xof128(m, out_len)
