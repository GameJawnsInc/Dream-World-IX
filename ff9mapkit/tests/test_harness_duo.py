"""``tools/harness/duo.py`` -- two instance-root games paired over a local relay, offline.

WHAT THESE PIN. A Duo over two FakeGames in two tmp roots (built from a fake install, never the real one) runs the P4
recipe end to end against a SIMULATED engine that answers each root's own ini in that root's Memoria.log: each role's
[Netsync] lands in its OWN root (Role=client for the guest, never ``guest``), a config that only lands at a field load is
fetched with ONE same-field warp, the cross-instance helpers judge both games and record on both Sessions, a strict red
stops the run and still restores both inis and writes duo.json, and the laws -- private ports, a fresh code, two distinct
roots -- refuse before anything starts. The duo's engine-line matchers are pinned to the T2 bench's (whose self-check
pins THEM to the engine's C#). The helper-process wrapper is exercised against a real ``coop_peer relay``.

WHAT THEY ARE NOT. No FF9 runs, no engine pairs: ``py tools/harness/duo.py --smoke`` (and duo_p4.py) is that proof.
"""

import datetime as _dt
import json
import os
import pathlib
import re
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from harness import HarnessError, Session                          # noqa: E402
from harness import duo as D                                       # noqa: E402
from harness import instance as I                                  # noqa: E402
from harness.fakegame import FakeGame                              # noqa: E402
from test_harness_instance import make_install                     # noqa: E402

needs_junctions = pytest.mark.skipif(os.name != "nt", reason="NTFS junctions are Windows-only")


def stamp() -> str:
    return _dt.datetime.now().strftime("%d.%m.%Y %H:%M:%S")


class FakeEngine(threading.Thread):
    """Plays both games' NetSync for the duo: watches each root's OWN Memoria.ini [Netsync] and answers in that root's
    Memoria.log the way the engine does -- the config line (the guest's only after a field LOAD, like a root booted with
    Netsync off), the relay legs, the pairing, a ghost each, the guest's mirror ARMED and the host's story byte."""

    def __init__(self, roots: dict, fakes: dict, *, guest_config_needs_load: bool = True, guest_pairs: bool = True):
        super().__init__(daemon=True)
        self.roots, self.fakes = roots, fakes
        self.needs_load = guest_config_needs_load
        self.guest_pairs = guest_pairs
        self.stop = threading.Event()
        self.said: dict = {r: set() for r in roots}
        self.visit_at_enable: dict = {}

    def ns(self, role: str) -> dict:
        from ff9mapkit.coop import read_ini_key
        try:
            text = (self.roots[role] / "Memoria.ini").read_text(encoding="utf-8")
        except OSError:
            return {}
        return {k: read_ini_key(text, "Netsync", k) for k in ("Enabled", "Role", "RelayUrl", "SessionCode")}

    def say(self, role: str, key: str, msg: str) -> None:
        if key in self.said[role]:
            return
        self.said[role].add(key)
        with open(self.roots[role] / "Memoria.log", "a", encoding="utf-8") as f:
            f.write(f"{stamp()} |I| {msg}\n")

    def run(self) -> None:
        while not self.stop.is_set():
            cfg = {r: self.ns(r) for r in self.roots}
            on = {r: cfg[r].get("Enabled") == "1" for r in self.roots}
            for r in self.roots:
                if not on[r]:
                    continue
                fake = self.fakes[r]
                self.visit_at_enable.setdefault(r, fake._visit)
                if r == "guest" and self.needs_load and fake._visit == self.visit_at_enable[r]:
                    continue                       # no NetSyncClient polls a Netsync-off boot: only a field load reads it
                c = cfg[r]
                self.say(r, "config", f"[NetSync] config enabled=True role={c['Role']} field={fake.field_id} "
                                      f"relay={c['RelayUrl']} code={c['SessionCode']}")
                self.say(r, "relay", f"[NetSync] relay connected {c['RelayUrl']}/sess/{c['SessionCode']}?role="
                                     f"{'host' if c['Role'] == 'host' else 'guest'}")
            if all("relay" in self.said[r] for r in self.roots) and self.guest_pairs:
                fld = self.fakes["host"].field_id
                self.say("guest", "paired", f"[NetSync] paired on the host's field ({fld}) -- reloading it once so the "
                                            f"state mirror arms")
                self.say("host", "ghost", f"[NetSync] ghost spawned as vivi on field {fld} (ui=FieldHUD)")
                self.say("guest", "ghost", f"[NetSync] ghost spawned as zidane on field {fld} (ui=FieldHUD)")
                self.say("guest", "armed", "[NetSync] state-mirror ARMED -- this guest's fields now stage the HOST's "
                                           "story")
                self.fakes["guest"].story_bytes[D.MARKER_BYTE] = self.fakes["host"].story_bytes[D.MARKER_BYTE]
            time.sleep(0.05)


