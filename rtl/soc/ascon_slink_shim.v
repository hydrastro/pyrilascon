// ---------------------------------------------------------------------------
// ascon_slink_shim
//
// Converts NEORV32's SLINK word stream into the tagged AXI4-Stream that
// ascon_aead128_axis expects.
//
// Why this exists
// ---------------
// ascon_aead128_axis is already AXI4-Stream native, but its slave port carries
// two things SLINK cannot express per beat:
//
//   * s_tuser  -- 0 = associated data, 1 = message
//   * s_tkeep  -- which bytes of the final (partial) word are valid
//
// SLINK's per-beat sidebands are the routing field (set once per transfer via a
// register, so it cannot vary per beat when a DMA is driving) and the last flag
// (chosen by the write address). Neither can carry a per-beat byte-mask.
//
// So this shim *derives* tuser/tkeep/tlast from AD_LEN and MSG_LEN -- which the
// accelerator's control registers already hold -- plus a byte counter. The
// consequence is important: the data plane becomes a plain, unadorned word
// stream, which is exactly what a DMA can produce with a constant destination
// address. The CPU never touches the payload.
//
// Stream contract expected by the host
// ------------------------------------
//   * send ceil(AD_LEN/4)  words of associated data, then
//   * send ceil(MSG_LEN/4) words of message.
// Associated data is padded to a word boundary; the shim masks the surplus
// bytes with tkeep, so the padding is never absorbed.
//
// An empty message still has to terminate the input phase (the core advances on
// s_tlast && s_tuser==1), so the shim synthesises that final zero-length beat
// itself, consuming no SLINK word.
// ---------------------------------------------------------------------------
`default_nettype none

module ascon_slink_shim (
  input  wire        clk,
  input  wire        rst_n,

  // from the accelerator's control registers
  input  wire        start_i,      // one-cycle pulse: begin a new operation
  input  wire [7:0]  ad_len_i,
  input  wire [7:0]  msg_len_i,

  // SLINK TX side (NEORV32 -> shim): a plain word stream
  input  wire [31:0] slink_dat_i,
  input  wire        slink_val_i,
  output wire        slink_rdy_o,

  // AXI4-Stream to ascon_aead128_axis
  output wire [31:0] s_tdata,
  output reg  [3:0]  s_tkeep,
  output reg         s_tuser,
  output reg         s_tlast,
  output wire        s_tvalid,
  input  wire        s_tready
);

  localparam [1:0] ST_IDLE = 2'd0,  // waiting for start
                   ST_AD   = 2'd1,  // forwarding associated-data words
                   ST_MSG  = 2'd2,  // forwarding message words
                   ST_NULL = 2'd3;  // synthesising the empty-message beat

  reg [1:0] st;
  reg [7:0] ad_len_r, msg_len_r;
  reg [7:0] cnt;                    // bytes already forwarded in this phase

  // Bytes still owed in the current phase, and the resulting byte-enable.
  wire [7:0] rem_ad  = ad_len_r  - cnt;
  wire [7:0] rem_msg = msg_len_r - cnt;
  wire [7:0] rem     = (st == ST_AD) ? rem_ad : rem_msg;
  wire [2:0] keepn   = (rem >= 8'd4) ? 3'd4 : rem[2:0];

  function [3:0] keep_mask;
    input [2:0] n;
    begin
      case (n)
        3'd0:    keep_mask = 4'b0000;
        3'd1:    keep_mask = 4'b0001;
        3'd2:    keep_mask = 4'b0011;
        3'd3:    keep_mask = 4'b0111;
        default: keep_mask = 4'b1111;
      endcase
    end
  endfunction

  // Data is a straight pass-through; only the sidebands are synthesised.
  assign s_tdata  = slink_dat_i;

  // A real beat needs a SLINK word; the synthetic empty-message beat does not.
  assign s_tvalid = ((st == ST_AD) || (st == ST_MSG)) ? slink_val_i :
                    (st == ST_NULL) ? 1'b1 : 1'b0;

  // Back-pressure straight through to SLINK, so the FIFO stalls naturally.
  assign slink_rdy_o = ((st == ST_AD) || (st == ST_MSG)) ? s_tready : 1'b0;

  // Sidebands (combinational on the current phase).
  always @(*) begin
    case (st)
      ST_AD: begin
        s_tkeep = keep_mask(keepn);
        s_tuser = 1'b0;
        s_tlast = 1'b0;               // the core only acts on tlast when tuser=1
      end
      ST_MSG: begin
        s_tkeep = keep_mask(keepn);
        s_tuser = 1'b1;
        s_tlast = (rem_msg <= 8'd4);  // final message word ends the input phase
      end
      ST_NULL: begin
        s_tkeep = 4'b0000;            // zero-length beat
        s_tuser = 1'b1;
        s_tlast = 1'b1;
      end
      default: begin
        s_tkeep = 4'b0000;
        s_tuser = 1'b0;
        s_tlast = 1'b0;
      end
    endcase
  end

  wire beat = s_tvalid & s_tready;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      st       <= ST_IDLE;
      cnt      <= 8'd0;
      ad_len_r <= 8'd0;
      msg_len_r<= 8'd0;
    end else begin
      case (st)
        ST_IDLE: if (start_i) begin
          ad_len_r  <= ad_len_i;
          msg_len_r <= msg_len_i;
          cnt       <= 8'd0;
          // Skip phases that carry no bytes.
          if (ad_len_i != 8'd0)       st <= ST_AD;
          else if (msg_len_i != 8'd0) st <= ST_MSG;
          else                        st <= ST_NULL;
        end

        ST_AD: if (beat) begin
          if (rem_ad <= 8'd4) begin       // associated data complete
            cnt <= 8'd0;
            st  <= (msg_len_r != 8'd0) ? ST_MSG : ST_NULL;
          end else begin
            cnt <= cnt + 8'd4;
          end
        end

        ST_MSG: if (beat) begin
          if (rem_msg <= 8'd4) st  <= ST_IDLE;   // last beat carried tlast
          else                 cnt <= cnt + 8'd4;
        end

        ST_NULL: if (beat) st <= ST_IDLE;

        default: st <= ST_IDLE;
      endcase
    end
  end

endmodule

`default_nettype wire
