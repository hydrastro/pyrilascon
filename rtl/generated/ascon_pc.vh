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
