# // reporting.py
from pathlib import Path
from datetime import datetime

from PIL import Image as PILImage

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
MUTED   = colors.HexColor("#6b7280")
WHITE   = colors.white

PAGE_W, PAGE_H  = A4
LEFT_MARGIN     = 1.8 * cm
RIGHT_MARGIN    = 1.8 * cm
TOP_MARGIN      = 1.6 * cm
BOTTOM_MARGIN   = 1.4 * cm
CONTENT_WIDTH   = PAGE_W - LEFT_MARGIN - RIGHT_MARGIN   # 17.4 cm
CONTENT_HEIGHT  = PAGE_H - TOP_MARGIN - BOTTOM_MARGIN    # 26.7 cm


def build_styles():
    styles = {}
    styles["cover_title"] = ParagraphStyle(
        "cover_title", fontSize=23, leading=28, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=6)
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub", fontSize=12, leading=16, textColor=MID,
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=3)
    styles["cover_abstract"] = ParagraphStyle(
        "cover_abstract", fontSize=9.5, leading=14, textColor=colors.HexColor("#444444"),
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=0)
    styles["tile_number"] = ParagraphStyle(
        "tile_number", fontSize=18, leading=22, textColor=NAVY,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=1)
    styles["tile_label"] = ParagraphStyle(
        "tile_label", fontSize=7.5, leading=10, textColor=MUTED,
        fontName="Helvetica", alignment=TA_CENTER)
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
    styles["small"] = ParagraphStyle(
        "small", fontSize=7.5, leading=10,
        textColor=colors.HexColor("#2c2c2c"),
        fontName="Helvetica")
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
    def __init__(self, title, total_pairs, timestamp):
        self.title       = title
        self.total_pairs = total_pairs
        self.timestamp   = timestamp

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
        canvas.drawString(1.2*cm, 0.27*cm, f"Generated: {self.timestamp}")
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


def _pval_eff(row):
    return row.get("p_value_weighted_eff", row.get("p_value_weighted", row.get("p_value", 0)))


def _tile(number, label, styles):
    """One stat tile for the cover page: a big number over a small caption."""
    cell = [
        Paragraph(str(number), styles["tile_number"]),
        Paragraph(label, styles["tile_label"]),
    ]
    tbl = Table([[cell[0]], [cell[1]]], colWidths=[CONTENT_WIDTH / 4 - 0.3*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT),
        ("BOX",           (0,0), (-1,-1), 0.6, MID),
        ("TOPPADDING",    (0,0), (0,0), 10),
        ("BOTTOMPADDING", (0,0), (0,0), 2),
        ("TOPPADDING",    (0,1), (0,1), 0),
        ("BOTTOMPADDING", (0,1), (0,1), 10),
    ]))
    return tbl


def _sized_image(path, max_width, max_height):
    """Return (width, height) in points that preserve the source image's
    aspect ratio while fitting within max_width x max_height."""
    with PILImage.open(path) as im:
        px_w, px_h = im.size
    aspect = px_w / px_h
    width, height = max_width, max_width / aspect
    if height > max_height:
        height = max_height
        width = height * aspect
    return width, height


# ============================================================
# COVER PAGE
# ============================================================

