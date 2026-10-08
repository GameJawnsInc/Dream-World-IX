"""In-game check of THE HOST-AREA STAMP (terrain study defects 15-17, fixed on the live Southern Ring 2026-10-08;
southern-ring REVERT.md section 32). NO DEPLOY: it reads the live install as it stands.

    py studies/terrain-malleability/ingame/area_host_prep.py
    py tools/play.py studies/terrain-malleability/ingame/area_host_session.py --label area-host

REGISTERED PREDICTIONS (out/area_host_prep.json, written before the run; area 14 = "Lindblum Plateau"):
  H0  precondition: scenario < 4990, so the area-12 camera lock WOULD be live if any area 12 were left.
  H1  P12, round 1's lock spot on the carried Cleyra tiles: the window title names area 14 (round 1: "Vube Desert").
  H2  CONTROL at P14: R2 changes the camera. Then at P12, R2 ALSO changes it (round 1: refused, the area-12 lock).
  H3  BEACH, a first-hit Beach1 point on Sandreach (12,18): the title names area 14 (before: "Palmnell Island").
  H4  QUAY, Ashvale's trigger tile: the title names area 14 (before: "Gunitas Basin"), and Confirm still enters
      field 6601 (the Lantern Hall) -- the trigger dispatches through its cell tag, which the stamp did not touch.
CALIBRATION: if the P14 control does not change the frame, H2 is reported as proved-nothing, never as a pass.
  C1-C3  the title follows the tile: before each fixed point the session stands on a STOCK area-12 point (CONTROL,
         "Vube Desert") and the title must read it. Every fixed point names area 14, as P14 does, so without this a
         title that never updated would pass H1/H3/H4a (the first run, 2026-10-08 10:45, had no such control).
"""
import ctypes
import json
import sys
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import terrain_session1 as T1                         # noqa: E402 -- reuse the round-1 frame instruments

PREP = json.loads((HERE / "out" / "area_host_prep.json").read_text(encoding="utf-8"))
WANT = PREP["location_text"]["14"]
CONTROL_NAME = PREP["location_text"]["12"]
LANTERN_HALL = 6601
SETTLE = 150                                          # frames: a teleport eases the camera for > 90 frames
_RECORD: dict = {"notes": []}


def titles():
    """Every top-level window title containing 'World Map' (Memoria prefixes 'FINAL FANTASY IX - ')."""
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _l):
        n = user32.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, buf, n + 1)
            if "World Map" in buf.value:
                found.append(buf.value)
        return True

    user32.EnumWindows(cb, 0)
    return found


def names_ok(ts, want=None):
    return any(t.endswith(want or WANT) for t in ts)


def control(g, n):
    ts = stand(g, "CONTROL")
    _RECORD[f"CONTROL_{n}"] = _RECORD.pop("CONTROL")
    g.check(names_ok(ts, CONTROL_NAME), f"C{n} (instrument): on the stock control the title names '{CONTROL_NAME}'",
            str(ts))


def stand(g, key):
    """Teleport onto a prep point, let the camera settle, return (titles, position)."""
    x, z = PREP[key]["world"]
    g.teleport(x, z)
    g.world_settle()
    g.wait_frames(SETTLE)
    ts = titles()
    _RECORD[key] = {"titles": ts, "pos": T1.here(g)}
    return ts


def r2_change(g, tag):
    """(noise, change): two no-input frames, then R2 and a settled frame; R2 again restores the camera."""
    a = T1.snap(g, f"{tag}-a", 30)
    b = T1.snap(g, f"{tag}-b", 30)
    g.press("r2")
    c = T1.snap(g, f"{tag}-r2", T1.SETTLE)
    g.press("r2")
    g.wait_frames(T1.SETTLE)
    noise, change = T1.fdiff(a, b), T1.fdiff(a, c)
    _RECORD[f"{tag}_r2"] = {"noise": noise, "change": change}
    return noise, change


