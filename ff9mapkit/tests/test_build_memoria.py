"""``tools/build_memoria.py`` -- the enforcement call site for the engine build's four laws.

The build AUTO-DEPLOYS over the live install (csproj AfterBuild), and until Lane H (2026-08-24)
its safety was four PROCEDURAL rules with no call site: snapshot first, dash-style switches (MSYS
mangles ``/t:``), the SolutionDir trailing backslash, and a by-hand post-deploy sha comparison.
These tests pin that the wrapper (a) refuses to build without the full pre-build backup,
(b) assembles the exact mandated msbuild invocation as a LIST (no shell => no MSYS class),
(c) refuses --no-deploy when the csproj cannot honor it (a false promise would deploy anyway),
and (d) verifies the deploy landed on BOTH arches, flagging a mixed/partial deploy loudly.

Every fixture install is built under tmp_path; the fake runner never touches msbuild or the game.
"""

import importlib.util
import os
import pathlib
import types

REPO = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("build_memoria", REPO / "tools" / "build_memoria.py")
bm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bm)


# ---------------------------------------------------------------- fixtures

def _clone(tmp_path, *, dwix=True):
    """A fake Memoria clone: the csproj (with/without the DWIXNoDeploy condition) + Output DLLs."""
    clone = tmp_path / "Memoria"
    (clone / "Assembly-CSharp").mkdir(parents=True)
    (clone / "Assembly-CSharp" / "Assembly-CSharp.csproj").write_text(
        "<Project>" + ("<Target Name='AfterBuild' Condition=\"'$(DWIXNoDeploy)' != 'true'\"/>"
                       if dwix else "<Target Name='AfterBuild'/>") + "</Project>",
        encoding="utf-8")
    out = clone / "Output"
    out.mkdir()
    for dll in bm.DLLS:
        (out / dll).write_bytes(b"BUILT-" + dll.encode())
    return clone


def _install(tmp_path, *, live=True):
    """A fake game install (Managed dirs per arch, optionally holding live DLLs) + empty backups/."""
    managed = {}
    for arch in bm.ARCHES:
        d = tmp_path / "game" / arch / "FF9_Data" / "Managed"
        d.mkdir(parents=True)
        if live:
            for dll in bm.DLLS:
                (d / dll).write_bytes(b"LIVE-" + dll.encode())
        managed[arch] = str(d)
    bkp = tmp_path / "backups"
    bkp.mkdir()
    return str(bkp), managed


class _Runner:
    """Records every subprocess call; returns rc 0 with empty output (git calls included)."""

    def __init__(self, rc=0):
        self.calls, self.rc = [], rc

    def __call__(self, args, **kw):
        self.calls.append(list(args))
        rc = self.rc if os.path.basename(str(args[0])).lower().startswith("msbuild") else 0
        return types.SimpleNamespace(returncode=rc, stdout="", stderr="")

    def msbuild_calls(self):
        return [c for c in self.calls if os.path.basename(c[0]).lower().startswith("msbuild")]


def _wire(monkeypatch, tmp_path, runner, *, live=True):
    """Point the module's seams at the fake install; returns (clone, bkp, managed)."""
    clone = _clone(tmp_path)
    bkp, managed = _install(tmp_path, live=live)
    msbuild = tmp_path / "MSBuild.exe"
    msbuild.write_bytes(b"")
    monkeypatch.setattr(bm, "BKP", bkp)
    monkeypatch.setattr(bm, "MANAGED", managed)
    monkeypatch.setattr(bm, "DEFAULT_MSBUILD", str(msbuild))
    monkeypatch.setattr(bm, "RUN", runner)
    return clone, bkp, managed


# ---------------------------------------------------------------- the invocation itself

