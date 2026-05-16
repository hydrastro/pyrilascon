# ASCON FPGA/ASIC Generator — Development Summary

## 0. Project identity

This project is a configurable ASCON hardware-generation and evaluation platform. It is not a single fixed ASCON core. The intended deliverable is a modular system that can generate, integrate, and benchmark multiple ASCON accelerator architectures across FPGA and ASIC targets while keeping one stable firmware-facing interface.

The core goal is to explore the trade space between maximum FPGA throughput and minimum ASIC area without breaking the software contract used by firmware, tests, and future SoC integrations.

## 1. Global design principles

### 1.1 Stable separation of layers

The project is intentionally split into layers:

- **Specification/model layer:** typed Python model of ASCON state, permutation, AEAD, HASH, XOF, and CXOF behavior.
- **Architecture layer:** Python configuration vocabulary describing target technology, datapath width, permutation style, context storage, control style, padding policy, and security profile.
- **RTL layer:** generated and hand-written Verilog/SystemVerilog/VHDL building blocks for accelerator implementations.
- **Firmware layer:** C driver and benchmark scaffolding using a stable register-level ABI.
- **Board layer:** concrete bring-up targets, currently centered on Tang Nano 9K.
- **Benchmark layer:** cycle and throughput estimation plus firmware-side measurement hooks.

### 1.2 Frozen firmware ABI

The firmware-visible ABI is treated as frozen. Hardware may change internally, but the software-visible control contract should not. This allows slow, fast, single-core, multi-core, FPGA, ASIC, NEORV32, AXI Stream, and future DMA-based implementations to be swapped under the same driver.

The ABI includes:

- control and status registers;
- mode selection;
- capability discovery;
- key and nonce registers;
- input/output lengths;
- MMIO data fallback;
- tag registers;
- cycle counter;
- error code;
- ABI version.

Firmware must probe capabilities rather than assume a particular backend.

### 1.3 Control plane versus data plane

A major architectural decision is to keep the control plane stable while allowing the data plane to vary.

- **Control plane:** MMIO/CSR register interface. Always present.
- **Data plane:** selectable and implementation-dependent.

Supported or planned data planes:

- MMIO word-based fallback;
- AXI Stream payload interface;
- future DMA-fed AXI Stream integration.

The MMIO data path is important for bring-up, NEORV32 CFS-only integration, and debugging. The AXI Stream path is the high-throughput FPGA direction.

## 2. FPGA versus ASIC strategy

### 2.1 FPGA strategy

The FPGA objective is maximum throughput. Small boards such as Tang Nano 9K are validation targets, not the final performance target.

FPGA-favored choices include:

- 128-bit datapath and AXI Stream beats;
- 4-rounds-per-cycle and 8-rounds-per-cycle prototypes;
- fully pipelined permutations as the long-term goal;
- multiple independent engines;
- multiple pipelines with multiple contexts;
- LUTRAM/BRAM-backed context storage;
- descriptor/stream/DMA-style feeding;
- streaming final-byte masks through `tkeep`.

### 2.2 ASIC strategy

The ASIC objective is minimum area and implementation simplicity.

ASIC-favored choices include:

- hardcoded FSM control;
- single or small shared datapaths;
- 64-bit, 32-bit, 16-bit, 8-bit, 5-bit, or 1-bit datapath options;
- serial permutation styles;
- 5-bit S-box serial designs;
- single 320-bit state registers or compact shadow state structures;
- optional side-channel and fault-hardening profiles as later extensions.

## 3. Architecture decision matrix

The project already models a large design space.

### 3.1 Datapath widths

Tracked datapath options include:

- 128-bit wide datapath for FPGA throughput;
- 64-bit balanced datapath;
- 32-bit and 16-bit reduced datapaths;
- 8-bit serial datapath;
- 5-bit S-box-serial datapath;
- 1-bit bit-serial datapath.

### 3.2 Permutation styles

Tracked permutation options include:

- one round per cycle;
- two rounds per cycle;
- four rounds per cycle;
- eight rounds per cycle;
- fully pipelined permutation;
- column-serial permutation;
- bit-serial permutation.

### 3.3 Top-level organization

Tracked top-level organizations include:

- shared datapath;
- separate encryption/decryption datapaths;
- shared permutation with mode FSM;
- N identical parallel engines;
- one pipelined permutation with N contexts;
- M pipelines with N contexts.

### 3.4 Context and state organization

Tracked context/state options include:

- single 320-bit register;
- shadow state;
- multi-context register files;
- FPGA LUTRAM/BRAM context storage;
- dynamic context scheduling for pipeline utilization.

### 3.5 Control architecture

Tracked control styles include:

- hardcoded FSM;
- microcoded sequencer;
- AXI Stream control;
- AXI Stream plus microcoded hybrid control;
- CSR/MMIO control;
- future DMA-driven operation.

### 3.6 Padding and length handling

Tracked padding/length options include:

- RTL-performed padding;
- descriptor length handling;
- internal byte counters;
- streaming final-byte mask handling through byte-valid masks such as AXI `tkeep`.

### 3.7 Security and decryption policy

