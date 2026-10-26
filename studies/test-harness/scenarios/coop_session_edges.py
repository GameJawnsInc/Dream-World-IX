"""s153 -- THE SESSION-EDGE ROUND, the SOLO bench (studies/coop-review/REVIEW.md section 1, memoria-patches s153).

One instance root, harness-driven, unattended. Each leg is one fix's own in-game check:

  E1  the selftest proof block: "session edges selftest: OK" (the suppress rule, the host never follows, the session-over
      diorama leave, the ending pass, the single-shot intake's command types) and "dialogue authority selftest: OK" (now
      with the inbox-TTL-under-a-pause rows and the orphan re-ask breaker's rows).
  E2  fix 8, the ghost's unknown anim id: `netsync selfdress wire 98 65000` makes the selftest mirror play a clip this
      install does not register. Pre-s153 DriveGhost's GetValue threw on it every frame ("[NetSync] update failed").
      Green = one "the peer plays anim 65000, which this install does not register" line and NO "update failed".
  E3  fix 5, the single-shot intake: in an own selftest battle whose loopback guest owns slot 1, `netsync bcmd` sends
      ActInstant on menu 4 (Item: an Item-type command) -> dropped "Item-type command is not a single-shot pick"; then
      ActInstant on menu 3 (slot 1's Ability2) -> its outcome is named (Vivi's Focus is an Instant command: queued).
  E4  fix 7, the direct-LAN listener: Role=host, no relay, a private port. Co-op off then on again live: the new host
      binds again ("host listening" twice, no "host loop failed" / "cannot listen"), and a TCP connect from here reaches it
      ("peer connected:"). Pre-s153 the old HostLoop kept the port and the second bind failed.

THE PREREQS: the instance root (py tools/harness/instance.py ensure C:\\gd\\ff9-inst\\host), COOPPARTY (30604) and LOCKT2
(30602) registered (the -msgs folder), no other FF9 from that root, no controller, nobody at the keyboard.

    py tools/play.py studies/test-harness/scenarios/coop_session_edges.py --instance C:\\gd\\ff9-inst\\host
"""
from __future__ import annotations

import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

GUEST = 1                         # the loopback guest's party slot
LAN_PORT = 49233                  # private: never the owner's 49200 / 49201
UNKNOWN_ANIM = 65000              # the kit's minted-anim band top; no stock or deployed id here

CATALOG = {
    "E0": "the forced selftest role on the bench field",
    "E1a": "session edges selftest: OK",
    "E1b": "dialogue authority selftest: OK (with the s153 rows)",
    "E2": "an unregistered wire anim is logged once and Update keeps running (no 'update failed')",
    "E3-pre": "slot 1 seated and ready in an own battle",
    "E3a": "ActInstant on menu 4 (an Item-type command) is refused at the host intake, named",
    "E3b": "ActInstant on menu 3 (slot 1's Ability2) is judged by its type, not refused for being single-shot",
    "E4a": "a direct-LAN host listens on the private port",
    "E4b": "co-op off then on again live: the new host binds again (no 'host loop failed' / 'cannot listen')",
    "E4c": "a TCP connect reaches the NEW listener ('peer connected:')",
}


def run(g, field: int = cb.FIELD):
    led = cb.Ledger(g, CATALOG)
    try:
        _selftest_legs(g, led, field)
        cb.release(g)
        _lan_leg(g, led)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'session-edges')}")
        try:
            if g.instance is not None and g.instance.restore_ini():
                g.note("the root's Memoria.ini put back to install + overlay")
        except Exception as err:                       # noqa: BLE001 - teardown must not mask the verdicts
            g.note(f"restore_ini failed: {err}")
        led.close(final=True)


