import React, { useEffect, useMemo, useState } from "react";
import { T } from "../../constants";
import { apiClient } from "../../api/client";
import { PanelHeader } from "../ui";
import { Icon } from "../ui/Icon";
import type { GapMatrix } from "../../types";

// Exact palette from spindep/src/gap_analysis.py (plot_pair_coverage_matrix),
// reproduced here so this view matches the matplotlib PNG it stands in for.
const NAVY    = "#1a2e4a";
const STEEL   = "#2d6a9f";
const CRIMSON = "#b03a2e";
const LIGHT   = "#f4f6f9";
const WHITE   = "#ffffff";

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * Reproduces matplotlib's LinearSegmentedColormap.from_list("cov",
 * [LIGHT, STEEL, NAVY]) — a 3-stop colormap, equal-spaced, so t in [0, 0.5]
 * interpolates LIGHT->STEEL and t in [0.5, 1] interpolates STEEL->NAVY.
 */
function covColor(t: number): string {
  const clamped = Math.max(0, Math.min(1, t));
  const [a, b] = clamped <= 0.5
    ? [hexToRgb(LIGHT), hexToRgb(STEEL)]
    : [hexToRgb(STEEL), hexToRgb(NAVY)];
  const localT = clamped <= 0.5 ? clamped / 0.5 : (clamped - 0.5) / 0.5;
  const r = Math.round(lerp(a[0], b[0], localT));
  const g = Math.round(lerp(a[1], b[1], localT));
  const bl = Math.round(lerp(a[2], b[2], localT));
  return `rgb(${r}, ${g}, ${bl})`;
}