def run(g):
    g.note("area_host_session: the host-area stamp, no deploy")
    g.newgame()
    g.warp(T1.LANDING_FIELD)
    g.wait_frames(45)
    g.calibrate_axes(hazards=[T1.DOOR])
    g.walk_to(*T1.EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()
    st = g.state
    _RECORD["start"] = T1.here(g)
    g.check(0 <= st.scenario < T1.LOCK_SCENARIO, "H0: scenario below 4990 (an area-12 tile would lock the camera)",
            f"scenario {st.scenario}")

    # H2 control + H1 + H2
    stand(g, "P14")
    n14, c14 = r2_change(g, "p14")
    cam_ok = c14 > max(3 * n14, n14 + 2.0)
    g.check(cam_ok, "H2 control: R2 changes the camera on P14 (area 14)", f"change {c14} vs noise {n14}")
    control(g, 1)
    ts = stand(g, "P12")
    g.check(names_ok(ts), f"H1: on the Cleyra tiles (P12) the title names '{WANT}' (was 'Vube Desert')", str(ts))
    n12, c12 = r2_change(g, "p12")
    if cam_ok:
        g.check(c12 > max(3 * n12, n12 + 2.0), "H2: R2 now changes the camera on P12 (round 1: refused)",
                f"change {c12} vs noise {n12}")
    else:
        _RECORD["notes"].append("H2 proved nothing: the P14 control did not change the frame")

    # H3
    control(g, 2)
    ts = stand(g, "BEACH")
    g.shot("beach")
    g.check(names_ok(ts), f"H3: on Sandreach Beach1 the title names '{WANT}' (was 'Palmnell Island')", str(ts))

    # H4 -- title on the trigger, then Confirm must still enter the Lantern Hall
    control(g, 3)
    ts = stand(g, "QUAY")
    g.shot("quay")
    g.check(names_ok(ts), f"H4a: on Ashvale's trigger the title names '{WANT}' (was 'Gunitas Basin')", str(ts))
    entered = False
    for attempt in range(2):
        if attempt:                                   # fallback: step onto the trigger from its arrive point
            g.teleport(*PREP["QUAY_ARRIVE"]["world"])
            g.world_settle()
            face = g.world_face(180.0, home=tuple(PREP["QUAY_ARRIVE"]["world"]), tolerance=8.0)
            g.world_approach(180.0, 12.0, speed=face.get("speed"), burst_frames=8)
            g.world_settle()
        g.press("confirm")
        try:
            g.wait_for(lambda s: not s.on_world and s.field_id == LANTERN_HALL, timeout=20,
                       what="the Lantern Hall after Confirm on the quay")
            entered = True
            break
        except Exception as err:
            _RECORD["notes"].append(f"quay attempt {attempt}: {err!r} (ui {g.state.ui_state}, "
                                    f"field {g.state.field_id}, on_world {g.state.on_world})")
    g.wait_frames(60)
    g.shot("quay-after-confirm")
    _RECORD["quay_after"] = {"field": g.state.field_id, "on_world": g.state.on_world, "ui": g.state.ui_state}
    g.check(entered, f"H4b: Confirm on Ashvale's trigger still enters field {LANTERN_HALL} (the Lantern Hall)",
            json.dumps(_RECORD["quay_after"]))
    # H4c -- the first run's frame 60 frames after arrival was black, while the hall was still initialising. Wait for
    # the hall to hand back control, then the frame must not be black.
    if entered:
        try:
            g.wait_control(timeout=30)
            controlled = True
        except Exception as err:
            controlled = False
            _RECORD["notes"].append(f"no control in the hall: {err!r}")
        g.wait_frames(30)
        from PIL import Image, ImageStat
        lum = ImageStat.Stat(Image.open(g.shot("hall")).convert("L")).mean[0]
        _RECORD["hall"] = {"control": controlled, "mean_luma": round(lum, 1),
                           "player": [g.state.player_x, g.state.player_z]}
        g.check(controlled and lum > 8.0, "H4c: the Lantern Hall renders and grants control (not a black screen)",
                json.dumps(_RECORD["hall"]))
    try:
        (g.run_dir / "area_host_session.json").write_text(json.dumps(_RECORD, indent=1, default=str),
                                                          encoding="utf-8")
    except Exception as err:
        print(f"[area-host] could not write the record: {err}")
