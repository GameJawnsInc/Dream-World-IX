"""A prefab TURNED (rung P5, studies/overworld-editor/PREFABS.md, world/prefab.py THE QUARTER TURN).

``world-prefab NAME --cell BX,BY --turn 90|180|270`` places the WALKED land turned: composed at its catalog site and
held to the catalog, then every block moved to its turned place with its content turned about the block centre
(``transplant._rot_xz``), written through the kit's ledgered writers. The identity is the catalog's land with exactly
that turn applied. Hermetic tests cover the turn's arithmetic (the block map, the point map, the local turn, all one
rigid motion), the turned digest against the turned writer, every refusal, and the recipe / fuse / CLI plumbing; the
install-gated ones turn the shipped desert peak isle for real and prove the turned identity CAN fail.
"""
from __future__ import annotations

import itertools
import json

import pytest

from ff9mapkit.world import fuse as FU, mesh as M, prefab as PF
from ff9mapkit.world.extract import BlockMesh, CH_NRM, CH_POS, CH_TAN, CH_UV

SQ = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 0], [0, 1], [1, -1], [1, 0], [1, 1]]
COMMA = [[0, 0], [1, 0], [1, 1], [2, 0], [2, 1]]


def _p(foot, **kw):
    return {"name": "x", "status": "qualified", "footprint": foot, "fingerprint": "f" * 64,
            "rows": [{"table": "transplant", "cell": [0, 0], "donor": [9, 5]}], **kw}


# ---------------------------------------------------------------- the arithmetic: one rigid motion
def test_a_square_footprint_turns_onto_itself_and_a_rect_swaps_its_sides_from_the_same_corner():
    for t in PF.TURNS:
        assert PF.turned(_p(SQ), t)["footprint"] == sorted(SQ)
    v = PF.turned(_p(COMMA), 90)
    xs, ys = [b[0] for b in v["footprint"]], [b[1] for b in v["footprint"]]
    assert (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1) == (2, 3)          # 3x2 -> 2x3
    assert (min(xs), min(ys)) == (0, 0)                                       # the rect starts where it did
    assert v["source_footprint"] == COMMA and v["turn"] == 90 and PF.turned(_p(COMMA), 0)["footprint"] == COMMA


def test_four_quarter_turns_are_the_identity_and_two_are_a_half_turn():
    p = _p(COMMA)
    for b in COMMA:
        r = tuple(b)
        for _ in range(4):
            r = PF._rot_block(r, 1)
        assert r == tuple(b)
        assert PF._rot_block(b, 2) == PF._rot_block(PF._rot_block(b, 1), 1)
    for x, z in itertools.product((0.0, 1.5, 33.25, 64.0), (0.0, -2.5, -40.75, -64.0)):
        assert PF._local_turn(x, z, 4) == (x, z)
    assert sorted(PF.turned(p, 180)["footprint"]) == sorted([[2 - b[0], 1 - b[1]] for b in COMMA])


def test_the_local_turn_is_transplant_s_own_rot_xz():
    from ff9mapkit.world.transplant import _rot_dir, _rot_xz
    for n in range(4):
        for x, z in itertools.product((0.0, 4.0, 17.3, 64.0), (0.0, -4.0, -51.9, -64.0)):
            assert repr(PF._local_turn(x, z, n)) == repr(_rot_xz(x, z, n))    # bit for bit (a -0.0 differs)
            assert PF._dir_turn(x, z, n) == _rot_dir(x, z, n)


