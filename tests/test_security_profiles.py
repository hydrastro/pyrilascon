from dataclasses import replace
from pathlib import Path

import pytest

from ascon_arch import (
    ConfigValidationError,
    DecryptionReleasePolicy,
    FaultDetectionProfile,
    SecurityProfile,
    TargetTechnology,
    asic_dual_enc_dec_cores_config,
    config_with_security_profile,
    estimate_security,
    fpga_n_parallel_engines_config,
    security_config_for_profile,
    validate_config,
    write_design_product,
)


def test_decryption_plaintext_release_is_buffer_until_tag_verify_for_asic() -> None:
    config = asic_dual_enc_dec_cores_config()
    validate_config(config)
    assert config.security.decryption_release_policy == DecryptionReleasePolicy.BUFFER_UNTIL_TAG_VERIFY
    assert config.security.plaintext_buffer_until_tag_verified is True
    assert config.security.zeroize_plaintext_buffer_on_failure is True


def test_asic_default_security_is_counter_hardening_and_constant_time_tag() -> None:
    config = asic_dual_enc_dec_cores_config()
    validate_config(config)
    assert config.security.profile == SecurityProfile.ASIC_BASELINE
    assert config.security.randomized_counter_hardening is True
    assert config.security.constant_time_tag_compare is True
    assert config.security.fault_detection == FaultDetectionProfile.NONE
    assert estimate_security(config.security).area_class == "small_plus_plaintext_buffer"


def test_fpga_default_security_enables_fault_detection_counter_and_tag_compare() -> None:
    config = fpga_n_parallel_engines_config(4)
    validate_config(config)
    assert config.security.profile == SecurityProfile.FPGA_FAULT_DETECT
    assert config.security.fault_detection == FaultDetectionProfile.DUPLICATE_COMPUTE
    assert config.security.duplicate_compute_check is True
    assert config.security.randomized_counter_hardening is True
    assert config.security.constant_time_tag_compare is True


def test_security_none_is_allowed_but_still_keeps_safe_decryption_buffering() -> None:
    config = config_with_security_profile(asic_dual_enc_dec_cores_config(), SecurityProfile.NONE)
    validate_config(config)
    assert config.security.profile == SecurityProfile.NONE
    assert config.security.constant_time_tag_compare is False
    assert config.security.randomized_counter_hardening is False
    assert config.security.decryption_release_policy == DecryptionReleasePolicy.BUFFER_UNTIL_TAG_VERIFY
    assert config.security.plaintext_buffer_until_tag_verified is True


def test_decrypt_release_before_tag_verify_is_rejected() -> None:
    config = asic_dual_enc_dec_cores_config()
    bad_security = replace(config.security, plaintext_buffer_until_tag_verified=False)
    bad = replace(config, security=bad_security)
    with pytest.raises(ConfigValidationError):
        validate_config(bad)


def test_duplicate_compute_requires_matching_fault_detection_profile() -> None:
    config = asic_dual_enc_dec_cores_config()
    bad_security = replace(config.security, duplicate_compute_check=True)
    bad = replace(config, security=bad_security)
    with pytest.raises(ConfigValidationError):
        validate_config(bad)


def test_security_profile_factory_masked_profiles_require_randomness() -> None:
    first_order = security_config_for_profile(SecurityProfile.FIRST_ORDER_MASKED, TargetTechnology.ASIC)
    threshold = security_config_for_profile(SecurityProfile.THRESHOLD_SBOX, TargetTechnology.ASIC)
    assert first_order.randomness_bits_per_cycle > 0
    assert threshold.randomness_bits_per_cycle > first_order.randomness_bits_per_cycle


def test_generated_product_contains_security_and_plaintext_buffer_modules(tmp_path: Path) -> None:
    config = fpga_n_parallel_engines_config(4)
    write_design_product(config, tmp_path)
    rtl_root = tmp_path / config.name / "rtl"
    assert (rtl_root / f"ascon_{config.name}_security.sv").exists()
    assert (rtl_root / f"ascon_{config.name}_decrypt_plaintext_buffer.sv").exists()
    metrics = (tmp_path / config.name / "metadata" / "expected_metrics.json").read_text(encoding="utf-8")
    assert "security_profile" in metrics
    assert "buffer_until_tag_verify" in metrics