@pytest.fixture
def duo_env(tmp_path):
    install = make_install(tmp_path / "steam")
    roots = {r: tmp_path / "inst" / r for r in D.ROLES}
    insts = {r: I.Instance(p, install=install, label=r, procs=lambda: [], log=lambda m: None) for r, p in roots.items()}
    for i in insts.values():
        i.build()
        (i.root / "Memoria.log").write_text(f"{stamp()} |I| boot\n", encoding="utf-8")
    fakes = {r: FakeGame(p) for r, p in roots.items()}

    def factory(role, inst, run_dir, label):
        return Session(label=label, instance=inst, run_dir=run_dir, save_dir=tmp_path / "saves",
                       launcher=lambda exe: fakes[role].start(), boot_timeout=15.0, verbose=False)

    def make(**kw):
        kw.setdefault("procs", False)
        kw.setdefault("verbose", False)
        kw.setdefault("config_wait", 1.0)
        return D.Duo(label="t", instances=insts, session_factory=factory, run_dir=tmp_path / "duo", field=30810, **kw)
    return {"install": install, "roots": roots, "insts": insts, "fakes": fakes, "make": make, "tmp": tmp_path}


def boot_fast(monkeypatch):
    """New Game with no 10 s title settle (a stand-in has nothing to settle)."""
    orig = Session.newgame
    monkeypatch.setattr(Session, "newgame", lambda self, **kw: orig(self, **{**kw, "settle": 0}))


# ------------------------------------------------------------------------------------------- the pure parts


def test_the_duo_matchers_are_the_t2_benchs_verbatim():
    """duo.MATCHERS are copies; _coop_peer_bench's self-check pins ITS regexes to the engine's C#. Drift = red here."""
    sys.path.insert(0, str(REPO / "studies" / "test-harness" / "scenarios"))
    pb = pytest.importorskip("_coop_peer_bench")
    for name, rx in D.MATCHERS.items():
        assert name in pb.MATCHERS, name
        assert rx.pattern == pb.MATCHERS[name].pattern, name


def test_fresh_codes_have_the_engine_shape_and_differ():
    codes = {D.fresh_code() for _ in range(50)}
    assert len(codes) == 50
    assert all(re.fullmatch(r"ff9-DUO[A-Z0-9]{5}", c) and len(c) == len("ff9-") + 8 for c in codes)


@needs_junctions
def test_role_values_put_the_guest_on_role_client_and_the_right_port(duo_env):
    d = duo_env["make"](code="ff9-DUOTEST1")
    assert d.role_values("guest")["Role"] == "client" and d.role_values("host")["Role"] == "host"
    assert d.role_values("host")["RelayUrl"] == "ws://127.0.0.1:49211"
    assert d.role_values("guest")["RelayUrl"] == "ws://127.0.0.1:49212"
    r = duo_env["make"](code="ff9-DUOTEST1", topology="relay")
    assert {r.role_values(x)["RelayUrl"] for x in D.ROLES} == {"ws://127.0.0.1:7787"}
    assert all(v["SessionCode"] == "ff9-DUOTEST1" for v in map(d.role_values, D.ROLES))


