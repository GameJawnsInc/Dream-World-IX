#!/usr/bin/env python3
"""Dump every object an FF9 field places: model token + group + spawn (x, z) + canonical pose + whether
it attaches to another object. For inspecting composite props -- which objects co-locate, at what poses.

Usage: py tools/dump_field_objects.py <field_id> [<field_id> ...]
"""
import os
import sys
from collections import defaultdict

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import catalog as C
from ff9mapkit import extract
from ff9mapkit._fieldtable import FBG_TO_EVT
from ff9mapkit.eb import EbScript
from ff9mapkit.eb.disasm import iter_code

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_composite_props import entry_info, tok      # reuse the (model, pos, attach) extractor

SET_STAND_ANIM = 0x33


def dump(fid, env, field2evt):
    evt = field2evt.get(fid)
    if not evt:
        print(f"field {fid}: no evt mapping")
        return
    raw = None
    for k, obj in env.container.items():
        kl = k.lower()
        if "field/us/" in kl and kl.endswith(evt.lower() + ".eb.bytes"):
            raw = extract._raw_bytes(obj.read())
            break
    if raw is None:
        print(f"field {fid}: .eb not found")
        return
    eb = EbScript.from_bytes(raw)
    print(f"\n=== field {fid} objects ===")
    bypos = defaultdict(list)
    for i, e in enumerate(eb.entries):
        if e.empty:
            continue
        info = entry_info(raw, e)
        if not info:
            continue
        model, pos, att = info
        f0 = e.func_by_tag(0)
        pose = None
        for ins in iter_code(raw, f0.abs_start, f0.abs_end):
            if ins.op == SET_STAND_ANIM and pose is None:
                pose = int.from_bytes(raw[ins.off + 2:ins.off + 4], "little")
        m = C.model(model)
        print(f"  e{i:<2} {tok(model):5} {(m.group if m else '?'):4} @ {pos!s:16} pose={pose} "
              f"{'ATTACH' if att else ''}")
        bypos[pos].append(tok(model))
    co = {p: v for p, v in bypos.items() if len(v) > 1}
    if co:
        print("  co-located:", co)


def main():
    fids = [int(a) for a in sys.argv[1:]]
    field2evt = {rec[0]: rec[1] for rec in FBG_TO_EVT.values()}
    env = extract._unitypy().load(str(extract._streaming_assets() / extract._events_bundle()))
    for fid in fids:
        dump(fid, env, field2evt)


if __name__ == "__main__":
    main()
