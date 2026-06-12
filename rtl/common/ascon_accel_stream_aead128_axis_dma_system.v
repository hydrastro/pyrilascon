`ifndef ASCON_ACCEL_STREAM_AEAD128_AXIS_DMA_SYSTEM_V
`define ASCON_ACCEL_STREAM_AEAD128_AXIS_DMA_SYSTEM_V

// -----------------------------------------------------------------------------
// Autonomous (DMA-fed) integration wrapper for the stream-native AEAD128 backend.
//
// This is the DMA counterpart of ascon_accel_stream_aead128_axis_mmio_system.
// Where the MMIO system exposes a CPU-driven push/pop bridge that costs the
// firmware O(length) loads/stores, this system drops the descriptor-driven
// ascon_axis_dma engine in front of the same backend.  Two independent MMIO
// regions are exposed, mirroring the firmware transport split:
//   * csr_bus_*  -> frozen ASCON accelerator register ABI (key/nonce/lengths/
//                   CONTROL.START and the resulting tag); unchanged contract.
//   * dma_bus_*  -> DMA descriptor register block (source/destination addresses,
//                   lengths, GO/IRQ_EN/CLEAR, and BUSY/DONE/ERROR status).
//
// The DMA owns a single system-memory master port (word addressed) that the SoC
// arbitrates against the CPU.  Internally the DMA's stream master feeds the
// backend stream input and the backend stream output feeds the DMA stream sink,
// so once the CPU has programmed both windows and pulsed CONTROL.START (CSR) and
// CTRL.GO (DMA) the whole encryption payload moves without further CPU work.
//
// Scope: the autonomous path automates the *encryption* data plane only (the
// unbounded streaming-encrypt backend emits exactly one ciphertext beat per
// plaintext beat).  Buffered authenticated decryption, which releases plaintext
// only after the tag check, keeps a different dataflow and remains CPU-driven.
// -----------------------------------------------------------------------------
module ascon_accel_stream_aead128_axis_dma_system #(
  parameter integer DATA_BYTES     = 16,
  parameter integer DATA_WIDTH     = DATA_BYTES * 8,
  parameter integer MAX_TEXT_BYTES = 1024,
  parameter integer MAX_TEXT_BITS  = MAX_TEXT_BYTES * 8,
  parameter integer ADDR_WORD_BITS = 14
) (
  input  wire                          clk_i,
  input  wire                          rstn_i,

  // Frozen accelerator CSR/MMIO window.
  input  wire                          csr_bus_valid_i,
  input  wire                          csr_bus_write_i,
  input  wire [7:0]                    csr_bus_addr_i,
  input  wire [31:0]                   csr_bus_wdata_i,
  input  wire [3:0]                    csr_bus_wstrb_i,
  output wire [31:0]                   csr_bus_rdata_o,
  output wire                          csr_bus_ready_o,

  // DMA descriptor MMIO window.
  input  wire                          dma_bus_valid_i,
  input  wire                          dma_bus_write_i,
  input  wire [7:0]                    dma_bus_addr_i,
  input  wire [31:0]                   dma_bus_wdata_i,
  input  wire [3:0]                    dma_bus_wstrb_i,
  output wire [31:0]                   dma_bus_rdata_o,
  output wire                          dma_bus_ready_o,

  // System-memory master port driven by the DMA (word addressed).
  output wire                          mem_req_valid_o,
  output wire                          mem_req_we_o,
  output wire [ADDR_WORD_BITS-1:0]     mem_req_addr_o,
  output wire [31:0]                   mem_req_wdata_o,
  output wire [3:0]                    mem_req_wstrb_o,
  input  wire                          mem_req_ready_i,
  input  wire                          mem_rsp_valid_i,
  input  wire [31:0]                   mem_rsp_rdata_i,

  // Accelerator (tag-ready) interrupt and DMA (transfer-complete) interrupt.
  output wire                          csr_irq_o,
  output wire                          dma_irq_o,
  output wire                          dma_busy_o,
  output wire                          dma_done_o,
  output wire                          dma_error_o
);

  // DMA stream master -> backend stream input.
  wire [DATA_WIDTH-1:0] dma_to_core_tdata_w;
  wire [DATA_BYTES-1:0] dma_to_core_tkeep_w;
  wire                  dma_to_core_tvalid_w;
  wire                  dma_to_core_tready_w;
  wire                  dma_to_core_tlast_w;
  wire [3:0]            dma_to_core_tuser_w;

  // Backend stream output -> DMA stream sink.
  wire [DATA_WIDTH-1:0] core_to_dma_tdata_w;
  wire [DATA_BYTES-1:0] core_to_dma_tkeep_w;
  wire                  core_to_dma_tvalid_w;
  wire                  core_to_dma_tready_w;
  wire                  core_to_dma_tlast_w;
  wire [3:0]            core_to_dma_tuser_w;

  ascon_axis_dma #(
    .DATA_BYTES(DATA_BYTES),
    .DATA_WIDTH(DATA_WIDTH),
    .ADDR_WORD_BITS(ADDR_WORD_BITS)
  ) dma_i (
    .clk_i(clk_i),
    .rstn_i(rstn_i),
    .bus_valid_i(dma_bus_valid_i),
    .bus_write_i(dma_bus_write_i),
    .bus_addr_i(dma_bus_addr_i),
    .bus_wdata_i(dma_bus_wdata_i),
    .bus_wstrb_i(dma_bus_wstrb_i),
    .bus_rdata_o(dma_bus_rdata_o),
    .bus_ready_o(dma_bus_ready_o),
    .mem_req_valid_o(mem_req_valid_o),
    .mem_req_we_o(mem_req_we_o),
    .mem_req_addr_o(mem_req_addr_o),
    .mem_req_wdata_o(mem_req_wdata_o),
    .mem_req_wstrb_o(mem_req_wstrb_o),
    .mem_req_ready_i(mem_req_ready_i),
    .mem_rsp_valid_i(mem_rsp_valid_i),
    .mem_rsp_rdata_i(mem_rsp_rdata_i),
    .m_axis_tdata(dma_to_core_tdata_w),
    .m_axis_tkeep(dma_to_core_tkeep_w),
    .m_axis_tvalid(dma_to_core_tvalid_w),
    .m_axis_tready(dma_to_core_tready_w),
    .m_axis_tlast(dma_to_core_tlast_w),
    .m_axis_tuser(dma_to_core_tuser_w),
    .s_axis_tdata(core_to_dma_tdata_w),
    .s_axis_tkeep(core_to_dma_tkeep_w),
    .s_axis_tvalid(core_to_dma_tvalid_w),
    .s_axis_tready(core_to_dma_tready_w),
    .s_axis_tlast(core_to_dma_tlast_w),
    .s_axis_tuser(core_to_dma_tuser_w),
    .busy_o(dma_busy_o),
    .done_o(dma_done_o),
    .irq_o(dma_irq_o),
    .error_o(dma_error_o)
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
    .irq_o(csr_irq_o),
    .s_axis_tdata(dma_to_core_tdata_w),
    .s_axis_tkeep(dma_to_core_tkeep_w),
    .s_axis_tvalid(dma_to_core_tvalid_w),
    .s_axis_tready(dma_to_core_tready_w),
    .s_axis_tlast(dma_to_core_tlast_w),
    .s_axis_tuser(dma_to_core_tuser_w),
    .m_axis_tdata(core_to_dma_tdata_w),
    .m_axis_tkeep(core_to_dma_tkeep_w),
    .m_axis_tvalid(core_to_dma_tvalid_w),
    .m_axis_tready(core_to_dma_tready_w),
    .m_axis_tlast(core_to_dma_tlast_w),
    .m_axis_tuser(core_to_dma_tuser_w)
  );

endmodule

`endif // ASCON_ACCEL_STREAM_AEAD128_AXIS_DMA_SYSTEM_V
