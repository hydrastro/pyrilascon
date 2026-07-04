"""Unified board CLI.

  python -m ascon_boards list-boards
  python -m ascon_boards list-targets
  python -m ascon_boards emit    --board tangnano9k --target perm_smoke
  python -m ascon_boards build   --board tangnano9k --target perm_smoke [--dry-run]
  python -m ascon_boards flash   --board tangnano9k --target perm_smoke [--to-flash]

`build` runs synth -> pnr -> pack; `flash` runs the whole flow then the loader.
`--dry-run` prints the exact commands without running them.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from ascon_boards import build as B
from ascon_boards.targets import emit_target, list_targets


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--board", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--build-dir", default="build")
    p.add_argument("--dry-run", action="store_true")


def _prepare(args):
    board = B.load_board(args.board)
    build_dir = pathlib.Path(args.build_dir).resolve()
    built = emit_target(args.target, build_dir, board=board)
    return board, built, build_dir


def _do_synth(board, built, build_dir, dry_run):
    cmd, json_out = B.synth_command(board, built, build_dir)
    rc = B.run_step("synth (yosys)", cmd, dry_run=dry_run)
    return rc, json_out


def _do_pnr(board, built, build_dir, json_out, dry_run):
    cmd, pnr_out = B.pnr_command(board, built, build_dir, json_out)
    rc = B.run_step("pnr (nextpnr)", cmd, dry_run=dry_run)
    return rc, pnr_out


def _do_pack(board, built, build_dir, pnr_out, dry_run):
    cmd, fs = B.pack_command(board, built, build_dir, pnr_out)
    rc = B.run_step("pack (gowin_pack)", cmd, dry_run=dry_run)
    return rc, fs


def main() -> None:
    ap = argparse.ArgumentParser(prog="ascon_boards")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-boards")
    sub.add_parser("list-targets")
    for name in ("emit", "synth", "pnr", "pack", "build", "flash"):
        sp = sub.add_parser(name)
        _add_common(sp)
        if name == "flash":
            sp.add_argument("--to-flash", action="store_true", help="write SPI flash (persistent) instead of SRAM")

    args = ap.parse_args()

    if args.cmd == "list-boards":
        for b in B.list_boards():
            print(b)
        return
    if args.cmd == "list-targets":
        for t in list_targets():
            print(t)
        return

    board, built, build_dir = _prepare(args)

    if args.cmd == "emit":
        print(f"top module : {built.top_module}")
        print(f"sources    : {', '.join(str(s) for s in built.sources)}")
        print(f"include    : {', '.join(str(d) for d in built.include_dirs)}")
        return

    if args.cmd == "synth":
        rc, _ = _do_synth(board, built, build_dir, args.dry_run)
        sys.exit(rc)
    if args.cmd == "pnr":
        _, json_out = B.synth_command(board, built, build_dir)
        rc, _ = _do_pnr(board, built, build_dir, json_out, args.dry_run)
        sys.exit(rc)
    if args.cmd == "pack":
        _, json_out = B.synth_command(board, built, build_dir)
        _, pnr_out = B.pnr_command(board, built, build_dir, json_out)
        rc, _ = _do_pack(board, built, build_dir, pnr_out, args.dry_run)
        sys.exit(rc)

    if args.cmd in ("build", "flash"):
        rc, json_out = _do_synth(board, built, build_dir, args.dry_run)
        if rc:
            sys.exit(rc)
        rc, pnr_out = _do_pnr(board, built, build_dir, json_out, args.dry_run)
        if rc:
            sys.exit(rc)
        rc, fs = _do_pack(board, built, build_dir, pnr_out, args.dry_run)
        if rc:
            sys.exit(rc)
        if args.cmd == "flash":
            cmd = B.flash_command(board, fs, to_flash=getattr(args, "to_flash", False))
            where = "SPI flash" if getattr(args, "to_flash", False) else "SRAM"
            sys.exit(B.run_step(f"flash -> {where} (openFPGALoader)", cmd, dry_run=args.dry_run))
        print(f"bitstream: {fs}")


if __name__ == "__main__":
    main()