@pytest.mark.parametrize("foot", [SQ, COMMA, [[0, 0], [0, 1]]])
@pytest.mark.parametrize("turn", [90, 180, 270])
def test_the_point_map_is_the_block_map_with_the_local_turn(foot, turn):
    """turn_point (the ghost's map) and the files' map (a block to its turned label, its content turned about the
    block centre) are the same rigid motion, at every anchor, across the x seam too."""
    from ff9mapkit.world.extract import block_world_origin
    p = _p(foot)
    for cell in ((10, 9), (23, 5), (0, 12)):
        for b in foot:
            label = PF.label_of(b, cell)
            for lx, lz in ((3.0, -5.0), (61.0, -60.0), (32.0, -32.0)):
                _ox, oz = block_world_origin(*label)
                x = 64.0 * (cell[0] + PF.rel_block(label, cell)[0]) + lx      # unwrapped beside the anchor
                tl = PF.label_of(PF.turn_rel(p, PF.rel_block(label, cell), turn), cell)
                tx, tz = PF.turn_point(x, oz + lz, p, cell, turn)
                ux, uz = PF._local_turn(lx, lz, turn // 90)
                tox, toz = block_world_origin(*tl)
                assert (tx % 1536.0, tz) == pytest.approx((tox + ux, toz + uz), abs=1e-9)


def test_a_bad_turn_refuses_by_name():
    with pytest.raises(PF.PrefabRefused, match="quarter turns") as e:
        PF.turned(_p(SQ), 45)
    assert e.value.gate == "turn"


# ---------------------------------------------------------------- the catalog
def _cat(tmp_path, extra: str):
    body = ('[[prefab]]\nname = "x"\nstatus = "qualified"\n' + extra +
            '\n[[prefab.rows]]\ntable = "transplant"\ncell = [0, 0]\ndonor = [9, 5]\n')
    p = tmp_path / "prefabs.toml"
    p.write_text(body, encoding="utf-8")
    return p


def test_a_prefab_turns_only_when_its_entry_says_so_and_names_its_site(tmp_path):
    assert PF.turns_of(PF.load_catalog(_cat(tmp_path, ""))[0]) == (0,)
    assert PF.turns_of(PF.load_catalog(_cat(tmp_path, "turns = [0, 90]\nfingerprint_cell = [1, 2]"))[0]) == (0, 90)
    for bad, why in (("turns = [0, 90]", "fingerprint_cell"), ("turns = [90]\nfingerprint_cell = [1, 2]", "0 among"),
                     ("turns = [0, 45]\nfingerprint_cell = [1, 2]", "quarter turns"),
                     ("turns = [0, 90]\nfingerprint_cell = [1, 2]\nwalked_turns = [180]", "walked_turns")):
        with pytest.raises(ValueError, match=why):
            PF.load_catalog(_cat(tmp_path, bad))


def test_the_shipped_turns_are_well_formed():
    for p in PF.load_catalog():
        assert 0 in PF.turns_of(p)
        if PF.turns_of(p) != (0,):
            assert len(p["fingerprint_cell"]) == 2, p["name"]
    assert PF.turns_of(PF.get("beach-chain")) == (0,)                      # Chocobo's Lagoon's object pins it


# ---------------------------------------------------------------- the turned digest IS the turned writer
def _bm(label, part, tris, *, nrm=(0.6, 0.8, 0.0)):
    pos, nr, uvs, tan, flat, out = [], [], [], [], [], []
    for tri in tris:
        base = len(pos)
        for c in tri:
            pos.append(list(c))
            nr.append(list(nrm))
            uvs.append([c[0] / 64.0, -c[2] / 64.0])
            tan.append([float(4 * 17 + 1), 0.25, 0.0, 1.0])
            flat.append(len(pos) - 1)
        out.append([base, base + 1, base + 2])
    return BlockMesh(name=f"Block[{label[0]}][{label[1]}] {part}", disc=1, x=label[0], y=label[1], lod="0_1",
                     vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nr, CH_UV: uvs, CH_TAN: tan},
                     flat_index=flat, tris=out, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


TRI = [(1.0000001, 3.25, -0.5), (9.3, 4.0, -0.5), (1.0000001, 3.1, -7.77)]   # off-lattice floats, as a real coast
TRI2 = [(40.0, 3.0, -12.0), (63.9, 2.0, -12.0), (40.0, 1.0, -63.3)]


@pytest.fixture
def staged(tmp_path, monkeypatch):
    """A staged folder (anchor (5, 5)): two blocks of a comma-shaped footprint, Terrain + Sea4 + a Donor.txt each."""
    from ff9mapkit import config
    game = tmp_path / "game"
    game.mkdir()
    monkeypatch.setattr(config, "find_game_path", lambda g=None: game)
    src = tmp_path / "src"
    for rel, tris in (((0, 0), [TRI]), ((2, 1), [TRI, TRI2])):
        label = PF.label_of(rel, (5, 5))
        for part in ("Terrain", "Sea4"):
            dest = src / M.override_relpath(1, *label, "0_1", part)
            dest.parent.mkdir(parents=True, exist_ok=True)
            M.write_ff9mesh(_bm(label, part, tris), dest)
        M.deploy_donor_sidecar(13, 8, mod_folder=str(src), disc=1, x=label[0], y=label[1], backup=False)
    return {"src": src, "game": game, "tmp": tmp_path, "prefab": _p(COMMA)}


@pytest.mark.parametrize("turn", [90, 180, 270])
def test_the_turned_writer_writes_what_the_turned_fingerprint_names(staged, turn):
    """The writer (BlockMesh, deploy_override) and the digest (read_ff9mesh, its own arithmetic) are separate paths;
    the turned placement on another anchor -- across the x seam -- is exactly the walked land turned."""
    p, dst = staged["prefab"], staged["tmp"] / "dst"
    PF.write_turned(staged["src"], (5, 5), p, turn, dst, (23, 9), skip_mirror=True)
    blocks = PF.written_blocks(dst)
    view = PF.turned(p, turn)
    assert sorted(PF.rel_block(b, (23, 9)) for b in blocks) == sorted(
        tuple(PF.turn_rel(p, r, turn)) for r in ((0, 0), (2, 1)))
    assert {b for b in blocks} <= set(PF.footprint_labels(view, (23, 9)))
    want = PF.fingerprint(staged["src"], (5, 5), PF.written_blocks(staged["src"]), turn=turn, prefab=p,
                          to_cell=(23, 9))
    assert PF.fingerprint(dst, (23, 9), blocks) == want
    assert PF.fingerprint(dst, (23, 9), blocks) != PF.fingerprint(staged["src"], (5, 5),
                                                                   PF.written_blocks(staged["src"]))


def test_the_turn_turns_positions_and_land_normals_and_keeps_uvs_tangents_sea_normals_and_the_donor(staged):
    p, dst = staged["prefab"], staged["tmp"] / "dst"
    PF.write_turned(staged["src"], (5, 5), p, 90, dst, (5, 5), skip_mirror=True)
    s_label, t_label = PF.label_of((0, 0), (5, 5)), PF.label_of(PF.turn_rel(p, (0, 0), 90), (5, 5))
    for part, nrm in (("Terrain", (0.0, 0.8, 0.6)), ("Sea4", (0.6, 0.8, 0.0))):
        a = M.read_ff9mesh(staged["src"] / M.override_relpath(1, *s_label, "0_1", part))
        b = M.read_ff9mesh(dst / M.override_relpath(1, *t_label, "0_1", part))
        assert b["uvs"] == a["uvs"] and b["tangents"] == a["tangents"] and b["indices"] == a["indices"]
        for va, vb in zip(a["verts"], b["verts"]):
            assert (vb[0], vb[1], vb[2]) == pytest.approx((-va[2], va[1], va[0] - 64.0), abs=1e-5)
        assert b["normals"][0] == pytest.approx(nrm, abs=1e-6)               # land turned (0.6,0,.) -> (0,.,0.6)
    donor = dst / M.donor_sidecar_relpath(1, *t_label, "0_1")
    assert donor.read_text(encoding="utf-8") == "13,8"
    rows = [json.loads(r) for r in (dst / ".ff9world.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {r["part"] for r in rows} >= {"Terrain", "Sea4", "Donor"}          # every file ledgered


def test_a_turn_that_moves_the_wrong_way_is_not_the_catalog_s_land(staged):
    """The turned identity CAN fail: land turned 270 is not the land turned 90 (and neither is the walked land)."""
    p, dst = staged["prefab"], staged["tmp"] / "dst"
    PF.write_turned(staged["src"], (5, 5), p, 270, dst, (10, 9), skip_mirror=True)
    got = PF.fingerprint(dst, (10, 9), PF.written_blocks(dst))
    for turn in (90, 180):
        assert got != PF.fingerprint(staged["src"], (5, 5), PF.written_blocks(staged["src"]), turn=turn, prefab=p,
                                     to_cell=(10, 9))


def test_a_donor_prefab_part_the_prefab_does_not_override_blocks_the_turn(staged, monkeypatch):
    """A part the Donor.txt prefab draws but no file overrides would ride that prefab UNTURNED."""
    monkeypatch.setattr(PF, "_donor_parts", lambda d, game=None: {"terrain", "sea4"})
    assert PF.turn_blockers(staged["src"]) == {}
    monkeypatch.setattr(PF, "_donor_parts", lambda d, game=None: {"terrain", "sea4", "object"})
    assert set(PF.turn_blockers(staged["src"])) == {PF.label_of((0, 0), (5, 5)), PF.label_of((2, 1), (5, 5))}
    assert all(v == ["object"] for v in PF.turn_blockers(staged["src"]).values())


# ---------------------------------------------------------------- place(turn=)
@pytest.fixture
def fake(tmp_path, monkeypatch):
    """A turnable one-prefab catalog, a tmp install, and stand-ins for every staging: a turned stage that is the
    catalog's land turned. Each test breaks one."""
    from ff9mapkit import config
    from ff9mapkit.world import island as I
    game = tmp_path / "game"
    game.mkdir()
    monkeypatch.setattr(config, "find_game_path", lambda g=None: game)
    cat = tmp_path / "prefabs.toml"
    cat.write_text('[[prefab]]\nname = "x"\nstatus = "qualified"\nfingerprint = "' + "f" * 64 + '"\n'
                   'fingerprint_cell = [1, 14]\nturns = [0, 90, 180]\nfootprint = '
                   + json.dumps(COMMA) + '\n[[prefab.rows]]\ntable = "island"\ncenter = [32.0, 32.0]\nseed = 5.0\n',
                   encoding="utf-8")
    calls = {"turned": [], "written": [], "plain": []}

    def stage_turned(entry, turn, cell, game=None):
        calls["turned"].append((turn, tuple(cell)))
        root, src = tmp_path / f"t{len(calls['turned'])}", tmp_path / f"s{len(calls['turned'])}"
        root.mkdir(), src.mkdir()
        v = PF.turned(entry, turn)
        return {"root": root, "source": {"root": src, "blocks": []}, "fingerprint": "t" * 64, "nav": {},
                "blocks": PF.footprint_labels(v, cell), "footprint": sorted(tuple(b) for b in v["footprint"])}
    monkeypatch.setattr(PF, "stage_turned", stage_turned)
    monkeypatch.setattr(PF, "stage", lambda *a, **k: calls["plain"].append(a) or pytest.fail("turn 0 staged"))
    monkeypatch.setattr(PF, "write_turned", lambda *a, **k: calls["written"].append((a, k)))
    monkeypatch.setattr(PF, "nav_settled", lambda *a, **k: {})
    monkeypatch.setattr(PF, "stock_ground", lambda *a, **k: {})
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: "t" * 64)
    monkeypatch.setattr(I, "_real_block_parts", lambda b, disc=1, game=None: {})
    return {"cat": cat, "calls": calls, "tmp": tmp_path, "game": game}


def _place(fake, cell=(10, 9), **kw):
    kw.setdefault("stack", ())
    return PF.place("x", cell, "Target", catalog=fake["cat"], log=lambda *a: None, **kw)


def test_a_turned_placement_stages_turned_and_writes_through_the_turned_writer(fake):
    rep = _place(fake, turn=90, skip_mirror=True)
    assert fake["calls"]["turned"] == [(90, (10, 9))] and len(fake["calls"]["written"]) == 1
    (args, kw) = fake["calls"]["written"][0]
    assert args[3] == 90 and args[5] == (10, 9) and kw["skip_mirror"] is True
    assert rep["turn"] == 90 and rep["identity"].startswith("clean site: the catalog's land turned 90")
    assert sorted(tuple(b) for b in rep["blocks"]) == PF.footprint_labels(PF.turned(PF.get("x", fake["cat"]), 90),
                                                                           (10, 9))


def test_a_turn_the_catalog_does_not_allow_refuses_before_anything(fake):
    with pytest.raises(PF.PrefabRefused, match="does not turn 270") as e:
        _place(fake, turn=270)
    assert e.value.gate == "turn" and not fake["calls"]["turned"]


def test_a_turned_footprint_on_stock_land_refuses_by_the_open_ocean_law(fake, monkeypatch):
    from ff9mapkit.world import island as I
    v = PF.turned(PF.get("x", fake["cat"]), 90)
    hit = sorted(set(PF.footprint_labels(v, (10, 9))) - set(PF.footprint_labels(PF.get("x", fake["cat"]), (10, 9))))[0]
    # (only the TURNED footprint covers it)
    monkeypatch.setattr(I, "_real_block_parts", lambda b, disc=1, game=None: {"terrain": 4} if b == hit else {})
    with pytest.raises(PF.PrefabRefused, match="open ocean") as e:
        _place(fake, turn=90)
    assert e.value.where == [hit] and e.value.gate == "window" and not fake["calls"]["turned"]


def test_the_clear_window_is_the_turned_one(fake, tmp_path):
    """Review P5: the block planted must lie in the TURNED window and outside the walked one's footprint AND ring, or
    the test passes on a window computed from the unturned entry."""
    entry = PF.get("x", fake["cat"])
    v = PF.turned(entry, 90)
    walked = set(PF.footprint_labels(entry, (10, 9)))
    walked |= PF._ring(walked) | PF.reads(entry, (10, 9))
    turned_win = set(PF.footprint_labels(v, (10, 9)))
    turned_win |= PF._ring(turned_win) | PF.reads(v, (10, 9))
    only_turned = sorted(turned_win - walked)[0]
    from .test_world_prefab import _put
    _put(fake["game"] / "Target", only_turned)
    with pytest.raises(PF.PrefabRefused, match="already holds land") as e:
        _place(fake, turn=90)
    assert only_turned in e.value.where


def test_a_turned_identity_that_is_not_the_turn_refuses_and_writes_nothing(fake, monkeypatch):
    seq = iter(["w" * 64, "t" * 64])
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: next(seq))
    with pytest.raises(PF.PrefabRefused, match="NOT the catalog's land turned") as e:
        _place(fake, turn=90)
    assert e.value.gate == "identity" and not fake["calls"]["written"]


def test_turned_land_beside_stock_land_is_judged_outside_the_margin_and_its_margin_settled(fake, monkeypatch):
    masks = []
    monkeypatch.setattr(PF, "stock_ground", lambda *a, **k: {(9, 7): [(600.0, -500.0)]})
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: masks.append(kw.get("mask_tri")) or "t" * 64)
    rep = _place(fake, turn=90, dry_run=True)
    assert rep["identity"].startswith("nav margin") and masks[0] is not None and masks[1] is not None
    monkeypatch.setattr(PF, "nav_settled", lambda *a, **k: {53: 4})
    fake["calls"]["turned"].clear()
    stage = PF.stage_turned

    def unsettled(*a, **k):
        st = stage(*a, **k)
        st["nav"] = {53: 4}
        return st
    monkeypatch.setattr(PF, "stage_turned", unsettled)
    with pytest.raises(PF.PrefabRefused, match="would still re-class") as e:
        _place(fake, turn=90, dry_run=True)
    assert e.value.gate == "nav"


