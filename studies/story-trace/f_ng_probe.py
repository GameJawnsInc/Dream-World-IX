"""F-PROBE -- a full-opening New Game under the story trace: does the New-Game override stop 643 before its warp?

    py tools/play.py studies/story-trace/f_ng_probe.py --label f-ng-probe

F-NG: stock field 70 marks Byte[13] := 2, plays its ambient 643 and warps Field(50), a same-id handoff (50 owns
643). The kit's override used to swap only that literal, so the New-Game target (the Southern Ring hub 4600, which
owns no ambient) was entered with 643 playing and a 2 its prologue turns into the error mark 9 (the F-REDEPLOY run
20260929-175641 traced exactly that: 70 ip475 [13] 1 -> 2, 4600 ip109 2 -> 9, then the spliced TAIL's 9 -> 0).
The fix (newgame.set_handoff) inserts 70's own exit stop before `Int16[2] := 0; Field(4600)`:
`if Byte[13] < 9 { Byte[13] := 3 }; RunSoundCode1(20864, 643, 0)`. The `:= 3` and the stop are one straight-line
block (the JMP_IFNOT skips only the `:= 3`), so a trace row at the `:= 3`'s ip means the stop op ran next.

This drives the REAL route: New Game, field 70's whole opening (no warp), and 70's own Field(4600). Deploy first,
with the owner's go: `py tools/retarget_newgame_warp.py 4600` (it rewrites the 7 live copies in FF9CustomMap-world).

Checks, registered before the run:
P0  preflight (read-only): every live copy of the override is the kit's own build from stock 70 for 4600
    (newgame.build_override), reads handoff "stop" and warps 4600; the ips below come from those bytes
P1  New Game lands in field 70, and field 70 leaves on its own script to 4600
P2  THE STOP: field 70's Main_Init writes Byte[13] 1 -> 2 at the play's ip, then 2 -> 3 at the inserted stop's
    ip, and the 2 -> 3 row precedes every 4600 row
P3  4600's prologue receives the 3: it writes Byte[13] 3 -> 0 at its `:= 0` ip; no 4600 row writes a 9, and the
    TAIL's clear never fires (nothing to clear)
P4  once control returns in 4600, gEventGlobal[13] == 0 and [14] == 0, read from watched bits 104-119
    (independent of the trace)
P5  no exception thrown through EventEngine/EBin/StoryTrace/HarnessAgent from New Game to the hub

Not measured: the sound itself. The harness has no audio channel (SoundLib.Log is a no-op in this engine), so P2
proves the stop op EXECUTED before the warp; that FF9SOUND_SNDEFFECTRES_STOP (FF9Snd.cs:695) silences a resident
sound is the engine's contract, the same op stock runs at 2,669 exits. Only an ear hears it.
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

HUB, NG = 4600, 70
NAME = "SOUTHERN_RING_HUB"
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")


def _ip_of(data: bytes, pred) -> list:
    """Entry-0 Main_Init instructions satisfying ``pred(off_in_main_init, raw)``, as trace ips (the instruction's
    start minus entry 0's start -- the model calibrated on story-rung5b2 and used by f_redeploy_4600)."""
    from ff9mapkit.eb import EbScript
    eb = EbScript.from_bytes(data)
    f = eb.entry(0).func_by_tag(0)
    e0 = eb.entry(0).abs_start
    return [i.off - e0 for i in eb.instrs(f) if pred(i.off - f.abs_start, bytes(data[i.off:i.end]))]


def _let13(v: int) -> bytes:
    """``Byte[13] := v``."""
    return bytes([0x05, 0xD4, 13, 0x7D, v, 0x00, 0x2C, 0x7F])


def predicted_ips(override: bytes, hub: bytes) -> dict:
    """The ips P2/P3 judge by, read off the live bytes: 70's play mark (its first ``:= 2``, case 0), the ``:= 3``
    inside the inserted stop, and 4600's prologue ``:= 0`` / ``:= 9`` (never the TAIL's clear)."""
    from ff9mapkit import newgame
    from ff9mapkit.content import ambient
    from ff9mapkit.eb import EbScript
    stop = ambient.exit_stop(ambient.ambient_id(override))
    seat = newgame._entrance_rel(override) - len(stop)
    f = EbScript.from_bytes(hub).entry(0).func_by_tag(0)
    tail = hub[f.abs_start:f.abs_end].find(ambient.TAIL)
    in_tail = lambda rel: tail >= 0 and tail <= rel < tail + len(ambient.TAIL)       # noqa: E731
    return {"play2": _ip_of(override, lambda rel, raw: raw == _let13(2))[0],
            "stop3": _ip_of(override, lambda rel, raw: raw == _let13(3) and seat <= rel < seat + len(stop))[0],
            "hub_let0": _ip_of(hub, lambda rel, raw: raw == _let13(0) and not in_tail(rel))[0],
            "hub_set9": _ip_of(hub, lambda rel, raw: raw == _let13(9))[0]}


def _byte(g, n: int):
    bits = [g.state.flag(8 * n + j) for j in range(8)]
    return None if None in bits else sum(1 << j for j, b in enumerate(bits) if b)


def preflight(game_path) -> tuple:
    """(ok, detail, override bytes, hub bytes) -- read-only; runnable without a game session."""
    from ff9mapkit import extract, newgame
    game_path = Path(game_path)
    copies = newgame.live_overrides(game_path)
    datas = {p: p.read_bytes() for p in copies}
    hub_p = next((game_path / "FF9CustomMap-world" / "StreamingAssets").rglob(f"field/us/EVT_{NAME}.eb.bytes"))
    hub = hub_p.read_bytes()
    stock = extract.EventBundle(game=str(game_path)).eb_for_id(NG)
    want = newgame.build_override(stock, HUB, newgame.target_ambient(game_path, HUB))
    ok = (len(copies) == 7 and all(d == want for d in datas.values()) and newgame.handoff(want) == "stop"
          and newgame.newgame_target(want) == HUB)
    detail = (f"{len(copies)} copies, all == build_override(stock 70, {HUB}): "
              f"{all(d == want for d in datas.values())}, handoff {newgame.handoff(want)}, "
              f"sha {hashlib.sha256(want).hexdigest()[:16]}")
    return ok, detail, want, hub


def run(g) -> None:
    g.note("F-PROBE: a full-opening New Game -- does the override stop 643 before Field(4600)?")
    ok, detail, override, hub = preflight(g.game_path)
    g.check(ok, "P0: the live override is the kit's build for 4600, handoff stop", detail)
    if not ok:
        return
    ips = predicted_ips(override, hub)
    print(f"[f-ng] predicted ips {ips}")

    st = g.newgame()
    mark = g.log_mark()
    g.check(st.field_id == NG, "P1a: New Game lands in field 70", f"field {st.field_id}")
    g.storytrace(True)
    t0 = time.monotonic()
    g.wait_for(lambda s: s.field_id not in (NG, 0), timeout=300.0, what="field 70 to leave on its own")
    g.check(g.state.field_id == HUB, "P1b: field 70 leaves on its own script to 4600",
            f"-> {g.state.field_id} after {time.monotonic() - t0:.0f}s")
    if g.state.field_id != HUB:
        return
    g.wait_playable(timeout=90.0)
    g.watch(*range(104, 120))
    g.wait_for(lambda s: all(s.flag(b) is not None for b in range(104, 120)), timeout=5.0,
               what="bits 104-119 to be published")
    b13, b14 = _byte(g, 13), _byte(g, 14)
    g.shot("hub-arrival")

    rows = [r for r in g.story_rows() if r.k == "w" and r.fld in (NG, HUB)
            and r.byte is not None and set(r.span) & {13, 14}]
    for r in rows:
        print(f"[f-ng] trace: fld {r.fld} sid {r.sid} tag {r.tag} ip {r.ip} byte {r.byte} w {r.width} "
              f"{r.old} -> {r.new}  line {r.line}")
    ng13 = [r for r in rows if r.fld == NG and r.byte == 13 and r.sid == 0 and r.tag == 0]
    hub13 = [r for r in rows if r.fld == HUB and r.byte == 13]
    play = [r for r in ng13 if (r.old, r.new) == (1, 2) and r.ip == ips["play2"]]
    stop = [r for r in ng13 if (r.old, r.new) == (2, 3) and r.ip == ips["stop3"]]
    first_hub = min((r.line for r in hub13), default=None)
    g.check(bool(play) and bool(stop) and stop[0].line > play[0].line
            and (first_hub is None or stop[0].line < first_hub),
            "P2: field 70 marks 2 at the play, then 3 at the inserted stop, before any 4600 row",
            f"70 rows {[(r.ip, r.old, r.new) for r in ng13]} (predicted play {ips['play2']}, "
            f"stop {ips['stop3']})")
    got0 = [r for r in hub13 if r.sid == 0 and r.tag == 0 and (r.old, r.new) == (3, 0) and r.ip == ips["hub_let0"]]
    nines = [r for r in hub13 if r.new == 9]
    clears = [r for r in hub13 if r.old == 9]
    g.check(bool(got0) and not nines and not clears,
            "P3: 4600's prologue receives the 3 and writes 3 -> 0; no 9, no TAIL clear",
            f"4600 rows {[(r.ip, r.old, r.new) for r in hub13]} (predicted := 0 at {ips['hub_let0']}, "
            f"the 9 would be {ips['hub_set9']})")
    g.check(b13 == 0 and b14 == 0, "P4: gEventGlobal[13] and [14] read 0 in the hub", f"[13]={b13} [14]={b14}")
    bad = [e for e in g.exceptions_since(mark) if e.name in THROWS
           and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not bad, "P5: no exception through the event engine, New Game to the hub",
            f"{[(e.name, e.where) for e in bad[:4]]}" if bad else "none")
    g.storytrace(False)


if __name__ == "__main__":                                   # the preflight alone, offline: py f_ng_probe.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
    from ff9mapkit.config import find_game_path
    ok, detail, override, hub = preflight(find_game_path())
    print("P0", "PASS" if ok else "FAIL", detail)
    print("ips", predicted_ips(override, hub))
