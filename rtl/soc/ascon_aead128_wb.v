// Wishbone-b4 slave adapter around the generated Ascon-AEAD128 MMIO peripheral,
// for NEORV32's XBUS (external bus).
//
// NEORV32's XBUS (rtl/core/neorv32_xbus.vhd) drives STB as a single-cycle pulse
// and holds CYC until it is acknowledged; it only samples the acknowledge in the
// cycles AFTER the strobe (while its internal "pending" is set). So the adapter
// captures the strobe, presents the access to the peripheral until it is ready,
// and asserts ACK for exactly that completing cycle. This also gives the streaming
// DATA_IN_CTRL writes their back-pressure for free (they complete when s_tready).
//
// The register datapath (ascon_aead128_axis_mmio -> ascon_aead128_axis ->
// ascon_aead128_core) is simulation-verified against the NIST model; this adapter
// + handshake is verified by tests/test_wb_xbus_sim.py driving it exactly the way
// NEORV32's XBUS does.
//
// Emit the datapath RTL first:  make accel-rtl
module ascon_aead128_wb (
  input  wire        clk,
  input  wire        rst_n,
  input  wire [31:0] wb_adr_i,
  input  wire [31:0] wb_dat_i,
  output wire [31:0] wb_dat_o,
  input  wire        wb_we_i,
  input  wire [3:0]  wb_sel_i,   // byte lanes (unused: registers are 32-bit)
  input  wire        wb_stb_i,   // single-cycle strobe (NEORV32 XBUS)
  input  wire        wb_cyc_i,   // held until ack
  output wire        wb_ack_o,
  output wire        wb_err_o
);
  wire [31:0] rdata;
  wire        ready;

  // A transaction is "in progress" from the strobe pulse until the peripheral
  // completes it. `access` is the window during which we present the access to
  // the peripheral and watch for its `ready`.
  reg access;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n)          access <= 1'b0;
    else if (!access)    access <= wb_cyc_i & wb_stb_i;  // capture the strobe pulse
    else if (ready)      access <= 1'b0;                 // done when peripheral is ready
  end

  ascon_aead128_axis_mmio u_mmio (
    .clk(clk), .rst_n(rst_n),
    .sel(access), .we(wb_we_i), .addr(wb_adr_i[7:0]), .wdata(wb_dat_i),
    .rdata(rdata), .ready(ready)
  );

  assign wb_dat_o = rdata;
  assign wb_ack_o = access & ready;   // ack in the cycle NEORV32 samples it
  assign wb_err_o = 1'b0;
endmodule
