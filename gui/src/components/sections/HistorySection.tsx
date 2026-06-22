import React, { useState, useMemo } from "react";
import { T, SIG } from "../../constants";
import { Icon } from "../ui/Icon";
import { Stat, PanelHeader } from "../ui";
import type { RunRecord, AnalysisPair } from "../../types";

interface HistorySectionProps {
  history:     RunRecord[];
  activeRunId: string | null;
  onRestore:   (pairs: AnalysisPair[]) => void;
  onDelete:    (id: string) => void;
  onRename:    (id: string, label: string) => void;
  onClear:     () => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function modeTag(mode: string) {
  const cfg: Record<string, { cls: string; label: string }> = {
    full:     { cls: "tag-blue",   label: "full" },
    validate: { cls: "tag-teal",   label: "validate" },
    gaps:     { cls: "tag-violet", label: "gaps" },
    atlas:    { cls: "tag-amber",  label: "atlas" },
  };
  const c = cfg[mode] ?? { cls: "tag-muted", label: mode };
  return <span className={`tag ${c.cls}`}>{c.label}</span>;
}

function formatTs(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1)   return "just now";
  if (mins < 60)  return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ─── Config diff between two runs ─────────────────────────────────────────────

interface DiffResult {
  addedDatasets:   string[];
  removedDatasets: string[];
  addedCouplings:  string[];
  removedCouplings: string[];
  pairDelta:       number;
  sigDelta:        number;
  absADelta:       number;
}

function diffRuns(a: RunRecord, b: RunRecord): DiffResult {
  const aDsets = new Set(a.summary.datasets);
  const bDsets = new Set(b.summary.datasets);
  const aCoups = new Set(a.summary.couplings);
  const bCoups = new Set(b.summary.couplings);
  return {
    addedDatasets:    [...bDsets].filter(d => !aDsets.has(d)),
    removedDatasets:  [...aDsets].filter(d => !bDsets.has(d)),
    addedCouplings:   [...bCoups].filter(c => !aCoups.has(c)),
    removedCouplings: [...aCoups].filter(c => !bCoups.has(c)),
    pairDelta:        b.summary.nPairs - a.summary.nPairs,
    sigDelta:         b.summary.nSignificant - a.summary.nSignificant,
    absADelta:        b.summary.avgAbsA - a.summary.avgAbsA,
  };
}

// ─── Run detail drawer ────────────────────────────────────────────────────────

function RunDrawer({
  record, isActive, onRestore, onClose,
}: {
  record:    RunRecord;
  isActive:  boolean;
  onRestore: () => void;
  onClose:   () => void;
}) {
  const [tab, setTab] = useState<"summary" | "log" | "pairs">("summary");

  return (
    <div className="panel fade-in" style={{ margin: "4px 0 8px" }}>
      <PanelHeader
        title={record.label}
        icon="report"
        sub={`${formatTs(record.timestamp)} · job: ${record.id}`}
        right={
          <div style={{ display: "flex", gap: 6 }}>
            {!isActive && (
              <button className="btn btn-primary" style={{ fontSize: 11 }} onClick={onRestore}>
                <Icon name="play" size={12} /> Restore to active
              </button>
            )}
            {isActive && (
              <span className="tag tag-teal" style={{ alignSelf: "center" }}>Active</span>
            )}
            <button className="btn btn-ghost btn-icon" onClick={onClose}>
              <Icon name="close" size={13} />
            </button>
          </div>
        }
      />

      {/* Tabs */}
      <div style={{
        display: "flex", gap: 0, borderBottom: `1px solid ${T.border}`,
        padding: "0 16px",
      }}>
        {(["summary", "log", "pairs"] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              background: "none", border: "none", cursor: "pointer",
              padding: "8px 14px", fontSize: 12,
              color: tab === t ? T.blue : T.textDim,
              borderBottom: tab === t ? `2px solid ${T.blue}` : "2px solid transparent",
              fontFamily: T.sans, fontWeight: tab === t ? 600 : 400,
              textTransform: "capitalize",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div style={{ padding: 16 }}>
        {tab === "summary" && (
          <div>
            {/* Stats grid */}
            <div className="split split-4" style={{ marginBottom: 16 }}>
              <Stat label="Pairs"       value={record.summary.nPairs} />
              <Stat label="Significant" value={record.summary.nSignificant}
                color={record.summary.nSignificant > 0 ? T.red : T.teal} />
              <Stat label="Avg |Aα|"    value={record.summary.avgAbsA.toFixed(4)}
                color={record.summary.avgAbsA >= 0.95 ? T.red : T.text} />
              <Stat label="Mode"        value={modeTag(record.mode)} />
            </div>

            {/* Config fingerprint */}
            <div style={{
              padding: "10px 14px", background: T.bg2, borderRadius: 8,
              border: `1px solid ${T.border}`, marginBottom: 12,
            }}>
              <div style={{ fontSize: 10, color: T.textDim, textTransform: "uppercase", letterSpacing: ".09em", marginBottom: 8, fontWeight: 600 }}>
                Reproducibility fingerprint
              </div>
              <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: 9, color: T.muted, textTransform: "uppercase", marginBottom: 2 }}>Config hash</div>
                  <div style={{ fontFamily: T.mono, color: T.blue, fontSize: 12 }}>{record.configHash}</div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: T.muted, textTransform: "uppercase", marginBottom: 2 }}>Job ID</div>
                  <div style={{ fontFamily: T.mono, color: T.textDim, fontSize: 12 }}>{record.id}</div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: T.muted, textTransform: "uppercase", marginBottom: 2 }}>Timestamp</div>
                  <div style={{ fontFamily: T.mono, color: T.textDim, fontSize: 12 }}>{record.timestamp}</div>
                </div>
              </div>
            </div>

