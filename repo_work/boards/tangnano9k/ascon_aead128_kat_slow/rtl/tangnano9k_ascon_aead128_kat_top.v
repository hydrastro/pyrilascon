module tangnano9k_ascon_aead128_kat_top(
  input  wire clk,
  input  wire rst_n,
  output wire [5:0] led
);
  reg [24:0] heartbeat_q;
  wire busy_w;
  wire done_w;
  wire pass_w;
  wire fail_w;
  wire activity_w;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      heartbeat_q <= 25'b0;
    end else begin
      heartbeat_q <= heartbeat_q + 25'd1;
    end
  end

  ascon_aead128_kat_slow_core u_core(
    .clk(clk),
    .rst_n(rst_n),
    .busy_o(busy_w),
    .done_o(done_w),
    .pass_o(pass_w),
    .fail_o(fail_w),
    .activity_o(activity_w)
  );

  // Tang Nano 9K LEDs are active low.
  assign led[0] = ~heartbeat_q[24];
  assign led[1] = ~pass_w;
  assign led[2] = ~fail_w;
  assign led[3] = ~busy_w;
  assign led[4] = ~done_w;
  assign led[5] = ~(pass_w & done_w & ~fail_w);
endmodule
