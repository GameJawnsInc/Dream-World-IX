#!/usr/bin/env python3
"""Teleport the RUNNING game's party to a world point, through the in-game test harness (dev checkout only).

    py tools/world_teleport.py X Z                # e.g. py tools/world_teleport.py 1100.5 -800.25
    py tools/world_teleport.py X Z --shot NAME    # ... and an in-engine still once he has settled

The World tab's 3D view runs this for "Teleport game here" (editor rung A1, ``studies/overworld-editor/PLAN.md``),
the way the Build tab shells out to ``tools/deploy_field.py``: the shipped package never imports the harness.

It ATTACHES to the game already running (never launches or quits it), arms the harness only for the one request,
sends the engine's own overworld ``teleport x z`` (the debug menu's: the party re-grounds by the sky ray at the new
point), verifies the published world position moved there, waits for it to settle, and disarms. It refuses, with
the reason, when no game is running, when the game is not on the overworld, or when another harness run holds this
install. The last line of output is one JSON object: ``{"ok", "x", "z", "world_x", "world_y", "world_z", "shot", "run_dir", "error"}``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                                 # tools/harness


def main(argv) -> int:
    shot = None
    if len(argv) == 4 and argv[2] == "--shot":
        shot, argv = argv[3], argv[:2]
    if len(argv) != 2:
        print(__doc__)
        return 2
    x, z = float(argv[0]), float(argv[1])
    out = {"ok": False, "x": x, "z": z, "world_x": None, "world_y": None, "world_z": None, "shot": None,
           "run_dir": None, "error": None}
    try:
        from harness.session import Session
        with Session(label="world-teleport", attach=True, verbose=False) as s:
            out["run_dir"] = str(s.run_dir)
            s.teleport(x, z)
            st = s.world_settle()                             # the sky re-ground lands a tick or two later
            out.update(ok=True, world_x=st.world_x, world_y=st.world_y, world_z=st.world_z)
            y = "?" if st.world_y is None else f"{st.world_y:.3f}"
            print(f"teleported to x {st.world_x:.2f}, z {st.world_z:.2f}, standing at y {y} "
                  f"(asked {x:.2f}, {z:.2f})")
            if shot:
                out["shot"] = str(s.shot(shot))
    except Exception as e:                                    # noqa: BLE001 -- the reason IS the output
        out["error"] = f"{type(e).__name__}: {e}"
        print(f"teleport refused: {out['error']}")
    print(json.dumps(out))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
