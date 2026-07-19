# The first minted DUNES ecotone patch — BUILD PLAN (design only, 2026-07-19)

Scope discipline per the brief: **no mint code was written, nothing was deployed.** Every number
below either (a) quotes a shipped constant from `ff9mapkit/ff9mapkit/world/grassland.py` read
directly for this doc, or (b) was reproduced by re-running an existing, committed script against
the live install in this worktree (commands + raw output logged inline). Where a fact is
genuinely unmeasured, that is stated as such, never guessed past.

THE NO-ENCLOSED-DUNES LAW (`dunes_patch_carry.py:1-12`, `GROUND-FAMILY-DECODE-2026-07-19.md`)
rules out a verbatim carry: no real dunes ensemble closes inside desert alone. This is therefore
a **MINT + IN-PLACE RETILE**, not a carry — a desert `world-island` host, then a compact interior
cell-set re-tagged to dunes' own mains, with the boundary dressed in the proven
`STRIPS[("desert","dunes")]` rect. Geometry (vertex positions, normals, triangle winding, block
partition) stays byte-identical to a plain `--ground desert` mint at every step — only
`tangent.x` (topograph) and `uv` change on the affected triangles.

---

## 1. DUNES MAINS — tile set / UV rule for a lawful flat dunes interior cell

`grassland.py:146-154` (`GROUNDS["dunes"]`):

```python
"dunes": dict(topo=41, mains_du=0.38964, mains_dv=-0.13477,
              wall_du=-0.27127, wall_dv=-0.02066,
              cls="interior", wall_coastal=False)
```

Confirmed by direct read (`py -c "from ff9mapkit.world import grassland as G; print(G.GROUNDS['dunes'])"`,
run this session):
`{'topo': 41, 'mains_du': 0.38964, 'mains_dv': -0.13477, 'wall_du': -0.27127, 'wall_dv': -0.02066,
'cls': 'interior', 'wall_coastal': False}`.

