`ifndef ASCON_ACCEL_MMIO_STUB_TOP_V
`define ASCON_ACCEL_MMIO_STUB_TOP_V

`include "ascon_accel_regs.vh"

module ascon_accel_mmio_stub_top (
  input  wire        clk_i,
  input  wire        rstn_i,
  input  wire        bus_valid_i,
  input  wire        bus_write_i,
  input  wire [7:0]  bus_addr_i,
  input  wire [31:0] bus_wdata_i,
  input  wire [3:0]  bus_wstrb_i,
  output wire [31:0] bus_rdata_o,
  output wire        bus_ready_o,
  output wire        irq_o
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
  wire         core_data_in_pulse_w;
  wire [31:0]  core_data_in_w;
  wire [31:0]  core_data_in_ctrl_w;
  wire         core_data_out_read_pulse_w;
  wire         core_busy_w;
  wire         core_done_w;
  wire         core_tag_valid_w;
  wire         core_error_w;
  wire [31:0]  core_error_code_w;
  wire [31:0]  core_data_out_w;
  wire [31:0]  core_data_out_ctrl_w;
  wire [127:0] core_generated_tag_w;

  ascon_accel_mmio_regs #(
    .CAPABILITIES(`ASCON_CAP_AEAD128 |
                  `ASCON_CAP_DECRYPT_BUFFERED |
                  `ASCON_CAP_CONSTTIME_TAG_COMPARE |
                  `ASCON_CAP_CYCLE_COUNTER)
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
    .core_data_in_pulse_o(core_data_in_pulse_w),
    .core_data_in_o(core_data_in_w),
    .core_data_in_ctrl_o(core_data_in_ctrl_w),
    .core_data_out_read_pulse_o(core_data_out_read_pulse_w),
    .core_busy_i(core_busy_w),
    .core_done_i(core_done_w),
    .core_tag_valid_i(core_tag_valid_w),
    .core_error_i(core_error_w),
    .core_error_code_i(core_error_code_w),
    .core_data_out_i(core_data_out_w),
    .core_data_out_ctrl_i(core_data_out_ctrl_w),
    .core_generated_tag_i(core_generated_tag_w)
  );

  ascon_accel_core_stub stub_i (
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
    .data_in_pulse_i(core_data_in_pulse_w),
    .data_in_i(core_data_in_w),
    .data_in_ctrl_i(core_data_in_ctrl_w),
    .data_out_read_pulse_i(core_data_out_read_pulse_w),
    .busy_o(core_busy_w),
    .done_o(core_done_w),
    .tag_valid_o(core_tag_valid_w),
    .error_o(core_error_w),
    .error_code_o(core_error_code_w),
    .data_out_o(core_data_out_w),
    .data_out_ctrl_o(core_data_out_ctrl_w),
    .generated_tag_o(core_generated_tag_w)
  );

endmodule

`endif
