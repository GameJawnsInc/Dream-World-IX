"""Independent audit of treasure_join.py: how many counted grant sites survive
CONSTANT-FOLDED control flow (the FF9 reward macro emits dead template arms)?

cfg.FuncFlow builds JMP_IFNOT/JMP_IF succs as [fallthrough, jump_target].
"""
import json, os, sys, collections
REPO = r"C:\gd\Dream-World-IX\.claude\worktrees\ff9-completion-journal-research-d86041"
sys.path.insert(0, os.path.join(REPO, "ff9mapkit"))
from ff9mapkit.extract import EventBundle, ID_TO_EVT
from ff9mapkit.eb import EbScript
from ff9mapkit.eb.cfg import FieldFlow
from ff9mapkit import forkreport as FR

ADD_ITEM, ADD_GIL = 0x48, 0xCE
JIFN, JIF, SET = 0x02, 0x03, 0x05


def const_of_set(raw, ins):
    """value if this SET is a bare 16-bit literal (`05 7D lo hi 7F`), else None."""
    if ins.op != SET or ins.end - ins.off != 5:
        return None
    if raw[ins.off + 1] != 0x7D or raw[ins.off + 4] != 0x7F:
        return None
    return raw[ins.off + 2] | (raw[ins.off + 3] << 8)


def folded_reachable(fl, raw):
    seen, stack = {fl.entry}, [fl.entry]
    while stack:
        b = stack.pop()
        blk = fl.blocks[b]
        edges = list(blk.succs)
        last = blk.instrs[-1] if blk.instrs else None
        if last is not None and last.op in (JIFN, JIF) and len(blk.instrs) >= 2 \
                and len(edges) == 2:
            cv = const_of_set(raw, blk.instrs[-2])
            if cv is not None:
                taken = (cv == 0) if last.op == JIFN else (cv != 0)
                edges = [edges[1]] if taken else [edges[0]]
        for (s, _c) in edges:
            if s not in seen:
                seen.add(s)
                stack.append(s)
    return seen


def main():
    bundle = EventBundle()
    rows = []
    stats = collections.Counter()
    for fid in sorted(ID_TO_EVT):
        try:
            data = bundle.eb_for_id(fid)
            if not data:
                continue
            eb = EbScript.from_bytes(data)
            ff = FieldFlow.build(eb)
        except Exception:
            continue
        raw = eb.data
        for key, fl in ff.flows.items():
            live = folded_reachable(fl, raw)
            for blk in fl.blocks:
                if fl._dom[blk.index] == 0:
                    continue
                for ins in blk.instrs:
                    if ins.op not in (ADD_ITEM, ADD_GIL):
                        continue
                    is_item = ins.op == ADD_ITEM
                    lit = None
                    if not (ins.arg_is_expr and ins.arg_is_expr[0]) and ins.args \
                            and isinstance(ins.args[0], int):
                        lit = int(ins.args[0])
                    if is_item and lit is not None and (lit == FR.NO_ITEM
                                                        or FR.item_inert(lit)):
                        continue
                    alive = blk.index in live
                    rows.append({"field": fid, "key": list(key), "off": ins.off,
                                 "kind": "item" if is_item else "gil",
                                 "lit": lit, "live": alive})
                    stats["total"] += 1
                    stats[("item" if is_item else "gil") +
                          ("_live" if alive else "_DEAD")] += 1
    gl = [r for r in rows if r["kind"] == "gil" and r["lit"] is not None]
    sig = sum(1 for r in gl if 16776216 <= r["lit"] <= 16776216 + 999)
    print(json.dumps({
        "stats": dict(sorted(stats.items())),
        "gil_literal_rows": len(gl),
        "gil_literal_in_item_id_minus_1000_band": sig,
        "gil_literal_plausible_amounts(1..99999)": sum(
            1 for r in gl if 1 <= r["lit"] <= 99999),
    }, indent=1))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "fold.json"), "w") as fh:
        json.dump(rows, fh)


main()
