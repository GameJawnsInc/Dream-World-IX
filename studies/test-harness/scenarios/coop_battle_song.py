"""s154 -- THE RETURN'S BATTLE HALF, the SOLO bench (studies/coop-review/REVIEW.md 1.8, appendix #21; memoria-patches s154).

THE DEFECT. Stock never carries a battle song into a field load: BattleResultUI.Hide / GameOverUI run
battle.ff9ShutdownStateBattleResult before the field returns. A diorama runs that only in a FINISHED fight's settle, so every
other leave (the ~ Leave, the stall and hold caps, the s153 session-over leave, a pre-B5 host) brings the battle's song into
the return, and s153's stop keyed on the SUSPEND SLOT, warm only: a COLD return kept the battle song looping beside the
restored field song (the orphan), and a field SILENT at the boot kept the battle song as its own current song, warm or cold.
s154 stops, at EVERY return of ours, a current song that is not the song the boot found playing (NetSyncDiorama.ReturnStopsSong
keyed on _bootSong). THE KEPT-SONG LAW: a kept song survives the return only when it is the song the boot found playing.

One instance root, harness-driven, unattended, the forced selftest role. The wire bench (`netsync dioboot 67 0 wire`, the REAL
ParseView -> BootFromWire chain, song 156 -- the ending theme, distinctive on purpose) boots the diorama; `netsync dioleave` is
the ~ menu's LeaveFrom(null); the solo bench feeds no end block, so every leave is MID-FIGHT (SettleForReturn returns early).
The legs, judged on keys s153 already publishes (`netsync.battle.end.music` = GetCurrentMusicId on the field, the diorama's
`returns` / `last_return`, `netsync.world.dio.suspend_song` / `song_sid`) beside s154's receipts:

  BS-OR     the OFFLINE ORACLE over the DEPLOYED .eb bytes, before anything is judged: the silent fields (30604 COOPPARTY, 30602
            LOCKT2) run no RunSoundCode PLAY (0) / LOAD (1792) / STOPCURRENT (265) at their load (every entry's tag-0 function
            and entry 0's Main_Reinit) -- else a SIL leg's s153 red is hidden by the field's own song op -- and the song source
            (SONGSRC 30610, or COOP_BS_SONGSRC) plays exactly one literal song at its load. LOCKT2 is a shared bench other
            sessions redeploy: a deployed field is never assumed.
  BS-I      the instrument: the forced selftest role on COOPPARTY (party seeded).
  BS-S0a/b  "return song selftest: OK" and "diorama seat selftest: OK" -- s154's proof lines. N/A on an engine without
            `netsync.diorama.boot_song` (a missing line is no behaviour): recorded red with N/A named, never green, kept out of
            the predicted set.
  BS-P      silence(): a COLD `wire silent` boot on 30604 (s54's lane STOPs the field song pre-swirl, the swirl renders
            silence), left: the field's music -1 -- BS-C-SIL's precondition, asserted (never assumed).
  BS-C-SIL  [the s153 red] cold, silent at the boot (30604): after `dioleave`, every free FieldHUD sample reads music -1.
            s153: 156 on every sample (nothing suspended: the s153 seam needs a slot, and a cold return never runs it).
  BS-P2     the second silence() -- BS-W-SIL's precondition, its OWN row (s153 leaves 156 current after BS-C-SIL's red): a
            failed second silence is an unpredicted red, never a stand-in for BS-W-SIL's predicted one.
  BS-W-SIL  [the s153 red] the same WARM (30602, last_return 'warm'): s153's warm seam needs a suspended song -- 156 again.
  BS-W-SUSP [green on both: the proven path] warm with the source's song S suspended at the boot: music S, the SAME instance
            (song_sid == the pre-boot read: the restore, not a restart), the slot empty after.
  BS-C-SUSP [the review's exact shape] cold with S suspended: music S, the same instance, and (s154) `leave_song_live` false
            past the 500 ms STOPCURRENT fade -- the battle song's instance gone, no orphan beside S. N/A on s153: no s153 key
            can see the orphan (its world witness latches world boots only), so it is recorded red with N/A named.
  BS-R      `reset`: the forced role released, nothing booted.
  BS-PRE    COOP_CALIBRATE=1 only: the calibration's PREMISE, by the engine found -- s153: every predicted red is the s153
            BEHAVIOUR (song_leg's `behavioural`: the leg REACHED -- precondition, the boot's branch and slot, a free mid-fight
            leave -- and judge_return saw the return as meant with ONLY the battle song 156 wrong); a red folded in from a
            precondition, a refused boot, a wrong branch or an unreached row is not. s154: the orphan witness `leave_song_live`
            read TRUE inside a stop's own fade on at least one leg (the field latch shown armed on this DLL). Never predicted: a
            red BS-PRE reds BS-CAL.
  BS-CAL    COOP_CALIBRATE=1 only: exactly PREDICTED_S153 red on an engine without the s154 probe (the N/A set excluded from
            the equality as maybe-reds); on s154 nothing red (no lever on s154 -- the critic's simpler alternative: the s153 DLL
            is the calibration engine, and ReturnSongSelfTest's s153-seam mutant the in-engine one). The equality compares SETS
            only (cb.Ledger.judge_calibration), so the behaviour behind each red is BS-PRE's to vouch for.

THE WITNESS's CALIBRATION (named, not hidden): `leave_song_live` is HarnessBootSongLive's exact read (IsExist && !IsPaused on
the instance latched after the Leave's settle, beside a different current one) over a field boot's latch (LeaveFrom's
`_fieldLeaveSongSid`); that READ was calibrated red on a real orphan by s145 (S145-MUSIC, fakegame's `bwe_stop_missing`). The
LATCH is calibrated in-run, on the same DLL and scene (BS-PRE on s154): every leg's return stops the battle song 156 at
BeforeFieldEvents (FF9SOUND_SONG_STOPCURRENT, a native 500 ms fade -- MINIMUM_SONG_FADE_MS -- with IsExist 1), so a latch that
is armed reads TRUE on the samples inside that fade and false past it; a dropped or misplaced latch (left at -1) never reads
true. judge_return reports the in-fade count on every s154 leg (the receipt) and judges only the samples >= FADE_S past the first
FieldHUD one. The stand-in models no field music, so this is the one place the latch can be shown live.

THE PREREQS: the instance root (py tools/harness/instance.py ensure C:\\gd\\ff9-inst\\host); COOPPARTY (30604) and LOCKT2
(30602) registered (-msgs); the song source registered: SONGSRC 30610 (studies/battle-coop/bench/songsrc.field.toml, deployed
and registered in -msgs -- the default) or COOP_BS_SONGSRC=<a registered field whose deployed .eb plays one literal song at its
load>; no other FF9 from
that root, no controller, nobody at the keyboard.

    py tools/play.py studies/test-harness/scenarios/coop_battle_song.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_battle_song.py --instance C:\\gd\\ff9-inst\\host
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

PROBE = "netsync.diorama.boot_song"                        # the s154 capability (AppendDioramaReturnSong)
COLD_FIELD = cb.PARTY_FIELD                                # 30604 COOPPARTY: no Main_Reinit, no encounters -> a COLD return
WARM_FIELD = cb.FIELD                                      # 30602 LOCKT2: tag-10 Main_Reinit + [encounter] -> a WARM return
SILENT_FIELDS = (COLD_FIELD, WARM_FIELD)
SONGSRC = 30610                                            # studies/battle-coop/bench/songsrc.field.toml ([music] song = 9)
BENCH_SONG = 156                                           # NetSyncBattle.WireBenchBoot's song (the ending theme)
SCENE, PATTERN = cb.SCENE, cb.PATTERN
#: RunSoundCode codes that change the field's song at its load (the kit's content/music.py: PLAY, LOAD, STOPCURRENT)
SONG_CODES = {0: "PLAY", 1792: "LOAD", 265: "STOPCURRENT"}
SOUND_OPS = (0xC5, 0xC6, 0xC7, 0xC8)                       # RunSoundCode, RunSoundCode1/2/3 (eb/_optables.py)
BOOT_S = 30.0
SONG_S = 10.0                                              # a warp onto the song source -> its song current
HOLD_S = 1.5                                               # the return judged over this many seconds of free FieldHUD samples
FADE_S = 1.0                                               # leave_song_live judged this far past the first FieldHUD sample
LINE_RETURN = re.compile(r"\[NetSync\] diorama return \((warm|cold)\): ")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


SONG_SOURCE = _env_int("COOP_BS_SONGSRC", SONGSRC)

CHECKS = {
    "BS-OR": "the offline oracle over the DEPLOYED .eb: 30604 / 30602 run no PLAY / LOAD / STOPCURRENT at their load; the song "
             "source plays exactly one literal song there",
    "BS-I": "the instrument: the forced selftest role on COOPPARTY 30604",
    "BS-S0a": "return song selftest: OK (s154's proof line; N/A on an engine without netsync.diorama.boot_song)",
    "BS-S0b": "diorama seat selftest: OK (s154's proof line; N/A on an engine without netsync.diorama.boot_song)",
    "BS-P": "silence(): a cold `wire silent` boot on 30604, left -- the field's music -1",
    "BS-C-SIL": "cold, silent at the boot (30604): the return's music -1 on every free FieldHUD sample (s153: the battle song 156)",
    "BS-P2": "the second silence() before BS-W-SIL: a cold `wire silent` boot on 30604, left -- music -1",
    "BS-W-SIL": "warm, silent at the boot (30602): the return's music -1 on every free FieldHUD sample (s153: 156)",
    "BS-W-SUSP": "warm, the field song suspended at the boot (30602): the return plays it, the SAME instance, the slot empty",
    "BS-C-SUSP": "cold, the field song suspended at the boot (30604): the same instance back and no orphan "
                 "(leave_song_live false past the fade; N/A on an engine without it)",
    "BS-R": "`reset` releases the forced role and no diorama stays booted",
    "BS-PRE": "CALIBRATION's premise: s153 -- every predicted red is the s153 behaviour (the leg reached; only the battle song "
              "156 wrong on the return); s154 -- the orphan witness read TRUE inside a stop's fade on >= 1 leg (the latch armed)",
    "BS-CAL": "CALIBRATION: exactly the predicted rows red for the engine found",
}
#: recorded only under COOP_CALIBRATE=1, both judged in run()'s finally (finish_calibration: BS-PRE, then BS-CAL over it)
CAL_ONLY = ("BS-PRE", "BS-CAL")


def catalog(calibrate: bool) -> dict:
    """The run's ledger: every check, BS-PRE / BS-CAL only under COOP_CALIBRATE=1 (an unasked calibration is no row at all)."""
    return {k: v for k, v in CHECKS.items() if calibrate or k not in CAL_ONLY}


