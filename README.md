# Ascon hardware-oriented Python model

This package is a typed Python model of selected NIST SP 800-232 Ascon building blocks, written so the model structure maps cleanly to Verilog.

Implemented so far:

- fixed-width unsigned integer wrappers: `U4`, `U8`, `U16`, `U64`, `U128`, `U320`
- separated byte-sequence hex and integer hex views
- bitstring and byte-oriented `parse` / `pad`
- Ascon IV construction for AEAD128, Hash256, XOF128, and CXOF128
- little-endian five-word Ascon state model
- 64-bit and 128-bit block wrappers
- 64-bit and 128-bit rate absorption helpers
- AEAD128 key/nonce initial-state construction
- AEAD128 key injection helpers
- AEAD associated-data domain separator
- split Ascon permutation layers: `pc.py`, `ps.py`, `pl.py`
- substitution layer implemented both as `p_s_lut()` and `p_s_bitsliced()`
- split permutation wrappers: `p6.py`, `p8.py`, `p12.py`
- Verilog emission colocated with the Python model object/layer it describes
- generated `.vh` include fragments and standalone `.v` combinational wrappers
- byte-aligned known-answer tests for NIST AEAD128, Hash256, XOF128, and CXOF128
- AXI-stream AEAD128 transaction oracle for unbounded AD/plaintext/ciphertext framing
- stream-native AEAD128 encryption RTL plus buffered authenticated decrypt RTL policy
- optional Icarus simulation harnesses for streaming encryption and buffered decrypt backends
- unified stream backend wrapper and firmware-facing 128-bit AXI Stream SoC top
- host-side AXI Stream reference emulator for end-to-end firmware validation
- host-side firmware stream benchmark tool for pre-board NEORV32/SoC smoke testing
- CPU-driven AXI-stream MMIO transport for NEORV32/bring-up bridge integration
- FIFO-backed RTL MMIO-to-AXI-stream bridge and integrated stream AEAD128 system wrapper
- multi-beat integrated AXI-MMIO system simulation coverage up to the default RX FIFO depth
- NEORV32 benchmark firmware can select the stream-native MMIO bridge path with `USE_AXIS_MMIO=1`
- stream-native NEORV32 CFS wrapper maps CSR and AXI-MMIO bridge windows into one CFS region
- Tang Nano 9K NEORV32 stream board manifest freezes the RTL file list, firmware mode, and memory map

## Run tests

From the package root:

```bash
python -m pytest -q
```

Expected result for this step in an environment without `iverilog`/`vvp`:

```text
263 passed, 23 skipped
```

With Icarus Verilog installed, the optional RTL simulation tests run instead of
skipping, so the expected total is:

```text
286 passed
```



## Configurable architecture generation

The repository now separates the golden specification model from implementation choices:

```text
ascon_hwmodel/   # typed golden model and reference Verilog helpers
ascon_arch/      # architecture/configuration vocabulary and validation
configs/         # concrete ASIC/FPGA configuration examples
tools/           # design and Verilog generation entry points
build/           # generated design products, ignored by git
```

Generate the ASIC baseline with separate encryption/decryption datapaths:

```bash
PYTHONPATH=. python tools/generate_design.py --preset asic_two_datapaths
```

Generate the ASIC two-datapath variant with two rounds per cycle:

```bash
PYTHONPATH=. python tools/generate_design.py   --preset asic_two_datapaths   --permutation-profile two_rounds_per_cycle
```

Generate an FPGA design with N parallel engines and a selected permutation profile:

```bash
PYTHONPATH=. python tools/generate_design.py   --preset fpga_n_parallel_engines   --engine-count 4   --permutation-profile four_rounds_per_cycle
```

Permutation profiles are documented in `docs/permutation_architecture.md`.

## Known-answer tests

`tests/test_known_answer_vectors.py` embeds a compact byte-aligned KAT subset:

- Ascon-AEAD128 encrypt/decrypt vectors from the official `ascon/ascon-c` LWC KAT file
- Ascon-Hash256 empty-message digest
- Ascon-XOF128 empty-message 512-bit output
- Ascon-CXOF128 single-byte message with empty customization string

The current test scope is deliberately byte-aligned. Full ACVP bit-length coverage will require bit-granular hash/XOF wrappers on top of `bitstring.py`.

## Endianness convention

The state is modeled as five 64-bit integer words:

```text
x0 = S[0:63]
x1 = S[64:127]
x2 = S[128:191]
x3 = S[192:255]
x4 = S[256:319]
```

A 40-byte state image is loaded little-endian word by word. For example, bytes `00 01 02 03 04 05 06 07` become the integer word `0x0706050403020100`.

A Verilog `[319:0]` state bus preserves the logical bit index:

```verilog
state[63:0]    = x0;
state[127:64]  = x1;
state[191:128] = x2;
state[255:192] = x3;
state[319:256] = x4;
```

Therefore state packing is:

```verilog
state = {x4, x3, x2, x1, x0};
```

## S-box implementation policy

The substitution layer has two equivalent Python views:

- `p_s_lut(state)`: reference model using 64 scalar 5-bit S-box table lookups
- `p_s_bitsliced(state)`: hardware-shaped model using word-level boolean operations

`p_s(state)` currently aliases `p_s_bitsliced(state)`, because that representation maps directly to combinational RTL and is much faster in Python than looping through 64 single-bit slices.

Generated Verilog also emits both:

- `ascon_p_s_lut`
- `ascon_p_s_bitsliced`
- `ascon_p_s`, which currently calls the bitsliced implementation

## Verilog generation policy

The Verilog generation code is colocated with the Python model layer it describes:

```text
iv.py       -> IV Verilog helpers
state.py    -> state pack/access helpers
byteops.py  -> pad helpers
pc.py       -> p_C and round constant helpers
ps.py       -> p_S LUT and bitsliced helpers
pl.py       -> p_L and rotation helpers
round.py    -> round composition helper
p6.py       -> Ascon-p[6] helper and standalone wrapper
p8.py       -> Ascon-p[8] helper and standalone wrapper
p12.py      -> Ascon-p[12] helper and standalone wrapper
domain.py   -> AEAD domain separator helper
keyops.py   -> AEAD128 key/init/finalization helpers
```

`ascon_hwmodel/verilog.py` is only an aggregation/file-writing facade.

Generate Verilog files with:

```bash
PYTHONPATH=. python tools/generate_verilog.py
```

This writes:

```text
rtl/generated/ascon_iv.vh
rtl/generated/ascon_state.vh
rtl/generated/ascon_aux.vh
rtl/generated/ascon_pc.vh
rtl/generated/ascon_ps.vh
rtl/generated/ascon_pl.vh
rtl/generated/ascon_round.vh
rtl/generated/ascon_p6.vh
rtl/generated/ascon_p8.vh
rtl/generated/ascon_p12.vh
rtl/generated/ascon_aead_domain_key.vh
rtl/generated/ascon_model.vh
rtl/generated/ascon_permutation_comb.v
rtl/generated/ascon_p6_comb.v
rtl/generated/ascon_p8_comb.v
rtl/generated/ascon_p12_comb.v
```

The `.vh` files are include fragments because they define functions/localparams to be included inside a module or package scope. The `.v` files are standalone combinational module wrappers.

## AEAD encryption/decryption step

The AEAD layer is now split by phase:

```text
ascon_hwmodel/aead_config.py
ascon_hwmodel/aead_init.py
ascon_hwmodel/aead_ad.py
ascon_hwmodel/aead_plaintext.py
ascon_hwmodel/aead_ciphertext.py
ascon_hwmodel/aead_final.py
ascon_hwmodel/aead_encrypt.py
ascon_hwmodel/aead_decrypt.py
ascon_hwmodel/aead.py
```

The standardized NIST mode is `AEADVariant.NIST_AEAD128`. Legacy Ascon submission-family parameter sets are present in `aead_config.py` as scaffolds, but only the NIST mode is byte-level conformance-targeted by the current little-endian state model.

Run:

```bash
python -m pytest -q
PYTHONPATH=. python tools/generate_verilog.py
python demo_aead.py
```

Generated Verilog now includes:

```text
rtl/generated/ascon_rate.vh
rtl/generated/ascon_aead.vh
rtl/generated/ascon_hash_xof.vh
```

## Hash/XOF bonus layer

NIST byte-oriented helpers are included for:

```python
ascon_hash256(message)
ascon_xof128(message, output_bytes)
ascon_cxof128(message, output_bytes, customization)
```

These currently expose byte-aligned APIs. Bit-granular output can be layered on top of `bitstring.py` later.

## Architecture configuration layer

