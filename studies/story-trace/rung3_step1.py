"""THE STORY-WRITE TRACE, RUNG 3 STEP 1 -- can the stock Dali morning be driven unattended, and does the trace
see the one write that matters? One stock run: no deploy, no relaunch, no DLL.

    py tools/play.py studies/story-trace/rung3_step1.py --label story-rung3-s1 --timeout 180

THE ROUTE IS NOT CHOSEN. The start is the story's own: the village entrance 359 at SC 2540 (312 writes 2540 and
leaves only to the world map; 359 reads neither SC nor its entrance and sets the party itself), and the game plays
359 -> 351 -> 352 (arrival, the inn, the night, the wake) on its own. From control in 352 a BLIND tour crosses
every exit of every field it reaches -- in the order `eventscan.scan_gateways` lists them, bounded by the in-game
location label "Dali/" (not by FBG zone: 450 Dali/Field is zone `airp`, the village `vgdl`), never talking to
anyone, ignoring ATE prompts -- until the scenario counter LEAVES 2600, i.e. until the story itself moves on. The
research (studies/story-trace/PLAN.md, rung 3) found that SC 2610 needs latch 2079, 2079 needs bit 2102, and only
field 450 writes 2102 = 1 -- so "until the story moves on" reaches 450 without anyone choosing it. This run tests
that claim; it does not assume it.

S1-SEGMENT  the scripted segment hands control back in 352 at SC 2600
S1-TOUR     the tour ran: crossings attempted / landed, the fields reached, the stop reason
S1-PING     the premise: a script write Bit[2102] := 1 in field 450 -- and the WRITERS of 2102 := 1 are only 450
S1-ADVANCE  the story moved on (SC left 2600) inside the budget
S1-JOIN     every script row joins its store in the stock bytes
NC-THROW
"""
from __future__ import annotations

import json
import sys
import time
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit import eventscan, extract, storytrace as T  # noqa: E402

try:
    from harness import HarnessError
except ImportError:
    from tools.harness import HarnessError  # noqa: E402

START, START_SC, BEAT = 359, 2540, 2600
LABEL = "Dali/"
MAX_CROSSINGS, MAX_PASSES, BUDGET_S = 80, 3, 40 * 60
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")

_names: dict = {}
_exits: dict = {}
_stock = T.stock_script_source()


def label(fid: int) -> str:
    if fid not in _names:
        rows = [r for r in extract.find_fields(str(fid)) if int(r["id"]) == fid]
        _names[fid] = (rows[0]["name"] or "") if rows else ""
    return _names[fid]


def exits(fid: int) -> list:
    """This field's walk-in exits, in scan order, bounded by the location label: [(to, entrance, cx, cz)]."""
    if fid not in _exits:
        idx = _stock(fid)
        out = []
        for gw in (eventscan.scan_gateways(idx.data) if idx else []):
            if not label(gw["to"]).startswith(LABEL):
                continue
            zone = gw["zone"]
            cx = sum(p[0] for p in zone) / len(zone)
            cz = sum(p[1] for p in zone) / len(zone)
            out.append((gw["to"], gw["entrance"], cx, cz))
        _exits[fid] = out
    return _exits[fid]


def settle(g, log, why: str) -> None:
    """Sit through whatever the game plays until the player has control again."""
    st = g.state
    if not st.control:
        pages = g.watch_cutscene(timeout=240)
        log.append({"k": "scene", "why": why, "field": g.state.field_id, "sc": g.state.scenario,
                    "pages": len(pages), "first": (pages[0][:80] if pages else "")})


def next_hop(start: int, want) -> tuple | None:
    """BFS over the exit graph from ``start`` to the nearest field satisfying ``want``: the first exit to take."""
    seen, q = {start}, deque([(start, None)])
    while q:
        f, first = q.popleft()
        if f != start and want(f):
            return first
        for i, (to, _e, cx, cz) in enumerate(exits(f)):
            if to not in seen:
                seen.add(to)
                q.append((to, first if first is not None else (i, to, cx, cz)))
    return None


def tour(g, log) -> str:
    t0 = time.time()
    n = 0
    for p in range(1, MAX_PASSES + 1):
        tried: set = set()
        while True:
            st = g.state
            if st.scenario != BEAT:
                return f"SC left {BEAT}: now {st.scenario} in field {st.field_id} (pass {p}, crossing {n})"
            if n >= MAX_CROSSINGS or time.time() - t0 > BUDGET_S:
                return f"budget spent (crossings {n}, {time.time() - t0:.0f}s)"
            f = st.field_id
            mine = [(i, x) for i, x in enumerate(exits(f)) if (f, i) not in tried]
            if mine:
                i, (to, _e, cx, cz) = mine[0]
                tried.add((f, i))
                leg = "tour"
            else:
                hop = next_hop(f, lambda h: any((h, j) not in tried for j in range(len(exits(h)))))
                if hop is None:
                    break                                            # this pass has crossed everything
                i, to, cx, cz = hop
                leg = "back"
            n += 1
            rec = {"k": "cross", "n": n, "pass": p, "leg": leg, "from": f, "exit": i, "to": to,
                   "target": [round(cx), round(cz)], "sc0": st.scenario}
            try:
                r = g.cross(cx, cz, timeout=20)
                rec.update(reached=r.get("reached"), travelled=round(r.get("travelled") or 0), landed=r.get("landed"))
                if r.get("landed") is None and not r.get("reached"):
                    g.shot(f"stuck-{n}-{f}-to-{to}")
            except HarnessError as err:
                rec.update(error=str(err)[:200])
            settle(g, log, f"after crossing {n}")
            rec.update(now=g.state.field_id, sc1=g.state.scenario, t=round(time.time() - t0))
            log.append(rec)
            print(f"[rung3-s1] {json.dumps(rec)}")
    return f"passes exhausted ({MAX_PASSES}) without the story moving on"


