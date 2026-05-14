from dataclasses import dataclass

from ascon_arch.config import SecurityConfig
from ascon_arch.enums import (
    DecryptionBufferStorage,
    DecryptionReleasePolicy,
    FaultDetectionProfile,
    SecurityProfile,
    SideChannelProtection,
    TargetTechnology,
)


@dataclass(frozen=True, slots=True)
class SecurityEstimate:
    profile: SecurityProfile
    side_channel_class: str
    fault_detection_class: str
    area_class: str
    performance_impact: str
    plaintext_release_policy: str
    plaintext_buffer_area: str
    notes: str

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile.value,
            "side_channel_class": self.side_channel_class,
            "fault_detection_class": self.fault_detection_class,
            "area_class": self.area_class,
            "performance_impact": self.performance_impact,
            "plaintext_release_policy": self.plaintext_release_policy,
            "plaintext_buffer_area": self.plaintext_buffer_area,
            "notes": self.notes,
        }


def recommended_security_profile(target: TargetTechnology) -> SecurityProfile:
    if target == TargetTechnology.FPGA:
        return SecurityProfile.FPGA_FAULT_DETECT
    return SecurityProfile.ASIC_BASELINE


def _buffer_storage_for_target(target: TargetTechnology) -> DecryptionBufferStorage:
    if target == TargetTechnology.FPGA:
        return DecryptionBufferStorage.BRAM_FIFO
    return DecryptionBufferStorage.SRAM_FIFO


def _buffer_capacity_for_target(target: TargetTechnology) -> int:
    if target == TargetTechnology.FPGA:
        return 65536
    return 4096


def security_config_for_profile(
    profile: SecurityProfile,
    target: TargetTechnology,
    *,
    plaintext_buffer_capacity_bytes: int | None = None,
) -> SecurityConfig:
    capacity = plaintext_buffer_capacity_bytes or _buffer_capacity_for_target(target)
    storage = _buffer_storage_for_target(target)

    if profile == SecurityProfile.NONE:
        return SecurityConfig(
            profile=profile,
            side_channel_protection=SideChannelProtection.NONE,
            fault_detection=FaultDetectionProfile.NONE,
            constant_time_control=False,
            constant_time_tag_compare=False,
            randomized_counter_hardening=False,
            duplicate_control_fsm_checks=False,
            duplicate_compute_check=False,
            randomness_bits_per_cycle=0,
            decryption_release_policy=DecryptionReleasePolicy.BUFFER_UNTIL_TAG_VERIFY,
            plaintext_buffer_until_tag_verified=True,
            plaintext_buffer_storage=storage,
            plaintext_buffer_capacity_bytes=capacity,
        )

    if profile == SecurityProfile.ASIC_BASELINE:
        return SecurityConfig(
            profile=profile,
            side_channel_protection=SideChannelProtection.NONE,
            fault_detection=FaultDetectionProfile.NONE,
            constant_time_control=True,
            constant_time_tag_compare=True,
            randomized_counter_hardening=True,
            duplicate_control_fsm_checks=False,
            duplicate_compute_check=False,
            randomness_bits_per_cycle=0,
            decryption_release_policy=DecryptionReleasePolicy.BUFFER_UNTIL_TAG_VERIFY,
            plaintext_buffer_until_tag_verified=True,
            plaintext_buffer_storage=storage,
            plaintext_buffer_capacity_bytes=capacity,
        )

    if profile == SecurityProfile.FPGA_FAULT_DETECT:
        return SecurityConfig(
            profile=profile,
            side_channel_protection=SideChannelProtection.NONE,
            fault_detection=FaultDetectionProfile.DUPLICATE_COMPUTE,
            constant_time_control=True,
            constant_time_tag_compare=True,
            randomized_counter_hardening=True,
            duplicate_control_fsm_checks=True,
            duplicate_compute_check=True,
            randomness_bits_per_cycle=0,
            decryption_release_policy=DecryptionReleasePolicy.BUFFER_UNTIL_TAG_VERIFY,
            plaintext_buffer_until_tag_verified=True,
            plaintext_buffer_storage=storage,
            plaintext_buffer_capacity_bytes=capacity,
        )

    if profile == SecurityProfile.DUPLICATE_COMPUTE:
        return SecurityConfig(
            profile=profile,
            side_channel_protection=SideChannelProtection.NONE,
            fault_detection=FaultDetectionProfile.DUPLICATE_COMPUTE,
            constant_time_control=True,
            constant_time_tag_compare=True,
            randomized_counter_hardening=True,
            duplicate_control_fsm_checks=True,
            duplicate_compute_check=True,
            randomness_bits_per_cycle=0,
            decryption_release_policy=DecryptionReleasePolicy.BUFFER_UNTIL_TAG_VERIFY,
            plaintext_buffer_until_tag_verified=True,
            plaintext_buffer_storage=storage,
            plaintext_buffer_capacity_bytes=capacity,
        )

    if profile == SecurityProfile.FIRST_ORDER_MASKED:
        return SecurityConfig(
            profile=profile,
            side_channel_protection=SideChannelProtection.FIRST_ORDER_MASKING,
            fault_detection=FaultDetectionProfile.NONE,
            constant_time_control=True,
            constant_time_tag_compare=True,
            randomized_counter_hardening=True,
            duplicate_control_fsm_checks=False,
            duplicate_compute_check=False,
            randomness_bits_per_cycle=64,
            decryption_release_policy=DecryptionReleasePolicy.BUFFER_UNTIL_TAG_VERIFY,
            plaintext_buffer_until_tag_verified=True,
            plaintext_buffer_storage=storage,
            plaintext_buffer_capacity_bytes=capacity,
        )

    if profile == SecurityProfile.THRESHOLD_SBOX:
        return SecurityConfig(
            profile=profile,
            side_channel_protection=SideChannelProtection.THRESHOLD_IMPLEMENTATION,
            fault_detection=FaultDetectionProfile.NONE,
            constant_time_control=True,
            constant_time_tag_compare=True,
            randomized_counter_hardening=True,
            duplicate_control_fsm_checks=False,
            duplicate_compute_check=False,
            randomness_bits_per_cycle=96,
            decryption_release_policy=DecryptionReleasePolicy.BUFFER_UNTIL_TAG_VERIFY,
            plaintext_buffer_until_tag_verified=True,
            plaintext_buffer_storage=storage,
            plaintext_buffer_capacity_bytes=capacity,
        )

    raise ValueError(f"unsupported security profile: {profile}")


