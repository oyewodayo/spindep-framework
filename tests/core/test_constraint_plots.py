from src.constraint_plots import (
    deduplicate_by_content,
    plot_single_potential,
    plot_constraint_atlas,
    run_constraint_plots,
)


def _real_datasets_for_potential(make_dataset, tmp_path):
    """Datasets with real on-disk CSVs (needed: plot_single_potential
    actually loads and plots the coupling data, unlike gap_analysis's
    metadata-only plots)."""
    specs = [
        ("m1", "ee",    False, "1e-9,1e-10\n1e-8,1e-11\n1e-7,1e-12\n"),
        ("a1", "eebar", True,  "1e-9,2e-10\n1e-8,2e-11\n1e-7,2e-12\n"),
    ]
    datasets = []
    for filename, sector, is_anti, content in specs:
        fp = tmp_path / f"{filename}.csv"
        fp.write_text(content)
        datasets.append(make_dataset(
            filepath=fp, filename=filename, sector=sector,
            potential="V2", contains_antimatter=is_anti,
        ))
    return datasets


# ── deduplicate_by_content (same logic as gap_analysis.py's copy) ────────

def test_deduplicate_by_content_collapses_identical_bytes(make_dataset, tmp_path):
    f1 = tmp_path / "a.csv"
    f2 = tmp_path / "b.csv"
    f1.write_text("1e-9,1e-10\n")
    f2.write_text("1e-9,1e-10\n")
    d1 = make_dataset(filepath=f1, filename="a")
    d2 = make_dataset(filepath=f2, filename="b")
    assert len(deduplicate_by_content([d1, d2])) == 1


# ── plotting smoke tests ─────────────────────────────────────────────────

def test_plot_single_potential_writes_nonempty_png(make_dataset, tmp_path):
    out = tmp_path / "constraint_V2.png"
    plot_single_potential(_real_datasets_for_potential(make_dataset, tmp_path), "V2", out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_plot_single_potential_no_plottable_data_writes_nothing(make_dataset, tmp_path):
    # Each dataset has < 2 valid points -> nothing plottable
    fp = tmp_path / "too_short.csv"
    fp.write_text("1e-9,1e-10\n")
    d = make_dataset(filepath=fp, filename="too_short", potential="V2")
    out = tmp_path / "empty.png"
    plot_single_potential([d], "V2", out)
    assert not out.exists()


def test_plot_constraint_atlas_writes_nonempty_png(make_dataset, tmp_path):
    out = tmp_path / "atlas_all.png"
    plot_constraint_atlas(_real_datasets_for_potential(make_dataset, tmp_path), out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_run_constraint_plots_end_to_end(make_dataset, tmp_path):
    datasets = _real_datasets_for_potential(make_dataset, tmp_path)
    figures_dir = tmp_path / "figures"
    plots_dir = tmp_path / "plots"
    run_constraint_plots(datasets, summary_rows=[], plots_dir=plots_dir, figures_dir=figures_dir)

    atlas_dir = figures_dir / "constraint_atlas"
    assert (atlas_dir / "constraint_V2.png").exists()
    assert (atlas_dir / "constraint_atlas_all.png").exists()
