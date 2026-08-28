"""THE CANVAS CENSUS (read-only, 2026-07-25).

Produces studies/overworld-topography/out/world-design/canvas.json + canvas.png:
  (1) LIVE CENSUS  -- every override block on the shared install RIGHT NOW, grouped into
      clusters, cross-referenced against the study record.
  (2) FREE SPACE   -- reuses the fold-back forbidden-block machinery (stock prefab-occupied +
      live-deployed + study-named benches) to map the free ocean, binned by radius class
      (r132/r96/r72/r48), general (unconstrained-centre) sweep -- NOT the whole-block-shift
      lattice that only the two-ground JUNCTION carry is bound to.
  (3) CAPABILITY MANIFEST -- verified against cli.py / grassland.py / interior.py, not memory.
  (4) ENTRANCE CAPACITY -- reads the LIVE dispatcher .eb, finds the AREA switch (base 2, 59
      cases), counts dead (== default target) vs alive cases; cross-checks DictionaryPatch
      FieldScene ids in both mod folders.
  (5) RENDER -- a 24x20 block-grid PNG: stock land (grey) / live clusters (colored, labeled) /
      named-bench reserves (hatched) / free ocean (blue) with the best free-radius circles
      overlaid for each size class.

READ-ONLY: never writes the install. Caches stock occupancy/land in out/foldback/stock_grid.json
(shared with the fold-back study; regenerated there, reused here).

    py -X utf8 canvas_census.py
"""
from __future__ import annotations

import glob
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import island as ISL         # noqa: E402
from ff9mapkit import config as CFG               # noqa: E402

OUT_DIR = HERE / "out" / "world-design"
FOLDBACK = HERE / "out" / "foldback"
BLOCK = 64.0
NX, NZ = 24, 20
WORLD_W, WORLD_H = BLOCK * NX, BLOCK * NZ

# THE STUDY'S NAMED-BENCH REGISTRY (freshmint_site_scan.py NAMED_BENCH_BLOCKS, reproduced here so
# this script has no import-order dependency on that study file). Kept verbatim + labeled.
NAMED_BENCHES = {
    "rung-F / the accepted two-ground junction island (site rect)":
        {(bx, by) for bx in range(0, 5) for by in range(15, 20)},
    "first-continent archipelago remnant (island E lineage / topology rounds 6-7 target)":
        {(6, 18), (6, 19), (7, 18), (7, 19), (8, 19)},
    "relief-demo island (r44, --relief, world (672,-608))":
        {(9, 9), (10, 8), (10, 9), (10, 10), (11, 8), (11, 9)},
    "desert-fidelity-check island (r52 seed-11, GroundRetile donor (8,17)/(9,17)-family)":
        {(11, 18), (11, 19), (12, 18), (12, 19)},
    "horseshoe/crag mountain bench region (r72-class bench footprint)":
        {(18, 17), (18, 18), (18, 19), (19, 17), (19, 18), (19, 19), (20, 17), (20, 18), (20, 19)},
    "donor read window -- Cleyra junction donor (13-15,11-12) + margin, NEVER a mint target":
        {(bx, by) for bx in range(12, 17) for by in range(10, 14)},
    "stock dunes envelope-calibration reference (read-only, not a mint)":
        {(18, 3), (19, 3), (20, 3)},
}
ALL_NAMED = set().union(*NAMED_BENCHES.values())


def live_blocks_fresh(live_root: Path) -> dict:
    """Fresh (uncached) scan of every Block override actually on disk right now, both discs."""
    pat = re.compile(r"Disc(\d+)[\\/][^\\/]+[\\/]r\d+[\\/]Block\[(\d+)\]\[(\d+)\]")
    by_disc = {}
    for f in glob.glob(str(live_root / "FF9_Data" / "WorldMap" / "**" / "Block*"), recursive=True):
        m = pat.search(str(Path(f)))
        if m:
            disc, bx, by = int(m.group(1)), int(m.group(2)), int(m.group(3))
            by_disc.setdefault(disc, set()).add((bx, by))
    return by_disc


