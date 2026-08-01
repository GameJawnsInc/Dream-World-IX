"""THE BAND SEAT -- the (15,14) mesa on a LEVEL HOST, cut inside its own band course.

Registration: studies/path-d-new-world/BAND-SEAT-PREDICTION.md. This is mesa_carry.py
(the level-cut build with two clean playtests: 4 residual once-edges, an untouched
flat lawn, zero seam/tile/hill complaints) with exactly ONE lever changed and one
falsified block removed:

- THE SEAT: the bury round's `dy = LOWLAND - (w_max + 0.2)` put the whole ground-weld
  line just below the cut, so the cut crossed MID-FACE rock and the base had no
  transition art. The band-seat window `[LOWLAND - w_p10 - 3.7, LOWLAND - w_max]`
  (~[-4.31, -4.2]) keeps every column's wall reaching the cut plane AND lands the cut
  INSIDE the donor's own ~3.7u band course for every column with weld >= ~3.75 --
  the visible bottom course becomes the donor's own row-10/11 transition art,
  carried bytes, u and v the column's own continuation (THE BAND-CONTINUATION LAW
  satisfied by construction; the low-weld tail shows the row above = stock's own
  intermittency).
- THE FRINGE BLOCK IS DELETED: the arclength-stationed re-mint is the falsified lane
  (mismatched faces, BASE-TILE-GRAMMAR.md); the band is carried now.

No lift field, no ground partition beyond the proven level-cut hole, no stitch
passes -- the ground-junction synthesis's complete causal model says all three
owner-named defect classes are that machinery's artifacts, so this build is its
deletion. If hill/seams/tiles recur here, the model itself is refuted (registered).

Regenerate: py -X utf8 band_seat.py  (offline gates + renders; --apply to deploy)
"""
from terrace_wall_strip import *                            # noqa: F401,F403 -- the shared, proven module
from terrace_wall_strip import kk, OUTD, DECODE, ANATOMY    # noqa: F401 -- explicit for clarity

