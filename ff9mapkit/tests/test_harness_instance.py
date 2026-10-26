"""``tools/harness/instance.py`` + the Session's multi-instance mode -- two FF9s on one machine, offline.

WHAT THESE PIN. An instance root is built, verified, refreshed and torn down against a FAKE install tree in tmp_path --
never the real one -- and the teardown law is proven where it matters: every junction target is byte-for-byte untouched
after a teardown, including junctions the plan never made. The claim refuses a live run and adopts a dead one; the
path-scoped pid probe tells one root's game from another's; the ``-single-instance`` mutex key is computed and a clash
drops the flag; two FakeGames in two tmp roots run side by side under two Sessions in ONE process, each on its own
channel, with nonce-distinct arms; and a Session without ``instance=`` is exactly what it was.

WHAT THEY ARE NOT. No FF9 runs here. Junction tests need Windows (NTFS junctions, unelevated); the rest is portable.
"""

import hashlib
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "ff9mapkit"))

from harness import HarnessError, Session                          # noqa: E402
from harness import channel as channel_mod                         # noqa: E402
from harness import instance as I                                  # noqa: E402
from harness.channel import Channel                                # noqa: E402
from harness.fakegame import FakeGame                              # noqa: E402
from harness.session import ff9_pids, launch_args                  # noqa: E402

needs_junctions = pytest.mark.skipif(os.name != "nt", reason="NTFS junctions are Windows-only")

INI = (
    "[Mod]\r\n"
    "FolderNames = \"FF9CustomMap\", \"ModB\"\r\n"
    "Priorities = \"FF9CustomMap\", \"ModB\"\r\n"
    "\r\n"
    "[Graphics]\r\n"
    "Enabled = 1\r\n"
    "\r\n"
    "[Control]\r\n"
    "Enabled = 1\r\n"
    "AlwaysCaptureGamepad = 1\r\n"
    "\r\n"
    "[Netsync]\r\n"
    "Enabled = 1\r\n"
    "Role = host\r\n"
    "RelayUrl = ws://127.0.0.1:49201\r\n"
    "SessionCode = ff9-OWNERLIV\r\n"
    "HostSessionCode = ff9-OWNERHST\r\n"
    "\r\n"
    "[SfxProbe]\r\n"
    "Enabled = 1\r\n"
)


def make_install(base: pathlib.Path) -> pathlib.Path:
    """A real-shaped fake FF9 install: exe + DLLs, x64\\FF9_Data with the junctioned dirs and data files, the root trees a
    root links, two mod folders (one with a DictionaryPatch the warp guard reads), and an owner-like Memoria.ini."""
    inst = base / "FINAL FANTASY IX"
    x64 = inst / "x64"
    data = x64 / "FF9_Data"
    for d in ("Managed", "Mono", "Plugins", "Resources"):
        (data / d).mkdir(parents=True)
        (data / d / f"{d}.bin").write_bytes(d.encode() * 50)
    for f in I.EXE_FILES:
        (x64 / f).write_bytes(b"MZ" + f.encode())
    for f in ("level0", "mainData", "resources.assets", "sharedassets0.assets"):
        (data / f).write_bytes(f.encode() * 100)
    (data / "output_log.txt").write_text("a previous launch's unity log\n", encoding="utf-8")
    (inst / "StreamingAssets").mkdir()
    (inst / "StreamingAssets" / "p0data1.bin").write_bytes(b"\x00\x01" * 500)
    (inst / "FF9_Data" / "EmbeddedAsset").mkdir(parents=True)
    (inst / "FF9_Data" / "EmbeddedAsset" / "text.txt").write_text("embedded\n", encoding="utf-8")
    (inst / "FF9CustomMap").mkdir()
    (inst / "FF9CustomMap" / "DictionaryPatch.txt").write_text(
        "FieldScene 30810 11 CHEST_ROOM CHEST_ROOM 30810\nFieldScene 30820 11 ROOM_A ROOM_A 30820\n", encoding="utf-8")
    (inst / "ModB").mkdir()
    (inst / "ModB" / "b.txt").write_text("mod b\n", encoding="utf-8")
    (inst / "Unregistered").mkdir()
    (inst / "Unregistered" / "keep.txt").write_text("not in FolderNames\n", encoding="utf-8")
    (inst / "Memoria.ini").write_bytes(INI.encode("utf-8"))
    (inst / "Settings.ini").write_text("[Settings]\nWindowMode = 0\n", encoding="utf-8")
    return inst


