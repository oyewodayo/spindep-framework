# SPINDEP

**Spin-Dependent Exotic Interaction Analysis Framework**

A Python pipeline for systematic analysis of matter–antimatter asymmetry in spin-dependent exotic interactions, built for M.Sc./Ph.D.-level research in physics beyond the Standard Model.

---

## Table of Contents

1. [Overview](#overview)
2. [Physics Background](#physics-background)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Usage — Terminal Commands](#usage--terminal-commands)
6. [Usage — Config Files](#usage--config-files)
7. [Usage — Batch Processing](#usage--batch-processing)
8. [Usage — Python API](#usage--python-api)
9. [Dataset File Naming Convention](#dataset-file-naming-convention)
10. [Data Preparation Reference](#data-preparation-reference)
11. [Complete Command Reference](#complete-command-reference)
12. [Output Files](#output-files)
13. [Module Reference](#module-reference)
14. [Interpreting Results](#interpreting-results)
15. [Extending the Framework](#extending-the-framework)
16. [Troubleshooting](#troubleshooting)
17. [File Structure](#file-structure)
18. [Citation](#citation)
19. [License](#license)

---

## Overview

SPINDEP automates the comparison of experimental coupling-constant upper bounds between matter and antimatter sectors across a range of interaction ranges λ. For each compatible matter–antimatter pair, it:

1. Discovers and classifies constraint datasets from a structured directory tree
2. Matches matter datasets to their antimatter conjugates
3. Interpolates both constraint curves onto a common log-spaced λ grid
4. Computes the **asymmetry parameter** A_α = (g_matter − g_antimatter) / (g_matter + g_antimatter)
5. Runs a χ² sensitivity test to quantify the statistical significance of any observed asymmetry
6. Generates publication-quality comparison plots
7. Exports a full PDF analysis report with per-pair statistics

The framework is designed around the Dobrescu–Mocioiu potential classification (V1–V16) and covers lepton-lepton, lepton-nucleon, and nucleon-nucleon fermion sectors.

---

## Physics Background

### Potentials

Spin-dependent exotic interactions between fermions are parameterised through a set of non-relativistic potentials V_n derived from the most general Lorentz-invariant interaction Lagrangian. Each potential has a distinct spin-velocity structure and couples to specific combinations of scalar (g_S), pseudoscalar (g_P), vector (g_V), and axial-vector (g_A) couplings.

| Potential | Type | Coupling | Description |
|-----------|------|----------|-------------|
| V1 | Monopole-monopole | g_S g_S | Yukawa scalar |
| V2 | Spin-spin | g_A g_A | Axial-axial |
| V3 | Dipole-dipole | g_P g_P | Pseudoscalar |
| V4+5 | Spin-velocity | g_A g_V | Axial-vector |
| V8 | Monopole-dipole | g_S g_P | Scalar-pseudoscalar |
| V9+10 | Spin-orbit | g_P g_S | Pseudoscalar-scalar |
| V11 | Quadratic spin-velocity | g_A g_V | Transverse spin coupling |

### Asymmetry Parameter

For each pair of matter (m) and antimatter (ā) datasets, the asymmetry is defined pointwise across the shared λ range:

```
A_α(λ) = [g_m(λ) − g_ā(λ)] / [g_m(λ) + g_ā(λ)]
```

- **A_α → +1**: matter constraint is much weaker (less constrained)
- **A_α → −1**: antimatter constraint is much weaker
- **A_α ≈ 0**: matter and antimatter bounds are consistent — CPT symmetry respected within experimental sensitivity

### Fermion Sectors

| Canonical label | Physical system | Matter | Antimatter partner |
|-----------------|-----------------|--------|--------------------|
| `ee` | Electron-electron | ✓ | `eebar` (e⁻e⁺) |
| `emu` | Electron-muon | ✓ | `emubar` (e-μ̄) |
| `ep` | Electron-proton | ✓ | `epbar` (e-p̄) |
| `en` | Electron-neutron | ✓ | `enbar` |
| `np` | Neutron-proton | ✓ | `npbar` |
| `nn` | Neutron-neutron | ✓ | `nnbar` (n-n̄) |
| `pp` | Proton-proton | ✓ | `ppbar` (p-p̄) |
| `eN` | Electron-nucleus | ✓ | `eNbar` |
| `mumu` | Muon-muon | ✓ | `mumubar` (μ-μ̄) |

---

## Installation

### Prerequisites

- Python 3.9+
- Linux, macOS, or Windows WSL
- Node.js (LTS, from [nodejs.org](https://nodejs.org)) — only needed for `spin start` (the web interface)

### Option 1 — One-line install (recommended)

```bash
git clone https://github.com/oyewodayo/spindep_framework.git
cd spindep_framework
python3 install.py
```

The install script will:

1. Check your Python version (3.9+ required)
2. Create a virtual environment (optional but recommended)
3. Install all dependencies (numpy, scipy, pandas, matplotlib, reportlab, Pillow)
4. Register the `spin` command globally so you can use it from any folder
5. Verify the installation with `spin info`

> **TIP:** After install, open a new terminal tab and type `spin --help` to confirm it works.

### Option 2 — Manual install via pip

```bash
cd spindep_framework
pip install -e .                  # installs 'spin' command
pip install -e '.[full]'          # also installs pyyaml + seaborn
```

### Option 3 — Without installing (run directly)

```bash
export SPINDEP_HOME=/path/to/spindep_framework/spindep
python3 spindep/cli.py run --data ./datasets
```

### Verify the installation

```bash
spin info
spin info --data ./datasets       # also shows dataset summary
```

---

## Quick Start

**New to SPINDEP or not a terminal person?** Just run:

```bash
spin start
```

This launches the backend and the web interface together and opens it in your
browser — no other commands needed. Press `Ctrl+C` in the terminal to stop it.

For terminal / scripted use:

```bash
# Full analysis on your dataset folder
spin run --data ./datasets

# Quick CPT test on two CSV files — no folder structure needed
spin test matter.csv antimatter.csv --plot

# Check your datasets before a full run
spin validate --data ./datasets

# Import CSV files from anywhere and run immediately
spin import --from ~/Downloads/new_data \
            --coupling gAgA --potential V2 \
            --sector-matter ee --sector-antimatter eebar \
            --run
```

---

## Usage — Terminal Commands

The `spin` command covers the entire framework through simple sub-commands. All commands print coloured progress output and clear error messages.

### `spin start` — Web GUI (recommended for most researchers)

```
spin start [--no-browser]
```

Starts the backend API (port 8001) and the web interface (port 5173) together,
waits for both to come up, and opens the interface in your default browser.
The first run installs the web interface's dependencies automatically (one-time,
about a minute); after that it starts in a couple of seconds.

```bash
spin start                # start everything and open a browser tab
spin start --no-browser   # start everything but don't open a browser
```

Stop both servers with `Ctrl+C` in the terminal where `spin start` is running.

---

### `spin run` — Full pipeline

```
spin run --data DIR [--output DIR]
```

Runs the complete analysis: dataset discovery → unit audit → gap analysis → constraint atlas → pair matching → asymmetry computation → PDF report.

```bash
spin run --data ./datasets
spin run --data ./datasets --output ./my_results
```

**Outputs created:**

- `results/reports/asymmetry_report_TIMESTAMP.pdf`
- `results/figures/gap_analysis/*.png` (3 figures)
- `results/figures/constraint_atlas/*.png` (one per potential + combined atlas)
- `results/tables/asymmetry_summary.csv`
- `results/tables/dataset_registry.csv`

---

### `spin test` — Quick CPT test

```
spin test MATTER.CSV ANTIMATTER.CSV [--plot FILE] [--save FILE] [--points N]
```

The most direct entry point for external researchers. Pass any two CSV files — no folder structure required.

```bash
# Minimal: just print results
spin test electron_bounds.csv positron_bounds.csv

# Save a plot
spin test matter.csv antimatter.csv --plot

# Save plot to a specific file
spin test matter.csv antimatter.csv --plot cpt_result.png

# Save full results table as CSV
spin test matter.csv antimatter.csv --save results.csv

# All options combined
spin test matter.csv antimatter.csv --plot test.png --save out.csv --points 300
```

**Example output:**

```
  ──────────────────────────────────────────────────────────────
  SPINDEP  ·  Quick CPT Test
  ──────────────────────────────────────────────────────────────

  ●  Matter:      2Kotler_2015_m_abs_ee
  ●  Antimatter:  3Fadeev_2022_2_m_abs_ebare

  CPT Asymmetry Results
  ─────────────────────────
    Lambda overlap:        1.75e-07 → 1.63e-05 m
    Valid points:          300 / 300

    Mean |A_alpha|:        1.0000  Strong CPT-sensitive asymmetry

    chi2 (uniform 10%):   119989.9   dof=300
    chi2 (weighted):      33391.2    dof=300
    p-value (weighted):   0.000e+00  *** highly significant
```

---

### `spin validate` — Pre-flight check

```
spin validate --data DIR [--verbose]
```

Run this before `spin run` to check datasets for issues. Reports unknown sectors, unit problems, and shows exactly which pairs will be matched.

```bash
spin validate --data ./datasets
spin validate --data ./datasets --verbose    # shows all unrecognised files
```

---

### `spin import` — Bring in data from anywhere

```
spin import --from DIR --coupling NAME --potential Vi \
            --sector-matter S --sector-antimatter S [options]
```

Copy CSV files from any folder into the correct SPINDEP structure. Files are automatically renamed to follow the naming convention if needed.

```bash
# Import and run immediately
spin import --from ~/Downloads/new_constraints  \
            --coupling gAgA --potential V2      \
            --sector-matter ee                  \
            --sector-antimatter eebar           \
            --run

# Import to a custom destination
spin import --from /data --dest ./myproject/datasets/normalized \
            --coupling gsgs --potential V1                       \
            --sector-matter nn --sector-antimatter nnbar
```

> **TIP:** The `--run` flag lets you go from raw CSV files to a full PDF report in one command.

---

### `spin gaps` and `spin atlas` — Figures only

```bash
# Gap analysis figures only
spin gaps  --data ./datasets
spin gaps  --data ./datasets --output ./my_figures

# Constraint atlas only
spin atlas --data ./datasets
spin atlas --data ./datasets --output ./thesis_figures
```

---

### `spin info` — Status check

```bash
spin info                           # framework status + dependency versions
spin info --data ./datasets         # also shows dataset and pair counts
```

---

### Getting help

```bash
spin --help                # all commands
spin run --help            # help for a specific command
spin import --help         # most options
```

---

## Usage — Config Files

Config files let you store all parameters in a YAML or JSON file and run with a single command. Ideal for reproducible analyses and sharing with collaborators.

### Run config

```yaml
# myrun.yaml
command: run
data:    ./datasets
output:  ./results
```

```bash
spin config myrun.yaml
```

### CPT test config

```yaml
# mytest.yaml
command:    test
matter:     ./data/electron_torsion.csv
antimatter: ./data/positronium_bounds.csv
plot:       ./results/cpt_comparison.png
save:       ./results/cpt_table.csv
points:     300
```

### Import config

```yaml
# import_fadeev2024.yaml
command:           import
from:              /data/Fadeev2024
dest:              ./datasets/normalized
coupling:          gAgA
potential:         V2
sector_matter:     ee
sector_antimatter: eebar
interaction_class: lepton-lepton
run:               true
```

### JSON format

All config files also work as JSON:

```json
{
  "command": "test",
  "matter":     "electron_bounds.csv",
  "antimatter": "positron_bounds.csv",
  "plot":       "result.png",
  "points":     300
}
```

> **NOTE:** YAML requires PyYAML: `pip install pyyaml` (included in `pip install -e '.[full]'`)

---

## Usage — Batch Processing

Run multiple independent analyses from a single jobs file. Failed jobs are reported but do not stop remaining jobs.

```yaml
# jobs.yaml

- name: "gAgA V2 electron sector"
  command: run
  data: ./datasets/gAgA_V2
  output: ./results/gAgA_V2

- name: "Quick test — positronium vs torsion balance"
  command: test
  matter: ./data/torsion_ee.csv
  antimatter: ./data/positronium_eebar.csv
  plot: ./results/torsion_vs_positronium.png
  save: ./results/torsion_vs_positronium.csv

- name: "Import new Fadeev 2024 data and run"
  command: import
  from: /downloads/Fadeev2024_constraints
  dest: ./datasets/normalized
  coupling: gAgA
  potential: V2
  sector_matter: ee
  sector_antimatter: eebar
  interaction_class: lepton-lepton
  run: true

- name: "Gap analysis for full dataset"
  command: run
  data: ./datasets
  output: ./results/full_run
```

```bash
spin batch jobs.yaml
```

---

## Usage — Python API

All modules are importable directly for use in notebooks or custom scripts.

### Quick test

```python
from spindep.src.parser          import load_dataset
from spindep.src.unit_conversion import convert_lambda_to_metres
from spindep.src.statistics      import chi_squared_from_datasets

df_m = load_dataset('matter.csv')
df_a = load_dataset('antimatter.csv')

df_m, _, unit = convert_lambda_to_metres(df_m, 'matter', verbose=True)
df_a, _, unit = convert_lambda_to_metres(df_a, 'antimatter', verbose=True)

result = chi_squared_from_datasets(df_m, df_a)
print(f'|A_alpha|     = {result["mean_abs_A"]:.4f}')
print(f'chi2 weighted = {result["chi2_weighted"]:.1f}')
print(f'p-value       = {result["pval_weighted"]:.3e}')
```

### Full pipeline

```python
from spindep.src.pipeline import run_pipeline

run_pipeline(
    dataset_root='./datasets/normalized',
    results_root='./results'
)
```

### Available modules

| Module | Import | Key function |
|--------|--------|-------------|
| Parser | `from spindep.src.parser import discover_datasets` | `discover_datasets(root)` |
| Matcher | `from spindep.src.matcher import build_pairs` | `build_pairs(datasets)` |
| Asymmetry | `from spindep.src.asymmetry import compute_asymmetry` | `compute_asymmetry(df_m, df_a)` |
| Statistics | `from spindep.src.statistics import chi_squared_from_datasets` | `chi_squared_from_datasets(df_m, df_a)` |
| Unit conversion | `from spindep.src.unit_conversion import convert_lambda_to_metres` | `convert_lambda_to_metres(df, filename)` |
| Gap analysis | `from spindep.src.gap_analysis import run_gap_analysis` | `run_gap_analysis(datasets, figures_dir)` |
| Constraint plots | `from spindep.src.constraint_plots import run_constraint_plots` | `run_constraint_plots(datasets, ...)` |

---

## Dataset File Naming Convention

All CSV files must follow a strict naming convention for the parser to correctly classify them:

```
{V}{Author}{Year}_{m}_{abs}_{sector}.csv
```

| Token | Meaning | Examples |
|-------|---------|---------|
| `{V}` | Potential number prefix | `2`, `3`, `45`, `1a` |
| `{Author}` | First author surname | `Fadeev`, `Karshenboim`, `Hunter` |
| `{Year}` | Publication year (4 digits) | `2022`, `2013` |
| `m` | Matter-sector flag | always `m` |
| `abs` | Absolute value flag | always `abs` |
| `{sector}` | Fermion sector | `ee`, `ebare`, `ep`, `epbar`, `en`, `nn` |

### Antimatter sector aliases recognised

| Filename token | Canonical sector |
|---------------|-----------------|
| `ebare` | `eebar` |
| `ebarpabr` | `epbar` |
| `emubare` | `emubar` |
| `ebar` | `eebar` |
| `epbare` | `epbar` |
| `nnbare` | `nnbar` |

### Directory structure

```
datasets/normalized/{coupling}/{interaction_class}/{filename}.csv
```

Example:
```
datasets/normalized/gAgA/lepton-lepton/2Fadeev_2022_4_m_abs_ee.csv
```

### CSV format

Two columns, no header. Lambda in metres by default:

```
1.754e-07,1.23e-11
2.100e-07,9.87e-12
3.500e-07,7.43e-12
```

| Column | Unit | Description |
|--------|------|-------------|
| `lambda_m` | metres | Interaction range λ |
| `coupling_abs` | dimensionless | Upper bound on \|coupling constant\| |

Both columns must be strictly positive. Rows with non-numeric or non-positive values are silently dropped.

---

## Data Preparation Reference

### Lambda unit tokens

| Filename token | Unit | Conversion to metres |
|----------------|------|---------------------|
| `_m_` (default) | metres | 1.0 (no conversion) |
| `_millionev_` | MeV⁻¹ | × 1.9733e-13 |
| `_ev_` | eV⁻¹ | × 1.9733e-7 |
| `_cm_` | centimetres | × 1e-2 |
| `_nm_` | nanometres | × 1e-9 |
| `_fm_` | femtometres | × 1e-15 |

### Supported coupling types

| Coupling | Potential | Description |
|----------|-----------|-------------|
| `gAgA` | V2, V3 | Axial-axial (spin-spin) |
| `gsgs` | V1, UNKNOWN | Scalar-scalar (monopole-monopole) |
| `gVgV` | V1, V2, V3 | Vector-vector |
| `gpgp` | V3 | Pseudoscalar-pseudoscalar (dipole-dipole) |
| `gpgs` | V1, V2, V9+10 | Monopole-dipole |
| `gAgV` | V11, V12+13 | Axial-vector |
| `lepton-nucleon` | V1, V2, V3 | Lepton-nucleon cross-coupling |

---

## Complete Command Reference

| Command | Flags | Description |
|---------|-------|-------------|
| `spin start` | `[--no-browser]` | Launch backend + web GUI together |
| `spin run` | `--data DIR  [--output DIR]` | Full pipeline |
| `spin test` | `MATTER.CSV ANTI.CSV  [--plot FILE]  [--save FILE]  [--points N]` | Quick CPT test on two files |
| `spin validate` | `--data DIR  [--verbose]` | Pre-flight checks |
| `spin import` | `--from DIR  --coupling NAME  --potential Vi  --sector-matter S  --sector-antimatter S  [--interaction-class C]  [--dest DIR]  [--run]` | Import from any folder |
| `spin gaps` | `--data DIR  [--output DIR]` | Gap figures only |
| `spin atlas` | `--data DIR  [--output DIR]` | Constraint atlas only |
| `spin config` | `CONFIG.yaml` | Run from config file |
| `spin batch` | `JOBS.yaml` | Run multiple jobs |
| `spin info` | `[--data DIR]` | Status and dependency info |
| `spin --help` | | List all commands |
| `spin CMD --help` | | Help for specific command |

---

## Output Files

| File | Description |
|------|-------------|
| `results/tables/dataset_registry.csv` | Full metadata for every discovered dataset |
| `results/tables/asymmetry_summary.csv` | Per-pair: χ², dof, p-value, mean \|A_α\|, λ range |
| `results/plots/{coupling}_{potential}_{sector}.png` | Constraint comparison + asymmetry plot |
| `results/reports/asymmetry_report.pdf` | Full PDF report (cover, summary table, per-pair sections) |

---

## Module Reference

### `parser.py`

Responsible for discovering CSV files and extracting structured metadata from filenames and directory paths.

**Key functions:**

```python
discover_datasets(root: str | Path) -> list[ConstraintDataset]
parse_dataset(filepath: str | Path) -> ConstraintDataset | None
load_dataset(filepath: str | Path) -> pd.DataFrame
```

**ConstraintDataset fields:**

| Field | Type | Description |
|-------|------|-------------|
| `filepath` | Path | Absolute path to CSV |
| `filename` | str | Stem (no extension) |
| `coupling` | str | Coupling family (from directory) |
| `interaction_class` | str | Fermion class (from directory) |
| `potential` | str | e.g. `V2`, `V4+5` |
| `source` | str | e.g. `Fadeev2022` |
| `sector` | str | Canonical sector label |
| `contains_antimatter` | bool | True for antimatter sectors |
| `label` | str | Human-readable legend label |

---

### `matcher.py`

```python
build_pairs(datasets: list[ConstraintDataset]) -> list[tuple]
```

Returns `(matter_ds, antimatter_ds)` tuples. Two datasets pair when they share the same `coupling`, `potential`, `interaction_class`, and have physically conjugate sectors.

---

### `interpolation.py`

```python
make_log_interpolator(df: pd.DataFrame) -> Callable
```

Constructs a log-log linear interpolator. Returns `f(lam) -> g`, extrapolating as `nan` outside the data range.

---

### `asymmetry.py`

```python
compute_asymmetry(
    df_m: pd.DataFrame,
    df_a: pd.DataFrame,
    n_points: int = 300
) -> tuple[np.ndarray, np.ndarray, tuple] | tuple[None, None, None]
```

Returns `(lam_grid, A, (g_m, g_a))` or `(None, None, None)` if no overlapping λ range exists.

---

### `statistics.py`

```python
chi_squared_sensitivity(
    g_m: np.ndarray,
    g_a: np.ndarray,
    sigma_frac: float = 0.1
) -> tuple[float, int, float]
```

Returns `(chi2_total, dof, p_value)`.

---

### `plotting.py`

```python
plot_asymmetry(lam, A, g_m, g_a, matter_ds, antimatter_ds, output_path)
```

Two-panel plot: log-log coupling bounds (top) and asymmetry parameter A_α (bottom).

---

### `reporting.py`

```python
generate_report(
    summary_rows: list[dict],
    plots_dir: str | Path,
    output_path: str | Path
) -> Path
```

Generates a structured PDF report with cover page, summary table, and one section per pair.

---

## Interpreting Results

### `asymmetry_summary.csv` columns

| Column | Description |
|--------|-------------|
| `coupling` | Coupling family (e.g. `gAgA`) |
| `potential` | Potential label (e.g. `V2`) |
| `interaction_class` | Fermion class (e.g. `lepton-lepton`) |
| `sector` | Matter sector (e.g. `ee`) |
| `matter_source` | Citation key of matter dataset |
| `antimatter_source` | Citation key of antimatter dataset |
| `mean_abs_A` | Mean of \|A_α(λ)\| over the shared range |
| `chi2` | Total χ² statistic |
| `dof` | Degrees of freedom (number of valid λ points) |
| `p_value` | p-value from chi-squared CDF |
| `lambda_min` | Minimum shared interaction range (m) |
| `lambda_max` | Maximum shared interaction range (m) |

### Significance thresholds

| p-value | Interpretation |
|---------|---------------|
| p < 0.001 | *** Strong evidence for asymmetry |
| p < 0.01  | **  Moderate evidence |
| p < 0.05  | *   Marginal evidence |
| p ≥ 0.05  | ns  No significant asymmetry detected |

---

## Extending the Framework

### Adding new sectors

Edit `FERMION_MAP`, `ANTIMATTER_SECTORS`, `SECTOR_EQUIVALENCE`, and `SECTOR_ALIASES` in `parser.py`:

```python
ANTIMATTER_SECTORS.add("taubar")
SECTOR_EQUIVALENCE["tau"] = ["taubar"]
SECTOR_EQUIVALENCE["taubar"] = ["tau"]
SECTOR_ALIASES["taub"] = "taubar"
```

### Adding new potentials

Edit `POTENTIAL_INFO` in `classifier.py`:

```python
POTENTIAL_INFO["V12"] = {
    "type": "tensor-tensor",
    "description": "Tensor-tensor interaction",
    "couplings": ["gTgT"]
}
```

### Handling non-standard filenames

Add an entry to `FILENAME_SECTOR_OVERRIDES` in `parser.py`:

```python
FILENAME_SECTOR_OVERRIDES["MyAuthor_2024"] = ("ep", False)
#                                               ^     ^
#                                              sector  contains_antimatter
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `'spin' command not found` | Run `source ~/.bashrc` or open a new terminal. If still missing: `export PATH=$(python3 -m site --user-base)/bin:$PATH` |
| `'spin' not found on Windows` | Use `python spindep/cli.py run --data ./datasets` or add `Scripts/` to PATH |
| `ModuleNotFoundError: No module named 'spindep'` | Run from `spindep_framework/`, or set `export SPINDEP_HOME=/path/to/spindep_framework/spindep` |
| `[SKIP] No overlapping lambda range` | Physical gap — not a bug. Run `spin validate` to inspect lambda ranges |
| `[WARN] Unrecognized sector 'UNKNOWN'` | Filename sector token not recognised. Check naming convention and add alias if needed |
| Found N datasets but 0 valid pairs | Sector misclassification — inspect parsed sectors via `spin validate --verbose` |
| Unit conversion gives wrong results | If file is pre-converted, add filename to `ALREADY_CONVERTED` in `src/unit_conversion.py` |
| Empty pages in PDF report | Replace `reporting.py` with the latest version |
| `pip install` fails | Try `pip install --user -e .` or `pip install --break-system-packages -e .` |
| `PyYAML not found` when using `spin config` | Run `pip install pyyaml` (or `pip install -e '.[full]'`) |

---

## File Structure

```
spindep_framework/
├── install.py                    # One-line installer
├── setup.py                      # pip install config (registers 'spin')
├── README.md                     # This file
├── spin_run.yaml                 # Example config files
├── spin_batch_jobs.yaml          # Example batch file
└── spindep/                      # Main package
    ├── __init__.py
    ├── cli.py                    # 'spin' command entry point
    ├── main.py                   # Direct Python entry point
    ├── datasets/
    │   └── normalized/           # All CSV datasets
    │       ├── gAgA/
    │       │   └── lepton-lepton/
    │       ├── gsgs/
    │       ├── gVgV/
    │       └── gpgp/
    ├── results/                  # Auto-generated
    │   ├── reports/              # PDF reports
    │   ├── plots/                # Per-pair asymmetry plots
    │   ├── figures/              # Atlas + gap analysis
    │   └── tables/               # CSV summaries
    └── src/
        ├── parser.py             # Dataset discovery & classification
        ├── matcher.py            # Matter-antimatter pairing
        ├── asymmetry.py          # A_alpha computation
        ├── statistics.py         # Chi-squared (uniform + weighted)
        ├── interpolation.py      # Log-linear interpolation
        ├── unit_conversion.py    # Lambda unit standardisation
        ├── gap_analysis.py       # Gap analysis figures
        ├── constraint_plots.py   # Constraint atlas plots
        ├── plotting.py           # Per-pair asymmetry plots
        ├── reporting.py          # PDF report generation
        └── pipeline.py           # Full pipeline orchestration
```

---

## Citation

If you use this framework in published work, please cite the relevant experimental constraint papers listed in `dataset_registry.csv` alongside this repository.

---

## License

Academic use. Contact the author for redistribution rights.

---

*SPINDEP v1.0 · University of Ibadan · oyewodayo@gmail.com · 2026*