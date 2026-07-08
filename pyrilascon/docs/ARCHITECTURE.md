# Architecture

This document records the decisions behind the rewrite so they don't have to be
rediscovered.

## Three layers, one source of truth for the crypto

1. **Golden model (`ascon_hwmodel`).** A typed Python model of Ascon that is the
   single source of cryptographic truth. It passes the official NIST SP 800-232
   known-answer vectors (AEAD128, Hash256, XOF128, CXOF128). Crucially, it
   already emits *real, synthesizable* Verilog for the primitives: the round is
   `p_l(p_s(p_c(state)))`, and it emits both the LUT and bitsliced S-box at full
   320-bit width. Everything hardware-side is anchored to this model.

2. **Design space (`ascon_designspace`).** The vocabulary of architecture
   choices (algorithm, datapath width, permutation style, control, security,
   topology, ...), the validity rules that make some combinations legal and
   others not, and a **catalog** that enumerates every valid point. This replaces
   the old `ascon_arch`, which had the enumeration and validation but emitted
   only structural *skeletons* for RTL (`assign state_o = state_i; // TODO`).

3. **Realization.** How each cataloged point turns into hardware. This is the
   part that was missing, and it is organized into tiers (below).

## Why tiers, and why not "generate everything"

The obvious ambition is a generator that emits synthesizable RTL for all 560
points. The reason that is not the day-one plan is that the design-space axes are
wildly unequal in difficulty, and treating them uniformly is a trap:

* **Datapath width (1 / 8 / 32 / 64 / 128 / 320) and rounds-per-cycle** are
  regular and tractable. The model already emits the 320-bit round; a generator
  is that emission parameterized by how many bits of the S-box layer are
  processed per cycle and how many rounds are unrolled. This is also the axis
  that matters for ASIC: a 320-bit fully-parallel Ascon will not fit a
  TinyTapeout tile, but a 1-bit-serial or 8-bit datapath will. So the most
  valuable generator work is also the most buildable.
* **Topology (N cores, M pipelines x contexts) and control/interface
  (FSM / AXI-stream / CSR / DMA)** are mostly *structural* - how many cores are
  instantiated and how they are fed. This is what the old skeleton generator
  already sketched; it just needs to wrap a *real* core instead of a stub.
* **S-box style (bitsliced / LUT5 / case)** is a free knob - the model emits all
  three already.
* **Security (masking / threshold implementations / DOM)** is research-grade. A
  generator that emits plausible-but-unverified masked RTL is *actively
  dangerous*: a masked S-box that looks right but leaks is a false-confidence bug
  of the worst kind in crypto. These stay hand-written-and-verified-when-built.

### The tiers

* **Tier 1 - generator.** Grown from the golden model's emission. Datapath width
  x rounds-per-cycle x S-box style, plus structural wrappers. Built axis by axis,
  datapath width first. A point's status is `GENERATOR_PLANNED` until the
  generator covers it, then `GENERATED`.
* **Tier 2 - hand-written.** A vetted core exists (the working FPGA AEAD128
  cores). Wired in as a first-class realization.
* **Tier 3 - specified.** Enumerated and validated, but not auto-generated:
  security countermeasures, and algorithm variants without KAT support.

The catalog (`ascon_designspace.catalog`) assigns a tier to every valid point
and is regression-tested to reproduce the exact counts (ASIC 352, FPGA 208, 560
total). This is the honesty layer: the project can state precisely what is
specified versus built.

**The catalog is the generator's front-end, not an alternative to it.** "Catalog
vs generator" is a false choice - enumeration/validation is what a generator
needs on its input side, and the tier ledger is what keeps its output honest.

## Generator (grown from the model, not the old skeleton)

The old `ascon_arch` skeleton track and the model's real emission were
disconnected. The rewrite unifies them: the generator extends
`ascon_hwmodel`'s emission rather than the `ascon_arch` stub emitter.

**Built (stage 3a): the round-based permutation core.**
`generator/permutation.py` emits an iterative permutation module that clocks the
model's `ascon_round_const_index` **R rounds per cycle** (R in 1/2/4/8), using
the model's exact round-constant schedule (p6: idx 10..15, p8: 8..15, p12:
4..15; start = 16 - rounds). Per-stage guards let R not divide the round count,
so one generator handles p6/p8/p12 for every R. The round block is instantiated
once (into `next_s`) and shared between the state update and the result capture,
so the logic is not duplicated.

