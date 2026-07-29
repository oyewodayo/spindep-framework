# Naming fix: missing `V1` potential tag (2026-07-28)

## What changed

The following files were renamed to add the `V1_` prefix required by the
[spindep-convention](https://github.com/oyewodayo/spindep-convention)
filename spec:

| Old name | New name |
|---|---|
| `Delaunay_2017.csv` | `V1_Delaunay_2017.csv` |
| `Adkins_2022_eeplus.csv` | `V1_Adkins_2022_eeplus.csv` |
| `Casimir_ee.csv` | `V1_Casimir_ee.csv` |
| `WEP_ee.csv` | `V1_WEP_ee.csv` |
| `Torsion_ee.csv` | `V1_Torsion_ee.csv` |
| `eeastro_m_abs.csv` | `V1_eeastro_m_abs.csv` |
| `Ohayon_2022_e_muplus.csv` | `V1_Ohayon_2022_e_muplus.csv` |
| `Supernova_mu_mu.csv` | `V1_Supernova_mu_mu.csv` |
| `Stadnik_2023_e_muplus.csv` | `V1_Stadnik_2023_e_muplus.csv` |

No CSV contents were modified — only filenames.

## Why

The canonical filename spec (`{V}{n}_{Author}{Year}_{sector}_{coupling}.csv`)
requires an explicit potential-number token in every filename; there is no
documented fallback for inferring it otherwise. These files were missing
that token, so `spindep/src/parser.py::extract_potential()` fell back to
`"UNKNOWN"` for all of them, which showed up as an `UNKNOWN` potential in
the Batch Results table for every gsgs pair that matched one of these files.

The correct potential is **V1** (monopole-monopole, Yukawa scalar) — not
inferred from the data, but from the coupling type itself: gsgs is the
g_S·g_S vertex product, and per the Dobrescu-Mocioiu classification
(see `about_project.md`, Potentials table) g_S·g_S maps to exactly one
non-relativistic potential structure, V1. There is no other V-number built
from a g_S·g_S coupling, so the mapping is definitional, not per-dataset.

## Related change

`spindep/src/parser.py` had matching entries added to
`FILENAME_SECTOR_OVERRIDES` for each renamed file (old keys were kept, not
replaced, since some stems — e.g. `eNastro_m_abs` — are shared with files
in other coupling folders that were not renamed).
