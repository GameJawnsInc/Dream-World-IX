"""THE STORY-WRITE TRACE, RUNG 0 -- the engine hook + sink on a STOCK field, measured on Lindblum 552.

    py tools/build_memoria.py --label pre-s88-story-trace     # s88 in the live DLL (backs up first)
    py tools/play.py studies/story-trace/rung0_trace.py --label story-rung0

The beat is the narrative-state arc's proven calibration: Lindblum 552 @ SC 3115 with the ATE word
(``UInt16[236]``) = 0x0F, which boots the real Small-Town Knight ATE. Entrance 3 is pinned: the player entry
puts it at a fixed spot (337, 1046), and Main_Init's ATE branch runs for any entrance but 1 and 2.

PRE   P-CAP the engine advertises the trace at proto 1; P-STOCK no mod folder overrides 552's script
R0-OFF   armed but not started: no story.jsonl rows, the tracer off with 0 rows
R0-RUN   one traced run, closed by its `off` (a fault or a cut file would read as "nothing written")
R0-JOIN  every script write in 552 lands on a store instruction of the STOCK 552 bytes at its (sid, tag, offset)
R0-ATTR  every such row carries a real attribution: sid, uid, level, ip, a tag the function table agrees with
R0-SEED  the harness's own seed pokes arrive as `harness` rows, not script rows
R0-MAIN  Main_Init's writes arrive in script order -- the unconditional ones and the ATE branch the seed opens:
         Bit[191]:=0, Bit[184]:=0, Int16[9]:=1582, Byte[13], Int16[11]:=1587, Byte[14], Int16[239]:=552,
         SByte[238]:=1, Int16[241]:=15, UInt16[251] |= 15
R0-CLI   `ff9mapkit story-trace --strict` reads the run back and joins it
(report) residue bytes and every other field's rows, for rung 1
NC-THROW
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit import storytrace as T  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
FIELD, ENTRANCE, SC, ATE_WORD = 552, 3, 3115, 0x0F
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")

#: Main_Init's writes for this beat, in script order: (target, value or None = any, or ("or", mask)). Bit 184 set at
#: load adds Int16[2]:=10000 between the first two -- allowed, and reported.
MAIN = [
    ("Global.Bit[191]", 0),
    ("Global.Bit[184]", 0),
    ("Global.Int16[9]", 1582),
    ("Global.Byte[13]", None),
    ("Global.Int16[11]", 1587),
    ("Global.Byte[14]", None),
    ("Global.Int16[239]", 552),
    ("Global.SByte[238]", 1),
    ("Global.Int16[241]", ATE_WORD),
    ("Global.UInt16[251]", ("or", ATE_WORD)),
]


def mod_roots() -> list:
    text = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', text, re.M)
    names = re.findall(r'"([^"]+)"', m.group(1)) if m else []
    return [GAME / n for n in names if (GAME / n).is_dir()]


def analyse(rows, idx) -> list:
    """The rung's checks over one traced run's rows -- a pure function, so it runs offline against rows built
    from the real bytes. ``idx`` = the STOCK 552 :class:`storytrace.ScriptIndex`. Returns [(ok, what, detail)]."""
    out = []
    runs = T.split_runs(rows)
    closed = len(runs) == 1 and T.epochs(runs[0])[-1].closed_by is not None
    out.append((closed, "R0-RUN: exactly one traced run, closed by its `off` epoch",
                f"{len(runs)} run(s); epochs {[e.why for e in T.epochs(runs[0])] if runs else []}"))
    if not runs:
        return out
    run = runs[0]
    mine = [r for r in run if r.k == "w" and r.src == "eb" and r.fld == FIELD]
    joins = [(r, idx.join(r, donor=FIELD)) for r in mine if not r.add]
    fails = [(r.line, r.target, r.ip, j.reason) for r, j in joins if not j.ok]
    stores = sum(j.status == "store" for _r, j in joins)
    out.append((bool(joins) and not fails,
                f"R0-JOIN: every script write in {FIELD} lands on a store of the STOCK bytes at its (sid, tag, offset)",
                f"{len(joins)} rows: {stores} store, {sum(j.status == 'unverified' for _r, j in joins)} unverified, "
                f"{sum(j.status == 'engine' for _r, j in joins)} engine, {len(fails)} FAILED {fails[:4]}"))
    bad_attr = [r.line for r in mine if r.sid < 0 or r.uid < 0 or r.lvl is None or r.lvl < 0 or r.ip < 0
                or (not r.add and r.tag < 0)]
    out.append((bool(mine) and not bad_attr, "R0-ATTR: every script row carries sid, uid, level, ip and a tag",
                f"{len(mine)} rows, {len(bad_attr)} without: lines {bad_attr[:6]}"))
    seed = [r for r in run if r.k == "w" and r.src == "harness"]
    seeded = [r for r in seed if r.byte == 236 and r.new == ATE_WORD]
    leaked = [r for r in mine if r.byte in (236, 237) and r.new == ATE_WORD and r.old != ATE_WORD]
    out.append((bool(seeded) and not leaked, "R0-SEED: the harness's seed poke arrives as a `harness` row",
                f"{len(seed)} harness rows, byte 236 := {ATE_WORD}: {len(seeded)}; script rows claiming it: {len(leaked)}"))
    main = [(r, j) for r, j in joins if j.ok and r.sid == 0 and r.tag == 0]
    seq = [(r.target, r.new, r.old, r.ip) for r, _j in main]
    got, i, extra = [], 0, []
    for tgt, new, old, ip in seq:
        if i < len(MAIN) and tgt == MAIN[i][0]:
            want = MAIN[i][1]
            if want is None or want == new or (isinstance(want, tuple) and new == (old | want[1])):
                got.append((tgt, new))
                i += 1
                continue
        extra.append((tgt, new))
    ips = [ip for *_x, ip in seq]
    ordered = ips == sorted(ips)
    out.append((i == len(MAIN) and ordered,
                "R0-MAIN: Main_Init's writes arrive in script order (the unconditional ones and the ATE branch)",
                f"matched {i}/{len(MAIN)} {got}; missing {[t for t, _v in MAIN[i:]]}; others {extra}; "
                f"ip order {'ascending' if ordered else 'NOT ascending: ' + str(ips)}"))
    return out


def report_only(rows) -> dict:
    """What rung 1 will judge, recorded now: residue bytes and every other field's rows."""
    runs = T.split_runs(rows)
    run = runs[0] if runs else []
    res = {}
    for r in run:
        if r.k == "r":
            res.setdefault(r.byte, []).append((r.why, r.old, r.new, r.fld))
    other = {}
    for r in run:
        if r.k == "w" and r.fld != FIELD:
            other[r.fld] = other.get(r.fld, 0) + 1
    return {"residue": {str(b): v for b, v in sorted(res.items())}, "other_fields": other,
            "kinds": {k: sum(r.k == k for r in run) for k in "wrce"}}