            {/* Datasets */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: T.textDim, textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 600, marginBottom: 6 }}>
                Datasets ({record.summary.datasets.length})
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                {record.summary.datasets.map(d => (
                  <span key={d} className="tag tag-muted" style={{ fontFamily: T.mono, fontSize: 10 }}>{d}</span>
                ))}
              </div>
            </div>

            {/* Couplings */}
            <div>
              <div style={{ fontSize: 10, color: T.textDim, textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 600, marginBottom: 6 }}>
                Couplings
              </div>
              <div style={{ display: "flex", gap: 5 }}>
                {record.summary.couplings.map(c => (
                  <span key={c} className="tag tag-blue">{c}</span>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === "log" && (
          <div style={{
            fontFamily: T.mono, fontSize: 11, lineHeight: 1.8,
            maxHeight: 320, overflowY: "auto",
            background: T.bg0, borderRadius: 6, padding: 12,
            border: `1px solid ${T.border}`,
          }}>
            {record.log.length === 0 && (
              <div style={{ color: T.muted }}>No log stored for this run.</div>
            )}
            {record.log.map((line, i) => {
              const col = line.includes("[OK]") || line.includes("OK") ? T.teal
                : line.includes("[WARN]") || line.includes("WARN") ? T.amber
                : line.includes("[ERR]") || line.includes("ERROR") ? T.red
                : T.textDim;
              return <div key={i} style={{ color: col }}>{line}</div>;
            })}
          </div>
        )}

        {tab === "pairs" && (
          <div style={{ overflowX: "auto", maxHeight: 320, overflowY: "auto" }}>
            <table className="data-table">
              <thead style={{ position: "sticky", top: 0, background: T.panel }}>
                <tr>
                  <th>Pair ID</th>
                  <th>Coupling</th>
                  <th>Potential</th>
                  <th>|Aα|</th>
                  <th>p-value</th>
                  <th>χ² ratio</th>
                </tr>
              </thead>
              <tbody>
                {record.pairs.map(p => (
                  <tr key={p.id}>
                    <td style={{ fontFamily: T.mono, fontSize: 10, color: T.textDim }}>{p.id}</td>
                    <td><span className="tag tag-blue">{p.coupling}</span></td>
                    <td><span className="tag tag-violet">{p.potential}</span></td>
                    <td style={{ color: p.meanAbsA >= 0.95 ? T.red : T.text }}>{p.meanAbsA?.toFixed(4)}</td>
                    <td style={{ color: p.pval < SIG.HIGHLY ? T.red : T.text, fontFamily: T.mono, fontSize: 11 }}>
                      {p.pval < 1e-9 ? "<10⁻⁹" : p.pval?.toExponential(2)}
                    </td>
                    <td style={{ color: (p.chi2Ratio ?? 1) < 1 ? T.teal : T.amber, fontFamily: T.mono, fontSize: 11 }}>
                      {p.chi2Ratio?.toFixed(3) ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Run diff panel ───────────────────────────────────────────────────────────

function DiffPanel({ a, b }: { a: RunRecord; b: RunRecord }) {
  const diff = diffRuns(a, b);
  const hasChanges = diff.addedDatasets.length + diff.removedDatasets.length +
    diff.addedCouplings.length + diff.removedCouplings.length > 0;

  return (
    <div className="panel fade-in" style={{ marginBottom: 16 }}>
      <PanelHeader
        title={`Diff: "${a.label}" → "${b.label}"`}
        icon="layers"
        sub="Changes between selected runs"
      />
      <div style={{ padding: 16 }}>
        {/* Numeric deltas */}
        <div className="split split-4" style={{ marginBottom: 14 }}>
          <Stat label="Pairs Δ"
            value={`${diff.pairDelta >= 0 ? "+" : ""}${diff.pairDelta}`}
            color={diff.pairDelta > 0 ? T.teal : diff.pairDelta < 0 ? T.red : T.textDim} />
          <Stat label="Significant Δ"
            value={`${diff.sigDelta >= 0 ? "+" : ""}${diff.sigDelta}`}
            color={diff.sigDelta !== 0 ? T.amber : T.textDim} />
          <Stat label="Avg |Aα| Δ"
            value={`${diff.absADelta >= 0 ? "+" : ""}${diff.absADelta.toFixed(4)}`}
            color={Math.abs(diff.absADelta) > 0.01 ? T.amber : T.textDim} />
          <Stat label="Config hash"
            value={a.configHash === b.configHash ? "identical" : "changed"}
            color={a.configHash === b.configHash ? T.teal : T.amber} />
        </div>

        {hasChanges ? (
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {diff.addedDatasets.length > 0 && (
              <div>
                <div style={{ fontSize: 10, color: T.teal, marginBottom: 4, fontWeight: 600 }}>
                  + Datasets added
                </div>
                {diff.addedDatasets.map(d => (
                  <span key={d} className="tag tag-teal" style={{ marginRight: 4, fontFamily: T.mono }}>{d}</span>
                ))}
              </div>
            )}
            {diff.removedDatasets.length > 0 && (
              <div>
                <div style={{ fontSize: 10, color: T.red, marginBottom: 4, fontWeight: 600 }}>
                  − Datasets removed
                </div>
                {diff.removedDatasets.map(d => (
                  <span key={d} className="tag tag-red" style={{ marginRight: 4, fontFamily: T.mono }}>{d}</span>
                ))}
              </div>
            )}
            {diff.addedCouplings.length > 0 && (
              <div>
                <div style={{ fontSize: 10, color: T.teal, marginBottom: 4, fontWeight: 600 }}>
                  + Couplings added
                </div>
                {diff.addedCouplings.map(c => (
                  <span key={c} className="tag tag-teal" style={{ marginRight: 4 }}>{c}</span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div style={{ color: T.teal, fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
            <Icon name="check" size={14} />
            Same datasets and couplings — only statistical differences.
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main section ─────────────────────────────────────────────────────────────

export const HistorySection: React.FC<HistorySectionProps> = ({
  history, activeRunId, onRestore, onDelete, onRename, onClear,
}) => {
  const [expanded,    setExpanded]    = useState<string | null>(null);
  const [diffA,       setDiffA]       = useState<string | null>(null);
  const [diffB,       setDiffB]       = useState<string | null>(null);
  const [editingId,   setEditingId]   = useState<string | null>(null);
  const [editLabel,   setEditLabel]   = useState("");
  const [confirmClear, setConfirmClear] = useState(false);

  const diffPairA = history.find(r => r.id === diffA);
  const diffPairB = history.find(r => r.id === diffB);

  const configGroups = useMemo(() => {
    const groups = new Map<string, RunRecord[]>();
    for (const r of history) {
      const existing = groups.get(r.configHash) ?? [];
      groups.set(r.configHash, [...existing, r]);
    }
    return groups;
  }, [history]);

  if (history.length === 0) {
    return (
      <div className="fade-in" style={{ textAlign: "center", padding: 60, color: T.muted }}>
        <Icon name="layers" size={40} />
        <div style={{ marginTop: 16, fontSize: 14, fontWeight: 600, color: T.textDim }}>
          No run history yet
        </div>
        <div style={{ marginTop: 8, fontSize: 12 }}>
          Run the pipeline to start recording history. Runs persist across page refreshes.
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ color: T.textHi, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
          Run History
        </h2>
        <p style={{ color: T.textDim, fontSize: 13 }}>
          Every pipeline run is saved locally with its full results, log, and a
          reproducibility fingerprint. Restore any run to make it the active analysis.
        </p>
      </div>

      {/* Summary stats */}
      <div className="split split-4" style={{ marginBottom: 18 }}>
        <Stat label="Total runs"       value={history.length} />
        <Stat label="Unique configs"   value={configGroups.size} color={T.teal}
          sub="distinct config hashes" />
        <Stat label="Active run"
          value={activeRunId ? history.find(r => r.id === activeRunId)?.label?.slice(0, 16) + "…" ?? "—" : "none"}
          color={activeRunId ? T.blue : T.muted} />
        <Stat label="Stored locally"
          value={`${Math.round(JSON.stringify(history).length / 1024)} KB`}
          color={T.textDim} sub="localStorage" />
      </div>

      {/* Diff controls */}
      {history.length >= 2 && (
        <div className="panel" style={{ padding: "12px 16px", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, color: T.textDim, fontWeight: 600 }}>
              Compare runs:
            </span>
            <select className="select" value={diffA ?? ""} onChange={e => setDiffA(e.target.value || null)}>
              <option value="">Select run A…</option>
              {history.map(r => (
                <option key={r.id} value={r.id}>{r.label}</option>
              ))}
            </select>
            <span style={{ color: T.muted }}>→</span>
            <select className="select" value={diffB ?? ""} onChange={e => setDiffB(e.target.value || null)}>
              <option value="">Select run B…</option>
              {history.map(r => (
                <option key={r.id} value={r.id}>{r.label}</option>
              ))}
            </select>
            {(diffA || diffB) && (
              <button className="btn btn-ghost" style={{ fontSize: 11 }}
                onClick={() => { setDiffA(null); setDiffB(null); }}>
                <Icon name="close" size={11} /> Clear
              </button>
            )}
          </div>
        </div>
      )}

      {/* Diff result */}
      {diffPairA && diffPairB && diffPairA.id !== diffPairB.id && (
        <DiffPanel a={diffPairA} b={diffPairB} />
      )}

      {/* History table */}
      <div className="panel" style={{ marginBottom: 16 }}>
        <PanelHeader
          title="All Runs"
          icon="table"
          sub="Click any row to expand. Runs with identical config hash used the same datasets."
          right={
            <div style={{ display: "flex", gap: 6 }}>
              {confirmClear ? (
                <>
                  <span style={{ fontSize: 11, color: T.red, alignSelf: "center" }}>Confirm delete all?</span>
                  <button className="btn btn-ghost" style={{ fontSize: 11, color: T.red, borderColor: T.red }}
                    onClick={() => { onClear(); setConfirmClear(false); }}>
                    Yes, delete
                  </button>
                  <button className="btn btn-ghost" style={{ fontSize: 11 }}
                    onClick={() => setConfirmClear(false)}>
                    Cancel
                  </button>
                </>
              ) : (
                <button className="btn btn-ghost" style={{ fontSize: 11 }}
                  onClick={() => setConfirmClear(true)}>
                  <Icon name="close" size={11} /> Clear all
                </button>
              )}
            </div>
          }
        />
        <div>
          {history.map((record, idx) => {
            const isActive   = record.id === activeRunId;
            const isExpanded = expanded === record.id;
            const isEditing  = editingId === record.id;
            // Are there other runs with the same config hash?
            const sameConfig = (configGroups.get(record.configHash) ?? []).length > 1;

            return (
              <div key={record.id}>
                <div
                  style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "10px 16px",
                    borderBottom: idx < history.length - 1 ? `1px solid ${T.border}20` : "none",
                    background: isActive ? `${T.blueDim}60` : isExpanded ? T.bg2 : "transparent",
                    cursor: "pointer",
                    transition: "background .1s",
                  }}
                  onClick={() => setExpanded(isExpanded ? null : record.id)}
                >
                  {/* Active indicator */}
                  <div style={{
                    width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                    background: isActive ? T.teal : T.border,
                  }} />

                  {/* Label — editable on double-click */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {isEditing ? (
                      <input
                        className="input"
                        style={{ fontSize: 12, padding: "3px 8px", width: "100%" }}
                        value={editLabel}
                        autoFocus
                        onChange={e => setEditLabel(e.target.value)}
                        onBlur={() => {
                          if (editLabel.trim()) onRename(record.id, editLabel.trim());
                          setEditingId(null);
                        }}
                        onKeyDown={e => {
                          if (e.key === "Enter") {
                            if (editLabel.trim()) onRename(record.id, editLabel.trim());
                            setEditingId(null);
                          }
                          if (e.key === "Escape") setEditingId(null);
                        }}
                        onClick={e => e.stopPropagation()}
                      />
                    ) : (
                      <div
                        style={{ fontSize: 12, color: isActive ? T.blue : T.textHi, fontWeight: isActive ? 600 : 400 }}
                        onDoubleClick={e => {
                          e.stopPropagation();
                          setEditingId(record.id);
                          setEditLabel(record.label);
                        }}
                        title="Double-click to rename"
                      >
                        {record.label}
                        {isActive && (
                          <span className="tag tag-teal" style={{ marginLeft: 8, fontSize: 9 }}>active</span>
                        )}
                      </div>
                    )}
                    <div style={{ fontSize: 10, color: T.muted, marginTop: 1, fontFamily: T.mono }}>
                      {formatRelative(record.timestamp)} · {record.id.slice(0, 8)}
                      {sameConfig && (
                        <span style={{ color: T.amber, marginLeft: 8 }}>
                          ⚑ same config as {(configGroups.get(record.configHash) ?? []).length - 1} other run{(configGroups.get(record.configHash) ?? []).length > 2 ? "s" : ""}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Mode */}
                  {modeTag(record.mode)}

                  {/* Key stats */}
                  <div style={{ display: "flex", gap: 12, fontSize: 11, fontFamily: T.mono }}>
                    <span style={{ color: T.textDim }}>{record.summary.nPairs}p</span>
                    <span style={{ color: record.summary.nSignificant > 0 ? T.red : T.teal }}>
                      {record.summary.nSignificant} sig.
                    </span>
                    <span style={{ color: T.textDim }}>{record.summary.avgAbsA.toFixed(3)}</span>
                  </div>

                  {/* Config hash chip */}
                  <span style={{
                    fontFamily: T.mono, fontSize: 10, color: T.muted,
                    background: T.bg2, padding: "2px 6px", borderRadius: 4,
                    flexShrink: 0,
                  }}>
                    #{record.configHash}
                  </span>

                  {/* Actions */}
                  <div style={{ display: "flex", gap: 4, flexShrink: 0 }}
                    onClick={e => e.stopPropagation()}>
                    {!isActive && (
                      <button
                        className="btn btn-ghost"
                        style={{ fontSize: 10, padding: "3px 8px" }}
                        onClick={() => onRestore(record.pairs)}
                        title="Restore this run as the active analysis"
                      >
                        <Icon name="play" size={11} /> Restore
                      </button>
                    )}
                    <button
                      className="btn btn-ghost btn-icon"
                      style={{ padding: "3px 6px", color: T.red }}
                      onClick={() => onDelete(record.id)}
                      title="Delete this run"
                    >
                      <Icon name="close" size={11} />
                    </button>
                  </div>

                  <span style={{ color: T.muted, flexShrink: 0 }}>
                    <Icon name={isExpanded ? "chevD" : "chevron"} size={13} />
                  </span>
                </div>

                {isExpanded && (
                  <div style={{ padding: "0 16px 8px" }}>
                    <RunDrawer
                      record={record}
                      isActive={isActive}
                      onRestore={() => onRestore(record.pairs)}
                      onClose={() => setExpanded(null)}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* localStorage note */}
      <div style={{
        padding: "10px 16px", borderRadius: 8, fontSize: 11,
        background: T.bg2, border: `1px solid ${T.border}`,
        color: T.textDim, lineHeight: 1.6,
      }}>
        <b style={{ color: T.textHi }}>Storage note:</b> Run history is persisted in browser
        localStorage (<span style={{ fontFamily: T.mono }}>spindep_run_history_v1</span>).
        Last {" "}<span style={{ color: T.blue }}>20 runs</span> are kept. For long-term archiving,
        use <b>Export &amp; Report</b> to save the full HDF5 data archive.
        History is per-browser — not shared between researchers. For shared run history,
        the server needs a <span style={{ fontFamily: T.mono, color: T.blue }}>/api/runs</span>{" "}
        endpoint (planned).
      </div>
    </div>
  );
};