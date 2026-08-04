# THE RENDER GATE — the offline look-axis instrument (study angle 1)

> Registered BEFORE building, 2026-08-02. Parent: VSHORE-SEAL-PREDICTION.md
> "STUDY ANGLES" §1. Motivation: three consecutive V-shore visual rounds
> (playtests 4-6) shipped through fully-green sim gates because NO gate renders
> — walk_sim sees triangles as query targets, never as pixels. The calibration
> law applied to the look axis: **the instrument gates nothing until it
> reproduces the LAST rounds' defects offline.**

## The instrument (design, banked before build)

`render_gate.py` — a numpy software rasterizer over the same block meshes
walk_sim reads (`load_world`-style: live files + `part_src` overrides for
staged/archived candidates), textured from the real donor atlas:

- **Texture source**: every bench cell's `Donor.txt` reads `0,0` — ONE stock
  prefab (block (0,0)) supplies all materials. Extract its Terrain atlas (and
  the per-name Sea/Beach atlases — THE PER-NAME MATERIAL LAW) from the
  install's p0data via UnityPy, cache as PNG under `out/render_gate/atlas/`.
- **Faithfully UNLIT**: the WorldMap terrain shader binds NO normal
  (GROUND-JUNCTION-SYNTHESIS) — flat textured rasterization is not a
  simplification, it is the engine's own model. No lighting term.
- **Rasterization**: z-buffer, per-pixel XZ→barycentric UV interpolation,
  nearest-neighbour atlas sampling, backface culling (the game backface-culls;
  handedness verified on the baseline render, not assumed).
- **Views**: (a) sea-side perspective aimed at the V-corner from the SW ocean
  (the owner's screenshot vantage class); (b) top-down ortho of the corner
  bbox; (c) land-side perspective. Fixed cameras, committed constants — every
  run is pixel-comparable.
- **The diff**: candidate-vs-baseline pixel diff → count + bbox clusters of
  changed pixels OUTSIDE the intended edit footprint; identical-input runs
  must diff to ZERO (determinism gate).

## The calibration corpus (all on disk, hash-known)

| state | Terrain (5,7)/(5,8) | Sea4 | known truth (owner-scored) |
|---|---|---|---|
| BASELINE (parked, live now) | `.r*.20260802-025232` | `out/vcorner_park/` | the owner-confirmed tuck look — clean |
| v1 fairing | `.r*.20260802-032654` | live park | playtest 5: pale fins ABOVE the crest, right-angle grass seam |
| v2 fairing | `*.park.20260802-033102` | live park | playtest 6: forest tile, pale sliver, voids, still seaming |

## CALIBRATION PREDICTIONS (falsifiable; scored before the gate may gate)

- **P-A (baseline coherence)**: the baseline render shows a coherent island —
  cliff-band texels on the wall faces, lawn on top, sea around, ZERO holes
  inside the land silhouette. FALSIFIED IF the render is garbage (wrong
  winding/uv convention) — fix the instrument, not the corpus.
- **P-B (v1 reproduces playtest 5)**: the v1 render shows BOTH classes: (i)
  silhouette spikes rising above the crest line near the corner; (ii) curtain
  pixels colored from OUTSIDE the cliff rock band (the pale). FALSIFIED IF
  either class is invisible — the blind spot gets named in the ledger.
- **P-C (v2 reproduces playtest 6)**: the v2 render shows ≥3 of: forest-band
  texels on the curtain; a pale/white sliver; ≥1 void (hole) in the corner
  surface; a grass seam/phase discontinuity. Same falsification rule.
- **P-D (localization)**: baseline-vs-candidate diffs localize the defect
  pixels to the corner neighbourhood (bbox ~(370..390, -520..-505)), not
  scattered over the bench (which would mean uv/winding noise in the
  instrument itself).
- **P-E (determinism)**: baseline-vs-baseline diffs to exactly 0 pixels.

## Blind-spot ledger (named, standing)

The renderer cannot see: caustic/uv ANIMATION (sea scrolls in-game), texture
filtering/mip differences, fog/atmosphere, the skybox, draw-order transparency
blending between sea layers, LOD/far-clip behavior, and the ACTUAL in-game
camera path. A green render gate is still a REGRESSION HARNESS, NOT AN ORACLE
— it sees one lighting-free frame from three fixed cameras. Owner playtests
remain the verdict; the gate's job is to stop the last three rounds' DEFECT
CLASSES from shipping again.

## BUILD LEDGER (2026-08-02)

**Prior art superseded the design's extraction plan** (the own-prior-art rule,
applied): atlas extraction was ALREADY productized — `ff9mapkit.world.atlas
.load_atlas(part, source="engine")` resolves exactly as the engine does (Moguri
loose PNG first, p0data3 bundle fallback). Water textures are the per-name
frame-0 caustic PNGs (map engine-verified in `whole_island_eye.py`). The
game-eye cull convention is carried from `terrace_wall_strip.render_strip`
(cull when `cross(b−a,c−a)·(toward-eye) ≤ 0` — the convention that caught
round 5's cull holes). New here: the perspective camera, the per-part
engine-faithful texture binding, the corpus/diff machinery.

**Engine facts locked by the Memoria trace** (WMWorld.cs:539-846,
WMBlock.cs:106-342, WMRenderTextureBank.cs, WorldMeshOverride.cs): part→texture
binds per sub-mesh GameObject NAME, never per tri; Terrain/Object each sample
ONE 1024² atlas with plain 0..1 uv; sea/beach = ~13 standalone frame-animated
textures (frame SWAP, no uv scroll — frame 0 is a faithful still); overrides
keep the stock material path; sea layering is OPAQUE geometric z-order, not
alpha blending; vanilla filtering is NEAREST; a loose `Block[x][y] <Part>.png`
would cell-override the texture (the bench ships none); alpha-0 texels render
white in-game.

## CALIBRATION FINDINGS (2026-08-02) — ★ ALL PREDICTIONS SCORE, the gate is LIVE

- **P-A PASS**: the baseline renders a coherent island — mesa walls in rock,
  lawn ring, continuous rocky lip through the corner notch, caustic sea. Zero
  voids in the land silhouette.
- **P-B PASS**: v1 `sea_w` shows BOTH playtest-5 classes: two pale fins rising
  at the corner (one with the exact "stepped edge" the owner photographed).
  The right-angle grass seam scores PARTIAL — the diff sees it (the straight
  north edge of the wedge), but at 26.7 px/u it is eye-subtle; seam-gating by
  eye wants a tighter top window.
- **P-C PASS**: v2 `sea_w` reproduces the playtest-6 report term for term:
  the dark FOREST-texel column on the curtain, the WHITE sliver beside it, a
  white streak in the grass, sky-through-land VOIDS at the wall base. The top
  view adds two classes the owner's low camera could not even see: a hole
  visible from above at the notch tip, and the rock LIP BAND vanishing along
  the fairing stretch (grass meets water bare — both fairings never re-laid
  the lip vocabulary seen from above).
- **P-D PASS**: every diff is a compact box at the corner; `diff_v1_top` is
  exactly the fairing wedge footprint. No instrument noise anywhere else.
- **P-E PASS**: baseline re-render diffs 0 px in all four views.

**THE VERDICT**: the look axis now has an instrument. Three consecutive rounds
of defects that passed every sim gate are all reproducible offline in one
frame each. The blind-spot ledger stands (animation, filtering, fog, real
camera path) — the gate is a regression harness, not an oracle; the owner
still verdicts. **Standing rule for every future visual round on this bench:
no deploy until the candidate's render is CLEAN at these four committed
cameras AND the diff-vs-baseline is confined to the intended footprint.**

Corpus renders + diffs: `out/render_gate/`. Runtime ~40s per state.

## THE CLOSE-RANGE UPGRADE (playtest-8 response, 2026-08-02)

Playtests 7 and 8 both failed at vantages the four committed cameras do not
cover — the residuals live below the mid-range threshold. Two cameras and one
analytic check added; **the standing rule now reads SIX cameras + a clean
flow verdict.**

- **owner_close** — eye (384,21,-504) → at (377.5,0.5,-513.5), fov 50, reach
  45: the owner's near-top-down class (playtest 8's shot).