CATALOG = catalog(cb.CALIBRATE)
#: the calibration ledger: exactly these red on the s153 DLL (behaviour -- the battle song current on the returned field;
#: BS-PRE vouches that each one's red IS that behaviour, the set equality alone cannot)
PREDICTED_S153 = ("BS-C-SIL", "BS-W-SIL")
#: not discriminating on an engine without the s154 probe: recorded red with N/A named, never green, never predicted
NA_S153 = ("BS-S0a", "BS-S0b", "BS-C-SUSP")
#: the legs whose return stops the battle song at BeforeFieldEvents (156 current at every mid-fight leave): each one's in-fade
#: receipt can show the s154 latch armed (BS-PRE on s154)
LEGS = ("BS-C-SIL", "BS-W-SIL", "BS-W-SUSP", "BS-C-SUSP")


# ================================================================================================ the offline oracle (PURE parts)
def load_sound_ops(raw: bytes) -> list:
    """(PURE over an .eb's bytes) every RunSoundCode* op a field load runs: each entry's tag-0 function (Main_Init and every
    entry it activates -- the kit's [music] plays from an appended init entry) and entry 0's tag 10 (Main_Reinit, a warm
    return's) -> [(entry, tag, code | None, arg | None)] (None = a computed operand)."""
    from ff9mapkit.eb import EbScript
    eb = EbScript.from_bytes(bytes(raw))
    out = []
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            if f.tag == 0 or (e.index == 0 and f.tag == 10):
                for ins in eb.instrs(f):
                    if ins.op in SOUND_OPS:
                        code, arg = ins.imm(0), ins.imm(1)
                        out.append((e.index, f.tag, None if code is None else int(code), None if arg is None else int(arg)))
    return out


