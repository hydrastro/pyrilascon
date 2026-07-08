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
