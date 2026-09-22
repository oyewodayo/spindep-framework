# // plotting.py
import matplotlib.pyplot as plt

try:
    from .print_style import PrintStyle, apply_print_rcparams, save_figure, INK
except ImportError:
    from print_style import PrintStyle, apply_print_rcparams, save_figure, INK

apply_print_rcparams()

FIG_W = 10.0


def plot_asymmetry(
    lam,
    A,
    g_m,
    g_a,
    matter_ds,
    antimatter_ds,
    output_path
):

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(FIG_W, 8),
        sharex=True,
        gridspec_kw={"height_ratios": [2, 1]}
    )

    # Sizes below are the points these elements should measure once the
    # figure has been scaled down to the page; ps.pt() pre-compensates.
    ps = PrintStyle(FIG_W)

    # --------------------------------------------------------
    # TOP PANEL
    # --------------------------------------------------------

    ax1.loglog(
        lam,
        g_m,
        lw=ps.pt(1.4),
        color="#1f5c8b",
        solid_capstyle="round",
        label=f"Matter: {matter_ds.label}"
    )

    ax1.loglog(
        lam,
        g_a,
        lw=ps.pt(1.4),
        ls="--",
        dashes=(ps.pt(4.0), ps.pt(2.0)),
        color="#a4243b",
        label=f"Antimatter: {antimatter_ds.label}"
    )

    ax1.set_ylabel("Coupling upper bound", fontsize=ps.pt(9.5), color=INK)

    ax1.set_title(
        f"{matter_ds.coupling} | "
        f"{matter_ds.potential} | "
        f"{matter_ds.sector}",
        fontsize=ps.pt(10.5), color=INK
    )

    ps.apply(ax1)

    leg1 = ax1.legend(fontsize=ps.pt(8), framealpha=1.0, edgecolor=INK)
    leg1.get_frame().set_linewidth(ps.pt(0.6))

    # --------------------------------------------------------
    # BOTTOM PANEL
    # --------------------------------------------------------

    ax2.semilogx(
        lam,
        A,
        lw=ps.pt(1.4),
        color="#b3541e",
        solid_capstyle="round"
    )

    ax2.axhline(0, color=INK, ls="--", lw=ps.pt(0.7))

    # The fills mark which side is weaker; kept light so they read as
    # background shading rather than competing with the curve.
    ax2.fill_between(
        lam,
        A,
        0,
        where=(A > 0),
        alpha=0.18,
        color="#1f5c8b",
        linewidth=0,
        label="Matter weaker"
    )

    ax2.fill_between(
        lam,
        A,
        0,
        where=(A < 0),
        alpha=0.18,
        color="#a4243b",
        linewidth=0,
        label="Antimatter weaker"
    )

    ax2.set_xlabel(r"Interaction range $\lambda$ (m)",
                   fontsize=ps.pt(9.5), color=INK)

    ax2.set_ylabel(r"$A_\alpha$", fontsize=ps.pt(9.5), color=INK)

    ax2.set_ylim(-1.1, 1.1)

    ps.apply(ax2)

    leg2 = ax2.legend(fontsize=ps.pt(8), framealpha=1.0, edgecolor=INK)
    leg2.get_frame().set_linewidth(ps.pt(0.6))

    plt.tight_layout()

    save_figure(fig, output_path, style=ps)

    plt.close(fig)
