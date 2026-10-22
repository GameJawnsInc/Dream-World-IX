"""[ff9mapkit netsync s145] BATTLES FROM THE WORLD MAP's REPO HARNESS CORE -- what the repo builds on the s145 patch: the stand-in's
world diorama (fakegame's `worlddio` rung) and its fault levers, the driver (`bench worldwarm`, Session.vehicle, the world `dioboot`
guard), the accessors and keys, the T2 tape's facts and plan (coop_peer's battle segments, _coop_peer_bench's world-battle leg),
the recorder's world-battle variant, and the s144 benches re-keyed by stage.

tests/test_world_diorama.py pins the ENGINE's pure steps (every WdioRow / WWatchRow / FreezeRow evaluated against battlewire's
twins). This file pins the rest:

  * THE STAND-IN BENCH: two legs driven through the real Session against the stand-in -- SOLO (the selftest role: a FIELD boot,
    the control; the world boot from WorldHUD, its warm return judged on witnesses the engine does not compute -- world x / z,
    the camera, the MAP-var digest, battle_prob, ui_state, the freeze -- beside its claim; `reset` with a world diorama up; the
    decline aboard a vehicle and under the lever, judged on the world tick that never restarted; the cold reference last) and
    the FOLLOWED CLIENT (the watcher boots on the host's battle lane, leaves on the host back on the world map, follows no
    field inside the diorama, declines for a visit aboard a vehicle, and a ~ release survives the round trip).
  * EVERY ROW CAN FAIL: each fault lever (FG.WORLD_DIO_FAULTS) turns EXACTLY its DIO_FAULT_REDS rows red; the faults together
    cover every row but the control; the s144 stand-in (caps_through("worldwait")) reads exactly OLD_PREDICTED red -- the driver
    refusing `bench worldwarm`, `vehicle` and the world `dioboot` before the step --, and the solo leg under the calibration lever
    (`bench worldwarm off`, pulled first) exactly LEVER_PREDICTED: every boot row declined, never a cold return.
"""
import importlib.util
import json
import os
import pathlib
import re
import struct
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import HarnessError, Session                              # noqa: E402
from harness import battlewire as BW                                   # noqa: E402
from harness import channel as CH                                      # noqa: E402
from harness import coop_peer as CP                                    # noqa: E402
from harness import fakegame as FG                                     # noqa: E402
from harness.fakegame import FakeGame                                  # noqa: E402

SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
FIELDS = (250, 300, 6603)
LANDING = (68.0, -444.0)                     # 6603's door sets the party down here on 9011 (the world's Main_Init spawn too)
SPOT = (128.0, -444.0)                       # where the solo leg's walk off the landing stops (the stand-in's 30-frame `hold up`)


