#!/usr/bin/env python3
"""Spot-check the divergence classifier on concrete window sites: for a field id, print each
dialogue window with its enclosing guard condition(s) pretty-printed (Source.Type[index] /
B_SYSVAR[n] / B_KEYON ...), so a human can confirm the census label is byte-accurate.

Usage: py verify.py <field_id> [<field_id> ...]
       py verify.py 563 652 600 --only RNG,TIMING     # filter to a class
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]
sys.path.insert(0, str(_REPO / "ff9mapkit"))
sys.path.insert(0, str(_HERE.parent))

from ff9mapkit.eb import EbScript                # noqa: E402
from ff9mapkit.eb.disasm import pretty_expr, read_code   # noqa: E402
from ff9mapkit.extract import EventBundle, ID_TO_EVT      # noqa: E402
import census                                     # noqa: E402


def pretty_cond(eb, cond_ins):
    """Pretty-print the expression of a 0x05 push instr from its raw bytes."""
    raw = eb.data
    # the expression starts right after the opcode byte (0x05 has no argFlag byte read for <0x10... but
    # read_code forces argFlag=1 for 0x05; the single expr operand begins at cond_ins.off+1).
    try:
        txt, _ = pretty_expr(raw, cond_ins.off + 1)
        return txt
    except Exception:
        return str(cond_ins.args[0]) if cond_ins.args else "?"


def dump(fid, only=None):
    bundle = EventBundle()
    eb_bytes = bundle.eb_for_id(fid)
    if not eb_bytes:
        print(f"field {fid}: no .eb"); return
    eb = EbScript.from_bytes(eb_bytes)
    print("=" * 78)
    print(f"field {fid}  ({ID_TO_EVT.get(fid, '?')})")
    print("=" * 78)
    for ent in eb.entries:
        if ent.empty:
            continue
        for func in ent.funcs:
            instrs, guards, locked = census.analyze_function(eb, func)
            # map guard span -> the 0x05 cond instr for pretty printing
            for ins in instrs:
                if ins.op not in census.WIN_OPS:
                    continue
                ti = census.WIN_TEXTID_IDX[ins.op]
                textid = ins.args[ti] if ti < len(ins.args) else "?"
                gcats, ng, _m = census.guards_for(ins.off, guards)
                lab = census.primary_label(gcats)
                if only and lab not in only:
                    continue
                blk = "BLOCK" if census.WIN_BLOCK[ins.op] else "async"
                inlock = "LOCK" if census.in_span(ins.off, locked) else "    "
                print(f"\n  entry{ent.index} func(tag{func.tag}) @off {ins.off}  "
                      f"{census.WIN_TEXTID_IDX and ''}op 0x{ins.op:02X} {blk} {inlock}  "
                      f"textId={textid}  ->  {lab}  cats={sorted(gcats)}")
                # print the guarding conditions
                shown = 0
                for (s, e, c, kind, hascond) in guards:
                    if s <= ins.off < e and c:
                        # find the 0x05 just before span start
                        cond = None
                        for k in range(len(instrs)):
                            if instrs[k].end == s and k > 0 and instrs[k - 1].op == 0x05:
                                cond = instrs[k - 1]; break
                            if instrs[k].off < s <= instrs[k].end and instrs[k].op in census.COND_JUMPS | census.SWITCH_OPS:
                                # the jump/switch whose span starts at s; its cond is the preceding 0x05
                                idx = instrs.index(instrs[k])
                                if idx > 0 and instrs[idx - 1].op == 0x05:
                                    cond = instrs[idx - 1]
                                break
                        ptxt = pretty_cond(eb, cond) if cond else "?"
                        print(f"        guard[{kind}] cats={sorted(c)}: {ptxt}")
                        shown += 1
                        if shown >= 4:
                            print("        ...")
                            break


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
        args = [a for a in args if a != sys.argv[sys.argv.index("--only") + 1]]
    for a in args:
        dump(int(a), only)
