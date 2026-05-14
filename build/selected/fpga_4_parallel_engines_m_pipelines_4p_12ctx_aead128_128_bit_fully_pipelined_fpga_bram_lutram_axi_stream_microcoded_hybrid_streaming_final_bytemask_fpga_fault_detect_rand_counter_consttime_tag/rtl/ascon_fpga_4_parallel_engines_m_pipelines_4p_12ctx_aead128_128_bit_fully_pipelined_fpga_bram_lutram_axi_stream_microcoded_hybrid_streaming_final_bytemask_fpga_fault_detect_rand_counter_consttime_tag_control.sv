// Generated ASCON control/sequencer skeleton.
// profile=axi_stream_microcoded_hybrid
// area_class=high, flexibility=very_high
// scheduler=stream_scheduler_plus_microcode
// microcode_words=256, command_fifo_depth=32, csr_register_count=0
module ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_control #(
  parameter int MICROCODE_WORDS = 256,
  parameter int COMMAND_FIFO_DEPTH = 32,
  parameter int CSR_REGISTER_COUNT = 0,
  parameter int AXI_STREAM_COMMAND_CHANNELS = 3
) (
  input  logic clk,
  input  logic rst_n,
  input  logic start_i,
  output logic busy_o,
  output logic command_valid_o
);

  // TODO: replace this control scaffold with the selected control backend.
  assign busy_o = start_i;
  assign command_valid_o = start_i;
endmodule
