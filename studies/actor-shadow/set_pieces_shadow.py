"""SET PIECES, the actor-shadow follow-up -- do kit SET PIECES cast the stock shadow stock gives them, in-game?

    py tools/play.py studies/actor-shadow/set_pieces_shadow.py --label shadow-set-pieces-on
    SHADOW_CONTROL=1 py tools/play.py studies/actor-shadow/set_pieces_shadow.py --label shadow-set-pieces-control
      (the CONTROL run, after deploying bench/set_pieces_control.field.toml to the same slot: shadow = false on
      every set piece -- their pre-change bytes; its frames are measure_shadows.py --bench set_pieces's reference)

Bench studies/actor-shadow/bench/set_pieces.field.toml (30921), rung 0's floor + camera. Row A: a cask prop (stock
casts), a cactus (stock DISABLES it -- no ops), the same cactus with shadow = true, a chest. Row B: an instant
save moogle, an NPC holding a cup (the held cup gets no ops), and a barrel_pop save point whose moogle spawns
stowed in its cask. The player spawns between the rows (the camera follows it), north of the barrel.

PRE  the DEPLOYED .eb carries exactly the expected ops per object (keyed by model + Init position): size +
     amp on the casting set pieces, none on the cactus / the held cup, DisableShadow (donor) and no size op
     on the act's book + feather; the player + holder keep their rung-0 ops in BOTH runs
A0   no exception THROUGH a shadow path, in either log; every other exception tallied (the ~26
     FieldMapActorController.MovePC NREs per pre-s87 run were field 70's, thrown before the warp, not this
     floor's; engine patch s87 fixed them -- compare the control's count on the same engine)
R1   the barrel_pop REVEAL still runs with the 7 new bytes in the moogle + cask Inits (its state machine was
     proven byte-for-byte in-game, bench 30210): pressing the cask takes control away and hands it back (the
     cask's handshake poll), and the save point's zone then OPENS the menu -- its gate passes only once the
     moogle's pop arm has run to its end and written OUT
F1   1-spawn (a LOOK): a blob under the cask, cactus_on, chest, the save moogle, the holder, the barrel cask;
     NONE under the plain cactus; the stowed moogle is hidden and so is its shadow
F2   2-popped: the moogle perched on the cask, its shadow on the cask top
F3   3-after-cancel: the menu cancelled (a LOOK; whether Cancel stows the moogle depends on which handler took
     the press -- not asserted)
"""
from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.content.ladder import find_player_entry  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402

FIELD = 30921
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
EB_FILE = (GAME / "FF9CustomMap" / "StreamingAssets" / "Assets" / "Resources" / "CommonAsset" / "EventEngine"
           / "EventBinary" / "Field" / "us" / "EVT_SHD1.eb.bytes")
CASK, GAS, CHEST, MOOGLE, CSO, CUP, BOOK, FEATHER = 241, 537, 75, 220, 217, 234, 133, 134
BARREL = (900, -1000)                                   # the barrel_pop cask + its stowed moogle

# (model, x, z) -> (SetShadowSize arg, SetShadowAmplifier arg), None = no size/amp op, "off" = DisableShadow only
EXPECT = {
    "player": (9, 32),
    (CASK, -900, -250): (11, 40),                       # the cask prop
    (GAS, -450, -250): None,                            # the cactus: stock-dark
    (GAS, 0, -250): (8, 32),                          # the cactus, shadow = true
    (CHEST, 450, -250): (10, 32),                       # the chest
    (MOOGLE, -800, -950): (6, 16),                      # the instant save moogle
    (BOOK, -800, -950): "off", (FEATHER, -800, -950): "off",     # its act props (donor DisableShadow)
    (CSO, -300, -1000): (9, 24),                        # the holder NPC (rung 0)
    (CUP, -300, -1000): None,                           # the HELD cup
    (CASK, *BARREL): (11, 40),                          # the barrel_pop cask
    (MOOGLE, *BARREL): (6, 16),                         # the barrel_pop moogle
    (BOOK, *BARREL): "off", (FEATHER, *BARREL): "off",
}
UNCHANGED = {"player", (CSO, -300, -1000)}             # this change does not touch them: same in both runs
CONTROL = os.environ.get("SHADOW_CONTROL") == "1"
if CONTROL:                                             # bench/set_pieces_control.field.toml
    EXPECT = {k: (v if k in UNCHANGED or v in (None, "off") else None) for k, v in EXPECT.items()}
