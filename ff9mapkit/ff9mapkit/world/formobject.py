"""A CUSTOM FORM CELL'S BUILDING IN FORM 2 (engine patches s92 + s93; ``world-forms --building2``).

An armed custom form cell (``world-forms --arm``) keeps its form-1 building in form 2 unless a loose ``Object2``
replaces it there. This module writes that ``Object2`` -- a blank (the building is gone) or a seated OBJ (another
building) -- together with the cell's ``Terrain2`` it needs:

* REMOVING A STOCK BUILDING LEAVES A HOLE. Every stock building plugs a hole in its cell's ground: over the 59 disc-1
  cells with an Object, nothing else answers the ground query under 90% of the building's footprint
  (``studies/terrain-malleability/forms/object2_census.py``). So the form-2 ground is the form-1 ground with that
  hole FILLED from the tiles around it: the hole's edge tiles are split at the 4u tile lines (each split keeps its
  tile's look exactly), and :func:`ff9mapkit.world.coastmorph._tiled_fill_region` -- the coast morphs' gated tile
  carry -- fills the hole from the nearby tiles that map cleanly onto one atlas rect. A hole that reaches the cell's
  edge, or one the fill's gates refuse, is refused here, before anything is written.
* A NEW BUILDING renders only (``Object2`` tris carry IDALL 4078, which the ground query skips); the ground under its
  footprint is made impassable (topograph 59, split exactly at the footprint), as ``world-entrance --building`` does.
* On a cell with NO stock building the engine needs s93 to show an ``Object2`` at all (s92 reads one only where the
  cell has a stock Object). A kit building (a loose ``Object`` on such a cell) is refused: its footprint's topograph
  59 is baked into the ground both forms start from.
"""
from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

#: a hole edge longer than this is halved (with the tile that owns it), so the fill's grain gate sees stock spacing
MAX_RING_EDGE = 4.0
#: how far from the hole the fill looks for clean source tiles (world units)
SOURCE_RADIUS = 20.0
#: the coverage check's sample pitch (world units) and the largest uncovered area it lets pass (square units)
SAMPLE = 0.5
MAX_UNCOVERED = 0.5
#: the IDALL a render-only building carries (the ground query skips it: placement.IDALL_SKIP)
RENDER_ONLY_IDALL = 4078
BLOCKED_TOPO = 59


def _pk(p):
    return (round(p[0], 4), round(p[1], 4), round(p[2], 4))


def _xz(p):
    return (round(p[0], 3), round(p[2], 3))


def _to_local(tris, bx, by):
    return [[((p[0] - 64.0 * bx, p[1], p[2] + 64.0 * by), n, u, t) for (p, n, u, t) in tri] for tri in tris]


def aperture_rings(ter, obj, open_pts) -> list:
    """The holes in ``ter`` (world triangle soup) that ``obj`` plugs: boundary cycles whose every vertex is an ``obj``
    vertex (plan match to 1e-3) and that enclose a point of ``open_pts`` (the building's footprint where ``ter`` has no
    ground). The second test tells a HOLE from the outer edge of a patch of ground the building surrounds, whose
    vertices are all the building's too."""
    from .coastmorph import _in_poly
    from .meshedit import boundary_cycles
    okeys = {_xz(v[0]) for t in obj for v in t}
    out = []
    for r in boundary_cycles([[(v[0],) for v in t] for t in ter]):
        if not all(_xz(p) in okeys for p in r):
            continue
        poly = [(p[0], p[2]) for p in r]
        if any(_in_poly(px, pz, poly) for px, pz in open_pts):
            out.append(list(r))
    return out


def _split_edge_owner(ter, ka, kb, t):
    """Split the one tri that owns boundary edge ``ka``-``kb`` at parameter ``t``; returns the new vertex."""
    from .transplant import _lerp_vert
    for i, tri in enumerate(ter):
        ks = [_pk(v[0]) for v in tri]
        if ka in ks and kb in ks:
            ia, ib = ks.index(ka), ks.index(kb)
            vp = _lerp_vert(tri[ia], tri[ib], t)
            t1, t2 = list(tri), list(tri)
            t1[ib] = vp
            t2[ia] = vp
            ter[i] = t1
            ter.append(t2)
            return vp
    raise ValueError("a hole edge has no owning ground tile (the ground is not edge-manifold here)")


