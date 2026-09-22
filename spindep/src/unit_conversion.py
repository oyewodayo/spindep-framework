# // unit_conversion.py
"""
Unit conversion utilities for SPINDEP constraint datasets.

Lambda (interaction range) can appear in different units depending
on the experiment and source paper. This module standardises all
lambda values to metres before analysis.

Known unit tokens found in filenames:
  _m_       → metres (default, no conversion needed)
  _millionev_ / _Mev_ / _MeV_ → 10^6 eV^-1 (inverse energy → length)
  _ev_      → eV^-1
  _cm_      → centimetres
  _mm_      → millimetres
  _um_      → micrometres
  _nm_      → nanometres
  _fm_      → femtometres (fermi)
  _ang_     → Angstroms

Physical constants
------------------
  hbar * c = 197.3269804 MeV·fm = 1.97327e-7 eV·m
  So 1 eV^-1 = hbar*c = 1.97327e-7 m
     1 MeV^-1 = 1.97327e-13 m
     1 (million eV)^-1 = 1 MeV^-1 = 1.97327e-13 m
"""

import re
import numpy as np
from pathlib import Path

# ============================================================
# PHYSICAL CONSTANTS
# ============================================================

HBAR_C_EV_M  = 1.9732697e-7    # hbar*c in eV·m  (1 eV^-1 = 1.9733e-7 m)
HBAR_C_MEV_M = 1.9732697e-13   # hbar*c in MeV·m (1 MeV^-1 = 1.9733e-13 m)

# ============================================================
# UNIT TOKEN MAP
# Token found in filename → conversion factor to metres
# ============================================================

UNIT_TOKENS = {
    # Length units
    "_m_":         1.0,           # metres (default)
    "_m_abs":      1.0,           # metres (common suffix pattern)
    "_cm_":        1e-2,          # centimetres
    "_mm_":        1e-3,          # millimetres
    "_um_":        1e-6,          # micrometres
    "_nm_":        1e-9,          # nanometres
    "_fm_":        1e-15,         # femtometres
    "_ang_":       1e-10,         # Angstroms

    # Inverse energy units (via hbar*c)
    "_millionev_": HBAR_C_MEV_M,  # million eV^-1 = MeV^-1
    "_millionev":  HBAR_C_MEV_M,  # variant without trailing _
    "_mev_":       HBAR_C_MEV_M,  # MeV^-1
    "_Mev_":       HBAR_C_MEV_M,  # MeV^-1 (capitalised)
    "_MeV_":       HBAR_C_MEV_M,  # MeV^-1
    "_gev_":       HBAR_C_MEV_M * 1e-3,  # GeV^-1
    "_GeV_":       HBAR_C_MEV_M * 1e-3,  # GeV^-1
    "_ev_":        HBAR_C_EV_M,   # eV^-1
    "_eV_":        HBAR_C_EV_M,   # eV^-1
}

# Files where the name suggests non-metre units but data 
# is already in metres (pre-converted by dataset author)
ALREADY_CONVERTED = {
    "2Karshenboim_2011_1_millionev_abs_ep",
    "2Karshenboim_2011_2_millionev_abs_en",
}

# ============================================================
# DETECT UNIT FROM FILENAME
# ============================================================

def detect_unit_factor(filename: str) -> tuple[float, str]:
    """
    Detect the lambda unit from a dataset filename and return
    the conversion factor to metres.

    Parameters
    ----------
    filename : str
        The stem of the CSV filename (no extension).

    Returns
    -------
    factor : float
        Multiply raw lambda values by this to get metres.
    unit_label : str
        Human-readable label of the detected unit.
    """

    if filename in ALREADY_CONVERTED:
        return 1.0, "m (pre-converted)"
    
    fname_lower = filename.lower()

    # Check inverse-energy units first (more specific)
    if "millionev" in fname_lower:
        return HBAR_C_MEV_M, "MeV⁻¹"
    if "_mev_" in fname_lower or "_mev" == fname_lower[-4:]:
        return HBAR_C_MEV_M, "MeV⁻¹"
    if "_gev_" in fname_lower:
        return HBAR_C_MEV_M * 1e-3, "GeV⁻¹"
    if "_ev_" in fname_lower:
        return HBAR_C_EV_M, "eV⁻¹"

    # Length units
    if "_fm_" in fname_lower:
        return 1e-15, "fm"
    if "_nm_" in fname_lower:
        return 1e-9, "nm"
    if "_um_" in fname_lower:
        return 1e-6, "μm"
    if "_mm_" in fname_lower:
        return 1e-3, "mm"
    if "_cm_" in fname_lower:
        return 1e-2, "cm"
    if "_ang_" in fname_lower:
        return 1e-10, "Å"

    # Default: assume metres
    return 1.0, "m"


# ============================================================
# CONVERT DATAFRAME IN PLACE
# ============================================================

