# Benchmarks

This directory is reserved for measured and estimated performance records.

- `estimates/`: architecture-level estimates generated before synthesis or board testing.
- `results/`: measured board or simulator benchmark records.

Measured records should use the JSON fields documented in `docs/benchmark_methodology.md` and produced by `ascon_arch.benchmarking.BenchmarkResult.to_dict()`.
