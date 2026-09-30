import numpy as np
import pandas as pd
import pytest

from src.statistics import (
    chi_squared_sensitivity,
    estimate_uncertainty,
    chi_squared_weighted,
    effective_dof,
    bootstrap_aalpha_ci,
    chi_squared_from_datasets,
    uncertainty_summary,
)


# ── chi_squared_sensitivity ──────────────────────────────────────────────

def test_chi_squared_sensitivity_identical_curves_gives_zero_chi2():
    g = np.array([1.0, 2.0, 3.0])
    chi2, dof, p = chi_squared_sensitivity(g, g)
    assert chi2 == pytest.approx(0.0)
    assert dof == 3
    assert p == pytest.approx(1.0)


def test_chi_squared_sensitivity_larger_difference_gives_larger_chi2():
    g_m = np.array([1.0, 1.0, 1.0])
    g_a_small_diff = np.array([1.05, 1.05, 1.05])
    g_a_large_diff = np.array([2.0, 2.0, 2.0])
    chi2_small, _, _ = chi_squared_sensitivity(g_m, g_a_small_diff)
    chi2_large, _, _ = chi_squared_sensitivity(g_m, g_a_large_diff)
    assert chi2_large > chi2_small


# ── estimate_uncertainty ─────────────────────────────────────────────────

def test_estimate_uncertainty_short_input_returns_baseline():
    lam = np.array([1e-9, 2e-9])
    g   = np.array([1e-10, 2e-10])
    sigma = estimate_uncertainty(lam, g, baseline_frac=0.07)
    assert len(sigma) == 2
    assert np.all(sigma == 0.07)


def test_estimate_uncertainty_smooth_power_law_is_near_baseline():
    lam = np.logspace(-10, -6, 50)
    g   = 1e-10 * (lam / 1e-8) ** -0.5   # perfectly smooth power law
    sigma = estimate_uncertainty(lam, g, baseline_frac=0.05, min_frac=0.02, max_frac=0.5)
    assert np.all(sigma >= 0.02)
    assert np.all(sigma <= 0.5)
    # A perfectly smooth curve has ~zero curvature everywhere -> should sit
    # at (or very near) the baseline fraction, not the noisy max.
    assert np.median(sigma) == pytest.approx(0.05, abs=0.01)


def test_estimate_uncertainty_clips_to_min_max():
    lam = np.logspace(-10, -6, 50)
    rng = np.random.default_rng(0)
    g = 1e-10 * (1 + 0.9 * rng.standard_normal(50))  # jagged, high curvature
    sigma = estimate_uncertainty(lam, np.abs(g) + 1e-12, min_frac=0.02, max_frac=0.3)
    assert np.all(sigma >= 0.02)
    assert np.all(sigma <= 0.3)


# ── chi_squared_weighted ─────────────────────────────────────────────────

def test_chi_squared_weighted_identical_curves_gives_zero_chi2():
    g = np.array([1.0, 2.0, 3.0])
    sigma = np.array([0.1, 0.1, 0.1])
    chi2, dof, p, sigma_combined = chi_squared_weighted(g, g, sigma, sigma)
    assert chi2 == pytest.approx(0.0)
    assert dof == 3
    assert len(sigma_combined) == 3


def test_chi_squared_weighted_ignores_non_finite_points():
    g_m = np.array([1.0, np.nan, 3.0])
    g_a = np.array([1.0, 2.0, 3.0])
    sigma = np.array([0.1, 0.1, 0.1])
    chi2, dof, p, sigma_combined = chi_squared_weighted(g_m, g_a, sigma, sigma)
    assert dof == 2  # the NaN point is excluded


# ── effective_dof ─────────────────────────────────────────────────────────

def test_effective_dof_short_input_short_circuits():
    residuals = np.array([1.0, 2.0, 3.0])  # n < 4
    lam_grid  = np.array([1e-9, 2e-9, 3e-9])
    result = effective_dof(residuals, lam_grid)
    assert result == {"dof_effective": 3, "autocorr_length": 1.0, "n_valid": 3}


def test_effective_dof_uncorrelated_noise_gives_dof_near_n():
    rng = np.random.default_rng(1)
    residuals = rng.standard_normal(200)
    lam_grid  = np.logspace(-10, -6, 200)
    result = effective_dof(residuals, lam_grid)
    assert result["n_valid"] == 200
    # Uncorrelated noise: autocorrelation length should be small (near 1),
    # so dof_effective should be close to n, not drastically reduced.
    assert result["dof_effective"] > 100


def test_effective_dof_ignores_nan_residuals():
    residuals = np.array([1.0, np.nan, 2.0, 3.0, 4.0, 5.0])
    lam_grid  = np.arange(6, dtype=float)
    result = effective_dof(residuals, lam_grid)
    assert result["n_valid"] == 5


# ── bootstrap_aalpha_ci ───────────────────────────────────────────────────

def test_bootstrap_aalpha_ci_empty_input_returns_zeros():
    A = np.array([np.nan, np.nan])
    sigma = np.array([np.nan, np.nan])
    result = bootstrap_aalpha_ci(A, sigma, n_boot=10, seed=0)
    assert result["mean_aalpha"] == 0.0
    assert result["ci_low"] == 0.0
    assert result["ci_high"] == 0.0


def test_bootstrap_aalpha_ci_deterministic_with_fixed_seed():
    A = np.array([0.1, 0.2, 0.3, 0.15, 0.25])
    sigma = np.array([0.05, 0.05, 0.05, 0.05, 0.05])
    r1 = bootstrap_aalpha_ci(A, sigma, n_boot=500, seed=0)
    r2 = bootstrap_aalpha_ci(A, sigma, n_boot=500, seed=0)
    assert r1 == r2  # same seed -> bit-identical result


