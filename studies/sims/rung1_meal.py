"""THE FIRST MEAL, driven live -- sims-arc rung 1's five-point playtest checklist (studies/sims/PLAN.md),
run by the in-game harness instead of a human.

    py studies/sims/sims_bench.py deploy          # bench 30430 (first deploy of the id = a fresh launch)
    py tools/play.py studies/sims/rung1_meal.py   # this

What a harness CAN settle here is the mechanism: does the number move, does the Sim go, does the order
retire itself, does the menu hide the row, does a re-entry reseed. Whether it is FUN -- pacing, framing,
whether Bilba reads as a person -- is still the owner's call; the frames this run saves are for that.

Reads, all from published state (never frame counts): hunger = the rendered HUD strip ("HUNGER nn") in
``dialog.texts``; Bilba = the s89 ``objects`` entry nearest her home at entry, then followed by uid; the
order = gEventGlobal bit 14867 (the bench's public flag, watched). The pot menu is driven with plain
presses -- the HUD strip is itself an open window, so ``interact``/``advance`` (which refuse or page
under any open box) do not fit a field that always has one up.
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sims_bench as B                                   # noqa: E402  (the bench's own constants)

FID = B.FIELD_ID
ORDER_FLAG = 14867                                       # printed by the build: order -> flag 14867
COOK_ROW = "Bilba, cook something."
NEVER_ROW = "Never mind."
# Where the steward stands to order: inside POT_ZONE (x 420..780, z -860..-300), >=186u from both the pot
# and Bilba's cooking spot, east of her approach line -- a walker into a STANDING player is held there.
ORDER_SPOT = (740, -575)
SENTINEL = 999                                           # digits = 3: the HUD shows this before its first value
LOG = []                                                 # the timeline: one row per sample


def _hunger(st) -> int | None:
    for t in st.texts:
        m = re.search(r"HUNGER\s+(-?\d+)", t)
        if m and int(m.group(1)) != SENTINEL:          # the strip's width sentinel until the first live write
            return int(m.group(1))
    return None


def _obj(st, uid):
    for o in st.objects or ():
        if o.get("uid") == uid:
            return o
    return None


def _d(ax, az, bx, bz) -> float:
    return math.hypot(ax - bx, az - bz)


def _sample(g, uid, tag: str) -> dict:
    st = g.state
    o = _obj(st, uid)
    row = {"t": round(time.monotonic() - T0, 2), "tag": tag, "frame": st.frame, "field": st.field_id,
           "hunger": _hunger(st), "flag": st.flag(ORDER_FLAG),
           "bx": o and round(o["x"]), "bz": o and round(o["z"]),
           "px": st.player_x and round(st.player_x), "pz": st.player_z and round(st.player_z),
           "choice": bool(st.choice), "control": st.control}
    LOG.append(row)
    return row


def _watch_for(g, uid, until, *, seconds: float, tag: str, every: float = 0.25) -> dict | None:
    """Sample until ``until(row)`` or the time runs out; returns the first row that satisfied it."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        row = _sample(g, uid, tag)
        if until(row):
            return row
        time.sleep(every)
    return None


def _open_menu(g, *, tries: int = 3):
    """Confirm at the pot until its menu is up (the first press can be eaten by a fade/turn)."""
    for _ in range(tries):
        g.press("confirm", 4)
        try:
            return g.wait_for(lambda s: s.choice is not None, timeout=3.0, what="the pot's menu")
        except Exception:                                # noqa: BLE001 - retried, then reported
            continue
    return None


def _pick(g, row: str) -> bool:
    """Answer the menu with ``row`` and VERIFY the game took it. A blind choose() lost the second order in
    run 1: the first Confirm into a freshly opened window is often dropped (the harness's O4 law).
    choose_landed waits for the READY window itself (group Dialog.Choice) -- run 3 caught it scoring a Confirm
    dropped in the OPENING as landed (frames 2128-2136); the cook pick is still re-proven by the flag it sets."""
    got = g.choose_landed(g.option_index(row))
    print(f"[sims] pick {row!r}: {got.get('landed')} after {got.get('confirms')} confirm(s) {got.get('why') or ''}")
    return bool(got.get("landed"))


def _close_reply(g, needle: str) -> bool:
    """Page out a one-page reply WITHOUT a stray Confirm reopening the menu (the zone is instant)."""
    try:
        g.wait_for(lambda s: needle in s.text, timeout=4.0, what=f"the reply {needle!r}")
    except Exception:                                    # noqa: BLE001
        return False
    for _ in range(4):
        g.press("confirm", 3)
        try:
            g.wait_for(lambda s: needle not in s.text, timeout=1.5, what="the reply to close")
            return True
        except Exception:                                # noqa: BLE001
            continue
    return False


