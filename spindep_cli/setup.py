"""
SPINDEP Framework — setup.py
=============================

Installs the 'spin' terminal command globally.

QUICK INSTALL
─────────────
  cd spindep_framework
  pip install -e .

AFTER INSTALL — works from anywhere:
  spin run      --data ./my_datasets
  spin test     matter.csv antimatter.csv --plot
  spin validate --data ./my_datasets
  spin import   --from /data --coupling gAgA --potential V2 ...
  spin gaps     --data ./my_datasets
  spin atlas    --data ./my_datasets
  spin config   myrun.yaml
  spin batch    jobs.yaml
  spin info
"""

from setuptools import setup, find_packages
from pathlib import Path

long_desc = Path("README.md").read_text(encoding="utf-8") if Path("README.md").exists() else ""

setup(
    name="spindep_cli",
    version="1.0.0",
    description=(
        "SPINDEP: Spin-Dependent Exotic Interaction Constraint "
        "Analysis Pipeline for CPT symmetry tests"
    ),
    long_description=long_desc,
    long_description_content_type="text/markdown",
    author="Oyewo Temidayo Solomon",
    author_email="oyewodayo@gmail.com",
    url="https://github.com/oyewodayo/spindep_framework",
    license="MIT",

    # ── package discovery ────────────────────────────────────
    # Finds spindep/ package and all sub-packages
    packages=find_packages(),

    # ── Python version ────────────────────────────────────────
    python_requires=">=3.9",

    # ── required dependencies ────────────────────────────────
    install_requires=[
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "pandas>=2.0.0",
        "matplotlib>=3.7.0",
        "reportlab>=4.0.0",
        "Pillow>=9.0.0",
    ],

    # ── optional dependencies ────────────────────────────────
    extras_require={
        "yaml":  ["pyyaml>=6.0"],      # for spin config / spin batch
        "dev":   ["pytest", "black", "flake8"],
        "api":   ["fastapi>=0.136.0", "uvicorn>=0.47.0", "python-multipart>=0.0.32", "h5py>=3.16.0"],
        "full":  ["pyyaml>=6.0", "seaborn>=0.12.0", "fastapi>=0.136.0", "uvicorn>=0.47.0",
                  "python-multipart>=0.0.32", "h5py>=3.16.0"],
    },

    # ── THE KEY PART: register 'spin' as a terminal command ──
    # After pip install, typing 'spin' anywhere runs cli.main()
    entry_points={
        "console_scripts": [
            "spin = spindep_cli.cli:main",
        ],
    },

    # ── metadata ─────────────────────────────────────────────
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Physics",
        "Intended Audience :: Science/Research",
        "Development Status :: 4 - Beta",
    ],
    keywords=[
        "spin-dependent interactions",
        "CPT symmetry",
        "exotic forces",
        "Standard Model Extension",
        "matter-antimatter",
        "constraint analysis",
        "physics",
    ],
)