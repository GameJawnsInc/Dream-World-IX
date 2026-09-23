"""[[npc]] / [player] do NOT follow STOCK_CASTS -- in-game: a kit actor wearing a model stock's Inits mostly
disable casts its census shadow standing, and the opt-out still casts none.

    py tools/deploy_field.py studies/actor-shadow/bench/npc_default.field.toml --id 30925 --name SHN0 --text-block 30925
    py tools/play.py studies/actor-shadow/npc_default_shadow.py --label shadow-npc-default
    py tools/deploy_field.py studies/actor-shadow/bench/npc_default_control.field.toml --id 30925 --name SHN0 --text-block 30925
    SHADOW_CONTROL=1 py tools/play.py studies/actor-shadow/npc_default_shadow.py --label shadow-npc-default-control
    py studies/actor-shadow/measure_npc_default.py <on run> <control run> --out <sheet.png>

Bench studies/actor-shadow/bench/npc_default.field.toml (30925), on rung 0's floor, camera and actor slots.
Every actor wears a model STOCK_CASTS disables, and none has a shadow key. The player is re-skinned to
Black Waltz 3. The NPCs are the kit's frog, bird and ramuh archetypes, plus a second frog with
shadow = false as the in-frame negative control. The field camera FOLLOWS the player, so only the spawn
frame is pixel-comparable between the run and its control.

PRE  the DEPLOYED .eb (what the engine runs, not what the build says) carries exactly the census ops per
     actor -- SetShadowSize(s, s) + SetShadowAmplifier(i << 3), s/i = content.shadow.params_for(model) --
     and none on frog_off. Actors are keyed by (model, Init x, z).
A0   no exception THROUGH a shadow path, in either log. Every other exception is tallied by name, for the
     control run to compare (field 70's MovePC NullReferenceExceptions predate all of this).
F1   the spawn frame (read by eye, then measured against the control run): a blob under the player,
     the frog, the bird and Ramuh; none under frog_off.
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

from ff9mapkit.build import _npc_model_kwargs, resolve_npc_model  # noqa: E402
from ff9mapkit.content import shadow as SH  # noqa: E402
from ff9mapkit.content.ladder import find_player_entry  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402

FIELD = 30925
CONTROL = os.environ.get("SHADOW_CONTROL") == "1"
BENCH = HERE / "bench" / ("npc_default_control.field.toml" if CONTROL else "npc_default.field.toml")
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
EB_FILE = (GAME / "FF9CustomMap" / "StreamingAssets" / "Assets" / "Resources" / "CommonAsset" / "EventEngine"
           / "EventBinary" / "Field" / "us" / "EVT_SHN0.eb.bytes")

_RAW = tomllib.loads(BENCH.read_text(encoding="utf-8"))


def _model_of(spec: dict) -> int:
    """The model id the BUILD gives this block (its own resolver: archetype / model / creature name)."""
    if "archetype" in spec:
        return int(_npc_model_kwargs(spec)["model"])
    return resolve_npc_model(spec["model"])


def _expected() -> dict:
    """name -> ((model, x, z), (size, amp) or None), from the bench toml + the kit's census."""
    out = {}
    p = _RAW["player"]
    pm = _model_of(p)
    out["player"] = (pm, None if p.get("shadow", True) is False else SH.params_for(pm))
    for n in _RAW["npc"]:
        m = _model_of(n)
        key = (m, int(n["pos"][0]), int(n["pos"][1]))
        out[n["name"]] = (key, None if n.get("shadow", True) is False else SH.params_for(m))
    return {k: (who, None if s is None else (s[0], s[1] << 3)) for k, (who, s) in out.items()}


def _init_shadow(eb, entry):
    ins = list(eb.instrs(eb.entry(entry).func_by_tag(0)))
    sz = [i.args for i in ins if i.op == SH.SET_SHADOW_SIZE]
    am = [i.args[0] for i in ins if i.op == SH.SET_SHADOW_AMP]
    if not sz and not am:
        return None
    if len(sz) != 1 or len(am) != 1 or sz[0][0] != sz[0][1]:
        return ("malformed", tuple(map(tuple, sz)), tuple(am))
    return sz[0][0], am[0]


def _init_key(data, eb, entry):
    """(model, x, z) an NPC Init places: its literal SetModel + the D9(0)/D9(4) consts (build_npc_init)."""
    f0 = eb.entry(entry).func_by_tag(0)
    sm = next((i for i in eb.instrs(f0) if i.op == SH.SET_MODEL), None)
    body = data[f0.abs_start:f0.abs_end]
    xz = []
    for var in (0, 4):
        k = body.find(bytes([0x05, 0xD9, var, 0x7D]))
        xz.append(struct.unpack_from("<h", body, k + 4)[0] if k >= 0 else None)
    return (None if sm is None else sm.imm(0), *xz)


def _preflight(g) -> None:
    data = EB_FILE.read_bytes()
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    want = _expected()
    by_key = {who: name for name, (who, _s) in want.items() if name != "player"}
    got = {"player": (SH.player_model(data), _init_shadow(eb, pe))}
    for e in eb.entries:
        if e.empty or e.index == pe or e.func_by_tag(0) is None:
            continue
        key = _init_key(data, eb, e.index)
        if key[0] is None:
            continue
        got[by_key.get(key, f"?{key}")] = (key, _init_shadow(eb, e.index))
    print(f"[shadow-npc] deployed Init shadow ops: {got}")
    g.check(got == want, "PRE: the deployed .eb carries exactly the census shadow ops per actor "
            "(model-keyed) and none on the opted-out ones", f"{got} vs {want}")


SHADOW_PATHS = ("ff9shadow", "FF9Shadow", "DoEventCode", "SetRenderer", "fldmcf")


def _exceptions(g, mark, when: str) -> None:
    ex = g.exceptions_since(mark)
    ours = [e for e in ex if e.through(*SHADOW_PATHS)]
    g.check(not ours, f"A0: no exception through a shadow path ({when})", "; ".join(map(str, ours[:3])))
    tally: dict = {}
    for e in ex:
        if e not in ours:
            tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[shadow-npc] other exceptions {when} (compare the control run): {tally or 'none'}")


def run(g) -> None:
    _preflight(g)
    g.note("[[npc]]/[player] ignore STOCK_CASTS" + (" -- CONTROL (every actor shadow = false)" if CONTROL else ""))
    g.newgame()
    mark = g.log_mark()                                 # BEFORE the warp: the Inits' shadow ops run on entry
    g.warp(FIELD)
    g.settle()
    g.wait_frames(60)
    g.shot("1-spawn")
    _exceptions(g, mark, "entering the field")
