import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient } from "../api/client";
import { API_HEALTH_INTERVAL_MS, API_POLL_INTERVAL_MS } from "../constants";
import { estimateProgress } from "../utils";
import type { AnalysisPair, JobStatus, PipelineMode } from "../types";

// ─── useApiHealth ──────────────────────────────────────────────────────────────

export function useApiHealth(): boolean {
  const [online, setOnline] = useState(false);

  useEffect(() => {
    const check = async () => setOnline(!!(await apiClient.getStatus()));
    check();
    const id = setInterval(check, API_HEALTH_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  return online;
}

// ─── usePipelineJob ────────────────────────────────────────────────────────────

interface UsePipelineJobReturn {
  log: string[];
  progress: number;
  status: JobStatus;
}

export function usePipelineJob(
  jobId: string | null,
  onComplete?: () => void
): UsePipelineJobReturn {
  const [log, setLog]           = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [status, setStatus]     = useState<JobStatus>("queued");
  const cancelRef               = useRef(false);

  useEffect(() => {
    if (!jobId) return;
    cancelRef.current = false;

    const poll = async () => {
      while (!cancelRef.current) {
        try {
          const job = await apiClient.pollJob(jobId);
          if (cancelRef.current) break;

          setLog(job.log ?? []);
          setProgress(estimateProgress(job.log?.length ?? 0));

          if (job.status === "done") {
            setProgress(100);
            setStatus("done");
            setTimeout(() => onComplete?.(), 600);
            return;
          }
          if (job.status === "error") {
            setStatus("error");
            return;
          }
        } catch {
          // Network blip — keep polling
        }
        await new Promise(r => setTimeout(r, API_POLL_INTERVAL_MS));
      }
    };

    poll();
    return () => { cancelRef.current = true; };
  }, [jobId, onComplete]);

  return { log, progress, status };
}

// ─── usePipeline ───────────────────────────────────────────────────────────────

interface UsePipelineReturn {
  jobId: string | null;
  mode: PipelineMode;
  pairs: AnalysisPair[];
  resultsReady: boolean;
  lastLog: string[];
  startRun: (mode: PipelineMode) => Promise<void>;
  handleComplete: () => Promise<{ pairs: AnalysisPair[]; log: string[] } | null>;
}

export function usePipeline(): UsePipelineReturn {
  const [jobId, setJobId]               = useState<string | null>(null);
  const [mode, setMode]                 = useState<PipelineMode>("full");
  const [pairs, setPairs]               = useState<AnalysisPair[]>([]);
  const [resultsReady, setResultsReady] = useState(false);
  const [lastLog, setLastLog]           = useState<string[]>([]);

  const startRun = useCallback(async (m: PipelineMode) => {
    setMode(m);
    try {
      const { job_id } = await apiClient.run(m);
      setJobId(job_id);
    } catch {
      console.error("Could not reach API — is app_server.py running on port 8001?");
    }
  }, []);

  const handleComplete = useCallback(async (): Promise<{ pairs: AnalysisPair[]; log: string[] } | null> => {
    if (!jobId) return null;
    try {
      const data = await apiClient.getResults(jobId);
      if (data?.pairs?.length) {
        // Fetch log for history record
        const job = await apiClient.pollJob(jobId).catch(() => ({ log: [] as string[] }));
        const log = (job as any).log ?? [];
        setPairs(data.pairs);
        setLastLog(log);
        setResultsReady(true);
        return { pairs: data.pairs, log };
      }
    } catch (e) {
      console.error("Failed to fetch results:", e);
    }
    return null;
  }, [jobId]);

  return { jobId, mode, pairs, resultsReady, lastLog, startRun, handleComplete };
}

// ─── useSort ──────────────────────────────────────────────────────────────────

export function useSort<T>(defaultKey: keyof T, defaultDir: "asc" | "desc" = "asc") {
  const [sort, setSort] = useState<{ key: keyof T; direction: "asc" | "desc" }>({
    key: defaultKey,
    direction: defaultDir,
  });

  const toggleSort = useCallback((key: keyof T) => {
    setSort(prev =>
      prev.key === key
        ? { key, direction: prev.direction === "asc" ? "desc" : "asc" }
        : { key, direction: "asc" }
    );
  }, []);

  return { sort, toggleSort };
}

// ─── useCopyToClipboard ────────────────────────────────────────────────────────

export function useCopyToClipboard(resetDelay = 1_600) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copy = useCallback((key: string, text: string) => {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), resetDelay);
  }, [resetDelay]);

  return { copiedKey, copy };
}