def build_cover(styles, summary_rows, skipped, timestamp):
    total_pairs = len(summary_rows)
    n_significant = sum(1 for r in summary_rows if _pval_eff(r) < 0.001)
    n_couplings   = len({r["coupling"] for r in summary_rows}) if summary_rows else 0

    story = []
    story.append(Spacer(1, 3.2*cm))

    title_table = Table(
        [[Paragraph("Spin-Dependent Exotic Interactions", styles["cover_title"])],
         [Paragraph("Matter–Antimatter Asymmetry Analysis Report", styles["cover_sub"])],
         [Spacer(1, 0.25*cm)],
         [Paragraph(f"Generated: {timestamp}", styles["cover_sub"])]],
        colWidths=[CONTENT_WIDTH],
    )
    title_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 16),
        ("BOTTOMPADDING", (0,0), (-1,-1), 16),
        ("LEFTPADDING",   (0,0), (-1,-1), 24),
        ("RIGHTPADDING",  (0,0), (-1,-1), 24),
    ]))
    story.append(title_table)
    story.append(Spacer(1, 1.0*cm))

    story.append(Paragraph(
        f"This report compares experimental coupling-constant upper bounds between "
        f"matter and antimatter sectors across {total_pairs} matched dataset pairs, "
        f"computing the CPT asymmetry parameter A<sub>α</sub> and its statistical "
        f"significance for each.",
        styles["cover_abstract"]
    ))
    story.append(Spacer(1, 0.8*cm))

    tiles = [
        _tile(total_pairs,   "Pairs Analysed",             styles),
        _tile(n_significant, "Significant at p &lt; 0.001", styles),
        _tile(n_couplings,   "Coupling Families",           styles),
        _tile(skipped,       "Pairs Skipped",               styles),
    ]
    tile_row = Table([tiles], colWidths=[CONTENT_WIDTH/4]*4)
    tile_row.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
    ]))
    story.append(tile_row)
    story.append(Spacer(1, 1.4*cm))

    story.append(Paragraph(
        "Framework: SPINDEP v1.0  &nbsp;·&nbsp;  "
        "Method: log-interpolated χ² asymmetry test  &nbsp;·&nbsp;  "
        "Modes: uniform (10%) and per-point weighted uncertainty",
        styles["caption"]
    ))

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
    col_w = [1.8*cm, 1.6*cm, 1.3*cm, 2.6*cm, 2.6*cm,
             1.5*cm, 2.0*cm, 1.6*cm, 2.4*cm]
    assert abs(sum(col_w) - CONTENT_WIDTH) < 0.05*cm

    data = [headers]
    for r in rows:
        pval_eff = _pval_eff(r)
        dof_eff  = r.get("dof_effective", r.get("dof", 300))
        p_label  = significance_label(pval_eff)[:3].strip()
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
        "p-value shown for weighted method against the effective (autocorrelation-corrected) dof. "
        "*** p &lt; 0.001.",
        styles["body"]
    ))

    if rows:
        n_strong = sum(1 for r in rows if r["mean_abs_A"] > 0.5)
        n_sig    = sum(1 for r in rows if _pval_eff(r) < 0.001)
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Key Observations", styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.75, color=MID, spaceAfter=6))
        story.append(Paragraph(
            f"Of the {len(rows)} pairs analysed, {n_strong} show strong asymmetry "
            f"(|A<sub>α</sub>| &gt; 0.5) and {n_sig} are statistically significant at "
            f"p &lt; 0.001 under the effective-dof weighted test. An asymmetry value near "
            f"unity computed from one-sided experimental upper bounds is <i>consistent "
            f"with</i>, but not proof of, genuine CPT violation: the same pattern arises "
            f"from a sensitivity gap between the matter- and antimatter-sector "
            f"measurements being compared, independent of the true CPT status of the "
            f"underlying physics. Per-pair diagnostics for distinguishing the two follow.",
            styles["body"]
        ))
    return story


# ============================================================
# PER-PAIR SECTION — designed to fit on a single page
# ============================================================