Verification is the point: `generator/verify.py` compiles each emitted core with
Icarus Verilog and checks it **bit-exact against the model's combinational
`p6`/`p8`/`p12`** - which are themselves NIST-KAT-verified - over random and
edge-case vectors. So generated core == model combinational == NIST, by
transitivity. This is what lets a catalog point read `GENERATED` honestly (**all
134 tier-1 points today - the generator axis has nothing left `PLANNED`**).

**Four families, all verified.** Beyond the round-based core, the generator emits
(a) a *fully-pipelined* permutation (`emit_pipelined_permutation`, one round per
stage, throughput one result/cycle - the testbench streams inputs back-to-back so
throughput as well as correctness is checked), (b) a *column-serial* permutation
(`serial.py`, K S-box columns/cycle), and (c) a *bit-serial* permutation
(`serial.py`, the most-serial datapath). The serial cores are genuinely
area-reduced, not fake serializations: they are built from the model's *own*
emitted primitives - `ascon_p_c`, the exact 5-bit `ascon_sbox5_lut`, and the
model's rotation constants - using its documented column bit-layout, and they
present the same interface as the iterative core so the standard testbench
verifies them unchanged.

**Bit-serial, done right.** The subtlety is real: the S-box's atomic unit is a
5-bit column, so "bit-serial" cannot mean a sub-column S-box. The generated
bit-serial core serializes *both* layers instead - one S-box column per cycle,
and the linear layer one bit *per word* per cycle (each output bit is
`x_i[j] ^ x_i[(j+r1)%64] ^ x_i[(j+r2)%64]`; since 64 = 2**6 the rotated index is
a truncated 6-bit add, and a working register holds the pre-update word). The
combinational core collapses to one S-box plus five 3-input XORs. It is verified
bit-exact against the model like every other family, so it ships.

**Structural topologies.** The generator also arranges cores into the catalog's
*topologies* (`structural.py`), verified by composing the already-proven cores:
`single_core` (a bare permutation engine), `one_pipelined_permutation_n_contexts`
(N independent sessions interleaved through one pipelined core, each result
carried out with its context tag), and `m_pipelines_n_contexts` (M such lanes for
M-times throughput). What is deliberately *not* auto-generated is the microcoded
control variant and full AEAD/sponge integration - Tier 2 already provides a
hand-written working AEAD core - and the Tier 3 countermeasures.

**Algorithm cores.** The generator closes the loop from "generate a permutation"
to "generate an accelerator", for the whole family the model has a reference for.
`aead.py` emits one config-driven AEAD core covering AEAD128, AEAD128a, Ascon-128
and Ascon-80pq - the variants differ only in rate (8 vs 16, i.e. x0 vs x0||x1),
data rounds (p6 vs p8), key size (128 vs 160-bit, placed byte-aligned into the
IV||key||nonce image and XORed relative to the last state word), and IV; domain
separation is uniformly x4 ^= 1<<63. `hash256.py` emits the sponge hash/XOF family
- Hash256, XOF128 (word-aligned extendable output), and CXOF128 (which first
absorbs a length word and the customization buffer). All compose the generated
`ascon_perm_iter_r1` and drive it through a hardwired-FSM sponge with a bounded
buffered interface, so a testbench can load a vector, pulse start, and read the
result without modelling a stream. Each is checked in simulation against the
model over a spread of lengths - AEAD for ciphertext+tag, decrypt round-trip, and
corrupted-tag rejection; hash/XOF for the digest including the empty-message KAT.

The two variants deliberately absent are HashA and XofA: the model does not
implement them (its hash absorb hardcodes p12, so there is no rounds-8 reference
to verify against), and an unverified crypto core is precisely what this project
will not ship. Both control styles are now emitted. The permutation comes in the hardwired-FSM
form (counter + comparator derive the round constant and stop condition) and a
**microcoded-sequencer** form (`control.py`): a small microcode ROM holds one
instruction per round - {const_index, halt} - and a PC-driven sequencer walks it,
applying the verified round function with the ROM's constant. The p12 microprogram
is the constant schedule 4..15; p8/p6 are suffixes, so choosing the round count is
just an entry point. Both drive the identical round datapath, so both are verified
against the model by the same permutation testbench.

HashA and XofA are emitted too, despite the model having no independent reference
for them (its hash absorb hardcodes p12). They are verified against a Python
reference built from the model's *verified* permutation, following the Ascon
spec's schedule (p12 init/finalization, p8 intermediate absorb/squeeze). That
reference is grounded by a test proving it reduces byte-for-byte to the model's
Hash256/XOF128 at b=12 - so the only spec-supplied quantity for the b=8 cores is
the round count itself, which the Ascon specification pins down. It is weaker than
a NIST KAT (there is none) but far from unverified.

