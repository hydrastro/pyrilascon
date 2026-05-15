from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
import json


class BoardClass(str, Enum):
    TANG_NANO_9K = "tangnano9k"
    TANG_NANO_20K = "tangnano20k"
    XILINX_LOW = "xilinx_low"
    XILINX_MEDIUM = "xilinx_medium"
    XILINX_HIGH = "xilinx_high"
    EXTREME = "extreme"


@dataclass(frozen=True, slots=True)
class BoardCandidate:
    name: str
    priority: int
    summary: str
    top_level_profile: str
    permutation_profile: str
    datapath_profile: str
    context_profile: str
    control_profile: str
    padding_profile: str
    security_profile: str
    data_plane: str
    engine_count: int = 1
    contexts_per_engine: int = 1
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "priority": self.priority,
            "summary": self.summary,
            "top_level_profile": self.top_level_profile,
            "permutation_profile": self.permutation_profile,
            "datapath_profile": self.datapath_profile,
            "context_profile": self.context_profile,
            "control_profile": self.control_profile,
            "padding_profile": self.padding_profile,
            "security_profile": self.security_profile,
            "data_plane": self.data_plane,
            "engine_count": self.engine_count,
            "contexts_per_engine": self.contexts_per_engine,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoardCandidate":
        return cls(
            name=str(data["name"]),
            priority=int(data["priority"]),
            summary=str(data["summary"]),
            top_level_profile=str(data["top_level_profile"]),
            permutation_profile=str(data["permutation_profile"]),
            datapath_profile=str(data["datapath_profile"]),
            context_profile=str(data["context_profile"]),
            control_profile=str(data["control_profile"]),
            padding_profile=str(data["padding_profile"]),
            security_profile=str(data["security_profile"]),
            data_plane=str(data["data_plane"]),
            engine_count=int(data.get("engine_count", 1)),
            contexts_per_engine=int(data.get("contexts_per_engine", 1)),
            notes=tuple(str(note) for note in data.get("notes", ())),
        )


