"""THE HOUSEHOLD DAY, driven live -- sims-arc rung 2 (studies/sims/PLAN.md), run by the in-game harness.

    py studies/sims/sims_bench2.py deploy       # bench 30431
    py tools/play.py studies/sims/rung2_day.py  # this

Phase A, THE UNDIRECTED DAY: nobody orders anything for one in-game day and then some (~150 s at 5 s an
hour). Asserted from published state: the clock HUD and the alternator agree; every need decays; her own urges
start tasks; each task she starts takes her to its object, fills the meter to FULL_AT and retires; she turns
in at night; nothing reaches 0; and she is never idle for long while a need sits under the urge line.

Phase B, THE QUEUE: the steward orders two needs at their objects, back to back. Asserted: the second
menu hides its order row only while ITS task pends; both tasks complete; and they run one at a time (she
finishes what she is at before starting the next).

Reads: the two HUD strips (rendered text, sentinels skipped), the six watched bits (5 task flags + `night`,
indices parsed from the build's own report), Bilba by her s89 uid. Menus are answered only once the
window reads Dialog.Choice (rung 1's opening-window lesson), and every order is re-proven by its flag.
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

import sims_bench2 as B                                  # noqa: E402

FID = B.FIELD_ID
NAMES = B.NAMES
LABEL = {"hunger": "HUN", "thirst": "THR", "energy": "NRG", "hygiene": "HYG", "fun": "FUN"}
SPOT = {n[0]: n[3] for n in B.NEEDS}
ZONE = {n[0]: n[4] for n in B.NEEDS}
LOG: list[dict] = []
T0 = 0.0


def _flags_from_report() -> dict:
    text = B.REPORT.read_text(encoding="utf-8")
    got = {m.group(2): int(m.group(1)) for m in re.finditer(r"^\s*flag\s+(\d+)\s+(\S+)\s*$", text, re.M)}
    return {**{n: got[f"t_{n}"] for n in NAMES}, "night": got["night"]}


FLAG = _flags_from_report()


def _needs(st) -> dict | None:
    for t in st.texts:
        if "HUN" not in t:
            continue
        vals = {}
        for n in NAMES:
            m = re.search(LABEL[n] + r"\s+(-?\d+)", t)
            if not m or int(m.group(1)) == 999:          # the width sentinel before the first live write
                return None
            vals[n] = int(m.group(1))
        return vals
    return None


def _clock(st) -> tuple | None:
    for t in st.texts:
        m = re.search(r"DAY\s+(\d+)\s+(\d+):00", t)
        if m and int(m.group(1)) != 99 and int(m.group(2)) != 99:
            h = int(m.group(2))                      # night = 18:00-06:00, read off the hour (no HUD word)
            return int(m.group(1)), h, "night" if (h >= 18 or h < 6) else "day"
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
    row = {"t": round(time.monotonic() - T0, 2), "tag": tag, "frame": st.frame, "needs": _needs(st),
           "clock": _clock(st), "tasks": [n for n in NAMES if st.flag(FLAG[n])], "night": st.flag(FLAG["night"]),
           "bx": o and round(o["x"]), "bz": o and round(o["z"]),
           "px": st.player_x and round(st.player_x), "pz": st.player_z and round(st.player_z),
           "choice": bool(st.choice)}
    LOG.append(row)
    return row


def _run_for(g, uid, seconds: float, tag: str, every: float = 0.5, until=None):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        r = _sample(g, uid, tag)
        if until and until(r):
            return r
        time.sleep(every)
    return None


def _at_spot(r, n, rad=200) -> bool:
    return r["bx"] is not None and _d(r["bx"], r["bz"], *SPOT[n]) <= rad


def _open_menu(g, tries: int = 3):
    for _ in range(tries):
        g.press("confirm", 4)
        try:
            return g.wait_for(lambda s: s.choice is not None and s.menu_group == g.CHOICE_GROUP, timeout=3.0,
                              what="a ready directive menu")
        except Exception:                                # noqa: BLE001
            continue
    return None


# The steward's stand point in each zone, and the clear rows between them. walk_to presses the LARGER axis
# first, so one call from the spawn to the pot cut straight up past the cask (inside its collision ring) and
# never arrived (run 1). Every leg below moves ONE axis along a lane the probe shows clear of every object.
STAND = {"hunger": (850, -250), "energy": (-500, -170), "fun": (330, -160),
         "thirst": (-970, -1410), "hygiene": (960, -1355)}
BACK_ROW, FRONT_ROW = -880, -1400


def _go(g, n: str) -> bool:
    sx, sz = STAND[n]
    st = g.state
    cx, cz = st.player_x, st.player_z
    legs = []
    if cz < -1200:                                       # in the front row: slide to the centre column first
        legs += [(0, cz), (0, BACK_ROW)]
    else:                                                # back or middle: drop to the back row, then centre
        legs += [(cx, BACK_ROW), (0, BACK_ROW)]
    if sz < -1200:
        legs += [(0, FRONT_ROW), (sx, FRONT_ROW), (sx, sz)]
    else:
        legs += [(sx, BACK_ROW), (sx, sz)]
    for x, z in legs:
        g.walk_to(x, z, tolerance=40, strict=False)
    x0, z0, x1, z1 = ZONE[n]
    st = g.state
    return x0 < st.player_x < x1 and z0 < st.player_z < z1


def _order(g, uid, n: str) -> tuple[bool, list]:
    """Walk to n's zone, open its menu, take the order row. Returns (landed by flag, the options seen)."""
    if not _go(g, n):
        print(f"[sims] the steward did not reach the {n} zone: {g.state}")
    st = _open_menu(g)
    if st is None:
        return False, []
    opts = g.options()
    row = f"Bilba, {B.VERB[n]}."
    if row not in opts:
        g.choose_landed(g.option_index("Never mind."))
        return False, opts
    g.choose_landed(g.option_index(row))
    ok = _run_for(g, uid, 2.0, f"order-{n}", every=0.1, until=lambda r: n in r["tasks"]) is not None
    return ok, opts


