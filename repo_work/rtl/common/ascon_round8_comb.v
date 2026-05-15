`ifndef ASCON_ROUND8_COMB_V
`define ASCON_ROUND8_COMB_V

// Eight-round combinational Ascon slice.
//
// round_count_i selects whether the slice applies four or eight rounds:
//   round_count_i = 4  -> constants rc_start_i .. rc_start_i+3
//   round_count_i = 8  -> constants rc_start_i .. rc_start_i+7
//
// This supports the 8-rounds-per-cycle FPGA candidate:
//   p8  = one cycle  with rc_start_i=8,  round_count_i=8
//   p12 = two cycles: rc_start_i=4,  round_count_i=8
//                    rc_start_i=12, round_count_i=4
module ascon_round8_comb(
  input  wire [319:0] state_i,
  input  wire [3:0]   rc_start_i,
  input  wire [3:0]   round_count_i,
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
  wire [319:0] s4_w;
  wire [319:0] s5_w;
  wire [319:0] s6_w;
  wire [319:0] s7_w;
  wire [319:0] s8_w;

  ascon_round_comb r0_i(.state_i(state_i), .rc_i(round_constant(rc_start_i)),          .state_o(s1_w));
  ascon_round_comb r1_i(.state_i(s1_w),    .rc_i(round_constant(rc_start_i + 4'd1)),  .state_o(s2_w));
  ascon_round_comb r2_i(.state_i(s2_w),    .rc_i(round_constant(rc_start_i + 4'd2)),  .state_o(s3_w));
  ascon_round_comb r3_i(.state_i(s3_w),    .rc_i(round_constant(rc_start_i + 4'd3)),  .state_o(s4_w));
  ascon_round_comb r4_i(.state_i(s4_w),    .rc_i(round_constant(rc_start_i + 4'd4)),  .state_o(s5_w));
  ascon_round_comb r5_i(.state_i(s5_w),    .rc_i(round_constant(rc_start_i + 4'd5)),  .state_o(s6_w));
  ascon_round_comb r6_i(.state_i(s6_w),    .rc_i(round_constant(rc_start_i + 4'd6)),  .state_o(s7_w));
  ascon_round_comb r7_i(.state_i(s7_w),    .rc_i(round_constant(rc_start_i + 4'd7)),  .state_o(s8_w));

  assign state_o = (round_count_i == 4'd4) ? s4_w : s8_w;
endmodule

`endif
