# Selected valid architecture configurations

This file is generated from `tools/list_valid_configs.py`. It lists the selected subset of architecture combinations that pass the current config validator. These are architecture-valid generation products; not all have a completed production RTL backend yet.

- ASIC selected valid configs: 44
- FPGA selected valid configs: 26
- Total selected valid configs: 70

## ASIC valid configurations

| # | Datapath | Permutation | Control | Padding | Security |
|---:|---|---|---|---|---|
| 1 | `64_bit` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 2 | `64_bit` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 3 | `64_bit` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 4 | `64_bit` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 5 | `64_bit` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 6 | `64_bit` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 7 | `32_bit` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 8 | `32_bit` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 9 | `32_bit` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 10 | `32_bit` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 11 | `32_bit` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 12 | `32_bit` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 13 | `16_bit` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 14 | `16_bit` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 15 | `16_bit` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 16 | `16_bit` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 17 | `16_bit` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 18 | `16_bit` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 19 | `16_bit` | `bit_serial` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 20 | `16_bit` | `bit_serial` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 21 | `8_bit_serial` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 22 | `8_bit_serial` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 23 | `8_bit_serial` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 24 | `8_bit_serial` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 25 | `8_bit_serial` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 26 | `8_bit_serial` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 27 | `8_bit_serial` | `bit_serial` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 28 | `8_bit_serial` | `bit_serial` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 29 | `5bit_sbox_serial` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 30 | `5bit_sbox_serial` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 31 | `5bit_sbox_serial` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 32 | `5bit_sbox_serial` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 33 | `5bit_sbox_serial` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 34 | `5bit_sbox_serial` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 35 | `5bit_sbox_serial` | `bit_serial` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 36 | `5bit_sbox_serial` | `bit_serial` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 37 | `1_bit_serial` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 38 | `1_bit_serial` | `one_round_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 39 | `1_bit_serial` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 40 | `1_bit_serial` | `two_rounds_per_cycle` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 41 | `1_bit_serial` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 42 | `1_bit_serial` | `column_serial` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |
| 43 | `1_bit_serial` | `bit_serial` | `hardcoded_fsm` | `rtl_performed` | `none` |
| 44 | `1_bit_serial` | `bit_serial` | `hardcoded_fsm` | `rtl_performed` | `asic_rand_counter_consttime_tag` |

## FPGA valid configurations

| # | Top level | Datapath | Permutation | Control | Padding | Security |
|---:|---|---|---|---|---|---|
| 1 | `n_identical_aead_cores` | `128_bit` | `four_rounds_per_cycle` | `axi_stream` | `streaming_final_bytemask` | `none` |
| 2 | `n_identical_aead_cores` | `128_bit` | `four_rounds_per_cycle` | `axi_stream` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 3 | `n_identical_aead_cores` | `128_bit` | `four_rounds_per_cycle` | `microcoded_sequencer` | `streaming_final_bytemask` | `none` |
| 4 | `n_identical_aead_cores` | `128_bit` | `four_rounds_per_cycle` | `microcoded_sequencer` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 5 | `n_identical_aead_cores` | `128_bit` | `four_rounds_per_cycle` | `axi_stream_microcoded_hybrid` | `streaming_final_bytemask` | `none` |
| 6 | `n_identical_aead_cores` | `128_bit` | `four_rounds_per_cycle` | `axi_stream_microcoded_hybrid` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 7 | `n_identical_aead_cores` | `128_bit` | `eight_rounds_per_cycle` | `axi_stream` | `streaming_final_bytemask` | `none` |
| 8 | `n_identical_aead_cores` | `128_bit` | `eight_rounds_per_cycle` | `axi_stream` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 9 | `n_identical_aead_cores` | `128_bit` | `eight_rounds_per_cycle` | `microcoded_sequencer` | `streaming_final_bytemask` | `none` |
| 10 | `n_identical_aead_cores` | `128_bit` | `eight_rounds_per_cycle` | `microcoded_sequencer` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 11 | `n_identical_aead_cores` | `128_bit` | `eight_rounds_per_cycle` | `axi_stream_microcoded_hybrid` | `streaming_final_bytemask` | `none` |
| 12 | `n_identical_aead_cores` | `128_bit` | `eight_rounds_per_cycle` | `axi_stream_microcoded_hybrid` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 13 | `n_identical_aead_cores` | `128_bit` | `fully_pipelined` | `axi_stream` | `streaming_final_bytemask` | `none` |
| 14 | `n_identical_aead_cores` | `128_bit` | `fully_pipelined` | `axi_stream` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 15 | `n_identical_aead_cores` | `128_bit` | `fully_pipelined` | `microcoded_sequencer` | `streaming_final_bytemask` | `none` |
| 16 | `n_identical_aead_cores` | `128_bit` | `fully_pipelined` | `microcoded_sequencer` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 17 | `n_identical_aead_cores` | `128_bit` | `fully_pipelined` | `axi_stream_microcoded_hybrid` | `streaming_final_bytemask` | `none` |
| 18 | `n_identical_aead_cores` | `128_bit` | `fully_pipelined` | `axi_stream_microcoded_hybrid` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 19 | `one_pipelined_permutation_n_contexts` | `128_bit` | `fully_pipelined` | `axi_stream` | `streaming_final_bytemask` | `none` |
| 20 | `one_pipelined_permutation_n_contexts` | `128_bit` | `fully_pipelined` | `axi_stream` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 21 | `one_pipelined_permutation_n_contexts` | `128_bit` | `fully_pipelined` | `axi_stream_microcoded_hybrid` | `streaming_final_bytemask` | `none` |
| 22 | `one_pipelined_permutation_n_contexts` | `128_bit` | `fully_pipelined` | `axi_stream_microcoded_hybrid` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 23 | `m_pipelines_n_contexts` | `128_bit` | `fully_pipelined` | `axi_stream` | `streaming_final_bytemask` | `none` |
| 24 | `m_pipelines_n_contexts` | `128_bit` | `fully_pipelined` | `axi_stream` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
| 25 | `m_pipelines_n_contexts` | `128_bit` | `fully_pipelined` | `axi_stream_microcoded_hybrid` | `streaming_final_bytemask` | `none` |
| 26 | `m_pipelines_n_contexts` | `128_bit` | `fully_pipelined` | `axi_stream_microcoded_hybrid` | `streaming_final_bytemask` | `fpga_fault_detect_rand_counter_consttime_tag` |
