"""Re-run the treasure_join census, adding a constant-fold reachability verdict per grant."""
from __future__ import annotations
import json, os, sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-completion-journal-research-d86041"
for p in (os.path.join(_REPO, "ff9mapkit"), _REPO, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from ff9mapkit.extract import EventBundle, ID_TO_EVT   # noqa
from ff9mapkit.eb import EbScript                      # noqa
from ff9mapkit.eb.cfg import FieldFlow                 # noqa
from ff9mapkit import forkreport as FR                 # noqa
from constfold import folded_reach                     # noqa

CENSUS = os.path.join(_REPO, "studies", "completion-journal", "research", "treasure_join.json")


def main():
    census = json.load(open(CENSUS, encoding="utf-8"))
    by_site = {}
    for g in census["grants"]:
        by_site[(g["field"], g["entry"], g["off"])] = g

    bundle = EventBundle()
    out = []
    per_field_reach = {}
    for fid in sorted({g["field"] for g in census["grants"]}):
        try:
            eb = EbScript.from_bytes(bundle.eb_for_id(fid))
            ff = FieldFlow.build(eb)
        except Exception as e:
            per_field_reach[fid] = None
            continue
        for (ei, fi), fl in ff.flows.items():
            reach = folded_reach(fl, eb.data)
            for blk in fl.blocks:
                for ins in blk.instrs:
                    key = (fid, ei, ins.off)
                    if key in by_site:
                        g = dict(by_site[key])
                        g["fold_live"] = blk.index in reach
                        out.append(g)
    known = {(g["field"], g["entry"], g["off"]) for g in out}
    missing = [g for g in census["grants"] if (g["field"], g["entry"], g["off"]) not in known]

    tab = Counter()
    for g in out:
        tab[(g["cls"], g["fold_live"])] += 1
    print("class            live  dead")
    classes = sorted({c for c, _ in tab})
    for c in classes:
        print("%-14s %5d %5d" % (c, tab[(c, True)], tab[(c, False)]))
    print("missing-from-scan:", len(missing))
    json.dump(out, open(os.path.join(_HERE, "fold_grants.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
