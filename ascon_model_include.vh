// Generated Ascon IV model. Include inside a module or package scope.

function [63:0] ascon_iv;
  input [7:0]  v;
  input [3:0]  a;
  input [3:0]  b;
  input [15:0] t;
  input [7:0]  rate_bytes;
  begin
    // Numeric IV representation: {0^16, r/8, t, b, a, 0^8, v}
    ascon_iv = {16'h0000, rate_bytes, t, b, a, 8'h00, v};
  end
endfunction

localparam [63:0] ASCON_AEAD128_IV = 64'h0000_1000_808C_0001;
localparam [63:0] ASCON_HASH256_IV = 64'h0000_0801_00CC_0002;
localparam [63:0] ASCON_XOF128_IV = 64'h0000_0800_00CC_0003;
localparam [63:0] ASCON_CXOF128_IV = 64'h0000_0800_00CC_0004;

// Generated Ascon state helpers. Include inside a module or package scope.

function [319:0] ascon_state_pack;
  input [63:0] x0;
  input [63:0] x1;
  input [63:0] x2;
  input [63:0] x3;
  input [63:0] x4;
  begin
    // Logical Ascon mapping: x0=state[63:0], x4=state[319:256]
    ascon_state_pack = {x4, x3, x2, x1, x0};
  end
endfunction

function [63:0] ascon_state_word;
  input [319:0] state;
  input [2:0]   index;
  begin
    case (index)
      3'd0: ascon_state_word = state[63:0];
      3'd1: ascon_state_word = state[127:64];
      3'd2: ascon_state_word = state[191:128];
      3'd3: ascon_state_word = state[255:192];
      3'd4: ascon_state_word = state[319:256];
      default: ascon_state_word = 64'h0000_0000_0000_0000;
    endcase
  end
endfunction

// Generated Ascon byte-oriented auxiliary helpers.

function [63:0] ascon_pad64_partial;
  input [63:0] data;
  input [2:0]  valid_bytes;
  begin
    ascon_pad64_partial = data ^ (64'h0000_0000_0000_0001 << (valid_bytes * 8));
  end
endfunction

function [127:0] ascon_pad128_partial;
  input [127:0] data;
  input [3:0]   valid_bytes;
  begin
    ascon_pad128_partial = data ^ (128'h0000_0000_0000_0000_0000_0000_0000_0001 << (valid_bytes * 8));
  end
endfunction

// Generated Ascon permutation helpers.

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

function [63:0] ascon_rotr64;
  input [63:0] x;
  input [5:0]  amount;
  begin
    ascon_rotr64 = (x >> amount) | (x << (6'd64 - amount));
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

function [319:0] ascon_p_s;
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
    ascon_p_s = {y4, y3, y2, y1, y0};
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

function [319:0] ascon_round_const_index;
  input [319:0] state;
  input [3:0]   const_index;
  begin
    ascon_round_const_index = ascon_p_l(ascon_p_s(ascon_p_c(state, const_index)));
  end
endfunction

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

// Generated Ascon AEAD domain/key helpers.

function [319:0] ascon_aead_domain_separator;
  input [319:0] state;
  begin
    // S <- S xor (0^319 || 1): toggle logical bit S[319] = state[319].
    ascon_aead_domain_separator = state ^ {1'b1, 319'b0};
  end
endfunction

function [319:0] ascon_aead128_initial_state;
  input [127:0] key;
  input [127:0] nonce;
  begin
    ascon_aead128_initial_state = {nonce[127:64], nonce[63:0], key[127:64], key[63:0], ASCON_AEAD128_IV};
  end
endfunction

function [319:0] ascon_aead128_add_key_after_init;
  input [319:0] state;
  input [127:0] key;
  begin
    // S <- S xor (0^192 || K)
    ascon_aead128_add_key_after_init = state ^ {key[127:0], 192'b0};
  end
endfunction

function [319:0] ascon_aead128_add_key_before_final;
  input [319:0] state;
  input [127:0] key;
  begin
    // S <- S xor (0^128 || K || 0^64)
    ascon_aead128_add_key_before_final = state ^ {64'b0, key[127:0], 128'b0};
  end
endfunction

function [127:0] ascon_aead128_extract_tag;
  input [319:0] state;
  input [127:0] key;
  begin
    ascon_aead128_extract_tag = state[319:192] ^ key;
  end
endfunction