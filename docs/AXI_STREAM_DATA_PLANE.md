# The AXI-Stream data plane

## What was wrong

The accelerator's engine, `ascon_aead128_axis`, was always AXI4-Stream native —
real `s_tdata/s_tkeep/s_tuser/s_tlast/s_tvalid/s_tready` in, `m_tdata/...` out.
The problem was one line in the MMIO wrapper:

```verilog
wire s_tvalid = din_ctl_wr;   // a stream beat fires when the CPU writes a register
```

A streaming datapath, driven by a CPU store instruction. The stream can accept a
beat every cycle; the CPU delivered one every ~400. Measurement said the
accelerator spent **97.8% of its busy time waiting**, and that a permutation 8×
faster would buy **+0.2×**.

## What was built

```
DMEM ──▶ DMA ──▶ SLINK TX FIFO ──▶ s_axis ──▶ Ascon ──▶ m_axis ──▶ SLINK RX FIFO ──▶ DMA ──▶ DMEM
```

The CPU writes key/nonce/lengths/START over XBUS, programs a DMA descriptor, and
waits. **It never touches a payload byte.**

Three things made this a small amount of glue rather than a new bus:

1. **NEORV32's SLINK is AXI4-Stream** — 32-bit data, valid/ready/last. It maps
   1:1 onto the engine's ports, and the width matches exactly.
2. **NEORV32's DMA supports a constant destination address**
   (descriptor bit `conf_dst_hi_c = 0`), so it can read incrementing from memory
   and write repeatedly to the single SLINK TX register.
3. **SLINK's TLAST is chosen by the write address** (`+0x8` = last 0, `+0xC` =
   last 1), so it costs no sideband.

### The one real design problem

SLINK cannot carry the engine's `tuser` (associated data vs message) or `tkeep`
(byte mask) per beat. Its routing field is set once per transfer by a register,
so a DMA cannot vary it beat by beat.

`ascon_slink_shim` solves this by **deriving** tuser/tkeep/tlast from the
`AD_LEN`/`TEXT_LEN` control registers plus a byte counter. The consequence is the
point: the payload becomes a plain, unadorned word stream — exactly what a DMA
can produce unaided. The shim also synthesises the zero-length terminating beat
that an empty message needs, consuming no SLINK word.

## Results — measured, not estimated

Simulated with the stream fed as fast as the shim accepts (what a DMA does).
The SW column is the board-measured reference-C baseline; MMIO is the
board-measured accelerator.

| Case | SW | MMIO busy | **SLINK busy** | crypto | MMIO × | **SLINK ×** | gain |
|---|---|---|---|---|---|---|---|
| empty | 38 866 | 684 | **41** | 36 | 56.8× | **948×** | 16.7× |
| ad8 | 50 205 | 1 335 | **55** | 47 | 37.6× | **913×** | 24.3× |
| pt8 | 39 458 | 1 239 | **45** | 36 | 31.8× | **877×** | 27.5× |
| ad8_pt8 | 50 797 | 1 890 | **60** | 47 | 26.9× | **847×** | 31.5× |
| pt16 | 52 156 | 2 007 | **63** | 48 | 26.0× | **828×** | 31.9× |
| pt24 | 52 748 | 2 763 | **69** | 48 | 19.1× | **764×** | 40.0× |
| pt32 | 65 447 | 3 531 | **87** | 60 | 18.5× | **752×** | 40.6× |
| ad16_pt32 | 86 984 | 4 948 | **118** | 83 | 17.6× | **737×** | 41.9× |

**The design flipped from interface-bound to compute-bound:**

| | crypto share of busy time | interface overhead |
|---|---|---|
| MMIO | 2.2 % | 97.8 % |
| **SLINK** | **75.3 %** | **24.7 %** |

### And now the design space pays off

On the MMIO plane, a faster permutation was worth +0.2×. On the SLINK plane it is
worth 500×. Same AEAD core, same model, only the permutation swapped
(`emit_iterative_permutation(N, module_name="ascon_perm_iter_r1")` — the
interface is identical, so it is a drop-in):

| Permutation | busy cycles | speed-up | correct |
|---|---|---|---|
| 1 round/cycle | 118 | 737× | tag_ok |
| 2 rounds/cycle | 90 | 966× | tag_ok |
| 4 rounds/cycle | 76 | 1145× | tag_ok |
| 8 rounds/cycle | 70 | **1243×** | tag_ok |

The design-space exploration wasn't wasted — it was **blocked by the data plane**.
Fixing the interface is what makes those seven architectures worth having.

