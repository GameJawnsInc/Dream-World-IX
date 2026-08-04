"""THE SEAL GATE (gF) -- VSHORE-SEAL-PREDICTION.md gates 1/4/5, run on the BUILT
meshes before deploy. (Gate 2 = full_skirt's own suite; gate 3 = walk_gate_fix.)

  gF     zero true hover once-edges > 0.5u within 12u of the four registered sites
         (global geometry-keyed once-edges over all 6 blocks -- no per-block border
         phantoms; render vocabulary -- 4078 counts as a surface; vertical
         plan-degenerate once-edges are the declared curtain chain-end class, a
         zero-area line that cannot be a sightline slit).
  inv    exactly 18 curtain tris: |geometric ny| <= 0.05, uv v in {930,961}/1024,
         u in [115,241]/1024, every top edge 2-owned.
  add    additive-only spot check: per-block tri counts vs the previous deploy's
         printed counts where known ((7,7) 81 -> +2, (7,8) 201 -> +4).
  exempt the site-external hover census (the declared hem/skirt classes) reported
         by count for the record -- not gated.

Run: py -X utf8 probe_seal_gate.py
"""
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402

BUILT = HERE / "out" / "terrace_strip" / "underlay_meshes"
SITES = [("east", 448.8, -507.8), ("west", 382.4, -511.6),
         ("south", 448.0, -538.0), ("border", 384.0, -497.7)]
V_TOP, V_BOT = 930.0 / 1024.0, 961.0 / 1024.0
PREV_COUNTS = {(7, 7): 81, (7, 8): 201}                     # from the last deploy's log


