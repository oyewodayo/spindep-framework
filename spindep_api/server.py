# server.py  — FastAPI bridge between GUI and spindep pipeline
#!/usr/bin/env python3
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, uuid, json, sys, logging
from pathlib import Path

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


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)