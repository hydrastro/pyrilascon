from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "rtl" / "neorv32" / "neorv32_cfs_ascon_stream_axis_mmio.vhd"
FILE_LIST = ROOT / "rtl" / "neorv32" / "ascon_cfs_stream_axis_mmio_file_list.f"
BENCH_MAKEFILE = ROOT / "firmware" / "neorv32_ascon_benchmark" / "Makefile"
BENCH_README = ROOT / "firmware" / "neorv32_ascon_benchmark" / "README.md"
DOC = ROOT / "docs" / "neorv32_stream_cfs_integration.md"


def test_stream_cfs_wrapper_exists_as_alternative_neorv32_cfs_entity() -> None:
    text = WRAPPER.read_text(encoding="utf-8")
    assert "entity neorv32_cfs is" in text
    assert "architecture neorv32_cfs_stream_axis_mmio_rtl of neorv32_cfs is" in text
    assert "ascon_accel_stream_aead128_axis_mmio_system" in text
    assert "bus_req_i : in  bus_req_t" in text
    assert "bus_rsp_o : out bus_rsp_t" in text
    assert "use neorv32.neorv32_package.all" in text


def test_stream_cfs_wrapper_splits_single_cfs_window_between_csr_and_axis_bridge() -> None:
    text = WRAPPER.read_text(encoding="utf-8")
    assert "axis_window_sel <= bus_req_i.addr(8)" in text
    assert "csr_valid       <= bus_req_i.stb and not axis_window_sel" in text
    assert "axis_valid      <= bus_req_i.stb and axis_window_sel" in text
    assert "csr_bus_addr_i      => bus_req_i.addr(7 downto 0)" in text
    assert "axis_bus_addr_i     => bus_req_i.addr(7 downto 0)" in text
    assert "cfs_rdata <= axis_rdata when axis_window_sel = '1' else csr_rdata" in text
    assert "bus_rsp_o.ack  <= bus_req_i.stb" in text
    assert "bus_rsp_o.data <= cfs_rdata" in text


def test_stream_cfs_wrapper_exposes_debug_conduit_bits() -> None:
    text = WRAPPER.read_text(encoding="utf-8")
    assert "axis_bridge_error_o => axis_error" in text
    assert "irq_o <= accel_irq" in text
    assert "cfs_out_o <= (255 downto 4 => '0') & cfs_ready & axis_window_sel & axis_error & accel_irq" in text


def test_stream_cfs_file_list_contains_stream_system_sources_in_order() -> None:
    lines = [line.strip() for line in FILE_LIST.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    expected = [
        "rtl/common/ascon_accel_regs.vh",
        "rtl/common/ascon_round_comb.v",
        "rtl/common/ascon_accel_mmio_regs.v",
        "rtl/stream/ascon_aead128_stream_encrypt.v",
        "rtl/stream/ascon_aead128_stream_decrypt_buffered.v",
        "rtl/stream/ascon_aead128_stream.v",
        "rtl/common/ascon_accel_stream_aead128_top.v",
        "rtl/common/ascon_axis_mmio_bridge.v",
        "rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v",
        "rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd",
    ]
    assert lines == expected


def test_neorv32_benchmark_has_single_cfs_stream_build_mode() -> None:
    text = BENCH_MAKEFILE.read_text(encoding="utf-8")
    assert "USE_CFS_AXIS_MMIO ?= 0" in text
    assert "ifeq ($(USE_CFS_AXIS_MMIO),1)" in text
    assert "USE_AXIS_MMIO := 1" in text
    assert "AXIS_MMIO_BASE_ADDR ?= 0xFFEB0100u" in text
    assert "APP_CFLAGS += -DASCON_ACCEL_AXIS_MMIO_BASE_ADDR=$(AXIS_MMIO_BASE_ADDR)" in text


def test_neorv32_stream_cfs_docs_and_readme_explain_memory_map_and_build() -> None:
    doc = DOC.read_text(encoding="utf-8")
    readme = BENCH_README.read_text(encoding="utf-8")
    for text in (doc, readme):
        assert "USE_CFS_AXIS_MMIO=1" in text
        assert "0xffeb0100" in text.lower() or "0xFFEB0100" in text
    assert "0x000..0x0ff" in doc
    assert "0x100..0x1ff" in doc
    assert "ascon_cfs_stream_axis_mmio_file_list.f" in doc
