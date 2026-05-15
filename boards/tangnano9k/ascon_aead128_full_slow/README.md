# Tang Nano 9K: full Ascon-AEAD128 slow KAT target

This target runs a fixed full Ascon-AEAD128 encryption KAT and a fixed full
Ascon-AEAD128 decryption KAT in hardware. It is still a board-level smoke test,
not the final streaming accelerator.

The design uses one Ascon round per cycle. It is deliberately slow and simple so
that it is easy to fit and debug on the Tang Nano 9K before integrating NEORV32.

## Build and program SRAM

```sh
nix develop
cd boards/tangnano9k/ascon_aead128_full_slow
make clean
make tools
make
make prog-sram
```

Use SRAM during development. Flash only after the design is stable:

```sh
make prog-flash
```

## LED meaning

Tang Nano 9K LEDs are active-low.

| LED | Meaning |
| --- | --- |
| LED0 | heartbeat |
| LED1 | encryption KAT passed |
| LED2 | decryption KAT passed |
| LED3 | failure indicator, on when either KAT failed |
| LED4 | both KAT cores done |
| LED5 | final pass: encryption pass and decryption pass and no failure |

A good run leaves LED1, LED2, LED4, and LED5 on, LED3 off, and LED0 blinking.

## What is tested

The fixed vector exercises:

- initialization
- associated-data processing
- plaintext processing
- ciphertext processing
- finalization
- tag generation
- tag verification
- decryption plaintext buffering until tag verification succeeds

The test vector uses:

- key: `000102030405060708090a0b0c0d0e0f`
- nonce: `101112131415161718191a1b1c1d1e1f`
- associated data: `AD123`
- plaintext: `hello ASCON hardware model`
