from datetime import datetime
from pathlib import Path
from dataclasses import asdict
import json

import pandas as pd
import numpy as np

from .parser import discover_datasets, load_dataset
from .matcher import build_pairs
from .statistics import (
    chi_squared_sensitivity,
    chi_squared_from_datasets,
)
from .plotting import plot_asymmetry
from .reporting import generate_report
from .unit_conversion import convert_lambda_to_metres, audit_units, classify_scale_regime
from .gap_analysis import run_gap_analysis
from .constraint_plots import run_constraint_plots, drop_excluded_from_analysis


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _portable_path(filepath, dataset_root):
    """
    Path of a dataset relative to the repo, or to the dataset folder if it
    lives outside the repo, or just its file name as a last resort.

    The registry is committed to GitHub, so an absolute path would only
    publish my local folder layout (/home/user/...) and would mean nothing
    on anyone else's machine.
    """
    p = Path(filepath).resolve()
    for base in (_REPO_ROOT, Path(dataset_root).resolve()):
        try:
            return p.relative_to(base).as_posix()
        except ValueError:
            continue
    return p.name


def run_pipeline(dataset_root, results_root, json_out=None):

    dataset_root = Path(dataset_root)
    results_root = Path(results_root)

    plots_dir   = results_root / "plots"
    tables_dir  = results_root / "tables"
    reports_dir = results_root / "reports"
    figures_dir = results_root / "figures"

    for d in [plots_dir, tables_dir, reports_dir, figures_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # DISCOVER DATASETS
    # --------------------------------------------------------
    print("=" * 60)
    print("DISCOVERING DATASETS")
    print("=" * 60)

    datasets = discover_datasets(dataset_root)
    for d in datasets:
        if "bar" in d.filename.lower() or "bare" in d.filename.lower():
            print(f"  {d.filename:50s} → sector={d.sector!r:12s}  antimatter={d.contains_antimatter}")
    print(f"Found {len(datasets)} datasets")

    # --------------------------------------------------------
    # UNIT AUDIT
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("UNIT AUDIT")
    print("=" * 60)
    audit_units(datasets, verbose=True)

    # --------------------------------------------------------
    # SCALE REGIME (microscopic / macroscopic / mixed)
    # --------------------------------------------------------
    for d in datasets:
        try:
            df = load_dataset(d.filepath)
            df, _, _ = convert_lambda_to_metres(df, d.filename)
            d.scale_regime = classify_scale_regime(df["lambda_m"])
        except Exception as e:
            print(f"[WARN] Could not classify scale regime for {d.filename}: {e}")
            d.scale_regime = "UNKNOWN"

    # --------------------------------------------------------
    # HOLD EXCLUDED DATASETS OUT OF THE ANALYSIS
    # --------------------------------------------------------
    # The registry below records every compiled dataset, excluded ones
    # included, so the count of what was gathered stays auditable. Only
    # `datasets` -- the kept half -- reaches gap analysis, the atlas,
    # pair matching and the asymmetry figures.
    print("\n" + "=" * 60)
    print("EXCLUSIONS")
    print("=" * 60)
    datasets, excluded = drop_excluded_from_analysis(datasets)
    print(f"Compiled {len(datasets) + len(excluded)} | "
          f"excluded {len(excluded)} | analysing {len(datasets)}")

    # --------------------------------------------------------
    # EXPORT REGISTRY  (all compiled datasets, excluded flagged)
    # --------------------------------------------------------
    registry = pd.DataFrame([asdict(d) for d in datasets + excluded])
    # Make the paths portable before writing; see _portable_path().
    registry["filepath"] = registry["filepath"].map(
        lambda fp: _portable_path(fp, dataset_root)
    )
    registry["excluded"] = registry["excluded_reason"] != ""
    registry = registry.sort_values(
        ["excluded", "coupling", "potential", "filename"]
    )
    registry.to_csv(tables_dir / "dataset_registry.csv", index=False)

    # --------------------------------------------------------
    # GAP ANALYSIS
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("GAP ANALYSIS")
    print("=" * 60)
    run_gap_analysis(datasets, figures_dir=figures_dir)

    # --------------------------------------------------------
    # CONSTRAINT ATLAS (all datasets, not just valid pairs)
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("CONSTRAINT ATLAS")
    print("=" * 60)
    run_constraint_plots(
        datasets=datasets,
        summary_rows=[],
        plots_dir=plots_dir,
        figures_dir=figures_dir,
    )

    # --------------------------------------------------------
    # BUILD MATCHED PAIRS
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("MATCHING PAIRS")
    print("=" * 60)
    pairs = build_pairs(datasets)
    print(f"\nFound {len(pairs)} valid pairs")

    # --------------------------------------------------------
    # ANALYSIS LOOP
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("COMPUTING CHI2 & ASYMMETRY")
    print("=" * 60)
    summary_rows = []
    gui_pairs    = []

    for matter_ds, antimatter_ds in pairs:

        print("-" * 50)
        print(matter_ds.filename)
        print(antimatter_ds.filename)

        # Load + convert units
        df_m = load_dataset(matter_ds.filepath)
        df_a = load_dataset(antimatter_ds.filepath)

        df_m, _, unit_m = convert_lambda_to_metres(df_m, matter_ds.filename,     verbose=True)
        df_a, _, unit_a = convert_lambda_to_metres(df_a, antimatter_ds.filename,  verbose=True)

        # --------------------------------------------------
        # WEIGHTED CHI-SQUARED (uses per-point uncertainties)
        # --------------------------------------------------
        stats = chi_squared_from_datasets(df_m, df_a, n_points=300)

        if stats is None:
            print(f"  [SKIP] No overlapping lambda range")
            continue

        lam  = stats["lam_grid"]
        A    = stats["A_alpha"]
        g_m  = stats["g_m"]
        g_a  = stats["g_a"]

        valid = np.isfinite(g_m) & np.isfinite(g_a)

        chi2_u     = stats["chi2_uniform"]
        chi2_w     = stats["chi2_weighted"]
        dof_w      = stats["dof_weighted"]
        pval_u     = stats["pval_uniform"]
        pval_w     = stats["pval_weighted"]
        mean_A     = stats["mean_abs_A"]
        sigma_m    = stats["mean_sigma_m"]
        sigma_a    = stats["mean_sigma_a"]
        dof_eff    = stats["dof_effective"]
        pval_w_eff = stats["pval_weighted_eff"]
        chi2_w_eff = stats["chi2_weighted_eff"]
        log10p_eff = stats["log10_pval_weighted_eff"]
        z_eff      = stats["z_weighted_eff"]
        autocorr   = stats["autocorr_length"]
        ci_low     = stats["aalpha_ci_low"]
        ci_high    = stats["aalpha_ci_high"]

        # --------------------------------------------------
        # BUILD GUI PAYLOAD (downsample for browser)
        # --------------------------------------------------
        lam_valid = lam[valid]
        g_m_valid = g_m[valid]
        g_a_valid = g_a[valid]
        A_valid   = A[valid]

        step = max(1, len(lam_valid) // 60)  # ~60 points per curve

        gui_pairs.append({
            "id":           f"{matter_ds.coupling}·{matter_ds.potential}·{matter_ds.sector}×{antimatter_ds.sector}",
            "coupling":     matter_ds.coupling,
            "potential":    matter_ds.potential,
            "secM":         matter_ds.sector,
            "secA":         antimatter_ds.sector,
            "experiment_m": matter_ds.source,
            "experiment_a": antimatter_ds.source,
            "meanAbsA":     float(mean_A),
            "chi2Weighted": float(chi2_w),
            "chi2Uniform":  float(chi2_u),
            "dof":          int(dof_w),
            "pval":         float(pval_w),
            "dofEffective": int(dof_eff),
            "pvalEffective":float(pval_w_eff),
            "log10PvalEffective": float(log10p_eff),
            "zEffective":   float(z_eff),
            "autocorrLength": float(autocorr),
            "aalphaCiLow":  float(ci_low),
            "aalphaCiHigh": float(ci_high),
            "sigmaM":       float(sigma_m * 100),
            "sigmaA":       float(sigma_a * 100),
            "lambdaMin":    float(lam_valid.min()),
            "lambdaMax":    float(lam_valid.max()),
            "improvement":  float(chi2_w / chi2_u if chi2_u > 0 else 1.0),
            "points": [
                {
                    "logLam": float(np.log10(lam_valid[i])),
                    "logGm":  float(np.log10(g_m_valid[i])) if g_m_valid[i] > 0 else -30.0,
                    "logGa":  float(np.log10(g_a_valid[i])) if g_a_valid[i] > 0 else -30.0,
                    "A":      float(A_valid[i]),
                }
                for i in range(0, len(lam_valid), step)
            ],
        })

        # --------------------------------------------------
        # SAVE PLOT
        # --------------------------------------------------
        plot_name = (
            f"{matter_ds.coupling}_{matter_ds.potential}_"
            f"{matter_ds.sector}_{matter_ds.filename}.png"
        )
        plot_path = plots_dir / plot_name

        try:
            plot_asymmetry(lam[valid], A[valid], g_m[valid], g_a[valid],
                           matter_ds, antimatter_ds, plot_path)
        except Exception as e:
            print(f"  [PLOT ERROR] {e}")
            continue

        # --------------------------------------------------
        # SUMMARY
        # --------------------------------------------------
        summary_rows.append({
            "coupling":            matter_ds.coupling,
            "potential":           matter_ds.potential,
            "interaction_class":   matter_ds.interaction_class,
            "sector":              matter_ds.sector,
            "matter_source":       matter_ds.source,
            "matter_filename":     matter_ds.filename,
            "matter_unit":         unit_m,
            "antimatter_source":   antimatter_ds.source,
            "antimatter_unit":     unit_a,
            "mean_abs_A":          mean_A,
            "chi2_uniform":        chi2_u,
            "dof":                 dof_w,
            "p_value_uniform":     pval_u,
            "chi2_weighted":       chi2_w,
            "p_value_weighted":    pval_w,
            "dof_effective":       dof_eff,
            "p_value_weighted_eff":pval_w_eff,
            "chi2_weighted_eff":   chi2_w_eff,
            "log10_p_value_weighted_eff": log10p_eff,
            "z_weighted_eff":      z_eff,
            "autocorr_length":     round(autocorr, 2),
            "aalpha_ci_low":       round(ci_low, 4),
            "aalpha_ci_high":      round(ci_high, 4),
            "mean_sigma_m_pct":    round(sigma_m * 100, 1),
            "mean_sigma_a_pct":    round(sigma_a * 100, 1),
            "chi2_ratio":          round(chi2_w / chi2_u if chi2_u > 0 else 1.0, 3),
            "lambda_min":          float(lam[valid].min()),
            "lambda_max":          float(lam[valid].max()),
        })

        print(f"  chi2_uniform={chi2_u:.1f}  chi2_weighted={chi2_w:.1f}  "
              f"|A|={mean_A:.3f}  sigma_m={sigma_m*100:.1f}%  sigma_a={sigma_a*100:.1f}%")
        print(f"  dof_effective={dof_eff}  chi2_eff={chi2_w_eff:.1f}  "
              f"log10(p_eff)={log10p_eff:.1f}  Z={z_eff:.1f}  "
              f"(autocorr_length={autocorr:.1f} pts)")

    # --------------------------------------------------------
    # EXPORT SUMMARY CSV
    # --------------------------------------------------------
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(tables_dir / "asymmetry_summary.csv", index=False)

    # --------------------------------------------------------
    # EXPORT GUI JSON
    # --------------------------------------------------------
    if json_out and gui_pairs:
        json_path = Path(json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump({"pairs": gui_pairs}, f)
        print(f"\n[GUI] JSON written → {json_path}  ({len(gui_pairs)} pairs)")
    elif json_out and not gui_pairs:
        print(f"\n[GUI] --output-json requested but no valid pairs to export.")

    # --------------------------------------------------------
    # COMPARISON PLOTS
    # --------------------------------------------------------
    if summary_rows:
        from .constraint_plots import plot_matter_antimatter_comparison
        plot_matter_antimatter_comparison(
            summary_rows=summary_rows,
            plots_dir=plots_dir,
            output_dir=figures_dir / "matter_antimatter",
        )

    print("=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)

    # --------------------------------------------------------
    # GENERATE REPORT
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("GENERATING REPORT")
    print("=" * 60)
    if summary_rows:
        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"asymmetry_report_{timestamp}.pdf"
        generate_report(
            summary_rows=summary_rows,
            plots_dir=plots_dir,
            output_path=report_path,
        )