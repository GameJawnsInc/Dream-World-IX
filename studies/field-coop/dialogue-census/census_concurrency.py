#!/usr/bin/env python3
"""F3 dialogue-lockstep census -- CONCURRENCY / UNIQUENESS / WAIT-IDIOM OUTLIERS.

Third pass. Answers, with numbers:
  Q3  the blocking-wait idiom: canonical patterns + non-canonical OUTLIERS (WAITMES with no matching
      in-function open; winnum==255 sentinel windows; expression winnums).
  Q4  concurrency + the (fldMapNo, winnum, textId) alignment-key uniqueness:
        - winnum is ALWAYS a statically-known immediate (proven: 0 expr sites) in range 0..7.
        - the engine (NewMesWin -> DisposWindowByID) makes a winnum map to AT MOST one LIVE window, so
          winnum alone is the liveness key; the triple is over-specified but always statically resolvable.
        - the real concurrency is CROSS-WINNUM (an ATE poll-loop window on a different winnum while the
          main thread holds a window) + the CROSS-THREAD SAME-WINNUM destructive-replace hazard.
        Measured: fields opening the same winnum from >1 entry; fields opening winATE + plain from
        different entries; per-field distinct-winnum and distinct-entry counts.
  Q5  multi-page: close-then-reopen chains (separate windows) vs [PAGE] within one textId.

Reads window_sites.json (+ window_sites_enriched.json when present). Deterministic + re-runnable.
Rebuilds the per-function open/close sequences from the live .eb so the wait-idiom scan is exact.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit.extract import EventBundle                    # noqa: E402
from ff9mapkit._fieldtable import FIELD_BY_ID                # noqa: E402
from ff9mapkit.eb import EbScript                            # noqa: E402

MES, MESN, MESA, MESAN = 0x1F, 0x20, 0x95, 0x96
WINDOW_OPEN = {MES, MESN, MESA, MESAN}
SYNC_OPS = {MES, MESA}
ASYNC_OPS = {MESN, MESAN}
EX_OPS = {MESA, MESAN}
CLOSE, CLOSEALL, WAITMES = 0x21, 0xEB, 0x54
WINATE = 64


def win_idx(op):
    return (1, 2, 3) if op in EX_OPS else (0, 1, 2)


def imm(ins, i):
    if i >= len(ins.arg_is_expr):
        return None
    return "expr" if ins.arg_is_expr[i] else ins.imm(i)


def main():
    bundle = EventBundle()
    fields = sorted(FIELD_BY_ID)

    # Q3 -- wait idiom
    waitmes_total = 0
    waitmes_no_open_in_func = 0            # WAITMES whose winnum was not opened earlier in the SAME func
    waitmes_expr_winnum = 0
    waitmes_examples_orphan = []          # (fid, entry, tag, winnum) cross-thread waits
    winnum255_windows = 0                 # a window opened directly on the sentinel winnum
    inline_sync = 0                       # MES/MESA -- the opcode itself blocks
    async_then_wait = 0                   # MESN/MESAN followed by WAITMES(same winnum) in-func

    # Q4 -- concurrency / uniqueness
    fields_same_winnum_multi_entry = 0    # a winnum opened from >1 DISTINCT entry (cross-thread reuse)
    fields_ate_plain_diff_entry = 0       # winATE window + plain window opened from DIFFERENT entries
    per_field_distinct_entries_with_windows = {}
    per_field_distinct_winnums = {}
    cross_thread_same_winnum_pairs = 0    # count of (field, winnum) reused across entries
    triple_collisions = 0                 # DISTINCT (winnum,textId) live-key duplicated? (sanity)

    # Q5 -- multi-page
    reopen_runs = Counter()               # consecutive same-winnum reopen run lengths (separate windows)

    for fid in fields:
        data = bundle.eb_for_id(fid)
        if data is None:
            continue
        eb = EbScript.from_bytes(data)
        field_winnum_entries = defaultdict(set)     # winnum -> set(entry.index) that OPEN it
        ate_entries = set()
        plain_entries = set()
        entries_with_windows = set()
        winnums_here = set()
        for entry in eb.entries:
            if entry.empty:
                continue
            for func in entry.funcs:
                instrs = list(eb.instrs(func))
                opened_winnums = set()               # winnums opened so far in THIS func
                run_win = None
                run_len = 0
                for i, ins in enumerate(instrs):
                    op = ins.op
                    if op in WINDOW_OPEN:
                        wi, ui, ti = win_idx(op)
                        w = imm(ins, wi)
                        uf = imm(ins, ui)
                        entries_with_windows.add(entry.index)
                        if w == 255:
                            winnum255_windows += 1
                        if w != "expr" and w is not None:
                            field_winnum_entries[w].add(entry.index)
                            winnums_here.add(w)
                            opened_winnums.add(w)
                        if uf not in (None, "expr") and (uf & WINATE):
                            ate_entries.add(entry.index)
                        else:
                            plain_entries.add(entry.index)
                        if op in SYNC_OPS:
                            inline_sync += 1
                        else:
                            # look ahead for WAITMES(same winnum)
                            for j in range(i + 1, len(instrs)):
                                nj = instrs[j]
                                if nj.op == WAITMES:
                                    ww = imm(nj, 0)
                                    if ww == w:
                                        async_then_wait += 1
                                        break
                                if nj.op in WINDOW_OPEN:
                                    wj, _, _ = win_idx(nj.op)
                                    if imm(nj, wj) == w:
                                        break
                                if nj.op == CLOSE and imm(nj, 0) == w:
                                    break
                        # reopen run
                        if w is not None and w == run_win:
                            run_len += 1
                        else:
                            if run_len >= 2:
                                reopen_runs[run_len] += 1
                            run_win = w
                            run_len = 1
                    elif op == WAITMES:
                        waitmes_total += 1
                        ww = imm(ins, 0)
                        if ww == "expr":
                            waitmes_expr_winnum += 1
                        elif ww not in opened_winnums:
                            waitmes_no_open_in_func += 1
                            if len(waitmes_examples_orphan) < 25:
                                waitmes_examples_orphan.append((fid, entry.index, func.tag, ww))
                if run_len >= 2:
                    reopen_runs[run_len] += 1
        per_field_distinct_entries_with_windows[fid] = len(entries_with_windows)
        per_field_distinct_winnums[fid] = len(winnums_here)
        # winnum opened from >1 entry?
        reused = [w for w, ents in field_winnum_entries.items() if len(ents) > 1]
        if reused:
            fields_same_winnum_multi_entry += 1
            cross_thread_same_winnum_pairs += len(reused)
        # ATE + plain from different entries?
        if ate_entries and plain_entries and (ate_entries - plain_entries):
            fields_ate_plain_diff_entry += 1

    out = {
        "wait_idiom": {
            "inline_sync_blocking (MES/MESA opcode itself waits)": inline_sync,
            "async_then_waitmes (MESN/MESAN + WAITMES same winnum)": async_then_wait,
            "waitmes_total": waitmes_total,
            "waitmes_orphan_cross_thread (no in-func open of that winnum)": waitmes_no_open_in_func,
            "waitmes_expr_winnum": waitmes_expr_winnum,
            "winnum255_sentinel_windows": winnum255_windows,
            "orphan_examples (fid,entry,tag,winnum)": waitmes_examples_orphan[:25],
        },
        "concurrency_uniqueness": {
            "fields_same_winnum_opened_from_multiple_entries": fields_same_winnum_multi_entry,
            "total_(field,winnum)_reused_across_entries": cross_thread_same_winnum_pairs,
            "fields_ate_and_plain_from_different_entries": fields_ate_plain_diff_entry,
            "max_distinct_entries_with_windows_in_a_field": max(per_field_distinct_entries_with_windows.values()),
            "max_distinct_winnums_in_a_field": max(per_field_distinct_winnums.values()),
        },
        "multipage": {
            "separate_window_reopen_runs (len>=2 consecutive same-winnum)": dict(sorted(reopen_runs.items())),
            "total_reopen_runs": sum(reopen_runs.values()),
        },
    }
    (HERE / "census_concurrency.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    p = print
    p("=" * 78)
    p("F3 CONCURRENCY / UNIQUENESS / WAIT-IDIOM OUTLIERS")
    p("=" * 78)
    p("-- Q3 blocking-wait idiom --")
    wi = out["wait_idiom"]
    for k, v in wi.items():
        if k == "orphan_examples (fid,entry,tag,winnum)":
            continue
        p(f"   {k}: {v}")
    p(f"   orphan (cross-thread) WAITMES examples: {wi['orphan_examples (fid,entry,tag,winnum)'][:12]}")
    p("")
    p("-- Q4 concurrency / (fldMapNo,winnum,textId) uniqueness --")
    for k, v in out["concurrency_uniqueness"].items():
        p(f"   {k}: {v}")
    p("")
    p("-- Q5 multi-page: separate-window reopen runs vs [PAGE] (=37, from text pass) --")
    p(f"   total consecutive same-winnum reopen runs (len>=2): {out['multipage']['total_reopen_runs']}")
    p(f"   run-length histogram: {out['multipage']['separate_window_reopen_runs (len>=2 consecutive same-winnum)']}")
    p("=" * 78)


if __name__ == "__main__":
    main()