# ------------------------------------------------------------------------------------------------ the stand-in, in-process
def _game(root, fields=FIELDS):
    (root / "x64").mkdir(parents=True)
    (root / "x64" / "FF9.exe").write_bytes(b"MZ")
    (root / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    mod = root / "FF9CustomMap"
    mod.mkdir()
    (mod / "DictionaryPatch.txt").write_text("".join(f"FieldScene {f} 11 T{f} T{f} {f}\n" for f in fields),
                                             encoding="utf-8")
    return root


def _fake(root, faults=(), caps=None) -> FakeGame:
    fake = FakeGame(root, fps=600)
    if caps is not None:
        fake.netsync_caps = caps
    fake.world_dio_faults = set(faults)
    fake.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    fake.world_swirl_frames = 40
    fake.world_exit_frames = 40
    fake.reinit_fields, fake.encounter_fields = {250}, {250}
    return fake


def _session(root, fake) -> Session:
    return Session(game_path=root, run_dir=root / "run", save_dir=root / "player-saves", pid_probe=lambda: [],
                   launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=False)


def _log(fake) -> str:
    return pathlib.Path(fake.memoria_log).read_text(encoding="utf-8", errors="replace")


class _Rows:
    """The stand-in bench's ledger: a row is (ok, detail); a step that cannot run reds its row 'not reached'."""

    def __init__(self):
        self.rows = {}

    def row(self, name, fn):
        try:
            ok, detail = fn()
        except Exception as err:                       # noqa: BLE001 -- any step that cannot run reds ITS row, never the bench
            ok, detail = False, f"not reached: {str(err)[:300]}"
        self.rows[name] = (bool(ok), detail)


def _dio(st, key=None, default=None):
    node = ((st.netsync or {}).get("world") or {}).get("dio")
    if key is None:
        return node
    return node.get(key, default) if isinstance(node, dict) else default


def _d(st, key):
    return ((st.netsync or {}).get("diorama") or {}).get(key)


def _to_world(g, fake, wld=9011, x=LANDING[0], z=LANDING[1], *, from_field=False):
    f0 = fake.frame
    fake.enter_world(wld, x, z, from_field=from_field)
    return g.wait_for(lambda s: s.on_world and s.world_id == wld and s.frame > f0 + 2, timeout=6.0, what="the world map")


def _hold_up(g, frames=20):
    st = g.state
    x0, z0 = st.world_x, st.world_z
    g.send(f"hold up {frames}")
    g.wait_frames(frames + 6)
    st = g.state
    return st, abs(st.world_x - x0) + abs(st.world_z - z0)


def _boot(g, *args):
    g.netsync("dioboot", 359, 0, "wire", *args)
    return g.wait_for(lambda s: s.ui_state == "BattleHUD" and _d(s, "booted"), timeout=6.0, what="the diorama")


def _leave(g, done):
    """`netsync dioleave` (request-only: the boot's swirl defers it -- retried, as _coop_battle.leave does) and the return."""
    for attempt in range(8):
        try:
            g.netsync("dioleave")
            break
        except HarnessError as err:
            if "deferred" not in str(err) or attempt == 7:
                raise
            g.wait_frames(30)
    return g.wait_for(done, timeout=8.0, what="the return")


def _away(st, xz) -> float:
    return abs((st.world_x or 0.0) - xz[0]) + abs((st.world_z or 0.0) - xz[1])


def _refused(g, fn) -> str | None:
    """The step's refusal (HarnessError's text), None when it went through."""
    try:
        fn()
    except HarnessError as err:
        return str(err)
    return None


def _solo(g, fake) -> dict:
    """THE SOLO LEG (the selftest role): the field control on 250, then 6603's WorldMap() exit onto 9011, the walk off the
    landing and a camera turn with the walker free (`bench 0`), then `bench 1` (frozen) and snapshot A."""
    led = _Rows()
    g.newgame(settle=0)
    g.warp(250)
    g.netsync("selftest", 1)

    def field():
        """THE CONTROL (F3.3, byte-identical in behaviour): a FIELD boot and its warm return -- on every rung; the world block's
        counters never move for it."""
        r0 = _d(g.state, "returns") or 0
        st = _boot(g)
        booted = _d(st, "boot") == "warm" and _d(st, "boot_field") == 250
        st = _leave(g, lambda s: s.ui_state == "FieldHUD" and (_d(s, "returns") or 0) == r0 + 1)
        world_ok = _dio(st) is None or (_dio(st, "boot_world") == -1 and _dio(st, "returns") == 0)
        ok = booted and st.field_id == 250 and _d(st, "last_return") == "warm" and _d(st, "last_return_field") == 250 and world_ok
        return ok, f"boot {booted}, field {st.field_id}, last_return {_d(st, 'last_return')!r}, dio {_dio(st)}"
    led.row("WD-FIELD", field)

    g.warp(6603)
    g.wait_frames(10)
    _to_world(g, fake, from_field=True)
    g.send("hold up 30")                                   # the walk off the landing (the area script's first-move writes)
    g.wait_frames(36)
    g.send("hold leftbumper 20")                           # the camera turned (a world load with prevMode 1 would zero it)
    g.wait_frames(26)
    g.netsync("bench", 1)
    g.wait_frames(12)
    a = g.state

    def keys():
        nothing = _dio(a)
        world = list(a.raw.get("world") or {})
        proof = _log(fake)
        lines = [BW.proof_ok(BW.PROOF_WORLD_FREEZE, BW.world_freeze_selftest_rows(145)),
                 BW.proof_ok(BW.PROOF_WORLD_DIORAMA, BW.WORLD_DIORAMA_SELFTEST_ROWS),
                 BW.proof_ok(BW.PROOF_WORLD_WATCHER, BW.WORLD_WATCHER_SELFTEST_ROWS)]
        ok = (isinstance(nothing, dict) and list(nothing) == list(BW.WORLD_DIO_SENTINELS) and a.coop_world_dio is True
              and world[-6:] == list(BW.WORLD_WITNESS_SENTINELS) and isinstance(a.prev_mode, int)
              and isinstance(a.world_mapvar, str) and len(a.world_mapvar) == 160 and all(ln in proof for ln in lines)
              and "selftest: FAIL" not in proof)
        return ok, f"dio {nothing}, world keys {world}, prev_mode {a.prev_mode!r}"
    led.row("WD-KEYS", keys)

    def boot():
        st = _boot(g)
        boot.st = st
        ok = (_dio(st, "boot_world") == 9011 and _dio(st, "boot") == "warm" and _dio(st, "booted_world") is True
              and st.prev_mode == 3 and st.gmode == 3 and _d(st, "boot_field") == -1 and _d(st, "boot") == "warm")
        return ok, (f"dio {_dio(st)}, prev_mode {st.prev_mode}, gmode {st.gmode}, diorama boot {_d(st, 'boot')!r} "
                    f"field {_d(st, 'boot_field')}")
    led.row("WD-BOOT", boot)

    def audio():
        ok = getattr(boot, "st", None) is not None and BW.LOG_PRESWIRL_AUDIO_FAILED not in _log(fake)
        return ok, "no pre-swirl audio failure" if ok else "booted? / the pre-swirl audio replicate failed"
    led.row("WD-AUDIO", audio)

    def ret():
        r0 = _dio(a, "returns", 0)
        st = _leave(g, lambda s: s.ui_state in ("WorldHUD", "FieldHUD") and not _d(s, "booted"))
        g.wait_frames(10)
        st = g.state
        ret.st = st
        ok = (st.ui_state == "WorldHUD" and st.world_id == 9011 and _dio(st, "returns") == r0 + 1
              and _dio(st, "last_return") == "warm" and _dio(st, "last_world") == 9011 and _d(st, "last_return") == "warm"
              and _d(st, "last_return_field") == -1 and (st.world_ticks or 0) < (a.world_ticks or 0)
              and BW.log_world_leave(9011) in _log(fake))
        return ok, (f"ui {st.ui_state} world {st.world_id}; dio returns {r0}->{_dio(st, 'returns')}, last "
                    f"{_dio(st, 'last_return')!r} on {_dio(st, 'last_world')}; ticks {a.world_ticks}->{st.world_ticks}")
    led.row("WD-RETURN", ret)

    def back():
        """The state the return landed in -- only when the world map really RELOADED under it (the world tick restarted: a
        witness the engine does not compute), never a stale earlier state: a refused boot leaves every witness as it was, which
        would read 'warm' for nothing."""
        st = getattr(ret, "st", None)
        if st is None or st.world_ticks is None or a.world_ticks is None or not 0 <= st.world_ticks < a.world_ticks:
            raise RuntimeError("no world return happened (the world never reloaded)")
        return st

    def place():
        st = back()
        ok = st.ui_state == "WorldHUD" and _away(st, (a.world_x, a.world_z)) < 4.0 and _away(st, LANDING) > 4.0
        return ok, f"({st.world_x}, {st.world_z}) vs A ({a.world_x}, {a.world_z}), the landing {LANDING}"
    led.row("WD-PLACE", place)

    def camera():
        st = back()
        ok = st.world_cam_rot is not None and st.world_cam_rot == a.world_cam_rot and st.world_cam_upper == a.world_cam_upper \
            and a.world_cam_rot != 0.0
        return ok, f"cam_rot {a.world_cam_rot}->{st.world_cam_rot}, cam_upper {a.world_cam_upper}->{st.world_cam_upper}"
    led.row("WD-CAMERA", camera)

    def mapvar():
        st = back()
        # [ff9mapkit netsync s145 fix1] battle_prob BY VALUE: the reinit branch's own write (op 26 in Main_Reinit), never A's (A follows
        # a Main_Init load) -- the stand-in's FAKE_WORLD_BATTLE_PROB_REINIT, the bench's oracle in game
        ok = (st.world_mapvar is not None and st.world_mapvar == a.world_mapvar
              and st.world_battle_prob == FG.FAKE_WORLD_BATTLE_PROB_REINIT != a.world_battle_prob)
        return ok, f"mapvar same {st.world_mapvar == a.world_mapvar}, battle_prob {a.world_battle_prob}->{st.world_battle_prob}"
    led.row("WD-MAPVAR", mapvar)

    def frozen():
        e0 = a.world_freeze_edges or 0
        st, moved = _hold_up(g)
        ok = st.ui_state == "WorldHUD" and st.world_freeze_on is True and moved < 2.0 and (st.world_freeze_edges or 0) == e0 + 1
        return ok, f"ui {st.ui_state}, freeze.on {st.world_freeze_on}, moved {moved:.2f}, edges {e0}->{st.world_freeze_edges}"
    led.row("WD-FROZEN", frozen)

    def again():
        """Each later row starts on the frozen world map under the role (a row a fault stranded elsewhere reds itself, not the
        rest): a diorama still up is left, a field re-enters the world at the spot, the role and `bench 1` re-forced."""
        st = g.state
        if _d(st, "booted"):
            _leave(g, lambda s: not _d(s, "booted"))
        if g.state.ui_state != "WorldHUD":
            _to_world(g, fake, 9011, *SPOT)
        if not (g.state.netsync or {}).get("forced"):
            g.netsync("selftest", 1)
        g.netsync("bench", 1)
        g.wait_frames(8)

    def reset():
        """`reset` with a world diorama up: the release waits for its teardown (the return lands warm), then the role is gone."""
        again()
        st0 = g.state
        r0 = _dio(st0, "returns", 0)
        _boot(g)
        g.send("reset")
        st = g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"] and s.ui_state == "WorldHUD",
                        timeout=8.0, what="the deferred release")
        ok = _dio(st, "returns") == r0 + 1 and _dio(st, "last_return") == "warm" and _away(st, (st0.world_x, st0.world_z)) < 4.0
        return ok, (f"returns {r0}->{_dio(st, 'returns')}, last {_dio(st, 'last_return')!r}, at ({st.world_x}, {st.world_z}) "
                    f"from ({st0.world_x}, {st0.world_z})")
    led.row("WD-RESET", reset)

    def vehicle():
        """Aboard (`vehicle 1` on 9011), a world boot DECLINES: refused, nothing booted, the decline counted durable -- and NO
        world reload (the world tick never restarted: the witness the engine does not compute)."""
        again()
        st0 = g.vehicle(1)
        d0, t0 = _dio(st0, "declines", 0), st0.world_ticks or 0
        why = _refused(g, lambda: _boot(g))
        g.wait_frames(6)
        st = g.state
        if _d(st, "booted"):                                 # (a fault booted aboard: out again, before the next row)
            _leave(g, lambda s: not _d(s, "booted"))
        g.send("vehicle 0")
        g.wait_frames(6)
        ok = (why is not None and "refused" in why and not _d(st, "booted") and st.ui_state == "WorldHUD"
              and _dio(st, "declines") == d0 + 1 and _dio(st, "decline_durable") is True
              and "aboard a vehicle (travel mode 1)" in (_dio(st, "decline_why") or "") and (st.world_ticks or 0) > t0
              and st.world_ctl == 1)
        return ok, (f"refusal {why and why[:80]!r}, declines {d0}->{_dio(st, 'declines')}, why {_dio(st, 'decline_why')!r}, "
                    f"ticks {t0}->{st.world_ticks}, ctl {st.world_ctl}")
    led.row("WD-VEHICLE", vehicle)

    def lever():
        again()
        st0 = g.netsync("bench", "worldwarm", "off")
        g.wait_frames(4)
        st0 = g.state
        d0, t0 = _dio(st0, "declines", 0), st0.world_ticks or 0
        why = _refused(g, lambda: _boot(g))
        g.wait_frames(6)
        st = g.state
        ok = (st0.world_dio_lever == "off" and why is not None and not _d(st, "booted") and _dio(st, "declines") == d0 + 1
              and _dio(st, "decline_durable") is True and (_dio(st, "decline_why") or "").startswith("CALIBRATION")
              and (st.world_ticks or 0) > t0)
        return ok, f"lever {st0.world_dio_lever!r}, declines {d0}->{_dio(st, 'declines')}, ticks {t0}->{st.world_ticks}"
    led.row("WD-LEVER", lever)

    def release():
        """Every harness release puts the lever back ON, its line once (this row pulls it itself)."""
        again()
        n0 = _log(fake).count(BW.LOG_WORLD_WARM_RELEASED)
        g.netsync("bench", "worldwarm", "off")
        g.wait_frames(4)
        g.send("reset")
        g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        g.netsync("selftest", 1)
        st = g.wait_for(lambda s: s.netsync["forced"], timeout=5.0, what="the role again")
        n = _log(fake).count(BW.LOG_WORLD_WARM_RELEASED) - n0
        g.netsync("bench", 1)
        g.wait_frames(10)
        return st.world_dio_lever == "on" and n == 1, f"lever {st.world_dio_lever!r}, release lines {n}"
    led.row("WD-RELEASE", release)

    def cold():
        """THE COLD REFERENCE, last (`bench worldwarm cold`): the boot primes no copy, so its return re-enters through Main_Init
        -- the spawn, the MAP vars Main_Init writes: the rows that judge a warm return CAN fail."""
        again()
        g.netsync("bench", "worldwarm", "cold")
        st = _boot(g)
        booted = _dio(st, "boot") == "cold"
        st = _leave(g, lambda s: s.ui_state in ("WorldHUD", "FieldHUD") and not _d(s, "booted"))
        g.wait_frames(10)
        st = g.state
        ok = (booted and _dio(st, "last_return") == "cold" and _away(st, LANDING) < 4.0 and _away(st, (a.world_x, a.world_z)) > 4.0
              and st.world_mapvar != a.world_mapvar)
        g.send("reset")
        return ok, (f"boot cold {booted}, last {_dio(st, 'last_return')!r}, at ({st.world_x}, {st.world_z}), mapvar differs "
                    f"{st.world_mapvar != a.world_mapvar}")
    led.row("WD-COLD", cold)
    return led.rows