def tree_fingerprint(top: pathlib.Path) -> dict:
    """Every file under ``top`` (no link is ever followed: the install holds none): relative path -> (sha, size, mtime)."""
    out = {}
    for dirpath, _dirs, files in os.walk(top):
        for f in files:
            p = pathlib.Path(dirpath) / f
            st = p.stat()
            out[str(p.relative_to(top))] = (hashlib.sha256(p.read_bytes()).hexdigest(), st.st_size, st.st_mtime_ns)
    return out


def no_procs():
    return []


@pytest.fixture
def install(tmp_path):
    return make_install(tmp_path / "steam")


@pytest.fixture
def root(tmp_path):
    return tmp_path / "inst" / "guest"


def inst_for(root, install, **kw):
    kw.setdefault("procs", no_procs)
    kw.setdefault("log", lambda m: None)
    return I.Instance(root, install=install, **kw)


# ------------------------------------------------------------------------------------------- the pure parts


def test_single_instance_key_is_the_last_30_chars_with_non_alphanumerics_dashed():
    # Both spellings longer than the 30-char tail (the drive letter is 2 of the Windows one's 31): a shorter path's key
    # is the whole path, so the POSIX one carries a /srv prefix -- without it, 29 chars and a 29-char key.
    exe = r"C:\gd\ff9-inst\host\x64\FF9.exe" if os.name == "nt" else "/srv/gd/ff9-inst/host/x64/FF9.exe"
    key = I.single_instance_key(exe)
    assert len(key) == 30
    assert key.endswith("x64-FF9-exe")
    assert set(key) <= set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-")


def test_single_instance_clash_finds_roots_sharing_the_last_30_chars(tmp_path):
    a = tmp_path / "aaaaaaaa" / "common" / "inst" / "hostroot" / "x64" / "FF9.exe"
    b = tmp_path / "bbbbbbbb" / "common" / "inst" / "hostroot" / "x64" / "FF9.exe"    # same 30-char tail
    c = tmp_path / "inst" / "guest" / "x64" / "FF9.exe"
    assert I.single_instance_key(a) == I.single_instance_key(b)
    assert I.single_instance_clash(a, [b, c]) == [str(b)]
    assert I.single_instance_clash(c, [a, b]) == []
    assert I.single_instance_clash(a, [a]) == [], "an exe never clashes with itself"


def test_scan_game_scopes_by_image_path_and_counts_unreadable_images(tmp_path):
    mine = tmp_path / "inst" / "host" / "x64" / "FF9.exe"
    other = tmp_path / "inst" / "guest" / "x64" / "FF9.exe"
    images = {11: str(mine), 12: str(other), 13: str(mine).upper() if os.name == "nt" else str(mine)}

    def image_of(pid):
        if pid not in images:
            raise OSError("access denied")
        return images[pid]

    procs = lambda: [(11, "FF9.exe"), (12, "ff9.EXE"), (13, "FF9.exe"), (14, "FF9.exe"), (15, "notepad.exe")]   # noqa: E731
    got_mine, got_others, unknown = I.scan_game(mine, procs=procs, image_of=image_of)
    assert got_mine == [11, 13] and got_others == [12] and unknown == [14]
    assert I.pids_at(other, procs=procs, image_of=image_of) == [12]


