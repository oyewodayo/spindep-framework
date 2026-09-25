# // parser.py
"""
Parser for SPINDEP constraint datasets.
Handles all Dobrescu-Mocioiu potentials V1-V16 across all couplings:
  gAgA, gAgV, gVgV, gpgp, gpgs, gsgs
"""
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd
import re


# ============================================================
# DATASET OBJECT
# ============================================================

@dataclass
class ConstraintDataset:
    filepath: Path
    filename: str
    coupling: str
    interaction_class: str
    potential: str
    source: str
    sector: str
    contains_antimatter: bool
    label: str
    # Populated later, once the CSV's lambda column has been loaded and
    # unit-converted (see pipeline.run_pipeline) -- not known at parse time.
    scale_regime: str = "UNKNOWN"
    # Which quantity the second CSV column holds. Most of the database is a
    # coupling bound |g|; the V1_alpha_data family is |alpha|, the Yukawa
    # strength relative to gravity ("presented in unified units, i.e.
    # lambda (eV) and |alpha| (dimensionless)" -- datasets/normalized/V1/
    # V1_data.md). The two differ by ~37 decades and must never share a
    # y-axis. See NORMALISATION_LABELS in constraint_plots.py.
    normalisation: str = "g"
    # Non-empty when the dataset is compiled into the registry but held out
    # of the physics analysis. Set in pipeline.run_pipeline from
    # constraint_plots.EXCLUDED_FROM_ANALYSIS; the text is the stated reason.
    excluded_reason: str = ""


# ============================================================
# SECTOR ALIASES
# Raw filename token → canonical sector name
# Covers both old underscore style and new hyphen style
# ============================================================

SECTOR_ALIASES = {

    # ── electron sectors ──────────────────────────────────────
    "ebare":      "eebar",
    "ebar":       "eebar",
    "ebarpar":    "epbar",
    "ebarpabr":   "epbar",
    "ebarpbar":   "epbar",
    "eeplus":     "eebar",    # positronium-like e-e+
    "eebar":      "eebar",

    # ── muon sectors ──────────────────────────────────────────
    "emubare":    "emubar",
    "emubar":     "emubar",
    "mumubare":   "mumubar",
    "muplus":     "mubar",
    "eeplus":     "eebar",
    "mu":         "mu",

    # ── nucleon sectors (underscore style) ────────────────────
    "epbare":     "epbar",
    "nnbare":     "nnbar",
    "ppbare":     "ppbar",
    "pnbar":      "npbar",
    "np":         "np",
    "pn":         "np",

    # ── nucleon sectors (hyphen style, gAgV/gVgV files) ───────
    "e-n":        "en",
    "e-p":        "ep",
    "e-N":        "eN",
    "n-n":        "nn",
    "n-p":        "np",
    "p-N":        "pN",
    "n-N":        "nN",
    "N-N":        "nN",      # treat N-N as generic nucleon-nucleus

    # ── nucleus sectors ───────────────────────────────────────
    "nN":         "nN",
    "pN":         "pN",
    "eN":         "eN",
    "NN":         "nN",      # NN (capitalised) → nN

    # ── exotic lepton sectors ─────────────────────────────────
    "muplus":     "mubar",
    "eeplus":     "eebar",
    "e_muplus":   "emu",     # Ohayon/Stadnik e-mu+ files

    # ── experiment-type labels ────────────────────────────────
    "Casimir":    "ee",
    "EMM":        "eN",
    "EEP":        "eN",
    "Torsion":    "ee",
    "MS":         "nN",
    "WEP":        "ee",

    # ── astrophysical ─────────────────────────────────────────
    "eastro":     "eastro",
    "eeastro":    "eastro",
    "NNastro":    "NNastro",
    "eNastro":    "eNastro",
    "nNastro":    "nNastro",
    "pNastro":    "pNastro",
    "NN":         "nN",
    "eN":         "eN",
}


# ============================================================
# FERMION MAP  (canonical sector → display label)
# ============================================================