def test_turn_0_is_the_plain_placement_unchanged(fake, monkeypatch):
    composed = []
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None, keep=False: {
        "fingerprint": "f" * 64, "footprint": sorted(tuple(b) for b in COMMA), "nav": {},
        "blocks": sorted(PF.label_of(b, cell) for b in COMMA), "root": None})
    monkeypatch.setattr(PF, "_compose", lambda folder, rows, **kw: composed.append(rows))
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: "f" * 64)
    rep = _place(fake, skip_mirror=True)
    assert rep["turn"] == 0 and len(composed) == 1 and not fake["calls"]["turned"] and not fake["calls"]["written"]


# ---------------------------------------------------------------- the recipe, the fuse row, the CLI
def test_a_turned_step_s_row_label_cells_and_windows_are_the_turned_ones(monkeypatch, tmp_path):
    from ff9mapkit.world import recipe as RC
    cat = tmp_path / "c.toml"
    cat.write_text('[[prefab]]\nname = "x"\nstatus = "qualified"\nfingerprint = "' + "f" * 64 + '"\n'
                   'fingerprint_cell = [1, 14]\nturns = [0, 90]\nfootprint = ' + json.dumps(COMMA) +
                   '\n[[prefab.rows]]\ntable = "island"\ncenter = [32.0, 32.0]\nseed = 5.0\n', encoding="utf-8")
    real = PF.get
    monkeypatch.setattr(PF, "get", lambda name, path=None: real(name, cat))
    row = RC.row_for(["world-prefab", "x", "--cell", "10,9", "--turn", "90", "--mod-folder", "F"])
    assert row == {"table": "prefab", "name": "x", "cell": [10, 9], "turn": 90}
    assert "turn" not in RC.row_for(["world-prefab", "x", "--cell", "10,9", "--mod-folder", "F"])
    assert RC.label(row) == "prefab x on block (10, 9), turned 90"
    v = PF.turned(real("x", cat), 90)
    assert sorted(RC.row_cells(row)) == PF.footprint_labels(v, (10, 9))
    assert RC.anchor(row) == PF.footprint_center(v, (10, 9)) != RC.anchor({**row, "turn": 0})
    win = RC.replay_window({"row": row, "cells": []})
    assert set(PF.footprint_labels(v, (10, 9))) <= win