def _client(g, fake) -> dict:
    """THE FOLLOWED-CLIENT LEG: a live followed session (``follow_session``), its host on the world map and fighting on the wire
    (``host_at(battle=...)``, ``battle_nonce``): the world watcher."""
    led = _Rows()
    g.newgame(settle=0)
    g.warp(250)
    fake.follow_session(250, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, entrance=11)
    g.wait_frames(4)
    host_world = BW.HF_WORLD | BW.HF_MENU | BW.HF_CONTROL
    fake.host_at(0, flags=host_world)
    _to_world(g, fake, 9011, 120.0, 80.0)
    g.wait_frames(10)

    def wboot():
        fake.host_at(0, battle=True, battle_nonce=1, flags=BW.HF_BATTLE | BW.HF_MENU)
        st = g.wait_for(lambda s: s.ui_state == "BattleHUD" and _d(s, "booted"), timeout=6.0, what="the watcher's boot")
        ok = _dio(st, "booted_world") is True and _dio(st, "boot") == "warm" and _dio(st, "boot_world") == 9011
        return ok, f"dio {_dio(st)}"
    led.row("WC-BOOT", wboot)

    def follow():
        """Inside the world diorama the follow compares against NO field: the host's intent into the departed field (250) is
        not "arrived" there -- it waits, and arms the rejoin once the guest is back on the world map."""
        st = g.state
        a0 = ((st.netsync or {}).get("world") or {}).get("rejoin", {}).get("arms") or 0
        follow.inside = _dio(st, "booted_world") is True             # the intent goes out INSIDE the world diorama
        fake.host_intent(250)
        g.wait_frames(10)
        follow.a0 = a0
        return True, "intent sent"
    follow(); follow_rows = follow                                          # noqa: E702 -- the row is judged after the return

    def leave():
        fake.host_at(0, battle=False, flags=host_world)
        st = g.wait_for(lambda s: s.ui_state == "WorldHUD" and not _d(s, "booted"), timeout=8.0, what="the leave")
        g.wait_frames(6)
        st = g.state
        hold = ((st.netsync or {}).get("diorama") or {}).get("hold") or {}
        ok = (hold.get("why") == "host_world" and _dio(st, "last_return") == "warm" and _away(st, (120.0, 80.0)) < 4.0)
        return ok, f"hold.why {hold.get('why')!r}, last {_dio(st, 'last_return')!r}, at ({st.world_x}, {st.world_z})"
    led.row("WC-LEAVE", leave)

    def follow_judge():
        st = g.wait_for(lambda s: (s.netsync.get("world") or {}).get("rejoin", {}).get("arms", 0) > follow_rows.a0
                        or s.ui_state == "FieldHUD", timeout=4.0, what="the deferred intent's arm")
        arms = (st.netsync.get("world") or {}).get("rejoin", {}).get("arms", 0)
        return follow_rows.inside and arms > follow_rows.a0, f"sent inside the diorama {follow_rows.inside}, arms {follow_rows.a0}->{arms}"
    led.row("WC-FOLLOW", follow_judge)
    # the rejoin (if it armed) lands the guest on 250: let it, then back onto the world map for the rest
    fake.host_at(0, flags=host_world)
    try:
        g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=3.0, what="the rejoin's landing")
    except HarnessError:
        pass
    g.wait_frames(10)
    if g.state.ui_state != "WorldHUD":
        _to_world(g, fake, 9011, 120.0, 80.0)
    g.wait_frames(30)

    def decline():
        st0 = g.vehicle(6)
        d0 = _dio(st0, "declines", 0)
        fake.host_at(0, battle=True, battle_nonce=2, flags=BW.HF_BATTLE | BW.HF_MENU)
        g.wait_frames(int(fake.fps * 2.5))
        st = g.state
        fake.host_at(0, battle=False, flags=host_world)
        log = _log(fake)
        line = BW.log_world_declined(9011, (_dio(st, "visit_decline") or "?"), 2)
        ok = (st.ui_state == "WorldHUD" and not _d(st, "booted") and _dio(st, "declines") == d0 + 1
              and "aboard a vehicle" in (_dio(st, "visit_decline") or "") and log.count(line) == 1
              and "REFUSED on the world map" not in log.split("vehicle", 1)[-1])
        g.send("vehicle 0")
        g.wait_frames(10)
        return ok, f"declines {d0}->{_dio(st, 'declines')}, visit {_dio(st, 'visit_decline')!r}, booted {_d(st, 'booted')}"
    led.row("WC-DECLINE", decline)

    def released():
        """A ~ release survives a world battle round trip (decision 10): released, the host fights, the guest's diorama boots and
        returns warm -- still released."""
        why = fake.release_world_freeze()
        fake.host_at(0, battle=True, battle_nonce=3, flags=BW.HF_BATTLE | BW.HF_MENU)
        g.wait_for(lambda s: s.ui_state == "BattleHUD" and _d(s, "booted"), timeout=6.0, what="the boot")
        fake.host_at(0, battle=False, flags=host_world)
        st = g.wait_for(lambda s: s.ui_state == "WorldHUD" and not _d(s, "booted"), timeout=8.0, what="the return")
        g.wait_frames(6)
        st = g.state
        return why is None and st.world_freeze_released is True, f"release {why!r}, released after {st.world_freeze_released}"
    led.row("WC-RELEASE", released)
    return led.rows


