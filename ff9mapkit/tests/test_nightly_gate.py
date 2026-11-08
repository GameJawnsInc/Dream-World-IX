"""The nightly gate's own honesty (tools/nightly_gate.py) -- Lane C of the 2026-08 adversarial review.

The gate is the trust artifact every session reads before building on master, so its failure modes are
the systemic ones: a guard that rots as the suite grows, a non-verdict run overwriting the real verdict,
a collection error minting smoke-ok. These tests exercise the module's pure helpers directly (the script
has a real main() and imports clean); the orchestration is pinned by source asserts where execution would
need git + a provisioned worktree.
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("nightly_gate", REPO / "tools" / "nightly_gate.py")
ng = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ng)

_SRC = (REPO / "tools" / "nightly_gate.py").read_text(encoding="utf-8")


def _quiet(_msg):
    pass


def _ledger(state: Path, rows):
    state.mkdir(parents=True, exist_ok=True)
    (state / "ledger.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# ---- the collect floor must ratchet with the suite (the guard that ROTTED) -------------------------
def test_effective_floor_ratchets_to_the_last_full_green(tmp_path):
    """THE ROT: the static default (6500) was seeded when the suite was ~6.9k and never raised while it
    grew to 8418 -- so the floor admitted a ~1900-test silent drop, 4x the 479-test worktree skip-trap it
    was BUILT to catch (nightly_gate.md's own 'raise it as collected rises' law, unenforced). The
    effective floor derives from the gate's own ledger: 98% of the last full green's collection."""
    _ledger(tmp_path, [
        {"result": "green", "mode": "full", "collected": 8418},
    ])
    assert ng.effective_collect_floor(6500, tmp_path, _quiet) == int(8418 * 0.98)


def test_effective_floor_ignores_non_baseline_rows(tmp_path):
    # narrowed runs collect their filter, smoke runs collect nothing new, red runs may have died early --
    # none is a baseline. Malformed lines are tolerated (the file is append-only across crashes).
    _ledger(tmp_path, [
        {"result": "green", "mode": "full", "collected": 8418},
        {"result": "red", "mode": "full", "collected": 9999},
        {"result": "green", "mode": "narrowed", "collected": 12},
        {"result": "smoke-ok", "mode": "smoke", "collected": 8500},
    ])
    (tmp_path / "ledger.jsonl").open("a", encoding="utf-8").write("{not json\n")
    assert ng.last_green_collected(tmp_path) == 8418


def test_effective_floor_falls_back_to_static(tmp_path):
    assert ng.effective_collect_floor(6500, tmp_path, _quiet) == 6500          # no ledger at all
    _ledger(tmp_path, [{"result": "green", "mode": "full", "collected": 6000}])
    assert ng.effective_collect_floor(6500, tmp_path, _quiet) == 6500          # dynamic below static


def test_main_wires_the_dynamic_floor_and_records_it():
    # the helper existing is not the guard -- main() must SPEND it, record the effective floor in the
    # ledger entry, and keep --no-dynamic-floor as the deliberate shrink escape hatch.
    assert "effective_collect_floor(args.collect_floor, state, log)" in _SRC
    assert 'entry["collect_floor"]' in _SRC
    assert "no_dynamic_floor" in _SRC


# ---- a collection ERROR must never mint a healthy verdict ------------------------------------------
def test_collect_error_aborts_before_the_floor_check():
    """A module that fails to import leaves a floor-clearing count while part of the suite silently is
    not in it. In --smoke mode nothing downstream would ever surface that (the old code logged the rc and
    dropped it -> smoke-ok over a broken collection)."""
    assert '"collect-error"' in _SRC
    assert _SRC.index('"collect-error"') < _SRC.index('"collect-short"'), \
        "the collect-error abort must run before the floor comparison"


# ---- latest.json is a VERDICT file: only full runs may write it ------------------------------------
def test_run_mode_classifies_narrowed_and_smoke():
    assert ng.run_mode(True, None) == "smoke"
    assert ng.run_mode(False, "-k foo") == "narrowed"
    assert ng.run_mode(False, None) == "full"


def test_smoke_and_narrowed_never_overwrite_latest(tmp_path):
    """THE LIVE INCIDENT (2026-08-05, nightly_gate.md): a narrowed verification run flipped latest.json
    to skip-long and had to be restored BY HAND. And a smoke run overwrote the last real verdict with
    smoke-ok -- which the post-merge hook presented as calmly as green. latest.json keeps the last FULL
    verdict; everything still lands in ledger.jsonl."""
    ng.write_ledger(tmp_path, {"result": "green", "mode": "full", "collected": 8418}, _quiet)
    ng.write_ledger(tmp_path, {"result": "smoke-ok", "mode": "smoke"}, _quiet, update_latest=False)
    ng.write_ledger(tmp_path, {"result": "skip-long", "mode": "narrowed"}, _quiet, update_latest=False)
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert latest["result"] == "green" and latest["mode"] == "full"
    rows = [json.loads(ln) for ln in (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["result"] for r in rows] == ["green", "smoke-ok", "skip-long"]   # history keeps everything


def test_latest_json_write_is_staged_and_replaced(tmp_path):
    # the hook reads latest.json at every merge into master -- it must never observe a half-written file
    ng.write_ledger(tmp_path, {"result": "green", "mode": "full"}, _quiet)
    assert not (tmp_path / "latest.json.tmp").exists()
    assert "os.replace(tmp, state" in _SRC


def test_main_gates_latest_on_full_mode():
    assert 'update_latest=entry.get("mode") == "full"' in _SRC
    assert "run_mode(args.smoke, args.pytest_args)" in _SRC


def test_full_run_checks_the_hook_is_still_installed():
    # the hook is the ledger's delivery mechanism and is untracked -- its silent loss must be noticed
    assert '"post-merge"' in _SRC and 'entry["hook"]' in _SRC


# ---- the post-merge hook TEMPLATE (nightly_gate.md is its only backup -- hooks are untracked) ------
def _hook_template() -> str:
    md = (REPO / "tools" / "nightly_gate.md").read_text(encoding="utf-8")
    inside, lines = False, []
    for ln in md.splitlines():
        if ln.strip() == "```sh":
            inside = True
            continue
        if inside and ln.strip() == "```":
            break
        if inside:
            lines.append(ln)
    assert lines and lines[0].startswith("#!/bin/sh"), "the hook template sh fence has moved/vanished"
    return "\n".join(lines) + "\n"


def test_hook_template_is_valid_sh(tmp_path):
    import shutil as _sh
    import subprocess
    sh = _sh.which("sh")
    if sh is None:
        import pytest
        pytest.skip("no sh on PATH (Git Bash absent)")
    f = tmp_path / "post-merge"
    f.write_text(_hook_template(), encoding="utf-8", newline="\n")
    p = subprocess.run([sh, "-n", str(f)], capture_output=True, text=True)
    assert p.returncode == 0, f"the documented hook template does not parse: {p.stderr}"


def test_hook_template_judges_staleness_and_never_calms_smoke():
    """Lane C: (1) a green verdict DECAYS -- if the scheduled task silently dies, latest.json stays green
    forever and every merge reads yesterday's suite as today's, so the hook must judge the stamp's age;
    (2) smoke-ok is a NON-verdict and must never share green's calm one-liner (the old `green|smoke-ok)`
    branch presented an unknown suite state as healthy)."""
    t = _hook_template()
    assert "STALE" in t and "age_h" in t
    assert "green|smoke-ok)" not in t
    assert "SUITE HAS NOT RUN" in t


# ---- parse_summary (the counts the skip ceiling judges on) -----------------------------------------
def test_parse_summary_reads_the_final_pytest_line(tmp_path):
    log = tmp_path / "run.pytest.log"
    log.write_text("...\n1.23s call  test_x\n8395 passed, 23 skipped, 14 warnings in 979.60s\n",
                   encoding="utf-8")
    got = ng.parse_summary(log)
    assert got["passed"] == 8395 and got["skipped"] == 23
    log.write_text("2 failed, 8393 passed, 23 skipped, 1 error in 990.00s\n", encoding="utf-8")
    got = ng.parse_summary(log)
    assert got["failed"] == 2 and got["error"] == 1


# ---- the lint ratchet: the pyflakes count is frozen at the last full green; only an INCREASE judges ----
def test_parse_ruff_count_reads_the_three_transcript_shapes():
    assert ng.parse_ruff_count("cli.py:1738:16: F821 Undefined name `re`\nFound 109 errors.\n[*] 85 fixable") == 109
    assert ng.parse_ruff_count("Found 1 error.\n") == 1
    assert ng.parse_ruff_count("All checks passed!\n") == 0
    assert ng.parse_ruff_count("/usr/bin/python3: No module named ruff\n") is None   # absent = skipped, never red
    assert ng.parse_ruff_count("") is None


def test_lint_baseline_is_the_last_full_green_that_measured(tmp_path):
    # rows that PREDATE the field are skipped, not read as 0 -- the ratchet bootstraps from the first
    # run that measured; narrowed and red rows are not baselines, exactly as for the collect floor
    _ledger(tmp_path, [
        {"result": "green", "mode": "full", "collected": 8000},                  # predates ruff_f
        {"result": "green", "mode": "full", "collected": 8100, "ruff_f": 109},
        {"result": "green", "mode": "narrowed", "ruff_f": 5},
        {"result": "red", "mode": "full", "ruff_f": 90},
    ])
    assert ng.last_green_field(tmp_path, "ruff_f") == 109
    assert ng.last_green_field(tmp_path, "nothing") is None
    assert ng.last_green_collected(tmp_path) == 8100                             # the floor still reads its own


def test_main_wires_the_lint_ratchet_and_records_it():
    # measured in every mode, judged only on a green full run, with the deliberate one-run escape hatch
    assert 'entry["ruff_f"] = ruff_f_count(' in _SRC
    assert '"lint-up"' in _SRC
    assert "no_lint_ratchet" in _SRC
    assert _SRC.index('"lint-up"') > _SRC.index('"skip-long"'), \
        "the lint verdict sits beside the skip ceiling, after the suite -- never before it runs"


# ---- a KILLED run still names its failures (the 2026-11-07/08 timeouts named none) -------------------------
def _results(path: Path, rows, finish=None):
    lines = [json.dumps({"ev": "start", "pid": 1, "workers": 6})] + [json.dumps(r) for r in rows]
    if finish is not None:
        lines.append(json.dumps({"ev": "finish", "exitstatus": finish}))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_parse_results_counts_reports_the_way_pytest_does(tmp_path):
    """A failed call or an xdist worker crash (phase ``???``) is ``failed``; a failed setup/teardown or a collection
    error is ``error`` -- pytest's own summary-line arithmetic, so a killed run's counts read like a finished one's.
    No finish record = the run was killed; a torn last line (the kill landed mid-write) is skipped, not fatal."""
    p = tmp_path / "r.results.jsonl"
    _results(p, [
        {"id": "t/a.py::ok", "w": "call", "o": "passed", "d": 1.0, "s": 0.5},
        {"id": "t/a.py::bad", "w": "call", "o": "failed", "d": 2.0, "s": 0.0},
        {"id": "t/a.py::bad", "w": "teardown", "o": "failed", "d": 0.1},
        {"id": "t/b.py::fix", "w": "setup", "o": "failed", "d": 0.2},
        {"id": "t/b.py::skip", "w": "setup", "o": "skipped", "d": 0.0},
        {"id": "t/b.py::xf", "w": "call", "o": "xfailed", "d": 0.0, "s": 0.0},
        {"id": "t/c.py::hung", "w": "???", "o": "failed", "d": 0.0},
        {"id": "t/d.py", "w": "collect", "o": "failed"},
    ])
    with p.open("a", encoding="utf-8") as fh:
        fh.write('{"id": "t/e.py::torn", "w": "ca')
    got = ng.parse_results(p)
    assert (got["passed"], got["failed"], got["error"], got["skipped"], got["xfailed"]) == (1, 2, 3, 1, 1)
    assert got["failed_ids"] == ["t/a.py::bad", "t/c.py::hung"]
    assert got["error_ids"] == ["t/a.py::bad", "t/b.py::fix", "t/d.py"]
    assert got["finished"] is False and got["completed"] == 6
    assert got["slowest_files"][0] == ["t/a.py", 3.6]
    _results(p, [{"id": "t/a.py::ok", "w": "call", "o": "passed", "d": 1.0}], finish=0)
    assert ng.parse_results(p)["finished"] is True
    assert ng.parse_results(tmp_path / "absent.jsonl") == {}


def test_parse_results_caps_the_ids_and_says_how_many(tmp_path):
    p = tmp_path / "r.results.jsonl"
    _results(p, [{"id": f"t/a.py::f{i}", "w": "call", "o": "failed", "d": 0} for i in range(ng.MAX_IDS + 7)])
    got = ng.parse_results(p)
    assert len(got["failed_ids"]) == ng.MAX_IDS and got["failed_ids_total"] == ng.MAX_IDS + 7


def test_parse_short_summary_reads_a_complete_runs_names(tmp_path):
    # the fallback when the results log is absent: the shapes the 2026-11-03 red printed
    log = tmp_path / "run.pytest.log"
    log.write_text("....F [100%]\n=== short test summary info ===\n"
                   r"FAILED tests\test_coop_world_battle.py::test_the_solo_leg_is_green_on_the_s145_stand_in" "\n"
                   r"ERROR tests\test_x.py::test_y - RuntimeError: setup" "\n"
                   "1 failed, 1 error, 15550 passed in 9970.94s (2:46:10)\n", encoding="utf-8")
    got = ng.parse_short_summary(log)
    assert got["failed_ids"] == [r"tests\test_coop_world_battle.py::test_the_solo_leg_is_green_on_the_s145_stand_in"]
    assert got["error_ids"] == [r"tests\test_x.py::test_y"]
    log.write_text("....F [ 87%]\n", encoding="utf-8")                      # a killed run printed no summary
    assert ng.parse_short_summary(log) == {}


def test_prune_results_keeps_the_newest(tmp_path):
    for ts in ("20261101-030001", "20261102-030002", "20261103-030002"):
        (tmp_path / f"{ts}.results.jsonl").write_text("", encoding="utf-8")
        (tmp_path / f"{ts}.pytest.log").write_text("", encoding="utf-8")
    ng.prune_results(tmp_path, keep=2)
    assert sorted(p.name for p in tmp_path.glob("*.results.jsonl")) == [
        "20261102-030002.results.jsonl", "20261103-030002.results.jsonl"]
    assert len(list(tmp_path.glob("*.pytest.log"))) == 3                     # the text logs are never pruned


_STUB = '''
import os, time, pytest
def test_ok(): pass
def test_bad(): assert 0
@pytest.fixture
def boom(): raise RuntimeError("setup")
def test_setup_err(boom): pass
def test_hangs(request):
    open(os.environ["GATE_STUB_ROOT"], "w").write(str(request.config.rootpath))
    open(os.environ["GATE_STUB_PID"], "w").write(str(os.getpid()))
    time.sleep(600)
'''


def _stub_suite(tmp_path):
    """The stub suite in ``suite/`` and its results log in a SIBLING ``state/`` -- the nightly's own shape (the gate
    worktree's tests, the main repo's ``.test-gate/runs``), which is what exposed the two-token rootdir drift."""
    suite, state = tmp_path / "suite", tmp_path / "state"
    suite.mkdir()
    state.mkdir()
    (suite / "test_stub.py").write_text(_STUB, encoding="utf-8")
    env = dict(os.environ)
    env["GATE_STUB_PID"] = str(tmp_path / "worker.pid")
    env["GATE_STUB_ROOT"] = str(tmp_path / "worker.rootdir")
    results = state / "r.results.jsonl"
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(suite / "test_stub.py")]
    cmd += ng.plugin_args(results, env, _quiet)
    if importlib.util.find_spec("xdist") is not None:
        # the gate's shape (only the CONTROLLER writes); loadfile keeps the file's order, so the hang runs LAST
        cmd += ["-n", "2", "--dist", "loadfile"]
    return cmd, env, results, suite


def test_plugin_args_pass_the_log_path_as_one_token():
    """THE ROOTDIR DRIFT (found by the first forced-kill run through main(), 2026-11-08): ``--gate-results PATH`` as two
    tokens reads as a positional path in an xdist worker, whose rootdir then drifts to the common ancestor of the tests
    and the log -- for the nightly that is C:\\gd, and the workers stalled in collection: 0 tests ran in 45 s."""
    env = {}
    got = ng.plugin_args(Path("C:/state/runs/x.results.jsonl"), env, _quiet)
    assert got == ["-p", ng.PLUGIN_NAME, "--gate-results=" + str(Path("C:/state/runs/x.results.jsonl"))]
    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(ng.PLUGIN_DIR)


def test_a_killed_suite_still_names_what_failed_before_the_kill(tmp_path):
    """THE PROOF, end to end: a real pytest (under xdist when it is installed, as the gate runs it) with the plugin
    loaded the gate's way, one test hanging, killed by the gate's own ``run`` timeout. The kill must still leave the
    failure and the setup error NAMED, report the run unfinished -- and take the hung worker down with it (the
    2026-11-08 workers outlived their kill by three minutes). The worker's rootdir must be the SUITE's, not the common
    ancestor of the suite and the log (the two-token drift)."""
    cmd, env, results, suite = _stub_suite(tmp_path)
    assert "-p" in cmd and ng.PLUGIN_NAME in cmd, "the plugin must load through -p, from PLUGIN_DIR on PYTHONPATH"
    lines = []
    with pytest.raises(subprocess.TimeoutExpired):
        # cwd = the suite (no ini: pytest's rootdir is the common ancestor of cwd and the args), so a correct worker
        # roots at suite/ -- and the two-token drift roots it at tmp_path, the ancestor of the suite and the log
        ng.run(cmd, lines.append, cwd=suite, env=env, timeout=20, tee_to=tmp_path / "run.log")
    got = ng.parse_results(results)
    assert got["finished"] is False
    assert got["failed_ids"] == ["test_stub.py::test_bad"], (got, (tmp_path / "run.log").read_text())
    assert got["error_ids"] == ["test_stub.py::test_setup_err"]
    assert got["passed"] == 1
    assert Path((tmp_path / "worker.rootdir").read_text()) == suite, "the worker's rootdir drifted off the suite"
    pid_file = tmp_path / "worker.pid"
    assert pid_file.is_file(), "the hanging test never started -- the kill proved nothing"
    pid = int(pid_file.read_text())
    deadline = time.time() + 10
    while ng.pid_alive(pid) and time.time() < deadline:
        time.sleep(0.2)
    assert not ng.pid_alive(pid), f"the hung test's process {pid} outlived the kill (orphaned worker)"


def test_parse_results_sums_each_workers_busy_time(tmp_path):
    # the tail witness: a wide spread between workers is scheduling, not a slow suite
    p = tmp_path / "r.results.jsonl"
    _results(p, [{"id": "t/a.py::x", "w": "call", "o": "passed", "d": 10.0, "s": 1.0, "wk": "gw0"},
                 {"id": "t/a.py::y", "w": "call", "o": "passed", "d": 4.0, "s": 0.0, "wk": "gw1"},
                 {"id": "t/a.py::z", "w": "call", "o": "passed", "d": 2.0, "s": 0.0, "wk": "gw1"}])
    assert ng.parse_results(p)["worker_busy_s"] == {"gw0": 11, "gw1": 6}


def test_the_suite_cap_fits_inside_the_scheduled_tasks_limit():
    """THE TIME BUDGET: Task Scheduler kills the task at its ExecutionTimeLimit, and a kill there skips main()'s
    finally -- the night leaves no ledger row at all. So the default cap plus the pre-suite budget must fit inside the
    limit the task is REGISTERED with, and the registration must read the same constant (raising one alone breaks it)."""
    assert ng.DEFAULT_TIMEOUT_MIN + ng.PRESUITE_BUDGET_MIN <= ng.TASK_LIMIT_MIN
    assert ng.DEFAULT_TIMEOUT_MIN > 184, "the 2026-11-07 run needed ~184 min (98% at the old 180 cap)"
    assert "New-TimeSpan -Minutes {TASK_LIMIT_MIN}" in _SRC and "New-TimeSpan -Hours" not in _SRC
    assert "default=DEFAULT_TIMEOUT_MIN" in _SRC


def test_main_names_failures_on_both_paths():
    # the helpers existing is not the fix -- main() must load the plugin into the SUITE command, read the log in the
    # timeout branch (where the summary never printed), and also on a complete run
    assert "cmd += extra" in _SRC and "plugin_args(results, env, log)" in _SRC
    timeout_branch = _SRC[_SRC.index("except subprocess.TimeoutExpired:\n            entry[\"result\"] = \"timeout\""):]
    assert timeout_branch.index("parse_results(results)") < timeout_branch.index("return 1")
    assert "parse_short_summary(suite_log)" in _SRC
    assert "kill_tree(p.pid, log)" in _SRC