def test_a_scenarios_role_extra_rides_its_roles_ini_and_never_the_duos_own_keys(duo_env):
    """[ff9mapkit netsync s139] ``pair(role_extra=...)`` (coop_dress_wire.py's host GhostAs / GuestSlots): a scenario's own
    [Netsync] keys join THAT role's values on top of ROLE_VALUES; the keys the duo owns (Role, RelayUrl, SessionCode) are
    refused BEFORE anything is written -- a scenario can never turn the guest into the selftest role or off the relay."""
    d = duo_env["make"](code="ff9-DUOTEST1")
    d.role_extra = {"host": {"GhostAs": "auto", "GuestSlots": "2"}}
    host, guest = d.role_values("host"), d.role_values("guest")
    assert (host["GhostAs"], host["GuestSlots"], host["Role"]) == ("auto", "2", "host")
    assert "GhostAs" not in guest and guest["Role"] == "client"
    for key in ("Role", "RelayUrl", "SessionCode"):
        d.role_extra = {"guest": {key: "x"}}
        with pytest.raises(HarnessError, match="the duo owns those keys"):
            d.role_values("guest")
    d.role_extra = {}
    with pytest.raises(HarnessError, match="the duo owns those keys"):
        d.pair(role_extra={"guest": {"Role": "guest"}})        # refused before any New Game or ini write
    assert not d.ini_backups


def test_a_live_netsync_edit_rewrites_the_roles_ini_and_waits_for_the_engines_echo(duo_env, tmp_path):
    """[ff9mapkit netsync s139] ``Duo.set_netsync`` (coop_dress_wire.py steps the host's GuestSlots 2 -> 4 -> 0 on a live
    pair): the edit folds into the role's scenario keys and the role's WHOLE [Netsync] is rewritten -- the same Role,
    RelayUrl and SessionCode (the transport signature unchanged: the session survives), the edited key new; it returns the
    engine's echo, a config line on this role's URL and code logged AFTER the write that the caller's match accepts (an
    older line, another code or a line the match rejects is not one: [] at the timeout); the keys the duo owns are refused
    before anything is written."""
    d = duo_env["make"](code="ff9-DUOTEST1")
    d.role_extra = {"host": {"GhostAs": "auto", "GuestSlots": "2"}}
    log = tmp_path / "host-Memoria.log"
    url = d.role_values("host")["RelayUrl"]
    log.write_text(f"{stamp()} |I| [NetSync] config enabled=True role=host field=0 guestSlots=4 ghostAs=auto "
                   f"relay={url} code=ff9-DUOTEST1\n", encoding="utf-8")      # an OLDER line, before the write
    d.logs = {"host": D.EngineLog(log)}
    time.sleep(1.1)                                                          # engine stamps are whole seconds
    written = []

    class Inst:
        def netsync(self, vals, *, backup_to=None):
            written.append(dict(vals))
            slots = int(vals.get("GuestSlots", "0"))
            with open(log, "a", encoding="utf-8") as f:                       # the engine's echo of the new values
                f.write(f"{stamp()} |I| [NetSync] config enabled=True role=host field=0"
                        + (f" guestSlots={slots}" if slots else "") + f" ghostAs={vals.get('GhostAs', '')} "
                        f"relay={vals['RelayUrl']} code={vals['SessionCode']}\n")
            return None
    d.instances = dict(d.instances, host=Inst())

    def slots_of(m):
        hit = re.search(r"\bguestSlots=(\d+)", m.group(4) or "")
        return int(hit.group(1)) if hit else 0
    got = d.set_netsync("host", {"GuestSlots": 4}, timeout=2.0, pred=lambda m: slots_of(m) == 4)
    assert len(got) == 1 and "guestSlots=4" in got[0][1], got                 # the NEW echo only, never the older line
    assert written[-1]["GuestSlots"] == "4" and written[-1]["GhostAs"] == "auto"
    assert (written[-1]["Role"], written[-1]["RelayUrl"], written[-1]["SessionCode"]) == ("host", url, "ff9-DUOTEST1")
    assert d.role_extra["host"] == {"GhostAs": "auto", "GuestSlots": "4"}
    got = d.set_netsync("host", {"GuestSlots": 0}, timeout=2.0, pred=lambda m: slots_of(m) == 0)
    assert len(got) == 1 and "guestSlots" not in got[0][1] and written[-1]["GuestSlots"] == "0"
    t0 = time.time()
    assert d.set_netsync("host", {"GuestSlots": 2}, timeout=0.6, pred=lambda m: slots_of(m) == 5) == []
    assert time.time() - t0 >= 0.5                                           # the match rejected every line: the timeout
    n = len(written)
    for key in ("Role", "RelayUrl", "SessionCode"):
        with pytest.raises(HarnessError, match="the duo owns those keys"):
            d.set_netsync("host", {key: "x"}, timeout=0.1)
    assert len(written) == n, "a refused edit writes nothing"


