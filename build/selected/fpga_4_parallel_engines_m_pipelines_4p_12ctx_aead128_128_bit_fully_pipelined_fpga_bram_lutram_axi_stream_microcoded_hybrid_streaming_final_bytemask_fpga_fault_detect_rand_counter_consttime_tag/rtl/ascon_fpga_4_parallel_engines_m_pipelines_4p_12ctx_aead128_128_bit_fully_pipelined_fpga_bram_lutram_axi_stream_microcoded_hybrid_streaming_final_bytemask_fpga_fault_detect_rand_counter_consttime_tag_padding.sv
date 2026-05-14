// Generated ASCON padding/final-block skeleton.
// profile=streaming_final_bytemask, strategy=inline_combinational, length_handling=streaming_final_bytemask
// area_class=medium, flexibility=high, streaming_efficiency=excellent_streaming
// final_bytemask=true, final_bytemask_width=64
module ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_padding #(
  parameter int DATA_BUS_BITS = 512,
  parameter int KEEP_BITS = 64,
  parameter int PARTIAL_BLOCK_BUFFER_BYTES = 64
) (
  input  logic clk,
  input  logic rst_n,
  input  logic valid_i,
  input  logic last_i,
  input  logic [DATA_BUS_BITS-1:0] data_i,
  input  logic [KEEP_BITS-1:0] keep_i,
  output logic valid_o,
  output logic [DATA_BUS_BITS-1:0] data_o,
  output logic [KEEP_BITS-1:0] keep_o
);

  // TODO: implement selected padding backend.
  // For streaming_final_bytemask, keep_i marks valid bytes on the final beat.
  // For rtl_performed, the FSM/counter determines the pad10* insertion point internally.
  assign valid_o = valid_i;
  assign data_o  = data_i;
  assign keep_o  = keep_i;
endmodule
