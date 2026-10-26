"""s154 -- THE PAIRING AUTOSAVE (#17) and THE TITLE ENDS THE MIRROR (#28): the SOLO T2 bench, ONE LEG PER LAUNCH (COOP_LEG).
[ff9mapkit netsync s154]

One real game on an INSTANCE ROOT plays the GUEST; tools/harness/coop_peer.py `replay-host` replays the field-250 HOST tape
(_coop_peer_bench.latest_tape: <main repo>/.harness-runs/coop-tapes/latest.json, COOP_TAPE overrides) on a PRIVATE port the
root's own [Netsync] names (written through harness.instance -- never the install's Memoria.ini). No second game, no new
harness verb, no new state key: every judged observable is s153's.

THE DEFECTS. #17: the exit ramp reloads the guest's Continue slot (ExitMirrorToOwnSave), but nothing writes the guest's own
state there between its last own cold field entry and the first mirror (EventEngine's noSave holds every autosave from the
peer-alive edge on) -- so own progress made after that entry is LOST when the session ends. #28: a soft reset to the title
while mirroring leaves the mirror (and a ramp the title cannot fire) alive; the next New Game or Load is then refused its
menus and YANKED back by the ramp's Autoload within ~10 s.

THE LEGS (COOP_LEG):
  p17-kick     the guest on 250 with the host: New Game -> 250 -> the root's [Netsync] -> its config line (a same-field
               reload) -> 45 frames (that entry's own autosave lands) -> FREE (FieldHUD, control, menu_refusal.now 'open',
               session.state 'none') -> POKE the own byte (1122, else the first of 1123-1127 the tape's host holds at 0x00)
               to 0x3C -> the replay -> the same-field kick pairs ('paired on the host's field (250)'), the mirror arms
               (byte 1121 reads the host's 0xA5) -> the replay STOPS (--stop-at, --at-end hold) -> the grace (5 s) runs out
               -> '[NetSync] session ended -> reloading own autosave (Continue)' -> the guest playable again.
               P17K-a: byte 1122 reads 0x3C (s153: the pre-poke entry autosave, 0x00). P17K-b: byte 1121 reads 0x00 (no
               host story in the restored save -- the save-safety row, green on both).
  p17-follow   the same, standing on AWAY (30602 LOCKT2; COOP_AWAY overrides): the guest FOLLOW-WARPS to 250 and the ramp
               lands it back on AWAY. P17F-a / -b as above; P17F-c: back on AWAY. The write P17F judges is the PAIRING
               WINDOW's (its line reads '(the pairing window)'), never the follow-warp's: PairingWindowTick runs before
               ServiceIntentFollow and FollowHostTick in the same Update, so StartFollowWarp's departure attempt sees the
               verdict the window just computed (Already after the write, or the same durable decline, silent) and can
               only SPEAK a Busy decline of its own -- which no leg provokes (NOT PROVEN below).
  p17-ownwalk  the same, on AWAY, but right after the session goes live (netsync.session.peer_alive rising) the guest warps
               into 250 ITSELF (the harness `warp`, COOP_OWNWALK_FRAMES after the edge, inside the 1.2 s follow debounce),
               so the mirror arms at that landing with NO follow move. P17W-own (instrument): no follow.pending 250 before
               that landing. P17W-a / -b / -c as above. As first designed (departure sites only) s154 read 0x00 here too;
               with the PAIRING WINDOW (the peer-alive edge -> the first free-standing own frame) it reads 0x3C.
  t28-config   paired on 250 as p17-kick (no poke) -> the PSX SOFT RESET (L1 L2 R1 R2 Start Select held 8 frames in ONE
               request: Session.soft_reset; the chord fires on a later HELD frame through UIKeyTrigger.GetKey while
               FieldHUD) -> T28C-pre: ui_state 'Title' within 10 s -> at the title [Netsync] Enabled=0 -> 'config change
               applied live (disabled)' -> the title's samples -> New Game -> 25 s of samples. T28C-a NOT YANKED: no
               'session ended -> reloading own autosave (Continue)' and no sample on 250. T28C-b: mirroring false and
               ramp_pending false on the title's samples and every New-Game sample (s153: ramp_pending true, cause
               'config', at the title; the ramp's 10 s fail-safe yanks the new game to 250).
  t28-grace    as t28-config, but at the title the replay-host is STOPPED and the bench waits for session.state 'ended'
               (grace 5 s + stale 2 s + slack) before New Game (s153: the grace arms the ramp AT the title, cause 'grace').
  T28-new (both): this root's New Game must land somewhere other than 250 (measured at the leg's own first New Game), or
  "no sample on 250" could not tell the outcomes apart.

PRE-CHECKS (each reads 'not reached', never green): T2-ROOT an instance-root run (`--instance`); T2-SAND the run's saves
SANDBOXED (save_sandboxed true -- the pairing autosave is a NEW mid-session write, never onto the owner's Continue); T2-INI0
the root's [SaveFile] AutoSaveOnlyAtMoogle 0 and DisableAutoSave 0 (s154 declines its pairing autosave under either BY
DESIGN), and for t28 [Control] SoftReset 1 and [Cheats] Enabled 1 (BOTH gate the chord: UIKeyTrigger's soft-reset branch
sits inside HandleBoosterButton, which returns at once unless [Cheats] Enabled -- both engine defaults are 0); T2-TAPE the
host on 250, its story with 1121 = 0xA5 and
the own byte free of 0x3C, battle-free through the leg's replay; T2-CAL coop_cut_hold's CAL leg passed on THIS tape.

ORDER (the design's ordering notes): the poke comes AFTER the last pre-pairing field load and BEFORE the peer starts (a
load after the poke autosaves 0x3C and s153 goes green by accident); T28's title comes FIRST, the session's end second;
t28-grace's New Game only after session.state 'ended'.

CALIBRATION (COOP_CALIBRATE=1, ON THE s153 DLL FIRST): <PFX>-CAL judges exactly PREDICTED_S153[leg] red (the P17 legs: the
byte lost; the T28 legs: yanked), every instrument row green, and reads red outright when the log holds an s154 line
('pairing autosave ...', 'no pairing autosave this session', 'at the title: ...') -- that is not the s153 DLL. If P17*-a
reads 0x3C on s153 the poke reached an autosave: the leg could not fail and the run is void (its CAL reads red).
The new s154 lines are informational only (the run's notes): no leg is judged on them.

    COOP_LEG=p17-kick    py tools/play.py studies/test-harness/scenarios/coop_ramp_title.py --instance C:/gd/ff9-inst/host
    COOP_LEG=p17-follow  py tools/play.py studies/test-harness/scenarios/coop_ramp_title.py --instance C:/gd/ff9-inst/host
    COOP_LEG=p17-ownwalk py tools/play.py studies/test-harness/scenarios/coop_ramp_title.py --instance C:/gd/ff9-inst/host
    COOP_LEG=t28-config  py tools/play.py studies/test-harness/scenarios/coop_ramp_title.py --instance C:/gd/ff9-inst/host
    COOP_LEG=t28-grace   py tools/play.py studies/test-harness/scenarios/coop_ramp_title.py --instance C:/gd/ff9-inst/host
    (each again with COOP_CALIBRATE=1 on the s153 DLL first; PowerShell: clear $env:COOP_* after EVERY leg)

Prereqs: the root built (py tools/harness/instance.py ensure C:/gd/ff9-inst/host), no FF9 from it, LOCKT2 30602 registered
there, the field-250 host tape and its CAL sidecar, the private port (COOP_PEER_PORT, default 49243; 49201 is refused), no
controller connected and nobody at the keyboard (THE UNATTENDED LAW: the chord is injected, never an OS keystroke).
NOT PROVEN HERE: a world-map rejoin's pairing autosave (the world-rejoin site), a Load picked at the title (no harness verb
loads a slot), the s154 live-ladder re-check of a mid-field no-save beat (the selftest's); THE BEND CARRY -- a bounced own
gateway, or a follow landing whose mirror apply was skipped, inside the pairing window (and a cold re-entry of such a bent
place): that reload must read NOT an own place, so no pairing autosave of a field-plus-another-door's-entrance -- proven
only by the selftest's sequence rows (no leg bounces a gateway or skips the mirror apply); THE DEPARTURE SITES' own attempt
(StartFollowWarp, the same-field kick, the world rejoin): never the write here (the window ticks first in the same
Update), and their Busy decline -- an input-taking ETb line held open across the peer-alive rise and the follow start, where
s154 should log 'pairing autosave declined at the follow-warp ... not free-standing' and the ramp restore the pre-poke
autosave -- is unprovoked (no harness verb opens and holds a line deterministically); feel.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - the T2 two-role bench helpers

HarnessError = cb.HarnessError
CALIBRATE = cb.CALIBRATE

LEGS = ("p17-kick", "p17-follow", "p17-ownwalk", "t28-config", "t28-grace")
PFX = {"p17-kick": "P17K", "p17-follow": "P17F", "p17-ownwalk": "P17W", "t28-config": "T28C", "t28-grace": "T28G"}
_RAW_LEG = os.environ.get("COOP_LEG", "p17-kick").strip().lower()
LEG = _RAW_LEG if _RAW_LEG in LEGS else None

HOME = pb.BENCH_FIELD                                      # 250: the tape's field
AWAY = pb.env_int("COOP_AWAY", 30602)                      # LOCKT2 (the -msgs folder), the guest's own place for P17F / P17W
MARKER = pb.MARKER_BYTE                                    # 1121: the host's 0xA5, the guest's own 0x00
OWN_VALUE = 0x3C                                           # the guest's own progress, poked after its last pre-pairing load
OWN_BYTES = (1122, 1123, 1124, 1125, 1126, 1127)           # >= flags.FIRST_SAFE_FLAG / 8; the first the host holds at 0x00
PORT = pb.env_int("COOP_PEER_PORT", 49243)                 # a PRIVATE port (49201, the owner's bridge, is refused)
CODE = pb.BENCH_CODE
GRACE_MS, GRACE_NOTE = pb.engine_grace("5000")             # the clamp floor: a session ends ~7 s after the host goes silent
GRACE_S = GRACE_MS / 1000.0
P17_STOP_S = 20.0                                          # P17: the replay stops this long after the tape's first host frame
T28_STOP_S = 60.0                                          # T28: a late backstop only (the leg ends the session itself)
TAPE_ROOM_S = 3.0                                          # the replay must stop this long before the tape's first battle
TITLE_S = 10.0                                             # T28-pre: the chord -> ui_state 'Title'
NEW_GAME_S = 25.0                                          # T28: samples after the title's New Game (the s153 fail-safe is 10 s)
LIVE_S = 25.0
PAIR_S = 40.0
OWNWALK_FRAMES = pb.env_int("COOP_OWNWALK_FRAMES", 2)      # P17W: frames after the live edge before the own warp (< 1.2 s
                                                           # debounce - 0.9 s fade: the window gets its free-standing frames)

GUEST_VALUES = {"Enabled": "1", "Role": "client", "RelayUrl": f"ws://127.0.0.1:{PORT}", "SessionCode": CODE,
                "FollowHost": "1", "TargetField": "0", "GuestSlots": "0", "GuestStockMenu": "1",
                "SessionGraceMs": str(GRACE_MS), "AutoTeleport": "0", "DioramaSwirlFrames": "0"}

COMMON = {
    "T2-ROOT": "an instance-root run (play.py --instance): the bench writes ONLY that root's own [Netsync], through "
               "harness.instance -- never the install's Memoria.ini",
    "T2-SAND": "the run's saves are SANDBOXED (save_sandboxed true, a sandbox save_path): the pairing autosave can never land "
               "on the owner's Continue slot",
    "T2-INI0": "the root's ini as the engine reads it: [SaveFile] AutoSaveOnlyAtMoogle and DisableAutoSave off (+ t28: "
               "[Control] SoftReset 1 and [Cheats] Enabled 1 -- the soft reset sits inside HandleBoosterButton, gated on both)",
    "T2-TAPE": "the host tape reads back: the host on 250, its story with byte 1121 = 0xA5 and an own byte (1122-1127) the "
               "host holds at 0x00, no battle before the leg's replay stops",
    "T2-CAL": "coop_cut_hold's CAL leg passed on THIS tape (<tape>.cal.json, sha256-keyed): the replay instrument is trusted",
    "T2-PEER": f"port {PORT} free (never {pb.OWNER_PORT}); the guest config applied live (the engine's 'config enabled=True "
               f"role=client ... code={CODE}'); the guest dialled the replay-host and the replay started",
    "T2-SAVE": "the guest had its OWN autosave to end a session on: no 'session ended, no autosave to resume -> title screen'",
    "T2-INI": "the root's Memoria.ini put back to install + overlay (harness.instance.restore_ini, read back)",
}


def _p17_rows(p: str, start: int) -> dict:
    rows = {
        f"{p}-free": f"before the poke: on {start} FieldHUD with control, netsync.menu_refusal.now 'open', session.state 'none' "
                     "(no live host yet)",
        f"{p}-poke": f"the own progress: the own byte poked to 0x{OWN_VALUE:02X} reads it (after the last pre-pairing field load, "
                     "whose autosave holds 0x00)",
    }
    if p == "P17W":
        rows[f"{p}-own"] = ("the own walk: the guest's own warp to 250 left within its frames of the live edge and landed with NO "
                            "follow move (follow.pending never read 250 before that landing)")
    rows.update({
        f"{p}-I": ("the instrument: " + ("'paired on the host's field (250)', " if p == "P17K" else "")
                   + "'state-mirror ARMED', session.mirroring true and byte 1121 = 0xA5 on 250 before the replay stops"),
        f"{p}-ramp": "the session ends: '[NetSync] session ended -> reloading own autosave (Continue)', then the guest playable",
        f"{p}-a": f"THE OWN PROGRESS SURVIVES: after the ramp the own byte reads 0x{OWN_VALUE:02X} (s153: the pre-poke entry "
                  "autosave, 0x00)",
        f"{p}-b": "SAFETY: after the ramp byte 1121 reads 0x00 -- no host story in the restored save (both builds)",
    })
    if p in ("P17F", "P17W"):
        rows[f"{p}-c"] = f"after the ramp the guest is back on AWAY ({start}), the pairing point's field (both builds)"
    return rows


def _t28_rows(p: str) -> dict:
    rows = {
        f"{p}-I": "the instrument: 'state-mirror ARMED', session.mirroring true and byte 1121 = 0xA5 on 250, the replay live",
        f"{p}-new": "precondition: this root's New Game lands on a field other than 250 (measured at the leg's first New Game)",
        f"{p}-pre": f"the soft reset (L1 L2 R1 R2 Start Select held 8 frames, one request) reaches ui_state 'Title' within "
                    f"{TITLE_S:g} s",
    }
    if p == "T28C":
        rows[f"{p}-cfg"] = "Enabled=0 written at the title: the engine's 'config change applied live (disabled)'"
    else:
        rows[f"{p}-end"] = "the replay-host stopped at the title: session.state reads 'ended' within grace + stale + slack"
    rows.update({
        f"{p}-a": f"NOT YANKED: for {NEW_GAME_S:g} s after the title's New Game no 'session ended -> reloading own autosave "
                  "(Continue)' and no sample on 250",
        f"{p}-b": "THE MIRROR ENDS AT THE TITLE: session.mirroring false and ramp_pending false on the title's samples after the "
                  "edit / the end, and on every New-Game sample",
    })
    return rows


def leg_rows(leg: str) -> dict:
    p = PFX[leg]
    if leg.startswith("p17"):
        return _p17_rows(p, HOME if leg == "p17-kick" else AWAY)
    return _t28_rows(p)


#: COOP_CALIBRATE=1 on the s153 DLL: exactly these red (every instrument row green).
PREDICTED_S153 = {"p17-kick": ("P17K-a",), "p17-follow": ("P17F-a",), "p17-ownwalk": ("P17W-a",),
                  "t28-config": ("T28C-a", "T28C-b"), "t28-grace": ("T28G-a", "T28G-b")}


def catalog(leg: str, calibrate: bool = CALIBRATE) -> dict:
    cat = {k: v for k, v in COMMON.items() if k not in ("T2-SAVE", "T2-INI")}
    cat.update(leg_rows(leg))
    cat["T2-SAVE"] = COMMON["T2-SAVE"]
    cat["T2-INI"] = COMMON["T2-INI"]
    if calibrate:
        cat[f"{PFX[leg]}-CAL"] = ("CALIBRATION (COOP_CALIBRATE=1, the s153 DLL): exactly PREDICTED_S153 red, the instrument "
                                  "rows green, and no s154 line in the log")
    return cat


#: The s154 lines (corroboration only; written from design-ramp-autosave-title.json's logging section and the lead's
#: decisions -- a reworded line only drops a note, and arms the calibration's not-s153 guard).
S154 = {
    "pair_written": re.compile(r"^\[NetSync\] pairing autosave written on (field|world map) (\d+) \(the (.+?)\)"),
    "pair_declined": re.compile(r"^\[NetSync\] pairing autosave declined at the (.+?) on (field|world map) (\d+): (.+)$"),
    "pair_failed": re.compile(r"^\[NetSync\] pairing autosave FAILED on "),
    "no_pair": re.compile(r"^\[NetSync\] no pairing autosave this session"),
    # every form: the pending ramp consumed / the story mirror ends / a follow-warp dropped in its fade (or both, '; ')
    "title": re.compile(r"^\[NetSync\] at the title: "),
    "selftest": re.compile(r"^\[NetSync\] pairing save \+ title selftest: (OK|FAIL)"),
}


# ================================================================================================ the pure judges
def byte_of(x, byte: int):
    """A gEventGlobal byte as the WATCHED bits publish it (``flags``, LSB first); None while any of its 8 bits is
    unwatched or the document is missing."""
    raw = x.raw if hasattr(x, "raw") else (x or {})
    flags = raw.get("flags") or {}
    val = 0
    for b in range(8):
        bit = flags.get(str(byte * 8 + b))
        if bit is None:
            return None
        if bit:
            val |= 1 << b
    return val


def pick_own_byte(story, candidates=OWN_BYTES, value: int = OWN_VALUE) -> tuple:
    """(byte | None, the host's value there, why): the first candidate the tape's HOST story holds at 0x00, else the first
    it does not hold at ``value`` -- a byte the mirror would write ``value`` into could never tell the outcomes apart."""
    if not story or len(story) <= max(candidates):
        return None, None, f"no host story section long enough ({len(story or b'')} B)"
    for c in candidates:
        if story[c] == 0:
            return c, 0, f"byte {c}: the host holds 0x00"
    for c in candidates:
        if story[c] != value:
            return c, story[c], f"byte {c}: the host holds 0x{story[c]:02X} (no 0x00 candidate; not 0x{value:02X})"
    return None, None, f"every candidate {list(candidates)} holds 0x{value:02X} on the host"


def ini_verdict(vals: dict, leg: str) -> tuple:
    """The root's ini as the engine reads it (IniValue booleans: exactly "1" is on): (ok, why). ``vals`` keys:
    AutoSaveOnlyAtMoogle, DisableAutoSave, SoftReset, CheatsEnabled (None = absent: the engine default).

    T28 needs BOTH [Control] SoftReset and [Cheats] Enabled: UIKeyTrigger's soft-reset branch (``Configuration.Control.
    SoftReset && (F8 && IsPause || SoftResetKeyPSXDown)``) sits INSIDE HandleBoosterButton, whose first line returns
    unless ``Configuration.Cheats.Enabled`` (CheatsSection binds Enabled default false) -- with Cheats off the injected
    chord can never reach the title, and T28C/G-pre would read red for the instrument's sake."""
    bad = []
    for k in ("AutoSaveOnlyAtMoogle", "DisableAutoSave"):
        if str(vals.get(k) or "").strip() == "1":
            bad.append(f"[SaveFile] {k} = 1 (s154 declines its pairing autosave by design: P17 would read red on both)")
    if leg.startswith("t28"):
        if str(vals.get("SoftReset") or "").strip() != "1":
            bad.append(f"[Control] SoftReset = {vals.get('SoftReset')!r} (the chord needs 1; the engine default is 0)")
        if str(vals.get("CheatsEnabled") or "").strip() != "1":
            bad.append(f"[Cheats] Enabled = {vals.get('CheatsEnabled')!r} (the soft reset sits inside UIKeyTrigger."
                       "HandleBoosterButton, which returns at once unless it is 1; the engine default is 0)")
    return not bad, ("; ".join(bad) if bad else "read: " + ", ".join(f"{k}={v!r}" for k, v in sorted(vals.items())))


