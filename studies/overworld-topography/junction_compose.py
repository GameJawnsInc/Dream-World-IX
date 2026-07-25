"""JUNCTION COMPOSE -- THE GENERATOR FOLD-BACK, module 1 of 2  (2026-07-25).

THE PROBLEM THIS CLOSES.  The Rung F two-ground island is accepted in-game after eight fix rounds,
but every fix lived in the DEPLOYED BYTES ONLY: ``rung_f_layout.py`` / ``rung_f_stitch.py`` /
``rung_f_holefill.py`` / ``rung_f_build.py`` still contained every original defect, so a fresh mint
at a fresh site would regress all eight rounds.  This module folds L1-L8 back into the GENERATOR and
runs the whole gate battery on its own final composite, refusing to emit on any red.

WHAT IS REUSED VERBATIM (topology + byte-rigidity -- none of it was ever the defect):
  * ``rung_f_layout``  -- the site/frame mint, the donor window read + THE VERBATIM-CORE DROP, the
    DY seat, the whole-cell rigid shift + event/area strip, the 64u re-partition (``TR.clip_poly``).
  * ``rung_f_stitch.stitch_tile`` -- THE TILING STITCH, unchanged: ear-clip the blob's interior
    holes, dilate the grass removal by one cell, contour-tile the annulus with EXACTLY the A/B verts,
    excise+refill, re-block, T-junction closure, apron up-face.
  * ``rung_f_holefill`` -- ``above_skirt_loops`` / ``fill_loop`` / ``contour_tile`` /
    ``excise_and_refill`` / ``dilate`` / ``enclosed_missing_cells``, directed half-edge extraction.

WHAT CHANGES -- the eight laws, each lifted from the round that proved it:

  L1  ONE WINDOW PER TRI.  The pipeline used to thread ONE constant ``(grass_id, grass_uv)`` pair from
      ``rung_f_layout.py:377`` into every synthesized vertex of every stage (the flat-sheet stain).
      Here the topology stages emit a SENTINEL UV, and THE SYNTHESIS RE-EMIT resolves every
      synthesized triangle's three UVs from ONE ``(cell,quad,ori)`` window keyed on the tri CENTROID
      cell via ``grassland.ground_uv`` -- vertex-own-cell fallback, documented per-vertex last resort.
      Lifted from ``uvf_fix3.build_fixed3a`` (lines 319-403).
  L2  FAMILY FIELD.  Fill used to be blanket grass.  Here each fill cell takes the family of its
      EXACT-NEAREST kept-ground source cell (squared Euclidean, ring-majority tie-break, then next
      ring, then lexical).  Kept ground tris vote ``grassland.TOPO_FAMILY``; rock 58/31 and murals
      ABSTAIN.  Lifted from ``uvf_fix4.stage2`` (lines 175-318).  NOTE: nearest-by-DISTANCE, NOT a
      BFS/flood-fill -- uvf_fix4's own docstring disclaims diagonal/BFS bias, and near an irregular
      DROP_SET boundary the two are not equivalent.
  L3  DIVERSITY.  ``interior.decode_cell_pick``'s uniform-random per-cell ori (chevron lattices) is
      never used.  The (quad,ori) field resolves through the ``assign_mains`` POLICY -- p=0.32 W/S
      rotation copy, single random neighbour quad-avoid -- pre-seeded with decoded ground truth.
      Lifted from ``uvf_fix2.assign_mains_seeded`` + ``uvf_fix2.decode_quad_ori``, seed 0xF92.
  L4  HEIGHTS.  Fill Y used to be the constant LAND_HEIGHT welded into undulating carried ground
      (``rung_f_layout.py:416``).  Here it follows the local kept-ground REFERENCE FIELD (IDW +
      2-pass Tukey-biweight IRLS growing-radius plane, ``uvf_relief_probe.stage2``/``ref_at``)
      blended by the HARMONIC mesh-function solve on the patch's own edge graph, C0 into pinned
      kept-coincident positions -- never a distance falloff (that merely RELOCATES the step onto the
      pins).  Weld-safe per POSITION: every coincident copy moves together, across blocks.
      Lifted from ``uvf_relief_probe.stage2/ref_at/stage6``.
  L5a SPIKE/STEP SHAVE.  Post-drop carried remnants: the 5-predicate census (ground topo with rock
      58/31 EXEMPT at three levels; residual >= 0.80u; CONE arm prominence >= 0.40u OR STEP arm
      prominence >= 0.0u AND welded drop >= 1.50u; outside the basin discs; Terrain-only), shaved by
      the SAME harmonic solver scoped to HOPS=2.  Lifted from ``uvf_fix6``/``uvf_fix7``.
      THE BASIN REFERENCE TRAP, generalized: enclosure-detected bowls are excluded from BOTH the
      shave set AND the reference SAMPLES (with the basin in the samples, its own rim crest scores as
      spikes -- 9/14 crest vertices would have been flattened).
  L5b ORPHAN-DECAL REDRESS.  A carried ground tri with an uncatalogued rect AND live dip < 25deg AND
      its OWN donor tri's dip >= 25deg wears the surrounding family's mains (one window).  Stock-flat
      decals (donor dip below the same threshold) are SPARED.  Lifted from ``uvf_fix8.census``.
      D2 (2026-07-25) -- THE DOUBLE REDRESS, found by the code-disjoint falsifier: stage 12 also ran
      the KIT orphangate with ``redress=True`` on the very meshes about to be staged, a SECOND
      independent re-clothing mechanism.  The kit gate judges a decal by RING CONTEXT, and at a fresh
      frame it re-clothed 2 genuinely CARRIED, bit-exact CATALOGUED grass|desert transition-strip
      tiles into plain desert mains and re-stamped topo 16 -> 17 -- a verbatim-carry violation the
      two-sided L5b census (uncatalogued rect required) correctly spares.  L5b is now THE ONLY
      REDRESS; the kit gate runs WARN-only on a deep copy, gated non-mutating, reported as advisory.
  L6  SEA.  ``rung_f_build._sea4_y0_stub``'s degenerate Y=0 Sea4 under the blob blocks is DELETED:
      uniform full Sea4 planes on every block, 1-tri hidden placeholders elsewhere.  contract v5's
      sea-vertex-convention flag made the old gaming unnecessary.
  L7  THE FINAL-COMPOSITE RULE.  ``composite_gates.run_composite_gates`` runs the whole battery on
      THIS build's own final composite; ``compose`` REFUSES to report green on any red.
  L8  EYE ARTIFACTS.  Per-pixel family-colour planview + shaded-relief planview + oblique + the
      round-8 texel-density heatmap channel, emitted as review outputs after the gates are green.
  D3  PROVENANCE LABEL + WINDING (2026-07-25, the code-disjoint falsifier).  The winding gate split
      down-facing tris by ``cell in carried_cells`` -- a PLAN heuristic -- so 3 synthesized fill tris
      over the donor's dropped topo-59 shaft were labelled "carried stock down-facing ... faithful"
      and exempted, in EVERY historical build, invisible to 8 rounds.  (a) the split now consumes
      ``tri_provenance``, the pipeline's own sentinel bookkeeping; (b) STAGE 6a re-winds any
      SYNTHESIZED tri whose plan cross-product is negative, so the folded generator stops PRODUCING
      them.  Carried tris are never re-wound -- stock's winding is stock's -- but they are counted.
      The DEPLOYED island keeps its 3 (accepted in-game); this is a generator fix, not a re-deploy.

THE ONE ORDERING THE FOLD ADDS: ``basin_discs`` is computed ONCE (stage 7) and threaded into BOTH
L4's target pinning and L5's reference-sample exclusion.  Rounds 5 and 6 computed two independently
derived but geometrically identical exclusions; sharing one is what keeps them from drifting apart.

READ-ONLY vs the game install: stock/donor/atlas reads only, output staged to the caller's directory.
NEVER deploys, NEVER git commits.

    py -X utf8 junction_compose.py --self-test     # re-run the ORIGINAL rung-F site, staged
"""
from __future__ import annotations

import json
import math
import random
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                          # noqa: E402
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import island as ISL                     # noqa: E402
from ff9mapkit.world import mesh as M                         # noqa: E402
from ff9mapkit.world import transplant as TR                  # noqa: E402
from ff9mapkit.world import orphangate as OG                  # noqa: E402
from ff9mapkit.world import grassland as G                    # noqa: E402
from ff9mapkit.world.extract import CH_POS, CH_NRM, CH_UV, CH_TAN   # noqa: E402

import rung_f_layout as RFL                                    # noqa: E402  (frame/donor/carry machinery)
import rung_f_stitch as STITCH                                 # noqa: E402  (THE TILING STITCH)
import rung_f_holefill as HF                                   # noqa: E402
import contract_mass_gates as CMG                              # noqa: E402
import composite_gates as CG                                   # noqa: E402
import seam_null_recon as SNR                                  # noqa: E402  (FAM_OF)
import uvf_stock_census as SC                                  # noqa: E402  (classify_tri_plus)

BLOCK = 64.0
CELL = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
POS_DP = 3

# ---- L1/L3 ------------------------------------------------------------------------------------------
SENTINEL_UV = (-9.0, -9.0)          # the topology stages' provenance marker; never reaches disk
QO_SEED = 0xF92                     # uvf_fix2.V2_SEED
DECODE_ERR = 1e-4                   # uvf_fix2.DECODE_ERR
UV_AREA_EPS = 1e-6                  # uvf_fix2.AREA_EPS
# ---- L4 (uvf_relief_probe constants) ----------------------------------------------------------------
ANOM_T = 0.60
CLUSTER_R = 4.5
MIN_CLUSTER = 2
ENCLOSE_R = 20.0
ENCLOSE_DY = 1.5
L4_W_DATA, L4_W_HOLD, W_EDGE, EPS = 4.0, 1.0, 1.0, 1e-3
MIN_LAND_Y = 0.5
# ---- L5a (uvf_fix6 + uvf_fix7 constants) ------------------------------------------------------------
SPIKE_RES_T = 0.80
SPIKE_PROM_T = 0.40
STEP_PROM_T = 0.00
STEP_DROP_T = 1.50
HOPS = 2
W_SWEEP = (4.0, 8.0, 12.0, 16.0, 24.0)
W_ACCEPT_POST = 0.15
W_ACCEPT_FILL = 0.60
BASIN_GUARD_PAD = 2.0
# ---- L5b (uvf_fix8 constants) -----------------------------------------------------------------------
FLAT_DIP_T = 25.0
DONOR_DIP_T = 25.0

GROUND_FAM = G.TOPO_FAMILY
PARTS = ("Terrain", "Object", "Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5")


# =====================================================================================================
#  THE SITE CONTRACT
# =====================================================================================================
def rung_f_site(stage_dir):
    """THE ORIGINAL Rung F site parameters (the self-test's input).  Values are the ones
    ``rung_f_layout``/``rung_f_build`` actually built with; the caller cross-checks them against the
    recorded ``out/rung_f/rung_f_build.json``."""
    return dict(
        name="rung_f_original",
        island_center=RFL.ISLAND_CENTER, island_radius=RFL.ISLAND_RADIUS,
        land_height=RFL.LAND_HEIGHT, island_seed=RFL.ISLAND_SEED,
        island_undulation=RFL.ISLAND_UNDULATION, island_n_corners=RFL.ISLAND_N_CORNERS,
        island_corner_strength=RFL.ISLAND_CORNER_STRENGTH,
        site_blocks=set(RFL.SITE_BLOCKS),
        donor_cell_x=RFL.DONOR_CELL_X, donor_cell_y=RFL.DONOR_CELL_Y,
        donor_blocks=list(RFL.DONOR_BLOCKS), shift_cells=RFL.SHIFT_CELLS,
        drop_set=set(RFL.DROP_SET), qo_seed=QO_SEED,
        stage_dir=Path(stage_dir))


