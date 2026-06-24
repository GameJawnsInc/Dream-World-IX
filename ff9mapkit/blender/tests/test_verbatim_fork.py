"""Blender verbatim-fork markers-only re-export safety (bpy-free side).

A VERBATIM/faithful fork ships the real field's `.bgi` walkmesh byte-for-byte
(`[walkmesh] bgi = "walkmesh.bgi"`, connectivity preserved). When you place NPC/gateway/event
markers on it in Blender and Export, the add-on writes ONLY the spatial overlay (a `<x>.scene.toml`
with positions, NO `[walkmesh]` key) and never re-emits the walkmesh as an `.obj`. The obj round-trip
would route the multi-floor mesh through `bgi.build`'s `rebuild_neighbors` (links by shared vertex
INDEX); FF9 floors use disjoint per-floor vertex sets, so cross-floor seams vanish and the player
strands on the spawn floor (proven on field 50's cargo deck: 1 connected component -> 7, 2 of 3
floors stranded).

The export operator is bpy-dependent, but the load-bearing SAFETY CONTRACT lives in the build's
two-file merge and is bpy-free: a markers `scene.toml` with no `[walkmesh]` key leaves the field.toml's
verbatim `bgi=` authoritative (build `_SCENE_SCALAR` overrides a scalar only when the scene CONTAINS
it) while positions merge onto the field logic by name. These tests lock that contract end to end,
including a byte-for-byte ship of the verbatim walkmesh through a real build.
"""

from __future__ import annotations

import sys
from pathlib import Path

BLENDER = Path(__file__).resolve().parents[1]
KIT_ROOT = BLENDER.parent
sys.path.insert(0, str(BLENDER))
sys.path.insert(0, str(KIT_ROOT))

from ff9mapkit_blender import bridge                  # noqa: E402
from ff9mapkit_blender.vendor import bgx              # noqa: E402
from ff9mapkit.build import FieldProject, build_mod   # noqa: E402
from ff9mapkit.config import ModLayout               # noqa: E402
from ff9mapkit.scene import bgi                       # noqa: E402


def _two_floor_walkmesh_bytes():
    """A multi-floor walkmesh whose two floors share a seam by world position (disjoint vertex sets) --
    exactly the topology the obj round-trip would fragment. Returned as ready-to-ship .bgi bytes."""
    verts = [(-500, 0, 0), (500, 0, 0), (500, 0, 1000), (-500, 0, 1000),        # floor 0
             (-500, 0, 1000), (500, 0, 1000), (500, 0, 2000), (-500, 0, 2000)]  # floor 1
    wm = bgi.build(verts, [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)], floor_ids=[0, 0, 1, 1])
    shared = tuple(sorted([(-500, 0, 1000), (500, 0, 1000)]))
    linked, missing, _ = wm.apply_seams([(0, shared, 1, shared)])
    assert linked == 1 and missing == 0                         # the seam joins the two floors
    assert len(wm.tri_components()) == 1                        # one connected, fully-walkable surface
    return wm.to_bytes()


# --------------------------------------------------------------------------- merge contract (no build)
def test_verbatim_scene_merge_preserves_bgi_and_merges_markers(tmp_path):
    # The markers-only export writes a scene.toml with positions and NO [walkmesh] key, so the
    # field.toml's verbatim bgi= stays authoritative; markers merge onto the field LOGIC by name.
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "vfork.field.toml").write_text(
        '[field]\nid = 4011\nname = "VFORK"\narea = 21\ntext_block = 1073\n\n'
        '[camera]\nborrow = "camera.bgx"\n\n'
        '[walkmesh]\nbgi = "walkmesh.bgi"\n\n'
        '[[npc]]\nname = "Guard"\ndialogue = "Halt."\n\n'
        '[[gateway]]\nname = "door"\nto = 100\nentrance = 0\n', encoding="utf-8")
    (proj / "vfork.scene.toml").write_text(                      # what Export writes: positions only
        '[camera]\nborrow = "camera.bgx"\n\n'
        '[[npc]]\nname = "Guard"\npos = [120, 60]\n\n'
        '[[gateway]]\nname = "door"\nzone = [[0, 0], [100, 0], [100, 100], [0, 100]]\n', encoding="utf-8")
    raw = FieldProject.load(proj / "vfork.field.toml").raw
    assert raw["walkmesh"] == {"bgi": "walkmesh.bgi"}           # verbatim walkmesh preserved (no obj key)
    npc = next(n for n in raw["npc"] if n["name"] == "Guard")
    assert npc["pos"] == [120, 60] and npc["dialogue"] == "Halt."   # pos from scene, logic from field
    gw = next(g for g in raw["gateway"] if g["name"] == "door")
    assert gw["to"] == 100 and len(gw["zone"]) == 4                 # zone from scene, target from field


