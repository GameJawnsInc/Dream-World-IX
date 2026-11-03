"""The s164 bench hardening's tooling: THE BENCH GUARD (tools/harness/benchguard.py: a live bench refuses to start under a
running test suite -- the nightly gate's lock, or a live pytest) and THE RELEASE GATE (tools/harness/release_gate.py: every
regression report must name the final Assembly-CSharp.dll; Session's report.json and duo.json now carry it).

Every seam is pinned: no test reads the real gate lock, lists the real process table or hashes the live install's DLL.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import zipfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from harness import Session                                        # noqa: E402
from harness import benchguard as BG                               # noqa: E402
from harness import duo as D                                       # noqa: E402
from harness import release_gate as RG                             # noqa: E402
from harness.fakegame import FakeGame                              # noqa: E402

PY = r'"C:\Python\python.exe"'
PYTEST_LINES = [f"{PY} -m pytest -q -n 6 tests/test_coop_field_swap_timing_bench.py",
                f"{PY} -u -c \"import sys;exec(eval(sys.stdin.readline()))\"",          # an xdist (execnet) worker
                r"C:\Python\Scripts\pytest.exe -q tests",
                "py.test tests/test_x.py",
                "/usr/bin/python3 -m pytest -x"]
OTHER_LINES = [f"{PY} tools/play.py studies/test-harness/scenarios/coop_step_out.py --instance C:\\gd\\ff9-inst\\host",
               f"{PY} tools/harness/duo.py coop_field_swap_timing_duo.py",
               f"{PY} -m ff9mapkit build field.toml",
               f"{PY} tools/nightly_gate.py --dry-run",
               f"{PY} -c \"print('test_harness_pytestish')\"",
               ""]


# --------------------------------------------------------------------------------------------- THE BENCH GUARD
def test_a_pytest_command_line_is_told_from_a_bench_or_a_tool():
    assert all(BG.is_pytest(c) for c in PYTEST_LINES), [c for c in PYTEST_LINES if not BG.is_pytest(c)]
    assert not any(BG.is_pytest(c) for c in OTHER_LINES), [c for c in OTHER_LINES if BG.is_pytest(c)]


def test_the_cim_listing_parses_one_many_none_and_garbage():
    one = json.dumps({"ProcessId": 7, "ParentProcessId": 1, "CommandLine": "py -c \"\nx\""})
    many = json.dumps([{"ProcessId": 7, "ParentProcessId": 1, "CommandLine": None}, {"ProcessId": "x"},
                       {"ProcessId": 8, "ParentProcessId": 7, "CommandLine": "python -m pytest"}])
    assert BG.parse_cim_json(one) == [(7, 1, "py -c \"\nx\"")]
    assert BG.parse_cim_json(many) == [(7, 1, ""), (8, 7, "python -m pytest")]
    assert BG.parse_cim_json("") == [] and BG.parse_cim_json("not json") is None


def _lock(tmp_path, doc) -> pathlib.Path:
    p = tmp_path / ".test-gate" / "lock"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
    return p


def test_the_gate_lock_refuses_unless_its_holder_is_provably_dead(tmp_path):
    live = _lock(tmp_path, {"pid": 4242, "started": "2026-10-30T04:00:01"})
    ref, notes = BG.bench_blockers(lock=live, procs=lambda: [], alive=lambda pid: True, me=(1,))
    assert len(ref) == 1 and "nightly test gate is running" in ref[0] and "pid 4242" in ref[0] and notes == [], ref
    ref, notes = BG.bench_blockers(lock=live, procs=lambda: [], alive=lambda pid: False, me=(1,))
    assert ref == [] and len(notes) == 1 and "stale gate lock" in notes[0], notes
    garbled = _lock(tmp_path, "{half a json")
    ref, _ = BG.bench_blockers(lock=garbled, procs=lambda: [], alive=lambda pid: False, me=(1,))
    assert len(ref) == 1 and "cannot be read" in ref[0], ref
    ref, notes = BG.bench_blockers(lock=tmp_path / "absent" / "lock", procs=lambda: [], me=(1,))
    assert ref == [] and notes == []


def test_a_live_pytest_refuses_and_names_itself_but_never_this_process(tmp_path):
    nolock = tmp_path / "none"
    rows = [(10, 1, PYTEST_LINES[0]), (11, 10, PYTEST_LINES[1]), (12, 1, OTHER_LINES[0]), (99, 1, PYTEST_LINES[0])]
    ref, _ = BG.bench_blockers(lock=nolock, procs=lambda: rows, alive=lambda pid: True, me=(99, 98))
    assert len(ref) == 1 and "2 pytest process(es)" in ref[0] and "pid 10:" in ref[0] and "pid 11:" in ref[0], ref
    assert "pid 99" not in ref[0] and "ORPHANED xdist worker" in ref[0], ref
    ref, notes = BG.bench_blockers(lock=nolock, procs=lambda: None, me=(99,))
    assert ref == [] and notes == ["the process probe could not list processes: a live pytest run is unchecked"]


def test_an_exited_pytest_still_listed_is_noted_never_refused(tmp_path):
    """2026-11-02: an xdist worker whose launcher died had EXITED but stayed in the process table (another process held a
    handle to it) and refused every bench. A listed pytest that is not alive is a note; a live one beside it still refuses."""
    nolock = tmp_path / "none"
    rows = [(10, 1, PYTEST_LINES[1]), (11, 1, PYTEST_LINES[0])]
    ref, notes = BG.bench_blockers(lock=nolock, procs=lambda: rows, alive=lambda pid: False, me=(99,))
    assert ref == [] and len(notes) == 2 and all("exited pytest process is still listed" in n for n in notes), notes
    assert "pid 10" in notes[0] and "pid 11" in notes[1], notes
    ref, notes = BG.bench_blockers(lock=nolock, procs=lambda: rows, alive=lambda pid: pid == 11, me=(99,))
    assert len(ref) == 1 and "1 pytest process(es)" in ref[0] and "pid 11:" in ref[0] and "pid 10:" not in ref[0], ref
    assert len(notes) == 1 and "pid 10" in notes[0], notes


@pytest.mark.skipif(sys.platform != "win32", reason="the Windows exited-but-held process entry")
def test_pid_alive_reads_an_exited_process_held_open_as_dead():
    """The real probe on a real case: a child that has exited while its Popen still holds the process handle (so the
    process object -- and OpenProcess -- outlives it) is not alive; this process is."""
    import subprocess
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    try:
        child.wait(timeout=60)
        assert BG.pid_alive(child.pid) is False
    finally:
        del child
    assert BG.pid_alive(os.getpid()) is True


def test_the_gate_lock_is_the_main_repos_from_any_checkout():
    lock = BG.gate_lock_path()
    assert lock.name == "lock" and lock.parent.name == ".test-gate"
    assert (lock.parent.parent / ".git").exists(), f"{lock} is not under the main repo (the one that owns .git)"


def _load_play():
    spec = importlib.util.spec_from_file_location("play_under_test", REPO / "tools" / "play.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_play_refuses_to_start_under_a_running_suite(tmp_path, capsys):
    """Before the scenario is loaded (a missing file would raise) or anything launched: exit 2 with the reasons."""
    play = _load_play()
    play.bench_blockers = lambda: (["the nightly test gate is running: X"], ["a note"])
    assert play.main([str(tmp_path / "no_such_scenario.py")]) == 2
    err = capsys.readouterr()
    assert "NEVER BENCH UNDER A RUNNING TEST SUITE" in err.err and "the nightly test gate is running: X" in err.err
    assert "[play] note: a note" in err.out


def test_duo_refuses_to_start_under_a_running_suite(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(D, "bench_blockers", lambda: (["1 pytest process(es) are running (pid 10: x)"], []))
    assert D.main([str(tmp_path / "no_such_scenario.py")]) == 2
    assert "1 pytest process(es) are running" in capsys.readouterr().err


# --------------------------------------------------------------------------------------------- THE RELEASE GATE
FINAL = hashlib.sha256(b"the final dll").hexdigest()
OLD = hashlib.sha256(b"an earlier build").hexdigest()


def _session_run(root: pathlib.Path, name: str, sha: str | None, *, where: str = "report", verdict: str = "pass") -> pathlib.Path:
    run = root / name
    run.mkdir(parents=True)
    block = {"path": "x", "exists": sha is not None, "sha256": sha}
    rep = {"verdict": verdict}
    if where == "report":
        rep["assembly_csharp"] = block
    (run / "report.json").write_text(json.dumps(rep), encoding="utf-8")
    if where == "env":
        (run / "env.json").write_text(json.dumps({"engine": {"assembly_csharp": block}}), encoding="utf-8")
    return run


def _duo_run(root: pathlib.Path, name: str, shas: dict, *, recorded: bool = True) -> pathlib.Path:
    run = root / name
    run.mkdir(parents=True)
    dirs = {}
    for role, sha in shas.items():
        dirs[role] = str(_session_run(run, role, sha, where="env"))
    doc = {"verdict": "fail", "session_run_dirs": dirs}
    if recorded:
        doc["assembly_csharp"] = {r: {"sha256": s} for r, s in shas.items()}
    (run / "duo.json").write_text(json.dumps(doc), encoding="utf-8")
    return run


def test_the_release_gate_refuses_unless_every_report_names_the_final_dll(tmp_path):
    runs = tmp_path / "runs"
    _session_run(runs, "a-solo", FINAL)
    _session_run(runs, "b-solo-env-only", FINAL, where="env")            # a run from before report.json carried it
    _duo_run(runs, "c-duo", {"host": FINAL, "guest": FINAL})
    _duo_run(runs, "d-duo-old", {"host": FINAL, "guest": FINAL}, recorded=False)
    rows = RG.collect(runs)
    assert len(rows) == 6 and all(r["sha"] == FINAL for r in rows), rows
    ok, lines = RG.judge_release(FINAL[:16], rows)
    assert ok and lines[-1].startswith("6 of 6 report(s) name the final DLL"), lines
    _session_run(runs, "e-solo-older", OLD)
    _session_run(runs, "f-solo-unhashed", None)
    _duo_run(runs, "g-duo-mixed", {"host": FINAL, "guest": OLD})
    ok, lines = RG.judge_release(FINAL, RG.collect(runs))
    refused = [ln for ln in lines if ln.startswith("REFUSE")]
    assert not ok and len(refused) == 3, lines
    assert any("e-solo-older" in ln and "drove " + OLD[:16] in ln for ln in refused)
    assert any("f-solo-unhashed" in ln and "names no DLL" in ln for ln in refused)
    assert any("g-duo-mixed [guest]" in ln for ln in refused)
    assert RG.judge_release(FINAL, [])[0] is False
    assert RG.judge_release(FINAL[:8], RG.collect(runs / "a-solo"))[0] is False      # too short a prefix to trust


def test_the_release_gate_reads_a_bundle_zip_and_exits_by_its_verdict(tmp_path, capsys):
    bundle = tmp_path / "dwix-custom-memoria-test.zip"
    with zipfile.ZipFile(bundle, "w") as z:
        z.writestr("dwix/" + RG.DLL_IN_BUNDLE, b"the final dll")
        z.writestr("dwix/x86/FF9_Data/Managed/Assembly-CSharp.dll", b"the x86 build")
    assert RG.final_sha(bundle) == FINAL
    runs = tmp_path / "runs"
    _session_run(runs, "a", FINAL)
    assert RG.main([str(runs), "--dll", str(bundle)]) == 0 and "RELEASE GATE: PASS" in capsys.readouterr().out
    _session_run(runs, "b", OLD)
    assert RG.main([str(runs), "--sha", FINAL[:16]]) == 1 and "RELEASE GATE: REFUSED" in capsys.readouterr().out
    assert RG.main([str(runs), "--dll", str(tmp_path / "missing.zip")]) == 2


@pytest.fixture
def game(tmp_path):
    (tmp_path / "x64").mkdir()
    (tmp_path / "x64" / "FF9.exe").write_bytes(b"MZ")
    (tmp_path / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (tmp_path / "FF9CustomMap").mkdir()
    (tmp_path / "FF9CustomMap" / "DictionaryPatch.txt").write_text("", encoding="utf-8")
    return tmp_path


def test_a_sessions_report_names_the_dll_it_drove(game):
    """Session hashes the x64 Assembly-CSharp.dll before the launch (write_env) and report.json carries it beside env.json, so the
    release gate needs no second file."""
    managed = game / "x64" / "FF9_Data" / "Managed"
    managed.mkdir(parents=True)
    (managed / "Assembly-CSharp.dll").write_bytes(b"the final dll")
    fake = FakeGame(game)
    with Session(game_path=game, run_dir=game / "run", save_dir=game / "player-saves", pid_probe=lambda: [],
                 launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=False) as g:
        g.check(True, "a check")
    rep = json.loads((game / "run" / "report.json").read_text(encoding="utf-8"))
    assert rep["assembly_csharp"]["sha256"] == FINAL, rep.get("assembly_csharp")
    assert RG.collect(game / "run")[0]["source"] == "report.json"
