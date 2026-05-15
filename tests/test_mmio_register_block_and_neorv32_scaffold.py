from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mmio_register_block_exists_and_uses_generated_abi() -> None:
    rtl = (ROOT / "rtl" / "common" / "ascon_accel_mmio_regs.v").read_text()
    assert '`include "ascon_accel_regs.vh"' in rtl
    assert "module ascon_accel_mmio_regs" in rtl
    assert "ASCON_REG_CONTROL" in rtl
    assert "ASCON_REG_CAPABILITIES" in rtl
    assert "ASCON_REG_ABI_VERSION" in rtl
    assert "core_start_o" in rtl
    assert "core_data_in_pulse_o" in rtl
    assert "core_generated_tag_i" in rtl


def test_mmio_register_block_exposes_required_capabilities_and_status() -> None:
    rtl = (ROOT / "rtl" / "common" / "ascon_accel_mmio_regs.v").read_text()
    assert "ASCON_CAP_AEAD128" in rtl
    assert "ASCON_CAP_DECRYPT_BUFFERED" in rtl
    assert "ASCON_CAP_CONSTTIME_TAG_COMPARE" in rtl
    assert "ASCON_CAP_CYCLE_COUNTER" in rtl
    assert "ASCON_STATUS_BUSY" in rtl
    assert "ASCON_STATUS_DONE" in rtl
    assert "ASCON_STATUS_TAG_VALID" in rtl
    assert "ASCON_STATUS_ERROR" in rtl


def test_mmio_stub_top_is_explicitly_non_crypto_stub() -> None:
    stub = (ROOT / "rtl" / "common" / "ascon_accel_core_stub.v").read_text()
    top = (ROOT / "rtl" / "common" / "ascon_accel_mmio_stub_top.v").read_text()
    assert "not the cryptographic core" in stub
    assert "module ascon_accel_core_stub" in stub
    assert "module ascon_accel_mmio_stub_top" in top
    assert "ascon_accel_mmio_regs" in top
    assert "ascon_accel_core_stub" in top


def test_driver_default_base_is_neorv32_cfs_base() -> None:
    header = (ROOT / "firmware" / "ascon_accel" / "ascon_accel.h").read_text()
    assert "#define ASCON_ACCEL_BASE_ADDR 0xFFEB0000u" in header


def test_neorv32_firmware_demo_and_docs_exist() -> None:
    demo = ROOT / "firmware" / "neorv32_ascon_demo" / "main.c"
    assert demo.is_file()
    text = demo.read_text()
    assert "#include <neorv32.h>" in text
    assert "ascon_accel_encrypt" in text
    assert "ASCON_ACCEL_MODE_AEAD128" in text
    assert (ROOT / "docs" / "neorv32_cfs_integration.md").is_file()
    assert (ROOT / "rtl" / "neorv32" / "README.md").is_file()
