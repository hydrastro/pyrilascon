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