def split_ring(ter, ring, *, snap: float | None = None, max_edge: float = MAX_RING_EDGE):
    """Split every hole edge that crosses a 4u tile line deeper than ``snap`` at that line, and every edge longer than
    ``max_edge`` at its midpoint, splitting the ground tile that owns the edge (lerped exactly, so the tile looks the
    same). Returns ``(ter, ring)``: the edited soup (a copy) and the refined ring."""
    from .coastmorph import _BOUNDARY_SNAP
    snap = _BOUNDARY_SNAP if snap is None else snap
    ter = [list(t) for t in ter]
    ring = list(ring)
    for _guard in range(4 * len(ring) + 400):
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            hit = None
            for ax in (0, 2):
                lo, hi = sorted((a[ax], b[ax]))
                for g in range(math.floor(lo / 4.0) + 1, math.ceil(hi / 4.0)):
                    line = 4.0 * g
                    if min(abs(a[ax] - line), abs(b[ax] - line)) > snap:
                        hit = (line - a[ax]) / (b[ax] - a[ax])
                        break
                if hit is not None:
                    break
            if hit is None and math.dist((a[0], a[2]), (b[0], b[2])) > max_edge:
                hit = 0.5
            if hit is None:
                continue
            vp = _split_edge_owner(ter, _pk(a), _pk(b), hit)
            ring.insert(i + 1, vp[0])
            break
        else:
            return ter, ring
    raise ValueError("the hole's edge did not settle onto the tile lines (a kit bug)")


def _orientable(src, snap) -> bool:
    """A source tile the fill can carry: it lies in one 4u cell and its uv map orients onto its own atlas rect (the
    fill's TILE-RECT CONTAINMENT precondition, checked up front so the fill never meets a sheared edge tile)."""
    from .transplant import _affine_uv
    cx = math.floor(sum(v[0][0] for v in src) / 12.0)
    cz = math.floor(sum(v[0][2] for v in src) / 12.0)
    if any(not (4 * cx - snap <= v[0][0] <= 4 * cx + 4 + snap and 4 * cz - snap <= v[0][2] <= 4 * cz + 4 + snap)
           for v in src):
        return False
    us = [v[2][0] for v in src]
    vs = [v[2][1] for v in src]
    if max(us) - min(us) < 1e-6 or max(vs) - min(vs) < 1e-6:
        return False
    rc = ((min(us), min(vs)), (max(us), min(vs)), (min(us), max(vs)), (max(us), max(vs)))
    uvf = _affine_uv(src)
    used = set()
    for gx, gz in ((0, 0), (1, 0), (0, 1), (1, 1)):
        q = uvf(4.0 * cx + 4.0 * gx, 4.0 * cz + 4.0 * gz)
        used.add(min(range(4), key=lambda i: (q[0] - rc[i][0]) ** 2 + (q[1] - rc[i][1]) ** 2))
    return len(used) == 4


