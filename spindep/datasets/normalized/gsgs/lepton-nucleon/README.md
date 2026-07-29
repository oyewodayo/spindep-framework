# Naming fix: missing `V1` potential tag (2026-07-28)

## What changed

The following files were renamed to add the `V1_` prefix required by the
[spindep-convention](https://github.com/oyewodayo/spindep-convention)
filename spec:

| Old name | New name |
|---|---|
| `eNastro_m_abs.csv` | `V1_eNastro_m_abs.csv` |
| `Delaunay_2017_en.csv` | `V1_Delaunay_2017_en.csv` |
| `Salumbides_2018_mu_N.csv` | `V1_Salumbides_2018_mu_N.csv` |
| `Salumbides_2018_p_N.csv` | `V1_Salumbides_2018_p_N.csv` |
| `Alighanbari_2020.csv` | `V1_Alighanbari_2020.csv` |
| `Astrophysical_2020_m_abs_eN.csv` | `V1_Astrophysical_2020_m_abs_eN.csv` |

No CSV contents were modified — only filenames.

Note: `eNastro_m_abs.csv` and `Alighanbari_2020.csv` also exist, unchanged,
in `gpgp/lepton-nucleon/` and `V1/V1_alpha_data/` respectively — those are
separate files for a different coupling/staging area and were intentionally
left as-is.

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
replaced, since some stems — e.g. `eNastro_m_abs`, `Alighanbari_2020` — are
shared with files in other coupling folders/staging areas that were not
renamed).
