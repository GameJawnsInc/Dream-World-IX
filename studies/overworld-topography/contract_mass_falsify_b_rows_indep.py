"""Falsifier B, row-distribution deep-dive: reconcile the lane's row-distribution
population (ALL grass+desert family tris wearing the decal, both sides) against the
saturation-consistent population (topo-16 desert body only). Report the by-family-side
split for stock and Rung E, so the "Rung E is row0-heavy" separation can be judged
on the SAME population the saturation gate uses.

Out -> out/contract_mass/falsify_b_rows_indep.json
"""
from __future__ import annotations
import json, math, sys, re, glob
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-special-effect-plugin-dll-2fdd97/studies/overworld-topography")
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit")); sys.path.insert(0, str(HERE))
from ff9mapkit.world import extract as X          # noqa
from ff9mapkit.world import mesh as M             # noqa
from seam_null_recon import FAM_OF, classify_tri  # noqa

CELL = 4.0
OUT = HERE / "out" / "contract_mass" / "falsify_b_rows_indep.json"
STAGE = HERE / "out" / "rung_e" / "FF9CustomMap-world"
STOCK_CORE = {(bx, by) for bx in (13, 14, 15) for by in (11, 12)}


def recs(bm, bx, by):
    ox, oz = X.block_world_origin(bx, by)
    o = []
    for tri in bm.tris:
        idall0 = int(round(bm.tangents[tri[0]][0]))
        topo = X.decode_id(idall0)["topograph"]
        fam = FAM_OF.get(topo)
        uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
        o.append(dict(block=(bx, by), topo=topo, fam=fam, uv=uv))
    return o


def load_stock(blocks):
    t = []
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            continue
        t += recs(bm, bx, by)
    return t


def load_staged():
    t = []
    for f in sorted(glob.glob(str(STAGE / "**" / "*Terrain.ff9mesh"), recursive=True)):
        m = re.search(r"Block\[(\d+)\]\[(\d+)\]", f)
        bx, by = int(m.group(1)), int(m.group(2))
        bm = M.blockmesh_from_ff9mesh(Path(f), disc=1, x=bx, y=by, part="terrain")
        t += recs(bm, bx, by)
    return t


def rowdist(tris, restrict_topo16, only_fam=None):
    tot = Counter()
    for t in tris:
        if t["fam"] not in ("grass", "desert"):
            continue
        if restrict_topo16 and t["topo"] != 16:
            continue
        if only_fam and t["fam"] != only_fam:
            continue
        cls, k = classify_tri(t["fam"], t["uv"])
        if cls == "strip_grass_desert":
            tot[k] += 1
    n = sum(tot.values())
    frac = {k: round(tot.get(k, 0) / n, 4) for k in range(4)} if n else {}
    return dict(n=n, counts={k: tot.get(k, 0) for k in range(4)}, frac=frac)


def report(tris, label):
    return dict(
        label=label,
        lane_convention_grass_plus_desert=rowdist(tris, restrict_topo16=False),
        saturation_consistent_topo16_only=rowdist(tris, restrict_topo16=True),
        grass_side_only=rowdist(tris, restrict_topo16=False, only_fam="grass"),
        desert_side_only=rowdist(tris, restrict_topo16=False, only_fam="desert"),
    )


def main():
    stock = load_stock(STOCK_CORE)
    staged = load_staged()
    out = dict(stock=report(stock, "stock"), rung_e=report(staged, "rung_e"))
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    for lab, rep in out.items():
        print(f"\n=== {lab} ===")
        for k, v in rep.items():
            if k == "label":
                continue
            print(f"  {k:42s} n={v['n']:4d} frac={v['frac']}")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
