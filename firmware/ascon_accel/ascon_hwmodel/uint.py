from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class FixedUInt:
    """Unsigned fixed-width integer for hardware-oriented modeling.

    The class intentionally stays small and explicit: no implicit widening, no
    signed interpretation, and no hidden bit growth. This makes it easier to
    translate later into Verilog expressions.
    """

    value: int

    WIDTH: ClassVar[int] = 0

    def __post_init__(self) -> None:
        if self.WIDTH <= 0:
            raise TypeError(f"{type(self).__name__}.WIDTH must be positive")
        if not isinstance(self.value, int):
            raise TypeError(f"{type(self).__name__}.value must be int")
        if self.value < 0 or self.value >= (1 << self.WIDTH):
            raise ValueError(
                f"{type(self).__name__} value {self.value} does not fit in {self.WIDTH} bits"
            )

    @property
    def mask(self) -> int:
        return (1 << self.WIDTH) - 1

    def to_int(self) -> int:
        return self.value

    def hex(self, group: bool = True) -> str:
        digits: int = (self.WIDTH + 3) // 4
        raw: str = f"{self.value:0{digits}X}"
        if not group:
            return raw
        groups: list[str] = []
        while raw:
            groups.append(raw[-4:])
            raw = raw[:-4]
        return "_".join(reversed(groups))

    def verilog_literal(self) -> str:
        return f"{self.WIDTH}'h{self.hex()}"


@dataclass(frozen=True, slots=True)
class U4(FixedUInt):
    WIDTH: ClassVar[int] = 4


@dataclass(frozen=True, slots=True)
class U8(FixedUInt):
    WIDTH: ClassVar[int] = 8


@dataclass(frozen=True, slots=True)
class U16(FixedUInt):
    WIDTH: ClassVar[int] = 16


@dataclass(frozen=True, slots=True)
class U64(FixedUInt):
    WIDTH: ClassVar[int] = 64


@dataclass(frozen=True, slots=True)
class U128(FixedUInt):
    WIDTH: ClassVar[int] = 128


@dataclass(frozen=True, slots=True)
class U320(FixedUInt):
    WIDTH: ClassVar[int] = 320