def test_scene_walkmesh_key_would_override_verbatim_bgi(tmp_path):
    # Guard-rail / explainer: if a scene.toml DID carry a [walkmesh] key it REPLACES the field.toml's
    # verbatim bgi= (build _SCENE_SCALAR). This is exactly the corruption the verbatim markers-only
    # export avoids by emitting NO [walkmesh] key -- the editable branch's obj line must never leak here.
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "v.field.toml").write_text(
        '[field]\nid = 4011\nname = "V"\narea = 21\ntext_block = 1073\n\n'
        '[walkmesh]\nbgi = "walkmesh.bgi"\n', encoding="utf-8")
    (proj / "v.scene.toml").write_text(
        '[walkmesh]\nobj = "walkmesh.obj"\nframe = "world"\n', encoding="utf-8")
    raw = FieldProject.load(proj / "v.field.toml").raw
    assert raw["walkmesh"] == {"obj": "walkmesh.obj", "frame": "world"}   # bgi= LOST -- the danger


# --------------------------------------------------------------------------- full build: byte-for-byte ship
def test_verbatim_fork_markers_keep_walkmesh_byte_identical(tmp_path):
    # The load-bearing safety proof: a fork shipping [walkmesh] bgi= builds the walkmesh BYTE-FOR-BYTE
    # from the source file (no rebuild, no re-serialize), and adding a markers scene.toml never perturbs
    # it. An [[event]] keeps the build asset-free (no model catalog needed offline).
    wm_bytes = _two_floor_walkmesh_bytes()
    eye = (0.0, -3000.0, 3000.0)
    R_bl = bridge.look_at_blender(eye, (0.0, 0.0, 0.0))
    c = bridge.blender_cam_to_ff9(eye, R_bl, bridge.H_to_lens(497, bridge.DEFAULT_SENSOR, 384))

    def make_proj(name, with_markers):
        proj = tmp_path / name; proj.mkdir()
        (proj / "camera.bgx").write_text(bgx.build(c, []), encoding="utf-8")
        (proj / "walkmesh.bgi").write_bytes(wm_bytes)           # the verbatim walkmesh, shipped as-is
        field = ('[field]\nid = 4011\nname = "VFORK"\narea = 21\ntext_block = 1073\n\n'
                 '[camera]\nborrow = "camera.bgx"\n\n'
                 '[walkmesh]\nbgi = "walkmesh.bgi"\n\n'
                 '[player]\nspawn = [0, 400]\n')
        if with_markers:                                        # the author's logic for the placed event
            field += '\n[[event]]\nname = "chime"\nmessage = "ding"\nonce = false\n'
        (proj / "vfork.field.toml").write_text(field, encoding="utf-8")
        if with_markers:                                        # what Export writes: zone only, NO walkmesh
            (proj / "vfork.scene.toml").write_text(
                '[camera]\nborrow = "camera.bgx"\n\n'
                '[[event]]\nname = "chime"\nzone = [[-100, 300], [100, 300], [100, 500], [-100, 500]]\n',
                encoding="utf-8")
        return proj

    def ship(name, with_markers):
        out = tmp_path / f"mod_{name}"
        proj = make_proj(name, with_markers)
        build_mod([FieldProject.load(proj / "vfork.field.toml")], out, mod_name="FF9CustomMap")
        bgi_path = ModLayout(out).fieldmap_dir("FBG_N21_VFORK") / "FBG_N21_VFORK.bgi.bytes"
        return bgi_path.read_bytes()

    shipped_bare = ship("bare", False)
    shipped_markers = ship("markers", True)
    # 1) the verbatim walkmesh ships byte-for-byte (resolve_walkmesh returns the file bytes untouched)
    assert shipped_bare == wm_bytes
    # 2) placing spatial markers NEVER perturbs the walkmesh -- byte-identical with and without
    assert shipped_markers == shipped_bare
    # 3) the event marker actually reached the build (zone from scene merged onto field logic by name)
    raw = FieldProject.load(make_proj("check", True) / "vfork.field.toml").raw
    ev = next(e for e in raw["event"] if e["name"] == "chime")
    assert ev["message"] == "ding" and len(ev["zone"]) == 4
