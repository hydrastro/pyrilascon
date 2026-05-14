# Top-Level Core / Pipeline Organization

This axis describes how many independent AEAD operations, cores, or permutation
pipelines are visible at the chip/top level. It is separate from datapath width,
permutation style, and state/context storage.

## Profiles

| Profile | Intent | Typical target |
|---|---|---|
| `single_core` | One AEAD operation at a time | smallest ASIC, simple FPGA debug core |
| `dual_enc_dec_cores` | Independent encrypt and decrypt datapaths/cores | ASIC baseline chosen for this project |
| `n_identical_aead_cores` | N complete AEAD cores for independent packets/messages | simple high-throughput FPGA scaling |
| `one_pipelined_permutation_n_contexts` | One shared pipelined permutation engine with many interleaved contexts | efficient high-throughput FPGA |
| `m_pipelines_n_contexts` | M shared permutation pipelines fed by N contexts | extreme FPGA throughput, hardest scheduler |

## Selected project baselines

### ASIC

The selected ASIC baseline is:

```text
profile: dual_enc_dec_cores
context: single_320_register
```

This models independent encryption and decryption progress while keeping each
active datapath state organization minimal.

### FPGA

The main FPGA candidates are:

```text
profile: n_identical_aead_cores
profile: one_pipelined_permutation_n_contexts
profile: m_pipelines_n_contexts
```

`n_identical_aead_cores` is the simplest scaling strategy. The pipelined-context
profiles are more area-efficient when the scheduler can keep independent message
contexts in flight and the I/O subsystem can feed the design.

## Generator examples

```bash
PYTHONPATH=. python tools/generate_design.py --preset asic_dual_enc_dec_cores
```

```bash
PYTHONPATH=. python tools/generate_design.py \
  --preset fpga_n_parallel_engines \
  --engine-count 4
```

```bash
PYTHONPATH=. python tools/generate_design.py \
  --preset fpga_one_pipelined_permutation_n_contexts \
  --contexts-per-engine 12
```

```bash
PYTHONPATH=. python tools/generate_design.py \
  --preset fpga_m_pipelines_n_contexts \
  --engine-count 4 \
  --contexts-per-engine 12
```

For `m_pipelines_n_contexts`, the command-line `--engine-count` value is used as
the pipeline count by the preset for now. The more explicit override is:

```bash
PYTHONPATH=. python tools/generate_design.py \
  --preset fpga_n_parallel_engines \
  --top-level-profile m_pipelines_n_contexts \
  --pipeline-count 4 \
  --contexts-per-engine 12
```
