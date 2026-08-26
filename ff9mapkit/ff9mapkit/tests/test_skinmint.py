"""Offline tests for palette-swap enemy minting ([[scene.enemy]] skin) -- no install needed.

The load-bearing pieces pinned pure: skin_spec's fail-loud validation (a malformed skin must never
silently ship), the Geo@30 poke (i16, per-type offset), and recolor_image's guarantees (alpha
untouched -- FF9 cutout masks; hue rotation + tint compose). The install-side mint emit reuses the
proven models mint/emit path and is exercised by the real battle-build (deploy-time).
"""
import struct

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image

from ff9mapkit.battle import scene_data, skinmint
from ff9mapkit.models import reskin as mreskin


def _raw16(patcount=1, typcount=2, geo=(152, 151)):
    """A minimal synthetic raw16: header counts + pattern blocks + per-type 116-byte monster blocks."""
    b = bytearray(8)
    b[1], b[2], b[3] = patcount, typcount, 0
    b += bytes(56 * patcount)
    for t in range(typcount):
        blk = bytearray(116)
        struct.pack_into("<h", blk, 30, geo[t])
        b += blk
    return bytes(b)


def test_geo_read_write_roundtrip():
    raw = _raw16()
    assert skinmint._read_geo(raw, 0) == 152 and skinmint._read_geo(raw, 1) == 151
    raw2 = skinmint._write_geo(raw, 0, 6200)
    assert skinmint._read_geo(raw2, 0) == 6200
    assert skinmint._read_geo(raw2, 1) == 151          # the other block untouched
    assert raw2[:8] == raw[:8]
    with pytest.raises(skinmint.SkinError, match="out of range"):
        skinmint._read_geo(raw, 5)


def test_skin_spec_validation():
    ok = skinmint.skin_spec({"type": 0, "skin": {"id": 6200, "hue": 150}})
    assert ok == {"id": 6200, "type": 0, "hue": 150, "tint": None, "textures": {},
                  "from": None, "name": None}
    assert skinmint.skin_spec({"type": 0}) is None                       # no skin -> None
    with pytest.raises(skinmint.SkinError, match="mint band"):
        skinmint.skin_spec({"type": 0, "skin": {"id": 152, "hue": 1}})   # a real id would OVERWRITE
    with pytest.raises(skinmint.SkinError, match="mint band"):
        skinmint.skin_spec({"type": 0, "skin": {"id": 40000, "hue": 1}})  # over the i16 ceiling
    with pytest.raises(skinmint.SkinError, match="type = N"):
        skinmint.skin_spec({"skin": {"id": 6200, "hue": 1}})
    with pytest.raises(skinmint.SkinError, match="does nothing"):
        skinmint.skin_spec({"type": 0, "skin": {"id": 6200}})
    with pytest.raises(skinmint.SkinError, match="tint"):
        skinmint.skin_spec({"type": 0, "skin": {"id": 6200, "tint": [1.0, 2.0]}})
    with pytest.raises(skinmint.SkinError, match="textures"):
        skinmint.skin_spec({"type": 0, "skin": {"id": 6200, "textures": ["a.png"]}})


def test_skin_spec_full_form():
    s = skinmint.skin_spec({"type": 1, "skin": {"id": 7000, "tint": [1.4, 0.7, 0.7],
                                                "textures": {"152_0": "my.png"},
                                                "from": "GEO_MON_B3_001", "name": "GEO_MON_B3_XYZ"}})
    assert s["from"] == "GEO_MON_B3_001" and s["name"] == "GEO_MON_B3_XYZ"
    assert s["textures"] == {"152_0": "my.png"} and s["type"] == 1


def test_recolor_hue_rotates_and_preserves_alpha():
    img = Image.new("RGBA", (2, 1))
    img.putpixel((0, 0), (255, 0, 0, 255))      # pure red
    img.putpixel((1, 0), (10, 20, 30, 0))       # a transparent texel -- the cutout mask
    out = mreskin.recolor_image(img, hue=120)   # red -> green third of the wheel
    r, g, b, a = out.getpixel((0, 0))
    assert g > 200 and r < 60, f"hue 120 should turn red green: {(r, g, b)}"
    assert out.getpixel((1, 0))[3] == 0, "alpha must be preserved exactly"
    assert img.getpixel((0, 0)) == (255, 0, 0, 255), "the input image must not be mutated"


