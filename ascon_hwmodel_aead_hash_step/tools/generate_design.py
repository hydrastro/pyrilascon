from argparse import ArgumentParser
from pathlib import Path

from ascon_arch.config import ImplementationConfig
from ascon_arch.enums import PermutationProfile, TargetTechnology
from ascon_arch.presets import (
    asic_two_datapaths_column_serial_config,
    asic_two_datapaths_config,
    asic_two_datapaths_two_rounds_per_cycle_config,
    config_with_permutation_profile,
    fpga_n_parallel_engines_config,
    fpga_n_parallel_engines_with_profile_config,
    shared_datapath_config,
    shared_permutation_mode_fsm_config,
)
from ascon_arch.design_product import write_design_product


PRESET_NAMES: tuple[str, ...] = (
    "asic_two_datapaths",
    "asic_two_datapaths_2rpc",
    "asic_two_datapaths_column_serial",
    "fpga_n_parallel_engines",
    "asic_shared_datapath",
    "fpga_shared_datapath",
    "asic_shared_permutation_mode_fsm",
    "fpga_shared_permutation_mode_fsm",
)


def build_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Generate an ASCON architecture product directory.")
    parser.add_argument("--config", type=Path, help="Path to a JSON ImplementationConfig.")
    parser.add_argument("--preset", choices=PRESET_NAMES, help="Built-in preset to generate.")
    parser.add_argument("--engine-count", type=int, default=4, help="Engine count for fpga_n_parallel_engines preset.")
    parser.add_argument(
        "--permutation-profile",
        choices=tuple(profile.value for profile in PermutationProfile),
        help="Override the preset permutation profile while preserving the rest of the architecture.",
    )
    parser.add_argument("--out", type=Path, default=Path("build"), help="Output root directory.")
    return parser


def config_from_args(preset: str, engine_count: int) -> ImplementationConfig:
    if preset == "asic_two_datapaths":
        return asic_two_datapaths_config()
    if preset == "asic_two_datapaths_2rpc":
        return asic_two_datapaths_two_rounds_per_cycle_config()
    if preset == "asic_two_datapaths_column_serial":
        return asic_two_datapaths_column_serial_config()
    if preset == "fpga_n_parallel_engines":
        return fpga_n_parallel_engines_config(engine_count)
    if preset == "asic_shared_datapath":
        return shared_datapath_config(TargetTechnology.ASIC, name="asic_shared_datapath")
    if preset == "fpga_shared_datapath":
        return shared_datapath_config(TargetTechnology.FPGA, name="fpga_shared_datapath")
    if preset == "asic_shared_permutation_mode_fsm":
        return shared_permutation_mode_fsm_config(TargetTechnology.ASIC)
    if preset == "fpga_shared_permutation_mode_fsm":
        return shared_permutation_mode_fsm_config(TargetTechnology.FPGA)
    raise SystemExit("unknown preset")


def apply_profile(config: ImplementationConfig, profile_value: str | None, engine_count: int) -> ImplementationConfig:
    if profile_value is None:
        return config
    profile = PermutationProfile(profile_value)
    if config.target == TargetTechnology.FPGA and config.topology.family.value == "parallel_engines":
        return fpga_n_parallel_engines_with_profile_config(engine_count, profile)
    return config_with_permutation_profile(config, profile)


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.config is not None:
        config = ImplementationConfig.read_json(args.config)
    elif args.preset is not None:
        config = config_from_args(args.preset, args.engine_count)
    else:
        raise SystemExit("provide either --config or --preset")

    config = apply_profile(config, args.permutation_profile, args.engine_count)
    written = write_design_product(config, args.out)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
