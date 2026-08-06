# // constraint_plots.py
"""
Constraint atlas for spin-dependent exotic interactions.

Generates publication-quality log-log plots of coupling upper bounds
vs interaction range lambda for each potential Vi.

Two plot types:
  1. Per-potential atlas: all datasets for a given Vi on one panel,
     coloured by sector, matter=solid/antimatter=dashed.
  2. Multi-panel grid: all potentials in one figure (16-panel atlas).

Style follows Cong et al., Rev. Mod. Phys. 97, 025005 (2025).
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.patheffects as pe
from adjustText import adjust_text
from pathlib import Path
from collections import defaultdict
import hashlib
import re

# hbar*c in eV*m, for the secondary "equivalent boson mass" axis
# (m = hbar*c / lambda), matching Cong et al. 2025 Figs. 15-16.
HBAR_C_EV_M = 1.973269804e-7


def deduplicate_by_content(datasets):
    """Collapse datasets whose underlying CSV is byte-identical (the same
    bound catalogued once per coupling class that can generate a given
    potential -- deliberate in the upstream Cong et al. dataset) to a
    single representative, so each independent measurement is drawn once
    per potential instead of once per coupling class it's filed under."""
    seen_hashes = set()
    deduped = []
    for d in datasets:
        content_hash = hashlib.md5(Path(d.filepath).read_bytes()).hexdigest()
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            deduped.append(d)
    return deduped

# ============================================================
# STYLE CONSTANTS
# ============================================================

NAVY    = "#1a2e4a"
WHITE   = "#ffffff"

# Colour palette: one colour per sector
SECTOR_COLOURS = {
    "ee":      "#2d6a9f",   # steel blue
    "eebar":   "#e74c3c",   # red
    "ep":      "#27ae60",   # green
    "epbar":   "#e67e22",   # orange
    "en":      "#8e44ad",   # purple
    "enbar":   "#c0392b",   # dark red
    "emu":     "#16a085",   # teal
    "emubar":  "#d35400",   # burnt orange
    "mumu":    "#2980b9",   # blue
    "mumubar": "#e74c3c",   # red
    "np":      "#1abc9c",   # mint
    "npbar":   "#f39c12",   # amber
    "nn":      "#34495e",   # dark grey
    "nnbar":   "#95a5a6",   # grey
    "pp":      "#7f8c8d",   # mid grey
    "ppbar":   "#bdc3c7",   # light grey
    "eN":      "#6c3483",   # violet
    "eNbar":   "#a93226",   # dark crimson
    "nN":      "#1a5276",   # dark blue
    "pN":      "#0e6655",   # dark green
    "muN":     "#784212",   # brown
    "mumu":    "#2471a3",
    "eastro":  "#aab7b8",
    "eNastro": "#aab7b8",
    "NNastro": "#aab7b8",
    "UNKNOWN": "#bdc3c7",
}

SECTOR_LABELS = {
    "ee":      r"$e^-$–$e^-$",
    "eebar":   r"$e^-$–$e^+$",
    "ep":      r"$e$–$p$",
    "epbar":   r"$e$–$\bar{p}$",
    "en":      r"$e$–$n$",
    "enbar":   r"$e$–$\bar{n}$",
    "emu":     r"$e$–$\mu$",
    "emubar":  r"$e$–$\bar{\mu}$",
    "mumu":    r"$\mu$–$\mu$",
    "mumubar": r"$\mu$–$\bar{\mu}$",
    "np":      r"$n$–$p$",
    "npbar":   r"$n$–$\bar{p}$",
    "nn":      r"$n$–$n$",
    "nnbar":   r"$n$–$\bar{n}$",
    "pp":      r"$p$–$p$",
    "ppbar":   r"$p$–$\bar{p}$",
    "eN":      r"$e$–$N$",
    "eNbar":   r"$e$–$\bar{N}$",
    "nN":      r"$n$–$N$",
    "pN":      r"$p$–$N$",
    "muN":     r"$\mu$–$N$",
    "UNKNOWN": "Unknown",
}

ANTIMATTER_SECTORS = {
    "eebar","epbar","enbar","emubar","mumubar",
    "npbar","nnbar","ppbar","eNbar"
}


def pot_sort_key(p):
    m = re.match(r"V(\d+)", p)
    return int(m.group(1)) if m else 999


# ============================================================
# LOAD DATASET DATA (with unit conversion)
# ============================================================

