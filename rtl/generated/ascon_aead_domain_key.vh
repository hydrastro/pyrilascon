// Generated Ascon AEAD domain/key helpers.

function [319:0] ascon_aead_domain_separator;
  input [319:0] state;
  begin
    // S <- S xor (0^319 || 1): toggle logical bit S[319] = state[319].
    ascon_aead_domain_separator = state ^ {1'b1, 319'b0};
  end
endfunction

// Generated Ascon AEAD key helpers. Include inside a module or package scope.

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
