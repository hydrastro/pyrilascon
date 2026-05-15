`ifndef ASCON_ACCEL_AXIS_AEAD128_TOP_V
`define ASCON_ACCEL_AXIS_AEAD128_TOP_V

`include "ascon_accel_regs.vh"
`include "ascon_accel_axis_defs.vh"

// -----------------------------------------------------------------------------
// Frozen-ABI control/status + AXI4-Stream-style data-plane top for AEAD128.
//
// This is the first bridge between the existing register-buffered AEAD128 backend
// and the intended FPGA architecture:
//   * MMIO/CSR bus configures key, nonce, lengths, mode, tag, start/clear;
//   * S_AXIS carries AD and plaintext/ciphertext words before START;
//   * M_AXIS returns ciphertext/plaintext words after DONE;
//   * DATA_IN/DATA_OUT MMIO registers are still kept for backward compatibility.
//
// The current backend is bounded to 32 bytes of AD and 32 bytes of text.  This
// wrapper freezes the data-plane handshake so that a later high-throughput core
// can replace the backend without changing software-visible control semantics.
// -----------------------------------------------------------------------------
module ascon_accel_axis_aead128_top (
  input  wire        clk_i,
  input  wire        rstn_i,

  // Frozen CSR/MMIO control plane.
  input  wire        bus_valid_i,
  input  wire        bus_write_i,
  input  wire [7:0]  bus_addr_i,
  input  wire [31:0] bus_wdata_i,
  input  wire [3:0]  bus_wstrb_i,
  output wire [31:0] bus_rdata_o,
  output wire        bus_ready_o,
  output wire        irq_o,

  // Input AXI4-Stream-style data plane.
  input  wire [31:0] s_axis_tdata,
  input  wire [3:0]  s_axis_tkeep,
  input  wire        s_axis_tvalid,
  output wire        s_axis_tready,
  input  wire        s_axis_tlast,
  input  wire [3:0]  s_axis_tuser,

  // Output AXI4-Stream-style data plane.
  output wire [31:0] m_axis_tdata,
  output wire [3:0]  m_axis_tkeep,
  output wire        m_axis_tvalid,
  input  wire        m_axis_tready,
  output wire        m_axis_tlast,
  output wire [3:0]  m_axis_tuser
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
  wire         core_busy_w;
  wire         core_done_w;
  wire         core_tag_valid_w;
  wire         core_error_w;
  wire [31:0]  core_error_code_w;
  wire [31:0]  core_data_out_w;
  wire [31:0]  core_data_out_ctrl_w;
  wire [127:0] core_generated_tag_w;

  reg          output_active_q;

  wire         axis_in_fire_w;
  wire         axis_out_fire_w;
  wire [31:0] axis_data_ctrl_w;
  wire [31:0] selected_data_in_w;
  wire [31:0] selected_data_ctrl_w;
  wire         selected_data_pulse_w;
  wire         selected_data_out_read_w;
  wire         out_valid_w;

  assign s_axis_tready = !core_busy_w;
  assign axis_in_fire_w = s_axis_tvalid && s_axis_tready;

  assign axis_data_ctrl_w = `ASCON_DATA_VALID |
                            (s_axis_tlast ? `ASCON_DATA_LAST : 32'h00000000) |
                            ({28'h0000000, s_axis_tkeep} << `ASCON_DATA_KEEP_SHIFT) |
                            ((s_axis_tuser == `ASCON_AXIS_USER_AD)     ? `ASCON_DATA_AD     : 32'h00000000) |
                            ((s_axis_tuser == `ASCON_AXIS_USER_TEXT)   ? `ASCON_DATA_TEXT   : 32'h00000000) |
                            ((s_axis_tuser == `ASCON_AXIS_USER_CUSTOM) ? `ASCON_DATA_CUSTOM : 32'h00000000);

  // AXIS input has priority when both data paths are used in the same cycle.
  assign selected_data_pulse_w = axis_in_fire_w | mmio_data_in_pulse_w;
  assign selected_data_in_w    = axis_in_fire_w ? s_axis_tdata : mmio_data_in_w;
  assign selected_data_ctrl_w  = axis_in_fire_w ? axis_data_ctrl_w : mmio_data_in_ctrl_w;

  assign out_valid_w = output_active_q && ((core_data_out_ctrl_w & `ASCON_DATA_VALID) != 32'h00000000);
  assign axis_out_fire_w = out_valid_w && m_axis_tready;
  assign selected_data_out_read_w = axis_out_fire_w | mmio_data_out_read_pulse_w;

  assign m_axis_tdata  = core_data_out_w;
  assign m_axis_tkeep  = core_data_out_ctrl_w[`ASCON_DATA_KEEP_SHIFT +: 4];
  assign m_axis_tvalid = out_valid_w;
  assign m_axis_tlast  = ((core_data_out_ctrl_w & `ASCON_DATA_LAST) != 32'h00000000);
  assign m_axis_tuser  = `ASCON_AXIS_USER_TEXT;

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
    .core_busy_i(core_busy_w),
    .core_done_i(core_done_w),
    .core_tag_valid_i(core_tag_valid_w),
    .core_error_i(core_error_w),
    .core_error_code_i(core_error_code_w),
    .core_data_out_i(core_data_out_w),
    .core_data_out_ctrl_i(core_data_out_ctrl_w),
    .core_generated_tag_i(core_generated_tag_w)
  );

  ascon_aead128_mmio_backend backend_i (
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
    .data_in_pulse_i(selected_data_pulse_w),
    .data_in_i(selected_data_in_w),
    .data_in_ctrl_i(selected_data_ctrl_w),
    .data_out_read_pulse_i(selected_data_out_read_w),
    .busy_o(core_busy_w),
    .done_o(core_done_w),
    .tag_valid_o(core_tag_valid_w),
    .error_o(core_error_w),
    .error_code_o(core_error_code_w),
    .data_out_o(core_data_out_w),
    .data_out_ctrl_o(core_data_out_ctrl_w),
    .generated_tag_o(core_generated_tag_w)
  );

  always @(posedge clk_i or negedge rstn_i) begin
    if (!rstn_i) begin
      output_active_q <= 1'b0;
    end else begin
      if (core_clear_w || core_start_w) begin
        output_active_q <= 1'b0;
      end else if (core_done_w && !core_error_w) begin
        output_active_q <= 1'b1;
      end else if (axis_out_fire_w && m_axis_tlast) begin
        output_active_q <= 1'b0;
      end
    end
  end

endmodule

`endif