def _bench(root, faults=(), caps=None, legs=("solo", "client"), setup=None) -> dict:
    rows = {}
    for leg, fn in (("solo", _solo), ("client", _client)):
        if leg not in legs:
            continue
        game = _game(root / leg)
        fake = _fake(game, faults, caps)
        if setup is not None:
            setup(fake)
        with _session(game, fake) as g:
            rows.update(fn(g, fake))
    return rows


ROWS = ("WD-FIELD", "WD-KEYS", "WD-BOOT", "WD-AUDIO", "WD-RETURN", "WD-PLACE", "WD-CAMERA", "WD-MAPVAR", "WD-FROZEN", "WD-RESET",
        "WD-VEHICLE", "WD-LEVER", "WD-RELEASE", "WD-COLD", "WC-BOOT", "WC-LEAVE", "WC-FOLLOW", "WC-DECLINE", "WC-RELEASE")
#: the control: green under every fault and on every engine (F3.3's field diorama path is behaviour-identical)
CONTROL = ("WD-FIELD",)
#: each fault lever's reds -- EXACTLY these rows, and why
DIO_FAULT_REDS = {
    "boot_cold": ("WD-BOOT", "WD-RETURN", "WD-PLACE", "WD-MAPVAR", "WD-RESET", "WC-BOOT", "WC-LEAVE"),   # a cold reload
    "leave_fieldmap": ("WD-RETURN", "WD-PLACE", "WD-CAMERA", "WD-MAPVAR", "WD-FROZEN", "WD-RESET", "WD-COLD", "WC-LEAVE",
                       "WC-FOLLOW", "WC-RELEASE"),                                 # the departed field, cold
    "prevmode_unset": ("WD-BOOT", "WD-CAMERA"),                                    # the return's camera reset (prevMode 1)
    "audio_field_block": ("WD-AUDIO",),                                            # the field block's cosmetic failure line
    "vehicle_boots": ("WD-VEHICLE",),                                              # a guest aboard boots
    "lever_ignored_warm": ("WD-LEVER", "WD-COLD"),                                 # off and cold both boot warm
    "warm_lever_stuck": ("WD-RELEASE",),                                           # the release leaves the lever
    "decline_reload": ("WD-VEHICLE", "WD-LEVER"),                                  # a refusal reloads the world (ticks restart)
    "return_uncounted": ("WD-RETURN", "WD-RESET", "WD-COLD", "WC-LEAVE"),         # s144's consume rule: no world return counted
    "refreeze_lost": ("WD-FROZEN",),                                               # free on the world map after the fight
    "hostworld_blind": ("WC-LEAVE",),                                              # leaves at the stall cap
    "follow_departed": ("WC-FOLLOW",),                                             # the intent read "arrived" in the diorama
    "decline_unprojected": ("WC-DECLINE",),                                        # REFUSED per attempt, the visit unread
    "release_world_end": ("WC-RELEASE",),                                          # s144's release lifetime
    "proof_fail": ("WD-KEYS",),                                                    # the engine's own proof line FAIL
}
#: the s144 stand-in (the calibration engine): every s145 row reads red but the control -- the keys absent, the driver refusing
#: `bench worldwarm`, `vehicle` and the world `dioboot` before the step, the watcher booting nothing from the world map
OLD_PREDICTED = tuple(r for r in ROWS if r not in CONTROL)
#: the solo leg under the calibration lever (`bench worldwarm off` pulled before it): every world boot DECLINES (refused, a
#: durable decline, nothing booted, no reload) -- so every row a world boot or its return feeds reads red; the keys, the field
#: control, the lever's own row, the release and the cold reference (its own lever replaces the pulled one) stay green
LEVER_PREDICTED = ("WD-AUDIO", "WD-BOOT", "WD-CAMERA", "WD-FROZEN", "WD-MAPVAR", "WD-PLACE", "WD-RESET", "WD-RETURN",
                   "WD-VEHICLE")    # (aboard, the lever's row outranks the vehicle's: the decline names the CALIBRATION, not the vehicle)


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    return _bench(tmp_path_factory.mktemp("clean"))


def test_the_stand_in_bench_is_green_on_s145(clean):
    assert tuple(clean) == ROWS, list(clean)
    assert not [n for n, (ok, _d) in clean.items() if not ok], {n: d for n, (ok, d) in clean.items() if not ok}


@pytest.mark.parametrize("fault", FG.WORLD_DIO_FAULTS)
def test_each_world_dio_fault_turns_exactly_its_rows_red(tmp_path, fault):
    rows = _bench(tmp_path, (fault,))
    red = sorted(n for n, (ok, _d) in rows.items() if not ok)
    assert red == sorted(DIO_FAULT_REDS[fault]), {n: rows[n][1] for n in set(red) ^ set(DIO_FAULT_REDS[fault])}


def test_the_faults_cover_every_row_but_the_control_and_the_table_is_the_fakes():
    assert set(DIO_FAULT_REDS) == set(FG.WORLD_DIO_FAULTS) and len(FG.WORLD_DIO_FAULTS) == len(set(FG.WORLD_DIO_FAULTS))
    assert all(DIO_FAULT_REDS[f] for f in FG.WORLD_DIO_FAULTS)
    covered = {r for reds in DIO_FAULT_REDS.values() for r in reds}
    assert covered == set(ROWS) - set(CONTROL), set(ROWS) - set(CONTROL) - covered
    assert not covered & set(CONTROL)
    src = (REPO / "tools" / "harness" / "fakegame.py").read_text(encoding="utf-8")
    assert all(f'#:   "{f}"' in src for f in FG.WORLD_DIO_FAULTS)


def test_the_control_row_can_fail(tmp_path):
    """The control is green under every fault -- and still a check: a field with no Main_Reinit boots COLD and returns through
    Main_Init, and WD-FIELD reads it red (its warm witness is the return's own branch on its field)."""
    rows = _bench(tmp_path, legs=("solo",), setup=lambda f: setattr(f, "reinit_fields", set()))
    assert rows["WD-FIELD"][0] is False, rows["WD-FIELD"]


def test_the_s144_stand_in_reads_exactly_old_predicted_red(tmp_path):
    """THE CALIBRATION ENGINE: on the s144 stand-in (the ladder through `worldwait`) every s145 row reads red -- but the control:
    a field diorama boots and returns warm on every engine."""
    rows = _bench(tmp_path, caps=FG.caps_through("worldwait"))
    red = sorted(n for n, (ok, _d) in rows.items() if not ok)
    assert red == sorted(OLD_PREDICTED), {n: rows[n][1] for n in set(red) ^ set(OLD_PREDICTED)}


