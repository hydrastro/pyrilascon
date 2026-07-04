"""Host-side companion to the on-chip NEORV32 ASCON benchmark.

The board runs the same C reference (software) and the hardware accelerator on
one fabric and emits one machine-parsable line per payload:

    CASE name=<n> ad=<a> pt=<p> sw_enc_cy=<H>:<L> sw_dec_cy=<H>:<L>
         hw_enc_cy=<H>:<L> hw_dec_cy=<H>:<L>
         enc_ok=<0|1> dec_ok=<0|1> tag_valid=<0|1>
         hw_enc_err=0x<x> hw_dec_err=0x<x>

This tool has two roles:

    capture : read that UART stream from a serial port into a log file
    report  : parse a log and print the SW-vs-HW comparison, checking the
              headline criterion (hardware cycles < software cycles, on the
              same fabric and clock)

`report` needs no hardware and is exercised by the test suite; `capture` needs a
flashed board and pyserial (imported lazily).
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass


def _int(s: str) -> int:
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def _cycles(pair: str) -> int:
    hi, lo = pair.split(":", 1)
    return (_int(hi) << 32) | _int(lo)


@dataclass(frozen=True)
class Case:
    name: str
    ad: int
    pt: int
    sw_enc: int
    sw_dec: int
    hw_enc: int
    hw_dec: int
    enc_ok: bool
    dec_ok: bool
    tag_valid: bool
    hw_enc_err: int
    hw_dec_err: int

    @property
    def enc_speedup(self) -> float:
        return (self.sw_enc / self.hw_enc) if self.hw_enc else float("inf")

    @property
    def dec_speedup(self) -> float:
        return (self.sw_dec / self.hw_dec) if self.hw_dec else float("inf")

    @property
    def correct(self) -> bool:
        return self.enc_ok and self.dec_ok and self.tag_valid

    @property
    def hw_faster(self) -> bool:
        return self.hw_enc < self.sw_enc and self.hw_dec < self.sw_dec


_FIELD = re.compile(r"(\w+)=(\S+)")


def parse_case(line: str) -> Case | None:
    """Parse one CASE line into a Case, or None if it is not a data case."""
    line = line.strip()
    if not line.startswith("CASE ") or "SKIP" in line or "SW_ERR" in line:
        return None
    fields = dict(_FIELD.findall(line[len("CASE ") :]))
    try:
        return Case(
            name=fields["name"],
            ad=int(fields["ad"]),
            pt=int(fields["pt"]),
            sw_enc=_cycles(fields["sw_enc_cy"]),
            sw_dec=_cycles(fields["sw_dec_cy"]),
            hw_enc=_cycles(fields["hw_enc_cy"]),
            hw_dec=_cycles(fields["hw_dec_cy"]),
            enc_ok=fields["enc_ok"] == "1",
            dec_ok=fields["dec_ok"] == "1",
            tag_valid=fields["tag_valid"] == "1",
            hw_enc_err=_int(fields["hw_enc_err"]),
            hw_dec_err=_int(fields["hw_dec_err"]),
        )
    except KeyError:
        return None


def parse_log(text: str) -> list[Case]:
    return [c for c in (parse_case(line) for line in text.splitlines()) if c is not None]


@dataclass(frozen=True)
class Report:
    cases: list[Case]

    @property
    def all_correct(self) -> bool:
        return all(c.correct for c in self.cases)

    @property
    def all_hw_faster(self) -> bool:
        return all(c.hw_faster for c in self.cases)

    @property
    def passed(self) -> bool:
        # The headline claim: on the same fabric, the accelerator is both
        # correct and faster (fewer cycles) than the CPU reference.
        return bool(self.cases) and self.all_correct and self.all_hw_faster


def format_report(cases: list[Case]) -> str:
    if not cases:
        return "no benchmark cases found in log"
    rows = [
        f"{'case':<12} {'ad':>4} {'pt':>4} {'sw_enc':>10} {'hw_enc':>10} "
        f"{'enc x':>7} {'sw_dec':>10} {'hw_dec':>10} {'dec x':>7} {'ok':>3}",
        "-" * 88,
    ]
    for c in cases:
        rows.append(
            f"{c.name:<12} {c.ad:>4} {c.pt:>4} {c.sw_enc:>10} {c.hw_enc:>10} "
            f"{c.enc_speedup:>6.2f}x {c.sw_dec:>10} {c.hw_dec:>10} {c.dec_speedup:>6.2f}x "
            f"{'Y' if c.correct else 'N':>3}"
        )
    rep = Report(cases)
    rows.append("-" * 88)
    rows.append(
        f"{len(cases)} cases | all correct: {rep.all_correct} | "
        f"accelerator faster on every case: {rep.all_hw_faster} | "
        f"HEADLINE {'PASS' if rep.passed else 'FAIL'}"
    )
    return "\n".join(rows)


def capture_serial(port: str, baud: int, timeout: float) -> str:
    """Read UART lines until the board prints its terminal PASS/FAIL. Lazily
    imports pyserial so the rest of the tool works without it."""
    try:
        import serial  # type: ignore
    except ImportError:  # pragma: no cover - needs hardware anyway
        raise SystemExit("pyserial is required for capture (pip install pyserial)")
    lines: list[str] = []
    with serial.Serial(port, baud, timeout=timeout) as ser:  # pragma: no cover
        while True:
            raw = ser.readline()
            if not raw:
                break
            line = raw.decode("ascii", errors="replace").rstrip("\r\n")
            print(line)
            lines.append(line)
            if line.strip() in ("PASS", "FAIL"):
                break
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ascon_bench")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rp = sub.add_parser("report", help="parse a UART log and print SW-vs-HW comparison")
    rp.add_argument("log", nargs="?", default="-", help="log file, or - for stdin")

    cp = sub.add_parser("capture", help="capture the board's UART benchmark output")
    cp.add_argument("--port", required=True)
    cp.add_argument("--baud", type=int, default=19200)
    cp.add_argument("--timeout", type=float, default=10.0)
    cp.add_argument("--out", help="write the captured log here (also parsed)")

    args = ap.parse_args(argv)

    if args.cmd == "report":
        text = sys.stdin.read() if args.log == "-" else open(args.log).read()
        cases = parse_log(text)
        print(format_report(cases))
        return 0 if Report(cases).passed else 1

    if args.cmd == "capture":
        text = capture_serial(args.port, args.baud, args.timeout)
        if args.out:
            with open(args.out, "w") as fh:
                fh.write(text)
        cases = parse_log(text)
        print()
        print(format_report(cases))
        return 0 if Report(cases).passed else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
