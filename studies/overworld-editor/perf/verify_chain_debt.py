"""Skeptic of lane chain: is the "first-open debt" (the first read of a file just written costs ~5 ms) something a
user's draft actually carries when the whole-map snapshot or a world-fuse job reads it, or an artifact of probes that
read a copy the instant it was written?

    py studies/overworld-editor/perf/verify_chain_debt.py [waits...]     # default waits: 0 60 240 (seconds)

(a) THE OWNER'S REAL DRAFT (main repo cache, written by ensure_draft about a day ago): two read passes over its world
    files, READ ONLY (open + read, nothing written). Says whether a draft long in use still carries the debt.
(b) DECAY: for each wait W, a fresh raw copy of the install folder's world files (read only from the install, written
    under OUT/verify/decay_<W>), then sleep W seconds, then three read passes. If the debt decays with time, a human-
    paced flow (a draft made at the first Accept, a sink Accept minutes later) never pays it.
(c) WHAT PAYS IT: on a fresh copy, a stat-only pass (what the cards' draftinfo readers do), then an open+read-1-byte
    pass, then a full read pass.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402

OWNER_DRAFT = Path(r"C:\gd\Dream-World-IX\ff9mapkit\.ff9mapkit-cache\world-drafts\FF9CustomMap-world.draft")
V = CC.OUT / "verify"
V.mkdir(parents=True, exist_ok=True)


def read_pass(files):
    t = time.perf_counter()
    n = 0
    for p in files:
        with open(p, "rb") as f:
            n += len(f.read())
    return round(time.perf_counter() - t, 3), n


def copy_install(dst: Path):
    dst = CC.assert_outside_game(dst)
    if dst.exists():
        shutil.rmtree(dst)
    files = []
    t = time.perf_counter()
    for rel, p in sorted(D._world_files(CC.SOURCE).items()):
        q = dst / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes(p.read_bytes())
        files.append(q)
    return files, round(time.perf_counter() - t, 3)


def main(waits):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S")}
    # (a) the owner's draft, read only
    if OWNER_DRAFT.is_dir():
        files = list(D._world_files(OWNER_DRAFT).values())
        mt = sorted(os.stat(p).st_mtime for p in files)
        out["owner_draft"] = {"files": len(files),
                              "oldest_mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(mt[0])),
                              "newest_mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(mt[-1])),
                              "passes": [read_pass(files)[0] for _ in range(2)]}
        print("owner draft", out["owner_draft"], flush=True)
    # (c) what pays it
    files, tc = copy_install(V / "pays")
    t = time.perf_counter()
    for p in files:
        os.stat(p)
    stat_s = round(time.perf_counter() - t, 3)
    t = time.perf_counter()
    for p in files:
        with open(p, "rb") as f:
            f.read(1)
    one_s = round(time.perf_counter() - t, 3)
    full = [read_pass(files)[0] for _ in range(2)]
    out["pays"] = {"copy_s": tc, "stat_pass_s": stat_s, "open_read1_pass_s": one_s, "full_passes_after": full}
    print("pays", out["pays"], flush=True)
    # (b) decay
    out["decay"] = []
    for w in waits:
        files, tc = copy_install(V / f"decay_{w}")
        time.sleep(w)
        passes = [read_pass(files)[0] for _ in range(3)]
        rec = {"wait_s": w, "copy_s": tc, "files": len(files), "passes": passes}
        out["decay"].append(rec)
        print("decay", rec, flush=True)
    p = V / "debt.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("->", p)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [0, 60, 240])
