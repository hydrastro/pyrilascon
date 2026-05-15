// Tang Nano 9K standalone full Ascon-AEAD128 smoke test.
// Runs one fixed encryption KAT and one fixed decryption KAT in parallel.
module tangnano9k_ascon_aead128_full_slow_top(
  input  wire clk,
  input  wire rst_n,
  output wire [5:0] led
);
  reg [24:0] heartbeat_q;

  wire enc_busy_w;
  wire enc_done_w;
  wire enc_pass_w;
  wire enc_fail_w;
  wire enc_activity_w;

  wire dec_busy_w;
  wire dec_done_w;
  wire dec_pass_w;
  wire dec_fail_w;
  wire dec_activity_w;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) heartbeat_q <= 25'b0;
    else heartbeat_q <= heartbeat_q + 25'd1;
  end

  ascon_aead128_encrypt_kat_core u_encrypt_kat(
    .clk(clk),
    .rst_n(rst_n),
    .busy_o(enc_busy_w),
    .done_o(enc_done_w),
    .pass_o(enc_pass_w),
    .fail_o(enc_fail_w),
    .activity_o(enc_activity_w)
  );

  ascon_aead128_decrypt_kat_core u_decrypt_kat(
    .clk(clk),
    .rst_n(rst_n),
    .busy_o(dec_busy_w),
    .done_o(dec_done_w),
    .pass_o(dec_pass_w),
    .fail_o(dec_fail_w),
    .activity_o(dec_activity_w)
  );

  // Tang Nano 9K LEDs are active-low.
  assign led[0] = ~heartbeat_q[24];
  assign led[1] = ~enc_pass_w;
  assign led[2] = ~dec_pass_w;
  assign led[3] = ~(enc_fail_w | dec_fail_w);
  assign led[4] = ~(enc_done_w & dec_done_w);
  assign led[5] = ~(enc_pass_w & dec_pass_w & ~enc_fail_w & ~dec_fail_w);
endmodule