export const GapAnalysisSection: React.FC = () => {
  const [data, setData] = useState<GapMatrix | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hover, setHover] = useState<{ sector: string; potential: string; value: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .getGapMatrix()
      .then(m => { if (!cancelled) setData(m); })
      .catch(e => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); });
    return () => { cancelled = true; };
  }, []);

  const antimatterSet = useMemo(
    () => new Set(data?.antimatterSectors ?? []),
    [data]
  );

  if (error) {
    return (
      <div className="fade-in" style={{ textAlign: "center", padding: 60, color: T.red }}>
        <div style={{ fontSize: 14, fontWeight: 600 }}>Couldn't load the coverage matrix</div>
        <div style={{ fontSize: 12, color: T.textDim, marginTop: 6 }}>{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="fade-in" style={{ textAlign: "center", padding: 60, color: T.muted }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: T.textDim }}>Loading coverage matrix…</div>
      </div>
    );
  }

  const { potentials, sectors, sectorLabels, matrix, maxValue, totalDatasets } = data;

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ color: T.textHi, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
          Gap Analysis
        </h2>
        <p style={{ color: T.textDim, fontSize: 13 }}>
          {totalDatasets} classified datasets across {sectors.length} fermion sectors
          &nbsp;&times;&nbsp;{potentials.length} potentials — one cell per experimental dataset,
          not per matched pair.
        </p>
      </div>

      <div className="panel">
        <PanelHeader
          title="Dataset Coverage: Potential × Fermion Sector"
          icon="grid"
          sub="Reproduces figures/gap_analysis/pair_coverage_matrix.png from the compiled registry."
        />

        <div style={{ padding: 20, overflowX: "auto" }}>
          <div
            style={{
              background: WHITE,
              borderRadius: 8,
              padding: "28px 24px 20px",
              minWidth: 780,
            }}
          >
            <div style={{ textAlign: "center", color: NAVY, fontSize: 13, fontWeight: 700, marginBottom: 18 }}>
              Dataset Coverage: Potential × Fermion Sector
            </div>

            <div style={{ display: "flex", gap: 20 }}>
              {/* Grid: 1 label column + N potential columns */}
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: `108px repeat(${potentials.length}, minmax(38px, 1fr))`,
                  }}
                >
                  {/* corner cell */}
                  <div />
                  {potentials.map(p => (
                    <div
                      key={p}
                      style={{
                        display: "flex",
                        alignItems: "flex-end",
                        justifyContent: "center",
                        height: 46,
                        paddingBottom: 4,
                      }}
                    >
                      <span
                        style={{
                          display: "inline-block",
                          transform: "rotate(-45deg)",
                          transformOrigin: "bottom left",
                          fontSize: 10.5,
                          fontFamily: T.mono,
                          color: NAVY,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {p}
                      </span>
                    </div>
                  ))}

                  {sectors.map((sec, si) => (
                    <React.Fragment key={sec}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          fontSize: 11,
                          fontFamily: T.mono,
                          fontWeight: 600,
                          color: antimatterSet.has(sec) ? CRIMSON : STEEL,
                          paddingRight: 8,
                        }}
                      >
                        {sectorLabels[sec] ?? sec}
                      </div>
                      {potentials.map((pot, pi) => {
                        const val = matrix[si]?.[pi] ?? 0;
                        const t = maxValue > 0 ? val / maxValue : 0;
                        const textColor = val > maxValue * 0.5 ? WHITE : NAVY;
                        return (
                          <div
                            key={pot}
                            onMouseEnter={() => setHover({ sector: sectorLabels[sec] ?? sec, potential: pot, value: val })}
                            onMouseLeave={() => setHover(null)}
                            style={{
                              height: 26,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              background: covColor(t),
                              outline: hover?.sector === (sectorLabels[sec] ?? sec) && hover?.potential === pot
                                ? `2px solid ${NAVY}` : "1px solid rgba(26,46,74,0.06)",
                              outlineOffset: -1,
                              fontSize: 10,
                              fontWeight: 700,
                              fontFamily: T.mono,
                              color: textColor,
                              cursor: "default",
                            }}
                          >
                            {val > 0 ? val : ""}
                          </div>
                        );
                      })}
                    </React.Fragment>
                  ))}
                </div>

                <div style={{ textAlign: "center", fontSize: 10.5, color: NAVY, marginTop: 10, fontWeight: 600 }}>
                  Interaction Potential
                </div>
              </div>

              {/* Right rail: legend + colorbar */}
              <div style={{ width: 168, flexShrink: 0, display: "flex", flexDirection: "column", gap: 18 }}>
                <div
                  style={{
                    border: "1px solid rgba(26,46,74,0.15)",
                    borderRadius: 6,
                    padding: "10px 12px",
                    fontSize: 11,
                    color: NAVY,
                  }}
                >
                  {[
                    ["Matter sector", STEEL],
                    ["Antimatter sector", CRIMSON],
                    ["No data (gap)", LIGHT],
                  ].map(([label, color]) => (
                    <div key={label} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 5 }}>
                      <span
                        style={{
                          width: 11, height: 11, borderRadius: 2, background: color,
                          border: color === LIGHT ? "1px solid rgba(26,46,74,0.25)" : "none",
                          flexShrink: 0,
                        }}
                      />
                      <span>{label}</span>
                    </div>
                  ))}
                </div>

                <div>
                  <div style={{ fontSize: 10, color: NAVY, marginBottom: 6, textAlign: "center" }}>
                    Number of datasets
                  </div>
                  <div style={{ display: "flex", alignItems: "stretch", gap: 6 }}>
                    <div
                      style={{
                        width: 16,
                        height: 140,
                        borderRadius: 3,
                        background: `linear-gradient(to top, ${LIGHT}, ${STEEL} 50%, ${NAVY})`,
                        border: "1px solid rgba(26,46,74,0.15)",
                      }}
                    />
                    <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", fontSize: 10, color: NAVY, fontFamily: T.mono }}>
                      <span>{maxValue}</span>
                      <span>{Math.round(maxValue / 2)}</span>
                      <span>0</span>
                    </div>
                  </div>
                </div>

                {hover && (
                  <div
                    style={{
                      fontSize: 11,
                      color: NAVY,
                      background: LIGHT,
                      borderRadius: 6,
                      padding: "8px 10px",
                      lineHeight: 1.5,
                    }}
                  >
                    <div style={{ fontFamily: T.mono, fontWeight: 700 }}>{hover.sector} · {hover.potential}</div>
                    <div>{hover.value > 0 ? `${hover.value} dataset${hover.value === 1 ? "" : "s"}` : "No data — gap"}</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div style={{ padding: "0 20px 18px", display: "flex", justifyContent: "flex-end" }}>
          <button className="btn btn-ghost" style={{ fontSize: 12 }} onClick={() => apiClient.downloadGapAnalysis()}>
            <Icon name="dl" size={13} />
            Download all gap-analysis figures (.zip)
          </button>
        </div>
      </div>
    </div>
  );
};
