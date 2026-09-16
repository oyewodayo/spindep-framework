import numpy as np
import pandas as pd
import pytest

from src.null_test import (
    run_null_test,
    _inject_scale,
    _inject_replace,
    _inject_shift,
    _sigma_from_pval,
)


def _make_dfs():
    lam = np.logspace(-9, -6, 40)
    g_m = 1e-10 * (lam / 1e-8) ** -0.5
    g_a = 1.05e-10 * (lam / 1e-8) ** -0.5
    return (
        pd.DataFrame({"lambda_m": lam, "coupling_abs": g_m}),
        pd.DataFrame({"lambda_m": lam, "coupling_abs": g_a}),
    )


# ── _sigma_from_pval ──────────────────────────────────────────────────────

def test_sigma_from_pval_small_pvalue_gives_large_sigma():
    assert _sigma_from_pval(1e-10) > _sigma_from_pval(0.5)


def test_sigma_from_pval_p_near_one_gives_near_zero_sigma():
    # sigma = sqrt(2) * erfinv(1 - p); as p -> 1, (1-p) -> 0 -> erfinv -> 0
    assert _sigma_from_pval(1.0 - 1e-12) == pytest.approx(0.0, abs=1e-4)


# ── injector helpers ───────────────────────────────────────────────────

def test_inject_scale_reduces_antimatter_curve_for_positive_aalpha():
    lam = np.logspace(-9, -6, 20)
    g_m = np.full(20, 1e-10)
    g_a = np.full(20, 1e-10)
    rng = np.random.default_rng(0)
    _, g_a_new = _inject_scale(lam, g_m, g_a, aalpha=0.5, rng=rng)
    # Envelope peaks in the middle of the lambda range -> biggest reduction there
    mid = len(lam) // 2
    assert g_a_new[mid] < g_a[mid]


def test_inject_replace_gives_target_asymmetry():
    lam = np.logspace(-9, -6, 20)
    g_m = np.full(20, 1e-10)
    g_a = np.full(20, 1e-10)
    rng = np.random.default_rng(0)
    _, g_a_new = _inject_replace(lam, g_m, g_a, aalpha=0.5, rng=rng)
    A = (g_m - g_a_new) / (g_m + g_a_new)
    assert np.mean(A) == pytest.approx(0.5, abs=0.02)


def test_inject_shift_zero_aalpha_leaves_curve_unchanged_up_to_jitter():
    lam = np.logspace(-9, -6, 20)
    g_m = np.full(20, 2e-10)
    g_a = np.full(20, 1e-10)
    rng = np.random.default_rng(0)
    # aalpha=0 -> 10**(0 * mean_offset) == 1, so only the ~0.5% jitter remains
    _, g_a_new = _inject_shift(lam, g_m, g_a, aalpha=0.0, rng=rng)
    assert np.allclose(g_a_new, g_a, rtol=0.03)


# ── run_null_test ──────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", ["scale", "replace", "shift"])
def test_run_null_test_happy_path_all_modes(mode):
    df_m, df_a = _make_dfs()
    result = run_null_test(
        pair_id="test-pair",
        df_matter=df_m,
        df_antimatter=df_a,
        injected_aalpha=0.3,
        injection_mode=mode,
        seed=42,
    )
    assert result["status"] == "done"
    assert result["injection_mode"] == mode
    assert np.isfinite(result["recovery_fraction"])
    assert result["recovery_fraction"] >= 0.0
    assert len(result["points"]) > 0
    assert isinstance(result["calibration_ok"], bool)


def test_run_null_test_deterministic_with_fixed_seed():
    df_m, df_a = _make_dfs()
    r1 = run_null_test(pair_id="p", df_matter=df_m, df_antimatter=df_a,
                        injected_aalpha=0.4, injection_mode="scale", seed=7)
    r2 = run_null_test(pair_id="p", df_matter=df_m, df_antimatter=df_a,
                        injected_aalpha=0.4, injection_mode="scale", seed=7)
    assert r1["mean_recovered"] == r2["mean_recovered"]
    assert r1["chi2_recovered"] == r2["chi2_recovered"]


def test_run_null_test_too_few_points_raises():
    df_m = pd.DataFrame({"lambda_m": [1e-9, 2e-9], "coupling_abs": [1e-10, 1e-11]})
    df_a = pd.DataFrame({"lambda_m": [1e-9, 2e-9], "coupling_abs": [1e-10, 1e-11]})
    with pytest.raises(ValueError, match="too short"):
        run_null_test(pair_id="p", df_matter=df_m, df_antimatter=df_a,
                       injected_aalpha=0.3)


def test_run_null_test_no_overlap_raises():
    lam_m = np.logspace(-12, -10, 10)
    lam_a = np.logspace(-6, -4, 10)
    df_m = pd.DataFrame({"lambda_m": lam_m, "coupling_abs": np.full(10, 1e-10)})
    df_a = pd.DataFrame({"lambda_m": lam_a, "coupling_abs": np.full(10, 1e-10)})
    with pytest.raises(ValueError, match="overlap"):
        run_null_test(pair_id="p", df_matter=df_m, df_antimatter=df_a,
                       injected_aalpha=0.3)


def test_run_null_test_unknown_injection_mode_raises():
    df_m, df_a = _make_dfs()
    with pytest.raises(ValueError, match="Unknown injection_mode"):
        run_null_test(pair_id="p", df_matter=df_m, df_antimatter=df_a,
                       injected_aalpha=0.3, injection_mode="bogus")
