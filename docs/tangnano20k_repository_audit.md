# Tang Nano 20K repository audit and operating procedure

## Executive assessment

The maintained hardware path is:

```text
boards/tangnano20k/neorv32_mmio/
```

It instantiates a 27 MHz NEORV32 RV32I SoC and an ASCON-AEAD128 accelerator in
the NEORV32 CFS window. The benchmark firmware runs the portable C reference and
the hardware path on the same CPU, verifies encryption/decryption results,
checks corrupted-tag rejection, and reports both CPU-visible end-to-end latency
and accelerator-internal latency.

The architecture is suitable for functional board validation and a fair
software-versus-accelerator comparison on the same embedded CPU. The primary
performance result is the **end-to-end speedup**. The core-only speedup is a
microarchitectural diagnostic and must not be presented as the practical
application speedup.

## Corrections applied by this audit

### Repository hygiene

Removed or prohibited:

- board-local `.venv-fpga` (machine-specific, approximately 650 MB);
- board-local duplicate `external/neorv32` checkout;
- a complete duplicate repository nested under `firmware/ascon_accel/`;
- precompiled headers, object files, backup files, stale UART logs, and failed
  report evidence;
- a 30 MB printer/PostScript artifact named `sys`;
- a generated 1.5 MB GHDL Verilog netlist;
- generated FPGA, firmware, simulator, and benchmark products.

Added:

- root `.gitignore` for reproducible dependencies and generated products;
- `tools/check_repository_hygiene.py`;
- `make repo-audit`, `make clean-repo-junk`, and `make distclean`.

### Reproducible NixOS environment

The development shell now:

- uses one root-local `.venv-fpga` regardless of the current subdirectory;
- materializes one pinned writable NEORV32 checkout at `external/neorv32`;
- leaves `NEORV32_HOME` unset globally so tests are isolated;
- creates each `riscv-none-elf-*` compatibility wrapper independently;
- installs pinned Apycula, YoWASP, NumPy, and pyserial versions;
- includes GHDL, Icarus Verilog, Verilator, openFPGALoader, and the RV32
  bare-metal toolchain.

### Tang Nano 20K build correctness

The board Makefile now:

- treats firmware as a hard dependency of synthesis, preventing stale embedded
  firmware and parallel-build races;
- uses `synth_gowin -family gw2a`;
- uses nextpnr device `GW2AR-LV18QN88C8/I7` and family `GW2A-18C`;
- emits a nextpnr timing/resource JSON report;
- uses 32 KiB IMEM and 8 KiB DMEM consistently in RTL and the linker contract;
- uses `openFPGALoader -f` only for persistent flash;
- has separate doctor, sanity, build, detect, SRAM, flash, capture, and report
  targets;
- has no obsolete UART bootloader upload step because firmware is embedded in
  pre-initialized IMEM (`BOOT_MODE_SELECT=2`).

### Benchmark integrity

The board firmware and tools now enforce:

- eight named payload/AD cases;
- software encryption/decryption correctness;
- accelerator encryption/decryption correctness;
- ciphertext, plaintext, and tag agreement;
- explicit corrupted-tag rejection;
- no plaintext output mutation on authentication failure;
- end-to-end CPU cycle measurements around the complete hardware-driver calls;
- accelerator-core busy-cycle measurements as a secondary diagnostic;
- capture completion only on a standalone final `PASS` or `FAIL`;
- strict report rejection for truncated, failed, or incomplete logs.

## Validation performed during this audit

The cleaned tree collects **422 pytest tests**. Because the audit container did
not include Icarus Verilog, the suite was executed in isolated groups to avoid
tool-runner time limits: **367 passed, 55 simulator-dependent tests skipped,
zero failed**. The focused Tang Nano 20K audit suite completed **32 passed**.

Additional checks completed:

- repository hygiene audit: pass;
- Python syntax compilation for capture, parser, and hygiene tools: pass;
- shell syntax check for `bringup.sh`: pass;
- host C syntax check for the benchmark firmware with warnings as errors: pass;
- patch dry-run against the uploaded repository: pass.

Native Nix evaluation, RV32 linking, GHDL synthesis, Yosys synthesis, nextpnr
place-and-route, packing, and physical board programming cannot be executed in
the audit container. They are deliberately part of the NixOS runbook below.
The development shell includes Icarus Verilog, so the simulator-dependent tests
should execute rather than skip on the target NixOS workstation.

## Repository policy

### Commit as source

Commit RTL, firmware source, tests, Makefiles, Nix files, documentation,
constraints, and small fixed test vectors.

### Do not commit

Do not commit:

```text
.venv-fpga/
external/neorv32/
build/
firmware/neorv32_ascon_benchmark/build/
*.o *.gch *.elf *.bin *.hex *.map
*.fs *.bit *.svf
*.vcd *.fst *.ghw
*.log
boards/tangnano20k/neorv32_mmio/uart_mmio.log
```

Benchmark reports should normally remain generated under `build/`. For a formal
release or paper artifact, copy a validated report and its raw UART log into a
versioned, dated release-evidence directory together with the Git commit hash,
Nix flake lock, and P&R report.

## First-time setup on NixOS

From the repository root:

```bash
nix develop
```

The first entry creates `.venv-fpga`, installs pinned Python FPGA packages, and
materializes the pinned NEORV32 tree. Later entries reuse both when their pinned
versions have not changed.

Verify the shell:

```bash
command -v ghdl
command -v iverilog
command -v yowasp-yosys
command -v yowasp-nextpnr-himbaechel-gowin
command -v gowin_pack
command -v openFPGALoader
command -v riscv-none-elf-gcc
command -v riscv-none-elf-readelf
python -c 'import apycula, numpy, serial; print("Python FPGA packages: OK")'
```

## Source sanity sequence

