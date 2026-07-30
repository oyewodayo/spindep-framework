# // reporting.py
from pathlib import Path
from datetime import datetime

import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, HRFlowable, PageBreak,
    KeepTogether
)

NAVY    = colors.HexColor("#1a2e4a")
STEEL   = colors.HexColor("#2d6a9f")
CRIMSON = colors.HexColor("#b03a2e")
LIGHT   = colors.HexColor("#f4f6f9")
MID     = colors.HexColor("#dce3ed")
WHITE   = colors.white


def build_styles():
    styles = {}
    styles["cover_title"] = ParagraphStyle(
        "cover_title", fontSize=26, leading=32, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=8)
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub", fontSize=13, leading=18, textColor=MID,
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4)
    styles["section_header"] = ParagraphStyle(
        "section_header", fontSize=14, leading=18, textColor=NAVY,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=4)
    styles["pair_header"] = ParagraphStyle(
        "pair_header", fontSize=11, leading=14, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_LEFT)
    styles["body"] = ParagraphStyle(
        "body", fontSize=9, leading=13,
        textColor=colors.HexColor("#2c2c2c"),
        fontName="Helvetica", spaceAfter=4)
    styles["caption"] = ParagraphStyle(
        "caption", fontSize=8, leading=11,
        textColor=colors.HexColor("#555555"),
        fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=6)
    styles["warn"] = ParagraphStyle(
        "warn", fontSize=8, leading=11, textColor=CRIMSON,
        fontName="Helvetica-Oblique")
    styles["footer"] = ParagraphStyle(
        "footer", fontSize=7, leading=10,
        textColor=colors.HexColor("#888888"),
        fontName="Helvetica", alignment=TA_CENTER)
    return styles


class ReportCanvas:
    def __init__(self, title, total_pairs):
        self.title       = title
        self.total_pairs = total_pairs

    def on_page(self, canvas, doc):
        canvas.saveState()
        W, H = A4
        if doc.page > 1:
            canvas.setFillColor(NAVY)
            canvas.rect(0, H - 1.1*cm, W, 1.1*cm, fill=1, stroke=0)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.setFillColor(WHITE)
            canvas.drawString(1.2*cm, H - 0.72*cm, self.title)
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(MID)
            canvas.drawRightString(W - 1.2*cm, H - 0.72*cm,
                "Spin-Dependent Exotic Interactions — Asymmetry Analysis")
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, W, 0.8*cm, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MID)
        canvas.drawString(1.2*cm, 0.27*cm,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        canvas.drawCentredString(W / 2, 0.27*cm, f"Page {doc.page}")
        canvas.drawRightString(W - 1.2*cm, 0.27*cm,
            f"{self.total_pairs} matter-antimatter pairs analysed")
        canvas.restoreState()


def significance_label(p_value):
    if p_value < 0.001:   return "***  (p < 0.001)"
    elif p_value < 0.01:  return "**   (p < 0.01)"
    elif p_value < 0.05:  return "*    (p < 0.05)"
    else:                 return "ns   (p >= 0.05)"


def asymmetry_interpretation(mean_abs_A):
    if mean_abs_A > 0.5:    return "Strong asymmetry — large CPT-sensitive difference."
    elif mean_abs_A > 0.2:  return "Moderate asymmetry — measurable matter/antimatter difference."
    elif mean_abs_A > 0.05: return "Weak asymmetry — marginal difference within constraints."
    else:                   return "Near-symmetric — matter and antimatter bounds are consistent."


# ============================================================
# COVER PAGE
# ============================================================

def build_cover(styles, total_pairs, skipped, timestamp):
    W, H = A4
    story = []
    cover_table = Table(
        [[Paragraph("Spin-Dependent Exotic Interactions", styles["cover_title"])],
         [Paragraph("Matter–Antimatter Asymmetry Analysis Report", styles["cover_sub"])],
         [Spacer(1, 0.3*cm)],
         [Paragraph(f"Generated: {timestamp}", styles["cover_sub"])]],
        colWidths=[W - 4*cm],
    )
    cover_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 18),
        ("BOTTOMPADDING", (0,0), (-1,-1), 18),
        ("LEFTPADDING",   (0,0), (-1,-1), 24),
        ("RIGHTPADDING",  (0,0), (-1,-1), 24),
    ]))
    story.append(Spacer(1, 2*cm))
    story.append(cover_table)
    story.append(Spacer(1, 1*cm))

    stats_data = [
        ["Metric", "Value"],
        ["Pairs analysed",     str(total_pairs)],
        ["Pairs skipped",      str(skipped)],
        ["Analysis timestamp", timestamp],
        ["Framework",          "SPINDEP v1.0"],
        ["Method",             "log-interpolated chi-squared asymmetry"],
        ["Chi-squared modes",  "Uniform (10%) + Weighted (per-point curvature)"],
    ]
    stats_table = Table(stats_data, colWidths=[6*cm, 9*cm])
    stats_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), STEEL),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
        ("GRID",          (0,0), (-1,-1), 0.4, MID),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(stats_table)
    story.append(PageBreak())
    return story


