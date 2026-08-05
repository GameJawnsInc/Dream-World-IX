"""world-mesh-build stock-object guard: a full Object override REPLACES the block's stock mesh (trees/bridge/town)
unless --keep-block merges. build_from_obj must report `replaced_stock_tris` so the CLI can warn.

Also pins the RAW `--idall` lever: `--topograph` can only reach bits 2-7, so the engine's render-only marker id
4078 (0x0FEE = area 15, topo 59, flags 2 -- skipped by WMPhysics.Raycast) is UNREACHABLE without it."""
from __future__ import annotations

from types import SimpleNamespace

from ff9mapkit.world import blendio as BIO
from ff9mapkit.world.extract import CH_TAN, decode_id, encode_id


def _tri_obj(tmp_path):
    # a triangle INSIDE block (16,14)'s frame -- world x 1024..1030 (local 0..6), world z -940..-934
    # (local -44..-38; the block spans world z [-960,-896]). The old fixture sat at z -896..-890,
    # NORTH of the block -- tolerated before the rec-15 frame gate, refused (correctly) now.
    p = tmp_path / "tri.obj"
    p.write_text("v 1024 3 -940\nv 1030 3 -940\nv 1030 3 -934\nf 1 2 3\n")
    return str(p)


def test_replace_reports_stock_tris(tmp_path, monkeypatch):
    monkeypatch.setattr(BIO.W, "read_block", lambda *a, **k: SimpleNamespace(tris=[[0, 1, 2]] * 7))   # 7-tri stock
    monkeypatch.setattr(BIO.M, "deploy_override", lambda bm, **k: tmp_path / "out.ff9mesh")
    info = BIO.build_from_obj(_tri_obj(tmp_path), into_block=(16, 14), mod_folder="X", part="object", keep_block=False)
    assert info["replaced_stock_tris"] == 7 and info["kept_stock"] is False   # would silently wipe 7 stock tris


def test_keep_block_merges_and_does_not_warn(tmp_path, monkeypatch):
    monkeypatch.setattr(BIO.W, "read_block", lambda *a, **k: SimpleNamespace(tris=[[0, 1, 2]] * 7))
    monkeypatch.setattr(BIO.M, "place_building", lambda dst, src, **k: src)   # merge (channel-agnostic stub)
    monkeypatch.setattr(BIO.M, "deploy_override", lambda bm, **k: tmp_path / "out.ff9mesh")
    info = BIO.build_from_obj(_tri_obj(tmp_path), into_block=(16, 14), mod_folder="X", part="object", keep_block=True)
    assert info["kept_stock"] is True and info["replaced_stock_tris"] == 0


def test_bare_block_no_warning(tmp_path, monkeypatch):
    def no_stock(*a, **k):
        raise ValueError("no stock object mesh")             # a bare block -> nothing to replace
    monkeypatch.setattr(BIO.W, "read_block", no_stock)
    monkeypatch.setattr(BIO.M, "deploy_override", lambda bm, **k: tmp_path / "out.ff9mesh")
    info = BIO.build_from_obj(_tri_obj(tmp_path), into_block=(16, 14), mod_folder="X", part="object", keep_block=False)
    assert info["replaced_stock_tris"] == 0


# --- the RAW --idall lever (render-only markers) -----------------------------------------------------------------

def test_topograph_alone_cannot_express_the_render_only_id():
    """THE GAP the lever closes: 4078 needs area 15 + flags 2, and the topograph encode zeroes both."""
    assert decode_id(4078) == {"event": 0, "area": 15, "topograph": 59, "flags": 2}
    assert encode_id(topograph=59) == 236 != 4078
    assert all(encode_id(topograph=t) != 4078 for t in range(64))


def test_idall_stamps_raw_value_on_every_triangle():
    obj = {"V": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0), (0.0, 6.0, 0.0)],
           "VT": [(0.2, 0.3)], "VN": [(0.0, 1.0, 0.0)],
           "faces": [((1, 1, 1), (2, 1, 1), (3, 1, 1)), ((1, 1, 1), (2, 1, 1), (4, 1, 1))]}
    bm = BIO.obj_to_blockmesh(obj, into_block=(0, 18), idall=4078)
    tans = bm.chan_arrays[CH_TAN]
    assert len(tans) == 6 and {t[0] for t in tans} == {4078.0}          # every corner of every tri
    assert {int(round(tans[bm.flat_index[3 * i]][0])) for i in range(len(bm.tris))} == {4078}
    assert [tuple(u) for u in bm.uvs] == [(0.2, 0.3)] * 6               # UVs still carried (a UV-less carry = white)


