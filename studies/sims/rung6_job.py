"""A JOB, A SKILL, GIL, BUY MODE, driven live -- sims-arc rung 6 (studies/sims/PLAN.md). A reason to play a second day?

    py studies/sims/sims_bench2.py deploy --variant rung6   # bench 30435
    py tools/play.py studies/sims/rung6_job.py               # this

  R6.1 THE WORKDAY: rested, by day, she goes to the Mognet desk on her own and sorts mail for a shift (it costs
       fun); the shift ends by raising the payday flag her skill earns (60 gil at skill 0).
  R6.2 PAYDAY: the steward cashes it at the household ledger -- real gil (the HUD's live purse) +60; the wage row
       then hides.
  R6.3 STUDY: ordered at the ledger, she studies at the desk -- SKILL climbs; the session ends itself.
  R6.4 BUY MODE: SELECT anywhere opens the moogle catalogue; the toy airship costs 50 real gil and appears where
       the steward stands.
  R6.5 THE PURCHASE PAYS OFF: sent to play, she goes to the TOY (not the puppet) and fun fills.
  R6.6 THE SECOND DAY: a re-entry re-seeds the needs, but SKILL (a persistent table) and gil carry over.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sims_bench2 as B                                  # noqa: E402

B.configure("rung6")                                     # BEFORE rung2_day reads FIELD_ID / the report
import rung2_day as R                                    # noqa: E402

NAMES = B.NAMES
R.STAND["ledger"] = (B.DESK[0], B.LEDGER_ZONE[1] + 30)      # the desk's front edge, inside its zone
R.ZONE["ledger"] = B.LEDGER_ZONE
BUY_SPOT = (-450, -1250)                                 # where the steward stands to buy (open floor)


def _report_flags() -> dict:
    text = B.REPORT.read_text(encoding="utf-8")
    return {m.group(2): int(m.group(1)) for m in re.finditer(r"^\s*flag\s+(\d+)\s+(\S+)\s*$", text, re.M)}


RF = _report_flags()
EXTRA = {k: RF[k] for k in ("t_work", "t_study", "pay_lo", "pay_hi", "worked")}


def _skill_gil(st):
    for t in st.texts:
        m = re.search(r"SKILL\s+(\d+)\s+(\d+):00\s+GIL\s+(\d+)", t)
        if m and int(m.group(1)) != 999 and int(m.group(3)) != 99999:
            return int(m.group(1)), int(m.group(3))
    return None, None


def _row(g, bu, tag):
    r = R._sample(g, bu, tag)
    st = g.state
    r["skill"], r["gil"] = _skill_gil(st)
    for k, b in EXTRA.items():
        r[k] = st.flag(b)
    r["nobj"] = len(st.objects or [])
    return r


def _run_for(g, bu, seconds, tag, every=0.4, until=None):
    """rung2_day._run_for, on THIS bench's richer row (skill, gil, the job flags)."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        r = _row(g, bu, tag)
        if until and until(r):
            return r
        time.sleep(every)
    return None


def _cheb(r, pt) -> float:
    return max(abs(r["bx"] - pt[0]), abs(r["bz"] - pt[1])) if r["bx"] is not None else 9e9


def _menu_pick(g, row: str) -> list:
    if R._open_menu(g) is None:
        return []
    opts = g.options()
    if row in opts:
        g.choose_landed(g.option_index(row))
    else:
        g.choose_landed(g.option_index(opts[-1]))           # the last row is always the decline
    return opts


