"""THE DONOR-RETILE SCREEN -- map-wide qualification of every beach-bearing block/island as a
``GroundRetile.for_donor`` donor for the two mintable coastal targets (desert, snow), reusing the
shipped gate machinery WITHOUT writing anything (no deploy, no mint, no game/install writes).

Answers the roadmap SOON item: "Screen remaining beach/snow/canyon coastal donors -- only
(7,17)/(10,17) proven of ~44 beach-bearing blocks."

Method:

  1. Enumerate every disc-1 data block (``extract.list_blocks``); classify BEACH-BEARING as
     ``beach1`` part non-empty OR terrain carries topo in {31 sand, 32 desert-sand, 33 frozen-shore}
     (``coastmorph.SAND_BANDS`` + the frozen-shore earmark in that module's header comment).
  2. Cluster ALL data blocks into landmass connected components over the WRAP-AWARE 24x20 block
     grid (``navimap._wrap_world`` -- the overworld's real toroidal adjacency; a block's E/W/N/S
     neighbour is taken mod GRID_X/GRID_Y). Islands are the SMALL components (<= 12 blocks); the
     mainland is the one giant component every coastal beach block on the continent belongs to.
  3. Beach blocks in a small component collapse to ONE multi-block window = that component's
     bounding rectangle (unwrapped around a reference corner so ``for_donor``'s plain-integer
     ``dbx+i``/``dby+j`` gather is valid -- ``GroundRetile.for_donor`` does NOT itself wrap).
     SELF-CONTAINMENT is checked: does the bounding rect's data footprint match the component
     exactly, or does it clip in a a different island/the mainland? Beach blocks in the giant
     mainland component (or non-self-contained rects) fall back to a single-block (1,1) window --
     exactly how the proven (7,17) donor was screened.
  4. Per window x family in {desert, snow}: run the REAL qualification gate --
     ``GroundRetile.for_donor(donor, dst, size=..., strips=...)`` (catches every raise: same-family,
     no-measured-sand-family, non-monotone sand pins, THE WALL-CONTEXT LAW coastal-wall refusal),
     then, if it built, REGATHER the exact polys ``transplant()``/``transplant_region()`` would feed
     it (donor rect whole + the border strips) and re-``apply()`` + ``gate()`` -- because
     ``for_donor``'s own prescan only pre-assigns GRASS-topo recover cells; any OTHER residual
     unclassified content (wrong sand family, a non-terrain part with no rule) would only surface
     on a real ``apply()`` pass, never inside ``for_donor`` itself. Both ``strips="auto"`` and
     ``strips="none"`` are tried per window x family (the (10,17) STRIPS-PARITY precedent: auto
     drags in a neighbour's beach fragments and refuses for a no-sand-family target; none is
     byte-equivalent when the strip content wholly clips away).
  5. canyon is refused unconditionally by the WALL-CONTEXT LAW's ``wall_coastal`` chokepoint
     (``GROUNDS["canyon"]["wall_coastal"] is False`` -- an INTERIOR-only band, 0 open-sea faces
     map-wide) -- per the task, canyon is NOT screened window-by-window; only its candidate-window
     COUNT is tallied for the record.
  6. Two sanity anchors gate the whole screen (assert -- a screen that can't reproduce the two
     PROVEN in-game precedents is not trustworthy): (7,17) must qualify desert exactly as shipped;
     (10,17)+2x2 must qualify desert AND must reproduce the STRIPS-PARITY nuance for snow (refuse
     under strips=auto, qualify under strips=none).

Offline only. No deploys, no mint, no writes outside ``studies/overworld-topography/out/``.
Run from the repo root:  py studies/overworld-topography/donor_retile_screen.py
"""
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                              # noqa: E402
from ff9mapkit.world import transplant as TR                          # noqa: E402
from ff9mapkit.world import grassland as G                            # noqa: E402
from ff9mapkit.world.extract import decode_id                         # noqa: E402
from ff9mapkit.world.terrain import GRID_X, GRID_Y                    # noqa: E402

