from ascon_hwmodel import AsconVariant, EXPECTED_IV, ascon_iv, assert_iv_table


def test_iv_table() -> None:
    assert_iv_table()


def test_aead128_iv() -> None:
    assert ascon_iv(AsconVariant.AEAD128) == EXPECTED_IV[AsconVariant.AEAD128]
