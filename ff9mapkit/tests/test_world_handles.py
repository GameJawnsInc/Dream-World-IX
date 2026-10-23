"""THE HANDLE TABLE's fence (overworld editor rung B2): each relief verb declares its handles once in
``world/handles.py``, and every surface reads it -- argparse (``cli``), ``world-fuse``'s rows (``row``) and the World
tab's cards (``gui``). These tests fail when a handle exists in one surface only, or a surface strays from the table:
a parser flag the table does not declare, a row key it does not allow, a card widget or command flag it does not map,
a spin that stops somewhere else, a picker that lists another catalogue."""
from __future__ import annotations

import argparse
import os

import pytest

from ff9mapkit import cli
from ff9mapkit.world import fuse as FU
from ff9mapkit.world import handles as HD
from ff9mapkit.world import interior as IN

VERBS = {"forest": "world-forest", "mountain": "world-mountain", "hill": "world-hill"}
#: the flags a verb carries that are not handles: where it writes and how (never a person's turn of the shape)
PLUMBING = {"mod_folder", "disc", "target_disc", "dry_run", "skip_mirror", "report_json", "help"}
TABLES = sorted(VERBS)


def _parser(verb):
    p = cli.build_parser()
    sub = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    return sub.choices[verb]


def test_the_table_is_well_formed():
    for table in TABLES:
        names = [h.name for h in HD.handles(table)]
        assert len(names) == len(set(names)), table
        for h in HD.handles(table):
            assert set(h.surfaces.split()) <= set(HD.SURFACES) and h.on("cli"), (table, h.name)
            assert h.flag == "--" + h.name.replace("_", "-"), (table, h.name)
            assert h.help, (table, h.name)
            if h.ceiling:
                assert h.lo is not None and h.top() > h.lo, (table, h.name)
            if h.on("gui") and h.type is float and h.name not in ("reach",):
                assert h.lo is not None and h.top() is not None, f"{table}.{h.name}: a gui spin needs a range"


@pytest.mark.parametrize("table", TABLES)
def test_argparse_carries_exactly_the_table_s_cli_handles(table):
    sp = _parser(VERBS[table])
    acts = {a.dest: a for a in sp._actions if a.dest not in PLUMBING}
    assert set(acts) == {h.name for h in HD.handles(table, "cli")}
    for h in HD.handles(table, "cli"):
        a = acts[h.name]
        assert a.option_strings == [h.flag] and a.help == h.help and a.default == h.default, h.name
        assert a.type is h.type and a.metavar == h.metavar, h.name
    (where,) = sp._mutually_exclusive_groups
    assert where.required and {a.dest for a in where._group_actions} == \
        {h.name for h in HD.handles(table) if h.group == "where"}


@pytest.mark.parametrize("table", TABLES)
def test_a_row_allows_exactly_the_table_s_row_handles(table, monkeypatch, tmp_path):
    """The fuse runner's own key check: every row handle passes it, and a key on the CLI only is refused."""
    seen = {}

    def strict(t, row, allowed):
        seen[t] = set(allowed)
        raise ValueError("stop")                          # the key check is the first thing the runner does
    monkeypatch.setattr(FU, "_strict_keys", strict)
    monkeypatch.setattr(FU, "_row_point", lambda t, row: ((0.0, 0.0), True))
    out = FU.compose_layout(str(tmp_path), {table: [{"center": [0, 0]}]}, game=tmp_path, dry_run=True)
    assert out["gates"][-1]["error"] == "stop"            # a row's refusal lands in its gate
    assert seen[table] == HD.row_keys(table)
    assert HD.row_keys(table) <= {h.name for h in HD.handles(table, "cli")}


def test_a_cli_only_handle_is_refused_on_a_row(tmp_path):
    out = FU.compose_layout(str(tmp_path), {"mountain": [{"center": [0, 0], "gblend": 20.0}]}, game=tmp_path,
                            dry_run=True)
    assert "unknown key(s) ['gblend']" in out["gates"][-1]["error"]


def test_the_ceilings_are_the_verbs_own_constants():
    assert HD.handle("forest", "spread").range() == (1.0, IN.FOREST_SPREAD_MAX)
    assert HD.handle("mountain", "spread").range() == (1.0, IN.MTN_SPREAD_MAX)
    assert HD.handle("mountain", "rock_height").range() == (1.0, IN.MTN_ROCK_HEIGHT_MAX)


def test_the_pickers_list_the_table_s_catalogue():
    from ff9mapkit.world import forestedit as FE
    from ff9mapkit.world import mountainedit as ME
    from ff9mapkit.world.donors import load_donors
    for table, rows in (("forest", FE.canopy_donors()), ("mountain", ME.massif_donors())):
        cls = HD.handle(table, "donor").catalogue
        want = [r["name"] for r in load_donors() if r.get("class") == cls and r.get("status") == "qualified"]
        assert want and [r["name"] for r in rows] == want, table


def test_the_commands_omit_exactly_the_table_s_defaults():
    """The editor's command omits a handle at its default, as a hand-typed command does: the defaults it omits are
    the table's."""
    from ff9mapkit.world import mountainedit as ME
    assert ME.DEFAULT_REACH == HD.handle("mountain", "reach").default
    assert HD.handle("mountain", "ground").default == "grass" == HD.handle("mountain", "ground").choices()[0]
    for table in ("forest", "mountain"):
        for name in ("spread",) + (("rock_height",) if table == "mountain" else ()):
            assert HD.handle(table, name).default == 1.0


