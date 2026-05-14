from ascon_hwmodel import BitString, AsconState, pad_bytes, parse_bytes

state = AsconState.from_bytes(bytes(range(40)))
print("state words:")
for index, word in enumerate(state.words()):
    print(f"S{index} = 0x{word.hex()}")

bits = BitString.from_bytes(bytes([0x01, 0x02, 0x80]))
print("\nbitstring:", bits.bit_string())

parsed = parse_bytes(bytes(range(20)), 16)
print("\nfull byte blocks:", [block.hex() for block in parsed.full_blocks])
print("final byte block:", parsed.final_block.hex())
print("padded final block:", parsed.padded_final_block().hex())

print("\npad 7-byte final block to 8 bytes:", pad_bytes(b"\xff" * 7, 8).hex())