def judge_p17(after, *, own_byte: int, start: int, p: str) -> dict:
    """The P17 verdicts off the state AFTER the ramp's reload: {"a", "b", "c"} -> (ok, why)."""
    own, mk = byte_of(after, own_byte), byte_of(after, MARKER)
    raw = after.raw if hasattr(after, "raw") else (after or {})
    field = int((raw.get("field") or {}).get("id", -1))
    rows = {"a": (own == OWN_VALUE, f"own byte {own_byte} reads {own!r} (want 0x{OWN_VALUE:02X}; s153's pre-poke autosave "
                                    f"holds 0x00)"),
            "b": (mk == 0, f"byte {MARKER} reads {mk!r} (want 0x00: the host's 0x{pb.MARKER_VALUE:02X} would be host story in "
                           "the guest's save)")}
    if p in ("P17F", "P17W"):
        rows["c"] = (field == start, f"the guest on field {field} after the ramp (want {start})")
    return rows


def judge_ownwalk(samples, *, home: int, accepted: bool, cancelled: bool = False) -> tuple:
    """P17W-own: the own warp accepted, the guest landed on ``home`` (FieldHUD) BY ITS OWN WARP. A follow that STARTED inside the
    own warp's fade does not make it the follow-warp site, so long as the own load landed first; that is told apart per engine:
      * no follow.pending ``home`` before the landing -- the pure own walk (both engines);
      * s153: the follow's pending still reads ``home`` ON the landing sample (it survived the own landing: its commit had not
        run, so the landing was the own warp's);
      * s154: ``cancelled`` -- the landing step's '[NetSync] follow-warp to field <home> cancelled: this load already landed on
        it' line (the own load landed on the follow's destination first, s154's #5 fix).
    A follow pending that FELL before the landing with neither witness is the follow's own commit: not the own walk (unreached).
    [ff9mapkit netsync s154 calibration] the first s154 run: the pairing autosave's write in the rise frame left the own warp's
    0.9 s fade overlapping the 1.2 s follow debounce, a follow started 6 frames before the landing and s154 cancelled it there --
    the strict 'no pending ever' rule read that correct run as unreached."""
    land = None
    for i, s in enumerate(samples):
        raw = s.raw if hasattr(s, "raw") else s
        if int((raw.get("field") or {}).get("id", -1)) == home and raw.get("ui_state") == "FieldHUD" \
                and not raw.get("fading") and (raw.get("player") or {}).get("control"):
            land = i
            break
    upto = samples if land is None else samples[:land + 1]
    pend = [cb.path(s, "netsync.session.follow.pending") for s in upto]
    follow = [v for v in pend[:-1] if v == home] if land is not None else [v for v in pend if v == home]
    survived = land is not None and pend[-1] == home
    own_first = not follow or survived or cancelled
    ok = accepted and land is not None and own_first
    how = ("no follow move" if not follow else "a follow started inside the own warp's fade and "
           + ("survived the own landing (s153)" if survived else "was cancelled by the own landing (s154)" if cancelled
              else "FELL before the landing (its own commit: the follow's move, not the own walk)"))
    return ok, (f"own warp {'accepted' if accepted else 'REFUSED'}; landed on {home} "
                f"{'at sample ' + str(land) if land is not None else 'NEVER'} of {len(samples)}; follow.pending read {home} on "
                f"{len(follow)} sample(s) before it -- {how}")


