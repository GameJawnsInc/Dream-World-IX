"""VERIFY (adversarial) -- G8 counterexample hunt: does WORLD08 (the disc-4 free-roam dispatcher) reach the
24 closed places by some OTHER path than an object-0 cell trigger at the same cell?

(a) every occurrence of the Map.Byte[39]=<case> ASSIGNMENT (opD5(39) op7D <case> op2C) anywhere in WORLD08 vs
    WORLD09, with the entry/function/tag that holds it -> do the closed places' cases (48 Esto Gaza, 28 Desert
    Palace, 33 Conde Petie, 4/12/9/7 Ice Cavern, 8 South Gate, 15 North Gate, 35/36 Conde Petie path, 93 Cleyra)
    appear in WORLD08 at all, and where?
(b) does WORLD08 have a trigger at the same (x, z) under a DIFFERENT event id?
Read-only. Writes out/verify_w08_cases.json.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
from ff9mapkit.world import entrance as EN          # noqa: E402
from ff9mapkit.eb.model import EbScript              # noqa: E402

alld = EN.load_all_dispatchers(game=L.GAME)
s6 = json.loads((L.OUT / "s6_semantic.json").read_text(encoding="utf-8"))
lost = [tuple(c["cell"]) for r in s6["C"]["rows"] for c in r["lost_cells"]]
lost_cases = sorted({c["w09_case"] for r in s6["C"]["rows"] for c in r["lost_cells"] if isinstance(c["w09_case"], int)})
res = {"lost_cases": lost_cases}
for name in ("evt_world_world08", "evt_world_world09"):
    s = EbScript(alld[name]["us"])
    where = defaultdict(list)
    xz_trig = defaultdict(list)
    for ei in range(s.entry_count if hasattr(s, "entry_count") else 64):
        try:
            e = s.entry(ei)
        except Exception:
            break
        if e is None or not getattr(e, "funcs", None):
            continue
        for f in e.funcs:
            body = s.data[f.abs_start:f.abs_end]
            j = body.find(EN._BYTE39_PAT)
            while j >= 0:
                # ASSIGNMENT only: opD5(39) op7D <lo hi> op2C (B_LET). The bare D5 27 7D prefix also matches a
                # COMPARISON (e.g. opD5(39) op7D(16,0) op1A = Map.Byte[39] <= 16 in entry-1 tag-11's range lookup)
                if j + 6 <= len(body) and body[j + 5] == 0x2C:
                    case = body[j + 3] | (body[j + 4] << 8)
                    cell = EN.unpack_cell_tag(f.tag) if ei == 0 else None
                    where[case].append({"entry": ei, "tag": f.tag, "cell": cell})
                j = body.find(EN._BYTE39_PAT, j + 1)
            if ei == 0:
                cell = EN.unpack_cell_tag(f.tag)
                if cell:
                    xz_trig[(cell[0], cell[1])].append(cell[2])
    res[name] = {"cases_present": {c: where.get(c, []) for c in lost_cases},
                 "same_xz_other_event": {str(c): xz_trig.get((c[0], c[1]), []) for c in lost}}
    print(name)
    for c in lost_cases:
        print("  case", c, "->", where.get(c, [])[:4])
    print("  lost cells with ANY trigger at same (x,z):",
          [(c, xz_trig[(c[0], c[1])]) for c in lost if xz_trig.get((c[0], c[1]))])
(L.OUT / "verify_w08_cases.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
