"""R3 T2 -- THE HOST TAPE, the recording half of the solo two-role bench (studies/battle-coop/R3-SITTING-A-FIXES.md "T2"),
run unattended. [ff9mapkit netsync R3 T2]

THE GAP. No guest-side watcher, exit-ramp or mirror-gated behaviour can be benched in the selftest role: it returns
before the transport and DioramaTick exist, and IsMirroringStory needs a real socket. s119 (the diorama hold keyed on the
peer), s120 (the session grace) and s121 (the audible menu refusal) are all guest-side, so they are judged by REPLAYING a
recorded host into the desktop running as the guest (coop_cut_hold.py). This scenario makes that recording: the desktop as
the co-op HOST, tools/harness/coop_peer.py `serve-guest` standing in for the bridge on the game's RelayUrl port as its
fake guest, taping every frame the host sends.

THE BENCH.
  1. New Game, the party seeded through COOPPARTY (30604: +vivi +garnet +steiner -- a guest slot needs a member in slot
     1), field 250 (Evil Forest/Trail, sitting A's meeting field, warm), random encounters off (the free roam must stay
     free roam), and the STORY MARKER: gEventGlobal byte 1121 (bits 8968-8975, the campaign lane) poked to 0xA5 -- a
     value no New-Game save holds, so a guest reading it is reading the HOST's story (the roam leg's story-byte check).
  2. Memoria.ini [Netsync] (BACKED UP FIRST -- the MAIN repo's backups/ and the run dir; restored byte-exact in the
     `finally`): Enabled 1, Role host, RelayUrl ws://127.0.0.1:<COOP_PEER_PORT, 49201>, SessionCode ff9-T2BENCH1,
     GuestSlots 2, FollowHost 0, TargetField 0, StartHoldMs 8000. The engine hot-reloads it (mtime-gated, polled every
     2 s; a field load when no NetSyncClient exists yet), so the RUNNING game turns host; its config line is the proof.
  3. `py tools/harness/coop_peer.py serve-guest --port <port> --report live --tap <tape>` as a subprocess (stopped with
     CTRL_BREAK -> its own KeyboardInterrupt path, so the tape closes whole). Its fake guest answers at 30 Hz on the
     host's field and reports its diorama LIVE on every battle nonce: the s114 start hold releases at once, and slot 1
     stays GUEST-OWNED (the host's HUD skips it, G2) -- so on the replay the guest's ready mirror has a slot to serve, as
     in sitting A (the laptop's slot-1 window was up at the cut).
  4. COOP_TAPE_PRE_S (70) s of free roam -- the replay's pairing, mirror arm, S121 presses and the two roam cuts (20 s and
     40 s) all live here -- then `battle 67 -1 rand` from the field, fought COOP_TAPE_FIGHT_S (40) s with Defend (slots 0,
     2, 3; slot 1 is the guest's), then Attack to the win; the result screen confirmed through (its Hide is the end-leave's
     trigger); COOP_TAPE_POST_S (30) s back on 250 (the "still mirrored after the victory" window); the peer stopped.

WHY THIS BATTLE PATH (the publication gate). NetSyncBattle.Pump publishes the type-1 lane only for an OWN battle:
InOwnBattle needs EventEngine.gMode 2 or 4, which only EventEngine.StartEvents writes -- and HonoluluBattleMain skips
StartEvents under isDebug. So NetSyncDiorama.Boot / `netsync dioboot` (isDebug set) and any ~ menu debug fight never
reach NoteOwnBattleStart (no "battle intro:" line, no nonce, nothing on the wire). The harness `battle <scene> <group>
[rand]` verb (Ff9mkDebugMenu.HarnessBattle -> StartBattle) is NOT a debug fight: it performs exactly ENCOUNT2's writes
(btlSubMapNo, SetNextMap, isRandomEncounter, `isDebug = false`, nextMode 2, BackupPosObjData, attr |= 8) -- the field's
own encounter transition through the swirl, StartEvents, gMode 2 -- which is the publishing path every selftest own
battle in coop_battle_*.py already rides (there SelfTestPump is the publisher; here the real Pump is). `rand` (s111+)
makes it a random encounter, as sitting A's were; REC-B proves the publication rather than assuming it: the host's
NoteOwnBattleStart line ("battle intro: ...") AND the peer's decoded "host battle lane UP: nonce N map 67". Walking 250
until a random encounter would also publish, but at an unbounded time -- the tape's phases must land where the legs'
cuts are planned.

WHERE THE TAPE GOES. <the MAIN repo>/.harness-runs/coop-tapes/<stamp>-host<field>-s<stage>.f9tape (COOP_TAPE_DIR
overrides), plus latest.json there (written only when all five facts are on the tape: coop_cut_hold.py's default). Not
studies/test-harness/tapes/: the type-5 story snapshot (~2 KB) rides EVERY 33 ms write tick, so a ~3 min tape is 10-20
MB of binary; a tape replays exactly one engine build's wire; it is a run artifact, not source. .harness-runs/ is
gitignored, and the MAIN repo's copy outlives the worktree that recorded it (the worktree-parked-backups lesson).

THE FIVE CALIBRATION FACTS (REC-F1..F5, printed as notes): read back off the closed tape with coop_peer's codec -- the
five things a replay must find before coop_cut_hold's CAL leg can see its five lines:
  F1 PAIR    the host on field 250 >= 10 s before its battle          -> 'paired on the host's field (250)'
  F2 MIRROR  type-5 story frames from the first second, the marker    -> 'state-mirror ARMED'
  F3 BOOT    a type-1 run on one nonce, scene 67, command-gated caps  -> 'diorama BOOT scene=67'
  F4 LIVE    >= 20 s of live fight, the seq advancing, a player Ready -> 'diorama LIVE'
  F5 END     the end block terminal, the result screen at Hide, the host back on 250 -> the end-leave
Each leg's cut on THIS tape (or why the tape cannot carry it) is printed after them.

CHECKS (REC-*): P0 the port free and the peer listening; P1 the host config applied live (the engine's own config line
naming role=host and the bench code); P2 the host dialled the peer (both sides' lines); M the marker reads 0xA5 on the
host before the tape starts; B a REAL own battle PUBLISHED (above); W the fight ran >= FIGHT_S s, was won, and the host is
back on 250 with control; T the tape closed cleanly and reads back with no torn tail; F1-F5 the five facts; INI (final)
Memoria.ini restored byte-exact.

CALIBRATION. The recording is the INSTRUMENT, not a bench of s118-s121: the host side of the wire is v14 on every DLL from
s110 on, and the fake guest's LIVE report keeps every s114/s118 host rule out of the way. Expected red set on the deployed
s117 DLL: NONE. Each check fails when its fact is missing (REC-B on a debug-fight path, F4 on a short fight, F2 when the
mirror lane is off, P2 when a production bridge holds the port -- P0 then refuses before any edit). A tape recorded on
s117 replays into s117 and s121 guests alike (the wire is unchanged), which is what lets one tape calibrate red on s117
and judge green on s118-s121.

THE HAND RECORDING (a world-map victory for coop_cut_hold's s120-world leg, which a field-250 tape cannot carry): with the
desktop's [Netsync] set to the host values above by hand, run
    py tools/harness/coop_peer.py serve-guest --report live --tap <tape>.f9tape
play to a WORLD-MAP fight, win it, stay on the world map >= 20 s, Ctrl+C; then, in ONE launch (a world tape has no field
for its CAL leg to pair on, so the leg runs forced -- coop_cut_hold.py's RUN notes):
    COOP_CUT_FORCE=1 COOP_TAPE=<tape> COOP_CUT_LEG=s120-world py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py

RUN (the game must be closed; play.py launches it; the production bridge must NOT be running on 49201):
    py tools/play.py studies/test-harness/scenarios/coop_tape_record.py
    COOP_TAPE_FIGHT_S=45 py tools/play.py studies/test-harness/scenarios/coop_tape_record.py      (a longer fight)
  PowerShell (a `$env:` value persists in that shell -- clear it, or every later launch inherits it):
    $env:COOP_TAPE_FIGHT_S='45'; py tools/play.py studies/test-harness/scenarios/coop_tape_record.py
    Remove-Item Env:COOP_TAPE_FIGHT_S -ErrorAction SilentlyContinue
then the guest legs, in order (coop_cut_hold.py): COOP_CUT_LEG=cal first -- nothing else judges until it passes.
AFTER AN ABORTED RUN (anything that skips the `finally`): the install's Memoria.ini may still say Role host /
SessionCode ff9-T2BENCH1. Compare it with the newest <main repo>/backups/Memoria.ini.pre-coop-tape-record.<stamp> and copy
that back if they differ (the run dir keeps a second copy). [ff9mapkit netsync R3 resume]
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - the T2 two-role bench helpers

HarnessError = cb.HarnessError

FIELD = pb.BENCH_FIELD
SCENE = pb.BENCH_SCENE
PORT = pb.env_int("COOP_PEER_PORT", pb.DEFAULT_PORT)
CODE = pb.BENCH_CODE
PRE_S = pb.env_float("COOP_TAPE_PRE_S", 70.0)
FIGHT_S = pb.env_float("COOP_TAPE_FIGHT_S", 40.0)
POST_S = pb.env_float("COOP_TAPE_POST_S", 30.0)
GUEST_SLOTS = pb.env_int("COOP_TAPE_GUEST_SLOTS", 2)

CATALOG = {
    "REC-P0": f"the bench port {PORT} is free and `coop_peer serve-guest` listens on it (no production bridge there)",
    "REC-P1": f"the HOST config applied live: the engine's own line 'config enabled=True role=host ... relay=ws://127.0.0.1:"
              f"{PORT} code={CODE}'",
    "REC-P2": f"the HOST game dialled the peer: coop-peer 'HOST game connected (session {CODE})' and the engine's 'relay "
              f"connected ...?role=host'",
    "REC-M": f"the story marker: gEventGlobal byte {pb.MARKER_BYTE} reads 0x{pb.MARKER_VALUE:02X} on the host (its watched "
             "bits) before the tape starts",
    "REC-B": f"a REAL own battle on field {FIELD} (`battle {SCENE} -1 rand`: ENCOUNT2's writes, isDebug cleared) is "
             "PUBLISHED: the host's 'battle intro:' line (NoteOwnBattleStart) and the peer's 'host battle lane UP: nonce N "
             f"map {SCENE}'",
    "REC-W": f"the fight ran >= COOP_TAPE_FIGHT_S ({FIGHT_S:g}) s, was WON, and the host is back on field {FIELD} with "
             "control (the warm return)",
    "REC-T": "the tape closed cleanly (the peer's own KeyboardInterrupt path wrote its 'tape ...: N record(s)' line) and "
             "reads back with no torn tail",
    "REC-F1": "F1 PAIR: the host on field 250 >= 10 s before its battle (the replay's 'paired on the host's field')",
    "REC-F2": "F2 MIRROR: type-5 story frames from the first second, carrying the marker (the replay's 'state-mirror ARMED')",
    "REC-F3": "F3 BOOT: a type-1 run on one nonce, scene 67, command-phase-gated caps (the replay's 'diorama BOOT')",
    "REC-F4": "F4 LIVE: >= 20 s of live fight, the seq advancing, a player Ready (the replay's 'diorama LIVE')",
    "REC-F5": "F5 END: the end block terminal, the result screen at Hide, the host back on 250 (the replay's end-leave)",
    "REC-INI": "Memoria.ini restored byte-exact (sha256) after the run -- the install is shared",
}

HOST_VALUES = {"Enabled": "1", "Role": "host", "RelayUrl": f"ws://127.0.0.1:{PORT}", "SessionCode": CODE,
               "GuestSlots": str(GUEST_SLOTS), "FollowHost": "0", "TargetField": "0", "StartHoldMs": "8000"}


class _Ctx:
    def __init__(self, field: int):
        self.field = field
        self.guard = None
        self.peer = None
        self.tape = None
        self.eng = None
        self.stage = 0
        self.host_s118 = False


def _run_dir(g) -> Path:
    return Path(getattr(g, "scenario_dir", None) or g.run_dir)


def _config_applied(lines, role: str) -> list:
    return pb.hits(lines, "config", pred=lambda m: m.group(1) == "True" and m.group(2) == role
                   and m.group(5) == f"ws://127.0.0.1:{PORT}" and m.group(6) == CODE)


def run(g, field: int = FIELD):
    led = cb.Ledger(g, CATALOG, finals=("REC-INI",))
    ctx = _Ctx(field)
    try:
        _run(g, led, ctx)
    except HarnessError as err:
        g.note(f"the recording raised: {str(err)[:400]}")
        led.close(f"the recording raised before this check: {str(err)[:200]}")
    finally:
        _teardown(g, led, ctx)
        led.close(final=True)


def _teardown(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """The peer FIRST (the tape closes; and a restored owner config that dials the same port must find nobody), then the
    ini, then the logs."""
    if ctx.peer is not None and ctx.peer.how_ended is None:
        g.note(f"coop_peer serve-guest: {ctx.peer.stop()}")
    if ctx.guard is not None:
        ok, why = ctx.guard.restore()
        led.check("REC-INI", ok, why)
    else:
        led.check("REC-INI", True, "Memoria.ini was never edited (the run stopped before the edit)")
    g.note(f"Memoria.log archived: {cb.archive_log(g, 'coop-tape-record')}")


def _run(g, led: cb.Ledger, ctx: _Ctx) -> None:
    cb.provenance(g)
    g.note(f"R3 T2 tape record: host on field {ctx.field}, peer port {PORT}, pre {PRE_S:g} s / fight {FIGHT_S:g} s / "
           f"post {POST_S:g} s, GuestSlots {GUEST_SLOTS}")
    free, why = pb.port_free(PORT)
    if not free:
        led.check("REC-P0", False, why)
        led.close(f"the bench port is taken -- nothing was edited ({why[:160]})")
        return
    # 1. the host's game
    g.newgame()
    g.note(cb.seed_party(g, back_to=ctx.field))
    if g.state.field_id != ctx.field:
        g.warp(ctx.field)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]}) -- a random battle may interrupt the free roam")
    g.poke(pb.MARKER_BYTE, pb.MARKER_VALUE)
    g.watch(*(pb.MARKER_BYTE * 8 + b for b in range(8)))
    st = cb.poll(g, lambda s: pb.marker_value(s) == pb.MARKER_VALUE, 5.0, "the story marker on the watched bits")
    st = st or g.state
    led.check("REC-M", pb.marker_value(st) == pb.MARKER_VALUE,
              f"byte {pb.MARKER_BYTE} reads {pb.marker_value(st)!r} on field {st.field_id}")
    ctx.stage = pb.engine_stage(st)
    ctx.host_s118 = pb.has(st, "netsync.battle.host.handback.refused_report")
    g.note(f"the engine reads as s{ctx.stage or '<117'} (guest ladder){'; s118 host keys present' if ctx.host_s118 else ''}"
           f"; {cb.stage_note(st)}")
    # 2. the ini, then wait for the engine's own config line
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", HOST_VALUES, label="coop-tape-record",
                            run_dir=_run_dir(g))
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("REC-P1", False, f"the edit failed: {err}")
        led.close(f"Memoria.ini could not be edited ({str(err)[:160]})")
        return
    applied = _wait_config(g, ctx, "host")
    led.check("REC-P1", bool(applied), pb.show(applied) if applied else
              f"no matching config line in Memoria.log after the edit (and a field reload); config lines seen: "
              f"{pb.show(pb.hits(ctx.eng.lines(), 'config'))}")
    if not applied:
        led.close("the engine never took the host config -- is this the Memoria.ini the game reads (cwd = the game root)?")
        return
    # 3. the peer
    stamp = time.strftime("%Y%m%d-%H%M%S")
    tdir = pb.tape_dir()
    tdir.mkdir(parents=True, exist_ok=True)
    ctx.tape = tdir / f"{stamp}-host{ctx.field}-s{ctx.stage or 0}.f9tape"
    rd = _run_dir(g)
    ctx.peer = pb.PeerProc("serve-guest", ["--port", PORT, "--report", "live", "--tap", ctx.tape, "--status", "5"],
                           log_path=rd / "coop_peer-serve-guest.log", out_path=rd / "coop_peer-serve-guest.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0)
    err = ctx.peer.first(pb.PEER["error"])
    led.check("REC-P0", up is not None and err is None,
              (up[1] if up else f"no listening line; tail: {ctx.peer.tail()}") + (f"; {err[1]}" if err else ""))
    if up is None:
        led.close("coop_peer serve-guest never listened")
        return
    conn = ctx.peer.wait_for(pb.PEER["host_connected"], 20.0)
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "host" and m.group(2) == CODE)
    led.check("REC-P2", conn is not None and conn[2].group(1) == CODE and bool(relay),
              f"peer: {conn[1] if conn else 'no HOST connection'}; engine: {pb.show(relay)}")
    if conn is None:
        led.close("the host game never dialled the peer")
        return
    # 4. the free roam, the battle, the post-battle roam
    _hold_until(ctx, conn[0], PRE_S)
    _note_host_ghost(g)                     # [ff9mapkit netsync s139] the transport site's tuple: a NOTE, no check
    _battle(g, led, ctx)
    g.note(f"post-battle free roam: {POST_S:g} s on field {g.state.field_id}")
    time.sleep(POST_S)
    g.note(f"coop_peer serve-guest: {ctx.peer.stop()}")
    _facts(g, led, ctx)


def _note_host_ghost(g) -> None:
    """[ff9mapkit netsync s139] A NOTE (never a check: the recorder's calibration is unchanged) of the HOST's own ghost of the
    fake guest while it roams -- the transport site (HostDress behind GhostGuard on the fake guest's wire body, which
    mirrors the host's model: 98) -- for a reader to judge against battlewire's host rule and the install oracle
    (coop_dress_wire.py's G9d-f are that judge on a real guest, at three GuestSlots). An engine before s138 publishes no
    `netsync.dress`."""
    gh = cb.path(g.state, "netsync.dress.ghost")
    if not isinstance(gh, dict):
        g.note("s139 transport site: the host publishes no `netsync.dress.ghost` (an engine before s138)")
        return
    g.note("s139 transport site -- the host's ghost of the fake guest: "
           + ", ".join(f"{k}={gh.get(k)!r}" for k in ("model", "rig", "geo", "body", "clip", "playing", "mode")
                       if k in gh))


def _note_section8(g, ctx: _Ctx, cp) -> None:
    """[ff9mapkit netsync s139] NOTES (never a check) of the tape's section 8 -- coop_peer's `dress` report with each host
    frame's own party (its section 1) and the host's [Netsync] GhostAs read READ-ONLY: what `py tools/harness/coop_peer.py
    dress <tape> --ghost-as <it> --guest-slots 2` prints. An s138-or-older host's tape reads "none"."""
    ghost_as = (cb.ini_value(g, "Netsync", "GhostAs") or "").strip()
    try:
        ok, lines = cp.tape_dress_lines(ctx.tape, cp.frame_expect(ghost_as, GUEST_SLOTS))
    except Exception as err:                 # noqa: BLE001 -- a note only
        g.note(f"section 8: the tape's dress read raised {type(err).__name__}: {err}")
        return
    g.note(f"SECTION 8 on {ctx.tape.name} (GhostAs {ghost_as!r}, GuestSlots {GUEST_SLOTS}): {'held' if ok else 'NOT held'}")
    for line in lines[1:]:
        g.note("  " + line)


def _wait_config(g, ctx: _Ctx, role: str, first: float = 6.0, second: float = 10.0) -> list:
    """The engine's config line for ``role`` + the bench relay/code. A running NetSyncClient polls Memoria.ini every 2 s;
    with none yet (the owner's Enabled=0), only a field load's Ensure() reads it -- so one same-field warp, then wait."""
    deadline = time.time() + first
    while time.time() < deadline:
        found = _config_applied(ctx.eng.lines(), role)
        if found:
            return found
        time.sleep(0.25)
    g.note("no config line within the poll window -- reloading the field (Ensure reads the ini at a field load)")
    try:
        g.warp(ctx.field)
    except HarnessError as err:
        g.note(f"the reload warp failed: {str(err)[:200]}")
    deadline = time.time() + second
    while time.time() < deadline:
        found = _config_applied(ctx.eng.lines(), role)
        if found:
            return found
        time.sleep(0.25)
    return []


def _hold_until(ctx: _Ctx, base, seconds: float) -> None:
    """Idle until ``seconds`` after ``base`` (the peer's HOST-connected stamp), reading the peer's log as it grows."""
    end = base + _dt.timedelta(seconds=seconds)
    while _dt.datetime.now() < end and ctx.peer.alive():
        ctx.peer.lines()
        time.sleep(0.5)


def _battle(g, led: cb.Ledger, ctx: _Ctx) -> None:
    st = g.state
    rand = bool(getattr(st, "coop_intro_mirror", False))
    if not rand:
        g.note("the engine publishes no `netsync.diorama.intro` (pre-s111): the battle boots NON-random")
    at = _dt.datetime.now()
    try:
        g.start_battle(SCENE, group=-1, rand=rand)
    except HarnessError as err:
        led.check("REC-B", False, f"`battle {SCENE} -1{' rand' if rand else ''}` failed: {str(err)[:300]}")
        led.unreached(("REC-W",), "no battle")
        return
    lane = ctx.peer.wait_for(pb.PEER["host_lane_up"], 15.0, after=at)
    intro = pb.hits(ctx.eng.lines(), "intro", after=at)
    ok = lane is not None and int(lane[2].group(2)) == SCENE and bool(intro)
    led.check("REC-B", ok, f"peer: {lane[1] if lane else 'no host battle lane'}; host: {pb.show(intro)}")
    st = g.state
    g.note(f"battle up: party slots {cb.player_slots(st)}, enemies "
           f"{[u.get('name') for u in cb.units(st, player=False)]}; slot 1 is the fake guest's (GuestSlots {GUEST_SLOTS}, "
           "reported LIVE): the host's HUD skips it")
    t0 = time.time()

    def policy(s, slot):
        # Defend until FIGHT_S has run (the tape needs a LONG live fight: the s119 / s120 cuts land inside it), healing a
        # member under 45% with a Potion (a New-Game party at level 1 must outlast ~45 s of Goblin hits), then Attack
        if time.time() - t0 >= FIGHT_S:
            return {"command": "Attack"}
        try:
            menu = g.menus(slot)
        except HarnessError:
            return None
        names = {c.get("name") for c in (menu.get("commands") or []) if c.get("offered", True)}
        items = {i.get("name") for i in (menu.get("items") or [])}
        hurt = [u for u in cb.units(s, player=True) if u.get("alive") and int(u.get("hp_max") or 0) > 0
                and int(u.get("hp") or 0) * 100 < int(u.get("hp_max")) * 45]
        if hurt and "Potion" in items:
            return {"command": "Potion"}
        return {"command": "Defend"} if "Defend" in names else None

    try:
        result = g.fight(policy=policy, timeout=FIGHT_S + 180.0, max_turns=240)
    except HarnessError as err:
        led.check("REC-W", False, f"the fight raised: {str(err)[:300]}")
        return
    lf = getattr(g, "last_fight", {}) or {}
    back, why = cb.arrive(g, ctx.field, timeout=90.0)
    won = result in (1, 2)
    long_enough = float(lf.get("seconds", 0.0)) >= FIGHT_S - 1.0
    led.check("REC-W", won and long_enough and back,
              f"result {result} ({lf.get('name')}), {lf.get('seconds')} s, {lf.get('turns')} turn(s); "
              f"{'back on ' + str(ctx.field) if back else why}")


def _facts(g, led: cb.Ledger, ctx: _Ctx) -> None:
    summary = ctx.peer.first(pb.PEER["tape_summary"])
    try:
        cp = pb.coop_peer_module()
        header, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                 # noqa: BLE001 -- the reason goes into the checks
        led.check("REC-T", False, f"the tape does not read back: {err}")
        led.unreached(("REC-F1", "REC-F2", "REC-F3", "REC-F4", "REC-F5"), "the tape does not read back")
        return
    size = ctx.tape.stat().st_size
    led.check("REC-T", summary is not None and not torn and "stopped cleanly" in (ctx.peer.how_ended or ""),
              f"{summary[1] if summary else 'no tape line (the peer did not close it itself)'}; {ctx.peer.how_ended}; "
              f"{len(records)} record(s), {size / 1e6:.1f} MB, torn tail {torn} B")
    facts = pb.tape_facts(records, cp, field=ctx.field)
    g.note(f"THE FIVE CALIBRATION FACTS of {ctx.tape.name}:")
    for line in pb.facts_lines(facts):
        g.note("  " + line)
    for k in ("f1", "f2", "f3", "f4", "f5"):
        led.check(f"REC-{k.upper()}", facts[k]["ok"], facts[k]["why"])
    _note_section8(g, ctx, cp)              # [ff9mapkit netsync s139] the tape's section 8: NOTES, no check
    plans = {leg: pb.plan_leg(leg, facts) for leg in pb.LEGS}
    plans["s120-world"] = pb.plan_leg("span", facts, world=True)
    for leg, p in plans.items():
        how = (f"cut at tape {p['bh'][0]:.2f} s for {p['bh'][1]:g} s" if p.get("bh") else
               f"no cut, the replay stops at tape {p['stop_at']:.2f} s" if p.get("stop_at") else "no cut (the whole tape)")
        g.note(f"  leg {leg}: " + (how if p["ok"] else "CANNOT -- " + p["why"]))
    try:
        (_run_dir(g) / "tape-info.txt").write_text("\n".join(cp.tape_info(ctx.tape)) + "\n", encoding="utf-8")
    except Exception as err:                 # noqa: BLE001 -- a convenience copy only
        g.note(f"tape-info.txt not written: {err}")
    all_ok = all(facts[k]["ok"] for k in ("f1", "f2", "f3", "f4", "f5"))
    if all_ok:
        ptr = ctx.tape.parent / "latest.json"
        ptr.write_text(json.dumps({"tape": str(ctx.tape), "stage": ctx.stage, "host_s118": ctx.host_s118,
                                   "recorded": header.get("started"), "field": ctx.field, "scene": SCENE,
                                   "facts": {k: facts[k]["why"] for k in ("f1", "f2", "f3", "f4", "f5")}},
                                  indent=1), encoding="utf-8")
        g.note(f"tape: {ctx.tape} ({size / 1e6:.1f} MB) -- latest.json points at it (coop_cut_hold.py's default)")
    else:
        g.note(f"tape: {ctx.tape} -- a fact is MISSING, so latest.json was NOT moved to it")