def judge_t28(title, newgame, ramps, *, home: int) -> dict:
    """The T28 verdicts: {"a", "b"} -> (ok, why). ``title`` / ``newgame``: states (or raw docs) at the title after the edit
    or the end, and after the title's New Game; ``ramps``: the exit-ramp lines logged after that New Game."""
    def raw(s):
        return s.raw if hasattr(s, "raw") else (s or {})
    on_home = [raw(s) for s in newgame if int((raw(s).get("field") or {}).get("id", -1)) == home]
    a_ok = bool(newgame) and not ramps and not on_home
    every = list(title) + list(newgame)
    held = [raw(s) for s in every if cb.path(s, "netsync.session.mirroring") is not False
            or cb.path(s, "netsync.session.ramp_pending") is not False]
    causes = sorted({str(cb.path(s, "netsync.session.ramp_cause")) for s in held})
    b_ok = bool(title) and bool(newgame) and not held
    fields = sorted({int((raw(s).get("field") or {}).get("id", -1)) for s in newgame})
    return {"a": (a_ok, f"{len(newgame)} New-Game sample(s) on fields {fields[:8]}; on {home}: {len(on_home)}; ramp lines "
                        f"{[str(r)[:120] for r in ramps][:2] or 'none'}"),
            "b": (b_ok, f"{len(held)} of {len(every)} sample(s) ({len(title)} at the title) read mirroring / ramp_pending not "
                        f"false; ramp causes {causes or 'none'}")}