def test_bootstrap_aalpha_ci_ci_bounds_contain_mean():
    A = np.array([0.1, 0.2, 0.3, 0.15, 0.25])
    sigma = np.array([0.05, 0.05, 0.05, 0.05, 0.05])
    result = bootstrap_aalpha_ci(A, sigma, n_boot=1000, seed=0)
    assert result["ci_low"] <= result["mean_aalpha"] <= result["ci_high"]


# ── chi_squared_from_datasets ─────────────────────────────────────────────

def test_chi_squared_from_datasets_returns_none_on_no_overlap(non_overlapping_csv_pair):
    m_path, a_path = non_overlapping_csv_pair
    df_m = pd.read_csv(m_path, header=None, names=["lambda_m", "coupling_abs"])
    df_a = pd.read_csv(a_path, header=None, names=["lambda_m", "coupling_abs"])
    assert chi_squared_from_datasets(df_m, df_a) is None


def test_chi_squared_from_datasets_known_constant_asymmetry(matter_antimatter_csv_pair):
    m_path, a_path = matter_antimatter_csv_pair
    df_m = pd.read_csv(m_path, header=None, names=["lambda_m", "coupling_abs"])
    df_a = pd.read_csv(a_path, header=None, names=["lambda_m", "coupling_abs"])

    result = chi_squared_from_datasets(df_m, df_a, n_points=100, n_boot=200)
    assert result is not None

    # g_a = 2*g_m everywhere -> A_alpha = (g_m-g_a)/(g_m+g_a) = -1/3 exactly
    assert result["mean_abs_A"] == pytest.approx(1.0 / 3.0, abs=0.02)
    assert result["chi2_weighted"] > 0
    assert result["dof_weighted"] > 0
    assert 0.0 <= result["pval_weighted"] <= 1.0
    assert result["aalpha_ci_low"] <= result["mean_abs_A"] <= result["aalpha_ci_high"]


def test_chi_squared_from_datasets_n_boot_zero_skips_bootstrap(matter_antimatter_csv_pair):
    m_path, a_path = matter_antimatter_csv_pair
    df_m = pd.read_csv(m_path, header=None, names=["lambda_m", "coupling_abs"])
    df_a = pd.read_csv(a_path, header=None, names=["lambda_m", "coupling_abs"])

    result = chi_squared_from_datasets(df_m, df_a, n_points=50, n_boot=0)
    assert result is not None
    assert np.isnan(result["aalpha_ci_low"])
    assert np.isnan(result["aalpha_ci_high"])


# ── uncertainty_summary ───────────────────────────────────────────────────

def test_uncertainty_summary_skips_none_entries():
    fake_result = {
        "chi2_uniform": 1.0, "chi2_weighted": 2.0,
        "dof_weighted": 10, "dof_effective": 5,
        "autocorr_length": 2.0,
        "pval_uniform": 0.5, "pval_weighted": 0.4, "pval_weighted_eff": 0.3,
        "mean_sigma_m": 0.1, "mean_sigma_a": 0.1,
        "mean_abs_A": 0.2, "aalpha_ci_low": 0.1, "aalpha_ci_high": 0.3,
        "improvement": 0.9,
    }
    rows = uncertainty_summary([None, fake_result, None])
    assert len(rows) == 1
    assert rows[0]["mean_abs_A"] == 0.2


def test_effective_pvalue_rescales_chi2_with_dof():
    # For correlated curves the effective-dof test uses chi2 * dof_eff / n,
    # so it can never come out more significant than the nominal one.
    import pandas as pd
    from src.statistics import chi_squared_from_datasets, significance_from_chi2
    lam = np.logspace(-12, -8, 300)
    df_m = pd.DataFrame({"lambda_m": lam, "coupling_abs": 1e-10 * (lam / 1e-10) ** -0.5})
    df_a = pd.DataFrame({"lambda_m": lam, "coupling_abs": 1.3e-10 * (lam / 1e-10) ** -0.5})
    r = chi_squared_from_datasets(df_m, df_a, n_boot=0)
    n = r["dof_weighted"]
    assert r["chi2_weighted_eff"] == pytest.approx(r["chi2_weighted"] * r["dof_effective"] / n)
    assert r["log10_pval_weighted_eff"] >= np.log10(max(r["pval_weighted"], 1e-300)) - 1e-9


def test_significance_from_chi2_does_not_underflow():
    from src.statistics import significance_from_chi2
    s = significance_from_chi2(5000.0, 6)
    assert s["p_value"] == 0.0 or s["p_value"] < 1e-300
    assert np.isfinite(s["log10_p"]) and s["log10_p"] < -300
    assert s["z"] > 30
    small = significance_from_chi2(12.59, 6)      # ~5% point of chi2(6)
    assert small["p_value"] == pytest.approx(0.05, rel=0.01)
    assert small["z"] == pytest.approx(1.645, abs=0.01)


def test_bootstrap_from_couplings_keeps_saturated_mean_inside_ci():
    # Close to |A| = 1 the interval should still contain the estimate.
    g_m = np.full(50, 1e-15)
    g_a = np.full(50, 1e-11)
    s = np.full(50, 0.2)
    r = bootstrap_aalpha_ci(np.zeros(50), s, n_boot=500, seed=0,
                            g_m=g_m, g_a=g_a, sigma_m=s, sigma_a=s)
    assert r["ci_low"] <= r["mean_aalpha"] <= r["ci_high"]
    assert r["ci_high"] < 1.0
