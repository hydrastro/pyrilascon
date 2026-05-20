#!/usr/bin/env python3
"""Run one Ascon hash/XOF/CXOF RTL vector against the Python golden model.

This is the hash-family analogue of ``run_stream_encrypt_vector.py``.
It builds a small per-vector Icarus Verilog testbench around
``rtl/common/ascon_hash_xof_backend.v``, runs it, and compares the
emitted digest bytes against the matching ``ascon_hwmodel.hash_xof``
function.

Variants supported:

  * ``hash256``  --> ``ASCON_MODE_HASH    = 4'd3``  (32-byte digest)
  * ``xof128``   --> ``ASCON_MODE_XOF     = 4'd5``  (variable length)
  * ``cxof128``  --> ``ASCON_MODE_CXOF128 = 4'd7``  (variable + customisation)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ascon_hwmodel.hash_xof import (  # noqa: E402
    ascon_hash256,
    ascon_xof128,
    ascon_cxof128,
)

# Bus protocol bit positions, mirroring ascon_accel_regs.vh.
ASCON_DATA_LAST   = 0x1
ASCON_DATA_VALID  = 0x2
ASCON_DATA_AD     = 0x4
ASCON_DATA_TEXT   = 0x8
ASCON_DATA_CUSTOM = 0x10
ASCON_DATA_KEEP_SHIFT = 8

MODE_HASH    = 3
MODE_XOF     = 5
MODE_CXOF128 = 7


@dataclass(frozen=True)
class GoldenVector:
    variant: str
    mode: int
    message_hex: str
    customisation_hex: str
    output_bytes: int
    digest_hex: str


@dataclass(frozen=True)
class RtlResult:
    digest_hex: str
    stdout: str
    cycles: int


@dataclass(frozen=True)
class ComparisonResult:
    golden: GoldenVector
    rtl: RtlResult | None
    matched: bool | None
    simulator: str | None


def build_golden(variant: str, message: bytes, customisation: bytes, out_bytes: int) -> GoldenVector:
    if variant == "hash256":
        if out_bytes != 32:
            raise ValueError("hash256 always produces 32 bytes")
        digest = ascon_hash256(message)
        mode = MODE_HASH
    elif variant == "xof128":
        digest = ascon_xof128(message, out_bytes)
        mode = MODE_XOF
    elif variant == "cxof128":
        digest = ascon_cxof128(message, out_bytes, customisation)
        mode = MODE_CXOF128
    else:
        raise ValueError(f"unknown variant: {variant}")
    return GoldenVector(
        variant=variant,
        mode=mode,
        message_hex=message.hex(),
        customisation_hex=customisation.hex(),
        output_bytes=out_bytes,
        digest_hex=digest.hex(),
    )


def _chunk_into_32bit_words(data: bytes) -> list[tuple[int, int]]:
    """Return list of (word_value_LE, keep_count) for streaming."""
    out: list[tuple[int, int]] = []
    for i in range(0, len(data), 4):
        chunk = data[i : i + 4]
        word = int.from_bytes(chunk + b"\x00" * (4 - len(chunk)), "little")
        out.append((word, len(chunk)))
    return out


def generate_testbench(golden: GoldenVector) -> str:
    """Emit a self-contained Icarus-Verilog testbench for one vector.

    The testbench streams the (optional) customisation first, then the
    message, then issues START. It drains the digest words from
    DATA_OUT and prints `DIGEST=<hex>` for the harness to capture.
    """
    cust = bytes.fromhex(golden.customisation_hex)
    msg = bytes.fromhex(golden.message_hex)
    cust_words = _chunk_into_32bit_words(cust)
    msg_words = _chunk_into_32bit_words(msg)
    out_words = (golden.output_bytes + 3) // 4

    lines: list[str] = []
    lines.append("`timescale 1ns/100ps")
    lines.append("module tb;")
    lines.append("  reg clk = 0; reg rstn = 0; reg start = 0;")
    lines.append(f"  reg [3:0]  mode = 4'd{golden.mode};")
    lines.append(f"  reg [31:0] text_len = 32'd{len(msg)};")
    lines.append(f"  reg [31:0] out_len  = 32'd{golden.output_bytes};")
    lines.append(f"  reg [31:0] custom_len = 32'd{len(cust)};")
    lines.append("  reg din_pulse=0; reg [31:0] din=0, din_ctrl=0;")
    lines.append("  reg dout_read=0;")
    lines.append("  wire busy, done, error;")
    lines.append("  wire [31:0] error_code, data_out, data_out_ctrl;")
    lines.append("")
    lines.append("  ascon_hash_xof_backend dut(")
    lines.append("    .clk_i(clk), .rstn_i(rstn), .start_i(start), .clear_i(1'b0),")
    lines.append("    .mode_i(mode), .text_len_i(text_len), .out_len_i(out_len),")
    lines.append("    .custom_len_i(custom_len),")
    lines.append("    .data_in_pulse_i(din_pulse), .data_in_i(din), .data_in_ctrl_i(din_ctrl),")
    lines.append("    .data_out_read_pulse_i(dout_read),")
    lines.append("    .busy_o(busy), .done_o(done), .error_o(error), .error_code_o(error_code),")
    lines.append("    .data_out_o(data_out), .data_out_ctrl_o(data_out_ctrl));")
    lines.append("")
    lines.append("  always #5 clk = ~clk;")
    lines.append("")
    lines.append(f"  reg [31:0] words [0:{max(out_words - 1, 0)}];")
    lines.append("  integer words_read = 0, safety = 0, k;")
    lines.append("  integer cycle_count = 0;")
    lines.append("")
    lines.append("  task stream_word(input [31:0] data, input [3:0] keep, input is_text, input is_custom);")
    lines.append("    begin")
    lines.append("      @(negedge clk);")
    lines.append("      din = data;")
    lines.append("      din_ctrl = (keep << 8) | (is_text ? 32'h8 : 32'h0) |")
    lines.append("                 (is_custom ? 32'h10 : 32'h0) | 32'h2;")
    lines.append("      din_pulse = 1;")
    lines.append("      @(posedge clk); @(negedge clk);")
    lines.append("      din_pulse = 0;")
    lines.append("      din_ctrl  = 0;")
    lines.append("    end")
    lines.append("  endtask")
    lines.append("")
    lines.append("  always @(posedge clk) if (rstn) cycle_count = cycle_count + 1;")
    lines.append("")
    lines.append("  initial begin")
    lines.append("    rstn = 0; #50 rstn = 1;")
    lines.append("    @(posedge clk);")
    # Stream customisation first (CXOF only); otherwise it's empty.
    for word, keep in cust_words:
        lines.append(f"    stream_word(32'h{word:08x}, 4'd{keep}, 1'b0, 1'b1);")
    # Then the message.
    for word, keep in msg_words:
        lines.append(f"    stream_word(32'h{word:08x}, 4'd{keep}, 1'b1, 1'b0);")
    lines.append("")
    lines.append("    @(negedge clk); start = 1;")
    lines.append("    @(posedge clk); @(negedge clk); start = 0;")
    lines.append("")
    lines.append(f"    while (words_read < {out_words} && safety < 100000) begin")
    lines.append("      @(posedge clk); safety = safety + 1;")
    lines.append("      if ((data_out_ctrl & 32'h2) != 0) begin")
    lines.append("        words[words_read] = data_out;")
    lines.append("        words_read = words_read + 1;")
    lines.append("        @(negedge clk); dout_read = 1;")
    lines.append("        @(posedge clk); @(negedge clk); dout_read = 0;")
    lines.append("      end")
    lines.append("    end")
    lines.append('    $write("DIGEST=");')
    lines.append(f"    for (k = 0; k < {out_words}; k = k + 1)")
    lines.append('      $write("%02x%02x%02x%02x", words[k][7:0], words[k][15:8], words[k][23:16], words[k][31:24]);')
    lines.append('    $write("\\n");')
    lines.append('    $display("CYCLES=%0d", cycle_count);')
    lines.append("    $finish;")
    lines.append("  end")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def run_vector(golden: GoldenVector, simulator: str = "iverilog") -> RtlResult:
    if simulator != "iverilog":
        raise ValueError(f"unsupported simulator: {simulator}")
    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    if iverilog is None or vvp is None:
        raise RuntimeError("iverilog / vvp not on PATH")

    rtl_dir = REPO_ROOT / "rtl" / "common"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tb_path = tmp / "tb.v"
        tb_path.write_text(generate_testbench(golden))
        out_path = tmp / "sim.out"

        compile_cmd = [
            iverilog, "-g2012",
            "-I", str(rtl_dir),
            "-o", str(out_path),
            str(rtl_dir / "ascon_round_comb.v"),
            str(rtl_dir / "ascon_hash_xof_backend.v"),
            str(tb_path),
        ]
        subprocess.run(compile_cmd, check=True, capture_output=True, text=True)

        run = subprocess.run([vvp, str(out_path)], check=True, capture_output=True, text=True)
        stdout = run.stdout

    digest_hex = ""
    cycles = -1
    truncated_digest = (golden.output_bytes * 2)
    for line in stdout.splitlines():
        if line.startswith("DIGEST="):
            full = line[len("DIGEST="):].strip()
            # The TB always emits 4-byte-aligned hex; truncate to actual length.
            digest_hex = full[: truncated_digest]
        elif line.startswith("CYCLES="):
            cycles = int(line[len("CYCLES="):].strip())
    return RtlResult(digest_hex=digest_hex, stdout=stdout, cycles=cycles)


def compare(golden: GoldenVector, rtl: RtlResult | None) -> ComparisonResult:
    matched = None if rtl is None else (rtl.digest_hex == golden.digest_hex)
    return ComparisonResult(golden=golden, rtl=rtl, matched=matched, simulator="iverilog")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("hash256", "xof128", "cxof128"), required=True)
    parser.add_argument("--message-hex", default="")
    parser.add_argument("--customisation-hex", default="")
    parser.add_argument("--out-bytes", type=int, default=32)
    parser.add_argument("--dry-run", action="store_true",
                        help="Emit the golden vector and the testbench source; don't run a simulator.")
    parser.add_argument("--emit-testbench", action="store_true",
                        help="Write the generated testbench to stdout instead of running.")
    args = parser.parse_args(argv)

    msg = bytes.fromhex(args.message_hex)
    cust = bytes.fromhex(args.customisation_hex)
    if args.variant == "hash256":
        args.out_bytes = 32
    if args.variant != "cxof128" and cust:
        raise SystemExit("customisation is only valid for cxof128")

    golden = build_golden(args.variant, msg, cust, args.out_bytes)

    if args.emit_testbench:
        sys.stdout.write(generate_testbench(golden))
        return 0
    if args.dry_run:
        json.dump(asdict(golden), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    rtl = run_vector(golden)
    result = compare(golden, rtl)
    payload = {
        "golden": asdict(result.golden),
        "rtl": None if result.rtl is None else asdict(result.rtl),
        "matched": result.matched,
        "simulator": result.simulator,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if result.matched else 1


if __name__ == "__main__":
    sys.exit(main())
