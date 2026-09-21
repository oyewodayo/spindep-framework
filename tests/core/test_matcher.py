import pytest

from src.matcher import compatible_sectors, are_compatible, build_pairs


# ── compatible_sectors ───────────────────────────────────────────────────

def test_compatible_sectors_identical():
    assert compatible_sectors("ee", "ee") is True


def test_compatible_sectors_matter_antimatter_pair():
    assert compatible_sectors("ee", "eebar") is True
    assert compatible_sectors("nn", "nnbar") is True


def test_compatible_sectors_incompatible():
    assert compatible_sectors("ee", "nn") is False


def test_compatible_sectors_en_ep_cross_pairing():
    # matcher.py's own SECTOR_EQUIVALENCE (which shadows the one imported
    # from parser.py) explicitly allows en<->ep cross-sector pairing for
    # gAgV-style files. This documents that current behavior so a future
    # "cleanup" of the apparently-unused parser import doesn't silently
    # remove it.
    assert compatible_sectors("en", "ep") is True
    assert compatible_sectors("ep", "en") is True


# ── are_compatible ───────────────────────────────────────────────────────

def test_are_compatible_true_for_matching_pair(make_dataset):
    a = make_dataset(sector="ee", contains_antimatter=False)
    b = make_dataset(sector="eebar", contains_antimatter=True)
    assert are_compatible(a, b) is True
    assert are_compatible(b, a) is True


def test_are_compatible_false_on_coupling_mismatch(make_dataset):
    a = make_dataset(sector="ee", contains_antimatter=False, coupling="gAgA")
    b = make_dataset(sector="eebar", contains_antimatter=True, coupling="gVgV")
    assert are_compatible(a, b) is False


def test_are_compatible_false_on_potential_mismatch(make_dataset):
    a = make_dataset(sector="ee", contains_antimatter=False, potential="V1")
    b = make_dataset(sector="eebar", contains_antimatter=True, potential="V2")
    assert are_compatible(a, b) is False


def test_are_compatible_false_when_both_matter(make_dataset):
    a = make_dataset(sector="ee", contains_antimatter=False)
    b = make_dataset(sector="eebar", contains_antimatter=False)
    assert are_compatible(a, b) is False


def test_are_compatible_false_on_interaction_class_mismatch(make_dataset):
    a = make_dataset(sector="ee", contains_antimatter=False, interaction_class="lepton-lepton")
    b = make_dataset(sector="eebar", contains_antimatter=True, interaction_class="nucleon-nucleon")
    assert are_compatible(a, b) is False


# ── build_pairs ──────────────────────────────────────────────────────────

def test_build_pairs_matches_exactly_one_valid_pair(make_dataset):
    matter = make_dataset(sector="ee", contains_antimatter=False, filename="matter")
    anti   = make_dataset(sector="eebar", contains_antimatter=True, filename="anti")
    unrelated = make_dataset(sector="nn", contains_antimatter=False, filename="unrelated")

    pairs = build_pairs([matter, anti, unrelated])
    assert len(pairs) == 1
    m, a = pairs[0]
    assert m.filename == "matter"
    assert a.filename == "anti"


def test_build_pairs_orders_matter_first_regardless_of_input_order(make_dataset):
    matter = make_dataset(sector="ee", contains_antimatter=False, filename="matter")
    anti   = make_dataset(sector="eebar", contains_antimatter=True, filename="anti")

    pairs = build_pairs([anti, matter])
    assert len(pairs) == 1
    m, a = pairs[0]
    assert m.contains_antimatter is False
    assert a.contains_antimatter is True


def test_build_pairs_no_antimatter_means_no_pairs(make_dataset):
    a = make_dataset(sector="ee", contains_antimatter=False, filename="a")
    b = make_dataset(sector="ee", contains_antimatter=False, filename="b")
    assert build_pairs([a, b]) == []


def test_build_pairs_empty_input():
    assert build_pairs([]) == []