## What is verified, and what is not

**Verified here, in simulation, against the golden model:**

- `ascon_slink_shim` + `ascon_aead128_slink_mmio` + the engine: **24 cases**
  (12 payload shapes × encrypt/decrypt), including empty AD, empty message,
  partial words, and full rate blocks. Expected values come from
  `ascon_hwmodel`, which passes the official NIST KATs — never from the RTL.
- Guarded by `tests/test_slink_plane_sim.py`; the suite is now **119 passed, 1 skipped**.
- The permutation sweep above: all four architectures produce the correct tag.
- The C driver compiles clean under `-Wall -Wextra`.

**NOT verified — needs your machine:**

- **`neorv32_ascon_slink_soc.vhd` has never been elaborated.** No GHDL here.
  Run `make soc-check` first.
- **It has never been fitted.** This is the live risk: the MMIO SoC already
  needed `RISCV_ISA_M => false` to fit the GW2AR-18, and this adds SLINK **and**
  DMA. It may not fit. If it doesn't, the honest options are a smaller
  `IMEM_SIZE`, a shallower descriptor FIFO, or a bigger FPGA — and note that
  "a bigger FPGA would help" is *true here* in a way it was never true for the
  MMIO design.
- **The driver has never run on hardware.** The DMA timing, the descriptor
  programming, and the RX read-back are all board-side unknowns.
- The wall-clock speed-up. The busy-cycle numbers above are the same metric the
  project already reports, and are honest as such — but the DMA setup cost is
  real and is not in them.

## FIFO sizing — a real constraint, not a detail

NEORV32's SLINK **does not back-pressure bus writes**: a write to a full TX FIFO
is lost. So an unthrottled DMA is only safe if the TX FIFO is at least as deep as
the largest payload in words: 32 B AD + 32 B message = **16 words**. The SoC sets
`IO_SLINK_TX_FIFO => 16` for exactly that reason.

The RX FIFO has the mirror-image constraint: the engine back-pressures in its TX
state until SLINK accepts each beat, so if the RX FIFO cannot hold a whole result
(MSG_MAX/4 = 8 words) the engine stalls before it can raise `done` — a deadlock.
`IO_SLINK_RX_FIFO => 16` gives headroom.

**Raising AD_MAX/MSG_MAX means raising the FIFOs too, or chunking the DMA.**
This is the thing most likely to bite whoever extends this to real streaming.

## How to build it

The proven MMIO SoC is untouched. This is a separate top.

```bash
nix develop .#soc

# 1. elaborate first -- fast, and catches VHDL errors before a 30-minute fit
NEORV32_HOME=$NEORV32_HOME ./rtl/soc/build_soc.sh --check-only   # adapt for the new top

# 2. build the bitstream (edit build_soc.sh's top name, or copy it)
#    top: neorv32_ascon_slink_soc
#    sources: rtl/soc/neorv32_ascon_slink_soc.vhd
#             rtl/soc/ascon_aead128_slink_wb.v
#             rtl/soc/ascon_aead128_slink_mmio.v
#             rtl/soc/ascon_slink_shim.v
#             rtl/generated/accel/*.v  (make accel-rtl)

# 3. flash to SRAM first (temporary -- your proven SoC returns on power-cycle)
openFPGALoader -b tangnano20k build/soc/neorv32_ascon_slink_soc.fs
```

**Flash to SRAM (no `-f`) the first time.** If the stream SoC misbehaves, a
power-cycle brings back the SPI-flashed MMIO SoC that is known to work.

Software identifies the build at runtime: `CAPABILITIES` bit 23
(`ASCON_SLINK_CAP_SLINK_PLANE`) is set only by this SoC, so
`CAPS = 0x00E00001` instead of `0x00600001`.

## Files

| File | What | Status |
|---|---|---|
| `rtl/soc/ascon_slink_shim.v` | SLINK word stream → tagged AXI4-Stream | verified vs model |
| `rtl/soc/ascon_aead128_slink_mmio.v` | control registers + shim + engine | verified vs model |
| `rtl/soc/ascon_aead128_slink_wb.v` | XBUS adapter (same handshake as the proven one) | verified by construction |
| `rtl/soc/neorv32_ascon_slink_soc.vhd` | SoC top: SLINK + DMA enabled | **not elaborated** |
| `firmware/ascon_slink/ascon_slink.{c,h}` | DMA-driven driver | compiles clean, **not run** |
| `tools/verify_slink_plane.py` | the RTL-vs-model harness | passing |
| `tests/test_slink_plane_sim.py` | suite integration | passing |
