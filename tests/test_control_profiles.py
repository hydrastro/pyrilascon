from dataclasses import replace
from pathlib import Path

import pytest

from ascon_arch import (
    ConfigValidationError,
    ControlProfile,
    estimate_control,
    asic_dual_enc_dec_cores_config,
    config_with_control_profile,
    fpga_m_pipelines_n_contexts_config,
    fpga_n_parallel_engines_config,
    validate_config,
    write_design_product,
)


def test_asic_default_control_is_hardcoded_fsm() -> None:
    config = asic_dual_enc_dec_cores_config()
    validate_config(config)
    assert config.control.profile == ControlProfile.HARDCODED_FSM
    assert estimate_control(config.control).area_class == "very_low"


def test_fpga_default_control_is_axi_stream_microcoded_hybrid() -> None:
    config = fpga_n_parallel_engines_config(4)
    validate_config(config)
    assert config.control.profile == ControlProfile.AXI_STREAM_MICROCODED_HYBRID
    assert config.control.supports_runtime_algorithm_select
    assert config.control.scheduler_required


def test_fpga_dma_profile_is_valid_descriptor_wrapper() -> None:
    config = config_with_control_profile(fpga_n_parallel_engines_config(4), ControlProfile.DMA_FED)
    validate_config(config)
    assert config.control.supports_dma
    assert config.control.supports_descriptors


def test_hardcoded_fsm_rejects_multi_algorithm_fpga_config() -> None:
    config = config_with_control_profile(fpga_n_parallel_engines_config(4), ControlProfile.HARDCODED_FSM)
    with pytest.raises(ConfigValidationError):
        validate_config(config)


def test_pipeline_context_topology_requires_scheduler_capable_control() -> None:
    config = fpga_m_pipelines_n_contexts_config(2, 12)
    bad = replace(config, control=config_with_control_profile(config, ControlProfile.CSR_REGISTER_FILE).control)
    with pytest.raises(ConfigValidationError):
        validate_config(bad)


def test_generated_product_contains_control_module_and_metadata(tmp_path: Path) -> None:
    config = fpga_m_pipelines_n_contexts_config(2, 12)
    write_design_product(config, tmp_path)
    rtl_root = tmp_path / config.name / "rtl"
    assert (rtl_root / f"ascon_{config.name}_control.sv").exists()
    manifest = (tmp_path / config.name / "metadata" / "module_manifest.json").read_text(encoding="utf-8")
    metrics = (tmp_path / config.name / "metadata" / "expected_metrics.json").read_text(encoding="utf-8")
    assert "control_profile" in manifest
    assert "axi_stream_microcoded_hybrid" in metrics
