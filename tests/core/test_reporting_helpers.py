import pytest

from src.reporting import significance_label, asymmetry_interpretation, _pval_eff


# ── significance_label ───────────────────────────────────────────────────

@pytest.mark.parametrize("p,expected_prefix", [
    (0.0001, "***"),
    (0.005,  "**"),
    (0.02,   "*"),
    (0.5,    "ns"),
])
def test_significance_label_thresholds(p, expected_prefix):
    assert significance_label(p).startswith(expected_prefix)


def test_significance_label_boundary_values():
    # exactly at a boundary should fall into the *lower* significance bucket
    assert significance_label(0.001).startswith("**") and not significance_label(0.001).startswith("***")
    assert significance_label(0.05).startswith("ns")


# ── asymmetry_interpretation ─────────────────────────────────────────────

@pytest.mark.parametrize("a,expected_substr", [
    (0.9,  "Strong"),
    (0.3,  "Moderate"),
    (0.1,  "Weak"),
    (0.01, "Near-symmetric"),
])
def test_asymmetry_interpretation(a, expected_substr):
    assert expected_substr in asymmetry_interpretation(a)


# ── _pval_eff ─────────────────────────────────────────────────────────────

def test_pval_eff_prefers_weighted_eff_key():
    row = {"p_value_weighted_eff": 0.01, "p_value_weighted": 0.5, "p_value": 0.9}
    assert _pval_eff(row) == 0.01


def test_pval_eff_falls_back_to_weighted_then_plain():
    row = {"p_value_weighted": 0.5, "p_value": 0.9}
    assert _pval_eff(row) == 0.5

    row2 = {"p_value": 0.9}
    assert _pval_eff(row2) == 0.9


def test_pval_eff_defaults_to_zero_when_missing():
    assert _pval_eff({}) == 0