def convert_lambda_to_metres(df, filename: str, verbose: bool = False):
    """
    Convert the lambda_m column of a dataset DataFrame to metres.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns ['lambda_m', 'coupling_abs'].
    filename : str
        Filename stem used to detect units.
    verbose : bool
        Print conversion info if True.

    Returns
    -------
    df : pd.DataFrame
        DataFrame with lambda_m converted to metres (copy).
    factor : float
        The conversion factor applied.
    unit_label : str
        The source unit detected.
    """
    factor, unit_label = detect_unit_factor(filename)

    if factor != 1.0:
        df = df.copy()
        df["lambda_m"] = df["lambda_m"] * factor
        if verbose:
            print(f"  [UNIT] {filename}: {unit_label} → m  (×{factor:.4e})")

    return df, factor, unit_label


# ============================================================
# MICROSCOPIC / MACROSCOPIC CLASSIFICATION
# ============================================================

# Boundary between "microscopic" (atomic/nuclear/collider-probed) and
# "macroscopic" (bulk-matter, Dobrescu-Mocioiu-style) interaction ranges.
# 1 um is the conventional cutoff in the Yukawa-force literature (e.g.
# Adelberger/Eot-Wash reviews): below it, bounds come from atomic, nuclear
# or collider physics; above it, from torsion-balance-style experiments.
SCALE_REGIME_THRESHOLD_M = 1e-6


def classify_scale_regime(lambda_m_values, threshold_m: float = SCALE_REGIME_THRESHOLD_M) -> str:
    """
    Classify a dataset's interaction-range (lambda) values as
    'microscopic', 'macroscopic', or 'mixed', by majority vote.

    Parameters
    ----------
    lambda_m_values : array-like
        Lambda values already converted to metres.
    threshold_m : float
        Boundary between microscopic and macroscopic, in metres.

    Returns
    -------
    str
        'microscopic' if >50% of points have lambda < threshold_m,
        'macroscopic' if >50% have lambda >= threshold_m,
        'mixed' on an exact 50/50 split, 'UNKNOWN' if there are no points.
    """
    lam = np.asarray(lambda_m_values, dtype=float)
    lam = lam[np.isfinite(lam) & (lam > 0)]

    if lam.size == 0:
        return "UNKNOWN"

    frac_micro = np.mean(lam < threshold_m)

    if frac_micro > 0.5:
        return "microscopic"
    if frac_micro < 0.5:
        return "macroscopic"
    return "mixed"


# ============================================================
# AUDIT ALL DATASETS
# ============================================================

def audit_units(datasets, verbose: bool = True) -> dict:
    """
    Scan all discovered datasets and report unit breakdown.

    Parameters
    ----------
    datasets : list of ConstraintDataset
        As returned by discover_datasets().
    verbose : bool
        Print summary table.

    Returns
    -------
    report : dict
        {filename: (factor, unit_label)} for all datasets.
    """
    report = {}
    non_metre = []

    for d in datasets:
        factor, unit_label = detect_unit_factor(d.filename)
        report[d.filename] = (factor, unit_label)
        if factor != 1.0:
            non_metre.append((d.filename, unit_label, factor))

    if verbose:
        print(f"\nUnit audit: {len(datasets)} datasets total")
        print(f"  Standard metres:     {len(datasets) - len(non_metre)}")
        print(f"  Require conversion:  {len(non_metre)}")

        if non_metre:
            print("\n  Non-metre datasets:")
            print(f"  {'Filename':<55} {'Unit':<10} {'Factor'}")
            print("  " + "-" * 80)
            for fname, unit, factor in sorted(non_metre):
                print(f"  {fname:<55} {unit:<10} {factor:.4e}")

    return report


# ============================================================
# SELF-TEST
# ============================================================

if __name__ == "__main__":
    test_cases = [
        ("2Karshenboim_2011_1_millionev_abs_ep", "MeV⁻¹", HBAR_C_MEV_M),
        ("3Fadeev_2022_2_m_abs_ebare",           "m",      1.0),
        ("3Terrano_2015_m_abs_ee",               "m",      1.0),
        ("SomeFile_cm_sector",                   "cm",     1e-2),
        ("SomeFile_nm_sector",                   "nm",     1e-9),
    ]

    print("Unit detection self-test:")
    print(f"{'Filename':<45} {'Expected':<10} {'Got':<10} {'Pass'}")
    print("-" * 75)
    all_pass = True
    for fname, expected_label, expected_factor in test_cases:
        factor, label = detect_unit_factor(fname)
        ok = abs(factor - expected_factor) < 1e-30 * max(factor, 1)
        status = "✓" if ok else "✗"
        if not ok:
            all_pass = False
        print(f"{fname:<45} {expected_label:<10} {label:<10} {status}")

    print(f"\n{'All tests passed ✓' if all_pass else 'Some tests FAILED ✗'}")