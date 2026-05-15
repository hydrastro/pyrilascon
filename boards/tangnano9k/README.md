# Tang Nano 9K board targets

Use these targets from inside the repository root after installing the open-source Gowin flow (`yosys`, `nextpnr-gowin`, `gowin_pack`, `openFPGALoader`).

## Full AEAD128 KAT smoke test

```sh
cd boards/tangnano9k/ascon_aead128_kat_slow
make
make prog-sram
```

This is the first required target for this project because it exercises the full Ascon-AEAD128 flow in hardware, not just the permutation.

## p12 pipeline experiment

```sh
cd boards/tangnano9k/ascon_p12_pipeline
make
make prog-sram
```

This is only a high-throughput permutation experiment. It is useful later, but it is not a full AEAD accelerator.

## Full AEAD128 encrypt+decrypt slow KAT

```sh
cd boards/tangnano9k/ascon_aead128_full_slow
make
make prog-sram
```

This target runs both a fixed encryption KAT and a fixed decryption KAT. It is the
current standalone full-AEAD smoke test before NEORV32 integration.

## ascon_aead128_mmio_slow

This target exercises the frozen 32-bit accelerator MMIO register map on the FPGA.
It is the bridge target before NEORV32 integration: an on-chip test controller
writes the same registers that firmware will write, then verifies encryption and
decryption KAT outputs.

```bash
cd boards/tangnano9k/ascon_aead128_mmio_slow
make clean
make tools
make
make prog-sram
```

Expected pass indication: LED1, LED2, LED4, and LED5 on; LED3 off; LED0 blinking.


## ascon_aead128_axis_slow

Validates the FPGA-facing split interface: CSR/MMIO control plus AXI Stream payload data.  This is the first board-level AXI Stream smoke test and should pass before replacing the backend with a higher-throughput implementation.

```sh
cd boards/tangnano9k/ascon_aead128_axis_slow
make clean
make tools
make
make prog-sram
```

Expected LEDs: LED0 blinking, LED1/LED2/LED4/LED5 on, LED3 off.
