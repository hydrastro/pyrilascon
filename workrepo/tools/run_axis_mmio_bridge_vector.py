#!/usr/bin/env python3
"""Generate and optionally run a behavioral simulation for ascon_axis_mmio_bridge.

This tool verifies the firmware-facing MMIO bridge contract independently from
ASCON crypto logic.  It is intentionally small: the generated testbench performs
one TX transaction and one RX transaction through the bridge register map.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

DATA_BYTES = 16

TX_DATA0 = 0x00
TX_DATA1 = 0x04
TX_DATA2 = 0x08
TX_DATA3 = 0x0C
TX_KEEP = 0x10
TX_USER = 0x14
TX_CTRL = 0x18
STATUS = 0x1C
RX_DATA0 = 0x20
RX_DATA1 = 0x24
RX_DATA2 = 0x28
RX_DATA3 = 0x2C
RX_KEEP = 0x30
RX_USER = 0x34
RX_CTRL = 0x38

TX_CTRL_VALID = 0x1
TX_CTRL_LAST = 0x2
RX_CTRL_POP = 0x1


@dataclass(frozen=True)
class BridgeVector:
    tx_payload_hex: str
    tx_keep_hex: str
    tx_user_hex: str
    tx_last: bool
    rx_payload_hex: str
    rx_keep_hex: str
    rx_user_hex: str
    rx_last: bool


@dataclass(frozen=True)
class BridgeSimResult:
    tx_payload_hex: str
    tx_keep_hex: str
    tx_user_hex: str
    tx_last: bool
    rx_payload_hex: str
    rx_keep_hex: str
    rx_user_hex: str
    rx_last: bool
    status_before_pop_hex: str
    status_after_pop_hex: str
    error: int
    stdout: list[str]


@dataclass(frozen=True)
class BridgeRunResult:
    vector: BridgeVector
    rtl: BridgeSimResult | None
    matched: bool | None
    simulator: str | None
    testbench: str | None = None


def _bytes_to_words_le(data: bytes) -> list[int]:
    padded = data + bytes(max(0, DATA_BYTES - len(data)))
    padded = padded[:DATA_BYTES]
    return [int.from_bytes(padded[i : i + 4], "little") for i in range(0, DATA_BYTES, 4)]


def _bytes_to_verilog_128(data: bytes) -> str:
    padded = data + bytes(max(0, DATA_BYTES - len(data)))
    padded = padded[:DATA_BYTES]
    return f"128'h{int.from_bytes(padded, 'little'):032x}"


def make_vector(
    *,
    tx_payload: bytes,
    tx_user: int,
    tx_last: bool,
    rx_payload: bytes,
    rx_user: int,
    rx_last: bool,
) -> BridgeVector:
    if len(tx_payload) > DATA_BYTES or len(rx_payload) > DATA_BYTES:
        raise ValueError("bridge vectors are one AXI beat; payload length must be <= 16 bytes")
    tx_keep = (1 << len(tx_payload)) - 1 if tx_payload else 0
    rx_keep = (1 << len(rx_payload)) - 1 if rx_payload else 0
    return BridgeVector(
        tx_payload_hex=tx_payload.hex(),
        tx_keep_hex=f"{tx_keep:04x}",
        tx_user_hex=f"{tx_user & 0xf:x}",
        tx_last=tx_last,
        rx_payload_hex=rx_payload.hex(),
        rx_keep_hex=f"{rx_keep:04x}",
        rx_user_hex=f"{rx_user & 0xf:x}",
        rx_last=rx_last,
    )


def generate_testbench(vector: BridgeVector) -> str:
    tx_payload = bytes.fromhex(vector.tx_payload_hex)
    rx_payload = bytes.fromhex(vector.rx_payload_hex)
    tx_words = _bytes_to_words_le(tx_payload)
    tx_keep = int(vector.tx_keep_hex, 16)
    tx_user = int(vector.tx_user_hex, 16)
    tx_last_bit = 1 if vector.tx_last else 0
    rx_keep = int(vector.rx_keep_hex, 16)
    rx_user = int(vector.rx_user_hex, 16)
    rx_last_bit = 1 if vector.rx_last else 0
    rx_data_lit = _bytes_to_verilog_128(rx_payload)

    return f'''`timescale 1ns/1ps

module tb_ascon_axis_mmio_bridge;
  reg clk = 1'b0;
  always #5 clk = ~clk;

  reg rstn = 1'b0;
  reg bus_valid = 1'b0;
  reg bus_write = 1'b0;
  reg [7:0] bus_addr = 8'h00;
  reg [31:0] bus_wdata = 32'h00000000;
  reg [3:0] bus_wstrb = 4'hf;
  wire [31:0] bus_rdata;
  wire bus_ready;

  wire [127:0] m_axis_tdata;
  wire [15:0] m_axis_tkeep;
  wire m_axis_tvalid;
  reg m_axis_tready = 1'b0;
  wire m_axis_tlast;
  wire [3:0] m_axis_tuser;

  reg [127:0] s_axis_tdata = 128'h0;
  reg [15:0] s_axis_tkeep = 16'h0000;
  reg s_axis_tvalid = 1'b0;
  wire s_axis_tready;
  reg s_axis_tlast = 1'b0;
  reg [3:0] s_axis_tuser = 4'h0;

  wire error;
  reg [31:0] read_value = 32'h00000000;
  reg [31:0] status_before_pop = 32'h00000000;
  reg [31:0] status_after_pop = 32'h00000000;

  ascon_axis_mmio_bridge dut (
    .clk_i(clk),
    .rstn_i(rstn),
    .bus_valid_i(bus_valid),
    .bus_write_i(bus_write),
    .bus_addr_i(bus_addr),
    .bus_wdata_i(bus_wdata),
    .bus_wstrb_i(bus_wstrb),
    .bus_rdata_o(bus_rdata),
    .bus_ready_o(bus_ready),
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tkeep(m_axis_tkeep),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),
    .m_axis_tlast(m_axis_tlast),
    .m_axis_tuser(m_axis_tuser),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tkeep(s_axis_tkeep),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tlast(s_axis_tlast),
    .s_axis_tuser(s_axis_tuser),
    .error_o(error)
  );

  task mmio_write;
    input [7:0] addr;
    input [31:0] data;
    begin
      @(negedge clk);
      bus_addr = addr;
      bus_wdata = data;
      bus_wstrb = 4'hf;
      bus_write = 1'b1;
      bus_valid = 1'b1;
      @(negedge clk);
      bus_valid = 1'b0;
      bus_write = 1'b0;
      bus_addr = 8'h00;
      bus_wdata = 32'h00000000;
    end
  endtask

  task mmio_read;
    input [7:0] addr;
    output [31:0] data;
    begin
      @(negedge clk);
      bus_addr = addr;
      bus_write = 1'b0;
      bus_valid = 1'b1;
      @(posedge clk);
      data = bus_rdata;
      @(negedge clk);
      bus_valid = 1'b0;
      bus_addr = 8'h00;
    end
  endtask

  integer timeout;

  initial begin
    repeat (4) @(negedge clk);
    rstn = 1'b1;
    repeat (2) @(negedge clk);

    mmio_write(8'h00, 32'h{tx_words[0]:08x});
    mmio_write(8'h04, 32'h{tx_words[1]:08x});
    mmio_write(8'h08, 32'h{tx_words[2]:08x});
    mmio_write(8'h0c, 32'h{tx_words[3]:08x});
    mmio_write(8'h10, 32'h{tx_keep:08x});
    mmio_write(8'h14, 32'h{tx_user:08x});
    mmio_write(8'h18, 32'h{(TX_CTRL_VALID | (TX_CTRL_LAST if vector.tx_last else 0)):08x});

    // Hold ready low long enough to prove the bridge preserves the TX beat.
    repeat (3) @(negedge clk);
    if (!m_axis_tvalid) begin
      $display("FAIL no_tx_valid_while_waiting");
      $finish;
    end
    m_axis_tready = 1'b1;
    @(posedge clk);
    if (m_axis_tvalid && m_axis_tready) begin
      $display("TX_BEAT data=%032x keep=%04x last=%0d user=%0x", m_axis_tdata, m_axis_tkeep, m_axis_tlast, m_axis_tuser);
    end else begin
      $display("FAIL no_tx_handshake");
      $finish;
    end
    @(negedge clk);
    m_axis_tready = 1'b0;

    // Drive one RX beat into the bridge and then read it through MMIO.
    s_axis_tdata = {rx_data_lit};
    s_axis_tkeep = 16'h{rx_keep:04x};
    s_axis_tuser = 4'h{rx_user:x};
    s_axis_tlast = 1'b{rx_last_bit};
    s_axis_tvalid = 1'b1;
    timeout = 0;
    while (!s_axis_tready && timeout < 20) begin
      @(negedge clk);
      timeout = timeout + 1;
    end
    @(posedge clk);
    if (s_axis_tvalid && s_axis_tready) begin
      $display("RX_ACCEPT data=%032x keep=%04x last=%0d user=%0x", s_axis_tdata, s_axis_tkeep, s_axis_tlast, s_axis_tuser);
    end else begin
      $display("FAIL no_rx_accept");
      $finish;
    end
    @(negedge clk);
    s_axis_tvalid = 1'b0;

    mmio_read(8'h1c, status_before_pop);
    mmio_read(8'h20, read_value); $display("RX_WORD0 data=%08x", read_value);
    mmio_read(8'h24, read_value); $display("RX_WORD1 data=%08x", read_value);
    mmio_read(8'h28, read_value); $display("RX_WORD2 data=%08x", read_value);
    mmio_read(8'h2c, read_value); $display("RX_WORD3 data=%08x", read_value);
    mmio_read(8'h30, read_value); $display("RX_KEEP keep=%04x", read_value[15:0]);
    mmio_read(8'h34, read_value); $display("RX_USER user=%0x", read_value[3:0]);
    $display("STATUS_BEFORE_POP status=%08x", status_before_pop);
    mmio_write(8'h38, 32'h00000001);
    mmio_read(8'h1c, status_after_pop);
    $display("STATUS_AFTER_POP status=%08x", status_after_pop);
    $display("DONE error=%0d", error);
    $finish;
  end
endmodule
'''


def parse_stdout(stdout: str) -> BridgeSimResult:
    fields: dict[str, str | int | bool | list[str]] = {
        "stdout": [line for line in stdout.splitlines() if line.strip()],
    }
    rx_words: dict[int, int] = {}
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("TX_BEAT "):
            parts = dict(part.split("=", 1) for part in line.split()[1:])
            data = int(parts["data"], 16).to_bytes(DATA_BYTES, "big")[::-1]
            keep = int(parts["keep"], 16)
            payload = bytes(data[i] for i in range(DATA_BYTES) if (keep >> i) & 1)
            fields["tx_payload_hex"] = payload.hex()
            fields["tx_keep_hex"] = f"{keep:04x}"
            fields["tx_user_hex"] = parts["user"].lower()
            fields["tx_last"] = parts["last"] == "1"
        elif line.startswith("RX_WORD"):
            label, value = line.split(" ", 1)
            index = int(label.removeprefix("RX_WORD"))
            rx_words[index] = int(value.split("=", 1)[1], 16)
        elif line.startswith("RX_KEEP "):
            fields["rx_keep_hex"] = f"{int(line.split('=', 1)[1], 16):04x}"
        elif line.startswith("RX_USER "):
            fields["rx_user_hex"] = line.split("=", 1)[1].lower()
        elif line.startswith("STATUS_BEFORE_POP "):
            fields["status_before_pop_hex"] = line.split("=", 1)[1].lower()
        elif line.startswith("STATUS_AFTER_POP "):
            fields["status_after_pop_hex"] = line.split("=", 1)[1].lower()
        elif line.startswith("DONE "):
            fields["error"] = int(line.split("=", 1)[1])
        elif line.startswith("FAIL "):
            raise RuntimeError(line)

    if len(rx_words) == 4 and "rx_keep_hex" in fields:
        data = b"".join(rx_words[i].to_bytes(4, "little") for i in range(4))
        keep = int(str(fields["rx_keep_hex"]), 16)
        payload = bytes(data[i] for i in range(DATA_BYTES) if (keep >> i) & 1)
        fields["rx_payload_hex"] = payload.hex()
    status = int(str(fields.get("status_before_pop_hex", "0")), 16)
    fields["rx_last"] = bool(status & 0x4)

    required = [
        "tx_payload_hex",
        "tx_keep_hex",
        "tx_user_hex",
        "tx_last",
        "rx_payload_hex",
        "rx_keep_hex",
        "rx_user_hex",
        "rx_last",
        "status_before_pop_hex",
        "status_after_pop_hex",
        "error",
        "stdout",
    ]
    missing = [name for name in required if name not in fields]
    if missing:
        raise RuntimeError(f"simulation output missing fields: {missing}; stdout={stdout}")

    return BridgeSimResult(**{name: fields[name] for name in required})  # type: ignore[arg-type]


def run_iverilog(repo_root: Path, testbench: str, workdir: Path) -> BridgeSimResult:
    tb_path = workdir / "tb_ascon_axis_mmio_bridge.v"
    out_path = workdir / "tb_ascon_axis_mmio_bridge.vvp"
    tb_path.write_text(testbench, encoding="utf-8")
    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-I",
        str(repo_root / "rtl" / "common"),
        "-o",
        str(out_path),
        str(repo_root / "rtl" / "common" / "ascon_axis_mmio_bridge.v"),
        str(tb_path),
    ]
    subprocess.run(compile_cmd, cwd=repo_root, check=True, capture_output=True, text=True)
    completed = subprocess.run(["vvp", str(out_path)], cwd=repo_root, check=True, capture_output=True, text=True)
    return parse_stdout(completed.stdout)


def run_vector(*, repo_root: Path, dry_run: bool, vector: BridgeVector) -> BridgeRunResult:
    tb = generate_testbench(vector)
    if dry_run or shutil.which("iverilog") is None or shutil.which("vvp") is None:
        return BridgeRunResult(vector=vector, rtl=None, matched=None, simulator=shutil.which("iverilog"), testbench=tb)
    with tempfile.TemporaryDirectory(prefix="ascon_axis_mmio_bridge_sim_") as tmp:
        rtl = run_iverilog(repo_root, tb, Path(tmp))
    matched = (
        rtl.tx_payload_hex == vector.tx_payload_hex
        and rtl.tx_keep_hex == vector.tx_keep_hex
        and rtl.tx_user_hex == vector.tx_user_hex
        and rtl.tx_last == vector.tx_last
        and rtl.rx_payload_hex == vector.rx_payload_hex
        and rtl.rx_keep_hex == vector.rx_keep_hex
        and rtl.rx_user_hex == vector.rx_user_hex
        and rtl.rx_last == vector.rx_last
        and int(rtl.status_before_pop_hex, 16) & 0x2 != 0
        and int(rtl.status_after_pop_hex, 16) & 0x2 == 0
        and rtl.error == 0
    )
    return BridgeRunResult(vector=vector, rtl=rtl, matched=matched, simulator=shutil.which("iverilog"))


def result_to_jsonable(result: BridgeRunResult) -> dict[str, object]:
    return {
        "vector": asdict(result.vector),
        "rtl": None if result.rtl is None else asdict(result.rtl),
        "matched": result.matched,
        "simulator": result.simulator,
        "testbench": result.testbench,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tx-payload-hex", default="000102030405060708090a0b0c0d0e0f")
    parser.add_argument("--tx-user", type=lambda s: int(s, 0), default=2)
    parser.add_argument("--tx-last", action="store_true", default=True)
    parser.add_argument("--rx-payload-hex", default="a0a1a2a3a4")
    parser.add_argument("--rx-user", type=lambda s: int(s, 0), default=2)
    parser.add_argument("--rx-last", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    vector = make_vector(
        tx_payload=bytes.fromhex(args.tx_payload_hex),
        tx_user=args.tx_user,
        tx_last=args.tx_last,
        rx_payload=bytes.fromhex(args.rx_payload_hex),
        rx_user=args.rx_user,
        rx_last=args.rx_last,
    )
    result = run_vector(repo_root=args.repo_root, dry_run=args.dry_run, vector=vector)
    payload = result_to_jsonable(result)
    if args.json or args.dry_run:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
        if result.matched is not True:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
