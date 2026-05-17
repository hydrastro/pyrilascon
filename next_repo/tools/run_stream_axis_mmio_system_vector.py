#!/usr/bin/env python3
"""Generate and optionally run a full stream-AEAD + MMIO-bridge RTL smoke vector.

The generated testbench drives ``ascon_accel_stream_aead128_axis_mmio_system``
through the same two MMIO windows the NEORV32 firmware will use:

* CSR window for the frozen ASCON control/status/key/nonce/tag ABI.
* AXI-MMIO bridge window for CPU-driven 128-bit stream beats.

This is intentionally a smoke/integration test rather than a throughput test.
It validates the complete encrypt path for messages that fit in the small
AXI-MMIO bridge RX FIFO, so CSR programming, CONTROL.START sequencing, AXI
bridge TX/RX, status, and tag capture are all exercised before DMA exists.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

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
SYSTEM_RX_FIFO_DEPTH = 4
ASCON_AXIS_USER_AD = 0x1
ASCON_AXIS_USER_TEXT = 0x2
ASCON_MODE_AEAD128 = 0x0

# CSR register offsets.
CSR_CONTROL = 0x00
CSR_STATUS = 0x04
CSR_MODE = 0x08
CSR_AD_LEN = 0x10
CSR_TEXT_LEN = 0x14
CSR_KEY0 = 0x20
CSR_KEY1 = 0x24
CSR_KEY2 = 0x28
CSR_KEY3 = 0x2C
CSR_NONCE0 = 0x30
CSR_NONCE1 = 0x34
CSR_NONCE2 = 0x38
CSR_NONCE3 = 0x3C
CSR_TAG0 = 0x60
CSR_TAG1 = 0x64
CSR_TAG2 = 0x68
CSR_TAG3 = 0x6C
CSR_ERROR_CODE = 0x78

CSR_CONTROL_START = 0x00000001
CSR_STATUS_DONE = 0x00000002
CSR_STATUS_ERROR = 0x00000008

# Axis-MMIO bridge register offsets.
AXIS_TX_DATA0 = 0x00
AXIS_TX_DATA1 = 0x04
AXIS_TX_DATA2 = 0x08
AXIS_TX_DATA3 = 0x0C
AXIS_TX_KEEP = 0x10
AXIS_TX_USER = 0x14
AXIS_TX_CTRL = 0x18
AXIS_STATUS = 0x1C
AXIS_RX_DATA0 = 0x20
AXIS_RX_DATA1 = 0x24
AXIS_RX_DATA2 = 0x28
AXIS_RX_DATA3 = 0x2C
AXIS_RX_KEEP = 0x30
AXIS_RX_USER = 0x34
AXIS_RX_CTRL = 0x38

AXIS_TX_CTRL_VALID = 0x00000001
AXIS_TX_CTRL_LAST = 0x00000002
AXIS_STATUS_TX_READY = 0x00000001
AXIS_STATUS_RX_VALID = 0x00000002
AXIS_STATUS_RX_LAST = 0x00000004
AXIS_STATUS_ERROR = 0x80000000
AXIS_STATUS_RX_LEVEL_SHIFT = 8
AXIS_STATUS_RX_LEVEL_MASK = 0x0000FF00
AXIS_RX_CTRL_POP = 0x00000001


@dataclass(frozen=True)
class BeatJson:
    data_hex: str
    keep_hex: str
    last: bool
    user_hex: str
    payload_hex: str


@dataclass(frozen=True)
class GoldenSystemVector:
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
class RtlSystemResult:
    ciphertext_hex: str
    tag_hex: str
    status_hex: str
    error_code: int
    cycles: int
    rx_levels: list[int]
    stdout: str


@dataclass(frozen=True)
class SystemComparisonResult:
    golden: GoldenSystemVector
    rtl: RtlSystemResult | None
    matched: bool | None
    simulator: str | None
    testbench: str | None = None


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
        keep_hex=f"{beat.keep:04x}",
        last=beat.last,
        user_hex="1" if beat.kind == AeadStreamKind.AD else "2",
        payload_hex=beat.payload.hex(),
    )


def build_golden_vector(key: bytes, nonce: bytes, associated_data: bytes, plaintext: bytes) -> GoldenSystemVector:
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
    if len(golden.ciphertext_beats) > SYSTEM_RX_FIFO_DEPTH:
        raise ValueError(
            "integrated AXI-MMIO system vectors are limited to the bridge RX FIFO depth "
            f"({SYSTEM_RX_FIFO_DEPTH} output beats)"
        )
    return GoldenSystemVector(
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


def _word_literals_for_beat_data(data_hex: str) -> list[str]:
    data = bytes.fromhex(data_hex)
    if len(data) != DATA_BYTES:
        raise ValueError("beat data must already be padded to 16 bytes")
    return [f"32'h{int.from_bytes(data[i:i+4], 'little'):08x}" for i in range(0, DATA_BYTES, 4)]


def _word_literals_for_16_bytes(data_hex: str) -> list[str]:
    data = bytes.fromhex(data_hex)
    if len(data) != 16:
        raise ValueError("expected 16 bytes")
    return [f"32'h{int.from_bytes(data[i:i+4], 'little'):08x}" for i in range(0, 16, 4)]


def send_bridge_beat_statement(beat: BeatJson) -> str:
    words = _word_literals_for_beat_data(beat.data_hex)
    user = ASCON_AXIS_USER_AD if beat.user_hex == "1" else ASCON_AXIS_USER_TEXT
    ctrl = AXIS_TX_CTRL_VALID | (AXIS_TX_CTRL_LAST if beat.last else 0)
    return "\n".join(
        [
            f"    axis_send_beat({words[0]}, {words[1]}, {words[2]}, {words[3]}, 16'h{beat.keep_hex}, 4'h{user:x}, 32'h{ctrl:08x});"
        ]
    )


def generate_testbench(vector: GoldenSystemVector, *, timeout_cycles: int = 8000) -> str:
    key_words = _word_literals_for_16_bytes(vector.key_hex)
    nonce_words = _word_literals_for_16_bytes(vector.nonce_hex)
    ad_len = len(bytes.fromhex(vector.associated_data_hex))
    text_len = len(bytes.fromhex(vector.plaintext_hex))
    send_lines: list[str] = []
    send_lines.extend(send_bridge_beat_statement(beat) for beat in vector.ad_beats)
    send_lines.extend(send_bridge_beat_statement(beat) for beat in vector.plaintext_beats)
    send_body = "\n".join(send_lines) if send_lines else "    // Zero-length AD and plaintext: no AXI-MMIO stream beats."
    recv_lines = ["    axis_recv_beat();" for _ in vector.ciphertext_beats]
    recv_body = "\n".join(recv_lines) if recv_lines else "    // Zero-length plaintext: no output beat expected."

    return f"""`timescale 1ns/1ps

module tb_ascon_stream_axis_mmio_system;
  reg clk_i = 1'b0;
  reg rstn_i = 1'b0;

  reg csr_bus_valid = 1'b0;
  reg csr_bus_write = 1'b0;
  reg [7:0] csr_bus_addr = 8'h00;
  reg [31:0] csr_bus_wdata = 32'h00000000;
  reg [3:0] csr_bus_wstrb = 4'hf;
  wire [31:0] csr_bus_rdata;
  wire csr_bus_ready;

  reg axis_bus_valid = 1'b0;
  reg axis_bus_write = 1'b0;
  reg [7:0] axis_bus_addr = 8'h00;
  reg [31:0] axis_bus_wdata = 32'h00000000;
  reg [3:0] axis_bus_wstrb = 4'hf;
  wire [31:0] axis_bus_rdata;
  wire axis_bus_ready;

  wire irq;
  wire axis_bridge_error;

  reg [31:0] read_value = 32'h00000000;
  reg [31:0] final_status = 32'h00000000;
  reg [31:0] error_code = 32'h00000000;
  reg [31:0] tag0 = 32'h00000000;
  reg [31:0] tag1 = 32'h00000000;
  reg [31:0] tag2 = 32'h00000000;
  reg [31:0] tag3 = 32'h00000000;
  reg [127:0] rx_data = 128'h0;
  reg [15:0] rx_keep = 16'h0000;
  reg [3:0] rx_user = 4'h0;
  reg rx_last = 1'b0;
  integer cycle_count = 0;
  integer guard = 0;

  ascon_accel_stream_aead128_axis_mmio_system dut (
    .clk_i(clk_i),
    .rstn_i(rstn_i),
    .csr_bus_valid_i(csr_bus_valid),
    .csr_bus_write_i(csr_bus_write),
    .csr_bus_addr_i(csr_bus_addr),
    .csr_bus_wdata_i(csr_bus_wdata),
    .csr_bus_wstrb_i(csr_bus_wstrb),
    .csr_bus_rdata_o(csr_bus_rdata),
    .csr_bus_ready_o(csr_bus_ready),
    .axis_bus_valid_i(axis_bus_valid),
    .axis_bus_write_i(axis_bus_write),
    .axis_bus_addr_i(axis_bus_addr),
    .axis_bus_wdata_i(axis_bus_wdata),
    .axis_bus_wstrb_i(axis_bus_wstrb),
    .axis_bus_rdata_o(axis_bus_rdata),
    .axis_bus_ready_o(axis_bus_ready),
    .irq_o(irq),
    .axis_bridge_error_o(axis_bridge_error)
  );

  always #5 clk_i = ~clk_i;

  always @(posedge clk_i) begin
    cycle_count <= cycle_count + 1;
    if (cycle_count > {timeout_cycles}) begin
      $display("TIMEOUT cycle=%0d", cycle_count);
      $finish;
    end
  end

  task csr_write;
    input [7:0] addr;
    input [31:0] data;
    begin
      @(negedge clk_i);
      csr_bus_addr = addr;
      csr_bus_wdata = data;
      csr_bus_wstrb = 4'hf;
      csr_bus_write = 1'b1;
      csr_bus_valid = 1'b1;
      @(negedge clk_i);
      csr_bus_valid = 1'b0;
      csr_bus_write = 1'b0;
      csr_bus_addr = 8'h00;
      csr_bus_wdata = 32'h00000000;
    end
  endtask

  task csr_read;
    input [7:0] addr;
    output [31:0] data;
    begin
      @(negedge clk_i);
      csr_bus_addr = addr;
      csr_bus_write = 1'b0;
      csr_bus_valid = 1'b1;
      @(posedge clk_i);
      data = csr_bus_rdata;
      @(negedge clk_i);
      csr_bus_valid = 1'b0;
      csr_bus_addr = 8'h00;
    end
  endtask

  task axis_write;
    input [7:0] addr;
    input [31:0] data;
    begin
      @(negedge clk_i);
      axis_bus_addr = addr;
      axis_bus_wdata = data;
      axis_bus_wstrb = 4'hf;
      axis_bus_write = 1'b1;
      axis_bus_valid = 1'b1;
      @(negedge clk_i);
      axis_bus_valid = 1'b0;
      axis_bus_write = 1'b0;
      axis_bus_addr = 8'h00;
      axis_bus_wdata = 32'h00000000;
    end
  endtask

  task axis_read;
    input [7:0] addr;
    output [31:0] data;
    begin
      @(negedge clk_i);
      axis_bus_addr = addr;
      axis_bus_write = 1'b0;
      axis_bus_valid = 1'b1;
      @(posedge clk_i);
      data = axis_bus_rdata;
      @(negedge clk_i);
      axis_bus_valid = 1'b0;
      axis_bus_addr = 8'h00;
    end
  endtask

  task wait_axis_bits;
    input [31:0] mask;
    begin
      guard = 0;
      axis_read(8'h{AXIS_STATUS:02x}, read_value);
      while ((read_value & mask) != mask) begin
        guard = guard + 1;
        if (guard > {timeout_cycles}) begin
          $display("TIMEOUT wait_axis_bits mask=%08x status=%08x cycle=%0d", mask, read_value, cycle_count);
          $finish;
        end
        axis_read(8'h{AXIS_STATUS:02x}, read_value);
      end
    end
  endtask

  task wait_done;
    begin
      guard = 0;
      csr_read(8'h{CSR_STATUS:02x}, read_value);
      while ((read_value & 32'h{CSR_STATUS_DONE:08x}) == 32'h00000000) begin
        guard = guard + 1;
        if (guard > {timeout_cycles}) begin
          $display("TIMEOUT wait_done status=%08x cycle=%0d", read_value, cycle_count);
          $finish;
        end
        csr_read(8'h{CSR_STATUS:02x}, read_value);
      end
      final_status = read_value;
    end
  endtask

  task axis_send_beat;
    input [31:0] w0;
    input [31:0] w1;
    input [31:0] w2;
    input [31:0] w3;
    input [15:0] keep;
    input [3:0] user;
    input [31:0] ctrl;
    begin
      wait_axis_bits(32'h{AXIS_STATUS_TX_READY:08x});
      axis_write(8'h{AXIS_TX_DATA0:02x}, w0);
      axis_write(8'h{AXIS_TX_DATA1:02x}, w1);
      axis_write(8'h{AXIS_TX_DATA2:02x}, w2);
      axis_write(8'h{AXIS_TX_DATA3:02x}, w3);
      axis_write(8'h{AXIS_TX_KEEP:02x}, {{16'h0000, keep}});
      axis_write(8'h{AXIS_TX_USER:02x}, {{28'h0000000, user}});
      axis_write(8'h{AXIS_TX_CTRL:02x}, ctrl);
      $display("TX_COMMIT cycle=%0d w0=%08x w1=%08x w2=%08x w3=%08x keep=%04x user=%0h ctrl=%08x", cycle_count, w0, w1, w2, w3, keep, user, ctrl);
    end
  endtask

  task axis_recv_beat;
    reg [31:0] w0;
    reg [31:0] w1;
    reg [31:0] w2;
    reg [31:0] w3;
    reg [31:0] keep_word;
    reg [31:0] user_word;
    reg [31:0] status_word;
    begin
      wait_axis_bits(32'h{AXIS_STATUS_RX_VALID:08x});
      axis_read(8'h{AXIS_STATUS:02x}, status_word);
      axis_read(8'h{AXIS_RX_DATA0:02x}, w0);
      axis_read(8'h{AXIS_RX_DATA1:02x}, w1);
      axis_read(8'h{AXIS_RX_DATA2:02x}, w2);
      axis_read(8'h{AXIS_RX_DATA3:02x}, w3);
      axis_read(8'h{AXIS_RX_KEEP:02x}, keep_word);
      axis_read(8'h{AXIS_RX_USER:02x}, user_word);
      rx_data = {{w3, w2, w1, w0}};
      rx_keep = keep_word[15:0];
      rx_user = user_word[3:0];
      rx_last = (status_word & 32'h{AXIS_STATUS_RX_LAST:08x}) != 32'h00000000;
      $display("OUT_BEAT cycle=%0d data=%032x keep=%04x last=%0d user=%0h level=%0d", cycle_count, rx_data, rx_keep, rx_last, rx_user, status_word[15:8]);
      axis_write(8'h{AXIS_RX_CTRL:02x}, 32'h{AXIS_RX_CTRL_POP:08x});
    end
  endtask

  initial begin
    repeat (5) @(negedge clk_i);
    rstn_i = 1'b1;
    repeat (3) @(negedge clk_i);

    csr_write(8'h{CSR_CONTROL:02x}, 32'h00000100); // CLEAR
    csr_write(8'h{CSR_MODE:02x}, 32'h{ASCON_MODE_AEAD128:08x});
    csr_write(8'h{CSR_AD_LEN:02x}, 32'd{ad_len});
    csr_write(8'h{CSR_TEXT_LEN:02x}, 32'd{text_len});
    csr_write(8'h{CSR_KEY0:02x}, {key_words[0]});
    csr_write(8'h{CSR_KEY1:02x}, {key_words[1]});
    csr_write(8'h{CSR_KEY2:02x}, {key_words[2]});
    csr_write(8'h{CSR_KEY3:02x}, {key_words[3]});
    csr_write(8'h{CSR_NONCE0:02x}, {nonce_words[0]});
    csr_write(8'h{CSR_NONCE1:02x}, {nonce_words[1]});
    csr_write(8'h{CSR_NONCE2:02x}, {nonce_words[2]});
    csr_write(8'h{CSR_NONCE3:02x}, {nonce_words[3]});
    csr_write(8'h{CSR_CONTROL:02x}, 32'h{CSR_CONTROL_START:08x});

{send_body}
{recv_body}

    wait_done();
    csr_read(8'h{CSR_ERROR_CODE:02x}, error_code);
    csr_read(8'h{CSR_TAG0:02x}, tag0);
    csr_read(8'h{CSR_TAG1:02x}, tag1);
    csr_read(8'h{CSR_TAG2:02x}, tag2);
    csr_read(8'h{CSR_TAG3:02x}, tag3);
    $display("DONE cycle=%0d status=%08x error_code=%0d tag_words=%08x,%08x,%08x,%08x", cycle_count, final_status, error_code, tag0, tag1, tag2, tag3);
    $finish;
  end
endmodule
"""


def parse_rtl_stdout(stdout: str) -> RtlSystemResult:
    ciphertext = bytearray()
    rx_levels: list[int] = []
    done: dict[str, str] | None = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("OUT_BEAT "):
            fields = dict(part.split("=", 1) for part in line.split()[1:])
            data = int(fields["data"], 16).to_bytes(DATA_BYTES, "little")
            keep = int(fields["keep"], 16)
            if "level" in fields:
                rx_levels.append(int(fields["level"], 0))
            for index in range(DATA_BYTES):
                if (keep >> index) & 1:
                    ciphertext.append(data[index])
        elif line.startswith("DONE "):
            fields = dict(part.split("=", 1) for part in line.split()[1:])
            done = fields
        elif line.startswith("TIMEOUT "):
            raise RuntimeError(line)
    if done is None:
        raise RuntimeError(f"RTL simulation did not print DONE. stdout:\n{stdout}")
    tag_words = [int(word, 16) for word in done["tag_words"].split(",")]
    tag = b"".join(word.to_bytes(4, "little") for word in tag_words)
    return RtlSystemResult(
        ciphertext_hex=bytes(ciphertext).hex(),
        tag_hex=tag.hex(),
        status_hex=done["status"],
        error_code=int(done["error_code"]),
        cycles=int(done["cycle"]),
        rx_levels=rx_levels,
        stdout=stdout,
    )


def run_iverilog_simulation(repo_root: Path, testbench: str, workdir: Path) -> RtlSystemResult:
    tb_path = workdir / "tb_ascon_stream_axis_mmio_system.v"
    out_path = workdir / "tb_ascon_stream_axis_mmio_system.vvp"
    tb_path.write_text(testbench, encoding="utf-8")
    sources = [
        repo_root / "rtl/common/ascon_round_comb.v",
        repo_root / "rtl/common/ascon_accel_mmio_regs.v",
        repo_root / "rtl/stream/ascon_aead128_stream_encrypt.v",
        repo_root / "rtl/stream/ascon_aead128_stream_decrypt_buffered.v",
        repo_root / "rtl/stream/ascon_aead128_stream.v",
        repo_root / "rtl/common/ascon_accel_stream_aead128_top.v",
        repo_root / "rtl/common/ascon_axis_mmio_bridge.v",
        repo_root / "rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v",
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
        str(out_path),
        *[str(source) for source in sources],
    ]
    subprocess.run(compile_cmd, cwd=repo_root, check=True, capture_output=True, text=True)
    completed = subprocess.run(["vvp", str(out_path)], cwd=repo_root, check=True, capture_output=True, text=True)
    return parse_rtl_stdout(completed.stdout)


def run_vector(
    *,
    key: bytes,
    nonce: bytes,
    associated_data: bytes,
    plaintext: bytes,
    repo_root: Path,
    dry_run: bool,
    include_testbench: bool = False,
) -> SystemComparisonResult:
    golden = build_golden_vector(key, nonce, associated_data, plaintext)
    tb = generate_testbench(golden)
    if dry_run:
        return SystemComparisonResult(
            golden=golden,
            rtl=None,
            matched=None,
            simulator=None,
            testbench=tb if include_testbench else None,
        )
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        raise RuntimeError("iverilog and vvp are required unless --dry-run is used")
    with tempfile.TemporaryDirectory(prefix="ascon_stream_axis_mmio_system_") as tmp:
        rtl = run_iverilog_simulation(repo_root, tb, Path(tmp))
    matched = (
        rtl.ciphertext_hex == golden.ciphertext_hex
        and rtl.tag_hex == golden.tag_hex
        and rtl.error_code == 0
        and (int(rtl.status_hex, 16) & CSR_STATUS_DONE) != 0
        and (int(rtl.status_hex, 16) & CSR_STATUS_ERROR) == 0
    )
    return SystemComparisonResult(
        golden=golden,
        rtl=rtl,
        matched=matched,
        simulator=shutil.which("iverilog"),
        testbench=tb if include_testbench else None,
    )


def result_to_jsonable(result: SystemComparisonResult) -> dict[str, object]:
    payload = asdict(result)
    if result.rtl is not None:
        payload["rtl"]["stdout"] = result.rtl.stdout.splitlines()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-hex", "--key", dest="key", required=True, help="16-byte key as hex")
    parser.add_argument("--nonce-hex", "--nonce", dest="nonce", required=True, help="16-byte nonce as hex")
    parser.add_argument("--ad-hex", "--ad", dest="ad", default="", help="associated data as hex")
    parser.add_argument(
        "--plaintext-hex",
        "--plaintext",
        dest="plaintext",
        default="",
        help=f"plaintext as hex, limited to {SYSTEM_RX_FIFO_DEPTH} AXI output beats for this CPU-bridge smoke test",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-testbench", action="store_true")
    args = parser.parse_args()

    result = run_vector(
        key=parse_hex_bytes(args.key, field="key", expected_len=16),
        nonce=parse_hex_bytes(args.nonce, field="nonce", expected_len=16),
        associated_data=parse_hex_bytes(args.ad, field="ad"),
        plaintext=parse_hex_bytes(args.plaintext, field="plaintext"),
        repo_root=args.repo_root.resolve(),
        dry_run=args.dry_run,
        include_testbench=args.include_testbench,
    )
    print(json.dumps(result_to_jsonable(result), indent=2, sort_keys=True))
    return 0 if result.matched is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
