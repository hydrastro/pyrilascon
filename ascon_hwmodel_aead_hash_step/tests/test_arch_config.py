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
