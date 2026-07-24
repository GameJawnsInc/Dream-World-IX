"""``summons.deploy.stage_import`` -- the summon-import Blender-return packager (M2, DESIGN section 3).

  * PURE-LOGIC (always runs) -- the import validation list: the bone000..N rig contiguity/hierarchy
    checks (smooth weights allowed for a USER mesh), the ready-FBX texture-name check, the clip
    bone-number -> hierarchy-path re-key, and the bad-extension refusal.
  * GAME-GATED -- the full glb round-trip: a locally-extracted skinned summon .glb through stage_import
    into a tmp mod mirror (validate -> glb->FBX -> mint -> host .seq). Skips when the install / the local
    ``C:/gd/SCRATCH/summon-transplant/ef227_bahamut.glb`` is absent.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import config
from ff9mapkit.summons import deploy as D

_BAHAMUT_GLB = Path(r"C:/gd/SCRATCH/summon-transplant/ef227_bahamut.glb")


def _game():
    try:
        return config.find_game_path()
    except config.ConfigError:
        return None


def _rig(n: int) -> dict:
    """A synthetic model struct with a valid bone000..bone{n-1} chain (each parented to the prior)."""
    bones = [{"name": "bone000", "parent": None}]
    bones += [{"name": f"bone{k:03d}", "parent": f"bone{k - 1:03d}"} for k in range(1, n)]
    return {"bones": bones}


# =========================================================================== PURE LOGIC (always runs)

def test_valid_rig_passes():
    assert D.validate_import_rig(_rig(93)) == []


def test_rig_needs_bones():
    assert D.validate_import_rig({"bones": []})


def test_rig_rejects_non_bone_name():
    m = _rig(3)
    m["bones"][1]["name"] = "spine_01"
    probs = D.validate_import_rig(m)
    assert probs and "boneNNN" in probs[0]


def test_rig_rejects_gap():
    m = _rig(3)
    m["bones"][2]["name"] = "bone005"          # gap: 0,1,5
    m["bones"][2]["parent"] = "bone001"
    probs = D.validate_import_rig(m)
    assert any("contiguous" in p for p in probs)


def test_rig_rejects_multi_root():
    m = _rig(3)
    m["bones"][2]["parent"] = None             # a second root
    probs = D.validate_import_rig(m)
    assert any("exactly one root" in p for p in probs)


def test_rig_rejects_missing_parent():
    m = _rig(3)
    m["bones"][2]["parent"] = "bone099"        # dangling parent (still one root, contiguous names)
    probs = D.validate_import_rig(m)
    assert any("missing parent" in p for p in probs)


def test_smooth_weights_are_allowed():
    """A user mesh may carry smooth/multi-bone weights -- validate_import_rig checks only the SKELETON,
    never the per-vertex weights (rigidity is a property of the donor, not a constraint on the user's
    mesh). REGRESSION guard against a vacuous version of this test: a prior revision carried NO weight
    data at all, so it would have passed identically even if smooth skinning were secretly rejected
    somewhere in the path. This fixture carries REAL multi-bone weights (the models/gltf.py mesh shape --
    one ``[(bone_num, weight), ...]`` influence list per vertex) with 2+ bones summing to 1.0, and the
    validator must still pass the rig clean."""
    m = _rig(4)
    m["meshes"] = [{
        "name": "part0",
        "weights": [
            [(0, 0.5), (1, 0.5)],
            [(1, 0.7), (2, 0.3)],
            [(2, 0.25), (3, 0.75)],
        ],
    }]
    for infl in m["meshes"][0]["weights"]:
        assert len(infl) >= 2, "fixture must be genuinely multi-bone, not a disguised rigid bind"
        assert abs(sum(w for _, w in infl) - 1.0) < 1e-9, "fixture weights must actually sum to 1"
    assert D.validate_import_rig(m) == []


def test_texture_name_check_for_fbx():
    assert D.validate_import_textures_fbx(b"...Thomas_d.png...") == []
    assert D.validate_import_textures_fbx(b"...body.tga...") == []
    probs = D.validate_import_textures_fbx(b"no texture reference here")
    assert probs and "references no texture" in probs[0]


def test_clip_bone_number_to_hierarchy_path():
    """DESIGN 3.3 detail 1: clip['bones'] keyed by bone NUMBER is re-keyed to the nested hierarchy PATH."""
    parent_of = {"bone000": None, "bone001": "bone000", "bone002": "bone001"}
    clip = {"name": "clip0", "sample_rate": 15.0, "length": 1.0,
            "bones": {"bone000": {"rot": [(0.0, (0, 0, 0, 1))]},
                      "bone002": {"rot": [(0.0, (0, 0, 0, 1))]}}}
    out = D._clip_bone_paths(clip, parent_of)
    assert set(out["bones"]) == {"bone000", "bone000/bone001/bone002"}
    assert out["name"] == "clip0" and out["sample_rate"] == 15.0


def test_clip_bone_paths_root_self_cycle_does_not_hang():
    """REGRESSION: the real donor rig reports the root's own parent as ITSELF (container.Geom.parents()
    returns parents[0]==0, a self-reference -- NOT -1). A parent_of that maps the root to itself must NOT
    send _clip_bone_paths into an infinite loop (the cycle guard in path_of); it terminates and yields a
    sane path. (This is the exact shape that hung the overlay lane before the k==0 root fix.)"""
    parent_of = {"bone000": "bone000",            # <-- self-cycle, as a naive parents[k]<0 build produced
                 "bone001": "bone000", "bone002": "bone001"}
    clip = {"name": "clip0", "sample_rate": 15.0, "length": 1.0,
            "bones": {"bone000": {"rot": []}, "bone002": {"rot": []}}}
    out = D._clip_bone_paths(clip, parent_of)          # must return, not spin forever
    # the guard stops when a parent repeats -- no runaway 'bone000/bone000/bone000/...' key
    assert all(k.count("bone000") <= 1 for k in out["bones"])
    assert "bone000/bone001/bone002" in out["bones"]


def test_stage_import_rejects_bad_extension(tmp_path):
    junk = tmp_path / "model.obj"
    junk.write_text("v 0 0 0\n")
    with pytest.raises(D.SummonDeployError) as ei:
        D.stage_import(junk, {"donor": 227, "id": 6201, "private_ef": 84})
    assert ".glb" in str(ei.value) or "takes a" in str(ei.value)


def test_stage_import_missing_model():
    with pytest.raises(D.SummonDeployError):
        D.stage_import(Path("nonexistent-model.glb"), {"donor": 227})


# =========================================================================== GAME-GATED

@pytest.mark.skipif(_game() is None or not _BAHAMUT_GLB.is_file(),
                    reason="needs the FF9 install + a local skinned summon .glb (ef227_bahamut.glb)")
def test_glb_round_trip_deploys(tmp_path):
    """A skinned summon .glb through stage_import: validate -> glb->FBX -> mint -> host .seq into a tmp
    mod mirror (hybrid lane). The donor .seq is fetched read-only from the install; nothing live is
    mutated (mod_root is the tmp mirror)."""
    game = _game()
    if not D.donor_seq_path(game, 227).is_file():
        pytest.skip("donor ef227/PlayerSequence.seq not loose in this install")
    mod = tmp_path / "FF9CustomMap"
    block = {"donor": 227, "lane": "hybrid", "id": 6201, "name": "GEO_MON_B0_M201", "private_ef": 84}
    res = D.stage_import(_BAHAMUT_GLB, block, game=str(game), mod_root=mod)
    # a deployed FBX (converted from the glb) + host .seq exist under the tmp mirror
    assert Path(res["mint"]["fbx_dest"]).is_file()
    assert Path(res["mint"]["fbx_dest"]).read_bytes()[:1] == b";"    # kit ASCII-FBX starts with a comment
    seq = Path(res["seq"]["seq_dest"]).read_text(encoding="utf-8")
    assert "PlaySFX: SFX=Bahamut__Full ; Reflect=True" in seq
    assert "3DModel 6201 GEO_MON_B0_M201" in (mod / "DictionaryPatch.txt").read_text()
    assert res["imported_from"] == str(_BAHAMUT_GLB)


_DONOR_BYTES = D._local_ef_bytes(227)   # C:/gd/SCRATCH/summon-transplant/ef227.bytes (design-pinned)


@pytest.mark.skipif(_game() is None or not _DONOR_BYTES.is_file(),
                    reason="needs the FF9 install + the caller-extracted ef227.bytes under SCRATCH")
def test_overlay_lane_decodes_clips_with_nested_paths(tmp_path):
    """REGRESSION (the overlay clip-decode hang): the full overlay lane decodes the donor clips and writes
    .anim files whose SetCurve relativePaths are the NESTED bone hierarchy (bone000/bone001/...), never a
    self-repeat (bone000/bone000). Exercises _stage_overlay_extras' real parent_of build against the real
    93-bone rig (parents[0]==0) -- the path the earlier tests, using a hand-made root=None parent_of, never
    hit. Emits into a tmp mod mirror; the donor .seq/.bytes are read-only, nothing live is touched."""
    import json
    game = _game()
    if not D.donor_seq_path(game, 227).is_file():
        pytest.skip("donor ef227/PlayerSequence.seq not loose in this install")
    fbx = tmp_path / "m.fbx"
    fbx.write_bytes(b"Kaydara FBX Binary  \x00" + b"Thomas_d.png" + b"\x00" * 8)  # minimal binary-FBX stub
    (tmp_path / "Thomas_d.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    spec = D.normalize_spec({"donor": 227, "model": str(fbx), "id": 6201, "name": "GEO_MON_B0_M201",
                             "group": "MON", "private_ef": 84, "lane": "overlay", "clips": "all"})
    mod = tmp_path / "FF9CustomMap"
    res = D.emit_overlay(spec, mod, game, work_dir=tmp_path)     # MUST return (no infinite loop)
    anims = mod / "StreamingAssets/Assets/Resources/Animations/6201"
    files = sorted(anims.glob("*.anim"))
    assert files, "the overlay lane wrote no .anim clips"
    raw = files[0].read_text(encoding="utf-8")
    json.loads(raw)                                             # a valid JSON .anim the kit reader parses
    assert "bone000/bone001" in raw                            # nested hierarchy path landed
    assert "bone000/bone000" not in raw                        # NOT the self-cycle that hung before
    # the .sfxmodel Animations[] paths agree with the on-disk clip stems
    man = json.loads(Path(res["overlay"]["manifest_dest"]).read_text())
    man_stems = {p["Path"].rsplit("/", 1)[-1] for p in man["FBX"][0]["Animations"]}
    assert man_stems == {p.stem for p in files}