def _selftest_legs(g, led, field):
    at0 = cb.mark(g)
    ok, why = cb.setup(g, field, label="s153 session edges, solo")
    led.check("E0", ok, why)
    if not ok:
        led.close("the forced selftest role did not arm")
        return
    lines = cb.wait_log(g, at0, "session edges selftest:", timeout=20.0)
    edge = [ln for ln in lines if "session edges selftest:" in ln]
    led.check("E1a", bool(edge) and "OK (" in edge[-1], cb.grep(lines, "session edges selftest:") or "no line")
    dlg = [ln for ln in lines if "dialogue authority selftest:" in ln]
    led.check("E1b", bool(dlg) and "OK (" in dlg[-1], cb.grep(lines, "dialogue authority selftest:")[:300] or "no line")

    # the raw-anim rule plays the wire's own clip only on its OWN body (NetSyncVisitor.GhostAnim: dress == wire model); the bench
    # mirror wears the auto dress (the moogle with GuestSlots 0), so pin the stand-in body to the model the ghost wears -- else
    # the unknown id never reaches DriveGhost's lookup and this leg cannot fail (calibrated: first run, 0 lines either way)
    worn = (cb.path(g.state, "netsync.dress.ghost.model", -1) or -1)
    body = worn if isinstance(worn, int) and worn > 0 else 98
    at = cb.mark(g)
    ok, why = cb.try_ns(g, "selfdress", "wire", body, UNKNOWN_ANIM)
    time.sleep(4.0)
    lines = cb.new(g, at)
    seen = cb.count(lines, f"the peer plays anim {UNKNOWN_ANIM}, which this install does not register")
    failed = cb.count(lines, "update failed")
    led.check("E2", ok and seen == 1 and failed == 0,
              (why or "") + f" body {body}; unknown-anim lines {seen}, 'update failed' lines {failed}; "
              + cb.grep(lines, "does not register", "update failed"))
    cb.try_ns(g, "selfdress", "wire", "off")

    ok, why = cb.try_ns(g, "guestslots", 2)
    if not ok:
        led.unreached(["E3-pre", "E3a", "E3b"], f"`netsync guestslots 2` refused -- {why}")
        return
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        led.unreached(["E3-pre", "E3a", "E3b"], f"`battle {cb.SCENE}` did not start: {str(err)[:200]}")
        return
    st = cb.poll(g, lambda s: s.commands_enabled and (cb.mask_bits(cb.peer(s).get("ready_mask")) & (1 << GUEST)),
                 75.0, "slot 1 ready in an own battle")
    seated = st is not None and GUEST in cb.player_slots(st)
    led.check("E3-pre", seated, f"party slots {cb.player_slots(st or g.state)}; ready_mask "
              f"{cb.peer(st or g.state).get('ready_mask')!r}")
    if not seated:
        led.unreached(["E3a", "E3b"], "slot 1 was not seated and ready")
        return
    h0 = cb.host(g.state)
    at = cb.mark(g)
    ok, why = cb.try_ns(g, "bcmd", *cb.cmd_hex(GUEST, cb.ACT_INSTANT, menu=4, mask=1 << GUEST).split())
    lines = cb.wait_log(g, at, "not a single-shot pick", timeout=4.0)
    h1 = cb.host(g.state)
    led.check("E3a", ok and cb.count(lines, "not a single-shot pick") >= 1
              and (h1.get("cmd_dropped") or 0) > (h0.get("cmd_dropped") or 0)
              and (h1.get("cmd_queued") or 0) == (h0.get("cmd_queued") or 0),
              (why or "") + f" dropped {h0.get('cmd_dropped')}->{h1.get('cmd_dropped')} queued {h0.get('cmd_queued')}->"
              f"{h1.get('cmd_queued')}; " + cb.grep(lines, "peer command"))
    enemy = cb.first_enemy(g.state)
    mask = (1 << int(enemy.get("slot", 4))) if enemy else 0x10   # enemies ride btl_id bits 4-7
    at = cb.mark(g)
    ok, why = cb.try_ns(g, "bcmd", *cb.cmd_hex(GUEST, cb.ACT_INSTANT, menu=3, mask=mask).split())
    lines = cb.wait_log(g, at, "peer command", timeout=4.0)
    h2 = cb.host(g.state)
    refused_as_single_shot = cb.count(lines, "not a single-shot pick") > 0
    led.check("E3b", ok and not refused_as_single_shot and cb.count(lines, "peer command") >= 1,
              (why or "") + f" queued {h1.get('cmd_queued')}->{h2.get('cmd_queued')}; " + cb.grep(lines, "peer command"))
    cb.release(g)
    try:
        g.fight(timeout=180.0)                         # finish the bench battle: the LAN leg starts from the field
    except HarnessError as err:
        g.note(f"the bench battle's finish: {str(err)[:200]}")
    cb.poll(g, lambda s: s.ui_state == "FieldHUD", 60.0, "back on the field after the bench battle")


def _lan_leg(g, led):
    if g.instance is None:
        led.unreached(["E4a", "E4b", "E4c"], "not an instance-root run: the LAN leg writes the root's own [Netsync]")
        return
    base = {"Enabled": "1", "Role": "host", "RelayUrl": "", "SessionCode": "", "PeerAddress": "127.0.0.1",
            "Port": str(LAN_PORT), "FollowHost": "0", "TargetField": "0", "GuestSlots": "0"}
    at = cb.mark(g)
    g.instance.netsync(base, backup_to=g.run_dir / "ini")
    lines = cb.wait_log(g, at, f"host listening on port {LAN_PORT}", timeout=6.0)
    if cb.count(lines, f"host listening on port {LAN_PORT}") == 0:
        g.warp(g.state.field_id)                       # a root booted co-op-off reads its ini at a field load
        lines = cb.wait_log(g, at, f"host listening on port {LAN_PORT}", timeout=15.0)
    led.check("E4a", cb.count(lines, f"host listening on port {LAN_PORT}") >= 1, cb.grep(lines, "host", "config"))
    at = cb.mark(g)
    g.instance.netsync(dict(base, Enabled="0"), backup_to=g.run_dir / "ini")
    cb.wait_log(g, at, "config change applied live (disabled)", timeout=8.0)
    g.instance.netsync(base, backup_to=g.run_dir / "ini")
    lines = cb.wait_log(g, at, f"host listening on port {LAN_PORT}", timeout=12.0)
    bad = cb.count(lines, "host loop failed") + cb.count(lines, "cannot listen")
    led.check("E4b", cb.count(lines, f"host listening on port {LAN_PORT}") >= 1 and bad == 0,
              cb.grep(lines, "host listening", "host loop failed", "cannot listen", "config change applied live"))
    at = cb.mark(g)
    connected = False
    try:
        with socket.create_connection(("127.0.0.1", LAN_PORT), timeout=5.0):
            lines = cb.wait_log(g, at, "peer connected:", timeout=6.0)
            connected = cb.count(lines, "peer connected:") >= 1
    except OSError as err:
        lines = cb.new(g, at)
        g.note(f"TCP connect to {LAN_PORT} failed: {err}")
    led.check("E4c", connected, cb.grep(lines, "peer connected", "host loop failed", "disconnected"))
    at = cb.mark(g)
    g.instance.netsync(dict(base, Enabled="0"), backup_to=g.run_dir / "ini")
    cb.wait_log(g, at, "config change applied live (disabled)", timeout=8.0)
