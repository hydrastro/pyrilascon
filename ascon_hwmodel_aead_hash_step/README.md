# Ascon hardware-oriented Python model

This package is a typed Python model of selected NIST SP 800-232 Ascon building blocks, written so the model structure maps cleanly to Verilog.

Implemented so far:

- fixed-width unsigned integer wrappers: `U4`, `U8`, `U16`, `U64`, `U128`, `U320`
- separated byte-sequence hex and integer hex views
- bitstring and byte-oriented `parse` / `pad`
- Ascon IV construction for AEAD128, Hash256, XOF128, and CXOF128
- little-endian five-word Ascon state model
- 64-bit and 128-bit block wrappers
- 64-bit and 128-bit rate absorption helpers
- AEAD128 key/nonce initial-state construction
- AEAD128 key injection helpers
- AEAD associated-data domain separator
- split Ascon permutation layers: `pc.py`, `ps.py`, `pl.py`
- substitution layer implemented both as `p_s_lut()` and `p_s_bitsliced()`
- split permutation wrappers: `p6.py`, `p8.py`, `p12.py`
- Verilog emission colocated with the Python model object/layer it describes
- generated `.vh` include fragments and standalone `.v` combinational wrappers
- byte-aligned known-answer tests for NIST AEAD128, Hash256, XOF128, and CXOF128

## Run tests

From the package root:

```bash
python -m pytest -q
```

Expected result for this step:

```text
45 passed
```


## Known-answer tests

`tests/test_known_answer_vectors.py` embeds a compact byte-aligned KAT subset:

- Ascon-AEAD128 encrypt/decrypt vectors from the official `ascon/ascon-c` LWC KAT file
- Ascon-Hash256 empty-message digest
- Ascon-XOF128 empty-message 512-bit output
- Ascon-CXOF128 single-byte message with empty customization string

The current test scope is deliberately byte-aligned. Full ACVP bit-length coverage will require bit-granular hash/XOF wrappers on top of `bitstring.py`.

## Endianness convention

The state is modeled as five 64-bit integer words:

```text
x0 = S[0:63]
x1 = S[64:127]
x2 = S[128:191]
x3 = S[192:255]
x4 = S[256:319]
```

A 40-byte state image is loaded little-endian word by word. For example, bytes `00 01 02 03 04 05 06 07` become the integer word `0x0706050403020100`.

A Verilog `[319:0]` state bus preserves the logical bit index:

```verilog
state[63:0]    = x0;
state[127:64]  = x1;
state[191:128] = x2;
state[255:192] = x3;
state[319:256] = x4;
```

Therefore state packing is:

```verilog
state = {x4, x3, x2, x1, x0};
```

## S-box implementation policy

The substitution layer has two equivalent Python views:

- `p_s_lut(state)`: reference model using 64 scalar 5-bit S-box table lookups
- `p_s_bitsliced(state)`: hardware-shaped model using word-level boolean operations

`p_s(state)` currently aliases `p_s_bitsliced(state)`, because that representation maps directly to combinational RTL and is much faster in Python than looping through 64 single-bit slices.

Generated Verilog also emits both:

- `ascon_p_s_lut`
- `ascon_p_s_bitsliced`
- `ascon_p_s`, which currently calls the bitsliced implementation

## Verilog generation policy

The Verilog generation code is colocated with the Python model layer it describes:

```text
iv.py       -> IV Verilog helpers
state.py    -> state pack/access helpers
byteops.py  -> pad helpers
pc.py       -> p_C and round constant helpers
ps.py       -> p_S LUT and bitsliced helpers
pl.py       -> p_L and rotation helpers
round.py    -> round composition helper
p6.py       -> Ascon-p[6] helper and standalone wrapper
p8.py       -> Ascon-p[8] helper and standalone wrapper
p12.py      -> Ascon-p[12] helper and standalone wrapper
domain.py   -> AEAD domain separator helper
keyops.py   -> AEAD128 key/init/finalization helpers
```

`ascon_hwmodel/verilog.py` is only an aggregation/file-writing facade.

Generate Verilog files with:

```bash
PYTHONPATH=. python tools/generate_verilog.py
```

This writes:

```text
rtl/generated/ascon_iv.vh
rtl/generated/ascon_state.vh
rtl/generated/ascon_aux.vh
rtl/generated/ascon_pc.vh
rtl/generated/ascon_ps.vh
rtl/generated/ascon_pl.vh
rtl/generated/ascon_round.vh
rtl/generated/ascon_p6.vh
rtl/generated/ascon_p8.vh
rtl/generated/ascon_p12.vh
rtl/generated/ascon_aead_domain_key.vh
rtl/generated/ascon_model.vh
rtl/generated/ascon_permutation_comb.v
rtl/generated/ascon_p6_comb.v
rtl/generated/ascon_p8_comb.v
rtl/generated/ascon_p12_comb.v
```

The `.vh` files are include fragments because they define functions/localparams to be included inside a module or package scope. The `.v` files are standalone combinational module wrappers.

## AEAD encryption/decryption step

The AEAD layer is now split by phase:

```text
ascon_hwmodel/aead_config.py
ascon_hwmodel/aead_init.py
ascon_hwmodel/aead_ad.py
ascon_hwmodel/aead_plaintext.py
ascon_hwmodel/aead_ciphertext.py
ascon_hwmodel/aead_final.py
ascon_hwmodel/aead_encrypt.py
ascon_hwmodel/aead_decrypt.py
ascon_hwmodel/aead.py
```

The standardized NIST mode is `AEADVariant.NIST_AEAD128`. Legacy Ascon submission-family parameter sets are present in `aead_config.py` as scaffolds, but only the NIST mode is byte-level conformance-targeted by the current little-endian state model.

Run:

```bash
python -m pytest -q
PYTHONPATH=. python tools/generate_verilog.py
python demo_aead.py
```

Generated Verilog now includes:

```text
rtl/generated/ascon_rate.vh
rtl/generated/ascon_aead.vh
rtl/generated/ascon_hash_xof.vh
```

## Hash/XOF bonus layer

NIST byte-oriented helpers are included for:

```python
ascon_hash256(message)
ascon_xof128(message, output_bytes)
ascon_cxof128(message, output_bytes, customization)
```

These currently expose byte-aligned APIs. Bit-granular output can be layered on top of `bitstring.py` later.