OUTD = Path(__file__).with_name("out")
OUTD.mkdir(exist_ok=True)
t0 = time.time()
out: dict = {}

# Per-(block,part) tri cache -- windows overlap heavily (shared neighbour strips, and every
# single-block mainland window re-reads its own E/N/S/W neighbours), and ``read_block`` re-scans
# the loaded Unity env's object list from scratch on every call with no cache of its own.
# ``GroundRetile.apply`` never mutates a poly in place (always returns fresh tuples in the
# touched branches, the same list reference untouched otherwise), so sharing the cached tri
# lists/tuples across many ``[list(t) for t in world_tris(...)]`` call sites is safe.
_tri_cache: dict = {}
_orig_world_tris = TR.world_tris


def _cached_world_tris(bx, by, part, *, disc=1, lod="0_1", game=None):
    key = (bx, by, part, disc, lod)
    if key not in _tri_cache:
        _tri_cache[key] = _orig_world_tris(bx, by, part, disc=disc, lod=lod, game=game)
    return _tri_cache[key]


TR.world_tris = _cached_world_tris          # for_donor calls the bare module-global name

BEACH_TOPOS = {31, 32, 33}                     # grass sand / desert sand / frozen-shore (coastmorph.py header)
SMALL_COMPONENT_MAX = 12                        # blocks -- islands are small; the mainland is huge
FAMILIES = ("desert", "snow")                   # canyon is tallied-only, never screened (wall_coastal law)


def log(msg):
    print(f"[{time.time() - t0:6.0f}s] {msg}", flush=True)


# ==== stage 1: map-wide data + beach classification ================================================
log("stage 1: reading every disc-1 data block, classifying beach content...")
blocks_all = sorted(X.list_blocks(disc=1))
data_set = set(blocks_all)
block_topos: dict = {}
beach_blocks = []
for (bx, by) in blocks_all:
    terr = TR.world_tris(bx, by, "terrain", disc=1)
    beach1 = TR.world_tris(bx, by, "beach1", disc=1)
    topos = {decode_id(int(round(t[0][3][0])))["topograph"] for t in terr}
    block_topos[(bx, by)] = topos
    if beach1 or (topos & BEACH_TOPOS):
        beach_blocks.append((bx, by))
beach_blocks.sort()
log(f"  {len(blocks_all)} data blocks map-wide, {len(beach_blocks)} beach-bearing "
    f"(earmark was ~44)")
out["totals"] = dict(data_blocks=len(blocks_all), beach_bearing_blocks=len(beach_blocks),
                     beach_bearing_list=[list(b) for b in beach_blocks])


# ==== stage 2: LAND-TRIANGLE edge-adjacency components ==============================================
# NOT block-asset adjacency: a first attempt clustered on "both blocks carry a terrain mesh" and
# collapsed 259/260 data blocks into ONE component -- near-shore/buffer blocks carry a terrain
# submesh even where their own land content is zero, so co-presence of a terrain ASSET says
# nothing about physical land connectivity. The real test (mirrors donor_qualify_scan.py's rock
# census, generalized from rock-only to ALL non-water topo): two land tris are adjacent iff they
# share a world-frame EDGE (position identity). A true island's shoreline tris border SEA-part
# tris (a different submesh), never another block's land tri, so islands fall out as their own
# components for free; the mainland is the one giant component its whole coastline welds into.
log("stage 2: land-triangle connected components (edge-sharing, not co-block)...")
_WATER = frozenset({53, 54, 55, 56, 57})
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))            # noqa: E731

land_tris = []
for (bx, by) in blocks_all:
    for t in TR.world_tris(bx, by, "terrain", disc=1):
        topo = decode_id(int(round(t[0][3][0])))["topograph"]
        if topo in _WATER:
            continue
        land_tris.append(dict(w=[v[0] for v in t], topo=topo, blk=(bx, by)))
log(f"  {len(land_tris)} land tris map-wide (non-water terrain topo)")