FERMION_MAP = {
    # lepton-lepton
    "ee":       "e⁻-e⁻",
    "eebar":    "e⁻-e⁺",
    "emu":      "e-μ",
    "emubar":   "e-μ̄",
    "mumu":     "μ-μ",
    "mumubar":  "μ-μ̄",
    "mu":       "μ",
    "mubar":    "μ̄",

    # lepton-nucleon
    "ep":       "e-p",
    "epbar":    "e-p̄",
    "en":       "e-n",
    "enbar":    "e-n̄",
    "np":       "n-p",
    "npbar":    "n-p̄",

    # lepton-nucleus
    "eN":       "e-N",
    "eNbar":    "e-N̄",
    "pN":       "p-N",
    "nN":       "n-N",

    # nucleon-nucleon
    "nn":       "n-n",
    "nnbar":    "n-n̄",
    "pp":       "p-p",
    "ppbar":    "p-p̄",

    # exotic
    "antipHe":  "p̄-He",
    "ddmu":     "dd-μ",
    "muN":      "μ-N",

    # astrophysical
    "eastro":   "e (astro)",
    "NNastro":  "N-N (astro)",
    "eNastro":  "e-N (astro)",
    "pNastro":  "p-N (astro)",
    "nNastro":  "n-N (astro)",
}


# ============================================================
# ANTIMATTER SECTORS  (canonical forms only)
# ============================================================

ANTIMATTER_SECTORS = {
    "eebar",
    "emubar",
    "mumubar",
    "epbar",
    "enbar",
    "npbar",
    "eNbar",
    "nnbar",
    "ppbar",
    "mubar",
    "antipHe",  # p-bar-He: contains an antiproton
    "ddmu",     # ddmu+ molecular ion: contains an antimuon
}


# ============================================================
# MATTER-ANTIMATTER EQUIVALENCE
# ============================================================

SECTOR_EQUIVALENCE = {
    "ee":       ["eebar"],
    "eebar":    ["ee"],
    "emu":      ["emubar"],
    "emubar":   ["emu"],
    "mumu":     ["mumubar"],
    "mumubar":  ["mumu"],
    "ep":       ["epbar"],
    "epbar":    ["ep"],
    "en":       ["enbar"],
    "enbar":    ["en"],
    "np":       ["npbar"],
    "npbar":    ["np"],
    "eN":       ["eNbar"],
    "eNbar":    ["eN"],
    "nn":       ["nnbar"],
    "nnbar":    ["nn"],
    "pp":       ["ppbar"],
    "ppbar":    ["pp"],
    # nucleus sectors pair with their antimatter equivalents
    "nN":       ["nNbar"],
    "pN":       ["pNbar"],
}


# ============================================================
# KNOWN SECTORS
# ============================================================

KNOWN_SECTORS = set(FERMION_MAP.keys())


# ============================================================
# TOKENS TO SKIP IN SECTOR SEARCH
# ============================================================

SKIP_TOKENS = {
    "m", "M", "abs", "ABS", "copy", "Copy",
    "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8",
    "V9", "V10", "V11", "V12", "V13", "V14", "V15", "V16",
    "combined", "Combined", "astro",
}


# ============================================================
# FILENAME → (sector, contains_antimatter) OVERRIDES
# For files whose sector cannot be reliably parsed from name
# ============================================================

