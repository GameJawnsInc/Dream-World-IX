"""THE EDIT-ATOMIC DISC-4 MIRROR (terrain study O2; defects 7-9).

* Defect 9: the copy gate compared each real part as ORDERED arrays, so 10 land cells holding the same triangles in a
  different buffer order on disc 4 were refused. It now compares triangle multisets.
* Defect 8: the gate ran per cell, so a multi-cell edit across a copyable and a refused cell left disc 4 with the
  edit on one side of their border and stock on the other (a 4.0u step in the study's G3 demo; 7.5% of random
  multi-cell reshapes). ``auto_mirror`` now mirrors a group of adjacent written cells whole or not at all.
* The replay: ``world-terrain``/``world-deploy`` hand ``auto_mirror`` their own call re-run on disc 4, which edits
  disc 4's own ground where it cannot be copied.

Hermetic: a fake mod tree under tmp_path; the real map's asset layer stubbed at ``extract._worldmap_env`` and
``extract.read_block`` (the same seams as ``test_discmirror.py``). The end-to-end run on real data is the study's
``gap_disc4_edit_reach/o2_postfix.py``.
"""
from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import discmirror as DM, extract as X, terrain as T
from ff9mapkit.world.extract import BlockMesh, CH_NRM, CH_POS, CH_TAN, CH_UV, encode_id

MOD = "FF9CustomMap"
_TRI_A = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
_TRI_B = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 2.0]]
_TRI_C = [[4.0, 0.0, 0.0], [5.0, 0.0, 0.0], [4.0, 0.0, 1.0]]


def _mk(name, *, disc, x, y, verts):
    n = len(verts)
    idall = float(encode_id(topograph=0))
    flat = list(range(n))
    return BlockMesh(name=name, disc=disc, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: [list(v) for v in verts], CH_NRM: [[0.0, 1.0, 0.0]] * n,
                                  CH_UV: [[0.25 * i, 0.5 * i] for i in range(n)],
                                  CH_TAN: [[idall, 0.0, 0.0, 1.0]] * n},
                     flat_index=flat, tris=[flat[i:i + 3] for i in range(0, n, 3)], raw_vbuf=b"", raw_ibuf=b"",
                     use32=True, submeshes=[])


class _Env:
    def __init__(self, container):
        self.container = list(container)


def _cont(disc, x, y, part):
    return f"assets/resources/worldmap/disc{disc}/0_1/r{y}/block[{x}][{y}] {part}.asset"


def _patch(monkeypatch, blocks):
    """``blocks`` = {(disc, x, y, part): BlockMesh}: the REAL map, both discs."""
    cont = {}
    for (d, x, y, p) in blocks:
        cont.setdefault(d, []).append(_cont(d, x, y, p))
    monkeypatch.setattr(X, "_worldmap_env", lambda disc, game=None: _Env(cont.get(disc, [])))

    def rb(x, y, *, disc=1, lod="0_1", part="terrain", game=None):
        key = (disc, x, y, part.lower())
        if key not in blocks:
            raise ValueError(f"no fake block for {key}")
        return blocks[key]
    monkeypatch.setattr(X, "read_block", rb)


# ---- the order-invariant gate (defect 9) ---------------------------------------------------------------------------

def _rotated(bm):
    """Every triangle's corners rotated by one (same winding) and the triangles in reverse buffer order."""
    v = bm.verts
    tris = [v[i:i + 3] for i in range(0, len(v), 3)]
    out = [t[1:] + t[:1] for t in reversed(tris)]
    return [c for t in out for c in t]


def test_parts_identical_ignores_buffer_order_and_corner_rotation(monkeypatch):
    a = _mk("Block[9][9] Terrain", disc=1, x=9, y=9, verts=_TRI_A + _TRI_C)
    b = _mk("Block[9][9] Terrain", disc=4, x=9, y=9, verts=_rotated(a))
    b = dataclasses.replace(b, chan_arrays={**b.chan_arrays, CH_UV: [a.uvs[i] for i in (4, 5, 3, 1, 2, 0)]})
    assert a.verts != b.verts                                         # the ordered compare refused this cell
    _patch(monkeypatch, {(1, 9, 9, "terrain"): a, (4, 9, 9, "terrain"): b})
    assert DM._parts_identical((9, 9), "terrain", 1, 4) is True


def test_parts_identical_still_sees_a_moved_vertex_and_a_flipped_winding(monkeypatch):
    a = _mk("Block[9][9] Terrain", disc=1, x=9, y=9, verts=_TRI_A + _TRI_C)
    moved = _mk("Block[9][9] Terrain", disc=4, x=9, y=9, verts=_TRI_B + _TRI_C)
    _patch(monkeypatch, {(1, 9, 9, "terrain"): a, (4, 9, 9, "terrain"): moved})
    assert DM._parts_identical((9, 9), "terrain", 1, 4) is False
    flipped = _mk("Block[9][9] Terrain", disc=4, x=9, y=9, verts=[_TRI_A[0], _TRI_A[2], _TRI_A[1]] + _TRI_C)
    flipped = dataclasses.replace(flipped, chan_arrays={**flipped.chan_arrays,
                                                        CH_UV: [a.uvs[i] for i in (0, 2, 1, 3, 4, 5)]})
    _patch(monkeypatch, {(1, 9, 9, "terrain"): a, (4, 9, 9, "terrain"): flipped})
    assert DM._parts_identical((9, 9), "terrain", 1, 4) is False


