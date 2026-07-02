# Tang Nano 20K — NEORV32 + ASCON-AEAD128 benchmark

This target compares two implementations on the same 27 MHz NEORV32 RV32I
processor:

1. the portable C ASCON-AEAD128 reference implementation;
2. the ASCON hardware accelerator accessed through the NEORV32 CFS MMIO window.

The firmware checks encryption, authenticated decryption, ciphertext/tag/plaintext
agreement, and rejection of a deliberately corrupted tag. It reports both:

- **end-to-end cycles**: complete CPU-visible driver/MMIO call latency;
- **core cycles**: accelerator-internal busy time only.

Use end-to-end speedup in performance claims.

## Reproducible workflow

Run from the repository root unless stated otherwise.

```bash
nix develop
make repo-audit
make test
make tn20k-doctor
make tn20k-sanity
make tn20k-rebuild
make tn20k-detect
make tn20k-prog-sram
```

The build embeds the firmware into 32 KiB of pre-initialized NEORV32 IMEM.
There is no separate UART bootloader upload step.

Find the stable UART path:

```bash
ls -l /dev/serial/by-id/
```

Capture one complete run. The capture waits for the board reset key and exits
automatically on the firmware's final `PASS` or `FAIL` line:

```bash
make tn20k-capture \
  SERIAL=/dev/serial/by-id/usb-SIPEED_USB_Debugger_<id>-if01-port0
```

Press **S1/KEY1 once** after the capture command opens the port. Then generate
strict Markdown, CSV, and JSON reports:

```bash
make tn20k-report
cat build/neorv32_mmio_20k/uart_report.md
```

Only after the SRAM run and report pass, write the image to persistent flash:

```bash
make tn20k-prog-flash
```

Do not keep a serial monitor open while programming the FPGA.

## Artifacts

```text
build/neorv32_mmio_20k/tangnano20k_neorv32_mmio_top.fs
build/neorv32_mmio_20k/tangnano20k_neorv32_mmio_top_pnr_report.json
boards/tangnano20k/neorv32_mmio/uart_mmio.log
build/neorv32_mmio_20k/uart_report.md
build/neorv32_mmio_20k/uart_report.csv
build/neorv32_mmio_20k/uart_report.json
```

All of these are generated and ignored by Git.

## Clean rebuild

```bash
make -C boards/tangnano20k/neorv32_mmio clean
make tn20k-rebuild
```

To remove all reproducible local dependencies as well:

```bash
make distclean
nix develop
```
