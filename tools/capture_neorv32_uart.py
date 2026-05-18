#!/usr/bin/env python3
"""Capture NEORV32 benchmark UART output with portable serial auto-detection."""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

SERIAL_PATTERNS = [
    "/dev/serial/by-id/*",
    "/dev/ttyUSB*",
    "/dev/ttyACM*",
    "/dev/cu.usbserial*",
    "/dev/cu.usbmodem*",
]


def serial_candidates() -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()
    for pattern in SERIAL_PATTERNS:
        for name in glob.glob(pattern):
            path = Path(name)
            # Keep the human-stable /dev/serial/by-id symlink when available.
            key = str(path.resolve()) if path.exists() else str(path)
            if key not in seen:
                seen.add(key)
                found.append(path)
    return found


def _serial_score(path: Path) -> int:
    text = str(path)
    score = 0
    if "/dev/serial/by-id/" in text:
        score += 20
    upper = text.upper()
    if "SIPEED" in upper or "TANG" in upper or "GOWIN" in upper:
        score += 50
    # Sipeed debug adapters commonly expose if00 and if01.  Prefer if01 for
    # the UART bridge when both interfaces are present, but still require the
    # selected device to be readable/writable.
    if "-if01-" in text or "_if01" in text or "if01" in text:
        score += 5
    if "-if00-" in text or "_if00" in text or "if00" in text:
        score += 1
    return score


def _choose_best_ready(candidates: list[Path]) -> dict[str, Any] | None:
    ready = [_device_status(path) for path in candidates if _device_status(path)["ready"]]
    if not ready:
        return None
    scored = sorted(ready, key=lambda item: (_serial_score(Path(item["path"])), item["path"]), reverse=True)
    if len(scored) == 1:
        return scored[0]
    best_score = _serial_score(Path(scored[0]["path"]))
    second_score = _serial_score(Path(scored[1]["path"]))
    if best_score > second_score:
        return scored[0]
    return None


def _device_status(path: Path) -> dict[str, Any]:
    exists = path.exists()
    readable = os.access(path, os.R_OK) if exists else False
    writable = os.access(path, os.W_OK) if exists else False
    mode = None
    if exists:
        try:
            mode = stat.filemode(path.stat().st_mode)
        except OSError:
            mode = None
    return {"path": str(path), "exists": exists, "readable": readable, "writable": writable, "ready": readable and writable, "mode": mode}


def choose_serial(explicit: Path | None = None) -> dict[str, Any]:
    if explicit is None and os.environ.get("SERIAL"):
        explicit = Path(os.environ["SERIAL"])
    if explicit is not None:
        status = _device_status(explicit)
        status["source"] = "explicit"
        status["candidates"] = [str(p) for p in serial_candidates()]
        if not status["exists"]:
            status["message"] = f"serial device does not exist: {explicit}"
        elif not status["ready"]:
            status["message"] = f"serial device is not readable/writable by this user: {explicit}"
        else:
            status["message"] = "serial device is ready"
        return status

    candidates = serial_candidates()
    best = _choose_best_ready(candidates)
    if best is not None:
        best["source"] = "auto"
        best["candidates"] = [str(p) for p in candidates]
        best["message"] = "auto-detected a preferred usable serial device"
        return best
    return {
        "path": None,
        "exists": False,
        "readable": False,
        "writable": False,
        "ready": False,
        "mode": None,
        "source": "auto",
        "candidates": [str(p) for p in candidates],
        "message": "no unique usable serial device found; set SERIAL=/dev/ttyUSBx, SERIAL=/dev/ttyACMx, or a stable /dev/serial/by-id/... path",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial-device", type=Path, default=None, help="serial device; defaults to SERIAL or auto-detection")
    parser.add_argument("--log", type=Path, default=Path("uart.log"), help="capture log path")
    parser.add_argument("--baud", default=os.environ.get("BAUD", "19200"), help="UART baud rate")
    parser.add_argument("--dry-run", action="store_true", help="print the command without opening the port")
    parser.add_argument("--json", action="store_true", help="print selected device status as JSON")
    args = parser.parse_args()

    status = choose_serial(args.serial_device)
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))

    if not status["ready"]:
        print(f"error: {status['message']}", file=sys.stderr)
        if status["candidates"]:
            print("candidates:", file=sys.stderr)
            for candidate in status["candidates"]:
                print(f"  {candidate}", file=sys.stderr)
        return 2

    picocom = shutil.which("picocom")
    if picocom is None:
        print("error: picocom not found; enter the flake dev shell or install picocom", file=sys.stderr)
        return 2

    args.log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [picocom, "-b", str(args.baud), str(status["path"])]
    if args.dry_run:
        print(" ".join(cmd) + f" | tee {args.log}")
        return 0

    # Picocom forwards raw UART bytes. During early bring-up the stream may
    # contain framing noise, boot ROM probes, or bytes produced with the wrong
    # baud/clock configuration.  Do not let a single non-UTF-8 byte abort the
    # capture; preserve it visibly in the text log using the Unicode
    # replacement character so uart-report can still parse any valid lines.
    with args.log.open("w", encoding="utf-8", errors="replace") as log_file:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False)
        assert proc.stdout is not None
        try:
            for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace")
                print(line, end="")
                log_file.write(line)
                log_file.flush()
        finally:
            proc.wait()
    return proc.returncode


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
