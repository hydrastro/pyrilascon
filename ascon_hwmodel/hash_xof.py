from dataclasses import dataclass
from enum import Enum
from typing import Final, Mapping

from ascon_hwmodel.byteops import parse_bytes
from ascon_hwmodel.iv import ascon_iv
from ascon_hwmodel.p12 import ascon_p12
from ascon_hwmodel.rate import rate_bytes_from_state, xor_rate_bytes
from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64
from ascon_hwmodel.variants import AsconVariant


class HashXofVariant(str, Enum):
    NIST_HASH256 = "Ascon-Hash256"
    NIST_XOF128 = "Ascon-XOF128"
    NIST_CXOF128 = "Ascon-CXOF128"
    LEGACY_HASH = "Ascon-Hash-v1.2"
    LEGACY_HASHA = "Ascon-Hasha-v1.2"
    LEGACY_XOF = "Ascon-Xof-v1.2"
    LEGACY_XOFA = "Ascon-Xofa-v1.2"


@dataclass(frozen=True, slots=True)
class HashXofConfig:
    variant: HashXofVariant
    rate_bytes: int
    rounds: int
    iv_bytes: bytes
    standardized: bool
    note: str


HASH_XOF_CONFIGS: Final[Mapping[HashXofVariant, HashXofConfig]] = {
    HashXofVariant.NIST_HASH256: HashXofConfig(
        HashXofVariant.NIST_HASH256,
        rate_bytes=8,
        rounds=12,
        iv_bytes=ascon_iv(AsconVariant.HASH256).value.to_bytes(8, "little"),
        standardized=True,
        note="NIST SP 800-232 fixed 256-bit hash.",
    ),
    HashXofVariant.NIST_XOF128: HashXofConfig(
        HashXofVariant.NIST_XOF128,
        rate_bytes=8,
        rounds=12,
        iv_bytes=ascon_iv(AsconVariant.XOF128).value.to_bytes(8, "little"),
        standardized=True,
        note="NIST SP 800-232 extendable-output function.",
    ),
    HashXofVariant.NIST_CXOF128: HashXofConfig(
        HashXofVariant.NIST_CXOF128,
        rate_bytes=8,
        rounds=12,
        iv_bytes=ascon_iv(AsconVariant.CXOF128).value.to_bytes(8, "little"),
        standardized=True,
        note="NIST SP 800-232 customized extendable-output function.",
    ),
    HashXofVariant.LEGACY_HASH: HashXofConfig(
        HashXofVariant.LEGACY_HASH,
        rate_bytes=8,
        rounds=12,
        iv_bytes=bytes.fromhex("00400c0000000100"),
        standardized=False,
        note="Legacy scaffold only; not byte-level validated in this little-endian model.",
    ),
    HashXofVariant.LEGACY_HASHA: HashXofConfig(
        HashXofVariant.LEGACY_HASHA,
        rate_bytes=8,
        rounds=8,
        iv_bytes=bytes.fromhex("00400c0400000100"),
        standardized=False,
        note="Legacy scaffold only; not byte-level validated in this little-endian model.",
    ),
    HashXofVariant.LEGACY_XOF: HashXofConfig(
        HashXofVariant.LEGACY_XOF,
        rate_bytes=8,
        rounds=12,
        iv_bytes=bytes.fromhex("00400c0000000000"),
        standardized=False,
        note="Legacy scaffold only; not byte-level validated in this little-endian model.",
    ),
    HashXofVariant.LEGACY_XOFA: HashXofConfig(
        HashXofVariant.LEGACY_XOFA,
        rate_bytes=8,
        rounds=8,
        iv_bytes=bytes.fromhex("00400c0400000000"),
        standardized=False,
        note="Legacy scaffold only; not byte-level validated in this little-endian model.",
    ),
}


def get_hash_xof_config(variant: HashXofVariant) -> HashXofConfig:
    return HASH_XOF_CONFIGS[variant]


def hash_xof_initial_state(config: HashXofConfig) -> AsconState:
    image: bytes = config.iv_bytes + (b"\x00" * 32)
    if len(image) != 40:
        raise ValueError("hash/XOF initialization image must be 40 bytes")
    return ascon_p12(AsconState.from_bytes(image))


def absorb_message_64_then_permute(state: AsconState, message: bytes) -> AsconState:
    parsed = parse_bytes(message, 8)
    for block in parsed.full_blocks:
        state = xor_rate_bytes(state, block, 8)
        state = ascon_p12(state)
    state = xor_rate_bytes(state, parsed.padded_final_block(), 8)
    return ascon_p12(state)


def squeeze_64(state: AsconState, output_bytes: int) -> bytes:
    if output_bytes <= 0:
        raise ValueError("output_bytes must be positive")
    output = bytearray()
    while len(output) < output_bytes:
        output.extend(rate_bytes_from_state(state, 8))
        if len(output) < output_bytes:
            state = ascon_p12(state)
    return bytes(output[:output_bytes])


def ascon_hash256(message: bytes) -> bytes:
    config = get_hash_xof_config(HashXofVariant.NIST_HASH256)
    state = hash_xof_initial_state(config)
    state = absorb_message_64_then_permute(state, message)
    return squeeze_64(state, 32)


def ascon_xof128(message: bytes, output_bytes: int) -> bytes:
    config = get_hash_xof_config(HashXofVariant.NIST_XOF128)
    state = hash_xof_initial_state(config)
    state = absorb_message_64_then_permute(state, message)
    return squeeze_64(state, output_bytes)


def ascon_cxof128(message: bytes, output_bytes: int, customization: bytes) -> bytes:
    if len(customization) > 256:
        raise ValueError("Ascon-CXOF128 customization must be at most 256 bytes")
    config = get_hash_xof_config(HashXofVariant.NIST_CXOF128)
    state = hash_xof_initial_state(config)

    z0: bytes = (len(customization) * 8).to_bytes(8, "little")
    state = xor_rate_bytes(state, z0, 8)
    state = ascon_p12(state)
    state = absorb_message_64_then_permute(state, customization)
    state = absorb_message_64_then_permute(state, message)
    return squeeze_64(state, output_bytes)


def emit_verilog_hash_xof_include() -> str:
    return "\n".join(
        (
            "// Generated Ascon hash/XOF notes.",
            "// Hash/XOF datapaths reuse ascon_rate_xor(), ascon_p12(), and ASCON_*_IV localparams.",
            "// Streaming control will be added in the next RTL step.",
        )
    )