Important security choices already reflected in the project:

- constant-time tag comparison is required;
- decrypted plaintext must not be released before authentication succeeds;
- random counter hardening and fault detection are modeled as selectable profiles;
- advanced ASIC masking/threshold implementations are future work.

## 4. Implemented repository state

The current repository contains the following major artifacts.

### 4.1 Python hardware-oriented model

Implemented model areas include:

- fixed-width integer wrappers;
- state representation;
- endian-aware packing conventions;
- ASCON IV construction;
- p_C, p_S, p_L permutation layers;
- p6, p8, and p12 wrappers;
- AEAD phase decomposition;
- AEAD128 encrypt/decrypt helpers;
- HASH/XOF/CXOF helpers;
- known-answer tests for byte-aligned vectors;
- Verilog emission helpers colocated with model layers.

### 4.2 Architecture/configuration framework

Implemented architecture areas include:

- target technology profiles;
- datapath planning;
- permutation planning;
- context planning;
- control planning;
- padding planning;
- security planning;
- board suggestion profiles;
- validation rules;
- design-product generation;
- selected architecture matrix generation.

### 4.3 RTL components

Implemented RTL areas include:

- common accelerator register definitions;
- common AXI Stream definitions;
- MMIO register block;
- MMIO stub top;
- bounded AEAD128 MMIO backend;
- 4-rounds-per-cycle and 8-rounds-per-cycle bounded backends;
- 32-bit AXI Stream wrapper around the bounded backend;
- 128-bit AXI Stream wrappers around 4RPC and 8RPC bounded backends;
- Tang Nano 9K board tops;
- NEORV32 CFS wrapper scaffold;
- generated Verilog fragments for ASCON model/permutation helpers.

### 4.4 Firmware driver

Implemented firmware areas include:

- high-level accelerator API;
- register/control access layer;
- capability probing;
- MMIO data transport;
- AXI transport abstraction;
- AXI mock transport;
- benchmark support layer;
- NEORV32 demo and benchmark scaffolds;
- C reference AEAD128 implementation for software comparison.

### 4.5 Board targets

Implemented Tang Nano 9K board targets include:

- p12 pipeline demo;
- KAT slow core;
- full slow AEAD128 core;
- MMIO AEAD128 slow core;
- AXI AEAD128 slow core;
- 128-bit AXI + 4RPC candidate;
- 128-bit AXI + 8RPC candidate.

### 4.6 Benchmarks and estimates

Implemented benchmark areas include:

- benchmark methodology documentation;
- cycle-count structure;
- throughput-estimation tool;
- JSON estimates for Tang Nano 9K 128-bit AXI 4RPC and 8RPC candidates;
- firmware benchmark scaffolding for software versus hardware comparisons.

## 5. Repository health check performed in this handoff

The uploaded repository was unpacked and tested.

Observed state:

- root `pytest` now passes: **192 tests passing, plus 5 optional RTL simulation tests skipped when `iverilog`/`vvp` are unavailable**;
- `make verify` now passes after repairing the Makefile/tool compatibility issue around `--algorithms requested`;
- generated docs/config reports are produced under `docs/generated/`;
- generated RTL is produced under `rtl/generated/`.

The previous README test-count reference was stale and has been updated.

## 6. Issue fixed during handoff

`make verify` initially failed because the Makefile passed:

```text
--algorithms requested
```

to `tools/list_valid_configs.py`, but that CLI did not accept the option.

The fix keeps the Makefile interface stable by adding a reserved compatibility `--algorithms` argument to `list_valid_configs.py`. The current selected-config sweep remains architecture-focused; algorithm support is still encoded in each preset. A regression test was added so this does not break again.

## 7. Streaming AEAD128 reference model added

A host-side AXI-stream AEAD128 transaction model now exists in
`ascon_hwmodel/aead_stream.py`. It models the intended FPGA data-plane contract
without the old 32-byte backend limit:

- AD and TEXT are packed into fixed-width stream beats;
- `keep` must be a contiguous low-byte final bytemask;
- only the final beat may be partial;
- stream payload length must match the CSR length register;
- scalar AEAD128 encryption/decryption is used as the oracle;
- decrypt returns plaintext beats only after the tag is valid.

This is not the final RTL backend yet. It is the executable reference that the
next true streaming RTL core should match.

## 8. What is not finished yet

### 8.1 True unbounded streaming AEAD128 core

Current AXI Stream wrappers still feed bounded register-buffered backends. They establish the interface shape but do not yet implement a true unbounded streaming backend.

Missing:

- arbitrary-length associated data;
- arbitrary-length plaintext/ciphertext;
- block-by-block streaming absorption;
- streaming output production for encryption;
- decrypt buffering until tag validation;
- robust AXI backpressure behavior inside the real AEAD pipeline.

### 8.2 High-throughput FPGA core

The real performance target is not finished.

Missing:

- fully pipelined permutation;
- context scheduler;
- M-pipeline × N-context architecture;
- direct 128-bit stream consumption without 32-bit serialization;
- DMA-suitable descriptor/frontend design.

