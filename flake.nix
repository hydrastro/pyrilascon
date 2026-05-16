{
  description = "pyrilascon FPGA/ASCON development shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python3
          python3Packages.pytest
          python3Packages.pip
          python3Packages.virtualenv

          yosys
          nextpnr
          openfpgaloader
          picocom
          usbutils
          pkgsCross.riscv32-embedded.buildPackages.gcc

          gnumake
          git
          which
        ];

        shellHook = ''
          echo "pyrilascon FPGA shell"

          if [ ! -d .venv-fpga ]; then
            echo "Creating .venv-fpga for YoWASP Gowin tools..."
            python -m venv .venv-fpga
          fi

          source .venv-fpga/bin/activate

          python -m pip install --upgrade pip >/dev/null
          python -m pip install \
            yowasp-yosys \
            yowasp-nextpnr-himbaechel-gowin \
            >/dev/null

          export YOSYS=yowasp-yosys
          export NEXTPNR=yowasp-nextpnr-himbaechel-gowin
          export GOWIN_PACK=gowin_pack
          export OPENFPGALOADER=openFPGALoader

          # NEORV32's upstream Makefiles expect a riscv-none-elf-* prefix.
          # Nixpkgs' embedded RISC-V cross toolchain commonly exposes
          # riscv32-none-elf-* instead, so provide repo-local compatibility
          # wrappers without relying on any user-specific $HOME path.
          if command -v riscv32-none-elf-gcc >/dev/null 2>&1 && ! command -v riscv-none-elf-gcc >/dev/null 2>&1; then
            for tool in gcc g++ cpp as ld ar ranlib objcopy objdump size strip; do
              src="$(command -v riscv32-none-elf-$tool 2>/dev/null || true)"
              if [ -n "$src" ]; then
                ln -sf "$src" ".venv-fpga/bin/riscv-none-elf-$tool"
              fi
            done
          fi

          echo "Tool check:"
          which $YOSYS || true
          which $NEXTPNR || true
          which $GOWIN_PACK || true
          which $OPENFPGALOADER || true
          which picocom || true
          which riscv-none-elf-gcc || true
        '';
      };
    };
}
