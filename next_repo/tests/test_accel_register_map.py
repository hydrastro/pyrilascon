from pathlib import Path
import re

from ascon_arch import register_map as rm
from tools import generate_accel_regs

ROOT = Path(__file__).resolve().parents[1]


def test_register_offsets_are_unique_word_aligned_and_versioned() -> None:
    offsets = [reg.offset for reg in rm.REGISTERS]
    assert len(offsets) == len(set(offsets))
    assert all(offset % 4 == 0 for offset in offsets)
    assert rm.REGISTER_MAP_VERSION == 1
    names = {reg.name for reg in rm.REGISTERS}
    assert {"CONTROL", "STATUS", "MODE", "CAPABILITIES", "ABI_VERSION"}.issubset(names)
    assert {"AD_LEN", "TEXT_LEN", "OUT_LEN", "CUSTOM_LEN"}.issubset(names)


def test_generated_c_and_verilog_register_headers_are_in_sync() -> None:
    assert (ROOT / "firmware/ascon_accel/ascon_accel_regs.h").read_text() == generate_accel_regs.emit_c_header()
    assert (ROOT / "rtl/common/ascon_accel_regs.vh").read_text() == generate_accel_regs.emit_v_header()
    assert (ROOT / "docs/ascon_accel_register_map.md").read_text() == generate_accel_regs.emit_doc()


def test_firmware_uses_generated_register_header_not_private_defines() -> None:
    header = (ROOT / "firmware/ascon_accel/ascon_accel.h").read_text()
    source = (ROOT / "firmware/ascon_accel/ascon_accel.c").read_text()
    assert '#include "ascon_accel_regs.h"' in header
    assert 'ASCON_REG_CAPABILITIES' in source
    assert 'ascon_accel_supports' in source
    assert '#define ASCON_REG_CONTROL' not in source
    assert 'ASCON_REG_AD_LEN            0x10u' in (ROOT / "firmware/ascon_accel/ascon_accel_regs.h").read_text()


def test_c_and_verilog_mode_values_match_python_register_map() -> None:
    c_header = (ROOT / "firmware/ascon_accel/ascon_accel_regs.h").read_text()
    v_header = (ROOT / "rtl/common/ascon_accel_regs.vh").read_text()
    for enum in rm.MODE_ENUMS:
        assert f"#define ASCON_MODE_{enum.name}" in c_header
        assert f"`define ASCON_MODE_{enum.name}" in v_header
        assert re.search(rf"#define ASCON_MODE_{enum.name}\s+{enum.value}u", c_header)
        assert re.search(rf"`define ASCON_MODE_{enum.name}\s+4'd{enum.value}", v_header)


def test_register_map_documents_decryption_buffer_policy() -> None:
    doc = (ROOT / "docs/ascon_accel_register_map.md").read_text()
    assert "ABI version: `1`" in doc
    assert "plaintext must not be made visible" in doc
    assert "CAPABILITIES" in doc
    assert "ASCON_CAP_DECRYPT_BUFFERED" in doc
