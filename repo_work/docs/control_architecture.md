# Control architecture axis

The control architecture is modeled separately from the datapath, permutation, context storage, and I/O bus width. This keeps the design generator able to build both tiny fixed-function ASIC cores and FPGA wrappers that support runtime mode selection, queues, and interleaved contexts.

| Profile | Area | Flexibility | Primary use |
|---|---:|---:|---|
| `hardcoded_fsm` | smallest | low | Fixed-function ASIC AEAD flow |
| `microcoded_sequencer` | medium | high | Multi-mode AEAD + Hash/XOF/CXOF sequencing |
| `command_fifo` | medium | medium | FPGA wrapper with decoupled command issue |
| `axi_stream` | medium/high | high | FPGA streaming integration |
| `axi_stream_microcoded_hybrid` | high | very high | Multi-context FPGA pipelines supporting several modes |
| `csr_register_file` | medium | medium | Software-controlled integration |
| `dma_fed` | large | very high | Descriptor/DMA FPGA system wrapper |

## Current prioritized choices

ASIC baseline:

```text
control.profile = hardcoded_fsm
```

This is paired with two independent encrypt/decrypt datapaths and single 320-bit state registers.

FPGA baseline:

```text
control.profile = axi_stream_microcoded_hybrid
```

This is paired with N engines or M pipelined permutation engines, multi-context storage, descriptor-based length handling, and a scheduler-capable command layer.

## Important distinction

`IOConfig.interface_style` describes how data enters and leaves the core. `ControlConfig.profile` describes how commands, phases, modes, context scheduling, and runtime algorithm selection are sequenced.

For example, a design can use a stream data interface with either a fixed FSM or a microcoded sequencer. A DMA-fed design is treated as a wrapper around descriptor-driven command/control rather than as the minimal ASCON datapath itself.