FILENAME_SECTOR_OVERRIDES = {

    # ── V1 / scalar exchange datasets ─────────────────────────
    "Alighanbari_2020":          ("ep",   False),
    "Hoskins_1985":              ("nn",   False),
    "Kapner_2007":               ("ee",   False),
    "Chen_2016":                 ("ee",   False),
    "Tan_2020":                  ("ee",   False),
    "Lee_2020":                  ("nn",   False),
    "Bordag_2001":               ("ee",   False),
    "Delaunay_2017":             ("ee",   False),
    "Colliders":                 ("ee",   False),
    # Salumbides et al. (2014): bounds derived from antiprotonic helium
    # (p-bar-He, contains an antiproton) and the ddmu+ molecular ion
    # (contains an antimuon) -- Cong et al. 2025, p.82: "for p-bar-N" and
    # "for mu+-N" respectively -- both genuine antimatter-sector bounds.
    "Salumbides_antipHe_2014":   ("antipHe", True),
    "Salumbides_ddmu_2014":      ("ddmu",    True),
    "New_constriants_1":         ("ee",   False),
    "New_constriants_2":         ("ee",   False),
    "Neutron_scattering":        ("nn",   False),
    "neutron_scattering":        ("nn",   False),
    "Supernova_mu_mu":           ("mumu", False),

    # ── gsgs specific ─────────────────────────────────────────
    "Casimir_ee":                ("ee",   False),
    "Torsion_ee":                ("ee",   False),
    "WEP_ee":                    ("ee",   False),
    "Adkins_2022_eeplus":        ("eebar",True),
    "Ohayon_2022_e_muplus":      ("emu",  False),   # e-μ+ is matter side
    "Stadnik_2023_e_muplus":     ("emu",  False),
    "Delaunay_2017_en":          ("en",   False),
    "Casimir_NN":                ("nN",   False),
    "Delaunay_2022_NN":          ("nN",   False),
    "Torsion_NN":                ("nN",   False),
    "WEP_NN":                    ("nN",   False),
    "Salumbides_2018_mu_N":      ("muN",  False),
    "Salumbides_2018_p_N":       ("pN",   False),

    # ── gsgs specific, V1-prefixed (post spindep-convention rename) ──
    # Same stems as above with a V1_ prefix added to comply with the
    # canonical {V}{n}_{Author}{Year}_{sector}_{coupling}.csv naming
    # convention. Old keys kept above for other couplings' copies
    # (e.g. eNastro_m_abs.csv also exists under gpgp/).
    "V1_Casimir_ee":             ("ee",     False),
    "V1_Torsion_ee":             ("ee",     False),
    "V1_WEP_ee":                 ("ee",     False),
    "V1_Adkins_2022_eeplus":     ("eebar",  True),
    "V1_Ohayon_2022_e_muplus":   ("emu",    False),
    "V1_Stadnik_2023_e_muplus":  ("emu",    False),
    "V1_Delaunay_2017":          ("ee",     False),
    "V1_Delaunay_2017_en":       ("en",     False),
    "V1_Casimir_NN":             ("nN",     False),
    "V1_Delaunay_2022_NN":       ("nN",     False),
    "V1_Torsion_NN":             ("nN",     False),
    "V1_WEP_NN":                 ("nN",     False),
    "V1_Salumbides_2018_mu_N":  ("muN",    False),
    "V1_Salumbides_2018_p_N":   ("pN",     False),
    "V1_eeastro_m_abs":          ("eastro", False),
    "V1_eNastro_m_abs":          ("eNastro",False),
    "V1_Neutron_scattering":     ("nn",     False),
    "V1_Supernova_mu_mu":        ("mumu",   False),
    "V1_Alighanbari_2020":       ("ep",     False),

    # ── gAgV / gVgV Combined experiment-type files ────────────
    # lepton-lepton
    "Combined_Casimir_e-e":      ("ee",   False),
    "Combined_EEP_e-e":          ("ee",   False),
    "Combined_EMM_e-e":          ("ee",   False),
    "Combined_Torsion_e-e":      ("ee",   False),
    # lepton-nucleon
    "Combined_Casimir_e-N":      ("eN",   False),
    "Combined_EEP_e-N":          ("eN",   False),
    "Combined_MS_e-N":           ("eN",   False),
    "Combined_Torsion_e-N":      ("eN",   False),
    # nucleon-nucleon
    "Combined_Casimir_N-N":      ("nN",   False),
    "Combined_EEP_N-N":          ("nN",   False),
    "Combined_MS_N-N":           ("nN",   False),
    "Combined_Torsion_N-N":      ("nN",   False),

    # ── gVgV specific ─────────────────────────────────────────
    "V1_gsN_Casimir":            ("nN",   False),
    "V1_gsN_EEP":                ("nN",   False),
    "V1_gsN_MS":                 ("nN",   False),
    "V1_gsN_Torsion":            ("nN",   False),
    "V1_gse_Casimir":            ("ee",   False),
    "V1_gse_EEP":                ("ee",   False),
    "V1_gse_EMM":                ("ee",   False),
    "V1_gse_Torsion":            ("ee",   False),

    # ── gpgs combined curves ──────────────────────────────────
    # lepton-lepton (e-e sector, combined monopole-dipole)
    "1agepgescombined1_m_abs":   ("ee",   False),
    "1agepgescombined2_m_abs":   ("ee",   False),
    "1agepgescombined3_m_abs":   ("ee",   False),
    "1agepgescombined4_m_abs":   ("ee",   False),
    # lepton-nucleon (e-N sector)
    "1agepgNscombined1_m_abs":   ("eN",   False),
    "1agepgNscombined2_m_abs":   ("eN",   False),
    "1agepgNscombined3_m_abs":   ("eN",   False),
    "1agepgNscombined4_m_abs":   ("eN",   False),
    # nucleon-nucleon neutron (n-N sector)
    "1agnpgNscombined1_m_abs":   ("nN",   False),
    "1agnpgNscombined2_m_abs":   ("nN",   False),
    "1agnpgNscombined3_m_abs":   ("nN",   False),
    "1agnpgNscombined4_m_abs":   ("nN",   False),
    # nucleon-nucleon proton (p-N sector)
    "1agppgNscombined1_m_abs":   ("pN",   False),
    "1agppgNscombined2_m_abs":   ("pN",   False),
    "1agppgNscombined3_m_abs":   ("pN",   False),
    "1agppgNscombined4_m_abs":   ("pN",   False),

    # ── gpgs/gpgp astrophysical ───────────────────────────────
    "eeastro_m_abs":             ("eastro", False),
    "eNastro_m_abs":             ("eNastro", False),
    "NNastro_m_abs":             ("NNastro", False),
    "nNastro_m_abs":             ("nNastro", False),
    "pNastro_m_abs":             ("pNastro", False),
    "1aeeastro_m_abs":           ("eastro", False),
    "1aeNastro_m_abs":           ("eNastro", False),
    "1aNNastro_m_abs":           ("NNastro", False),
    "1anNastro_m_abs":           ("nNastro", False),
    "1apNastro_m_abs":           ("pNastro", False),
}


