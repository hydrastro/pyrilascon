// Generated ASCON permutation wrapper skeleton.
// style=round_pipelined, sbox=lut5
// rounds_per_cycle=1, sbox_columns_per_cycle=64
// p8_cycles=8, p12_cycles=12, initiation_interval=1
// datapath_profile=128_bit, lane_width=128, absorb_width=128
// area_class=large, timing_risk=medium
module ascon_fpga_4_parallel_engines_m_pipelines_4p_12ctx_aead128_128_bit_fully_pipelined_fpga_bram_lutram_axi_stream_microcoded_hybrid_streaming_final_bytemask_fpga_fault_detect_rand_counter_consttime_tag_permutation #(
  parameter int ROUNDS_PER_CYCLE = 1,
  parameter int SBOX_COLUMNS_PER_CYCLE = 64,
  parameter int PIPELINE_STAGES = 12,
  parameter int INITIATION_INTERVAL = 1,
  parameter int P8_CYCLES = 8,
  parameter int P12_CYCLES = 12
) (
  input  logic clk,
  input  logic rst_n,
  input  logic start_i,
  input  logic [1:0] rounds_i, // 0:p6, 1:p8, 2:p12
  input  logic [319:0] state_i,
  output logic [319:0] state_o,
  output logic ready_o,
  output logic done_o
);

  // Round pipeline: independent contexts/messages are needed for full utilization.
  logic [319:0] pipe_state [0:PIPELINE_STAGES];
  // TODO: populate each stage with one fixed-constant Ascon round and context metadata.

  assign state_o = state_i;
  assign ready_o = 1'b1;
  assign done_o  = start_i;
endmodule
