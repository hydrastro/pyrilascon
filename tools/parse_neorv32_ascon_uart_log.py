#!/usr/bin/env python3
"""Parse NEORV32 ASCON benchmark UART logs into machine-readable reports."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CYCLE_RE = re.compile(r"^(?P<label>SW cycles|ENC hw cycles|DEC hw cycles)\s*:\s*(?P<hi>[0-9a-fA-Fx]+):(?P<lo>[0-9a-fA-Fx]+)\s*$")
KEY_VALUE_RE = re.compile(r"^(?P<key>[^:]+?)\s*:\s*(?P<value>.*)$")
HEX_RE = re.compile(r"^[0-9a-fA-F]*$")


class UartBenchmarkParseError(ValueError):
    """Raised when a UART benchmark log is malformed or incomplete."""


@dataclass(frozen=True)
class ParsedLine:
    key: str
    value: str


def _parse_int(value: str) -> int:
    value = value.strip()
    if value.lower().startswith("0x"):
        return int(value, 16)
    return int(value, 10)


def _parse_cycle_pair(value: str) -> int:
    hi_s, lo_s = value.split(":", 1)
    return (_parse_int(hi_s) << 32) | _parse_int(lo_s)


def _clean_key(key: str) -> str:
    return " ".join(key.strip().split())


def _collect_key_values(text: str) -> tuple[list[str], dict[str, str], list[str], list[str]]:
    lines = [line.rstrip() for line in text.splitlines()]
    pairs: dict[str, str] = {}
    warnings: list[str] = []
    failures: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("WARN:"):
            warnings.append(line)
            continue
        if line.startswith("FAIL:") or line.startswith("ERROR:"):
            failures.append(line)
            continue
        match = KEY_VALUE_RE.match(line)
        if match:
            pairs[_clean_key(match.group("key"))] = match.group("value").strip()
    return lines, pairs, warnings, failures


def _hex_field(pairs: dict[str, str], key: str, *, required: bool = True) -> str | None:
    value = pairs.get(key)
    if value is None:
        if required:
            raise UartBenchmarkParseError(f"missing UART field: {key}")
        return None
    compact = value.replace(" ", "").lower()
    if not HEX_RE.match(compact):
        raise UartBenchmarkParseError(f"field {key!r} is not hexadecimal: {value!r}")
    return compact


def _optional_int(pairs: dict[str, str], key: str) -> int | None:
    if key not in pairs:
        return None
    return _parse_int(pairs[key])


def _benchmark_block(pairs: dict[str, str], prefix: str) -> dict[str, Any]:
    cycles_key = f"{prefix} hw cycles"
    cycles = _parse_cycle_pair(pairs[cycles_key]) if cycles_key in pairs else None
    status = _optional_int(pairs, f"{prefix} status")
    mcy_per_byte = _optional_int(pairs, f"{prefix} hw mcy/byte")
    tag_valid = _optional_int(pairs, f"{prefix} tag valid")
    hw_err = _optional_int(pairs, f"{prefix} hw err")
    speedup_x1000 = _optional_int(pairs, f"{prefix} speedup x1000")
    return {
        "status": status,
        "cycles": cycles,
        "mcycles_per_byte": mcy_per_byte,
        "tag_valid": None if tag_valid is None else bool(tag_valid),
        "error_code": hw_err,
        "speedup_x1000": speedup_x1000,
        "speedup": None if speedup_x1000 is None else speedup_x1000 / 1000.0,
    }


def parse_uart_log(text: str, *, strict: bool = False) -> dict[str, Any]:
    """Parse a NEORV32 benchmark UART log.

    The parser accepts the exact labels printed by
    ``firmware/neorv32_ascon_benchmark/main.c`` and returns a stable report
    dictionary that can be serialized to JSON or Markdown.
    """
    lines, pairs, warnings, failures = _collect_key_values(text)
    joined = "\n".join(lines)
    saw_pass = any(line.strip() == "PASS" for line in lines)

    required = ["ABI", "CAPS", "SW CT", "SW TAG", "HW CT", "HW TAG", "HW PT", "SW cycles"]
    missing = [key for key in required if key not in pairs]
    if strict and missing:
        raise UartBenchmarkParseError("missing required UART fields: " + ", ".join(missing))

    sw_ct = _hex_field(pairs, "SW CT", required=strict)
    sw_tag = _hex_field(pairs, "SW TAG", required=strict)
    hw_ct = _hex_field(pairs, "HW CT", required=strict)
    hw_tag = _hex_field(pairs, "HW TAG", required=strict)
    hw_pt = _hex_field(pairs, "HW PT", required=strict)

    sw_cycles = _parse_cycle_pair(pairs["SW cycles"]) if "SW cycles" in pairs else None
    enc = _benchmark_block(pairs, "ENC")
    dec = _benchmark_block(pairs, "DEC")

    encryption_matches = None if sw_ct is None or hw_ct is None or sw_tag is None or hw_tag is None else (sw_ct == hw_ct and sw_tag == hw_tag)
    hardware_beats = {
        "tx": _optional_int(pairs, "AXIS TX beats"),
        "rx": _optional_int(pairs, "AXIS RX beats"),
        "status": _optional_int(pairs, "AXIS status"),
    }

    report: dict[str, Any] = {
        "schema_version": 1,
        "headline": "pass" if saw_pass and not failures else "fail",
        "data_plane": pairs.get("DATA PLANE"),
        "axis_base": pairs.get("AXIS BASE"),
        "abi": pairs.get("ABI"),
        "caps": pairs.get("CAPS"),
        "software": {
            "ciphertext_hex": sw_ct,
            "tag_hex": sw_tag,
            "cycles": sw_cycles,
        },
        "hardware": {
            "ciphertext_hex": hw_ct,
            "tag_hex": hw_tag,
            "plaintext_hex": hw_pt,
            "encryption": enc,
            "decryption": dec,
            "axis_mmio": hardware_beats,
        },
        "checks": {
            "saw_pass": saw_pass,
            "encryption_matches_reference": encryption_matches,
            "encrypt_status_ok": enc["status"] == 0 if enc["status"] is not None else None,
            "decrypt_status_ok": dec["status"] == 0 if dec["status"] is not None else None,
            "axis_status_ok": hardware_beats["status"] == 0 if hardware_beats["status"] is not None else None,
            "hardware_encrypt_beats_software": (enc["cycles"] < sw_cycles) if enc["cycles"] is not None and sw_cycles is not None else None,
            "hardware_decrypt_beats_software": (dec["cycles"] < sw_cycles) if dec["cycles"] is not None and sw_cycles is not None else None,
        },
        "warnings": warnings,
        "failures": failures,
        "raw_line_count": len(lines),
    }

    if strict:
        failed_checks = [key for key, value in report["checks"].items() if value is False]
        if failed_checks or failures or not saw_pass:
            raise UartBenchmarkParseError("UART benchmark did not pass strict checks: " + ", ".join(failed_checks or failures or ["missing PASS"]))
    return report


def render_markdown(report: dict[str, Any]) -> str:
    """Render a concise benchmark report as Markdown."""
    enc = report["hardware"]["encryption"]
    dec = report["hardware"]["decryption"]
    axis = report["hardware"]["axis_mmio"]
    checks = report["checks"]
    rows = [
        ("Result", report["headline"]),
        ("Data plane", report.get("data_plane") or "unknown"),
        ("ABI", report.get("abi") or "unknown"),
        ("CAPS", report.get("caps") or "unknown"),
        ("SW cycles", report["software"].get("cycles")),
        ("ENC HW cycles", enc.get("cycles")),
        ("DEC HW cycles", dec.get("cycles")),
        ("ENC speedup", enc.get("speedup")),
        ("DEC speedup", dec.get("speedup")),
        ("AXIS TX beats", axis.get("tx")),
        ("AXIS RX beats", axis.get("rx")),
    ]
    lines = ["# NEORV32 ASCON benchmark report", "", "| Field | Value |", "|---|---|"]
    for key, value in rows:
        lines.append(f"| {key} | {value if value is not None else 'n/a'} |")
    lines.extend(["", "## Checks", "", "| Check | Value |", "|---|---|"])
    for key, value in checks.items():
        lines.append(f"| `{key}` | {value} |")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    return "\n".join(lines)


def _read_input(path: Path | None) -> str:
    if path is None or str(path) == "-":
        return sys.stdin.read()
    if not path.exists():
        raise UartBenchmarkParseError(f"UART log file does not exist: {path}")
    if not path.is_file():
        raise UartBenchmarkParseError(f"UART log path is not a file: {path}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", nargs="?", type=Path, help="UART log path; omit or use '-' for stdin")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown", action="store_true", help="print Markdown report")
    parser.add_argument("--out", type=Path, help="write report to this path instead of stdout")
    parser.add_argument("--strict", action="store_true", help="fail if PASS or required correctness checks are missing")
    args = parser.parse_args()

    try:
        report = parse_uart_log(_read_input(args.log), strict=args.strict)
    except UartBenchmarkParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.markdown:
        rendered = render_markdown(report)
    else:
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
