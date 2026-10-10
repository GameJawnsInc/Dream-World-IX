"""The SOUND control for the choice-menu leak: stand on SEBENCH (bench/sebench.field.toml, slot 30488), where an NPC's
behavior plays SE 103 -- the menu cursor blip -- about once a second with no window and no UI cursor, and sample FF9's
private memory. Compare the slope with the per-cursor-move cost bench_soak measures.

    py tools/deploy_field.py studies/menu-leak/bench/sebench.field.toml --id 30488   # first deploy = relaunch
    py tools/play.py studies/menu-leak/se_soak.py          # SOAK_SECONDS=120 SOAK_EVERY_S=10
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))

from harness.session import ff9_pids                     # noqa: E402
from memprobe import private_mb                          # noqa: E402

FID = 30488


def run(g) -> None:
    seconds = float(os.environ.get("SOAK_SECONDS", "120"))
    every = float(os.environ.get("SOAK_EVERY_S", "10"))
    pid = ff9_pids()[0]
    g.newgame()
    g.warp(FID)
    g.wait_for(lambda s: s.field_id == FID and s.control, timeout=30, what="the bench")
    time.sleep(10)
    rows = []
    t0 = time.time()
    while True:
        t = time.time() - t0
        priv, ws = private_mb(pid)
        rows.append({"t": round(t, 1), "private_mb": round(priv, 1), "ws_mb": round(ws, 1)})
        print(f"  [{t:6.1f}s] private {priv:7.1f} MB  ws {ws:7.1f} MB", flush=True)
        if t >= seconds:
            break
        time.sleep(every)
    rate = (rows[-1]["private_mb"] - rows[0]["private_mb"]) / max(rows[-1]["t"], 1e-6)
    summary = {"seconds": rows[-1]["t"], "delta_mb": round(rows[-1]["private_mb"] - rows[0]["private_mb"], 1),
               "mb_per_s": round(rate, 3)}
    print(f"== se: {summary}", flush=True)
    (Path(g.run_dir) / "soak.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows)
                                                + json.dumps({"summary": summary}) + "\n")
    g.check(True, "se soak finished", json.dumps(summary))
