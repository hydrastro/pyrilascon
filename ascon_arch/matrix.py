from dataclasses import dataclass

from ascon_arch.config import ImplementationConfig
from ascon_arch.enums import DatapathProfile, PermutationProfile, TargetTechnology
from ascon_arch.presets import (
    asic_two_datapaths_config,
    config_with_datapath_profile,
    config_with_permutation_profile,
    fpga_n_parallel_engines_config,
)
from ascon_arch.validation import ConfigValidationError, validate_config


@dataclass(frozen=True, slots=True)
class MatrixEntry:
    config: ImplementationConfig | None
    target: TargetTechnology
    datapath_profile: DatapathProfile
    permutation_profile: PermutationProfile
    valid: bool
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "config_name": None if self.config is None else self.config.name,
            "target": self.target.value,
            "datapath_profile": self.datapath_profile.value,
            "permutation_profile": self.permutation_profile.value,
            "valid": self.valid,
            "reason": self.reason,
        }


def build_config_candidate(
    target: TargetTechnology,
    datapath_profile: DatapathProfile,
    permutation_profile: PermutationProfile,
    *,
    engine_count: int = 4,
) -> ImplementationConfig:
    if target == TargetTechnology.FPGA:
        base = fpga_n_parallel_engines_config(engine_count)
    else:
        base = asic_two_datapaths_config()
    config = config_with_datapath_profile(base, datapath_profile)
    return config_with_permutation_profile(config, permutation_profile)


def enumerate_valid_matrix(
    target: TargetTechnology,
    datapath_profiles: tuple[DatapathProfile, ...],
    permutation_profiles: tuple[PermutationProfile, ...],
    *,
    engine_count: int = 4,
) -> tuple[MatrixEntry, ...]:
    entries: list[MatrixEntry] = []
    for datapath_profile in datapath_profiles:
        for permutation_profile in permutation_profiles:
            try:
                config = build_config_candidate(
                    target,
                    datapath_profile,
                    permutation_profile,
                    engine_count=engine_count,
                )
                validate_config(config)
            except (ConfigValidationError, ValueError) as exc:
                entries.append(
                    MatrixEntry(
                        config=None,
                        target=target,
                        datapath_profile=datapath_profile,
                        permutation_profile=permutation_profile,
                        valid=False,
                        reason=str(exc),
                    )
                )
            else:
                entries.append(
                    MatrixEntry(
                        config=config,
                        target=target,
                        datapath_profile=datapath_profile,
                        permutation_profile=permutation_profile,
                        valid=True,
                    )
                )
    return tuple(entries)


ASIC_DATAPATH_MATRIX: tuple[DatapathProfile, ...] = (
    DatapathProfile.W64,
    DatapathProfile.W32,
    DatapathProfile.W16,
    DatapathProfile.W8_SERIAL,
    DatapathProfile.W5_SBOX_SERIAL,
    DatapathProfile.W1_BIT_SERIAL,
)

ASIC_PERMUTATION_MATRIX: tuple[PermutationProfile, ...] = (
    PermutationProfile.ONE_ROUND_PER_CYCLE,
    PermutationProfile.TWO_ROUNDS_PER_CYCLE,
    PermutationProfile.COLUMN_SERIAL,
    PermutationProfile.BIT_SERIAL,
)

FPGA_DATAPATH_MATRIX: tuple[DatapathProfile, ...] = (
    DatapathProfile.W128,
    DatapathProfile.W64,
)

FPGA_PERMUTATION_MATRIX: tuple[PermutationProfile, ...] = (
    PermutationProfile.FOUR_ROUNDS_PER_CYCLE,
    PermutationProfile.EIGHT_ROUNDS_PER_CYCLE,
    PermutationProfile.FULLY_PIPELINED,
)
