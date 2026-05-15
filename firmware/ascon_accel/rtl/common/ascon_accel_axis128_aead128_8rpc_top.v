`ifndef ASCON_ACCEL_AXIS128_AEAD128_8RPC_TOP_V
`define ASCON_ACCEL_AXIS128_AEAD128_8RPC_TOP_V

`include "ascon_accel_regs.vh"
`include "ascon_accel_axis_defs.vh"

// -----------------------------------------------------------------------------
// 128-bit AXI4-Stream-style data plane + frozen CSR/MMIO control plane.
//
// This is the first high-throughput FPGA candidate top:
//   * 128-bit stream beats with 16-bit tkeep final-byte mask;
//   * eight Ascon rounds per cycle backend, so p8=1 cycle and p12=2 cycles;
//   * same frozen CSR/MMIO ABI as the slow core;
//   * same externally visible decrypt safety policy.
//
// The current backend is still bounded to small register-buffered messages and
// this bridge serializes each 128-bit input beat into four internal 32-bit words.
// The interface and permutation cadence are the important migration points; a
// later backend can consume/produce full 128-bit stream beats directly.
// -----------------------------------------------------------------------------
module ascon_accel_axis128_aead128_8rpc_top (
  input  wire         clk_i,
  input  wire         rstn_i,

  // Frozen CSR/MMIO control plane.
  input  wire         bus_valid_i,
  input  wire         bus_write_i,
  input  wire [7:0]   bus_addr_i,
  input  wire [31:0]  bus_wdata_i,
  input  wire [3:0]   bus_wstrb_i,
  output wire [31:0]  bus_rdata_o,
  output wire         bus_ready_o,
  output wire         irq_o,

  // 128-bit input AXI4-Stream-style data plane.
  input  wire [127:0] s_axis_tdata,
  input  wire [15:0]  s_axis_tkeep,
  input  wire         s_axis_tvalid,
  output wire         s_axis_tready,
  input  wire         s_axis_tlast,
  input  wire [3:0]   s_axis_tuser,

  // 128-bit output AXI4-Stream-style data plane.
  output wire [127:0] m_axis_tdata,
  output wire [15:0]  m_axis_tkeep,
  output wire         m_axis_tvalid,
  input  wire         m_axis_tready,
  output wire         m_axis_tlast,
  output wire [3:0]   m_axis_tuser
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

  // 128-bit input beat splitter.
  reg          in_split_active_q;
  reg [1:0]    in_lane_q;
  reg [127:0]  in_data_hold_q;
  reg [15:0]   in_keep_hold_q;
  reg          in_last_hold_q;
  reg [3:0]    in_user_hold_q;

  wire         axis_in_accept_w;
  wire [31:0] axis_data_word_w;
  wire [3:0]  axis_keep_word_w;
  wire [31:0] axis_data_ctrl_w;
  wire         axis_data_pulse_w;

  assign s_axis_tready = !core_busy_w && !in_split_active_q;
  assign axis_in_accept_w = s_axis_tvalid && s_axis_tready;

  assign axis_data_word_w = (in_lane_q == 2'd0) ? in_data_hold_q[31:0] :
                            (in_lane_q == 2'd1) ? in_data_hold_q[63:32] :
                            (in_lane_q == 2'd2) ? in_data_hold_q[95:64] :
                                                   in_data_hold_q[127:96];

  assign axis_keep_word_w = (in_lane_q == 2'd0) ? in_keep_hold_q[3:0] :
                            (in_lane_q == 2'd1) ? in_keep_hold_q[7:4] :
                            (in_lane_q == 2'd2) ? in_keep_hold_q[11:8] :
                                                   in_keep_hold_q[15:12];

  assign axis_data_ctrl_w = `ASCON_DATA_VALID |
                            ((in_user_hold_q == `ASCON_AXIS_USER_AD) ? `ASCON_DATA_AD : 32'h00000000) |
                            ((in_user_hold_q == `ASCON_AXIS_USER_TEXT) ? `ASCON_DATA_TEXT : 32'h00000000) |
                            ((in_user_hold_q == `ASCON_AXIS_USER_CUSTOM) ? `ASCON_DATA_CUSTOM : 32'h00000000) |
                            ((in_last_hold_q && (in_lane_q == 2'd3)) ? `ASCON_DATA_LAST : 32'h00000000) |
                            ({28'h0000000, axis_keep_word_w} << `ASCON_DATA_KEEP_SHIFT);

  assign axis_data_pulse_w = in_split_active_q;

  wire [31:0] selected_data_in_w = axis_data_pulse_w ? axis_data_word_w : mmio_data_in_w;
  wire [31:0] selected_data_ctrl_w = axis_data_pulse_w ? axis_data_ctrl_w : mmio_data_in_ctrl_w;
  wire        selected_data_pulse_w = axis_data_pulse_w | mmio_data_in_pulse_w;

  // 32-bit backend output packer into 128-bit stream beats.
  reg          out_collect_active_q;
  reg [1:0]    out_lane_q;
  reg [127:0]  out_beat_data_q;
  reg [15:0]   out_beat_keep_q;
  reg          out_beat_last_q;
  reg          out_beat_valid_q;

  wire [3:0]   core_data_keep_w = core_data_out_ctrl_w[`ASCON_DATA_KEEP_SHIFT +: 4];
  wire         core_data_valid_w = (core_data_out_ctrl_w & `ASCON_DATA_VALID) != 32'h00000000;
  wire         core_data_last_w  = (core_data_out_ctrl_w & `ASCON_DATA_LAST)  != 32'h00000000;
  wire         axis_out_read_w   = out_collect_active_q && !out_beat_valid_q && core_data_valid_w;

  assign m_axis_tdata  = out_beat_data_q;
  assign m_axis_tkeep  = out_beat_keep_q;
  assign m_axis_tvalid = out_beat_valid_q;
  assign m_axis_tlast  = out_beat_last_q;
  assign m_axis_tuser  = `ASCON_AXIS_USER_TEXT;

  wire selected_data_out_read_w = axis_out_read_w | mmio_data_out_read_pulse_w;

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

  ascon_aead128_mmio_backend_8rpc backend_i (
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
      in_split_active_q <= 1'b0;
      in_lane_q <= 2'd0;
      in_data_hold_q <= 128'b0;
      in_keep_hold_q <= 16'b0;
      in_last_hold_q <= 1'b0;
      in_user_hold_q <= `ASCON_AXIS_USER_NONE;
      out_collect_active_q <= 1'b0;
      out_lane_q <= 2'd0;
      out_beat_data_q <= 128'b0;
      out_beat_keep_q <= 16'b0;
      out_beat_last_q <= 1'b0;
      out_beat_valid_q <= 1'b0;
    end else begin
      if (core_clear_w || core_start_w) begin
        out_collect_active_q <= 1'b0;
        out_lane_q <= 2'd0;
        out_beat_data_q <= 128'b0;
        out_beat_keep_q <= 16'b0;
        out_beat_last_q <= 1'b0;
        out_beat_valid_q <= 1'b0;
      end

      if (axis_in_accept_w) begin
        in_split_active_q <= 1'b1;
        in_lane_q <= 2'd0;
        in_data_hold_q <= s_axis_tdata;
        in_keep_hold_q <= s_axis_tkeep;
        in_last_hold_q <= s_axis_tlast;
        in_user_hold_q <= s_axis_tuser;
      end else if (in_split_active_q) begin
        if (in_lane_q == 2'd3) begin
          in_split_active_q <= 1'b0;
          in_lane_q <= 2'd0;
        end else begin
          in_lane_q <= in_lane_q + 2'd1;
        end
      end

      if (core_done_w && !core_error_w) begin
        out_collect_active_q <= 1'b1;
        out_lane_q <= 2'd0;
        out_beat_data_q <= 128'b0;
        out_beat_keep_q <= 16'b0;
        out_beat_last_q <= 1'b0;
        out_beat_valid_q <= 1'b0;
      end else if (axis_out_read_w) begin
        case (out_lane_q)
          2'd0: begin
            out_beat_data_q[31:0] <= core_data_out_w;
            out_beat_keep_q[3:0] <= core_data_keep_w;
          end
          2'd1: begin
            out_beat_data_q[63:32] <= core_data_out_w;
            out_beat_keep_q[7:4] <= core_data_keep_w;
          end
          2'd2: begin
            out_beat_data_q[95:64] <= core_data_out_w;
            out_beat_keep_q[11:8] <= core_data_keep_w;
          end
          default: begin
            out_beat_data_q[127:96] <= core_data_out_w;
            out_beat_keep_q[15:12] <= core_data_keep_w;
          end
        endcase

        if (core_data_last_w || (out_lane_q == 2'd3)) begin
          out_beat_last_q <= core_data_last_w;
          out_beat_valid_q <= 1'b1;
          out_collect_active_q <= 1'b0;
          out_lane_q <= 2'd0;
        end else begin
          out_lane_q <= out_lane_q + 2'd1;
        end
      end else if (out_beat_valid_q && m_axis_tready) begin
        out_beat_valid_q <= 1'b0;
        if (out_beat_last_q) begin
          out_collect_active_q <= 1'b0;
        end else begin
          out_collect_active_q <= 1'b1;
          out_lane_q <= 2'd0;
          out_beat_data_q <= 128'b0;
          out_beat_keep_q <= 16'b0;
          out_beat_last_q <= 1'b0;
        end
      end
    end
  end

endmodule

`endif
