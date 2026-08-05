"""KNOWLEDGE IN CODE (audit rec 13): the invocable surface carries the project's verdicts.

Two halves, each with a gate that can actually fail (feedback-a-check-that-cannot-fail):
the FALSIFIED banner on ``world-island --beach`` (delete the banner anywhere -- runtime,
--help, module docstring -- and a test here goes red), and the read-only donor catalog
``world/data/donors.toml`` with a DRIFT test pinning every frozen donor literal in
interior/island/transplant to a catalog row -- which is what keeps the table from becoming
a fifth stale copy of the donor list.
"""
from __future__ import annotations

import argparse

import pytest

from ff9mapkit import cli


def _subparser(name):
    parser = cli.build_parser()
    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction):
            return a.choices[name]
    raise AssertionError("no subparsers action found")


# ---- the FALSIFIED banner -------------------------------------------------------------------------------------------

def test_beach_help_carries_the_falsified_verdict():
    assert "[FALSIFIED" in _subparser("world-island").format_help()


def test_beach_runtime_banner_prints_before_the_mint(monkeypatch, capsys):
    """The runtime banner is the call-site verdict; it must print even when the mint then
    fails. Delete the banner in _cmd_world_island and this goes red."""
    from ff9mapkit.world import island as I

    def _stub(*a, **k):
        raise ValueError("stub -- banner test stops before any geometry")

    monkeypatch.setattr(I, "landmass", _stub)
    args = cli.build_parser().parse_args(
        ["world-island", "--mod-folder", "X", "--cell", "5,18", "--beach", "90,180"])
    rc = args.func(args)
    out = capsys.readouterr()
    assert rc == 2 and "stub" in out.err
    assert "FALSIFIED LANE" in out.out and "world-transplant --ground" in out.out


def test_beach_banner_absent_without_the_flag(monkeypatch, capsys):
    from ff9mapkit.world import island as I
    monkeypatch.setattr(I, "landmass",
                        lambda *a, **k: (_ for _ in ()).throw(ValueError("stub")))
    args = cli.build_parser().parse_args(
        ["world-island", "--mod-folder", "X", "--cell", "5,18"])
    assert args.func(args) == 2
    assert "FALSIFIED LANE" not in capsys.readouterr().out


def test_module_docstring_carries_the_verdict():
    from ff9mapkit.world import islandbeach
    assert "FALSIFIED IN GAME" in islandbeach.__doc__
    assert "world-transplant --ground" in islandbeach.__doc__


# ---- the donor catalog + THE DRIFT TEST -----------------------------------------------------------------------------

def _spec(t):
    return f"{t[0]},{t[1]}"


def test_donor_literals_pin_to_catalog_rows():
    """Every frozen donor literal in the geometry modules appears as a catalog row with a
    matching status -- the geometry keeps its literals (the Uaho carry's bit-frozen
    acceptance must not acquire a file-parse dependency); this join is what keeps the
    catalog honest."""
    from ff9mapkit.world import interior as IN, island as I, transplant as TR
    from ff9mapkit.world.donors import donors_by_blocks
    rows = donors_by_blocks()

    uaho = rows[_spec(IN.MOUNTAIN_DONOR)]
    assert uaho["class"] == "massif" and uaho["status"] == "qualified"
    (x0, x1), (z0, z1), ymin = IN.UAHO_ALCOVE
    assert uaho["alcove"] == [x0, x1, z0, z1, ymin]

    forest = rows[_spec(IN.FOREST_DONOR)]
    assert forest["class"] == "canopy" and forest["status"] == "qualified"

    plane = rows[_spec(I.SEA_PLANE_SOURCE)]
    assert plane["class"] == "sea-plane" and plane["status"] == "qualified"

    for fam, pins in I.BEACH_PINS.items():
        row = rows[_spec(pins)]
        assert row["class"] == "coast" and row["status"] == "qualified", fam

    proven = rows[_spec(TR.PROVEN_DONOR)]
    assert proven["class"] == "coast" and proven["status"] == "qualified"

    # the four qualified massif rects the interior topo-narrowing verified (interior.py's
    # MOUNTAIN_ROCK_TOPOS comment names them)
    for blocks in ("0,0", "10,5-6", "5-6,15-16", "12,16-17"):
        assert rows[blocks]["class"] == "massif" and rows[blocks]["status"] == "qualified"


def test_catalog_rows_are_well_formed():
    from ff9mapkit.world.donors import load_donors
    rows = load_donors()
    assert rows, "empty donor catalog"
    for r in rows:
        assert r["status"] in ("qualified", "candidate", "disqualified"), r
        assert r["class"] in ("massif", "canopy", "coast", "sea-plane"), r
        assert r.get("aperture", "none") in ("none", "object", "ensemble"), r
        # every blocks spec parses as the CLI rect grammar and lands on the 24x20 grid
        from ff9mapkit.world.mesh import block_in_grid
        for (bx, by) in cli._parse_block_rect(r["blocks"]):
            assert block_in_grid(bx, by), r


def test_world_donors_verb_prints_the_table(capsys):
    args = cli.build_parser().parse_args(["world-donors"])
    assert args.func(args) == 0
    out = capsys.readouterr().out
    for name in ("uaho", "crag", "horseshoe", "beach-island", "sea-plane"):
        assert name in out
    args = cli.build_parser().parse_args(["world-donors", "--class", "massif"])
    assert args.func(args) == 0
    out = capsys.readouterr().out
    assert "uaho" in out and "beach-island" not in out