def cluster_blocks(blocks: set) -> list:
    """Connected components at block-adjacency (4-neighbour, x-wrap-aware)."""
    remaining = set(blocks)
    comps = []
    while remaining:
        seed = next(iter(remaining))
        stack, comp = [seed], set()
        while stack:
            b = stack.pop()
            if b in comp:
                continue
            comp.add(b)
            remaining.discard(b)
            bx, by = b
            for nb in ((bx - 1, by), (bx + 1, by), (bx, by - 1), (bx, by + 1),
                       ((bx - 1) % NX, by), ((bx + 1) % NX, by)):
                if nb in remaining:
                    stack.append(nb)
        comps.append(sorted(comp))
    return sorted(comps, key=lambda c: (min(c), len(c)))


def block_files(live_root: Path, disc: int, bx: int, by: int) -> list:
    d = live_root / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
    return sorted(p.name for p in d.glob(f"Block[{bx}][{by}]*")) if d.exists() else []


def donor_of(live_root: Path, disc: int, bx: int, by: int):
    f = live_root / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Donor.txt"
    return f.read_text().strip() if f.exists() else None


def label_for(comp: list) -> str:
    hits = {name for name, blocks in NAMED_BENCHES.items() if blocks & set(comp)}
    if hits:
        return " + ".join(sorted(hits))
    return "UNRECORDED cluster (not in the study's named-bench registry)"


def gather_stock_cached(game):
    cache = FOLDBACK / "stock_grid.json"
    if cache.exists():
        d = json.loads(cache.read_text())
        return ([tuple(p) for p in d["land"]],
                {tuple(map(int, k.split(","))): v for k, v in d["occ"].items()})
    # not expected on a normal run -- the fold-back study already built this cache; keep a
    # fallback path so this script is still runnable standalone (slow: ~1-2 min).
    land, occ = [], {}
    for by in range(NZ):
        for bx in range(NX):
            p = ISL._real_block_parts((bx, by), disc=1, lod="0_1", game=game)
            if p:
                occ[(bx, by)] = p
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except Exception:
                continue
            ox, oz = X.block_world_origin(bx, by)
            for v in bm.verts:
                if v[1] > 0.6:
                    land.append((v[0] + ox, v[2] + oz))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dict(land=[list(p) for p in land],
                                     occ={f"{k[0]},{k[1]}": v for k, v in occ.items()})))
    return land, occ


def footprint_blocks(cx, cz, r):
    out = set()
    for bx in range(NX):
        for by in range(NZ):
            x0, x1 = BLOCK * bx, BLOCK * (bx + 1)
            z1, z0 = -BLOCK * by, -BLOCK * (by + 1)
            dx = 0.0 if x0 <= cx <= x1 else min(
                abs(cx - x0), abs(cx - x1),
                abs(cx - x0 + WORLD_W), abs(cx - x1 + WORLD_W),
                abs(cx - x0 - WORLD_W), abs(cx - x1 - WORLD_W))
            dz = 0.0 if z0 <= cz <= z1 else min(abs(cz - z0), abs(cz - z1))
            if math.hypot(dx, dz) <= r:
                out.add((bx, by))
    return out