The repository now has a first implementation-architecture layer under `ascon_arch/`.
The ASCON specification model remains in `ascon_hwmodel/`; architecture choices are represented separately as typed configs.

Current architecture families:

```text
shared_datapath                 low/medium area, one operation at a time
separate_enc_dec_datapaths      higher area, encrypt and decrypt datapaths can progress independently
shared_permutation_mode_fsm     medium area, one shared permutation bottleneck
parallel_engines                N independent engines for high-throughput FPGA scaling
```

The architecture config now has typed axes for algorithm support, topology, permutation style, datapath width, context storage/scheduling, padding and length handling, I/O style, security options, and RTL emission metadata. Invalid combinations are rejected before RTL is generated.

Chosen baselines:

```text
ASIC: asic_two_datapaths
FPGA: fpga_N_parallel_engines, with configurable N
```

Generate design-product skeletons with:

```bash
PYTHONPATH=. python tools/generate_design.py --preset asic_two_datapaths
PYTHONPATH=. python tools/generate_design.py --preset fpga_n_parallel_engines --engine-count 4
PYTHONPATH=. python tools/generate_design.py --preset asic_shared_datapath
PYTHONPATH=. python tools/generate_design.py --preset asic_shared_permutation_mode_fsm
```

Or use the explicit JSON configs:

```bash
PYTHONPATH=. python tools/generate_design.py --config configs/asic/two_separate_datapaths.json
PYTHONPATH=. python tools/generate_design.py --config configs/fpga/n_parallel_engines_4.json
```

Generated design products are written under `build/`, which is intentionally ignored by git. Each product includes resolved config metadata, expected metrics, a module manifest, and structural SystemVerilog boundaries for the selected architecture.

## State/context organization axis

The architecture generator now includes explicit state/context profiles:

```text
single_320_register
state_plus_shadow
multi_context_registers
fpga_bram_lutram
separate_state_per_core
shared_state_ram_pipelined_p8
```

Project defaults:

```text
ASIC: single_320_register
FPGA: fpga_bram_lutram with multi-context interleaving
```

Generate the FPGA baseline with explicit context profile:

```bash
PYTHONPATH=. python tools/generate_design.py \
  --preset fpga_n_parallel_engines \
  --engine-count 4 \
  --context-profile fpga_bram_lutram \
  --contexts-per-engine 12
```

Generate the ASIC single-state baseline:

```bash
PYTHONPATH=. python tools/generate_design.py \
  --preset asic_two_datapaths \
  --context-profile single_320_register
```

See `docs/context_architecture.md` for the detailed profile meanings.

## Tang Nano 9K full AEAD128 hardware target

The first board-level target is a complete Ascon-AEAD128 fixed-vector smoke test:

```sh
cd boards/tangnano9k/ascon_aead128_kat_slow
make
make prog-sram
```

This target is intentionally slow and simple: one Ascon round per clock. It exercises initialization, associated-data processing, plaintext processing, finalization, and ciphertext/tag comparison in RTL.


### AXI-stream MMIO bridge simulation

Run the CPU-driven bridge behavioral smoke test with:

```bash
make axis-mmio-bridge-sim
```
Additional optional RTL smoke test:

```bash
make stream-axis-mmio-system-sim
```

This drives the complete CSR + AXI-MMIO bridge + stream AEAD128 system wrapper through its two MMIO windows and compares the RTL encryption result against the Python golden model.


This verifies the MMIO register contract, TX AXI-stream commit/handshake behavior, RX holding register, and `RX_CTRL.POP` path before NEORV32 board bring-up.


## Tang Nano 9K NEORV32 stream preflight

The board-facing stream target includes manifest and preflight checks:

```sh
make neorv32-stream-board-manifest
make neorv32-stream-board-preflight
```

The preflight writes `build/neorv32_stream_axis_mmio/preflight.json` and records the CSR/AXI-MMIO memory map, firmware build mode, RTL source list, host tool availability, and optional `NEORV32_HOME` readiness.

## Tang Nano 9K NEORV32 stream board package

The board-facing stream target can generate a deterministic handoff package:

```sh
make neorv32-stream-board-package
```

This writes `build/neorv32_stream_axis_mmio/package` with the validated manifest,
preflight plan, split Verilog/VHDL file lists, firmware defines, memory map, and
pre-board command script for the NEORV32 stream CFS target.
