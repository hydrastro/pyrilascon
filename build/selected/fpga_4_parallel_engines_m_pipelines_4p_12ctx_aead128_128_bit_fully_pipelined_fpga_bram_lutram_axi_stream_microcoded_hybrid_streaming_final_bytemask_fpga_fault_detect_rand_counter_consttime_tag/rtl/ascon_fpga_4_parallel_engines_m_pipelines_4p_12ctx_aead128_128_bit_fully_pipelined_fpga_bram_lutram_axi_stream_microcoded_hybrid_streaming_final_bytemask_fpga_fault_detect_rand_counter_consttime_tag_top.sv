// Generated ASCON architecture top-level skeleton.
// This is structural RTL scaffolding; datapath internals are generated in later phases.
// Config: fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag
// Target: fpga
// Family: shared_permutation_mode_fsm
// Engine count: 4
// Top-level profile: m_pipelines_n_contexts
// Control profile: axi_stream_microcoded_hybrid
// Security profile: fpga_fault_detect_rand_counter_consttime_tag
// Decrypt release policy: buffer_until_tag_verify
// AEAD core count: 4
// Permutation pipeline count: 4
// Expected parallel operations: 4

module ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_top #(
  parameter int ENGINE_COUNT = 4,
  parameter int AEAD_CORE_COUNT = 4,
  parameter int PERM_PIPELINE_COUNT = 4,
  parameter int CONTEXTS_PER_PIPELINE = 12,
  parameter int DATA_BUS_BITS = 512
) (
  input  logic clk,
  input  logic rst_n,
  input  logic start_i,
  input  logic [DATA_BUS_BITS-1:0] data_i,
  output logic [DATA_BUS_BITS-1:0] data_o,
  output logic ready_o,
  output logic done_o
);

  ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_control u_control (
    .clk(clk),
    .rst_n(rst_n),
    .start_i(start_i),
    .busy_o(),
    .command_valid_o()
  );

  localparam int PIPELINE_COUNT = 4;
  localparam int PIPELINE_DATA_BITS = 128;
  logic [PIPELINE_COUNT-1:0] pipeline_ready;
  logic [PIPELINE_COUNT-1:0] pipeline_done;
  logic [319:0] pipeline_state_o [0:PIPELINE_COUNT-1];

  genvar pipeline_index;
  generate
    for (pipeline_index = 0; pipeline_index < PIPELINE_COUNT; pipeline_index = pipeline_index + 1) begin : gen_perm_pipeline
      ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_permutation u_perm_pipeline (
        .clk(clk),
        .rst_n(rst_n),
        .start_i(start_i),
        .rounds_i(2'd2),
        .state_i(320'b0),
        .state_o(pipeline_state_o[pipeline_index]),
        .ready_o(pipeline_ready[pipeline_index]),
        .done_o(pipeline_done[pipeline_index])
      );
    end
  endgenerate

  // TODO: add context scheduler: maps N session contexts onto the permutation pipeline(s).
  assign ready_o = &pipeline_ready;
  assign done_o  = &pipeline_done;
  assign data_o  = data_i;

endmodule
