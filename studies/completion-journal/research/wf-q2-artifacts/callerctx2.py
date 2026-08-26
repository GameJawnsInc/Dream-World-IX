"""Residue recovery test using FieldFlow's own edge list.

For each 'bare'/'sc-window' grant, separate the in-edges of its function into
CALL edges (RunScript) and ARM edges (InitObject/InitCode/InitRegion), and ask
what the CALL edges alone would prove -- i.e. what ctx throws away when an
unguarded arm edge intersects it out.
"""
from __future__ import annotations
import json, os, sys, collections

_REPO = r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-completion-journal-research-d86041"
_HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(_REPO, "ff9mapkit"), _REPO, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from ff9mapkit.extract import EventBundle          # noqa
from ff9mapkit.eb import EbScript                  # noqa
from ff9mapkit.eb.cfg import FieldFlow             # noqa

GR = json.load(open(os.path.join(_HERE, "fold_grants.json"), encoding="utf-8"))


def main():
    b = EventBundle()
    cache = {}
    tab = collections.Counter()
    detail = []
    for g in GR:
        if g["cls"] not in ("bare", "sc-window", "ambiguous"):
            continue
        fid = g["field"]
        if fid not in cache:
            eb = EbScript.from_bytes(b.eb_for_id(fid))
            ff = FieldFlow.build(eb)
            ine = collections.defaultdict(list)
            for (src, dst, guards, armed) in ff.edges:
                ine[dst].append((src, guards, armed))
            cache[fid] = (eb, ff, ine)
        eb, ff, ine = cache[fid]
        ent = eb.entries[g["entry"]]
        fidx = None
        for i, f in enumerate(ent.funcs):
            if f.abs_start <= g["off"] < f.abs_end:
                fidx = i
        key = (g["entry"], fidx)
        edges = ine.get(key, [])
        calls = [e for e in edges if not e[2]]
        arms = [e for e in edges if e[2]]
        rec = {"field": fid, "entry": g["entry"], "func": g["func"], "off": g["off"],
               "cls": g["cls"], "label": g.get("label") or g["kind"],
               "n_call_edges": len(calls), "n_arm_edges": len(arms),
               "unguarded_arm": any(not e[1] for e in arms)}
        if calls:
            sets = []
            for (src, guards, _a) in calls:
                allc = set(guards) | set(ff.ctx.get(src, {}).keys())
                sets.append(allc)
            inter = sets[0]
            for s in sets[1:]:
                inter &= s
            bits = sorted({c.index for c in inter if c.is_glob_bit and c.cmp == "==" and c.value == 0})
            sc = sorted({c.value for c in inter if c.is_scenario})
            rec["call_bits"] = bits
            rec["call_sc"] = sc
            if len(bits) == 1:
                verdict = "CALLERS-GIVE-1-BIT"
            elif len(bits) > 1:
                verdict = "callers-give-many-bits"
            elif sc:
                verdict = "callers-give-SC"
            else:
                verdict = "callers-give-nothing"
        else:
            verdict = "no-call-edge"
        rec["verdict"] = verdict
        tab[(g["cls"], verdict)] += 1
        detail.append(rec)
    for k, v in sorted(tab.items()):
        print("%-12s %-26s %d" % (k[0], k[1], v))
    json.dump(detail, open(os.path.join(_HERE, "caller_ctx2.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