def song_changers(ops) -> list:
    """The ops of :func:`load_sound_ops` that can change the current song at the load: PLAY / LOAD / STOPCURRENT, or a computed
    code (it could be one of them)."""
    return [op for op in ops if op[2] is None or op[2] in SONG_CODES]


def judge_oracle(ops_by_field: dict, source: int) -> dict:
    """(PURE) BS-OR. ``ops_by_field``: field id -> (load_sound_ops list | None, where) for each silent field and the song source.
    -> {"problems": {name: why}, "silent_ok": bool, "song": the source's song or None, "facts": {...}}."""
    out = {"problems": {}, "facts": {}, "silent_ok": True, "song": None}
    for fld in SILENT_FIELDS:
        ops, where = ops_by_field.get(fld, (None, f"field {fld}: not read"))
        if ops is None:
            out["problems"][f"field {fld}"] = where
            out["silent_ok"] = False
            continue
        bad = song_changers(ops)
        out["facts"][f"field {fld}"] = f"{where}: {len(ops)} load-time sound op(s)"
        if bad:
            out["problems"][f"field {fld}"] = (f"{where}: its load runs {[(SONG_CODES.get(c, 'computed'), a) for _e, _t, c, a in bad]} "
                                               f"-- a song op there hides the battle song a SIL leg must see")
            out["silent_ok"] = False
    ops, where = ops_by_field.get(source, (None, f"field {source}: not read"))
    if ops is None:
        out["problems"]["song source"] = where
        return out
    plays = sorted({a for _e, _t, c, a in ops if c == 0 and a is not None})
    computed = [op for op in ops if op[2] is None or (op[2] == 0 and op[3] is None)]
    out["facts"]["song source"] = f"{where}: PLAY {plays}"
    if len(plays) != 1 or computed:
        out["problems"]["song source"] = (f"{where}: its load plays {plays} (computed ops {computed}) -- the bench wants exactly one "
                                          "literal song")
    elif plays[0] == BENCH_SONG or plays[0] < 0:
        out["problems"]["song source"] = f"{where}: its song {plays[0]} is the wire bench's own battle song (it cannot tell them apart)"
    else:
        out["song"] = plays[0]
    return out


