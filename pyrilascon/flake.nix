{
  description = "pyrilascon — a tiered, verified Ascon (NIST SP 800-232) hardware generator and design-space explorer";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # NEORV32 soft core (VHDL) - pinned raw source, no manual clone. Pin a release
    # with url = "github:stnolting/neorv32/v1.11.0"; bump: nix flake update neorv32.
    neorv32 = { url = "github:stnolting/neorv32"; flake = false; };
  };

  outputs = { self, nixpkgs, neorv32 }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      pythonFor = pkgs: pkgs.python3.withPackages (ps: with ps; [ pytest pyserial ]);

      apiculaFor = pkgs:
        if pkgs ? apicula then pkgs.apicula
        else if pkgs.python3Packages ? apycula then pkgs.python3Packages.apycula
        else null;

      # A yosys that can read VHDL via the GHDL plugin. nixpkgs builds its yosys
      # plugins against its OWN yosys+ghdl (version-matched), exposed as
      # yosys.allPlugins - so this is far more robust than compiling the upstream
      # plugin against nixpkgs' (fast-moving, often dev) ghdl. If your channel does
      # not expose the ghdl plugin (or it fails to build), the guard falls back to
      # plain yosys and you use YosysHQ oss-cad-suite for the SoC synthesis instead.
      yosysGhdlFor = pkgs:
        let plugins = pkgs.yosys.allPlugins or { };
        in if plugins ? ghdl
           then pkgs.yosys.withPlugins [ plugins.ghdl ]
           else pkgs.yosys;
    in
    {
      devShells = forAllSystems (pkgs:
        let
          lib = pkgs.lib;
          pythonEnv = pythonFor pkgs;
          apicula = apiculaFor pkgs;

          # FPGA back end (place & route + program), minus yosys (added per shell).
          fpgaBackend = [ pkgs.nextpnr pkgs.openfpgaloader ]
            ++ lib.optional (apicula != null) apicula;

          verify = [ pkgs.iverilog pkgs.gcc ];
          firmware = [ pkgs.pkgsCross.riscv32-embedded.buildPackages.gcc pkgs.picocom ];
          base = [ pythonEnv pkgs.gnumake pkgs.git pkgs.ghdl ];

          apiculaNote = lib.optionalString (apicula == null) ''
            echo ""
            echo "  NOTE: gowin_pack (Project Apicula) is not in this nixpkgs pin."
            echo "        Get it with:  pip install --user apycula  (or use oss-cad-suite)."
          '';
        in
        {
          # Default: the verified flows (model, generator, RTL sim, C, the Verilog
          # perm_smoke board flow) + ghdl for VHDL linting. Plain yosys. Always builds.
          default = pkgs.mkShell {
            name = "pyrilascon";
            packages = base ++ [ pkgs.yosys ] ++ fpgaBackend ++ verify ++ firmware;
            shellHook = ''
              export NEORV32_HOME="${neorv32}"
              echo "pyrilascon dev shell — model, generator, RTL sim, and the Tang Nano flow"
              echo "  make test        run the full suite (generator + RTL sim + C)"
              echo "  make catalog     design-space tier breakdown"
              echo "  make flash BOARD=tangnano20k TARGET=perm_smoke   build + flash the LED demo"
              echo "  nix develop .#soc   for the fully-open NEORV32 SoC build (yosys + GHDL)"
              echo "  NEORV32_HOME  -> pinned soft-core source"
            '' + apiculaNote;
          };

          # SoC shell: yosys WITH the GHDL plugin (nixpkgs-matched if available),
          # so the fully-open VHDL+Verilog build needs no external toolchain. If the
          # matched plugin is not on your channel, this yosys is plain and you should
          # `source <oss-cad-suite>/environment` before `make soc-build`.
          soc = pkgs.mkShell {
            name = "pyrilascon-soc";
            packages = base ++ [ (yosysGhdlFor pkgs) ] ++ fpgaBackend ++ verify ++ firmware;
            shellHook = ''
              export NEORV32_HOME="${neorv32}"
              export GHDL_PREFIX="$(${pkgs.ghdl}/bin/ghdl --disp-config | sed -n 's/.*library directory: //p' | head -1)"
              echo "pyrilascon SoC shell — fully-open NEORV32 + Ascon build"
              if ! yosys -p 'help ghdl' 2>&1 | grep -qi 'no such'; then
                echo "  yosys has the GHDL plugin (nixpkgs-matched). Build the SoC:"
                echo "    make soc-check     # elaborate + link NEORV32 + accelerator (fast)"
                echo "    make soc-build     # full bitstream (ghdl -> yosys -> nextpnr -> gowin_pack)"
              else
                echo "  this channel's yosys has no GHDL plugin. Source oss-cad-suite, then"
                echo "  'make soc-build':  https://github.com/YosysHQ/oss-cad-suite-build/releases"
              fi
              echo "  NEORV32_HOME  -> pinned soft-core source"
            '' + apiculaNote;
          };
        });

      # `nix flake check` runs the whole test suite reproducibly.
      checks = forAllSystems (pkgs:
        let pythonEnv = pythonFor pkgs;
        in {
          tests = pkgs.runCommandLocal "pyrilascon-tests"
            { nativeBuildInputs = [ pythonEnv pkgs.iverilog pkgs.gcc ]; }
            ''
              cp -r ${self}/. src
              chmod -R u+w src
              cd src
              export HOME="$TMPDIR"
              python -m pytest -q
              touch "$out"
            '';
        });

      formatter = forAllSystems (pkgs: pkgs.nixpkgs-fmt);
    };
}
