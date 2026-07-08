# Ascon AXI-Stream accelerator on NEORV32 / Tang Nano 20K

Run the generated Ascon-AEAD128 accelerator as a memory-mapped peripheral on a
[NEORV32](https://github.com/stnolting/neorv32) soft core on the Tang Nano 20K,
and benchmark hardware-vs-software with the firmware in this repo - via a
**fully-open toolchain** (GHDL + Yosys + nextpnr + Project Apicula).

## What is verified, and where

**Verified in CI (against the NIST-verified model):**

* `ascon_aead128_axis` - the AXI-Stream AEAD128 engine.
* `ascon_aead128_axis_mmio` - the driver-compatible MMIO peripheral, driven
  through the firmware driver's exact register protocol (encrypt, decrypt
  round-trip, tag rejection). `make test` runs both.

**Verified to build (elaborate + link) in the open flow:**

* The whole `neorv32_ascon_soc` - NEORV32 CPU + the Ascon accelerator on XBUS -
  analyzed by GHDL and linked in Yosys (mixed VHDL/Verilog), `hierarchy -check`
  clean. Reproduce with `make soc-check` (see below).

**Board-side (your hardware, not reproducible in CI):**

* `synth_gowin` to completion, nextpnr place-and-route, `gowin_pack`, flashing,
  and the on-chip run. The crypto datapath and the SoC wiring are verified; PnR
  timing/fit and the firmware base address are yours to close.

## 1. Toolchain

Everything is pinned by the flake. NEORV32 is a `flake = false` input exported as
`$NEORV32_HOME` - no manual clone.

* **`nix develop`** - the verified flows: model, generator, RTL sim, C, the
  Verilog `perm_smoke` board flow, and `ghdl` for VHDL linting. Always builds.

* **VHDL synthesis for the SoC** needs yosys **with the GHDL plugin**. nixpkgs'
  yosys has no built-in plugin, and building the standalone plugin against
  nixpkgs' `ghdl` is unreliable - nixpkgs tracks a *dev* ghdl (e.g. 6.0.0) that is
  frequently ahead of the plugin's API, so the plugin fails to compile. The
  robust, matched toolchain is **YosysHQ oss-cad-suite**, which ships yosys +
  ghdl + the plugin (plus nextpnr-himbaechel and gowin_pack) already consistent:

  ```sh
  # one-time: grab a release for your platform, extract it
  #   https://github.com/YosysHQ/oss-cad-suite-build/releases
  source /path/to/oss-cad-suite/environment
  ```

  `nix develop .#soc` sets `$NEORV32_HOME` + `$GHDL_PREFIX` and prints this; from
  there just `source` oss-cad-suite and run the SoC targets. `build_soc.sh`
  auto-detects the plugin (`yosys-ghdl` wrapper or `yosys -m ghdl`).

## 2. Emit the accelerator RTL

```sh
make accel-rtl        # writes rtl/generated/accel/*.v (+ model include files)
```

`ascon_perm_iter_r1.v`, `ascon_aead128_core.v`, `ascon_aead128_axis.v`,
`ascon_aead128_axis_mmio.v`. The Wishbone adapter `rtl/soc/ascon_aead128_wb.v`
instantiates `ascon_aead128_axis_mmio`; the SoC top `rtl/soc/neorv32_ascon_soc.vhd`
wires that onto NEORV32's XBUS.

## 3. Build the SoC (fully open)

```sh
nix develop .#soc                          # sets NEORV32_HOME + GHDL_PREFIX, prints guidance
source /path/to/oss-cad-suite/environment  # yosys + ghdl + plugin + nextpnr + gowin_pack
make soc-check                             # elaborate + link NEORV32 + accelerator (fast, CI-verified)
make soc-build                             # full: emit -> ghdl -> yosys -> nextpnr -> gowin_pack
```

