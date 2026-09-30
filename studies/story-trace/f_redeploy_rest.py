"""F-REDEPLOY, the other 41 -- every synthesized field left in FF9CustomMap, -schema and -msgs, spliced by
tools/ambient_splice.py, made to clear an arriving ambient mark in BOTH slots, one field at a time, in one run.

    py tools/play.py studies/story-trace/f_redeploy_rest.py --label f-redeploy-rest

Each id was spliced alone (its live .eb plus exactly the 38-byte ambient TAIL, checked instruction by instruction), so
each id's check below reads only its own file: a failure names one field and is undone by its own
tools/scroll_out/revert_ambient_<id>.py. The method is f_redeploy_6601's B4, which proved both slots on 6601-6603:
warp to the Southern Ring hub (4600, already spliced and proven), poke gEventGlobal[13] = [14] = 2 there after its
Main_Init ran (2 = "ambient still playing"), then debug-warp into the field. Every one of these fields was built from
the kit's one blank, so each shares 6601's prologue and TAIL; the ips are predicted per field from its live bytes.

The debug warp here only waits for the field id and the trace rows, never for control: a bench may open on a scene,
and the check is about its Main_Init, which runs before any of that. Control within 20 s is report-only.

The bits read waits for a fresh state sample. Run 1 read [13]/[14] the instant the trace rows landed, and on some
fields the newest sample was still the one published as the field began loading (fading, 2/2), with all four rows
already at the predicted ips. E2 now waits up to 10 s for a sample reading 0/0 and judges the last one it saw.
`F_REDEPLOY_ONLY=4010,30416` limits E2 to those ids (E0 still reads all 41).

Checks, registered before the run:
E0  preflight (read-only): each of the 41 live US .eb reads `restored`, and its Main_Init has the prologue's two
    `Byte[n] := 9` and the TAIL's two `Byte[n] := 0` at resolvable ips (an id still `missing` = not spliced: it fails
    E0 and is skipped, named)
E1  New Game, then a debug warp out of field 70 to the hub with control
E2  per id, THE CLEAR: arriving with [13] = [14] = 2, the field's Main_Init (entry 0, tag 0) writes [13] and [14]
    2 -> 9 at the prologue's ips and 9 -> 0 at the TAIL's ips, and the bits then read [13] == [14] == 0
E3  no exception thrown through EventEngine/EBin/StoryTrace/HarnessAgent for the whole run
Report-only: control within 20 s of each arrival; one frame per field.

RESULT (2026-09-29): ALL 41 PROVEN, over two runs archived in the MAIN repo's .harness-runs (each with driver.log).
- 20260929-195813-f-redeploy-rest (all 41, E2's first bits read): E0, E1 and E3 PASS; E2 33 of 41 PASS. The other 8
  (4010, 30416, 30801, 30911, 30921, 30925, 30930, 30935) wrote all four rows at the predicted ips and failed only
  the bits read. On each, the trace's next write to [13]/[14] is the following poke in the hub, and it reads old 0 in
  both slots: the game held 0, and the sample was stale.
- 20260929-200455-f-redeploy-rest-8 (those 8, with the fresh-sample read): 11 of 11 PASS.
Every field reached control within 20 s except 30601 (FF9CustomMap-msgs), which is report-only.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from f_redeploy_4600 import THROWS, WHERE, _byte, predicted_ips        # noqa: E402
from f_redeploy_6601 import _watch                                      # noqa: E402

HUB = 4600
IDS = {
    "FF9CustomMap": [4010, 4011, 4012, 4013, 6500,                      # shipped band first
                     30416, 30801, 30860, 30861, 30862, 30863, 30870, 30880, 30883, 30890, 30900, 30910, 30911,
                     30912, 30920, 30921, 30922, 30925, 30930, 30935, 30936, 30937, 30945, 30946, 30947, 30948,
                     30949, 30955, 30956, 30960, 31100],
    "FF9CustomMap-schema": [30820, 30821],
    "FF9CustomMap-msgs": [30601, 30602, 30603],
}


def _name(game: Path, folder: str, fid: int) -> str:
    dp = game / folder / "DictionaryPatch.txt"
    rows = [ln.split() for ln in dp.read_text(encoding="utf-8-sig").splitlines()]
    hits = [r[4] for r in rows if len(r) >= 6 and r[0] == "FieldScene" and r[1] == str(fid)]
    if len(hits) != 1:
        raise RuntimeError(f"{dp}: want exactly one `FieldScene {fid}`, found {len(hits)}")
    return hits[0]


def _live_eb(game: Path, folder: str, name: str) -> bytes:
    p = next((game / folder / "StreamingAssets").rglob(f"field/us/EVT_{name}.eb.bytes"))
    return p.read_bytes()


def preflight(game: Path) -> tuple[list, list]:
    """``(ready, refused)``: ready = ``[(folder, id, name, ips)]`` for every spliced id whose four ips resolve."""
    from ff9mapkit.content import ambient
    ready, refused = [], []
    for folder, ids in IDS.items():
        for fid in ids:
            try:
                name = _name(game, folder, fid)
                live = _live_eb(game, folder, name)
                state = ambient.classify(live)
                ips = predicted_ips(live) if state == "restored" else {}
            except (RuntimeError, StopIteration, ValueError) as err:
                refused.append((fid, f"{type(err).__name__}: {err}"[:160]))
                continue
            want = {(n, k) for n in (13, 14) for k in ("set9", "tail0")}
            if state != "restored" or set(ips) != want:
                refused.append((fid, f"{state}, ips {sorted(ips)}"))
            else:
                ready.append((folder, fid, name, ips))
    return ready, refused


def _sbyte(s, n: int):
    bits = [s.flag(8 * n + j) for j in range(8)]
    return None if None in bits else sum(1 << j for j, b in enumerate(bits) if b)


def enter(g, fid: int, *, timeout: float = 60.0) -> None:
    """Debug-warp into ``fid`` and wait only for the id -- never for control (see the module doc)."""
    g._check_field_id(fid, "warp", True)
    g.send(f"warp {fid} -1 -1")
    g.wait_for(lambda s: s.field_id == fid, timeout=timeout, what=f"field {fid} to load")


def run(g) -> None:
    from harness import HarnessError

    g.note("F-REDEPLOY rest: the 41 spliced synthesized fields, the two-slot clear per field")
    ready, refused = preflight(g.game_path)
    only = {int(x) for x in os.environ.get("F_REDEPLOY_ONLY", "").split(",") if x.strip()}
    if only:
        ready = [r for r in ready if r[1] in only]
        g.note(f"F_REDEPLOY_ONLY: {sorted(only)}")
    g.check(not refused, f"E0: all {sum(map(len, IDS.values()))} live .eb read `restored` with four resolvable ips",
            f"{len(ready)} ready; refused {refused}" if refused else f"{len(ready)} ready")
    for folder, fid, name, ips in ready:
        print(f"[rest] {fid} {name} ({folder}) predicted ips {ips}")

    g.newgame()
    mark = g.log_mark()
    g.storytrace(True)
    try:
        g.warp(HUB)
        _watch(g)
    except HarnessError as err:
        g.check(False, "E1: New Game, then a debug warp to the hub with control", str(err)[:200])
        return
    g.check(True, "E1: New Game, then a debug warp to the hub with control")

    for folder, fid, name, ips in ready:
        try:
            g.warp(HUB)
            g.poke(13, 2)
            g.poke(14, 2)
            g.wait_for(lambda s: _byte(g, 13) == 2 and _byte(g, 14) == 2, timeout=5.0, what="the poke to land")
            line0 = max((r.line for r in g.story_rows()), default=0)
            enter(g, fid)

            def rows():
                return [r for r in g.story_rows() if r.k == "w" and r.fld == fid and r.sid == 0 and r.tag == 0
                        and r.byte in (13, 14) and r.line > line0]

            def hit(rs, n, kind, old, new):
                return any(r.byte == n and r.ip == ips[(n, kind)] and r.old == old and r.new == new for r in rs)

            try:
                g.wait_for(lambda s: all(hit(rows(), n, "tail0", 9, 0) for n in (13, 14)), timeout=30.0,
                           what=f"{fid}'s TAIL to clear both slots")
            except HarnessError:
                pass                                      # judged below, from whatever rows landed
            rs = rows()
            try:                                          # a sample published AFTER the rows (see the module doc)
                g.wait_for(lambda s: _sbyte(s, 13) == 0 and _sbyte(s, 14) == 0, timeout=10.0,
                           what=f"{fid}'s bits to read 0 in a fresh sample")
            except HarnessError:
                pass                                      # judged below, from the last sample
            a13, a14 = _byte(g, 13), _byte(g, 14)
            marks = {n: hit(rs, n, "set9", 2, 9) for n in (13, 14)}
            clears = {n: hit(rs, n, "tail0", 9, 0) for n in (13, 14)}
            print(f"[rest] {fid} rows: {[(r.byte, r.ip, r.old, r.new) for r in rs]}")
            g.check(all(marks.values()) and all(clears.values()) and a13 == 0 and a14 == 0,
                    f"E2 {fid} {name}: arriving with [13] = [14] = 2, it marks both 9 and its TAIL clears both 9 -> 0",
                    f"marks {marks}, clears {clears} at predicted {ips}; bits after [13]={a13} [14]={a14}")
            try:
                g.wait_playable(timeout=20.0)
                ctl = "control"
            except HarnessError:
                ctl = "no control within 20 s (report-only)"
            print(f"[rest] {fid} {ctl}")
            g.shot(f"f{fid}")
        except HarnessError as err:
            g.check(False, f"E2 {fid} {name}: the clear path ran", str(err)[:200])

    bad = [e for e in g.exceptions_since(mark) if e.name in THROWS
           and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not bad, "E3: no exception through the event engine, the whole run",
            f"{[(e.name, e.where) for e in bad[:4]]}" if bad else "none")
    g.storytrace(False)
