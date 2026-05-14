from ascon_hwmodel import AsconVariant, ascon_iv, assert_iv_table, emit_verilog_iv_include


if __name__ == "__main__":
    assert_iv_table()
    for variant in AsconVariant:
        print(f"{variant.value:16s} 0x{ascon_iv(variant).hex()}")
    print()
    print(emit_verilog_iv_include())
