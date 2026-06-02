"""End-to-end dry run (no Blender): a bridged Blender camera + mesh -> artifacts -> ff9mapkit build.

Simulates what the add-on's Export Field operator writes (camera.bgx + walkmesh.obj + field.toml)
from a Blender camera pose + mesh, then runs the real `ff9mapkit` builder on it. Proves the
Blender -> ff9mapkit handoff produces a compilable field, entirely offline.
"""

from __future__ import annotations

import sys
from pathlib import Path

BLENDER = Path(__file__).resolve().parents[1]      # .../ff9mapkit/blender
KIT_ROOT = BLENDER.parent                          # .../ff9mapkit  (contains the ff9mapkit package)
sys.path.insert(0, str(BLENDER))                   # ff9mapkit_blender
sys.path.insert(0, str(KIT_ROOT))                  # ff9mapkit

from ff9mapkit_blender import bridge                # noqa: E402
from ff9mapkit_blender.vendor import bgx            # noqa: E402
from ff9mapkit.build import FieldProject, build_mod  # noqa: E402
from ff9mapkit.config import ModLayout, LANGS        # noqa: E402


def test_blender_export_feeds_ffmapkit_build(tmp_path):
    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()

    # 1) a Blender camera posed above & behind the origin, looking down ~45 deg
    eye = (0.0, -3000.0, 3000.0)
    R_bl = bridge.look_at_blender(eye, (0.0, 0.0, 0.0))
    lens = bridge.H_to_lens(497, bridge.DEFAULT_SENSOR, 384)
    c = bridge.blender_cam_to_ff9(eye, R_bl, lens, range_wh=(384, 448))
    (proj_dir / "camera.bgx").write_text(bgx.build(c, []), encoding="utf-8")

    # 2) a flat quad mesh on Blender z=0 -> FF9-coord walkmesh.obj
    verts_bl = [(-1000.0, -2000.0, 0.0), (1000.0, -2000.0, 0.0),
                (1000.0, 0.0, 0.0), (-1000.0, 0.0, 0.0)]
    faces = [(0, 1, 2), (0, 2, 3)]
    (proj_dir / "walkmesh.obj").write_text(bridge.mesh_to_ff9_obj(verts_bl, faces), encoding="utf-8")

    # 3) the field.toml the Export operator emits (borrow camera + walkmesh, no art layers)
    (proj_dir / "room.field.toml").write_text(
        '[field]\nid = 4007\nname = "BLENDER_ROOM"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\nborrow = "camera.bgx"\n\n'
        '[walkmesh]\nobj = "walkmesh.obj"\n\n'
        '[player]\nspawn = [0, -800]\n', encoding="utf-8")

    # 4) run the real ff9mapkit builder
    out = tmp_path / "mod"
    info = build_mod([FieldProject.load(proj_dir / "room.field.toml")], out, mod_name="FF9CustomMap")

    assert info["dictionary"] == ["FieldScene 4007 11 BLENDER_ROOM BLENDER_ROOM 1073"]
    L = ModLayout(out)
    for lang in LANGS:
        assert L.eb_path(lang, "EVT_BLENDER_ROOM.eb.bytes").is_file()
    fm = L.fieldmap_dir("FBG_N11_BLENDER_ROOM")
    assert (fm / "FBG_N11_BLENDER_ROOM.bgi.bytes").is_file()
    assert (fm / "FBG_N11_BLENDER_ROOM.bgx").is_file()
