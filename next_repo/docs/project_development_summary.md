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

- root `pytest` now passes: **206 tests passing, plus 11 optional RTL simulation tests skipped when `iverilog`/`vvp` are unavailable**;
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

- `python -m pytest -q`: **232 passed, 11 skipped**;
- `make verify`: **232 passed, 11 skipped**, then config/docs/RTL generation completes.

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

- `python -m pytest -q`: **232 passed, 11 skipped**;
- `make verify`: **232 passed, 11 skipped**, then config/docs/RTL generation completes.

## 15. Buffered authenticated decrypt RTL policy added

The next slice adds `rtl/stream/ascon_aead128_stream_decrypt_buffered.v` and
`docs/streaming_aead_decrypt_buffered_backend.md`. This is the conservative
decrypt-side policy: ciphertext is received over AXI Stream, plaintext is written
into an internal quarantine buffer, and plaintext is released on the output
stream only after the computed tag matches `expected_tag_i`.

This does not claim unbounded decrypt. Safe authenticated decrypt requires either
internal buffering, speculative release with external quarantine discipline, or a
DMA quarantine region. The current RTL chooses the bounded internal buffer
variant through the explicit `MAX_TEXT_BYTES` parameter, preserving the rule that
unauthenticated plaintext is never exposed.

Current validation after this slice:

- `python -m pytest -q`: **232 passed, 11 skipped**;
- `make verify`: **232 passed, 11 skipped**, then config/docs/RTL generation completes.

## 16. Buffered decrypt behavioral simulation harness added

The newest slice adds `tools/run_stream_decrypt_vector.py`,
`tests/test_aead128_stream_decrypt_sim.py`, and
`docs/streaming_aead_decrypt_simulation.md`.  The tool mirrors the successful
stream-encrypt simulation flow, but targets
`ascon_aead128_stream_decrypt_buffered`.  It starts from a plaintext test case,
uses the Python stream oracle to generate ciphertext and the correct AEAD tag,
feeds AD/ciphertext beats into the RTL decrypt backend, and compares the RTL
output against the Python buffered-authentication policy.

Two security-critical cases are locked down:

- valid tag: plaintext is released after authentication and must match the
  original plaintext exactly;
- corrupt tag: no plaintext beat may be emitted, `tag_valid_o` remains low, and
  `ASCON_ERROR_TAG_INVALID` is reported.

The Makefile now exposes both stream simulation entry points:

- `make stream-encrypt-sim`;
- `make stream-decrypt-sim`.

Current validation after this slice:

- `python -m pytest -q`: **232 passed, 11 skipped**;
- `make verify`: **232 passed, 11 skipped**, then config/docs/RTL generation completes.

## 17. Unified streaming AEAD backend wrapper added

The unified stream backend slice adds `rtl/stream/ascon_aead128_stream.v` and
`rtl/stream/ascon_stream_file_list.f`.  This wrapper gives downstream firmware,
SoC, DMA, and board integration one backend module to target while preserving the
policy split internally:

- `decrypt_i = 0` dispatches to `ascon_aead128_stream_encrypt`;
- `decrypt_i = 1` dispatches to `ascon_aead128_stream_decrypt_buffered`;
- output/status/tag/error signals are multiplexed from the selected operation.

This is still below the full system top: it is the algorithm/data-plane backend,
not the MMIO register integration wrapper.

Current validation after this slice:

- `python -m pytest -q`: **232 passed, 11 skipped**;
- `make verify`: **232 passed, 11 skipped**, then config/docs/RTL generation completes.

## 18. Firmware-facing streaming AEAD SoC top added

The newest slice adds `rtl/common/ascon_accel_stream_aead128_top.v`,
`rtl/common/ascon_stream_aead128_top_file_list.f`,
`docs/streaming_aead_soc_top.md`, and structural tests around the new boundary.

This top-level module is the integration point for firmware and future SoC/DMA
work:

