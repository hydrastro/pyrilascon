#!/usr/bin/env python3
"""Capture a complete NEORV32 benchmark run from a serial port.

The capture is deterministic: it opens the UART, discards stale bytes, waits for
the user to press the board reset key, records raw bytes, and exits only after a
standalone ``PASS``/``FAIL`` line or a timeout. This avoids picocom banners and
truncated one-case logs in benchmark evidence.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import stat
import sys
import time
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
            key = str(path.resolve()) if path.exists() else str(path)
            if key not in seen:
                seen.add(key)
                found.append(path)
    return found


def _serial_score(path: Path) -> int:
    text = str(path)
    score = 20 if "/dev/serial/by-id/" in text else 0
    upper = text.upper()
    if "SIPEED" in upper or "TANG" in upper or "GOWIN" in upper:
        score += 50
    if "if01" in text:
        score += 5
    if "if00" in text:
        score += 1
    return score


def _device_status(path: Path) -> dict[str, Any]:
    exists = path.exists()
    readable = os.access(path, os.R_OK) if exists else False
    writable = os.access(path, os.W_OK) if exists else False
    mode = None
    if exists:
        try:
            mode = stat.filemode(path.stat().st_mode)
        except OSError:
            pass
    return {
        "path": str(path),
        "exists": exists,
        "readable": readable,
        "writable": writable,
        "ready": readable and writable,
        "mode": mode,
    }


def _choose_best_ready(candidates: list[Path]) -> dict[str, Any] | None:
    ready: list[dict[str, Any]] = []
    for path in candidates:
        status = _device_status(path)
        if status["ready"]:
            ready.append(status)
    if not ready:
        return None
    scored = sorted(
        ready,
        key=lambda item: (_serial_score(Path(item["path"])), item["path"]),
        reverse=True,
    )
    if len(scored) == 1:
        return scored[0]
    if _serial_score(Path(scored[0]["path"])) > _serial_score(Path(scored[1]["path"])):
        return scored[0]
    return None


def choose_serial(explicit: Path | None = None) -> dict[str, Any]:
    if explicit is None and os.environ.get("SERIAL"):
        explicit = Path(os.environ["SERIAL"])
    if explicit is not None:
        status = _device_status(explicit)
        status["source"] = "explicit"
        status["candidates"] = [str(path) for path in serial_candidates()]
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
        best["candidates"] = [str(path) for path in candidates]
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
        "candidates": [str(path) for path in candidates],
        "message": (
            "no unique usable serial device found; set SERIAL=/dev/ttyUSBx, "
            "SERIAL=/dev/ttyACMx, or a stable /dev/serial/by-id/... path"
        ),
    }


def capture(path: str, *, baud: int, log_path: Path, timeout_s: float) -> int:
    try:
        import serial  # type: ignore[import-not-found]
    except ImportError:
        print("error: pyserial is not installed; re-enter `nix develop`", file=sys.stderr)
        return 2

    log_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_s
    line_buffer = bytearray()
    final_result: str | None = None

    print(f"Opening {path} at {baud} baud (8N1, no flow control).")
    print("Press S1/KEY1 on the Tang Nano 20K once. Capture stops automatically at PASS/FAIL.")

    try:
        with serial.Serial(
            port=path,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        ) as port, log_path.open("wb") as log_file:
            port.reset_input_buffer()
            while time.monotonic() < deadline:
                chunk = port.read(256)
                if not chunk:
                    continue
                log_file.write(chunk)
                log_file.flush()
                sys.stdout.write(chunk.decode("utf-8", errors="replace"))
                sys.stdout.flush()
                line_buffer.extend(chunk)

                while b"\n" in line_buffer:
                    raw_line, _, remainder = line_buffer.partition(b"\n")
                    line_buffer = bytearray(remainder)
                    line = raw_line.decode("utf-8", errors="replace").strip().strip("\x00\ufffd").strip()
                    if line == "PASS":
                        final_result = "PASS"
                        break
                    if line == "FAIL" or line.startswith("FAIL:"):
                        final_result = "FAIL"
                        break
                if final_result is not None:
                    break
    except (OSError, ValueError) as exc:
        print(f"\nerror: serial capture failed: {exc}", file=sys.stderr)
        return 2

    if final_result == "PASS":
        print(f"\nCaptured complete PASS log: {log_path}")
        return 0
    if final_result == "FAIL":
        print(f"\nFirmware reported FAIL; log retained at {log_path}", file=sys.stderr)
        return 1
    print(f"\nerror: timed out after {timeout_s:g}s before PASS/FAIL; partial log: {log_path}", file=sys.stderr)
    return 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial-device", type=Path, default=None)
    parser.add_argument("--log", type=Path, default=Path("uart.log"))
    parser.add_argument("--baud", type=int, default=int(os.environ.get("BAUD", "19200")))
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    status = choose_serial(args.serial_device)
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
    if not status["ready"]:
        print(f"error: {status['message']}", file=sys.stderr)
        for candidate in status["candidates"]:
            print(f"  {candidate}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(
            f"capture {status['path']} at {args.baud} baud to {args.log}; "
            f"timeout={args.timeout:g}s"
        )
        return 0
    return capture(
        str(status["path"]),
        baud=args.baud,
        log_path=args.log,
        timeout_s=args.timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
