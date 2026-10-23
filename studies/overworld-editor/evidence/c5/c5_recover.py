"""Recover the C5 lab's failed promote: the live writes and the disc-4 mirror pass ran, then writing promote.json failed
(its folder was never made: the live folder had no file at the island's cells). Rebuild the record exactly as
draft.promote would have written it, from the state it left, and rebase the draft. Read-only on the install."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\.claude\worktrees\terrain-shaping-continue-4647b2\ff9mapkit")
from ff9mapkit.world import draft as D

draft = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\terrain-shaping-continue-4647b2\studies\overworld-editor\out"
             r"\c5_lab\drafts\FF9CustomMap-world.draft")
meta = D.read_meta(draft)
source = Path(meta["source"])
rels = D.edits(draft)
print("edits still against the old baseline:", len(rels))
cells = sorted({p[1] for p in map(D._parse_rel, rels) if p is not None})
# the promote's own guard: every edited file is now the draft's bytes in the live folder
same = [rel for rel in rels if (source / rel).is_file() and D._sha(source / rel) == D._sha(draft / rel)]
assert same == rels, sorted(set(rels) - set(same))
# what was there before: the snapshot would have been the live files at those cells before the writes, and the
# promote's moved-guard proved each edited file matched the draft's baseline (here: absent). Anything else at the
# cells now that the promote did not write was there before too.
after = D._cell_files(source, cells)
before_files = [rel for rel in after if rel not in rels]
assert not before_files, before_files                 # nothing else lives at those cells
h = D.history(draft)
stamp = time.strftime("%Y%m%d-%H%M%S")
rec_dir = draft / D.PROMOTES / f"{stamp}-recovered"
rec_dir.mkdir(parents=True)
record = {"op": "promote", "source": str(source), "folder": source.name, "cells": [list(c) for c in cells],
          "promoted": rels, "utc": time.strftime("%Y-%m-%dT%H:%M:%S"), "record": str(rec_dir), "before": {},
          "after": {rel: D._sha(p) for rel, p in after.items()}, "reverted": None,
          "history_promoted_before": 0,
          "note": "recovered by hand: the promote's record folder was not made (fixed in world/draft.py)"}
assert h["promoted"] == h["cursor"] == 1, h        # _mark_promoted ran before the failure
(rec_dir / "promote.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
D._rebase(draft, meta, list(after) + D.stale(draft))
print("recorded", rec_dir, "| edits now", D.edits(draft), "| stale", D.stale(draft)[:3], "| last", bool(D.last_promote(draft)))
