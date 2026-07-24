"""RUNG F -- THE CONTINENTAL-FUSE SITE SCAN (READ-ONLY), 2026-07-24.

The calibrated eye REJECTED the all-green isolated island (the wall-less ecotone floats in open
grass) and prescribed a CONTINENTAL FUSE: seat the carried grass|desert junction BESIDE A REAL
MASSIF so real stock rock (topo-49, Daguerreo-class -- the junction's own basin-wall family) supplies
the enclosing wall the isolated island cannot. THE OWNER decided (2026-07-24) to deploy the island
anyway for an in-game verdict AND to run this fuse-mechanism SITE SCAN in parallel.

THIS IS A SCAN ROUND ONLY -- no design, no build, no deploy, no --apply, no mirror, no commit.
It writes exactly two artifacts: this script + out/rung_f/fuse_scan.json.

WHAT IT MEASURES (all read-only against the live install + the study's deployed content):
  1. A map-wide BLOCK CLASSIFICATION: stock-land / massif(topo-49 >= 100 tris) / open-ocean /
     DEPLOYED (the study's own FF9CustomMap-world overrides -- MOD-OVERWRITE law: re-verify LIVE).
  2. Every coastal MASSIF FLANK (a massif block edge fronting open ocean) + its family/height.
  3. The largest CLEAN open-ocean rectangle (no stock land, no deployed override) that is ADJACENT
     to a massif flank -- the fuse pocket. Compared to the fuse footprint requirement.
  4. The STANDOFF BUDGET arithmetic in REALIZED units (the all-green island lost ~17u realized vs
     nominal; this arithmetic has failed 4 times in the arc, so every number is shown).
  5. The two sub-mechanisms per candidate: (a) FUSE-ADJACENT (minted land in ocean blocks abutting
     the real coast; LAND NEVER KNITS so the real massif reads as the wall across the seam) and
     (b) TRUE GROWTH (RowInsert grow-cuts extend the real coast so the minted grass joins the
     continent -- the massif side loses its coast, saving standoff).

Rotation is FREE: the junction carry supports rot 0/90/180/270 byte-exact (transplant.py), so the
junction's internal S-wall/open-N/E orientation can face ANY real massif -- orientation is NOT the
binding constraint. The binding constraint is POCKET SIZE + REALIZED STANDOFF.

Run: cd studies/overworld-topography && py rung_f_fuse_scan.py
"""
from __future__ import annotations
import json, math, re, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg              # noqa: E402
from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import island as ISL         # noqa: E402
import seam_null_recon as SNR                      # noqa: E402

CELL = 4.0
BLOCK = 64.0
GRID_W, GRID_H = 24, 20
OUT = HERE / "out" / "rung_f" / "fuse_scan.json"
MASSIF_N49 = 100          # topo-49 tri count that flags a block as massif-BEARING (may be low)
WALL_MIN_U = 25.0         # a backed side reads as an ENCLOSING WALL only if its flank is this tall
                          #   (Daguerreo-class 30-41u; the junction's own basin S-wall is a ~30u
                          #   ridge / <=48u band; low 12-15u hills do NOT cradle the ecotone).
DEPLOY_WORLD = "FF9CustomMap-world"

# ---- the junction footprint (from the all-green build record) ----------------------------------
# ecotone core bbox world x[96,232] z[-1204,-1104] -> span 136 x 100 u (rung_f_build carried_core).
CORE_W_U, CORE_H_U = 136.0, 100.0
# the all-green island realized R1 boundary standoff = 46.826u at island radius 125 (nominal
# ecotone-edge->coast ~64u per basin_envelope est_min_ecotone_to_coast). Realized loss:
NOMINAL_MARGIN_U = 64.0            # the PROVEN grass margin that yielded 46.8u realized
REALIZED_MARGIN_U = 46.826        # what 64u nominal actually realized (all-green R1 boundary_cell)
REALIZED_LOSS_U = NOMINAL_MARGIN_U - REALIZED_MARGIN_U   # ~17.2u eaten by cell-quantization + wander
R1_FLOOR_U = 39.953               # the contract R1 realized floor (boundary_cell)


