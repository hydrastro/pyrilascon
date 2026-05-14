from pathlib import Path

import pytest

from ascon_arch import (
    ConfigValidationError,
    TopLevelProfile,
    asic_dual_enc_dec_cores_config,
    config_with_top_level_profile,
    estimate_top_level,
    fpga_m_pipelines_n_contexts_config,
    fpga_n_parallel_engines_config,
    fpga_one_pipelined_permutation_n_contexts_config,
    validate_config,
    write_design_product,
)


def test_asic_dual_enc_dec_core_profile_matches_user_choice() -> None:
    config = asic_dual_enc_dec_cores_config()
    validate_config(config)
    assert config.topology.top_level_profile == TopLevelProfile.DUAL_ENC_DEC_CORES
    assert config.topology.aead_core_count == 2
    assert config.topology.expected_parallel_operations() == 2
    assert estimate_top_level(config).throughput_class == "independent_encrypt_and_decrypt"


def test_fpga_n_identical_aead_cores_profile_matches_simple_scaling_choice() -> None:
    config = fpga_n_parallel_engines_config(6)
    validate_config(config)
    assert config.topology.top_level_profile == TopLevelProfile.N_IDENTICAL_AEAD_CORES
    assert config.topology.aead_core_count == 6
    assert config.topology.expected_parallel_operations() == 6
    assert estimate_top_level(config).throughput_class == "near_linear_packet_parallel_scaling"


def test_fpga_one_pipelined_permutation_with_contexts_profile() -> None:
    config = fpga_one_pipelined_permutation_n_contexts_config(12)
    validate_config(config)
    assert config.topology.top_level_profile == TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS
    assert config.topology.permutation_pipeline_count == 1
    assert config.topology.contexts_per_pipeline == 12
    assert config.context.context_count == 12
    assert estimate_top_level(config).scheduling_class == "single_pipeline_context_interleaving"


def test_fpga_m_pipelines_n_contexts_profile() -> None:
    config = fpga_m_pipelines_n_contexts_config(4, 12)
    validate_config(config)
    assert config.topology.top_level_profile == TopLevelProfile.M_PIPELINES_N_CONTEXTS
    assert config.topology.permutation_pipeline_count == 4
    assert config.topology.contexts_per_pipeline == 12
    assert config.context.context_count == 48
    assert estimate_top_level(config).area_class == "very_high"


def test_invalid_single_pipeline_profile_without_contexts_is_rejected() -> None:
    base = fpga_n_parallel_engines_config(4)
    bad = config_with_top_level_profile(
        base,
        TopLevelProfile.ONE_PIPELINED_PERMUTATION_N_CONTEXTS,
        contexts_per_pipeline=1,
    )
    with pytest.raises(ConfigValidationError):
        validate_config(bad)


def test_generated_product_records_top_level_metadata(tmp_path: Path) -> None:
    config = fpga_m_pipelines_n_contexts_config(2, 12)
    write_design_product(config, tmp_path)
    manifest = (tmp_path / config.name / "metadata" / "module_manifest.json").read_text(encoding="utf-8")
    top = (tmp_path / config.name / "rtl" / f"ascon_{config.name}_top.sv").read_text(encoding="utf-8")
    assert "m_pipelines_n_contexts" in manifest
    assert "PERM_PIPELINE_COUNT" in top
    assert "gen_perm_pipeline" in top
