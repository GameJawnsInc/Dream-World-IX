"""COMP20-BENCH.md's C3 -- which WorldMap files differ between a bench mirror and the live folder (read-only).

    py -X utf8 bench_vs_live.py <bench FF9CustomMap-world> [--expect-blocks 22,5 23,5 ...]

Prints every added / removed / changed path under Disc1/0_1 and Disc4/0_1, grouped by block, and flags any
change OUTSIDE the R4 revert set (the r4-pre file list + the 54 R4-created parts) and the expected blocks.
"""
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

LIVE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap-world\FF9_Data\WorldMap")
R4PRE = Path(r"C:\gd\Dream-World-IX\backups\west-seam-continent\r4-pre.20260828-103332")
CREATED = Path(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\4defe9bc-0f55-44e7-952d-bd74e20446f5"
               r"\scratchpad\r4_created.txt")


def tree(root):
    out = {}
    for disc in ("Disc1", "Disc4"):
        base = root / disc / "0_1"
        if base.is_dir():
            for p in base.rglob("*"):
                if p.is_file():
                    out[f"{disc}/{p.relative_to(base).as_posix()}"] = hashlib.sha1(p.read_bytes()).hexdigest()
    return out


def block_of(path):
    m = re.search(r"Block\[(\d+)\]\[(\d+)\]", path)
    return (int(m.group(1)), int(m.group(2))) if m else None


def main():
    bench = Path(sys.argv[1]) / "FF9_Data" / "WorldMap"
    expect = set()
    if "--expect-blocks" in sys.argv:
        for tok in sys.argv[sys.argv.index("--expect-blocks") + 1:]:
            a, b = tok.split(",")
            expect.add((int(a), int(b)))
    revert = {f"{p.parts[-3]}/{p.parts[-2]}/{p.name}" for p in R4PRE.rglob("*") if p.is_file()}
    revert |= {line.strip() for line in CREATED.read_text(encoding="utf-8").splitlines() if line.strip()}
    revert = {r.replace("Disc1/", "Disc1/").replace("Disc4/", "Disc4/") for r in revert}
    lv, bn = tree(LIVE), tree(bench)
    changed = defaultdict(list)
    for k in sorted(set(lv) | set(bn)):
        if lv.get(k) == bn.get(k):
            continue
        kind = "added" if k not in lv else "removed" if k not in bn else "changed"
        changed[block_of(k)].append((kind, k))
    n = sum(len(v) for v in changed.values())
    print(f"live {len(lv)} files, bench {len(bn)} files; differing paths: {n}")
    outside = []
    for blk in sorted(changed, key=lambda b: (b is None, b)):
        rows = changed[blk]
        in_rev = sum(1 for _, k in rows if k in revert)
        tag = "EXPECTED" if blk in expect else ""
        print(f"  block {blk}: {len(rows)} ({', '.join(sorted({r[0] for r in rows}))}); in the R4 revert set {in_rev} {tag}")
        for kind, k in rows:
            if k not in revert and blk not in expect:
                outside.append((kind, k))
    print(f"changes OUTSIDE the revert set and the expected blocks: {len(outside)}")
    for kind, k in outside[:30]:
        print(f"    {kind}: {k}")


if __name__ == "__main__":
    main()
