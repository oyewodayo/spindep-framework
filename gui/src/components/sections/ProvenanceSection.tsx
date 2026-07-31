import React, { useMemo, useState, useEffect } from "react";
import { T } from "../../constants";
import { Icon } from "../ui/Icon";
import { Stat, PanelHeader, SearchBar } from "../ui";
import { apiClient } from "../../api/client";
import type { AnalysisPair, DatasetRecord, ConversionFlag } from "../../types";

interface ProvenanceSectionProps {
  pairs: AnalysisPair[];
}

// Derive dataset registry from pipeline results
// The pipeline returns pairs, not a dataset table. We reconstruct the registry
// from pair metadata so this section stays in sync with actual results.

function buildRegistry(pairs: AnalysisPair[]): DatasetRecord[] {
  const seen = new Map<string, DatasetRecord>();

  for (const p of pairs) {
    // Matter dataset
    if (!seen.has(p.matterDataset)) {
      const flag: ConversionFlag =
        p.matterUnit?.includes("pre-converted") ? "pre-converted"
        : p.matterUnit ? "none"
        : "unknown";

      seen.set(p.matterDataset, {
        name:             p.matterDataset,
        authors:          authorFromName(p.matterDataset),
        year:             yearFromName(p.matterDataset),
        journal:          journalHint(p.matterDataset),
        doi:              undefined,
        arxiv:            undefined,
        sector:           p.secM,
        interactionClass: p.interactionClass,
        originalUnit:     p.matterUnit ?? "unknown",
        storedUnit:       "m",
        conversionFlag:   flag,
        conversionNote:   flag === "pre-converted"
          ? `Published in non-SI units; converted to metres before storage in datasets/normalized/.`
          : undefined,
        lambdaMin:        p.lambdaMin,
        lambdaMax:        p.lambdaMax,
        nPoints:          p.points?.length ?? 0,
        couplings:        [p.coupling],
        appearsInPairs:   [p.id],
        isMatter:         true,
      });
    } else {
      const r = seen.get(p.matterDataset)!;
      if (!r.couplings.includes(p.coupling))  r.couplings.push(p.coupling);
      if (!r.appearsInPairs.includes(p.id))   r.appearsInPairs.push(p.id);
      r.lambdaMin = Math.min(r.lambdaMin, p.lambdaMin);
      r.lambdaMax = Math.max(r.lambdaMax, p.lambdaMax);
    }

    // Antimatter dataset
    if (!seen.has(p.antimatterDataset)) {
      const flag: ConversionFlag =
        p.antimatterUnit?.includes("pre-converted") ? "pre-converted"
        : p.antimatterUnit ? "none"
        : "unknown";

      seen.set(p.antimatterDataset, {
        name:             p.antimatterDataset,
        authors:          authorFromName(p.antimatterDataset),
        year:             yearFromName(p.antimatterDataset),
        journal:          journalHint(p.antimatterDataset),
        doi:              undefined,
        arxiv:            undefined,
        sector:           p.secA,
        interactionClass: p.interactionClass,
        originalUnit:     p.antimatterUnit ?? "unknown",
        storedUnit:       "m",
        conversionFlag:   flag,
        conversionNote:   flag === "pre-converted"
          ? `Published in non-SI units; converted to metres before storage in datasets/normalized/.`
          : undefined,
        lambdaMin:        p.lambdaMin,
        lambdaMax:        p.lambdaMax,
        nPoints:          p.points?.length ?? 0,
        couplings:        [p.coupling],
        appearsInPairs:   [p.id],
        isMatter:         false,
      });
    } else {
      const r = seen.get(p.antimatterDataset)!;
      if (!r.couplings.includes(p.coupling))  r.couplings.push(p.coupling);
      if (!r.appearsInPairs.includes(p.id))   r.appearsInPairs.push(p.id);
      r.lambdaMin = Math.min(r.lambdaMin, p.lambdaMin);
      r.lambdaMax = Math.max(r.lambdaMax, p.lambdaMax);
    }
  }

  return [...seen.values()].sort((a, b) => a.year - b.year || a.name.localeCompare(b.name));
}

// Heuristics to extract author/year/journal from dataset name
// These are best-effort; users should add a provenance JSON file on the server
// to override with real citations.

function yearFromName(name: string): number {
  const m = name.match(/(\d{4})/);
  return m ? parseInt(m[1]) : 0;
}

function authorFromName(name: string): string {
  const m = name.match(/^([A-Za-z]+)(\d{4})/);
  return m ? m[1] + " et al." : name;
}

