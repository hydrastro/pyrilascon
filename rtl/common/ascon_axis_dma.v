`ifndef ASCON_AXIS_DMA_V
`define ASCON_AXIS_DMA_V

`include "ascon_accel_axis_defs.vh"

// -----------------------------------------------------------------------------
// Descriptor-driven AXI-stream DMA front-end for the streaming AEAD128 backend.
//
// This is the autonomous-transport counterpart of ascon_axis_mmio_bridge.  The
// CPU-driven bridge requires firmware to push and pop every 128-bit beat through
// MMIO registers, so a long payload costs O(length) CPU loads/stores.  This DMA
// engine instead takes a small descriptor (source addresses, lengths, and a
// destination address) and then drives the data plane itself: it fetches AD and
// plaintext beats from memory, feeds them into the backend stream input, drains
// the ciphertext beats from the backend stream output, and writes them back to
// memory.  Firmware programs five descriptor registers and one GO bit, then
// waits for DONE / IRQ.  This is the "DMA-friendly interface" described in
// RASD section 10.4 and the "DMA-fed AXI-stream front-end" deferred in the
// development report.
//
// Scope: this engine automates the *encryption* data plane (the unbounded
// streaming-encrypt backend ascon_aead128_stream_encrypt, which emits exactly
// one ciphertext beat per plaintext beat).  The control plane
// (key/nonce/lengths/CONTROL.START and the final tag) stays on the frozen CSR
// ABI, so the DMA is a pure data-plane accelerator that drops in front of the
// existing backend without changing its register contract.  The engine uses
// strict per-beat serialization (send one plaintext beat, drain its ciphertext
// beat, repeat); this favours clarity and matches the bring-up philosophy of
// the rest of the project over maximum overlap/throughput.
//
// Memory port (this module is the bus master):
//   mem_req_valid_o / mem_req_ready_i  request handshake (combinational accept)
//   mem_req_we_o                       1 = write, 0 = read
//   mem_req_addr_o[ADDR_WORD_BITS-1:0] 32-bit-word address
//   mem_req_wdata_o / mem_req_wstrb_o  write word and byte strobes
//   mem_rsp_valid_i / mem_rsp_rdata_i  read data, one cycle (or more) after a
//                                      read request is accepted (a single read
//                                      is outstanding at a time)
//
// Descriptor MMIO window (byte offsets, full-word writes, accepted while idle):
//   0x00 AD_ADDR    byte address of associated data    (4-byte aligned)
//   0x04 AD_LEN     associated-data length in bytes
//   0x08 TEXT_ADDR  byte address of input plaintext     (4-byte aligned)
//   0x0c TEXT_LEN   plaintext length in bytes
//   0x10 DST_ADDR   byte address of output ciphertext   (4-byte aligned)
//   0x14 CTRL       bit0 GO (start), bit8 IRQ_EN, bit16 CLEAR
//   0x18 STATUS     bit0 BUSY, bit1 DONE, bit2 ERROR, bits[15:8] out-beat count
//   0x1c OUT_BYTES  number of ciphertext bytes written to memory
// -----------------------------------------------------------------------------
module ascon_axis_dma #(
  parameter integer DATA_BYTES      = 16,
  parameter integer DATA_WIDTH      = DATA_BYTES * 8,
  parameter integer ADDR_WORD_BITS  = 14
) (
  input  wire                          clk_i,
  input  wire                          rstn_i,

  // Descriptor MMIO window (byte-addressed, 32-bit, single-cycle ack).
  input  wire                          bus_valid_i,
  input  wire                          bus_write_i,
  input  wire [7:0]                    bus_addr_i,
  input  wire [31:0]                   bus_wdata_i,
  input  wire [3:0]                    bus_wstrb_i,
  output reg  [31:0]                   bus_rdata_o,
  output wire                          bus_ready_o,

  // System-memory master port (word addressed).
  output reg                           mem_req_valid_o,
  output reg                           mem_req_we_o,
  output reg  [ADDR_WORD_BITS-1:0]     mem_req_addr_o,
  output reg  [31:0]                   mem_req_wdata_o,
  output reg  [3:0]                    mem_req_wstrb_o,
  input  wire                          mem_req_ready_i,
  input  wire                          mem_rsp_valid_i,
  input  wire [31:0]                   mem_rsp_rdata_i,

  // Stream beat driven toward the accelerator input (DMA is the source).
  output reg  [DATA_WIDTH-1:0]         m_axis_tdata,
  output reg  [DATA_BYTES-1:0]         m_axis_tkeep,
  output reg                           m_axis_tvalid,
  input  wire                          m_axis_tready,
  output reg                           m_axis_tlast,
  output reg  [3:0]                    m_axis_tuser,

  // Stream beat received from the accelerator output (DMA is the sink).
  input  wire [DATA_WIDTH-1:0]         s_axis_tdata,
  input  wire [DATA_BYTES-1:0]         s_axis_tkeep,
  input  wire                          s_axis_tvalid,
  output reg                           s_axis_tready,
  input  wire                          s_axis_tlast,
  input  wire [3:0]                    s_axis_tuser,

  output wire                          busy_o,
  output wire                          done_o,
  output wire                          irq_o,
  output wire                          error_o
);

  localparam [7:0] REG_AD_ADDR   = 8'h00;
  localparam [7:0] REG_AD_LEN    = 8'h04;
  localparam [7:0] REG_TEXT_ADDR = 8'h08;
  localparam [7:0] REG_TEXT_LEN  = 8'h0c;
  localparam [7:0] REG_DST_ADDR  = 8'h10;
  localparam [7:0] REG_CTRL      = 8'h14;
  localparam [7:0] REG_STATUS    = 8'h18;
  localparam [7:0] REG_OUT_BYTES = 8'h1c;

  localparam [31:0] CTRL_GO      = 32'h00000001;
  localparam [31:0] CTRL_IRQ_EN  = 32'h00000100;
  localparam [31:0] CTRL_CLEAR   = 32'h00010000;
  localparam [31:0] STATUS_BUSY  = 32'h00000001;
  localparam [31:0] STATUS_DONE  = 32'h00000002;
  localparam [31:0] STATUS_ERROR = 32'h00000004;

  // FSM states.
  localparam [3:0] ST_IDLE    = 4'd0;
  localparam [3:0] ST_AD_REQ  = 4'd1;
  localparam [3:0] ST_AD_WAIT = 4'd2;
  localparam [3:0] ST_AD_TX   = 4'd3;
  localparam [3:0] ST_ARB     = 4'd4;
  localparam [3:0] ST_IN_REQ  = 4'd5;
  localparam [3:0] ST_IN_WAIT = 4'd6;
  localparam [3:0] ST_IN_TX   = 4'd7;
  localparam [3:0] ST_RX      = 4'd8;
  localparam [3:0] ST_WR      = 4'd9;
  localparam [3:0] ST_DONE    = 4'd10;

  // ---------------------------------------------------------------- functions
  // Beat byte count for the head of a stream with "bytes_left" bytes remaining.
  function [4:0] head_beat_bytes;
    input [31:0] bytes_left;
    begin
      if (bytes_left >= DATA_BYTES) head_beat_bytes = DATA_BYTES[4:0];
      else                         head_beat_bytes = bytes_left[4:0];
    end
  endfunction

  // Number of 32-bit words spanned by "n" valid bytes (ceil(n/4)).
  function [2:0] words_for_bytes;
    input [4:0] n;
    begin
      words_for_bytes = (n + 5'd3) >> 2;
    end
  endfunction

  // Contiguous low keep mask for n valid bytes.
  function [DATA_BYTES-1:0] keep_for_bytes;
    input [4:0] n;
    integer b;
    begin
      keep_for_bytes = {DATA_BYTES{1'b0}};
      for (b = 0; b < DATA_BYTES; b = b + 1)
        if (b[4:0] < n) keep_for_bytes[b] = 1'b1;
    end
  endfunction

  // Population count of a keep mask (number of valid bytes, 0..16).
  function [4:0] keep_count;
    input [DATA_BYTES-1:0] mask;
    integer b;
    reg [4:0] acc;
    begin
      acc = 5'd0;
      for (b = 0; b < DATA_BYTES; b = b + 1)
        acc = acc + {4'd0, mask[b]};
      keep_count = acc;
    end
  endfunction

  // Byte strobe for word "w" of a beat carrying "n" valid bytes.
  function [3:0] strobe_for_word;
    input [4:0] n;
    input [2:0] w;
    integer k;
    reg [5:0] base;
    begin
      base = {w, 2'b00};
      strobe_for_word = 4'h0;
      for (k = 0; k < 4; k = k + 1)
        if ((base + k[5:0]) < {1'b0, n}) strobe_for_word[k] = 1'b1;
    end
  endfunction

  // ------------------------------------------------------------------ storage
  reg [3:0]  state_q;

  reg [31:0] ad_addr_q;
  reg [31:0] text_addr_q;
  reg [31:0] dst_addr_q;
  reg [31:0] ad_len_q;
  reg [31:0] text_len_q;
  reg        irq_en_q;

  reg [31:0] rd_addr_q;       // current read byte pointer
  reg [31:0] wr_addr_q;       // current write byte pointer
  reg [31:0] ad_left_q;       // AD bytes not yet sent (incl. current beat)
  reg [31:0] tin_left_q;      // input plaintext bytes not yet sent
  reg [31:0] tout_left_q;     // output ciphertext bytes not yet written
  reg [31:0] out_bytes_q;     // total ciphertext bytes written
  reg [7:0]  out_beats_q;     // count of drained output beats
  reg [7:0]  pending_out_q;   // sent text beats whose ct beat is not yet drained

  reg [DATA_WIDTH-1:0] beat_q;
  reg [4:0]  beat_bytes_q;    // valid bytes of the staged beat (0..16)
  reg [2:0]  words_q;         // words spanned by the staged beat (1..4)
  reg [2:0]  word_idx_q;      // word index within the staged beat

  reg        busy_q;
  reg        done_q;
  reg        error_q;
  reg        irq_q;

  assign bus_ready_o = bus_valid_i;
  assign busy_o      = busy_q;
  assign done_o      = done_q;
  assign error_o     = error_q;
  assign irq_o       = irq_q;

  wire write_access_w = bus_valid_i & bus_write_i;
  wire go_pulse_w     = write_access_w & (bus_addr_i == REG_CTRL) &
                        ((bus_wdata_i & CTRL_GO) != 32'h0);
  wire clear_pulse_w  = write_access_w & (bus_addr_i == REG_CTRL) &
                        ((bus_wdata_i & CTRL_CLEAR) != 32'h0);

  wire [ADDR_WORD_BITS-1:0] rd_word_addr_w =
      rd_addr_q[ADDR_WORD_BITS+1:2] + {{(ADDR_WORD_BITS-3){1'b0}}, word_idx_q};
  wire [ADDR_WORD_BITS-1:0] wr_word_addr_w =
      wr_addr_q[ADDR_WORD_BITS+1:2] + {{(ADDR_WORD_BITS-3){1'b0}}, word_idx_q};

  wire [31:0] beat_bytes_ext_w = {27'h0, beat_bytes_q};

  // tlast for the staged beat is "this beat covers all bytes still owed for the
  // current segment".  ad_left_q / tin_left_q include the staged beat until it
  // fires, so the comparison is valid throughout the presenting (TX) cycle and
  // needs no extra pipeline register.
  wire staged_last_ad_w   = (beat_bytes_ext_w >= ad_left_q);
  wire staged_last_text_w = (beat_bytes_ext_w >= tin_left_q);

  // --------------------------------------------------------- combinational out
  // Bus-master request lines, decoded from the FSM state.
  always @(*) begin
    mem_req_valid_o = 1'b0;
    mem_req_we_o    = 1'b0;
    mem_req_addr_o  = {ADDR_WORD_BITS{1'b0}};
    mem_req_wdata_o = 32'h0;
    mem_req_wstrb_o = 4'h0;
    case (state_q)
      ST_AD_REQ, ST_IN_REQ: begin
        mem_req_valid_o = 1'b1;
        mem_req_we_o    = 1'b0;
        mem_req_addr_o  = rd_word_addr_w;
      end
      ST_WR: begin
        mem_req_valid_o = 1'b1;
        mem_req_we_o    = 1'b1;
        mem_req_addr_o  = wr_word_addr_w;
        mem_req_wdata_o = beat_q[(word_idx_q*32) +: 32];
        mem_req_wstrb_o = strobe_for_word(beat_bytes_q, word_idx_q);
      end
      default: begin
      end
    endcase
  end

  // Stream master lines.
  always @(*) begin
    m_axis_tvalid = (state_q == ST_AD_TX) || (state_q == ST_IN_TX);
    m_axis_tdata  = beat_q;
    m_axis_tkeep  = keep_for_bytes(beat_bytes_q);
    m_axis_tlast  = (state_q == ST_AD_TX) ? staged_last_ad_w : staged_last_text_w;
    m_axis_tuser  = (state_q == ST_AD_TX) ? `ASCON_AXIS_USER_AD : `ASCON_AXIS_USER_TEXT;
  end

  // Stream slave (output drain) ready.
  always @(*) begin
    s_axis_tready = (state_q == ST_RX);
  end

  // ---------------------------------------------------------- descriptor read
  always @(*) begin
    bus_rdata_o = 32'h0;
    if (bus_valid_i & ~bus_write_i) begin
      case (bus_addr_i)
        REG_AD_ADDR:   bus_rdata_o = ad_addr_q;
        REG_AD_LEN:    bus_rdata_o = ad_len_q;
        REG_TEXT_ADDR: bus_rdata_o = text_addr_q;
        REG_TEXT_LEN:  bus_rdata_o = text_len_q;
        REG_DST_ADDR:  bus_rdata_o = dst_addr_q;
        REG_CTRL:      bus_rdata_o = (irq_en_q ? CTRL_IRQ_EN : 32'h0);
        REG_STATUS:    bus_rdata_o = (busy_q  ? STATUS_BUSY  : 32'h0) |
                                     (done_q  ? STATUS_DONE  : 32'h0) |
                                     (error_q ? STATUS_ERROR : 32'h0) |
                                     ({16'h0, out_beats_q, 8'h0} & 32'h0000FF00);
        REG_OUT_BYTES: bus_rdata_o = out_bytes_q;
        default:       bus_rdata_o = 32'h0;
      endcase
    end
  end

  // --------------------------------------------------------------------- FSM
  always @(posedge clk_i or negedge rstn_i) begin
    if (!rstn_i) begin
      state_q       <= ST_IDLE;
      ad_addr_q     <= 32'h0;
      text_addr_q   <= 32'h0;
      dst_addr_q    <= 32'h0;
      ad_len_q      <= 32'h0;
      text_len_q    <= 32'h0;
      irq_en_q      <= 1'b0;
      rd_addr_q     <= 32'h0;
      wr_addr_q     <= 32'h0;
      ad_left_q     <= 32'h0;
      tin_left_q    <= 32'h0;
      tout_left_q   <= 32'h0;
      out_bytes_q   <= 32'h0;
      out_beats_q   <= 8'h0;
      pending_out_q <= 8'h0;
      beat_q        <= {DATA_WIDTH{1'b0}};
      beat_bytes_q  <= 5'h0;
      words_q       <= 3'h0;
      word_idx_q    <= 3'h0;
      busy_q        <= 1'b0;
      done_q        <= 1'b0;
      error_q       <= 1'b0;
      irq_q         <= 1'b0;
    end else begin
      irq_q <= 1'b0;

      // Descriptor programming and CLEAR are accepted only while idle.
      if (write_access_w && (state_q == ST_IDLE)) begin
        case (bus_addr_i)
          REG_AD_ADDR:   ad_addr_q   <= bus_wdata_i;
          REG_AD_LEN:    ad_len_q    <= bus_wdata_i;
          REG_TEXT_ADDR: text_addr_q <= bus_wdata_i;
          REG_TEXT_LEN:  text_len_q  <= bus_wdata_i;
          REG_DST_ADDR:  dst_addr_q  <= bus_wdata_i;
          REG_CTRL:      irq_en_q    <= (bus_wdata_i & CTRL_IRQ_EN) != 32'h0;
          default: begin
          end
        endcase
        if ((bus_addr_i == REG_CTRL) && clear_pulse_w) begin
          done_q  <= 1'b0;
          error_q <= 1'b0;
        end
      end

      case (state_q)
        // -------------------------------------------------------------
        ST_IDLE: begin
          if (go_pulse_w) begin
            busy_q        <= 1'b1;
            done_q        <= 1'b0;
            error_q       <= 1'b0;
            out_bytes_q   <= 32'h0;
            out_beats_q   <= 8'h0;
            pending_out_q <= 8'h0;
            wr_addr_q     <= dst_addr_q;
            ad_left_q     <= ad_len_q;
            tin_left_q    <= text_len_q;
            tout_left_q   <= text_len_q;
            beat_q        <= {DATA_WIDTH{1'b0}};
            word_idx_q    <= 3'h0;
            if (ad_len_q != 32'h0) begin
              rd_addr_q    <= ad_addr_q;
              beat_bytes_q <= head_beat_bytes(ad_len_q);
              words_q      <= words_for_bytes(head_beat_bytes(ad_len_q));
              state_q      <= ST_AD_REQ;
            end else begin
              rd_addr_q <= text_addr_q;
              state_q   <= ST_ARB;
            end
          end
        end

        // ---------------- AD fetch & send ----------------------------
        ST_AD_REQ: begin
          if (mem_req_ready_i) state_q <= ST_AD_WAIT;
        end

        ST_AD_WAIT: begin
          if (mem_rsp_valid_i) begin
            beat_q[(word_idx_q*32) +: 32] <= mem_rsp_rdata_i;
            if (word_idx_q == (words_q - 3'd1)) begin
              state_q <= ST_AD_TX;
            end else begin
              word_idx_q <= word_idx_q + 3'd1;
              state_q    <= ST_AD_REQ;
            end
          end
        end

        ST_AD_TX: begin
          if (m_axis_tready) begin
            ad_left_q  <= ad_left_q - beat_bytes_ext_w;
            rd_addr_q  <= rd_addr_q + beat_bytes_ext_w;
            beat_q     <= {DATA_WIDTH{1'b0}};
            word_idx_q <= 3'h0;
            if (ad_left_q <= beat_bytes_ext_w) begin
              // AD complete -> begin text/interleave phase.
              rd_addr_q <= text_addr_q;
              state_q   <= ST_ARB;
            end else begin
              beat_bytes_q <= head_beat_bytes(ad_left_q - beat_bytes_ext_w);
              words_q      <= words_for_bytes(head_beat_bytes(ad_left_q - beat_bytes_ext_w));
              state_q      <= ST_AD_REQ;
            end
          end
        end

        // ---------------- text input / ct output ---------------------
        ST_ARB: begin
          if (s_axis_tvalid) begin
            // Drain a pending ciphertext beat (highest priority).
            state_q <= ST_RX;
          end else if (pending_out_q != 8'h0) begin
            // A plaintext beat was sent; wait for its ciphertext beat.
            state_q <= ST_ARB;
          end else if (tin_left_q != 32'h0) begin
            // Stage the next plaintext beat.
            beat_bytes_q <= head_beat_bytes(tin_left_q);
            words_q      <= words_for_bytes(head_beat_bytes(tin_left_q));
            beat_q       <= {DATA_WIDTH{1'b0}};
            word_idx_q   <= 3'h0;
            state_q      <= ST_IN_REQ;
          end else begin
            state_q <= ST_DONE;
          end
        end

        ST_IN_REQ: begin
          if (mem_req_ready_i) state_q <= ST_IN_WAIT;
        end

        ST_IN_WAIT: begin
          if (mem_rsp_valid_i) begin
            beat_q[(word_idx_q*32) +: 32] <= mem_rsp_rdata_i;
            if (word_idx_q == (words_q - 3'd1)) begin
              state_q <= ST_IN_TX;
            end else begin
              word_idx_q <= word_idx_q + 3'd1;
              state_q    <= ST_IN_REQ;
            end
          end
        end

        ST_IN_TX: begin
          if (m_axis_tready) begin
            tin_left_q    <= tin_left_q - beat_bytes_ext_w;
            rd_addr_q     <= rd_addr_q + beat_bytes_ext_w;
            pending_out_q <= pending_out_q + 8'd1;
            beat_q        <= {DATA_WIDTH{1'b0}};
            word_idx_q    <= 3'h0;
            state_q       <= ST_ARB;
          end
        end

        ST_RX: begin
          // s_axis_tready asserted this cycle; capture the ciphertext beat.
          if (s_axis_tvalid) begin
            beat_q        <= s_axis_tdata;
            beat_bytes_q  <= keep_count(s_axis_tkeep);
            words_q       <= words_for_bytes(keep_count(s_axis_tkeep));
            word_idx_q    <= 3'h0;
            out_beats_q   <= out_beats_q + 8'd1;
            pending_out_q <= (pending_out_q != 8'h0) ? (pending_out_q - 8'd1) : 8'h0;
            state_q       <= ST_WR;
          end
        end

        ST_WR: begin
          if (mem_req_ready_i) begin
            if (word_idx_q == (words_q - 3'd1)) begin
              wr_addr_q   <= wr_addr_q + beat_bytes_ext_w;
              out_bytes_q <= out_bytes_q + beat_bytes_ext_w;
              tout_left_q <= (tout_left_q <= beat_bytes_ext_w) ?
                             32'h0 : (tout_left_q - beat_bytes_ext_w);
              word_idx_q  <= 3'h0;
              state_q     <= ST_ARB;
            end else begin
              word_idx_q <= word_idx_q + 3'd1;
            end
          end
        end

        // -------------------------- done -----------------------------
        ST_DONE: begin
          busy_q  <= 1'b0;
          done_q  <= 1'b1;
          if (irq_en_q) irq_q <= 1'b1;
          state_q <= ST_IDLE;
        end

        default: state_q <= ST_IDLE;
      endcase
    end
  end

endmodule

`endif // ASCON_AXIS_DMA_V
