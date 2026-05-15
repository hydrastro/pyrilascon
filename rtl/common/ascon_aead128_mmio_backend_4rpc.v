`ifndef ASCON_AEAD128_MMIO_BACKEND_4RPC_V
`define ASCON_AEAD128_MMIO_BACKEND_4RPC_V

`include "ascon_accel_regs.vh"

// -----------------------------------------------------------------------------
// Four-rounds-per-cycle register-buffered Ascon-AEAD128 backend for the frozen accelerator ABI.
//
// This is the first real cryptographic backend behind the MMIO register block.
// It is deliberately conservative:
//   * NIST Ascon-AEAD128 only;
//   * four Ascon rounds per cycle;
//   * up to 32 bytes of associated data;
//   * up to 32 bytes of plaintext/ciphertext;
//   * 32-bit DATA_IN/DATA_OUT software words;
//   * decrypted plaintext is only exposed after a successful tag check.
//
// The module is intended as the bridge between the currently working standalone
// Tang Nano 9K KAT targets and the future NEORV32 CFS wrapper.  It is not the
// final high-throughput streaming FPGA architecture.
// -----------------------------------------------------------------------------
module ascon_aead128_mmio_backend_4rpc #(
  parameter integer MAX_AD_BYTES   = 32,
  parameter integer MAX_TEXT_BYTES = 32
) (
  input  wire         clk_i,
  input  wire         rstn_i,
  input  wire         start_i,
  input  wire         clear_i,
  input  wire         decrypt_i,
  input  wire [3:0]   mode_i,
  input  wire [31:0]  ad_len_i,
  input  wire [31:0]  text_len_i,
  input  wire [31:0]  out_len_i,
  input  wire [31:0]  custom_len_i,
  input  wire [127:0] key_i,
  input  wire [127:0] nonce_i,
  input  wire [127:0] expected_tag_i,
  input  wire         data_in_pulse_i,
  input  wire [31:0]  data_in_i,
  input  wire [31:0]  data_in_ctrl_i,
  input  wire         data_out_read_pulse_i,
  output reg          busy_o,
  output reg          done_o,
  output reg          tag_valid_o,
  output reg          error_o,
  output reg [31:0]   error_code_o,
  output wire [31:0]  data_out_o,
  output wire [31:0]  data_out_ctrl_o,
  output reg [127:0]  generated_tag_o
);

  localparam [63:0] IV_AEAD128 = 64'h0000_1000_808c_0001;

  localparam [4:0] ST_IDLE       = 5'd0;
  localparam [4:0] ST_INIT_P12   = 5'd1;
  localparam [4:0] ST_INIT_KEY   = 5'd2;
  localparam [4:0] ST_AD_DECIDE  = 5'd3;
  localparam [4:0] ST_AD_XOR     = 5'd4;
  localparam [4:0] ST_AD_P8      = 5'd5;
  localparam [4:0] ST_DOMAIN     = 5'd6;
  localparam [4:0] ST_TX_DECIDE  = 5'd7;
  localparam [4:0] ST_TX_FULL    = 5'd8;
  localparam [4:0] ST_TX_P8      = 5'd9;
  localparam [4:0] ST_TX_FINAL   = 5'd10;
  localparam [4:0] ST_FINAL_KEY  = 5'd11;
  localparam [4:0] ST_FINAL_P12  = 5'd12;
  localparam [4:0] ST_FINISH     = 5'd13;
  localparam [4:0] ST_ERROR      = 5'd14;

  reg [4:0]   state_q;
  reg [319:0] s_q;
  reg [3:0]   rc_index_q;
  reg [1:0]   ad_block_q;
  reg [1:0]   text_block_q;
  reg         ad_final_q;

  reg [255:0] ad_buf_q;
  reg [255:0] text_buf_q;
  reg [255:0] out_buf_q;
  reg [3:0]   ad_word_count_q;
  reg [3:0]   text_word_count_q;
  reg [3:0]   out_word_index_q;
  reg         stream_error_q;

  wire [7:0]   rc_w;
  wire [319:0] round_state_w;
  wire [1:0]   ad_full_blocks_w;
  wire [1:0]   text_full_blocks_w;
  wire [4:0]   ad_final_bytes_w;
  wire [4:0]   text_final_bytes_w;
  wire [31:0]  out_word_count_w;
  wire [127:0] current_ad_block_w;
  wire [127:0] current_text_block_w;
  wire [127:0] ad_padded_block_w;
  wire [127:0] text_padded_block_w;
  wire [127:0] byte_mask_final_w;
  wire [127:0] rate_w;
  wire [127:0] enc_full_rate_w;
  wire [127:0] dec_full_plain_w;
  wire [127:0] enc_final_rate_w;
  wire [127:0] dec_final_plain_w;
  wire [127:0] dec_final_rate_w;
  wire [127:0] tag_calc_w;
  wire [127:0] tag_diff_w;
  wire          tag_match_w;

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

  function [2:0] keep_count;
    input [3:0] keep;
    begin
      case (keep)
        4'b0000: keep_count = 3'd0;
        4'b0001: keep_count = 3'd1;
        4'b0011: keep_count = 3'd2;
        4'b0111: keep_count = 3'd3;
        4'b1111: keep_count = 3'd4;
        default: keep_count = 3'd7; // invalid/non-contiguous byte mask
      endcase
    end
  endfunction

  function [127:0] low_byte_mask;
    input [4:0] nbytes;
    integer j;
    begin
      low_byte_mask = 128'h00000000000000000000000000000000;
      for (j = 0; j < 16; j = j + 1) begin
        if (j < nbytes) begin
          low_byte_mask[j*8 +: 8] = 8'hff;
        end
      end
    end
  endfunction

  function [127:0] block_from_buf;
    input [255:0] buf;
    input [1:0]   idx;
    begin
      case (idx)
        2'd0: block_from_buf = buf[127:0];
        2'd1: block_from_buf = buf[255:128];
        default: block_from_buf = 128'h00000000000000000000000000000000;
      endcase
    end
  endfunction

  function [127:0] pad_block;
    input [127:0] block;
    input [4:0]   valid_bytes;
    begin
      pad_block = (block & low_byte_mask(valid_bytes)) ^ (128'h1 << (valid_bytes * 8));
    end
  endfunction

  function [255:0] set_output_block;
    input [255:0] old_buf;
    input [1:0]   idx;
    input [127:0] block;
    input [4:0]   valid_bytes;
    reg [127:0] masked_block;
    begin
      masked_block = block & low_byte_mask(valid_bytes);
      set_output_block = old_buf;
      case (idx)
        2'd0: set_output_block[127:0]   = (old_buf[127:0]   & ~low_byte_mask(valid_bytes)) | masked_block;
        2'd1: set_output_block[255:128] = (old_buf[255:128] & ~low_byte_mask(valid_bytes)) | masked_block;
        default: set_output_block = old_buf;
      endcase
    end
  endfunction

  function [31:0] output_word;
    input [255:0] buf;
    input [3:0] idx;
    begin
      case (idx)
        4'd0: output_word = buf[31:0];
        4'd1: output_word = buf[63:32];
        4'd2: output_word = buf[95:64];
        4'd3: output_word = buf[127:96];
        4'd4: output_word = buf[159:128];
        4'd5: output_word = buf[191:160];
        4'd6: output_word = buf[223:192];
        4'd7: output_word = buf[255:224];
        default: output_word = 32'h00000000;
      endcase
    end
  endfunction

  function [3:0] output_keep;
    input [31:0] total_len;
    input [3:0]  idx;
    reg [31:0] byte_base;
    reg [31:0] remaining;
    begin
      byte_base = {28'h0000000, idx} << 2;
      if (byte_base >= total_len) begin
        output_keep = 4'b0000;
      end else begin
        remaining = total_len - byte_base;
        if (remaining >= 4) begin
          output_keep = 4'b1111;
        end else begin
          case (remaining[2:0])
            3'd1: output_keep = 4'b0001;
            3'd2: output_keep = 4'b0011;
            3'd3: output_keep = 4'b0111;
            default: output_keep = 4'b0000;
          endcase
        end
      end
    end
  endfunction

  assign rc_w = round_constant(rc_index_q);
  assign ad_full_blocks_w = ad_len_i[5:4];
  assign text_full_blocks_w = text_len_i[5:4];
  assign ad_final_bytes_w = {1'b0, ad_len_i[3:0]};
  assign text_final_bytes_w = {1'b0, text_len_i[3:0]};
  assign out_word_count_w = (text_len_i + 32'd3) >> 2;
  assign current_ad_block_w = block_from_buf(ad_buf_q, ad_block_q);
  assign current_text_block_w = block_from_buf(text_buf_q, text_block_q);
  assign ad_padded_block_w = pad_block(current_ad_block_w, ad_final_bytes_w);
  assign text_padded_block_w = pad_block(current_text_block_w, text_final_bytes_w);
  assign byte_mask_final_w = low_byte_mask(text_final_bytes_w);
  assign rate_w = s_q[127:0];
  assign enc_full_rate_w = rate_w ^ current_text_block_w;
  assign dec_full_plain_w = rate_w ^ current_text_block_w;
  assign enc_final_rate_w = rate_w ^ text_padded_block_w;
  assign dec_final_plain_w = rate_w ^ (current_text_block_w & byte_mask_final_w);
  assign dec_final_rate_w = ((rate_w & ~byte_mask_final_w) | (current_text_block_w & byte_mask_final_w)) ^
                            (128'h1 << (text_final_bytes_w * 8));
  assign tag_calc_w = round_state_w[319:192] ^ key_i;
  assign tag_diff_w = generated_tag_o ^ expected_tag_i;
  assign tag_match_w = ~|tag_diff_w;

  assign data_out_o = output_word(out_buf_q, out_word_index_q);
  assign data_out_ctrl_o = ((out_word_index_q < out_word_count_w[3:0]) ? `ASCON_DATA_VALID : 32'h00000000) |
                           ((out_word_index_q + 4'd1 >= out_word_count_w[3:0]) ? `ASCON_DATA_LAST : 32'h00000000) |
                           ({28'h0000000, output_keep(text_len_i, out_word_index_q)} << `ASCON_DATA_KEEP_SHIFT);

  ascon_round4_comb round4_i(
    .state_i(s_q),
    .rc_start_i(rc_index_q),
    .state_o(round_state_w)
  );

  always @(posedge clk_i or negedge rstn_i) begin
    if (!rstn_i) begin
      state_q <= ST_IDLE;
      s_q <= 320'b0;
      rc_index_q <= 4'd0;
      ad_block_q <= 2'd0;
      text_block_q <= 2'd0;
      ad_final_q <= 1'b0;
      ad_buf_q <= 256'b0;
      text_buf_q <= 256'b0;
      out_buf_q <= 256'b0;
      ad_word_count_q <= 4'd0;
      text_word_count_q <= 4'd0;
      out_word_index_q <= 4'd0;
      stream_error_q <= 1'b0;
      busy_o <= 1'b0;
      done_o <= 1'b0;
      tag_valid_o <= 1'b0;
      error_o <= 1'b0;
      error_code_o <= `ASCON_ERROR_NONE;
      generated_tag_o <= 128'h00000000000000000000000000000000;
    end else begin
      done_o <= 1'b0;

      if (clear_i) begin
        state_q <= ST_IDLE;
        s_q <= 320'b0;
        rc_index_q <= 4'd0;
        ad_block_q <= 2'd0;
        text_block_q <= 2'd0;
        ad_final_q <= 1'b0;
        ad_buf_q <= 256'b0;
        text_buf_q <= 256'b0;
        out_buf_q <= 256'b0;
        ad_word_count_q <= 4'd0;
        text_word_count_q <= 4'd0;
        out_word_index_q <= 4'd0;
        stream_error_q <= 1'b0;
        busy_o <= 1'b0;
        tag_valid_o <= 1'b0;
        error_o <= 1'b0;
        error_code_o <= `ASCON_ERROR_NONE;
        generated_tag_o <= 128'h00000000000000000000000000000000;
      end else begin
        if (!busy_o && data_in_pulse_i) begin
          if (keep_count(data_in_ctrl_i[`ASCON_DATA_KEEP_SHIFT +: 4]) == 3'd7) begin
            stream_error_q <= 1'b1;
          end
          if ((data_in_ctrl_i & `ASCON_DATA_AD) != 32'h00000000) begin
            case (ad_word_count_q)
              4'd0: ad_buf_q[31:0]    <= data_in_i;
              4'd1: ad_buf_q[63:32]   <= data_in_i;
              4'd2: ad_buf_q[95:64]   <= data_in_i;
              4'd3: ad_buf_q[127:96]  <= data_in_i;
              4'd4: ad_buf_q[159:128] <= data_in_i;
              4'd5: ad_buf_q[191:160] <= data_in_i;
              4'd6: ad_buf_q[223:192] <= data_in_i;
              4'd7: ad_buf_q[255:224] <= data_in_i;
              default: stream_error_q <= 1'b1;
            endcase
            ad_word_count_q <= ad_word_count_q + 4'd1;
          end else if ((data_in_ctrl_i & `ASCON_DATA_TEXT) != 32'h00000000) begin
            case (text_word_count_q)
              4'd0: text_buf_q[31:0]    <= data_in_i;
              4'd1: text_buf_q[63:32]   <= data_in_i;
              4'd2: text_buf_q[95:64]   <= data_in_i;
              4'd3: text_buf_q[127:96]  <= data_in_i;
              4'd4: text_buf_q[159:128] <= data_in_i;
              4'd5: text_buf_q[191:160] <= data_in_i;
              4'd6: text_buf_q[223:192] <= data_in_i;
              4'd7: text_buf_q[255:224] <= data_in_i;
              default: stream_error_q <= 1'b1;
            endcase
            text_word_count_q <= text_word_count_q + 4'd1;
          end else begin
            stream_error_q <= 1'b1;
          end
        end

        if (data_out_read_pulse_i && !busy_o && out_word_index_q < out_word_count_w[3:0]) begin
          out_word_index_q <= out_word_index_q + 4'd1;
        end

        case (state_q)
          ST_IDLE: begin
            busy_o <= 1'b0;
            if (start_i) begin
              out_word_index_q <= 4'd0;
              out_buf_q <= 256'b0;
              generated_tag_o <= 128'h00000000000000000000000000000000;
              tag_valid_o <= 1'b0;
              error_o <= 1'b0;
              error_code_o <= `ASCON_ERROR_NONE;
              if (mode_i != `ASCON_MODE_AEAD128) begin
                state_q <= ST_ERROR;
                error_code_o <= `ASCON_ERROR_UNSUPPORTED_MODE;
              end else if (custom_len_i != 32'd0 || out_len_i != 32'd0 ||
                           ad_len_i > MAX_AD_BYTES || text_len_i > MAX_TEXT_BYTES ||
                           stream_error_q) begin
                state_q <= ST_ERROR;
                error_code_o <= stream_error_q ? `ASCON_ERROR_STREAM_PROTOCOL : `ASCON_ERROR_BAD_LENGTH;
              end else begin
                // S <- IV || K || N, packed as {x4,x3,x2,x1,x0}.
                s_q <= {nonce_i[127:64], nonce_i[63:0], key_i[127:64], key_i[63:0], IV_AEAD128};
                rc_index_q <= 4'd4;
                ad_block_q <= 2'd0;
                text_block_q <= 2'd0;
                busy_o <= 1'b1;
                state_q <= ST_INIT_P12;
              end
            end
          end

          ST_INIT_P12: begin
            s_q <= round_state_w;
            if (rc_index_q == 4'd12) begin
              state_q <= ST_INIT_KEY;
            end else begin
              rc_index_q <= rc_index_q + 4'd4;
            end
          end

          ST_INIT_KEY: begin
            s_q <= s_q ^ {key_i, 192'b0};
            state_q <= ST_AD_DECIDE;
          end

          ST_AD_DECIDE: begin
            if (ad_len_i == 32'd0) begin
              state_q <= ST_DOMAIN;
            end else if (ad_block_q < ad_full_blocks_w) begin
              ad_final_q <= 1'b0;
              state_q <= ST_AD_XOR;
            end else begin
              ad_final_q <= 1'b1;
              state_q <= ST_AD_XOR;
            end
          end

          ST_AD_XOR: begin
            s_q <= s_q ^ {192'b0, (ad_final_q ? ad_padded_block_w : current_ad_block_w)};
            rc_index_q <= 4'd8;
            state_q <= ST_AD_P8;
          end

          ST_AD_P8: begin
            s_q <= round_state_w;
            if (rc_index_q == 4'd12) begin
              if (ad_final_q) begin
                state_q <= ST_DOMAIN;
              end else begin
                ad_block_q <= ad_block_q + 2'd1;
                state_q <= ST_AD_DECIDE;
              end
            end else begin
              rc_index_q <= rc_index_q + 4'd4;
            end
          end

          ST_DOMAIN: begin
            s_q <= s_q ^ {1'b1, 319'b0};
            state_q <= ST_TX_DECIDE;
          end

          ST_TX_DECIDE: begin
            if (text_block_q < text_full_blocks_w) begin
              state_q <= ST_TX_FULL;
            end else begin
              state_q <= ST_TX_FINAL;
            end
          end

          ST_TX_FULL: begin
            if (decrypt_i) begin
              out_buf_q <= set_output_block(out_buf_q, text_block_q, dec_full_plain_w, 5'd16);
              s_q <= {s_q[319:128], current_text_block_w};
            end else begin
              out_buf_q <= set_output_block(out_buf_q, text_block_q, enc_full_rate_w, 5'd16);
              s_q <= {s_q[319:128], enc_full_rate_w};
            end
            rc_index_q <= 4'd8;
            state_q <= ST_TX_P8;
          end

          ST_TX_P8: begin
            s_q <= round_state_w;
            if (rc_index_q == 4'd12) begin
              text_block_q <= text_block_q + 2'd1;
              state_q <= ST_TX_DECIDE;
            end else begin
              rc_index_q <= rc_index_q + 4'd4;
            end
          end

          ST_TX_FINAL: begin
            if (decrypt_i) begin
              out_buf_q <= set_output_block(out_buf_q, text_block_q, dec_final_plain_w, text_final_bytes_w);
              s_q <= {s_q[319:128], dec_final_rate_w};
            end else begin
              out_buf_q <= set_output_block(out_buf_q, text_block_q, enc_final_rate_w, text_final_bytes_w);
              s_q <= {s_q[319:128], enc_final_rate_w};
            end
            state_q <= ST_FINAL_KEY;
          end

          ST_FINAL_KEY: begin
            s_q <= s_q ^ {64'b0, key_i, 128'b0};
            rc_index_q <= 4'd4;
            state_q <= ST_FINAL_P12;
          end

          ST_FINAL_P12: begin
            s_q <= round_state_w;
            if (rc_index_q == 4'd12) begin
              generated_tag_o <= tag_calc_w;
              state_q <= ST_FINISH;
            end else begin
              rc_index_q <= rc_index_q + 4'd4;
            end
          end

          ST_FINISH: begin
            busy_o <= 1'b0;
            done_o <= 1'b1;
            if (decrypt_i) begin
              tag_valid_o <= tag_match_w;
              if (!tag_match_w) begin
                // Do not expose unauthenticated plaintext.
                out_buf_q <= 256'b0;
                error_o <= 1'b1;
                error_code_o <= `ASCON_ERROR_TAG_INVALID;
              end else begin
                error_o <= 1'b0;
                error_code_o <= `ASCON_ERROR_NONE;
              end
            end else begin
              tag_valid_o <= 1'b0;
              error_o <= 1'b0;
              error_code_o <= `ASCON_ERROR_NONE;
            end
            state_q <= ST_IDLE;
          end

          ST_ERROR: begin
            busy_o <= 1'b0;
            done_o <= 1'b1;
            tag_valid_o <= 1'b0;
            error_o <= 1'b1;
            state_q <= ST_IDLE;
          end

          default: begin
            state_q <= ST_IDLE;
            busy_o <= 1'b0;
          end
        endcase
      end
    end
  end

endmodule

`endif
