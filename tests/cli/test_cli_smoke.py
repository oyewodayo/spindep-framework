"""
Smoke tests for the 'spin' CLI. These invoke the installed console script
as a real subprocess (not by importing cli.py) so they exercise exactly
what a user gets after `pip install -e .` — including the source-location
auto-detection in cli.py's _find_core().

Kept intentionally small: this is a smoke layer on top of the core-engine
unit tests elsewhere in tests/core/, not a re-test of argument parsing.
"""
import shutil
import subprocess
import sys

import pytest

SPIN = shutil.which("spin")

pytestmark = pytest.mark.skipif(
    SPIN is None, reason="'spin' console script not found on PATH"
)


def _run(*args, timeout=60):
    return subprocess.run(
        [SPIN, *args], capture_output=True, text=True, timeout=timeout
    )


def test_spin_info_runs_successfully():
    result = _run("info")
    assert result.returncode == 0
    assert "Framework Info" in result.stdout
    assert "Python:" in result.stdout


def test_spin_validate_reports_dataset_and_pair_counts(tmp_dataset_dir):
    result = _run("validate", "--data", str(tmp_dataset_dir / "normalized"))
    assert result.returncode == 0
    assert "Total datasets:" in result.stdout
    assert "Valid pairs found: 1" in result.stdout


def test_spin_test_quick_cpt_check(matter_antimatter_csv_pair):
    m_path, a_path = matter_antimatter_csv_pair
    result = _run("test", str(m_path), str(a_path))
    assert result.returncode == 0
    assert "CPT Asymmetry Results" in result.stdout
    assert "Mean |A_alpha|:" in result.stdout


def test_spin_test_missing_file_exits_nonzero(tmp_path):
    missing = tmp_path / "does_not_exist.csv"
    result = _run("test", str(missing), str(missing))
    assert result.returncode != 0
    assert "File not found" in result.stderr


def test_spin_with_no_command_prints_help_and_exits_zero():
    result = _run()
    assert result.returncode == 0
    assert "SPINDEP" in result.stdout
