from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_real_aead128_mmio_backend_exists_and_is_not_stub() -> None:
    backend = ROOT / "rtl" / "common" / "ascon_aead128_mmio_backend.v"
    text = backend.read_text()
    assert backend.is_file()
    assert "module ascon_aead128_mmio_backend" in text
    assert "NIST Ascon-AEAD128 only" in text
    assert "MAX_AD_BYTES" in text
    assert "MAX_TEXT_BYTES" in text
    assert "ascon_round_comb" in text
    assert "ASCON_ERROR_TAG_INVALID" in text
    assert "Do not expose unauthenticated plaintext" in text


def test_mmio_register_block_supports_output_read_pulse() -> None:
    rtl = (ROOT / "rtl" / "common" / "ascon_accel_mmio_regs.v").read_text()
    assert "core_data_out_read_pulse_o" in rtl
    assert "ASCON_REG_DATA_OUT" in rtl
    assert "core_data_out_i" in rtl
    assert "core_data_out_ctrl_i" in rtl


def test_mmio_aead128_top_connects_regs_to_backend() -> None:
    top = (ROOT / "rtl" / "common" / "ascon_accel_mmio_aead128_top.v").read_text()
    assert "module ascon_accel_mmio_aead128_top" in top
    assert "ascon_accel_mmio_regs" in top
    assert "ascon_aead128_mmio_backend" in top
    assert "ASCON_CAP_AEAD128" in top
    assert "ASCON_CAP_DECRYPT_BUFFERED" in top


def test_tangnano9k_mmio_slow_target_exists() -> None:
    target = ROOT / "boards" / "tangnano9k" / "ascon_aead128_mmio_slow"
    assert (target / "Makefile").is_file()
    assert (target / "README.md").is_file()
    assert (target / "tangnano9k_ascon_aead128_mmio_slow.cst").is_file()
    top = (target / "rtl" / "tangnano9k_ascon_aead128_mmio_slow_top.v").read_text()
    assert "ascon_accel_mmio_aead128_top" in top
    assert "ST_ENC_SETUP" in top
    assert "ST_DEC_SETUP" in top
    assert "expected_ct_word" in top
    assert "expected_pt_word" in top


def test_mmio_slow_makefile_includes_common_backend_files() -> None:
    makefile = (ROOT / "boards" / "tangnano9k" / "ascon_aead128_mmio_slow" / "Makefile").read_text()
    assert "ascon_aead128_mmio_backend.v" in makefile
    assert "ascon_accel_mmio_regs.v" in makefile
    assert "ascon_accel_mmio_aead128_top.v" in makefile
    assert "prog-sram" in makefile
