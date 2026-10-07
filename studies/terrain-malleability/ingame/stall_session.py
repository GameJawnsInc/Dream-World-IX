"""In-game session "stall" -- THE DESCENT STALL (ingame/RESULTS.md section 6), the confirmation run. DEPLOYS into the
scratch mod folder FF9CustomMap-lab ONLY (first in Memoria.ini FolderNames for the run, removed after).

THE CLAIM UNDER TEST (stall_sim.py, calibrated on BOTH session-5 legs to <= 0.002u per tick, stall_PLAN.md): the
engine never stalled. When the full-speed probe (s = 0.4375) lands across the +3 tear, w_movementControl's 3D step
normalisation (ff9.cs:5568-5590) collapses the step to s^2/sqrt(s^2+dy^2) = 0.062u; the actor CREEPS to the edge and
drops (session 5 line 479.64: creep ticks 7-12, beach at tick 13). Session 5 saw "blocked" because world_approach
ends a walk after ONE burst under 0.35 x commanded (session.py:2877), three creep ticks into a six-tick creep.
Whether a line creeps at all is a PHASE: d0, the edge distance when the first probe crosses, is anywhere in (0, s];
the actor crosses at once iff d0 < one creep step. 476.28 "passed" because its d0 was 0.029, not because its drop
(2.56) was smaller.

DEPLOY (orchestrator, exactly session 5's +3 change):
    cd C:\\gd\\Dream-World-IX\\ff9mapkit
    py -m ff9mapkit world-terrain --mod-folder FF9CustomMap-lab --radius 16 --at 480 -1120 --raise 3
  -> FF9CustomMap-lab/FF9_Data/WorldMap/Disc1/0_1/r17/Block[7][17] Terrain.ff9mesh (+ its Disc4 mirror), which must be
     byte-identical to stall_sim.regen_terrain(3) (sha256 below; K0 checks it). First deploy of the folder = relaunch.
RUN:    py tools/play.py studies/terrain-malleability/ingame/stall_session.py --label stall-session
SCORE:  py studies/terrain-malleability/ingame/stall_sim.py replay .harness-runs/<stamp>-stall-session
        (re-simulates every line at the run's OWN measured heading and matches every ring position)

LINES (all on the +3 deploy; one launch; scenario order, which is also the simulator's cache order):
  C   climb control  (479.64, -1120.18) bearing 90, held through 6 bursts -- a TRUE stall the creep walker must see
  L2  the replay     (479.64, -1117.0)  bearing 270: session 5's line 2 exactly, world_approach, then HELD ON
  L4  THE 4TH LINE   (479.64, -1119.105) bearing 270: same x, same drop (2.96) as L2, start shifted so d0 = 0.036
  L5  the mirror     (476.28, -1118.78)  bearing 270: the "passing" x (drop 2.57), start shifted so d0 = 0.37

REGISTERED PREDICTIONS (stall_sim.py predict -> out/stall_predict.json; robust across the face tolerance +-2 deg and
REAL bursts unless marked). A burst is sized to ~3 world ticks from the WORLD-measured walk speed; at WorldTPS 28 vs
a 60 fps render a 6-frame burst holds 2 OR 3 ticks (the session-5 +1 ring has both), so a check never assumes a
fixed ticks-per-burst -- it asks only whether the walk ended INSIDE the line's creep run (the creep-tick tables):
  K0  the deployed Terrain sha256 == SIM_SHA; teleport grounds publish y 4.08984375 (L2), 3.87890625 (L4),
      3.23046875 (L5) exactly -- the live mesh is the simulated one
  K1  C: the creep walker reports STALLED: at most 1 moving tick, then >= 3 still bursts; final z in
      (-1120.0854, -1120.0) [within s*cos(78.75 deg) of the seam], y < 1.0 (still on the beach). Control: this is
      the instrument's proof that it CAN see a real stall.
  K2  L2 world_approach: "blocked", ending ON one of L2's creep ticks 7-13 (K2_CREEP_Z, +-0.01; with 2-3-tick bursts
      ticks 8-11, 9 the most likely: -1119.797, session 5's end) -- session 5's artifact reproduced inside the creep.
      [drop hypothesis: blocked at the last FULL tick, z -1119.610 -- no creep tick]
  K3  L2 held on: the FIRST continuation burst moves >= 0.06u (one creep tick or more) and within 4 bursts the actor
      is on the beach: z < -1120.0 and y < 1.0 (tick 13 lands (479.563, -1120.050) y 0.766).
      [stall hypothesis: no motion past the edge, y stays ~3.72-3.77]
  K4  L4 (THE 4TH LINE) world_approach: "reached"; on the beach (y < 1.0) at the end; exactly ONE collapsed tick
      (ring, scored by replay). [drop law "refused where the drop is ~3u": blocked, like L2 at the same x]
  K5  L5 world_approach: "blocked", ending ON one of L5's creep/crossing ticks 3-8 (K5_CREEP_Z, +-0.01; with 2-3-tick
      bursts ticks 4-6); held on, it crosses (z < -1120.0, y < 1.0). Holds while a burst is <= 4 ticks; at >= 5 it
      would read "reached" (an instrument limit, recorded in burst_frames / ticks_per_frame).
      [drop law: "reached", the drop is the passing line's 2.57]
  Ring (replay): every published position of C/L2/L4/L5 equals a simulated tick position within 0.002u (the state
      ring is flushed after every line, so the early lines survive to be scored).
A line a random battle interrupts is NOT JUDGED (its K check is skipped, never failed) and a failing "interrupted"
check names it -- a battle must never read as evidence for the stall hypothesis.
"""
import hashlib
import json
import os
from pathlib import Path

LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
LANDING = (68.0, -444.0)
LAB = os.environ.get("STALL_LAB_FOLDER", "FF9CustomMap-lab")
TERRAIN_REL = "FF9_Data/WorldMap/Disc1/0_1/r17/Block[7][17] Terrain.ff9mesh"
SIM_SHA = "c9bea91f0d32006e7f2492418202c14c010b9bd01fe572a620ea23199a07452e"
SEAM_Z = -1120.0
WIDE_PROBE = 0.0854                                   # 0.4375 * cos(78.75 deg): the sweep's shortest forward reach
LINES = {
    "C": {"start": (479.64, -1120.18), "bearing": 90.0, "y0": None},
    "L2": {"start": (479.64, -1117.0), "bearing": 270.0, "y0": 4.08984375, "distance": 4.0},
    "L4": {"start": (479.64, -1119.105), "bearing": 270.0, "y0": 3.87890625, "distance": 1.5},
    "L5": {"start": (476.28, -1118.78), "bearing": 270.0, "y0": 3.23046875, "distance": 1.5},
}
ON_FOOT_STEP = 0.4375                                 # S(112): one full on-foot tick on flat ground
# The z of every CREEP tick of L2 / L5 (and L5's crossing tick 8), tick -> z (stall_sim predict "creep_tick_table":
# mid of the +-2 deg band, half-range <= 0.002). world_approach's "blocked" must land on one of them. (REVIEW FIX: the
# first cut registered one end z per FIXED ticks-per-burst B = 2/3/4; real bursts mix 2 and 3 ticks, which ends the
# walk on tick 10 or 11 of L2 / tick 5 of L5 in about a third of runs -- a K2/K5 failure for a reason of the
# instrument, which the dry run's every-other-frame stand-in could not show.)
K2_CREEP_Z = {7: -1119.6719, 8: -1119.7342, 9: -1119.7969, 10: -1119.8598, 11: -1119.9230, 12: -1119.9864,
              13: -1120.0501}
K5_CREEP_Z = {3: -1119.6981, 4: -1119.7696, 5: -1119.8414, 6: -1119.9136, 7: -1119.9862, 8: -1120.0593}
TICK_TOL = 0.01
_RECORD: dict = {"lines": []}


def _tick_fit(z, table, tol=TICK_TOL):
    """The creep tick whose simulated z matches z (None: the walk did not end inside the creep run)."""
    hits = [t for t, zz in table.items() if z is not None and abs(z - zz) <= tol]
    return hits[0] if hits else None


