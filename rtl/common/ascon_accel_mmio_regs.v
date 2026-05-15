`ifndef ASCON_ACCEL_MMIO_REGS_V
`define ASCON_ACCEL_MMIO_REGS_V

`include "ascon_accel_regs.vh"

// -----------------------------------------------------------------------------
// ASCON accelerator frozen-ABI MMIO register block.
//
// This module is intentionally algorithm-agnostic. It implements the software
// visible register map and exposes clean control/data signals to a future ASCON
// core implementation. Board-specific or CPU-specific wrappers should translate
// their local bus protocol into this simple one-cycle MMIO interface.
// -----------------------------------------------------------------------------
module ascon_accel_mmio_regs #(
  parameter [31:0] CAPABILITIES = (`ASCON_CAP_AEAD128 |
                                   `ASCON_CAP_DECRYPT_BUFFERED |
                                   `ASCON_CAP_CONSTTIME_TAG_COMPARE |
                                   `ASCON_CAP_CYCLE_COUNTER)
) (
  input  wire         clk_i,
  input  wire         rstn_i,

  // Simple byte-addressed 32-bit MMIO request interface.
  input  wire         bus_valid_i,
  input  wire         bus_write_i,
  input  wire [7:0]   bus_addr_i,
  input  wire [31:0]  bus_wdata_i,
  input  wire [3:0]   bus_wstrb_i,
  output reg  [31:0]  bus_rdata_o,
  output wire         bus_ready_o,

  // Interrupt output. High when DONE is set and IRQ_ENABLE is set.
  output wire         irq_o,

  // Control interface to the implementation core.
  output reg          core_start_o,
  output reg          core_clear_o,
  output wire         core_decrypt_o,
  output wire [3:0]   core_mode_o,
  output wire [31:0]  core_ad_len_o,
  output wire [31:0]  core_text_len_o,
  output wire [31:0]  core_out_len_o,
  output wire [31:0]  core_custom_len_o,
  output wire [127:0] core_key_o,
  output wire [127:0] core_nonce_o,
  output wire [127:0] core_expected_tag_o,

  // Register-staged data stream beat. A core can sample this on writes to
  // DATA_IN_CTRL when the VALID bit is set.
  output reg          core_data_in_pulse_o,
  output wire [31:0]  core_data_in_o,
  output wire [31:0]  core_data_in_ctrl_o,
  output reg          core_data_out_read_pulse_o,

  // Status/data returned by the implementation core.
  input  wire         core_busy_i,
  input  wire         core_done_i,
  input  wire         core_tag_valid_i,
  input  wire         core_error_i,
  input  wire [31:0]  core_error_code_i,
  input  wire [31:0]  core_data_out_i,
  input  wire [31:0]  core_data_out_ctrl_i,
  input  wire [127:0] core_generated_tag_i
);

  reg [31:0] control_q;
  reg [31:0] mode_q;
  reg [31:0] ad_len_q;
  reg [31:0] text_len_q;
  reg [31:0] out_len_q;
  reg [31:0] custom_len_q;

  reg [31:0] key_q [0:3];
  reg [31:0] nonce_q [0:3];
  reg [31:0] tag_q [0:3];

  reg [31:0] data_in_q;
  reg [31:0] data_in_ctrl_q;

  reg [63:0] cycle_count_q;
  reg [31:0] error_code_q;
  reg        done_q;
  reg        tag_valid_q;
  reg        error_q;

  wire write_access_w = bus_valid_i & bus_write_i;
  wire read_access_w  = bus_valid_i & ~bus_write_i;

  assign bus_ready_o = bus_valid_i;
  assign irq_o = done_q & ((control_q & `ASCON_CONTROL_IRQ_ENABLE) != 32'h00000000);

  assign core_decrypt_o      = (control_q & `ASCON_CONTROL_DECRYPT) != 32'h00000000;
  assign core_mode_o         = mode_q[3:0];
  assign core_ad_len_o       = ad_len_q;
  assign core_text_len_o     = text_len_q;
  assign core_out_len_o      = out_len_q;
  assign core_custom_len_o   = custom_len_q;
  assign core_key_o          = {key_q[3], key_q[2], key_q[1], key_q[0]};
  assign core_nonce_o        = {nonce_q[3], nonce_q[2], nonce_q[1], nonce_q[0]};
  assign core_expected_tag_o = {tag_q[3], tag_q[2], tag_q[1], tag_q[0]};
  assign core_data_in_o      = data_in_q;
  assign core_data_in_ctrl_o = data_in_ctrl_q;

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

  wire clear_w = write_access_w && (bus_addr_i == `ASCON_REG_CONTROL) &&
                 ((bus_wdata_i & `ASCON_CONTROL_CLEAR) != 32'h00000000);
  wire start_w = write_access_w && (bus_addr_i == `ASCON_REG_CONTROL) &&
                 ((bus_wdata_i & `ASCON_CONTROL_START) != 32'h00000000);

  integer i;
  always @(posedge clk_i or negedge rstn_i) begin
    if (!rstn_i) begin
      control_q <= 32'h00000000;
      mode_q <= 32'h00000000;
      ad_len_q <= 32'h00000000;
      text_len_q <= 32'h00000000;
      out_len_q <= 32'h00000000;
      custom_len_q <= 32'h00000000;
      data_in_q <= 32'h00000000;
      data_in_ctrl_q <= 32'h00000000;
      cycle_count_q <= 64'h0000000000000000;
      error_code_q <= `ASCON_ERROR_NONE;
      done_q <= 1'b0;
      tag_valid_q <= 1'b0;
      error_q <= 1'b0;
      core_start_o <= 1'b0;
      core_clear_o <= 1'b0;
      core_data_in_pulse_o <= 1'b0;
      core_data_out_read_pulse_o <= 1'b0;
      for (i = 0; i < 4; i = i + 1) begin
        key_q[i] <= 32'h00000000;
        nonce_q[i] <= 32'h00000000;
        tag_q[i] <= 32'h00000000;
      end
    end else begin
      core_start_o <= 1'b0;
      core_clear_o <= 1'b0;
      core_data_in_pulse_o <= 1'b0;
      core_data_out_read_pulse_o <= 1'b0;

      if (read_access_w && (bus_addr_i == `ASCON_REG_DATA_OUT)) begin
        core_data_out_read_pulse_o <= 1'b1;
      end

      if (core_busy_i) begin
        cycle_count_q <= cycle_count_q + 64'h0000000000000001;
      end

      if (clear_w) begin
        control_q <= control_q & `ASCON_CONTROL_IRQ_ENABLE;
        done_q <= 1'b0;
        tag_valid_q <= 1'b0;
        error_q <= 1'b0;
        error_code_q <= `ASCON_ERROR_NONE;
        cycle_count_q <= 64'h0000000000000000;
        core_clear_o <= 1'b1;
      end else begin
        if (write_access_w) begin
          case (bus_addr_i)
            `ASCON_REG_CONTROL: begin
              control_q <= apply_wstrb(control_q, bus_wdata_i, bus_wstrb_i) &
                           (`ASCON_CONTROL_DECRYPT | `ASCON_CONTROL_HASH |
                            `ASCON_CONTROL_XOF | `ASCON_CONTROL_CXOF |
                            `ASCON_CONTROL_IRQ_ENABLE);
              if ((bus_wdata_i & `ASCON_CONTROL_START) != 32'h00000000) begin
                done_q <= 1'b0;
                tag_valid_q <= 1'b0;
                error_q <= 1'b0;
                error_code_q <= `ASCON_ERROR_NONE;
                cycle_count_q <= 64'h0000000000000000;
                core_start_o <= 1'b1;
              end
            end
            `ASCON_REG_MODE:       mode_q <= apply_wstrb(mode_q, bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_AD_LEN:     ad_len_q <= apply_wstrb(ad_len_q, bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_TEXT_LEN:   text_len_q <= apply_wstrb(text_len_q, bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_OUT_LEN:    out_len_q <= apply_wstrb(out_len_q, bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_CUSTOM_LEN: custom_len_q <= apply_wstrb(custom_len_q, bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_KEY0:       key_q[0] <= apply_wstrb(key_q[0], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_KEY1:       key_q[1] <= apply_wstrb(key_q[1], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_KEY2:       key_q[2] <= apply_wstrb(key_q[2], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_KEY3:       key_q[3] <= apply_wstrb(key_q[3], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_NONCE0:     nonce_q[0] <= apply_wstrb(nonce_q[0], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_NONCE1:     nonce_q[1] <= apply_wstrb(nonce_q[1], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_NONCE2:     nonce_q[2] <= apply_wstrb(nonce_q[2], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_NONCE3:     nonce_q[3] <= apply_wstrb(nonce_q[3], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_DATA_IN:    data_in_q <= apply_wstrb(data_in_q, bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_DATA_IN_CTRL: begin
              data_in_ctrl_q <= apply_wstrb(data_in_ctrl_q, bus_wdata_i, bus_wstrb_i);
              if ((bus_wdata_i & `ASCON_DATA_VALID) != 32'h00000000) begin
                core_data_in_pulse_o <= 1'b1;
              end
            end
            `ASCON_REG_TAG0:       tag_q[0] <= apply_wstrb(tag_q[0], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_TAG1:       tag_q[1] <= apply_wstrb(tag_q[1], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_TAG2:       tag_q[2] <= apply_wstrb(tag_q[2], bus_wdata_i, bus_wstrb_i);
            `ASCON_REG_TAG3:       tag_q[3] <= apply_wstrb(tag_q[3], bus_wdata_i, bus_wstrb_i);
            default: begin
            end
          endcase
        end

        if (core_done_i) begin
          done_q <= 1'b1;
          tag_valid_q <= core_tag_valid_i;
          error_q <= core_error_i;
          error_code_q <= core_error_i ? core_error_code_i : `ASCON_ERROR_NONE;
          if (!core_decrypt_o) begin
            tag_q[0] <= core_generated_tag_i[31:0];
            tag_q[1] <= core_generated_tag_i[63:32];
            tag_q[2] <= core_generated_tag_i[95:64];
            tag_q[3] <= core_generated_tag_i[127:96];
          end
        end
      end
    end
  end

  always @* begin
    bus_rdata_o = 32'h00000000;
    if (read_access_w) begin
      case (bus_addr_i)
        `ASCON_REG_CONTROL:        bus_rdata_o = control_q;
        `ASCON_REG_STATUS:         bus_rdata_o = (core_busy_i ? `ASCON_STATUS_BUSY : 32'h00000000) |
                                                (done_q ? `ASCON_STATUS_DONE : 32'h00000000) |
                                                (tag_valid_q ? `ASCON_STATUS_TAG_VALID : 32'h00000000) |
                                                (error_q ? `ASCON_STATUS_ERROR : 32'h00000000) |
                                                `ASCON_STATUS_IN_READY |
                                                ((core_data_out_ctrl_i & `ASCON_DATA_VALID) ? `ASCON_STATUS_OUT_VALID : 32'h00000000);
        `ASCON_REG_MODE:           bus_rdata_o = mode_q;
        `ASCON_REG_CAPABILITIES:   bus_rdata_o = CAPABILITIES;
        `ASCON_REG_AD_LEN:         bus_rdata_o = ad_len_q;
        `ASCON_REG_TEXT_LEN:       bus_rdata_o = text_len_q;
        `ASCON_REG_OUT_LEN:        bus_rdata_o = out_len_q;
        `ASCON_REG_CUSTOM_LEN:     bus_rdata_o = custom_len_q;
        `ASCON_REG_KEY0:           bus_rdata_o = key_q[0];
        `ASCON_REG_KEY1:           bus_rdata_o = key_q[1];
        `ASCON_REG_KEY2:           bus_rdata_o = key_q[2];
        `ASCON_REG_KEY3:           bus_rdata_o = key_q[3];
        `ASCON_REG_NONCE0:         bus_rdata_o = nonce_q[0];
        `ASCON_REG_NONCE1:         bus_rdata_o = nonce_q[1];
        `ASCON_REG_NONCE2:         bus_rdata_o = nonce_q[2];
        `ASCON_REG_NONCE3:         bus_rdata_o = nonce_q[3];
        `ASCON_REG_DATA_IN:        bus_rdata_o = data_in_q;
        `ASCON_REG_DATA_IN_CTRL:   bus_rdata_o = data_in_ctrl_q;
        `ASCON_REG_DATA_OUT:       bus_rdata_o = core_data_out_i;
        `ASCON_REG_DATA_OUT_CTRL:  bus_rdata_o = core_data_out_ctrl_i;
        `ASCON_REG_TAG0:           bus_rdata_o = tag_q[0];
        `ASCON_REG_TAG1:           bus_rdata_o = tag_q[1];
        `ASCON_REG_TAG2:           bus_rdata_o = tag_q[2];
        `ASCON_REG_TAG3:           bus_rdata_o = tag_q[3];
        `ASCON_REG_CYCLE_COUNT_LO: bus_rdata_o = cycle_count_q[31:0];
        `ASCON_REG_CYCLE_COUNT_HI: bus_rdata_o = cycle_count_q[63:32];
        `ASCON_REG_ERROR_CODE:     bus_rdata_o = error_code_q;
        `ASCON_REG_ABI_VERSION:    bus_rdata_o = `ASCON_ACCEL_ABI_VERSION;
        default:                   bus_rdata_o = 32'h00000000;
      endcase
    end
  end

endmodule

`endif
