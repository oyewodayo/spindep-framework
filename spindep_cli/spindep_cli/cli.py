#!/usr/bin/env python3
# spindep_cli/cli.py
"""
SPINDEP 'spin' command — entry point registered by setup.py.

After   pip install -e .   this becomes the global 'spin' command.

USAGE
-----
  spin start     [--no-browser]             # Launch the web GUI (backend + frontend)
  spin run       --data ./datasets          # Full pipeline
  spin test      matter.csv anti.csv        # Quick CPT test on two files
  spin validate  --data ./datasets          # Pre-flight checks
  spin import    --from /data --coupling gAgA --potential V2 ...
  spin gaps      --data ./datasets          # Gap figures only
  spin atlas     --data ./datasets          # Constraint atlas only
  spin config    myconfig.yaml              # Run from a config file
  spin batch     jobs.yaml                  # Run multiple jobs
  spin info      --data ./datasets          # Framework status

For help on any command:
  spin <command> --help
"""

"""
SPINDEP Command-Line Interface
==============================

A single entry-point command that gives non-technical users full
access to the SPINDEP framework without touching any code.

USAGE
-----
# Full pipeline on a dataset folder:
  python spindep_cli.py run --data ./my_datasets

# Analyse just one pair of CSV files:
  python spindep_cli.py pair matter.csv antimatter.csv

# Import datasets from a different directory structure:
  python spindep_cli.py import --from /path/to/data --coupling gAgA --potential V2 --sector ee

# Run gap analysis only:
  python spindep_cli.py gaps --data ./my_datasets

# Run constraint atlas only:
  python spindep_cli.py atlas --data ./my_datasets

# Validate your dataset folder before a full run:
  python spindep_cli.py validate --data ./my_datasets

# Quick CPT test on two CSV files (no folder structure needed):
  python spindep_cli.py test matter.csv antimatter.csv --plot

INSTALL AS SYSTEM COMMAND
--------------------------
  # Linux / macOS — add alias to shell profile
  echo 'alias spindep="python3 /path/to/spindep_cli.py"' >> ~/.bashrc
  source ~/.bashrc
  spindep run --data ./my_datasets

  # Linux / macOS — make directly executable
  chmod +x spindep_cli.py
  ./spindep_cli.py run --data ./my_datasets

  # Windows — run via Python directly
  python spindep_cli.py run --data ./my_datasets
"""

import argparse
import sys
import os
import shutil
import textwrap
import json
import platform
import signal
import socket
import subprocess
import time
import webbrowser
from pathlib import Path
from datetime import datetime


# ============================================================
# TERMINAL COLOURS — safe on all platforms
# ============================================================

def _ansi_supported() -> bool:
    if not sys.stdout.isatty():
        return False
    if platform.system() == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass
        return bool(
            os.environ.get("WT_SESSION") or
            os.environ.get("TERM_PROGRAM") or
            os.environ.get("ANSICON") or
            os.environ.get("TERM")
        )
    return True


_USE_COLOR = _ansi_supported()


class C:
    BOLD    = "\033[1m"  if _USE_COLOR else ""
    GREEN   = "\033[92m" if _USE_COLOR else ""
    BLUE    = "\033[94m" if _USE_COLOR else ""
    YELLOW  = "\033[93m" if _USE_COLOR else ""
    RED     = "\033[91m" if _USE_COLOR else ""
    CYAN    = "\033[96m" if _USE_COLOR else ""
    MAGENTA = "\033[95m" if _USE_COLOR else ""
    RESET   = "\033[0m"  if _USE_COLOR else ""
    GREY    = "\033[90m" if _USE_COLOR else ""
    DIM     = "\033[2m"  if _USE_COLOR else ""


def ok(msg):    print(f"  {C.GREEN}[OK]{C.RESET}   {msg}")
def info(msg):  print(f"  {C.BLUE}[..]{C.RESET}   {msg}")
def warn(msg):  print(f"  {C.YELLOW}[!!]{C.RESET}   {msg}")
def err(msg):   print(f"  {C.RED}[ERR]{C.RESET}  {msg}", file=sys.stderr)
def grey(msg):  print(f"  {C.GREY}{msg}{C.RESET}")
def blank():    print()


def banner(title: str):
    width = 62
    print(f"\n{C.BOLD}{C.CYAN}{'─'*width}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {title}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'─'*width}{C.RESET}\n")


def section(title: str):
    print(f"\n{C.BOLD}  {title}{C.RESET}")
    print(f"  {'─' * (len(title) + 2)}")


# ============================================================
# SPINDEP CORE LOADER
# Resolves spindep regardless of where 'spin' is invoked
# ============================================================

