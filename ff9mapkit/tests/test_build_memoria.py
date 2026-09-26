"""``tools/build_memoria.py`` -- the enforcement call site for the engine build's four laws.

The build AUTO-DEPLOYS over the live install (csproj AfterBuild), and until Lane H (2026-08-24)
its safety was four PROCEDURAL rules with no call site: snapshot first, dash-style switches (MSYS
mangles ``/t:``), the SolutionDir trailing backslash, and a by-hand post-deploy sha comparison.
These tests pin that the wrapper (a) refuses to build without the full pre-build backup,
(b) assembles the exact mandated msbuild invocation as a LIST (no shell => no MSYS class),
(c) refuses --no-deploy unless every Deploy task in the ProjectReference closure honors it (s45
gated only Assembly-CSharp; the sibling Memoria.Prime + UnityEngine.UI deployed on every
"compile-check" until s91), then sha-compares every live DLL + .mdb around the build and exits 4
on any drift, and (d) verifies the deploy landed on BOTH arches, flagging a mixed/partial deploy.

Every fixture install is built under tmp_path; the fake runner never touches msbuild or the game.
"""

import importlib.util
import os
import pathlib
import types

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("build_memoria", REPO / "tools" / "build_memoria.py")
bm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bm)


# ---------------------------------------------------------------- fixtures

_GATE = "Condition=\"'$(DWIXNoDeploy)' != 'true'\""
_SIBLINGS = ["Memoria.Prime", "Memoria.XInputDotNetPure", "UnityEngine.UI"]


def _csproj(path, *, gated, refs=(), deploy=True):
    """A csproj shaped like the clone's: BOM, the msbuild/2003 namespace, backslash ProjectReferences,
    and an AfterBuild Deploy (XInput's is commented out upstream -- `deploy=False`)."""
    target = (f'<Target Name="AfterBuild" {_GATE if gated else ""}><Deploy TargetName="$(TargetName)" /></Target>'
              if deploy else '<!-- <Target Name="AfterBuild"><Deploy /></Target> -->')
    items = "".join(f'<ProjectReference Include="{r}"><Name>n</Name></ProjectReference>' for r in refs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xef\xbb\xbf" + (
        '<?xml version="1.0" encoding="utf-8"?>\r\n<Project ToolsVersion="15.0" '
        'xmlns="http://schemas.microsoft.com/developer/msbuild/2003">'
        f"<ItemGroup>{items}</ItemGroup>{target}</Project>").encode())


def _clone(tmp_path, *, dwix=True, siblings=True):
    """A fake Memoria clone: Assembly-CSharp.csproj (s45 gate: `dwix`) referencing the sibling
    projects (s91 gate: `siblings`) the real build compiles -- and deploys -- first, + Output DLLs."""
    clone = tmp_path / "Memoria"
    _csproj(clone / "Assembly-CSharp" / "Assembly-CSharp.csproj", gated=dwix,
            refs=[f"..\\{s}\\{s}.csproj" for s in _SIBLINGS])
    for s in _SIBLINGS:
        _csproj(clone / s / f"{s}.csproj", gated=siblings, deploy=(s != "Memoria.XInputDotNetPure"))
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
    """Records every subprocess call; returns rc 0 with empty output (git calls included).
    `on_msbuild` runs INSIDE the msbuild call -- a sibling Deploy writing the live install."""

    def __init__(self, rc=0, on_msbuild=None):
        self.calls, self.rc, self.on_msbuild = [], rc, on_msbuild

    def __call__(self, args, **kw):
        self.calls.append(list(args))
        is_msbuild = os.path.basename(str(args[0])).lower().startswith("msbuild")
        if is_msbuild and self.on_msbuild:
            self.on_msbuild()
        return types.SimpleNamespace(returncode=self.rc if is_msbuild else 0, stdout="", stderr="")

    def msbuild_calls(self):
        return [c for c in self.calls if os.path.basename(c[0]).lower().startswith("msbuild")]


def _wire(monkeypatch, tmp_path, runner, *, live=True):
    """Point the module's seams at the fake install; returns (clone, bkp, managed)."""
    clone = _clone(tmp_path)
    bkp, managed = _install(tmp_path, live=live)
    if live:                                                   # the .mdb pdb2mdb writes beside each
        for mgd in managed.values():
            for dll in bm.DLLS:
                (pathlib.Path(mgd) / (dll + ".mdb")).write_bytes(b"MDB-" + dll.encode())
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


