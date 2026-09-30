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
from matplotlib.colors import to_rgb
from matplotlib.ticker import LogLocator, NullLocator
from adjustText import adjust_text
from pathlib import Path
from collections import defaultdict
import hashlib
import math
import re

try:
    from .print_style import PrintStyle, apply_print_rcparams, save_figure, INK
except ImportError:
    from print_style import PrintStyle, apply_print_rcparams, save_figure, INK

apply_print_rcparams()

# hbar*c in eV*m, for the secondary "equivalent boson mass" axis
# (m = hbar*c / lambda), matching Cong et al. 2025 Figs. 15-16.
HBAR_C_EV_M = 1.973269804e-7


def deduplicate_by_content(datasets):
    """Collapse datasets whose underlying CSV is byte-identical (the same
    bound catalogued once per coupling class that can generate a given
    potential -- deliberate in the upstream Cong et al. dataset) to a
    single representative, so each independent measurement is drawn once
    per potential instead of once per coupling class it's filed under."""
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

# ============================================================
# EXPLICITLY EXCLUDED DUPLICATES
# ============================================================

# Curves that duplicate another curve in the same panel but are not
# byte-identical, so deduplicate_by_content() cannot see them.
#
# This is a list, not a numeric tolerance, on purpose. A tolerance is a
# heuristic that silently decides which measurements exist -- the same
# failure mode as the directory-order bug that was deleting seven real
# V2+3 bounds -- and a genuinely close but distinct pair of bounds would
# vanish with no warning. Every entry below is named, evidenced and
# auditable; adding one is a deliberate act.
#
# Keyed by filename stem, which is unique to the excluded copy in each case.
EXCLUDED_DUPLICATES = {
    # The two *_squareV1bounds directories hold re-exports of the named
    # gsgs V1 files, rounded to ~5 significant figures. Verified agreement:
    # max |dlog10 g| <= 6e-4 at every sampled point over the full shared
    # span. The named copies are kept -- full precision, and their
    # filenames say which experiment they are.
    "V1_gse_EMM":     "duplicate of gsgs/lepton-lepton/V1_Delaunay_2017.csv",
    "V1_gse_EEP":     "duplicate of gsgs/lepton-lepton/V1_WEP_ee.csv",
    "V1_gse_Torsion": "duplicate of gsgs/lepton-lepton/V1_Torsion_ee.csv",
    "V1_gse_Casimir": "duplicate of gsgs/lepton-lepton/V1_Casimir_ee.csv",
    "V1_gsN_EEP":     "duplicate of gsgs/nucleon-nucleon/V1_WEP_NN.csv",
    "V1_gsN_Torsion": "duplicate of gsgs/nucleon-nucleon/V1_Torsion_NN.csv",
    "V1_gsN_Casimir": "duplicate of gsgs/nucleon-nucleon/V1_Casimir_NN.csv",
    "V1_gsN_MS":      "duplicate of gsgs/nucleon-nucleon/V1_Delaunay_2022_NN.csv",

    # gAgA's "eNastro" is a stray copy of gAgA's own NNastro curve, not an
    # e-N astrophysical bound: the two agree to max |dlog10 g| = 2e-4,
    # while in every other coupling class eNastro and NNastro are entirely
    # different curves (gVgV differs by 31 decades, gsgs by 0.3). The stem
    # with the underscore, "1a_eNastro_m_abs", occurs only under gAgA.
    "1a_eNastro_m_abs": "stray copy of gAgA/nucleon-nucleon/1aNNastro_m_abs.csv",
}


# ============================================================
# EXCLUDED FROM PHYSICS ANALYSIS
# ============================================================

# Datasets that are compiled into the registry -- so the chapter can state
# what was gathered and what was rejected -- but held out of gap analysis,
# the constraint atlas, pair matching and every asymmetry figure.
#
# Same rule as EXCLUDED_DUPLICATES above: a named, evidenced, auditable
# list, never a heuristic. "potential == UNKNOWN" is deliberately NOT the
# criterion, because the reasons differ and the thesis reports them
# separately.
#
# Keyed by filename stem, verified unique across datasets/normalized.
EXCLUDED_FROM_ANALYSIS = {}

