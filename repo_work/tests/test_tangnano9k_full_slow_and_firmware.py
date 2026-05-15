from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_tangnano9k_full_slow_target_exists() -> None:
    target = ROOT / "boards" / "tangnano9k" / "ascon_aead128_full_slow"
    assert (target / "Makefile").is_file()
    assert (target / "tangnano9k_ascon_aead128_full_slow.cst").is_file()
    assert (target / "rtl" / "ascon_round_comb.v").is_file()
    assert (target / "rtl" / "ascon_aead128_encrypt_kat_core.v").is_file()
    assert (target / "rtl" / "ascon_aead128_decrypt_kat_core.v").is_file()
    assert (target / "rtl" / "tangnano9k_ascon_aead128_full_slow_top.v").is_file()


def test_full_slow_decryption_buffers_plaintext_until_tag_verification() -> None:
    rtl = (ROOT / "boards" / "tangnano9k" / "ascon_aead128_full_slow" / "rtl" / "ascon_aead128_decrypt_kat_core.v").read_text()
    assert "plaintext_release_q" in rtl
    assert "tag_match_w && (pt_buffer_q == PT_EXPECTED)" in rtl
    assert "pt_buffer_q <= 208'b0" in rtl


def test_firmware_api_names_requested_modes() -> None:
    header = (ROOT / "firmware" / "ascon_accel" / "ascon_accel.h").read_text()
    for mode in [
        "ASCON_ACCEL_MODE_AEAD128",
        "ASCON_ACCEL_MODE_AEAD128A",
        "ASCON_ACCEL_MODE_AEAD128PQ",
        "ASCON_ACCEL_MODE_HASH",
        "ASCON_ACCEL_MODE_HASHA",
        "ASCON_ACCEL_MODE_XOF",
        "ASCON_ACCEL_MODE_XOFA",
        "ASCON_ACCEL_MODE_CXOF128",
    ]:
        assert mode in header


def test_full_slow_makefile_uses_expected_top() -> None:
    makefile = (ROOT / "boards" / "tangnano9k" / "ascon_aead128_full_slow" / "Makefile").read_text()
    assert "TOP      := tangnano9k_ascon_aead128_full_slow_top" in makefile
    assert "prog-sram" in makefile
    assert "prog-flash" in makefile
