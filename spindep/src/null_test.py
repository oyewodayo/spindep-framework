"""
null_test.py
============
Synthetic CPT asymmetry injection and recovery framework.

Provides the core logic for the Null Test / Injection feature in the
SPINDEP dashboard. Given an already-analysed AnalysisPair result and a
desired injection level, this module:

  1. Loads the original matter and antimatter datasets from disk.
  2. Applies a synthetic Aα perturbation to the antimatter curve via
     one of three injection modes (scale / replace / shift).
  3. Re-runs the full weighted chi-squared pipeline on the modified data.
  4. Returns a NullTestResult dict suitable for direct JSON serialisation.

Injection modes
---------------
scale   — g_a_new = g_a * (1 - Aα·f(λ))     [most physically motivated]
replace — g_a_new = g_m * (1 - Aα) / (1 + Aα)  [direct replacement at target level]
shift   — g_a_new = g_a * 10^(Aα * log10(g_m/g_a).mean())  [additive log-space offset]

The `seed` parameter controls the optional jitter added to prevent
degenerate recovery on perfectly smooth injections.
"""

from __future__ import annotations

import time
import uuid
import numpy as np
import pandas as pd
from typing import Literal, TypedDict

from .statistics import (
    chi_squared_from_datasets,
    chi_squared_sensitivity,
    estimate_uncertainty,
)


# ─── Types ────────────────────────────────────────────────────────────────────

InjectionMode = Literal["scale", "replace", "shift"]


class NullTestPoint(TypedDict):
    log_lam:          float
    injected_a:       float
    recovered_a:      float
    residual:         float
    within_one_sigma: bool


class NullTestResult(TypedDict):
    job_id:            str
    status:            str
    label:             str
    pair_id:           str
    injected_aalpha:   float
    injection_mode:    str
    seed:              int
    mean_injected:     float
    mean_recovered:    float
    recovery_fraction: float
    chi2_recovered:    float
    chi2_uniform:      float
    dof:               int
    pval_recovered:    float
    pval_uniform:      float
    expected_sigma:    float
    observed_sigma:    float
    calibration_ok:    bool
    points:            list[NullTestPoint]
    log:               list[str]
    elapsed_s:         float


# ─── Sigma ↔ p-value conversion ───────────────────────────────────────────────

def _sigma_from_pval(pval: float) -> float:
    """Approximate one-sided Gaussian sigma from a p-value."""
    from scipy.special import erfinv
    pval = float(np.clip(pval, 1e-15, 1.0 - 1e-15))
    return float(np.sqrt(2) * erfinv(1 - pval))


# ─── Injection functions ──────────────────────────────────────────────────────

