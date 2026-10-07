"""VERIFIER (forms lane, F3/F4/F17) -- does any stock WORLD dispatcher issue a world->world jump?

The lane's F4 names `WorldMap(<same id>)` (WMAPJUMP 0xB6) from a world .eb as "the clean refresh". In the engine,
WMAPJUMP -> SetNextMap -> FF9ChangeMap (mode 3: only writes FF9World.map.nextMapNo) and returns 5
(DoEventCode.cs:2458-2461, EventEngine.cs:1296-1322). The world tick (WMScriptDirector.HonoUpdate20FPS
:150-162) acts on w_frameMainRoutine results 3 (battle) and 4 (field) only. So a world-originated WorldMap()
should be INERT in stock. This census tests the data side: if shipping world scripts used 0xB6 for a world->world
hop, there would have to be an engine route we missed.

Census over the 13 EVT_WORLD_* 'us' dispatchers (read-only, via the kit's loader + disassembler):
  * every op 0xB6 (WMAPJUMP / WorldMap) and 0x2B (MAPJUMP / Field) -- counts + immediates.
CALIBRATION: 0x2B (Field) must be > 0 (the world enters fields through Field(); if this is 0 the opcode
decode is broken and the 0xB6 count means nothing). RunWorldCode(26) == 18 (same as the lane's script).
Rerun:  py verify_world_eb_mapjumps.py
"""
import sys, collections
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import entrance as E
from ff9mapkit.eb.model import EbScript

alld = E.load_all_dispatchers()
ops = collections.Counter()
b6 = []
n26 = 0
for name in sorted(alld):
    data = alld[name].get("us")
    if not data:
        continue
    s = EbScript(data)
    for e in s.entries:
        for f in e.funcs:
            for i in s.instrs(f):
                if i.op in (0xB6, 0x2B):
                    ops[(name, hex(i.op))] += 1
                    if i.op == 0xB6:
                        b6.append((name, e.index, f.tag, i.args, i.arg_is_expr))
                if i.op == 0xC4 and i.imm(0) == 26 and not i.arg_is_expr[1]:
                    n26 += 1
tot = collections.Counter()
for (n, o), c in ops.items():
    tot[o] += c
print("dispatchers:", len([n for n in alld if alld[n].get("us")]))
print("calibration: RunWorldCode(26, imm) =", n26, "(expected 18)")
assert n26 == 18
print("calibration: total 0x2B Field() =", tot.get("0x2b", 0), "(must be > 0)")
assert tot.get("0x2b", 0) > 0
print("total 0xB6 WorldMap() in world dispatchers =", tot.get("0xb6", 0))
for h in b6[:40]:
    print("   ", h)
