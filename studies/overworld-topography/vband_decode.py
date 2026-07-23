"""THE 0.836 V-BAND DECODE -- RUNG A of the seam-dressing arc (read-only census, 2026-07-22).

Round 10 (``GROUND-FAMILY-DECODE-2026-07-19.md``) decoded the desert|grass combining language and,
in passing, flagged TWO co-resident small atlas assets sharing one v-band it never inspected:

  * grass|scrub, u[0.34082,0.40332] v[0.83594,0.86621] ("a real lead that the atlas may carry a
    whole row of small per-pair transition decals at that v-band, untouched by this round")
  * dunes|topo-49-mural, u[0.13867,0.19922], same v-band ("a genuinely new, still-undecoded
    dunes|topo-49-mural fringe tile ... found only where dunes directly touches the mesa wall")

This script censuses that v-band MAP-WIDE (all 24x20 disc-1 blocks, real stock bytes, zero writes)
to answer: is this a systematic PER-PAIR DECAL ROW (one small transition asset per family pair,
parallel to but distinct from the STRIPS table), which pairs use it, what are their exact UV
windows (5dp), and do the Round-10 straddle/fringe/topo-consistency laws replicate here (with
honest small-n caveats -- do not law-ify n=2).

METHOD (mirrors Round 10 + the orphan-decal gate's own census discipline):
  1. ONE pass over every disc-1 terrain block builds a WORLD-CELL family/topo map
     (``cell_fams``/``cell_topos``) from EVERY terrain tri map-wide (extended family table:
     the 7 GROUNDS-covered walkable ground families + forest/rock/shore/lip, since the known
     dunes|mural instance pairs a GROUNDS family against the uncatalogued rock/mural texture
     axis, not another GROUNDS entry).
  2. The SAME pass classifies each tri against the TARGET V-BAND: a tri's OWN 3-corner UV bbox
     must closely equal the full row height [V_LO, V_HI] (tight tolerance -- a diagonal-split
     tri covering a whole affine-mapped cell spans the FULL u/v extent of its tile on its own,
     exactly the property Round 10's ``classify_strip_tri`` relies on) -- this is the PRIMARY
     census. A looser SECONDARY pass flags any vertex merely touching the band without full-tile
     coverage (partial/boundary residue), reported but never law-ified.
  3. Primary hits are clustered by their OWN (min_u, max_u) rounded to 5dp -- distinct clusters
     are candidate per-pair decal windows. A coarser OUTER V-SCAN (v roughly 0.75-0.95, any u)
     is also collected to show what other rows exist near this one (row/column substructure).
  4. Per cluster, per hit: same-CELL family context (straddle candidate) else an expanding-radius
     search (fringe candidate, mirrors ``orphangate.row_lawfulness``) determines a usage law,
     with sample sizes reported honestly -- clusters below a stated n are flagged, not law-ified.

Nothing is deployed, mirrored, or written outside this repo's own ``studies/`` tree. Reads only.
Run from the repo root:  py studies/overworld-topography/vband_decode.py
"""
from __future__ import annotations

import collections
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))

from ff9mapkit.world import extract as X                     # noqa: E402

# ---- the target band (Round 10's flagged lead, verbatim) -----------------------------------------------------------
V_LO, V_HI = 0.83594, 0.86621
V_TOL = 0.0015                 # ~6 texels at a 4096px atlas row pitch -- generous vs rounding, tight vs the
                                # ~0.03 row-to-row spacing (no risk of merging an adjacent row)
U_TOL = 0.0015

# known leads, for auto-labelling clusters that reproduce them
KNOWN = {
    ("grass", "scrub"): (0.34082, 0.40332),
    ("dunes", "mural"): (0.13867, 0.19922),
}

# ---- the extended family table (walkable GROUNDS families + forest/rock/shore/lip -- the dunes|mural lead
# pairs a GROUNDS family against the uncatalogued rock/mural axis, so that axis must be visible as context too)
FAM_OF = {}
for _t in (0, 1, 2, 3, 10, 11, 12, 13, 42):
    FAM_OF[_t] = "grass"
