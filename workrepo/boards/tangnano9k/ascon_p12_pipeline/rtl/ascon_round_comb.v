// SPDX-License-Identifier: MIT
// Combinational Ascon round for the NIST little-endian state-vector convention.
// state[ 63:  0] = x0 = S0
// state[127: 64] = x1 = S1
// state[191:128] = x2 = S2
// state[255:192] = x3 = S3
// state[319:256] = x4 = S4

module ascon_round_comb #(
  parameter [7:0] ROUND_CONST = 8'h00
)(
  input  wire [319:0] state_i,
  output wire [319:0] state_o
);
  wire [63:0] x0 = state_i[ 63:  0];
  wire [63:0] x1 = state_i[127: 64];
  wire [63:0] x2 = state_i[191:128] ^ {56'h0000_0000_0000_00, ROUND_CONST};
  wire [63:0] x3 = state_i[255:192];
  wire [63:0] x4 = state_i[319:256];

  // Parallel bitsliced 5-bit S-box, matching ascon_hwmodel.ps.p_s_bitsliced.
  wire [63:0] y0 = (x4 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ (x1 & x0) ^ x1 ^ x0;
  wire [63:0] y1 = x4 ^ (x3 & x2) ^ (x3 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ x1 ^ x0;
  wire [63:0] y2 = (x4 & x3) ^ x4 ^ x2 ^ x1 ^ 64'hffff_ffff_ffff_ffff;
  wire [63:0] y3 = (x4 & x0) ^ x4 ^ (x3 & x0) ^ x3 ^ x2 ^ x1 ^ x0;
  wire [63:0] y4 = (x4 & x1) ^ x4 ^ x3 ^ (x1 & x0) ^ x1;

  function [63:0] rotr64;
    input [63:0] value;
    input integer amount;
    begin
      rotr64 = (value >> amount) | (value << (64 - amount));
    end
  endfunction

  wire [63:0] z0 = y0 ^ rotr64(y0, 19) ^ rotr64(y0, 28);
  wire [63:0] z1 = y1 ^ rotr64(y1, 61) ^ rotr64(y1, 39);
  wire [63:0] z2 = y2 ^ rotr64(y2, 1 ) ^ rotr64(y2, 6 );
  wire [63:0] z3 = y3 ^ rotr64(y3, 10) ^ rotr64(y3, 17);
  wire [63:0] z4 = y4 ^ rotr64(y4, 7 ) ^ rotr64(y4, 41);

  assign state_o = {z4, z3, z2, z1, z0};
endmodule
