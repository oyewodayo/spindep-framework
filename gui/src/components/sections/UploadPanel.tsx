// UploadPanel.tsx — drop into the right column of the Ingest page
import { useState, useCallback, useRef } from "react";
import { apiClient } from "../../api/client";
import type { UploadSuggestion } from "../../api/client";
import { T } from "../../constants";

type UploadState = "idle" | "dragging" | "uploading" | "done" | "error";

interface UploadPanelProps {
  onSuccess: () => void;
  prominent?: boolean;
}

export function UploadPanel({ onSuccess, prominent = false }: UploadPanelProps) {
  const [state, setState]         = useState<UploadState>("idle");
  const [saved, setSaved]         = useState<string[]>([]);
  const [warnings, setWarnings]   = useState<string[]>([]);
  const [error, setError]         = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<UploadSuggestion[]>([]);
  const [organizing, setOrganizing]   = useState<string | null>(null);
  const [organized, setOrganized]     = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(async (files: File[]) => {
    if (!files.length) return;
    const csvs = files.filter(f => f.name.endsWith(".csv"));
    if (!csvs.length) {
      setError("Only .csv files are accepted.");
      setState("error");
      return;
    }
    setState("uploading");
    try {
      const result = await apiClient.uploadDatasets(csvs);
      setSaved(result.saved);
      setWarnings(result.warnings);
      setSuggestions(result.suggestions ?? []);
      setState("done");
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setState("error");
    }
  }, [onSuccess]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setState("idle");
    handleFiles(Array.from(e.dataTransfer.files));
  }, [handleFiles]);

  const handleOrganize = async (s: UploadSuggestion) => {
    setOrganizing(s.filename);
    try {
      await apiClient.organizeDataset(s.filename, s.coupling, s.interaction_class);
      setOrganized(prev => [...prev, s.filename]);
      onSuccess();
    } catch (e) {
      setWarnings(prev => [...prev, `Failed to move ${s.filename}: ${e}`]);
    } finally {
      setOrganizing(null);
    }
  };

  const reset = () => {
    setState("idle");
    setSaved([]);
    setWarnings([]);
    setSuggestions([]);
    setOrganized([]);
    setError(null);
  };

  return (
    <div
      className={`upload-panel ${state === "dragging" ? "dragging" : ""}`}
      style={{
        border: prominent
          ? `1.5px solid ${T.amber}`
          : `1px solid ${T.border ?? "#333"}`,
        borderRadius: 8,
        padding: 16,
        textAlign: "center",
        transition: "border-color 0.2s",
      }}
      onDragOver={e => { e.preventDefault(); setState("dragging"); }}
      onDragLeave={() => setState(s => s === "dragging" ? "idle" : s)}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        multiple
        style={{ display: "none" }}
        onChange={e => handleFiles(Array.from(e.target.files ?? []))}
      />

      {/* Idle / dragging */}
      {(state === "idle" || state === "dragging") && (
        <>
          <div style={{ fontSize: 24, marginBottom: 8, color: T.muted }}>⬆</div>
          <p style={{ color: T.textHi, fontWeight: 600, marginBottom: 4 }}>
            Drop normalized CSVs here
          </p>
          <p style={{ color: T.textDim, fontSize: 11, marginBottom: 10 }}>
            Expected columns: <code>lambda_m</code>, <code>coupling_abs</code>
          </p>
          <p style={{ color: T.textDim, fontSize: 11, marginBottom: 10 }}>
            Filename convention:{" "}
            <code style={{ fontFamily: T.mono }}>
              V2_Author2024_sector_coupling.csv
            </code>
            <br />
            Folder structure will be inferred automatically.
          </p>
          <button className="btn btn-ghost" onClick={() => inputRef.current?.click()}>
            Browse files
          </button>
        </>
      )}

      {/* Uploading */}
      {state === "uploading" && (
        <p style={{ color: T.textDim }}>Uploading…</p>
      )}

      {/* Done */}
      {state === "done" && (
        <>
          <div style={{ color: T.teal, fontSize: 20, marginBottom: 6 }}>✓</div>
          <p style={{ color: T.textHi, fontWeight: 600, marginBottom: 8 }}>
            {saved.length} file{saved.length !== 1 ? "s" : ""} saved
          </p>

          {/* Warnings */}
          {warnings.map((w, i) => (
            <p key={i} style={{ color: T.amber, fontSize: 11, marginBottom: 4 }}>
              ⚠ {w}
            </p>
          ))}

          {/* Suggestion cards */}
          {suggestions
            .filter(s => !organized.includes(s.filename))
            .map(s => (
              <div
                key={s.filename}
                style={{
                  marginTop: 10,
                  padding: "10px 14px",
                  background: T.bg1 ?? "#1a1a2e",
                  border: `1px solid ${T.amber}`,
                  borderRadius: 6,
                  fontSize: 12,
                  textAlign: "left",
                }}
              >
                <div style={{ color: T.amber, marginBottom: 4, fontWeight: 600 }}>
                  ⚡ Folder structure inferred from filename
                </div>
                <div style={{
                  color: T.textDim,
                  fontFamily: T.mono,
                  fontSize: 11,
                  marginBottom: 8,
                }}>
                  {s.filename}<br />
                  <span style={{ color: T.muted }}>
                    → normalized/{s.coupling}/{s.interaction_class}/
                  </span>
                </div>
                <div style={{ color: T.textDim, fontSize: 11, marginBottom: 8 }}>
                  Coupling:{" "}
                  <b style={{ color: T.textHi }}>{s.coupling}</b>
                  {" · "}Class:{" "}
                  <b style={{ color: T.textHi }}>{s.interaction_class}</b>
                  {" · "}Sector:{" "}
                  <b style={{ color: T.textHi }}>{s.sector}</b>
                </div>
                <button
                  className="btn btn-ghost"
                  style={{ fontSize: 11 }}
                  disabled={organizing === s.filename}
                  onClick={() => handleOrganize(s)}
                >
                  {organizing === s.filename
                    ? "Moving…"
                    : `Move into normalized/${s.coupling}/${s.interaction_class}/`}
                </button>
              </div>
            ))}

          {/* Confirmed moves */}
          {organized.map(name => (
            <div key={name} style={{ color: T.teal, fontSize: 11, marginTop: 6 }}>
              ✓ {name} moved to correct folder
            </div>
          ))}

          <div style={{ marginTop: 12 }}>
            <button className="btn btn-ghost" onClick={reset}>
              Upload more
            </button>
          </div>
        </>
      )}

      {/* Error */}
      {state === "error" && (
        <>
          <p style={{ color: T.red ?? "#e05", marginBottom: 8 }}>✗ {error}</p>
          <button className="btn btn-ghost" onClick={reset}>
            Try again
          </button>
        </>
      )}
    </div>
  );
}