import React, { useState, useMemo, useRef, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, ScatterChart, Scatter,
  Cell, AreaChart, Area, ErrorBar, Legend,
} from "recharts";
import { T, SIG } from "../../constants";
import { Icon } from "../ui/Icon";
import { Stat, PanelHeader, ProgressBar } from "../ui";
import { useNullTest, useNullTestBattery } from "../../hooks";
import { pvalColor, formatPval, reducedChi2 } from "../../utils";
import type {
  AnalysisPair,
  NullTestConfig,
  NullTestResult,
  NullTestBattery,
} from "../../types";

interface NullTestSectionProps {
  pairs: AnalysisPair[];
}

// Constants

const BATTERY_LEVELS_DEFAULT = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0];

const INJECTION_MODE_DESCRIPTIONS: Record<NullTestConfig["injectionMode"], string> = {
  scale:   "Multiply the antimatter curve by (1 − Aα·f(λ)), shrinking it toward the matter curve. Most physically motivated.",
  replace: "Replace the antimatter curve with a synthetic one at the injected Aα level. Maximum control.",
  shift:   "Add a constant log-space offset to the antimatter curve. Tests additive systematic offsets.",
};

// Helpers

function calibrationColor(ok: boolean): string {
  return ok ? T.teal : T.red;
}

function recoveryColor(frac: number): string {
  if (frac > 0.95 && frac < 1.05) return T.teal;
  if (frac > 0.85 && frac < 1.15) return T.amber;
  return T.red;
}

function sigmaFromPval(pval: number): number {
  // Approximate: p = erfc(z/√2) → z ≈ √(2)·erfinv(1−p)
  // Use a lookup for common values; for display purposes this is sufficient.
  if (pval <= 0)    return 10;
  if (pval >= 0.5)  return 0;
  // Rational approximation to probit
  const p = 1 - pval;
  const a = [2.515517, 0.802853, 0.010328];
  const b = [1.432788, 0.189269, 0.001308];
  const t = Math.sqrt(-2 * Math.log(1 - p));
  const num = a[0] + a[1] * t + a[2] * t * t;
  const den = 1 + b[0] * t + b[1] * t * t + b[2] * t * t * t;
  return Math.max(0, t - num / den);
}

// Config Panel

interface ConfigPanelProps {
  pairs:       AnalysisPair[];
  onRun:       (cfg: NullTestConfig) => void;
  onBattery:   (pairId: string, levels: number[], mode: NullTestConfig["injectionMode"]) => void;
  isRunning:   boolean;
}

