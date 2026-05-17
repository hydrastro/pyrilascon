`ifndef ASCON_ACCEL_STREAM_AEAD128_TOP_V
`define ASCON_ACCEL_STREAM_AEAD128_TOP_V

`include "ascon_accel_regs.vh"
`include "ascon_accel_axis_defs.vh"

// -----------------------------------------------------------------------------
// Frozen-ABI MMIO control plane + stream-native AEAD128 data plane.
//
// This top-level wrapper is the SoC/firmware integration point for the real
// streaming backend.  It keeps the same register ABI as the older MMIO and
// bounded AXIS wrappers, but routes the data plane directly to the unified
// 128-bit stream backend:
//   * CONTROL/STATUS/MODE/LENGTH/KEY/NONCE/TAG/CYCLE registers remain MMIO;
//   * s_axis carries AD followed by plaintext/ciphertext beats;
//   * m_axis carries ciphertext/plaintext beats;
//   * CONTROL.DECRYPT selects encrypt or buffered authenticated decrypt;
//   * MMIO DATA_IN/DATA_OUT registers are retained only for ABI visibility and
//     debug status.  Bulk data for this top must use AXI Stream.
// -----------------------------------------------------------------------------
module ascon_accel_stream_aead128_top #(
  parameter integer DATA_BYTES     = 16,
  parameter integer DATA_WIDTH     = DATA_BYTES * 8,
  parameter integer MAX_TEXT_BYTES = 1024,
  parameter integer MAX_TEXT_BITS  = MAX_TEXT_BYTES * 8
) (
  input  wire                    clk_i,
  input  wire                    rstn_i,

  // Frozen CSR/MMIO control plane.
  input  wire                    bus_valid_i,
  input  wire                    bus_write_i,
  input  wire [7:0]              bus_addr_i,
  input  wire [31:0]             bus_wdata_i,
  input  wire [3:0]              bus_wstrb_i,
  output wire [31:0]             bus_rdata_o,
  output wire                    bus_ready_o,
  output wire                    irq_o,

  // 128-bit AXI4-Stream-style input data plane.
  input  wire [DATA_WIDTH-1:0]   s_axis_tdata,
  input  wire [DATA_BYTES-1:0]   s_axis_tkeep,
  input  wire                    s_axis_tvalid,
  output wire                    s_axis_tready,
  input  wire                    s_axis_tlast,
  input  wire [3:0]              s_axis_tuser,

  // 128-bit AXI4-Stream-style output data plane.
  output wire [DATA_WIDTH-1:0]   m_axis_tdata,
  output wire [DATA_BYTES-1:0]   m_axis_tkeep,
  output wire                    m_axis_tvalid,
  input  wire                    m_axis_tready,
  output wire                    m_axis_tlast,
  output wire [3:0]              m_axis_tuser
);

  wire         core_start_w;
  wire         core_clear_w;
  wire         core_decrypt_w;
  wire [3:0]   core_mode_w;
  wire [31:0]  core_ad_len_w;
  wire [31:0]  core_text_len_w;
  wire [31:0]  core_out_len_w;
  wire [31:0]  core_custom_len_w;
  wire [127:0] core_key_w;
  wire [127:0] core_nonce_w;
  wire [127:0] core_expected_tag_w;

  wire         mmio_data_in_pulse_w;
  wire [31:0]  mmio_data_in_w;
  wire [31:0]  mmio_data_in_ctrl_w;
  wire         mmio_data_out_read_pulse_w;

  wire         stream_busy_w;
  wire         stream_done_w;
  wire         stream_tag_valid_w;
  wire         stream_error_w;
  wire [31:0]  stream_error_code_w;
  wire [127:0] stream_generated_tag_w;

  wire [31:0]  stream_data_out_word_w;
  wire [31:0]  stream_data_out_ctrl_w;

  // Preserve DATA_OUT register visibility for software diagnostics.  The stream
  // handshake is still controlled only by m_axis_tready.
  assign stream_data_out_word_w = m_axis_tdata[31:0];
  assign stream_data_out_ctrl_w = (m_axis_tvalid ? `ASCON_DATA_VALID : 32'h00000000) |
                                  (m_axis_tlast  ? `ASCON_DATA_LAST  : 32'h00000000) |
                                  ({28'h0000000, m_axis_tkeep[3:0]} << `ASCON_DATA_KEEP_SHIFT) |
                                  `ASCON_DATA_TEXT;

  ascon_accel_mmio_regs #(
    .CAPABILITIES(`ASCON_CAP_AEAD128 |
                  `ASCON_CAP_DECRYPT_BUFFERED |
                  `ASCON_CAP_CONSTTIME_TAG_COMPARE |
                  `ASCON_CAP_STREAMING_BYTEMASK |
                  `ASCON_CAP_CYCLE_COUNTER |
                  `ASCON_CAP_AXI_STREAM_DATA)
  ) regs_i (
    .clk_i(clk_i),
    .rstn_i(rstn_i),
    .bus_valid_i(bus_valid_i),
    .bus_write_i(bus_write_i),
    .bus_addr_i(bus_addr_i),
    .bus_wdata_i(bus_wdata_i),
    .bus_wstrb_i(bus_wstrb_i),
    .bus_rdata_o(bus_rdata_o),
    .bus_ready_o(bus_ready_o),
    .irq_o(irq_o),
    .core_start_o(core_start_w),
    .core_clear_o(core_clear_w),
    .core_decrypt_o(core_decrypt_w),
    .core_mode_o(core_mode_w),
    .core_ad_len_o(core_ad_len_w),
    .core_text_len_o(core_text_len_w),
    .core_out_len_o(core_out_len_w),
    .core_custom_len_o(core_custom_len_w),
    .core_key_o(core_key_w),
    .core_nonce_o(core_nonce_w),
    .core_expected_tag_o(core_expected_tag_w),
    .core_data_in_pulse_o(mmio_data_in_pulse_w),
    .core_data_in_o(mmio_data_in_w),
    .core_data_in_ctrl_o(mmio_data_in_ctrl_w),
    .core_data_out_read_pulse_o(mmio_data_out_read_pulse_w),
    .core_busy_i(stream_busy_w),
    .core_done_i(stream_done_w),
    .core_tag_valid_i(stream_tag_valid_w),
    .core_error_i(stream_error_w),
    .core_error_code_i(stream_error_code_w),
    .core_data_out_i(stream_data_out_word_w),
    .core_data_out_ctrl_i(stream_data_out_ctrl_w),
    .core_generated_tag_i(stream_generated_tag_w)
  );

  ascon_aead128_stream #(
    .DATA_BYTES(DATA_BYTES),
    .DATA_WIDTH(DATA_WIDTH),
    .MAX_TEXT_BYTES(MAX_TEXT_BYTES),
    .MAX_TEXT_BITS(MAX_TEXT_BITS)
  ) stream_backend_i (
    .clk_i(clk_i),
    .rstn_i(rstn_i),
    .start_i(core_start_w),
    .clear_i(core_clear_w),
    .decrypt_i(core_decrypt_w),
    .mode_i(core_mode_w),
    .ad_len_i(core_ad_len_w),
    .text_len_i(core_text_len_w),
    .out_len_i(core_out_len_w),
    .custom_len_i(core_custom_len_w),
    .key_i(core_key_w),
    .nonce_i(core_nonce_w),
    .expected_tag_i(core_expected_tag_w),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tkeep(s_axis_tkeep),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tlast(s_axis_tlast),
    .s_axis_tuser(s_axis_tuser),
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tkeep(m_axis_tkeep),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),
    .m_axis_tlast(m_axis_tlast),
    .m_axis_tuser(m_axis_tuser),
    .busy_o(stream_busy_w),
    .done_o(stream_done_w),
    .tag_valid_o(stream_tag_valid_w),
    .error_o(stream_error_w),
    .error_code_o(stream_error_code_w),
    .generated_tag_o(stream_generated_tag_w)
  );

  // Explicitly mark the compatibility-only MMIO data-plane signals as observed.
  // DATA_IN writes do not feed this stream-native top; use s_axis for bulk data.
  wire mmio_data_compat_unused_w = mmio_data_in_pulse_w |
                                   mmio_data_out_read_pulse_w |
                                   (|mmio_data_in_w) |
                                   (|mmio_data_in_ctrl_w);

endmodule

`endif // ASCON_ACCEL_STREAM_AEAD128_TOP_V