def test_recolor_tint_multiplies_and_clamps():
    img = Image.new("RGBA", (1, 1), (100, 100, 200, 255))
    out = mreskin.recolor_image(img, tint=[2.0, 0.5, 1.0])
    r, g, b, a = out.getpixel((0, 0))
    assert (r, g, b, a) == (200, 50, 200, 255)
    out2 = mreskin.recolor_image(img, tint=[3.0, 1.0, 1.0])
    assert out2.getpixel((0, 0))[0] == 255      # clamped, not wrapped


def test_apply_skins_noop_without_skins():
    raw = _raw16()
    out, dlines, written, warns = skinmint.apply_skins(raw, {"enemy": [{"type": 0, "hp": 300}]}, None)
    assert out is raw and not dlines and not written and not warns


def _fake_model():
    return {"geo": "GEO_MON_B3_001", "geo_id": 152, "type_int": 3, "root_bone": "bone000",
            "bones": [{"name": "bone000", "parent": None, "pos": [0, 0, 0],
                       "rot": [0, 0, 0, 1], "scale": [1, 1, 1]}],
            "meshes": [{"name": "mesh0", "verts": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                        "normals": [[0, 1, 0]] * 3, "uvs": [[0, 0]] * 3,
                        "submeshes": [{"material_idx": 0, "tris": [[0, 1, 2]]}],
                        "weights": [[(0, 1.0)]] * 3, "parent": None}],
            "materials": [{"name": "m0", "texture": "152_0"}],
            "textures": {"152_0": Image.new("RGBA", (4, 4), (255, 0, 0, 255))},
            "bind_correction": None, "per_mesh_bind": [None]}


class _Layout:
    def __init__(self, root):
        self.root = root

    def model_dir(self, t, i):
        return self.root / "Models" / str(t) / str(i)


def test_apply_skins_rejects_duplicate_ids(tmp_path, monkeypatch):
    from ff9mapkit.models import extract as mextract
    monkeypatch.setattr(mextract, "read_model", lambda tok, game=None: _fake_model())
    raw = _raw16()
    cfg = {"enemy": [{"type": 0, "skin": {"id": 6200, "hue": 1}},
                     {"type": 1, "skin": {"id": 6200, "hue": 2}}]}
    with pytest.raises(skinmint.SkinError, match="used twice"):
        skinmint.apply_skins(raw, cfg, _Layout(tmp_path))


def test_apply_skins_end_to_end_with_a_fake_model(tmp_path, monkeypatch):
    """The whole offline path: mint dir + recolored PNG + FBX + directive + the Geo@30 poke."""
    from ff9mapkit.models import extract as mextract
    monkeypatch.setattr(mextract, "read_model", lambda tok, game=None: _fake_model())

    raw = _raw16()
    cfg = {"enemy": [{"type": 0, "skin": {"id": 6200, "hue": 120}}]}
    out, dlines, written, warns = skinmint.apply_skins(raw, cfg, _Layout(tmp_path))
    assert skinmint._read_geo(out, 0) == 6200 and skinmint._read_geo(out, 1) == 151
    assert len(dlines) == 1 and dlines[0].startswith("3DModel 6200 GEO_MON_B3_")
    fbx = tmp_path / "Models" / "3" / "6200" / "6200.fbx"
    png = tmp_path / "Models" / "3" / "6200" / "152_0.png"
    assert fbx.is_file() and png.is_file()
    px = Image.open(png).convert("RGBA").getpixel((0, 0))
    assert px[1] > 200 and px[0] < 60, f"the minted texture must be recolored: {px}"
    assert any("palette-swapped" in w and "RELAUNCH" in w for w in warns)
