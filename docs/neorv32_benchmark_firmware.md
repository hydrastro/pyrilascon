# NEORV32 benchmark firmware

The benchmark firmware is the first complete software-side acceptance harness for
the ASCON accelerator ABI. It is intentionally independent from a specific FPGA
microarchitecture: the same firmware can be used with the slow MMIO backend, a
4-rounds-per-cycle backend, an 8-rounds-per-cycle backend, or a future pipelined
AXI Stream backend, as long as the hardware obeys the frozen register ABI.

## Project location

```text
firmware/neorv32_ascon_benchmark/
  Makefile
  README.md
  main.c
```

The firmware links against:

```text
firmware/ascon_accel/        portable accelerator driver
firmware/ascon_ref/          portable software Ascon-AEAD128 reference
```

## Benchmark method

The firmware performs one fixed AEAD128 benchmark shape:

```text
AD length:   16 bytes
Text length: 32 bytes
Key length:  16 bytes
Nonce size:  16 bytes
```

The benchmark sequence is:

1. run software Ascon-AEAD128 encryption and decryption;
2. read the RISC-V `cycle` counter around the software run;
3. run hardware encryption through the accelerator driver;
4. run hardware decryption through the accelerator driver;
5. compare software ciphertext/tag with hardware ciphertext/tag;
6. verify decrypted plaintext equals the original plaintext;
7. print cycle counts and speedup over UART.

## Acceptance rule

The main acceptance rule for a hardware configuration is:

```text
hardware_cycles < software_cycles
```

for every mode that the accelerator advertises in `CAPABILITIES`.

If a hardware design is functionally correct but slower than software, the
firmware prints a warning instead of silently accepting the result. This is
important because the project goal is acceleration, not only correctness.

## Data-plane portability

The benchmark uses the high-level driver API. The driver decides how payloads are
moved according to the configured data plane:

```text
MMIO word data plane:      CPU writes DATA_IN / reads DATA_OUT registers
AXI Stream data plane:     platform transport or DMA callback sends/receives data
```

The benchmark code does not change when the backend changes. A future Xilinx or
larger Gowin board should reuse the same benchmark firmware and only provide a
platform-specific AXI Stream/DMA transport.

## Build

From `firmware/neorv32_ascon_benchmark`:

```sh
make neorv32-stream-build-firmware
```

The resulting NEORV32 executable should be loaded into the SoC image using the
normal NEORV32 software flow.

## Expected UART output

The exact cycle counts depend on the NEORV32 clock, compiler options, and the
selected accelerator backend. The output has this form:

```text
pyrilascon NEORV32 ASCON benchmark
ABI          : 0x00010000
CAPS         : 0x...
SW CT        : ...
SW TAG       : ...
HW CT        : ...
HW TAG       : ...
HW PT        : ...
ENC status       : 0
ENC hw cycles    : hi:lo
ENC hw mcy/byte  : ...
DEC status       : 0
DEC hw cycles    : hi:lo
DEC hw mcy/byte  : ...
SW cycles    : hi:lo
ENC speedup x1000: ...
DEC speedup x1000: ...
PASS
```
