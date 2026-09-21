from pathlib import Path

from src.gap_analysis import (
    deduplicate_by_content,
    plot_pair_coverage_matrix,
    plot_lambda_coverage,
    plot_matter_antimatter_ratio,
    run_gap_analysis,
)


def _sample_datasets(make_dataset, tmp_path):
    # run_gap_analysis() calls deduplicate_by_content(), which reads bytes
    # off dataset.filepath -- so these need to be real, distinct files, not
    # the make_dataset fixture's placeholder Path("dummy.csv").
    specs = [
        ("m1", "ee",    "V2", False, "1e-9,1e-10\n"),
        ("a1", "eebar", "V2", True,  "2e-9,2e-10\n"),
        ("m2", "nn",    "V1", False, "3e-9,3e-10\n"),
    ]
    datasets = []
    for filename, sector, potential, is_anti, content in specs:
        fp = tmp_path / f"{filename}.csv"
        fp.write_text(content)
        datasets.append(make_dataset(
            filepath=fp, filename=filename, sector=sector,
            potential=potential, contains_antimatter=is_anti,
        ))
    return datasets


# ── deduplicate_by_content ─────────────────────────────────────────────

def test_deduplicate_by_content_collapses_identical_bytes(make_dataset, tmp_path):
    f1 = tmp_path / "a.csv"
    f2 = tmp_path / "b.csv"
    f1.write_text("1e-9,1e-10\n2e-9,2e-10\n")
    f2.write_text("1e-9,1e-10\n2e-9,2e-10\n")  # byte-identical to f1

    d1 = make_dataset(filepath=f1, filename="a")
    d2 = make_dataset(filepath=f2, filename="b")

    deduped = deduplicate_by_content([d1, d2])
    assert len(deduped) == 1


def test_deduplicate_by_content_keeps_distinct_files(make_dataset, tmp_path):
    f1 = tmp_path / "a.csv"
    f2 = tmp_path / "b.csv"
    f1.write_text("1e-9,1e-10\n")
    f2.write_text("2e-9,2e-10\n")  # different content

    d1 = make_dataset(filepath=f1, filename="a")
    d2 = make_dataset(filepath=f2, filename="b")

    deduped = deduplicate_by_content([d1, d2])
    assert len(deduped) == 2


# ── plotting smoke tests ─────────────────────────────────────────────────

def test_plot_pair_coverage_matrix_writes_nonempty_png(make_dataset, tmp_path):
    out = tmp_path / "coverage.png"
    plot_pair_coverage_matrix(_sample_datasets(make_dataset, tmp_path), out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_plot_lambda_coverage_writes_one_file_per_potential(make_dataset, tmp_path):
    out_dir = tmp_path / "lambda_coverage"
    paths = plot_lambda_coverage(_sample_datasets(make_dataset, tmp_path), out_dir)
    assert paths is not None
    assert len(paths) == 2  # V1 and V2 present in the sample
    for p in paths:
        assert p.exists() and p.stat().st_size > 0


def test_plot_lambda_coverage_no_known_potentials_returns_none(make_dataset, tmp_path):
    unknowns = [make_dataset(filename="x", potential="UNKNOWN")]
    assert plot_lambda_coverage(unknowns, tmp_path / "out") is None


def test_plot_matter_antimatter_ratio_writes_nonempty_png(make_dataset, tmp_path):
    out = tmp_path / "ratio.png"
    plot_matter_antimatter_ratio(_sample_datasets(make_dataset, tmp_path), out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_run_gap_analysis_end_to_end_writes_all_figures(make_dataset, tmp_path):
    figures_dir = tmp_path / "figures"
    run_gap_analysis(_sample_datasets(make_dataset, tmp_path), figures_dir)

    gap_dir = figures_dir / "gap_analysis"
    assert (gap_dir / "pair_coverage_matrix.png").exists()
    assert (gap_dir / "matter_antimatter_ratio.png").exists()
    assert any((gap_dir / "lambda_coverage_by_potential").glob("*.png"))
