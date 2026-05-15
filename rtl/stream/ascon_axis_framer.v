`ifndef ASCON_AXIS_FRAMER_V
`define ASCON_AXIS_FRAMER_V

`include "ascon_accel_regs.vh"
`include "ascon_accel_axis_defs.vh"

// -----------------------------------------------------------------------------
// AXI4-Stream packet framer / protocol checker.
//
// This block is deliberately ASCON-agnostic. It converts one logical AXI stream
// packet into validated fixed-width blocks and checks the contract documented in
// docs/streaming_aead_contract.md:
//   * tkeep must be contiguous from lane 0;
//   * only the final beat may be partial;
//   * the final beat must carry tlast;
//   * the accumulated byte count must match expected_len_i;
//   * tuser must match the active stream kind when expected_user_i is not NONE.
//
// Zero-length packets are represented by expected_len_i == 0 and no AXI beats;
// asserting start_i immediately completes the packet.
// -----------------------------------------------------------------------------
module ascon_axis_framer #(
  parameter integer DATA_BYTES = 16,
  parameter integer DATA_WIDTH = DATA_BYTES * 8
) (
  input  wire                    clk_i,
  input  wire                    rstn_i,
  input  wire                    clear_i,
  input  wire                    start_i,
  input  wire [31:0]             expected_len_i,
  input  wire [3:0]              expected_user_i,

  input  wire [DATA_WIDTH-1:0]   s_axis_tdata,
  input  wire [DATA_BYTES-1:0]   s_axis_tkeep,
  input  wire                    s_axis_tvalid,
  output wire                    s_axis_tready,
  input  wire                    s_axis_tlast,
  input  wire [3:0]              s_axis_tuser,

  output reg  [DATA_WIDTH-1:0]   block_data_o,
  output reg  [7:0]              block_bytes_o,
  output reg                     block_last_o,
  output reg  [3:0]              block_user_o,
  output reg                     block_valid_o,
  input  wire                    block_ready_i,

  output reg                     done_o,
  output reg                     error_o,
  output reg  [31:0]             error_code_o,
  output reg  [31:0]             bytes_seen_o
);

  wire sink_ready_w;
  wire fire_w;
  wire keep_contiguous_w;
  wire keep_nonzero_w;
  wire kind_ok_w;
  wire partial_w;
  wire overflow_w;
  wire exact_end_without_last_w;
  wire short_final_w;
  wire protocol_error_w;
  wire [7:0] keep_count_w;
  wire [31:0] next_seen_w;

  assign sink_ready_w = (!done_o) && (!error_o) && ((!block_valid_o) || block_ready_i);
  assign s_axis_tready = sink_ready_w;
  assign fire_w = s_axis_tvalid && s_axis_tready;

  assign keep_count_w = keep_count(s_axis_tkeep);
  assign keep_contiguous_w = is_contiguous_keep(s_axis_tkeep);
  assign keep_nonzero_w = |s_axis_tkeep;
  assign kind_ok_w = (expected_user_i == `ASCON_AXIS_USER_NONE) || (s_axis_tuser == expected_user_i);
  assign partial_w = keep_count_w != DATA_BYTES;
  assign next_seen_w = bytes_seen_o + {24'h000000, keep_count_w};
  assign overflow_w = next_seen_w > expected_len_i;
  assign exact_end_without_last_w = (next_seen_w == expected_len_i) && (!s_axis_tlast);
  assign short_final_w = s_axis_tlast && (next_seen_w != expected_len_i);

  assign protocol_error_w = (!keep_contiguous_w) ||
                            (!keep_nonzero_w) ||
                            (!kind_ok_w) ||
                            ((!s_axis_tlast) && partial_w) ||
                            overflow_w ||
                            exact_end_without_last_w ||
                            short_final_w;

  always @(posedge clk_i or negedge rstn_i) begin
    if (!rstn_i) begin
      block_data_o  <= {DATA_WIDTH{1'b0}};
      block_bytes_o <= 8'h00;
      block_last_o  <= 1'b0;
      block_user_o  <= `ASCON_AXIS_USER_NONE;
      block_valid_o <= 1'b0;
      done_o        <= 1'b0;
      error_o       <= 1'b0;
      error_code_o  <= `ASCON_ERROR_NONE;
      bytes_seen_o  <= 32'h00000000;
    end else begin
      if (clear_i || start_i) begin
        block_data_o  <= {DATA_WIDTH{1'b0}};
        block_bytes_o <= 8'h00;
        block_last_o  <= 1'b0;
        block_user_o  <= expected_user_i;
        block_valid_o <= 1'b0;
        done_o        <= (start_i && (expected_len_i == 32'h00000000));
        error_o       <= 1'b0;
        error_code_o  <= `ASCON_ERROR_NONE;
        bytes_seen_o  <= 32'h00000000;
      end else begin
        if (block_valid_o && block_ready_i) begin
          block_valid_o <= 1'b0;
        end

        if (fire_w) begin
          if (protocol_error_w) begin
            block_valid_o <= 1'b0;
            done_o        <= 1'b0;
            error_o       <= 1'b1;
            error_code_o  <= `ASCON_ERROR_STREAM_PROTOCOL;
          end else begin
            block_data_o  <= s_axis_tdata;
            block_bytes_o <= keep_count_w;
            block_last_o  <= s_axis_tlast;
            block_user_o  <= s_axis_tuser;
            block_valid_o <= 1'b1;
            bytes_seen_o  <= next_seen_w;
            done_o        <= s_axis_tlast;
          end
        end
      end
    end
  end

  function [7:0] keep_count;
    input [DATA_BYTES-1:0] keep;
    integer i;
    reg found_zero;
    begin
      keep_count = 8'h00;
      found_zero = 1'b0;
      for (i = 0; i < DATA_BYTES; i = i + 1) begin
        if (!found_zero && keep[i]) begin
          keep_count = keep_count + 8'h01;
        end else begin
          found_zero = 1'b1;
        end
      end
    end
  endfunction

  function is_contiguous_keep;
    input [DATA_BYTES-1:0] keep;
    integer i;
    reg found_zero;
    begin
      is_contiguous_keep = 1'b1;
      found_zero = 1'b0;
      for (i = 0; i < DATA_BYTES; i = i + 1) begin
        if (!keep[i]) begin
          found_zero = 1'b1;
        end else if (found_zero) begin
          is_contiguous_keep = 1'b0;
        end
      end
    end
  endfunction

endmodule

`endif