def test_the_lever_reads_exactly_lever_predicted_red(tmp_path):
    game = _game(tmp_path)
    fake = _fake(game)
    fake._wdx["lever"] = BW.WORLD_WARM_OFF                 # NetSyncDiorama._benchWorldWarm, pulled before the leg
    with _session(game, fake) as g:
        rows = _solo(g, fake)
    red = sorted(n for n, (ok, _d) in rows.items() if not ok)
    assert red == sorted(LEVER_PREDICTED), {n: rows[n][1] for n in set(red) ^ set(LEVER_PREDICTED)}


# ------------------------------------------------------------------------------------------------ the driver's guards
def test_the_driver_never_sends_an_s145_step_to_an_s144_engine(tmp_path):
    """THE s110 HAZARD AGAIN: an s144 agent reads `bench worldwarm off` as `bench 1` (the field-gate bench ON), answers `vehicle`
    "unknown op", and refuses a world `dioboot` "from a live field only". The driver refuses all three before the step on an
    engine without `netsync.world.dio`; on s145 they land."""
    old_game = _game(tmp_path / "old")
    old = _fake(old_game, caps=FG.caps_through("worldwait"))
    with _session(old_game, old) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        _to_world(g, old)
        n = len(old.executed)
        with pytest.raises(HarnessError, match=r"netsync bench worldwarm: the deployed engine publishes no `netsync\.world\.dio`"):
            g.netsync("bench", "worldwarm", "off")
        with pytest.raises(HarnessError, match=r"vehicle: the deployed engine publishes no `netsync\.world\.dio`.*Not sent"):
            g.vehicle(1)
        with pytest.raises(HarnessError, match=r"netsync dioboot: the deployed engine publishes no `netsync\.world\.dio`.*Not sent"):
            g.netsync("dioboot", 359, 0, "wire")
        assert len(old.executed) == n and g.state.netsync["bench"] is False
    old._netsync(["bench", "worldwarm", "off"])                               # what that engine would DO with each
    assert old.netsync["bench"] is True
    with pytest.raises(RuntimeError, match=r"unknown op 'vehicle'"):
        old._execute(["vehicle", "1"])
    with pytest.raises(RuntimeError, match=re.escape(BW.DIOBOOT_FIELD_ONLY)):
        old._netsync(["dioboot", "359"])
    new_game = _game(tmp_path / "new")
    new = _fake(new_game)
    with _session(new_game, new) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        _to_world(g, new)
        st = g.netsync("bench", "worldwarm", "cold")
        assert new.executed[-1] == ["netsync", "bench", "worldwarm", "cold"] and st.netsync["bench"] is False
        assert g.wait_for(lambda s: s.world_dio_lever == "cold", timeout=4.0, what="the lever").world_dio_lever == "cold"
        assert g.vehicle(1).world_ctl == 1
        assert new.debug_status == BW.vehicle_status(1, 9011)[1]


def test_the_vehicle_verb_refuses_in_the_menus_words(tmp_path):
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(250)
        with pytest.raises(HarnessError, match="vehicle is an OVERWORLD verb"):
            g.vehicle(1)
        _to_world(g, fake, 9000, 100.0, 100.0)
        with pytest.raises(HarnessError) as err:
            g.vehicle(1)
        assert BW.vehicle_status(1, 9000)[1] in str(err.value)
        _to_world(g, fake, 9011, 100.0, 100.0)
        with pytest.raises(HarnessError) as err:
            g.vehicle(12)
        assert "mode 12" in str(err.value)
        with pytest.raises(HarnessError) as err:
            g.send("vehicle x")
        assert BW.vehicle_usage(["x"]) in str(err.value)
        assert g.vehicle(0).world_ctl == 0


# ------------------------------------------------------------------------------------------------ the keys, the stand-in
def test_the_stand_in_publishes_the_s145_keys_and_none_on_s144(tmp_path):
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(250)
        st = g.wait_for(lambda s: s.gmode == 1, timeout=4.0, what="gMode 1")
        raw = list(st.raw)
        assert raw[raw.index("gmode") + 1] == "prev_mode"
        assert list(st.raw["world"])[-11:] == list(BW.WORLD_LIVE_KEYS_S144) + list(BW.WORLD_WITNESS_SENTINELS)
        assert {k: st.raw["world"][k] for k in BW.WORLD_WITNESS_SENTINELS} == BW.WORLD_WITNESS_SENTINELS   # off the world map
        assert list(st.netsync["world"]) == list(BW.WORLD_SENTINELS) and st.world_dio_lever == "on"
        fake.enter_world(9011, 100.0, 100.0)
        st = g.wait_for(lambda s: s.gmode == 3 and s.world_ticks is not None and s.world_ticks > 0, timeout=4.0, what="world")
        assert st.prev_mode == 1 and st.world_battle_prob == FG.FAKE_WORLD_BATTLE_PROB_INIT and st.world_ctl == 0
        assert st.world_cam_rot == 0.0 and len(st.world_mapvar) == 160
    old_game = _game(tmp_path / "old")
    old = _fake(old_game, caps=FG.caps_through("worldwait"))
    with _session(old_game, old) as g:
        g.newgame(settle=0)
        old.enter_world(9011)
        st = g.wait_world(timeout=5)
        assert st.prev_mode is None and st.world_mapvar is None and st.coop_world_dio is False and "dio" not in st.netsync["world"]
        assert list(st.raw["world"])[-5:] == list(BW.WORLD_LIVE_KEYS_S144)


def test_the_stand_in_logs_the_proof_lines_by_stage(tmp_path):
    def heads(caps):
        fake = _fake(_game(tmp_path / (caps and "old" or "new")), caps=caps)
        logged = []
        fake._mlog = logged.append
        fake._dress_proof()
        return [ln.split("[NetSync] ", 1)[1] for ln in logged if "selftest: OK" in ln]
    new = heads(None)
    i = new.index(BW.proof_ok(BW.PROOF_LEADER_GUARD, BW.LEADER_GUARD_SELFTEST_ROWS))
    assert new[i + 1:i + 6] == [BW.proof_ok(BW.PROOF_WORLD_FREEZE, 46), BW.proof_ok(BW.PROOF_WORLD_REJOIN, 70),
                                BW.proof_ok(BW.PROOF_OVERLAY_TEXT, 50), BW.proof_ok(BW.PROOF_WORLD_DIORAMA, 86),
                                BW.proof_ok(BW.PROOF_WORLD_WATCHER, 59)]
    old = heads(FG.caps_through("worldwait"))
    j = old.index(BW.proof_ok(BW.PROOF_LEADER_GUARD, BW.LEADER_GUARD_SELFTEST_ROWS))
    assert old[j + 1:j + 4] == [BW.proof_ok(BW.PROOF_WORLD_FREEZE, 42), BW.proof_ok(BW.PROOF_WORLD_REJOIN, 70),
                                BW.proof_ok(BW.PROOF_OVERLAY_TEXT, 50)]
    assert not any(BW.PROOF_WORLD_DIORAMA in h or BW.PROOF_WORLD_WATCHER in h for h in old)


def test_a_release_survives_a_world_load_and_the_title_ends_it_on_s145(tmp_path):
    """Decision 10 on the stand-in: a ~ release survives a world load (it ends at the next FIELD load or the title); s144's
    stand-in ends it at the world load (tests/test_world_coop_harness.py pins that stage)."""
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(250)
        fake.follow_session(30999, flags=BW.HF_ON_FIELD | BW.HF_CONTROL)
        _to_world(g, fake)
        assert fake.release_world_freeze() is None
        assert fake.release_world_freeze() == "already released (until the next field load)"
        _to_world(g, fake, 9011, 110.0, 100.0)                                 # a world load: kept
        st = g.wait_for(lambda s: s.world_freeze_released is True, timeout=4.0, what="still released")
        assert BW.LOG_WORLD_FREEZE_REARMED_WORLD not in _log(fake)
        assert "[NetSync] " + BW.log_world_freeze_released("~ menu", 9011) in _log(fake)
        fake.ui_state, fake.field_id = "Title", -1                             # the title (the stand-in's seam)
        g.wait_for(lambda s: s.ui_state == "Title", timeout=4.0, what="the title")
        g.wait_frames(6)
        assert fake._wf_released is False and "[NetSync] " + BW.LOG_WORLD_FREEZE_REARMED_TITLE in _log(fake)


