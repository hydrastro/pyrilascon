// Generated ASCON padding/final-block skeleton.
// profile=rtl_performed, strategy=fsm_assisted, length_handling=internal_byte_counter
// area_class=medium, flexibility=medium, streaming_efficiency=good
// final_bytemask=false, final_bytemask_width=0
module ascon_asic_shared_datapath_aead128_16_bit_one_round_per_cycle_single_core_single_320_register_hardcoded_fsm_rtl_performed_asic_rand_counter_consttime_tag_padding #(
  parameter int DATA_BUS_BITS = 16,
  parameter int KEEP_BITS = 2,
  parameter int PARTIAL_BLOCK_BUFFER_BYTES = 16
) (
  input  logic clk,
  input  logic rst_n,
  input  logic valid_i,
  input  logic last_i,
  input  logic [DATA_BUS_BITS-1:0] data_i,
  input  logic [KEEP_BITS-1:0] keep_i,
  output logic valid_o,
  output logic [DATA_BUS_BITS-1:0] data_o,
  output logic [KEEP_BITS-1:0] keep_o
);

  // TODO: implement selected padding backend.
  // For streaming_final_bytemask, keep_i marks valid bytes on the final beat.
  // For rtl_performed, the FSM/counter determines the pad10* insertion point internally.
  assign valid_o = valid_i;
  assign data_o  = data_i;
  assign keep_o  = keep_i;
endmodule
