#!/usr/bin/env bash
# Reproducible Tang Nano 20K build, SRAM test, and benchmark workflow.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

skip_tests=0
flash=0
for arg in "$@"; do
  case "$arg" in
    --skip-tests) skip_tests=1 ;;
    --flash) flash=1 ;;
    -h|--help)
      cat <<'EOF'
Usage: ./bringup.sh [--skip-tests] [--flash]

Environment:
  SERIAL=/dev/serial/by-id/...   optional; auto-detected when unambiguous
  UART_TIMEOUT=60                UART capture timeout in seconds

Run this script inside `nix develop`. It programs SRAM first, captures a strict
benchmark PASS, generates reports, and writes flash only when --flash is given.
EOF
      exit 0
      ;;
    *) echo "error: unknown argument: $arg" >&2; exit 2 ;;
  esac
done

for tool in python make ghdl yowasp-yosys yowasp-nextpnr-himbaechel-gowin gowin_pack openFPGALoader riscv-none-elf-gcc; do
  command -v "$tool" >/dev/null || {
    echo "error: missing $tool; run 'nix develop' from the repository first" >&2
    exit 2
  }
done

make repo-audit
if [[ "$skip_tests" -eq 0 ]]; then
  make test
fi
make tn20k-doctor
make tn20k-rebuild
make tn20k-detect
make tn20k-prog-sram

if [[ -n "${SERIAL:-}" ]]; then
  make tn20k-capture SERIAL="$SERIAL"
else
  make tn20k-capture
fi
make tn20k-report

if [[ "$flash" -eq 1 ]]; then
  make tn20k-prog-flash
fi

echo
printf 'Validated report: %s\n' "build/neorv32_mmio_20k/uart_report.md"
printf 'Bitstream:       %s\n' "build/neorv32_mmio_20k/tangnano20k_neorv32_mmio_top.fs"
