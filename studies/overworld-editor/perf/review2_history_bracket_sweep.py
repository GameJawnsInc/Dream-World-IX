"""Review-2 probe (history slice, b6b806c5): the discard's sweep finds its renamed copy by Path.glob(name +
".discarding-*"). A mod folder name holding '[' is a glob character class there, so the sweep never matches the
copy it just renamed aside: the whole draft stays on disk, one more copy per discard.

Hermetic: fake game + drafts under studies/overworld-editor/out/perf/review2/history/bracket_sweep/."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review2" / "history" / "bracket_sweep"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    game = OUT / "GAME"
    src = game / "Mod[1]-world"
    row = src / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0"
    row.mkdir(parents=True)
    (row / "Block[0][0] Terrain.ff9mesh").write_bytes(b"stock" * 1000)
    root = OUT / "drafts"
    for i in range(3):
        d = D.ensure_draft(src, game=game, root=root)
        D.discard(d, root=root)
        print(f"after discard {i + 1}:", sorted(p.name for p in root.iterdir()))


if __name__ == "__main__":
    main()
