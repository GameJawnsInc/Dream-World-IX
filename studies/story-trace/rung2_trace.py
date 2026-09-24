"""THE STORY-WRITE TRACE, RUNG 2 -- THE NULL PAIR, the instrument's real falsifier.

    py tools/deploy_field.py <scratch>/TRC552.field.toml --id 30830 --name TRC552 --mod-folder FF9CustomMap
    py tools/play.py studies/story-trace/rung2_trace.py --label story-rung2

Stock Lindblum 552 against its OWN verbatim fork (slot 30830, `ff9mapkit import 552 --verbatim`, the deploy writes
`ForkDonorPatch.txt` 30830 -> 552), three runs a side, interleaved S F S F S F. Each run: New Game, `storytrace 1`,
seed the ATE word (byte 236 = 0x0F), `warp <field> 3 3115`, stand ~3 s, `storytrace 0`, soft reset.

The fork ships the donor's script byte for byte (only its Field() operands are remapped), so a working instrument
must report NOTHING the stock field runs that the fork does not. An instrument that reports differences between
identical scripts is broken -- which is exactly what the board's original falsifier could never catch.

R2-RUNS     six closed runs, three a side, each reaching its field
R2-DONOR    every fork row in 30830 says `don` 552: the ForkDonorPatch mapping is live in the engine
R2-JOIN     no join failure in any run (each side joined against the bytes it RAN: the install's 552, the mod
            folder's 30830, the field-70 New Game override on both)
R2-NULL     STOCK ONLY is empty -- the falsifier
R2-MIRROR   FORK ONLY is empty too (a verbatim fork writes nothing the donor does not)
R2-SEEN     the pair compared something: the 552 Main_Init keys matched on both sides
NC-THROW
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit import storytrace as T  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
STOCK, FORK, ENTRANCE, SC, ATE_WORD = 552, 30830, 3, 3115, 0x0F
ORDER = [STOCK, FORK, STOCK, FORK, STOCK, FORK]
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")


def mod_roots() -> list:
    text = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', text, re.M)
    return [GAME / n for n in (re.findall(r'"([^"]+)"', m.group(1)) if m else []) if (GAME / n).is_dir()]


def analyse(rows) -> tuple:
    """The rung's checks. Returns ([(ok, what, detail)], report text). Pure given the install + mod folders."""
    out = []
    runs = T.split_runs(rows)
    stock_src = T.stock_script_source()
    ran = T.mod_script_source(mod_roots(), fallback=stock_src)      # the bytes each side actually RAN
    fields = [sorted({r.fld for r in run if r.k == "w" and r.src == "eb"}) for run in runs]
    closed = [T.epochs(run)[-1].closed_by is not None for run in runs]
    reached = [ORDER[i] in fields[i] if i < len(ORDER) else False for i in range(len(runs))]
    out.append((len(runs) == len(ORDER) and all(closed) and all(reached),
                "R2-RUNS: six closed runs, three a side, each reaching its field",
                f"{len(runs)} runs; closed {closed}; fields {fields}"))
    if len(runs) != len(ORDER):
        return out, ""
    fork_rows = [r for i, run in enumerate(runs) if ORDER[i] == FORK for r in run
                 if r.k == "w" and r.src == "eb" and r.fld == FORK]
    bad_don = sorted({r.don for r in fork_rows if r.don != STOCK})
    out.append((bool(fork_rows) and not bad_don, f"R2-DONOR: every fork row in {FORK} says don {STOCK}",
                f"{len(fork_rows)} fork rows; other donors {bad_don}"))
    digests = []
    for i, run in enumerate(runs):
        side = "stock" if ORDER[i] == STOCK else "fork"
        digests.append((side, T.digest(f"{side}#{i + 1}", run, scripts=ran, donor_scripts=stock_src)))
    fails = [(d.label, r.line, r.target, why) for _s, d in digests for r, why in d.failures]
    out.append((not fails, "R2-JOIN: no join failure in any run", f"{len(fails)} failures {fails[:4]}"))
    c = T.compare([d for s, d in digests if s == "stock"], [d for s, d in digests if s == "fork"])
    out.append((not c.stock_only, "R2-NULL: STOCK ONLY is empty -- nothing the stock field writes that its verbatim "
                                  "fork does not",
                f"{len(c.stock_only)} keys {[str(k) for k in c.stock_only[:4]]}"))
    out.append((not c.fork_only, "R2-MIRROR: FORK ONLY is empty too",
                f"{len(c.fork_only)} keys {[str(k) for k in c.fork_only[:4]]}"))
    main = [k for k in c.matched if k.donor == STOCK and k.sid == 0 and k.tag == 0]
    out.append((len(main) >= 10, f"R2-SEEN: the pair compared something -- {STOCK}'s Main_Init keys matched on both "
                                 f"sides",
                f"{len(c.matched)} matched keys, {len(main)} of them 552 Main_Init; unstable {len(c.unstable)}"))
    return out, T.report(c, title=f"story trace: stock {STOCK} x3 vs verbatim fork {FORK} x3")


def run(g) -> None:
    cap = g.state.storytrace
    if not g.check(isinstance(cap, dict) and cap.get("proto") == T.PROTO,
                   "P-CAP: the engine advertises the story trace at proto 1", str(cap)):
        return
    mark = g.log_mark()
    rows: list = []
    try:
        for i, fid in enumerate(ORDER):
            if i:
                g.soft_reset()
            g.newgame()
            g.wait_frames(30)
            g.storytrace(True)
            g.poke(236, ATE_WORD)
            g.poke(237, 0)
            g.warp(fid, entrance=ENTRANCE, scenario=SC)
            g.wait_control(timeout=60)
            g.wait_frames(90)
            g.storytrace(False)
            print(f"[story-rung2] run {i + 1}/{len(ORDER)}: field {fid} traced")
        rows = g.story_rows()
    finally:
        (g.run_dir / "story_rung2.jsonl").write_text(g.channel.story_text() or "", encoding="utf-8")
    checks, report = analyse(rows)
    (g.run_dir / "story_rung2_report.txt").write_text(report, encoding="utf-8")
    print(report[:3000])
    for ok, what, detail in checks:
        g.check(ok, what, detail)
    every = g.exceptions_since(mark)
    ours = [e for e in every if e.name in THROWS and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not ours, "NC-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
            str([(e.name, e.where) for e in ours[:5]]))
