#!/usr/bin/env python3
"""Verify the SLINK data plane end-to-end against the golden model.

Drives ascon_aead128_slink_mmio exactly as the SoC will:
  * control registers over the register interface,
  * payload as a plain word stream on the SLINK TX port,
  * ciphertext captured off the SLINK RX port.

The expected values come from ascon_hwmodel (the same model that passes the
official NIST KATs), so this is an RTL-vs-model check, not a self-consistency
check.
"""
from __future__ import annotations
import pathlib
import random
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ascon_designspace.generator.aead import emit_aead128_core
from ascon_designspace.generator.axis import emit_aead128_axis
from ascon_designspace.generator.permutation import emit_iterative_permutation
from ascon_designspace.generator.verify import ensure_model_emitted
from ascon_hwmodel.aead import ascon_aead128_encrypt, ascon_aead128_decrypt

ROOT = pathlib.Path(__file__).resolve().parents[1]
AD_MAX = MSG_MAX = 32


def lit(data: bytes, nbytes: int) -> str:
    """Verilog hex literal, little-endian -- matching _axis_hexlit in the generator."""
    v = int.from_bytes(data, "little") if data else 0
    return f"{nbytes * 8}'h{v:0{nbytes * 2}X}"


def words_le(data: bytes) -> list[int]:
    """Little-endian 32-bit words, zero-padded to a word boundary."""
    padded = data + b"\x00" * ((-len(data)) % 4)
    return [int.from_bytes(padded[i:i + 4], "little") for i in range(0, len(padded), 4)]


def build_tb(cases) -> str:
    body = []
    for i, (key, nonce, ad, msg, ct, tag, decrypt) in enumerate(cases):
        aw = words_le(ad)
        mw = words_le(msg)
        stream = aw + mw
        body.append(f"    // ---- case {i}: ad={len(ad)} msg={len(msg)} dec={int(decrypt)}")
        body.append(f"    n_stream = {len(stream)};")
        for j, w in enumerate(stream):
            body.append(f"    stream[{j}] = 32'h{w:08x};")
        body.append(
            f"    run_case({i}, {lit(key,16)}, {lit(nonce,16)}, "
            f"8'd{len(ad)}, 8'd{len(msg)}, {int(decrypt)}, "
            f"{lit(tag,16)}, {lit(ct,16)}, {len(ct)});"
        )
    calls = "\n".join(body)

    return f"""`timescale 1ns/1ps
`default_nettype none
module tb;
  reg clk = 0, rst_n = 0;
  always #5 clk = ~clk;

  reg         sel = 0, we = 0;
  reg  [7:0]  addr = 0;
  reg  [31:0] wdata = 0;
  wire [31:0] rdata;
  wire        ready;

  reg  [31:0] tx_dat = 0;
  reg         tx_val = 0;
  wire        tx_rdy;

  wire [31:0] rx_dat;
  wire        rx_val, rx_lst;
  wire [3:0]  rx_src;
  reg         rx_rdy = 1;

  integer errors = 0;
  integer n_stream;
  reg [31:0] stream [0:31];
  reg [31:0] rxbuf  [0:31];
  integer    rx_n;

  ascon_aead128_slink_mmio #(.AD_MAX({AD_MAX}), .MSG_MAX({MSG_MAX})) dut (
    .clk(clk), .rst_n(rst_n),
    .sel(sel), .we(we), .addr(addr), .wdata(wdata), .rdata(rdata), .ready(ready),
    .slink_tx_dat_i(tx_dat), .slink_tx_val_i(tx_val), .slink_tx_rdy_o(tx_rdy),
    .slink_rx_dat_o(rx_dat), .slink_rx_val_o(rx_val), .slink_rx_rdy_i(rx_rdy),
    .slink_rx_lst_o(rx_lst), .slink_rx_src_o(rx_src)
  );

  // Capture the SLINK RX stream, exactly as the DMA would.
  always @(posedge clk) begin
    if (rst_n && rx_val && rx_rdy) begin
      rxbuf[rx_n] <= rx_dat;
      rx_n <= rx_n + 1;
    end
  end

  task wr(input [7:0] a, input [31:0] d);
  begin
    @(negedge clk); sel = 1; we = 1; addr = a; wdata = d;
    @(negedge clk); sel = 0; we = 0;
  end endtask

  task rd(input [7:0] a, output [31:0] d);
  begin
    @(negedge clk); sel = 1; we = 0; addr = a;
    @(negedge clk); d = rdata; sel = 0;
  end endtask

  // Push one word onto SLINK TX, respecting back-pressure.
  task push(input [31:0] d);
  begin
    @(negedge clk); tx_dat = d; tx_val = 1;
    // wait for the shim to take it
    while (!tx_rdy) @(negedge clk);
    @(negedge clk); tx_val = 0;
  end endtask

  task run_case(input integer idx, input [127:0] key, input [127:0] nonce,
                input [7:0] adl, input [7:0] msl, input dec,
                input [127:0] exp_tag, input [127:0] exp_ct, input integer ct_len);
    integer i, guard;
    reg [31:0] st, t0, t1, t2, t3;
    reg [127:0] got_tag, got_ct;
  begin
    rx_n = 0;
    wr(8'h00, 32'h100);                     // CLEAR
    wr(8'h20, key[31:0]);   wr(8'h24, key[63:32]);
    wr(8'h28, key[95:64]);  wr(8'h2C, key[127:96]);
    wr(8'h30, nonce[31:0]); wr(8'h34, nonce[63:32]);
    wr(8'h38, nonce[95:64]);wr(8'h3C, nonce[127:96]);
    if (dec) begin
      wr(8'h60, exp_tag[31:0]);  wr(8'h64, exp_tag[63:32]);
      wr(8'h68, exp_tag[95:64]); wr(8'h6C, exp_tag[127:96]);
    end
    wr(8'h10, {{24'b0, adl}});
    wr(8'h14, {{24'b0, msl}});
    wr(8'h00, dec ? 32'h3 : 32'h1);         // START (| DECRYPT)

    for (i = 0; i < n_stream; i = i + 1) push(stream[i]);

    guard = 0;
    st = 0;
    while (!(st & 32'h2) && guard < 20000) begin
      rd(8'h04, st); guard = guard + 1;
    end
    if (guard >= 20000) begin
      $display("CASE %0d TIMEOUT (status=%h)", idx, st); errors = errors + 1;
    end else begin
      rd(8'h60, t0); rd(8'h64, t1); rd(8'h68, t2); rd(8'h6C, t3);
      got_tag = {{t3, t2, t1, t0}};
      got_ct = 128'h0;
      for (i = 0; i < 4; i = i + 1)
        if (i < ((ct_len + 3) / 4)) got_ct[32*i +: 32] = rxbuf[i];
      // compare only the bytes that matter
      for (i = 0; i < 16; i = i + 1)
        if (i >= ct_len) begin
          got_ct[8*i +: 8] = 8'h0;
        end
      if (!dec && got_tag !== exp_tag) begin
        $display("CASE %0d TAG  got=%h exp=%h", idx, got_tag, exp_tag);
        errors = errors + 1;
      end
      if (got_ct !== exp_ct) begin
        $display("CASE %0d DATA got=%h exp=%h (len=%0d)", idx, got_ct, exp_ct, ct_len);
        errors = errors + 1;
      end
      if (dec) begin
        if (!(st & 32'h4)) begin
          $display("CASE %0d TAGVALID not set on decrypt", idx);
          errors = errors + 1;
        end
      end
    end
  end endtask

  initial begin
    repeat (4) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
{calls}
    if (errors == 0) $display("PASS all cases through the SLINK data plane");
    else             $display("FAIL %0d", errors);
    $finish;
  end
endmodule
"""


