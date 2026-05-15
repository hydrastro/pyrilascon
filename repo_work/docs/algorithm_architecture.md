# Algorithm configuration axis

The architecture generator now treats the algorithm family as an explicit configuration axis.

The selected sweep currently includes these user-requested single-algorithm targets:

- `aead128`
- `aead128a`
- `aead80pq`
- `hash`
- `hasha`
- `xof`
- `xofa`
- `cxof`

These names are valid architecture-generation targets. They are not all equally verified yet.

Currently KAT-backed in the golden Python model:

- `aead128` via the NIST Ascon-AEAD128 flow
- `hash256`
- `xof128`
- `cxof128`

Architecture placeholders requiring dedicated IV/endian/KAT work before production RTL signoff:

- `aead128a`
- `aead80pq`
- `hash`
- `hasha`
- `xof`
- `xofa`
- `cxof`

A hardcoded FSM may use any one fixed algorithm feature. Multi-algorithm designs should use a microcoded, command-FIFO, AXI-stream, or hybrid control profile.

Useful commands:

```bash
make list-valid-configs
make list-valid-configs-csv
make list-valid-configs-json
PYTHONPATH=. python tools/generate_design.py --preset asic_dual_enc_dec_cores --algorithm-feature hasha
PYTHONPATH=. python tools/generate_design.py --preset fpga_n_parallel_engines --engine-count 4 --algorithm-feature xofa
```