- `ascon_accel_mmio_regs` keeps the frozen software-visible ABI;
- `ascon_aead128_stream` provides the 128-bit AXI Stream data plane;
- `CONTROL.DECRYPT` selects encryption or buffered authenticated decryption;
- capabilities advertise AEAD128, buffered decrypt, constant-time tag compare,
  streaming byte masks, cycle counter, and AXI Stream data support;
- legacy MMIO DATA registers remain ABI/debug-visible, but bulk data transfer for
  this top is explicitly AXI Stream-only.

The older bounded `ascon_accel_axis_aead128_top` is retained for compatibility.
New NEORV32, DMA, and board-level stream integration should target
`ascon_accel_stream_aead128_top`.

Current validation after this slice:

- `python -m pytest -q`: **232 passed, 11 skipped**;
- `make verify`: **232 passed, 11 skipped**, then config/docs/RTL generation completes.


## 19. Firmware sequencing for the stream-native SoC top added

The latest slice wires the new stream-native hardware boundary into the portable
C driver contract.  The important software distinction is now explicit:

- MMIO word data plane keeps the compatibility sequence: write payload words
  first, then assert `CONTROL.START`;
- external AXI Stream data plane uses the stream-native sequence: program
  registers, assert `CONTROL.START`, then send AD/text beats through the
  installed transport callbacks.

This matches `ascon_accel_stream_aead128_top`, whose `s_axis_tready` is owned by
the active streaming FSM and is only meaningful after start. The driver also now
translates hardware `ASCON_ERROR_TAG_INVALID` into the public
`ASCON_ACCEL_ERR_TAG_INVALID` status, so buffered authenticated decrypt failures
are reported as authentication failures rather than generic hardware faults.

New coverage includes a host-compiled C integration test that uses a fake MMIO
register window plus AXI transport callbacks. It verifies that stream operations
start before the first payload callback and that invalid decrypt tags suppress
RX/plaintext handling and return `ASCON_ACCEL_ERR_TAG_INVALID`.

Current validation after this slice:

- `python -m pytest -q`: **232 passed, 11 skipped** in this environment;
- `make verify`: **232 passed, 11 skipped**, then config/docs/RTL generation completes.

With `iverilog`/`vvp` installed, the 11 optional RTL simulation tests should run
instead of skipping, for an expected total of **243 passed**.


## 20. Host firmware stream benchmark smoke test added

This slice adds `tools/run_firmware_stream_ref_benchmark.py` and the
`make firmware-stream-ref-bench` target. The tool compiles and runs a temporary
C benchmark that drives the normal firmware API through the AXI-stream reference
emulator. It exercises the same control/data-plane sequence that the NEORV32
stream benchmark will use once a real MMIO-to-AXI-stream bridge or DMA frontend
is connected.

The benchmark covers empty, short, partial-final-block, and two-block AEAD128
messages. For each case it verifies:

- encryption succeeds and matches the portable C reference;
- authenticated decrypt releases plaintext only after a valid tag;
- an invalid decrypt tag returns `ASCON_ACCEL_ERR_TAG_INVALID`;
- invalid-tag decrypt suppresses plaintext output;
- benchmark cycle deltas are nonzero.

The AXI-stream reference emulator now keeps a monotonic synthetic cycle counter
so consecutive encrypt/decrypt benchmark measurements report useful nonzero
deltas.

Current validation after this slice:

- `python -m pytest -q`: **232 passed, 11 skipped** in this environment;
- `make docs-configs` and `make generate-verilog` complete successfully.

With `iverilog`/`vvp` installed, the 11 optional RTL simulation tests should run
instead of skipping, for an expected total of **243 passed**.


## 21. CPU-driven AXI-stream MMIO bridge transport added

This slice adds `firmware/ascon_accel/ascon_accel_axis_mmio_transport.h` and
`firmware/ascon_accel/ascon_accel_axis_mmio_transport.c`. The transport gives
NEORV32/Tang Nano bring-up a concrete non-DMA path to the stream-native backend:
firmware still uses the callback-based `ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL`
contract, but the callbacks now write/read a small 128-bit MMIO stream bridge.

The bridge base is deliberately separate from the frozen ASCON CSR base:

