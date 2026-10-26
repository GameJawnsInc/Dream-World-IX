"""Multi-instance probe P8: two processes parse ONE custom FBX at once through the engine's own FbxIO.ReadFlexible.

THE DEFECT (stock Memoria 9732e30e, FbxIO.cs): every FBX read opens ``new FileStream(path, FileMode.Open)`` -- READ-WRITE access,
share Read -- for the whole parse. Two games on one desktop junction the same mod folder (tools/harness/instance.py), so when
both build the world map in the same second, the second open is refused (a sharing violation), the import returns null and the
world never constructs (the cal153 run .harness-runs/20261026-121811-duo-s154-wpm-cal153: the guest's dead world). s155 opens
the readers with FileAccess.Read + FileShare.Read.

The worker (p8_fbx_share.cs, compiled here with the .NET Framework csc) loads a COPY of a Managed folder's Assembly-CSharp.dll
and calls the COMPILED FbxIO.ReadFlexible -- the bytes the game runs, not a re-implementation -- so the same probe is red on the
s154 DLL and green on s155 only if the engine's open really changed. Per DLL, per round:

  * SOLO -- one worker alone: the control. Any failure here is the file or the loader, never a share race: must be clean.
  * PAIR -- two workers released together by a named event, on the same file: ``red`` expects >= 1 sharing violation over the
    rounds (the instrument can see the race); ``green`` expects zero failures and a parsed document on every call.

    py studies/test-harness/multi-instance/p8_fbx_share.py --fbx C:\\path\\6321.fbx \\
        --dll s154=C:\\copy\\of\\s154\\Managed:red --dll s155=C:\\copy\\of\\s155\\Managed:green

Never point --dll at the live Managed folder: a loaded DLL is mapped until the worker exits and would block a build's deploy.
Exit 0 iff every expectation held.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import tempfile
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "p8_fbx_share.cs"
CSC = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
OUT = Path(tempfile.gettempdir()) / "ff9-mi-p8"

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateEventW.restype = wintypes.HANDLE
_k32.CreateEventW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR)
_k32.SetEvent.argtypes = (wintypes.HANDLE,)
_k32.CloseHandle.argtypes = (wintypes.HANDLE,)


def build_worker() -> Path:
    OUT.mkdir(exist_ok=True)
    exe = OUT / "p8_fbx_share.exe"
    if exe.exists() and exe.stat().st_mtime >= SRC.stat().st_mtime:
        return exe
    r = subprocess.run([str(CSC), "/nologo", "/optimize+", f"/out:{exe}", str(SRC)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"csc failed:\n{r.stdout}{r.stderr}")
    return exe


def run_round(exe: Path, managed: Path, fbx: Path, workers: int, iterations: int, name: str) -> list:
    """Start ``workers`` workers ONE AT A TIME (each warm-up parse alone: on s154 two overlapping warm-ups race each other and
    one dies before the barrier), then release them together; return each worker's result dict."""
    event = _k32.CreateEventW(None, True, False, name)            # manual reset: one SetEvent releases every waiter
    if not event:
        sys.exit(f"CreateEventW failed: {ctypes.get_last_error()}")
    procs = []
    try:
        for _ in range(workers):
            p = subprocess.Popen([str(exe), str(managed), str(fbx), str(iterations), name],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            procs.append(p)
            line = p.stdout.readline().strip()
            if line != "READY":
                err = p.stderr.read()
                for q in procs:
                    q.kill()
                sys.exit(f"worker did not reach READY ({line!r}):\n{err}")
        _k32.SetEvent(event)
        results = []
        for p in procs:
            out, err = p.communicate(timeout=600)
            last = [ln for ln in out.splitlines() if ln.startswith("{")]
            if p.returncode != 0 or not last:
                sys.exit(f"worker failed (exit {p.returncode}):\n{out}\n{err}")
            results.append(json.loads(last[-1]))
        return results
    finally:
        _k32.CloseHandle(event)


def clean(results: list, iterations: int) -> bool:
    return all(r["sharing"] == 0 and r["other"] == 0 and r["ok"] == r["docs"] == iterations for r in results)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fbx", required=True, type=Path)
    ap.add_argument("--dll", action="append", required=True, help="LABEL=MANAGED_DIR:red|green")
    ap.add_argument("--iterations", type=int, default=400)
    ap.add_argument("--rounds", type=int, default=3)
    a = ap.parse_args()
    exe = build_worker()
    held = True
    for spec in a.dll:
        label, rest = spec.split("=", 1)
        managed, expect = rest.rsplit(":", 1)
        managed = Path(managed)
        if expect not in ("red", "green"):
            sys.exit(f"--dll {spec}: expect red or green")
        solo = [run_round(exe, managed, a.fbx, 1, a.iterations, f"ff9-mi-p8-{label}-solo-{i}") for i in range(a.rounds)]
        pair = [run_round(exe, managed, a.fbx, 2, a.iterations, f"ff9-mi-p8-{label}-pair-{i}") for i in range(a.rounds)]
        solo_ok = all(clean(r, a.iterations) for r in solo)
        violations = sum(w["sharing"] for r in pair for w in r)
        calls = 2 * a.iterations * a.rounds
        if expect == "red":
            pair_ok = violations > 0
        else:
            pair_ok = all(clean(r, a.iterations) for r in pair)
        firsts = sorted({w["first"] for r in pair for w in r if w["first"]})
        print(f"{label:>6} [{expect}] solo {'clean' if solo_ok else 'NOT CLEAN'} ({a.rounds}x{a.iterations}); pair: "
              f"{violations} sharing violation(s) in {calls} calls, per round "
              f"{[sum(w['sharing'] for w in r) for r in pair]}, other {sum(w['other'] for r in pair for w in r)}, docs "
              f"{sum(w['docs'] for r in pair for w in r)}/{calls} -> {'HELD' if solo_ok and pair_ok else 'BROKEN'}")
        for f in firsts:
            print(f"         first error: {f[:200]}")
        held &= solo_ok and pair_ok
    print("P8:", "every expectation held" if held else "an expectation BROKE")
    return 0 if held else 1


if __name__ == "__main__":
    sys.exit(main())
