#!/usr/bin/env python3
"""Per-payload cycle sweep for the descriptor-driven DMA AXI-stream front-end.

The integrated NEORV32 + ASCON-CFS co-simulation table in the report
(``tab:sweep``) stops at the eight payload shapes the *bounded* CPU-driven MMIO
backend supports (text up to the wrapper's small ``MAX_TEXT_BYTES`` and the
four-beat bridge RX FIFO). The RASD's performance requirement (RASD~§8.4) also
calls for the larger 64-, 256-, and 1024-byte payloads, which the MMIO bridge
cannot stream without an interleaved firmware pump. The autonomous DMA
front-end can: it moves the whole payload itself, one beat in flight, with no
internal output FIFO to overflow.

This script drives the same Icarus Verilog system cosimulation used by
``run_stream_axis_dma_system_vector.py`` across a payload set that includes the
RASD~§8.4 sizes, verifies each result bit-for-bit against the Python golden
model, and reports the end-to-end cycle count (from the descriptor ``GO`` pulse
to ``STATUS.DONE``) for each size. The cosimulation memory model accepts every
request with a single-cycle read latency, so the reported cycles are the
front-end's own streaming/bookkeeping cost, not a model of external DRAM timing.

Usage::

    python tools/run_stream_axis_dma_system_sweep.py            # full iverilog sweep
    python tools/run_stream_axis_dma_system_sweep.py --json      # machine-readable
    python tools/run_stream_axis_dma_system_sweep.py --dry-run   # list the set only

The exit status is non-zero if any case fails to match the golden model.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.run_stream_axis_dma_system_vector import (  # noqa: E402
    DATA_BYTES,
    DST_BASE_BYTES,
    MEM_WORDS,
    run_vector,
)

# Standard streaming test key/nonce, matching the other stream vector runners.
KEY = bytes(range(16))
NONCE = bytes(range(0x10, 0x20))


@dataclass(frozen=True)
class SweepCase:
    label: str
    ad_len: int
    text_len: int


# The 64/256/1024-byte plaintext sizes are the RASD~§8.4 payload set; 0 and 16
# anchor the low end so the per-beat slope is visible, and the final case
# exercises associated data alongside the largest payload.
SWEEP_CASES: tuple[SweepCase, ...] = (
    SweepCase("empty", 0, 0),
    SweepCase("pt16", 0, 16),
    SweepCase("pt64", 0, 64),
    SweepCase("pt256", 0, 256),
    SweepCase("pt1024", 0, 1024),
    SweepCase("ad16_pt1024", 16, 1024),
)


def _pattern(n: int, *, seed: int = 0) -> bytes:
    """Deterministic, size-distinct byte pattern."""
    return bytes(((i + seed) * 7 + 1) & 0xFF for i in range(n))


def _beats(n: int) -> int:
    if n == 0:
        return 0
    return (n + DATA_BYTES - 1) // DATA_BYTES


def _check_memory_fits(case: SweepCase) -> None:
    end = DST_BASE_BYTES + case.text_len
    if end > MEM_WORDS * 4:
        raise ValueError(
            f"case {case.label}: destination end 0x{end:x} exceeds the "
            f"{MEM_WORDS * 4}-byte cosim memory model"
        )


@dataclass
class SweepRow:
    label: str
    ad_len: int
    text_len: int
    ad_beats: int
    text_beats: int
    matched: bool
    cycles: int | None
    out_bytes: int | None
    error_code: int | None


def run_sweep(*, dry_run: bool) -> list[SweepRow]:
    rows: list[SweepRow] = []
    for case in SWEEP_CASES:
        _check_memory_fits(case)
        if dry_run:
            rows.append(
                SweepRow(
                    label=case.label,
                    ad_len=case.ad_len,
                    text_len=case.text_len,
                    ad_beats=_beats(case.ad_len),
                    text_beats=_beats(case.text_len),
                    matched=False,
                    cycles=None,
                    out_bytes=None,
                    error_code=None,
                )
            )
            continue

        result = run_vector(
            key=KEY,
            nonce=NONCE,
            associated_data=_pattern(case.ad_len, seed=0x20),
            plaintext=_pattern(case.text_len, seed=0x80),
            repo_root=REPO_ROOT,
            dry_run=False,
        )
        rtl = result.rtl
        rows.append(
            SweepRow(
                label=case.label,
                ad_len=case.ad_len,
                text_len=case.text_len,
                ad_beats=_beats(case.ad_len),
                text_beats=_beats(case.text_len),
                matched=bool(result.matched),
                cycles=None if rtl is None else rtl.cycles,
                out_bytes=None if rtl is None else rtl.dma_out_bytes,
                error_code=None if rtl is None else rtl.error_code,
            )
        )
    return rows


def _print_table(rows: list[SweepRow], *, dry_run: bool) -> None:
    header = f"{'case':<14}{'AD':>5}{'PT':>7}{'beats':>7}{'cycles':>9}{'cy/beat':>9}  {'match':>6}"
    print(header)
    print("-" * len(header))
    for r in rows:
        total_beats = r.ad_beats + r.text_beats
        if dry_run or r.cycles is None:
            cyc = "-"
            per = "-"
            match = "(dry)" if dry_run else "n/a"
        else:
            cyc = str(r.cycles)
            per = f"{r.cycles / total_beats:.1f}" if total_beats else "-"
            match = "ok" if r.matched else "FAIL"
        print(
            f"{r.label:<14}{r.ad_len:>5}{r.text_len:>7}{total_beats:>7}{cyc:>9}{per:>9}  {match:>6}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the payload set without invoking the simulator",
    )
    args = parser.parse_args()

    if not args.dry_run and (shutil.which("iverilog") is None or shutil.which("vvp") is None):
        print("iverilog and vvp are required unless --dry-run is used", file=sys.stderr)
        return 2

    rows = run_sweep(dry_run=args.dry_run)

    if args.json:
        print(json.dumps([row.__dict__ for row in rows], indent=2))
    else:
        _print_table(rows, dry_run=args.dry_run)

    if args.dry_run:
        return 0

    all_ok = all(r.matched for r in rows)
    if not all_ok:
        print("\nSWEEP FAILED: at least one case did not match the golden model", file=sys.stderr)
        return 1
    print(f"\nSWEEP PASS: {len(rows)}/{len(rows)} cases matched the golden model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
