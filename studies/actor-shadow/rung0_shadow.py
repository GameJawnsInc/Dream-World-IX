"""RUNG 0 of the actor-shadow fix -- do kit-field actors cast the stock blob shadow in-game?

    py tools/play.py studies/actor-shadow/rung0_shadow.py --label shadow-rung0
    SHADOW_CONTROL=1 py tools/play.py studies/actor-shadow/rung0_shadow.py --label shadow-rung0-control
      (the CONTROL run, after deploying bench/shadow0_control.field.toml to the same slot: every actor at
      shadow = false; its frames are the pixel reference measure_shadows.py compares against)

Bench studies/actor-shadow/bench/shadow0.field.toml (30920), on the walkmesh-sensor bench's floor + camera
(its rung-0 frame, .harness-runs/20260923-094949-bgi-rung0/shots/1-spawn.png, is the BEFORE: no shadow under
the player or either NPC). Every case sits in ONE frame, so the eye can judge a single shot:
the player + `stock` + the behavior unit `rover` at their census values, `big` at an override, and `none`
opted out -- the in-frame NEGATIVE CONTROL, the same model on the same floor with no ops. The measured
verdict is measure_shadows.py against the CONTROL run (the same bench, every actor shadow = false).

PRE  the DEPLOYED .eb (what the engine will run, not what the build says) carries exactly the expected ops:
     SetShadowSize(s, s) + SetShadowAmplifier(i << 3) per actor, none on `none`
A0   no exception THROUGH a shadow path, in either log (a shadow op before SetModel would KeyNotFound on
     shadowArray inside DoEventCode; the render side is SetRenderer / ff9shadow). Every OTHER exception is
     reported by name + count, never silently passed. The ~26-28 FieldMapActorController.MovePC
     NullReferenceExceptions the pre-s87 runs tallied were NOT this floor's. Field 70 (the New Game FMV
     field) has no walkmesh, and it threw them between newgame() and the warp; the mark is taken before the
     warp, so they count. Engine patch s87 fixed that stock bug and the count is now 0. Compare only against
     a control run on the same engine.
F1   the spawn frame (a LOOK, read by eye): a blob under player / stock / big / rover, NONE under `none`,
     `big` visibly larger and darker than `stock`
F2   the rover walking (the behavior unit's shadow travels with it)
"""
from __future__ import annotations

import os
import struct
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.content import behaviortoml as BT  # noqa: E402
from ff9mapkit.content.ladder import find_player_entry  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402

FIELD = 30920
BENCH = HERE / "bench" / "shadow0.field.toml"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
EB_FILE = (GAME / "FF9CustomMap" / "StreamingAssets" / "Assets" / "Resources" / "CommonAsset" / "EventEngine"
           / "EventBinary" / "Field" / "us" / "EVT_SHD0.eb.bytes")

# name -> (SetShadowSize arg, SetShadowAmplifier arg) the deployed Init must carry; None = no shadow ops
EXPECT = {"player": (9, 32), "stock": (9, 24), "big": (16, 64), "none": None, "rover": (9, 24)}
CONTROL = os.environ.get("SHADOW_CONTROL") == "1"
if CONTROL:                                             # bench/shadow0_control.field.toml: nobody casts one
    EXPECT = {n: None for n in EXPECT}

_RAW = tomllib.loads(BENCH.read_text(encoding="utf-8"))
_FB, _CB = BT.dry_compile(_RAW)
WALK = _FB.bb.flag("walk")
POS = {n["name"]: tuple(n["pos"]) for n in _RAW["npc"]}


def _init_shadow(eb, entry):
    ins = list(eb.instrs(eb.entry(entry).func_by_tag(0)))
    sz = [i.args[0] for i in ins if i.op == 0x81]
    am = [i.args[0] for i in ins if i.op == 0x85]
    return None if not sz and not am else (tuple(sz), tuple(am))


def _npc_xz(data, eb, entry):
    """The (x, z) an NPC Init's D9(0)/D9(4) consts place it at (content.npc.build_npc_init's shape)."""
    f0 = eb.entry(entry).func_by_tag(0)
    body = data[f0.abs_start:f0.abs_end]
    out = []
    for var in (0, 4):
        k = body.find(bytes([0x05, 0xD9, var, 0x7D]))
        out.append(struct.unpack_from("<h", body, k + 4)[0] if k >= 0 else None)
    return tuple(out)


def _preflight(g) -> None:
    data = EB_FILE.read_bytes()
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    got = {"player": _init_shadow(eb, pe)}
    for e in eb.entries:
        if e.empty or e.index == pe or e.func_by_tag(0) is None:
            continue
        if not any(i.op == 0x2F for i in eb.instrs(e.func_by_tag(0))):
            continue
        xz = _npc_xz(data, eb, e.index)
        name = next((n for n, p in POS.items() if p == xz), f"?{xz}")
        got[name] = _init_shadow(eb, e.index)
    want = {n: (None if v is None else ((v[0],), (v[1],))) for n, v in EXPECT.items()}
    print(f"[shadow-rung0] deployed Init shadow ops: {got}")
    g.check(got == want, "PRE: the deployed .eb carries exactly the expected shadow ops per actor "
            "(size, amp) and none on `none`", f"{got} vs {want}")


def run(g) -> None:
    _preflight(g)
    g.note("actor shadow rung 0" + (" -- CONTROL (every actor shadow = false)" if CONTROL else ""))
    g.newgame()
    mark = g.log_mark()
    g.warp(FIELD)
    g.flag(WALK, False)
    g.settle()
    g.wait_frames(60)                                   # the behavior warmup + a few render frames
    g.shot("1-spawn")
    _exceptions(g, mark, "entering the field")

    g.flag(WALK, True)
    g.wait_frames(150)
    g.shot("2-rover-walking")
    g.wait_frames(150)
    g.shot("3-rover-walking-later")
    _exceptions(g, mark, "entering the field and while the unit walks")


SHADOW_PATHS = ("ff9shadow", "FF9Shadow", "DoEventCode", "SetRenderer", "fldmcf")


def _exceptions(g, mark, when: str) -> None:
    ex = g.exceptions_since(mark)
    ours = [e for e in ex if e.through(*SHADOW_PATHS)]
    g.check(not ours, f"A0: no exception through a shadow path ({when})", "; ".join(map(str, ours[:3])))
    tally: dict = {}
    for e in ex:
        if e not in ours:
            tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[shadow-rung0] other exceptions {when} (compare the control run): {tally or 'none'}")
