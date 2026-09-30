import pandas as pd
import pytest

from src.pipeline import run_pipeline


def test_run_pipeline_end_to_end_on_one_synthetic_pair(tmp_dataset_dir, tmp_path):
    results_root = tmp_path / "results"

    run_pipeline(dataset_root=tmp_dataset_dir, results_root=results_root)

    tables_dir  = results_root / "tables"
    plots_dir   = results_root / "plots"
    reports_dir = results_root / "reports"

    registry_csv = tables_dir / "dataset_registry.csv"
    summary_csv  = tables_dir / "asymmetry_summary.csv"
    assert registry_csv.exists()
    assert summary_csv.exists()

    registry = pd.read_csv(registry_csv)
    assert len(registry) == 2  # the one matter + one antimatter file

    summary = pd.read_csv(summary_csv)
    assert len(summary) == 1  # exactly one valid matched pair
    row = summary.iloc[0]

    expected_columns = {
        "coupling", "potential", "interaction_class", "sector",
        "matter_source", "antimatter_source", "mean_abs_A",
        "chi2_uniform", "chi2_weighted", "p_value_uniform", "p_value_weighted",
        "dof_effective", "p_value_weighted_eff", "lambda_min", "lambda_max",
    }
    assert expected_columns.issubset(set(summary.columns))

    assert row["coupling"] == "gAgA"
    assert row["potential"] == "V2"
    assert row["sector"] == "ee"
    # matter_antimatter_csv_pair fixture behind tmp_dataset_dir sets
    # g_antimatter = 2 * g_matter everywhere -> A_alpha = -1/3 exactly.
    assert row["mean_abs_A"] == pytest.approx(1.0 / 3.0, abs=0.02)
    assert row["chi2_weighted"] > 0
    assert 0.0 <= row["p_value_weighted"] <= 1.0

    # At least one asymmetry plot was produced for the pair
    assert any(plots_dir.glob("*.png"))

    # A PDF report was generated since there was a valid pair
    report_pdfs = list(reports_dir.glob("*.pdf"))
    assert len(report_pdfs) == 1
    assert report_pdfs[0].stat().st_size > 0


def test_registry_filepaths_are_not_absolute(tmp_dataset_dir, tmp_path):
    # The registry is committed publicly, so it must not carry absolute
    # paths from whichever machine ran the pipeline.
    results_root = tmp_path / "results"
    run_pipeline(dataset_root=tmp_dataset_dir, results_root=results_root)
    registry = pd.read_csv(results_root / "tables" / "dataset_registry.csv")
    assert not registry["filepath"].astype(str).str.startswith("/").any()
