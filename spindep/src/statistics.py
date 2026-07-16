"""
statistics.py
=============
Statistical tests for matter-antimatter CPT consistency.

Additions over v1.0
-------------------
A. Bootstrap confidence intervals on mean |Aα|
   bootstrap_aalpha_ci(A, sigma_combined, n_boot, ci_level)
   Returns (mean, lower, upper) — ready for report and publication.

B. Effective degrees of freedom correction
   effective_dof(residuals, lam_grid)
   Estimates dof_eff using the autocorrelation length of chi-squared
   residuals on the log-spaced lambda grid. Prevents over-stating
   significance when adjacent interpolated points are correlated.

Both are integrated into chi_squared_from_datasets() return dict
via new keys:
   aalpha_ci_low, aalpha_ci_high   (bootstrap 95% CI bounds)
   dof_effective                    (autocorrelation-corrected dof)
   pval_weighted_eff                (p-value using dof_effective)
   autocorr_length                  (for transparency in reports)

Existing behaviour is unchanged — all original keys still present.
"""

import numpy as np
from scipy.stats import chi2 as chi2_dist
from scipy.interpolate import interp1d


# ============================================================
# 1. ORIGINAL UNIFORM CHI-SQUARED (backward compatible)
# ============================================================

def chi_squared_sensitivity(g_m, g_a, sigma_frac=0.1):
    """
    Chi-squared test with uniform fractional uncertainty.
    Returns chi2_total, dof, p_value.
    """
    g_m = np.asarray(g_m, dtype=float)
    g_a = np.asarray(g_a, dtype=float)

    sigma_sq   = (sigma_frac * (g_m + g_a) / 2) ** 2
    chi2_vals  = (g_m - g_a) ** 2 / sigma_sq
    chi2_total = float(np.nansum(chi2_vals))
    dof        = int(np.sum(np.isfinite(chi2_vals)))
    p_value    = 1.0 - chi2_dist.cdf(chi2_total, df=dof)

    return chi2_total, dof, p_value


# ============================================================
# 2. UNCERTAINTY ESTIMATION FROM CURVE SMOOTHNESS
# ============================================================

def estimate_uncertainty(lam, g, min_frac=0.02, max_frac=0.50,
                         baseline_frac=0.05):
    """
    Estimate per-point fractional uncertainty from log-log curvature.
    Returns sigma_frac array (same length as lam).
    """
    lam = np.asarray(lam, dtype=float)
    g   = np.asarray(g,   dtype=float)

    if len(lam) < 3:
        return np.full(len(lam), baseline_frac)

    log_lam   = np.log10(np.maximum(lam, 1e-40))
    log_g     = np.log10(np.maximum(g,   1e-40))
    curvature = np.zeros(len(lam))

    for i in range(1, len(lam) - 1):
        dlam_fwd = log_lam[i+1] - log_lam[i]
        dlam_bwd = log_lam[i]   - log_lam[i-1]
        dg_fwd   = log_g[i+1]   - log_g[i]
        dg_bwd   = log_g[i]     - log_g[i-1]
        if dlam_fwd > 0 and dlam_bwd > 0:
            d2 = (dg_fwd / dlam_fwd - dg_bwd / dlam_bwd) / \
                 (0.5 * (dlam_fwd + dlam_bwd))
            curvature[i] = abs(d2)

    curvature[0]  = curvature[1]  if len(curvature) > 1 else 0.0
    curvature[-1] = curvature[-2] if len(curvature) > 1 else 0.0

    c_max = np.percentile(curvature[curvature > 0], 95) \
            if np.any(curvature > 0) else 1.0
    c_max = max(c_max, 1e-10)

    sigma_frac = baseline_frac + \
        (max_frac - baseline_frac) * np.clip(curvature / c_max, 0, 1)
    sigma_frac = np.clip(sigma_frac, min_frac, max_frac)

    return sigma_frac


# ============================================================
# 3. WEIGHTED CHI-SQUARED
# ============================================================