def test_base_overlay_parks_netsync_away_from_the_owner_and_keeps_crlf(tmp_path):
    text = I.overlay_text(INI, I.base_overlay(tmp_path / "r"))
    assert "\r\n" in text and "\n" not in text.replace("\r\n", "")
    assert "RelayUrl = ws://127.0.0.1:9\r\n" in text and "49201" not in text
    assert "ff9-OWNERLIV" not in text and I.parked_code(tmp_path / "r") in text
    # [ff9mapkit s154] the kit's own-code record is parked too: a `coop host` aimed at a root that inherited the
    # owner's HostSessionCode would re-publish the OWNER's session
    assert "ff9-OWNERHST" not in text and f"HostSessionCode = {I.parked_code(tmp_path / 'r')}\r\n" in text
    assert I.parked_code(tmp_path / "r") != I.parked_code(tmp_path / "s")
    assert len(I.parked_code(tmp_path / "r")) == len("ff9-") + 8
    # only [Netsync] Enabled flips there; [Graphics]/[Control] Enabled = 1 stay
    assert text.count("Enabled = 1") == 2 and "AlwaysCaptureGamepad = 0" in text


# ------------------------------------------------------------------------------------------- build / verify


@needs_junctions
def test_build_makes_junctions_copies_and_the_overlaid_ini(root, install):
    inst = inst_for(root, install)
    inst.build()
    assert inst.verify() == [] and inst.verify(deep=True) == []
    for name in ("StreamingAssets", "FF9_Data", "FF9CustomMap", "ModB"):
        assert os.path.isjunction(root / name), name
        assert I._same_path(root / name, install / name)
    for d in I.DATA_DIRS:
        assert os.path.isjunction(root / "x64" / "FF9_Data" / d)
    assert not (root / "Unregistered").exists(), "only FolderNames entries are linked"
    exe = root / "x64" / "FF9.exe"
    assert exe.is_file() and not I._is_reparse(exe) and exe.read_bytes() == (install / "x64" / "FF9.exe").read_bytes()
    assert os.stat(exe).st_ino != os.stat(install / "x64" / "FF9.exe").st_ino, "a COPY, never a hardlink"
    assert not (root / "x64" / "FF9_Data" / "output_log.txt").exists(), "the game's own log is never copied"
    ini = (root / "Memoria.ini").read_bytes().decode()
    assert "Enabled = 0" in ini and "AlwaysCaptureGamepad = 0" in ini and "ff9-OWNERLIV" not in ini
    assert (root / I.MARKER).is_file()
    assert inst.ensure() == [], "ensure() on a right root changes nothing"


@needs_junctions
def test_build_refuses_to_place_a_root_inside_or_over_the_install(tmp_path, install):
    for bad in (install, install / "inner", install.parent):
        with pytest.raises(I.InstanceError, match="overlaps the install"):
            inst_for(bad, install).build()


# ------------------------------------------------------------------------------------------- THE TEARDOWN LAW


@needs_junctions
def test_teardown_never_touches_a_junction_target(root, install):
    """THE TEARDOWN LAW, proven where it matters: after build -> run-like writes -> teardown, every file of the
    install -- every junction's target included -- is byte-, size- and mtime-identical, and the root is gone."""
    before = tree_fingerprint(install)
    inst = inst_for(root, install)
    inst.build()
    # what a run leaves in a root: logs, a channel, a save sandbox, FontList
    (root / "Memoria.log").write_text("run log\n", encoding="utf-8")
    (root / "FontList").write_text("fonts\n", encoding="utf-8")
    (root / "x64" / "ff9harness" / "save").mkdir(parents=True)
    (root / "x64" / "ff9harness" / "state.json").write_text("{}", encoding="utf-8")
    (root / "x64" / "FF9_Data" / "output_log.txt").write_text("unity\n", encoding="utf-8")
    counts = inst.teardown()
    assert not root.exists()
    assert counts["links"] == 4 + len(I.DATA_DIRS)
    assert tree_fingerprint(install) == before