const ConfigPanel: React.FC<ConfigPanelProps> = ({ pairs, onRun, onBattery, isRunning }) => {
  const [pairId,    setPairId]    = useState(pairs[0]?.id ?? "");
  const [injected,  setInjected]  = useState(0.0);
  const [mode,      setMode]      = useState<NullTestConfig["injectionMode"]>("scale");
  const [seed,      setSeed]      = useState(42);
  const [battMode,  setBattMode]  = useState(false);
  const [customLevels, setCustomLevels] = useState(BATTERY_LEVELS_DEFAULT.join(", "));

  const selectedPair = pairs.find(p => p.id === pairId);

  const handleSingle = () => {
    const cfg: NullTestConfig = {
      id:             `${pairId}-${injected}-${Date.now()}`,
      label:          `|Aα|=${injected.toFixed(2)} · ${pairId.slice(0, 20)}`,
      targetPairId:   pairId,
      injectedAalpha: injected,
      injectionMode:  mode,
      seed,
    };
    onRun(cfg);
  };

  const handleBattery = () => {
    const levels = customLevels
      .split(",")
      .map(s => parseFloat(s.trim()))
      .filter(n => !isNaN(n) && n >= 0 && n <= 1);
    onBattery(pairId, levels, mode);
  };

  return (
    <div className="panel">
      <PanelHeader
        title="Injection Configuration"
        icon="settings"
        sub="Configure a synthetic CPT asymmetry to inject, then run to verify recovery"
      />
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>

        {/* Pair selector */}
        <div>
          <label className="label">Target pair</label>
          <select className="select" style={{ width: "100%" }}
            value={pairId} onChange={e => setPairId(e.target.value)}>
            {pairs.map(p => (
              <option key={p.id} value={p.id}>
                {p.id} · |Aα|={p.meanAbsA.toFixed(4)} · {p.coupling}·{p.potential}
              </option>
            ))}
          </select>
          {selectedPair && (
            <div style={{ marginTop: 6, fontSize: 10, color: T.textDim, fontFamily: T.mono }}>
              Real |Aα| = {selectedPair.meanAbsA.toFixed(4)} ·
              λ: {selectedPair.lambdaMin.toExponential(1)} – {selectedPair.lambdaMax.toExponential(1)} m ·
              dof = {selectedPair.dof}
            </div>
          )}
        </div>

        {/* Injection mode */}
        <div>
          <label className="label">Injection mode</label>
          <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
            {(["scale", "replace", "shift"] as const).map(m => (
              <button key={m}
                className={`btn ${mode === m ? "btn-primary" : "btn-ghost"}`}
                style={{ fontSize: 11, fontFamily: T.mono }}
                onClick={() => setMode(m)}
              >
                {m}
              </button>
            ))}
          </div>
          <div style={{ fontSize: 11, color: T.textDim, lineHeight: 1.6,
            padding: "8px 10px", background: T.bg2, borderRadius: 6 }}>
            {INJECTION_MODE_DESCRIPTIONS[mode]}
          </div>
        </div>

        {/* Single vs battery */}
        <div style={{ display: "flex", gap: 6 }}>
          <button className={`btn ${!battMode ? "btn-primary" : "btn-ghost"}`}
            style={{ fontSize: 11 }} onClick={() => setBattMode(false)}>
            Single test
          </button>
          <button className={`btn ${battMode ? "btn-primary" : "btn-ghost"}`}
            style={{ fontSize: 11 }} onClick={() => setBattMode(true)}>
            Battery (multiple levels)
          </button>
        </div>

        {!battMode ? (
          /* Single test controls */
          <div>
            <label className="label">Injected |Aα| = {injected.toFixed(2)}</label>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <input type="range" min={0} max={1} step={0.05}
                value={injected}
                onChange={e => setInjected(parseFloat(e.target.value))}
                style={{ flex: 1, accentColor: T.blue }}
              />
              <input type="number" min={0} max={1} step={0.05}
                value={injected}
                onChange={e => setInjected(Math.min(1, Math.max(0, parseFloat(e.target.value))))}
                className="input"
                style={{ width: 70, fontSize: 12 }}
              />
            </div>
            {/* Aα preset chips */}
            <div style={{ display: "flex", gap: 5, marginTop: 8, flexWrap: "wrap" }}>
              {[0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0].map(v => (
                <button key={v}
                  className={`btn btn-ghost`}
                  style={{ fontSize: 10, padding: "2px 8px",
                    background: injected === v ? T.blueDim : "transparent",
                    color: injected === v ? T.blue : T.textDim,
                    borderColor: injected === v ? T.blue : T.border,
                  }}
                  onClick={() => setInjected(v)}
                >
                  {v.toFixed(2)}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Battery controls */
          <div>
            <label className="label">Injection levels (comma-separated, 0–1)</label>
            <input className="input" style={{ width: "100%", fontSize: 12 }}
              value={customLevels}
              onChange={e => setCustomLevels(e.target.value)}
            />
            <div style={{ fontSize: 10, color: T.textDim, marginTop: 4 }}>
              {customLevels.split(",").filter(s => !isNaN(parseFloat(s.trim()))).length} levels configured
            </div>
          </div>
        )}

        {/* Seed */}
        <div>
          <label className="label">RNG seed (reproducibility)</label>
          <input type="number" className="input" style={{ width: 120, fontSize: 12 }}
            value={seed} onChange={e => setSeed(parseInt(e.target.value) || 42)} />
          <span style={{ fontSize: 10, color: T.textDim, marginLeft: 8 }}>
            Same seed = identical injection pattern
          </span>
        </div>

        {/* Run button */}
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn btn-primary"
            style={{ padding: "9px 20px" }}
            disabled={isRunning || !pairId}
            onClick={battMode ? handleBattery : handleSingle}
          >
            <Icon name="play" size={13} />
            {battMode ? "Run battery" : "Run null test"}
          </button>
          {isRunning && (
            <span style={{ color: T.blue, fontSize: 12, alignSelf: "center", display: "flex", gap: 5 }}>
              <span className="spin-anim" style={{ display: "inline-block" }}>
                <Icon name="atom" size={13} />
              </span>
              Running…
            </span>
          )}
        </div>

        {/* Methodology note */}
        <div style={{
          padding: "10px 12px", background: T.bg2, borderRadius: 6,
          border: `1px solid ${T.border}`, fontSize: 11, color: T.textDim, lineHeight: 1.6,
        }}>
          <b style={{ color: T.textHi }}>What this tests:</b> A synthetic Aα is injected into
          the antimatter dataset of the selected pair. The full χ² asymmetry pipeline runs on the
          modified data. If the pipeline is correctly calibrated, the recovered Aα and p-value
          should closely match what is expected for the injected signal strength.
          Recovery fraction ≈ 1.0 and |observed σ − expected σ| / expected σ &lt; 20% are the
          pass criteria.
        </div>
      </div>
    </div>
  );
};

// Single result panel

const SingleResultPanel: React.FC<{ result: NullTestResult }> = ({ result }) => {
  const { config, points } = result;
  const expSig  = sigmaFromPval(0.05); // what 0.05 threshold corresponds to
  const obsSig  = sigmaFromPval(result.pvalRecovered);

  return (
    <div className="panel fade-in">
      <PanelHeader
        title={`Result: ${config.label}`}
        icon="chart"
        sub={`Injection mode: ${config.injectionMode} · seed: ${config.seed} · pair: ${config.targetPairId}`}
      />
      <div style={{ padding: 16 }}>

        {/* Key metrics */}
        <div className="split split-4" style={{ marginBottom: 16 }}>
          <Stat
            label="Recovery fraction"
            value={result.recoveryFraction.toFixed(4)}
            color={recoveryColor(result.recoveryFraction)}
            sub={result.recoveryFraction > 0.95 && result.recoveryFraction < 1.05
              ? "✓ within 5%" : "outside 5% tolerance"}
          />
          <Stat
            label="Injected |Aα|"
            value={result.meanInjected.toFixed(4)}
            color={T.blue}
          />
          <Stat
            label="Recovered |Aα|"
            value={result.meanRecovered.toFixed(4)}
            color={recoveryColor(result.recoveryFraction)}
          />
          <Stat
            label="Calibration"
            value={result.calibrationOk ? "PASS" : "FAIL"}
            color={calibrationColor(result.calibrationOk)}
            sub={result.calibrationOk ? "σ within 20%" : "σ outside 20% tolerance"}
          />
        </div>

        {/* Stats table */}
        <div style={{ marginBottom: 16 }}>
          <table className="data-table" style={{ background: T.bg2, borderRadius: 8, overflow: "hidden" }}>
            <thead>
              <tr>
                <th>Statistic</th><th>Value</th><th>Interpretation</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ color: T.textDim }}>Injected |Aα|</td>
                <td style={{ color: T.blue }}>{result.meanInjected.toFixed(4)}</td>
                <td style={{ color: T.textDim }}>Synthetic signal strength</td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>Recovered |Aα|</td>
                <td style={{ color: recoveryColor(result.recoveryFraction) }}>
                  {result.meanRecovered.toFixed(4)}
                </td>
                <td style={{ color: T.textDim }}>
                  Δ = {(result.meanRecovered - result.meanInjected >= 0 ? "+" : "")
                    + (result.meanRecovered - result.meanInjected).toFixed(4)}
                </td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>Recovery fraction</td>
                <td style={{ color: recoveryColor(result.recoveryFraction), fontWeight: 700 }}>
                  {(result.recoveryFraction * 100).toFixed(2)}%
                </td>
                <td style={{ color: T.textDim }}>Target: 95%–105%</td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>χ² (weighted)</td>
                <td>{result.chi2Recovered.toFixed(1)}</td>
                <td style={{ color: T.textDim }}>
                  χ²/dof = {reducedChi2(result.chi2Recovered, config.targetPairId ? 300 : 1).toFixed(0)}
                </td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>p-value (recovered)</td>
                <td style={{ color: pvalColor(result.pvalRecovered) }}>
                  {formatPval(result.pvalRecovered)}
                </td>
                <td style={{ color: T.textDim }}>
                  {result.pvalRecovered < SIG.HIGHLY
                    ? "✓ Correctly detected at p < 0.001"
                    : result.injectedAalpha === 0
                    ? "✓ Null correctly not rejected"
                    : "⚠ Signal not detected at expected significance"}
                </td>
              </tr>
              <tr>
                <td style={{ color: T.textDim }}>Calibration</td>
                <td style={{ color: calibrationColor(result.calibrationOk), fontWeight: 700 }}>
                  {result.calibrationOk ? "PASS" : "FAIL"}
                </td>
                <td style={{ color: T.textDim }}>
                  |Δσ| / σ_expected &lt; 20%
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Per-lambda recovery plot */}
        {points.length > 0 && (
          <div className="split split-2" style={{ gap: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: T.textDim, fontWeight: 600,
                textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 8 }}>
                Per-λ: Injected vs Recovered Aα
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={points} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                  <XAxis dataKey="logLam"
                    tickFormatter={v => `10^${Number(v).toFixed(0)}`}
                    tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }} />
                  <YAxis domain={[-0.1, 1.1]}
                    tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }} width={32} />
                  <Tooltip
                    contentStyle={{ background: T.bg1, border: `1px solid ${T.border}`,
                      borderRadius: 8, fontSize: 11, fontFamily: T.mono }}
                    formatter={(v: number, n: string) => [v.toFixed(4), n]}
                  />
                  <Legend wrapperStyle={{ fontSize: 10, color: T.textDim }} />
                  <ReferenceLine y={0} stroke={T.muted} strokeDasharray="3 3" />
                  <Line type="monotone" dataKey="injectedA" name="Injected"
                    stroke={T.blue} strokeWidth={2} dot={false} strokeDasharray="5 3" />
                  <Line type="monotone" dataKey="recoveredA" name="Recovered"
                    stroke={T.teal} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div>
              <div style={{ fontSize: 11, color: T.textDim, fontWeight: 600,
                textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 8 }}>
                Per-λ Residual (Recovered − Injected)
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={points} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                  <XAxis dataKey="logLam"
                    tickFormatter={v => `10^${Number(v).toFixed(0)}`}
                    tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }} />
                  <YAxis domain={[-0.5, 0.5]}
                    tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }} width={36} />
                  <Tooltip
                    contentStyle={{ background: T.bg1, border: `1px solid ${T.border}`,
                      borderRadius: 8, fontSize: 11, fontFamily: T.mono }}
                    formatter={(v: number) => [v.toFixed(4), "residual"]}
                  />
                  <ReferenceLine y={0} stroke={T.teal} strokeDasharray="4 4" />
                  <defs>
                    <linearGradient id="residGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"   stopColor={T.amber} stopOpacity={0.3} />
                      <stop offset="95%"  stopColor={T.amber} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area type="monotone" dataKey="residual" name="Residual"
                    stroke={T.amber} fill="url(#residGrad)" strokeWidth={1.5} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Battery results panel

