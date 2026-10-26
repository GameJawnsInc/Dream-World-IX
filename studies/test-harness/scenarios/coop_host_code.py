"""s154 -- THE OWN-CODE LAW, the SOLO bench (studies/coop-review/REVIEW.md appendix 25; a KIT fix: no engine hunk).

One instance root, harness-driven, unattended, plus bench peers (tools/harness/coop_peer.py: a local relay and fake guest
clients) -- no second game. The DLL is the same in both runs; the calibration axis is the KIT. Before s154 one ini key,
[Netsync] SessionCode, meant both "the code the engine dials" (a guest's FRIEND's code after `coop join`) and "this PC's own
host code", so a PC that had joined a friend and then hosted published the friend's invite as its own session: anyone
holding that invite walked into its game. The kit now keeps the own code in HostSessionCode (ff9mapkit.coop.own_host_code).

The kit runs as a SUBPROCESS through a stub (:data:`STUB`), never in this process: the stub pins the kit directory on
sys.path, asserts the package it imported IS that kit and that the kit is the one this run expects (behaviourally:
``hasattr(coop, 'own_host_code')`` False for the calibration kit, True otherwise), asserts ``config.find_game_path(root)``
resolves to the ROOT (never the install, never a fall-through: FF9_GAME_PATH is removed from its environment and never
set), disables the clipboard, and hard-wires ``--no-room --no-bridge --port <private>`` onto every call (NOTHING POINTS AT
A ROOT: ensure_room would deploy THROUGH the root's junctions into the real install's mod folders). A stub that cannot
vouch for any of that exits 97 and the run is VOID, never a false red or green.

  H0     the instance root, the kit pin and the root guard; the root's ini reads co-op off
  H1     precondition: `coop join FF9-HCJOINED` lands (the engine's config line role=client code=FF9-HCJOINED, warped
         unconditionally: a root booted co-op-off creates the client at a field load), then `coop off` lands
  H2     a FORMER GUEST's `coop host` (no code, no --new-code): the engine's own `config ... role=host ... code=<C>` line
         and the relay's `relay session <C>: host joined` say C is NOT the invite. RED on the s153 kit: C == FF9-HCJOINED
  H3     the consequence: a stranger holding the old invite (a fake guest on FF9-HCJOINED) gets no ghost into this game
         and the relay never pairs FF9-HCJOINED. RED on the s153 kit: it pairs and its ghost appears in the host's field
  H4     the instrument's positive control: a fake guest on C builds a ghost (netsync.session.ghost and ghost_held read
         false right before it starts, then a false-to-true edge) -- VOID otherwise, and an H4 failure VOIDS H3 (an
         instrument that cannot show a ghost cannot show a stranger's either)
  H2g-pre the GUI leg's precondition: join + off again (a fresh relay port, so no leg of the CLI half lingers)
  H2g    the Workspace's own path (the one the tutorial uses, fixed by a DIFFERENT edit: start_coop no longer forwards the
         field): the stub builds the real CoopDoc offscreen (find_game_path patched to the root INSIDE the stub process),
         presses Start hosting on the switched-off former-guest ini, captures the argv its run_job would get, and runs
         that argv through the same stub. Judged on the same engine + relay observables as H2. RED on the s153 kit: its
         argv is `coop host FF9-HCJOINED` (the Host field was seeded from SessionCode)
  H2g-ran the Workspace leg's INSTRUMENT, split out of H2g (:func:`host_verdict`): the stub exited 0, not VOID, with a
         captured coop argv; the engine's role=host config line on PORT_B named a code, the relay registered the host
         under it, and the root ini's SessionCode agrees. GREEN ON BOTH KITS and never predicted: H2g has no downstream
         control (H4 corroborates H2, nothing corroborates H2g), so before the split a VOID stub, a crash, a timeout or a
         dead relay B made H2g red exactly as the s153 leak does and HC-CAL read it as calibrated. Now each is an
         unpredicted red, and every early exit of the GUI half unreaches both rows (:func:`gui_leg_unreached`)
  HC-CAL COOP_CALIBRATE=1 only: exactly :data:`PREDICTED_S153` went red

THE TWO RUNS (the lead's, both on the s153 DLL, one change per in-game test):

    py tools/harness/instance.py ensure C:\\gd\\ff9-inst\\host
    $env:COOP_CALIBRATE = "1"
    py tools/play.py studies/test-harness/scenarios/coop_host_code.py --instance C:\\gd\\ff9-inst\\host
    Remove-Item Env:COOP_CALIBRATE
    py tools/play.py studies/test-harness/scenarios/coop_host_code.py --instance C:\\gd\\ff9-inst\\host

COOP_CALIBRATE=1 materializes the s153-era kit by ``git archive 8ad20a11 ff9mapkit/ff9mapkit`` into the run dir (no
shared worktree; the archive is by commit, so the main repo's checkout does not matter); COOP_HOSTCODE_KIT=<dir holding
the ff9mapkit package> overrides the kit either way.

THE PREREQS: the root ensured (its base_overlay parks HostSessionCode; the Session also refreshes it at launch), LOCKT2
(30602) registered, no other FF9 from that root, ports 49245 + 49246 free, no controller, nobody at the keyboard.

OFFLINE: ``py studies/test-harness/scenarios/coop_host_code.py --selfcheck`` runs the stub (both kits, CLI and GUI legs)
against a throwaway fake root -- no game, no relay -- and checks the KIT half of the verdicts: the s153 kit publishes the
invite, this kit does not. It also drives the shipped H2g / H2g-ran split (:func:`record_host`, :func:`gui_leg_unreached`)
through the shipped calibration judge: the real s153 leak calibrates, and a VOID stub, a crash, a timeout, a missing
registration or argv, a disagreeing ini, a dead relay B and a mid-leg exception each fail HC-CAL. It calibrates the stub
and the judge; it is not the in-game proof.
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - PeerProc (coop_peer as a subprocess), port_free

REPO = HERE.parents[2]
JOINED = "FF9-HCJOINED"            # the invite this PC "joined" with (GenerateSessionCode's ff9- + 8 shape)
PORT_A = 49245                     # the CLI half's private relay port: never the owner's 49200 / 49201
PORT_B = 49246                     # the GUI half's (a fresh relay: no leg of the CLI half can linger in it)
CAL_SHA = "8ad20a11"               # the s153-era kit (the s153 merge)
VOID_RC = 97                       # the stub's "cannot vouch for this run" exit
SAMPLE_S = 12.0                    # H3 / H4 windows
CLEAR_S = 12.0                     # the stranger's ghost clears: the s56 ghost hold is 5 s

CATALOG = {
    "H0": "an instance-root run; the kit pinned (path + identity) and the root guarded (find_game_path(root) == root, "
          "not the install); the root's Memoria.ini reads co-op off",
    "H1": "precondition: `coop join FF9-HCJOINED` lands (config role=client code=FF9-HCJOINED, netsync.role client), "
          "then `coop off` lands (applied live, disabled)",
    "H2": "a former guest's `coop host` publishes ITS OWN code: the engine's config line and the relay's registration "
          "name a code C != FF9-HCJOINED",
    "H3": "a stranger holding the old invite gets no ghost into this host's game and is never paired (12 s)",
    "H4": "positive control: a fake guest on the host's own code C builds a ghost (a false-to-true edge from a clean start)",
    "H2g-pre": "precondition: join + off land again before the Workspace leg",
    "H2g": "the Workspace's Start hosting on a switched-off former-guest ini publishes its own code (the captured argv run "
           "through the stub: config line + relay registration name C' != FF9-HCJOINED)",
    "H2g-ran": "instrument: the Workspace leg ran -- the stub exited 0, not VOID, with a captured coop argv; the engine's "
               "role=host config line on PORT_B and the relay's host registration under that code were seen; the root "
               "ini's SessionCode equals it (green on BOTH kits)",
}
#: The checks the s153-era kit (8ad20a11) must turn red, by behaviour: the host publishes the invite (H2, H2g) and the
#: stranger walks in (H3). H0, H1, H2g-pre, H4 and H2g-ran are preconditions / controls / the instrument: green on both
#: kits, so a red there is an UNPREDICTED red and fails HC-CAL (H4 voids H3; H2g-ran voids H2g).
PREDICTED_S153 = ("H2", "H2g", "H3")
#: The GUI half's rows: every early exit of that half unreaches BOTH, so a leg that never ran is never read as the leak.
H2G_LEG = ("H2g", "H2g-ran")

STUB = r'''
import json, os, sys
from pathlib import Path
kit, root, install, mode, expect, port = sys.argv[1:7]
argv = sys.argv[7:]
sys.path.insert(0, kit)
import ff9mapkit
import ff9mapkit.coop as coop
import ff9mapkit.config as config
def void(why):
    print("STUB VOID " + why, flush=True)
    sys.exit(97)
where = Path(ff9mapkit.__file__).resolve()
print("STUB KIT " + str(where), flush=True)
if not where.is_relative_to(Path(kit).resolve()):
    void("the ff9mapkit imported is not the pinned kit's: " + str(where))
has = hasattr(coop, "own_host_code")
print("STUB OWN_HOST_CODE " + str(has), flush=True)
if has != (expect == "new"):
    void("expected the " + expect + " kit, but own_host_code is " + ("present" if has else "absent"))
def same(a, b):
    return os.path.normcase(os.path.realpath(str(a))) == os.path.normcase(os.path.realpath(str(b)))
rootp = Path(root).resolve()
got = config.find_game_path(root)
if not same(got, rootp):
    void("find_game_path(%r) resolved %s, not the root" % (root, got))
if same(rootp, install):
    void("the root IS the install: " + str(rootp))
if not (rootp / "Memoria.ini").is_file():
    void("the root has no Memoria.ini: " + str(rootp))
coop._copy_clipboard = lambda _t: False
tail = ["--no-room", "--no-bridge", "--port", port]
if mode == "gui":
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    config.find_game_path = lambda *_a, **_k: rootp      # refresh_status imports it at call time; never FF9_GAME_PATH
    from ff9mapkit.editor import theme
    from ff9mapkit.workspace.coopdoc import CoopDoc
    seen = []
    doc = CoopDoc(theme.derive(dict(theme.THEMES["mist"])), kit, run=lambda a, **kw: seen.append(list(a)) or True)
    doc._poll.stop()
    doc.rb_relay.setChecked(True)
    doc.rb_host.setChecked(True)
    print("STUB FIELD " + json.dumps(doc.code.text()), flush=True)
    doc.start_coop()
    if not seen:
        void("Start hosting spawned nothing: " + doc.lbl_session.text())
    print("STUB ARGV " + json.dumps(seen[-1][1:]), flush=True)
    if seen[-1][1:4] != ["-m", "ff9mapkit", "coop"]:
        void("not a coop argv: " + json.dumps(seen[-1]))
    argv = seen[-1][4:]
from ff9mapkit import cli
full = ["--game", root, "coop", *argv, *tail]
print("STUB RUN " + json.dumps(full), flush=True)
sys.stdout.flush()
sys.exit(cli.main(full))
'''


# ---------------------------------------------------------------------------------------------- the kit under test
class KitRun:
    """One stub call: its exit code, its stdout lines, and the parsed STUB/kit facts."""

    def __init__(self, rc: int, out: str):
        self.rc = rc
        self.lines = out.splitlines()

    def fact(self, tag: str):
        for ln in self.lines:
            if ln.startswith(f"STUB {tag} "):
                return ln[len(f"STUB {tag} "):]
        return None

    @property
    def void(self):
        return self.fact("VOID") if self.rc == VOID_RC or self.fact("VOID") else None

    @property
    def install_line(self):
        hit = [ln for ln in self.lines if ln.startswith("FF9 install: ")]
        return hit[0][len("FF9 install: "):] if hit else None

    def tail(self, n: int = 8) -> str:
        return " | ".join(ln.strip() for ln in self.lines[-n:])[:700]


def kit_env(mode: str) -> dict:
    env = dict(os.environ)
    env.pop("FF9_GAME_PATH", None)                # NOTHING POINTS AT A ROOT -- and nothing points the kit anywhere else
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if mode == "gui":
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["FF9MAPKIT_NO_THUMBS"] = "1"
    return env


def kit_call(kit: Path, root: Path, install: Path, mode: str, expect: str, port: int, *argv: str,
             timeout: float = 240.0) -> KitRun:
    """Run the KIT through :data:`STUB` as a subprocess (cwd = the kit). ``mode`` cli | gui; ``expect`` old | new."""
    cmd = [sys.executable, "-c", STUB, str(kit), str(root), str(install), mode, expect, str(port), *argv]
    try:
        p = subprocess.run(cmd, cwd=str(kit), env=kit_env(mode), capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as err:
        return KitRun(-1, f"STUB VOID the kit call timed out after {timeout:g} s\n" + (err.stdout or b"").decode(
            "utf-8", "replace"))
    text = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
    return KitRun(p.returncode, text)


def materialize_cal_kit(dest: Path) -> Path:
    """``git archive <CAL_SHA> ff9mapkit/ff9mapkit`` (the package alone) extracted under ``dest`` -- no shared worktree,
    and by COMMIT, so no checkout's state matters (the object store is the main repo's). Returns the kit dir (the one
    holding the ``ff9mapkit`` package)."""
    proc = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", CAL_SHA, "ff9mapkit/ff9mapkit"],
                          capture_output=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"git archive {CAL_SHA} failed: {proc.stderr.decode('utf-8', 'replace')[:300]}")
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
        try:
            tar.extractall(dest, filter="data")
        except TypeError:                          # a Python without extraction filters
            tar.extractall(dest)
    return dest / "ff9mapkit"


def pick_kit(run_dir: Path, calibrate: bool) -> tuple:
    """(kit dir, expect, provenance text)."""
    override = os.environ.get("COOP_HOSTCODE_KIT", "").strip()
    expect = "old" if calibrate else "new"
    if override:
        return Path(override), expect, f"COOP_HOSTCODE_KIT={override}"
    if calibrate:
        return materialize_cal_kit(run_dir / f"kit-{CAL_SHA}"), expect, f"git archive {CAL_SHA} ff9mapkit/ff9mapkit"
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "ff9mapkit"],
                           capture_output=True, text=True).stdout.strip().splitlines()
    return REPO / "ff9mapkit", expect, f"this worktree's kit at {head[:10]} ({len(dirty)} uncommitted path(s))"


def ini_keys(root: Path) -> dict:
    """The root's [Netsync] keys the verdicts note (last key wins, BOM-safe) -- read with the harness's own kit copy."""
    from ff9mapkit.coop import read_ini_key, read_ini_text
    try:
        text = read_ini_text(Path(root) / "Memoria.ini")
    except OSError:
        return {}
    return {k: read_ini_key(text, "Netsync", k) for k in ("Enabled", "Role", "SessionCode", "HostSessionCode",
                                                          "RelayUrl")}


# ---------------------------------------------------------------------------------------------- the engine's lines
CFG = re.compile(r"\[NetSync\] config enabled=True role=(\w+) .*relay=ws://127\.0\.0\.1:(\d+) code=(\S*)")
DISABLED = "[NetSync] config change applied live (disabled)"
REG = re.compile(r"^relay session (\S+): (host|guest) (joined|rejoined|reconnected)")
PAIRED = re.compile(r"^relay session (\S+): (host|guest) paired -- forwarding")


def wait_cfg(g, at: int, role: str, port: int, timeout: float):
    """The newest `config enabled=True role=<role> ... relay=ws://127.0.0.1:<port> code=` line after ``at``:
    (code, lines)."""
    deadline = time.time() + timeout
    while True:
        lines = cb.new(g, at)
        hits = [m for m in (CFG.search(ln) for ln in lines) if m and m.group(1) == role and int(m.group(2)) == port]
        if hits or time.time() >= deadline:
            return (hits[-1].group(3) if hits else None), lines
        time.sleep(0.25)


def ghost(st) -> tuple:
    s = cb.path(st, "netsync.session", {}) or {}
    return bool(s.get("ghost")), bool(s.get("ghost_held"))


# ---------------------------------------------------------------------------------------------- the scenario
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    catalog = dict(CATALOG)
    if calibrate:
        catalog["HC-CAL"] = ("CALIBRATION (the s153-era kit): exactly the predicted checks are red -- "
                             + ", ".join(PREDICTED_S153))
    led = cb.Ledger(g, catalog, finals=("HC-CAL",))
    ctx = {"peers": [], "t0": time.time(), "root": None}
    try:
        _legs(g, led, field, calibrate, ctx)
    finally:
        for peer in ctx["peers"]:
            try:
                g.note(f"{peer.mode} ({peer.log_path.name}): {peer.stop()}")
            except Exception as err:                   # noqa: BLE001 - teardown must not mask the verdicts
                g.note(f"stopping a peer failed: {err}")
        root = ctx["root"]
        if root is not None:
            _park_backups(g, root, ctx["t0"])
        try:
            if g.instance is not None and g.instance.restore_ini():
                g.note("the root's Memoria.ini put back to install + overlay")
        except Exception as err:                       # noqa: BLE001
            g.note(f"restore_ini failed: {err}")
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'host-code')}")
        if calibrate:
            led.close("the run ended before this check was reached")
            led.judge_calibration("HC-CAL", PREDICTED_S153)
        led.close(final=True)


def _park_backups(g, root: Path, t0: float) -> None:
    """The kit's `Memoria.ini.coop-bak-*` snapshots of THIS run, moved out of the root into the run dir."""
    dest = Path(g.run_dir) / "ini"
    moved = 0
    for bak in Path(root).glob("Memoria.ini.coop-bak-*"):
        try:
            if bak.stat().st_mtime >= t0 - 2.0:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.move(str(bak), str(dest / bak.name))
                moved += 1
        except OSError as err:
            g.note(f"could not move {bak.name}: {err}")
    if moved:
        g.note(f"{moved} kit ini backup(s) moved to {dest}")