# ============================================================
# POTENTIAL EXTRACTION
# Maps leading numeric tokens to canonical potential names
# ============================================================

# Direct prefix → potential (checked first, most specific)
POTENTIAL_PREFIX_MAP = {
    "V1213":  "V12+13",
    "V45":    "V4+5",
    "V4+5":   "V4+5",
    "V910":   "V9+10",
    "V11":    "V11",
    "V12":    "V12+13",
    "V13":    "V12+13",
    "V16":    "V16",
    "V15":    "V15",
    "V14":    "V14",
    "451":    "V4+5",   # e.g. 451_Wu_2023
    "45":     "V4+5",   # e.g. 45Ficek_2017
    "910":    "V9+10",  # e.g. 910Crescini_2022
    "1213":   "V12+13",
    "15":     "V15",
    "16":     "V16",
    "14":     "V14",
    "8":      "V8",
    "23":     "V2+3",   # e.g. 23Cong_2025: upstream records this as V2+V3
    # A bare "3" prefix is V3 alone, NOT the V2+V3 combination. Verified
    # against the source database's curation records: all 36 of the
    # 3-prefixed files that carry an api/v1/records entry are labelled
    # "V3" there, and six papers (Ficek 2017/2018, Almasi 2020, Cong 2025,
    # Kimball 2010, Ledbetter 2013) publish BOTH a 2- and a 3-prefixed
    # curve in the same coupling and sector, differing by up to 27 decades
    # -- two separable bounds, so "3" cannot mean the inseparable pair.
    "3":      "V3",
    "2":      "V2",
    "1":      "V1",
    "1a":     "V1a",    # astrophysical combined
}