def build_pair_section(row, plot_path, styles, pair_index, total_pairs):
    story = [PageBreak()]

    banner_text = (
        f"Pair {pair_index}/{total_pairs}  |  "
        f"{row['coupling']}  ·  {row['potential']}  ·  {row['sector']}"
    )
    banner = Table([[Paragraph(banner_text, styles["pair_header"])]], colWidths=[CONTENT_WIDTH])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), STEEL),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.25*cm))

    # Identity / provenance table
    source_data = [
        [Paragraph("<b>Matter</b>",              styles["body"]),
         Paragraph(row["matter_source"],         styles["body"]),
         Paragraph("<b>Antimatter</b>",           styles["body"]),
         Paragraph(row["antimatter_source"],     styles["body"])],
        [Paragraph("<b>Interaction class</b>",   styles["body"]),
         Paragraph(row["interaction_class"],     styles["body"]),
         Paragraph("<b>Lambda range</b>",        styles["body"]),
         Paragraph(
             f"{row['lambda_min']:.2e} – {row['lambda_max']:.2e} m",
             styles["body"])],
        [Paragraph("<b>Units</b>", styles["body"]),
         Paragraph(f"{row.get('matter_unit', 'm')} / {row.get('antimatter_unit', 'm')}"
                    f" (matter / anti.)", styles["body"]),
         Paragraph("", styles["body"]),
         Paragraph("", styles["body"])],
    ]
    src_tbl = Table(source_data, colWidths=[3.2*cm, 5.5*cm, 3.2*cm, 5.5*cm])
    src_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT),
        ("GRID",          (0,0), (-1,-1), 0.3, MID),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(src_tbl)
    story.append(Spacer(1, 0.3*cm))

    # Statistics table — one row per statistical question, not per number,
    # so the whole pair fits on one page alongside its plot.
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
        ["Statistic", "Value", "Note"],
        ["Mean |A_alpha|  (95% CI)",
         f"{A:.4f}   {ci_str}",
         asymmetry_interpretation(A)],
        ["p-value, effective dof — preferred",
         f"{p_w_eff:.3e}",
         f"{significance_label(p_w_eff)}   (chi2={c_w:.1f}, dof_eff={int(dof_eff)}, "
         f"autocorr={autocorr:.0f} pts)"],
        ["p-value, uniform 10%",
         f"{p_u:.3e}",
         f"{significance_label(p_u)}   (chi2={c_u:.1f}, dof={int(dof)})"],
        ["chi2 ratio (weighted / uniform)",
         f"{ratio:.3f}",
         "< 1 means the weighted analysis is more conservative"],
        ["Mean sigma  (matter / antimatter)",
         f"{sm:.1f}%  /  {sa:.1f}%",
         "Per-point uncertainty from constraint-curve curvature"],
        ["Lambda range",
         f"{row['lambda_min']:.3e} – {row['lambda_max']:.3e} m",
         ""],
    ]
    met_tbl = Table(metrics_data, colWidths=[4.6*cm, 4.4*cm, 8.4*cm])
    met_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
        ("GRID",          (0,0), (-1,-1), 0.3, MID),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
        ("TOPPADDING",    (0,0), (-1,-1), 3.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3.5),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND",    (0,1), (-1,1), colors.HexColor("#eaf0f8")),
    ]))
    story.append(met_tbl)
    story.append(Spacer(1, 0.3*cm))

    if row.get("potential") in ("V3", "V3a") and row.get("coupling") == "gAgA":
        story.append(Paragraph(
            "⚠ NOTE: V₃ under gAgA coupling diverges as λ² at small boson mass "
            "(Cong et al. 2025, Eq. 48–52). The f₃ coefficient in raw datasets "
            "must be converted to physical gAgA before comparing with other potentials. "
            "Values shown are raw digitised constraint curves — apply Table VI correction "
            "before citing.",
            styles["warn"]
        ))
        story.append(Spacer(1, 0.15*cm))

    # Plot — sized to preserve its native aspect ratio and use the full
    # remaining page width, capped so the whole pair still fits one page.
    if plot_path and Path(plot_path).exists():
        img_w, img_h = _sized_image(str(plot_path), CONTENT_WIDTH, 14.5*cm)
        img = Image(str(plot_path), width=img_w, height=img_h)
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
        leftMargin=LEFT_MARGIN, rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN, bottomMargin=BOTTOM_MARGIN,
        title="Spin-Dependent Exotic Interactions — Asymmetry Report",
        author="SPINDEP Framework",
    )
    rc = ReportCanvas(
        title=f"SPINDEP Analysis  |  {timestamp}",
        total_pairs=total_pairs,
        timestamp=timestamp,
    )

    story  = []
    story += build_cover(styles, summary_rows, skipped, timestamp)
    story += build_summary_table(summary_rows, styles)

    for idx, row in enumerate(summary_rows, start=1):
        pp = plot_path_for(row)
        story += build_pair_section(row, pp, styles, idx, total_pairs)

    doc.build(story, onFirstPage=rc.on_page, onLaterPages=rc.on_page)
    print(f"[REPORT] Saved → {output_path}")
    return output_path
