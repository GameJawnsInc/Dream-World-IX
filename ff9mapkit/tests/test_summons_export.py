"""``summons.export`` -- the user-facing offline glTF exporters + the LOCAL-ONLY write guard.

Two lanes (the suite's game-gated pattern, cf. test_summons_container.py / test_summons_build.py):
  * OFFLINE (always runs) -- the write guard's refusal logic (repo tree + mod-folder classes), the default
    output path, and the "no creature" rejection on a hand-built synthetic blob. No install, no stock bytes.
  * GAME-GATED -- the full end-to-end export + rig-ref of the user's own locally-extracted Bahamut (ef227,
    93 bones / 8 clips) and Odin (ef261, 97 bones) with a structural glTF parse of the emitted .glb. Skips
    cleanly when the local ``C:/gd/SCRATCH/summon-format/`` blobs are absent.
"""
from __future__ import annotations

import json
import os
import re
import struct

import pytest

import ff9mapkit
from ff9mapkit.summons import export as X

_SCRATCH = r"C:/gd/SCRATCH/summon-format"


def _ef(effid: int) -> str:
    return os.path.join(_SCRATCH, f"ef{effid:03d}.bytes")


def _have(effid: int) -> bool:
    return os.path.exists(_ef(effid))


def _read_glb_json(path) -> dict:
    """The JSON chunk of a .glb (structural validation -- no Blender)."""
    b = open(path, "rb").read()
    magic, ver, _total = struct.unpack_from("<III", b, 0)
    assert magic == 0x46546C67 and ver == 2
    jlen, jtype = struct.unpack_from("<II", b, 12)
    assert jtype == 0x4E4F534A
    return json.loads(b[20:20 + jlen].decode("utf-8"))


def _bone_names(gltf) -> list:
    return [n["name"] for n in gltf["nodes"] if re.fullmatch(r"bone\d{3}", str(n.get("name", "")))]


# ------------------------------------------------------------------ OFFLINE: the write guard (always runs)
def test_guard_refuses_inside_the_repo():
    # A path derived from the installed package location is inside the git checkout -> refused (any ancestor
    # holding a .git file/dir). Deterministic regardless of CWD.
    inside_repo = os.path.join(os.path.dirname(ff9mapkit.__file__), "summons", "NOPE.glb")
    with pytest.raises(X.SummonExportError) as ei:
        X.assert_local_only(inside_repo)
    assert "git repo" in str(ei.value)


def test_guard_refuses_a_mod_folder_streamingassets(tmp_path):
    # The mod-folder class: any StreamingAssets segment on the path (independent of any real install).
    modish = tmp_path / "FF9CustomMap" / "StreamingAssets" / "Assets" / "x.glb"
    with pytest.raises(X.SummonExportError) as ei:
        X.assert_local_only(modish)
    assert "mod folder" in str(ei.value)


def test_guard_allows_a_plain_local_path(tmp_path):
    # A scratch/temp dir that is not a repo, not a mod folder, not the install -> allowed (returns resolved).
    out = tmp_path / "sub" / "ok.glb"
    got = X.assert_local_only(out)
    assert got == out.resolve()


def test_default_out_lives_under_default_out_dir():
    assert X.default_out("C:/gd/SCRATCH/summon-format/ef227.bytes") == X.DEFAULT_OUT_DIR / "ef227.glb"
    assert X.default_out("ef261.bytes", rig=True) == X.DEFAULT_OUT_DIR / "ef261_rig.glb"


def test_export_of_a_non_creature_blob_is_rejected(tmp_path):
    # A well-formed container with only an id-3 resource (no id-4 + id-5 creature package) -> SummonExportError,
    # and NOTHING is written. Offline: a hand-built blob, a plain local out path.
    header = struct.pack("<H", 1) + struct.pack("<HH", 0, 1) + struct.pack("<bbH", 3, 0, 1)
    blob = header + b"\x00" * (0x1000 - len(header))
    src = tmp_path / "ef999.bytes"
    src.write_bytes(blob)
    out = tmp_path / "out.glb"
    with pytest.raises(X.SummonExportError) as ei:
        X.export_summon_glb(str(src), str(out))
    assert "no creature" in str(ei.value)
    assert not out.exists()


