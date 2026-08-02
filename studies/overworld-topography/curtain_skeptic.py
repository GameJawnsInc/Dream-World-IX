"""C2 SKEPTIC -- independent adversarial re-measurement of the CURTAIN GRAMMAR claims.

Re-measures every C2.* claim by a method deliberately DIFFERENT from the C2 instrument
(curtain_uv.py). Differences, by design:

  * EXACT integer arithmetic everywhere: verts are verified to sit on the 1/256 grid and
    uvs on the 1/1024 texel grid, so positions snap to ints (x*256) and uvs to texel ints
    (u*1024). No 0.01/0.001 float rounding, no 1e-4 uv thresholds -- uv continuity is
    exact texel equality at exactly-identical snapped positions.
  * Curtain detector: |ny|/|n| <= 0.10 on the raw geometric normal (covers both the
    exact-zero-plan-area tris, where ny == 0 identically, and the near-vertical stragglers)
    -- not the instrument's (|ny|<=0.05 OR plan_area < 1e-3*area3D) pair. Exact-zero
    counts are reported separately so detector sensitivity is visible.
  * Top/bottom vertex classification is COLUMN-based: verts of a curtain tri are grouped
    by exact plan key; in a 2-vert column the higher vert is TOP, the lower BOTTOM;
    singletons classify against the 2-vert column's midpoint (per tri), not a global
    mid-height split of all three verts.
  * u-rate (du/run) is sampled on WELDED top rim edges only -- curtain edges with plan
    extent whose both endpoints are position-identical with a non-degenerate surface tri
    of the same family -- not on "2 verts within 0.05 of tri ymax" edges.
  * Winding is judged against the WELDED surface neighbour (fallback: nearest surface
    centroid), not the nearest surface-37 centroid outright.
  * Rim census re-derived from scratch: boundary edges of the non-degenerate family
    patch (exact 3D edge keys, multiplicity 1) classified curtain-sealed / direct-weld /
    block-border / open.

Read-only vs stock disc-1. Artifact -> out/curtain_skeptic.json.
Regenerate: py -X utf8 curtain_skeptic.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X  # noqa: E402

OUT = Path(__file__).with_name("out") / "curtain_skeptic.json"
DONOR = (15, 14)
NY_CURTAIN = 0.10          # my near-vertical threshold (context: NEAR-VERTICAL is 0.2)
BORDER_EPS = 0.5           # world units from block-local plan edge
WALL_CLASSES = {49, 50, 58}


def snap3(v):
    return (round(v[0] * 256), round(v[1] * 256), round(v[2] * 256))


def snap_plan(v):
    return (round(v[0] * 256), round(v[2] * 256))


def texel(q):
    return (round(q[0] * 1024), round(q[1] * 1024))


class Tri:
    __slots__ = ("t", "verts", "uvs", "raw", "topo", "keys3", "pkeys", "ny_ratio",
                 "plan_area", "ymin", "ymax", "curtain")

    def __init__(self, t, verts, uvs, raw, topo):
        self.t = t
        self.verts = verts
        self.uvs = uvs
        self.raw = raw
        self.topo = topo
        self.keys3 = [snap3(v) for v in verts]
        self.pkeys = [snap_plan(v) for v in verts]
        a, b, c = verts
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        wx, wy, wz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx = uy * wz - uz * wy
        ny = uz * wx - ux * wz
        nz = ux * wy - uy * wx
        L = math.sqrt(nx * nx + ny * ny + nz * nz)
        self.ny_ratio = abs(ny) / L if L > 0 else None
        self.plan_area = abs(ux * wz - uz * wx) / 2
        ys = [v[1] for v in verts]
        self.ymin, self.ymax = min(ys), max(ys)
        self.curtain = self.ny_ratio is not None and self.ny_ratio <= NY_CURTAIN

    def plan_normal(self):
        a, b, c = self.verts
        ux, uz = b[0] - a[0], b[2] - a[2]
        wx, wz = c[0] - a[0], c[2] - a[2]
        uy, wy = b[1] - a[1], c[1] - a[1]
        nx = uy * wz - uz * wy
        nz = ux * wy - uy * wx
        L = math.hypot(nx, nz)
        return (nx / L, nz / L) if L > 0 else None

    def plan_centroid(self):
        return (sum(v[0] for v in self.verts) / 3, sum(v[2] for v in self.verts) / 3)

    def top_bottom(self):
        """Column-based split -> (top list, bottom list) of corner indices."""
        cols = defaultdict(list)
        for i, pk in enumerate(self.pkeys):
            cols[pk].append(i)
        top, bot = [], []
        pair_mids = []
        for idxs in cols.values():
            if len(idxs) >= 2:
                ys = sorted(idxs, key=lambda i: self.verts[i][1])
                bot.append(ys[0])
                top.append(ys[-1])
                if len(ys) == 3:      # fully vertical column of 3 (should not happen)
                    bot.append(ys[1])
                pair_mids.append((self.verts[ys[0]][1] + self.verts[ys[-1]][1]) / 2)
        mid = sum(pair_mids) / len(pair_mids) if pair_mids else (self.ymin + self.ymax) / 2
        for idxs in cols.values():
            if len(idxs) == 1:
                i = idxs[0]
                (top if self.verts[i][1] > mid else bot).append(i)
        return top, bot


def load_block(bx, by):
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except ValueError:
        return None
    fi = bm.flat_index
    tris = []
    for t in range(len(fi) // 3):
        idx = [fi[3 * t + k] for k in range(3)]
        raw = int(round(bm.tangents[idx[0]][0]))
        topo = X.decode_id(raw)["topograph"]
        verts = [tuple(bm.verts[i]) for i in idx]
        uvs = [tuple(bm.uvs[i][:2]) for i in idx]
        tris.append(Tri(t, verts, uvs, raw, topo))
    return tris


def near_border(key3):
    x, z = key3[0] / 256.0, key3[2] / 256.0
    return (x <= BORDER_EPS or x >= 64.0 - BORDER_EPS or
            z >= -BORDER_EPS or z <= -64.0 + BORDER_EPS)


def edge3_keys(tri):
    for i, j in ((0, 1), (1, 2), (2, 0)):
        yield frozenset((tri.keys3[i], tri.keys3[j])), (i, j)


def block_indexes(tris):
    """Vert-position and 3D-edge ownership maps over non-degenerate tris + all tris."""
    pos_owner_nd = defaultdict(list)     # snap3 -> [(tri, corner)] non-degenerate only
    edge_owner_nd = defaultdict(list)    # 3D edge -> [tri] non-degenerate only
    edge_owner_cur = defaultdict(list)   # 3D edge -> [tri] curtains only
    for tr in tris:
        if tr.curtain:
            for ek, _ in edge3_keys(tr):
                if len(ek) == 2:
                    edge_owner_cur[ek].append(tr)
        else:
            for i, k in enumerate(tr.keys3):
                pos_owner_nd[k].append((tr, i))
            for ek, _ in edge3_keys(tr):
                if len(ek) == 2:
                    edge_owner_nd[ek].append(tr)
    return pos_owner_nd, edge_owner_nd, edge_owner_cur


# ---------------------------------------------------------------- per-family scan

def family_scan(all_blocks, fam):
    """Map-wide stats for one topograph family's curtains."""
    res = dict(fam=fam, n_curtain=0, n_zero_area=0, blocks=set(), drops=[],
               v_top=Counter(), v_bot=Counter(), u_all=Counter(),
               pin_ok=0, pin_bad=[], below_topo=Counter(), above_topo=Counter(),
               uv_cont=0, uv_disc=0,
               weld_du_run=[], weld_runs=[],
               seam_same_u=0, seam_diff_u=0,
               wind_out=0, wind_in=0, wind_na=0,
               bot_twin=0, bot_total=0)
    for (bx, by), tris in all_blocks.items():
        curtains = [tr for tr in tris if tr.curtain and tr.topo == fam]
        if not curtains:
            continue
        res["blocks"].add((bx, by))
        pos_nd, edge_nd, _ = block_indexes(tris)
        surf_cent = [tr.plan_centroid() for tr in tris
                     if not tr.curtain and tr.topo == fam]
        top_pos_fam = set()
        bot_pos_fam = []
        vert_edge_owner = defaultdict(list)   # vertical edge (same plan key) -> owners
        for tr in curtains:
            res["n_curtain"] += 1
            if tr.plan_area == 0:
                res["n_zero_area"] += 1
            drop = tr.ymax - tr.ymin
            res["drops"].append(drop)
            top, bot = tr.top_bottom()
            vt = [texel(tr.uvs[i])[1] for i in top]
            vb = [texel(tr.uvs[i])[1] for i in bot]
            for v in vt:
                res["v_top"][v] += 1
            for v in vb:
                res["v_bot"][v] += 1
            for i in range(3):
                res["u_all"][texel(tr.uvs[i])[0]] += 1
            if fam in (36, 37) :
                if all(v == 930 for v in vt) and all(v == 961 for v in vb):
                    res["pin_ok"] += 1
                else:
                    res["pin_bad"].append(dict(block=[bx, by], t=tr.t, v_top=vt, v_bot=vb))
            for i in top:
                top_pos_fam.add(tr.keys3[i])
            for i in bot:
                bot_pos_fam.append(tr.keys3[i])
            # uv continuity vs any non-degenerate tri at identical positions
            for i in range(3):
                for nb, j in pos_nd.get(tr.keys3[i], ()):
                    if texel(tr.uvs[i]) == texel(nb.uvs[j]):
                        res["uv_cont"] += 1
                    else:
                        res["uv_disc"] += 1
            # 3D edge co-owners above / below
            topset, botset = set(top), set(bot)
            for ek, (i, j) in edge3_keys(tr):
                if len(ek) != 2:
                    continue
                owners = edge_nd.get(ek, ())
                if i in topset and j in topset:
                    for nb in owners:
                        res["above_topo"][nb.topo] += 1
                elif i in botset and j in botset:
                    for nb in owners:
                        res["below_topo"][nb.topo] += 1
                # vertical seams: same plan key both ends
                if tr.pkeys[i] == tr.pkeys[j]:
                    vert_edge_owner[ek].append(tr)
            # du/run on welded top edges
            for ek, (i, j) in edge3_keys(tr):
                if len(ek) != 2 or not (i in topset and j in topset):
                    continue
                if tr.pkeys[i] == tr.pkeys[j]:
                    continue
                if tr.keys3[i] in pos_nd and tr.keys3[j] in pos_nd:
                    run = math.hypot(tr.verts[i][0] - tr.verts[j][0],
                                     tr.verts[i][2] - tr.verts[j][2])
                    if run > 0:
                        du = abs(tr.uvs[i][0] - tr.uvs[j][0])
                        res["weld_du_run"].append(du / run)
                        res["weld_runs"].append(run)
            # winding vs welded/nearest surface neighbour
            pn = tr.plan_normal()
            if pn is None or not surf_cent:
                res["wind_na"] += 1
            else:
                nb_tris = [nb for k in tr.keys3 for nb, _ in pos_nd.get(k, ())
                           if nb.topo == fam]
                cx, cz = tr.plan_centroid()
                if nb_tris:
                    sx, sz = min((nb.plan_centroid() for nb in nb_tris),
                                 key=lambda c: (c[0] - cx) ** 2 + (c[1] - cz) ** 2)
                else:
                    sx, sz = min(surf_cent,
                                 key=lambda c: (c[0] - cx) ** 2 + (c[1] - cz) ** 2)
                d = pn[0] * (cx - sx) + pn[1] * (cz - sz)
                if d > 0:
                    res["wind_out"] += 1
                elif d < 0:
                    res["wind_in"] += 1
                else:
                    res["wind_na"] += 1
        # vertical-seam u agreement between distinct curtain tris
        for ek, owners in vert_edge_owner.items():
            uniq = list({id(o): o for o in owners}.values())
            for a in range(len(uniq)):
                for b in range(a + 1, len(uniq)):
                    ta, tb = uniq[a], uniq[b]
                    for k in ek:
                        ua = [texel(ta.uvs[i])[0] for i in range(3) if ta.keys3[i] == k]
                        ub = [texel(tb.uvs[i])[0] for i in range(3) if tb.keys3[i] == k]
                        for x1 in ua:
                            for x2 in ub:
                                if x1 == x2:
                                    res["seam_same_u"] += 1
                                else:
                                    res["seam_diff_u"] += 1
        # bottom-vert plan twins (unique bottom positions in this block)
        top_plan = {(k[0], k[2]) for k in top_pos_fam}
        for k in set(bot_pos_fam):
            res["bot_total"] += 1
            if (k[0], k[2]) in top_plan:
                res["bot_twin"] += 1
    return res


