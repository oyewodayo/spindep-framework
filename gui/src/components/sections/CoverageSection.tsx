import React, { useMemo, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend, ReferenceArea,
} from "recharts";
import { T } from "../../constants";
import { formatLogScale, lambdaOverlapFraction } from "../../utils";
import { Stat, PanelHeader } from "../ui";
import { Icon } from "../ui/Icon";
import type { AnalysisPair } from "../../types";

interface CoverageSectionProps {
  pairs: AnalysisPair[];
}

// Color palette for datasets
const MATTER_PALETTE    = [T.blue,   "#22d3ee", "#818cf8", "#34d399", "#60a5fa"] as const;
const ANTIMATTER_PALETTE = [T.amber, T.red,     "#f472b6", "#fb923c", "#facc15"] as const;

// Gantt-style λ coverage chart

function LambdaGantt({ pairs, coupling }: { pairs: AnalysisPair[]; coupling: string }) {
  const relevant = pairs.filter(p => p.coupling === coupling);

  // Collect unique datasets with their λ ranges for this coupling
  const datasets = useMemo(() => {
    const seen = new Map<string, { name: string; logMin: number; logMax: number; isMatter: boolean; sector: string }>();
    for (const p of relevant) {
      if (!seen.has(p.matterDataset)) {
        seen.set(p.matterDataset, {
          name: p.matterDataset,
          logMin: Math.log10(p.lambdaMin),
          logMax: Math.log10(p.lambdaMax),
          isMatter: true,
          sector: p.secM,
        });
      } else {
        const d = seen.get(p.matterDataset)!;
        d.logMin = Math.min(d.logMin, Math.log10(p.lambdaMin));
        d.logMax = Math.max(d.logMax, Math.log10(p.lambdaMax));
      }
      if (!seen.has(p.antimatterDataset)) {
        seen.set(p.antimatterDataset, {
          name: p.antimatterDataset,
          logMin: Math.log10(p.lambdaMin),
          logMax: Math.log10(p.lambdaMax),
          isMatter: false,
          sector: p.secA,
        });
      } else {
        const d = seen.get(p.antimatterDataset)!;
        d.logMin = Math.min(d.logMin, Math.log10(p.lambdaMin));
        d.logMax = Math.max(d.logMax, Math.log10(p.lambdaMax));
      }
    }
    return [...seen.values()];
  }, [relevant]);

  const globalLogMin = Math.min(...datasets.map(d => d.logMin));
  const globalLogMax = Math.max(...datasets.map(d => d.logMax));
  const totalSpan    = globalLogMax - globalLogMin || 1;

  // Find overlapping windows between matter/antimatter datasets
  const matterDs   = datasets.filter(d => d.isMatter);
  const antimatterDs = datasets.filter(d => !d.isMatter);
  const overlaps: { logMin: number; logMax: number; frac: number }[] = [];
  for (const m of matterDs) {
    for (const a of antimatterDs) {
      const oMin = Math.max(m.logMin, a.logMin);
      const oMax = Math.min(m.logMax, a.logMax);
      if (oMax > oMin) {
        overlaps.push({ logMin: oMin, logMax: oMax, frac: (oMax - oMin) / totalSpan });
      }
    }
  }

  if (datasets.length === 0) return null;

  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ fontSize: 11, color: T.textDim, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 10 }}>
        λ coverage — {coupling}
      </div>

      {/* Gantt bars */}
      <div style={{ position: "relative", paddingLeft: 160 }}>
        {/* Axis ticks */}
        <div style={{
          position: "absolute", left: 160, right: 0, top: 0,
          display: "flex", justifyContent: "space-between",
          fontSize: 9, color: T.muted, fontFamily: T.mono, marginBottom: 4,
        }}>
          {Array.from({ length: 7 }, (_, i) => {
            const v = globalLogMin + (i / 6) * totalSpan;
            return <span key={i}>10<sup>{v.toFixed(0)}</sup></span>;
          })}
        </div>

        {/* Overlap shading */}
        {overlaps.map((o, i) => {
          const leftPct = ((o.logMin - globalLogMin) / totalSpan) * 100;
          const widthPct = ((o.logMax - o.logMin) / totalSpan) * 100;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: `${leftPct}%`, width: `${widthPct}%`,
                top: 18, bottom: 0,
                background: `${T.teal}18`,
                border: `1px solid ${T.teal}40`,
                borderRadius: 2,
                pointerEvents: "none",
              }}
            />
          );
        })}

        {/* Dataset bars */}
        <div style={{ marginTop: 20 }}>
          {datasets.map((d, idx) => {
            const leftPct  = ((d.logMin - globalLogMin) / totalSpan) * 100;
            const widthPct = ((d.logMax - d.logMin) / totalSpan) * 100;
            const mIdx     = d.isMatter ? matterDs.indexOf(d) : antimatterDs.indexOf(d);
            const color    = d.isMatter ? MATTER_PALETTE[mIdx % 5] : ANTIMATTER_PALETTE[mIdx % 5];

            return (
              <div key={d.name} style={{ display: "flex", alignItems: "center", marginBottom: 8, height: 24 }}>
                <div style={{
                  width: 150, paddingRight: 10, fontSize: 11, fontFamily: T.mono,
                  color: d.isMatter ? T.blue : T.amber,
                  textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  flexShrink: 0,
                }}>
                  {d.name}
                  <span style={{ fontSize: 9, color: T.textDim, marginLeft: 4 }}>
                    ({d.isMatter ? "M" : "AM"})
                  </span>
                </div>
                <div style={{ position: "relative", flex: 1, height: "100%", background: T.border + "30", borderRadius: 3 }}>
                  <div
                    style={{
                      position: "absolute",
                      left: `${leftPct}%`, width: `${Math.max(widthPct, 1)}%`,
                      height: "100%",
                      background: color,
                      borderRadius: 3,
                      opacity: 0.8,
                      display: "flex", alignItems: "center", paddingLeft: 6,
                      fontSize: 9, fontFamily: T.mono, color: T.bg0, fontWeight: 600,
                      overflow: "hidden",
                    }}
                    title={`${d.logMin.toFixed(1)} – ${d.logMax.toFixed(1)} (log₁₀ m)`}
                  >
                    {widthPct > 12 && `${Math.pow(10, d.logMin).toExponential(1)} – ${Math.pow(10, d.logMax).toExponential(1)} m`}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Overlap legend */}
        {overlaps.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, fontSize: 10, color: T.textDim }}>
            <div style={{ width: 16, height: 8, background: `${T.teal}40`, border: `1px solid ${T.teal}60`, borderRadius: 2 }} />
            <span>λ overlap region ({overlaps.length} window{overlaps.length > 1 ? "s" : ""}, covering {(overlaps.reduce((s,o) => s + o.frac, 0) * 100).toFixed(0)}% of total span)</span>
          </div>
        )}
      </div>
    </div>
  );
}

