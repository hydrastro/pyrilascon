# Datapath-width architecture profiles

The datapath-width profile is independent from the permutation profile. This is
intentional: a design can use a byte-oriented external interface while using a
5-bit S-box-serial permutation core, or a 128-bit absorb datapath with a deeply
pipelined permutation.

## Profiles

| Profile | Main lane | Absorb slice | Area intuition | Performance intuition | Notes |
|---|---:|---:|---|---|---|
| `128_bit` | 128 | 128 | medium/high | best single-engine rate handling | FPGA default |
| `64_bit` | 64 | 64 | medium | good | balanced baseline |
| `32_bit` | 32 | 32 | small/medium | moderate | useful for narrower embedded buses |
| `16_bit` | 16 | 16 | small | moderate/low | ASIC candidate if 8-bit is too slow |
| `8_bit_serial` | 8 | 8 | very small | low | strong ASIC fit when I/O is the bottleneck |
| `1_bit_serial` | 1 | 1 | tiny | very low | extreme area exploration |
| `5bit_sbox_serial` | 5 | 8 | tiny | very low | byte I/O plus a 5-bit physical S-box datapath |

## Cycle estimates

The planning model uses simple ceiling estimates for block movement:

```text
absorb128_cycles = ceil(128 / absorb_width)
absorb64_cycles  = ceil(64  / absorb_width)
key128_cycles    = ceil(128 / lane_width)
tag128_cycles    = ceil(128 / lane_width)
state320_cycles  = ceil(320 / lane_width)
```

These are not final cycle-accurate RTL estimates. They are design-space metadata
used to compare configurations and catch obviously inconsistent combinations.

## Current target defaults

FPGA default:

```text
topology: N parallel engines
datapath profile: 128_bit
permutation profile: fully_pipelined
```

ASIC exploration points:

```text
baseline:        64_bit, one round/cycle
likely tiny fit: 8_bit_serial, column-serial permutation
alternative:     16_bit, column-serial permutation
extreme:         5bit_sbox_serial or 1_bit_serial
```

The `8_bit_serial` ASIC point is currently the most practical tiny baseline
because byte I/O, padding, and length handling remain natural. The 5-bit and
1-bit profiles are kept for extreme area exploration and require more careful
control scheduling.
