`include "ascon_model.vh"

module ascon_p6_comb(
  input  wire [319:0] state_i,
  output wire [319:0] state_o
);
  assign state_o = ascon_p6(state_i);
endmodule
