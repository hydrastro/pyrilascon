#!/usr/bin/env python3
"""Parse the NEORV32 ASCON multi-case UART benchmark log.

The canonical board firmware emits one ``CASE`` line per payload shape, one
``AUTH_NEGATIVE`` line for corrupted-tag rejection, a ``SUMMARY`` line, and a
final standalone ``PASS`` or ``FAIL``. The parser distinguishes:

* end-to-end accelerator cycles: CPU-visible driver/MMIO latency;
* core cycles: accelerator-internal busy time.

Use end-to-end speedup for practical performance claims. Core-only speedup is a
datapath diagnostic and intentionally excludes software/MMIO overhead.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

CASE_RE = re.compile(
    r"^CASE\s+name=(?P<name>\S+)\s+"
    r"ad=(?P<ad>\d+)\s+pt=(?P<pt>\d+)\s+"
    r"sw_enc_cy=(?P<sw_enc_hi>\d+):(?P<sw_enc_lo>\d+)\s+"
    r"sw_dec_cy=(?P<sw_dec_hi>\d+):(?P<sw_dec_lo>\d+)\s+"
    r"hw_enc_cy=(?P<hw_enc_hi>\d+):(?P<hw_enc_lo>\d+)\s+"
    r"hw_dec_cy=(?P<hw_dec_hi>\d+):(?P<hw_dec_lo>\d+)\s+"
    r"(?:hw_enc_e2e_cy=(?P<hw_enc_e2e_hi>\d+):(?P<hw_enc_e2e_lo>\d+)\s+"
    r"hw_dec_e2e_cy=(?P<hw_dec_e2e_hi>\d+):(?P<hw_dec_e2e_lo>\d+)\s+)?"
    r"enc_ok=(?P<enc_ok>[01])\s+dec_ok=(?P<dec_ok>[01])\s+"
    r"tag_valid=(?P<tag_valid>[01])\s+"
    r"hw_enc_err=0x(?P<hw_enc_err>[0-9a-fA-F]+)\s+"
    r"hw_dec_err=0x(?P<hw_dec_err>[0-9a-fA-F]+)\s*$"
)
BUILD_RE = re.compile(r"^BUILD\s*:\s*(\S+)")
MAX_BYTES_RE = re.compile(r"^MAX_BYTES\s*:\s*(\d+)")
SWEEP_CASES_RE = re.compile(r"^SWEEP_CASES\s*:\s*(\d+)")
SUMMARY_RE = re.compile(
    r"^SUMMARY\s*:\s*passed=(\d+)\s+failed=(\d+)\s+total=(\d+)"
    r"(?:\s+negative_pass=([01]))?\s*$"
)
NEGATIVE_RE = re.compile(
    r"^AUTH_NEGATIVE\s+enc_status=(-?\d+)\s+dec_status=(-?\d+)\s+"
    r"tag_valid=([01])\s+hw_err=0x([0-9a-fA-F]+)\s+"
    r"output_unchanged=([01])\s+pass=([01])\s*$"
)
PASS_RE = re.compile(r"^PASS\s*$")
FAIL_RE = re.compile(r"^FAIL(?:\s|:|$)")


class SweepLogError(ValueError):
    """Raised when a strict benchmark log is incomplete or failed."""


@dataclass
class Case:
    name: str
    ad: int
    pt: int
    sw_enc_cy: int
    sw_dec_cy: int
    hw_enc_cy: int
    hw_dec_cy: int
    hw_enc_e2e_cy: int | None
    hw_dec_e2e_cy: int | None
    enc_ok: bool
    dec_ok: bool
    tag_valid: bool
    hw_enc_err: int
    hw_dec_err: int

    @staticmethod
    def _ratio(numerator: int, denominator: int | None) -> float | None:
        return numerator / denominator if denominator else None

    @property
    def enc_e2e_speedup(self) -> float | None:
        return self._ratio(self.sw_enc_cy, self.hw_enc_e2e_cy)

    @property
    def dec_e2e_speedup(self) -> float | None:
        return self._ratio(self.sw_dec_cy, self.hw_dec_e2e_cy)

    @property
    def enc_core_speedup(self) -> float | None:
        return self._ratio(self.sw_enc_cy, self.hw_enc_cy)

    @property
    def dec_core_speedup(self) -> float | None:
        return self._ratio(self.sw_dec_cy, self.hw_dec_cy)

    @property
    def ok(self) -> bool:
        return (
            self.enc_ok
            and self.dec_ok
            and self.tag_valid
            and self.hw_enc_err == 0
            and self.hw_dec_err == 0
        )


@dataclass
class NegativeCheck:
    enc_status: int
    dec_status: int
    tag_valid: bool
    hw_err: int
    output_unchanged: bool
    passed: bool


@dataclass
class Report:
    build: str | None
    max_bytes: int | None
    expected_cases: int | None
    cases: list[Case]
    negative: NegativeCheck | None
    summary_passed: int | None
    summary_failed: int | None
    summary_total: int | None
    summary_negative_pass: bool | None
    saw_pass: bool
    saw_fail: bool
    errors: list[str]

    @property
    def overall_pass(self) -> bool:
        return not self.errors


def _cycles(hi: str, lo: str) -> int:
    return (int(hi) << 32) | int(lo)


def _optional_cycles(match: re.Match[str], prefix: str) -> int | None:
    hi = match.group(f"{prefix}_hi")
    lo = match.group(f"{prefix}_lo")
    return None if hi is None or lo is None else _cycles(hi, lo)


def parse_log(text: str, *, strict: bool = False) -> Report:
    build: str | None = None
    max_bytes: int | None = None
    expected_cases: int | None = None
    cases: list[Case] = []
    negative: NegativeCheck | None = None
    summary_passed = summary_failed = summary_total = None
    summary_negative_pass: bool | None = None
    saw_pass = False
    saw_fail = False

    for raw in text.splitlines():
        # UART framing noise is commonly decoded as U+FFFD. Trim only edge noise
        # so valid payload text remains untouched.
        line = raw.strip().strip("\x00\ufffd").strip()
        if not line:
            continue
        if match := BUILD_RE.match(line):
            build = match.group(1)
        elif match := MAX_BYTES_RE.match(line):
            max_bytes = int(match.group(1))
        elif match := SWEEP_CASES_RE.match(line):
            expected_cases = int(match.group(1))
        elif match := CASE_RE.match(line):
            cases.append(
                Case(
                    name=match.group("name"),
                    ad=int(match.group("ad")),
                    pt=int(match.group("pt")),
                    sw_enc_cy=_cycles(match.group("sw_enc_hi"), match.group("sw_enc_lo")),
                    sw_dec_cy=_cycles(match.group("sw_dec_hi"), match.group("sw_dec_lo")),
                    hw_enc_cy=_cycles(match.group("hw_enc_hi"), match.group("hw_enc_lo")),
                    hw_dec_cy=_cycles(match.group("hw_dec_hi"), match.group("hw_dec_lo")),
                    hw_enc_e2e_cy=_optional_cycles(match, "hw_enc_e2e"),
                    hw_dec_e2e_cy=_optional_cycles(match, "hw_dec_e2e"),
                    enc_ok=match.group("enc_ok") == "1",
                    dec_ok=match.group("dec_ok") == "1",
                    tag_valid=match.group("tag_valid") == "1",
                    hw_enc_err=int(match.group("hw_enc_err"), 16),
                    hw_dec_err=int(match.group("hw_dec_err"), 16),
                )
            )
        elif match := NEGATIVE_RE.match(line):
            negative = NegativeCheck(
                enc_status=int(match.group(1)),
                dec_status=int(match.group(2)),
                tag_valid=match.group(3) == "1",
                hw_err=int(match.group(4), 16),
                output_unchanged=match.group(5) == "1",
                passed=match.group(6) == "1",
            )
        elif match := SUMMARY_RE.match(line):
            summary_passed = int(match.group(1))
            summary_failed = int(match.group(2))
            summary_total = int(match.group(3))
            summary_negative_pass = None if match.group(4) is None else match.group(4) == "1"
        elif PASS_RE.match(line):
            saw_pass = True
        elif FAIL_RE.match(line):
            saw_fail = True

    errors: list[str] = []
    if not cases:
        errors.append("no CASE records were parsed")
    if expected_cases is not None and len(cases) != expected_cases:
        errors.append(f"expected {expected_cases} CASE records, parsed {len(cases)}")
    if summary_total is None:
        errors.append("missing SUMMARY record")
    else:
        if summary_total != len(cases):
            errors.append(f"SUMMARY total={summary_total}, parsed cases={len(cases)}")
        if summary_failed != 0:
            errors.append(f"firmware reported {summary_failed} failed case(s)")
        if summary_passed != summary_total:
            errors.append("SUMMARY passed count does not equal total")
    bad_cases = [case.name for case in cases if not case.ok]
    if bad_cases:
        errors.append("failed correctness cases: " + ", ".join(bad_cases))
    if any(case.hw_enc_e2e_cy is None or case.hw_dec_e2e_cy is None for case in cases):
        errors.append("log lacks end-to-end hardware cycle fields")
    if negative is None:
        errors.append("missing AUTH_NEGATIVE corrupted-tag check")
    elif not negative.passed:
        errors.append("corrupted-tag rejection check failed")
    if summary_negative_pass is False:
        errors.append("SUMMARY reports negative_pass=0")
    if saw_fail:
        errors.append("firmware emitted FAIL")
    if not saw_pass:
        errors.append("missing final PASS")

    report = Report(
        build=build,
        max_bytes=max_bytes,
        expected_cases=expected_cases,
        cases=cases,
        negative=negative,
        summary_passed=summary_passed,
        summary_failed=summary_failed,
        summary_total=summary_total,
        summary_negative_pass=summary_negative_pass,
        saw_pass=saw_pass,
        saw_fail=saw_fail,
        errors=errors,
    )
    if strict and errors:
        raise SweepLogError("; ".join(errors))
    return report


def _fmt_ratio(value: float | None) -> str:
    return "n/a" if value is None else f"{value:,.2f}×"


def _fmt_cycles(value: int | None) -> str:
    return "n/a" if value is None else f"{value:,}"


def _geomean(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None and value > 0.0]
    if not clean:
        return None
    return math.exp(sum(math.log(value) for value in clean) / len(clean))


def render_markdown(report: Report, *, freq_mhz: float = 27.0) -> str:
    lines = [
        "# Tang Nano 20K NEORV32 ASCON benchmark",
        "",
        f"- Build: `{report.build or 'unknown'}`",
        f"- CPU/accelerator clock: {freq_mhz:g} MHz",
        f"- Payload limit: {report.max_bytes if report.max_bytes is not None else 'unknown'} bytes",
        f"- Correctness: {'**PASS**' if report.overall_pass else '**FAIL**'}",
        "- Primary metric: end-to-end speedup = CPU software cycles / complete accelerator driver-call cycles.",
        "- Diagnostic metric: core-only speedup excludes MMIO, polling, and result-transfer overhead.",
        "",
    ]
    if report.errors:
        lines += ["## Validation errors", ""] + [f"- {error}" for error in report.errors] + [""]

    lines += [
        "## Per-case results",
        "",
        "| Case | AD B | PT B | SW enc cy | HW enc E2E cy | Enc E2E speedup | SW dec cy | HW dec E2E cy | Dec E2E speedup | HW enc core cy | HW dec core cy | Correct |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for case in report.cases:
        lines.append(
            f"| `{case.name}` | {case.ad} | {case.pt} | {case.sw_enc_cy:,} | "
            f"{_fmt_cycles(case.hw_enc_e2e_cy)} | {_fmt_ratio(case.enc_e2e_speedup)} | "
            f"{case.sw_dec_cy:,} | {_fmt_cycles(case.hw_dec_e2e_cy)} | "
            f"{_fmt_ratio(case.dec_e2e_speedup)} | {case.hw_enc_cy:,} | "
            f"{case.hw_dec_cy:,} | {'yes' if case.ok else 'no'} |"
        )

    enc_mean = _geomean([case.enc_e2e_speedup for case in report.cases])
    dec_mean = _geomean([case.dec_e2e_speedup for case in report.cases])
    lines += [
        "",
        "## Aggregate",
        "",
        f"- Encryption end-to-end geometric-mean speedup: **{_fmt_ratio(enc_mean)}**",
        f"- Decryption end-to-end geometric-mean speedup: **{_fmt_ratio(dec_mean)}**",
        f"- Corrupted-tag rejection: **{'PASS' if report.negative and report.negative.passed else 'FAIL'}**",
        "",
    ]
    return "\n".join(lines)


def _case_dict(case: Case, freq_mhz: float) -> dict[str, object]:
    data: dict[str, object] = asdict(case)
    data.update(
        enc_e2e_speedup=case.enc_e2e_speedup,
        dec_e2e_speedup=case.dec_e2e_speedup,
        enc_core_speedup=case.enc_core_speedup,
        dec_core_speedup=case.dec_core_speedup,
        sw_enc_us=case.sw_enc_cy / freq_mhz,
        sw_dec_us=case.sw_dec_cy / freq_mhz,
        hw_enc_e2e_us=None if case.hw_enc_e2e_cy is None else case.hw_enc_e2e_cy / freq_mhz,
        hw_dec_e2e_us=None if case.hw_dec_e2e_cy is None else case.hw_dec_e2e_cy / freq_mhz,
        ok=case.ok,
    )
    return data


def render_json(report: Report, *, freq_mhz: float = 27.0) -> str:
    data = asdict(report)
    data["overall_pass"] = report.overall_pass
    data["frequency_mhz"] = freq_mhz
    data["cases"] = [_case_dict(case, freq_mhz) for case in report.cases]
    data["aggregate"] = {
        "enc_e2e_geomean_speedup": _geomean([case.enc_e2e_speedup for case in report.cases]),
        "dec_e2e_geomean_speedup": _geomean([case.dec_e2e_speedup for case in report.cases]),
    }
    return json.dumps(data, indent=2)


def render_csv(report: Report, *, freq_mhz: float = 27.0) -> str:
    output = io.StringIO()
    fields = [
        "name", "ad", "pt", "sw_enc_cy", "hw_enc_e2e_cy", "enc_e2e_speedup",
        "sw_dec_cy", "hw_dec_e2e_cy", "dec_e2e_speedup", "hw_enc_cy",
        "hw_dec_cy", "enc_core_speedup", "dec_core_speedup", "ok",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for case in report.cases:
        values = _case_dict(case, freq_mhz)
        writer.writerow({field: values[field] for field in fields})
    return output.getvalue().rstrip("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="captured UART log")
    formats = parser.add_mutually_exclusive_group()
    formats.add_argument("--json", action="store_true")
    formats.add_argument("--csv", action="store_true")
    formats.add_argument("--markdown", action="store_true")
    parser.add_argument("--strict", action="store_true", help="reject incomplete or failed logs")
    parser.add_argument("--freq-mhz", type=float, default=27.0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    if not args.log.is_file():
        print(f"error: UART log file does not exist: {args.log}", file=sys.stderr)
        return 2
    text = args.log.read_bytes().decode("utf-8", errors="replace")
    try:
        report = parse_log(text, strict=args.strict)
    except SweepLogError as exc:
        print(f"error: invalid benchmark log: {exc}", file=sys.stderr)
        return 1

    if args.json:
        rendered = render_json(report, freq_mhz=args.freq_mhz)
    elif args.csv:
        rendered = render_csv(report, freq_mhz=args.freq_mhz)
    else:
        rendered = render_markdown(report, freq_mhz=args.freq_mhz)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(rendered)
    return 0 if report.overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