def _load_with_conversion(dataset):
    """Load a ConstraintDataset and return (lambda_m, coupling) arrays."""
    try:
        import pandas as pd
        df = pd.read_csv(
            dataset.filepath,
            header=None,
            names=["lambda_m", "coupling_abs"]
        )
        df = df.apply(pd.to_numeric, errors="coerce").dropna()
        df = df[(df["lambda_m"] > 0) & (df["coupling_abs"] > 0)]
        df = df.sort_values("lambda_m").reset_index(drop=True)

        # Apply unit conversion
        try:
            from .unit_conversion import convert_lambda_to_metres
        except ImportError:
            from unit_conversion import convert_lambda_to_metres

        df, _, _ = convert_lambda_to_metres(df, dataset.filename, verbose=False)
        return df["lambda_m"].values, df["coupling_abs"].values
    except Exception as e:
        print(f"  [LOAD ERROR] {dataset.filename}: {e}")
        return None, None


# ============================================================
# FIGURE 1: SINGLE-POTENTIAL CONSTRAINT PLOT
# ============================================================

# A single sector colour, shared by every dataset in that sector, made it
# impossible to tell one experiment's curve apart from another's whenever a
# sector had more than one dataset (the common case) — see DATASET_PALETTE
# below, which assigns each individual *dataset* its own colour instead.
DATASET_PALETTE = (
    list(plt.get_cmap("tab20").colors)
    + list(plt.get_cmap("tab20b").colors)
    + list(plt.get_cmap("tab20c").colors)
)  # 60 visually-distinct colours; cycles (via %) if a potential somehow exceeds that


def _readable_color(rgb):
    """Darken palette colours too light to read as inline label text on
    the white axes background (some tab20b/c entries are near-pastel)."""
    r, g, b = rgb
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if lum > 0.6:
        factor = 0.6 / lum
        r, g, b = r * factor, g * factor, b * factor
    return (r, g, b)


def plot_single_potential(datasets_for_potential, potential, output_path,
                          coupling_label="g", title_suffix=""):
    """
    Plot all coupling upper bounds for one potential on a single log-log
    axis, matching the style of the source review (Cong et al. 2025,
    Figs. 15-16): each curve is labelled inline, in its own colour, next
    to the curve itself -- no legend box -- plus a secondary top axis
    showing the equivalent new-boson mass. Matter datasets: solid lines.
    Antimatter: dashed.
    """
    # Sort: matter first, then antimatter, alphabetically within each —
    # keeps colour assignment stable across regenerations.
    sorted_dsets = sorted(
        datasets_for_potential,
        key=lambda d: (d.sector in ANTIMATTER_SECTORS, d.sector, d.source)
    )

    n_entries = len(sorted_dsets)
    # More curves need more room for inline labels to spread into.
    fig_w = min(11 + 0.09 * n_entries, 22)
    fig_h = min(7 + 0.07 * n_entries, 14)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_facecolor(WHITE)
    fig.patch.set_facecolor(WHITE)

    curves = []
    n_plotted = 0

    for i, d in enumerate(sorted_dsets):
        lam, g = _load_with_conversion(d)
        if lam is None or g is None or len(lam) < 2 or len(g) < 2:
            continue

        color     = _readable_color(DATASET_PALETTE[i % len(DATASET_PALETTE)])
        linestyle = "--" if d.sector in ANTIMATTER_SECTORS else "-"

        ax.plot(lam, g, color=color, linestyle=linestyle,
                linewidth=1.3, alpha=0.9)

        label = f"{d.source} ({SECTOR_LABELS.get(d.sector, d.sector)})"
        curves.append((lam, g, color, label))
        n_plotted += 1

    if n_plotted == 0:
        plt.close(fig)
        return

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Interaction range $\lambda$ (m)", fontsize=12, color=NAVY)
    ax.set_ylabel(rf"Coupling upper bound $|{coupling_label}|$", fontsize=12, color=NAVY)
    ax.set_title(
        rf"${potential}$ potential constraints{' — ' + title_suffix if title_suffix else ''}"
        f"  (solid = matter, dashed = antimatter)",
        fontsize=13, color=NAVY, pad=32
    )

    # Secondary top axis: equivalent new-boson mass, m = hbar*c / lambda
    # (self-inverse formula, same function both directions).
    def _lambda_to_mass(lam):
        with np.errstate(divide="ignore"):
            return HBAR_C_EV_M / np.where(lam > 0, lam, np.nan)

    secax = ax.secondary_xaxis("top", functions=(_lambda_to_mass, _lambda_to_mass))
    secax.set_xlabel("Mass (eV)", fontsize=11, color=NAVY)
    secax.tick_params(labelsize=9)

    # Inline labels anchored at each curve's rightmost point, coloured to
    # match the curve, with overlaps resolved automatically (thin leader
    # line drawn where a label had to move away from its curve).
    texts = []
    for lam, g, color, label in curves:
        t = ax.text(lam[-1], g[-1], label, color=color,
                    fontsize=7.5, fontweight="bold", alpha=0.95)
        t.set_path_effects([pe.withStroke(linewidth=2.2, foreground=WHITE, alpha=0.85)])
        texts.append(t)

    adjust_text(
        texts, ax=ax,
        arrowprops=dict(arrowstyle="-", color="grey", lw=0.6, alpha=0.6),
        expand_text=(1.3, 1.6), expand_points=(1.2, 1.4),
        force_text=(0.6, 1.0), force_points=(0.3, 0.5),
        lim=1500,
    )

    ax.grid(True, which="both", linestyle=":", linewidth=0.5,
            color="#cccccc", alpha=0.7)
    ax.tick_params(labelsize=10)

    # Annotation: dataset count
    ax.text(0.02, 0.02,
            f"N = {n_plotted} datasets",
            transform=ax.transAxes, fontsize=8,
            color=NAVY, va="bottom")

    fig.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)


