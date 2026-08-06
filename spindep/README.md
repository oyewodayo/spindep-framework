# SPINDEP Framework User Guide

**Spin-Dependent Exotic Interaction Constraint Analysis Pipeline**  
**Version 1.0 | University of Ibadan | 2026**

---

# 1. What Is SPINDEP?

SPINDEP is a Python analysis pipeline for compiling, standardising, and statistically comparing published experimental constraints on spin-dependent exotic interactions — specifically the Dobrescu-Mocioiu potentials V1 through V16.

Given a collection of CSV constraint datasets (coupling upper bound vs interaction range lambda), SPINDEP:

1. Automatically discovers and classifies all datasets by coupling type, potential, fermion sector, and matter/antimatter identity
2. Pairs matter datasets with their antimatter counterparts
3. Computes the CPT asymmetry parameter:

$$
A_\alpha = \frac{g_{\text{matter}} - g_{\text{antimatter}}}{g_{\text{matter}} + g_{\text{antimatter}}}
$$

across overlapping lambda ranges

4. Performs chi-squared CPT consistency tests with both uniform and per-point weighted uncertainties
5. Generates publication-quality constraint atlas plots, gap analysis figures, and a formatted PDF report

> **TIP:** SPINDEP was developed for the MSc thesis *"Unified Constraint Framework for Exotic Spin-Dependent Interactions: Matter-Antimatter Sector Comparison"* at the University of Ibadan. It is designed to be reusable for any new dataset following the same file naming convention.

---

# 2. System Requirements

| Requirement | Minimum Version | Notes |
|---|---|---|
| Python | 3.9+ | 3.10 or 3.11 recommended |
| numpy | 1.24+ | Array operations |
| scipy | 1.10+ | Chi-squared distribution, interpolation |
| pandas | 2.0+ | CSV loading and registry export |
| matplotlib | 3.7+ | All plot generation |
| reportlab | 4.0+ | PDF report generation |
| Pillow | 9.0+ | Image stitching for gap analysis figures |
| seaborn | 0.12+ | Optional: enhanced plot styling |

> **NOTE:** Pillow is required for `gap_analysis.py` to stitch the lambda coverage figure.

Install with:

```bash
pip install Pillow
```

---

# 3. Installation

## 3.1 Clone and Set Up Environment

```bash
# Clone the repository
git clone https://github.com/YourUsername/spindep_framework.git

cd spindep_framework/spindep

# Create a virtual environment
python3 -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Install dependencies
pip install numpy scipy pandas matplotlib reportlab Pillow
```

---

## 3.2 Verify the Installation

```bash
# From spindep_framework/spindep/
python3 -c "from src.parser import discover_datasets; print('OK')"
```

If you see:

```text
OK
```

the installation is working correctly.

---

## 3.3 Required Directory Structure

```text
spindep_framework/
└── spindep/
    ├── main.py
    ├── datasets/
    │   └── normalized/
    │       ├── gAgA/
    │       │   ├── lepton-lepton/
    │       │   │   ├── 2Kotler_2015_m_abs_ee.csv
    │       │   │   └── 3Fadeev_2022_2_m_abs_ebare.csv
    │       │   └── lepton-nucleon/
    │       ├── gsgs/
    │       ├── gVgV/
    │       └── gpgp/
    ├── results/
    │   ├── plots/
    │   ├── reports/
    │   ├── tables/
    │   └── figures/
    └── src/
        ├── parser.py
        ├── matcher.py
        ├── asymmetry.py
        ├── statistics.py
        ├── interpolation.py
        ├── unit_conversion.py
        ├── gap_analysis.py
        ├── constraint_plots.py
        ├── plotting.py
        ├── reporting.py
        └── pipeline.py
```

---

# 4. Preparing Your Data

## 4.1 CSV Format

Each dataset must be a two-column CSV file with **no header**:

```text
# Column 1: lambda (interaction range)
# Column 2: coupling upper bound

1.754e-07,1.23e-11
2.100e-07,9.87e-12
3.500e-07,7.43e-12
```

> **NOTE:** Do not include column headers in the CSV. The loader expects exactly two numeric columns.

---

