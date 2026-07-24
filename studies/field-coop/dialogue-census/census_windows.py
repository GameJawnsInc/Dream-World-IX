#!/usr/bin/env python3
"""F3 dialogue-lockstep census -- LANE: WINDOW LIFECYCLE + ADVANCE MECHANISMS.

Byte-grounded census over ALL ~818 real FF9 field scripts. Works on RAW DECODED OPCODES via the
kit's eb model (EbScript.from_bytes + eb.disasm) -- NEVER on text transcripts (THE CENSUS LAW).

Reads every field's .eb live from the Steam install through the kit's own extractor
(ff9mapkit.extract.EventBundle -> eb_for_id), the exact loop the b36/battle-locations censuses used.

Deterministic + re-runnable: fields walked in ascending id order; output is a stable JSON blob + a
printed set of tables. No writes outside this directory (the JSON cache is written HERE).

The window family (kit dialogue.WINDOW_OPS + engine EventEngine.DoEventCode.cs):
    MES    0x1F  WindowSync    args[winnum, uiFlags, textId]           SYNC  (sets gCur.wait=254)
    MESN   0x20  WindowAsync   args[winnum, uiFlags, textId]           ASYNC (returns 0, no wait)
    MESA   0x95  WindowSyncEx  args[talker, winnum, uiFlags, textId]   SYNC  (sets gCur.wait=254)
    MESAN  0x96  WindowAsyncEx args[talker, winnum, uiFlags, textId]   ASYNC (returns 0, no wait)
Close / wait / control family:
    CLOSE     0x21  CloseWindow(winnum)         force-close one winnum
    CLOSEALL  0xEB  CloseAllWindows             close every dialog
    WAITMES   0x54  WaitWindow(winnum)          sets gCur.wait=254 (block on a winnum)
    RAISE     0x8E  RaiseWindows
    NOINITMES 0x53  PreventWindowInit
    WAIT      0x22  Wait(frames)                the frame delay (marks a TIMED close)
    CHOOSEPARAM 0x7C EnableDialogChoices        choice availability setup
    SETSIGNAL 0xE3  SetDialogProgression
    MENU      0x75  Menu                        opens a menu (out of the dialogue family; counted for context)
    MESB      0xD0  BattleDialog                battle text, 60-frame timed (not a field window; counted)

Engine ground truth (verified in C:/gd/FFIX/Memoria this pass):
  * NewMesWin (ETb.cs:91-96) calls DisposWindowByID(winID) FIRST -> opening a winnum force-closes any
    live window already on that winnum. CheckDialogShowing (DialogManager.cs:176) scans Id==winnum.
    => at any instant a winnum maps to AT MOST ONE live window. winnum alone is the liveness key;
       textId is a redundant (over-specified, safe) content check.
  * SYNC (MES/MESA) sets gCur.wait=254; the interpreter (EBin.cs:138) unblocks when !MesWinActive(winnum).
    winnum==255 -> wait clears immediately (a non-blocking sentinel).
  * The WINDOW's own close mechanism is governed by the .mes text, resolved in census_text.py:
    [TIME=N>0] -> EndMode>0 -> AutoHide coroutine + FlagButtonInh (button inhibited) = TIMED auto-close.
    [TIME=-1]  -> FlagButtonInh, no auto-hide = waits for a SCRIPT close.  no [TIME] = player CONFIRM.
    [IMME]=instant-print, [FEED]=horizontal indent -> NEITHER is auto-advance (a common misread).
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
# import the kit (repo/ff9mapkit is the package root)
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit.extract import EventBundle                    # noqa: E402
from ff9mapkit._fieldtable import FIELD_BY_ID                # noqa: E402
from ff9mapkit.eb import EbScript                            # noqa: E402

# ---- opcodes ----
MES, MESN, MESA, MESAN = 0x1F, 0x20, 0x95, 0x96
WINDOW_OPEN = {MES, MESN, MESA, MESAN}
SYNC_OPS = {MES, MESA}          # set gCur.wait=254 in-line
ASYNC_OPS = {MESN, MESAN}       # return 0, no wait
EX_OPS = {MESA, MESAN}          # arg0 is the talker obj; winnum shifts +1
CLOSE, CLOSEALL, WAITMES = 0x21, 0xEB, 0x54
RAISE, NOINITMES, WAIT_OP = 0x8E, 0x53, 0x22
CHOOSEPARAM, SETSIGNAL = 0x7C, 0xE3
MENU_OP, MESB = 0x75, 0xD0
WINATE, WINMOG = 64, 8          # uiFlags bits (ETb.cs:483/486)


def win_operand_indices(op):
    """(winnum_idx, uiflags_idx, textid_idx) for a window-open op."""
    if op in EX_OPS:            # MESA/MESAN: [talker, winnum, uiFlags, textId]
        return 1, 2, 3
    return 0, 1, 2              # MES/MESN: [winnum, uiFlags, textId]


def imm_or_expr(ins, idx):
    """The immediate int at operand idx, or the string 'expr' if it's an expression operand, or None."""
    if idx >= len(ins.arg_is_expr):
        return None
    if ins.arg_is_expr[idx]:
        return "expr"
    return ins.imm(idx)