def s154_seen(msgs) -> list:
    return [m for m in msgs if any(rx.search(m) for k, rx in S154.items())]


def cal_judgement(done: dict, predicted, s154=(), cal_id: str = "") -> tuple:
    """The CAL verdict as a pure step (the CAL row itself excluded): exactly ``predicted`` red, and no s154 line."""
    if s154:
        return False, f"this engine logged s154 lines ({list(s154)[:2]}) -- COOP_CALIBRATE=1 judges the s153 DLL"
    failed = {c for c, ok in done.items() if not ok and c != cal_id}
    predicted = set(predicted)
    missing, extra = sorted(predicted - failed), sorted(failed - predicted)
    return (not missing and not extra,
            f"predicted reds that stayed GREEN: {missing or 'none'} (a green P17*-a on s153 = the poke reached an autosave: "
            f"the run is void); unpredicted reds: {extra or 'none'} (an instrument red voids the leg)")


def tape_story(records, cp):
    """The host's first type-5 story section (2048 B) on the tape, or None."""
    for _r, w, p in cp.host_frames(records):
        if w == cp.TYPE_STATE:
            sec = pb.state_sections(p)
            if 0 in sec:
                return sec[0]
    return None


# ================================================================================================ the run
class _Ctx:
    def __init__(self):
        self.tape = None
        self.facts = None
        self.own_byte = None
        self.start = HOME
        self.newgame_field = None
        self.eng = None
        self.peer = None
        self.ini_written = False
        self.anchor = None


