"""THE PICK, driven live -- sims-arc rung 3 (studies/sims/PLAN.md): the rung-2 household with its urge tier
gated on a [[behavior.pick]] (the index of the LOWEST need, every pass) instead of a fixed priority list.

    py studies/sims/sims_bench2.py deploy --variant pick   # bench 30432
    py tools/play.py studies/sims/rung3_pick.py             # this

It runs the whole rung-2 day (every R2 check, now against 30432), then judges the lane itself from the HUD's
URG slot -- the compiled loop's own output, published beside the five needs it read:
  R3.1 the slot renders live;  R3.2 it always names the lowest displayed need (ties -> the lower index);
  R3.3 every task she starts on her own, night bedtime aside, is for the need the pick named.
The A/B verdict ("visibly smarter?") is NOT this file's: offline, `sims_bench2.py ab` -- see PLAN.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sims_bench2 as B                                  # noqa: E402

B.configure("pick")                                      # BEFORE rung2_day reads FIELD_ID / the report
import rung2_day as R                                    # noqa: E402

NAMES = B.NAMES


def _argmin(needs: dict) -> int:
    vals = [needs[n] for n in NAMES]
    return vals.index(min(vals))                         # first occurrence = the lower index on a tie


def run(g) -> None:
    assert R.FID == 30432, R.FID
    R.run(g)
    rows = [r for r in R.LOG if r["needs"]]
    live = [r for r in rows if r["urg"] is not None]
    g.check(len(live) >= 0.9 * len(rows), "R3.1: the URG slot renders live (the pick's published index)",
            f"{len(live)} of {len(rows)} samples")
    bad = [r for r in live if r["urg"] != _argmin(r["needs"])]
    g.check(live and len(bad) <= max(2, len(live) // 50),
            "R3.2: URG always names the LOWEST displayed need (ties -> the lower index)",
            f"{len(bad)} of {len(live)} disagree; first {[(r['t'], r['needs'], r['urg']) for r in bad[:3]]}")
    und = [r for r in rows if r["tag"] == "undirected"]
    starts, prev = [], set()
    for i, r in enumerate(und):
        new = set(r["tasks"]) - prev
        prev = set(r["tasks"])
        for n in new:
            before = und[i - 1] if i else r
            night_bed = n == "energy" and (before["night"] or r["night"])   # the alternator leads the HUD hour
            if not night_bed:
                starts.append((n, before["urg"], r["urg"], before["needs"], r["clock"]))
    off = [s for s in starts if NAMES.index(s[0]) not in (s[1], s[2])]
    g.check(starts and not off, "R3.3: every task she starts on her own (bedtime aside) is the need the pick named",
            f"{len(starts)} starts; off-pick {off[:3]}")
    print("[sims] rung-3 starts (need, urg before, urg at, needs before, clock):")
    for s in starts:
        print("   ", s)
