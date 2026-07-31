import { API_BASE_URL } from "../constants";
import type {
  PipelineMode,
  PipelineJob,
  PipelineResults,
  AnalysisPair,
  DataPoint,
  FileTreeNode,
  ApiStatus,
  DatasetRecord,
  NullTestConfig,
  NullTestResult,
  NullTestPoint,
  NullTestStatus,
} from "../types";

// Generic fetcher

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, init);
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText} — ${path}`);
  }
  return res.json() as Promise<T>;
}

// File downloads

function _saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function _filenameFromResponse(res: Response, fallback: string): string {
  const match = res.headers.get("Content-Disposition")?.match(/filename="?([^"]+)"?/);
  return match?.[1] ?? fallback;
}

async function _downloadGet(path: string, fallbackName: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Export failed (${res.status})`);
  }
  _saveBlob(await res.blob(), _filenameFromResponse(res, fallbackName));
}

// Field normalisation: DataPoint

type RawDataPoint = {
  log_lam?: number; logLam?: number;
  log_gm?:  number; logGm?:  number;
  log_ga?:  number; logGa?:  number;
  A?: number; a?: number;
};

function normalisePoint(raw: RawDataPoint): DataPoint {
  return {
    logLam: raw.log_lam ?? raw.logLam ?? 0,
    logGm:  raw.log_gm  ?? raw.logGm  ?? 0,
    logGa:  raw.log_ga  ?? raw.logGa  ?? 0,
    A:      raw.A       ?? raw.a       ?? 0,
  };
}