edge_tris = defaultdict(list)
for ti, t in enumerate(land_tris):
    ps = [kk(v) for v in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_tris[tuple(sorted((ps[a], ps[b])))].append(ti)
adj = defaultdict(set)
for ts in edge_tris.values():
    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            adj[ts[i]].add(ts[j])
            adj[ts[j]].add(ts[i])
seen: set = set()
tri_components = []
for s in range(len(land_tris)):
    if s in seen:
        continue
    comp = {s}
    st = [s]
    seen.add(s)
    while st:
        c = st.pop()
        for n in adj[c]:
            if n not in seen:
                seen.add(n)
                comp.add(n)
                st.append(n)
    tri_components.append(comp)
tri_components.sort(key=len, reverse=True)
log(f"  {len(tri_components)} land-tri components map-wide; sizes (top 10) "
    f"{[len(c) for c in tri_components[:10]]}")

# a block belongs to whichever land component owns the MOST of its land tris (a block whose
# land is split across 2 components -- a strait bisecting one cell -- is a genuine edge case,
# surfaced, not silently merged)
block_comp_tris: dict = defaultdict(Counter)
for ci, comp in enumerate(tri_components):
    for ti in comp:
        block_comp_tris[land_tris[ti]["blk"]][ci] += 1
comp_of: dict = {}
straddling = []
for blk, counts in block_comp_tris.items():
    best = counts.most_common()
    comp_of[blk] = best[0][0]
    if len(best) > 1:
        straddling.append((blk, best))
components = [set() for _ in tri_components]
for blk, ci in comp_of.items():
    components[ci].add(blk)
comp_sizes = sorted((len(c) for c in components if c), reverse=True)
log(f"  -> {sum(1 for c in components if c)} block-level land components (from land blocks "
    f"only, {len(components) - sum(1 for c in components if c)} tri-components own no whole "
    f"block-majority); sizes (top 10) {comp_sizes[:10]}, smallest 10 {comp_sizes[-10:]}")
if straddling:
    log(f"  {len(straddling)} block(s) straddle >1 land component (majority-assigned): "
        f"{[b for b, _ in straddling][:10]}")
out["n_land_components"] = sum(1 for c in components if c)
out["land_component_sizes_top10"] = comp_sizes[:10]
out["straddling_blocks"] = [[list(b), [[ci, n] for ci, n in cnts]] for b, cnts in straddling]


def unwrap_component(comp):
    """Unwrap every block in ``comp`` relative to an arbitrary reference corner so the
    bounding rect is a plain (possibly-negative) integer box -- ``for_donor`` reads
    ``dbx+i``/``dby+j`` directly with no wrap of its own."""
    ref = next(iter(comp))

    def uw(b):
        bx, by = b
        dx = ((bx - ref[0] + GRID_X // 2) % GRID_X) - GRID_X // 2
        dy = ((by - ref[1] + GRID_Y // 2) % GRID_Y) - GRID_Y // 2
        return (ref[0] + dx, ref[1] + dy)

    uw_map = {b: uw(b) for b in comp}
    xs = [v[0] for v in uw_map.values()]
    ys = [v[1] for v in uw_map.values()]
    return uw_map, min(xs), min(ys), max(xs), max(ys)


# ==== stage 3: build donor WINDOWS (dedup multi-block islands; else single-block) ===================
log("stage 3: clustering beach blocks into donor windows...")
windows = []
seen_multi_comp = set()
for b in beach_blocks:
    if b not in comp_of:
        # no land tri majority-owns this block (shouldn't happen for a beach block by the
        # sand-implies-land-topo law) -- fall back to a bare single-block window, flagged.
        windows.append(dict(kind="single-no-land-component", donor=b, size=(1, 1), blocks=[b],
                            n_blocks=1, self_contained=True, spans_wrap=False))
        continue
    ci = comp_of[b]
    comp = components[ci]
    if len(comp) <= SMALL_COMPONENT_MAX:
        if ci in seen_multi_comp:
            continue
        seen_multi_comp.add(ci)
        uw_map, minx, miny, maxx, maxy = unwrap_component(comp)
        nx, ny = maxx - minx + 1, maxy - miny + 1
        spans_wrap = nx > GRID_X or ny > GRID_Y
        donor = (minx % GRID_X, miny % GRID_Y)
        rect_cells, self_contained = [], True
        if not spans_wrap:
            for ux in range(minx, maxx + 1):
                for uy in range(miny, maxy + 1):
                    wb = (ux % GRID_X, uy % GRID_Y)
                    rect_cells.append(wb)
                    if wb in data_set and comp_of[wb] != ci:
                        self_contained = False
        windows.append(dict(kind="multi" if len(comp) > 1 else "single",
                            donor=donor, size=(nx, ny), blocks=sorted(comp),
                            n_blocks=len(comp), self_contained=self_contained,
                            spans_wrap=spans_wrap))
    else:
        # attached to the mainland (or another oversized component) -- single-block window,
        # exactly the (7,17)-style screening unit; the component itself is never windowed whole.
        windows.append(dict(kind="single-mainland", donor=b, size=(1, 1), blocks=[b],
                            n_blocks=1, self_contained=True, spans_wrap=False))
log(f"  {len(windows)} donor windows from {len(beach_blocks)} beach blocks "
    f"({sum(1 for w in windows if w['kind'] == 'multi')} multi-block islands, "
    f"{sum(1 for w in windows if w['kind'] != 'multi')} single-block)")
out["n_windows"] = len(windows)


# ==== qualification: the real gate, no writes =======================================================
def gather(donor, size, strips):
    """Mirror for_donor's own gather EXACTLY (donor rect whole + border strips per ``strips``)."""
    (dbx, dby) = donor
    (nx, ny) = (int(size[0]), int(size[1]))
    polys = {p: [] for p in TR.PARTS}
    for p in polys:
        for j in range(ny):
            for i in range(nx):
                polys[p] += [list(t) for t in TR.world_tris(dbx + i, dby + j, p, disc=1)]
    extra = 8.0
    all_specs = {
        "E": [((dbx + nx, dby + j), 0, 64.0 * (dbx + nx) + extra, True) for j in range(ny)],
        "W": [((dbx - 1, dby + j), 0, 64.0 * dbx - extra, False) for j in range(ny)],
        "N": [((dbx + i, dby - 1), 2, -64.0 * dby + extra, True) for i in range(nx)],
        "S": [((dbx + i, dby + ny), 2, -64.0 * (dby + ny) - extra, False) for i in range(nx)]}
    if strips in ("auto", "all"):
        gathered = set(all_specs)
    elif strips in ("none", None):
        gathered = set()
    else:
        gathered = {str(d).upper() for d in strips}
    strip_specs = [spec for d in sorted(gathered) for spec in all_specs[d]]
    for ((nx2, ny2), axis, plane, below) in strip_specs:
        if not (0 <= nx2 < GRID_X and 0 <= ny2 < GRID_Y):
            continue
        for p in polys:
            for tri in TR.world_tris(nx2, ny2, p, disc=1):
                cp = TR.clip_poly(list(tri), axis, plane, below)
                if len(cp) >= 3:
                    polys[p].append(cp)
    return polys


def qualify(donor, dst, size, strips):
    """The REAL gate, offline: build via ``for_donor`` (every raise = a named failing gate),
    then regather + re-apply + ``gate()`` (catches residual unclassified content ``for_donor``'s
    own prescan doesn't pre-empt). Returns a dict with ``ok`` and the FIRST failing gate."""
    try:
        gt = TR.GroundRetile.for_donor(donor, dst, size=size, strips=strips, disc=1)
    except ValueError as e:
        return dict(ok=False, first_failing_gate="for_donor", detail=str(e))
    polys = gather(donor, size, strips)
    for p, pl in polys.items():
        for poly in pl:
            gt.apply(p, poly)
    g = gt.gate()
    if not g["ok"]:
        gate_name = "unclassified-content" if g["unclassified"] else "expected-count-mismatch"
        detail = g["unclassified"] if g["unclassified"] else \
            {k: (gt.n[k], gt.expected.get(k)) for k in gt.expected if gt.n[k] != gt.expected.get(k)}
        return dict(ok=False, first_failing_gate=gate_name, detail=str(detail))
    return dict(ok=True, first_failing_gate=None,
               counts={k: g[k] for k in ("mains", "wall", "sand", "foam", "recovered")})


# ==== stage 4: sanity anchors (must pass before any candidate verdict is trusted) ====================
log("stage 4: SANITY ANCHORS...")
anchors = {}
anchors["(7,17)->desert (size 1x1, strips=auto)"] = qualify((7, 17), "desert", (1, 1), "auto")
anchors["(10,17)+2x2->desert (strips=auto)"] = qualify((10, 17), "desert", (2, 2), "auto")
anchors["(10,17)+2x2->snow (strips=auto, MUST REFUSE)"] = qualify((10, 17), "snow", (2, 2), "auto")
anchors["(10,17)+2x2->snow (strips=none, MUST QUALIFY)"] = qualify((10, 17), "snow", (2, 2), "none")
for k, v in anchors.items():
    if v["ok"]:
        log(f"  {k}: PASS")
    else:
        log(f"  {k}: refuse [{v['first_failing_gate']}] {str(v['detail'])[:120]}")
anchor_ok = (anchors["(7,17)->desert (size 1x1, strips=auto)"]["ok"]
            and anchors["(10,17)+2x2->desert (strips=auto)"]["ok"]
            and not anchors["(10,17)+2x2->snow (strips=auto, MUST REFUSE)"]["ok"]
            and anchors["(10,17)+2x2->snow (strips=none, MUST QUALIFY)"]["ok"])
log(f"  SANITY ANCHORS: {'ALL PASS' if anchor_ok else 'FAIL -- the screen below is NOT trustworthy'}")
out["sanity_anchors"] = {k: v for k, v in anchors.items()}
out["sanity_anchors_pass"] = anchor_ok
assert anchor_ok, "sanity anchors failed -- fix the screen before trusting the candidate table"


# ==== stage 5: screen every window x {desert, snow}; canyon = tally only ============================
log(f"stage 5: screening {len(windows)} windows x {len(FAMILIES)} families "
    f"(both strip modes each)...")
results = []
for wi, w in enumerate(windows):
    donor, size = tuple(w["donor"]), tuple(w["size"])
    row = dict(idx=wi, donor=list(donor), size=list(size), blocks=[list(b) for b in w["blocks"]],
              n_blocks=w["n_blocks"], kind=w["kind"], self_contained=w["self_contained"],
              spans_wrap=w["spans_wrap"], families={})
    if w["spans_wrap"]:
        row["note"] = "SKIPPED -- component spans the grid wrap seam, unsupported by " \
                       "for_donor's plain-integer rectangle gather"
        results.append(row)
        continue
    for fam in FAMILIES:
        auto = qualify(donor, fam, size, "auto")
        if auto["ok"]:
            row["families"][fam] = dict(verdict="QUALIFIED (strips=auto)", auto=auto)
        else:
            none_r = qualify(donor, fam, size, "none")
            if none_r["ok"]:
                row["families"][fam] = dict(
                    verdict="QUALIFIED (strips=none only -- STRIPS-PARITY)", auto=auto, none=none_r)
            else:
                row["families"][fam] = dict(
                    verdict=f"REFUSED [{auto['first_failing_gate']}]", auto=auto, none=none_r)
    results.append(row)
    if (wi + 1) % 10 == 0 or wi == len(windows) - 1:
        log(f"  ...{wi + 1}/{len(windows)} windows screened")
out["windows"] = results

n_qual_desert = sum(1 for r in results if r.get("families", {}).get("desert", {})
                    .get("verdict", "").startswith("QUALIFIED"))
n_qual_snow = sum(1 for r in results if r.get("families", {}).get("snow", {})
                  .get("verdict", "").startswith("QUALIFIED"))
n_strips_parity = sum(1 for r in results for fam in ("desert", "snow")
                      if "STRIPS-PARITY" in r.get("families", {}).get(fam, {}).get("verdict", ""))
n_canyon_candidates = sum(1 for r in results if not r.get("spans_wrap"))
out["n_qualified_desert"] = n_qual_desert
out["n_qualified_snow"] = n_qual_snow
out["n_strips_parity_windows"] = n_strips_parity
out["canyon_tally_only"] = dict(
    candidate_windows=n_canyon_candidates,
    note="NOT screened per task instructions -- GROUNDS['canyon']['wall_coastal'] is False "
         "(interior-only band, 0 open-sea coastal faces map-wide, family_wall_envelope.py), "
         "so for_donor's THE WALL-CONTEXT LAW chokepoint refuses EVERY donor whose rect carries "
         "a coastal (waterline) wall course, unconditionally, before any per-window content check.")

# ==== ranked verdict table ===========================================================================
print("\n== RANKED VERDICT TABLE ==")
print(f"{'#':>3s} {'donor':>10s} {'size':>6s} {'blk':>3s} {'kind':14s} {'selfC':>5s} "
      f"{'family':7s} {'verdict'}")
already_proven = {((7, 17), (1, 1)): "PROVEN in-game (2026-07-15)",
                  ((10, 17), (2, 2)): "PROVEN in-game (2026-07-15)"}
for r in sorted(results, key=lambda r: (-(r.get("families", {}).get("desert", {})
                                          .get("verdict", "").startswith("QUALIFIED")
                                          + r.get("families", {}).get("snow", {})
                                          .get("verdict", "").startswith("QUALIFIED")),
                                        r["idx"])):
    donor_s = f"({r['donor'][0]},{r['donor'][1]})"
    size_s = f"{r['size'][0]}x{r['size'][1]}"
    proven = already_proven.get((tuple(r["donor"]), tuple(r["size"])), "")
    if r.get("note"):
        print(f"{r['idx']:3d} {donor_s:>10s} {size_s:>6s} {r['n_blocks']:3d} {r['kind']:14s} "
              f"{'-':>5s} {'-':7s} {r['note']}")
        continue
    for fam in FAMILIES:
        fr = r["families"][fam]
        tag = f"  [{proven}]" if proven else ""
        sc = "Y" if r["self_contained"] else "N"
        print(f"{r['idx']:3d} {donor_s:>10s} {size_s:>6s} {r['n_blocks']:3d} {r['kind']:14s} "
              f"{sc:>5s} {fam:7s} {fr['verdict']}{tag}")

print(f"\nqualified: desert {n_qual_desert}/{len(windows)}, snow {n_qual_snow}/{len(windows)} "
      f"windows; {n_strips_parity} window/family cells needed strips=none (STRIPS-PARITY); "
      f"canyon candidate windows (tally only, refused by wall_coastal): {n_canyon_candidates}")

# top new picks: qualified, self-contained, multi-block (islands read richer than bare single
# blocks), excluding the two already-proven donors
new_qualified = []
for r in results:
    if r.get("note") or tuple(r["donor"]) in (( 7, 17), (10, 17)):
        continue
    quals = [fam for fam in FAMILIES if r["families"][fam]["verdict"].startswith("QUALIFIED")]
    if quals and r["self_contained"]:
        new_qualified.append((r, quals))
new_qualified.sort(key=lambda t: (-(t[0]["kind"] == "multi"), -t[0]["n_blocks"]))
out["top_new_qualified"] = [
    dict(donor=r["donor"], size=r["size"], blocks=r["blocks"], families=quals)
    for r, quals in new_qualified[:10]]
print(f"\ntop new qualified donors ({len(new_qualified)} total self-contained candidates beyond "
      f"the 2 proven):")
for r, quals in new_qualified[:10]:
    print(f"  ({r['donor'][0]},{r['donor'][1]})+{r['size'][0]}x{r['size'][1]} "
          f"[{r['kind']}, {r['n_blocks']} blk]: {', '.join(quals)}")

# ==== write artifact ==================================================================================
outp = OUTD / "donor_retile_screen.json"
outp.write_text(json.dumps(out, indent=1, default=str))
log(f"-> {outp}")
log(f"total runtime: {time.time() - t0:.0f}s")
