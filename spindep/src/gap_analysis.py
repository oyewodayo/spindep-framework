# // gap_analysis.py
"""
Gap analysis for spin-dependent exotic interaction constraints.
Produces three publication-quality figures:
  1. Fermion pair coverage matrix  (potential x sector heatmap)
  2. Dataset inventory by potential (no overlapping labels)
  3. Matter vs antimatter coverage ratio per sector
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from collections import defaultdict
import hashlib
import re

try:
    from .print_style import PrintStyle, apply_print_rcparams, save_figure, INK
except ImportError:
    from print_style import PrintStyle, apply_print_rcparams, save_figure, INK

apply_print_rcparams()


def deduplicate_by_content(datasets):
    """Collapse datasets whose underlying CSV is byte-identical (the same
    bound catalogued once per coupling class that can generate a given
    potential -- deliberate in the upstream Cong et al. dataset) to a
    single representative, so coverage counts reflect independent
    measurements rather than coupling-class multiplicity."""
    #
    # Which copy represents the group matters: a copy filed under a coupling
    # class whose filename carries no potential token (e.g. gpgp/Kimball_2010
    # ... .csv, missing the "3" prefix its gVgV twin has) parses as UNKNOWN
    # and is dropped downstream. Taking whichever copy arrives first made the
    # result depend on directory traversal order, which differs between
    # filesystems -- V2+3 came out as 18 datasets on ext4 and 25 on NTFS from
    # the same files. Always prefer a labelled copy over an UNKNOWN one.
    by_hash  = {}
    order    = []
    for d in datasets:
        content_hash = hashlib.md5(Path(d.filepath).read_bytes()).hexdigest()
        kept = by_hash.get(content_hash)
        if kept is None:
            by_hash[content_hash] = d
            order.append(content_hash)
        elif kept.potential == "UNKNOWN" and d.potential != "UNKNOWN":
            by_hash[content_hash] = d
    return [by_hash[h] for h in order]

NAVY    = "#1a2e4a"
STEEL   = "#2d6a9f"
CRIMSON = "#b03a2e"
LIGHT   = "#f4f6f9"
WHITE   = "#ffffff"

MATTER_ANTIMATTER_PAIRS = {
    "ee": "eebar", "ep": "epbar", "en": "enbar",
    "emu": "emubar", "mumu": "mumubar", "np": "npbar",
    "nn": "nnbar", "pp": "ppbar", "eN": "eNbar",
}

SECTOR_LABELS = {
    "ee": "e-e", "eebar": "e-e+", "ep": "e-p", "epbar": "e-pbar",
    "en": "e-n", "enbar": "e-nbar", "emu": "e-mu", "emubar": "e-mubar",
    "mumu": "mu-mu", "mumubar": "mu-mubar", "np": "n-p", "npbar": "n-pbar",
    "nn": "n-n", "nnbar": "n-nbar", "pp": "p-p", "ppbar": "p-pbar",
    "eN": "e-N", "eNbar": "e-Nbar", "nN": "n-N", "pN": "p-N",
    "antipHe": "pbar-He", "ddmu": "ddmu+",
}

ANTIMATTER_SECTORS = {
    "eebar","epbar","enbar","emubar","mumubar",
    "npbar","nnbar","ppbar","eNbar",
    "antipHe",  # p-bar-He: contains an antiproton
    "ddmu",     # ddmu+ molecular ion: contains an antimuon
}


def pot_sort_key(p):
    m = re.match(r"V(\d+)", p)
    return int(m.group(1)) if m else 999


# ============================================================
# FIGURE 1 — COVERAGE MATRIX
# ============================================================

def plot_pair_coverage_matrix(datasets, output_path):
    counts = defaultdict(int)
    potentials_seen, sectors_seen = set(), set()
    for d in datasets:
        if d.potential == "UNKNOWN":
            continue
        counts[(d.potential, d.sector)] += 1
        potentials_seen.add(d.potential)
        sectors_seen.add(d.sector)

    potentials = sorted(potentials_seen, key=pot_sort_key)
    sectors    = sorted(sectors_seen)
    matrix = np.zeros((len(sectors), len(potentials)), dtype=int)
    for (pot, sec), cnt in counts.items():
        if pot in potentials and sec in sectors:
            matrix[sectors.index(sec), potentials.index(pot)] = cnt

    row_colors = [CRIMSON if s in ANTIMATTER_SECTORS else STEEL for s in sectors]
    fig_w = max(12, len(potentials)*0.9)
    fig, ax = plt.subplots(figsize=(fig_w, max(8, len(sectors)*0.45)))
    ps = PrintStyle(fig_w)
    cmap = LinearSegmentedColormap.from_list("cov", [LIGHT, STEEL, NAVY], N=256)
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0, vmax=max(matrix.max(), 1))
    for si in range(len(sectors)):
        for pi in range(len(potentials)):
            val = matrix[si, pi]
            if val > 0:
                c = WHITE if val > matrix.max() * 0.5 else NAVY
                ax.text(pi, si, str(val), ha="center", va="center",
                        fontsize=ps.pt(7), color=c, fontweight="bold")
    ax.set_xticks(range(len(potentials)))
    ax.set_xticklabels(potentials, fontsize=ps.pt(8), rotation=45, ha="right")
    ax.set_yticks(range(len(sectors)))
    ax.set_yticklabels([str(SECTOR_LABELS.get(s, s)) for s in sectors], fontsize=ps.pt(8))
    for tick, color in zip(ax.get_yticklabels(), row_colors):
        tick.set_color(color)
    ax.set_xlabel("Interaction Potential", fontsize=ps.pt(9.5), color=INK)
    ax.set_ylabel("Fermion Sector", fontsize=ps.pt(9.5), color=INK)
    ax.set_title("Dataset Coverage: Potential x Fermion Sector",
                 fontsize=ps.pt(10.5), color=INK, pad=ps.pt(10))
    ax.legend(handles=[
        mpatches.Patch(color=STEEL,   label="Matter sector"),
        mpatches.Patch(color=CRIMSON, label="Antimatter sector"),
        mpatches.Patch(color=LIGHT,   label="No data (gap)"),
    ], loc="upper right", fontsize=ps.pt(8), framealpha=1.0, edgecolor=INK)
    cbar = plt.colorbar(im, ax=ax, shrink=0.6)
    cbar.set_label("Number of datasets", fontsize=ps.pt(8.5), color=INK)
    cbar.ax.tick_params(labelsize=ps.pt(7.5), width=ps.pt(0.7),
                        length=ps.pt(3), color=INK, labelcolor=INK)
    cbar.outline.set_linewidth(ps.pt(0.7))
    fig.tight_layout()
    save_figure(fig, output_path, style=ps)
    plt.close(fig)
    print(f"[GAP] Saved pair coverage matrix -> {output_path}")


# ============================================================
# FIGURE 2 — DATASET INVENTORY (one page-sized image per potential)
# Uses a table-style layout: one row per dataset, labels in
# a separate text column so bars never collide with text.
# ============================================================

def _sanitize_potential(pot):
    """Filesystem/LaTeX-safe filename stem, e.g. 'V4+5' -> 'V4p5'."""
    return pot.replace("+", "p")


def plot_lambda_coverage(datasets, output_dir):
    by_potential = defaultdict(list)
    for d in datasets:
        if d.potential != "UNKNOWN":
            by_potential[d.potential].append(d)
    potentials = sorted(by_potential.keys(), key=pot_sort_key)
    if not potentials:
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for pot in potentials:
        dsets = sorted(by_potential[pot], key=lambda x: (x.sector, x.source))
        n = len(dsets)
        row_h = 0.30          # inches per row
        panel_h = max(1.2, n * row_h)

        fig, ax = plt.subplots(figsize=(9, panel_h))
        ps = PrintStyle(9)
        fs = ps.pt(max(5.5, min(8.5, 180 / max(n, 1))))

        for yi, d in enumerate(dsets):
            is_anti = d.sector in ANTIMATTER_SECTORS
            color   = CRIMSON if is_anti else STEEL
            hatch   = "///" if is_anti else ""
            ax.barh(yi, 1, left=0, height=0.7,
                    color=color, alpha=0.75,
                    hatch=hatch, edgecolor=INK, linewidth=ps.pt(0.5))

        # Labels: truncated to avoid overflow
        def lbl(d):
            sec = SECTOR_LABELS.get(d.sector, d.sector)
            src = d.source[:20]
            return f"{src}  [{sec}]"

        ax.set_yticks(range(n))
        ax.set_yticklabels([lbl(d) for d in dsets], fontsize=fs)
        ax.set_ylim(-0.6, n - 0.4)
        ax.set_xticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)

        n_m = sum(1 for d in dsets if d.sector not in ANTIMATTER_SECTORS)
        n_a = n - n_m
        ax.set_title(f"Dataset Inventory: {pot}   (matter: {n_m}  antimatter: {n_a}  total: {n})",
                     fontsize=ps.pt(9), color=INK, loc="left",
                     pad=ps.pt(4), fontweight="bold")
        fig.tight_layout(pad=0.4)

        out_path = output_dir / f"lambda_coverage_{_sanitize_potential(pot)}.png"
        save_figure(fig, out_path, style=ps)
        plt.close(fig)
        saved_paths.append(out_path)

    print(f"[GAP] Saved {len(saved_paths)} lambda coverage charts -> {output_dir}/")
    return saved_paths


# ============================================================
# FIGURE 3 — MATTER vs ANTIMATTER RATIO
# ============================================================

def plot_matter_antimatter_ratio(datasets, output_path):
    matter_counts = defaultdict(int)
    anti_counts   = defaultdict(int)
    for d in datasets:
        if d.sector in ANTIMATTER_SECTORS:
            for m, a in MATTER_ANTIMATTER_PAIRS.items():
                if a == d.sector:
                    anti_counts[m] += 1
                    break
        else:
            matter_counts[d.sector] += 1

    all_sectors = sorted(set(matter_counts) | set(anti_counts))
    m_vals = [matter_counts[s] for s in all_sectors]
    a_vals = [anti_counts[s]   for s in all_sectors]
    x = np.arange(len(all_sectors))
    w = 0.38

    fig_w = max(10, len(all_sectors))
    fig, ax = plt.subplots(figsize=(fig_w, 5))
    ps = PrintStyle(fig_w)
    ax.bar(x - w/2, m_vals, w, color=STEEL,   label="Matter sector",
           edgecolor=INK, linewidth=ps.pt(0.7))
    ax.bar(x + w/2, a_vals, w, color=CRIMSON, label="Antimatter sector",
           edgecolor=INK, linewidth=ps.pt(0.7))
    for xi, av in zip(x, a_vals):
        if av == 0:
            ax.annotate("GAP", xy=(xi + w/2, 0.15), fontsize=ps.pt(7),
                        color=CRIMSON, ha="center", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([str(SECTOR_LABELS.get(s, s)) for s in all_sectors],
                       rotation=35, ha="right", fontsize=ps.pt(8.5))
    ax.set_ylabel("Number of datasets", fontsize=ps.pt(9.5), color=INK)
    ax.tick_params(labelsize=ps.pt(8.5), width=ps.pt(0.8), color=INK, labelcolor=INK)
    ax.set_title("Matter vs Antimatter Dataset Coverage per Fermion Sector\n(GAP = no antimatter data)", fontsize=ps.pt(10.5), color=INK)
    ax.legend(fontsize=ps.pt(8.5), framealpha=1.0, edgecolor=INK)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_facecolor(LIGHT)
    fig.patch.set_facecolor(WHITE)
    fig.tight_layout()
    save_figure(fig, output_path, style=ps)
    plt.close(fig)
    print(f"[GAP] Saved matter/antimatter ratio -> {output_path}")


# ============================================================
# FIGURE 4 — MICROSCOPIC vs MACROSCOPIC SCALE REGIME
# ============================================================

REGIME_COLORS = {
    "microscopic": CRIMSON,
    "macroscopic": STEEL,
    "mixed":       "#8a8a8a",
    "UNKNOWN":     LIGHT,
}

def plot_scale_regime_coverage(datasets, output_path):
    """Bar chart of dataset counts by microscopic/macroscopic/mixed
    scale regime (see unit_conversion.classify_scale_regime), split
    by coupling type (gAgA, gVgV, ...)."""
    counts = defaultdict(lambda: defaultdict(int))
    regimes_seen = set()
    for d in datasets:
        regime = getattr(d, "scale_regime", "UNKNOWN")
        counts[d.coupling][regime] += 1
        regimes_seen.add(regime)

    couplings = sorted(counts.keys())
    regime_order = [r for r in ("macroscopic", "microscopic", "mixed", "UNKNOWN") if r in regimes_seen]
    x = np.arange(len(couplings))
    n_regimes = len(regime_order)
    w = 0.8 / max(n_regimes, 1)

    fig_w = max(8, len(couplings) * 1.3)
    fig, ax = plt.subplots(figsize=(fig_w, 5))
    ps = PrintStyle(fig_w)
    for i, regime in enumerate(regime_order):
        vals = [counts[c][regime] for c in couplings]
        offset = (i - (n_regimes - 1) / 2) * w
        ax.bar(x + offset, vals, w, color=REGIME_COLORS.get(regime, "#cccccc"),
               edgecolor=INK, linewidth=ps.pt(0.6), label=regime)

    ax.set_xticks(x)
    ax.set_xticklabels(couplings, fontsize=ps.pt(8.5))
    ax.set_ylabel("Number of datasets", fontsize=ps.pt(9.5), color=INK)
    ax.tick_params(labelsize=ps.pt(8.5), width=ps.pt(0.8), color=INK, labelcolor=INK)
    ax.set_title(f"Dataset Scale Regime by Coupling\n"
                 f"(microscopic: λ < {1e-6:.0e} m, macroscopic: λ ≥ {1e-6:.0e} m, by majority of points)",
                 fontsize=ps.pt(10.5), color=INK)
    ax.legend(fontsize=ps.pt(8.5), framealpha=1.0, edgecolor=INK)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_facecolor(LIGHT)
    fig.patch.set_facecolor(WHITE)
    fig.tight_layout()
    save_figure(fig, output_path, style=ps)
    plt.close(fig)
    print(f"[GAP] Saved scale regime coverage -> {output_path}")


# ============================================================
# RUN ALL
# ============================================================

def run_gap_analysis(datasets, figures_dir):
    n_before = len(datasets)
    datasets = deduplicate_by_content(datasets)

    # The same curve-level exclusions the constraint atlas applies, so the
    # coverage counts and the figures describe the same set of bounds.
    try:
        from .constraint_plots import drop_excluded_duplicates
    except ImportError:
        from constraint_plots import drop_excluded_duplicates
    datasets = drop_excluded_duplicates(datasets, verbose=False)
    if len(datasets) != n_before:
        print(f"[GAP] Collapsed {n_before - len(datasets)} duplicate-content "
              f"datasets (same bound filed under multiple coupling classes) "
              f"-> {len(datasets)} independent datasets for coverage counting")

    figures_dir = Path(figures_dir)
    plot_pair_coverage_matrix(datasets, figures_dir / "gap_analysis" / "pair_coverage_matrix.png")
    plot_lambda_coverage(datasets,      figures_dir / "gap_analysis" / "lambda_coverage_by_potential")
    plot_matter_antimatter_ratio(datasets, figures_dir / "gap_analysis" / "matter_antimatter_ratio.png")
    plot_scale_regime_coverage(datasets, figures_dir / "gap_analysis" / "scale_regime_coverage.png")
    print(f"\n[GAP] All gap analysis figures saved to {figures_dir}/gap_analysis/")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "spindep")
    from src.parser import discover_datasets
    datasets = discover_datasets(Path("spindep/datasets/normalized"))
    print(f"Loaded {len(datasets)} datasets")
    run_gap_analysis(datasets, figures_dir="results/figures")