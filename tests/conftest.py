"""
Shared fixtures for the SPINDEP test suite.

Mirrors the sys.path setup that production code (spindep_cli/cli.py and
spindep_api/server.py) already uses: insert spindep/ (the parent of the
namespace package src/) onto sys.path, then `import src.<module>`. Tests
import the exact same way, so they exercise the real import path rather
than a parallel test-only package layout.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT    = Path(__file__).resolve().parent.parent
SPINDEP_ROOT = REPO_ROOT / "spindep"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

if str(SPINDEP_ROOT) not in sys.path:
    sys.path.insert(0, str(SPINDEP_ROOT))


@pytest.fixture
def real_fixtures_dir():
    return FIXTURES_DIR / "real"


def _write_csv(path, lam, g):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{l:.10e},{gg:.10e}" for l, gg in zip(lam, g)]
    path.write_text("\n".join(lines) + "\n")


@pytest.fixture
def matter_antimatter_csv_pair(tmp_path):
    """
    A synthetic matter/antimatter CSV pair with a constant, hand-computable
    asymmetry: g_a = 2 * g_m everywhere, so A_alpha = (g_m-g_a)/(g_m+g_a)
    = -1/3 at every point in the overlap. Used to regression-test the
    statistics pipeline against a known-correct answer, not just "did it
    run without crashing".
    """
    lam = np.logspace(-9, -6, 25)
    g_m = 1e-10 * (lam / 1e-8) ** -0.5
    g_a = 2.0 * g_m
    m_path = tmp_path / "matter.csv"
    a_path = tmp_path / "antimatter.csv"
    _write_csv(m_path, lam, g_m)
    _write_csv(a_path, lam, g_a)
    return m_path, a_path


@pytest.fixture
def non_overlapping_csv_pair(tmp_path):
    """Matter and antimatter curves whose lambda ranges never overlap."""
    lam_m = np.logspace(-12, -10, 15)
    lam_a = np.logspace(-6, -4, 15)
    g_m = 1e-10 * (lam_m / 1e-11) ** -0.5
    g_a = 1e-10 * (lam_a / 1e-5) ** -0.5
    m_path = tmp_path / "matter_no_overlap.csv"
    a_path = tmp_path / "antimatter_no_overlap.csv"
    _write_csv(m_path, lam_m, g_m)
    _write_csv(a_path, lam_a, g_a)
    return m_path, a_path


@pytest.fixture
def tmp_dataset_dir(tmp_path, matter_antimatter_csv_pair):
    """
    A tiny synthetic datasets/normalized/<coupling>/<class>/ tree containing
    exactly one valid matter/antimatter pair (gAgA / V2 / lepton-lepton /
    ee <-> eebar), mirroring the real on-disk layout parser.py expects.
    """
    m_src, a_src = matter_antimatter_csv_pair
    root = tmp_path / "dataset_root" / "normalized" / "gAgA" / "lepton-lepton"
    root.mkdir(parents=True)
    m_dst = root / "2TestAuthor2024_m_abs_ee.csv"
    a_dst = root / "2TestAuthor2024_m_abs_ebare.csv"
    m_dst.write_text(m_src.read_text())
    a_dst.write_text(a_src.read_text())
    return tmp_path / "dataset_root"


def _make_constraint_dataset(**overrides):
    """Build a ConstraintDataset for unit-level tests that don't need
    real files on disk (e.g. matcher.py tests)."""
    from src.parser import ConstraintDataset
    defaults = dict(
        filepath=Path("dummy.csv"),
        filename="dummy",
        coupling="gAgA",
        interaction_class="lepton-lepton",
        potential="V2",
        source="Test2024",
        sector="ee",
        contains_antimatter=False,
        label="Test2024 (e-e)",
    )
    defaults.update(overrides)
    return ConstraintDataset(**defaults)


@pytest.fixture
def make_dataset():
    """Factory fixture: make_dataset(sector="ee", contains_antimatter=True, ...)."""
    return _make_constraint_dataset