def _legs(g, led, field, calibrate, ctx):
    rest = list(CATALOG)
    if g.instance is None:
        led.unreached(rest, "not an instance-root run: every leg writes the ROOT's Memoria.ini through the kit")
        return
    root, install = Path(g.instance.root), Path(g.instance.install)
    from harness.instance import _same_path
    if _same_path(root, install):
        led.unreached(rest, f"the root {root} IS the install -- refusing to run the kit against it")
        return
    ctx["root"] = root
    run_dir = Path(g.run_dir)
    try:
        kit, expect, prov = pick_kit(run_dir, calibrate)
    except Exception as err:                           # noqa: BLE001 - no kit, no run
        led.unreached(rest, f"VOID: the kit under test could not be materialized: {str(err)[:300]}")
        return
    g.note(f"the kit under test: {kit} -- {prov}; expected {'WITHOUT' if expect == 'old' else 'WITH'} own_host_code")
    log = run_dir / "kit-calls.log"

    def kit_cli(port, *argv, mode="cli"):
        r = kit_call(kit, root, install, mode, expect, port, *argv)
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"=== {mode} {' '.join(argv)} (port {port}) -> rc {r.rc}\n" + "\n".join(r.lines) + "\n")
        return r

    # ---- H0: the pin, the guard, the root's starting state
    probe = kit_cli(PORT_A, "show")
    keys0 = ini_keys(root)
    named_root = probe.install_line is not None and _same_path(probe.install_line, root)
    ok0 = probe.rc == 0 and not probe.void and named_root and (keys0.get("Enabled") or "0").strip() != "1"
    led.check("H0", ok0, f"stub: {probe.void or 'pinned'}; KIT {probe.fact('KIT')}; own_host_code "
                         f"{probe.fact('OWN_HOST_CODE')}; 'FF9 install:' {probe.install_line!r}; root ini {keys0}")
    if not ok0:
        led.unreached(rest, "VOID: the kit pin / root guard / starting state did not hold (H0)")
        return
    for p in (PORT_A, PORT_B):
        free, why = pb.port_free(p)
        if not free:
            led.unreached(rest, why)
            return
    g.newgame()
    if g.state.field_id != field:
        g.warp(field)
    try:
        g.no_encounters(True)
    except (cb.HarnessError, AttributeError) as err:
        g.note(f"noencounter refused ({str(err)[:120]}) -- a random battle may interrupt a leg")
    g.wait_frames(45)

    # ---- H1: the PC joins a friend (no relay up yet: its guest dial just fails), then turns co-op off
    if not _join_then_off(g, led, "H1", kit_cli, PORT_A, field):
        led.unreached(rest, "the join/off precondition did not land (H1)")
        return

    # ---- the CLI half's relay: started only now, so no H1 guest leg can sit in FF9-HCJOINED's guest slot
    relay = pb.PeerProc("relay", ["--port", PORT_A, "--pair-wait", 900, "--status", 0],
                        log_path=run_dir / "relay-a.log", out_path=run_dir / "relay-a.out")
    ctx["peers"].append(relay)
    relay.start()
    if relay.wait_for(r"^relay listening", 15.0) is None:
        led.unreached(rest, f"the bench relay on {PORT_A} never listened: {relay.tail()}")
        return

    # ---- H2: a former guest hosts (no code, no --new-code) -- exactly the s153 hole
    c, h2_ok = _host_and_judge(g, led, "H2", kit_cli, relay, PORT_A, field, gui=False)
    if not c:
        led.unreached(["H3", "H4"], "H2 found no host code to aim the guests at")
    else:
        h3_ok, h3_why = _stranger(g, relay, PORT_A, run_dir, ctx)
        h4_ok, h4_why = _control(g, PORT_A, run_dir, ctx, c)
        led.check("H4", h4_ok, h4_why)
        led.check("H3", h3_ok and h4_ok, h3_why if h4_ok else f"VOID: the positive control failed ({h4_why[:200]}) -- "
                                                               f"an instrument that cannot show a ghost cannot show "
                                                               f"the stranger's; raw H3: {h3_why}")
    at = cb.mark(g)
    off = kit_cli(PORT_A, "off")
    cb.wait_log(g, at, DISABLED, timeout=8.0)
    g.note(f"CLI half done: `coop off` rc {off.rc}; relay A: {relay.stop()}")

    # ---- H2g-pre + H2g: the Workspace's path, on a fresh relay port
    if not _join_then_off(g, led, "H2g-pre", kit_cli, PORT_B, field):
        gui_leg_unreached(led, "the join/off precondition did not land again (H2g-pre)")
        return
    relay_b = pb.PeerProc("relay", ["--port", PORT_B, "--pair-wait", 900, "--status", 0],
                          log_path=run_dir / "relay-b.log", out_path=run_dir / "relay-b.out")
    ctx["peers"].append(relay_b)
    relay_b.start()
    if relay_b.wait_for(r"^relay listening", 15.0) is None:
        gui_leg_unreached(led, f"the bench relay on {PORT_B} never listened: {relay_b.tail()}")
        return
    c2, _ = _host_and_judge(g, led, "H2g", kit_cli, relay_b, PORT_B, field, gui=True)
    if c and c2:
        same = "the same own code" if c == c2 else "DIFFERENT"
        g.note(f"the CLI half hosted on {c}, the Workspace half on {c2} ({same})")
    at = cb.mark(g)
    kit_cli(PORT_B, "off")
    cb.wait_log(g, at, DISABLED, timeout=8.0)