def test_idall_none_keeps_the_topograph_encode_and_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(BIO.W, "read_block", lambda *a, **k: SimpleNamespace(tris=[]))
    monkeypatch.setattr(BIO.M, "deploy_override", lambda bm, **k: tmp_path / "out.ff9mesh")
    plain = BIO.build_from_obj(_tri_obj(tmp_path), into_block=(16, 14), mod_folder="X", part="object")
    marker = BIO.build_from_obj(_tri_obj(tmp_path), into_block=(16, 14), mod_folder="X", part="object", idall=4078)
    assert plain["idall"] == encode_id(topograph=59) == 236             # unchanged default behaviour
    assert marker["idall"] == 4078


def test_idall_is_masked_to_16_bits():
    obj = {"V": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0)], "VT": [], "VN": [],
           "faces": [((1, 0, 0), (2, 0, 0), (3, 0, 0))]}
    bm = BIO.obj_to_blockmesh(obj, into_block=(0, 18), idall=0x1_0FEE)
    assert {t[0] for t in bm.chan_arrays[CH_TAN]} == {4078.0}


def test_idall_survives_the_keep_block_merge(tmp_path, monkeypatch):
    """`world-entrance --building` defaults to keep_block=True (merge, don't replace the town). The
    render-only stamp must survive that merge, or a building placed beside a stock town silently
    becomes collision again -- `place_building` is called with no `set_idall`, so the appended mesh has
    to carry 4078 in its OWN tangents."""
    stock = BIO.obj_to_blockmesh(                                  # a fake 1-tri "stock town", topo 59
        # in-frame world coords (the old -896..-894 fixture sat NORTH of block (16,14) -- the
        # rec-15 frame gate now correctly refuses that, so the fixture moved inside)
        {"V": [(1024.0, 0.0, -940.0), (1026.0, 0.0, -940.0), (1026.0, 0.0, -938.0)], "VT": [], "VN": [],
         "faces": [((1, 0, 0), (2, 0, 0), (3, 0, 0))]}, into_block=(16, 14))
    captured = {}
    monkeypatch.setattr(BIO.W, "read_block", lambda *a, **k: stock)
    monkeypatch.setattr(BIO.M, "deploy_override", lambda bm, **k: captured.setdefault("bm", bm)
                        or (tmp_path / "out.ff9mesh"))
    BIO.build_from_obj(_tri_obj(tmp_path), into_block=(16, 14), mod_folder="X", part="object",
                       keep_block=True, idall=4078)
    tans = [t[0] for t in captured["bm"].chan_arrays[CH_TAN]]
    assert len(tans) == 6                                          # 3 stock corners + 3 ours
    assert set(tans[3:]) == {4078.0}                               # OUR tris are render-only
    assert set(tans[:3]) == {float(encode_id(topograph=59))}        # the stock town keeps its collision


# --- the rec-15 split: FAIL-CLOSED write path -------------------------------------------------------------------

def test_terrain_rebuild_is_refused_without_the_explicit_kwarg(tmp_path, monkeypatch):
    """THE CLOSED LANE: the OBJ round-trip destroys per-triangle IDALL, so a terrain rebuild
    would stamp one uniform walk/event id across the block -- refused, naming the real paths."""
    import pytest
    monkeypatch.setattr(BIO.M, "deploy_override", lambda bm, **k: tmp_path / "out.ff9mesh")
    with pytest.raises(ValueError) as e:
        BIO.build_from_obj(_tri_obj(tmp_path), into_block=(16, 14), mod_folder="X", part="terrain")
    msg = str(e.value)
    assert "IDALL" in msg and "world-terrain" in msg and "world-transplant" in msg
    monkeypatch.setattr(BIO.W, "read_block", lambda *a, **k: SimpleNamespace(tris=[]))
    info = BIO.build_from_obj(_tri_obj(tmp_path), into_block=(16, 14), mod_folder="X",
                              part="terrain", allow_uniform_terrain_idall=True)
    assert info["tris"] == 1                                  # the explicit bench-prop escape still works


def test_out_of_frame_geometry_is_refused_with_the_bbox(tmp_path, monkeypatch):
    """THE BLOCK-FRAME GATE: a vert dragged past the block's east frame plane (x=64 local) is
    culled/garbage in-game -- refused before the deploy, bbox and legal frame in the message."""
    import pytest
    monkeypatch.setattr(BIO.W, "read_block", lambda *a, **k: SimpleNamespace(tris=[]))
    deployed = []
    monkeypatch.setattr(BIO.M, "deploy_override", lambda bm, **k: deployed.append(1) or tmp_path / "o.ff9mesh")
    p = tmp_path / "far.obj"                                  # x 1024..1090 -> local 0..66 (past 64)
    p.write_text("v 1024 3 -940\nv 1090 3 -940\nv 1090 3 -934\nf 1 2 3\n")
    with pytest.raises(ValueError) as e:
        BIO.build_from_obj(str(p), into_block=(16, 14), mod_folder="X", part="object")
    msg = str(e.value)
    assert "66.000" in msg and "x[0,64]" in msg and "(16,14)" in msg
    assert not deployed                                       # refused BEFORE the write seam


