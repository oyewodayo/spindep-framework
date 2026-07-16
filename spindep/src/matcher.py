# // matcher.py
"""
Matter-antimatter pair matching for SPINDEP.

Covers all sectors across all Dobrescu-Mocioiu couplings:
  gAgA, gAgV, gVgV, gpgp, gpgs, gsgs
"""
from .parser import SECTOR_EQUIVALENCE


# ============================================================
# EXTENDED SECTOR EQUIVALENCE
# Supersedes the base dict in parser.py with full coverage
# ============================================================

SECTOR_EQUIVALENCE = {
    # lepton-lepton
    "ee":       ["eebar"],
    "eebar":    ["ee"],
    "emu":      ["emubar"],
    "emubar":   ["emu"],
    "mumu":     ["mumubar"],
    "mumubar":  ["mumu"],

    # lepton-nucleon
    "ep":       ["epbar"],
    "epbar":    ["ep"],
    "en":       ["enbar"],
    "enbar":    ["en"],
    "np":       ["npbar"],
    "npbar":    ["np"],

    # lepton-nucleus
    "eN":       ["eNbar"],
    "eNbar":    ["eN"],

    # nucleon-nucleon
    "nn":       ["nnbar"],
    "nnbar":    ["nn"],
    "pp":       ["ppbar"],
    "ppbar":    ["pp"],

    # nucleus sectors
    # nN and pN are matter; their antimatter counterparts don't
    # yet exist in the dataset, but define for future use.
    "nN":       ["nNbar"],
    "pN":       ["pNbar"],

    # same-type pairings used in gAgV / gVgV
    # These files compare e-n vs e-p within the same coupling
    # (cross-sector within lepton-nucleon class)
    "en":       ["enbar", "ep"],   # en can pair with ep for gAgV
    "ep":       ["epbar", "en"],
}


# ============================================================
# CHECK SECTOR COMPATIBILITY
# ============================================================

def compatible_sectors(a_sector, b_sector):
    if a_sector == b_sector:
        return True
    return b_sector in SECTOR_EQUIVALENCE.get(a_sector, [])


# ============================================================
# CHECK DATASET COMPATIBILITY
# Two datasets are a valid matter-antimatter pair if they share:
#   - same coupling (gAgA, gAgV, ...)
#   - same potential (V2, V4+5, V9+10, ...)
#   - same interaction_class (lepton-lepton, lepton-nucleon, ...)
#   - compatible sectors
#   - opposite matter/antimatter status
# ============================================================

def are_compatible(a, b):
    return (
        a.coupling          == b.coupling          and
        a.potential         == b.potential         and
        a.interaction_class == b.interaction_class and
        compatible_sectors(a.sector, b.sector)     and
        a.contains_antimatter != b.contains_antimatter
    )


# ============================================================
# BUILD MATCHED PAIRS
# ============================================================

def build_pairs(datasets):
    pairs = []
    for i in range(len(datasets)):
        for j in range(i + 1, len(datasets)):
            a = datasets[i]
            b = datasets[j]
            if are_compatible(a, b):
                matter     = a if not a.contains_antimatter else b
                antimatter = b if not a.contains_antimatter else a
                pairs.append((matter, antimatter))
    return pairs