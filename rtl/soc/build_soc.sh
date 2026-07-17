#!/usr/bin/env bash
# Build the NEORV32 + Ascon-AEAD128 accelerator SoC for the Tang Nano 20K, fully
# open: ghdl (VHDL) + yosys-with-GHDL-plugin (mixed VHDL/Verilog) +
# nextpnr-himbaechel + gowin_pack.
#
#   NEORV32_HOME=... ./rtl/soc/build_soc.sh              # full bitstream
#   NEORV32_HOME=... ./rtl/soc/build_soc.sh --check-only # elaborate + link only (fast)
#
# In `nix develop .#soc` the yosys+plugin command is `yosys-ghdl`; with YosysHQ
# oss-cad-suite the plugin is in-tree so plain `yosys -m ghdl` is used. Both are
# auto-detected. The elaborate+link step is CI-verified; synth/PnR/pack need the
# Gowin tools on PATH.
set -euo pipefail

CHECK_ONLY=0
[ "${1:-}" = "--check-only" ] && CHECK_ONLY=1

: "${NEORV32_HOME:?set NEORV32_HOME to the NEORV32 source (the flake exports it)}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# Which SoC to build. Defaults reproduce the silicon-validated MMIO SoC exactly;
# the stream variant is selected by overriding these (see `make soc-build-slink`).
SOC_TOP="${SOC_TOP:-neorv32_ascon_soc}"
SOC_VHD="${SOC_VHD:-$ROOT/rtl/soc/neorv32_ascon_soc.vhd}"
SOC_V="${SOC_V:-$ROOT/rtl/soc/ascon_aead128_wb.v}"
# Separate build dir per variant, so a stream build never clobbers the bitstream
# that is known to work.
if [ "$SOC_TOP" = "neorv32_ascon_soc" ]; then
  BUILD="${BUILD:-$ROOT/build/soc}"
else
  BUILD="${BUILD:-$ROOT/build/soc-$SOC_TOP}"
fi
mkdir -p "$BUILD"

# yosys with the GHDL plugin, detected in priority order:
#   1. a `yosys-ghdl` wrapper on PATH
#   2. plain `yosys` with the plugin preloaded (nixpkgs `yosys.withPlugins`) - no -m
#   3. `yosys -m ghdl` (oss-cad-suite ships the plugin in-tree)
# `help ghdl` prints "No such command" when the plugin is absent; the exit code is
# unreliable, so we inspect the output (captured first, to stay pipefail-safe).
ghdl_ok() {
  local out
  out="$("$@" -p 'help ghdl' 2>&1 || true)"
  ! printf '%s' "$out" | grep -qi 'no such'
}
if command -v yosys-ghdl >/dev/null 2>&1; then
  YOSYS=(yosys-ghdl)
elif ghdl_ok yosys; then
  YOSYS=(yosys)
elif ghdl_ok yosys -m ghdl; then
  YOSYS=(yosys -m ghdl)
else
  cat >&2 <<'MSG'
ERROR: no yosys with the GHDL plugin was found.

  The NEORV32 SoC is VHDL, so its synthesis needs yosys + the GHDL plugin.
  Two ways to get one:

  * nix: `nix develop .#soc` - uses the nixpkgs-matched GHDL plugin if your
    channel has it (the shell tells you which case you are in).
  * oss-cad-suite (yosys + ghdl + plugin, all matched):
      # download + extract from
      #   https://github.com/YosysHQ/oss-cad-suite-build/releases
      source /path/to/oss-cad-suite/environment
      make soc-build

  The Verilog perm_smoke flow and everything else still work without it.
MSG
  exit 1
fi
# The plugin needs GHDL's library prefix at runtime (mcode/gcc/llvm layouts differ).
export GHDL_PREFIX="${GHDL_PREFIX:-$(ghdl --disp-config 2>/dev/null | sed -n 's/.*library directory: //p' | head -1)}"
echo "NEORV32_HOME=$NEORV32_HOME"
echo "GHDL_PREFIX=$GHDL_PREFIX"
echo "yosys: ${YOSYS[*]}"

echo "== 1/4 emit accelerator datapath =="
( cd "$ROOT" && make accel-rtl >/dev/null )

echo "== 2/4 analyze NEORV32 (into 'neorv32' lib) + SoC top =="
FILES=$(sed "s#\$NEORV32_HOME#$NEORV32_HOME#g" "$NEORV32_HOME/rtl/file_list_soc.f")
ghdl -a --std=08 --work=neorv32 --workdir="$BUILD" $FILES
ghdl -a --std=08 --workdir="$BUILD" -P"$BUILD" "$SOC_VHD"

RD="read_verilog -I$ROOT/rtl/generated $SOC_V $ROOT/rtl/generated/accel/*.v"

if [ "$CHECK_ONLY" = 1 ]; then
  echo "== 3/3 elaborate + link (hierarchy -check), no synthesis =="
  "${YOSYS[@]}" -p "
    ghdl --std=08 --workdir=$BUILD -P$BUILD $SOC_TOP;
    $RD;
    hierarchy -check -top $SOC_TOP;
    stat -top $SOC_TOP"
  echo "OK: $SOC_TOP elaborates and links."
  exit 0
fi

echo "== 3/4 synthesize (mixed VHDL+Verilog) -> Gowin JSON =="
"${YOSYS[@]}" -p "
  ghdl --std=08 --workdir=$BUILD -P$BUILD $SOC_TOP;
  $RD;
  synth_gowin -top $SOC_TOP -json $BUILD/$SOC_TOP.json"

echo "== 4/4 place & route + pack =="
nextpnr-himbaechel --json "$BUILD/$SOC_TOP.json" \
  --write "$BUILD/$SOC_TOP.pnr.json" \
  --device GW2AR-LV18QN88C8/I7 \
  --vopt family=GW2A-18C --vopt cst="$ROOT/boards/tangnano20k/neorv32_soc.cst"
gowin_pack -d GW2A-18C -o "$BUILD/$SOC_TOP.fs" "$BUILD/$SOC_TOP.pnr.json"
echo "bitstream: $BUILD/$SOC_TOP.fs"
echo ""
echo "NOTE: this only BUILT the bitstream. It did not touch the board."
echo "flash to SRAM (temporary, safe): openFPGALoader -b tangnano20k $BUILD/$SOC_TOP.fs"
echo "flash to SPI  (persistent)    : openFPGALoader -b tangnano20k -f $BUILD/$SOC_TOP.fs"
