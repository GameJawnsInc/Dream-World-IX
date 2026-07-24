#!/usr/bin/env python3
"""F3 dialogue-lockstep DIVERGENCE census over all ~818 real FF9 field scripts.

Reads every field's ``.eb`` LIVE from the Steam install (UnityPy) and decodes RAW
opcodes / expressions via the kit's own byte-exact ``eb`` model -- NEVER text
transcripts (they hide the tokens this census is built on). Answers: where can the
GUEST's dialogue-window stream diverge from the HOST's DESPITE the F1/state mirror,
so the F3 (fldMapNo, winnum, textId) alignment key mismatches?

The mirror (per studies/field-coop/dialogue-sync.md) covers:
  * gEventGlobal (GLOB / Global.* var reads)  -- wholesale, host->guest each field load
  * read-WRAPS for partychk / PARTY_MEMBER / B_HAVE_ITEM
It does NOT cover: MAP-scoped flags (Map.* reads), AteCheckArray, gScriptVector/Dict,
RNG, per-machine frame/step/timer counters, local input, exact position.

METHOD (engine-grounded; every fact re-verified against C:/gd/FFIX/Memoria):
  * Window opens: MES 0x1F (block) / MESN 0x20 (noblock) / MESA 0x95 (block) /
    MESAN 0x96 (noblock). textId operand index {0x1F:2,0x20:2,0x95:3,0x96:3};
    uiFlags index {0x1F:1,0x20:1,0x95:2,0x96:2}; winATE bit = 64 (ETb.cs:486).
  * BattleDialog 0xD0 counted separately (battle-context window).
  * SetTextVariable 0x66: value operand index 1 (number / item substitution).
  * ATE opcode 0xD7 (mode arg).
  * A condition is pushed by opcode 0x05 (expr/"set") which EMPTIES the calc stack
    then pushes ONE result; the very next 0x02 (JMP_IFNOT/beq) / 0x03 (JMP_IF/bne) /
    switch (0x06/0x0B/0x0D) consumes exactly that result (EBin.cs beq/bne/expr). So a
    branch's guard condition IS the args[0] expression of the immediately preceding
    0x05 -- engine-faithful, not a heuristic.
  * A window at offset W is control-dependent on every conditional/switch guard in the
    same function whose forward-skip span [jump.end, target) contains W.
  * usercontrol lock: UCOFF/DisableMove 0x2D -> 0, UCON/EnableMove 0x2E -> 1
    (DoEventCode.cs:1046/1064) -- marks the scripted/cutscene span.

Re-runnable + deterministic: same install -> identical numbers.

Usage:  py census.py [--json OUT.json]     # runs from anywhere; self-adds the kit path
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]                       # <repo>/studies/field-coop/dialogue-census/census.py
sys.path.insert(0, str(_REPO / "ff9mapkit"))   # so `import ff9mapkit` finds the local package

from ff9mapkit.eb import EbScript                # noqa: E402
from ff9mapkit.eb.disasm import jump_target      # noqa: E402
from ff9mapkit.extract import EventBundle         # noqa: E402
from ff9mapkit._fieldtable import FIELD_BY_ID     # noqa: E402

# ---- opcode constants (engine-verified) --------------------------------------------------
WIN_BLOCK = {0x1F: True, 0x20: False, 0x95: True, 0x96: False}    # op -> waits for close?
WIN_TEXTID_IDX = {0x1F: 2, 0x20: 2, 0x95: 3, 0x96: 3}
WIN_UIFLAG_IDX = {0x1F: 1, 0x20: 1, 0x95: 2, 0x96: 2}
WIN_OPS = set(WIN_BLOCK)
BATTLEDIALOG = 0xD0
SETTEXTVAR = 0x66
ATE_OP = 0xD7
COND_JUMPS = {0x02, 0x03}
SWITCH_OPS = {0x06, 0x0B, 0x0D}
PUSH_EXPR = 0x05
DISABLE_MOVE = 0x2D
ENABLE_MOVE = 0x2E
WIN_ATE_FLAG = 64

# ---- source-category classification of one read_expr token stream ------------------------
# read_expr renders each token as `opXX` (bare operator) or `opXX(...)` (var / const /
# sysvar / objspec / member / ptr). Var tokens are byte >= 0xC0: source = byte & 3 (0 Global /
# 1 Map / 2 Instance / 3 Null). Sysvar 0x7A(index): 0 = Comn.random8() (RNG!), 7 = gStepCount,
# 9 = GetChoose, {17,20,21} = timer, 6 = gil, {10,11,12,13} = map-jump / sys x,y (GetSysvar.cs).
_SYSVAR_CAT = {0: "rng", 7: "step", 9: "choice", 17: "timer", 20: "timer", 21: "timer",
               6: "gil", 10: "position", 11: "position", 12: "position", 13: "position"}
_OP_CAT = {
    0x4F: "keyon",                                       # B_KEYON
    0x58: "key", 0x59: "key", 0x5A: "key", 0x5B: "key", 0x5C: "key",   # KEYOFF / KEY / *2
    0x6A: "frame", 0x65: "frame",                        # B_FRAME / B_BAFRAME
    0x6B: "party", 0x6D: "party",                        # B_PARTYCHK / B_PARTYADD
    0x64: "item",                                        # B_HAVE_ITEM
    0x52: "hp", 0x53: "hp", 0x6E: "hp", 0x6F: "hp",      # CURHP / MAXHP / CURMP / MAXMP
    0x5D: "position", 0x5E: "position", 0x60: "position", 0x61: "position", 0x66: "position",
    0x70: "position", 0x71: "position",                  # BGIID / BGIFLOOR
    0x6C: "sps",                                         # B_SPS
}
_VARSRC = {0: "glob", 1: "map", 2: "instance", 3: "null"}
_TOK_RE = re.compile(r"op([0-9A-Fa-f]{2})(\(\d+)?")


def classify_expr(expr_str) -> set:
    """Set of source categories read by a read_expr `{...}` token string (empty for a
    pure-literal / arithmetic condition)."""
    cats: set = set()
    if not isinstance(expr_str, str) or not expr_str.startswith("{"):
        return cats
    for m in _TOK_RE.finditer(expr_str):
        b = int(m.group(1), 16)
        has_paren = m.group(2) is not None
        if has_paren and b >= 0xC0:
            cats.add(_VARSRC[b & 3])
        elif b == 0x7A:                                  # B_SYSVAR(index)
            idx = int(m.group(2)[1:]) if m.group(2) else -1
            cats.add(_SYSVAR_CAT.get(idx, "sysvar"))
        elif b == 0x79:                                  # B_SYSLIST
            cats.add("syslist")
        elif b == 0x78:                                  # B_OBJSPECA (obj-var read)
            cats.add("objspec")
        elif b in (0x29, 0x5F):                          # B_MEMBER / B_PTR
            cats.add("objspec")
        elif b in (0x7D, 0x7E):                          # const literal -- not state
            pass
        elif not has_paren and b in _OP_CAT:
            cats.add(_OP_CAT[b])
    return cats


# mirror status of each category (studies/field-coop/dialogue-sync.md)
MIRRORED = {"glob", "party", "item"}                     # covered by mirror / read-wraps -> SAFE
FIXABLE = {"map"}                                        # non-mirrored today, widenable during a pinned scene
STRUCT = {"rng", "frame", "step", "timer", "keyon", "key"}   # per-machine, cannot widen away
CHOICE = {"choice"}                                      # L2-mirrorable (host's confirm / choice)
SOFT = {"position", "objspec", "syslist", "hp", "gil", "instance", "sysvar", "sps", "null"}

# primary label priority (worst / most-F3-relevant first)
_PRIORITY = [
    ("rng", "RNG"), ("timer", "TIMING"), ("frame", "TIMING"), ("step", "TIMING"),
    ("map", "MAP"), ("choice", "CHOICE"), ("keyon", "INPUT"), ("key", "INPUT"),
    ("position", "POSITION"), ("syslist", "PARTY-DERIVED"), ("hp", "PARTY-DERIVED"),
    ("gil", "PARTY-DERIVED"), ("objspec", "SCRIPT-LOCAL"), ("instance", "SCRIPT-LOCAL"),
    ("sysvar", "SCRIPT-LOCAL"), ("sps", "SCRIPT-LOCAL"), ("null", "SCRIPT-LOCAL"),
]
NONMIRROR_LABELS = {"RNG", "TIMING", "MAP", "CHOICE", "INPUT", "POSITION",
                    "PARTY-DERIVED", "SCRIPT-LOCAL"}


def primary_label(cats: set) -> str:
    """The divergence class of a window given the union of its guard/textId source cats."""
    nonmirror = cats - MIRRORED
    if not cats:
        return "UNGUARDED"
    if not nonmirror:
        return "MIRRORED"
    for key, lab in _PRIORITY:
        if key in nonmirror:
            return lab
    return "MIRRORED"


# ---- per-function guard analysis ---------------------------------------------------------
def analyze_function(eb: EbScript, func) -> tuple:
    """(instrs, guards, locked_spans) for one function.
    guards = [(span_start, span_end, cats, kind, has_cond)]; locked_spans = [(s,e)]."""
    instrs = list(eb.instrs(func))
    guards = []
    locked = []
    lock_start = None
    for i, ins in enumerate(instrs):
        if ins.op == DISABLE_MOVE:
            lock_start = ins.end
        elif ins.op == ENABLE_MOVE and lock_start is not None:
            locked.append((lock_start, ins.off)); lock_start = None
        if ins.op in COND_JUMPS:
            tgt = jump_target(ins)
            if tgt is None or tgt <= ins.end:            # expression offset or backward (loop) -> not a skip-guard
                continue
            cond = instrs[i - 1] if i > 0 and instrs[i - 1].op == PUSH_EXPR else None
            cats = classify_expr(cond.args[0]) if (cond and cond.arg_is_expr and cond.arg_is_expr[0]) else set()
            guards.append((ins.end, tgt, cats, "if", cond is not None))
        elif ins.op in SWITCH_OPS:
            sw = ins.switch()
            cond = instrs[i - 1] if i > 0 and instrs[i - 1].op == PUSH_EXPR else None
            cats = classify_expr(cond.args[0]) if (cond and cond.arg_is_expr and cond.arg_is_expr[0]) else set()
            if sw and sw.edges:
                maxt = max(e.target for e in sw.edges)
                if maxt > ins.end:
                    guards.append((ins.end, maxt, cats, "switch", cond is not None))
    if lock_start is not None:                            # DisableMove w/ no matching EnableMove in-func
        locked.append((lock_start, func.abs_end))
    return instrs, guards, locked


def guards_for(off: int, guards: list) -> tuple:
    """(union_cats, n_guards, n_missing_cond) for guards whose span contains off."""
    cats, n, miss = set(), 0, 0
    for (s, e, c, _kind, hascond) in guards:
        if s <= off < e:
            cats |= c
            n += 1
            if not hascond:
                miss += 1
    return cats, n, miss


def in_span(off: int, spans: list) -> bool:
    return any(s <= off < e for (s, e) in spans)


# ---- main census -------------------------------------------------------------------------
def run(json_out=None):
    bundle = EventBundle()
    fields = sorted(FIELD_BY_ID)

    stats = {
        "n_fields_total": len(fields), "n_fields_with_eb": 0, "n_fields_scanned": 0,
        "cond_branches": 0, "cond_branches_with_push": 0,
        "n_windows": 0, "n_windows_guarded": 0, "n_windows_locked": 0,
        "battledialog": 0, "win_ate_flagged": 0,
        "textid_expr": 0, "stv_total": 0, "stv_expr": 0,
        "win_timing_gated": 0, "mesn_noblock": 0, "guard_missing_cond": 0, "ate_total": 0,
    }
    win_by_op = Counter()
    win_block = Counter()
    win_class = Counter()               # over ALL window opens
    win_class_locked = Counter()        # control-locked (cutscene) windows only
    win_cat_hits = Counter()            # every guard-source cat that appears in any window's guard set
    textid_expr_cats = Counter()
    stv_expr_cats = Counter()
    ate_class = Counter()
    per_field = []

    for fid in fields:
        eb_bytes = bundle.eb_for_id(fid)
        if not eb_bytes:
            continue
        stats["n_fields_with_eb"] += 1
        try:
            eb = EbScript.from_bytes(eb_bytes)
        except Exception:
            continue
        stats["n_fields_scanned"] += 1
        f_win = f_nonmirror = 0
        f_classes = Counter()

        for e in eb.entries:
            if e.empty:
                continue
            for func in e.funcs:
                try:
                    instrs, guards, locked = analyze_function(eb, func)
                except Exception:
                    continue
                for i, ins in enumerate(instrs):
                    if ins.op in COND_JUMPS or ins.op in SWITCH_OPS:
                        stats["cond_branches"] += 1
                        if i > 0 and instrs[i - 1].op == PUSH_EXPR:
                            stats["cond_branches_with_push"] += 1
                for ins in instrs:
                    op = ins.op
                    if op == BATTLEDIALOG:
                        stats["battledialog"] += 1
                        continue
                    if op == SETTEXTVAR:
                        stats["stv_total"] += 1
                        if len(ins.arg_is_expr) > 1 and ins.arg_is_expr[1]:
                            stats["stv_expr"] += 1
                            for c in classify_expr(ins.args[1]):
                                stv_expr_cats[c] += 1
                        continue
                    if op == ATE_OP:
                        stats["ate_total"] += 1
                        gcats, _n, _m = guards_for(ins.off, guards)
                        ate_class[primary_label(gcats)] += 1
                        continue
                    if op not in WIN_OPS:
                        continue
                    # -- a dialogue window open --
                    stats["n_windows"] += 1
                    f_win += 1
                    win_by_op[op] += 1
                    blk = "block" if WIN_BLOCK[op] else "noblock"
                    win_block[blk] += 1
                    if not WIN_BLOCK[op]:
                        stats["mesn_noblock"] += 1
                    ti = WIN_TEXTID_IDX[op]
                    ui = WIN_UIFLAG_IDX[op]
                    # uiFlags winATE bit (immediate only)
                    if ui < len(ins.arg_is_expr) and not ins.arg_is_expr[ui] \
                            and isinstance(ins.args[ui], int) and (ins.args[ui] & WIN_ATE_FLAG):
                        stats["win_ate_flagged"] += 1
                    # textId expression? (data-driven text selection)
                    tcats = set()
                    if ti < len(ins.arg_is_expr) and ins.arg_is_expr[ti]:
                        stats["textid_expr"] += 1
                        tcats = classify_expr(ins.args[ti])
                        for c in tcats:
                            textid_expr_cats[c] += 1
                    # guard set
                    gcats, ng, miss = guards_for(ins.off, guards)
                    stats["guard_missing_cond"] += miss
                    if ng:
                        stats["n_windows_guarded"] += 1
                    union = gcats | tcats
                    for c in union:
                        win_cat_hits[c] += 1
                    if union & {"frame", "step", "timer"}:
                        stats["win_timing_gated"] += 1
                    label = primary_label(union)
                    win_class[label] += 1
                    f_classes[label] += 1
                    if label in NONMIRROR_LABELS:
                        f_nonmirror += 1
                    if in_span(ins.off, locked):
                        stats["n_windows_locked"] += 1
                        win_class_locked[label] += 1

        if f_win:
            per_field.append((fid, f_win, f_nonmirror, dict(f_classes)))

    out = {
        "stats": stats,
        "win_by_op": {f"0x{k:02X}": v for k, v in sorted(win_by_op.items())},
        "win_block": dict(win_block),
        "win_class": dict(win_class.most_common()),
        "win_class_locked": dict(win_class_locked.most_common()),
        "win_cat_hits": dict(win_cat_hits.most_common()),
        "textid_expr_cats": dict(textid_expr_cats.most_common()),
        "stv_expr_cats": dict(stv_expr_cats.most_common()),
        "ate_class": dict(ate_class.most_common()),
        "per_field_top": sorted(per_field, key=lambda r: (-r[2], -r[1]))[:40],
    }
    _print_report(out)
    if json_out:
        Path(json_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\n[json written -> {json_out}]")
    return out


def _pct(n, d):
    return f"{100.0 * n / d:.1f}%" if d else "n/a"


def _print_report(out):
    s = out["stats"]
    P = print
    P("=" * 78)
    P("F3 DIALOGUE-LOCKSTEP DIVERGENCE CENSUS  (raw .eb opcodes, all real fields)")
    P("=" * 78)
    P(f"fields: {s['n_fields_total']} total / {s['n_fields_with_eb']} with .eb / "
      f"{s['n_fields_scanned']} scanned")
    P(f"branch-idiom self-check: {s['cond_branches_with_push']}/{s['cond_branches']} "
      f"conditional+switch ops immediately preceded by 0x05 push "
      f"({_pct(s['cond_branches_with_push'], s['cond_branches'])})")
    P(f"guards with a missing/stale condition (excluded from cats): {s['guard_missing_cond']}")
    P("")
    P(f"WINDOW OPENS (MES/MESN/MESA/MESAN): {s['n_windows']}")
    P(f"  by op: {out['win_by_op']}   block/noblock: {out['win_block']}")
    P(f"  guarded by >=1 conditional: {s['n_windows_guarded']} "
      f"({_pct(s['n_windows_guarded'], s['n_windows'])})")
    P(f"  inside a DisableMove..EnableMove lock (cutscene, same-func): {s['n_windows_locked']} "
      f"({_pct(s['n_windows_locked'], s['n_windows'])})")
    P(f"  winATE-flagged (ATE-captioned): {s['win_ate_flagged']}")
    P(f"  BattleDialog 0xD0 (separate): {s['battledialog']}")
    P("")
    P("Q1+Q5  DIVERGENCE CLASS over ALL window opens (primary label):")
    for lab, n in out["win_class"].items():
        P(f"    {lab:14s} {n:6d}  {_pct(n, s['n_windows'])}")
    P("  -- restricted to control-locked cutscene windows:")
    tot_locked = sum(out["win_class_locked"].values())
    for lab, n in out["win_class_locked"].items():
        P(f"    {lab:14s} {n:6d}  {_pct(n, tot_locked)}")
    P("")
    P("Q1  TEXTID data-driven (textId operand is an EXPRESSION): "
      f"{s['textid_expr']} ({_pct(s['textid_expr'], s['n_windows'])})")
    P(f"    source cats: {out['textid_expr_cats']}")
    P("  guard-source cat hits across all windows (a window can hit several):")
    P(f"    {out['win_cat_hits']}")
    P("")
    P(f"Q2  SetTextVariable 0x66: {s['stv_total']} total / {s['stv_expr']} with an EXPRESSION value "
      f"({_pct(s['stv_expr'], s['stv_total'])})")
    P(f"    expression source cats: {out['stv_expr_cats']}")
    P("")
    P(f"Q3  ATE opcode 0xD7: {s['ate_total']} sites; divergence class of each ATE's guard set:")
    for lab, n in out["ate_class"].items():
        P(f"    {lab:14s} {n:6d}  {_pct(n, s['ate_total'])}")
    P("")
    P(f"Q4  TIMING-gated windows (guard reads frame/step/timer): {s['win_timing_gated']} "
      f"({_pct(s['win_timing_gated'], s['n_windows'])})")
    P(f"    non-blocking auto-advance windows (MESN/MESAN): {s['mesn_noblock']} "
      f"({_pct(s['mesn_noblock'], s['n_windows'])})")
    P("")
    P("TOP FIELDS by non-mirrored window count (field_id, windows, nonmirror, classes):")
    for fid, nw, nm, cls in out["per_field_top"][:20]:
        P(f"    field {fid:5d}: {nw:3d} win, {nm:3d} nonmirror  {cls}")
    P("=" * 78)


if __name__ == "__main__":
    jout = None
    if "--json" in sys.argv:
        jout = sys.argv[sys.argv.index("--json") + 1]
    run(jout)