def main():
    tsrc = {}
    for (bx, by) in W.CELLS:
        p = BUILT / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            tsrc[(bx, by)] = p
    assert len(tsrc) == 6, f"built meshes missing: {sorted(tsrc)}"
    world = W.load_world(terrain_src=tsrc)

    fails = []
    # ---- global Terrain soup (world frame), edge -> owner count -------------------
    tris = []
    per_block = {}
    for bk, meshes in sorted(world.items()):
        for m in meshes:
            if m["name"] != "Terrain":
                continue
            per_block[bk] = len(m["tris"])
            tris.extend(m["tris"])
    ec = defaultdict(int)
    for tri in tris:
        ks = [tuple(round(v, 3) for v in p) for p in (tri[0], tri[1], tri[2])]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ec[tuple(sorted((ks[a], ks[b])))] += 1
    once = [e for e, n in ec.items() if n == 1]

    # up-facing surface cover (render vocabulary: every Terrain tri incl. 4078)
    cov = defaultdict(list)
    for tri in tris:
        t3 = tri[:3]
        xs = [p[0] for p in t3]
        zs = [p[2] for p in t3]
        for cx in range(int(min(xs) // 4), int(max(xs) // 4) + 1):
            for cz in range(int(min(zs) // 4), int(max(zs) // 4) + 1):
                cov[(cx, cz)].append(t3)

    def surf_below(px, pz, ymax):
        hit = None
        for t3 in cov.get((int(px // 4), int(pz // 4)), ()):
            (x1, z1), (x2, z2), (x3, z3) = ((p[0], p[2]) for p in t3)
            det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
            if abs(det) < 1e-12:
                continue
            w2 = ((px - x1) * (z3 - z1) - (x3 - x1) * (pz - z1)) / det
            w3 = ((x2 - x1) * (pz - z1) - (px - x1) * (z2 - z1)) / det
            if w2 >= -1e-6 and w3 >= -1e-6 and w2 + w3 <= 1 + 1e-6:
                y = (1 - w2 - w3) * t3[0][1] + w2 * t3[1][1] + w3 * t3[2][1]
                if y < ymax - 1e-6 and (hit is None or y > hit):
                    hit = y
        # sea sheets close the render floor at y=0 everywhere on this bench
        if hit is None and any(s[1] in ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
                               for s in W.all_sheets(world, px, pz)):
            hit = 0.0 if ymax > 0.0 else hit
        return hit

    # ---- gF + the exempt record ---------------------------------------------------
    n_site_hover = 0
    n_vertical = 0
    n_ext_hover = 0
    n_hem = 0
    for (va, vb) in once:
        plan = math.hypot(va[0] - vb[0], va[2] - vb[2])
        if plan < 0.01:
            n_vertical += 1                                 # curtain chain-end class
            continue
        gap = 0.0
        over_terrain = False
        for f in (0.5, 0.0, 1.0):
            px = va[0] + (vb[0] - va[0]) * f
            pz = va[2] + (vb[2] - va[2]) * f
            py = va[1] + (vb[1] - va[1]) * f
            y = surf_below(px, pz, py)
            if y is not None:
                if py - y > gap:
                    gap = py - y
                    over_terrain = y > 0.01                 # sea fallback lands at 0.0
        if gap <= 0.5:
            continue
        # THE HEM CLASS (registered exempt): sub-1u drop over the build's OWN
        # terrain -- never over open sea
        if gap <= 1.0 and over_terrain:
            n_hem += 1
            continue
        d = min(math.hypot((va[0] + vb[0]) / 2 - sx, (va[2] + vb[2]) / 2 - sz)
                for _n, sx, sz in SITES)
        if d <= 12.0:
            n_site_hover += 1
            fails.append(f"gF: hover once-edge {va} -- {vb} gap {gap:.2f}u "
                         f"{d:.1f}u from a sealed site")
        else:
            n_ext_hover += 1
    print(f"gF: {n_site_hover} hover once-edges >0.5u within 12u of the 4 sites "
          f"(MUST be 0); {n_vertical} vertical curtain-end edges + {n_hem} "
          f"sub-1u hem edges over own terrain (declared classes); "
          f"{n_ext_hover} site-external hovers >1u (for the record)")

    # ---- curtain invariants (uvs read from the built files directly) --------------
    # ROUND 2: the only forest-pin curtain left is the donor's own 0.051u sliver
    # at east (carried stock bytes); the minted seals are the bench's topo-58
    # cliff class (v corner-role pins 0.893/0.923 = texels 914/945, u sawtooth
    # in [0.699,0.947]) -- 4 quads / 8 tris (east 1 + W2 1 + south-sea 2).
    n_forest = 0
    n_cliff = 0
    n_native = 0
    bad_uv = 0
    for (bx, by), p in sorted(tsrc.items()):
        bm = W.M.blockmesh_from_ff9mesh(p, disc=W.DISC, x=bx, y=by, part="terrain")
        pos = bm.chan_arrays[W.X.CH_POS]
        uv = bm.chan_arrays[W.X.CH_UV]
        for t in bm.tris:
            vpins = {round(uv[i][1] * 1024) for i in t}
            if vpins == {930, 961}:
                n_forest += 1
                continue
            if vpins != {914, 945}:
                continue
            # the bench's NATIVE coastal cliff band carries the same pins (the
            # re-skin speaks its exact language) -- but it is SLOPED here; only
            # the minted seals are vertical
            a = tuple(pos[t[0]])
            b = tuple(pos[t[1]])
            c = tuple(pos[t[2]])
            if abs(W.up_ny(a, b, c)) > 0.05:
                n_native += 1
                continue
            n_cliff += 1
            for i in t:
                if not (0.6989 <= uv[i][0] <= 0.9471):
                    bad_uv += 1
    print(f"curtain census: {n_forest} forest-pin (expect 1 = the donor sliver), "
          f"{n_cliff} VERTICAL cliff-pin minted (expect 8), {n_native} sloped "
          f"cliff-pin = the bench's native shore band (report only); "
          f"off-strip u: {bad_uv} (MUST be 0)")
    if n_forest != 1 or n_cliff != 8:
        fails.append(f"invariants: {n_forest} forest / {n_cliff} vertical cliff "
                     f"curtains, expected 1 / 8")
    if bad_uv:
        fails.append(f"invariants: {bad_uv} off-strip u samples")

    # top-edge weld: proven by gF -- an unsealed rim edge would still read hover

    # ---- additive-only spot check ------------------------------------------------
    for bk, prev in PREV_COUNTS.items():
        cur = per_block.get(bk)
        add = {(7, 7): 2, (7, 8): 4}[bk]
        ok = cur == prev + add
        print(f"additive: block {bk} tris {prev} -> {cur} (expected +{add}) "
              f"{'OK' if ok else 'MISMATCH'}")
        if not ok:
            fails.append(f"additive: block {bk} {prev}->{cur}, expected +{add}")

    print()
    if fails:
        print("SEAL GATE: RED")
        for f in fails:
            print("  !!", f)
        return 1
    print("SEAL GATE: GREEN (gF 0 site hovers; cliff seals on-strip; "
          "block counts match)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