def test_msbuild_args_are_the_mandated_recipe_as_a_list():
    args = bm.msbuild_args(r"C:\mb\MSBuild.exe", r"C:\c\A.csproj", r"C:\gd\FFIX\Memoria")
    assert args == [r"C:\mb\MSBuild.exe", r"C:\c\A.csproj", "-t:Build",
                    "-p:Configuration=Release", "-p:SolutionDir=C:\\gd\\FFIX\\Memoria\\", "-m"]
    # dash-style throughout -- a list-args subprocess also sidesteps MSYS /t: mangling entirely
    assert not any(a.startswith("/") for a in args[2:])
    # the trailing backslash is load-bearing and normalized whatever the caller passed
    assert bm.msbuild_args("m", "c", "C:\\clone\\")[4] == "-p:SolutionDir=C:\\clone\\"
    assert bm.msbuild_args("m", "c", "C:\\clone", no_deploy=True)[-1] == "-p:DWIXNoDeploy=true"


def test_no_deploy_supported_reads_the_csproj_condition(tmp_path):
    assert bm.no_deploy_supported(str(_clone(tmp_path / "a") / "Assembly-CSharp" / "Assembly-CSharp.csproj"))
    assert not bm.no_deploy_supported(
        str(_clone(tmp_path / "b", dwix=False) / "Assembly-CSharp" / "Assembly-CSharp.csproj"))
    assert not bm.no_deploy_supported(str(tmp_path / "missing.csproj"))


# ---------------------------------------------------------------- the backup law

def test_build_refuses_without_a_full_backup(tmp_path, capsys, monkeypatch):
    """No live DLLs to snapshot => backup incomplete => the build must NOT run (the snapshot is
    the only revert point once the AfterBuild deploy fires)."""
    runner = _Runner()
    clone, bkp, _ = _wire(monkeypatch, tmp_path, runner, live=False)
    rc = bm.main(["build_memoria.py", "--clone", str(clone)])
    assert rc == 2
    assert "backup INCOMPLETE" in capsys.readouterr().out
    assert runner.msbuild_calls() == []                        # msbuild never invoked


def test_skip_backup_only_honors_a_fresh_full_set(tmp_path, capsys, monkeypatch):
    runner = _Runner()
    clone, bkp, managed = _wire(monkeypatch, tmp_path, runner)
    rc = bm.main(["build_memoria.py", "--clone", str(clone), "--skip-backup"])
    assert rc == 2 and runner.msbuild_calls() == []            # empty backups/ -> refused
    assert "--skip-backup REFUSED" in capsys.readouterr().out
    for dll in bm.DLLS:                                        # fabricate a fresh full set
        stem, ext = os.path.splitext(dll)
        for arch in bm.ARCHES:
            (pathlib.Path(bkp) / f"{stem}.{arch}{ext}.20260824-000000").write_bytes(b"x")
    # make the live copies match Output so the verification passes
    for arch, mgd in managed.items():
        for dll in bm.DLLS:
            (pathlib.Path(mgd) / dll).write_bytes(b"BUILT-" + dll.encode())
    rc = bm.main(["build_memoria.py", "--clone", str(clone), "--skip-backup"])
    assert rc == 0 and len(runner.msbuild_calls()) == 1


def test_full_backup_set_age_requires_every_target(tmp_path):
    bkp, _ = _install(tmp_path, live=False)
    assert bm.full_backup_set_age_s(bkp) is None               # empty
    now = 1_700_000_000
    for i, dll in enumerate(bm.DLLS):
        stem, ext = os.path.splitext(dll)
        for arch in bm.ARCHES:
            p = pathlib.Path(bkp) / f"{stem}.{arch}{ext}.20260824-000000"
            p.write_bytes(b"x")
            os.utime(p, (now - 100 - i, now - 100 - i))
    age = bm.full_backup_set_age_s(bkp, now=now)
    assert age == 100 + len(bm.DLLS) - 1                       # the OLDEST member defines the set's age
    (pathlib.Path(bkp) / "Memoria.Prime.x86.dll.20260824-000000").unlink()
    assert bm.full_backup_set_age_s(bkp, now=now) is None      # one gap -> no full set


# ---------------------------------------------------------------- --no-deploy honesty

