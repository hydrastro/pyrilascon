from ascon_hwmodel import AsconState, ascon_p6, ascon_p8, ascon_p12, emit_verilog_model_include

state = AsconState.zero()
for name, func in (("p6", ascon_p6), ("p8", ascon_p8), ("p12", ascon_p12)):
    out = func(state)
    print(name)
    for index, word in enumerate(out.hex_words()):
        print(f"  x{index} = 0x{word}")

with open("ascon_model_include.vh", "w", encoding="utf-8") as fh:
    fh.write(emit_verilog_model_include())