# ============================================================
# FIGURE 2: MULTI-PANEL ATLAS (all potentials in one figure)
# ============================================================

def plot_constraint_atlas(datasets, output_path, max_panels=20):
    """
    Multi-panel constraint atlas: one subplot per potential,
    arranged in a grid. Publication-quality for thesis figures/.
    """
    # Group by potential
    by_pot = defaultdict(list)
    for d in datasets:
        if d.potential != "UNKNOWN":
            by_pot[d.potential].append(d)

    potentials = sorted(by_pot.keys(), key=pot_sort_key)[:max_panels]
    n = len(potentials)
    if n == 0:
        print("[CONSTRAINT] No datasets with known potentials.")
        return

    ncols = min(4, n)
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(ncols * 5.5, nrows * 4.5),
        squeeze=False
    )
    fig.patch.set_facecolor(WHITE)

    # Track which sectors appear globally for a unified legend
    global_sectors = set()

    for idx, pot in enumerate(potentials):
        row, col = divmod(idx, ncols)
        ax = axes[row][col]
        ax.set_facecolor(WHITE)

        dsets = sorted(by_pot[pot],
                       key=lambda d: (d.sector in ANTIMATTER_SECTORS, d.sector))
        n_plotted = 0

        for d in dsets:
            lam, g = _load_with_conversion(d)
            if lam is None or len(lam) < 2:
                continue

            color     = SECTOR_COLOURS.get(d.sector, "#888888")
            linestyle = "--" if d.sector in ANTIMATTER_SECTORS else "-"
            lw        = 1.0

            ax.plot(lam, g, color=color, linestyle=linestyle,
                    linewidth=lw, alpha=0.8)
            global_sectors.add(d.sector)
            n_plotted += 1

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"$V_{{{pot[1:]}}}$" if pot.startswith("V") else pot,
                     fontsize=10, color=NAVY, pad=4)
        ax.tick_params(labelsize=7)
        ax.grid(True, which="both", linestyle=":", linewidth=0.4,
                color="#cccccc", alpha=0.6)

        # Minimal axis labels only on edges
        if row == nrows - 1:
            ax.set_xlabel(r"$\lambda$ (m)", fontsize=8, color=NAVY)
        if col == 0:
            ax.set_ylabel("Coupling bound", fontsize=8, color=NAVY)

        ax.text(0.97, 0.97, f"N={n_plotted}",
                transform=ax.transAxes, fontsize=6.5,
                color=NAVY, ha="right", va="top")

    # Hide unused subplots
    for idx in range(n, nrows * ncols):
        row, col = divmod(idx, ncols)
        axes[row][col].set_visible(False)

    # Unified sector legend below the figure
    legend_handles = []
    for sec in sorted(global_sectors):
        color = SECTOR_COLOURS.get(sec, "#888888")
        ls    = "--" if sec in ANTIMATTER_SECTORS else "-"
        legend_handles.append(
            mlines.Line2D([], [], color=color, linestyle=ls,
                          linewidth=1.8,
                          label=SECTOR_LABELS.get(sec, sec))
        )
    # Add style guide
    legend_handles += [
        mlines.Line2D([], [], color="grey", linestyle="-",  linewidth=2, label="Matter sector"),
        mlines.Line2D([], [], color="grey", linestyle="--", linewidth=2, label="Antimatter sector"),
    ]

    fig.legend(handles=legend_handles,
               loc="lower center",
               bbox_to_anchor=(0.5, -0.02),
               ncol=min(8, len(legend_handles)),
               fontsize=8,
               framealpha=0.9,
               title="Fermion sector  (solid=matter, dashed=antimatter)",
               title_fontsize=8)

    fig.suptitle(
        "Spin-Dependent Exotic Interaction Constraint Atlas\n"
        r"Coupling upper bounds $|g|$ vs interaction range $\lambda$",
        fontsize=13, color=NAVY, y=1.01
    )

    fig.tight_layout(rect=(0, 0.06, 1, 1))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"[CONSTRAINT] Saved constraint atlas -> {output_path}")


