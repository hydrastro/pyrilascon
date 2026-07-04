# pyrilascon

A configurable hardware accelerator for the **Ascon** family (NIST SP 800-232),
built around a correct Python golden model, a design-space catalog, and a real
RTL generator grown from that model. FPGA target is the Tang Nano 9K (open Gowin
flow); the ASIC path feeds TinyTapeout via
[`pyrilascontt`](https://github.com/hydrastro/pyrilascontt).

This tree is a rewrite of an earlier, heavier repository. The goal is the same
ambition (explore the whole design space) with far less ceremony, and an honest
line between what is *specified* and what is *built*.

## Layout

```
ascon_hwmodel/       typed golden model + Verilog emission   (REUSED, passes NIST KATs)
ascon_designspace/   the slim design-space layer             (NEW - replaced ascon_arch)
  axes.py            the vocabulary (algorithm, datapath, permutation, ...)
  resolve.py         coordinates -> derived RTL-relevant fields
  rules.py           validity predicates (the reason it's 560, not 816)
  realize.py         the tier model (generated / hand-written / specified)
  catalog.py         enumerate the space + attach a realization to every point
  generator/         the tier-1 RTL generator, grown from the model
    permutation.py   emit the round-based permutation core (R rounds/cycle)
    smoke.py         emit a self-checking board top around a generated core
    verify.py        simulate a generated core bit-exact vs the golden model
ascon_boards/        one build driver for every board (synth/PnR/pack/flash)
boards/              board descriptors (*.toml) + pin maps (*.cst)
tests/               golden-model + catalog/rules + generator-sim + board tests
docs/ARCHITECTURE.md the design rationale (tiers, generator plan, benchmark)
```

The generator, the board flow, the firmware, and the benchmark/host path are all
in the tree now (stages 1-4). The remaining hand-written cores and the one
deferred generator family (bit-serial) land as noted in the Roadmap - brought
over deliberately, not dumped. RTL-simulation tests run alongside the RTL they
exercise (they skip only when Icarus Verilog is absent).

## The tier model (the honest part)

Every point in the design space is one of three tiers:

* **Tier 1 - generator.** Emitted by a parameterized RTL generator grown from
  the golden model's Verilog emission (the model already emits a correct 320-bit
  round). The generator emits **three permutation families** today, and every
  emitted core is **verified bit-exact against the model's NIST-KAT-verified
  p6/p8/p12** by simulation:
  round-based (R rounds/cycle), fully-pipelined (one round/stage, 1 result/cycle,
  throughput-verified), column-serial (K S-box columns/cycle), and bit-serial
  (serial S-box *and* serial linear layer - the most-serial datapath, the narrow
  width that fits a TinyTapeout ASIC tile). The serial cores are built from the
  model's own S-box and rotation constants, not from memory. **All 134 tier-1
  points read `GENERATED`; nothing on the generator axis is left `PLANNED`.**
  The generator also emits and verifies the design-space *topologies* that
  arrange these cores (single core; one pipelined permutation shared across N
  contexts; M parallel pipelines - `generator/structural.py`), and full
  **end-to-end algorithm cores** - Ascon-AEAD128 (`generator/aead.py`) and
  Ascon-Hash256 (`generator/hash256.py`) - that wrap a generated permutation in
  a hardwired-FSM sponge and are verified against NIST-KAT model vectors
  (encrypt/decrypt/tag-reject and digests, across partial and multi-block inputs).
* **Tier 2 - hand-written.** A vetted RTL core already implements the point
  (today: the working FPGA AEAD128 128-bit AXI-stream cores).
* **Tier 3 - specified.** In the design space but deliberately not
  auto-generated. **Security countermeasures (masking / threshold / DOM) live
  here** - a generator that emits unverified crypto countermeasures is worse
  than none. Algorithm variants without golden-model KAT support live here too,
  until that support exists.

The catalog records the tier for all 560 valid points, so "we explored the whole
space, and here is exactly what is realized and how" is a checkable statement,
not a slogan.

```sh
python -m ascon_designspace        # prints the catalog + tier breakdown
```

## Generate and verify a core

```sh
python -m ascon_designspace.generator --list                        # what the generator emits
python -m ascon_designspace.generator --rounds-per-cycle 4 --verify  # round-based, sim vs model
python -m ascon_designspace.generator --pipelined 12 --verify        # fully-pipelined p12
python -m ascon_designspace.generator --column-serial 1 --verify     # column-serial (1 col/cycle)
python -m ascon_designspace.generator --bit-serial --verify          # bit-serial (most serial)
python -m ascon_designspace.generator --context-pipeline 12 --contexts 4 --verify  # topology
```

`--verify` compiles the emitted core with Icarus Verilog and checks it
bit-for-bit against the model's combinational p6/p8/p12 over random + edge-case
vectors.

