"""The facing gate, in the game: engine patch s90's facing and in-place turn, and the walker's closed loop, at the
stock door that missed 10 of 10 times in rung-3 session 2 -- Dali's Village Road (350) to the Inn (351).

    PYTHONUNBUFFERED=1 py tools/play.py studies/story-trace/facing_check.py --label story-facing-check

THE PLACE. Stock 350's region 18 (to 351) runs its warp only while the player FACES the door: his facing byte
within 47/256 of a turn of the bearing to his projection onto the region's first edge (content.doorface; research
rung3-6). Arriving from 351 (entrance 2) stands him at (258, -58), 5u outside that region, facing byte 50 (70.3 deg)
-- back the way he came, away from the door. That is the rung-3 miss: a walk in of a frame or two left him inside,
unfaced, and the door stayed shut while the tour waited.

THE STORY STATE is the tour's own: New Game, then the game's scripted segment from the village entrance 359 at SC
2540 until control returns in 352 at SC 2600 (dali_tour.segment), then a warp into 350 by entrance 2 -- SC and every
story byte as the tour meets them. Each return to the arrival goes through the Inn (warp 351, then 350 by entrance 2),
which also resets his facing to the arrival's own byte 50: every step below starts from a known yaw.

THE BASIS IS THE FIELD'S OWN PREDICTION, CHECKED -- NOT PROBED. route_to calibrates a field's button->world basis on
its first walk there, with probes that avoid every OTHER exit -- not the one it is sent to, and a probe pressed toward
this door from this spot fired it in rung-3 session 3. Probing clear of every exit does not work here either: the
first run's left probe slid along the road's north wall ((-0.94, -0.34) against the predicted (-1.00, +0.02)) and the
calibration rightly refused it. So the basis is 350's TWIST prediction (Session.key_prior ->
content.movement.key_move_basis, exact on 351/352) seeded into the session, and FC-BASIS checks it where it matters:
a long in-place turn on a pad converges to the heading that prediction gives the pad.

THE WALK IN, AND WHY IT CANNOT FACE THE DOOR. From the arrival's byte 50 a walked press toward the door (the pad
most along the bearing) leaves a gate error of 83 / 56 / 40 units after 1 / 2 / 3 MovePC calls: one call (a 2-frame
walked hold, 30u, into the region by ~25u) or even two leaves the door shut; only a third would face it. A retry
first turns him fully away in place from a yaw BELOW the away pad's (so the turn never crosses the window) and then
presses once more. Should the walk in fire the door anyway, or never get him in, FC-SHUT is VOID -- the check never
started -- not a failure of the gate.

FC-CAP      the engine publishes the facing (s90: state.player.face)
FC-BYTE     the published byte is the kit's byte of the published yaw (content.doorface.facing_byte, +-0.001 deg)
FC-INPLACE  every turn_in_place at the arrival moved him <= 0.25u (a turn IN PLACE), ended normally, turned his yaw,
            and reported the byte state.json shows
FC-BASIS    a long turn on the toward pad and on the away pad converged within 0.5 deg of the heading the field's
            TWIST predicts for each (the basis every pad choice below rests on)
FC-LERP     the engine turns him 40% of the way per MovePC call, in WHOLE calls, two a 30 Hz tick at the run rate a
            turn uses: a short turn's remaining angle is 0.6**k of what it was, k an even whole number
FC-SHUT     the stock gate holds the door SHUT for a player standing in its region facing away: inside it (the
            engine's triangle ring AND the kit's zone) with his MEASURED byte outside the window, a turn away there
            ending normally, and 90 frames later still in 350, inside, with control -- the rung-3 miss, measured.
            It says the gate is what held the door only together with FC-FACE, at the same spot
FC-FACE     the walker's closed loop from where FC-SHUT left him: route_cross(gate=, region=) to the spot he stands
            on walks nothing, turns him in place, judges the door by the measured byte, and crosses to 351 (faced
            True, face_measured True, during "face", a turn that moved him <= 0.25u)
NC-THROW    nothing thrown through the event engine, the evaluator, the controller or the agent
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dali_tour as D  # noqa: E402
from dali_tour import T  # noqa: E402
from ff9mapkit.content import doorface, pathfind  # noqa: E402

try:
    from harness import HarnessError
except ImportError:
    from tools.harness import HarnessError  # noqa: E402

START, START_SC, BEAT = 359, 2540, 2600
ROAD, INN, FROM_INN = 350, 351, 2            # the Village Road, the Inn, the entrance that arrives from it
MOVED = 0.25                                  # the s90 contract's in-place noise ceiling (turn_end.moved)
TRIGGER_PAD = 60.0                            # beyond a published trigger's radius, for the calibration probes
WALK_TRIES = 3
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "HarnessAgent", "FieldMapActorController")

_tour = D.Tour(stock=T.stock_script_source(), tag="facing-check")
say = _tour.say


class Void(Exception):
    """A check that never started: what it would judge did not come about (not a verdict on the gate)."""


def _octagon(x: float, z: float, r: float) -> list:
    return [[x + r * math.cos(math.pi * k / 4), z + r * math.sin(math.pi * k / 4)] for k in range(8)]


def _objects(g, frames: int = 60):
    """The published objects, read until the agent lists them (a sample can say "unknown")."""
    for _ in range(max(1, frames // 4)):
        st = g.state
        if st.objects_status == "listed":
            return st.objects
        g.wait_frames(4)
    raise HarnessError(f"the agent never listed the field's objects (objects_status {g.state.objects_status!r})")


def _trigger_hazards(objs) -> list:
    """Every published trigger a probe or a turn could fire, as a polygon: a Range (range_r), and the talk search
    (talk_r) of an entry that has a Range too -- facing it inside talk_r requests that Range (s89's note)."""
    out = []
    for o in objs or ():
        if o.get("range") and o.get("range_r"):
            out.append(_octagon(float(o["x"]), float(o["z"]), float(o["range_r"]) + TRIGGER_PAD))
        if o.get("range") and o.get("talk") and o.get("talk_r"):
            out.append(_octagon(float(o["x"]), float(o["z"]), float(o["talk_r"]) + TRIGGER_PAD))
    return out


def _pad(basis: dict, u, *, toward: bool) -> str:
    """The one-key pad whose calibrated world direction is most along ``u`` (``toward``) or against it."""
    pads = {"up": basis["v"], "down": (-basis["v"][0], -basis["v"][1]),
            "right": basis["h"], "left": (-basis["h"][0], -basis["h"][1])}
    key = (lambda p: pads[p][0] * u[0] + pads[p][1] * u[1])
    return max(pads, key=key) if toward else min(pads, key=key)


def _door_pads(st, door, basis) -> dict:
    """The one-key pads most toward, and most against, the bearing from where he stands to his exit point."""
    exit_pt = doorface.calc_exit_position(st.player_x, st.player_z, door["zone"][0], door["zone"][1])
    d = (exit_pt[0] - st.player_x, exit_pt[1] - st.player_z)
    m = math.hypot(*d) or 1.0
    u = (d[0] / m, d[1] / m)
    return {"toward": _pad(basis, u, toward=True), "away": _pad(basis, u, toward=False), "exit": list(exit_pt)}


def _gate(st, door) -> dict:
    """Where he stands against the door, from the published position and facing byte."""
    q0, q1 = door["zone"][0], door["zone"][1]
    v = doorface.gate_value_from_face(st.player_x, st.player_z, st.player_face, q0, q1)
    return {"x": round(st.player_x, 1), "z": round(st.player_z, 1), "face": st.player_face, "yaw": st.player_yaw,
            "v": v, "err": doorface.signed_error(v), "faced": doorface.gate_faced(v, door["gate"]),
            "in_region": doorface.region_contains(st.player_x, st.player_z, door["region"]),
            "in_zone": pathfind.poly_gap(st.player_x, st.player_z, door["zone"]) < 0}


def _on_road(st) -> bool:
    """On the Village Road with control and a readable position and facing."""
    return (st.field_id == ROAD and st.control and st.player_x is not None and st.player_z is not None
            and st.player_face is not None and st.player_yaw is not None)


def _turn(g, pad: str, frames: int) -> dict:
    """turn_in_place, with the facing byte state.json shows once its report is in."""
    end = g.turn_in_place(pad, frames)
    end["state_face"] = g.state.player_face
    end["pad"] = pad
    say("turn", json.dumps(end))
    return end


def _arrive(g) -> None:
    """Into 350 by the Inn's door, through the Inn -- which also sets his facing to the arrival's own byte."""
    if g.state.field_id == ROAD:
        g.warp(INN)
    g.warp(ROAD, entrance=FROM_INN)
    g.settle()


def _walk_in(g, door, basis, notes) -> None:
    """Into the door's region, still facing away (THE WALK IN, the module docstring); Void if it fires the door or
    never gets him in."""
    tries = notes.setdefault("walk_in", [])
    for k in range(WALK_TRIES):
        st = g.state
        if not _on_road(st):
            raise Void(f"the walk in left the road before it got him in (field {st.field_id}, control {st.control})")
        here = _gate(st, door)
        if here["in_region"] and here["in_zone"]:
            return
        pads = _door_pads(st, door, basis)
        if k:                                                   # a retry: fully away first, from below its yaw
            _turn(g, pads["away"], 30)
            st = g.state
        start = (st.player_x, st.player_z, st.player_yaw)
        g.send("hold cancel 3", f"hold {pads['toward']} 2", "wait 8")
        st = g.settle()
        moved = math.hypot(st.player_x - start[0], st.player_z - start[1]) if st.player_x is not None else None
        tries.append({"from": start, "pad": pads["toward"], "moved": moved, "calls": moved and moved / 30.0,
                      "field": st.field_id, "control": st.control, "yaw": st.player_yaw, "face": st.player_face})
        say("walk in", json.dumps(tries[-1]))
        if st.field_id != ROAD or not st.control:
            raise Void(f"the walk in fired the door (try {k + 1}: {json.dumps(tries[-1])})")
    st = g.state
    if not (_on_road(st) and _gate(st, door)["in_region"] and _gate(st, door)["in_zone"]):
        raise Void(f"{WALK_TRIES} walked presses never stood him in both the region and the zone")


def run(g) -> None:
    mark = g.log_mark()
    log: list = []
    notes: dict = {}
    turns: list = []
    stop = "not reached"
    try:
        g.newgame()
        g.wait_frames(30)
        if not D.segment(g, log, start=START, sc=START_SC, beat=BEAT)["ok"]:
            stop = f"the segment did not hand control back in 352 at SC {BEAT}: {log[-1]}"
            raise HarnessError(stop)
        gates = _tour.gateways(ROAD)
        to, _entrance, zone = next(gw for gw in gates if gw[0] == INN)
        door = dict(_tour.door(ROAD, to, zone), zone=zone)
        regions = [_tour.door(ROAD, gw[0], gw[2])["region"] for gw in gates]
        notes["door"] = door
        if door.get("gate") != [48, 208]:
            stop = f"the kit does not read 350's door to 351 as facing-gated [48, 208]: {door.get('gate')}"
            raise HarnessError(stop)

        _arrive(g)
        st = g.state
        notes["arrival"] = {"x": st.player_x, "z": st.player_z, "yaw": st.player_yaw, "face": st.player_face,
                            "facing_status": st.facing_status}
        say("arrival", json.dumps(notes["arrival"]))
        if not g.check(st.facing_status == "known" and _on_road(st),
                       "FC-CAP: the engine publishes the facing (s90)", json.dumps(notes["arrival"])):
            stop = "the engine does not publish the facing (s90)"
            return
        near_bytes = {doorface.facing_byte(st.player_yaw + d) for d in (-0.001, 0.0, 0.001)}
        g.check(st.player_face in near_bytes, "FC-BYTE: the published byte is the kit's byte of the published yaw",
                f"face {st.player_face}, yaw {st.player_yaw}, kit {sorted(near_bytes)}")

        hazards = [gw[2] for gw in gates] + regions + _trigger_hazards(_objects(g))
        basis = g.key_prior(ROAD)
        if not basis:
            stop = "no movement prior for 350 (its TWIST is unreadable)"
            raise HarnessError(stop)
        g._axes[ROAD] = basis                                    # THE BASIS IS THE PREDICTION, CHECKED (FC-BASIS)
        notes["basis"] = basis

        # THE TURNS, at the arrival: 121u off every wall, outside every region -- toward the door (converged), a
        # short turn away (the per-call measurement; a longer one if no tick fell inside it), away (converged)
        _arrive(g)
        st = g.state
        spots = hazards[len(gates):]                             # the regions and the trigger discs
        if not _on_road(st) or any(doorface.region_contains(st.player_x, st.player_z, r) for r in spots):
            stop = f"the arrival is not a safe place to turn: {json.dumps(_gate(st, door) if _on_road(st) else {})}"
            raise HarnessError(stop)
        pads = _door_pads(st, door, basis)
        notes["turns_at"] = dict(_gate(st, door), pads=pads)
        say("the turns at", json.dumps(notes["turns_at"]))
        near, far = pads["toward"], pads["away"]
        turns.append(_turn(g, near, 30))
        short = _turn(g, far, 3)
        if short["yaw"] is not None and short["yaw0"] is not None and doorface.angle_off(short["yaw0"], short["yaw"]) < 1e-3:
            turns.append(short)                                  # no tick fell inside it: once more, longer
            short = _turn(g, far, 5)
        turns.append(short)
        turns.append(_turn(g, far, 30))
        ok_inplace = all(t["why"] == "ended" and t["moved"] is not None and t["moved"] <= MOVED
                         and t["face"] == t["state_face"] for t in turns)
        ok_inplace = ok_inplace and all(t["yaw0"] is not None and t["yaw"] is not None
                                        and doorface.angle_off(t["yaw0"], t["yaw"]) > 1.0
                                        for t in (turns[0], short, turns[-1]))
        g.check(ok_inplace, "FC-INPLACE: every turn turned him in place and reported the byte state.json shows",
                json.dumps(turns))
        heads = {"up": basis["v"], "down": (-basis["v"][0], -basis["v"][1]),
                 "right": basis["h"], "left": (-basis["h"][0], -basis["h"][1])}
        want = {p: doorface.yaw_of(*heads[p]) for p in (near, far)}
        got = {near: turns[0]["yaw"], far: turns[-1]["yaw"]}
        notes["basis_check"] = {"want": want, "got": got}
        g.check(all(got[p] is not None and doorface.angle_off(got[p], want[p]) < 0.5 for p in want),
                "FC-BASIS: a long turn on each pad converged to the heading the field's TWIST predicts for it",
                json.dumps(notes["basis_check"]))
        y_far = turns[-1]["yaw"]
        k = None
        if None not in (short["yaw0"], short["yaw"], y_far):
            before, after = doorface.angle_off(short["yaw0"], y_far), doorface.angle_off(short["yaw"], y_far)
            k = math.log(after / before) / math.log(0.6) if before > 1.0 and after > 1e-3 else None
            notes["lerp"] = {"off_before": before, "off_after": after, "calls": k, "frames": short["frames"]}
        g.check(k is not None and abs(k - round(k)) < 0.1 and round(k) >= 2 and round(k) % 2 == 0,
                "FC-LERP: a short turn left 0.6**k of the angle, k an even whole number of MovePC calls",
                json.dumps(notes.get("lerp")))

        # INTO THE REGION FACING AWAY, from the arrival's own facing (THE WALK IN)
        _arrive(g)
        try:
            _walk_in(g, door, basis, notes)
        except Void as why:
            g.check(False, "VOID FC-SHUT / FC-FACE: the setup never stood him in the region facing away", str(why))
            stop = f"VOID: {why}"
            return
        st = g.state
        notes["away_inside"] = _turn(g, _door_pads(st, door, basis)["away"], 30)
        st = g.settle()
        notes["inside"] = _gate(st, door) if _on_road(st) else {"field": st.field_id, "control": st.control}
        say("inside", json.dumps(notes["inside"]))
        g.wait_frames(90)
        st = g.state
        inside = notes["inside"]
        after = _gate(st, door) if _on_road(st) else {}
        shut = (_on_road(st) and inside.get("in_region") and inside.get("in_zone") and inside.get("faced") is False
                and notes["away_inside"].get("why") == "ended" and after.get("in_region") and after.get("in_zone")
                and after.get("face") == inside.get("face"))
        g.check(bool(shut), "FC-SHUT: standing in the 351 door's region facing away (measured), the door stays "
                "shut", json.dumps(dict(inside, after=after, field_after=st.field_id, control_after=st.control,
                                        turn=notes["away_inside"])))
        if not shut:
            stop = "FC-SHUT did not hold -- the closed loop has no unfaced start to prove itself from"
            return

        rec = g.route_cross(st.player_x, st.player_z, zone=zone, gate=door["gate"], region=door["region"],
                            avoid=_tour.avoid_for(ROAD, zone), margin=D.MARGIN, timeout=D.CROSS_TIMEOUT,
                            walkmesh=_tour.floor(ROAD), prior=g.key_prior(ROAD), unstick=True, smooth=True,
                            npcs=True)
        keep = ("landed", "during", "reached", "inside", "travelled", "faced", "face_measured", "face_err",
                "face_worst", "face_to", "face_calls", "face_pad", "face_moved", "face_gate")
        notes["cross"] = {k2: rec.get(k2) for k2 in keep}
        say("cross", json.dumps(notes["cross"]))
        g.check(rec.get("landed") == INN and rec.get("faced") is True and rec.get("face_measured") is True
                and rec.get("during") == "face" and rec.get("face_pad") is not None
                and rec.get("face_moved") is not None and rec["face_moved"] <= MOVED
                and (rec.get("travelled") or 0.0) <= 5.0,
                "FC-FACE: the walker's closed loop turned him in place to face the door, and it crossed to 351",
                json.dumps(notes["cross"]))
        stop = "done"
    except Exception as err:                                     # noqa: BLE001 -- every stop is reported as one
        stop = stop if stop != "not reached" else f"STOPPED: {type(err).__name__}: {str(err)[:300]}"
        g.check(False, "FC-RAN: the check ran to its end", stop)
    finally:
        (g.run_dir / "facing_check.json").write_text(
            json.dumps({"stop": stop, "notes": notes, "turns": turns, "log": log}, indent=1, default=str),
            encoding="utf-8")
        every = g.exceptions_since(mark)
        ours = [e for e in every if e.name in THROWS and (not e.trace or any(w in fr for fr in e.trace for w in WHERE))]
        g.check(not ours, "NC-THROW: nothing thrown through the event engine, the evaluator, the controller or the "
                "agent", str([(e.name, e.where) for e in ours[:5]]))
