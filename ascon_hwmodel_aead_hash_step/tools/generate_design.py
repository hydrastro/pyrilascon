from argparse import ArgumentParser
from pathlib import Path

from ascon_arch.config import ImplementationConfig
from ascon_arch.enums import ContextProfile, DatapathProfile, PermutationProfile, TargetTechnology, TopLevelProfile
from ascon_arch.presets import (
    asic_two_datapaths_column_serial_config,
    asic_dual_enc_dec_cores_config,
    asic_two_datapaths_config,
    asic_two_datapaths_with_datapath_profile_config,
    config_with_context_profile,
    config_with_datapath_profile,
    asic_two_datapaths_two_rounds_per_cycle_config,
    config_with_permutation_profile,
    config_with_top_level_profile,
    fpga_m_pipelines_n_contexts_config,
    fpga_n_parallel_engines_config,
    fpga_n_parallel_engines_with_datapath_profile_config,
    fpga_n_parallel_engines_with_profile_config,
    fpga_one_pipelined_permutation_n_contexts_config,
    shared_datapath_config,
    shared_permutation_mode_fsm_config,
)
from ascon_arch.design_product import write_design_product


PRESET_NAMES: tuple[str, ...] = (
    "asic_two_datapaths",
    "asic_dual_enc_dec_cores",
    "asic_two_datapaths_2rpc",
    "asic_two_datapaths_column_serial",
    "fpga_n_parallel_engines",
    "fpga_one_pipelined_permutation_n_contexts",
    "fpga_m_pipelines_n_contexts",
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
    parser.add_argument(
        "--datapath-profile",
        choices=tuple(profile.value for profile in DatapathProfile),
        help="Override the preset datapath width profile while preserving the rest of the architecture.",
    )
    parser.add_argument(
        "--top-level-profile",
        choices=tuple(profile.value for profile in TopLevelProfile),
        help="Override the top-level core/pipeline organization while preserving other config choices when possible.",
    )
    parser.add_argument("--pipeline-count", type=int, help="Pipeline count for m_pipelines_n_contexts top-level organization.")
    parser.add_argument(
        "--context-profile",
        choices=tuple(profile.value for profile in ContextProfile),
        help="Override the preset state/context organization while preserving the rest of the architecture.",
    )
    parser.add_argument(
        "--contexts-per-engine",
        type=int,
        help="Override contexts per engine when --context-profile selects a multi-context organization.",
    )
    parser.add_argument("--out", type=Path, default=Path("build"), help="Output root directory.")
    return parser


def config_from_args(preset: str, engine_count: int) -> ImplementationConfig:
    if preset == "asic_two_datapaths":
        return asic_two_datapaths_config()
    if preset == "asic_dual_enc_dec_cores":
        return asic_dual_enc_dec_cores_config()
    if preset == "asic_two_datapaths_2rpc":
        return asic_two_datapaths_two_rounds_per_cycle_config()
    if preset == "asic_two_datapaths_column_serial":
        return asic_two_datapaths_column_serial_config()
    if preset == "fpga_n_parallel_engines":
        return fpga_n_parallel_engines_config(engine_count)
    if preset == "fpga_one_pipelined_permutation_n_contexts":
        return fpga_one_pipelined_permutation_n_contexts_config()
    if preset == "fpga_m_pipelines_n_contexts":
        return fpga_m_pipelines_n_contexts_config(engine_count)
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
    sbox = None
    if config.target == TargetTechnology.FPGA and profile in (
        PermutationProfile.FOUR_ROUNDS_PER_CYCLE,
        PermutationProfile.EIGHT_ROUNDS_PER_CYCLE,
        PermutationProfile.FULLY_PIPELINED,
    ):
        # Preserve any previous datapath-profile override while selecting the
        # FPGA-friendly S-box default for these permutation profiles.
        from ascon_arch.enums import SBoxStyle
        sbox = SBoxStyle.LUT5
    return config_with_permutation_profile(config, profile, sbox_style=sbox)


def apply_datapath_profile(config: ImplementationConfig, profile_value: str | None, engine_count: int) -> ImplementationConfig:
    if profile_value is None:
        return config
    profile = DatapathProfile(profile_value)
    if config.target == TargetTechnology.FPGA and config.topology.family.value == "parallel_engines":
        return fpga_n_parallel_engines_with_datapath_profile_config(engine_count, profile)
    if config.target == TargetTechnology.ASIC and config.topology.family.value == "separate_enc_dec_datapaths":
        return asic_two_datapaths_with_datapath_profile_config(profile)
    return config_with_datapath_profile(config, profile)


def apply_top_level_profile(
    config: ImplementationConfig,
    profile_value: str | None,
    engine_count: int,
    pipeline_count: int | None,
    contexts_per_engine: int | None,
) -> ImplementationConfig:
    if profile_value is None:
        return config
    profile = TopLevelProfile(profile_value)
    return config_with_top_level_profile(
        config,
        profile,
        core_count=engine_count,
        pipeline_count=pipeline_count,
        contexts_per_pipeline=contexts_per_engine,
    )


def apply_context_profile(
    config: ImplementationConfig,
    profile_value: str | None,
    contexts_per_engine: int | None,
) -> ImplementationConfig:
    if profile_value is None:
        return config
    return config_with_context_profile(config, ContextProfile(profile_value), contexts_per_engine=contexts_per_engine)


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.config is not None:
        config = ImplementationConfig.read_json(args.config)
    elif args.preset is not None:
        config = config_from_args(args.preset, args.engine_count)
    else:
        raise SystemExit("provide either --config or --preset")

    config = apply_datapath_profile(config, args.datapath_profile, args.engine_count)
    config = apply_profile(config, args.permutation_profile, args.engine_count)
    config = apply_top_level_profile(config, args.top_level_profile, args.engine_count, args.pipeline_count, args.contexts_per_engine)
    config = apply_context_profile(config, args.context_profile, args.contexts_per_engine)
    written = write_design_product(config, args.out)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
