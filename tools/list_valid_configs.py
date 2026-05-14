from argparse import ArgumentParser
from dataclasses import dataclass
from itertools import product
from pathlib import Path
import csv
import json

from ascon_arch.algorithm_planning import REQUESTED_SINGLE_ALGORITHM_FEATURES
from ascon_arch.config import ImplementationConfig
from ascon_arch.enums import (
    AlgorithmFeature,
    ControlProfile,
    DatapathProfile,
    PaddingProfile,
    PermutationProfile,
    SecurityProfile,
    TargetTechnology,
    TopLevelProfile,
)
from ascon_arch.presets import (
    asic_dual_enc_dec_cores_config,
    config_with_algorithm_feature,
    config_with_control_profile,
    config_with_datapath_profile,
    config_with_padding_profile,
    config_with_permutation_profile,
    config_with_security_profile,
    fpga_m_pipelines_n_contexts_config,
    fpga_n_parallel_engines_config,
    fpga_one_pipelined_permutation_n_contexts_config,
)
from ascon_arch.validation import ConfigValidationError, validate_config


@dataclass(frozen=True, slots=True)
class ValidConfigEntry:
    target: str
    algorithm: str
    top_level: str
    datapath: str
    permutation: str
    control: str
    padding: str
    security: str
    valid: bool
    name: str
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "algorithm": self.algorithm,
            "top_level": self.top_level,
            "datapath": self.datapath,
            "permutation": self.permutation,
            "control": self.control,
            "padding": self.padding,
            "security": self.security,
            "valid": self.valid,
            "name": self.name,
            "reason": self.reason,
        }


FPGA_TOP_LEVELS: dict[str, object] = {
    TopLevelProfile.N_IDENTICAL_AEAD_CORES.value: lambda engine_count, pipeline_count, contexts_per_pipeline: fpga_n_parallel_engines_config(engine_count),
    TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS.value: lambda engine_count, pipeline_count, contexts_per_pipeline: fpga_one_pipelined_permutation_n_contexts_config(contexts_per_pipeline),
    TopLevelProfile.M_PIPELINES_N_CONTEXTS.value: lambda engine_count, pipeline_count, contexts_per_pipeline: fpga_m_pipelines_n_contexts_config(pipeline_count, contexts_per_pipeline),
}


def _build_candidate(
    base: ImplementationConfig,
    algorithm: AlgorithmFeature,
    datapath: DatapathProfile,
    permutation: PermutationProfile,
    control: ControlProfile,
    padding: PaddingProfile,
    security: SecurityProfile,
) -> ImplementationConfig:
    config = config_with_algorithm_feature(base, algorithm)
    config = config_with_datapath_profile(config, datapath)
    config = config_with_permutation_profile(config, permutation)
    config = config_with_control_profile(config, control)
    config = config_with_padding_profile(config, padding)
    config = config_with_security_profile(config, security)
    validate_config(config)
    return config


