"""
sensitivity_ratio.py
====================
Sensitivity-ratio diagnostic for every matched matter/antimatter pair.

For two one-sided limits on the same coupling, U_f (matter) and U_fbar
(antimatter), the asymmetry A_U = (U_f - U_fbar)/(U_f + U_fbar) only
depends on their ratio. So instead of A_U I look at the ratio directly,

    R(lambda) = U_fbar(lambda) / U_f(lambda),     G(lambda) = |ln R(lambda)|,

on the same 300-point log grid the pipeline uses for A_alpha. R = 1 (G = 0)
means both sectors are probed equally well at that range. A stretch of
lambda where G stays small is a "balanced interval": the only place where a
future likelihood-level CPT comparison of the two sectors can say anything.

Pairs come from matcher.build_pairs() on the analysed datasets, exactly as
in pipeline.py, so this script sees the same 15 pairs as
asymmetry_summary.csv.

Outputs
-------
results/tables/sensitivity_ratio.csv      one row per pair
results/figures/sensitivity_ratio.{png,pdf}

Run from the repo root:
    python scripts/sensitivity_ratio.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Applied inside the plotting functions: importing the spindep modules
# resets matplotlib's style, so setting it at import time does not stick.
STYLE = {
    "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 7,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "mathtext.fontset": "cm", "font.family": "serif",
}

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from spindep.src.parser import discover_datasets, load_dataset          # noqa: E402
from spindep.src.matcher import build_pairs                             # noqa: E402
from spindep.src.statistics import chi_squared_from_datasets            # noqa: E402
from spindep.src.unit_conversion import convert_lambda_to_metres        # noqa: E402
from spindep.src.constraint_plots import drop_excluded_from_analysis    # noqa: E402

# Tolerances for "balanced": within a factor of 2 and within a factor of 10.
FACTORS = (2.0, 10.0)


def balanced_intervals(lam, G, eps):
    """Contiguous lambda ranges where G < eps, as a list of (lo, hi)."""
    inside = G < eps
    out, start = [], None
    for i, flag in enumerate(inside):
        if flag and start is None:
            start = i
        if start is not None and (not flag or i == len(inside) - 1):
            end = i if flag else i - 1
            out.append((lam[start], lam[end]))
            start = None
    return out


def fmt_intervals(intervals):
    return "; ".join(f"[{lo:.2e}, {hi:.2e}]" for lo, hi in intervals)


def analyse_pairs(dataset_root):
    datasets = discover_datasets(dataset_root)
    datasets, _ = drop_excluded_from_analysis(datasets)
    pairs = build_pairs(datasets)

    rows, curves = [], []
    for m, a in pairs:
        df_m, _, _ = convert_lambda_to_metres(load_dataset(m.filepath), m.filename)
        df_a, _, _ = convert_lambda_to_metres(load_dataset(a.filepath), a.filename)
        stats = chi_squared_from_datasets(df_m, df_a, n_points=300, n_boot=0)
        if stats is None:
            continue

        lam, g_m, g_a = stats["lam_grid"], stats["g_m"], stats["g_a"]
        ok = np.isfinite(g_m) & np.isfinite(g_a) & (g_m > 0) & (g_a > 0)
        lam, R = lam[ok], g_a[ok] / g_m[ok]
        G = np.abs(np.log(R))
        i_min = int(np.argmin(G))

        row = {
            "coupling": m.coupling, "potential": m.potential, "sector": m.sector,
            "matter_source": m.source, "antimatter_source": a.source,
            "matter_filename": m.filename, "antimatter_filename": a.filename,
            "mean_abs_A": stats["mean_abs_A"],
            "lambda_min": lam.min(), "lambda_max": lam.max(),
            "median_log10_R": float(np.median(np.log10(R))),
            "median_G": float(np.median(G)),
            "min_G": float(G[i_min]),
            "lambda_at_min_G": float(lam[i_min]),
            # The grid is log-spaced, so these are fractions of the overlap in log(lambda).
            "frac_within_x2": float(np.mean(G < np.log(FACTORS[0]))),
            "frac_within_x10": float(np.mean(G < np.log(FACTORS[1]))),
            "balanced_x2": fmt_intervals(balanced_intervals(lam, G, np.log(FACTORS[0]))),
            "balanced_x10": fmt_intervals(balanced_intervals(lam, G, np.log(FACTORS[1]))),
        }
        rows.append(row)
        curves.append((row, lam, R))
    return pd.DataFrame(rows), curves


def plot_ratios(curves, out_base):
    plt.rcParams.update(STYLE)
    # The compilation files some Fadeev et al. (2022) curves under both gVgV
    # and gpgp, so those two pairs give identical ratios. Draw each distinct
    # ratio curve once and list every coupling it belongs to. The check is on
    # the data, not the file names: the same file name can hold different
    # curves in different coupling folders.
    seen = {}
    for row, lam, R in curves:
        key = (row["sector"], row["potential"], len(R),
               tuple(np.round(np.log10(R[::10]), 6)))
        if key in seen:
            seen[key][0]["coupling"] += "/" + row["coupling"]
        else:
            seen[key] = [dict(row), lam, R]

    # Author names only in the legend; the years in the source tags follow
    # the preprint, which does not always match the journal reference.
    author = {"Cong2025": "Cong", "Karshenboim2010": "Karshenboim", "Karshenboim2011": "Karshenboim", "Ficek2017": "Ficek",
              "Ficek2018": "Ficek", "Fadeev2022": "Fadeev", "Jiao2020": "Jiao",
              "Delaunay2017": "Delaunay", "Adkins2022": "Adkins"}
    pretty = {"gAgA": r"$g_Ag_A$", "gVgV": r"$g_Vg_V$", "gpgp": r"$g_Pg_P$", "gsgs": r"$g_Sg_S$"}
    sector_title = {"ee": r"(a) $e$–$e$ vs $e$–$e^+$", "ep": r"(b) $e$–$p$ vs $e$–$\bar p$"}

    fig, axes = plt.subplots(2, 1, figsize=(7.0, 6.4), sharex=True)
    for ax, sector in zip(axes, ("ee", "ep")):
        ax.axhspan(-np.log10(FACTORS[1]), np.log10(FACTORS[1]), color="0.92", zorder=0)
        ax.axhspan(-np.log10(FACTORS[0]), np.log10(FACTORS[0]), color="0.80", zorder=0)
        ax.axhline(0, color="k", lw=0.8)
        entries = [v for v in seen.values() if v[0]["sector"] == sector]
        entries.sort(key=lambda v: -v[0]["mean_abs_A"])
        for row, lam, R in entries:
            couplings = "/".join(pretty.get(c, c) for c in row["coupling"].split("/"))
            label = (f"{couplings} ${row['potential'].replace('V', 'V_{')}}}$, "
                     f"{author.get(row['matter_source'], row['matter_source'])} / "
                     f"{author.get(row['antimatter_source'], row['antimatter_source'])}")
            # A few curves sit on top of each other (the same spectroscopy
            # gives nearly the same ratio for every coupling), so non-axial
            # couplings are dashed to keep both visible.
            ls = "-" if row["coupling"].startswith("gAgA") else "--"
            ax.plot(lam, np.log10(R), lw=1.5, ls=ls, label=label)
        ax.set_xscale("log")
        ax.set_ylabel(r"$\log_{10} R_\alpha = \log_{10}(U_{\bar f}/U_f)$")
        ax.set_title(sector_title[sector], loc="left", fontsize=10)
        ax.legend(fontsize=7, loc="best", frameon=False)
        ax.grid(alpha=0.3, which="major")
    axes[-1].set_xlabel(r"Interaction range $\lambda$ (m)")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_base}.{ext}", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    dataset_root = REPO / "spindep" / "datasets" / "normalized"
    table, curves = analyse_pairs(dataset_root)

    tables_dir = REPO / "results" / "tables"
    figures_dir = REPO / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    table = table.sort_values("mean_abs_A", ascending=False)
    table.to_csv(tables_dir / "sensitivity_ratio.csv", index=False)
    plot_ratios(curves, figures_dir / "sensitivity_ratio")

    cols = ["coupling", "potential", "sector", "matter_source", "antimatter_source",
            "mean_abs_A", "median_G", "min_G", "lambda_at_min_G",
            "frac_within_x2", "frac_within_x10"]
    print(table[cols].to_string(index=False, float_format=lambda x: f"{x:.3g}"))
    print("\nBalanced within a factor of 2:")
    for _, r in table[table.balanced_x2 != ""].iterrows():
        print(f"  {r.coupling} {r.potential} {r.sector} {r.matter_source}/{r.antimatter_source}: {r.balanced_x2}")