# ================================================================================================ pure readers / judges
def music(x):
    """GetCurrentMusicId as the agent publishes it on every scene (`netsync.battle.end.music`; -1 = none / unreadable)."""
    v = cb.path(x, "netsync.battle.end.music")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def song_sid(x):
    v = cb.path(x, "netsync.world.dio.song_sid")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def suspend_song(x):
    v = cb.path(x, "netsync.world.dio.suspend_song")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def has_probe(x) -> bool:
    return cb.has(x, PROBE)


def on_field_free(s, field: int) -> bool:
    return s is not None and s.ui_state == "FieldHUD" and s.field_id == field and cb.free(s)


def judge_return(timed, field: int, *, want_music: int, mode: str, returns0, sid=None, probe: bool = False,
                 fade_s: float = FADE_S) -> tuple:
    """(PURE) one leg's return over ``timed`` = [(wall_s, state)] from the `dioleave` on: the return counted (returns +1, the
    branch ``mode``, on ``field``), every FREE FieldHUD sample on ``field`` reads ``want_music`` (and ``sid``, the pre-boot
    instance, when given), the slot empty; on an s154 engine (``probe``) `leave_song_live` false on every FieldHUD sample at
    least ``fade_s`` past the first one (the battle song's instance gone, not fading). -> (ok, detail, facts):
      facts["behavioural"]  the s153 SHAPE, the one a predicted red must have (BS-PRE): the return happened as meant (counted,
                            ``mode``, on ``field``, the instance and the slot as wanted) and ONLY the battle song was wrong -- the
                            music over the free samples off ``want_music`` by exactly [BENCH_SONG]. False on every other red and
                            on a green.
      facts["live_inside"]  (``probe`` only, else None) the FieldHUD samples on ``field`` LESS than ``fade_s`` past the first one
                            that read `leave_song_live` TRUE: the stop's own 500 ms STOPCURRENT fade seen by an ARMED field latch
                            (the in-run receipt; a latch left at -1 never reads true). A receipt, never part of ``ok``."""
    # [ff9mapkit netsync s154 calibration] THE PRE-INIT SAMPLE: the field reads FieldHUD, not fading and not booted from its level
    # load on, but its first HonoUpdate (the init: ff9InitStateFieldMap -> BeforeFieldEvents, where the seam stops the song, the
    # suspend slot is restored and `returns` is counted) can lag the harness publish by a frame or more (no execution order between
    # HarnessAgent and HonoBehaviorSystem; frames with no logic tick). Such a sample still reads the BATTLE's music and the slot full
    # on EVERY engine (the first s153 calibration run: f3562 read 156 / sid 22 / slot 9, f3564 read the restored 9 / sid 18 / slot
    # empty). Only samples AFTER the return was counted are the return's -- the counter moves inside that same init.
    def after_init(s) -> bool:
        r = cb.path(s, "netsync.diorama.returns")
        return isinstance(r, int) and isinstance(returns0, int) and r > returns0
    pre_init = sum(1 for _t, s in timed if on_field_free(s, field) and not after_init(s))
    free = [(t, s) for t, s in timed if on_field_free(s, field) and after_init(s)]
    if not free:
        last = timed[-1][1] if timed else None
        return False, (f"no free FieldHUD sample on {field} after the return was counted ({pre_init} before it; last: ui "
                       f"{getattr(last, 'ui_state', None)!r} field {getattr(last, 'field_id', None)!r} returns "
                       f"{cb.path(last, 'netsync.diorama.returns') if last is not None else None!r}, want > {returns0})"),\
            {"behavioural": False, "live_inside": None}
    end = free[-1][1]
    r1 = cb.path(end, "netsync.diorama.returns")
    counted = isinstance(r1, int) and isinstance(returns0, int) and r1 == returns0 + 1
    branch = cb.path(end, "netsync.diorama.last_return")
    on = cb.path(end, "netsync.diorama.last_return_field")
    musics = [music(s) for _t, s in free]
    wrong = sorted({m for m in musics if m != want_music}, key=lambda m: (m is None, m))
    sids = sorted({song_sid(s) for _t, s in free if sid is not None} - {sid}, key=lambda v: (v is None, v))
    slots = sorted({suspend_song(s) for _t, s in free} - {-1}, key=lambda v: (v is None, v))
    as_meant = counted and branch == mode and on == field and not sids and not slots
    ok = as_meant and not wrong
    behavioural = as_meant and wrong == [BENCH_SONG]
    detail = (f"returns {returns0}->{r1} (want +1), last_return {branch!r} on {on} (want {mode!r} on {field}); music over "
              f"{len(free)} free FieldHUD sample(s) after the return's init {sorted(set(musics), key=lambda m: (m is None, m))} "
              f"(want only {want_music}{'; WRONG ' + str(wrong) if wrong else ''}; {pre_init} pre-init sample(s) not judged)")
    if sid is not None:
        detail += f"; song_sid {'kept ' + str(sid) if not sids else 'CHANGED to ' + str(sids) + ' (a restart, not the restore)'}"
    detail += f"; suspend slot {'empty' if not slots else 'HOLDS ' + str(slots)}"
    live_inside = None
    if probe:
        fh = [(t, s) for t, s in timed if s is not None and s.ui_state == "FieldHUD" and s.field_id == field
              and after_init(s)]   # the stop's fade starts at the init (BeforeFieldEvents), never at a pre-init sample
        t0 = fh[0][0] if fh else None
        late = [s for t, s in fh if t0 is not None and t - t0 >= fade_s]
        live = [s for s in late if cb.path(s, "netsync.diorama.leave_song_live") is not False]
        live_inside = sum(1 for t, s in fh if t - t0 < fade_s and cb.path(s, "netsync.diorama.leave_song_live") is True)
        ok = ok and bool(late) and not live
        detail += (f"; leave_song_live false on {len(late) - len(live)}/{len(late)} sample(s) >= {fade_s:g} s past the first "
                   f"FieldHUD one" + (" -- the battle song still PLAYS beside the field's (the orphan)" if live else "")
                   + ("" if late else " -- NONE that late: not judged, so red"))
        detail += (f"; the witness read TRUE on {live_inside} sample(s) inside the stop's fade (the field latch armed)" if live_inside
                   else "; the witness never read TRUE inside the stop's fade (the latch not shown armed on this leg)")
    return ok, detail, {"behavioural": behavioural, "live_inside": live_inside}