def test_no_deploy_refused_when_a_sibling_deploy_is_ungated(tmp_path, capsys, monkeypatch):
    """The pre-s91 clone: s45 gated Assembly-CSharp's AfterBuild, but msbuild builds the
    ProjectReferences first and Memoria.Prime + UnityEngine.UI each deploy from their OWN
    unconditional AfterBuild -- every 'compile-check' rewrote their live .dll + .mdb, unbacked.
    Reading only the root csproj passed that clone; the wrapper must read the closure."""
    runner = _Runner()
    _wire(monkeypatch, tmp_path, runner)
    pre_s91 = _clone(tmp_path / "pre-s91", dwix=True, siblings=False)
    rc = bm.main(["build_memoria.py", "--clone", str(pre_s91), "--no-deploy"])
    out = capsys.readouterr().out
    assert rc == 2 and runner.msbuild_calls() == []
    assert "--no-deploy REFUSED" in out
    assert "ungated  Memoria.Prime/Memoria.Prime.csproj: AfterBuild" in out
    assert "ungated  UnityEngine.UI/UnityEngine.UI.csproj: AfterBuild" in out
    assert "Assembly-CSharp.csproj" not in out.split("REFUSED", 1)[1].split("Apply", 1)[0]  # s45's is fine


def test_gate_audit_walks_the_reference_closure(tmp_path):
    csproj = _clone(tmp_path / "ok") / "Assembly-CSharp" / "Assembly-CSharp.csproj"
    gated, ungated, problems = bm.deploy_gate_audit(str(csproj))
    assert gated == ["Assembly-CSharp/Assembly-CSharp.csproj: AfterBuild",
                     "Memoria.Prime/Memoria.Prime.csproj: AfterBuild",
                     "UnityEngine.UI/UnityEngine.UI.csproj: AfterBuild"]   # XInput's is a comment
    assert ungated == [] and problems == []
    # a referenced project that cannot be read is unverifiable -> refused, never assumed gated
    (tmp_path / "ok" / "Memoria" / "UnityEngine.UI" / "UnityEngine.UI.csproj").unlink()
    _, _, problems = bm.deploy_gate_audit(str(csproj))
    assert [p for p in problems if p.startswith("UnityEngine.UI/UnityEngine.UI.csproj: unreadable")]
    assert not bm.no_deploy_supported(str(csproj))
    # a parse that finds NO Deploy at all cannot promise anything (the check must be able to fail)
    bare = tmp_path / "bare" / "A" / "A.csproj"
    _csproj(bare, gated=True, deploy=False)
    assert bm.deploy_gate_audit(str(bare))[2] and not bm.no_deploy_supported(str(bare))
    # the gate may sit on the Deploy element itself instead of its Target
    own = tmp_path / "own" / "A" / "A.csproj"
    own.parent.mkdir(parents=True)
    own.write_text(f'<Project><Target Name="AfterBuild"><Deploy {_GATE} /></Target></Project>', encoding="utf-8")
    assert bm.no_deploy_supported(str(own))


def test_no_deploy_builds_without_backup_and_passes_the_property(tmp_path, capsys, monkeypatch):
    runner = _Runner()
    clone, bkp, _ = _wire(monkeypatch, tmp_path, runner)
    rc = bm.main(["build_memoria.py", "--clone", str(clone), "--no-deploy"])
    assert rc == 0
    (call,) = runner.msbuild_calls()
    assert call[-1] == "-p:DWIXNoDeploy=true"
    out = capsys.readouterr().out
    n = len(bm.DLLS) * 2 * len(bm.ARCHES)                      # each DLL + its .mdb, every arch
    assert f"NOTHING deployed -- verified: all {n} live engine files" in out
    assert "byte-identical before and after the build." in out
    assert list(pathlib.Path(bkp).iterdir()) == []             # no snapshot taken (nothing at risk)


def test_no_deploy_tripwire_catches_a_leaked_mdb(tmp_path, capsys, monkeypatch):
    """The OBSERVED leak (2026-09-26): identical DLL bytes, a freshly generated .mdb every run.
    The .mdb is what shows a deploy of unchanged DLLs -- so the tripwire must fingerprint it."""
    runner = _Runner()
    clone, bkp, managed = _wire(monkeypatch, tmp_path, runner)
    mdb = pathlib.Path(managed["x86"]) / "UnityEngine.UI.dll.mdb"
    runner.on_msbuild = lambda: mdb.write_bytes(b"FRESH-PDB2MDB-OUTPUT")
    rc = bm.main(["build_memoria.py", "--clone", str(clone), "--no-deploy"])
    out = capsys.readouterr().out
    assert rc == 4
    assert "--no-deploy DEPLOYED ANYWAY" in out and "NOTHING deployed" not in out
    assert "CHANGED  UnityEngine.UI.dll.mdb [x86]" in out
    assert out.count("CHANGED  ") == 1
    assert "only .mdb debug symbols" in out
    assert list(pathlib.Path(bkp).iterdir()) == []             # an .mdb is not a restorable backup


