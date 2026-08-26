"""For every 'bare' / 'sc-window' grant: what do its RunScript CALL SITES prove?

Tests the hypothesis that FieldFlow.ctx loses the caller's gate because an
unguarded InitObject arm-edge into the same entry intersects it away.
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
from ff9mapkit.eb.cfg import FieldFlow, RUNSCRIPT_OPS  # noqa
from ff9mapkit import eventscan                    # noqa

GR = json.load(open(os.path.join(_HERE, "fold_grants.json"), encoding="utf-8"))


def caller_conds(eb, ff, target_entry, target_tag):
    """Intersection of proven guards over every RunScript site that targets (entry, tag)."""
    sets = []
    sites = 0
    for (ei, fi), fl in ff.flows.items():
        for blk in fl.blocks:
            if fl._dom[blk.index] == 0:
                continue
            for ins in blk.instrs:
                if ins.op not in RUNSCRIPT_OPS:
                    continue
                if ins.imm(2) != target_tag:
                    continue
                uid = ins.imm(1)
                if uid is None:
                    continue
                # cheap uid->slot: default uid == slot
                if uid != target_entry:
                    continue
                sites += 1
                g = fl.guards_at(ins.off) or ()
                own = ff.ctx.get((ei, fi), {})
                allc = set(g) | set(own.keys())
                sets.append(allc)
    if not sets:
        return None, 0
    out = sets[0]
    for s in sets[1:]:
        out &= s
    return out, sites


def main():
    b = EventBundle()
    cache = {}
    tab = collections.Counter()
    detail = []
    for g in GR:
        if g["cls"] not in ("bare", "sc-window"):
            continue
        fid = g["field"]
        if fid not in cache:
            eb = EbScript.from_bytes(b.eb_for_id(fid))
            cache[fid] = (eb, FieldFlow.build(eb))
        eb, ff = cache[fid]
        conds, sites = caller_conds(eb, ff, g["entry"], g["func"])
        if conds is None:
            tab[(g["cls"], "no-call-site")] += 1
            detail.append(dict(g, caller="none"))
            continue
        bits = sorted({c.index for c in conds if c.is_glob_bit and c.cmp == "==" and c.value == 0})
        sc = [c for c in conds if c.is_scenario]
        if len(bits) == 1:
            tab[(g["cls"], "caller-gives-1-bit")] += 1
        elif len(bits) > 1:
            tab[(g["cls"], "caller-gives-many-bits")] += 1
        elif sc:
            tab[(g["cls"], "caller-gives-SC-only")] += 1
        else:
            tab[(g["cls"], "caller-gives-nothing")] += 1
        detail.append(dict(g, caller_sites=sites, caller_bits=bits,
                           caller_sc=[c.value for c in sc]))
    for k, v in sorted(tab.items()):
        print(k, v)
    json.dump(detail, open(os.path.join(_HERE, "caller_ctx.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
