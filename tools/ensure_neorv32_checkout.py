#!/usr/bin/env python3
"""Locate or optionally fetch a NEORV32 checkout for board bring-up.

The ASCON repository intentionally does not vendor NEORV32.  This helper makes
that external dependency portable by using a deterministic project-local default
(`external/neorv32`) while still honoring an explicit NEORV32_HOME supplied by a
user, CI job, or board-lab machine.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VENDOR_DIR = REPO_ROOT / "external" / "neorv32"
DEFAULT_REPO_URL = "https://github.com/stnolting/neorv32.git"
PLACEHOLDER_NEORV32_HOME = "/path/to/neorv32"


class NEORV32CheckoutError(RuntimeError):
    """Raised when a NEORV32 checkout cannot be located or fetched."""


def _is_placeholder(path: Path | None) -> bool:
    if path is None:
        return False
    text = str(path)
    return text == PLACEHOLDER_NEORV32_HOME or "path/to/neorv32" in text


def is_neorv32_checkout(path: Path) -> bool:
    return (path / "sw" / "common" / "common.mk").is_file()


def _normalize_path(path: Path, *, base: Path | None = None) -> Path:
    """Return an absolute path without relying on $HOME-specific probes.

    Relative project-local defaults are anchored to the repository root.
    Explicit CLI/env paths are anchored to the caller's current directory, which
    is how shell users expect relative path arguments to behave.
    """

    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded
    return (base or Path.cwd()) / expanded


def candidate_paths(explicit: Path | None = None, vendor_dir: Path = DEFAULT_VENDOR_DIR) -> list[dict[str, str]]:
    # Precedence is strict: an explicit CLI path overrides everything, then an
    # exported NEORV32_HOME, then the project-local checkout.  We intentionally
    # do *not* fall back when an explicit/env path is invalid, because that hides
    # configuration errors and makes board-bringup non-reproducible.
    if explicit is not None:
        candidates: list[tuple[str, Path, Path | None]] = [("cli", explicit, None)]
    elif os.environ.get("NEORV32_HOME"):
        candidates = [("env:NEORV32_HOME", Path(os.environ["NEORV32_HOME"]), None)]
    else:
        candidates = [("project-local", vendor_dir, REPO_ROOT)]

    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for source, path, base in candidates:
        resolved_path = _normalize_path(path, base=base)
        resolved = str(resolved_path)
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append({"source": source, "path": resolved})
    return result


def locate_neorv32(explicit: Path | None = None, vendor_dir: Path = DEFAULT_VENDOR_DIR) -> dict[str, Any]:
    candidates = candidate_paths(explicit=explicit, vendor_dir=vendor_dir)
    inspected: list[dict[str, Any]] = []
    for item in candidates:
        path = Path(item["path"]).expanduser()
        status = {
            "source": item["source"],
            "path": str(path),
            "is_placeholder": _is_placeholder(path),
            "exists": path.exists(),
            "common_mk": is_neorv32_checkout(path),
            "ready": path.exists() and is_neorv32_checkout(path) and not _is_placeholder(path),
        }
        inspected.append(status)
        if status["ready"]:
            return {
                "ready": True,
                "home": str(path),
                "source": item["source"],
                "candidates": inspected,
                "message": "NEORV32 checkout found.",
            }

    return {
        "ready": False,
        "home": None,
        "source": None,
        "candidates": inspected,
        "message": (
            "No usable NEORV32 checkout found. Set NEORV32_HOME to an existing checkout "
            "or run `make neorv32-fetch` to clone one into external/neorv32."
        ),
    }


def fetch_neorv32(vendor_dir: Path = DEFAULT_VENDOR_DIR, repo_url: str = DEFAULT_REPO_URL, ref: str | None = None, depth: int = 1) -> Path:
    vendor_dir = vendor_dir.expanduser()
    if is_neorv32_checkout(vendor_dir):
        return vendor_dir
    if vendor_dir.exists() and any(vendor_dir.iterdir()):
        raise NEORV32CheckoutError(f"target directory exists but is not a NEORV32 checkout: {vendor_dir}")
    git = shutil.which("git")
    if git is None:
        raise NEORV32CheckoutError("git is not available; cannot clone NEORV32")
    vendor_dir.parent.mkdir(parents=True, exist_ok=True)
    cmd = [git, "clone", "--depth", str(depth)]
    if ref:
        cmd.extend(["--branch", ref])
    cmd.extend([repo_url, str(vendor_dir)])
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    if not is_neorv32_checkout(vendor_dir):
        raise NEORV32CheckoutError(f"clone completed but sw/common/common.mk was not found in {vendor_dir}")
    return vendor_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neorv32-home", type=Path, default=None, help="explicit checkout path; overrides auto-detection")
    parser.add_argument("--vendor-dir", type=Path, default=DEFAULT_VENDOR_DIR, help="project-local checkout directory")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL, help="NEORV32 git URL used by --fetch")
    parser.add_argument("--ref", default=None, help="optional branch/tag for --fetch")
    parser.add_argument("--depth", type=int, default=1, help="git clone depth for --fetch")
    parser.add_argument("--fetch", action="store_true", help="clone NEORV32 into --vendor-dir if it is missing")
    parser.add_argument("--check", action="store_true", help="return nonzero when no checkout is ready")
    parser.add_argument("--print-home", action="store_true", help="print the resolved checkout path only")
    parser.add_argument("--json", action="store_true", help="print JSON status")
    args = parser.parse_args()

    if args.fetch:
        try:
            fetch_neorv32(vendor_dir=args.vendor_dir, repo_url=args.repo_url, ref=args.ref, depth=args.depth)
        except (NEORV32CheckoutError, subprocess.CalledProcessError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    status = locate_neorv32(explicit=args.neorv32_home, vendor_dir=args.vendor_dir)

    if args.print_home:
        if status["ready"]:
            print(status["home"])
            return 0
        print(status["message"], file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        print(status["message"])
        if status["home"]:
            print(f"NEORV32_HOME={status['home']}")
        else:
            print("suggested setup:")
            print("  make neorv32-fetch")
            print("  export NEORV32_HOME=$PWD/external/neorv32")

    if args.check and not status["ready"]:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