def test_the_accessors_cover_the_s145_keys_and_read_none_on_s144():
    table = CH.State.NETSYNC_WORLD_ACCESSORS
    assert {p for p in table if p.startswith("dio")} == {"dio"} | {f"dio.{k}" for k in BW.WORLD_DIO_SENTINELS}
    s144 = CH.State({"frame": 1, "netsync": {"world": {k: dict(v) for k, v in BW.WORLD_SENTINELS_S144.items()}}})
    assert s144.coop_world_wait is True and s144.coop_world_dio is False
    assert all(getattr(s144, n) is None for p, n in table.items() if p.startswith("dio"))


# ------------------------------------------------------------------------------------------------ the T2 tape, its facts and plan
def _pb():
    sys.path.insert(0, str(SCENARIOS))
    import _coop_peer_bench as pb                            # noqa: E402
    return pb


def test_the_world_battle_tapes_facts_and_plan_hold_and_each_refusal_reads_red():
    pb = _pb()
    rows = pb._world_battle_rows(pb.coop_peer_module())
    bad = [w for ok, w in rows if not ok]
    assert len(rows) == 8 and not bad, bad
    cp = pb.coop_peer_module()
    good = pb.world_battle_tape_facts(pb.synthetic_world_battle_tape(cp), cp)
    assert pb.plan_world_leg("world-battle", good)["expect"]["leave_whys"] == ("terminal", "host_world")
    # the dwell boundary: exactly the plan's need passes, a frame short refuses
    edge = pb.world_battle_tape_facts(pb.synthetic_world_battle_tape(cp, dwell_s=pb.WB_DWELL_NEED_S + 0.2), cp)
    short = pb.world_battle_tape_facts(pb.synthetic_world_battle_tape(cp, dwell_s=pb.WB_DWELL_NEED_S - 0.5), cp)
    assert edge["wb3"]["ok"] and not short["wb3"]["ok"] and not pb.plan_world_leg("world-battle", short)["ok"]
    # a field-250 tape is no world-battle tape (its battle reads 'field' before and after)
    field = pb.tape_facts(pb.synthetic_tape(cp), cp)
    assert not pb.plan_world_leg("world-battle", field)["ok"]


def test_coop_peer_where_reports_the_battle_segments_and_wants_a_world_battle(tmp_path, capsys):
    pb = _pb()
    cp = pb.coop_peer_module()
    tape = tmp_path / "wb.f9tape"
    field = tmp_path / "field.f9tape"
    for path, recs in ((tape, pb.synthetic_world_battle_tape(cp)), (field, pb.synthetic_tape(cp))):
        head = json.dumps({"tool": "test"}).encode("utf-8")
        body = b"".join(struct.pack("<dBI", r.t, r.dir, len(r.payload)) + bytes(r.payload) for r in recs)
        path.write_bytes(b"F9TAPE01" + struct.pack("<I", len(head)) + head + body)
    d = CP.tape_where(CP.read_tape(tape)[1])
    assert d["world_battles"] == 1 and d["battles"][0]["world"] and d["battles"][0]["map"] == 67
    assert CP.main(["where", str(tape), "--want", "world-battle"]) == 0
    assert CP.main(["where", str(field), "--want", "world-battle"]) == 1
    fd = CP.tape_where(CP.read_tape(field)[1])
    assert fd["world_battles"] == 0 and len(fd["battles"]) == 1 and not fd["battles"][0]["world"]
    out = capsys.readouterr().out
    assert "A WORLD-MAP BATTLE" in out and "VERDICT (--want world-battle): OK" in out and "VERDICT (--want world-battle): FAIL" in out


def test_the_span_verdict_is_keyed_by_the_guests_stage():
    """coop_cut_hold's s120-world span: stall_cap before s145, host_world on s145 when the tape's host says b6 after its victory
    (the stage law: never one answer for both) -- and the tape facts carry that b6."""
    pb = _pb()
    cp = pb.coop_peer_module()
    world = pb.synthetic_world_battle_tape(cp, field_s=25.0)
    facts = pb.tape_facts(world, cp, field=None)
    assert facts["after_b6"] is True and facts["after_field"] == 0
    plan = pb.plan_leg("span", facts, world=True)
    assert plan["expect"]["why"] == "stall_cap" and plan["expect"]["why_s145"] == "host_world"
    assert pb.span_why(plan, 144) == "stall_cap" and pb.span_why(plan, 145) == "host_world"
    plain = pb.tape_facts(pb.synthetic_tape(cp), cp)
    assert plain["after_b6"] is False and pb.span_why(pb.plan_leg("span", plain), 145) == "host_field"
    src = (SCENARIOS / "coop_cut_hold.py").read_text(encoding="utf-8")
    assert "want = pb.span_why(ctx.plan, ctx.stage)" in src and "why = pb.span_why(ctx.plan, ctx.stage)" in src
    assert "the host's fight is over (the peer is alive and back on the world map)" in src
    assert BW.WATCH_WHY_TEXT_HOST_WORLD == "the host's fight is over (the peer is alive and back on the world map)"


def test_coop_world_waits_probe_reads_its_engines_stage():
    """coop_world_wait's P0 (judge_probe) by stage: an s145 engine's `world` adds `dio` and its freeze line reads 46 rows; an
    s144 engine's is the three blocks and 42 -- each stage's count can fail on the other."""
    spec = importlib.util.spec_from_file_location("coop_world_wait_s145", SCENARIOS / "coop_world_wait.py")
    sys.path.insert(0, str(SCENARIOS))
    cw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cw)
    L = lambda *m: ["21.10.2026 12:00:00 |M| [NetSync] " + x for x in m]   # noqa: E731

    def st(dio):
        world = {k: dict(v) for k, v in (BW.WORLD_SENTINELS if dio else BW.WORLD_SENTINELS_S144).items()}
        return CH.State({"frame": 1, "netsync": {"world": world, "session": {"overlay_text": None,
                                                                             "follow": dict(BW.SESSION_FOLLOW_SENTINELS)}}})

    def proof(freeze):
        return L(BW.proof_ok(BW.PROOF_WORLD_FREEZE, freeze), BW.proof_ok(BW.PROOF_WORLD_REJOIN, 70),
                 BW.proof_ok(BW.PROOF_OVERLAY_TEXT, 50))
    assert cw.judge_probe(st(True), proof(46))[0] and not cw.judge_probe(st(True), proof(42))[0]
    assert cw.judge_probe(st(False), proof(42))[0] and not cw.judge_probe(st(False), proof(46))[0]


