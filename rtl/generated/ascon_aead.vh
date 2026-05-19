// Generated Ascon AEAD mode encodings.
localparam [1:0] ASCON_AEAD_MODE_NIST_AEAD128 = 2'd0;
localparam [1:0] ASCON_AEAD_MODE_LEGACY_128   = 2'd1;
localparam [1:0] ASCON_AEAD_MODE_LEGACY_128A  = 2'd2;
localparam [1:0] ASCON_AEAD_MODE_LEGACY_80PQ  = 2'd3;

function [319:0] ascon_rounds;
  input [319:0] state;
  input [3:0]   rounds;
  begin
    case (rounds)
      4'd6:  ascon_rounds = ascon_p6(state);
      4'd8:  ascon_rounds = ascon_p8(state);
      4'd12: ascon_rounds = ascon_p12(state);
      default: ascon_rounds = 320'b0;
    endcase
  end
endfunction

// Generated Ascon AEAD initialization helpers.

function [319:0] ascon_aead128_initial_state;
  input [127:0] key;
  input [127:0] nonce;
  begin
    // state[63:0]=IV, state[191:64]=key, state[319:192]=nonce
    ascon_aead128_initial_state = {nonce[127:0], key[127:0], ASCON_AEAD128_IV};
  end
endfunction

function [319:0] ascon_aead128_init_finish;
  input [319:0] state_after_p12;
  input [127:0] key;
  begin
    // S <- S xor (0^192 || K), with little-endian state vector indexing.
    ascon_aead128_init_finish = state_after_p12 ^ {key[127:0], 192'b0};
  end
endfunction

// Generated Ascon AEAD associated-data helper functions.

function [319:0] ascon_aead_absorb_ad_block;
  input [319:0] state;
  input [127:0] block;
  input         rate128;
  input [3:0]   rounds;
  begin
    ascon_aead_absorb_ad_block = ascon_rounds(ascon_rate_xor(state, block, rate128), rounds);
  end
endfunction

// Generated Ascon AEAD plaintext-processing helper functions.

function [319:0] ascon_aead_encrypt_full_block_state;
  input [319:0] state;
  input [127:0] plaintext_block;
  input         rate128;
  input [3:0]   rounds;
  begin
    ascon_aead_encrypt_full_block_state = ascon_rounds(ascon_rate_xor(state, plaintext_block, rate128), rounds);
  end
endfunction

function [319:0] ascon_aead_encrypt_final_state;
  input [319:0] state;
  input [127:0] padded_final_plaintext;
  input         rate128;
  begin
    ascon_aead_encrypt_final_state = ascon_rate_xor(state, padded_final_plaintext, rate128);
  end
endfunction

// Generated Ascon AEAD ciphertext-processing helper functions.

function [319:0] ascon_aead_decrypt_full_block_state;
  input [319:0] state;
  input [127:0] ciphertext_block;
  input         rate128;
  input [3:0]   rounds;
  begin
    ascon_aead_decrypt_full_block_state = ascon_rounds(ascon_rate_replace(state, ciphertext_block, rate128), rounds);
  end
endfunction

function [127:0] ascon_aead_decrypt_full_block_plaintext;
  input [319:0] state;
  input [127:0] ciphertext_block;
  input         rate128;
  begin
    ascon_aead_decrypt_full_block_plaintext = ascon_rate_select(state, rate128) ^ ciphertext_block;
  end
endfunction

// Generated Ascon AEAD finalization helpers.

function [319:0] ascon_aead128_add_key_before_final;
  input [319:0] state;
  input [127:0] key;
  begin
    // S <- S xor (0^128 || K || 0^64), little-endian state vector indexing.
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
