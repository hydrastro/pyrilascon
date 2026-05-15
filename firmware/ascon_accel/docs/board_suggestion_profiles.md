# FPGA board suggestion profiles

The board suggestion profiles are **not hardcoded implementation choices**. They are ranked throughput-oriented starting points for synthesis experiments. The generator should keep the architecture pluggable: data-plane width, permutation style, top-level core count, context organization, control architecture, padding strategy, and security profile remain independent configuration axes.

The invariant is:

- firmware-visible ABI stays stable;
- hardware backend is replaceable;
- the core advertises real capabilities;
- every design that claims a mode must pass known-answer tests;
- FPGA suggestions optimize for maximum throughput first and fall back only when timing or fit fails.

Generated JSON profiles live in `docs/board_suggestions/`.

## Suggested search order

| Board class | First candidates |
| --- | --- |
| Tang Nano 9K | AXIS128 8RPC, then AXIS128 4RPC, then known-good 1RPC |
| Tang Nano 20K | fully pipelined + 12 contexts, then 8RPC, then two cores |
| Xilinx low | AXIS128 8RPC or small context-interleaved pipeline |
| Xilinx medium | one/two fully pipelined engines with 12 contexts each |
| Xilinx high | four/eight fully pipelined engines with DMA-fed stream aggregation |

These are suggestions for exploration. They are deliberately separate from the actual RTL backends.