def _join_then_off(g, led, cid, kit_cli, port, field) -> bool:
    at = cb.mark(g)
    j = kit_cli(port, "join", JOINED)
    g.warp(g.state.field_id or field)                  # unconditional: a co-op-off root creates its client at a field load
    code, lines = wait_cfg(g, at, "client", port, 15.0)
    st = cb.poll(g, lambda s: (s.netsync or {}).get("role") == "client", 6.0, "netsync.role client")
    role = ((st or g.state).netsync or {}).get("role")
    at2 = cb.mark(g)
    o = kit_cli(port, "off")
    off_lines = cb.wait_log(g, at2, DISABLED, timeout=10.0)
    ok = (j.rc == 0 and not j.void and code is not None and code.upper() == JOINED and role == "client"
          and o.rc == 0 and cb.count(off_lines, DISABLED) >= 1)
    led.check(cid, ok, f"join rc {j.rc} {j.void or ''}; config code {code!r}; netsync.role {role!r}; off rc {o.rc}, "
                       f"disabled lines {cb.count(off_lines, DISABLED)}; "
                       + cb.grep(lines, "[NetSync] config", "relay connect", limit=300))
    return ok


def _host_and_judge(g, led, cid, kit_cli, relay, port, field, *, gui: bool):
    """`coop host` (CLI) or the Workspace's Start hosting (GUI) -> (C, ok): the engine's config line, the relay's own
    registration under C, and the root ini's SessionCode == C. Green iff C is not the invite."""
    at = cb.mark(g)
    started = time.time()
    r = kit_cli(port, "host", mode="gui") if gui else kit_cli(port, "host")
    g.warp(g.state.field_id or field)                  # unconditional (a live apply lands too; this makes it a field load)
    c, lines = wait_cfg(g, at, "host", port, 15.0)
    reg = None
    if c:
        deadline = time.time() + 15.0
        while reg is None and time.time() < deadline:
            reg = next((m for _t, _msg, m in relay.find(REG)
                        if m.group(2) == "host" and m.group(1).upper() == c.upper()), None)
            if reg is None:
                time.sleep(0.25)
    keys = ini_keys(g.instance.root)
    return c, record_host(led, cid, r, c, reg, keys, gui=gui, elapsed=time.time() - started)


