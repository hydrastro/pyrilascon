#!/usr/bin/env python3
"""Summarize a pyrilascon NEORV32 ASCON benchmark UART log.

The firmware (firmware/neorv32_ascon_benchmark/main.c) prints one machine-parsable
line per sweep case:

    CASE name=<n> ad=<a> pt=<p> sw_enc_cy=<hi>:<lo> sw_dec_cy=<hi>:<lo> \
         hw_enc_cy=<hi>:<lo> hw_dec_cy=<hi>:<lo> enc_ok=<b> dec_ok=<b> \
         tag_valid=<b> hw_enc_err=0x<e> hw_dec_err=0x<e>

This tool reads those lines and emits a per-size comparison of the software
reference (running on the NEORV32 core) against the hardware CFS accelerator,
with the speedup and, at the given core clock, the throughput. Correctness is a
gate: a case whose enc_ok/dec_ok/tag_valid is not 1 is reported but flagged, and
its timing is not to be trusted (a fast-but-wrong result is meaningless).

Usage:
    python tools/summarize_ascon_benchmark.py LOG [--freq-mhz 27] \
        [--markdown | --csv] [--out FILE]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CASE_RE = re.compile(
    r"CASE\s+name=(?P<name>\S+)\s+ad=(?P<ad>\d+)\s+pt=(?P<pt>\d+)\s+"
    r"sw_enc_cy=(?P<swe_hi>\d+):(?P<swe_lo>\d+)\s+"
    r"sw_dec_cy=(?P<swd_hi>\d+):(?P<swd_lo>\d+)\s+"
    r"hw_enc_cy=(?P<hwe_hi>\d+):(?P<hwe_lo>\d+)\s+"
    r"hw_dec_cy=(?P<hwd_hi>\d+):(?P<hwd_lo>\d+)\s+"
    r"enc_ok=(?P<enc_ok>\d+)\s+dec_ok=(?P<dec_ok>\d+)\s+tag_valid=(?P<tag_valid>\d+)"
)


def _u64(hi: str, lo: str) -> int:
    return (int(hi) << 32) | int(lo)


def parse_cases(text: str) -> list[dict]:
    cases = []
    for m in CASE_RE.finditer(text):
        g = m.groupdict()
        sw_enc = _u64(g["swe_hi"], g["swe_lo"])
        sw_dec = _u64(g["swd_hi"], g["swd_lo"])
        hw_enc = _u64(g["hwe_hi"], g["hwe_lo"])
        hw_dec = _u64(g["hwd_hi"], g["hwd_lo"])
        correct = g["enc_ok"] == "1" and g["dec_ok"] == "1" and g["tag_valid"] == "1"
        cases.append(
            {
                "name": g["name"], "ad": int(g["ad"]), "pt": int(g["pt"]),
                "sw_enc": sw_enc, "sw_dec": sw_dec, "hw_enc": hw_enc, "hw_dec": hw_dec,
                "enc_speedup": (sw_enc / hw_enc) if hw_enc else None,
                "dec_speedup": (sw_dec / hw_dec) if hw_dec else None,
                "correct": correct,
            }
        )
    return cases


def _banner(text: str) -> dict:
    out = {}
    for key in ("BUILD", "MAX_BYTES", "SWEEP_CASES", "DATA PLANE"):
        m = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", text, re.M)
        if m:
            out[key] = m.group(1).strip()
    return out


def _thru_mbps(nbytes: int, cycles: int, freq_hz: float) -> float | None:
    if not cycles or nbytes == 0:
        return None
    return nbytes * freq_hz / cycles / 1e6


def render_markdown(cases: list[dict], banner: dict, freq_hz: float) -> str:
    lines = ["# NEORV32 ASCON — software vs hardware accelerator", ""]
    if banner:
        lines += [f"- {k}: {v}" for k, v in banner.items()]
    lines.append(f"- Core clock: {freq_hz/1e6:.0f} MHz (1 cycle = {1e9/freq_hz:.2f} ns)")
    lines += [
        "",
        "| Case | AD | PT | SW enc | HW enc | Enc ↑ | SW dec | HW dec | Dec ↑ | Enc MB/s (HW) | Correct |",
        "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|",
    ]
    enc_ups, dec_ups = [], []
    for c in cases:
        if c["enc_speedup"]:
            enc_ups.append(c["enc_speedup"])
        if c["dec_speedup"]:
            dec_ups.append(c["dec_speedup"])
        thr = _thru_mbps(c["pt"], c["hw_enc"], freq_hz)
        lines.append(
            "| {name} | {ad} | {pt} | {sw_enc} | {hw_enc} | {es} | "
            "{sw_dec} | {hw_dec} | {ds} | {thr} | {ok} |".format(
                name=c["name"], ad=c["ad"], pt=c["pt"],
                sw_enc=c["sw_enc"], hw_enc=c["hw_enc"],
                es=f"{c['enc_speedup']:.1f}×" if c["enc_speedup"] else "n/a",
                sw_dec=c["sw_dec"], hw_dec=c["hw_dec"],
                ds=f"{c['dec_speedup']:.1f}×" if c["dec_speedup"] else "n/a",
                thr=f"{thr:.2f}" if thr is not None else "—",
                ok="yes" if c["correct"] else "**NO**",
            )
        )
    lines.append("")
    if enc_ups:
        lines.append(
            f"Encrypt speedup: {min(enc_ups):.1f}×–{max(enc_ups):.1f}× "
            f"(mean {sum(enc_ups)/len(enc_ups):.1f}×)."
        )
    if dec_ups:
        lines.append(
            f"Decrypt speedup: {min(dec_ups):.1f}×–{max(dec_ups):.1f}× "
            f"(mean {sum(dec_ups)/len(dec_ups):.1f}×)."
        )
    bad = [c["name"] for c in cases if not c["correct"]]
    if bad:
        lines.append("")
        lines.append(f"⚠ Correctness failed for: {', '.join(bad)} — timing not trustworthy.")
    return "\n".join(lines) + "\n"


def render_csv(cases: list[dict], freq_hz: float) -> str:
    rows = ["case,ad,pt,sw_enc,hw_enc,enc_speedup,sw_dec,hw_dec,dec_speedup,enc_mbps,correct"]
    for c in cases:
        thr = _thru_mbps(c["pt"], c["hw_enc"], freq_hz)
        rows.append(
            "{name},{ad},{pt},{sw_enc},{hw_enc},{es},{sw_dec},{hw_dec},{ds},{thr},{ok}".format(
                name=c["name"], ad=c["ad"], pt=c["pt"], sw_enc=c["sw_enc"], hw_enc=c["hw_enc"],
                es=f"{c['enc_speedup']:.4f}" if c["enc_speedup"] else "",
                sw_dec=c["sw_dec"], hw_dec=c["hw_dec"],
                ds=f"{c['dec_speedup']:.4f}" if c["dec_speedup"] else "",
                thr=f"{thr:.4f}" if thr is not None else "",
                ok=int(c["correct"]),
            )
        )
    return "\n".join(rows) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log", type=Path, help="UART capture log")
    ap.add_argument("--freq-mhz", type=float, default=27.0, help="core clock in MHz (default 27)")
    ap.add_argument("--csv", action="store_true", help="emit CSV instead of Markdown")
    ap.add_argument("--out", type=Path, help="write to file instead of stdout")
    args = ap.parse_args()

    text = args.log.read_text(errors="replace")
    cases = parse_cases(text)
    if not cases:
        print(
            "No CASE lines found. Check that: the board actually ran (LED heartbeat), "
            "the serial capture used the right port at 19200 baud, and Zicntr is enabled "
            "in the top (otherwise rdcycle traps and no case is printed).",
            file=sys.stderr,
        )
        return 1

    freq_hz = args.freq_mhz * 1e6
    rendered = render_csv(cases, freq_hz) if args.csv else render_markdown(cases, _banner(text), freq_hz)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
