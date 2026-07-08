// Generated Ascon round composition.

function [319:0] ascon_round_const_index;
  input [319:0] state;
  input [3:0]   const_index;
  begin
    ascon_round_const_index = ascon_p_l(ascon_p_s(ascon_p_c(state, const_index)));
  end
endfunction