const BatteryResultsPanel: React.FC<{
  battery:  NullTestBattery;
  running:  boolean;
  configs:  NullTestConfig[];
}> = ({ battery, running, configs }) => {
  const results = battery.results;

  // Build calibration curve data: injected Aα → recovered Aα
  const curveData = useMemo(() => {
    const done = results.filter(r => r.status === "done");
    return done.map(r => ({
      injected:  r.meanInjected,
      recovered: r.meanRecovered,
      pval:      r.pvalRecovered,
      frac:      r.recoveryFraction,
      ok:        r.calibrationOk,
    })).sort((a, b) => a.injected - b.injected);
  }, [results]);

  // Significance calibration data: injected Aα → observed σ
  const sigData = useMemo(() => {
    return curveData.map(d => ({
      injected: d.injected,
      sigma:    sigmaFromPval(d.pval),
      pval:     d.pval,
    }));
  }, [curveData]);

  const nDone    = results.length;
  const nTotal   = configs.length;
  const nPassed  = results.filter(r => r.calibrationOk).length;
  const avgFrac  = results.length
    ? results.reduce((s, r) => s + r.recoveryFraction, 0) / results.length
    : 0;

  return (
    <div className="panel fade-in">
      <PanelHeader
        title={battery.label}
        icon="layers"
        sub={`${nDone}/${nTotal} tests complete · ${nPassed}/${nDone} calibration pass`}
        right={running
          ? <span style={{ color: T.blue, fontSize: 11, display: "flex", gap: 5, alignItems: "center" }}>
              <span className="spin-anim" style={{ display: "inline-block" }}>
                <Icon name="atom" size={13} />
              </span>
              Running level {nDone + 1} of {nTotal}…
            </span>
          : <span className={`tag ${nPassed === nDone ? "tag-teal" : "tag-amber"}`}>
              {nPassed === nDone ? "All calibrated" : `${nDone - nPassed} failed`}
            </span>
        }
      />
      <div style={{ padding: 16 }}>

        {/* Progress */}
        {running && (
          <div style={{ marginBottom: 16 }}>
            <ProgressBar value={(nDone / nTotal) * 100} height={4} />
            <div style={{ fontSize: 10, color: T.textDim, marginTop: 4, fontFamily: T.mono }}>
              {nDone}/{nTotal} levels complete
            </div>
          </div>
        )}

        {/* Overview stats */}
        <div className="split split-4" style={{ marginBottom: 16 }}>
          <Stat label="Tests run"          value={`${nDone}/${nTotal}`} />
          <Stat label="Calibration pass"
            value={`${nPassed}/${nDone}`}
            color={nPassed === nDone ? T.teal : T.red}
            sub={nPassed === nDone ? "all passed" : `${nDone - nPassed} failed`}
          />
          <Stat label="Avg recovery"
            value={`${(avgFrac * 100).toFixed(1)}%`}
            color={recoveryColor(avgFrac)}
          />
          <Stat label="Null (Aα=0)"
            value={results.find(r => r.meanInjected < 0.02)?.pvalRecovered != null
              ? formatPval(results.find(r => r.meanInjected < 0.02)!.pvalRecovered)
              : "—"
            }
            color={T.teal}
            sub="should be ns"
          />
        </div>

        {curveData.length >= 2 && (
          <div className="split split-2" style={{ gap: 16, marginBottom: 16 }}>

            {/* Recovery calibration curve */}
            <div>
              <div style={{ fontSize: 11, color: T.textDim, fontWeight: 600,
                textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 8 }}>
                Recovery Calibration Curve
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <ScatterChart margin={{ top: 4, right: 16, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                  <XAxis type="number" dataKey="injected" domain={[0, 1.05]} name="Injected |Aα|"
                    tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
                    label={{ value: "Injected |Aα|", position: "insideBottom",
                      offset: -12, fill: T.muted, fontSize: 10 }}
                  />
                  <YAxis type="number" dataKey="recovered" domain={[0, 1.05]} name="Recovered |Aα|"
                    tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
                    width={36}
                    label={{ value: "Recovered |Aα|", angle: -90,
                      position: "insideLeft", fill: T.muted, fontSize: 10 }}
                  />
                  {/* Perfect recovery diagonal */}
                  <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
                    stroke={T.teal} strokeDasharray="5 3"
                    label={{ value: "ideal", fill: T.teal, fontSize: 9 }}
                  />
                  {/* ±5% tolerance band */}
                  <ReferenceLine segment={[{ x: 0, y: 0.05 }, { x: 1, y: 1.05 }]}
                    stroke={T.border} strokeDasharray="3 3" />
                  <ReferenceLine segment={[{ x: 0.05, y: 0 }, { x: 1, y: 0.95 }]}
                    stroke={T.border} strokeDasharray="3 3" />
                  <Tooltip
                    contentStyle={{ background: T.bg1, border: `1px solid ${T.border}`,
                      borderRadius: 8, fontSize: 11, fontFamily: T.mono }}
                    formatter={(v: number, n: string) => [v.toFixed(4), n]}
                  />
                  <Scatter data={curveData} name="Recovery">
                    {curveData.map((d, i) => (
                      <Cell key={i} fill={d.ok ? T.teal : T.red} fillOpacity={0.85} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              <div style={{ fontSize: 10, color: T.textDim, textAlign: "center", marginTop: 4 }}>
                <span style={{ color: T.teal }}>● pass</span>
                <span style={{ marginLeft: 12, color: T.red }}>● fail</span>
                <span style={{ marginLeft: 12, color: T.border }}>--- ±5% tolerance</span>
              </div>
            </div>

            {/* Significance curve */}
            <div>
              <div style={{ fontSize: 11, color: T.textDim, fontWeight: 600,
                textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 8 }}>
                Detection Significance vs Injected |Aα|
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={sigData} margin={{ top: 4, right: 16, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                  <XAxis dataKey="injected" type="number" domain={[0, 1.05]}
                    tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }}
                    label={{ value: "Injected |Aα|", position: "insideBottom",
                      offset: -12, fill: T.muted, fontSize: 10 }}
                  />
                  <YAxis tick={{ fill: T.textDim, fontSize: 9, fontFamily: T.mono }} width={28}
                    label={{ value: "σ", angle: -90,
                      position: "insideLeft", fill: T.muted, fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{ background: T.bg1, border: `1px solid ${T.border}`,
                      borderRadius: 8, fontSize: 11, fontFamily: T.mono }}
                    formatter={(v: number) => [`${v.toFixed(2)} σ`, "significance"]}
                  />
                  {/* 3σ and 5σ reference lines */}
                  <ReferenceLine y={3} stroke={T.amber} strokeDasharray="4 4"
                    label={{ value: "3σ", fill: T.amber, fontSize: 9 }} />
                  <ReferenceLine y={5} stroke={T.red} strokeDasharray="4 4"
                    label={{ value: "5σ", fill: T.red, fontSize: 9 }} />
                  <Line type="monotone" dataKey="sigma" name="Observed σ"
                    stroke={T.blue} strokeWidth={2} dot={{ fill: T.blue, r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Per-level results table */}
        <div>
          <div style={{ fontSize: 11, color: T.textDim, fontWeight: 600,
            textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 8 }}>
            Per-level results
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table" style={{ background: T.bg2, borderRadius: 8, overflow: "hidden" }}>
              <thead>
                <tr>
                  <th>Level #</th>
                  <th>Injected |Aα|</th>
                  <th>Recovered |Aα|</th>
                  <th>Recovery %</th>
                  <th>p-value</th>
                  <th>σ detected</th>
                  <th>Calibration</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {configs.map((cfg, i) => {
                  const res = results.find(r => r.config.id === cfg.id);
                  const isPending = !res;
                  return (
                    <tr key={cfg.id}>
                      <td style={{ color: T.textDim, fontFamily: T.mono }}>{i + 1}</td>
                      <td style={{ color: T.blue, fontFamily: T.mono }}>
                        {cfg.injectedAalpha.toFixed(3)}
                      </td>
                      <td style={{ fontFamily: T.mono }}>
                        {res ? (
                          <span style={{ color: recoveryColor(res.recoveryFraction) }}>
                            {res.meanRecovered.toFixed(4)}
                          </span>
                        ) : "—"}
                      </td>
                      <td style={{ fontFamily: T.mono }}>
                        {res ? (
                          <span style={{ color: recoveryColor(res.recoveryFraction) }}>
                            {(res.recoveryFraction * 100).toFixed(1)}%
                          </span>
                        ) : "—"}
                      </td>
                      <td style={{ fontFamily: T.mono }}>
                        {res
                          ? <span style={{ color: pvalColor(res.pvalRecovered) }}>
                              {formatPval(res.pvalRecovered)}
                            </span>
                          : "—"}
                      </td>
                      <td style={{ fontFamily: T.mono, color: T.textDim }}>
                        {res ? `${sigmaFromPval(res.pvalRecovered).toFixed(1)}σ` : "—"}
                      </td>
                      <td>
                        {res
                          ? <span className={`tag ${res.calibrationOk ? "tag-teal" : "tag-red"}`}>
                              {res.calibrationOk ? "PASS" : "FAIL"}
                            </span>
                          : "—"}
                      </td>
                      <td>
                        {isPending && running && i === nDone
                          ? <span className="tag tag-blue">running</span>
                          : isPending
                          ? <span className="tag tag-muted">pending</span>
                          : <span className="tag tag-teal">done</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Methods note */}
        {!running && nDone === nTotal && (
          <div style={{
            marginTop: 16, padding: "12px 16px", borderRadius: 8,
            background: nPassed === nDone ? T.tealDim : T.amberDim,
            border: `1px solid ${nPassed === nDone ? T.teal : T.amber}40`,
            fontSize: 12, color: T.text, lineHeight: 1.7,
          }}>
            <b style={{ color: nPassed === nDone ? T.teal : T.amber }}>
              {nPassed === nDone
                ? "✓ Framework calibrated"
                : `⚠ ${nDone - nPassed} calibration failure(s)`}
            </b>
            {" — "}
            {nPassed === nDone
              ? `All ${nDone} injection levels recovered within tolerance. The χ² asymmetry pipeline is correctly calibrated across the full Aα range [${curveData[0]?.injected.toFixed(2)} – ${curveData[curveData.length-1]?.injected.toFixed(2)}]. This result should be included in your methods section.`
              : "Some injection levels fall outside the 20% σ tolerance. Review the residual plots for systematic λ-dependent biases. Check the injection mode and verify that the dataset has sufficient point density across the λ overlap window."
            }
          </div>
        )}
      </div>
    </div>
  );
};

// Live log for single test

const RunLog: React.FC<{ log: string[]; progress: number }> = ({ log, progress }) => {
  const logRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    setTimeout(() => logRef.current?.scrollTo(0, logRef.current.scrollHeight), 30);
  }, [log]);

  return (
    <div className="panel">
      <PanelHeader title="Test log" icon="report" sub="Live output from injection pipeline" />
      <div style={{ marginBottom: 4, padding: "8px 16px 0" }}>
        <ProgressBar value={progress} height={3} />
      </div>
      <div ref={logRef} style={{
        padding: 12, fontFamily: T.mono, fontSize: 11, lineHeight: 1.8,
        maxHeight: 200, overflowY: "auto", background: T.bg0,
      }}>
        {log.length === 0 && <div style={{ color: T.muted }}>Waiting for output…</div>}
        {log.map((line, i) => {
          const col = line.includes("[OK]") || line.includes("OK") ? T.teal
            : line.includes("[WARN]") || line.includes("WARN") ? T.amber
            : line.includes("[ERR]") || line.includes("ERROR") ? T.red
            : T.textDim;
          return <div key={i} style={{ color: col }}>{line}</div>;
        })}
        {progress < 100 && <div style={{ color: T.blue }}>▌</div>}
      </div>
    </div>
  );
};

// Main section

export const NullTestSection: React.FC<NullTestSectionProps> = ({ pairs }) => {
  const [mode, setMode]           = useState<"single" | "battery">("single");
  const singleTest                = useNullTest();
  const batteryTest               = useNullTestBattery();
  const [lastBatteryConfigs, setLastBatteryConfigs] = useState<NullTestConfig[]>([]);

  const handleSingle = (cfg: NullTestConfig) => {
    setMode("single");
    singleTest.run(cfg);
  };

  const handleBattery = (
    pairId: string,
    levels: number[],
    injMode: NullTestConfig["injectionMode"]
  ) => {
    setMode("battery");
    const configs: NullTestConfig[] = levels.map((level, i) => ({
      id:             `${pairId}-${level.toFixed(2)}-${Date.now()}`,
      label:          `|Aα| = ${level.toFixed(2)}`,
      targetPairId:   pairId,
      injectedAalpha: level,
      injectionMode:  injMode,
      seed:           42 + i,
    }));
    setLastBatteryConfigs(configs);
    batteryTest.runBattery(pairId, levels, injMode);
  };

  const isRunning = singleTest.status === "running" || batteryTest.running;

  if (pairs.length === 0) {
    return (
      <div className="fade-in" style={{ textAlign: "center", padding: 60, color: T.muted }}>
        <Icon name="validate" size={40} />
        <div style={{ marginTop: 16, fontSize: 14, fontWeight: 600, color: T.textDim }}>
          Run the pipeline first to enable null tests
        </div>
        <div style={{ marginTop: 8, fontSize: 12 }}>
          Null tests require at least one analysed pair to inject into.
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ color: T.textHi, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
          Null Test / Injection Framework
        </h2>
        <p style={{ color: T.textDim, fontSize: 13 }}>
          Inject a known synthetic CPT asymmetry into a pair's antimatter dataset and verify the
          pipeline recovers it at the correct significance. Used to calibrate the χ² framework and
          produce the validation figures required by a methods paper.
        </p>
      </div>

      <div className="split split-2" style={{ alignItems: "start", gap: 16 }}>
        {/* Left: config */}
        <ConfigPanel
          pairs={pairs}
          onRun={handleSingle}
          onBattery={handleBattery}
          isRunning={isRunning}
        />

        {/* Right: live log (single) or battery progress */}
        {(singleTest.log.length > 0 || singleTest.status === "running") && mode === "single" && (
          <RunLog log={singleTest.log} progress={singleTest.progress} />
        )}
        {mode === "battery" && batteryTest.battery && (
          <div style={{ fontSize: 12, color: T.textDim, padding: "12px 0" }}>
            {batteryTest.running
              ? <span style={{ color: T.blue }}>Battery running — results appear below as each level completes.</span>
              : <span style={{ color: T.teal }}>Battery complete.</span>}
          </div>
        )}
      </div>

      {/* Single test result */}
      {mode === "single" && singleTest.result && (
        <div style={{ marginTop: 16 }}>
          <SingleResultPanel result={singleTest.result} />
        </div>
      )}

      {/* Single test error */}
      {mode === "single" && singleTest.status === "error" && (
        <div style={{
          marginTop: 16, padding: "12px 16px", borderRadius: 8,
          background: T.redDim, border: `1px solid ${T.red}40`,
          color: T.red, fontSize: 12,
        }}>
          <Icon name="error" size={14} /> Null test failed — check the server log for details.
        </div>
      )}

      {/* Battery results */}
      {mode === "battery" && batteryTest.battery && lastBatteryConfigs.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <BatteryResultsPanel
            battery={batteryTest.battery}
            running={batteryTest.running}
            configs={lastBatteryConfigs}
          />
        </div>
      )}
    </div>
  );
};