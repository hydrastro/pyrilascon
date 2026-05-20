#!/usr/bin/env python3
"""Parse NEORV32 ASCON benchmark sweep logs into a structured report.

The sweep firmware (`firmware/neorv32_ascon_benchmark/main.c`) emits one
machine-parsable line per payload-size case:

    CASE name=<n> ad=<a> pt=<p>
         sw_enc_cy=<H>:<L> sw_dec_cy=<H>:<L>
         hw_enc_cy=<H>:<L> hw_dec_cy=<H>:<L>
         enc_ok=<0|1> dec_ok=<0|1> tag_valid=<0|1>
         hw_enc_err=0x<x> hw_dec_err=0x<x>

This tool collects those lines from a UART log, produces a JSON / Markdown
report, and computes per-case HW/SW speed-ups for the FINAL_REPORT's
performance-comparison section.

Designed to be robust to:
  * UART boot-time line noise (non-UTF-8 bytes before the first banner);
  * lines that don't match the CASE schema (e.g. WITNESS, BUILD banner);
  * out-of-order or truncated output.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

CASE_RE = re.compile(
    r"^CASE\s+name=(?P<name>\S+)\s+"
    r"ad=(?P<ad>\d+)\s+"
    r"pt=(?P<pt>\d+)\s+"
    r"sw_enc_cy=(?P<sw_enc_hi>\d+):(?P<sw_enc_lo>\d+)\s+"
    r"sw_dec_cy=(?P<sw_dec_hi>\d+):(?P<sw_dec_lo>\d+)\s+"
    r"hw_enc_cy=(?P<hw_enc_hi>\d+):(?P<hw_enc_lo>\d+)\s+"
    r"hw_dec_cy=(?P<hw_dec_hi>\d+):(?P<hw_dec_lo>\d+)\s+"
    r"enc_ok=(?P<enc_ok>\d+)\s+"
    r"dec_ok=(?P<dec_ok>\d+)\s+"
    r"tag_valid=(?P<tag_valid>\d+)\s+"
    r"hw_enc_err=0x(?P<hw_enc_err>[0-9a-fA-F]+)\s+"
    r"hw_dec_err=0x(?P<hw_dec_err>[0-9a-fA-F]+)\s*$"
)

BUILD_RE   = re.compile(r"^BUILD\s*:\s*(\S+)")
MAXBYTES_RE = re.compile(r"^MAX_BYTES\s*:\s*(\d+)")
SUMMARY_RE = re.compile(r"^SUMMARY\s*:\s*passed=(\d+)\s+failed=(\d+)\s+total=(\d+)")
PASS_RE    = re.compile(r"^PASS\s*$")
FAIL_RE    = re.compile(r"^FAIL")


@dataclass
class Case:
    name: str
    ad: int
    pt: int
    sw_enc_cy: int
    sw_dec_cy: int
    hw_enc_cy: int
    hw_dec_cy: int
    enc_ok: bool
    dec_ok: bool
    tag_valid: bool
    hw_enc_err: int
    hw_dec_err: int

    @property
    def enc_speedup(self) -> float:
        return self.sw_enc_cy / self.hw_enc_cy if self.hw_enc_cy else 0.0

    @property
    def dec_speedup(self) -> float:
        return self.sw_dec_cy / self.hw_dec_cy if self.hw_dec_cy else 0.0


@dataclass
class Report:
    build: str | None
    max_bytes: int | None
    cases: list[Case]
    summary_passed: int | None
    summary_failed: int | None
    summary_total: int | None
    overall_pass: bool


def _cy(hi: str, lo: str) -> int:
    return (int(hi) << 32) | int(lo)


def parse_log(text: str) -> Report:
    build = None
    max_bytes = None
    cases: list[Case] = []
    s_passed = s_failed = s_total = None
    overall_pass = False
    overall_fail = False

    for raw in text.splitlines():
        line = raw.strip()
        if (m := BUILD_RE.match(line)):
            build = m.group(1)
            continue
        if (m := MAXBYTES_RE.match(line)):
            max_bytes = int(m.group(1))
            continue
        if (m := SUMMARY_RE.match(line)):
            s_passed = int(m.group(1))
            s_failed = int(m.group(2))
            s_total  = int(m.group(3))
            continue
        if PASS_RE.match(line):
            overall_pass = True
            continue
        if FAIL_RE.match(line):
            overall_fail = True
            continue
        if (m := CASE_RE.match(line)):
            cases.append(Case(
                name=m.group("name"),
                ad=int(m.group("ad")),
                pt=int(m.group("pt")),
                sw_enc_cy=_cy(m.group("sw_enc_hi"), m.group("sw_enc_lo")),
                sw_dec_cy=_cy(m.group("sw_dec_hi"), m.group("sw_dec_lo")),
                hw_enc_cy=_cy(m.group("hw_enc_hi"), m.group("hw_enc_lo")),
                hw_dec_cy=_cy(m.group("hw_dec_hi"), m.group("hw_dec_lo")),
                enc_ok=bool(int(m.group("enc_ok"))),
                dec_ok=bool(int(m.group("dec_ok"))),
                tag_valid=bool(int(m.group("tag_valid"))),
                hw_enc_err=int(m.group("hw_enc_err"), 16),
                hw_dec_err=int(m.group("hw_dec_err"), 16),
            ))

    return Report(
        build=build,
        max_bytes=max_bytes,
        cases=cases,
        summary_passed=s_passed,
        summary_failed=s_failed,
        summary_total=s_total,
        overall_pass=overall_pass and not overall_fail,
    )


def render_markdown(report: Report) -> str:
    lines: list[str] = []
    lines.append(f"# NEORV32 ASCON sweep report")
    lines.append("")
    lines.append(f"- Build:       `{report.build}`")
    lines.append(f"- Max bytes:   {report.max_bytes}")
    if report.summary_total is not None:
        lines.append(f"- Summary:     passed={report.summary_passed}, failed={report.summary_failed}, total={report.summary_total}")
    lines.append(f"- Overall:     {'**PASS**' if report.overall_pass else '**FAIL**'}")
    lines.append("")
    lines.append("## Per-payload sweep")
    lines.append("")
    lines.append("| Case | AD | PT | SW enc cy | SW dec cy | HW enc cy | HW dec cy | enc×  | dec×  | OK |")
    lines.append("|------|---:|---:|----------:|----------:|----------:|----------:|------:|------:|:--:|")
    for c in report.cases:
        ok_mark = "✓" if (c.enc_ok and c.dec_ok and c.tag_valid) else "✗"
        lines.append(
            f"| `{c.name}` | {c.ad} | {c.pt} | "
            f"{c.sw_enc_cy:,} | {c.sw_dec_cy:,} | "
            f"{c.hw_enc_cy:,} | {c.hw_dec_cy:,} | "
            f"{c.enc_speedup:,.0f}× | {c.dec_speedup:,.0f}× | {ok_mark} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_json(report: Report) -> str:
    data = asdict(report)
    # add computed columns
    for raw_case, c in zip(data["cases"], report.cases):
        raw_case["enc_speedup"] = c.enc_speedup
        raw_case["dec_speedup"] = c.dec_speedup
    return json.dumps(data, indent=2)


def render_latex_rows(report: Report) -> str:
    """Render the per-case rows in a form ready to paste into the FINAL_REPORT
    LaTeX performance-comparison table."""
    lines: list[str] = []
    for c in report.cases:
        lines.append(
            f"\\texttt{{{c.name}}} & {c.ad} & {c.pt} & "
            f"{c.sw_enc_cy:,} & {c.hw_enc_cy:,} & {c.enc_speedup:,.0f}$\\times$ & "
            f"{c.sw_dec_cy:,} & {c.hw_dec_cy:,} & {c.dec_speedup:,.0f}$\\times$ \\\\"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("log", nargs="?", type=Path, help="UART log path; '-' for stdin")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--json",     action="store_true", help="output JSON")
    g.add_argument("--markdown", action="store_true", help="output Markdown (default)")
    g.add_argument("--latex",    action="store_true", help="output the LaTeX table rows for FINAL_REPORT")
    p.add_argument("--out", type=Path, help="write to file instead of stdout")
    args = p.parse_args(argv)

    if args.log is None or str(args.log) == "-":
        text = sys.stdin.read()
    else:
        # Decode with errors='replace' to survive UART boot-time line noise.
        text = args.log.read_bytes().decode("utf-8", errors="replace")

    report = parse_log(text)

    if args.json:
        out = render_json(report)
    elif args.latex:
        out = render_latex_rows(report)
    else:
        out = render_markdown(report)

    if args.out:
        args.out.write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 0 if report.overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