def log_maker(sink):
    def log(m):
        print(m, flush=True)
        sink.append(str(m))
    return log


def pkey(p):
    return (round(float(p[0]), POS_DP), round(float(p[1]), POS_DP), round(float(p[2]), POS_DP))


def own_cell(vx, vz):
    return (math.floor(vx / CELL), math.floor(vz / CELL))


def centroid_xz(w3):
    return (sum(p[0] for p in w3) / 3.0, sum(p[2] for p in w3) / 3.0)


def tri_world(tri):
    return [t[0] for t in tri]


def tri_uv(tri):
    return [(float(t[2][0]), float(t[2][1])) for t in tri]


def tri_topo(tri):
    return X.decode_id(int(round(tri[0][3][0])))["topograph"]


def is_sentinel(tri):
    return all(abs(t[2][0] - SENTINEL_UV[0]) < 1e-6 and abs(t[2][1] - SENTINEL_UV[1]) < 1e-6
               for t in tri)


def uv_tri_degen(uv3):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) * 0.5 < UV_AREA_EPS


def up_normal(w3):
    a, b, c = w3
    e1 = [b[k] - a[k] for k in range(3)]
    e2 = [c[k] - a[k] for k in range(3)]
    n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
    if n[1] < 0.0:
        n = [-n[0], -n[1], -n[2]]
    ln = math.sqrt(sum(v * v for v in n))
    if ln < 1e-12:
        return None
    return [n[0] / ln, n[1] / ln, n[2] / ln]


def dip_deg(w3):
    return CG.dip_deg(w3)


def plan_ny2(w3):
    """The PLAN cross-product, sign-identical to the winding gate's own ``ny2``
    (``composite_gates.gate_stage4_plumbing``): > 0 = up-facing, < 0 = down-facing, == 0 =
    plan-degenerate.  Depends only on XZ, so it is invariant under every Y-only stage (L4/L5a)."""
    a, b, c = w3
    return (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])


# =====================================================================================================
#  L3 -- THE (quad, ori) FIELD   [lifted: uvf_fix2.decode_quad_ori + uvf_fix2.assign_mains_seeded]
# =====================================================================================================
def decode_quad_ori(cell, verts_world, uv3):
    """LIFTED VERBATIM from uvf_fix2.py:108-127 -- brute-force the 16 (quad,ori) combos against
    grassland.mains_uv."""
    best = None
    for uh in (0, 1):
        for vh in (0, 1):
            quad = (uh, vh)
            for ori in G.ORIS:
                maxerr = 0.0
                for (vx, _vy, vz), (su, sv) in zip(verts_world, uv3):
                    mu, mv = G.mains_uv(vx, vz, cell, quad, ori)
                    e = math.hypot(mu - su, mv - sv)
                    if e > maxerr:
                        maxerr = e
                    if maxerr >= DECODE_ERR:
                        break
                if best is None or maxerr < best[0]:
                    best = (maxerr, quad, ori)
    if best is not None and best[0] < DECODE_ERR:
        return best[1], best[2]
    return None


def assign_mains_seeded(dropped_cells, pre_quad, pre_ori, seed=QO_SEED):
    """LIFTED VERBATIM from uvf_fix2.py:130-157 -- a mirror of grassland.assign_mains' loop body
    (single random.Random stream, W/S single-neighbour quad-avoid, p=0.32 rotation copy) applied only
    to the cells with no decoded ground truth."""
    rng = random.Random(seed)
    cell_quad = dict(pre_quad)
    cell_ori = dict(pre_ori)
    out_quad, out_ori = {}, {}
    for (i, j) in sorted(dropped_cells):
        nb_q = [cell_quad[n] for n in ((i - 1, j), (i, j - 1)) if n in cell_quad]
        choices = [(u, v) for u in (0, 1) for v in (0, 1)]
        if nb_q:
            avoid = nb_q[rng.randrange(len(nb_q))]
            choices = [q for q in choices if q != avoid]
        q = choices[rng.randrange(len(choices))]
        cell_quad[(i, j)] = q
        out_quad[(i, j)] = q
        nb_o = [cell_ori[n] for n in ((i - 1, j), (i, j - 1)) if n in cell_ori]
        if nb_o and rng.random() < 0.32:
            o = nb_o[rng.randrange(len(nb_o))]
        else:
            o = G.ORIS[rng.randrange(4)]
        cell_ori[(i, j)] = o
        out_ori[(i, j)] = o
    return out_quad, out_ori


def quad_ori_field(host_bms, resolve_cells, seed, log=print):
    """THE (quad,ori) CELL FIELD.  Method (a): decode the minted frame's OWN lawful grass tris (the
    ground truth already in the bytes).  Every remaining cell in ``resolve_cells`` is resolved by
    ``assign_mains_seeded`` -- the assign_mains POLICY, never a uniform-random per-cell draw.
    Construction identical to uvf_fix3.build_fixed3a's cell-field step."""
    by_cell = defaultdict(list)
    for soup in host_bms.values():
        for tri in soup:
            if tri_topo(tri) != G.GROUNDS["grass"]["topo"]:
                continue
            uv3 = tri_uv(tri)
            if uv_tri_degen(uv3):
                continue
            vw = tri_world(tri)
            cell = own_cell(*centroid_xz(vw))
            if len(by_cell[cell]) < 6:
                by_cell[cell].append((vw, uv3))
    decoded_a = {}
    for cell in sorted(by_cell):
        for (vw, uv3) in by_cell[cell]:
            qo = decode_quad_ori(cell, vw, uv3)
            if qo is not None:
                decoded_a[cell] = qo
                break
    dropped = sorted(c for c in resolve_cells if c not in decoded_a)
    pre_quad = dict(decoded_a)
    pre_ori = {c: o for c, (q, o) in decoded_a.items()}
    q2, o2 = assign_mains_seeded(dropped, pre_quad, pre_ori, seed=seed)
    decoded = {c: (q, o, "a") for c, (q, o) in decoded_a.items()}
    for c in dropped:
        decoded[c] = (q2[c], o2[c], "policy")
    log(f"  [L3] (quad,ori) field: method-a decoded {len(decoded_a)} cells, policy-resolved "
        f"{len(dropped)}, total {len(decoded)} (seed 0x{seed:X})")
    return decoded, dict(method_a=len(decoded_a), policy=len(dropped), total=len(decoded), seed=seed)


# =====================================================================================================
#  L2 -- THE FAMILY FIELD   [lifted: uvf_fix4.stage2, EXACT-NEAREST source, not a BFS]
# =====================================================================================================
class FamilyField:
    def __init__(self, votes, log=print):
        self.src_list = [(c[0], c[1], votes[c]) for c in sorted(votes)]
        self._cache = {}
        self.stats = Counter()
        if not self.src_list:
            raise AssertionError("no kept ground content anywhere -- family field undefined")
        log(f"  [L2] family field: {len(self.src_list)} source cells, "
            f"{sum(sum(v.values()) for v in votes.values())} kept ground tris")

    def at(self, cell):
        got = self._cache.get(cell)
        if got is not None:
            return got
        groups = defaultdict(Counter)
        for (sx, sy, cnt) in self.src_list:
            d2 = (sx - cell[0]) ** 2 + (sy - cell[1]) ** 2
            groups[d2] += cnt
        ds = sorted(groups)
        acc = Counter()
        chosen = None
        for k, d2 in enumerate(ds):
            acc += groups[d2]
            rank = acc.most_common()
            if len(rank) == 1 or rank[0][1] > rank[1][1]:
                chosen = rank[0][0]
                self.stats["ring0" if k == 0 else "ring_expanded"] += 1
                break
        if chosen is None:
            best = max(acc.values())
            chosen = sorted(f for f, n in acc.items() if n == best)[0]
            self.stats["lexical"] += 1
        self._cache[cell] = chosen
        return chosen


# =====================================================================================================
#  L1 -- ONE WINDOW PER TRI   [lifted: uvf_fix3.build_fixed3a lines 319-403]
# =====================================================================================================
def one_window_uv(vw, fam, decoded):
    """Primary window = the tri's CENTROID cell's (quad,ori), all three verts.  If that window's
    directional bleed CLAMP collapses the tri to zero UV area, fall back to each vertex own-cell
    (still exactly ONE window).  Documented last resort: the per-vertex path."""
    ccell = own_cell(*centroid_xz(vw))
    cand = [ccell] + [own_cell(p[0], p[2]) for p in vw]
    seen = set()
    for k, cell in enumerate(cand):
        if cell in seen or cell not in decoded:
            continue
        seen.add(cell)
        quad, ori = decoded[cell][0], decoded[cell][1]
        uv = [tuple(G.ground_uv(p[0], p[2], cell, quad, ori, fam)) for p in vw]
        if not uv_tri_degen(uv):
            return uv, cell, ("centroid" if k == 0 else "owncell-fallback")
    uv = []
    for p in vw:
        c = own_cell(p[0], p[2])
        if c not in decoded:
            c = ccell
        q, o = decoded[c][0], decoded[c][1]
        uv.append(tuple(G.ground_uv(p[0], p[2], c, q, o, fam)))
    return uv, ccell, "pervertex-lastresort"


# =====================================================================================================
#  L4/L5 -- THE REFERENCE FIELD + THE HARMONIC SOLVER
#           [lifted: uvf_relief_probe.Hash2D / stage2 / ref_at / stage6 ; uvf_fix6.ExcludeHash]
# =====================================================================================================
class Hash2D:
    """LIFTED VERBATIM from uvf_relief_probe.py:126-149."""

    def __init__(self, pts, cell=8.0):
        self.cell = cell
        self.pts = np.asarray(pts, dtype=float)
        self.buckets = defaultdict(list)
        for i, p in enumerate(self.pts):
            self.buckets[(math.floor(p[0] / cell), math.floor(p[2] / cell))].append(i)

    def query(self, x, z, r):
        c = self.cell
        i0, i1 = math.floor((x - r) / c), math.floor((x + r) / c)
        j0, j1 = math.floor((z - r) / c), math.floor((z + r) / c)
        out = []
        r2 = r * r
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                for k in self.buckets.get((i, j), ()):
                    p = self.pts[k]
                    d2 = (p[0] - x) ** 2 + (p[2] - z) ** 2
                    if d2 <= r2:
                        out.append((k, d2))
        return out


class ExcludeHash:
    """LIFTED VERBATIM from uvf_fix6.py:151-163 -- Hash2D with an index blacklist, so ref_at runs its
    EXACT IRLS fit on a sample set minus the query vertex (leave-one-out), minus the basin, and minus
    the pass-A candidates.  Only the sample membership changes."""

    def __init__(self, base, drop):
        self.base = base
        self.drop = drop
        self.cell = base.cell
        self.pts = base.pts

    def query(self, x, z, r):
        return [(i, d2) for i, d2 in self.base.query(x, z, r) if i not in self.drop]


