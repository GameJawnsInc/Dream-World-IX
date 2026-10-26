"""The forest as the overworld editor drives it (rung C1), hermetic: world.forestedit, world.draft, the located
refusals (interior.CarveRefused) and ``world-forest --report-json``.

The C1 acceptance (the editor writes the bytes the hand-typed command writes) is GUI-driven, so it lives with the
forest tool's tests in ``test_worldforest.py``. The donor read here is monkeypatched (the synthetic carpet the
interior tests use), so no game bytes are needed.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import numpy as np
import pytest

from ff9mapkit.world import draft as D
from ff9mapkit.world import forestedit as FE
from ff9mapkit.world import interior as IN
from ff9mapkit.world import mesh as M

from .test_world_interior import (GRASS, ROCK, _MAIN_U, _bm, _canopy_dome, _mains_grid,  # noqa: F401
                                 _patch_donor)


@pytest.fixture(autouse=True)
def _no_real_install(monkeypatch):
    """NEVER THE REAL INSTALL. ``config.find_game_path`` trusts an explicit path only when it exists, and falls
    through to auto-detecting the real game otherwise -- a test whose tmp game folder was not made yet wrote into
    the live install that way (caught: a stray ``<install>/Src`` the launcher would have activated). Here every
    fall-through is closed, so a missing path raises instead of finding the game."""
    from ff9mapkit import config
    monkeypatch.delenv("FF9_GAME_PATH", raising=False)
    monkeypatch.setattr(config, "_read_user_config", lambda: {})
    for name in ("_registry_candidates", "_steam_library_candidates", "_fallback_candidates"):
        monkeypatch.setattr(config, name, lambda: [])


def _game(tmp_path) -> Path:
    g = tmp_path / "game"
    g.mkdir(parents=True, exist_ok=True)
    return g


def test_the_install_guard_holds():
    """The guard above is the only thing between these tests and the live install: prove it refuses."""
    from ff9mapkit import config
    with pytest.raises(config.ConfigError):
        config.find_game_path(Path("Z:/no/such/game"))


# ---------------------------------------------------------------- the command
def test_command_spells_the_handles_the_way_a_hand_typed_command_does():
    """Defaults are omitted, numbers sit on the handles' grids, and only Check carries --dry-run."""
    assert FE.command("M", (1400.0, -460.0), (13, 15), dry_run=False) == \
        ["world-forest", "--mod-folder", "M", "--center", "1400,-460", "--donor", "13,15"]
    assert FE.command("M", (1400.04, -460.26), (3, 12), spread=1.25, rot_deg=370, dry_run=True, report="r.json") == \
        ["world-forest", "--mod-folder", "M", "--center", "1400,-460.3", "--donor", "3,12", "--spread", "1.25",
         "--rot", "10", "--dry-run", "--report-json", "r.json"]
    assert "--rot" not in FE.command("M", (0, 0), (15, 15), rot_deg=360)
    assert "--spread" not in FE.command("M", (0, 0), (15, 15), spread=1.0)


def test_the_command_parses_as_world_forest():
    """What the editor builds, argparse reads back as the same handles (no flag the verb does not know)."""
    from ff9mapkit import cli
    a = cli.build_parser().parse_args(FE.command("M", (12.3, -4.5), (19, 8), spread=1.5, rot_deg=90,
                                                 report="r.json"))
    assert (a.mod_folder, a.center, a.donor, a.spread, a.rot, a.dry_run, a.report_json) == \
        ("M", "12.3,-4.5", "19,8", 1.5, 90.0, True, "r.json")


def test_canopy_donors_are_the_qualified_canopy_rows():
    """The picker's list is the catalogue's qualified canopies, each naming a block of its own rect."""
    from ff9mapkit.world.donors import load_donors, spec_blocks
    rows = FE.canopy_donors()
    want = [r["name"] for r in load_donors() if r.get("class") == "canopy" and r.get("status") == "qualified"]
    assert [r["name"] for r in rows] == want and len(want) >= 5
    assert any(r["donor"] == IN.FOREST_DONOR for r in rows)
    for r in rows:
        assert r["donor"] in spec_blocks(r["blocks"])


