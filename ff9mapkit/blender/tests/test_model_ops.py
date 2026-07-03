"""Offline validation of the bpy-free model-loop command helpers (the testable half of the Import/Export
FF9 Model operators; the bpy operator code + glТF I/O needs Blender). The add-on exports the .glb and REPORTS
the `ff9mapkit model-import ...` command -- it never runs the toolkit, matching Export Field -> `ff9mapkit build`."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # .../ff9mapkit/blender
from ff9mapkit_blender import bridge   # noqa: E402


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


def test_quote_cmd_double_quotes_spaced_tokens():
    """The reported command must survive a paste into a terminal -- a path with spaces (Program Files) gets
    double-quoted (Windows-friendly, not shlex's POSIX single-quotes); bare tokens stay bare."""
    argv = bridge.model_import_argv(r"C:\out\my model.glb", r"C:\Program Files (x86)\Steam\FF9\FF9CustomMap")
    cmd = "ff9mapkit " + bridge.quote_cmd(argv)
    assert cmd == ('ff9mapkit model-import "C:\\out\\my model.glb" --deploy '
                   '"C:\\Program Files (x86)\\Steam\\FF9\\FF9CustomMap"')
    assert bridge.quote_cmd(["model-import", "x.glb", "--deploy", "MOD"]) == "model-import x.glb --deploy MOD"
