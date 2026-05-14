// Generated ASCON permutation wrapper skeleton.
// style=round_serial, sbox=boolean
// rounds_per_cycle=1, sbox_columns_per_cycle=64
// p8_cycles=8, p12_cycles=12, initiation_interval=12
// datapath_profile=16_bit, lane_width=16, absorb_width=16
// area_class=small, timing_risk=low
module ascon_asic_shared_datapath_aead128_16_bit_one_round_per_cycle_single_core_single_320_register_hardcoded_fsm_rtl_performed_asic_rand_counter_consttime_tag_permutation #(
  parameter int ROUNDS_PER_CYCLE = 1,
  parameter int SBOX_COLUMNS_PER_CYCLE = 64,
  parameter int PIPELINE_STAGES = 0,
  parameter int INITIATION_INTERVAL = 12,
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

  // One p_C/p_S/p_L round is evaluated per cycle.
  // TODO: add round counter, round-constant schedule, and state register.

  assign state_o = state_i;
  assign ready_o = 1'b1;
  assign done_o  = start_i;
endmodule
