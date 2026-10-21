"""The ``slow_leg`` marker (tests/_slow_leg.py, applied by tests/conftest.py at collection) holds what it claims: every leg it
registers is a test its file defines (a rename reads MISSING, never silently unmarked), the story-trace rule takes the O4-O8
drives and rehearsals on the fake and none of those rungs' pure tests, and the mark reaches pytest's ``-m`` -- set BEFORE
the deselection reads it, so ``-m "not slow_leg"`` and ``-m slow_leg`` split a file exactly."""
import ast
import os
import pathlib
import subprocess
import sys

from ._slow_leg import LEGS, STORY_DRIVES, STORY_FILE, STORY_FIXTURE, is_slow_leg

HERE = pathlib.Path(__file__).resolve().parent


def _tests_of(path: pathlib.Path) -> dict:
    """{top-level test function: its argument names} of a test file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name: [a.arg for a in n.args.args] for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}


def missing_legs(legs: dict) -> list:
    """Every registered ``file::name`` its file does not define as a top-level test (or whose file is gone)."""
    out = []
    for f, names in legs.items():
        p = HERE / f
        have = _tests_of(p) if p.is_file() else {}
        out += [f"{f}::{n}" for n in names if n not in have]
    return out


def test_every_registered_leg_is_a_test_its_file_defines():
    assert missing_legs(LEGS) == []
    assert all(names and len(set(names)) == len(names) for names in LEGS.values()), LEGS
    # the check can fail: a renamed leg, a moved file
    assert missing_legs({"test_coop_leader_guard.py": ("test_no_such_leg",)}) == [
        "test_coop_leader_guard.py::test_no_such_leg"]
    assert missing_legs({"test_no_such_file.py": ("test_x",)}) == ["test_no_such_file.py::test_x"]


def test_the_story_rule_takes_the_drives_on_the_fake_and_nothing_pure():
    tests = _tests_of(HERE / STORY_FILE)
    picked = {n for n, args in tests.items() if is_slow_leg(STORY_FILE, n, args)}
    assert picked and all(STORY_DRIVES.match(n) and STORY_FIXTURE in tests[n] for n in picked)
    for rung in range(4, 9):                                    # every rung with a rehearsal has its drives marked
        assert any(n.startswith(f"test_o{rung}_") for n in picked), rung
    # a same-rung pure test (no stand-in) stays in every subset; a story test outside O4-O8 too
    assert "test_o4_rehearsal_gate_reads_the_pair_on_the_fake" in picked
    for pure in ("test_o8_rehearsal_stage_ids_follow_the_chain", "test_o4_read_gap_void_reads_the_zone_reason_alone",
                 "test_o2_drive_walks_its_table_to_the_end"):
        assert pure in tests and pure not in picked, pure
    assert STORY_FILE not in LEGS                               # one mechanism a file: the rule owns test_harness.py
    # the same name in any other file is not a story drive
    assert not is_slow_leg("test_harness_netsync.py", "test_o4_drive_scores_100_on_the_fake", ["game"])


def _collect(*args) -> set:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
    out = subprocess.run([sys.executable, "-m", "pytest", "tests/test_coop_leader_guard.py", "--collect-only", "-q",
                          "-p", "no:cacheprovider", *args], cwd=HERE.parent, env=env, capture_output=True, text=True,
                         timeout=300)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    return {ln.strip() for ln in out.stdout.splitlines() if "::" in ln}


def test_the_marker_reaches_minus_m_before_the_deselection():
    whole, slow, rest = _collect(), _collect("-m", "slow_leg"), _collect("-m", "not slow_leg")
    assert slow and rest and slow | rest == whole and not slow & rest
    assert {n.split("::")[1].split("[")[0] for n in slow} == set(LEGS["test_coop_leader_guard.py"])
