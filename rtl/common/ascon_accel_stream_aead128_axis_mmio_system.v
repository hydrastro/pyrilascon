`ifndef ASCON_ACCEL_STREAM_AEAD128_AXIS_MMIO_SYSTEM_V
`define ASCON_ACCEL_STREAM_AEAD128_AXIS_MMIO_SYSTEM_V

// -----------------------------------------------------------------------------
// NEORV32/bring-up integration wrapper for the stream-native AEAD128 backend.
//
// The control/status plane and CPU-driven stream bridge intentionally remain two
// independent MMIO regions, matching the firmware transport:
//   * csr_bus_*  -> frozen ASCON accelerator register ABI
//   * axis_bus_* -> tiny MMIO-to-AXI-stream bridge register block
// -----------------------------------------------------------------------------
module ascon_accel_stream_aead128_axis_mmio_system #(
  parameter integer DATA_BYTES     = 16,
  parameter integer DATA_WIDTH     = DATA_BYTES * 8,
  parameter integer MAX_TEXT_BYTES = 1024,
  parameter integer MAX_TEXT_BITS  = MAX_TEXT_BYTES * 8
) (
  input  wire                    clk_i,
  input  wire                    rstn_i,

  // Frozen accelerator CSR/MMIO window.
  input  wire                    csr_bus_valid_i,
  input  wire                    csr_bus_write_i,
  input  wire [7:0]              csr_bus_addr_i,
  input  wire [31:0]             csr_bus_wdata_i,
  input  wire [3:0]              csr_bus_wstrb_i,
  output wire [31:0]             csr_bus_rdata_o,
  output wire                    csr_bus_ready_o,

  // CPU-driven AXI-stream bridge MMIO window.
  input  wire                    axis_bus_valid_i,
  input  wire                    axis_bus_write_i,
  input  wire [7:0]              axis_bus_addr_i,
  input  wire [31:0]             axis_bus_wdata_i,
  input  wire [3:0]              axis_bus_wstrb_i,
  output wire [31:0]             axis_bus_rdata_o,
  output wire                    axis_bus_ready_o,

  output wire                    irq_o,
  output wire                    axis_bridge_error_o
);

  wire [DATA_WIDTH-1:0] bridge_to_core_tdata_w;
  wire [DATA_BYTES-1:0] bridge_to_core_tkeep_w;
  wire                  bridge_to_core_tvalid_w;
  wire                  bridge_to_core_tready_w;
  wire                  bridge_to_core_tlast_w;
  wire [3:0]            bridge_to_core_tuser_w;

  wire [DATA_WIDTH-1:0] core_to_bridge_tdata_w;
  wire [DATA_BYTES-1:0] core_to_bridge_tkeep_w;
  wire                  core_to_bridge_tvalid_w;
  wire                  core_to_bridge_tready_w;
  wire                  core_to_bridge_tlast_w;
  wire [3:0]            core_to_bridge_tuser_w;

  ascon_axis_mmio_bridge #(
    .DATA_BYTES(DATA_BYTES),
    .DATA_WIDTH(DATA_WIDTH)
  ) axis_bridge_i (
    .clk_i(clk_i),
    .rstn_i(rstn_i),
    .bus_valid_i(axis_bus_valid_i),
    .bus_write_i(axis_bus_write_i),
    .bus_addr_i(axis_bus_addr_i),
    .bus_wdata_i(axis_bus_wdata_i),
    .bus_wstrb_i(axis_bus_wstrb_i),
    .bus_rdata_o(axis_bus_rdata_o),
    .bus_ready_o(axis_bus_ready_o),
    .m_axis_tdata(bridge_to_core_tdata_w),
    .m_axis_tkeep(bridge_to_core_tkeep_w),
    .m_axis_tvalid(bridge_to_core_tvalid_w),
    .m_axis_tready(bridge_to_core_tready_w),
    .m_axis_tlast(bridge_to_core_tlast_w),
    .m_axis_tuser(bridge_to_core_tuser_w),
    .s_axis_tdata(core_to_bridge_tdata_w),
    .s_axis_tkeep(core_to_bridge_tkeep_w),
    .s_axis_tvalid(core_to_bridge_tvalid_w),
    .s_axis_tready(core_to_bridge_tready_w),
    .s_axis_tlast(core_to_bridge_tlast_w),
    .s_axis_tuser(core_to_bridge_tuser_w),
    .error_o(axis_bridge_error_o)
  );

  ascon_accel_stream_aead128_top #(
    .DATA_BYTES(DATA_BYTES),
    .DATA_WIDTH(DATA_WIDTH),
    .MAX_TEXT_BYTES(MAX_TEXT_BYTES),
    .MAX_TEXT_BITS(MAX_TEXT_BITS)
  ) accel_i (
    .clk_i(clk_i),
    .rstn_i(rstn_i),
    .bus_valid_i(csr_bus_valid_i),
    .bus_write_i(csr_bus_write_i),
    .bus_addr_i(csr_bus_addr_i),
    .bus_wdata_i(csr_bus_wdata_i),
    .bus_wstrb_i(csr_bus_wstrb_i),
    .bus_rdata_o(csr_bus_rdata_o),
    .bus_ready_o(csr_bus_ready_o),
    .irq_o(irq_o),
    .s_axis_tdata(bridge_to_core_tdata_w),
    .s_axis_tkeep(bridge_to_core_tkeep_w),
    .s_axis_tvalid(bridge_to_core_tvalid_w),
    .s_axis_tready(bridge_to_core_tready_w),
    .s_axis_tlast(bridge_to_core_tlast_w),
    .s_axis_tuser(bridge_to_core_tuser_w),
    .m_axis_tdata(core_to_bridge_tdata_w),
    .m_axis_tkeep(core_to_bridge_tkeep_w),
    .m_axis_tvalid(core_to_bridge_tvalid_w),
    .m_axis_tready(core_to_bridge_tready_w),
    .m_axis_tlast(core_to_bridge_tlast_w),
    .m_axis_tuser(core_to_bridge_tuser_w)
  );

endmodule

`endif // ASCON_ACCEL_STREAM_AEAD128_AXIS_MMIO_SYSTEM_V
