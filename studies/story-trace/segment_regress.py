"""THE REGRESSION GATE for the shared segment machinery: every change to ``segment_trace``, ``segment_drive``,
``o2_alexandria`` or the harness verbs they drive must leave every O1 output (research/o2_design.md, section 1.6)
AND every O2 output (research/o3_design.md, section 1.4) byte-identical.

    py studies/story-trace/segment_regress.py --capture      # G0, once, BEFORE the O2 refactor: the O1 baseline
    py studies/story-trace/segment_regress.py --capture-o2   # G0', once, BEFORE any O3 code change: the O2 baseline
    py studies/story-trace/segment_regress.py                # G1-G12; exit 0 only if every item passes

Exit 2 means an archive or a baseline is missing: the gate was not run, which is not a pass.

The O1 items import only the O1 modules (``o1_opening``, ``o1_dryrun``), the O2 items only the O2 modules
(``o2_alexandria``, ``o2_dryrun``, imported inside their functions), each through its public names, so each baseline
was captured at the code before the change it guards and the same file judges the changed code:
  G0  --capture: the full ``(checks, report)`` of the archived PROVEN session o1e, of the archived VOID session
      o1d, of every o1_dryrun case (its 15 CASES and "predictions-changed"), of the G6 noise mutant, and
      ``offline_check(v4)``, plus the G7 tests collected -> ``research/o1_regress_baseline.json`` (LF, ``-text``).
      It refuses to overwrite a baseline, and to write one the pre-refactor code does not itself pass.
  G1  ``analyse(o1e, v4)``: the report is the archived ``o1_report.txt`` exactly, and the baseline's; the checks
      are the baseline's; PROVEN with 6 checks, all True.
  G2  the CLI ``o1_opening.py --analyse o1e --predictions v4`` exits 0 and prints that report.
  G3  every dry-run case's ``(checks, report)`` is byte-equal to the baseline's -- every detail and every report
      line, not only the verdicts ``o1_dryrun.result`` compares -- and ``run_cases(v4)`` still returns 0.
  G4  ``offline_check(v4)`` equals the baseline's ``[(ok, what, detail)]``.
  G5  o1d's ``(checks, report)`` is byte-equal to the baseline's: a real VOID path.
  G6  THE O1 NOISE MUTANT: ``six(v4)`` plus a FIELD-mode (m 1) ``Global.Byte[206]`` row in the F runs only reads
      O1-NULL False, O1-JOIN True, NOT PROVEN. O1's noise is ``{not_m: 1, target}``: it covers m != 1 only, so an
      ``is_noise`` widened to every mode reads PROVEN here. No stock store of ``Global.Byte[206]`` exists in 50 or
      in any of the chain's 20 donors, so no field-mode JOIN can key the row: it is an addition-buffer row
      (``add`` 1, ``tag`` -1), which ``storytrace.digest`` keys WITHOUT a join -- a field-mode ``Global.Byte[206]``
      key that reaches O1-NULL. Its ``(checks, report)`` is byte-equal to the baseline's too.
  G7  ``pytest tests/test_harness.py -k "o1_ or overlay_hint or segment"`` from ``ff9mapkit/``: every test passed,
      0 failed, 0 skipped, 0 errors; every test the baseline collected still runs, and so does every name in
      :data:`REQUIRED_TESTS`.
  G0' --capture-o2: the full ``(checks, report)`` of the archived PROVEN session story-o2 read with
      ``o2_predictions_v1``; of every o2_dryrun session case (its CASES and "predictions-changed"); every o2_dryrun
      unit case's and offline mutant's ``(name, ok, detail)``; ``offline_check(v1)``; the G12 tests collected; the
      HEAD and v1's sha -> ``research/o2_regress_baseline.json`` (LF, ``-text``). It refuses to overwrite a
      baseline, and to write one unless G8-G12's baseline-free halves pass at the code it captures.
  G8  ``O2.analyse(story-o2, pred_path=v1)``: the report is the archived ``o2_report.txt`` exactly, and the
      baseline's; the checks are the baseline's; PROVEN with 15 checks, all True.
  G9  the CLI ``o2_alexandria.py --analyse story-o2 --predictions v1`` exits 0 and prints that report.
  G10 every o2_dryrun session case's ``(checks, report)`` is byte-equal to the baseline's, every unit case's and
      offline mutant's ``(name, ok, detail)`` too, and ``run_cases(v1)`` still returns 0 printing "N/N cases as
      registered" (86 at the capture). The gate replicates run_cases's loop step for step, as G3 does O1's, so every
      session gets the label run_cases gives it (``s0``, ``s1``, ... in creation order).
      G10 IS THE ONLY VOID-PATH BASELINE O2 HAS: the story-o2 archive holds six covered runs and no VOID, so G8/G9
      never take the coverage rule's VOID or A-BEATS path, nor VOID-ASYM's. An edit to the coverage rule, the
      V-classes or VOID-ASYM is proven O2-neutral by G10's synthetic sessions alone.
  G11 ``O2.offline_check(v1)`` equals the baseline's ``[(ok, what, detail)]``: 5 checks, all PASS (it reads the O2
      build and the stock assets, read-only).
  G12 ``pytest tests/test_harness.py -k "o2_ or rehearse"`` from ``ff9mapkit/``: every test passed, 0 failed, 0
      skipped, 0 errors; every test the baseline collected still runs, and so does every name in
      :data:`REQUIRED_TESTS_O2`.

Nothing here touches the game or writes to the install: it reads the archives, the builds and the stock bytes.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import o1_opening as O                                                     # noqa: E402
import o1_dryrun as D                                                      # noqa: E402

V4 = HERE / "o1_predictions_v4.json"
O1E = Path(r"C:\gd\Dream-World-IX\.harness-runs\20260929-213149-story-o1e")
O1D = Path(r"C:\gd\Dream-World-IX\.harness-runs\20260929-212507-story-o1d")
BASELINE = HERE / "research" / "o1_regress_baseline.json"
PYTEST_K = "o1_ or overlay_hint or segment"
#: Tests G7 must find (and find passing) beyond the ones the baseline collected: each arrives with the PART A step
#: that adds it (research/o2_design.md section 9), so a later step cannot drop it silently.
REQUIRED_TESTS: tuple = (
    # A3: O1Segment.run keeps O1's session surface; the shared session loop and its THROW check, on the fake
    "test_o1_segment_run_pins_o1s_session_surface",
    "test_segment_session_loop_on_the_fake",
    "test_segment_throw_check_fails_on_an_engine_exception",
)

O1E_VERDICT = "PROVEN"
O1D_VERDICT = "VOID: O1-COVER, O1-LADDER, O1-NULL, O1-STABLE, O1-JOIN"
MUTANT_VERDICT = "NOT PROVEN: O1-NULL"

# -- O2 (research/o3_design.md 1.4): the frozen v1 predictions and the PROVEN story-o2 archive
V1 = HERE / "o2_predictions_v1.json"
O2S = Path(r"C:\gd\Dream-World-IX\.harness-runs\20260930-192740-story-o2")
BASELINE_O2 = HERE / "research" / "o2_regress_baseline.json"
PYTEST_K_O2 = "o2_ or rehearse"
#: Tests G12 must find (and find passing) beyond the ones the O2 baseline collected: each arrives with the step of
#: research/o3_design.md section 9 that adds it (B4's renamed no-registry test, C3's rehearse tests), so a later step
#: cannot drop it silently.
REQUIRED_TESTS_O2: tuple = ()

O2S_VERDICT = "PROVEN"
O2S_CHECKS = 15
O2_OFFLINE_CHECKS = 5


# ======================================================================== what the O1 code says
def _pair(checks, report) -> dict:
    return {"checks": [list(c) for c in checks], "report": report}


def analyse_archive(run_dir: Path) -> dict:
    checks, report = O.analyse(run_dir, pred_path=V4)
    return _pair(checks, report)


def dryrun_outputs(stock) -> tuple:
    """``({case: (checks, report)}, [case names in run order])`` -- ``o1_dryrun.run_cases``'s own loop, step for
    step: the same temp-directory sequence gives every case the session label run_cases gives it."""
    pred, _sha = O.load_predictions(V4)
    out, order = {}, []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, fn, _want_verdict, _want in D.CASES:
            d = D.make_session(tmp, V4, fn(copy.deepcopy(pred)))
            out[name] = _pair(*O.analyse(d, stock=stock))
            order.append(name)
        frozen_tmp = tmp / "pred_copy.json"
        frozen_tmp.write_bytes(V4.read_bytes())
        d = D.make_session(tmp, frozen_tmp, D.six(pred))
        frozen_tmp.write_bytes(V4.read_bytes() + b" ")
        out["predictions-changed"] = _pair(*O.analyse(d, stock=stock))
        order.append("predictions-changed")
    return out, order


def mutant_row(members: dict, f: int, value: int) -> dict:
    """G6's row: 50's e17, field mode, an addition-buffer store of Global.Byte[206] (keyed with no join), on the
    fork side (``fld`` = member(50), ``don`` = 50, as the engine writes it)."""
    r = D.row((50, 17, -1, 40, "Byte", 206, 0, value), side="F", members=members, f=f)
    r.update(add=1, tag=-1)
    return r


def noise_mutant(stock) -> dict:
    pred, _sha = O.load_predictions(V4)
    members = O.members_of(pred)
    value = random.Random(206).randrange(1, 256)          # one draw: the same key in every fork run
    runs = D.six(pred)
    for r in runs:
        if r["side"] == "F":
            r["rows"].insert(3, mutant_row(members, 205, value))
    with tempfile.TemporaryDirectory() as tmp:
        d = D.make_session(Path(tmp), V4, runs)
        return _pair(*O.analyse(d, stock=stock))


def offline() -> list:
    pred, _sha = O.load_predictions(V4)
    return [list(c) for c in O.offline_check(pred)]


def run_cases_quietly() -> tuple:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D.run_cases(V4)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else "")


def cli_analyse() -> tuple:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "o1_opening.py"), "--analyse", str(O1E), "--predictions",
                        str(V4)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout, p.stderr


def pytest_g7() -> dict:
    """Run G7's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K)