def extract_potential(parts, filepath=None):
    """
    Extract the Dobrescu-Mocioiu potential label from filename parts.

    Priority order:
    1. Explicit V-token (V11, V1213, V4+5, V16, ...)
    2. Numeric prefix on first token
    3. Directory-based fallback (e.g. V1_alpha_data/Hoskins_1985.csv, whose
       filename carries no potential token at all but whose parent
       directory names the potential unambiguously)
    4. Fallback UNKNOWN
    """
    if not parts:
        return "UNKNOWN"

    first = parts[0]

    # ── 1. Explicit V-prefixed token anywhere ─────────────────
    for p in parts:
        # V4+5 or V45 style
        if re.match(r"^V4\+5$", p, re.IGNORECASE):
            return "V4+5"
        # V1213 style
        if re.match(r"^V1213$", p, re.IGNORECASE):
            return "V12+13"
        # V910 style
        if re.match(r"^V910$", p, re.IGNORECASE):
            return "V9+10"
        # Generic V{digits} token
        m = re.match(r"^V(\d+(?:\+\d+)?)$", p, re.IGNORECASE)
        if m:
            return f"V{m.group(1)}"

    # ── 2. Leading digit(s) on first part ─────────────────────
    # Match patterns like: 45Ficek, 910Crescini, 1213Foo, 451Wu, 15Hunter, 8Ji
    # Pure standalone numeric first token: "451", "45", "1a", "8" etc.
    m = re.match(r"^(1213|910|451|45|23|15|16|14|13|12|11|10|1a|8|7|6|5|4|3|2|1)$", first)
    if m:
        prefix = m.group(1)
        return POTENTIAL_PREFIX_MAP.get(prefix, f"V{prefix}")

    # Prefix attached directly to author: "45Ficek", "910Crescini", "8Ji"
    m = re.match(r"^(1213|910|451|45|23|15|16|14|13|12|11|10|1a|8|7|6|5|4|3|2|1)([A-Za-z])", first)
    if m:
        prefix = m.group(1)
        return POTENTIAL_PREFIX_MAP.get(prefix, f"V{prefix}")

    # ── 3. Standalone digit token in parts[1:] ────────────────
    for p in parts[1:]:
        if re.match(r"^\d+[a-z]?$", p) and len(p) <= 3:
            return f"V{p}"

    # ── 4. Directory-based fallback ───────────────────────────
    if filepath is not None:
        for segment in Path(filepath).parts:
            m = re.match(r"^V(\d+)_alpha_data$", segment, re.IGNORECASE)
            if m:
                return f"V{m.group(1)}"

    return "UNKNOWN"


# ============================================================
# SECTOR EXTRACTION
# ============================================================

def extract_sector_from_hyphen(name_clean):
    """
    Handle hyphenated sector notation used in gAgV/gVgV files.
    e.g. 'V11_Hunter_2013_e-n' → 'en'
         'V1213_Clayburn_2023_n-N' → 'nN'
    """
    # Match trailing hyphenated sector: e-n, n-N, p-N, n-p, e-p, e-N, N-N
    m = re.search(r"[_-]([epnNmu]+)-([NnpePmu]+)$", name_clean)
    if m:
        raw = m.group(1) + "-" + m.group(2)
        return SECTOR_ALIASES.get(raw, None)
    return None


def normalize_sector(raw):
    s = raw.strip()
    s = re.sub(r"\s*copy\s*$", "", s, flags=re.IGNORECASE)
    s = s.replace("-", "")    # remove hyphens for alias lookup
    s = s.replace("+", "bar")
    s = s.replace("−", "")
    return SECTOR_ALIASES.get(s, SECTOR_ALIASES.get(raw.strip(), s))


def extract_sector(parts, coupling=None):
    skip = {
        "m", "M", "abs", "ABS", "copy", "V1", "V2", "V3", "V4",
        "V5", "V6", "V7", "V8", "V9", "V10", "V11", "V12", "V13",
        "V14", "V15", "V16", "combined", "Combined",
    }
    # spindep-convention filenames end in "_{coupling}" (e.g. "..._gsgs.csv");
    # that token is never a sector, so exclude it from candidates.
    coupling_lc = coupling.lower() if coupling else None
    candidates = []

    for p in reversed(parts):
        p_clean = p.strip()
        if re.match(r"^\d+$", p_clean):
            continue
        if re.match(r"^V\d+(\+\d+)?$", p_clean, re.IGNORECASE):
            continue
        if p_clean in skip:
            continue
        if coupling_lc and p_clean.lower() == coupling_lc:
            continue
        if re.match(r"^[a-zA-Z]", p_clean):
            candidates.append(p_clean)

    if not candidates:
        return "UNKNOWN"

    # Try joined pair for split sectors like "p"+"N" → "pN"
    if len(candidates) >= 2:
        a, b = candidates[0], candidates[1]
        if len(a) <= 2 and len(b) <= 2:
            joined = b + a
            if joined in KNOWN_SECTORS or joined in SECTOR_ALIASES:
                return joined

    return candidates[0]


