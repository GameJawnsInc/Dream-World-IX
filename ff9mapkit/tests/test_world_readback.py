"""world-readback: the s22 dump reader (audit rec 10 step 3 -- the instrument with zero
consumers, given its first). Hermetic: synthetic dump dirs + a tmp deployed tree.

The dump's floats are C# ToString("R") -- they round-trip float32 -- so equality is tested
at float32 width; a float64 == would flake on R-string decimals.
"""
from __future__ import annotations

import pytest

from ff9mapkit.world import mesh as M, readback as RB
from ff9mapkit.world.extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN

GRASS = float(encode_id(topograph=0))


def _bm(y=3.25, idall=None, x=5, by=7):
    idall = GRASS if idall is None else idall
    corners = [(0.0, y, 0.0), (7.3125, y, 0.0), (0.0, y, -7.53125)]   # non-round floats
    pos, nrm, uv, tan, flat = [], [], [], [], []
    for c in corners:
        pos.append(list(c)); nrm.append([0.0, 1.0, 0.0]); uv.append([0.25, 0.5])
        tan.append([idall, 0.0, 0.0, 1.0]); flat.append(len(pos) - 1)
    return BlockMesh(name=f"Block[{x}][{by}] Terrain", disc=1, x=x, y=by, lod="0_1",
                     vcount=3, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=[[0, 1, 2]], raw_vbuf=b"", raw_ibuf=b"",
                     use32=True, submeshes=[])


def _r(x):
    """C# ToString('R')-alike: the shortest string that round-trips the float32."""
    import struct as st
    f32 = st.unpack("<f", st.pack("<f", x))[0]
    return repr(f32)


def _dump_dir(tmp, bm, *, mutate_vert=None, idall=None, name="Terrain"):
    d = tmp / "ff9mk_dumps" / "block_5_7"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.txt").write_text(
        "block 5,7  Number=173  Form=1  IsReady=True  IsSea=False  HasBeach1=False  "
        "HasBeach2=False  HasSea=True  activeSelf=True\n"
        "transform.position=(320.0, 0.0, -448.0)  Current=5,7  Initial=5,7\n"
        "\n"
        f"child[0] '{name}'  activeInHierarchy=True  rendererEnabled=True  "
        "localPos=(0.0, 0.0, 0.0)  worldPos=(320.0, 0.0, -448.0)\n"
        "  material=WorldMapTerrain  shader=WorldMap/Terrain  tex=worldmap_atlas\n",
        encoding="utf-8")
    verts = [list(v) for v in bm.chan_arrays[CH_POS]]
    if mutate_vert is not None:
        verts[mutate_vert][1] += 0.5
    tanid = bm.chan_arrays[CH_TAN][0][0] if idall is None else idall
    lines = [f"# ff9mk block dump: {name}", f"o {name}"]
    lines += [f"v {_r(v[0])} {_r(v[1])} {_r(v[2])}" for v in verts]
    lines += ["f 1/1 2/2 3/3"]
    lines += [f"# tan {i} {_r(tanid)} 0 0 1" for i in range(3)]
    (d / f"00_{name}.obj").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (d / "walk_form1_00.obj").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return d


def test_readback_matches_a_faithful_deploy(tmp_path):
    bm = _bm()
    M.deploy_override(bm, mod_folder="TestMod", game=tmp_path)
    d = _dump_dir(tmp_path, bm)
    rep = RB.readback(d, mod_folder="TestMod", disc=1, game=tmp_path)
    (c,) = rep["children"]
    assert c["deployed"] and c["match"] and c["idall_match"]
    (w,) = rep["walk"]
    assert w["matches_child"] == "Terrain" and w["idall"] == [int(GRASS)]
    assert rep["materials"][0]["shader"] == "WorldMap/Terrain"


def test_readback_flags_a_divergent_engine_mesh(tmp_path):
    """The point of the instrument: the engine built something OTHER than our bytes --
    report the first differing vert, never claim a match."""
    bm = _bm()
    M.deploy_override(bm, mod_folder="TestMod", game=tmp_path)
    d = _dump_dir(tmp_path, bm, mutate_vert=1)
    rep = RB.readback(d, mod_folder="TestMod", disc=1, game=tmp_path)
    (c,) = rep["children"]
    assert not c["match"] and c["first_mismatch"]["index"] == 1


def test_readback_flags_an_idall_swap_and_stock_children(tmp_path):
    """Same geometry, different walk identity (the wrong-donor divert class) -- geometry
    MATCHES but IDALL differs; and a child with no deployed override reports stock."""
    bm = _bm()
    M.deploy_override(bm, mod_folder="TestMod", game=tmp_path)
    d = _dump_dir(tmp_path, bm, idall=float(encode_id(topograph=57)))
    rep = RB.readback(d, mod_folder="TestMod", disc=1, game=tmp_path)
    (c,) = rep["children"]
    assert c["match"] and not c["idall_match"]
    d2 = _dump_dir(tmp_path, bm, name="Sea4")
    rep2 = RB.readback(d2, mod_folder="TestMod", disc=1, game=tmp_path)
    sea = next(x for x in rep2["children"] if x["child"] == "Sea4")
    assert not sea["deployed"] and "stock" in sea["note"]


def test_readback_refuses_a_non_dump_dir(tmp_path):
    with pytest.raises(ValueError, match="not a block"):
        RB.readback(tmp_path / "somewhere", mod_folder="TestMod", disc=1, game=tmp_path)
    bad = tmp_path / "block_3_3"; bad.mkdir()
    with pytest.raises(ValueError, match="manifest"):
        RB.readback(bad, mod_folder="TestMod", disc=1, game=tmp_path)
