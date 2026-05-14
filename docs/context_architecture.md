# State / Context Organization

The generator treats state/context organization as a separate architecture axis from topology, permutation style, and datapath width.

## Profiles

| Profile | Intent |
|---|---|
| `single_320_register` | Smallest storage shape: one 320-bit state register per active datapath/core. |
| `state_plus_shadow` | Adds a second 320-bit shadow copy for debug, rollback, or speculative phase handling. |
| `multi_context_registers` | Register-file style multi-context storage for interleaving one permutation engine among sessions. |
| `fpga_bram_lutram` | FPGA session storage intended to infer LUTRAM for small banks or BRAM for larger banks. |
| `separate_state_per_core` | Simplest multicore scaling: one state bank per core/engine. |
| `shared_state_ram_pipelined_p8` | Shared state RAM feeding an interleaved pipelined round/p8-style engine. |

## Project defaults

ASIC baseline:

```text
profile = single_320_register
```

For the ASIC two-datapath architecture this means one plain 320-bit state register per active encrypt/decrypt datapath. The profile is still `single_320_register`; the duplicated storage comes from having two active datapaths.

FPGA baseline:

```text
profile = fpga_bram_lutram
contexts_per_engine = 12
```

This matches the high-throughput FPGA direction: N replicated engines, each capable of interleaving multiple independent contexts through a pipelined permutation. For the default fully pipelined p12 engine, twelve contexts per engine can keep the pipeline filled for independent messages.

## Config fields

```text
context.profile
context.scheduling
context.storage
context.context_count
context.contexts_per_engine
context.interleave_depth
context.context_id_bits
context.shadow_state
context.rollback_supported
context.state_memory_read_ports
context.state_memory_write_ports
```

`context_count` is the total number of state contexts in the generated product. `contexts_per_engine` disambiguates N-engine FPGA products.

Example: four FPGA engines with twelve interleaved contexts per engine:

```text
engine_count = 4
contexts_per_engine = 12
context_count = 48
interleave_depth = 12
```

The current RTL generated for context storage is still a skeleton, but the metadata is now explicit and validated.