def host_verdict(r: KitRun, c, reg, keys: dict, *, gui: bool) -> tuple:
    """THE INSTRUMENT / VERDICT SPLIT, pure: ``(ran, ok)`` for one host leg.

    ``ran`` -- the leg's instrument ran: the stub exited 0 and is not VOID (in GUI mode it also captured a coop argv), the
    engine's role=host config line named a code ``c``, the relay registered the host under it (``reg``), and the root
    ini's SessionCode equals it. ``ok`` -- ``ran`` AND ``c`` is not the invite. Only ``ok`` (H2 / H2g) is predicted red on
    s153; ``ran`` (H2g-ran) is green on both kits, so a broken instrument is an UNPREDICTED red and fails HC-CAL."""
    ran = (r.rc == 0 and not r.void and bool(c) and reg is not None and keys.get("SessionCode") == c
           and (not gui or r.fact("ARGV") is not None))
    return ran, bool(ran and c.upper() != JOINED)


def record_host(led, cid: str, r: KitRun, c, reg, keys: dict, *, gui: bool, elapsed: float = 0.0) -> bool:
    """Record a host leg's verdict as ``cid`` (H2 / H2g) and, for the GUI leg, its instrument as H2g-ran -- the call site
    :func:`selfcheck` drives with real and broken stub runs. Returns ``ok``."""
    ran, ok = host_verdict(r, c, reg, keys, gui=gui)
    extra = f"; the Host field read {r.fact('FIELD')}; the captured argv {r.fact('ARGV')}" if gui else ""
    leak = "THE INVITE WAS PUBLISHED AS THIS PC'S SESSION; " if c and c.upper() == JOINED else ""
    said = " | ".join(ln.strip() for ln in r.lines if any(k in ln for k in ("reusing", "adopting", "session code:")))
    detail = (f"kit rc {r.rc} {r.void or ''}{extra}; engine config code {c!r}; relay registered "
              f"{reg.group(0) if reg else None!r}; root ini {keys}; {leak}kit said: {said[:300]} ({elapsed:.1f} s)")
    led.check(cid, ok, ("" if ran else "the leg's instrument did not run" + (" (see H2g-ran)" if gui else "")
                        + " -- not a verdict on the code; ") + detail)
    if gui:
        led.check("H2g-ran", ran, ("the instrument ran; " if ran else "INSTRUMENT RED -- the Workspace leg did not run, "
                                   "so H2g's red is not the s153 leak; ") + detail)
    return ok