DONOR_BLK = (15, 14)
SEAT_CLEAR = 0.05                                           # min clearance of the cut above the highest weld vert
BAND_H = 3.7                                                # the donor band course's height (rim study R5)
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

    # ---- THE MESA EXTRACTION (verbatim: wall ring + ring-1 + enclosed plateau) -------------
    W = extract_wall(*DONOR_BLK)
    topoD, tidD = W["topo"], W["tri_idx"]
    VD, UD, ND, TD = W["V"], W["U"], W["N"], W["T"]
    comp_count = Counter(W["comp_of"].values())
    root = comp_count.most_common(1)[0][0]
    mesa = {t for t, r in W["comp_of"].items() if r == root}
    ring1 = set()
    crest_e = []
    for e, ts in W["edge_tris"].items():
        if len(ts) != 2:
            continue
        w = [t for t in ts if t in mesa]
        p = [t for t in ts if topoD[t] in PLATEAU_T]
        if len(w) == 1 and len(p) == 1:
            ring1.add(p[0])
            crest_e.append(e)
    padj = defaultdict(set)
    for e, ts in W["edge_tris"].items():
        pp = [t for t in ts if topoD[t] in PLATEAU_T]
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
    print(f"mesa: {len(mesa)} wall tris + {len(ring1)} ring-1 + "
          f"{len(plat) - len(ring1)} interior plateau tris carried (blk {DONOR_BLK})")

    # ---- pose + seat (lattice-group; BURY the sloped donor seat below the cut plane) -------
    bnd_y = []
    for e, ts in W["edge_tris"].items():
        w = [t for t in ts if t in carry]
        o = [t for t in ts if t not in carry]
        if len(w) == 1 and o:
            bnd_y.extend((e[0][1], e[1][1]))
    wy = sorted({round(y, 3) for y in bnd_y})
    y_weld_max = max(wy)
    w_p10 = float(np.percentile(wy, 10))
    # THE BAND SEAT (the round's one lever): deepest bound keeps every column's wall
    # reaching the cut plane; shallowest keeps the cut inside the p10 column's band
    dy = max(LOWLAND - y_weld_max - SEAT_CLEAR, LOWLAND - w_p10 - BAND_H)
    n_band_cols = sum(1 for y in wy if y + dy + BAND_H >= LOWLAND - 1e-6
                      and y + dy <= LOWLAND + 1e-6)
    cvx = [VD[i][0] + W["ox"] for t in carry for i in tidD[t]]
    cvz = [VD[i][2] + W["oz"] for t in carry for i in tidD[t]]
    tx = CELL * round((CENTER[0] - (min(cvx) + max(cvx)) / 2.0) / CELL)
    tz = CELL * round((CENTER[1] - (min(cvz) + max(cvz)) / 2.0) / CELL)
    print(f"pose: yaw 0, translate ({tx:+.0f}, {tz:+.0f}) [4u lattice], seat dy "
          f"{dy:+.2f} (BAND SEAT: weld y {min(wy):.2f}..{y_weld_max:.2f} p10 "
          f"{w_p10:.2f}; cut inside the band course for {n_band_cols}/{len(wy)} "
          f"weld verts)")

    wall = []
    for t in sorted(carry):
        idx = tidD[t]
        rec = []
        for i in idx:
            w3 = (VD[i][0] + W["ox"] + tx, VD[i][1] + dy, VD[i][2] + W["oz"] + tz)
            rec.append((w3, tuple(UD[i]), tuple(ND[i]), tuple(TD[i])))
        wall.append(rec)
    crest = sorted({(round(p[0] + W["ox"] + tx, 3), round(p[1] + dy, 3),
                     round(p[2] + W["oz"] + tz, 3))
                    for e in crest_e for p in e})
    top_y = max(r[0][1] for rec in wall for r in [rec[0], rec[1], rec[2]])
    print(f"carry: {len(wall)} tris, crest ring {len(crest)} verts at bench y "
          f"~{float(np.median([p[1] for p in crest])):.1f}, top {top_y:.1f}")

    # strip-machinery placeholders: nothing is composed, welded, or minted up top --
    # the spliced pipeline's strip-specific gates see benign empties
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
            # fan from an ORIGINAL corner: single hit -> the OPPOSITE corner (all-real
            # tris); multi-hit -> the corner SHARED by the hit edges (its slivers are
            # zero-area but TOPOLOGICALLY exact -- every sub-edge pairs with the
            # neighbour's; an ear fan instead chooses among zero-area ears by noise
            # and mints chord-skipping slivers, the measured once-edge factory)
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


    # ---- THE FOOT (the foot law): level cut at the ground plane -- no burial, no pierce ----
    # Stock walls terminate ON the ground mesh (junction study J3: 96.7% bottom weld,
    # ground level and plain to the weld; no pierce exists). The posed wall is cut at
    # y = LOWLAND; crossings are computed once per EDGE (sorted endpoints) so neighbours
    # split bit-exact; everything below the plane is DISCARDED.
    xcache = {}

    def _crossing(A, B):
        ka, kb2 = kk(A[0]), kk(B[0])
        key = (ka, kb2) if ka <= kb2 else (kb2, ka)
        got = xcache.get(key)
        if got is None:
            P0, P1 = (A, B) if ka <= kb2 else (B, A)
            t = (LOWLAND - P0[0][1]) / (P1[0][1] - P0[0][1])
            p = (P0[0][0] + t * (P1[0][0] - P0[0][0]), LOWLAND,
                 P0[0][2] + t * (P1[0][2] - P0[0][2]))
            uv = tuple(P0[1][q2] + t * (P1[1][q2] - P0[1][q2]) for q2 in range(2))
            n3 = tuple(P0[2][q2] + t * (P1[2][q2] - P0[2][q2]) for q2 in range(3))
            got = (p, uv, n3, P0[3])
            xcache[key] = got
        return got

    lev_wall = []
    for rec in wall:
        ys2 = [r[0][1] for r in rec]
        if min(ys2) >= LOWLAND:
            lev_wall.append(rec)
            continue
        if max(ys2) <= LOWLAND:
            continue
        poly = []
        for k3 in range(3):
            A, B = rec[k3], rec[(k3 + 1) % 3]
            if A[0][1] >= LOWLAND:
                poly.append(A)
            if (A[0][1] - LOWLAND) * (B[0][1] - LOWLAND) < 0:
                poly.append(_crossing(A, B))
        if len(poly) < 3:
            continue
        for q2 in range(1, len(poly) - 1):
            lev_wall.append([poly[0], poly[q2], poly[q2 + 1]])
    print(f"level cut at y={LOWLAND}: {len(wall)} -> {len(lev_wall)} wall tris "
          f"(sub-ground mesh discarded)")
    wall = lev_wall

    # ---- the foot polyline -> chord simplification -> THE RIM (the weld line itself) -------
    # The cut's at-plane once-edges chain into the foot loops. Each loop is simplified to
    # chords (every original vert within SIMPLIFY_TOL of its chord) and the intermediate
    # wall verts SNAP onto the chord, so the wall's foot edges lie EXACTLY along the rim
    # lines the ground is sliced with -- the precondition for a shared-vertex weld.
    fcnt = Counter()
    fmap = {}
    for rec in wall:
        ps = [r[0] for r in rec]
        for a2, b2 in ((0, 1), (1, 2), (2, 0)):
            pa, pb = ps[a2], ps[b2]
            if abs(pa[1] - LOWLAND) < 1e-6 and abs(pb[1] - LOWLAND) < 1e-6:
                e = tuple(sorted((kk(pa), kk(pb))))
                if e[0] != e[1]:
                    fcnt[e] += 1
                    fmap[e] = (pa, pb)
    padj2 = defaultdict(list)
    pexact = {}
    for e, n2 in fcnt.items():
        if n2 != 1:
            continue
        pa, pb = fmap[e]
        pexact[kk(pa)] = pa
        pexact[kk(pb)] = pb
        padj2[kk(pa)].append(kk(pb))
        padj2[kk(pb)].append(kk(pa))
    deg_odd = [p for p, l3 in padj2.items() if len(l3) != 2]
    if deg_odd:
        n_multi = sum(1 for e, n2 in fcnt.items() if n2 > 1)
        print(f"   DBG foot edges: {len(fcnt)} total, {n_multi} multi-count (excluded)")
        for e, n2 in fcnt.items():
            if n2 > 1:
                print(f"      multi x{n2}: {e}")
        for p in deg_odd[:8]:
            print(f"   DBG foot degree-{len(padj2[p])} at {p}: nbrs {padj2[p][:4]}")
            for rec in wall:
                ps2 = [r[0] for r in rec]
                if any(kk(q2) == p for q2 in ps2):
                    print(f"      tri: {[kk(q2) for q2 in ps2]}")
    assert not deg_odd, (f"foot graph not 2-regular: {len(deg_odd)} odd-degree pts, "
                         f"e.g. {deg_odd[:3]}")
    floops = []
    fvisited = set()
    for start in list(padj2):
        if start in fvisited:
            continue
        loop = [start]
        prev = None
        while True:
            nxts = [p for p in padj2[loop[-1]] if p != prev]
            if not nxts or nxts[0] == start:
                break
            prev = loop[-1]
            loop.append(nxts[0])
        fvisited.update(loop)
        if len(loop) >= 3:
            floops.append([pexact[k3] for k3 in loop])
    floops.sort(key=len, reverse=True)
    assert floops, "no foot loop -- the wall does not reach the ground plane"

    def simplify_loop(loop3):
        """Greedy chord walk (deviation vs the ORIGINAL polyline bounded by
        SIMPLIFY_TOL). Returns (chords, snap): chords = (cornerA, cornerB, [snapped
        intermediate wall verts in order]); snap = kk(old) -> new on-chord position."""
        n2 = len(loop3)
        pts3 = loop3 + [loop3[0]]

        def dev_ok(i3, j3):
            a, b2 = pts3[i3], pts3[j3]
            dx, dz = b2[0] - a[0], b2[2] - a[2]
            L2 = dx * dx + dz * dz
            if L2 < 1e-12:
                return False
            for q2 in range(i3 + 1, j3):
                p = pts3[q2]
                t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[2] - a[2]) * dz) / L2))
                if math.hypot(p[0] - (a[0] + t * dx),
                              p[2] - (a[2] + t * dz)) > SIMPLIFY_TOL:
                    return False
            return True

        corners = [0]
        i3 = 0
        while i3 < n2:
            j3 = i3 + 1
            while j3 < n2 and dev_ok(i3, j3 + 1):
                j3 += 1
            corners.append(j3)
            i3 = j3
        if corners[-1] != n2:
            corners.append(n2)
        snap = {}
        chords = []
        for c0, c1 in zip(corners, corners[1:]):
            a, b2 = pts3[c0], pts3[c1]
            dx, dz = b2[0] - a[0], b2[2] - a[2]
            L2 = (dx * dx + dz * dz) or 1.0
            mids = []
            for q2 in range(c0 + 1, c1):
                p = pts3[q2]
                t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[2] - a[2]) * dz) / L2))
                np_ = (a[0] + t * dx, LOWLAND, a[2] + t * dz)
                snap[kk(p)] = np_
                mids.append(np_)
            chords.append(((a[0], LOWLAND, a[2]), (b2[0], LOWLAND, b2[2]), mids))
        return chords, snap

    all_chords = []
    snap_all = {}
    loop_polys = []
    for l3 in floops:
        chords, snap = simplify_loop(l3)
        all_chords.extend(chords)
        snap_all.update(snap)
        loop_polys.append([(c[0][0], c[0][2]) for c in chords])
    if snap_all:
        wall = [[(snap_all.get(kk(w), (w[0], LOWLAND, w[2]) if abs(w[1] - LOWLAND) < 1e-6
                               else w), uv, n3, t4) for (w, uv, n3, t4) in rec]
                for rec in wall]
    outer_poly = loop_polys[0]
    sec_polys = loop_polys[1:]
    print(f"rim: outer {len(outer_poly)} chords (from {len(floops[0])} foot verts), "
          f"{len(sec_polys)} secondary loop(s) {[len(p2) for p2 in sec_polys]} "
          f"(ledge dips: ground patches inside, welded); {len(snap_all)} verts snapped "
          f"<= {SIMPLIFY_TOL}u")

    # ---- the ground: the rim IS the foot polyline -- exact cut of the bench grass ----------
    # Round 5 inset a hidden rim 1.5u INSIDE the face (burial pierce). The foot law
    # replaces it: the ground partition's hole rim is the chord-simplified foot polyline
    # itself, and after the per-chord union refinement below, the wall's foot edges and
    # the ground's rim edges are the SAME edges -- a true weld, zero hidden geometry.

    # exact cut: general-line slices with crossings computed once per (line, edge)
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
            return True                                     # a ledge-dip ground patch
        return not pinp(cx3, cz3, outer_poly)
    for ti, t in enumerate(tris):
        if t["topo"] not in GRASS_TOPO:
            grass_keep.append(ti)
            continue
        d0 = math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
        if d0 > rim_r_max + 8.0:
            grass_keep.append(ti)
            continue
        # EVERY zone tri goes through the SAME slice pipeline -- an all-inside "drop
        # whole" shortcut loses the bay portions where the rim polygon crosses a tri
        # edge twice (both endpoints inside), and any per-tri shortcut gives neighbours
        # different subdivisions -> T-junctions. Distant lines leave a polygon intact.
        pieces = [[(p[0], p[2]) for p in t["w"]]]
        for (o, dvec) in rim_lines:
            nxt = []
            for pg in pieces:
                pos_, neg_ = slice_line(pg, o, dvec)
                for part in (pos_, neg_):
                    # keep SLIVERS: an area filter drops them on one side of a shared
                    # edge only, unpairing every neighbour (T1's 92-edge apron failure)
                    if len(part) >= 3 and poly_area2(part) > 1e-14:
                        nxt.append(part)
            pieces = nxt
        kept_pieces = [pg for pg in pieces if keep_pg(pg)]
        if len(pieces) == 1 and kept_pieces:
            grass_keep.append(ti)                           # untouched: no line crossed it
        else:
            # subdivided (even if fully kept): emit the pieces, so shared-edge crossings
            # stay consistent with the neighbours' subdivisions
            grass_cut.append((ti, kept_pieces))
            dropped += 0 if kept_pieces else 1
    print(f"ground: {dropped} grass tris dropped inside the rim, {len(grass_cut)} cut, "
          f"{len(grass_keep)} untouched")

    # ---- THE RIM WELD: wall foot edges and ground rim edges become the SAME edges ----------
    # Per chord, the vert chain differs by side: the wall has {corners + snapped foot
    # verts}, the ground has {corners + slice crossings}. Take the UNION as canonical:
    # ground verts within 2e-3 of a wall point CANONICALIZE to it (gsnap, applied to the
    # pieces so every fragment sharing the vert agrees); ground-only points refine the
    # wall's foot tris; wall-only points are inserted into the pieces' rim edges at
    # emission. Both sides then emit identical (kk) edges -- matched, not declared.
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
                        chord_pts[ci2].append((t, (q2[0], LOWLAND, q2[1])))
                        n_gadd += 1
                    break
    for ci2 in range(len(chord_pts)):
        chord_pts[ci2].sort()
    if gsnap:
        grass_cut = [(ti, [[gsnap.get((round(q2[0], 4), round(q2[1], 4)), q2)
                            for q2 in pg] for pg in pieces])
                     for ti, pieces in grass_cut]
    # ground-only chord points refine the WALL's foot tris (edge-lerped attrs)
    foot_refine = defaultdict(list)
    for ci2, c in enumerate(all_chords):
        wall_chain = [(0.0, c[0])] + [(chord_param(c, (m2[0], m2[2])), m2)
                                      for m2 in c[2]] + [(1.0, c[1])]
        for (t0, p0), (t1, p1) in zip(wall_chain, wall_chain[1:]):
            mids2 = [p for (t2, p) in chord_pts[ci2] if t0 + 1e-9 < t2 < t1 - 1e-9]
            if mids2:
                ek = tuple(sorted((kk(p0), kk(p1))))
                foot_refine[ek].extend(mids2)
    wall, n_foot_split = refine_wall(wall, foot_refine)
    print(f"rim weld: {len(gsnap)} ground verts canonicalized to wall points, "
          f"{n_gadd} ground crossings added to chords, {n_foot_split} wall foot splits")

    # ---- THE CARRIED BAND (no retile -- the band-seat's whole point) -----------------------
    # The cut course wears whatever the donor's own columns wear at the cut height;
    # with the band seat that is the row-10/11 transition course for ~90% of columns
    # and the row above for the low-weld tail (stock's own intermittency). The
    # arclength-stationed fringe re-mint that stood here is the falsified lane
    # (BASE-TILE-GRAMMAR.md: the band is the column's own uv continuation, zero
    # freedom). Report + gate the coverage from the BUILT bytes.
    pu_ph, pv_ph = json.loads(DECODE.read_text())["phase"]
    band_rows = Counter()
    for rec in wall:
        ys3 = [r[0][1] for r in rec]
        if abs(min(ys3) - LOWLAND) > 1e-6:
            continue                                        # not a cut-course tri
        vmin = min(r[1][1] for r in rec)
        band_rows[int(math.floor((vmin - pv_ph) / TILE_V + 0.5))] += 1
    n_cut = sum(band_rows.values())
    band_share = (band_rows.get(10, 0) + band_rows.get(11, 0)) / max(1, n_cut)
    print(f"carried band: cut-course rows {band_rows.most_common(6)} -> band(10+11) "
          f"share {band_share:.0%} of {n_cut} (predict ~80%; gate >=60%)")


    def enrich_rim_edges(pg):
        """Insert the chords' union points into any piece edge lying on a chord, so the
        piece's rim edges match the wall's refined foot edges vert for vert."""
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

    # enrich BEFORE kept conformance, so the conformance vocabulary (frag_verts2) sees
    # the rim union verts -- and add the union points themselves: a KEPT tri whose edge
    # lies along a chord must split at them (the hole-side fragment that would have
    # carried them was dropped)
    grass_cut = [(ti, [enrich_rim_edges(pg) for pg in pieces])
                 for ti, pieces in grass_cut]
    # the cut's crossing points, or the rim cut mints T-junctions against it (the exact
    # failure class the T1 apron partition hit; here the geometry is flat and two-party,
    # so the split is geometry-neutral).
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
        # conformance covers grass AND the coast-nav stamp classes (53-56): a stamped or
        # sloped tri neighbouring zone grass must still split at shared crossings. +16,
        # NOT +9: the mint's coast-fan tris are large and irregular.
        if t["topo"] not in (GRASS_TOPO | {53, 54, 55, 56}) or d0 > rim_r_max + 16.0:
            kept_out.append((t["w"], t["uv"], t["n"], t["tan"], t["blk"]))
            continue
        pg = []
        inserted = False
        for k3 in range(3):
            a, b = t["w"][k3], t["w"][(k3 + 1) % 3]
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
                p3 = (p2[0], a[1] + tt * (b[1] - a[1]), p2[1])  # edge-lerped y (slopes!)
                pg.append((p3, affine_attr(t, p2, "uv"), affine_attr(t, p2, "n"),
                           affine_attr(t, p2, "tan")))
                inserted = True
                n_kept_split += 1
        if not inserted:
            kept_out.append((t["w"], t["uv"], t["n"], t["tan"], t["blk"]))
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
    print(f"kept conformance: {n_kept_split} edge splits on kept grass")

    # ---- L3 for the top (T1 verbatim: seeded from the bench's own kept grass) --------------
    sys.path.insert(0, str(ROOT / "studies" / "overworld-topography"))
    import uvf_fix2 as UF                                   # noqa: E402

    def tri_cell(t3):
        """FLOOR-z cells: mains_uv computes fz = (z - 4j)/4, so j = floor(z/4) (negative
        south of origin). The negated int(-z//4) convention fed it fz ~ -256 -> clamp ->
        every u collapsed (THE ROUND-3 'BANDED TOP', root-caused offline: decode rate
        0/354 with the negated key, 59/60 with this one)."""
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

    # cut grass pieces take their UVs AFFINELY from the parent tri -- the exact
    # continuation of the cell's own mapping, no window decode needed, no stretch
    cut_out = []
    for ti, pieces in grass_cut:
        t = tris[ti]
        for pg in pieces:
            for tt in centroid_fan(pg):
                t3 = [(q[0], LOWLAND, q[1]) for q in tt]
                a, b, c = (np.array(p) for p in t3)
                if np.cross(b - a, c - a)[1] < 0:
                    t3 = [t3[0], t3[2], t3[1]]
                uvt = [affine_attr(t, (p[0], p[2]), "uv") for p in t3]
                cut_out.append((t3, uvt, t))
    print(f"ground cut fragments: {len(cut_out)} tris re-emitted (parent-affine UVs)")

    # ---- THE GLOBAL T-CONFORMANCE SWEEP (fixpoint) -----------------------------------------
    # The per-interface conformance passes (top T-splits, crest weld, rim weld, kept
    # conformance) each cover one seam of the composition; the residue is CROSS-
    # interface T-junctions (rim corner wedges, crest micro-splinters, block-border
    # slices). One absolute-tolerance sweep subsumes them all: every tri edge carrying
    # another OUTPUT vert in its interior splits at that vert -- exact positions only,
    # no new geometry -- iterated to fixpoint. Anything still open after this is a REAL
    # hole and gates red.
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
        # a notch dart is too THIN for its own centroid-containment test -- proximity
        # to any patch vert is the reliable membership predicate
        if any(pinp(cx3, cz3, np_) for np_ in notch_polys):
            return True
        return any(math.hypot(cx3 - p[0], cz3 - p[2]) < 2.0
                   for pt in notch_patches for p in pt)

    n_chute = 0
    for t3, uvt in top_out:
        cx3 = float(np.mean([p[0] for p in t3]))
        cz3 = float(np.mean([p[2] for p in t3]))
        # a notch chute stays GRASS to the eye but ROCK to the feet: the playtest
        # walked a 5u near-vertical fan tri because it carried the shelf topograph
        tid = ID_SHELF
        nrm_t = (0.0, 1.0, 0.0)
        if near_notch(cx3, cz3):
            tid = ID_ROCK
            n_chute += 1
            a3n, b3n, c3n = (np.array(p) for p in t3)
            fn3 = np.cross(b3n - a3n, c3n - a3n)
            L3n = float(np.linalg.norm(fn3))
            if L3n > 1e-9:                                  # a chute lights by its slope
                nrm_t = tuple(float(v) / L3n for v in fn3)
        final.append(([(tuple(t3[k3]), tuple(uvt[k3]), nrm_t,
                        (tid, 0.0, 0.0, 1.0)) for k3 in range(3)], None))
    if n_chute:
        print(f"   notch chutes: {n_chute} top tris carry ROCK topograph (unwalkable)")

    # THE MICRO-WELD: any two output verts within 0.05 collapse to one canonical
    # position (bench-original wins, then a crest vert, then the smallest key) -- the
    # splinter-pair class (two interfaces each minting "the same" point) dies here
    # wholesale. The radius must stay BELOW the sweep net (0.065): pairs between the
    # two radii are consumed by the sweep as T-splits instead. (A 0.08 weld forced a
    # 0.1 net, and a 0.1 net CRAWLS -- each bend-split lands new sub-edges within net
    # range of further verts; the cascade ran 61 -> 1669 splits without converging.)
    bench_verts = {kk(p) for t3, _, _, _, _ in kept_out for p in t3}
    crest_keys = {kk(p) for p in crest}
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

    # SINGLE PASS: iterating the sweep measurably cascades (each pass's bend-splits and
    # sliver fans mint new near-edge geometry for the next; 48 -> 1081 splits by pass
    # 7). Pass 0 alone takes the safe majority of true T-junctions; the residue is
    # gated against STOCK'S OWN once-edge rate below, not against an aspiration stock
    # itself does not meet (junction study J1/J3: stock boundaries are 3-7% open).
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
            # the CREST-BAND net (0.065) EXCEEDS the micro-weld radius (0.05): pairs
            # the weld leaves behind are consumed here as T-splits. Splitting bends
            # the edge through an existing vert, deterministically on both sides --
            # invisible at game scale (~1 texel). A wider net (0.1) measurably CRAWLS
            # (each bend lands new sub-edges near further verts; 61 -> 1669 splits).
            # The GROUND plane keeps the exact 2e-3.
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
    # the weld gate: displacement bounded by the corner warp (a kink k rotates the ~12u
    # batter lean by 2*12*sin(k/2)) plus profile spread -- beyond it the taper visibly
    # shears the outgoing strip's terminal station
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
    for i, (n_ok, n_bad, bad) in enumerate(seam_report):
        if n_bad > n_ok:
            fails.append(f"seam {i}: h_pairs mostly unlawful ({n_bad} vs {n_ok}) {bad}")

    # THE RIM GATES (RIM-AWARE-PREDICTION.md): displacement envelope vs stock's own
    # (med 0.80 / p99 2.41), sliver fraction vs stock's ring-1 (2.1%), zero home jumps
    if rim_gate_stats["disp_p50"] > 1.2:
        fails.append(f"rim: displacement p50 {rim_gate_stats['disp_p50']:.2f}u > 1.2u")
    if rim_gate_stats["disp_p99"] > 2.5:
        fails.append(f"rim: displacement p99 {rim_gate_stats['disp_p99']:.2f}u > 2.5u")
    if rim_gate_stats["sliver"] > 0.03:
        fails.append(f"rim: top-sheet sliver fraction {rim_gate_stats['sliver']:.1%} "
                     f"> 3% ({rim_gate_stats['n_sliver']} tris)")
    if rim_gate_stats["jumps"]:
        fails.append(f"rim: {rim_gate_stats['jumps']} home JUMPs on non-bridge crest "
                     f"edges (the inherited correspondence broke)")
    # THE BAND GATE, carried form (BAND-SEAT-PREDICTION.md): the seat must have put
    # the donor's own transition course on the visible bottom row
    if band_share < 0.60:
        fails.append(f"band: cut-course rows 10+11 share {band_share:.0%} < 60% -- "
                     f"the seat missed the band course")

    def outward_of(px, pz):
        d = (px - CENTER[0], pz - CENTER[1])
        L = math.hypot(*d) or 1.0
        return (d[0] / L, d[1] / L)

    # wall winding: a tri must agree with its OWN CARRIED vertex normals -- the donor's
    # reentrant relief (gully flanks, ledge undersides) legitimately faces inward or
    # down relative to the ring, so the round-5 radial test false-alarms on real rock;
    # what it must catch is a FLIP (geometry opposing the normals the donor shipped)
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
            fails.append(f"winding: a wall tri OPPOSES its carried normals at "
                         f"{kk(t3[0])} (area {L / 2:.3f}u2, verts {[kk(p) for p in t3]})")
    def near_notch(cx3, cz3):
        # a notch dart is too THIN for its own centroid-containment test -- proximity
        # to any patch vert is the reliable membership predicate
        if any(pinp(cx3, cz3, np_) for np_ in notch_polys):
            return True
        return any(math.hypot(cx3 - p[0], cz3 - p[2]) < 2.0
                   for pt in notch_patches for p in pt)

    for t3, _ in top_out:
        cx3 = float(np.mean([p[0] for p in t3]))
        cz3 = float(np.mean([p[2] for p in t3]))
        if near_notch(cx3, cz3):
            continue                                        # a chute DRAPES; it may lean
        a, b, c = (np.array(p) for p in t3)
        fn = np.cross(b - a, c - a)
        if fn[1] < 0 and float(np.linalg.norm(fn)) > 2e-2:
            fails.append(f"winding: a top tri faces DOWN at {kk(t3[0])}")
    print(f"winding: {n_degen} near-degenerate wall tris exempt")

    # watertight: kept + cut + wall + top; allowed once-edges = rim lines + sub-ground
    cnt3 = defaultdict(int)

    def _acc(t3):
        ps = [kk(p) for p in t3]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt3[tuple(sorted((ps[a], ps[b])))] += 1
    pre_once = set()
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

    # ZERO declared classes (the registration): every once-edge that is not one of the
    # bench's own pre-existing block borders is a BUG -- no hole rim, no buried skirt,
    # no mortar zone, no sliver capper. Full closure or red.
    grew_bad = [e for e in grew if not degen(e)]
    n_dg = sum(1 for e in grew if degen(e))
    n_all_edges = len(cnt3)
    rate = len(grew_bad) / max(1, n_all_edges)
    print(f"watertight: {len(grew)} new once-edges = {n_dg} degenerate + "
          f"{len(grew_bad)} residual of {n_all_edges} edges ({rate:.4%}; STOCK's own "
          f"measured open rate is 2.8-6.8%)")
    # the gate is STOCK'S OWN standard (junction study J1/J3), not zero: residuals must
    # stay two orders below stock's open rate, each short, and the culled game-eye
    # renders are the visibility check reviewed before any deploy
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
        for e in grew_bad:
            own = set(edge_owner.get(e, ["?"]))
            if own & {"wall", "top"}:
                da = min((math.dist(e[0], c2) for c2 in crest), default=99)
                db2 = min((math.dist(e[1], c2) for c2 in crest), default=99)
                print(f"   crest-area BAD {sorted(own)} {e} inA={e[0] in crest_set} "
                      f"inB={e[1] in crest_set} dA={da:.3f} dB={db2:.3f}")
        for e in grew_bad[:6]:
            print(f"   BAD {edge_owner.get(e, ['?'])} {e}")
        # targeted forensics: the FINAL tris touching each bad edge's endpoints
        for e0 in grew_bad[:4]:
            print(f"   FORENSICS edge {e0}:")
            for rec, _blk in final:
                ks3 = [kk(r[0]) for r in rec]
                if e0[0] in ks3 or e0[1] in ks3:
                    print(f"     tri: {ks3}")

    if args.probe:
        for (qx3, qz3, tag3) in ((402.0, -494.0, "notch gap"),
                                 (425.0, -518.0, "jutting flake"),
                                 (442.0, -512.0, "foot fringe")):
            print(f"   PROBE {tag3} ({qx3}, {qz3}):")
            for rec, _blk in final:
                cx3 = float(np.mean([r[0][0] for r in rec]))
                cz3 = float(np.mean([r[0][2] for r in rec]))
                cy3 = float(np.mean([r[0][1] for r in rec]))
                if math.hypot(cx3 - qx3, cz3 - qz3) < 2.5 and cy3 > 10.0:
                    print(f"     {[kk(r[0]) for r in rec]}")

    # massing gates on the composed ground line (the visible foot = the outer foot loop)
    fl0 = [(p[0], p[2]) for p in floops[0]]
    fturn = [signed_turn(fl0[(i2 - 1) % len(fl0)], fl0[i2],
                         fl0[(i2 + 1) % len(fl0)])
             for i2 in range(len(fl0))]
    fabs = [abs(a2) for a2 in fturn]
    med_t = float(np.median(fabs))
    n_right = sum(1 for a2 in fabs if 80 <= a2 <= 100)
    if med_t > 30.0 or n_right > len(fabs) * 0.03:
        fails.append(f"massing: ground line med turn {med_t:.1f} deg / {n_right} right angles")
    print(f"massing: ground-line turn med {med_t:.1f} deg, right angles {n_right}"
          f"/{len(fabs)}")

    # bench reach: the ring (all of it visible now) needs a flat annulus before the coast
    reach_vis = max(math.hypot(r[0][0] - CENTER[0], r[0][2] - CENTER[1])
                    for rec in wall for r in rec)
    need_r = reach_vis + 6.0
    print(f"reach: {reach_vis:.1f}u -> island radius needed ~{need_r:.0f}u "
          f"(bench grass ~{grass_r:.1f}u)")
    if grass_r < need_r - 2.0:
        fails.append(f"bench too small: re-mint the island at radius "
                     f"{math.ceil(need_r - 2.5)} (same center, same six blocks)")

    # ---- assemble (from the swept FINAL list -- audit and emit see the same tris) ----------
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
        print("\nSTRIP: GATES RED -- not deployable")
        return 1
    if not args.apply:
        print("\nSTRIP: gates green (offline). Review the renders; --apply to deploy.")
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
