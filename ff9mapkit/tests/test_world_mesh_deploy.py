"""world-mesh-build stock-object guard: a full Object override REPLACES the block's stock mesh (trees/bridge/town)
unless --keep-block merges. build_from_obj must report `replaced_stock_tris` so the CLI can warn.

Also pins the RAW `--idall` lever: `--topograph` can only reach bits 2-7, so the engine's render-only marker id
4078 (0x0FEE = area 15, topo 59, flags 2 -- skipped by WMPhysics.Raycast) is UNREACHABLE without it."""
from __future__ import annotations

from types import SimpleNamespace

from ff9mapkit.world import blendio as BIO
from ff9mapkit.world.extract import CH_TAN, decode_id, encode_id


def _tri_obj(tmp_path):
    p = tmp_path / "tri.obj"                                  # a triangle in block(16,14) world coords (origin 1024,-896)
    p.write_text("v 1024 3 -896\nv 1030 3 -896\nv 1030 3 -890\nf 1 2 3\n")
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
