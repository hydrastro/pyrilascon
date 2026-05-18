import serial, time, sys

port = "/dev/serial/by-id/usb-SIPEED_JTAG_Debugger_FactoryAIOT_Pro-if01-port0"
for baud in [9600, 19200, 38400, 57600, 115200, 230400, 460800, 500000, 921600, 1000000, 1500000, 2000000, 3000000]:
    try:
        s = serial.Serial(port, baud, timeout=0.5)
        time.sleep(0.3)
        data = s.read(64)
        s.close()
        printable = sum(1 for b in data if 32 <= b < 127 or b in (10,13))
        ratio = printable / max(len(data), 1)
        marker = "  <-- CLEAN!" if ratio > 0.8 else ""
        print(f"{baud:>8}: {len(data):3} bytes, {ratio*100:5.1f}% printable  {data!r}{marker}")
    except Exception as e:
        print(f"{baud:>8}: error: {e}")