def chi_squared_weighted(g_m, g_a, sigma_m, sigma_a):
    """
    Weighted chi-squared using per-point uncertainties.

        chi2_i = (g_m_i - g_a_i)^2 / (sigma_m_i^2 + sigma_a_i^2)

    Returns chi2_total, dof, p_value, sigma_combined.
    """
    g_m     = np.asarray(g_m,     dtype=float)
    g_a     = np.asarray(g_a,     dtype=float)
    sigma_m = np.asarray(sigma_m, dtype=float)
    sigma_a = np.asarray(sigma_a, dtype=float)

    abs_sigma_m  = sigma_m * g_m
    abs_sigma_a  = sigma_a * g_a
    combined_var = abs_sigma_m ** 2 + abs_sigma_a ** 2

    valid = np.isfinite(g_m) & np.isfinite(g_a) & (combined_var > 0)

    chi2_vals = np.where(
        valid,
        (g_m - g_a) ** 2 / np.where(combined_var > 0, combined_var, 1.0),
        np.nan,
    )

    chi2_total = float(np.nansum(chi2_vals))
    dof        = int(np.sum(valid))
    p_value    = 1.0 - chi2_dist.cdf(chi2_total, df=max(dof, 1))

    return chi2_total, dof, p_value, np.sqrt(combined_var)


# ============================================================
# 4A. EFFECTIVE DEGREES OF FREEDOM
# ============================================================

def effective_dof(residuals: np.ndarray, lam_grid: np.ndarray) -> dict:
    """
    Estimate the effective degrees of freedom by measuring the
    autocorrelation length of the chi-squared residuals in log-lambda
    space, then applying the standard correction:

        dof_eff = n / autocorr_length

    where n is the number of valid points and autocorr_length is the
    number of consecutive points over which residuals remain correlated
    (defined as the lag at which the normalised autocorrelation first
    drops below 1/e).

    This is the Thiébaux & Zwiers (1984) method adapted to log-spaced
    grids: the autocorrelation is computed in grid-index space, which
    is uniform, so no resampling is needed.

    Parameters
    ----------
    residuals : array — per-point chi2_i values (may contain NaN)
    lam_grid  : array — corresponding lambda values (for logging)

    Returns
    -------
    dict with keys:
        dof_effective  : int
        autocorr_length: float (in grid points)
        n_valid        : int
    """
    finite = np.isfinite(residuals)
    r      = residuals[finite].astype(float)
    n      = len(r)

    if n < 4:
        return {"dof_effective": n, "autocorr_length": 1.0, "n_valid": n}

    # Mean-centre residuals
    r_c = r - r.mean()

    # Normalised autocorrelation at lags 0..min(n//2, 50)
    max_lag   = min(n // 2, 50)
    acf       = np.array([
        float(np.dot(r_c[:n-k], r_c[k:]) / (np.dot(r_c, r_c) + 1e-30))
        for k in range(max_lag + 1)
    ])

    # Autocorrelation length: first lag where acf < 1/e
    threshold  = 1.0 / np.e
    below      = np.where(acf < threshold)[0]
    tau        = float(below[0]) if len(below) > 0 else float(max_lag)
    tau        = max(tau, 1.0)   # never less than 1

    dof_eff    = max(1, int(round(n / tau)))

    return {
        "dof_effective":   dof_eff,
        "autocorr_length": tau,
        "n_valid":         n,
    }


# ============================================================
# 4B. BOOTSTRAP CONFIDENCE INTERVAL ON MEAN |Aα|
# ============================================================

def bootstrap_aalpha_ci(
    A:             np.ndarray,
    sigma_combined: np.ndarray,
    n_boot:        int   = 2000,
    ci_level:      float = 0.95,
    seed:          int   = 0,
) -> dict:
    """
    Parametric bootstrap confidence interval on mean |Aα|.

    At each bootstrap iteration:
      1. Perturb each coupling pair (g_m_i, g_a_i) by drawing from
         N(0, sigma_combined_i) independently for matter and antimatter.
      2. Recompute Aα_i = (g_m_i - g_a_i) / (g_m_i + g_a_i).
      3. Record mean |Aα|.

    Since we don't store per-point (g_m, g_a) here — only A and sigma —
    we use the delta-method approximation:

        A_perturbed_i ≈ A_i + dA/dg_m * δ_m + dA/dg_a * δ_a

    For A = (g_m - g_a)/(g_m + g_a):
        dA/dg_m =  2*g_a / (g_m + g_a)^2  ≈  (1 - A^2) / 2  (if g_m≈g_a)
        dA/dg_a = -2*g_m / (g_m + g_a)^2  ≈ -(1 - A^2) / 2

    The per-point propagated uncertainty on Aα is approximately:
        sigma_A_i ≈ sigma_combined_i / (g_m + g_a) ≈ sigma_combined_i * (1 - A_i^2) / (2 * g_ref)

    Since g_ref cancels when normalised, we use the simpler bound:
        sigma_A_i = 0.5 * sigma_frac_combined * (1 - A_i^2)

    where sigma_frac_combined is the fractional uncertainty on the
    coupling ratio. We approximate sigma_frac_combined ≈ sigma_combined
    (already fractional from the curvature model).

    Parameters
    ----------
    A              : array — per-point Aα values (may contain NaN)
    sigma_combined : array — combined absolute uncertainty per point
                     (as fraction, from chi_squared_weighted)
    n_boot         : int — bootstrap iterations (2000 is sufficient)
    ci_level       : float — e.g. 0.95 for 95% CI
    seed           : int — RNG seed for reproducibility

    Returns
    -------
    dict with keys:
        mean_aalpha     : float — point estimate of mean |Aα|
        ci_low          : float — lower CI bound
        ci_high         : float — upper CI bound
        ci_level        : float — e.g. 0.95
        n_boot          : int
        std_aalpha      : float — bootstrap standard deviation
    """
    rng    = np.random.default_rng(seed)
    valid  = np.isfinite(A) & np.isfinite(sigma_combined)
    A_v    = np.abs(A[valid])
    sig_v  = sigma_combined[valid]

    if len(A_v) == 0:
        return {
            "mean_aalpha": 0.0, "ci_low": 0.0, "ci_high": 0.0,
            "ci_level": ci_level, "n_boot": n_boot, "std_aalpha": 0.0,
        }

    # Propagated uncertainty on |Aα| per point
    # sigma_A_i ≈ sigma_combined_i * (1 - A_i^2) / 2
    # Clamp so perturbation never flips sign past ±1
    sigma_A = np.clip(sig_v * (1.0 - A_v ** 2) / 2.0, 0.001, 0.5)

    boot_means = np.empty(n_boot)
    for b in range(n_boot):
        noise = rng.standard_normal(len(A_v)) * sigma_A
        A_boot = np.clip(np.abs(A_v + noise), 0.0, 1.0)
        boot_means[b] = float(np.mean(A_boot))

    alpha   = 1.0 - ci_level
    ci_low  = float(np.percentile(boot_means, 100 * alpha / 2))
    ci_high = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))

    return {
        "mean_aalpha": float(np.mean(A_v)),
        "ci_low":      ci_low,
        "ci_high":     ci_high,
        "ci_level":    ci_level,
        "n_boot":      n_boot,
        "std_aalpha":  float(np.std(boot_means)),
    }


