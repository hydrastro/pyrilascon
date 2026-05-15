# Padding and length-handling architecture

This axis describes how the RTL discovers the final block length and where the
Ascon `pad10*` operation is performed. It is deliberately separate from the
external interface and from the datapath width.

## Profiles

| Profile | Area | Flexibility | Intended use | Notes |
| --- | --- | --- | --- | --- |
| `rtl_performed` | medium | medium | ASIC baseline | The core tracks byte count / final block state and inserts padding internally. |
| `full_arbitrary_bytelength` | medium-high | high | eventual full-feature core | Descriptor or explicit length field supplies the total byte length. Useful for DMA and software-controlled flows. |
| `streaming_final_bytemask` | medium | high | FPGA streaming baseline | The final stream beat carries a byte-valid mask. The core pads the invalid tail bytes without buffering the whole message. |

## What is streaming final bytemask?

For a byte stream with `valid/ready`, `last_i` marks the last beat. A `keep_i`
or `byte_valid_i` mask marks which bytes on that final beat are real message
bytes. For a 128-bit bus, the mask is 16 bits:

```text
DATA_BUS_BITS = 128
KEEP_BITS     = 16
```

Example: if the last beat contains five real bytes, the mask can be
`0000_0000_0001_1111` in LSB-byte-first convention. The padding unit then
places the Ascon `1` padding bit immediately after byte 4 and clears the
remaining tail bytes as required by the selected rate operation.

This is efficient for FPGA packet/stream systems because the upstream interface
already knows which bytes are valid on the last beat. The core does not need an
arbitrary-length descriptor for the common streaming case.

## Project defaults

Current selected defaults:

```text
ASIC: rtl_performed
FPGA: streaming_final_bytemask
```

The `full_arbitrary_bytelength` profile remains available for DMA-fed or
software-descriptor products.

## Relation to byte/bit granularity

The current architecture profiles are byte-oriented. Bit-granular KAT support
can be added later, but it should be a distinct profile because it changes final
mask semantics and padding insertion.