def test_a_fuse_prefab_row_forwards_its_turn(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(PF, "place", lambda *a, **k: seen.append(k["turn"]))
    for doc, want in (({"name": "x", "cell": [1, 1], "turn": 90}, 90), ({"name": "x", "cell": [1, 1]}, 0)):
        FU.compose_layout(str(tmp_path), {"prefab": [doc]}, game=tmp_path, dry_run=True)
        assert seen[-1] == want


def test_the_cli_takes_turn_writes_a_turned_recipe_row_and_refuses_a_turned_fingerprint(tmp_path, capsys):
    from ff9mapkit import cli
    out = tmp_path / "r.toml"
    assert cli.main(["world-prefab", "desert-peak-isle", "--cell", "10,9", "--turn", "90", "--recipe-out",
                     str(out)]) == 0                       # no --mod-folder: the recipe alone
    from ff9mapkit.world import recipe as RC
    assert RC.loads(out.read_text(encoding="utf-8")) == [
        {"table": "prefab", "name": "desert-peak-isle", "cell": [10, 9], "turn": 90}]
    # review P5: nothing is written by a refused invocation -- a turned fingerprint, or a turn the catalog forbids
    for name, bad, code in (("desert-peak-isle", ["--cell", "1,14", "--turn", "90", "--fingerprint"], 2),
                            ("beach-chain", ["--cell", "19,1", "--turn", "90"], 1)):
        o = tmp_path / f"no{code}.toml"
        assert cli.main(["world-prefab", name, *bad, "--recipe-out", str(o)]) == code and not o.exists()
    err = capsys.readouterr().err
    assert "turn 0" in err and "does not turn 90" in err and "Lagoon" in err


def test_a_hand_written_turn_0_is_the_card_s_row():
    from ff9mapkit.world import recipe as RC
    assert RC.canon({"table": "prefab", "name": "x", "cell": [1, 1], "turn": 0}) == RC.canon(
        RC.row_for(["world-prefab", "x", "--cell", "1,1", "--mod-folder", "F"]))


def _cw_local(x, z, n):
    for _ in range(n % 4):
        x, z = z + 64.0, -x
    return x, z


def _cw_block(d, n):
    dx, dy = int(d[0]), int(d[1])
    for _ in range(n % 4):
        dx, dy = -dy, dx
    return dx, dy


@pytest.mark.parametrize("name, bad", [("_local_turn", _cw_local), ("_rot_block", _cw_block)])
def test_a_turn_function_that_is_not_one_rigid_motion_refuses_at_identity(staged, monkeypatch, name, bad):
    """Review P5: the identity's digest turns by transplant's own _rot_xz and places each block by the RIGID point map,
    so a writer whose content turn or block map drifts from them is refused -- not the writer checking itself."""
    p, src = staged["prefab"], staged["src"]
    dst = staged["tmp"] / f"bad-{name}"
    with monkeypatch.context() as m:                    # the regression is in the module: both sides see it
        m.setattr(PF, name, bad)
        PF.write_turned(src, (5, 5), p, 90, dst, (10, 9), skip_mirror=True)
        want = PF.fingerprint(src, (5, 5), PF.written_blocks(src), turn=90, prefab=p, to_cell=(10, 9))
        got = PF.fingerprint(dst, (10, 9), PF.written_blocks(dst))
    assert got != want


def test_manifest_step_refuses_drift_records_its_files_and_a_waiver_writes(tmp_path, monkeypatch):
    from ff9mapkit import config
    monkeypatch.setattr(config, "find_game_path", lambda g=None: tmp_path)
    root = tmp_path / "F"
    f = root / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r1" / "Block[1][1] Terrain.ff9mesh"

    def write(data):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        return "done"
    assert FU.manifest_step("F", "a", {}, lambda: write(b"one")) == "done"
    man = json.loads((root / "FF9_Data" / "WorldMap" / "world_manifest.json").read_text(encoding="utf-8"))
    assert list(man["entries"][0]["files"]) == ["FF9_Data/WorldMap/Disc1/0_1/r1/Block[1][1] Terrain.ff9mesh"]
    f.write_bytes(b"hand edit")
    with pytest.raises(ValueError, match="manifest-drift"):
        FU.manifest_step("F", "b", {}, lambda: write(b"two"))
    assert f.read_bytes() == b"hand edit"
    FU.manifest_step("F", "b", {}, lambda: write(b"two"), allow_overwrite=True)
    assert f.read_bytes() == b"two"


def test_a_turned_placement_writes_under_the_manifest_law(fake, monkeypatch):
    seen = []
    monkeypatch.setattr(FU, "manifest_step", lambda folder, label, spec, write, **kw: seen.append((label, spec, kw))
                        or write())
    _place(fake, turn=90, skip_mirror=True)
    assert seen == [("prefab x turn 90", {"name": "x", "cell": [10, 9], "turn": 90},
                     {"game": None, "allow_overwrite": False})] and len(fake["calls"]["written"]) == 1

    def drift(*a, **k):
        raise ValueError("manifest-drift: x")
    monkeypatch.setattr(FU, "manifest_step", drift)
    with pytest.raises(PF.PrefabRefused, match="manifest-drift") as e:
        _place(fake, turn=90, skip_mirror=True)
    assert e.value.gate == "compose"


def test_a_turned_accept_into_a_draft_holds_the_draft_laws_to_the_turned_footprint(fake, monkeypatch):
    from ff9mapkit.world import draft as D
    laws, waived = [], []
    monkeypatch.setattr(D, "stands_in_for", lambda folder: "FF9CustomMap-world")
    monkeypatch.setattr(PF, "_draft_laws", lambda prefab, *a, **k: laws.append(prefab))
    monkeypatch.setattr(FU, "manifest_step", lambda folder, label, spec, write, **kw: waived.append(
        kw["allow_overwrite"]) or write())
    rep = _place(fake, turn=90)
    assert laws[0]["turn"] == 90 and laws[0]["footprint"] == PF.turned(PF.get("x", fake["cat"]), 90)["footprint"]
    assert waived == [True] and rep["written_disc4"].startswith("deferred")


# ---------------------------------------------------------------- install-gated: the shipped land, turned for real
def test_the_desert_peak_isle_turned_is_the_walked_land_turned_and_a_wrong_turn_refuses(tmp_path, monkeypatch):
    """Turned 90 onto the clean site (1,16): world-prefab's own identity passes on real bytes with the full fingerprint,
    and beside stock land at (0,12) at the nav-margin tier (measured: evidence/prefab-turn). Then sabotage the writer to
    turn one quarter turn too far and the same placement refuses at identity (the check can fail)."""
    from .test_world_prefab import _install
    _install()
    kw = dict(stack=(), dry_run=True, turn=90, log=lambda *a: None)
    rep = PF.place("desert-peak-isle", (1, 16), str(tmp_path / "T"), **kw)
    assert rep["identity"] == "clean site: the catalog's land turned 90, the full fingerprint"
    # (0,12): across the seam beside (22,13)/(22,14), where the stamp re-classes 15-20 samples of the turned sea
    # (measured, evidence/prefab-turn) -- a turned write that skipped the stamp is refused here
    rep = PF.place("desert-peak-isle", (0, 12), str(tmp_path / "T1"), **kw)
    assert rep["identity"].startswith("nav margin: the catalog's land turned 90")
    real = PF.write_turned
    monkeypatch.setattr(PF, "write_turned", lambda src, sc, p, turn, *a, **k: real(src, sc, p, (turn + 90) % 360,
                                                                                   *a, **k))
    with pytest.raises(PF.PrefabRefused, match="NOT the catalog's land turned") as e:
        PF.place("desert-peak-isle", (1, 16), str(tmp_path / "T2"), **kw)
    assert e.value.gate == "identity"


def test_a_turned_carry_unit_writes_for_real_its_ledger_and_manifest_with_it(tmp_path):
    """The comma turned 90, written for real (no mirror) into a scratch folder: the written land is the staged land,
    every file is ledgered, and the manifest names them."""
    from .test_world_prefab import _install
    _install()
    rep = PF.place("comma-isle", (2, 16), str(tmp_path / "T"), stack=(), skip_mirror=True, turn=90,
                   log=lambda *a: None)
    assert rep["written_fingerprint"] == rep["staged"]
    root = tmp_path / "T"
    files = sorted(p.relative_to(root).as_posix() for p in (root / "FF9_Data" / "WorldMap" / "Disc1").rglob("*")
                   if p.is_file() and ".bak-" not in p.name)
    man = json.loads((root / "FF9_Data" / "WorldMap" / "world_manifest.json").read_text(encoding="utf-8"))
    assert sorted(man["entries"][-1]["files"]) == files and man["entries"][-1]["spec"]["turn"] == 90
    ledgered = {(tuple(r["cell"]), r["part"]) for r in map(json.loads, (root / ".ff9world.jsonl").read_text(
        encoding="utf-8").splitlines())}
    assert len(ledgered) == len(files)


def test_the_beach_chain_cannot_turn_because_its_lagoon_object_rides_a_donor_prefab():
    """Measured: staged at (19,1), its (21,1) block's Donor.txt prefab draws an Object no file overrides (Chocobo's
    Lagoon, donor (9,17)); turned, it would stand unturned. turn_blockers finds it by itself, and the catalog agrees."""
    from .test_world_prefab import _install
    _install()
    p = PF.get("beach-chain")
    st = PF.stage(p, (19, 1), keep=True)
    try:
        assert st["fingerprint"] == p["fingerprint"]
        assert PF.turn_blockers(st["root"]) == {(21, 1): ["object"]}
    finally:
        PF._drop(st)
    assert PF.turns_of(p) == (0,)



# ---------------------------------------------------------------- the mutation round's fences (P5)
def test_staging_a_turn_refuses_a_riding_part_before_writing_anything(monkeypatch, tmp_path):
    """stage_turned runs turn_blockers on the walked land before it turns a single file."""
    written = []
    src = tmp_path / "src"
    src.mkdir()
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None, keep=False: {
        "fingerprint": "f" * 64, "root": src, "blocks": [], "footprint": [], "nav": {}})
    monkeypatch.setattr(PF, "turn_blockers", lambda root, game=None: {(21, 1): ["object"]})
    monkeypatch.setattr(PF, "write_turned", lambda *a, **k: written.append(a))
    p = _p(COMMA, fingerprint_cell=[3, 3], turns=[0, 90])
    with pytest.raises(PF.PrefabRefused, match="UNTURNED") as e:
        PF.stage_turned(p, 90, (10, 9))
    assert e.value.gate == "turn" and not written


