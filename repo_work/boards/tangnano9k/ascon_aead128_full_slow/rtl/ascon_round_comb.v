// Combinational Ascon round for the NIST little-endian state-vector convention:
// state[63:0] = x0, state[127:64] = x1, ..., state[319:256] = x4.
module ascon_round_comb(
  input  wire [319:0] state_i,
  input  wire [7:0]   rc_i,
  output wire [319:0] state_o
);
  function [63:0] rotr64;
    input [63:0] x;
    input integer n;
    begin
      rotr64 = (x >> n) | (x << (64 - n));
    end
  endfunction

  wire [63:0] x0 = state_i[63:0];
  wire [63:0] x1 = state_i[127:64];
  wire [63:0] x2 = state_i[191:128] ^ {56'b0, rc_i};
  wire [63:0] x3 = state_i[255:192];
  wire [63:0] x4 = state_i[319:256];

  // Bitsliced 5-bit S-box layer, equivalent to the 32-entry S-box table.
  wire [63:0] y0 = (x4 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ (x1 & x0) ^ x1 ^ x0;
  wire [63:0] y1 = x4 ^ (x3 & x2) ^ (x3 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ x1 ^ x0;
  wire [63:0] y2 = (x4 & x3) ^ x4 ^ x2 ^ x1 ^ 64'hffff_ffff_ffff_ffff;
  wire [63:0] y3 = (x4 & x0) ^ x4 ^ (x3 & x0) ^ x3 ^ x2 ^ x1 ^ x0;
  wire [63:0] y4 = (x4 & x1) ^ x4 ^ x3 ^ (x1 & x0) ^ x1;

  wire [63:0] z0 = y0 ^ rotr64(y0, 19) ^ rotr64(y0, 28);
  wire [63:0] z1 = y1 ^ rotr64(y1, 61) ^ rotr64(y1, 39);
  wire [63:0] z2 = y2 ^ rotr64(y2,  1) ^ rotr64(y2,  6);
  wire [63:0] z3 = y3 ^ rotr64(y3, 10) ^ rotr64(y3, 17);
  wire [63:0] z4 = y4 ^ rotr64(y4,  7) ^ rotr64(y4, 41);

  assign state_o = {z4, z3, z2, z1, z0};
endmodule