# ------------------------------------------------------------------------------------------- the laws refuse first


@needs_junctions
def test_the_same_root_twice_is_refused(duo_env):
    i = duo_env["insts"]["host"]
    with pytest.raises(HarnessError, match="same root"):
        D.Duo(instances={"host": i, "guest": I.Instance(i.root, install=duo_env["install"])}, procs=False)


@needs_junctions
def test_the_owners_live_code_and_port_are_refused_before_anything_starts(duo_env, monkeypatch):
    started = []
    monkeypatch.setattr(D.ToolProc, "start", lambda self: started.append(self.name) or self)
    with pytest.raises(HarnessError, match="owner's live one"):
        with duo_env["make"](code="ff9-OWNERLIV"):
            pass
    with pytest.raises(HarnessError, match="PRIVATE ports"):
        with duo_env["make"](procs=True, bridge_ports={"host": 49201, "guest": 49212}):
            pass
    assert started == [], "no relay or bridge may start before the laws pass"
    assert all(duo_env["fakes"][r]._thread is None for r in D.ROLES), "nor a game"


# ------------------------------------------------------------------------------------------- the recipe, end to end


@needs_junctions
def test_a_duo_pairs_two_fakegames_through_their_own_inis(duo_env, monkeypatch):
    boot_fast(monkeypatch)
    eng = FakeEngine(duo_env["roots"], duo_env["fakes"])
    eng.start()
    owner = (duo_env["install"] / "Memoria.ini").read_bytes()
    try:
        with duo_env["make"](code="ff9-DUOTEST1") as d:
            d.pair()
            d.expect_mirror(cid="C7")
            d.expect_parity("both on the bench field", lambda s: s.field_id, want=30810, cid="P")
            # the root inis carry the roles WHILE the duo runs
            for r, want in (("host", "Role = host"), ("guest", "Role = client")):
                assert want in (duo_env["roots"][r] / "Memoria.ini").read_text(encoding="utf-8")
            guest_session = d.guest
    finally:
        eng.stop.set()
    ids = [c["id"] for c in d.checks]
    assert ids == ["C2-host", "C2-guest", "C3-host", "C3-guest", "C4", "C5-host", "C5-guest", "C6", "C7", "P"]
    assert d.passed
    rows = [json.loads(ln) for ln in (duo_env["tmp"] / "duo" / "guest" / "steps.jsonl").read_text(
        encoding="utf-8").splitlines() if ln.strip()]
    warps = [r["steps"][0] for r in rows if r.get("steps") and r["steps"][0].startswith("warp ")]
    assert [w for w in warps if w.startswith("warp 30810")] == warps and len(warps) == 2, \
        f"the guest's config needed exactly ONE same-field warp after its bench warp: {warps}"
    # every duo check is on the Session it concerns (both, for a both-game check)
    assert any(c["what"].startswith("[duo] the guest paired") for c in guest_session.checks)
    rep = json.loads((duo_env["tmp"] / "duo" / "duo.json").read_text(encoding="utf-8"))
    assert rep["verdict"] == "pass" and rep["code"] == "ff9-DUOTEST1" and rep["paired"] is True
    assert rep["roots_verify_after"] == {"host": [], "guest": []}, "both inis back to install + overlay"
    assert (duo_env["install"] / "Memoria.ini").read_bytes() == owner, "the install's ini is never written"
    assert sorted(p.name.split("-Memoria")[0] for p in (duo_env["tmp"] / "duo" / "ini").iterdir()) == ["guest", "host"]
    for r in D.ROLES:
        assert (duo_env["tmp"] / "duo" / r / "report.json").is_file()
        assert (duo_env["tmp"] / "duo" / r / "Memoria.log").is_file(), "each Session archived its own log"