# ============================================================
# COUPLING AND INTERACTION CLASS
# ============================================================

# Directories whose CSVs hold |alpha| rather than |g|.
ALPHA_DATA_DIR_SUFFIX = "_alpha_data"


def detect_normalisation(filepath):
    """'alpha' for the gravity-normalised families, otherwise 'g'."""
    for part in Path(filepath).parts:
        if part.lower().endswith(ALPHA_DATA_DIR_SUFFIX):
            return "alpha"
    return "g"


def extract_coupling_and_class(filepath):
    parts = filepath.parts
    try:
        normalized_idx = next(
            i for i, p in enumerate(parts) if p == "normalized"
        )
        coupling          = parts[normalized_idx + 1]
        interaction_class = parts[normalized_idx + 2]
        return coupling, interaction_class
    except (StopIteration, IndexError):
        return filepath.parts[-3], filepath.parts[-2]


# ============================================================
# BUILD DISPLAY LABEL
# ============================================================

def build_label(source, sector):
    pair = FERMION_MAP.get(sector, sector)
    return f"{source} ({pair})"


# ============================================================
# AUTHOR / SOURCE EXTRACTION
# ============================================================

def extract_year(parts):
    for p in parts:
        # A trailing letter marks one of several bounds from the same
        # paper ("2023a", "2023b"). Requiring a bare 4-digit token threw
        # it away and, with it, the year: all three Clayburn 2023 files
        # collapsed to the source "Clayburn", so they could only be told
        # apart in a legend by appending their whole filename.
        if re.match(r"^\d{4}[a-z]?$", p):
            return p
    # spindep-convention fuses {Author}{Year} with no separator (e.g.
    # "Smith2024"); fall back to a trailing 4-digit year on any alpha token.
    for p in parts:
        if any(c.isalpha() for c in p):
            m = re.search(r"(\d{4})$", p)
            if m:
                return m.group(1)
    return "UNKNOWN"


def extract_author(parts):
    skip = {
        "m", "M", "abs", "ABS", "copy",
        "combined", "Combined", "astro",
    }
    for p in parts:
        if re.match(r"^\d+$", p):
            continue
        if re.match(r"^V?\d+[a-z]?$", p, re.IGNORECASE):
            continue
        if p in skip:
            continue
        # Coupling-type tokens (e.g. "gse", "gsN" -- scalar coupling to
        # electron/nucleon) are not author names; the real identifier
        # (e.g. "Casimir", "EMM") follows later in these filenames.
        if re.match(r"^g[sVAp][a-zA-Z]{0,3}$", p):
            continue
        if any(c.isalpha() for c in p):
            # Strip the leading potential token. "1a" is the only one that
            # carries a letter, so only that letter may be consumed: a bare
            # r"^\d+[a-z]?" also ate the first letter of a lower-case author
            # ("910guigue" -> "uigue", "2ledbetter" -> "edbetter").
            author = re.sub(r"^1a(?=[A-Za-z])", "", p)
            if author == p:
                author = re.sub(r"^\d+", "", p)
            # spindep-convention fused "{Author}{Year}" (e.g. "Smith2024")
            author = re.sub(r"\d{4}$", "", author)
            if author:
                return author
    return "UnknownAuthor"


# ============================================================
# FILENAME → potential OVERRIDES
# For files whose potential cannot be parsed from the filename at all
# (no V-token, no numeric prefix). Only add an entry here once the
# source publication has been checked to confirm the potential label --
# see the comment on each entry for the verification.
# ============================================================

FILENAME_POTENTIAL_OVERRIDES = {
    # Delaunay, Frugiuele, Fuchs & Soreq (2017), Phys. Rev. D 96, 115002:
    # "Probing new spin-independent interactions through precision
    # spectroscopy in atoms with few electrons" -- spin-independent
    # scalar (monopole-monopole) interaction between electrons -> V1.
    "Delaunay_2017":       "V1",
    # Adkins, Cassidy & Perez-Rios (2022), Phys. Rept. 975, 1: bounds on
    # spin-independent g_s^e g_s^{e+} from positronium spectroscopy -> V1.
    "Adkins_2022_eeplus":  "V1",
}


