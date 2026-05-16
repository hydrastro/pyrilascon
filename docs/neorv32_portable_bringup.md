# Portable NEORV32/Tang Nano stream bring-up

This project does not assume that every developer has the same checkout layout,
Linux group configuration, or serial-device name.  The board flow now uses a
portable dependency layer around the two machine-specific inputs that remain
outside the repository: the upstream NEORV32 checkout and the board UART device.

## NEORV32 checkout policy

The ASCON repository does not vendor NEORV32.  A machine can provide NEORV32 in
one of three ways, in priority order:

1. pass `NEORV32_HOME=/explicit/neorv32` for a lab-managed checkout;
2. export `NEORV32_HOME` in the shell;
3. use the project-local default `external/neorv32`.

No helper probes `$HOME/src` or other user-specific locations implicitly.

For a reproducible project-local setup, run:

```sh
make neorv32-fetch
```

To print the checkout path that the tools will use:

```sh
make neorv32-home
```

The checkout is accepted only if it contains:

```text
sw/common/common.mk
```

This keeps the firmware build independent of a developer's home-directory
layout.

## UART device policy

UART capture can use an explicit device:

```sh
make neorv32-stream-uart-capture SERIAL=/dev/ttyUSB0 LOG=uart.log
```

If `SERIAL` is omitted, the capture helper attempts to auto-detect a unique
usable serial device from:

```text
/dev/serial/by-id/*
/dev/ttyUSB*
/dev/ttyACM*
/dev/cu.usbserial*
/dev/cu.usbmodem*
```

If no usable device or multiple usable devices are found, the helper prints the
candidate list and asks for `SERIAL=...` explicitly.  This avoids hardcoding
`/dev/ttyUSB0` into the flow.

## Bring-up doctor

Use the doctor before firmware build or UART capture:

```sh
make neorv32-stream-bringup-doctor
make neorv32-stream-bringup-doctor SERIAL=/dev/ttyUSB0
```

The doctor reports:

- how NEORV32 was resolved;
- whether `sw/common/common.mk` exists;
- detected serial candidates;
- serial permissions;
- required tools such as `picocom`, `make`, Python, and `openFPGALoader`;
- the next action needed to unblock board bring-up.

## Portable sequence

```sh
nix develop
make neorv32-fetch
make neorv32-stream-gowin-handoff
make neorv32-stream-bringup-doctor
make neorv32-stream-build-firmware
```

After integrating/building/programming the FPGA image, capture and parse UART:

```sh
make neorv32-stream-uart-capture LOG=uart.log
make neorv32-stream-uart-report LOG=uart.log
```

The UART report still requires real benchmark output from a programmed board.
An empty or failed capture is intentionally rejected.
