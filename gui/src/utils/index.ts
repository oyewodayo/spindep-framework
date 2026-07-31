import { T, SIG } from "../constants";
import type { AnalysisPair, SystematicFlag } from "../types";

// Basic formatters

export function pvalColor(p: number): string {
  if (p < SIG.HIGHLY)   return T.red;
  if (p < SIG.STANDARD) return T.amber;
  return T.green;
}

export function formatPval(p: number): string {
  if (p < 1e-9) return "<10⁻⁹";
  return p.toExponential(2);
}

export function formatLogScale(v: number): string {
  return `10^${v.toFixed(0)}`;
}

export function logLineColor(line: string): string {
  if (line.includes("[OK]")  || line.includes("OK"))    return T.teal;
  if (line.includes("[WARN]")|| line.includes("WARN"))  return T.amber;
  if (line.includes("[ERR]") || line.includes("ERROR")
                             || line.includes("error"))  return T.red;
  return T.textDim;
}

export function safeId(s: string): string {
  return s.replace(/[^a-z0-9]/gi, "_");
}

// Statistical analysis

/** χ²/dof — expected ~1 for pure statistical scatter. */
export function reducedChi2(chi2: number, dof: number): number {
  return dof > 0 ? chi2 / dof : 0;
}

/**
 * Interpret χ²(w)/χ²(u) ratio.
 * < 1  → weighted is more conservative (curvature σ > uniform 10%)
 * ~ 1  → both methods agree
 * > 1  → weighted is LESS conservative (check curvature σ)
 */
export function chi2RatioInterpretation(ratio: number): {
  label: string; color: string; detail: string;
} {
  if (ratio < 0.2) return {
    label: "Highly conservative", color: T.teal,
    detail: "Large per-point spread — weighted method much stricter than uniform 10%.",
  };
  if (ratio < 0.8) return {
    label: "Conservative", color: T.teal,
    detail: "Weighted method more conservative. Curvature-derived uncertainties dominate.",
  };
  if (ratio < 1.2) return {
    label: "Consistent", color: T.text,
    detail: "Both χ² methods broadly agree. Uncertainty model is self-consistent.",
  };
  return {
    label: "Weighted less strict", color: T.amber,
    detail: "Weighted method less conservative than uniform 10%. Check curvature-derived σ.",
  };
}

/**
 * Automated systematic checks — every flag here is a question
 * an examiner or PRL referee would ask.
 */
export function detectSystematics(pairs: AnalysisPair[]): SystematicFlag[] {
  const flags: SystematicFlag[] = [];

  for (const p of pairs) {
    const id = p.id;

    // 1. Unit pre-conversion applied
    if (
      p.matterUnit?.includes("pre-converted") ||
      p.antimatterUnit?.includes("pre-converted")
    ) {
      flags.push({
        pairId: id, code: "UNIT_CONVERSION", severity: "warn",
        message: "Unit pre-conversion applied",
        detail: `Matter: "${p.matterUnit}" | Antimatter: "${p.antimatterUnit}". ` +
                `Verify conversion factor and reference-frame consistency.`,
      });
    }

    // 2. Near-maximal asymmetry
    if (p.meanAbsA >= 0.95) {
      flags.push({
        pairId: id, code: "NEAR_MAXIMAL_ASYMMETRY", severity: "warn",
        message: `|Aα| = ${p.meanAbsA.toFixed(4)} ≥ 0.95`,
        detail: "Near-maximal asymmetry. Verify that matter/antimatter datasets probe " +
                "the same λ range and coupling. Could indicate datasets are fundamentally " +
                "incompatible rather than CPT violation.",
      });
    }

    // 3. High reduced χ²
    const rchi2 = reducedChi2(p.chi2Weighted, p.dof);
    if (rchi2 > 100) {
      flags.push({
        pairId: id, code: "HIGH_REDUCED_CHI2", severity: "critical",
        message: `χ²/dof = ${rchi2.toFixed(0)} >> 1`,
        detail: `Reduced χ² = ${rchi2.toFixed(1)} (dof = ${p.dof}). Expected ~1 for ` +
                `statistical fluctuations. This magnitude suggests a systematic offset ` +
                `between curves, not statistical scatter.`,
      });
    }

    // 4. Asymmetric per-point uncertainties
    if (p.sigmaA > 0 && p.sigmaM > 0) {
      const sigRatio = Math.max(p.sigmaA, p.sigmaM) / Math.min(p.sigmaA, p.sigmaM);
      if (sigRatio > 3) {
        const larger  = p.sigmaA > p.sigmaM ? "antimatter" : "matter";
        const smaller = p.sigmaA > p.sigmaM ? "matter"     : "antimatter";
        flags.push({
          pairId: id, code: "ASYMMETRIC_UNCERTAINTY", severity: "warn",
          message: `σ ratio ${sigRatio.toFixed(1)}× (${larger} >> ${smaller})`,
          detail: `σ_matter = ${p.sigmaM.toFixed(1)}%, σ_antimatter = ${p.sigmaA.toFixed(1)}%. ` +
                  `Highly asymmetric per-point uncertainties. The dataset with smaller σ ` +
                  `likely has a smoother constraint curve.`,
        });
      }
    }

    // 5. Potential unknown
    if (p.potential?.toUpperCase() === "UNKNOWN") {
      flags.push({
        pairId: id, code: "UNKNOWN_POTENTIAL", severity: "warn",
        message: "Potential type: UNKNOWN",
        detail: "Interaction potential not identified in dataset metadata. Results are " +
                "valid but cannot be placed on a theory-specific exclusion plot.",
      });
    }

    // 6. Narrow λ range (< 1 decade)
    const logSpan = Math.log10(p.lambdaMax) - Math.log10(p.lambdaMin);
    if (logSpan < 1.0 && p.lambdaMin > 0) {
      flags.push({
        pairId: id, code: "NARROW_LAMBDA_RANGE", severity: "warn",
        message: `λ span = ${logSpan.toFixed(2)} decades`,
        detail: `λ range: ${p.lambdaMin.toExponential(2)} – ${p.lambdaMax.toExponential(2)} m. ` +
                `Narrow overlap window. Constraint comparison is only meaningful in ` +
                `this restricted range.`,
      });
    }
  }

  return flags;
}

