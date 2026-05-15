#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ascon_hwmodel.verilog import write_verilog_files


def main() -> None:
    out_dir = Path("rtl/generated")
    written = write_verilog_files(out_dir)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