@needs_junctions
def test_teardown_unlinks_junctions_the_plan_never_made_without_following_them(root, install):
    """A stale junction (an unregistered folder) and one buried deep in the tree are links too: removed, not followed."""
    before = tree_fingerprint(install)
    inst = inst_for(root, install)
    inst.build()
    I.make_junction(root / "Unregistered", install / "Unregistered")
    (root / "x64" / "deep" / "er").mkdir(parents=True)
    I.make_junction(root / "x64" / "deep" / "er" / "sa", install / "StreamingAssets")
    found = [p for _d, _s, _f, rp in I.walk_no_follow(root) for p in rp]
    assert root / "Unregistered" in found and root / "x64" / "deep" / "er" / "sa" in found
    inst.teardown()
    assert not root.exists()
    assert tree_fingerprint(install) == before


@needs_junctions
def test_walk_no_follow_never_descends_into_a_junction(root, install):
    inst_for(root, install).build()
    walked = [d for d, _s, _f, _rp in I.walk_no_follow(root)]
    assert all(not str(d).startswith(str(root / "StreamingAssets")) for d in walked)
    assert all("p0data1.bin" not in str(f) for _d, _s, fs, _rp in I.walk_no_follow(root) for f in fs)


@needs_junctions
def test_teardown_refuses_without_the_marker_and_while_its_game_runs(root, install):
    inst = inst_for(root, install)
    inst.build()
    running = inst_for(root, install, procs=lambda: [(77, "FF9.exe")], image_of=lambda pid: str(root / "x64" / "FF9.exe"))
    with pytest.raises(I.InstanceBusy, match="its game is running"):
        running.teardown()
    unreadable = inst_for(root, install, procs=lambda: [(78, "FF9.exe")],
                          image_of=lambda pid: (_ for _ in ()).throw(OSError("denied")))
    with pytest.raises(I.InstanceBusy, match="cannot read"):
        unreadable.teardown()
    (root / I.MARKER).unlink()
    with pytest.raises(I.InstanceError, match="no .ff9-instance.json"):
        inst.teardown()
    assert os.path.isjunction(root / "StreamingAssets"), "a refused teardown touched nothing"


@needs_junctions
def test_teardown_refuses_an_unknown_reparse_kind_before_deleting_any_file(root, install, monkeypatch):
    inst = inst_for(root, install)
    inst.build()
    monkeypatch.setattr(I, "_is_junction", lambda p: False)      # every link now reads as "neither junction nor symlink"
    with pytest.raises(I.InstanceError, match="neither a junction nor a symlink"):
        inst.teardown()
    assert (root / "x64" / "FF9.exe").is_file(), "no real file may go before every link is gone"


# ------------------------------------------------------------------------------------------- refresh (drift)


@needs_junctions
def test_refresh_links_a_newly_registered_folder_and_repairs_drift(root, install):
    inst = inst_for(root, install)
    inst.build()
    # the owner registers a new mod folder, Steam updates a data file, a co-op run leaves its [Netsync] behind
    (install / "ModC").mkdir()
    ini = (install / "Memoria.ini").read_bytes().decode().replace(
        'FolderNames = "FF9CustomMap", "ModB"', 'FolderNames = "FF9CustomMap", "ModB", "ModC"')
    (install / "Memoria.ini").write_bytes(ini.encode())
    (install / "x64" / "FF9_Data" / "level0").write_bytes(b"patched" * 300)
    inst.netsync({"Enabled": "1", "Role": "client"}, backup_to=root.parent / "bak")
    assert any("drifted" in b for b in inst.verify()) and any("ModC" in b for b in inst.verify())
    done = inst.refresh()
    assert any("ModC" in d for d in done) and any("level0" in d for d in done) and any("Memoria.ini" in d for d in done)
    assert os.path.isjunction(root / "ModC") and inst.verify() == []