def _run_dir(g) -> Path:
    return Path(getattr(g, "scenario_dir", None) or g.run_dir)


def run(g, field: int | None = None):
    leg = LEG or "p17-kick"
    p = PFX[leg]
    led = cb.Ledger(g, catalog(leg, CALIBRATE), finals=("T2-SAVE", "T2-INI", f"{p}-CAL"))
    ctx = _Ctx()
    try:
        if LEG is None:
            led.check("T2-ROOT", False, f"COOP_LEG={_RAW_LEG!r} is no leg: one of {LEGS}")
            led.close("not reached: no such leg")
            return
        if field is not None:
            g.note(f"--field {field} is ignored: the leg picks its own fields")
        _run(g, led, ctx, leg)
    except HarnessError as err:
        g.note(f"the leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        _teardown(g, led, ctx)
        news = s154_seen([m for _t, _l, m in ctx.eng.lines()]) if ctx.eng is not None else []
        g.note(f"s154 lines (informational): {len(news)} -- {news[:4] or 'none'}")
        if CALIBRATE and LEG is not None:
            led.close("not reached: the leg ended before this check")
            ok, why = cal_judgement(led.done, PREDICTED_S153[leg], news, f"{p}-CAL")
            g.note(f"{p}-CAL: predicted reds on s153 {list(PREDICTED_S153[leg])}")
            led.check(f"{p}-CAL", ok, why)
        led.close(final=True)


def _teardown(g, led, ctx) -> None:
    """The peer first, then the root's ini, then the log."""
    if ctx.peer is not None and ctx.peer.how_ended is None:
        g.note(f"coop_peer replay-host: {ctx.peer.stop()}")
    if "T2-SAVE" not in led.done:
        fell = pb.hits(ctx.eng.lines(), "ramp_failed") if ctx.eng is not None else []
        led.check("T2-SAVE", not fell, f"the exit ramp fell back to the TITLE: {pb.show(fell, 1)}" if fell else
                  "no title fallback" + ("" if ctx.eng is not None else " (the guest never ran a session)"))
    if "T2-INI" not in led.done:
        if not ctx.ini_written or getattr(g, "instance", None) is None:
            led.check("T2-INI", True, "the root's Memoria.ini was never edited")
        else:
            try:
                first = g.instance.restore_ini()
                second = g.instance.restore_ini()      # False = it already reads install + overlay (compared inside)
                led.check("T2-INI", second is False, f"restore_ini rewrote it: {first}; the read-back is install + overlay: "
                                                     f"{second is False}")
            except Exception as err:                  # noqa: BLE001 - the verdict names it
                led.check("T2-INI", False, f"restore_ini failed: {err} -- the root's next refresh() regenerates it")
    g.note(f"Memoria.log archived: {cb.archive_log(g, f'coop-ramp-title-{LEG or _RAW_LEG}')}")


def _run(g, led, ctx, leg: str) -> None:
    p = PFX[leg]
    rows = list(leg_rows(leg))
    # A. the instance root, the sandbox, the root's ini -- before any game action
    if getattr(g, "instance", None) is None:
        led.check("T2-ROOT", False, "not an instance-root run: this bench writes a root's own [Netsync] only (play.py "
                                    "--instance C:/gd/ff9-inst/host)")
        led.close("not reached: not an instance-root run (nothing was edited)")
        return
    led.check("T2-ROOT", True, f"root {g.instance.root}")
    st = g.state
    sp, sand = cb.raw(st).get("save_path"), cb.raw(st).get("save_sandboxed")
    led.check("T2-SAND", sand is True and bool(sp), f"save_sandboxed {sand!r}, save_path {sp!r}")
    if not (sand is True and sp):
        led.close("not reached: the saves are not sandboxed -- the bench never risks the owner's Continue slot")
        return
    vals = {"AutoSaveOnlyAtMoogle": cb.ini_value(g, "SaveFile", "AutoSaveOnlyAtMoogle"),
            "DisableAutoSave": cb.ini_value(g, "SaveFile", "DisableAutoSave"),
            "SoftReset": cb.ini_value(g, "Control", "SoftReset"), "CheatsEnabled": cb.ini_value(g, "Cheats", "Enabled")}
    ok, why = ini_verdict(vals, leg)
    led.check("T2-INI0", ok, why)
    if not ok:
        led.close("not reached: the root's ini cannot carry this leg (nothing was edited)")
        return
    # B. the tape: its facts, the own byte, the replay's span
    ctx.tape = pb.latest_tape()
    if ctx.tape is None or not ctx.tape.exists():
        led.check("T2-TAPE", False, f"no tape ({ctx.tape or pb.tape_dir()}): record one -- coop_tape_record.py")
        led.close("not reached: no tape")
        return
    try:
        cp = pb.coop_peer_module()
        _header, records, _torn = cp.read_tape(ctx.tape)
        ctx.facts = pb.tape_facts(records, cp, field=HOME)
        story = tape_story(records, cp)
    except Exception as err:                         # noqa: BLE001 -- the reason is the check's detail
        led.check("T2-TAPE", False, f"{ctx.tape} does not read back: {err}")
        led.close("not reached: the tape does not read back")
        return
    f1, f2, b = ctx.facts["f1"], ctx.facts["f2"], ctx.facts.get("battle")
    ctx.own_byte, host_own, own_why = pick_own_byte(story)
    span = T28_STOP_S if leg.startswith("t28") else P17_STOP_S
    room = (b["start"] - ctx.facts["start"]) if b else 1e9
    ok = (f1["field"] == HOME and f2["ok"] and f2.get("marker_ok") and ctx.own_byte is not None
          and room >= span + TAPE_ROOM_S)
    led.check("T2-TAPE", ok, f"{ctx.tape.name}: host on {f1.get('field')} ({f1['why']}); {f2['why']}; own byte: {own_why}; "
                             f"first battle {room:.1f} s after the start (the replay stops at +{span:g} s)")
    if not ok:
        led.close("not reached: this tape cannot carry the leg")
        return
    okc, whyc = pb.read_cal(ctx.tape)
    led.check("T2-CAL", okc, whyc)
    if not okc:
        led.close(f"not reached: the instrument is untrustworthy -- {whyc[:200]}")
        return
    if PORT == pb.OWNER_PORT:
        free, why = False, f"COOP_PEER_PORT={PORT} is the owner's bridge port -- pick a private one (default 49243)"
    else:
        free, why = pb.port_free(PORT)
    if not free:
        led.check("T2-PEER", False, why)
        led.close("not reached: the bench port is taken (nothing was edited)")
        return
    # C. the guest's own game
    cb.provenance(g)
    ctx.start = HOME if leg in ("p17-kick", "t28-config", "t28-grace") else AWAY
    g.note(f"s154 ramp/title leg {leg} ({p}): the guest on {ctx.start}; own byte {ctx.own_byte} (host 0x{host_own:02X}); "
           f"grace {GRACE_MS} ms; port {PORT}")
    g.newgame()
    ctx.newgame_field = g.state.field_id
    g.note(f"this root's New Game landed on field {ctx.newgame_field}")
    if g.state.field_id != ctx.start:
        g.warp(ctx.start)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.watch(*(MARKER * 8 + i for i in range(8)), *(ctx.own_byte * 8 + i for i in range(8)))
    # D. the root's [Netsync], the engine's own config line (a same-field reload: a pre-peer own entry, autosaved)
    ctx.eng = pb.EngineLog(g.engine_log())
    try:
        bak = g.instance.netsync(GUEST_VALUES, backup_to=_run_dir(g) / "ini")
        ctx.ini_written = True
        g.note(f"the root's [Netsync] set {GUEST_VALUES} (backup {bak})")
    except Exception as err:                         # noqa: BLE001
        led.check("T2-PEER", False, f"the root's [Netsync] write failed: {err}")
        led.close("not reached: the root's ini could not be edited")
        return
    cfg = _wait_config(g, ctx)
    if not cfg:
        led.check("T2-PEER", False, f"the engine never logged the guest config (seen: "
                                    f"{pb.show(pb.hits(ctx.eng.lines(), 'config'))})")
        led.close("not reached: the guest config never applied")
        return
    g.wait_frames(45)                                # the last pre-pairing entry's own autosave lands
    # E. P17: free-standing, then the own progress -- BEFORE the peer exists
    if leg.startswith("p17"):
        st = g.state
        ok = (st.field_id == ctx.start and st.ui_state == "FieldHUD" and st.control and not st.dialog_open and not st.fading
              and pb.path(st, "netsync.menu_refusal.now") == "open" and pb.path(st, "netsync.session.state") == "none")
        led.check(f"{p}-free", ok, f"field {st.field_id} ui {st.ui_state} control {st.control} dialog {st.dialog_open} "
                                   f"fading {st.fading}; menu_refusal.now {pb.path(st, 'netsync.menu_refusal.now')!r}; session "
                                   f"{pb.path(st, 'netsync.session.state')!r}")
        if not ok:
            led.unreached(rows, f"the guest was not free-standing on its own place before pairing ({p}-free)")
            return
        g.poke(ctx.own_byte, OWN_VALUE)
        g.wait_frames(4)
        v = byte_of(g.state, ctx.own_byte)
        led.check(f"{p}-poke", v == OWN_VALUE, f"byte {ctx.own_byte} reads {v!r}")
        if v != OWN_VALUE:
            led.unreached(rows, "the poke did not read back")
            return
    # F. the replay-host
    stop = ctx.facts["start"] + (T28_STOP_S if leg.startswith("t28") else P17_STOP_S)
    rd = _run_dir(g)
    args = [ctx.tape, "--port", str(PORT), "--code", CODE, "--at-end", "hold", "--stop-at", f"{stop:.3f}"]
    ctx.peer = pb.PeerProc("replay-host", args, log_path=rd / f"coop_peer-replay-{leg}.log",
                           out_path=rd / f"coop_peer-replay-{leg}.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0)
    conn = ctx.peer.wait_for(pb.PEER["guest_connected"], 25.0) if up else None
    start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0) if conn else None
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == CODE)
    ok = up is not None and conn is not None and start is not None and bool(relay)
    led.check("T2-PEER", ok, f"config: {pb.show(cfg, 1)}; peer: {up[1] if up else 'never listened'} / "
                             f"{conn[1] if conn else 'no guest'} / {start[1] if start else 'no replay start'}; engine: "
                             f"{pb.show(relay, 1)}; SessionGraceMs {GRACE_MS}; peer tail: {ctx.peer.tail(3)}")
    if not ok:
        led.unreached(rows, "the instrument never started (T2-PEER)")
        return
    ctx.anchor = start[0]
    if leg.startswith("p17"):
        _leg_p17(g, led, ctx, leg)
    else:
        _leg_t28(g, led, ctx, leg)