# ---- the edit-atomic mirror (defect 8) -----------------------------------------------------------------------------

@pytest.fixture
def tree(tmp_path, monkeypatch):
    """Deployed Disc1 Terrain overrides at A=(2,3) (copyable), B=(3,3) (refused: disc 4's real ground differs) --
    A and B adjacent -- and C=(10,3) (copyable, far away)."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    src = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r3"
    src.mkdir(parents=True)
    for c in ((2, 3), (3, 3), (10, 3)):
        (src / f"Block[{c[0]}][{c[1]}] Terrain.ff9mesh").write_bytes(f"EDIT-{c}".encode())
    blocks = {}
    for c in ((2, 3), (3, 3), (10, 3)):
        blocks[(1, *c, "terrain")] = _mk(f"Block[{c[0]}][{c[1]}] Terrain", disc=1, x=c[0], y=c[1], verts=_TRI_A)
        blocks[(4, *c, "terrain")] = _mk(f"Block[{c[0]}][{c[1]}] Terrain", disc=4, x=c[0], y=c[1],
                                         verts=_TRI_B if c == (3, 3) else _TRI_A)
    _patch(monkeypatch, blocks)
    return tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r3"


def test_atomic_holds_back_a_cell_whose_edit_spans_a_refused_one(tree):
    log = []
    out = DM.mirror(MOD, cells={(2, 3), (3, 3)}, atomic=True, log=log.append)
    assert out["mirrored"] == [] and out["held"] == [(2, 3)] and not tree.exists()
    assert dict(out["skipped"])[(3, 3)].startswith("real cell differs")
    assert any("NOT MIRRORED: [(2, 3)]" in s and "[(3, 3)]" in s for s in log)


def test_atomic_groups_are_the_connected_cells_only(tree):
    out = DM.mirror(MOD, cells={(2, 3), (3, 3), (10, 3)}, atomic=True, log=lambda *a: None)
    assert [p.name for p in out["mirrored"]] == ["Block[10][3] Terrain.ff9mesh"] and out["held"] == [(2, 3)]


def test_the_standalone_mirror_still_copies_per_cell_and_names_the_border(tree):
    log = []
    out = DM.mirror(MOD, cells={(2, 3), (3, 3)}, log=log.append)
    assert [p.name for p in out["mirrored"]] == ["Block[2][3] Terrain.ff9mesh"] and out["held"] == []
    assert any("WARNING: a refused cell borders a mirrored one at [((2, 3), (3, 3))]" in s for s in log)


def test_components_wrap_the_torus():
    assert DM._components({(0, 5), (23, 5), (12, 5)}) == [{(0, 5), (23, 5)}, {(12, 5)}]
    assert DM._components({(4, 0), (4, 19)}) == [{(4, 0), (4, 19)}]


# ---- the replay ----------------------------------------------------------------------------------------------------

def test_a_refused_cell_replays_the_edit_instead_of_copying(tree):
    calls, log = [], []
    out = DM.mirror(MOD, cells={(2, 3), (3, 3)}, atomic=True, replay=calls.append, log=log.append)
    assert calls == [4] and out["mirrored"] == [] and not tree.exists()
    assert out["replay"]["cells"] == [(2, 3), (3, 3)] and list(out["replay"]["differs"]) == [(3, 3)]
    assert any("REPLAYED (3, 3) on Disc4" in s for s in log)


def test_a_replay_that_refuses_leaves_disc4_alone(tree):
    def refuse(d):
        raise ValueError("ONE-WAY WALL in block (3, 3)")
    log = []
    out = DM.mirror(MOD, cells={(2, 3), (3, 3)}, atomic=True, replay=refuse, log=log.append)
    assert out["mirrored"] == [] and out["replay"] == {"refused": "ONE-WAY WALL in block (3, 3)"}
    assert any("NOT MIRRORED: the replay on Disc4 refused (ONE-WAY WALL" in s for s in log) and not tree.exists()


def test_copyable_cells_copy_and_never_replay(tree):
    calls = []
    out = DM.mirror(MOD, cells={(2, 3)}, atomic=True, replay=calls.append, log=lambda *a: None)
    assert calls == [] and [p.name for p in out["mirrored"]] == ["Block[2][3] Terrain.ff9mesh"]


def test_a_dry_run_plans_the_replay_without_running_it(tree):
    calls = []
    out = DM.mirror(MOD, cells={(2, 3), (3, 3)}, atomic=True, replay=calls.append, dry_run=True,
                    log=lambda *a: None)
    assert calls == [] and out["replay"]["dry_run"] is True


def test_auto_mirror_is_atomic_and_passes_the_replay(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(DM, "mirror", lambda *a, **k: seen.update(k) or {"mirrored": []})
    p = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r3" / "Block[2][3] Terrain.ff9mesh"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"x")
    hook = object()
    DM.auto_mirror([p], mod_folder=MOD, replay=hook, log=lambda *a: None)
    assert seen["atomic"] is True and seen["replay"] is hook and seen["cells"] == {(2, 3)}


# ---- the writers hand in their replay ------------------------------------------------------------------------------

def test_reshape_hands_auto_mirror_a_disc4_replay_of_itself(monkeypatch):
    from types import SimpleNamespace
    from ff9mapkit.world import mesh as M
    monkeypatch.setattr(X, "read_block", lambda bx, by, **k: SimpleNamespace(block=(bx, by)))
    monkeypatch.setattr(X, "block_world_origin", lambda bx, by: (bx * 64, -by * 64))
    monkeypatch.setattr(M, "flatten_region", lambda ter, **k: 5)
    monkeypatch.setattr(M, "deploy_override", lambda ter, **k: Path("x"))
    seen = {}
    monkeypatch.setattr(DM, "auto_mirror", lambda written, **k: seen.update(k))
    T.reshape("MOD", at=(1030.0, -910.0), radius=8.0, flatten=True, height=7.5, seam_taper=2.0)
    calls = []
    monkeypatch.setattr(T, "reshape", lambda mod, **k: calls.append((mod, k)))
    seen["replay"](4)
    mod, k = calls[0]
    assert mod == "MOD" and k["disc"] == 4 and k["skip_mirror"] == DM.REPLAY and k["flatten"] is True
    assert k["at"] == (1030.0, -910.0) and k["radius"] == 8.0 and k["height"] == 7.5 and k["seam_taper"] == 2.0


def test_reshape_into_another_namespace_has_no_replay(monkeypatch):
    from types import SimpleNamespace
    from ff9mapkit.world import mesh as M
    monkeypatch.setattr(X, "read_block", lambda bx, by, **k: SimpleNamespace(block=(bx, by)))
    monkeypatch.setattr(X, "block_world_origin", lambda bx, by: (bx * 64, -by * 64))
    monkeypatch.setattr(M, "deform_radial", lambda ter, **k: 5)
    monkeypatch.setattr(M, "deploy_override", lambda ter, **k: Path("x"))
    monkeypatch.setattr(M, "deployed_override", lambda *a, **k: None)
    from ff9mapkit.world import entrance as EN
    monkeypatch.setattr(EN, "read_block_stacked", lambda mod, bx, by, **k: SimpleNamespace(block=(bx, by)))
    seen = {}
    monkeypatch.setattr(DM, "auto_mirror", lambda written, **k: seen.update(k))
    T.reshape("MOD", at=(1030.0, -910.0), radius=8.0, amount=2.0, target_disc=9)
    assert seen["replay"] is None


def test_world_deploy_replays_itself_on_disc4(monkeypatch):
    seen = {}
    monkeypatch.setattr(DM, "auto_mirror", lambda written, **k: seen.update(k))
    calls = []
    real = cli._cmd_world_deploy
    ns = argparse.Namespace(block=None, cluster=None, disc=1, lod="0_1", mod_folder="MOD", hill=2.0, crater=0.0,
                            flatten=False, height=None, radius=8.0, center=[1030.0, -910.0], falloff="smooth",
                            no_normals=True, allow_entrances=False, spike=0.0, lift=0.0, skip_mirror=False,
                            game=None, fresh=False, allow_overwrite=False)
    from types import SimpleNamespace
    from ff9mapkit.world import entrance as EN, mesh as M
    monkeypatch.setattr(X, "list_blocks", lambda **k: [(16, 14)])
    monkeypatch.setattr(EN, "read_block_stacked", lambda mod, x, y, **k: SimpleNamespace(
        x=x, y=y, name=f"Block[{x}][{y}] Terrain", verts=[], tris=[], tangents=None))
    monkeypatch.setattr(M, "deform_radial", lambda bm, **k: 3)
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: Path("x"))
    monkeypatch.setattr(T, "stitch_partners", lambda *a, **k: [])
    assert real(ns) == 0
    monkeypatch.setattr(cli, "_cmd_world_deploy", lambda a: calls.append(a) or 0)
    seen["replay"](4)
    assert calls[0].disc == 4 and calls[0].skip_mirror == DM.REPLAY and calls[0].center == [1030.0, -910.0]
    monkeypatch.setattr(cli, "_cmd_world_deploy", lambda a: 2)
    with pytest.raises(ValueError, match="world-deploy --disc 4 refused the same reshape"):
        seen["replay"](4)


def test_the_replayed_call_skips_its_own_mirror_silently():
    # the writer call a replay re-runs on disc 4 IS the mirror: it used to print "skipped (--skip-mirror)" mid-replay
    lines = []
    assert DM.auto_mirror(["x"], mod_folder="MOD", skip_mirror=DM.REPLAY, log=lines.append) is None
    assert lines == []
    assert DM.auto_mirror(["x"], mod_folder="MOD", skip_mirror=True, log=lines.append) is None
    assert lines == ["disc-4 mirror: skipped (--skip-mirror)"]