def free_space_sweep(forbidden: set, step: float = 16.0, pad: float = 8.0):
    """General (unconstrained-centre) free-space sweep -- appropriate for world-island /
    world-mountain / world-forest / world-hill, which (unlike the two-ground junction) carry no
    whole-block-shift alignment requirement. Returns best sites per radius class."""
    fb = sorted(forbidden)

    def nearest_forbidden(cx, cz):
        best = 1e9
        for (bx, by) in fb:
            x0, x1 = BLOCK * bx, BLOCK * (bx + 1)
            z1, z0 = -BLOCK * by, -BLOCK * (by + 1)
            dx = 0.0 if x0 <= cx <= x1 else min(
                abs(cx - x0), abs(cx - x1),
                abs(cx - x0 + WORLD_W), abs(cx - x1 + WORLD_W),
                abs(cx - x0 - WORLD_W), abs(cx - x1 - WORLD_W))
            dz = 0.0 if z0 <= cz <= z1 else min(abs(cz - z0), abs(cz - z1))
            d = math.hypot(dx, dz)
            if d < best:
                best = d
            if best <= 0.0:
                return 0.0
        return best

    rows = []
    for cx in np.arange(step / 2, WORLD_W, step):
        # THE OFFSEAM CAP IS LIFTED (2026-08-27). It existed because island._split_at_borders
        # could not wrap bx, so no mint could cross x=0/1536; the seam-wrap fix closed that and
        # the r20 bench islet playtest CONFIRMED the seam is walkable land (owner: position jump
        # with no visible seam or stutter; the boat's toroidal standoff belt holds through it).
        # nearest_forbidden was already toroidal in x -- the cap was the only x constraint. The
        # z edges stay: rows 0..19 are the engine's hard grid.
        for cz in np.arange(-step / 2, -WORLD_H, -step):
            edge = min(abs(cz), abs(-WORLD_H - cz))
            cap = edge
            if cap < 20.0:
                continue
            clr = nearest_forbidden(float(cx), float(cz))
            rmax = min(clr, cap)
            if rmax < 20.0:
                continue
            rows.append((float(cx), float(cz), round(rmax, 1)))

    classes = {}
    for lo, name in ((132.0, "r132"), (96.0, "r96"), (72.0, "r72"), (48.0, "r48")):
        sites = [r for r in rows if r[2] >= lo]
        sites.sort(key=lambda r: -r[2])
        # de-duplicate near-identical top sites (keep spatially distinct ones)
        picked = []
        for r in sites:
            if all(math.hypot(r[0] - p[0], r[1] - p[1]) > 48.0 for p in picked):
                picked.append(r)
            if len(picked) >= 8:
                break
        classes[name] = dict(min_radius=lo, n_sites=len(sites),
                             top=[dict(cx=r[0], cz=r[1], r_max=r[2]) for r in picked])
    return classes, rows


def entrance_capacity(game):
    from ff9mapkit.eb import edit as E
    from ff9mapkit.eb.model import EbScript
    live = Path(game) / "FF9CustomMap-world" / "StreamingAssets" / "assets" / "resources" / \
        "commonasset" / "eventengine" / "eventbinary" / "world" / "us" / "EVT_WORLD_WORLD11.eb.bytes"
    result = {"source": str(live), "exists": live.exists()}
    if not live.exists():
        return result
    data = live.read_bytes()
    eb = EbScript.from_bytes(data)
    f, ins, si = E.find_switch(eb, 1, 1, switch_base=2)
    default_target = next(e.target for e in si.edges if e.is_default)
    cases = [e for e in si.edges if not e.is_default]
    dead = sorted(e.value for e in cases if e.target == default_target)
    alive = sorted(e.value for e in cases if e.target != default_target)
    result.update(total_cases=len(cases), dead_cases=dead, n_dead=len(dead),
                  alive_cases=alive, n_alive=len(alive),
                  note="dead == routes to the switch default (never fires); a nameplate-surgery "
                       "target repoints exactly one dead case to Field(<id>) + an explored-bit set. "
                       "case 53 (NAMEPLATE_SURGERY_CASE default) is in this list -> no custom "
                       "entrance is currently live on this install.")
    return result


def dictionary_patch_ids(game):
    out = {}
    for folder in ("FF9CustomMap", "FF9CustomMap-world"):
        p = Path(game) / folder / "DictionaryPatch.txt"
        ids = []
        if p.exists():
            ids = sorted({int(m) for m in re.findall(r"FieldScene (\d+)", p.read_text())})
        out[folder] = ids
    return out


def band_of(i: int) -> str:
    if 10 <= i <= 3100:
        return "real (locked)"
    if 4000 <= i <= 9899:
        return "reserved-hole 9000-9012" if 9000 <= i <= 9012 else "shipped-custom"
    if 30000 <= i <= 32767:
        return "dev-scratch"
    return "OFF-BAND"