# ---------------------------------------------------------------- the ghost
def test_plan_xz_is_forest_plans_map():
    """The ghost turns and spreads exactly as the carve does (interior._forest_plan), quarter turns and odd ones."""
    rng = np.random.default_rng(3)
    pts = rng.uniform(-20, 20, (40, 3))
    for spread, rot in ((1.0, 0), (1.0, 90), (1.25, 270), (1.5, 37.0), (1.1, 200)):
        want, _n = IN._forest_plan(pts, [[0.0, 1.0, 0.0]] * len(pts), (0.0, 0.0), spread=spread, rot_deg=rot)
        got = FE.plan_xz(pts[:, [0, 2]], spread=spread, rot_deg=rot)
        assert np.allclose(got, np.asarray(want)[:, [0, 2]], atol=1e-9), (spread, rot)


def test_outline_reads_the_blob_the_carve_carries(monkeypatch, tmp_path):
    """The ghost's outline is the carve's blob: same triangles, centred on the blob centre, rim on 0."""
    _patch_donor(monkeypatch, _canopy_dome())
    ol = FE.outline((15, 15), game=tmp_path)
    assert ol.tris.shape == (50, 3, 3)
    assert ol.size == (20.0, 20.0)
    assert np.allclose(ol.rim[:, 1], 0.0) and len(ol.rim) == 20
    assert math.isclose(ol.tris[..., 0].min(), -10.0) and math.isclose(ol.tris[..., 0].max(), 10.0)
    t, r = FE.placed(ol, (26.0, -26.0), spread=1.5, rot_deg=0, ground_y=3.2)
    assert math.isclose(r[:, 0].min(), 11.0) and math.isclose(r[:, 0].max(), 41.0)
    assert np.allclose(r[:, 1], 3.2) and math.isclose(t[..., 1].max(), 4.2)


# ---------------------------------------------------------------- the footprint law, vectorised
def _patchy_soup(seed):
    """A 3x3-block mains field with rock tris (topo 58: the coast proxy) and a stamp patch scattered through it."""
    rng = np.random.default_rng(seed)
    blocks = {}
    for bx in range(3):
        for by in range(3):
            tris = []
            for i in range(16):
                for j in range(16):
                    x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
                    roll = rng.random()
                    idall, u = (ROCK, _MAIN_U) if roll < 0.01 else (GRASS, 0.4) if roll < 0.02 else (GRASS, _MAIN_U)
                    tris.append((((x0, 3.0, z0), (x1, 3.0, z0), (x0, 3.0, z1)), idall, u))
                    tris.append((((x1, 3.0, z0), (x1, 3.0, z1), (x0, 3.0, z1)), GRASS, _MAIN_U))
            blocks[(bx, by)] = _bm(tris, name=f"Block[{bx}][{by}] Terrain", x=bx, y=by)
    return IN.soup_from_blocks(blocks)


def test_footprint_preview_is_the_gate_s_own_law():
    """THE PREVIEW IS THE LAW: at random centres, turns and spreads over a patchy field, the vectorised preview
    and the carve's own loop (interior.forest_footprint_lawful) give the same verdict and judge the same count."""
    ring = np.array([(math.cos(a) * 9.0, 0.0, math.sin(a) * 6.0) for a in np.linspace(0, 2 * math.pi, 19)[:-1]])
    ol = FE.Outline((0, 0), np.zeros((0, 3, 3)), ring, (18.0, 12.0))
    rng = np.random.default_rng(11)
    lawful = refused = 0
    for seed in (1, 2):
        soup = _patchy_soup(seed)
        ix = FE.SoupIndex(soup)
        tri_c = IN._tri_centroids(soup)
        for _ in range(60):
            c = (rng.uniform(-10, 202), rng.uniform(-202, 10))
            _t, rim = FE.placed(ol, c, spread=float(rng.choice([1.0, 1.25, 1.5])),
                                rot_deg=float(rng.choice([0, 90, 33, 250])))
            poly = [(float(x), float(z)) for x, _y, z in rim]
            got = FE.footprint_preview(ix, poly)
            seen = IN.forest_footprint_lawful(soup, tri_c, poly)
            assert got["ok"] == (seen is not None and seen >= 40), c
            assert got["seen"] == seen, c
            lawful += got["ok"]
            refused += not got["ok"]
    assert lawful >= 10 and refused >= 10              # both verdicts exercised, or the fence proves nothing


