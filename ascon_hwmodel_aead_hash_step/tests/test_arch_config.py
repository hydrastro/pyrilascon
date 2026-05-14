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
    assert config.datapath.lane_width == DatapathWidth.W128
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

from ascon_arch import (
    PermutationProfile,
    asic_two_datapaths_column_serial_config,
    asic_two_datapaths_two_rounds_per_cycle_config,
    cycles_for_permutation,
    estimate_permutation,
    fpga_n_parallel_engines_with_profile_config,
    permutation_config_for_profile,
)


def test_permutation_profile_cycle_estimates_match_user_notes() -> None:
    one = permutation_config_for_profile(PermutationProfile.ONE_ROUND_PER_CYCLE, TargetTechnology.ASIC)
    two = permutation_config_for_profile(PermutationProfile.TWO_ROUNDS_PER_CYCLE, TargetTechnology.ASIC)
    four = permutation_config_for_profile(PermutationProfile.FOUR_ROUNDS_PER_CYCLE, TargetTechnology.FPGA)
    eight = permutation_config_for_profile(PermutationProfile.EIGHT_ROUNDS_PER_CYCLE, TargetTechnology.FPGA)

    assert cycles_for_permutation(8, one) == 8
    assert cycles_for_permutation(12, one) == 12
    assert cycles_for_permutation(8, two) == 4
    assert cycles_for_permutation(12, two) == 6
    assert cycles_for_permutation(8, four) == 2
    assert cycles_for_permutation(12, four) == 3
    assert cycles_for_permutation(8, eight) == 1
    assert cycles_for_permutation(12, eight) == 2


def test_fully_pipelined_profile_requires_context_interleaving() -> None:
    config = fpga_n_parallel_engines_with_profile_config(8, PermutationProfile.FULLY_PIPELINED)
    validate_config(config)
    estimate = estimate_permutation(config.permutation)
    assert config.permutation.context_interleaving_required is True
    assert estimate.initiation_interval == 1
    assert estimate.contexts_for_full_pipeline == 12


def test_asic_2rpc_and_column_serial_presets_validate() -> None:
    two_rpc = asic_two_datapaths_two_rounds_per_cycle_config()
    column_serial = asic_two_datapaths_column_serial_config()
    validate_config(two_rpc)
    validate_config(column_serial)
    assert estimate_permutation(two_rpc.permutation).p12_cycles == 6
    assert estimate_permutation(column_serial.permutation).area_class == "very_small"


from ascon_arch import (
    DatapathProfile,
    asic_two_datapaths_with_datapath_profile_config,
    datapath_config_for_profile,
    estimate_datapath,
    fpga_n_parallel_engines_with_datapath_profile_config,
)


def test_datapath_width_profile_cycle_estimates_match_user_notes() -> None:
    w128 = estimate_datapath(datapath_config_for_profile(DatapathProfile.W128, TargetTechnology.FPGA))
    w64 = estimate_datapath(datapath_config_for_profile(DatapathProfile.W64, TargetTechnology.ASIC))
    w32 = estimate_datapath(datapath_config_for_profile(DatapathProfile.W32, TargetTechnology.ASIC))
    w16 = estimate_datapath(datapath_config_for_profile(DatapathProfile.W16, TargetTechnology.ASIC))
    w8 = estimate_datapath(datapath_config_for_profile(DatapathProfile.W8_SERIAL, TargetTechnology.ASIC))
    w1 = estimate_datapath(datapath_config_for_profile(DatapathProfile.W1_BIT_SERIAL, TargetTechnology.ASIC))

    assert w128.absorb128_cycles == 1
    assert w64.absorb128_cycles == 2
    assert w32.absorb128_cycles == 4
    assert w16.absorb128_cycles == 8
    assert w8.absorb128_cycles == 16
    assert w1.absorb128_cycles == 128
    assert w8.io_fit == "strong_fit_when_asic_io_is_the_bottleneck"


def test_fpga_parallel_engine_default_uses_128bit_datapath() -> None:
    config = fpga_n_parallel_engines_config(4)
    validate_config(config)
    assert config.datapath.profile == DatapathProfile.W128
    assert config.datapath.lane_width == DatapathWidth.W128
    assert config.io.data_bus_bits == 512


def test_asic_tiny_datapath_profiles_validate() -> None:
    for profile in (DatapathProfile.W8_SERIAL, DatapathProfile.W16, DatapathProfile.W5_SBOX_SERIAL):
        config = asic_two_datapaths_with_datapath_profile_config(profile)
        validate_config(config)
        assert config.datapath.profile == profile
        assert config.datapath.serialized_absorb is True
        assert config.datapath.serialized_state_update is True


def test_fpga_datapath_profile_override_preserves_engine_scaling() -> None:
    config = fpga_n_parallel_engines_with_datapath_profile_config(8, DatapathProfile.W128)
    validate_config(config)
    assert config.topology.engine_count == 8
    assert config.io.data_bus_bits == 1024

from ascon_arch import ASIC_DATAPATH_MATRIX, ASIC_PERMUTATION_MATRIX, FPGA_DATAPATH_MATRIX, FPGA_PERMUTATION_MATRIX, enumerate_valid_matrix


def test_matrix_enumeration_finds_valid_asic_and_fpga_combinations() -> None:
    asic_entries = enumerate_valid_matrix(TargetTechnology.ASIC, ASIC_DATAPATH_MATRIX, ASIC_PERMUTATION_MATRIX)
    fpga_entries = enumerate_valid_matrix(TargetTechnology.FPGA, FPGA_DATAPATH_MATRIX, FPGA_PERMUTATION_MATRIX, engine_count=4)
    assert any(entry.valid for entry in asic_entries)
    assert any(entry.valid for entry in fpga_entries)
    assert any(entry.datapath_profile == DatapathProfile.W8_SERIAL and entry.valid for entry in asic_entries)
    assert any(entry.datapath_profile == DatapathProfile.W128 and entry.valid for entry in fpga_entries)
