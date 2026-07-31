# SPINDEP

**Spin-Dependent Exotic Interaction Analysis Framework**

A Python pipeline I built for my M.Sc. project to compare matter and antimatter coupling-constant bounds for spin-dependent exotic interactions, and check whether the two sides are consistent with CPT symmetry.

## What it does

Given a folder of matter and antimatter constraint datasets, SPINDEP:

1. discovers and classifies the CSV files from a structured directory tree,
2. matches each matter dataset to its antimatter conjugate,
3. interpolates both constraint curves onto a common log-spaced λ grid,
4. computes the asymmetry parameter A_α = (g_matter − g_antimatter) / (g_matter + g_antimatter),
5. runs a χ² test to check whether any observed asymmetry is statistically significant, and
6. writes out comparison plots plus a PDF report with per-pair statistics.

It's built around the Dobrescu–Mocioiu potential classification (V1–V16) and covers lepton-lepton, lepton-nucleon, and nucleon-nucleon sectors — see [about_project.md](about_project.md) for the physics motivation.

## Physics background

### Potentials

Spin-dependent exotic interactions are parameterised by a set of non-relativistic potentials V_n, each with a distinct spin-velocity structure and a distinct combination of scalar (g_S), pseudoscalar (g_P), vector (g_V), and axial-vector (g_A) couplings.

| Potential | Type | Coupling | Description |
|-----------|------|----------|-------------|
| V1 | Monopole-monopole | g_S g_S | Yukawa scalar |
| V2 | Spin-spin | g_A g_A | Axial-axial |
| V3 | Dipole-dipole | g_P g_P | Pseudoscalar |
| V4+5 | Spin-velocity | g_A g_V | Axial-vector |
| V8 | Monopole-dipole | g_S g_P | Scalar-pseudoscalar |
| V9+10 | Spin-orbit | g_P g_S | Pseudoscalar-scalar |
| V11 | Quadratic spin-velocity | g_A g_V | Transverse spin coupling |

### Asymmetry parameter

For a matched matter (m) / antimatter (ā) pair, the asymmetry is computed pointwise across the shared λ range:

```
A_α(λ) = [g_m(λ) − g_ā(λ)] / [g_m(λ) + g_ā(λ)]
```

- A_α → +1: matter constraint is much weaker
- A_α → −1: antimatter constraint is much weaker
- A_α ≈ 0: matter and antimatter bounds agree — consistent with CPT symmetry given current sensitivity

(Note: an A_α near ±1 by itself doesn't prove CPT violation — it's equally explained by one side just having a looser bound. See the caveat in `spindep/README.md` and Chapter 3 of the thesis.)

### Fermion sectors

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

## Installation

Needs Python 3.9+, and Node.js if you want the web GUI (`spin start`).

Easiest way:

```bash
git clone https://github.com/oyewodayo/spindep_framework.git
cd spindep_framework
bash install.sh
```

This checks your Python version, optionally sets up a virtualenv, installs the dependencies (numpy, scipy, pandas, matplotlib, reportlab, Pillow), and registers the `spin` command globally. Open a new terminal afterwards and run `spin --help` to confirm it worked.

If you'd rather install manually:

```bash
cd spindep_framework
pip install -e .                  # installs 'spin' command
pip install -e '.[full]'          # also installs pyyaml + seaborn
```

Or skip installing entirely and run it in place:

```bash
export SPINDEP_HOME=/path/to/spindep_framework/spindep
python3 spindep/cli.py run --data ./datasets
```

Check everything's working with `spin info` (add `--data ./datasets` to also see a dataset summary).

## Quick start

Not a terminal person, or just want to poke around? Run `spin start` — it launches the backend and the web GUI together and opens your browser. `Ctrl+C` stops both.

For the command line:

```bash
# Full analysis on a dataset folder
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

## Terminal commands

All `spin` sub-commands print coloured progress output and, where possible, tell you plainly what went wrong.

### `spin start` — web GUI

```
spin start [--no-browser]
```

Starts the backend API (port 8001) and the web interface (port 5173) together and opens a browser tab. The first run installs the GUI's npm dependencies (about a minute); after that it's a couple of seconds. `Ctrl+C` stops both servers.

### `spin run` — full pipeline

```
spin run --data DIR [--output DIR]
```

Runs dataset discovery → unit audit → gap analysis → constraint atlas → pair matching → asymmetry computation → PDF report, in one go.

Produces:
- `results/reports/asymmetry_report_TIMESTAMP.pdf`
- `results/figures/gap_analysis/*.png` (3 figures)
- `results/figures/constraint_atlas/*.png` (one per potential + a combined atlas)
- `results/tables/asymmetry_summary.csv`
- `results/tables/dataset_registry.csv`

### `spin test` — quick CPT test

```
spin test MATTER.CSV ANTIMATTER.CSV [--plot FILE] [--save FILE] [--points N]
```

The fastest way in if you just have two CSVs and don't want to set up the folder structure:

```bash
spin test electron_bounds.csv positron_bounds.csv
spin test matter.csv antimatter.csv --plot                  # save a plot
spin test matter.csv antimatter.csv --save results.csv      # save the results table
```

Example output:

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

### `spin validate` — pre-flight check

```
spin validate --data DIR [--verbose]
```

Run before `spin run` to catch problems early — unknown sectors, unit issues, and exactly which pairs will be matched. `--verbose` also lists unrecognised files.

### `spin import` — bring in data from anywhere

```
spin import --from DIR --coupling NAME --potential Vi \
            --sector-matter S --sector-antimatter S [options]
```

Copies CSVs from any folder into the correct SPINDEP structure, renaming them to match the naming convention if needed. Add `--run` to go straight from raw CSVs to a full PDF report in one command.

```bash
spin import --from ~/Downloads/new_constraints  \
            --coupling gAgA --potential V2      \
            --sector-matter ee                  \
            --sector-antimatter eebar           \
            --run
```

### `spin gaps` / `spin atlas` — figures only

```bash
spin gaps  --data ./datasets --output ./my_figures    # gap analysis figures only
spin atlas --data ./datasets --output ./thesis_figures # constraint atlas only
```

### `spin info` — status check

```bash
spin info                     # framework status + dependency versions
spin info --data ./datasets   # also shows dataset and pair counts
```

### Help

```bash
spin --help
spin run --help
spin import --help
```

## Config files

For reproducible runs, put the parameters in a YAML or JSON file instead of typing them out each time.

```yaml
# myrun.yaml
command: run
data:    ./datasets
output:  ./results
```

```bash
spin config myrun.yaml
```

Works the same way for `test` and `import`:

```yaml
# mytest.yaml
command:    test
matter:     ./data/electron_torsion.csv
antimatter: ./data/positronium_bounds.csv
plot:       ./results/cpt_comparison.png
save:       ./results/cpt_table.csv
points:     300
```

JSON works too, if you prefer it — same keys. (YAML needs `pip install pyyaml`, included in `pip install -e '.[full]'`.)

## Batch processing

For running several independent analyses from one file — failed jobs get reported but don't stop the rest:

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
```

```bash
spin batch jobs.yaml
```

## Python API

Everything is importable directly, for notebooks or custom scripts:

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

Or run the whole pipeline in one call:

```python
from spindep.src.pipeline import run_pipeline

run_pipeline(
    dataset_root='./datasets/normalized',
    results_root='./results'
)
```

| Module | Import | Key function |
|--------|--------|-------------|
| Parser | `from spindep.src.parser import discover_datasets` | `discover_datasets(root)` |
| Matcher | `from spindep.src.matcher import build_pairs` | `build_pairs(datasets)` |
| Asymmetry | `from spindep.src.asymmetry import compute_asymmetry` | `compute_asymmetry(df_m, df_a)` |
| Statistics | `from spindep.src.statistics import chi_squared_from_datasets` | `chi_squared_from_datasets(df_m, df_a)` |
| Unit conversion | `from spindep.src.unit_conversion import convert_lambda_to_metres` | `convert_lambda_to_metres(df, filename)` |
| Gap analysis | `from spindep.src.gap_analysis import run_gap_analysis` | `run_gap_analysis(datasets, figures_dir)` |
| Constraint plots | `from spindep.src.constraint_plots import run_constraint_plots` | `run_constraint_plots(datasets, ...)` |

## Dataset file naming convention

CSV files need to follow this pattern for the parser to classify them correctly:

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

Antimatter sector aliases the parser knows about:

| Filename token | Canonical sector |
|---------------|-----------------|
| `ebare` | `eebar` |
| `ebarpabr` | `epbar` |
| `emubare` | `emubar` |
| `ebar` | `eebar` |
| `epbare` | `epbar` |
| `nnbare` | `nnbar` |

Directory layout: `datasets/normalized/{coupling}/{interaction_class}/{filename}.csv`, e.g. `datasets/normalized/gAgA/lepton-lepton/2Fadeev_2022_4_m_abs_ee.csv`.

CSV format is two columns, no header, lambda in metres by default:

```
1.754e-07,1.23e-11
2.100e-07,9.87e-12
3.500e-07,7.43e-12
```

| Column | Unit | Description |
|--------|------|-------------|
| `lambda_m` | metres | Interaction range λ |
| `coupling_abs` | dimensionless | Upper bound on \|coupling constant\| |

Both columns must be strictly positive — rows that aren't get silently dropped.

## Data preparation reference

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

## Complete command reference

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

## Output files

| File | Description |
|------|-------------|
| `results/tables/dataset_registry.csv` | Full metadata for every discovered dataset |
| `results/tables/asymmetry_summary.csv` | Per-pair: χ², dof, p-value, mean \|A_α\|, λ range |
| `results/plots/{coupling}_{potential}_{sector}.png` | Constraint comparison + asymmetry plot |
| `results/reports/asymmetry_report.pdf` | Full PDF report (cover, summary table, per-pair sections) |

## Module reference

- **`parser.py`** — discovers CSV files and extracts metadata from filenames/paths. Key functions: `discover_datasets(root)`, `parse_dataset(filepath)`, `load_dataset(filepath)`. Returns `ConstraintDataset` objects with fields `filepath`, `filename`, `coupling`, `interaction_class`, `potential`, `source`, `sector`, `contains_antimatter`, `label`.
- **`matcher.py`** — `build_pairs(datasets)` returns `(matter_ds, antimatter_ds)` tuples for any two datasets sharing `coupling`, `potential`, `interaction_class`, and a physically conjugate sector pair.
- **`interpolation.py`** — `make_log_interpolator(df)` builds a log-log linear interpolator; extrapolates as `nan` outside the data range.
- **`asymmetry.py`** — `compute_asymmetry(df_m, df_a, n_points=300)` returns `(lam_grid, A, (g_m, g_a))`, or `(None, None, None)` if the λ ranges don't overlap.
- **`statistics.py`** — `chi_squared_sensitivity(g_m, g_a, sigma_frac=0.1)` returns `(chi2_total, dof, p_value)`.
- **`plotting.py`** — `plot_asymmetry(lam, A, g_m, g_a, matter_ds, antimatter_ds, output_path)` draws a two-panel plot: log-log coupling bounds on top, A_α below.
- **`reporting.py`** — `generate_report(summary_rows, plots_dir, output_path)` builds the PDF report (cover page, summary table, one section per pair).

## Interpreting results

`asymmetry_summary.csv` columns:

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
| `lambda_min` / `lambda_max` | Shared interaction range (m) |

Significance thresholds: p < 0.001 (\*\*\*, strong), p < 0.01 (\*\*, moderate), p < 0.05 (\*, marginal), p ≥ 0.05 (ns, not significant).

## Extending the framework

**New sectors** — edit `FERMION_MAP`, `ANTIMATTER_SECTORS`, `SECTOR_EQUIVALENCE`, `SECTOR_ALIASES` in `parser.py`:

```python
ANTIMATTER_SECTORS.add("taubar")
SECTOR_EQUIVALENCE["tau"] = ["taubar"]
SECTOR_EQUIVALENCE["taubar"] = ["tau"]
SECTOR_ALIASES["taub"] = "taubar"
```

**New potentials** — edit `POTENTIAL_INFO` in `classifier.py`:

```python
POTENTIAL_INFO["V12"] = {
    "type": "tensor-tensor",
    "description": "Tensor-tensor interaction",
    "couplings": ["gTgT"]
}
```

**Non-standard filenames** — add an entry to `FILENAME_SECTOR_OVERRIDES` in `parser.py`:

```python
FILENAME_SECTOR_OVERRIDES["MyAuthor_2024"] = ("ep", False)
#                                               ^     ^
#                                              sector  contains_antimatter
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `'spin' command not found` | Run `source ~/.bashrc` or open a new terminal. Still missing: `export PATH=$(python3 -m site --user-base)/bin:$PATH` |
| `'spin' not found on Windows` | Use `python spindep/cli.py run --data ./datasets` or add `Scripts/` to PATH |
| `ModuleNotFoundError: No module named 'spindep'` | Run from `spindep_framework/`, or set `export SPINDEP_HOME=/path/to/spindep_framework/spindep` |
| `[SKIP] No overlapping lambda range` | Physical gap, not a bug — run `spin validate` to inspect lambda ranges |
| `[WARN] Unrecognized sector 'UNKNOWN'` | Filename sector token not recognised — check naming convention, add an alias if needed |
| Found N datasets but 0 valid pairs | Sector misclassification — inspect with `spin validate --verbose` |
| Unit conversion gives wrong results | If the file's already converted, add its filename to `ALREADY_CONVERTED` in `src/unit_conversion.py` |
| Empty pages in PDF report | Replace `reporting.py` with the latest version |
| `pip install` fails | Try `pip install --user -e .` or `pip install --break-system-packages -e .` |
| `PyYAML not found` when using `spin config` | `pip install pyyaml` (or `pip install -e '.[full]'`) |

## File structure

```
spindep_framework/
├── install.sh                    # One-line installer
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

## Citation

If you use this framework, please cite the relevant experimental constraint papers listed in `dataset_registry.csv` alongside this repository.

## License

Academic use. Contact the author for redistribution rights.

---
*SPINDEP v1.0 · University of Ibadan · oyewodayo@gmail.com · 2026*
