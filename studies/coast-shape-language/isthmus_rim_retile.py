"""RIM RE-TILE for the Path D isthmus -- terminate its cropped shallow ring into deep water.

What the owner asked for and I twice failed to build: the carried island's shallow ring is
cropped at the donor rect frame, so it ends against the open-ocean deep ring with no
transition -- a hard sea3|deep seam. The fix is to RE-TILE that rim, not to delete the ring
(``--deepen-shallow``, a registered dead end) and not to author uvs (which produced a
checkerboard and then stretched tiles).

This reuses ``studies/overworld-topography/wang_rim_retile.py``, the proven pattern from the
(8,17) desert-beach island, and keeps its governing principle:

  **the replacement sea5 uvs are HARVESTED byte-exact from the donor's OWN termination
  tiles. Nothing is synthesized.**

Each flagged rim quad keeps its EXACT verts, normals and tangent-x topo; only the uv rect
and the containing Sea file change. So the {Sea3,Sea4,Sea5} triangle union is a pure
REPARTITION -- geometry identical -- and walk/boat legality is preserved by construction.

  py studies/coast-shape-language/isthmus_rim_retile.py            # plan + gates, writes nothing
  py studies/coast-shape-language/isthmus_rim_retile.py --apply    # write the overrides

Verification is the kit's own gate: after a retile, a re-carry with
``--enforce-wang-carry`` must pass (the gate's docstring names exactly this as the
post-retile CI check).
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import mesh as M                            # noqa: E402
from ff9mapkit.world import water as W                           # noqa: E402
from ff9mapkit.world import extract as X                         # noqa: E402

GAME = Path(r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX")
WORLD = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
DISC = 9
LOD = "0_1"
SEA = ("sea3", "sea4", "sea5")
G = 16
CELL = 4.0

#: the deployed isthmus (donor (6,6)+2x2 carried to (14,12))
ISLAND = [(14, 12), (15, 12), (14, 13), (15, 13)]
#: its carry donors, on the real disc -- the verbatim sea5 vocabulary
DONORS = [(6, 6), (7, 6), (6, 7), (7, 7)]


def _load_study():
    """Import the (8,17) retile study for its pure helpers, with OUR donors bound."""
    p = REPO / "studies" / "overworld-topography" / "wang_rim_retile.py"
    spec = importlib.util.spec_from_file_location("wang_rim_retile", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wang_rim_retile"] = mod
    spec.loader.exec_module(mod)
    mod.DONORS = DONORS          # harvest_variants closes over this
    mod.ISLAND = ISLAND
    return mod


def rdir(by):
    return WORLD / f"Disc{DISC}" / LOD / f"r{by}"


def load_cell(bx, by):
    """{part: BlockMesh} for the cell's sea parts, from the DEPLOYED disc-9 overrides."""
    out = {}
    for part in SEA:
        p = rdir(by) / f"Block[{bx}][{by}] {part.capitalize()}.ff9mesh"
        if p.exists():
            out[part] = M.blockmesh_from_ff9mesh(str(p), disc=DISC, x=bx, y=by,
                                                 lod=LOD, part=part)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    WR = _load_study()

    cells = {c: load_cell(*c) for c in ISLAND}
    have = {c: sorted(p for p in v) for c, v in cells.items()}
    print("deployed isthmus sea parts:")
    for c in ISLAND:
        n = {p: len(WR.part_tris(cells[c].get(p))) for p in SEA if p in cells[c]}
        print(f"   {c}: {n}")
    if not any(cells[c].get("sea3") for c in ISLAND):
        print("\nno shallow ring deployed -- redeploy the isthmus WITHOUT --deepen-shallow first")
        return 2

    # Local harvest: the study's own tolerates no missing part, and donor (6,7) has no
    # sea5 at all. Same logic, same verbatim-first rule, skipping absent blocks.
    print("\nharvesting the donor's own sea5 termination vocabulary...")
    per = defaultdict(list)
    for (dx, dy) in DONORS:
        try:
            bm = X.read_block(dx, dy, disc=1, part="sea5")
        except ValueError as e:
            if "mesh not found" not in str(e):
                raise
            print(f"   donor ({dx},{dy}): no sea5 part -- skipped")
            continue
        corners = defaultdict(dict)
        for tri in bm.tris:
            i, j = WR.cell_of([sum(bm.verts[k][0] for k in tri) / 3, 0,
                               sum(bm.verts[k][2] for k in tri) / 3])
            for k in tri:
                corners[(i, j)][WR.corner_of(bm.verts[k], i, j)] = tuple(bm.uvs[k])
        for d in corners.values():
            if all(c in d for c in ((0, 0), (1, 0), (1, 1), (0, 1))):
                fit = W._fit_tile(d)
                if fit:
                    u0, u1, v0, v1, name = fit
                    per[(W._strip_of(v0), name)].append(
                        {c: d[c] for c in ((0, 0), (1, 0), (1, 1), (0, 1))})
    variants = {}
    for key, maps in per.items():
        rep = maps[0]
        spread = max((abs(m[c][k] - rep[c][k]) for m in maps for c in rep for k in (0, 1)),
                     default=0.0)
        if spread > 1e-4:
            print(f"   variant {key}: intra-variant uv spread {spread:.4f} -- NOT "
                  f"self-consistent, refusing to harvest it verbatim")
            continue
        variants[key] = rep
    print(f"   {len(variants)} verbatim variants: {sorted(variants)}")

    SHADE, WATER = WR._shade_water_maps(cells)
    # the rim = every water cell on the island's OUTER frame whose deep-set is non-empty
    xs = sorted({b[0] for b in ISLAND})
    ys = sorted({b[1] for b in ISLAND})
    plan = defaultdict(dict)
    kinds = Counter()
    for (bx, by) in ISLAND:
        for i in range(G):
            for j in range(G):
                if not WATER[(bx, by)][i][j]:
                    continue
                sh = SHADE[(bx, by)][i][j]
                if sh not in ("sea3", "sea5"):
                    continue
                # only OUTER-frame cells can face the generic ring
                on_frame = ((bx == xs[0] and i == 0) or (bx == xs[-1] and i == G - 1)
                            or (by == ys[0] and j == 0) or (by == ys[-1] and j == G - 1))
                if not on_frame:
                    continue
                ds = WR.land_deepset(SHADE, WATER, bx, by, i, j)
                if not ds:
                    continue
                if len(ds) == 4:
                    plan[(bx, by)][(i, j)] = ("sea4", None)
                    kinds[f"{sh}->sea4"] += 1
                else:
                    plan[(bx, by)][(i, j)] = ("sea5", ds)
                    kinds[f"{sh}->sea5"] += 1
    total = sum(len(v) for v in plan.values())
    print(f"\nrim plan: {total} quads  {dict(kinds)}")
    for c in ISLAND:
        if plan.get(c):
            print(f"   {c}: {len(plan[c])} quads")
    if not total:
        print("   nothing to retile")
        return 0

    # A deep-set names a WANG TILE via DEEPSET2TILE, which lists the (strip, rot) variants
    # that realise it. The harvest is keyed the same way, so coverage is: does the donor's
    # own vocabulary contain at least one variant for every deep-set the plan needs?
    need, missing = set(), []
    for cs in plan.values():
        for (_sh, ds) in cs.values():
            if ds:
                need.add(ds)
    for ds in sorted(need, key=lambda s: "".join(sorted(s))):
        opts = W.DEEPSET2TILE.get(ds, [])
        have = [o for o in opts if tuple(o) in variants]
        tag = "".join(sorted(ds))
        if not opts:
            missing.append(f"{tag} (no lawful tile: a 2-opposite channel)")
        elif not have:
            missing.append(f"{tag} (needs {opts}, donor has none)")
    print(f"\ndeep-sets the plan needs: {sorted(''.join(sorted(d)) for d in need)}")
    if missing:
        print("  NOT COVERED by the donor's own tiles:")
        for m in missing:
            print(f"    {m}")
        print("  -> a deep-set with no verbatim donor tile must NOT be synthesized "
              "(that is what produced the checkerboard). Report and stop.")
    else:
        print("  all covered VERBATIM from the donor's own sea5 tiles")

    if missing:
        return 2

    # ---- apply: move each flagged quad to sea5 and re-uv from the harvested tile -------
    post, changed = {}, defaultdict(set)
    for (bx, by), cellplan in plan.items():
        pre = cells[(bx, by)]
        shade = WR.wf.parts_shade_grid(pre)
        buckets = {part: WR.part_tris(pre.get(part)) for part in SEA}
        for (i, j), (tsh, ds) in cellplan.items():
            src = shade[i][j]
            uvmap = variants[tuple(W.DEEPSET2TILE[ds][0])]
            moved = [e for e in buckets[src] if e[0] == (i, j)]
            if not moved:
                print(f"  apply: no {src} tris at ({bx},{by}) {(i, j)} -- skipped")
                continue
            buckets[src] = [e for e in buckets[src] if e[0] != (i, j)]
            for [_c, verts, topo] in moved:
                nv = []
                for (p, n, _u, t) in verts:
                    c = WR.corner_of(p, i, j)
                    c = (min(max(c[0], 0), 1), min(max(c[1], 0), 1))
                    nv.append((p, n, uvmap[c], t))      # VERBATIM donor uv, verts untouched
                buckets["sea5"].append([_c, nv, topo])
            changed[(bx, by)].add((i, j))
        post[(bx, by)] = {p: WR.build_part([e[1] for e in buckets[p]], p.capitalize(),
                                           bx, by, DISC)
                          for p in SEA if pre.get(p) is not None}

    # ---- the non-regression gate: geometry is a pure REPARTITION ----------------------
    ok = True
    for c in post:
        def multiset(d):
            return Counter((tuple(round(x, 4) for x in v[0]), t)
                           for p in SEA if d.get(p) is not None
                           for [_i, vs, t] in WR.part_tris(d[p]) for v in vs)
        before = multiset(cells[c])
        after = multiset({p: post[c][p] for p in post[c]})
        if before != after:
            print(f"  GATE repartition[{c}]: FAIL -- geometry changed, not a pure re-shade")
            ok = False
    print(f"\nGATE repartition: {'ok -- verts+topo multiset identical per cell' if ok else 'FAIL'}")
    if not ok:
        return 2

    if not args.apply:
        print(f"\ndry run -- {sum(len(v) for v in changed.values())} quads would be "
              f"re-tiled, nothing written. Re-run with --apply.")
        return 0

    for (bx, by), parts in post.items():
        d = rdir(by)
        for part, bm in parts.items():
            p = d / f"Block[{bx}][{by}] {part.capitalize()}.ff9mesh"
            bak = p.with_suffix(".ff9mesh.prerim")
            if p.exists() and not bak.exists():
                shutil.copy2(p, bak)
            M.write_ff9mesh(bm, p)
            print(f"  wrote {p.name}")
    print("\nRELAUNCH (or exit+re-enter the overworld) to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