# ============================================================
# 5. FULL PIPELINE: DATASET → WEIGHTED CHI-SQUARED
# ============================================================

def chi_squared_from_datasets(df_m, df_a, lam_grid=None, n_points=300,
                               n_boot=2000, ci_level=0.95):
    """
    Full weighted chi-squared pipeline from raw DataFrames.

    Steps:
      1. Determine overlapping lambda range
      2. Build common log-spaced grid
      3. Log-linear interpolation of both curves onto grid
      4. Estimate per-point uncertainties from curvature
      5. Compute weighted chi-squared
      6. Effective DOF correction          ← NEW
      7. Bootstrap CI on mean |Aα|         ← NEW

    Parameters
    ----------
    df_m, df_a : pd.DataFrame with columns [lambda_m, coupling_abs]
    lam_grid   : optional pre-computed lambda grid
    n_points   : grid resolution if lam_grid not provided
    n_boot     : bootstrap iterations for CI (set 0 to skip)
    ci_level   : confidence level for bootstrap CI

    Returns
    -------
    result : dict — all original keys plus:
        dof_effective      : int   — autocorrelation-corrected dof
        pval_weighted_eff  : float — p-value using dof_effective
        autocorr_length    : float — in grid points
        aalpha_ci_low      : float — lower 95% CI on mean |Aα|
        aalpha_ci_high     : float — upper 95% CI on mean |Aα|
        aalpha_ci_level    : float — CI level used
        aalpha_std         : float — bootstrap std of mean |Aα|
    """
    lam_m   = df_m["lambda_m"].values
    g_m_raw = df_m["coupling_abs"].values
    lam_a   = df_a["lambda_m"].values
    g_a_raw = df_a["coupling_abs"].values

    # 1. Overlap range
    lam_min = max(lam_m.min(), lam_a.min())
    lam_max = min(lam_m.max(), lam_a.max())
    if lam_min >= lam_max:
        return None

    # 2. Common grid
    if lam_grid is None:
        lam_grid = np.logspace(
            np.log10(lam_min), np.log10(lam_max), n_points
        )

    # 3. Log-linear interpolation
    def log_interp(lam_src, g_src, lam_tgt):
        f = interp1d(
            np.log10(lam_src),
            np.log10(np.maximum(g_src, 1e-300)),
            kind="linear", bounds_error=False, fill_value=np.nan,
        )
        return 10 ** f(np.log10(lam_tgt))

    g_m = log_interp(lam_m, g_m_raw, lam_grid)
    g_a = log_interp(lam_a, g_a_raw, lam_grid)

    valid = np.isfinite(g_m) & np.isfinite(g_a)
    if not np.any(valid):
        return None

    # 4. Per-point uncertainties
    sigma_frac_m_dense = estimate_uncertainty(lam_m, g_m_raw)
    sigma_frac_a_dense = estimate_uncertainty(lam_a, g_a_raw)

    sigma_frac_m = log_interp(lam_m, sigma_frac_m_dense, lam_grid)
    sigma_frac_a = log_interp(lam_a, sigma_frac_a_dense, lam_grid)

    sigma_frac_m = np.where(np.isfinite(sigma_frac_m), sigma_frac_m, 0.10)
    sigma_frac_a = np.where(np.isfinite(sigma_frac_a), sigma_frac_a, 0.10)
    sigma_frac_m = np.clip(sigma_frac_m, 0.02, 0.50)
    sigma_frac_a = np.clip(sigma_frac_a, 0.02, 0.50)

    # 5. Chi-squared — both versions
    chi2_u, dof_u, pval_u = chi_squared_sensitivity(
        g_m[valid], g_a[valid], sigma_frac=0.10
    )
    chi2_w, dof_w, pval_w, sigma_combined = chi_squared_weighted(
        g_m[valid], g_a[valid],
        sigma_frac_m[valid], sigma_frac_a[valid],
    )

    # Asymmetry parameter
    denom  = g_m + g_a
    A      = np.where(denom > 0, (g_m - g_a) / denom, np.nan)
    mean_abs_A = float(np.nanmean(np.abs(A)))

    # ── 6. Effective DOF ──────────────────────────────────────────────
    # Compute per-point chi2 residuals for autocorrelation analysis
    abs_sigma_m_v  = sigma_frac_m[valid] * g_m[valid]
    abs_sigma_a_v  = sigma_frac_a[valid] * g_a[valid]
    combined_var_v = abs_sigma_m_v**2 + abs_sigma_a_v**2
    chi2_per_point = np.where(
        combined_var_v > 0,
        (g_m[valid] - g_a[valid])**2 / combined_var_v,
        np.nan,
    )

    eff_dof_info   = effective_dof(chi2_per_point, lam_grid[valid])
    dof_eff        = eff_dof_info["dof_effective"]
    autocorr_len   = eff_dof_info["autocorr_length"]
    pval_w_eff     = float(1.0 - chi2_dist.cdf(chi2_w, df=max(dof_eff, 1)))

    # ── 7. Bootstrap CI on mean |Aα| ─────────────────────────────────
    # Build full-grid sigma_combined (valid points only → pad with NaN)
    sigma_combined_full = np.full(len(lam_grid), np.nan)
    sigma_combined_full[valid] = sigma_combined

    if n_boot > 0:
        ci_info = bootstrap_aalpha_ci(
            A, sigma_combined_full,
            n_boot=n_boot, ci_level=ci_level,
        )
    else:
        ci_info = {
            "mean_aalpha": mean_abs_A, "ci_low": np.nan,
            "ci_high": np.nan, "ci_level": ci_level,
            "n_boot": 0, "std_aalpha": np.nan,
        }

    return {
        # ── Original keys (unchanged) ─────────────────────────
        "lam_grid":         lam_grid,
        "g_m":              g_m,
        "g_a":              g_a,
        "A_alpha":          A,
        "sigma_frac_m":     sigma_frac_m,
        "sigma_frac_a":     sigma_frac_a,
        "sigma_combined":   sigma_combined_full,
        "chi2_uniform":     chi2_u,
        "chi2_weighted":    chi2_w,
        "dof_uniform":      dof_u,
        "dof_weighted":     dof_w,
        "pval_uniform":     pval_u,
        "pval_weighted":    pval_w,
        "mean_abs_A":       mean_abs_A,
        "mean_sigma_m":     float(np.nanmean(sigma_frac_m[valid])),
        "mean_sigma_a":     float(np.nanmean(sigma_frac_a[valid])),
        "improvement":      chi2_w / chi2_u if chi2_u > 0 else 1.0,
        # ── New: effective DOF ────────────────────────────────
        "dof_effective":    dof_eff,
        "pval_weighted_eff":pval_w_eff,
        "autocorr_length":  autocorr_len,
        # ── New: bootstrap CI ─────────────────────────────────
        "aalpha_ci_low":    ci_info["ci_low"],
        "aalpha_ci_high":   ci_info["ci_high"],
        "aalpha_ci_level":  ci_level,
        "aalpha_std":       ci_info["std_aalpha"],
    }