def fill_sources(ter, ring) -> list:
    """The tiles the fill may carry: within :data:`SOURCE_RADIUS` of the hole, no event bits (an entrance tile is never
    copied), orientable, and per 4u cell either one look or a pair split on the cell's diagonal (stock's patch-edge
    pair); WALKABLE tiles only when any are near (a removed building leaves walkable ground)."""
    from .coastmorph import _BOUNDARY_SNAP, _uv_rect
    from .extract import decode_id
    from .placement import WALK_OK

    def near(t):
        c = (sum(v[0][0] for v in t) / 3.0, sum(v[0][2] for v in t) / 3.0)
        return min(math.dist(c, (p[0], p[2])) for p in ring) < SOURCE_RADIUS
    ids = lambda t: decode_id(int(round(t[0][3][0])))           # noqa: E731
    cand = [t for t in ter if near(t) and ids(t)["event"] == 0 and _orientable(t, _BOUNDARY_SNAP)]
    walk = [t for t in cand if ids(t)["topograph"] in WALK_OK]
    cand = walk or cand
    by = defaultdict(list)
    for t in cand:
        by[(math.floor(sum(v[0][0] for v in t) / 12.0), math.floor(sum(v[0][2] for v in t) / 12.0))].append(t)
    out = []
    for cell, ts in sorted(by.items()):
        if len({(_uv_rect(s), tuple(s[0][3])) for s in ts}) == 1:
            out += ts
            continue
        if len(ts) != 2:
            continue
        shared = {_pk(v[0]) for v in ts[0]} & {_pk(v[0]) for v in ts[1]}
        cs = {(round((k[0] - 4.0 * cell[0]) / 4.0), round((k[2] - 4.0 * cell[1]) / 4.0)) for k in shared}
        if len(shared) == 2 and cs in ({(0, 0), (1, 1)}, {(1, 0), (0, 1)}):
            out += ts
    return out


def _covers(tris, pts):
    """For each plan point, is it inside an up-facing, non-skipped triangle of ``tris`` (world soup)?"""
    import numpy as np
    from .placement import IDALL_SKIP
    keep = []
    for t in tris:
        (a, b, c) = [v[0] for v in t]
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        if ny / L > 0.1 and int(round(t[0][3][0])) not in IDALL_SKIP:
            keep.append((a, b, c))
    P = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
    hit = np.zeros(len(P), dtype=bool)
    for (a, b, c) in keep:
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        x, z = P[:, 0], P[:, 1]
        w0 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        w1 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        hit |= (w0 >= -1e-9) & (w1 >= -1e-9) & (1 - w0 - w1 >= -1e-9)
    return hit


def footprint_points(obj, cell) -> list:
    """The building's plan footprint on a :data:`SAMPLE` grid: the points where its up-facing tris answer."""
    import numpy as np
    bx, by = cell
    n = int(64 / SAMPLE)
    xs = 64.0 * bx + (np.arange(n) + 0.37) * SAMPLE
    zs = -64.0 * by - (np.arange(n) + 0.61) * SAMPLE
    X_, Z_ = np.meshgrid(xs, zs, indexing="ij")
    pts = np.stack([X_.ravel(), Z_.ravel()], axis=1)
    return pts[_covers(obj, pts)].tolist()


def fill_aperture(ter, obj, cell) -> tuple:
    """``ter`` (world soup) with every hole ``obj`` plugs filled from the ground around it. Returns ``(ter, report)``.
    Raises ``ValueError`` (nothing is lost: the caller writes nothing) when the building's footprint is not all over
    closed holes in the ground, or when a hole's fill fails a gate."""
    from .coastmorph import _tiled_fill_region
    from .extract import decode_id
    foot = footprint_points(obj, cell)
    if not foot:
        raise ValueError("the building has no up-facing surface in this cell -- nothing to take away")
    open_ = ~_covers(ter, foot)
    rings = aperture_rings(ter, obj, [p for p, o in zip(foot, open_) if o])
    report = {"footprint_u2": round(len(foot) * SAMPLE * SAMPLE, 2),
              "hole_u2": round(int(open_.sum()) * SAMPLE * SAMPLE, 2), "rings": [], "fill_tris": 0, "topographs": {}}
    if not open_.any():
        return ter, report                                  # already filled (a re-run): nothing to add
    if not rings:
        raise ValueError(f"the ground under this building is open to the cell's edge (or the building IS the ground "
                         f"there): {report['hole_u2']} u^2 under it has no ground, and none of it is a closed hole "
                         f"the kit can fill -- this building cannot be removed cleanly")
    topo = defaultdict(int)
    for k, ring in enumerate(rings):
        ter, ring2 = split_ring(ter, ring)
        rk = {_pk(p) for p in ring2}
        gnrm = {}
        for t in ter:
            for v in t:
                if _pk(v[0]) in rk:
                    gnrm.setdefault(_pk(v[0]), tuple(v[1]))
        srcs = fill_sources(ter, ring2)
        if not srcs:
            raise ValueError(f"hole {k + 1} of {len(rings)}: no clean ground tile within {SOURCE_RADIUS:g}u to fill it "
                             f"from")
        try:
            emit = _tiled_fill_region(list(ring2), gnrm, srcs)
        except ValueError as e:
            raise ValueError(f"hole {k + 1} of {len(rings)} ({len(ring)} edge points) cannot be filled lawfully: "
                             f"{str(e).splitlines()[0][:240]}") from None
        for t in emit:
            topo[decode_id(int(round(t[0][3][0])))["topograph"]] += 1
        ter = ter + [list(t) for t in emit]
        report["rings"].append({"points": len(ring), "split_to": len(ring2), "fill_tris": len(emit),
                                "sources": len(srcs)})
        report["fill_tris"] += len(emit)
    left = ~_covers(ter, foot)
    gap = round(int(left.sum()) * SAMPLE * SAMPLE, 2)
    report["topographs"] = dict(sorted(topo.items()))
    report["uncovered_u2"] = gap
    if gap > MAX_UNCOVERED:
        raise ValueError(f"after filling its {len(rings)} closed hole(s), {gap} u^2 under this building still has no "
                         f"ground (the rest of the hole reaches the cell's edge) -- it cannot be removed cleanly")
    return ter, report


