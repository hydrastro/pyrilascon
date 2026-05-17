from dataclasses import dataclass

from ascon_arch.config import AlgorithmConfig
from ascon_arch.enums import AlgorithmFeature


@dataclass(frozen=True, slots=True)
class AlgorithmEstimate:
    feature: AlgorithmFeature
    family: str
    rate_bits: int
    requires_key: bool
    requires_nonce: bool
    produces_tag: bool
    kat_status: str
    notes: str

    def to_dict(self) -> dict[str, object]:
        return {
            "feature": self.feature.value,
            "family": self.family,
            "rate_bits": self.rate_bits,
            "requires_key": self.requires_key,
            "requires_nonce": self.requires_nonce,
            "produces_tag": self.produces_tag,
            "kat_status": self.kat_status,
            "notes": self.notes,
        }


AEAD_FEATURES: tuple[AlgorithmFeature, ...] = (
    AlgorithmFeature.AEAD128,
    AlgorithmFeature.AEAD128A,
    AlgorithmFeature.AEAD80PQ,
    AlgorithmFeature.LEGACY_AEAD128A,
    AlgorithmFeature.LEGACY_AEAD80PQ,
    AlgorithmFeature.LEGACY_AEAD128PQ,
)

HASH_FEATURES: tuple[AlgorithmFeature, ...] = (
    AlgorithmFeature.HASH,
    AlgorithmFeature.HASH256,
    AlgorithmFeature.HASHA,
)

XOF_FEATURES: tuple[AlgorithmFeature, ...] = (
    AlgorithmFeature.XOF,
    AlgorithmFeature.XOF128,
    AlgorithmFeature.XOFA,
)

CXOF_FEATURES: tuple[AlgorithmFeature, ...] = (
    AlgorithmFeature.CXOF,
    AlgorithmFeature.CXOF128,
)

REQUESTED_SINGLE_ALGORITHM_FEATURES: tuple[AlgorithmFeature, ...] = (
    AlgorithmFeature.AEAD128,
    AlgorithmFeature.AEAD128A,
    AlgorithmFeature.AEAD80PQ,
    AlgorithmFeature.HASH,
    AlgorithmFeature.HASHA,
    AlgorithmFeature.XOF,
    AlgorithmFeature.XOFA,
    AlgorithmFeature.CXOF,
)

NIST_KAT_BACKED_FEATURES: tuple[AlgorithmFeature, ...] = (
    AlgorithmFeature.AEAD128,
    AlgorithmFeature.HASH256,
    AlgorithmFeature.XOF128,
    AlgorithmFeature.CXOF128,
)


def is_aead_feature(feature: AlgorithmFeature) -> bool:
    return feature in AEAD_FEATURES


def is_hash_feature(feature: AlgorithmFeature) -> bool:
    return feature in HASH_FEATURES


def is_xof_feature(feature: AlgorithmFeature) -> bool:
    return feature in XOF_FEATURES


def is_cxof_feature(feature: AlgorithmFeature) -> bool:
    return feature in CXOF_FEATURES


def algorithm_config_for_feature(feature: AlgorithmFeature) -> AlgorithmConfig:
    if is_aead_feature(feature):
        return AlgorithmConfig(
            features=(feature,),
            include_encrypt=True,
            include_decrypt=True,
            include_hash=False,
            include_xof=False,
            include_cxof=False,
        )
    if is_hash_feature(feature):
        return AlgorithmConfig(
            features=(feature,),
            include_encrypt=False,
            include_decrypt=False,
            include_hash=True,
            include_xof=False,
            include_cxof=False,
        )
    if is_xof_feature(feature):
        return AlgorithmConfig(
            features=(feature,),
            include_encrypt=False,
            include_decrypt=False,
            include_hash=False,
            include_xof=True,
            include_cxof=False,
        )
    if is_cxof_feature(feature):
        return AlgorithmConfig(
            features=(feature,),
            include_encrypt=False,
            include_decrypt=False,
            include_hash=False,
            include_xof=False,
            include_cxof=True,
        )
    raise ValueError(f"unsupported algorithm feature: {feature}")


def requested_multi_algorithm_config() -> AlgorithmConfig:
    return AlgorithmConfig(
        features=REQUESTED_SINGLE_ALGORITHM_FEATURES,
        include_encrypt=True,
        include_decrypt=True,
        include_hash=True,
        include_xof=True,
        include_cxof=True,
    )


def algorithm_name_suffix(feature: AlgorithmFeature) -> str:
    return feature.value.replace("legacy_", "")


def estimate_algorithm(config: AlgorithmConfig) -> tuple[AlgorithmEstimate, ...]:
    estimates: list[AlgorithmEstimate] = []
    for feature in config.features:
        if is_aead_feature(feature):
            estimates.append(
                AlgorithmEstimate(
                    feature=feature,
                    family="aead",
                    rate_bits=128,
                    requires_key=True,
                    requires_nonce=True,
                    produces_tag=True,
                    kat_status="kat_backed" if feature == AlgorithmFeature.AEAD128 else "architecture_placeholder",
                    notes="AEAD encrypt/decrypt profile; non-NIST variants need dedicated IV/endian/KAT work.",
                )
            )
        elif is_hash_feature(feature):
            estimates.append(
                AlgorithmEstimate(
                    feature=feature,
                    family="hash",
                    rate_bits=64,
                    requires_key=False,
                    requires_nonce=False,
                    produces_tag=False,
                    kat_status="kat_backed" if feature == AlgorithmFeature.HASH256 else "architecture_placeholder",
                    notes="Hash-family profile; HASHa/HASH placeholders are not production-verified yet.",
                )
            )
        elif is_xof_feature(feature):
            estimates.append(
                AlgorithmEstimate(
                    feature=feature,
                    family="xof",
                    rate_bits=64,
                    requires_key=False,
                    requires_nonce=False,
                    produces_tag=False,
                    kat_status="kat_backed" if feature == AlgorithmFeature.XOF128 else "architecture_placeholder",
                    notes="XOF-family profile; XOFa/XOF placeholders are not production-verified yet.",
                )
            )
        elif is_cxof_feature(feature):
            estimates.append(
                AlgorithmEstimate(
                    feature=feature,
                    family="cxof",
                    rate_bits=64,
                    requires_key=False,
                    requires_nonce=False,
                    produces_tag=False,
                    kat_status="kat_backed" if feature == AlgorithmFeature.CXOF128 else "architecture_placeholder",
                    notes="CXOF-family profile; CXOF placeholder maps to a configurable architecture target.",
                )
            )
        else:
            raise ValueError(f"unsupported algorithm feature: {feature}")
    return tuple(estimates)