@needs_junctions
def test_refresh_repoints_a_wrong_junction_and_refuses_a_real_dir_in_its_place(root, install):
    inst = inst_for(root, install)
    inst.build()
    os.rmdir(root / "ModB")
    I.make_junction(root / "ModB", install / "Unregistered")
    assert any("ModB" in b for b in inst.verify())
    assert any("re-pointed ModB" in d for d in inst.refresh())
    assert I._same_path(root / "ModB", install / "ModB")
    os.rmdir(root / "ModB")
    (root / "ModB").mkdir()
    (root / "ModB" / "mine.txt").write_text("someone's real files\n", encoding="utf-8")
    with pytest.raises(I.InstanceError, match="REAL directory"):
        inst.refresh()
    assert (root / "ModB" / "mine.txt").is_file()


@needs_junctions
def test_refresh_refuses_under_a_running_game(root, install):
    inst_for(root, install).build()
    running = inst_for(root, install, procs=lambda: [(9, "FF9.exe")], image_of=lambda pid: str(root / "x64" / "FF9.exe"))
    with pytest.raises(I.InstanceBusy, match="refresh it"):
        running.refresh()


@needs_junctions
def test_an_unmarked_prototype_root_is_adopted_and_a_random_dir_is_not(root, install, tmp_path):
    inst = inst_for(root, install)
    inst.build()
    (root / I.MARKER).unlink()                                   # what the study prototype built: no marker
    inst.refresh()
    assert (root / I.MARKER).is_file() and "adopted" in json.loads((root / I.MARKER).read_text(encoding="utf-8"))
    stranger = tmp_path / "inst" / "notaroot"
    (stranger / "x64").mkdir(parents=True)
    (stranger / "x64" / "FF9.exe").write_bytes(b"MZ")
    with pytest.raises(I.InstanceError, match="does not look like an instance root"):
        inst_for(stranger, install).refresh()


# ------------------------------------------------------------------------------------------- the ini


@needs_junctions
def test_netsync_writes_only_the_roots_ini_and_restore_puts_the_overlay_back(root, install):
    owner = (install / "Memoria.ini").read_bytes()
    inst = inst_for(root, install)
    inst.build()
    bak = inst.netsync({"Enabled": "1", "Role": "client", "SessionCode": "ff9-DUOTEST1"}, backup_to=root.parent / "b")
    assert bak.parent == root.parent / "b" and bak.is_file()
    assert not list(root.glob("Memoria.ini.coop-bak-*")), "the backup is moved out of the root"
    text = (root / "Memoria.ini").read_text(encoding="utf-8")
    assert "Role = client" in text and "ff9-DUOTEST1" in text
    assert (install / "Memoria.ini").read_bytes() == owner, "the install's ini is never written"
    assert inst.restore_ini() is True and inst.restore_ini() is False
    assert inst.verify() == []


# ------------------------------------------------------------------------------------------- the claim


@needs_junctions
def test_the_claim_refuses_a_live_sibling_and_a_live_foreign_pid_and_adopts_the_dead(root, install):
    a = inst_for(root, install)
    a.build()
    b = inst_for(root, install)
    with a.claimed("a"):
        with pytest.raises(I.InstanceBusy, match="claimed by pid"):
            b.claim("b")
        assert a.claim("again") == a._nonce, "reentrant for its holder"
        a.release()
        assert a.claim_path.exists()
    assert not a.claim_path.exists()
    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        a.claim_path.write_text(json.dumps({"pid": sleeper.pid, "nonce": "x", "label": "other worktree"}),
                                encoding="utf-8")
        with pytest.raises(I.InstanceBusy, match="other worktree"):
            b.claim("b")
    finally:
        sleeper.kill()
        sleeper.wait(10)
    # A DEAD claimant. Not the sleeper's pid: a killed process stays openable while any handle to it is open, and a pid
    # is soon reused -- pid_alive (rightly) reads both as alive, so that check would flake. No process has this pid.
    a.claim_path.write_text(json.dumps({"pid": 0x7FFFFFF0, "nonce": "x", "label": "a dead driver"}), encoding="utf-8")
    b.claim("b")                                                 # adopted
    b.release()
    a.claim_path.write_text(json.dumps({"pid": os.getpid(), "nonce": "leaked-by-a-dead-object"}), encoding="utf-8")
    b.claim("b")                                                 # same pid, a nonce no live object holds: a leak
    b.release()
    assert not a.claim_path.exists()


