from argparse import ArgumentParser
from pathlib import Path

from ascon_arch.config import ImplementationConfig
from ascon_arch.presets import asic_two_datapaths_config, fpga_n_parallel_engines_config
from ascon_arch.design_product import write_design_product


def build_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Generate an ASCON architecture product directory.")
    parser.add_argument("--config", type=Path, help="Path to a JSON ImplementationConfig.")
    parser.add_argument("--preset", choices=("asic_two_datapaths", "fpga_n_parallel_engines"), help="Built-in preset to generate.")
    parser.add_argument("--engine-count", type=int, default=4, help="Engine count for fpga_n_parallel_engines preset.")
    parser.add_argument("--out", type=Path, default=Path("build"), help="Output root directory.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.config is not None:
        config = ImplementationConfig.read_json(args.config)
    elif args.preset == "asic_two_datapaths":
        config = asic_two_datapaths_config()
    elif args.preset == "fpga_n_parallel_engines":
        config = fpga_n_parallel_engines_config(args.engine_count)
    else:
        raise SystemExit("provide either --config or --preset")

    written = write_design_product(config, args.out)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
