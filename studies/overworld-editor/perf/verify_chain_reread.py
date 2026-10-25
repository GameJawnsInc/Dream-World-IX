"""Skeptic of lane chain: after the Windows Defender security-intelligence update logged at 17:23:57 (event 2000), do
long-lived files that read fast before it (the owner's real draft, read at ~17:00 in 0.21 s by verify_chain_debt)
owe a first open again? READ ONLY (open + read, nothing written).

    py studies/overworld-editor/perf/verify_chain_reread.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
from ff9mapkit.world import draft as D                                # noqa: E402

OWNER_DRAFT = Path(r"C:\gd\Dream-World-IX\ff9mapkit\.ff9mapkit-cache\world-drafts\FF9CustomMap-world.draft")


def read_pass(files):
    t = time.perf_counter()
    for p in files:
        with open(p, "rb") as f:
            f.read()
    return round(time.perf_counter() - t, 3)


files = list(D._world_files(OWNER_DRAFT).values())
out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "files": len(files), "passes": [read_pass(files) for _ in range(3)]}
print(out)
p = CC.OUT / "verify" / "reread.json"
p.write_text(json.dumps(out, indent=1), encoding="utf-8")
print("->", p)
