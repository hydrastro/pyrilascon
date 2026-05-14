// Generated Ascon rate-lane helpers.

function [127:0] ascon_rate_select;
  input [319:0] state;
  input         rate128;
  begin
    ascon_rate_select = rate128 ? state[127:0] : {64'b0, state[63:0]};
  end
endfunction

function [319:0] ascon_rate_replace;
  input [319:0] state;
  input [127:0] block;
  input         rate128;
  begin
    ascon_rate_replace = rate128 ? {state[319:128], block[127:0]} : {state[319:64], block[63:0]};
  end
endfunction

function [319:0] ascon_rate_xor;
  input [319:0] state;
  input [127:0] block;
  input         rate128;
  begin
    ascon_rate_xor = rate128 ? (state ^ {192'b0, block[127:0]}) : (state ^ {256'b0, block[63:0]});
  end
endfunction
