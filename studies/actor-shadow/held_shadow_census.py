"""Where stock puts a HELD object's DisableShadow -- the shape the kit's held prop copies on an MCF field.

    py studies/actor-shadow/held_shadow_census.py

A held object is an `AttachObject` target (matched by uid like `_regen_shadowparams._cast_votes`). For each one
with a literal Init `SetModel`, this reports where the Init's `DisableShadow` (0x80) sits: after `SetModel`?
relative to an `AttachObject` in the same Init? what op follows it? does it dominate every exit? Derived
counts only -- no Square-Enix bytes are printed.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import _regen_shadowparams as R, extract  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402
from ff9mapkit.eb.cfg import CfgError  # noqa: E402

SET_MODEL, DISABLE, ATTACH = 0x2F, 0x80, 0x4C


def main() -> None:
    bundle = extract.EventBundle()
    held = 0
    tally: Counter = Counter()
    after: Counter = Counter()
    for fid in extract.ID_TO_EVT:
        data = bundle.eb_for_id(fid)
        if not data:
            continue
        try:
            eb = EbScript.from_bytes(data)
        except Exception:                                      # noqa: BLE001
            continue
        uids, attached = defaultdict(set), set()
        for e in eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                for ins in eb.instrs(f):
                    if ins.op == R.INIT_OBJECT and ins.imm(0) is not None:
                        uids[ins.imm(0)].add(ins.imm(1) or ins.imm(0))
                    elif ins.op == ATTACH and ins.imm(0) is not None:
                        attached.add(ins.imm(0))
        for e in eb.entries:
            f0 = None if e.empty else e.func_by_tag(0)
            if f0 is None or not ((uids.get(e.index, set()) | {e.index}) & attached):
                continue
            ops = [i.op for i in eb.instrs(f0)]
            if SET_MODEL not in ops:
                continue
            held += 1
            if DISABLE not in ops:
                tally["no DisableShadow in the Init"] += 1
                continue
            d = ops.index(DISABLE)
            tally["DisableShadow after SetModel" if d > ops.index(SET_MODEL) else "DisableShadow BEFORE SetModel"] += 1
            if ATTACH in ops:
                tally["own-Init AttachObject, DisableShadow after it" if d > ops.index(ATTACH)
                      else "own-Init AttachObject, DisableShadow before it"] += 1
            else:
                tally["attached from another entry"] += 1
            try:
                tally["dominates every exit" if R._disables_on_every_path(eb, f0) else "behind a branch"] += 1
            except CfgError:
                tally["flow unreadable"] += 1
            after[f"0x{ops[d + 1]:02X}" if d + 1 < len(ops) else "(end)"] += 1
    print(f"held objects with a literal Init SetModel: {held}")
    for k, v in tally.most_common():
        print(f"  {v:4d}  {k}")
    print("the op right after DisableShadow:")
    for k, v in after.most_common(8):
        print(f"  {v:4d}  {k}")


if __name__ == "__main__":
    main()