def main() -> int:
    gen = ensure_model_emitted().resolve()
    rng = random.Random(20260717)

    shapes = [(0, 0), (0, 4), (4, 0), (8, 8), (0, 16), (16, 0), (3, 5),
              (16, 16), (1, 1), (0, 15), (15, 0), (7, 9)]
    cases = []
    for ad_len, msg_len in shapes:
        key = bytes(rng.getrandbits(8) for _ in range(16))
        nonce = bytes(rng.getrandbits(8) for _ in range(16))
        ad = bytes(rng.getrandbits(8) for _ in range(ad_len))
        msg = bytes(rng.getrandbits(8) for _ in range(msg_len))
        r = ascon_aead128_encrypt(key, nonce, ad, msg)
        cases.append((key, nonce, ad, msg, r.ciphertext, r.tag, False))
        # decrypt: feed the ciphertext, expect the plaintext back
        cases.append((key, nonce, ad, r.ciphertext, msg, r.tag, True))

    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        (d / "tb.v").write_text(build_tb(cases))
        (d / "perm.v").write_text(emit_iterative_permutation(1))
        (d / "core.v").write_text(emit_aead128_core(AD_MAX, MSG_MAX))
        (d / "axis.v").write_text(emit_aead128_axis(AD_MAX, MSG_MAX))
        srcs = [
            str(d / "tb.v"), str(d / "perm.v"), str(d / "core.v"), str(d / "axis.v"),
            str(ROOT / "rtl/soc/ascon_slink_shim.v"),
            str(ROOT / "rtl/soc/ascon_aead128_slink_mmio.v"),
        ]
        c = subprocess.run(["iverilog", "-g2012", "-I", str(gen), "-o", str(d / "sim"), *srcs],
                           capture_output=True, text=True)
        if c.returncode:
            print("COMPILE FAILED\n" + c.stderr[:3000])
            return 1
        r = subprocess.run(["vvp", str(d / "sim")], capture_output=True, text=True)
        print(r.stdout[-3000:])
        return 0 if "PASS" in r.stdout else 1


if __name__ == "__main__":
    raise SystemExit(main())
