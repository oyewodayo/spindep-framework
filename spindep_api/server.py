# server.py  — FastAPI bridge between GUI and spindep pipeline
#!/usr/bin/env python3
import re

from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, uuid, json, sys, logging
from pathlib import Path
import shutil
from fastapi import UploadFile, File
from typing import List


logger = logging.getLogger("spindep.server")
logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

jobs = {}

# Populated by _run_pipeline; keys are pair_id strings (GUI format).
# Values are (df_matter, df_antimatter) — ready for run_null_test().
_PAIR_DATASET_CACHE: dict[str, tuple] = {}

DATA_ROOT    = Path.home() / "spindep_framework" / "spindep" / "datasets" / "normalized"
RESULTS_ROOT = Path.home() / "spindep_framework" / "spindep" / "results"

_SPINDEP_ROOT = Path.home() / "spindep_framework" / "spindep"
if str(_SPINDEP_ROOT) not in sys.path:
    sys.path.insert(0, str(_SPINDEP_ROOT))

from src.null_test import run_null_test
from src.parser import parse_dataset, FERMION_MAP, ANTIMATTER_SECTORS

# ─── Dataset loader ───────────────────────────────────────────────────────────

def _pair_id_from_datasets(matter_ds, antimatter_ds) -> str:
    """
    Reconstruct the GUI pair_id string exactly as pipeline.py builds it:
        f"{coupling}·{potential}·{secM}×{secA}"
    """
    return (
        f"{matter_ds.coupling}"
        f"\u00b7{matter_ds.potential}"          # ·
        f"\u00b7{matter_ds.sector}"             # ·
        f"\u00d7{antimatter_ds.sector}"         # ×
    )

def _warm_dataset_cache() -> None:
    from src.parser import discover_datasets, load_dataset
    from src.matcher import build_pairs
    from src.unit_conversion import convert_lambda_to_metres
    from src.statistics import chi_squared_from_datasets

    try:
        datasets = discover_datasets(DATA_ROOT)
        pairs    = build_pairs(datasets)
        count    = 0

        for matter_ds, antimatter_ds in pairs:
            pid = _pair_id_from_datasets(matter_ds, antimatter_ds)

            # Skip if already cached
            if pid in _PAIR_DATASET_CACHE:
                continue

            # Load + convert units exactly as the pipeline does
            df_m = load_dataset(matter_ds.filepath)
            df_a = load_dataset(antimatter_ds.filepath)
            df_m, _, _ = convert_lambda_to_metres(df_m, matter_ds.filename, verbose=False)
            df_a, _, _ = convert_lambda_to_metres(df_a, antimatter_ds.filename, verbose=False)

            # Only cache pairs that actually have lambda overlap
            # (mirrors pipeline.py's `if stats is None: continue`)
            stats = chi_squared_from_datasets(df_m, df_a, n_points=50)  # cheap check
            if stats is None:
                logger.debug("Cache skip (no overlap): %s  [%s × %s]",
                             pid, matter_ds.filename, antimatter_ds.filename)
                continue

            # Multiple matter files may share the same pair_id — keep the
            # one with the widest overlap (largest lambda range), matching
            # what the pipeline would have used for its gui_pairs entry.
            existing = _PAIR_DATASET_CACHE.get(pid)
            if existing is not None:
                _, existing_a = existing
                new_range = stats["lam_grid"].max() - stats["lam_grid"].min()
                # Re-check existing pair's range
                existing_stats = chi_squared_from_datasets(existing[0], existing[1], n_points=50)
                existing_range = (existing_stats["lam_grid"].max() - existing_stats["lam_grid"].min()
                                  if existing_stats else 0)
                if new_range <= existing_range:
                    continue  # keep the wider one already cached

            _PAIR_DATASET_CACHE[pid] = (df_m, df_a)
            count += 1
            logger.info("Cached: %s  [%s × %s]", pid, matter_ds.filename, antimatter_ds.filename)

        logger.info("Dataset cache warmed: %d pairs added (%d total)",
                    count, len(_PAIR_DATASET_CACHE))
    except Exception:
        logger.exception("Cache warming failed")

