"""THE STORY-WRITE TRACE, RUNG 1 -- the residue net and the epochs, in one traced run.

    py tools/play.py studies/story-trace/rung1_trace.py --label story-rung1

A C# writer the tracer is NOT told about must arrive as residue with its exact byte and value; the harness's own
pokes must arrive as `harness` rows and never as residue; a stretch of script-only play must leave no residue; and a
whole-array replacement -- New Game, a save load -- must be ONE `swap` epoch, never a flood.

The calibration writer is the debug menu's own warp: it writes the scenario counter (bytes 0-1) and the entrance
(bytes 2-3) straight into gEventGlobal, a real C# bypass, with values this scenario chooses. The world map's
`SC += 10` (ff9.cs:7168) fires only at a continent-title fade-in, a one-off story beat no scenario reaches, so it
is not used. The debug menu's restore/clear epochs have no harness verb (HarnessWarp passes resetFlags=false) and
co-op's `netsync` epoch needs two games: those three stay code-reviewed only.

R1-NEWGAME  `storytrace 1` on the title, then New Game: exactly one `swap` epoch before the new field's writes
R1-HARNESS  a `flag` and two `byte` pokes arrive as `harness` rows (bit + bytes) and none of their bytes as residue
R1-NET-A    warp 552 entrance 3 @ SC 3115: residue on byte 0 = 43, byte 1 = 12, byte 2 = 3
R1-NET-B    warp 552 entrance 5 @ SC 3120: residue on byte 0 = 48, byte 2 = 5 (and byte 1 stays 12: no row)
R1-QUIET    ~5 s standing in 552 after control: no residue at all
R1-LOAD     soft reset -> title -> Continue (the sandbox autosave): exactly one `swap` epoch before the loaded
            field's writes
R1-RUN      one traced run, closed by its `off`; R1-CLI `ff9mapkit story-trace --strict` reads it back
NC-THROW
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit import storytrace as T  # noqa: E402

FIELD = 552
SAFE_BIT = 12200                                   # in the safe custom band (flags.FIRST_SAFE_FLAG = 8712)
WARP_A = (3, 3115)                                 # (entrance, scenario)
WARP_B = (5, 3120)
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")


def marks(g) -> int:
    """How many rows the live trace holds now -- the phase boundaries are row indices, which need no clock."""
    g.wait_frames(3)                               # the tracer appends once per frame
    return len(g.story_rows())


def between(rows, a: int, b: int | None = None) -> list:
    return rows[a:b]


def residue_at(rows, byte: int) -> list:
    return [(r.old, r.new, r.why) for r in rows if r.k == "r" and r.byte == byte]


def analyse(rows, m: dict) -> list:
    """The rung's checks over the run's rows and the phase marks (row indices). Pure: runs offline."""
    out = []
    runs = T.split_runs(rows)
    closed = len(runs) == 1 and T.epochs(runs[0])[-1].closed_by is not None
    out.append((closed, "R1-RUN: exactly one traced run, closed by its `off` epoch",
                f"{len(runs)} run(s); epochs {[(e.why, e.index) for e in T.epochs(runs[0])] if runs else []}"))

    ng = between(rows, m["title"], m["newgame"])
    swaps = [r for r in ng if r.k == "e" and r.why == "swap"]
    first_w = next((i for i, r in enumerate(ng) if r.k == "w" and r.src == "eb"), len(ng))
    out.append((len(swaps) == 1 and ng.index(swaps[0]) < first_w,
                "R1-NEWGAME: New Game is exactly one `swap` epoch, before the new field's first script write",
                f"{len(swaps)} swap(s); epochs {[r.why for r in ng if r.k == 'e']}; first script write at {first_w}"))

    hz = between(rows, m["newgame"], m["poked"])
    hrows = [r for r in hz if r.k == "w" and r.src == "harness"]
    want = {("Bit", SAFE_BIT, 1), ("Byte", 236, 15), ("Byte", 237, 0)}
    got = {(r.width, r.bit if r.is_bit else r.byte, r.new) for r in hrows}
    leaked = [r.byte for r in hz if r.k == "r" and r.byte in (236, 237, SAFE_BIT >> 3)]
    out.append((want <= got and not leaked, "R1-HARNESS: the harness's pokes arrive as `harness` rows, never residue",
                f"harness rows {sorted(got)}; wanted {sorted(want)}; residue on their bytes {leaked}"))

    wa = between(rows, m["poked"], m["warpA"])
    ok_a = (residue_at(wa, 0)[-1:] and residue_at(wa, 0)[-1][1] == WARP_A[1] & 0xFF
            and residue_at(wa, 1)[-1:] and residue_at(wa, 1)[-1][1] == WARP_A[1] >> 8
            and residue_at(wa, 2)[-1:] and residue_at(wa, 2)[-1][1] == WARP_A[0])
    out.append((bool(ok_a), f"R1-NET-A: the debug warp's own writes arrive as residue: SC {WARP_A[1]} -> bytes 0/1 = "
                            f"{WARP_A[1] & 0xFF}/{WARP_A[1] >> 8}, entrance {WARP_A[0]} -> byte 2",
                f"byte 0 {residue_at(wa, 0)}, byte 1 {residue_at(wa, 1)}, byte 2 {residue_at(wa, 2)}"))

    q = between(rows, m["quiet0"], m["quiet1"])
    qres = [(r.byte, r.old, r.new, r.why) for r in q if r.k == "r"]
    out.append((not qres, "R1-QUIET: ~5 s of script-only play in 552 leaves no residue",
                f"{sum(r.k == 'w' for r in q)} script/harness writes, residue {qres[:8]}"))

    wb = between(rows, m["quiet1"], m["warpB"])
    ok_b = (residue_at(wb, 0)[-1:] and residue_at(wb, 0)[-1][1] == WARP_B[1] & 0xFF
            and not residue_at(wb, 1)
            and residue_at(wb, 2)[-1:] and residue_at(wb, 2)[-1][1] == WARP_B[0])
    out.append((bool(ok_b), f"R1-NET-B: a second warp, other values: byte 0 = {WARP_B[1] & 0xFF}, byte 2 = "
                            f"{WARP_B[0]}, and byte 1 (unchanged at {WARP_B[1] >> 8}) no row",
                f"byte 0 {residue_at(wb, 0)}, byte 1 {residue_at(wb, 1)}, byte 2 {residue_at(wb, 2)}"))

    ld = between(rows, m["reset"], m["loaded"])
    lswaps = [r for r in ld if r.k == "e" and r.why == "swap"]
    lfirst = next((i for i, r in enumerate(ld) if r.k == "w" and r.src == "eb"), len(ld))
    out.append((len(lswaps) == 1 and ld.index(lswaps[0]) < lfirst,
                "R1-LOAD: loading the autosave is exactly one `swap` epoch, before the loaded field's first write",
                f"{len(lswaps)} swap(s); epochs {[r.why for r in ld if r.k == 'e']}; residue rows "
                f"{sum(r.k == 'r' for r in ld)}; first script write at {lfirst}"))
    return out


def _continue_from_title(g) -> None:
    """Title -> Continue: the cursor defaults to Continue when an autosave exists (TitleUI.CheckAutoSaveSlot); the
    harness sandboxes saves, so this loads the autosave this run's own field entries wrote."""
    g.wait_for(lambda s: s.ui_state == "Title", timeout=120, what="the title screen")
    g._sleep_alive(8.0)
    g.press("confirm")
    g.wait_for(lambda s: s.ui_state == "FieldHUD" and s.field_id > 0, timeout=90,
               what="Continue to load the autosave into a field")


