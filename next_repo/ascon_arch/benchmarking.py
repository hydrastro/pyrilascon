from dataclasses import dataclass
from math import ceil
from typing import Any

from ascon_arch.config import ImplementationConfig, PermutationConfig
from ascon_arch.enums import PermutationStyle
from ascon_arch.permutation_planning import cycles_for_permutation, estimate_permutation

AEAD128_RATE_BYTES = 16
AEAD128_RATE_BITS = 128


@dataclass(frozen=True, slots=True)
class AeadBenchmarkShape:
    """Message shape used for architecture-level AEAD throughput estimates."""

    ad_bytes: int
    text_bytes: int

    def __post_init__(self) -> None:
        if self.ad_bytes < 0 or self.text_bytes < 0:
            raise ValueError("benchmark byte counts must be non-negative")

    @property
    def ad_blocks(self) -> int:
        # Ascon-AEAD128 processes padded associated data only when AD is non-empty.
        if self.ad_bytes == 0:
            return 0
        return ceil((self.ad_bytes + 1) / AEAD128_RATE_BYTES)

    @property
    def text_blocks(self) -> int:
        # Plaintext/ciphertext is always padded; an empty message still has one final padded block.
        return ceil((self.text_bytes + 1) / AEAD128_RATE_BYTES)

    @property
    def payload_bits(self) -> int:
        return self.text_bytes * 8


@dataclass(frozen=True, slots=True)
class AeadCycleEstimate:
    """Approximate cycle model for one AEAD128 operation.

    This is an architecture-planning estimate. Backend-specific FSM overhead,
    FIFO stalls, stream scheduler bubbles, and CPU/DMA setup costs should be
    measured on hardware and stored in BenchmarkResult.
    """

    init_cycles: int
    associated_data_cycles: int
    text_cycles: int
    final_cycles: int
    data_movement_cycles: int
    total_cycles: int
    sustained_block_interval_cycles: int

    def to_dict(self) -> dict[str, int]:
        return {
            "init_cycles": self.init_cycles,
            "associated_data_cycles": self.associated_data_cycles,
            "text_cycles": self.text_cycles,
            "final_cycles": self.final_cycles,
            "data_movement_cycles": self.data_movement_cycles,
            "total_cycles": self.total_cycles,
            "sustained_block_interval_cycles": self.sustained_block_interval_cycles,
        }