def run(g) -> None:
    assert R.FID == 30435, R.FID
    R.T0 = time.monotonic()
    mark = g.log_mark()
    g.newgame()
    g.warp(R.FID)
    g.watch(*R.FLAG.values(), *EXTRA.values())
    st = g.wait_for(lambda s: R._needs(s) is not None and _skill_gil(s)[0] is not None and s.objects_status == "listed",
                    timeout=15, what="the HUD strip (needs, skill, gil) and the object list")
    bilba = sorted(st.objects, key=lambda o: R._d(o["x"], o["z"], *B.HOME))[0]
    bu = bilba["uid"]
    boot = _row(g, bu, "boot")
    g.check(boot["skill"] == 0 and boot["gil"] is not None, "R6.0: SKILL boots at 0 (a fresh save), GIL reads live",
            f"skill {boot['skill']} gil {boot['gil']}")
    g.shot("1-boot")

    # ---------------- R6.1 the workday -------------------------------------------------------------------
    work, shot = [], False
    end = time.monotonic() + 60
    while time.monotonic() < end:
        r = _row(g, bu, "workday")
        work.append(r)
        if r["t_work"] and _cheb(r, B.DESK_SPOT) <= 200 and not shot:
            shot = True
            g.shot("2-at-work")
        if r["pay_lo"] or r["pay_hi"]:
            break
        time.sleep(0.4)
    at_desk = [r for r in work if r["t_work"] and _cheb(r, B.DESK_SPOT) <= 200]
    g.check(any(r["t_work"] for r in work), "R6.1: rested and by day, she goes to work on her own (t_work)")
    g.check(len(at_desk) >= 5, "R6.1: she sits at the Mognet desk for the shift", f"{len(at_desk)} samples")
    last = work[-1]
    g.check(last["pay_lo"] and not last["pay_hi"] and last["worked"] and not last["t_work"],
            "R6.1: the shift ends: the 60-gil payday flag (skill 0), worked, the task retired", str(last))
    if at_desk:
        g.check(last["needs"]["fun"] < at_desk[0]["needs"]["fun"], "R6.1: work costs fun",
                f"{at_desk[0]['needs']['fun']} -> {last['needs']['fun']}")

    # ---------------- R6.2 payday ----------------------------------------------------------------------------
    _run_for(g, bu, 30, "await-idle", every=0.4, until=lambda r: not r["tasks"] and not g.state.flag(EXTRA["t_work"]))
    gil0 = _row(g, bu, "pre-pay")["gil"]
    R._go(g, "ledger")
    opts = _menu_pick(g, f"Collect Bilba's wages ({B.WAGE_LO} gil).")
    g.check(f"Collect Bilba's wages ({B.WAGE_LO} gil)." in opts and f"Collect Bilba's wages ({B.WAGE_HI} gil)." not in opts,
            "R6.2: the ledger offers the 60-gil wage (and not the 150)", str(opts))
    g.shot("3-the-ledger")
    paid = _run_for(g, bu, 4, "paid", every=0.2, until=lambda r: r["gil"] is not None and r["gil"] != gil0)
    g.check(paid is not None and paid["gil"] - gil0 == B.WAGE_LO and not paid["pay_lo"],
            "R6.2: payday -- real gil +60, the payday flag cleared", f"{gil0} -> {paid and paid['gil']}")

    # ---------------- R6.3 study -----------------------------------------------------------------------------
    sk0 = _row(g, bu, "pre-study")["skill"]
    opts = _menu_pick(g, "Bilba, study.")
    g.check("Bilba, study." in opts and not any("wages" in o for o in opts),
            "R6.3: (the wage row is gone once cashed) and the ledger orders study", str(opts))
    studied = _run_for(g, bu, 40, "study", every=0.4,
                         until=lambda r: r["skill"] is not None and r["skill"] > sk0 and not r["t_study"])
    rows = [r for r in R.LOG if r["tag"] == "study"]
    g.check(any(r["t_study"] for r in rows), "R6.3: she goes off to study (t_study)")
    g.check(studied is not None and studied["skill"] - sk0 >= 15,
            "R6.3: SKILL climbs at the desk and the session ends itself", f"{sk0} -> {studied and studied['skill']}")

    # ---------------- R6.4 buy mode --------------------------------------------------------------------------
    for x, z in ((g.state.player_x, R.FRONT_ROW), (BUY_SPOT[0], R.FRONT_ROW), BUY_SPOT):
        g.walk_to(x, z, tolerance=40, strict=False)
    pre = _row(g, bu, "pre-buy")
    uids0 = {o["uid"] for o in g.state.objects or []}
    g.press("select", 4)
    menu = None
    try:
        menu = g.wait_for(lambda s: s.choice is not None and s.menu_group == g.CHOICE_GROUP, timeout=6,
                          what="the moogle catalogue")
    except Exception:                                        # noqa: BLE001
        pass
    if g.check(menu is not None, "R6.4: SELECT anywhere opens the moogle catalogue", g.state.text[-100:]):
        opts = g.options()
        g.check(f"A toy airship ({B.TOY_PRICE} gil)." in opts, "R6.4: it offers the toy airship", str(opts))
        g.choose_landed(g.option_index(f"A toy airship ({B.TOY_PRICE} gil)."))
    bought = _run_for(g, bu, 6, "bought", every=0.2,
                        until=lambda r: any(o["uid"] not in uids0 for o in g.state.objects or []))
    st = g.state
    new = [o for o in st.objects or [] if o["uid"] not in uids0]
    g.check(new and R._d(new[0]["x"], new[0]["z"], st.player_x, st.player_z) <= 200,
            "R6.4: the toy appears where the steward stands", str([(o["uid"], round(o["x"]), round(o["z"])) for o in new]))
    after = _row(g, bu, "post-buy")
    g.check(pre["gil"] is not None and after["gil"] == pre["gil"] - B.TOY_PRICE, "R6.4: it costs 50 real gil",
            f"{pre['gil']} -> {after['gil']}")
    g.wait_frames(20)
    g.shot("4-the-toy-placed")
    toy = (new[0]["x"], new[0]["z"]) if new else None

    # ---------------- R6.5 the purchase pays off -----------------------------------------------------------
    _run_for(g, bu, 30, "await-idle2", every=0.4, until=lambda r: not r["tasks"])
    R._go(g, "fun")
    opts = _menu_pick(g, "Bilba, play a while.")
    for x, z in ((g.state.player_x, R.BACK_ROW), (0, R.BACK_ROW), (0, -1700)):
        g.walk_to(x, z, tolerance=60, strict=False)
    playing, shot = [], False
    end = time.monotonic() + 40
    while time.monotonic() < end and toy:
        r = _row(g, bu, "play")
        if "fun" in r["tasks"]:
            playing.append(r)
            if _cheb(r, toy) <= 240 and not shot:
                shot = True
                g.shot("5-playing-with-the-toy")
        elif playing:
            playing.append(r)
            break
        time.sleep(0.4)
    with_toy = [r for r in playing if "fun" in r["tasks"] and _cheb(r, toy) <= 240]
    at_puppet = [r for r in playing if "fun" in r["tasks"] and _cheb(r, R.SPOT["fun"]) <= 160]
    g.check(len(with_toy) >= 3 and not at_puppet, "R6.5: sent to play, she goes to the TOY, not the puppet",
            f"{len(with_toy)} samples at the toy, {len(at_puppet)} at the puppet")
    g.check(playing and playing[-1]["needs"]["fun"] >= B.FULL_AT - 3, "R6.5: fun fills", str(playing[-1:]))

    # ---------------- R6.6 the second day ------------------------------------------------------------------
    before = _row(g, bu, "pre-reentry")
    g.warp(R.FID)
    g.watch(*R.FLAG.values(), *EXTRA.values())
    g.wait_for(lambda s: R._needs(s) is not None and _skill_gil(s)[0] is not None, timeout=15, what="the strip again")
    nxt = _row(g, bu, "second-day")
    g.check(nxt["skill"] == before["skill"] and nxt["skill"] > 0,
            "R6.6: the second day -- SKILL carries over (a persistent table)", f"{before['skill']} -> {nxt['skill']}")
    g.check(nxt["gil"] == before["gil"], "R6.6: ...and so does the gil", f"{before['gil']} -> {nxt['gil']}")
    g.check(all(abs(nxt["needs"][n] - B.SEED[n]) <= 2 for n in NAMES), "R6.6: ...while the needs start a fresh day",
            str(nxt["needs"]))
    g.shot("6-the-second-day")

    exc = g.exceptions_since(mark)
    g.check(not exc, "R6: no exception in Memoria.log or output_log over the run", "; ".join(e.name for e in exc[:5]))
    out = Path(g.run_dir) / "sims-timeline.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in R.LOG) + "\n", encoding="utf-8")
    print(f"[sims] timeline -> {out} ({len(R.LOG)} rows)")
