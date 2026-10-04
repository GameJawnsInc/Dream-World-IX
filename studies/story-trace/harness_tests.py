"""THE FAST WAY TO RUN ``tests/test_harness.py``, and the receipt that says a run was green (PLAN.md "Build testing").

    py studies/story-trace/harness_tests.py whole --out DIR    # the whole file at -n 8, flakes settled, DIR/receipt.json
    py studies/story-trace/harness_tests.py check DIR/receipt.json   # is that receipt for HEAD and this working tree?

The file's tests drive FakeGame on a real-time loop, so they are sleep-bound and run in parallel: 66 min serial, 14.4
min at ``-n 8`` (measured 2026-10-04, 918 passed). Under load a timing test can fail where it passes alone. THE FLAKE
PROTOCOL re-runs ONLY the failed tests, alone and one after another, up to 3 times each: a test that passes 3/3 alone
is a FLAKE -- named in the receipt and in the output, never hidden; one that fails any of its runs is a FAILURE. More
than :data:`MAX_SETTLE` failures are not re-run at all: that many is a breakage, not load.

A receipt binds the junit to the commit AND the working tree (:func:`tree_id`: the tree ``git add -A`` would write,
through a temporary index -- untracked files count, ignored ones do not, the real index is never touched), to the
Python and to the test file. ``segment_regress.py --pytest-junit`` refuses a receipt that does not match
(:func:`receipt_problems`), so a green run is reused only for the code it ran.

Library use (``segment_regress.py``): :func:`run`, :func:`collect`, :func:`settle`, :func:`read_junit` print NOTHING --
the gate runs them on a thread while its in-process items redirect ``sys.stdout``.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KIT = ROOT / "ff9mapkit"
TEST_FILE = "tests/test_harness.py"
#: The default xdist worker count: 8 measured green on this 12-CPU machine with other sessions running (2026-10-04);
#: ``FF9_TEST_WORKERS`` overrides it (6 while the nightly or another session is testing; 0 = serial).
WORKERS = 8
#: More failures than this are not re-run alone: a breakage, not load.
MAX_SETTLE = 10
#: Runs alone a failed test must pass, every one, to be a flake.
SETTLE_RUNS = 3
#: The flags every run here passes (the build agents' own: no cache files, warnings off).
BASE_ARGS = ("-q", "-p", "no:cacheprovider", "-W", "ignore")


def workers(n: int | None = None) -> int:
    """The xdist worker count: ``n`` when given, else ``FF9_TEST_WORKERS``, else :data:`WORKERS`; 0 (serial, as before)
    when it is 0 or pytest-xdist is not importable."""
    if n is None:
        env = os.environ.get("FF9_TEST_WORKERS")
        n = int(env) if env not in (None, "") else WORKERS
    return n if n > 0 and importlib.util.find_spec("xdist") is not None else 0


def _py() -> str:
    return sys.version.split()[0]


def pytest_argv(*, k: str | None = None, junit: Path | None = None, n: int = 0, nodes=()) -> list:
    """The pytest command line: the test file (or ``nodes``), :data:`BASE_ARGS`, ``-k``, xdist's ``-n`` with
    ``--dist worksteal`` (its default ``load`` hands each worker a fixed block up front and leaves the long O4 tests to
    finish last), the junit."""
    argv = [sys.executable, "-m", "pytest", *(nodes or [TEST_FILE]), *BASE_ARGS]
    if k is not None:
        argv += ["-k", k]
    if n > 0:
        argv += ["-n", str(n), "--dist", "worksteal"]
    if junit is not None:
        argv.append(f"--junitxml={junit}")
    return argv


def read_junit(path: Path) -> dict:
    """``{test name: "passed" | "failed" | "error" | "skipped" | "xfailed"}`` from a junit XML, by the testcase's name
    (pytest's node name, parameters included). An error outranks a failure, a failure a skip."""
    out: dict = {}
    rank = {"passed": 0, "xfailed": 1, "skipped": 2, "failed": 3, "error": 4}
    for tc in ET.parse(path).getroot().iter("testcase"):
        kinds = {child.tag: child for child in tc}
        if "error" in kinds:
            st = "error"
        elif "failure" in kinds:
            st = "failed"
        elif "skipped" in kinds:
            st = "xfailed" if (kinds["skipped"].get("type") or "") == "pytest.xfail" else "skipped"
        else:
            st = "passed"
        name = tc.get("name")
        if rank[st] >= rank[out.get(name, "passed")]:
            out[name] = st
    return out


#: Every child this module has running, so :func:`stop_all` can end them (the gate's thread cannot be interrupted).
_LIVE: set = set()
_LIVE_LOCK = threading.Lock()
_STOPPED = threading.Event()


def _call(argv, *, cwd, env=None) -> tuple:
    """``(rc, stdout, stderr)`` of one child, registered while it runs; refused once :func:`stop_all` has been called
    (until :func:`reset_stop`)."""
    if _STOPPED.is_set():
        raise RuntimeError("stopped: the gate is ending")
    p = subprocess.Popen(argv, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace", env=env)
    with _LIVE_LOCK:
        _LIVE.add(p)
    try:
        out, err = p.communicate()
    finally:
        with _LIVE_LOCK:
            _LIVE.discard(p)
    return p.returncode, out or "", err or ""


def stop_all() -> None:
    """End every running child and its own children (pytest's xdist workers), and refuse new ones: a gate whose
    in-process half raised must not wait on, or orphan, a pytest run nobody will read."""
    _STOPPED.set()
    with _LIVE_LOCK:
        live = list(_LIVE)
    for p in live:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        else:
            p.kill()


def reset_stop() -> None:
    _STOPPED.clear()


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*, k: str | None = None, n: int | None = None, junit: Path | None = None, env=None) -> dict:
    """Run the test file (or its ``-k`` selection) once: ``{"rc", "results": {name: status}, "tail", "seconds",
    "argv"}``; ``results`` empty and an ``error`` key when this run wrote no junit -- a ``junit`` path is cleared
    before the run, so a file left there by an earlier run is never read as this one's."""
    n = workers(n)
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(junit).resolve() if junit is not None else Path(tmp) / "run.xml"
        xml.unlink(missing_ok=True)
        argv = pytest_argv(k=k, junit=xml, n=n)
        t0 = time.time()
        rc, so, se = _call(argv, cwd=KIT, env=env)
        out = {"rc": rc, "results": {}, "tail": (so + se)[-1500:],
               "seconds": round(time.time() - t0, 1), "argv": [str(a) for a in argv[1:] if not str(a).startswith(
                   "--junitxml")], "n": n}
        if xml.is_file():
            out["results"] = read_junit(xml)
        else:
            out["error"] = "no JUnit XML written"
    return out


def collect(k: str, *, env=None) -> list:
    """The test names ``-k k`` selects, by pytest's own matching (``--collect-only``): never a re-implementation of
    ``-k``. Raises RuntimeError when the collection itself fails."""
    argv = [sys.executable, "-m", "pytest", TEST_FILE, "--collect-only", *BASE_ARGS, "-k", k]
    rc, so, se = _call(argv, cwd=KIT, env=env)
    names = [ln.strip().split("::", 1)[1] for ln in so.splitlines()           # node ids from pytest's rootdir
             if "::" in ln and ln.strip().split("::", 1)[0].endswith(TEST_FILE)]
    if rc not in (0, 5) or (rc == 0 and not names):
        raise RuntimeError(f"collecting -k {k!r}: exit {rc}: {(so + se)[-600:]}")
    return names


def _run_alone(name: str, *, env=None, test_file: str = TEST_FILE, cwd: Path = KIT) -> bool:
    """One serial run of one test: True only when its junit row reads PASSED -- pytest exits 0 for a test that skips
    or xfails alone too, and neither is a pass (a test that no longer collects is not one either)."""
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "alone.xml"
        _call(pytest_argv(nodes=[f"{test_file}::{name}"], junit=xml), cwd=cwd, env=env)
        return xml.is_file() and read_junit(xml).get(name) == "passed"


def settle(names, *, env=None, runner=None) -> dict:
    """THE FLAKE PROTOCOL: each failed (or errored) test in ``names`` re-run alone, serially, up to
    :data:`SETTLE_RUNS` times, stopping at its first failure: ``{"flakes": [{"name", "alone"}], "failures": [{"name",
    "alone"}], "unsettled": bool}`` -- ``alone`` "3/3" for a flake, "i/3" (passes before the failing run) for a failure.
    More than :data:`MAX_SETTLE` names are all failures, none re-run (``unsettled`` True)."""
    runner = runner or (lambda nm: _run_alone(nm, env=env))
    names = sorted(set(names))
    if len(names) > MAX_SETTLE:
        return {"flakes": [], "failures": [{"name": nm, "alone": "not re-run"} for nm in names], "unsettled": True}
    flakes, failures = [], []
    for nm in names:
        ok = 0
        while ok < SETTLE_RUNS and runner(nm):
            ok += 1
        (flakes if ok == SETTLE_RUNS else failures).append({"name": nm, "alone": f"{ok}/{SETTLE_RUNS}"})
    return {"flakes": flakes, "failures": failures, "unsettled": False}


def head(root: Path = ROOT) -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(root), capture_output=True, text=True)
    return p.stdout.strip() or "unknown"


