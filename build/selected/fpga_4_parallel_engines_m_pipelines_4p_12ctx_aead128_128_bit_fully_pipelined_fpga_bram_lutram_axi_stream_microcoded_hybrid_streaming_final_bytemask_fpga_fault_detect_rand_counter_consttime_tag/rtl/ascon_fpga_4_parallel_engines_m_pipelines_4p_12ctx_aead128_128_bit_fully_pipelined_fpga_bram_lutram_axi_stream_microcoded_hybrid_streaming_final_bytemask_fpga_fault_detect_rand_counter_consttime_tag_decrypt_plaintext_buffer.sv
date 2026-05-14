// Generated ASCON decrypt plaintext release buffer skeleton.
// Decryption plaintext must not be externally released until tag verification succeeds.
// storage=bram_fifo, capacity_bytes=65536
module ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_decrypt_plaintext_buffer #(
  parameter int DATA_BUS_BITS = 512,
  parameter int CAPACITY_BYTES = 65536
) (
  input  logic clk,
  input  logic rst_n,
  input  logic plaintext_valid_i,
  input  logic [DATA_BUS_BITS-1:0] plaintext_i,
  input  logic tag_verified_i,
  input  logic decrypt_failed_i,
  output logic plaintext_valid_o,
  output logic [DATA_BUS_BITS-1:0] plaintext_o
);

  // TODO: implement full-message FIFO/RAM buffering.
  // Until tag_verified_i is asserted, plaintext_valid_o must remain deasserted.
  assign plaintext_valid_o = plaintext_valid_i & tag_verified_i & ~decrypt_failed_i;
  assign plaintext_o = tag_verified_i ? plaintext_i : '0;
endmodule
