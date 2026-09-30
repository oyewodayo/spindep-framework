"""Tests for the balanced-interval search in scripts/sensitivity_ratio.py."""

import importlib.util
from pathlib import Path

import numpy as np

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sensitivity_ratio.py"
_spec = importlib.util.spec_from_file_location("sensitivity_ratio", _SCRIPT)
sensitivity_ratio = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sensitivity_ratio)
balanced_intervals = sensitivity_ratio.balanced_intervals


def test_single_interior_interval():
    lam = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    G = np.array([2.0, 0.1, 0.2, 2.0, 2.0])
    assert balanced_intervals(lam, G, eps=0.5) == [(2.0, 3.0)]


def test_interval_running_to_the_end_of_the_grid():
    lam = np.array([1.0, 2.0, 3.0])
    G = np.array([2.0, 0.1, 0.1])
    assert balanced_intervals(lam, G, eps=0.5) == [(2.0, 3.0)]


def test_two_separate_intervals_and_none():
    lam = np.arange(1.0, 7.0)
    G = np.array([0.1, 2.0, 2.0, 0.1, 0.1, 2.0])
    assert balanced_intervals(lam, G, eps=0.5) == [(1.0, 1.0), (4.0, 5.0)]
    assert balanced_intervals(lam, np.full(6, 3.0), eps=0.5) == []


def test_equal_limits_are_balanced_everywhere():
    lam = np.logspace(-10, -8, 50)
    G = np.abs(np.log(np.ones(50)))
    assert balanced_intervals(lam, G, eps=np.log(2)) == [(lam[0], lam[-1])]