# ============================================================
# DIRECTORY / FILENAME SECTOR CROSS-CHECK
# ============================================================

# Two branches of the tree carry a third directory level naming the sector:
# gpgs/nucleon-nucleon/ -- g_p g_s has asymmetric vertices, so which nucleon
# carries the pseudoscalar coupling is a different bound -- and
# gAgA/lepton-nucleon/. Nothing read that level, which is how a file named
# "..._nN.csv" came to sit in proton-nucleon/ and be plotted as an n-N bound.
# The directory is authoritative where the filename is merely generic, and a
# check on it otherwise.
SECTOR_DIR_HINTS = {
    "neutron-nucleon":               ("nN",),
    "proton-nucleon":                ("pN",),
    "electron-neutron":              ("en",),
    "electron-nucleon":              ("eN",),
    "electron-proton_or_antiproton": ("ep", "epbar"),
}

# Filename tokens that say "a nucleon" without saying which one.
GENERIC_NUCLEON_TOKENS = {"NN", "N-N", "N", "nucleon"}


def _sector_dir_hint(filepath):
    """The sector-naming directory on this path, if there is one."""
    for part in Path(filepath).parts:
        expected = SECTOR_DIR_HINTS.get(part.lower())
        if expected:
            return part, expected
    return None, None


def reconcile_sector_with_directory(sector, sector_raw, filepath, name):
    """Reconcile the sector read from the filename with its directory.

    A generic filename token ("NN") defers to the directory, which is
    strictly more specific. A specific token that contradicts the directory
    is left as-is but reported: only the source publication can say which of
    the two is wrong, and silently trusting either would be a guess.
    """
    folder, expected = _sector_dir_hint(filepath)
    if expected is None:
        return sector

    # Astrophysical bounds are filed by the particles they constrain, not by
    # the nucleon pairing these directories describe -- not comparable.
    if sector.endswith("astro"):
        return sector

    if sector_raw in GENERIC_NUCLEON_TOKENS:
        if sector != expected[0]:
            print(f"[SECTOR] {name}: generic {sector_raw!r} resolved to "
                  f"{expected[0]!r} by {folder}/ (filename alone gave "
                  f"{sector!r})")
        return expected[0]

    if sector not in expected:
        print(f"[WARN] {name}: filename says sector {sector!r} but the file "
              f"sits in {folder}/, which expects "
              f"{' or '.join(repr(e) for e in expected)}")
    return sector


# ============================================================
# MAIN PARSE FUNCTION
# ============================================================

def parse_dataset(filepath):
    filepath = Path(filepath)
    name = filepath.stem
    name_clean = re.sub(r"\s*copy\s*$", "", name, flags=re.IGNORECASE)

    # Replace hyphens between sector tokens with underscores for splitting
    # but keep the original for hyphen-sector detection
    parts = name_clean.replace("V4+5", "V4p5").split("_")
    # Restore V4+5
    parts = [p.replace("V4p5", "V4+5") for p in parts]

    try:
        potential                    = FILENAME_POTENTIAL_OVERRIDES.get(name_clean) or extract_potential(parts, filepath)
        year                         = extract_year(parts)
        author                       = extract_author(parts)
        coupling, interaction_class  = extract_coupling_and_class(filepath)

        # ── Sector resolution (priority order) ────────────────
        sector_raw = None

        if name_clean in FILENAME_SECTOR_OVERRIDES:
            sector, contains_antimatter = FILENAME_SECTOR_OVERRIDES[name_clean]

        else:
            # Try hyphen-style first (gAgV/gVgV convention)
            sector = extract_sector_from_hyphen(name_clean)

            if sector is None:
                # Fall back to underscore-token extraction
                sector_raw = extract_sector(parts, coupling=coupling)
                sector     = normalize_sector(sector_raw)

                if sector not in KNOWN_SECTORS:
                    # One more attempt: check SECTOR_ALIASES directly
                    sector = SECTOR_ALIASES.get(sector_raw, sector)

            contains_antimatter = sector in ANTIMATTER_SECTORS

            if sector not in KNOWN_SECTORS:
                print(f"[WARN] Unrecognized sector {sector!r} in {name}")

        # The directory can be more specific than the filename, and disagree
        # with it. A hand-curated override keeps its antimatter flag unless
        # the sector itself is revised here.
        reconciled = reconcile_sector_with_directory(
            sector, sector_raw, filepath, name
        )
        if reconciled != sector:
            sector = reconciled
            contains_antimatter = sector in ANTIMATTER_SECTORS

        source = f"{author}{year}" if year != "UNKNOWN" else author
        label  = build_label(source, sector)

        return ConstraintDataset(
            filepath=filepath,
            filename=name,
            coupling=coupling,
            interaction_class=interaction_class,
            potential=potential,
            normalisation=detect_normalisation(filepath),
            source=source,
            sector=sector,
            contains_antimatter=contains_antimatter,
            label=label,
        )

    except Exception as e:
        print(f"\n[PARSE ERROR] {name}: {e}")
        return None


