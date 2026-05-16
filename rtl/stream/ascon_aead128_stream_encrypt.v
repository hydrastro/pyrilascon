`ifndef ASCON_AEAD128_STREAM_ENCRYPT_V
`define ASCON_AEAD128_STREAM_ENCRYPT_V

`include "ascon_accel_regs.vh"
`include "ascon_accel_axis_defs.vh"

// -----------------------------------------------------------------------------
// Unbounded AXI4-Stream AEAD128 encryption backend, one round per cycle.
//
// This module is the first real streaming backend for the frozen pyrilascon ABI.
// It deliberately implements encryption only:
//   * key/nonce/length/mode are still provided by the CSR/MMIO control plane;
//   * AD and plaintext arrive as two AXI stream packets on the shared input;
//   * tuser selects AD then TEXT and is checked by the backend receiver;
//   * ciphertext is emitted as TEXT beats as plaintext is consumed;
//   * no complete AD/plaintext buffering is required, so encryption is unbounded;
//   * authenticated decrypt remains a later buffered/quarantine backend.
//
// The reusable ascon_axis_framer remains available as an independent validator
// for wrappers, fuzzing, and future HASH/XOF frontends. This backend keeps its
// input beat receiver local so ready/valid is never coupled to an output/P8 stall
// through a second stateful block. That makes multi-beat plaintext packets
// deterministic under Icarus and synthesis simulators.
// -----------------------------------------------------------------------------
module ascon_aead128_stream_encrypt #(
  parameter integer DATA_BYTES = 16,
  parameter integer DATA_WIDTH = DATA_BYTES * 8
) (
  input  wire                    clk_i,
  input  wire                    rstn_i,
  input  wire                    start_i,
  input  wire                    clear_i,
  input  wire                    decrypt_i,
  input  wire [3:0]              mode_i,
  input  wire [31:0]             ad_len_i,
  input  wire [31:0]             text_len_i,
  input  wire [31:0]             out_len_i,
  input  wire [31:0]             custom_len_i,
  input  wire [127:0]            key_i,
  input  wire [127:0]            nonce_i,

  input  wire [DATA_WIDTH-1:0]   s_axis_tdata,
  input  wire [DATA_BYTES-1:0]   s_axis_tkeep,
  input  wire                    s_axis_tvalid,
  output wire                    s_axis_tready,
  input  wire                    s_axis_tlast,
  input  wire [3:0]              s_axis_tuser,

  output reg  [DATA_WIDTH-1:0]   m_axis_tdata,
  output reg  [DATA_BYTES-1:0]   m_axis_tkeep,
  output reg                     m_axis_tvalid,
  input  wire                    m_axis_tready,
  output reg                     m_axis_tlast,
  output reg  [3:0]              m_axis_tuser,

  output reg                     busy_o,
  output reg                     done_o,
  output reg                     tag_valid_o,
  output reg                     error_o,
  output reg  [31:0]             error_code_o,
  output reg  [127:0]            generated_tag_o
);

  localparam [63:0] IV_AEAD128 = 64'h0000_1000_808c_0001;
  localparam [7:0]  DATA_BYTES_U8 = DATA_BYTES;

  localparam [4:0] ST_IDLE          = 5'd0;
  localparam [4:0] ST_INIT_P12      = 5'd1;
  localparam [4:0] ST_INIT_KEY      = 5'd2;
  localparam [4:0] ST_AD_START      = 5'd3;
  localparam [4:0] ST_AD_WAIT       = 5'd4;
  localparam [4:0] ST_AD_P8         = 5'd5;
  localparam [4:0] ST_AD_EMPTY      = 5'd6;
  localparam [4:0] ST_DOMAIN        = 5'd7;
  localparam [4:0] ST_TEXT_START    = 5'd8;
  localparam [4:0] ST_TEXT_WAIT     = 5'd9;
  localparam [4:0] ST_TEXT_EMIT     = 5'd10;
  localparam [4:0] ST_TEXT_OUT_WAIT = 5'd11;
  localparam [4:0] ST_TEXT_P8       = 5'd12;
  localparam [4:0] ST_TEXT_EMPTY    = 5'd13;
  localparam [4:0] ST_FINAL_KEY     = 5'd14;
  localparam [4:0] ST_FINAL_P12     = 5'd15;
  localparam [4:0] ST_FINISH        = 5'd16;
  localparam [4:0] ST_ERROR         = 5'd17;

  reg [4:0]   state_q;
  reg [319:0] s_q;
  reg [3:0]   rc_index_q;
  reg         ad_empty_after_full_q;
  reg         text_empty_after_full_q;
  reg         text_p8_after_last_full_q;
  reg         text_output_final_partial_q;
  reg [31:0]  ad_seen_q;
  reg [31:0]  text_seen_q;
  reg [127:0] text_block128_q;
  reg [7:0]   text_block_bytes_q;
  reg         text_block_last_q;

  wire [7:0]   rc_w;
  wire [319:0] round_state_w;
  wire [127:0] rate_w;
  wire [127:0] input_block128_w;
  wire [127:0] input_padded_block_w;
  wire [127:0] ciphertext_block_w;
  wire [127:0] text_padded_block_w;
  wire [127:0] tag_calc_w;

  wire [7:0]  input_bytes_w;
  wire        input_keep_contiguous_w;
  wire        input_keep_nonzero_w;
  wire        input_partial_w;
  wire        input_kind_ad_w;
  wire        input_kind_text_w;
  wire        input_fire_w;
  wire        output_fire_w;
  wire        text_block_is_full_w;
  wire        text_block_is_partial_final_w;
  wire        text_block_is_full_final_w;
  wire [31:0] ad_next_seen_w;
  wire [31:0] text_next_seen_w;
  wire        ad_protocol_error_w;
  wire        text_protocol_error_w;
  wire        ad_length_error_w;
  wire        text_length_error_w;

  assign rc_w = round_constant(rc_index_q);
  assign rate_w = s_q[127:0];
  assign input_block128_w = s_axis_tdata[127:0];
  assign input_bytes_w = keep_count(s_axis_tkeep);
  assign input_keep_contiguous_w = is_contiguous_keep(s_axis_tkeep);
  assign input_keep_nonzero_w = |s_axis_tkeep;
  assign input_partial_w = (input_bytes_w != DATA_BYTES_U8);
  assign input_kind_ad_w = (s_axis_tuser == `ASCON_AXIS_USER_AD);
  assign input_kind_text_w = (s_axis_tuser == `ASCON_AXIS_USER_TEXT);
  assign input_padded_block_w = pad_block(input_block128_w, input_bytes_w[4:0]);
  assign ciphertext_block_w = rate_w ^ text_block128_q;
  assign text_padded_block_w = pad_block(text_block128_q, text_block_bytes_q[4:0]);
  assign tag_calc_w = round_state_w[319:192] ^ key_i;

  // Do not assert ready for zero-length phases. This prevents the next logical
  // packet from being consumed while the FSM is merely passing through AD_WAIT
  // or TEXT_WAIT to handle a zero-length phase.
  assign s_axis_tready = ((state_q == ST_AD_WAIT) && (ad_len_i != 32'd0)) ||
                         ((state_q == ST_TEXT_WAIT) && (text_len_i != 32'd0) && !m_axis_tvalid);
  assign input_fire_w = s_axis_tvalid && s_axis_tready;
  assign output_fire_w = m_axis_tvalid && m_axis_tready;
  assign text_block_is_full_w = (text_block_bytes_q == DATA_BYTES_U8);
  assign text_block_is_partial_final_w = text_block_last_q && !text_block_is_full_w;
  assign text_block_is_full_final_w = text_block_last_q && text_block_is_full_w;
  assign ad_next_seen_w = ad_seen_q + {24'h000000, input_bytes_w};
  assign text_next_seen_w = text_seen_q + {24'h000000, input_bytes_w};

  assign ad_protocol_error_w = (!input_keep_contiguous_w) ||
                               (!input_keep_nonzero_w) ||
                               (!input_kind_ad_w) ||
                               ((!s_axis_tlast) && input_partial_w);
  assign text_protocol_error_w = (!input_keep_contiguous_w) ||
                                 (!input_keep_nonzero_w) ||
                                 (!input_kind_text_w) ||
                                 ((!s_axis_tlast) && input_partial_w);
  assign ad_length_error_w = (ad_next_seen_w > ad_len_i) ||
                             (s_axis_tlast && (ad_next_seen_w != ad_len_i)) ||
                             ((!s_axis_tlast) && (ad_next_seen_w >= ad_len_i));
  assign text_length_error_w = (text_next_seen_w > text_len_i) ||
                               (s_axis_tlast && (text_next_seen_w != text_len_i)) ||
                               ((!s_axis_tlast) && (text_next_seen_w >= text_len_i));

  ascon_round_comb round_i (
    .state_i(s_q),
    .rc_i(rc_w),
    .state_o(round_state_w)
  );

  always @(posedge clk_i or negedge rstn_i) begin
    if (!rstn_i) begin
      state_q <= ST_IDLE;
      s_q <= 320'b0;
      rc_index_q <= 4'd0;
      ad_empty_after_full_q <= 1'b0;
      text_empty_after_full_q <= 1'b0;
      text_p8_after_last_full_q <= 1'b0;
      text_output_final_partial_q <= 1'b0;
      ad_seen_q <= 32'h00000000;
      text_seen_q <= 32'h00000000;
      text_block128_q <= 128'h00000000000000000000000000000000;
      text_block_bytes_q <= 8'h00;
      text_block_last_q <= 1'b0;
      m_axis_tdata <= {DATA_WIDTH{1'b0}};
      m_axis_tkeep <= {DATA_BYTES{1'b0}};
      m_axis_tvalid <= 1'b0;
      m_axis_tlast <= 1'b0;
      m_axis_tuser <= `ASCON_AXIS_USER_TEXT;
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
        ad_empty_after_full_q <= 1'b0;
        text_empty_after_full_q <= 1'b0;
        text_p8_after_last_full_q <= 1'b0;
        text_output_final_partial_q <= 1'b0;
        ad_seen_q <= 32'h00000000;
        text_seen_q <= 32'h00000000;
        text_block128_q <= 128'h00000000000000000000000000000000;
        text_block_bytes_q <= 8'h00;
        text_block_last_q <= 1'b0;
        m_axis_tdata <= {DATA_WIDTH{1'b0}};
        m_axis_tkeep <= {DATA_BYTES{1'b0}};
        m_axis_tvalid <= 1'b0;
        m_axis_tlast <= 1'b0;
        m_axis_tuser <= `ASCON_AXIS_USER_TEXT;
        busy_o <= 1'b0;
        tag_valid_o <= 1'b0;
        error_o <= 1'b0;
        error_code_o <= `ASCON_ERROR_NONE;
        generated_tag_o <= 128'h00000000000000000000000000000000;
      end else begin
        if (output_fire_w) begin
          m_axis_tvalid <= 1'b0;
        end

        case (state_q)
          ST_IDLE: begin
            busy_o <= 1'b0;
            if (start_i) begin
              generated_tag_o <= 128'h00000000000000000000000000000000;
              tag_valid_o <= 1'b0;
              error_o <= 1'b0;
              error_code_o <= `ASCON_ERROR_NONE;
              m_axis_tvalid <= 1'b0;
              m_axis_tlast <= 1'b0;
              ad_seen_q <= 32'h00000000;
              text_seen_q <= 32'h00000000;
              if (mode_i != `ASCON_MODE_AEAD128 || decrypt_i) begin
                state_q <= ST_ERROR;
                error_code_o <= `ASCON_ERROR_UNSUPPORTED_MODE;
              end else if (custom_len_i != 32'd0 || out_len_i != 32'd0 || DATA_BYTES != 16) begin
                state_q <= ST_ERROR;
                error_code_o <= `ASCON_ERROR_BAD_LENGTH;
              end else begin
                s_q <= {nonce_i[127:64], nonce_i[63:0], key_i[127:64], key_i[63:0], IV_AEAD128};
                rc_index_q <= 4'd4;
                busy_o <= 1'b1;
                state_q <= ST_INIT_P12;
              end
            end
          end

          ST_INIT_P12: begin
            s_q <= round_state_w;
            if (rc_index_q == 4'd15) begin
              state_q <= ST_INIT_KEY;
            end else begin
              rc_index_q <= rc_index_q + 4'd1;
            end
          end

          ST_INIT_KEY: begin
            s_q <= s_q ^ {key_i, 192'b0};
            state_q <= ST_AD_START;
          end

          ST_AD_START: begin
            ad_empty_after_full_q <= 1'b0;
            ad_seen_q <= 32'h00000000;
            state_q <= ST_AD_WAIT;
          end

          ST_AD_WAIT: begin
            if (ad_len_i == 32'd0) begin
              state_q <= ST_DOMAIN;
            end else if (input_fire_w) begin
              if (ad_protocol_error_w || ad_length_error_w) begin
                state_q <= ST_ERROR;
                error_code_o <= `ASCON_ERROR_STREAM_PROTOCOL;
              end else begin
                ad_seen_q <= ad_next_seen_w;
                if (s_axis_tlast && (input_bytes_w == DATA_BYTES_U8)) begin
                  s_q <= s_q ^ {192'b0, input_block128_w};
                  ad_empty_after_full_q <= 1'b1;
                end else if (s_axis_tlast) begin
                  s_q <= s_q ^ {192'b0, input_padded_block_w};
                  ad_empty_after_full_q <= 1'b0;
                end else begin
                  s_q <= s_q ^ {192'b0, input_block128_w};
                  ad_empty_after_full_q <= 1'b0;
                end
                rc_index_q <= 4'd8;
                state_q <= ST_AD_P8;
              end
            end
          end

          ST_AD_P8: begin
            s_q <= round_state_w;
            if (rc_index_q == 4'd15) begin
              if (ad_empty_after_full_q) begin
                state_q <= ST_AD_EMPTY;
              end else if (ad_seen_q == ad_len_i) begin
                state_q <= ST_DOMAIN;
              end else begin
                state_q <= ST_AD_WAIT;
              end
            end else begin
              rc_index_q <= rc_index_q + 4'd1;
            end
          end

          ST_AD_EMPTY: begin
            s_q <= s_q ^ {192'b0, pad_block(128'h0, 5'd0)};
            ad_empty_after_full_q <= 1'b0;
            rc_index_q <= 4'd8;
            state_q <= ST_AD_P8;
          end

          ST_DOMAIN: begin
            s_q <= s_q ^ {1'b1, 319'b0};
            state_q <= ST_TEXT_START;
          end

          ST_TEXT_START: begin
            text_empty_after_full_q <= 1'b0;
            text_seen_q <= 32'h00000000;
            text_p8_after_last_full_q <= 1'b0;
            text_output_final_partial_q <= 1'b0;
            text_block128_q <= 128'h00000000000000000000000000000000;
            text_block_bytes_q <= 8'h00;
            text_block_last_q <= 1'b0;
            state_q <= ST_TEXT_WAIT;
          end

          ST_TEXT_WAIT: begin
            if (text_len_i == 32'd0) begin
              state_q <= ST_TEXT_EMPTY;
            end else if (input_fire_w) begin
              if (text_protocol_error_w || text_length_error_w) begin
                state_q <= ST_ERROR;
                error_code_o <= `ASCON_ERROR_STREAM_PROTOCOL;
              end else begin
                text_seen_q <= text_next_seen_w;
                text_block128_q <= input_block128_w;
                text_block_bytes_q <= input_bytes_w;
                text_block_last_q <= s_axis_tlast;
                state_q <= ST_TEXT_EMIT;
              end
            end
          end

          ST_TEXT_EMIT: begin
            m_axis_tdata <= ciphertext_block_w;
            m_axis_tkeep <= keep_mask(text_block_bytes_q[4:0]);
            m_axis_tvalid <= 1'b1;
            m_axis_tlast <= text_block_last_q;
            m_axis_tuser <= `ASCON_AXIS_USER_TEXT;
            if (text_block_is_partial_final_w) begin
              s_q <= {s_q[319:128], rate_w ^ text_padded_block_w};
              text_empty_after_full_q <= 1'b0;
              text_p8_after_last_full_q <= 1'b0;
              text_output_final_partial_q <= 1'b1;
            end else begin
              s_q <= {s_q[319:128], ciphertext_block_w};
              text_empty_after_full_q <= text_block_is_full_final_w;
              text_p8_after_last_full_q <= text_block_is_full_final_w;
              text_output_final_partial_q <= 1'b0;
            end
            state_q <= ST_TEXT_OUT_WAIT;
          end

          ST_TEXT_OUT_WAIT: begin
            if (!m_axis_tvalid || output_fire_w) begin
              if (text_output_final_partial_q) begin
                text_output_final_partial_q <= 1'b0;
                state_q <= ST_FINAL_KEY;
              end else begin
                rc_index_q <= 4'd8;
                state_q <= ST_TEXT_P8;
              end
            end
          end

          ST_TEXT_P8: begin
            s_q <= round_state_w;
            if (rc_index_q == 4'd15) begin
              if (text_p8_after_last_full_q) begin
                text_p8_after_last_full_q <= 1'b0;
                state_q <= ST_TEXT_EMPTY;
              end else begin
                state_q <= ST_TEXT_WAIT;
              end
            end else begin
              rc_index_q <= rc_index_q + 4'd1;
            end
          end

          ST_TEXT_EMPTY: begin
            s_q <= {s_q[319:128], rate_w ^ pad_block(128'h0, 5'd0)};
            text_empty_after_full_q <= 1'b0;
            state_q <= ST_FINAL_KEY;
          end

          ST_FINAL_KEY: begin
            s_q <= s_q ^ {64'b0, key_i, 128'b0};
            rc_index_q <= 4'd4;
            state_q <= ST_FINAL_P12;
          end

          ST_FINAL_P12: begin
            s_q <= round_state_w;
            if (rc_index_q == 4'd15) begin
              generated_tag_o <= tag_calc_w;
              state_q <= ST_FINISH;
            end else begin
              rc_index_q <= rc_index_q + 4'd1;
            end
          end

          ST_FINISH: begin
            busy_o <= 1'b0;
            done_o <= 1'b1;
            tag_valid_o <= 1'b0;
            error_o <= 1'b0;
            error_code_o <= `ASCON_ERROR_NONE;
            state_q <= ST_IDLE;
          end

          ST_ERROR: begin
            busy_o <= 1'b0;
            done_o <= 1'b1;
            tag_valid_o <= 1'b0;
            error_o <= 1'b1;
            if (error_code_o == `ASCON_ERROR_NONE) begin
              error_code_o <= `ASCON_ERROR_STREAM_PROTOCOL;
            end
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

  function [7:0] keep_count;
    input [DATA_BYTES-1:0] keep;
    integer i;
    reg found_zero;
    begin
      keep_count = 8'h00;
      found_zero = 1'b0;
      for (i = 0; i < DATA_BYTES; i = i + 1) begin
        if (!found_zero && keep[i]) begin
          keep_count = keep_count + 8'h01;
        end else begin
          found_zero = 1'b1;
        end
      end
    end
  endfunction

  function is_contiguous_keep;
    input [DATA_BYTES-1:0] keep;
    integer i;
    reg found_zero;
    begin
      is_contiguous_keep = 1'b1;
      found_zero = 1'b0;
      for (i = 0; i < DATA_BYTES; i = i + 1) begin
        if (!keep[i]) begin
          found_zero = 1'b1;
        end else if (found_zero) begin
          is_contiguous_keep = 1'b0;
        end
      end
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

  function [127:0] pad_block;
    input [127:0] block;
    input [4:0]   valid_bytes;
    begin
      pad_block = (block & low_byte_mask(valid_bytes)) ^ (128'h1 << (valid_bytes * 8));
    end
  endfunction

  function [DATA_BYTES-1:0] keep_mask;
    input [4:0] valid_bytes;
    integer i;
    begin
      keep_mask = {DATA_BYTES{1'b0}};
      for (i = 0; i < DATA_BYTES; i = i + 1) begin
        if (i < valid_bytes) begin
          keep_mask[i] = 1'b1;
        end
      end
    end
  endfunction

endmodule

`endif
