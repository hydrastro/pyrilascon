"""Verify generated permutation cores bit-exact against the golden model using
Icarus Verilog.

The golden model's combinational ``p6``/``p8``/``p12`` are NIST-KAT-verified
(``tests/test_known_answer_vectors.py``); if a generated core matches them over
random + edge-case vectors, it is correct by transitivity. Requires
``iverilog``/``vvp`` on PATH - callers should skip when absent.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile

from ascon_designspace.generator.permutation import (
    emit_iterative_permutation,
    emit_permutation_testbench,
    emit_pipeline_testbench,
    emit_pipelined_permutation,
)
from ascon_designspace.generator.serial import (
    emit_bit_serial_permutation,
    emit_column_serial_permutation,
)
from ascon_designspace.generator.structural import (
    context_pipeline_name,
    emit_context_pipeline,
    emit_context_pipeline_testbench,
    emit_multi_pipeline,
    emit_multi_pipeline_testbench,
    multi_pipeline_name,
)

GENERATED_DIR = pathlib.Path(__file__).resolve().parents[2] / "rtl" / "generated"


def iverilog_available() -> bool:
    return shutil.which("iverilog") is not None and shutil.which("vvp") is not None


def ensure_model_emitted(generated_dir: pathlib.Path | str = GENERATED_DIR) -> pathlib.Path:
    """Emit the model primitives (ascon_model.vh + includes) if not present."""
    generated_dir = pathlib.Path(generated_dir)
    if not (generated_dir / "ascon_model.vh").exists():
        from ascon_hwmodel.verilog import write_verilog_files

        generated_dir.mkdir(parents=True, exist_ok=True)
        write_verilog_files(generated_dir)
    return generated_dir


def _run_sim(
    dut_name: str,
    dut_src: str,
    tb_src: str,
    *,
    generated_dir: pathlib.Path | str = GENERATED_DIR,
) -> tuple[bool, int, str]:
    gen = ensure_model_emitted(generated_dir).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        (d / f"{dut_name}.v").write_text(dut_src)
        (d / "tb.v").write_text(tb_src)
        sim = d / "sim.vvp"
        comp = subprocess.run(
            ["iverilog", "-g2012", "-I", str(gen), "-o", str(sim), str(d / "tb.v"), str(d / f"{dut_name}.v")],
            capture_output=True,
            text=True,
        )
        if comp.returncode != 0:
            return (False, 0, "compile error: " + comp.stderr.strip())
        run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True)
        line = next((l for l in run.stdout.splitlines() if "PASS" in l or "FAIL" in l), "")
        trials = next((int(t) for t in line.split() if t.isdigit()), 0)
        passed = "PASS" in line and "FAIL" not in line
        return (passed, trials, line.strip() or run.stdout.strip())


def verify_permutation(rounds_per_cycle: int, **kw) -> tuple[bool, int, str]:
    """Round-based iterative core, R rounds/cycle."""
    name = f"ascon_perm_iter_r{rounds_per_cycle}"
    return _run_sim(name, emit_iterative_permutation(rounds_per_cycle), emit_permutation_testbench(name), **kw)


def verify_pipeline(num_rounds: int, **kw) -> tuple[bool, int, str]:
    """Fully-pipelined p[num_rounds] (checks correctness and throughput=1/cycle)."""
    name = f"ascon_perm_pipe_p{num_rounds}"
    return _run_sim(name, emit_pipelined_permutation(num_rounds), emit_pipeline_testbench(name, num_rounds), **kw)


def verify_column_serial(columns_per_cycle: int, **kw) -> tuple[bool, int, str]:
    """Column-serial core (K columns/cycle); same interface as the iterative core."""
    name = f"ascon_perm_colser_k{columns_per_cycle}"
    return _run_sim(name, emit_column_serial_permutation(columns_per_cycle), emit_permutation_testbench(name), **kw)


def verify_bit_serial(**kw) -> tuple[bool, int, str]:
    """Bit-serial core (serial S-box + serial linear layer); iterative interface."""
    name = "ascon_perm_bitser"
    return _run_sim(name, emit_bit_serial_permutation(), emit_permutation_testbench(name), **kw)


def _run_sim_files(
    sources: list[tuple[str, str]],
    tb_src: str,
    *,
    generated_dir: pathlib.Path | str = GENERATED_DIR,
) -> tuple[bool, int, str]:
    """Like _run_sim but compiles several named DUT sources together (e.g. a
    structural wrapper plus the core it instantiates)."""
    gen = ensure_model_emitted(generated_dir).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        files = []
        for name, src in sources:
            f = d / f"{name}.v"
            f.write_text(src)
            files.append(str(f))
        (d / "tb.v").write_text(tb_src)
        sim = d / "sim.vvp"
        comp = subprocess.run(
            ["iverilog", "-g2012", "-I", str(gen), "-o", str(sim), str(d / "tb.v"), *files],
            capture_output=True,
            text=True,
        )
        if comp.returncode != 0:
            return (False, 0, "compile error: " + comp.stderr.strip())
        run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True)
        line = next((l for l in run.stdout.splitlines() if "PASS" in l or "FAIL" in l), "")
        trials = next((int(t) for t in line.split() if t.isdigit()), 0)
        return ("PASS" in line and "FAIL" not in line, trials, line.strip() or run.stdout.strip())


def verify_context_pipeline(num_rounds: int, num_contexts: int, **kw) -> tuple[bool, int, str]:
    """ONE_PIPELINED_PERMUTATION_N_CONTEXTS wrapper composed over the pipelined core."""
    core = f"ascon_perm_pipe_p{num_rounds}"
    wrap = context_pipeline_name(num_rounds, num_contexts)
    return _run_sim_files(
        [(core, emit_pipelined_permutation(num_rounds)),
         (wrap, emit_context_pipeline(num_rounds, num_contexts))],
        emit_context_pipeline_testbench(num_rounds, num_contexts),
        **kw,
    )


def verify_multi_pipeline(num_rounds: int, num_pipelines: int, num_contexts: int, **kw) -> tuple[bool, int, str]:
    """M_PIPELINES_N_CONTEXTS top composed over the context pipeline and core."""
    core = f"ascon_perm_pipe_p{num_rounds}"
    ctx = context_pipeline_name(num_rounds, num_contexts)
    top = multi_pipeline_name(num_rounds, num_pipelines, num_contexts)
    return _run_sim_files(
        [(core, emit_pipelined_permutation(num_rounds)),
         (ctx, emit_context_pipeline(num_rounds, num_contexts)),
         (top, emit_multi_pipeline(num_rounds, num_pipelines, num_contexts))],
        emit_multi_pipeline_testbench(num_rounds, num_pipelines, num_contexts),
        **kw,
    )


def _aead_vectors(variant: str, seed: int) -> tuple[list[dict], int]:
    """Deterministic AEAD vectors for a variant from the model: encrypt (ct+tag),
    decrypt round-trip, and a corrupted-tag case, over lengths spanning empty,
    partial, block-aligned and multi-block for that variant's rate."""
    import random

    from ascon_hwmodel.aead_encrypt import aead_encrypt

    from ascon_designspace.generator.aead import aead_variant_params

    p = aead_variant_params(variant)
    enum, kb, r = p["enum"], p["key_bytes"], p["rate_bytes"]
    rng = random.Random(seed)
    rb = lambda n: bytes(rng.getrandbits(8) for _ in range(n))
    half = r // 2 if r > 1 else 0
    lengths = [(0, 0), (0, 1), (0, r), (0, r + 1), (half, 0), (r, r), (r, 2 * r - 1),
               (2 * r, 2 * r), (1, r - 1), (r - 1, 1), (0, 2 * r), (2 * r, 0),
               (r - 1, r - 1), (2 * r - 1, 2 * r)]
    vecs: list[dict] = []
    for adl, ml in lengths:
        key, nonce, ad, pt = rb(kb), rb(16), rb(adl), rb(ml)
        res = aead_encrypt(key, nonce, ad, pt, enum)
        ct, tag = res.ciphertext, res.tag
        vecs.append(dict(key=key, nonce=nonce, ad=ad, msg=pt, dec=False, tag_in=bytes(16),
                         exp_out=ct, exp_tag=tag, exp_valid=1, do_out=True, do_tag=True))
        vecs.append(dict(key=key, nonce=nonce, ad=ad, msg=ct, dec=True, tag_in=tag,
                         exp_out=pt, exp_tag=tag, exp_valid=1, do_out=True, do_tag=False))
    key, nonce, ad, pt = rb(kb), rb(16), rb(5), rb(12)
    res = aead_encrypt(key, nonce, ad, pt, enum)
    bad = bytearray(res.tag); bad[0] ^= 1
    vecs.append(dict(key=key, nonce=nonce, ad=ad, msg=res.ciphertext, dec=True, tag_in=bytes(bad),
                     exp_out=b"", exp_tag=bytes(16), exp_valid=0, do_out=False, do_tag=False))
    return vecs, kb