for _t in (4, 5, 6):
    FAM_OF[_t] = "scrub"
for _t in (16, 17, 19, 20):
    FAM_OF[_t] = "desert"
for _t in (27, 28):
    FAM_OF[_t] = "snow"
FAM_OF[38] = "brush"
FAM_OF[41] = "dunes"
for _t in (45, 46):
    FAM_OF[_t] = "canyon"
for _t in (36, 37):
    FAM_OF[_t] = "forest"
for _t in (49, 7, 62):
    FAM_OF[_t] = "rock"          # incl. topo-49 -- the "mural" surface the dunes lead names
for _t in (31, 32, 33):
    FAM_OF[_t] = "shore"
FAM_OF[58] = "lip"
del _t

# accept radii for the fringe-partner search (mirrors orphangate.ACCEPT_RADIUS/MAX_BAND_RADIUS, widened by
# one step since this is a DISCOVERY census, not a gate re-checking an already-known law)
ACCEPT_RADIUS = 2
MAX_SEARCH_RADIUS = 6

MIN_LAWFUL_N = 5           # below this, a usage-rate claim is flagged "too few instances to law-ify"


def cell_of(x: float, z: float) -> tuple:
    return (math.floor(x / 4.0), math.floor(z / 4.0))


def tri_uv_bbox(uvs):
    us = [p[0] for p in uvs]
    vs = [p[1] for p in uvs]
    return min(us), min(vs), max(us), max(vs)


def find_partner(cell, own_fam, cell_fams, *, max_radius=MAX_SEARCH_RADIUS):
    """Round-10-style context search: same-cell partner (radius 0, straddle) else expanding
    Chebyshev rings (fringe). Returns (kind, partner_fams_sorted, radius) -- ``kind`` in
    {"straddle", "fringe", "isolated"}; multiple co-present partner families at the SAME radius
    are all reported (never silently collapsed to one)."""
    here = cell_fams.get(cell, set()) - {own_fam}
    if here:
        return "straddle", sorted(here), 0
    for r in range(1, max_radius + 1):
        found = set()
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                if max(abs(di), abs(dj)) != r:
                    continue
                nb = (cell[0] + di, cell[1] + dj)
                fams = cell_fams.get(nb)
                if fams:
                    found |= (fams - {own_fam})
        if found:
            return "fringe", sorted(found), r
    return "isolated", [], None