// Field normalisation: AnalysisPair
//
// The Python server serialises in snake_case. We normalise here — one place,
// zero leakage into components. Safe defaults ensure nothing crashes against
// an older server version.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalisePair(raw: any): AnalysisPair {
  const chi2w = raw.chi2_weighted  ?? raw.chi2Weighted  ?? 0;
  const chi2u = raw.chi2_uniform   ?? raw.chi2Uniform   ?? 0;
  const ratio = raw.chi2_ratio     ?? raw.chi2Ratio
    ?? (chi2u > 0 ? chi2w / chi2u : 1);

  const pvalW = raw.pval_weighted ?? raw.pval ?? raw.p_value ?? 0;
  const pvalU = raw.pval_uniform  ?? raw.pvalUniform ?? pvalW;

  // dof_effective / pval_weighted_eff etc. come from the autocorrelation-length
  // correction in statistics.py — the 300 interpolated grid points per pair are
  // not independent, so treating them as 300 dof overstates significance. These
  // are the numbers actually worth citing; see reporting.py for the equivalent
  // PDF-report fix.
  const dofEff  = raw.dof_effective       ?? raw.dofEffective       ?? undefined;
  const pvalEff = raw.pval_weighted_eff   ?? raw.pvalEffective      ?? undefined;
  const autocorr= raw.autocorr_length     ?? raw.autocorrLength     ?? undefined;
  const ciLow   = raw.aalpha_ci_low       ?? raw.aalphaCiLow        ?? undefined;
  const ciHigh  = raw.aalpha_ci_high      ?? raw.aalphaCiHigh       ?? undefined;

  // experiment_m/experiment_a is what pipeline.py actually emits (the source
  // citation key, e.g. "Fadeev2022"); matter_dataset/matterDataset are kept as
  // fallbacks in case an older or different server payload shape is in use.
  const mDs = basename(raw.matter_dataset     ?? raw.matterDataset     ?? raw.experiment_m ?? "unknown");
  const aDs = basename(raw.antimatter_dataset ?? raw.antimatterDataset ?? raw.experiment_a ?? "unknown");

  const iClass = raw.interaction_class ?? raw.interactionClass
    ?? raw.sector_class ?? inferInteractionClass(raw.sec_m ?? raw.secM ?? "");

  return {
    id:               raw.id ?? `${raw.coupling}-${raw.potential}-${raw.sec_m ?? raw.secM}`,
    coupling:         raw.coupling        ?? "unknown",
    potential:        raw.potential       ?? "UNKNOWN",
    secM:             raw.sec_m           ?? raw.secM           ?? "?",
    secA:             raw.sec_a           ?? raw.secA           ?? "?",
    interactionClass: iClass,
    matterDataset:    mDs,
    antimatterDataset:aDs,
    matterUnit:       raw.matter_unit     ?? raw.matterUnit     ?? "m",
    antimatterUnit:   raw.antimatter_unit ?? raw.antimatterUnit ?? "m",
    meanAbsA:         raw.mean_abs_a      ?? raw.meanAbsA       ?? 0,
    chi2Weighted:     chi2w,
    chi2Uniform:      chi2u,
    chi2Ratio:        ratio,
    pval:             pvalW,
    pvalUniform:      pvalU,
    dof:              raw.dof             ?? 0,
    dofEffective:     dofEff,
    pvalEffective:    pvalEff,
    autocorrLength:   autocorr,
    aalphaCiLow:      ciLow,
    aalphaCiHigh:     ciHigh,
    sigmaM:           raw.sigma_matter     ?? raw.sigmaM   ?? raw.mean_sigma_matter     ?? 0,
    sigmaA:           raw.sigma_antimatter ?? raw.sigmaA   ?? raw.mean_sigma_antimatter ?? 0,
    lambdaMin:        raw.lambda_min      ?? raw.lambdaMin ?? 0,
    lambdaMax:        raw.lambda_max      ?? raw.lambdaMax ?? 1,
    points:           (raw.points ?? []).map(normalisePoint),
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normaliseResults(raw: any): PipelineResults {
  const pairs: AnalysisPair[] = (raw.pairs ?? []).map(normalisePair);
  return {
    pairs,
    meta: {
      run_id:        raw.meta?.run_id       ?? raw.run_id       ?? "unknown",
      mode:          raw.meta?.mode         ?? raw.mode         ?? "full",
      completed_at:  raw.meta?.completed_at ?? raw.completed_at ?? new Date().toISOString(),
      n_pairs:       raw.meta?.n_pairs      ?? pairs.length,
      n_significant: raw.meta?.n_significant
        ?? pairs.filter((p: AnalysisPair) => (p.pvalEffective ?? p.pval) < 0.05).length,
    },
  };
}

function basename(s: string): string {
  return s.replace(/\\/g, "/").split("/").pop()?.replace(/\.[^.]+$/, "") ?? s;
}

function inferInteractionClass(sec: string): string {
  const s = sec.toLowerCase();
  if (s.includes("p") || s.includes("n")) return "lepton-nucleon";
  if (s.includes("e") || s.includes("mu") || s.includes("tau")) return "lepton-lepton";
  return "unknown";
}

// Field normalisation: Provenance

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normaliseProvenanceRecord(raw: any): Partial<DatasetRecord> {
  return {
    name:           raw.name           ?? raw.dataset,
    authors:        raw.authors        ?? raw.author  ?? "",
    year:           raw.year           ?? 0,
    journal:        raw.journal        ?? raw.reference ?? "",
    doi:            raw.doi            ?? undefined,
    arxiv:          raw.arxiv          ?? raw.arxiv_id ?? undefined,
    conversionNote: raw.conversion_note ?? raw.conversionNote ?? undefined,
  };
}

// Field normalisation: Null test

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normaliseNullTestPoint(raw: any): NullTestPoint {
  const injected  = raw.injected_a  ?? raw.injectedA  ?? 0;
  const recovered = raw.recovered_a ?? raw.recoveredA ?? 0;
  return {
    logLam:         raw.log_lam        ?? raw.logLam  ?? 0,
    injectedA:      injected,
    recoveredA:     recovered,
    residual:       recovered - injected,
    withinOneSigma: raw.within_one_sigma ?? raw.withinOneSigma
      ?? Math.abs(recovered - injected) < 0.1,
  };
}

function normaliseNullTestResult(config: NullTestConfig, raw: any): NullTestResult {
  const points: NullTestPoint[] = (raw.points ?? []).map(normaliseNullTestPoint);
  const meanInj = raw.mean_injected  ?? raw.meanInjected  ?? config.injectedAalpha;
  const meanRec = raw.mean_recovered ?? raw.meanRecovered
    ?? (points.length ? points.reduce((s, p) => s + p.recoveredA, 0) / points.length : 0);
  const expSig = raw.expected_sigma ?? raw.expectedSigma ?? 0;
  const obsSig = raw.observed_sigma ?? raw.observedSigma ?? 0;

  return {
    config,
    injectedAalpha:   config.injectedAalpha,   // ← add this line
    jobId:            raw.job_id         ?? raw.jobId         ?? "",
    status:           (raw.status as NullTestStatus)          ?? "done",
    log:              raw.log            ?? [],
    meanInjected:     meanInj,
    meanRecovered:    meanRec,
    recoveryFraction: meanInj > 0 ? meanRec / meanInj : 0,
    chi2Recovered:    raw.chi2_recovered ?? raw.chi2Recovered ?? 0,
    pvalRecovered:    raw.pval_recovered ?? raw.pvalRecovered ?? 0,
    points,
    expectedSigma:    expSig,
    observedSigma:    obsSig,
    calibrationOk:    expSig > 0
      ? Math.abs(obsSig - expSig) / expSig < 0.2
      : Math.abs(meanRec - meanInj) < 0.05,
  };
}
// Config hash
//
// Deterministic fingerprint of a run: mode + sorted pair IDs.
// Used by the history feature to flag runs that used identical configurations.

export function buildConfigHash(mode: PipelineMode, pairs: AnalysisPair[]): string {
  const key = mode + "|" + pairs.map(p => p.id).sort().join(",");
  let h = 5381;
  for (let i = 0; i < key.length; i++) {
    h = ((h << 5) + h) ^ key.charCodeAt(i);
    h = h >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}

// Returned by uploadDatasets when filename encodes folder info
export interface UploadSuggestion {
  filename:          string;
  coupling:          string;
  interaction_class: string;
  sector:            string;
  suggested_path:    string;
  suggested_dir:     string;
}

// Public API client

export const apiClient = {
  // Pipeline

  /** Submit a new pipeline job → { job_id }. */
  run(mode: PipelineMode = "full"): Promise<{ job_id: string }> {
    return request(`/api/run?mode=${mode}`, { method: "POST" });
  },

  /** Poll job status and log lines. */
  pollJob(jobId: string): Promise<PipelineJob> {
    return request<PipelineJob>(`/api/job/${jobId}`);
  },

  /**
   * Fetch and normalise final results.
   * All snake_case → camelCase conversion and missing-field defaults happen
   * here so every component can assume fully-typed AnalysisPair[].
   */
  async getResults(jobId: string): Promise<PipelineResults> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw = await request<any>(`/api/results/${jobId}`);
    return normaliseResults(raw);
  },

  async uploadDatasets(
    files: File[]
  ): Promise<{ saved: string[]; warnings: string[]; suggestions: UploadSuggestion[] }> {
    const form = new FormData();
    files.forEach(f => form.append("files", f));
    const res = await fetch(`${API_BASE_URL}/api/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error(`Upload failed ${res.status}: ${res.statusText}`);
    return res.json();
  },

  async organizeDataset(
    filename: string,
    coupling: string,
    interaction_class: string
  ): Promise<{ moved_to: string }> {
    const res = await fetch(`${API_BASE_URL}/api/organize`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, coupling, interaction_class }),
    });
    if (!res.ok) throw new Error(`Organize failed ${res.status}: ${res.statusText}`);
    return res.json();
  },

  

  // Status / tree

  /** Lightweight health check — returns null on any network failure. */
  async getStatus(): Promise<ApiStatus | null> {
    try {
      return await request<ApiStatus>("/api/status");
    } catch {
      return null;
    }
  },

  /** Server-side dataset directory tree. */
  async getTree(): Promise<FileTreeNode> {
    return request<FileTreeNode>("/api/tree");
  },

  // Provenance

  /**
   * Optional citation enrichment — GET /api/provenance.
   * Returns partial DatasetRecord overrides keyed by dataset name.
   * Returns an empty map if the endpoint is not yet implemented.
   */
  async getProvenance(): Promise<Map<string, Partial<DatasetRecord>>> {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const raw = await request<any[]>("/api/provenance");
      const map = new Map<string, Partial<DatasetRecord>>();
      for (const item of raw) {
        const record = normaliseProvenanceRecord(item);
        if (record.name) map.set(record.name, record);
      }
      return map;
    } catch {
      return new Map();
    }
  },

  // Null test

  /**
   * Run a null-injection test.
   * POST /api/null_test runs synchronously and returns the full result in
   * one response — there is no background job/poll step for this endpoint.
   * Body: { pair_id, injected_aalpha, injection_mode, seed, label }
   * Returns NullTestResult (normalised from snake_case server response).
   */
  async runNullTest(cfg: NullTestConfig): Promise<NullTestResult> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw = await request<any>("/api/null_test", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pair_id:         cfg.targetPairId,
        injected_aalpha: cfg.injectedAalpha,
        injection_mode:  cfg.injectionMode,
        seed:            cfg.seed,
        label:           cfg.label,
      }),
    });
    return normaliseNullTestResult(cfg, raw);
  },

  // Dataset upload

  // Folder management

  async createFolder(path: string): Promise<{ created: string }> {
    const res = await fetch(`${API_BASE_URL}/api/datasets/folder`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ path }),
    });
    if (!res.ok) throw new Error(`Create folder failed: ${res.statusText}`);
    return res.json();
  },

  async renameItem(oldPath: string, newPath: string): Promise<{ renamed_to: string }> {
    const res = await fetch(`${API_BASE_URL}/api/datasets/rename`, {
      method:  "PUT",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ old_path: oldPath, new_path: newPath }),
    });
    if (!res.ok) throw new Error(`Rename failed: ${res.statusText}`);
    return res.json();
  },

  /**
   * Delete a single CSV from DATA_ROOT by filename.
   * DELETE /api/datasets/{filename}
   */
  async deleteDataset(relativePath: string): Promise<{ deleted: string }> {
    const res = await fetch(
        `${API_BASE_URL}/api/datasets/${encodeURIComponent(relativePath)}`,
        { method: "DELETE" }
      );
      if (!res.ok) throw new Error(`Delete failed: ${res.statusText}`);
      return res.json();
    },

    async listFolders(): Promise<string[]> {
    const res = await fetch(`${API_BASE_URL}/api/datasets/folders`);
    if (!res.ok) throw new Error(`List folders failed: ${res.statusText}`);
    const data = await res.json();
    return data.folders ?? [];
  },

  async moveFile(
    filename: string,
    fromPath: string,         // relative path of the file e.g. gAgA/lepton-lepton/V2_Fadeev2022_ee_gAgA.csv
    toFolder: string          // destination folder e.g. gAgA/Nucleon-Nucleon
  ): Promise<{ moved_to: string }> {
    const res = await fetch(`${API_BASE_URL}/api/datasets/rename`, {
      method:  "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        old_path: fromPath,
        new_path: `${toFolder}/${filename}`,
      }),
    });
    if (!res.ok) throw new Error(`Move failed: ${res.statusText}`);
    return res.json();
  },

  // Export

  downloadReport():         Promise<void> { return _downloadGet("/api/export/report", "asymmetry_report.pdf"); },
  downloadSummaryCsv():     Promise<void> { return _downloadGet("/api/export/summary-csv", "asymmetry_summary.csv"); },
  downloadPlots():          Promise<void> { return _downloadGet("/api/export/plots", "asymmetry_plots.zip"); },
  downloadConstraintAtlas():Promise<void> { return _downloadGet("/api/export/constraint-atlas", "constraint_atlas.zip"); },
  downloadGapAnalysis():    Promise<void> { return _downloadGet("/api/export/gap-analysis", "gap_analysis_figures.zip"); },
  downloadConfig():         Promise<void> { return _downloadGet("/api/export/config", "spindep_run_config.yaml"); },

  async downloadHdf5(pairs: AnalysisPair[]): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/api/export/hdf5`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ pairs }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ?? `Export failed (${res.status})`);
    }
    _saveBlob(await res.blob(), _filenameFromResponse(res, "spindep_data_archive.h5"));
  },
};