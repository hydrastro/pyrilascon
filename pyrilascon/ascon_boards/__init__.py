"""Unified board flow: one build driver + per-board descriptors.

Adding a board is a data change (a ``boards/<name>.toml`` + a ``.cst`` pin map),
not a new Makefile. The same driver constructs the yosys -> nextpnr ->
gowin_pack -> openFPGALoader commands for any board/target pair, and can print
them (`--dry-run`) or run them.
"""
from ascon_boards.build import Board, BuiltSources, list_boards, load_board

__all__ = ["Board", "BuiltSources", "list_boards", "load_board"]
