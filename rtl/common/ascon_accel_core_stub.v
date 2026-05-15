`ifndef ASCON_ACCEL_CORE_STUB_V
`define ASCON_ACCEL_CORE_STUB_V

`include "ascon_accel_regs.vh"

// Small synthesis/simulation stub used only to validate the frozen MMIO ABI.
// It is not the cryptographic core. Replace it with a real ASCON engine when
// integrating with the standalone AEAD128 RTL.
module ascon_accel_core_stub #(
  parameter integer DONE_DELAY_CYCLES = 8
) (
  input  wire         clk_i,
  input  wire         rstn_i,
  input  wire         start_i,
  input  wire         clear_i,
  input  wire         decrypt_i,
  input  wire [3:0]   mode_i,
  input  wire [31:0]  ad_len_i,
  input  wire [31:0]  text_len_i,
  input  wire [31:0]  out_len_i,
  input  wire [31:0]  custom_len_i,
  input  wire [127:0] key_i,
  input  wire [127:0] nonce_i,
  input  wire [127:0] expected_tag_i,
  input  wire         data_in_pulse_i,
  input  wire [31:0]  data_in_i,
  input  wire [31:0]  data_in_ctrl_i,
  input  wire         data_out_read_pulse_i,
  output reg          busy_o,
  output reg          done_o,
  output reg          tag_valid_o,
  output reg          error_o,
  output reg [31:0]   error_code_o,
  output reg [31:0]   data_out_o,
  output reg [31:0]   data_out_ctrl_o,
  output reg [127:0]  generated_tag_o
);

  reg [15:0] count_q;
  reg [31:0] last_input_q;

  always @(posedge clk_i or negedge rstn_i) begin
    if (!rstn_i) begin
      busy_o <= 1'b0;
      done_o <= 1'b0;
      tag_valid_o <= 1'b0;
      error_o <= 1'b0;
      error_code_o <= `ASCON_ERROR_NONE;
      data_out_o <= 32'h00000000;
      data_out_ctrl_o <= 32'h00000000;
      generated_tag_o <= 128'h00000000000000000000000000000000;
      count_q <= 16'h0000;
      last_input_q <= 32'h00000000;
    end else begin
      done_o <= 1'b0;

      if (clear_i) begin
        busy_o <= 1'b0;
        tag_valid_o <= 1'b0;
        error_o <= 1'b0;
        error_code_o <= `ASCON_ERROR_NONE;
        data_out_o <= 32'h00000000;
        data_out_ctrl_o <= 32'h00000000;
        generated_tag_o <= 128'h00000000000000000000000000000000;
        count_q <= 16'h0000;
        last_input_q <= 32'h00000000;
      end else begin
        if (data_in_pulse_i) begin
          last_input_q <= data_in_i;
        end

        if (start_i && !busy_o) begin
          busy_o <= 1'b1;
          count_q <= DONE_DELAY_CYCLES;
          tag_valid_o <= 1'b0;
          error_o <= 1'b0;
          error_code_o <= `ASCON_ERROR_NONE;
        end else if (busy_o) begin
          if (count_q == 16'h0000) begin
            busy_o <= 1'b0;
            done_o <= 1'b1;
            if (mode_i != `ASCON_MODE_AEAD128) begin
              error_o <= 1'b1;
              error_code_o <= `ASCON_ERROR_UNSUPPORTED_MODE;
              tag_valid_o <= 1'b0;
              data_out_ctrl_o <= 32'h00000000;
            end else begin
              error_o <= 1'b0;
              error_code_o <= `ASCON_ERROR_NONE;
              tag_valid_o <= decrypt_i ? 1'b1 : 1'b0;
              data_out_o <= last_input_q ^ 32'hA5A5A5A5;
              data_out_ctrl_o <= `ASCON_DATA_VALID | `ASCON_DATA_LAST | (32'hF << `ASCON_DATA_KEEP_SHIFT);
              generated_tag_o <= key_i ^ nonce_i ^ expected_tag_i ^
                                 {ad_len_i, text_len_i, out_len_i, custom_len_i};
            end
          end else begin
            count_q <= count_q - 16'h0001;
          end
        end
      end
    end
  end

endmodule

`endif
