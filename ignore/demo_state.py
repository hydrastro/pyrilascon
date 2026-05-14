from ascon_hwmodel.state import AsconState
from ascon_hwmodel.uint import U64
from ascon_hwmodel.verilog import emit_verilog_state_include


state = AsconState(
    U64(0x0001_0203_0405_0607),
    U64(0x1011_1213_1415_1617),
    U64(0x2021_2223_2425_2627),
    U64(0x3031_3233_3435_3637),
    U64(0x4041_4243_4445_4647),
)

print("words:", state.hex_words())
print("u320 :", state.to_u320().verilog_literal())
print("bytes little/x0_first:", state.to_bytes("little", "x0_first").hex())
print()
print(emit_verilog_state_include())
