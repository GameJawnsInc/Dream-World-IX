"""THE VISITOR, driven live -- sims-arc rung 5 (studies/sims/PLAN.md). Does the social loop read?

    py studies/sims/sims_bench2.py deploy --variant rung5   # bench 30434
    py tools/play.py studies/sims/rung5_social.py            # this

Phase A, A GOOD CHAT (undirected): Bilba's SOCIAL need runs low; on her own she seeks Garnet out, Garnet stops
to talk, social fills and the relationship (REL) rises.
Phase B, THE FALLING-OUT: the steward keeps her up all night (CRANKY), then sends her to chat. It is a quarrel:
REL falls fast and Garnet glares back; at REL 10 the falling-out is a REAL battle (scene 67, a lone Goblin),
which the harness fights. Back on the field the conversation is over and Bilba is SORRY -- she stands sad while
REL climbs back to 60.
Poses are judged from frames (the harness publishes no playing clip); the mechanism from state.
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

B.configure("rung5")                                     # BEFORE rung2_day reads FIELD_ID / the report
import rung2_day as R                                    # noqa: E402

NAMES = B.NAMES
R.LABEL["social"] = "SOC"
R.STAND["social"] = ((B.PARLOR_ZONE[0] + B.PARLOR_ZONE[2]) // 2, (B.PARLOR_ZONE[1] + B.PARLOR_ZONE[3]) // 2)
R.ZONE["social"] = B.PARLOR_ZONE


def _report_flags() -> dict:
    text = B.REPORT.read_text(encoding="utf-8")
    return {m.group(2): int(m.group(1)) for m in re.finditer(r"^\s*flag\s+(\d+)\s+(\S+)\s*$", text, re.M)}


RF = _report_flags()
EXTRA = {k: RF[k] for k in ("nosleep", "fought", "sorry", "f_energy")}


def _hour_rel(st):
    for t in st.texts:
        m = re.search(r"(\d+):00\s+REL\s+(\d+)", t)
        if m and int(m.group(1)) != 99 and int(m.group(2)) != 999:
            return int(m.group(1)), int(m.group(2))
    return None, None


def _row(g, buid, guid, tag):
    r = R._sample(g, buid, tag)
    st = g.state
    r["hour"], r["rel"] = _hour_rel(st)
    o = R._obj(st, guid)
    r["gx"], r["gz"] = (round(o["x"]), round(o["z"])) if o else (None, None)
    for k, b in EXTRA.items():
        r[k] = st.flag(b)
    r["field"] = st.field_id
    return r


def _gap(r) -> float | None:
    """The CHEBYSHEV gap -- the metric the compiled `near` test uses (a box, not a circle): run 3's chats held at
    Chebyshev 309-313 while the straight-line gap read 324-428, and a Euclidean check saw no chat at all."""
    if None in (r["bx"], r["gx"]):
        return None
    return max(abs(r["bx"] - r["gx"]), abs(r["bz"] - r["gz"]))


def run(g) -> None:
    assert R.FID == 30434, R.FID
    R.T0 = time.monotonic()
    mark = g.log_mark()
    g.newgame()
    g.warp(R.FID)
    g.watch(*R.FLAG.values(), *EXTRA.values())
    st = g.wait_for(lambda s: R._needs(s) is not None and _hour_rel(s)[1] is not None and s.objects_status == "listed",
                    timeout=15, what="the HUD strip (needs, hour, REL) and the object list")
    near = lambda pt: sorted(st.objects, key=lambda o: R._d(o["x"], o["z"], *pt))[0]
    bilba, garnet = near(B.HOME), near(B.PARLOR)
    g.check(R._d(bilba["x"], bilba["z"], *B.HOME) < 400 and R._d(garnet["x"], garnet["z"], *B.PARLOR) < 400
            and bilba["uid"] != garnet["uid"], "R5.0: Bilba at home, Garnet in the parlour",
            str([(o["uid"], round(o["x"]), round(o["z"])) for o in st.objects]))
    bu, gu = bilba["uid"], garnet["uid"]
    first = _row(g, bu, gu, "boot")
    g.check(first["rel"] == B.REL_SEED and first["needs"]["social"] in range(B.SEED["social"] - 2, B.SEED["social"] + 1),
            "R5.0: REL boots at 50, SOCIAL at its seed", f"rel {first['rel']} social {first['needs']['social']}")
    g.shot("1-boot")

    # ---------------- phase A: a good chat, unprompted ------------------------------------------------
    chat_rows, shot = [], False
    end = time.monotonic() + 90
    while time.monotonic() < end:
        r = _row(g, bu, gu, "undirected")
        if "social" in r["tasks"]:
            chat_rows.append(r)
            gap = _gap(r)
            if gap is not None and gap <= 320 and not shot:
                shot = True
                g.wait_frames(20)
                g.shot("2-a-good-chat")
        elif chat_rows:
            chat_rows.append(r)
            break
        time.sleep(0.4)
    talking = [r for r in chat_rows if "social" in r["tasks"] and (_gap(r) or 9e9) <= 320]
    g.check(chat_rows, "R5.1: social runs low and she seeks Garnet out on her own (the social task starts)",
            f"social low {min((r['needs']['social'] for r in R.LOG if r['needs']), default=None)}")
    g.check(len(talking) >= 4, "R5.1: she reaches Garnet and they talk (within 320u)", f"{len(talking)} samples")
    if talking:
        gs = [(r["gx"], r["gz"]) for r in talking]
        spread = max(math.hypot(x - gs[0][0], z - gs[0][1]) for x, z in gs)
        g.check(spread <= 60, "R5.1: Garnet stops to talk (holds still while Bilba chats)", f"spread {spread:.0f}u")
        g.check(talking[-1]["rel"] > talking[0]["rel"], "R5.1: a good chat raises REL",
                f"{talking[0]['rel']} -> {talking[-1]['rel']}")
    done = chat_rows and "social" not in chat_rows[-1]["tasks"]
    g.check(done and chat_rows[-1]["needs"]["social"] >= B.FULL_AT - 3, "R5.1: social fills and the chat ends",
            str(chat_rows[-1] if chat_rows else None))

    # ---------------- phase B: the falling-out --------------------------------------------------------
    # order from an IDLE moment: a queued task (run 1: a meal) runs before the chat, and the window is finite
    R._run_for(g, bu, 40, "await-idle", every=0.4, until=lambda r: not r["tasks"])
    for need, row in (("energy", "Bilba, stay up all night!"), ("social", "Bilba, go chat with Garnet.")):
        R._go(g, need)
        if not g.check(R._open_menu(g) is not None, f"R5.2 setup: the {need} menu opens", g.state.text[-100:]):
            return
        opts = g.options()
        if not g.check(row in opts, f"R5.2 setup: the menu offers {row!r}", str(opts)):
            return
        g.choose_landed(g.option_index(row))
        flag = EXTRA["nosleep"] if need == "energy" else R.FLAG["social"]
        g.check(R._run_for(g, bu, 3, f"order-{need}", every=0.1, until=lambda r: bool(g.state.flag(flag))) is not None,
                f"R5.2: {row!r} lands")
    # the steward STAYS in the parlour zone (run 2: the quarrel and the battle both happened during the walk
    # out, before sampling began). Its stand is ~370u in front of Garnet's spot, clear of Bilba's approach.

    epoch = g.state.battle_epoch
    quarrel, glare_shot = [], False
    end = time.monotonic() + 100
    battle_up = False
    while time.monotonic() < end:
        st = g.state
        if st.in_battle or st.battle_epoch != epoch:
            battle_up = True
            break
        r = _row(g, bu, gu, "quarrel")
        if (_gap(r) or 9e9) <= 320 and "social" in r["tasks"]:
            quarrel.append(r)
            if not glare_shot and r["rel"] is not None and r["rel"] <= B.GLARE_AT:
                glare_shot = True
                g.shot("3-the-quarrel")
        time.sleep(0.25)
    rels = [r["rel"] for r in quarrel if r["rel"] is not None]
    g.check(len(rels) >= 4 and rels[-1] < rels[0], "R5.2: cranky, the chat is a QUARREL -- REL falls",
            f"{rels[:1]} -> {rels[-1:]} over {len(rels)} samples")
    before = quarrel[-1] if quarrel else None
    g.check(battle_up, f"R5.3: at REL {B.FALLOUT_AT} the falling-out is a REAL battle",
            f"last rel {before and before['rel']}")
    if not battle_up:
        return
    g.wait_battle(after_epoch=epoch, timeout=30)
    g.wait_frames(60)
    g.shot("4-the-falling-out")
    result = g.fight()
    g.check(result in (1, 2), "R5.3: the party wins the falling-out", f"result {result}, {g.last_fight}")
    back = g.wait_for(lambda s: s.field_id == R.FID and s.control and not s.in_battle, timeout=60,
                      what="the return to the manor")
    r0 = _row(g, bu, gu, "returned")
    g.check(r0["fought"] and "social" not in r0["tasks"],
            "R5.4: back on the field, the conversation is over (fought set, the social task cleared)", str(r0))
    g.check(r0["rel"] is not None and r0["rel"] <= 30,
            "R5.4: REL survives the battle (the after-battle return does not re-seed the tables)", f"rel {r0['rel']}")
    sorry = [r0]
    end = time.monotonic() + 30
    while time.monotonic() < end:
        r = _row(g, bu, gu, "sorry")
        sorry.append(r)
        if not r["sorry"]:
            break
        time.sleep(0.25)
    g.shot("5-after")
    held = [s for s in sorry if s["sorry"] and s["bx"] is not None]
    spread = max((math.hypot(s["bx"] - held[0]["bx"], s["bz"] - held[0]["bz"]) for s in held), default=0)
    g.check(len(held) >= 3 and spread <= 40, "R5.4: SORRY -- she stands still (sad) while they make up",
            f"{len(held)} samples, spread {spread:.0f}u")
    g.check(sorry[-1]["sorry"] is False and (sorry[-1]["rel"] or 0) >= B.SORRY_UNTIL - 3,
            f"R5.4: made up -- REL back to {B.SORRY_UNTIL} and sorry ends", str(sorry[-1]))

    exc = g.exceptions_since(mark)
    g.check(not exc, "R5: no exception in Memoria.log or output_log over the run", "; ".join(e.name for e in exc[:5]))
    out = Path(g.run_dir) / "sims-timeline.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in R.LOG) + "\n", encoding="utf-8")
    print(f"[sims] timeline -> {out} ({len(R.LOG)} rows)")