A second board, the **Tang Nano 20K** (GW2AR-18, himbaechel backend), is wired in
as a pure descriptor + pin map, exercising the "add a board" workflow: it reuses
the same generated smoke target, with a power-on reset (the 20K wires no reset
button) selected by a `reset_style` field in the board TOML.

TinyTapeout consumes Tier 1 output: clean, single-clock, synthesizable Verilog
sized to a tile.

## Boards (one flow, board as data)

A board is a `boards/<name>.toml` (device / family / clock / loader) plus a
`.cst` pin map. `ascon_boards/build.py` is the single driver: it emits a
target's RTL, then constructs the `yosys synth_gowin` -> `nextpnr` ->
`gowin_pack` -> `openFPGALoader` commands for any board, with `--dry-run` to
print them and knowledge of both the `nextpnr-gowin` and `nextpnr-himbaechel`
invocations. Adding a board is a data change, not a new Makefile.

The `perm_smoke` target is the concrete link between the generator and the
board: it emits a **generated** core plus a self-checking top that runs p12 on a
fixed vector and lights an LED iff the result matches the model's golden value
(embedded at generation time). It synthesizes with `synth_gowin` and fits the
Tang Nano 9K (R=1: ~4.1k LUTs / ~675 FF of the part's 8.6k / 6.5k).

## Benchmark decision

The claim the project defends is "an Ascon hardware accelerator is worth adding
to a system." The controlled experiment for that is the **same-fabric**
comparison: on one chip at one clock, NEORV32 running the C reference vs the
accelerator running Ascon in hardware, `hardware_cycles < software_cycles`. Same
process, same clock, same design context - the only variable is software-on-a-
soft-CPU vs the accelerator.

A host-CPU-vs-FPGA comparison is the wrong experiment for this claim, even if it
counts cycles rather than wall-clock. Counting cycles removes the clock-speed
penalty, but a laptop cycle and an accelerator cycle are incomparable units of
work (an out-of-order, ~4-8-wide x86 core with native 64-bit rotates does far
more per cycle), so the result is either a loss for an irrelevant reason or a win
for a trivial one. The legitimate cross-platform metric is **cycles-per-byte**
(the crypto-standard unit), which can be reported as *context* alongside the
headline same-fabric number - with the caveat that cpb across microarchitectures
reflects the whole package, not just the datapath.

Roles: the on-chip NEORV32 comparison is the headline benchmark; host-over-serial
is the interaction/demo path (it can read back the accelerator's internal cycle
counter for an honest hardware number without pretending wall-clock is the
architecture claim).

**What's implemented, and where verification lands.** The software baseline -
the portable C reference in `firmware/ascon_ref/` - is verified bit-exact against
the golden model via ctypes (`tests/test_reference_c.py`), so the benchmark's
"software" side is provably the same algorithm as NIST's. The accelerator driver
in `firmware/ascon_accel/` (the interact-via-C ABI, with MMIO / AXI-stream / DMA
transports) is verified natively end-to-end: `firmware/host/driver_selftest.c`
drives the real driver through a ref-emulator transport that models the hardware,
and checks the output against the reference in the same binary plus a full
encrypt->decrypt round trip (`tests/test_driver_selftest.py`). The on-chip
harness (`firmware/neorv32_ascon_benchmark/`) emits one machine-parsable `CASE`
line per payload; `host/ascon_bench.py` captures the UART stream and reduces it to
a SW-vs-HW table with the `hardware_cycles < software_cycles` verdict (parsing
verified in `tests/test_bench_host.py`). The one step that genuinely needs the
board or the vendor simulator - producing the hardware cycle counts - is the only
part not run in this repo's test suite; everything feeding it is verified here.
`make bench-native` runs the reference cross-check; `make bench` builds the
NEORV32 image; `make bench-host PORT=...` captures and reports.

## AXI-stream

The prof-assistant asked for AXI-stream on the deliverable build; the design
already uses it, and the framer enforces the AXI4-Stream contract (contiguous
`tkeep` from lane 0, only the final beat partial, `tlast` on the last beat,
byte-count match) with a clean `tready` that does not combinationally depend on
`tvalid`. That compliance is what matters, not whose library it came from. A
SystemVerilog-heavy library like `taxi` is a risk on the open Gowin/yosys flow
(SV interfaces usually need `sv2v`); `cocotbext-axi` is pure upside for
*verification* and the older Verilog-2001 `verilog-axis` FIFOs are yosys-safe if
stream FIFOs/width-converters are ever needed. The hand-rolled minimal interface
is appropriate for the tiny GW1NR-9 resource budget.
