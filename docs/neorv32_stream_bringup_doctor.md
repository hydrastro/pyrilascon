# NEORV32 stream board bring-up doctor

`tools/neorv32_stream_bringup_doctor.py` checks the host-side prerequisites for the
Tang Nano 9K NEORV32 stream-ASCON bring-up before you build firmware or open the
UART port.

The doctor is intentionally non-invasive: it does not synthesize, program the
FPGA, or open the serial device. It reports blockers and next actions for:

- `NEORV32_HOME` correctness;
- the generated board package and Gowin handoff directories;
- `picocom` availability;
- `openFPGALoader` availability;
- optional serial-device existence and read/write permission.

## Typical usage

```sh
# First regenerate the board handoff.
make neorv32-stream-gowin-handoff

# Check the local bring-up environment. Replace paths with real values.
make neorv32-stream-bringup-doctor NEORV32_HOME=/actual/path/to/neorv32 SERIAL=/dev/ttyUSB0
```

The target writes:

```text
build/neorv32_stream_axis_mmio/bringup_doctor.json
build/neorv32_stream_axis_mmio/bringup_doctor.md
```

## Interpreting common failures

### `NEORV32_HOME` still points at `/path/to/neorv32`

That path is only a documentation placeholder. Point it at an actual NEORV32
checkout that contains:

```text
sw/common/common.mk
```

Example:

```sh
make neorv32-fetch
make neorv32-stream-build-firmware
```

### UART permission denied

If `picocom` reports permission denied for `/dev/ttyUSB0`, inspect the device:

```sh
ls -l /dev/ttyUSB0
```

Add your user to the group shown by the device, then start a new login shell. On
many Linux systems this is `dialout`; on some systems it may be another group.
For a quick one-off smoke test, a root/sudo serial capture can also confirm that
the hardware is alive, but the durable fix is group membership.

### Empty or incomplete UART log

`make neorv32-stream-uart-report LOG=uart.log` expects a completed benchmark log
from the NEORV32 firmware. If the UART tool never opened the port or the FPGA was
not programmed/running the benchmark, strict parsing will report missing fields
such as `ABI`, `CAPS`, `SW CT`, and `SW cycles`.

## UART capture helper

The flake dev shell now includes `picocom`. After fixing serial permissions and
programming the board, capture the UART with:

```sh
make neorv32-stream-uart-capture SERIAL=/dev/ttyUSB0 LOG=uart.log
```

Then parse it:

```sh
make neorv32-stream-uart-report LOG=uart.log
```