_AEAD_SEEDS = {"aead128": 0xAE01, "aead128a": 0xAE02, "ascon128": 0xAE03, "aead80pq": 0xAE04}


def verify_aead(variant: str, ad_max: int = 32, msg_max: int = 32, **kw) -> tuple[bool, int, str]:
    """Generated AEAD core (any variant) vs the model: encrypt/decrypt/tag-reject."""
    from ascon_designspace.generator.aead import emit_aead_core_for, emit_aead_testbench

    vecs, kb = _aead_vectors(variant, _AEAD_SEEDS[variant])
    name = f"ascon_{variant}_core"
    return _run_sim_files(
        [(name, emit_aead_core_for(variant, ad_max, msg_max)),
         ("ascon_perm_iter_r1", emit_iterative_permutation(1))],
        emit_aead_testbench(vecs, ad_max, msg_max, key_bytes=kb, module_name=name),
        **kw,
    )


def verify_aead128(**kw) -> tuple[bool, int, str]:
    return verify_aead("aead128", **kw)


def _hash256_vectors(seed: int = 0x4A5) -> list[dict]:
    import random

    from ascon_hwmodel.hash_xof import ascon_hash256

    rng = random.Random(seed)
    rb = lambda n: bytes(rng.getrandbits(8) for _ in range(n))
    msgs = [b"", b"abc", bytes(1), rb(7), rb(8), rb(9), rb(16), rb(17), rb(31), rb(32)]
    return [dict(msg=m, digest=ascon_hash256(m)) for m in msgs]


