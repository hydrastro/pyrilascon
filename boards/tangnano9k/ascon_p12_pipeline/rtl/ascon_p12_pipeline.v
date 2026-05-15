// SPDX-License-Identifier: MIT
// 12-stage fully-pipelined Ascon-p[12] permutation.
// One 320-bit permutation result is produced per clock after the 12-cycle fill.

module ascon_p12_pipeline(
  input  wire         clk,
  input  wire         rst,
  input  wire         valid_i,
  input  wire [319:0] state_i,
  output wire         valid_o,
  output wire [319:0] state_o
);
  wire [319:0] r0_o;
  wire [319:0] r1_o;
  wire [319:0] r2_o;
  wire [319:0] r3_o;
  wire [319:0] r4_o;
  wire [319:0] r5_o;
  wire [319:0] r6_o;
  wire [319:0] r7_o;
  wire [319:0] r8_o;
  wire [319:0] r9_o;
  wire [319:0] r10_o;
  wire [319:0] r11_o;

  reg [319:0] s1;
  reg [319:0] s2;
  reg [319:0] s3;
  reg [319:0] s4;
  reg [319:0] s5;
  reg [319:0] s6;
  reg [319:0] s7;
  reg [319:0] s8;
  reg [319:0] s9;
  reg [319:0] s10;
  reg [319:0] s11;
  reg [319:0] s12;
  reg [11:0]  valid_pipe;

  // Ascon-p[12] uses round constants const4..const15.
  ascon_round_comb #(.ROUND_CONST(8'hF0)) u_round_00 (.state_i(state_i), .state_o(r0_o));
  ascon_round_comb #(.ROUND_CONST(8'hE1)) u_round_01 (.state_i(s1),     .state_o(r1_o));
  ascon_round_comb #(.ROUND_CONST(8'hD2)) u_round_02 (.state_i(s2),     .state_o(r2_o));
  ascon_round_comb #(.ROUND_CONST(8'hC3)) u_round_03 (.state_i(s3),     .state_o(r3_o));
  ascon_round_comb #(.ROUND_CONST(8'hB4)) u_round_04 (.state_i(s4),     .state_o(r4_o));
  ascon_round_comb #(.ROUND_CONST(8'hA5)) u_round_05 (.state_i(s5),     .state_o(r5_o));
  ascon_round_comb #(.ROUND_CONST(8'h96)) u_round_06 (.state_i(s6),     .state_o(r6_o));
  ascon_round_comb #(.ROUND_CONST(8'h87)) u_round_07 (.state_i(s7),     .state_o(r7_o));
  ascon_round_comb #(.ROUND_CONST(8'h78)) u_round_08 (.state_i(s8),     .state_o(r8_o));
  ascon_round_comb #(.ROUND_CONST(8'h69)) u_round_09 (.state_i(s9),     .state_o(r9_o));
  ascon_round_comb #(.ROUND_CONST(8'h5A)) u_round_10 (.state_i(s10),    .state_o(r10_o));
  ascon_round_comb #(.ROUND_CONST(8'h4B)) u_round_11 (.state_i(s11),    .state_o(r11_o));

  always @(posedge clk) begin
    if (rst) begin
      s1 <= 320'b0;
      s2 <= 320'b0;
      s3 <= 320'b0;
      s4 <= 320'b0;
      s5 <= 320'b0;
      s6 <= 320'b0;
      s7 <= 320'b0;
      s8 <= 320'b0;
      s9 <= 320'b0;
      s10 <= 320'b0;
      s11 <= 320'b0;
      s12 <= 320'b0;
      valid_pipe <= 12'b0;
    end else begin
      s1 <= r0_o;
      s2 <= r1_o;
      s3 <= r2_o;
      s4 <= r3_o;
      s5 <= r4_o;
      s6 <= r5_o;
      s7 <= r6_o;
      s8 <= r7_o;
      s9 <= r8_o;
      s10 <= r9_o;
      s11 <= r10_o;
      s12 <= r11_o;
      valid_pipe <= {valid_pipe[10:0], valid_i};
    end
  end

  assign valid_o = valid_pipe[11];
  assign state_o = s12;
endmodule
