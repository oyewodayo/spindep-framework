import React from "react";
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { T } from "../../constants";
import { pvalColor, formatPval, formatLogScale, safeId } from "../../utils";
import { PanelHeader, ChartTooltip } from "../ui";
import { Icon } from "../ui/Icon";
import type { AnalysisPair } from "../../types";

interface PairDetailProps {
  pair: AnalysisPair;
  onClose: () => void;
}

export const PairDetail: React.FC<PairDetailProps> = ({ pair, onClose }) => {
  const pts = pair.points ?? [];
  const gradId = `gP_${safeId(pair.id)}`;

  // Interpretation text matching the report
  const asymmInterp = pair.meanAbsA >= 0.95
    ? "Strong asymmetry — large CPT-sensitive difference."
    : pair.meanAbsA >= 0.5
    ? "Moderate asymmetry — CPT-sensitive difference."
    : "Weak asymmetry.";

  const chi2RatioInterp = pair.chi2Ratio != null
    ? (pair.chi2Ratio < 1 ? "< 1 — weighted is more conservative" : "≥ 1 — uniform is more conservative")
    : "—";

  return (
    <div className="panel fade-in">
      <PanelHeader
        title={pair.id}
        icon="chart"
        right={
          <button className="btn btn-ghost btn-icon" onClick={onClose}>
            <Icon name="close" size={14} />
          </button>
        }
      />
      <div style={{ padding: 16 }}>

        {/* Metadata row — mirrors the report's dataset/class table */}
        <div
          className="split split-4"
          style={{
            gap: 8,
            marginBottom: 16,
            padding: "10px 14px",
            background: T.bg2,
            borderRadius: 8,
            border: `1px solid ${T.border}`,
            fontSize: 12,
          }}
        >
          {[
            ["Matter dataset",     pair.matterDataset     ?? "—"],
            ["Antimatter dataset", pair.antimatterDataset ?? "—"],
            ["Interaction class",  pair.interactionClass  ?? "—"],
            ["λ range",            `${pair.lambdaMin?.toExponential(2)} – ${pair.lambdaMax?.toExponential(2)} m`],
            ["Matter unit",        pair.matterUnit        ?? "—"],
            ["Antimatter unit",    pair.antimatterUnit    ?? "—"],
            ["Sector (matter)",    pair.secM              ?? "—"],
            ["Sector (antimatter)",pair.secA              ?? "—"],
          ].map(([k, v]) => (
            <div key={k as string}>
              <div style={{ fontSize: 9, color: T.textDim, textTransform: "uppercase", letterSpacing: ".09em", marginBottom: 2 }}>{k}</div>
              <div style={{ fontFamily: T.mono, color: T.textHi, fontSize: 11 }}>{v}</div>
            </div>
          ))}
        </div>

        {/* Primary statistics — all rows from the report */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 10, color: T.textDim, textTransform: "uppercase", letterSpacing: ".09em", fontWeight: 600, marginBottom: 8 }}>
            Statistics
          </div>
          <table className="data-table" style={{ background: T.bg2, borderRadius: 8, overflow: "hidden" }}>
            <thead>
              <tr>
                <th style={{ width: "28%" }}>Statistic</th>
                <th style={{ width: "22%" }}>Value</th>
                <th>Interpretation</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ color: T.textDim }}>Mean |A_α|</td>
                <td style={{ color: pair.meanAbsA >= 0.95 ? T.red : pair.meanAbsA >= 0.5 ? T.amber : T.teal, fontWeight: 700 }}>
                  {pair.meanAbsA?.toFixed(4)}
                </td>
                <td style={{ color: T.textDim }}>{asymmInterp}</td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>χ² (uniform 10%)</td>
                <td>{pair.chi2Uniform?.toFixed(1)}</td>
                <td style={{ color: T.textDim }}>dof = {pair.dof} {pair.pvalUniform < 0.001 ? <span className="tag tag-red" style={{ fontSize: 9 }}>*** p &lt; 0.001</span> : ""}</td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>χ² (weighted)</td>
                <td>{pair.chi2Weighted?.toFixed(1)}</td>
                <td style={{ color: T.textDim }}>dof = {pair.dof} {pair.pval < 0.001 ? <span className="tag tag-red" style={{ fontSize: 9 }}>*** p &lt; 0.001</span> : ""}</td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>p-value (uniform)</td>
                <td style={{ color: pvalColor(pair.pvalUniform ?? pair.pval) }}>
                  {pair.pvalUniform != null ? formatPval(pair.pvalUniform) : formatPval(pair.pval)}
                </td>
                <td style={{ color: T.textDim }}>Assumes flat 10% uncertainty at every point</td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>p-value (weighted)</td>
                <td style={{ color: pvalColor(pair.pval) }}>{formatPval(pair.pval)}</td>
                <td style={{ color: T.textDim }}>
                  Nominal — assumes all {pair.dof} grid points are independent dof
                </td>
              </tr>
              {pair.dofEffective != null && (
                <tr>
                  <td style={{ color: T.textDim }}>dof (effective)</td>
                  <td>{pair.dofEffective}</td>
                  <td style={{ color: T.textDim }}>
                    Autocorrelation length ≈ {pair.autocorrLength?.toFixed(1) ?? "—"} grid points
                  </td>
                </tr>
              )}
              {pair.pvalEffective != null && (
                <tr>
                  <td style={{ color: T.textDim }}>p-value (effective dof)</td>
                  <td style={{ color: pvalColor(pair.pvalEffective) }}>{formatPval(pair.pvalEffective)}</td>
                  <td style={{ color: T.teal, fontSize: 11 }}>Preferred for thesis</td>
                </tr>
              )}
              {(pair.aalphaCiLow != null && pair.aalphaCiHigh != null) && (
                <tr>
                  <td style={{ color: T.textDim }}>|A_α| 95% CI</td>
                  <td>[{pair.aalphaCiLow.toFixed(4)}, {pair.aalphaCiHigh.toFixed(4)}]</td>
                  <td style={{ color: T.textDim }}>Bootstrap CI on mean |A_α|</td>
                </tr>
              )}
              <tr>
                <td style={{ color: T.textDim }}>χ² ratio (w/u)</td>
                <td style={{ color: pair.chi2Ratio < 1 ? T.teal : T.amber }}>
                  {pair.chi2Ratio?.toFixed(3) ?? "—"}
                </td>
                <td style={{ color: T.textDim }}>{chi2RatioInterp}</td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>Mean σ_matter</td>
                <td>{pair.sigmaM?.toFixed(1)}%</td>
                <td style={{ color: T.textDim }}>Per-point uncertainty from curve curvature</td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>Mean σ_antimatter</td>
                <td>{pair.sigmaA?.toFixed(1)}%</td>
                <td style={{ color: T.textDim }}>Per-point uncertainty from curve curvature</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="split split-2">
          {/* Coupling bounds */}
          <div>
            <div
              style={{
                fontSize: 11,
                color: T.textDim,
                marginBottom: 8,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: ".08em",
              }}
            >
              Coupling Upper Bounds (log–log)
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={pts} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                <XAxis
                  dataKey="logLam"
                  tickFormatter={formatLogScale}
                  tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
                />
                <YAxis
                  tickFormatter={formatLogScale}
                  tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
                  width={48}
                />
                <Tooltip content={<ChartTooltip fmt={v => `10^${v.toFixed(2)}`} />} />
                <Line
                  type="monotone"
                  dataKey="logGm"
                  name={`Matter (${pair.secM})`}
                  stroke={T.blue}
                  strokeWidth={1.8}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="logGa"
                  name={`Antimatter (${pair.secA})`}
                  stroke={T.amber}
                  strokeWidth={1.8}
                  dot={false}
                  strokeDasharray="5 3"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* CPT Asymmetry */}
          <div>
            <div
              style={{
                fontSize: 11,
                color: T.textDim,
                marginBottom: 8,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: ".08em",
              }}
            >
              CPT Asymmetry Aα
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={pts} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor={T.blue} stopOpacity={0.4} />
                    <stop offset="100%" stopColor={T.blue} stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                <XAxis
                  dataKey="logLam"
                  tickFormatter={formatLogScale}
                  tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
                />
                <YAxis
                  domain={[-1.1, 1.1]}
                  tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
                  width={36}
                />
                <Tooltip content={<ChartTooltip fmt={v => v.toFixed(4)} />} />
                <ReferenceLine y={0} stroke={T.muted} strokeDasharray="4 4" />
                <Area
                  type="monotone"
                  dataKey="A"
                  name="Aα"
                  stroke={T.blue}
                  fill={`url(#${gradId})`}
                  strokeWidth={1.5}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};