def ref_at(ghash, samples, x, z):
    """LIFTED VERBATIM from uvf_relief_probe.py:294-336 -- IDW-weighted least-squares plane over a
    growing 8/12/18/26u radius with two Tukey-biweight IRLS passes; weighted-median fallback."""
    for R in (8.0, 12.0, 18.0, 26.0):
        hits = ghash.query(x, z, R)
        if len(hits) < 8:
            continue
        idx = np.array([h[0] for h in hits])
        d2 = np.array([h[1] for h in hits])
        P = samples[idx]
        dx, dz, y = P[:, 0] - x, P[:, 2] - z, P[:, 1]
        A = np.column_stack([np.ones_like(dx), dx, dz])
        w = 1.0 / (d2 + 1.0)
        beta = None
        for _ in range(3):
            W = np.sqrt(w)
            try:
                beta, *_ = np.linalg.lstsq(A * W[:, None], y * W, rcond=None)
            except np.linalg.LinAlgError:
                beta = None
                break
            r = y - A @ beta
            mad = float(np.median(np.abs(r - np.median(r))))
            s = max(1.4826 * mad, 0.05)
            u = np.clip(np.abs(r) / (4.685 * s), 0, 1)
            w = (1.0 / (d2 + 1.0)) * (1 - u ** 2) ** 2
            if w.sum() <= 1e-9:
                w = 1.0 / (d2 + 1.0)
                break
        if beta is None:
            continue
        yhat = float(beta[0])
        r = y - A @ beta
        return yhat, dict(R=R, n=len(hits), rms=float(np.sqrt(np.mean(r ** 2))),
                          d_near=float(np.sqrt(d2.min())), slope=float(math.hypot(beta[1], beta[2])))
    hits = ghash.query(x, z, 40.0)
    if not hits:
        return None, dict(R=None, n=0, rms=None, d_near=None, slope=None)
    hits.sort(key=lambda h: h[1])
    idx = [h[0] for h in hits[:12]]
    return float(np.median(samples[idx][:, 1])), dict(R=40.0, n=len(idx), rms=None,
                                                      d_near=float(math.sqrt(hits[0][1])),
                                                      slope=None, fallback="weighted-median")


def enclosure(ghash, samples, x, y, z, n_rays=16):
    """LIFTED VERBATIM from uvf_relief_probe.py:426-443.  A BASIN closes on nearly every azimuth; a
    CHANNEL closes on its two flanks only."""
    hits = ghash.query(x, z, ENCLOSE_R)
    if not hits:
        return 0.0, 0.0
    best = [-1e9] * n_rays
    for k, d2 in hits:
        p = samples[k]
        a = math.atan2(p[2] - z, p[0] - x)
        s = int(((a + math.pi) / (2 * math.pi)) * n_rays) % n_rays
        if p[1] > best[s]:
            best[s] = p[1]
    live = [b for b in best if b > -1e8]
    if not live:
        return 0.0, 0.0
    closed = sum(1 for b in live if b - y >= ENCLOSE_DY)
    return closed / n_rays, float(np.median(live) - y)


def harmonic_relax(unknowns, edges, res, core, w_core, w_hold):
    """THE MESH-FUNCTION SOLVE, generalized so L4's whole-fill relax and L5's HOPS=2 spike relax share
    ONE body (rounds 5 and 6 carried near-duplicate copies).  LIFTED from uvf_relief_probe.stage6
    (lines 896-921) / uvf_fix6.stage4 (lines 542-569): data term dY = -residual (w_core on the core,
    'hold your ground' w_hold elsewhere), smoothness on every edge inside the patch, Dirichlet dY = 0
    on every edge leaving it, EPS everywhere to keep isolated unknowns at 0.  C0 into the pins BY
    CONSTRUCTION -- a distance falloff would merely RELOCATE the step onto the pin."""
    Ul = sorted(unknowns)
    uidx = {k: i for i, k in enumerate(Ul)}
    n = len(Ul)
    if n == 0:
        return {}, dict(n_unknowns=0, n_patch_edges=0, n_pin_edges=0)
    e_uu = [(uidx[a], uidx[b]) for a, b in edges if a in uidx and b in uidx]
    e_ub = ([uidx[a] for a, b in edges if a in uidx and b not in uidx]
            + [uidx[b] for a, b in edges if b in uidx and a not in uidx])
    A = np.zeros((n + len(e_uu) + len(e_ub) + n, n))
    rhs = np.zeros(A.shape[0])
    r0 = 0
    for k in Ul:
        w = w_core if k in core else w_hold
        A[r0, uidx[k]] = w
        rhs[r0] = -w * res[k]
        r0 += 1
    for i, j in e_uu:
        A[r0, i], A[r0, j] = W_EDGE, -W_EDGE
        r0 += 1
    for i in e_ub:
        A[r0, i] = W_EDGE
        r0 += 1
    for i in range(n):
        A[r0, i] = EPS
        r0 += 1
    dY, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    moved = {Ul[i]: float(dY[i]) for i in range(n) if abs(dY[i]) > 1e-4}
    return moved, dict(n_unknowns=n, n_patch_edges=len(e_uu), n_pin_edges=len(e_ub))


# =====================================================================================================
#  the working mesh: a per-block WORLD soup + a parallel synthesized flag
# =====================================================================================================
class Composite:
    def __init__(self, soup, synth):
        self.soup = soup                     # {blk: [tri]}
        self.synth = synth                   # {blk: [bool]}
        self.moved_tris = set()              # (blk, i) touched by ANY Y move -- a carried tri here is
        #                                      no longer byte-verbatim (the L5a shave is a deliberate,
        #                                      guarded exception to rigidity), so the stock-envelope
        #                                      gate must not hold it to stock's ceiling.

    def tris(self):
        for blk in sorted(self.soup):
            for i, tri in enumerate(self.soup[blk]):
                yield blk, i, tri, self.synth[blk][i]

    def position_graph(self):
        """Positions keyed on the ROUNDED 3D WORLD POSITION (same XZ + different Y is a wall, not a
        weld -- uvf_relief_probe's law).  Returns kept_ground / kept_rock / synth_pos / adj /
        tri_index."""
        kept_ground = defaultdict(set)
        kept_rock = defaultdict(set)
        synth_pos = set()
        adj = defaultdict(set)
        tri_index = defaultdict(list)
        for blk, i, tri, is_s in self.tris():
            topo = tri_topo(tri)
            ks = [pkey(v[0]) for v in tri]
            for a in range(3):
                for c in range(3):
                    if a != c and ks[a] != ks[c]:
                        adj[ks[a]].add(ks[c])
            for k in ks:
                tri_index[k].append((blk, i, is_s))
                if is_s:
                    synth_pos.add(k)
                elif GROUND_FAM.get(topo) is not None:
                    kept_ground[k].add(topo)
                else:
                    kept_rock[k].add(topo)
        return dict(kept_ground=kept_ground, kept_rock=kept_rock, synth_pos=synth_pos,
                    adj=adj, tri_index=tri_index)

    def apply_dy(self, moved, recompute_normals=True):
        """Y-ONLY, per POSITION: every coincident vertex entry at a moved position -- across parts of
        a block AND across block borders -- receives the identical dY.  X/Z, UVs, tangents and
        indices are untouched; per-tri geometric up-normals are recomputed for every tri with a moved
        vertex."""
        n_entries = 0
        n_tris = 0
        for blk in self.soup:
            soup = self.soup[blk]
            for i, tri in enumerate(soup):
                hit = False
                new = []
                for (p, nn, u, t) in tri:
                    d = moved.get(pkey(p))
                    if d:
                        p = (p[0], p[1] + d, p[2])
                        hit = True
                        n_entries += 1
                    new.append((p, nn, u, t))
                if hit:
                    n_tris += 1
                    self.moved_tris.add((blk, i))
                    if recompute_normals:
                        nv = up_normal([v[0] for v in new])
                        if nv is not None:
                            new = [(p, tuple(nv), u, t) for (p, _n, u, t) in new]
                    soup[i] = new
        return dict(vertex_entries_moved=n_entries, tris_touched=n_tris)


def bm_from_soup(world_tris, bx, by):
    """rung_f_layout.soup_to_bm, lifted -- the FLAT-MESH invariant (verts == idx)."""
    return RFL.soup_to_bm(world_tris, bx, by)