**Method that produced it** (`studies/overworld-topography/README.md:489-510`): the desert
translation-fit method (census → per-4u-cell exact-affine decode → mural screen → **AUTO 2×2
quadrant DETECTION** → 5dp outer-bound rect recovery → translation fit → wall probe) run over
dunes' real bytes. The AUTO-2×2-detection step succeeding means dunes genuinely carries the
**same 2×2-quadrant mains structure** as every other family (`FAM_REGION["main"]`, width
0.06054/0.03028 — reconfirmed this session:
`GRASS_U_HALF widths [0.06054, 0.06054]`, `GRASS_V_HALF widths [0.03028, 0.03028]`), just
translated to its own atlas rect — **this is the "family-model exception" langauge**: dunes'
rect is its *own* pale-sand painting, not a re-use of desert's rect the way dirt-19/20 are
(`README.md:507`: *"dirt 41 | 41 | (0.38964, −0.13477) | none in stock | family-model
EXCEPTION — its own pale-sand set, NOT desert's"*).

**Generative rule for a lawful flat dunes cell**: identical to every other family — call
`grassland.mains_uv(x, z, cell, quad, ori)` (the linear-in-position quadrant map,
`grassland.py:266-279`) then add `(mains_du, mains_dv)` — i.e. `grassland.ground_uv(x, z, cell,
quad, ori, "dunes")` (`grassland.py:214-219`), already generic over `ground`. `topograph` tags to
41 (`GROUNDS["dunes"]["topo"]`), same `island.py:439` idiom
(`idg = float(encode_id(topograph=gspec["topo"]))`) any other `--ground` value uses.

**2×2 avoid-repeat neighbour policy — UNMEASURED specifically for dunes.** The neighbour-repeat
statistics quoted in `grassland.py`'s module docstring (same-quadrant 12%, same-rotation 49%)
were measured once, on the grass mains tile language, and are treated as **the universal
generative policy** — every family mint to date (desert, snow, canyon, already in-game proven)
calls the *same* `assign_mains()` (`grassland.py:245-263`) with no per-family remeasurement; only
the translated *rect* differs per family, never the placement statistics. No script in this
study has isolated dunes-bearing blocks and independently measured their own same-quadrant /
same-rotation rates. **Conservative rule, consistent with every prior in-game-proven mint**: reuse
`assign_mains()` unchanged — do not invent a dunes-specific variant. This is a real gap (flagged
in §7), but it is the *same* gap every other already-shipped `--ground` family mint carries and
none has read as wrong in-game.

---

## 2. STRIP RING

**Orientation (own-side census, re-measured this session — see §7 for the full rerun log):**

```
== proven strip rect in play: STRIPS('desert', 'dunes') du=-0.13476 dv=-0.09863 rows=4
blocks read: 260/480; cells classified: 21226
INDEPENDENT edge census: 190 desert|dunes tri-shared edges over 9 blocks
cell-level strip classification: 195 strip cells over 9 blocks
ORIENTATION Q1: {'dunes': 99, 'desert': 96}  (49.2% desert-topo / 50.8% dunes-topo)
   -> BOTH: roughly half the strip-wearing cells are walkable AS desert, half AS dunes.
ORIENTATION Q3: FAMILY-RELATIVE (holds in all 4 compass directions -- does NOT flip)
   direction: row increases toward dunes (A-only mean 0.839 vs B-only mean 1.704)
```

This byte-exactly reproduces the record in `GROUND-FAMILY-DECODE-2026-07-19.md` (190
edges/195 cells/9 blocks) — independently re-derived, not re-quoted (LAW 5).

**Which cells wear the strip, concretely, for a MINTED patch** (the record measures a *real*
seam's cell classification; it does not, by itself, tell a mint where to put the ring — that is
this section's design call): a lawful desert|dunes seam is **not a one-sided edge trim**. Ring
cells split into two concentric shells around the dunes core, both wearing the strip UV, differing
only in which *topograph* they carry:

- **inner ring** (the 1-cell shell touching the dunes core on the outside) → topo 41 (dunes),
  strip UV, touch-category `B-only` (touches dunes core only, once desert cells lie outside it).
- **outer ring** (the 1-cell shell touching the inner ring, still surrounded by plain desert
  farther out) → topo 17 (desert), strip UV, touch-category `A-only`.
- a cell touched by **both** the dunes core (through a diagonal or the inner ring) and plain
  desert simultaneously classifies `both` — this happens naturally at inside corners of a
  non-convex core footprint.

This is the **conservative, falsifiable reading** of the measured ~50/50 split and the
family-relative direction law — it is not itself proven to be the *specific spatial pattern* FF9
uses (the census establishes the marginal split and the direction, not a spatial rule beyond
"the column straddles the seam"). Flagged as an open item in §7; the render gate (§5) is exactly
what would catch a wrong spatial rule before deploy.

**Row → v mapping** (`grassland.py:187-190`, `dunes_strip_emitter.py:87-114`):

```
STRIP_U = (0.39355, 0.4541)                      # u-column, shared by every strip pair
STRIPS_V = [(0.36914,0.39844),(0.40039,0.43066),(0.43164,0.46191),(0.46289,0.49316)]  # rows 0-3
ROW_PITCH = 0.03125                              # exact, all 4 rows (re-verified this session)
S = STRIPS[("desert","dunes")]  # du=-0.13476 dv=-0.09863
row_v(k) = STRIPS_V[0][0] + S["dv"] + k * ROW_PITCH        # k in 0..3
row_u    = STRIP_U + S["du"]
```

**No generative `strip_uv()` exists yet** — `STRIPS` is explicitly `"DATA ONLY, not yet an
authoring surface"` (`grassland.py:157-166`). It must be authored mirroring `mains_uv`
(`grassland.py:266-279`) exactly: linear-in-cell-position across the row's rect, with the SAME
`rot_ab` direction-aware mapping, but **orientation fixed at `ori=0`** — round 2/3's emitter only
ever varied *which row* (0-3), never rotated the tile within the cell; there is no measurement of
strip-tile rotation freedom, so freezing it is the conservative choice (flagged in §7):

```python
def strip_uv(x, z, cell, row, ori=0, *, pair=("desert", "dunes")):
    (i, j) = cell
    fx, fz = (x - 4.0*i) / 4.0, (z - 4.0*j) / 4.0
    a, b = rot_ab(fx, fz, ori)                    # same fn grassland.py:233-242
    a, b = max(0.0, min(1.0, a)), max(0.0, min(1.0, b))   # plain clamp -- no cross-cell bleed
    S = STRIPS[pair]
    u0, u1 = STRIP_U
    v0, v1 = STRIPS_V[row]
    return [u0 + a*(u1-u0) + S["du"], v0 + b*(v1-v0) + S["dv"]]
```

**Emitter plug-in point** — both existing scripts already share one signature; a design that
targets it is agnostic to which lane wins:

```python
def emit(cells: set[tuple[int,int]], touch_of: dict[tuple[int,int], str], *, seed: int) \
        -> dict[tuple[int,int], int]:       # cell -> row 0..3
```

- round 3's BFS emitter (`dunes_strip_emitter.py:406-448`, `emit_strip_rows(cells, touch_of,
  target_pmf, delta_p, seed)`) matches this signature with `target_pmf`/`delta_p` closed over
  from the measured constants above (re-derived this session, see §7's raw dump: e.g.
  `TARGET_PMF["both"] = {0:0.170, 1:0.292, 2:0.239, 3:0.299}`,
  `DELTA_P = {0:0.098, 1:0.526, 2:0.293, 3:0.083}`).
- the round-3 write-up's named-but-unbuilt alternative ("sample one continuous coverage-density
  scalar along the seam, interpolate, snap to nearest row") would implement the same signature —
  a continuous field over the ring cells' centroids, discretized to `{0,1,2,3}` at the end. No
  file implements this yet.
- **Calibrated status (the retracted-then-reinstated verdict,
  `GROUND-FAMILY-DECODE-2026-07-19.md` lines 104-176):** the emitter sits *inside* stock's own
  cross-cluster transplant-null variance on all 20 seeds (jumpiness 4.62–5.62 vs the null band
  3.83–5.85); only `all-row-0` sits outside. The bar for "acceptable" is **non-degenerate**, not
  "solved" — either emitter satisfies it. The one measured, real shortfall: the BFS emitter's
  lag-1 autocorrelation across seeds averages **+0.073** vs real stock's **−0.4233** (re-measured
  this session) — real placement alternates step-to-step more than the emitter does. Not
  gating (the jumpiness metric, not autocorrelation, is what visual read tracks), but a genuine,
  named defect for whichever lane builds the coverage-field version to try to close.

---

## 3. TOPO + FLAGS

**Walk-mask verification (re-derived independently this session, not quoted):**

```python
WALK_TOPO = frozenset(t for t in range(64)
    if (((0x0010667F >> (t-32)) & 1) if t>=32 else ((0xD8FF3CFF >> t) & 1)))
# -> [0,1,2,3,4,5,6,7,10,11,12,13,16,17,18,19,20,21,22,23,27,28,30,31,32,33,34,35,36,37,38,41,42,45,46,52]
41 in WALK_TOPO -> True
58 in WALK_TOPO -> False    # the coastal wall band is correctly NOT walkable
0  in WALK_TOPO -> True
17 in WALK_TOPO -> True
```

Source: `w_movementCheckTopographID(limit, id)` (ff9.cs:5769 per
`ff9mapkit/docs/OVERWORLD_ENGINE.md:424-425,508-509`), on-foot `limit = {0x0010667F,
0xD8FF3CFF}`, testing bit `(idall & 0xFC) >> 2` of the 64-bit mask (`extract.decode_id`,
`extract.py:65-76`, bits 2-7 = topograph — the task's cited formula, confirmed against the
shipped decoder). **Topo 41 (dunes) IS on-foot walkable**; the patch's core, ring, and margin
are all lawfully traversable.

**event/area/flags**: this is a **mint retile**, not a carry, so there is no donor to inherit
flags from (contrast `dunes_patch_carry.py`'s comment "area/event bits rewritten to the islet's
own — topo + flags stay donor-verbatim", which applies only when real donor tris are being
imported). A plain `world-island --ground desert` mint's mains tris already all carry
`event=0, area=0, flags=0` (`island.py:439`, `encode_id(topograph=gspec["topo"])` with every
other arg defaulted 0 — reconfirmed this session:
`encode_id(topograph=17) == 68`, `decode_id(68) == {'event':0,'area':0,'topograph':17,'flags':0}`).
The retile changes **only the topograph field**: core cells → `encode_id(topograph=41) == 164`;
strip-ring cells → `encode_id(topograph=41)` (inner ring) or `encode_id(topograph=17)` (outer
ring), `event`/`area`/`flags` untouched at 0/0/0 throughout. No entrance/area semantics are
introduced anywhere in the patch.

**IDALL_SKIP collision check (a real, previously-uncataloged risk this design closes off):**
`placement.py:33` hardcodes `IDALL_SKIP = {4078, 4088, 2040}` — any triangle whose `tangent.x`
decodes to exactly one of those raw ints is skipped by the placement raycast outright, independent
of geometry. Decoded this session:

```
4078 -> {'event': 0, 'area': 15, 'topograph': 59, 'flags': 2}
4088 -> {'event': 0, 'area': 15, 'topograph': 62, 'flags': 0}
2040 -> {'event': 0, 'area': 7,  'topograph': 62, 'flags': 0}
```

All three require `area` 7 or 15. Every idall this design ever emits keeps `area=0`, so a
collision with `IDALL_SKIP` is structurally impossible (bits 8-13 are always zero) — not merely
untested.

---

## 4. PLACEMENT

**FF9CustomMap-world tree, listed this session** (`find … -maxdepth 6`):
only `Disc1/0_1/r18/Block[6][18]*`, `Block[7][18]*`, `Disc1/0_1/r19/Block[6][19]*`,
`Block[7][19]*` (9 files + a `.bak` each) and their `Disc4` mirrors (9 files, no `.bak`) —
**exactly the comp20 massif carry at blocks (6-7,18-19)**, matching the CONTEXT's post-reset
claim. No block at `(8,19)`/(10,19)/anywhere else carries a mod override.

**Real-game occupancy check** (`island._real_block_parts`, run this session):

```
(8, 19)  {}      (9, 19)  {}      (10, 19) {}     (11, 19) {}
(9, 18)  {'terrain': 40, 'beach1': 7, 'sea2': 1, 'sea3': 40, 'sea5': 42, 'sea4': 407}
(10, 18) {'terrain': 26, 'sea3': 30, 'sea5': 36, 'sea4': 436}
(11, 18) {}      (6,18) {}  (7,18) {}  (6,19) {}  (7,19) {}
```

`(8,19)` (the scrub recreate site) and `(6-7,18-19)` (comp20) are correctly excluded per the
brief. `(9,18)`/`(10,18)` carry REAL stock terrain (open ocean is empty `{}` — this island.py
convention, `island.py:787-799`) — avoid. `(9,19)`/`(10,19)`/`(11,19)` are all true open ocean.

**Chosen site: block `(10, 19)`, world center `(672.0, -1248.0)`, radius `26.0`, seed `2.0`,
`--ground desert --mod-folder FF9CustomMap-world`.** This is the pre-reset dunes-sampler
neighborhood the CONTEXT flagged for checking — confirmed free and suitable. Verified this
session via a **zero-write dry run** (`island.landmass(..., dry_run=True)`):

```
seed 1.0 reject: landmass NOT CLEAN -- ... 'walk_filter_fails': 1 ...
seed 2.0 OK -> [[10, 19]] tris [494]
```

Seed 2.0 passes every offline gate cleanly (geometry, UV, footprint, and — since `dry_run=True`
still runs `verify_landmass(..., sea_plane=...)` — the full engine placement census) as a
single-block island, 494 tris, before any patch content is added.

**Interior cell-set for the dunes patch** (re-derived this session by building the seed-2.0
desert islet and walking its `topo==17` mains cells in world-cell coordinates):

```
mains desert cell count: 130   x range [162,173]  z range [-319,-307]
candidate interior core rect with a 2-cell all-desert margin on every side:
   cell origin (164, -314), size 3x3  -> world center (662.0, -1250.0)
```

**Recommended layout**: dunes core = the 3×3 cell block `x∈[164,166] z∈[-312,-314]` (9 cells,
world center `(662, -1250)`) — same order of magnitude as the scrub carry's 9-15-cell windows
(`dunes_patch_carry.py:11`). Strip ring = its 1-cell 4-neighbour dilation shell (up to 12 cells
for a 3×3 core, fewer with corner-adjacency choices — an exact count depends on whether
diagonal-touching cells are included, a build-time decision, not a design blocker). A further
1-cell pure-desert buffer separates the ring from the rest of the islet, and the verified 2-cell
margin above guarantees the whole assembly sits ≥2 cells (8u) inside the rim wall in every
direction — clear of `ROCK_U`/`ROCK_V` (the wall band) by construction, so the `wall_coastal`
gate on `dunes`/`GROUNDS["dunes"]["wall_coastal"]=False` never comes into play: the minted
island's rim stays 100% desert (`wall_coastal=True`), and the dunes patch never reaches it.

**`--near` vs `--center`/`--cell`**: `world-island` takes `--cell BX,BY` or `--center WX,WZ`
(`cli.py:5865-5868`); this design uses `--center 672,-1248 --radius 26 --seed 2 --ground desert
--mod-folder FF9CustomMap-world` (equivalently `--cell 10,19`, which resolves to the same block
center per `island.landmass`'s `cell=` branch, `island.py:815-818`).

---

## 5. THE GATE LIST (in order), and which existing function runs it

1. **Mint acceptance** (baseline desert island, before any retile) —
   `island.build_landmass` + `island.verify_landmass` (`island.py:223-728`): watertight/cracks,
   winding, on-grain (`grass_over_8u`), per-family UV-region bounds (`uv_out_of_region` — this
   is also what PROVES the retile's input cells are 100% pure mains, §5.2 below), footprint
   holes, the closed-surface once-edge audit, and the coastline shape gate. Already verified
   clean this session at the chosen site/seed (dry run).
2. **OPEN-OCEAN TARGET** — `island.landmass`'s `_real_block_parts` occupancy check
   (`island.py:826-834`): every touched block must be true open ocean. Verified this session
   (§4).
3. **THE WALL-CONTEXT LAW** (`island.build_landmass:256-264`): `--ground desert` passes
   (`wall_coastal=True`); the dunes patch never touches the wall by construction (§4's 2-cell
   margin), so `GROUNDS["dunes"]["wall_coastal"]=False` never triggers this gate for the
   *interior* content — only relevant if a future design tried a whole dunes ISLAND, which this
   is explicitly not.
4. **Retile strict-unclassified/zero-residual** — no shipped function does this for a
   *mint-local* retile (`transplant.GroundRetile.apply`/`gate()`,
   `transplant.py:342-401`, is scoped to a *donor's* carried tris). The retile step to be
   authored must replicate its REFUSE discipline: every triangle in the touched cell-set must
   classify as exactly one of {desert-mains (untouched), dunes-mains (core), strip (ring)} —
   reuse `dunes_strip_emitter.py`'s `classify_tri`/`classify_strip`/`mains_rect` helpers
   (`dunes_strip_emitter.py:79-125`) as the acceptance oracle, run as a **post-retile pass**
   over the touched footprint; zero `"other"` classifications required. (Largely pre-guaranteed:
   §5.1's `uv_out_of_region==0` on the baseline build already proves every input tri starts as
   pure desert-mains or rock — nothing else exists to misclassify going in.)
5. **Boundary invariance + weld audit** — `dunes_patch_carry.py`'s `once_edges()` helper
   (`dunes_patch_carry.py:62-70`) and `ff9mapkit.world.mesh.weld_audit`
   (`mesh.py:1156`), exactly as the scrub carry runs them. Both are **position-only** checks;
   since this design moves zero vertices (only `uv`/`tangent.x` change), they pass automatically
   by construction — still run as a regression proof per LAW 5, not because failure is plausible.
6. **Frame-bounds gate** — `dunes_patch_carry.py`'s local-frame assertion
   (`dunes_patch_carry.py:365-371`), same reasoning: automatic here (no coordinate transform is
   introduced), run as a regression check.
7. **Engine placement census, MISS=0 in every touched cell** — `placement.census`
   (`placement.py:81-99`), called through `island.verify_landmass(..., sea_plane=...)`. **Provable
   invariant, not merely testable**: `placement.place` (`placement.py:44-78`) decides a hit purely
   from triangle vertex positions + the up-facing winding test; `tangent.x` only supplies the
   *returned* topo/mesh label (via `IDALL_SKIP` membership, §3) and this design's outputs never
   land in `IDALL_SKIP` (area always 0). So MISS is byte-identical before and after the retile —
   the census re-run is a regression proof, not a real risk (§7 states this as a checked fact,
   not an assumption).
8. **`wall_coastal` gate** — already covered by #3; restated here only because the brief lists it
   explicitly. No second check needed.
9. **The offline eye render** — adapt `dunes_strip_emitter.py`'s `render_plan`/`sheet`
   (`dunes_strip_emitter.py:594-673`) or `dunes_strip_emitter_v2.py`'s jumpiness metric
   (`dunes_strip_emitter_v2.py:93-96`) to the MINTED patch instead of a stock seam window: render
   the finished (10,19) island (texture + row-color overlay) before deploy, and score the ring's
   luminance-jumpiness against the transplant-null band already established
   (3.83–5.85, `GROUND-FAMILY-DECODE-2026-07-19.md` line 138) as the acceptance band, exactly as
   v2 did for the stock-seam case. This is the step that would catch a wrong spatial ring rule
   (§2) before it reaches a playtest.

**Not gating, explicitly**: a per-family dunes 2×2 neighbour-repeat remeasurement (§1) and
strip-tile rotation freedom (§2) are unmeasured; the design's conservative defaults (reuse
`assign_mains` unmodified; fix `ori=0`) are not proven optimal, only proven non-degenerate by the
same logic that cleared the row emitter (§2, THE FORM LESSON risk is bounded, not eliminated —
see §7).

---

## 6. DEPLOY + MIRROR

Exact procedure (mirrors `island.landmass`, `island.py:802-881`, with the retile step inserted
between build and deploy):

1. `built = island.build_landmass(center=(672.0,-1248.0), base_radius=26.0, seed=2.0,
   ground="desert", stamps=None, disc=1)` — the plain desert island, gated clean (§5.1, already
   dry-run-verified this session).
2. **[new, to be authored]** retile step: classify `built["blocks"][(10,19)]`'s `topo==17`
   mains tris by 4u cell against the core/ring/margin layout (§4); rewrite `uv` (via
   `ground_uv(..., "dunes")` for core, the new `strip_uv()` for ring, §1/§2) and `tangent.x`
   (topo 41 for core + inner ring, topo 17 unchanged for outer ring) in place. Zero vertex
   motion.
3. Run gates 4-9 from §5 against the retiled block.
4. `island.landmass`'s own deploy loop, reused verbatim (ground="desert" with no `beach=`, so
   the plain non-beach branch, `island.py:871-877`): per touched block, write
   `Terrain` (the retiled mesh), a hole-patched `Sea4`
   (`island._cut_plane`/`island._sea_plane`, `SEA_PLANE_SOURCE=(12,0)`), the 6 `HIDDEN_PARTS`
   (`Object, Sea1, Sea2, Sea3, Sea5, Beach1` — blanked stubs,
   `mesh.hidden_block_mesh`), and a `Donor.txt` sidecar naming `DEFAULT_DONOR=(0,0)` (Uaho, for
   the s34 divert, `mesh.deploy_donor_sidecar`).
5. **Expected written-file list** (9 files, matching every existing block in the tree, verified
   against the comp20 blocks' own 9-file shape this session): for block `[10][19]`:
   `Terrain.ff9mesh`, `Sea4.ff9mesh`, `Object.ff9mesh`, `Sea1.ff9mesh`, `Sea2.ff9mesh`,
   `Sea3.ff9mesh`, `Sea5.ff9mesh`, `Beach1.ff9mesh`, `Donor.txt` — all under
   `FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r19/`.
6. **Disc-4 mirror — automatic.** `island.landmass` calls `discmirror.auto_mirror(written,
   mod_folder=..., skip_mirror=skip_mirror)` unconditionally after every non-dry-run deploy
   (`island.py:879-880`; this is the "b7d2435" auto-mirror-since behavior the brief names).
   Default (`--skip-mirror` NOT passed): the same 9 files, minus any `.bak`, get written to
   `FF9CustomMap-world/FF9_Data/WorldMap/Disc4/0_1/r19/Block[10][19] *` — exactly the pattern
   observed this session for the comp20 blocks' own Disc1/Disc4 pairs. No manual `world-mirror`
   run is needed; passing `--skip-mirror` would require one.
7. **Relaunch note**: per `deploying-ff9-mods`/CLAUDE.md §4, a brand-new block id (`(10,19)` has
   never been registered in this mod folder before) needs a world **re-entry** (not a full
   relaunch) to stream the new override — F6 → World → Teleport to `(672, -1248)` after
   re-entering the world map.

---

## 7. RISKS + UNKNOWNS

| # | Risk / unknown | Status | Probe that would settle it |
|---|---|---|---|
| 1 | Dunes-specific 2×2 quadrant neighbour-repeat statistics | **Unmeasured** — reusing the grass-derived universal policy (§1), same as every other shipped family | Isolate the 9 real dunes-bearing blocks (`strip_blocks`-adjacent census already has their coordinates) and run the grass study's own same-quadrant/same-rotation measurement restricted to dunes-topo cells |
| 2 | Strip-tile rotation freedom (`ori` beyond the row axis) | **Unmeasured** — never varied by round 2/3; `ori=0` fixed as the conservative default (§2) | Extend `dunes_strip_emitter.py`'s `classify_strip` to also fit a per-cell rotation against the real 195 strip cells' vertex-order/UV-gradient direction, the way `mains_uv`'s `rot_ab` was originally fit |
| 3 | The two-shell (inner-ring=dunes / outer-ring=desert) spatial rule for strip placement | **A design proposal, not a measured fact** — consistent with the ~50/50 own-topo split and the family-relative direction law, not independently proven as *the* spatial pattern | The offline-eye render gate (§5.9) on the actual minted footprint, before any deploy; if it reads wrong, the alternative (checkerboard, or a single-shell rule with row alone carrying the "which side" signal) is cheap to swap since the classification is data-driven, not hardcoded |
| 4 | Emitter lag-1 autocorrelation miss (+0.073 vs real −0.4233) | **Measured, real, non-gating** (re-verified this session, §2) | The unbuilt coverage-field emitter (round 3's named next design) is the natural fix; not required to ship rung 1 |
| 5 | `IDALL_SKIP` collision | **Closed this session** (§3) — structurally impossible since `area` stays 0 throughout | n/a — decoded and checked directly, not a live risk |
| 6 | Engine placement MISS regression | **Closed by construction** (§5.7) — MISS depends only on vertex positions + winding, both untouched; `tangent.x` only feeds `IDALL_SKIP` membership (closed, #5) and the returned topo label | Still re-run `placement.census` post-retile as a regression proof before deploy, per LAW 5 |
| 7 | Save-brick risk | **Near-zero, argued structurally, not proven zero** | This mint only reuses the exact `island.build_landmass`/`verify_landmass`/`landmass` pipeline already in-game-proven for `--ground desert` (comp20's own blocks, the r52 desert check island, etc.); the retile touches uv/topo only, so every geometric gate that guards against a brick (watertightness, winding, MISS=0, centre-grounds-walkable) is either unchanged or explicitly re-run (§5). The only way this design could brick a save is if a *later* lane wires a `world-entrance`/arrival point to spawn a player exactly inside the strip ring or dunes core at a moment none of these gates were re-checked — out of this design's scope, and `world-entrance` has its own independent `_cell_openness_note` walkability lint (`entrance.py:492-506`) that would fire on a bad target cell |
| 8 | Whether a 3×3 core (9 cells) reads as a convincing "patch" in-game vs. too small/too large | **Untested** — sized to match the scrub carry's precedent (9-15 cells) for a first rung, not derived from a dunes-specific measurement | A playtest is the only real settling probe; the offline eye render (§5.9) is the pre-playtest proxy |

**Explicitly NOT a risk, and why**: geometry drift/cracks — no vertex is ever moved by this
design (mint stays byte-identical to a plain desert island at the position/normal/index level;
only `uv` and `tangent.x` on a bounded cell-set change), so every geometry-shape gate in §5 that
doesn't depend on those two fields is either a pure regression check or literally cannot fail.

---

## Reproduction log (commands run this session, no writes except this file + the `out/` scratch dir)

```
py -c "... G.GROUNDS['dunes'] / G.GROUNDS['desert'] / G.STRIPS[('desert','dunes')] ..."
py -c "... WALK_TOPO mask recompute + 41/58/0/17 membership ..."
py -c "... decode_id(4078/4088/2040), encode_id(topograph=17/41) ..."
py -c "... island._real_block_parts for (8,19),(9,19),(10,19),(11,19),(9,18),(10,18),(11,18),(6-7,18-19) ..."
py -c "... island.landmass(..., center=(672,-1248), base_radius=26, seed=1..40 scan, ground='desert', dry_run=True) ..."
py -c "... island.build_landmass(... seed=2.0 ...) -> mains-cell census -> 130 cells, 3x3 interior core at (164,-314) ..."
py  studies/overworld-topography/dunes_strip_emitter.py  (truncated before its render section, via the
    same exec-and-cut technique dunes_strip_emitter_v2.py already uses) -> reproduced 190 edges / 195
    cells / 9 blocks / TARGET_PMF / DELTA_P / lag-1 autocorrelation -0.4233, byte-matching the memory
    record independently.
find "FF9CustomMap-world" -maxdepth 6   -> confirmed only the comp20 blocks (6-7,18-19) carry overrides.
```

No `dunes_mint_design.py` script exists (design doc only, per the brief) — the probes above were
one-off `py -c` invocations and a truncated re-run of the already-committed
`dunes_strip_emitter.py`, not a new artifact script. A future implementation lane should promote
the retile step + gate sequence in §5-6 into a proper `dunes_patch_mint.py` (naming intentionally
distinct from the falsified-window `dunes_patch_carry.py`).