def rim_census(all_blocks, fam):
    """Classify every boundary 3D edge of the non-degenerate fam patch, map-wide."""
    cls = Counter()
    open_edges = []
    for (bx, by), tris in all_blocks.items():
        surf = [tr for tr in tris if not tr.curtain and tr.topo == fam]
        if not surf:
            continue
        count = Counter()
        for tr in surf:
            for ek, _ in edge3_keys(tr):
                if len(ek) == 2:
                    count[ek] += 1
        boundary = [ek for ek, c in count.items() if c == 1]
        _, edge_nd, edge_cur = block_indexes(tris)
        for ek in boundary:
            if edge_cur.get(ek):
                cls["curtain"] += 1
            elif any(nb.topo != fam for nb in edge_nd.get(ek, ())):
                cls["weld"] += 1
            elif all(near_border(k) for k in ek):
                cls["border"] += 1
            else:
                cls["open"] += 1
                open_edges.append(dict(block=[bx, by],
                                       edge=[[k[0] / 256, k[1] / 256, k[2] / 256]
                                             for k in ek]))
    return cls, open_edges


# ---------------------------------------------------------------- donor deep-dive

def donor_report(tris):
    fam = 37
    forest = [tr for tr in tris if tr.topo == fam]
    curtains = [tr for tr in forest if tr.curtain]
    surface = [tr for tr in forest if not tr.curtain]
    pos_nd, edge_nd, _ = block_indexes(tris)
    top_y, bot_y, drops = [], [], []
    top_edges, bot_edges = [], []
    for tr in curtains:
        top, bot = tr.top_bottom()
        top_y += [tr.verts[i][1] for i in top]
        bot_y += [tr.verts[i][1] for i in bot]
        drops.append(tr.ymax - tr.ymin)
        ts, bs = set(top), set(bot)
        for ek, (i, j) in edge3_keys(tr):
            if len(ek) != 2 or tr.pkeys[i] == tr.pkeys[j]:
                continue
            if i in ts and j in ts:
                top_edges.append((ek, tr, i, j))
            elif i in bs and j in bs:
                bot_edges.append((ek, tr, i, j))
    # plan-owner census on top (rim) edges
    plan_edge_owner = defaultdict(set)
    for tr in tris:
        for ek, (i, j) in edge3_keys(tr):
            pk = frozenset((tr.pkeys[i], tr.pkeys[j]))
            if len(pk) == 2:
                plan_edge_owner[pk].add(tr.t)
    rim_plan = {frozenset((tr.pkeys[i], tr.pkeys[j])) for ek, tr, i, j in top_edges}
    owner_hist = Counter(len(plan_edge_owner[pk]) for pk in rim_plan)
    # 3D co-owners
    above = Counter()
    for ek, tr, i, j in top_edges:
        for nb in edge_nd.get(ek, ()):
            above[nb.topo] += 1
    below = Counter()
    n_weld = n_border = n_open = 0
    for ek, tr, i, j in bot_edges:
        owners = edge_nd.get(ek, ())
        if owners:
            n_weld += 1
            for nb in owners:
                below[nb.topo] += 1
        elif all(near_border(k) for k in ek):
            n_border += 1
        else:
            n_open += 1
    return dict(
        forest_total=len(forest), curtains=len(curtains), surface=len(surface),
        curtain_zero_area=sum(1 for tr in curtains if tr.plan_area == 0),
        raw_ids_curtain=sorted({tr.raw for tr in curtains}),
        raw_ids_surface=sorted({tr.raw for tr in surface}),
        top_y=[round(min(top_y), 3), round(max(top_y), 3)],
        bot_y=[round(min(bot_y), 3), round(max(bot_y), 3)],
        drops=[round(min(drops), 3), round(max(drops), 3),
               round(sorted(drops)[len(drops) // 2], 3)],
        n_top_edges=len(top_edges), n_bot_edges=len(bot_edges),
        rim_plan_edges=len(rim_plan), rim_plan_owner_hist=dict(owner_hist),
        above_topo=dict(above), below_topo=dict(below),
        bot_weld=n_weld, bot_border=n_border, bot_open=n_open,
        n_top_verts=len(top_y), n_bot_verts=len(bot_y),
        v_top_hist=dict(Counter(round(v) for v in
                                [texel(tr.uvs[i])[1] for tr in curtains
                                 for i in tr.top_bottom()[0]])),
        v_bot_hist=dict(Counter(round(v) for v in
                                [texel(tr.uvs[i])[1] for tr in curtains
                                 for i in tr.top_bottom()[1]])),
    )


def pct(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    return s[min(len(s) - 1, int(p * len(s)))]


def summarize(res):
    drops = res["drops"]
    out = dict(fam=res["fam"], n_curtain=res["n_curtain"],
               n_zero_area=res["n_zero_area"], n_blocks=len(res["blocks"]),
               drops=[round(min(drops), 3), round(max(drops), 3),
                      round(sorted(drops)[len(drops) // 2], 3)] if drops else None,
               v_top=dict(res["v_top"].most_common(6)),
               v_bot=dict(res["v_bot"].most_common(6)),
               u_min=min(res["u_all"]), u_max=max(res["u_all"]),
               u_top3=res["u_all"].most_common(3),
               u_samples=sum(res["u_all"].values()),
               pin_ok=res["pin_ok"], pin_bad=res["pin_bad"][:6],
               n_pin_bad=len(res["pin_bad"]),
               above_topo=dict(res["above_topo"]), below_topo=dict(res["below_topo"]),
               uv_cont=res["uv_cont"], uv_disc=res["uv_disc"],
               wind_out=res["wind_out"], wind_in=res["wind_in"],
               wind_na=res["wind_na"],
               seam_same_u=res["seam_same_u"], seam_diff_u=res["seam_diff_u"],
               bot_twin=res["bot_twin"], bot_total=res["bot_total"])
    dr = res["weld_du_run"]
    out["weld_edges"] = len(dr)
    if dr:
        out["du_run_med"] = round(pct(dr, 0.5), 5)
        out["du_run_p10"] = round(pct(dr, 0.10), 5)
        out["du_run_p90"] = round(pct(dr, 0.90), 5)
        out["run_med"] = round(pct(res["weld_runs"], 0.5), 3)
        out["run_max"] = round(max(res["weld_runs"]), 3)
    return out


def addendum(all_blocks):
    """Follow-up checks that settled the three claim discrepancies.

    (a) vertex-level pin truth: a curtain tri fails the (930,961) pin iff ANY of its
        v texels is off-pin -- immune to top/bottom classification artifacts at
        stairstep rims (where a mid-height or column split mislabels the shared vert).
    (b) seam continuity three ways: strict vertical (zero plan extent) inter-tri edges
        vs the dy>=0.5 family that also admits within-quad diagonals -- the latter
        reproduces the C2 instrument's 77% figure, the former is the true seam number.
    (c) donor tile rows for the band-continuation cross-check.
    """
    out = {}
    for fam in (36, 37):
        bad = []
        for (bx, by), tris in all_blocks.items():
            for tr in tris:
                if tr.curtain and tr.topo == fam:
                    vs = sorted(texel(q)[1] for q in tr.uvs)
                    if any(v not in (930, 961) for v in vs):
                        bad.append(dict(block=[bx, by], t=tr.t, v=vs))
        out[f"fam{fam}_offpin_tris"] = bad
    counts = dict(strict_edge=[0, 0], strict_vert=[0, 0], dy_any_vert=[0, 0],
                  diag_edges=0)
    for tris in all_blocks.values():
        curt = [tr for tr in tris if tr.curtain and tr.topo == 37]
        owner = defaultdict(list)
        for tr in curt:
            for ek, _ in edge3_keys(tr):
                if len(ek) == 2:
                    owner[ek].append(tr)
        for ek, lst in owner.items():
            if len(lst) < 2:
                continue
            ka, kb = tuple(ek)
            planlen = math.hypot(ka[0] - kb[0], ka[2] - kb[2])
            dy = abs(ka[1] - kb[1]) / 256.0
            if planlen > 0 and dy >= 0.5:
                counts["diag_edges"] += 1
            for a in range(len(lst)):
                for b in range(a + 1, len(lst)):
                    ta, tb = lst[a], lst[b]
                    if ta is tb:
                        continue
                    agree = True
                    for k in ek:
                        ua = {texel(ta.uvs[i])[0] for i in range(3) if ta.keys3[i] == k}
                        ub = {texel(tb.uvs[i])[0] for i in range(3) if tb.keys3[i] == k}
                        same = ua == ub
                        if not same:
                            agree = False
                        if planlen == 0:
                            counts["strict_vert"][0 if same else 1] += 1
                        if dy >= 0.5:
                            counts["dy_any_vert"][0 if same else 1] += 1
                    if planlen == 0:
                        counts["strict_edge"][0 if agree else 1] += 1
    out["seam_37"] = counts
    tris = all_blocks[DONOR]
    for name, fam, deg in (("surface37", 37, False), ("ground0", 0, False)):
        vv = [texel(q)[1] for tr in tris if tr.curtain == deg and tr.topo == fam
              for q in tr.uvs]
        out[f"donor_{name}_tile_rows_v"] = sorted({(v - 16) // 32 for v in vv})
    out["donor_curtain_tile_rows_v"] = sorted(
        {(texel(q)[1] - 16) // 32 for tr in tris
         if tr.curtain and tr.topo == 37 for q in tr.uvs})
    return out


def main():
    blocks = X.list_blocks(disc=1)
    all_blocks = {}
    n_deg3d = 0
    for bx, by in blocks:
        tris = load_block(bx, by)
        if tris:
            all_blocks[(bx, by)] = tris
            n_deg3d += sum(1 for tr in tris if tr.ny_ratio is None)
    print(f"blocks loaded: {len(all_blocks)}  (3D-degenerate tris skipped: {n_deg3d})")

    # global curtain census by topograph
    census = Counter()
    census_zero = Counter()
    for tris in all_blocks.values():
        for tr in tris:
            if tr.curtain:
                census[tr.topo] += 1
                if tr.plan_area == 0:
                    census_zero[tr.topo] += 1
    print("curtain census (|ny|/|n|<=0.1):", dict(census.most_common()))
    print("  of which exact-zero plan area:", dict(census_zero.most_common()))

    donor = donor_report(all_blocks[DONOR])
    print("donor:", json.dumps(donor, indent=1))

    fam_out = {}
    for fam in (37, 36, 38, 59, 0):
        r = family_scan(all_blocks, fam)
        fam_out[fam] = summarize(r)
        print(f"fam {fam}:", json.dumps(fam_out[fam], default=str)[:600])

    rim, open_edges = rim_census(all_blocks, 37)
    print("rim census fam37:", dict(rim), "open:", open_edges[:5])

    extra = addendum(all_blocks)
    print("addendum:", json.dumps(extra, default=str)[:800])

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(dict(
        detector=dict(ny_ratio_max=NY_CURTAIN, border_eps=BORDER_EPS),
        n_blocks=len(all_blocks),
        census=dict(census), census_zero_area=dict(census_zero),
        donor=donor,
        families={str(k): v for k, v in fam_out.items()},
        rim_census_37=dict(rim), rim_open_edges=open_edges,
        addendum=extra,
    ), indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
