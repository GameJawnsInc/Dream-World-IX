"""The nightly gate's own honesty (tools/nightly_gate.py) -- Lane C of the 2026-08 adversarial review.

The gate is the trust artifact every session reads before building on master, so its failure modes are
the systemic ones: a guard that rots as the suite grows, a non-verdict run overwriting the real verdict,
a collection error minting smoke-ok. These tests exercise the module's pure helpers directly (the script
has a real main() and imports clean); the orchestration is pinned by source asserts where execution would
need git + a provisioned worktree.
"""

import importlib.util
import json
from pathlib import Path

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
