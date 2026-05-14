from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
import json

from ascon_arch.enums import (
    AlgorithmFeature,
    ArchitectureFamily,
    ContextProfile,
    ContextSchedulingStyle,
    DatapathProfile,
    DatapathWidth,
    EngineCapability,
    FlowControlStyle,
    InterfaceStyle,
    LengthHandling,
    PaddingStrategy,
    PermutationStyle,
    ResetStyle,
    RtlLanguage,
    SBoxStyle,
    SideChannelProtection,
    StateStorageStyle,
    TargetTechnology,
)


def _enum_list(enum_type: type, values: object, default: tuple[Any, ...]) -> tuple[Any, ...]:
    if values is None:
        return default
    if not isinstance(values, list | tuple):
        raise TypeError("enum list field must be a list or tuple")
    return tuple(enum_type(str(value)) for value in values)


@dataclass(frozen=True, slots=True)
class AlgorithmConfig:
    """Algorithm features supported by one generated core."""

    features: tuple[AlgorithmFeature, ...] = (AlgorithmFeature.AEAD128,)
    include_encrypt: bool = True
    include_decrypt: bool = True
    include_hash: bool = False
    include_xof: bool = False
    include_cxof: bool = False

    def supports(self, feature: AlgorithmFeature) -> bool:
        return feature in self.features

    def to_dict(self) -> dict[str, Any]:
        return {
            "features": [feature.value for feature in self.features],
            "include_encrypt": self.include_encrypt,
            "include_decrypt": self.include_decrypt,
            "include_hash": self.include_hash,
            "include_xof": self.include_xof,
            "include_cxof": self.include_cxof,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "AlgorithmConfig":
        if data is None:
            return cls()
        features = _enum_list(AlgorithmFeature, data.get("features"), (AlgorithmFeature.AEAD128,))
        return cls(
            features=features,
            include_encrypt=bool(data.get("include_encrypt", True)),
            include_decrypt=bool(data.get("include_decrypt", True)),
            include_hash=bool(data.get("include_hash", AlgorithmFeature.HASH256 in features)),
            include_xof=bool(data.get("include_xof", AlgorithmFeature.XOF128 in features)),
            include_cxof=bool(data.get("include_cxof", AlgorithmFeature.CXOF128 in features)),
        )


@dataclass(frozen=True, slots=True)
class PermutationConfig:
    """Microarchitecture choices for one Ascon permutation engine.

    rounds_per_cycle controls how many complete p_C/p_S/p_L rounds are composed in
    one cycle for combinational/unrolled styles. sbox_columns_per_cycle controls
    how many of the 64 parallel 5-bit S-box columns are physically implemented;
    64 means a normal bitsliced word datapath, while 1 means an ultra-small
    column-serial S-box core.
    """

    style: PermutationStyle
    sbox_style: SBoxStyle
    rounds_per_cycle: int
    pipeline_stages: int
    unroll_factor: int = 1
    register_between_rounds: bool = False
    share_round_logic: bool = True
    sbox_columns_per_cycle: int = 64
    pipeline_initiation_interval: int | None = None
    context_interleaving_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "style": self.style.value,
            "sbox_style": self.sbox_style.value,
            "rounds_per_cycle": self.rounds_per_cycle,
            "pipeline_stages": self.pipeline_stages,
            "unroll_factor": self.unroll_factor,
            "register_between_rounds": self.register_between_rounds,
            "share_round_logic": self.share_round_logic,
            "sbox_columns_per_cycle": self.sbox_columns_per_cycle,
            "pipeline_initiation_interval": self.pipeline_initiation_interval,
            "context_interleaving_required": self.context_interleaving_required,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PermutationConfig":
        raw_ii = data.get("pipeline_initiation_interval")
        return cls(
            style=PermutationStyle(str(data["style"])),
            sbox_style=SBoxStyle(str(data["sbox_style"])),
            rounds_per_cycle=int(data["rounds_per_cycle"]),
            pipeline_stages=int(data["pipeline_stages"]),
            unroll_factor=int(data.get("unroll_factor", data.get("rounds_per_cycle", 1))),
            register_between_rounds=bool(data.get("register_between_rounds", False)),
            share_round_logic=bool(data.get("share_round_logic", True)),
            sbox_columns_per_cycle=int(data.get("sbox_columns_per_cycle", 64)),
            pipeline_initiation_interval=None if raw_ii is None else int(raw_ii),
            context_interleaving_required=bool(data.get("context_interleaving_required", False)),
        )


@dataclass(frozen=True, slots=True)
class DatapathConfig:
    """Width/resource choices inside one engine.

    profile is the architectural intent. lane_width is the main internal
    datapath slice. absorb_width is the width used when moving rate data
    into/out of the sponge. These are separate so a tiny ASIC can use a
    5-bit S-box-serial permutation core while still accepting 8-bit I/O.
    """

    state_width_bits: int = 320
    rate_width_bits: int = 128
    profile: DatapathProfile = DatapathProfile.W64
    lane_width: DatapathWidth = DatapathWidth.W64
    absorb_width: DatapathWidth = DatapathWidth.W128
    io_word_width: DatapathWidth = DatapathWidth.W128
    key_width_bits: int = 128
    tag_width_bits: int = 128
    split_encrypt_decrypt_control: bool = False
    share_key_registers: bool = False
    share_pad_logic: bool = True
    serialized_state_update: bool = False
    serialized_absorb: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_width_bits": self.state_width_bits,
            "rate_width_bits": self.rate_width_bits,
            "profile": self.profile.value,
            "lane_width": self.lane_width.value,
            "absorb_width": self.absorb_width.value,
            "io_word_width": self.io_word_width.value,
            "key_width_bits": self.key_width_bits,
            "tag_width_bits": self.tag_width_bits,
            "split_encrypt_decrypt_control": self.split_encrypt_decrypt_control,
            "share_key_registers": self.share_key_registers,
            "share_pad_logic": self.share_pad_logic,
            "serialized_state_update": self.serialized_state_update,
            "serialized_absorb": self.serialized_absorb,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "DatapathConfig":
        if data is None:
            return cls()
        return cls(
            state_width_bits=int(data.get("state_width_bits", 320)),
            rate_width_bits=int(data.get("rate_width_bits", 128)),
            profile=DatapathProfile(str(data.get("profile", DatapathProfile.W64.value))),
            lane_width=DatapathWidth(str(data.get("lane_width", DatapathWidth.W64.value))),
            absorb_width=DatapathWidth(str(data.get("absorb_width", DatapathWidth.W128.value))),
            io_word_width=DatapathWidth(str(data.get("io_word_width", data.get("absorb_width", DatapathWidth.W128.value)))),
            key_width_bits=int(data.get("key_width_bits", 128)),
            tag_width_bits=int(data.get("tag_width_bits", 128)),
            split_encrypt_decrypt_control=bool(data.get("split_encrypt_decrypt_control", False)),
            share_key_registers=bool(data.get("share_key_registers", False)),
            share_pad_logic=bool(data.get("share_pad_logic", True)),
            serialized_state_update=bool(data.get("serialized_state_update", False)),
            serialized_absorb=bool(data.get("serialized_absorb", False)),
        )


@dataclass(frozen=True, slots=True)
class ContextConfig:
    """How state/context is stored and scheduled.

    context_count is the total number of state contexts visible to the generated
    product. contexts_per_engine disambiguates N-engine FPGA products: for
    example, four engines with twelve interleaved contexts per engine has
    context_count=48 and contexts_per_engine=12.
    """

    profile: ContextProfile = ContextProfile.SINGLE_320_REGISTER
    scheduling: ContextSchedulingStyle = ContextSchedulingStyle.SINGLE_CONTEXT
    storage: StateStorageStyle = StateStorageStyle.SINGLE_CONTEXT_REGS
    context_count: int = 1
    contexts_per_engine: int = 1
    interleave_depth: int = 1
    context_id_bits: int = 0
    shadow_state: bool = False
    rollback_supported: bool = False
    state_memory_read_ports: int = 1
    state_memory_write_ports: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.value,
            "scheduling": self.scheduling.value,
            "storage": self.storage.value,
            "context_count": self.context_count,
            "contexts_per_engine": self.contexts_per_engine,
            "interleave_depth": self.interleave_depth,
            "context_id_bits": self.context_id_bits,
            "shadow_state": self.shadow_state,
            "rollback_supported": self.rollback_supported,
            "state_memory_read_ports": self.state_memory_read_ports,
            "state_memory_write_ports": self.state_memory_write_ports,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "ContextConfig":
        if data is None:
            return cls()
        context_count = int(data.get("context_count", 1))
        return cls(
            profile=ContextProfile(str(data.get("profile", ContextProfile.SINGLE_320_REGISTER.value))),
            scheduling=ContextSchedulingStyle(str(data.get("scheduling", ContextSchedulingStyle.SINGLE_CONTEXT.value))),
            storage=StateStorageStyle(str(data.get("storage", StateStorageStyle.SINGLE_CONTEXT_REGS.value))),
            context_count=context_count,
            contexts_per_engine=int(data.get("contexts_per_engine", context_count)),
            interleave_depth=int(data.get("interleave_depth", 1)),
            context_id_bits=int(data.get("context_id_bits", 0)),
            shadow_state=bool(data.get("shadow_state", False)),
            rollback_supported=bool(data.get("rollback_supported", False)),
            state_memory_read_ports=int(data.get("state_memory_read_ports", 1)),
            state_memory_write_ports=int(data.get("state_memory_write_ports", 1)),
        )


@dataclass(frozen=True, slots=True)
class PaddingConfig:
    strategy: PaddingStrategy = PaddingStrategy.INLINE_COMBINATIONAL
    length_handling: LengthHandling = LengthHandling.EXTERNAL_LAST_STROBE
    supports_partial_blocks: bool = True
    supports_bit_granular_lengths: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "length_handling": self.length_handling.value,
            "supports_partial_blocks": self.supports_partial_blocks,
            "supports_bit_granular_lengths": self.supports_bit_granular_lengths,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "PaddingConfig":
        if data is None:
            return cls()
        return cls(
            strategy=PaddingStrategy(str(data.get("strategy", PaddingStrategy.INLINE_COMBINATIONAL.value))),
            length_handling=LengthHandling(str(data.get("length_handling", LengthHandling.EXTERNAL_LAST_STROBE.value))),
            supports_partial_blocks=bool(data.get("supports_partial_blocks", True)),
            supports_bit_granular_lengths=bool(data.get("supports_bit_granular_lengths", False)),
        )


@dataclass(frozen=True, slots=True)
class DatapathTopology:
    family: ArchitectureFamily
    engine_count: int
    engine_capability: EngineCapability
    shared_encrypt_decrypt_datapath: bool
    encrypt_datapaths_per_engine: int
    decrypt_datapaths_per_engine: int
    shared_permutation_per_engine: bool
    mode_fsm_count_per_engine: int

    def expected_parallel_operations(self) -> int:
        if self.family == ArchitectureFamily.PARALLEL_ENGINES:
            return self.engine_count
        if self.family == ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS:
            return self.engine_count * (self.encrypt_datapaths_per_engine + self.decrypt_datapaths_per_engine)
        return self.engine_count

    def total_encrypt_datapaths(self) -> int:
        return self.engine_count * self.encrypt_datapaths_per_engine

    def total_decrypt_datapaths(self) -> int:
        return self.engine_count * self.decrypt_datapaths_per_engine

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family.value,
            "engine_count": self.engine_count,
            "engine_capability": self.engine_capability.value,
            "shared_encrypt_decrypt_datapath": self.shared_encrypt_decrypt_datapath,
            "encrypt_datapaths_per_engine": self.encrypt_datapaths_per_engine,
            "decrypt_datapaths_per_engine": self.decrypt_datapaths_per_engine,
            "shared_permutation_per_engine": self.shared_permutation_per_engine,
            "mode_fsm_count_per_engine": self.mode_fsm_count_per_engine,
            "expected_parallel_operations": self.expected_parallel_operations(),
            "total_encrypt_datapaths": self.total_encrypt_datapaths(),
            "total_decrypt_datapaths": self.total_decrypt_datapaths(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DatapathTopology":
        return cls(
            family=ArchitectureFamily(str(data["family"])),
            engine_count=int(data["engine_count"]),
            engine_capability=EngineCapability(str(data["engine_capability"])),
            shared_encrypt_decrypt_datapath=bool(data["shared_encrypt_decrypt_datapath"]),
            encrypt_datapaths_per_engine=int(data["encrypt_datapaths_per_engine"]),
            decrypt_datapaths_per_engine=int(data["decrypt_datapaths_per_engine"]),
            shared_permutation_per_engine=bool(data["shared_permutation_per_engine"]),
            mode_fsm_count_per_engine=int(data["mode_fsm_count_per_engine"]),
        )


@dataclass(frozen=True, slots=True)
class IOConfig:
    interface_style: InterfaceStyle
    data_bus_bits: int
    supports_backpressure: bool
    flow_control: FlowControlStyle = FlowControlStyle.VALID_READY
    separate_ad_text_channels: bool = False
    separate_encrypt_decrypt_ports: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "interface_style": self.interface_style.value,
            "data_bus_bits": self.data_bus_bits,
            "supports_backpressure": self.supports_backpressure,
            "flow_control": self.flow_control.value,
            "separate_ad_text_channels": self.separate_ad_text_channels,
            "separate_encrypt_decrypt_ports": self.separate_encrypt_decrypt_ports,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "IOConfig":
        return cls(
            interface_style=InterfaceStyle(str(data["interface_style"])),
            data_bus_bits=int(data["data_bus_bits"]),
            supports_backpressure=bool(data["supports_backpressure"]),
            flow_control=FlowControlStyle(str(data.get("flow_control", FlowControlStyle.VALID_READY.value))),
            separate_ad_text_channels=bool(data.get("separate_ad_text_channels", False)),
            separate_encrypt_decrypt_ports=bool(data.get("separate_encrypt_decrypt_ports", False)),
        )


@dataclass(frozen=True, slots=True)
class SecurityConfig:
    side_channel_protection: SideChannelProtection
    constant_time_control: bool
    clear_state_on_done: bool = True
    duplicate_control_fsm_checks: bool = False
    randomness_bits_per_cycle: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "side_channel_protection": self.side_channel_protection.value,
            "constant_time_control": self.constant_time_control,
            "clear_state_on_done": self.clear_state_on_done,
            "duplicate_control_fsm_checks": self.duplicate_control_fsm_checks,
            "randomness_bits_per_cycle": self.randomness_bits_per_cycle,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SecurityConfig":
        return cls(
            side_channel_protection=SideChannelProtection(str(data["side_channel_protection"])),
            constant_time_control=bool(data["constant_time_control"]),
            clear_state_on_done=bool(data.get("clear_state_on_done", True)),
            duplicate_control_fsm_checks=bool(data.get("duplicate_control_fsm_checks", False)),
            randomness_bits_per_cycle=int(data.get("randomness_bits_per_cycle", 0)),
        )


@dataclass(frozen=True, slots=True)
class RtlConfig:
    language: RtlLanguage = RtlLanguage.SYSTEMVERILOG
    reset_style: ResetStyle = ResetStyle.ASYNC_ACTIVE_LOW
    emit_separate_files: bool = True
    include_reference_comments: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language.value,
            "reset_style": self.reset_style.value,
            "emit_separate_files": self.emit_separate_files,
            "include_reference_comments": self.include_reference_comments,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "RtlConfig":
        if data is None:
            return cls()
        return cls(
            language=RtlLanguage(str(data.get("language", RtlLanguage.SYSTEMVERILOG.value))),
            reset_style=ResetStyle(str(data.get("reset_style", ResetStyle.ASYNC_ACTIVE_LOW.value))),
            emit_separate_files=bool(data.get("emit_separate_files", True)),
            include_reference_comments=bool(data.get("include_reference_comments", True)),
        )


@dataclass(frozen=True, slots=True)
class ImplementationConfig:
    name: str
    target: TargetTechnology
    topology: DatapathTopology
    permutation: PermutationConfig
    io: IOConfig
    security: SecurityConfig
    description: str
    algorithm: AlgorithmConfig = field(default_factory=AlgorithmConfig)
    datapath: DatapathConfig = field(default_factory=DatapathConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    padding: PaddingConfig = field(default_factory=PaddingConfig)
    rtl: RtlConfig = field(default_factory=RtlConfig)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "target": self.target.value,
            "algorithm": self.algorithm.to_dict(),
            "topology": self.topology.to_dict(),
            "permutation": self.permutation.to_dict(),
            "datapath": self.datapath.to_dict(),
            "context": self.context.to_dict(),
            "padding": self.padding.to_dict(),
            "io": self.io.to_dict(),
            "security": self.security.to_dict(),
            "rtl": self.rtl.to_dict(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ImplementationConfig":
        return cls(
            name=str(data["name"]),
            target=TargetTechnology(str(data["target"])),
            algorithm=AlgorithmConfig.from_dict(data.get("algorithm")),
            topology=DatapathTopology.from_dict(data["topology"]),
            permutation=PermutationConfig.from_dict(data["permutation"]),
            datapath=DatapathConfig.from_dict(data.get("datapath")),
            context=ContextConfig.from_dict(data.get("context")),
            padding=PaddingConfig.from_dict(data.get("padding")),
            io=IOConfig.from_dict(data["io"]),
            security=SecurityConfig.from_dict(data["security"]),
            rtl=RtlConfig.from_dict(data.get("rtl")),
            description=str(data.get("description", "")),
        )

    def write_json(self, path: str | Path) -> None:
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def read_json(cls, path: str | Path) -> "ImplementationConfig":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