def judge_booted(st, *, want_mode: str, want_slot: int) -> tuple:
    """(PURE) the leg's boot as the bench meant it: a diorama up (BattleMapDebug, battle.debug), the boot's branch (warm /
    cold), the battle song current and the slot holding ``want_slot`` (-1 = nothing suspended). (ok, detail)."""
    if st is None:
        return False, "the diorama never came up with the battle song current"
    mode = cb.path(st, "netsync.diorama.boot")
    m, slot = music(st), suspend_song(st)
    ok = cb.in_diorama(st) and mode == want_mode and m == BENCH_SONG and slot == want_slot
    return ok, f"booted {mode!r} (want {want_mode!r}), music {m!r} (want {BENCH_SONG}), suspend slot {slot!r} (want {want_slot})"


def calibration(probe: bool) -> tuple:
    """(PURE) (predicted, maybe) for BS-CAL by the engine found: s153 (no probe) -> PREDICTED_S153 with the N/A rows as maybe;
    s154 -> nothing red (no lever)."""
    return (PREDICTED_S153, NA_S153) if not probe else ((), ())


def premise(probe: bool, facts: dict) -> tuple:
    """(PURE) BS-PRE over the legs' facts (cid -> song_leg's facts; a row recorded through unreached() has none). s153 (no probe):
    every PREDICTED_S153 row was REACHED and red BY THE BEHAVIOUR (facts["behavioural"]) -- the set equality BS-CAL judges
    cannot see why a row went red. s154: at least one leg's `leave_song_live` read TRUE inside its stop's fade (the field latch
    shown armed on this DLL: the one positive control BS-C-SUSP's green-only witness has). (ok, detail)."""
    if not probe:
        def say(c):
            f = facts.get(c)
            return f"{c}: never ran (recorded not reached)" if f is None else (
                f"{c}: reached {f['reached']}, behavioural {f['behavioural']}")
        bad = [c for c in PREDICTED_S153 if not (facts.get(c) or {}).get("behavioural")]
        return not bad, (f"pre-s154: {'; '.join(say(c) for c in PREDICTED_S153)}"
                         + (f" -- NOT the s153 behaviour: {bad} (their reds prove nothing about the seam)" if bad else
                            " -- every predicted red is the battle song 156 current on a return that happened as meant"))
    seen = {c: (facts.get(c) or {}).get("live_inside") for c in LEGS}
    hits = [c for c, n in seen.items() if n]
    return bool(hits), (f"s154: leave_song_live TRUE inside the stop's fade per leg {seen}"
                        + (f" -- the field latch shown armed on {hits}" if hits else
                           " -- on NO leg: the witness BS-C-SUSP rests on was never shown able to read true"))


