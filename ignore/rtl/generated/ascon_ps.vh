// Generated Ascon substitution layer p_S.

function [4:0] ascon_sbox5_lut;
  input [4:0] x;
  begin
    case (x)
      5'h00: ascon_sbox5_lut = 5'h04;
      5'h01: ascon_sbox5_lut = 5'h0B;
      5'h02: ascon_sbox5_lut = 5'h1F;
      5'h03: ascon_sbox5_lut = 5'h14;
      5'h04: ascon_sbox5_lut = 5'h1A;
      5'h05: ascon_sbox5_lut = 5'h15;
      5'h06: ascon_sbox5_lut = 5'h09;
      5'h07: ascon_sbox5_lut = 5'h02;
      5'h08: ascon_sbox5_lut = 5'h1B;
      5'h09: ascon_sbox5_lut = 5'h05;
      5'h0A: ascon_sbox5_lut = 5'h08;
      5'h0B: ascon_sbox5_lut = 5'h12;
      5'h0C: ascon_sbox5_lut = 5'h1D;
      5'h0D: ascon_sbox5_lut = 5'h03;
      5'h0E: ascon_sbox5_lut = 5'h06;
      5'h0F: ascon_sbox5_lut = 5'h1C;
      5'h10: ascon_sbox5_lut = 5'h1E;
      5'h11: ascon_sbox5_lut = 5'h13;
      5'h12: ascon_sbox5_lut = 5'h07;
      5'h13: ascon_sbox5_lut = 5'h0E;
      5'h14: ascon_sbox5_lut = 5'h00;
      5'h15: ascon_sbox5_lut = 5'h0D;
      5'h16: ascon_sbox5_lut = 5'h11;
      5'h17: ascon_sbox5_lut = 5'h18;
      5'h18: ascon_sbox5_lut = 5'h10;
      5'h19: ascon_sbox5_lut = 5'h0C;
      5'h1A: ascon_sbox5_lut = 5'h01;
      5'h1B: ascon_sbox5_lut = 5'h19;
      5'h1C: ascon_sbox5_lut = 5'h16;
      5'h1D: ascon_sbox5_lut = 5'h0A;
      5'h1E: ascon_sbox5_lut = 5'h0F;
      5'h1F: ascon_sbox5_lut = 5'h17;
      default: ascon_sbox5_lut = 5'h00;
    endcase
  end
endfunction

function [319:0] ascon_p_s_lut;
  input [319:0] state;
  integer j;
  reg [4:0] y;
  reg [319:0] out;
  begin
    out = 320'b0;
    for (j = 0; j < 64; j = j + 1) begin
      y = ascon_sbox5_lut({state[j], state[64+j], state[128+j], state[192+j], state[256+j]});
      out[j]       = y[4];
      out[64+j]    = y[3];
      out[128+j]   = y[2];
      out[192+j]   = y[1];
      out[256+j]   = y[0];
    end
    ascon_p_s_lut = out;
  end
endfunction

function [319:0] ascon_p_s_bitsliced;
  input [319:0] state;
  reg [63:0] x0;
  reg [63:0] x1;
  reg [63:0] x2;
  reg [63:0] x3;
  reg [63:0] x4;
  reg [63:0] y0;
  reg [63:0] y1;
  reg [63:0] y2;
  reg [63:0] y3;
  reg [63:0] y4;
  begin
    x0 = state[63:0];
    x1 = state[127:64];
    x2 = state[191:128];
    x3 = state[255:192];
    x4 = state[319:256];
    y0 = (x4 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ (x1 & x0) ^ x1 ^ x0;
    y1 = x4 ^ (x3 & x2) ^ (x3 & x1) ^ x3 ^ (x2 & x1) ^ x2 ^ x1 ^ x0;
    y2 = (x4 & x3) ^ x4 ^ x2 ^ x1 ^ 64'hFFFF_FFFF_FFFF_FFFF;
    y3 = (x4 & x0) ^ x4 ^ (x3 & x0) ^ x3 ^ x2 ^ x1 ^ x0;
    y4 = (x4 & x1) ^ x4 ^ x3 ^ (x1 & x0) ^ x1;
    ascon_p_s_bitsliced = {y4, y3, y2, y1, y0};
  end
endfunction

function [319:0] ascon_p_s;
  input [319:0] state;
  begin
    // Default RTL view: direct bitsliced boolean network.
    ascon_p_s = ascon_p_s_bitsliced(state);
  end
endfunction