def _wait_config(g, ctx, first: float = 6.0, second: float = 10.0) -> list:
    """The engine's config line for the bench guest: a root booted with Netsync off reads its ini only at a field load
    (no client instance polls it), so a short wait, then ONE same-field warp, then wait."""
    def found():
        return pb.hits(ctx.eng.lines(), "config", pred=lambda m: m.group(1) == "True" and m.group(2) == "client"
                       and m.group(5) == f"ws://127.0.0.1:{PORT}" and m.group(6) == CODE)
    deadline = time.time() + first
    while time.time() < deadline:
        if found():
            return found()
        time.sleep(0.25)
    g.note("no config line within the poll window -- reloading the field (Ensure reads the ini at a field load)")
    try:
        g.warp(ctx.start)
    except HarnessError as err:
        g.note(f"the reload warp failed: {str(err)[:200]}")
    deadline = time.time() + second
    while time.time() < deadline:
        if found():
            return found()
        time.sleep(0.25)
    return []


def _mirrored_on_home(s) -> bool:
    return (s.field_id == HOME and s.ui_state == "FieldHUD" and pb.path(s, "netsync.session.mirroring") is True
            and byte_of(s, MARKER) == pb.MARKER_VALUE)


def _instrument(g, led, ctx, p: str, *, kick: bool) -> bool:
    st = cb.poll(g, _mirrored_on_home, PAIR_S, "the guest mirroring the host's story on 250")
    lines = ctx.eng.lines()
    paired = pb.hits(lines, "paired", after=ctx.anchor, pred=lambda m: int(m.group(1)) == HOME)
    armed = pb.hits(lines, "armed", after=ctx.anchor)
    ok = st is not None and bool(armed) and (bool(paired) or not kick)
    s = st or g.state
    led.check(f"{p}-I", ok, (f"paired {pb.show(paired, 1)}; " if kick else "") + f"ARMED {pb.show(armed, 1)}; field "
              f"{s.field_id} mirroring {pb.path(s, 'netsync.session.mirroring')!r} byte {MARKER} {byte_of(s, MARKER)!r}")
    return ok


