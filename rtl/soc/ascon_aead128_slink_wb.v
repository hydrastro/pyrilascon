// Wishbone-b4 slave adapter around the SLINK-native Ascon-AEAD128 peripheral,
// for NEORV32's XBUS (external bus).
//
// Identical handshake to ascon_aead128_wb (the one proven on silicon): NEORV32's
// XBUS drives STB as a single-cycle pulse and only samples the acknowledge in the
// cycles AFTER the strobe, so the adapter captures the strobe, presents the
// access until the peripheral is ready, and asserts ACK for exactly that
// completing cycle.
//
// The difference from ascon_aead128_wb is what travels over this bus: only
// CONTROL. Key, nonce, lengths, start, status, tag -- a handful of accesses per
// operation. The payload never touches it; it arrives on AXI4-Stream from
// NEORV32's SLINK, which the DMA feeds. That is the entire point: in the MMIO
// variant every 4 payload bytes cost two bus transactions, and the accelerator
// spent ~98% of its busy time waiting for the CPU.
//
// Because no register access can stall here (there is no data-movement register
// left to back-pressure), `ready` is constant 1 and every access is single-cycle.
//
// Emit the datapath RTL first:  make accel-rtl
`default_nettype none

module ascon_aead128_slink_wb #(
  parameter AD_MAX  = 32,
  parameter MSG_MAX = 32
) (
  input  wire        clk,
  input  wire        rst_n,

  // Wishbone / XBUS slave -- control plane only
  input  wire [31:0] wb_adr_i,
  input  wire [31:0] wb_dat_i,
  output wire [31:0] wb_dat_o,
  input  wire        wb_we_i,
  input  wire [3:0]  wb_sel_i,   // byte lanes (unused: registers are 32-bit)
  input  wire        wb_stb_i,   // single-cycle strobe (NEORV32 XBUS)
  input  wire        wb_cyc_i,   // held until ack
  output wire        wb_ack_o,
  output wire        wb_err_o,

  // NEORV32 SLINK TX -> payload in
  input  wire [31:0] slink_tx_dat_i,
  input  wire        slink_tx_val_i,
  output wire        slink_tx_rdy_o,

  // payload out -> NEORV32 SLINK RX
  output wire [31:0] slink_rx_dat_o,
  output wire        slink_rx_val_o,
  input  wire        slink_rx_rdy_i,
  output wire        slink_rx_lst_o,
  output wire [3:0]  slink_rx_src_o
);
  wire [31:0] rdata;
  wire        ready;

  reg access;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n)       access <= 1'b0;
    else if (!access) access <= wb_cyc_i & wb_stb_i;  // capture the strobe pulse
    else if (ready)   access <= 1'b0;
  end

  ascon_aead128_slink_mmio #(.AD_MAX(AD_MAX), .MSG_MAX(MSG_MAX)) u_mmio (
    .clk(clk), .rst_n(rst_n),
    .sel(access), .we(wb_we_i), .addr(wb_adr_i[7:0]), .wdata(wb_dat_i),
    .rdata(rdata), .ready(ready),
    .slink_tx_dat_i(slink_tx_dat_i), .slink_tx_val_i(slink_tx_val_i),
    .slink_tx_rdy_o(slink_tx_rdy_o),
    .slink_rx_dat_o(slink_rx_dat_o), .slink_rx_val_o(slink_rx_val_o),
    .slink_rx_rdy_i(slink_rx_rdy_i), .slink_rx_lst_o(slink_rx_lst_o),
    .slink_rx_src_o(slink_rx_src_o)
  );

  assign wb_dat_o = rdata;
  assign wb_ack_o = access & ready;   // ack in the cycle NEORV32 samples it
  assign wb_err_o = 1'b0;

  wire _unused = &{wb_sel_i, 1'b0};
endmodule

`default_nettype wire