def _find_core() -> "Path | None":
    """
    Search for the spindep/src directory in order of priority:
      1. Sibling package in a monorepo layout  (../spindep/src)
      2. Legacy in-tree src/                   (../src)
      3. SPINDEP_HOME environment variable
      4. Default install path under $HOME
      5. Current working directory
    """
    candidates = [
        # monorepo: spindep-cli/ sits next to spindep-core/
        Path(__file__).parent.parent.parent / "spindep" / "src",
        # legacy in-tree layout
        Path(__file__).parent.parent.parent / "spindep" / "src",
        Path(__file__).parent.parent.parent / "src",
        # env-var override
        Path(os.environ.get("SPINDEP_HOME", "")) / "src",
        # standard install
        Path.home() / "spindep_framework" / "spindep" / "src",
        Path.home() / "spindep_framework" / "spindep" / "src",
        # cwd fallbacks
        Path.cwd() / "spindep" / "src",
        Path.cwd() / "src",
    ]
    for c in candidates:
        if c.is_dir() and (c / "parser.py").exists():
            return c
    return None


def _find_project_root() -> "Path | None":
    """
    Locate the spindep_framework checkout (the folder containing both
    spindep_api/ and gui/), regardless of where 'spin' is invoked from.
    """
    candidates = [
        Path(__file__).parent.parent.parent,          # monorepo: spindep_cli/spindep_cli/cli.py -> root
        Path(os.environ.get("SPINDEP_HOME", "")).parent,
        Path.home() / "spindep_framework",
        Path.cwd(),
    ]
    for c in candidates:
        if c and (c / "spindep_api" / "server.py").exists() and (c / "gui").is_dir():
            return c
    return None


def _load() -> dict:
    """Import all SPINDEP core modules, auto-detecting the source location."""
    src = _find_core()
    if src is None:
        err("Cannot locate spindep source files (src/parser.py).")
        blank()
        grey("Try one of the following:")
        grey("  Linux/macOS:  export SPINDEP_HOME=/path/to/spindep")
        grey("  Windows CMD:  set SPINDEP_HOME=C:\\path\\to\\spindep")
        grey("  Windows PS:   $env:SPINDEP_HOME='C:\\...'")
        grey("  Or clone spindep next to spindep-cli and re-run.")
        sys.exit(1)

    root = src.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        from src.parser           import discover_datasets, load_dataset
        from src.matcher          import build_pairs
        from src.statistics       import chi_squared_from_datasets
        from src.unit_conversion  import convert_lambda_to_metres, audit_units
        from src.pipeline         import run_pipeline
        from src.gap_analysis     import run_gap_analysis
        from src.constraint_plots import run_constraint_plots
        return {k: v for k, v in locals().items() if not k.startswith("_")}
    except ImportError as e:
        err(f"Import failed: {e}")
        grey("  Make sure all spindep/src/*.py files are present.")
        sys.exit(1)


# ============================================================
# SHARED HELPERS
# ============================================================

def _resolve_data(data_arg: str) -> Path:
    """Return the normalized/ sub-directory if it exists, else data_arg itself."""
    p = Path(data_arg).resolve()
    if not p.exists():
        err(f"Path not found: {p}")
        sys.exit(1)
    if (p / "normalized").is_dir():
        return p / "normalized"
    return p


def _results_dir(output_arg: "str | None", data_path: Path) -> Path:
    if output_arg:
        return Path(output_arg).resolve()
    return data_path.parent.parent / "results"


def _print_pair_results(stats: dict, matter_name: str = "matter", anti_name: str = "antimatter"):
    """Pretty-print chi-squared results for a single pair."""
    import numpy as np
    section("CPT Asymmetry Results")

    lam   = stats["lam_grid"]
    valid = np.isfinite(stats["g_m"]) & np.isfinite(stats["g_a"])

    print(f"    Lambda overlap:        {lam[valid].min():.3e} -> {lam[valid].max():.3e} m")
    print(f"    Valid points:          {valid.sum()} / {len(lam)}")
    blank()

    A = stats["mean_abs_A"]
    print(f"    Mean |A_alpha|:        {C.BOLD}{A:.4f}{C.RESET}  ", end="")
    if A > 0.5:   print(f"{C.RED}Strong CPT-sensitive asymmetry{C.RESET}")
    elif A > 0.2: print(f"{C.YELLOW}Moderate asymmetry{C.RESET}")
    else:         print(f"{C.GREEN}Near-symmetric{C.RESET}")

    blank()
    print(f"    chi2 (uniform 10%):    {stats['chi2_uniform']:.1f}   dof={stats['dof_uniform']}")
    print(f"    chi2 (weighted):       {C.BOLD}{stats['chi2_weighted']:.1f}{C.RESET}   dof={stats['dof_weighted']}")

    p = stats["pval_weighted"]
    sig = (f"{C.RED}*** p < 0.001{C.RESET}" if p < 0.001 else
           f"{C.YELLOW}*   p < 0.05{C.RESET}"  if p < 0.05  else
           f"{C.GREEN}ns  p >= 0.05{C.RESET}")
    print(f"    p-value (weighted):    {p:.3e}  {sig}")

    blank()
    print(f"    sigma matter   (avg):  {stats['mean_sigma_m']*100:.1f}%  (from curve curvature)")
    print(f"    sigma antimatter (avg):{stats['mean_sigma_a']*100:.1f}%  (from curve curvature)")
    print(f"    chi2 ratio (w/u):      {stats['improvement']:.3f}  "
          f"{'<-- more conservative' if stats['improvement'] < 1 else ''}")


