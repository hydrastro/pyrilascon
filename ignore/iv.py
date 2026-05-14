from dataclasses import dataclass
from typing import Final, Mapping, Sequence

from ascon_hwmodel.uint import FixedUInt, U4, U8, U16, U64
from ascon_hwmodel.variants import AsconVariant


@dataclass(frozen=True, slots=True)
class IVParams:
    """Parameters used to construct one 64-bit Ascon initial value."""

    variant: AsconVariant
    v: U8
    a: U4
    b: U4
    t: U16
    rate_bytes: U8

    def build(self) -> U64:
        """Build IV as the numeric 64-bit word used by the NIST state model.

        Appendix B writes the field formula as:
            V || 0^8 || a || b || t || r/8 || 0^16

        The corresponding hexadecimal IV table represents V in bits [7:0].
        Therefore the Python numeric packing below is least-significant-field
        first. A Verilog concatenation writes the same value in reverse order:
            {16'h0000, rate_bytes, t, b, a, 8'h00, v}
        """
        return pack_lsf_u64((self.v, U8(0), self.a, self.b, self.t, self.rate_bytes, U16(0)))


def pack_lsf_u64(fields: Sequence[FixedUInt]) -> U64:
    """Pack fields into a U64 with fields[0] occupying the least-significant bits."""
    shift: int = 0
    value: int = 0
    for field in fields:
        value |= field.value << shift
        shift += field.WIDTH
    if shift != 64:
        raise ValueError(f"packed width must be exactly 64 bits, got {shift}")
    return U64(value)


IV_PARAMS: Final[Mapping[AsconVariant, IVParams]] = {
    AsconVariant.AEAD128: IVParams(
        variant=AsconVariant.AEAD128,
        v=U8(1),
        a=U4(12),
        b=U4(8),
        t=U16(128),
        rate_bytes=U8(16),
    ),
    AsconVariant.HASH256: IVParams(
        variant=AsconVariant.HASH256,
        v=U8(2),
        a=U4(12),
        b=U4(12),
        t=U16(256),
        rate_bytes=U8(8),
    ),
    AsconVariant.XOF128: IVParams(
        variant=AsconVariant.XOF128,
        v=U8(3),
        a=U4(12),
        b=U4(12),
        t=U16(0),
        rate_bytes=U8(8),
    ),
    AsconVariant.CXOF128: IVParams(
        variant=AsconVariant.CXOF128,
        v=U8(4),
        a=U4(12),
        b=U4(12),
        t=U16(0),
        rate_bytes=U8(8),
    ),
}


EXPECTED_IV: Final[Mapping[AsconVariant, U64]] = {
    AsconVariant.AEAD128: U64(0x0000_1000_808C_0001),
    AsconVariant.HASH256: U64(0x0000_0801_00CC_0002),
    AsconVariant.XOF128: U64(0x0000_0800_00CC_0003),
    AsconVariant.CXOF128: U64(0x0000_0800_00CC_0004),
}


def ascon_iv(variant: AsconVariant) -> U64:
    return IV_PARAMS[variant].build()


def assert_iv_table() -> None:
    for variant, expected in EXPECTED_IV.items():
        actual: U64 = ascon_iv(variant)
        if actual != expected:
            raise AssertionError(
                f"{variant.value}: got 0x{actual.hex()}, expected 0x{expected.hex()}"
            )
