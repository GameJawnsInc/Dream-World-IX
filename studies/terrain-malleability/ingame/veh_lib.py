"""Shared harness helpers for the vehicle sessions (veh_session1-4). Imported by the scenarios; never run alone.

THE ROUTE (no DLL, no ~ menu; evidence in veh_PLAN.md section 2 and out/veh_prep.json "route"):
  vehicle IDENTITY binds at WORLD LOAD from gEventGlobal[190]. Each free-roam dispatcher's vehicle actor Init runs
  `if Global.Byte[190] == mode: AttachObject(anchor, self, bone); DefinePlayerCharacter(); EnableMove()` and places
  itself from its own gEventGlobal record (boat/airships Int24[74] Int16[77] Int24[79] Byte[82]; chocobo [83..91]).
  So: warp to field 6603 with the ScenarioCounter that makes its exit cascade load the wanted dispatcher (key 35:
  <5990 -> 9011, 5990-10399 -> 9003, 10400-11089 -> 9007, >=11090 -> 9008), poke [190] (+[191]) and the record,
  walk out the door. The same load-time binding a save loaded on a vehicle or a bridge-interior exit uses.

Input, all through hooked accessors (veh_PLAN.md section 3): on foot / chocobo (type 0) exactly the rimwalk verbs;
boat (type 2) "up" = forward (LY, ff9.cs:6205-6206), left/right turn the hull (LX, :6204/:6214); airship (type 1)
"confirm" = forward throttle (w_moveGetPadStateR falls to UIManager.Input.GetKey(Confirm) when the raw right stick
is idle, ff9.cs:6665-6672 -> UIKeyTrigger.cs:104 HonoInputManager.IsInput), "special" = reverse, up/down = dive/climb
(LY x InvertedFlightY, ff9.cs:6278/:6310 -- "down" climbs on this install, calibrated per session), Cancel = land
(the world .eb's KEYON 0x10000 arm, EventInput.cs:288-290 -> 484-485).
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
LANDING = (68.0, -444.0)
CEILING = 42.1875


def prep() -> dict:
    return json.loads((HERE / "out" / "veh_prep.json").read_text(encoding="utf-8"))


def build() -> dict:
    return json.loads((HERE / "out" / "veh_build.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------- gEventGlobal bytes
def watch_bytes(g, idxs) -> None:
    bits = []
    for i in idxs:
        bits.extend(range(8 * int(i), 8 * int(i) + 8))
    g.watch(*bits)


def read_byte(st, idx):
    v = 0
    for k in range(8):
        b = st.flag(8 * int(idx) + k)
        if b is None:
            return None
        v |= (1 if b else 0) << k
    return v


def read_bytes(st, idxs) -> dict:
    return {str(i): read_byte(st, i) for i in idxs}


# ------------------------------------------------------------------------------------------- reaching the world
def here(g) -> dict:
    st = g.state
    return {"x": st.world_x, "z": st.world_z, "y": st.world_y, "world": st.world_id, "vehicle": st.vehicle,
            "ui": st.ui_state, "scenario": st.scenario, "control": st.control, "frame": st.frame}


def reach_world_as(g, rec: dict, *, scenario: int, pokes: dict, flags=(), expect_world: int, first: bool):
    """newgame (first) or a world->6603 round trip, set the story state in the FIELD, walk out of the door.

    `pokes` = {byte index: value}; `flags` = bits to set. Everything written is read back from the published state
    BEFORE the door (watched bits), so a refused poke cannot masquerade as a vehicle that failed to bind."""
    if first:
        g.newgame()
        g.warp(LANDING_FIELD, scenario=scenario)
    else:
        g.world_warp(LANDING_FIELD, scenario=scenario)
    g.wait_frames(45)
    for b in flags:
        g.flag(int(b), True)
    for i, v in pokes.items():
        g.poke(int(i), int(v))
    idxs = sorted({int(i) for i in pokes} | {1062, 1063})
    watch_bytes(g, idxs)
    if flags:
        g.watch(*[int(b) for b in flags])
    g.wait_frames(6)
    st = g.state
    back = read_bytes(st, idxs)
    rec["field_readback"] = {"scenario": st.scenario, "bytes": back,
                             "flags": {str(b): st.flag(int(b)) for b in flags}}
    ok = (st.scenario == scenario and all(back.get(str(int(i))) == int(v) for i, v in pokes.items())
          and all(st.flag(int(b)) for b in flags))
    g.check(ok, f"pre-door: scenario {scenario} and every poked byte read back in field 6603",
            json.dumps(rec["field_readback"]))
    if not ok:
        # [review] DO NOT WALK OUT ON A STATE THAT DID NOT LAND. The dispatchers' vehicle arms dereference the vehicle
        # actor (obj(uid=6)/obj(uid=5), e.g. WORLD07 entry 12 func 1 case 8, PretendToBe(6)); a [190] whose actor the
        # ScenarioCounter / [191] gate did not spawn is the ~ menu's "forced mode crashes the event script" state. A
        # failed read-back is the finding -- stop here, in the field, where the run is still recoverable.
        err = getattr(sys.modules.get(type(g).__module__), "HarnessError", RuntimeError)   # play.py reports it cleanly
        raise err(f"veh: pre-door read-back failed, refusing to load the world: {rec['field_readback']}")
    if back.get("1062") or back.get("1063"):
        rec.setdefault("notes", []).append(f"Global.Int16[1062] nonzero ({back.get('1062')},{back.get('1063')}): "
                                           f"6603 calls WorldMap(that) before its cascade")
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.unwatch()
    settle3(g)
    rec["arrival"] = here(g)
    return g.state


# ------------------------------------------------------------------------------------------- settling and reading
def settle3(g, *, still_s: float = 0.6, eps: float = 0.006, timeout: float = 10.0) -> dict:
    """Wait until world x, z AND y are unchanged for `still_s` of the game's clock -- a vehicle coasts (XZAlpha and
    YAlpha decay 1/8 a tick, ff9.cs:6236/:6311/:6314), so x/z-only stillness (world_settle) can read mid-glide."""
    t_end = time.time() + timeout
    last = None
    since = None
    while time.time() < t_end:
        st = g.state
        if not st.on_world or st.world_x is None:
            return here(g)
        cur = (st.world_x, st.world_z, st.world_y if st.world_y is not None else 0.0)
        now = time.time()
        if last is not None and all(abs(a - b) <= eps for a, b in zip(cur, last)):
            if since is None:
                since = now
            elif now - since >= still_s:
                return here(g)
        else:
            since = None
        last = cur
        time.sleep(0.03)
    return here(g)


def tp(g, x: float, z: float) -> dict:
    """Teleport the CONTROLLED actor (the vehicle when one is bound -- Ff9mkDebugMenu.WorldTeleportTo moves
    EventEngine.GetControlChar(), :1830-1845) after the vehicle has come to rest, then settle."""
    settle3(g)
    g.teleport(x, z)
    return settle3(g)


# ------------------------------------------------------------------------------------------- holding
def hold_until(g, buttons, *, measure, done=None, stall_s: float = 0.9, start_s: float = 2.5,
               max_s: float = 12.0, min_gain: float = 0.05):
    """Hold `buttons` (non-blocking, one request) and poll: stop when done(st) is true, or when measure(st) has not
    grown by `min_gain` for `stall_s` seconds after it first moved (or never moved within `start_s`). Releases every
    button. Returns {"outcome", "samples": [...]} -- the samples are the evidence."""
    frames = int(max_s * 70) + 30
    g.send(*[f"hold {b} {frames}" for b in buttons], wait=False)
    t0 = time.time()
    samples = []
    best = None
    best_t = t0
    moved = False
    outcome = "max"
    while time.time() - t0 < max_s:
        st = g.state
        if not st.on_world or st.world_x is None:
            outcome = "left_world"
            break
        m = measure(st)
        samples.append({"t": round(time.time() - t0, 3), "x": st.world_x, "z": st.world_z, "y": st.world_y,
                        "m": None if m is None else round(m, 4), "vehicle": st.vehicle, "frame": st.frame})
        if done is not None and done(st):
            outcome = "done"
            break
        if m is not None and (best is None or m > best + min_gain):
            if best is not None:
                moved = True
            best, best_t = m, time.time()
        if moved and time.time() - best_t > stall_s:
            outcome = "stalled"
            break
        if not moved and time.time() - t0 > start_s:
            outcome = "never_moved"
            break
        time.sleep(0.04)
    for b in buttons:
        try:
            g.release(b)
        except Exception:                                  # noqa: BLE001 -- a release must never mask the finding
            pass
    return {"outcome": outcome, "samples": samples, "best": best}


def plateau_y(g, button: str, *, max_s: float = 8.0) -> dict:
    """Hold `button` (climb or dive) until the published y stops changing; returns the plateau and the trace."""
    st0 = g.state
    y0 = st0.world_y
    r = hold_until(g, [button], measure=lambda s: None if s.world_y is None else abs(s.world_y - y0),
                   stall_s=0.7, start_s=2.0, max_s=max_s, min_gain=0.004)
    s = settle3(g)
    r["y_start"], r["y_end"] = y0, s["y"]
    return r


def calibrate_climb(g, rec: dict) -> str | None:
    """Which of up/down CLIMBS (InvertedFlightY flips it; Memoria.ini [AnalogControl] InvertedFlightY = 1 here, so
    'down' is predicted, ff9.cs:6278). Returns the button or None (vertical input not reaching the airship)."""
    out = {}
    for b in ("down", "up"):
        s0 = settle3(g)
        g.hold(b, 14)
        g.wait_frames(18)
        s1 = settle3(g)
        out[b] = None if None in (s0["y"], s1["y"]) else round(s1["y"] - s0["y"], 4)
    rec["climb_calibration"] = out
    if (out.get("down") or 0) > 0.3:
        return "down"
    if (out.get("up") or 0) > 0.3:
        return "up"
    return None


def radial(cx: float, cz: float):
    return lambda s: None if s.world_x is None else math.hypot(s.world_x - cx, s.world_z - cz)


def along(x0: float, z0: float, bearing: float):
    u = (math.cos(math.radians(bearing)), math.sin(math.radians(bearing)))
    return lambda s: None if s.world_x is None else (s.world_x - x0) * u[0] + (s.world_z - z0) * u[1]


def heading_of(a: dict, b: dict):
    dx, dz = b["x"] - a["x"], b["z"] - a["z"]
    if math.hypot(dx, dz) < 0.5:
        return None
    return math.degrees(math.atan2(dz, dx)) % 360.0


def angdiff(a: float, b: float) -> float:
    d = (a - b) % 360.0
    return d - 360.0 if d > 180.0 else d


DEFLECT_U = 0.5                           # a lateral offset this large off the straight run = the hull was slid


def first_deflection(points, x0: float, z0: float, heading_deg: float, x_border: float, min_lat: float = DEFLECT_U):
    """First point whose offset from the straight line (x0, z0) + t*(cos h, sin h) reaches `min_lat`: where the hull was
    first slid (w_movementControl's 7 slide angles each side, ff9.cs:5552-5603). Returns {"into": x - x_border, "lat"}
    or None. `points` are dicts with x/z: simulator trace rows (veh_prep.heading_scan) or hold_until samples (the
    session judges with the measured hull heading, so a +-2 deg hull does not read as a deflection)."""
    sh, ch = math.sin(math.radians(heading_deg)), math.cos(math.radians(heading_deg))
    for p in points:
        if p.get("x") is None or p.get("z") is None:
            continue
        lat = -(p["x"] - x0) * sh + (p["z"] - z0) * ch
        if abs(lat) >= min_lat:
            return {"into": round(p["x"] - x_border, 2), "lat": round(lat, 2)}
    return None


def hull_heading(g, start, *, button: str = "up", frames: int = 14):
    """Bearing a boat/airship hull actually moves along: from rest at `start`, a short forward burst."""
    s0 = tp(g, *start)
    g.hold(button, frames)
    g.wait_frames(frames + 2)
    s1 = settle3(g)
    return heading_of(s0, s1), s0, s1


def hull_steer(g, start, target: float, rec: dict, *, button: str = "up", tol: float = 2.0, rounds: int = 6):
    """Closed-loop hull turn (boat: LX turns the hull in place, ff9.cs:6204/:6214/:6241-6244 -- the camera bumpers
    do NOT steer a hull). The signed deg-per-frame rate of 'left' is learned from the first correction."""
    rate = None                                            # bearing change per frame of 'left' held
    hist = []
    hd, _a, _b = hull_heading(g, start, button=button)
    for _ in range(rounds):
        if hd is None:
            break
        err = angdiff(target, hd)
        hist.append({"heading": round(hd, 2), "error": round(err, 2)})
        if abs(err) <= tol:
            rec["hull_steer"] = {"rounds": hist, "rate": rate}
            return hd
        k = rate if rate else 2.0
        n = max(1, min(60, int(round(abs(err / k)))))
        btn = "left" if (err / k) > 0 else "right"
        tp(g, *start)
        g.hold(btn, n)
        g.wait_frames(n + 2)
        prev = hd
        hd, _a, _b = hull_heading(g, start, button=button)
        if hd is not None and prev is not None:
            turned = angdiff(hd, prev)
            if abs(turned) > 0.5:
                rate = turned / (n if btn == "left" else -n)
        hist[-1]["held"] = f"{btn} {n}"
    rec["hull_steer"] = {"rounds": hist, "rate": rate}
    return hd


def save(g, name: str, rec: dict) -> None:
    try:
        (g.run_dir / name).write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    except Exception as err:                               # noqa: BLE001
        print(f"[veh] could not write {name}: {err}")