def pytest_selection(k: str) -> dict:
    """Run one ``-k`` selection of tests/test_harness.py; ``{"rc", "passed": [...], "failed": [...], "skipped":
    [...], "errors": [...]}`` read from its JUnit XML (the names, not a summary line)."""
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "g7.xml"
        p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_harness.py", "-q", "-p", "no:cacheprovider",
                            "-W", "ignore", "-k", k, f"--junitxml={xml}"],
                           cwd=str(ROOT / "ff9mapkit"), capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        out = {"rc": p.returncode, "passed": [], "failed": [], "skipped": [], "errors": [],
               "tail": (p.stdout + p.stderr)[-1500:]}
        if not xml.is_file():
            out["errors"].append("no JUnit XML written")
            return out
        for tc in ET.parse(xml).getroot().iter("testcase"):
            name = tc.get("name")
            kinds = {child.tag for child in tc}
            if "error" in kinds:
                out["errors"].append(name)
            elif "failure" in kinds:
                out["failed"].append(name)
            elif "skipped" in kinds:
                out["skipped"].append(name)
            else:
                out["passed"].append(name)
    return out


def _verdict(pair: dict) -> str:
    return O.verdict([tuple(c) for c in pair["checks"]])


def _result(pair: dict) -> dict:
    return {w.split(":")[0]: ok for ok, w, _d in pair["checks"]}


