"""Emit (and optionally verify) generated ASCON RTL cores.

  python -m ascon_designspace.generator --list
  python -m ascon_designspace.generator --rounds-per-cycle 4  -o core.v [--verify]
  python -m ascon_designspace.generator --pipelined 12        -o pipe.v [--verify]
  python -m ascon_designspace.generator --column-serial 1     -o cs.v   [--verify]
"""
from __future__ import annotations

import argparse
import sys

from ascon_designspace.generator.permutation import (
    ROUND_BASED_RPC,
    emit_iterative_permutation,
    emit_pipelined_permutation,
)
from ascon_designspace.generator.structural import emit_context_pipeline
from ascon_designspace.generator.control import emit_microcoded_permutation
from ascon_designspace.generator.aead import emit_aead_core_for
from ascon_designspace.generator.hash256 import (
    emit_cxof128_core, emit_hash256_core, emit_hasha_core, emit_xof128_core, emit_xofa_core)
from ascon_designspace.generator.serial import (
    COLUMN_SERIAL_COLUMNS,
    emit_bit_serial_permutation,
    emit_column_serial_permutation,
)


def main() -> None:
    ap = argparse.ArgumentParser(prog="ascon_designspace.generator")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--rounds-per-cycle", type=int, metavar="R", help="round-based core, R in 1/2/4/8")
    g.add_argument("--pipelined", type=int, metavar="N", help="fully-pipelined p[N], N in 6/8/12")
    g.add_argument("--column-serial", type=int, metavar="K", help="column-serial core, K columns/cycle")
    g.add_argument("--bit-serial", action="store_true", help="bit-serial core (most serial)")
    g.add_argument("--context-pipeline", type=int, metavar="N",
                   help="one-pipelined-permutation-N-contexts wrapper for p[N]")
    g.add_argument("--microcoded", action="store_true", help="microcoded-sequencer permutation (control style)")
    ap.add_argument("--contexts", type=int, default=4, help="contexts for --context-pipeline")
    g.add_argument("--aead", choices=["aead128", "aead128a", "ascon128", "aead80pq"],
                   help="full AEAD core for a variant (composes a permutation)")
    g.add_argument("--hash", choices=["hash256", "xof128", "cxof128", "hasha", "xofa"],
                   help="full hash/XOF core (composes a permutation)")
    ap.add_argument("-o", "--out", help="write the module here (default: stdout)")
    ap.add_argument("--verify", action="store_true", help="simulate against the golden model (needs iverilog)")
    ap.add_argument("--list", action="store_true", help="list what the generator emits")
    args = ap.parse_args()

    if args.list:
        print("round-based (rounds/cycle): " + ", ".join(str(r) for r in sorted(set(ROUND_BASED_RPC.values()))))
        print("fully-pipelined (rounds)  : 6, 8, 12")
        print("column-serial (cols/cycle): " + ", ".join(str(k) for k in COLUMN_SERIAL_COLUMNS))
        print("bit-serial                : serial S-box + serial linear layer")
        print("context-pipeline (topology): N contexts through one pipelined p[6/8/12]")
        print("microcoded (control style): ROM-driven sequencer over the round datapath")
        print("aead (cores)              : aead128, aead128a, ascon128, aead80pq")
        print("hash (cores)              : hash256, xof128, cxof128, hasha, xofa")
        return

    if args.rounds_per_cycle is not None:
        kind, param, rtl = "rounds_per_cycle", args.rounds_per_cycle, emit_iterative_permutation(args.rounds_per_cycle)
    elif args.pipelined is not None:
        kind, param, rtl = "pipelined", args.pipelined, emit_pipelined_permutation(args.pipelined)
    elif args.column_serial is not None:
        kind, param, rtl = "column_serial", args.column_serial, emit_column_serial_permutation(args.column_serial)
    elif args.bit_serial:
        kind, param, rtl = "bit_serial", None, emit_bit_serial_permutation()
    elif args.context_pipeline is not None:
        cn = args.context_pipeline
        kind, param = "context_pipeline", (cn, args.contexts)
        rtl = emit_pipelined_permutation(cn) + "\n" + emit_context_pipeline(cn, args.contexts)
    elif args.microcoded:
        kind, param, rtl = "microcoded", None, emit_microcoded_permutation()
    elif args.aead is not None:
        kind, param = "aead", args.aead
        rtl = emit_aead_core_for(args.aead) + "\n" + emit_iterative_permutation(1)
    elif args.hash is not None:
        kind, param = "hash", args.hash
        hcore = {"hash256": emit_hash256_core, "xof128": emit_xof128_core, "cxof128": emit_cxof128_core,
                 "hasha": emit_hasha_core, "xofa": emit_xofa_core}[args.hash]
        rtl = hcore() + "\n" + emit_iterative_permutation(1)
    else:
        ap.error("pass a --rounds-per-cycle / --pipelined / --column-serial / --bit-serial / --context-pipeline / --microcoded / --aead / --hash, or --list")

    if args.verify:
        from ascon_designspace.generator.verify import (
            iverilog_available,
            verify_column_serial,
            verify_permutation,
            verify_pipeline,
        )

        if not iverilog_available():
            print("iverilog/vvp not found; cannot verify", file=sys.stderr)
            sys.exit(2)
        if kind == "bit_serial":
            from ascon_designspace.generator.verify import verify_bit_serial
            ok, _trials, line = verify_bit_serial()
        elif kind == "microcoded":
            from ascon_designspace.generator.verify import verify_microcoded
            ok, _trials, line = verify_microcoded()
        elif kind == "context_pipeline":
            from ascon_designspace.generator.verify import verify_context_pipeline
            ok, _trials, line = verify_context_pipeline(*param)
        elif kind == "aead":
            from ascon_designspace.generator.verify import verify_aead
            ok, _trials, line = verify_aead(param)
        elif kind == "hash":
            from ascon_designspace.generator import verify as _v
            fn = {"hash256": _v.verify_hash256, "xof128": _v.verify_xof128, "cxof128": _v.verify_cxof128,
                  "hasha": _v.verify_hasha, "xofa": _v.verify_xofa}[param]
            ok, _trials, line = fn()
        else:
            verifier = {
                "rounds_per_cycle": verify_permutation,
                "pipelined": verify_pipeline,
                "column_serial": verify_column_serial,
            }[kind]
            ok, _trials, line = verifier(param)
        print(line)
        sys.exit(0 if ok else 1)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(rtl)
        print(f"wrote {args.out}")
    else:
        print(rtl)


if __name__ == "__main__":
    main()