def verify_hash256(msg_max: int = 32, **kw) -> tuple[bool, int, str]:
    """Generated Hash256 core vs the model digests in sim."""
    from ascon_designspace.generator.hash256 import emit_hash256_core, emit_hash256_testbench

    vecs = _hash256_vectors()
    return _run_sim_files(
        [("ascon_hash256_core", emit_hash256_core(msg_max)),
         ("ascon_perm_iter_r1", emit_iterative_permutation(1))],
        emit_hash256_testbench(vecs, msg_max),
        **kw,
    )


def verify_xof128(out_bytes: int = 32, msg_max: int = 32, **kw) -> tuple[bool, int, str]:
    """Generated XOF128 core vs the model, at a word-aligned output length."""
    import random

    from ascon_hwmodel.hash_xof import ascon_xof128

    from ascon_designspace.generator.hash256 import emit_xof128_core, emit_xof128_testbench

    rng = random.Random(0x30F)
    rb = lambda n: bytes(rng.getrandbits(8) for _ in range(n))
    msgs = [b"", b"abc", rb(7), rb(8), rb(9), rb(16), rb(17), rb(31), rb(32)]
    vecs = [dict(msg=m, digest=ascon_xof128(m, out_bytes)) for m in msgs]
    return _run_sim_files(
        [("ascon_xof128_core", emit_xof128_core(out_bytes // 8, msg_max)),
         ("ascon_perm_iter_r1", emit_iterative_permutation(1))],
        emit_xof128_testbench(vecs, out_bytes, msg_max),
        **kw,
    )


def verify_cxof128(out_bytes: int = 32, msg_max: int = 32, cust_max: int = 32, **kw) -> tuple[bool, int, str]:
    """Generated CXOF128 core vs the model, with customization strings."""
    import random

    from ascon_hwmodel.hash_xof import ascon_cxof128

    from ascon_designspace.generator.hash256 import emit_cxof128_core, emit_cxof128_testbench

    rng = random.Random(0xCF)
    rb = lambda n: bytes(rng.getrandbits(8) for _ in range(n))
    pairs = [(0, 0), (0, 8), (5, 0), (8, 16), (3, 7), (16, 32), (20, 5)]
    vecs = []
    for cl, ml in pairs:
        cust, msg = rb(cl), rb(ml)
        vecs.append(dict(cust=cust, msg=msg, digest=ascon_cxof128(msg, out_bytes, cust)))
    return _run_sim_files(
        [("ascon_cxof128_core", emit_cxof128_core(out_bytes // 8, msg_max, cust_max)),
         ("ascon_perm_iter_r1", emit_iterative_permutation(1))],
        emit_cxof128_testbench(vecs, out_bytes, msg_max, cust_max),
        **kw,
    )


def _hashxof_ref(message: bytes, out_bytes: int, iv_bytes: bytes, b: int) -> bytes:
    """Ascon hash/XOF reference built from the model's VERIFIED primitives, with a
    parameterized intermediate round count b (p^b for absorb/squeeze, p12 for
    init/finalization). At b=12 this equals the model's Hash256/XOF128 exactly
    (checked in tests), so only the b value is spec-supplied - the byte-level
    structure is the model's."""
    from ascon_hwmodel.byteops import parse_bytes
    from ascon_hwmodel.rate import rate_bytes_from_state, xor_rate_bytes
    from ascon_hwmodel.round import ascon_permutation
    from ascon_hwmodel.state import AsconState

    state = ascon_permutation(AsconState.from_bytes(iv_bytes + bytes(32)), 12)
    parsed = parse_bytes(message, 8)
    for block in parsed.full_blocks:
        state = xor_rate_bytes(state, block, 8)
        state = ascon_permutation(state, b)
    state = xor_rate_bytes(state, parsed.padded_final_block(), 8)
    state = ascon_permutation(state, 12)
    out = bytearray()
    while len(out) < out_bytes:
        out.extend(rate_bytes_from_state(state, 8))
        if len(out) < out_bytes:
            state = ascon_permutation(state, b)
    return bytes(out[:out_bytes])


def _legacy_iv(variant_name: str) -> bytes:
    from ascon_hwmodel.hash_xof import HASH_XOF_CONFIGS, HashXofVariant

    return HASH_XOF_CONFIGS[HashXofVariant[variant_name]].iv_bytes


def _hashxof_msgs(seed: int) -> list[bytes]:
    import random

    rng = random.Random(seed)
    rb = lambda n: bytes(rng.getrandbits(8) for _ in range(n))
    return [b"", b"abc", rb(7), rb(8), rb(9), rb(16), rb(17), rb(31), rb(32)]


def verify_hasha(msg_max: int = 32, **kw) -> tuple[bool, int, str]:
    """Generated Ascon-Hasha core vs the b=8 reference (structure-verified at b=12)."""
    from ascon_designspace.generator.hash256 import emit_hash256_testbench, emit_hasha_core

    iv = _legacy_iv("LEGACY_HASHA")
    vecs = [dict(msg=m, digest=_hashxof_ref(m, 32, iv, 8)) for m in _hashxof_msgs(0xA5A)]
    return _run_sim_files(
        [("ascon_hasha_core", emit_hasha_core(msg_max)),
         ("ascon_perm_iter_r1", emit_iterative_permutation(1))],
        emit_hash256_testbench(vecs, msg_max, module_name="ascon_hasha_core"),
        **kw,
    )


def verify_xofa(out_bytes: int = 32, msg_max: int = 32, **kw) -> tuple[bool, int, str]:
    """Generated Ascon-Xofa core vs the b=8 reference."""
    from ascon_designspace.generator.hash256 import emit_xof128_testbench, emit_xofa_core

    iv = _legacy_iv("LEGACY_XOFA")
    vecs = [dict(msg=m, digest=_hashxof_ref(m, out_bytes, iv, 8)) for m in _hashxof_msgs(0xF0A)]
    return _run_sim_files(
        [("ascon_xofa_core", emit_xofa_core(out_bytes // 8, msg_max)),
         ("ascon_perm_iter_r1", emit_iterative_permutation(1))],
        emit_xof128_testbench(vecs, out_bytes, msg_max, module_name="ascon_xofa_core"),
        **kw,
    )


def verify_microcoded(**kw) -> tuple[bool, int, str]:
    """Microcoded-sequencer permutation core vs the model (same round datapath)."""
    from ascon_designspace.generator.control import emit_microcoded_permutation

    name = "ascon_perm_microcoded"
    return _run_sim(name, emit_microcoded_permutation(), emit_permutation_testbench(name), **kw)
