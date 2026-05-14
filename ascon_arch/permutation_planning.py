from dataclasses import dataclass
from math import ceil

from ascon_arch.config import PermutationConfig
from ascon_arch.enums import PermutationProfile, PermutationStyle, SBoxStyle, TargetTechnology


@dataclass(frozen=True, slots=True)
class PermutationLatencyEstimate:
    """Cycle and qualitative implementation estimate for one permutation config."""

    p6_cycles: int
    p8_cycles: int
    p12_cycles: int
    initiation_interval: int
    contexts_for_full_pipeline: int
    area_class: str
    timing_risk: str
    throughput_model: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "p6_cycles": self.p6_cycles,
            "p8_cycles": self.p8_cycles,
            "p12_cycles": self.p12_cycles,
            "initiation_interval": self.initiation_interval,
            "contexts_for_full_pipeline": self.contexts_for_full_pipeline,
            "area_class": self.area_class,
            "timing_risk": self.timing_risk,
            "throughput_model": self.throughput_model,
            "notes": list(self.notes),
        }


def permutation_config_for_profile(
    profile: PermutationProfile,
    target: TargetTechnology,
    *,
    sbox_style: SBoxStyle | None = None,
) -> PermutationConfig:
    """Build a canonical permutation config for a named architectural profile."""
    default_sbox = SBoxStyle.LUT5 if target == TargetTechnology.FPGA else SBoxStyle.BOOLEAN
    sbox = sbox_style or default_sbox

    if profile == PermutationProfile.ONE_ROUND_PER_CYCLE:
        return PermutationConfig(
            style=PermutationStyle.ROUND_SERIAL,
            sbox_style=sbox,
            rounds_per_cycle=1,
            pipeline_stages=0,
            unroll_factor=1,
            register_between_rounds=False,
            share_round_logic=True,
            sbox_columns_per_cycle=64,
        )
    if profile == PermutationProfile.TWO_ROUNDS_PER_CYCLE:
        return _rounds_per_cycle_config(2, sbox)
    if profile == PermutationProfile.FOUR_ROUNDS_PER_CYCLE:
        return _rounds_per_cycle_config(4, sbox)
    if profile == PermutationProfile.EIGHT_ROUNDS_PER_CYCLE:
        return _rounds_per_cycle_config(8, sbox)
    if profile == PermutationProfile.FULLY_PIPELINED:
        return PermutationConfig(
            style=PermutationStyle.ROUND_PIPELINED,
            sbox_style=sbox,
            rounds_per_cycle=1,
            pipeline_stages=12,
            unroll_factor=12,
            register_between_rounds=True,
            share_round_logic=False,
            sbox_columns_per_cycle=64,
            pipeline_initiation_interval=1,
            context_interleaving_required=True,
        )
    if profile == PermutationProfile.COLUMN_SERIAL:
        return PermutationConfig(
            style=PermutationStyle.COLUMN_SERIAL,
            sbox_style=SBoxStyle.BOOLEAN,
            rounds_per_cycle=1,
            pipeline_stages=0,
            unroll_factor=1,
            register_between_rounds=False,
            share_round_logic=True,
            sbox_columns_per_cycle=1,
        )
    if profile == PermutationProfile.BIT_SERIAL:
        return PermutationConfig(
            style=PermutationStyle.BIT_SERIAL,
            sbox_style=SBoxStyle.BOOLEAN,
            rounds_per_cycle=1,
            pipeline_stages=0,
            unroll_factor=1,
            register_between_rounds=False,
            share_round_logic=True,
            sbox_columns_per_cycle=1,
        )
    raise ValueError(f"unsupported permutation profile: {profile}")


def _rounds_per_cycle_config(rounds_per_cycle: int, sbox_style: SBoxStyle) -> PermutationConfig:
    return PermutationConfig(
        style=PermutationStyle.ROUND_UNROLLED,
        sbox_style=sbox_style,
        rounds_per_cycle=rounds_per_cycle,
        pipeline_stages=0,
        unroll_factor=rounds_per_cycle,
        register_between_rounds=False,
        share_round_logic=False,
        sbox_columns_per_cycle=64,
    )