def test_a_turned_stage_that_covers_other_blocks_is_not_the_turned_footprint(fake, monkeypatch):
    stage = PF.stage_turned

    def walked_foot(entry, turn, cell, game=None):
        st = stage(entry, turn, cell, game=game)
        st["footprint"] = sorted(tuple(b) for b in entry["footprint"])      # the walked rect, not the turned one
        return st
    monkeypatch.setattr(PF, "stage_turned", walked_foot)
    with pytest.raises(PF.PrefabRefused, match="IDENTITY BROKEN") as e:
        _place(fake, turn=90)
    assert e.value.gate == "identity" and not fake["calls"]["written"]


def test_a_turned_prefab_s_read_windows_are_the_walked_ones_turned():
    """A relief row's read window turns with the land (a forest 140u east of the anchor reads east; turned 90 it
    reads where east turned to)."""
    p = {"name": "r", "footprint": COMMA, "rows": [
        {"table": "island", "center": [96.0, 32.0], "seed": 1.0},
        {"table": "forest", "center": [180.0, 32.0], "reach": 40.0}]}
    cell = (10, 9)
    walked = PF.reads(p, cell)
    v = PF.turned(p, 90)
    want = {PF.label_of(PF.turn_rel(p, PF.rel_block(b, cell), 90), cell) for b in walked}
    assert PF.reads(v, cell) == want != walked