# ------------------------------------------------------------------------------------------- Session: instance mode


def fake_session(root, install, fake, **kw):
    inst = kw.pop("inst", None) or inst_for(root, install)
    return Session(instance=inst, run_dir=root.parent / f"run-{root.name}", save_dir=root.parent / "player-saves",
                   launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=kw.pop("verbose", False), **kw)


@needs_junctions
def test_two_fakegames_in_two_roots_run_side_by_side_under_one_driver(tmp_path, install, capsys):
    """The duo's foundation: two Sessions in ONE process, two roots, two channels -- each step lands in its own game,
    each arm carries its own nonce, and both log lines say whose they are."""
    roots = {r: tmp_path / "inst" / r for r in ("host", "guest")}
    for r in roots.values():
        inst_for(r, install).build()
    fakes = {r: FakeGame(p) for r, p in roots.items()}
    with fake_session(roots["host"], install, fakes["host"], label="duo-host", verbose=True) as h, \
            fake_session(roots["guest"], install, fakes["guest"], label="duo-guest", verbose=True) as g:
        assert h.channel.dir == roots["host"] / "x64" / "ff9harness"
        assert g.channel.dir == roots["guest"] / "x64" / "ff9harness"
        arms = {r: json.loads((p / "x64" / "ff9harness" / "arm").read_text(encoding="utf-8")) for r, p in roots.items()}
        assert arms["host"]["pid"] == arms["guest"]["pid"] == os.getpid()
        assert arms["host"]["nonce"] != arms["guest"]["nonce"]
        h.newgame(settle=0)
        g.newgame(settle=0)
        h.warp(30810)
        g.warp(30820)
        assert (h.state.field_id, g.state.field_id) == (30810, 30820)
        assert (fakes["host"].field_id, fakes["guest"].field_id) == (30810, 30820)
        assert h.instance.holds_claim and g.instance.holds_claim
    out = capsys.readouterr().out
    assert "[harness][duo-host]" in out and "[harness][duo-guest]" in out
    for r, p in roots.items():
        assert not (p / "x64" / "ff9harness" / "arm").exists()
        assert not (p / I.CLAIM).exists(), "the claim is released at stop"
        env = json.loads((tmp_path / "inst" / f"run-{r}" / "env.json").read_text(encoding="utf-8"))
        assert env.get("instance", {}).get("root") == str(p)


@needs_junctions
def test_one_root_twice_in_one_driver_is_refused(tmp_path, install):
    root = tmp_path / "inst" / "host"
    inst_for(root, install).build()
    f1, f2 = FakeGame(root), FakeGame(root)
    with fake_session(root, install, f1, label="a"):
        with pytest.raises(HarnessError, match="claimed by pid"):
            with fake_session(root, install, f2, label="b"):
                pass
        assert (root / "x64" / "ff9harness" / "arm").exists(), "the refused twin must not drop the live arm"


@needs_junctions
def test_instance_mode_refreshes_the_root_before_the_launch(tmp_path, install):
    root = tmp_path / "inst" / "guest"
    inst = inst_for(root, install)
    inst.build()
    inst.netsync({"Enabled": "1", "Role": "client"})              # a previous co-op run's leftovers
    os.rmdir(root / "ModB")                                       # and a missing junction
    with fake_session(root, install, FakeGame(root), inst=inst):
        assert os.path.isjunction(root / "ModB")
        assert "Role = client" not in (root / "Memoria.ini").read_text(encoding="utf-8")


