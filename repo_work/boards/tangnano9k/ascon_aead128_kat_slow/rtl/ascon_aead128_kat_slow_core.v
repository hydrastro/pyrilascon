// Full Ascon-AEAD128 fixed-vector encryption KAT core.
// This is a board bring-up core, not a streaming production interface yet.
module ascon_aead128_kat_slow_core(
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
  localparam [127:0] PT_FULL       = 128'h64726168204e4f435341206f6c6c6568;
  localparam [127:0] PT_FINAL_PAD  = 128'h0000000000016c65646f6d2065726177;
  localparam [207:0] CT_EXPECTED   = 208'he3ad96765b1455538ea8359947c8b877a859abebb16de8e5d595;
  localparam [127:0] TAG_EXPECTED  = 128'h91fadaf6ab4ff8091f10d2dfab66db04;

  localparam [3:0] ST_INIT_LOAD    = 4'd0;
  localparam [3:0] ST_INIT_P12     = 4'd1;
  localparam [3:0] ST_INIT_KEY     = 4'd2;
  localparam [3:0] ST_AD_XOR       = 4'd3;
  localparam [3:0] ST_AD_P8        = 4'd4;
  localparam [3:0] ST_DOMAIN       = 4'd5;
  localparam [3:0] ST_PT_FULL      = 4'd6;
  localparam [3:0] ST_PT_P8        = 4'd7;
  localparam [3:0] ST_PT_FINAL     = 4'd8;
  localparam [3:0] ST_FINAL_KEY    = 4'd9;
  localparam [3:0] ST_FINAL_P12    = 4'd10;
  localparam [3:0] ST_CHECK        = 4'd11;
  localparam [3:0] ST_DONE         = 4'd12;

  reg [3:0] state_q;
  reg [319:0] s_q;
  reg [3:0] rc_index_q;
  reg [207:0] ct_q;
  reg [127:0] tag_q;

  wire [7:0] rc_w;
  wire [319:0] round_state_w;
  wire [319:0] pt_full_xor_w;
  wire [319:0] pt_final_xor_w;

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
  assign pt_full_xor_w = s_q ^ {192'b0, PT_FULL};
  assign pt_final_xor_w = s_q ^ {192'b0, PT_FINAL_PAD};

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
      ct_q <= 208'b0;
      tag_q <= 128'b0;
      busy_o <= 1'b0;
      done_o <= 1'b0;
      pass_o <= 1'b0;
      fail_o <= 1'b0;
      activity_o <= 1'b0;
    end else begin
      activity_o <= 1'b0;
      case (state_q)
        ST_INIT_LOAD: begin
          // S <- IV || K || N, packed as {x4,x3,x2,x1,x0}
          s_q <= {NONCE[127:64], NONCE[63:0], KEY[127:64], KEY[63:0], IV};
          rc_index_q <= 4'd4; // p12 uses constants 4..15
          busy_o <= 1'b1;
          done_o <= 1'b0;
          pass_o <= 1'b0;
          fail_o <= 1'b0;
          state_q <= ST_INIT_P12;
        end

        ST_INIT_P12: begin
          s_q <= round_state_w;
          activity_o <= 1'b1;
          if (rc_index_q == 4'd15) begin
            state_q <= ST_INIT_KEY;
          end else begin
            rc_index_q <= rc_index_q + 4'd1;
          end
        end

        ST_INIT_KEY: begin
          // S <- S xor (0^192 || K) -> state[319:192] ^= KEY
          s_q <= s_q ^ {KEY, 192'b0};
          state_q <= ST_AD_XOR;
        end

        ST_AD_XOR: begin
          // One final padded AD block, then p8.
          s_q <= s_q ^ {192'b0, AD_PAD};
          rc_index_q <= 4'd8;
          state_q <= ST_AD_P8;
        end

        ST_AD_P8: begin
          s_q <= round_state_w;
          activity_o <= 1'b1;
          if (rc_index_q == 4'd15) begin
            state_q <= ST_DOMAIN;
          end else begin
            rc_index_q <= rc_index_q + 4'd1;
          end
        end

        ST_DOMAIN: begin
          // S <- S xor (0^319 || 1), i.e. toggle state[319].
          s_q <= s_q ^ {1'b1, 319'b0};
          state_q <= ST_PT_FULL;
        end

        ST_PT_FULL: begin
          // Full 16-byte plaintext block: S_r ^= P_i, C_i = S_r.
          s_q <= pt_full_xor_w;
          ct_q[127:0] <= pt_full_xor_w[127:0];
          rc_index_q <= 4'd8;
          state_q <= ST_PT_P8;
        end

        ST_PT_P8: begin
          s_q <= round_state_w;
          activity_o <= 1'b1;
          if (rc_index_q == 4'd15) begin
            state_q <= ST_PT_FINAL;
          end else begin
            rc_index_q <= rc_index_q + 4'd1;
          end
        end

        ST_PT_FINAL: begin
          // Final padded 10-byte plaintext block. Only 10 ciphertext bytes are emitted.
          s_q <= pt_final_xor_w;
          ct_q[207:128] <= pt_final_xor_w[79:0];
          state_q <= ST_FINAL_KEY;
        end

        ST_FINAL_KEY: begin
          // S <- S xor (0^128 || K || 0^64) -> state[255:128] ^= KEY
          s_q <= s_q ^ {64'b0, KEY, 128'b0};
          rc_index_q <= 4'd4;
          state_q <= ST_FINAL_P12;
        end

        ST_FINAL_P12: begin
          s_q <= round_state_w;
          activity_o <= 1'b1;
          if (rc_index_q == 4'd15) begin
            tag_q <= round_state_w[319:192] ^ KEY;
            state_q <= ST_CHECK;
          end else begin
            rc_index_q <= rc_index_q + 4'd1;
          end
        end

        ST_CHECK: begin
          if ((ct_q == CT_EXPECTED) && (tag_q == TAG_EXPECTED)) begin
            pass_o <= 1'b1;
            fail_o <= 1'b0;
          end else begin
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

        default: begin
          state_q <= ST_INIT_LOAD;
        end
      endcase
    end
  end
endmodule