# ============================================================
# COMMAND: start  (launch backend API + web GUI together)
# ============================================================

BACKEND_PORT  = 8001
FRONTEND_PORT = 5173


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_port(host: str, port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open(host, port):
            return True
        time.sleep(0.5)
    return False


def _popen_detached(cmd: list, cwd: str) -> subprocess.Popen:
    """
    Launch a child in its own process group/session, so tools like
    'npm run dev' that spawn further children (vite, esbuild, ...) can be
    stopped as a unit instead of leaving orphans behind.
    """
    if platform.system() == "Windows":
        return subprocess.Popen(
            cmd, cwd=cwd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(cmd, cwd=cwd, start_new_session=True)


def _stop_process(proc: "subprocess.Popen | None"):
    if proc is None or proc.poll() is not None:
        return

    if platform.system() == "Windows":
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        except Exception:
            proc.terminate()
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError:
            proc.terminate()

    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if platform.system() == "Windows":
            proc.kill()
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                proc.kill()


def cmd_start(args):
    banner("SPINDEP  .  Start")

    root = _find_project_root()
    if root is None:
        err("Could not find the spindep_framework project "
            "(needs a spindep_api/ folder and a gui/ folder).")
        blank()
        grey("  Run 'spin start' from inside the cloned spindep_framework folder,")
        grey("  or set SPINDEP_HOME to point at it.")
        sys.exit(1)

    api_dir  = root / "spindep_api"
    gui_dir  = root / "gui"
    info(f"Project: {root}")
    blank()

    backend_proc = None
    frontend_proc = None

    # Treat SIGTERM/SIGHUP (e.g. a closed terminal, `kill`, or a process
    # manager stopping us) the same as Ctrl+C, so child processes are
    # always cleaned up instead of left running on the ports.
    def _handle_signal(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle_signal)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _handle_signal)

    try:
        # ── backend ──────────────────────────────────────────
        if _port_open("localhost", BACKEND_PORT):
            warn(f"Something is already listening on port {BACKEND_PORT} — "
                 "assuming the backend is already running.")
        else:
            info(f"Starting backend API on port {BACKEND_PORT}...")
            backend_proc = _popen_detached([sys.executable, "server.py"], cwd=str(api_dir))
            if not _wait_for_port("localhost", BACKEND_PORT, timeout=25):
                err(f"Backend did not come up on port {BACKEND_PORT} within 25s.")
                _stop_process(backend_proc)
                sys.exit(1)
            ok(f"Backend is up:  http://localhost:{BACKEND_PORT}")

        # ── frontend ─────────────────────────────────────────
        npm = shutil.which("npm")
        if npm is None:
            err("Node.js/npm not found — required to run the web interface.")
            grey("  Install Node.js (LTS) from https://nodejs.org, then re-run 'spin start'.")
            _stop_process(backend_proc)
            sys.exit(1)

        if not (gui_dir / "node_modules").is_dir():
            info("First run — installing web interface dependencies (one-time, ~1 min)...")
            install = subprocess.run([npm, "install"], cwd=str(gui_dir))
            if install.returncode != 0:
                err("npm install failed — see output above.")
                _stop_process(backend_proc)
                sys.exit(1)
            ok("Dependencies installed.")

        if _port_open("localhost", FRONTEND_PORT):
            warn(f"Something is already listening on port {FRONTEND_PORT} — "
                 "assuming the web interface is already running.")
        else:
            info(f"Starting web interface on port {FRONTEND_PORT}...")
            frontend_proc = _popen_detached(
                [npm, "run", "dev", "--", "--port", str(FRONTEND_PORT), "--strictPort"],
                cwd=str(gui_dir),
            )
            if not _wait_for_port("localhost", FRONTEND_PORT, timeout=30):
                err(f"Web interface did not come up on port {FRONTEND_PORT} within 30s.")
                _stop_process(frontend_proc)
                _stop_process(backend_proc)
                sys.exit(1)
            ok(f"Web interface is up:  http://localhost:{FRONTEND_PORT}")

        blank()
        if not args.no_browser:
            webbrowser.open(f"http://localhost:{FRONTEND_PORT}")

        ok("SPINDEP is running.")
        grey(f"    Web interface:  http://localhost:{FRONTEND_PORT}")
        grey(f"    Backend API:    http://localhost:{BACKEND_PORT}")
        blank()
        grey("  Press Ctrl+C to stop.")

        # Idle until either child process exits or the user hits Ctrl+C.
        while True:
            time.sleep(1)
            if backend_proc is not None and backend_proc.poll() is not None:
                err("Backend process exited unexpectedly.")
                break
            if frontend_proc is not None and frontend_proc.poll() is not None:
                err("Web interface process exited unexpectedly.")
                break

    except KeyboardInterrupt:
        blank()
        info("Stopping...")
    finally:
        _stop_process(frontend_proc)
        _stop_process(backend_proc)
        ok("Stopped.")


# ============================================================
# COMMAND: run
# ============================================================

def cmd_run(args):
    banner("SPINDEP  .  Full Pipeline")
    normalized   = _resolve_data(args.data)
    results_root = _results_dir(args.output, normalized)
    info(f"Data:    {normalized}")
    info(f"Results: {results_root}")
    blank()
    sp = _load()
    sp["run_pipeline"](dataset_root=str(normalized), results_root=str(results_root))
    blank()
    ok(f"Report:  {results_root / 'reports'}")
    ok(f"Figures: {results_root / 'figures'}")
    ok(f"Tables:  {results_root / 'tables'}")


# ============================================================
# COMMAND: test
# ============================================================

def cmd_test(args):
    import numpy as np
    banner("SPINDEP  .  Quick CPT Test")

    m_path = Path(args.matter).resolve()
    a_path = Path(args.antimatter).resolve()
    for p, label in [(m_path, "matter"), (a_path, "antimatter")]:
        if not p.exists():
            err(f"File not found ({label}): {p}")
            sys.exit(1)

    sp = _load()
    info(f"Matter:      {m_path.name}")
    info(f"Antimatter:  {a_path.name}")
    blank()

    df_m = sp["load_dataset"](m_path)
    df_a = sp["load_dataset"](a_path)
    df_m, _, unit_m = sp["convert_lambda_to_metres"](df_m, m_path.stem, verbose=False)
    df_a, _, unit_a = sp["convert_lambda_to_metres"](df_a, a_path.stem, verbose=False)

    info(f"Matter lambda:    {df_m['lambda_m'].min():.3e} -> {df_m['lambda_m'].max():.3e} m  [{unit_m}]")
    info(f"Antimatter lambda:{df_a['lambda_m'].min():.3e} -> {df_a['lambda_m'].max():.3e} m  [{unit_a}]")

    stats = sp["chi_squared_from_datasets"](df_m, df_a, n_points=args.points)
    if stats is None:
        blank()
        err("No overlapping lambda range.")
        warn("The two datasets probe different physical scales and cannot be compared.")
        grey("  Tip: check the lambda ranges above — they must share a common range.")
        sys.exit(0)

    _print_pair_results(stats, m_path.stem, a_path.stem)

    # ── optional plot ────────────────────────────────────────
    if args.plot is not None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            lam   = stats["lam_grid"]
            valid = np.isfinite(stats["g_m"]) & np.isfinite(stats["g_a"])
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

            ax1.plot(lam[valid], stats["g_m"][valid], "-",  color="#2d6a9f", lw=1.5,
                     label=f"Matter ({m_path.stem})")
            ax1.plot(lam[valid], stats["g_a"][valid], "--", color="#b03a2e", lw=1.5,
                     label=f"Antimatter ({a_path.stem})")
            ax1.set_yscale("log"); ax1.set_xscale("log")
            ax1.set_ylabel("Coupling upper bound |g|", fontsize=10)
            ax1.legend(fontsize=8); ax1.grid(True, which="both", ls=":", alpha=0.5)
            ax1.set_title(
                f"CPT Asymmetry Test  |  |Aa| = {stats['mean_abs_A']:.4f}  "
                f"|  chi2(w) = {stats['chi2_weighted']:.0f}",
                fontsize=10,
            )

            A = stats["A_alpha"]
            ax2.fill_between(lam[valid], A[valid], 0,
                             where=A[valid] > 0, color="#2d6a9f", alpha=0.3, label="Matter weaker")
            ax2.fill_between(lam[valid], A[valid], 0,
                             where=A[valid] < 0, color="#b03a2e", alpha=0.3, label="Antimatter weaker")
            ax2.axhline(0, color="black", lw=0.8, ls="--")
            ax2.set_ylim(-1.1, 1.1)
            ax2.set_ylabel("A_alpha", fontsize=10)
            ax2.set_xlabel("Interaction range lambda (m)", fontsize=10)
            ax2.legend(fontsize=8); ax2.grid(True, which="both", ls=":", alpha=0.5)

            plot_out = (Path(args.plot) if args.plot
                        else Path(f"spin_test_{m_path.stem}_vs_{a_path.stem}.png"))
            fig.tight_layout()
            fig.savefig(str(plot_out), dpi=150, bbox_inches="tight")
            plt.close(fig)
            blank()
            ok(f"Plot saved: {plot_out}")
        except ImportError:
            warn("matplotlib not installed — skipping plot")

    # ── optional CSV save ────────────────────────────────────
    if args.save:
        import pandas as pd
        lam   = stats["lam_grid"]
        valid = np.isfinite(stats["g_m"]) & np.isfinite(stats["g_a"])
        pd.DataFrame({
            "lambda_m":     lam[valid],
            "g_matter":     stats["g_m"][valid],
            "g_antimatter": stats["g_a"][valid],
            "A_alpha":      stats["A_alpha"][valid],
            "sigma_m_frac": stats["sigma_frac_m"][valid],
            "sigma_a_frac": stats["sigma_frac_a"][valid],
        }).to_csv(args.save, index=False)
        ok(f"Results CSV: {args.save}")


# ============================================================
# COMMAND: validate
# ============================================================

def cmd_validate(args):
    banner("SPINDEP  .  Dataset Validation")
    normalized = _resolve_data(args.data)
    info(f"Scanning: {normalized}")
    blank()

    sp = _load()
    datasets = sp["discover_datasets"](normalized)

    unknown_pot = [d for d in datasets if d.potential == "UNKNOWN"]
    unknown_sec = [d for d in datasets if d.sector    == "UNKNOWN"]
    antimatter  = [d for d in datasets if d.contains_antimatter]
    matter      = [d for d in datasets if not d.contains_antimatter]

    section("Dataset Inventory")
    ok(f"Total datasets:      {len(datasets)}")
    ok(f"Matter datasets:     {len(matter)}")
    ok(f"Antimatter datasets: {len(antimatter)}")

    if unknown_pot:
        warn(f"Unknown potential:   {len(unknown_pot)}  (will be excluded from pairing)")
        if args.verbose:
            for d in unknown_pot[:10]:
                grey(f"    {d.filename}")
    else:
        ok("All potentials recognised")

    if unknown_sec:
        warn(f"Unknown sector:      {len(unknown_sec)}  (will be excluded from pairing)")
        if args.verbose:
            for d in unknown_sec[:10]:
                grey(f"    {d.filename}")
    else:
        ok("All sectors recognised")

    blank()
    section("Unit Audit")
    sp["audit_units"](datasets, verbose=True)

    blank()
    section("Pair Matching Preview")
    pairs = sp["build_pairs"](datasets)
    if len(pairs) == 0:
        err("No valid pairs found.")
        blank()
        grey("  Checklist:")
        grey("  1. Matter and antimatter files are in the SAME coupling/ folder")
        grey("  2. Filenames encode the SAME potential token (e.g. both have V2)")
        grey("  3. Sectors are compatible (ee <-> eebar, ep <-> ebarpabr, etc.)")
        grey("  4. The interaction_class subfolder matches (lepton-lepton, etc.)")
    else:
        ok(f"Valid pairs found: {len(pairs)}")
        for m, a in pairs:
            print(f"    {C.BLUE}{m.source:<20}{C.RESET} x {C.RED}{a.source}{C.RESET}  "
                  f"[{m.coupling} . {m.potential} . {m.sector}]")


# ============================================================
# COMMAND: import
# ============================================================

def cmd_import(args):
    banner("SPINDEP  .  Import Datasets")

    src_dir   = Path(args.src).resolve()
    dest_base = Path(args.dest).resolve() if args.dest else Path("datasets") / "normalized"
    target    = dest_base / args.coupling / args.interaction_class
    target.mkdir(parents=True, exist_ok=True)

    if not src_dir.exists():
        err(f"Source not found: {src_dir}")
        sys.exit(1)

    csv_files = sorted(src_dir.rglob("*.csv"))
    if not csv_files:
        err(f"No CSV files found in {src_dir}")
        sys.exit(1)

    info(f"Found {len(csv_files)} CSV files")
    info(f"Target: {target}")
    blank()

    imported = []
    for f in csv_files:
        stem = f.stem
        if "_m_abs_" in stem or "_abs_" in stem:
            new_name = f.name
        else:
            is_anti = any(t in stem.lower() for t in ["anti", "bar", "plus", "positron", "pos"])
            sector  = args.sector_antimatter if is_anti else args.sector_matter
            new_name = f"{args.potential}_{stem}_m_abs_{sector}.csv"
            warn(f"Renamed: {f.name}  ->  {new_name}")

        dest_file = target / new_name
        shutil.copy2(str(f), str(dest_file))
        ok(f"Imported: {new_name}")
        imported.append(dest_file)

    blank()
    ok(f"Imported {len(imported)} files to {target}")

    if args.run:
        blank()
        info("Running pipeline on imported data...")
        sp = _load()
        results = dest_base.parent.parent / "results"
        sp["run_pipeline"](dataset_root=str(dest_base), results_root=str(results))


# ============================================================
# COMMAND: gaps
# ============================================================

def cmd_gaps(args):
    banner("SPINDEP  .  Gap Analysis")
    normalized = _resolve_data(args.data)
    out_dir    = Path(args.output).resolve() if args.output else normalized.parent.parent / "results" / "figures"
    sp = _load()
    datasets = sp["discover_datasets"](normalized)
    info(f"Loaded {len(datasets)} datasets")
    sp["run_gap_analysis"](datasets, figures_dir=out_dir)
    ok(f"Figures: {out_dir / 'gap_analysis'}")


# ============================================================
# COMMAND: atlas
# ============================================================

def cmd_atlas(args):
    banner("SPINDEP  .  Constraint Atlas")
    normalized = _resolve_data(args.data)
    out_dir    = Path(args.output).resolve() if args.output else normalized.parent.parent / "results" / "figures"
    sp = _load()
    datasets = sp["discover_datasets"](normalized)
    info(f"Loaded {len(datasets)} datasets")
    sp["run_constraint_plots"](
        datasets=datasets,
        summary_rows=[],
        plots_dir=normalized.parent.parent / "results" / "plots",
        figures_dir=out_dir,
    )
    ok(f"Atlas: {out_dir / 'constraint_atlas'}")


# ============================================================
# COMMAND: config  (run from a YAML or JSON config file)
# ============================================================

def cmd_config(args):
    banner("SPINDEP  .  Config-File Run")
    cfg_path = Path(args.config).resolve()
    if not cfg_path.exists():
        err(f"Config file not found: {cfg_path}")
        sys.exit(1)

    if cfg_path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            with open(cfg_path, encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh)
        except ImportError:
            err("PyYAML not installed.  Run: pip install pyyaml")
            sys.exit(1)
    else:
        with open(cfg_path, encoding="utf-8") as fh:
            cfg = json.load(fh)

    info(f"Config: {cfg_path.name}")
    blank()

    command = cfg.get("command", "run")

    if command == "run":
        data   = cfg.get("data")
        output = cfg.get("output")
        if not data:
            err("Config must specify 'data' field")
            sys.exit(1)
        normalized   = _resolve_data(data)
        results_root = Path(output).resolve() if output else normalized.parent.parent / "results"
        sp = _load()
        sp["run_pipeline"](dataset_root=str(normalized), results_root=str(results_root))

    elif command == "test":
        matter     = cfg.get("matter")
        antimatter = cfg.get("antimatter")
        if not matter or not antimatter:
            err("Config must specify 'matter' and 'antimatter' for test command")
            sys.exit(1)
        ns = argparse.Namespace(
            matter=matter, antimatter=antimatter,
            plot=cfg.get("plot"), save=cfg.get("save"),
            points=cfg.get("points", 300),
        )
        cmd_test(ns)

    elif command == "import":
        ns = argparse.Namespace(
            src=cfg["from"], dest=cfg.get("dest"),
            coupling=cfg["coupling"], potential=cfg["potential"],
            sector_matter=cfg["sector_matter"],
            sector_antimatter=cfg["sector_antimatter"],
            interaction_class=cfg.get("interaction_class", "lepton-lepton"),
            run=cfg.get("run", False),
        )
        cmd_import(ns)

    else:
        err(f"Unknown command in config: '{command}'")
        sys.exit(1)

    ok("Config run complete.")


# ============================================================
# COMMAND: batch  (run multiple jobs from one file)
# ============================================================

def cmd_batch(args):
    banner("SPINDEP  .  Batch Run")
    jobs_path = Path(args.jobs).resolve()
    if not jobs_path.exists():
        err(f"Jobs file not found: {jobs_path}")
        sys.exit(1)

    if jobs_path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            with open(jobs_path, encoding="utf-8") as fh:
                jobs = yaml.safe_load(fh)
        except ImportError:
            err("PyYAML not installed.  Run: pip install pyyaml")
            sys.exit(1)
    else:
        with open(jobs_path, encoding="utf-8") as fh:
            jobs = json.load(fh)

    if not isinstance(jobs, list):
        jobs = [jobs]

    info(f"Found {len(jobs)} job(s) in {jobs_path.name}")
    blank()

    import tempfile
    for i, job in enumerate(jobs, 1):
        print(f"{C.BOLD}{C.MAGENTA}  -- Job {i}/{len(jobs)}: {job.get('name', 'unnamed')} --{C.RESET}")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(job, tmp)
            tmp_path = tmp.name
        ns = argparse.Namespace(config=tmp_path)
        try:
            cmd_config(ns)
            ok(f"Job {i} complete")
        except SystemExit:
            err(f"Job {i} failed — continuing to next job")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        blank()


# ============================================================
# COMMAND: info  (show framework status)
# ============================================================

def cmd_info(args):
    banner("SPINDEP  .  Framework Info")
    src = _find_core()
    if src:
        ok(f"spindep: {src}")
    else:
        err("spindep not found")
        blank()
        grey("  Set SPINDEP_HOME to fix this.")

    section("Python Environment")
    ok(f"Python:   {sys.version.split()[0]}  ({platform.system()} {platform.machine()})")
    ok(f"Prefix:   {sys.prefix}")

    section("Dependencies")
    deps = ["numpy", "scipy", "pandas", "matplotlib", "reportlab", "PIL", "yaml"]
    for dep in deps:
        real = "Pillow" if dep == "PIL" else ("PyYAML" if dep == "yaml" else dep)
        try:
            mod = __import__(dep)
            ver = getattr(mod, "__version__", "installed")
            ok(f"{real:<15} {ver}")
        except ImportError:
            warn(f"{real:<15} NOT installed  (pip install {real})")

    if args.data:
        blank()
        section("Dataset Summary")
        try:
            normalized = _resolve_data(args.data)
            sp = _load()
            datasets = sp["discover_datasets"](normalized)
            pairs    = sp["build_pairs"](datasets)
            info(f"Datasets:  {len(datasets)}")
            info(f"Pairs:     {len(pairs)}")
        except Exception as exc:
            warn(f"Could not load datasets: {exc}")


# ============================================================
# MAIN ARGUMENT PARSER
# ============================================================

EPILOG = f"""
{C.BOLD}Examples:{C.RESET}
  {C.CYAN}spin start{C.RESET}
      Launch the web interface (backend + frontend) and open it in your browser.

  {C.CYAN}spin run   --data ./datasets{C.RESET}
      Full pipeline on your dataset folder.

  {C.CYAN}spin test  matter.csv antimatter.csv --plot{C.RESET}
      Quick CPT test, saves a plot.

  {C.CYAN}spin test  e_bounds.csv eplus_bounds.csv --save results.csv{C.RESET}
      Test and export full results table.

  {C.CYAN}spin validate --data ./datasets{C.RESET}
      Check structure before a full run.

  {C.CYAN}spin import --from /data/new --coupling gAgA --potential V2 \\{C.RESET}
  {C.CYAN}            --sector-matter ee --sector-antimatter eebar --run{C.RESET}
      Import files and run immediately.

  {C.CYAN}spin config  myrun.yaml{C.RESET}
      Run from a config file (no flags needed).

  {C.CYAN}spin batch   jobs.yaml{C.RESET}
      Run multiple analyses from one file.

  {C.CYAN}spin info   --data ./datasets{C.RESET}
      Show framework status and dataset summary.
"""


def main():
    parser = argparse.ArgumentParser(
        prog="spin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            f"{C.BOLD}{C.CYAN}SPINDEP — Spin-Dependent Exotic Interaction Analysis{C.RESET}\n"
            "  CPT symmetry tests via matter-antimatter constraint comparison."
            "  Analyse matter-antimatter CPT asymmetry in exotic spin-dependent"
            "  interactions from published experimental constraint datasets."
            f"{C.BOLD}Quick start:{C.RESET}"
            f"  spindep run      --data ./my_datasets"
            f"  spindep test     matter.csv antimatter.csv --plot"
            f"  spindep validate --data ./my_datasets"
        ),
        epilog=EPILOG,
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ── start ────────────────────────────────────────────────
    p = sub.add_parser("start",
        help="Launch the web GUI (backend + frontend) in your browser",
        description="Start the backend API and the web interface together, "
                    "then open it in your default browser.\n\n"
                    "Example:\n  spin start")
    p.add_argument("--no-browser", action="store_true",
        help="Don't automatically open a browser tab")

    # ── run ──────────────────────────────────────────────────
    p = sub.add_parser("run",
        help="Full pipeline: discover -> analyse -> report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Run the complete SPINDEP analysis pipeline.\n\nExample:\n  spin run --data ./datasets")
    p.add_argument("--data",   required=True, metavar="DIR",
        help="Dataset folder (containing normalized/ or CSV files)")
    p.add_argument("--output", metavar="DIR",
        help="Results output folder (default: <data>/../results)")

    # ── test ─────────────────────────────────────────────────
    p = sub.add_parser("test",
        help="Quick CPT test on two CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Perform a CPT asymmetry test between two CSV files.\n"
                    "No folder structure required.\n\nExample:\n  spin test matter.csv antimatter.csv --plot")
    p.add_argument("matter",     metavar="MATTER.CSV",
        help="Matter sector CSV (lambda, coupling_bound)")
    p.add_argument("antimatter", metavar="ANTIMATTER.CSV",
        help="Antimatter sector CSV (lambda, coupling_bound)")
    p.add_argument("--plot", metavar="FILE.PNG", nargs="?", const="",
        help="Save asymmetry plot (default filename if no path given)")
    p.add_argument("--save", metavar="FILE.CSV",
        help="Export full results table as CSV")
    p.add_argument("--points", type=int, default=300, metavar="N",
        help="Lambda grid resolution (default: 300)")

    # ── validate ─────────────────────────────────────────────
    p = sub.add_parser("validate",
        help="Pre-flight checks on dataset folder",
        description="Validate dataset structure, names, units, and pairing.\n\n"
                    "Example:\n  spin validate --data ./datasets")
    p.add_argument("--data",    required=True, metavar="DIR")
    p.add_argument("--verbose", action="store_true",
        help="Show all unrecognised files")

    # ── import ───────────────────────────────────────────────
    p = sub.add_parser("import",
        help="Import CSV files from any folder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Copy external CSV files into the SPINDEP structure.\n\n"
                    "Example:\n  spin import --from /data --coupling gAgA "
                    "--potential V2 \\\n             --sector-matter ee "
                    "--sector-antimatter eebar --run")
    p.add_argument("--from", dest="src", required=True, metavar="DIR",
        help="Folder containing CSV files to import")
    p.add_argument("--dest", metavar="DIR",
        help="SPINDEP datasets root (default: datasets/normalized)")
    p.add_argument("--coupling",          required=True, metavar="NAME",
        help="Coupling type: gAgA | gsgs | gVgV | gpgp | gpgs")
    p.add_argument("--potential",         required=True, metavar="Vi",
        help="Potential: V2 | V3 | V11 | V4+5 | etc.")
    p.add_argument("--sector-matter",     required=True, metavar="SECTOR",
        help="Matter sector: ee | ep | en | nn | nN | eN ...")
    p.add_argument("--sector-antimatter", required=True, metavar="SECTOR",
        help="Antimatter sector: eebar | epbar | enbar | nnbar ...")
    p.add_argument("--interaction-class", default="lepton-lepton", metavar="CLASS",
        help="Subfolder: lepton-lepton | lepton-nucleon | nucleon-nucleon")
    p.add_argument("--run", action="store_true",
        help="Run full pipeline immediately after import")

    # ── gaps ─────────────────────────────────────────────────
    p = sub.add_parser("gaps", help="Gap analysis figures only",
        description="Generate the three gap analysis figures.\n\nExample:\n  spin gaps --data ./datasets")
    p.add_argument("--data",   required=True, metavar="DIR")
    p.add_argument("--output", metavar="DIR",
        help="Output folder (default: results/figures)")

    # ── atlas ────────────────────────────────────────────────
    p = sub.add_parser("atlas", help="Constraint atlas figures only",
        description="Generate constraint atlas plots.\n\nExample:\n  spin atlas --data ./datasets")
    p.add_argument("--data",   required=True, metavar="DIR")
    p.add_argument("--output", metavar="DIR",
        help="Output folder (default: results/figures)")

    # ── config ───────────────────────────────────────────────
    p = sub.add_parser("config", help="Run from a YAML or JSON config file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Run SPINDEP from a configuration file.\n\n"
                    "Example YAML:\n"
                    "  command: run\n"
                    "  data: ./datasets\n"
                    "  output: ./results\n\n"
                    "Example:\n  spin config myrun.yaml")
    p.add_argument("config", metavar="CONFIG.yaml",
        help="Path to YAML or JSON config file")

    # ── batch ────────────────────────────────────────────────
    p = sub.add_parser("batch", help="Run multiple jobs from one YAML/JSON file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Run multiple SPINDEP analyses from one jobs file.\n\n"
                    "Example:\n  spin batch jobs.yaml")
    p.add_argument("jobs", metavar="JOBS.yaml",
        help="Path to YAML or JSON jobs file (list of job configs)")

    # ── info ─────────────────────────────────────────────────
    p = sub.add_parser("info", help="Show framework status and dependency versions",
        description="Display SPINDEP installation info.\n\nExample:\n  spin info --data ./datasets")
    p.add_argument("--data", metavar="DIR",
        help="Optional: show dataset summary for this folder")

    # ── dispatch ─────────────────────────────────────────────
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    {
        "start":    cmd_start,
        "run":      cmd_run,
        "test":     cmd_test,
        "validate": cmd_validate,
        "import":   cmd_import,
        "gaps":     cmd_gaps,
        "atlas":    cmd_atlas,
        "config":   cmd_config,
        "batch":    cmd_batch,
        "info":     cmd_info,
    }[args.command](args)


if __name__ == "__main__":
    main()