- **graze** — eye (366,3,-526) → at (379.5,1,-512.5), fov 45, reach 90: low
  oblique from offshore; thin waterline constructions are near edge-on and
  smears glint along the seam.
- **`flow` verb** — per-face 3D uv gradients (frame-independent):
  |grad| density, constant-uv smear, handedness (mirror), shared-edge
  d-angle. Judged against TWO references: stock donor (5,14) and the
  owner-passed bench outside the corner bbox.

**CALIBRATION: PASS.** The live (deployed seam-fix transplant) state
reproduces BOTH playtest-8 classes offline:
- the light waterline seam = a streaky horizontal grass-green band above the
  rock at `graze` (the apron/fan stack sampling the GRASS-TOP band
  v≈0.916–0.923 at ~6× stretch, wedge fans constant-uv = solid smears);
- the texture break = the grey band interrupting the green shoreline at
  `owner_close`.

**FLOW DISCRIMINATION: CLEAN.** stock (5,14): 0 smear / 0 stretch / 2:139
neg-handed. Bench-out (owner-passed): 0 / 0 / 3:3058. The corner: **16
smears + 62 stretched (6.3×) + 69 mirrored**, ALL at y∈[−0.6,+0.06] — the
apron+fan+curtain stack, exactly the waterline. The edge d-angle axis is
WEAK (stock's own p90 is 134.6° — lawful atlas column u-flips); it stays
informational, never a gate.

**THE DIAGNOSIS.** Stock's own look at these vantages
(`probe_stock_graze.py`, the donor's coast): lawn → NARROW fine-textured
ROCK lip → water. Our waterline band samples GRASS, stretched. The fix
class: **band-continuation retexture** — the apron/fans/curtain must
continue the carried wall's own cliff band at stock density (THE
BAND-CONTINUATION LAW applied to the auxiliary stack), not smear the grass
band.

Instrument notes: (a) the BASELINE shows the same streak class at graze —
the defect class predates the transplant; the bench skirt shares it
(fold-back debt when the generator re-learns this law). (b) The floating NE
slivers at `graze` are the REAL disc edge — Disc9 near the bench holds
exactly the six cells, no sea ring — faithful to the game, not an artifact;
CELLS now loads a ring should one ever ship. (c) `flow` counts the walk
membranes among the mirrored faces (reversed coplanar copies with donor uv —
mirrored BY DESIGN, walk-only, drawn behind identical wall texels); the
post-fix lawful residue is membrane-count flips, not zero.
