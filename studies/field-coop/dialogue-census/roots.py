#!/usr/bin/env python3
"""ROOT-SEED census: separate MAP-gated windows that CONVERGE for free from those that
can genuinely diverge, for the F3 mismatch budget.

Rationale (the load-bearing argument): MAP-scoped flags are DERIVED state. In a pinned,
host-driven scripted scene the guest re-runs the SAME field script from the SAME mirrored
GLOB snapshot, so every MAP flag it writes is a deterministic function of (mirrored GLOB +
the script itself + the ROOT non-mirrored inputs the script reads). If a field reads NO
root non-mirrored input, its entire MAP state -- and therefore every MAP-gated window --
evolves byte-identically on both machines and CANNOT drive an F3 alignment-key mismatch,
even though the naive window-class census labels those windows "MAP".

Root non-mirrored inputs (the only things a scripted span can read that the mirror does
not equalise):
  * RNG      -- B_SYSVAR[0] = Comn.random8()                       (structural, unfixable)
  * TIMING   -- B_FRAME / B_SYSVAR[7]=step / B_SYSVAR[{17,20,21}]=timer   (structural)
  * INPUT    -- B_KEYON / B_KEY* (the guest's own controller)      (L2-mirrorable via host confirm)
  * CHOICE   -- B_SYSVAR[9] = GetChoose (the dialogue pick)        (L2-mirrorable)
GLOB / party / item reads are mirror-equalised (never a root divergence).

So a field whose scripts read ZERO of {RNG, TIMING} has MAP state that converges for free
UNDER L1+L2 (input+choice mirrored); a field that also reads zero {INPUT, CHOICE} converges
for free under L1 ALONE. This script counts both populations, corpus-wide.

Re-runnable + deterministic. Usage: py roots.py [--json OUT.json]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]
sys.path.insert(0, str(_REPO / "ff9mapkit"))
sys.path.insert(0, str(_HERE.parent))          # so we can reuse census.py's classifiers

from ff9mapkit.eb import EbScript                # noqa: E402
from ff9mapkit.extract import EventBundle         # noqa: E402
from ff9mapkit._fieldtable import FIELD_BY_ID     # noqa: E402
import census                                     # noqa: E402  (classify_expr, analyze_function, ...)

RNG = {"rng"}
TIMING = {"frame", "step", "timer"}
INPUTC = {"keyon", "key", "choice"}


def field_root_reads(eb: EbScript):
    """Set of root-input categories read ANYWHERE in this field's scripts, plus the count of
    each window class (reuses census.analyze_function so the guard model is identical)."""
    roots = set()
    win_class = Counter()
    n_win = 0
    for e in eb.entries:
        if e.empty:
            continue
        for func in e.funcs:
            try:
                instrs, guards, locked = census.analyze_function(eb, func)
            except Exception:
                continue
            # collect root reads from EVERY expression operand in the function (0x05 conds AND
            # any expression argument) -- a root input anywhere in the field can seed MAP state.
            for ins in instrs:
                for j, is_expr in enumerate(ins.arg_is_expr):
                    if is_expr and isinstance(ins.args[j], str):
                        cats = census.classify_expr(ins.args[j])
                        if cats & RNG:
                            roots.add("rng")
                        if cats & TIMING:
                            roots.add("timing")
                        if cats & {"keyon", "key"}:
                            roots.add("input")
                        if "choice" in cats:
                            roots.add("choice")
            for ins in instrs:
                if ins.op in census.WIN_OPS:
                    n_win += 1
                    ti = census.WIN_TEXTID_IDX[ins.op]
                    tcats = census.classify_expr(ins.args[ti]) if (ti < len(ins.arg_is_expr)
                                                                   and ins.arg_is_expr[ti]) else set()
                    gcats, _n, _m = census.guards_for(ins.off, guards)
                    win_class[census.primary_label(gcats | tcats)] += 1
    return roots, win_class, n_win


def run(json_out=None):
    bundle = EventBundle()
    fields = sorted(FIELD_BY_ID)

    n_scanned = 0
    root_field_counts = Counter()          # 'rng'/'timing'/'input'/'choice' -> #fields that read it
    # window populations split by whether the OWNING FIELD is root-clean
    map_win_total = 0
    map_win_in_l1l2_clean = 0              # MAP windows in fields with zero {rng,timing} -> converge under L1+L2
    map_win_in_l1_clean = 0               # MAP windows in fields with zero {rng,timing,input,choice} -> converge under L1 alone
    fields_l1l2_clean = 0                 # fields with zero {rng,timing}
    fields_l1_clean = 0                   # fields with zero {rng,timing,input,choice}
    fields_rng = fields_timing = fields_input = fields_choice = 0
    total_win = 0
    win_in_l1l2_clean_field = 0           # ALL windows whose field is {rng,timing}-clean

    for fid in fields:
        eb_bytes = bundle.eb_for_id(fid)
        if not eb_bytes:
            continue
        try:
            eb = EbScript.from_bytes(eb_bytes)
        except Exception:
            continue
        n_scanned += 1
        roots, win_class, n_win = field_root_reads(eb)
        total_win += n_win
        for r in roots:
            root_field_counts[r] += 1
        if "rng" in roots:
            fields_rng += 1
        if "timing" in roots:
            fields_timing += 1
        if "input" in roots:
            fields_input += 1
        if "choice" in roots:
            fields_choice += 1
        l1l2_clean = not (roots & {"rng", "timing"})
        l1_clean = not (roots & {"rng", "timing", "input", "choice"})
        if l1l2_clean:
            fields_l1l2_clean += 1
            win_in_l1l2_clean_field += n_win
        if l1_clean:
            fields_l1_clean += 1
        nmap = win_class.get("MAP", 0)
        map_win_total += nmap
        map_win_in_l1l2_clean += (nmap if l1l2_clean else 0)
        map_win_in_l1_clean += (nmap if l1_clean else 0)

    out = {
        "n_scanned": n_scanned,
        "total_win": total_win,
        "fields_with_root_read": dict(root_field_counts.most_common()),
        "fields_rng": fields_rng, "fields_timing": fields_timing,
        "fields_input": fields_input, "fields_choice": fields_choice,
        "fields_l1l2_clean(zero rng+timing)": fields_l1l2_clean,
        "fields_l1_clean(zero rng+timing+input+choice)": fields_l1_clean,
        "map_win_total": map_win_total,
        "map_win_in_l1l2_clean_field": map_win_in_l1l2_clean,
        "map_win_in_l1_clean_field": map_win_in_l1_clean,
        "all_win_in_l1l2_clean_field": win_in_l1l2_clean_field,
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
    P("ROOT-SEED CENSUS  --  does a MAP-gated window CONVERGE for free?")
    P("=" * 78)
    P(f"fields scanned: {o['n_scanned']}   total window opens: {o['total_win']}")
    P("")
    P("Fields that read a ROOT non-mirrored input ANYWHERE in their scripts:")
    P(f"    RNG (random8)      : {o['fields_rng']:4d}  ({_pct(o['fields_rng'], o['n_scanned'])} of fields)")
    P(f"    TIMING (frame/step): {o['fields_timing']:4d}  ({_pct(o['fields_timing'], o['n_scanned'])})")
    P(f"    INPUT (keyon/key)  : {o['fields_input']:4d}  ({_pct(o['fields_input'], o['n_scanned'])})")
    P(f"    CHOICE (GetChoose) : {o['fields_choice']:4d}  ({_pct(o['fields_choice'], o['n_scanned'])})")
    P("")
    P(f"Fields structurally clean (ZERO rng+timing anywhere) -> MAP converges under L1+L2:")
    P(f"    {o['fields_l1l2_clean(zero rng+timing)']}  ({_pct(o['fields_l1l2_clean(zero rng+timing)'], o['n_scanned'])} of fields)")
    P(f"Fields clean of ALL root inputs (zero rng+timing+input+choice) -> converge under L1 alone:")
    P(f"    {o['fields_l1_clean(zero rng+timing+input+choice)']}  ({_pct(o['fields_l1_clean(zero rng+timing+input+choice)'], o['n_scanned'])})")
    P("")
    P(f"MAP-gated windows total: {o['map_win_total']}")
    P(f"  in rng+timing-CLEAN fields (converge for free under L1+L2): {o['map_win_in_l1l2_clean_field']} "
      f"({_pct(o['map_win_in_l1l2_clean_field'], o['map_win_total'])} of MAP windows)")
    P(f"  in ALL-root-CLEAN fields (converge under L1 alone):        {o['map_win_in_l1_clean_field']} "
      f"({_pct(o['map_win_in_l1_clean_field'], o['map_win_total'])})")
    P(f"ALL windows living in a rng+timing-clean field: {o['all_win_in_l1l2_clean_field']} "
      f"({_pct(o['all_win_in_l1l2_clean_field'], o['total_win'])} of all windows)")
    P("=" * 78)


if __name__ == "__main__":
    jout = None
    if "--json" in sys.argv:
        jout = sys.argv[sys.argv.index("--json") + 1]
    run(jout)
