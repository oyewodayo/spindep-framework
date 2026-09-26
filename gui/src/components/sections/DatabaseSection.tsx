import React, { useEffect, useMemo, useState } from "react";
import { T } from "../../constants";
import { apiClient } from "../../api/client";
import { PanelHeader, Stat } from "../ui";
import { Icon } from "../ui/Icon";
import type { Registry, RegistryRecord } from "../../types";

/**
 * The compiled database, as the pipeline recorded it.
 *
 * Every other results view is built from matched *pairs*, which cover only a
 * handful of datasets. This one reads the registry, so it reports the same
 * compiled / excluded / analysed totals as the pipeline and the write-up, and
 * shows which datasets were held out of the analysis and on what grounds.
 */

/** The eleven canonical matter–antimatter sector pairs used by the pipeline. */
const SECTOR_PAIRS: [string, string][] = [
  ["ee", "eebar"], ["ep", "epbar"], ["emu", "emubar"], ["en", "enbar"],
  ["mumu", "mumubar"], ["np", "npbar"], ["nn", "nnbar"], ["pp", "ppbar"],
  ["eN", "eNbar"], ["nN", "nNbar"], ["pN", "pNbar"],
];

const SECTOR_LABEL: Record<string, string> = {
  ee: "e-e", eebar: "e-e⁺", ep: "e-p", epbar: "e-p̄", emu: "e-μ", emubar: "e-μ̄",
  en: "e-n", enbar: "e-n̄", mumu: "μ-μ", mumubar: "μ-μ̄", np: "n-p", npbar: "n-p̄",
  nn: "n-n", nnbar: "n-n̄", pp: "p-p", ppbar: "p-p̄", eN: "e-N", eNbar: "e-N̄",
  nN: "n-N", nNbar: "n-N̄", pN: "p-N", pNbar: "p-N̄",
};

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div style={{ background: T.surface, borderRadius: 3, height: 8, width: "100%", overflow: "hidden" }}>
      <div style={{ width: `${pct}%`, background: color, height: "100%", borderRadius: 3 }} />
    </div>
  );
}