def test_the_footprint_law_asks_only_the_points_near_the_rim(monkeypatch):
    """The carve's footprint law ran pip() / near_poly() for every tri of the island (0.58 s of a forest Check; the
    two ten-line functions were 70% of world-forest --near). A point outside the rim polygon's box widened by
    SCAN_BAND is neither in it nor within SCAN_BAND of it, so it is not asked (PERF.md 5, P2)."""
    soup = _patchy_soup(1)
    tri_c = IN._tri_centroids(soup)
    poly = [(40.0, -40.0), (60.0, -40.0), (60.0, -60.0), (40.0, -60.0)]
    calls, real = [], IN.pip
    monkeypatch.setattr(IN, "pip", lambda *a: calls.append(1) or real(*a))
    boxed = IN.forest_footprint_lawful(soup, tri_c, poly)
    asked = len(calls)
    calls.clear()
    monkeypatch.setattr(IN, "_poly_box", lambda p: None, raising=False)   # every tri asked, as it was
    assert IN.forest_footprint_lawful(soup, tri_c, poly) == boxed
    assert 0 < asked < len(calls) / 10


def test_the_boxed_footprint_law_is_the_footprint_law(monkeypatch):
    """The box answers exactly what pip() and near_poly() answer: the same count, the same refusal and its point, at
    random centres, turns and spreads (the preview fence's) -- and an edge whose dz is under pip's 1e-12 guard's
    reach (0 < |dz| < 1e-6) turns the box off, the one case the guard could move a crossing along x."""
    ring = np.array([(math.cos(a) * 9.0, 0.0, math.sin(a) * 6.0) for a in np.linspace(0, 2 * math.pi, 19)[:-1]])
    ol = FE.Outline((0, 0), np.zeros((0, 3, 3)), ring, (18.0, 12.0))
    rng = np.random.default_rng(5)
    real_box = IN._poly_box
    for seed in (1, 2):
        soup = _patchy_soup(seed)
        tri_c = IN._tri_centroids(soup)
        for _ in range(40):
            c = (rng.uniform(-10, 202), rng.uniform(-202, 10))
            _t, rim = FE.placed(ol, c, spread=float(rng.choice([1.0, 1.5])), rot_deg=float(rng.choice([0, 33, 250])))
            poly = [(float(x), float(z)) for x, _y, z in rim]
            got, why = IN.forest_footprint_lawful(soup, tri_c, poly, why := []), why
            monkeypatch.setattr(IN, "_poly_box", lambda p: None)
            want, why2 = IN.forest_footprint_lawful(soup, tri_c, poly, why2 := []), why2
            monkeypatch.setattr(IN, "_poly_box", real_box)
            assert (got, why) == (want, why2), c
    assert IN._poly_box([(0.0, 0.0), (10.0, 5e-7), (5.0, 9.0)]) is None
    assert IN._poly_box([(0.0, 0.0), (10.0, 0.0), (5.0, 9.0)]) is not None


def test_footprint_preview_says_what_it_reached():
    soup = _patchy_soup(1)
    ix = FE.SoupIndex(soup)
    off = FE.footprint_preview(ix, [(500.0, 500.0), (510.0, 500.0), (505.0, 510.0)])
    assert not off["ok"] and off["why"] == "too little plain grass under it"
    bad = next(i for i, m in enumerate(soup["meta"]) if m[2] != "main")
    x, z = ix.cent[bad]
    got = FE.footprint_preview(ix, [(x - 3, z - 3), (x + 3, z - 3), (x + 3, z + 3), (x - 3, z + 3)])
    assert not got["ok"] and got["why"] in ("coast rock (topograph 58)", "a stamped grass tile", "the coast rim")
    assert got["where"]


def test_ground_y_is_the_top_surface_under_a_point():
    ix = FE.SoupIndex(IN.soup_from_blocks({(0, 0): _mains_grid(y=3.21)}))
    assert math.isclose(ix.ground_y(10.0, -10.0), 3.21)
    assert ix.ground_y(-5.0, 5.0) is None


# ---------------------------------------------------------------- the drafts
def _mod(game: Path, name: str, blocks=((0, 0),)) -> Path:
    root = game / name
    for bx, by in blocks:
        M.deploy_override(_bm([(((0, 3.0, 0), (4, 3.0, 0), (0, 3.0, -4)), GRASS, _MAIN_U)],
                              name=f"Block[{bx}][{by}] Terrain", x=bx, y=by),
                          mod_folder=name, game=game, part="Terrain", disc=1)
    return root