# 1. The twelve gAgV combined curves. Upstream does not assign these a
#    potential at all: metadata/reports/gAgV-matching-report.md lists each
#    with Potential = "combined" and Status = "review_only", and states
#    "This is a pilot, not an authoritative scientific release." They are
#    envelopes over several experiments, so no single V_n applies to them
#    by construction -- not a parsing gap that a filename pass could close.
_COMBINED_GAGV = [
    "Combined_Casimir_e-e", "Combined_EEP_e-e",
    "Combined_EMM_e-e",     "Combined_Torsion_e-e",
    "Combined_Casimir_e-N", "Combined_EEP_e-N",
    "Combined_MS_e-N",      "Combined_Torsion_e-N",
    "Combined_Casimir_N-N", "Combined_EEP_N-N",
    "Combined_MS_N-N",      "Combined_Torsion_N-N",
]
for _stem in _COMBINED_GAGV:
    EXCLUDED_FROM_ANALYSIS[_stem] = (
        "gAgV combined envelope curve; upstream marks it "
        "potential=combined, status=review_only"
    )

# 2. gpgp's astrophysical e-N bound. A real, distinct measurement (a flat
#    |g| = 5e-19 over lambda = 2e-11..1e+14 m, stored as two endpoints),
#    but no potential has been assigned to it. Upstream leaves both gpgp
#    astro files unprefixed and makes no V_n claim, and V1_data.md is
#    silent on the astrophysical bounds, so labelling it V1a from its
#    siblings' filenames would be an inference, not evidence. Held out
#    until the source publication settles it.
EXCLUDED_FROM_ANALYSIS["eNastro_m_abs"] = (
    "potential unassigned; no upstream or documentary evidence for a V_n"
)

# 3. The Code-plot-matlab entries. "Your-new-data" is a template directory
#    shipped upstream for contributors to drop their own curves into; the
#    coupling label is the source directory's file format, not a physics
#    category.
for _stem in ["New_constriants_1", "New_constriants_2"]:
    EXCLUDED_FROM_ANALYSIS[_stem] = (
        "Code-plot-matlab template placeholder, not a measured constraint"
    )


# 4. Cong (2025) hydrogen-spectroscopy bounds are published at two
#    confidence levels. Both CSVs ship upstream, but they are the same
#    measurement reported twice, so counting both would double-count the
#    experiment and would pair each twice against the same antimatter
#    curve. The 95% CL set is kept: it is the more conservative limit and
#    the only one upstream carries a curation record for (the 90% CL files
#    have no api/v1/records entry). Swap the suffix below to invert this.
for _stem in ["23Cong_2025_m_ep_gAgA_90CL", "2Cong_2025_m_ep_gAgA_90CL",
              "3Cong_2025_m_ep_gAgA_90CL", "23Cong_2025_m_ep_gVgV_90CL",
              "3Cong_2025_m_ep_gpgp_90CL"]:
    EXCLUDED_FROM_ANALYSIS[_stem] = (
        "90% CL duplicate of the corresponding 95% CL Cong (2025) curve"
    )


# 5. The gpgs "combined" envelope curves, the gpgs analogue of the twelve
#    gAgV Combined curves in group 1 above. The source database records
#    all sixteen with interaction = "combined" and status = "review_only",
#    the same treatment it gives the gAgV envelopes. The local "1a" prefix
#    caused them to be read as V1a, which is what surfaced them: their
#    upstream records disagree with that label. Excluded on identical
#    grounds -- an envelope over several experiments has no single V_n.
for _sec in ["epgNs", "epges", "npgNs", "ppgNs"]:
    for _i in (1, 2, 3, 4):
        EXCLUDED_FROM_ANALYSIS["1ag%scombined%d_m_abs" % (_sec, _i)] = (
            "gpgs combined envelope curve; upstream marks it "
            "interaction=combined, status=review_only"
        )


def drop_excluded_from_analysis(datasets, verbose=True):
    """Split datasets into (kept, excluded) per EXCLUDED_FROM_ANALYSIS.

    Stamps each excluded dataset's .excluded_reason so the registry can
    record why it was held out, and returns both halves -- the registry
    needs the full set, the analysis needs only the kept ones.
    """
    kept, excluded = [], []
    for d in datasets:
        reason = EXCLUDED_FROM_ANALYSIS.get(d.filename)
        if reason is None:
            kept.append(d)
        else:
            d.excluded_reason = reason
            excluded.append(d)
    if verbose and excluded:
        print(f"[EXCLUDE] Held {len(excluded)} dataset(s) out of the analysis:")
        for d in excluded:
            print(f"    {d.filename:24s} -- {d.excluded_reason}")
    return kept, excluded


