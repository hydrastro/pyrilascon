from dataclasses import dataclass
from enum import Enum
from typing import Final, Mapping

from ascon_hwmodel.iv import ascon_iv
from ascon_hwmodel.variants import AsconVariant


class AEADVariant(str, Enum):
    """AEAD configuration names.

    NIST_AEAD128 is the standardized SP 800-232 algorithm.
    LEGACY_* entries are compatibility parameter sets from the Ascon submission family.
    Their byte-level conformance needs legacy test vectors because v1.2 used big-endian
    formatting, while this package's state model is intentionally little-endian.
    """

    NIST_AEAD128 = "Ascon-AEAD128"
    LEGACY_ASCON128 = "Ascon-128-v1.2"
    LEGACY_ASCON128A = "Ascon-128a-v1.2"
    LEGACY_ASCON80PQ = "Ascon-80pq-v1.2"
    LEGACY_ASCON128PQ = "Ascon-128pq-v1.2-alias-for-80pq"


@dataclass(frozen=True, slots=True)
class AEADConfig:
    variant: AEADVariant
    key_bytes: int
    nonce_bytes: int
    tag_bytes: int
    rate_bytes: int
    init_rounds: int
    intermediate_rounds: int
    iv_bytes: bytes
    standardized: bool
    note: str

    @property
    def rate128(self) -> bool:
        return self.rate_bytes == 16

    def check_key(self, key: bytes) -> None:
        if len(key) != self.key_bytes:
            raise ValueError(f"{self.variant.value} requires {self.key_bytes} key bytes, got {len(key)}")

    def check_nonce(self, nonce: bytes) -> None:
        if len(nonce) != self.nonce_bytes:
            raise ValueError(f"{self.variant.value} requires {self.nonce_bytes} nonce bytes, got {len(nonce)}")

    def check_tag(self, tag: bytes) -> None:
        if len(tag) != self.tag_bytes:
            raise ValueError(f"{self.variant.value} requires {self.tag_bytes} tag bytes, got {len(tag)}")


def _le64(value: int) -> bytes:
    return value.to_bytes(8, "little")


AEAD_CONFIGS: Final[Mapping[AEADVariant, AEADConfig]] = {
    AEADVariant.NIST_AEAD128: AEADConfig(
        variant=AEADVariant.NIST_AEAD128,
        key_bytes=16,
        nonce_bytes=16,
        tag_bytes=16,
        rate_bytes=16,
        init_rounds=12,
        intermediate_rounds=8,
        iv_bytes=ascon_iv(AsconVariant.AEAD128).value.to_bytes(8, "little"),
        standardized=True,
        note="NIST SP 800-232 Ascon-AEAD128; based on submission Ascon-128a.",
    ),
    AEADVariant.LEGACY_ASCON128: AEADConfig(
        variant=AEADVariant.LEGACY_ASCON128,
        key_bytes=16,
        nonce_bytes=16,
        tag_bytes=16,
        rate_bytes=8,
        init_rounds=12,
        intermediate_rounds=6,
        iv_bytes=bytes.fromhex("80400c0600000000"),
        standardized=False,
        note="Legacy Ascon-128 parameter set; included as a hardware exploration scaffold.",
    ),
    AEADVariant.LEGACY_ASCON128A: AEADConfig(
        variant=AEADVariant.LEGACY_ASCON128A,
        key_bytes=16,
        nonce_bytes=16,
        tag_bytes=16,
        rate_bytes=16,
        init_rounds=12,
        intermediate_rounds=8,
        iv_bytes=bytes.fromhex("80800c0800000000"),
        standardized=False,
        note="Legacy Ascon-128a parameter set; final NIST AEAD128 uses updated IV and little-endian conventions.",
    ),
    AEADVariant.LEGACY_ASCON80PQ: AEADConfig(
        variant=AEADVariant.LEGACY_ASCON80PQ,
        key_bytes=20,
        nonce_bytes=16,
        tag_bytes=16,
        rate_bytes=8,
        init_rounds=12,
        intermediate_rounds=6,
        iv_bytes=bytes.fromhex("a0400c06"),
        standardized=False,
        note="Legacy Ascon-80pq / often miscalled 128pq; 160-bit key with 32-bit IV.",
    ),
    AEADVariant.LEGACY_ASCON128PQ: AEADConfig(
        variant=AEADVariant.LEGACY_ASCON128PQ,
        key_bytes=20,
        nonce_bytes=16,
        tag_bytes=16,
        rate_bytes=8,
        init_rounds=12,
        intermediate_rounds=6,
        iv_bytes=bytes.fromhex("a0400c06"),
        standardized=False,
        note="Alias for legacy Ascon-80pq; kept because some sources call it Ascon-128pq.",
    ),
}


def get_aead_config(variant: AEADVariant = AEADVariant.NIST_AEAD128) -> AEADConfig:
    return AEAD_CONFIGS[variant]


def emit_verilog_aead_config_include() -> str:
    return "\n".join(
        (
            "// Generated Ascon AEAD mode encodings.",
            "localparam [1:0] ASCON_AEAD_MODE_NIST_AEAD128 = 2'd0;",
            "localparam [1:0] ASCON_AEAD_MODE_LEGACY_128   = 2'd1;",
            "localparam [1:0] ASCON_AEAD_MODE_LEGACY_128A  = 2'd2;",
            "localparam [1:0] ASCON_AEAD_MODE_LEGACY_80PQ  = 2'd3;",
        )
    )
