"""In-game session PNG -- THE PER-CELL TEXTURE OVERRIDE (terrain study README section 7.1 rank 6; capacity X5,
consumption C10). DEPLOYS into the scratch folder FF9CustomMap-lab ONLY: the tree `png_prep.py` builds under
out/png_lab/FF9CustomMap-lab (commands in png_PLAN.md section 4). No live mod folder is touched.

THE LAB TREE (all Disc1, the s34 namespace `FF9_Data/WorldMap/Disc1/0_1/r{y}/Block[x][y] <child>`):
  A (21,1)  Terrain.ff9mesh + Sea4.ff9mesh   = the donor Block[12][10]'s own meshes, float-equal (zero authorship)
            Terrain.png magenta, Sea4.png red, Sea3.png lime  (Sea3 has NO .ff9mesh on purpose)
  B (0,13)  Terrain.ff9mesh + Sea4.ff9mesh   (same bytes), no PNG                -> the control cell
Both are IsSea cells with all 8 neighbours sea and nothing live in their 3x3, so the Terrain file arms the s34 divert
onto Block[12][10] (WMWorld.cs:521-533) and the cell renders the stock islet with its free-riding Sea1/3/5.

REGISTERED PREDICTIONS (before any run; source: WMWorld.cs:812-858 + :808, WMBlock.cs:106-111 + :273-341,
WorldMeshOverride.cs:141-170, WMRenderTextureBank.cs:46-63 -- see png_judge.py's header):
  L0   the actor stands on the islet at A and B: y = 3.546 +-0.15 (unbound: open sea ~0, or the lawn's 3.2 kept)
  L1   per world load, Memoria.log carries mesh receipts A{Terrain,Sea4} + B{Terrain,Sea4} from FF9CustomMap-lab,
       texture receipts EXACTLY A: Terrain then Sea4; none for B; none for Sea3 (TryLoadTexture only runs inside a
       successful mesh bind, WMWorld.cs:826 -> :835)
  T1   TERRAIN: the PNG is LOADED (L1) but NOT RENDERED: magenta at A <= B + noise in every frame. Mechanism:
       SetupPreloadedMaterials (WMWorld.cs:808) reassigns MaterialDatabase["Terrain"] = the Moguri loose atlas
       (MoguriMain ships worldmap/textures/res(1_24)_terrain.png; png_prep resolved it as the engine does).
       Counterfactual size: the islet is 6.2% (P1) / 8.5% (P2) of the frame.
  S4   SEA4: the PNG RENDERS: red >= 2% of the scored frame in every A frame (projection: 29.3% / 29.8%), B <= noise;
       S4s it is STATIC across the stock sea animation (red min/max >= 0.95 over 3 frames ~60 frames apart, while
       B's lower half changes between the same frames -- the animation precondition ANIM).
  S3   SEA3 PNG WITHOUT A SEA3 MESH: never opened, never rendered: lime at A <= B + noise (counterfactual 4.7% /
       3.8% detectable) and no Sea3 texture receipt (L1).
  CTRL B shows no vivid class above noise (0.05% of the frame, >= 200 px) in any frame.
  R1   after a world reload (field 6603 -> world), the receipts repeat (L1 again) and A is red again: a PNG is
       re-read on every world load (File.Exists per LoadBlock), so PNG content needs NO relaunch; the clobbering
       MaterialDatabase is process-static (WMBlock.cs:275 MaterialDatabaseLoaded).
  S4m  (secondary, model) red fraction / projected Sea4-detectable within [0.5, 1.5].
$PNG_PHASE=nopng is the optional temporal control (a second launch after deleting the three PNGs from the lab):
then L1 expects NO texture receipt and every class at A <= B + noise.

Poses: the camera is faced on the safe-road lawn FACE_HOME (32.37, -448.61) with world_face (bearing P1 45, P2 225 from
png_prep.json: each frame holds the islet, Sea4, Sea3 and Sea5), then the actor teleports to the stand point (the
centroid of the donor's lawn tri 18, off the 4u lattice) at A, back to the lawn, then to B -- the camera yaw survives
a teleport, so A and B frames share one pose. (The 6603 landing itself has the entrance tile 8-12u out on
bearings 345-25: a probe toward P1 could re-enter the field -- png_prep.py step 7.) Nothing moves on the islets
(encounters need movement).

    py studies/terrain-malleability/ingame/png_prep.py                     (builds the lab tree + prep json)
    py tools/play.py studies/terrain-malleability/ingame/png_session.py --label terrain-png
    py studies/terrain-malleability/ingame/png_post.py <run dir>          (offline re-score, same checks)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools"))
import png_judge as J                                  # noqa: E402
from harness.logs import line_start_offset, read_from   # noqa: E402

PHASE = os.environ.get("PNG_PHASE", "main")             # main | nopng
RELOAD = os.environ.get("PNG_RELOAD", "1") != "0"
PREP = json.loads(J.PREP_JSON.read_text(encoding="utf-8"))

LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
LANDING = (68.0, -444.0)                 # where walk_out lands (the 6603 west door); NOT a face home
FACE_HOME = J.FACE_HOME                   # clear 40u disc, area 14, y 3.2 (png_prep.py step 7)
STAND = {"A": tuple(PREP["stands"]["A"]["world"]), "B": tuple(PREP["stands"]["B"]["world"])}
POSES = [(p["tag"], float(p["bearing"])) for p in PREP["poses"]]
SETTLE_FRAMES = 180          # the camera eases after a teleport (> 90 frames measured, RESULTS.md lessons)
SPACING = 30                 # frames between the 3 shots of one pose (spans >= 1 sea-animation cycle of ~30 ticks)
NSHOTS = 3

_RECORD: dict = {"phase": PHASE, "prep_poses": POSES, "stands": STAND, "visits": [], "poses": {}, "notes": [],
                 "recoveries": 0}


def _save(g):
    (g.run_dir / "png_session.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")


def here(g) -> dict:
    st = g.state
    return {"x": st.world_x, "z": st.world_z, "y": st.world_y, "world": st.world_id, "ui": st.ui_state,
            "scenario": st.scenario}


# ---------------------------------------------------------------------------------------------- the log receipts
def log_mark(g):
    p = g.engine_log()
    return [str(p), line_start_offset(p)] if p is not None else [None, 0]


def take_receipts(g, tag, mark):
    path = g.engine_log()
    text = read_from(path, mark[1]) if (path is not None and str(path) == mark[0]) else ""
    rows = J.receipts(text)
    v = {"tag": tag, "mark": mark, "rows": rows, "summary": J.receipt_summary(rows)}
    _RECORD["visits"].append(v)
    print(f"[png] {tag} receipts: {json.dumps(v['summary'])}")
    _save(g)
    return v


# ---------------------------------------------------------------------------------------------- reaching the world
def walk_out(g):
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()


def reach_world(g):
    """Title/any state -> new game -> 6603 -> its west door -> the overworld. Returns the log mark taken on the
    field, BEFORE the world load that writes the receipts."""
    g.newgame()
    g.warp(LANDING_FIELD)
    mark = log_mark(g)
    walk_out(g)
    return mark


def recover(g, where: str) -> None:
    """Off the world map: flee/fight a battle; on a GameOver, back to the title and out again."""
    st = g.state
    _RECORD["notes"].append(f"left the world at {where}: ui {st.ui_state}")
    print(f"[png] left the world at {where}: ui {st.ui_state}")
    try:
        if st.in_battle or st.ui_state == "BattleHUD":
            if not g.flee(timeout=60):
                g.fight()
            g.leave_battle(timeout=120)
        if g.state.on_world:
            g.world_settle()
            return
    except Exception as err:
        print(f"[png] battle handling at {where} failed: {err}")
    ok, why = g.restore_baseline()
    print(f"[png] restore_baseline: {ok} {why}")
    _RECORD["recoveries"] += 1
    mark = reach_world(g)
    take_receipts(g, f"visit-recovered-{_RECORD['recoveries']}", mark)


# ---------------------------------------------------------------------------------------------- one pose, one cell
def go(g, xz):
    g.teleport(*xz)
    g.world_settle()
    g.wait_frames(20)


def shoot_cell(g, pose_tag, cell):
    go(g, FACE_HOME)                                   # A and B are both entered from the lawn (y 3.2): an
    go(g, STAND[cell])                                 # unbound cell can never read the islet's 3.546
    if not g.state.on_world:
        recover(g, f"{pose_tag}/{cell}")
        return None
    row = {"arrive": here(g), "y": g.state.world_y}
    g.wait_frames(SETTLE_FRAMES)
    shots, files = [], []
    for k in range(NSHOTS):
        if k:
            g.wait_frames(SPACING)
        p = g.shot(f"{pose_tag}-{cell}-{k}")
        c = J.frame_counts(p)
        c["file"] = p.name
        shots.append(c)
        files.append(p)
    row["shots"] = shots
    row["leave"] = here(g)
    if shots and shots[0]["w"] > 8:
        reg = J.lower_region(shots[0]["w"], shots[0]["h"])
        row["gray_change"] = [J.gray_change(files[k], files[k + 1], reg) for k in range(len(files) - 1)]
    else:
        row["gray_change"] = []
    print(f"[png] {pose_tag}/{cell}: y {row['y']} "
          + " ".join(f"[m {s['magenta']} r {s['red']} l {s['lime']} / {s['n']}]" for s in shots)
          + f" gray {row['gray_change']}")
    return row


def do_pose(g, tag, bearing):
    go(g, FACE_HOME)
    face = g.world_face(bearing, home=FACE_HOME, tolerance=6.0)
    rec = {"bearing": bearing, "face": {k: face.get(k) for k in ("heading", "error", "speed", "rate")}}
    _RECORD["poses"][tag] = rec
    for cell in ("A", "B"):
        rec[cell] = shoot_cell(g, tag, cell)
        _save(g)


# ---------------------------------------------------------------------------------------------- the run
def run(g):
    g.note(f"png_session: per-cell PNG override, phase {PHASE}")
    mark = reach_world(g)
    _RECORD["start"] = here(g)
    g.check(g.state.world_y is not None and abs(g.state.world_y - 3.2) <= 0.5,
            "control: the world loaded (the landing lawn reads its normal height)", f"{_RECORD['start']}")
    for tag, bearing in POSES:
        for attempt in (1, 2):                         # one recover-and-retry: a pose is A and B under ONE yaw
            try:
                do_pose(g, tag, bearing)
                break
            except Exception as err:                   # HarnessError from world_face/teleport off the world map
                _RECORD["notes"].append(f"{tag} attempt {attempt}: {err}")
                print(f"[png] {tag} attempt {attempt} failed: {err}")
                if attempt == 2:
                    break
                if g.state.on_world:
                    continue
                recover(g, tag)
    take_receipts(g, "visit1", mark)                   # flushed per line (Memoria.Prime/Log.cs:112): complete

    if RELOAD:
        go(g, FACE_HOME)
        g.world_warp(LANDING_FIELD)
        mark2 = log_mark(g)
        walk_out(g)
        tag, bearing = POSES[0]
        go(g, FACE_HOME)
        g.world_face(bearing, home=FACE_HOME, tolerance=6.0)
        go(g, STAND["A"])
        rl = {"y": g.state.world_y, "shots": []}
        g.wait_frames(SETTLE_FRAMES)
        p = g.shot(f"reload-{tag}-A")
        c = J.frame_counts(p)
        c["file"] = p.name
        rl["shots"].append(c)
        _RECORD["reload"] = rl
        take_receipts(g, "visit2-reload", mark2)

    for ok, what, detail in J.evaluate(_RECORD, PREP):
        g.check(ok, what, detail)
    _save(g)
    go(g, FACE_HOME)
    g.shot("99-done")
