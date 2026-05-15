// Generated Ascon AEAD domain separator helper.

function [319:0] ascon_aead_domain_separator;
  input [319:0] state;
  begin
    // S <- S xor (0^319 || 1): toggle logical bit S[319] = state[319].
    ascon_aead_domain_separator = state ^ {1'b1, 319'b0};
  end
endfunction
