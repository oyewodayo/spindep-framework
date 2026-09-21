import pandas as pd
import pytest

from src.unit_conversion import (
    detect_unit_factor,
    convert_lambda_to_metres,
    audit_units,
    HBAR_C_EV_M,
    HBAR_C_MEV_M,
    ALREADY_CONVERTED,
)


# ── detect_unit_factor ──────────────────────────────────────────────────
# These cases mirror the module's own __main__ self-test triples, minus
# the ALREADY_CONVERTED filename (see test below — the module's own
# self-test is stale for that one case, so we assert actual behavior).

@pytest.mark.parametrize("filename,expected_factor,expected_label", [
    ("3Fadeev_2022_2_m_abs_ebare",  1.0,          "m"),
    ("3Terrano_2015_m_abs_ee",      1.0,          "m"),
    ("SomeFile_cm_sector",          1e-2,         "cm"),
    ("SomeFile_nm_sector",          1e-9,         "nm"),
    ("SomeFile_fm_sector",          1e-15,        "fm"),
    ("SomeFile_mm_sector",          1e-3,         "mm"),
    ("SomeFile_ang_sector",         1e-10,        "Å"),
    ("SomeFile_ev_sector",          HBAR_C_EV_M,  "eV⁻¹"),
    ("SomeFile_gev_sector",         HBAR_C_MEV_M * 1e-3, "GeV⁻¹"),
    ("Foo_millionev_bar",           HBAR_C_MEV_M, "MeV⁻¹"),
])
def test_detect_unit_factor(filename, expected_factor, expected_label):
    factor, label = detect_unit_factor(filename)
    assert factor == pytest.approx(expected_factor, rel=1e-6)
    assert label == expected_label


def test_detect_unit_factor_already_converted_override():
    # The module's own __main__ self-test block predates the
    # ALREADY_CONVERTED override and still expects this exact filename to
    # convert as MeV^-1 -- it no longer does. This test documents the real,
    # current behavior: ALREADY_CONVERTED wins and returns a 1.0 factor.
    filename = "2Karshenboim_2011_1_millionev_abs_ep"
    assert filename in ALREADY_CONVERTED
    factor, label = detect_unit_factor(filename)
    assert factor == 1.0
    assert label == "m (pre-converted)"


def test_detect_unit_factor_unrecognized_unit_defaults_to_metres():
    factor, label = detect_unit_factor("SomeWeirdFilename_xyz")
    assert factor == 1.0
    assert label == "m"


# ── convert_lambda_to_metres ─────────────────────────────────────────────

def test_convert_lambda_to_metres_returns_same_object_when_no_conversion():
    df = pd.DataFrame({"lambda_m": [1.0, 2.0], "coupling_abs": [1e-10, 1e-11]})
    out_df, factor, label = convert_lambda_to_metres(df, "3Terrano_2015_m_abs_ee")
    assert factor == 1.0
    assert out_df is df


def test_convert_lambda_to_metres_returns_copy_and_scales_when_converting():
    df = pd.DataFrame({"lambda_m": [1.0, 2.0], "coupling_abs": [1e-10, 1e-11]})
    out_df, factor, label = convert_lambda_to_metres(df, "SomeFile_cm_sector")
    assert factor == 1e-2
    assert out_df is not df
    assert list(out_df["lambda_m"]) == [0.01, 0.02]
    # original untouched
    assert list(df["lambda_m"]) == [1.0, 2.0]


# ── audit_units ──────────────────────────────────────────────────────────

def test_audit_units_reports_factor_per_dataset(make_dataset, tmp_path, capsys):
    d1 = make_dataset(filename="Foo_m_abs_ee")
    d2 = make_dataset(filename="Bar_cm_sector")
    report = audit_units([d1, d2], verbose=False)
    assert report["Foo_m_abs_ee"] == (1.0, "m")
    assert report["Bar_cm_sector"] == (1e-2, "cm")
