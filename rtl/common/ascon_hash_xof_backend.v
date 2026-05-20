`ifndef ASCON_HASH_XOF_BACKEND_V
`define ASCON_HASH_XOF_BACKEND_V

`include "ascon_accel_regs.vh"

// -----------------------------------------------------------------------------
// ascon_hash_xof_backend                                          v1.0
// -----------------------------------------------------------------------------
//
//   STATUS:  RTL implementation of the Ascon hash family (NIST SP 800-232).
//            Bit-exact against the Python golden model on 18 test vectors
//            (see tests/test_hash_xof_sim.py): empty, partial, exact-rate,
//            and multi-block messages for Hash256/XOF128, plus all four
//            combinations of (message, customisation) presence for CXOF128.
//
//   SCOPE:   Ascon-Hash256, Ascon-XOF128, Ascon-CXOF128 per NIST SP 800-232.
//            Legacy Ascon-Hasha / Xofa variants are intentionally not
//            implemented in the RTL; their Python implementations are
//            available in `ascon_hwmodel` for spec parity.
//
//   INTERFACE: shares the project's frozen MMIO ABI. MODE selects the
//            variant (ASCON_MODE_HASH = 3, XOF = 5, CXOF128 = 7).
//            TEXT_LEN  = message byte count.
//            CUSTOM_LEN = customisation byte count (CXOF only).
//            OUT_LEN   = requested digest length (XOF/CXOF; Hash256 internally
//                        forces 32 bytes).
//            Message and customisation bytes are streamed through DATA_IN
//            with CTRL.{TEXT, CUSTOM, KEEP, LAST}. Digest bytes are read
//            through DATA_OUT word by word, with CTRL.VALID / CTRL.LAST.
//
//   BUFFERING: bounded buffers (MAX_MSG_BITS / MAX_CUSTOM_BITS) implemented
//            as wide registers, mirroring the AEAD backend's `ad_buf_q`
//            convention so the synthesis cost is predictable.
//
// -----------------------------------------------------------------------------
module ascon_hash_xof_backend #(
  parameter integer MAX_MSG_BYTES    = 64,   // bounded; matches AEAD baseline
  parameter integer MAX_CUSTOM_BYTES = 16,
  parameter integer MAX_OUT_BYTES    = 64,
  // Derived widths
  parameter integer MAX_MSG_BITS     = MAX_MSG_BYTES   * 8,
  parameter integer MAX_CUSTOM_BITS  = MAX_CUSTOM_BYTES * 8,
  parameter integer MAX_OUT_BITS     = MAX_OUT_BYTES   * 8
) (
  input  wire         clk_i,
  input  wire         rstn_i,
  input  wire         start_i,
  input  wire         clear_i,
  input  wire [3:0]   mode_i,
  input  wire [31:0]  text_len_i,
  input  wire [31:0]  out_len_i,
  input  wire [31:0]  custom_len_i,
  input  wire         data_in_pulse_i,
  input  wire [31:0]  data_in_i,
  input  wire [31:0]  data_in_ctrl_i,
  input  wire         data_out_read_pulse_i,
  output reg          busy_o,
  output reg          done_o,
  output reg          error_o,
  output reg [31:0]   error_code_o,
  output wire [31:0]  data_out_o,
  output wire [31:0]  data_out_ctrl_o
);

  // -------------------------------------------------------------------------
  // IV constants per NIST SP 800-232 (cross-checked with the Python golden
  // model's HASH_XOF_CONFIGS).
  // -------------------------------------------------------------------------
  localparam [63:0] IV_HASH256 = 64'h0000_0801_00cc_0002;
  localparam [63:0] IV_XOF128  = 64'h0000_0800_00cc_0003;
  localparam [63:0] IV_CXOF128 = 64'h0000_0800_00cc_0004;

  // -------------------------------------------------------------------------
  // Round-constant function — identical table to the AEAD backend.
  // -------------------------------------------------------------------------
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

  // -------------------------------------------------------------------------
  // FSM states.
  //
  // Plain hash/xof flow:
  //   IDLE -> INIT_P12 -> ABSORB_DECIDE -> ABSORB_XOR -> ABSORB_P12
  //         (loop over message blocks)
  //         -> SQUEEZE_OUT (read words) -> SQUEEZE_P12 (next 64-bit block) -> ...
  //         -> FINISH.
  //
  // CXOF prelude:
  //   IDLE -> INIT_P12 -> CUST_Z0_XOR -> CUST_P12 -> CUST_DECIDE
  //         -> CUST_XOR -> CUST_P12 (loop) -> ABSORB_DECIDE (message phase).
  // -------------------------------------------------------------------------
  localparam [4:0] ST_IDLE          = 5'd0;
  localparam [4:0] ST_INIT_P12      = 5'd1;
  localparam [4:0] ST_CUST_Z0_XOR   = 5'd2;
  localparam [4:0] ST_CUST_DECIDE   = 5'd3;
  localparam [4:0] ST_CUST_XOR      = 5'd4;
  localparam [4:0] ST_CUST_P12      = 5'd5;
  localparam [4:0] ST_ABSORB_DECIDE = 5'd6;
  localparam [4:0] ST_ABSORB_XOR    = 5'd7;
  localparam [4:0] ST_ABSORB_P12    = 5'd8;
  localparam [4:0] ST_SQUEEZE_OUT   = 5'd9;
  localparam [4:0] ST_SQUEEZE_P12   = 5'd10;
  localparam [4:0] ST_FINISH        = 5'd11;
  localparam [4:0] ST_ERROR         = 5'd12;

  reg [4:0]   state_q;
  reg [319:0] s_q;
  reg [3:0]   rc_index_q;

  // Wide register buffers, mirroring the AEAD backend's pattern.
  reg [MAX_MSG_BITS-1:0]    msg_buf_q;
  reg [MAX_CUSTOM_BITS-1:0] custom_buf_q;
  reg [31:0]                msg_byte_idx_q;
  reg [31:0]                cust_byte_idx_q;
  reg [31:0]                out_byte_idx_q;
  reg [31:0]                out_total_q;
  reg                       cust_final_q;
  reg                       msg_final_q;

  // Combinational round
  wire [319:0] round_state_w;
  wire [7:0]   rc_w;
  assign rc_w = round_constant(rc_index_q);
  ascon_round_comb round_i (.state_i(s_q), .rc_i(rc_w), .state_o(round_state_w));

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------
  function [63:0] iv_for_mode;
    input [3:0] m;
    begin
      case (m)
        `ASCON_MODE_HASH:    iv_for_mode = IV_HASH256;
        `ASCON_MODE_XOF:     iv_for_mode = IV_XOF128;
        `ASCON_MODE_CXOF128: iv_for_mode = IV_CXOF128;
        default:             iv_for_mode = 64'h0;
      endcase
    end
  endfunction

  // Extract the rate-sized (8-byte) absorb word from a wide buffer at byte
  // offset `base`. `total` is the true byte length; bytes beyond `total` are
  // forced to 0 to handle the final partial block.
  function [63:0] absorb_word_msg;
    input [31:0] base;
    input [31:0] total;
    reg   [63:0] w;
    integer k;
    begin
      w = 64'h0;
      for (k = 0; k < 8; k = k + 1) begin
        if ((base + k) < total && (base + k) < MAX_MSG_BYTES) begin
          // Little-endian within the 64-bit word: byte 0 lands at bits [7:0].
          w[8*k +: 8] = msg_buf_q[8*(base[$clog2(MAX_MSG_BYTES)-1:0] + k) +: 8];
        end
      end
      absorb_word_msg = w;
    end
  endfunction

  function [63:0] absorb_word_cust;
    input [31:0] base;
    input [31:0] total;
    reg   [63:0] w;
    integer k;
    begin
      w = 64'h0;
      for (k = 0; k < 8; k = k + 1) begin
        if ((base + k) < total && (base + k) < MAX_CUSTOM_BYTES) begin
          w[8*k +: 8] = custom_buf_q[8*(base[$clog2(MAX_CUSTOM_BYTES)-1:0] + k) +: 8];
        end
      end
      absorb_word_cust = w;
    end
  endfunction

  // Final-block 0x01 padding overlay. byte_idx in [0..7] places the pad bit;
  // 4'hF means "this is a full block, no padding here".
  function [63:0] pad_mask;
    input [3:0] byte_idx;
    begin
      case (byte_idx)
        4'd0: pad_mask = 64'h00_00_00_00_00_00_00_01;
        4'd1: pad_mask = 64'h00_00_00_00_00_00_01_00;
        4'd2: pad_mask = 64'h00_00_00_00_00_01_00_00;
        4'd3: pad_mask = 64'h00_00_00_00_01_00_00_00;
        4'd4: pad_mask = 64'h00_00_00_01_00_00_00_00;
        4'd5: pad_mask = 64'h00_00_01_00_00_00_00_00;
        4'd6: pad_mask = 64'h00_01_00_00_00_00_00_00;
        4'd7: pad_mask = 64'h01_00_00_00_00_00_00_00;
        default: pad_mask = 64'h0;
      endcase
    end
  endfunction

  // Stream-in CTRL decoding
  wire [3:0] keep_w           = (data_in_ctrl_i >> `ASCON_DATA_KEEP_SHIFT) & 4'hF;
  wire       custom_word_w    = (data_in_ctrl_i & `ASCON_DATA_CUSTOM) != 32'h0;
  wire       text_word_w      = (data_in_ctrl_i & `ASCON_DATA_TEXT)   != 32'h0;
  wire       valid_in_word_w  = (data_in_ctrl_i & `ASCON_DATA_VALID)  != 32'h0;

  // Squeeze output plumbing — 64-bit rate, exposed as two 32-bit words.
  reg  [63:0] out_buf_q;
  reg  [1:0]  out_words_left_q;
  wire        out_word_avail_w = (state_q == ST_SQUEEZE_OUT) && (out_words_left_q != 2'b00);
  assign data_out_o = out_buf_q[31:0];
  assign data_out_ctrl_o =
      (out_word_avail_w ? `ASCON_DATA_VALID : 32'h0) |
      (((out_byte_idx_q + 32'd4) >= out_total_q && out_word_avail_w) ? `ASCON_DATA_LAST : 32'h0);

  // -------------------------------------------------------------------------
  // Main FSM
  // -------------------------------------------------------------------------
  integer ib;
  always @(posedge clk_i or negedge rstn_i) begin
    if (!rstn_i) begin
      state_q          <= ST_IDLE;
      s_q              <= 320'h0;
      rc_index_q       <= 4'h0;
      msg_buf_q        <= {MAX_MSG_BITS{1'b0}};
      custom_buf_q     <= {MAX_CUSTOM_BITS{1'b0}};
      msg_byte_idx_q   <= 32'h0;
      cust_byte_idx_q  <= 32'h0;
      out_byte_idx_q   <= 32'h0;
      out_total_q      <= 32'h0;
      out_buf_q        <= 64'h0;
      out_words_left_q <= 2'b00;
      cust_final_q     <= 1'b0;
      msg_final_q      <= 1'b0;
      busy_o           <= 1'b0;
      done_o           <= 1'b0;
      error_o          <= 1'b0;
      error_code_o     <= `ASCON_ERROR_NONE;
    end else if (clear_i) begin
      state_q          <= ST_IDLE;
      rc_index_q       <= 4'h0;
      msg_byte_idx_q   <= 32'h0;
      cust_byte_idx_q  <= 32'h0;
      out_byte_idx_q   <= 32'h0;
      out_buf_q        <= 64'h0;
      out_words_left_q <= 2'b00;
      cust_final_q     <= 1'b0;
      msg_final_q      <= 1'b0;
      busy_o           <= 1'b0;
      done_o           <= 1'b0;
      error_o          <= 1'b0;
      error_code_o     <= `ASCON_ERROR_NONE;
    end else begin
      case (state_q)

        // ----------------------------------------------------------------
        ST_IDLE: begin
          done_o <= 1'b0;
          if (start_i) begin
            if (mode_i != `ASCON_MODE_HASH &&
                mode_i != `ASCON_MODE_XOF  &&
                mode_i != `ASCON_MODE_CXOF128) begin
              error_o      <= 1'b1;
              error_code_o <= `ASCON_ERROR_UNSUPPORTED_MODE;
              state_q      <= ST_ERROR;
            end else if (text_len_i > MAX_MSG_BYTES ||
                         (mode_i == `ASCON_MODE_CXOF128 && custom_len_i > MAX_CUSTOM_BYTES) ||
                         out_len_i > MAX_OUT_BYTES) begin
              error_o      <= 1'b1;
              error_code_o <= `ASCON_ERROR_BAD_LENGTH;
              state_q      <= ST_ERROR;
            end else begin
              s_q[63:0]        <= iv_for_mode(mode_i);
              s_q[319:64]      <= 256'h0;
              rc_index_q       <= 4'd4;          // p[12]: start at index 4
              msg_byte_idx_q   <= 32'h0;
              cust_byte_idx_q  <= 32'h0;
              out_byte_idx_q   <= 32'h0;
              out_total_q      <= (mode_i == `ASCON_MODE_HASH) ? 32'd32 : out_len_i;
              cust_final_q     <= 1'b0;
              msg_final_q      <= 1'b0;
              out_words_left_q <= 2'b00;
              busy_o           <= 1'b1;
              error_o          <= 1'b0;
              error_code_o     <= `ASCON_ERROR_NONE;
              state_q          <= ST_INIT_P12;
            end
          end
        end

        // ----------------------------------------------------------------
        ST_INIT_P12: begin
          s_q        <= round_state_w;
          rc_index_q <= rc_index_q + 4'd1;
          if (rc_index_q == 4'd15) begin
            rc_index_q <= 4'd4;
            if (mode_i == `ASCON_MODE_CXOF128) state_q <= ST_CUST_Z0_XOR;
            else                               state_q <= ST_ABSORB_DECIDE;
          end
        end

        // ---- CXOF128 prelude: absorb Z0 = (custom_len * 8) bits LE ------
        ST_CUST_Z0_XOR: begin
          // 64-bit LE little-endian: low 32 bits are (custom_len*8); upper 32 = 0.
          s_q[63:0]  <= s_q[63:0] ^ {32'h0, custom_len_i << 3};
          rc_index_q <= 4'd4;
          state_q    <= ST_CUST_P12;
        end

        ST_CUST_P12: begin
          s_q        <= round_state_w;
          rc_index_q <= rc_index_q + 4'd1;
          if (rc_index_q == 4'd15) begin
            rc_index_q <= 4'd4;
            if (cust_final_q) state_q <= ST_ABSORB_DECIDE;
            else              state_q <= ST_CUST_DECIDE;
          end
        end

        ST_CUST_DECIDE: begin
          state_q <= ST_CUST_XOR;
        end

        ST_CUST_XOR: begin : cust_xor_blk
          reg [31:0] remaining;
          reg [3:0]  pad_idx;
          reg [63:0] w;
          remaining = (cust_byte_idx_q >= custom_len_i)
                      ? 32'h0 : (custom_len_i - cust_byte_idx_q);
          pad_idx   = (remaining >= 32'd8) ? 4'hF : remaining[3:0];
          w         = absorb_word_cust(cust_byte_idx_q, custom_len_i);
          if (pad_idx != 4'hF) w = w | pad_mask(pad_idx);
          s_q[63:0]       <= s_q[63:0] ^ w;
          cust_byte_idx_q <= cust_byte_idx_q + 32'd8;
          rc_index_q      <= 4'd4;
          if (pad_idx != 4'hF) cust_final_q <= 1'b1;
          state_q         <= ST_CUST_P12;
        end

        // ---- Message absorb (hash / xof / cxof, common path) ------------
        ST_ABSORB_DECIDE: begin
          if (msg_final_q) begin
            // All message absorbed → start squeeze.
            out_buf_q        <= s_q[63:0];
            out_words_left_q <= 2'b10;
            state_q          <= ST_SQUEEZE_OUT;
          end else begin
            state_q <= ST_ABSORB_XOR;
          end
        end

        ST_ABSORB_XOR: begin : absorb_xor_blk
          reg [31:0] remaining;
          reg [3:0]  pad_idx;
          reg [63:0] w;
          remaining = (msg_byte_idx_q >= text_len_i)
                      ? 32'h0 : (text_len_i - msg_byte_idx_q);
          pad_idx   = (remaining >= 32'd8) ? 4'hF : remaining[3:0];
          w         = absorb_word_msg(msg_byte_idx_q, text_len_i);
          if (pad_idx != 4'hF) w = w | pad_mask(pad_idx);
          s_q[63:0]      <= s_q[63:0] ^ w;
          msg_byte_idx_q <= msg_byte_idx_q + 32'd8;
          rc_index_q     <= 4'd4;
          if (pad_idx != 4'hF) msg_final_q <= 1'b1;
          state_q        <= ST_ABSORB_P12;
        end

        ST_ABSORB_P12: begin
          s_q        <= round_state_w;
          rc_index_q <= rc_index_q + 4'd1;
          if (rc_index_q == 4'd15) begin
            rc_index_q <= 4'd4;
            state_q    <= ST_ABSORB_DECIDE;
          end
        end

        // ---- Squeeze ----------------------------------------------------
        ST_SQUEEZE_OUT: begin
          if (data_out_read_pulse_i && out_words_left_q != 2'b00) begin
            out_buf_q        <= {32'h0, out_buf_q[63:32]};
            out_words_left_q <= out_words_left_q - 2'b01;
            out_byte_idx_q   <= out_byte_idx_q + 32'd4;
            if (out_byte_idx_q + 32'd4 >= out_total_q) begin
              state_q <= ST_FINISH;
            end else if (out_words_left_q == 2'b01) begin
              // We've drained the current squeeze block; produce another.
              state_q    <= ST_SQUEEZE_P12;
              rc_index_q <= 4'd4;
            end
          end
        end

        ST_SQUEEZE_P12: begin
          s_q        <= round_state_w;
          rc_index_q <= rc_index_q + 4'd1;
          if (rc_index_q == 4'd15) begin
            rc_index_q       <= 4'd4;
            out_buf_q        <= round_state_w[63:0];
            out_words_left_q <= 2'b10;
            state_q          <= ST_SQUEEZE_OUT;
          end
        end

        // ----------------------------------------------------------------
        ST_FINISH: begin
          done_o  <= 1'b1;
          busy_o  <= 1'b0;
          state_q <= ST_IDLE;
        end

        ST_ERROR: begin
          busy_o  <= 1'b0;
          done_o  <= 1'b1;
          state_q <= ST_IDLE;
        end

        default: state_q <= ST_ERROR;

      endcase

      // Stream-in byte capture into the wide buffer registers. Each
      // DATA_IN write carries up to 4 valid bytes; KEEP tells us how many.
      // Writes happen at the current append pointer (msg_byte_idx_q for
      // text, cust_byte_idx_q for customisation — both reset to 0 at start
      // and incremented only by the absorb FSM, not by the streamer; the
      // streamer keeps its own counter pre-load by waiting until IDLE).
      //
      // For this first implementation we assume the caller streams in the
      // entire message before issuing START, exactly as the AEAD backend
      // expects. In that arrangement msg_byte_idx_q is 0 when the stream
      // arrives and the streamer can append at idx 0, 4, 8, .... The
      // testbench in tests/test_hash_xof_sim.py enforces that protocol.
      if (data_in_pulse_i && valid_in_word_w &&
          state_q == ST_IDLE) begin : streamer_blk
        integer k;
        if (text_word_w) begin
          for (k = 0; k < 4; k = k + 1) begin
            if (k < keep_w && (msg_byte_idx_q + k) < MAX_MSG_BYTES) begin
              msg_buf_q[8*(msg_byte_idx_q[$clog2(MAX_MSG_BYTES)-1:0] + k) +: 8] <=
                  data_in_i[8*k +: 8];
            end
          end
          msg_byte_idx_q <= msg_byte_idx_q + {28'h0, keep_w};
        end
        if (custom_word_w) begin
          for (k = 0; k < 4; k = k + 1) begin
            if (k < keep_w && (cust_byte_idx_q + k) < MAX_CUSTOM_BYTES) begin
              custom_buf_q[8*(cust_byte_idx_q[$clog2(MAX_CUSTOM_BYTES)-1:0] + k) +: 8] <=
                  data_in_i[8*k +: 8];
            end
          end
          cust_byte_idx_q <= cust_byte_idx_q + {28'h0, keep_w};
        end
      end
    end
  end

endmodule

`endif // ASCON_HASH_XOF_BACKEND_V
