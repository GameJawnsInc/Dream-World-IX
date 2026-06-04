#!/usr/bin/env python3
"""Smoke-test the WALKMESH_EDITING.md v2 reconcile OFFLINE, before building it for real.

For each field: (1) take the original .bgi; (2) simulate a geometry-only obj round-trip
(world_verts -> bgi.build -> intra-floor links only, cross-floor seams LOST); (3) extract seams from
the ORIGINAL keyed by world-position edge pairs; (4) reconcile them onto the geometry-only mesh by
position match. Then assert connectivity is reproduced: all floors reachable again AND the cross-floor
link set matches the original. Proves position-keying recovers seams (coincident AND vertical-bridge).

Usage:  py tools/smoke_reconcile.py [field-name-or-bgi-path ...]
"""
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1] / "ff9mapkit"
sys.path.insert(0, str(KIT))
from ff9mapkit import extract
from ff9mapkit.scene import bgi
from ff9mapkit.scene.bgi import SLOT_PAIRS

ROOT = Path(__file__).resolve().parents[1]


def load(arg):
    p = Path(arg)
    if p.is_file():
        return Path(arg).parent.name, bgi.BgiWalkmesh.from_bytes(p.read_bytes())
    _, _, roles, env = extract.find_field(arg)
    return arg, bgi.BgiWalkmesh.from_bytes(extract._raw_bytes(env.container[roles["bgi"]].read()))


def floor_of_tri(wm):
    return {ti: fi for fi, fl in enumerate(wm.floors) for ti in fl.tri_ndx_list}


def edge_world(wm, wv, ti, slot):
    i, j = SLOT_PAIRS[slot]
    return tuple(sorted([wv[wm.tris[ti].vtx[i]], wv[wm.tris[ti].vtx[j]]]))


def cross_floor_links(wm):
    """Set of (floorA,floorB, a_edge_world, b_edge_world) for every cross-floor neighbor link."""
    wv = wm.world_verts(); fo = floor_of_tri(wm); out = set(); seen = set()
    for ti, t in enumerate(wm.tris):
        fa = fo.get(ti)
        for k in range(3):
            nb = t.nbr[k]
            if nb < 0 or fo.get(nb) == fa:
                continue
            key = (min(ti, nb), max(ti, nb))
            if key in seen:
                continue
            seen.add(key)
            ec = wm.edges[t.edge[k]].clone if 0 <= t.edge[k] < len(wm.edges) else -1
            a, b = edge_world(wm, wv, ti, k), (edge_world(wm, wv, nb, ec) if 0 <= ec < 3 else None)
            fb = fo.get(nb)
            out.add((min(fa, fb), max(fa, fb), a, b) if (fa, a) <= (fb, b or a) else (fb, fa, b, a))
    return out


def reconcile(geom, seams):
    """Apply position-keyed seams onto a geometry-only mesh (intra-floor links already built)."""
    wv = geom.world_verts(); fo = floor_of_tri(geom)
    lut = {}                                            # (floor, edge_world) -> (tri, slot)
    for ti in range(len(geom.tris)):
        for k in range(3):
            lut[(fo[ti], edge_world(geom, wv, ti, k))] = (ti, k)
    linked = missing = 0
    for (fa, fb, a_edge, b_edge) in seams:
        ta, tb = lut.get((fa, a_edge)), lut.get((fb, b_edge)) if b_edge else None
        if ta and tb:
            (ia, sa), (ib, sb) = ta, tb
            geom.tris[ia].nbr[sa] = ib; geom.tris[ib].nbr[sb] = ia
            geom.edges[geom.tris[ia].edge[sa]].clone = sb
            geom.edges[geom.tris[ib].edge[sb]].clone = sa
            linked += 1
        else:
            missing += 1
    return linked, missing


def smoke(label, orig):
    # 1) geometry-only obj round-trip (the lossy path)
    wv = orig.world_verts()
    faces = [tuple(t.vtx) for t in orig.tris]
    fids = [t.floor_ndx for t in orig.tris]
    geom = bgi.build([(int(x), int(y), int(z)) for (x, y, z) in wv], faces, floor_ids=fids)
    lost = geom.reachable_floors()
    # 2) extract seams from ORIGINAL, 3) reconcile onto geometry-only
    seams = cross_floor_links(orig)
    linked, missing = reconcile(geom, seams)
    # 4) verify
    ok_reach = geom.reachable_floors() == orig.all_floors()
    ok_links = cross_floor_links(geom) == cross_floor_links(orig)
    print(f"{label:32s} floors={len(orig.floors):2d} seams={len(seams):3d} | "
          f"geom-only reachable={len(lost)} -> reconciled reachable={len(geom.reachable_floors())}/{len(orig.all_floors())} "
          f"| linked={linked} missing={missing} | reach_ok={ok_reach} links_ok={ok_links} "
          f"{'PASS' if ok_reach and ok_links and missing == 0 else 'FAIL'}")
    return ok_reach and ok_links and missing == 0


def main():
    args = sys.argv[1:] or [
        str(ROOT / "tools/scroll_out/grgr_edit/walkmesh.bgi"),
        str(ROOT / "tools/scroll_out/bmvl_import/walkmesh.bgi"),
        str(KIT / "tests/fixtures/editor_multifloor.bgi.bytes"),
        "udft_map120_uf_ent",          # the 23-floor vertical-bridge field
    ]
    results = []
    for a in args:
        try:
            label, wm = load(a)
            if len(wm.floors) > 1:
                results.append(smoke(label, wm))
        except Exception as e:
            print(f"{a}: ERROR {e}")
    print(f"\n{sum(results)}/{len(results)} fields reconciled cleanly")


if __name__ == "__main__":
    main()