def test_no_deploy_tripwire_keeps_the_drifted_dll_so_it_can_be_restored(tmp_path, capsys, monkeypatch):
    runner = _Runner()
    clone, bkp, managed = _wire(monkeypatch, tmp_path, runner)
    live = pathlib.Path(managed["x64"]) / "Memoria.Prime.dll"
    original = live.read_bytes()
    runner.on_msbuild = lambda: live.write_bytes(b"IN-FLIGHT-LOG.CS-EDIT")    # the s56 file, pushed live
    rc = bm.main(["build_memoria.py", "--clone", str(clone), "--no-deploy"])
    out = capsys.readouterr().out
    assert rc == 4 and "CHANGED  Memoria.Prime.dll [x64]" in out
    (kept,) = pathlib.Path(bkp).iterdir()
    assert kept.read_bytes() == original
    ts = out.split("restore_memoria_dll.py ", 1)[1].split()[0]
    # the printed selector finds exactly that file, routed to the arch it came from
    assert bm.find_backups("Memoria.Prime.dll", ts, bkp) == {"x64": str(kept)}
    assert bm.find_backups("Assembly-CSharp.dll", ts, bkp) == {}


def test_no_deploy_tripwire_also_runs_when_the_build_fails(tmp_path, capsys, monkeypatch):
    """msbuild builds (and deploys) the siblings BEFORE Assembly-CSharp compiles, so a compile
    error does not mean nothing landed."""
    runner = _Runner(rc=1)
    clone, _, managed = _wire(monkeypatch, tmp_path, runner)
    runner.on_msbuild = lambda: (pathlib.Path(managed["x64"]) / "Memoria.Prime.dll.mdb").write_bytes(b"NEW")
    rc = bm.main(["build_memoria.py", "--clone", str(clone), "--no-deploy"])
    out = capsys.readouterr().out
    assert rc == 4
    assert "DEPLOYED ANYWAY" in out and "build FAILED" in out


def test_s91_gates_exactly_the_two_sibling_afterbuild_targets():
    """Pin the capture: s91 changes one line in each sibling csproj -- its AfterBuild gains the
    s45 condition -- and nothing else."""
    patch = (REPO / "memoria-patches" / "s91-sibling-afterbuild-nodeploy.patch").read_bytes().decode("utf-8")
    heads = [ln[6:] for ln in patch.splitlines() if ln.startswith("+++ b/")]
    assert heads == ["Memoria.Prime/Memoria.Prime.csproj", "UnityEngine.UI/UnityEngine.UI.csproj"]
    minus = [ln for ln in patch.splitlines() if ln.startswith("-") and not ln.startswith("---")]
    plus = [ln for ln in patch.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    assert [m.strip() for m in minus] == ['-  <Target Name="AfterBuild">'] * 2
    assert len(plus) == 2 and all(bm.NO_DEPLOY_GATE.search(p) and 'Target Name="AfterBuild"' in p for p in plus)
    assert "\r\n" in patch                                     # CRLF kept, like the csprojs


def test_the_shared_clone_gates_every_deploy_it_builds():
    """The real clone (when present) must carry s45 + s91: a clone without them makes every
    `build_memoria.py --no-deploy` refuse, and every raw -p:DWIXNoDeploy=true build deploy."""
    csproj = pathlib.Path(bm.DEFAULT_CLONE) / "Assembly-CSharp" / "Assembly-CSharp.csproj"
    if not csproj.is_file():
        pytest.skip(f"no Memoria clone at {bm.DEFAULT_CLONE}")
    gated, ungated, problems = bm.deploy_gate_audit(str(csproj))
    assert ungated == [] and problems == []
    assert {g.split(":")[0] for g in gated} >= {"Assembly-CSharp/Assembly-CSharp.csproj",
                                                "Memoria.Prime/Memoria.Prime.csproj",
                                                "UnityEngine.UI/UnityEngine.UI.csproj"}


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
