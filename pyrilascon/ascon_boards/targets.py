"""Buildable targets. A target knows how to emit its RTL into a build dir.

`perm_smoke` emits the GENERATED permutation core plus a self-checking top, so
what gets synthesized/flashed is generated, model-verified RTL - the concrete
link between the generator (3a) and the board flow (3b).
"""
from __future__ import annotations

import pathlib

from ascon_boards.build import GENERATED_DIR, BuiltSources

# Rounds-per-cycle for the demo core. Any round-based profile the generator
# emits (1/2/4/8) works; 4 is a reasonable default for the Tang Nano 9K.
_PERM_SMOKE_RPC = 1


def _emit_perm_smoke(build_dir: pathlib.Path, board=None) -> BuiltSources:
    from ascon_designspace.generator.permutation import emit_iterative_permutation
    from ascon_designspace.generator.smoke import emit_perm_smoke_top
    from ascon_designspace.generator.verify import ensure_model_emitted

    ensure_model_emitted(GENERATED_DIR)  # rtl/generated/ascon_model.vh + includes
    board_name = getattr(board, "name", "tangnano9k")
    internal_reset = getattr(board, "reset_style", "button") == "internal"
    top_name = f"{board_name}_perm_smoke"
    core = f"ascon_perm_iter_r{_PERM_SMOKE_RPC}"
    core_v = build_dir / f"{core}.v"
    top_v = build_dir / f"{top_name}.v"
    core_v.write_text(emit_iterative_permutation(_PERM_SMOKE_RPC))
    top_v.write_text(emit_perm_smoke_top(_PERM_SMOKE_RPC, top_name=top_name, internal_reset=internal_reset))
    return BuiltSources(
        top_module=top_name,
        sources=[core_v, top_v],
        include_dirs=[GENERATED_DIR],
    )


_TARGETS = {
    "perm_smoke": _emit_perm_smoke,
}


def list_targets() -> list[str]:
    return sorted(_TARGETS)


def emit_target(name: str, build_dir: pathlib.Path | str, board=None) -> BuiltSources:
    if name not in _TARGETS:
        raise KeyError(f"unknown target {name!r} (have: {', '.join(list_targets())})")
    build_dir = pathlib.Path(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    return _TARGETS[name](build_dir, board)