def test_a_draft_copies_the_world_trees_and_tells_its_edits_from_the_source_moving(tmp_path):
    game = _game(tmp_path)
    src = _mod(game, "Src", ((0, 0), (1, 0)))
    tree = src / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0"
    (tree / "Block[0][0] Terrain.ff9mesh.bak-1").write_bytes(b"old")
    (src / "DictionaryPatch.txt").write_text("not world")
    d = D.ensure_draft(src, game=game, root=tmp_path / "drafts")
    assert d.name == "Src.draft" and D.read_meta(d)["source"] == str(src.resolve())
    got = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
    assert "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh" in got
    assert not any(".bak-" in g or "DictionaryPatch" in g for g in got)
    assert D.edits(d) == [] and D.stale(d) == []
    assert D.ensure_draft(src, game=game, root=tmp_path / "drafts") == d          # reused, not re-copied
    dtree = d / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0"
    (dtree / "Block[1][0] Terrain.ff9mesh").write_bytes(b"edited")
    (dtree / "Block[2][0] Terrain.ff9mesh").write_bytes(b"added")
    assert D.edits(d) == ["FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Terrain.ff9mesh",
                          "FF9_Data/WorldMap/Disc1/0_1/r0/Block[2][0] Terrain.ff9mesh"]
    assert D.edited_blocks(d) == [(1, 1, 0), (1, 2, 0)]
    assert D.stale(d) == []
    (tree / "Block[0][0] Terrain.ff9mesh").write_bytes(b"another session deployed")
    assert D.stale(d) == ["FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"]


def test_a_same_size_rewrite_is_still_an_edit(tmp_path):
    """The stat shortcut only skips the hash when size AND mtime match; a same-size rewrite is hashed and caught."""
    game = _game(tmp_path)
    src = _mod(game, "Src")
    d = D.ensure_draft(src, game=game, root=tmp_path / "drafts")
    p = d / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0" / "Block[0][0] Terrain.ff9mesh"
    data = bytearray(p.read_bytes())
    data[-1] ^= 0xFF
    p.write_bytes(bytes(data))
    assert D.edits(d) == ["FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"]


def test_a_draft_never_lives_in_the_install(tmp_path):
    """THE LAUNCHER LAW: the launcher activates any new folder in the install, so a draft root there refuses."""
    game = _game(tmp_path)
    src = _mod(game, "Src")
    with pytest.raises(ValueError, match="inside the game install"):
        D.ensure_draft(src, game=game, root=game / "drafts")
    assert not (game / "drafts").exists()


def test_discard_deletes_only_a_draft(tmp_path):
    game = _game(tmp_path)
    src = _mod(game, "Src")
    root = tmp_path / "drafts"
    d = D.ensure_draft(src, game=game, root=root)
    for not_a_draft in (src, root, tmp_path):
        with pytest.raises(ValueError, match="not a draft"):
            D.discard(not_a_draft, root=root)
    assert src.exists()
    D.discard(d, root=root)
    assert not d.exists() and src.exists()


# ---------------------------------------------------------------- the located refusals and the verdict
def _grid_with_stamp(odd=(6, 6), n=13, y=3.2):
    """:func:`_mains_grid` with one cell of stamped grass (topo 0 off the mains atlas: not lawful under a forest)."""
    tris = []
    for i in range(n):
        for j in range(n):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            u = 0.4 if (i, j) == odd else _MAIN_U
            tris.append((((x0, y, z0), (x1, y, z0), (x0, y, z1)), GRASS, u))
            tris.append((((x1, y, z0), (x1, y, z1), (x0, y, z1)), GRASS, u))
    return _bm(tris)


def test_a_footprint_refusal_says_where_and_keeps_its_text(monkeypatch, tmp_path):
    """B1 for the forest: the refusal names its gate and the point where it fails; its text is the gate's own."""
    _patch_donor(monkeypatch, _canopy_dome())
    soup = IN.soup_from_blocks({(0, 0): _grid_with_stamp()})
    with pytest.raises(IN.CarveRefused) as e:
        IN.carve_forest(soup, center=(26.0, -26.0), donor=(15, 15), game=tmp_path, log=lambda *a: None)
    assert e.value.gate == "footprint"
    assert str(e.value) == ("footprint at (26.0,-26.0) is not lawful plain-grass mains clear of the rim "
                            "(seen=None)")
    assert e.value.detail == "it reaches a stamped grass tile"
    (x, z), = e.value.where                                # the stamped cell itself, (24..28, -24..-28)
    assert 24 <= x <= 28 and -28 <= z <= -24
    assert isinstance(e.value, ValueError)                 # every caller that catches ValueError still does