def gui_leg_unreached(led, why: str) -> None:
    """Every early exit of the GUI half: BOTH of its rows unreached (:data:`H2G_LEG`) -- H2g alone read as the
    predicted s153 red and let HC-CAL pass on a leg that never ran."""
    led.unreached(H2G_LEG, why)


def _stranger(g, relay, port, run_dir, ctx) -> tuple:
    """H3: a fake guest holding the OLD invite. (ok, detail): ok = no ghost in SAMPLE_S and no FF9-HCJOINED pairing."""
    t_start = _dt.datetime.now()
    peer = pb.PeerProc("fake-guest-client", ["--relay", f"ws://127.0.0.1:{port}", "--code", JOINED],
                       log_path=run_dir / "stranger.log", out_path=run_dir / "stranger.out")
    ctx["peers"].append(peer)
    peer.start()
    seen = {"ghost": False, "held": False}

    def sample(st):
        gh, held = ghost(st)
        seen["ghost"] |= gh
        seen["held"] |= held
    cb.hold_for(g, SAMPLE_S, on_sample=sample)
    paired = [m.group(0) for _t, _msg, m in relay.find(PAIRED, after=t_start) if m.group(1).upper() == JOINED]
    how = peer.stop()
    st = cb.poll(g, lambda s: ghost(s) == (False, False), CLEAR_S, "the stranger's ghost cleared")
    cleared = st is not None
    ok = not seen["ghost"] and not paired
    return ok, (f"ghost seen {seen['ghost']} (held {seen['held']}); relay pairings on {JOINED}: {paired or 'none'}; "
                f"stranger: {peer.tail(4)}; {how}; cleared after: {cleared}")