def run(g) -> None:
    cap = g.state.storytrace
    if not g.check(isinstance(cap, dict) and cap.get("proto") == T.PROTO,
                   "P-CAP: the engine advertises the story trace at proto 1", str(cap)):
        return
    mark = g.log_mark()
    log: list = []
    rows: list = []
    stop = "not reached"
    seg_ok = False
    try:
        g.newgame()
        g.wait_frames(30)
        g.storytrace(True)
        g.send(f"warp {START} 0 {START_SC}")                 # raw: warp() waits for control this segment never gives
        g.wait_for(lambda s: s.field_id == START, timeout=60, what=f"field {START} to load")
        deadline = time.time() + 900
        while time.time() < deadline:
            st = g.state
            if st.field_id == 352 and st.control and st.scenario == BEAT:
                break
            if not st.control:
                pages = g.watch_cutscene(timeout=300)
                log.append({"k": "scene", "why": "segment", "field": g.state.field_id, "sc": g.state.scenario,
                            "pages": len(pages)})
            else:
                g.wait_frames(15)
        st = g.state
        seg_ok = st.field_id == 352 and st.control and st.scenario == BEAT
        log.append({"k": "segment", "field": st.field_id, "sc": st.scenario, "control": st.control})
        if seg_ok:
            g.calibrate_axes()
            stop = tour(g, log)
            settle(g, log, "after the tour")
        g.storytrace(False)
        rows = g.story_rows()
    except HarnessError as err:
        stop = f"STOPPED: {type(err).__name__}: {str(err)[:300]}"
    finally:
        (g.run_dir / "story_rung3s1.jsonl").write_text(g.channel.story_text() or "", encoding="utf-8")
        (g.run_dir / "rung3s1_log.json").write_text(json.dumps({"stop": stop, "log": log}, indent=1),
                                                     encoding="utf-8")
    g.check(seg_ok, f"S1-SEGMENT: the game's own segment 359 -> 351 -> 352 hands control back in 352 at SC {BEAT}",
            str([x for x in log if x["k"] == "segment"]))
    crossings = [x for x in log if x["k"] == "cross"]
    landed = [x for x in crossings if x.get("landed")]
    fields = sorted({x["now"] for x in crossings if x.get("now")})
    g.check(bool(crossings), "S1-TOUR: the blind tour ran",
            f"{len(crossings)} crossings, {len(landed)} landed, fields {fields}; stop: {stop}")
    run_ = T.split_runs(rows)[0] if rows else []
    ping = [r for r in run_ if r.k == "w" and r.src == "eb" and r.target == "Global.Bit[2102]" and r.new == 1]
    writers = sorted({r.don for r in ping})
    g.check(bool(ping) and writers == [450],
            "S1-PING: the story's own route wrote Bit[2102] := 1, and only field 450 wrote it",
            f"{len(ping)} rows; writers {writers}; at "
            f"{[(r.fld, r.sid, r.tag, r.ip) for r in ping[:4]]}")
    g.check(stop.startswith("SC left"), f"S1-ADVANCE: the story moved on past SC {BEAT} inside the budget", stop)
    if run_:
        import re as _re
        text = (Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX") / "Memoria.ini").read_text(
            encoding="utf-8", errors="replace")
        m = _re.search(r'^\s*FolderNames\s*=\s*(.+)$', text, _re.M)
        game = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
        roots = [game / n for n in (_re.findall(r'"([^"]+)"', m.group(1)) if m else []) if (game / n).is_dir()]
        ran = T.mod_script_source(roots, fallback=_stock)             # the bytes the game RAN (field 70 override)
        fails = []
        for r in run_:
            if r.k == "w" and r.src == "eb" and not r.add:
                idx = ran(r.fld)
                j = idx.join(r, donor=r.don) if idx else None
                if j is None or not j.ok:
                    fails.append((r.fld, r.target, r.ip, j.reason if j else "no stock script"))
        g.check(not fails, "S1-JOIN: every script row joins its store in the bytes the game ran",
                f"{len(fails)} failures {fails[:4]}")
    every = g.exceptions_since(mark)
    ours = [e for e in every if e.name in THROWS and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not ours, "NC-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
            str([(e.name, e.where) for e in ours[:5]]))
