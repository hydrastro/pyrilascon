"""AXI-stream-style AEAD128 transaction model.

This module is the software oracle for the future unbounded streaming FPGA
backend.  The frozen accelerator ABI keeps key/nonce/lengths on the CSR/MMIO
control plane while AD and text bytes travel over a valid/ready stream with a
final-beat byte mask.  The helpers here intentionally model only that data-plane
framing: they validate stream beats, reconstruct byte strings, run the existing
AEAD model, and repack output bytes as stream beats.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

from ascon_hwmodel.aead_config import AEADVariant
from ascon_hwmodel.aead_decrypt import AEADDecryptionResult, aead_decrypt
from ascon_hwmodel.aead_encrypt import AEADEncryptionResult, aead_encrypt


class AeadStreamKind(str, Enum):
    """Logical stream type encoded in AXI ``tuser`` or DATA_IN_CTRL kind bits."""

    AD = "ad"
    TEXT = "text"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class AxisStreamBeat:
    """One byte-oriented AXI-stream beat.

    ``data`` is stored as a fixed-width byte vector.  ``keep`` is a bit mask where
    bit *i* marks byte *i* as valid.  This matches the little-endian byte order
    already used by the hardware model and RTL DATA registers.
    """

    data: bytes
    keep: int
    last: bool
    kind: AeadStreamKind

    def __post_init__(self) -> None:
        if len(self.data) == 0:
            raise ValueError("AxisStreamBeat data width must be positive")
        max_keep = (1 << len(self.data)) - 1
        if self.keep < 0 or self.keep > max_keep:
            raise ValueError(f"keep mask 0x{self.keep:x} does not fit {len(self.data)} bytes")

    @property
    def valid_bytes(self) -> int:
        return valid_byte_count_from_keep(self.keep, len(self.data))

    @property
    def payload(self) -> bytes:
        return self.data[: self.valid_bytes]


@dataclass(frozen=True, slots=True)
class AxisAeadEncryptionResult:
    """Streaming encryption result plus the scalar AEAD oracle result."""

    ciphertext_beats: tuple[AxisStreamBeat, ...]
    ciphertext: bytes
    tag: bytes
    scalar: AEADEncryptionResult


@dataclass(frozen=True, slots=True)
class AxisAeadDecryptionResult:
    """Streaming decryption result plus the scalar AEAD oracle result."""

    plaintext_beats: tuple[AxisStreamBeat, ...]
    plaintext: bytes
    valid: bool
    computed_tag: bytes
    scalar: AEADDecryptionResult


def keep_mask(valid_bytes: int, bus_bytes: int) -> int:
    """Return a contiguous low-bit keep mask for ``valid_bytes`` bytes."""

    _check_bus_bytes(bus_bytes)
    if valid_bytes < 0 or valid_bytes > bus_bytes:
        raise ValueError(f"valid_bytes must be in 0..{bus_bytes}, got {valid_bytes}")
    return (1 << valid_bytes) - 1 if valid_bytes else 0


def valid_byte_count_from_keep(mask: int, bus_bytes: int) -> int:
    """Decode a contiguous low-bit byte-valid mask.

    Non-contiguous masks are rejected because the RTL streaming profile uses the
    final ``tkeep``/bytemask only to describe a tail length, not byte holes.
    """

    _check_bus_bytes(bus_bytes)
    if mask < 0 or mask >= (1 << bus_bytes):
        raise ValueError(f"keep mask 0x{mask:x} does not fit {bus_bytes} bytes")
    count = 0
    while count < bus_bytes and ((mask >> count) & 1) != 0:
        count += 1
    if mask != keep_mask(count, bus_bytes):
        raise ValueError(f"keep mask 0x{mask:x} is not contiguous from byte 0")
    return count


def pack_axis_beats(data: bytes, kind: AeadStreamKind, bus_bytes: int = 16) -> tuple[AxisStreamBeat, ...]:
    """Pack bytes into fixed-width stream beats.

    Empty streams produce no beats because zero lengths are already represented
    by the CSR/MMIO length registers in the frozen ABI.
    """

    _check_bus_bytes(bus_bytes)
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes-like")
    if len(data) == 0:
        return ()

    beats: list[AxisStreamBeat] = []
    raw = bytes(data)
    for offset in range(0, len(raw), bus_bytes):
        chunk = raw[offset : offset + bus_bytes]
        last = offset + bus_bytes >= len(raw)
        padded = chunk + (b"\x00" * (bus_bytes - len(chunk)))
        valid = len(chunk)
        beats.append(AxisStreamBeat(padded, keep_mask(valid, bus_bytes), last, kind))
    return tuple(beats)


def unpack_axis_beats(
    beats: Iterable[AxisStreamBeat],
    *,
    expected_kind: AeadStreamKind | None = None,
    expected_len: int | None = None,
    bus_bytes: int = 16,
) -> bytes:
    """Validate and unpack a stream packet into bytes."""

    _check_bus_bytes(bus_bytes)
    if expected_len is not None and expected_len < 0:
        raise ValueError("expected_len must be non-negative")

    packet = tuple(beats)
    if not packet:
        if expected_len not in (None, 0):
            raise ValueError(f"empty stream has length 0, expected {expected_len}")
        return b""

    output = bytearray()
    seen_last = False
    for index, beat in enumerate(packet):
        if len(beat.data) != bus_bytes:
            raise ValueError(f"beat {index} has {len(beat.data)} data bytes, expected {bus_bytes}")
        if expected_kind is not None and beat.kind != expected_kind:
            raise ValueError(f"beat {index} kind is {beat.kind.value}, expected {expected_kind.value}")
        valid = valid_byte_count_from_keep(beat.keep, bus_bytes)
        if seen_last:
            raise ValueError("stream contains data after a beat with last=True")
        if not beat.last and valid != bus_bytes:
            raise ValueError("only the final beat may have a partial keep mask")
        if beat.last and valid == 0:
            raise ValueError("non-empty streams must not terminate with an empty beat")
        output.extend(beat.data[:valid])
        seen_last = beat.last

    if not seen_last:
        raise ValueError("stream packet is missing a final beat with last=True")

    unpacked = bytes(output)
    if expected_len is not None and len(unpacked) != expected_len:
        raise ValueError(f"stream length is {len(unpacked)}, expected {expected_len}")
    return unpacked


def axis_aead128_encrypt(
    *,
    key: bytes,
    nonce: bytes,
    ad_beats: Sequence[AxisStreamBeat],
    plaintext_beats: Sequence[AxisStreamBeat],
    ad_len: int,
    text_len: int,
    bus_bytes: int = 16,
) -> AxisAeadEncryptionResult:
    """Encrypt one AEAD128 transaction from stream-framed AD/plaintext."""

    associated_data = unpack_axis_beats(ad_beats, expected_kind=AeadStreamKind.AD, expected_len=ad_len, bus_bytes=bus_bytes)
    plaintext = unpack_axis_beats(
        plaintext_beats,
        expected_kind=AeadStreamKind.TEXT,
        expected_len=text_len,
        bus_bytes=bus_bytes,
    )
    scalar = aead_encrypt(key, nonce, associated_data, plaintext, AEADVariant.NIST_AEAD128)
    ciphertext_beats = pack_axis_beats(scalar.ciphertext, AeadStreamKind.TEXT, bus_bytes)
    return AxisAeadEncryptionResult(ciphertext_beats, scalar.ciphertext, scalar.tag, scalar)


def axis_aead128_decrypt(
    *,
    key: bytes,
    nonce: bytes,
    ad_beats: Sequence[AxisStreamBeat],
    ciphertext_beats: Sequence[AxisStreamBeat],
    ad_len: int,
    text_len: int,
    tag: bytes,
    bus_bytes: int = 16,
) -> AxisAeadDecryptionResult:
    """Decrypt one AEAD128 transaction from stream-framed AD/ciphertext.

    Plaintext beats are returned only when the tag is valid.  This mirrors the
    chosen hardware policy: buffer-until-verify for decrypt, never expose
    unauthenticated plaintext.
    """

    associated_data = unpack_axis_beats(ad_beats, expected_kind=AeadStreamKind.AD, expected_len=ad_len, bus_bytes=bus_bytes)
    ciphertext = unpack_axis_beats(
        ciphertext_beats,
        expected_kind=AeadStreamKind.TEXT,
        expected_len=text_len,
        bus_bytes=bus_bytes,
    )
    scalar = aead_decrypt(key, nonce, associated_data, ciphertext, tag, AEADVariant.NIST_AEAD128)
    plaintext = scalar.plaintext if scalar.valid else b""
    plaintext_beats = pack_axis_beats(plaintext, AeadStreamKind.TEXT, bus_bytes)
    return AxisAeadDecryptionResult(plaintext_beats, plaintext, scalar.valid, scalar.computed_tag, scalar)


def _check_bus_bytes(bus_bytes: int) -> None:
    if not isinstance(bus_bytes, int):
        raise TypeError("bus_bytes must be int")
    if bus_bytes <= 0:
        raise ValueError("bus_bytes must be positive")
    if bus_bytes > 64:
        raise ValueError("bus_bytes above 64 are not supported by the reference helpers")
