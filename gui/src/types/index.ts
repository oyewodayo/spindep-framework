export type CouplingType = "gAgA" | "gsgs" | "gVgV" | "gpgp" | "gpgs" | string;
export type PotentialType = "Yukawa" | "power-law" | string;
export type PipelineMode = "full" | "validate" | "gaps" | "atlas";
export type JobStatus = "queued" | "running" | "done" | "error";
export type NavSection =
  | "ingest" | "pipeline" | "batch" | "pairs"
  | "atlas" | "gaps" | "export"
  | "interpretation" | "provenance" | "coverage"
  | "history" | "nulltest";

export interface DataPoint {
  logLam: number;
  logGm: number;
  logGa: number;
  A: number;
}

export interface AnalysisPair {
  // Identity
  id: string;
  coupling: CouplingType;
  potential: PotentialType;

  // Sectors
  secM: string;           // matter sector label (e.g. "ee", "ep")
  secA: string;           // antimatter sector label
  interactionClass: string; // e.g. "lepton-lepton", "lepton-nucleon"

  // Dataset metadata
  matterDataset: string;     // e.g. "Delaunay2017"
  antimatterDataset: string; // e.g. "Adkins2022"
  matterUnit: string;        // e.g. "m", "m (pre-converted)"
  antimatterUnit: string;

  // Core statistics
  meanAbsA: number;         // mean |Aα|
  chi2Weighted: number;     // χ² with per-point curvature weights
  chi2Uniform: number;      // χ² with uniform 10% uncertainty
  chi2Ratio: number;        // chi2Weighted / chi2Uniform — <1 means weighted is more conservative
  pval: number;             // p-value (weighted), nominal — assumes all 300 grid points are
                             // independent degrees of freedom, which they are not (they're
                             // interpolated from far fewer real measurements). Use pvalEffective
                             // for the number actually worth citing.
  pvalUniform: number;      // p-value (uniform)
  dof: number;

  // Autocorrelation-corrected significance (see statistics.py: effective_dof).
  // Optional because older server payloads may not include them.
  dofEffective?: number;     // effective dof from the residual autocorrelation length
  pvalEffective?: number;    // p-value against dofEffective — preferred for thesis
  autocorrLength?: number;   // autocorrelation length, in grid points
  aalphaCiLow?: number;      // 95% bootstrap CI lower bound on mean |Aα|
  aalphaCiHigh?: number;     // 95% bootstrap CI upper bound on mean |Aα|

  // Uncertainty estimates
  sigmaM: number;           // mean σ_matter (%)
  sigmaA: number;           // mean σ_antimatter (%)

  // Lambda range
  lambdaMin: number;
  lambdaMax: number;

  // Per-point data for charts
  points: DataPoint[];
}

export interface PipelineJob {
  job_id: string;
  status: JobStatus;
  log: string[];
  created_at: string;
  completed_at?: string;
}

export interface PipelineResults {
  pairs: AnalysisPair[];
  meta: {
    run_id: string;
    mode: PipelineMode;
    completed_at: string;
    n_pairs: number;
    n_significant: number;
  };
}

export interface FileTreeNode {
  name: string;
  type: "folder" | "file";
  rows?: number;
  children?: FileTreeNode[];
}

export interface ApiStatus {
  version: string;
  uptime: number;
  datasets_path: string;
}

export type ConversionFlag = "none" | "pre-converted" | "unknown";

export interface DatasetRecord {
  name: string;                   // e.g. "Delaunay2017"
  authors: string;                // short author list
  year: number;
  journal: string;                // e.g. "Phys. Rev. D"
  doi?: string;
  arxiv?: string;
  sector: string;                 // e.g. "ee", "ep"
  interactionClass: string;
  originalUnit: string;           // unit as published
  storedUnit: string;             // unit in datasets/normalized/
  conversionFlag: ConversionFlag;
  conversionNote?: string;        // human-readable description of what was done
  lambdaMin: number;
  lambdaMax: number;
  nPoints: number;
  couplings: string[];            // which coupling constants this dataset constrains
  appearsInPairs: string[];       // pair IDs this dataset participates in
  isMatter: boolean;
}

export type SystematicSeverity = "ok" | "warn" | "critical";

export interface SystematicFlag {
  pairId: string;
  code: string;           // e.g. "LAMBDA_MISMATCH", "UNIT_CONVERSION", "HIGH_CHI2_RATIO"
  severity: SystematicSeverity;
  message: string;
  detail: string;
}

export interface LambdaOverlapBand {
  logLamStart: number;
  logLamEnd: number;
  datasets: string[];     // names of datasets covering this range
  competitive: boolean;   // true if matter & antimatter constraints are within 2 orders of magnitude
}

export interface CoverageEntry {
  dataset: string;
  isMatter: boolean;
  coupling: string;
  sector: string;
  logLamMin: number;
  logLamMax: number;
  color: string;
}

export interface SortConfig<T> {
  key: keyof T;
  direction: "asc" | "desc";
}

export interface FilterState {
  query: string;
  coupling: CouplingType | "All";
}

export interface CoverageCell {
  coupling: CouplingType;
  potential: PotentialType;
  paired: number;
}

export interface TooltipPayloadItem {
  name: string;
  value: number;
  color?: string;
}

export interface RunSummary {
  nPairs:       number;
  nSignificant: number;
  avgAbsA:      number;
  couplings:    string[];
  datasets:     string[];    // unique dataset names involved
}

export interface RunRecord {
  id:          string;       // jobId from the server
  timestamp:   string;       // ISO-8601
  mode:        PipelineMode;
  configHash:  string;       // sha256-like fingerprint of the dataset tree + mode
  label:       string;       // user-editable name, defaults to timestamp
  summary:     RunSummary;
  pairs:       AnalysisPair[];
  log:         string[];
}

export type NullTestStatus = "idle" | "configuring" | "running" | "done" | "error";

/** A single injection scenario */
export interface NullTestConfig {
  id:              string;
  label:           string;
  targetPairId:    string;          // which pair to inject into
  injectedAalpha:  number;          // 0 = pure null, 0.5 = moderate, 1.0 = maximal
  injectionMode:   "scale" | "replace" | "shift";  // how to apply injection
  seed:            number;          // RNG seed for reproducibility
}

/** Per-lambda recovery statistics for a single injection test */
export interface NullTestPoint {
  logLam:           number;
  injectedA:        number;   // what we put in
  recoveredA:       number;   // what the pipeline measured
  residual:         number;   // recoveredA - injectedA
  withinOneSigma:   boolean;
}

/** Full result of one null test run */
export interface NullTestResult {
  injectedAalpha: number;
  config:          NullTestConfig;
  jobId:           string;
  status:          NullTestStatus;
  log:             string[];
  // Recovery statistics
  meanInjected:    number;
  meanRecovered:   number;
  recoveryFraction: number;   // meanRecovered / meanInjected (1.0 = perfect)
  chi2Recovered:   number;
  pvalRecovered:   number;
  // Per-point data
  points:          NullTestPoint[];
  // Calibration: did significance scale correctly?
  expectedSigma:   number;    // how many σ we expect to detect injectedAalpha
  observedSigma:   number;    // how many σ we actually detected
  calibrationOk:   boolean;   // |observedSigma - expectedSigma| / expectedSigma < 0.2
}

/** A battery of null tests across a range of injected Aα values */
export interface NullTestBattery {
  id:        string;
  label:     string;
  pairId:    string;
  configs:   NullTestConfig[];
  results:   NullTestResult[];
  createdAt: string;
}