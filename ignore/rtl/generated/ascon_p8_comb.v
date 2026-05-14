`include "ascon_model.vh"

module ascon_p8_comb(
  input  wire [319:0] state_i,
  output wire [319:0] state_o
);
  assign state_o = ascon_p8(state_i);
endmodule