# ------------------------------------------------------------------ GAME-GATED (local stock blobs)
@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_full_export_structure(tmp_path):
    out = tmp_path / "ef227.glb"
    man = X.export_summon_glb(_ef(227), str(out))
    assert out.exists() and man["bones"] == 93 and man["clip_frames"] == [24, 30, 26, 48, 40, 68, 82, 28]

    gltf = _read_glb_json(out)
    assert _bone_names(gltf) == [f"bone{k:03d}" for k in range(93)]
    # forward-referencing hierarchy: a bone node's children index higher than itself
    for i, n in enumerate(gltf["nodes"]):
        if re.fullmatch(r"bone\d{3}", str(n.get("name", ""))):
            assert all(c > i for c in n.get("children", []))
    # 8 animations, frame counts == the input-accessor counts of each first sampler
    anims = gltf["animations"]
    assert len(anims) == 8
    frames = [gltf["accessors"][a["samplers"][0]["input"]]["count"] for a in anims]
    assert frames == [24, 30, 26, 48, 40, 68, 82, 28]
    # skinned mesh parts present
    mesh_nodes = [n for n in gltf["nodes"] if "mesh" in n]
    assert len(mesh_nodes) == 2 and all("skin" in n for n in mesh_nodes)


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_rig_ref_is_skeleton_only(tmp_path):
    out = tmp_path / "ef227_rig.glb"
    man = X.export_rig_ref(_ef(227), str(out))
    assert out.exists() and man["bones"] == 93 and man["creature"]["meshes"] == 0

    gltf = _read_glb_json(out)
    assert len(gltf["nodes"]) == 93                              # exactly the bones, no mesh node
    assert _bone_names(gltf) == [f"bone{k:03d}" for k in range(93)]
    assert not gltf.get("animations")                           # 0 animations
    assert not gltf.get("meshes")                               # no mesh payload beyond markers
    assert not any("mesh" in n for n in gltf["nodes"])
    assert len(gltf["skins"][0]["joints"]) == 93                # the armature the user skins onto


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_export_respects_the_guard(tmp_path, monkeypatch):
    # Even a real creature is refused into a repo path (the guard fires before any write).
    monkeypatch.chdir(tmp_path)
    with pytest.raises(X.SummonExportError):
        X.export_summon_glb(_ef(227), os.path.join(os.path.dirname(ff9mapkit.__file__), "x.glb"))


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_rest_clip0_poses_the_root(tmp_path):
    # rest='clip0' poses the skeleton from clip0/frame0 -- node0's rotation differs from the identity default.
    ident = _read_glb_json(X.export_summon_glb(_ef(227), str(tmp_path / "i.glb"), anims="none") and tmp_path / "i.glb")
    posed = _read_glb_json(X.export_summon_glb(_ef(227), str(tmp_path / "p.glb"), anims="none", rest="clip0")
                           and tmp_path / "p.glb")
    r_ident = ident["nodes"][0].get("rotation", [0.0, 0.0, 0.0, 1.0])
    r_posed = posed["nodes"][0].get("rotation", [0.0, 0.0, 0.0, 1.0])
    assert r_ident != r_posed


@pytest.mark.skipif(not _have(261), reason="needs local C:/gd/SCRATCH/summon-format/ef261.bytes")
def test_ef261_odin_generalises(tmp_path):
    man = X.export_summon_glb(_ef(261), str(tmp_path / "ef261.glb"))
    assert man["bones"] == 97
    gltf = _read_glb_json(tmp_path / "ef261.glb")
    assert _bone_names(gltf) == [f"bone{k:03d}" for k in range(97)]

    rig = X.export_rig_ref(_ef(261), str(tmp_path / "ef261_rig.glb"))
    assert rig["bones"] == 97
    grig = _read_glb_json(tmp_path / "ef261_rig.glb")
    assert len(grig["nodes"]) == 97 and not grig.get("meshes") and not grig.get("animations")


@pytest.mark.skipif(not _have(381), reason="needs local C:/gd/SCRATCH/summon-format/ef381.bytes")
def test_ef381_one_frame_clips_do_not_over_report(tmp_path):
    # ef381 carries 1-frame clips (4 of its 12) that emit_model_gltf drops (a rotation channel needs >=2 keys).
    # clip_frames / creature.clips must count only the EMBEDDED clips, so all three manifest counts agree with
    # the .glb's actual animation count -- pre-fix clip_frames/creature.clips reported all 12 while the .glb
    # held 8 (a caller enumerating embedded clips via the manifest was off by the dropped 1-frame-clip count).
    out = tmp_path / "ef381.glb"
    man = X.export_summon_glb(_ef(381), str(out))
    n_glb = len(_read_glb_json(out).get("animations", []))
    assert len(man["clip_frames"]) == n_glb
    assert man["creature"]["clips"] == n_glb
    assert len(man["anims"]) == n_glb
    assert all(f >= 2 for f in man["clip_frames"])              # a 1-frame clip is never counted as embedded