def run(g) -> None:
    cap = g.state.storytrace
    if not g.check(isinstance(cap, dict) and cap.get("proto") == T.PROTO,
                   "P-CAP: the engine advertises the story trace at proto 1", str(cap)):
        return
    mark = g.log_mark()
    m: dict = {}
    rows: list = []
    try:
        g.storytrace(True)                                   # on the title: the New Game swap is in the run
        m["title"] = marks(g)
        g.newgame()
        g.wait_frames(30)
        m["newgame"] = marks(g)
        g.flag(SAFE_BIT, True)
        g.poke(236, 15)
        g.poke(237, 0)
        m["poked"] = marks(g)
        g.warp(FIELD, entrance=WARP_A[0], scenario=WARP_A[1])
        g.wait_control(timeout=60)
        g.wait_frames(30)
        m["warpA"] = m["quiet0"] = marks(g)
        g.wait_frames(150)
        m["quiet1"] = marks(g)
        g.warp(FIELD, entrance=WARP_B[0], scenario=WARP_B[1])
        g.wait_control(timeout=60)
        g.wait_frames(30)
        m["warpB"] = m["reset"] = marks(g)
        g.soft_reset()
        _continue_from_title(g)
        g.wait_control(timeout=60)
        g.wait_frames(30)
        m["loaded"] = marks(g)
        g.flag(SAFE_BIT, False)
        g.storytrace(False)
        rows = g.story_rows()
    finally:
        (g.run_dir / "story_rung1.jsonl").write_text(g.channel.story_text() or "", encoding="utf-8")
        (g.run_dir / "story_rung1_marks.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    need = ("title", "newgame", "poked", "warpA", "quiet0", "quiet1", "warpB", "reset", "loaded")
    if not g.check(all(k in m for k in need), "R1-PHASES: every phase ran", str(m)):
        return
    for ok, what, detail in analyse(rows, m):
        g.check(ok, what, detail)
    cli = subprocess.run([sys.executable, "-m", "ff9mapkit", "story-trace", "--strict",
                          str(g.run_dir / "story_rung1.jsonl")], cwd=REPO / "ff9mapkit", capture_output=True, text=True)
    (g.run_dir / "story_rung1_cli.txt").write_text(cli.stdout + cli.stderr, encoding="utf-8")
    g.check(cli.returncode == 0, "R1-CLI: `ff9mapkit story-trace --strict` reads the run back",
            f"exit {cli.returncode}; {(cli.stdout + cli.stderr)[-300:]}")
    every = g.exceptions_since(mark)
    ours = [e for e in every if e.name in THROWS and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not ours, "NC-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
            str([(e.name, e.where) for e in ours[:5]]))
