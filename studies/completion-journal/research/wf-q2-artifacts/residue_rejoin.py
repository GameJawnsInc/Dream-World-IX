"""Re-join the residue with WIDER latch shapes than the census's GLOB-bit-only rule.

Shapes tested, per residue grant:
  bytelatch : a GLOB byte/word var both guard-tested and constant-written in the region
  haveitem  : a B_HAVE_ITEM(...) token inside a dominator-chain guard expression
  removeitem: a RemoveItem op in the same region (a TRADE, not a treasure)
  loop      : the grant's block sits in a cycle (repeatable by construction)
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
from ff9mapkit.eb.cfg import FieldFlow, parse_set, OP_SET  # noqa

GR = json.load(open(os.path.join(_HERE, "fold_grants.json"), encoding="utf-8"))
B_HAVE_ITEM = 0x64
REMOVE_ITEM_OP = 0x49


def guard_set_instrs(fl, b):
    """The SET statements that produce each dominator-chain guard condition for block b."""
    out = []
    mask = fl._dom[b]
    d = 0
    while mask:
        if mask & 1:
            blk = fl.blocks[d]
            if d != fl.entry and len(blk.preds) == 1:
                p = blk.preds[0]
                if fl._dom[p]:
                    pb = fl.blocks[p]
                    if len(pb.instrs) >= 2 and pb.instrs[-2].op == OP_SET:
                        out.append(pb.instrs[-2])
        mask >>= 1
        d += 1
    return out


def main():
    b = EventBundle()
    cache = {}
    tab = collections.Counter()
    detail = []
    for g in GR:
        if g["cls"] not in ("bare", "sc-window", "ambiguous", "unresolved"):
            continue
        if not g.get("fold_live", True):
            tab[(g["cls"], "const-dead")] += 1
            continue
        fid = g["field"]
        if fid not in cache:
            eb = EbScript.from_bytes(b.eb_for_id(fid))
            cache[fid] = (eb, FieldFlow.build(eb))
        eb, ff = cache[fid]
        raw = eb.data
        found = None
        for (ei, fi), fl in ff.flows.items():
            if ei != g["entry"]:
                continue
            blk = fl.block_at(g["off"])
            if blk is not None:
                found = (fl, blk)
                break
        if found is None:
            tab[(g["cls"], "?noblock")] += 1
            continue
        fl, blk = found
        root = fl.innermost_guard_block(blk)
        region = set(fl.dominated_by(root)) if root is not None else {blk}
        # byte/word GLOB latch: written const in region AND tested in a guard
        writes = {}
        for st, wb in fl.iter_sets(raw):
            if wb in region and st.kind == "assign" and st.source == 0 \
                    and st.vtype in (4, 5, 6, 7) and st.value is not None:
                writes.setdefault(st.index, set()).add(st.value)
        tested = set()
        haveitem = False
        for ins in guard_set_instrs(fl, blk):
            body = raw[ins.off:ins.end]
            if B_HAVE_ITEM in body:
                haveitem = True
            stt = parse_set(raw, ins)
            for c in stt.conds:
                if c.source == 0 and c.vtype in (4, 5, 6, 7) and not c.is_scenario:
                    tested.add(c.index)
        both = set(writes) & tested
        removeitem = any(i.op == REMOVE_ITEM_OP
                         for bi in region for i in fl.blocks[bi].instrs)
        # cycle test: is blk reachable from itself?
        fwd = fl._fwd_reach()
        in_loop = bool(sum((fwd[s] >> blk) & 1 for s, _c in fl.blocks[blk].succs))
        shape = ("bytelatch-1" if len(both) == 1 else
                 "bytelatch-many" if len(both) > 1 else
                 "haveitem" if haveitem else
                 "trade(removeitem)" if removeitem else
                 "in-loop" if in_loop else "none")
        tab[(g["cls"], shape)] += 1
        detail.append({**{k: g[k] for k in ("field", "entry", "func", "off", "cls")},
                       "label": g.get("label") or g["kind"], "shape": shape,
                       "bytelatch": sorted(both), "haveitem": haveitem,
                       "removeitem": removeitem, "in_loop": in_loop})
    for k in sorted(tab):
        print("%-11s %-20s %d" % (k[0], k[1], tab[k]))
    json.dump(detail, open(os.path.join(_HERE, "residue_rejoin.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