def main():
    import argparse
    ap = argparse.ArgumentParser(description="the world-design canvas census")
    ap.add_argument("--exclude-cells", default=None, metavar="BX,BY;BX,BY;...",
                    help="treat these deployed cells as FREE in the written _forbidden_blocks.json "
                         "(recorded under its 'excluded' key). For planning a build that REPLACES "
                         "our own scratch content -- e.g. the r20 seam bench islet inside the "
                         "ratified (48,-240) pocket. The live-census section stays honest either "
                         "way; only the sidecar the siting pipeline consumes is filtered.")
    args = ap.parse_args()
    excluded = set()
    if args.exclude_cells:
        excluded = {tuple(int(v) for v in c.split(",")) for c in args.exclude_cells.split(";") if c}
    game = CFG.find_game_path(None)
    live_root = Path(game) / "FF9CustomMap-world"
    print("game:", game)
    if excluded:
        print("EXCLUDED from the forbidden sidecar (ours, replaceable):", sorted(excluded))

    # ---------- (1) LIVE CENSUS ----------
    by_disc = live_blocks_fresh(live_root)
    disc1 = by_disc.get(1, set())
    disc4 = by_disc.get(4, set())
    clusters = cluster_blocks(disc1)
    cluster_detail = []
    for comp in clusters:
        sample = comp[len(comp) // 2]
        files_sample = block_files(live_root, 1, *sample)
        donor_sample = donor_of(live_root, 1, *sample)
        bxs = [b[0] for b in comp]
        bys = [b[1] for b in comp]
        cluster_detail.append(dict(
            label=label_for(comp), n_blocks=len(comp), blocks=[list(b) for b in comp],
            bbox=dict(bx=[min(bxs), max(bxs)], by=[min(bys), max(bys)]),
            sample_block=list(sample), sample_files=files_sample, sample_donor=donor_sample,
        ))
    unrecorded = [c for c in cluster_detail if c["label"].startswith("UNRECORDED")]
    named_but_absent = {name: sorted(blocks) for name, blocks in NAMED_BENCHES.items()
                        if not (blocks & disc1) and "donor read window" not in name
                        and "calibration reference" not in name}
    disc_mismatch = sorted((disc1 | disc4) - (disc1 & disc4))

    live_census = dict(
        disc1_block_count=len(disc1), disc4_block_count=len(disc4),
        discs_match=(disc1 == disc4), disc_mismatch_blocks=[list(b) for b in disc_mismatch],
        n_clusters=len(clusters), clusters=cluster_detail,
        unrecorded_cluster_count=len(unrecorded),
        named_benches_in_registry_but_absent_from_live=named_but_absent,
    )

    # ---------- (2) FREE SPACE ----------
    stock_land, stock_occ = gather_stock_cached(game)
    forbidden = (disc1 | ALL_NAMED | set(stock_occ)) - excluded
    print(f"stock prefab-occupied {len(stock_occ)}  live {len(disc1)}  "
          f"named-extra {len(ALL_NAMED - disc1 - set(stock_occ))}  forbidden total {len(forbidden)}")
    classes, all_rows = free_space_sweep(forbidden)
    free_blocks = 480 - len(forbidden)
    free_space = dict(
        method="general unconstrained-centre 16u sweep; forbidden = stock prefab-occupied blocks "
               "(THE OPEN-OCEAN TARGET LAW) + every live-deployed block (fresh scan) + every "
               "study-named bench/reserve; NOT the whole-block-shift lattice (that constraint is "
               "unique to the two-ground junction carry, see junction_note below).",
        grid_blocks=480, stock_prefab_occupied=len(stock_occ), live_deployed=len(disc1),
        named_reserved_extra=len(ALL_NAMED - disc1 - set(stock_occ)),
        forbidden_total=len(forbidden), free_blocks_by_count=free_blocks,
        by_radius_class=classes,
        junction_note="THE ONE-SITE WORLD LAW (fold-back study, 2026-07-25, freshmint_report.json): "
                       "on the WHOLE-BLOCK-SHIFT lattice the two-ground junction carry's donor "
                       "requires, the world admits exactly ONE legal centre at R>=125 -- (160,-1152), "
                       "the rung-F site itself. No second two-ground junction of this donor's size "
                       "fits anywhere else; best remaining lattice centre is (160,-128) at R=115.38, "
                       "below the pipeline's own measured floor (121u). This general sweep answers a "
                       "DIFFERENT question (unconstrained world-island/mountain/forest/hill fills).",
    )

    # ---------- (3) CAPABILITY MANIFEST ----------
    from ff9mapkit.world.grassland import GROUNDS
    capability_manifest = {
        "world-island": dict(
            verb="world-island", donors="n/a (procedural mint)", size_class="--radius (u); "
            "--cell centres on a single ocean block, --center allows multi-block spans",
            grounds=sorted(GROUNDS), ground_classes={k: v.get("cls") for k, v in GROUNDS.items()},
            constraints=["adaptive-outline density past r60", "--relief mutually exclusive with "
                        "world-hill/forest/mountain on the same island (2.4u rolling-relief "
                        "envelope gate)", "dunes SIZE CLASS >=~130-cell footprint (quilts smaller)",
                        "meadow --patches only fit on grass"],
            verified_against="ff9mapkit/ff9mapkit/cli.py world-island parser"),
        "world-forest (carve_forest)": dict(
            verb="world-forest", donors="topo-37 canopy blob; default (15,15), the proven "
                "grass-bounded donor -- a multi-blob/non-simple-rim donor refuses",
            size_class="single canopy blob per call, seated via --center/--near on a DEPLOYED island",
            constraints=["THE CANOPY STEP LAW (wall rises <=2.2u under the 2.34375u step ceiling)",
                        "perimeter walk-in simulation gate", "just re-fixed/being re-verified in a "
                        "parallel lane this round per the round brief"],
            verified_against="ff9mapkit/ff9mapkit/world/interior.py:carve_forest + cli.py world-forest parser"),
        "world-hill (build_hill)": dict(
            verb="world-hill", donors="n/a (raised-cosine dome, pure-Y displacement of deployed bytes)",
            size_class="--height default 4.2 (real language 3.5-5.2), --radius default 18 (real 20-26u diam)",
            constraints=["lowland-band peak cap", "local normal re-smooth only"],
            verified_against="ff9mapkit/ff9mapkit/world/interior.py:build_hill + cli.py world-hill parser"),
        "world-mountain (carve_mountain)": dict(
            verb="world-mountain", donors="Uaho (0,0) default; crag (10,5-6); horseshoe (5-6,15-16); "
                "comp20 (12,16-17) -- CARRY ONLY, synthesis falsified over 8 rounds",
            size_class="per-donor fixed (Uaho ~r31 bench pocket ceiling ~23.5u; horseshoe needs ~r69-72 "
                "bench, r69 world-island mint not robustly clean across seeds)",
            grounds=sorted(GROUNDS),
            constraints=["ROCK-RIGID", "weld-safe per-position apron lift", "DP zip envelope",
                        "aperture must validate against object OR the full ensemble part union",
                        "a NEW donor needs its own anatomy study first"],
            verified_against="ff9mapkit/ff9mapkit/world/interior.py:carve_mountain + cli.py world-mountain parser"),
        "junction_compose (two-ground landmass)": dict(
            verb="NOT a CLI verb -- study script only (studies/overworld-topography/junction_compose.py)",
            donors="Cleyra donor window (13-15,11-12)",
            size_class="r125-132 class; THE ONE-SITE WORLD LAW: fits at exactly one whole-block-"
                "lattice centre world-wide -- the existing accepted island. A smaller donor window "
                "would need a new study round.",
            constraints=["36-gate battery", "whole-block SHIFT lattice (cx%64==32, cz%64==0)"],
            verified_against="studies/overworld-topography/freshmint_report.json (2026-07-25) + "
                "junction_compose.py docstring"),
        "GroundRetile beach carry": dict(
            verb="world-transplant / retile machinery",
            donors="(7,17) grass, (8,17) desert, (10,17) desert-family (per the round brief)",
            size_class="per-cell/per-window carry", constraints=["THE MOD-OVERWRITE GATE"],
            verified_against="studies/overworld-topography/README.md desert-fidelity-check section"),
        "native entrance (area-switch surgery)": dict(
            verb="world-entrance --field-direct + --nameplate-name (nameplate surgery route)",
            donors="n/a (repoints a dead AREA-switch case)",
            size_class="1 dead case per entrance; 59 total non-default cases in the switch",
            constraints=["needs a DEAD case (arm==default)", "field id must be 0..0x7FFF",
                        "per-language repoint (7 langs) since the switch is present in every "
                        "free-roam dispatcher"],
            verified_against="ff9mapkit/ff9mapkit/world/entrance.py + live EVT_WORLD_WORLD11.eb.bytes read this run"),
        "world-encounters (zone-keyed)": dict(
            verb="world-encounters", donors="n/a", size_class="n/a",
            constraints=["zone 0 shared with Mist -- private per-landmass tables need the DLL round"],
            verified_against="round brief (not independently re-verified this pass)"),
        "world-minimap composite": dict(
            verb="world-minimap", donors="n/a", size_class="n/a",
            constraints=["pause-map dots for custom locations IMPOSSIBLE without an engine table "
                        "edit -- navipos is all-zero (known limit, not re-litigated this pass)"],
            verified_against="round brief (not independently re-verified this pass)"),
        "vehicles": dict(verb="TransportControls.csv (physics) + boarding/dismount",
            donors="n/a", size_class="n/a",
            constraints=["rungs 0-2 proven; boarding/dismount partially open (round brief)"],
            verified_against="round brief (not independently re-verified this pass)"),
    }

    # ---------- (4) ENTRANCE CAPACITY ----------
    ent = entrance_capacity(game)
    dict_ids = dictionary_patch_ids(game)
    field_budget = {folder: {"ids": ids, "by_band": {i: band_of(i) for i in ids}}
                   for folder, ids in dict_ids.items()}
    shipped_custom_used = sorted(i for ids in dict_ids.values() for i in ids
                                 if band_of(i) == "shipped-custom")
    scratch_used = sorted(i for ids in dict_ids.values() for i in ids if band_of(i) == "dev-scratch")

    # ---------- assemble ----------
    canvas = dict(
        generated_by="studies/overworld-topography/canvas_census.py",
        game_install=str(game),
        live_census=live_census,
        free_space=free_space,
        capability_manifest=capability_manifest,
        entrance_capacity=dict(
            area_switch=ent,
            dictionary_patch_field_ids=field_budget,
            shipped_custom_ids_used=shipped_custom_used,
            dev_scratch_ids_used=scratch_used,
            shipped_custom_band_width=9899 - 4000 + 1 - (9012 - 9000 + 1),
            note="Field-id headroom is effectively unconstrained (5 of ~5870 shipped-custom slots "
                "used); the real entrance-capacity ceiling is the AREA-switch dead-case budget.",
        ),
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "canvas.json").write_text(json.dumps(canvas, indent=1))
    print("wrote", OUT_DIR / "canvas.json")

    # stash the raw sweep rows for the renderer (not part of the design-facing json)
    (OUT_DIR / "_free_sweep_rows.json").write_text(json.dumps(all_rows))
    (OUT_DIR / "_forbidden_blocks.json").write_text(json.dumps(dict(
        stock_occ=[list(b) for b in sorted(set(stock_occ) - excluded)], live=[list(b) for b in sorted(disc1 - excluded)],
        named=[list(b) for b in sorted(set(ALL_NAMED) - excluded)],
        excluded=[list(b) for b in sorted(excluded)],
        clusters=[dict(label=c["label"], blocks=c["blocks"]) for c in cluster_detail])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
