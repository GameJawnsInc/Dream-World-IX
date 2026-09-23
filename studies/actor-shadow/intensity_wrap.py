"""THE INTENSITY WRAP -- does an authored shadow intensity of 16-31 wrap in-game, as the engine source says?

    py tools/deploy_field.py studies/actor-shadow/bench/intensity_wrap_a.field.toml --id 30922 --name SHWR --text-block 30922 --mod-folder FF9CustomMap
    WRAP_RUN=a py tools/play.py studies/actor-shadow/intensity_wrap.py --label shadow-wrap-a
      (then the same with intensity_wrap_b / WRAP_RUN=b, and intensity_wrap_control / WRAP_RUN=control)
    py studies/actor-shadow/measure_intensity_wrap.py <run a> <run b> <control run> --out sheet.png

The kit emits SetShadowAmplifier(intensity << 3); the opcode's argument is one byte, so 0-31 all ENCODE.
The engine stores it as an Int32 amp and DRAWS the blob in colour (Byte)(amp * 2)
(EventEngine.ProcessEvents.cs:612), so intensity i >= 16 should draw exactly as i - 16:
16 -> colour 0 (the same as intensity 0), 31 -> colour 240 (the same as 15).

Bench studies/actor-shadow/bench/intensity_wrap_*.field.toml (30922): four size-9 GEO_NPC_F0_CSO NPCs at
the rung-0 bench's calibrated slots; runs A and B swap the intensities between slots, so every wrap claim is a
SAME-SLOT comparison across two runs (see the bench header). The player casts nothing in any run.

PRE  the DEPLOYED .eb (what the engine will run, not what the build says) carries exactly this run's
     SetShadowSize(9, 9) + SetShadowAmplifier(i << 3) per NPC, and no shadow op on the player
A0   no exception through a shadow path, in either log. Every other exception is reported by name + count.
F1   the spawn frame, twice (1-spawn, 2-spawn-later: the second is this run's own repeat)
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
from ff9mapkit.content.ladder import find_player_entry  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402

FIELD = 30922
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
EB_FILE = (GAME / "FF9CustomMap" / "StreamingAssets" / "Assets" / "Resources" / "CommonAsset" / "EventEngine"
           / "EventBinary" / "Field" / "us" / "EVT_SHWR.eb.bytes")

RUN = os.environ.get("WRAP_RUN", "").lower()
if RUN not in ("a", "b", "control"):
    raise SystemExit("set WRAP_RUN=a|b|control (and deploy the matching bench/intensity_wrap_<run>.field.toml)")
BENCH = HERE / "bench" / f"intensity_wrap_{RUN}.field.toml"
_RAW = tomllib.loads(BENCH.read_text(encoding="utf-8"))
POS = {n["name"]: tuple(n["pos"]) for n in _RAW["npc"]}
# name -> the (SetShadowSize arg, SetShadowAmplifier arg) this run's deployed Init must carry; None = no ops
EXPECT = {"player": None}
for n in _RAW["npc"]:
    sh = n.get("shadow")
    EXPECT[n["name"]] = None if sh is False else (sh["size"], sh["intensity"] << 3)


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
    print(f"[shadow-wrap {RUN}] deployed Init shadow ops: {got}")
    g.check(got == want, f"PRE: the deployed .eb carries exactly run {RUN.upper()}'s shadow ops per actor "
            "(size, amp) and none on the player", f"{got} vs {want}")


def run(g) -> None:
    _preflight(g)
    g.note(f"actor shadow intensity wrap -- run {RUN.upper()}")
    g.newgame()
    mark = g.log_mark()
    g.warp(FIELD)
    g.settle()
    g.wait_frames(60)                                   # a few render frames past the Init
    g.shot("1-spawn")
    g.wait_frames(60)
    g.shot("2-spawn-later")
    _exceptions(g, mark)


SHADOW_PATHS = ("ff9shadow", "FF9Shadow", "DoEventCode", "SetRenderer", "fldmcf")


def _exceptions(g, mark) -> None:
    ex = g.exceptions_since(mark)
    ours = [e for e in ex if e.through(*SHADOW_PATHS)]
    g.check(not ours, "A0: no exception through a shadow path", "; ".join(map(str, ours[:3])))
    tally: dict = {}
    for e in ex:
        if e not in ours:
            tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[shadow-wrap {RUN}] other exceptions (compare the control run): {tally or 'none'}")