# ============================================================
# DISCOVER ALL DATASETS
# ============================================================

def discover_datasets(root):
    root = Path(root).resolve()
    datasets = []
    # rglob yields directory entries in filesystem order: alphabetical on
    # NTFS, hash order on ext4. Downstream deduplication picks one
    # representative per duplicated CSV, so an unsorted walk made the dataset
    # counts differ between platforms for the same files.
    #
    # Sorted by as_posix(), not by the Path objects themselves: comparing
    # Paths is case-insensitive on Windows and case-sensitive on POSIX, so
    # "gVgV" sorts before "gsgs" on one and after it on the other -- which
    # would leave the choice of representative platform-dependent again.
    for filepath in sorted(root.rglob("*.csv"), key=lambda p: p.as_posix()):
        parsed = parse_dataset(filepath)
        if parsed is not None:
            datasets.append(parsed)
    return datasets


# ============================================================
# LOAD CSV DATA
# ============================================================

# A boundary sentinel is a row the original figure used to close the shaded
# excluded region, not a measured bound: the same lambda as the first real
# point, with |g| set to a round "infinity" such as 1e+20. Detected by shape
# rather than by value, so an unusually large but genuine bound is safe.
SENTINEL_JUMP_FACTOR = 1e5      # >5 decades above its neighbour
SENTINEL_LAMBDA_RATIO = 1.023   # at the same lambda, within ~0.01 decades


def _strip_boundary_sentinel(df):
    """Drop a leading or trailing plot-boundary marker, if present.

    Checked at both ends because which end it lands on depends on the
    direction the file was written in. Only ever removes a single row.
    """
    for first, second, keep in ((0, 1, slice(1, None)), (-1, -2, slice(None, -1))):
        if len(df) < 3:
            break
        lam = df["lambda_m"].iloc
        g = df["coupling_abs"].iloc
        if g.__getitem__(second) <= 0 or lam.__getitem__(first) <= 0:
            continue
        ratio = lam.__getitem__(second) / lam.__getitem__(first)
        same_lambda = 1 / SENTINEL_LAMBDA_RATIO < ratio < SENTINEL_LAMBDA_RATIO
        towering = g.__getitem__(first) > g.__getitem__(second) * SENTINEL_JUMP_FACTOR
        if same_lambda and towering:
            return df.iloc[keep].reset_index(drop=True)
    return df


def load_dataset(filepath):
    df = pd.read_csv(
        filepath,
        header=None,
        names=["lambda_m", "coupling_abs"]
    )
    df = df.apply(pd.to_numeric, errors="coerce")
    # "Inf" in a CSV survives to_numeric as a float infinity rather than NaN,
    # and passes a ">0" test, so it reaches the plots and any statistics
    # computed downstream. One file (V11_Vasilakis_2009_n-n) carries ten.
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    df = df[(df["lambda_m"] > 0) & (df["coupling_abs"] > 0)]
    df = df.sort_values("lambda_m").reset_index(drop=True)
    return _strip_boundary_sentinel(df)