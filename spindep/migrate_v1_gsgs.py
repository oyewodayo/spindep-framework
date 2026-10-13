"""
migrate_v1_gsgs.py
------------------
Safely migrates files from V1/V1_gsgs_data/ into the correct
gsgs/ subfolders based on particle sector classification.

Usage:
    python migrate_v1_gsgs.py --root /path/to/datasets/normalized
    python migrate_v1_gsgs.py --root /path/to/datasets/normalized --dry-run
"""

import argparse
import shutil
from pathlib import Path

# ============================================================
# MIGRATION MAP
# filename stem → destination subfolder within gsgs/
# ============================================================

MIGRATION_MAP = {

    # lepton-lepton (e-e, e-e+)
    "Adkins_2022_eeplus":       "lepton-lepton",
    "Delaunay_2017":            "lepton-lepton",
    "Torsion_ee":               "lepton-lepton",
    "WEP_ee":                   "lepton-lepton",
    "Casimir_ee":               "lepton-lepton",   # e-e Casimir (electron-electron)

    # lepton-nucleon (e-n, e-p, mu-N)
    "Delaunay_2017_en":         "lepton-nucleon",  # electron-neutron
    "Alighanbari_2020":         "lepton-nucleon",  # HD+ spectroscopy (e-p)
    "Salumbides_2014_mu_N":     "lepton-nucleon",  # ddmu+ (mu+ -N), antimatter
    "Salumbides_2014_p_N":      "lepton-nucleon",  # antiprotonic He (pbar-N), antimatter

    # nucleon-nucleon (n-n, N-N)
    "Casimir_NN":               "nucleon-nucleon",
    "WEP_NN":                   "nucleon-nucleon",
    "Delaunay_2022_NN":         "nucleon-nucleon",
    "Neutron_scattering":       "nucleon-nucleon",
    "Torsion_NN":               "nucleon-nucleon",  # torsion balance, nucleon-nucleon

    # exotic lepton (e-mu, mu-mu) — placed in lepton-lepton for now
    "Ohayon_2022_e_muplus":     "lepton-lepton",
    "Stadnik_2023_e_muplus":    "lepton-lepton",
    "Supernova_mu_mu":          "lepton-lepton",
}

# ============================================================
# MAIN
# ============================================================

def migrate(root: Path, dry_run: bool = False):

    source_dir = root / "V1" / "V1_gsgs_data"
    gsgs_dir   = root / "gsgs"

    if not source_dir.exists():
        print(f"[ERROR] Source directory not found: {source_dir}")
        return

    if not gsgs_dir.exists():
        print(f"[ERROR] gsgs directory not found: {gsgs_dir}")
        return

    print("=" * 60)
    print(f"SOURCE : {source_dir}")
    print(f"TARGET : {gsgs_dir}")
    print(f"MODE   : {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 60)

    moved    = []
    skipped  = []
    unknown  = []
    conflicts = []

    for filepath in sorted(source_dir.glob("*.csv")):

        stem = filepath.stem

        if stem not in MIGRATION_MAP:
            print(f"  [UNKNOWN]  {filepath.name} — not in migration map, skipping")
            unknown.append(filepath.name)
            continue

        subfolder   = MIGRATION_MAP[stem]
        target_dir  = gsgs_dir / subfolder
        target_path = target_dir / filepath.name

        # Check for conflict
        if target_path.exists():
            print(f"  [CONFLICT] {filepath.name} already exists in {subfolder}/")
            conflicts.append(filepath.name)
            continue

        print(f"  [MOVE]     {filepath.name}")
        print(f"             → gsgs/{subfolder}/")

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(filepath), str(target_path))
            moved.append(filepath.name)
        else:
            moved.append(filepath.name)

    # --------------------------------------------------------
    # CLEANUP wrongly created folders from previous runs
    # --------------------------------------------------------

    wrong_folders = ["lepton-ee"]  # folders that should never have been created

    for wrong in wrong_folders:
        wrong_dir = gsgs_dir / wrong
        if wrong_dir.exists():
            for f in wrong_dir.glob("*.csv"):
                stem = f.stem
                correct_subfolder = MIGRATION_MAP.get(stem)
                if correct_subfolder:
                    correct_dest = gsgs_dir / correct_subfolder / f.name
                    if not dry_run:
                        (gsgs_dir / correct_subfolder).mkdir(parents=True, exist_ok=True)
                        shutil.move(str(f), str(correct_dest))
                        print(f"\n  [FIX]      {f.name} moved from lepton-ee/ → gsgs/{correct_subfolder}/")
                    else:
                        print(f"\n  [FIX DRY]  {f.name} would move from lepton-ee/ → gsgs/{correct_subfolder}/")
            if not dry_run:
                try:
                    wrong_dir.rmdir()
                    print(f"  [REMOVED]  Wrong folder: gsgs/{wrong}/")
                except OSError:
                    print(f"  [WARN]     Could not remove gsgs/{wrong}/ — not empty")

    # --------------------------------------------------------
    # CLEANUP empty source dirs (live only)
    # --------------------------------------------------------

    if not dry_run:
        try:
            source_dir.rmdir()
            print(f"\n  [REMOVED]  Empty dir: V1/V1_gsgs_data/")
        except OSError:
            remaining = list(source_dir.iterdir())
            print(f"\n  [WARN] V1/V1_gsgs_data/ not empty — {len(remaining)} file(s) remain:")
            for f in remaining:
                print(f"         {f.name}")

        try:
            v1_dir = root / "V1"
            v1_dir.rmdir()
            print(f"  [REMOVED]  Empty dir: V1/")
        except OSError:
            pass  # V1/ still has other contents (V1_alpha_data etc.), that's fine

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"  Moved     : {len(moved)}")
    print(f"  Skipped   : {len(skipped)}")
    print(f"  Conflicts : {len(conflicts)}")
    print(f"  Unknown   : {len(unknown)}")

    if unknown:
        print("\n  Files not in migration map (manual review needed):")
        for f in unknown:
            print(f"    - {f}")

    if conflicts:
        print("\n  Conflicts (file already exists at destination):")
        for f in conflicts:
            print(f"    - {f}")

    if dry_run:
        print("\n  [DRY RUN] No files were moved. Re-run without --dry-run to apply.")

    print("=" * 60)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Migrate V1_gsgs_data files into correct gsgs/ subfolders."
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Path to datasets/normalized/ directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview moves without touching any files"
    )

    args = parser.parse_args()

    migrate(Path(args.root), dry_run=args.dry_run)