def test_report_json_carries_the_verdict_beside_the_unchanged_text(monkeypatch, tmp_path, capsys):
    from ff9mapkit import cli
    game = _game(tmp_path)
    src = game / "Src"
    M.deploy_override(_mains_grid(), mod_folder="Src", game=game, part="Terrain", disc=1)
    _patch_donor(monkeypatch, _canopy_dome())
    M.deploy_override(_grid_with_stamp(), mod_folder="Rocky", game=game, part="Terrain", disc=1)
    rep = tmp_path / "v.json"
    assert cli.main(["--game", str(game)] + FE.command("Rocky", (26.0, -26.0), (15, 15), report=rep)) == 2
    err = capsys.readouterr().err
    v = json.loads(rep.read_text())
    assert v["ok"] is False and v["refused"]["gate"] == "footprint" and v["refused"]["where"]
    assert v["refused"]["message"] in err
    assert cli.main(["--game", str(game)] + FE.command("Src", (26.0, -26.0), (15, 15), report=rep)) == 0
    v = json.loads(rep.read_text())
    assert v["ok"] is True and v["dry_run"] is True and v["center"] == [26.0, -26.0]
    assert v["report"]["blob_tris"] == 50 and v["blocks"] == [[0, 0]] and v["written"] == []
    assert src.is_dir()


# ---------------------------------------------------------------- promote and revert (rung C4)
T1 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
T4 = "FF9_Data/WorldMap/Disc4/0_1/r0/Block[0][0] Terrain.ff9mesh"
S4 = "FF9_Data/WorldMap/Disc4/0_1/r0/Block[0][0] Sea4.ff9mesh"


def _tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / "FF9_Data").rglob("*") if p.is_file()}


def _fake_mirror(monkeypatch):
    """The disc-4 mirror needs the install's bundles; here it copies each written disc-1 file to disc 4 (and adds a
    Sea4 there), as a mirror writes through the deploy seam, so promote and revert are judged on both discs."""
    from ff9mapkit.world import discmirror as DM
    calls = []

    def mirror(written, *, mod_folder, log=print, **_k):
        calls.append(mod_folder)
        for p in written:
            p = Path(p)
            d4 = Path(str(p).replace("Disc1", "Disc4"))
            d4.parent.mkdir(parents=True, exist_ok=True)
            if d4.exists():
                M.park_backup(d4)
            d4.write_bytes(p.read_bytes())
            (d4.parent / d4.name.replace("Terrain", "Sea4")).write_bytes(b"sea for " + p.read_bytes()[:8])
    monkeypatch.setattr(DM, "auto_mirror", mirror)
    return calls


def _edited_draft(tmp_path):
    game = _game(tmp_path)
    src = _mod(game, "Src", ((0, 0), (1, 0)))
    tree4 = src / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r0"
    tree4.mkdir(parents=True)
    (tree4 / "Block[0][0] Terrain.ff9mesh").write_bytes((src / T1).read_bytes())
    d = D.ensure_draft(src, game=game, root=tmp_path / "drafts")
    (d / T1).write_bytes(b"the forest")
    # ...ledgered as world-forest ledgers what it writes. Without the row the "verb that made the bytes" was whatever
    # cli.main last ran in the test process (mesh._DEPLOY_ARGV, via _mod's own ledger rows): alone, or after a
    # world-mountain test on the same worker, the promote test failed
    import hashlib
    with open(d / D.LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"cell": [0, 0], "part": "Terrain", "write_disc": 1, "read_disc": 1,
                            "sha256": hashlib.sha256(b"the forest").hexdigest(),
                            "argv": ["world-forest", "--mod-folder", str(d)]}) + "\n")
    return game, src, d