def _control(g, port, run_dir, ctx, code: str) -> tuple:
    """H4: a fake guest on the host's OWN code. VOID unless ghost and ghost_held read false right before it starts."""
    before = ghost(g.state)
    if before != (False, False):
        return False, (f"VOID: ghost/ghost_held read {before} right before the control guest started (a held ghost "
                       "could pass it)")
    peer = pb.PeerProc("fake-guest-client", ["--relay", f"ws://127.0.0.1:{port}", "--code", code],
                       log_path=run_dir / "control.log", out_path=run_dir / "control.out")
    ctx["peers"].append(peer)
    peer.start()
    st = cb.poll(g, lambda s: ghost(s)[0], SAMPLE_S, "the control guest's ghost")
    how = peer.stop()
    edge = "seen" if st is not None else "NEVER"
    return st is not None, f"before {before}; ghost edge {edge}; control: {peer.tail(4)}; {how}"


# ---------------------------------------------------------------------------------------------- the offline self-check
def _reg_for(code):
    """A relay registration line for ``code``, matched by the bench's own :data:`REG` (None for no code)."""
    return REG.match(f"relay session {code}: host joined") if code else None


class _Boom(Exception):
    """An exception mid-leg, as the GUI half can raise one: nothing recorded, the scenario's ``finally`` closes."""