def _load_pair_datasets_for_null_test(pair_id: str):
    """
    Return (df_matter, df_antimatter) for the given GUI pair_id.

    Fast path: in-memory cache (populated after each pipeline run).
    Slow path: re-discover + re-match from DATA_ROOT (works after server restart).
    """
    # ── 1. Cache hit ──────────────────────────────────────────────────────────
    if pair_id in _PAIR_DATASET_CACHE:
        return _PAIR_DATASET_CACHE[pair_id]

    logger.info("Cache miss for %r — warming from DATA_ROOT", pair_id)
    _warm_dataset_cache()

    # ── 2. Cache miss after warming ──────────────────────────────────────────
    if pair_id in _PAIR_DATASET_CACHE:
        return _PAIR_DATASET_CACHE[pair_id]

    # ── 3. Still not found — error out (probably invalid pair_id or no pipeline run yet) ──
    raise ValueError(
        f"Pair {pair_id!r} not found after scanning {DATA_ROOT}. "
        "Run the pipeline at least once, or verify the pair_id is valid."
    )


# ─── Existing routes ──────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/tree")
def get_tree():
    def walk(path: Path) -> dict:
        node = {"name": path.name, "type": "folder", "children": []}
        for child in sorted(path.iterdir()):
            if child.is_dir():
                node["children"].append(walk(child))
            elif child.suffix == ".csv":
                node["children"].append({"name": child.name, "type": "file"})
        return node

    if not DATA_ROOT.exists():
        return {"name": "datasets/normalized", "type": "folder", "children": [], "error": "not found"}
    root = walk(DATA_ROOT)
    root["name"] = "datasets/normalized"
    return root


@app.post("/api/run")
async def run(background_tasks: BackgroundTasks, mode: str = "full"):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "log": [], "results": None}
    background_tasks.add_task(_run_pipeline, job_id, mode)
    return {"job_id": job_id}


@app.get("/api/job/{job_id}")
def get_job(job_id: str):
    j = jobs.get(job_id, {"status": "not_found"})
    return {"status": j["status"], "log": j["log"]}


@app.get("/api/results/{job_id}")
def get_results(job_id: str):
    j = jobs.get(job_id)
    if not j or not j["results"]:
        return {"error": "not ready"}
    return j["results"]


# ─── Pipeline runner ──────────────────────────────────────────────────────────

def _run_pipeline(job_id: str, mode: str):
    import traceback
    json_path = f"/tmp/spindep_{job_id}.json"
    try:
        from src.pipeline import run_pipeline

        jobs[job_id]["log"].append("[..] Starting pipeline...")
        run_pipeline(
            dataset_root=str(DATA_ROOT),
            results_root=str(RESULTS_ROOT),
            json_out=json_path,
        )
        if Path(json_path).exists():
            with open(json_path) as f:
                jobs[job_id]["results"] = json.load(f)
            jobs[job_id]["status"] = "done"
            jobs[job_id]["log"].append("[OK] Pipeline complete")
            # Warm cache so null tests are instant after a run
            _warm_dataset_cache()
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["log"].append("[ERR] No output JSON produced")
    except Exception:
        jobs[job_id]["status"] = "error"
        for line in traceback.format_exc().splitlines():
            jobs[job_id]["log"].append(f"[ERR] {line}")


# ─── Null test routes ─────────────────────────────────────────────────────────

