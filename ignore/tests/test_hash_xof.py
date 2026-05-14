from ascon_hwmodel.hash_xof import ascon_cxof128, ascon_hash256, ascon_xof128


def test_hash256_length_and_determinism():
    digest1 = ascon_hash256(b"abc")
    digest2 = ascon_hash256(b"abc")
    digest3 = ascon_hash256(b"abd")
    assert len(digest1) == 32
    assert digest1 == digest2
    assert digest1 != digest3


def test_xof_lengths_prefix_property():
    out16 = ascon_xof128(b"abc", 16)
    out40 = ascon_xof128(b"abc", 40)
    assert len(out16) == 16
    assert len(out40) == 40
    assert out40[:16] == out16


def test_cxof_customization_domain_separates():
    msg = b"abc"
    out_a = ascon_cxof128(msg, 32, b"A")
    out_b = ascon_cxof128(msg, 32, b"B")
    assert len(out_a) == 32
    assert out_a != out_b
