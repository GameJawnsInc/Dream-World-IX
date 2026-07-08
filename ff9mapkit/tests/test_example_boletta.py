"""The boletta example (a from-scratch creature) stays coherent -- struct-valid, emit-clean, and
wired consistently between its generator scripts and its field.toml. No install needed: the
winding calibration is bypassed with its known fallback (+1)."""
import sys
import tomllib
from pathlib import Path

EXAMPLE = Path(__file__).parents[1] / "examples" / "boletta"
sys.path.insert(0, str(EXAMPLE))

import make_creature  # noqa: E402
import make_creature_anims  # noqa: E402


def test_build_model_struct_is_sane():
    model = make_creature.build_model(wind=1)
    mesh = model["meshes"][0]
    nv = len(mesh["verts"])
    assert nv > 100 and len(mesh["submeshes"][0]["tris"]) > 200
    assert len(mesh["normals"]) == nv == len(mesh["uvs"]) == len(mesh["weights"])
    nbones = len(model["bones"])
    for infl in mesh["weights"]:
        assert 1 <= len(infl) <= 4
        assert all(0 <= b < nbones for b, _ in infl)
        assert abs(sum(w for _, w in infl) - 1.0) < 1e-6
    assert all(0.0 <= u <= 1.0 and 0.0 <= v <= 1.0 for u, v in mesh["uvs"])
    # Y-down space: everything at/above the ground plane, head into negative y
    ys = [v[1] for v in mesh["verts"]]
    assert max(ys) <= 0.0 and min(ys) < -250.0
    assert str(model["geo_id"]) in model["textures"]


def test_emit_skinned_fbx_accepts_the_creature():
    from ff9mapkit.models import fbx_skin
    model = make_creature.build_model(wind=1)
    text, meta = fbx_skin.emit_skinned_fbx(model)       # self-validates against the engine tokenizer
    assert meta["euler_max_err"] < 1e-9                 # rest rig is identity rotations
    for b in model["bones"]:
        assert f'"Model::{b["name"]}"' in text
    assert '"Model::Armature"' in text                  # the root-bone NRE guard node


def test_idle_clip_keys_the_full_skeleton_and_loops():
    clip = make_creature_anims.build_idle_clip()
    assert len(clip["bones"]) == len(make_creature.BONES)          # statics fill the unkeyed bones
    assert clip["length"] == 2.0
    for entry in clip["bones"].values():
        assert set(entry) >= {"rot", "pos", "scale"}
        for chan in ("rot", "pos", "scale"):
            first, last = entry[chan][0][1], entry[chan][-1][1]
            assert all(abs(a - b) < 1e-9 for a, b in zip(first, last))   # clean loop


def test_field_toml_wires_the_same_ids_as_the_scripts():
    doc = tomllib.loads((EXAMPLE / "boletta.field.toml").read_text(encoding="utf-8"))
    (mint,) = doc["mint"]
    assert mint["id"] == make_creature.GEO_ID and mint["name"] == make_creature.GEO_NAME
    assert mint["fbx"] == f"creature/{make_creature.GEO_ID}.fbx"
    (npc,) = doc["npc"]
    assert npc["model"] == make_creature.GEO_ID
    assert npc["speaker"] and npc["dialogue"]
    assert 60_000 <= npc["anims"]["stand"] <= 65_535               # a 16-bit field-band key
    assert (EXAMPLE / "art" / "back.png").is_file() and (EXAMPLE / "art" / "floor.png").is_file()