def estimate_security(config: SecurityConfig) -> SecurityEstimate:
    if config.profile == SecurityProfile.NONE:
        return SecurityEstimate(
            config.profile,
            "none",
            "none",
            "plaintext_buffer_only",
            "none_except_decrypt_buffering",
            config.decryption_release_policy.value,
            "medium_to_large_message_buffer",
            "No side-channel/fault countermeasures are enabled; safe decryption buffering is still enforced.",
        )
    if config.profile == SecurityProfile.ASIC_BASELINE:
        return SecurityEstimate(
            config.profile,
            "unmasked",
            "control_counter_hardening_only",
            "small_plus_plaintext_buffer",
            "negligible",
            config.decryption_release_policy.value,
            "medium_sram_or_fifo",
            "ASIC baseline: randomized/control counter hardening plus constant-time tag compare.",
        )
    if config.profile == SecurityProfile.FPGA_FAULT_DETECT:
        return SecurityEstimate(
            config.profile,
            "unmasked",
            "duplicate_compute",
            "approximately_2x_compute_plus_buffer",
            "slower_or_double_resources",
            config.decryption_release_policy.value,
            "large_bram_fifo",
            "FPGA baseline: duplicate computation fault detection, counter hardening, and constant-time tag compare.",
        )
    if config.profile == SecurityProfile.DUPLICATE_COMPUTE:
        return SecurityEstimate(
            config.profile,
            "unmasked",
            "duplicate_compute",
            "approximately_2x_compute_plus_buffer",
            "slower_or_double_resources",
            config.decryption_release_policy.value,
            "target_dependent_buffer",
            "Fault-detection profile based on redundant computation and comparison.",
        )
    if config.profile == SecurityProfile.FIRST_ORDER_MASKED:
        return SecurityEstimate(
            config.profile,
            "first_order_masked",
            "none_by_default",
            "high_plus_buffer",
            "slower",
            config.decryption_release_policy.value,
            "target_dependent_buffer",
            "Serious ASIC side-channel profile; requires randomness and masked storage/datapath work.",
        )
    if config.profile == SecurityProfile.THRESHOLD_SBOX:
        return SecurityEstimate(
            config.profile,
            "threshold_sbox",
            "none_by_default",
            "high_plus_buffer",
            "slower",
            config.decryption_release_policy.value,
            "target_dependent_buffer",
            "Threshold S-box profile; useful for stronger SCA resistance once masked datapath backend exists.",
        )
    raise ValueError(f"unsupported security profile: {config.profile}")