(You can also run the whole SoC build from just `nix develop` + oss-cad-suite -
`.#soc` only adds the `GHDL_PREFIX` export and the reminder. If `build_soc.sh`
can't find a GHDL-capable yosys it prints exactly how to source oss-cad-suite.)

`build_soc.sh` (what those targets call) does, in order:

1. `make accel-rtl`.
2. `ghdl -a --std=08 --work=neorv32 …` - analyze all of `$NEORV32_HOME/rtl/file_list_soc.f`
   into a library named `neorv32` (NEORV32's VHDL does `library neorv32;` - this
   `--work=neorv32` is the step a bare `ghdl -a` misses), then analyze the SoC top.
3. `yosys-ghdl -p 'ghdl … neorv32_ascon_soc; read_verilog … accel/*.v; synth_gowin …'`
   - GHDL imports the VHDL (NEORV32 + top), `read_verilog` supplies the Verilog
   accelerator, Yosys links them and maps to Gowin. `GHDL_PREFIX` is auto-detected
   from `ghdl --disp-config` (the plugin needs GHDL's library path at runtime).
4. `nextpnr-himbaechel --device GW2AR-LV18QN88C8/I7 --vopt family=GW2A-18C
   --vopt cst=boards/tangnano20k/neorv32_soc.cst`, then `gowin_pack -d GW2A-18C`.

Constraints are in `boards/tangnano20k/neorv32_soc.cst` (clock pin 4 @ 27 MHz,
LEDs 15-20; **verify the UART pins to the onboard BL616 against your board's
schematic** - they vary by revision).

## 4. Firmware

The benchmark is in `firmware/neorv32_ascon_benchmark/`, the driver in
`firmware/ascon_accel/`. The accelerator's base address defaults to
`ASCON_ACCEL_BASE_ADDR = 0x90000000` - an address NEORV32 routes to XBUS (outside
IMEM `0x0…`, DMEM `0x80000000`, and the internal IO region `0xFFE00000+`). The
default benchmark uses the register-based `MMIO_WORD` data plane, which is exactly
the register protocol the accelerator implements (and the one verified in CI), so
no code change is needed:

```sh
nix develop                                 # $NEORV32_HOME is set
make -C firmware/neorv32_ascon_benchmark    # links against $NEORV32_HOME/sw + this driver
```

It emits machine-parsable `CASE …` lines over UART0 with software and hardware
cycle counts per payload. The accelerator also exposes a start-to-done cycle
counter (`CYCLE_COUNT_LO/HI`) for a pure-hardware latency number.

> If you change the SoC's XBUS decode or map the peripheral elsewhere, override
> with `-DASCON_ACCEL_BASE_ADDR=0x…`. Do **not** use an address in `0xFFE00000+`
> - that is NEORV32's internal IO region and never reaches XBUS.

## 5. Flash + benchmark

```sh
openFPGALoader -b tangnano20k build/soc/neorv32_ascon_soc.fs
python host/ascon_bench.py capture --port /dev/ttyUSB0 --out run.log
python host/ascon_bench.py report run.log            # SW-vs-HW table + verdict
```

**Flashing on NixOS.** The 20K's onboard debugger enumerates as an FTDI
`0403:6010` (FT2232). openFPGALoader needs udev access:

* `openFPGALoader: unable to open ftdi device: -3 (device not found)` means the
  board isn't seen at the USB level. Check `lsusb | grep 0403` - if nothing shows,
  it's the cable (use a *data* cable, not power-only), the port, or power; if it
  shows but flashing still fails, it's permissions.
* Permanent fix - in `configuration.nix`:

  ```nix
  services.udev.packages = [ pkgs.openfpgaloader ];   # installs its uaccess rules
  ```

  then `sudo nixos-rebuild switch` and replug. Quick test without that:
  `sudo openFPGALoader -b tangnano20k build/soc/neorv32_ascon_soc.fs` (if sudo
  works, it was udev). `openFPGALoader --detect -b tangnano20k` verifies the JTAG
  chain once access works.

`host/ascon_bench.py` reduces the `CASE` lines to the same-fabric
hardware-vs-software cycle comparison (its parsing is unit-tested; only the cycle
numbers come from the board).

## Notes

* The accelerator is bounded to 32 B AD + 32 B message per call (the generated
  core's buffers); the benchmark payloads fit. Arbitrary-length streaming through
  the rate blocks would be a new generator target.
* The Wishbone adapter is standard single-cycle classic Wishbone (`ack = access &
  ready`); the peripheral inserts wait states only while streaming input, covered
  by the `ready`/`ack` handshake. For NEORV32 XBUS in *pipelined* mode, register
  `wb_ack_o` by one cycle.
* Not using Nix? NEORV32 can instead be a git submodule
  (`git submodule add https://github.com/stnolting/neorv32 vendor/neorv32`); set
  `NEORV32_HOME=vendor/neorv32`. You still need a yosys with the GHDL plugin
  (oss-cad-suite is simplest).