- `ASCON_ACCEL_BASE_ADDR` remains the control/status/key/nonce/tag ABI window;
- `ASCON_ACCEL_AXIS_MMIO_BASE_ADDR` is the platform-specific stream bridge window.

The transport chunks arbitrary byte strings into 16-byte stream beats, emits
contiguous low-byte `keep` masks, preserves AD/TEXT/CUSTOM through `tuser`, and
requires exact receive length agreement plus final-beat `RX_LAST`. It is a
bring-up bridge before DMA, not the final high-throughput data mover.

Current validation after this slice:

- `python -m pytest -q`: **232 passed, 11 skipped** in this environment;
- `make verify`: **232 passed, 11 skipped**, then config/docs/RTL generation completes.

With `iverilog`/`vvp` installed, the 11 optional RTL simulation tests should run
instead of skipping, for an expected total of **243 passed**.


## 22. NEORV32 stream benchmark build mode added

This slice wires the CPU-driven AXI-stream MMIO transport into the actual
`firmware/neorv32_ascon_benchmark` application instead of leaving it as a
standalone transport and documentation-only bridge. The benchmark now has two
compile-time modes:

- default `USE_AXIS_MMIO=0`: legacy MMIO word data plane;
- `USE_AXIS_MMIO=1`: stream-native data plane through the MMIO-to-AXI-stream
  bridge transport.

The stream build adds `ascon_accel_axis_mmio_transport.c`, defines
`ASCON_BENCH_USE_AXIS_MMIO=1`, initializes an
`ascon_accel_axis_mmio_transport_ctx_t`, switches the driver to
`ASCON_ACCEL_DATA_PLANE_AXI_STREAM_EXTERNAL`, installs the transport callbacks,
and only then resets/probes the accelerator. This matches the stream-native SoC
top behavior: firmware programs the CSR window, asserts `CONTROL.START`, and
then pushes AD/text beats into the separate stream bridge window.

The UART output now reports which data plane was selected. For the stream build
it also prints the AXI bridge base address plus TX/RX beat counters and the last
transport status, which gives board bring-up an immediate smoke-test signal that
the CPU really exercised the stream path.