// Competitive constraint plot
// All curves for a coupling on one plot, with overlap bands shaded

function CompetitiveConstraintPlot({
  pairs, coupling, potential,
}: {
  pairs: AnalysisPair[];
  coupling: string;
  potential: string;
}) {
  const relevant = pairs.filter(p => p.coupling === coupling && p.potential === potential);

  if (relevant.length === 0) {
    return (
      <div style={{ padding: 32, textAlign: "center", color: T.muted, fontSize: 12 }}>
        No data for {coupling} · {potential}
      </div>
    );
  }

  // Find global λ overlap regions across all matter/antimatter pairs
  const overlapRegions = useMemo(() => {
    const regions: { x1: number; x2: number }[] = [];
    for (const p of relevant) {
      regions.push({
        x1: Math.log10(p.lambdaMin),
        x2: Math.log10(p.lambdaMax),
      });
    }
    return regions;
  }, [relevant]);

  // Build line series
  const lines = relevant.flatMap((p, i) => {
    const mColor  = MATTER_PALETTE[i % 5];
    const aColor  = ANTIMATTER_PALETTE[i % 5];
    return [
      { data: p.points, key: `${p.matterDataset}-m`, name: `${p.matterDataset} (M·${p.secM})`, color: mColor, dash: "" },
      { data: p.points, key: `${p.antimatterDataset}-a`, name: `${p.antimatterDataset} (AM·${p.secA})`, color: aColor, dash: "6 3" },
    ];
  });

  // Deduplicate by dataset name
  const seen = new Set<string>();
  const uniqueLines = lines.filter(l => {
    const dsName = l.name.split(" (")[0];
    if (seen.has(dsName)) return false;
    seen.add(dsName);
    return true;
  });

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart margin={{ top: 8, right: 20, left: 8, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
        <XAxis
          type="number" dataKey="logLam" domain={["auto", "auto"]}
          tickFormatter={formatLogScale}
          tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
          label={{ value: "Interaction range λ (m)", position: "insideBottom", offset: -12, fill: T.muted, fontSize: 11 }}
        />
        <YAxis
          tickFormatter={formatLogScale}
          tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
          width={54}
          label={{ value: "Coupling upper bound |g|", angle: -90, position: "insideLeft", fill: T.muted, fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{ background: T.bg1, border: `1px solid ${T.border}`, borderRadius: 8, fontSize: 11, fontFamily: T.mono }}
          formatter={(v: number) => [`10^(${v.toFixed(2)})`, ""]}
        />
        <Legend wrapperStyle={{ fontSize: 10, color: T.textDim, paddingTop: 8 }} />

        {/* Shade overlap regions */}
        {overlapRegions.map((r, i) => (
          <ReferenceArea
            key={i} x1={r.x1} x2={r.x2}
            fill={T.teal} fillOpacity={0.07}
            stroke={T.teal} strokeOpacity={0.3} strokeDasharray="4 4"
          />
        ))}

        {uniqueLines.map(l => (
          <Line
            key={l.key}
            data={l.data}
            type="monotone"
            dataKey={l.key.endsWith("-m") ? "logGm" : "logGa"}
            name={l.name}
            stroke={l.color}
            strokeWidth={1.8}
            dot={false}
            strokeDasharray={l.dash}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

// Overlap matrix

function OverlapMatrix({ pairs }: { pairs: AnalysisPair[] }) {
  // Build list of all unique (matterDataset, antimatterDataset) combos
  const combos = useMemo(() => {
    const list: { m: string; a: string; pair: AnalysisPair; frac: number }[] = [];
    for (const p of pairs) {
      const frac = lambdaOverlapFraction(p, p); // self-overlap = 1 by construction
      // For cross-pair overlap, compare against other pairs
      list.push({ m: p.matterDataset, a: p.antimatterDataset, pair: p, frac: 1 });
    }
    return list;
  }, [pairs]);

  // Cross-pair λ overlap table
  const crossOverlap = useMemo(() => {
    const result: { a: AnalysisPair; b: AnalysisPair; frac: number }[] = [];
    for (let i = 0; i < pairs.length; i++) {
      for (let j = i + 1; j < pairs.length; j++) {
        const frac = lambdaOverlapFraction(pairs[i], pairs[j]);
        if (frac > 0.01) result.push({ a: pairs[i], b: pairs[j], frac });
      }
    }
    return result.sort((a, b) => b.frac - a.frac);
  }, [pairs]);

  if (crossOverlap.length === 0) return null;

  return (
    <div className="panel">
      <PanelHeader
        title="Cross-Pair λ Overlap"
        icon="scope"
        sub="Pairs sharing λ coverage — important for identifying redundant or complementary constraints"
      />
      <div style={{ overflowX: "auto", maxHeight: 280, overflowY: "auto" }}>
        <table className="data-table">
          <thead style={{ position: "sticky", top: 0, background: T.panel }}>
            <tr>
              <th>Pair A</th>
              <th>Pair B</th>
              <th>Overlap fraction</th>
              <th>Competitive?</th>
              <th>λ window</th>
            </tr>
          </thead>
          <tbody>
            {crossOverlap.map(({ a, b, frac }, i) => {
              const oLogMin = Math.max(Math.log10(a.lambdaMin), Math.log10(b.lambdaMin));
              const oLogMax = Math.min(Math.log10(a.lambdaMax), Math.log10(b.lambdaMax));
              // "Competitive" = both pairs constrain same coupling and their g-bounds are within 2 orders
              const competitive = a.coupling === b.coupling;
              return (
                <tr key={i}>
                  <td style={{ fontFamily: T.mono, fontSize: 10, color: T.textDim, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                      title={a.id}>{a.id}</td>
                  <td style={{ fontFamily: T.mono, fontSize: 10, color: T.textDim, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                      title={b.id}>{b.id}</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ flex: 1, height: 6, background: T.border, borderRadius: 3, minWidth: 60 }}>
                        <div style={{ width: `${frac * 100}%`, height: "100%", background: frac > 0.5 ? T.teal : T.blue, borderRadius: 3 }} />
                      </div>
                      <span style={{ fontFamily: T.mono, fontSize: 11, color: frac > 0.5 ? T.teal : T.text }}>
                        {(frac * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td>
                    {competitive
                      ? <span className="tag tag-teal">same coupling</span>
                      : <span className="tag tag-muted">different coupling</span>}
                  </td>
                  <td style={{ fontFamily: T.mono, fontSize: 10, color: T.textDim }}>
                    10<sup>{oLogMin.toFixed(1)}</sup> – 10<sup>{oLogMax.toFixed(1)}</sup> m
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Main section

export const CoverageSection: React.FC<CoverageSectionProps> = ({ pairs }) => {
  const couplings  = useMemo(() => [...new Set(pairs.map(p => p.coupling))].sort(), [pairs]);
  const potentials = useMemo(() => [...new Set(pairs.map(p => p.potential))].sort(), [pairs]);
  const [selCoupling,  setSelCoupling]  = useState<string>("");
  const [selPotential, setSelPotential] = useState<string>("");

  React.useEffect(() => {
    if (couplings.length  && !selCoupling)  setSelCoupling(couplings[0]);
    if (potentials.length && !selPotential) setSelPotential(potentials[0]);
  }, [couplings, potentials]);

  // Global λ span across all pairs
  const globalLogMin = pairs.length ? Math.min(...pairs.map(p => Math.log10(p.lambdaMin))) : -12;
  const globalLogMax = pairs.length ? Math.max(...pairs.map(p => Math.log10(p.lambdaMax))) : 0;
  const totalDecades = globalLogMax - globalLogMin;

  // Count overlapping pairs
  const overlappingPairs = useMemo(() => {
    let count = 0;
    for (let i = 0; i < pairs.length; i++)
      for (let j = i + 1; j < pairs.length; j++)
        if (lambdaOverlapFraction(pairs[i], pairs[j]) > 0.05) count++;
    return count;
  }, [pairs]);

  if (pairs.length === 0) {
    return (
      <div className="fade-in" style={{ textAlign: "center", padding: 60, color: T.muted }}>
        <Icon name="scope" size={40} />
        <div style={{ marginTop: 16, fontSize: 14, fontWeight: 600, color: T.textDim }}>
          Run the pipeline first to see the λ coverage viewer
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ color: T.textHi, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
          λ Coverage Viewer
        </h2>
        <p style={{ color: T.textDim, fontSize: 13 }}>
          Interaction-range coverage for all datasets, overlap regions highlighted,
          and competitive constraint comparison for the selected coupling.
        </p>
      </div>

      <div className="split split-4" style={{ marginBottom: 20 }}>
        <Stat label="Total λ span"       value={totalDecades.toFixed(1)} unit="decades" />
        <Stat label="Couplings covered"  value={couplings.length} color={T.blue} />
        <Stat label="Overlapping pairs"  value={overlappingPairs}
          color={overlappingPairs > 0 ? T.teal : T.muted}
          sub="share λ range" />
        <Stat label="Unique datasets"
          value={new Set([...pairs.map(p => p.matterDataset), ...pairs.map(p => p.antimatterDataset)]).size}
          color={T.violet} />
      </div>

      {/* Gantt charts — one per coupling */}
      <div className="panel" style={{ padding: 20, marginBottom: 16 }}>
        <PanelHeader
          title="Dataset λ Coverage (all couplings)"
          icon="layers"
          sub="Horizontal bars show each dataset's λ range. Teal shading = overlap between matter (M) and antimatter (AM)."
        />
        <div style={{ padding: "16px 0 0" }}>
          {couplings.map((c, i) => (
            <div key={c} style={{ marginBottom: i < couplings.length - 1 ? 28 : 0 }}>
              <LambdaGantt pairs={pairs} coupling={c} />
              {i < couplings.length - 1 && (
                <div style={{ height: 1, background: T.border, marginTop: 20 }} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Competitive constraint plot */}
      <div className="panel" style={{ marginBottom: 16 }}>
        <PanelHeader
          title="Competitive Constraint Comparison"
          icon="chart"
          sub="All matter (solid) and antimatter (dashed) curves for the selected coupling on one axes. Teal bands = λ overlap regions."
        />
        <div style={{ padding: "12px 16px 8px", display: "flex", gap: 10, flexWrap: "wrap", borderBottom: `1px solid ${T.border}` }}>
          <div>
            <label className="label">Coupling</label>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {couplings.map(c => (
                <button key={c}
                  className={`btn ${selCoupling === c ? "btn-primary" : "btn-ghost"}`}
                  style={{ fontSize: 11, fontFamily: T.mono }}
                  onClick={() => setSelCoupling(c)}
                >{c}</button>
              ))}
            </div>
          </div>
          <div style={{ width: 1, background: T.border, margin: "0 4px" }} />
          <div>
            <label className="label">Potential</label>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {potentials.map(p => (
                <button key={p}
                  className={`btn ${selPotential === p ? "btn-primary" : "btn-ghost"}`}
                  style={{ fontSize: 11, fontFamily: T.mono }}
                  onClick={() => setSelPotential(p)}
                >{p}</button>
              ))}
            </div>
          </div>
        </div>
        <div style={{ padding: "8px 4px" }}>
          <CompetitiveConstraintPlot pairs={pairs} coupling={selCoupling} potential={selPotential} />
        </div>
        <div style={{ padding: "8px 16px 12px", fontSize: 11, color: T.textDim, lineHeight: 1.6, borderTop: `1px solid ${T.border}` }}>
          <b style={{ color: T.textHi }}>Reading this plot:</b> Constraints that probe the same λ region
          allow direct comparison. When a matter curve lies{" "}
          <span style={{ color: T.blue }}>orders of magnitude below</span> its antimatter counterpart,
          |Aα| → 1 — which explains the near-maximal asymmetries in the results. This is not a CPT
          violation signal; it reflects the relative experimental sensitivities of the two datasets.
        </div>
      </div>

      {/* Cross-pair overlap matrix */}
      <OverlapMatrix pairs={pairs} />
    </div>
  );
};