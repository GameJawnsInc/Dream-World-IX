"""Rung-0 dominance census — the narrative-state arc's first instrument.

For every real field's event script (us language), build the per-function CFG + dominator
analysis (``ff9mapkit.eb.cfg``) and emit, for every GLOB story-bit write site, the conditions
PROVEN to hold on the path to it: ScenarioCounter windows, flag gates, and the interesting
sibling ops of its innermost guarded region. Also dumps every literal ScenarioCounter write
with its own guards (estimator E3's raw material).

Run from ``ff9mapkit/`` (so the local package shadows any editable install):

    py ../research/dominance_census.py

Writes ``research/dominance_census.json`` (gitignored — regenerable, derived from the user's
own install) and prints the rung-0 falsifier: the fraction of bit-write sites carrying at
least one dominating ScenarioCounter condition. The scoping baseline (naive same-function
byte-adjacency, 2026-08-03) was 32.6%; the rung-0 prediction is >55%. See
``studies/narrative-state/PLAN.md``.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for p in (os.path.join(_REPO, "ff9mapkit"), _REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

from ff9mapkit.extract import EventBundle, ID_TO_EVT            # noqa: E402
from ff9mapkit.eb import EbScript                               # noqa: E402
from ff9mapkit.eb.cfg import CfgError, FieldFlow, FuncFlow     # noqa: E402
from ff9mapkit.eb._optables import OP_NAMES                     # noqa: E402

# the ops worth recording next to a story-bit write (feeds the classifier's reward-adjacency
# and roster signals). Resolved by NAME so a table renumbering can't silently rot this list.
_INTERESTING_NAMES = {
    "AddItem", "AddGil", "RemoveItem", "InitObject", "InitCode", "InitRegion",
    "Field", "Battle", "BattleEx", "WindowSync", "WindowAsync", "Menu",
    "RemoveParty", "SetPartyReserve", "SetCharacterData", "SetTextVariable",
}
_INTERESTING = {op: name for op, name in OP_NAMES.items() if name in _INTERESTING_NAMES}
_REGION_CAP = 64            # blocks; a bigger guarded region records only the write's own block


def _cond_row(c) -> list:
    val = list(c.value) if isinstance(c.value, tuple) else c.value
    return [c.source, c.vtype, c.index, c.cmp, val]


def _sibling_ops(fl: FuncFlow, block: int) -> list[str]:
    root = fl.innermost_guard_block(block)
    blocks = fl.dominated_by(root) if root is not None else [block]
    if len(blocks) > _REGION_CAP:
        blocks = [block]
    names = set()
    for b in blocks:
        for ins in fl.blocks[b].instrs:
            nm = _INTERESTING.get(ins.op)
            if nm:
                names.add(nm)
    return sorted(names)


def main() -> int:
    bundle = EventBundle()
    bit_sites: list[dict] = []
    sc_sites: list[dict] = []
    stats = defaultdict(int)
    degraded: list[list] = []

    for fid in sorted(ID_TO_EVT):
        try:
            data = bundle.eb_for_id(fid)
            if not data:
                continue
            eb = EbScript.from_bytes(data)
        except Exception:
            stats["fields_unreadable"] += 1
            continue
        stats["fields_scanned"] += 1
        ff = FieldFlow.build(eb)
        for key, reason in ff.degraded.items():
            stats["funcs_degraded"] += 1
            degraded.append([fid, key[0], key[1], reason])
        for key, fl in ff.flows.items():
            ei, fi = key
            ftag = eb.entries[ei].funcs[fi].tag
            stats["funcs_analyzed"] += 1
            for k in ("negated_compound", "condless_branches"):
                stats[k] += fl.stats[k]
            ctx = ff.ctx.get(key, {})
            ctx_direct = [c for c, a in ctx.items() if not a]
            ctx_armed = [c for c, a in ctx.items() if a]
            for st, blk in fl.iter_sets(eb.data):
                if st.kind != "assign" or st.source != 0:
                    continue
                guards = list(fl.guards_of_block(blk) or ()) + ctx_direct
                sc = [c for c in guards if c.is_scenario]
                sc_armed = [c for c in ctx_armed if c.is_scenario]
                flg = [c for c in guards if c.is_glob_bit]
                flg_armed = [c for c in ctx_armed if c.is_glob_bit]
                other = [c for c in guards if not c.is_scenario and not c.is_glob_bit]
                if st.vtype in (0, 1):                      # a GLOB story-bit write
                    stats["bit_write_sites"] += 1
                    if sc:
                        stats["bit_sites_sc_guarded"] += 1
                    if sc or sc_armed:
                        stats["bit_sites_sc_any"] += 1
                    if flg:
                        stats["bit_sites_flag_guarded"] += 1
                    bit_sites.append({
                        "bit": st.index, "value": st.value, "pure": st.pure,
                        "field": fid, "entry": ei, "func": ftag, "off": st.off,
                        "sc": [_cond_row(c) for c in sc],
                        "sc_armed": [_cond_row(c) for c in sc_armed],
                        "flags": [_cond_row(c) for c in flg],
                        "flags_armed": [_cond_row(c) for c in flg_armed],
                        "other": [_cond_row(c) for c in other],
                        "sib": _sibling_ops(fl, blk),
                    })
                elif st.vtype in (6, 7) and st.index == 0 and st.value is not None:
                    stats["sc_write_sites"] += 1
                    sc_sites.append({
                        "value": st.value,
                        "field": fid, "entry": ei, "func": ftag, "off": st.off,
                        "sc": [_cond_row(c) for c in sc],
                        "sc_armed": [_cond_row(c) for c in sc_armed],
                        "flags": [_cond_row(c) for c in flg],
                    })

    # story-site metrics: the byte-23 handshake and the Mognet bands are compiled dispatch
    # noise (77% of raw sites) -- the falsifier is scored on the STORY population
    _HANDSHAKE = set(range(184, 192))
    _MOGNET = set(range(8192, 8712))
    story = [x for x in bit_sites if x["bit"] not in _HANDSHAKE and x["bit"] not in _MOGNET]
    sc_by_func = {}
    for x in sc_sites:
        sc_by_func.setdefault((x["field"], x["entry"], x["func"]), []).append(x["value"])
    n_story = len(story)
    n_direct = sum(1 for x in story if x["sc"])
    n_any = sum(1 for x in story if x["sc"] or x["sc_armed"])
    n_e3 = sum(1 for x in story if (x["field"], x["entry"], x["func"]) in sc_by_func)
    n_all = sum(1 for x in story if x["sc"] or x["sc_armed"]
                or (x["field"], x["entry"], x["func"]) in sc_by_func)
    bits_windowed = {x["bit"] for x in story if x["sc"] or x["sc_armed"]}
    bits_all = {x["bit"] for x in story}
    total = stats["bit_write_sites"]
    guarded = stats["bit_sites_sc_guarded"]
    coverage = (n_all / n_story * 100) if n_story else 0.0

    out = {
        "generator": "research/dominance_census.py",
        "stats": dict(sorted(stats.items())),
        "coverage": {
            "raw_bit_write_sites": total,
            "raw_sc_guarded_sites": guarded,
            "story_sites": n_story,
            "story_sc_direct": n_direct,
            "story_sc_direct_or_armed": n_any,
            "story_e3_colocated_advance": n_e3,
            "story_any_sc_signal": n_all,
            "story_any_sc_signal_pct": round(coverage, 1),
            "naive_baseline_pct_raw_denominator": 32.6,
            "prediction_pct": 55.0,
            "story_distinct_bits": len(bits_all),
            "story_distinct_bits_sc_windowed": len(bits_windowed),
        },
        "degraded_funcs": degraded,
        "bit_sites": bit_sites,
        "sc_sites": sc_sites,
    }
    dest = os.path.join(_HERE, "dominance_census.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)

    print(json.dumps({"stats": out["stats"], "coverage": out["coverage"]}, indent=2))
    print(f"wrote {dest}")
    verdict = "PASS (>55%)" if coverage > 55.0 else "FALSIFIED (<=55%) -- re-plan rung 0"
    print(f"RUNG-0 FALSIFIER: any-SC-signal coverage {coverage:.1f}% of {n_story} story sites -> {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
