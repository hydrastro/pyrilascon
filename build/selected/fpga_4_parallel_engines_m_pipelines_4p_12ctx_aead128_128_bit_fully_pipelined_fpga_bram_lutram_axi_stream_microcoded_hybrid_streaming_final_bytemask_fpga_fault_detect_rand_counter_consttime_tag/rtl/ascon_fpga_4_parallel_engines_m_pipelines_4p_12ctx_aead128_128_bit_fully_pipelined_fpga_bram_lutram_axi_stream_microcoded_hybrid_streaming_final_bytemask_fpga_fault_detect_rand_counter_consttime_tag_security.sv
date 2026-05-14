// Generated ASCON security/fault/decryption-release skeleton.
// profile=fpga_fault_detect_rand_counter_consttime_tag, side_channel=none, fault_detection=duplicate_compute
// constant_time_tag_compare=true, randomized_counter_hardening=true
// plaintext_release_policy=buffer_until_tag_verify
// plaintext_buffer=bram_fifo, capacity_bytes=65536
// area_class=approximately_2x_compute_plus_buffer, performance_impact=slower_or_double_resources
module ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_security #(
  parameter int PLAINTEXT_BUFFER_CAPACITY_BYTES = 65536,
  parameter bit CONSTANT_TIME_TAG_COMPARE = 1,
  parameter bit RANDOMIZED_COUNTER_HARDENING = 1,
  parameter bit DUPLICATE_COMPUTE_CHECK = 1
) (
  input  logic clk,
  input  logic rst_n,
  input  logic tag_compare_start_i,
  input  logic [127:0] tag_expected_i,
  input  logic [127:0] tag_actual_i,
  output logic tag_valid_o,
  output logic fault_o
);

  logic [127:0] tag_diff;
  assign tag_diff = tag_expected_i ^ tag_actual_i;

  // Constant-time tag compare shape: OR-reduce all differences; do not early-exit.
  assign tag_valid_o = tag_compare_start_i & ~(|tag_diff);

  // TODO: bind duplicate-computation comparison and randomized counter hardening backends.
  assign fault_o = 1'b0;
endmodule
