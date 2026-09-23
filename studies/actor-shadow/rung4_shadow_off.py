"""RUNG 4 of the actor-shadow arc -- on a field that ships MapConfigData, `shadow = false` switches off the
player, an [[npc]], a [[chest]] and a [[savepoint]] with stock's DisableShadow, and the player's stays off
after a jump (the engine's FinishJump re-enables a jumper's shadow; the kit re-disables it at the arc's end).

The bench is the set-pieces bench shipping field 1607's MCF with `shadow = false` on the player, the chest, the
instant save point and the holder NPC, plus a tread [[jump]] (rung4_variants.py -> the gitignored
imported/rung4/). ON / INIT-ONLY / CONTROL are the same toml built three ways (rung4_deploy.py); CONTROL is
byte-identical to a HEAD build.

    py studies/actor-shadow/rung4_variants.py
    py studies/actor-shadow/rung4_deploy.py <variant> --id 30937 --name SHD4F --text-block 30937
    RUNG4_VARIANT=<variant> py tools/play.py studies/actor-shadow/rung4_shadow_off.py --label mcf-rung4-<variant>
    py studies/actor-shadow/measure_rung4.py <on run> <init-only run> <control run>

PRE  the deployed MCF is 1607's; no size/amp op anywhere; the variant's DisableShadow ops are where it puts
     them: the player's Init (on, init-only), before the jump arc's RETURN (on only), the holder's, the
     chest's and the save moogle's Init tail (on, init-only), and the save act's landings keep it off
     (on, init-only: no EnableShadow; control: the donor's two)
J1   the tread zone fires the jump and the player lands at the jump's `to`, with control back
A0   no exception through a shadow path
F1   1-spawn: the off actors show no MCF blob in ON / INIT-ONLY, one in CONTROL; the cask, cactus_on and
     barrel save point unchanged in all three
F2   2-landed (+ 3-landed-later): no blob under the landed player in ON; INIT-ONLY's comes back (FinishJump)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402
from ff9mapkit.content.ladder import find_player_entry  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402

FIELD = 30937
NAME = "SHD4F"
LIVE = ModLayout(find_game_path() / "FF9CustomMap")
STAGED_MCF = HERE / "imported" / "rung4" / "mapconfig.bytes"
VARIANT = os.environ.get("RUNG4_VARIANT", "on")
assert VARIANT in ("on", "init-only", "control"), VARIANT
CSO, CHEST, MOOGLE = 217, 75, 220
JUMP_ZONE_X, JUMP_ZONE_Z = 1055, -225        # the tread zone's middle (x 1000..1110, z -300..-150)
LANDING = (650, -600)                        # the jump's `to`
DISABLE, ENABLE, SIZE, AMP, JUMP, RETURN, HEADFOCUS = 0x80, 0x7F, 0x81, 0x85, 0xDC, 0x04, 0x8B


def _objects(data, eb):
    """``{(model, x, z): entry}`` from each object Init's literal SetModel + D9(0)/D9(4) placement consts."""
    import struct
    out = {}
    for e in eb.entries:
        f0 = None if e.empty else e.func_by_tag(0)
        sm = next((i for i in eb.instrs(f0) if i.op == 0x2F), None) if f0 is not None else None
        if sm is None:
            continue
        body = data[f0.abs_start:f0.abs_end]
        xz = []
        for var in (0, 4):
            k = body.find(bytes([0x05, 0xD9, var, 0x7D]))
            xz.append(struct.unpack_from("<h", body, k + 4)[0] if k >= 0 else None)
        out[(sm.args[0], *xz)] = e.index
    return out


def _preflight(g) -> None:
    mcf = LIVE.mapconfig_path(f"EVT_{NAME}")
    g.check(mcf.is_file() and mcf.read_bytes() == STAGED_MCF.read_bytes(), "PRE: the deployed MCF is 1607's")
    data = LIVE.eb_path("us", f"EVT_{NAME}.eb.bytes").read_bytes()
    eb = EbScript.from_bytes(data)
    ops = {(e.index, f.tag): [i.op for i in eb.instrs(f)] for e in eb.entries if not e.empty for f in e.funcs}
    g.check(not any(op in (SIZE, AMP) for o in ops.values() for op in o), "PRE: no size/amp op anywhere")
    on_side = VARIANT != "control"
    pe = find_player_entry(eb)
    init = ops[(pe, 0)]
    g.check((init[init.index(HEADFOCUS) + 1] == DISABLE) == on_side,
            "PRE: the player's Init DisableShadow is the variant's", str(init[init.index(HEADFOCUS):][:3]))
    arcs = [o for (e, t), o in ops.items() if e == pe and JUMP in o]
    g.check(len(arcs) == 1 and (arcs[0][-2:] == [DISABLE, RETURN]) == (VARIANT == "on"),
            "PRE: the jump arc re-disables before its RETURN in ON only", str(arcs and arcs[0][-3:]))
    objs = _objects(data, eb)
    for key, what in (((CSO, -300, -1000), "holder"), ((CHEST, 450, -250), "chest"),
                      ((MOOGLE, -800, -950), "save moogle")):
        tail = ops[(objs[key], 0)][-2:]
        g.check((tail == [DISABLE, RETURN]) == on_side, f"PRE: the {what}'s Init DisableShadow is the variant's",
                str(tail))
    act = [op for (e, t), o in ops.items() if e == objs[(MOOGLE, -800, -950)] for op in o]
    g.check(act.count(ENABLE) == (0 if on_side else 2), "PRE: the save act's landings are the variant's",
            f"EnableShadow x{act.count(ENABLE)}")


SHADOW_PATHS = ("ff9shadow", "FF9Shadow", "DoEventCode", "SetRenderer", "fldmcf", "FinishJump")


def _exceptions(g, mark, when: str) -> None:
    ex = g.exceptions_since(mark)
    ours = [e for e in ex if e.through(*SHADOW_PATHS)]
    g.check(not ours, f"A0: no exception through a shadow path ({when})", "; ".join(map(str, ours[:3])))
    print(f"[mcf-rung4] {VARIANT}: other exceptions {when}: {len(ex) - len(ours)}")


def run(g) -> None:
    _preflight(g)
    g.note(f"actor shadow rung 4: shadow = false on an MCF field -- {VARIANT}")
    g.newgame()
    mark = g.log_mark()
    g.warp(FIELD)
    g.settle()
    g.wait_frames(60)
    g.shot("1-spawn")
    # J1 -- walk east along the spawn row, then north into the tread zone: it fires the jump on entry
    g.calibrate_axes()
    g.walk_to(JUMP_ZONE_X, -600, tolerance=40, strict=False)
    g.walk_to(JUMP_ZONE_X, JUMP_ZONE_Z, tolerance=40, strict=False)
    g.wait_control(timeout=20.0)
    s = g.settle()
    at = (s.player_x, s.player_z)
    print(f"[mcf-rung4] {VARIANT}: landed at {at}")
    g.check(g.distance_to(*LANDING) < 120 and g.state.control,
            "J1: the tread zone fired the jump and the player landed at its `to`, control back", str(at))
    g.wait_frames(45)
    g.shot("2-landed")
    g.wait_frames(120)
    g.shot("3-landed-later")
    _exceptions(g, mark, "the whole run")
