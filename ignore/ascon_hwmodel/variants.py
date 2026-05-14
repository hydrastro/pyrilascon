from enum import Enum


class AsconVariant(str, Enum):
    AEAD128 = "Ascon-AEAD128"
    HASH256 = "Ascon-Hash256"
    XOF128 = "Ascon-XOF128"
    CXOF128 = "Ascon-CXOF128"


def verilog_identifier(variant: AsconVariant) -> str:
    return variant.value.upper().replace("ASCON-", "ASCON_").replace("-", "_")
