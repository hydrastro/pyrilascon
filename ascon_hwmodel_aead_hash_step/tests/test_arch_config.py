from pathlib import Path

import pytest

from ascon_arch import (
    ArchitectureFamily,
    ConfigValidationError,
    ImplementationConfig,
    TargetTechnology,
    asic_two_datapaths_config,
    fpga_n_parallel_engines_config,
    top_module_name,
    validate_config,
    write_design_product,
)
from ascon_arch.config import DatapathTopology
from ascon_arch.enums import EngineCapability


def test_asic_two_datapaths_preset_matches_user_choice() -> None:
    config = asic_two_datapaths_config()
    validate_config(config)
    assert config.target == TargetTechnology.ASIC
    assert config.topology.family == ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS
    assert config.topology.engine_count == 1
    assert config.topology.encrypt_datapaths_per_engine == 1
    assert config.topology.decrypt_datapaths_per_engine == 1
    assert config.topology.expected_parallel_operations() == 2


def test_fpga_n_parallel_engines_preset_matches_user_choice() -> None:
    config = fpga_n_parallel_engines_config(8)
    validate_config(config)
    assert config.target == TargetTechnology.FPGA
    assert config.topology.family == ArchitectureFamily.PARALLEL_ENGINES
    assert config.topology.engine_count == 8
    assert config.topology.expected_parallel_operations() == 8
    assert config.io.data_bus_bits == 1024


def test_json_round_trip_for_arch_config(tmp_path: Path) -> None:
    config = fpga_n_parallel_engines_config(4)
    path = tmp_path / "config.json"
    config.write_json(path)
    loaded = ImplementationConfig.read_json(path)
    assert loaded == config


def test_invalid_parallel_engine_count_is_rejected() -> None:
    config = fpga_n_parallel_engines_config(1)
    with pytest.raises(ConfigValidationError):
        validate_config(config)


def test_invalid_separate_datapath_shape_is_rejected() -> None:
    config = asic_two_datapaths_config()
    bad_topology = DatapathTopology(
        family=ArchitectureFamily.SEPARATE_ENC_DEC_DATAPATHS,
        engine_count=1,
        engine_capability=EngineCapability.AEAD_ENCRYPT_DECRYPT,
        shared_encrypt_decrypt_datapath=True,
        encrypt_datapaths_per_engine=1,
        decrypt_datapaths_per_engine=1,
        shared_permutation_per_engine=False,
        mode_fsm_count_per_engine=2,
    )
    bad_config = ImplementationConfig(
        name=config.name,
        target=config.target,
        topology=bad_topology,
        permutation=config.permutation,
        io=config.io,
        security=config.security,
        description=config.description,
    )
    with pytest.raises(ConfigValidationError):
        validate_config(bad_config)


def test_write_design_product_creates_metadata_and_top_stub(tmp_path: Path) -> None:
    config = asic_two_datapaths_config()
    written = write_design_product(config, tmp_path)
    written_names = {path.name for path in written}
    assert "config_resolved.json" in written_names
    assert "module_manifest.json" in written_names
    assert f"{top_module_name(config)}.sv" in written_names
    top_file = tmp_path / config.name / "rtl" / f"{top_module_name(config)}.sv"
    assert "module ascon_asic_two_datapaths_top" in top_file.read_text(encoding="utf-8")

from ascon_arch import (
    AlgorithmFeature,
    ContextSchedulingStyle,
    DatapathWidth,
    LengthHandling,
    PaddingStrategy,
    StateStorageStyle,
    shared_datapath_config,
    shared_permutation_mode_fsm_config,
)


def test_fpga_parallel_engine_config_has_scalable_context_and_wide_io() -> None:
    config = fpga_n_parallel_engines_config(6)
    validate_config(config)
    assert AlgorithmFeature.HASH256 in config.algorithm.features
    assert AlgorithmFeature.XOF128 in config.algorithm.features
    assert AlgorithmFeature.CXOF128 in config.algorithm.features
    assert config.context.scheduling == ContextSchedulingStyle.DYNAMIC_QUEUE
    assert config.context.storage == StateStorageStyle.MULTI_CONTEXT_REGFILE
    assert config.context.context_count == 6
    assert config.context.context_id_bits == 3
    assert config.datapath.lane_width == DatapathWidth.W320
    assert config.io.data_bus_bits == 768


def test_shared_datapath_and_shared_permutation_presets_validate() -> None:
    for config in (
        shared_datapath_config(TargetTechnology.ASIC, name="asic_shared_datapath_test"),
        shared_permutation_mode_fsm_config(TargetTechnology.ASIC),
        shared_permutation_mode_fsm_config(TargetTechnology.FPGA),
    ):
        validate_config(config)


def test_generated_product_contains_architecture_module_boundaries(tmp_path: Path) -> None:
    config = asic_two_datapaths_config()
    write_design_product(config, tmp_path)
    rtl_root = tmp_path / config.name / "rtl"
    assert (rtl_root / "ascon_asic_two_datapaths_engine.sv").exists()
    assert (rtl_root / "ascon_asic_two_datapaths_encrypt_datapath.sv").exists()
    assert (rtl_root / "ascon_asic_two_datapaths_decrypt_datapath.sv").exists()
    manifest = (tmp_path / config.name / "metadata" / "module_manifest.json").read_text(encoding="utf-8")
    assert "expected_parallel_operations" in manifest
    assert "total_encrypt_datapaths" in manifest


def test_invalid_descriptor_stream_requires_descriptor_lengths() -> None:
    config = fpga_n_parallel_engines_config(4)
    bad = ImplementationConfig(
        name=config.name,
        target=config.target,
        topology=config.topology,
        permutation=config.permutation,
        io=config.io,
        security=config.security,
        description=config.description,
        algorithm=config.algorithm,
        datapath=config.datapath,
        context=config.context,
        padding=type(config.padding)(
            strategy=PaddingStrategy.INLINE_COMBINATIONAL,
            length_handling=LengthHandling.INTERNAL_BYTE_COUNTER,
            supports_partial_blocks=True,
            supports_bit_granular_lengths=False,
        ),
        rtl=config.rtl,
    )
    with pytest.raises(ConfigValidationError):
        validate_config(bad)
