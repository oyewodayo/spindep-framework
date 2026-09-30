"""
paper_figures.py
================
Journal versions of two figures in the paper, drawn straight from the
registry so the numbers match the tables exactly.

  pair_bounds.{png,pdf}      the published bounds for the highest- and the
                             lowest-asymmetry matched pairs, on their
                             overlapping range
  coverage_matrix.{png,pdf}  analysed records by potential label and fermion
                             sector, antimatter sectors marked

The pipeline's own figures (results/figures/) are working plots: they use the
raw sector tags and count unique curves rather than records. These use plain
labels and count records, the same unit as the coverage tables.

Run from the repo root:
    python scripts/paper_figures.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import NullFormatter

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from spindep.src.parser import load_dataset                          # noqa: E402
from spindep.src.statistics import chi_squared_from_datasets         # noqa: E402
from spindep.src.unit_conversion import convert_lambda_to_metres     # noqa: E402

OUT = REPO / "results" / "figures" / "paper"

# Applied inside the plotting functions: importing the spindep modules
# resets matplotlib's style, so setting it at import time does not stick.
STYLE = {
    "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 7.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "mathtext.fontset": "cm", "font.family": "serif",
}

# (coupling, matter file, antimatter file, panel title, matter label,
#  antimatter label, legend position, explicit x ticks or None)
PAIRS = [
    ("gAgA", "2Karshenboim_2011_1_millionev_abs_ep", "2Ficek_2018_V2_m_abs_epbar",
     r"(a) $g_Ag_A$, $V_2$: $e$–$p$ vs $e$–$\bar p$",
     r"$e$–$p$, hydrogen (Karshenboim)", r"$e$–$\bar p$, $\bar p$He (Ficek et al.)",
     "center right", None),
    ("gAgA", "2Jiao_2019_m_abs_ee", "2Karshenboim_2011_3_m_abs_eebar",
     r"(b) $g_Ag_A$, $V_2$: $e$–$e$ vs $e$–$e^+$",
     r"$e$–$e$ (Jiao et al.)", r"$e$–$e^+$, positronium (Karshenboim)",
     "upper right", [4e-9, 1e-8, 2e-8]),
]

SECTOR_LABEL = {
    "ee": "$e$–$e$", "eebar": "$e$–$e^+$", "ep": "$e$–$p$", "epbar": r"$e$–$\bar p$",
    "emubar": r"$e$–$\bar\mu$", "en": "$e$–$n$", "eN": "$e$–$N$", "nN": "$n$–$N$",
    "pN": "$p$–$N$", "nn": "$n$–$n$", "np": "$n$–$p$", "mumu": r"$\mu$–$\mu$",
    "muN": r"$\mu$–$N$", "antipHe": r"$\bar p$–He", "ddmu": r"$dd\mu^+$",
    "eastro": "$e$ (astro)", "eNastro": "$e$–$N$ (astro)",
    "nNastro": "$n$–$N$ (astro)", "pNastro": "$p$–$N$ (astro)",
    "NNastro": "$N$–$N$ (astro)",
}
# Matter sector directly above its antimatter partner, then the rest.
SECTOR_ORDER = ["ee", "eebar", "ep", "epbar", "emubar", "en", "eN", "nN", "pN",
                "nn", "np", "mumu", "muN", "antipHe", "ddmu",
                "eastro", "eNastro", "nNastro", "pNastro", "NNastro"]
POTENTIAL_ORDER = ["V1", "V1a", "V2", "V2+3", "V3", "V4+5", "V8", "V9+10",
                   "V11", "V12+13", "V15", "V16"]


def pot_label(p):
    return "$V_{" + p[1:] + "}$"


def load(registry, coupling, filename):
    row = registry[(registry.coupling == coupling) & (registry.filename == filename)].iloc[0]
    df, _, _ = convert_lambda_to_metres(load_dataset(REPO / row.filepath), filename)
    return df.sort_values("lambda_m")


def plot_pair_bounds(registry):
    plt.rcParams.update(STYLE)
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
    for ax, (c, fm, fa, title, lm, la, loc, xticks) in zip(axes, PAIRS):
        df_m, df_a = load(registry, c, fm), load(registry, c, fa)
        stats = chi_squared_from_datasets(df_m, df_a, n_points=300, n_boot=0)
        lam = stats["lam_grid"]
        ax.plot(lam, stats["g_m"], color="#1f4e79", lw=1.6, label=lm)
        ax.plot(lam, stats["g_a"], color="#a4262c", lw=1.6, ls="--", label=la)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"$\lambda$ (m)")
        ax.set_title(title, fontsize=9, loc="left")
        ax.text(0.03, 0.05, rf"$\overline{{|A_U|}}={stats['mean_abs_A']:.4f}$",
                transform=ax.transAxes, fontsize=8)
        ax.legend(frameon=False, loc=loc)
        ax.xaxis.set_minor_formatter(NullFormatter())
        if xticks:
            # The overlap spans less than a decade here, so label it by hand.
            ax.set_xticks(xticks)
            ax.set_xticklabels([rf"${t / 10**np.floor(np.log10(t)):.0f}\times10^{{{int(np.floor(np.log10(t)))}}}$"
                                for t in xticks])
        ax.grid(alpha=0.3, which="major")
    axes[0].set_ylabel(r"upper bound on $|g_A g_A|$")
    fig.tight_layout()
    save(fig, "pair_bounds")


def plot_coverage_matrix(registry):
    plt.rcParams.update(STYLE)
    kept = registry[~registry.excluded]
    counts = (kept.groupby(["sector", "potential"]).size()
              .unstack(fill_value=0)
              .reindex(index=SECTOR_ORDER, columns=POTENTIAL_ORDER, fill_value=0))
    assert counts.values.sum() == len(kept), "matrix must account for every analysed record"

    cmap = LinearSegmentedColormap.from_list("cov", ["#f4f6f9", "#1f4e79"])
    fig, ax = plt.subplots(figsize=(7.0, 5.4))
    im = ax.imshow(counts.values, cmap=cmap, aspect="auto", vmin=0)
    for i in range(counts.shape[0]):
        for j in range(counts.shape[1]):
            v = counts.values[i, j]
            if v:
                ax.text(j, i, str(v), ha="center", va="center", fontsize=7.5,
                        color="white" if v > counts.values.max() / 2 else "#1a1a1a")
    ax.set_xticks(range(len(POTENTIAL_ORDER)))
    ax.set_xticklabels([pot_label(p) for p in POTENTIAL_ORDER])
    ax.set_yticks(range(len(SECTOR_ORDER)))
    ax.set_yticklabels([SECTOR_LABEL[s] for s in SECTOR_ORDER])
    anti = set(kept.loc[kept.contains_antimatter, "sector"])
    for tick, s in zip(ax.get_yticklabels(), SECTOR_ORDER):
        if s in anti:
            tick.set_color("#a4262c")
    ax.set_xlabel("potential label")
    ax.set_ylabel("fermion sector (antimatter in red)")
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("analysed records")
    fig.tight_layout()
    save(fig, "coverage_matrix")


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    registry = pd.read_csv(REPO / "results" / "tables" / "dataset_registry.csv")
    plot_pair_bounds(registry)
    plot_coverage_matrix(registry)
    print(f"Figures written to {OUT}")