def finish_calibration(led, probe: bool, facts: dict) -> None:
    """run()'s finally under COOP_CALIBRATE=1: BS-PRE (the premise), then BS-CAL over every row -- a red BS-PRE is an
    unpredicted red there, so BS-CAL passes only on the behaviour (s153) or a latch shown armed (s154)."""
    led.check("BS-PRE", *premise(probe, facts))
    predicted, maybe = calibration(probe)
    led.judge_calibration("BS-CAL", predicted, maybe)


# ================================================================================================ the moves
def _timed_watch(g, until, timeout: float) -> tuple:
    """Every distinct published frame with its wall time until ``until(state)`` holds or ``timeout`` runs out:
    ([(t, state)], the ending state or None)."""
    out, seen = [], None
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = g.state
        if st.frame != seen:
            seen = st.frame
            out.append((time.time(), st))
            try:
                if until(st):
                    return out, st
            except (TypeError, KeyError, AttributeError, IndexError, ValueError):
                pass
        time.sleep(0.004)
    return out, None


def _wire_boot(g, *, silent: bool = False) -> tuple:
    """`netsync dioboot 67 0 wire [silent]` and wait for the diorama with its song current (156, or none for `silent`).
    (booted state | None, why)."""
    args = [SCENE, PATTERN, "wire"] + (["silent"] if silent else [])
    for attempt in range(2):
        at = cb.mark(g)
        ok, why = cb.try_ns(g, "dioboot", *args)
        if ok:
            break
        logged = cb.grep(cb.wait_log(g, at, cb.BOOT_REFUSED, 2.0), cb.BOOT_REFUSED, limit=240)
        if attempt or cb.FADE_REFUSAL not in (why + " " + logged):   # only a fade refusal is retried, once (cb.boot's rule)
            return None, f"dioboot refused: {why}" + (f" -- log: {logged}" if logged else "")
        g.wait_frames(30)
    want = (lambda s: cb.in_diorama(s) and music(s) == -1) if silent else (lambda s: cb.in_diorama(s) and music(s) == BENCH_SONG)
    st = cb.poll(g, want, BOOT_S, "the wire diorama up with its song current")
    if st is None:
        s = g.state
        return None, f"no diorama with its song (scene {s.scene!r}, music {music(s)!r}, booted {cb.dio(s).get('booted')!r})"
    return st, ""


def _leave_timed(g, field: int) -> tuple:
    """`netsync dioleave` (a fade defers it: retried) and every publish from it until ``field`` is free AFTER the return's init
    (`netsync.diorama.returns` past its value at the leave), then HOLD_S more. ([(t, state)], why).
    [ff9mapkit netsync s154 calibration] a free sample BEFORE the init (THE PRE-INIT SAMPLE, judge_return) used to start the hold:
    on a cold return whose Main_Init keeps control off past HOLD_S (the first s154 run's BS-C-SUSP: control off from the init on),
    the hold then ended with no free sample the judge may read."""
    r0 = cb.path(g.state, "netsync.diorama.returns")
    counted = (lambda s: isinstance(cb.path(s, "netsync.diorama.returns"), int)
               and cb.path(s, "netsync.diorama.returns") > r0) if isinstance(r0, int) else (lambda s: True)
    for attempt in range(4):
        ok, why = cb.try_ns(g, "dioleave")
        if ok:
            break
        if "deferred" not in why or attempt == 3:
            return [], f"dioleave refused: {why}"
        g.wait_frames(30)
    timed, hit = _timed_watch(g, lambda s: on_field_free(s, field) and counted(s), cb.LEAVE_S)
    if hit is None:
        return timed, f"no free return to {field} after its init (returns past {r0!r})"
    more, _ = _timed_watch(g, lambda s: False, HOLD_S)
    return timed + more, ""


def silence(g) -> tuple:
    """The SIL legs' precondition: on COLD_FIELD a `wire silent` boot and its leave (s54's cold lane STOPs the field song; the
    swirl renders silence) -> the field's music -1, read (never assumed). (ok, detail)."""
    try:
        if g.state.field_id != COLD_FIELD:
            g.warp(COLD_FIELD)
        ok, why = cb.arrive(g, COLD_FIELD)
        if not ok:
            return False, f"silence: {why}"
    except HarnessError as err:
        return False, f"silence: the warp to {COLD_FIELD} failed: {str(err)[:200]}"
    st, why = _wire_boot(g, silent=True)
    if st is None:
        return False, f"silence: {why}"
    timed, why = _leave_timed(g, COLD_FIELD)
    free = [s for _t, s in timed if on_field_free(s, COLD_FIELD)]
    musics = sorted({music(s) for s in free}, key=lambda m: (m is None, m))
    ok = not why and bool(free) and musics == [-1]
    return ok, (why + "; " if why else "") + f"music after the silent boot's return {musics} (want [-1])"


