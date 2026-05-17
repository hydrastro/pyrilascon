# Project status report generator

`tools/generate_project_status_report.py` creates a deterministic implementation and verification snapshot for the current ASCON FPGA/ASIC generator repository.

The report is useful at this stage because the project now contains several distinct layers:

- Python golden model and KAT baseline
- AXI-stream AEAD128 transaction model
- stream-native encryption RTL
- buffered authenticated decrypt RTL
- unified stream backend
- firmware driver sequencing and AXI-stream emulator
- CPU-driven AXI-stream MMIO bridge
- integrated CSR + bridge + stream-system simulation
- NEORV32 CFS wrapper
- Tang Nano 9K board manifest/package/preflight/session/Gowin handoff

The status report makes those layers explicit and separates **implemented/verified repository evidence** from **remaining physical-board work**.

## Generate the report

```sh
make project-status-report
```

This writes:

```text
build/project_status/project_status.json
build/project_status/project_status.md
```

The tool can also be invoked directly:

```sh
PYTHONPATH=. python tools/generate_project_status_report.py --check
PYTHONPATH=. python tools/generate_project_status_report.py --json
PYTHONPATH=. python tools/generate_project_status_report.py --markdown
```

## What `--check` validates

The check mode does not run synthesis or program hardware. It verifies that each declared milestone has concrete repository evidence, such as source files, tests, simulation tools, board handoff scripts, and documentation.

It fails if any milestone evidence is missing.

## How to interpret the status

A successful report means the repository is ready for the next hard gate:

```text
real Tang Nano / NEORV32 build plus UART benchmark report
```

It does **not** mean the final hardware performance claim is complete. The remaining proof requires a programmed board, captured UART output, and a strict UART report generated with:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio uart-report LOG=/path/to/uart.log
```