## 4.2 File Naming Convention

The filename encodes all metadata.

Convention:

```text
[prefix][Author]_[Year]_[potential]_m_abs_[sector].csv
```

Examples:

```text
2Kotler_2015_m_abs_ee.csv
3Fadeev_2022_2_m_abs_ebare.csv
45Ficek_2017_V4+5_m_abs_ee.csv
3Terrano_2015_m_abs_eN.csv
```

### Potential Extraction Rules

| Pattern | Potential Extracted | Example |
|---|---|---|
| Explicit V-token | V-token value | `2Ficek_2017_V2_m_abs_ee.csv -> V2` |
| Standalone digit after year | `V{digit}` | `3Fadeev_2022_3_m_abs_emu.csv -> V3` |
| Leading digit on author | `V{digit}` | `3Terrano_2015_m_abs_eN.csv -> V3` |

---

## 4.3 Sector Naming

| Filename Token | Canonical Sector | Meaning | Antimatter? |
|---|---|---|---|
| ee | ee | electron-electron | No |
| ebare | eebar | electron-positron | Yes |
| ep | ep | electron-proton | No |
| ebarpabr | epbar | electron-antiproton | Yes |
| emubar | emubar | electron-antimuon | Yes |
| eN | eN | electron-nucleus | No |
| nn | nn | neutron-neutron | No |
| nN | nN | neutron-nucleus | No |
| NN | nn | nucleon-nucleon alias | No |

---

## 4.4 Lambda Units

The pipeline auto-detects lambda units from the filename.

| Filename Token | Unit | Conversion Factor |
|---|---|---|
| `_m_` | metres | 1.0 |
| `_millionev_` | MeV^-1 | 1.9733e-13 |
| `_ev_` | eV^-1 | 1.9733e-7 |
| `_cm_` | centimetres | 1e-2 |
| `_nm_` | nanometres | 1e-9 |
| `_fm_` | femtometres | 1e-15 |

> **NOTE:** If your file is already converted to metres but contains a non-metre token, add it to `ALREADY_CONVERTED` in `src/unit_conversion.py`.

---

## 4.5 Folder Structure

```text
datasets/normalized/
  {coupling}/
    {interaction_class}/
      [optional_subfolder/]
        {filename}.csv
```

Examples of couplings:

```text
gAgA
gsgs
gVgV
gpgp
```

Interaction classes:

```text
lepton-lepton
lepton-nucleon
nucleon-nucleon
```

> **IMPORTANT:** Coupling and interaction class are read from folder names, not filenames.

---

# 5. Running the Pipeline

## 5.1 Full Pipeline Run

```bash
cd spindep_framework/spindep

source .venv/bin/activate

python3 main.py
```

### Pipeline Stages

| Stage | Output |
|---|---|
| Dataset discovery | Dataset count + unit audit |
| Unit audit | Files requiring conversion |
| Registry export | `results/tables/dataset_registry.csv` |
| Gap analysis | Gap analysis figures |
| Constraint atlas | Constraint atlas figures |
| Pair matching | Valid matter-antimatter pairs |
| Analysis loop | Asymmetry + chi-squared + plots |
| Report generation | PDF report |

> **TIP:** Runtime for 273 datasets and 10 valid pairs is approximately 30–60 seconds.

---

## 5.2 Outputs Explained

| File / Folder | Contents |
|---|---|
| `results/reports/asymmetry_report_*.pdf` | Full PDF report |
| `results/tables/asymmetry_summary.csv` | Summary statistics |
| `results/tables/dataset_registry.csv` | Parsed dataset registry |
| `results/plots/*.png` | Asymmetry plots |
| `results/figures/gap_analysis/*.png` | Gap analysis figures |
| `results/figures/constraint_atlas/*.png` | Constraint atlas plots |
| `results/figures/matter_antimatter/*.png` | Valid-pair plots |

---

## 5.3 Interpreting Results