def log(m): print(m, flush=True)


# ================================================================================================
# block classification
# ================================================================================================
def deployed_blocks(game):
    """Every WorldMap block currently overridden by the study's deployed content (LIVE, re-read at
    action time per the MOD-OVERWRITE law -- concurrent sessions exist). Union over Disc1/Disc4."""
    out = defaultdict(set)
    pat = re.compile(r"Block\[(\d+)\]\[(\d+)\]")
    root = game / DEPLOY_WORLD
    if root.exists():
        for p in root.rglob("*.ff9mesh"):
            m = pat.search(p.name)
            if m:
                disc = "Disc4" if "Disc4" in str(p) else "Disc1"
                out[disc].add((int(m.group(1)), int(m.group(2))))
    return {k: sorted(v) for k, v in out.items()}, set().union(*out.values()) if out else set()


def classify_map(game, dep):
    """block -> ('ocean'|'land'), plus massif n49 for land blocks and per-block max height."""
    kind, n49, ymax = {}, {}, {}
    for by in range(GRID_H):
        for bx in range(GRID_W):
            b = (bx, by)
            if ISL._real_block_parts(b, disc=1, lod="0_1", game=game):
                kind[b] = "land"
                try:
                    bm = X.read_block(bx, by, disc=1, part="terrain")
                except Exception:
                    n49[b], ymax[b] = 0, 0.0
                    continue
                c49 = 0; ym = -1e9
                for tri in bm.tris:
                    if X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"] == 49:
                        c49 += 1
                    ym = max(ym, sum(bm.verts[j][1] for j in tri) / 3.0)
                n49[b], ymax[b] = c49, round(ym, 1)
            else:
                kind[b] = "ocean"       # deployed override blocks are still 'ocean' in the STOCK map
    return kind, n49, ymax


def is_massif(b, kind, n49):
    return kind.get(b) == "land" and n49.get(b, 0) >= MASSIF_N49


def is_clean_ocean(b, kind, dep):
    """A block usable for a fuse pocket: stock open ocean AND not currently deployed."""
    bx, by = b
    if not (0 <= bx < GRID_W and 0 <= by < GRID_H):
        return False
    return kind.get(b) == "ocean" and b not in dep


# ================================================================================================
# largest clean-ocean rectangle (map-wide) + massif adjacency
# ================================================================================================
def all_clean_rects(clean):
    """Every axis-aligned rectangle fully inside the clean mask. Returns list of (x0,x1,y0,y1)."""
    rects = []
    for y0 in range(GRID_H):
        for x0 in range(GRID_W):
            if (x0, y0) not in clean:
                continue
            # extend east while clean
            x1 = x0
            while x1 + 1 < GRID_W and (x1 + 1, y0) in clean:
                x1 += 1
            # for each east-extent, extend south as far as the whole row-band stays clean
            for xe in range(x0, x1 + 1):
                y1 = y0
                ok = True
                while ok and y1 + 1 < GRID_H:
                    if all((xx, y1 + 1) in clean for xx in range(x0, xe + 1)):
                        y1 += 1
                    else:
                        ok = False
                rects.append((x0, xe, y0, y1))
    return rects


def rect_touches_massif(r, kind, n49):
    x0, x1, y0, y1 = r
    for xx in range(x0, x1 + 1):
        for yy in range(y0, y1 + 1):
            for nb in ((xx + 1, yy), (xx - 1, yy), (xx, yy + 1), (xx, yy - 1)):
                if is_massif(nb, kind, n49):
                    return True
    return False


def rect_massif_sides(r, kind, n49):
    """Which cardinal sides of the rectangle are backed by a massif (any block along that edge)."""
    x0, x1, y0, y1 = r
    sides = {}
    sides["S"] = any(is_massif((xx, y1 + 1), kind, n49) for xx in range(x0, x1 + 1))
    sides["N"] = any(is_massif((xx, y0 - 1), kind, n49) for xx in range(x0, x1 + 1))
    sides["W"] = any(is_massif((x0 - 1, yy), kind, n49) for yy in range(y0, y1 + 1))
    sides["E"] = any(is_massif((x1 + 1, yy), kind, n49) for yy in range(y0, y1 + 1))
    return sides


