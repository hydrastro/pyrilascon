from pathlib import Path

from ascon_hwmodel.verilog import write_verilog_files


def main() -> None:
    out_dir = Path("rtl/generated")
    written = write_verilog_files(out_dir)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
