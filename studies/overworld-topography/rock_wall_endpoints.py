"""ROCK-WALL ENDPOINT GRAMMAR -- how stock walls TERMINATE and CONNECT (6th wall study).

The rim-aware round closed the minted-plan lane (studies/path-d-new-world/
RIM-AWARE-PREDICTION.md): the residual defects were the COMPOSITION's -- cut windows
mint endpoints stock never ships. This instrument measures what no prior study asked:

  E1 ENDPOINT CENSUS -- chain each component's crest (the plateau-weld line); classify
     every chain endpoint: BORDER (block-cut artifact) / TAPER-TO-GROUND (the body
     pinches out) / CONTINUES-AS-ROCK (the massif goes on without a plateau weld);
     cycles = CLOSED RING.
  E2 TAPER ANATOMY -- per taper endpoint, the height profile h(s) walking inward:
     descent-run length, the crest-descends vs ground-rises split, monotonicity,
     whether the crest band (cols 4-7 rows 3-4) and foot band (row 10) persist to the
     tip.
  E3 RING TOPOLOGY -- chains vs cycles per component; what each closed cycle encloses
     (mesa: plateau in / ground out, like the bench premise -- or not).
  E4 WHOLE-FEATURE CARRY -- per component: size, footprint, border contact; the
     SELF-TERMINATING candidate list (all endpoints taper/ring, zero border) sized
     for the ~48u bench, with the ring-1 plateau payload counted.

Questions registered in studies/path-d-new-world/ENDPOINT-GRAMMAR.md BEFORE this ran.
Read-only vs stock disc-1. Artifacts -> out/rock_wall_endpoints.json + renders.
Regenerate: py -X utf8 rock_wall_endpoints.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

PLATEAU = {10, 11, 12}
TILE_U, TILE_V = 0.0625, 0.03125
OUT = Path(__file__).with_name("out") / "rock_wall_endpoints.json"
PNG_T = Path(__file__).with_name("out") / "endpoint_tapers.png"
PNG_C = Path(__file__).with_name("out") / "endpoint_candidates.png"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731

PU, PV = json.loads((Path(__file__).with_name("out") / "rock_tiles.json").read_text())["phase"]


def tile_of(uvs):
    us = [q[0] for q in uvs]
    vs = [q[1] for q in uvs]
    return (int(math.floor((min(us) - PU) / TILE_U + 0.5)),
            int(math.floor((min(vs) - PV) / TILE_V + 0.5)))


def on_border(p):
    return (min(abs(p[0]), abs(p[0] - 64.0)) < 1.0 or
            min(abs(p[2]), abs(p[2] + 64.0)) < 1.0)


def build_chains(edges):
    """Ordered polylines/cycles from an edge set. Returns (chains, cycles)."""
    adj = defaultdict(set)
    pt3 = {}
    for e in edges:
        a, b = e
        adj[a].add(b)
        adj[b].add(a)
        pt3[a] = np.array(a, dtype=float)
        pt3[b] = np.array(b, dtype=float)
    done = set()
    chains, cycles = [], []

    def walk(a, b):
        ch = [a, b]
        done.add(frozenset((a, b)))
        while len(adj[ch[-1]]) == 2:
            nxt = [q for q in adj[ch[-1]] if frozenset((ch[-1], q)) not in done]
            if not nxt:
                break
            done.add(frozenset((ch[-1], nxt[0])))
            ch.append(nxt[0])
        return ch

    for a in adj:
        if len(adj[a]) != 2:
            for b in adj[a]:
                if frozenset((a, b)) not in done:
                    chains.append(walk(a, b))
    for a in adj:                                           # remaining pure cycles
        for b in adj[a]:
            if frozenset((a, b)) not in done:
                cyc = walk(a, b)
                cycles.append(cyc)
    return ([[pt3[q] for q in ch] for ch in chains if len(ch) >= 2],
            [[pt3[q] for q in cyc] for cyc in cycles if len(cyc) >= 3])


# ---- accumulators ---------------------------------------------------------------------------
ep_classes = Counter()                                      # E1
comp_rows = []                                              # E3/E4 per component
taper_recs = []                                             # E2 per taper endpoint
ring_recs = []                                              # E3 per cycle
tip_top_band = Counter()                                    # E2 tile persistence at tips
tip_foot_band = Counter()
mid_top_band = Counter()
mid_foot_band = Counter()
n_blocks = 0
taper_profiles = []                                         # (label, [(s, h, cy, gy)])
cand_render = []                                            # best candidates plan data

for (bx, by) in X.list_blocks(disc=1):
    try:
        bm = X.read_block(bx, by, disc=1)
    except Exception:                                       # noqa: BLE001
        continue
    V, U, T = bm.verts, bm.uvs, bm.tangents
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
    if not any(t in PLATEAU for t in topo):
        continue

    edge_tris = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))].append(t)

    crest49 = set()
    for e, ts in edge_tris.items():
        if len(ts) == 2:
            pair = {topo[ts[0]], topo[ts[1]]}
            if 49 in pair and pair & PLATEAU:
                crest49.add(ts[0] if topo[ts[0]] == 49 else ts[1])
    adj49 = defaultdict(set)
    for e, ts in edge_tris.items():
        r = [t for t in ts if topo[t] == 49]
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
    wall_tris = set(comp_of)
    if not wall_tris:
        continue
    n_blocks += 1

    comp_tris = defaultdict(list)
    for t in wall_tris:
        comp_tris[comp_of[t]].append(t)

    # crest edges per component (wall tri | plateau tri, 2-tri edges)
    comp_crest_edges = defaultdict(list)
    for e, ts in edge_tris.items():
        if len(ts) != 2:
            continue
        w = [t for t in ts if t in wall_tris]
        p = [t for t in ts if topo[t] in PLATEAU]
        if len(w) == 1 and len(p) == 1:
            comp_crest_edges[comp_of[w[0]]].append(e)

    for root, ts in comp_tris.items():
        ys = [V[i][1] for t in ts for i in tri_idx[t]]
        band_h = max(ys) - min(ys)
        if band_h < 6.0 or len(ts) < 12:
            continue
        ces = comp_crest_edges.get(root, [])
        if not ces:
            continue
        chains, cycles = build_chains(ces)
        vset = [np.array(V[i], dtype=float) for t in ts for i in tri_idx[t]]
        VP = np.array([[p[0], p[2]] for p in vset])
        VY = np.array([p[1] for p in vset])
        xs_ = [p[0] for p in vset]
        zs_ = [p[2] for p in vset]
        n_border_v = sum(1 for p in vset if on_border(p))
        crest_len = sum(sum(float(np.linalg.norm((ch[i + 1] - ch[i])[[0, 2]]))
                            for i in range(len(ch) - 1)) for ch in chains)
        crest_len += sum(sum(float(np.linalg.norm((cy[(i + 1) % len(cy)] - cy[i])[[0, 2]]))
                             for i in range(len(cy))) for cy in cycles)

        def local_band(px, pz, rad):
            d2 = (VP[:, 0] - px) ** 2 + (VP[:, 1] - pz) ** 2
            m = d2 <= rad * rad
            if not m.any():
                return None, None
            return float(VY[m].max() - VY[m].min()), float(VY[m].min())

        def ground_y_near(px, pz, rad=3.0):
            d2 = (VP[:, 0] - px) ** 2 + (VP[:, 1] - pz) ** 2
            m = d2 <= rad * rad
            return float(VY[m].min()) if m.any() else None

        ep_kinds = []
        for ch in chains:
            for tip, nxt in ((ch[0], ch[1]), (ch[-1], ch[-2])):
                if on_border(tip):
                    ep_classes["border"] += 1
                    ep_kinds.append("border")
                    continue
                d = (tip - nxt)[[0, 2]]
                L = float(np.linalg.norm(d)) or 1.0
                probe = tip[[0, 2]] + d / L * 4.0           # 4u beyond the tip
                hb, _ = local_band(float(probe[0]), float(probe[1]), 3.0)
                ht, _ = local_band(float(tip[0]), float(tip[2]), 3.0)
                if hb is None or hb < 0.4 * band_h:
                    ep_classes["taper"] += 1
                    ep_kinds.append("taper")
                    # ---- E2 anatomy: walk inward, profile h(s) ----------------------
                    prof = []
                    s_acc = 0.0
                    prev = None
                    for v3 in ch if tip is ch[0] else ch[::-1]:
                        if prev is not None:
                            s_acc += float(np.linalg.norm((v3 - prev)[[0, 2]]))
                        prev = v3
                        gy = ground_y_near(float(v3[0]), float(v3[2]))
                        if gy is not None:
                            prof.append((round(s_acc, 1), round(float(v3[1]) - gy, 2),
                                         round(float(v3[1]), 2), round(gy, 2)))
                        if s_acc > 40.0:
                            break
                    if len(prof) >= 3:
                        hmax = max(q[1] for q in prof)
                        run = next((q[0] for q in prof if q[1] >= 0.85 * hmax), None)
                        cy0, cyN = prof[0][2], prof[-1][2]
                        gy0, gyN = prof[0][3], prof[-1][3]
                        mono = all(prof[i + 1][1] >= prof[i][1] - 0.6
                                   for i in range(len(prof) - 1))
                        taper_recs.append(dict(
                            blk=(bx, by), run=run, hmax=round(hmax, 1),
                            d_crest=round(cyN - cy0, 2), d_ground=round(gy0 - gyN, 2),
                            mono=mono, tip_h=round(prof[0][1], 2)))
                        if len(taper_profiles) < 10:
                            taper_profiles.append((f"{(bx, by)}", prof))
                    # tile persistence at the tip (last 2 stations ~ 9u)
                    tipP = tip[[0, 2]]
                    for t in ts:
                        c3 = np.mean([[V[i][0], V[i][2]] for i in tri_idx[t]], axis=0)
                        if float(np.linalg.norm(c3 - tipP)) > 9.0:
                            continue
                        tl = tile_of([U[i] for i in tri_idx[t]])
                        if tl[1] in (3, 4) and 4 <= tl[0] <= 7:
                            tip_top_band["band"] += 1
                        elif tl[1] == 10:
                            tip_foot_band["band"] += 1
                        else:
                            tip_top_band["other"] += 1
                            tip_foot_band["other"] += 1
                else:
                    ep_classes["continues"] += 1
                    ep_kinds.append("continues")
        # mid-run tile baseline (everything not near any tip)
        tips = [q for ch in chains for q in (ch[0], ch[-1])]
        for t in ts:
            c3 = np.mean([[V[i][0], V[i][2]] for i in tri_idx[t]], axis=0)
            if any(float(np.linalg.norm(c3 - tp[[0, 2]])) < 9.0 for tp in tips):
                continue
            tl = tile_of([U[i] for i in tri_idx[t]])
            if tl[1] in (3, 4) and 4 <= tl[0] <= 7:
                mid_top_band["band"] += 1
            elif tl[1] == 10:
                mid_foot_band["band"] += 1
            else:
                mid_top_band["other"] += 1
                mid_foot_band["other"] += 1

        # ---- E3: cycles -> enclosure ---------------------------------------------------------
        n_mesa = 0
        for cyc in cycles:
            ep_classes["ring"] += 1
            poly = [(float(p[0]), float(p[2])) for p in cyc]
            area = 0.5 * abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1]
                                 - poly[(i + 1) % len(poly)][0] * poly[i][1]
                                 for i in range(len(poly))))

            def pinp_(px, pz):
                nn = len(poly)
                ins = False
                j2 = nn - 1
                for i2 in range(nn):
                    if ((poly[i2][1] > pz) != (poly[j2][1] > pz)) and \
                            (px < (poly[j2][0] - poly[i2][0]) * (pz - poly[i2][1])
                             / (poly[j2][1] - poly[i2][1] + 1e-12) + poly[i2][0]):
                        ins = not ins
                    j2 = i2
                return ins
            in_p = in_g = 0
            for t in range(ntri):
                c3 = np.mean([[V[i][0], V[i][2]] for i in tri_idx[t]], axis=0)
                if not pinp_(float(c3[0]), float(c3[1])):
                    continue
                if topo[t] in PLATEAU:
                    in_p += 1
                elif topo[t] != 49:
                    in_g += 1
            mesa = in_p > in_g
            if mesa:
                n_mesa += 1
            ring_recs.append(dict(blk=(bx, by), verts=len(cyc),
                                  area=round(area, 0), mesa=bool(mesa),
                                  inside_plateau=in_p, inside_ground=in_g))

        fx = max(xs_) - min(xs_)
        fz = max(zs_) - min(zs_)
        self_term = (n_border_v == 0 and ep_kinds
                     and all(k in ("taper",) for k in ep_kinds)) or \
                    (n_border_v == 0 and not ep_kinds and len(cycles) > 0)
        comp_rows.append(dict(
            blk=(bx, by), tris=len(ts), band_h=round(band_h, 1),
            crest_len=round(crest_len, 1), chains=len(chains), rings=len(cycles),
            mesas=n_mesa, foot=(round(fx, 1), round(fz, 1)),
            border_verts=n_border_v, ep=dict(Counter(ep_kinds)),
            self_term=bool(self_term)))
        if self_term:
            ring1 = set()
            for e in comp_crest_edges.get(root, []):
                for t in edge_tris[e]:
                    if topo[t] in PLATEAU:
                        ring1.add(t)
            comp_rows[-1]["ring1_tris"] = len(ring1)
            if len(cand_render) < 4:
                cand_render.append(dict(
                    blk=(bx, by), foot=(fx, fz),
                    body=[[(V[i][0], V[i][2]) for i in tri_idx[t]] for t in ts],
                    ring1=[[(V[i][0], V[i][2]) for i in tri_idx[t]] for t in ring1],
                    crest=[[(float(p[0]), float(p[2])) for p in ch] for ch in chains]
                    + [[(float(p[0]), float(p[2])) for p in cy + [cy[0]]]
                       for cy in cycles]))


# ---- summaries ------------------------------------------------------------------------------
def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


tot_ep = sum(ep_classes.values())
print(f"population: {n_blocks} blocks, {len(comp_rows)} components, {tot_ep} crest "
      f"chain endpoints (+ rings counted separately)\n")

print("== E1 THE ENDPOINT CENSUS ==")
for k in ("taper", "continues", "border", "ring"):
    print(f"   {k:10s}: {ep_classes.get(k, 0):4d}"
          + (f"  ({ep_classes.get(k, 0) / max(1, tot_ep):.0%} of endpoints)"
             if k != "ring" else "  (closed cycles)"))
real = ep_classes.get("taper", 0) + ep_classes.get("continues", 0)
print(f"   REAL endpoints (non-border): {real}; taper share of real: "
      f"{ep_classes.get('taper', 0) / max(1, real):.0%}")

print("\n== E2 TAPER ANATOMY ==")
runs = [r["run"] for r in taper_recs if r["run"] is not None]
print(f"   taper endpoints profiled: {len(taper_recs)}")
print(f"   descent-run length (tip -> 85% height): med {pct(runs, 50)}u "
      f"p25 {pct(runs, 25)} p75 {pct(runs, 75)} p90 {pct(runs, 90)}")
dc = [r["d_crest"] for r in taper_recs]
dg = [r["d_ground"] for r in taper_recs]
print(f"   the lift split over the run: crest RISES med {pct(dc, 50)}u "
      f"(p25 {pct(dc, 25)} p75 {pct(dc, 75)}); ground FALLS med {pct(dg, 50)}u "
      f"(p25 {pct(dg, 25)} p75 {pct(dg, 75)})")
print(f"   tip height h(0): med {pct([r['tip_h'] for r in taper_recs], 50)}u; "
      f"monotone climbs: {sum(1 for r in taper_recs if r['mono'])}/{len(taper_recs)}")
tt = tip_top_band
print(f"   crest band (cols4-7 rows3-4) near tips: {tt.get('band', 0)} band / "
      f"{tt.get('other', 0)} other (mid-run: {mid_top_band.get('band', 0)} / "
      f"{mid_top_band.get('other', 0)})")
print(f"   foot band (row 10) near tips: {tip_foot_band.get('band', 0)} band "
      f"(mid-run: {mid_foot_band.get('band', 0)})")

print("\n== E3 RING TOPOLOGY ==")
n_ring_comp = sum(1 for c in comp_rows if c["rings"])
print(f"   components with >=1 closed crest cycle: {n_ring_comp}/{len(comp_rows)}; "
      f"cycles total {len(ring_recs)}, MESA (plateau in / ground out): "
      f"{sum(1 for r in ring_recs if r['mesa'])}")
for r in sorted(ring_recs, key=lambda q: -q["area"])[:8]:
    print(f"      blk {r['blk']}: {r['verts']} verts, area {r['area']}u2, "
          f"{'MESA' if r['mesa'] else 'not-mesa'} (in: {r['inside_plateau']}p/"
          f"{r['inside_ground']}g)")

print("\n== E4 WHOLE-FEATURE CANDIDATES ==")
cands = [c for c in comp_rows if c["self_term"]]
print(f"   self-terminating components (no border, endpoints all taper/ring): "
      f"{len(cands)}/{len(comp_rows)}")
for c in sorted(cands, key=lambda q: q["tris"]):
    fit = max(c["foot"]) <= 48.0
    print(f"      blk {c['blk']}: {c['tris']} tris, foot {c['foot']}, band_h "
          f"{c['band_h']}, crest {c['crest_len']}u, chains {c['chains']} rings "
          f"{c['rings']} ({c.get('ring1_tris', 0)} ring-1 tris) "
          f"{'<= BENCH-SIZED' if fit else '(too big)'} ep {c['ep']}")

# ---- renders --------------------------------------------------------------------------------
PNG_T.parent.mkdir(parents=True, exist_ok=True)
img = Image.new("RGB", (760, 420), (24, 26, 30))
dr = ImageDraw.Draw(img)
dr.text((10, 6), "taper height profiles h(s): tip at s=0 (10 sampled endpoints)",
        fill=(220, 220, 220))
for li, (lab, prof) in enumerate(taper_profiles):
    col = (90 + (li * 37) % 160, 120 + (li * 53) % 130, 230 - (li * 29) % 120)
    pts = [(60 + q[0] * 15.0, 400 - q[1] * 18.0) for q in prof]
    if len(pts) >= 2:
        dr.line(pts, fill=col, width=2)
dr.line([(60, 400), (700, 400)], fill=(120, 120, 130), width=1)
dr.text((62, 402), "s=0 (tip)  ->  40u inward; y = wall height (0-20u)",
        fill=(150, 150, 160))
img.save(PNG_T)

img2 = Image.new("RGB", (380 * max(1, len(cand_render)), 420), (24, 26, 30))
dr2 = ImageDraw.Draw(img2)
for pi, rc in enumerate(cand_render):
    pts = [p for tri in rc["body"] for p in tri]
    cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2.0
    cz = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2.0
    span = max(rc["foot"][0], rc["foot"][1], 8.0)
    sc = 340.0 / (span + 8.0)
    ox = pi * 380 + 190

    def M(p, ox=ox, cx=cx, cz=cz, sc=sc):
        return (ox + (p[0] - cx) * sc, 214 + (p[1] - cz) * sc)

    for tri in rc["body"]:
        dr2.polygon([M(p) for p in tri], outline=(80, 84, 94))
    for tri in rc["ring1"]:
        dr2.polygon([M(p) for p in tri], outline=(90, 200, 120))
    for ch in rc["crest"]:
        dr2.line([M(p) for p in ch], fill=(245, 220, 90), width=2)
    dr2.text((pi * 380 + 8, 6), f"blk {rc['blk']}  foot "
             f"{rc['foot'][0]:.0f}x{rc['foot'][1]:.0f}u", fill=(220, 220, 220))
dr2.text((8, 402), "gray = rock body  yellow = crest  green = ring-1 plateau course",
         fill=(170, 170, 180))
img2.save(PNG_C)
print(f"\nrenders -> {PNG_T}\n           {PNG_C}")

OUT.write_text(json.dumps(dict(
    population=dict(blocks=n_blocks, comps=len(comp_rows), endpoints=tot_ep),
    e1=dict(ep_classes), e2=dict(n=len(taper_recs),
                                 run_med=pct(runs, 50), run_p75=pct(runs, 75),
                                 d_crest_med=pct(dc, 50), d_ground_med=pct(dg, 50),
                                 recs=taper_recs),
    e3=ring_recs, e4=comp_rows), indent=0))
print(f"artifacts -> {OUT}")