def _stacked(mod_folder, x, y, part, disc, game):
    from .entrance import read_block_stacked
    return read_block_stacked(mod_folder, x, y, disc=disc, part=part, game=game, missing_ok=True)


def _has_stock(x, y, part, disc, game) -> bool:
    from . import extract as X
    try:
        X.read_block(x, y, disc=disc, part=part, game=game)
        return True
    except (ValueError, FileNotFoundError):
        return False


def plan(mod_folder: str, x: int, y: int, what: str, *, at=None, disc: int = 1, game=None) -> dict:
    """Everything :func:`apply` writes for one disc, computed and gated, nothing written. ``what`` = ``"none"``,
    ``"keep"`` or an OBJ path."""
    from . import mesh as M, terrain as T
    from .forms import SWITCHABLE, custom_condition
    from .transplant import _soup, _soup_block_mesh
    if (x, y) in SWITCHABLE:
        raise ValueError(f"cell ({x},{y}) switches with {SWITCHABLE[(x, y)]}: its form-2 building is that place's "
                         f"own (stock Object2) -- --building2 is for cells armed with world-forms --arm")
    root = T._mod_root(mod_folder, game)
    cond = custom_condition(root, disc, x, y) if root is not None else None
    if not cond:
        raise ValueError(f"Block[{x}][{y}] is not armed on disc {disc}: run world-forms --arm {x} {y} --when "
                         f"\"<condition>\"{'' if disc == 1 else f' --disc {disc}'} first (its form 2 needs a "
                         f"condition)")
    out = {"disc": disc, "cell": [x, y], "condition": cond, "what": what, "writes": {}, "delete": []}
    stock_obj = _has_stock(x, y, "object", disc, game)
    obj_bm = _stacked(mod_folder, x, y, "object", disc, game)
    if what == "keep":
        dep = M.deployed_override(mod_folder, x, y, disc=disc, part="Object2", game=game)
        out["delete"] = [str(dep)] if dep is not None else []
        out["kind"] = "keep"
        return out
    if obj_bm is not None and not stock_obj:
        raise ValueError(f"Block[{x}][{y}]'s building is a kit Object (no stock building here): its footprint's "
                         f"topograph {BLOCKED_TOPO} is baked into the ground both forms start from, so a form-2 "
                         f"building cannot replace it cleanly")
    dep2 = M.deployed_override(mod_folder, x, y, disc=disc, part="Terrain2", game=game)
    base = (M.blockmesh_from_ff9mesh(dep2, disc=disc, x=x, y=y, part="Terrain2") if dep2 is not None
            else _stacked(mod_folder, x, y, "terrain", disc, game))
    if base is None or not getattr(base, "verts", None):
        raise ValueError(f"Block[{x}][{y}] has no ground (a sea cell) -- nothing to stand a form-2 building on")
    ter = _soup(base, x, y)
    report = None
    if stock_obj and obj_bm is not None:
        ter, report = fill_aperture(ter, _soup(obj_bm, x, y), (x, y))
    out["fill"] = report
    hull = None
    if what == "none":
        if not stock_obj:
            raise ValueError(f"Block[{x}][{y}] has no building to remove")
        o2 = M.hidden_block_mesh(name=f"Block[{x}][{y}] Object2", disc=disc, x=x, y=y)
        out["kind"] = "remove"
    else:
        from . import blendio as BIO
        from .entrance import _building_world_box, _building_world_hull
        objp = Path(what)
        if not objp.is_file():
            raise ValueError(f"--building2: no such OBJ (or 'none' / 'keep'): {what}")
        if not BIO.read_obj(str(objp))["V"]:
            raise ValueError(f"--building2: {objp} has no vertices")
        b = {"obj": str(objp), "at": list(at) if at else None}
        centre = (64.0 * x + 32.0, -64.0 * y - 32.0)
        xmin, xmax, zmin, zmax = _building_world_box(b, centre, margin=0.0)
        if not (64.0 * x <= xmin and xmax <= 64.0 * x + 64.0 and -64.0 * y - 64.0 <= zmin and zmax <= -64.0 * y):
            raise ValueError(f"--building2: the OBJ placed at {tuple(b['at'] or centre)} spans "
                             f"x[{xmin:.1f},{xmax:.1f}] z[{zmin:.1f},{zmax:.1f}], outside Block[{x}][{y}] -- move it "
                             f"with --at or make it smaller")
        hull = _building_world_hull(b, centre)
        out["kind"] = "replace" if stock_obj else "add"
        out["building"] = b
        o2 = None                                           # built at apply time, seated on the final Terrain2
    t2 = _soup_block_mesh(f"Block[{x}][{y}] Terrain2", (x, y), _to_local(ter, x, y), disc=disc, lod="0_1")
    if hull is not None:
        t2 = M.split_retarget_by_polygon(t2, hull, topograph=BLOCKED_TOPO, world_origin=(64.0 * x, -64.0 * y))
        out["footprint_blocked"] = sum(
            1 for tri in t2.tris if (int(round(t2.tangents[tri[0]][0])) & 0xFC) >> 2 == BLOCKED_TOPO)
    # THE KEEP GATE (the stitch gate's form for an edit that only ADDS geometry): every vertex position of the ground
    # it starts from survives, so every weld to another part or a neighbour cell holds; and no new vertex lands on the
    # cell's border, where a neighbour would meet it as a T-junction
    pre = {_pk(p) for p in M.world_positions(base, (64.0 * x, -64.0 * y))}
    post_pts = M.world_positions(t2, (64.0 * x, -64.0 * y))
    post = {_pk(p) for p in post_pts}
    lost = len(pre - post)
    edge = sum(1 for p in post_pts if _pk(p) not in pre
               and min(abs(p[0] - 64.0 * x), abs(p[0] - 64.0 * x - 64.0),
                       abs(p[2] + 64.0 * y), abs(p[2] + 64.0 * y + 64.0)) < 0.05)
    out["keep_gate"] = {"vertices": len(pre), "lost": lost, "new_on_border": edge}
    if lost or edge:
        raise ValueError(f"KEEP GATE: the form-2 ground would lose {lost} vertex position(s) of the ground it starts "
                         f"from and put {edge} new one(s) on the cell border -- a kit bug, nothing was written")
    out["writes"] = {"Terrain2": t2, "Object2": o2}
    out["entrances"] = sorted(M.entrance_tags(t2))
    return out


