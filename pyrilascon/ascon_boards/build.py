"""Board descriptors + build-command construction for the Gowin/Apicula flow."""
from __future__ import annotations

import dataclasses
import pathlib
import shlex
import subprocess
import tomllib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
BOARDS_DIR = REPO_ROOT / "boards"
GENERATED_DIR = REPO_ROOT / "rtl" / "generated"


@dataclasses.dataclass(frozen=True)
class Board:
    name: str
    device: str
    family: str
    freq_mhz: int
    loader: str
    constraints: pathlib.Path
    nextpnr: str
    reset_style: str = "button"   # "button" (external rst_n pin) or "internal" (power-on)


@dataclasses.dataclass(frozen=True)
class BuiltSources:
    top_module: str
    sources: list[pathlib.Path]
    include_dirs: list[pathlib.Path]


def list_boards() -> list[str]:
    return sorted(p.stem for p in BOARDS_DIR.glob("*.toml"))


def load_board(name: str) -> Board:
    toml_path = BOARDS_DIR / f"{name}.toml"
    if not toml_path.exists():
        raise FileNotFoundError(
            f"no board descriptor {toml_path.name!r} (have: {', '.join(list_boards()) or 'none'})"
        )
    data = tomllib.loads(toml_path.read_text())
    b = data["board"]
    tools = data.get("tools", {})
    return Board(
        name=b["name"],
        device=b["device"],
        family=b["family"],
        freq_mhz=int(b["freq_mhz"]),
        loader=b["loader"],
        constraints=(BOARDS_DIR / b["constraints"]).resolve(),
        nextpnr=tools.get("nextpnr", "nextpnr-gowin"),
        reset_style=b.get("reset_style", "button"),
    )


def _artifact(build_dir: pathlib.Path, board: Board, built: BuiltSources, suffix: str) -> pathlib.Path:
    return build_dir / f"{built.top_module}{suffix}"


def synth_command(board: Board, built: BuiltSources, build_dir: pathlib.Path):
    json_out = _artifact(build_dir, board, built, ".json")
    incs = " ".join(f"-I {d}" for d in built.include_dirs)
    srcs = " ".join(str(s) for s in built.sources)
    script = f"read_verilog {incs} {srcs}; synth_gowin -top {built.top_module} -json {json_out}"
    return ["yosys", "-q", "-p", script], json_out


def pnr_command(board: Board, built: BuiltSources, build_dir: pathlib.Path, json_in: pathlib.Path):
    pnr_out = _artifact(build_dir, board, built, ".pnr.json")
    if board.nextpnr == "nextpnr-himbaechel":
        cmd = [
            board.nextpnr, "--json", str(json_in), "--write", str(pnr_out),
            "--device", board.device,
            "--vopt", f"family={board.family}",
            "--vopt", f"cst={board.constraints}",
        ]
    else:  # nextpnr-gowin (classic)
        cmd = [
            board.nextpnr, "--json", str(json_in), "--write", str(pnr_out),
            "--freq", str(board.freq_mhz),
            "--device", board.device,
            "--family", board.family,
            "--cst", str(board.constraints),
        ]
    return cmd, pnr_out


def pack_command(board: Board, built: BuiltSources, build_dir: pathlib.Path, pnr_json: pathlib.Path):
    fs = _artifact(build_dir, board, built, ".fs")
    return ["gowin_pack", "-d", board.family, "-o", str(fs), str(pnr_json)], fs


def flash_command(board: Board, fs: pathlib.Path, *, to_flash: bool = False):
    cmd = ["openFPGALoader", "-b", board.loader]
    if to_flash:
        cmd.append("-f")
    cmd.append(str(fs))
    return cmd


def run_step(label: str, argv: list[str], *, dry_run: bool) -> int:
    printable = " ".join(shlex.quote(a) for a in argv)
    if dry_run:
        print(f"[dry-run] {label}\n    {printable}")
        return 0
    print(f"[{label}] {printable}")
    return subprocess.run(argv).returncode