@dataclass(frozen=True, slots=True)
class ThroughputEstimate:
    """Clock-based throughput estimate for one benchmark shape."""

    clock_mhz: float
    payload_bits: int
    cycles: int
    cycles_per_byte: float
    operation_throughput_mbps: float
    sustained_payload_mbps: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "clock_mhz": self.clock_mhz,
            "payload_bits": self.payload_bits,
            "cycles": self.cycles,
            "cycles_per_byte": self.cycles_per_byte,
            "operation_throughput_mbps": self.operation_throughput_mbps,
            "sustained_payload_mbps": self.sustained_payload_mbps,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Machine-readable measured benchmark record.

    These records are intended for JSON reports produced by firmware, testbenches,
    or board scripts. They deliberately include both measured hardware cycles and
    an optional software baseline so the required speedup gate is explicit.
    """

    design_name: str
    board: str
    algorithm: str
    operation: str
    clock_mhz: float
    ad_bytes: int
    text_bytes: int
    hardware_cycles: int
    software_cycles: int | None = None
    valid: bool = True
    notes: tuple[str, ...] = ()

    @property
    def cycles_per_byte(self) -> float:
        if self.text_bytes == 0:
            return float(self.hardware_cycles)
        return self.hardware_cycles / self.text_bytes

    @property
    def hardware_throughput_mbps(self) -> float:
        if self.hardware_cycles <= 0:
            return 0.0
        return (self.text_bytes * 8 * self.clock_mhz) / self.hardware_cycles

    @property
    def speedup_vs_software(self) -> float | None:
        if self.software_cycles is None or self.hardware_cycles <= 0:
            return None
        return self.software_cycles / self.hardware_cycles

    @property
    def beats_software(self) -> bool | None:
        speedup = self.speedup_vs_software
        if speedup is None:
            return None
        return speedup > 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "design_name": self.design_name,
            "board": self.board,
            "algorithm": self.algorithm,
            "operation": self.operation,
            "clock_mhz": self.clock_mhz,
            "ad_bytes": self.ad_bytes,
            "text_bytes": self.text_bytes,
            "hardware_cycles": self.hardware_cycles,
            "software_cycles": self.software_cycles,
            "cycles_per_byte": self.cycles_per_byte,
            "hardware_throughput_mbps": self.hardware_throughput_mbps,
            "speedup_vs_software": self.speedup_vs_software,
            "beats_software": self.beats_software,
            "valid": self.valid,
            "notes": list(self.notes),
        }


def aead128_cycle_estimate(
    permutation: PermutationConfig,
    shape: AeadBenchmarkShape,
    *,
    data_bus_bits: int = AEAD128_RATE_BITS,
    contexts_available: int = 1,
) -> AeadCycleEstimate:
    """Estimate cycles for one AEAD128 encrypt/decrypt operation."""
    p8 = _effective_p8_interval(permutation, contexts_available)
    p12 = cycles_for_permutation(12, permutation)
    init_cycles = p12
    associated_data_cycles = shape.ad_blocks * p8
    # The last text block goes directly into finalization; previous text blocks use p8.
    text_cycles = max(0, shape.text_blocks - 1) * p8
    final_cycles = p12
    data_movement_cycles = _data_movement_cycles(shape, data_bus_bits)
    total_cycles = init_cycles + associated_data_cycles + text_cycles + final_cycles + data_movement_cycles
    return AeadCycleEstimate(
        init_cycles=init_cycles,
        associated_data_cycles=associated_data_cycles,
        text_cycles=text_cycles,
        final_cycles=final_cycles,
        data_movement_cycles=data_movement_cycles,
        total_cycles=total_cycles,
        sustained_block_interval_cycles=p8,
    )


def throughput_estimate(
    permutation: PermutationConfig,
    shape: AeadBenchmarkShape,
    *,
    clock_mhz: float,
    data_bus_bits: int = AEAD128_RATE_BITS,
    contexts_available: int = 1,
) -> ThroughputEstimate:
    cycles = aead128_cycle_estimate(
        permutation,
        shape,
        data_bus_bits=data_bus_bits,
        contexts_available=contexts_available,
    )
    if shape.text_bytes == 0:
        cycles_per_byte = float(cycles.total_cycles)
        op_mbps = 0.0
    else:
        cycles_per_byte = cycles.total_cycles / shape.text_bytes
        op_mbps = (shape.payload_bits * clock_mhz) / cycles.total_cycles
    sustained = (AEAD128_RATE_BITS * clock_mhz) / max(1, cycles.sustained_block_interval_cycles)
    return ThroughputEstimate(
        clock_mhz=clock_mhz,
        payload_bits=shape.payload_bits,
        cycles=cycles.total_cycles,
        cycles_per_byte=cycles_per_byte,
        operation_throughput_mbps=op_mbps,
        sustained_payload_mbps=sustained,
    )


def estimate_config_throughput(
    config: ImplementationConfig,
    *,
    clock_mhz: float,
    ad_bytes: int = 32,
    text_bytes: int = 1024,
) -> dict[str, Any]:
    """Return a JSON-friendly benchmark estimate for a generated config."""
    shape = AeadBenchmarkShape(ad_bytes=ad_bytes, text_bytes=text_bytes)
    estimate = throughput_estimate(
        config.permutation,
        shape,
        clock_mhz=clock_mhz,
        data_bus_bits=config.io.data_bus_bits,
        contexts_available=max(1, config.context.contexts_per_engine),
    )
    return {
        "design_name": config.name,
        "target": config.target.value,
        "clock_mhz": clock_mhz,
        "shape": {"ad_bytes": ad_bytes, "text_bytes": text_bytes},
        "permutation": estimate_permutation(config.permutation).to_dict(),
        "throughput": estimate.to_dict(),
    }


def _effective_p8_interval(permutation: PermutationConfig, contexts_available: int) -> int:
    if permutation.style in (PermutationStyle.ROUND_PIPELINED, PermutationStyle.FULLY_UNROLLED_PIPELINED):
        required_contexts = max(1, permutation.pipeline_stages)
        if contexts_available >= required_contexts:
            return max(1, permutation.pipeline_initiation_interval or 1)
        # Not enough independent contexts: each logical context must wait for the visible p8 latency.
        return cycles_for_permutation(8, permutation)
    return cycles_for_permutation(8, permutation)


def _data_movement_cycles(shape: AeadBenchmarkShape, data_bus_bits: int) -> int:
    if data_bus_bits <= 0 or data_bus_bits % 8 != 0:
        raise ValueError("data_bus_bits must be a positive byte-aligned width")
    bus_bytes = data_bus_bits // 8
    return ceil(shape.ad_bytes / bus_bytes) + ceil(shape.text_bytes / bus_bytes)