function journalHint(name: string): string {
  // Known dataset → journal mappings from the report
  const MAP: Record<string, string> = {
    Delaunay2017:      "Phys. Rev. D 96, 093001 (2017)",
    Adkins2022:        "Phys. Rev. A 106, 042808 (2022)",
    Karshenboim2011:   "Phys. Rev. D 82, 073003 (2010)",
    Fadeev2022:        "Phys. Rev. A 105, 023311 (2022)",
    Kotler2015:        "Nature 510, 376 (2014)",
    Ficek2017:         "Phys. Rev. A 95, 032505 (2017)",
    Rong2018:          "Phys. Rev. Lett. 120, 260402 (2018)",
    Jiao2019:          "Phys. Rev. Lett. 123, 031601 (2019)",
  };
  return MAP[name] ?? "—";
}

// Conversion flag badge

function ConvFlag({ flag, unit }: { flag: ConversionFlag; unit: string }) {
  const cfg = {
    none:          { color: T.teal,  bg: T.tealDim,   label: "native SI" },
    "pre-converted":{ color: T.amber, bg: T.amberDim,  label: "pre-converted" },
    unknown:       { color: T.muted, bg: T.dim,        label: "unknown" },
  }[flag];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <span
        style={{
          display: "inline-flex", alignItems: "center", gap: 3,
          padding: "2px 7px", borderRadius: 4,
          fontSize: 10, fontWeight: 700, fontFamily: T.mono,
          background: cfg.bg, color: cfg.color, width: "fit-content",
        }}
      >
        {cfg.label}
      </span>
      <span style={{ fontSize: 10, color: T.textDim, fontFamily: T.mono }}>{unit}</span>
    </div>
  );
}

// λ range mini-bar

function LambdaBar({ min, max, globalMin, globalMax }: {
  min: number; max: number; globalMin: number; globalMax: number;
}) {
  const logMin    = Math.log10(min);
  const logMax    = Math.log10(max);
  const logGMin   = Math.log10(globalMin);
  const logGMax   = Math.log10(globalMax);
  const span      = logGMax - logGMin || 1;
  const left      = ((logMin - logGMin) / span) * 100;
  const width     = ((logMax - logMin) / span) * 100;
  return (
    <div style={{ position: "relative", height: 8, background: T.border, borderRadius: 4, minWidth: 100 }}>
      <div
        style={{
          position: "absolute", left: `${left}%`, width: `${width}%`,
          height: "100%", background: T.blue, borderRadius: 4, minWidth: 3,
        }}
        title={`${min.toExponential(2)} – ${max.toExponential(2)} m`}
      />
    </div>
  );
}

// Participation map