def analyze_function(eb, entry, func):
    """Walk one function's linear instruction stream; return (opens, events).

    opens: list of dicts per window-open site with a downstream-flow classification.
    events: aggregate opcode counts + the raw close/wait/etc. sites for the field-level tallies.
    """
    instrs = list(eb.instrs(func))
    opens = []
    ev = Counter()
    # first pass: record indices of close/wait/reopen anchors for downstream scans
    for i, ins in enumerate(instrs):
        op = ins.op
        if op in WINDOW_OPEN:
            wi, ui, ti = win_operand_indices(op)
            winnum = imm_or_expr(ins, wi)
            uiflags = imm_or_expr(ins, ui)
            textid = imm_or_expr(ins, ti)
            opens.append({"idx": i, "op": op, "winnum": winnum, "uiflags": uiflags,
                          "textid": textid, "off": ins.off})
        elif op == CLOSE:
            ev["close"] += 1
        elif op == CLOSEALL:
            ev["closeall"] += 1
        elif op == WAITMES:
            ev["waitmes"] += 1
        elif op == RAISE:
            ev["raise"] += 1
        elif op == NOINITMES:
            ev["noinitmes"] += 1
        elif op == CHOOSEPARAM:
            ev["chooseparam"] += 1
        elif op == SETSIGNAL:
            ev["setsignal"] += 1
        elif op == MENU_OP:
            ev["menu"] += 1
        elif op == MESB:
            ev["battledialog"] += 1

    # classify each open by DOWNSTREAM linear flow in this same function
    for k, o in enumerate(opens):
        i, op, winnum = o["idx"], o["op"], o["winnum"]
        klass = None
        timed = False
        # SYNC opcode: the calling script blocks in-line (wait=254). Window advance = text-driven
        # (confirm default / [TIME] auto) -- resolved in the text pass. Label the OPCODE behavior.
        if op in SYNC_OPS:
            o["blocking"] = True
            klass = "sync_blocking"
        else:
            o["blocking"] = False
            # scan downstream in this function for the fate of this winnum
            fate = "fireforget"
            for j in range(i + 1, len(instrs)):
                nj = instrs[j]
                if nj.op == WAIT_OP:
                    timed = True
                    continue
                if nj.op == WAITMES:
                    w = imm_or_expr(nj, 0)
                    if w == winnum or w == "expr" or winnum == "expr":
                        fate = "async_wait"
                        break
                if nj.op == CLOSE:
                    w = imm_or_expr(nj, 0)
                    if w == winnum or w == "expr" or winnum == "expr":
                        fate = "async_close"
                        break
                if nj.op == CLOSEALL:
                    fate = "async_closeall"
                    break
                if nj.op in WINDOW_OPEN:
                    wi2, _, _ = win_operand_indices(nj.op)
                    w2 = imm_or_expr(nj, wi2)
                    if w2 == winnum and winnum is not None:
                        fate = "async_replaced"     # NewMesWin auto-disposes the same winnum
                        break
            klass = fate
        o["klass"] = klass
        o["timed"] = timed

    # static within-function concurrency: simulate the live-winnum set across the linear stream
    live = set()
    max_live = 0
    concurrency_trace = []
    for ins in instrs:
        op = ins.op
        if op in WINDOW_OPEN:
            wi, _, _ = win_operand_indices(op)
            w = imm_or_expr(ins, wi)
            key = w if w is not None else "?"
            # NewMesWin force-disposes the same winnum first, then adds -> set semantics already dedupe
            if op in ASYNC_OPS:
                live.add(key)
            else:
                # SYNC: the window is live only until the script's own wait clears (window closes).
                # For a static linear model treat a sync open as momentarily live then resolved by its
                # own in-line block -- it does NOT stack with a later sync open (the first must close to
                # reach the second). So a sync open does not persist in `live`.
                live.add(key)
                max_live = max(max_live, len(live))
                live.discard(key)
                continue
        elif op == CLOSE:
            w = imm_or_expr(ins, 0)
            live.discard(w if w is not None else "?")
        elif op == CLOSEALL:
            live.clear()
        elif op == WAITMES:
            # blocking on a winnum -> once it clears it is gone
            w = imm_or_expr(ins, 0)
            live.discard(w if w is not None else "?")
        max_live = max(max_live, len(live))
    return opens, ev, max_live


