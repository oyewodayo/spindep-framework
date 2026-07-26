import React, { useMemo, useState } from "react";
import { T, SIG } from "../../constants";
import { pvalColor, formatPval, buildCsvTable, buildLatexTable, downloadTextFile } from "../../utils";
import { Stat, PanelHeader, SearchBar, SigTag } from "../ui";
import { Icon } from "../ui/Icon";
import { PairDetail } from "./PairDetail";
import { useSort } from "../../hooks";
import type { AnalysisPair } from "../../types";

interface BatchResultsSectionProps {
  pairs: AnalysisPair[];
}

export const BatchResultsSection: React.FC<BatchResultsSectionProps> = ({ pairs }) => {
  const { sort, toggleSort } = useSort<AnalysisPair>("pval", "asc");
  const [query,           setQuery]           = useState("");
  const [filterCoupling,  setFilterCoupling]  = useState("All");
  const [selected,        setSelected]        = useState<AnalysisPair | null>(null);

  const couplings = useMemo(() => [...new Set(pairs.map(p => p.coupling))], [pairs]);

  const sorted = useMemo(() => {
    const filtered = pairs.filter(
      p =>
        (filterCoupling === "All" || p.coupling === filterCoupling) &&
        (!query || p.id?.toLowerCase().includes(query.toLowerCase()) ||
         p.matterDataset?.toLowerCase().includes(query.toLowerCase()) ||
         p.antimatterDataset?.toLowerCase().includes(query.toLowerCase()) ||
         p.interactionClass?.toLowerCase().includes(query.toLowerCase()))
    );
    return [...filtered].sort((a, b) => {
      const diff = (() => {
        switch (sort.key) {
          case "pval":         return a.pval - b.pval;
          case "meanAbsA":     return a.meanAbsA - b.meanAbsA;
          case "chi2Weighted": return a.chi2Weighted - b.chi2Weighted;
          case "chi2Uniform":  return a.chi2Uniform - b.chi2Uniform;
          case "chi2Ratio":    return (a.chi2Ratio ?? 0) - (b.chi2Ratio ?? 0);
          default:             return 0;
        }
      })();
      return sort.direction === "asc" ? diff : -diff;
    });
  }, [pairs, sort, query, filterCoupling]);

  const sig  = pairs.filter(p => p.pval < SIG.STANDARD).length;
  const hSig = pairs.filter(p => p.pval < SIG.HIGHLY).length;

  const SortTh: React.FC<{ col: keyof AnalysisPair; label: string }> = ({ col, label }) => (
    <th
      style={{ cursor: "pointer", userSelect: "none" }}
      onClick={() => toggleSort(col)}
    >
      {label} {sort.key === col ? (sort.direction === "asc" ? "↑" : "↓") : ""}
    </th>
  );

  if (pairs.length === 0) {
    return (
      <div className="fade-in" style={{ textAlign: "center", padding: 60, color: T.muted }}>
        <Icon name="table" size={40} />
        <div style={{ marginTop: 16, fontSize: 14, fontWeight: 600, color: T.textDim }}>
          No results yet
        </div>
        <div style={{ marginTop: 8, fontSize: 12 }}>
          Run the pipeline from the Ingest tab to load real data
        </div>
      </div>
    );
  }

  const interactionClasses = useMemo(() => [...new Set(pairs.map(p => p.interactionClass).filter(Boolean))], [pairs]);

  return (
    <div className="fade-in">
      <div className="split split-4" style={{ marginBottom: 18 }}>
        <Stat label="Total pairs"    value={pairs.length} />
        <Stat label="p < 0.05"       value={sig}  color={T.amber} sub="significant" />
        <Stat label="p < 0.001"      value={hSig} color={T.red}   sub="highly significant" />
        <Stat label="Coupling types" value={couplings.length} color={T.teal} />
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 14, alignItems: "center", flexWrap: "wrap" }}>
        <SearchBar
          value={query}
          onChange={setQuery}
          placeholder="Filter by coupling, dataset, interaction class…"
        />
        <select
          className="select"
          value={filterCoupling}
          onChange={e => setFilterCoupling(e.target.value)}
        >
          <option>All</option>
          {couplings.map(c => <option key={c}>{c}</option>)}
        </select>
        <button
          className="btn btn-ghost"
          style={{ marginLeft: "auto" }}
          disabled={sorted.length === 0}
          onClick={() => downloadTextFile(buildCsvTable(sorted), "cpt_pairs.csv")}
        >
          <Icon name="dl" size={12} /> Export CSV
        </button>
        <button
          className="btn btn-ghost"
          disabled={sorted.length === 0}
          onClick={() => downloadTextFile(buildLatexTable(sorted), "cpt_asymmetry_table.tex")}
        >
          <Icon name="dl" size={12} /> Export LaTeX
        </button>
      </div>

      <div className="panel" style={{ marginBottom: selected ? 16 : 0 }}>
        <div style={{ overflowX: "auto", maxHeight: 460, overflowY: "auto" }}>
          <table className="data-table">
            <thead style={{ position: "sticky", top: 0, background: T.panel }}>
              <tr>
                <th>Pair ID</th>
                <th>Coupling</th>
                <th>Potential</th>
                <th>Class</th>
                <th>Sectors</th>
                <SortTh col="meanAbsA"     label="|Aα| mean" />
                <SortTh col="chi2Uniform"  label="χ²(u)" />
                <SortTh col="chi2Weighted" label="χ²(w)" />
                <SortTh col="chi2Ratio"    label="χ² ratio" />
                <th>dof</th>
                <SortTh col="pval" label="p-val (w)" />
                <th>Sig.</th>
                <th>λ range (m)</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {sorted.map(p => (
                <tr
                  key={p.id}
                  onClick={() => setSelected(selected?.id === p.id ? null : p)}
                  style={{ cursor: "pointer" }}
                >
                  <td
                    style={{
                      color: T.textDim,
                      maxWidth: 130,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={p.id}
                  >
                    {p.id}
                  </td>
                  <td><span className="tag tag-blue">{p.coupling}</span></td>
                  <td><span className="tag tag-violet">{p.potential}</span></td>
                  <td style={{ color: T.textDim, fontSize: 10 }}>{p.interactionClass ?? "—"}</td>
                  <td style={{ color: T.textDim, fontFamily: T.mono, fontSize: 11 }}>
                    {p.secM} × {p.secA}
                  </td>
                  <td
                    style={{
                      color: p.meanAbsA >= 0.95 ? T.red : p.meanAbsA >= 0.5 ? T.amber : T.text,
                      fontWeight: p.meanAbsA >= 0.95 ? 700 : 400,
                    }}
                  >
                    {p.meanAbsA?.toFixed(4)}
                  </td>
                  <td style={{ color: T.textDim }}>{p.chi2Uniform?.toFixed(0)}</td>
                  <td>{p.chi2Weighted?.toFixed(0)}</td>
                  <td style={{ color: (p.chi2Ratio ?? 1) < 1 ? T.teal : T.amber, fontSize: 11 }}>
                    {p.chi2Ratio?.toFixed(3) ?? "—"}
                  </td>
                  <td style={{ color: T.textDim }}>{p.dof}</td>
                  <td style={{ color: pvalColor(p.pval) }}>{formatPval(p.pval)}</td>
                  <td><SigTag pval={p.pval} /></td>
                  <td style={{ color: T.textDim, fontSize: 10, fontFamily: T.mono }}>
                    {p.lambdaMin?.toExponential(2)}&nbsp;–&nbsp;{p.lambdaMax?.toExponential(2)}
                  </td>
                  <td>
                    <button className="btn btn-ghost btn-icon" style={{ padding: "3px 6px" }}>
                      <Icon name="chevron" size={11} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <PairDetail pair={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
};