function ParticipationMap({ record, pairs }: { record: DatasetRecord; pairs: AnalysisPair[] }) {
  const relevant = pairs.filter(p =>
    p.matterDataset === record.name || p.antimatterDataset === record.name
  );
  return (
    <div>
      <div style={{ fontSize: 10, color: T.textDim, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 6, fontWeight: 600 }}>
        Appears in {relevant.length} pair{relevant.length !== 1 ? "s" : ""}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
        {relevant.map(p => (
          <div
            key={p.id}
            style={{
              padding: "3px 8px", borderRadius: 4, fontSize: 10, fontFamily: T.mono,
              background: p.matterDataset === record.name ? T.blueDim : T.violetDim,
              color: p.matterDataset === record.name ? T.blue : T.violet,
              border: `1px solid ${p.matterDataset === record.name ? T.blue : T.violet}30`,
            }}
            title={`${p.coupling} · ${p.potential} · ${p.secM}×${p.secA}`}
          >
            {p.id.length > 30 ? p.id.slice(0, 28) + "…" : p.id}
            <span style={{ marginLeft: 4, opacity: 0.6, fontSize: 9 }}>
              {p.matterDataset === record.name ? "(matter)" : "(antimatter)"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Detail drawer

function DatasetDrawer({ record, pairs, onClose }: {
  record: DatasetRecord;
  pairs: AnalysisPair[];
  onClose: () => void;
}) {
  const globalMin = Math.min(...pairs.map(p => p.lambdaMin));
  const globalMax = Math.max(...pairs.map(p => p.lambdaMax));

  return (
    <div className="panel fade-in" style={{ marginTop: 12 }}>
      <PanelHeader
        title={record.name}
        icon="report"
        sub={record.journal}
        right={
          <button className="btn btn-ghost btn-icon" onClick={onClose}>
            <Icon name="close" size={14} />
          </button>
        }
      />
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16 }}>

        {/* Citation block */}
        <div style={{ padding: "12px 16px", background: T.bg2, borderRadius: 8, border: `1px solid ${T.border}` }}>
          <div style={{ fontSize: 10, color: T.textDim, textTransform: "uppercase", letterSpacing: ".09em", fontWeight: 600, marginBottom: 8 }}>
            Citation
          </div>
          <div style={{ fontSize: 13, color: T.textHi, fontWeight: 500, marginBottom: 4 }}>
            {record.authors} ({record.year})
          </div>
          <div style={{ fontSize: 12, color: T.text, marginBottom: 8 }}>{record.journal}</div>
          <div style={{ display: "flex", gap: 8 }}>
            {record.doi ? (
              <a href={`https://doi.org/${record.doi}`} target="_blank" rel="noreferrer"
                style={{ color: T.blue, fontSize: 11, fontFamily: T.mono, textDecoration: "none" }}>
                DOI: {record.doi}
              </a>
            ) : (
              <span style={{ color: T.muted, fontSize: 11 }}>
                DOI not yet in registry — add via <span style={{ fontFamily: T.mono }}>datasets/provenance.json</span>
              </span>
            )}
            {record.arxiv && (
              <a href={`https://arxiv.org/abs/${record.arxiv}`} target="_blank" rel="noreferrer"
                style={{ color: T.violet, fontSize: 11, fontFamily: T.mono, textDecoration: "none" }}>
                arXiv: {record.arxiv}
              </a>
            )}
          </div>
        </div>

        {/* Metadata grid */}
        <div className="split split-4" style={{ gap: 10 }}>
          {[
            ["Sector",           record.sector],
            ["Interaction",      record.interactionClass],
            ["Role",             record.isMatter ? "Matter" : "Antimatter"],
            ["Data points",      record.nPoints.toString()],
            ["Original unit",    record.originalUnit],
            ["Stored unit",      record.storedUnit],
            ["λ min",            record.lambdaMin.toExponential(2) + " m"],
            ["λ max",            record.lambdaMax.toExponential(2) + " m"],
          ].map(([k, v]) => (
            <div key={k} style={{ background: T.bg2, borderRadius: 6, padding: "8px 10px", border: `1px solid ${T.border}` }}>
              <div style={{ fontSize: 9, color: T.textDim, textTransform: "uppercase", letterSpacing: ".09em", marginBottom: 3 }}>{k}</div>
              <div style={{ fontFamily: T.mono, color: T.textHi, fontSize: 11 }}>{v}</div>
            </div>
          ))}
        </div>

        {/* Conversion note */}
        {record.conversionFlag !== "none" && (
          <div style={{
            padding: "10px 14px",
            background: record.conversionFlag === "pre-converted" ? T.amberDim : T.dim,
            borderRadius: 8,
            border: `1px solid ${record.conversionFlag === "pre-converted" ? T.amber : T.muted}30`,
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: record.conversionFlag === "pre-converted" ? T.amber : T.muted, marginBottom: 4 }}>
              {record.conversionFlag === "pre-converted" ? "⚠ Unit Conversion Applied" : "⚠ Unit Unknown"}
            </div>
            <div style={{ fontSize: 12, color: T.text, lineHeight: 1.6 }}>
              {record.conversionNote ?? "No conversion note available."}
            </div>
          </div>
        )}

        {/* λ coverage bar */}
        <div>
          <div style={{ fontSize: 10, color: T.textDim, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 8, fontWeight: 600 }}>
            λ Coverage (relative to full dataset span)
          </div>
          <LambdaBar min={record.lambdaMin} max={record.lambdaMax} globalMin={globalMin} globalMax={globalMax} />
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 10, color: T.muted, fontFamily: T.mono }}>
            <span>{globalMin.toExponential(1)} m</span>
            <span>{globalMax.toExponential(1)} m</span>
          </div>
        </div>

        {/* Participation map */}
        <ParticipationMap record={record} pairs={pairs} />
      </div>
    </div>
  );
}

// Main section

export const ProvenanceSection: React.FC<ProvenanceSectionProps> = ({ pairs }) => {
  const baseRegistry = useMemo(() => buildRegistry(pairs), [pairs]);

  // Fetch optional server-side enrichment (DOIs, arXiv IDs, full citations).
  // Merges on top of the derived registry — never blocks rendering.
  const [enrichment, setEnrichment] = useState<Map<string, Partial<DatasetRecord>>>(new Map());
  const [enrichmentStatus, setEnrichmentStatus] = useState<"idle" | "loading" | "ok" | "unavailable">("idle");

  useEffect(() => {
    if (pairs.length === 0) return;
    setEnrichmentStatus("loading");
    apiClient.getProvenance().then(map => {
      setEnrichment(map);
      setEnrichmentStatus(map.size > 0 ? "ok" : "unavailable");
    });
  }, [pairs.length]);

  // Merge server enrichment on top of derived records
  const registry = useMemo<DatasetRecord[]>(() =>
    baseRegistry.map(r => {
      const extra = enrichment.get(r.name);
      if (!extra) return r;
      return {
        ...r,
        authors:        extra.authors        ?? r.authors,
        year:           extra.year           ?? r.year,
        journal:        extra.journal        ?? r.journal,
        doi:            extra.doi            ?? r.doi,
        arxiv:          extra.arxiv          ?? r.arxiv,
        conversionNote: extra.conversionNote ?? r.conversionNote,
      };
    }),
    [baseRegistry, enrichment]
  );

  const [query, setQuery]       = useState("");
  const [selected, setSelected] = useState<DatasetRecord | null>(null);
  const [filterRole, setFilterRole] = useState<"All" | "Matter" | "Antimatter">("All");

  const globalMin = pairs.length ? Math.min(...pairs.map(p => p.lambdaMin)) : 1e-15;
  const globalMax = pairs.length ? Math.max(...pairs.map(p => p.lambdaMax)) : 1e-3;

  const filtered = useMemo(() =>
    registry.filter(r =>
      (filterRole === "All" || (filterRole === "Matter") === r.isMatter) &&
      (!query || r.name.toLowerCase().includes(query.toLowerCase()) ||
                 r.authors.toLowerCase().includes(query.toLowerCase()) ||
                 r.journal.toLowerCase().includes(query.toLowerCase()) ||
                 r.sector.toLowerCase().includes(query.toLowerCase()))
    ), [registry, query, filterRole]);

  const conversionCount = registry.filter(r => r.conversionFlag === "pre-converted").length;

  if (pairs.length === 0) {
    return (
      <div className="fade-in" style={{ textAlign: "center", padding: 60, color: T.muted }}>
        <Icon name="report" size={40} />
        <div style={{ marginTop: 16, fontSize: 14, fontWeight: 600, color: T.textDim }}>
          Run the pipeline first to build the dataset registry
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ color: T.textHi, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
          Dataset Provenance
        </h2>
        <p style={{ color: T.textDim, fontSize: 13 }}>
          Full audit trail for every dataset in the analysis — citations, units, conversions,
          and participation map. Click any row to expand.
        </p>
      </div>

      <div className="split split-4" style={{ marginBottom: 18 }}>
        <Stat label="Unique datasets"   value={registry.length} />
        <Stat label="Matter datasets"   value={registry.filter(r => r.isMatter).length}    color={T.blue} />
        <Stat label="Antimatter"        value={registry.filter(r => !r.isMatter).length}   color={T.amber} />
        <Stat label="Unit conversions"  value={conversionCount}
          color={conversionCount > 0 ? T.amber : T.teal}
          sub={conversionCount > 0 ? "review required" : "all native SI"} />
      </div>

      {/* Conversion audit banner */}
      {conversionCount > 0 && (
        <div style={{
          padding: "10px 16px", borderRadius: 8, marginBottom: 16,
          background: T.amberDim, border: `1px solid ${T.amber}40`,
          display: "flex", alignItems: "center", gap: 10, fontSize: 12, color: T.amber,
        }}>
          <Icon name="warn" size={14} />
          <span>
            <b>{conversionCount} dataset{conversionCount > 1 ? "s have" : " has"} a unit pre-conversion flag.</b>{" "}
            These were not in SI metres as published. Verify conversion factors in the thesis appendix.
          </span>
        </div>
      )}

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, marginBottom: 14, alignItems: "center", flexWrap: "wrap" }}>
        <SearchBar value={query} onChange={setQuery} placeholder="Search by name, author, journal, sector…" />
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {(["All", "Matter", "Antimatter"] as const).map(r => (
            <button
              key={r}
              className={`btn ${filterRole === r ? "btn-primary" : "btn-ghost"}`}
              style={{ fontSize: 11 }}
              onClick={() => setFilterRole(r)}
            >
              {r}
            </button>
          ))}
        </div>
        <span style={{ marginLeft: "auto", fontSize: 11, color: T.textDim }}>
          {filtered.length} of {registry.length} datasets
        </span>
      </div>

      {/* Registry table */}
      <div className="panel" style={{ marginBottom: selected ? 0 : 0 }}>
        <div style={{ overflowX: "auto" }}>
          <table className="data-table">
            <thead style={{ position: "sticky", top: 0, background: T.panel }}>
              <tr>
                <th>Dataset</th>
                <th>Authors</th>
                <th>Journal / Reference</th>
                <th>Role</th>
                <th>Sector</th>
                <th>Couplings</th>
                <th>Unit / Conversion</th>
                <th>λ range (m)</th>
                <th>λ coverage</th>
                <th>In pairs</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <React.Fragment key={r.name}>
                  <tr
                    onClick={() => setSelected(selected?.name === r.name ? null : r)}
                    style={{
                      cursor: "pointer",
                      background: selected?.name === r.name ? T.bg2 : "transparent",
                    }}
                  >
                    <td style={{ fontWeight: 600, color: T.textHi, fontFamily: T.mono, fontSize: 12 }}>
                      {r.name}
                    </td>
                    <td style={{ color: T.textDim, fontSize: 11 }}>{r.authors}</td>
                    <td style={{ color: T.textDim, fontSize: 11, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {r.journal}
                    </td>
                    <td>
                      <span className={`tag ${r.isMatter ? "tag-blue" : "tag-amber"}`}>
                        {r.isMatter ? "matter" : "antimatter"}
                      </span>
                    </td>
                    <td style={{ fontFamily: T.mono, fontSize: 11 }}>{r.sector}</td>
                    <td>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        {r.couplings.map(c => (
                          <span key={c} className="tag tag-blue" style={{ fontSize: 9 }}>{c}</span>
                        ))}
                      </div>
                    </td>
                    <td><ConvFlag flag={r.conversionFlag} unit={r.originalUnit} /></td>
                    <td style={{ color: T.textDim, fontSize: 10, fontFamily: T.mono, whiteSpace: "nowrap" }}>
                      {r.lambdaMin.toExponential(1)} – {r.lambdaMax.toExponential(1)}
                    </td>
                    <td style={{ minWidth: 100 }}>
                      <LambdaBar min={r.lambdaMin} max={r.lambdaMax} globalMin={globalMin} globalMax={globalMax} />
                    </td>
                    <td style={{ color: T.textDim, fontSize: 11 }}>{r.appearsInPairs.length}</td>
                    <td>
                      <button className="btn btn-ghost btn-icon" style={{ padding: "3px 6px" }}>
                        <Icon name={selected?.name === r.name ? "chevD" : "chevron"} size={11} />
                      </button>
                    </td>
                  </tr>
                  {selected?.name === r.name && (
                    <tr>
                      <td colSpan={11} style={{ padding: 0 }}>
                        <DatasetDrawer
                          record={r}
                          pairs={pairs}
                          onClose={() => setSelected(null)}
                        />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provenance enrichment status */}
      <div style={{
        marginTop: 16, padding: "12px 16px", borderRadius: 8,
        background: enrichmentStatus === "ok" ? T.tealDim : T.bg2,
        border: `1px solid ${enrichmentStatus === "ok" ? T.teal + "50" : T.border}`,
        fontSize: 12, color: T.textDim, lineHeight: 1.7,
        display: "flex", alignItems: "flex-start", gap: 10,
      }}>
        <span style={{ color: enrichmentStatus === "ok" ? T.teal : T.muted, marginTop: 1, flexShrink: 0 }}>
          <Icon name={enrichmentStatus === "ok" ? "check" : enrichmentStatus === "loading" ? "atom" : "info"} size={14} />
        </span>
        <div>
          {enrichmentStatus === "ok" && (
            <><b style={{ color: T.teal }}>Provenance enriched</b> — DOIs and full citations loaded from{" "}
            <span style={{ fontFamily: T.mono, color: T.blue }}>/api/provenance</span>. {enrichment.size} dataset records merged.</>
          )}
          {enrichmentStatus === "unavailable" && (
            <><b style={{ color: T.textHi }}>Enrich provenance data:</b> Add a{" "}
            <span style={{ fontFamily: T.mono, color: T.blue }}>datasets/provenance.json</span>{" "}
            file on the server with DOIs, arXiv IDs, and full citations. The API will expose it at{" "}
            <span style={{ fontFamily: T.mono, color: T.blue }}>/api/provenance</span>{" "}
            and this registry will automatically display full citation links with no frontend changes.</>
          )}
          {enrichmentStatus === "loading" && (
            <span style={{ color: T.muted }}>Loading provenance enrichment…</span>
          )}
          {enrichmentStatus === "idle" && (
            <span style={{ color: T.muted }}>Provenance enrichment will load after pipeline run.</span>
          )}
        </div>
      </div>
    </div>
  );
};