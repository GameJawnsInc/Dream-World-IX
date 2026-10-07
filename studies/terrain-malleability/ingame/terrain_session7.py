"""In-game session 7 -- the VERTEX-CAP WINDOW (experiment rank 8, capacity CAP-1). DEPLOYS into the scratch mod
folder FF9CustomMap-lab ONLY (owner-approved). $VCAP_PHASE = under | over picks which vcap_build.py mesh is deployed
as Disc1 Block[21][1] Terrain.ff9mesh (an isolated IsSea cell: its Terrain file arms the sea divert onto the
Block[12][10] donor, whose own Sea1/3/4/5 free-ride under it -- consumption C6/C7).

REGISTERED PREDICTIONS (source read: WorldMeshOverride.ReadMesh admits <= 65535; Unity 5.2.3p2 refuses > 65000):
  under (64998 verts)  the cell renders a flat plane at y 6.0 and the actor stands on it (+-0.15) at both points
  over  (65001 verts)  Unity logs "Mesh.vertices is too large" (output_log.txt) WITHOUT throwing, the assignment is
                       dropped, and s34 still hands the EMPTY mesh in as the override: the cell has no land (the actor
                       grounds on the donor's free-riding water, y ~0, or the 0 default) -- and the REST of the world
                       still loads (the landing reads its normal lawn height): no LoadBlocks abort
"""
import json
import os
from pathlib import Path

PHASE = os.environ.get("VCAP_PHASE", "under")
LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
LANDING = (68.0, -444.0)
PTS = {"centre": (1377.37, -97.61), "off": (1350.63, -120.29)}
_RECORD: dict = {"phase": PHASE}


def run(g):
    g.note(f"terrain_session7: vertex-cap window, phase {PHASE}")
    g.newgame()
    g.warp(LANDING_FIELD)
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()
    _RECORD["landing_y"] = g.state.world_y
    g.check(g.state.world_y is not None and abs(g.state.world_y - 3.2) <= 0.5,
            "control: the rest of the world loaded (the landing lawn reads its normal height)",
            f"landing y {g.state.world_y}")
    rows = {}
    for k, p in PTS.items():
        g.teleport(*p)
        g.world_settle()
        g.wait_frames(30)
        rows[k] = {"y": g.state.world_y, "ui": g.state.ui_state}
    g.shot(f"vcap-{PHASE}")
    _RECORD["cell"] = rows
    if PHASE == "under":
        g.check(all(r["y"] is not None and abs(r["y"] - 6.0) <= 0.15 for r in rows.values()),
                "under (64998 verts): the actor stands on the plane at y 6.0", json.dumps(rows))
    else:
        g.check(all(r["y"] is not None and r["y"] < 3.0 for r in rows.values()),
                "over (65001 verts): the cell has NO land (the override mesh was emptied)", json.dumps(rows))
    (g.run_dir / "terrain_session7.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