# ======================================================================== what the O2 code says
def _o2() -> tuple:
    """``(o2_alexandria, o2_dryrun)``: imported here, never at the module's top, so the O1 items import only O1's
    modules (research/o3_design.md 1.4)."""
    import o2_alexandria as A
    import o2_dryrun as D2
    return A, D2


def o2_analyse_archive() -> dict:
    A, _D2 = _o2()
    return _pair(*A.O2.analyse(O2S, pred_path=V1))


def o2_dryrun_outputs(stock) -> tuple:
    """``({case: (checks, report)}, [case names in run order], [[unit, ok, detail], ...])`` -- ``o2_dryrun.run_cases``'s
    own loop over V1, step for step: the same temporary layout (``pred/``, ``sessions/``), the same session
    directories in the same order (``s0``, ``s1``, ... -- each report's title carries its label), the same units in
    the same order (state-history's session is the last one made), the offline mutants on the same temporary root.
    Left out are only run_cases's verdict comparisons and its extra ``read_session`` reads of a case's VOID classes:
    pure reads that make no directory and leave nothing an output reads."""
    from ff9mapkit.content.verbatim import remap_fields
    A, D2 = _o2()
    out, order, units = {}, [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdir = tmp / "pred"
        pdir.mkdir()
        sdir = tmp / "sessions"
        sdir.mkdir()
        path = V1                                         # run_cases's _prepare(V1, pdir) is V1 itself
        pred, _sha = A.O2.load(path)
        members = D2.members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, *_want in D2.CASES:
            d = D2.make_session(sdir, path, fn(copy.deepcopy(pred)), scripts)
            out[name] = _pair(*A.O2.analyse(d, stock=stock))
            order.append(name)
        copy_path = pdir / "pred_copy.json"               # O2-FROZEN: the predictions changed after the session
        copy_path.write_bytes(path.read_bytes())
        d = D2.make_session(sdir, copy_path, D2.six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        out["predictions-changed"] = _pair(*A.O2.analyse(d, stock=stock))
        order.append("predictions-changed")
        for name, fn in (("span-selector", D2.unit_span_selector),
                         ("span-count-row", lambda: D2.unit_span_count_row(pred, stock)),
                         ("text-rule-defect", D2.unit_text_defect),
                         ("text-rule-session", D2.unit_text_session), ("text-rule-garbage", D2.unit_text_garbage),
                         ("trace-summary", lambda: D2.unit_trace_summary(pred, stock)),
                         ("state-history", lambda: D2.unit_state_history(pred, stock, scripts, sdir, path))):
            ok, detail = fn()
            units.append([name, ok, detail])
        for name, ok, detail in D2.unit_offline_mutants(pred, stock, tmp):
            units.append([name, ok, detail])
    return out, order, units


def o2_offline() -> list:
    A, _D2 = _o2()
    pred, _sha = A.O2.load(V1)
    return [list(c) for c in A.O2.offline_check(pred)]


def o2_run_cases_quietly() -> tuple:
    _A, D2 = _o2()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D2.run_cases(V1)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else "")


def o2_cli_analyse() -> tuple:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "o2_alexandria.py"), "--analyse", str(O2S), "--predictions",
                        str(V1)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout, p.stderr


