# Architecture configuration layer

The repository separates the ASCON specification model from implementation architecture choices.

The specification model answers: **what does ASCON compute?**

The architecture layer answers: **how is a selected ASCON implementation organized?**

## Architecture families

| Family | Intent |
|---|---|
| `shared_datapath` | Low/medium area, one operation at a time. |
| `separate_enc_dec_datapaths` | Higher area, separate encryption and decryption datapaths, up to two operations at a time per engine. |
| `shared_permutation_mode_fsm` | Medium area, one shared permutation bottleneck controlled by a mode FSM. |
| `parallel_engines` | High area, N independent engines for near-linear scaling on independent jobs. |

## Main configuration axes

The generator now treats architectural choices as typed axes:

| Config object | Purpose |
|---|---|
| `AlgorithmConfig` | Selects AEAD128, Hash256, XOF128, CXOF128 support. |
| `DatapathTopology` | Selects shared datapath, separate enc/dec datapaths, shared permutation, or N engines. |
| `PermutationConfig` | Selects round-serial, unrolled, pipelined, column-serial, S-box style, unroll factor. |
| `DatapathConfig` | Selects lane width, absorb width, key/tag width, sharing of key/pad logic. |
| `ContextConfig` | Selects single context, interleaving, dynamic queues, register/regfile/BRAM/SRAM-style storage. |
| `PaddingConfig` | Selects inline/FSM/preprocessor padding and length handling. |
| `IOConfig` | Selects block/stream/descriptor-stream interface, bus width, flow control, port splitting. |
| `SecurityConfig` | Selects side-channel protection placeholder options and security hygiene controls. |
| `RtlConfig` | Selects SystemVerilog/Verilog metadata and reset style. |

The validator rejects inconsistent combinations. Examples:

- `parallel_engines` requires FPGA target and at least two engines.
- descriptor-stream I/O requires descriptor-based length handling.
- fully unrolled pipelined permutations require pipeline registers.
- 128-bit absorb width requires a 128-bit rate.
- masked/side-channel-protected variants require randomness input metadata.

## Chosen baselines

| Target | Baseline |
|---|---|
| ASIC | `asic_two_datapaths`: one encryption datapath and one decryption datapath. |
| FPGA | `fpga_N_parallel_engines`: N independent engines, parameterized by `engine_count`. |

## Built-in presets

```bash
PYTHONPATH=. python tools/generate_design.py --preset asic_two_datapaths
PYTHONPATH=. python tools/generate_design.py --preset fpga_n_parallel_engines --engine-count 4
PYTHONPATH=. python tools/generate_design.py --preset asic_shared_datapath
PYTHONPATH=. python tools/generate_design.py --preset fpga_shared_datapath
PYTHONPATH=. python tools/generate_design.py --preset asic_shared_permutation_mode_fsm
PYTHONPATH=. python tools/generate_design.py --preset fpga_shared_permutation_mode_fsm
```

Or from explicit JSON:

```bash
PYTHONPATH=. python tools/generate_design.py --config configs/asic/two_separate_datapaths.json
PYTHONPATH=. python tools/generate_design.py --config configs/fpga/n_parallel_engines_4.json
```

The generated build directory contains:

```text
build/<design_name>/
  README.md
  metadata/
    config_resolved.json
    module_manifest.json
    expected_metrics.json
  rtl/
    <top>.sv
    <engine>.sv
    <permutation>.sv
    ... architecture-specific datapath skeletons ...
```

The current RTL files are structural skeletons. They intentionally preserve module boundaries before datapath internals are implemented.
