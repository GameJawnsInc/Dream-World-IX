"""The open question, measured: how close can the 3D view's camera come to the game's own world camera?

    py studies/overworld-editor/c7_lab.py capture   # the game: stills at known spots and yaws, with the live camera state
    py studies/overworld-editor/c7_lab.py compare   # offline: world.gamecam's pose, rendered, against each still

THE CAPTURE: reach the world (a1_reach), then at each SPOT teleport the party, turn the camera by a held bumper for
each TURN, let it settle (the eye and aim ease in), read the published state -- world x/y/z, ``cam_rot`` (yaw,
degrees), ``cam_upper`` (tilt), ``ctl`` (on foot) -- and take the engine's own still (the full frame, ReadPixels). The
game is closed at the end. Nothing is deployed: it reads the world as it stands.

THE COMPARE: for each still, ``world.gamecam.pose`` from the published state (the user's own Memoria.ini [Worldmap],
the ground under the eye from the kit's ground query), drawn by ``render.raster`` at the still's own size, and the two
frames compared where they can be: the land/sea boundary (the game's fog leaves the near field; render.py draws no
fog). The residual is searched over the decode's one slack (the eye and aim heights inside their settle bands) and,
apart, over a free yaw/pitch nudge, so what is left is named, not hidden.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402  (the paths, the ground probe)
import c2_lab as C2                                                    # noqa: E402  (the shell steps)

GAME, KIT, REPO = C1.GAME, C1.KIT, C1.REPO
OUT = HERE / "out" / "c7_lab"
CAPTURE = HERE / "out" / "c7_capture.json"
COMPARE = HERE / "out" / "c7_compare.json"
SPOTS = {                                                              # named, known ground: each lab left one
    "landing": C1.CONTROL[1:],                                         # the Landing Site, stock grass
    "hill": (80.37, -472.29),                                          # C6's hill top (the dome in the near field)
    "river": (22.37, -702.29),                                         # C5's moved river island (the channel nearby)
}
TURNS = (0, 24, 24)                                                    # bumper frames before each still (cumulative)
SETTLE = 90                                                            # frames for the eased eye / aim to stop


def capture_scenario(g):
    """Run by tools/play.py: the stills and the state beside each."""
    import traceback
    rows = []
    out = g.run_dir / "c7_capture.json"
    for name, (x, z) in SPOTS.items():
        try:
            g.teleport(x, z)
            g.world_settle()
            for k, frames in enumerate(TURNS):
                if frames:
                    g.send(f"hold leftbumper {frames}", f"wait {frames + 2}")
                g.wait_frames(SETTLE)
                st = g.state                                     # a property on the scenario's harness
                row = {"spot": name, "turn": k, "x": st.world_x, "y": st.world_y, "z": st.world_z,
                       "cam_rot": st.world_cam_rot, "cam_upper": st.world_cam_upper, "ctl": st.world_ctl}
                rows.append(row)
                out.write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
                row["shot"] = str(g.shot(f"c7-{name}-{k}"))
                out.write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
                g.check(st.world_cam_rot is not None, f"{name} #{k}: the camera's yaw is published",
                        json.dumps(row, default=str))
        except Exception:                                              # noqa: BLE001 -- the next spot still runs
            rows.append({"spot": name, "error": traceback.format_exc()})
            out.write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")


def run(g):                                                            # tools/play.py's entry
    capture_scenario(g)


def capture():
    py = sys.executable
    OUT.mkdir(parents=True, exist_ok=True)
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S")}
    r = C2._sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c7-reach"], 900)
    rec["reach_rc"] = r.returncode
    try:
        if r.returncode == 0:
            r = C2._sh([py, "tools/play.py", Path(__file__), "--attach", "--keep-open", "--label", "c7-capture"], 900)
            rec["capture_rc"] = r.returncode
            (OUT / "capture_stdout.txt").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr, encoding="utf-8")
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c7-quit"], 300)   # close the game
    runs = sorted((REPO / ".harness-runs").glob("*-c7-capture"))
    if runs and (runs[-1] / "c7_capture.json").is_file():
        rows = json.loads((runs[-1] / "c7_capture.json").read_text(encoding="utf-8"))
        for row in rows:                                               # the stills stay out of the repo (provenance)
            if not row.get("shot"):
                continue
            src = Path(row["shot"])
            if not src.is_file():
                cand = list(runs[-1].rglob(src.name))
                if cand:
                    row["shot"] = str(cand[0])
        rec["rows"] = rows
    CAPTURE.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items() if k != "rows"}, default=str))
    for row in rec.get("rows", []):
        print(row)


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["capture"]:
        capture()
    elif cmd == ["compare"]:
        import c7_compare
        c7_compare.main()
    else:
        raise SystemExit(__doc__)