Build command for the stream path:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware
```

Current validation after this slice:

- `python -m pytest -q`: **236 passed, 11 skipped** in this environment;
- with `iverilog`/`vvp` installed, the 11 optional RTL simulation tests should
  run instead of skipping, for an expected total of **247 passed**.


## 23. RTL MMIO-to-AXI-stream bridge added

This slice adds the hardware side of the CPU-driven stream bridge introduced for
NEORV32 and Tang Nano bring-up. The new `rtl/common/ascon_axis_mmio_bridge.v`
module implements the same register contract used by
`ascon_accel_axis_mmio_transport.c`: TX data/keep/user/control registers commit
one 128-bit AXI-stream beat, while RX data/keep/user/status registers expose
the oldest output beat queued in a small RX FIFO until firmware writes `RX_CTRL.POP`.

The bridge keeps TX one beat deep but now gives RX a small FIFO. It is designed
for correctness, register-contract validation, and early board smoke tests rather
than peak throughput. The RX FIFO avoids the immediate CPU-driven full-duplex
deadlock for small multi-beat ciphertext/plaintext outputs. Future
high-throughput systems can still replace it with DMA while keeping the
stream-native AEAD backend and firmware ABI intact.

The slice also adds `rtl/common/ascon_accel_stream_aead128_axis_mmio_system.v`,
a NEORV32-oriented integration wrapper with two independent MMIO windows:

- `csr_bus_*` drives the frozen ASCON control/status/key/nonce/tag ABI;
- `axis_bus_*` drives the CPU-controlled stream bridge.

This gives board-level integration one concrete RTL block that matches the
existing `USE_AXIS_MMIO=1` firmware benchmark mode.

Current validation after this slice:

- `python -m pytest -q`: **241 passed, 12 skipped** in this environment;
- with `iverilog`/`vvp` installed, the optional RTL simulation and syntax tests
  should run instead of skipping, for an expected total of **253 passed**.


## Added: AXI-stream MMIO bridge behavioral simulation

The CPU-driven stream bridge now has an optional Icarus Verilog behavioral simulation via:

```bash
make axis-mmio-bridge-sim
```

The simulation drives MMIO writes into `ascon_axis_mmio_bridge.v`, verifies that the TX AXI-stream beat is held until `tready`, injects one RX AXI-stream beat, reads it back through MMIO, and verifies `RX_CTRL.POP` clears the RX holding register.

Validation in this environment: `python -m pytest -q` reports **243 passed, 14 skipped**. On a machine with `iverilog/vvp`, the optional simulator tests run for an expected total of **257 passed**.

### Integrated stream AEAD AXI-MMIO system simulation

Added an integration-level RTL smoke simulation for `ascon_accel_stream_aead128_axis_mmio_system`. The testbench drives the frozen CSR/MMIO window plus the CPU-driven AXI-MMIO bridge window, starts the stream backend, feeds AD/TEXT beats through the bridge, reads ciphertext back through the bridge RX register, and checks the generated tag through the ABI tag registers.

Validation in this environment: `python -m pytest -q` reports **247 passed, 18 skipped**. On a machine with `iverilog/vvp`, the optional simulator tests run for an expected total of **265 passed**.

### Added: FIFO-backed RX path for the AXI-MMIO bridge

The CPU-driven AXI-MMIO bridge no longer has a single-beat RX bottleneck. The
RX side is now FIFO-backed, with `RX_FIFO_DEPTH` forwarded by
`ascon_accel_stream_aead128_axis_mmio_system`. `STATUS.RX_LEVEL` exposes the
queued-beat count for bring-up diagnostics, while existing firmware can continue
to use only `RX_VALID`, `RX_LAST`, and `RX_CTRL.POP`.

The integrated system simulation tool now accepts multi-beat plaintext vectors
that fit within the default four-beat RX FIFO. This proves the CSR window,
CPU-driven bridge, and stream-native AEAD backend can complete small multi-beat
messages without requiring DMA.

Validation in this environment: `python -m pytest -q` reports **248 passed, 19 skipped**. On a machine with `iverilog/vvp`, the optional simulator tests run for an expected total of **267 passed**.

### Added: multi-beat integrated stream AXI-MMIO system simulation

The integrated `ascon_accel_stream_aead128_axis_mmio_system` simulation now covers a broader FIFO-fit vector matrix instead of only the original smoke cases. The behavioral tests include empty payloads, short partial-final-block payloads, two-beat text, one-beat AD plus two-beat text, multi-beat AD plus multi-beat text, and a message that fills the default four-beat RX FIFO exactly.

The generated testbench now prints the bridge `STATUS.RX_LEVEL` alongside each `OUT_BEAT`, and the Python parser records those levels. On machines with `iverilog/vvp`, pytest checks that every expected ciphertext beat is drained and that the observed RX level never exceeds `SYSTEM_RX_FIFO_DEPTH`.

Validation in this environment: `python -m pytest -q` reports **250 passed, 23 skipped**. On a machine with `iverilog/vvp`, the optional simulator tests run for an expected total of **273 passed**.

### Added: stream-native NEORV32 CFS wrapper

This slice adds the board-facing CFS replacement for the stream-native AEAD128
path: `rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd`.  It instantiates
`ascon_accel_stream_aead128_axis_mmio_system` and splits one NEORV32 CFS address
region into two local windows:

```text
CFS base + 0x000..0x0ff -> frozen ASCON CSR/MMIO ABI
CFS base + 0x100..0x1ff -> CPU-driven AXI-stream MMIO bridge
```

The matching file list is `rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f`.
The NEORV32 benchmark Makefile now supports `USE_CFS_AXIS_MMIO=1`, which selects
the stream transport and defines `ASCON_ACCEL_AXIS_MMIO_BASE_ADDR=0xFFEB0100u`
for the single-CFS-window wrapper.  Documentation was added in
`docs/neorv32_stream_cfs_integration.md`.

Validation in this environment: the new CFS integration tests pass, and the test
collection is now **256 passed, 23 skipped** without `iverilog/vvp`.  On a
machine where every optional simulator test runs instead of skipping, the full
collection is expected to total **279 tests**.


### Added: Tang Nano 9K NEORV32 stream board manifest

This slice adds the first board-facing handoff contract for the stream-native
NEORV32/Tang Nano 9K path:

```text
boards/tangnano9k/neorv32_stream_axis_mmio/manifest.json
```

The manifest binds together:

- `rtl/neorv32/ascon_cfs_stream_axis_mmio_file_list.f`;
- `rtl/neorv32/neorv32_cfs_ascon_stream_axis_mmio.vhd`;
- firmware build mode `USE_CFS_AXIS_MMIO=1`;
- `ASCON_ACCEL_BASE_ADDR=0xFFEB0000u`;
- `ASCON_ACCEL_AXIS_MMIO_BASE_ADDR=0xFFEB0100u`;
- the intended Tang Nano 9K bring-up sequence.

A new inspection tool, `tools/print_neorv32_stream_board_manifest.py`, validates
that the manifest references existing RTL/firmware paths and that the memory map
is internally consistent. The root Makefile target
`make -C boards/tangnano9k/neorv32_stream_axis_mmio manifest` prints and checks the manifest, while
`boards/tangnano9k/neorv32_stream_axis_mmio/Makefile` provides convenience
targets for manifest inspection and the NEORV32 firmware build.

Validation in this environment was run in two pytest groups because the full
combined command exceeded the sandbox execution window:

- `python -m pytest -q -k 'not sim'`: **244 passed, 1 skipped, 41 deselected**;
- `python -m pytest -q -k sim`: **19 passed, 22 skipped, 245 deselected**;
- combined coverage: **263 passed, 23 skipped** without `iverilog/vvp`;
- with optional simulator tests available, the full collection is expected to
  reach **286 passing tests**.

Generation and manifest targets completed:

- `make docs-configs`;
- `make generate-verilog`;
- `make -C boards/tangnano9k/neorv32_stream_axis_mmio manifest`.


## NEORV32 stream board preflight

The Tang Nano 9K stream-native NEORV32 scaffold now includes a preflight tool and Makefile target. It validates the manifest, source paths, firmware mode, memory map, and Makefile target availability, then emits `build/neorv32_stream_axis_mmio/preflight.json` as the first board bring-up plan.


## NEORV32 stream board build package

The Tang Nano 9K stream-native NEORV32 target now has a reproducible board
handoff package generator:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio package
```