@needs_junctions
def test_instance_mode_refuses_a_running_root_and_attaches_without_refreshing(tmp_path, install):
    root = tmp_path / "inst" / "guest"
    image = str(root / "x64" / "FF9.exe")
    running = inst_for(root, install, procs=lambda: [(4242, "FF9.exe")], image_of=lambda pid: image)
    inst_for(root, install).build()
    s = Session(instance=running, run_dir=tmp_path / "run", save_dir=tmp_path / "saves",
                launcher=lambda exe: None, verbose=False)
    with pytest.raises(HarnessError, match=r"already running from .*guest"):
        s.start()
    # attach: only VERIFIED -- a drifted ini is reported, never rewritten under the live game
    (root / "Memoria.ini").write_text("drifted\n", encoding="utf-8")
    fake = FakeGame(root, boot_state="FieldHUD").start()
    try:
        with Session(instance=running, attach=True, run_dir=tmp_path / "run2", save_dir=tmp_path / "saves",
                     boot_timeout=15.0, verbose=False) as g:
            assert g.pid == 4242
            assert (root / "Memoria.ini").read_text(encoding="utf-8") == "drifted\n"
    finally:
        fake.stop()


def test_instance_launch_drops_single_instance_only_on_a_mutex_clash(tmp_path):
    exe_dir = tmp_path / "aaaaaaaa" / "common" / "inst" / "hostroot"
    twin = tmp_path / "bbbbbbbb" / "common" / "inst" / "hostroot" / "x64" / "FF9.exe"
    clash = I.Instance(exe_dir, install=tmp_path / "install", others=[twin])
    clean = I.Instance(exe_dir, install=tmp_path / "install", others=[tmp_path / "x" / "guest" / "x64" / "FF9.exe"])
    s1 = Session(instance=clash, run_dir=tmp_path / "r1", verbose=False)
    s2 = Session(instance=clean, run_dir=tmp_path / "r2", verbose=False)
    assert "-single-instance" not in s1._launch_args()
    assert s2._launch_args() == launch_args(*s2.window_size)


def test_a_default_session_is_unchanged(tmp_path, capsys):
    """No instance= : the shared install's 'any FF9 at all' probe, the stock launch arguments, the bare prefix."""
    s = Session(game_path=tmp_path, run_dir=tmp_path / "run", verbose=True)
    assert s.instance is None and s._pid_probe is ff9_pids
    assert s._launch_args() == launch_args(*s.window_size) and "-single-instance" in s._launch_args()
    s._log("hello")
    assert capsys.readouterr().out == "[harness] hello\n"


def test_game_path_and_instance_must_agree(tmp_path):
    with pytest.raises(HarnessError, match="disagree"):
        Session(game_path=tmp_path / "a", instance=I.Instance(tmp_path / "b", install=tmp_path / "i"), verbose=False)


# ------------------------------------------------------------------------------------------- the channel nonce


def test_a_guarded_channel_refuses_a_live_sibling_and_leaves_its_arm(tmp_path):
    """An instance-root Session's channel (sibling_guard): another LIVE armed channel of this very process on the same
    directory is refused, and the refused one's disarm leaves the live arm alone."""
    (tmp_path / "x64").mkdir()
    a, b = Channel(tmp_path, label="a", sibling_guard=True), Channel(tmp_path, label="b", sibling_guard=True)
    assert a.nonce != b.nonce
    a.arm(force_cycle=False)
    with pytest.raises(HarnessError, match="THIS process"):
        b.claim()
    b.disarm()
    assert a.armed and json.loads(a.arm_path.read_text(encoding="utf-8"))["nonce"] == a.nonce
    a.disarm()
    assert not a.armed


def test_an_unguarded_channel_takes_over_a_same_pid_arm_as_it_always_did(tmp_path):
    """The shared install's default: the nonce is written, but a same-pid arm -- even a live object's -- is taken over
    (the harness suite models a leaked arm exactly so)."""
    (tmp_path / "x64").mkdir()
    a, b = Channel(tmp_path, label="a"), Channel(tmp_path, label="b")
    a.arm(force_cycle=False)
    b.arm(force_cycle=False)
    assert json.loads(b.arm_path.read_text(encoding="utf-8"))["nonce"] == b.nonce
    a.disarm()
    assert not b.armed, "the same-pid disarm removes it, as before nonces"


