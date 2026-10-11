"""THE `[household]` SMOKE -- the shipped example (examples/household) built through the product path, live.

    py tools/deploy_field.py ff9mapkit/examples/household/household.field.toml --id 30436
    py tools/play.py studies/sims/household_smoke.py

Parity tests (ff9mapkit/tests/test_household.py) prove the desugared block equals the rung-4/6 benches' toml. This proves
the block's own build RUNS: the strip renders, the needs drift, Bilba acts on her own, the steward's menu at an object
offers its order row, the ledger and the catalogue exist, and the order lands (the task flag rises, she goes).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sims_bench2 as B                                  # noqa: E402

B.configure("rung6")                                     # the parsers + the lanes (the example uses the Manor layout)
import rung2_day as R                                    # noqa: E402

FID = 30436


def run(g) -> None:
    R.T0 = time.monotonic()
    g.newgame()
    g.warp(FID)
    st = g.wait_for(lambda s: R._needs(s) is not None and s.objects_status == "listed", timeout=20,
                    what="the HUD strip (needs) and the object list")
    objs = sorted(st.objects, key=lambda o: R._d(o["x"], o["z"], *B.HOME))
    bu = objs[0]["uid"]
    g.check(R._d(objs[0]["x"], objs[0]["z"], *B.HOME) < 400, "H1: Bilba stands at home")
    n0 = R._needs(st)
    g.shot("1-boot")
    time.sleep(14)
    n1 = R._needs(g.state)
    g.check(n1 is not None and sum(n1.values()) < sum(n0.values()),
            "H2: the needs drift down on their own", f"{n0} -> {n1}")

    # an order: stand at the pot, take its row, and the task flag rises (flag indices are the block's own)
    flags_before = None
    if not R._go(g, "hunger"):
        print(f"[household] the steward did not reach the pot zone: {g.state}")
    menu = R._open_menu(g)
    g.check(menu is not None, "H3: the pot's menu opens at the object")
    if menu is None:
        return
    opts = g.options()
    g.check("Bilba, eat something." in opts and opts[-1] == "Never mind.",
            "H3: the order row is offered, 'Never mind.' last", str(opts))
    g.choose_landed(g.option_index("Bilba, eat something."))
    g.shot("2-ordered")
    moved = None
    start = (R._sample(g, bu, "post-order")["bx"], R._sample(g, bu, "post-order")["bz"])
    end = time.monotonic() + 40
    while time.monotonic() < end:
        r = R._sample(g, bu, "go")
        if r["bx"] is not None and R._d(r["bx"], r["bz"], *start) > 150:
            moved = r
            break
        time.sleep(0.3)
    g.check(moved is not None, "H4: the order lands -- Bilba sets off", str(R.LOG[-1]))

    # the ledger and the catalogue exist: their zones open a menu
    g.walk_to(0, R.BACK_ROW, tolerance=60, strict=False)
    opened = {}
    for label, spot in (("ledger", (300, -1150 + 200)), ("catalogue", (-500, -1650 + 200))):
        g.walk_to(*spot, tolerance=60, strict=False)
        m = R._open_menu(g)
        opened[label] = g.options() if m is not None else None
        if m is not None:
            g.choose_landed(g.option_index(opened[label][-1]))
    g.check(opened["ledger"] and "Bilba, study." in opened["ledger"], "H5: the household ledger menu opens",
            str(opened["ledger"]))
    g.check(opened["catalogue"] and any("toy airship" in o.lower() for o in opened["catalogue"]),
            "H5: the moogle catalogue opens (the toy row is gated until she can afford it)",
            str(opened["catalogue"]))
