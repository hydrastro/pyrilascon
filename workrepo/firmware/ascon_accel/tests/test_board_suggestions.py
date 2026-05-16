from pathlib import Path
import json

from ascon_arch import BoardClass, all_board_suggestions, board_suggestions
from ascon_arch.board_suggestions import BoardSuggestionProfile

ROOT = Path(__file__).resolve().parents[1]


def test_board_suggestions_cover_requested_fpga_classes() -> None:
    profiles = {profile.board_class for profile in all_board_suggestions()}
    assert {
        BoardClass.TANG_NANO_9K,
        BoardClass.TANG_NANO_20K,
        BoardClass.XILINX_LOW,
        BoardClass.XILINX_MEDIUM,
        BoardClass.XILINX_HIGH,
    }.issubset(profiles)


def test_tangnano9k_suggestions_prioritize_max_throughput_candidates() -> None:
    profile = board_suggestions(BoardClass.TANG_NANO_9K)
    names = [candidate.name for candidate in sorted(profile.candidates, key=lambda item: item.priority)]
    assert names[0] == "tn9k_axis128_8rpc_single_context"
    assert names[1] == "tn9k_axis128_4rpc_single_context"
    assert all(candidate.data_plane.startswith("axi_stream") for candidate in profile.candidates)


def test_xilinx_high_suggestions_scale_pipelines_and_contexts() -> None:
    profile = board_suggestions(BoardClass.XILINX_HIGH)
    first = min(profile.candidates, key=lambda item: item.priority)
    assert first.top_level_profile == "m_pipelines_n_contexts"
    assert first.permutation_profile == "fully_pipelined"
    assert first.engine_count >= 4
    assert first.contexts_per_engine >= 12


def test_generated_board_suggestion_json_files_are_in_sync() -> None:
    for profile in all_board_suggestions():
        path = ROOT / "docs" / "board_suggestions" / f"{profile.board_class.value}_suggestions.json"
        assert path.exists()
        loaded = BoardSuggestionProfile.from_dict(json.loads(path.read_text(encoding="utf-8")))
        assert loaded == profile