# ============================================================
# 6. UNCERTAINTY SUMMARY TABLE
# ============================================================

def uncertainty_summary(results_list):
    rows = []
    for r in results_list:
        if r is None:
            continue
        rows.append({
            "chi2_uniform":      r["chi2_uniform"],
            "chi2_weighted":     r["chi2_weighted"],
            "dof_nominal":       r["dof_weighted"],
            "dof_effective":     r.get("dof_effective", r["dof_weighted"]),
            "autocorr_length":   round(r.get("autocorr_length", 1.0), 2),
            "pval_uniform":      r["pval_uniform"],
            "pval_weighted":     r["pval_weighted"],
            "pval_weighted_eff": r.get("pval_weighted_eff", r["pval_weighted"]),
            "mean_sigma_m_%":    round(r["mean_sigma_m"] * 100, 1),
            "mean_sigma_a_%":    round(r["mean_sigma_a"] * 100, 1),
            "mean_abs_A":        round(r["mean_abs_A"], 4),
            "aalpha_ci_low":     round(r.get("aalpha_ci_low",  0.0), 4),
            "aalpha_ci_high":    round(r.get("aalpha_ci_high", 0.0), 4),
            "chi2_ratio_w/u":    round(r["improvement"], 3),
        })
    return rows


# ============================================================
# SELF-TEST
# ============================================================

