import React, { useMemo, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, ReferenceLine, Cell, Legend,
} from "recharts";
import { T, SIG } from "../../constants";
import {
  detectSystematics, reducedChi2, chi2RatioInterpretation,
  formatPval, pvalColor,
} from "../../utils";
import { Stat, PanelHeader } from "../ui";
import { Icon } from "../ui/Icon";
import type { AnalysisPair, SystematicFlag, SystematicSeverity } from "../../types";

interface InterpretationSectionProps {
  pairs: AnalysisPair[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SEV_COLOR: Record<SystematicSeverity, string> = {
  ok:       T.teal,
  warn:     T.amber,
  critical: T.red,
};

const SEV_BG: Record<SystematicSeverity, string> = {
  ok:       T.tealDim,
  warn:     T.amberDim,
  critical: T.redDim,
};

const SEV_LABEL: Record<SystematicSeverity, string> = {
  ok:       "OK",
  warn:     "WARN",
  critical: "CRITICAL",
};

function SeverityBadge({ sev }: { sev: SystematicSeverity }) {
  return (
    <span
      style={{
        display: "inline-flex", alignItems: "center", gap: 3,
        padding: "2px 7px", borderRadius: 4,
        fontSize: 10, fontWeight: 700, fontFamily: T.mono,
        background: SEV_BG[sev], color: SEV_COLOR[sev],
      }}
    >
      {SEV_LABEL[sev]}
    </span>
  );
}

// ─── Sub-panels ───────────────────────────────────────────────────────────────

/** |Aα| distribution bar chart with null-hypothesis reference */
function AsymmetryDistribution({ pairs }: { pairs: AnalysisPair[] }) {
  // Bin |Aα| values into 10 bins from 0 → 1
  const bins = useMemo(() => {
    const N = 10;
    const counts = Array.from({ length: N }, (_, i) => ({
      bin: `${(i / N).toFixed(1)}–${((i + 1) / N).toFixed(1)}`,
      center: (i + 0.5) / N,
      count: 0,
    }));
    for (const p of pairs) {
      const idx = Math.min(Math.floor(p.meanAbsA * N), N - 1);
      counts[idx].count++;
    }
    return counts;
  }, [pairs]);

  // Under null hypothesis (CPT conservation), |Aα| should be ~uniform [0,1]
  const nullExpected = pairs.length / 10;

  return (
    <div className="panel">
      <PanelHeader
        title="|Aα| Distribution"
        icon="chart"
        sub="Observed vs null hypothesis (CPT conservation → uniform distribution)"
      />
      <div style={{ padding: "12px 8px 8px" }}>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={bins} margin={{ top: 4, right: 16, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
            <XAxis
              dataKey="bin"
              tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
              label={{ value: "|Aα| bin", position: "insideBottom", offset: -12, fill: T.muted, fontSize: 10 }}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
              width={28}
              label={{ value: "count", angle: -90, position: "insideLeft", fill: T.muted, fontSize: 10 }}
            />
            <Tooltip
              contentStyle={{ background: T.bg1, border: `1px solid ${T.border}`, borderRadius: 8, fontSize: 11, fontFamily: T.mono }}
              labelStyle={{ color: T.textDim }}
              itemStyle={{ color: T.text }}
            />
            <ReferenceLine
              y={nullExpected}
              stroke={T.teal}
              strokeDasharray="6 3"
              label={{ value: "null H₀", fill: T.teal, fontSize: 9 }}
            />
            <Bar dataKey="count" radius={[3, 3, 0, 0]}>
              {bins.map((b, i) => (
                <Cell
                  key={i}
                  fill={b.center >= 0.95 ? T.red : b.center >= 0.5 ? T.amber : T.blue}
                  fillOpacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 6, fontSize: 10, color: T.textDim }}>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 10, height: 10, background: T.blue, borderRadius: 2, display: "inline-block" }} /> |Aα| &lt; 0.5
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 10, height: 10, background: T.amber, borderRadius: 2, display: "inline-block" }} /> 0.5 – 0.95
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 10, height: 10, background: T.red, borderRadius: 2, display: "inline-block" }} /> ≥ 0.95 (near-maximal)
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 10, height: 3, background: T.teal, display: "inline-block", borderTop: `2px dashed ${T.teal}` }} /> null H₀
          </span>
        </div>
      </div>
    </div>
  );
}