| Quantity | Meaning | Typical Range | CPT Implication |
|---|---|---|---|
| \|Aα\| mean | Average CPT asymmetry | 0–1 | Near 0 = CPT symmetric |
| chi2 (uniform) | Chi-squared with 10% uncertainty | ~100k | High value rejects CPT symmetry |
| chi2 (weighted) | Weighted chi-squared | Lower than uniform | Preferred for publication |
| chi2 ratio | Weighted/uniform ratio | 0.1–1.0 | Lower ratio = smoother curves |
| Mean sigma_matter % | Matter uncertainty | 5–25% | Higher = noisier |
| Mean sigma_antimatter % | Antimatter uncertainty | 5–25% | Relative precision |

> **NOTE:** A displayed p-value of `0.000e+00` means `p < 10^-300`, not exactly zero.

---

# 6. Adding New Datasets

## 6.1 Step-by-Step

1. Obtain the constraint data
2. Save as a two-column CSV with no header
3. Name the file correctly
4. Place it in the correct folder
5. Run `main.py`

> **TIP:** No code changes are required for adding datasets.

---

## 6.2 Adding Antimatter Datasets

Recognised antimatter sector tokens:

```text
ebare
ebar
ebarpabr
emubar
nnbar
ppbar
```

Example:

```text
2Smith_2025_m_abs_ebare.csv
```

---

## 6.3 Handling Non-Standard Units

Examples:

```text
2Smith_2025_millionev_abs_ep.csv
2Smith_2025_fm_abs_ep.csv
```

If already converted:

```python
ALREADY_CONVERTED = {
    '2Smith_2025_millionev_abs_ep',
}
```

---

## 6.4 New Coupling Types

Simply create a new folder:

```text
datasets/normalized/gTgT/lepton-lepton/
```

No code changes are required.

---

# 7. Customisation

## 7.1 Changing Chi-Squared Uncertainty

```python
def chi_squared_sensitivity(g_m, g_a, sigma_frac=0.10):
```

Weighted uncertainty:

```python
def estimate_uncertainty(
    lam,
    g,
    min_frac=0.02,
    max_frac=0.50,
    baseline_frac=0.05
):
```

---

## 7.2 Changing Lambda Grid Resolution

```python
stats = chi_squared_from_datasets(
    df_m,
    df_a,
    n_points=300
)
```

> **NOTE:** Higher `n_points` increases chi-squared proportionally.

---

## 7.3 Running Specific Stages Only

### Gap Analysis Only

```python
import sys
sys.path.insert(0, 'spindep')

from src.parser import discover_datasets
from src.gap_analysis import run_gap_analysis
from pathlib import Path

datasets = discover_datasets(Path('datasets/normalized'))

run_gap_analysis(
    datasets,
    figures_dir='results/figures'
)
```

---

### Constraint Atlas Only

```python
from src.constraint_plots import run_constraint_plots

run_constraint_plots(
    datasets,
    summary_rows=[],
    plots_dir=Path('results/plots'),
    figures_dir=Path('results/figures')
)
```

---

### Analyse a Single Pair

```python
from src.parser import load_dataset
from src.asymmetry import compute_asymmetry
from src.statistics import chi_squared_from_datasets
from src.unit_conversion import convert_lambda_to_metres

df_m = load_dataset('path/to/matter.csv')
df_a = load_dataset('path/to/antimatter.csv')

df_m, _, _ = convert_lambda_to_metres(
    df_m,
    'matter_filename'
)

df_a, _, _ = convert_lambda_to_metres(
    df_a,
    'antimatter_filename'
)

stats = chi_squared_from_datasets(df_m, df_a)

print(stats['chi2_weighted'], stats['mean_abs_A'])
```

---

# 8. Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| Found 0 datasets | Wrong working directory | Run from `spindep_framework/spindep/` |
| Dataset not paired | Metadata mismatch | Check folder placement and filename |
| No overlapping lambda range | Physical scale mismatch | Check lambda overlap |
| Unrecognized sector | Missing alias | Add to `SECTOR_ALIASES` |
| Wrong unit conversion | Pre-converted dataset | Add to `ALREADY_CONVERTED` |
| `ModuleNotFoundError: reportlab` | Missing dependency | `pip install reportlab` |
| `ModuleNotFoundError: PIL` | Missing Pillow | `pip install Pillow` |
| Empty PDF pages | Old reporting.py | Update reporting.py |
| Missing atlas plots | Missing file | Copy `constraint_plots.py` |