if __name__ == "__main__":
    import pandas as pd

    print("=== statistics.py self-test (v2 — CI + effective DOF) ===\n")

    lam   = np.logspace(-12, -8, 300)
    g_m   = 1e-10 * (lam / 1e-10) ** (-0.5)
    g_a   = 1e-8  * (lam / 1e-10) ** (-0.5)

    df_m  = pd.DataFrame({"lambda_m": lam, "coupling_abs": g_m})
    df_a  = pd.DataFrame({"lambda_m": lam, "coupling_abs": g_a})

    result = chi_squared_from_datasets(df_m, df_a, n_boot=500)
    if result is None:
        raise ValueError("chi_squared_from_datasets returned None")

    print(f"Uniform  chi2: {result['chi2_uniform']:.1f}  "
          f"(dof={result['dof_uniform']})  p={result['pval_uniform']:.3e}")
    print(f"Weighted chi2: {result['chi2_weighted']:.1f}  "
          f"(dof_nominal={result['dof_weighted']})  p={result['pval_weighted']:.3e}")
    print(f"Effective DOF: {result['dof_effective']}  "
          f"(autocorr_length={result['autocorr_length']:.1f} pts)  "
          f"p_eff={result['pval_weighted_eff']:.3e}")
    print(f"Mean |Aα|:     {result['mean_abs_A']:.4f}  "
          f"95% CI [{result['aalpha_ci_low']:.4f}, {result['aalpha_ci_high']:.4f}]  "
          f"std={result['aalpha_std']:.4f}")
    print(f"\nSelf-test complete.")