#!/usr/bin/env pythonw
"""Double-click launcher for the FF9 Map Kit field-logic editor (no terminal needed).

Or run from anywhere:  py -m ff9mapkit edit [field.toml]   /   ff9mapkit edit [field.toml]

Edit a field's LOGIC (dialogue, events, story flags, encounters, music, cutscenes) in forms --
no TOML hand-editing. Spatial placement (camera / walkmesh / positions / zones) stays in Blender;
this never touches a sibling <name>.scene.toml.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from ff9mapkit.editor import app
except ModuleNotFoundError:                       # dev checkout without an editable install
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ff9mapkit"))
    from ff9mapkit.editor import app

if __name__ == "__main__":
    app.main(sys.argv[1] if len(sys.argv) > 1 else None)