def _tasks_started(rows) -> list[tuple]:
    """(need, row index) for every task flag's rising edge in rows."""
    out, prev = [], set()
    for i, r in enumerate(rows):
        cur = set(r["tasks"])
        out += [(n, i) for n in sorted(cur - prev)]
        prev = cur
    return out


def run(g) -> None:
    global T0
    T0 = time.monotonic()
    mark = g.log_mark()
    g.newgame()
    g.warp(FID)
    g.watch(*FLAG.values())
    st = g.wait_for(lambda s: _needs(s) is not None and _clock(s) is not None and s.objects_status == "listed",
                    timeout=15, what="both HUD strips live and the object list")
    objs = sorted(st.objects, key=lambda o: _d(o["x"], o["z"], *B.HOME))
    if not g.check(objs and _d(objs[0]["x"], objs[0]["z"], *B.HOME) < 400, "R2.0: Bilba stands at home",
                   str([(o["uid"], round(o["x"]), round(o["z"])) for o in st.objects])):
        return
    uid = objs[0]["uid"]
    first = _sample(g, uid, "boot")
    g.check(first["clock"] and first["clock"][:2] == (1, 6) and first["clock"][2] == "day",
            "R2.0: the clock boots at DAY 1 6:00 (day)", str(first["clock"]))
    g.check(all(abs(first["needs"][n] - B.SEED[n]) <= 2 for n in NAMES), "R2.0: the needs boot at their seeds",
            f"{first['needs']} vs {B.SEED}")
    g.shot("1-boot")

    # ---------------- phase A: the undirected day ---------------------------------------------------
    shots = {"night": False, "sleep": False}
    end = time.monotonic() + 24 * B.HOUR / 30 + 25         # one in-game day (+ slack past the next 06:00)
    while time.monotonic() < end:
        r = _sample(g, uid, "undirected")
        if r["clock"] and r["clock"][2] == "night" and not shots["night"]:
            shots["night"] = True
            g.shot("2-nightfall")
        if "energy" in r["tasks"] and _at_spot(r, "energy") and not shots["sleep"]:
            shots["sleep"] = True
            g.shot("3-asleep")
        time.sleep(0.5)
    rows = [r for r in LOG if r["tag"] == "undirected" and r["needs"] and r["clock"]]
    last = rows[-1]

    # the clock: rate, and the alternator agrees with the HUD's day/night
    hours = [(r["t"], (r["clock"][0] - 1) * 24 + r["clock"][1]) for r in rows]
    rate = (hours[-1][1] - hours[0][1]) / max(hours[-1][0] - hours[0][0], 1)
    g.check(0.15 <= rate <= 0.24, "R2.1: the clock runs ~1 in-game hour / 5 s", f"{rate:.3f} h/s, "
            f"{rows[0]['clock']} -> {last['clock']}")
    g.check(last["clock"][0] >= 2, "R2.1: a whole day turned over (DAY 2 reached)", str(last["clock"]))
    agree = [r for r in rows if r["night"] is not None]
    off = [r for r in agree if bool(r["night"]) != (r["clock"][2] == "night")]
    # one sample of slop at each flip: the flag and the HUD update on different ticks
    g.check(agree and len(off) <= 4, "R2.1: the night alternator agrees with the clock's (day)/(night)",
            f"{len(off)} of {len(agree)} samples disagree; first {off[:1]}")

    # metabolism: every need fell below its seed at some point
    lows = {n: min(r["needs"][n] for r in rows) for n in NAMES}
    g.check(all(lows[n] < B.SEED[n] for n in NAMES), "R2.2: every need decays", str(lows))
    g.check(all(lows[n] > 0 for n in NAMES), "R2.2: left alone, nothing bottoms out (no need reaches 0)",
            str(lows))

    # autonomy: tasks start with nobody ordering, each one is carried out
    started = _tasks_started(rows)
    g.check(len(started) >= 3, "R2.3: her own urges start tasks (>= 3 in the day, no orders given)",
            str([(n, rows[i]["clock"]) for n, i in started]))
    done = []                                            # (need, start row, reached, full, retired)
    for n, i in started:
        tail = rows[i:]
        reached = any(_at_spot(r, n) for r in tail)
        # the finish tier fires the TICK the need reads FULL_AT, and decay can take it straight back down
        # (energy at night: 95 -> 94 inside one 0.5 s sample) -- so "full" is judged within 3 points
        full = any(r["needs"][n] >= B.FULL_AT - 3 for r in tail)
        retired = any(n not in r["tasks"] for r in tail)
        done.append((n, i, reached, full, retired))
    complete = [d for d in done if all(d[2:])]
    unfinished = [d for d in done if not all(d[2:])]
    # a task started in the window's last ~25 s may honestly still be running when it closes
    late = [d for d in unfinished if rows[-1]["t"] - rows[d[1]]["t"] < 25]
    g.check(complete and len(unfinished) == len(late), "R2.3: every task she starts takes her to its object, "
            "fills it to FULL_AT and retires", f"complete {[(d[0], rows[d[1]]['clock']) for d in complete]}; "
            f"unfinished {[(d[0], rows[d[1]]['clock'], d[2:]) for d in unfinished]}")
    by_need = {n for n, _ in started}
    print("[sims] tasks started:", [(n, rows[i]["clock"], rows[i]["needs"][n]) for n, i in started])

    # night: she turns in at night
    night_sleeps = [(n, rows[i]["clock"]) for n, i in started if n == "energy" and rows[i]["clock"][2] == "night"]
    g.check(night_sleeps, "R2.4: at night she turns in (an energy task starts in the night)", str(night_sleeps))

    # idleness: no stretch > 4 s with no task while some need sits at/below the urge line
    worst, run_s, run_from = 0.0, 0.0, None
    for a, b in zip(rows, rows[1:]):
        lazy = not a["tasks"] and any(a["needs"][n] <= B.URGE_AT for n in NAMES)
        if lazy:
            run_from = run_from or a
            run_s = b["t"] - run_from["t"]
            worst = max(worst, run_s)
        else:
            run_from = None
    g.check(worst <= 4.0, "R2.4: never idle while a need is under the urge line (longest stretch <= 4 s)",
            f"{worst:.1f}s")

    # ---------------- phase B: the queue --------------------------------------------------------------
    now = _sample(g, uid, "pre-queue")
    cand = sorted((n for n in NAMES if n not in now["tasks"] and now["needs"][n] <= 85),
                  key=lambda n: now["needs"][n])
    # two orders whose zones are far apart from her current spot; at least the two lowest
    if not g.check(len(cand) >= 2, "R2.5 setup: two needs low enough to order (<= 85, not pending)",
                   f"{now['needs']} tasks {now['tasks']}"):
        return
    first_n, second_n = cand[0], cand[1]
    ok1, opts1 = _order(g, uid, first_n)
    g.check(ok1, f"R2.5: the steward orders {first_n} at its object -- the task flag rises", str(opts1))
    ok2, opts2 = _order(g, uid, second_n)
    g.check(ok2, f"R2.5: ...then {second_n} at its object -- queued", str(opts2))
    st = _open_menu(g)                                    # still standing in second_n's zone
    if g.check(st is not None, "R2.5: the second menu re-opens with the order pending"):
        busy = g.options()
        g.check(f"Bilba, {B.VERB[second_n]}." not in busy, "R2.5: its order row is hidden while it pends",
                str(busy))
        g.choose_landed(g.option_index("Never mind."))
    for x, z in ((g.state.player_x, BACK_ROW) if g.state.player_z > -1200 else (0, g.state.player_z),
                 (0, BACK_ROW), (0, -1700)):          # out of everybody's way, by the clear lanes
        g.walk_to(x, z, tolerance=60, strict=False)
    qrows = []
    end = time.monotonic() + 90
    while time.monotonic() < end:
        r = _sample(g, uid, "queue")
        qrows.append(r)
        if r["needs"] and first_n not in r["tasks"] and second_n not in r["tasks"]:
            break
        time.sleep(0.4)
    both_done = qrows and first_n not in qrows[-1]["tasks"] and second_n not in qrows[-1]["tasks"]
    g.check(both_done, "R2.5: both ordered tasks complete", f"last {qrows[-1] if qrows else None}")
    # one at a time: never seen using second_n's object while first_n still pends, unless second_n came first in
    # her tier order (the go tier walks the first FLAGGED need in table order)
    order = sorted([first_n, second_n], key=NAMES.index)
    a_n, b_n = order
    overlap = [r for r in qrows if a_n in r["tasks"] and b_n in r["tasks"] and _at_spot(r, b_n, 160)
               and r["needs"] and r["needs"][a_n] < B.FULL_AT]
    g.check(not overlap, f"R2.5: one task at a time -- {b_n} waits until {a_n} is done (tier order)",
            f"{len(overlap)} samples at the {b_n} object with {a_n} pending")
    g.shot("4-after-queue")

    exc = g.exceptions_since(mark)
    g.check(not exc, "R2: no exception in Memoria.log or output_log over the run", "; ".join(e.name for e in exc[:5]))
    out = Path(g.run_dir) / "sims-timeline.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in LOG) + "\n", encoding="utf-8")
    print(f"[sims] timeline -> {out} ({len(LOG)} rows); needs served by urge: {sorted(by_need)}")
