from dataclasses import dataclass

from ascon_hwmodel.uint import FixedUInt


def _clean_hex(text: str) -> str:
    cleaned: str = text.replace("_", "").replace(" ", "")
    if cleaned.startswith(("0x", "0X")):
        cleaned = cleaned[2:]
    if len(cleaned) == 0:
        return ""
    int(cleaned, 16)
    return cleaned


@dataclass(frozen=True, slots=True)
class ByteSequenceHex:
    """Hex text that denotes bytes in memory/bitstring order.

    Example: ByteSequenceHex("0001020304050607").to_bytes() returns the eight
    bytes 00 01 02 03 04 05 06 07. Interpreting those bytes as an Ascon U64 word
    gives integer hex 0x0706050403020100.
    """

    text: str

    def to_bytes(self) -> bytes:
        cleaned: str = _clean_hex(self.text)
        if len(cleaned) % 2 != 0:
            raise ValueError("byte-sequence hex must contain an even number of hex digits")
        return bytes.fromhex(cleaned)

    @classmethod
    def from_bytes(cls, data: bytes) -> "ByteSequenceHex":
        return cls(data.hex())


@dataclass(frozen=True, slots=True)
class UIntHex:
    """Hex text that denotes a numeric unsigned integer value.

    This is intentionally separate from ByteSequenceHex. Numeric hex is printed
    most-significant nibble first, while Ascon byte strings are loaded little-endian.
    """

    text: str
    width: int

    def to_int(self) -> int:
        if self.width <= 0:
            raise ValueError("width must be positive")
        cleaned: str = _clean_hex(self.text)
        value: int = int(cleaned or "0", 16)
        if value >= (1 << self.width):
            raise ValueError(f"integer 0x{value:X} does not fit in {self.width} bits")
        return value

    @classmethod
    def from_uint(cls, value: FixedUInt) -> "UIntHex":
        return cls(value.hex(group=False), value.WIDTH)
