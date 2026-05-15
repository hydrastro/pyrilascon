# Benchmarks

This directory is reserved for measured and estimated performance records.

- `estimates/`: architecture-level estimates generated before synthesis or board testing.
- `results/`: measured board or simulator benchmark records.

Measured records should use the JSON fields documented in `docs/benchmark_methodology.md` and produced by `ascon_arch.benchmarking.BenchmarkResult.to_dict()`.

## NEORV32 on-device benchmark

The first on-device benchmark firmware lives in:

```text
firmware/neorv32_ascon_benchmark/
```

It compares the hardware accelerator against the portable C Ascon-AEAD128
reference in `firmware/ascon_ref`. The acceptance rule is that hardware cycles
must be lower than software cycles for each mode advertised by the accelerator
capability register. See `docs/neorv32_benchmark_firmware.md` for details.
