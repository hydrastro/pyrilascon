# Decryption release, side-channel, and fault-detection architecture

This layer separates two concerns:

1. **Decryption release policy**: decrypted plaintext must not be externally released until the authentication tag has verified. This is enforced independently of the selected side-channel/fault profile.
2. **Security/fault countermeasures**: optional implementation hardening such as counter hardening, constant-time tag compare, duplicate-computation fault detection, and future masking/threshold S-box backends.

## Decryption release policy

The configured release policy is:

```text
buffer_until_tag_verify
```

For AEAD decryption, plaintext produced while processing ciphertext is written into a FIFO/RAM-style release buffer. The output side remains suppressed until tag verification succeeds. On failure, the buffer must be dropped/zeroized.

This is intentionally non-negotiable for both ASIC and FPGA configs.

## Security profiles

| Profile | Intent |
|---|---|
| `none` | No side-channel or fault countermeasures. Safe decrypt buffering remains enabled. |
| `asic_rand_counter_consttime_tag` | ASIC baseline: randomized/control counter hardening plus constant-time tag compare. |
| `fpga_fault_detect_rand_counter_consttime_tag` | FPGA baseline: duplicate-computation fault detection, randomized/control counter hardening, constant-time tag compare. |
| `duplicate_compute` | Explicit redundant-computation fault-detection profile. |
| `first_order_masked` | Placeholder/profile for future serious first-order masked ASIC backend. |
| `threshold_sbox` | Placeholder/profile for future threshold-implementation S-box backend. |

## Defaults

ASIC default:

```text
security.profile = asic_rand_counter_consttime_tag
plaintext release = buffer_until_tag_verify
plaintext buffer storage = sram_fifo
```

FPGA default:

```text
security.profile = fpga_fault_detect_rand_counter_consttime_tag
plaintext release = buffer_until_tag_verify
plaintext buffer storage = bram_fifo
```

## Generated RTL boundaries

The design generator now emits:

```text
ascon_<name>_security.sv
ascon_<name>_decrypt_plaintext_buffer.sv
```

These are still structural scaffolds. The security module contains the constant-time tag-compare shape, and the plaintext buffer module preserves the release-policy contract for later FIFO/RAM implementation.