def run(g) -> None:
    global T0
    T0 = time.monotonic()
    mark = g.log_mark()
    import collections
    g._ring._buf = collections.deque(g._ring._buf, maxlen=6000)   # the whole run, not the last ~10 s
    g.newgame()
    g.warp(FID)
    g.watch(ORDER_FLAG)
    g.wait_frames(20)
    st = g.wait_for(lambda s: _hunger(s) is not None and s.objects_status == "listed", timeout=10,
                    what="the HUNGER strip and the object list")

    # ---- 0. the room as built: the steward at spawn, Bilba at home --------------------------------
    px, pz = st.player_x, st.player_z
    g.check(_d(px, pz, *B.PLAYER_SPAWN) < 80, "R1.0: the steward spawns at the bench's spawn (frame check)",
            f"({px:.0f},{pz:.0f}) vs {B.PLAYER_SPAWN}")
    objs = sorted(st.objects, key=lambda o: _d(o["x"], o["z"], *B.HOME))
    print("[sims] objects at entry:", [(o.get("uid"), o.get("sid"), round(o["x"]), round(o["z"])) for o in st.objects])
    bilba = objs[0] if objs and _d(objs[0]["x"], objs[0]["z"], *B.HOME) < 400 else None
    if not g.check(bilba is not None, "R1.0: an actor stands at Bilba's home corner", str(objs[:2])):
        return
    uid = bilba["uid"]
    g.shot("1-room")

    # ---- 1. THE ROOM: hunger ticks down ~1 / 1.5 s; Bilba ambles near home -------------------------
    a = _sample(g, uid, "decay")
    _watch_for(g, uid, lambda r: False, seconds=12, tag="decay", every=0.5)
    b = LOG[-1]
    g.check(a["hunger"] is not None and 74 <= a["hunger"] <= 80, "R1.1: hunger boots at its seed (80, minus entry drift)",
            str(a["hunger"]))
    rate = (a["hunger"] - b["hunger"]) / max(b["t"] - a["t"], 0.1)
    g.check(0.45 <= rate <= 0.95, "R1.1: hunger DECAYS at ~1 point / 1.5 s (0.67/s) with nobody directing",
            f"{a['hunger']}->{b['hunger']} over {b['t'] - a['t']:.1f}s = {rate:.2f}/s")
    rows = [r for r in LOG if r["tag"] == "decay" and r["bx"] is not None]
    far = max(_d(r["bx"], r["bz"], *B.HOME) for r in rows)
    span = max(_d(r["bx"], r["bz"], rows[0]["bx"], rows[0]["bz"]) for r in rows)
    g.check(far <= 350, "R1.1: unordered, Bilba stays in her wander box (radius 220 round home)", f"max {far:.0f}u from home")
    g.check(span >= 30, "R1.1: ...and actually ambles (moved off her first spot)", f"max {span:.0f}u")
    g.check(not b["flag"], "R1.1: no order is pending at boot", str(b["flag"]))

    # ---- 2. THE ORDER: the steward walks to the pot and directs -----------------------------------
    g.calibrate_axes()
    g.walk_to(*ORDER_SPOT, tolerance=30, strict=False)
    st = g.state
    g.check(420 < st.player_x < 780 and -860 < st.player_z < -300, "R1.2: the steward stands inside the pot's zone",
            f"({st.player_x:.0f},{st.player_z:.0f})")
    g.shot("2-at-the-pot")
    st = _open_menu(g)
    if not g.check(st is not None, "R1.2: Confirm at the pot opens its menu", g.state.text[-120:]):
        return
    opts = g.options()
    print("[sims] menu (fresh):", g.prompt(), opts)
    g.check(COOK_ROW in opts and NEVER_ROW in opts, "R1.2: the menu offers the cook row and Never mind", str(opts))
    g.shot("3-menu")
    g.check(_pick(g, COOK_ROW), "R1.2: the cook order lands (choose_landed)")
    t_order = _sample(g, uid, "ordered")["t"]
    g.check(_close_reply(g, "shuffles"), "R1.2: the reply 'Bilba shuffles toward the pot.' shows and pages out",
            g.state.text[-120:])
    # the [[choice]] raises its flag AFTER the reply page closes (run 4: reply out 1747, flag 1751), not at the pick
    g.check(_watch_for(g, uid, lambda r: r["flag"] in (True, 1), seconds=2, tag="ordered") is not None,
            "R1.2: ...and the game took it: the order flag 14867 is raised once the reply closes")

    # ---- 4a. RE-ORDER while one is pending: the cook row is HIDDEN --------------------------------
    st = _open_menu(g)
    if g.check(st is not None, "R1.4: Confirm again (order pending) opens the menu", g.state.text[-120:]):
        opts_busy = g.options()
        print("[sims] menu (order pending):", opts_busy, st.choice)
        g.check(COOK_ROW not in opts_busy and NEVER_ROW in opts_busy,
                "R1.4: while an order is pending the cook row is hidden -- 'Never mind' only", str(opts_busy))
        _pick(g, NEVER_ROW)
        g.wait_frames(20)

    # ---- 2/3. Bilba walks over, cooks to 95+, ambles home, the order retires -----------------------
    at_pot = _watch_for(g, uid, lambda r: r["bx"] is not None and _d(r["bx"], r["bz"], *B.POT_SPOT) <= 160,
                        seconds=15, tag="to-pot")
    g.check(at_pot is not None, "R1.2: ordered, Bilba walks to the pot (within 160u of her cooking spot)",
            f"after {at_pot['t'] - t_order:.1f}s" if at_pot else str(LOG[-1]))
    if at_pot:
        g.shot("4-cooking")
    h_at = at_pot["hunger"] if at_pot else None
    full = _watch_for(g, uid, lambda r: (r["hunger"] or 0) >= B.FULL_AT, seconds=25, tag="cooking")
    g.check(full is not None, f"R1.3: at the pot hunger climbs to {B.FULL_AT}+",
            f"{h_at} -> {full['hunger']} in {full['t'] - at_pot['t']:.1f}s" if full and at_pot else str(LOG[-1]))
    cleared = _watch_for(g, uid, lambda r: r["flag"] is False or r["flag"] == 0, seconds=10, tag="retire")
    g.check(cleared is not None, "R1.3: full, the order retires itself (flag 14867 clears)", str(LOG[-1]))
    home = _watch_for(g, uid, lambda r: r["bx"] is not None and _d(r["bx"], r["bz"], *B.HOME) <= 150,
                      seconds=20, tag="home")
    g.check(home is not None, "R1.3: ...and Bilba ambles home on her own",
            f"{home['t'] - (cleared or home)['t']:.1f}s after the clear" if home else str(LOG[-1]))
    if home:
        g.shot("5-home")
    peak = max((r["hunger"] or 0) for r in LOG)
    g.check(peak <= 100, "R1.3: the clamp holds (hunger never reads above 100)", f"peak {peak}")

    # ---- 4b. after the meal the cook row is back ---------------------------------------------------
    st = _open_menu(g)
    if g.check(st is not None, "R1.4: after the meal Confirm opens the menu again", g.state.text[-120:]):
        opts_after = g.options()
        g.check(COOK_ROW in opts_after, "R1.4: ...and the cook row is back", str(opts_after))
        # order again, then RE-ENTER mid-order: step 5 must clear what the cooking was doing
        _pick(g, COOK_ROW)
        _close_reply(g, "shuffles")
        _watch_for(g, uid, lambda r: r["flag"] in (True, 1), seconds=2, tag="reorder")

    # ---- 5. re-entry (the warp the ~ menu's Reload stands in for) reseeds the day -----------------
    pre = _sample(g, uid, "pre-reload")
    g.check(pre["flag"] in (True, 1), "R1.5 setup: an order is pending going into the re-entry", str(pre))
    g.warp(FID)
    g.watch(ORDER_FLAG)
    g.wait_frames(20)
    st = g.wait_for(lambda s: _hunger(s) is not None and s.objects_status == "listed", timeout=10,
                    what="the strip after re-entry")
    objs = sorted(st.objects, key=lambda o: _d(o["x"], o["z"], *B.HOME))
    post = _sample(g, objs[0]["uid"] if objs else None, "reloaded")
    g.check(post["hunger"] is not None and 76 <= post["hunger"] <= 80, "R1.5: re-entry reseeds hunger to 80",
            str(post["hunger"]))
    g.check(post["bx"] is not None and _d(post["bx"], post["bz"], *B.HOME) <= 150, "R1.5: Bilba is back home",
            str(post))
    g.check(post["flag"] in (False, 0), "R1.5: the pending order is clear after re-entry", str(post["flag"]))
    g.shot("6-reloaded")

    exc = g.exceptions_since(mark)
    g.check(not exc, "R1: no exception in Memoria.log or output_log over the run", "; ".join(e.name for e in exc[:5]))

    out = Path(g.run_dir) / "sims-timeline.jsonl" if getattr(g, "run_dir", None) else HERE / "bench" / "timeline.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in LOG) + "\n", encoding="utf-8")
    print(f"[sims] timeline -> {out} ({len(LOG)} rows)")


T0 = 0.0
