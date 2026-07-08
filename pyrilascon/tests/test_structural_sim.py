"""Structural topology wrappers must arrange verified cores correctly.

Covers ONE_PIPELINED_PERMUTATION_N_CONTEXTS: N contexts interleaved through one
pipelined permutation, each labelled result checked as p[N] of its input.
Skips when Icarus Verilog is unavailable.
"""
import pytest

from ascon_designspace.generator.verify import (
    iverilog_available,
    verify_context_pipeline,
    verify_multi_pipeline,
)

pytestmark = pytest.mark.skipif(not iverilog_available(), reason="iverilog/vvp not installed")


@pytest.mark.parametrize("num_rounds,num_contexts", [(6, 4), (8, 4), (12, 4), (12, 8), (12, 3)])
def test_context_pipeline_matches_model(num_rounds: int, num_contexts: int) -> None:
    passed, trials, line = verify_context_pipeline(num_rounds, num_contexts)
    assert passed, f"p{num_rounds} c{num_contexts}: {line}"
    assert trials >= 100


@pytest.mark.parametrize("num_rounds,num_pipelines,num_contexts", [(12, 2, 4), (12, 3, 4), (8, 2, 3)])
def test_multi_pipeline_matches_model(num_rounds: int, num_pipelines: int, num_contexts: int) -> None:
    passed, trials, line = verify_multi_pipeline(num_rounds, num_pipelines, num_contexts)
    assert passed, f"p{num_rounds} m{num_pipelines} c{num_contexts}: {line}"
    assert trials >= 100