function CountTable({ title, counts }: { title: string; counts: Record<string, number> }) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(e => e[1]), 1);
  return (
    <div style={{ flex: 1, minWidth: 240 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.6,
                    color: T.textDim, marginBottom: 8 }}>{title}</div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <tbody>
          {entries.map(([k, v]) => (
            <tr key={k}>
              <td style={{ fontFamily: T.mono, padding: "3px 8px 3px 0", whiteSpace: "nowrap" }}>{k}</td>
              <td style={{ width: "100%", padding: "3px 8px" }}>
                <Bar value={v} max={max} color={T.blue} />
              </td>
              <td style={{ fontFamily: T.mono, textAlign: "right", padding: "3px 0" }}>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const DatabaseSection: React.FC = () => {
  const [reg, setReg] = useState<Registry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [showExcluded, setShowExcluded] = useState(false);

  useEffect(() => {
    let alive = true;
    apiClient.getRegistry()
      .then(r => { if (alive) setReg(r); })
      .catch(e => { if (alive) setError(String(e)); });
    return () => { alive = false; };
  }, []);

  const sectorRows = useMemo(() => {
    if (!reg) return [];
    const analysed = reg.records.filter(r => !r.excluded);
    const count = (s: string) => analysed.filter(r => r.sector === s).length;
    return SECTOR_PAIRS.map(([m, a]) => {
      const nm = count(m), na = count(a);
      let status = "Populated";
      if (nm === 0 && na === 0) status = "No data either side";
      else if (na === 0 && nm >= 8) status = "Gap";
      else if (na === 0) status = "Gap (thin)";
      return { m, a, nm, na, status };
    });
  }, [reg]);

  const filtered = useMemo(() => {
    if (!reg) return [] as RegistryRecord[];
    const q = query.trim().toLowerCase();
    return reg.records
      .filter(r => (showExcluded ? r.excluded : !r.excluded))
      .filter(r => !q || r.filename.toLowerCase().includes(q)
                      || r.coupling.toLowerCase().includes(q)
                      || r.potential.toLowerCase().includes(q)
                      || r.sector.toLowerCase().includes(q));
  }, [reg, query, showExcluded]);

  if (error) {
    return (
      <div className="panel">
        <PanelHeader title="Database" icon={<Icon name="layers" />} />
        <div style={{ padding: 24, color: T.textDim, fontSize: 13 }}>
          Could not load the registry: {error}
          <div style={{ marginTop: 8 }}>Run the pipeline once to generate it.</div>
        </div>
      </div>
    );
  }
  if (!reg) {
    return (
      <div className="panel">
        <PanelHeader title="Database" icon={<Icon name="layers" />} />
        <div style={{ padding: 24, color: T.textDim, fontSize: 13 }}>Loading registry…</div>
      </div>
    );
  }

  const s = reg.summary;
  const maxSector = Math.max(...sectorRows.map(r => r.nm), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="panel">
        <PanelHeader
          title="Compiled database"
          icon={<Icon name="layers" />}
          sub="Read from the pipeline's dataset registry — the same file the write-up quotes"
        />
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", padding: "4px 0 12px" }}>
          <Stat label="Compiled"   value={s.compiled} />
          <Stat label="Excluded"   value={s.excluded} color={T.amber} />
          <Stat label="Analysed"   value={s.analysed} color={T.blue} />
          <Stat label="Matter"     value={s.matter} />
          <Stat label="Antimatter" value={s.antimatter} color={T.red}
                sub={`${((s.antimatter / Math.max(s.analysed, 1)) * 100).toFixed(1)}% of analysed`} />
        </div>
        <div style={{ fontSize: 12, color: T.textDim, lineHeight: 1.6 }}>
          {s.compiled} datasets compiled, {s.excluded} held out, {s.analysed} analysed.
          Only {s.antimatter} involve an antimatter sector — the coverage gap this
          framework exists to quantify.
        </div>
      </div>

      <div className="panel">
        <PanelHeader title="Breakdown" icon={<Icon name="chart" />} sub="Analysed datasets only" />
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <CountTable title="By coupling family" counts={s.byCoupling} />
          <CountTable title="By DM potential"    counts={s.byPotential} />
        </div>
      </div>

      <div className="panel">
        <PanelHeader
          title="Coverage by fermion sector"
          icon={<Icon name="scope" />}
          sub="Canonical matter–antimatter sector pairs, counted over the analysed set"
        />
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ color: T.textDim, textAlign: "left" }}>
              <th style={{ padding: "6px 8px 6px 0" }}>Matter</th>
              <th style={{ padding: "6px 8px" }}>Antimatter</th>
              <th style={{ padding: "6px 8px", width: "40%" }}>Matter-sector datasets</th>
              <th style={{ padding: "6px 8px", textAlign: "right" }}>M</th>
              <th style={{ padding: "6px 8px", textAlign: "right" }}>A</th>
              <th style={{ padding: "6px 8px" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {sectorRows.map(r => {
              const isGap = r.status.startsWith("Gap");
              return (
                <tr key={r.m} style={{ borderTop: `1px solid ${T.border}` }}>
                  <td style={{ fontFamily: T.mono, padding: "5px 8px 5px 0" }}>{SECTOR_LABEL[r.m] ?? r.m}</td>
                  <td style={{ fontFamily: T.mono, padding: "5px 8px", color: T.textDim }}>{SECTOR_LABEL[r.a] ?? r.a}</td>
                  <td style={{ padding: "5px 8px" }}>
                    <Bar value={r.nm} max={maxSector} color={isGap ? T.red : T.blue} />
                  </td>
                  <td style={{ fontFamily: T.mono, textAlign: "right", padding: "5px 8px" }}>{r.nm}</td>
                  <td style={{ fontFamily: T.mono, textAlign: "right", padding: "5px 8px",
                               color: r.na === 0 ? T.red : T.text }}>{r.na}</td>
                  <td style={{ padding: "5px 8px", color: isGap ? T.red : T.textDim,
                               fontWeight: isGap ? 600 : 400 }}>{r.status}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div style={{ fontSize: 11, color: T.textDim, marginTop: 10, lineHeight: 1.6 }}>
          A row with matter-sector data and zero antimatter is a measurement
          opportunity, not a null result. These are the channels where a new
          antimatter-sector bound would have most effect.
        </div>
      </div>

      <div className="panel">
        <PanelHeader
          title="Exclusions"
          icon={<Icon name="validate" />}
          sub={`${s.excluded} datasets compiled into the registry but held out of the analysis`}
        />
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <tbody>
            {s.exclusionReasons.map(e => (
              <tr key={e.reason} style={{ borderTop: `1px solid ${T.border}` }}>
                <td style={{ fontFamily: T.mono, textAlign: "right", padding: "6px 12px 6px 0",
                             color: T.amber, width: 48 }}>{e.count}</td>
                <td style={{ padding: "6px 0", lineHeight: 1.5 }}>{e.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ fontSize: 11, color: T.textDim, marginTop: 10, lineHeight: 1.6 }}>
          Each exclusion is recorded individually with a stated reason rather
          than applied by a blanket rule, so the difference between what was
          compiled and what was analysed stays auditable.
        </div>
      </div>

      <div className="panel">
        <PanelHeader
          title={showExcluded ? "Excluded datasets" : "Analysed datasets"}
          icon={<Icon name="table" />}
          right={
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="filter by name, coupling, potential, sector"
                style={{ background: T.surface, border: `1px solid ${T.border}`, color: T.text,
                         borderRadius: 4, padding: "4px 8px", fontSize: 12, width: 260 }}
              />
              <button
                onClick={() => setShowExcluded(v => !v)}
                style={{ background: showExcluded ? T.amber : T.surface,
                         color: showExcluded ? "#000" : T.text,
                         border: `1px solid ${T.border}`, borderRadius: 4,
                         padding: "4px 10px", fontSize: 12, cursor: "pointer" }}
              >
                {showExcluded ? "Showing excluded" : "Show excluded"}
              </button>
            </div>
          }
        />
        <div style={{ maxHeight: 420, overflow: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
            <thead>
              <tr style={{ color: T.textDim, textAlign: "left", position: "sticky", top: 0, background: T.panel }}>
                <th style={{ padding: "6px 8px 6px 0" }}>Dataset</th>
                <th style={{ padding: "6px 8px" }}>Coupling</th>
                <th style={{ padding: "6px 8px" }}>Potential</th>
                <th style={{ padding: "6px 8px" }}>Sector</th>
                {showExcluded && <th style={{ padding: "6px 8px" }}>Reason</th>}
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.filepath || r.filename} style={{ borderTop: `1px solid ${T.border}` }}>
                  <td style={{ fontFamily: T.mono, padding: "4px 8px 4px 0" }}>
                    {r.filename}
                    {r.isAntimatter && (
                      <span style={{ color: T.red, marginLeft: 6, fontSize: 10 }}>antimatter</span>
                    )}
                  </td>
                  <td style={{ padding: "4px 8px", color: T.textDim }}>{r.coupling}</td>
                  <td style={{ fontFamily: T.mono, padding: "4px 8px" }}>{r.potential}</td>
                  <td style={{ fontFamily: T.mono, padding: "4px 8px", color: T.textDim }}>{r.sector}</td>
                  {showExcluded && (
                    <td style={{ padding: "4px 8px", color: T.amber, lineHeight: 1.4 }}>
                      {r.exclusionReason ?? "—"}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ fontSize: 11, color: T.textDim, marginTop: 8 }}>
          Showing {filtered.length} of {showExcluded ? s.excluded : s.analysed}
        </div>
      </div>
    </div>
  );
};
