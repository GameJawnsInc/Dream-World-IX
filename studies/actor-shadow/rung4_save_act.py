"""RUNG 4 follow-up -- the save act's landings keep a `shadow = false` moogle's shadow off on an MCF field.

Bench 30937 (rung4_variants.py): its instant save point at (-800, -950) is `shadow = false`, so the moogle's
Init switches the MCF's blob off. The act the moogle performs on a confirmed save hops out and back, and each
landing ran the donor's EnableShadow -- which would bring the blob back after the first save. With the fix
those two landings are DisableShadow. Two builds of the same toml (rung4_deploy.py):

    on           the fix (the act's landings are DisableShadow)
    act-unfixed  the fix minus the act's kept-off landings -- the negative control: after the save the moogle's
                 MCF blob must come back

    py studies/actor-shadow/rung4_deploy.py <variant> --id 30937 --name SHD4F --text-block 30937
    RUNG4_VARIANT=<variant> py tools/play.py studies/actor-shadow/rung4_save_act.py --label mcf-rung4-save-<variant>
    py studies/actor-shadow/measure_rung4.py save <on run> <act-unfixed run>

PRE  the deployed save moogle's Init ends DisableShadow in both builds; its functions carry no EnableShadow
     (on) or the donor's two (act-unfixed)
S1   talking to the moogle opens its option window (Save), the confirm window (Yes), the ACT runs (its line
     shows -- a press in the zone would run the region's act-less save instead), and it opens the save screen
S2   Cancel backs out of the save screen, the act finishes and hands control back
A0   no exception through a shadow path
F    0-before (the moogle at rest, the player north of it) -- same in both builds; 1-after / 2-after-later --
     the moogle back at rest: no blob in ON, the MCF blob back in ACT-UNFIXED
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402

FIELD = 30937
NAME = "SHD4F"
LIVE = ModLayout(find_game_path() / "FF9CustomMap")
VARIANT = os.environ.get("RUNG4_VARIANT", "on")
assert VARIANT in ("on", "act-unfixed"), VARIANT
MOOGLE = 220
# THE ACT PLAYS ONLY WHEN YOU TALK TO THE MOOGLE: a press inside the save ZONE runs the region's own save,
# which has no act (a type-1 region has no model to animate -- build._dispatch passes it no save_body). So the
# player walks along the spawn row to x -800 and then south INTO the moogle at (-800, -950) from the north,
# outside the zone (z -1200..-1000): collision stops it ~176u short, facing the moogle, and a press talks
# to it. The moogle then stands in front of the player on screen, so its feet (and any blob) stay visible.
ROUTE = [(-800, -600), (-800, -800)]
ACT_LINE = "Here we go"                       # savepoint.DEFAULT_ACT_LINE -- only the act says it


def _moogle_entry(data, eb):
    import struct
    for e in eb.entries:
        f0 = None if e.empty else e.func_by_tag(0)
        sm = next((i for i in eb.instrs(f0) if i.op == 0x2F), None) if f0 is not None else None
        if sm is None or sm.args[0] != MOOGLE:
            continue
        body = data[f0.abs_start:f0.abs_end]
        k = body.find(bytes([0x05, 0xD9, 0x00, 0x7D]))
        if k >= 0 and struct.unpack_from("<h", body, k + 4)[0] == -800:
            return e.index
    raise AssertionError("no save moogle at x -800")


def _preflight(g) -> None:
    data = LIVE.eb_path("us", f"EVT_{NAME}.eb.bytes").read_bytes()
    eb = EbScript.from_bytes(data)
    m = _moogle_entry(data, eb)
    init = [i.op for i in eb.instrs(eb.entry(m).func_by_tag(0))]
    g.check(init[-2:] == [0x80, 0x04], "PRE: the save moogle's Init switches its shadow off (both builds)")
    enables = sum(1 for f in eb.entry(m).funcs for i in eb.instrs(f) if i.op == 0x7F)
    g.check(enables == (0 if VARIANT == "on" else 2), "PRE: the act's landings are the variant's",
            f"EnableShadow x{enables}")


def _pick(g, want, label: str):
    """Choose the option ``want(text)`` names and confirm it LIKE A PLAYER: a window still typewriting eats
    the first Confirm as a fast-forward, so press, check the window moved on, press again -- never twice
    blind (a second blind press would confirm the NEXT window's default row)."""
    opts = g.options()
    i = next((k for k, o in enumerate(opts) if want(o)), None)
    g.check(i is not None, f"S1: the {label} window offers it", str(opts))
    if i is None:
        return None
    before = g.state.text
    g.select(i)
    for _ in range(6):
        g.press("confirm", 4)
        g.wait_frames(20)
        st = g.state
        if not st.dialog_open or st.text != before:
            return opts
    raise AssertionError(f"the {label} window never took the confirm: {before[:60]!r}")


SHADOW_PATHS = ("ff9shadow", "FF9Shadow", "DoEventCode", "SetRenderer", "fldmcf")


def run(g) -> None:
    _preflight(g)
    g.note(f"actor shadow rung 4: the save act under shadow = false -- {VARIANT}")
    g.newgame()
    mark = g.log_mark()
    g.warp(FIELD)
    g.settle()
    g.calibrate_axes()
    for x, z in ROUTE:
        g.walk_to(x, z, tolerance=40, strict=False)
    s = g.settle()
    print(f"[mcf-rung4-save] {VARIANT}: at {(s.player_x, s.player_z)}")
    g.wait_frames(60)
    g.shot("0-before")

    box = g.interact(timeout=6.0)
    g.check(box is not None, "S1: talking to the moogle opens the save point's window")
    if box is None:
        return
    opts = _pick(g, lambda o: "save" in o.lower(), "option")
    print(f"[mcf-rung4-save] {VARIANT}: option window {opts}")
    if opts is None:
        return
    confirm = _pick(g, lambda o: o.strip().lower().startswith("yes"), "confirm")
    print(f"[mcf-rung4-save] {VARIANT}: confirm window {confirm}")
    if confirm is None:
        return
    said = g.wait_for(lambda s: ACT_LINE in (s.text or ""), timeout=20.0, what="the act's line")
    g.check(ACT_LINE in (said.text or ""), "S1: the ACT ran (its line shows -- the zone's region save has none)",
            (said.text or "")[:60])
    st = g.wait_for(lambda s: s.ui_state not in ("FieldHUD",), timeout=30.0,
                    what="the act to open the save screen")
    print(f"[mcf-rung4-save] {VARIANT}: save screen ui_state {st.ui_state!r}")
    g.check(st.ui_state != "FieldHUD", "S1: the act opens the save screen", st.ui_state)
    g.wait_frames(60)
    g.shot("0b-save-screen")
    g.close_ui()
    g.wait_control(timeout=60.0)
    g.settle()
    g.check(g.state.control, "S2: the act finished and handed control back")
    g.wait_frames(90)
    g.shot("1-after")
    g.wait_frames(120)
    g.shot("2-after-later")
    ex = g.exceptions_since(mark)
    ours = [e for e in ex if e.through(*SHADOW_PATHS)]
    g.check(not ours, "A0: no exception through a shadow path", "; ".join(map(str, ours[:3])))
    print(f"[mcf-rung4-save] {VARIANT}: other exceptions: {len(ex) - len(ours)}")
