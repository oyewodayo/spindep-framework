// Design Tokens

export const T = {
  // Backgrounds
  bg0:       "#050810",
  bg1:       "#08101a",
  bg2:       "#0c1624",
  surface:   "#0f1e30",
  panel:     "#122238",

  // Borders
  border:    "#1a2e45",
  borderHi:  "#234060",

  // Blue family
  blue:      "#4a9eff",
  blueD:     "#1a4a8a",
  blueDim:   "#0d2040",

  // Teal family
  teal:      "#2dd4bf",
  tealDim:   "#0a2520",

  // Amber family
  amber:     "#fbbf24",
  amberD:    "#78350f",
  amberDim:  "#1e1200",

  // Red family
  red:       "#f87171",
  redDim:    "#2a0a0a",

  // Green family
  green:     "#34d399",
  greenDim:  "#0a1f17",

  // Violet family
  violet:    "#a78bfa",
  violetDim: "#1a1040",

  // Neutrals
  muted:     "#3a5570",
  dim:       "#2a4060",
  text:      "#b8cfe8",
  textDim:   "#5a7898",
  textHi:    "#dceeff",

  // Typography
  mono:      "'IBM Plex Mono', 'Fira Code', monospace",
  sans:      "'IBM Plex Sans', 'DM Sans', sans-serif",
} as const;

export type DesignToken = typeof T;

// API Constants

export const API_BASE_URL = "http://localhost:8001";
export const API_POLL_INTERVAL_MS = 1_000;
export const API_HEALTH_INTERVAL_MS = 5_000;

// Pipeline Constants

export const PIPELINE_STEPS: Record<string, string[]> = {
  full:     ["Discovering datasets", "Unit audit & conversion", "Matching matter–antimatter pairs", "Computing χ² & asymmetry", "Gap analysis", "Constraint atlas", "Generating report"],
  validate: ["Discovering datasets", "Unit audit & conversion", "Matching matter–antimatter pairs", "Generating validation report"],
  gaps:     ["Discovering datasets", "Scanning λ coverage", "Gap analysis figures"],
  atlas:    ["Discovering datasets", "Constraint atlas plots"],
};

// Navigation

import type { NavSection } from "../types";

export interface NavItem {
  id: NavSection;
  label: string;
  icon: string;
  group: "Data" | "Analysis" | "Validation" | "Output";
}

export const NAV_ITEMS: NavItem[] = [
  { id: "ingest",         label: "Ingest",                icon: "upload",   group: "Data"       },
  { id: "pipeline",       label: "Pipeline Runner",       icon: "play",     group: "Data"       },
  { id: "history",        label: "Run History",           icon: "layers",   group: "Data"       },
  { id: "batch",          label: "Batch Results",         icon: "table",    group: "Analysis"   },
  { id: "pairs",          label: "Per-Pair Plots",        icon: "chart",    group: "Analysis"   },
  { id: "interpretation", label: "Interpretation",        icon: "validate", group: "Analysis"   },
  { id: "provenance",     label: "Dataset Provenance",    icon: "report",   group: "Analysis"   },
  { id: "coverage",       label: "λ Coverage Viewer",     icon: "scope",    group: "Analysis"   },
  { id: "atlas",          label: "Constraint Atlas",      icon: "layers",   group: "Analysis"   },
  { id: "gaps",           label: "Gap Analysis",          icon: "grid",     group: "Analysis"   },
  { id: "nulltest",       label: "Null Test / Injection", icon: "atom",     group: "Validation" },
  { id: "export",         label: "Export & Report",       icon: "dl",       group: "Output"     },
];

export const NAV_GROUPS = ["Data", "Analysis", "Validation", "Output"] as const;

// Significance Thresholds

export const SIG = {
  HIGHLY: 0.001,
  STANDARD: 0.05,
} as const;