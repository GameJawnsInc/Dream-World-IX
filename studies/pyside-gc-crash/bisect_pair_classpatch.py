"""The pair-crash bisect driver that isolated THE CLASS-PATCH FLAVOR (see NOTES.md).

Reproduces the record: `tests/test_cutscenedoc.py tests/test_workspace_floorplan.py` crashed
0xC0000005 in the floorplan module's qt_drain teardown. Detector = the first 5 floorplan
tests (their autouse drain is the detonation point). Verdicts: CRASH (fatal-exception banner
or 0xC0000005), PASS, RC<n>.

Findings on the pre-fix tree (2026-08-14, master 4ea8a31c..21d1ea6c):
  * the QFrame class-patch test ALONE + detector -> CRASH, deterministic, ~1s, every run;
  * prefix bisect converged on exactly that test (minimal crashing prefix's last element);
  * all 42 OTHER tests + detector -> PASS (the residual full-pair crash with the suspect
    deselected needed the full 100-test neighbour: the unparked-module GC flake, intermittent).

Run from anywhere; KIT below points at the tree under test. Post-fix, every subset PASSes.
"""
import subprocess
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parents[2] / "ff9mapkit"
SUSPECT = "tests/test_cutscenedoc.py::test_nothing_shows_the_accordion_panels_while_parentless"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def collect(f):
    r = subprocess.run(
        [sys.executable, "-m", "pytest", f, "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=KIT, capture_output=True, text=True, timeout=300)
    return [ln.strip().removeprefix("ff9mapkit/") for ln in r.stdout.splitlines() if "::" in ln]


def run(ids, tag):
    t0 = time.time()
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *ids, "-q", "-p", "no:cacheprovider"],
        cwd=KIT, capture_output=True, text=True, timeout=600)
    out = r.stdout + r.stderr
    crashed = ("Windows fatal exception" in out) or (r.returncode in (3221225477, -1073741819))
    verdict = "CRASH" if crashed else ("PASS" if r.returncode == 0 else f"RC{r.returncode}")
    log(f"{tag}: {verdict} rc={r.returncode} n={len(ids)} {time.time() - t0:.0f}s")
    return verdict


def main():
    cd = collect("tests/test_cutscenedoc.py")
    fp = collect("tests/test_workspace_floorplan.py")
    det = fp[:5]
    log(f"collected cutscenedoc={len(cd)} floorplan={len(fp)}; detector = first 5 floorplan tests")

    if run(det, "detector-alone") != "PASS":
        log("ABORT: detector alone is not clean")
        return
    whole = run(cd + det, "full+det")
    run([SUSPECT] + det, "suspect-alone+det")
    others = [t for t in cd if t != SUSPECT]
    run(others + det, "all-others+det")
    if whole != "CRASH":
        log("full+det did not crash -- on a fixed tree that is the expected verdict")
        return

    if run([cd[0]] + det, "first-test-alone+det") == "CRASH":
        log("VERDICT: a SINGLE (arbitrary) test poisons -> fixture-level, not test-level")
        return
    lo, hi = 1, len(cd)  # invariant: prefix[:hi] crashes
    while lo < hi:
        mid = (lo + hi) // 2
        if run(cd[:mid] + det, f"prefix[:{mid}]+det") == "CRASH":
            hi = mid
        else:
            lo = mid + 1
    log(f"minimal crashing prefix = {hi}; last test = {cd[hi - 1]}")
    run([cd[hi - 1]] + det, "prefix-last-alone+det")


if __name__ == "__main__":
    main()