def apply(mod_folder: str, x: int, y: int, what: str, *, at=None, disc: int = 1, game=None,
          dry_run: bool = False, replay_disc4: bool = True, log=print) -> dict:
    """Plan (and unless ``dry_run`` write) the form-2 building of armed custom cell ``(x, y)`` on ``disc``; on disc 1,
    the same edit is replayed on disc 4 when the cell is armed there too. Every disc is planned before the first
    write."""
    from . import mesh as M, terrain as T
    from .forms import custom_condition
    plans = [plan(mod_folder, x, y, what, at=at, disc=disc, game=game)]
    root = T._mod_root(mod_folder, game)
    if disc == 1 and replay_disc4:
        if root is not None and custom_condition(root, 4, x, y):
            plans.append(plan(mod_folder, x, y, what, at=at, disc=4, game=game))
        else:
            plans[0]["disc4"] = "not armed on disc 4: disc 4 keeps this cell as it is (arm it there with --disc 4)"
    if dry_run:
        return {"plans": plans, "dry_run": True}
    for p in plans:
        written = []
        if p["kind"] == "keep":
            for f in p["delete"]:
                Path(f).unlink()
            p["written"] = []
            continue
        t2 = p["writes"]["Terrain2"]
        written.append(str(M.deploy_override(t2, mod_folder=mod_folder, game=game, part="Terrain2", disc=p["disc"])))
        if p["writes"]["Object2"] is not None:
            written.append(str(M.deploy_override(p["writes"]["Object2"], mod_folder=mod_folder, game=game,
                                                 part="Object2", disc=p["disc"])))
        else:
            from . import blendio as BIO, discmirror as DM
            b = p["building"]
            # skip_mirror=REPLAY: this verb plans and writes each disc itself (a copy would skip disc 4's own ground)
            got = BIO.build_from_obj(b["obj"], into_block=(x, y), mod_folder=mod_folder, disc=p["disc"],
                                     part="object2", idall=RENDER_ONLY_IDALL,
                                     at=tuple(b["at"]) if b["at"] else (64.0 * x + 32.0, -64.0 * y - 32.0),
                                     seat=True, keep_block=False, terrain_bm=t2, game=game,
                                     skip_mirror=DM.REPLAY)
            written.append(got["dest"])
            p["object2"] = {k: got[k] for k in ("tris", "degenerate_tris") if k in got}
        p["written"] = written
    return {"plans": plans, "dry_run": False}


