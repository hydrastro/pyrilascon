#!/usr/bin/env python3
"""Run one AXI-stream AEAD128 encryption RTL vector against the Python oracle.

The script generates a small vector-specific Verilog testbench, builds it with
Icarus Verilog, runs it with vvp, and compares the emitted ciphertext/tag against
``ascon_hwmodel.aead_stream.axis_aead128_encrypt``.

Use ``--dry-run`` when a simulator is not available; it still emits the golden
reference values and the generated input beat metadata.
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
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ascon_hwmodel.aead_stream import (  # noqa: E402
    AeadStreamKind,
    AxisStreamBeat,
    axis_aead128_encrypt,
    pack_axis_beats,
)

DATA_BYTES = 16
ASCON_AXIS_USER_AD = 0x1
ASCON_AXIS_USER_TEXT = 0x2
ASCON_MODE_AEAD128 = 0x0


@dataclass(frozen=True)
class BeatJson:
    data_hex: str
    keep_hex: str
    last: bool
    user_hex: str
    payload_hex: str


@dataclass(frozen=True)
class GoldenVector:
    key_hex: str
    nonce_hex: str
    associated_data_hex: str
    plaintext_hex: str
    ciphertext_hex: str
    tag_hex: str
    ad_beats: list[BeatJson]
    plaintext_beats: list[BeatJson]
    ciphertext_beats: list[BeatJson]


@dataclass(frozen=True)
class RtlResult:
    ciphertext_hex: str
    tag_hex: str
    error: int
    error_code: int
    cycles: int
    stdout: str


@dataclass(frozen=True)
class ComparisonResult:
    golden: GoldenVector
    rtl: RtlResult | None
    matched: bool | None
    simulator: str | None


def parse_hex_bytes(text: str, *, field: str, expected_len: int | None = None) -> bytes:
    clean = text.strip().lower().removeprefix("0x").replace("_", "").replace(" ", "")
    if len(clean) % 2 != 0:
        raise ValueError(f"{field} must contain an even number of hex digits")
    try:
        data = bytes.fromhex(clean)
    except ValueError as exc:
        raise ValueError(f"{field} is not valid hexadecimal") from exc
    if expected_len is not None and len(data) != expected_len:
        raise ValueError(f"{field} must be {expected_len} bytes, got {len(data)}")
    return data


def int_literal_from_bytes_le(data: bytes) -> str:
    return f"{int.from_bytes(data, 'little'):0{len(data) * 2}x}"


def beat_to_json(beat: AxisStreamBeat) -> BeatJson:
    return BeatJson(
        data_hex=beat.data.hex(),
        keep_hex=f"{beat.keep:0{DATA_BYTES // 4}x}",
        last=beat.last,
        user_hex="1" if beat.kind == AeadStreamKind.AD else "2",
        payload_hex=beat.payload.hex(),
    )


def build_golden_vector(key: bytes, nonce: bytes, associated_data: bytes, plaintext: bytes) -> GoldenVector:
    ad_beats = pack_axis_beats(associated_data, AeadStreamKind.AD, DATA_BYTES)
    pt_beats = pack_axis_beats(plaintext, AeadStreamKind.TEXT, DATA_BYTES)
    golden = axis_aead128_encrypt(
        key=key,
        nonce=nonce,
        ad_beats=ad_beats,
        plaintext_beats=pt_beats,
        ad_len=len(associated_data),
        text_len=len(plaintext),
        bus_bytes=DATA_BYTES,
    )
    return GoldenVector(
        key_hex=key.hex(),
        nonce_hex=nonce.hex(),
        associated_data_hex=associated_data.hex(),
        plaintext_hex=plaintext.hex(),
        ciphertext_hex=golden.ciphertext.hex(),
        tag_hex=golden.tag.hex(),
        ad_beats=[beat_to_json(beat) for beat in ad_beats],
        plaintext_beats=[beat_to_json(beat) for beat in pt_beats],
        ciphertext_beats=[beat_to_json(beat) for beat in golden.ciphertext_beats],
    )


def verilog_tdata_literal(data_hex: str) -> str:
    data = bytes.fromhex(data_hex)
    return f"128'h{int_literal_from_bytes_le(data)}"


def send_beat_statement(beat: BeatJson) -> str:
    user = ASCON_AXIS_USER_AD if beat.user_hex == "1" else ASCON_AXIS_USER_TEXT
    return (
        f"    send_beat({verilog_tdata_literal(beat.data_hex)}, "
        f"16'h{beat.keep_hex}, 1'b{1 if beat.last else 0}, 4'h{user:x});"
    )


def generate_testbench(vector: GoldenVector, *, timeout_cycles: int = 5000) -> str:
    send_lines = [send_beat_statement(beat) for beat in vector.ad_beats]
    send_lines.extend(send_beat_statement(beat) for beat in vector.plaintext_beats)
    send_body = "\n".join(send_lines) if send_lines else "    // Zero-length AD and plaintext: no AXI input beats."

    key_lit = int_literal_from_bytes_le(bytes.fromhex(vector.key_hex))
    nonce_lit = int_literal_from_bytes_le(bytes.fromhex(vector.nonce_hex))
    ad_len = len(bytes.fromhex(vector.associated_data_hex))
    text_len = len(bytes.fromhex(vector.plaintext_hex))

    return f"""`timescale 1ns/1ps

module tb_ascon_aead128_stream_encrypt;
  localparam integer DATA_BYTES = 16;
  localparam integer DATA_WIDTH = DATA_BYTES * 8;

  reg clk_i = 1'b0;
  reg rstn_i = 1'b0;
  reg start_i = 1'b0;
  reg clear_i = 1'b0;
  reg decrypt_i = 1'b0;
  reg [3:0] mode_i = 4'h{ASCON_MODE_AEAD128:x};
  reg [31:0] ad_len_i = 32'd{ad_len};
  reg [31:0] text_len_i = 32'd{text_len};
  reg [31:0] out_len_i = 32'd0;
  reg [31:0] custom_len_i = 32'd0;
  reg [127:0] key_i = 128'h{key_lit};
  reg [127:0] nonce_i = 128'h{nonce_lit};

  reg [DATA_WIDTH-1:0] s_axis_tdata = {{DATA_WIDTH{{1'b0}}}};
  reg [DATA_BYTES-1:0] s_axis_tkeep = {{DATA_BYTES{{1'b0}}}};
  reg s_axis_tvalid = 1'b0;
  wire s_axis_tready;
  reg s_axis_tlast = 1'b0;
  reg [3:0] s_axis_tuser = 4'h0;

  wire [DATA_WIDTH-1:0] m_axis_tdata;
  wire [DATA_BYTES-1:0] m_axis_tkeep;
  wire m_axis_tvalid;
  reg m_axis_tready = 1'b1;
  wire m_axis_tlast;
  wire [3:0] m_axis_tuser;

  wire busy_o;
  wire done_o;
  wire tag_valid_o;
  wire error_o;
  wire [31:0] error_code_o;
  wire [127:0] generated_tag_o;

  integer cycle_count = 0;
  integer timeout_cycles = {timeout_cycles};

  ascon_aead128_stream_encrypt #(
    .DATA_BYTES(DATA_BYTES),
    .DATA_WIDTH(DATA_WIDTH)
  ) dut (
    .clk_i(clk_i),
    .rstn_i(rstn_i),
    .start_i(start_i),
    .clear_i(clear_i),
    .decrypt_i(decrypt_i),
    .mode_i(mode_i),
    .ad_len_i(ad_len_i),
    .text_len_i(text_len_i),
    .out_len_i(out_len_i),
    .custom_len_i(custom_len_i),
    .key_i(key_i),
    .nonce_i(nonce_i),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tkeep(s_axis_tkeep),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tlast(s_axis_tlast),
    .s_axis_tuser(s_axis_tuser),
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tkeep(m_axis_tkeep),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),
    .m_axis_tlast(m_axis_tlast),
    .m_axis_tuser(m_axis_tuser),
    .busy_o(busy_o),
    .done_o(done_o),
    .tag_valid_o(tag_valid_o),
    .error_o(error_o),
    .error_code_o(error_code_o),
    .generated_tag_o(generated_tag_o)
  );

  always #5 clk_i = ~clk_i;

  always @(posedge clk_i) begin
    cycle_count <= cycle_count + 1;
    if (m_axis_tvalid && m_axis_tready) begin
      $display("OUT_BEAT cycle=%0d data=%032x keep=%04x last=%0d user=%0h", cycle_count, m_axis_tdata, m_axis_tkeep, m_axis_tlast, m_axis_tuser);
    end
    if (done_o) begin
      $display("DONE cycle=%0d error=%0d error_code=%0d tag=%032x", cycle_count, error_o, error_code_o, generated_tag_o);
      $finish;
    end
    if (cycle_count > timeout_cycles) begin
      $display("TIMEOUT cycle=%0d", cycle_count);
      $finish;
    end
  end

  task send_beat;
    input [DATA_WIDTH-1:0] data;
    input [DATA_BYTES-1:0] keep;
    input last;
    input [3:0] user;
    begin
      // AXI valid must remain asserted until a real valid/ready handshake.
      // Earlier versions sampled tready before asserting tvalid and then held
      // the beat for only one cycle; that can drop later beats when the DUT
      // deasserts ready between the pre-check and the sampling edge.
      @(negedge clk_i);
      s_axis_tdata = data;
      s_axis_tkeep = keep;
      s_axis_tlast = last;
      s_axis_tuser = user;
      s_axis_tvalid = 1'b1;
      while (!s_axis_tready) begin
        @(posedge clk_i);
      end
      @(posedge clk_i);
      @(negedge clk_i);
      s_axis_tvalid = 1'b0;
      s_axis_tdata = {{DATA_WIDTH{{1'b0}}}};
      s_axis_tkeep = {{DATA_BYTES{{1'b0}}}};
      s_axis_tlast = 1'b0;
      s_axis_tuser = 4'h0;
    end
  endtask

  initial begin
    repeat (4) @(posedge clk_i);
    rstn_i = 1'b1;
    repeat (2) @(posedge clk_i);
    @(negedge clk_i);
    start_i = 1'b1;
    @(negedge clk_i);
    start_i = 1'b0;

{send_body}
  end
endmodule
"""


def simulator_available() -> str | None:
    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    if not iverilog or not vvp:
        return None
    return iverilog


def parse_rtl_stdout(stdout: str) -> RtlResult:
    ciphertext = bytearray()
    done: dict[str, int | str] | None = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("OUT_BEAT "):
            fields = dict(part.split("=", 1) for part in line.split()[1:])
            data = int(fields["data"], 16).to_bytes(DATA_BYTES, "little")
            keep = int(fields["keep"], 16)
            for index in range(DATA_BYTES):
                if (keep >> index) & 1:
                    ciphertext.append(data[index])
        elif line.startswith("DONE "):
            fields = dict(part.split("=", 1) for part in line.split()[1:])
            done = fields
        elif line.startswith("TIMEOUT "):
            raise RuntimeError(line)
    if done is None:
        raise RuntimeError(f"simulation did not report DONE; output was:\n{stdout}")
    tag = int(str(done["tag"]), 16).to_bytes(DATA_BYTES, "little")
    return RtlResult(
        ciphertext_hex=bytes(ciphertext).hex(),
        tag_hex=tag.hex(),
        error=int(str(done["error"]), 0),
        error_code=int(str(done["error_code"]), 0),
        cycles=int(str(done["cycle"]), 0),
        stdout=stdout,
    )


def run_iverilog_simulation(repo_root: Path, testbench_text: str, workdir: Path) -> RtlResult:
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        raise RuntimeError("iverilog and vvp are required for RTL simulation")

    tb_path = workdir / "tb_ascon_aead128_stream_encrypt.v"
    simv_path = workdir / "tb_ascon_aead128_stream_encrypt.vvp"
    tb_path.write_text(testbench_text, encoding="utf-8")

    sources = [
        repo_root / "rtl/common/ascon_round_comb.v",
        repo_root / "rtl/stream/ascon_axis_framer.v",
        repo_root / "rtl/stream/ascon_aead128_stream_encrypt.v",
        tb_path,
    ]
    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-I",
        str(repo_root / "rtl/common"),
        "-I",
        str(repo_root / "rtl/stream"),
        "-o",
        str(simv_path),
        *[str(path) for path in sources],
    ]
    subprocess.run(compile_cmd, cwd=repo_root, check=True, capture_output=True, text=True)
    completed = subprocess.run(["vvp", str(simv_path)], cwd=repo_root, check=True, capture_output=True, text=True)
    return parse_rtl_stdout(completed.stdout)


def run_vector(
    *,
    key: bytes,
    nonce: bytes,
    associated_data: bytes,
    plaintext: bytes,
    repo_root: Path = REPO_ROOT,
    workdir: Path | None = None,
    dry_run: bool = False,
    keep_temp: bool = False,
) -> ComparisonResult:
    golden = build_golden_vector(key, nonce, associated_data, plaintext)
    tb = generate_testbench(golden)
    sim = simulator_available()
    if dry_run:
        return ComparisonResult(golden=golden, rtl=None, matched=None, simulator=sim)
    if sim is None:
        raise RuntimeError("iverilog and vvp are required for RTL simulation; use --dry-run for golden data only")

    if workdir is None:
        with tempfile.TemporaryDirectory(prefix="ascon_stream_encrypt_sim_") as tmp:
            rtl = run_iverilog_simulation(repo_root, tb, Path(tmp))
    else:
        workdir.mkdir(parents=True, exist_ok=True)
        rtl = run_iverilog_simulation(repo_root, tb, workdir)
        if not keep_temp:
            # Keep explicit work directories intact by default in failure analysis; remove only generated simulator binary.
            pass

    matched = (
        rtl.error == 0
        and rtl.error_code == 0
        and rtl.ciphertext_hex == golden.ciphertext_hex
        and rtl.tag_hex == golden.tag_hex
    )
    return ComparisonResult(golden=golden, rtl=rtl, matched=matched, simulator=sim)


def result_to_jsonable(result: ComparisonResult) -> dict[str, object]:
    payload = asdict(result)
    if result.rtl is not None:
        payload["rtl"]["stdout"] = result.rtl.stdout.splitlines()  # type: ignore[index]
    return payload


def default_hex(length: int, start: int = 0) -> str:
    return bytes((start + index) & 0xFF for index in range(length)).hex()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-hex", default=default_hex(16, 0), help="16-byte key as hex; default: 000102...0f")
    parser.add_argument("--nonce-hex", default=default_hex(16, 16), help="16-byte nonce as hex; default: 101112...1f")
    parser.add_argument("--ad-hex", default="", help="associated data bytes as hex")
    parser.add_argument("--plaintext-hex", default="", help="plaintext bytes as hex")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="repository root containing rtl/")
    parser.add_argument("--workdir", type=Path, default=None, help="directory for generated simulation files")
    parser.add_argument("--dry-run", action="store_true", help="emit the golden vector JSON without running a simulator")
    parser.add_argument("--keep-temp", action="store_true", help="keep generated files when --workdir is supplied")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        key = parse_hex_bytes(args.key_hex, field="--key-hex", expected_len=16)
        nonce = parse_hex_bytes(args.nonce_hex, field="--nonce-hex", expected_len=16)
        associated_data = parse_hex_bytes(args.ad_hex, field="--ad-hex")
        plaintext = parse_hex_bytes(args.plaintext_hex, field="--plaintext-hex")
        result = run_vector(
            key=key,
            nonce=nonce,
            associated_data=associated_data,
            plaintext=plaintext,
            repo_root=args.repo_root.resolve(),
            workdir=args.workdir,
            dry_run=args.dry_run,
            keep_temp=args.keep_temp,
        )
    except Exception as exc:  # pragma: no cover - exercised through CLI failures.
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result_to_jsonable(result), indent=2, sort_keys=True))
    if result.matched is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