## Add a board / flash

A board is a descriptor plus a pin map; the same driver builds any board/target
pair. `perm_smoke` wraps a **generated** core in a self-checking top (an LED
lights iff the hardware result matches the model's golden value).

```sh
python -m ascon_boards list-boards
python -m ascon_boards list-targets
make board-dry-run BOARD=tangnano9k TARGET=perm_smoke   # print the exact flow
make synth         BOARD=tangnano9k TARGET=perm_smoke   # yosys synth (needs yosys)
make flash         BOARD=tangnano9k TARGET=perm_smoke   # full flow + openFPGALoader
```

Adding a board means dropping a `boards/<name>.toml` and a `.cst` - no new
Makefile. The driver knows both the `nextpnr-gowin` and `nextpnr-himbaechel`
invocations.

## The four workflows this repo is organized around

1. **Add a board** - a board becomes a small descriptor (device / family / clock)
   plus a pin-constraint file; one shared build flow does synth/PnR/pack. No
   per-board Makefile. *(stage 3 - done)*
2. **Flash a board** - one command, board as a parameter:
   `make flash BOARD=tangnano9k TARGET=...`. *(stage 3 - done)*
3. **Interact via C** - the accelerator driver (clean ABI + MMIO/AXI-stream/DMA
   transports) with two clear entry points: on-chip firmware (NEORV32 runs the
   driver) and host-driven (your machine drives the flashed board over serial).
   The driver is verified natively end-to-end through a ref-emulator transport
   (`tests/test_driver_selftest.py`). *(stage 4 - done)*
4. **Benchmark vs CPU-only** - one command builds the SW-reference-vs-HW-accel
   harness, runs it, and parses the result. Headline metric is the **same-fabric**
   NEORV32 cycle comparison (`hardware_cycles < software_cycles`), which is the
   controlled experiment; cross-platform cycles-per-byte is optional context.
   The C reference (the software baseline) is verified bit-exact vs the model;
   the host tool parses the UART log and checks the criterion. `make bench-native`
   runs here; `make bench` builds the NEORV32 image. *(stage 4 - done)*

## Run the tests

```sh
python -m pytest -q
```

Golden-model + catalog tests run everywhere. Simulator-dependent RTL tests skip
automatically when `iverilog`/`vvp` are unavailable, and run when Icarus Verilog
is installed.

## Roadmap

1. **Scaffold + reuse** *(done)* - new tree, golden model reused with NIST KATs
   green, design-space catalog reproducing 560 with the tier ledger, ceremony
   and checked-in artifacts dropped.
2. **Design-space rewrite** *(done)* - enumeration + validation now live in
   `ascon_designspace` (`axes` + `resolve` + `rules`); `ascon_arch` is deleted.
   The layer went from ~5.3k lines + 38 JSON configs to ~800 lines, same 560
   counts, plus the tier ledger.
3. **Real generator + unified boards** *(done)* - (3a) the generator emits the
   round-based permutation core, R rounds/cycle, verified bit-exact vs the golden
   model in simulation; (3b) one build driver
   + board descriptors, with a self-checking `perm_smoke` target that puts a
   generated core on the Tang Nano 9K and synthesizes with yosys `synth_gowin`.
   The generator now also emits fully-pipelined and column-serial families, all
   verified (118 of 560 `GENERATED`); only bit-serial remains.
4. **Benchmark + host path** *(done)* - the portable C reference (verified
   bit-exact vs the model), the accelerator driver (verified natively through a
   ref-emulator transport), the NEORV32 benchmark harness, and a host-over-serial
   tool that parses the UART log into a SW-vs-HW table and checks
   `hardware_cycles < software_cycles`. `make bench-native` / `bench` / `bench-host`.

5. **Generator, wrappers, algorithm cores, both control styles** *(done)* - all
   134 tier-1 points are `GENERATED` (four permutation families); the three
   catalog topologies are emitted and verified; the permutation is emitted in
   both control styles (hardwired FSM and microcoded sequencer); and the
   generator produces the full algorithm family - AEAD128, AEAD128a, Ascon-128,
   Ascon-80pq, Hash256, XOF128, CXOF128, HashA, XofA. HashA/XofA have no
   independent KAT in the model, so they are verified against a Python reference
   *proven to reduce to the model's Hash256/XOF128 at b=12* (so only the b=8
   round count is spec-supplied, and it is spec-confirmed). The only thing
   deliberately left out is the Tier 3 security countermeasures.

## Provenance

`ascon_hwmodel` and the accelerator firmware/RTL are reused from the previous
repository because they are correct and tested (the golden model passes the
official NIST AEAD128 / Hash256 / XOF128 / CXOF128 vectors). What changed is the
architecture layer, the build orchestration, and the removal of reporting
ceremony, doc sprawl, and generated artifacts from source control.