def _warp_music(g, field: int, want: int, timeout: float = 3.0) -> tuple:
    """Warp onto ``field`` and read its music once free (a debug warp never touches the music: a song carries): (ok, detail,
    state)."""
    try:
        g.warp(field)
        ok, why = cb.arrive(g, field)
    except HarnessError as err:
        return False, f"the warp to {field} failed: {str(err)[:200]}", g.state
    if not ok:
        return False, why, g.state
    st = cb.poll(g, lambda s: music(s) == want, timeout, f"music {want} on {field}") or g.state
    return music(st) == want, f"field {field}: music {music(st)!r} (want {want})", st


def _leg_facts(reached: bool = False, behavioural: bool = False, live_inside=None) -> dict:
    return {"reached": bool(reached), "behavioural": bool(behavioural), "live_inside": live_inside}


def song_leg(g, *, field: int, warm: bool, song: int | None, probe: bool) -> tuple:
    """One return leg on ``field``: the boot (warm/cold, ``song`` suspended or silent), the mid-fight leave, the return judged.
    ``song`` None = a SIL leg (silent at the boot), else a SUSP leg (``song`` carried onto ``field`` from the song source).
    -> (ok, detail, facts) -- the caller records it (:func:`record_leg`). facts["reached"]: every precondition held -- the field's
    music before the boot, a boot with its battle song, the boot's branch and slot as meant (judge_booted), a leave that came back
    free, a MID-FIGHT leave (end_leave.settled False) -- so only judge_return decides the leg; facts["behavioural"]: reached AND
    judge_return's s153 shape (only the battle song wrong); facts["live_inside"]: judge_return's in-fade receipt (s154)."""
    mode = "warm" if warm else "cold"
    if song is None:
        if g.state.field_id != field:
            ok, why, st0 = _warp_music(g, field, -1)
        else:
            st0 = g.state
            ok, why = music(st0) == -1, f"field {field}: music {music(st0)!r} (want -1)"
    else:
        ok, why, st0 = _warp_music(g, SONG_SOURCE, song, SONG_S)
        if ok:
            ok, why, st0 = _warp_music(g, field, song)
    if not ok:
        return False, f"not reached: the precondition -- {why}; reached False, behavioural False", _leg_facts()
    sid0, r0 = song_sid(st0), cb.path(st0, "netsync.diorama.returns")
    at = cb.mark(g)
    booted, why = _wire_boot(g)
    if booted is None:
        return False, f"not reached: {why}; reached False, behavioural False", _leg_facts()
    b_ok, b_why = judge_booted(booted, want_mode=mode, want_slot=-1 if song is None else song)
    timed, why = _leave_timed(g, field)
    r_ok, r_why, r_facts = judge_return(timed, field, want_music=-1 if song is None else song, mode=mode, returns0=r0,
                                        sid=sid0 if song is not None else None, probe=probe)
    lines = cb.new(g, at)
    settled = cb.path(timed[-1][1], "netsync.battle.end.end_leave.settled") if timed else None
    receipts = cb.grep(lines, "diorama return (", "diorama return:", "diorama RETURN", limit=400)
    reached = b_ok and not why and settled is False
    behavioural = reached and r_facts["behavioural"]
    return (reached and r_ok,
            f"BOOT {b_why}; RETURN {r_why}" + (f"; {why}" if why else "") + f"; end_leave.settled {settled!r} (want False: "
            f"mid-fight); reached {reached}, behavioural {behavioural} (the s153 shape: reached, only {BENCH_SONG} wrong); "
            f"receipts: {receipts or 'none'}",
            _leg_facts(reached, behavioural, r_facts["live_inside"]))


def record_leg(led, facts: dict, cid: str, result) -> None:
    """Record one :func:`song_leg` result as ``cid`` and keep its facts for BS-PRE (a row recorded through ``led.unreached``
    has none: :func:`premise` reads it as not behavioural)."""
    ok, detail, f = result
    facts[cid] = f
    led.check(cid, ok, detail)


def _oracle_or_problem(game) -> dict:
    try:
        return read_oracle(Path(game))
    except Exception as err:                               # noqa: BLE001 - an unreadable oracle is a named problem, never a pass
        return {"problems": {"oracle": f"{type(err).__name__}: {str(err)[:200]}"}, "facts": {}, "silent_ok": False, "song": None}


