#!/usr/bin/env python3
"""LOCKED-SPAN (cutscene) root-seed census -- the tightest F3-relevant budget.

The F3 scenario is a host-driven cutscene: the host holds usercontrol=0 (a
DisableMove/UCOFF .. EnableMove/UCON span) and the guest is L1-pinned, re-running the
same script. Within such a scripted span the ONLY thing that can make the guest's window
stream diverge from the host's is a ROOT non-mirrored input READ INSIDE THAT SPAN:
  * RNG    (B_SYSVAR[0])                       -- structural, unfixable by any mirror
  * TIMING (B_FRAME / step / timer)            -- structural
  * INPUT  (B_KEYON / B_KEY*)                  -- L2-mirrorable (host confirm)
  * CHOICE (B_SYSVAR[9] = GetChoose)           -- L2-mirrorable (host choice)
Everything else the span reads -- GLOB (mirrored), MAP (a deterministic function of the
mirrored entry state + the span's own code), party/item (wrapped) -- is equalised, so a
MAP-gated window inside a root-CLEAN locked span converges byte-for-byte.

This is a per-function span (one DisableMove..EnableMove pair). It UNDER-counts cutscenes
that disable control in a parent function and open windows in RunScript'd child functions
(the span/window then live in different functions); such windows fall in the "unlocked"
bucket here and are reported separately. So the locked-span figures are a floor on the
scripted population, not the whole of it -- stated honestly in the findings.

Re-runnable + deterministic. Usage: py spans.py [--json OUT.json]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]
sys.path.insert(0, str(_REPO / "ff9mapkit"))
sys.path.insert(0, str(_HERE.parent))

from ff9mapkit.eb import EbScript                # noqa: E402
from ff9mapkit.extract import EventBundle         # noqa: E402
from ff9mapkit._fieldtable import FIELD_BY_ID     # noqa: E402
import census                                     # noqa: E402

STRUCT_ROOT = {"rng", "frame", "step", "timer"}          # unfixable structural
L2_ROOT = {"keyon", "key", "choice"}                     # L2-mirrorable


def span_root_reads(instrs, s, e):
    """Set of root categories read by any expression operand of instrs within [s, e)."""
    cats = set()
    for ins in instrs:
        if not (s <= ins.off < e):
            continue
        for j, is_expr in enumerate(ins.arg_is_expr):
            if is_expr and isinstance(ins.args[j], str):
                cats |= census.classify_expr(ins.args[j])
    return cats


def run(json_out=None):
    bundle = EventBundle()
    fields = sorted(FIELD_BY_ID)

    n_scanned = 0
    n_spans = 0
    n_spans_struct = 0            # locked spans that read a STRUCTURAL root (rng/timing)
    n_spans_l2 = 0               # locked spans that read an L2 root (input/choice)
    n_spans_clean = 0           # locked spans with NO root read at all
    n_spans_struct_clean = 0    # locked spans with no STRUCTURAL root (may still read input/choice)

    # windows inside locked spans, split by whether their span is structurally clean
    lw_total = 0
    lw_struct_clean = 0          # window in a locked span with zero structural root -> converges under L1+L2
    lw_fully_clean = 0          # window in a locked span with zero root at all -> converges under L1 alone
    lw_class = Counter()        # class of locked-span windows
    lw_class_struct_clean = Counter()   # class among windows whose span is structurally clean

    for fid in fields:
        eb_bytes = bundle.eb_for_id(fid)
        if not eb_bytes:
            continue
        try:
            eb = EbScript.from_bytes(eb_bytes)
        except Exception:
            continue
        n_scanned += 1
        for ent in eb.entries:
            if ent.empty:
                continue
            for func in ent.funcs:
                try:
                    instrs, guards, locked = census.analyze_function(eb, func)
                except Exception:
                    continue
                for (s, e) in locked:
                    n_spans += 1
                    roots = span_root_reads(instrs, s, e)
                    struct = bool(roots & STRUCT_ROOT)
                    l2 = bool(roots & L2_ROOT)
                    n_spans_struct += struct
                    n_spans_l2 += l2
                    if not roots:
                        n_spans_clean += 1
                    if not struct:
                        n_spans_struct_clean += 1
                    for ins in instrs:
                        if ins.op in census.WIN_OPS and s <= ins.off < e:
                            lw_total += 1
                            ti = census.WIN_TEXTID_IDX[ins.op]
                            tcats = census.classify_expr(ins.args[ti]) if (ti < len(ins.arg_is_expr)
                                                                           and ins.arg_is_expr[ti]) else set()
                            gcats, _n, _m = census.guards_for(ins.off, guards)
                            lab = census.primary_label(gcats | tcats)
                            lw_class[lab] += 1
                            if not struct:
                                lw_struct_clean += 1
                                lw_class_struct_clean[lab] += 1
                            if not roots:
                                lw_fully_clean += 1

    out = {
        "n_scanned": n_scanned, "n_spans": n_spans,
        "n_spans_struct(rng/timing)": n_spans_struct,
        "n_spans_l2(input/choice)": n_spans_l2,
        "n_spans_struct_clean": n_spans_struct_clean,
        "n_spans_fully_clean": n_spans_clean,
        "locked_windows_total": lw_total,
        "locked_win_in_struct_clean_span": lw_struct_clean,
        "locked_win_in_fully_clean_span": lw_fully_clean,
        "locked_win_class": dict(lw_class.most_common()),
        "locked_win_class_struct_clean": dict(lw_class_struct_clean.most_common()),
    }
    _print(out)
    if json_out:
        Path(json_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\n[json -> {json_out}]")
    return out


def _pct(n, d):
    return f"{100.0*n/d:.1f}%" if d else "n/a"


def _print(o):
    P = print
    P("=" * 78)
    P("LOCKED-SPAN (CUTSCENE) ROOT-SEED CENSUS -- the tight F3 budget")
    P("=" * 78)
    P(f"fields: {o['n_scanned']}   same-function DisableMove..EnableMove spans: {o['n_spans']}")
    P(f"  spans reading a STRUCTURAL root (rng/timing): {o['n_spans_struct(rng/timing)']} "
      f"({_pct(o['n_spans_struct(rng/timing)'], o['n_spans'])})")
    P(f"  spans reading an L2 root (input/choice):      {o['n_spans_l2(input/choice)']} "
      f"({_pct(o['n_spans_l2(input/choice)'], o['n_spans'])})")
    P(f"  spans STRUCTURALLY clean (no rng/timing):     {o['n_spans_struct_clean']} "
      f"({_pct(o['n_spans_struct_clean'], o['n_spans'])})")
    P(f"  spans FULLY clean (no root at all):           {o['n_spans_fully_clean']} "
      f"({_pct(o['n_spans_fully_clean'], o['n_spans'])})")
    P("")
    P(f"windows inside a locked span: {o['locked_windows_total']}")
    P(f"  in a STRUCTURALLY clean span (converge under L1+L2): {o['locked_win_in_struct_clean_span']} "
      f"({_pct(o['locked_win_in_struct_clean_span'], o['locked_windows_total'])})")
    P(f"  in a FULLY clean span (converge under L1 alone):     {o['locked_win_in_fully_clean_span']} "
      f"({_pct(o['locked_win_in_fully_clean_span'], o['locked_windows_total'])})")
    P("")
    P("  class breakdown of ALL locked-span windows:")
    for lab, n in o["locked_win_class"].items():
        P(f"     {lab:14s} {n:6d}  {_pct(n, o['locked_windows_total'])}")
    P("  class breakdown of locked-span windows in STRUCTURALLY CLEAN spans (MAP here = converges):")
    tot = sum(o["locked_win_class_struct_clean"].values())
    for lab, n in o["locked_win_class_struct_clean"].items():
        P(f"     {lab:14s} {n:6d}  {_pct(n, tot)}")
    P("=" * 78)


if __name__ == "__main__":
    jout = None
    if "--json" in sys.argv:
        jout = sys.argv[sys.argv.index("--json") + 1]
    run(jout)
