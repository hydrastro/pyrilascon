#!/usr/bin/env python3
"""Upload a NEORV32 executable to the on-chip bootloader and capture its output.

Robust to two realities of the Tang Nano 20K debugger:
  * it exposes two interfaces on one FT2232 - if00 = JTAG (used by openFPGALoader),
    if01 = UART. Read ONLY the UART (if01), never the JTAG side.
  * reconfiguring the FPGA briefly disturbs the USB device, so reads can throw; we
    reconnect and keep going instead of crashing.

Recommended flow (flash FIRST so JTAG is released, THEN this reads the UART):

  openFPGALoader -b tangnano20k build/soc/neorv32_ascon_soc.fs && \
    python host/neorv32_upload.py \
      /dev/serial/by-id/usb-SIPEED_USB_Debugger_2025030317-if01-port0 \
      firmware/neorv32_ascon_benchmark/neorv32_exe.bin run.log

Then:  python host/ascon_bench.py report run.log
"""
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("pyserial not found - run inside `nix develop`")

BAUD = 19200


class Link:
    """A serial link that transparently reconnects on I/O errors."""

    def __init__(self, port: str):
        self.port = port
        self.ser = None
        self.open()

    def open(self) -> None:
        try:
            self.ser = serial.Serial(self.port, BAUD, timeout=0.1)
            try:
                self.ser.dtr = False
                self.ser.rts = False
            except OSError:
                pass
        except serial.SerialException:
            self.ser = None

    def reopen(self) -> None:
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        self.ser = None
        time.sleep(0.3)
        self.open()

    def read(self, n: int = 256) -> bytes:
        if not self.ser:
            self.reopen()
            return b""
        try:
            return self.ser.read(n)
        except (serial.SerialException, OSError):
            self.reopen()
            return b""

    def write(self, data: bytes) -> None:
        if not self.ser:
            self.reopen()
        try:
            if self.ser:
                self.ser.write(data)
                self.ser.flush()
        except (serial.SerialException, OSError):
            self.reopen()

    def reset_input(self) -> None:
        try:
            if self.ser:
                self.ser.reset_input_buffer()
        except Exception:
            pass


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(f"usage: {sys.argv[0]} <serial-port(if01/UART)> <neorv32_exe.bin> [logfile]")
    port, exe = sys.argv[1], sys.argv[2]
    logpath = sys.argv[3] if len(sys.argv) > 3 else "run.log"

    try:
        with open(exe, "rb") as f:
            image = f.read()
    except OSError as e:
        sys.exit(f"cannot read {exe}: {e}\n"
                 f"build it: make -C firmware/neorv32_ascon_benchmark FREESTANDING=1 exe")

    link = Link(port)
    if not link.ser:
        sys.exit(f"cannot open {port}\n"
                 f"Use the UART interface (if01), e.g. the /dev/serial/by-id/...-if01-port0 path,\n"
                 f"and make sure openFPGALoader has finished (it holds the JTAG interface).")

    log: list[str] = []

    def emit(chunk: bytes) -> None:
        if chunk:
            text = chunk.decode("latin1", "replace")
            sys.stdout.write(text); sys.stdout.flush()
            log.append(text)

    print(f"Reading UART on {port} @ {BAUD}.")
    print(">>> If the board isn't already in the bootloader, reset it now")
    print("    (re-flash in another terminal). Waiting up to 90s ...\n")

    # Phase 1 - wait for the bootloader prompt (nudge it with the abort char).
    seen = b""
    at_prompt = False
    last_nudge = 0.0
    deadline = time.time() + 90
    while time.time() < deadline:
        now = time.time()
        if now - last_nudge > 0.1:
            link.write(b" ")
            last_nudge = now
        chunk = link.read(256)
        emit(chunk)
        seen += chunk
        if len(seen) > 4096:
            seen = seen[-4096:]
        if b"CMD:>" in seen or b"Bootloader" in seen:
            at_prompt = True
            break

    if not at_prompt:
        _save(logpath, log)
        print("\n\nNo bootloader prompt seen.")
        print("- Use the UART interface (if01), not JTAG (if00).")
        print("- Flash the bitstream, THEN run this within a few seconds:")
        print("    openFPGALoader -b tangnano20k build/soc/neorv32_ascon_soc.fs && \\")
        print(f"      python {sys.argv[0]} {port} {exe} {logpath}")
        sys.exit(1)

    # Phase 2 - upload.
    time.sleep(0.3)
    link.reset_input()
    print("\n\n[bootloader ready -> uploading %d bytes]" % len(image))
    link.write(b"u")
    time.sleep(0.4)
    emit(link.read(256))
    for i in range(0, len(image), 256):
        link.write(image[i:i + 256])

    got = b""
    t = time.time() + 10
    while time.time() < t:
        c = link.read(256)
        emit(c)
        got += c
        if b"OK" in got:
            break
    if b"OK" not in got:
        print("\n[warning] no 'OK' ack - trying to execute anyway")

    # Phase 3 - execute + capture.
    print("\n[executing - capturing benchmark output for 45s; it prints now]")
    link.write(b"e")
    t = time.time() + 45
    while time.time() < t:
        emit(link.read(512))

    _save(logpath, log)
    print(f"\n\n-> saved {logpath}   (parse: python host/ascon_bench.py report {logpath})")


def _save(path: str, log: list[str]) -> None:
    with open(path, "w") as f:
        f.write("".join(log))


if __name__ == "__main__":
    main()