def test_no_deploy_refused_when_the_csproj_cannot_honor_it(tmp_path, capsys, monkeypatch):
    runner = _Runner()
    _wire(monkeypatch, tmp_path, runner)
    plain = _clone(tmp_path / "plain", dwix=False)             # csproj WITHOUT the condition
    rc = bm.main(["build_memoria.py", "--clone", str(plain), "--no-deploy"])
    assert rc == 2
    assert "--no-deploy REFUSED" in capsys.readouterr().out
    assert runner.msbuild_calls() == []


def test_no_deploy_builds_without_backup_and_passes_the_property(tmp_path, capsys, monkeypatch):
    runner = _Runner()
    clone, bkp, _ = _wire(monkeypatch, tmp_path, runner, live=False)   # no live DLLs needed
    rc = bm.main(["build_memoria.py", "--clone", str(clone), "--no-deploy"])
    assert rc == 0
    (call,) = runner.msbuild_calls()
    assert call[-1] == "-p:DWIXNoDeploy=true"
    assert "NOTHING deployed" in capsys.readouterr().out
    assert list(pathlib.Path(bkp).iterdir()) == []             # no snapshot taken (nothing at risk)


# ---------------------------------------------------------------- deploy verification

def test_verify_deploy_classifies_ok_mismatch_absent(tmp_path):
    clone = _clone(tmp_path)
    _, managed = _install(tmp_path, live=False)
    a = pathlib.Path(managed["x64"])
    (a / bm.DLLS[0]).write_bytes(b"BUILT-" + bm.DLLS[0].encode())      # matches Output
    (a / bm.DLLS[1]).write_bytes(b"STALE")                             # differs
    ok, mism, absent = bm.verify_deploy(str(clone / "Output"), managed)
    assert f"{bm.DLLS[0]} [x64]" in ok
    assert f"{bm.DLLS[1]} [x64]" in mism
    assert any(lbl.startswith(f"{bm.DLLS[2]} [x64]") for lbl in absent)
    assert all("[x86]" in lbl for lbl in absent if "[x86]" in lbl)     # empty x86 arch all absent


def test_a_mixed_deploy_is_loud_and_nonzero(tmp_path, capsys, monkeypatch):
    """The realistic partial-deploy: FF9 running locks the loaded arch mid-copy. The build 'worked'
    (rc 0 here) but one live copy differs from Output -- the wrapper must not call that success."""
    runner = _Runner()
    clone, _, managed = _wire(monkeypatch, tmp_path, runner)
    for arch, mgd in managed.items():
        for dll in bm.DLLS:
            (pathlib.Path(mgd) / dll).write_bytes(b"BUILT-" + dll.encode())
    (pathlib.Path(managed["x64"]) / bm.DLLS[0]).write_bytes(b"OLD")    # one target kept the old build
    rc = bm.main(["build_memoria.py", "--clone", str(clone)])
    out = capsys.readouterr().out
    assert rc == 3
    assert "MISMATCH" in out and "MIXED" in out
    assert "restore_memoria_dll.py" in out                     # the way back is printed


def test_the_green_path_backs_up_builds_verifies_and_prints_the_restore_line(tmp_path, capsys, monkeypatch):
    runner = _Runner()
    clone, bkp, managed = _wire(monkeypatch, tmp_path, runner)
    for arch, mgd in managed.items():                          # live == Output -> verification green
        for dll in bm.DLLS:
            (pathlib.Path(mgd) / dll).write_bytes(b"BUILT-" + dll.encode())
    rc = bm.main(["build_memoria.py", "--clone", str(clone), "--label", "pre-s81"])
    out = capsys.readouterr().out
    assert rc == 0
    snaps = list(pathlib.Path(bkp).iterdir())
    assert len(snaps) == len(bm.DLLS) * len(bm.ARCHES)         # the full 3x2 snapshot exists
    assert all(".pre-s81." in p.name for p in snaps)
    assert len(runner.msbuild_calls()) == 1
    assert "built + deployed + verified" in out and "RELAUNCH" in out
    assert "restore_memoria_dll.py" in out
