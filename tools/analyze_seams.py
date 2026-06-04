#!/usr/bin/env python3
"""Research: characterize how real FF9 multi-floor walkmeshes wire their CROSS-FLOOR seams.

For each field's .bgi, find every neighbor link that crosses a floor boundary and classify the
connecting edge:
  * shared-INDEX  -- the two triangles reference the same vertex indices (floors NOT disjoint there)
  * coincident    -- different indices but the edge endpoints are at the SAME world positions
  * bridge        -- endpoints at DIFFERENT world positions (ladder/step/warp; geometry can't express)
Also reports per-floor vertex-set disjointness and edge flags on seam edges.

This validates the WALKMESH_EDITING.md v2 spec's key assumption (position-keying recovers seams).
Usage:  py tools/analyze_seams.py [field-name-or-bgi-path ...]
With no args, analyzes the imported walkmeshes on disk + the test fixture.
"""
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1] / "ff9mapkit"
sys.path.insert(0, str(KIT))
from ff9mapkit.scene import bgi
from ff9mapkit.scene.bgi import SLOT_PAIRS

ROOT = Path(__file__).resolve().parents[1]


def load_bgi(arg):
    """arg may be a .bgi path or a field name (extract its walkmesh via UnityPy)."""
    p = Path(arg)
    if p.is_file():
        return arg, bgi.BgiWalkmesh.from_bytes(p.read_bytes())
    from ff9mapkit import extract
    _, _, roles, env = extract.find_field(arg)
    raw = extract._raw_bytes(env.container[roles["bgi"]].read())
    return arg, bgi.BgiWalkmesh.from_bytes(raw)


def analyze(label, wm):
    wv = wm.world_verts()
    vf = wm.vert_floor_map()
    floor_of_tri = {}
    for fi, fl in enumerate(wm.floors):
        for ti in fl.tri_ndx_list:
            floor_of_tri[ti] = fi

    # per-floor vertex sets (disjoint?)
    floor_vtx = {fi: set() for fi in range(len(wm.floors))}
    for ti, fi in floor_of_tri.items():
        if 0 <= ti < len(wm.tris):
            floor_vtx[fi].update(wm.tris[ti].vtx)
    shared_vtx_between_floors = 0
    fids = list(floor_vtx)
    for a in range(len(fids)):
        for b in range(a + 1, len(fids)):
            shared_vtx_between_floors += len(floor_vtx[fids[a]] & floor_vtx[fids[b]])

    seen = set()
    n_shared_idx = n_coincident = n_bridge = 0
    flags_seen = set()
    bridges = []
    for ti, t in enumerate(wm.tris):
        fa = floor_of_tri.get(ti)
        for k in range(3):
            nb = t.nbr[k]
            if nb < 0 or nb >= len(wm.tris):
                continue
            fb = floor_of_tri.get(nb)
            if fa == fb:
                continue
            key = (min(ti, nb), max(ti, nb))
            if key in seen:
                continue
            seen.add(key)
            ai, aj = SLOT_PAIRS[k]
            av = (t.vtx[ai], t.vtx[aj])
            eclone = wm.edges[t.edge[k]].clone if 0 <= t.edge[k] < len(wm.edges) else -1
            flags_seen.add(wm.edges[t.edge[k]].flags if 0 <= t.edge[k] < len(wm.edges) else 0)
            if 0 <= eclone < 3:
                bi, bj = SLOT_PAIRS[eclone]
                bv = (wm.tris[nb].vtx[bi], wm.tris[nb].vtx[bj])
            else:
                bv = (-1, -1)
            shared = set(av) & set(bv)
            pa = sorted([wv[av[0]], wv[av[1]]])
            pb = sorted([wv[bv[0]], wv[bv[1]]]) if bv != (-1, -1) else None
            if shared:
                n_shared_idx += 1
            elif pb is not None and pa == pb:
                n_coincident += 1
            else:
                n_bridge += 1
                if len(bridges) < 4:
                    bridges.append((fa, fb, pa, pb))

    print(f"\n=== {label} ===")
    print(f"  floors={len(wm.floors)} tris={len(wm.tris)} verts={len(wm.verts)} "
          f"| floors disjoint-verts: {'YES' if shared_vtx_between_floors == 0 else f'NO ({shared_vtx_between_floors} shared)'}")
    print(f"  cross-floor seams: {len(seen)}  -> shared-index={n_shared_idx} coincident-pos={n_coincident} bridge={n_bridge}")
    print(f"  seam-edge flags seen: {sorted(flags_seen)}")
    for (fa, fb, pa, pb) in bridges:
        print(f"    bridge floor{fa}<->floor{fb}: A{pa}  B{pb}")
    return dict(floors=len(wm.floors), seams=len(seen), shared=n_shared_idx,
                coincident=n_coincident, bridge=n_bridge)


def main():
    args = sys.argv[1:]
    if not args:
        args = [str(p) for p in [
            ROOT / "tools/scroll_out/grgr_edit/walkmesh.bgi",
            ROOT / "tools/scroll_out/brmc_import/walkmesh.bgi",
            ROOT / "tools/scroll_out/bmvl_import/walkmesh.bgi",
            ROOT / "tools/scroll_out/glgv_import/walkmesh.bgi",
            KIT / "tests/fixtures/editor_multifloor.bgi.bytes",
        ] if p.is_file()]
    rows = []
    for a in args:
        try:
            label, wm = load_bgi(a)
            rows.append(analyze(Path(label).parent.name or label, wm))
        except Exception as e:
            print(f"\n=== {a} ===\n  ERROR: {e}")
    multi = [r for r in rows if r["floors"] > 1]
    if multi:
        print(f"\n--- SUMMARY ({len(multi)} multi-floor) ---")
        print(f"  total cross-floor seams: {sum(r['seams'] for r in multi)}")
        print(f"  shared-index={sum(r['shared'] for r in multi)} "
              f"coincident-pos={sum(r['coincident'] for r in multi)} bridge={sum(r['bridge'] for r in multi)}")


if __name__ == "__main__":
    main()