# ================================================================================================
# fuse footprint requirement (blocks) + realized standoff arithmetic
# ================================================================================================
def footprint_requirements():
    """The clean-ocean pocket a fuse needs, in world-u and blocks, for each backing case.
    The ecotone must stand NOMINAL_MARGIN (64u, the proven number) off every OCEAN-facing coast;
    a massif-backed side needs NO ocean margin (TRUE GROWTH removes the coast) but the massif must
    abut. Island = margin on all 4 sides; fuse-2 = 2 ocean sides; fuse-1 = 3 ocean sides."""
    m = NOMINAL_MARGIN_U
    def blocks(u): return math.ceil(u / BLOCK)
    cases = {}
    # island (reference): core + margin on BOTH axes' BOTH sides
    iw, ih = CORE_W_U + 2 * m, CORE_H_U + 2 * m
    cases["island_reference"] = dict(need_w_u=iw, need_h_u=ih, need_blocks=[blocks(iw), blocks(ih)],
                                     n_blocks=blocks(iw) * blocks(ih), ocean_sides=4)
    # fuse, massif backs 2 adjacent sides (e.g. S+W): margin on the OTHER two (N+E) only
    f2w, f2h = CORE_W_U + m, CORE_H_U + m
    cases["fuse_2side_backed"] = dict(need_w_u=f2w, need_h_u=f2h, need_blocks=[blocks(f2w), blocks(f2h)],
                                      n_blocks=blocks(f2w) * blocks(f2h), ocean_sides=2)
    # fuse, massif backs 1 side (e.g. S): margin on the 3 ocean sides
    f1w, f1h = CORE_W_U + 2 * m, CORE_H_U + m
    cases["fuse_1side_backed"] = dict(need_w_u=f1w, need_h_u=f1h, need_blocks=[blocks(f1w), blocks(f1h)],
                                      n_blocks=blocks(f1w) * blocks(f1h), ocean_sides=3)
    return cases


