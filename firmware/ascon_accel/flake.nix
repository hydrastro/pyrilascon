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

          echo "Tool check:"
          which $YOSYS || true
          which $NEXTPNR || true
          which $GOWIN_PACK || true
          which $OPENFPGALOADER || true
        '';
      };
    };
}
