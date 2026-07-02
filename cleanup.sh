#!/usr/bin/env bash
# One-time repo cleanup: removes confirmed build artifacts and an accidental
# nested copy of the whole repo that ended up inside firmware/ascon_accel/.
#
# Safe to re-run. Use --dry-run first to see exactly what would be removed.
#
# Usage:
#   ./cleanup.sh --dry-run
#   ./cleanup.sh

set -euo pipefail
cd "$(dirname "$0")"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

rm_path() {
  local path="$1"
  if [[ -e "$path" ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "would remove: $path"
    else
      rm -rf -- "$path"
      echo "removed:      $path"
    fi
  fi
}

echo "== stray build artifacts at repo root =="
rm_path "ascon_accel.o"
rm_path "main_demo.o"
rm_path "uart.log"
rm_path "cosim_report.md"

echo
echo "== stray/garbage files under boards/tangnano9k =="
rm_path "boards/tangnano9k/neorv32_stream_axis_mmio/sys"     # 30MB, actually a PostScript file
rm_path "boards/tangnano9k/neorv32_stream_axis_mmio/readme"  # empty scratch note
rm_path "boards/tangnano9k/neorv32_stream_axis_mmio/real"    # empty
rm_path "boards/tangnano9k/neorv32_stream_axis_mmio/0.8"     # empty

echo
echo "== precompiled headers (regenerated on build) =="
for f in firmware/ascon_accel/*.h.gch; do
  rm_path "$f"
done

echo
echo "== accidental full repo copy nested inside firmware/ascon_accel/ =="
echo "   (firmware/ascon_accel/Makefile is a byte-for-byte copy of the"
echo "    top-level Makefile; the real driver files stay untouched)"
for d in ascon_arch ascon_hwmodel boards configs benchmarks docs firmware tests tools rtl vectors; do
  rm_path "firmware/ascon_accel/$d"
done

echo
echo "== sandbox/patch leftovers =="
echo "   Review before deleting -- if you still need this patch, apply it"
echo "   to boards/tangnano9k/*/Makefile first, then remove the folder:"
echo "     patch -p1 < mnt/data/tangnano9k_makefiles_nix_tools.patch"
rm_path "mnt"

echo
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run complete. Re-run without --dry-run to actually delete."
else
  echo "Cleanup complete."
fi