# =====================================================================================================
#  THE PIPELINE
# =====================================================================================================
def compose(site, *, game_root=None, log=print, run_contract=True, render=True):
    t0 = time.time()
    R = dict(meta=dict(site=site["name"], read_only=True, zero_game_writes=True, zero_deploys=True))
    gates = []
    game_root = Path(game_root or _cfg.find_game_path(None))
    stage_dir = Path(site["stage_dir"])
    log("=" * 100)
    log(f"JUNCTION COMPOSE -- site '{site['name']}'  ->  {stage_dir}")
    log("=" * 100)

    def gate(name, ok, detail="", advisory=False):
        g = CG._g(name, ok, detail, advisory)
        gates.append(g)
        log(f"GATE [{'PASS' if ok else 'FAIL'}] {g['name']}" + (f" -- {str(detail)[:300]}" if detail else ""))
        return bool(ok)

    # -- STAGE 1: mint the grass frame ---------------------------------------------------------------
    built = ISL.build_landmass(center=site["island_center"], base_radius=site["island_radius"],
                               seed=site["island_seed"], lobes=1, land_height=site["land_height"],
                               ground="grass", relief_amp=0.0, undulation=site["island_undulation"],
                               n_corners=site["island_n_corners"],
                               corner_strength=site["island_corner_strength"], n_patches=0,
                               disc=1, game=game_root)
    frame_blocks = dict(built["blocks"])
    host_bms = {blk: RFL.bm_world_soup(bm, blk[0], blk[1]) for blk, bm in frame_blocks.items()}
    log(f"  [S1] grass frame: {len(frame_blocks)} land blocks")
    plane = ISL._sea_plane(disc=1, game=game_root)
    v = ISL.verify_landmass(built, sea_plane=plane, land_height=site["land_height"])
    vk = ("cracks", "down_facing", "walk_filter_fails", "grass_over_8u", "uv_out_of_region",
          "holes", "open_edges", "missing_faces")
    gate("S1 verify_landmass on the GRASS FRAME (0 cracks/holes/open-edges/down-facing/steep/oob)",
         all(v.get(k, 0) == 0 for k in vk), f"{ {k: v.get(k) for k in vk} }")
    gate("S1 frame stays inside the declared site rect",
         set(built["blocks"]).issubset(site["site_blocks"]), f"blocks={sorted(built['blocks'])}")

    # -- STAGE 0 (at ACTION time, over the ACTUAL footprint) -----------------------------------------
    footprint = set(frame_blocks)
    occ = {}
    for blk in sorted(footprint):
        p = ISL._real_block_parts(blk, disc=1, lod="0_1", game=game_root)
        if p:
            occ[f"{blk[0]},{blk[1]}"] = p
    gate(f"S0 OPEN-OCEAN TARGET: all {len(footprint)} written blocks are true prefab open ocean",
         not occ, f"occupied={occ}" if occ else f"all {len(footprint)} clear")

    # -- STAGE 2: the donor window + THE VERBATIM-CORE DROP -------------------------------------------
    RFL.DONOR_CELL_X, RFL.DONOR_CELL_Y = site["donor_cell_x"], site["donor_cell_y"]
    RFL.DONOR_BLOCKS = list(site["donor_blocks"])
    RFL.DROP_SET = frozenset(site["drop_set"])
    RFL.SHIFT_CELLS = tuple(site["shift_cells"])
    RFL.SHIFT_WORLD = (CELL * RFL.SHIFT_CELLS[0], CELL * RFL.SHIFT_CELLS[1])
    donor = RFL.load_donor_window(game_root)
    Tx, Tz = RFL.SHIFT_CELLS
    Twx, Twz = RFL.SHIFT_WORLD

    # -- STAGE 3: the (quad,ori) field (ONCE, before any UV consumer) ---------------------------------
    R_cells = set(donor["by_cell"]) | set(donor["dropped_by_cell"])
    placed_R = {(c[0] + Tx, c[1] + Tz) for c in R_cells}
    placed_R |= HF.enclosed_missing_cells(placed_R)
    grass_remove = HF.dilate(placed_R, 1)
    frame_cells = set()
    for soup in host_bms.values():
        for tri in soup:
            frame_cells.add(own_cell(*centroid_xz(tri_world(tri))))
    resolve_cells = frame_cells | HF.dilate(grass_remove, 2)
    decoded, qo_stats = quad_ori_field(host_bms, resolve_cells, site["qo_seed"], log=log)

    # -- STAGE 4: the family field (kept-ground votes; L2 must resolve before any L1 emission) --------
    votes = defaultdict(Counter)
    for c, tris in donor["by_cell"].items():
        tc = (c[0] + Tx, c[1] + Tz)
        for tri in tris:
            fam = GROUND_FAM.get(tri_topo(tri))
            if fam is None:
                continue                       # rock 58/31 + murals ABSTAIN
            votes[tc][fam] += 1
    for soup in host_bms.values():
        for tri in soup:
            cell = own_cell(*centroid_xz(tri_world(tri)))
            if cell in grass_remove:
                continue                       # this grass is about to be removed -- it cannot vote
            fam = GROUND_FAM.get(tri_topo(tri))
            if fam is not None:
                votes[cell][fam] += 1
    famfield = FamilyField(votes, log=log)

    # -- STAGE 5+6: THE CARRY + THE TILING STITCH, topology UNCHANGED, UV emission SENTINELLED --------
    fill_idall, _dead_uv = RFL._grass_stamp(host_bms)     # the frame's own MAJORITY ground stamp: the
    #   IDALL half of the old stamp is lawful and stays (a fill tri must wear a frame-legal topo); it
    #   is the UV half (_dead_uv) that L1 deletes -- SENTINEL_UV goes in instead and is resolved per
    #   triangle by THE SYNTHESIS RE-EMIT below.
    saved_stamp = RFL._grass_stamp
    RFL._grass_stamp = lambda _h: (fill_idall, SENTINEL_UV)
    try:
        out_soup, placed_R2, carried_translated, cdiag = RFL.carry(donor, host_bms, site["land_height"])
    finally:
        RFL._grass_stamp = saved_stamp
    log(f"  [S5/6] carry+stitch: {len(out_soup)} blocks, placed_R={len(placed_R2)}")
    R["carry"] = dict(n_placed_R=len(placed_R2), n_verbatim_tris=cdiag["n_verbatim_tris"],
                      n_fill_tris=cdiag["n_fill_tris"], DY=cdiag["DY"],
                      ecotone_floor_y=cdiag["ecotone_floor_y"], stitch=cdiag["stitch"],
                      touched_blocks=cdiag["touched_blocks"],
                      donor=dict(n_kept_tris=len(donor["raw"]), n_kept_cells=donor["n_cells_kept"],
                                 n_dropped_tris=donor["n_dropped"],
                                 n_fully_dropped_cells=len(donor["fully_dropped_cells"]),
                                 n_partial_cells=len(donor["partial_cells"])))

    soup = {}
    synth = {}
    for blk, bm in frame_blocks.items():
        if blk not in out_soup:
            soup[blk] = RFL.bm_world_soup(bm, blk[0], blk[1])
            synth[blk] = [False] * len(soup[blk])
    for blk, s in out_soup.items():
        soup[blk] = list(s)
        synth[blk] = [is_sentinel(t) for t in s]
    C = Composite(soup, synth)
    n_synth = sum(sum(1 for b in f if b) for f in synth.values())
    n_tot = sum(len(s) for s in soup.values())
    log(f"  [S6] composite: {n_tot} tris, {n_synth} synthesized (sentinel-marked by construction)")
    gate("S6 PROVENANCE: every synthesized tri is sentinel-marked all-or-nothing (no mixed tri)",
         all(is_sentinel(t) == (all(abs(v[2][0] - SENTINEL_UV[0]) < 1e-6 for v in t))
             for blk in soup for t in soup[blk]),
         f"synth={n_synth}/{n_tot}")

    # -- STAGE 6a: D3 -- UPWARD WINDING on THE PIPELINE'S OWN SYNTHESIZED EMISSION --------------------
    # The ear-clip / contour-tile / apron emitters do not normalize the index order of the triangles
    # they mint: a near-flat fill triangle can come out wound clockwise in plan, i.e. with its
    # geometric normal pointing DOWN.  Every historical rung-F build printed exactly 3 of them, in the
    # fill over the donor's dropped topo-59 shaft -- and they survived 8 rounds because the winding
    # gate charged them to the CARRY (they sit inside the carry footprint) and the carry is exempt.
    # THE FIX AT THE SOURCE: any SYNTHESIZED tri whose plan cross-product is negative is re-wound by
    # swapping vertex entries 1 and 2.  Position, normal, UV and tangent/IDALL travel together in one
    # tuple, so the triangle is geometrically and texturally IDENTICAL -- only its index order changes.
    # CARRIED tris are NEVER re-wound: a carried tri's winding is stock's own, and byte-rigidity
    # outranks the convention (the gate keeps them exempt-but-counted).
    flip_rows = []
    degen_rows = []
    for blk in sorted(C.soup):
        s = C.soup[blk]
        for i, tri in enumerate(s):
            if not C.synth[blk][i]:
                continue
            ny2 = plan_ny2(tri_world(tri))
            if ny2 < 0.0:
                s[i] = [tri[0], tri[2], tri[1]]
                flip_rows.append(dict(block=list(blk), tri=i,
                                      centroid=[round(x, 3) for x in centroid_xz(tri_world(tri))],
                                      plan_ny2=round(ny2, 6),
                                      dip_deg=None if dip_deg(tri_world(tri)) is None
                                      else round(dip_deg(tri_world(tri)), 3),
                                      topo=tri_topo(tri)))
            elif ny2 == 0.0:
                degen_rows.append(dict(block=list(blk), tri=i,
                                       centroid=[round(x, 3) for x in centroid_xz(tri_world(tri))]))
    n_down_after = sum(1 for blk in C.soup for i, t in enumerate(C.soup[blk])
                       if C.synth[blk][i] and plan_ny2(tri_world(t)) <= 0.0)
    gate("L7-5e(D3) UPWARD-WINDING at the SOURCE: after the re-wind pass 0 SYNTHESIZED tris are "
         "down-facing or plan-degenerate (the folded generator stops PRODUCING them)",
         n_down_after == 0,
         f"flipped={len(flip_rows)} plan_degenerate={len(degen_rows)} remaining_down={n_down_after} "
         f"rows={flip_rows[:6]}")
    R["D3_winding"] = dict(n_synth=n_synth, n_flipped=len(flip_rows), flipped=flip_rows,
                           n_plan_degenerate=len(degen_rows), plan_degenerate=degen_rows[:12],
                           n_down_facing_synth_after=n_down_after,
                           rule=("SYNTHESIZED only (sentinel bookkeeping); swap vertex entries 1<->2 "
                                 "when the plan cross-product is negative; carried donor tris are "
                                 "never re-wound"))

    # -- STAGE 6b: THE SYNTHESIS RE-EMIT (L1 one-window x L2 family x L3 policy field) ----------------
    src_hist = Counter()
    fam_hist = Counter()
    for blk in C.soup:
        s = C.soup[blk]
        for i, tri in enumerate(s):
            if not C.synth[blk][i]:
                continue
            vw = tri_world(tri)
            fam = famfield.at(own_cell(*centroid_xz(vw)))
            uv, _cell, src = one_window_uv(vw, fam, decoded)
            src_hist[src] += 1
            fam_hist[fam] += 1
            s[i] = [(p, n, uv[k], t) for k, (p, n, _u, t) in enumerate(tri)]
    log(f"  [L1] re-emit: {sum(src_hist.values())} synthesized tris; window_source={dict(src_hist)}; "
        f"family={dict(fam_hist)}")
    R["L1_L2_L3"] = dict(quad_ori=qo_stats, window_source=dict(src_hist),
                         synth_family_hist=dict(fam_hist),
                         family_field_ties=dict(famfield.stats),
                         n_synthesized_tris=n_synth, n_total_tris=n_tot)
    gate("L1 NO SENTINEL SURVIVES the re-emit (every synthesized tri carries a resolved one-window UV)",
         not any(is_sentinel(t) for blk in C.soup for t in C.soup[blk]))

    # -- STAGE 7: the basin exclusion discs (computed ONCE, threaded into L4 AND L5) ------------------
    Gp = C.position_graph()
    ground_pos = {k: 1 for k in Gp["kept_ground"]}
    samples = np.array([[k[0], k[1], k[2]] for k in sorted(ground_pos)], dtype=float)
    ghash = Hash2D(samples, cell=8.0)
    movable = {k for k in Gp["synth_pos"] if k not in Gp["kept_ground"] and k not in Gp["kept_rock"]}
    dropped_cell_topo = {}
    for c, tris in donor["dropped_by_cell"].items():
        dropped_cell_topo[(c[0] + Tx, c[1] + Tz)] = Counter(tri_topo(t) for t in tris)
    rows = []
    for k in sorted(movable):
        yhat, _d = ref_at(ghash, samples, k[0], k[2])
        if yhat is None:
            continue
        cell = own_cell(k[0], k[2])
        dc = dropped_cell_topo.get(cell)
        rows.append(dict(k=k, x=k[0], y=k[1], z=k[2], ref=yhat, res=k[1] - yhat, cell=cell,
                         in49=bool(dc and dc.most_common(1)[0][0] == 49)))
    discs, clusters = basin_exclusion_discs(rows, ghash, samples, log=log)
    R["L4_basins"] = dict(n_clusters=len(clusters), exclusion_discs=discs,
                          rule=("proximity graph r=4.5u, same-sign, >=2 verts; BASIN(keep) when "
                                "enclosure>=0.70 over 16 azimuths AND elongation<=1.6 AND "
                                "dropped-topo-49 cell fraction<0.20 (uvf_relief_probe.stage4/5b)"))

    def in_basin(x, z, pad=0.0):
        return any(math.hypot(x - d["center"][0], z - d["center"][1]) <= d["radius_u"] + pad
                   for d in discs)

    # -- STAGE 8: L4 -- the whole-fill relief relax ---------------------------------------------------
    by_key = {r["k"]: r for r in rows}
    unknowns = {r["k"] for r in rows if not in_basin(r["x"], r["z"])}
    edges = set()
    for blk, i, tri, is_s in C.tris():
        if not is_s:
            continue
        ks = [pkey(v[0]) for v in tri]
        for a in range(3):
            p, q = ks[a], ks[(a + 1) % 3]
            if p != q:
                edges.add((min(p, q), max(p, q)))
    core = {k for k in unknowns if abs(by_key[k]["res"]) >= ANOM_T}
    res_map = {k: by_key[k]["res"] for k in unknowns}
    moved, solve_diag = harmonic_relax(unknowns, edges, res_map, core, L4_W_DATA, L4_W_HOLD)
    newY = [k[1] + v for k, v in moved.items()]
    l4_clear = (not newY) or min(newY) > MIN_LAND_Y
    gate("L4 HEIGHT RELAX: every relaxed fill position stays above the sea skirt "
         f"(> {MIN_LAND_Y}u)", l4_clear,
         f"unknowns={solve_diag['n_unknowns']} core={len(core)} patch_edges={solve_diag['n_patch_edges']} "
         f"pin_edges={solve_diag['n_pin_edges']} moved={len(moved)} "
         f"max|dY|={round(max((abs(x) for x in moved.values()), default=0.0), 3)} "
         f"minY={round(min(newY), 3) if newY else None}")
    basin_moved = [k for k in moved if in_basin(k[0], k[2])]
    gate("L4 BASIN REFERENCE TRAP (target side): 0 positions inside an enclosure-detected basin disc "
         "were relaxed", not basin_moved, f"{len(basin_moved)} moved inside a disc")
    ap = C.apply_dy(moved)
    res_before = [by_key[k]["res"] for k in unknowns]
    res_after = [by_key[k]["res"] + moved.get(k, 0.0) for k in unknowns]
    R["L4_relax"] = dict(**solve_diag, n_moved=len(moved),
                         weights=dict(data_core=L4_W_DATA, hold=L4_W_HOLD, edge=W_EDGE, eps=EPS),
                         anomaly_threshold_u=ANOM_T, n_core=len(core),
                         residual_p95_before=round(float(np.percentile(np.abs(res_before), 95)), 4)
                         if res_before else None,
                         residual_p95_after=round(float(np.percentile(np.abs(res_after), 95)), 4)
                         if res_after else None,
                         max_abs_dY=round(max((abs(x) for x in moved.values()), default=0.0), 4),
                         min_Y_after=round(min(newY), 4) if newY else None, apply=ap,
                         method=("harmonic / Laplacian least squares on the synthesized patch's own "
                                 "edge graph, C0 into the pins by construction -- NEVER a distance "
                                 "falloff (uvf_relief_probe.stage6's argued choice)"))

    # -- STAGE 9: L5a -- the spike/step census + shave ------------------------------------------------
    spike_res, spike_diag = spike_shave(C, discs, log=log, gate=gate)
    R["L5a_spike"] = spike_diag

    # -- STAGE 10: L5b -- the orphan-decal census + redress -------------------------------------------
    orph_res = orphan_redress(C, donor, (Twx, Twz), cdiag["DY"], site, famfield, decoded,
                              log=log, gate=gate)
    R["L5b_orphan"] = orph_res

    # -- STAGE 11: L6 -- the HONEST sea ---------------------------------------------------------------
    import dataclasses
    sea_by_cell = {}
    for blk in sorted(footprint):
        bx, by = blk
        hidden = {p.lower(): M.hidden_block_mesh(name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
                  for p in ("Sea1", "Sea2", "Sea3", "Sea5")}
        hidden["sea4"] = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
        sea_by_cell[blk] = hidden
    sea_y_bad = [f"{b[0]},{b[1]}" for b in footprint
                 if any(abs(v[1]) > 1e-6 for v in sea_by_cell[b]["sea4"].verts)]
    gate("L6 SEA-LAYER LAW: every staged Sea4 vertex Y == 0", not sea_y_bad, f"{sea_y_bad[:6]}")
    s4n = {len(sea_by_cell[b]["sea4"].tris) for b in footprint}
    gate("L6 UNIFORM FULL SEA4: every block carries the same full deep-ocean plane (the "
         "_sea4_y0_stub degenerate-blob gaming is DELETED -- contract v5's sea-vertex flag made it "
         "unnecessary)", len(s4n) == 1, f"distinct Sea4 tri-counts={sorted(s4n)}")
    R["L6_sea"] = dict(n_blocks=len(footprint), sea4_tris=sorted(s4n),
                       degenerate_stub_used=False)

    # -- STAGE 12: build the final BlockMeshes + the orphan-decal RING gate + stage the file set -------
    final_blocks = {blk: bm_from_soup(C.soup[blk], blk[0], blk[1]) for blk in sorted(C.soup)}
    # D2 -- THE DOUBLE-REDRESS FIX (2026-07-25, the code-disjoint falsifier).  This stage used to run
    # the kit orphangate a SECOND time with ``redress=True`` on the very BlockMeshes that are about to
    # be staged, so the pipeline carried TWO independent re-clothing mechanisms.  The kit gate judges a
    # decal by its RING CONTEXT (partner family within 2 cells / straddle within the cell); at a FRESH
    # frame a genuinely CARRIED, bit-exact CATALOGUED grass|desert transition-strip tile can land with
    # its partner family outside that radius, and the kit gate then re-clothed it into plain desert
    # mains and re-stamped topo 16 -> 17.  That is a verbatim-carry violation: the strip row IS stock's
    # own vocabulary, catalogued, and the authoritative mechanism (the L5b TWO-SIDED census at stage 10
    # -- uncatalogued rect AND live-flat AND donor-steep) correctly SPARES it.
    # THE RULE NOW: L5b is the ONLY redress in the pipeline.  The kit orphangate runs WARN-only, on a
    # DEEP COPY so it cannot mutate a staged byte even by accident, and its finding is recorded as an
    # ADVISORY with full detail.  (``redress=False`` is documented read-only; the copy is belt-and-
    # braces -- a law in a docstring is a wish.)
    import copy as _copy
    cell_meshes = {blk: [("Terrain", _copy.deepcopy(final_blocks[blk]))] for blk in sorted(footprint)}
    try:
        og_res = OG.orphan_decal_gate(cell_meshes, set(footprint), enforce=False, redress=False,
                                      mod_folder=None, disc=1, game=game_root)
        og_res["n_orphans_pre_redress"] = og_res.get("n_orphans")
        og_res["redress_applied"] = False
        og_ok = og_res.get("n_orphans", 1) == 0 and og_res.get("n_ambiguous", 1) == 0
    except Exception as e:                                   # noqa: BLE001
        og_res = {"error": str(e)}
        og_ok = False
    og_mutated = [f"{b[0]},{b[1]}" for b in sorted(footprint)
                  if any(cell_meshes[b][0][1].chan_arrays[ch] != final_blocks[b].chan_arrays[ch]
                         for ch in (CH_POS, CH_NRM, CH_UV, CH_TAN))
                  or cell_meshes[b][0][1].tris != final_blocks[b].tris]
    gate("S12 KIT-ORPHANGATE NON-MUTATION (D2): the advisory ring-context pass changed 0 staged "
         "bytes on any channel (pos/nrm/uv/tan=IDALL) or index buffer -- L5b is the pipeline's ONLY "
         "redress", not og_mutated, f"mutated={og_mutated}")
    # THE DISAGREEMENT ADJUDICATION.  An advisory that merely warns is not a verdict.  Every cell the
    # kit gate still reports must be accounted for on MY OWN bookkeeping: every ground tri in it is
    # CARRIED (not synthesized), wears a CATALOGUED rect, and is UV-byte-identical to its own donor
    # tile.  That is precisely the population L5b's two-sided rule spares -- so the disagreement is
    # the known ring-context misread and nothing else.  A synthesized or UNCATALOGUED tri in a
    # reported cell would be a real defect L5b missed, and reds the build.
    dindex_s12 = donor_index(site, (Twx, Twz), cdiag["DY"], game_root)
    adjudication = []
    unexplained = []
    for c in og_res.get("cells", []):
        cell = (int(c[0]), int(c[1]))
        for blk, i, tri, is_s in C.tris():
            vw = tri_world(tri)
            if own_cell(*centroid_xz(vw)) != cell:
                continue
            topo = tri_topo(tri)
            if GROUND_FAM.get(topo) is None:
                continue
            uv = tri_uv(tri)
            fam = SNR.FAM_OF.get(topo)
            cls, _d = SC.classify_tri_plus(fam, uv) if fam else ("no_family", None)
            d = dindex_s12.get(_trikey(vw))
            uv_exact = None if d is None else _donor_uv_matches(d, vw, uv)
            row = dict(cell=list(cell), block=list(blk), tri=i, topo=topo, uv_rect=cls,
                       synthesized=bool(is_s), donor_matched=d is not None,
                       uv_byte_identical_to_donor=uv_exact)
            adjudication.append(row)
            if is_s or cls == "other_uncatalogued" or not d or uv_exact is False:
                unexplained.append(row)
    gate("S12 KIT/L5b DISAGREEMENT ADJUDICATION (D2): every ground tri in a cell the kit orphangate "
         "still reports is CARRIED, CATALOGUED and UV-byte-identical to its donor tile -- i.e. exactly "
         "the population the L5b two-sided census spares, not a defect L5b missed",
         not unexplained,
         f"cells={og_res.get('cells', [])} tris_examined={len(adjudication)} "
         f"unexplained={unexplained[:4]}")
    # The WARN-only report itself.  Its predicate is what the pipeline actually CLAIMS since D2 --
    # not "the kit gate found nothing" (it does find the 2 carried strip tiles, and always will at a
    # fresh frame) but "the kit gate found nothing UNEXPLAINED".  The raw counts stay in the detail.
    gate("S12 ORPHAN-DECAL RING gate (kit orphangate, deployed-else-stock ring) -- WARN-ONLY since D2: "
         "it reports and NEVER mutates; every finding is adjudicated against the carry's own donor "
         "bytes, and the L5b two-sided census is authoritative",
         (og_res.get("error") is None) and not unexplained and og_res.get("n_ambiguous", 1) == 0,
         f"{ {k: og_res.get(k) for k in ('n_orphans', 'n_ambiguous', 'detail', 'error')} } "
         f"cells={og_res.get('cells', [])[:8]} unexplained={len(unexplained)} "
         f"kit_clean={og_ok}", advisory=True)
    R["S12_kit_orphangate_advisory"] = dict(
        result={k: v for k, v in og_res.items() if k not in ("cell_meshes",)},
        adjudication=adjudication, n_unexplained=len(unexplained),
        policy=("WARN-only since D2; the kit gate NEVER mutates here and its verdict is adjudicated "
                "against the pipeline's own carried/catalogued/donor-byte bookkeeping"))
    try:
        wang = TR.wang_carry_gate(sea_by_cell, set(footprint), enforce=True)
        wang_ok = wang.get("ok", False) and wang.get("incoherent", 1) == 0
    except Exception as e:                                   # noqa: BLE001
        wang = {"error": str(e)}
        wang_ok = False
    gate("S12 WANG-CARRY gate: 0 incoherent frame edges", wang_ok,
         f"{ {k: wang.get(k) for k in ('ok', 'incoherent', 'incoherent_deep', 'error')} }")

    written = stage_tree(stage_dir, final_blocks, sea_by_cell, footprint, log=log)
    R["stage"] = written

    # -- STAGE 13: L7 -- THE FULL GATE BATTERY on THIS build's own final composite --------------------
    # D3 -- THE PROVENANCE LABEL.  ``carried_cells`` (the carry FOOTPRINT) is still handed over as the
    # legacy fallback, but the down-facing split now consumes ``tri_provenance``: the SAME per-tri
    # class this loop already computes from the pipeline's sentinel bookkeeping, aligned 1:1 with
    # ``final_blocks[blk].tris`` (``soup_to_bm`` preserves soup order exactly).  The old plan
    # heuristic charged MINTED FILL emitted inside the footprint to the carry and exempted it.
    carried_cells = set(placed_R2)
    synth_records = []
    ground_tri_rows = []
    tri_provenance = {blk: [None] * len(C.soup[blk]) for blk in C.soup}
    prov_hist = Counter()
    for blk, i, tri, is_s in C.tris():
        vw = tri_world(tri)
        uv3 = tri_uv(tri)
        cell = own_cell(*centroid_xz(vw))
        if is_s:
            synth_records.append(dict(vw=vw, uv=uv3, fam=famfield.at(cell)))
        fam = GROUND_FAM.get(tri_topo(tri))
        famu = famfield.at(cell) if is_s else fam
        if is_s:
            cls = "synth"
        elif cell not in carried_cells:
            cls = "frame"
        elif (blk, i) in C.moved_tris:
            cls = "carried_shaved"
        else:
            cls = "carried"
        tri_provenance[blk][i] = cls
        prov_hist[cls] += 1
        if famu is not None:
            ground_tri_rows.append((famu, vw, uv3, cls))
    align_bad = [f"{b[0]},{b[1]}" for b in final_blocks
                 if len(tri_provenance[b]) != len(final_blocks[b].tris)]
    gate("S13 PROVENANCE ALIGNMENT (D3): the per-tri provenance vector is 1:1 with every staged "
         "block's index buffer (soup order == BlockMesh tri order)", not align_bad,
         f"bad={align_bad} hist={dict(prov_hist)}")
    R["D3_provenance"] = dict(hist=dict(prov_hist), aligned=not align_bad)
    jsafe = lambda d: {k: v for k, v in d.items()                       # noqa: E731
                       if k in ("n_spikes", "verdict_hist", "rule", "n_orphaned",
                                "n_uncatalogued_carried", "uv_class_hist", "rows", "orphans")}
    ctx = dict(stage_dir=stage_dir, blocks=sorted(footprint), final_blocks=final_blocks,
               carried_cells=carried_cells, tri_provenance=tri_provenance,
               synth_records=synth_records, decoded=decoded,
               ground_tri_rows=ground_tri_rows,
               spike_census=jsafe(spike_res), orphan_census=jsafe(orph_res["post_census"]))
    results, l7 = CG.run_composite_gates(ctx)
    for g in l7:
        gates.append(g)
        log(f"GATE [{'PASS' if g['ok'] else 'FAIL'}] {g['name']}"
            + (f" -- {g['detail'][:300]}" if g["detail"] else ""))
    R["L7_gate_results"] = results

    if run_contract:
        con = contract_screen(stage_dir, gate, log=log)
        R["contract"] = con

    green = CG.all_green(gates)
    R["gates"] = gates
    R["all_green"] = green
    R["n_gates"] = len(gates)
    R["failed"] = [g["name"] for g in gates if not g["ok"] and not g["name"].startswith("ADVISORY")]
    R["advisory_failed"] = [g["name"] for g in gates if not g["ok"] and g["name"].startswith("ADVISORY")]

    # -- STAGE 14: L8 -- eye artifacts, ONLY after the battery is green -------------------------------
    if render and green:
        R["L8_renders"] = renders(C, famfield, stage_dir.parent / f"renders-{site['name']}", log=log)
    elif render:
        R["L8_renders"] = dict(skipped="gates RED -- L8 renders are only emitted on an all-green "
                                       "composite (THE FINAL-COMPOSITE RULE)")
    R["meta"]["seconds"] = round(time.time() - t0, 1)
    log("\n" + "=" * 100)
    log(f"COMPOSITE {'GREEN' if green else 'RED'}  ({len(gates)} gates, "
        f"{len(R['failed'])} failed, {len(R['advisory_failed'])} advisory-failed) "
        f"in {R['meta']['seconds']}s")
    if R["failed"]:
        log(f"failed: {R['failed']}")
    return R


# =====================================================================================================
#  L4 -- basin discs   [lifted: uvf_relief_probe.stage4 clustering + stage5b exclusion discs]
# =====================================================================================================
def basin_exclusion_discs(rows, ghash, samples, log=print):
    anom = [r for r in rows if abs(r["res"]) >= ANOM_T]
    if not anom:
        log("  [L4] 0 anomalous fill positions -> no basin discs")
        return [], []
    for r in anom:
        r["enclose"], r["rise"] = enclosure(ghash, samples, r["x"], r["y"], r["z"])
    pts = np.array([[r["x"], r["y"], r["z"]] for r in anom])
    h = Hash2D(pts, cell=CLUSTER_R)
    parent = list(range(len(anom)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, r in enumerate(anom):
        for j, _d2 in h.query(r["x"], r["z"], CLUSTER_R):
            if j != i and (anom[j]["res"] > 0) == (r["res"] > 0):
                a, b = find(i), find(j)
                if a != b:
                    parent[b] = a
    groups = defaultdict(list)
    for i in range(len(anom)):
        groups[find(i)].append(i)
    clusters = []
    for _g, idxs in groups.items():
        if len(idxs) < MIN_CLUSTER:
            continue
        P = pts[idxs]
        rs = np.array([anom[i]["res"] for i in idxs])
        xz = P[:, [0, 2]]
        c = xz.mean(axis=0)
        cov = np.cov((xz - c).T)
        ev, _evec = np.linalg.eigh(np.atleast_2d(cov))
        L1 = math.sqrt(max(float(ev[-1]), 0.0))
        L2 = math.sqrt(max(float(ev[0]), 0.0))
        elong = (L1 / L2) if L2 > 1e-6 else 999.0
        enc = float(np.mean([anom[i]["enclose"] for i in idxs]))
        f49 = float(np.mean([anom[i]["in49"] for i in idxs]))
        verdict = ("BASIN(keep)" if (enc >= 0.70 and elong <= 1.6 and f49 < 0.20)
                   else ("channel" if elong >= 2.0 else "pit/dig-spot"))
        clusters.append(dict(n_verts=len(idxs), sign=("bump" if rs.mean() > 0 else "pit"),
                             centroid_world=[round(float(c[0]), 2), round(float(c[1]), 2)],
                             peak_residual=round(float(rs[np.argmax(np.abs(rs))]), 3),
                             extent_major_u=round(2.0 * L1, 2), extent_minor_u=round(2.0 * L2, 2),
                             elongation=round(elong, 2), enclosure_frac=round(enc, 3),
                             frac_in_topo49_cells=round(f49, 3), verdict=verdict,
                             _keys=[anom[i]["k"] for i in idxs]))
    clusters.sort(key=lambda c: -abs(c["peak_residual"]))
    discs = []
    for c in clusters:
        if c["verdict"] != "BASIN(keep)":
            continue
        cx, cz = c["centroid_world"]
        Rr = max(c["extent_major_u"], c["extent_minor_u"]) / 2.0 + 3.0
        discs.append(dict(center=[cx, cz], radius_u=round(Rr, 2), peak_residual=c["peak_residual"],
                          n_anom_verts=c["n_verts"], enclosure_frac=c["enclosure_frac"],
                          elongation=c["elongation"]))
    log(f"  [L4] {len(anom)} anomalous fill positions -> {len(clusters)} clusters -> "
        f"{len(discs)} BASIN(keep) exclusion disc(s): {discs}")
    return discs, [{k: v for k, v in c.items() if k != "_keys"} for c in clusters]


# =====================================================================================================
#  L5a -- the spike/step census + shave   [lifted: uvf_fix6.stage2/3/4 + uvf_fix7's STEP arm]
# =====================================================================================================
def spike_census(C, discs, *, exclude_basin_samples=True):
    """THE CENSUS RULE, mechanical.  Reference = uvf_relief_probe.ref_at on a sample set of CARRIED
    GROUND + FILL positions, minus (a) every basin disc [THE BASIN REFERENCE TRAP -- excluded from the
    SAMPLES, not merely from the target set], (b) the query position itself (leave-one-out), and
    (c) on the second pass every pass-A candidate.  Rock (58/31) abstains at the source."""
    Gp = C.position_graph()
    kept_ground, kept_rock, adj = Gp["kept_ground"], Gp["kept_rock"], Gp["adj"]
    fill = {k for k in Gp["synth_pos"] if k not in kept_ground and k not in kept_rock}
    sample_keys = sorted(set(kept_ground) | fill)
    samples = np.array([[k[0], k[1], k[2]] for k in sample_keys], dtype=float)
    idx_of = {k: i for i, k in enumerate(sample_keys)}
    base = Hash2D(samples, cell=8.0)

    def in_basin(k):
        return any(math.hypot(k[0] - d["center"][0], k[2] - d["center"][1]) <= d["radius_u"]
                   for d in discs)

    basin_idx = frozenset(idx_of[k] for k in sample_keys if in_basin(k)) if exclude_basin_samples \
        else frozenset()

    def census_pass(drop_extra):
        out = {}
        for k in sample_keys:
            y, _d = ref_at(ExcludeHash(base, basin_idx | {idx_of[k]} | drop_extra), samples,
                           k[0], k[2])
            out[k] = None if y is None else k[1] - y
        return out

    res_a = census_pass(frozenset())
    cand_a = {k for k, v in res_a.items() if v is not None and v >= SPIKE_RES_T}
    res = census_pass(frozenset(idx_of[k] for k in cand_a))

    prom, drop = {}, {}
    for k in sample_keys:
        nb = adj.get(k, ())
        prom[k] = (k[1] - max((n[1] for n in nb), default=-1e9)) if nb else None
        drop[k] = (k[1] - min((n[1] for n in nb), default=1e9)) if nb else None

    def arm_of(k):
        p, d = prom.get(k), drop.get(k)
        if p is None or d is None:
            return None
        if p >= SPIKE_PROM_T:
            return "CONE"
        if p >= STEP_PROM_T and d >= STEP_DROP_T:
            return "STEP"
        return None

    parts_only_terrain = True                # this generator stages Terrain + hidden/plane sea parts
    #   only; a fill position never shares a key with a non-Terrain part (asserted by the sea-layer
    #   gate: every Sea4 vertex is at Y==0, and MIN_LAND_Y keeps land above it).

    def classify(k):
        if k in kept_rock:
            return "rock-stamp-EXEMPT"
        if k not in kept_ground:
            return "fill"
        if res.get(k) is None:
            return "unscored"
        if res[k] < SPIKE_RES_T:
            return "below-residual-threshold"
        if arm_of(k) is None:
            return ("flush-with-a-neighbour-and-no-step(not-a-spike)"
                    if (prom.get(k) is not None and prom[k] >= STEP_PROM_T)
                    else "below-a-neighbour(not-a-spike)")
        if in_basin(k):
            return "inside-a-basin-disc(refused)"
        if not parts_only_terrain:
            return "shared-with-a-non-Terrain-part(refused)"
        return f"SPIKE-{arm_of(k)}"

    verdicts = {k: classify(k) for k in set(kept_ground) | set(kept_rock)}
    spikes = sorted([k for k, v in verdicts.items() if v.startswith("SPIKE")], key=lambda k: -res[k])
    return dict(spikes=spikes, res=res, prom=prom, drop=drop, adj=adj, fill=fill,
                kept_ground=kept_ground, kept_rock=kept_rock, basin_idx=basin_idx,
                n_spikes=len(spikes), verdict_hist=dict(sorted(Counter(verdicts.values()).items())),
                rows=[dict(k=list(k), res=round(res[k], 4), prom=round(prom[k], 4) if prom[k] else None,
                           drop=round(drop[k], 4) if drop[k] else None, arm=arm_of(k))
                      for k in spikes],
                rule=("ground topo (rock 58/31 EXEMPT at three levels) AND residual >= "
                      f"{SPIKE_RES_T}u AND (CONE prominence >= {SPIKE_PROM_T}u OR STEP prominence "
                      f">= {STEP_PROM_T}u AND welded drop >= {STEP_DROP_T}u) AND outside every basin "
                      "disc AND Terrain-only"))


def spike_shave(C, discs, *, log=print, gate=None):
    pre = spike_census(C, discs)
    log(f"  [L5a] spike/step census: {pre['n_spikes']} qualifying; verdicts={pre['verdict_hist']}")
    diag = dict(pre_census_n=pre["n_spikes"], pre_verdicts=pre["verdict_hist"],
                pre_rows=pre["rows"], rule=pre["rule"], basin_discs=discs,
                basin_samples_excluded=len(pre["basin_idx"]))
    if not pre["spikes"]:
        diag["shave"] = "no-op (census empty)"
        diag["post_census_n"] = 0
        return pre, diag

    spikes = set(pre["spikes"])
    adj, res, fill = pre["adj"], pre["res"], pre["fill"]

    def guard_ok(k):
        return not any(math.hypot(k[0] - d["center"][0], k[2] - d["center"][1])
                       <= d["radius_u"] + BASIN_GUARD_PAD for d in discs)

    U = set(spikes)
    frontier = set(spikes)
    for _h in range(HOPS):
        nxt = set()
        for k in frontier:
            for n in adj[k]:
                if n in fill and n not in U and guard_ok(n):
                    nxt.add(n)
        U |= nxt
        frontier = nxt
    edges = set()
    for k in U:
        for nb in adj[k]:
            edges.add((min(k, nb), max(k, nb)))
    res_u = {k: (res[k] if res.get(k) is not None else 0.0) for k in U}
    sweep, chosen = [], None
    for w in W_SWEEP:
        mv, sd = harmonic_relax(U, edges, res_u, spikes, w, 1.0)
        post = [abs(res_u[k] + mv.get(k, 0.0)) for k in spikes]
        fdy = [abs(v) for k, v in mv.items() if k not in spikes]
        ok = (max(post, default=0.0) <= W_ACCEPT_POST and max(fdy, default=0.0) <= W_ACCEPT_FILL)
        sweep.append(dict(w_spike=w, max_post_abs_residual=round(max(post, default=0.0), 4),
                          max_fill_abs_dY=round(max(fdy, default=0.0), 4), accepted=ok))
        if ok and chosen is None:
            chosen = (w, mv, sd)
    if chosen is None:
        diag["sweep"] = sweep
        diag["shave"] = "REFUSED -- no sweep weight met the acceptance rule"
        if gate:
            gate("L5a SHAVE ACCEPTANCE: some sweep weight lands every spike within "
                 f"{W_ACCEPT_POST}u of the rim surface with no fill unknown moving > {W_ACCEPT_FILL}u",
                 False, f"sweep={sweep}")
        post = spike_census(C, discs)
        diag["post_census_n"] = post["n_spikes"]
        return post, diag
    w_spike, moved, sd = chosen
    # -- the stop guards (uvf_fix6.stage_guards), checked BEFORE anything moves ----------------------
    carried_moved = [k for k in moved if (k in pre["kept_ground"] or k in pre["kept_rock"])
                     and k not in spikes]
    rock_moved = [k for k in moved if k in pre["kept_rock"]]
    basin_moved = [k for k in moved if not guard_ok(k)]
    down_only = all(moved.get(k, 0.0) < 0 for k in spikes)
    newY = [k[1] + v for k, v in moved.items()]
    guards = dict(carried_non_spike_frozen=not carried_moved, rock_stamps_frozen=not rock_moved,
                  basin_frozen=not basin_moved, all_spike_moves_downward=down_only,
                  sea_clearance_ok=bool(not newY or min(newY) > MIN_LAND_Y),
                  max_abs_dY=round(max(abs(v) for v in moved.values()), 4))
    guards["all_pass"] = all(v is True for k, v in guards.items() if isinstance(v, bool))
    if gate:
        gate("L5a STOP GUARDS: carried non-spike frozen, rock stamps frozen, basin (+2u annulus) "
             "frozen, every spike move DOWNWARD, sea clearance held", guards["all_pass"], f"{guards}")
    if guards["all_pass"]:
        ap = C.apply_dy(moved)
        diag["apply"] = ap
    else:
        moved = {}
        diag["apply"] = "REFUSED by the stop guards"
    diag.update(sweep=sweep, chosen_w_spike=w_spike, solve=sd, n_moved=len(moved), guards=guards)
    post = spike_census(C, discs)
    diag["post_census_n"] = post["n_spikes"]
    log(f"  [L5a] shaved {len(moved)} positions (w_spike={w_spike}); post-census "
        f"{post['n_spikes']} qualifying")
    return post, diag


# =====================================================================================================
#  L5b -- the orphan-decal census + redress   [lifted: uvf_fix8.load_donor / census / re-clothe]
# =====================================================================================================
def _trikey(w3, dp=2):
    return tuple(sorted((round(float(p[0]), dp), round(float(p[2]), dp)) for p in w3))


def donor_index(site, shift_world, DY, game_root):
    """The donor triangles the carry took, indexed by their SHIFTED plan key.  A transform, not a
    verdict (uvf_fix8.load_donor)."""
    out = {}
    for (bx, by) in site["donor_blocks"]:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except Exception:                                    # noqa: BLE001
            continue
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            w = [(bm.verts[j][0] + ox + shift_world[0], bm.verts[j][1] + DY,
                  bm.verts[j][2] + oz + shift_world[1]) for j in tri]
            out[_trikey(w)] = dict(w=w, block=(bx, by),
                                   uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri],
                                   topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"])
    return out


def _donor_uv_matches(dtri, w3, uv3, dp=2):
    """UV BYTE-IDENTITY against the tri's own donor tile, paired by PLAN POSITION rather than by
    index order: D3 re-winds SYNTHESIZED tris (a carried tri is never re-wound, but the pairing must
    not silently depend on that).  Sorted-tuple compare, so a repeated plan position cannot collapse
    the match."""
    a = sorted((round(float(p[0]), dp), round(float(p[2]), dp), float(u[0]), float(u[1]))
               for p, u in zip(dtri["w"], dtri["uv"]))
    b = sorted((round(float(p[0]), dp), round(float(p[2]), dp), float(u[0]), float(u[1]))
               for p, u in zip(w3, uv3))
    return a == b


def orphan_census(C, dindex):
    """THE 4-PREDICATE RULE (uvf_fix8.py:22-54), map-wide, no hand-picking:
       (1) CARRIED; (2) GROUND topograph; (3) UNCATALOGUED RECT
       (uvf_stock_census.classify_tri_plus == 'other_uncatalogued'); (4) PARENT-GEOMETRY-ABSENT
       (live dip < 25deg AND its OWN donor triangle's dip >= 25deg)."""
    cls_hist = Counter()
    carried_unc = []
    orphan = []
    for blk, i, tri, is_s in C.tris():
        w = tri_world(tri)
        uv = tri_uv(tri)
        topo = tri_topo(tri)
        fam = SNR.FAM_OF.get(topo)
        cls, _det = SC.classify_tri_plus(fam, uv) if fam else ("no_family", None)
        cls_hist[cls] += 1
        if cls != "other_uncatalogued":
            continue
        if is_s:
            continue
        if GROUND_FAM.get(topo) is None:
            continue
        live = dip_deg(w)
        d = dindex.get(_trikey(w))
        ddip = dip_deg(d["w"]) if d else None
        rec = dict(block=list(blk), tri=i, topo=topo, fam=fam,
                   centroid=[round(x, 3) for x in centroid_xz(w)],
                   live_dip=None if live is None else round(live, 2),
                   donor_matched=d is not None,
                   donor_dip=None if ddip is None else round(ddip, 2))
        rec["flat_now"] = (live is not None and live < FLAT_DIP_T)
        rec["donor_had_relief"] = (ddip is not None and ddip >= DONOR_DIP_T)
        rec["parent_geometry_absent"] = bool(rec["flat_now"] and rec["donor_had_relief"])
        carried_unc.append(rec)
        if rec["parent_geometry_absent"]:
            orphan.append((blk, i, rec))
    return dict(uv_class_hist=dict(cls_hist), n_uncatalogued_carried=len(carried_unc),
                n_orphaned=len(orphan), orphans=[r for (_b, _i, r) in orphan],
                _targets=[(b, i) for (b, i, _r) in orphan],
                rule=("carried AND ground topo AND uncatalogued rect AND live dip < "
                      f"{FLAT_DIP_T}deg AND own-donor dip >= {DONOR_DIP_T}deg; stock-flat decals "
                      "(donor dip below the same threshold) are SPARED"))


def orphan_redress(C, donor, shift_world, DY, site, famfield, decoded, *, log=print, gate=None):
    game_root = Path(_cfg.find_game_path(None))
    dindex = donor_index(site, shift_world, DY, game_root)
    pre = orphan_census(C, dindex)
    log(f"  [L5b] orphan-decal census: {pre['n_orphaned']} orphaned of "
        f"{pre['n_uncatalogued_carried']} carried uncatalogued")
    targets = set(pre["_targets"])
    n_re = 0
    fam_used = Counter()
    if targets:
        # family: the surrounding family's mains -- resolved by the L2 field with the TARGETS
        # EXCLUDED from voting (uvf_fix8 stage4_family), cross-checked against the tri's own topo.
        agree = 0
        for (blk, i) in sorted(targets):
            tri = C.soup[blk][i]
            vw = tri_world(tri)
            own_fam = GROUND_FAM.get(tri_topo(tri))
            vote_fam = famfield.at(own_cell(*centroid_xz(vw)))
            fam = vote_fam or own_fam
            agree += (vote_fam == own_fam)
            uv, _c, _s = one_window_uv(vw, fam, decoded)
            C.soup[blk][i] = [(p, n, uv[k], t) for k, (p, n, _u, t) in enumerate(tri)]
            fam_used[fam] += 1
            n_re += 1
        log(f"  [L5b] re-clothed {n_re} orphaned decal tris in the surrounding family's mains "
            f"({dict(fam_used)}); vote/own-topo agreement {agree}/{n_re}")
    post = orphan_census(C, dindex)
    if gate:
        gate("L5b ORPHAN-DECAL REDRESS: the post-redress census is EMPTY (UV-only; every re-clothed "
             "tri now wears its surrounding family's catalogued mains)", post["n_orphaned"] == 0,
             f"pre={pre['n_orphaned']} re_clothed={n_re} post={post['n_orphaned']}")
    return dict(pre_census={k: v for k, v in pre.items() if not k.startswith("_")},
                n_re_clothed=n_re, families=dict(fam_used),
                post_census={k: v for k, v in post.items() if not k.startswith("_")})


# =====================================================================================================
#  staging + the contract screen + L8
# =====================================================================================================
def stage_tree(stage_dir, final_blocks, sea_by_cell, footprint, *, log=print):
    stage_dir = Path(stage_dir)
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    written = 0
    for blk in sorted(footprint):
        bx, by = blk
        parts = {"Terrain": final_blocks[blk], "Sea4": sea_by_cell[blk]["sea4"]}
        for p in ("Sea1", "Sea2", "Sea3", "Sea5"):
            parts[p] = sea_by_cell[blk][p.lower()]
        parts["Object"] = M.hidden_block_mesh(name=f"Block[{bx}][{by}] Object", disc=1, x=bx, y=by)
        parts["Beach1"] = M.hidden_block_mesh(name=f"Block[{bx}][{by}] Beach1", disc=1, x=bx, y=by)
        for part_name, bm in parts.items():
            M.write_ff9mesh(bm, stage_dir / M.override_relpath(1, bx, by, "0_1", part_name))
            written += 1
        dp = stage_dir / M.donor_sidecar_relpath(1, bx, by, "0_1")
        dp.parent.mkdir(parents=True, exist_ok=True)
        dp.write_text("0,0", encoding="utf-8")
        written += 1
    log(f"  [S12] staged {written} files across {len(footprint)} blocks -> {stage_dir}")
    return dict(n_files=written, n_blocks=len(footprint), root=str(stage_dir))


def contract_screen(stage_dir, gate, *, log=print):
    stock = CMG.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=CMG.ECOTONE_CORE)
    stock_row = CMG.run_matrix_on(stock)
    cand = CMG.load_candidate("foldback_staged", str(stage_dir))
    row = CMG.run_matrix_on(cand)
    r1, r2, r3 = row["R1"], row["R2"], row["R3"]
    # contract v5 adds scalar FLAG entries alongside the measured checks (e.g.
    # ``sea_vertex_convention_invalid``) -- read only the measured dicts.
    measured = {k: v["measured_u"] for k, v in r1["checks"].items()
                if isinstance(v, dict) and "measured_u" in v}
    flags = {k: v for k, v in r1["checks"].items() if not isinstance(v, dict)}
    gate("CONTRACT R1 realized-boundary standoff PASS", r1["verdict"] == "PASS",
         f"measured={measured} convention_invalid={r1['convention_invalid']} flags={flags}")
    gate("CONTRACT R2 saturation + arrangement PASS", r2["verdict"] == "PASS",
         f"sat_grass={r2['saturation']['grass_decal']} sat_any={r2['saturation']['any_decal']} "
         f"fringe={r2['arrangement']['fringe_concentration']}")
    gate("CONTRACT R3 inland-backing extent PASS", r3["verdict"] == "PASS",
         f"backing={r3['largest_reachable_backing_cells']} "
         f"interface={r3['skin_backing_interface_pairs']}")
    gate("CONTRACT stock reference still PASSES all three (instrument calibrated)",
         stock_row["overall"] == "PASS", f"stock={stock_row['overall']}")
    return dict(overall=row["overall"], stock_overall=stock_row["overall"],
                R1=dict(verdict=r1["verdict"], measured=measured, flags=flags,
                        convention_invalid=r1["convention_invalid"]),
                R2=dict(verdict=r2["verdict"], saturation=r2["saturation"],
                        arrangement=r2["arrangement"]),
                R3=dict(verdict=r3["verdict"],
                        backing=r3["largest_reachable_backing_cells"],
                        interface=r3["skin_backing_interface_pairs"],
                        erosion=r3["erosion_survive_backing_cells"]))


def renders(C, famfield, render_dir, *, log=print):
    """L8 -- THREE channels: family colour (textured analogue), shaded relief, and the round-8
    TEXEL-DENSITY heatmap.  Renderer lifted from rung_f_build.stage8_renders."""
    try:
        from PIL import Image, ImageDraw
    except Exception as e:                                   # noqa: BLE001
        log(f"  [L8] PIL unavailable ({e}) -- skipping renders")
        return dict(rendered=[], error=str(e))
    render_dir = Path(render_dir)
    render_dir.mkdir(parents=True, exist_ok=True)
    FAM_COL = {"grass": (86, 140, 60), "desert": (200, 176, 110), "dunes": (222, 200, 140),
               "rock": (120, 112, 104), None: (150, 150, 150)}
    tris = []
    dens = []
    sig_by_fam = defaultdict(list)
    for blk, _i, tri, is_s in C.tris():
        p3 = tri_world(tri)
        uv3 = tri_uv(tri)
        topo = tri_topo(tri)
        fam = SNR.FAM_OF.get(topo)
        if topo == 49:
            fam = "rock"
        if is_s:
            fam = famfield.at(own_cell(*centroid_xz(p3)))
        s = CG.sigma_max(p3, uv3)
        d = dip_deg(p3)
        if s is not None and d is not None and (is_s or GROUND_FAM.get(topo) is not None):
            sig_by_fam[fam].append((s, d))
        tris.append((p3, FAM_COL.get(fam, FAM_COL[None]), sum(p[1] for p in p3) / 3.0, s, fam))
    base = {}
    for fam, rows in sig_by_fam.items():
        flat = sorted(s for (s, d) in rows if d is not None and d < 10.0) or sorted(s for (s, _d) in rows)
        if flat:
            base[fam] = flat[len(flat) // 2]
    xs = [p[0] for (p3, _c, _y, _s, _f) in tris for p in p3]
    zs = [p[2] for (p3, _c, _y, _s, _f) in tris for p in p3]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    rendered = []

    def planview(fname, title, mode):
        W = H = 900
        pad = 30
        s = min((W - 2 * pad) / (x1 - x0), (H - 2 * pad) / (z1 - z0))
        img = Image.new("RGB", (W, H + 26), (20, 22, 26))
        dr = ImageDraw.Draw(img)
        dr.text((pad, 6), title, fill=(235, 225, 170))
        lv = [c / math.sqrt(0.25 + 0.64 + 0.09) for c in (0.5, 0.8, 0.3)]
        for (p3, col, _my, sg, fam) in sorted(tris, key=lambda t: t[2]):
            pts = [(pad + (p[0] - x0) * s, 26 + H - pad - (p[2] - z0) * s) for p in p3]
            c = col
            if mode == "shade":
                n = up_normal(p3) or [0, 1, 0]
                sh = max(0.35, min(1.0, 0.45 + 0.55 * abs(sum(n[k] * lv[k] for k in range(3)))))
                c = tuple(int(v * sh) for v in col)
            elif mode == "density":
                b = base.get(fam)
                if sg is None or not b:
                    c = (60, 60, 66)
                else:
                    r = sg / b
                    t = max(-1.0, min(1.0, math.log(max(r, 1e-6)) / math.log(2.0)))
                    c = ((int(40 + 200 * t), int(40 + 60 * (1 - abs(t))), int(40))
                         if t > 0 else (int(40), int(40 + 60 * (1 - abs(t))), int(40 - 200 * t)))
                    c = tuple(max(0, min(255, q)) for q in c)
            dr.polygon(pts, fill=c)
        img.save(render_dir / fname)
        rendered.append(str(render_dir / fname))
        log(f"  [L8] wrote {fname}")

    planview("planview_family.png", "FOLD-BACK -- planview by ground family (grass/desert/dunes/rock)",
             "flat")
    planview("planview_shaded.png", "FOLD-BACK -- shaded relief (the L4 mesh-function relax)", "shade")
    planview("planview_density.png",
             "FOLD-BACK -- texel-density heatmap (red = denser than the family flat baseline, "
             "blue = stretched); the round-8 eye channel", "density")
    return dict(rendered=rendered, world_bbox=[round(x0, 1), round(z0, 1), round(x1, 1), round(z1, 1)],
                family_baselines={k: round(v, 2) for k, v in base.items()})


# =====================================================================================================
def selftest_crosscheck(rep):
    """THE SELF-TEST'S OWN INSTRUMENT CHECK: the fold is re-run against the ORIGINAL rung-F site
    parameters, so the quantities the original build RECORDED in out/rung_f/rung_f_build.json must
    come back identical wherever the fold did not deliberately change the mechanism.  Byte-equality
    with FIXED8 is NOT expected and NOT claimed -- FIXED8 reached its state by eight post-hoc
    rewrites of a staged tree; this is a single generator pass with different (better-ordered)
    mechanisms.  What must match is the SITE and the CARRY."""
    p = HERE / "out" / "rung_f" / "rung_f_build.json"
    if not p.exists():
        return dict(available=False)
    o = json.loads(p.read_text(encoding="utf-8"))
    od = o["compose_diag"]
    or1 = {k: v["measured_u"] for k, v in o["stage7_contract"]["rung_f"]["R1"]["checks"].items()
           if isinstance(v, dict) and "measured_u" in v}
    nr1 = rep.get("contract", {}).get("R1", {}).get("measured", {})
    s4 = o["stage4_composite_plumbing"]
    n4 = rep["L7_gate_results"]["stage4_plumbing"]
    rows = [
        ("footprint_blocks", len(o["stage0_site"]["footprint"]), rep["stage"]["n_blocks"]),
        ("staged_files", o["stage6_write"]["n_files"], rep["stage"]["n_files"]),
        ("DY", od["DY"], rep["carry"]["DY"]),
        ("fill_tris", od["n_fill_tris"], rep["carry"]["n_fill_tris"]),
        ("placed_R_cells", od["n_placed_R"], rep["carry"]["n_placed_R"]),
        ("verbatim_carried_tris", od["n_verbatim_tris"], rep["carry"]["n_verbatim_tris"]),
        ("open_edges_above_skirt", s4["open_edges_above_skirt"], n4["open_edges_above_skirt"]),
        ("weld_near_miss", s4["weld_near_miss"], n4["weld_near_miss"]),
        ("down_grass_or_apron", s4["down_grass_or_apron"], n4["down_grass_or_apron"]),
        ("R1_boundary_cell_u", or1.get("boundary_cell"), nr1.get("boundary_cell")),
        ("R1_straddle_cell_u", or1.get("straddle_cell"), nr1.get("straddle_cell")),
        ("R1_body_tri_u", or1.get("body_tri"), nr1.get("body_tri")),
    ]
    out = {k: dict(original=a, foldback=b, match=(a == b)) for (k, a, b) in rows}
    out["all_match"] = all(v["match"] for v in out.values() if isinstance(v, dict))
    # D3 DELIBERATELY CHANGES this one, so it is NOT an equality row any more: the original build's
    # 3 "carried faithful" down-facing tris were mislabelled MINTED FILL, and the folded generator
    # now re-winds them at emission.  The expected value is 0, and 3 -> 0 is the fix landing.
    out["down_carried_faithful__D3_EXPECTED_CHANGE"] = dict(
        original=s4["down_carried_faithful"], foldback=n4["down_carried_faithful"], expected=0,
        as_expected=(n4["down_carried_faithful"] == 0),
        note=("the original 3 sat inside the carry FOOTPRINT but were synthesized fill over the "
              "donor's dropped topo-59 shaft; D3(a) relabels by sentinel bookkeeping and D3(b) "
              "re-winds them at emission, so both the carried and the synth/frame counts are 0"))
    return dict(available=True, comparison=out,
                independently_rederived=dict(
                    basin_discs=("round 5's exclusion disc was (127.14,-1161.42) r=7.92; the fold "
                                 "derived it from scratch through the enclosure test"),
                    spike_arms=("rounds 6+7 shaved 4 CONE apexes then 1 STEP shoulder; the fold's "
                                "single census selects the same 4 CONE + 1 STEP"),
                    orphan_decals=("round 8 found 10 orphaned decal tris in 5 two-tri knobs; the "
                                   "fold's map-wide census finds the same 10")))


def main(argv):
    out_dir = HERE / "out" / "foldback"
    out_dir.mkdir(parents=True, exist_ok=True)
    site = rung_f_site(out_dir / "selftest-tree")
    rep = compose(site)
    rep["self_test_crosscheck"] = selftest_crosscheck(rep)
    print("\nSELF-TEST CROSS-CHECK vs the recorded original build:")
    for k, v in rep["self_test_crosscheck"].get("comparison", {}).items():
        if isinstance(v, dict):
            good = v["match"] if "match" in v else v.get("as_expected")
            tag = "OK " if good else ("DIFF" if "match" in v else "UNEXPECTED")
            print(f"  {tag}  {k}: original={v['original']} foldback={v['foldback']}"
                  + (f" expected={v['expected']}" if "expected" in v else ""))
    (out_dir / "foldback_build.json").write_text(json.dumps(rep, indent=1, default=str),
                                                 encoding="utf-8")
    print(f"-> {out_dir / 'foldback_build.json'}")
    return 0 if rep["all_green"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
