# NEORV32 UART benchmark report parser

After the Tang Nano 9K / NEORV32 stream build runs on hardware, the benchmark
firmware prints a UART transcript containing software reference output,
hardware accelerator output, cycle counts, AXI-MMIO beat counters, and final
`PASS`/`FAIL` status.

The parser in `tools/parse_neorv32_ascon_uart_log.py` converts that text log
into JSON or Markdown so board runs can be archived and compared without manual
copy/paste inspection.

## Usage

From the repository root:

```sh
PYTHONPATH=. python tools/parse_neorv32_ascon_uart_log.py uart.log --strict --json
PYTHONPATH=. python tools/parse_neorv32_ascon_uart_log.py uart.log --strict --markdown --out build/neorv32_stream_axis_mmio/uart_report.md
```

Or through the Makefile:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio uart-report LOG=uart.log
```

The board-local wrapper also exposes:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio uart-report LOG=/path/to/uart.log
```

## Strict checks

`--strict` fails if the log does not contain the expected pass/correctness
signals. It checks:

- `PASS` is present;
- software and hardware ciphertext match;
- software and hardware tags match;
- encrypt/decrypt driver status codes are zero;
- AXI-MMIO transport status is zero when printed;
- hardware encrypt/decrypt cycle counts are lower than the software reference
  cycle count when those fields are present.

Warnings printed by the firmware are preserved in the report. Fatal firmware
`FAIL:` and `ERROR:` lines are preserved and cause strict mode to fail.

## Report fields

The JSON report includes:

- selected data plane and AXI bridge base;
- ABI and capability register values;
- software ciphertext, tag, and cycle count;
- hardware ciphertext, tag, plaintext, encrypt/decrypt cycle counts, status,
  tag-valid bit, error code, and speedup;
- AXI-MMIO TX/RX beat counters;
- machine-readable boolean checks.

The Markdown report is intended for lab notes and project documentation.
