"""The tier-1 RTL generator, grown from the golden model's Verilog emission.

Emits three verified ASCON permutation families today, each checked bit-exact
against the model's NIST-KAT-verified p6/p8/p12 by simulation:

* round-based    - iterative, R rounds/cycle (R in 1/2/4/8)         [permutation.py]
* fully-pipelined- one round/stage, throughput 1/cycle (p6/p8/p12)  [permutation.py]
* column-serial  - K S-box columns/cycle, area-reduced (K in 1..8)  [serial.py]

* bit-serial     - serial S-box + serial linear layer, most-serial datapath  [serial.py]

All four families are verified bit-exact against the model in simulation.
"""
from ascon_designspace.generator.permutation import (
    ROUND_BASED_RPC,
    emit_iterative_permutation,
    emit_permutation_testbench,
    emit_pipeline_testbench,
    emit_pipelined_permutation,
)
from ascon_designspace.generator.serial import (
    COLUMN_SERIAL_COLUMNS,
    emit_bit_serial_permutation,
    emit_column_serial_permutation,
)
from ascon_designspace.generator.aead import (
    emit_aead128_core,
    emit_aead128_testbench,
    emit_aead_core,
    emit_aead_core_for,
)
from ascon_designspace.generator.hash256 import (
    emit_cxof128_core,
    emit_hash256_core,
    emit_hash256_testbench,
    emit_hasha_core,
    emit_xof128_core,
    emit_xofa_core,
)
from ascon_designspace.generator.axis import (
    emit_aead128_axis,
    emit_aead128_axis_mmio,
    emit_aead128_axis_testbench,
)
from ascon_designspace.generator.control import emit_microcoded_permutation
from ascon_designspace.generator.smoke import emit_perm_smoke_top, golden_p12_hex
from ascon_designspace.generator.structural import (
    context_pipeline_name,
    emit_context_pipeline,
    emit_context_pipeline_testbench,
    emit_multi_pipeline,
    emit_multi_pipeline_testbench,
    multi_pipeline_name,
)

# The permutation profiles (by their design-space value) the generator emits AND
# verifies today. Single source of truth for the catalog's GENERATED tier.
GENERATED_PERMUTATION_PROFILES: frozenset[str] = frozenset(
    set(ROUND_BASED_RPC) | {"fully_pipelined", "column_serial", "bit_serial"}
)

# Structural topologies the generator emits and verifies (arrangements of cores).
# single_core is what a bare permutation core already is; the multi-context
# pipeline is the new structure.
GENERATED_TOPOLOGIES: frozenset[str] = frozenset(
    {"single_core", "one_pipelined_permutation_n_contexts", "m_pipelines_n_contexts"}
)

# End-to-end algorithm cores the generator emits and verifies against NIST KATs,
# each composing a generated permutation core with a hardwired-FSM sponge.
GENERATED_ALGORITHM_CORES: frozenset[str] = frozenset(
    {"aead128", "aead128a", "ascon128", "aead80pq",
     "hash256", "xof128", "cxof128", "hasha", "xofa"}
)

# Control styles the generator emits for the permutation core.
GENERATED_CONTROL_STYLES: frozenset[str] = frozenset({"hardwired_fsm", "microcoded_sequencer"})

__all__ = [
    "ROUND_BASED_RPC",
    "COLUMN_SERIAL_COLUMNS",
    "GENERATED_PERMUTATION_PROFILES",
    "emit_iterative_permutation",
    "emit_pipelined_permutation",
    "emit_column_serial_permutation",
    "emit_bit_serial_permutation",
    "emit_permutation_testbench",
    "emit_pipeline_testbench",
    "emit_perm_smoke_top",
    "golden_p12_hex",
    "emit_context_pipeline",
    "emit_context_pipeline_testbench",
    "context_pipeline_name",
    "emit_multi_pipeline",
    "emit_multi_pipeline_testbench",
    "multi_pipeline_name",
    "GENERATED_TOPOLOGIES",
    "emit_aead128_core",
    "emit_aead_core",
    "emit_aead_core_for",
    "emit_hash256_core",
    "emit_xof128_core",
    "emit_cxof128_core",
    "emit_hasha_core",
    "emit_xofa_core",
    "GENERATED_ALGORITHM_CORES",
    "emit_microcoded_permutation",
    "emit_aead128_axis",
    "emit_aead128_axis_mmio",
    "GENERATED_CONTROL_STYLES",
]