@app.post("/api/null_test")
async def api_null_test(request: Request):
    body    = await request.json()
    pair_id = body.get("pair_id", "")
    aalpha  = float(body.get("injected_aalpha", 0.0))
    mode    = body.get("injection_mode", "scale")
    seed    = int(body.get("seed", 42))
    label   = body.get("label", None)

    try:
        df_matter, df_antimatter = _load_pair_datasets_for_null_test(pair_id)
        result = run_null_test(
            pair_id         = pair_id,
            df_matter       = df_matter,
            df_antimatter   = df_antimatter,
            injected_aalpha = aalpha,
            injection_mode  = mode,
            seed            = seed,
            label           = label,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("null_test failed for pair=%r", pair_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/null_test/{job_id}")
def api_null_test_result(job_id: str):
    raise HTTPException(status_code=404, detail="async polling not yet implemented")

def _infer_from_filename(filename: str) -> dict:
    """
    Parse coupling, interaction_class, and sector directly from the filename.
    e.g. V2_Fadeev2022_ee_gAgA.csv → coupling=gAgA, class=lepton-lepton, sector=ee
    
    Strategy: the coupling token is the LAST underscore-separated part (before .csv).
    The sector token is identified by cross-referencing KNOWN_SECTORS / SECTOR_ALIASES.
    """
    from src.parser import (
        extract_sector, normalize_sector, KNOWN_SECTORS,
        SECTOR_ALIASES, FERMION_MAP
    )

    stem   = Path(filename).stem                    # V2_Fadeev2022_ee_gAgA
    parts  = stem.split("_")                        # ['V2', 'Fadeev2022', 'ee', 'gAgA']

    # ── Coupling: last token that looks like a coupling name ──────────────────
    # Coupling tokens are typically camelCase with repeated letters: gAgA, gsgs, gVgV
    coupling = "unknown"
    for p in reversed(parts):
        if re.match(r"^g[A-Za-z]{1,4}$", p) or re.match(r"^g[A-Z][a-z][A-Z]$", p):
            coupling = p
            break
    # Fallback: last part that isn't a year, potential, or sector
    if coupling == "unknown" and parts:
        coupling = parts[-1]

    # ── Sector: scan all parts against known sectors / aliases ────────────────
    sector = "unknown"
    for p in parts:
        normalised = normalize_sector(p)
        if normalised in KNOWN_SECTORS or normalised in FERMION_MAP:
            sector = normalised
            break

    # ── Interaction class from sector ─────────────────────────────────────────
    interaction_class = _infer_interaction_class(sector)

    return {
        "coupling":          coupling,
        "sector":            sector,
        "interaction_class": interaction_class,
    }


def _infer_interaction_class(sector: str) -> str:
    lepton_lepton   = {"ee","eebar","emu","emubar","mumu","mumubar"}
    lepton_nucleon  = {"ep","epbar","en","enbar","np","npbar","eN","eNbar","muN"}
    nucleon_nucleon = {"nn","nnbar","pp","ppbar"}
    if sector in lepton_lepton:   return "lepton-lepton"
    if sector in lepton_nucleon:  return "lepton-nucleon"
    if sector in nucleon_nucleon: return "nucleon-nucleon"
    return "unknown"


@app.post("/api/upload")
async def upload_datasets(files: List[UploadFile] = File(...)):
    import pandas as pd, io
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    saved, warnings, suggestions = [], [], []

    for f in files:
        if not f.filename or not f.filename.endswith(".csv"):
            warnings.append(f"{f.filename}: skipped (not a .csv)")
            continue

        content = await f.read()

        # ── Infer structure directly from filename (not folder path) ──────────
        inferred = _infer_from_filename(f.filename)
        coupling          = inferred["coupling"]
        interaction_class = inferred["interaction_class"]
        sector            = inferred["sector"]

        suggested_dir  = DATA_ROOT / coupling / interaction_class
        suggested_path = suggested_dir / f.filename

        # ── Save flat into DATA_ROOT root for now ─────────────────────────────
        dest = DATA_ROOT / f.filename
        dest.write_bytes(content)

        # ── Column check ──────────────────────────────────────────────────────
        try:
            df       = pd.read_csv(io.BytesIO(content), nrows=2)
            required = {"lambda_m", "coupling_abs"}
            missing  = required - set(df.columns)
            if missing:
                warnings.append(
                    f"{f.filename}: saved but missing columns {missing} "
                    f"— found: {list(df.columns)}"
                )
        except Exception as e:
            warnings.append(f"{f.filename}: saved but could not validate ({e})")

        saved.append(f.filename)

        # Only suggest if we inferred something useful
        if coupling != "unknown":
            suggestions.append({
                "filename":          f.filename,
                "coupling":          coupling,
                "interaction_class": interaction_class,
                "sector":            sector,
                "suggested_path":    f"normalized/{coupling}/{interaction_class}/{f.filename}",
                "suggested_dir":     str(suggested_dir),
            })

        logger.info("Uploaded: %s → inferred coupling=%s class=%s sector=%s",
                    f.filename, coupling, interaction_class, sector)

    _PAIR_DATASET_CACHE.clear()
    return {"saved": saved, "warnings": warnings, "suggestions": suggestions}


@app.post("/api/organize")
async def organize_dataset(request: Request):
    """
    Move an uploaded file from its current location (anywhere under DATA_ROOT)
    into DATA_ROOT/{coupling}/{interaction_class}/{filename}.
    Body: { filename, coupling, interaction_class }
    """
    body              = await request.json()
    filename          = body["filename"]
    coupling          = body["coupling"]
    interaction_class = body["interaction_class"]

    # Find the file — it may be flat in DATA_ROOT or already partially moved
    src = DATA_ROOT / filename
    if not src.exists():
        # Search recursively in case it's somewhere else under DATA_ROOT
        matches = list(DATA_ROOT.rglob(filename))
        if not matches:
            raise HTTPException(status_code=404, detail=f"{filename} not found under DATA_ROOT")
        src = matches[0]

    dest_dir = DATA_ROOT / coupling / interaction_class
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    if src == dest:
        return {"moved_to": str(dest.relative_to(DATA_ROOT.parent)), "already_correct": True}

    shutil.move(str(src), str(dest))
    _PAIR_DATASET_CACHE.clear()
    logger.info("Organized: %s → %s/%s/%s", filename, coupling, interaction_class, filename)
    return {
        "moved_to": f"normalized/{coupling}/{interaction_class}/{filename}",
        "coupling": coupling,
        "interaction_class": interaction_class,
    }


@app.delete("/api/datasets/{filename:path}")
def delete_dataset(filename: str):
    """
    Delete a file OR folder by relative path under DATA_ROOT.
    filename can include subdirs: gAgA/lepton-lepton/V2_Fadeev2022_ee_gAgA.csv
    or just a folder: gAgA/lepton-lepton/jfoEF
    """
    target = DATA_ROOT / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found")

    if target.is_dir():
        shutil.rmtree(target)          # ← handles folders recursively
        logger.info("Deleted folder: %s", target)
    else:
        target.unlink()                # ← files as before
        logger.info("Deleted file: %s", target)

    _PAIR_DATASET_CACHE.clear()
    return {"deleted": filename}


@app.post("/api/datasets/folder")
async def create_folder(request: Request):
    """
    Create a subfolder under DATA_ROOT.
    Body: { path }  e.g. { "path": "gAgA/lepton-lepton" }
    """
    body        = await request.json()
    folder_path = body.get("path", "").strip("/")
    if not folder_path:
        raise HTTPException(status_code=400, detail="path is required")
    target = DATA_ROOT / folder_path
    target.mkdir(parents=True, exist_ok=True)
    logger.info("Created folder: %s", target)
    return {"created": folder_path}


@app.put("/api/datasets/rename")
async def rename_item(request: Request):
    """
    Rename/move a file or folder under DATA_ROOT.
    Body: { old_path, new_path }
    """
    body     = await request.json()
    old_path = DATA_ROOT / body["old_path"].strip("/")
    new_path = DATA_ROOT / body["new_path"].strip("/")
    if not old_path.exists():
        raise HTTPException(status_code=404, detail=f"{body['old_path']} not found")
    new_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old_path), str(new_path))
    _PAIR_DATASET_CACHE.clear()
    logger.info("Renamed: %s → %s", old_path, new_path)
    return {"renamed_to": body["new_path"]}

@app.get("/api/datasets/folders")
def list_folders():
    """Return all subdirectory paths under DATA_ROOT for the move picker."""
    if not DATA_ROOT.exists():
        return {"folders": []}
    folders = []
    for p in sorted(DATA_ROOT.rglob("*")):
        if p.is_dir():
            folders.append(str(p.relative_to(DATA_ROOT)))
    return {"folders": folders}
  
# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)