def test_promote_writes_the_edits_mirrors_and_leaves_the_draft_level(monkeypatch, tmp_path):
    calls = _fake_mirror(monkeypatch)
    game, src, d = _edited_draft(tmp_path)
    untouched = (src / "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Terrain.ff9mesh").read_bytes()
    rec = D.promote(d, game=game, log=lambda *a: None)
    assert (src / T1).read_bytes() == b"the forest" and (src / T4).read_bytes() == b"the forest"
    assert calls == ["Src"]                                # mirrored in the LIVE folder, by name
    assert rec["promoted"] == [T1] and rec["cells"] == [[0, 0]]
    assert set(rec["after"]) == {T1, T4, S4} and set(rec["before"]) == {T1, T4}
    assert (src / "FF9_Data/WorldMap/Disc1/0_1/r1".replace("r1", "r0") / "Block[1][0] Terrain.ff9mesh").read_bytes() \
        == untouched                                       # another block is never touched
    assert list((src / "FF9_Data/WorldMap/Disc1/0_1/r0").glob("Block[[]0[]][[]0[]] Terrain.ff9mesh.bak-*"))
    led = [json.loads(ln) for ln in (src / ".ff9world.jsonl").read_text().splitlines()]
    assert led[-1]["cell"] == [0, 0] and led[-1]["pipeline"]["via"] == "world-promote"   # the promote that carried it
    assert led[-1]["pipeline"]["verb"] == "world-forest"   # ...and the verb that made the bytes, kept
    assert D.edits(d) == [] and D.stale(d) == []           # the draft equals the live folder again
    assert (d / S4).read_bytes() == (src / S4).read_bytes()
    assert D.last_promote(d)["utc"] == rec["utc"]


def test_revert_puts_every_file_back_byte_for_byte_and_keeps_the_edit_in_the_draft(monkeypatch, tmp_path):
    _fake_mirror(monkeypatch)
    game, src, d = _edited_draft(tmp_path)
    before = {k: v for k, v in _tree(src).items() if ".bak-" not in k}
    D.promote(d, game=game, log=lambda *a: None)
    D.revert(d, game=game, log=lambda *a: None)
    after = {k: v for k, v in _tree(src).items() if ".bak-" not in k}
    assert after == before                                 # S4, which the promote created, is gone again
    assert D.edits(d) == [T1] and (d / T1).read_bytes() == b"the forest"
    assert D.stale(d) == [] and D.last_promote(d) is None
    with pytest.raises(ValueError, match="no promote to revert"):
        D.revert(d, game=game)
    D.promote(d, game=game, log=lambda *a: None)           # and it promotes again from there
    assert (src / T1).read_bytes() == b"the forest"


def test_promote_refuses_over_another_deploy_and_writes_nothing(monkeypatch, tmp_path):
    _fake_mirror(monkeypatch)
    game, src, d = _edited_draft(tmp_path)
    (src / T1).write_bytes(b"another session's island")
    before = _tree(src)
    with pytest.raises(ValueError, match="changed in Src since the draft was made"):
        D.promote(d, game=game)
    assert _tree(src) == before and not (d / D.PROMOTES).exists()


def test_revert_refuses_when_a_later_deploy_wrote_the_blocks(monkeypatch, tmp_path):
    _fake_mirror(monkeypatch)
    game, src, d = _edited_draft(tmp_path)
    D.promote(d, game=game, log=lambda *a: None)
    (src / T4).write_bytes(b"a later mirror")
    with pytest.raises(ValueError, match="changed after the promote"):
        D.revert(d, game=game)
    assert (src / T1).read_bytes() == b"the forest"


