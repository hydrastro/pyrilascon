// Full Ascon-AEAD128 fixed-vector decryption KAT core.
// Plaintext is kept internal until the computed authentication tag matches.
module ascon_aead128_decrypt_kat_core(
  input  wire clk,
  input  wire rst_n,
  output reg  busy_o,
  output reg  done_o,
  output reg  pass_o,
  output reg  fail_o,
  output reg  activity_o
);
  localparam [63:0]  IV            = 64'h0000_1000_808c_0001;
  localparam [127:0] KEY           = 128'h0f0e0d0c0b0a09080706050403020100;
  localparam [127:0] NONCE         = 128'h1f1e1d1c1b1a19181716151413121110;
  localparam [127:0] AD_PAD        = 128'h00000000000000000000013332314441;
  localparam [127:0] CT_FULL       = 128'h359947c8b877a859abebb16de8e5d595;
  localparam [79:0]  CT_FINAL      = 80'he3ad96765b1455538ea8;
  localparam [207:0] PT_EXPECTED   = 208'h6c65646f6d206572617764726168204e4f435341206f6c6c6568;
  localparam [127:0] TAG_EXPECTED  = 128'h91fadaf6ab4ff8091f10d2dfab66db04;

  localparam [3:0] ST_INIT_LOAD    = 4'd0;
  localparam [3:0] ST_INIT_P12     = 4'd1;
  localparam [3:0] ST_INIT_KEY     = 4'd2;
  localparam [3:0] ST_AD_XOR       = 4'd3;
  localparam [3:0] ST_AD_P8        = 4'd4;
  localparam [3:0] ST_DOMAIN       = 4'd5;
  localparam [3:0] ST_CT_FULL      = 4'd6;
  localparam [3:0] ST_CT_P8        = 4'd7;
  localparam [3:0] ST_CT_FINAL     = 4'd8;
  localparam [3:0] ST_FINAL_KEY    = 4'd9;
  localparam [3:0] ST_FINAL_P12    = 4'd10;
  localparam [3:0] ST_CHECK        = 4'd11;
  localparam [3:0] ST_DONE         = 4'd12;

  reg [3:0] state_q;
  reg [319:0] s_q;
  reg [3:0] rc_index_q;
  reg [207:0] pt_buffer_q;
  reg [127:0] tag_q;
  reg plaintext_release_q;

  wire [7:0] rc_w;
  wire [319:0] round_state_w;
  wire [127:0] pt_full_w;
  wire [79:0] pt_final_w;
  wire [319:0] state_after_full_ct_w;
  wire [319:0] state_after_final_ct_w;
  wire [127:0] tag_calc_w;
  wire [127:0] tag_diff_w;
  wire tag_match_w;

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

  assign rc_w = round_constant(rc_index_q);
  assign pt_full_w = s_q[127:0] ^ CT_FULL;
  assign pt_final_w = s_q[79:0] ^ CT_FINAL;
  assign state_after_full_ct_w = {s_q[319:128], CT_FULL};
  // Final partial decryption update: replace valid ciphertext bytes, then toggle the pad bit.
  assign state_after_final_ct_w = {s_q[319:81], s_q[80] ^ 1'b1, CT_FINAL};
  assign tag_calc_w = round_state_w[319:192] ^ KEY;
  assign tag_diff_w = tag_q ^ TAG_EXPECTED;
  assign tag_match_w = ~|tag_diff_w;

  ascon_round_comb u_round(
    .state_i(s_q),
    .rc_i(rc_w),
    .state_o(round_state_w)
  );

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_q <= ST_INIT_LOAD;
      s_q <= 320'b0;
      rc_index_q <= 4'd0;
      pt_buffer_q <= 208'b0;
      tag_q <= 128'b0;
      plaintext_release_q <= 1'b0;
      busy_o <= 1'b0;
      done_o <= 1'b0;
      pass_o <= 1'b0;
      fail_o <= 1'b0;
      activity_o <= 1'b0;
    end else begin
      activity_o <= 1'b0;
      case (state_q)
        ST_INIT_LOAD: begin
          s_q <= {NONCE[127:64], NONCE[63:0], KEY[127:64], KEY[63:0], IV};
          rc_index_q <= 4'd4;
          pt_buffer_q <= 208'b0;
          plaintext_release_q <= 1'b0;
          busy_o <= 1'b1;
          done_o <= 1'b0;
          pass_o <= 1'b0;
          fail_o <= 1'b0;
          state_q <= ST_INIT_P12;
        end

        ST_INIT_P12: begin
          s_q <= round_state_w;
          activity_o <= 1'b1;
          if (rc_index_q == 4'd15) state_q <= ST_INIT_KEY;
          else rc_index_q <= rc_index_q + 4'd1;
        end

        ST_INIT_KEY: begin
          s_q <= s_q ^ {KEY, 192'b0};
          state_q <= ST_AD_XOR;
        end

        ST_AD_XOR: begin
          s_q <= s_q ^ {192'b0, AD_PAD};
          rc_index_q <= 4'd8;
          state_q <= ST_AD_P8;
        end

        ST_AD_P8: begin
          s_q <= round_state_w;
          activity_o <= 1'b1;
          if (rc_index_q == 4'd15) state_q <= ST_DOMAIN;
          else rc_index_q <= rc_index_q + 4'd1;
        end

        ST_DOMAIN: begin
          s_q <= s_q ^ {1'b1, 319'b0};
          state_q <= ST_CT_FULL;
        end

        ST_CT_FULL: begin
          // Full-block decryption: P_i = S_r xor C_i, then S_r = C_i.
          pt_buffer_q[127:0] <= pt_full_w;
          s_q <= state_after_full_ct_w;
          rc_index_q <= 4'd8;
          state_q <= ST_CT_P8;
        end

        ST_CT_P8: begin
          s_q <= round_state_w;
          activity_o <= 1'b1;
          if (rc_index_q == 4'd15) state_q <= ST_CT_FINAL;
          else rc_index_q <= rc_index_q + 4'd1;
        end

        ST_CT_FINAL: begin
          // Final partial block: buffer plaintext internally; do not release it yet.
          pt_buffer_q[207:128] <= pt_final_w;
          s_q <= state_after_final_ct_w;
          state_q <= ST_FINAL_KEY;
        end

        ST_FINAL_KEY: begin
          s_q <= s_q ^ {64'b0, KEY, 128'b0};
          rc_index_q <= 4'd4;
          state_q <= ST_FINAL_P12;
        end

        ST_FINAL_P12: begin
          s_q <= round_state_w;
          activity_o <= 1'b1;
          if (rc_index_q == 4'd15) begin
            tag_q <= tag_calc_w;
            state_q <= ST_CHECK;
          end else begin
            rc_index_q <= rc_index_q + 4'd1;
          end
        end

        ST_CHECK: begin
          if (tag_match_w && (pt_buffer_q == PT_EXPECTED)) begin
            plaintext_release_q <= 1'b1;
            pass_o <= 1'b1;
            fail_o <= 1'b0;
          end else begin
            plaintext_release_q <= 1'b0;
            pt_buffer_q <= 208'b0;
            pass_o <= 1'b0;
            fail_o <= 1'b1;
          end
          done_o <= 1'b1;
          busy_o <= 1'b0;
          state_q <= ST_DONE;
        end

        ST_DONE: begin
          done_o <= 1'b1;
          busy_o <= 1'b0;
        end

        default: state_q <= ST_INIT_LOAD;
      endcase
    end
  end
endmodule
