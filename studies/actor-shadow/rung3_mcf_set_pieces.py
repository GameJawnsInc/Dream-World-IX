"""RUNG 3 of the actor-shadow arc -- on a field that ships MapConfigData, a kit set piece stock would not let
cast gets stock's DisableShadow: the held cup and the stock-dark cactus, which the MCF shadowed before.

The bench is the set-pieces bench (30921's actors, floor and camera) shipping field 1607's MCF, staged by
rung3_variants.py into the gitignored imported/rung3/. ON and CONTROL are the same toml built two ways
(rung3_deploy.py): ON with this change, CONTROL through the pre-fix call (byte-identical to the old build).

    py studies/actor-shadow/rung3_variants.py
    py studies/actor-shadow/rung3_deploy.py on --id 30936 --name SHD3M --text-block 30936
    py tools/play.py studies/actor-shadow/rung3_mcf_set_pieces.py --label mcf-rung3-on
    py studies/actor-shadow/rung3_deploy.py control --id 30936 --name SHD3M --text-block 30936
    RUNG3_CONTROL=1 py tools/play.py studies/actor-shadow/rung3_mcf_set_pieces.py --label mcf-rung3-control
    py studies/actor-shadow/measure_shadows.py <on run> <control run> --bench set_pieces --out SHEET.png

PRE  the deployed MCF is 1607's, byte for byte, and the deployed .eb carries exactly the variant's shadow state
     per object (keyed by model + Init position): NO size/amp op anywhere (the MCF owns the values), and
     DisableShadow on the act's book + feather (donor bytes, both runs) -- plus, in ON only, on the stock-dark
     cactus and the held cup
A0   no exception THROUGH a shadow path; every other exception tallied
F1   1-spawn (+ 2-spawn-later): the MCF blob under the cactus and near the holder's hand in CONTROL, none in
     ON; every casting actor (cask, cactus_on, chest, moogles, holder, player) the same in both
"""
from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402
from ff9mapkit.content.ladder import find_player_entry  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402

FIELD = 30936
NAME = "SHD3M"
LIVE = ModLayout(find_game_path() / "FF9CustomMap")
STAGED_MCF = HERE / "imported" / "rung3" / "mapconfig.bytes"
CASK, GAS, CHEST, MOOGLE, CSO, CUP, BOOK, FEATHER = 241, 537, 75, 220, 217, 234, 133, 134
BARREL = (900, -1000)
CONTROL = os.environ.get("RUNG3_CONTROL") == "1"

# (model, x, z) -> "off" (DisableShadow in the Init) or None (no shadow op: the MCF casts it)
EXPECT = {
    "player": None, (CSO, -300, -1000): None,
    (CASK, -900, -250): None, (GAS, 0, -250): None, (CHEST, 450, -250): None,
    (MOOGLE, -800, -950): None, (CASK, *BARREL): None, (MOOGLE, *BARREL): None,
    (BOOK, -800, -950): "off", (FEATHER, -800, -950): "off", (BOOK, *BARREL): "off", (FEATHER, *BARREL): "off",
    (GAS, -450, -250): None if CONTROL else "off",       # the stock-dark cactus
    (CUP, -300, -1000): None if CONTROL else "off",      # the HELD cup
}


def _state(eb, entry):
    ops = [i.op for i in eb.instrs(eb.entry(entry).func_by_tag(0))]
    if 0x81 in ops or 0x85 in ops:
        return "size/amp"                                  # never on an MCF field
    return "off" if 0x80 in ops else None


def _xz(data, eb, entry):
    f0 = eb.entry(entry).func_by_tag(0)
    body = data[f0.abs_start:f0.abs_end]
    out = []
    for var in (0, 4):
        k = body.find(bytes([0x05, 0xD9, var, 0x7D]))
        out.append(struct.unpack_from("<h", body, k + 4)[0] if k >= 0 else None)
    return tuple(out)


def _preflight(g) -> None:
    mcf = LIVE.mapconfig_path(f"EVT_{NAME}")
    g.check(mcf.is_file() and mcf.read_bytes() == STAGED_MCF.read_bytes(),
            "PRE: the deployed MCF is field 1607's, byte for byte", str(mcf))
    data = LIVE.eb_path("us", f"EVT_{NAME}.eb.bytes").read_bytes()
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    got = {"player": _state(eb, pe)}
    for e in eb.entries:
        f0 = None if e.empty else e.func_by_tag(0)
        if f0 is None or e.index == pe:
            continue
        sm = next((i for i in eb.instrs(f0) if i.op == 0x2F), None)
        if sm is None:
            continue
        key = (sm.args[0], *_xz(data, eb, e.index))
        g.check(key not in got, f"PRE: one object per (model, x, z) -- {key}")
        got[key] = _state(eb, e.index)
    print(f"[mcf-rung3] {'control' if CONTROL else 'on'}: deployed Init shadow state: {got}")
    diff = {k: (got.get(k), EXPECT.get(k)) for k in set(got) | set(EXPECT) if got.get(k) != EXPECT.get(k)}
    g.check(got == EXPECT, "PRE: the deployed .eb carries exactly the variant's shadow state per object",
            f"(got, want): {diff}")


SHADOW_PATHS = ("ff9shadow", "FF9Shadow", "DoEventCode", "SetRenderer", "fldmcf")


def _exceptions(g, mark, when: str) -> None:
    ex = g.exceptions_since(mark)
    ours = [e for e in ex if e.through(*SHADOW_PATHS)]
    g.check(not ours, f"A0: no exception through a shadow path ({when})", "; ".join(map(str, ours[:3])))
    tally: dict = {}
    for e in ex:
        if e not in ours:
            tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[mcf-rung3] other exceptions {when}: {tally or 'none'}")


def run(g) -> None:
    _preflight(g)
    g.note("actor shadow rung 3: set pieces on an MCF field" + (" -- CONTROL (pre-fix build)" if CONTROL else ""))
    g.newgame()
    mark = g.log_mark()
    g.warp(FIELD)
    g.settle()
    g.wait_frames(60)
    g.shot("1-spawn")
    g.wait_frames(120)
    g.shot("2-spawn-later")
    _exceptions(g, mark, "entering the field and standing")
