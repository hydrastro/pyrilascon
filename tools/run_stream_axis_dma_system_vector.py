#!/usr/bin/env python3
"""Generate and optionally run a full stream-AEAD + descriptor-DMA RTL vector.

The generated testbench drives ``ascon_accel_stream_aead128_axis_dma_system``
exactly the way the NEORV32 firmware will: it programs the frozen ASCON CSR ABI
(key/nonce/lengths/CONTROL.START), then programs the DMA descriptor window
(source/destination addresses, lengths, CTRL.GO), and finally waits for the DMA
``DONE`` and CSR ``DONE`` before reading the ciphertext back *from memory* and
the tag from the CSR.

A small synchronous memory model is instantiated on the DMA master port.  It is
preloaded with the associated data and plaintext at their descriptor addresses;
the DMA fetches them, feeds the streaming backend, drains the ciphertext beats,
and writes them to the destination region.  The check therefore proves the
complete autonomous encrypt path end to end: descriptor programming, AD and
plaintext fetch, stream encryption, ciphertext write-back, and tag capture, all
without the CPU touching a single payload beat.

Unlike the CPU-driven AXI-MMIO smoke vector, the DMA path is not limited by the
bridge RX FIFO depth: the ciphertext is streamed to memory beat by beat, so this
runner exercises multi-beat associated data and plaintext as well.
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
ASCON_MODE_AEAD128 = 0x0

# Descriptor memory layout (byte addresses, 4-byte aligned, disjoint regions).
AD_BASE_BYTES = 0x00000000
TEXT_BASE_BYTES = 0x00000800
DST_BASE_BYTES = 0x00001000
MEM_WORDS = 2048  # 8 KiB backing store, covers the three regions above.

# CSR register offsets (frozen ABI).
CSR_CONTROL = 0x00
CSR_STATUS = 0x04
CSR_MODE = 0x08
CSR_AD_LEN = 0x10
CSR_TEXT_LEN = 0x14
CSR_KEY0 = 0x20
CSR_NONCE0 = 0x30
CSR_TAG0 = 0x60
CSR_ERROR_CODE = 0x78

CSR_CONTROL_START = 0x00000001
CSR_CONTROL_CLEAR = 0x00000100
CSR_STATUS_DONE = 0x00000002
CSR_STATUS_ERROR = 0x00000008

# DMA descriptor register offsets.
DMA_AD_ADDR = 0x00
DMA_AD_LEN = 0x04
DMA_TEXT_ADDR = 0x08
DMA_TEXT_LEN = 0x0C
DMA_DST_ADDR = 0x10
DMA_CTRL = 0x14
DMA_STATUS = 0x18
DMA_OUT_BYTES = 0x1C

DMA_CTRL_GO = 0x00000001
DMA_CTRL_IRQ_EN = 0x00000100
DMA_CTRL_CLEAR = 0x00010000
DMA_STATUS_BUSY = 0x00000001
DMA_STATUS_DONE = 0x00000002
DMA_STATUS_ERROR = 0x00000004


@dataclass(frozen=True)
class GoldenDmaVector:
    key_hex: str
    nonce_hex: str
    associated_data_hex: str
    plaintext_hex: str
    ciphertext_hex: str
    tag_hex: str
    ad_words: list[int]
    plaintext_words: list[int]


@dataclass(frozen=True)
class RtlDmaResult:
    ciphertext_hex: str
    tag_hex: str
    dma_status_hex: str
    dma_out_bytes: int
    csr_status_hex: str
    error_code: int
    cycles: int
    stdout: str


@dataclass(frozen=True)
class DmaComparisonResult:
    golden: GoldenDmaVector
    rtl: RtlDmaResult | None
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


def bytes_to_words_le(data: bytes) -> list[int]:
    """Pack bytes into little-endian 32-bit words, zero padding the tail."""
    padded = data + b"\x00" * ((-len(data)) % 4)
    return [int.from_bytes(padded[i : i + 4], "little") for i in range(0, len(padded), 4)]


def words_to_bytes_le(words: list[int], byte_count: int) -> bytes:
    raw = b"".join((word & 0xFFFFFFFF).to_bytes(4, "little") for word in words)
    return raw[:byte_count]


def build_golden_vector(key: bytes, nonce: bytes, associated_data: bytes, plaintext: bytes) -> GoldenDmaVector:
    if len(plaintext) > 1024:
        raise ValueError("plaintext is limited to the backend MAX_TEXT_BYTES (1024)")
    if DST_BASE_BYTES + len(plaintext) > MEM_WORDS * 4:
        raise ValueError("destination region overflows the test memory model")
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
    return GoldenDmaVector(
        key_hex=key.hex(),
        nonce_hex=nonce.hex(),
        associated_data_hex=associated_data.hex(),
        plaintext_hex=plaintext.hex(),
        ciphertext_hex=golden.ciphertext.hex(),
        tag_hex=golden.tag.hex(),
        ad_words=bytes_to_words_le(associated_data),
        plaintext_words=bytes_to_words_le(plaintext),
    )


def _word_literals_for_16_bytes(data_hex: str) -> list[str]:
    data = bytes.fromhex(data_hex)
    if len(data) != 16:
        raise ValueError("expected 16 bytes")
    return [f"32'h{int.from_bytes(data[i:i+4], 'little'):08x}" for i in range(0, 16, 4)]


def _preload_lines(words: list[int], base_byte: int) -> str:
    base_word = base_byte // 4
    if not words:
        return "    // (empty region)"
    return "\n".join(f"    mem[{base_word + i}] = 32'h{word:08x};" for i, word in enumerate(words))


def generate_testbench(vector: GoldenDmaVector, *, timeout_cycles: int = 20000) -> str:
    key_words = _word_literals_for_16_bytes(vector.key_hex)
    nonce_words = _word_literals_for_16_bytes(vector.nonce_hex)
    ad_len = len(bytes.fromhex(vector.associated_data_hex))
    text_len = len(bytes.fromhex(vector.plaintext_hex))
    dst_word_count = (text_len + 3) // 4
    dst_base_word = DST_BASE_BYTES // 4

    ad_preload = _preload_lines(vector.ad_words, AD_BASE_BYTES)
    pt_preload = _preload_lines(vector.plaintext_words, TEXT_BASE_BYTES)

    dump_lines = "\n".join(
        f'    $display("OUT_DST idx=%0d data=%08x", {k}, mem[{dst_base_word + k}]);'
        for k in range(dst_word_count)
    )
    dump_body = dump_lines if dump_lines else "    // Zero-length plaintext: no ciphertext words."

    return f"""`timescale 1ns/1ps

module tb_ascon_stream_axis_dma_system;
  localparam integer ADDR_WORD_BITS = 14;
  localparam integer MEM_WORDS = {MEM_WORDS};

  reg clk_i = 1'b0;
  reg rstn_i = 1'b0;

  // CSR window.
  reg csr_bus_valid = 1'b0;
  reg csr_bus_write = 1'b0;
  reg [7:0] csr_bus_addr = 8'h00;
  reg [31:0] csr_bus_wdata = 32'h00000000;
  reg [3:0] csr_bus_wstrb = 4'hf;
  wire [31:0] csr_bus_rdata;
  wire csr_bus_ready;

  // DMA descriptor window.
  reg dma_bus_valid = 1'b0;
  reg dma_bus_write = 1'b0;
  reg [7:0] dma_bus_addr = 8'h00;
  reg [31:0] dma_bus_wdata = 32'h00000000;
  reg [3:0] dma_bus_wstrb = 4'hf;
  wire [31:0] dma_bus_rdata;
  wire dma_bus_ready;

  // DMA system-memory master port.
  wire mem_req_valid;
  wire mem_req_we;
  wire [ADDR_WORD_BITS-1:0] mem_req_addr;
  wire [31:0] mem_req_wdata;
  wire [3:0] mem_req_wstrb;
  wire mem_req_ready;
  wire mem_rsp_valid;
  wire [31:0] mem_rsp_rdata;

  wire csr_irq;
  wire dma_irq;
  wire dma_busy;
  wire dma_done;
  wire dma_error;

  reg [31:0] read_value = 32'h00000000;
  reg [31:0] dma_status = 32'h00000000;
  reg [31:0] dma_out_bytes = 32'h00000000;
  reg [31:0] csr_status = 32'h00000000;
  reg [31:0] error_code = 32'h00000000;
  reg [31:0] tag0 = 32'h00000000;
  reg [31:0] tag1 = 32'h00000000;
  reg [31:0] tag2 = 32'h00000000;
  reg [31:0] tag3 = 32'h00000000;
  integer cycle_count = 0;
  integer guard = 0;
  integer mi = 0;

  ascon_accel_stream_aead128_axis_dma_system #(
    .ADDR_WORD_BITS(ADDR_WORD_BITS)
  ) dut (
    .clk_i(clk_i),
    .rstn_i(rstn_i),
    .csr_bus_valid_i(csr_bus_valid),
    .csr_bus_write_i(csr_bus_write),
    .csr_bus_addr_i(csr_bus_addr),
    .csr_bus_wdata_i(csr_bus_wdata),
    .csr_bus_wstrb_i(csr_bus_wstrb),
    .csr_bus_rdata_o(csr_bus_rdata),
    .csr_bus_ready_o(csr_bus_ready),
    .dma_bus_valid_i(dma_bus_valid),
    .dma_bus_write_i(dma_bus_write),
    .dma_bus_addr_i(dma_bus_addr),
    .dma_bus_wdata_i(dma_bus_wdata),
    .dma_bus_wstrb_i(dma_bus_wstrb),
    .dma_bus_rdata_o(dma_bus_rdata),
    .dma_bus_ready_o(dma_bus_ready),
    .mem_req_valid_o(mem_req_valid),
    .mem_req_we_o(mem_req_we),
    .mem_req_addr_o(mem_req_addr),
    .mem_req_wdata_o(mem_req_wdata),
    .mem_req_wstrb_o(mem_req_wstrb),
    .mem_req_ready_i(mem_req_ready),
    .mem_rsp_valid_i(mem_rsp_valid),
    .mem_rsp_rdata_i(mem_rsp_rdata),
    .csr_irq_o(csr_irq),
    .dma_irq_o(dma_irq),
    .dma_busy_o(dma_busy),
    .dma_done_o(dma_done),
    .dma_error_o(dma_error)
  );

  // -------------------------------------------------------------------------
  // Synchronous system-memory model: always accepts a request; read data is
  // returned registered one cycle after acceptance (single outstanding read);
  // writes honour the per-byte strobe.
  // -------------------------------------------------------------------------
  reg [31:0] mem [0:MEM_WORDS-1];
  reg        mem_rsp_valid_q = 1'b0;
  reg [31:0] mem_rsp_rdata_q = 32'h00000000;

  assign mem_req_ready = 1'b1;
  assign mem_rsp_valid = mem_rsp_valid_q;
  assign mem_rsp_rdata = mem_rsp_rdata_q;

  always @(posedge clk_i) begin
    mem_rsp_valid_q <= 1'b0;
    if (mem_req_valid && mem_req_ready) begin
      if (mem_req_we) begin
        if (mem_req_wstrb[0]) mem[mem_req_addr[10:0]][7:0]   <= mem_req_wdata[7:0];
        if (mem_req_wstrb[1]) mem[mem_req_addr[10:0]][15:8]  <= mem_req_wdata[15:8];
        if (mem_req_wstrb[2]) mem[mem_req_addr[10:0]][23:16] <= mem_req_wdata[23:16];
        if (mem_req_wstrb[3]) mem[mem_req_addr[10:0]][31:24] <= mem_req_wdata[31:24];
      end else begin
        mem_rsp_rdata_q <= mem[mem_req_addr[10:0]];
        mem_rsp_valid_q <= 1'b1;
      end
    end
  end

  initial begin
    for (mi = 0; mi < MEM_WORDS; mi = mi + 1) mem[mi] = 32'h00000000;
    // Associated data region.
{ad_preload}
    // Plaintext region.
{pt_preload}
  end

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

  task dma_write;
    input [7:0] addr;
    input [31:0] data;
    begin
      @(negedge clk_i);
      dma_bus_addr = addr;
      dma_bus_wdata = data;
      dma_bus_wstrb = 4'hf;
      dma_bus_write = 1'b1;
      dma_bus_valid = 1'b1;
      @(negedge clk_i);
      dma_bus_valid = 1'b0;
      dma_bus_write = 1'b0;
      dma_bus_addr = 8'h00;
      dma_bus_wdata = 32'h00000000;
    end
  endtask

  task dma_read;
    input [7:0] addr;
    output [31:0] data;
    begin
      @(negedge clk_i);
      dma_bus_addr = addr;
      dma_bus_write = 1'b0;
      dma_bus_valid = 1'b1;
      @(posedge clk_i);
      data = dma_bus_rdata;
      @(negedge clk_i);
      dma_bus_valid = 1'b0;
      dma_bus_addr = 8'h00;
    end
  endtask

  task wait_dma_done;
    begin
      guard = 0;
      dma_read(8'h{DMA_STATUS:02x}, read_value);
      while ((read_value & 32'h{DMA_STATUS_DONE:08x}) == 32'h00000000) begin
        guard = guard + 1;
        if (guard > {timeout_cycles}) begin
          $display("TIMEOUT wait_dma_done status=%08x cycle=%0d", read_value, cycle_count);
          $finish;
        end
        dma_read(8'h{DMA_STATUS:02x}, read_value);
      end
      dma_status = read_value;
    end
  endtask

  task wait_csr_done;
    begin
      guard = 0;
      csr_read(8'h{CSR_STATUS:02x}, read_value);
      while ((read_value & 32'h{CSR_STATUS_DONE:08x}) == 32'h00000000) begin
        guard = guard + 1;
        if (guard > {timeout_cycles}) begin
          $display("TIMEOUT wait_csr_done status=%08x cycle=%0d", read_value, cycle_count);
          $finish;
        end
        csr_read(8'h{CSR_STATUS:02x}, read_value);
      end
      csr_status = read_value;
    end
  endtask

  initial begin
    repeat (5) @(negedge clk_i);
    rstn_i = 1'b1;
    repeat (3) @(negedge clk_i);

    // ---- Program the frozen CSR control plane and start the backend. ----
    csr_write(8'h{CSR_CONTROL:02x}, 32'h{CSR_CONTROL_CLEAR:08x});
    csr_write(8'h{CSR_MODE:02x}, 32'h{ASCON_MODE_AEAD128:08x});
    csr_write(8'h{CSR_AD_LEN:02x}, 32'd{ad_len});
    csr_write(8'h{CSR_TEXT_LEN:02x}, 32'd{text_len});
    csr_write(8'h{CSR_KEY0 + 0x0:02x}, {key_words[0]});
    csr_write(8'h{CSR_KEY0 + 0x4:02x}, {key_words[1]});
    csr_write(8'h{CSR_KEY0 + 0x8:02x}, {key_words[2]});
    csr_write(8'h{CSR_KEY0 + 0xC:02x}, {key_words[3]});
    csr_write(8'h{CSR_NONCE0 + 0x0:02x}, {nonce_words[0]});
    csr_write(8'h{CSR_NONCE0 + 0x4:02x}, {nonce_words[1]});
    csr_write(8'h{CSR_NONCE0 + 0x8:02x}, {nonce_words[2]});
    csr_write(8'h{CSR_NONCE0 + 0xC:02x}, {nonce_words[3]});
    csr_write(8'h{CSR_CONTROL:02x}, 32'h{CSR_CONTROL_START:08x});

    // ---- Program the DMA descriptor and launch the autonomous transfer. ----
    dma_write(8'h{DMA_CTRL:02x}, 32'h{DMA_CTRL_CLEAR:08x});
    dma_write(8'h{DMA_AD_ADDR:02x}, 32'h{AD_BASE_BYTES:08x});
    dma_write(8'h{DMA_AD_LEN:02x}, 32'd{ad_len});
    dma_write(8'h{DMA_TEXT_ADDR:02x}, 32'h{TEXT_BASE_BYTES:08x});
    dma_write(8'h{DMA_TEXT_LEN:02x}, 32'd{text_len});
    dma_write(8'h{DMA_DST_ADDR:02x}, 32'h{DST_BASE_BYTES:08x});
    dma_write(8'h{DMA_CTRL:02x}, 32'h{DMA_CTRL_GO:08x});

    wait_dma_done();
    wait_csr_done();

    dma_read(8'h{DMA_OUT_BYTES:02x}, dma_out_bytes);
    csr_read(8'h{CSR_ERROR_CODE:02x}, error_code);
    csr_read(8'h{CSR_TAG0 + 0x0:02x}, tag0);
    csr_read(8'h{CSR_TAG0 + 0x4:02x}, tag1);
    csr_read(8'h{CSR_TAG0 + 0x8:02x}, tag2);
    csr_read(8'h{CSR_TAG0 + 0xC:02x}, tag3);

{dump_body}

    $display("DMA_DONE cycle=%0d status=%08x out_bytes=%0d", cycle_count, dma_status, dma_out_bytes);
    $display("CSR_DONE status=%08x error_code=%0d tag_words=%08x,%08x,%08x,%08x", csr_status, error_code, tag0, tag1, tag2, tag3);
    $finish;
  end
endmodule
"""


def parse_rtl_stdout(stdout: str, *, text_len: int) -> RtlDmaResult:
    dst_words: dict[int, int] = {}
    dma_done: dict[str, str] | None = None
    csr_done: dict[str, str] | None = None
    for raw in stdout.splitlines():
        line = raw.strip()
        if line.startswith("OUT_DST "):
            fields = dict(part.split("=", 1) for part in line.split()[1:])
            dst_words[int(fields["idx"])] = int(fields["data"], 16)
        elif line.startswith("DMA_DONE "):
            dma_done = dict(part.split("=", 1) for part in line.split()[1:])
        elif line.startswith("CSR_DONE "):
            csr_done = dict(part.split("=", 1) for part in line.split()[1:])
        elif line.startswith("TIMEOUT "):
            raise RuntimeError(line)
    if dma_done is None or csr_done is None:
        raise RuntimeError(f"RTL simulation did not print both DONE lines. stdout:\n{stdout}")
    ordered = [dst_words[i] for i in range(len(dst_words))]
    ciphertext = words_to_bytes_le(ordered, text_len)
    tag_words = [int(word, 16) for word in csr_done["tag_words"].split(",")]
    tag = b"".join(word.to_bytes(4, "little") for word in tag_words)
    return RtlDmaResult(
        ciphertext_hex=ciphertext.hex(),
        tag_hex=tag.hex(),
        dma_status_hex=dma_done["status"],
        dma_out_bytes=int(dma_done["out_bytes"]),
        csr_status_hex=csr_done["status"],
        error_code=int(csr_done["error_code"]),
        cycles=int(dma_done["cycle"]),
        stdout=stdout,
    )


def run_iverilog_simulation(repo_root: Path, testbench: str, workdir: Path, *, text_len: int) -> RtlDmaResult:
    tb_path = workdir / "tb_ascon_stream_axis_dma_system.v"
    out_path = workdir / "tb_ascon_stream_axis_dma_system.vvp"
    tb_path.write_text(testbench, encoding="utf-8")
    sources = [
        repo_root / "rtl/common/ascon_round_comb.v",
        repo_root / "rtl/common/ascon_accel_mmio_regs.v",
        repo_root / "rtl/stream/ascon_aead128_stream_encrypt.v",
        repo_root / "rtl/stream/ascon_aead128_stream_decrypt_buffered.v",
        repo_root / "rtl/stream/ascon_aead128_stream.v",
        repo_root / "rtl/common/ascon_accel_stream_aead128_top.v",
        repo_root / "rtl/common/ascon_axis_dma.v",
        repo_root / "rtl/common/ascon_accel_stream_aead128_axis_dma_system.v",
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
    return parse_rtl_stdout(completed.stdout, text_len=text_len)


def run_vector(
    *,
    key: bytes,
    nonce: bytes,
    associated_data: bytes,
    plaintext: bytes,
    repo_root: Path,
    dry_run: bool,
    include_testbench: bool = False,
) -> DmaComparisonResult:
    golden = build_golden_vector(key, nonce, associated_data, plaintext)
    tb = generate_testbench(golden)
    if dry_run:
        return DmaComparisonResult(
            golden=golden,
            rtl=None,
            matched=None,
            simulator=None,
            testbench=tb if include_testbench else None,
        )
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        raise RuntimeError("iverilog and vvp are required unless --dry-run is used")
    with tempfile.TemporaryDirectory(prefix="ascon_stream_axis_dma_system_") as tmp:
        rtl = run_iverilog_simulation(repo_root, tb, Path(tmp), text_len=len(plaintext))
    matched = (
        rtl.ciphertext_hex == golden.ciphertext_hex
        and rtl.tag_hex == golden.tag_hex
        and rtl.error_code == 0
        and rtl.dma_out_bytes == len(plaintext)
        and (int(rtl.dma_status_hex, 16) & DMA_STATUS_DONE) != 0
        and (int(rtl.dma_status_hex, 16) & DMA_STATUS_ERROR) == 0
        and (int(rtl.csr_status_hex, 16) & CSR_STATUS_DONE) != 0
        and (int(rtl.csr_status_hex, 16) & CSR_STATUS_ERROR) == 0
    )
    return DmaComparisonResult(
        golden=golden,
        rtl=rtl,
        matched=matched,
        simulator=shutil.which("iverilog"),
        testbench=tb if include_testbench else None,
    )


def result_to_jsonable(result: DmaComparisonResult) -> dict[str, object]:
    payload = asdict(result)
    if result.rtl is not None:
        payload["rtl"]["stdout"] = result.rtl.stdout.splitlines()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-hex", "--key", dest="key", required=True, help="16-byte key as hex")
    parser.add_argument("--nonce-hex", "--nonce", dest="nonce", required=True, help="16-byte nonce as hex")
    parser.add_argument("--ad-hex", "--ad", dest="ad", default="", help="associated data as hex")
    parser.add_argument("--plaintext-hex", "--plaintext", dest="plaintext", default="", help="plaintext as hex")
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
