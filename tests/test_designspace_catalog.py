"""The new design-space catalog must reproduce the exact valid-point counts of
the old enumeration (ASIC 352, FPGA 208, 560 total) and attach an honest
realization tier to every point.
"""
from ascon_designspace.axes import SecurityProfile, TargetTechnology
from ascon_designspace.catalog import catalog_entries, summarize
from ascon_designspace.realize import RealizationStatus, RealizationTier


def test_catalog_reproduces_valid_counts() -> None:
    s = summarize()
    assert s["total"] == 560
    assert s["by_target"][TargetTechnology.ASIC] == 352
    assert s["by_target"][TargetTechnology.FPGA] == 208


def test_every_point_has_a_realization() -> None:
    entries = catalog_entries()
    assert len(entries) == 560
    assert all(real is not None for _, real in entries)


def test_tier_totals_sum_to_total() -> None:
    s = summarize()
    assert sum(s["by_tier"].values()) == s["total"]
    assert sum(s["by_status"].values()) == s["total"]


def test_all_three_tiers_are_represented() -> None:
    tiers = {real.tier for _, real in catalog_entries()}
    assert RealizationTier.GENERATOR in tiers
    assert RealizationTier.HANDWRITTEN in tiers
    assert RealizationTier.SPECIFIED in tiers


def test_security_countermeasures_are_never_generated() -> None:
    # Our decision: any non-none security profile is Tier 3, never auto-generated.
    for point, real in catalog_entries():
        if point.security is not SecurityProfile.NONE:
            assert real.tier is RealizationTier.SPECIFIED
            assert real.status is RealizationStatus.SPECIFIED_ONLY


def test_handwritten_cores_are_the_working_fpga_aead128_cores() -> None:
    hw = [p for p, r in catalog_entries() if r.tier is RealizationTier.HANDWRITTEN]
    assert hw, "expected at least the vetted FPGA AEAD128 cores"
    for point in hw:
        assert point.target is TargetTechnology.FPGA
        assert point.security is SecurityProfile.NONE


def test_generator_backed_points_are_marked_generated() -> None:
    # With the round-based generator in place, some tier-1 points are GENERATED
    # (verified core exists) rather than merely planned.
    from ascon_designspace.realize import RealizationStatus

    status = summarize()["by_status"]
    assert status.get(RealizationStatus.GENERATED, 0) > 0
