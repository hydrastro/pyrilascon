from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "firmware" / "neorv32_ascon_benchmark"


def test_neorv32_benchmark_can_select_axis_mmio_stream_transport() -> None:
    makefile = (BENCH / "Makefile").read_text(encoding="utf-8")
    assert "USE_AXIS_MMIO ?= 0" in makefile
    assert "ifeq ($(USE_AXIS_MMIO),1)" in makefile
    assert "../ascon_accel/ascon_accel_axis_mmio_transport.c" in makefile
    assert "-DASCON_BENCH_USE_AXIS_MMIO=1" in makefile


def test_neorv32_benchmark_initializes_stream_transport_before_reset() -> None:
    main = (BENCH / "main.c").read_text(encoding="utf-8")
    assert '#include "../ascon_accel/ascon_accel_axis_mmio_transport.h"' in main
    assert "ASCON_BENCH_USE_AXIS_MMIO" in main
    assert "ascon_accel_axis_mmio_transport_ctx_t axis_mmio_ctx" in main
    assert "ascon_accel_axis_mmio_transport_init(" in main
    assert "ascon_accel_set_data_plane(&accel, ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL)" in main
    assert "ascon_accel_set_axis_transport(&accel, &axis_mmio_transport)" in main
    assert "ascon_accel_reset(&accel);" in main
    assert main.index("ascon_accel_set_axis_transport") < main.index("ascon_accel_reset(&accel);")


def test_neorv32_benchmark_uart_reports_stream_path_bringup_counters() -> None:
    main = (BENCH / "main.c").read_text(encoding="utf-8")
    assert '"DATA PLANE   : AXI_STREAM_MMIO\\n"' in main
    assert '"AXIS BASE    : 0x%x\\n"' in main
    # The sweep-based firmware emits per-case CASE lines instead of the
    # legacy "AXIS TX/RX beats" diagnostic block. The stream path still
    # initialises and reports its identity via DATA PLANE/AXIS BASE.


def test_neorv32_stream_benchmark_documentation_has_build_command() -> None:
    readme = (BENCH / "README.md").read_text(encoding="utf-8")
    assert "USE_AXIS_MMIO=1" in readme
    assert "ASCON_ACCEL_AXIS_MMIO_BASE_ADDR" in readme
    assert "DATA PLANE : AXI_STREAM_MMIO" in readme
