"""Offline validation of the bpy-free model-loop CLI argv builders (the one testable half of the
Import/Export FF9 Model operators; the bpy operator code + subprocess plumbing needs Blender + the install)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # .../ff9mapkit/blender
from ff9mapkit_blender import bridge   # noqa: E402


def test_safe_stem_sanitizes_geo_tokens():
    assert bridge.safe_stem("GEO_MAIN_F0_VIV") == "GEO_MAIN_F0_VIV"
    assert bridge.safe_stem("8") == "8"
    assert bridge.safe_stem("a/b\\c:d") == "a_b_c_d"          # path separators -> underscores
    assert bridge.safe_stem("") == "model"                    # never empty


def test_model_gltf_argv_shape():
    assert bridge.model_gltf_argv("GEO_MAIN_F0_VIV") == ["model-gltf", "GEO_MAIN_F0_VIV", "--anims", "auto"]
    assert bridge.model_gltf_argv("8", anims="all", scale=0.02, out="x.glb", game="G:/FF9") == \
        ["model-gltf", "8", "--anims", "all", "--scale", "0.02", "--out", "x.glb", "--game", "G:/FF9"]


def test_model_import_argv_shape():
    assert bridge.model_import_argv("x.glb", "MOD") == ["model-import", "x.glb", "--deploy", "MOD"]
    assert bridge.model_import_argv("x.glb", "MOD", like="GEO_MAIN_F0_VIV", model_id=6001,
                                    no_anims=True, game="G") == \
        ["model-import", "x.glb", "--deploy", "MOD", "--like", "GEO_MAIN_F0_VIV",
         "--id", "6001", "--no-anims", "--game", "G"]


def test_model_import_argv_omits_falsey_options():
    """A blank --like / no id / anims-on must not emit stray flags (they'd confuse the CLI parser)."""
    argv = bridge.model_import_argv("x.glb", "MOD", like="", model_id=None, no_anims=False)
    assert "--like" not in argv and "--id" not in argv and "--no-anims" not in argv