def receipt(res) -> list:
    """The writer receipt, one block per disc."""
    lines = []
    for p in res["plans"]:
        x, y = p["cell"]
        where = f"Block[{x}][{y}] (Disc{p['disc']})"
        f = p.get("fill")
        if p["kind"] == "keep":
            lines.append(f"{where}: form 2 keeps the form-1 building -- "
                         + (f"removed {Path(p['delete'][0]).name}" if p["delete"] else "no Object2 was there"))
            continue
        head = {"remove": "the building is REMOVED in form 2",
                "replace": "a NEW building replaces the stock one in form 2",
                "add": "a building APPEARS in form 2 (engine s93)"}[p["kind"]]
        lines.append(f"{where}: {head}, when {p['condition']}")
        if f and f["fill_tris"]:
            lines.append(f"  the hole under the stock building ({f['hole_u2']} u^2, {len(f['rings'])} closed hole(s)) "
                         f"is filled with {f['fill_tris']} tris carried from the ground around it (topographs "
                         f"{f['topographs']})")
        elif f:
            lines.append("  the hole under the stock building is already filled in this Terrain2")
        if p.get("footprint_blocked"):
            lines.append(f"  the new building renders only; the ground under its footprint is impassable "
                         f"(topograph {BLOCKED_TOPO}, {p['footprint_blocked']} tris)")
        if p.get("entrances"):
            lines.append(f"  note: this cell's form-2 ground keeps {len(p['entrances'])} entrance tile tag(s) "
                         f"{p['entrances'][:4]}: walking onto them still fires the world event in form 2")
        if p.get("disc4"):
            lines.append(f"  disc 4: {p['disc4']}")
        for w in p.get("written", []):
            lines.append(f"  wrote {w}")
    return lines