def calibration_sim(gui_leg) -> tuple:
    """A COOP_CALIBRATE ledger, offline, through the SHIPPED calls: the s153-shaped CLI half (H2 the leak via
    :func:`record_host`, H3 the stranger in, H0/H1/H4/H2g-pre green), then ``gui_leg(led)`` for the GUI half, the
    scenario's ``finally`` (``close`` then :meth:`Ledger.judge_calibration`). Returns (HC-CAL green, its detail)."""
    class _G:
        def __init__(self):
            self.rows = []

        def check(self, ok, label, detail=""):
            self.rows.append((ok, label, detail))
            return ok

        def note(self, _msg):
            pass
    g = _G()
    led = cb.Ledger(g, dict(CATALOG, **{"HC-CAL": "CALIBRATION (simulated)"}), finals=("HC-CAL",))
    for cid in ("H0", "H1", "H4", "H2g-pre"):
        led.check(cid, True, "simulated green")
    record_host(led, "H2", KitRun(0, f"  session code:  {JOINED}"), JOINED, _reg_for(JOINED), {"SessionCode": JOINED},
                gui=False)
    led.check("H3", False, "simulated: the stranger paired")
    try:
        gui_leg(led)
    except _Boom:
        pass
    led.close("the run ended before this check was reached")
    green = led.judge_calibration("HC-CAL", PREDICTED_S153)
    return green, g.rows[-1][2]


def _instrument_rows(row, gui_runs: dict) -> None:
    """THE INSTRUMENT / VERDICT SPLIT (H2g-ran) on the shipped call sites -- :func:`host_verdict`, :func:`record_host`,
    :func:`gui_leg_unreached` -- judged by the shipped :meth:`Ledger.judge_calibration`: the real s153 leak still
    calibrates, and every way the Workspace leg can fail to RUN now fails HC-CAL instead of passing as the leak."""
    for expect, (run, sc) in gui_runs.items():
        ran, ok = host_verdict(run, sc, _reg_for(sc), {"SessionCode": sc}, gui=True)
        row(ran and ok == (expect == "new"),
            f"{expect}: the Workspace leg's real stub output -> H2g-ran {ran} (the instrument ran), H2g {ok}")
    row("H2g-ran" in CATALOG and "H2g-ran" not in PREDICTED_S153 and set(H2G_LEG) == {"H2g", "H2g-ran"},
        "H2g-ran is catalogued, never predicted, and unreached with H2g by every GUI-half early exit")
    leak, leak_sc = gui_runs.get("old", (KitRun(VOID_RC, "STUB VOID no old-kit run"), None))
    own, own_sc = gui_runs.get("new", (KitRun(VOID_RC, "STUB VOID no new-kit run"), None))
    no_argv = KitRun(0, "\n".join(ln for ln in leak.lines if not ln.startswith("STUB ARGV ")))

    def host(run, c, *, reg="auto", ini="auto"):
        return lambda led: record_host(led, "H2g", run, c, _reg_for(c) if reg == "auto" else reg,
                                       {"SessionCode": c if ini == "auto" else ini}, gui=True)

    def boom(_led):
        raise _Boom("mid-leg")
    cases = (   # (what, HC-CAL green?, a needle its detail must hold, the GUI half)
        ("the real s153 leak (the old kit's own stub output)", True, "unpredicted reds: none", host(leak, leak_sc)),
        ("this kit's own code (no leak: a calibration that cannot see the s153 kit)", False,
         "stayed GREEN: ['H2g']", host(own, own_sc)),
        ("a VOID stub (Start hosting spawned nothing)", False, "unpredicted reds: ['H2g-ran']",
         host(KitRun(VOID_RC, "STUB VOID Start hosting spawned nothing: another job is running"), None)),
        ("a GUI crash (rc 1)", False, "unpredicted reds: ['H2g-ran']",
         host(KitRun(1, "Traceback (most recent call last):\nImportError: no PySide6"), None)),
        ("a kit timeout (rc -1)", False, "unpredicted reds: ['H2g-ran']",
         host(KitRun(-1, "STUB VOID the kit call timed out after 240 s"), None)),
        ("no relay registration under the code", False, "unpredicted reds: ['H2g-ran']",
         host(leak, leak_sc, reg=None)),
        ("the root ini disagreeing with the engine", False, "unpredicted reds: ['H2g-ran']",
         host(leak, leak_sc, ini="ff9-SOMEONE1")),
        ("no captured Workspace argv", False, "unpredicted reds: ['H2g-ran']", host(no_argv, leak_sc)),
        ("relay B never listening (an early exit)", False, "unpredicted reds: ['H2g-ran']",
         lambda led: gui_leg_unreached(led, "the bench relay on 49246 never listened")),
        ("an exception mid-leg (the finally's close)", False, "unpredicted reds: ['H2g-ran']", boom),
    )
    for what, want, needle, gui_leg in cases:
        green, detail = calibration_sim(gui_leg)
        row(green == want and needle in detail, f"HC-CAL on {what}: {'green' if green else 'red'} -- {detail}")


