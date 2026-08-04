# THE LATTICE FILL — registered 2026-08-04, after the crescent playtest

## What the playtest showed

The crescent itself walks and looks good (owner-confirmed). Two defects, both mine:

1. **The excise fill renders as a faceted "iceberg" with stretched, random sea tiles** at
   the vacated harbor zone (donor x 896–940, z −164…−192 → target ~(1152–1196, −1188…−1216),
   exactly where the airship screenshot sits). Measured cause: `flat_patch` ear-clips the
   whole footprint — fill tri area median 23, **max 615u², edge max 71.5u** against stock
   sea4's ceiling of **10.5u² / 7u**. Stock sea is a strict 4u lattice; the wave-animated
   sheet renders a 615u² triangle as a giant facet, and one tile quadrant smears across
   ~18 tiles of water. Lawful geometry, synthetic WATER SHAPE — THE FORM LESSON, on water.
   The isthmus's 17-tri fill was below visual threshold; this is the first fill at scale.
2. **The rim was not auto-Wanged.** I deployed without running `world-rim-retile` (one
   change per test), but the cropped rim is a known, named, verb-remedied state — it
   should ship retiled.

## The fix — carry stock's shape, not just its vocabulary

`meshedit.lattice_patch`: fill = full 4u lattice tiles exactly as stock builds them
(two tris per tile, per-tile quadrant via the calibrated avalanche hash, diagonal
orientation mixed per tile — stock measures 298 NW-SE / 156 NE-SW), with the ring margin
clipped per lattice cell so **no emitted triangle spans a tile**. Ring verts are reused
exactly (Sutherland–Hodgman keeps interior originals); adjacent cell pieces share clip
points by identical-expression construction.

Known risk, refereed empirically: margin clipping can mint a vertex where a ring edge
crosses a lattice line — a T-vert against the stock sea4 sheet across the weld. Ring
edges are themselves stock water edges (≤ ~7u), so crossings are rare; whether they land
on existing sea4 verts is what the weld-audit + border-census will judge.

## Predictions

* **L-1** Fill tri max edge ≤ 5.7u (cell diagonal), max area ≤ 8.1u² — inside stock's own
  envelope. FALSIFIED IF any tri exceeds it.
* **L-2** Tile statistics match stock by the uv-tiling gate's own measures: coherence
  1.000 by construction, adjacent-variation within 0.2 of stock's, lattice-predictability
  under the gate ceiling, quadrant skew ≤ 2.5x.
* **L-3** The full `(14,1)+4x2 → (18,17)` dry-run stays `gates CLEAN` — weld pairs 0,
  census introduced 0, border holes 0. This is the T-vert risk's referee; FALSIFIED IF
  the weld audit finds pairs on the fill boundary.
* **L-4** Every ring waterline vert appears byte-exact in the emitted fill.
* **L-5** In game, the vacated harbor zone reads as ordinary deep ocean — no facets, no
  stretched tiles. Only the playtest can settle this one.

## Deploy plan (owner-approved direction: fix + retile in one relaunch)

Redeploy the crescent with the lattice fill, then run `world-rim-retile` over
(18–21, 17–18). Two changes, but of independent, separately-locatable classes (fill =
sea4 at the harbor zone; retile = uv-only re-shade of the rim), each offline-gated on its
own numbers.

---

## FINDINGS — L-1..L-4 CONFIRMED offline; L-5 deployed, awaiting the playtest

**L-1 CONFIRMED**: 308 tris, area max 8.02u², edge max 5.66u — inside stock's 10.5/7.0
envelope. Notch coverage 12/12 unchanged.

**L-2 CONFIRMED, after two real bugs the gate caught in order:**
1. **The 1-vert fake hash key.** `_tile_quad_index` divides by a real centroid's 3; my
   single-vertex key collapsed neighbouring cells onto one hash — quadrants 119/10/1/5,
   adjacent-variation 0.078 vs stock's 0.880, a flat repeat. Refactored to
   `_cell_quad_index` on cell indices.
2. **The modulo-wrap UV.** `(x/4)%1` maps a lattice-aligned far edge back to 0, so a full
   tile's corners collapse onto the quadrant corner — one texel smeared per tile. This
   defect is **inherited from `flat_patch`'s formula** and was masked there by giant
   triangles. Cell-relative UV with the far edge at 1.0.
   Final: coherence 0.986, spread off stock 0.155, lattice-predict 36%, skew 1.8x.

**L-3 CONFIRMED, after two more:** the ear-clipper jammed on a zero-width spur the cell
clip mints where the ring runs along a plane and back (`_despur`), and — surfaced by that
jam — **excise was FAIL-OPEN on a skipped ring**: tweaks handed back with the assembly
dropped and nothing filled. Now refuses. The predicted T-vert risk materialised as 2 weld
pairs and was closed by DENSIFY-FIRST snapping (a minted crossing within 0.049u of an
existing sheet vertex lands on it) — which itself first re-minted the pair at 0.00002u by
snapping onto the *rounded key* instead of the exact float (the E-2 law, again). Final
dry-run: `gates CLEAN`, weld 0, census introduced=0.

**L-4 CONFIRMED** (ring verts byte-exact, tested hermetically).

**Coverage**: 6 new hermetic tests; 4 mutations 4 caught — the collapsed-key mutation
survived the first version of the spread test (presence + skew missed a 3:1 collapse) and
the test was strengthened with adjacent-variation, the statistic that caught the original.

**The rim retile ran and applied**: 52 quads over 2 passes, hard seams **3 → 1**, and the
survivor at cell (21,17) tile (9,5) is **stock's own arrangement** (enc E / geo E+N appears
byte-identically in the stock donor rect, which carries 4 such under-readings in this
window) — re-tiling it would author a change to verbatim stock interior, so it stays.
Soft over-cover 23/92, the owner-accepted class.