// ─── useRunHistory ────────────────────────────────────────────────────────────
// Persists run records to localStorage so the UI is stateful across refreshes.
// Each record stores the full AnalysisPair[] so results can be restored.

import { buildConfigHash } from "../api/client";
import type { RunRecord, RunSummary, NullTestConfig, NullTestResult, NullTestStatus, NullTestBattery } from "../types";

const STORAGE_KEY = "spindep_run_history_v1";
const MAX_HISTORY = 20; // keep last 20 runs

function loadHistory(): RunRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as RunRecord[]) : [];
  } catch {
    return [];
  }
}

function saveHistory(records: RunRecord[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records.slice(0, MAX_HISTORY)));
  } catch {
    // Storage quota exceeded — silently skip
  }
}

function buildSummary(pairs: AnalysisPair[]): RunSummary {
  return {
    nPairs:       pairs.length,
    nSignificant: pairs.filter(p => p.pval < 0.05).length,
    avgAbsA:      pairs.length
      ? pairs.reduce((s, p) => s + p.meanAbsA, 0) / pairs.length
      : 0,
    couplings:    [...new Set(pairs.map(p => p.coupling))],
    datasets:     [...new Set([
      ...pairs.map(p => p.matterDataset),
      ...pairs.map(p => p.antimatterDataset),
    ])],
  };
}

interface UseRunHistoryReturn {
  history:       RunRecord[];
  activeRunId:   string | null;
  addRun:        (jobId: string, mode: PipelineMode, pairs: AnalysisPair[], log: string[]) => RunRecord;
  restoreRun:    (id: string) => AnalysisPair[] | null;
  deleteRun:     (id: string) => void;
  renameRun:     (id: string, label: string) => void;
  clearHistory:  () => void;
}

