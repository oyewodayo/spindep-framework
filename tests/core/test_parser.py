from pathlib import Path

import pandas as pd
import pytest

from src.parser import (
    extract_potential,
    extract_sector_from_hyphen,
    normalize_sector,
    extract_sector,
    extract_coupling_and_class,
    build_label,
    extract_year,
    extract_author,
    parse_dataset,
    discover_datasets,
    load_dataset,
    FILENAME_SECTOR_OVERRIDES,
    FILENAME_POTENTIAL_OVERRIDES,
)


# ── extract_potential ───────────────────────────────────────────────────

@pytest.mark.parametrize("parts,expected", [
    (["V11", "Hunter", "2013"], "V11"),
    (["V1213", "Clayburn", "2023"], "V12+13"),
    (["V4+5", "Ficek", "2017"], "V4+5"),
    (["V910", "Crescini", "2022"], "V9+10"),
    (["V16", "Foo"], "V16"),
    (["2", "Fadeev", "2022"], "V2"),
    (["45Ficek", "2017"], "V4+5"),
    (["910Crescini", "2022"], "V9+10"),
    (["8Ji"], "V8"),
    (["1a", "eeastro"], "V1a"),
])
def test_extract_potential_explicit_and_prefix(parts, expected):
    assert extract_potential(parts) == expected


def test_extract_potential_empty_parts_is_unknown():
    assert extract_potential([]) == "UNKNOWN"


def test_extract_potential_no_token_falls_back_to_unknown():
    assert extract_potential(["Foo", "Bar"]) == "UNKNOWN"


def test_extract_potential_directory_fallback():
    # Hoskins_1985.csv carries no potential token at all; the parent
    # directory V1_alpha_data/ is the only source of the potential.
    fp = Path("spindep/datasets/normalized/V1/V1_alpha_data/Hoskins_1985.csv")
    assert extract_potential(["Hoskins", "1985"], filepath=fp) == "V1"


# ── sector extraction / normalization ───────────────────────────────────

def test_extract_sector_from_hyphen():
    assert extract_sector_from_hyphen("V11_Hunter_2013_e-n") == "en"
    assert extract_sector_from_hyphen("V1213_Clayburn_2023_n-N") == "nN"


def test_extract_sector_from_hyphen_no_match_returns_none():
    assert extract_sector_from_hyphen("V11_Hunter_2013_ee") is None


@pytest.mark.parametrize("raw,expected", [
    ("ebare", "eebar"),
    ("ebar", "eebar"),
    ("epbare", "epbar"),
    ("nnbare", "nnbar"),
    ("ee", "ee"),          # not in SECTOR_ALIASES -> returned unchanged
])
def test_normalize_sector(raw, expected):
    assert normalize_sector(raw) == expected


def test_normalize_sector_strips_copy_suffix():
    assert normalize_sector("ee copy") == "ee"


def test_extract_sector_skips_reserved_tokens():
    parts = ["2TestAuthor2024", "m", "abs", "ee"]
    assert extract_sector(parts, coupling="gAgA") == "ee"


def test_extract_sector_unknown_when_no_candidates():
    parts = ["2", "m", "abs"]
    assert extract_sector(parts) == "UNKNOWN"


def test_extract_sector_joins_split_two_letter_tokens():
    # "p" + "N" (in that filename order) should join to a known sector "pN"
    parts = ["V1", "Salumbides", "2018", "p", "N"]
    assert extract_sector(parts) == "pN"


# ── coupling / interaction class ────────────────────────────────────────

def test_extract_coupling_and_class_from_normalized_path():
    fp = Path("/home/x/spindep/datasets/normalized/gAgA/lepton-lepton/2Foo_2020_m_abs_ee.csv")
    coupling, cls = extract_coupling_and_class(fp)
    assert (coupling, cls) == ("gAgA", "lepton-lepton")


def test_extract_coupling_and_class_fallback_without_normalized_dir():
    fp = Path("/some/other/gVgV/nucleon-nucleon/file.csv")
    coupling, cls = extract_coupling_and_class(fp)
    assert (coupling, cls) == ("gVgV", "nucleon-nucleon")


# ── author / year ────────────────────────────────────────────────────────

def test_extract_year_standalone_token():
    assert extract_year(["2", "Fadeev", "2022", "m", "abs", "ee"]) == "2022"


def test_extract_year_fused_author_year():
    assert extract_year(["2TestAuthor2024", "m", "abs", "ee"]) == "2024"


def test_extract_year_unknown_when_absent():
    assert extract_year(["Foo", "Bar"]) == "UNKNOWN"


def test_extract_author_fused_prefix_and_year():
    assert extract_author(["2TestAuthor2024", "m", "abs", "ee"]) == "TestAuthor"


def test_extract_author_skips_coupling_tokens():
    # "gse" is a coupling-type token, not an author name; the real author
    # (Casimir) follows later in the filename.
    assert extract_author(["V1", "gse", "Casimir"]) == "Casimir"


def test_extract_author_unknown_when_absent():
    assert extract_author(["1", "2020", "m", "abs"]) == "UnknownAuthor"


# ── build_label ──────────────────────────────────────────────────────────