def pytest_g12() -> dict:
    """Run G12's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K_O2)


def _verdict_o2(pair: dict) -> str:
    _A, D2 = _o2()
    return D2.verdict([tuple(c) for c in pair["checks"]])


# ======================================================================== the items
def _first_diff(a: str, b: str) -> str:
    la, lb = a.split("\n"), b.split("\n")
    for i, (x, y) in enumerate(zip(la, lb), 1):
        if x != y:
            return f"line {i}: {x[:140]!r} != {y[:140]!r}"
    return f"{len(la)} lines vs {len(lb)} lines"


def _same(got: dict, want: dict, what: str) -> list:
    bad = []
    if got["checks"] != want["checks"]:
        pairs = [(g, w) for g, w in zip(got["checks"], want["checks"]) if g != w]
        bad.append(f"{what} checks differ: {pairs[:1] or (len(got['checks']), len(want['checks']))}"[:400])
    if got["report"] != want["report"]:
        bad.append(f"{what} report differs at {_first_diff(got['report'], want['report'])}")
    return bad


def g1(base: dict, got: dict) -> tuple:
    bad = []
    archived = (O1E / "o1_report.txt").read_text(encoding="utf-8")
    if got["report"] != archived:
        bad.append(f"the report is not the archived o1_report.txt: {_first_diff(got['report'], archived)}")
    if base is not None:
        bad += _same(got, base["o1e"], "o1e")
    checks = got["checks"]
    if _verdict(got) != O1E_VERDICT or len(checks) != 6 or not all(c[0] is True for c in checks):
        bad.append(f"verdict {_verdict(got)!r} over {len(checks)} checks, want {O1E_VERDICT} over 6, all True")
    return (not bad, "G1: analyse(o1e, v4) is the archived report exactly, PROVEN with 6 checks all True",
            "; ".join(bad) or f"{len(got['report'].splitlines())} report lines, {_verdict(got)}")


def g2(report: str) -> tuple:
    rc, out, err = cli_analyse()
    bad = []
    if rc != 0:
        bad.append(f"exit {rc}: {err[-300:]}")
    if out != report + "\n":
        bad.append(f"stdout is not the report plus print's newline: {_first_diff(out, report + chr(10))}")
    return (not bad, "G2: the CLI --analyse o1e --predictions v4 exits 0 and prints that report",
            "; ".join(bad) or "exit 0")


def g3(base: dict, got: dict, order: list) -> tuple:
    bad = []
    if base is not None:
        if order != base["dryrun_order"]:
            bad.append(f"cases {order} != the baseline's {base['dryrun_order']}")
        for name in order:
            if name in base["dryrun"]:
                bad += _same(got[name], base["dryrun"][name], name)
    rc, last = run_cases_quietly()
    if rc != 0 or last != f"{len(D.CASES) + 1}/{len(D.CASES) + 1} cases as registered":
        bad.append(f"run_cases(v4) returned {rc}: {last!r}")
    return (not bad, "G3: every dry-run case's (checks, report) is the baseline's, byte for byte; run_cases(v4) 0",
            "; ".join(bad[:4]) or f"{len(order)} cases; {last}")


def g4(base: dict, got: list) -> tuple:
    bad = [] if base is None or got == base["offline"] else [f"{got} != {base['offline']}"[:500]]
    if not all(c[0] is True for c in got):
        bad.append(f"offline_check(v4) reads {[c[0] for c in got]}")
    return (not bad, "G4: offline_check(v4) is the baseline's [(ok, what, detail)]",
            "; ".join(bad) or "; ".join(f"{c[1].split(':')[0]}: {c[2]}" for c in got))


def g5(base: dict, got: dict) -> tuple:
    bad = [] if base is None else _same(got, base["o1d"], "o1d")
    if _verdict(got) != O1D_VERDICT:
        bad.append(f"verdict {_verdict(got)!r}, want {O1D_VERDICT!r}")
    return (not bad, "G5: o1d's (checks, report) is the baseline's, byte for byte (a real VOID path)",
            "; ".join(bad) or _verdict(got))


def g6(base: dict, got: dict) -> tuple:
    bad = [] if base is None else _same(got, base["noise_mutant"], "the mutant")
    res = _result(got)
    if res.get("O1-NULL") is not False or res.get("O1-JOIN") is not True or _verdict(got) != MUTANT_VERDICT:
        bad.append(f"O1-NULL {res.get('O1-NULL')}, O1-JOIN {res.get('O1-JOIN')}, verdict {_verdict(got)!r}; want "
                   f"False, True, {MUTANT_VERDICT!r} -- a field-mode Byte[206] key read as noise")
    return (not bad, "G6: a field-mode Byte[206] key in the F runs only is FORK ONLY (O1's noise covers m != 1 only)",
            "; ".join(bad) or _verdict(got))


def _selection_bad(base: dict | None, got: dict, required) -> list:
    """What is wrong with a pytest selection's run: any failure, error or skip; a test the baseline collected or
    ``required`` names that did not pass; a non-zero exit or nothing passed."""
    bad = []
    for kind in ("failed", "errors", "skipped"):
        if got[kind]:
            bad.append(f"{kind}: {got[kind][:6]}")
    want = set(required) | set(base["tests"] if base is not None else ())
    missing = sorted(want - set(got["passed"]))
    if missing:
        bad.append(f"not run or not passed: {missing}")
    if got["rc"] != 0 or not got["passed"]:
        bad.append(f"pytest exit {got['rc']}, {len(got['passed'])} passed: {got['tail'][-400:]}")
    return bad


def g7(base: dict, got: dict) -> tuple:
    bad = _selection_bad(base, got, REQUIRED_TESTS)
    return (not bad, f'G7: pytest -k "{PYTEST_K}": all passed, 0 failed, 0 skipped; the baseline\'s tests and '
                     f"REQUIRED_TESTS among them", "; ".join(bad) or f"{len(got['passed'])} passed")


def g8(base: dict, got: dict) -> tuple:
    bad = []
    archived = (O2S / "o2_report.txt").read_text(encoding="utf-8")
    if got["report"] != archived:
        bad.append(f"the report is not the archived o2_report.txt: {_first_diff(got['report'], archived)}")
    if base is not None:
        bad += _same(got, base["o2s"], "story-o2")
    checks = got["checks"]
    v = _verdict_o2(got)
    if v != O2S_VERDICT or len(checks) != O2S_CHECKS or not all(c[0] is True for c in checks):
        bad.append(f"verdict {v!r} over {len(checks)} checks, want {O2S_VERDICT} over {O2S_CHECKS}, all True")
    return (not bad, f"G8: analyse(story-o2, v1) is the archived report exactly, PROVEN with {O2S_CHECKS} checks "
                     f"all True", "; ".join(bad) or f"{len(got['report'].splitlines())} report lines, {v}")


def g9(report: str) -> tuple:
    rc, out, err = o2_cli_analyse()
    bad = []
    if rc != 0:
        bad.append(f"exit {rc}: {err[-300:]}")
    if out != report + "\n":
        bad.append(f"stdout is not the report plus print's newline: {_first_diff(out, report + chr(10))}")
    return (not bad, "G9: the CLI o2_alexandria.py --analyse story-o2 --predictions v1 exits 0 and prints that report",
            "; ".join(bad) or "exit 0")


def g10(base: dict, got: dict, order: list, units: list) -> tuple:
    bad = []
    if base is not None:
        if order != base["dryrun_order"]:
            bad.append(f"cases {order} != the baseline's {base['dryrun_order']}"[:400])
        for name in order:
            if name in base["dryrun"]:
                bad += _same(got[name], base["dryrun"][name], name)
        if units != base["units"]:
            want = {u[0]: u for u in base["units"]}
            diff = [u[0] for u in units if want.get(u[0]) != u] + [n for n in want if n not in {u[0] for u in units}]
            bad.append(f"units differ from the baseline's: {diff[:6]}"
                       + ("" if [u[0] for u in units] == [u[0] for u in base["units"]] else " (and their order)"))
    off = [u[0] for u in units if u[1] is not True]
    if off:
        bad.append(f"units not as registered: {off[:6]}")
    rc, last = o2_run_cases_quietly()
    n = len(order) + len(units)
    if rc != 0 or last != f"{n}/{n} cases as registered":
        bad.append(f"run_cases(v1) returned {rc}: {last!r}, want {n}/{n}")
    return (not bad, "G10: every o2_dryrun case's (checks, report) and unit's (name, ok, detail) is the baseline's, "
                     "byte for byte; run_cases(v1) 0", "; ".join(bad[:4]) or f"{len(order)} sessions, {len(units)} "
                                                                             f"units; {last}")


def g11(base: dict, got: list) -> tuple:
    bad = [] if base is None or got == base["offline"] else [f"{got} != {base['offline']}"[:500]]
    if len(got) != O2_OFFLINE_CHECKS or not all(c[0] is True for c in got):
        bad.append(f"offline_check(v1) reads {[c[0] for c in got]}, want {O2_OFFLINE_CHECKS} x True")
    return (not bad, f"G11: O2's offline_check(v1) is the baseline's [(ok, what, detail)], {O2_OFFLINE_CHECKS} PASS",
            "; ".join(bad) or "; ".join(f"{c[1].split(':')[0]}: {c[2][:90]}" for c in got))


def g12(base: dict, got: dict) -> tuple:
    bad = _selection_bad(base, got, REQUIRED_TESTS_O2)
    return (not bad, f'G12: pytest -k "{PYTEST_K_O2}": all passed, 0 failed, 0 skipped; the O2 baseline\'s tests and '
                     f"REQUIRED_TESTS_O2 among them", "; ".join(bad) or f"{len(got['passed'])} passed")


# ======================================================================== the gate
def _missing(*, o1: bool = True, o2: bool = True) -> list:
    need = ([V4, O1E / "o1_session.json", O1E / "o1_report.txt", O1D / "o1_session.json"] if o1 else []) \
        + ([V1, O2S / "o2_session.json", O2S / "o2_report.txt"] if o2 else [])
    return [str(p) for p in need if not p.is_file()]


def collect() -> dict:
    """Everything the O1 code says, once: the gate's reading (and, at G0, the baseline's)."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order = dryrun_outputs(stock)
    return {"o1e": analyse_archive(O1E), "o1d": analyse_archive(O1D), "dryrun": dry, "dryrun_order": order,
            "noise_mutant": noise_mutant(stock), "offline": offline()}


