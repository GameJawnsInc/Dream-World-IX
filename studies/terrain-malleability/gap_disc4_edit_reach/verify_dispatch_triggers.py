"""VERIFY (adversarial) -- G8: are WORLD09's object-0 triggers for the 24 disc-4-closed entrance cells really
UNCONDITIONAL (would fire at SC >= 11090), and does WORLD08 really carry none of them?

s6 C reads the case constant out of each cell-tag function (the opD5(39) op7D <case> byte pattern) but never
looks at the rest of the function body. If a 9009 trigger is wrapped in an SC test (opDC(0)), it would not fire
on disc 4 and the "fires in 9009" half of G8 would be wrong. Here: disassemble every WORLD09 (and WORLD08) cell
trigger for the lost cells and list every conditional / opDC(0) reference in its body; also confirm the cell-tag
packing used by s6 (unpack_cell_tag) against ff9.WorldEvent's formula (stock ff9.cs:2233:
0x8000 | (z<<8 & 0x3F00) | (x<<2 & 0xFC) | (id & 3)).
Read-only (pristine dispatchers from p0data via entrance.load_all_dispatchers). Writes out/verify_dispatch_triggers.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
from ff9mapkit.world import entrance as EN          # noqa: E402
from ff9mapkit.eb.model import EbScript              # noqa: E402
from ff9mapkit.eb import disasm as D                 # noqa: E402

# packing calibration against the engine formula
for (x, z, e) in ((11, 7, 1), (37, 28, 1), (47, 39, 3), (0, 0, 2)):
    tag = 0x8000 | (z << 8 & 0x3F00) | (x << 2 & 0xFC) | (e & 3)
    assert EN.unpack_cell_tag(tag) == (x, z, e), (x, z, e)

alld = EN.load_all_dispatchers(game=L.GAME)
s6 = json.loads((L.OUT / "s6_semantic.json").read_text(encoding="utf-8"))
lost = [tuple(c["cell"]) for r in s6["C"]["rows"] for c in r["lost_cells"]]
print("lost cells:", len(lost))
res = {}
for name in ("evt_world_world08", "evt_world_world09"):
    s = EbScript(alld[name]["us"])
    out = {}
    for f in s.entry(0).funcs:
        cell = EN.unpack_cell_tag(f.tag)
        if cell is None or cell not in lost:
            continue
        ins = list(D.iter_code(s.data, f.abs_start, f.abs_end))
        lines = [f"{i.off:05x} {D.op_name(i.op)} {i.args}" for i in ins]
        cond = [l for l in lines if "opDC(0)" in l or " if" in l.lower() or "JMP_IF" in l.upper() or "jmpif" in l.lower()]
        # every op_05 expression that feeds a conditional jump (op_02), minus the stock per-trigger guard
        # (Map.Byte[24]==100 && !Global.Byte[190]) -- the extra gates a trigger carries beyond the stock one
        guard = "opD5(24) op7D(100,0) op20 opD4(190) op0E op27"
        gates = [str(ins[k].args) for k in range(len(ins) - 1)
                 if ins[k].op == 0x05 and ins[k + 1].op == 0x02 and guard not in str(ins[k].args)]
        out[str(cell)] = {"n_instr": len(ins), "sc_or_cond_lines": cond, "extra_gates": gates}
    res[name] = out
    print(name, "triggers for lost cells:", len(out))
for cell, v in sorted(res["evt_world_world09"].items())[:24]:
    print(cell, v["n_instr"], "cond:", v["sc_or_cond_lines"][:4])
(L.OUT / "verify_dispatch_triggers.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