def tree_id(root: Path = ROOT) -> str:
    """The tree ``git add -A`` would write for the working tree, through a temporary COPY of the index: tracked edits
    and untracked files change it, ignored files do not, and the real index is never touched."""
    p = subprocess.run(["git", "rev-parse", "--git-path", "index"], cwd=str(root), capture_output=True, text=True,
                       check=True)
    index = Path(p.stdout.strip())
    index = index if index.is_absolute() else Path(root) / index
    with tempfile.TemporaryDirectory() as tmp:
        tmp_index = Path(tmp) / "index"
        if index.is_file():
            shutil.copyfile(index, tmp_index)
        env = dict(os.environ, GIT_INDEX_FILE=str(tmp_index))
        subprocess.run(["git", "add", "-A"], cwd=str(root), env=env, capture_output=True, check=True)
        w = subprocess.run(["git", "write-tree"], cwd=str(root), env=env, capture_output=True, text=True, check=True)
    return w.stdout.strip()


def receipt_problems(r: dict, *, now_head: str, now_tree: str, python: str | None = None) -> list:
    """Why a receipt is not evidence for the code here: another commit or working tree, another Python, not the whole
    test file, a tree that changed during its run, a run that did not finish (pytest's exit neither 0 nor 1), or its
    junit gone or not the file the run wrote (its sha256)."""
    bad = []
    if r.get("kind") != "whole" or r.get("test_file") != TEST_FILE:
        bad.append(f"not a whole-file run of {TEST_FILE} (kind {r.get('kind')!r}, file {r.get('test_file')!r})")
    if r.get("head") != now_head:
        bad.append(f"head {str(r.get('head'))[:8]} is not HEAD {now_head[:8]}")
    if r.get("tree") != now_tree:
        bad.append(f"tree {str(r.get('tree'))[:8]} is not the working tree's {now_tree[:8]} (an edit since the run)")
    if r.get("tree_after") != r.get("tree"):
        bad.append("the working tree changed during the run")
    if r.get("python") != (python or _py()):
        bad.append(f"python {r.get('python')} is not {python or _py()}")
    if r.get("rc") not in (0, 1):
        bad.append(f"pytest exited {r.get('rc')!r}: the run did not finish")
    if not r.get("junit") or not Path(r["junit"]).is_file():
        bad.append(f"its junit {r.get('junit')!r} is not there")
    elif r.get("junit_sha256") != _sha256(Path(r["junit"])):
        bad.append("its junit is not the file the run wrote (sha256): a later run overwrote it")
    return bad