def sil_legs(g, led, oracle: dict, probe: bool, facts: dict) -> None:
    """BS-P, BS-C-SIL, BS-P2, BS-W-SIL in run()'s order -- the SHIPPED sequence (the tests drive it with silence / song_leg
    stubbed). Each SIL leg's precondition is its OWN row (BS-P, BS-P2), never folded into the leg's: a failed silence is an
    unpredicted red, so it can never pass for the s153 behaviour the leg predicts."""
    ok, why = silence(g)
    led.check("BS-P", ok, why)
    if not oracle["silent_ok"]:
        led.unreached(["BS-C-SIL", "BS-P2", "BS-W-SIL"], f"the oracle (BS-OR) cannot vouch for the silent fields: "
                                                          f"{oracle['problems']}")
        return
    if not ok:
        led.unreached(["BS-C-SIL", "BS-P2", "BS-W-SIL"], f"the silence precondition (BS-P) failed ({why[:200]})")
        return
    record_leg(led, facts, "BS-C-SIL", song_leg(g, field=COLD_FIELD, warm=False, song=None, probe=probe))
    ok, why = silence(g)                           # s153 leaves 156 current after a SIL red: silence again, read
    led.check("BS-P2", ok, why)
    if not ok:
        led.unreached(["BS-W-SIL"], f"the second silence (BS-P2) failed ({why[:200]})")
        return
    record_leg(led, facts, "BS-W-SIL", song_leg(g, field=WARM_FIELD, warm=True, song=None, probe=probe))


def run(g, field: int = COLD_FIELD):
    """The solo bench (``field`` is play.py's; the legs pick their own fields)."""
    # BS-PRE and BS-CAL are judged in the finally (finish_calibration), over every other row; the legs' facts feed BS-PRE
    led = cb.Ledger(g, CATALOG, finals=CAL_ONLY, width=1600)
    probe = False
    facts: dict = {}
    try:
        oracle = _oracle_or_problem(g.game_path)
        led.check("BS-OR", not oracle["problems"], f"problems {oracle['problems'] or 'none'}; read {oracle['facts']}")
        at0 = cb.mark(g)
        ok, why = cb.setup(g, COLD_FIELD, label="s154 the return's battle half, solo")
        led.check("BS-I", ok, why)
        if not ok:
            led.close("the forced selftest role did not arm")
            return
        st = g.state
        probe = has_probe(st)
        g.note(f"engine: {'s154 (netsync.diorama.boot_song published)' if probe else 'pre-s154 (no ' + PROBE + ')'}; "
               f"{cb.stage_note(st)}; the song source {SONG_SOURCE}")
        cb.wait_log(g, at0, "return song selftest:", timeout=20.0)
        lines = cb.wait_log(g, at0, "diorama seat selftest:", timeout=5.0)
        for cid, needle in (("BS-S0a", "return song selftest:"), ("BS-S0b", "diorama seat selftest:")):
            got = [ln for ln in lines if needle in ln]
            if not probe:
                led.check(cid, False, f"N/A -- not discriminating on this engine (no {PROBE}): a missing proof line is no "
                                      f"behaviour; seen {cb.grep(lines, needle) or 'none'}")
            else:
                led.check(cid, bool(got) and "OK (" in got[-1], cb.grep(lines, needle) or "no line")
        sil_legs(g, led, oracle, probe, facts)
        song = oracle["song"]
        if song is None:
            led.unreached(["BS-W-SUSP", "BS-C-SUSP"], f"no song source: {oracle['problems'].get('song source')}")
        else:
            record_leg(led, facts, "BS-W-SUSP", song_leg(g, field=WARM_FIELD, warm=True, song=song, probe=probe))
            ok, detail, facts["BS-C-SUSP"] = song_leg(g, field=COLD_FIELD, warm=False, song=song, probe=probe)
            if probe:
                led.check("BS-C-SUSP", ok, detail)
            else:
                # the review's exact shape still RUNS here (its orphan really plays), but no pre-s154 key can see the orphan
                led.check("BS-C-SUSP", False, f"N/A -- not discriminating on this engine (no {PROBE}): its only orphan witness "
                                              f"latches world boots, and music / song_sid read the restored song alike. "
                                              f"Measured: {detail}")
        at = cb.mark(g)
        cb.release(g, led, "BS-R", at=at)
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"the run raised ({str(err)[:200]})")
    finally:
        led.close()
        if cb.CALIBRATE:
            finish_calibration(led, probe, facts)
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'battle-song')}")
        led.close(final=True)


# ================================================================================================ the oracle's reads
def read_oracle(game: Path, source: int | None = None) -> dict:
    """BS-OR over the DEPLOYED bytes (coop_world_wait.deployed_field_eb: the highest stacked folder that registers the field and
    ships its EVT_*.eb.bytes), READ-ONLY. A SEAM: the tests stub it."""
    import coop_world_wait as cw                           # the stacked-folder reader (imported, never copied)
    src = SONG_SOURCE if source is None else int(source)
    ops_by_field = {}
    for fld in (*SILENT_FIELDS, src):
        raw, where = cw.deployed_field_eb(Path(game), fld)
        if raw is None:
            ops_by_field[fld] = (None, where)
            continue
        try:
            cw._kit()
            ops_by_field[fld] = (load_sound_ops(raw), where)
        except Exception as err:                           # noqa: BLE001 - a parse fault is a named problem
            ops_by_field[fld] = (None, f"{where}: {type(err).__name__}: {str(err)[:160]}")
    return judge_oracle(ops_by_field, src)