def test_build_label_known_and_unknown_sector():
    assert build_label("Fadeev2022", "ee") == "Fadeev2022 (e⁻-e⁻)"
    assert build_label("Foo2020", "totally_unmapped") == "Foo2020 (totally_unmapped)"


# ── FILENAME_*_OVERRIDES sanity ─────────────────────────────────────────

def test_filename_sector_overrides_well_formed():
    for name, (sector, is_anti) in FILENAME_SECTOR_OVERRIDES.items():
        assert isinstance(sector, str) and sector
        assert isinstance(is_anti, bool)


def test_filename_potential_overrides_well_formed():
    for name, potential in FILENAME_POTENTIAL_OVERRIDES.items():
        assert potential.startswith("V")


# ── parse_dataset (end-to-end on filenames) ─────────────────────────────

def test_parse_dataset_basic_matter_file(tmp_path):
    fp = tmp_path / "normalized" / "gAgA" / "lepton-lepton" / "2TestAuthor2024_m_abs_ee.csv"
    fp.parent.mkdir(parents=True)
    fp.write_text("1e-9,1e-10\n1e-8,1e-11\n")

    ds = parse_dataset(fp)
    assert ds is not None
    assert ds.coupling == "gAgA"
    assert ds.interaction_class == "lepton-lepton"
    assert ds.potential == "V2"
    assert ds.sector == "ee"
    assert ds.contains_antimatter is False
    assert ds.source == "TestAuthor2024"


def test_parse_dataset_antimatter_file(tmp_path):
    fp = tmp_path / "normalized" / "gAgA" / "lepton-lepton" / "2TestAuthor2024_m_abs_ebare.csv"
    fp.parent.mkdir(parents=True)
    fp.write_text("1e-9,1e-10\n1e-8,1e-11\n")

    ds = parse_dataset(fp)
    assert ds is not None
    assert ds.sector == "eebar"
    assert ds.contains_antimatter is True


def test_parse_dataset_filename_override_applied(tmp_path):
    fp = tmp_path / "normalized" / "V1" / "V1_alpha_data" / "Hoskins_1985.csv"
    fp.parent.mkdir(parents=True)
    fp.write_text("1e-9,1e-10\n")

    ds = parse_dataset(fp)
    assert ds is not None
    # FILENAME_SECTOR_OVERRIDES["Hoskins_1985"] = ("nn", False)
    assert ds.sector == "nn"
    assert ds.contains_antimatter is False


def test_parse_dataset_unrecognized_sector_prints_warning_but_still_returns(tmp_path, capsys):
    fp = tmp_path / "normalized" / "gAgA" / "lepton-lepton" / "9_TotallyUnknownSector_2020_m_abs_zzz.csv"
    fp.parent.mkdir(parents=True)
    fp.write_text("1e-9,1e-10\n")

    ds = parse_dataset(fp)
    assert ds is not None
    assert ds.sector == "zzz"
    captured = capsys.readouterr()
    assert "[WARN] Unrecognized sector" in captured.out


def test_parse_dataset_returns_none_on_internal_error(tmp_path, monkeypatch):
    import src.parser as parser_mod

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(parser_mod, "extract_potential", boom)
    fp = tmp_path / "2Foo_2020_m_abs_ee.csv"
    fp.write_text("1e-9,1e-10\n")

    assert parse_dataset(fp) is None


# ── discover_datasets ────────────────────────────────────────────────────

def test_discover_datasets_finds_all_csvs(tmp_dataset_dir):
    datasets = discover_datasets(tmp_dataset_dir / "normalized")
    assert len(datasets) == 2
    filenames = {d.filename for d in datasets}
    assert filenames == {"2TestAuthor2024_m_abs_ee", "2TestAuthor2024_m_abs_ebare"}


def test_discover_datasets_empty_dir_returns_empty_list(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert discover_datasets(empty) == []


# ── load_dataset ─────────────────────────────────────────────────────────

def test_load_dataset_drops_non_numeric_and_non_positive_rows(tmp_path):
    fp = tmp_path / "dirty.csv"
    fp.write_text(
        "1e-9,1e-10\n"
        "not_a_number,1e-11\n"
        "1e-8,-5\n"          # negative coupling -> dropped
        "-1e-7,1e-12\n"      # negative lambda -> dropped
        "2e-9,2e-10\n"
    )
    df = load_dataset(fp)
    assert list(df.columns) == ["lambda_m", "coupling_abs"]
    assert len(df) == 2
    assert (df["lambda_m"] > 0).all()
    assert (df["coupling_abs"] > 0).all()


def test_load_dataset_sorted_by_lambda(tmp_path):
    fp = tmp_path / "unsorted.csv"
    fp.write_text("3e-8,1e-10\n1e-9,1e-11\n2e-8,1e-12\n")
    df = load_dataset(fp)
    assert list(df["lambda_m"]) == sorted(df["lambda_m"])


def test_load_dataset_on_real_fixture(real_fixtures_dir):
    df = load_dataset(real_fixtures_dir / "Hoskins_1985.csv")
    assert len(df) > 0
    assert (df["lambda_m"] > 0).all()
    assert (df["coupling_abs"] > 0).all()
