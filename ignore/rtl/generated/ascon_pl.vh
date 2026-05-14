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
