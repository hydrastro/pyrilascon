#!/usr/bin/env bash
# Tang Nano 9K + NEORV32 + ASCON-MMIO bring-up — NixOS / nix develop edition
# Run from the repo root, inside `nix develop`.

set -euo pipefail
cd "$(dirname "$0")"

# ── Defaults tuned for your Nix devShell ────────────────────────────────────
RISCV_PREFIX="${RISCV_PREFIX:-riscv-none-elf-}"
# `-if01-port0` is the data UART on the Tang Nano 9K (BL702 USB-UART).
# `-if00-port0` is the JTAG channel that openFPGALoader uses for programming.
SERIAL="${SERIAL:-/dev/serial/by-id/usb-SIPEED_JTAG_Debugger_SIPEED-if01-port0}"
BAUD="${BAUD:-19200}"
PROFILE="${NEORV32_FW_PROFILE:-auto}"

# ── Step 0: prereqs ─────────────────────────────────────────────────────────
echo "==> Checking host tools"
miss=0
need() { command -v "$1" >/dev/null 2>&1 || { echo "  MISS $1${2:+ ($2)}"; miss=1; }; }
need "${RISCV_PREFIX}gcc"     "nix devShell pkgsCross.riscv32-embedded.buildPackages.gcc + wrappers"
need yowasp-yosys             "pip install yowasp-yosys (in .venv-fpga)"
need yowasp-nextpnr-himbaechel-gowin "pip install yowasp-nextpnr-himbaechel-gowin (in .venv-fpga)"
need gowin_pack               "comes from yowasp; or add apicula"
need openFPGALoader           "nixpkgs openfpgaloader"
need picocom                  "nixpkgs picocom"
need ghdl                     "add 'ghdl' to flake.nix devShell packages"
if [ "$miss" = 1 ]; then
  echo ""
  echo "Some tools are missing. If 'ghdl' is the only one missing,"
  echo "add it to flake.nix and re-enter the shell:"
  echo ""
  echo "  packages = with pkgs; [ ... ghdl ... ];"
  exit 2
fi
echo "  all tools OK"

# ── Step 1: pre-board sanity (15 sec total) ─────────────────────────────────
echo ""
echo "==> Pre-board: pytest"
PYTHONPATH=. pytest -q tests

echo ""
echo "==> Pre-board: host C-firmware vs Python golden model"
PYTHONPATH=. python tools/run_firmware_stream_ref_benchmark.py

# ── Step 2: probe firmware toolchain profile that actually links ────────────
echo ""
echo "==> Probing usable firmware toolchain profile (this resolves which"
echo "    march/mabi nix's riscv-none-elf-gcc + bundled newlib can link)"
PYTHONPATH=. python tools/check_neorv32_toolchain.py \
  --prefix "$RISCV_PREFIX" --profile "$PROFILE" --check

# ── Step 3: bitstream ───────────────────────────────────────────────────────
echo ""
echo "==> Synth + PnR + pack (this can take 5–10 min on yowasp WASM)"
make -C boards/tangnano9k/neorv32_mmio tools  NEORV32_FW_PROFILE="$PROFILE"
make -C boards/tangnano9k/neorv32_mmio bitstream RISCV_PREFIX="$RISCV_PREFIX" NEORV32_FW_PROFILE="$PROFILE"

# ── Step 4: program FPGA SRAM (volatile — survives until power off) ─────────
echo ""
echo "==> Programming Tang Nano 9K SRAM"
echo "    If openFPGALoader can't reach the device, you may need:"
echo "      sudo make -C boards/tangnano9k/neorv32_mmio prog-sram"
echo "    or a udev rule for the Sipeed JTAG (60-openfpgaloader.rules)."
make -C boards/tangnano9k/neorv32_mmio prog-sram

# ── Step 5: firmware ────────────────────────────────────────────────────────
echo ""
echo "==> Building firmware"
make -C boards/tangnano9k/neorv32_mmio firmware RISCV_PREFIX="$RISCV_PREFIX" NEORV32_FW_PROFILE="$PROFILE"

# ── Step 6: upload firmware via the NEORV32 UART bootloader ─────────────────
# After bitstream programming, NEORV32 boots into its bootloader and listens
# on UART at 19200 8N1. The upload script sends 'u' then the .bin and runs it.
echo ""
echo "==> Uploading neorv32_exe.bin to NEORV32 via $SERIAL"
make -C boards/tangnano9k/neorv32_mmio upload \
  RISCV_PREFIX="$RISCV_PREFIX" \
  NEORV32_FW_PROFILE="$PROFILE" \
  SERIAL="$SERIAL"

# ── Step 7: capture the benchmark log ───────────────────────────────────────
# The firmware prints results then idles. Capture for ~12 seconds.
echo ""
echo "==> Capturing UART for 12 s into uart_mmio.log"
( make -C boards/tangnano9k/neorv32_mmio uart-capture \
    SERIAL="$SERIAL" BAUD="$BAUD" LOG=uart_mmio.log ) &
CAP=$!
sleep 12
kill "$CAP" 2>/dev/null || true
wait "$CAP" 2>/dev/null || true

# ── Step 8: parse log → structured report ───────────────────────────────────
echo ""
echo "==> Parsing UART log into report"
make -C boards/tangnano9k/neorv32_mmio uart-report LOG=uart_mmio.log

echo ""
echo "DONE."
echo ""
echo "Compare HW vs SW (C golden) cycles in:"
echo "  build/neorv32_mmio/uart_report.md"
echo "  build/neorv32_mmio/uart_report.json"
echo "Raw UART text: boards/tangnano9k/neorv32_mmio/uart_mmio.log"