# ---------------------------------------------------------------- the cards
@pytest.fixture(scope="module")
def app():
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _card(table, tmp_path):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldforest import ForestTool
    from ff9mapkit.workspace.worldmountain import MountainTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    cls = {"forest": ForestTool, "mountain": MountainTool}[table]
    return cls(pick_palette("dark"), WorldView3DPanel(pick_palette("dark")), game_fn=lambda: tmp_path,
               source_fn=lambda: tmp_path / "Src", runner=lambda *a, **k: None, drafts_root=tmp_path / "d",
               outline_fn=lambda donor: None, soup_fn=lambda folder: None, sync=True)


def _flags(argv):
    return {a for a in argv if a.startswith("--")}


@pytest.mark.parametrize("table", ["forest", "mountain"])
def test_a_card_maps_exactly_the_table_s_gui_handles(app, table, tmp_path):
    card = _card(table, tmp_path)
    assert card.HANDLE_TABLE == table
    assert set(card.HANDLES) == {h.name for h in HD.handles(table, "gui")}
    for name, how in card.HANDLES.items():
        h = HD.handle(table, name)
        w = getattr(card, how, None)
        if w is None:
            assert how.startswith("the "), f"{table}.{name}: {how!r} is neither a widget nor a rule"
            continue
        if h.lo is not None:                             # a spin stops where the table says
            lo, top = h.range()
            if h.wraps:
                assert (w.minimum(), w.maximum(), w.wrapping()) == (int(lo), int(top) - 1, True), name
            else:
                assert (w.minimum(), w.maximum()) == (lo, top), name
        if h.catalogue:                                  # a picker lists the catalogue's qualified rows
            mod = card.FE
            rows = mod.canopy_donors() if table == "forest" else mod.massif_donors()
            assert w.count() == len(rows) > 0, name


@pytest.mark.parametrize("table", ["forest", "mountain"])
def test_a_card_s_command_names_only_its_gui_handles(app, table, tmp_path):
    """Every handle flag the card's command can emit is one its map names, and every mapped handle reaches the
    command when it is off its default (the centre always does)."""
    card = _card(table, tmp_path)
    card.center = (100.0, -100.0)
    card.angle.setValue(90)
    card.spread.setValue(card.spread.maximum())
    if table == "mountain":
        card.rock_height.setValue(card.rock_height.maximum())
        card.ground = lambda: "desert"
        card._r_placed = lambda: 200.0                  # a radius whose reach is off the default
    plumbing = {"--mod-folder", "--dry-run", "--report-json"}
    got = _flags(card._cmd("D", dry_run=True, report="r.json")) - plumbing
    assert got == {HD.handle(table, n).flag for n in card.HANDLES}


#: one value off its default per row handle (the where pair swaps centre for near)
OFF = {"center": None, "near": [10.0, -20.0], "donor": {"forest": "7,7", "mountain": "1,1"}, "rot": 45.0,
       "spread": 1.2, "rock_height": 1.5, "reach": 120.0, "ground": "desert", "height": 3.0, "radius": 22.0}


@pytest.mark.parametrize("table", TABLES)
def test_every_row_handle_reaches_the_verb(table, monkeypatch, tmp_path):
    """A key the row allows but never passes on would pass the key check and carve the default: each row handle
    turned off its default must change what the runner hands the verb."""
    calls = []

    def rec(name, ret=None):
        def f(*a, **kw):
            calls.append((name, a[1:], {k: v for k, v in kw.items() if k not in ("game", "baseline", "stack")}))
            return ret() if callable(ret) else ret
        return f
    carve = lambda: {"changed": {}, "center": (0.0, 0.0)}           # noqa: E731
    monkeypatch.setattr(IN, "read_deployed_blocks", rec("blocks", list))
    monkeypatch.setattr(IN, "read_deployed_stack", rec("stack", list))
    monkeypatch.setattr(IN, "soup_from_blocks", lambda b: None)
    monkeypatch.setattr(IN, "census_gate", lambda *a, **k: None)
    monkeypatch.setattr(IN, "census_parts", lambda res: ())
    for verb in ("carve_forest", "carve_mountain", "build_hill"):
        monkeypatch.setattr(IN, verb, rec(verb, carve))
    from ff9mapkit.world import donors as DN
    monkeypatch.setattr(DN, "catalog_alcove", lambda d: None)
    monkeypatch.setattr(DN, "home_ground_note", lambda d, g: None)

    def run(row):
        calls.clear()
        out = FU.compose_layout(str(tmp_path), {table: [row]}, game=tmp_path, dry_run=True)
        assert out["clean"], out["gates"]
        return list(calls)
    base = run({"center": [10.0, -20.0]})
    for name in sorted(HD.row_keys(table) - {"center"}):
        v = OFF[name][table] if isinstance(OFF[name], dict) else OFF[name]
        row = {"near": v} if name == "near" else {"center": [10.0, -20.0], name: v}
        assert run(row) != base, f"[[{table}]] {name} = {v!r} reached nothing"
