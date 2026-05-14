// Generated Ascon permutation helpers. Include inside a module or package scope.

// Generated Ascon constant-addition layer p_C.

// Ascon round constants const0..const15
localparam [63:0] ASCON_CONST_00 = 64'h0000_0000_0000_003C;
localparam [63:0] ASCON_CONST_01 = 64'h0000_0000_0000_002D;
localparam [63:0] ASCON_CONST_02 = 64'h0000_0000_0000_001E;
localparam [63:0] ASCON_CONST_03 = 64'h0000_0000_0000_000F;
localparam [63:0] ASCON_CONST_04 = 64'h0000_0000_0000_00F0;
localparam [63:0] ASCON_CONST_05 = 64'h0000_0000_0000_00E1;
localparam [63:0] ASCON_CONST_06 = 64'h0000_0000_0000_00D2;
localparam [63:0] ASCON_CONST_07 = 64'h0000_0000_0000_00C3;
localparam [63:0] ASCON_CONST_08 = 64'h0000_0000_0000_00B4;
localparam [63:0] ASCON_CONST_09 = 64'h0000_0000_0000_00A5;
localparam [63:0] ASCON_CONST_10 = 64'h0000_0000_0000_0096;
localparam [63:0] ASCON_CONST_11 = 64'h0000_0000_0000_0087;
localparam [63:0] ASCON_CONST_12 = 64'h0000_0000_0000_0078;
localparam [63:0] ASCON_CONST_13 = 64'h0000_0000_0000_0069;
localparam [63:0] ASCON_CONST_14 = 64'h0000_0000_0000_005A;
localparam [63:0] ASCON_CONST_15 = 64'h0000_0000_0000_004B;

function [63:0] ascon_round_constant;
  input [3:0] const_index;
  begin
    case (const_index)
      4'd0: ascon_round_constant = 64'h0000_0000_0000_003C;
      4'd1: ascon_round_constant = 64'h0000_0000_0000_002D;
      4'd2: ascon_round_constant = 64'h0000_0000_0000_001E;
      4'd3: ascon_round_constant = 64'h0000_0000_0000_000F;
      4'd4: ascon_round_constant = 64'h0000_0000_0000_00F0;
      4'd5: ascon_round_constant = 64'h0000_0000_0000_00E1;
      4'd6: ascon_round_constant = 64'h0000_0000_0000_00D2;
      4'd7: ascon_round_constant = 64'h0000_0000_0000_00C3;
      4'd8: ascon_round_constant = 64'h0000_0000_0000_00B4;
      4'd9: ascon_round_constant = 64'h0000_0000_0000_00A5;
      4'd10: ascon_round_constant = 64'h0000_0000_0000_0096;
      4'd11: ascon_round_constant = 64'h0000_0000_0000_0087;
      4'd12: ascon_round_constant = 64'h0000_0000_0000_0078;
      4'd13: ascon_round_constant = 64'h0000_0000_0000_0069;
      4'd14: ascon_round_constant = 64'h0000_0000_0000_005A;
      4'd15: ascon_round_constant = 64'h0000_0000_0000_004B;
      default: ascon_round_constant = 64'h0000_0000_0000_0000;
    endcase
  end
endfunction

function [319:0] ascon_p_c;
  input [319:0] state;
  input [3:0]   const_index;
  reg [63:0] x0;
  reg [63:0] x1;
  reg [63:0] x2;
  reg [63:0] x3;
  reg [63:0] x4;
  begin
    x0 = state[63:0];
    x1 = state[127:64];
    x2 = state[191:128] ^ ascon_round_constant(const_index);
    x3 = state[255:192];
    x4 = state[319:256];
    ascon_p_c = {x4, x3, x2, x1, x0};
  end
endfunction

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

// Generated Ascon linear diffusion layer p_L.

function [63:0] ascon_rotr64;
  input [63:0] x;
  input [5:0]  amount;
  begin
    ascon_rotr64 = (x >> amount) | (x << (6'd64 - amount));
  end
endfunction

function [319:0] ascon_p_l;
  input [319:0] state;
  reg [63:0] x0;
  reg [63:0] x1;
  reg [63:0] x2;
  reg [63:0] x3;
  reg [63:0] x4;
  begin
    x0 = state[63:0];
    x1 = state[127:64];
    x2 = state[191:128];
    x3 = state[255:192];
    x4 = state[319:256];
    x0 = x0 ^ ascon_rotr64(x0, 6'd19) ^ ascon_rotr64(x0, 6'd28);
    x1 = x1 ^ ascon_rotr64(x1, 6'd61) ^ ascon_rotr64(x1, 6'd39);
    x2 = x2 ^ ascon_rotr64(x2, 6'd1)  ^ ascon_rotr64(x2, 6'd6);
    x3 = x3 ^ ascon_rotr64(x3, 6'd10) ^ ascon_rotr64(x3, 6'd17);
    x4 = x4 ^ ascon_rotr64(x4, 6'd7)  ^ ascon_rotr64(x4, 6'd41);
    ascon_p_l = {x4, x3, x2, x1, x0};
  end
endfunction

// Generated Ascon round composition.

function [319:0] ascon_round_const_index;
  input [319:0] state;
  input [3:0]   const_index;
  begin
    ascon_round_const_index = ascon_p_l(ascon_p_s(ascon_p_c(state, const_index)));
  end
endfunction

// Generated Ascon-p[6] function.

function [319:0] ascon_p6;
  input [319:0] state;
  reg [319:0] s;
  integer i;
  begin
    s = state;
    for (i = 10; i < 16; i = i + 1) begin
      s = ascon_round_const_index(s, i[3:0]);
    end
    ascon_p6 = s;
  end
endfunction

// Generated Ascon-p[8] function.

function [319:0] ascon_p8;
  input [319:0] state;
  reg [319:0] s;
  integer i;
  begin
    s = state;
    for (i = 8; i < 16; i = i + 1) begin
      s = ascon_round_const_index(s, i[3:0]);
    end
    ascon_p8 = s;
  end
endfunction

// Generated Ascon-p[12] function.

function [319:0] ascon_p12;
  input [319:0] state;
  reg [319:0] s;
  integer i;
  begin
    s = state;
    for (i = 4; i < 16; i = i + 1) begin
      s = ascon_round_const_index(s, i[3:0]);
    end
    ascon_p12 = s;
  end
endfunction
