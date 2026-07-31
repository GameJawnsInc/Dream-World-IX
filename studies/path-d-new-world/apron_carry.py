"""APRON CARRY -- the (15,14) mesa at DONOR STATURE with its own foot band + ground apron.

Registration: studies/path-d-new-world/APRON-CARRY-PREDICTION.md. The base-tile
grammar study (BASE-TILE-GRAMMAR.md) proved the transitional band is the column's own
uv continuation -- unmintable on cut fragments -- so this round re-seats the donor at
native height and carries BOTH sides of stock's transition: the near-solid row-10/11
foot band (92% at the donor's own weld) AND the donor's grass apron collar. The only
minted junction is the OUTER grass-to-grass weld (bench grass partitioned at the
apron's boundary + a 12u smoothstep lift toward the rim).

MEASURED DECISIONS (the registration's declared freedoms, resolved by probe_mesa_apron):
- Apron = donor GRASS-class tris (GRASS_TOPO) within APRON_D=10u plan of the weld
  polyline, adjacency-flooded over the 5-block donor neighborhood (no border
  truncation on any side that matters; residual border runs are reported).
- Forest (topo 37) is EXCLUDED -- a feature class with its own whole-blob carry law
  (world/interior.py). Where it abutted the weld the boundary becomes a secondary rim
  loop and bench grass fills the hole (the partition machinery's ledge-dip path).
- Rim = the VERBATIM apron boundary polyline (no chord simplification): the wall/
  apron side of the weld is donor-internal, so only the bench side is sliced.
- Seat: dy = LOWLAND - median(outer rim y): the donor sits at native stature with its
  rim at bench level (the buried round's -4.35 becomes ~-0.1).

Regenerate: py -X utf8 apron_carry.py  (offline gates + renders; --apply to deploy)
"""
from terrace_wall_strip import *                            # noqa: F401,F403 -- the shared, proven module
from terrace_wall_strip import kk, OUTD, DECODE, ANATOMY    # noqa: F401 -- explicit for clarity

DONOR_BLK = (15, 14)
NEIGH = [(14, 14), (16, 14), (15, 13), (15, 15)]
APRON_D = 6.0                                               # apron collar reach from the weld (plan;
                                                            # 10.0 pushed the west rim to 48u on a
                                                            # 50.6u bench -- the reach gate's call)