The default output is `build/neorv32_stream_axis_mmio/package`. It contains the
validated manifest, preflight plan, memory map, split Verilog/VHDL RTL source
lists, firmware make/C address definitions, and a `commands.sh` pre-board
validation sketch. This is the last software-side scaffold before integrating
the CFS replacement into an upstream NEORV32 Tang Nano 9K project.


## NEORV32 UART benchmark report parser

The board-facing benchmark flow now includes a UART log parser:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio uart-report LOG=uart.log
```

The parser consumes the output printed by `firmware/neorv32_ascon_benchmark`,
extracts the selected data plane, ABI/capability values, software and hardware
ciphertext/tag values, encrypt/decrypt cycle counts, AXI-MMIO beat counters,
speedups, warnings, and final PASS/FAIL status, then emits both JSON and
Markdown reports under `build/neorv32_stream_axis_mmio/`.  Strict mode rejects
logs with missing PASS, encryption/tag mismatches, nonzero driver status,
nonzero AXI transport status, or hardware cycle counts that do not beat the
software reference when the relevant fields are present.

This gives the physical board bring-up phase a reproducible artifact format for
lab notes and final project reporting instead of relying on manual UART-log
inspection.


## NEORV32 stream board dry-run build plan

The Tang Nano 9K stream-native NEORV32 target now has a dry-run build-plan tool:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio build-plan
```

The tool validates the generated board package, confirms the CSR/AXI-MMIO memory map, checks that the mixed Verilog/VHDL source split is complete, confirms stream firmware mode `USE_CFS_AXIS_MMIO=1`, records optional tool availability, and writes `build_plan.json` plus `build_plan.md`. This is a pre-synthesis handoff artifact: it does not program hardware, but it makes the board build sequence reproducible before the real Tang Nano flow.


