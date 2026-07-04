"""The host benchmark parser/report must correctly turn CASE lines into the
SW-vs-HW comparison and headline verdict. Runs natively (no board)."""
import textwrap

from host.ascon_bench import Report, format_report, parse_case, parse_log

# A representative log: accelerator correct and fewer cycles than the CPU ref.
GOOD_LOG = textwrap.dedent(
    """
    pyrilascon NEORV32 ASCON benchmark
    BUILD        : cosim-neorv32-mmio
    CASE name=ad0_pt0 ad=0 pt=0 sw_enc_cy=0:12000 sw_dec_cy=0:12500 hw_enc_cy=0:1800 hw_dec_cy=0:1900 enc_ok=1 dec_ok=1 tag_valid=1 hw_enc_err=0x0 hw_dec_err=0x0
    CASE name=ad0_pt16 ad=0 pt=16 sw_enc_cy=0:20000 sw_dec_cy=0:20500 hw_enc_cy=0:2600 hw_dec_cy=0:2700 enc_ok=1 dec_ok=1 tag_valid=1 hw_enc_err=0x0 hw_dec_err=0x0
    CASE name=ad16_pt32 ad=16 pt=32 sw_enc_cy=1:0 sw_dec_cy=1:100 hw_enc_cy=0:5000 hw_dec_cy=0:5200 enc_ok=1 dec_ok=1 tag_valid=1 hw_enc_err=0x0 hw_dec_err=0x0
    CASE name=too_big ad=0 pt=64 SKIP reason=exceeds_backend_max
    SUMMARY      : passed=3 failed=0 total=3
    PASS
    """
)


def test_parses_all_data_cases_and_skips_non_cases():
    cases = parse_log(GOOD_LOG)
    assert [c.name for c in cases] == ["ad0_pt0", "ad0_pt16", "ad16_pt32"]  # SKIP dropped


def test_cycle_pairs_and_speedup():
    c = parse_case(
        "CASE name=x ad=16 pt=32 sw_enc_cy=1:0 sw_dec_cy=1:100 hw_enc_cy=0:5000 "
        "hw_dec_cy=0:5200 enc_ok=1 dec_ok=1 tag_valid=1 hw_enc_err=0x0 hw_dec_err=0x0"
    )
    assert c is not None
    assert c.sw_enc == (1 << 32)  # HI:LO reassembled to 64-bit
    assert c.hw_enc == 5000
    assert abs(c.enc_speedup - (1 << 32) / 5000) < 1e-6
    assert c.hw_faster and c.correct


def test_headline_pass_when_correct_and_faster():
    rep = Report(parse_log(GOOD_LOG))
    assert rep.all_correct and rep.all_hw_faster and rep.passed
    assert "HEADLINE PASS" in format_report(rep.cases)


def test_headline_fails_if_hw_not_faster():
    slow = (
        "CASE name=x ad=0 pt=0 sw_enc_cy=0:1000 sw_dec_cy=0:1000 hw_enc_cy=0:9000 "
        "hw_dec_cy=0:9000 enc_ok=1 dec_ok=1 tag_valid=1 hw_enc_err=0x0 hw_dec_err=0x0"
    )
    rep = Report(parse_log(slow))
    assert rep.all_correct and not rep.all_hw_faster and not rep.passed


def test_headline_fails_if_incorrect():
    bad = (
        "CASE name=x ad=0 pt=0 sw_enc_cy=0:9000 sw_dec_cy=0:9000 hw_enc_cy=0:1000 "
        "hw_dec_cy=0:1000 enc_ok=1 dec_ok=1 tag_valid=0 hw_enc_err=0x0 hw_dec_err=0x2"
    )
    rep = Report(parse_log(bad))
    assert rep.all_hw_faster and not rep.all_correct and not rep.passed
