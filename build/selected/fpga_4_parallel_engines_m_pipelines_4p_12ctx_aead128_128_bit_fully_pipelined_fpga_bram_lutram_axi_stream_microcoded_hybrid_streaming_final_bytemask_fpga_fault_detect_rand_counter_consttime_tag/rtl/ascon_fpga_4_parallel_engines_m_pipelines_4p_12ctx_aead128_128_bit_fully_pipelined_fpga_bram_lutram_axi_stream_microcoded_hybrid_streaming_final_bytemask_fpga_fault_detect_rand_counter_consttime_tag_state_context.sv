// Generated ASCON state/context storage skeleton.
// profile=fpga_bram_lutram, storage=fpga_lutram_context_memory
// context_count=48, contexts_per_engine=12
// interleave_depth=12, shadow_state=false
// state_bits_total=15360, memory_bits=15360
module ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_state_context #(
  parameter int CONTEXT_COUNT = 48,
  parameter int CONTEXT_ID_BITS = 6
) (
  input  logic clk,
  input  logic rst_n,
  input  logic [CONTEXT_ID_BITS-1:0] context_id_i,
  input  logic state_we_i,
  input  logic [319:0] state_i,
  output logic [319:0] state_o
);

  logic [319:0] state_mem [0:CONTEXT_COUNT-1];

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_o <= 320'b0;
    end else begin
      if (state_we_i) begin
        state_mem[context_id_i] <= state_i;
      end
      state_o <= state_mem[context_id_i];
    end
  end
endmodule
