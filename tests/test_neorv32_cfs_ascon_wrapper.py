from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_neorv32_cfs_ascon_wrapper_exists_and_replaces_cfs_entity() -> None:
    wrapper = ROOT / "rtl" / "neorv32" / "neorv32_cfs_ascon.vhd"
    assert wrapper.is_file()
    text = wrapper.read_text()
    assert "entity neorv32_cfs is" in text
    assert "architecture neorv32_cfs_rtl of neorv32_cfs is" in text
    assert "use neorv32.neorv32_package.all" in text
    assert "bus_req_i : in  bus_req_t" in text
    assert "bus_rsp_o : out bus_rsp_t" in text


def test_neorv32_cfs_wrapper_maps_internal_bus_to_frozen_mmio() -> None:
    text = (ROOT / "rtl" / "neorv32" / "neorv32_cfs_ascon.vhd").read_text()
    assert "ascon_accel_mmio_aead128_top" in text
    assert "mmio_valid <= bus_req_i.stb" in text
    assert "mmio_write <= bus_req_i.rw" in text
    assert "mmio_addr  <= bus_req_i.addr(7 downto 0)" in text
    assert "mmio_wdata <= bus_req_i.data" in text
    assert "mmio_wstrb <= bus_req_i.ben" in text
    assert "bus_rsp_o.ack  <= bus_req_i.stb" in text
    assert "bus_rsp_o.data <= mmio_rdata" in text
    assert "irq_o <= mmio_irq" in text


def test_neorv32_cfs_file_list_references_required_sources() -> None:
    file_list = ROOT / "rtl" / "neorv32" / "ascon_cfs_file_list.f"
    assert file_list.is_file()
    text = file_list.read_text()
    for required in [
        "rtl/common/ascon_accel_regs.vh",
        "rtl/common/ascon_round_comb.v",
        "rtl/common/ascon_aead128_mmio_backend.v",
        "rtl/common/ascon_accel_mmio_regs.v",
        "rtl/common/ascon_accel_mmio_aead128_top.v",
        "rtl/neorv32/neorv32_cfs_ascon.vhd",
    ]:
        assert required in text


def test_neorv32_demo_makefile_uses_driver_and_neorv32_common_mk() -> None:
    makefile = ROOT / "firmware" / "neorv32_ascon_demo" / "Makefile"
    assert makefile.is_file()
    text = makefile.read_text()
    assert "NEORV32_HOME" in text
    assert "../ascon_accel/ascon_accel.c" in text
    assert "-I../ascon_accel" in text
    assert "sw/common/common.mk" in text


def test_neorv32_cfs_docs_describe_mixed_language_and_backend_status() -> None:
    doc = ROOT / "docs" / "neorv32_cfs_integration.md"
    assert doc.is_file()
    text = doc.read_text()
    assert "0xffeb0000" in text.lower()
    assert "neorv32_cfs_ascon.vhd" in text
    assert "ascon_cfs_file_list.f" in text
    assert "Mixed-language support is required" in text
    assert "does not yet include a full" in text
