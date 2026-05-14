from dataclasses import dataclass
from typing import Iterator, Sequence, TypeAlias

Bit: TypeAlias = int


@dataclass(frozen=True, slots=True)
class BitString:
    """Ascon bitstring in specification order.

    bits[0] is the first bit of the bitstring X[0].  For byte-oriented Ascon
    data, that first bit is the least-significant bit of the first byte.
    This is intentionally different from hexadecimal integer printing, where
    the most-significant byte and bit are printed first.
    """

    bits: tuple[Bit, ...]

    def __post_init__(self) -> None:
        for bit in self.bits:
            if bit not in (0, 1):
                raise ValueError(f"bit must be 0 or 1, got {bit}")

    @classmethod
    def empty(cls) -> "BitString":
        return cls(())

    @classmethod
    def from_bits(cls, bits: Sequence[Bit]) -> "BitString":
        return cls(tuple(bits))

    @classmethod
    def from_bytes(cls, data: bytes) -> "BitString":
        """Convert bytes to an Ascon bitstring, with each byte expanded LSB-first."""
        bits: list[Bit] = []
        for byte in data:
            for bit_index in range(8):
                bits.append((byte >> bit_index) & 1)
        return cls(tuple(bits))

    @classmethod
    def from_int_lsb_first(cls, value: int, width: int) -> "BitString":
        if value < 0:
            raise ValueError("value must be non-negative")
        if width < 0:
            raise ValueError("width must be non-negative")
        if value >= (1 << width):
            raise ValueError(f"value 0x{value:X} does not fit in {width} bits")
        return cls(tuple((value >> bit_index) & 1 for bit_index in range(width)))

    def __len__(self) -> int:
        return len(self.bits)

    def __iter__(self) -> Iterator[Bit]:
        return iter(self.bits)

    def bit(self, index: int) -> Bit:
        return self.bits[index]

    def slice(self, start: int, stop_inclusive: int) -> "BitString":
        """Return X[start:stop_inclusive], matching the inclusive Ascon notation."""
        if start < 0:
            raise ValueError("start must be non-negative")
        if stop_inclusive < start:
            return BitString.empty()
        return BitString(self.bits[start : stop_inclusive + 1])

    def prefix(self, bit_count: int) -> "BitString":
        if bit_count < 0:
            raise ValueError("bit_count must be non-negative")
        return BitString(self.bits[:bit_count])

    def concat(self, other: "BitString") -> "BitString":
        return BitString(self.bits + other.bits)

    def pad(self, rate_bits: int) -> "BitString":
        return pad_bitstring(self, rate_bits)

    def parse(self, rate_bits: int) -> "ParsedBitString":
        return parse_bitstring(self, rate_bits)

    def to_int_lsb_first(self) -> int:
        """Interpret bits[0] as integer bit 0, bits[1] as bit 1, etc."""
        value: int = 0
        for bit_index, bit in enumerate(self.bits):
            value |= bit << bit_index
        return value

    def to_bytes(self) -> bytes:
        """Convert to bytes, requiring byte alignment.

        The first eight bitstring bits become the first byte, with bits[0] as
        that byte's least-significant bit.
        """
        if len(self.bits) % 8 != 0:
            raise ValueError(f"bitstring length must be byte-aligned, got {len(self.bits)} bits")
        out: bytearray = bytearray()
        for index in range(0, len(self.bits), 8):
            byte_value: int = 0
            for bit_index, bit in enumerate(self.bits[index : index + 8]):
                byte_value |= bit << bit_index
            out.append(byte_value)
        return bytes(out)

    def bit_string(self) -> str:
        """Return a textual bitstring in Ascon order, i.e. bits[0] printed first."""
        return "".join(str(bit) for bit in self.bits)


@dataclass(frozen=True, slots=True)
class ParsedBitString:
    """Result of parse(X, r): full r-bit blocks plus the final partial block."""

    full_blocks: tuple[BitString, ...]
    final_block: BitString
    rate_bits: int

    def all_blocks(self) -> tuple[BitString, ...]:
        return self.full_blocks + (self.final_block,)

    def padded_final_block(self) -> BitString:
        return self.final_block.pad(self.rate_bits)


def check_rate_bits(rate_bits: int) -> None:
    if not isinstance(rate_bits, int):
        raise TypeError("rate_bits must be int")
    if rate_bits <= 0:
        raise ValueError("rate_bits must be positive")


def parse_bitstring(data: BitString, rate_bits: int) -> ParsedBitString:
    """Implement Algorithm 1 parse(X, r)."""
    check_rate_bits(rate_bits)
    full_count: int = len(data) // rate_bits
    full_blocks: list[BitString] = []
    for block_index in range(full_count):
        start: int = block_index * rate_bits
        full_blocks.append(BitString(data.bits[start : start + rate_bits]))
    final_start: int = full_count * rate_bits
    final_block: BitString = BitString(data.bits[final_start:])
    return ParsedBitString(tuple(full_blocks), final_block, rate_bits)


def pad_bitstring(data: BitString, rate_bits: int) -> BitString:
    """Implement Algorithm 2 pad(X, r): X || 1 || 0^j."""
    check_rate_bits(rate_bits)
    zero_count: int = (-len(data) - 1) % rate_bits
    return BitString(data.bits + (1,) + ((0,) * zero_count))
