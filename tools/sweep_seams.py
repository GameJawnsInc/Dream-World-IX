#!/usr/bin/env python3
"""Sweep EVERY FF9 field's walkmesh and characterize cross-floor seams game-wide.

The WALKMESH_EDITING.md v2 spec assumes cross-floor seams can be reconciled by world POSITION. This
sweep checks that assumption across all ~674 fields: does any field ever use a BRIDGE seam (endpoints
at different positions), a non-default seam edge FLAG, or NON-disjoint floor vertex sets? Opens each
p0data bundle once (groups fields by bundle), so it's a few minutes, not per-field.

Usage:  py tools/sweep_seams.py
"""
import os
import sys
from collections import Counter
from pathlib import Path

KIT = Path(__file__).resolve().parents[1] / "ff9mapkit"
sys.path.insert(0, str(KIT))
from ff9mapkit import extract
from ff9mapkit.scene import bgi
from ff9mapkit.scene.bgi import SLOT_PAIRS


def classify(wm):
    wv = wm.world_verts()
    floor_of_tri = {}
    floor_vtx = {}
    for fi, fl in enumerate(wm.floors):
        floor_vtx.setdefault(fi, set())
        for ti in fl.tri_ndx_list:
            floor_of_tri[ti] = fi
            if 0 <= ti < len(wm.tris):
                floor_vtx[fi].update(wm.tris[ti].vtx)
    fids = list(floor_vtx)
    shared_vtx = sum(len(floor_vtx[fids[a]] & floor_vtx[fids[b]])
                     for a in range(len(fids)) for b in range(a + 1, len(fids)))
    seen = set()
    shared_idx = coincident = bridge = 0
    flags = set()
    for ti, t in enumerate(wm.tris):
        fa = floor_of_tri.get(ti)
        for k in range(3):
            nb = t.nbr[k]
            if nb < 0 or nb >= len(wm.tris) or floor_of_tri.get(nb) == fa:
                continue
            key = (min(ti, nb), max(ti, nb))
            if key in seen:
                continue
            seen.add(key)
            ai, aj = SLOT_PAIRS[k]
            av = (t.vtx[ai], t.vtx[aj])
            e = t.edge[k]
            flags.add(wm.edges[e].flags if 0 <= e < len(wm.edges) else 0)
            eclone = wm.edges[e].clone if 0 <= e < len(wm.edges) else -1
            if 0 <= eclone < 3:
                bi, bj = SLOT_PAIRS[eclone]
                bv = (wm.tris[nb].vtx[bi], wm.tris[nb].vtx[bj])
            else:
                bv = (-1, -1)
            if set(av) & set(bv):
                shared_idx += 1
            elif bv != (-1, -1) and sorted([wv[av[0]], wv[av[1]]]) == sorted([wv[bv[0]], wv[bv[1]]]):
                coincident += 1
            else:
                bridge += 1
    return dict(floors=len(wm.floors), seams=len(seen), shared_idx=shared_idx,
                coincident=coincident, bridge=bridge, flags=flags, shared_vtx=shared_vtx)


def main():
    index = extract.build_field_index(verbose=True)         # folder -> bundle basename
    sa = extract._streaming_assets()
    by_bundle = {}
    for folder, bn in index.items():
        by_bundle.setdefault(bn, []).append(folder)
    UnityPy = extract._unitypy()

    n = multi = 0
    agg = Counter()
    floor_hist = Counter()
    bridges, flagged, nondisjoint, errs = [], [], [], []
    for bi, (bn, folders) in enumerate(sorted(by_bundle.items())):
        try:
            env = UnityPy.load(str(sa / bn))
        except Exception as e:
            errs.append((bn, str(e))); continue
        # map folder -> bgi container key
        bgi_key = {}
        for k in env.container:
            kl = k.lower()
            if kl.endswith(".bgi.bytes"):
                m = kl.split("fieldmaps/")
                if len(m) > 1:
                    bgi_key[m[1].split("/")[0]] = k
        print(f"  [{bi + 1}/{len(by_bundle)}] {bn}: {len(folders)} fields", flush=True)
        for folder in folders:
            key = bgi_key.get(folder)
            if not key:
                continue
            try:
                wm = bgi.BgiWalkmesh.from_bytes(extract._raw_bytes(env.container[key].read()))
                c = classify(wm)
            except Exception as e:
                errs.append((folder, str(e))); continue
            n += 1
            floor_hist[c["floors"]] += 1
            if c["floors"] > 1:
                multi += 1
                agg["seams"] += c["seams"]; agg["shared_idx"] += c["shared_idx"]
                agg["coincident"] += c["coincident"]; agg["bridge"] += c["bridge"]
                if c["bridge"]:
                    bridges.append((folder, c["bridge"], c["seams"]))
                if c["flags"] - {0}:
                    flagged.append((folder, sorted(c["flags"])))
                if c["shared_vtx"]:
                    nondisjoint.append((folder, c["shared_vtx"]))

    print(f"\n===== SWEEP: {n} fields analyzed, {multi} multi-floor =====")
    print(f"floor-count histogram: {dict(sorted(floor_hist.items()))}")
    print(f"cross-floor seams (multi-floor): total={agg['seams']} "
          f"shared-index={agg['shared_idx']} coincident-pos={agg['coincident']} BRIDGE={agg['bridge']}")
    print(f"\nfields with BRIDGE seams ({len(bridges)}): {bridges[:30]}")
    print(f"fields with NON-DEFAULT seam-edge flags ({len(flagged)}): {flagged[:30]}")
    print(f"fields with NON-DISJOINT floor verts ({len(nondisjoint)}): {nondisjoint[:30]}")
    if errs:
        print(f"\nerrors ({len(errs)}): {errs[:10]}")


if __name__ == "__main__":
    main()