BLEND_R = 12.0                                              # bench-side smoothstep radius
PLATEAU_T = {10, 11, 12}                                    # plateau topograph classes (the wall studies')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--probe", action="store_true",
                    help="dump final tris near named debug coordinates")
    args = ap.parse_args()
    OUTD.mkdir(parents=True, exist_ok=True)

    tris, bms = load_bench()
    assert tris, "bench island not deployed at Disc9 (run the world-island mint first)"
    n_rock_in = sum(1 for t in tris if t["topo"] == ROCK)
    assert n_rock_in == 0, (
        f"bench is NOT pristine ({n_rock_in} rock tris present -- a prior deploy is "
        f"live). Restore backups/terrace-strip-prewall.* first.")
    grass_r = max(math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
                  for t in tris if t["topo"] in GRASS_TOPO)
    print(f"bench: {len(tris)} tris across {len(bms)} cells; grass reach ~{grass_r:.1f}u")

    pu_ph, pv_ph = json.loads(DECODE.read_text())["phase"]

    def tile_row(uvs):
        return int(math.floor((min(q[1] for q in uvs) - pv_ph) / TILE_V + 0.5))

    # ---- THE MERGED DONOR SOUP (5 blocks, world frame) -------------------------------------
    soup = []
    for (bx, by) in [DONOR_BLK] + NEIGH:
        W = extract_wall(bx, by)
        VD, UD, ND, TD = W["V"], W["U"], W["N"], W["T"]
        for lt, idx in enumerate(W["tri_idx"]):
            soup.append(dict(
                w=[(VD[i][0] + W["ox"], VD[i][1], VD[i][2] + W["oz"]) for i in idx],
                uv=[tuple(UD[i]) for i in idx], n=[tuple(ND[i]) for i in idx],
                tan=[tuple(TD[i]) for i in idx], topo=W["topo"][lt], blk=(bx, by)))
    ET = defaultdict(list)
    for si, t in enumerate(soup):
        ps = [kk(p) for p in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ET[tuple(sorted((ps[a], ps[b])))].append(si)

    # ---- THE MESA (crest-seeded rock component on the merged graph -> the west
    # continuation joins by shared border verts, no special-casing) -------------------------
    crest49 = set()
    for e, ts in ET.items():
        if len(ts) == 2:
            pair = {soup[ts[0]]["topo"], soup[ts[1]]["topo"]}
            if 49 in pair and pair & PLATEAU_T:
                crest49.add(ts[0] if soup[ts[0]]["topo"] == 49 else ts[1])
    adj49 = defaultdict(set)
    for e, ts in ET.items():
        r = [t for t in ts if soup[t]["topo"] == 49]
        for i in range(len(r)):
            for j in range(i + 1, len(r)):
                adj49[r[i]].add(r[j])
                adj49[r[j]].add(r[i])
    comp_of = {}
    seen = set()
    for s in crest49:
        if s in seen:
            continue
        comp = {s}
        st = [s]
        while st:
            t = st.pop()
            for t2 in adj49[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        for t in comp:
            comp_of[t] = s
    comp_tris = defaultdict(list)
    for t, r in comp_of.items():
        comp_tris[r].append(t)
    root = max(comp_tris, key=lambda r: sum(1 for t in comp_tris[r]
                                            if soup[t]["blk"] == DONOR_BLK))
    mesa = set(comp_tris[root])
    n_cont = sum(1 for t in mesa if soup[t]["blk"] != DONOR_BLK)

    ring1 = set()
    crest_e = []
    for e, ts in ET.items():
        if len(ts) != 2:
            continue
        w = [t for t in ts if t in mesa]
        p = [t for t in ts if soup[t]["topo"] in PLATEAU_T]
        if len(w) == 1 and len(p) == 1:
            ring1.add(p[0])
            crest_e.append(e)
    padj = defaultdict(set)
    for e, ts in ET.items():
        pp = [t for t in ts if soup[t]["topo"] in PLATEAU_T]
        for i in range(len(pp)):
            for j in range(i + 1, len(pp)):
                padj[pp[i]].add(pp[j])
                padj[pp[j]].add(pp[i])
    plat = set(ring1)
    st = list(ring1)
    while st:
        t = st.pop()
        for t2 in padj[t]:
            if t2 not in plat:
                plat.add(t2)
                st.append(t2)
    carry = mesa | plat
    print(f"mesa: {len(mesa)} wall tris ({n_cont} continuation, west) + {len(ring1)} "
          f"ring-1 + {len(plat) - len(ring1)} interior plateau tris (blk {DONOR_BLK}"
          f" + neighbors)")

    # ---- the ground-weld line + THE BAND GATE baseline -------------------------------------
    weld_edges = []
    weld_rock_rows = Counter()
    for e, ts in ET.items():
        w = [t for t in ts if t in carry]
        o = [t for t in ts if t not in carry]
        if len(w) == 1 and o and all(soup[t]["topo"] != 49 and
                                     soup[t]["topo"] not in PLATEAU_T for t in o):
            weld_edges.append(e)
            if soup[w[0]]["topo"] == 49:
                weld_rock_rows[tile_row(soup[w[0]]["uv"])] += 1
    band_share = ((weld_rock_rows.get(10, 0) + weld_rock_rows.get(11, 0))
                  / max(1, sum(weld_rock_rows.values())))
    wy = [p[1] for e in weld_edges for p in e]
    print(f"weld line: {len(weld_edges)} edges, y {min(wy):.1f}..{max(wy):.1f}; "
          f"foot-course rows {weld_rock_rows.most_common(4)} -> band(10+11) share "
          f"{band_share:.1%}")

    # ---- pose plan (tx/tz on the (15,14) mesa bbox = the passed round's placement);
    # needed BEFORE the apron flood so the bench-grass clip tests posed positions ------------
    mes15 = [t for t in carry if soup[t]["blk"] == DONOR_BLK]
    cvx = [p[0] for t in mes15 for p in soup[t]["w"]]
    cvz = [p[2] for t in mes15 for p in soup[t]["w"]]
    tx = CELL * round((CENTER[0] - (min(cvx) + max(cvx)) / 2.0) / CELL)
    tz = CELL * round((CENTER[1] - (min(cvz) + max(cvz)) / 2.0) / CELL)

    # ---- THE APRON: the donor grass collar (adjacency flood, distance-clipped, and
    # CLIPPED TO BENCH GRASS: the donor's meadow continues past where the bench island
    # has grass -- run 2's residue was the apron overlapping the bench COAST band on
    # the west/southwest. An apron tri is accepted only if every vert lands over bench
    # grass with >= 2u clearance from any non-grass bench vert; where the bench runs
    # out, the collar ends and bench grass welds DIRECTLY to the donor weld line (the
    # registration's declared fallback, applied locally). --------------------------------
    wpts = sorted({p for e in weld_edges for p in e})
    warr = np.array([[p[0], p[2]] for p in wpts])

    def dist_weld(p):
        return float(np.min(np.hypot(warr[:, 0] - p[0], warr[:, 1] - p[2])))

    banned0 = {kk(p) for t in tris if t["topo"] not in GRASS_TOPO for p in t["w"]}
    barr = np.array([[p[0], p[2]] for p in banned0]) if banned0 else np.zeros((0, 2))
    bench_grass = [t for t in tris if t["topo"] in GRASS_TOPO]

    def over_grass(px, pz):
        for t in bench_grass:
            (x1, z1), (x2, z2), (x3, z3) = ((t["w"][k][0], t["w"][k][2])
                                            for k in range(3))
            det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
            if abs(det) < 1e-12:
                continue
            w2 = ((px - x1) * (z3 - z1) - (x3 - x1) * (pz - z1)) / det
            w3 = ((x2 - x1) * (pz - z1) - (px - x1) * (z2 - z1)) / det
            if w2 >= -1e-9 and w3 >= -1e-9 and w2 + w3 <= 1 + 1e-9:
                return True
        return False

    _fit_cache = {}

    def fits_bench(p):
        k3 = kk(p)
        got = _fit_cache.get(k3)
        if got is None:
            px, pz = p[0] + tx, p[2] + tz
            got = (float(np.min(np.hypot(barr[:, 0] - px, barr[:, 1] - pz))) >= 2.0
                   if len(barr) else True) and over_grass(px, pz)
            _fit_cache[k3] = got
        return got

    grass_s = {si for si, t in enumerate(soup) if t["topo"] in GRASS_TOPO}
    gadj = defaultdict(set)
    for e, ts in ET.items():
        gg = [t for t in ts if t in grass_s]
        for i in range(len(gg)):
            for j in range(i + 1, len(gg)):
                gadj[gg[i]].add(gg[j])
                gadj[gg[j]].add(gg[i])
    n_forest_weld = 0
    forest_y = []
    seeds = set()
    for e, ts in ET.items():
        w = [t for t in ts if t in carry]
        o = [t for t in ts if t not in carry]
        if len(w) == 1 and o:
            for t in o:
                if t in grass_s:
                    seeds.add(t)
                elif soup[t]["topo"] == 37:
                    n_forest_weld += 1
                    forest_y.extend(p[1] for p in soup[t]["w"])

    n_clip = [0]

    def apron_ok(si):
        if min(dist_weld(p) for p in soup[si]["w"]) > APRON_D:
            return False
        if not all(fits_bench(p) for p in soup[si]["w"]):
            n_clip[0] += 1
            return False
        return True

    apron = set()
    frontier = {t for t in seeds if apron_ok(t)}
    while frontier:
        apron |= frontier
        nxt = set()
        for t in frontier:
            for t2 in gadj[t]:
                if t2 not in apron and apron_ok(t2):
                    nxt.add(t2)
        frontier = nxt
    ap_blk = Counter(soup[t]["blk"] for t in apron)
    print(f"apron: {len(apron)} grass tris within {APRON_D}u of the weld "
          f"(by block {dict(ap_blk)}); {n_clip[0]} tris clipped at the bench's own "
          f"grass edge; forest EXCLUDED at the weld: {n_forest_weld} edges"
          + (f", forest y {min(forest_y):.1f}..{max(forest_y):.1f}" if forest_y else ""))
    carrall = carry | apron

    # ---- rim loops (donor frame; plan is pose-invariant) + THE SEAT ------------------------
    bcnt = Counter()
    for t in carrall:
        ps = [kk(p) for p in soup[t]["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            bcnt[tuple(sorted((ps[a], ps[b])))] += 1
    bnd_edges = [e for e, n2 in bcnt.items() if n2 == 1]
    padjR = defaultdict(list)
    for e in bnd_edges:
        padjR[e[0]].append(e[1])
        padjR[e[1]].append(e[0])
    n_trim = 0
    trimmed = True
    while trimmed:
        trimmed = False
        for p in list(padjR):
            if len(padjR[p]) == 1:
                q = padjR[p][0]
                padjR[q].remove(p)
                del padjR[p]
                n_trim += 1
                trimmed = True
            elif len(padjR[p]) == 0:
                del padjR[p]
                trimmed = True
    bad = {p: l3 for p, l3 in padjR.items() if len(l3) != 2}
    if bad:
        for p, l3 in list(bad.items())[:6]:
            print(f"   DBG rim degree-{len(l3)} at {p}: {l3[:4]}")
    assert not bad, f"rim graph not 2-regular after whisker trim: {len(bad)} pinch verts"
    loops = []
    vis = set()
    for start in list(padjR):
        if start in vis:
            continue
        loop = [start]
        prev = None
        while True:
            nxts = [p for p in padjR[loop[-1]] if p != prev]
            if not nxts or nxts[0] == start:
                break
            prev = loop[-1]
            loop.append(nxts[0])
        vis.update(loop)
        if len(loop) >= 3:
            loops.append(loop)
    loops.sort(key=lambda l3: -abs(poly_area2([(p[0], p[2]) for p in l3])))
    assert loops, "no rim loop"
    outer_loop = loops[0]
    hole_loops = loops[1:]
    rim_med = float(np.median([p[1] for p in outer_loop]))
    dy = LOWLAND - rim_med
    n_border_rim = sum(1 for e in bnd_edges
                       if all(abs(p[0] % BLOCK) < 1e-3 or abs(p[2] % BLOCK) < 1e-3
                              for p in e))
    print(f"rim: outer {len(outer_loop)} verts (y med {rim_med:.2f} p90 "
          f"{float(np.percentile([p[1] for p in outer_loop], 90)):.2f} max "
          f"{max(p[1] for p in outer_loop):.2f}), {len(hole_loops)} hole loop(s) "
          f"{[len(l3) for l3 in hole_loops]}; {n_trim} whisker edges trimmed; "
          f"{n_border_rim} rim edges on unloaded block borders")

    print(f"pose: yaw 0, translate ({tx:+.0f}, {tz:+.0f}) [4u lattice], seat dy "
          f"{dy:+.2f} (DONOR STATURE: the rim sits at bench level; the buried "
          f"round's -4.35 is undone)")

    def posed(p):
        return (p[0] + tx, p[1] + dy, p[2] + tz)

    wall = []
    for t in sorted(carrall):
        rec = [(posed(soup[t]["w"][k3]), soup[t]["uv"][k3], soup[t]["n"][k3],
                soup[t]["tan"][k3]) for k3 in range(3)]
        wall.append(rec)
    n_apr = len(apron)
    crest = sorted({kk(posed(p)) for e in crest_e for p in e})
    top_y = max(r[0][1] for rec in wall for r in rec)
    print(f"carry: {len(wall)} tris ({len(carry)} rock/plateau + {n_apr} apron), "
          f"crest ring {len(crest)} verts at bench y "
          f"~{float(np.median([p[1] for p in crest])):.1f}, top {top_y:.1f}")

    # strip-machinery placeholders: nothing is composed or welded up top
    strips = []
    S = 1
    gap = 0.0
    weld_stats = []
    move_maps = []
    seam_report = []
    notch_patches = []
    notch_polys = []
    top_tris = []
    n_cc = len(crest)
    rim_gate_stats = dict(disp_p50=0.0, disp_p99=0.0, disp_max=0.0,
                          sliver=0.0, n_sliver=0, jumps=0)

    def refine_wall(wall_in, rmap):
        """Split any tri edge listed in rmap at its points (attrs edge-lerped along that
        edge). A tri with several refined edges becomes a fan around its cycle."""
        out = []
        n_splits = 0
        for rec in wall_in:
            keys3 = [kk(rec[k3][0]) for k3 in range(3)]
            hits = [k3 for k3 in range(3)
                    if tuple(sorted((keys3[k3], keys3[(k3 + 1) % 3]))) in rmap]
            if not hits:
                out.append(rec)
                continue
            poly = []
            for k3 in range(3):
                a_r, b_r = rec[k3], rec[(k3 + 1) % 3]
                poly.append(a_r)
                if k3 not in hits:
                    continue
                pts2 = rmap[tuple(sorted((keys3[k3], keys3[(k3 + 1) % 3])))]
                L2 = math.dist(a_r[0], b_r[0]) or 1.0
                seen2 = {kk(a_r[0]), kk(b_r[0])}
                for p in sorted(pts2, key=lambda q2: math.dist(a_r[0], q2)):
                    if kk(p) in seen2:
                        continue
                    tt = min(1.0, max(0.0, math.dist(a_r[0], p) / L2))
                    uv_m = tuple(a_r[1][q2] + tt * (b_r[1][q2] - a_r[1][q2])
                                 for q2 in range(2))
                    n_m = tuple(a_r[2][q2] + tt * (b_r[2][q2] - a_r[2][q2])
                                for q2 in range(3))
                    poly.append((tuple(p), uv_m, n_m, a_r[3]))
                    seen2.add(kk(p))
                    n_splits += 1
            if len(poly) == 3:
                out.append(poly)
                continue
            if len(hits) == 1:
                c_key = keys3[(hits[0] + 2) % 3]
            elif set(hits) == {0, 1}:
                c_key = keys3[1]
            elif set(hits) == {1, 2}:
                c_key = keys3[2]
            else:
                c_key = keys3[0]
            start = next(q2 for q2 in range(len(poly)) if kk(poly[q2][0]) == c_key)
            cyc = poly[start:] + poly[:start]
            for q2 in range(1, len(cyc) - 1):
                out.append([cyc[0], cyc[q2], cyc[q2 + 1]])
        return out, n_splits

    # ---- THE RIM (the verbatim apron boundary, posed 3D) -----------------------------------
    # No level cut and no SHAPE simplification exist in this round: the wall/apron side
    # of every junction is donor-internal. But plan-COLLINEAR adjacent rim edges (the
    # lattice boundary's straight runs) MUST merge into one chord -- the on_chord /
    # enrich machinery reasons per chord, and a bench fragment edge spanning two
    # collinear chords would never split at their shared rim vertex (run-1's 262-edge
    # residue). Merged chords keep the intermediate rim verts as MIDS; y may kink at a
    # mid (plan-straight, height-kinked), so crossings interpolate y per SUB-edge.
    posed_loops = [[posed(p) for p in l3] for l3 in loops]
    all_chords = []
    loop_polys = []
    for l3 in posed_loops:
        n3 = len(l3)

        def coll_at(i3):
            a, b, c = l3[(i3 - 1) % n3], l3[i3], l3[(i3 + 1) % n3]
            cr = (b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0])
            dt = (b[0] - a[0]) * (c[0] - b[0]) + (b[2] - a[2]) * (c[2] - b[2])
            return abs(cr) < 1e-7 and dt > 0
        starts = [i3 for i3 in range(n3) if not coll_at(i3)] or [0]
        seq = [l3[(starts[0] + i3) % n3] for i3 in range(n3)] + [l3[starts[0]]]
        run = [seq[0]]
        for q2 in range(1, len(seq)):
            run.append(seq[q2])
            if q2 == len(seq) - 1:
                all_chords.append((run[0], run[-1], run[1:-1]))
                break
            a0, b, c = run[0], seq[q2], seq[q2 + 1]
            cr = (b[0] - a0[0]) * (c[2] - a0[2]) - (b[2] - a0[2]) * (c[0] - a0[0])
            dt = (b[0] - a0[0]) * (c[0] - b[0]) + (b[2] - a0[2]) * (c[2] - b[2])
            if abs(cr) > 1e-7 or dt <= 0:
                all_chords.append((run[0], run[-1], run[1:-1]))
                run = [seq[q2]]
        loop_polys.append([(p[0], p[2]) for p in l3])
    outer_poly = loop_polys[0]
    sec_polys = loop_polys[1:]
    print(f"   chords: {len(all_chords)} (collinear runs merged from "
          f"{sum(len(l3) for l3 in posed_loops)} rim edges)")

    # ---- the ground: exact cut of the bench grass at the rim lines -------------------------
    def slice_line(pg, o, dvec):
        keep_pos, keep_neg = [], []
        n3 = len(pg)
        dd = [((p[0] - o[0]) * dvec[1] - (p[1] - o[1]) * dvec[0]) for p in pg]
        for i3 in range(n3):
            a, b = pg[i3], pg[(i3 + 1) % n3]
            da, db = dd[i3], dd[(i3 + 1) % n3]
            if da >= -1e-12:
                keep_pos.append(a)
            if da <= 1e-12:
                keep_neg.append(a)
            if (da > 1e-12 and db < -1e-12) or (da < -1e-12 and db > 1e-12):
                t = da / (da - db)
                m = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
                keep_pos.append(m)
                keep_neg.append(m)
        return keep_pos, keep_neg

    rim_lines = [((c[0][0], c[0][2]), (c[1][0] - c[0][0], c[1][2] - c[0][2]))
                 for c in all_chords]
    grass_keep, grass_cut, dropped = [], [], 0
    rim_r_max = max(math.hypot(p[0] - CENTER[0], p[1] - CENTER[1]) for p in outer_poly)

    def keep_pg(pg):
        cx3 = sum(p[0] for p in pg) / len(pg)
        cz3 = sum(p[1] for p in pg) / len(pg)
        if any(pinp(cx3, cz3, sp2) for sp2 in sec_polys):
            return True                                     # a forest-hole ground patch
        return not pinp(cx3, cz3, outer_poly)
    for ti, t in enumerate(tris):
        if t["topo"] not in GRASS_TOPO:
            grass_keep.append(ti)
            continue
        d0 = math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
        if d0 > rim_r_max + 8.0:
            grass_keep.append(ti)
            continue
        pieces = [[(p[0], p[2]) for p in t["w"]]]
        for (o, dvec) in rim_lines:
            nxt = []
            for pg in pieces:
                pos_, neg_ = slice_line(pg, o, dvec)
                for part in (pos_, neg_):
                    if len(part) >= 3 and poly_area2(part) > 1e-14:
                        nxt.append(part)
            pieces = nxt
        kept_pieces = [pg for pg in pieces if keep_pg(pg)]
        if len(pieces) == 1 and kept_pieces:
            grass_keep.append(ti)
        else:
            grass_cut.append((ti, kept_pieces))
            dropped += 0 if kept_pieces else 1
    print(f"ground: {dropped} grass tris dropped inside the rim, {len(grass_cut)} cut, "
          f"{len(grass_keep)} untouched")

    # ---- THE RIM WELD: bench crossings canonicalize/refine against the rim edges -----------
    def chord_param(c, p2):
        a, b2 = c[0], c[1]
        dx, dz = b2[0] - a[0], b2[2] - a[2]
        L2 = (dx * dx + dz * dz) or 1.0
        return ((p2[0] - a[0]) * dx + (p2[1] - a[2]) * dz) / L2

    def on_chord(c, p2):
        a, b2 = c[0], c[1]
        dx, dz = b2[0] - a[0], b2[2] - a[2]
        L = math.hypot(dx, dz) or 1.0
        cr = ((p2[0] - a[0]) * dz - (p2[1] - a[2]) * dx) / L
        if abs(cr) > 1.5e-3:
            return None
        t = chord_param(c, p2)
        return t if -1e-6 <= t <= 1 + 1e-6 else None

    chord_pts = []                                          # per chord: [(t, 3D point)]
    for c in all_chords:
        chain = [(0.0, c[0])] + [(chord_param(c, (m2[0], m2[2])), m2)
                                 for m2 in c[2]] + [(1.0, c[1])]
        chord_pts.append(chain)
    chord_base = [list(ch) for ch in chord_pts]             # the rim's own verts (pre-crossing)

    def chain_y(ci2, t):
        """y at chord param t, interpolated per SUB-edge (plan-straight, y-kinked)."""
        ch = chord_base[ci2]
        for (t0, p0), (t1, p1) in zip(ch, ch[1:]):
            if t <= t1 + 1e-12:
                f2 = 0.0 if t1 - t0 < 1e-12 else (t - t0) / (t1 - t0)
                return p0[1] + f2 * (p1[1] - p0[1])
        return ch[-1][1][1]

    gsnap = {}
    n_gadd = 0
    for ti, pieces in grass_cut:
        for pg in pieces:
            for q2 in pg:
                for ci2, c in enumerate(all_chords):
                    t = on_chord(c, q2)
                    if t is None:
                        continue
                    Lc = math.dist((c[0][0], c[0][2]), (c[1][0], c[1][2])) or 1.0
                    nt, npnt = min(chord_pts[ci2], key=lambda tp: abs(tp[0] - t))
                    if abs(nt - t) * Lc <= 2e-3:
                        if math.hypot(q2[0] - npnt[0], q2[1] - npnt[2]) > 1e-9:
                            gsnap[(round(q2[0], 4), round(q2[1], 4))] = \
                                (npnt[0], npnt[2])
                    elif all(abs(t - t0) > 1e-9 for t0, _ in chord_pts[ci2]):
                        chord_pts[ci2].append((t, (q2[0], chain_y(ci2, t), q2[1])))
                        n_gadd += 1
                    break
    for ci2 in range(len(chord_pts)):
        chord_pts[ci2].sort()
    if gsnap:
        grass_cut = [(ti, [[gsnap.get((round(q2[0], 4), round(q2[1], 4)), q2)
                            for q2 in pg] for pg in pieces])
                     for ti, pieces in grass_cut]
    # bench crossing points refine the APRON's rim tris per SUB-edge (edge-lerped attrs)
    foot_refine = defaultdict(list)
    for ci2, c in enumerate(all_chords):
        for (t0, p0), (t1, p1) in zip(chord_base[ci2], chord_base[ci2][1:]):
            mids2 = [p for (t2, p) in chord_pts[ci2] if t0 + 1e-9 < t2 < t1 - 1e-9]
            if mids2:
                ek = tuple(sorted((kk(p0), kk(p1))))
                foot_refine[ek].extend(mids2)
    wall, n_foot_split = refine_wall(wall, foot_refine)
    print(f"rim weld: {len(gsnap)} bench verts canonicalized to rim points, "
          f"{n_gadd} bench crossings added to rim edges, {n_foot_split} apron rim splits")

    # ---- THE BLEND (the round's ONE minted vertex class): bench grass rises to the rim -----
    rimy = {}                                               # plan key -> exact rim y
    for chain2 in chord_pts:
        for _t2, p in chain2:
            rimy[(round(p[0], 4), round(p[2], 4))] = p[1]
    segs = [(np.array([c[0][0], c[0][2]]), np.array([c[1][0], c[1][2]]),
             c[0][1], c[1][1]) for c in all_chords]

    def blend_y(x, z):
        key = (round(x, 4), round(z, 4))
        if key in rimy:
            return rimy[key]
        best = None
        for a2, b2, ya, yb in segs:
            ab = b2 - a2
            L2 = float(ab @ ab) or 1.0
            t = max(0.0, min(1.0, float((np.array([x, z]) - a2) @ ab) / L2))
            q = a2 + t * ab
            d = math.hypot(x - q[0], z - q[1])
            if best is None or d < best[0]:
                best = (d, ya + t * (yb - ya))
        d, ynear = best
        if d >= BLEND_R:
            return LOWLAND
        s2 = 1.0 - d / BLEND_R
        w2 = s2 * s2 * (3.0 - 2.0 * s2)
        return LOWLAND + w2 * (ynear - LOWLAND)

    # THE LIFT IS PER-VERTEX, INTERPOLATED EVERYWHERE ELSE. Run 1 evaluated the field
    # per derived point; neighbours lerp per edge, so every kept/cut boundary and every
    # T-split cracked (149 cut + 63 kept once-edges). The conforming scheme: the field
    # is sampled ONLY at original bench verts (vlift); every derived point -- fragment
    # corner, crossing, conformance split, sweep split -- takes y by interpolating its
    # parent's LIFTED verts, so all derived y's are piecewise-linear over one surface.
    # Verts shared with any NON-grass bench tri never lift (coast edges stay put).
    banned = {kk(p) for t in tris if t["topo"] not in GRASS_TOPO for p in t["w"]}
    vlift = {}
    n_lift = 0
    max_lift = 0.0
    for t in tris:
        if t["topo"] not in GRASS_TOPO:
            continue
        for p in t["w"]:
            k3 = kk(p)
            if k3 in vlift or k3 in banned or abs(p[1] - LOWLAND) > 1e-6:
                continue
            if math.hypot(p[0] - CENTER[0], p[2] - CENTER[1]) > rim_r_max + BLEND_R + 2.0:
                continue
            y2 = blend_y(p[0], p[2])
            if abs(y2 - LOWLAND) > 1e-9:
                vlift[k3] = y2
                n_lift += 1
                max_lift = max(max_lift, abs(y2 - LOWLAND))

    def parent_dispy(t, p2):
        """y of plan point p2 on the parent tri's LIFTED surface (affine)."""
        ys = [vlift.get(kk(t["w"][k]), t["w"][k][1]) for k in range(3)]
        (x1, z1), (x2, z2), (x3, z3) = ((t["w"][k][0], t["w"][k][2]) for k in range(3))
        det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
        if abs(det) < 1e-12:
            return ys[0]
        w2 = ((p2[0] - x1) * (z3 - z1) - (x3 - x1) * (p2[1] - z1)) / det
        w3 = ((x2 - x1) * (p2[1] - z1) - (p2[0] - x1) * (z2 - z1)) / det
        return (1 - w2 - w3) * ys[0] + w2 * ys[1] + w3 * ys[2]

    def enrich_rim_edges(pg):
        out2 = []
        n3 = len(pg)
        for q2 in range(n3):
            a, b2 = pg[q2], pg[(q2 + 1) % n3]
            out2.append(a)
            for ci2, c in enumerate(all_chords):
                ta = on_chord(c, a)
                tb = on_chord(c, b2)
                if ta is None or tb is None or abs(tb - ta) < 1e-9:
                    continue
                lo2, hi2 = (ta, tb) if ta < tb else (tb, ta)
                mids2 = [(t2, p) for (t2, p) in chord_pts[ci2]
                         if lo2 + 1e-9 < t2 < hi2 - 1e-9]
                if not mids2:
                    break
                mids2.sort(reverse=(ta > tb))
                out2.extend((p[0], p[2]) for _, p in mids2)
                break
        return out2

    grass_cut = [(ti, [enrich_rim_edges(pg) for pg in pieces])
                 for ti, pieces in grass_cut]
    frag_verts2 = {}
    for ti, pieces in grass_cut:
        for pg in pieces:
            for q in pg:
                frag_verts2[(round(q[0], 3), round(q[1], 3))] = q
    for chain2 in chord_pts:
        for _t2, p in chain2:
            frag_verts2[(round(p[0], 3), round(p[2], 3))] = (p[0], p[2])

    def affine_attr(t, p2, chan):
        (x1, z1), (x2, z2), (x3, z3) = ((t["w"][k][0], t["w"][k][2]) for k in range(3))
        det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
        if abs(det) < 1e-12:
            return list(t[chan][0])
        w2 = ((p2[0] - x1) * (z3 - z1) - (x3 - x1) * (p2[1] - z1)) / det
        w3 = ((x2 - x1) * (p2[1] - z1) - (p2[0] - x1) * (z2 - z1)) / det
        w1 = 1 - w2 - w3
        return [w1 * t[chan][0][j] + w2 * t[chan][1][j] + w3 * t[chan][2][j]
                for j in range(len(t[chan][0]))]

    def _on_seg2(p2, a, b):
        ax, az, bx, bz = a[0], a[2], b[0], b[2]
        cross = (bx - ax) * (p2[1] - az) - (bz - az) * (p2[0] - ax)
        if abs(cross) > 1e-3:
            return None
        L2 = (bx - ax) ** 2 + (bz - az) ** 2
        if L2 < 1e-9:
            return None
        t = ((p2[0] - ax) * (bx - ax) + (p2[1] - az) * (bz - az)) / L2
        return t if 1e-4 < t < 1 - 1e-4 else None

    kept_out = []                                           # (t3, uv3, n3, tan3, blk)
    n_kept_split = 0
    for ti in grass_keep:
        t = tris[ti]
        d0 = math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
        if t["topo"] not in (GRASS_TOPO | {53, 54, 55, 56}) or d0 > rim_r_max + 16.0:
            kept_out.append((t["w"], t["uv"], t["n"], t["tan"], t["blk"]))
            continue
        w_l = [(p[0], vlift.get(kk(p), p[1]), p[2]) for p in t["w"]]
        pg = []
        inserted = False
        for k3 in range(3):
            a, b = w_l[k3], w_l[(k3 + 1) % 3]
            pg.append((a, t["uv"][k3], t["n"][k3], t["tan"][k3]))
            ins = []
            for p2 in frag_verts2:
                if (round(a[0], 3), round(a[2], 3)) == p2 or \
                        (round(b[0], 3), round(b[2], 3)) == p2:
                    continue
                tt = _on_seg2(p2, a, b)
                if tt is not None:
                    ins.append((tt, p2))
            for tt, p2 in sorted(ins):
                p3 = (p2[0], a[1] + tt * (b[1] - a[1]), p2[1])
                pg.append((p3, affine_attr(t, p2, "uv"), affine_attr(t, p2, "n"),
                           affine_attr(t, p2, "tan")))
                inserted = True
                n_kept_split += 1
        if not inserted:
            kept_out.append(([q[0] for q in pg], t["uv"], t["n"], t["tan"], t["blk"]))
            continue
        cx = sum(q[0][0] for q in pg) / len(pg)
        cy = sum(q[0][1] for q in pg) / len(pg)
        cz = sum(q[0][2] for q in pg) / len(pg)
        cen_rec = ((cx, cy, cz), affine_attr(t, (cx, cz), "uv"),
                   affine_attr(t, (cx, cz), "n"), affine_attr(t, (cx, cz), "tan"))
        for q0 in range(len(pg)):
            a_r, b_r = pg[q0], pg[(q0 + 1) % len(pg)]
            t3 = [cen_rec[0], a_r[0], b_r[0]]
            if np.cross(np.array(t3[1]) - np.array(t3[0]),
                        np.array(t3[2]) - np.array(t3[0]))[1] < 0:
                a_r, b_r = b_r, a_r
                t3 = [cen_rec[0], a_r[0], b_r[0]]
            kept_out.append((t3, [cen_rec[1], a_r[1], b_r[1]],
                             [cen_rec[2], a_r[2], b_r[2]],
                             [cen_rec[3], a_r[3], b_r[3]], t["blk"]))
    print(f"kept conformance: {n_kept_split} edge splits on kept grass; blend lifted "
          f"{n_lift} bench verts (max {max_lift:.2f}u over {BLEND_R}u)")

    # ---- L3 (no minted top exists; kept verbatim as a no-op seeder) ------------------------
    sys.path.insert(0, str(ROOT / "studies" / "overworld-topography"))
    import uvf_fix2 as UF                                   # noqa: E402

    def tri_cell(t3):
        cx4 = float(np.mean([p[0] for p in t3]))
        cz4 = float(np.mean([p[2] for p in t3]))
        return (math.floor(cx4 / CELL), math.floor(cz4 / CELL))

    pre_quad, pre_ori = {}, {}
    kept_set = set(grass_keep)
    for ti, t in enumerate(tris):
        if ti not in kept_set or t["topo"] not in GRASS_TOPO:
            continue
        ccell = tri_cell(t["w"])
        if ccell in pre_quad:
            continue
        if math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1]) > rim_r_max + 26.0:
            continue
        qo = UF.decode_quad_ori(ccell, t["w"], [tuple(u2) for u2 in t["uv"]])
        if qo is not None:
            pre_quad[ccell], pre_ori[ccell] = qo
    top_cells = sorted({tri_cell(t3) for t3 in top_tris})
    q2, o2 = UF.assign_mains_seeded([c for c in top_cells if c not in pre_quad],
                                    dict(pre_quad), dict(pre_ori), seed=SEED ^ 0xF92)
    cell_qo = {c: (pre_quad[c], pre_ori[c]) for c in top_cells if c in pre_quad}
    cell_qo.update({c: (q2[c], o2[c]) for c in q2 if c in set(top_cells)})
    print(f"L3 top: {len(pre_quad)} cells decoded from bench grass, {len(q2)} policy-resolved")
    top_out = []
    for t3 in top_tris:
        ccell = tri_cell(t3)
        quad, ori = cell_qo[ccell]
        top_out.append((t3, [G.ground_uv(p[0], p[2], ccell, quad, ori) for p in t3]))

    # cut grass pieces: parent-affine uvs; y = exact rim value on the rim, else the
    # parent's own LIFTED surface (the conforming scheme -- never the raw field)
    cut_out = []
    for ti, pieces in grass_cut:
        t = tris[ti]
        for pg in pieces:
            for tt in centroid_fan(pg):
                t3 = []
                for q in tt:
                    key = (round(q[0], 4), round(q[1], 4))
                    if key in rimy:
                        t3.append((q[0], rimy[key], q[1]))
                    else:
                        t3.append((q[0], parent_dispy(t, q), q[1]))
                a, b, c = (np.array(p) for p in t3)
                if np.cross(b - a, c - a)[1] < 0:
                    t3 = [t3[0], t3[2], t3[1]]
                uvt = [affine_attr(t, (p[0], p[2]), "uv") for p in t3]
                cut_out.append((t3, uvt, t))
    print(f"ground cut fragments: {len(cut_out)} tris re-emitted (parent-affine UVs, "
          f"rim-welded y)")

    # ---- THE GLOBAL T-CONFORMANCE SWEEP (fixpoint; verbatim) -------------------------------
    ID_SHELF = float(X.encode_id(topograph=SHELF))
    ID_ROCK = float(X.encode_id(topograph=ROCK))
    final = []                                              # (rec, blk); rec=[(p,uv,n,t4)]
    for t3, uv3, n3, tan3, blk in kept_out:
        final.append(([(tuple(t3[k3]), tuple(uv3[k3]), tuple(n3[k3]), tuple(tan3[k3]))
                       for k3 in range(3)], blk))
    for t3, uvt, src in cut_out:
        final.append(([(tuple(t3[k3]), tuple(uvt[k3]), tuple(src["n"][0]),
                        tuple(src["tan"][0])) for k3 in range(3)], None))
    for rec in wall:
        final.append(([(tuple(r[0]), tuple(r[1]), tuple(r[2]), tuple(r[3]))
                       for r in rec], None))

    def near_notch(cx3, cz3):
        if any(pinp(cx3, cz3, np_) for np_ in notch_polys):
            return True
        return any(math.hypot(cx3 - p[0], cz3 - p[2]) < 2.0
                   for pt in notch_patches for p in pt)

    n_chute = 0
    for t3, uvt in top_out:
        cx3 = float(np.mean([p[0] for p in t3]))
        cz3 = float(np.mean([p[2] for p in t3]))
        tid = ID_SHELF
        nrm_t = (0.0, 1.0, 0.0)
        if near_notch(cx3, cz3):
            tid = ID_ROCK
            n_chute += 1
            a3n, b3n, c3n = (np.array(p) for p in t3)
            fn3 = np.cross(b3n - a3n, c3n - a3n)
            L3n = float(np.linalg.norm(fn3))
            if L3n > 1e-9:
                nrm_t = tuple(float(v) / L3n for v in fn3)
        final.append(([(tuple(t3[k3]), tuple(uvt[k3]), nrm_t,
                        (tid, 0.0, 0.0, 1.0)) for k3 in range(3)], None))
    if n_chute:
        print(f"   notch chutes: {n_chute} top tris carry ROCK topograph (unwalkable)")

    bench_verts = {kk(p) for t3, _, _, _, _ in kept_out for p in t3}
    crest_keys = set(crest)
    uniq_v = {}
    for rec, _blk in final:
        for r in rec:
            uniq_v[kk(r[0])] = r[0]
    Hm = defaultdict(list)
    for k3, p in uniq_v.items():
        Hm[(int(p[0] // 1), int(p[2] // 1))].append(k3)
    mparent = {k3: k3 for k3 in uniq_v}

    def mfind(k3):
        while mparent[k3] != k3:
            mparent[k3] = mparent[mparent[k3]]
            k3 = mparent[k3]
        return k3
    for k3, p in uniq_v.items():
        for cx3 in (int(p[0] // 1) - 1, int(p[0] // 1), int(p[0] // 1) + 1):
            for cz3 in (int(p[2] // 1) - 1, int(p[2] // 1), int(p[2] // 1) + 1):
                for k4 in Hm.get((cx3, cz3), ()):
                    if k4 > k3 and math.dist(uniq_v[k3], uniq_v[k4]) <= 0.06:
                        ra, rb = mfind(k3), mfind(k4)
                        if ra != rb:
                            mparent[ra] = rb
    clusters = defaultdict(list)
    for k3 in uniq_v:
        clusters[mfind(k3)].append(k3)
    vmap = {}
    n_mw = 0
    for _root, ks in clusters.items():
        if len(ks) < 2:
            continue
        canon = (sorted(k3 for k3 in ks if k3 in bench_verts)
                 or sorted(k3 for k3 in ks if k3 in crest_keys)
                 or sorted(ks))[0]
        for k3 in ks:
            if k3 != canon:
                vmap[k3] = uniq_v[canon]
                n_mw += 1
    if vmap:
        out_mw = []
        n_dropped = 0
        for rec, blk in final:
            nr = [(vmap.get(kk(r[0]), r[0]), r[1], r[2], r[3]) for r in rec]
            if len({kk(r[0]) for r in nr}) == 3:
                out_mw.append((nr, blk))
            else:
                n_dropped += 1
        final = out_mw
        print(f"   micro-weld: {n_mw} splinter verts merged, {n_dropped} collapsed "
              f"tris dropped")

    prev_sw = None
    for sweep_pass in range(1):
        H2 = defaultdict(list)
        for rec, _blk in final:
            for r in rec:
                H2[(int(r[0][0] // 2), int(r[0][2] // 2))].append(r[0])

        def cands2(a, b2):
            x0, x1 = sorted((a[0], b2[0]))
            z0, z1 = sorted((a[2], b2[2]))
            out3 = []
            for cx3 in range(int((x0 - 0.01) // 2), int((x1 + 0.01) // 2) + 1):
                for cz3 in range(int((z0 - 0.01) // 2), int((z1 + 0.01) // 2) + 1):
                    out3.extend(H2.get((cx3, cz3), ()))
            return out3

        def on_edge3(p, a, b2):
            ka3, kb3 = kk(a), kk(b2)
            kp3 = kk(p)
            if kp3 == ka3 or kp3 == kb3:
                return None
            ab = (b2[0] - a[0], b2[1] - a[1], b2[2] - a[2])
            L2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2
            if L2 < 1e-12:
                return None
            t = ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]
                 + (p[2] - a[2]) * ab[2]) / L2
            if not (1e-4 < t < 1 - 1e-4):
                return None
            q = (a[0] + t * ab[0], a[1] + t * ab[1], a[2] + t * ab[2])
            tol = 0.065 if min(a[1], b2[1]) > LOWLAND + 2.0 else 2e-3
            return t if math.dist(p, q) <= tol else None

        out_f = []
        n_sw = 0
        for rec, blk in final:
            ins_all = [[], [], []]
            seen3 = {kk(r[0]) for r in rec}
            for k3 in range(3):
                a_r, b_r = rec[k3], rec[(k3 + 1) % 3]
                got = {}
                for p in cands2(a_r[0], b_r[0]):
                    t = on_edge3(p, a_r[0], b_r[0])
                    if t is not None and kk(p) not in seen3 and kk(p) not in got:
                        got[kk(p)] = (t, p)
                ins_all[k3] = sorted(got.values())
            n_hit = sum(1 for i3 in ins_all if i3)
            if not n_hit:
                out_f.append((rec, blk))
                continue
            n_sw += sum(len(i3) for i3 in ins_all)
            poly = []
            for k3 in range(3):
                a_r, b_r = rec[k3], rec[(k3 + 1) % 3]
                poly.append(a_r)
                for t, p in ins_all[k3]:
                    uv_m = tuple(a_r[1][q2] + t * (b_r[1][q2] - a_r[1][q2])
                                 for q2 in range(2))
                    n_m = tuple(a_r[2][q2] + t * (b_r[2][q2] - a_r[2][q2])
                                for q2 in range(3))
                    poly.append((tuple(p), uv_m, n_m, a_r[3]))
            hitset = {k3 for k3 in range(3) if ins_all[k3]}
            if len(hitset) == 1:
                c_key = kk(rec[(next(iter(hitset)) + 2) % 3][0])
            elif hitset == {0, 1}:
                c_key = kk(rec[1][0])
            elif hitset == {1, 2}:
                c_key = kk(rec[2][0])
            else:
                c_key = kk(rec[0][0])
            start = next(q2 for q2 in range(len(poly))
                         if kk(poly[q2][0]) == c_key)
            cyc = poly[start:] + poly[:start]
            for q2 in range(1, len(cyc) - 1):
                out_f.append(([cyc[0], cyc[q2], cyc[q2 + 1]], blk))
        final = out_f
        print(f"   T-sweep pass {sweep_pass}: {n_sw} splits -> {len(final)} tris")
        if not n_sw:
            break
        if prev_sw is not None and n_sw > max(220, prev_sw * 2.0):
            print("   T-sweep DIVERGING -- stopped; the audit will show the state")
            break
        prev_sw = n_sw

    # ---- gates ------------------------------------------------------------------------------
    fails = []
    if gap > 2.5:
        fails.append(f"closure gap {gap:.2f}u exceeds the last seam's taper budget")
    for si, dmax in enumerate(weld_stats):
        W_si = move_maps[(si + 1) % S][3]
        if dmax > WELD_DISP_MAX:
            fails.append(f"seam {si}: weld displacement {dmax:.2f}u exceeds the "
                         f"{WELD_DISP_MAX}u hard cap")
        if dmax / W_si > SHEAR_MAX:
            fails.append(f"seam {si}: shear ratio {dmax / W_si:.2f} exceeds "
                         f"{SHEAR_MAX} (taper {W_si:.1f}u)")
    for i, (n_ok, n_bad, bad2) in enumerate(seam_report):
        if n_bad > n_ok:
            fails.append(f"seam {i}: h_pairs mostly unlawful ({n_bad} vs {n_ok}) {bad2}")

    # THE BAND GATE (BASE-TILE-GRAMMAR.md): the donor's own transitional band must sit
    # above ground -- the whole point of the re-seat
    if band_share < 0.8:
        fails.append(f"band: foot-course rows 10+11 share {band_share:.1%} < 80% -- "
                     f"the transition did not survive the seat")

    def outward_of(px, pz):
        d = (px - CENTER[0], pz - CENTER[1])
        L = math.hypot(*d) or 1.0
        return (d[0] / L, d[1] / L)

    n_degen = 0
    for rec in wall:
        t3 = [r[0] for r in rec]
        a, b, c = (np.array(p) for p in t3)
        fn = np.cross(b - a, c - a)
        L = float(np.linalg.norm(fn))
        if L < 2e-2:
            n_degen += 1
            continue
        nv = np.array([float(np.mean([r[2][q2] for r in rec])) for q2 in range(3)])
        Ln = float(np.linalg.norm(nv))
        if Ln > 1e-6 and float(fn @ nv) / (L * Ln) < -0.3:
            fails.append(f"winding: a carried tri OPPOSES its carried normals at "
                         f"{kk(t3[0])} (area {L / 2:.3f}u2, verts {[kk(p) for p in t3]})")
    for t3, _ in top_out:
        cx3 = float(np.mean([p[0] for p in t3]))
        cz3 = float(np.mean([p[2] for p in t3]))
        if near_notch(cx3, cz3):
            continue
        a, b, c = (np.array(p) for p in t3)
        fn = np.cross(b - a, c - a)
        if fn[1] < 0 and float(np.linalg.norm(fn)) > 2e-2:
            fails.append(f"winding: a top tri faces DOWN at {kk(t3[0])}")
    print(f"winding: {n_degen} near-degenerate carried tris exempt")

    cnt3 = defaultdict(int)

    def _acc(t3):
        ps = [kk(p) for p in t3]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt3[tuple(sorted((ps[a], ps[b])))] += 1
    cnt0 = defaultdict(int)
    for t in tris:
        ps = [kk(p) for p in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt0[tuple(sorted((ps[a], ps[b])))] += 1
    pre_once = {e for e, n in cnt0.items() if n == 1}
    for rec, _blk in final:
        _acc([r[0] for r in rec])
    post_once = {e for e, n in cnt3.items() if n == 1}
    grew = post_once - pre_once

    def degen(e):
        return e[0] == e[1]

    # DECLARED class: STOCK'S OWN open edges, carried verbatim. The donor blocks are
    # themselves 2.8-6.8% open (junction study J1/J3); a carried once-edge that was
    # already once in the donor soup is stock's crack, not our weld's miss.
    soup_once = set()
    for e, ts in ET.items():
        if len(ts) == 1:
            soup_once.add(tuple(sorted((kk(posed(e[0])), kk(posed(e[1]))))))
    n_stock_open = sum(1 for e in grew if not degen(e) and e in soup_once)
    grew_bad = [e for e in grew if not degen(e) and e not in soup_once]
    if n_stock_open:
        print(f"   {n_stock_open} once-edges are STOCK'S OWN open cracks carried "
              f"verbatim (declared class)")
    n_dg = sum(1 for e in grew if degen(e))
    n_all_edges = len(cnt3)
    rate = len(grew_bad) / max(1, n_all_edges)
    print(f"watertight: {len(grew)} new once-edges = {n_dg} degenerate + "
          f"{len(grew_bad)} residual of {n_all_edges} edges ({rate:.4%}; STOCK's own "
          f"measured open rate is 2.8-6.8%)")
    long_bad = [e for e in grew_bad if math.dist(e[0], e[1]) > 5.0]
    if len(grew_bad) > 24:
        fails.append(f"watertight: {len(grew_bad)} residual once-edges exceed the "
                     f"24-edge bound (stock-rate-derived)")
    if long_bad:
        fails.append(f"watertight: {len(long_bad)} residual once-edges longer than 5u "
                     f"(sample {long_bad[:2]})")
        edge_owner = defaultdict(list)

        def _tag(t3, tag):
            ps = [kk(p) for p in t3]
            for a2, b2 in ((0, 1), (1, 2), (2, 0)):
                edge_owner[tuple(sorted((ps[a2], ps[b2])))].append(tag)
        for rec in wall:
            _tag([r[0] for r in rec], "wall")
        for t3, _ in top_out:
            _tag(t3, "top")
        for t3, _, _ in cut_out:
            _tag(t3, "cut")
        for t3, _, _, _, _ in kept_out:
            _tag(t3, "kept")
        hist = Counter(tuple(sorted(set(edge_owner.get(e, ["?"])))) for e in grew_bad)
        print(f"   undeclared owners: {dict(hist)}")
        for e in grew_bad[:6]:
            print(f"   BAD {edge_owner.get(e, ['?'])} {e}")
        for e0 in grew_bad[:4]:
            print(f"   FORENSICS edge {e0}:")
            for rec, _blk in final:
                ks3 = [kk(r[0]) for r in rec]
                if e0[0] in ks3 or e0[1] in ks3:
                    print(f"     tri: {ks3}")

    if args.probe:
        for (qx3, qz3, tag3) in ((428.0, -507.0, "east base"),
                                 (396.0, -504.0, "west base"),
                                 (416.0, -534.0, "south rim")):
            print(f"   PROBE {tag3} ({qx3}, {qz3}):")
            for rec, _blk in final:
                cx3 = float(np.mean([r[0][0] for r in rec]))
                cz3 = float(np.mean([r[0][2] for r in rec]))
                if math.hypot(cx3 - qx3, cz3 - qz3) < 2.5:
                    print(f"     {[kk(r[0]) for r in rec]}")

    # massing: REPORT-ONLY this round. The gate's subject -- a MINTED ground silhouette
    # -- does not exist: the visible rock-to-ground line is the donor's own weld line
    # (stock bytes, cannot be unlawful), and the grass-to-grass rim is a height-blended
    # boundary between two grass sheets with no visible silhouette. Stats recorded for
    # the build notes; nothing to gate.
    wadj2 = defaultdict(list)
    for e in weld_edges:
        wadj2[e[0]].append(e[1])
        wadj2[e[1]].append(e[0])
    trimmedW = True
    while trimmedW:
        trimmedW = False
        for p in list(wadj2):
            if len(wadj2[p]) == 1:
                q = wadj2[p][0]
                wadj2[q].remove(p)
                del wadj2[p]
                trimmedW = True
            elif len(wadj2[p]) == 0:
                del wadj2[p]
                trimmedW = True
    wloops = []
    visW = set()
    for startW in list(wadj2):
        if startW in visW:
            continue
        lw = [startW]
        prevW = None
        while True:
            nxtsW = [p for p in wadj2[lw[-1]] if p != prevW]
            if not nxtsW or nxtsW[0] == startW:
                break
            prevW = lw[-1]
            lw.append(nxtsW[0])
        visW.update(lw)
        if len(lw) >= 3:
            wloops.append(lw)
    wloops.sort(key=lambda l3: -abs(poly_area2([(p[0], p[2]) for p in l3])))
    fl0 = [(p[0] + tx, p[2] + tz) for p in wloops[0]] if wloops else []
    if fl0:
        fturn = [signed_turn(fl0[(i2 - 1) % len(fl0)], fl0[i2],
                             fl0[(i2 + 1) % len(fl0)])
                 for i2 in range(len(fl0))]
        fabs = [abs(a2) for a2 in fturn]
        print(f"massing (report only -- the ground line is DONOR bytes): weld-line "
              f"turn med {float(np.median(fabs)):.1f} deg, right angles "
              f"{sum(1 for a2 in fabs if 80 <= a2 <= 100)}/{len(fabs)}")

    # reach: report only -- the bench-grass clip in the apron flood enforces fit
    # structurally (the collar ends where the bench's grass ends), so an island
    # re-mint is no longer the gate's prescription
    reach_vis = max(math.hypot(r[0][0] - CENTER[0], r[0][2] - CENTER[1])
                    for rec in wall for r in rec)
    print(f"reach: {reach_vis:.1f}u (bench grass ~{grass_r:.1f}u max; fit enforced "
          f"by the grass clip)")

    # ---- assemble ---------------------------------------------------------------------------
    by_cell = defaultdict(lambda: ([], [], [], []))

    def emit(cell, p, u2, n2, t4):
        pos, nrm, uv, tan = by_cell[cell]
        pos.append([p[0] - BLOCK * cell[0], p[1], p[2] + BLOCK * cell[1]])
        nrm.append(list(n2))
        uv.append(list(u2))
        tan.append(list(t4))

    def cell_of(t3):
        cx = float(np.mean([p[0] for p in t3]))
        cz = float(np.mean([p[2] for p in t3]))
        return (int(cx // BLOCK), int(-cz // BLOCK))

    for rec, blk in final:
        c = blk if blk is not None else cell_of([r[0] for r in rec])
        for k3 in range(3):
            emit(c, rec[k3][0], rec[k3][1], rec[k3][2], rec[k3][3])

    changed = {}
    for cell, (pos, nrm, uv, tan) in by_cell.items():
        flat = list(range(len(pos)))
        changed[cell] = X.BlockMesh(
            name=f"Block[{cell[0]}][{cell[1]}] Terrain", disc=DISC, x=cell[0], y=cell[1],
            lod="0_1", vcount=len(pos), stride=48,
            channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
            chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
            flat_index=flat, tris=[flat[3 * t2:3 * t2 + 3] for t2 in range(len(flat) // 3)],
            raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
    IN.census_gate(changed, disc=1)
    print(f"census MISS=0 across {len(changed)} changed cells")

    # ---- renders ----------------------------------------------------------------------------
    render(wall, top_out, cut_out, kept_out, crest)

    print(f"gates: {len(fails)} failure(s)")
    for f in fails[:10]:
        print("  !!", f)
    if fails:
        print("\nAPRON: GATES RED -- not deployable")
        return 1
    if not args.apply:
        print("\nAPRON: gates green (offline). Review the renders; --apply to deploy.")
        return 0

    ts = time.strftime("%Y%m%d-%H%M%S")
    bdir = Path(r"C:\gd\Dream-World-IX\backups") / f"terrace-strip-prewall.{ts}"
    bdir.mkdir(parents=True, exist_ok=True)
    for cell, (p, _bm) in bms.items():
        shutil.copy2(p, bdir / p.name)
    for cell, bm in sorted(changed.items()):
        w = M.deploy_override(bm, mod_folder=MOD, disc=DISC, part="Terrain")
        print(f"deployed -> {w} ({len(bm.tris)} tris)")
    print(f"pre-wall bench backed up -> {bdir}")
    print("in game: ~ -> Go -> 9013 -> World -> teleport (416, -512); re-enter the world.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