def load_receipt(path: Path) -> tuple:
    """``(receipt, problems)`` for the code here (:func:`receipt_problems` against HEAD and :func:`tree_id`)."""
    r = json.loads(Path(path).read_text(encoding="utf-8"))
    return r, receipt_problems(r, now_head=head(), now_tree=tree_id())


def _inside_repo_unignored(path: Path) -> bool:
    path = Path(path).resolve()
    if ROOT.resolve() not in path.parents and path != ROOT.resolve():
        return False
    p = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=str(ROOT), capture_output=True)
    return p.returncode != 0


def whole(out_dir: Path, *, n: int | None = None) -> int:
    """Run the whole file at ``-n``, settle its failures, write ``out_dir/whole.xml`` and ``out_dir/receipt.json``.
    Exit 0 green (nothing failed but flakes, nothing skipped), 1 not green, 2 not run."""
    out_dir = Path(out_dir).resolve()
    if _inside_repo_unignored(out_dir):
        print(f"!! --out {out_dir} is inside the repo and not ignored: writing there would change the tree the receipt "
              f"binds -- use a scratch directory")
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    junit, rp = out_dir / "whole.xml", out_dir / "receipt.json"
    rp.unlink(missing_ok=True)                  # no earlier run's receipt beside this run's junit, ever
    h, t = head(), tree_id()
    got = run(n=n, junit=junit)
    if "error" in got or got["rc"] not in (0, 1):
        print(f"!! the run did not finish (exit {got['rc']}, {got.get('error') or 'a partial junit'}): not run\n"
              f"{got['tail']}")
        return 2
    res = got["results"]
    bad = [nm for nm, st in res.items() if st in ("failed", "error")]
    settled = settle(bad)
    flaky = {f["name"] for f in settled["flakes"]}
    counts = {st: sum(1 for v in res.values() if v == st) for st in ("passed", "failed", "error", "skipped", "xfailed")}
    skipped = sorted(nm for nm, st in res.items() if st == "skipped")
    green = not settled["failures"] and not skipped and got["rc"] in (0, 1) and bool(res)
    receipt = {"what": "a whole-file run of tests/test_harness.py (studies/story-trace/harness_tests.py)",
               "kind": "whole", "test_file": TEST_FILE, "head": h, "tree": t, "tree_after": tree_id(),
               "python": _py(), "argv": got["argv"], "n": got["n"], "rc": got["rc"], "seconds": got["seconds"],
               "junit": str(junit), "junit_sha256": _sha256(junit), "counts": counts, "skipped": skipped, "flakes": settled["flakes"],
               "failures": settled["failures"], "unsettled": settled["unsettled"], "green": green,
               "finished": time.strftime("%Y-%m-%d %H:%M:%S")}
    tmp = rp.with_suffix(".tmp")
    tmp.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, rp)
    print(f"harness tests: {counts['passed']} passed, {counts['xfailed']} xfailed, {len(skipped)} skipped, "
          f"{counts['failed'] + counts['error']} failed in {got['seconds']:.0f} s at -n {got['n']} "
          f"(HEAD {h[:8]}, tree {t[:8]})")
    for f in settled["flakes"]:
        print(f"FLAKE    {f['name']}: failed at -n {got['n']}, passed alone {f['alone']}")
    for f in settled["failures"]:
        print(f"FAILURE  {f['name']}: alone {f['alone']}")
    for nm in skipped:
        print(f"SKIPPED  {nm} -- a skip is not a pass")
    if receipt["tree_after"] != t:
        print("!! the working tree changed during the run: the receipt binds neither tree")
    print(f"{'GREEN' if green else 'NOT GREEN'} -- receipt {rp}" + (f" ({len(flaky)} flake(s) named above)"
                                                                   if flaky else ""))
    return 0 if green and receipt["tree_after"] == t else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("whole", help="run the whole file at -n, settle flakes, write a receipt")
    w.add_argument("--out", type=Path, required=True, help="a scratch directory (never inside the repo unignored)")
    w.add_argument("-n", type=int, default=None, help=f"xdist workers (default FF9_TEST_WORKERS or {WORKERS}; 0 = "
                                                      f"serial)")
    c = sub.add_parser("check", help="is a receipt for HEAD and this working tree?")
    c.add_argument("receipt", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "whole":
        return whole(args.out, n=args.n)
    r, bad = load_receipt(args.receipt)
    if bad:
        print("!! not evidence for the code here: " + "; ".join(bad))
        return 1
    print(f"ok: {r['head'][:8]} / tree {r['tree'][:8]}, {'GREEN' if r.get('green') else 'NOT GREEN'}, "
          f"{len(r.get('flakes') or ())} flake(s)")
    return 0 if r.get("green") else 1


if __name__ == "__main__":
    sys.exit(main())