def cycles_for_permutation(rounds: int, config: PermutationConfig) -> int:
    if rounds not in (6, 8, 12):
        raise ValueError("supported Ascon permutation sizes are p6, p8, and p12")

    if config.style in (PermutationStyle.ROUND_PIPELINED, PermutationStyle.FULLY_UNROLLED_PIPELINED):
        # A separate pN round pipeline has N visible cycles. A shared p12 pipeline
        # may later add bypass constraints, but that belongs in the backend.
        return rounds
    if config.style == PermutationStyle.COLUMN_SERIAL:
        return rounds * ceil(64 / config.sbox_columns_per_cycle)
    if config.style == PermutationStyle.BIT_SERIAL:
        # Conservative architectural placeholder: one S-box column per cycle plus
        # additional serialized linear/round-control work will be refined later.
        return rounds * 64
    return ceil(rounds / config.rounds_per_cycle)


def estimate_permutation(config: PermutationConfig) -> PermutationLatencyEstimate:
    p6 = cycles_for_permutation(6, config)
    p8 = cycles_for_permutation(8, config)
    p12 = cycles_for_permutation(12, config)
    notes: list[str] = []

    if config.style == PermutationStyle.ROUND_SERIAL:
        area_class = "small"
        timing_risk = "low"
        ii = p12
        contexts = 1
        throughput = "one active permutation; latency equals round count"
    elif config.style == PermutationStyle.ROUND_UNROLLED:
        if config.rounds_per_cycle <= 2:
            area_class = "medium"
            timing_risk = "medium"
        elif config.rounds_per_cycle <= 4:
            area_class = "medium_high"
            timing_risk = "medium_high"
        else:
            area_class = "large"
            timing_risk = "high"
        ii = p12
        contexts = 1
        throughput = f"{config.rounds_per_cycle} combinational rounds per cycle; one active permutation per engine"
    elif config.style in (PermutationStyle.ROUND_PIPELINED, PermutationStyle.FULLY_UNROLLED_PIPELINED):
        area_class = "large"
        timing_risk = "medium" if config.register_between_rounds else "high"
        ii = config.pipeline_initiation_interval or 1
        contexts = max(1, config.pipeline_stages)
        throughput = "one permutation can be launched every initiation interval when enough independent contexts exist"
        notes.append("requires context interleaving or independent messages for full utilization")
    elif config.style == PermutationStyle.COLUMN_SERIAL:
        area_class = "very_small"
        timing_risk = "low"
        ii = p12
        contexts = 1
        throughput = "reuses a small number of 5-bit S-box columns across the 64 state columns"
    elif config.style == PermutationStyle.BIT_SERIAL:
        area_class = "ultra_small"
        timing_risk = "low"
        ii = p12
        contexts = 1
        throughput = "ultra-small serialized permutation; exact cycle count is backend dependent"
    else:
        area_class = "unknown"
        timing_risk = "unknown"
        ii = p12
        contexts = 1
        throughput = "unknown"

    if config.rounds_per_cycle in (4, 8):
        notes.append("good FPGA candidate; synthesize both to compare timing closure")
    if config.rounds_per_cycle > 2 and config.style == PermutationStyle.ROUND_UNROLLED:
        notes.append("usually aggressive for small-area ASIC unless timing/area budget allows it")
    if config.sbox_columns_per_cycle < 64:
        notes.append("S-box is physically serialized; p_S no longer completes in one cycle")

    return PermutationLatencyEstimate(
        p6_cycles=p6,
        p8_cycles=p8,
        p12_cycles=p12,
        initiation_interval=ii,
        contexts_for_full_pipeline=contexts,
        area_class=area_class,
        timing_risk=timing_risk,
        throughput_model=throughput,
        notes=tuple(notes),
    )
