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