/** λ overlap fraction between two pairs (0 = none, 1 = full). */
export function lambdaOverlapFraction(a: AnalysisPair, b: AnalysisPair): number {
  if (a.lambdaMin <= 0 || b.lambdaMin <= 0) return 0;
  const oMin = Math.max(Math.log10(a.lambdaMin), Math.log10(b.lambdaMin));
  const oMax = Math.min(Math.log10(a.lambdaMax), Math.log10(b.lambdaMax));
  if (oMax <= oMin) return 0;
  const total = Math.max(Math.log10(a.lambdaMax), Math.log10(b.lambdaMax))
              - Math.min(Math.log10(a.lambdaMin), Math.log10(b.lambdaMin));
  return total > 0 ? (oMax - oMin) / total : 0;
}

// Data helpers

export function makeFallbackTree() {
  const COUPLINGS = ["gAgA", "gsgs", "gVgV", "gpgp", "gpgs"];
  return {
    name: "datasets/normalized",
    type: "folder" as const,
    children: COUPLINGS.map(c => ({
      name: c,
      type: "folder" as const,
      children: [{ name: "lepton-lepton", type: "folder" as const, children: [] }],
    })),
  };
}

export function estimateProgress(logLength: number): number {
  return Math.min(95, logLength * 4);
}

// LaTeX generation

export function buildLatexTable(pairs: AnalysisPair[]): string {
  const sig = pairs.filter(p => p.pval < SIG.STANDARD);
  return `\\begin{table}[h]
\\centering
\\caption{CPT Asymmetry Test Results — Weighted $\\chi^2$ Method}
\\label{tab:cpt_asymmetry}
\\begin{tabular}{llllccccr}
\\hline
Coupling & Potential & Class & Sectors & $\\langle|A_\\alpha|\\rangle$ & $\\chi^2_{\\mathrm{w}}$ & $\\chi^2_{\\mathrm{u}}$ & ratio & $p$-value \\\\
\\hline
${sig.slice(0, 12).map(p =>
  `${p.coupling} & ${p.potential} & ${p.interactionClass ?? "—"} & ` +
  `$${p.secM} \\times \\bar{${p.secA}}$ & ${p.meanAbsA?.toFixed(4)} & ` +
  `${p.chi2Weighted?.toFixed(0)} & ${p.chi2Uniform?.toFixed(0)} & ` +
  `${p.chi2Ratio?.toFixed(3) ?? "—"} & ${p.pval?.toExponential(1)} \\\\`
).join("\n")}
\\hline
\\end{tabular}
\\begin{tablenotes}
  \\small
  \\item $\\chi^2_{\\mathrm{w}}$: per-point curvature-weighted. $\\chi^2_{\\mathrm{u}}$: uniform 10\\% uncertainty.
  \\item ratio $< 1$: weighted method is more conservative (preferred for thesis).
  \\item All entries: $p < 0.001$ (***).
\\end{tablenotes}
\\end{table}`;
}

// CSV generation

function csvField(v: string | number): string {
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function buildCsvTable(pairs: AnalysisPair[]): string {
  const header = [
    "Pair ID", "Coupling", "Potential", "Class", "Sectors",
    "|Aalpha| mean", "chi2 (uniform)", "chi2 (weighted)", "chi2 ratio",
    "dof", "p-value (weighted)", "lambda min (m)", "lambda max (m)",
  ];
  const rows = pairs.map(p => [
    p.id, p.coupling, p.potential, p.interactionClass ?? "",
    `${p.secM} x ${p.secA}`,
    p.meanAbsA?.toFixed(4), p.chi2Uniform?.toFixed(0), p.chi2Weighted?.toFixed(0),
    p.chi2Ratio?.toFixed(3) ?? "", p.dof, p.pval?.toExponential(3),
    p.lambdaMin?.toExponential(3), p.lambdaMax?.toExponential(3),
  ]);
  return [header, ...rows].map(r => r.map(csvField).join(",")).join("\n");
}

// Client-side file download

export function downloadTextFile(text: string, filename: string): void {
  const blob = new Blob([text], { type: "text/plain" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}