@dataclass(frozen=True, slots=True)
class BoardSuggestionProfile:
    board_class: BoardClass
    goal: str
    assumptions: tuple[str, ...]
    candidates: tuple[BoardCandidate, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "board_class": self.board_class.value,
            "goal": self.goal,
            "assumptions": list(self.assumptions),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoardSuggestionProfile":
        return cls(
            board_class=BoardClass(str(data["board_class"])),
            goal=str(data["goal"]),
            assumptions=tuple(str(item) for item in data.get("assumptions", ())),
            candidates=tuple(BoardCandidate.from_dict(item) for item in data.get("candidates", ())),
        )

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


MAX_THROUGHPUT_GOAL = "maximum_throughput_that_fits"


def tangnano9k_suggestions() -> BoardSuggestionProfile:
    return BoardSuggestionProfile(
        board_class=BoardClass.TANG_NANO_9K,
        goal=MAX_THROUGHPUT_GOAL,
        assumptions=(
            "Use the board as a proof vehicle, not as the architecture limit.",
            "Try the most aggressive candidate first, then fall back only if timing or fit fails.",
            "Keep the AXI Stream/CSR architecture stable even if the internal backend is smaller.",
        ),
        candidates=(
            BoardCandidate(
                name="tn9k_axis128_8rpc_single_context",
                priority=1,
                summary="Aggressive Tang Nano 9K candidate: 128-bit AXIS, p8 in 1 cycle, p12 in 2 cycles.",
                top_level_profile="single_core",
                permutation_profile="eight_rounds_per_cycle",
                datapath_profile="128_bit",
                context_profile="single_320_register",
                control_profile="axi_stream_microcoded_hybrid",
                padding_profile="streaming_final_bytemask",
                security_profile="none",
                data_plane="axi_stream_128",
                notes=("Use if timing and LUT utilization pass.", "Good stress test for the small device."),
            ),
            BoardCandidate(
                name="tn9k_axis128_4rpc_single_context",
                priority=2,
                summary="Safer high-throughput candidate: 128-bit AXIS and 4 rounds per cycle.",
                top_level_profile="single_core",
                permutation_profile="four_rounds_per_cycle",
                datapath_profile="128_bit",
                context_profile="single_320_register",
                control_profile="axi_stream_microcoded_hybrid",
                padding_profile="streaming_final_bytemask",
                security_profile="none",
                data_plane="axi_stream_128",
                notes=("Recommended fallback if 8RPC fails timing or fit.",),
            ),
            BoardCandidate(
                name="tn9k_axis128_1rpc_known_good",
                priority=3,
                summary="Known-good fallback preserving the same interface with one round per cycle.",
                top_level_profile="single_core",
                permutation_profile="one_round_per_cycle",
                datapath_profile="128_bit",
                context_profile="single_320_register",
                control_profile="axi_stream_microcoded_hybrid",
                padding_profile="streaming_final_bytemask",
                security_profile="none",
                data_plane="axi_stream_128",
                notes=("Use for debugging firmware/AXIS integration, not as the final FPGA architecture.",),
            ),
        ),
    )


def tangnano20k_suggestions() -> BoardSuggestionProfile:
    return BoardSuggestionProfile(
        board_class=BoardClass.TANG_NANO_20K,
        goal=MAX_THROUGHPUT_GOAL,
        assumptions=(
            "Larger Gowin device should allow either 8RPC with more buffering or a small pipelined context engine.",
            "Use 128-bit AXI Stream as the default data plane.",
        ),
        candidates=(
            BoardCandidate(
                name="tn20k_axis128_fully_pipelined_12ctx",
                priority=1,
                summary="One fully pipelined permutation with 12 interleaved contexts.",
                top_level_profile="one_pipelined_permutation_n_contexts",
                permutation_profile="fully_pipelined",
                datapath_profile="128_bit",
                context_profile="fpga_bram_lutram",
                control_profile="axi_stream_microcoded_hybrid",
                padding_profile="streaming_final_bytemask",
                security_profile="none",
                data_plane="axi_stream_128",
                contexts_per_engine=12,
                notes=("Best match for context-interleaved high-throughput FPGA architecture.",),
            ),
            BoardCandidate(
                name="tn20k_axis128_8rpc_single_or_small_context",
                priority=2,
                summary="8 rounds per cycle with optional small context interleaving.",
                top_level_profile="single_core",
                permutation_profile="eight_rounds_per_cycle",
                datapath_profile="128_bit",
                context_profile="multi_context_registers",
                control_profile="axi_stream_microcoded_hybrid",
                padding_profile="streaming_final_bytemask",
                security_profile="none",
                data_plane="axi_stream_128",
                contexts_per_engine=4,
            ),
            BoardCandidate(
                name="tn20k_axis128_two_identical_cores",
                priority=3,
                summary="Two complete AEAD cores for simple packet-level scaling.",
                top_level_profile="n_identical_aead_cores",
                permutation_profile="four_rounds_per_cycle",
                datapath_profile="128_bit",
                context_profile="separate_state_per_core",
                control_profile="axi_stream_microcoded_hybrid",
                padding_profile="streaming_final_bytemask",
                security_profile="fpga_fault_detect_rand_counter_consttime_tag",
                data_plane="axi_stream_128",
                engine_count=2,
            ),
        ),
    )


def xilinx_low_suggestions() -> BoardSuggestionProfile:
    return BoardSuggestionProfile(
        board_class=BoardClass.XILINX_LOW,
        goal=MAX_THROUGHPUT_GOAL,
        assumptions=("Prefer AXI-Lite control plus AXI Stream data on Xilinx systems.",),
        candidates=(
            BoardCandidate(
                name="xilinx_low_axis128_8rpc",
                priority=1,
                summary="128-bit AXIS and 8RPC for Artix/Spartan-class devices if timing closes.",
                top_level_profile="single_core",
                permutation_profile="eight_rounds_per_cycle",
                datapath_profile="128_bit",
                context_profile="single_320_register",
                control_profile="axi_stream_microcoded_hybrid",
                padding_profile="streaming_final_bytemask",
                security_profile="none",
                data_plane="axi_stream_128",
            ),
            BoardCandidate(
                name="xilinx_low_axis128_fully_pipelined_4ctx",
                priority=2,
                summary="Small context-interleaved pipeline for low-end Xilinx parts.",
                top_level_profile="one_pipelined_permutation_n_contexts",
                permutation_profile="fully_pipelined",
                datapath_profile="128_bit",
                context_profile="multi_context_registers",
                control_profile="axi_stream_microcoded_hybrid",
                padding_profile="streaming_final_bytemask",
                security_profile="none",
                data_plane="axi_stream_128",
                contexts_per_engine=4,
            ),
        ),
    )


def xilinx_medium_suggestions() -> BoardSuggestionProfile:
    return BoardSuggestionProfile(
        board_class=BoardClass.XILINX_MEDIUM,
        goal=MAX_THROUGHPUT_GOAL,
        assumptions=("Expect AXI DMA or a packet scheduler to become part of the throughput path.",),
        candidates=(
            BoardCandidate(
                name="xilinx_medium_one_pipeline_12ctx",
                priority=1,
                summary="One fully pipelined permutation with 12 contexts and AXI Stream packet scheduling.",
                top_level_profile="one_pipelined_permutation_n_contexts",
                permutation_profile="fully_pipelined",
                datapath_profile="128_bit",
                context_profile="fpga_bram_lutram",
                control_profile="axi_stream_microcoded_hybrid",
                padding_profile="streaming_final_bytemask",
                security_profile="fpga_fault_detect_rand_counter_consttime_tag",
                data_plane="axi_stream_128_dma",
                contexts_per_engine=12,
            ),
            BoardCandidate(
                name="xilinx_medium_two_pipelines_12ctx",
                priority=2,
                summary="Two independent permutation pipelines, each with 12 contexts.",
                top_level_profile="m_pipelines_n_contexts",
                permutation_profile="fully_pipelined",
                datapath_profile="128_bit",
                context_profile="fpga_bram_lutram",
                control_profile="dma_fed",
                padding_profile="streaming_final_bytemask",
                security_profile="fpga_fault_detect_rand_counter_consttime_tag",
                data_plane="axi_stream_128_dma",
                engine_count=2,
                contexts_per_engine=12,
            ),
        ),
    )


def xilinx_high_suggestions() -> BoardSuggestionProfile:
    return BoardSuggestionProfile(
        board_class=BoardClass.XILINX_HIGH,
        goal=MAX_THROUGHPUT_GOAL,
        assumptions=(
            "I/O and packet scheduling are likely to become the bottleneck before the permutation logic.",
            "Scale by increasing pipeline count and stream aggregation width.",
        ),
        candidates=(
            BoardCandidate(
                name="xilinx_high_four_pipelines_12ctx_axis256",
                priority=1,
                summary="Four fully pipelined engines with 12 contexts each and aggregated 256-bit stream ingress.",
                top_level_profile="m_pipelines_n_contexts",
                permutation_profile="fully_pipelined",
                datapath_profile="128_bit",
                context_profile="fpga_bram_lutram",
                control_profile="dma_fed",
                padding_profile="streaming_final_bytemask",
                security_profile="fpga_fault_detect_rand_counter_consttime_tag",
                data_plane="axi_stream_256_dma",
                engine_count=4,
                contexts_per_engine=12,
            ),
            BoardCandidate(
                name="xilinx_high_eight_pipelines_12ctx_extreme",
                priority=2,
                summary="Extreme scaling point: eight pipelines and 96 contexts total.",
                top_level_profile="m_pipelines_n_contexts",
                permutation_profile="fully_pipelined",
                datapath_profile="128_bit",
                context_profile="fpga_bram_lutram",
                control_profile="dma_fed",
                padding_profile="streaming_final_bytemask",
                security_profile="fpga_fault_detect_rand_counter_consttime_tag",
                data_plane="multi_axi_stream_dma",
                engine_count=8,
                contexts_per_engine=12,
                notes=("Use only when the host/DMA subsystem can feed enough independent packets.",),
            ),
        ),
    )


SUGGESTION_BUILDERS = {
    BoardClass.TANG_NANO_9K: tangnano9k_suggestions,
    BoardClass.TANG_NANO_20K: tangnano20k_suggestions,
    BoardClass.XILINX_LOW: xilinx_low_suggestions,
    BoardClass.XILINX_MEDIUM: xilinx_medium_suggestions,
    BoardClass.XILINX_HIGH: xilinx_high_suggestions,
}


def board_suggestions(board_class: BoardClass | str) -> BoardSuggestionProfile:
    board = board_class if isinstance(board_class, BoardClass) else BoardClass(str(board_class))
    return SUGGESTION_BUILDERS[board]()


def all_board_suggestions() -> tuple[BoardSuggestionProfile, ...]:
    return tuple(builder() for builder in SUGGESTION_BUILDERS.values())


def write_board_suggestions(root: Path) -> list[Path]:
    written: list[Path] = []
    for profile in all_board_suggestions():
        path = root / f"{profile.board_class.value}_suggestions.json"
        profile.write_json(path)
        written.append(path)
    return written
