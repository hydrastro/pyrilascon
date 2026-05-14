`include "ascon_model.vh"

module ascon_permutation_comb(
  input  wire [319:0] state_i,
  input  wire [1:0]   rounds_i, // 0:p6, 1:p8, 2:p12
  output reg  [319:0] state_o
);
  always @* begin
    case (rounds_i)
      2'd0: state_o = ascon_p6(state_i);
      2'd1: state_o = ascon_p8(state_i);
      2'd2: state_o = ascon_p12(state_i);
      default: state_o = 320'b0;
    endcase
  end
endmodule
