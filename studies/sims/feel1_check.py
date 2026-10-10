"""The owner's first feel test, fixed and re-checked live (studies/sims/PLAN.md, "Feel test 1").

    py studies/sims/sims_bench2.py deploy --variant rung6   # bench 30435
    py tools/play.py studies/sims/feel1_check.py

  F1.1 THE MENU KEEPS THE HUD: the main menu CloseAlls the field's dialogs while the field is paused; the kit's
       HUD watcher re-opens the strip after it -- twice, so the watcher re-arms.
  F1.2 THE ZONES ARE THE OBJECTS: each object's menu opens standing at the object itself (zones centred on it).
  F1.3 A SHOP YOU CAN SEE: the moogle catalogue opens by walking up to the moogle (SELECT still works anywhere).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sims_bench2 as B                                  # noqa: E402

B.configure("rung6")
import rung2_day as R                                    # noqa: E402

R.STAND["ledger"] = (B.DESK[0], B.LEDGER_ZONE[1] + 30)
R.ZONE["ledger"] = B.LEDGER_ZONE
PROMPT = {**{n: B.PROMPT[n] for n in B.BASE_NAMES}, "ledger": "The Mognet desk"}


def _hud_up(s) -> bool:
    return R._needs(s) is not None


def _menu_round(g, label: str) -> None:
    g.press("menu", 4)
    try:
        g.wait_for(lambda s: s.ui_state != "FieldHUD", timeout=5, what="the main menu")
        time.sleep(1.0)
        g.shot(f"{label}-in-menu")
        gone = not _hud_up(g.state)
    except Exception:                                    # noqa: BLE001
        gone = None
    for _ in range(6):
        if g.state.ui_state == "FieldHUD":
            break
        g.press("cancel", 4)
        time.sleep(0.6)
    g.wait_for(lambda s: s.ui_state == "FieldHUD" and s.control, timeout=10, what="back on the field")
    try:
        g.wait_for(_hud_up, timeout=5, what="the HUD strip back")
        back = True
    except Exception:                                    # noqa: BLE001
        back = False
    g.shot(f"{label}-after-menu")
    g.check(back, f"F1.1: after the main menu ({label}) the HUD strip is back",
            f"strip hidden while in the menu: {gone}")


def run(g) -> None:
    assert R.FID == 30435, R.FID
    mark = g.log_mark()
    g.newgame()
    g.warp(R.FID)
    g.wait_for(lambda s: _hud_up(s) and s.objects_status == "listed", timeout=15, what="the HUD strip")
    g.shot("0-boot")
    _menu_round(g, "menu1")
    _menu_round(g, "menu2")

    for n in ("hunger", "fun", "energy", "thirst", "ledger", "hygiene"):
        R._go(g, n)
        st = g.state
        x0, z0, x1, z1 = R.ZONE[n]
        inside = x0 < st.player_x < x1 and z0 < st.player_z < z1
        got = R._open_menu(g)
        text = " ".join(got.texts) if got else ""
        g.shot(f"zone-{n}")
        g.check(got is not None and PROMPT[n] in text,
                f"F1.2: at the {n} object, its own menu opens", f"inside={inside} at ({st.player_x},{st.player_z})")
        if got:
            g.choose_landed(g.option_index("Never mind."))
            g.wait_for(lambda s: s.ui_state == "FieldHUD" and s.choice is None, timeout=5, what="menu closed")

    # the moogle: walk down the centre column to the front row, then west to its east flank
    g.walk_to(g.state.player_x, R.FRONT_ROW, tolerance=40, strict=False)   # one axis: down to the front lane
    g.walk_to(B.CATALOGUE[0] + 220, R.FRONT_ROW, tolerance=40, strict=False)
    g.walk_to(B.CATALOGUE[0] + 220, B.CATALOGUE[1], tolerance=40, strict=False)
    got = R._open_menu(g)
    text = " ".join(got.texts) if got else ""
    g.shot("zone-catalogue")
    g.check(got is not None and "moogle catalogue" in text and any("toy airship" in o for o in g.options()),
            "F1.3: walking up to the moogle opens the catalogue (the toy is for sale)")
    if got:
        g.choose_landed(g.option_index("Not now."))
    exc = g.exceptions_since(mark)
    g.check(not exc, "no engine exceptions", f"{len(exc)}")