/** χ² ratio scatter: each point is a pair; x = chi2Ratio, y = meanAbsA */
function Chi2RatioScatter({ pairs }: { pairs: AnalysisPair[] }) {
  const data = useMemo(
    () =>
      pairs.map(p => ({
        id:       p.id,
        x:        p.chi2Ratio ?? 1,
        y:        p.meanAbsA,
        rchi2:    reducedChi2(p.chi2Weighted, p.dof),
        coupling: p.coupling,
        pval:     p.pval,
      })),
    [pairs]
  );

  const CustomDot = (props: any) => {
    const { cx, cy, payload } = props;
    const col = payload.y >= 0.95 ? T.red : payload.y >= 0.5 ? T.amber : T.blue;
    return <circle cx={cx} cy={cy} r={6} fill={col} fillOpacity={0.85} stroke={T.bg0} strokeWidth={1} />;
  };

  return (
    <div className="panel">
      <PanelHeader
        title="χ² ratio vs |Aα|"
        icon="scope"
        sub="χ²(w)/χ²(u) — ratio < 1 means weighted method is more conservative (preferred)"
      />
      <div style={{ padding: "12px 8px 8px" }}>
        <ResponsiveContainer width="100%" height={220}>
          <ScatterChart margin={{ top: 4, right: 16, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
            <XAxis
              type="number" dataKey="x" name="χ² ratio" domain={[0, "auto"]}
              tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
              label={{ value: "χ²(w) / χ²(u)", position: "insideBottom", offset: -12, fill: T.muted, fontSize: 10 }}
            />
            <YAxis
              type="number" dataKey="y" name="|Aα|" domain={[0, 1.05]}
              tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
              width={36}
              label={{ value: "|Aα| mean", angle: -90, position: "insideLeft", fill: T.muted, fontSize: 10 }}
            />
            <ReferenceLine x={1} stroke={T.muted} strokeDasharray="4 4" label={{ value: "ratio=1", fill: T.muted, fontSize: 9 }} />
            <ReferenceLine y={0.95} stroke={T.red} strokeDasharray="4 4" label={{ value: "|Aα|=0.95", fill: T.red, fontSize: 9 }} />
            <Tooltip
              contentStyle={{ background: T.bg1, border: `1px solid ${T.border}`, borderRadius: 8, fontSize: 11, fontFamily: T.mono }}
              formatter={(val: number, name: string) => [
                name === "χ² ratio" ? val.toFixed(3) : val.toFixed(4), name
              ]}
              labelFormatter={() => ""}
              cursor={{ strokeDasharray: "3 3" }}
            />
            <Scatter data={data} shape={<CustomDot />} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/** χ² ratio trend bar chart showing each pair */
function Chi2RatioTrend({ pairs }: { pairs: AnalysisPair[] }) {
  const data = useMemo(
    () =>
      pairs.map(p => ({
        label:   p.id.length > 22 ? p.id.slice(0, 20) + "…" : p.id,
        fullId:  p.id,
        ratio:   p.chi2Ratio ?? 1,
        rchi2:   reducedChi2(p.chi2Weighted, p.dof),
      })),
    [pairs]
  );

  return (
    <div className="panel">
      <PanelHeader
        title="χ² ratio per pair"
        icon="grid"
        sub="Per-pair χ²(weighted)/χ²(uniform). All bars < 1 confirm weighted method is consistently more conservative."
      />
      <div style={{ padding: "12px 8px 8px" }}>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 48 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
            <XAxis
              dataKey="label"
              tick={{ fill: T.textDim, fontSize: 8, fontFamily: T.mono }}
              angle={-35} textAnchor="end"
            />
            <YAxis
              tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
              width={36}
              label={{ value: "χ² ratio", angle: -90, position: "insideLeft", fill: T.muted, fontSize: 10 }}
            />
            <ReferenceLine y={1} stroke={T.muted} strokeDasharray="4 4" label={{ value: "1.0", fill: T.muted, fontSize: 9 }} />
            <Tooltip
              contentStyle={{ background: T.bg1, border: `1px solid ${T.border}`, borderRadius: 8, fontSize: 11, fontFamily: T.mono }}
              formatter={(val: number, name: string) =>
                name === "ratio" ? [val.toFixed(4), "χ²(w)/χ²(u)"] : [val.toFixed(0), "χ²_red(w)"]
              }
              labelStyle={{ color: T.textDim }}
            />
            <Bar dataKey="ratio" radius={[3, 3, 0, 0]}>
              {data.map((d, i) => (
                <Cell key={i} fill={d.ratio < 1 ? T.teal : T.amber} fillOpacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/** Reduced χ² table */
function ReducedChi2Table({ pairs }: { pairs: AnalysisPair[] }) {
  const rows = useMemo(
    () =>
      [...pairs]
        .map(p => ({
          ...p,
          rchi2w: reducedChi2(p.chi2Weighted, p.dof),
          rchi2u: reducedChi2(p.chi2Uniform,  p.dof),
          ratioInterp: chi2RatioInterpretation(p.chi2Ratio ?? 1),
        }))
        .sort((a, b) => b.rchi2w - a.rchi2w),
    [pairs]
  );

  return (
    <div className="panel">
      <PanelHeader
        title="Reduced χ² Summary"
        icon="table"
        sub="χ²/dof for each method. Expected value ~1 for pure statistical scatter. Values >> 1 indicate systematic offsets."
      />
      <div style={{ overflowX: "auto", maxHeight: 320, overflowY: "auto" }}>
        <table className="data-table">
          <thead style={{ position: "sticky", top: 0, background: T.panel }}>
            <tr>
              <th>Pair</th>
              <th>Coupling</th>
              <th>χ²/dof (weighted)</th>
              <th>χ²/dof (uniform)</th>
              <th>ratio (w/u)</th>
              <th>Interpretation</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id}>
                <td style={{ color: T.textDim, fontSize: 10, maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                    title={r.id}>{r.id}</td>
                <td><span className="tag tag-blue">{r.coupling}</span></td>
                <td style={{ color: r.rchi2w > 500 ? T.red : r.rchi2w > 100 ? T.amber : T.text, fontWeight: r.rchi2w > 100 ? 700 : 400 }}>
                  {r.rchi2w.toFixed(0)}
                </td>
                <td style={{ color: T.textDim }}>{r.rchi2u.toFixed(0)}</td>
                <td style={{ color: r.ratioInterp.color }}>{r.chi2Ratio?.toFixed(3) ?? "—"}</td>
                <td style={{ color: r.ratioInterp.color, fontSize: 11 }}>{r.ratioInterp.label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ padding: "10px 16px", borderTop: `1px solid ${T.border}`, fontSize: 11, color: T.textDim, lineHeight: 1.7 }}>
        <b style={{ color: T.textHi }}>Interpretation note:</b> All reduced χ² values here are expected to be large
        (hundreds–thousands) because the pipeline computes χ² between two independent experimental
        constraint curves that differ by orders of magnitude at each λ point — not between data and a
        fit. The χ²<sub>red</sub> therefore quantifies <em>how different</em> the matter vs. antimatter
        curves are, not goodness-of-fit. The key diagnostic is the <b style={{ color: T.teal }}>ratio (w/u)</b>:
        values consistently &lt; 1 confirm the weighted method is more conservative throughout.
      </div>
    </div>
  );
}

/** Systematic flags panel */
function SystematicFlags({ flags }: { flags: SystematicFlag[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const counts = useMemo(() => ({
    critical: flags.filter(f => f.severity === "critical").length,
    warn:     flags.filter(f => f.severity === "warn").length,
    ok:       flags.filter(f => f.severity === "ok").length,
  }), [flags]);

  if (flags.length === 0) {
    return (
      <div className="panel">
        <PanelHeader title="Systematic Flags" icon="validate" sub="Automated checks for common analysis pitfalls" />
        <div style={{ padding: 32, textAlign: "center", color: T.teal }}>
          <Icon name="check" size={28} />
          <div style={{ marginTop: 8, fontWeight: 600 }}>No systematic flags raised</div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <PanelHeader
        title="Systematic Flags"
        icon="warn"
        sub="Automated checks for unit conversion, λ compatibility, χ² anomalies"
        right={
          <div style={{ display: "flex", gap: 6 }}>
            {counts.critical > 0 && <span className="tag tag-red">{counts.critical} critical</span>}
            {counts.warn > 0     && <span className="tag tag-amber">{counts.warn} warnings</span>}
          </div>
        }
      />
      <div style={{ padding: "8px 0" }}>
        {/* Sort critical first */}
        {[...flags]
          .sort((a, b) => {
            const order: Record<SystematicSeverity, number> = { critical: 0, warn: 1, ok: 2 };
            return order[a.severity] - order[b.severity];
          })
          .map((f, i) => {
            const key = `${f.pairId}-${f.code}`;
            const isOpen = expanded === key;
            return (
              <div
                key={key}
                style={{
                  borderBottom: i < flags.length - 1 ? `1px solid ${T.border}20` : "none",
                  cursor: "pointer",
                }}
                onClick={() => setExpanded(isOpen ? null : key)}
              >
                <div style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "10px 16px",
                  background: isOpen ? T.bg2 : "transparent",
                  transition: "background .1s",
                }}>
                  <SeverityBadge sev={f.severity} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, color: T.textHi, fontWeight: 500 }}>{f.message}</div>
                    <div style={{ fontSize: 10, color: T.textDim, fontFamily: T.mono, marginTop: 1 }}>{f.pairId} · {f.code}</div>
                  </div>
                  <span style={{ color: T.muted }}>
                    <Icon name={isOpen ? "chevD" : "chevron"} size={13} />
                  </span>
                </div>
                {isOpen && (
                  <div style={{
                    padding: "10px 16px 14px 52px",
                    background: SEV_BG[f.severity] + "44",
                    borderLeft: `3px solid ${SEV_COLOR[f.severity]}`,
                    marginLeft: 16,
                    marginRight: 16,
                    marginBottom: 8,
                    borderRadius: "0 0 6px 6px",
                    fontSize: 12,
                    color: T.text,
                    lineHeight: 1.7,
                  }}>
                    {f.detail}
                  </div>
                )}
              </div>
            );
          })}
      </div>
    </div>
  );
}

/** Narrative interpretation block */
function NarrativeInterpretation({ pairs, flags }: { pairs: AnalysisPair[]; flags: SystematicFlag[] }) {
  const critCount  = flags.filter(f => f.severity === "critical").length;
  const warnCount  = flags.filter(f => f.severity === "warn").length;
  const nearMaxN   = pairs.filter(p => p.meanAbsA >= 0.95).length;
  const allSig     = pairs.every(p => p.pval < SIG.HIGHLY);
  const avgRatio   = pairs.reduce((s, p) => s + (p.chi2Ratio ?? 1), 0) / pairs.length;
  const ratioInterp = chi2RatioInterpretation(avgRatio);
  const unitConvN  = flags.filter(f => f.code === "UNIT_CONVERSION").length;

  return (
    <div className="panel">
      <PanelHeader title="Narrative Interpretation" icon="report"
        sub="Auto-generated for thesis/paper — review and edit before use" />
      <div style={{ padding: "16px 20px", lineHeight: 1.9, fontSize: 13, color: T.text }}>

        <p style={{ marginBottom: 12 }}>
          <b style={{ color: T.textHi }}>Summary:</b> The analysis finds{" "}
          <span style={{ color: T.red, fontWeight: 600 }}>{pairs.length} matter–antimatter pairs</span>,
          {allSig
            ? <> all of which are statistically significant at <span style={{ color: T.red }}>p &lt; 0.001</span></>
            : <> {pairs.filter(p => p.pval < SIG.HIGHLY).length} of which reach p &lt; 0.001</>
          }.{" "}
          {nearMaxN === pairs.length
            ? `All ${nearMaxN} pairs show near-maximal CPT asymmetry (|Aα| ≥ 0.95), with the lowest observed |Aα| = ${Math.min(...pairs.map(p => p.meanAbsA)).toFixed(4)}.`
            : `${nearMaxN} of ${pairs.length} pairs show near-maximal asymmetry (|Aα| ≥ 0.95).`}
        </p>

        <p style={{ marginBottom: 12 }}>
          <b style={{ color: T.textHi }}>χ² methodology:</b>{" "}
          The average χ²(w)/χ²(u) ratio across all pairs is{" "}
          <span style={{ color: ratioInterp.color, fontWeight: 600 }}>{avgRatio.toFixed(3)}</span> ({ratioInterp.label.toLowerCase()}).{" "}
          This confirms that the curvature-derived per-point uncertainties are{" "}
          {avgRatio < 1
            ? "larger than the uniform 10% floor, making the weighted method the more conservative (and thus more credible) choice for the thesis."
            : "smaller than the uniform 10% floor — the uniform method should be treated as the baseline and the weighted result as a cross-check."
          }
        </p>

        {unitConvN > 0 && (
          <p style={{ marginBottom: 12, padding: "10px 14px", background: T.amberDim, borderRadius: 6, border: `1px solid ${T.amber}30` }}>
            <b style={{ color: T.amber }}>⚠ Unit conversion:</b>{" "}
            {unitConvN} dataset{unitConvN > 1 ? "s have" : " has"} a pre-conversion flag. The converted values
            are used in the analysis, but the original published units and conversion factors should be
            documented in the thesis appendix. Verify that the conversion preserves the λ interpretation.
          </p>
        )}

        <p style={{ marginBottom: 12 }}>
          <b style={{ color: T.textHi }}>Physical interpretation:</b>{" "}
          Near-maximal |Aα| values do not necessarily indicate new physics. They arise whenever the
          matter and antimatter constraint curves differ by more than ~1 order of magnitude throughout
          the overlap region — which is physically expected when comparing experiments with very different
          experimental sensitivities (e.g. Delaunay2017 vs. Adkins2022). The asymmetry quantifies
          <em> how much more constraining</em> one dataset is relative to the other, not the magnitude
          of CPT violation. A conclusive CPT test requires both curves to probe the <em>same</em>{" "}
          interaction at comparable sensitivity.
        </p>

        {critCount + warnCount > 0 && (
          <p style={{ marginBottom: 0, padding: "10px 14px", background: T.redDim, borderRadius: 6, border: `1px solid ${T.red}30` }}>
            <b style={{ color: T.red }}>Examiner note:</b>{" "}
            {critCount} critical and {warnCount} warning flag{warnCount !== 1 ? "s" : ""} were raised
            (see Systematic Flags panel below). Each should be addressed explicitly in the thesis.
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Main Section ─────────────────────────────────────────────────────────────

export const InterpretationSection: React.FC<InterpretationSectionProps> = ({ pairs }) => {
  const flags = useMemo(() => detectSystematics(pairs), [pairs]);

  const critCount = flags.filter(f => f.severity === "critical").length;
  const warnCount = flags.filter(f => f.severity === "warn").length;
  const avgAbsA   = pairs.length ? pairs.reduce((s, p) => s + p.meanAbsA, 0) / pairs.length : 0;
  const avgRatio  = pairs.length ? pairs.reduce((s, p) => s + (p.chi2Ratio ?? 1), 0) / pairs.length : 0;

  if (pairs.length === 0) {
    return (
      <div className="fade-in" style={{ textAlign: "center", padding: 60, color: T.muted }}>
        <Icon name="validate" size={40} />
        <div style={{ marginTop: 16, fontSize: 14, fontWeight: 600, color: T.textDim }}>
          Run the pipeline first to see the interpretation dashboard
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ color: T.textHi, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
          Statistical Interpretation
        </h2>
        <p style={{ color: T.textDim, fontSize: 13 }}>
          Systematic checks, χ² diagnostics, and narrative interpretation of your results.
          Designed to pre-empt examiner and referee questions.
        </p>
      </div>

      {/* Overview stats */}
      <div className="split split-4" style={{ marginBottom: 20 }}>
        <Stat label="Pairs analysed"      value={pairs.length} />
        <Stat label="Avg |Aα|"            value={avgAbsA.toFixed(4)}
          color={avgAbsA >= 0.95 ? T.red : avgAbsA >= 0.5 ? T.amber : T.teal}
          sub="mean asymmetry" />
        <Stat label="Avg χ² ratio (w/u)"  value={avgRatio.toFixed(3)}
          color={chi2RatioInterpretation(avgRatio).color}
          sub={chi2RatioInterpretation(avgRatio).label} />
        <Stat label="Systematic flags"
          value={`${critCount}c / ${warnCount}w`}
          color={critCount > 0 ? T.red : warnCount > 0 ? T.amber : T.teal}
          sub={critCount > 0 ? "needs attention" : warnCount > 0 ? "review recommended" : "clean"} />
      </div>

      {/* Narrative */}
      <div style={{ marginBottom: 16 }}>
        <NarrativeInterpretation pairs={pairs} flags={flags} />
      </div>

      {/* Charts row */}
      <div className="split split-2" style={{ marginBottom: 16 }}>
        <AsymmetryDistribution pairs={pairs} />
        <Chi2RatioScatter pairs={pairs} />
      </div>

      {/* χ² ratio trend */}
      <div style={{ marginBottom: 16 }}>
        <Chi2RatioTrend pairs={pairs} />
      </div>

      {/* Reduced χ² table */}
      <div style={{ marginBottom: 16 }}>
        <ReducedChi2Table pairs={pairs} />
      </div>

      {/* Systematic flags */}
      <SystematicFlags flags={flags} />
    </div>
  );
};