def burst_frames_for(g, face, tag: str) -> int:
    """~3 world ticks a burst, sized from the walk speed world_face MEASURED ON THE WORLD MAP (u per frame on the flat
    landing lawn, where one tick is exactly ON_FOOT_STEP). (REVIEW FIX: the first cut used g.rate(), which is measured
    on FIELDS against FieldTPS 30 -- stale on the world map, and the world runs WorldTPS 28.)"""
    sp = (face or {}).get("speed")
    if sp:
        tpf = float(sp) / ON_FOOT_STEP
        _RECORD[f"ticks_per_frame_{tag}"] = round(tpf, 4)
        return max(2, int(round(3.0 / tpf)))
    try:
        rate = g.rate()
        _RECORD["rate"] = rate.as_dict()
        return max(2, int(round(3.0 * rate.fps / 28.0)))
    except Exception as err:
        _RECORD["rate_error"] = str(err)
        return 6


def interrupted(g, rec: dict, what: str) -> None:
    """A random battle cut this line: say so with a FAILING check of its own, and judge nothing on the line."""
    rec["not_judged"] = what
    g.check(False, f"{rec['name']} interrupted by a random battle -- {what} NOT JUDGED (rerun the line)",
            json.dumps(rec.get("battle"), default=str))


def enter_world(g) -> None:
    """The world entry every terrain session used (memory project-ff9-test-harness, OVERWORLD ON FOOT)."""
    g.newgame()
    g.warp(LANDING_FIELD)
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()


def here(g) -> dict:
    st = g.state
    px, pz, py = st.player_x, st.player_z, st.player_y
    return {"x": st.world_x, "z": st.world_z, "y": st.world_y, "ui": st.ui_state, "frame": st.frame,
            "px": None if px is None else px / 256.0, "pz": None if pz is None else pz / 256.0,
            "battle": bool(getattr(st, "in_battle", False))}


def battle_out(g, rec: dict) -> bool:
    """A random battle mid-line (session 5's +1 run lost one): flee, back to the world, mark the line. False when the
    run cannot continue (a defeat)."""
    rec["battle"] = here(g)
    try:
        # the walk saw the world go away; the battle scene may not be up yet (REVIEW FIX: a flee skipped on that
        # transition sample left a level-1 party to fight it out)
        g.wait_for(lambda s: s.in_battle or s.on_world, timeout=30.0,
                   what="the random battle to come up (or the world map to come back)")
        if g.state.in_battle and g.state.can_escape is not False:
            rec["fled"] = g.flee(timeout=25.0)
        g.leave_battle()
        g.wait_world(timeout=90)
        g.world_settle()
        return g.state.on_world
    except Exception as err:                          # a GameOver, a scene that forbids running
        rec["battle_error"] = str(err)
        return False


def creep_walk(g, rec: dict, bearing: float, burst: int, *, max_bursts: int, cross=None) -> str:
    """Hold up in bursts and log the precise (player.*) position after each, judging NOTHING mid-walk except: a
    `cross(row)` predicate met -> "crossed"; 3 bursts in a row under 1e-4u -> "stalled"; the world gone -> "battle"."""
    rows = rec.setdefault("creep", [])
    still = 0
    prev = here(g)
    for _ in range(max_bursts):
        g.send(f"hold up {int(burst)}", f"wait {int(burst) + 2}")
        g.world_settle()
        now = here(g)
        if not g.state.on_world:
            rows.append(now)
            return "battle"
        d = ((now["px"] - prev["px"]) ** 2 + (now["pz"] - prev["pz"]) ** 2) ** 0.5
        now["moved"] = round(d, 5)
        rows.append(now)
        prev = now
        if cross is not None and cross(now):
            return "crossed"
        still = still + 1 if d < 1e-4 else 0
        if still >= 3:
            return "stalled"
    return "max_bursts"


def start_line(g, name: str) -> dict:
    ln = LINES[name]
    rec = {"name": name, "start": list(ln["start"]), "bearing": ln["bearing"]}
    _RECORD["lines"].append(rec)
    g.teleport(*ln["start"])
    g.world_settle()
    g.wait_frames(15)
    rec["start_state"] = here(g)
    return rec


def end_line(g, rec: dict) -> None:
    """Keep the line's per-tick ring: the harness ring holds only the last ~10 s, so without this the replay could
    score only the last line or two (REVIEW FIX: C and L2 would have scrolled out before the run's final flush)."""
    try:
        p = g.flush_states(f"line-{rec['name']}")
        rec["ring_file"] = None if p is None else p.name
    except Exception as err:                          # an artifact, never the run
        rec["ring_file_error"] = str(err)


