"""world-mesh-build stock-object guard: a full Object override REPLACES the block's stock mesh (trees/bridge/town)
unless --keep-block merges. build_from_obj must report `replaced_stock_tris` so the CLI can warn."""
from __future__ import annotations

from types import SimpleNamespace

from ff9mapkit.world import blendio as BIO


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
