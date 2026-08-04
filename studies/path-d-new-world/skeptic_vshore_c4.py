"""C4 SKEPTIC -- adversarial re-measurement of the V-shore hover-site claims.

CURTAIN GRAMMAR study, C4 skeptic pass (studies/path-d-new-world/CURTAIN-GRAMMAR.md).
Re-derives every number in probe_vshore_anatomy.py's claim set by DIFFERENT methods:

  * Terrain edge-ownership maps at 2dp AND 4dp vert rounding (instrument: 3dp),
    both PER-BLOCK (probe_vshore_gap's frame) and GLOBAL across the six blocks;
  * point-in-triangle by the 2D edge-function sign test + plane interpolation
    (instrument: barycentric weights); vertical-line sheet stacks are unioned
    over ALL loaded blocks (instrument: the single block_key block) -- the
    single-block gap is computed alongside for spec comparability;
  * own geometric face normals, own 8u-cell spatial grid, own chain walker;
  * carried-vs-bench attribution by direct set-difference of sorted rounded
    tri vert triples, live vs the pristine pre-wall backup, at both roundings;
  * pristine shore profiles resampled at 0.25u radial steps PLUS two lateral
    offset lines (+/-1u perpendicular) per site ray;
  * a pristine-world hover sweep over the pristine once-edge set (the
    bench free-edge envelope the authorship claim rests on).

Shared infrastructure reused: walk_sim.load_world ONLY (mesh loading).
Spec constants kept from the registration so numbers are comparable
(hover > 0.5u, below-guard 0.05, up-facing ny > 0.1, site radius 12u,
scan skips mapids {4078,4088,2040} + veto 0x31EE, render includes them).

Artifacts -> out/skeptic_c4.json.  READ-ONLY: no deploy, no bench mutation.
Run: py -X utf8 skeptic_vshore_c4.py     (from this directory)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402  (load_world only)

SKIP = {4078, 4088, 2040}
VETO = 0x31EE
UP = 0.1
HOVER = 0.5
GUARD = 0.05
R_SITE = 12.0
LOWLAND = 3.2
# (name, cx, cz, shore ray heading deg -- east/west from the claims, south from the
#  instrument's registered JSON; the heading is an input, the profile is the test)
SITES = [("east", 448.8, -507.8, 60.0), ("west", 382.4, -511.6, 210.0),
         ("south", 448.0, -538.0, 75.0)]
RIM_X = (320.0, 512.0)
RIM_Z = (-448.0, -576.0)
OUTP = HERE / "out" / "skeptic_c4.json"


# ---------------------------------------------------------------- geometry (own)
def face_ny(a, b, c):
    """Full cross(b-a, c-a), normalized, y component."""
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    cx = uy * vz - uz * vy
    cy = uz * vx - ux * vz
    cz = ux * vy - uy * vx
    n = math.sqrt(cx * cx + cy * cy + cz * cz)
    return cy / n if n > 1e-15 else 0.0


def y_at(a, b, c, x, z, eps=1e-6):
    """Plane y where the vertical line pierces tri abc, or None -- 2D edge-function
    sign test (inclusive within eps), then plane interpolation via the face normal."""
    d0 = (b[0] - a[0]) * (z - a[2]) - (b[2] - a[2]) * (x - a[0])
    d1 = (c[0] - b[0]) * (z - b[2]) - (c[2] - b[2]) * (x - b[0])
    d2 = (a[0] - c[0]) * (z - c[2]) - (a[2] - c[2]) * (x - c[0])
    neg = d0 < -eps or d1 < -eps or d2 < -eps
    pos = d0 > eps or d1 > eps or d2 > eps
    if neg and pos:
        return None
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    if abs(ny) < 1e-12:
        return None
    return a[1] - (nx * (x - a[0]) + nz * (z - a[2])) / ny


def seg_dist(px, pz, a, b):
    ax, az, bx, bz = a[0], a[2], b[0], b[2]
    dx, dz = bx - ax, bz - az
    l2 = dx * dx + dz * dz
    if l2 < 1e-12:
        return math.hypot(px - ax, pz - az)
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / l2))
    return math.hypot(px - (ax + t * dx), pz - (az + t * dz))


def bk_of(x, z):
    return (int(x / 64.0), int(abs(z) / 64.0))


# ---------------------------------------------------------------- index (own)
def build_index(world):
    """Flat mesh list with own normals + own 8u-cell grid, world coords."""
    idx = []
    for bk in sorted(world):
        for m in world[bk]:
            tris, cells = [], defaultdict(list)
            for ti, t in enumerate(m["tris"]):
                a, b, c = t[0], t[1], t[2]
                tris.append((a, b, c, t[3], t[4], face_ny(a, b, c)))
                x0 = min(a[0], b[0], c[0]); x1 = max(a[0], b[0], c[0])
                z0 = min(a[2], b[2], c[2]); z1 = max(a[2], b[2], c[2])
                for gi in range(int(math.floor(x0 / 8)), int(math.floor(x1 / 8)) + 1):
                    for gj in range(int(math.floor(z0 / 8)), int(math.floor(z1 / 8)) + 1):
                        cells[(gi, gj)].append(ti)
            idx.append(dict(bk=bk, part=m["name"], tris=tris, cells=cells))
    return idx


def sheets(idx, x, z, render=False, only_bk=None):
    """Up-facing vertical-line stack at (x,z), unioned over ALL loaded blocks
    (only_bk restricts to one block = the instrument's block_key convention).
    [(y, topo, mapid, part), ...] top-down, deduped per (part, y@2dp)."""
    gi, gj = int(math.floor(x / 8)), int(math.floor(z / 8))
    out = []
    for mesh in idx:
        if only_bk is not None and mesh["bk"] != only_bk:
            continue
        for ti in mesh["cells"].get((gi, gj), ()):
            a, b, c, mapid, topo, ny = mesh["tris"][ti]
            if ny <= UP:
                continue
            if not render and (mapid in SKIP or mapid == VETO):
                continue
            y = y_at(a, b, c, x, z)
            if y is None:
                continue
            out.append((y, topo, mapid, mesh["part"]))
    out.sort(key=lambda s: -s[0])
    seen, ded = set(), []
    for s in out:
        k = (s[3], round(s[0], 2))
        if k in seen:
            continue
        seen.add(k)
        ded.append(s)
    return ded


def below(idx, x, z, y, render=False, only_bk=None):
    for s in sheets(idx, x, z, render=render, only_bk=only_bk):
        if s[0] < y - GUARD:
            return s
    return None


# ---------------------------------------------------------------- edges (own)
def rkey(v, rnd):
    return (round(v[0], rnd), round(v[1], rnd), round(v[2], rnd))


def edge_maps(idx, rnd):
    """glob: edge -> [(bk, ti)] over every Terrain tri; per_block: bk -> edge -> [ti];
    tri lookup (bk, ti) -> tri tuple."""
    glob = defaultdict(list)
    per_block = defaultdict(lambda: defaultdict(list))
    tlk = {}
    for mesh in idx:
        if mesh["part"] != "Terrain":
            continue
        bk = mesh["bk"]
        for ti, t in enumerate(mesh["tris"]):
            tlk[(bk, ti)] = t
            vs = (rkey(t[0], rnd), rkey(t[1], rnd), rkey(t[2], rnd))
            for i, j in ((0, 1), (1, 2), (2, 0)):
                k = tuple(sorted((vs[i], vs[j])))
                glob[k].append((bk, ti))
                per_block[bk][k].append(ti)
    return glob, per_block, tlk


def tri_triples(idx, rnd):
    out = set()
    for mesh in idx:
        if mesh["part"] != "Terrain":
            continue
        for t in mesh["tris"]:
            out.add(tuple(sorted((rkey(t[0], rnd), rkey(t[1], rnd), rkey(t[2], rnd)))))
    return out


def on_rim(k):
    va, vb = k
    return any(abs(va[ax] - p) < 0.05 and abs(vb[ax] - p) < 0.05
               for ax, planes in ((0, RIM_X), (2, RIM_Z)) for p in planes)


def hover_sweep(idx, glob, tlk, pristine_triples, rnd):
    """Every global once-edge (rim excluded) hovering > HOVER over a scan sheet.
    Gap in union-of-blocks AND single-block(block_key) vocabularies."""
    out = []
    for k, own in glob.items():
        if len(own) != 1 or on_rim(k):
            continue
        va, vb = k
        mx, my, mz = (va[0] + vb[0]) / 2, (va[1] + vb[1]) / 2, (va[2] + vb[2]) / 2
        bs = below(idx, mx, mz, my, render=False)
        if bs is None or my - bs[0] <= HOVER:
            continue
        br = below(idx, mx, mz, my, render=True)
        bsb = below(idx, mx, mz, my, render=False, only_bk=bk_of(mx, mz))
        t = tlk[own[0]]
        trip = tuple(sorted((rkey(t[0], rnd), rkey(t[1], rnd), rkey(t[2], rnd))))
        d = {n: round(math.hypot(mx - cx, mz - cz), 1) for (n, cx, cz, _t) in SITES}
        out.append(dict(
            a=list(va), b=list(vb),
            mid=[round(mx, 2), round(my, 3), round(mz, 2)],
            plan_len=round(math.hypot(va[0] - vb[0], va[2] - vb[2]), 3),
            gap_scan=round(my - bs[0], 3),
            below_scan=dict(y=round(bs[0], 3), topo=bs[1], mapid=bs[2], part=bs[3]),
            gap_scan_singleblock=round(my - bsb[0], 3) if bsb else None,
            gap_render=round(my - br[0], 3) if br else None,
            below_render=dict(y=round(br[0], 3), topo=br[1], mapid=br[2],
                              part=br[3]) if br else None,
            underlay_sealed=bool(br and br[2] == 4078 and my - br[0] <= HOVER),
            owner=dict(bk=list(own[0][0]), ti=own[0][1], mapid=t[3], topo=t[4],
                       ny=round(face_ny(t[0], t[1], t[2]), 3),
                       verts=[[round(c, 3) for c in v] for v in (t[0], t[1], t[2])]),
            carried=trip not in pristine_triples,
            dist=d, in_site=any(v <= R_SITE for v in d.values())))
    return out


def per_block_calib(idx, per_block, glob, cx, cz):
    """probe_vshore_gap's per-block frame re-derived: per-block once-edges whose
    midpoint is in the 12u site and hovers (single-block scan, existence > 0.5),
    classified against the GLOBAL map."""
    kinds = Counter()
    n = 0
    tot = 0.0
    gmax = 0.0
    for bk in sorted(per_block):
        for k, tis in per_block[bk].items():
            if len(tis) != 1:
                continue
            va, vb = k
            mx, my, mz = (va[0] + vb[0]) / 2, (va[1] + vb[1]) / 2, (va[2] + vb[2]) / 2
            if math.hypot(mx - cx, mz - cz) > R_SITE:
                continue
            bl = [s[0] for s in sheets(idx, mx, mz, render=False, only_bk=bk_of(mx, mz))
                  if s[0] < my - HOVER]
            if not bl:
                continue
            n += 1
            tot += math.hypot(va[0] - vb[0], va[2] - vb[2])
            gmax = max(gmax, my - max(bl))
            gown = glob.get(k, [])
            if len(gown) <= 1:
                kinds["TRUE-open"] += 1
            elif any(o[0] != bk for o in gown):
                kinds["seam-phantom"] += 1
            else:
                kinds["same-block-shared"] += 1
    return dict(hover_edges=n, total_len=round(tot, 2), max_gap=round(gmax, 2),
                kinds=dict(kinds))


# ---------------------------------------------------------------- chains (own)
def chains_of(edges):
    """Order edge list (rounded-key pairs) into polylines from degree-1 ends."""
    adj = defaultdict(set)
    for (a, b) in edges:
        adj[a].add(b)
        adj[b].add(a)
    used, out = set(), []
    for start in sorted(adj):
        if len(adj[start]) == 1:
            for nxt in sorted(adj[start]):
                e = frozenset((start, nxt))
                if e in used:
                    continue
                ch = [start, nxt]
                used.add(e)
                while True:
                    cur = ch[-1]
                    ext = [q for q in adj[cur] if frozenset((cur, q)) not in used]
                    if len(adj[cur]) != 2 or not ext:
                        break
                    used.add(frozenset((cur, ext[0])))
                    ch.append(ext[0])
                out.append(ch)
    for a in sorted(adj):                                   # leftover cycles
        for b in sorted(adj[a]):
            e = frozenset((a, b))
            if e not in used:
                ch = [a, b]
                used.add(e)
                while True:
                    cur = ch[-1]
                    ext = [q for q in adj[cur] if frozenset((cur, q)) not in used]
                    if not ext:
                        break
                    used.add(frozenset((cur, ext[0])))
                    ch.append(ext[0])
                out.append(ch)
    return out


def drop_stations(idx, ch):
    """Verts + edge midpoints along a chain: gap to first scan/render sheet below."""
    pts = []
    prev = None
    for v in ch:
        if prev is not None:
            pts.append(((prev[0] + v[0]) / 2, (prev[1] + v[1]) / 2,
                        (prev[2] + v[2]) / 2, "mid"))
        pts.append((v[0], v[1], v[2], "vert"))
        prev = v
    out = []
    for (x, y, z, kind) in pts:
        bs = below(idx, x, z, y, render=False)
        br = below(idx, x, z, y, render=True)
        out.append(dict(kind=kind, x=round(x, 2), y=round(y, 3), z=round(z, 2),
                        gap_scan=round(y - bs[0], 3) if bs else None,
                        below_scan=f"{bs[3]}:topo{bs[1]}:mapid{bs[2]}" if bs else None,
                        gap_render=round(y - br[0], 3) if br else None,
                        below_render=f"{br[3]}:topo{br[1]}:mapid{br[2]}" if br else None))
    return out


# ---------------------------------------------------------------- shore (own)
def shore_line(pidx, cx, cz, th_deg, r0=-24.0, r1=32.0, step=0.5, off=0.0):
    """Pristine ground line along heading th (x=cx+r*sin, z=cz+r*cos), lateral
    offset off along the left normal (cos, -sin). Marks per the registration's
    definitions so numbers are comparable."""
    th = math.radians(th_deg)
    sx, cz_ = math.sin(th), math.cos(th)
    nx, nz = math.cos(th), -math.sin(th)
    samples = []
    r = r0
    while r <= r1 + 1e-9:
        x = cx + r * sx + off * nx
        z = cz + r * cz_ + off * nz
        sh = sheets(pidx, x, z, render=True)
        terr = [s for s in sh if s[3] == "Terrain"]
        sea = [s for s in sh if s[3].startswith("Sea")]
        samples.append(dict(r=round(r, 2), x=round(x, 2), z=round(z, 2),
                            terr_y=round(terr[0][0], 3) if terr else None,
                            topo=terr[0][1] if terr else None,
                            mapid=terr[0][2] if terr else None,
                            sea_y=round(sea[0][0], 3) if sea else None,
                            sea_under_land=bool(terr and sea
                                                and sea[0][0] < terr[0][0] - 0.05)))
        r += step
    desc = next((s["r"] for s in samples if s["r"] >= -R_SITE
                 and s["terr_y"] is not None and s["terr_y"] < LOWLAND - 0.05), None)
    end = next((s["r"] for s in samples if s["r"] >= -R_SITE
                and s["terr_y"] is None), None)
    wline = next((s["r"] for s in samples if s["terr_y"] is not None
                  and s["sea_y"] is not None and s["terr_y"] <= s["sea_y"] + 0.05),
                 None)
    ret = None
    if end is not None:
        ret = next((s["r"] for s in samples if s["r"] > end
                    and s["terr_y"] is not None), None)
    wys = sorted(s["sea_y"] for s in samples if s["sea_y"] is not None)
    rle = []
    for s in samples:
        t = s["topo"]
        if rle and rle[-1]["topo"] == t:
            rle[-1]["r1"] = s["r"]
        else:
            rle.append(dict(topo=t, r0=s["r"], r1=s["r"]))
    return dict(off=off, step=step,
                marks=dict(descent_r=desc, terrain_end_r=end, waterline_r=wline,
                           terrain_returns_r=ret,
                           water_y=wys[len(wys) // 2] if wys else None),
                topo_runs=rle, samples=samples)


def transect(idx, x0, x1, z, step=0.25):
    """Live render sheet stacks along x at fixed z (the east border transect)."""
    rows = []
    x = x0
    while x <= x1 + 1e-9:
        sh = sheets(idx, x, z, render=True)[:4]
        rows.append(dict(x=round(x, 2), z=z,
                         stack=[[round(s[0], 3), s[1], s[2], s[3]] for s in sh]))
        x += step
    return rows


# ---------------------------------------------------------------- main
def main():
    OUTP.parent.mkdir(parents=True, exist_ok=True)
    print("loading LIVE world ...")
    live = W.load_world()
    tsrc = {}
    for (bx, by) in W.CELLS:
        p = W.PRISTINE_BK / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            tsrc[(bx, by)] = p
    print(f"pristine Terrain files: {len(tsrc)}/6 from {W.PRISTINE_BK}")
    pristine = W.load_world(terrain_src=tsrc)

    lidx = build_index(live)
    pidx = build_index(pristine)
    report = dict(pristine_backup=str(W.PRISTINE_BK), roundings={})

    for rnd in (2, 4):
        glob, per_block, tlk = edge_maps(lidx, rnd)
        pglob, _pb, _pt = edge_maps(pidx, rnd)
        ptrip = tri_triples(pidx, rnd)
        ltrip = tri_triples(lidx, rnd)
        n_carried = len(ltrip - ptrip)
        print(f"\n===== ROUNDING {rnd}dp: live terrain triples {len(ltrip)}, "
              f"pristine {len(ptrip)}, carried {n_carried} =====")

        sweep = hover_sweep(lidx, glob, tlk, ptrip, rnd)
        inside = [e for e in sweep if e["in_site"]]
        outside = [e for e in sweep if not e["in_site"]]
        p_once = {k for k, o in pglob.items() if len(o) == 1}
        bench_idiom = sum(1 for e in sweep
                          if tuple(sorted((tuple(e["a"]), tuple(e["b"])))) in p_once)
        print(f"GLOBAL sweep: {len(sweep)} true hover once-edges "
              f"({len(inside)} in-site, {len(outside)} outside), "
              f"bench-idiom {bench_idiom}, carried {sum(1 for e in sweep if e['carried'])}")
        for e in sorted(outside, key=lambda e: -(e["gap_render"] or 0)):
            print(f"   OUT mid={e['mid']} gapS={e['gap_scan']} gapR={e['gap_render']} "
                  f"len={e['plan_len']} sealed={e['underlay_sealed']} "
                  f"below_render={e['below_render']} dist={e['dist']}")

        # pristine hover sweep (bench free-edge envelope)
        psweep = []
        pgaps = []
        for k, own in pglob.items():
            if len(own) != 1 or on_rim(k):
                continue
            va, vb = k
            mx, my, mz = (va[0] + vb[0]) / 2, (va[1] + vb[1]) / 2, (va[2] + vb[2]) / 2
            bs = below(pidx, mx, mz, my, render=False)
            if bs is None:
                continue
            g = my - bs[0]
            pgaps.append(g)
            if g > HOVER:
                psweep.append(dict(mid=[round(mx, 2), round(my, 3), round(mz, 2)],
                                   gap=round(g, 3), part=bs[3]))
        print(f"PRISTINE sweep: {len(psweep)} hover once-edges "
              f"(max free-edge gap {max(pgaps):.3f} over {len(pgaps)} edges with a "
              f"sheet below)" if pgaps else "PRISTINE sweep: no edges with sheets below")
        for e in psweep[:10]:
            print(f"   PRISTINE-HOVER {e}")

        sites_out = []
        for (name, cx, cz, th) in SITES:
            calib = per_block_calib(lidx, per_block, glob, cx, cz)
            se = [e for e in sweep
                  if math.hypot(e["mid"][0] - cx, e["mid"][2] - cz) <= R_SITE]
            tot = round(sum(e["plan_len"] for e in se), 2)
            gaps = [e["gap_scan"] for e in se]
            chs = chains_of([(tuple(e["a"]), tuple(e["b"])) for e in se])
            ch_recs = []
            for ch in chs:
                ln = round(sum(math.hypot(ch[i + 1][0] - ch[i][0],
                                          ch[i + 1][2] - ch[i][2])
                               for i in range(len(ch) - 1)), 2)
                ch_recs.append(dict(verts=[list(v) for v in ch], plan_len=ln,
                                    stations=drop_stations(lidx, ch)))
            ch_recs.sort(key=lambda c: -c["plan_len"])
            # window carried census (tri centroid within R+4)
            win = car = 0
            for mesh in lidx:
                if mesh["part"] != "Terrain":
                    continue
                for t in mesh["tris"]:
                    tx = (t[0][0] + t[1][0] + t[2][0]) / 3
                    tz = (t[0][2] + t[1][2] + t[2][2]) / 3
                    if math.hypot(tx - cx, tz - cz) <= R_SITE + 4:
                        win += 1
                        trip = tuple(sorted((rkey(t[0], rnd), rkey(t[1], rnd),
                                             rkey(t[2], rnd))))
                        if trip not in ptrip:
                            car += 1
            seg_d = [round(seg_dist(cx, cz, tuple(e["a"]), tuple(e["b"])), 2)
                     for e in se]
            print(f"SITE {name}: calib per-block {calib['hover_edges']} "
                  f"{calib['kinds']} | global hover in 12u: {len(se)} edges {tot}u "
                  f"gapS {min(gaps) if gaps else None}-{max(gaps) if gaps else None} "
                  f"carried {sum(1 for e in se if e['carried'])}/{len(se)} | "
                  f"window {car}/{win} carried | chains "
                  f"{[c['plan_len'] for c in ch_recs]} | seg_d {seg_d}")
            sites_out.append(dict(site=name, centroid=[cx, cz], calib=calib,
                                  hover_edges=se, hover_total_len=tot,
                                  chains=ch_recs, window_tris=win,
                                  window_carried=car, seg_dists=seg_d))
        report["roundings"][str(rnd)] = dict(
            live_triples=len(ltrip), pristine_triples=len(ptrip),
            carried_triples=n_carried,
            sweep_total=len(sweep), sweep_inside=len(inside),
            sweep_outside=len(outside), bench_idiom=bench_idiom,
            sweep=sweep, pristine_hover=psweep,
            pristine_free_gap_max=round(max(pgaps), 3) if pgaps else None,
            sites=sites_out)

    # east border transect (live, both sides of x=448 at z=-506)
    report["east_transect_z-506"] = transect(lidx, 444.0, 452.0, -506.0)

    # shore profiles: pristine, main line 0.25u + offsets +/-1u at 0.5u
    profs = {}
    for (name, cx, cz, th) in SITES:
        profs[name] = dict(
            heading_deg=th,
            main=shore_line(pidx, cx, cz, th, step=0.25),
            off_plus1=shore_line(pidx, cx, cz, th, step=0.5, off=1.0),
            off_minus1=shore_line(pidx, cx, cz, th, step=0.5, off=-1.0))
        for key in ("main", "off_plus1", "off_minus1"):
            m = profs[name][key]["marks"]
            print(f"SHORE {name} {key}: descent_r={m['descent_r']} "
                  f"end_r={m['terrain_end_r']} waterline_r={m['waterline_r']} "
                  f"returns_r={m['terrain_returns_r']} water_y={m['water_y']}")
    report["shore_profiles"] = profs

    json.dump(report, open(OUTP, "w"), indent=1)
    print(f"\nreport -> {OUTP}")


if __name__ == "__main__":
    main()
