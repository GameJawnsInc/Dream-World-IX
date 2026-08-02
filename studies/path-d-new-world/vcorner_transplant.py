"""THE VERBATIM COAST-SEGMENT TRANSPLANT — census + cut/seat/weld (stage-gated).

Registration: SEGMENT-TRANSPLANT-PREDICTION.md (read first). Stage 1 = census
(P-A): find stock shore windows matching the bench corner's proven fairing arc
(convex ~43 deg over ~8.25u chord, wall height ~3.2u, coastal free base).

  py vcorner_transplant.py census
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402

# the bench target (banked, SEGMENT-TRANSPLANT-PREDICTION.md)
V5 = (376.29, -509.40)
V11 = (380.08, -516.73)
CHORD = math.hypot(V11[0] - V5[0], V11[1] - V5[1])          # ~8.25
TURN_LO, TURN_HI = 35.0, 52.0
CHORD_LO, CHORD_HI = 7.5, 11.0
H_LO, H_HI = 2.4, 4.0
FAN_MAX = 67.5                                              # THE QUANTIZED-FAN LAW
COUNTER_MAX = 10.0

# donor pool: ALL real disc-1 blocks (the flow constraint prunes hard; family gates)
def _pool():
    return X.list_blocks(disc=1)


# THE FLOW CONSTRAINT (the seat-1 lesson): after chord-seating onto the bench
# (chord heading 152.65 deg), EVERY segment heading must be >= 135 deg so both
# hug holds (202.5 south / 22.5 north on the reversed tangent) stay within the
# 67.5 deg quantized-fan bound. The fairing's 138 chord was exactly this + 3.
BENCH_CHORD_H = math.degrees(math.atan2(380.08 - 376.29, -516.73 + 509.40))
SEATED_MIN_H = 135.05


def block_tris(bx, by):
    """Stock disc-1 Terrain tris in WORLD frame: (a,b,c, mapid, topo) + uvs."""
    bm = X.read_block(bx, by, disc=1, part="terrain")
    ox, oz = X.block_world_origin(bx, by)
    pos = bm.chan_arrays[X.CH_POS]
    uv = bm.chan_arrays[X.CH_UV]
    tan = bm.chan_arrays[X.CH_TAN]
    tris = []
    for t in bm.tris:
        pts = [(pos[i][0] + ox, pos[i][1], pos[i][2] + oz) for i in t]
        mapid = int(round(tan[t[0]][0]))
        topo = (mapid & 0xFC) >> 2
        tris.append((pts, [tuple(uv[i][:2]) for i in t], mapid, topo, list(t)))
    return tris


def key(p):
    return (round(p[0], 3), round(p[2], 3))


def boundary_chains(tris):
    """Walkable-boundary chains (probe_vcorner_boundary pattern) + per-edge land
    side. Returns list of chains; chain = list of (key, y, land_left bool)."""
    walk = [(i, t) for i, t in enumerate(tris) if t[3] in W.WALK_OK]
    edge_use = defaultdict(list)
    yof = {}
    for i, t in walk:
        ks = [key(p) for p in t[0]]
        for j, p in enumerate(t[0]):
            yof[ks[j]] = p[1]
        cen = (sum(p[0] for p in t[0]) / 3, sum(p[2] for p in t[0]) / 3)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_use[tuple(sorted((ks[a], ks[b])))].append((ks[a], ks[b], cen))
    nxt = defaultdict(list)
    landcen = {}
    for e, uses in edge_use.items():
        if len(uses) != 1:
            continue
        ka, kb, cen = uses[0]
        nxt[ka].append(kb)
        nxt[kb].append(ka)
        landcen[e] = cen
    seen, chains = set(), []
    for start in [p for p, ns in nxt.items() if len(ns) == 1] + list(nxt):
        if start in seen:
            continue
        chain, cur = [start], start
        seen.add(start)
        while True:
            cand = [q for q in nxt[cur] if q not in seen]
            if not cand:
                break
            cur = cand[0]
            seen.add(cur)
            chain.append(cur)
        if len(chain) > 3:
            chains.append(chain)
    return chains, landcen, yof


def signed_turns(chain):
    """Per-interior-vertex turn (deg, + = right/clockwise in compass heading)."""
    out = []
    for i in range(1, len(chain) - 1):
        d0 = (chain[i][0] - chain[i - 1][0], chain[i][1] - chain[i - 1][1])
        d1 = (chain[i + 1][0] - chain[i][0], chain[i + 1][1] - chain[i][1])
        a0 = math.atan2(d0[0], d0[1])
        a1 = math.atan2(d1[0], d1[1])
        out.append(math.degrees((a1 - a0 + math.pi) % (2 * math.pi) - math.pi))
    return out


def land_sign(chain, landcen):
    """+1 if land lies LEFT of traversal (bench convention), else -1; majority."""
    votes = 0
    for i in range(len(chain) - 1):
        e = tuple(sorted((chain[i], chain[i + 1])))
        if e not in landcen:
            continue
        cx, cz = landcen[e]
        dx, dz = chain[i + 1][0] - chain[i][0], chain[i + 1][1] - chain[i][1]
        # left of (dx,dz) in XZ compass frame: cross = dz*(cx-x) - dx*(cz-z)
        cr = dz * (cx - chain[i][0]) - dx * (cz - chain[i][1])
        votes += 1 if cr > 0 else -1
    return 1 if votes >= 0 else -1


def wall_heights(tris, chain_keys, yof):
    """Per crest key: (drop height, min wall y, topo set, v range) of touching
    non-walk tris — the height AND look-family facts in one pass."""
    touch = defaultdict(list)
    meta = defaultdict(lambda: [set(), [], []])
    for t in tris:
        if t[3] in W.WALK_OK:
            continue
        ks = [key(p) for p in t[0]]
        for j, k in enumerate(ks):
            if k in chain_keys:
                touch[k].extend(p[1] for p in t[0])
                meta[k][0].add(t[3])
                meta[k][1].extend(v for (u, v) in t[1])
                meta[k][2].extend(u for (u, v) in t[1])
    out = {}
    for k in chain_keys:
        if touch[k]:
            out[k] = (yof[k] - min(touch[k]), min(touch[k]),
                      meta[k][0], (min(meta[k][1]), max(meta[k][1])),
                      (min(meta[k][2]), max(meta[k][2])))
    return out


def census():
    print(f"bench target: chord {CHORD:.2f}u, turn +43 deg convex (land LEFT), "
          f"crest ~3.2u\n")
    hits = []
    pool = _pool()
    print(f"pool: {len(pool)} real disc-1 blocks")
    for (bx, by) in pool:
        try:
            tris = block_tris(bx, by)
        except Exception:
            continue
        chains, landcen, yof = boundary_chains(tris)
        for ci, chain in enumerate(chains):
            ls = land_sign(chain, landcen)
            ch = chain if ls > 0 else list(reversed(chain))  # land LEFT, no mirror
            turns = signed_turns(ch)
            hts = wall_heights(tris, set(ch), yof)
            n = len(ch)
            for i in range(n - 2):
                cum = 0.0
                for j in range(i + 1, n - 1):
                    t = turns[j - 1]
                    if abs(t) > FAN_MAX or t < -COUNTER_MAX:
                        break
                    cum += t
                    if cum > TURN_HI + 4:
                        break
                    chord = math.hypot(ch[j + 1][0] - ch[i][0],
                                       ch[j + 1][1] - ch[i][1])
                    if chord > CHORD_HI:
                        break
                    if TURN_LO <= cum <= TURN_HI and CHORD_LO <= chord <= CHORD_HI:
                        seg = ch[i:j + 2]
                        hs = [hts[k][0] for k in seg if k in hts]
                        base = [hts[k][1] for k in seg if k in hts]
                        if len(hs) < len(seg) * 0.7:
                            continue
                        med = sorted(hs)[len(hs) // 2]
                        if not (H_LO <= med <= H_HI) or min(base) > 0.5:
                            continue
                        # look family: topo-58 lip walls in THE GRASS-TOP strip
                        # (v pins 0.8926/0.9229, u band [0.699,0.947] — the bench's)
                        topos = set().union(*(hts[k][2] for k in seg if k in hts))
                        vlo = min(hts[k][3][0] for k in seg if k in hts)
                        vhi = max(hts[k][3][1] for k in seg if k in hts)
                        ulo = min(hts[k][4][0] for k in seg if k in hts)
                        uhi = max(hts[k][4][1] for k in seg if k in hts)
                        if topos != {58} or not (0.888 <= vlo <= 0.899) \
                                or not (0.917 <= vhi <= 0.929) \
                                or ulo < 0.67 or uhi > 0.98:
                            continue
                        # THE FLOW CONSTRAINT: seated headings all >= 135 deg
                        ch_h = math.degrees(math.atan2(seg[-1][0] - seg[0][0],
                                                       seg[-1][1] - seg[0][1]))
                        hmin_seated = 999.0
                        ok = True
                        for q in range(len(seg) - 1):
                            hq = math.degrees(math.atan2(seg[q + 1][0] - seg[q][0],
                                                         seg[q + 1][1] - seg[q][1]))
                            hs2 = (hq - ch_h + BENCH_CHORD_H) % 360
                            hmin_seated = min(hmin_seated, hs2)
                            if not (SEATED_MIN_H <= hs2 <= 269.0):
                                ok = False
                                break
                        if not ok:
                            continue
                        hits.append(dict(blk=(bx, by), chain=ci, i0=i, i1=j + 1,
                                         nv=len(seg), cum=round(cum, 1),
                                         chord=round(chord, 2), hmed=round(med, 2),
                                         hmin=round(min(hs), 2), hmax=round(max(hs), 2),
                                         base=round(min(base), 2),
                                         minh=round(hmin_seated, 1),
                                         at=(round(seg[0][0], 1), round(seg[0][1], 1))))
    hits.sort(key=lambda h: (abs(h["cum"] - 42.9) + 2 * abs(h["chord"] - CHORD)
                             + 3 * abs(h["hmed"] - 3.2) - 0.5 * (h["minh"] - 135)))
    print(f"{len(hits)} qualifying windows (flow + family constrained)")
    for h in hits[:14]:
        print(f"   {h['blk']} chain{h['chain']} v{h['i0']}..v{h['i1']} at {h['at']}: "
              f"turn {h['cum']:+.1f} chord {h['chord']} h {h['hmed']} "
              f"[{h['hmin']}..{h['hmax']}] base {h['base']} nv {h['nv']} "
              f"minSeatedH {h['minh']}")
    return hits


# ================================================================ stage 2: the carry
# PICKS (census 3, ranked): tried in order until THE LEAN TEST passes — the wall
# must be render-seaward AND walk-visible (ny > 0.1) at once, i.e. NON-overhanging:
# an overhang goes walk-invisible when seaward-wound, and over CUT sea the probes
# past the crest total-MISS -> the hug catches ((5,14)'s cove wall proved it).
PICKS = [dict(blk=(5, 14), chain=1, i0=0, i1=2, hmed=3.31),
         dict(blk=(20, 16), chain=1, i0=3, i1=5, hmed=3.32),
         dict(blk=(17, 9), chain=0, i0=3, i1=5, hmed=2.71),
         dict(blk=(10, 18), chain=0, i0=1, i1=3, hmed=3.91),
         dict(blk=(21, 9), chain=0, i0=0, i1=3, hmed=3.54)]
PICK = PICKS[0]


class DonorReject(Exception):
    pass

import dataclasses                                          # noqa: E402
import json                                                 # noqa: E402
import shutil                                               # noqa: E402
from datetime import datetime                               # noqa: E402

from vcorner_crest import (hug, INNER, LAWN_Y, V_TOP, V_BOT,  # noqa: E402
                           U0, URATE, TAN_CLIFF, SEAM_Z, U_SEED,
                           lawn_affines, affine_for, clip_halfplane, fan,
                           BASELINE_T, CHANGED_BBOX, PIN)
from probe_vcorner_trap import static_map, drive_walkers    # noqa: E402
from probe_vcorner_latent import sweep, refine              # noqa: E402
from vcorner_sea_cut import treat_part, live_path           # noqa: E402
from ff9mapkit.world.extract import CH_POS, CH_NRM, CH_UV, CH_TAN  # noqa: E402

BLOCKS = [(5, 7), (5, 8)]
U_HI = 0.947
BENCH_V5, BENCH_V11 = INNER[0], INNER[6]
OUTD2 = HERE / "out" / "vcorner_transplant"
BACKUPS = Path(r"C:\gd\Dream-World-IX\backups")
# pre-cut originals (the sea-cut round's first backups) — the seam-fix rebuild base
PRISTINE_SEA = {(5, 7): BACKUPS / "Block[5][7] Sea4.ff9mesh.r7.20260802-020657",
                (5, 8): BACKUPS / "Block[5][8] Sea4.ff9mesh.r8.20260802-020657"}


def walkable_cover(world, x, z):
    """WALKABLE terrain covers plan (x,z) at/above the sea band."""
    bk = W.block_key(x, z)
    if bk not in world:
        return False
    terr = next((m for m in world[bk] if m["name"] == "Terrain"), None)
    if terr is None:
        return False
    for ti in terr["grid"].get((int(x // 4), int(z // 4)), ()):
        tri = terr["tris"][ti]
        if tri[4] not in W.WALK_OK:
            continue
        hy = W.bary_y(x, z, tri)
        if hy is not None and hy >= -0.05:
            return True
    return False


FRINGE = 1.2                                                # stock's under-lip lapping water


def eroded_cover(world, x, z):
    """The seam-fix cut predicate: delete sea only DEEP under walkable land —
    walkable cover ERODED by FRINGE. Keeps stock's FREE-BASE fringe (water
    lapping the wall base under the lip, ≤~1.2u inland of the crest), which a
    ring cache can never weaponize (a fringe answers a couple of headings, the
    trap needs all 32); the latent sweep + walkers + pin replay verify."""
    if not walkable_cover(world, x, z):
        return False
    for k in range(8):
        a = math.pi * k / 4.0
        if not walkable_cover(world, x + FRINGE * math.sin(a),
                              z + FRINGE * math.cos(a)):
            return False
    return True


def get_window():
    """Re-derive the picked donor window: (seg crest keys, wall tris, yof)."""
    tris = block_tris(*PICK["blk"])
    chains, landcen, yof = boundary_chains(tris)
    ch = chains[PICK["chain"]]
    if land_sign(ch, landcen) < 0:
        ch = list(reversed(ch))
    seg = ch[PICK["i0"]:PICK["i1"] + 1]
    segkeys = set(seg)
    allchain = set(ch)
    # ONLY faces strictly BETWEEN the end columns: every crest key the face
    # touches must be a window key (a foreign face shares one end key + a crest
    # key OUTSIDE the window — the seat-3 over-grab lesson)
    lvl = []
    for t in tris:
        if t[3] in W.WALK_OK:
            continue
        crestk = [key(p) for p in t[0] if key(p) in allchain]
        if crestk and all(k in segkeys for k in crestk):
            lvl.append(t)
    grow_keys = {key(p) for t in lvl for p in t[0] if p[1] < yof[seg[0]] - 0.3}
    for t in tris:
        if t[3] in W.WALK_OK or t in lvl:
            continue
        ks = [key(p) for p in t[0]]
        if any(k in allchain for k in ks):
            continue
        if sum(1 for k in ks if k in grow_keys) >= 2:
            cen = (sum(p[0] for p in t[0]) / 3, sum(p[2] for p in t[0]) / 3)
            d = min(math.hypot(cen[0] - s[0], cen[1] - s[1]) for s in seg)
            if d < 7.0:
                lvl.append(t)
    return seg, lvl, yof


def refine_inner():
    """THE NEVER-HAND-TYPE-GEOMETRY LAW: INNER is 2-decimal rounded (probe
    output). Recover the EXACT baseline vert for each point — the weld targets
    and zip chain must be byte-true or every joint seeds a near-miss crack."""
    pts = []
    for (px, pz) in INNER:
        best, bd = None, 0.06
        for (bx, by) in BLOCKS:
            d = W.M.read_ff9mesh(BASELINE_T[(bx, by)])
            ox, oz = 64.0 * bx, -64.0 * by
            for v in d["verts"]:
                w2 = (v[0] + ox, v[1], v[2] + oz)
                dd = math.hypot(w2[0] - px, w2[2] - pz)
                if dd < bd and abs(w2[1] - LAWN_Y) < 0.4:
                    best, bd = w2, dd
        assert best is not None, f"no baseline vert near INNER point ({px},{pz})"
        pts.append(best)
    return pts


def build():
    inner_x = refine_inner()
    inner2 = [(p[0], p[2]) for p in inner_x]                # exact plan chain
    global BENCH_V5, BENCH_V11
    BENCH_V5, BENCH_V11 = inner2[0], inner2[6]
    print("   INNER refined to exact bytes: v5 "
          f"({inner_x[0][0]:.4f},{inner_x[0][2]:.4f}) v11 "
          f"({inner_x[6][0]:.4f},{inner_x[6][2]:.4f})")
    seg, wall, yof = get_window()
    print(f"window: {len(seg)} crest verts, {len(wall)} wall tris")
    topos = Counter(t[3] for t in wall)
    us = [u for t in wall for (u, v) in t[1]]
    vs = [v for t in wall for (u, v) in t[1]]
    print(f"   wall topos {dict(topos)}  u [{min(us):.3f},{max(us):.3f}] "
          f"v [{min(vs):.3f},{max(vs):.3f}]")
    assert set(topos) <= {58}, "non-lip wall class in the cut — wrong family"
    assert min(us) > U0 - 0.03 and max(us) < U_HI + 0.03, "u outside the rock band"

    # ---- RIGID SEAT: donor chord -> bench chord (rotation + uniform scale) --------
    d0 = (seg[-1][0] - seg[0][0], seg[-1][1] - seg[0][1])
    d1 = (BENCH_V11[0] - BENCH_V5[0], BENCH_V11[1] - BENCH_V5[1])
    L0, L1 = math.hypot(*d0), math.hypot(*d1)
    s = L1 / L0
    th = math.atan2(d1[0], d1[1]) - math.atan2(d0[0], d0[1])
    ct, st = math.cos(th), math.sin(th)
    hmed = PICK["hmed"]
    ys = LAWN_Y / hmed
    print(f"   seat: rotate {math.degrees(th):+.1f} deg, plan scale {s:.4f}, "
          f"y scale {ys:.3f}")

    def plan(p):
        rx, rz = p[0] - seg[0][0], p[1] - seg[0][1]
        return (BENCH_V5[0] + s * (rx * ct + rz * st),
                BENCH_V5[1] + s * (-rx * st + rz * ct))

    crest_pts = [plan(k) for k in seg]
    crest_pts[0], crest_pts[-1] = BENCH_V5, BENCH_V11       # exact joints
    print("   seated crest: " + " -> ".join(f"({p[0]:.2f},{p[1]:.2f})" for p in crest_pts))
    for i in range(len(crest_pts) - 1):
        d = (crest_pts[i + 1][0] - crest_pts[i][0], crest_pts[i + 1][1] - crest_pts[i][1])
        print(f"      seg {math.hypot(*d):5.2f}u @ "
              f"{math.degrees(math.atan2(d[0], d[1])) % 360:6.1f} deg")

    # transform wall verts; snap crest-verts to the shared crest points
    def seat_vert(p):
        px, pz = plan((p[0], p[2]))
        py = p[1] * ys
        k = key(p)
        if k in set(seg):
            i = seg.index(k)
            return (crest_pts[i][0], LAWN_Y, crest_pts[i][1])
        return (px, py, pz)

    # u: VERBATIM (no translation). The donor window carries its own in-band
    # sawtooth incl. a column-boundary wrap (stock grammar); translating it
    # pushed texels out of the band (seat-2 lesson). Joint phase jumps vs the
    # kept wall: ~0.013 at v5 (kept exits 0.8579, segment enters 0.871) — tiny
    # vs stock's own 0.248 wrap jumps; the render gate judges the joints.
    entry_us = [u for t in wall for p, (u, v) in zip(t[0], t[1])
                if math.hypot(p[0] - seg[0][0], p[2] - seg[0][1]) < 0.6]
    du = 0.0
    print(f"   u VERBATIM (entry u {sorted(set(round(u, 3) for u in entry_us))}, "
          f"kept exit {U_SEED})")

    arc = [0.0]
    for i in range(len(crest_pts) - 1):
        arc.append(arc[-1] + math.hypot(crest_pts[i + 1][0] - crest_pts[i][0],
                                        crest_pts[i + 1][1] - crest_pts[i][1]))

    def col_of(cen):
        best, bd = 0, 1e9
        for i in range(len(crest_pts) - 1):
            mx = (crest_pts[i][0] + crest_pts[i + 1][0]) / 2
            mz = (crest_pts[i][1] + crest_pts[i + 1][1]) / 2
            d = math.hypot(cen[0] - mx, cen[1] - mz)
            if d < bd:
                best, bd = i, d
        return best

    cols = {}
    seated = []                                             # (tri3, uv3, nrm3, col)
    for t in wall:
        p3 = [seat_vert(p) for p in t[0]]
        cen = ((p3[0][0] + p3[1][0] + p3[2][0]) / 3, (p3[0][2] + p3[1][2] + p3[2][2]) / 3)
        c = col_of(cen)
        uv3 = [(u + du, v) for (u, v) in t[1]]
        cols.setdefault(c, []).append(len(seated))
        seated.append([p3, uv3, c])
    uall = [u for t3, uv3, _c in seated for (u, v) in uv3]
    assert min(uall) > U0 - 0.02 and max(uall) < U_HI + 0.02, \
        f"seated u outside the band [{min(uall):.3f},{max(uall):.3f}]"

    # WINDING: the carried wall must face the SEA (the game-eye probe read 7/8
    # inland after the seat). Deterministic per-tri seaward test; a rigid carry
    # must be unanimous — assert, then flip by vertex-order swap.
    flips = 0
    for rec in seated:
        p3 = rec[0]
        a3, b3, c3 = p3
        fn = ((b3[1] - a3[1]) * (c3[2] - a3[2]) - (b3[2] - a3[2]) * (c3[1] - a3[1]),
              (b3[2] - a3[2]) * (c3[0] - a3[0]) - (b3[0] - a3[0]) * (c3[2] - a3[2]),
              (b3[0] - a3[0]) * (c3[1] - a3[1]) - (b3[1] - a3[1]) * (c3[0] - a3[0]))
        cen = ((a3[0] + b3[0] + c3[0]) / 3, (a3[2] + b3[2] + c3[2]) / 3)
        c2 = col_of(cen)
        m0, m1 = crest_pts[c2], crest_pts[c2 + 1]
        dx, dz = m1[0] - m0[0], m1[1] - m0[1]
        sea = (dz, -dx)                                     # land LEFT => sea RIGHT of travel
        if fn[0] * sea[0] + fn[2] * sea[1] < 0:
            rec[0] = [p3[0], p3[2], p3[1]]
            rec[1] = [rec[1][0], rec[1][2], rec[1][1]]
            flips += 1
    print(f"   winding: {flips}/{len(seated)} wall tris flipped seaward")
    assert flips in (0, len(seated)), \
        f"non-unanimous carry winding ({flips}/{len(seated)}) — mixed cut"
    # THE LEAN FACT (census 3, unanimous 5/5): stock's grass-family lip walls
    # ALL overhang (seaward-wound ny in [-0.37,-0.15] — the rock lip curls over
    # the water; the bench generator's back-lean was OUR deviation). Seaward
    # winding alone goes walk-INVISIBLE, and over the cut sea the fan MISSes
    # and the hug catches. THE SEPARABILITY LAW resolves it: navigation and
    # render are separable — emit the verbatim seaward render face PLUS a
    # coplanar reversed-winding WALK MEMBRANE (ny > 0.1, topo 58, occluded
    # in-game from every viewpoint: sea side shows the render face, land side
    # is under the lawn edge).
    nys = [W.up_ny(tuple(p3[0]), tuple(p3[1]), tuple(p3[2]))
           for (p3, _u, _c) in seated]
    print(f"   lean: seaward-wound ny in [{min(nys):.3f}, {max(nys):.3f}]")
    membranes = []
    if min(nys) <= 0.1:
        for (p3, uv3, c) in list(seated):
            membranes.append([[p3[0], p3[2], p3[1]],
                              [uv3[0], uv3[2], uv3[1]], c])
        m_ny = [W.up_ny(tuple(p3[0]), tuple(p3[1]), tuple(p3[2]))
                for (p3, _u, _c) in membranes]
        assert min(m_ny) > 0.1, f"membrane not walk-visible: {min(m_ny):.3f}"
        print(f"   walk membrane: +{len(membranes)} reversed copies "
              f"(ny [{min(m_ny):.3f},{max(m_ny):.3f}])")
    seated.extend(membranes)

    # BAND CONTINUATION for the auxiliary stack (the playtest-8 fix). The
    # apron/fans/curtain previously sampled an arbitrary sliver of the band
    # at ~6x stretch (+ constant-uv fans) — the flow check measured 16 smears
    # + 62 stretched + mirrored faces exactly at the waterline; at the graze
    # camera that IS the owner's "light seaming" streak. The lawful paint is
    # the carried wall's OWN uv field continued at stock density: u follows
    # each wall column's crest u; v continues from the foot row. Below the
    # band bottom (v_foot=0.9229) the atlas is white/blank (measured — the
    # white-sliver class), so v FOLDS BACK up the band from the foot row: the
    # rim shows the wall's own waterline row, the porch re-runs the rock rows
    # (mirror at the fold = the same texel row meets itself; stock precedent
    # 2/139 mirrored faces).
    crest_u = []
    for k in seg:
        us_here = {round(float(u), 4) for t in wall
                   for p, (u, v) in zip(t[0], t[1]) if key(p) == k}
        assert len(us_here) == 1, f"ambiguous crest u at {k}: {us_here}"
        crest_u.append(us_here.pop())
    v_foot = max(float(v) for t in wall for (u, v) in t[1])
    v_rate = 0.0095                                         # measured donor slope
    print(f"   band continuation: crest u {crest_u}, v_foot {v_foot:.4f}")

    # THE FOOT APRON — the look-side closure of the under-lip void. The sea
    # is (correctly) cut under ALL walkable plan (the 1.2u-fringe experiment
    # re-armed the trap: an exposed cross-mesh sheet gets ring-cached and
    # answers under-lawn probes). A SAME-mesh shelf behind the lawn in buffer
    # order can never enter the ring (the membrane proved the class): a
    # submerged rock strip from the crest line (y=-0.05) sloping 1.4u inland
    # down to y=-0.6, ending EXACTLY at the crest plan — never first-hit.
    # Subdivided ≤0.6u (the sea-cut precedent): a sub-tile's inradius can never
    # cover the whole 32-candidate fan — the hard-lock predicate is
    # structurally impossible for the shelf, and the latent sweep stays green.
    apron = []
    for i in range(len(crest_pts) - 1):
        a2p, b2p = crest_pts[i], crest_pts[i + 1]
        dxs, dzs = b2p[0] - a2p[0], b2p[1] - a2p[1]
        L2 = math.hypot(dxs, dzs) or 1.0
        land = (-dzs / L2, dxs / L2)                        # land LEFT of travel
        na = max(2, math.ceil(L2 / 0.6))
        nc = 3                                              # across 1.4u
        ua, ub = crest_u[i], crest_u[i + 1]                 # the column's own u

        def P(s, t):                                        # s along [0,1], t across [0,1]
            x2 = a2p[0] + s * dxs + t * 1.4 * land[0]
            z2 = a2p[1] + s * dzs + t * 1.4 * land[1]
            # outer edge +0.06 (a thin rock rim ABOVE the waterline: closes the
            # under-lip sightline slot to the hollow interior — the sky-band
            # forensic), sloping to -0.6 inland
            return (x2, 0.06 - 0.66 * t, z2)

        def UV(s, t):                                       # fold-back continuation
            return (ua + s * (ub - ua), v_foot - t * 1.4 * v_rate)

        for ja in range(na):
            for jc in range(nc):
                s0, s1 = ja / na, (ja + 1) / na
                t0, t1 = jc / nc, (jc + 1) / nc
                apron.append([[P(s0, t0), P(s1, t0), P(s0, t1)],
                              [UV(s0, t0), UV(s1, t0), UV(s0, t1)], -1])
                apron.append([[P(s1, t0), P(s1, t1), P(s0, t1)],
                              [UV(s1, t0), UV(s1, t1), UV(s0, t1)], -1])
    # corner WEDGE fans: each segment's rectangle offsets perpendicular to
    # itself — at a convex crest vertex the two leave an uncovered pie wedge
    # (ray-cast forensic: the sky band tunneled through it into the hollow
    # interior). Fill with a radially/angularly subdivided fan.
    for i in range(1, len(crest_pts) - 1):
        cv = crest_pts[i]
        dirs = []
        for (aa, bb) in ((crest_pts[i - 1], cv), (cv, crest_pts[i + 1])):
            dxs, dzs = bb[0] - aa[0], bb[1] - aa[1]
            L2 = math.hypot(dxs, dzs) or 1.0
            dirs.append((-dzs / L2, dxs / L2))
        a0 = math.atan2(dirs[0][0], dirs[0][1])
        a1 = math.atan2(dirs[1][0], dirs[1][1])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        nang, nrad = max(2, math.ceil(abs(da) / 0.45)), 3

        def PW(js, jt):
            ang = a0 + da * js / nang
            t = jt / nrad
            return (cv[0] + 1.4 * t * math.sin(ang), 0.06 - 0.66 * t,
                    cv[1] + 1.4 * t * math.cos(ang))

        # fan uv: u enters at the shared crest u (continuous with segment
        # i-1's apron edge) and sweeps by mid-radius arc length at the donor's
        # own u-rate, continuing the crest's u trend; v = the same fold-back.
        # The exit edge mismatches segment i by ~0.01 u — a lawful uv cut
        # (stock's own coast carries hundreds).
        u_dir = math.copysign(1.0, crest_u[i + 1] - crest_u[i])

        def UVW(js, jt):
            arcl = abs(da) * (js / nang) * 0.7
            return (crest_u[i] + u_dir * arcl * URATE,
                    v_foot - (jt / nrad) * 1.4 * v_rate)

        for js in range(nang):
            for jt in range(nrad):
                apron.append([[PW(js, jt), PW(js + 1, jt), PW(js, jt + 1)],
                              [UVW(js, jt), UVW(js + 1, jt), UVW(js, jt + 1)], -1])
                if jt < nrad:
                    apron.append([[PW(js + 1, jt), PW(js + 1, jt + 1), PW(js, jt + 1)],
                                  [UVW(js + 1, jt), UVW(js + 1, jt + 1),
                                   UVW(js, jt + 1)], -1])

    for rec in apron:                                       # up-facing winding
        p3 = rec[0]
        ny2 = W.up_ny(tuple(p3[0]), tuple(p3[1]), tuple(p3[2]))
        if ny2 < 0:
            rec[0] = [p3[0], p3[2], p3[1]]
            rec[1] = [rec[1][0], rec[1][2], rec[1][1]]
    apron = [r for r in apron
             if W.up_ny(tuple(r[0][0]), tuple(r[0][1]), tuple(r[0][2])) > 1e-9]

    # THE INNER CURTAIN — the categorical sightline closure. Grazing rays
    # cross at the rim edge and descend SHALLOWER than the apron dips (ray
    # forensic: 0.27/u vs 0.47/u), clearing its inner edge into the hollow
    # interior. A VERTICAL sheet at the apron's inland edge, floor (-0.6) to
    # just under the lawn (3.15), bounds the slot on every remaining path.
    # Plan-degenerate => the walk query can never even scan it (ny <= 0.1
    # skip) — walk-inert by construction, in-Terrain behind lawn regardless.
    curtain = []
    v_top_band = V_TOP                                      # 0.8926 (band top)

    def vquad(pa, pb, u0, u1):
        b0 = (pa[0], -0.6, pa[1])
        b1 = (pb[0], -0.6, pb[1])
        t0 = (pa[0], 3.15, pa[1])
        t1 = (pb[0], 3.15, pb[1])

        def vv(y):                                          # band re-run, top->foot
            return v_top_band + (3.15 - y) / 3.75 * (v_foot - v_top_band)

        # wind SEAWARD (-x-ish): cross(along, up) points inland, so reverse
        curtain.append([[b0, t0, b1],
                        [(u0, vv(-0.6)), (u0, vv(3.15)), (u1, vv(-0.6))], -1])
        curtain.append([[b1, t0, t1],
                        [(u1, vv(-0.6)), (u0, vv(3.15)), (u1, vv(3.15))], -1])

    inner_pts, inner_u = [], []
    for i in range(len(crest_pts) - 1):
        a2p, b2p = crest_pts[i], crest_pts[i + 1]
        dxs, dzs = b2p[0] - a2p[0], b2p[1] - a2p[1]
        L2 = math.hypot(dxs, dzs) or 1.0
        land = (-dzs / L2, dxs / L2)
        inner_pts.append((a2p[0] + 1.4 * land[0], a2p[1] + 1.4 * land[1]))
        inner_pts.append((b2p[0] + 1.4 * land[0], b2p[1] + 1.4 * land[1]))
        inner_u += [crest_u[i], crest_u[i + 1]]
    for i in range(0, len(inner_pts) - 1):
        vquad(inner_pts[i], inner_pts[i + 1], inner_u[i], inner_u[i + 1])
    seated.extend(apron)
    seated.extend(curtain)
    print(f"   foot apron: +{len(apron)} shelf + {len(curtain)} inner-curtain tris")

    # ---- WELD: joint columns re-anchor to the kept wall edges at v5/v11 -----------
    kept_edges = {0: [], 1: []}                             # 0 = v5 side, 1 = v11 side
    base_by_block = {}
    for (bx, by) in BLOCKS:
        d = W.M.read_ff9mesh(BASELINE_T[(bx, by)])
        base_by_block[(bx, by)] = d
        ox, oz = 64.0 * bx, -64.0 * by
        for t0 in range(0, len(d["indices"]), 3):
            t = d["indices"][t0:t0 + 3]
            topo = (int(round(d["tangents"][t[0]][0])) & 0xFC) >> 2
            if topo != 58:
                continue
            pw = [(d["verts"][j][0] + ox, d["verts"][j][1], d["verts"][j][2] + oz)
                  for j in t]
            for (ji, jp) in ((0, BENCH_V5), (1, BENCH_V11)):
                if any(math.hypot(p[0] - jp[0], p[2] - jp[1]) < 0.05 for p in pw):
                    for p in pw:
                        dd = math.hypot(p[0] - jp[0], p[2] - jp[1])
                        if 0.05 < dd < 1.6:
                            kept_edges[ji].append(p)
    for ji in (0, 1):
        print(f"   kept edge verts at joint {ji}: "
              + ", ".join(f"({p[0]:.2f},{p[1]:.2f},{p[2]:.2f})" for p in kept_edges[ji][:6]))
    moved = 0
    for t3, uv3, _c in seated:
        for k in range(3):
            p = t3[k]
            if p[1] > LAWN_Y - 0.05:
                continue                                    # crest verts already snapped
            for (ji, jp) in ((0, BENCH_V5), (1, BENCH_V11)):
                if math.hypot(p[0] - jp[0], p[2] - jp[1]) < 2.2 and kept_edges[ji]:
                    tgt = min(kept_edges[ji],
                              key=lambda q: (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2
                              + (q[2] - p[2]) ** 2)
                    if math.dist(tgt, p) < 2.4:
                        t3[k] = tuple(tgt)
                        moved += 1
    print(f"   weld re-anchors: {moved} verts")

    # ---- the drop + zip strip (v2 machinery, new outer, EXACT inner chain) --------
    ys_in = [p[1] for p in inner_x]
    assert all(abs(y - LAWN_Y) < 0.01 for y in ys_in), \
        f"inner lawn not flat at {LAWN_Y}: {ys_in} — needs exact-y zip welding"
    outer = crest_pts
    strip_poly = inner2 + list(reversed(outer[1:-1])) if len(outer) > 2 else inner2

    def in_strip2(p, eps=1e-6):
        n = len(strip_poly)
        inside = False
        for i in range(n):
            a, b = strip_poly[i], strip_poly[(i + 1) % n]
            if (a[1] > p[1]) != (b[1] > p[1]):
                xin = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                if p[0] < xin - eps:
                    inside = not inside
        return inside

    def in_tri2(p, tw):
        """STRICTLY interior — a strip vertex ON a kept face's corner/edge is
        boundary touch, not coverage (the exact-coords drop over-reach: the
        kept wall face AT v5 was dropped, holing the wall north of the joint)."""
        d0 = ((tw[1][0] - tw[0][0]) * (tw[2][1] - tw[0][1])
              - (tw[2][0] - tw[0][0]) * (tw[1][1] - tw[0][1]))
        if abs(d0) < 1e-12:
            return False
        w0 = ((tw[1][0] - p[0]) * (tw[2][1] - p[1])
              - (tw[2][0] - p[0]) * (tw[1][1] - p[1])) / d0
        w1 = ((tw[2][0] - p[0]) * (tw[0][1] - p[1])
              - (tw[0][0] - p[0]) * (tw[2][1] - p[1])) / d0
        return w0 > 1e-6 and w1 > 1e-6 and (1 - w0 - w1) > 1e-6

    strip_vs = list(strip_poly)

    def strictly_in(p):
        if min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in strip_vs) < 1e-4:
            return False                                    # ON a strip vertex
        return in_strip2(p)

    affs = lawn_affines([(BASELINE_T[(bx, by)], 64.0 * bx, -64.0 * by)
                         for (bx, by) in BLOCKS])
    # THE STRIP COVER: ear-clip the simple strip polygon — the naive two-chain
    # zip overlaps/holes when INNER folds back at the notch (the render gate
    # caught it). Donors: per ear, the nearest INNER-edge midpoint's donor.
    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (b[0] - o[0]) * (a[1] - o[1])

    def earclip(ring):
        P = list(ring)
        if sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1]
               for i in range(len(P))) < 0:
            P = list(reversed(P))
        tris3, guard = [], 0
        while len(P) > 3 and guard < 4000:
            guard += 1
            n = len(P)
            for i2 in range(n):
                a, b, c = P[(i2 - 1) % n], P[i2], P[(i2 + 1) % n]
                if _cross(a, b, c) <= 1e-12:
                    continue
                if any(_cross(a, b, q) >= -1e-12 and _cross(b, c, q) >= -1e-12
                       and _cross(c, a, q) >= -1e-12
                       for q in P if q not in (a, b, c)):
                    continue
                tris3.append((a, b, c))
                del P[i2]
                break
            else:
                break
        assert len(P) == 3, f"ear-clip stuck with {len(P)} verts"
        tris3.append(tuple(P))
        return tris3

    # THE ATLAS-VALIDATED TRANSLATE-CLONE LAWN (the render-gate probe chain):
    # the local lawn map is phase-consistent, but its PAINTED atlas band ENDS
    # at the old boundary — linear continuation seaward walks the uv into
    # white paint no matter how near the donor tile is (three identical
    # renders proved distance-based donor picks are no-ops). The mains are
    # 4u-periodic, so a whole-lattice shift is phase-lawful: pick the SMALLEST
    # (k,m) lattice shift whose uv footprint samples ZERO white/blank texels —
    # validated against the atlas itself (study angle 4, pulled forward).
    import numpy as _np
    from ff9mapkit.world import atlas as _A
    from ff9mapkit import config as _cfg
    _atl = _np.asarray(_A.load_atlas("terrain", game=Path(_cfg.find_game_path(None)),
                                     source="engine").convert("RGBA"))
    _ah, _aw = _atl.shape[:2]

    def _bad_uv(u, v):
        iu = int((u % 1.0) * _aw) % _aw
        iv = int((1.0 - (v % 1.0)) * _ah) % _ah
        r2, g2, b2, a2 = _atl[iv, iu]
        return a2 == 0 or (r2 > 235 and g2 > 235 and b2 > 235)

    def _footprint_bad(uv3):
        """EVERY texel under the uv triangle (point samples missed sliver
        whites). Bounding-box barycentric walk at texel resolution."""
        (u0, v0), (u1, v1), (u2, v2) = uv3
        d0 = (u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)
        if abs(d0) < 1e-12:
            return any(_bad_uv(u, v) for (u, v) in uv3)
        lo_u, hi_u = min(u0, u1, u2), max(u0, u1, u2)
        lo_v, hi_v = min(v0, v1, v2), max(v0, v1, v2)
        step = 1.0 / _aw
        u = lo_u
        while u <= hi_u + step:
            v = lo_v
            while v <= hi_v + step:
                w1 = ((u - u0) * (v2 - v0) - (u2 - u0) * (v - v0)) / d0
                w2 = ((u1 - u0) * (v - v0) - (u - u0) * (v1 - v0)) / d0
                if w1 >= -0.02 and w2 >= -0.02 and (1 - w1 - w2) >= -0.02 \
                        and _bad_uv(u, v):
                    return True
                v += step
            u += step
        return False

    ears = earclip(inner2 + list(reversed(outer[1:-1])))
    lawn3 = []
    for (p, q, r) in ears:
        cen = ((p[0] + q[0] + r[0]) / 3, (p[1] + q[1] + r[1]) / 3)
        best = min(affs, key=lambda pf: (sum(v[0] for v in pf[0]) / 3 - cen[0]) ** 2
                   + (sum(v[2] for v in pf[0]) / 3 - cen[1]) ** 2)
        f0 = best[1]
        pick = None
        for (k4, m4) in sorted([(k, m) for k in (-2, -1, 0, 1, 2)
                                for m in (-2, -1, 0, 1, 2)],
                               key=lambda km: (abs(km[0]) + abs(km[1]), km)):
            uv3 = [f0(s[0] - 4.0 * k4, s[1] - 4.0 * m4) for s in (p, q, r)]
            if not _footprint_bad(uv3):
                pick = (k4, m4)
                break
        if pick is None:
            pick = (0, 0)
            print(f"   !! ear at ({cen[0]:.1f},{cen[1]:.1f}): NO clean lattice "
                  f"shift in +/-2 — white texels will show")
        elif pick != (0, 0):
            print(f"   ear at ({cen[0]:.1f},{cen[1]:.1f}): lattice shift {pick}")
        donor = (lambda f2, kk, mm: lambda x, z: f2(x - 4.0 * kk, z - 4.0 * mm))(
            f0, pick[0], pick[1])
        lawn3.append(((p, q, r), donor))
    print(f"   strip cover: {len(lawn3)} ear tris (atlas-validated translate-clone)")

    staged = {}
    for (bx, by) in BLOCKS:
        ox, oz = 64.0 * bx, -64.0 * by
        d = base_by_block[(bx, by)]
        verts = [list(v) for v in d["verts"]]
        normals = [list(v) for v in d["normals"]]
        uvs = [list(v) for v in d["uvs"]]
        tans = [list(v) for v in d["tangents"]]
        idx = d["indices"]
        drop = set()
        for t0 in range(0, len(idx), 3):
            t = idx[t0:t0 + 3]
            topo = (int(round(tans[t[0]][0])) & 0xFC) >> 2
            if topo != 58:
                continue
            pw = [(verts[j2][0] + ox, verts[j2][2] + oz) for j2 in t]
            cen = ((pw[0][0] + pw[1][0] + pw[2][0]) / 3, (pw[0][1] + pw[1][1] + pw[2][1]) / 3)
            if any(strictly_in(p) for p in pw) or strictly_in(cen) \
                    or any(in_tri2(q, pw) for q in strip_poly):
                drop.add(t0 // 3)
        new_idx = [k for t0 in range(0, len(idx), 3) if t0 // 3 not in drop
                   for k in idx[t0:t0 + 3]]
        lawn_nrm = lawn_tan = None
        for t0 in range(0, len(idx), 3):
            t = idx[t0:t0 + 3]
            if ((int(round(tans[t[0]][0])) & 0xFC) >> 2) in W.WALK_OK:
                lawn_nrm, lawn_tan = list(normals[t[0]]), list(tans[t[0]])
                break
        wall_nrm = [0.0, 0.3, 0.9]

        def emit(p3, uv3, nrm, tan, up_sign):
            a2 = ((p3[1][0] - p3[0][0]) * (p3[2][2] - p3[0][2])
                  - (p3[2][0] - p3[0][0]) * (p3[1][2] - p3[0][2]))
            if abs(a2) < 1e-6 and up_sign > 0:
                return
            order = (0, 1, 2)
            ny = (p3[1][2] - p3[0][2]) * (p3[2][0] - p3[0][0]) \
                - (p3[1][0] - p3[0][0]) * (p3[2][2] - p3[0][2])
            if ny * up_sign < 0 and up_sign > 0:
                order = (0, 2, 1)
            for k in order:
                verts.append([p3[k][0] - ox, p3[k][1], p3[k][2] - oz])
                uvs.append(list(uv3[k]))
                normals.append(list(nrm))
                tans.append(list(tan))
                new_idx.append(len(verts) - 1)

        n_lawn = n_wall = 0
        for ((a, b, c), donor) in lawn3:
            poly = clip_halfplane([a, b, c], keep_north=(by == 7))
            for (p, q, r) in fan(poly):
                p3 = [(p[0], LAWN_Y, p[1]), (q[0], LAWN_Y, q[1]), (r[0], LAWN_Y, r[1])]
                uv3 = [donor(pt[0], pt[2]) for pt in p3]
                emit(p3, uv3, lawn_nrm, lawn_tan, +1)
                n_lawn += 1
        for (p3, uv3, _c) in seated:
            cz = (p3[0][2] + p3[1][2] + p3[2][2]) / 3
            cby = 7 if cz >= SEAM_Z else 8
            if cby != by:
                continue
            emit(p3, uv3, wall_nrm, list(TAN_CLIFF), 0)     # carried winding, no flip
            n_wall += 1
        print(f"   [{bx}][{by}]: {len(drop)} dropped, +{n_lawn} lawn, +{n_wall} wall; "
              f"tris {len(idx) // 3} -> {len(new_idx) // 3}")
        ev, en, eu, et, eidx = [], [], [], [], []
        for k in new_idx:
            eidx.append(len(ev))
            ev.append(list(verts[k]))
            en.append(list(normals[k]))
            eu.append(list(uvs[k]))
            et.append(list(tans[k]))
        bm = W.M.blockmesh_from_ff9mesh(BASELINE_T[(bx, by)], disc=W.DISC,
                                        x=bx, y=by, part="terrain")
        chan = dict(bm.chan_arrays)
        chan[CH_POS], chan[CH_NRM], chan[CH_UV], chan[CH_TAN] = ev, en, eu, et
        tris2 = [[eidx[k], eidx[k + 1], eidx[k + 2]] for k in range(0, len(eidx), 3)]
        out = dataclasses.replace(bm, vcount=len(ev), chan_arrays=chan,
                                  flat_index=eidx, tris=tris2)
        OUTD2.mkdir(parents=True, exist_ok=True)
        sp = OUTD2 / f"Block[{bx}][{by}] Terrain.ff9mesh"
        W.M.write_ff9mesh(out, sp)
        staged[(bx, by, "Terrain")] = sp

    # weld audit: near-miss vertex census over the staged joint neighbourhoods
    near = 0
    for (bx, by) in BLOCKS:
        d2 = W.M.read_ff9mesh(staged[(bx, by, "Terrain")])
        ox, oz = 64.0 * bx, -64.0 * by
        pts = {}
        for v in d2["verts"]:
            p = (v[0] + ox, v[1], v[2] + oz)
            if min(math.hypot(p[0] - j[0], p[2] - j[1])
                   for j in (BENCH_V5, BENCH_V11)) < 3.0:
                pts[(round(p[0], 4), round(p[1], 4), round(p[2], 4))] = p
        ks = list(pts.values())
        for a2 in range(len(ks)):
            for b2 in range(a2 + 1, len(ks)):
                dd = math.dist(ks[a2], ks[b2])
                if 1e-6 < dd < 0.05:
                    near += 1
                    print(f"      near-miss {dd:.4f}u: {ks[a2]} vs {ks[b2]}")
    print(f"   WELD AUDIT: {near} near-miss pairs (must be 0)")
    return staged, near == 0, in_strip2


def stage1():
    global PICK
    world_base = W.load_world(part_src={(bx, by, "Terrain"): BASELINE_T[(bx, by)]
                                        for (bx, by) in BLOCKS})
    staged = None
    for cand in PICKS:
        PICK = cand
        try:
            staged, g_weld, in_strip2 = build()
            print(f"   DONOR SEATED: {cand['blk']} chain{cand['chain']} "
                  f"v{cand['i0']}..v{cand['i1']}")
            break
        except DonorReject as e:
            print(f"   donor {cand['blk']} REJECTED: {e}")
    assert staged is not None, "every census donor rejected — record in the study"
    world_t = W.load_world(part_src=dict(staged))

    lost, gained, off = [], [], []
    x = 372.0
    while x <= 390.0:
        z = -519.0
        while z <= -506.0:
            a = any(s2[1] in W.WALK_OK for s2 in W.all_sheets(world_base, x, z))
            b = any(s2[1] in W.WALK_OK for s2 in W.all_sheets(world_t, x, z))
            if a and not b:
                lost.append((round(x, 1), round(z, 1)))
            if b and not a and not in_strip2((x, z)):
                off.append((round(x, 1), round(z, 1)))
            z += 0.2
        x += 0.2
    g_cov = len(lost) == 0 and len(off) <= 2
    print(f"COVERAGE: lost={len(lost)} off-strip={len(off)} "
          f"({'PASS' if g_cov else 'FAIL'}) {lost[:5]} {off[:5]}")

    print("=== SEA REBUILD from pristine, WALKABLE-only cover (the seam fix) ===")
    # PLAYTEST 7: pale waterline slivers = the historical ANY-terrain cut's
    # deletion boundary exposed under the transplanted (overhanging) stock lip.
    # Stock's FREE-BASE runs water under the wall to the base; only sea under
    # WALKABLE cover arms the ring trap. Rebuild the corner blocks' Sea4 from
    # the PRISTINE pre-cut bytes, cutting under walkable cover only.
    sea_records = {}
    for (bx, by) in BLOCKS:
        changed, out, records = treat_part(world_t, bx, by, "Sea4",
                                           src_path=PRISTINE_SEA[(bx, by)],
                                           cover=walkable_cover)
        if changed:
            sp = OUTD2 / f"Block[{bx}][{by}] Sea4.ff9mesh"
            W.M.write_ff9mesh(out, sp)
            staged[(bx, by, "Sea4")] = sp
            sea_records[(bx, by, "Sea4")] = records
    world_full = W.load_world(part_src=dict(staged))
    if sea_records:
        from vcorner_sea_cut import verify as sea_verify
        # reference = staged terrain + PRISTINE sea: restored tiles are a
        # subset of pristine, so new-legal must be 0 and hit->MISS = the cut
        pris = dict(staged)
        for (bx, by) in BLOCKS:
            pris[(bx, by, "Sea4")] = PRISTINE_SEA[(bx, by)]
        world_pris = W.load_world(part_src=pris)
        g_sea = sea_verify(world_pris, world_full, sea_records)
    else:
        g_sea = True
        print("   sea already conforms (no new hidden tris)")

    print("=== THE HUG GATES ===")
    south = [(377.5, -503.0), (377.2, -505.5), (377.0, -507.0)]
    r1 = hug(world_full, south, math.pi, math.radians(22.5), lambda x, z: z < -516.5)
    north = [(381.5, -517.5), (381.0, -518.5)]
    r3 = hug(world_full, north, 0.0, math.radians(22.5), lambda x, z: z > -507.0)
    ctrl = hug(world_full, [(446.5, -496.0)], math.pi, math.radians(-22.5),
               lambda x, z: z < -516.0)
    for tag, rr in (("south+22.5", r1), ("north+22.5", r3), ("control", ctrl)):
        for (sx, sz, res, stalls) in rr:
            print(f"   {tag} ({sx:6.1f},{sz:7.1f}): {res} stalls={stalls}")
    g_hug = all(r[2].startswith("PASS") for r in r1 + r3 + ctrl)

    ev, hard, ringy = drive_walkers(world_full, "STAGED transplant")
    own0 = [e for e in ev if e["own"] == 0]
    g_own0 = len(own0) == 0
    tl, cl, cells_l = static_map(world_base, "BASELINE")
    ts, cs, cells_s = static_map(world_full, "STAGED")
    bx0, bx1, bz0, bz1 = CHANGED_BBOX
    diff_out = 0
    for kk2 in set(cells_l) | set(cells_s):
        if cells_l.get(kk2) != cells_s.get(kk2):
            x = 368.0 + kk2[0] * 0.25
            z = -516.0 + kk2[1] * 0.25
            if not (bx0 <= x <= bx1 and bz0 <= z <= bz1):
                diff_out += 1
    g_stat = diff_out == 0 and len(ts) == 0

    gates = dict(g_weld=g_weld, g_coverage=g_cov, g_sea=g_sea, g_hug=g_hug,
                 g_no_own0=g_own0, g_statics=g_stat)
    print("=== STAGE-1 GATES ===")
    for k, v in gates.items():
        print(f"   {k}: {'PASS' if v else 'FAIL'}")
    json.dump(dict(gates=gates), open(OUTD2 / "gates_stage1.json", "w"), indent=1)


def staged_src():
    src = {}
    for (bx, by) in BLOCKS:
        for part in ("Terrain", "Sea4"):
            sp = OUTD2 / f"Block[{bx}][{by}] {part}.ff9mesh"
            if sp.is_file():
                src[(bx, by, part)] = sp
    return src


def stage2():
    world = W.load_world(part_src=staged_src())
    hard_c, poisonable, _cl = sweep(world, "STAGED transplant")
    hard_f = refine(world, poisonable, "STAGED transplant")
    g = len(hard_c) == 0 and len(hard_f) == 0
    print(f"g_latent: {'PASS' if g else 'FAIL'}")
    json.dump(dict(g_latent_zero=g), open(OUTD2 / "gates_stage2.json", "w"), indent=1)


def render():
    import numpy as np
    from PIL import Image
    import render_gate as RG
    batches = RG.load_batches(dict(staged_src()))
    for vn, v in RG.VIEWS.items():
        img = RG.raster(v, batches, f"transplant_{vn}")
        bp = RG.OUTD / f"baseline_{vn}.png"
        if bp.is_file():
            RG.diff(np.asarray(Image.open(bp).convert("RGB")), img, f"tp_{vn}")


def deploy():
    g1 = json.load(open(OUTD2 / "gates_stage1.json"))
    g2 = json.load(open(OUTD2 / "gates_stage2.json"))
    assert all(g1["gates"].values()) and g2["g_latent_zero"], "gates not green — NO DEPLOY"
    src = staged_src()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    lines = ["import shutil"]
    for (bx, by, part), sp in sorted(src.items()):
        lp = live_path(bx, by, part)
        bk = BACKUPS / f"{lp.name}.r{by}.{ts}"
        shutil.copy2(lp, bk)
        shutil.copy2(sp, lp)
        lines.append(f"shutil.copy2(r'{bk}', r'{lp}')")
        print(f"DEPLOYED {lp.name}   backup: {bk.name}")
    lines.append("print('reverted the segment-transplant deploy')")
    (HERE / "revert_vcorner_transplant.py").write_text("\n".join(lines) + "\n",
                                                      encoding="utf-8")
    world = W.load_world()
    r = hug(world, [(377.5, -503.0), (377.0, -507.0)], math.pi, math.radians(22.5),
            lambda x, z: z < -516.5)
    ev, hard, ringy = drive_walkers(world, "LIVE post-deploy")
    own0 = [e for e in ev if e["own"] == 0]
    print("post-deploy hug:", [rr[2] for rr in r])
    print(f"post-deploy own-ring-0: {len(own0)} ({'PASS' if not own0 else 'FAIL'})")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "census":
        census()
    elif len(sys.argv) > 1 and sys.argv[1] == "stage1":
        stage1()
    elif len(sys.argv) > 1 and sys.argv[1] == "stage2":
        stage2()
    elif len(sys.argv) > 1 and sys.argv[1] == "render":
        render()
    elif len(sys.argv) > 1 and sys.argv[1] == "deploy":
        deploy()
    else:
        raise SystemExit(__doc__)