def test_promote_refuses_an_empty_draft_and_a_source_outside_the_install(monkeypatch, tmp_path):
    _fake_mirror(monkeypatch)
    game, src, d = _edited_draft(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(ValueError, match="not a folder of the install"):
        D.promote(d, game=other)
    (d / T1).write_bytes((src / T1).read_bytes())
    with pytest.raises(ValueError, match="no edits to promote"):
        D.promote(d, game=game)


def test_world_promote_cli_reports_and_dry_runs(monkeypatch, tmp_path, capsys):
    from ff9mapkit import cli
    _fake_mirror(monkeypatch)
    game, src, d = _edited_draft(tmp_path)
    rep = tmp_path / "p.json"
    before = _tree(src)
    assert cli.main(["--game", str(game), "world-promote", str(d), "--dry-run", "--report-json", str(rep)]) == 0
    assert _tree(src) == before and json.loads(rep.read_text())["promoted"] == [T1]
    assert cli.main(["--game", str(game), "world-promote", str(d), "--report-json", str(rep)]) == 0
    v = json.loads(rep.read_text())
    assert v["ok"] and v["op"] == "promote" and v["cells"] == [[0, 0]] and (src / T1).read_bytes() == b"the forest"
    assert "promoted 1 file(s) at block(s) (0,0) in Src" in capsys.readouterr().out
    assert cli.main(["--game", str(game), "world-promote", str(d), "--revert", "--report-json", str(rep)]) == 0
    assert json.loads(rep.read_text())["op"] == "revert" and (src / T1).read_bytes() != b"the forest"
    assert cli.main(["--game", str(game), "world-promote", str(d), "--revert", "--report-json", str(rep)]) == 2
    assert "no promote to revert" in json.loads(rep.read_text())["error"]


def test_promote_onto_cells_the_live_folder_has_nothing_at_records_and_reverts(monkeypatch, tmp_path):
    """A sink of a stock island writes files the live folder never had at those cells: there is nothing to snapshot,
    and the promote must still write its record (it once failed there, after the live writes), so revert removes
    exactly what it created."""
    _fake_mirror(monkeypatch)
    game, src, d = _edited_draft(tmp_path)
    new = "FF9_Data/WorldMap/Disc1/0_1/r8/Block[3][8] Sea3.ff9mesh"
    (d / new).parent.mkdir(parents=True, exist_ok=True)
    (d / new).write_bytes(b"open water")
    (d / T1).write_bytes((src / T1).read_bytes())          # only the new cell is an edit
    before = {k: v for k, v in _tree(src).items() if ".bak-" not in k}
    rec = D.promote(d, game=game, log=lambda *a: None)
    assert rec["cells"] == [[3, 8]] and rec["before"] == {} and (src / new).read_bytes() == b"open water"
    assert D.last_promote(d)["utc"] == rec["utc"]
    D.revert(d, game=game, log=lambda *a: None)
    assert {k: v for k, v in _tree(src).items() if ".bak-" not in k} == before


class _Watched(np.ndarray):
    """A tri-corner array that records a box taken from it again (min / max over it)."""
    log: list = []

    def max(self, *a, **k):
        _Watched.log.append("max")
        return np.ndarray.max(np.asarray(self), *a, **k)

    def min(self, *a, **k):
        _Watched.log.append("min")
        return np.ndarray.min(np.asarray(self), *a, **k)


class _Coast(np.ndarray):
    """A coast array that records how many of its points each broadcast against the tested verts carries."""
    log: list = []

    def __getitem__(self, key):
        if isinstance(key, tuple) and key[:1] == (None,):
            _Coast.log.append(len(self))
        return np.ndarray.__getitem__(self, key)


def test_a_drag_preview_reuses_the_index_and_reads_only_the_coast_near_it():
    """A forest ghost drag cost 45-55 ms per mouse move on the GUI thread, 93% in footprint_preview: it took every
    tri's plan box again (SoupIndex already holds them: lo, hi) and measured every tested vertex against EVERY coast
    point of the island (PERF.md 6, C3). Neither now, and the answer is the same. (The coast fence watches the
    culled array itself: an asarray of the coast hid it, so the cull could go unnoticed -- review, CR-3.)"""
    ix = FE.SoupIndex(IN.soup_from_blocks({(0, 0): _mains_grid()}))
    far = [[5000.0 + i, 5000.0] for i in range(50)]
    ix.coast = np.vstack([ix.coast.reshape(-1, 2), [[30.0, -45.0]], far])   # one by the rim, many far off
    poly = [(20.0, -20.0), (40.0, -20.0), (40.0, -40.0), (20.0, -40.0)]
    want = FE.footprint_preview(ix, poly)
    assert want["why"] == "the coast rim" and want["where"]           # the coast check ran, and decided
    full = len(ix.coast)
    ix.corner, ix.coast = ix.corner.view(_Watched), ix.coast.view(_Coast)
    _Watched.log, _Coast.log = [], []
    got = FE.footprint_preview(ix, poly)
    assert _Watched.log == [] and got == want
    assert _Coast.log and max(_Coast.log) <= full - len(far)           # the far points were never measured