@needs_junctions
def test_a_strict_red_stops_the_duo_and_still_cleans_up(duo_env, monkeypatch):
    boot_fast(monkeypatch)
    eng = FakeEngine(duo_env["roots"], duo_env["fakes"], guest_pairs=False)      # the guest never pairs
    eng.start()
    monkeypatch.setattr(D.Duo, "wait_line", _short_waits(D.Duo.wait_line))
    try:
        with pytest.raises(D.DuoRed, match="C4"):
            with duo_env["make"](code="ff9-DUOTEST2") as d:
                d.pair()
    finally:
        eng.stop.set()
    assert [c["id"] for c in d.checks if not c["ok"]] == ["C4"]
    rep = json.loads((duo_env["tmp"] / "duo" / "duo.json").read_text(encoding="utf-8"))
    assert rep["verdict"] == "fail" and rep["raised"] is True
    assert rep["roots_verify_after"] == {"host": [], "guest": []}
    for r in D.ROLES:
        assert not (duo_env["roots"][r] / "x64" / "ff9harness" / "arm").exists()
        assert not (duo_env["roots"][r] / I.CLAIM).exists()


def _short_waits(orig):
    def wait_line(self, role, name, timeout, **kw):
        return orig(self, role, name, min(timeout, 3.0), **kw)
    return wait_line


@needs_junctions
def test_expect_line_reads_each_games_own_log_and_windows_by_time(duo_env, monkeypatch):
    boot_fast(monkeypatch)
    with duo_env["make"](code="ff9-DUOTEST3", strict=False) as d:
        at = _dt.datetime.now()
        with open(duo_env["roots"]["guest"] / "Memoria.log", "a", encoding="utf-8") as f:
            f.write(f"{stamp()} |I| [NetSync] diorama BOOT scene=67 pattern=0 start=normal intro=play swirl=1 "
                    f"clamp=none\n")
        assert d.expect_line("guest", "boot", "guest boots", timeout=2.0, after=at, pred=lambda m: m.group(1) == "67")
        assert not d.expect_line("host", "boot", "the host never boots a diorama", timeout=0.5)
        later = _dt.datetime.now() + _dt.timedelta(seconds=2)
        assert not d.wait_line("guest", "boot", 0.3, after=later), "a window after the line excludes it"
    assert [c["ok"] for c in d.checks] == [True, False]


# ------------------------------------------------------------------------------------------- the helper processes


def test_toolproc_runs_a_real_coop_peer_relay_and_stops_it_cleanly(tmp_path):
    port = _free_port()
    p = D.ToolProc("relay", D.COOP_PEER, ["relay", "--port", port, "--status", "0"], log_path=tmp_path / "relay.log",
                   out_path=tmp_path / "relay.out").start()
    try:
        line = p.wait_for(r"relay listening on ws://127\.0\.0\.1:(\d+)", 20.0)
        assert line and str(port) in line, p.tail()
        assert D.wait_bound(port, 5.0)
    finally:
        how = p.stop()
    assert how.startswith("stopped cleanly") or "had exited" in how, how
    assert D.port_free(port)


def test_toolproc_stops_a_real_bridge_cleanly(tmp_path):
    """The bridge's main thread used to sit in a bare join(), which never hears CTRL_BREAK on Windows: a duo's stop
    TERMINATED both bridges (sitting log: no 'stopped' line). Joined in slices it takes its own clean path."""
    port = _free_port()
    p = D.ToolProc("bridge", D.BRIDGE, ["--port", port, "--relay", "ws://127.0.0.1:9"], log_path=tmp_path / "b.log",
                   out_path=tmp_path / "b.out").start()
    try:
        assert D.wait_bound(port, 20.0, alive=p.alive), p.tail()
    finally:
        how = p.stop()
    assert how.startswith("stopped cleanly"), how
    assert "stopped" in p.text()


def _free_port() -> int:
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port
