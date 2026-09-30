"""THE O1 REGRESSION GATE (research/o2_design.md, section 1.6): moving O1's session and analysis machinery into
the shared ``segment_trace`` engine must leave every O1 output byte-identical.

    py studies/story-trace/segment_regress.py --capture     # G0, once, BEFORE the refactor: write the baseline
    py studies/story-trace/segment_regress.py               # G1-G7; exit 0 only if every item passes

Exit 2 means an archive or the baseline is missing: the gate was not run, which is not a pass.

It imports only the O1 modules (``o1_opening``, ``o1_dryrun``), through their public names, so the baseline was
captured at the pre-refactor code and the same file judges the refactored one:
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

Nothing here touches the game or writes to the install: it reads the archives, the build and the stock bytes.
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
    """Run G7's pytest selection; ``{"rc", "passed": [...], "failed": [...], "skipped": [...], "errors": [...]}``
    read from its JUnit XML (the names, not a summary line)."""
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "g7.xml"
        p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_harness.py", "-q", "-p", "no:cacheprovider",
                            "-W", "ignore", "-k", PYTEST_K, f"--junitxml={xml}"],
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


def g7(base: dict, got: dict) -> tuple:
    bad = []
    for kind in ("failed", "errors", "skipped"):
        if got[kind]:
            bad.append(f"{kind}: {got[kind][:6]}")
    want = set(REQUIRED_TESTS) | set(base["tests"] if base is not None else ())
    missing = sorted(want - set(got["passed"]))
    if missing:
        bad.append(f"not run or not passed: {missing}")
    if got["rc"] != 0 or not got["passed"]:
        bad.append(f"pytest exit {got['rc']}, {len(got['passed'])} passed: {got['tail'][-400:]}")
    return (not bad, f'G7: pytest -k "{PYTEST_K}": all passed, 0 failed, 0 skipped; the baseline\'s tests and '
                     f"REQUIRED_TESTS among them", "; ".join(bad) or f"{len(got['passed'])} passed")


# ======================================================================== the gate
def _missing() -> list:
    need = [V4, O1E / "o1_session.json", O1E / "o1_report.txt", O1D / "o1_session.json"]
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


def gate(baseline: Path = BASELINE) -> int:
    if not baseline.is_file():
        print(f"!! no baseline at {baseline}: the gate was not run (capture it first, before any refactor)")
        return 2
    base = json.loads(baseline.read_bytes())
    got = collect()
    items = judge(base, got, pytest_g7())
    for ok, what, detail in items:
        print(f"{'PASS' if ok else 'FAIL'}  {what}\n      {detail}")
    n = sum(1 for ok, _w, _d in items if ok)
    print(f"\n{n}/{len(items)} items PASS (baseline head {base['head'][:8]})")
    return 0 if n == len(items) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--capture", action="store_true", help="G0: write the baseline (refuses an existing one)")
    ap.add_argument("--out", type=Path, default=BASELINE, help="where --capture writes (default: the baseline)")
    ap.add_argument("--baseline", type=Path, default=BASELINE, help="the baseline the gate reads (default: the "
                                                                    "committed one; another is for testing the gate)")
    args = ap.parse_args(argv)
    missing = _missing()
    if missing:
        print("!! the gate was not run -- missing: " + ", ".join(missing))
        return 2
    return capture(args.out) if args.capture else gate(args.baseline)


if __name__ == "__main__":
    sys.exit(main())
