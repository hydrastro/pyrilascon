{
  description = "pyrilascon - Ascon hardware accelerator: model, design-space, RTL, firmware";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          # Python model + design-space + tooling
          python3
          python3Packages.pytest

          # RTL simulation (golden-model cosim; tests skip gracefully without these)
          iverilog
          verilator

          # FPGA open flow (Tang Nano 9K / Gowin). gowin_pack is provided via a
          # YoWASP wheel in stage 3, since it is not packaged in nixpkgs.
          yosys
          nextpnr
          openfpgaloader

          # NEORV32 soft-core firmware toolchain + serial
          pkgsCross.riscv32-embedded.buildPackages.gcc
          picocom
          python3Packages.pyserial

          gnumake
          git
        ];

        shellHook = ''
          echo "pyrilascon dev shell"
          echo "  make test      - golden-model + catalog tests"
          echo "  make catalog   - design-space tier breakdown"
        '';
      };
    };
}
