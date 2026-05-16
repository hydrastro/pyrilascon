# NEORV32 stream board session runner

The board session runner is the last host-side handoff step before real Tang
Nano 9K programming and UART capture. It validates the generated stream board
package, records the expected programming command, and optionally embeds a parsed
UART benchmark report.

It is safe by default: hardware programming is never attempted unless
`--program --no-dry-run` are both supplied.

## Root target

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio session
```

This generates:

```text
build/neorv32_stream_axis_mmio/session/session.json
build/neorv32_stream_axis_mmio/session/session.md
```

The default report validates the board package and records the memory map,
firmware mode, CFS wrapper, programming tool availability, and next actions.

## Include a UART log

After capturing a real benchmark log from the board:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio session LOG=/path/to/uart.log
```

The session report embeds the strict UART benchmark parser output. The report is
useful for archiving one complete board run together with the package/build-plan
state that produced it.

## Record a bitstream

To include the expected programming command without touching hardware:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio session BITSTREAM=build/tangnano9k/ascon.fs
```

The session report records:

```text
openFPGALoader -b tangnano9k build/tangnano9k/ascon.fs
```

## Manual CLI

```sh
PYTHONPATH=. python tools/run_neorv32_stream_board_session.py \
  --ensure-package \
  --bitstream build/tangnano9k/ascon.fs \
  --uart-log /path/to/uart.log \
  --strict-uart \
  --write-defaults
```

Use `--program --no-dry-run` only when a real bitstream and board are available:

```sh
PYTHONPATH=. python tools/run_neorv32_stream_board_session.py \
  --bitstream build/tangnano9k/ascon.fs \
  --program \
  --no-dry-run
```

## Relation to earlier board targets

Recommended order:

```sh
make -C boards/tangnano9k/neorv32_stream_axis_mmio manifest
make -C boards/tangnano9k/neorv32_stream_axis_mmio preflight
make -C boards/tangnano9k/neorv32_stream_axis_mmio package
make -C boards/tangnano9k/neorv32_stream_axis_mmio build-plan
make -C boards/tangnano9k/neorv32_stream_axis_mmio session
```

Then synthesize/program the board, capture UART output, and re-run the session
with `LOG=/path/to/uart.log`.