def main():
    bundle = EventBundle()
    fields = sorted(FIELD_BY_ID)                 # deterministic order

    # aggregates
    total_opens = 0
    op_counter = Counter()                       # by opcode
    klass_counter = Counter()                    # by downstream classification
    winnum_values = Counter()                    # observed winnum immediates
    winnum_expr = 0
    textid_expr = 0
    uiflags_hist = Counter()                     # observed uiFlags immediates
    ate_windows = 0
    mog_windows = 0
    per_field_opens = {}                         # fid -> count
    per_field_distinct_winnums = {}              # fid -> set size (immediate winnums only)
    per_field_maxlive = {}                       # fid -> max static within-function concurrency
    fields_with_ate_and_plain = 0
    field_ev = Counter()                         # field-level close/wait/etc. totals
    entry_class = Counter()                      # "main"(entry0) vs "other" window sites
    tag_counter = Counter()                      # func.tag of window sites
    ate_by_entry = Counter()                     # where ATE windows live: main vs other
    # concurrency: winnum reuse -- can two live windows share a winnum? (engine says no; measure the
    # structural reuse of a winnum across a field, and same-winnum reopen chains within a function.)
    reopen_chains = Counter()                    # length distribution of same-winnum consecutive reopen runs
    per_op_records = []                          # slim per-site rows for the text pass + outlier hunt

    for fid in fields:
        data = bundle.eb_for_id(fid)
        if data is None:
            continue
        try:
            eb = EbScript.from_bytes(data)
        except Exception as e:                   # noqa: BLE001 -- a malformed .eb should not kill the run
            print(f"WARN field {fid}: {e}", file=sys.stderr)
            continue
        f_opens = 0
        f_winnums = set()
        f_maxlive = 0
        f_has_ate = False
        f_has_plain = False
        for entry in eb.entries:
            if entry.empty:
                continue
            for func in entry.funcs:
                opens, ev, max_live = analyze_function(eb, entry, func)
                for kk, vv in ev.items():
                    field_ev[kk] += vv
                f_maxlive = max(f_maxlive, max_live)
                # same-winnum reopen run detection (within this func, consecutive opens on same winnum)
                run_win = None
                run_len = 0
                for o in opens:
                    total_opens += 1
                    f_opens += 1
                    op_counter[o["op"]] += 1
                    klass_counter[o["klass"]] += 1
                    if o["timed"]:
                        klass_counter["_async_timed_delay"] += 1
                    w = o["winnum"]
                    if w == "expr":
                        winnum_expr += 1
                    elif w is not None:
                        winnum_values[w] += 1
                        f_winnums.add(w)
                    t = o["textid"]
                    if t == "expr":
                        textid_expr += 1
                    uf = o["uiflags"]
                    if uf not in (None, "expr"):
                        uiflags_hist[uf] += 1
                        if uf & WINATE:
                            ate_windows += 1
                            f_has_ate = True
                            ate_by_entry["main" if entry.index == 0 else "other"] += 1
                        else:
                            f_has_plain = True
                        if uf & WINMOG:
                            mog_windows += 1
                    else:
                        f_has_plain = True
                    entry_class["main" if entry.index == 0 else "other"] += 1
                    tag_counter[func.tag] += 1
                    per_op_records.append({
                        "fid": fid, "entry": entry.index, "etype": entry.type, "tag": func.tag,
                        "op": o["op"], "winnum": w, "uiflags": uf, "textid": t,
                        "klass": o["klass"], "timed": o["timed"], "off": o["off"],
                    })
                    # reopen run
                    if w is not None and w == run_win:
                        run_len += 1
                    else:
                        if run_len >= 2:
                            reopen_chains[run_len] += 1
                        run_win = w
                        run_len = 1
                if run_len >= 2:
                    reopen_chains[run_len] += 1
        per_field_opens[fid] = f_opens
        per_field_distinct_winnums[fid] = len(f_winnums)
        per_field_maxlive[fid] = f_maxlive
        if f_has_ate and f_has_plain:
            fields_with_ate_and_plain += 1

    fields_with_windows = sum(1 for v in per_field_opens.values() if v > 0)
    out = {
        "corpus": {"fields_total": len(fields), "fields_with_windows": fields_with_windows},
        "total_window_opens": total_opens,
        "by_opcode": {f"{k:#04x}": v for k, v in sorted(op_counter.items())},
        "by_class": dict(klass_counter.most_common()),
        "sync_vs_async": {
            "sync_blocking": op_counter[MES] + op_counter[MESA],
            "async": op_counter[MESN] + op_counter[MESAN],
        },
        "winnum": {
            "distinct_immediate_values": len(winnum_values),
            "expr_winnum_sites": winnum_expr,
            "value_hist": dict(sorted(winnum_values.items())),
        },
        "textid_expr_sites": textid_expr,
        "uiflags_hist": dict(sorted(uiflags_hist.items())),
        "ate_windows": ate_windows,
        "mog_windows": mog_windows,
        "ate_by_entry": dict(ate_by_entry),
        "fields_with_ate_and_plain": fields_with_ate_and_plain,
        "entry_class": dict(entry_class),
        "func_tag_hist": dict(sorted(tag_counter.items())),
        "close_wait_family": dict(field_ev.most_common()),
        "reopen_chain_lengths": dict(sorted(reopen_chains.items())),
        "concurrency": {
            "fields_multi_distinct_winnum": sum(1 for v in per_field_distinct_winnums.values() if v > 1),
            "max_distinct_winnum_in_a_field": max(per_field_distinct_winnums.values()),
            "fields_static_maxlive_ge2": sum(1 for v in per_field_maxlive.values() if v >= 2),
            "max_static_maxlive": max(per_field_maxlive.values()),
        },
        "per_field_open_hist": _hist([per_field_opens[f] for f in fields if per_field_opens.get(f, 0) > 0]),
    }

    # write slim per-site table for the text pass + the outlier hunt
    (HERE / "window_sites.json").write_text(
        json.dumps(per_op_records), encoding="utf-8")
    (HERE / "census_windows.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    # also dump per-field opens for the distribution table
    (HERE / "per_field_opens.json").write_text(
        json.dumps({str(f): per_field_opens[f] for f in fields}, indent=0), encoding="utf-8")

    _print_report(out, per_field_opens, fields)


def _hist(values):
    """Bucketed histogram of a list of ints."""
    buckets = [(0, 0), (1, 5), (6, 10), (11, 20), (21, 40), (41, 80), (81, 100000)]
    labels = ["0", "1-5", "6-10", "11-20", "21-40", "41-80", "81+"]
    out = {}
    for lab, (lo, hi) in zip(labels, buckets):
        out[lab] = sum(1 for v in values if lo <= v <= hi)
    return out


def _print_report(out, per_field_opens, fields):
    p = print
    p("=" * 78)
    p("F3 WINDOW-LIFECYCLE CENSUS  (lane: window lifecycle + advance mechanisms)")
    p("=" * 78)
    c = out["corpus"]
    p(f"corpus: {c['fields_total']} fields, {c['fields_with_windows']} open >=1 dialogue window")
    p(f"total window-open sites (MES/MESN/MESA/MESAN): {out['total_window_opens']}")
    p("")
    p("-- by opcode --")
    names = {"0x1f": "MES  WindowSync   SYNC", "0x20": "MESN WindowAsync  ASYNC",
             "0x95": "MESA WindowSyncEx SYNC", "0x96": "MESAN WindowAsyncEx ASYNC"}
    for k, v in out["by_opcode"].items():
        p(f"   {k}  {names.get(k, k):24s} {v:6d}")
    sa = out["sync_vs_async"]
    tot = sa["sync_blocking"] + sa["async"]
    p(f"   SYNC (blocking): {sa['sync_blocking']} ({100*sa['sync_blocking']/tot:.1f}%)   "
      f"ASYNC: {sa['async']} ({100*sa['async']/tot:.1f}%)")
    p("")
    p("-- by downstream classification (async sites: fate of the winnum in the same func) --")
    for k, v in out["by_class"].items():
        p(f"   {k:22s} {v:6d}")
    p("")
    p("-- winnum --")
    wn = out["winnum"]
    p(f"   distinct immediate winnum values: {wn['distinct_immediate_values']}")
    p(f"   winnum-as-expression sites: {wn['expr_winnum_sites']}")
    p(f"   winnum value histogram: {wn['value_hist']}")
    p(f"   textId-as-expression sites: {out['textid_expr_sites']}")
    p("")
    p("-- uiFlags histogram (window-style bits; 64=ATE 8=MOG 128=chat 32=noFollow 16=transp 4=noTail) --")
    p(f"   {out['uiflags_hist']}")
    p(f"   ATE windows (uiFlags&64): {out['ate_windows']}   MOG windows (uiFlags&8): {out['mog_windows']}")
    p(f"   ATE window location: {out['ate_by_entry']}")
    p(f"   fields with BOTH ATE and plain windows: {out['fields_with_ate_and_plain']}")
    p("")
    p("-- entry/tag placement of window sites --")
    p(f"   entry class (entry0=main vs other): {out['entry_class']}")
    p(f"   func.tag histogram (3=NPC talk): {out['func_tag_hist']}")
    p("")
    p("-- close/wait/control family (site totals across corpus) --")
    p(f"   {out['close_wait_family']}")
    p("")
    p("-- concurrency --")
    cc = out["concurrency"]
    p(f"   fields with >1 distinct winnum: {cc['fields_multi_distinct_winnum']}  "
      f"(max distinct in one field: {cc['max_distinct_winnum_in_a_field']})")
    p(f"   fields where a func statically holds >=2 live windows: {cc['fields_static_maxlive_ge2']}  "
      f"(max: {cc['max_static_maxlive']})")
    p(f"   same-winnum reopen-chain lengths: {out['reopen_chain_lengths']}")
    p("")
    p("-- per-field window-open distribution --")
    p(f"   {out['per_field_open_hist']}")
    top = sorted(per_field_opens.items(), key=lambda kv: -kv[1])[:12]
    p(f"   heaviest fields (id:opens): {['%d:%d' % (k, v) for k, v in top]}")
    p("=" * 78)


if __name__ == "__main__":
    main()