def test_degenerate_triangles_are_counted_not_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(BIO.W, "read_block", lambda *a, **k: SimpleNamespace(tris=[]))
    monkeypatch.setattr(BIO.M, "deploy_override", lambda bm, **k: tmp_path / "o.ff9mesh")
    p = tmp_path / "deg.obj"                                  # tri 2 is a zero-area sliver (collinear)
    p.write_text("v 1024 3 -940\nv 1030 3 -940\nv 1030 3 -934\n"
                 "v 1025 3 -939\nv 1026 3 -939\nv 1027 3 -939\nf 1 2 3\nf 4 5 6\n")
    info = BIO.build_from_obj(str(p), into_block=(16, 14), mod_folder="X", part="object")
    assert info["degenerate_tris"] == 1 and info["tris"] == 2  # warned in the summary, never a refusal


# --- the rec-15 split: PERMISSIVE read path (deployed inspection) -----------------------------------------------

def _fake_bm(n=1, y=0.0):
    """A minimal export-shaped block mesh: n up-facing tris at height y, no uvs/normals."""
    verts, tris = [], []
    for i in range(n):
        b = len(verts)
        verts += [(4.0 * i, y, -4.0), (4.0 * i + 3.0, y, -4.0), (4.0 * i, y, -1.0)]
        tris.append((b, b + 1, b + 2))
    return SimpleNamespace(verts=verts, normals=None, uvs=None, tris=tris, vcount=len(verts))


def test_export_single_part_stays_byte_identical_no_materials(tmp_path, monkeypatch):
    monkeypatch.setattr(BIO.W, "read_block", lambda *a, **k: _fake_bm())
    out = tmp_path / "o.obj"
    info = BIO.export_obj([(16, 14)], part="object", out=out)
    text = out.read_text()
    assert "mtllib" not in text and "usemtl" not in text      # the classic lane: no material lines
    assert info["written"] == [str(out)] and info["parts"] == ["object"]
    assert not (tmp_path / "o.mtl").exists()


def test_export_all_parts_skips_missing_and_writes_the_ring_materials(tmp_path, monkeypatch):
    """--part all: carried parts only (a missing part is skipped, permissive), one usemtl per
    group, and the .mtl colour-codes the beach/sea ring; a failed atlas extract degrades to
    untextured instead of refusing (the read path never fails closed)."""
    have = {"terrain": _fake_bm(2), "sea4": _fake_bm(1, y=-1.0)}

    def fake_read(x, y, *, part, **k):
        if part in have:
            return have[part]
        raise ValueError(f"no {part} mesh")

    monkeypatch.setattr(BIO.W, "read_block", fake_read)
    from ff9mapkit.world import atlas as A

    def no_atlas(*a, **k):
        raise FileNotFoundError("no install in this test")
    monkeypatch.setattr(A, "extract_atlas", no_atlas)
    out = tmp_path / "all.obj"
    info = BIO.export_obj([(16, 14)], part="all", out=out)
    text = out.read_text()
    assert "usemtl terrain" in text and "usemtl sea4" in text and "usemtl sea1" not in text
    assert info["parts"] == ["terrain", "sea4"]
    mtl = (tmp_path / "all.mtl").read_text()
    assert "newmtl sea4" in mtl and "Kd 0.080 0.200 0.500" in mtl   # the deep-water rung colour
    assert "newmtl terrain" in mtl and "map_Kd" not in mtl          # atlas failed -> flat, not fatal


def test_export_mod_folder_routes_through_the_deployed_stack(tmp_path, monkeypatch):
    """--mod-folder: every read goes through entrance.read_block_stacked (override-first), so
    the export shows what the engine will LOAD -- the kit's own output included."""
    from ff9mapkit.world import entrance as EN
    calls = []

    def fake_stacked(mod_folder, x, y, *, part, missing_ok=False, **k):
        calls.append((mod_folder, x, y, part, missing_ok))
        return _fake_bm()
    monkeypatch.setattr(EN, "read_block_stacked", fake_stacked)
    out = tmp_path / "d.obj"
    info = BIO.export_obj([(16, 14)], part="terrain", out=out, mod_folder="FF9CustomMap-world")
    assert calls == [("FF9CustomMap-world", 16, 14, "terrain", False)]
    assert "deployed stack" in info["source"]
    assert "usemtl terrain" in out.read_text()                # inspection mode defaults materials ON
