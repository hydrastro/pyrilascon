# Permutation Architecture Profiles

The implementation generator now treats the permutation engine as a configurable microarchitecture, independent of the ASCON specification model.

## Supported profiles

| Profile | Style | p8 latency | p12 latency | Typical target | Notes |
|---|---:|---:|---:|---|---|
| `one_round_per_cycle` | round serial | 8 | 12 | ASIC / balanced FPGA | Small area, one full p_C/p_S/p_L round per cycle. |
| `two_rounds_per_cycle` | round unrolled | 4 | 6 | ASIC if timing allows | More area and longer combinational path. |
| `four_rounds_per_cycle` | round unrolled | 2 | 3 | FPGA | Good high-performance FPGA candidate. |
| `eight_rounds_per_cycle` | round unrolled | 1 | 2 | FPGA | Large area and high timing risk. |
| `fully_pipelined` | round pipeline | 8 visible p8 stages | 12 visible p12 stages | FPGA | Initiation interval can be 1 when enough contexts/messages are available. |
| `column_serial` | serialized S-box columns | 512 with one column/cycle | 768 with one column/cycle | tiny ASIC | Reuses a small number of 5-bit S-box columns. |
| `bit_serial` | ultra-small serial | backend-dependent | backend-dependent | tiny ASIC / research | Placeholder for the most aggressive area minimization. |

## Important throughput rule

A round pipeline only reaches its advertised initiation interval when the design has enough independent contexts or messages to fill the pipeline. For one long message, the sponge state dependency limits utilization. Therefore the FPGA baseline combines two scalable ideas:

1. N independent engines.
2. A permutation profile that can be switched between `fully_pipelined`, `four_rounds_per_cycle`, and `eight_rounds_per_cycle` depending on timing closure.

## Config examples

Generate 4 FPGA engines with a 4-round combinational step:

```bash
PYTHONPATH=. python tools/generate_design.py \
  --preset fpga_n_parallel_engines \
  --engine-count 4 \
  --permutation-profile four_rounds_per_cycle
```

Generate the ASIC two-datapath baseline with two rounds per cycle:

```bash
PYTHONPATH=. python tools/generate_design.py \
  --preset asic_two_datapaths \
  --permutation-profile two_rounds_per_cycle
```

Generate an ultra-small column-serial ASIC permutation variant:

```bash
PYTHONPATH=. python tools/generate_design.py \
  --preset asic_two_datapaths_column_serial
```
