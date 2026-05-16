from pathlib import Path

from ascon_arch.config import ImplementationConfig
from ascon_arch.validation import validate_config
from ascon_hwmodel.p12 import ascon_p12
from ascon_hwmodel.state import AsconState


ROOT = Path(__file__).resolve().parents[1]
BOARD_DIR = ROOT / "boards" / "tangnano9k" / "ascon_p12_pipeline"


def test_tangnano9k_p12_pipeline_files_exist() -> None:
    expected = [
        BOARD_DIR / "Makefile",
        BOARD_DIR / "tangnano9k_ascon_p12_pipeline.cst",
        BOARD_DIR / "rtl" / "ascon_round_comb.v",
        BOARD_DIR / "rtl" / "ascon_p12_pipeline.v",
        BOARD_DIR / "rtl" / "tangnano9k_ascon_p12_pipeline_top.v",
    ]
    for path in expected:
        assert path.exists(), path


def test_tangnano9k_config_validates() -> None:
    cfg = ImplementationConfig.read_json(ROOT / "configs" / "fpga" / "tangnano9k_p12_pipeline.json")
    validate_config(cfg)


def test_tangnano9k_p12_zero_expected_matches_model() -> None:
    top = (BOARD_DIR / "rtl" / "tangnano9k_ascon_p12_pipeline_top.v").read_text().lower().replace("_", "")
    expected = ascon_p12(AsconState.zero()).to_int()
    assert f"320'h{expected:080x}" in top