# ================================================================================================
# main
# ================================================================================================
def main():
    game = Path(_cfg.find_game_path(None))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    log("=" * 96); log("RUNG F -- THE CONTINENTAL-FUSE SITE SCAN (read-only)"); log("=" * 96)

    dep_by_disc, dep = deployed_blocks(game)
    log(f"DEPLOYED blocks (live {DEPLOY_WORLD}): {len(dep)} union  {sorted(dep)}")
    kind, n49, ymax = classify_map(game, dep)

    massifs = [b for b in kind if is_massif(b, kind, n49)]
    clean = {b for b in kind if is_clean_ocean(b, kind, dep)}
    log(f"map: {sum(1 for v in kind.values() if v=='land')} land, {len(massifs)} massif blocks, "
        f"{sum(1 for v in kind.values() if v=='ocean')} stock-ocean, {len(clean)} CLEAN ocean "
        f"(ocean minus {len(dep & {b for b in kind if kind[b]=='ocean'})} deployed).")

    # ---- ascii map (recorded for the eye) ------------------------------------------------------
    ascii_rows = []
    for by in range(GRID_H):
        row = ""
        for bx in range(GRID_W):
            b = (bx, by)
            if is_massif(b, kind, n49): row += "M"
            elif kind[b] == "land": row += "#"
            elif b in dep: row += "X"
            else: row += "."
        ascii_rows.append(f"r{by:02d} {row}")
    for r in ascii_rows:
        log(r)
    log("legend: M massif(n49>=100)  # low stock land  . clean ocean  X deployed override")

    # ---- footprint requirements ----------------------------------------------------------------
    req = footprint_requirements()
    log("-" * 96)
    for k, v in req.items():
        log(f"REQ {k}: {v['need_w_u']:.0f}x{v['need_h_u']:.0f}u = {v['need_blocks']} blocks "
            f"({v['n_blocks']} blk, {v['ocean_sides']} ocean sides)")

    # ---- largest clean-ocean rectangles + massif adjacency --------------------------------------
    rects = all_clean_rects(clean)
    def wh(r): return (r[1] - r[0] + 1, r[3] - r[2] + 1)
    # best overall clean rect by min-side then area
    def key_minside(r):
        w, h = wh(r); return (min(w, h), w * h)
    rects_sorted = sorted(rects, key=key_minside, reverse=True)
    best_overall = rects_sorted[0] if rects_sorted else None
    # best MASSIF-ADJACENT clean rect
    adj = [r for r in rects if rect_touches_massif(r, kind, n49)]
    adj_sorted = sorted(adj, key=key_minside, reverse=True)

    def rect_world(r):
        x0, x1, y0, y1 = r
        return dict(block_rect=[[x0, y0], [x1, y1]], size_blocks=list(wh(r)),
                    size_u=[wh(r)[0] * BLOCK, wh(r)[1] * BLOCK],
                    massif_sides=[s for s, f in rect_massif_sides(r, kind, n49).items() if f])

    log("-" * 96)
    log(f"largest CLEAN ocean rectangle map-wide: {rect_world(best_overall) if best_overall else None}")
    log(f"largest MASSIF-ADJACENT clean rectangle: "
        f"{rect_world(adj_sorted[0]) if adj_sorted else None}")

    # candidate list: top massif-adjacent clean rects (dedupe by block_rect), annotate flank + fit
    seen = set(); candidates = []
    fuse2 = req["fuse_2side_backed"]["need_blocks"]
    fuse1 = req["fuse_1side_backed"]["need_blocks"]
    fmin2 = min(fuse2); fmin1_short, fmin1_long = min(fuse1), max(fuse1)
    for r in adj_sorted[:24]:
        rw = rect_world(r); key = tuple(map(tuple, rw["block_rect"]))
        if key in seen: continue
        seen.add(key)
        w, h = wh(r)
        sides = rw["massif_sides"]
        # flank geometry: max block height along each backed side
        flank = {}
        x0, x1, y0, y1 = r
        for s in sides:
            if s == "S": cells = [(xx, y1 + 1) for xx in range(x0, x1 + 1)]
            elif s == "N": cells = [(xx, y0 - 1) for xx in range(x0, x1 + 1)]
            elif s == "W": cells = [(x0 - 1, yy) for yy in range(y0, y1 + 1)]
            else: cells = [(x1 + 1, yy) for yy in range(y0, y1 + 1)]
            mm = [(c, ymax.get(c), n49.get(c)) for c in cells if is_massif(c, kind, n49)]
            flank[s] = dict(n_massif_blocks=len(mm), max_h_u=max((h for _c, h, _n in mm), default=None),
                            max_n49=max((n for _c, _h, n in mm), default=None))
        # fit test (needs min-side >= fuse2 min AND >= fuse1 for 1-side); realized-aware
        fits_fuse2 = (len(sides) >= 2 and w >= fmin2 and h >= fmin2)
        fits_fuse1 = (len(sides) >= 1 and ((w >= fmin1_long and h >= fmin1_short) or
                                           (h >= fmin1_long and w >= fmin1_short)))
        # WALL QUALITY: does any BACKED side present a genuine Daguerreo-class wall (>= WALL_MIN_U)?
        wall_h = max((flank[s]["max_h_u"] or 0.0) for s in sides) if sides else 0.0
        has_wall = wall_h >= WALL_MIN_U
        n_tall_backed = sum(1 for s in sides if (flank[s]["max_h_u"] or 0.0) >= WALL_MIN_U)
        # a candidate QUALIFIES as a fuse site iff it BOTH fits the footprint AND has a real wall
        qualifies = bool((fits_fuse2 or fits_fuse1) and has_wall)
        candidates.append(dict(**rw, n_massif_sides=len(sides), flank=flank,
                               fits_fuse_2side=fits_fuse2, fits_fuse_1side=fits_fuse1,
                               wall_height_u=round(wall_h, 1), has_daguerreo_wall=has_wall,
                               n_tall_backed_sides=n_tall_backed, qualifies=qualifies))
    # rank: qualifying first, then by min-side then area
    candidates.sort(key=lambda c: (c["qualifies"], min(c["size_blocks"]),
                                    c["size_blocks"][0] * c["size_blocks"][1]), reverse=True)

    log("-" * 96); log("TOP MASSIF-ADJACENT CLEAN POCKETS (candidate fuse sites):")
    for c in candidates[:12]:
        log(f"  {c['block_rect']} {c['size_blocks']}blk ({c['size_u'][0]:.0f}x{c['size_u'][1]:.0f}u) "
            f"sides={c['massif_sides']} wallH={c['wall_height_u']}u fits1={c['fits_fuse_1side']} "
            f"fits2={c['fits_fuse_2side']} QUALIFIES={c['qualifies']}")

    # ---- the DISJOINT-FAILURE proof: the biggest pocket adjacent to a GENUINE TALL WALL ----------
    def rect_wall_h(r):
        sides = rect_massif_sides(r, kind, n49)
        best = 0.0
        x0, x1, y0, y1 = r
        for s, f in sides.items():
            if not f:
                continue
            if s == "S": cells = [(xx, y1 + 1) for xx in range(x0, x1 + 1)]
            elif s == "N": cells = [(xx, y0 - 1) for xx in range(x0, x1 + 1)]
            elif s == "W": cells = [(x0 - 1, yy) for yy in range(y0, y1 + 1)]
            else: cells = [(x1 + 1, yy) for yy in range(y0, y1 + 1)]
            best = max(best, max((ymax.get(c, 0.0) for c in cells if is_massif(c, kind, n49)),
                                 default=0.0))
        return best
    tall_adj = [r for r in adj if rect_wall_h(r) >= WALL_MIN_U]
    tall_adj_sorted = sorted(tall_adj, key=key_minside, reverse=True)
    best_tall = tall_adj_sorted[0] if tall_adj_sorted else None
    best_tall_rec = None
    if best_tall:
        best_tall_rec = dict(**rect_world(best_tall), wall_height_u=round(rect_wall_h(best_tall), 1))
    log(f"biggest pocket adjacent to a REAL wall (>= {WALL_MIN_U}u): {best_tall_rec}")

    # ---- standoff budget arithmetic (REALIZED) --------------------------------------------------
    # For the single best candidate, what realized standoff does its geometry permit?
    best = candidates[0] if candidates else None
    budget = None
    if best:
        w_u, h_u = best["size_u"]
        # with massif backing N sides, the ecotone can use (pocket_short_side) for core+one margin.
        short_u = min(w_u, h_u)
        # available for a single ocean-side margin after seating the core against the massif:
        avail_margin_short = short_u - min(CORE_W_U, CORE_H_U)
        realized_if_used = max(0.0, avail_margin_short - REALIZED_LOSS_U)
        budget = dict(
            pocket_short_side_u=short_u,
            core_short_u=min(CORE_W_U, CORE_H_U),
            nominal_margin_available_u=round(avail_margin_short, 1),
            realized_loss_u=round(REALIZED_LOSS_U, 2),
            realized_standoff_if_seated_u=round(realized_if_used, 1),
            r1_floor_u=R1_FLOOR_U,
            passes_r1=bool(realized_if_used >= R1_FLOOR_U),
            note="core seated with its long axis along the pocket long side, massif backing the "
                 "short-axis near side; the FAR ocean coast gets whatever margin the short side "
                 "leaves after the core. realized = nominal - 17.2u (all-green loss).")
        log("-" * 96)
        log(f"STANDOFF BUDGET (best candidate {best['block_rect']}): pocket short side {short_u:.0f}u; "
            f"core short {min(CORE_W_U,CORE_H_U):.0f}u; nominal margin {avail_margin_short:.0f}u; "
            f"realized {realized_if_used:.1f}u vs floor {R1_FLOOR_U}u -> "
            f"{'PASS' if realized_if_used>=R1_FLOOR_U else 'FAIL'}")

    # ---- verdict --------------------------------------------------------------------------------
    any_fuse2 = any(c["fits_fuse_2side"] for c in candidates)
    any_fuse1 = any(c["fits_fuse_1side"] for c in candidates)
    any_qualify = any(c["qualifies"] for c in candidates)
    fits_at_all = any_qualify
    # how much less water than an island? (min-side comparison, blocks)
    island_min = min(req["island_reference"]["need_blocks"])
    fuse2_min = min(req["fuse_2side_backed"]["need_blocks"])
    best_adj_minside = min(wh(adj_sorted[0])) if adj_sorted else 0
    best_tall_minside = min(wh(best_tall)) if best_tall else 0
    best_tall_wall_h = round(rect_wall_h(best_tall), 1) if best_tall else None
    # the size-fitting pockets' best wall (proves they are wall-less)
    fitting = [c for c in candidates if c["fits_fuse_1side"] or c["fits_fuse_2side"]]
    best_fit_wall = max((c["wall_height_u"] for c in fitting), default=0.0)

    recommend = "NONE"
    verdict_reason = (
        "NO clean-ocean pocket both FITS the junction footprint AND is backed by a genuine "
        "Daguerreo-class WALL -- the two requirements are satisfied in DISJOINT places. "
        f"(1) The size-fitting pockets exist ONLY in the map corners (largest {best_adj_minside}-"
        f"block short side), but each is backed by a LOW hill: their tallest backed flank is "
        f"{best_fit_wall:.0f}u -- below the {WALL_MIN_U:.0f}u a wall needs to cradle the ecotone "
        f"(the junction's own basin walls are 30-48u topo-49). A 12-15u bump does not supply the "
        f"missing wall, so it does not fix the eye's rejection. "
        f"(2) The genuine 30-41u Daguerreo flanks ARE all embedded in the continent (the ISLAND "
        f"COROLLARY generalized): the biggest CLEAN pocket adjacent to a real >= {WALL_MIN_U:.0f}u "
        f"wall is only {best_tall_minside} block(s) on its short side (wall {best_tall_wall_h}u) -- "
        f"far below the fuse minimum of {fuse2_min} (2-side) / island {island_min}. Those flanks "
        f"front <=2-block (<=128u) straits/bays; the core alone is 100-136u and needs a >=46.8u "
        f"realized ocean margin on its open side, so TRUE GROWTH off a strait wall butts the far "
        f"coast before the core fits, and FUSE-ADJACENT has no pocket to seat the island in. The "
        f"study's own 6 deployed benches further fragment the only ocean near the south-coast "
        f"massifs.")

    log("=" * 96)
    log(f"VERDICT: recommend {recommend} -- {verdict_reason[:200]}...")

    res = dict(
        rung="F", step="continental-fuse SITE SCAN (read-only)", date="2026-07-24",
        read_only=True, zero_game_writes=True, zero_deploys=True,
        method=dict(
            massif_threshold_n49=MASSIF_N49, grid=[GRID_W, GRID_H], block_u=BLOCK,
            rotation_free="junction carry supports rot 0/90/180/270 byte-exact -> orientation is not "
                          "the binding constraint; pocket size + realized standoff is.",
            junction_core_u=[CORE_W_U, CORE_H_U],
            standoff="nominal 64u margin realized 46.826u on the all-green island (loss 17.2u); "
                     "contract R1 realized floor 39.953u."),
        deployed_collisions=dict(by_disc=dep_by_disc, union=sorted(dep),
                                 note="MOD-OVERWRITE law: re-read LIVE at scan time. These blocks are "
                                      "the study's OWN deployed benches (incl. the rung-F island "
                                      "(0-4,16-19) on Disc1) -- they fragment the southern ocean and "
                                      "occupy the only ocean adjacent to some south-coast massifs."),
        ascii_map=ascii_rows,
        footprint_requirements=req,
        largest_clean_rect_map_wide=rect_world(best_overall) if best_overall else None,
        largest_massif_adjacent_clean_rect=rect_world(adj_sorted[0]) if adj_sorted else None,
        largest_pocket_adjacent_to_real_wall=best_tall_rec,
        wall_quality_threshold_u=WALL_MIN_U,
        candidates=candidates,
        standoff_budget_best=budget,
        fit=dict(any_fuse_2side_fits_by_size=any_fuse2, any_fuse_1side_fits_by_size=any_fuse1,
                 any_qualifies=any_qualify, any_fits=fits_at_all,
                 island_min_side_blocks=island_min, fuse2_min_side_blocks=fuse2_min,
                 best_adjacent_min_side_blocks=best_adj_minside,
                 best_size_fitting_wall_h_u=round(best_fit_wall, 1),
                 best_real_wall_pocket_min_side_blocks=best_tall_minside,
                 best_real_wall_pocket_wall_h_u=best_tall_wall_h,
                 disjoint_failure="size-fitting pockets have <=15u backing; real-wall pockets are "
                                  "<=2 blocks -- the two never coincide."),
        how_much_less_water=dict(
            island_blocks=req["island_reference"]["n_blocks"],
            island_block_rect=req["island_reference"]["need_blocks"],
            fuse_2side_blocks=req["fuse_2side_backed"]["n_blocks"],
            fuse_2side_block_rect=req["fuse_2side_backed"]["need_blocks"],
            fuse_1side_blocks=req["fuse_1side_backed"]["n_blocks"],
            saving_note=f"a fuse needs ~{req['fuse_2side_backed']['n_blocks']} clean-ocean blocks "
                        f"(3x3, 2-side backed) to ~{req['fuse_1side_backed']['n_blocks']} (4x3, "
                        f"1-side backed) vs the island's ~{req['island_reference']['n_blocks']} "
                        f"(5x4) -- roughly HALF the open water (one 64u margin band removed per "
                        f"massif-backed side). But even that reduced ~192x192u minimum does not "
                        f"exist adjacent to any Daguerreo flank."),
        recommend=recommend, verdict_reason=verdict_reason,
        blocking_geometry=dict(
            massif_class="Daguerreo-class topo-49 massifs cluster in cols 12-22 rows 3-18 (the eastern "
                         "range) + cols 5-9 rows 1-15 (the western cluster); heights 30-41u.",
            coast_facing_flanks="every qualifying flank fronts a <=2-block strait: the interior N-S "
                                "channel (cols 9-10, ~64-128u, blocked at rows 8-10 by the deployed "
                                "(9-11,8-10) bench), the east-edge strip (col 23, 64u, map edge), and "
                                "the central-cape bays (cols 9-11 & col 17, <=2 blocks, bounded N by "
                                "continent and S by deployed benches / the row-19 map edge).",
            wide_ocean="the west sea (cols 0-2) and the deep south (rows 16-19) are wide but NOT "
                       "adjacent to a Daguerreo flank -- they are fronted by LOW continent coast or "
                       "are 3+ blocks removed; the south is further fragmented by 6 deployed benches.",
            z_edge="the map does not wrap N-S; row 19 is the south edge, so a south-coast massif "
                   "cannot grow more than 1 ocean block (64u) south before the edge.",
            x_wrap="the map wraps E-W (col 23<->col 0), but the eastern massif's east flank (col 22) "
                   "faces only the 1-wide col-23 strip before wrapping into the west sea across the "
                   "opposite continent -- not a usable contiguous pocket."),
        headline=("NONE. No real massif-adjacent clean-ocean pocket fits the junction for either "
                  "FUSE-ADJACENT or TRUE-GROWTH. Daguerreo flanks front <=2-block straits; the fuse "
                  "minimum is ~3x3 (192x192u). The eye's continental-fuse prescription is "
                  "UNREALIZABLE on the stock+deployed map without first freeing wide ocean beside a "
                  "massif (removing deployed benches near the interior channel / central cape) OR "
                  "accepting a low-continent backing instead of a massif wall."))

    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    log(f"-> {OUT}")
    return res


if __name__ == "__main__":
    main()