### 8.3 NEORV32 full system integration

The project has CFS and firmware scaffolding, but the full system is not complete.

Missing:

- full NEORV32 SoC build for Tang Nano;
- UART demonstration running on the CPU;
- hardware accelerator mapped through the actual CFS path;
- firmware execution on the softcore rather than only host-side compilation/testing.

### 8.4 Hardware benchmark demonstration

The intended benchmark story is not complete.

Missing:

- run software ASCON on NEORV32;
- run accelerator ASCON through the same firmware API;
- report cycles per byte;
- report total cycles per operation;
- report throughput;
- report hardware speedup over software.

### 8.5 Real AXI DMA transport

The current AXI transport is abstracted and mockable but not connected to a real DMA engine.

Missing:

- Xilinx AXI DMA integration;
- Gowin stream feeder/front-end integration;
- descriptor queues;
- host/CPU-visible DMA buffer management.

### 8.6 Full algorithm-family hardware support

The model contains HASH/XOF/CXOF helpers and the architecture layer tracks multiple algorithm families, but production RTL support is currently centered on AEAD128.

Planned or partial features:

- AEAD128a;
- AEAD80pq / legacy variants;
- HASH / HASH256 / HASHA;
- XOF / XOF128 / XOFA;
- CXOF / CXOF128.

### 8.7 ASIC-specific implementations

ASIC architecture planning exists, but actual area-minimized ASIC RTL is still future work.

Missing:

- serial datapath RTL;
- 5-bit S-box serial RTL;
- bit-serial permutation RTL;
- synthesis-oriented area comparison;
- advanced masking/fault-hardening implementation.

## 9. Immediate next engineering plan

The recommended next step is to implement the true streaming AEAD128 backend before attempting full NEORV32 board integration. The reason is that the current AXI wrappers already expose the final intended interface, but they still serialize into bounded MMIO-style storage internally. Replacing that backend is the cleanest way to move from prototype to real accelerator.

Recommended order:

1. Use `ascon_hwmodel/aead_stream.py` as the strict streaming AEAD128 backend contract.
2. Implement encryption-only streaming RTL first.
3. Add arbitrary-length associated-data handling.
4. Add final-block `tkeep`/byte-mask behavior.
5. Add decryption with buffer-until-tag-valid policy.
6. Add tests around AXI backpressure and partial final blocks.
7. Only then connect the backend to NEORV32 or DMA flows.

## 10. Benchmark rule

The key performance rule remains:

> The FPGA accelerator must beat NEORV32 software ASCON.

The minimum comparison metrics should be:

- cycles per byte;
- total cycles per operation;
- throughput in Mbps;
- speedup versus software;
- area/resource usage for the selected FPGA target.

## 11. Report/documentation angle

For a development-process report, the strongest narrative is:

1. Start with a correct Python model.
2. Freeze a firmware ABI early.
3. Split control plane from data plane.
4. Build slow but verifiable RTL first.
5. Add AXI Stream shape before the final high-throughput backend.
6. Keep board targets as validation points, not as the only design constraint.
7. Use architecture configs to document tradeoffs instead of hardcoding one implementation.
8. Use benchmarks to prove when a hardware architecture becomes worthwhile.

## 12. One-line project summary

We designed a configurable ASCON FPGA/ASIC accelerator generator with a stable firmware ABI, pluggable data planes, selectable datapath/permutation/control/security architectures, board-aware FPGA prototypes, and a unified benchmarking path for comparing hardware acceleration against software execution.

## 13. Streaming encryption RTL backend added

The next implementation slice adds `rtl/stream/ascon_aead128_stream_encrypt.v`,
an encryption-only NIST Ascon-AEAD128 backend that consumes validated AXI stream
AD/plaintext packets and emits ciphertext beats without complete-message
buffering.

This is the first stream-native RTL backend in the repository. It uses
local AXI beat validation inside the backend, keeps the standalone `ascon_axis_framer` available for protocol validation in future wrappers, keeps the frozen CSR/MMIO control
contract for key/nonce/length/mode, and schedules one Ascon round per cycle. It
is intentionally not yet the authenticated decrypt backend and does not replace
the older bounded AXI top-level wrapper yet.

Current validation after this slice:

- `python -m pytest -q`: **192 passed, 5 skipped**;
- `make verify`: **192 passed, 5 skipped**, then config/docs/RTL generation completes.

## 14. Behavioral simulation harness added

The follow-up slice adds `tools/run_stream_encrypt_vector.py` and
`tests/test_aead128_stream_encrypt_sim.py`. The tool generates a
vector-specific Verilog testbench for `ascon_aead128_stream_encrypt`, runs it
through Icarus Verilog when `iverilog`/`vvp` are available, parses the emitted
AXI output beats and generated tag, and compares them against the Python golden
stream model.

The simulation tests are optional in environments without a Verilog simulator;
they are skipped rather than making the normal model/config verification flow
depend on external EDA packages.

Current validation after this slice:

- `python -m pytest -q`: **192 passed, 5 skipped**;
- `make verify`: **192 passed, 5 skipped**, then config/docs/RTL generation completes.
