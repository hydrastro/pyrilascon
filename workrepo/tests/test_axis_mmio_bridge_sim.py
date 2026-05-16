from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools.run_axis_mmio_bridge_vector import (
    make_vector,
    result_to_jsonable,
    run_vector,
)

ROOT = Path(__file__).resolve().parents[1]


def test_axis_mmio_bridge_sim_dry_run_generates_expected_testbench() -> None:
    vector = make_vector(
        tx_payload=bytes.fromhex("000102030405060708090a0b0c0d0e0f"),
        tx_user=2,
        tx_last=True,
        rx_payload=bytes.fromhex("a0a1a2a3a4"),
        rx_user=2,
        rx_last=True,
    )
    result = run_vector(repo_root=ROOT, dry_run=True, vector=vector)

    assert result.rtl is None
    assert result.matched is None
    assert result.testbench is not None
    assert "module tb_ascon_axis_mmio_bridge" in result.testbench
    assert "ascon_axis_mmio_bridge dut" in result.testbench
    assert "mmio_write(8'h18" in result.testbench
    assert "TX_BEAT" in result.testbench
    assert "RX_ACCEPT" in result.testbench
    assert "STATUS_BEFORE_POP" in result.testbench
    assert "STATUS_AFTER_POP" in result.testbench


def test_axis_mmio_bridge_sim_jsonable_result_for_dry_run() -> None:
    vector = make_vector(
        tx_payload=b"hello",
        tx_user=1,
        tx_last=True,
        rx_payload=b"world!",
        rx_user=2,
        rx_last=False,
    )
    result = run_vector(repo_root=ROOT, dry_run=True, vector=vector)
    payload = result_to_jsonable(result)

    assert payload["matched"] is None
    assert payload["vector"]["tx_payload_hex"] == b"hello".hex()
    assert payload["vector"]["tx_keep_hex"] == "001f"
    assert payload["vector"]["rx_payload_hex"] == b"world!".hex()
    assert json.dumps(payload)


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog/vvp not installed")
def test_axis_mmio_bridge_sim_transmits_and_receives_one_beat() -> None:
    vector = make_vector(
        tx_payload=bytes.fromhex("000102030405060708090a0b0c0d0e0f"),
        tx_user=2,
        tx_last=True,
        rx_payload=bytes.fromhex("a0a1a2a3a4"),
        rx_user=2,
        rx_last=True,
    )
    result = run_vector(repo_root=ROOT, dry_run=False, vector=vector)

    assert result.matched is True, json.dumps(result_to_jsonable(result), indent=2)
    assert result.rtl is not None
    assert result.rtl.tx_payload_hex == vector.tx_payload_hex
    assert result.rtl.rx_payload_hex == vector.rx_payload_hex
    assert int(result.rtl.status_before_pop_hex, 16) & 0x2
    assert not (int(result.rtl.status_after_pop_hex, 16) & 0x2)


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog/vvp not installed")
def test_axis_mmio_bridge_sim_handles_partial_tx_and_nonfinal_rx() -> None:
    vector = make_vector(
        tx_payload=b"metadata",
        tx_user=1,
        tx_last=False,
        rx_payload=b"chunk",
        rx_user=2,
        rx_last=False,
    )
    result = run_vector(repo_root=ROOT, dry_run=False, vector=vector)

    assert result.matched is True, json.dumps(result_to_jsonable(result), indent=2)
    assert result.rtl is not None
    assert result.rtl.tx_keep_hex == "00ff"
    assert result.rtl.tx_last is False
    assert result.rtl.rx_last is False
