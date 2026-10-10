"""FAILURE, MOOD, EMOTE, driven live -- sims-arc rung 4 (studies/sims/PLAN.md). Is failing funny?

    py studies/sims/sims_bench2.py deploy --variant rung4   # bench 30433
    py tools/play.py studies/sims/rung4_fail.py              # this

The harness publishes no object's playing CLIP, so the poses are judged two ways: the MECHANISM from state
(flags rise and clear on cue, the meters move, she holds still while down and walks again after), and the
LOOK from frames shot at each moment -- eating, sleeping, laughing, collapsed, back on her feet -- which a
person (or the agent, reading the PNG) judges.

Phase A, the undirected evening (~85 s): MOOD always reads the floor of the needs' average; the posed use
tiers fire (fun -> the laugh, night -> the bed, hunger -> the meal) and each frame is shot.
Phase B, THE ALL-NIGHTER: the steward orders "stay up all night!" at the tent. She gets out of bed, energy
drains to 0, she FAINTS where she stands (frozen collapse), lies there while energy creeps back to 25, gets
up, and takes herself to bed -- walking normally (the pose's restore: no frozen kneel carried into the walk).
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

B.configure("rung4")                                     # BEFORE rung2_day reads FIELD_ID / the report
import rung2_day as R                                    # noqa: E402

NAMES = B.NAMES


def _report_flags() -> dict:
    text = B.REPORT.read_text(encoding="utf-8")
    return {m.group(2): int(m.group(1)) for m in re.finditer(r"^\s*flag\s+(\d+)\s+(\S+)\s*$", text, re.M)}


RF = _report_flags()
EXTRA = {k: RF[k] for k in ("nosleep", "f_energy", "beat")}


def _mood(st) -> int | None:
    for t in st.texts:
        m = re.search(r"MOOD\s+(\d+)", t)
        if m and int(m.group(1)) != 999:
            return int(m.group(1))
    return None


def _row(g, uid, tag):
    r = R._sample(g, uid, tag)
    st = g.state
    r["mood"] = _mood(st)
    for k, b in EXTRA.items():
        r[k] = st.flag(b)
    return r


def run(g) -> None:
    assert R.FID == 30433, R.FID
    R.T0 = time.monotonic()
    mark = g.log_mark()
    g.newgame()
    g.warp(R.FID)
    g.watch(*R.FLAG.values(), *EXTRA.values())
    st = g.wait_for(lambda s: R._needs(s) is not None and _mood(s) is not None and s.objects_status == "listed",
                    timeout=15, what="the HUD strip (needs + mood) and the object list")
    objs = sorted(st.objects, key=lambda o: R._d(o["x"], o["z"], *B.HOME))
    uid = objs[0]["uid"]
    g.check(R._d(objs[0]["x"], objs[0]["z"], *B.HOME) < 400, "R4.0: Bilba stands at home")
    g.shot("1-boot")

    # ---------------- phase A: the undirected evening -------------------------------------------------
    shot = set()

    def moment(r):
        """Shoot each pose once, the first time its state shows (the tier at its object)."""
        for n, label in (("fun", "2-laugh-at-the-puppet"), ("energy", "3-asleep-at-the-tent"),
                         ("hunger", "4-eating-at-the-pot")):
            if n in r["tasks"] and R._at_spot(r, n, 160) and label not in shot:
                shot.add(label)
                g.shot(label)
        if (not r["tasks"] and r["beat"] and r["needs"] and r["needs"]["fun"] >= B.MERRY_AT
                and "5-idle-laugh" not in shot):
            shot.add("5-idle-laugh")
            g.shot("5-idle-laugh")

    end = time.monotonic() + 85
    while time.monotonic() < end:
        r = _row(g, uid, "evening")
        moment(r)
        time.sleep(0.5)
    rows = [r for r in R.LOG if r.get("mood") is not None and r["needs"]]
    bad = [r for r in rows if r["mood"] != sum(r["needs"].values()) // len(NAMES)]
    g.check(rows and len(bad) <= max(2, len(rows) // 50), "R4.1: MOOD reads the floor of the five needs' average",
            f"{len(bad)} of {len(rows)} off; first {[(r['needs'], r['mood']) for r in bad[:2]]}")
    g.check({"2-laugh-at-the-puppet", "3-asleep-at-the-tent"} <= shot,
            "R4.2: the posed use tiers fired (laugh at the puppet, asleep at the tent) -- frames shot",
            str(sorted(shot)))

    # ---------------- phase B: the all-nighter -----------------------------------------------------------
    pre = _row(g, uid, "pre-order")
    was_asleep = "energy" in pre["tasks"]
    R._go(g, "energy")
    menu = R._open_menu(g)
    if not g.check(menu is not None, "R4.3 setup: the tent menu opens", g.state.text[-120:]):
        return
    opts = g.options()
    g.check("Bilba, stay up all night!" in opts, "R4.3: the tent offers the all-nighter", str(opts))
    g.choose_landed(g.option_index("Bilba, stay up all night!"))
    on = R._run_for(g, uid, 3, "order", every=0.1, until=lambda r: bool(g.state.flag(EXTRA["nosleep"])))
    g.check(on is not None, "R4.3: the order lands (nosleep raised)")
    # out of her way, by the clear lanes, while she drains
    for x, z in ((g.state.player_x, R.BACK_ROW), (0, R.BACK_ROW), (0, -1700)):
        g.walk_to(x, z, tolerance=60, strict=False)

    faint = woke = None
    down_pos = []
    end = time.monotonic() + 60
    while time.monotonic() < end:
        r = _row(g, uid, "allnighter")
        if faint is None and r["f_energy"]:
            faint = r
            g.wait_frames(20)
            g.shot("6-fainted")
        if faint is not None and r["f_energy"] and r["bx"] is not None:
            down_pos.append((r["bx"], r["bz"], r["needs"]["energy"] if r["needs"] else None))
        if faint is not None and not r["f_energy"]:
            woke = r
            break
        time.sleep(0.25)
    seg = [r for r in R.LOG if r["tag"] in ("order", "allnighter") and r["needs"]]
    if was_asleep:
        up = next((r for r in seg if "energy" not in r["tasks"]), None)
        g.check(up is not None, "R4.3: she was asleep -- the all-nighter gets her out of bed (task cleared)")
    falls = [r["needs"]["energy"] for r in seg]
    g.check(faint is not None, "R4.4: energy drains to 0 and she FAINTS (the fainted flag rises)",
            f"energy {falls[:1]} -> {falls[-1:]}")
    if faint is None:
        return
    g.check(not faint["nosleep"], "R4.4: fainting ends the all-nighter (nosleep cleared)", str(faint))
    spread = max((math.hypot(a[0] - down_pos[0][0], a[1] - down_pos[0][1]) for a in down_pos), default=0)
    g.check(len(down_pos) >= 8 and spread <= 30, "R4.4: down, she does not move (the frozen collapse holds)",
            f"{len(down_pos)} samples, spread {spread:.0f}u")
    es = [p[2] for p in down_pos if p[2] is not None]
    g.check(es and es[-1] > es[0], "R4.4: lying there, energy creeps back", f"{es[:1]} -> {es[-1:]}")
    g.check(woke is not None and woke["needs"]["energy"] >= B.REVIVE_AT - 2,
            f"R4.5: at {B.REVIVE_AT} energy she gets up (fainted flag clears)", str(woke))
    if woke is None:
        return
    bed = R._run_for(g, uid, 25, "to-bed", every=0.25, until=lambda r: R._at_spot(r, "energy", 160))
    moved = bed is not None and R._d(bed["bx"], bed["bz"], woke["bx"], woke["bz"]) > 150
    g.check(moved, "R4.5: ...and walks herself to bed (the pose's restore: a normal walk, not a frozen kneel)",
            f"from ({woke['bx']},{woke['bz']}) to {bed and (bed['bx'], bed['bz'])}")
    g.wait_frames(30)
    g.shot("7-back-in-bed")

    exc = g.exceptions_since(mark)
    g.check(not exc, "R4: no exception in Memoria.log or output_log over the run", "; ".join(e.name for e in exc[:5]))
    out = Path(g.run_dir) / "sims-timeline.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in R.LOG) + "\n", encoding="utf-8")
    print(f"[sims] timeline -> {out} ({len(R.LOG)} rows); frames: {sorted(shot)}")