def main():
    cell_fams = collections.defaultdict(set)
    cell_topos = collections.defaultdict(collections.Counter)

    primary_hits = []           # full-tile matches against the target band
    partial_hits = []           # boundary/partial residue (any corner touches the band, not full coverage)
    outer_rows = collections.defaultdict(lambda: dict(n=0, u_min=1.0, u_max=0.0, topos=collections.Counter()))
    blocks_scanned = 0
    blocks_missing = 0
    tris_scanned = 0

    for bx in range(24):
        for by in range(20):
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except (ValueError, FileNotFoundError):
                blocks_missing += 1
                continue
            blocks_scanned += 1
            ox, oz = X.block_world_origin(bx, by)
            verts, uvs = bm.verts, bm.uvs
            for tri in bm.tris:
                tris_scanned += 1
                topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
                fam = FAM_OF.get(topo)
                wpts = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
                cx = sum(p[0] for p in wpts) / 3.0
                cz = sum(p[2] for p in wpts) / 3.0
                cell = cell_of(cx, cz)
                if fam:
                    cell_fams[cell].add(fam)
                    cell_topos[cell][topo] += 1

                tri_uvs = [uvs[j] for j in tri]
                u0, v0, u1, v1 = tri_uv_bbox(tri_uvs)

                # outer row histogram: any tri whose v-bbox sits in a wide window around the target,
                # bucketed by its OWN (v0,v1) rounded coarsely -- reveals neighbouring rows/columns
                if 0.75 <= v0 and v1 <= 0.95 and (v1 - v0) < 0.05:
                    key = (round(v0, 4), round(v1, 4))
                    rec = outer_rows[key]
                    rec["n"] += 1
                    rec["u_min"] = min(rec["u_min"], u0)
                    rec["u_max"] = max(rec["u_max"], u1)
                    rec["topos"][topo] += 1

                full_match = (abs(v0 - V_LO) <= V_TOL and abs(v1 - V_HI) <= V_TOL)
                any_touch = any(V_LO - V_TOL <= p[1] <= V_HI + V_TOL for p in tri_uvs)

                if full_match:
                    primary_hits.append(dict(
                        block=(bx, by), cell=cell, topo=topo, fam=fam,
                        world_xz=(round(cx, 3), round(cz, 3)), world_y=round(sum(p[1] for p in wpts) / 3.0, 3),
                        u_bbox=(round(u0, 5), round(u1, 5)), v_bbox=(round(v0, 5), round(v1, 5)),
                    ))
                elif any_touch:
                    partial_hits.append(dict(
                        block=(bx, by), cell=cell, topo=topo, fam=fam,
                        world_xz=(round(cx, 3), round(cz, 3)),
                        u_bbox=(round(u0, 5), round(u1, 5)), v_bbox=(round(v0, 5), round(v1, 5)),
                    ))

    # ---- cluster primary hits by their own (min_u, max_u) rounded to 5dp ------------------------------------------
    by_u = collections.defaultdict(list)
    for h in primary_hits:
        by_u[h["u_bbox"]].append(h)

    clusters = []
    for u_bbox, hits in sorted(by_u.items()):
        v_los = [h["v_bbox"][0] for h in hits]
        v_his = [h["v_bbox"][1] for h in hits]
        own_fam_ct = collections.Counter(h["fam"] for h in hits)
        own_topo_ct = collections.Counter(h["topo"] for h in hits)

        # context classification per hit
        kinds = collections.Counter()
        partner_fam_ct = collections.Counter()
        instances = []
        for h in hits:
            kind, partners, radius = find_partner(h["cell"], h["fam"], cell_fams)
            kinds[kind] += 1
            for p in partners:
                partner_fam_ct[p] += 1
            instances.append(dict(
                block=list(h["block"]), cell=list(h["cell"]), topo=h["topo"], fam=h["fam"],
                world_xz=list(h["world_xz"]), world_y=h.get("world_y"),
                usage=kind, partner_families=partners, radius=radius,
            ))

        n = len(hits)
        # honest pair label: own family (mode) paired with the dominant partner family (mode), IF any
        own_mode = own_fam_ct.most_common(1)[0][0] if own_fam_ct else None
        partner_mode = partner_fam_ct.most_common(1)[0][0] if partner_fam_ct else None
        pair_guess = tuple(sorted(x for x in (own_mode, partner_mode) if x)) if partner_mode else None

        known_match = None
        for k_pair, (ku0, ku1) in KNOWN.items():
            if abs(u_bbox[0] - ku0) <= U_TOL and abs(u_bbox[1] - ku1) <= U_TOL:
                known_match = list(k_pair)
                break

        caveat = None
        if n < MIN_LAWFUL_N:
            caveat = f"n={n} -- too few instances to law-ify a usage rate; reporting raw counts only"

        clusters.append(dict(
            u_bbox=list(u_bbox),
            v_bbox_observed=[round(min(v_los), 5), round(max(v_his), 5)],
            v_bbox_row_target=[V_LO, V_HI],
            n_tris=n,
            own_family_histogram=dict(own_fam_ct),
            own_topo_histogram={int(k): v for k, v in own_topo_ct.items()},
            usage_histogram=dict(kinds),
            partner_family_histogram=dict(partner_fam_ct),
            pair_guess=list(pair_guess) if pair_guess else None,
            known_match=known_match,
            sample_size_caveat=caveat,
            instances=instances,
        ))

    # ---- pair-level convenience aggregate: group raw clusters sharing the same guessed/known pair -----------------
    # (the raw per-exact-uv-bbox clusters above remain the primary evidence; this view answers "how many
    # distinct family PAIRS use this row" without deciding whether two adjacent/nested raw windows are the
    # same physical tile or two distinct roles -- that judgement is left to the write-up, not baked in here)
    pair_groups = collections.defaultdict(lambda: dict(clusters=[], total_n=0, usage=collections.Counter()))
    for c in clusters:
        key = tuple(c["known_match"] or c["pair_guess"] or ["?"])
        g = pair_groups[key]
        g["clusters"].append(c["u_bbox"])
        g["total_n"] += c["n_tris"]
        for k, v in c["usage_histogram"].items():
            g["usage"][k] += v

    pairs_summary = []
    for key, g in sorted(pair_groups.items()):
        us = [u for win in g["clusters"] for u in win]
        pairs_summary.append(dict(
            pair=list(key), n_raw_windows=len(g["clusters"]), raw_windows=sorted(g["clusters"]),
            u_envelope=[round(min(us), 5), round(max(us), 5)], total_n=g["total_n"],
            usage_histogram=dict(g["usage"]),
            caveat=(f"n={g['total_n']} total across {len(g['clusters'])} raw window(s) -- "
                    f"too few to law-ify a usage rate" if g["total_n"] < MIN_LAWFUL_N else None),
        ))

    # ---- outer row context (row/column substructure question) --------------------------------------------------
    outer_summary = []
    for (rv0, rv1), rec in sorted(outer_rows.items()):
        outer_summary.append(dict(
            v_bbox=[rv0, rv1], n_tris=rec["n"],
            u_range=[round(rec["u_min"], 5), round(rec["u_max"], 5)],
            topo_histogram={int(k): v for k, v in rec["topos"].items()},
            is_target_row=(abs(rv0 - V_LO) <= V_TOL and abs(rv1 - V_HI) <= V_TOL),
        ))

    result = dict(
        meta=dict(
            script="studies/overworld-topography/vband_decode.py",
            disc=1, blocks_scanned=blocks_scanned, blocks_missing=blocks_missing,
            tris_scanned=tris_scanned,
            v_lo=V_LO, v_hi=V_HI, v_tol=V_TOL, u_tol=U_TOL,
            accept_radius=ACCEPT_RADIUS, max_search_radius=MAX_SEARCH_RADIUS,
            min_lawful_n=MIN_LAWFUL_N,
            note="read-only census against real stock disc-1 bytes; zero writes, zero deploys, zero mirror.",
        ),
        n_primary_hits=len(primary_hits),
        n_partial_hits=len(partial_hits),
        n_clusters=len(clusters),
        clusters=clusters,
        pairs_summary=pairs_summary,
        partial_hits_sample=partial_hits[:40],
        n_partial_hits_total=len(partial_hits),
        outer_row_context=outer_summary,
    )

    out_path = HERE / "out" / "vband_census.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=1), encoding="utf-8")

    print(f"blocks scanned: {blocks_scanned} (missing/empty: {blocks_missing})")
    print(f"tris scanned:   {tris_scanned}")
    print(f"primary hits:   {len(primary_hits)}  in {len(clusters)} u-window cluster(s)")
    print(f"partial hits:   {len(partial_hits)}")
    print()
    for c in clusters:
        label = c["known_match"] or c["pair_guess"] or "?"
        print(f"  u{c['u_bbox']} v_obs{c['v_bbox_observed']} n={c['n_tris']:4d} "
              f"own={c['own_family_histogram']} usage={c['usage_histogram']} "
              f"partner={c['partner_family_histogram']} -> {label} {c['sample_size_caveat'] or ''}")
    print()
    print("pair-level summary:")
    for p in pairs_summary:
        print(f"  {p['pair']}: envelope u{p['u_envelope']} total_n={p['total_n']} "
              f"windows={p['raw_windows']} usage={p['usage_histogram']} {p['caveat'] or ''}")
    print()
    print("outer row context (v in [0.75,0.95]):")
    for r in outer_summary:
        star = "  <== TARGET ROW" if r["is_target_row"] else ""
        print(f"  v{r['v_bbox']} n={r['n_tris']:5d} u_range{r['u_range']} topos={r['topo_histogram']}{star}")
    print()
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