# ------------------------------------------------------------------------------------------------ the recorder's variant
def _recorder(monkeypatch, **env):
    for k in ("COOP_TAPE_WORLD", "COOP_TAPE_WORLD_BATTLE", "COOP_TAPE_SEAT", "COOP_PEER_PORT"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    sys.path.insert(0, str(SCENARIOS))
    spec = importlib.util.spec_from_file_location("coop_tape_record_s145", SCENARIOS / "coop_tape_record.py")
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    return rec


def test_the_world_battle_recorder_variant_plans_its_dwell_and_keeps_its_own_home(monkeypatch):
    pb = _pb()
    rec = _recorder(monkeypatch, COOP_TAPE_WORLD_BATTLE="1")
    assert rec.WORLD_BATTLE_TAPE and rec.ANY_WORLD and not rec.WORLD_TAPE and rec.PORT == pb.WORLD_PORT != pb.OWNER_PORT
    assert rec.PRE_S == 25.0 and rec.WB_DWELL_S >= pb.WB_DWELL_NEED_S + 10.0 and rec.WB_FIGHT_S >= pb.WB_LIVE_NEED_S
    assert rec.WB_POST_S >= pb.WB_AFTER_NEED_S and (rec.WB_SCENE, rec.WB_GROUP) == (67, 0)
    cat = rec._catalog(0)
    assert list(cat) == list(rec.WORLD_BATTLE_CATALOG) and "REC-B" not in cat and "REC-WS" not in cat
    assert [k for k in cat if k.startswith("REC-WBF")] == [f"REC-WBF{i}" for i in range(1, 6)]
    assert list(cat)[-1] == "REC-INI" and {"REC-WX", "REC-WD", "REC-WB", "REC-WW", "REC-WP", "REC-T"} <= set(cat)
    src = (SCENARIOS / "coop_tape_record.py").read_text(encoding="utf-8")
    assert "g.world_battle(WB_SCENE, group=WB_GROUP, rand=True)" in src and "pb.WORLD_BATTLE_POINTER" in src
    assert "COOP_TAPE_WORLD and COOP_TAPE_WORLD_BATTLE are separate variants" in src
    plain = _recorder(monkeypatch)
    assert not plain.ANY_WORLD and plain.PORT == pb.DEFAULT_PORT and list(plain._catalog(0)) == list(plain.CATALOG)
    world = _recorder(monkeypatch, COOP_TAPE_WORLD="1")
    assert world.WORLD_TAPE and not world.WORLD_BATTLE_TAPE and list(world._catalog(0)) == list(world.WORLD_CATALOG)


# ------------------------------------------------------------------------------------------------ fix1: the watcher's dedup, the bee
def _declines_over_an_epoch(tmp_path, *, reset=True) -> tuple:
    """A followed client aboard a vehicle on the world map: the host's nonce-1 fight declines; the same nonce again (the same fight)
    does not count twice; then the host RELAUNCHES (a new epoch: its battle nonces restart) and fights nonce 1 again. ``reset``
    False = the s145 engine before fix1 (ResetGuestDedupForEpoch never cleared the world watcher's latches). -> (the declines after
    each step, the declined lines logged)."""
    game = _game(tmp_path)
    fake = _fake(game)
    if not reset:
        fake._wdio_epoch_reset = lambda epoch: fake._wdx.update(epoch_seen=int(epoch))   # the epoch seen, nothing forgotten
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(250)
        fake.follow_session(250, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, entrance=11)
        g.wait_frames(4)
        host_world = BW.HF_WORLD | BW.HF_MENU | BW.HF_CONTROL
        fake.host_at(0, flags=host_world)
        _to_world(g, fake, 9011, 120.0, 80.0)
        g.wait_frames(10)
        g.vehicle(6)
        counts = []
        for epoch in (0, 0, 1):
            fake.host_at(0, epoch=epoch)
            fake.host_at(0, battle=True, battle_nonce=1, flags=BW.HF_BATTLE | BW.HF_MENU)
            g.wait_frames(int(fake.fps * 1.0))
            fake.host_at(0, battle=False, flags=host_world)
            g.wait_frames(int(fake.fps * 0.5))
            counts.append(_dio(g.state, "declines"))
        why = _dio(g.state, "visit_decline") or "?"
        return counts, _log(fake).count(BW.log_world_declined(9011, why, 1))


def test_a_host_relaunch_resets_the_world_watchers_decline_dedup(tmp_path):
    """watcher-decline-dedup-epoch: a relaunched host restarts its battle nonces from 0, so a same-nonce decline in the new
    session must still log its line and count -- ResetGuestDedupForEpoch resets the world watcher's (nonce, why) latches; the same
    fight inside one session never counts twice."""
    counts, lines = _declines_over_an_epoch(tmp_path / "fix1")
    assert counts == [1, 1, 2] and lines == 2, (counts, lines)
    # the red: without the reset the new session's nonce-1 decline is swallowed (no line, no count)
    counts, lines = _declines_over_an_epoch(tmp_path / "old", reset=False)
    assert counts == [1, 1, 1] and lines == 1, (counts, lines)


def test_the_bee_scene_declines_with_its_line_and_count_never_a_silent_wait(tmp_path):
    """watcher-bee-decline-silent: the bee scene is a DURABLE row -- the watcher declines it like every other durable row (one line,
    declines +1 per fight), never a quiet wait that reports NONE with no witness."""
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(250)
        fake.follow_session(250, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, entrance=11)
        g.wait_frames(4)
        fake.host_at(0, flags=BW.HF_WORLD | BW.HF_MENU | BW.HF_CONTROL)
        _to_world(g, fake, 9011, 120.0, 80.0)
        g.wait_frames(10)
        fake.world_bee = True
        d0 = _dio(g.state, "declines", 0)
        fake.host_at(0, battle=True, battle_nonce=4, flags=BW.HF_BATTLE | BW.HF_MENU)
        g.wait_frames(int(fake.fps * 1.0))
        st = g.state
        fake.host_at(0, battle=False)
        why = BW.world_warm_row(BW.world_warm_in(bee_scene=True))[0]
        assert _dio(st, "visit_decline") == why and _dio(st, "declines") == d0 + 1 and not _d(st, "booted")
        assert _log(fake).count(BW.log_world_declined(9011, why, 4)) == 1


# ------------------------------------------------------------------------------------------------ fix2: the Leave's song latch
def _wb():
    """coop_world_battle, for its PURE judge_music (nothing patched)."""
    sys.path.insert(0, str(SCENARIOS))
    spec = importlib.util.spec_from_file_location("coop_world_battle_fix2", SCENARIOS / "coop_world_battle.py")
    wb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wb)
    return wb


def _music_trip(tmp_path, *, finished: bool, faults=()) -> dict:
    """A WORLD boot's round trip on the stand-in WITH its sound instances (``world_music``: world song 12, battle song 40): A on the
    world map, the booted sample, then -- ``finished`` -- a won fight's end-leave with NO result-screen replay (the settle's
    StopCurrentSong(120) shuts the victory song: a 2 s fade), sampled at the FIRST world frame back -- inside that fade; else a
    mid-fight `dioleave` (nothing settled: the battle song still current, BeforeWorldEvents' stop owns it), sampled past
    BeforeWorldEvents' 500 ms fade. The samples, whether the first was inside the settle's fade, and coop_world_battle.judge_music."""
    root = _game(tmp_path)
    fake = _fake(root)
    fake.world_music = (12, 40)
    fake.world_music_faults = set(faults)
    with _session(root, fake) as g:
        g.newgame(settle=0)
        g.warp(250)
        g.netsync("selftest", 1)
        g.warp(6603)
        g.wait_frames(10)
        _to_world(g, fake, from_field=True)
        g.send("hold up 30")
        g.wait_frames(36)
        g.netsync("bench", 1)
        g.wait_frames(12)
        a = g.state
        booted = _boot(g)
        r0 = _dio(booted, "returns", 0)

        def back(s):
            return s.ui_state == "WorldHUD" and not _d(s, "booted") and _dio(s, "returns") == r0 + 1
        if finished:
            g.netsync("endbench", "victory")
            g.wait_for(lambda s: s.coop_present_r8_hits > 0, timeout=10.0, what="R8")
            g.netsync("endbench", "ui", 1)
            g.netsync("endbench", "state", 6)
            g.netsync("endbench", "state", 7)
            ret = g.wait_for(back, timeout=8.0, what="the end-leave's return")
        else:
            _leave(g, back)
            g.wait_frames(int(FG.FAKE_SONG_STOPCURRENT_FADE_S * 60) + 12)
            ret = g.state
        stops = [v["stop_frame"] for v in fake._wsnd["voices"].values() if v["song"] != 12 and v["stop_frame"] is not None]
        inside = bool(stops) and ret.frame - max(stops) < FG.FAKE_SONG_SETTLE_FADE_S * 60
        return {"a": a, "booted": booted, "ret": ret, "inside": inside, "music": _wb().judge_music(ret, a, booted),
                "settled": (ret.coop_exit_settled, ret.coop_exit_music_shut)}