def _leg_p17(g, led, ctx, leg: str) -> None:
    p = PFX[leg]
    rest = [c for c in leg_rows(leg) if c not in (f"{p}-free", f"{p}-poke")]
    if leg == "p17-ownwalk":
        live = cb.poll(g, lambda s: pb.path(s, "netsync.session.peer_alive") is True, LIVE_S, "the live host (peer-alive)")
        if live is None:
            led.unreached(rest, f"the session never went live within {LIVE_S:g} s")
            return
        frame0 = live.frame
        g.send(f"wait {max(1, OWNWALK_FRAMES)}")
        at = cb.mark(g)
        accepted, why = cb.try_send(g, f"warp {HOME} -1 -1")
        early = list(g.states_since(frame0) or [])
        samples, _hit = cb.watch(g, lambda s: s.field_id == HOME and s.on_field and s.control and not s.fading, 30.0)
        seen = {int(r.get("frame", -1)) for r in early}
        merged = early + [s.raw for s in samples if s.frame not in seen]
        cancelled = cb.count(cb.new(g, at), f"follow-warp to field {HOME} cancelled: this load already landed on it") > 0
        ok, detail = judge_ownwalk(merged, home=HOME, accepted=accepted, cancelled=cancelled)
        led.check(f"{p}-own", ok, detail + (f"; refusal {why}" if why else ""))
        if not ok:
            led.unreached(rest, f"the own walk was not reached ({p}-own)")
            return
    if not _instrument(g, led, ctx, p, kick=leg == "p17-kick"):
        led.unreached(rest, f"the instrument never showed the mirror ({p}-I)")
        return
    # the replay stops (--stop-at, --at-end hold), the grace runs out, the exit ramp reloads the Continue slot
    stop_hit = ctx.peer.wait_for(pb.PEER["stop_at"], P17_STOP_S + 30.0)
    t_stop = stop_hit[0] if stop_hit else _dt.datetime.now()
    deadline = time.time() + pb.STALE_S + GRACE_S + 25.0
    while time.time() < deadline and not pb.session_ends(ctx.eng.lines(), after=t_stop):
        time.sleep(0.25)
    ramps = pb.session_ends(ctx.eng.lines(), after=t_stop)
    back = cb.poll(g, lambda s: s.ui_state == "FieldHUD" and s.control and not s.fading and s.field_id > 0
                   and pb.path(s, "netsync.session.ramp_pending") is not True, 45.0, "the guest playable after the ramp")
    is_ramp = bool(ramps) and pb.MATCHERS["ramp"].search(ramps[0][1]) is not None
    led.check(f"{p}-ramp", is_ramp and back is not None,
              f"stop-at {stop_hit[1] if stop_hit else 'NEVER'}; ramp {pb.show(ramps, 1)}; playable "
              f"{'on ' + str(back.field_id) if back is not None else 'NEVER'}")
    if not (is_ramp and back is not None):
        led.unreached([f"{p}-a", f"{p}-b", f"{p}-c"], f"the session never ended through the own-autosave ramp ({p}-ramp)")
        return
    g.wait_frames(15)
    after = g.state
    for key, (ok, why) in judge_p17(after, own_byte=ctx.own_byte, start=ctx.start, p=p).items():
        led.check(f"{p}-{key}", ok, why)