def judge(base: dict | None, got: dict, tests: dict) -> list:
    return [g1(base, got["o1e"]), g2(got["o1e"]["report"]), g3(base, got["dryrun"], got["dryrun_order"]),
            g4(base, got["offline"]), g5(base, got["o1d"]), g6(base, got["noise_mutant"]), g7(base, tests)]


def collect_o2() -> dict:
    """Everything the O2 code says, once: the gate's reading (and, at G0', the O2 baseline's)."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order, units = o2_dryrun_outputs(stock)
    return {"o2s": o2_analyse_archive(), "dryrun": dry, "dryrun_order": order, "units": units,
            "offline": o2_offline()}


def judge_o2(base: dict | None, got: dict, tests: dict) -> list:
    return [g8(base, got["o2s"]), g9(got["o2s"]["report"]), g10(base, got["dryrun"], got["dryrun_order"],
                                                                 got["units"]),
            g11(base, got["offline"]), g12(base, tests)]


def _head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True)
    return p.stdout.strip() or "unknown"


def capture(out: Path) -> int:
    if out.exists():
        raise SystemExit(f"!! {out} exists: the baseline is captured once, before the refactor. It is never "
                         f"overwritten.")
    got = collect()
    tests = pytest_g7()
    items = judge(None, got, tests)
    for ok, what, detail in items:
        print(f"{'PASS' if ok else 'FAIL'}  {what}\n      {detail}")
    if not all(ok for ok, _w, _d in items):
        print("!! the pre-refactor code does not pass its own gate: no baseline written")
        return 1
    _pred, sha = O.load_predictions(V4)
    base = {"what": "O1's outputs at the pre-refactor code (research/o2_design.md 1.6 G0): every (checks, report) "
                    "the regression gate compares byte for byte",
            "head": _head(), "predictions": V4.name, "predictions_sha256": sha,
            "archives": {"o1e": str(O1E), "o1d": str(O1D)}, "tests": sorted(tests["passed"]), **got}
    text = json.dumps(base, indent=1, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    print(f"captured: {out} ({len(text)} chars, head {base['head'][:8]})")
    return 0


def capture_o2(out: Path) -> int:
    """G0': the O2 baseline, once, at the code BEFORE any O3 change (research/o3_design.md 1.4, 9 A0)."""
    if out.exists():
        raise SystemExit(f"!! {out} exists: the O2 baseline is captured once, before any O3 code change. It is "
                         f"never overwritten.")
    A, _D2 = _o2()
    got = collect_o2()
    tests = pytest_g12()
    items = judge_o2(None, got, tests)
    for ok, what, detail in items:
        print(f"{'PASS' if ok else 'FAIL'}  {what}\n      {detail}")
    if not all(ok for ok, _w, _d in items):
        print("!! the code here does not pass G8-G12's baseline-free halves: no O2 baseline written")
        return 1
    _pred, sha = A.O2.load(V1)
    base = {"what": "O2's outputs at the code before any O3 change (research/o3_design.md 1.4 G0'): every (checks, "
                    "report) and every unit's (name, ok, detail) the regression gate compares byte for byte",
            "head": _head(), "predictions": V1.name, "predictions_sha256": sha, "archive": str(O2S),
            "tests": sorted(tests["passed"]), **got}
    text = json.dumps(base, indent=1, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    print(f"captured: {out} ({len(text)} chars, head {base['head'][:8]})")
    return 0


def _show_items(items: list) -> None:
    for ok, what, detail in items:
        print(f"{'PASS' if ok else 'FAIL'}  {what}\n      {detail}", flush=True)


def gate(baseline: Path = BASELINE, baseline_o2: Path = BASELINE_O2) -> int:
    absent = [p for p in (baseline, baseline_o2) if not Path(p).is_file()]
    if absent:
        print(f"!! no baseline at {', '.join(str(p) for p in absent)}: the gate was not run (capture each first, "
              f"before the change it guards)")
        return 2
    base, base_o2 = json.loads(Path(baseline).read_bytes()), json.loads(Path(baseline_o2).read_bytes())
    items = judge(base, collect(), pytest_g7())
    _show_items(items)
    items_o2 = judge_o2(base_o2, collect_o2(), pytest_g12())
    _show_items(items_o2)
    items += items_o2
    n = sum(1 for ok, _w, _d in items if ok)
    print(f"\n{n}/{len(items)} items PASS (baseline heads: O1 {base['head'][:8]}, O2 {base_o2['head'][:8]})")
    return 0 if n == len(items) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--capture", action="store_true", help="G0: write the O1 baseline (refuses an existing one)")
    ap.add_argument("--capture-o2", action="store_true", help="G0': write the O2 baseline (refuses an existing one)")
    ap.add_argument("--out", type=Path, default=None,
                    help="where --capture / --capture-o2 writes (default: that baseline's committed path)")
    ap.add_argument("--baseline", type=Path, default=BASELINE, help="the O1 baseline the gate reads (default: the "
                                                                    "committed one; another is for testing the gate)")
    ap.add_argument("--baseline-o2", type=Path, default=BASELINE_O2,
                    help="the O2 baseline the gate reads (default: the committed one; another is for testing the gate)")
    args = ap.parse_args(argv)
    if args.capture and args.capture_o2:
        ap.error("capture one baseline at a time")
    missing = _missing(o1=not args.capture_o2, o2=not args.capture)
    if missing:
        print("!! the gate was not run -- missing: " + ", ".join(missing))
        return 2
    if args.capture:
        return capture(args.out or BASELINE)
    if args.capture_o2:
        return capture_o2(args.out or BASELINE_O2)
    return gate(args.baseline, args.baseline_o2)


if __name__ == "__main__":
    sys.exit(main())