def preflight(g) -> bool:
    cap = g.state.storytrace
    ok = g.check(isinstance(cap, dict) and cap.get("proto") == T.PROTO,
                 "P-CAP: the engine advertises the story trace at proto 1 (s88 is in the live DLL)", str(cap))
    over = T.stock_overrides(FIELD, mod_roots())
    ok &= g.check(not over, f"P-STOCK: no mod folder overrides field {FIELD}'s script", str(over))
    return ok


def run(g) -> None:
    if not preflight(g):
        return
    idx = T.stock_script_source()(FIELD)
    if not g.check(idx is not None, f"P-SCRIPT: the install's field bundle yields {FIELD}'s .eb", ""):
        return
    g.newgame()
    mark = g.log_mark()
    cap = g.state.storytrace or {}
    g.check(not g.channel.story_text() and not cap.get("on") and cap.get("rows") == 0,
            "R0-OFF: armed but not started, the tracer writes nothing",
            f"story.jsonl {len(g.channel.story_text() or '')} chars; {cap}")
    rows = []
    try:
        g.storytrace(True)
        g.poke(236, ATE_WORD)
        g.poke(237, 0)
        g.warp(FIELD, entrance=ENTRANCE, scenario=SC)
        g.wait_control(timeout=60)
        g.wait_frames(60)                                    # ~2 s of the field standing still
        g.storytrace(False)
        rows = g.story_rows()
    finally:
        (g.run_dir / "story_rung0.jsonl").write_text(g.channel.story_text() or "", encoding="utf-8")
    for ok, what, detail in analyse(rows, idx):
        g.check(ok, what, detail)
    rep = report_only(rows)
    (g.run_dir / "story_rung0_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[story-rung0] report-only: {json.dumps(rep)[:600]}")
    cli = subprocess.run([sys.executable, "-m", "ff9mapkit", "story-trace", "--strict",
                          str(g.run_dir / "story_rung0.jsonl")], cwd=REPO / "ff9mapkit",
                         capture_output=True, text=True)
    (g.run_dir / "story_rung0_cli.txt").write_text(cli.stdout + cli.stderr, encoding="utf-8")
    g.check(cli.returncode == 0 and str(FIELD) in cli.stdout,
            "R0-CLI: `ff9mapkit story-trace --strict` reads the run back and joins it",
            f"exit {cli.returncode}; {(cli.stdout + cli.stderr)[-300:]}")
    every = g.exceptions_since(mark)
    ours = [e for e in every if e.name in THROWS and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not ours, "NC-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
            str([(e.name, e.where) for e in ours[:5]]))