# ============================================================
# SUMMARY TABLE
# ============================================================

def build_summary_table(rows, styles):
    story = []
    story.append(Paragraph("Summary of All Pairs", styles["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=STEEL, spaceAfter=8))

    headers = [
        "Coupling", "Potential", "Sector",
        "Matter", "Antimatter",
        "|A| mean", "χ² weighted", "dof_eff", "p-value (dof_eff)"
    ]
    col_w = [2.0*cm, 1.6*cm, 1.4*cm, 2.8*cm, 2.8*cm,
             1.5*cm, 2.0*cm, 1.6*cm, 2.3*cm]

    data = [headers]
    for r in rows:
        pval_eff = r.get("p_value_weighted_eff", r.get("p_value_weighted", r.get("p_value", 0)))
        dof_eff  = r.get("dof_effective", r.get("dof", 300))
        p_label  = significance_label(pval_eff)[:2].strip()
        data.append([
            r["coupling"],
            r["potential"],
            r["sector"],
            r["matter_source"],
            r["antimatter_source"],
            f"{r['mean_abs_A']:.3f}",
            f"{r.get('chi2_weighted', r.get('chi2', 0)):.0f}",
            f"{int(dof_eff)}",
            f"{pval_eff:.2e} {p_label}",
        ])

    tbl = Table(data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 7),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
        ("GRID",          (0,0), (-1,-1), 0.3, MID),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ("RIGHTPADDING",  (0,0), (-1,-1), 4),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND",    (7,0), (7,0),  STEEL),
        ("BACKGROUND",    (7,1), (7,-1), colors.HexColor("#eaf0f8")),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "χ² uniform: 10% fractional uncertainty applied uniformly. "
        "χ² weighted: per-point uncertainty estimated from log-log curvature of constraint curve. "
        "p-value shown for weighted method. *** p < 0.001.",
        styles["body"]
    ))
    # NO PageBreak here — let content flow naturally
    return story


# ============================================================
# PER-PAIR SECTION
# key fix: PageBreak at the START (except first), not at end
# ============================================================

def build_pair_section(row, plot_path, styles, pair_index, total_pairs):
    story = []

    # PageBreak BEFORE each pair section (not after)
    # This prevents the blank page that occurs when the plot
    # exactly fills the previous page.
    story.append(PageBreak())

    banner_text = (
        f"Pair {pair_index}/{total_pairs}  |  "
        f"{row['coupling']}  ·  {row['potential']}  ·  {row['sector']}"
    )
    banner = Table(
        [[Paragraph(banner_text, styles["pair_header"])]],
        colWidths=["100%"],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), STEEL),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
    ]))
    story.append(KeepTogether([banner, Spacer(1, 0.3*cm)]))

    # Source / metadata table
    source_data = [
        [Paragraph("<b>Matter dataset</b>",     styles["body"]),
         Paragraph(row["matter_source"],         styles["body"]),
         Paragraph("<b>Antimatter dataset</b>",  styles["body"]),
         Paragraph(row["antimatter_source"],     styles["body"])],
        [Paragraph("<b>Interaction class</b>",   styles["body"]),
         Paragraph(row["interaction_class"],     styles["body"]),
         Paragraph("<b>Lambda range</b>",        styles["body"]),
         Paragraph(
             f"{row['lambda_min']:.2e} – {row['lambda_max']:.2e} m",
             styles["body"])],
        [Paragraph("<b>Matter unit</b>",         styles["body"]),
         Paragraph(row.get("matter_unit", "m"),  styles["body"]),
         Paragraph("<b>Antimatter unit</b>",     styles["body"]),
         Paragraph(row.get("antimatter_unit","m"), styles["body"])],
    ]
    src_tbl = Table(source_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    src_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT),
        ("GRID",          (0,0), (-1,-1), 0.3, MID),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(src_tbl)
    story.append(Spacer(1, 0.35*cm))

    # Statistics table
    p_u   = row.get("p_value_uniform",  row.get("p_value", 0))
    p_w   = row.get("p_value_weighted", row.get("p_value", 0))
    c_u   = row.get("chi2_uniform",     row.get("chi2",    0))
    c_w   = row.get("chi2_weighted",    row.get("chi2",    0))
    dof     = row.get("dof", 300)
    dof_eff = row.get("dof_effective", dof)
    p_w_eff = row.get("p_value_weighted_eff", p_w)
    autocorr = row.get("autocorr_length", 1.0)
    ci_lo   = row.get("aalpha_ci_low")
    ci_hi   = row.get("aalpha_ci_high")
    A     = row["mean_abs_A"]
    sm    = row.get("mean_sigma_m_pct", 10.0)
    sa    = row.get("mean_sigma_a_pct", 10.0)
    ratio = row.get("chi2_ratio", 1.0)

    ci_str = f"[{ci_lo:.4f}, {ci_hi:.4f}]" if ci_lo is not None and ci_hi is not None else "n/a"

    metrics_data = [
        ["Statistic", "Value", "Interpretation"],
        ["Mean |A_alpha|",        f"{A:.4f}",       asymmetry_interpretation(A)],
        ["|A_alpha| 95% CI",      ci_str,           "Bootstrap CI (see statistics.py)"],
        ["chi2 (uniform 10%)",    f"{c_u:.1f}",     f"dof = {int(dof)}  {significance_label(p_u)}"],
        ["chi2 (weighted)",       f"{c_w:.1f}",     f"dof = {int(dof)}  {significance_label(p_w)}"],
        ["p-value (uniform)",     f"{p_u:.4e}",     ""],
        ["p-value (weighted)",    f"{p_w:.4e}",     "Nominal — assumes all grid points independent"],
        ["dof (effective)",       f"{int(dof_eff)}", f"autocorrelation length = {autocorr:.1f} grid pts"],
        ["p-value (effective dof)", f"{p_w_eff:.4e}", f"{significance_label(p_w_eff)}  — preferred for thesis"],
        ["chi2 ratio (w/u)",      f"{ratio:.3f}",   "< 1 means weighted is more conservative"],
        ["Mean sigma_matter",     f"{sm:.1f}%",     "Per-point uncertainty from curve curvature"],
        ["Mean sigma_antimatter", f"{sa:.1f}%",     "Per-point uncertainty from curve curvature"],
        ["lambda min",            f"{row['lambda_min']:.3e} m", ""],
        ["lambda max",            f"{row['lambda_max']:.3e} m", ""],
    ]
    met_tbl = Table(metrics_data, colWidths=[4.5*cm, 3.5*cm, 10.0*cm])
    met_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
        ("GRID",          (0,0), (-1,-1), 0.3, MID),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("BACKGROUND",    (0,3), (-1,3), colors.HexColor("#eaf0f8")),
        ("BACKGROUND",    (0,5), (-1,5), colors.HexColor("#eaf0f8")),
    ]))
    story.append(met_tbl)
    story.append(Spacer(1, 0.4*cm))


    # After the statistics table:
    if row.get("potential") in ("V3", "V3a") and row.get("coupling") == "gAgA":
        story.append(Paragraph(
            "⚠ NOTE: V₃ under gAgA coupling diverges as λ² at small boson mass "
            "(Cong et al. 2025, Eq. 48–52). The f₃ coefficient in raw datasets "
            "must be converted to physical gAgA before comparing with other potentials. "
            "Values shown are raw digitised constraint curves — apply Table VI correction "
            "before citing.",
            styles["warn"]
        ))

    # Plot
    if plot_path and Path(plot_path).exists():
        img = Image(str(plot_path), width=16*cm, height=12.8*cm)
        caption = Paragraph(
            f"Figure: Coupling upper bounds vs interaction range λ (top panel) "
            f"and asymmetry parameter A<sub>α</sub> (bottom panel) for the "
            f"{row['sector']} sector under {row['potential']} potential. "
            f"Shaded region shows combined uncertainty band from weighted analysis.",
            styles["caption"]
        )
        story.append(KeepTogether([img, caption]))
    else:
        story.append(Paragraph("[Plot not available]", styles["warn"]))

    # NO PageBreak at the end — content flows naturally to next pair
    return story


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def generate_report(summary_rows, plots_dir, output_path):
    plots_dir   = Path(plots_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles    = build_styles()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_pairs = len(summary_rows)

    def plot_path_for(row):
        name = (
            f"{row['coupling']}_{row['potential']}_"
            f"{row['sector']}_{row['matter_filename']}.png"
        )
        p = plots_dir / name
        return p if p.exists() else None

    skipped = sum(1 for r in summary_rows if plot_path_for(r) is None)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.6*cm, bottomMargin=1.4*cm,
        title="Spin-Dependent Exotic Interactions — Asymmetry Report",
        author="SPINDEP Framework",
    )
    rc = ReportCanvas(
        title=f"SPINDEP Analysis  |  {timestamp}",
        total_pairs=total_pairs,
    )

    story  = []
    story += build_cover(styles, total_pairs, skipped, timestamp)
    story += build_summary_table(summary_rows, styles)

    for idx, row in enumerate(summary_rows, start=1):
        pp = plot_path_for(row)
        story += build_pair_section(row, pp, styles, idx, total_pairs)

    doc.build(story, onFirstPage=rc.on_page, onLaterPages=rc.on_page)
    print(f"[REPORT] Saved → {output_path}")
    return output_path