def run(g):
    g.note("stall_session: the descent stall at the +3 (7,17) beach tear")
    enter_world(g)

    # K0 -- the live Terrain is the simulated one (bytes), and grounds where the simulator grounds (heights below)
    f = Path(g.game_path) / LAB / TERRAIN_REL
    sha = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
    _RECORD["terrain_sha"] = sha
    g.check(sha == SIM_SHA, "K0 the deployed (7,17) Terrain is byte-identical to the simulated +3 mesh",
            f"{f}: {sha}")

    try:
        # ---- C: the climb control (a TRUE stall), facing north ----------------------------------------------
        face_n = g.world_face(90.0, home=LANDING, tolerance=2.0)
        _RECORD["face_n"] = {k: face_n.get(k) for k in ("heading", "error", "speed", "rate")}
        burst = burst_frames_for(g, face_n, "n")
        _RECORD["burst_frames"] = burst
        rec = start_line(g, "C")
        out = creep_walk(g, rec, 90.0, burst, max_bursts=6)
        rec["outcome"] = out
        rec["end"] = here(g)
        end_line(g, rec)
        if out == "battle":
            ok = battle_out(g, rec)
            interrupted(g, rec, "K1")
            if not ok:
                return
        else:
            moving = sum(1 for r in rec["creep"] if r.get("moved", 0) >= 1e-4)
            e = rec["end"]
            g.check(out == "stalled" and moving <= 1 and SEAM_Z - WIDE_PROBE < e["pz"] < SEAM_Z and e["y"] < 1.0,
                    "K1 control: the +3 CLIMB is a true stall the creep walker sees (<=1 moving burst, then still, "
                    "within 0.0854u short of the seam, on the beach)",
                    f"outcome {out}, moving bursts {moving}, end ({e['px']:.4f}, {e['pz']:.4f}) y {e['y']}")

        # ---- the descents, facing south --------------------------------------------------------------------
        face_s = g.world_face(270.0, home=LANDING, tolerance=2.0)
        _RECORD["face_s"] = {k: face_s.get(k) for k in ("heading", "error", "speed", "rate")}
        speed = face_s.get("speed")
        burst = burst_frames_for(g, face_s, "s")           # re-sized: the render rate can flip mid-launch
        _RECORD["burst_frames_s"] = burst
        y0 = {}
        on_beach = (lambda r: r["pz"] < SEAM_Z and r["y"] is not None and r["y"] < 1.0)

        # L2: the replay, then held on
        rec = start_line(g, "L2")
        y0["L2"] = rec["start_state"]["y"]
        w = g.world_approach(270.0, LINES["L2"]["distance"], speed=speed, burst_frames=burst)
        rec["approach"] = {k: w.get(k) for k in ("outcome", "progress", "path", "speed", "y_min", "y_max")}
        rec["approach"]["end"] = here(g)
        if w["outcome"] == "left_world":
            end_line(g, rec)
            ok = battle_out(g, rec)
            interrupted(g, rec, "K2 and K3")
            if not ok:
                return
        else:
            ez = rec["approach"]["end"]["pz"]
            t_fit = _tick_fit(ez, K2_CREEP_Z)
            rec["creep_tick_fit"] = t_fit
            g.check(w["outcome"] == "blocked" and t_fit is not None,
                    "K2 replay: world_approach calls session 5's line 479.64 'blocked' again, and the walk ended ON "
                    "one of the line's creep ticks (7-13) -- inside the creep, not at the last full step",
                    f"{w['outcome']} at z {ez:.4f} (burst {burst} frames; creep tick {t_fit})")
            out = creep_walk(g, rec, 270.0, burst, max_bursts=6, cross=on_beach)
            rec["outcome"] = out
            rec["end"] = here(g)
            end_line(g, rec)
            if out == "battle":
                ok = battle_out(g, rec)
                interrupted(g, rec, "K3")
                if not ok:
                    return
            else:
                first = rec["creep"][0] if rec["creep"] else {}
                first_dz = (ez - first.get("pz", ez)) if first else 0.0
                g.check(first_dz >= 0.06 and out == "crossed" and len(rec["creep"]) <= 4,
                        "K3 THE MECHANISM: held on past the 'stall', the actor keeps creeping (>= one 0.06u creep "
                        "tick in the first burst) and drops onto the beach within 4 bursts -- the engine never "
                        "refused it",
                        f"first continuation burst {first_dz:.4f}u at y {first.get('y')}; outcome {out} after "
                        f"{len(rec['creep'])} bursts; end ({rec['end']['px']:.4f}, {rec['end']['pz']:.4f}) "
                        f"y {rec['end']['y']}")

        # L4: THE 4TH LINE -- same x and drop as L2, phase-shifted start
        rec = start_line(g, "L4")
        y0["L4"] = rec["start_state"]["y"]
        w = g.world_approach(270.0, LINES["L4"]["distance"], speed=speed, burst_frames=burst)
        rec["approach"] = {k: w.get(k) for k in ("outcome", "progress", "path", "speed", "y_min", "y_max")}
        rec["end"] = here(g)
        end_line(g, rec)
        if w["outcome"] == "left_world":
            ok = battle_out(g, rec)
            interrupted(g, rec, "K4")
            if not ok:
                return
        else:
            g.check(w["outcome"] == "reached" and rec["end"]["y"] is not None and rec["end"]["y"] < 1.0,
                    "K4 THE 4TH LINE: at the SAME x and drop as the 'refused' line 479.64, a start shifted so the "
                    "last full step ends 0.036u from the edge crosses with no creep ('reached', on the beach)",
                    f"{w['outcome']} progress {w.get('progress')}; end ({rec['end']['px']:.4f}, "
                    f"{rec['end']['pz']:.4f}) y {rec['end']['y']}")

        # L5: the mirror -- the 'passing' x, phase-shifted into a long creep
        rec = start_line(g, "L5")
        y0["L5"] = rec["start_state"]["y"]
        w = g.world_approach(270.0, LINES["L5"]["distance"], speed=speed, burst_frames=burst)
        rec["approach"] = {k: w.get(k) for k in ("outcome", "progress", "path", "speed", "y_min", "y_max")}
        rec["approach"]["end"] = here(g)
        if w["outcome"] == "left_world":
            end_line(g, rec)
            ok = battle_out(g, rec)
            interrupted(g, rec, "K5")
            if not ok:
                return
        else:
            ez = rec["approach"]["end"]["pz"]
            t_fit = _tick_fit(ez, K5_CREEP_Z)
            rec["creep_tick_fit"] = t_fit
            out = creep_walk(g, rec, 270.0, burst, max_bursts=6, cross=on_beach) \
                if w["outcome"] == "blocked" else "not needed"
            rec["outcome"] = out
            rec["end"] = here(g)
            end_line(g, rec)
            if out == "battle":
                ok = battle_out(g, rec)
                interrupted(g, rec, "K5")
                if not ok:
                    return
            else:
                g.check(w["outcome"] == "blocked" and t_fit is not None and out == "crossed",
                        "K5 the mirror: at the 'passing' x 476.28 a start shifted into the creep reads 'blocked' "
                        "too (ON one of its creep ticks 3-8) -- and, held on, crosses",
                        f"{w['outcome']} at z {ez:.4f} (creep tick {t_fit}); held on: {out}; end "
                        f"({rec['end']['px']:.4f}, {rec['end']['pz']:.4f}) y {rec['end']['y']}")

        g.check(all(abs((y0.get(k) or -99) - LINES[k]["y0"]) < 1e-6 for k in ("L2", "L4", "L5")),
                "K0b the teleport grounds publish the simulated heights exactly (4.08984375 / 3.87890625 / "
                "3.23046875)", json.dumps(y0))
        g.check(not any("battle" in r for r in _RECORD["lines"]),
                "every line ran without a random battle (else its checks above are missing, not passed)",
                json.dumps([r["name"] for r in _RECORD["lines"] if "battle" in r]))
    finally:
        try:
            (g.run_dir / "stall_session.json").write_text(json.dumps(_RECORD, indent=1, default=str),
                                                          encoding="utf-8")
        except Exception as err:
            print(f"[stall] could not write the record: {err}")
