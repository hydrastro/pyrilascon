from pathlib import Path


def test_tangnano9k_aead128_kat_target_files_exist() -> None:
    root = Path("boards/tangnano9k/ascon_aead128_kat_slow")
    required = [
        root / "Makefile",
        root / "tangnano9k_ascon_aead128_kat.cst",
        root / "rtl/ascon_round_comb.v",
        root / "rtl/ascon_aead128_kat_slow_core.v",
        root / "rtl/tangnano9k_ascon_aead128_kat_top.v",
    ]
    for path in required:
        assert path.is_file(), path


def test_tangnano9k_aead128_core_declares_full_phases() -> None:
    text = Path("boards/tangnano9k/ascon_aead128_kat_slow/rtl/ascon_aead128_kat_slow_core.v").read_text()
    for token in ["ST_INIT_P12", "ST_AD_P8", "ST_DOMAIN", "ST_PT_FULL", "ST_PT_FINAL", "ST_FINAL_P12", "CT_EXPECTED", "TAG_EXPECTED"]:
        assert token in text
