import React, { useState } from "react";
import { T, SIG } from "../../constants";
import { buildLatexTable, downloadTextFile } from "../../utils";
import { apiClient } from "../../api/client";
import { PanelHeader } from "../ui";
import { Icon } from "../ui/Icon";
import { useCopyToClipboard } from "../../hooks";
import type { AnalysisPair } from "../../types";

interface ExportSectionProps {
  pairs: AnalysisPair[];
}

type OutputKey =
  | "report" | "summary-csv" | "plots" | "constraint-atlas"
  | "gap-analysis" | "latex" | "hdf5" | "config";

interface OutputSpec {
  key: OutputKey;
  label: string;
  icon: string;
  desc: string;
  size: string;
  ext: string;
}

const OUTPUTS: OutputSpec[] = [
  { key: "report",           label: "PDF Report",           icon: "report",   desc: "Full analysis report with all plots and tables",        size: "~4 MB",  ext: "pdf"  },
  { key: "summary-csv",      label: "Summary CSV",          icon: "table",    desc: "All pair results: χ², p-values, |Aα|, lambda ranges",  size: "~18 KB", ext: "csv"  },
  { key: "plots",            label: "Asymmetry plots",      icon: "chart",    desc: "Per-pair coupling and asymmetry figures (PNG 300 DPI)", size: "~12 MB", ext: "zip"  },
  { key: "constraint-atlas", label: "Constraint atlas",     icon: "layers",   desc: "All atlas figures, one per coupling × potential",       size: "~8 MB",  ext: "zip"  },
  { key: "gap-analysis",     label: "Gap analysis figures", icon: "scope",    desc: "Coverage matrix, λ-space gap plot",                    size: "~1 MB",  ext: "zip"  },
  { key: "latex",            label: "LaTeX tables",         icon: "copy",     desc: "Publication-ready .tex tables for significant results", size: "~6 KB",  ext: "tex"  },
  { key: "hdf5",             label: "HDF5 data archive",    icon: "dl",       desc: "All interpolated g(λ) and A_α(λ) arrays",              size: "~22 MB", ext: "h5"   },
  { key: "config",           label: "YAML config used",     icon: "settings", desc: "Reproducibility: exact config that produced this run", size: "<1 KB",  ext: "yaml" },
];

export const ExportSection: React.FC<ExportSectionProps> = ({ pairs }) => {
  const sig             = pairs.filter(p => p.pval < SIG.STANDARD);
  const { copiedKey, copy } = useCopyToClipboard();
  const latexTable      = buildLatexTable(pairs);
  const hasResults      = pairs.length > 0;

  const [busyKey, setBusyKey] = useState<OutputKey | null>(null);
  const [errorKey, setErrorKey] = useState<OutputKey | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const handleDownload = async (key: OutputKey) => {
    if (busyKey) return;
    setBusyKey(key);
    setErrorKey(null);
    try {
      switch (key) {
        case "report":           await apiClient.downloadReport(); break;
        case "summary-csv":      await apiClient.downloadSummaryCsv(); break;
        case "plots":            await apiClient.downloadPlots(); break;
        case "constraint-atlas": await apiClient.downloadConstraintAtlas(); break;
        case "gap-analysis":     await apiClient.downloadGapAnalysis(); break;
        case "config":           await apiClient.downloadConfig(); break;
        case "hdf5":             await apiClient.downloadHdf5(pairs); break;
        case "latex":            downloadTextFile(latexTable, "cpt_asymmetry_table.tex"); break;
      }
    } catch (e) {
      setErrorKey(key);
      setErrorMsg(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ color: T.textHi, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
          Export &amp; Report
        </h2>
        <p style={{ color: T.textDim, fontSize: 13 }}>
          Results are written to{" "}
          <span style={{ fontFamily: T.mono, color: T.blue }}>
            ~/spindep_framework/results/
          </span>{" "}
          on the server after each run.
        </p>
      </div>

      <div className="split split-2" style={{ marginBottom: 20 }}>
        {OUTPUTS.map(o => {
          const isBusy = busyKey === o.key;
          const isErr  = errorKey === o.key;
          return (
            <div
              key={o.key}
              className="panel"
              style={{ display: "flex", alignItems: "center", padding: 0 }}
            >
              <div
                style={{
                  padding: "14px 14px 14px 16px",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  flex: 1,
                  minWidth: 0,
                }}
              >
                <span style={{ color: T.blue, flexShrink: 0 }}>
                  <Icon name={o.icon as any} size={18} />
                </span>
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{ fontWeight: 600, color: T.textHi, fontSize: 13, marginBottom: 2 }}
                  >
                    {o.label}
                  </div>
                  <div style={{ fontSize: 11, color: isErr ? T.red : T.textDim }}>
                    {isErr ? errorMsg : o.desc}
                  </div>
                </div>
              </div>
              <div
                style={{
                  padding: "0 14px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "flex-end",
                  gap: 6,
                  flexShrink: 0,
                }}
              >
                <span className="tag tag-muted" style={{ fontFamily: T.mono }}>
                  {o.size}
                </span>
                <button
                  className="btn btn-ghost"
                  style={{ fontSize: 11, padding: "4px 10px" }}
                  disabled={!hasResults || isBusy}
                  title={hasResults ? undefined : "Run the pipeline first"}
                  onClick={() => handleDownload(o.key)}
                >
                  {isBusy ? "..." : <><Icon name="dl" size={11} /> .{o.ext}</>}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {sig.length > 0 && (
        <div className="panel">
          <PanelHeader
            title="LaTeX Table (significant results)"
            icon="copy"
            right={
              <button
                className="btn btn-ghost"
                style={{ fontSize: 11 }}
                onClick={() => copy("latex", latexTable)}
              >
                {copiedKey === "latex" ? (
                  <><Icon name="check" size={12} /> Copied</>
                ) : (
                  <><Icon name="copy" size={12} /> Copy</>
                )}
              </button>
            }
          />
          <pre
            className="code-block"
            style={{
              margin: 0,
              borderRadius: "0 0 10px 10px",
              maxHeight: 220,
              overflowY: "auto",
              fontSize: 11,
            }}
          >
            {latexTable}
          </pre>
        </div>
      )}
    </div>
  );
};