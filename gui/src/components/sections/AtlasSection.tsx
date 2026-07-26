import React, { useMemo, useState, useEffect } from "react";
import {
  LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import { T } from "../../constants";
import { formatLogScale } from "../../utils";
import { PanelHeader, ChartTooltip } from "../ui";
import type { AnalysisPair } from "../../types";

interface AtlasSectionProps {
  pairs: AnalysisPair[];
}

const MATTER_COLORS    = [T.blue,  T.teal,   T.violet] as const;
const ANTIMATTER_COLORS = [T.amber, T.red,    "#ec4899"] as const;

export const AtlasSection: React.FC<AtlasSectionProps> = ({ pairs }) => {
  const couplings  = useMemo(() => [...new Set(pairs.map(p => p.coupling))].sort(),  [pairs]);
  const potentials = useMemo(() => [...new Set(pairs.map(p => p.potential))].sort(), [pairs]);

  const [selectedCoupling,  setSelectedCoupling]  = useState<string | null>(null);
  const [selectedPotential, setSelectedPotential] = useState<string | null>(null);

  useEffect(() => {
    if (couplings.length  && !selectedCoupling)  setSelectedCoupling(couplings[0]);
    if (potentials.length && !selectedPotential) setSelectedPotential(potentials[0]);
  }, [couplings, potentials]);

  const visiblePairs = pairs.filter(
    p => p.coupling === selectedCoupling && p.potential === selectedPotential
  );

  if (pairs.length === 0) {
    return (
      <div className="fade-in" style={{ textAlign: "center", padding: 60, color: T.muted }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: T.textDim }}>
          Run the pipeline first to see the constraint atlas
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 18 }}>
        <h2 style={{ color: T.textHi, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
          Constraint Atlas
        </h2>
        <p style={{ color: T.textDim, fontSize: 13 }}>
          Real coupling upper bounds from your experimental datasets.
        </p>
      </div>

      {/* Selectors */}
      <div style={{ display: "flex", gap: 10, marginBottom: 18, flexWrap: "wrap", alignItems: "center" }}>
        <div>
          <label className="label">Coupling</label>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {couplings.map(c => (
              <button
                key={c}
                className={`btn ${selectedCoupling === c ? "btn-primary" : "btn-ghost"}`}
                style={{ fontSize: 11, fontFamily: T.mono }}
                onClick={() => setSelectedCoupling(c)}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
        <div style={{ width: 1, height: 32, background: T.border, margin: "0 4px" }} />
        <div>
          <label className="label">Potential</label>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {potentials.map(p => (
              <button
                key={p}
                className={`btn ${selectedPotential === p ? "btn-primary" : "btn-ghost"}`}
                style={{ fontSize: 11, fontFamily: T.mono }}
                onClick={() => setSelectedPotential(p)}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      {visiblePairs.length > 0 ? (
        <div className="panel">
          <PanelHeader
            title={`${selectedCoupling} · ${selectedPotential} — Constraint curves`}
            icon="chart"
            sub="Upper bounds on coupling |g| vs interaction range λ"
          />
          <div style={{ padding: "12px 4px 8px" }}>
            <ResponsiveContainer width="100%" height={340}>
              <LineChart margin={{ top: 8, right: 20, left: 8, bottom: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                <XAxis
                  type="number"
                  dataKey="logLam"
                  domain={[-12, 6]}
                  tickFormatter={formatLogScale}
                  tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
                  label={{
                    value: "Interaction range λ (m)",
                    position: "insideBottom",
                    offset: -8,
                    fill: T.muted,
                    fontSize: 11,
                  }}
                />
                <YAxis
                  type="number"
                  tickFormatter={formatLogScale}
                  tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
                  width={54}
                  label={{
                    value: "Coupling |g|",
                    angle: -90,
                    position: "insideLeft",
                    fill: T.muted,
                    fontSize: 11,
                  }}
                />
                <Tooltip content={<ChartTooltip fmt={v => `10^(${v.toFixed(2)})`} />} />
                <Legend wrapperStyle={{ fontSize: 10, color: T.textDim, paddingTop: 8 }} />
                {visiblePairs.flatMap((p, i) => [
                  <Line
                    key={`m${i}`}
                    data={p.points}
                    type="monotone"
                    dataKey="logGm"
                    name={`${p.secM} (matter)`}
                    stroke={MATTER_COLORS[i % 3]}
                    strokeWidth={1.8}
                    dot={false}
                  />,
                  <Line
                    key={`a${i}`}
                    data={p.points}
                    type="monotone"
                    dataKey="logGa"
                    name={`${p.secA} (antimatter)`}
                    stroke={ANTIMATTER_COLORS[i % 3]}
                    strokeWidth={1.8}
                    dot={false}
                    strokeDasharray="6 3"
                  />,
                ])}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div style={{ textAlign: "center", padding: 48, color: T.muted }}>
          No data for {selectedCoupling} · {selectedPotential}
        </div>
      )}
    </div>
  );
};