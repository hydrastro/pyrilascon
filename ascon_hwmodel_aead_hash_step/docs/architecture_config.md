# Architecture configuration layer

The repository now separates the ASCON specification model from implementation architecture choices.

The specification model answers: **what does ASCON compute?**

The architecture layer answers: **how is a selected ASCON implementation organized?**

Current architecture families:

| Family | Intent |
|---|---|
| `shared_datapath` | Low/medium area, one operation at a time. |
| `separate_enc_dec_datapaths` | Higher area, separate encryption and decryption datapaths, up to two operations at a time per engine. |
| `shared_permutation_mode_fsm` | Medium area, one shared permutation bottleneck controlled by a mode FSM. |
| `parallel_engines` | High area, N independent engines for nearly linear scaling on independent jobs. |

Chosen baselines:

| Target | Baseline |
|---|---|
| ASIC | `asic_two_datapaths`: one encryption datapath and one decryption datapath. |
| FPGA | `fpga_N_parallel_engines`: N independent engines, parameterized by `engine_count`. |

Generate design-product skeletons with:

```bash
PYTHONPATH=. python tools/generate_design.py --preset asic_two_datapaths
PYTHONPATH=. python tools/generate_design.py --preset fpga_n_parallel_engines --engine-count 4
```

Or from explicit JSON:

```bash
PYTHONPATH=. python tools/generate_design.py --config configs/asic/two_separate_datapaths.json
PYTHONPATH=. python tools/generate_design.py --config configs/fpga/n_parallel_engines_4.json
```

The generated build directory contains a resolved config, module manifest, and a top-level structural RTL placeholder. The next RTL step is to replace the placeholder with actual architecture-specific generators.
