"""PREFAB FEASIBILITY probe 2: compare two mod folders holding the same build at a whole-block offset.

usage: py studies/overworld-editor/prefab_folder_compare.py A B DBX DBY
Every A file  Block[x][y] <Part>  is paired with B's  Block[x+DBX][y+DBY] <Part>  (the r-folder follows);
ledgers are skipped.  Prints byte-identical / differing / unpaired counts per part.
"""
import collections
import pathlib
import re
import sys

a, b = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
dbx, dby = int(sys.argv[3]), int(sys.argv[4])
pat = re.compile(r"Block\[(\d+)\]\[(\d+)\] (.+)$")


def files(root):
    out = {}
    for p in root.rglob("*"):
        m = pat.search(p.name) if p.is_file() else None
        if m:
            out[(p.relative_to(root).parts[:3], int(m[1]), int(m[2]), m[3])] = p
    return out


fa, fb = files(a), files(b)
tally = collections.Counter()
diffs = []
for (pre, x, y, part), p in sorted(fa.items()):
    q = fb.get((pre, x + dbx, y + dby, part))
    if q is None:
        tally[(part, "unpaired")] += 1
        continue
    same = p.read_bytes() == q.read_bytes()
    tally[(part, "same" if same else "DIFF")] += 1
    if not same:
        diffs.append(f"{pre} [{x}][{y}] {part}")
extra = len(fb) - sum(v for (_, k), v in tally.items() if k != "unpaired")
for (part, k), v in sorted(tally.items()):
    print(f"  {part:16} {k:9} {v}")
print(f"A files {len(fa)}  B files {len(fb)}  B-only {extra}")
for d in diffs[:20]:
    print("  DIFF", d)
