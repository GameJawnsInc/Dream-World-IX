"""How much residue would the DOCUMENTED-but-unimplemented same-function fallback recover?

treasure_join.py's module docstring says the write side falls back to
"anywhere in the same function"; the code only ever uses `region_writes`
(func_writes is used solely for the latch-guard sanity check). Measure the gap,
restricted to fold-live grants and fold-live writes.
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
from constfold import folded_reach                 # noqa

TH = (set(range(896 * 8, 961 * 8)) | set(range(966 * 8, 976 * 8))
      | set(range(182 * 8, 187 * 8)))
GR = json.load(open(os.path.join(_HERE, "fold_grants.json"), encoding="utf-8"))


def main():
    b = EventBundle()
    cache = {}
    tab = collections.Counter()
    rows = []
    for g in GR:
        if g["cls"] not in ("bare", "sc-window", "ambiguous"):
            continue
        if not g.get("fold_live", True):
            continue
        fid = g["field"]
        if fid not in cache:
            eb = EbScript.from_bytes(b.eb_for_id(fid))
            cache[fid] = (eb, FieldFlow.build(eb))
        eb, ff = cache[fid]
        target = None
        for (ei, fi), fl in ff.flows.items():
            if ei != g["entry"]:
                continue
            if fl.block_at(g["off"]) is not None:
                target = (ei, fi, fl)
                break
        if target is None:
            continue
        ei, fi, fl = target
        reach = folded_reach(fl, eb.data)
        fw = {st.index for st, wb in fl.iter_sets(eb.data)
              if st.kind == "assign" and st.source == 0 and st.vtype in (0, 1)
              and st.value == 1 and wb in reach}
        if len(fw) == 1:
            bit = next(iter(fw))
            tab[(g["cls"], "recovered-TH" if bit in TH else "recovered-nonTH")] += 1
            rows.append({**{k: g[k] for k in ("field", "entry", "func", "off", "cls")},
                         "label": g.get("label") or g["kind"], "bit": bit,
                         "th": bit in TH})
        elif len(fw) > 1:
            tab[(g["cls"], "still-ambiguous(%d)" % min(len(fw), 9))] += 1
        else:
            tab[(g["cls"], "no-bit-write-in-func")] += 1
    for k in sorted(tab):
        print("%-11s %-24s %d" % (k[0], k[1], tab[k]))
    print()
    print("recovered TH-scored rows:")
    for r in rows:
        if r["th"]:
            print("  %5d e%-3s tag%-3s off%-6s %-16s -> bit %d" %
                  (r["field"], r["entry"], r["func"], r["off"], r["label"], r["bit"]))
    json.dump(rows, open(os.path.join(_HERE, "fallback_rows.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