def test_the_leave_latches_the_battle_song_after_its_settle_and_reads_a_song_left_playing(tmp_path):
    """raudio-1 (fix2) on the stand-in's sound instances: the Leave latches the instance current AFTER SettleForReturn. A won fight
    whose end-leave the settle closes (no result-screen replay: StopCurrentSong(120), a 2 s fade with IsExist 1) and whose return is
    sampled INSIDE that fade reads boot_song_live false -- MUSIC green; the pre-fix2 order (`latch_before_settle`) reads that fading
    victory song as 'left playing' -- MUSIC red on a correct return (the false red this fix removes). A mid-fight Leave still latches
    the battle song: with BeforeWorldEvents' stop it reads false past its 500 ms fade (green); without it (`bwe_stop_missing`) the
    battle song plays on over the restored world song -- MUSIC red (the hazard the witness exists for)."""
    fin = _music_trip(tmp_path / "fin", finished=True)
    assert fin["settled"] == (True, True) and fin["inside"], (fin["settled"], fin["inside"])   # the settle shut it; sampled in its fade
    assert _dio(fin["ret"], "boot_song_live") is False and fin["music"][0], fin["music"]
    assert _dio(fin["ret"], "song_sid") == _dio(fin["a"], "song_sid") >= 0 and _dio(fin["booted"], "suspend_song") == 12
    early = _music_trip(tmp_path / "early", finished=True, faults=["latch_before_settle"])
    assert early["settled"] == (True, True) and early["inside"]
    assert _dio(early["ret"], "boot_song_live") is True and not early["music"][0], early["music"]
    assert "still playing True" in early["music"][1]
    mid = _music_trip(tmp_path / "mid", finished=False)
    assert mid["settled"][0] is False and _dio(mid["ret"], "boot_song_live") is False and mid["music"][0], mid["music"]
    left = _music_trip(tmp_path / "left", finished=False, faults=["bwe_stop_missing"])
    assert _dio(left["ret"], "boot_song_live") is True and not left["music"][0], left["music"]
    # [fix3 -- v-raudio-1-2] each sound fault reds ONLY its own lane: after a settle that shut the song BeforeWorldEvents has nothing
    # to stop (the fix's own premise -- `bwe_stop_missing` on the finished lane reads green), and a mid-fight Leave settles nothing
    # (the latch's order is moot there -- `latch_before_settle` on the mid lane reads green)
    fin_bwe = _music_trip(tmp_path / "fin_bwe", finished=True, faults=["bwe_stop_missing"])
    assert fin_bwe["settled"] == (True, True) and fin_bwe["inside"], (fin_bwe["settled"], fin_bwe["inside"])
    assert _dio(fin_bwe["ret"], "boot_song_live") is False and fin_bwe["music"][0], fin_bwe["music"]
    mid_early = _music_trip(tmp_path / "mid_early", finished=False, faults=["latch_before_settle"])
    assert mid_early["settled"][0] is False, mid_early["settled"]
    assert _dio(mid_early["ret"], "boot_song_live") is False and mid_early["music"][0], mid_early["music"]
    # the model off (the default): the stand-in plays no music -- fix1's witnesses idle, as every other stand-in run reads them
    assert _fake(_game(tmp_path / "idle"))._wsnd_doc() == {"suspend_song": -1, "song_sid": -1, "boot_song_live": False}
    assert set(FG.WORLD_MUSIC_FAULTS) == {"bwe_stop_missing", "latch_before_settle"}


def test_the_sound_models_wall_fades_end_on_the_wall_whatever_the_frame_clock(tmp_path, monkeypatch):
    """[fix3-r2] v-raudio-1-1-fade-scale-premise-wrong: ``world_music_wall`` puts the sound model's stop fades on the WALL clock, as
    SaXAudio runs them (SdSoundSystem_SoundCtrl_Stop -> SaXAudio.Stop(soundID, ms / 1000f): a native real-time fade) -- a
    Leave-latched instance stopped at BeforeWorldEvents' 500 ms floor reads boot_song_live true until 500 ms of WALL time pass,
    however far the virtual clock runs (the stand-in's runs ~5x the wall at fps=600, never a fixed ratio); off (the default) the
    fade ends on the virtual clock, as every earlier run reads it."""
    import time
    fade = 2.0                                                # a fade long enough that no box reads past it by accident
    for wall in (True, False):
        fake = _fake(_game(tmp_path / f"wall{int(wall)}"))
        fake.world_music, fake.world_music_wall = (12, 40), wall
        monkeypatch.setattr(fake, "_wdio", lambda: True)      # the worlddio rung on (the model needs it), nothing running
        fake._wsnd_play(40)
        fake._wsnd["leave_sid"] = fake._wsnd["cur_sid"]       # LeaveFrom's latch: the battle song's instance
        t_stop = time.time()
        fake._wsnd_stop_current(fade)
        assert fake._wsnd_doc()["boot_song_live"] is True     # inside its fade on either clock
        fake.rt += 10.0 * fade                                # far past it on the virtual clock, no wall time
        assert fake._wsnd_doc()["boot_song_live"] is wall, wall   # the wall fade still sounding; the virtual one long over
        assert time.time() - t_stop < fade                    # (read inside the wall fade: the check above meant it)
        if wall:
            while time.time() - t_stop < fade + 0.05:
                time.sleep(0.05)
            assert fake._wsnd_doc()["boot_song_live"] is False   # past the fade on the WALL: over


def test_a_frozen_guest_on_topograph_52_declines_never_holds_the_host(tmp_path):
    """warm-4: topograph 52 is DURABLE -- a frozen guest standing on a 52 cell reports NONE (the projection declines it: one line, one
    count), never BOOTING with no boot behind it (the host's start hold held every such fight to StartHoldMs)."""
    assert BW.world_row_durable(BW.WORLD_ROW_TOPOGRAPH) and "topograph" in BW.WORLD_DURABLE_INPUTS
    assert BW.world_decline_why(BW.world_warm_in(topograph=52)) is not None
    assert not BW.boot_watching(True, True, False, True, True, BW.world_decline_why(BW.world_warm_in(topograph=52)))
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(250)
        fake.follow_session(250, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, entrance=11)
        g.wait_frames(4)
        fake.host_at(0, flags=BW.HF_WORLD | BW.HF_MENU | BW.HF_CONTROL)
        _to_world(g, fake, 9011, 120.0, 80.0)
        g.wait_frames(10)
        fake.world_topo = 52
        d0 = _dio(g.state, "declines", 0)
        fake.host_at(0, battle=True, battle_nonce=5, flags=BW.HF_BATTLE | BW.HF_MENU)
        g.wait_frames(int(fake.fps * 1.0))
        st = g.state
        fake.host_at(0, battle=False)
        assert "topograph 52" in (_dio(st, "visit_decline") or "") and _dio(st, "declines") == d0 + 1 and not _d(st, "booted")
