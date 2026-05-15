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
