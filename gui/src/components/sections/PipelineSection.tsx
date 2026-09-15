import React, { useRef, useEffect } from "react";
import { T, PIPELINE_STEPS } from "../../constants";
import { usePipelineJob } from "../../hooks";
import { logLineColor } from "../../utils";
import { PanelHeader, ProgressBar } from "../ui";
import { Icon } from "../ui/Icon";
import type { PipelineMode } from "../../types";

interface PipelineSectionProps {
  mode: PipelineMode;
  jobId: string | null;
  onComplete: () => Promise<void>;
}

export const PipelineSection: React.FC<PipelineSectionProps> = ({
  mode,
  jobId,
  onComplete,
}) => {
  const { log, progress, status, currentStep } = usePipelineJob(jobId, onComplete);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTimeout(() => logRef.current?.scrollTo(0, logRef.current.scrollHeight), 50);
  }, [log]);

  const steps   = PIPELINE_STEPS[mode] ?? PIPELINE_STEPS.full;
  const done    = status === "done";
  const isError = status === "error";
  // Real step index from the backend (matched against pipeline.py's own
  // print() phase headers as they execute) — not derived from the percentage.
  // Clamped because `mode` isn't currently threaded through to the backend
  // (every mode runs the full 7-phase pipeline), so a shorter step list
  // (e.g. "validate"'s 4 steps) could otherwise index out of range.
  const stepIdx = Math.min(currentStep, steps.length - 1);

  const modeLabel: Record<PipelineMode, string> = {
    full:     "Full Analysis",
    validate: "Validation",
    gaps:     "Gap Analysis",
    atlas:    "Constraint Atlas",
  };

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ color: T.textHi, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
          Pipeline: {modeLabel[mode]}
        </h2>
        {jobId && (
          <div style={{ fontSize: 10, color: T.muted, fontFamily: T.mono, marginBottom: 8 }}>
            job: {jobId}
          </div>
        )}
        <ProgressBar value={progress} height={4} />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 6,
            fontSize: 11,
            color: T.textDim,
          }}
        >
          <span>
            {done
              ? "Complete"
              : isError
              ? "Error — check log"
              : `Running: ${steps[stepIdx]}`}
          </span>
          <span style={{ fontFamily: T.mono }}>{progress.toFixed(0)}%</span>
        </div>
      </div>

      <div className="split split-2" style={{ alignItems: "start" }}>
        {/* Step list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {steps.map((step, i) => {
            const isDone    = done || i < stepIdx;
            const isRunning = !done && !isError && i === stepIdx;
            return (
              <div
                key={step}
                className={`pipe-step${isDone ? " done" : isRunning ? " running" : isError && i === stepIdx ? " error" : ""}`}
              >
                <span
                  style={{
                    color: isDone ? T.teal : isRunning ? T.blue : T.muted,
                    flexShrink: 0,
                  }}
                >
                  {isDone ? (
                    <Icon name="check" size={14} />
                  ) : isRunning ? (
                    <span className="spin-anim" style={{ display: "inline-block" }}>
                      <Icon name="atom" size={14} />
                    </span>
                  ) : (
                    <Icon name="scope" size={14} />
                  )}
                </span>
                <span
                  style={{
                    color: isDone ? T.text : isRunning ? T.textHi : T.muted,
                    fontSize: 12,
                  }}
                >
                  {step}
                </span>
                {isDone    && <span className="tag tag-teal"  style={{ marginLeft: "auto", fontSize: 9 }}>done</span>}
                {isRunning && <span className="tag tag-blue"  style={{ marginLeft: "auto", fontSize: 9 }}>running</span>}
              </div>
            );
          })}
        </div>

        {/* Live log */}
        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <PanelHeader
            title="Live Log Output"
            icon="report"
            sub="Streaming from Python pipeline"
          />
          <div
            ref={logRef}
            style={{
              padding: 12,
              fontFamily: T.mono,
              fontSize: 11,
              lineHeight: 1.9,
              maxHeight: 340,
              overflowY: "auto",
              background: T.bg0,
            }}
          >
            {log.length === 0 && (
              <div style={{ color: T.muted }}>Waiting for pipeline output…</div>
            )}
            {log.map((line, i) => (
              <div key={i} style={{ color: logLineColor(line) }}>
                {line}
              </div>
            ))}
            {!done && !isError && <div style={{ color: T.blue }}>▌</div>}
          </div>
        </div>
      </div>

      {/* Status banners */}
      {done && (
        <div
          style={{
            marginTop: 16,
            padding: "14px 16px",
            background: T.tealDim,
            border: `1px solid ${T.teal}40`,
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <Icon name="check" size={18} />
          <span style={{ color: T.teal, fontWeight: 600 }}>
            Pipeline complete — real results loaded in all tabs
          </span>
        </div>
      )}
      {isError && (
        <div
          style={{
            marginTop: 16,
            padding: "14px 16px",
            background: T.redDim,
            border: `1px solid ${T.red}40`,
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <Icon name="error" size={18} />
          <span style={{ color: T.red, fontWeight: 600 }}>
            Pipeline error — check the log above for details
          </span>
        </div>
      )}
    </div>
  );
};