# ============================================================
# FIGURE 3: MATTER-ANTIMATTER COMPARISON PLOTS
# (for each valid asymmetry pair — overlays matter and antimatter)
# ============================================================

def plot_matter_antimatter_comparison(summary_rows, plots_dir, output_dir):
    """
    For each successfully analysed pair in summary_rows, generate a
    dedicated comparison plot showing:
      - Top panel: matter and antimatter coupling bounds vs lambda
      - Bottom panel: asymmetry parameter A_alpha vs lambda
    This replicates the per-pair plots in the PDF report but saves
    them to figures/matter_antimatter/ as standalone publication files.
    """
    plots_dir  = Path(plots_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for row in summary_rows:
        # Find the matching plot file
        plot_name = (
            f"{row['coupling']}_{row['potential']}_"
            f"{row['sector']}_{row['matter_filename']}.png"
        )
        src = plots_dir / plot_name
        if not src.exists():
            continue

        # Copy to figures/matter_antimatter/ with a cleaner name
        clean_name = (
            f"{row['coupling']}_{row['potential']}_"
            f"{row['sector']}_{row['matter_source']}_vs_{row['antimatter_source']}.png"
        )
        import shutil
        shutil.copy2(src, output_dir / clean_name)

    print(f"[CONSTRAINT] Copied {len(summary_rows)} comparison plots -> {output_dir}")


# ============================================================
# MAIN ENTRY: RUN ALL CONSTRAINT PLOTS
# ============================================================

def run_constraint_plots(datasets, summary_rows, plots_dir, figures_dir):
    """
    Generate all constraint atlas figures.

    Parameters
    ----------
    datasets     : list of ConstraintDataset (all 273)
    summary_rows : list of dicts from pipeline (valid pairs only)
    plots_dir    : Path to per-pair asymmetry plots
    figures_dir  : Path to figures output root
    """
    figures_dir = Path(figures_dir)
    atlas_dir   = figures_dir / "constraint_atlas"
    comp_dir    = figures_dir / "matter_antimatter"

    n_before = len(datasets)
    datasets = deduplicate_by_content(datasets)
    if len(datasets) != n_before:
        print(f"[CONSTRAINT] Collapsed {n_before - len(datasets)} duplicate-content "
              f"datasets (same bound filed under multiple coupling classes) "
              f"-> {len(datasets)} independent datasets for plotting")

    # Group by potential
    by_pot = defaultdict(list)
    for d in datasets:
        if d.potential != "UNKNOWN":
            by_pot[d.potential].append(d)

    potentials = sorted(by_pot.keys(), key=pot_sort_key)

    print(f"\n[CONSTRAINT] Generating per-potential plots for {len(potentials)} potentials...")

    # 1. Per-potential individual plots
    for pot in potentials:
        out = atlas_dir / f"constraint_{pot}.png"
        plot_single_potential(by_pot[pot], pot, out)
        print(f"  [CONSTRAINT] {pot} ({len(by_pot[pot])} datasets) -> {out.name}")

    # 2. Multi-panel atlas
    plot_constraint_atlas(
        datasets,
        figures_dir / "constraint_atlas" / "constraint_atlas_all.png"
    )

    # 3. Matter-antimatter comparison copies
    if summary_rows:
        plot_matter_antimatter_comparison(
            summary_rows,
            plots_dir=plots_dir,
            output_dir=comp_dir
        )

    print(f"[CONSTRAINT] All constraint plots saved to {figures_dir}/")


# ============================================================
# STANDALONE ENTRY
# ============================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "spindep")
    from src.parser import discover_datasets

    datasets = discover_datasets(Path("spindep/datasets/normalized"))
    print(f"Loaded {len(datasets)} datasets")
    run_constraint_plots(
        datasets=datasets,
        summary_rows=[],
        plots_dir=Path("results/plots"),
        figures_dir=Path("results/figures")
    )