def test_a_leaked_same_pid_arm_is_adopted_as_before(tmp_path):
    """A dead Session object's arm (same pid, a nonce no live channel holds) -- or a pre-nonce arm -- is taken over
    exactly as the harness always did."""
    (tmp_path / "x64").mkdir()
    ch = Channel(tmp_path)
    ch.dir.mkdir(parents=True, exist_ok=True)
    for body in ({"pid": os.getpid(), "label": "old"}, {"pid": os.getpid(), "label": "dead", "nonce": "gone"}):
        ch.arm_path.write_text(json.dumps(body), encoding="utf-8")
        ch.claim()
    gone = Channel(tmp_path, label="collected")
    gone.arm(force_cycle=False)
    nonce = gone.nonce
    del gone
    import gc
    gc.collect()
    assert nonce not in channel_mod._LIVE_ARMS
    ch.claim()                                                    # its object is gone: a leak, adopted


# ------------------------------------------------------------------------------------------- hang dump: explicit pid


def test_hang_dumper_with_an_explicit_pid_skips_the_resolution():
    from ff9mapkit import hangdump as H

    def boom(*a, **k):
        raise AssertionError("the resolver must not run when --hang-pid names the game")

    # The image as THIS OS spells it (QueryFullProcessImageNameW's, on Windows): the dumper takes its basename with
    # os.path, so a backslashed literal is one whole path component on POSIX.
    image = os.path.join(os.path.abspath(os.sep), "gd", "ff9-inst", "host", "x64", "FF9.exe")
    d = H.HangDumper(True, "dumps", pid=4321, resolver=boom, image_of=lambda pid: image)
    proc = d._resolve(H.GameTarget(50000, 49211))
    assert (proc.pid, proc.exe, proc.how) == (4321, "FF9.exe", "--hang-pid 4321")
    unreadable = H.HangDumper(True, "dumps", pid=99, resolver=boom,
                              image_of=lambda pid: (_ for _ in ()).throw(OSError("gone")))
    proc = unreadable._resolve(H.GameTarget(1, 2))
    assert proc.pid == 99 and proc.image is None and proc.exe == H.GAME_EXE and "unreadable" in proc.how
    assert "pid 4321 (--hang-pid)" in d.describe()
    with pytest.raises(ValueError, match="hang-pid"):
        H.HangDumper.from_options(pid=0)


def test_the_bridge_cli_takes_hang_pid():
    import argparse
    from ff9mapkit import netsync_bridge as NB
    ap = argparse.ArgumentParser()
    NB.add_hang_arguments(ap)
    args = ap.parse_args(["--hang-pid", "777"])
    assert NB.hang_dumper_from_args(args).pid == 777
    assert NB.hang_dumper_from_args(ap.parse_args([])).pid is None


# ------------------------------------------------------------------------------------------- gamewin


def test_gamewin_raises_the_installs_game_when_an_instance_runs_beside_it(monkeypatch, tmp_path):
    from ff9mapkit import config, hangdump
    from ff9mapkit.workspace import gamewin
    install = tmp_path / "FINAL FANTASY IX"
    images = {1: str(install / "x64" / "FF9.exe"), 2: str(tmp_path / "ff9-inst" / "guest" / "x64" / "FF9.exe")}
    monkeypatch.setattr(config, "find_game_path", lambda: install)
    monkeypatch.setattr(hangdump, "process_image_path", lambda pid: images[pid])
    assert gamewin._install_scoped({1, 2}) == {1}
    assert gamewin._install_scoped({2}) == {2}, "one game: that one, wherever it runs from"
    monkeypatch.setattr(config, "find_game_path", lambda: (_ for _ in ()).throw(RuntimeError("no install")))
    assert gamewin._install_scoped({1, 2}) == {1, 2}, "fail-soft"
