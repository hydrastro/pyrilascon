from pathlib import Path

import pytest

from ascon_arch import (
    ConfigValidationError,
    LengthHandling,
    PaddingProfile,
    TargetTechnology,
    asic_dual_enc_dec_cores_config,
    config_with_padding_profile,
    estimate_padding,
    final_bytemask_width_for_bus,
    fpga_n_parallel_engines_config,
    fpga_one_pipelined_permutation_n_contexts_config,
    padding_config_for_profile,
    validate_config,
    write_design_product,
)
from dataclasses import replace


def test_asic_default_padding_is_rtl_performed() -> None:
    config = asic_dual_enc_dec_cores_config()
    validate_config(config)
    assert config.padding.profile == PaddingProfile.RTL_PERFORMED
    assert config.padding.length_handling == LengthHandling.INTERNAL_BYTE_COUNTER
    assert config.padding.pad_in_core is True
    assert config.padding.final_bytemask is False
    assert estimate_padding(config.padding).area_class == "medium"


def test_fpga_default_padding_is_streaming_final_bytemask() -> None:
    config = fpga_n_parallel_engines_config(4)
    validate_config(config)
    assert config.padding.profile == PaddingProfile.STREAMING_FINAL_BYTEMASK
    assert config.padding.length_handling == LengthHandling.STREAMING_FINAL_BYTEMASK
    assert config.padding.final_bytemask is True
    assert config.padding.final_bytemask_width == 64
    assert estimate_padding(config.padding).streaming_efficiency == "excellent_streaming"


def test_final_bytemask_width_tracks_bus_width_when_topology_changes() -> None:
    config = fpga_one_pipelined_permutation_n_contexts_config(12)
    validate_config(config)
    assert config.io.data_bus_bits == 128
    assert config.padding.final_bytemask_width == 16


def test_full_arbitrary_bytelength_requires_descriptor_length() -> None:
    padding = padding_config_for_profile(
        PaddingProfile.FULL_ARBITRARY_BYTELENGTH,
        TargetTechnology.FPGA,
        data_bus_bits=128,
    )
    assert padding.requires_total_length is True
    assert padding.length_handling == LengthHandling.DESCRIPTOR_BASED


def test_streaming_final_bytemask_width_must_match_bus_width() -> None:
    config = fpga_n_parallel_engines_config(4)
    bad = replace(config, padding=replace(config.padding, final_bytemask_width=1))
    with pytest.raises(ConfigValidationError):
        validate_config(bad)


def test_generated_product_contains_padding_module_and_metadata(tmp_path: Path) -> None:
    config = fpga_n_parallel_engines_config(4)
    write_design_product(config, tmp_path)
    rtl_root = tmp_path / config.name / "rtl"
    assert (rtl_root / f"ascon_{config.name}_padding.sv").exists()
    metrics = (tmp_path / config.name / "metadata" / "expected_metrics.json").read_text(encoding="utf-8")
    assert "padding_profile" in metrics
    assert "streaming_final_bytemask" in metrics


def test_padding_profile_override() -> None:
    config = config_with_padding_profile(fpga_n_parallel_engines_config(4), PaddingProfile.FULL_ARBITRARY_BYTELENGTH)
    validate_config(config)
    assert config.padding.length_handling == LengthHandling.DESCRIPTOR_BASED
    assert config.padding.requires_total_length is True


def test_final_bytemask_width_helper() -> None:
    assert final_bytemask_width_for_bus(128) == 16
    assert final_bytemask_width_for_bus(512) == 64
