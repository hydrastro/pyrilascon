from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import json

from ascon_arch.enums import (
    ArchitectureFamily,
    EngineCapability,
    InterfaceStyle,
    PermutationStyle,
    SBoxStyle,
    SideChannelProtection,
    TargetTechnology,
)


@dataclass(frozen=True, slots=True)
class PermutationConfig:
    style: PermutationStyle
    sbox_style: SBoxStyle
    rounds_per_cycle: int
    pipeline_stages: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "style": self.style.value,
            "sbox_style": self.sbox_style.value,
            "rounds_per_cycle": self.rounds_per_cycle,
            "pipeline_stages": self.pipeline_stages,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PermutationConfig":
        return cls(
            style=PermutationStyle(str(data["style"])),
            sbox_style=SBoxStyle(str(data["sbox_style"])),
            rounds_per_cycle=int(data["rounds_per_cycle"]),
            pipeline_stages=int(data["pipeline_stages"]),
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "interface_style": self.interface_style.value,
            "data_bus_bits": self.data_bus_bits,
            "supports_backpressure": self.supports_backpressure,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "IOConfig":
        return cls(
            interface_style=InterfaceStyle(str(data["interface_style"])),
            data_bus_bits=int(data["data_bus_bits"]),
            supports_backpressure=bool(data["supports_backpressure"]),
        )


@dataclass(frozen=True, slots=True)
class SecurityConfig:
    side_channel_protection: SideChannelProtection
    constant_time_control: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "side_channel_protection": self.side_channel_protection.value,
            "constant_time_control": self.constant_time_control,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SecurityConfig":
        return cls(
            side_channel_protection=SideChannelProtection(str(data["side_channel_protection"])),
            constant_time_control=bool(data["constant_time_control"]),
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "target": self.target.value,
            "topology": self.topology.to_dict(),
            "permutation": self.permutation.to_dict(),
            "io": self.io.to_dict(),
            "security": self.security.to_dict(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ImplementationConfig":
        return cls(
            name=str(data["name"]),
            target=TargetTechnology(str(data["target"])),
            topology=DatapathTopology.from_dict(data["topology"]),
            permutation=PermutationConfig.from_dict(data["permutation"]),
            io=IOConfig.from_dict(data["io"]),
            security=SecurityConfig.from_dict(data["security"]),
            description=str(data.get("description", "")),
        )

    def write_json(self, path: str | Path) -> None:
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def read_json(cls, path: str | Path) -> "ImplementationConfig":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