def _leg_t28(g, led, ctx, leg: str) -> None:
    p = PFX[leg]
    rest = [c for c in leg_rows(leg) if c != f"{p}-I"]
    if not _instrument(g, led, ctx, p, kick=True):
        led.unreached(rest, f"the instrument never showed the mirror ({p}-I)")
        return
    led.check(f"{p}-new", ctx.newgame_field is not None and ctx.newgame_field > 0 and ctx.newgame_field != HOME,
              f"this root's New Game landed on {ctx.newgame_field} (the sandbox autosave's field is {HOME})")
    if not led.done.get(f"{p}-new"):
        led.unreached(rest, f"the New Game lands on {HOME}: 'no sample on {HOME}' could not tell the outcomes apart")
        return
    cb.poll(g, lambda s: s.ui_state == "FieldHUD" and s.control and not s.fading and not s.dialog_open, 20.0,
            "the guest playable on 250 (past the kick's fade-in)")
    time.sleep(1.5)
    try:
        g.soft_reset(timeout=TITLE_S, frames=8)
        reset_ok, why = True, ""
    except HarnessError as err:
        reset_ok, why = False, str(err)[:300]
    st = g.state
    led.check(f"{p}-pre", reset_ok and st.ui_state == "Title", f"ui_state {st.ui_state!r}" + (f"; {why}" if why else ""))
    if not (reset_ok and st.ui_state == "Title"):
        led.unreached([c for c in rest if c not in (f"{p}-new", f"{p}-pre")], f"the title was never reached ({p}-pre)")
        return
    # the session ends AT the title (the title first, then the end -- the design's ordering note 4)
    if leg == "t28-config":
        at = len(ctx.eng.lines())
        try:
            g.instance.netsync({"Enabled": "0"}, backup_to=_run_dir(g) / "ini")
        except Exception as err:                     # noqa: BLE001
            led.check(f"{p}-cfg", False, f"the Enabled=0 write failed: {err}")
            led.unreached([f"{p}-a", f"{p}-b"], "the session could not be ended at the title")
            return
        deadline = time.time() + 10.0
        hit = []
        while time.time() < deadline and not hit:
            hit = [m for _t, _l, m in ctx.eng.lines()[at:] if pb.MATCHERS["config_live"].search(m) and "(disabled)" in m]
            time.sleep(0.25)
        led.check(f"{p}-cfg", bool(hit), hit[0][:200] if hit else "no 'config change applied live (disabled)' in 10 s")
        if not hit:
            led.unreached([f"{p}-a", f"{p}-b"], f"the edit never applied ({p}-cfg)")
            return
    else:
        g.note(f"coop_peer replay-host stopped at the title: {ctx.peer.stop()}")
        ended = cb.poll(g, lambda s: pb.path(s, "netsync.session.state") == "ended", GRACE_S + pb.STALE_S + 8.0,
                        "session.state 'ended' at the title")
        s = ended or g.state
        led.check(f"{p}-end", ended is not None, f"session.state {pb.path(s, 'netsync.session.state')!r} ui {s.ui_state!r}")
        if ended is None:
            led.unreached([f"{p}-a", f"{p}-b"], f"the session never ended at the title ({p}-end)")
            return
    title = cb.hold_for(g, 1.5)
    # the title's New Game: every sample for NEW_GAME_S, and every exit-ramp line logged after it
    frame0, at_ng = g.state.frame, _dt.datetime.now()
    try:
        g.newgame(timeout=120.0)
    except HarnessError as err:
        g.note(f"the title's New Game: {str(err)[:200]}")
    early = list(g.states_since(frame0) or [])
    seen = {int(r.get("frame", -1)) for r in early}
    later = [s.raw for s in cb.hold_for(g, NEW_GAME_S) if s.frame not in seen]
    ramps = [m for _t, m, _x in pb.session_ends(ctx.eng.lines(), after=at_ng)]
    for key, (ok, why) in judge_t28(title, early + later, ramps, home=HOME).items():
        led.check(f"{p}-{key}", ok, why)
