"""Tests for the DMA front-end per-payload sweep (RASD~§8.4 sizes).

The dry-run tests check the payload set is well formed and includes the
64/256/1024-byte RASD~§8.4 sizes. The simulation tests (skipped when Icarus is
absent) run the full sweep through the system cosimulation, confirm every case
matches the golden model, and assert that the end-to-end cycle count grows
monotonically with the number of beats --- the signature of true streaming, and
the property the four-beat CPU bridge FIFO cannot provide past four beats.
"""

import shutil

import pytest

from tools.run_stream_axis_dma_system_sweep import (
    SWEEP_CASES,
    DATA_BYTES,
    run_sweep,
)

_HAVE_IVERILOG = shutil.which("iverilog") is not None and shutil.which("vvp") is not None
_requires_iverilog = pytest.mark.skipif(not _HAVE_IVERILOG, reason="iverilog/vvp not installed")


def test_sweep_covers_rasd_payload_sizes() -> None:
    text_sizes = {c.text_len for c in SWEEP_CASES}
    # RASD~§8.4 performance payload set.
    assert {64, 256, 1024}.issubset(text_sizes)
    # The 1024-byte case is 64 beats, far beyond the four-beat CPU bridge FIFO.
    assert max(text_sizes) // DATA_BYTES == 64


def test_dry_run_reports_expected_beat_counts() -> None:
    rows = {r.label: r for r in run_sweep(dry_run=True)}
    assert rows["pt64"].text_beats == 4
    assert rows["pt256"].text_beats == 16
    assert rows["pt1024"].text_beats == 64
    # Associated data adds its own beat(s) on top of the text beats.
    assert rows["ad16_pt1024"].ad_beats == 1
    # Dry-run does not invoke the simulator, so no cycle data is present.
    assert all(r.cycles is None for r in rows.values())


@_requires_iverilog
def test_sweep_all_cases_match_golden() -> None:
    rows = run_sweep(dry_run=False)
    assert rows, "sweep produced no rows"
    for r in rows:
        assert r.matched, f"case {r.label} did not match the golden model"
        assert r.error_code == 0, f"case {r.label} raised error_code {r.error_code}"
        assert r.out_bytes == r.text_len, (
            f"case {r.label}: out_bytes {r.out_bytes} != text_len {r.text_len}"
        )


@_requires_iverilog
def test_sweep_cycles_grow_monotonically_with_beats() -> None:
    rows = [r for r in run_sweep(dry_run=False) if r.cycles is not None]
    # Order by total beats and confirm cycles are strictly increasing: each
    # additional beat costs real cycles, which is what streaming (rather than a
    # fixed-size buffered transfer) looks like.
    ordered = sorted(rows, key=lambda r: r.ad_beats + r.text_beats)
    cycles = [r.cycles for r in ordered]
    assert cycles == sorted(cycles), f"cycles not monotonic in beats: {cycles}"
    assert len(set(cycles)) == len(cycles), f"cycle counts not strictly increasing: {cycles}"


@_requires_iverilog
def test_largest_payload_streams_far_beyond_bridge_fifo() -> None:
    rows = {r.label: r for r in run_sweep(dry_run=False)}
    big = rows["pt1024"]
    assert big.text_beats == 64
    assert big.matched
    assert big.out_bytes == 1024
    # And it really cost more cycles than a four-beat (64-byte) transfer, i.e. it
    # streamed the extra 60 beats rather than truncating at the FIFO bound.
    small = rows["pt64"]
    assert big.cycles > small.cycles
