# // print_style.py
r"""
Print-quality figure styling for thesis/journal output.

WHY THIS EXISTS
---------------
Figures here are drawn on a canvas much wider than the page they end up
on: the V1a atlas is ~13.4 in wide, but LaTeX scales it down to the
~6.5 in text width. Everything shrinks with it, so a 1.3 pt curve prints
as 0.62 pt, a 0.5 pt grid line prints as 0.24 pt (a hairline no laser
printer reliably puts on paper -- it simply disappears), and 7.5 pt
labels print as 3.6 pt.

The fix is to pre-compensate: decide the sizes we want *on the printed
page*, then multiply them by the scale factor the page will later divide
them by. `PrintStyle` does that arithmetic once per figure, so call sites
just ask for on-page points and get canvas points back.

Use `save_figure()` to write output -- it emits a vector PDF alongside
the PNG, and the PDF is what should go into \includegraphics: vector
line art stays sharp at any size and never carries resampling mush.
"""

from pathlib import Path
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator

# Width the figure occupies on the printed page, in inches. The default is
# a standard LaTeX \textwidth for a one-sided thesis at 12pt/A4. Measure
# yours with \the\textwidth (1 in = 72.27 pt) and override if it differs;
# if a figure is included at \0.8\textwidth, pass that product instead.
TARGET_PAGE_WIDTH_IN = 6.5

# Resolution the PNG should resolve to *on the printed page*. 300 dpi is the
# usual print minimum. The canvas dpi needed to reach it is lower than this
# whenever the figure is drawn wider than its printed placement, so
# `save_figure` divides by the scale factor rather than using this directly
# -- setting 600 dpi on a 22 in canvas would produce a 13000 px PNG for no
# gain on paper. The PDF is resolution-independent and is the one to include.
TARGET_PAGE_DPI = 300

# Floor for the computed canvas dpi, so a heavily-scaled figure still has
# enough pixels to look right on screen and in on-screen PDF review.
MIN_CANVAS_DPI = 200

# Ink colours. Pure black for text beats a navy tint once a page goes
# through a greyscale printer, which lightens every colour it dithers.
INK        = "#101820"
GRID_MAJOR = "#9099a3"   # mid grey: visible at 0.5 pt, not competing with data
GRID_MINOR = "#c7ccd2"
WHITE      = "#ffffff"


class PrintStyle:
    """On-page sizes in points -> canvas sizes in points.

    `s` is how much larger the canvas is than its printed placement, so
    multiplying by it cancels the later shrink exactly.
    """

    def __init__(self, fig_width_in, page_width_in=TARGET_PAGE_WIDTH_IN):
        # Never scale below 1: a figure narrower than the text column is
        # enlarged by LaTeX, and thinning the ink to compensate would
        # undo the point of this module.
        self.s = max(1.0, fig_width_in / page_width_in)

    def pt(self, on_page_points):
        """Line width or font size, given in points as it should print."""
        return on_page_points * self.s

    def apply(self, ax, *, grid=True, minor_grid=True):
        """Spines, ticks and grid at print-legible weights."""
        _tame_extreme_log_axes(ax)

        for spine in ax.spines.values():
            spine.set_linewidth(self.pt(0.8))
            spine.set_color(INK)

        ax.tick_params(which="major", length=self.pt(3.5),
                       width=self.pt(0.8), color=INK,
                       labelsize=self.pt(8), labelcolor=INK)
        ax.tick_params(which="minor", length=self.pt(2.0),
                       width=self.pt(0.6), color=INK)

        if grid:
            # Solid, not dotted: a dotted line thinner than ~0.5 pt breaks
            # into dots too small to survive printing. Drawn under the data.
            ax.grid(True, which="major", linestyle="-",
                    linewidth=self.pt(0.5), color=GRID_MAJOR, alpha=1.0)
            if minor_grid:
                # Per axis, because a log axis covering many decades packs
                # nine minor lines into each one and they read as a grey
                # wash rather than as a reference grid.
                for name in ("x", "y"):
                    if _log_decades(ax, name) <= MAX_MINOR_GRID_DECADES:
                        ax.grid(True, which="minor", axis=name, linestyle="-",
                                linewidth=self.pt(0.35), color=GRID_MINOR,
                                alpha=1.0)
            ax.set_axisbelow(True)


# Beyond this many decades matplotlib's default LogLocator asks for more
# ticks than the range can express: it evaluates 10**decade for decades
# past the float ceiling, gets inf, and then raises OverflowError trying
# to format those ticks. Some potentials here really do span 300 decades.
MAX_AUTO_LOG_DECADES = 50

# Above this span, minor gridlines stop being readable as separate lines:
# each decade carries nine of them, so even a 7-decade axis lays down ~60
# verticals that print as shading. Wide log axes get major gridlines only.
MAX_MINOR_GRID_DECADES = 3


def _log_decades(ax, axis_name):
    """Decades spanned by a log axis; 0 for a linear one, where minor
    gridlines stay useful however wide the range."""
    axis = ax.xaxis if axis_name == "x" else ax.yaxis
    if axis.get_scale() != "log":
        return 0.0
    lo, hi = ax.get_xlim() if axis_name == "x" else ax.get_ylim()
    if lo <= 0 or hi <= 0:
        return 0.0
    return abs(math.log10(hi) - math.log10(lo))


def _tame_extreme_log_axes(ax, max_decades=MAX_AUTO_LOG_DECADES):
    """Give very wide log axes a bounded tick locator.

    Only the tick *locator* changes -- limits and data are untouched, so
    nothing is hidden; an axis this wide simply cannot carry a tick per
    decade anyway.
    """
    ax.autoscale_view()
    for axis, (lo, hi) in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
        if axis.get_scale() != "log" or lo <= 0 or hi <= 0:
            continue
        if math.log10(hi) - math.log10(lo) <= max_decades:
            continue
        axis.set_major_locator(LogLocator(base=10, numticks=8))
        axis.set_minor_locator(LogLocator(base=10, subs=(1.0,), numticks=8))


def apply_print_rcparams():
    """Global defaults that make every figure print cleanly.

    Call once at import time in each plotting module.
    """
    plt.rcParams.update({
        # Embed real TrueType fonts rather than Type 3 subsets, which many
        # journal/thesis submission checkers reject outright.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "savefig.facecolor": WHITE,
        "figure.facecolor": WHITE,
        "axes.facecolor": WHITE,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "axes.unicode_minus": False,
    })


def save_figure(fig, output_path, *, style=None, target_page_dpi=TARGET_PAGE_DPI,
                dpi=None, also_pdf=True):
    """Write `output_path` plus a vector PDF sibling.

    Pass the figure's `PrintStyle` as `style` to have the raster resolution
    derived from how much the page will shrink the canvas; pass `dpi` to set
    the canvas resolution outright. Returns the paths written -- include the
    .pdf in LaTeX.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if dpi is None:
        scale = style.s if style is not None else 1.0
        dpi = max(MIN_CANVAS_DPI, round(target_page_dpi / scale))

    written = []
    common = dict(bbox_inches="tight", pad_inches=0.05, facecolor=WHITE)

    fig.savefig(output_path, dpi=dpi, **common)
    written.append(output_path)

    if also_pdf and output_path.suffix.lower() != ".pdf":
        pdf_path = output_path.with_suffix(".pdf")
        fig.savefig(pdf_path, **common)
        written.append(pdf_path)

    return written
