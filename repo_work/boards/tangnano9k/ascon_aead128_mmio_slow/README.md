# Tang Nano 9K ASCON-AEAD128 MMIO Slow Target

This target exercises the frozen accelerator MMIO ABI on real hardware.
It instantiates:

- `ascon_accel_mmio_regs`
- `ascon_aead128_mmio_backend`
- a small on-chip MMIO KAT controller

The controller performs one encryption KAT and one decryption KAT through the
same 32-bit register interface that future NEORV32 firmware will use.

## Build and program

```bash
nix develop
cd boards/tangnano9k/ascon_aead128_mmio_slow
make clean
make tools
make
make prog-sram
```

## Expected LEDs

Tang Nano 9K LEDs are active-low.

| LED | Meaning |
| --- | --- |
| LED0 | heartbeat |
| LED1 | encryption through MMIO passed |
| LED2 | decryption through MMIO passed |
| LED3 | failure indicator |
| LED4 | test completed |
| LED5 | final pass |

A good run has LED1, LED2, LED4, LED5 on, LED3 off, and LED0 blinking.