def drop_excluded_duplicates(datasets, verbose=True):
    """Remove the curves named in EXCLUDED_DUPLICATES, reporting each."""
    kept, dropped = [], []
    for d in datasets:
        reason = EXCLUDED_DUPLICATES.get(d.filename)
        if reason is None:
            kept.append(d)
        else:
            dropped.append((d, reason))
    if verbose and dropped:
        print(f"[CONSTRAINT] Excluded {len(dropped)} known duplicate curve(s):")
        for d, reason in dropped:
            print(f"    {d.filename}  --  {reason}")
    return kept


# ============================================================
# NORMALISATION
# ============================================================

# The second CSV column is not the same quantity across the database, and
# the two conventions differ by ~37 decades, so they get separate panels
# rather than a shared, mislabelled y-axis.
NORMALISATION_LABELS = {
    "g":     r"Coupling upper bound $|g|$",
    "alpha": r"Yukawa strength $|\alpha|$  (relative to gravity)",
}
NORMALISATION_TITLES = {"g": "", "alpha": r"gravity-normalised $\alpha$"}
NORMALISATION_SUFFIX = {"g": "", "alpha": "_alpha"}


# ============================================================
# STYLE CONSTANTS
# ============================================================

# Text/axis ink comes from print_style.INK; WHITE is the paper.
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
        # parser.load_dataset, not a second copy of the same few lines: the
        # inline version here silently missed the non-finite and
        # plot-sentinel handling added there, so the figures kept drawing
        # rows that the rest of the pipeline had already discarded.
        try:
            from .parser import load_dataset
        except ImportError:
            from parser import load_dataset

        df = load_dataset(dataset.filepath)

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


# Printed ink is always lighter than the same colour on screen -- the
# printer dithers it and the paper scatters it -- so the cap here is
# well below what looks necessary on a monitor.
MAX_PRINT_LUMINANCE = 0.45


def _readable_color(rgb):
    """Darken palette colours too light to survive printing, as either a
    curve or inline label text on the white axes background (many
    tab20b/c entries are near-pastel and reproduce as barely-there grey)."""
    r, g, b = rgb
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if lum > MAX_PRINT_LUMINANCE:
        factor = MAX_PRINT_LUMINANCE / lum
        r, g, b = r * factor, g * factor, b * factor
    return (r, g, b)


# Above this many curves the inline-label style of the source review
# (Cong et al. 2025, Figs. 15-16) stops working. It relies on curves being
# far enough apart that each label can sit beside its own curve; past a
# dozen, adjustText has to fling labels across the axes and draw leader
# lines to them, which is a legend doing a legend's job badly.
INLINE_LABEL_MAX = 12

# A few bounds in this dataset are published as analytic extrapolations
# running out to lambda ~ 1e47 m -- twenty decades past the observable
# universe (~1e26 m) -- and some span 300 decades in |g|. Autoscaling to
# them squeezes every real measurement into a corner of the canvas. The
# view is clipped to the range the bulk of the curves occupy instead.
# Nothing is dropped: clipped curves run off the edge, and the figure
# annotates how many do.
CLIP_MIN_SPAN_DECADES = 25     # narrower than this, leave the view alone
CLIP_COVERAGE_FRACTION = 0.15  # a decade is "occupied" if this many curves cross it
CLIP_PAD_DECADES = 0.5
CLIP_MIN_GAIN = 1.5            # only clip if it shrinks the span this much


def _dense_x_range(curves):
    """The lambda range holding the bulk of the curves, or None to autoscale.

    Returns (lo, hi) in metres. Decades crossed by fewer than
    CLIP_COVERAGE_FRACTION of the curves are trimmed from each end, keeping
    the contiguous run around the most-covered decade so the visible range
    never becomes two disjoint islands.
    """
    spans = []
    for lam, *_ in curves:
        lo, hi = float(np.min(lam)), float(np.max(lam))
        if lo > 0 and hi > lo:
            spans.append((math.log10(lo), math.log10(hi)))
    if len(spans) < 2:
        return None

    full_lo = min(s[0] for s in spans)
    full_hi = max(s[1] for s in spans)
    if full_hi - full_lo <= CLIP_MIN_SPAN_DECADES:
        return None

    decades = list(range(math.floor(full_lo), math.ceil(full_hi) + 1))
    counts  = [sum(1 for a, b in spans if a <= d + 1 and b >= d) for d in decades]
    needed  = max(2, math.ceil(CLIP_COVERAGE_FRACTION * len(spans)))

    peak = counts.index(max(counts))
    if counts[peak] < needed:
        return None

    i = j = peak
    while i > 0 and counts[i - 1] >= needed:
        i -= 1
    while j < len(decades) - 1 and counts[j + 1] >= needed:
        j += 1

    lo = decades[i] - CLIP_PAD_DECADES
    hi = decades[j] + 1 + CLIP_PAD_DECADES
    if (full_hi - full_lo) < CLIP_MIN_GAIN * (hi - lo):
        return None
    return 10.0 ** lo, 10.0 ** hi


