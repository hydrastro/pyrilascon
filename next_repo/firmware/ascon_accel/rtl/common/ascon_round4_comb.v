`ifndef ASCON_ROUND4_COMB_V
`define ASCON_ROUND4_COMB_V

// Four consecutive Ascon rounds in one combinational step.
// This is the first high-throughput FPGA candidate permutation slice: p8 takes
// two cycles, p12 takes three cycles when driven with rc_start_i = 8/12 or 4/8/12.
module ascon_round4_comb(
  input  wire [319:0] state_i,
  input  wire [3:0]   rc_start_i,
  output wire [319:0] state_o
);
  function [7:0] round_constant;
    input [3:0] idx;
    begin
      case (idx)
        4'd0:  round_constant = 8'h3c;
        4'd1:  round_constant = 8'h2d;
        4'd2:  round_constant = 8'h1e;
        4'd3:  round_constant = 8'h0f;
        4'd4:  round_constant = 8'hf0;
        4'd5:  round_constant = 8'he1;
        4'd6:  round_constant = 8'hd2;
        4'd7:  round_constant = 8'hc3;
        4'd8:  round_constant = 8'hb4;
        4'd9:  round_constant = 8'ha5;
        4'd10: round_constant = 8'h96;
        4'd11: round_constant = 8'h87;
        4'd12: round_constant = 8'h78;
        4'd13: round_constant = 8'h69;
        4'd14: round_constant = 8'h5a;
        4'd15: round_constant = 8'h4b;
        default: round_constant = 8'h00;
      endcase
    end
  endfunction

  wire [319:0] s1_w;
  wire [319:0] s2_w;
  wire [319:0] s3_w;

  ascon_round_comb r0_i(.state_i(state_i), .rc_i(round_constant(rc_start_i)),          .state_o(s1_w));
  ascon_round_comb r1_i(.state_i(s1_w),    .rc_i(round_constant(rc_start_i + 4'd1)),  .state_o(s2_w));
  ascon_round_comb r2_i(.state_i(s2_w),    .rc_i(round_constant(rc_start_i + 4'd2)),  .state_o(s3_w));
  ascon_round_comb r3_i(.state_i(s3_w),    .rc_i(round_constant(rc_start_i + 4'd3)),  .state_o(state_o));
endmodule

`endif
