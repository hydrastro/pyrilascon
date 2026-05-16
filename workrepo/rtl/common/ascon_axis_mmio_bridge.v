`ifndef ASCON_AXIS_MMIO_BRIDGE_V
`define ASCON_AXIS_MMIO_BRIDGE_V

// -----------------------------------------------------------------------------
// CPU-driven MMIO-to-AXI-stream bridge.
//
// This bridge is the RTL counterpart of firmware/ascon_accel_axis_mmio_transport.
// It exposes a tiny byte-addressed 32-bit MMIO register file used by a small CPU
// to push and pull 128-bit AXI-stream beats without a DMA engine.
//
// Register map, byte offsets from the bridge base:
//   0x00 TX_DATA0     little-endian bytes  0..3
//   0x04 TX_DATA1     little-endian bytes  4..7
//   0x08 TX_DATA2     little-endian bytes  8..11
//   0x0c TX_DATA3     little-endian bytes 12..15
//   0x10 TX_KEEP      low 16 bits
//   0x14 TX_USER      low 4 bits
//   0x18 TX_CTRL      bit0 VALID, bit1 LAST; writing VALID commits one beat
//   0x1c STATUS       bit0 TX_READY, bit1 RX_VALID, bit2 RX_LAST,
//                     bits[15:8] RX_LEVEL, bit31 ERROR
//   0x20 RX_DATA0     little-endian bytes  0..3 of the oldest RX beat
//   0x24 RX_DATA1     little-endian bytes  4..7 of the oldest RX beat
//   0x28 RX_DATA2     little-endian bytes  8..11 of the oldest RX beat
//   0x2c RX_DATA3     little-endian bytes 12..15 of the oldest RX beat
//   0x30 RX_KEEP      low 16 bits of the oldest RX beat
//   0x34 RX_USER      low 4 bits of the oldest RX beat
//   0x38 RX_CTRL      bit0 POP; writing POP releases the oldest RX beat
//
// TX remains a single holding register because firmware waits for TX_READY before
// committing each beat.  RX is FIFO-backed so the accelerator can return several
// ciphertext/plaintext beats while a simple CPU is still pushing later input
// beats.  This avoids the one-beat output deadlock that appears in CPU-driven
// full-duplex stream systems before a DMA path exists.
// -----------------------------------------------------------------------------
module ascon_axis_mmio_bridge #(
  parameter integer DATA_BYTES    = 16,
  parameter integer DATA_WIDTH    = DATA_BYTES * 8,
  parameter integer RX_FIFO_DEPTH = 4
) (
  input  wire                    clk_i,
  input  wire                    rstn_i,

  // Simple byte-addressed 32-bit MMIO request interface.
  input  wire                    bus_valid_i,
  input  wire                    bus_write_i,
  input  wire [7:0]              bus_addr_i,
  input  wire [31:0]             bus_wdata_i,
  input  wire [3:0]              bus_wstrb_i,
  output reg  [31:0]             bus_rdata_o,
  output wire                    bus_ready_o,

  // Stream beat emitted toward the accelerator input.
  output wire [DATA_WIDTH-1:0]   m_axis_tdata,
  output wire [DATA_BYTES-1:0]   m_axis_tkeep,
  output wire                    m_axis_tvalid,
  input  wire                    m_axis_tready,
  output wire                    m_axis_tlast,
  output wire [3:0]              m_axis_tuser,

  // Stream beat received from the accelerator output.
  input  wire [DATA_WIDTH-1:0]   s_axis_tdata,
  input  wire [DATA_BYTES-1:0]   s_axis_tkeep,
  input  wire                    s_axis_tvalid,
  output wire                    s_axis_tready,
  input  wire                    s_axis_tlast,
  input  wire [3:0]              s_axis_tuser,

  output wire                    error_o
);

  localparam [7:0] REG_TX_DATA0 = 8'h00;
  localparam [7:0] REG_TX_DATA1 = 8'h04;
  localparam [7:0] REG_TX_DATA2 = 8'h08;
  localparam [7:0] REG_TX_DATA3 = 8'h0c;
  localparam [7:0] REG_TX_KEEP  = 8'h10;
  localparam [7:0] REG_TX_USER  = 8'h14;
  localparam [7:0] REG_TX_CTRL  = 8'h18;
  localparam [7:0] REG_STATUS   = 8'h1c;
  localparam [7:0] REG_RX_DATA0 = 8'h20;
  localparam [7:0] REG_RX_DATA1 = 8'h24;
  localparam [7:0] REG_RX_DATA2 = 8'h28;
  localparam [7:0] REG_RX_DATA3 = 8'h2c;
  localparam [7:0] REG_RX_KEEP  = 8'h30;
  localparam [7:0] REG_RX_USER  = 8'h34;
  localparam [7:0] REG_RX_CTRL  = 8'h38;

  localparam [31:0] TX_CTRL_VALID = 32'h00000001;
  localparam [31:0] TX_CTRL_LAST  = 32'h00000002;
  localparam [31:0] STATUS_TX_READY = 32'h00000001;
  localparam [31:0] STATUS_RX_VALID = 32'h00000002;
  localparam [31:0] STATUS_RX_LAST  = 32'h00000004;
  localparam [31:0] STATUS_ERROR    = 32'h80000000;
  localparam [31:0] RX_CTRL_POP     = 32'h00000001;

  function integer clog2_int;
    input integer value;
    integer v;
    begin
      v = value - 1;
      clog2_int = 0;
      while (v > 0) begin
        v = v >> 1;
        clog2_int = clog2_int + 1;
      end
    end
  endfunction

  localparam integer RX_PTR_BITS = (RX_FIFO_DEPTH <= 1) ? 1 : clog2_int(RX_FIFO_DEPTH);
  localparam integer RX_CNT_BITS = clog2_int(RX_FIFO_DEPTH + 1);
  localparam [RX_CNT_BITS-1:0] RX_FIFO_DEPTH_COUNT = RX_FIFO_DEPTH;
  localparam [RX_PTR_BITS-1:0] RX_FIFO_LAST_PTR = RX_FIFO_DEPTH - 1;

  reg [31:0] tx_data_q [0:3];
  reg [DATA_BYTES-1:0] tx_keep_q;
  reg [3:0] tx_user_q;
  reg       tx_last_q;
  reg       tx_valid_q;

  reg [DATA_WIDTH-1:0] rx_data_fifo_q [0:RX_FIFO_DEPTH-1];
  reg [DATA_BYTES-1:0] rx_keep_fifo_q [0:RX_FIFO_DEPTH-1];
  reg [3:0]            rx_user_fifo_q [0:RX_FIFO_DEPTH-1];
  reg                  rx_last_fifo_q [0:RX_FIFO_DEPTH-1];
  reg [RX_PTR_BITS-1:0] rx_rd_ptr_q;
  reg [RX_PTR_BITS-1:0] rx_wr_ptr_q;
  reg [RX_CNT_BITS-1:0] rx_count_q;

  reg error_q;

  wire write_access_w = bus_valid_i & bus_write_i;
  wire read_access_w  = bus_valid_i & ~bus_write_i;
  wire tx_fire_w      = tx_valid_q & m_axis_tready;
  wire rx_fifo_full_w = (rx_count_q == RX_FIFO_DEPTH_COUNT);
  wire rx_valid_w     = (rx_count_q != {RX_CNT_BITS{1'b0}});
  wire rx_fire_w      = s_axis_tvalid & s_axis_tready;
  wire rx_pop_w       = write_access_w & (bus_addr_i == REG_RX_CTRL) &
                        ((bus_wdata_i & RX_CTRL_POP) != 32'h00000000);

  assign bus_ready_o   = bus_valid_i;
  assign error_o       = error_q;
  assign m_axis_tdata  = {tx_data_q[3], tx_data_q[2], tx_data_q[1], tx_data_q[0]};
  assign m_axis_tkeep  = tx_keep_q;
  assign m_axis_tvalid = tx_valid_q;
  assign m_axis_tlast  = tx_last_q;
  assign m_axis_tuser  = tx_user_q;
  assign s_axis_tready = ~rx_fifo_full_w;

  function [31:0] apply_wstrb;
    input [31:0] old_value;
    input [31:0] new_value;
    input [3:0]  wstrb;
    begin
      apply_wstrb[7:0]   = wstrb[0] ? new_value[7:0]   : old_value[7:0];
      apply_wstrb[15:8]  = wstrb[1] ? new_value[15:8]  : old_value[15:8];
      apply_wstrb[23:16] = wstrb[2] ? new_value[23:16] : old_value[23:16];
      apply_wstrb[31:24] = wstrb[3] ? new_value[31:24] : old_value[31:24];
    end
  endfunction

  function [RX_PTR_BITS-1:0] bump_rx_ptr;
    input [RX_PTR_BITS-1:0] ptr;
    begin
      if (ptr == RX_FIFO_LAST_PTR) begin
        bump_rx_ptr = {RX_PTR_BITS{1'b0}};
      end else begin
        bump_rx_ptr = ptr + 1'b1;
      end
    end
  endfunction

  wire [31:0] tx_keep_word_w = {{(32-DATA_BYTES){1'b0}}, tx_keep_q};
  wire [31:0] rx_keep_word_w = {{(32-DATA_BYTES){1'b0}}, rx_valid_w ? rx_keep_fifo_q[rx_rd_ptr_q] : {DATA_BYTES{1'b0}}};
  wire [31:0] tx_keep_next_w = apply_wstrb(tx_keep_word_w, bus_wdata_i, bus_wstrb_i);
  wire [31:0] tx_user_next_w = apply_wstrb({28'h0000000, tx_user_q}, bus_wdata_i, bus_wstrb_i);
  wire [31:0] rx_level_word_w = {{(24-RX_CNT_BITS){1'b0}}, rx_count_q, 8'h00};
  wire [31:0] status_w = (tx_valid_q ? 32'h00000000 : STATUS_TX_READY) |
                         (rx_valid_w ? STATUS_RX_VALID : 32'h00000000) |
                         ((rx_valid_w & rx_last_fifo_q[rx_rd_ptr_q]) ? STATUS_RX_LAST : 32'h00000000) |
                         rx_level_word_w |
                         (error_q ? STATUS_ERROR : 32'h00000000);

  always @(*) begin
    bus_rdata_o = 32'h00000000;
    if (read_access_w) begin
      case (bus_addr_i)
        REG_TX_DATA0: bus_rdata_o = tx_data_q[0];
        REG_TX_DATA1: bus_rdata_o = tx_data_q[1];
        REG_TX_DATA2: bus_rdata_o = tx_data_q[2];
        REG_TX_DATA3: bus_rdata_o = tx_data_q[3];
        REG_TX_KEEP:  bus_rdata_o = tx_keep_word_w;
        REG_TX_USER:  bus_rdata_o = {28'h0000000, tx_user_q};
        REG_TX_CTRL:  bus_rdata_o = (tx_valid_q ? TX_CTRL_VALID : 32'h00000000) |
                                    (tx_last_q  ? TX_CTRL_LAST  : 32'h00000000);
        REG_STATUS:   bus_rdata_o = status_w;
        REG_RX_DATA0: bus_rdata_o = rx_valid_w ? rx_data_fifo_q[rx_rd_ptr_q][31:0] : 32'h00000000;
        REG_RX_DATA1: bus_rdata_o = rx_valid_w ? rx_data_fifo_q[rx_rd_ptr_q][63:32] : 32'h00000000;
        REG_RX_DATA2: bus_rdata_o = rx_valid_w ? rx_data_fifo_q[rx_rd_ptr_q][95:64] : 32'h00000000;
        REG_RX_DATA3: bus_rdata_o = rx_valid_w ? rx_data_fifo_q[rx_rd_ptr_q][127:96] : 32'h00000000;
        REG_RX_KEEP:  bus_rdata_o = rx_keep_word_w;
        REG_RX_USER:  bus_rdata_o = rx_valid_w ? {28'h0000000, rx_user_fifo_q[rx_rd_ptr_q]} : 32'h00000000;
        REG_RX_CTRL:  bus_rdata_o = 32'h00000000;
        default:      bus_rdata_o = 32'h00000000;
      endcase
    end
  end

  integer reset_i;
  always @(posedge clk_i or negedge rstn_i) begin
    if (!rstn_i) begin
      tx_data_q[0] <= 32'h00000000;
      tx_data_q[1] <= 32'h00000000;
      tx_data_q[2] <= 32'h00000000;
      tx_data_q[3] <= 32'h00000000;
      tx_keep_q    <= {DATA_BYTES{1'b0}};
      tx_user_q    <= 4'h0;
      tx_last_q    <= 1'b0;
      tx_valid_q   <= 1'b0;
      for (reset_i = 0; reset_i < RX_FIFO_DEPTH; reset_i = reset_i + 1) begin
        rx_data_fifo_q[reset_i] <= {DATA_WIDTH{1'b0}};
        rx_keep_fifo_q[reset_i] <= {DATA_BYTES{1'b0}};
        rx_user_fifo_q[reset_i] <= 4'h0;
        rx_last_fifo_q[reset_i] <= 1'b0;
      end
      rx_rd_ptr_q <= {RX_PTR_BITS{1'b0}};
      rx_wr_ptr_q <= {RX_PTR_BITS{1'b0}};
      rx_count_q  <= {RX_CNT_BITS{1'b0}};
      error_q     <= 1'b0;
    end else begin
      if (tx_fire_w) begin
        tx_valid_q <= 1'b0;
        tx_last_q  <= 1'b0;
      end

      if (rx_fire_w) begin
        rx_data_fifo_q[rx_wr_ptr_q] <= s_axis_tdata;
        rx_keep_fifo_q[rx_wr_ptr_q] <= s_axis_tkeep;
        rx_user_fifo_q[rx_wr_ptr_q] <= s_axis_tuser;
        rx_last_fifo_q[rx_wr_ptr_q] <= s_axis_tlast;
        rx_wr_ptr_q <= bump_rx_ptr(rx_wr_ptr_q);
      end

      if (rx_pop_w) begin
        if (!rx_valid_w) begin
          error_q <= 1'b1;
        end else begin
          rx_rd_ptr_q <= bump_rx_ptr(rx_rd_ptr_q);
        end
      end

      case ({rx_fire_w, rx_pop_w & rx_valid_w})
        2'b10: rx_count_q <= rx_count_q + 1'b1;
        2'b01: rx_count_q <= rx_count_q - 1'b1;
        default: begin
        end
      endcase

      if (write_access_w) begin
        case (bus_addr_i)
          REG_TX_DATA0: tx_data_q[0] <= apply_wstrb(tx_data_q[0], bus_wdata_i, bus_wstrb_i);
          REG_TX_DATA1: tx_data_q[1] <= apply_wstrb(tx_data_q[1], bus_wdata_i, bus_wstrb_i);
          REG_TX_DATA2: tx_data_q[2] <= apply_wstrb(tx_data_q[2], bus_wdata_i, bus_wstrb_i);
          REG_TX_DATA3: tx_data_q[3] <= apply_wstrb(tx_data_q[3], bus_wdata_i, bus_wstrb_i);
          REG_TX_KEEP: begin
            tx_keep_q <= tx_keep_next_w[DATA_BYTES-1:0];
          end
          REG_TX_USER: begin
            tx_user_q <= tx_user_next_w[3:0];
          end
          REG_TX_CTRL: begin
            if ((bus_wdata_i & TX_CTRL_VALID) != 32'h00000000) begin
              if (tx_valid_q) begin
                error_q <= 1'b1;
              end else begin
                tx_valid_q <= 1'b1;
                tx_last_q  <= (bus_wdata_i & TX_CTRL_LAST) != 32'h00000000;
              end
            end
          end
          REG_RX_CTRL: begin
            if ((bus_wdata_i & RX_CTRL_POP) != 32'h00000000) begin
              if (!rx_valid_w) begin
                error_q <= 1'b1;
              end
            end
          end
          default: begin
          end
        endcase
      end
    end
  end

endmodule

`endif // ASCON_AXIS_MMIO_BRIDGE_V