def _y_range_within(curves, x_lo, x_hi, pad_decades=0.5):
    """Coupling range spanned inside the visible lambda window.

    Clipping x alone does not rescale y -- matplotlib still autoscales to
    the off-screen tail -- so y has to be recomputed from the points that
    remain visible.
    """
    lows, highs = [], []
    for lam, g, *_ in curves:
        visible = (lam >= x_lo) & (lam <= x_hi) & (g > 0)
        if visible.any():
            lows.append(float(np.min(g[visible])))
            highs.append(float(np.max(g[visible])))
    if not lows:
        return None
    return (10.0 ** (math.log10(min(lows)) - pad_decades),
            10.0 ** (math.log10(max(highs)) + pad_decades))


def _distinguishing_tokens(group):
    """Per member, the filename tokens that member does not share with the
    rest of its group.

    Appending a whole filename made legend entries up to 65 characters
    ("Safronova2018 (p-N, gpgs, 910Safronova_2018_Youdin_m_abs_pN)"), which
    forced the legend wider than the plot. Only the discriminating part is
    needed -- here, "Youdin" against "Kimball".
    """
    token_sets = [set(d.filename.split("_")) for d in group]
    shared = set.intersection(*token_sets) if token_sets else set()
    out = []
    for d in group:
        unique = [t for t in d.filename.split("_") if t not in shared]
        out.append(" ".join(unique) if unique else d.filename)
    return out


def _disambiguated_labels(dsets):
    """Curve labels that are unique within one panel.

    Source and sector alone collide whenever the same experiment is
    catalogued under several coupling classes -- and those copies are
    different bounds, not duplicates: gAgA and gVgV constrain different
    products of couplings, so their curves do not coincide. Qualifiers are
    appended, shortest-first, until every label is distinct; a legend with
    two identical entries for two different curves is worse than a longer
    label, but a needlessly long label costs page area, so each qualifier
    carries only the part that actually discriminates.
    """
    sectors = [SECTOR_LABELS.get(d.sector, d.sector) for d in dsets]
    quals   = [[] for _ in dsets]

    def render():
        return [f"{d.source} ({s}" + ("".join(", " + q for q in qs)) + ")"
                for d, s, qs in zip(dsets, sectors, quals)]

    def apply(qualifier_fn):
        """Qualify only the labels that still clash. Returns True when done."""
        labels   = render()
        clashing = {lab for lab in labels if labels.count(lab) > 1}
        if not clashing:
            return True
        groups = defaultdict(list)
        for i, lab in enumerate(labels):
            if lab in clashing:
                groups[lab].append(i)
        for idxs in groups.values():
            for i, q in zip(idxs, qualifier_fn([dsets[j] for j in idxs])):
                if q:
                    quals[i].append(str(q))
        return False

    qualifiers = (
        lambda group: [d.coupling for d in group],
        _distinguishing_tokens,
        lambda group: [Path(d.filepath).parent.name for d in group],
        # Last resort: indistinguishable from their metadata, so number them
        # rather than emit a legend with two entries that read alike.
        lambda group: [f"#{n}" for n in range(1, len(group) + 1)],
    )
    for qualifier in qualifiers:
        if apply(qualifier):
            break
    return render()


def _label_anchor(lam, g, x_lo, x_hi):
    """Rightmost point of a curve that is still inside the visible window."""
    inside = np.flatnonzero((lam >= x_lo) & (lam <= x_hi))
    k = int(inside[-1]) if inside.size else len(lam) - 1
    return lam[k], g[k]