def _inject_scale(
    lam: np.ndarray,
    g_m: np.ndarray,
    g_a: np.ndarray,
    aalpha: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Multiply the antimatter curve by (1 − Aα · f(λ)) where f(λ) is a
    smooth envelope that peaks at the centre of the lambda range.
    This is the most physically motivated mode: it produces a
    scale-dependent CPT violation pattern.
    """
    log_lam = np.log10(np.maximum(lam, 1e-40))
    # Smooth Gaussian envelope centred in log-lambda space
    lam_mid = 0.5 * (log_lam.min() + log_lam.max())
    lam_std = 0.4 * (log_lam.max() - log_lam.min())
    envelope = np.exp(-0.5 * ((log_lam - lam_mid) / lam_std) ** 2)
    # Small reproducible jitter prevents degenerate flat injections
    jitter = 1.0 + 0.005 * rng.standard_normal(len(g_a))
    g_a_new = g_a * (1.0 - aalpha * envelope) * jitter
    return g_m, np.maximum(g_a_new, g_a * 0.01)


def _inject_replace(
    lam: np.ndarray,
    g_m: np.ndarray,
    g_a: np.ndarray,
    aalpha: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Construct a synthetic antimatter curve that has exactly Aα asymmetry
    with respect to the matter curve: g_a = g_m · (1 − Aα) / (1 + Aα).
    Small jitter breaks the perfect symmetry so the pipeline isn't trivial.
    """
    ratio = (1.0 - aalpha) / (1.0 + aalpha + 1e-12)
    jitter = 1.0 + 0.005 * rng.standard_normal(len(g_a))
    g_a_new = g_m * ratio * jitter
    return g_m, np.maximum(g_a_new, g_m * 0.001)


def _inject_shift(
    lam: np.ndarray,
    g_m: np.ndarray,
    g_a: np.ndarray,
    aalpha: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Add a constant log-space offset: g_a_new = g_a · 10^(Aα · Δ̄)
    where Δ̄ is the mean log10(g_m / g_a) offset. Models additive
    systematic offsets in log space.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        log_ratio = np.where(
            (g_m > 0) & (g_a > 0),
            np.log10(g_m / g_a),
            0.0,
        )
    mean_offset = float(np.nanmean(log_ratio))
    jitter = 1.0 + 0.005 * rng.standard_normal(len(g_a))
    g_a_new = g_a * (10 ** (aalpha * mean_offset)) * jitter
    return g_m, np.maximum(g_a_new, g_a * 0.01)


_INJECTORS = {
    "scale":   _inject_scale,
    "replace": _inject_replace,
    "shift":   _inject_shift,
}


# ─── Core runner ─────────────────────────────────────────────────────────────

def run_null_test(
    *,
    pair_id:         str,
    df_matter:       pd.DataFrame,
    df_antimatter:   pd.DataFrame,
    injected_aalpha: float,
    injection_mode:  InjectionMode = "scale",
    seed:            int = 42,
    label:           str | None = None,
    n_points:        int = 300,
) -> NullTestResult:
    """
    Run a single null-injection test.

    Parameters
    ----------
    pair_id         : Identifier of the analysis pair being tested.
    df_matter       : DataFrame with columns [lambda_m, coupling_abs]
                      for the matter dataset.
    df_antimatter   : Same schema, antimatter dataset.
    injected_aalpha : Synthetic CPT asymmetry level to inject (0–1).
    injection_mode  : One of "scale" | "replace" | "shift".
    seed            : RNG seed for jitter (same seed → identical result).
    label           : Human-readable label for the run.
    n_points        : Grid resolution for chi-squared computation.

    Returns
    -------
    NullTestResult dict — JSON-serialisable, matches the frontend schema.
    """
    t0  = time.perf_counter()
    log: list[str] = []
    job_id = str(uuid.uuid4())[:12]
    label  = label or f"|Aα|={injected_aalpha:.2f} · {pair_id[:30]} · {injection_mode}"

    log.append(f"[INFO] null_test job_id={job_id}")
    log.append(f"[INFO] pair={pair_id}  Aα={injected_aalpha:.4f}  mode={injection_mode}  seed={seed}")

    # ── 1. Validate inputs ────────────────────────────────────────────────────
    aalpha = float(np.clip(injected_aalpha, 0.0, 1.0))
    rng    = np.random.default_rng(seed)

    lam_m = df_matter["lambda_m"].values.astype(float)
    g_m   = df_matter["coupling_abs"].values.astype(float)
    lam_a = df_antimatter["lambda_m"].values.astype(float)
    g_a   = df_antimatter["coupling_abs"].values.astype(float)

    if len(lam_m) < 3 or len(lam_a) < 3:
        raise ValueError(f"Datasets too short: matter={len(lam_m)}, antimatter={len(lam_a)}")

    log.append(f"[INFO] matter:      {len(lam_m)} pts, λ∈[{lam_m.min():.2e}, {lam_m.max():.2e}]")
    log.append(f"[INFO] antimatter:  {len(lam_a)} pts, λ∈[{lam_a.min():.2e}, {lam_a.max():.2e}]")

    # ── 2. Compute baseline (uninjected) to get expected sigma ────────────────
    baseline = chi_squared_from_datasets(
        df_matter, df_antimatter, n_points=n_points
    )
    if baseline is None:
        raise ValueError("No lambda overlap between matter and antimatter datasets.")

    expected_sigma = _sigma_from_pval(baseline["pval_weighted"])
    log.append(f"[INFO] baseline:    χ²_w={baseline['chi2_weighted']:.1f}  p={baseline['pval_weighted']:.3e}  σ={expected_sigma:.2f}")

    # ── 3. Build common grid over overlap ─────────────────────────────────────
    lam_lo = max(lam_m.min(), lam_a.min())
    lam_hi = min(lam_m.max(), lam_a.max())
    if lam_lo >= lam_hi:
        raise ValueError("No lambda overlap after grid construction.")

    lam_grid = np.logspace(np.log10(lam_lo), np.log10(lam_hi), n_points)

    # Log-linear interpolation onto common grid
    from scipy.interpolate import interp1d

    def log_interp(lam_src, g_src, lam_tgt):
        f = interp1d(
            np.log10(lam_src),
            np.log10(np.maximum(g_src, 1e-300)),
            kind="linear", bounds_error=False, fill_value=np.nan,
        )
        return 10 ** f(np.log10(lam_tgt))

    g_m_grid = log_interp(lam_m, g_m, lam_grid)
    g_a_grid = log_interp(lam_a, g_a, lam_grid)

    valid = np.isfinite(g_m_grid) & np.isfinite(g_a_grid)
    log.append(f"[INFO] grid:        {n_points} pts, {valid.sum()} valid overlap points")

    # ── 4. Inject synthetic asymmetry ─────────────────────────────────────────
    injector = _INJECTORS.get(injection_mode)
    if injector is None:
        raise ValueError(f"Unknown injection_mode: {injection_mode!r}")

    g_m_inj, g_a_inj = injector(lam_grid, g_m_grid, g_a_grid, aalpha, rng)
    log.append(f"[OK]  injection:    mode={injection_mode}  applied to {valid.sum()} points")

    # Compute actual injected Aα per point
    denom_inj = g_m_inj + g_a_inj
    A_injected = np.where(
        (denom_inj > 0) & valid,
        (g_m_inj - g_a_inj) / denom_inj,
        np.nan,
    )
    mean_injected = float(np.nanmean(np.abs(A_injected)))
    log.append(f"[INFO] mean |Aα| injected: {mean_injected:.4f}  (requested: {aalpha:.4f})")

    # ── 5. Re-run chi-squared on injected data ────────────────────────────────
    df_m_inj = pd.DataFrame({"lambda_m": lam_grid[valid], "coupling_abs": g_m_inj[valid]})
    df_a_inj = pd.DataFrame({"lambda_m": lam_grid[valid], "coupling_abs": g_a_inj[valid]})

    recovered = chi_squared_from_datasets(df_m_inj, df_a_inj, n_points=n_points)
    if recovered is None:
        raise RuntimeError("chi_squared_from_datasets returned None on injected data.")

    log.append(f"[OK]  recovered:    χ²_w={recovered['chi2_weighted']:.1f}  p={recovered['pval_weighted']:.3e}")

    # ── 6. Recovered Aα per point ──────────────────────────────────────────────
    g_m_rec = recovered["g_m"]
    g_a_rec = recovered["g_a"]
    lam_rec = recovered["lam_grid"]

    denom_rec  = g_m_rec + g_a_rec
    A_recovered = np.where(denom_rec > 0, (g_m_rec - g_a_rec) / denom_rec, np.nan)
    mean_recovered = float(np.nanmean(np.abs(A_recovered)))

    log.append(f"[INFO] mean |Aα| recovered: {mean_recovered:.4f}")

    # ── 7. Calibration assessment ──────────────────────────────────────────────
    recovery_fraction = mean_recovered / mean_injected if mean_injected > 1e-9 else 0.0
    observed_sigma    = _sigma_from_pval(recovered["pval_weighted"])

    calibration_ok = abs(recovery_fraction - 1.0) < 0.20  # within 20%

    if calibration_ok:
        log.append(f"[OK]  calibration:  recovery={recovery_fraction:.3f}  σ_obs={observed_sigma:.2f}  PASS")
    else:
        log.append(f"[WARN] calibration: recovery={recovery_fraction:.3f}  σ_obs={observed_sigma:.2f}  FAIL")

    # ── 8. Per-point output ────────────────────────────────────────────────────
    # Align injected and recovered onto the same grid for per-point output.
    # recovered["lam_grid"] may differ in length from lam_grid[valid], so
    # interpolate injected Aα onto the recovered grid.
    A_inj_interp_fn = interp1d(
        np.log10(np.maximum(lam_grid[valid], 1e-40)),
        np.where(np.isfinite(A_injected[valid]), A_injected[valid], 0.0),
        kind="linear", bounds_error=False, fill_value=0.0,
    )
    A_inj_on_rec = A_inj_interp_fn(np.log10(np.maximum(lam_rec, 1e-40)))

    sigma_combined = recovered["sigma_combined"]
    points: list[NullTestPoint] = []
    for i, lam_i in enumerate(lam_rec):
        inj_i = float(A_inj_on_rec[i]) if np.isfinite(A_inj_on_rec[i]) else 0.0
        rec_i = float(A_recovered[i])  if np.isfinite(A_recovered[i])  else 0.0
        res_i = rec_i - inj_i
        sig_i = float(sigma_combined[i]) if i < len(sigma_combined) else 0.05
        points.append({
            "log_lam":          float(np.log10(max(lam_i, 1e-40))),
            "injected_a":       abs(inj_i),
            "recovered_a":      abs(rec_i),
            "residual":         res_i,
            "within_one_sigma": abs(res_i) < sig_i,
        })

    elapsed = time.perf_counter() - t0
    log.append(f"[OK]  done in {elapsed:.2f} s")

    return NullTestResult(
        job_id            = job_id,
        status            = "done",
        label             = label,
        pair_id           = pair_id,
        injected_aalpha   = aalpha,
        injection_mode    = injection_mode,
        seed              = seed,
        mean_injected     = mean_injected,
        mean_recovered    = mean_recovered,
        recovery_fraction = recovery_fraction,
        chi2_recovered    = recovered["chi2_weighted"],
        chi2_uniform      = recovered["chi2_uniform"],
        dof               = recovered["dof_weighted"],
        pval_recovered    = recovered["pval_weighted"],
        pval_uniform      = recovered["pval_uniform"],
        expected_sigma    = expected_sigma,
        observed_sigma    = observed_sigma,
        calibration_ok    = calibration_ok,
        points            = points,
        log               = log,
        elapsed_s         = elapsed,
    )