# FPGA maximum-throughput direction

These decisions are treated as the FPGA design direction for pyrilascon.  Small boards such as the Tang Nano 9K are used as proof vehicles; they do not change the target architecture.

## Fixed FPGA direction

- Data plane: AXI4-Stream-style payload interface.
- Control plane: frozen CSR/MMIO register map for configuration, status, lengths, keys, nonces, tags, capabilities, cycle counts, and errors.
- Data width target: 128-bit payload path for final high-throughput AEAD128 designs.
- Padding: streaming final bytemask using `tkeep`.
- Top-level organization candidates:
  - one pipelined permutation with multiple interleaved contexts;
  - M pipelined permutations with N contexts per pipeline;
  - N identical AEAD cores for simple packet-level scaling.
- Permutation candidates:
  - fully pipelined p8/p12;
  - 8 rounds per cycle;
  - 4 rounds per cycle as a safer timing fallback.
- Context organization: multi-context interleaving for shared pipelined permutations.
- Security/fault baseline: buffered decryption output, constant-time tag compare, randomized counter hardening, and FPGA fault-detection profile where resources allow.

## Tang Nano 9K role

Tang Nano 9K targets are validation milestones, not the final architecture constraint.  The current `ascon_aead128_axis_slow` target validates the CSR + AXI Stream contract with the existing slow AEAD128 backend.  A later backend can replace the slow core with a 128-bit, pipelined, multi-context implementation without changing the software-visible ABI.