def plot_single_potential(datasets_for_potential, potential, output_path,
                          coupling_label="g", title_suffix="", y_label=None):
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

    n_entries  = len(sorted_dsets)
    use_legend = n_entries > INLINE_LABEL_MAX

    if use_legend:
        # This canvas is the PLOT's size, not the finished image's: the
        # legend is attached below the axes and bbox_inches="tight" grows
        # the canvas around it at save time. Pinning it at a small fixed
        # size therefore shrank the axes twice over -- once directly, and
        # again as the legend claimed a share of the taller image -- which
        # left the curves squeezed into under half the frame. Grow it with
        # the curve count, as the inline branch does.
        fig_w = min(11 + 0.06 * n_entries, 18)
        fig_h = min(7 + 0.05 * n_entries, 11)
    else:
        # More curves need more room for inline labels to spread into.
        fig_w = min(11 + 0.09 * n_entries, 22)
        fig_h = min(7 + 0.07 * n_entries, 14)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_facecolor(WHITE)
    fig.patch.set_facecolor(WHITE)

    # Every size below is quoted as it should measure on the printed page;
    # `ps.pt()` scales it up by however much LaTeX will shrink this canvas.
    ps = PrintStyle(fig_w)

    labels_for = dict(zip(
        (id(d) for d in sorted_dsets), _disambiguated_labels(sorted_dsets)
    ))

    curves = []
    n_plotted = 0

    for i, d in enumerate(sorted_dsets):
        lam, g = _load_with_conversion(d)
        if lam is None or g is None or len(lam) < 2 or len(g) < 2:
            continue

        color     = _readable_color(DATASET_PALETTE[i % len(DATASET_PALETTE)])
        linestyle = "--" if d.sector in ANTIMATTER_SECTORS else "-"

        # Dashes are specified in on-page points too, so they stay
        # distinguishable from a solid line after the figure is scaled.
        kwargs = {}
        if linestyle == "--":
            kwargs["dashes"] = (ps.pt(3.6), ps.pt(1.8))

        # No alpha: translucency that reads as "slightly lighter" on screen
        # comes out of a printer as a broken, washed-out line.
        ax.plot(lam, g, color=color, linestyle=linestyle,
                linewidth=ps.pt(1.0), solid_capstyle="round", **kwargs)

        curves.append((lam, g, color, linestyle, labels_for[id(d)]))
        n_plotted += 1

    if n_plotted == 0:
        plt.close(fig)
        return

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Interaction range $\lambda$ (m)",
                  fontsize=ps.pt(9.5), color=INK)
    ax.set_ylabel(y_label or rf"Coupling upper bound $|{coupling_label}|$",
                  fontsize=ps.pt(9.5), color=INK)
    ax.set_title(
        rf"${potential}$ potential constraints{' — ' + title_suffix if title_suffix else ''}"
        f"  (solid = matter, dashed = antimatter)",
        fontsize=ps.pt(10.5), color=INK, pad=ps.pt(24)
    )

    # Secondary top axis: equivalent new-boson mass, m = hbar*c / lambda
    # (self-inverse formula, same function both directions).
    def _lambda_to_mass(lam):
        with np.errstate(divide="ignore"):
            return HBAR_C_EV_M / np.where(lam > 0, lam, np.nan)

    secax = ax.secondary_xaxis("top", functions=(_lambda_to_mass, _lambda_to_mass))
    secax.set_xlabel("Mass (eV)", fontsize=ps.pt(9), color=INK)
    secax.tick_params(labelsize=ps.pt(8), width=ps.pt(0.8),
                      length=ps.pt(3.5), color=INK, labelcolor=INK)
    secax.spines["top"].set_linewidth(ps.pt(0.8))
    secax.spines["top"].set_color(INK)

    # Clip the view to where the measurements actually are, before any
    # label is placed -- the anchors below depend on the visible window.
    clip     = _dense_x_range(curves)
    n_beyond = 0
    if clip is not None:
        x_lo, x_hi = clip
        ax.set_xlim(x_lo, x_hi)
        y_range = _y_range_within(curves, x_lo, x_hi)
        if y_range is not None:
            ax.set_ylim(*y_range)
        n_beyond = sum(1 for lam, *_ in curves
                       if float(np.max(lam)) > x_hi or float(np.min(lam)) < x_lo)
    else:
        x_lo, x_hi = ax.get_xlim()

    if use_legend:
        # Too many curves for inline labels: a legend below the axes, whose
        # frame is opaque for print, so it is anchored by its top edge at
        # the bottom of the figure rather than overlapping the x-axis.
        # bbox_inches="tight" at save time grows the canvas to include it.
        handles = []
        for _, _, color, linestyle, label in curves:
            h = mlines.Line2D([], [], color=color, linestyle=linestyle,
                              linewidth=ps.pt(1.4), label=label)
            if linestyle == "--":
                h.set_dashes((ps.pt(3.6), ps.pt(1.8)))
            handles.append(h)

        # Widest column count whose legend still fits inside the canvas.
        # A legend wider than the figure makes bbox_inches="tight" grow the
        # image sideways at save time, and the axes then occupy a smaller
        # fraction of the page for no gain -- at 5 columns the V4+5 legend
        # pushed the image to 21.7 in around 12.1 in of axes. Extra rows
        # cost far less page area than extra width, so narrow wins.
        def _add_legend(ncol):
            lg = fig.legend(handles=handles, loc="upper center",
                            bbox_to_anchor=(0.5, 0.0), ncol=ncol,
                            fontsize=ps.pt(7), framealpha=1.0,
                            edgecolor=INK, handlelength=ps.pt(2.2),
                            columnspacing=ps.pt(1.4))
            lg.get_frame().set_linewidth(ps.pt(0.6))
            return lg

        # The axes are a fixed size, so the column count that leaves them the
        # largest share of the page is simply the one that makes the whole
        # image smallest. Measure rather than guess: too few columns makes a
        # tall image, too many makes one wider than the plot, and which way
        # it goes depends on how long this panel's labels happen to be.
        legend, best_ncol, best_area = None, 1, None
        for ncol in range(1, min(6, len(handles)) + 1):
            if legend is not None:
                legend.remove()
            legend = _add_legend(ncol)
            fig.canvas.draw()
            bbox = fig.get_tightbbox(fig.canvas.get_renderer())
            area = bbox.width * bbox.height
            if best_area is None or area < best_area:
                best_area, best_ncol = area, ncol
        legend.remove()
        legend = _add_legend(best_ncol)
    else:
        # Inline labels anchored at each curve's rightmost visible point,
        # coloured to match the curve, with overlaps resolved automatically
        # (thin leader line where a label had to move away from its curve).
        texts = []
        for lam, g, color, _, label in curves:
            ax_x, ax_y = _label_anchor(lam, g, x_lo, x_hi)
            txt = ax.text(ax_x, ax_y, label, color=color,
                          fontsize=ps.pt(6.5), fontweight="bold")
            # Opaque halo: at this size a semi-transparent one lets the curve
            # underneath print through the glyph strokes and blur them.
            txt.set_path_effects([
                pe.withStroke(linewidth=ps.pt(1.6), foreground=WHITE)
            ])
            texts.append(txt)

        adjust_text(
            texts, ax=ax,
            arrowprops=dict(arrowstyle="-", color="#5a6470", lw=ps.pt(0.45)),
            expand_text=(1.3, 1.6), expand_points=(1.2, 1.4),
            force_text=(0.6, 1.0), force_points=(0.3, 0.5),
            lim=1500,
        )

    ps.apply(ax)

    # Annotation: dataset count, and an honest note when the axes hide
    # part of a curve's published range.
    # "datasets" overstated it: several curves are the same experiment
    # catalogued under a different coupling class, so the experiment count
    # is quoted alongside the curve count.
    n_experiments = len({d.source for d in sorted_dsets})
    note = (f"{n_plotted} curves from {n_experiments} experiments"
            if n_experiments != n_plotted else f"{n_plotted} curves")
    if n_beyond:
        plural = "s" if n_beyond != 1 else ""
        note += f"\naxes clipped: {n_beyond} curve{plural} continue beyond"
    ax.text(0.02, 0.02, note,
            transform=ax.transAxes, fontsize=ps.pt(7.5),
            color=INK, va="bottom")

    fig.tight_layout()
    save_figure(fig, output_path, style=ps)
    plt.close(fig)