def selfcheck() -> int:
    """The stub + the KIT half, offline: a throwaway fake root, both kits, the CLI and the GUI leg. No game, no relay."""
    rows = []

    def row(ok, what):
        rows.append(ok)
        print(("  ok    " if ok else "  FAIL  ") + what)
    tmp = Path(tempfile.mkdtemp(prefix="coop-host-code-"))
    gui_runs = {}                                  # expect -> (the GUI leg's real KitRun, the SessionCode it left)
    try:
        kits = {"new": REPO / "ff9mapkit", "old": materialize_cal_kit(tmp / f"kit-{CAL_SHA}")}
        not_install = tmp / "not-the-install"
        for expect, kit in kits.items():
            root = tmp / f"root-{expect}"
            root.mkdir()
            (root / "Memoria.ini").write_text("[Netsync]\nEnabled = 0\nRole = host\nSessionCode = ff9-I0000000\n"
                                              "HostSessionCode = ff9-I0000000\n", encoding="utf-8")

            def call(*argv, mode="cli", want=expect, port=PORT_A):
                return kit_call(kit, root, not_install, mode, want, port, *argv)

            wrong = call("show", want="new" if expect == "old" else "old")
            row(wrong.rc == VOID_RC and "expected the" in (wrong.void or ""), f"{expect}: the wrong-kit pin is VOID")
            ghost_root = kit_call(kit, tmp / "no-such-root", not_install, "cli", expect, PORT_A, "show")
            row(ghost_root.rc != 0, f"{expect}: a missing root never falls through (rc {ghost_root.rc})")
            shown = call("show")
            row(shown.rc == 0 and shown.install_line is not None and Path(shown.install_line).resolve() == root.resolve(),
                f"{expect}: `show` names the root ({shown.install_line})")
            call("join", JOINED)
            call("off")
            host = call("host")
            text = (root / "Memoria.ini").read_text(encoding="utf-8-sig")
            sc = re.findall(r"(?m)^SessionCode = (.*)$", text)[-1].strip()
            published = sc.upper() == JOINED
            row(published == (expect == "old"),
                f"{expect}: a former guest's CLI `coop host` -> SessionCode {sc} ({'the invite' if published else 'own'})")
            row(host.rc == 0 and f"RelayUrl = ws://127.0.0.1:{PORT_A}" in text,
                f"{expect}: the CLI leg ran with the private port (RelayUrl ws://127.0.0.1:{PORT_A})")
            call("join", JOINED, port=PORT_B)
            call("off", port=PORT_B)
            gui = call("host", mode="gui", port=PORT_B)
            argv = json.loads(gui.fact("ARGV") or "[]")
            text = (root / "Memoria.ini").read_text(encoding="utf-8-sig")
            sc = re.findall(r"(?m)^SessionCode = (.*)$", text)[-1].strip()
            carried = JOINED in argv
            row(gui.rc == 0 and carried == (expect == "old") and (sc.upper() == JOINED) == (expect == "old"),
                f"{expect}: the Workspace leg -> field {gui.fact('FIELD')}, argv carries the invite {carried}, "
                f"SessionCode {sc} (rc {gui.rc}: {gui.void or gui.tail(2)})")
            row(f"RelayUrl = ws://127.0.0.1:{PORT_B}" in text,
                f"{expect}: the GUI leg's argv ran with the private port appended")
            gui_runs[expect] = (gui, sc)
        _instrument_rows(row, gui_runs)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = rows.count(False)
    print(f"coop_host_code selfcheck: {'OK' if not bad else 'FAIL'} ({len(rows) - bad}/{len(rows)} rows)")
    return 0 if not bad else 1


if __name__ == "__main__":
    if "--selfcheck" in sys.argv[1:]:
        raise SystemExit(selfcheck())
    print(__doc__)
    raise SystemExit(2)
