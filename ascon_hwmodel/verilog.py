"""Verilog aggregation and file emission helpers.

Verilog source generators live next to the Python model objects they refer to.
This module only aggregates those colocated emitters and writes .v/.vh files.
"""

from pathlib import Path
from typing import Mapping

from ascon_hwmodel.byteops import emit_verilog_aux_include, emit_verilog_pad64_partial_function, emit_verilog_pad128_partial_function
from ascon_hwmodel.domain import emit_verilog_domain_separator_function
from ascon_hwmodel.iv import emit_verilog_iv_function, emit_verilog_iv_include, emit_verilog_iv_localparams
from ascon_hwmodel.keyops import (
    emit_verilog_aead128_add_key_after_init_function,
    emit_verilog_aead128_add_key_before_final_function,
    emit_verilog_aead128_extract_tag_function,
    emit_verilog_aead128_initial_state_function,
    emit_verilog_keyops_include,
)
from ascon_hwmodel.p6 import emit_verilog_p6_function, emit_verilog_p6_include, emit_verilog_p6_module
from ascon_hwmodel.p8 import emit_verilog_p8_function, emit_verilog_p8_include, emit_verilog_p8_module
from ascon_hwmodel.p12 import emit_verilog_p12_function, emit_verilog_p12_include, emit_verilog_p12_module
from ascon_hwmodel.pc import (
    emit_verilog_pc_function,
    emit_verilog_pc_include,
    emit_verilog_round_constant_function,
    emit_verilog_round_constants,
)
from ascon_hwmodel.permutation import emit_verilog_permutation_comb_module, emit_verilog_permutation_functions, emit_verilog_permutation_include
from ascon_hwmodel.pl import emit_verilog_pl_function, emit_verilog_pl_include, emit_verilog_rotr64_function
from ascon_hwmodel.ps import (
    emit_verilog_ps_bitsliced_function,
    emit_verilog_ps_function,
    emit_verilog_ps_include,
    emit_verilog_ps_lut_function,
    emit_verilog_sbox5_lut_function,
)
from ascon_hwmodel.round import emit_verilog_round_function, emit_verilog_round_include
from ascon_hwmodel.rate import emit_verilog_rate_include
from ascon_hwmodel.aead import emit_verilog_aead_include
from ascon_hwmodel.aead_config import emit_verilog_aead_config_include
from ascon_hwmodel.hash_xof import emit_verilog_hash_xof_include
from ascon_hwmodel.state import emit_verilog_state_include, emit_verilog_state_pack_function, emit_verilog_state_word_function


def emit_verilog_domain_key_functions() -> str:
    return emit_verilog_domain_separator_function()


def emit_verilog_domain_key_include() -> str:
    return "\n\n".join(
        (
            "// Generated Ascon AEAD domain separator helper.",
            emit_verilog_domain_separator_function(),
        )
    )


def emit_verilog_model_include() -> str:
    return "\n\n".join(
        (
            emit_verilog_iv_include(),
            emit_verilog_state_include(),
            emit_verilog_aux_include(),
            emit_verilog_rate_include(),
            emit_verilog_permutation_include(),
            emit_verilog_domain_key_include(),
            emit_verilog_aead_include(),
            emit_verilog_hash_xof_include(),
        )
    )


def render_verilog_files() -> Mapping[str, str]:
    """Return generated Verilog filenames and their contents."""
    return {
        "ascon_iv.vh": emit_verilog_iv_include(),
        "ascon_state.vh": emit_verilog_state_include(),
        "ascon_aux.vh": emit_verilog_aux_include(),
        "ascon_rate.vh": emit_verilog_rate_include(),
        "ascon_pc.vh": emit_verilog_pc_include(),
        "ascon_ps.vh": emit_verilog_ps_include(),
        "ascon_pl.vh": emit_verilog_pl_include(),
        "ascon_round.vh": emit_verilog_round_include(),
        "ascon_p6.vh": emit_verilog_p6_include(),
        "ascon_p8.vh": emit_verilog_p8_include(),
        "ascon_p12.vh": emit_verilog_p12_include(),
        "ascon_permutation.vh": emit_verilog_permutation_include(),
        "ascon_aead_domain_key.vh": emit_verilog_domain_key_include(),
        "ascon_aead.vh": emit_verilog_aead_include(),
        "ascon_hash_xof.vh": emit_verilog_hash_xof_include(),
        "ascon_model.vh": "\n".join(
            (
                '`include "ascon_iv.vh"',
                '`include "ascon_state.vh"',
                '`include "ascon_aux.vh"',
                '`include "ascon_rate.vh"',
                '`include "ascon_pc.vh"',
                '`include "ascon_ps.vh"',
                '`include "ascon_pl.vh"',
                '`include "ascon_round.vh"',
                '`include "ascon_p6.vh"',
                '`include "ascon_p8.vh"',
                '`include "ascon_p12.vh"',
                '`include "ascon_aead_domain_key.vh"',
                '`include "ascon_aead.vh"',
                '`include "ascon_hash_xof.vh"',
                "",
            )
        ),
        "ascon_permutation_comb.v": emit_verilog_permutation_comb_module(),
        "ascon_p6_comb.v": emit_verilog_p6_module(),
        "ascon_p8_comb.v": emit_verilog_p8_module(),
        "ascon_p12_comb.v": emit_verilog_p12_module(),
    }


def write_verilog_files(output_dir: str | Path) -> tuple[Path, ...]:
    out_path: Path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, content in render_verilog_files().items():
        path: Path = out_path / filename
        path.write_text(content + "\n", encoding="utf-8")
        written.append(path)
    return tuple(written)
