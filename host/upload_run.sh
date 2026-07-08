#!/usr/bin/env bash
# Upload a NEORV32 executable to the on-chip bootloader AND capture the program's
# output in one shot. NEORV32's own uart_upload.sh returns as soon as the upload
# is acknowledged, so the benchmark's CASE lines (printed right after) would be
# missed - this keeps the port open and logs them.
#
#   1. RESET the board (so the bootloader is in its auto-boot wait window)
#   2. ./host/upload_run.sh /dev/ttyUSB1 firmware/neorv32_ascon_benchmark/neorv32_exe.bin run.log
#   3. python host/ascon_bench.py report run.log
#
# Adapted from NEORV32's sw/image_gen/uart_upload.sh (same raw protocol: send a
# SPACE to abort auto-boot, 'u' to start upload, then the raw executable bytes).
set -euo pipefail

PORT="${1:?usage: upload_run.sh <serial-port> <neorv32_exe.bin> [logfile] [seconds]}"
EXE="${2:?path to neorv32_exe.bin (build it with: make -C firmware/neorv32_ascon_benchmark FREESTANDING=1 exe)}"
LOG="${3:-run.log}"
SECS="${4:-25}"
BAUD=19200

[ -e "$PORT" ] || { echo "no such serial port: $PORT (try: ls /dev/ttyUSB*)" >&2; exit 1; }
[ -f "$EXE" ]  || { echo "executable not found: $EXE" >&2; exit 1; }

# Raw 8N1, no flow control, do not toggle modem lines on open/close (-hup, clocal).
stty -F "$PORT" "$BAUD" -hup raw -echo cs8 -cstopb -ixon clocal cread

exec 3<>"$PORT"
printf ' u' >&3                       # SPACE aborts auto-boot; 'u' starts UART upload
cat "$EXE" >&3                        # send the raw executable
echo "uploaded $(stat -c%s "$EXE") bytes to $PORT; capturing ${SECS}s -> $LOG"
: > "$LOG"
timeout "$SECS" cat <&3 | tee -a "$LOG" || true
exec 3>&-
if [ -s "$LOG" ]; then
  echo "done -> $LOG   (parse with: python host/ascon_bench.py report $LOG)"
else
  echo "" >&2
  echo "WARNING: the board sent nothing back - the bootloader was not listening." >&2
  echo "It only accepts an upload during its ~8s window right after reset. Reset the" >&2
  echo "SoC and re-run immediately. Options to reset:" >&2
  echo "  * press the S1 button (if the SoC was built with the reset-button .cst), or" >&2
  echo "  * reconfigure the FPGA (also resets the SoC) and chain the upload:" >&2
  echo "      openFPGALoader -b tangnano20k build/soc/neorv32_ascon_soc.fs && \\" >&2
  echo "        $0 $PORT $EXE $LOG" >&2
fi