Run from the repository root inside `nix develop`:

```bash
make repo-audit
make test
make tn20k-doctor
make tn20k-sanity
```

Acceptance criteria:

- repository audit prints `Repository hygiene: PASS`;
- pytest completes with zero failures;
- simulator tests run rather than skip because Icarus Verilog is present;
- board doctor prints `Tang Nano 20K toolchain and dependency checks: PASS`;
- focused Tang Nano tests complete with zero failures.

## Clean build and timing review

Perform a clean build:

```bash
make clean-board
make tn20k-rebuild
```

Equivalent direct board command:

```bash
make -C boards/tangnano20k/neorv32_mmio rebuild
```

Expected generated artifacts:

```text
build/neorv32_mmio_20k/tangnano20k_neorv32_mmio_top.fs
build/neorv32_mmio_20k/tangnano20k_neorv32_mmio_top_pnr_report.json
firmware/neorv32_ascon_benchmark/build/main.elf
```

Inspect firmware size:

```bash
riscv-none-elf-size firmware/neorv32_ascon_benchmark/build/main.elf
riscv-none-elf-readelf -h -S firmware/neorv32_ascon_benchmark/build/main.elf | less
```

Inspect the P&R report:

```bash
python -m json.tool \
  build/neorv32_mmio_20k/tangnano20k_neorv32_mmio_top_pnr_report.json | less
```

The build must complete without timing failure at 27 MHz. Keep the JSON report
with any benchmark evidence used for publication.

## Board detection and volatile SRAM test

Close all serial monitors before programming. Then:

```bash
make tn20k-detect
make tn20k-prog-sram
```

Equivalent direct commands:

```bash
openFPGALoader -b tangnano20k --detect
openFPGALoader -b tangnano20k \
  build/neorv32_mmio_20k/tangnano20k_neorv32_mmio_top.fs
```

SRAM programming is the mandatory validation stage because it is reversible.
Do not write persistent flash until the complete benchmark passes.

## Complete UART benchmark

Find the stable serial path:

```bash
ls -l /dev/serial/by-id/
```

Capture a complete run:

```bash
make tn20k-capture \
  SERIAL=/dev/serial/by-id/usb-SIPEED_USB_Debugger_<id>-if01-port0
```

The capture utility clears stale input and prompts for a board reset. Press
**S1/KEY1 once** after the port opens. It exits automatically only after the
firmware emits a standalone final `PASS` or `FAIL`, or after the timeout.

If the board is slower to start or the serial path is unusual:

```bash
make tn20k-capture \
  SERIAL=/dev/serial/by-id/<device> \
  UART_TIMEOUT=120
```

The successful raw log contains:

```text
BUILD        : tangnano20k-neorv32-mmio
SWEEP_CASES  : 8
CASE name=empty ...
CASE name=ad8 ...
CASE name=pt8 ...
CASE name=ad8_pt8 ...
CASE name=pt16 ...
CASE name=pt24 ...
CASE name=pt32 ...
CASE name=ad16_pt32 ...
AUTH_NEGATIVE ... pass=1
SUMMARY      : passed=8 failed=0 total=8 negative_pass=1
PASS
```

Quickly inspect the evidence before reporting:

```bash
grep -aE '^(BUILD|CASE|AUTH_NEGATIVE|SUMMARY|PASS|FAIL)' \
  boards/tangnano20k/neorv32_mmio/uart_mmio.log

grep -a '^CASE ' boards/tangnano20k/neorv32_mmio/uart_mmio.log | wc -l
```

The count must be `8`.

## Generate the benchmark reports

```bash
make tn20k-report
```

This strict target writes:

```text
build/neorv32_mmio_20k/uart_report.md
build/neorv32_mmio_20k/uart_report.csv
build/neorv32_mmio_20k/uart_report.json
```

Read the human report:

```bash
cat build/neorv32_mmio_20k/uart_report.md
```

The report refuses incomplete captures, failed functional checks, a missing
negative-authentication test, a failed summary, or a missing final `PASS`.

## Persistent flash

Only after SRAM programming and the strict report both pass:

```bash
make tn20k-prog-flash
```

This rebuilds if necessary and runs openFPGALoader with `-f` for external flash.

## One-command professional bring-up

Inside `nix develop`:

```bash
SERIAL=/dev/serial/by-id/<device> ./bringup.sh
```

This runs the repository audit, full tests, board doctor, clean build, detection,
SRAM programming, complete UART capture, and strict report generation.

To flash only after all earlier stages pass:

```bash
SERIAL=/dev/serial/by-id/<device> ./bringup.sh --flash
```

## Performance interpretation

For each operation:

```text
practical speedup = software cycles / hardware end-to-end cycles
core-only speedup = software cycles / accelerator busy cycles
```

Use practical/end-to-end speedup in the primary results table. It includes MMIO
writes, polling, accelerator execution, and result reads as observed by the
NEORV32 CPU. Label the baseline precisely as **27 MHz NEORV32 RV32I portable C**;
it is not a desktop x86/ARM CPU comparison.

For payload throughput studies, the present 0–32 byte sweep is a latency-oriented
bring-up benchmark. A publication-quality throughput claim should add larger
payloads and/or a streaming/DMA target so fixed MMIO overhead is amortized.

## Maintenance commands

Remove generated board products but preserve the environment and dependencies:

```bash
make clean-board
```

Remove all generated products and known accidental repository debris:

```bash
make clean
make clean-repo-junk
```

Remove reproducible local dependencies as well:

```bash
make distclean
```

Restore them later with:

```bash
nix develop
```

Before every commit:

```bash
make repo-audit
git status --short
git diff --check
```

A clean source commit should not contain machine-local paths, local virtual
environments, copied third-party source trees, bitstreams, UART logs, or build
reports.