---

# 9. Diagnostic Commands

## 9.1 List All Datasets

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, 'spindep')

from src.parser import discover_datasets
from pathlib import Path

datasets = discover_datasets(Path('datasets/normalized'))

print(f'\n{"COUPLING":<15} {"POTENTIAL":<10} {"SECTOR":<12} {"ANTIMATTER":<12} FILE')
print('-' * 70)

for d in sorted(datasets, key=lambda x: (x.coupling, x.potential, x.sector)):
    print(f'{d.coupling:<15} {d.potential:<10} {d.sector:<12} {str(d.contains_antimatter):<12} {d.filename}')
EOF
```

---

## 9.2 Check Why Files Don't Pair

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, 'spindep')

from src.parser import discover_datasets
from src.matcher import are_compatible
from pathlib import Path

datasets = discover_datasets(Path('datasets/normalized'))

m = next(d for d in datasets if 'YourMatterFile' in d.filename)
a = next(d for d in datasets if 'YourAntimatterFile' in d.filename)

print(f'coupling match:     {m.coupling} == {a.coupling}: {m.coupling == a.coupling}')
print(f'potential match:    {m.potential} == {a.potential}: {m.potential == a.potential}')
print(f'class match:        {m.interaction_class} == {a.interaction_class}: {m.interaction_class == a.interaction_class}')
print(f'sector compatible:  {m.sector} <-> {a.sector}')
print(f'antimatter flags:   {m.contains_antimatter} vs {a.contains_antimatter}')
print(f'are_compatible():   {are_compatible(m, a)}')
EOF
```

---

## 9.3 Check Lambda Overlap

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, 'spindep')

from src.parser import discover_datasets, load_dataset
from src.unit_conversion import convert_lambda_to_metres
from pathlib import Path

datasets = discover_datasets(Path('datasets/normalized'))

m = next(d for d in datasets if 'YourMatterFile' in d.filename)
a = next(d for d in datasets if 'YourAntimatterFile' in d.filename)

df_m, _, _ = convert_lambda_to_metres(load_dataset(m.filepath), m.filename, verbose=True)
df_a, _, _ = convert_lambda_to_metres(load_dataset(a.filepath), a.filename, verbose=True)

lmin = max(df_m['lambda_m'].min(), df_a['lambda_m'].min())
lmax = min(df_m['lambda_m'].max(), df_a['lambda_m'].max())

print(f'Matter:     {df_m["lambda_m"].min():.3e} -> {df_m["lambda_m"].max():.3e} m')
print(f'Antimatter: {df_a["lambda_m"].min():.3e} -> {df_a["lambda_m"].max():.3e} m')
print(f'Overlap:    {lmin:.3e} -> {lmax:.3e}  ({"OK" if lmax > lmin else "NO OVERLAP"})')
EOF
```

---

## 9.4 Run Statistics Self-Test

```bash
cd spindep_framework/spindep

python3 src/statistics.py
```

Expected output:

```text
Uniform chi2:  ~300000  (dof=300)  p=0.000e+00
Weighted chi2: ~varies  (dof=300)  p=0.000e+00
Mean |A_alpha|: 0.9802
Self-test complete.
```

---

# 10. Citing This Framework

```bibtex
@mastersthesis{Oyewo2026,
  author  = {Oyewo Temidayo Solomon},
  title   = {Unified Constraint Framework for Exotic Spin-Dependent
             Interactions: Matter-Antimatter Sector Comparison},
  school  = {University of Ibadan},
  year    = {2026},
  note    = {MSc Thesis, Department of Physics}
}
```

Key datasets and references:

1. Fadeev et al. (2022) — antimatter constraints: *Phys. Rev. A*
2. Cong et al. (2025) — comprehensive review: *Rev. Mod. Phys. 97, 025005*
3. Dobrescu & Mocioiu (2006) — potential classification: *JHEP*
4. Kostelecky & Lane (1999) — SME framework: *Phys. Rev. D 60, 116010*

---

**SPINDEP v1.0 | University of Ibadan | oyewodayo@gmail.com | 2026**