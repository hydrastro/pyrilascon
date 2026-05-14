// Generated ASCON engine skeleton.
// Permutation style: round_pipelined
// S-box style: lut5
// Datapath profile: 128_bit
// Datapath lane width: 128
// Absorb width: 128
// Context profile: fpga_bram_lutram
// Contexts per engine: 12
// Control profile: axi_stream_microcoded_hybrid

module ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_engine #(
  parameter int ENGINE_ID = 0,
  parameter int DATA_BUS_BITS = 128
) (
  input  logic clk,
  input  logic rst_n,
  input  logic start_i,
  input  logic [DATA_BUS_BITS-1:0] data_i,
  output logic [DATA_BUS_BITS-1:0] data_o,
  output logic ready_o,
  output logic done_o
);

  logic enc_ready;
  logic enc_done;
  logic dec_ready;
  logic dec_done;
  logic [DATA_BUS_BITS-1:0] enc_data_o;
  logic [DATA_BUS_BITS-1:0] dec_data_o;
  logic [319:0] context_state_q;

  ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_state_context #(
    .CONTEXT_COUNT(48),
    .CONTEXT_ID_BITS(6)
  ) u_state_context (
    .clk(clk),
    .rst_n(rst_n),
    .context_id_i('0),
    .state_we_i(1'b0),
    .state_i(320'b0),
    .state_o(context_state_q)
  );

  // Single logical datapath placeholder for this architecture family.
  ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_permutation u_permutation (
    .clk(clk),
    .rst_n(rst_n),
    .start_i(start_i),
    .rounds_i(2'd2),
    .state_i({320{1'b0}}),
    .state_o(),
    .ready_o(),
    .done_o()
  );

  assign ready_o = 1'b1;
  assign done_o  = start_i;
  assign data_o  = data_i;

endmodule