## NEORV32 stream board session

Use `make -C boards/tangnano9k/neorv32_stream_axis_mmio session` to generate `build/neorv32_stream_axis_mmio/session/session.json` and `session.md`. The report ties the board package, memory map, optional bitstream, optional UART log, and benchmark parser output into one archived bring-up session.

---

## Latest stage: NEORV32 stream board session runner

A board-session handoff layer was added so Tang Nano 9K bring-up can be archived
as one reproducible report. The new tool validates the generated board package,
records the memory map and firmware mode, records the optional bitstream/program
command, and embeds the UART benchmark parser output when a captured log is
provided.

New files:

- `tools/run_neorv32_stream_board_session.py`
- `tests/test_neorv32_stream_board_session.py`
- `docs/neorv32_stream_board_session.md`

New targets:

- `make -C boards/tangnano9k/neorv32_stream_axis_mmio session`
- `make -C boards/tangnano9k/neorv32_stream_axis_mmio session`

The default mode is safe: it does not program hardware. Hardware programming is
only attempted if the user explicitly passes `--program --no-dry-run` to the CLI.
This keeps CI and development machines from touching boards accidentally while
still documenting the exact `openFPGALoader` command needed for bring-up.

Validation performed for this stage:

- `python -m pytest -q tests/test_neorv32_stream_board_session.py`: 7 passed
- `make -C boards/tangnano9k/neorv32_stream_axis_mmio session`: completed
- `make docs-configs`: completed
- `make generate-verilog`: completed
- `python -m pytest --collect-only -q`: 320 tests collected

## Tang Nano 9K Gowin/NEORV32 handoff scaffold

Added a Gowin/NEORV32 handoff generator for the stream-native ASCON target:

- `tools/prepare_neorv32_stream_gowin_handoff.py`
- `docs/neorv32_stream_gowin_handoff.md`
- `tests/test_neorv32_stream_gowin_handoff.py`

The generated directory records the memory map, firmware build flags, Verilog
source list, VHDL CFS wrapper list, guarded programming helper, and manual
integration notes.  This stage intentionally does not synthesize the full board
project because the real NEORV32/Tang Nano build is mixed-language and requires
a VHDL-capable SoC integration flow.

## Project checkpoint bundle

A release-style checkpoint generator now packages the current stream-native ASCON
development state into an archiveable handoff artifact:

```sh
make project-checkpoint-bundle
```

The output directory `build/project_checkpoint_bundle/` and archive
`build/project_checkpoint_bundle.zip` contain checkpoint metadata, the project
status snapshot, the Tang Nano 9K NEORV32 stream board manifest, and copied
evidence files referenced by the milestone report. This is intended for the
development-process report and for preserving a clean handoff before the next
hard gate: real Tang Nano/NEORV32 build execution plus strict UART benchmark
proof.


## Latest board bring-up UX update

Added a Tang Nano / NEORV32 stream bring-up doctor that checks `NEORV32_HOME`, generated handoff files, UART tool availability, serial-device permissions, and provides guided next actions before real board execution. The flake dev shell now includes `picocom`, and the generated Gowin handoff includes a guarded UART capture helper.


## Latest portability update: machine-independent board bring-up

The board bring-up flow no longer assumes a specific workstation layout such as
`$HOME`-specific NEORV32 paths or a hardcoded `/dev/ttyUSB0` UART path. New helper tools
resolve NEORV32 from an explicit `NEORV32_HOME`, the environment, or the
project-local `external/neorv32` checkout created by `make -C boards/tangnano9k/neorv32_stream_axis_mmio firmware`. UART
capture now uses a Python wrapper that can auto-detect a unique usable serial
device across common Linux and macOS USB-serial naming schemes, while still
allowing `SERIAL=...` when several devices are connected. This makes the Tang
Nano / NEORV32 handoff reproducible across machines instead of being specific to
one developer PC.


See `docs/neorv32_firmware_toolchain_profiles.md` for the portable NEORV32 firmware toolchain profile and Nix compatibility probe.
