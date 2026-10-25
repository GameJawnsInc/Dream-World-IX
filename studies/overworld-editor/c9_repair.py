"""Repair after c9_lab's second promote crashed half way (draft.promote's relabel KeyError, fixed in the same commit).

The crash wrote the edited draft's disc-1 files and one relabel row into FF9CustomMap-world, then stopped before the
disc-4 mirror and before writing its promote record, so Revert promote could not undo it. The ORIG draft's promote
record holds the exact snapshot of every live file at the six blocks before any of it (promote 1 was reverted to
those very bytes), so this puts them back the way revert does: each differing file written back (parked first, by
the deploy seam) or removed, ledgered under world-promote; the relabelled file's bytes never moved, so it is only
ledgered again. Then every file at the cells is checked against the snapshot.

    py studies/overworld-editor/c9_repair.py          # dry: what differs
    py studies/overworld-editor/c9_repair.py --apply
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402  (pins the worktree package)

from ff9mapkit.world import draft as D                                 # noqa: E402
from ff9mapkit.world import mesh as M                                  # noqa: E402

RELABELLED = ["FF9_Data/WorldMap/Disc1/0_1/r7/Block[1][7] Terrain.ff9mesh"]   # promote 2's one relabel row


def main(apply: bool):
    prep = json.loads((HERE / "out" / "c9_prep.json").read_text(encoding="utf-8"))
    orig = Path(prep["orig"])
    rec = D.promotes(orig)[-1]
    assert rec.get("reverted"), "ORIG's last promote is not the reverted promote 1"
    source, snap = Path(rec["source"]), Path(rec["record"]) / "before"
    assert source == C1.GAME / "FF9CustomMap-world", source
    cells = [tuple(c) for c in rec["cells"]]
    for rel, sha in rec["before"].items():
        assert D._sha(snap / rel) == sha, f"snapshot damaged: {rel}"
    now = D._cell_files(source, cells)
    differ = sorted(rel for rel in set(rec["before"]) | set(now)
                    if rel not in now or rel not in rec["before"] or D._sha(now[rel]) != rec["before"][rel])
    print(f"{len(differ)} file(s) at {cells} differ from the snapshot: {differ}")
    if not apply:
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = C1.MAIN_BACKUPS / f"FF9CustomMap-world.ff9world.jsonl.{stamp}.c9-repair"
    shutil.copyfile(source / D.LEDGER, bak)
    print(f"ledger backed up to {bak}")
    with M.ledger_pipeline("world-promote", draft=str(orig), revert=rec["utc"], repair="c9 promote-2 crash"):
        for rel in differ:
            live = source / rel
            if rel in rec["before"]:
                D._write_live(live, (snap / rel).read_bytes(), source=source)
                print(f"restored -> {live}")
            else:
                D._unlink_live(live, source=source)
                print(f"removed -> {live}")
        for rel in RELABELLED:
            key = D._ledger_key(rel)
            M.record_ledger_write(source / rel, cell=key[1], part=key[2], write_disc=key[0], mod_root=source)
            print(f"ledgered again -> {source / rel}")
    now = D._cell_files(source, cells)
    left = sorted(rel for rel in set(rec["before"]) | set(now)
                  if rel not in now or rel not in rec["before"] or D._sha(now[rel]) != rec["before"][rel])
    assert not left, left
    print(f"every file at the {len(cells)} blocks is the snapshot's again ({len(now)} files)")


if __name__ == "__main__":
    main("--apply" in sys.argv[1:])
