"""Lane chain: the per-job start tax, with the bytecode cache as THIS agent shell has it (PYTHONDONTWRITEBYTECODE=1 in
the process env only -- not in the User or Machine environment, so the owner's Workspace writes .pyc files) against
a warm bytecode cache under OUT/pycache (PYTHONPYCACHEPREFIX: nothing is written under the package).

    py studies/overworld-editor/perf/chain_pyc.py [runs]

The job: world-fuse on a missing layout file (it imports the CLI and refuses at once), and the same for
world-promote --dry-run on a missing draft (the bar's revert/promote job's start).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402


def env(kind):
    e = dict(os.environ)
    if kind == "as-is":
        return e
    e.pop("PYTHONDONTWRITEBYTECODE", None)
    e["PYTHONPYCACHEPREFIX"] = str(CC.OUT / "pycache")
    return e


def main(runs=5):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs,
           "agent_env_PYTHONDONTWRITEBYTECODE": os.environ.get("PYTHONDONTWRITEBYTECODE")}
    jobs = {"world-fuse": [sys.executable, "-m", "ff9mapkit", "--game", str(CC.GAME), "world-fuse",
                           str(CC.OUT / "no-such.toml"), "--mod-folder", str(CC.OUT / "nowhere")],
            "world-promote": [sys.executable, "-m", "ff9mapkit", "--game", str(CC.GAME), "world-promote",
                              str(CC.OUT / "no-such.draft"), "--dry-run"]}
    for kind in ("as-is", "pyc-cache"):
        if kind == "pyc-cache":                                       # one run to fill the cache (not timed)
            for a in jobs.values():
                subprocess.run(a, cwd=str(CC.KIT), env=env(kind), capture_output=True, text=True, timeout=600)
        for name, a in jobs.items():
            ts = []
            for _ in range(runs):
                t = time.perf_counter()
                subprocess.run(a, cwd=str(CC.KIT), env=env(kind), capture_output=True, text=True, timeout=600)
                ts.append(time.perf_counter() - t)
            out[f"{name} {kind}"] = CC.stats(ts)
            print(f"{name:14s} {kind:9s} min {min(ts):.2f} median {sorted(ts)[len(ts) // 2]:.2f}")
    CC.save("pyc.json", out)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
