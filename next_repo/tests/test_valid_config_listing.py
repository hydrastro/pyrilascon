from tools.list_valid_configs import enumerate_selected_configs

from ascon_arch.algorithm_planning import REQUESTED_SINGLE_ALGORITHM_FEATURES
from ascon_arch.enums import AlgorithmFeature, TargetTechnology


def test_selected_asic_config_listing_count() -> None:
    entries = enumerate_selected_configs(target=TargetTechnology.ASIC)
    assert len(entries) == 352
    assert all(entry.valid for entry in entries)
    assert {entry.algorithm for entry in entries} == {feature.value for feature in REQUESTED_SINGLE_ALGORITHM_FEATURES}


def test_selected_fpga_config_listing_count() -> None:
    entries = enumerate_selected_configs(target=TargetTechnology.FPGA)
    assert len(entries) == 208
    assert all(entry.valid for entry in entries)
    assert {entry.algorithm for entry in entries} == {feature.value for feature in REQUESTED_SINGLE_ALGORITHM_FEATURES}


def test_selected_config_listing_with_invalids() -> None:
    asic = enumerate_selected_configs(target=TargetTechnology.ASIC, include_invalid=True)
    fpga = enumerate_selected_configs(target=TargetTechnology.FPGA, include_invalid=True)
    assert sum(entry.valid for entry in asic) == 352
    assert len(asic) == 384
    assert sum(entry.valid for entry in fpga) == 208
    assert len(fpga) == 432


def test_algorithm_subset_listing_can_select_one_feature() -> None:
    entries = enumerate_selected_configs(
        target=TargetTechnology.ASIC,
        algorithms=(AlgorithmFeature.AEAD128,),
    )
    assert len(entries) == 44
    assert {entry.algorithm for entry in entries} == {"aead128"}
