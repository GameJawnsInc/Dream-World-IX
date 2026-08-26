"""Per-CALL-SITE join for residue grants that live in a called subroutine.

FieldFlow.ctx propagates the INTERSECTION of every in-edge into a function, and an
unguarded InitObject arm-edge (which feeds every func of the entry) zeroes it. Ask
instead: at each RunScript call site that reaches this grant, does the CALLER supply a
single GLOB bit that is both tested ==0 and written =1 in the call's guarded region?
"""
from __future__ import annotations
import json, os, sys, collections

_REPO = r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-completion-journal-research-d86041"
_HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(_REPO, "ff9mapkit"), _REPO, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from ff9mapkit.extract import EventBundle              # noqa
from ff9mapkit.eb import EbScript                      # noqa
from ff9mapkit.eb.cfg import FieldFlow, RUNSCRIPT_OPS  # noqa
from constfold import folded_reach                     # noqa

TH = (set(range(896 * 8, 961 * 8)) | set(range(966 * 8, 976 * 8))
      | set(range(182 * 8, 187 * 8)))
GR = json.load(open(os.path.join(_HERE, "fold_grants.json"), encoding="utf-8"))


def caller_latches(eb, ff, src_key, tag):
    """Per call-site latch candidates in src for RunScript(..., tag)."""
    fl = ff.flows[src_key]
    raw = eb.data
    out = []
    reach = folded_reach(fl, raw)
    bit_sets = [(st, wb) for st, wb in fl.iter_sets(raw)
                if st.kind == "assign" and st.source == 0 and st.vtype in (0, 1)
                and st.value == 1 and wb in reach]
    for blk in fl.blocks:
        if blk.index not in reach:
            continue
        for ins in blk.instrs:
            if ins.op not in RUNSCRIPT_OPS or ins.imm(2) != tag:
                continue
            root = fl.innermost_guard_block(blk.index)
            region = set(fl.dominated_by(root)) if root is not None else {blk.index}
            gb = set()
            for _d, conds in fl._raw_guards(blk.index):
                for c in conds:
                    if c.is_glob_bit and c.cmp == "==" and c.value == 0:
                        gb.add(c.index)
            for cond, _a in ff.ctx.get(src_key, {}).items():
                if cond.is_glob_bit and cond.cmp == "==" and cond.value == 0:
                    gb.add(cond.index)
            rw = {st.index for st, wb in bit_sets if wb in region}
            fw = {st.index for st, _wb in bit_sets}
            both = gb & rw
            pick = (sorted(both) if both else sorted(rw) if rw else sorted(gb & fw)
                    if (gb & fw) else sorted(fw) if fw else [])
            out.append((ins.off, pick))
    return out


def main():
    b = EventBundle()
    cache = {}
    tab = collections.Counter()
    rows = []
    for g in GR:
        if g["cls"] not in ("bare", "sc-window") or not g.get("fold_live", True):
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
        calls = [e for e in ine.get(key, []) if not e[2]]
        if not calls:
            tab[(g["cls"], "no-call-edge")] += 1
            continue
        picks = []
        for (src, _guards, _a) in calls:
            picks.extend(caller_latches(eb, ff, src, g["func"]))
        singles = [p for _o, p in picks if len(p) == 1]
        if len(picks) == 1 and len(singles) == 1:
            bit = singles[0][0]
            tab[(g["cls"], "1-callsite-1-bit-TH" if bit in TH else "1-callsite-1-bit")] += 1
            rows.append({**{k: g[k] for k in ("field", "entry", "func", "off", "cls")},
                         "label": g.get("label") or g["kind"], "bit": bit, "th": bit in TH,
                         "callsites": 1})
        elif singles:
            tab[(g["cls"], "n-callsites-each-1-bit(%d)" % min(len(picks), 9))] += 1
            rows.append({**{k: g[k] for k in ("field", "entry", "func", "off", "cls")},
                         "label": g.get("label") or g["kind"],
                         "bits": sorted({p[0] for p in singles}),
                         "callsites": len(picks)})
        else:
            tab[(g["cls"], "callers-give-no-bit")] += 1
    for k in sorted(tab):
        print("%-11s %-28s %d" % (k[0], k[1], tab[k]))
    print()
    for r in rows:
        if r.get("th") or any(x in TH for x in r.get("bits", [])):
            print("  TH %5d e%-3s tag%-3s off%-6s %-16s %s" %
                  (r["field"], r["entry"], r["func"], r["off"], r["label"],
                   r.get("bit", r.get("bits"))))
    json.dump(rows, open(os.path.join(_HERE, "callsite_rows.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