# ============================================================
# FIGURE 2: MULTI-PANEL ATLAS (all potentials in one figure).
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

    # Panels sized so the whole grid is only a little wider than the page it
    # prints on. Drawing it at 5.5 in per panel meant a ~3.4x squeeze, and
    # text scaled up to survive that squeeze no longer fit inside a panel:
    # tick labels ran into each other and the axis labels were clipped.
    fig_w = ncols * 3.0
    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(fig_w, nrows * 2.5),
        squeeze=False
    )
    fig.patch.set_facecolor(WHITE)

    ps = PrintStyle(fig_w)

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

            color     = _readable_color(to_rgb(SECTOR_COLOURS.get(d.sector, "#888888")))
            linestyle = "--" if d.sector in ANTIMATTER_SECTORS else "-"

            kwargs = {}
            if linestyle == "--":
                kwargs["dashes"] = (ps.pt(3.0), ps.pt(1.5))

            ax.plot(lam, g, color=color, linestyle=linestyle,
                    linewidth=ps.pt(0.9), solid_capstyle="round", **kwargs)
            global_sectors.add(d.sector)
            n_plotted += 1

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"$V_{{{pot[1:]}}}$" if pot.startswith("V") else pot,
                     fontsize=ps.pt(9), color=INK, pad=ps.pt(3))

        # Minor grid off here: at panel size the decade ticks are close
        # enough together that minor lines print as a grey wash.
        ps.apply(ax, minor_grid=False)

        # A panel is a thumbnail, not a readable plot: a handful of ticks
        # marks the scale, and more would just overlap each other.
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(LogLocator(base=10, numticks=5))
            axis.set_minor_locator(NullLocator())
        ax.tick_params(which="major", labelsize=ps.pt(6.5))

        # Minimal axis labels only on edges
        if row == nrows - 1:
            ax.set_xlabel(r"$\lambda$ (m)", fontsize=ps.pt(8), color=INK)
        if col == 0:
            ax.set_ylabel("Coupling bound", fontsize=ps.pt(8), color=INK)

        ax.text(0.97, 0.97, f"N={n_plotted}",
                transform=ax.transAxes, fontsize=ps.pt(7),
                color=INK, ha="right", va="top")

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
            mlines.Line2D([], [], color=_readable_color(to_rgb(color)),
                          linestyle=ls, linewidth=ps.pt(1.4),
                          label=SECTOR_LABELS.get(sec, sec))
        )
    # Add style guide
    legend_handles += [
        mlines.Line2D([], [], color=INK, linestyle="-",
                      linewidth=ps.pt(1.6), label="Matter sector"),
        mlines.Line2D([], [], color=INK, linestyle="--",
                      linewidth=ps.pt(1.6), label="Antimatter sector"),
    ]

    # Anchored by its top edge at the bottom of the figure, so the whole
    # legend sits below the axes: its frame is opaque for print and would
    # otherwise cover the bottom row's x-axis labels. bbox_inches="tight"
    # at save time grows the canvas to include it.
    legend = fig.legend(handles=legend_handles,
                        loc="upper center",
                        bbox_to_anchor=(0.5, 0.0),
                        ncol=min(8, len(legend_handles)),
                        fontsize=ps.pt(8),
                        framealpha=1.0,
                        edgecolor=INK,
                        title="Fermion sector  (solid=matter, dashed=antimatter)",
                        title_fontsize=ps.pt(8))
    legend.get_frame().set_linewidth(ps.pt(0.6))

    fig.suptitle(
        "Spin-Dependent Exotic Interaction Constraint Atlas\n"
        r"Coupling upper bounds $|g|$ vs interaction range $\lambda$",
        fontsize=ps.pt(11), color=INK, y=1.01
    )

    fig.tight_layout(rect=(0, 0.02, 1, 1))
    save_figure(fig, output_path, style=ps)
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
    datasets     : list of ConstraintDataset (every compiled dataset)
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

    datasets = drop_excluded_duplicates(datasets)

    # Group by potential AND normalisation: |g| and |alpha| are different
    # quantities about 37 decades apart and cannot share a y-axis.
    by_panel = defaultdict(list)
    for d in datasets:
        if d.potential != "UNKNOWN":
            by_panel[(d.potential, d.normalisation)].append(d)

    panels = sorted(by_panel.keys(), key=lambda k: (pot_sort_key(k[0]), k[1]))

    print(f"\n[CONSTRAINT] Generating {len(panels)} per-potential panels...")

    # 1. Per-potential individual plots
    for pot, norm in panels:
        out = atlas_dir / f"constraint_{pot}{NORMALISATION_SUFFIX[norm]}.png"
        plot_single_potential(by_panel[(pot, norm)], pot, out,
                              title_suffix=NORMALISATION_TITLES[norm],
                              y_label=NORMALISATION_LABELS[norm])
        print(f"  [CONSTRAINT] {pot} [{norm}] "
              f"({len(by_panel[(pot, norm)])} curves) -> {out.name}")

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