def enumerate_selected_configs(
    *,
    target: TargetTechnology,
    engine_count: int = 4,
    pipeline_count: int = 2,
    contexts_per_pipeline: int = 12,
    include_invalid: bool = False,
    algorithms: tuple[AlgorithmFeature, ...] = REQUESTED_SINGLE_ALGORITHM_FEATURES,
) -> tuple[ValidConfigEntry, ...]:
    entries: list[ValidConfigEntry] = []

    if target == TargetTechnology.ASIC:
        top_builders = {TopLevelProfile.DUAL_ENC_DEC_CORES.value: lambda: asic_dual_enc_dec_cores_config()}
        datapaths = (
            DatapathProfile.W64,
            DatapathProfile.W32,
            DatapathProfile.W16,
            DatapathProfile.W8_SERIAL,
            DatapathProfile.W5_SBOX_SERIAL,
            DatapathProfile.W1_BIT_SERIAL,
        )
        permutations = (
            PermutationProfile.ONE_ROUND_PER_CYCLE,
            PermutationProfile.TWO_ROUNDS_PER_CYCLE,
            PermutationProfile.COLUMN_SERIAL,
            PermutationProfile.BIT_SERIAL,
        )
        controls = (ControlProfile.HARDCODED_FSM,)
        paddings = (PaddingProfile.RTL_PERFORMED,)
        securities = (SecurityProfile.NONE, SecurityProfile.ASIC_BASELINE)
    else:
        top_builders = {
            name: (lambda b=builder: b(engine_count, pipeline_count, contexts_per_pipeline))
            for name, builder in FPGA_TOP_LEVELS.items()
        }
        datapaths = (DatapathProfile.W128,)
        permutations = (
            PermutationProfile.FOUR_ROUNDS_PER_CYCLE,
            PermutationProfile.EIGHT_ROUNDS_PER_CYCLE,
            PermutationProfile.FULLY_PIPELINED,
        )
        controls = (
            ControlProfile.AXI_STREAM,
            ControlProfile.MICROCODED_SEQUENCER,
            ControlProfile.AXI_STREAM_MICROCODED_HYBRID,
        )
        paddings = (PaddingProfile.STREAMING_FINAL_BYTEMASK,)
        securities = (SecurityProfile.NONE, SecurityProfile.FPGA_FAULT_DETECT)

    for top_name, build_base in top_builders.items():
        for algorithm, datapath, permutation, control, padding, security in product(algorithms, datapaths, permutations, controls, paddings, securities):
            try:
                config = _build_candidate(build_base(), algorithm, datapath, permutation, control, padding, security)
            except (ConfigValidationError, ValueError) as exc:
                if include_invalid:
                    entries.append(
                        ValidConfigEntry(
                            target=target.value,
                            algorithm=algorithm.value,
                            top_level=top_name,
                            datapath=datapath.value,
                            permutation=permutation.value,
                            control=control.value,
                            padding=padding.value,
                            security=security.value,
                            valid=False,
                            name="",
                            reason=str(exc),
                        )
                    )
            else:
                entries.append(
                    ValidConfigEntry(
                        target=target.value,
                        algorithm=algorithm.value,
                        top_level=top_name,
                        datapath=datapath.value,
                        permutation=permutation.value,
                        control=control.value,
                        padding=padding.value,
                        security=security.value,
                        valid=True,
                        name=config.name,
                    )
                )
    return tuple(entries)


def _parse_algorithms(value: str) -> tuple[AlgorithmFeature, ...]:
    if value == "requested":
        return REQUESTED_SINGLE_ALGORITHM_FEATURES
    return tuple(AlgorithmFeature(item.strip()) for item in value.split(",") if item.strip())


def main() -> None:
    parser = ArgumentParser(description="List selected valid ASCON architecture configurations.")
    parser.add_argument("--target", choices=("asic", "fpga", "both"), default="both")
    parser.add_argument("--engine-count", type=int, default=4)
    parser.add_argument("--pipeline-count", type=int, default=2)
    parser.add_argument("--contexts-per-pipeline", type=int, default=12)
    parser.add_argument("--algorithms", default="requested", help="Comma-separated AlgorithmFeature values or 'requested'.")
    parser.add_argument("--include-invalid", action="store_true")
    parser.add_argument("--format", choices=("json", "csv", "text"), default="text")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    targets = (TargetTechnology.ASIC, TargetTechnology.FPGA) if args.target == "both" else (TargetTechnology(args.target),)
    algorithms = _parse_algorithms(args.algorithms)
    entries: list[ValidConfigEntry] = []
    for target in targets:
        entries.extend(
            enumerate_selected_configs(
                target=target,
                engine_count=args.engine_count,
                pipeline_count=args.pipeline_count,
                contexts_per_pipeline=args.contexts_per_pipeline,
                include_invalid=args.include_invalid,
                algorithms=algorithms,
            )
        )

    if args.format == "json":
        payload = json.dumps([entry.to_dict() for entry in entries], indent=2, sort_keys=True) + "\n"
    elif args.format == "csv":
        import io

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(entries[0].to_dict().keys()) if entries else [])
        if entries:
            writer.writeheader()
            for entry in entries:
                writer.writerow(entry.to_dict())
        payload = buf.getvalue()
    else:
        valid_count = sum(1 for entry in entries if entry.valid)
        payload_lines = [f"valid={valid_count} total_listed={len(entries)} algorithms={len(algorithms)}"]
        for entry in entries:
            status = "VALID" if entry.valid else "INVALID"
            suffix = f" reason={entry.reason}" if entry.reason else ""
            payload_lines.append(
                f"{status:7s} {entry.target:4s} algo={entry.algorithm:10s} {entry.top_level:38s} "
                f"dp={entry.datapath:17s} perm={entry.permutation:24s} "
                f"ctrl={entry.control:32s} sec={entry.security}{suffix}"
            )
        payload = "\n".join(payload_lines) + "\n"

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        try:
            print(payload, end="")
        except BrokenPipeError:
            # Allows commands such as `make list-valid-configs | head` to exit cleanly.
            pass


if __name__ == "__main__":
    main()
