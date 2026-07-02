{
  description = "pyrilascon FPGA/ASCON development shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    # NEORV32 RISC-V SoC RTL + software framework, pinned to the exact revision
    # this project targets: v1.13.01.01 (hw_version 0x01130101). Pinning here
    # means `nix develop` always brings the correct sources — no manual clone or
    # `git checkout`, and no breakage when upstream changes its file-list format
    # (post-f62ca43 it switched NEORV32_RTL_PATH_PLACEHOLDER -> $NEORV32_HOME,
    # which the board Makefiles do not expect). `flake = false` because NEORV32
    # is a plain source tree, not a flake.
    neorv32 = {
      url = "github:stnolting/neorv32/f62ca4323d263cfb0289e779bb107ffcf0dafff6";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, neorv32 }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };

      # Bare-metal RISC-V toolchain matching the NEORV32 CPU: RV32I with the
      # soft-float ilp32 ABI. The stock nixpkgs riscv32-embedded toolchain ships
      # a hard-float (ilp32d) newlib/libgcc only, so linking the firmware — built
      # soft-float, because the core has no FPU — fails with
      #   "can't link double-float modules with soft-float modules".
      # Building newlib + libgcc for ilp32 removes the mismatch at the root, and
      # the toolchain probe then selects its clean `soft` profile automatically.
      riscvPkgs = import nixpkgs {
        localSystem = system;
        crossSystem = {
          config = "riscv32-none-elf";
          libc = "newlib-nano";
          # Match the NEORV32 core exactly: base RV32I (no M/A/F/D) with the
          # soft-float ilp32 ABI. arch=rv32i is deliberate — if newlib were built
          # with M, its internal multiplies (e.g. inside printf) would be illegal
          # instructions on this multiply-less core even though the firmware
          # links. The firmware itself still compiles -march=rv32i_zicsr_zifencei;
          # those extras live in firmware objects and link fine against rv32i libs.
          gcc = {
            arch = "rv32i";
            abi = "ilp32";
          };
        };
      };
      riscvToolchain = riscvPkgs.buildPackages.gcc;
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python3
          python3Packages.pytest
          python3Packages.pip
          python3Packages.virtualenv
          python3Packages.platformdirs
          python3Packages.pyserial

          yosys
          nextpnr
          openfpgaloader
          picocom
          usbutils
          ghdl
          iverilog
          verilator

          gnumake
          git
          which
        ] ++ [
          riscvToolchain            # soft-float ilp32 RISC-V cross toolchain
        ];

        shellHook = ''
          echo "pyrilascon FPGA shell"

          # Resolve the checkout root even when `nix develop` is started from a
          # board subdirectory. This prevents board-local virtual environments
          # and duplicate external/neorv32 trees.
          PYRILASCON_ROOT="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || true)"
          if [ -z "$PYRILASCON_ROOT" ] || [ ! -f "$PYRILASCON_ROOT/flake.nix" ]; then
            probe="$PWD"
            while [ "$probe" != "/" ] && [ ! -f "$probe/flake.nix" ]; do
              probe="$(dirname "$probe")"
            done
            if [ ! -f "$probe/flake.nix" ]; then
              echo "error: could not locate the pyrilascon checkout root" >&2
              return 1
            fi
            PYRILASCON_ROOT="$probe"
          fi
          export PYRILASCON_ROOT

          VENV="$PYRILASCON_ROOT/.venv-fpga"
          REQUIREMENTS="$PYRILASCON_ROOT/requirements-fpga.txt"
          REQUIREMENTS_STAMP="$VENV/.requirements.sha256"

          if [ ! -x "$VENV/bin/python" ]; then
            echo "Creating $VENV"
            python -m venv "$VENV"
          fi
          source "$VENV/bin/activate"

          required_hash="$(sha256sum "$REQUIREMENTS" | cut -d' ' -f1)"
          installed_hash="$(cat "$REQUIREMENTS_STAMP" 2>/dev/null || true)"
          if [ "$required_hash" != "$installed_hash" ]; then
            echo "Installing pinned FPGA Python tools..."
            python -m pip install --disable-pip-version-check --upgrade pip >/dev/null
            python -m pip install --disable-pip-version-check -r "$REQUIREMENTS" >/dev/null
            printf '%s\n' "$required_hash" > "$REQUIREMENTS_STAMP"
          fi

          export YOSYS=yowasp-yosys
          export NEXTPNR=yowasp-nextpnr-himbaechel-gowin
          export GOWIN_PACK=gowin_pack
          export OPENFPGALOADER=openFPGALoader

          # Materialize the pinned, writable NEORV32 source tree once at the
          # checkout root. BOOT_MODE_SELECT=2 installs the generated IMEM image
          # into this tree before GHDL synthesis.
          NEORV32_DIR="$PYRILASCON_ROOT/external/neorv32"
          if [ "$(cat "$NEORV32_DIR/.flake-rev" 2>/dev/null)" != "${neorv32.rev}" ]; then
            echo "Materializing NEORV32 @ ${builtins.substring 0 7 neorv32.rev} -> $NEORV32_DIR"
            rm -rf "$NEORV32_DIR"
            mkdir -p "$PYRILASCON_ROOT/external"
            cp -r ${neorv32} "$NEORV32_DIR"
            chmod -R u+w "$NEORV32_DIR"
            printf '%s\n' "${neorv32.rev}" > "$NEORV32_DIR/.flake-rev"
          fi
          # Keep NEORV32_HOME unset globally: board Makefiles
          # resolve the project-local checkout explicitly, and tests remain
          # isolated from the developer's shell environment.

          # per-tool compatibility wrappers: NEORV32 expects riscv-none-elf-* while nixpkgs provides
          # riscv32-none-elf-*. Create each compatibility wrapper independently;
          # do not gate readelf/objcopy/etc. on whether gcc already exists.
          for tool in \
            gcc g++ cpp as ld ar ranlib objcopy objdump size strip readelf \
            addr2line nm strings c++filt elfedit; do
            src="$(command -v riscv32-none-elf-$tool 2>/dev/null || true)"
            if ! command -v riscv-none-elf-$tool >/dev/null 2>&1 \
              || [ -L "$VENV/bin/riscv-none-elf-$tool" ]; then
              [ -n "$src" ] && ln -sf "$src" "$VENV/bin/riscv-none-elf-$tool"
            fi
          done

          echo "Checkout: $PYRILASCON_ROOT"
          echo "Tool check:"
          command -v "$YOSYS" || true
          command -v "$NEXTPNR" || true
          command -v "$GOWIN_PACK" || true
          command -v "$OPENFPGALOADER" || true
          command -v riscv-none-elf-gcc || true
        '';
      };
    };
}
