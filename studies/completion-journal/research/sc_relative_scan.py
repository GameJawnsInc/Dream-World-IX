"""THROWAWAY -- reconcile "7 fields" (CENSUS_DIGEST.md:15) vs "2 relative" (narrative-state
PLAN.md) ScenarioCounter RELATIVE-write counts. ScenarioCounter = Global word idx 0, vtype 6/7,
source 0 (EventState.cs:16-18). A RELATIVE/computed write is kind=='assign' at that address with
value is None (computed RHS) OR pure is False (a compound += &= etc, even if constant-folded).

Run from ff9mapkit/:  py ../studies/completion-journal/research/sc_relative_scan.py
"""
from __future__ import annotations
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))   # .../ff9-completion-journal-research-d86041
for p in (os.path.join(_REPO, "ff9mapkit"), _REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

from ff9mapkit.extract import EventBundle, ID_TO_EVT                       # noqa: E402
from ff9mapkit.eb import EbScript                                          # noqa: E402
from ff9mapkit.eb.cfg import FieldFlow, parse_set, OP_SET                  # noqa: E402
from ff9mapkit.eb.disasm import pretty_expr                                # noqa: E402

ROOM = {}
for ln in open(os.path.join(_REPO, "reference", "field-manifest.tsv"), encoding="utf-8"):
    p = ln.rstrip("\n").split("\t")
    if len(p) >= 3 and p[1].strip().isdigit():
        ROOM.setdefault(int(p[1]), p[2].strip())

bundle = EventBundle()
abs_n = rel_n = fields_scanned = 0
rel_sites = []
for fid in sorted(ID_TO_EVT):
    data = bundle.eb_for_id(fid)
    if not data:
        continue
    try:
        eb = EbScript.from_bytes(data)
        ff = FieldFlow.build(eb)
    except Exception:
        continue
    fields_scanned += 1
    for key, fl in ff.flows.items():
        ei, fi = key
        ftag = eb.entries[ei].funcs[fi].tag
        for st, blk in fl.iter_sets(eb.data):
            if st.kind != "assign" or st.source != 0 or st.vtype not in (6, 7) or st.index != 0:
                continue
            if st.value is not None and st.pure:
                abs_n += 1
                continue
            rel_n += 1
            expr, _ = pretty_expr(eb.data, st.off + 1)
            rel_sites.append(dict(field=fid, name=ROOM.get(fid, "?"), entry=ei, func=ftag,
                                   off=st.off, op_token=st.op_token, value=st.value,
                                   pure=st.pure, expr=expr))

print(f"fields_scanned={fields_scanned}  SC assign sites (CFG-reachable only): "
      f"absolute={abs_n} relative={rel_n}")
print()
for s in rel_sites:
    print(f"field {s['field']:5d}  {s['name']:<28s} entry={s['entry']:2d} func_tag={s['func']:3d} "
          f"off=0x{s['off']:X}  op_token={s['op_token']}  value={s['value']}  pure={s['pure']}")
    print(f"    {s['expr']}")

# ---------------------------------------------------------------------------
# cross-check: a LINEAR per-func walk (eb.instrs -- no CFG/dominance filter at all) to see
# whether the reachable-only pass above is dropping anything that lives in CFG-dead code.
abs2 = rel2 = 0
rel_sites2 = []
for fid in sorted(ID_TO_EVT):
    data = bundle.eb_for_id(fid)
    if not data:
        continue
    try:
        eb = EbScript.from_bytes(data)
    except Exception:
        continue
    for e in eb.entries:
        if e.empty:
            continue
        for fi, f in enumerate(e.funcs):
            for ins in eb.instrs(f):
                if ins.op != OP_SET:
                    continue
                st = parse_set(eb.data, ins)
                if st.kind != "assign" or st.source != 0 or st.vtype not in (6, 7) or st.index != 0:
                    continue
                if st.value is not None and st.pure:
                    abs2 += 1
                    continue
                rel2 += 1
                expr, _ = pretty_expr(eb.data, st.off + 1)
                rel_sites2.append(dict(field=fid, name=ROOM.get(fid, "?"), entry=e.index,
                                        func=f.tag, off=st.off, op_token=st.op_token,
                                        value=st.value, pure=st.pure, expr=expr))

print()
print(f"LINEAR (no CFG filter): absolute={abs2} relative={rel2}")
for s in rel_sites2:
    print(f"field {s['field']:5d}  {s['name']:<28s} entry={s['entry']:2d} func_tag={s['func']:3d} "
          f"off=0x{s['off']:X}  op_token={s['op_token']}  value={s['value']}  pure={s['pure']}")
    print(f"    {s['expr']}")
