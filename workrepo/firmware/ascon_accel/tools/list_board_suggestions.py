#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ascon_arch.board_suggestions import BoardClass, all_board_suggestions, board_suggestions, write_board_suggestions


def main() -> None:
    parser = argparse.ArgumentParser(description="List pyrilascon FPGA board suggestion profiles.")
    parser.add_argument("--board", choices=[board.value for board in BoardClass], help="board class to list")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--write", type=Path, help="directory where JSON profiles should be written")
    args = parser.parse_args()

    if args.write is not None:
        written = write_board_suggestions(args.write)
        for path in written:
            print(path)
        return

    profiles = (board_suggestions(args.board),) if args.board else all_board_suggestions()
    if args.format == "json":
        print(json.dumps([profile.to_dict() for profile in profiles], indent=2, sort_keys=True))
        return

    for profile in profiles:
        print(f"{profile.board_class.value}: {profile.goal}")
        for candidate in sorted(profile.candidates, key=lambda item: item.priority):
            print(f"  {candidate.priority}. {candidate.name}: {candidate.summary}")
        print()


if __name__ == "__main__":
    main()
