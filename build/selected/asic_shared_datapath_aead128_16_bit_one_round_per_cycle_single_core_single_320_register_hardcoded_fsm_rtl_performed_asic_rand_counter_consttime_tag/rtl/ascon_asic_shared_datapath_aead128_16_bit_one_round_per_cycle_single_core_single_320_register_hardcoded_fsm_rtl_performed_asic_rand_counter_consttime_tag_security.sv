// Generated ASCON security/fault/decryption-release skeleton.
// profile=asic_rand_counter_consttime_tag, side_channel=none, fault_detection=none
// constant_time_tag_compare=true, randomized_counter_hardening=true
// plaintext_release_policy=buffer_until_tag_verify
// plaintext_buffer=sram_fifo, capacity_bytes=4096
// area_class=small_plus_plaintext_buffer, performance_impact=negligible
module ascon_asic_shared_datapath_aead128_16_bit_one_round_per_cycle_single_core_single_320_register_hardcoded_fsm_rtl_performed_asic_rand_counter_consttime_tag_security #(
  parameter int PLAINTEXT_BUFFER_CAPACITY_BYTES = 4096,
  parameter bit CONSTANT_TIME_TAG_COMPARE = 1,
  parameter bit RANDOMIZED_COUNTER_HARDENING = 1,
  parameter bit DUPLICATE_COMPUTE_CHECK = 0
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
