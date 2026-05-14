// Generated ASCON architecture top-level skeleton.
// This is structural RTL scaffolding; datapath internals are generated in later phases.
// Config: asic_shared_datapath_aead128_16_bit_one_round_per_cycle_single_core_single_320_register_hardcoded_fsm_rtl_performed_asic_rand_counter_consttime_tag
// Target: asic
// Family: shared_datapath
// Engine count: 1
// Top-level profile: single_core
// Control profile: hardcoded_fsm
// Security profile: asic_rand_counter_consttime_tag
// Decrypt release policy: buffer_until_tag_verify
// AEAD core count: 1
// Permutation pipeline count: 0
// Expected parallel operations: 1

module ascon_asic_shared_datapath_aead128_16_bit_one_round_per_cycle_single_core_single_320_register_hardcoded_fsm_rtl_performed_asic_rand_counter_consttime_tag_top #(
  parameter int ENGINE_COUNT = 1,
  parameter int AEAD_CORE_COUNT = 1,
  parameter int PERM_PIPELINE_COUNT = 1,
  parameter int CONTEXTS_PER_PIPELINE = 1,
  parameter int DATA_BUS_BITS = 16
) (
  input  logic clk,
  input  logic rst_n,
  input  logic start_i,
  input  logic [DATA_BUS_BITS-1:0] data_i,
  output logic [DATA_BUS_BITS-1:0] data_o,
  output logic ready_o,
  output logic done_o
);

  ascon_asic_shared_datapath_aead128_16_bit_one_round_per_cycle_single_core_single_320_register_hardcoded_fsm_rtl_performed_asic_rand_counter_consttime_tag_control u_control (
    .clk(clk),
    .rst_n(rst_n),
    .start_i(start_i),
    .busy_o(),
    .command_valid_o()
  );

  ascon_asic_shared_datapath_aead128_16_bit_one_round_per_cycle_single_core_single_320_register_hardcoded_fsm_rtl_performed_asic_rand_counter_consttime_tag_engine #(
    .ENGINE_ID(0),
    .DATA_BUS_BITS(DATA_BUS_BITS)
  ) u_engine (
    .clk(clk),
    .rst_n(rst_n),
    .start_i(start_i),
    .data_i(data_i),
    .data_o(data_o),
    .ready_o(ready_o),
    .done_o(done_o)
  );

endmodule