# THE CASK CALIBRATION (SHADOW_CASKDIAG=1): the census cask shadow measures 1.000 -- its 154 x 132u quad is
# smaller than the barrel's own ~380u footprint. To tell "drawn under the model" from "the op did nothing on
# this object", the deployed shadows-on .eb has both casks' SetShadowSize byte-patched 11 -> 40 in place
# (81 00 0B 0B -> 81 00 28 28, same length, nothing else moves): a 560u quad must show past the barrel.
CASKDIAG = os.environ.get("SHADOW_CASKDIAG") == "1"
if CASKDIAG:
    EXPECT = {k: ((40, 40) if isinstance(k, tuple) and k[0] == CASK else v) for k, v in EXPECT.items()}


def _init_ops(eb, entry):
    ins = list(eb.instrs(eb.entry(entry).func_by_tag(0)))
    sz = [i.args[0] for i in ins if i.op == 0x81]
    am = [i.args[0] for i in ins if i.op == 0x85]
    if not sz and not am:
        return "off" if any(i.op == 0x80 for i in ins) else None
    if len(sz) != 1 or len(am) != 1:
        return ("?", tuple(sz), tuple(am))
    return sz[0], am[0]


def _xz(data, eb, entry):
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
    got = {"player": _init_ops(eb, pe)}
    for e in eb.entries:
        f0 = None if e.empty else e.func_by_tag(0)
        if f0 is None or e.index == pe:
            continue
        sm = next((i for i in eb.instrs(f0) if i.op == 0x2F), None)
        if sm is None:
            continue
        key = (sm.args[0], *_xz(data, eb, e.index))
        g.check(key not in got, f"PRE: one object per (model, x, z) -- {key}")
        got[key] = _init_ops(eb, e.index)
    print(f"[shadow-set-pieces] deployed Init shadow ops: {got}")
    diff = {k: (got.get(k), EXPECT.get(k)) for k in set(got) | set(EXPECT) if got.get(k) != EXPECT.get(k)}
    g.check(got == EXPECT, "PRE: the deployed .eb carries exactly the expected shadow ops per object",
            f"(got, want): {diff}")


def run(g) -> None:
    _preflight(g)
    g.note("actor shadow: set pieces" + (" -- CONTROL (every set piece shadow = false)" if CONTROL else ""))
    g.newgame()
    mark = g.log_mark()
    g.warp(FIELD)
    g.settle()
    g.wait_frames(60)
    g.shot("1-spawn")
    _exceptions(g, mark, "entering the field")

    # R1 -- press the barrel. walk_to moves one axis at a time, and x already matches, so this is a pure
    # walk SOUTH into the cask: collision stops the player at contact, facing it.
    g.calibrate_axes()
    g.walk_to(BARREL[0], BARREL[1] + 60, tolerance=40, strict=False)
    s = g.state
    print(f"[shadow-set-pieces] at the cask: pos {s.pos}, control {s.control}")
    g.press("confirm", 4)
    dropped = True
    try:
        g.wait_for(lambda st: not st.control, timeout=5.0, what="the cask press takes control")
    except Exception as e:                                  # noqa: BLE001 -- reported as the check below
        dropped = False
        print(f"[shadow-set-pieces] control never dropped: {e}")
    g.check(dropped, "R1: pressing the cask takes control (its handler's DisableMove + handshake poll)")
    g.wait_control(timeout=30.0)
    g.check(g.state.control, "R1: control comes back -- the moogle's pop arm released the cask's handshake")
    g.wait_frames(45)
    g.shot("2-popped")

    box = g.interact(timeout=6.0)
    g.check(box is not None and bool(box.choice),
            "R1: the save point's menu OPENS after the pop (its zone gate needs the pop arm's OUT write)",
            f"{box.text[:80]!r}" if box is not None else "no dialogue")
    if box is not None:
        g.shot("2b-menu")
        opts = g.options()
        print(f"[shadow-set-pieces] menu options: {opts}")
        cancel = next((i for i, o in enumerate(opts) if "cancel" in o.lower()), len(opts) - 1)
        g.choose(cancel)
        g.wait_control(timeout=30.0)
        g.wait_frames(90)
        g.shot("3-after-cancel")
    _exceptions(g, mark, "the whole run")


SHADOW_PATHS = ("ff9shadow", "FF9Shadow", "DoEventCode", "SetRenderer", "fldmcf")


def _exceptions(g, mark, when: str) -> None:
    ex = g.exceptions_since(mark)
    ours = [e for e in ex if e.through(*SHADOW_PATHS)]
    g.check(not ours, f"A0: no exception through a shadow path ({when})", "; ".join(map(str, ours[:3])))
    tally: dict = {}
    for e in ex:
        if e not in ours:
            tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[shadow-set-pieces] other exceptions {when} (compare the control run): {tally or 'none'}")