export function useRunHistory(): UseRunHistoryReturn {
  const [history, setHistory] = useState<RunRecord[]>(() => loadHistory());
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const addRun = useCallback(
    (jobId: string, mode: PipelineMode, pairs: AnalysisPair[], log: string[]): RunRecord => {
      const record: RunRecord = {
        id:         jobId,
        timestamp:  new Date().toISOString(),
        mode,
        configHash: buildConfigHash(mode, pairs),
        label:      `${mode} · ${new Date().toLocaleString()}`,
        summary:    buildSummary(pairs),
        pairs,
        log,
      };
      setHistory(prev => {
        const next = [record, ...prev.filter(r => r.id !== jobId)].slice(0, MAX_HISTORY);
        saveHistory(next);
        return next;
      });
      setActiveRunId(jobId);
      return record;
    },
    []
  );

  const restoreRun = useCallback((id: string): AnalysisPair[] | null => {
    const record = history.find(r => r.id === id);
    if (!record) return null;
    setActiveRunId(id);
    return record.pairs;
  }, [history]);

  const deleteRun = useCallback((id: string) => {
    setHistory(prev => {
      const next = prev.filter(r => r.id !== id);
      saveHistory(next);
      return next;
    });
  }, []);

  const renameRun = useCallback((id: string, label: string) => {
    setHistory(prev => {
      const next = prev.map(r => r.id === id ? { ...r, label } : r);
      saveHistory(next);
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return { history, activeRunId, addRun, restoreRun, deleteRun, renameRun, clearHistory };
}

// ─── useNullTest ──────────────────────────────────────────────────────────────
// Manages one null-injection job: submit → poll → result.

interface UseNullTestReturn {
  status:   NullTestStatus;
  log:      string[];
  progress: number;
  result:   NullTestResult | null;
  run:      (cfg: NullTestConfig) => Promise<void>;
  reset:    () => void;
}

export function useNullTest(): UseNullTestReturn {
  const [status,   setStatus]   = useState<NullTestStatus>("idle");
  const [log,      setLog]      = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [result,   setResult]   = useState<NullTestResult | null>(null);
  const cancelRef = useRef(false);

  const run = useCallback(async (cfg: NullTestConfig) => {
    setStatus("running");
    setLog([]);
    setProgress(0);
    setResult(null);
    cancelRef.current = false;

    try {
      const { job_id } = await (apiClient as any).runNullTest(cfg);

      // Poll job (reuse same poll pattern as pipeline)
      while (!cancelRef.current) {
        try {
          const job = await apiClient.pollJob(job_id);
          if (cancelRef.current) break;

          setLog(job.log ?? []);
          setProgress(estimateProgress(job.log?.length ?? 0));

          if (job.status === "done") {
            setProgress(100);
            const res = await (apiClient as any).getNullTestResult(cfg, job_id);
            setResult(res);
            setStatus("done");
            return;
          }
          if (job.status === "error") {
            setStatus("error");
            return;
          }
        } catch {
          // network blip
        }
        await new Promise(r => setTimeout(r, API_POLL_INTERVAL_MS));
      }
    } catch (e) {
      console.error("Null test failed:", e);
      setStatus("error");
    }
  }, []);

  const reset = useCallback(() => {
    cancelRef.current = true;
    setStatus("idle");
    setLog([]);
    setProgress(0);
    setResult(null);
  }, []);

  return { status, log, progress, result, run, reset };
}

// ─── useNullTestBattery ────────────────────────────────────────────────────────
// Runs a battery of null tests sequentially across multiple injected Aα values.

interface UseNullTestBatteryReturn {
  battery:  NullTestBattery | null;
  running:  boolean;
  runBattery: (pairId: string, levels: number[], mode: NullTestConfig["injectionMode"]) => Promise<void>;
  reset:    () => void;
}

export function useNullTestBattery(): UseNullTestBatteryReturn {
  const [battery, setBattery] = useState<NullTestBattery | null>(null);
  const [running, setRunning] = useState(false);
  const cancelRef = useRef(false);

  const runBattery = useCallback(async (
    pairId: string,
    levels: number[],
    mode: NullTestConfig["injectionMode"]
  ) => {
    cancelRef.current = false;
    setRunning(true);

    const configs: NullTestConfig[] = levels.map((level, i) => ({
      id:             `${pairId}-${level.toFixed(2)}-${Date.now()}`,
      label:          `|Aα| = ${level.toFixed(2)}`,
      targetPairId:   pairId,
      injectedAalpha: level,
      injectionMode:  mode,
      seed:           42 + i,
    }));

    const newBattery: NullTestBattery = {
      id:        `battery-${Date.now()}`,
      label:     `Battery: ${pairId} · ${levels.length} levels`,
      pairId,
      configs,
      results:   [],
      createdAt: new Date().toISOString(),
    };
    setBattery({ ...newBattery });

    for (const cfg of configs) {
      if (cancelRef.current) break;
      try {
        const { job_id } = await (apiClient as any).runNullTest(cfg);

        // Poll to completion
        let done = false;
        while (!done && !cancelRef.current) {
          await new Promise(r => setTimeout(r, API_POLL_INTERVAL_MS));
          try {
            const job = await apiClient.pollJob(job_id);
            if (job.status === "done") {
              const res = await (apiClient as any).getNullTestResult(cfg, job_id);
              setBattery(prev => prev
                ? { ...prev, results: [...prev.results, res] }
                : null
              );
              done = true;
            } else if (job.status === "error") {
              done = true;
            }
          } catch { /* retry */ }
        }
      } catch (e) {
        console.error("Battery step failed:", e);
      }
    }

    setRunning(false);
  }, []);

  const reset = useCallback(() => {
    cancelRef.current = true;
    setBattery(null);
    setRunning(false);
  }, []);

  return { battery, running, runBattery, reset };
}