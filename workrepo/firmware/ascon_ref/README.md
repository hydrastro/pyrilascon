# Portable ASCON reference firmware

This directory contains small portable C reference code used by firmware-side
benchmarking. It is not intended to replace the Python golden model or the
known-answer-vector tests. Its role is to provide an on-device software baseline
when running on NEORV32.

Currently implemented:

```text
Ascon-AEAD128 encrypt/decrypt
```

The reference follows the same NIST little-endian state convention as the Python
model and RTL:

```text
S0/x0 -> state bits [63:0]
S4/x4 -> state bits [319:256]
```

The decrypt function uses constant-time tag comparison and clears the plaintext
buffer when authentication fails.
