# Benchmark methodology

The project has two separate correctness/performance contracts:

1. **Correctness:** the generated hardware must match the golden Ascon model and known-answer tests.
2. **Acceleration:** any FPGA accelerator configuration that claims support for a mode must outperform the NEORV32 software implementation for that mode.

The meaningful benchmark is not Python versus FPGA. The meaningful benchmark is:

```text
NEORV32 software Ascon
vs
NEORV32 + pyrilascon accelerator
```

## Required measurements

For every benchmark record, capture:

- design name and board
- algorithm and operation
- clock frequency
- associated-data length
- plaintext/ciphertext length
- hardware accelerator cycles
- software baseline cycles, when available
- cycles per byte
- throughput in Mbit/s
- speedup versus software
- whether the output matched the known-good result

The machine-readable schema is represented by `ascon_arch.benchmarking.BenchmarkResult`.

## Hardware cycle counter

The frozen accelerator ABI exposes:

```text
CYCLE_COUNT_LO
CYCLE_COUNT_HI
```

The firmware helper `ascon_accel_cycle_count()` reads this as a stable 64-bit value. The benchmark helpers in `ascon_accel_benchmark.h` use it to measure elapsed accelerator-visible cycles around AEAD operations.

## Software baseline

The NEORV32 firmware report must also measure a software reference implementation with the CPU cycle counter. This is the baseline the accelerator must beat.

The acceptance rule is:

```text
hardware_cycles < software_cycles
```

or equivalently:

```text
speedup_vs_software > 1.0
```

## FPGA throughput targets

The architecture estimator in `ascon_arch/benchmarking.py` provides planning estimates. It is intentionally conservative and does not replace synthesis or board measurements.

For AEAD128 with a 128-bit rate:

```text
1 round/cycle:  p8 interval = 8 cycles
4 rounds/cycle: p8 interval = 2 cycles
8 rounds/cycle: p8 interval = 1 cycle
fully pipelined with enough contexts: p8 launch interval = 1 cycle
```

Sustained payload throughput is estimated as:

```text
128 bits * f_clk / p8_interval
```

Actual throughput may be lower because of input/output stalls, scheduler bubbles, DMA setup, final-block handling, or packet-size effects.

## Reporting files

Board scripts or firmware dumps should eventually write JSON records with fields matching `BenchmarkResult.to_dict()`. These can be collected under:

```text
benchmarks/results/
```

Generated estimates can be kept under:

```text
benchmarks/estimates/
```
