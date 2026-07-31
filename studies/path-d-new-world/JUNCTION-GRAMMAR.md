# JUNCTION GRAMMAR — how stock joins wall meshes (the study the strip carry demanded)

2026-07-31, opened on the strip-carry PLUMBING STOP (STRIP-CARRY-PREDICTION.md, SCORED):
across both playtests **not one complaint landed on a carried surface** — every named defect
lived on a MINTED JOIN. The carried content is solved; the synthesis debt is concentrated
entirely in the joins, and no study has decoded them. This study is read-only measurement
on the SAME instrument as the three prior wall decodes (rock_wall_language / instances /
massing): disc-1 crest-seeded topo-49 wall components adjacent to PLATEAU {10,11,12}.

Instrument: `studies/overworld-topography/rock_wall_junctions.py` →
`out/rock_wall_junctions.json` + a crest cross-section render. Questions declared here
BEFORE running; findings appended after.

## The three junctions, each tied to its in-game defect

### J1 — THE CREST JUNCTION (defect: "floaty grass bits at the top")

The carried crest-cap rows floated because in the donor they weld to plateau mesh behind
them, which the strip carry did not bring. Measure:

- **Weld completeness**: along the wall's top boundary (top 15% of component height,
  block-border edges excluded), what fraction of edges are shared with a PLATEAU tri vs
  open (once-edges)? Expected law: ~100% welded — stock has no floating crest.
- **Cap anatomy**: of wall tris touching a crest edge, what fraction are near-flat caps
  (dip < 35°) vs steep-to-the-top? Cap cross-section: outward extent and outward drop
  (y at the weld line vs y at the cap's outer verts).
- **The fringe behind**: for plateau tris within two rings of the crest edges, the
  (distance-behind, Δy vs crest) profile — is the plateau top flat at crest height, or
  does a fringe rise/dip? And its TILE rows vs far-field plateau tiles — is there a
  dedicated rim row?
- **The dihedral**: wall-tri dip vs plateau-tri dip across each crest edge.

### J2 — THE CORNER COLUMN (defect: "blurred mortar columns")

Our minted mortar continued one tile across the seam and stretched it over the corner
warp. Stock turns corners constantly — how? Per horizontally-adjacent instance pair
(the h_pairs machinery), binned by plan turn angle between the two faces' outward
normals (<10°, 10–25°, 25–45°, >45°):

- **Station width** of the participating instances — does stock NARROW corner columns?
- **Texel density** (atlas px per world u along the wall) each side, and the density
  jump across the pair — does stock hold density constant through a turn, or absorb
  the warp as stretch the way our mortar did?
- **The seam's uv**: at shared verts, is each side's u at a tile boundary (full tiles
  meet at the corner) or mid-tile? Mirroring rate vs turn. Same-tile rate vs turn.
- **Weld integrity**: shared-vert count across the pair (full-column weld or partial),
  and instance planarity vs turn (do corner quads warp?).

### J3 — THE WALL|GROUND WELD (defects: "missing faces + dirt at the base", ~1px dots)

Our carry buried the wall through a pierced hole; the base defects lived on that rim.
Measure what stock actually does at the foot:

- **Pierce-vs-weld law**: along the wall's bottom boundary (bottom 15%, borders
  excluded), what fraction of edges are shared with a ground tri vs open? Expected:
  stock WELDS the foot everywhere — no pierce, no hidden buried geometry.
- **The ground side**: topo histogram of foot-adjacent ground tris (shelf 13? grass?),
  their dip, their outward slope (does ground fall away from the wall — talus?), and
  their TILES vs far-field ground — a dedicated foot-transition row?
- **The bottom course**: dip/height/tiles of foot-touching wall tris vs mid-face.

## What a decode must yield

Quantitative laws a future builder can GATE on, in the same style as the massing and
instance laws — e.g. "top-boundary weld fraction ≥ X", "corner stations narrow to Y× at
turns > 25°", "foot ground slope in [a, b]". If the numbers say the three junctions are
each a small lawful vocabulary, a junction-aware builder round becomes registrable; if
they are mural-like (arbitrary per-site), the wall lane's honest next step is
whole-feature carry only.

## FINDINGS (2026-07-31, 48 blocks / 62 wall components / 9682 instance pairs)

All three junctions decode to SMALL LAWFUL VOCABULARIES — none is mural-like. The
builder-gateable laws:

### J1 — THE CREST LAW: no cap, level top, weld everything

- **Stock walls have essentially NO cap row.** Of 951 crest-touching wall tris, dip med
  **52.5°** (p25 45.3) — the steep face runs right to the weld; only 6.2% are near-flat,
  and those RISE outward (+2.5u — the start of a higher tier, not caps). The crest is a
  sharp dihedral: 52.5° face meets 7.1° plateau at the shared polyline.
- **The plateau is LEVEL from the weld line**: fringe dy med 0.0–0.25u out to 8u behind
  (render: out/crest_section.png). No berm, no dip, no rim relief.
- **No rim tile vocabulary**: fringe tiles = far-field tiles (mains cols 0–1, rows 24–25
  dominate both). The top is plain ground right up to the edge.
- **Weld completeness**: top-band boundary edges are 91.7% plateau-welded excluding
  block-border edges; raw open rate 3.6% (≤6.8% non-border), part of which is
  measurement artifact (the border test needs both endpoints on the border; cross-PART
  adjacency, e.g. vs the Sea mesh, is invisible here). Effectively: **stock never
  leaves a crest open.**
- **What our floaty bits were**: carried top-row geometry whose donor-side weld partners
  (level plateau sheet / upper tier) weren't brought, welded by us to a simplified crest
  polyline instead of to every real top-boundary edge. The law for a builder: the minted
  top sheet must weld to the strip's ACTUAL top once-edge path, edge for edge, and be
  level behind it.

### J2 — THE CORNER LAW: full stations, hard crease, mirror at sharp turns

- **Corners are ordinary columns.** Station width barely moves with turn (med 5.32u
  straight → 5.12u at 25–45° → ~5.0u at 90°+). Stock does NOT narrow, insert, or
  stretch a special mortar column. Quads stay planar (plan-RMS 0.05→0.10u); the whole
  turn is a crease AT the shared edge (pairs share exactly one edge, med 2 verts).
- **Density jumps are normal language**: adjacent columns differ in texel density by
  med 14% (p90 43%) even dead straight; 20–25% at corners. Density continuity was never
  the constraint our mortar thought it was — TILE INTEGRITY was: stock keeps full tile
  windows through every turn.
- **THE MIRROR GRADIENT** — u-mirroring is the sharp-turn idiom, monotone in turn angle:
  6–11% (0–45°) → 17% (45–70°) → 43–47% (70–120°) → 60% (120°+). At 120°+ (fold-backs,
  fins; 421 pairs >150°) seams sit mid-tile (seam@tile-edge 3.4% vs ~36–45% elsewhere):
  the same tile is REFLECTED across the seam — the butterfly is the fold vocabulary.
  (Refines instance LAW 2: mirroring isn't rare noise, it's concentrated at turns.)
- **What our mortar blur was**: a minted narrow column with a stretched, clamped,
  continued tile — off-language on every axis. The lawful seam: end strip at a full
  tile column, start the next full tile column, crease at the shared edge; at sharp
  kinks, mirror the tile instead of continuing it.

### J3 — THE FOOT LAW: weld to level plain ground; the transition art lives on the wall

- **No pierce.** Bottom-band edges are 96.7% welded (ground 70.2% + next-tier plateau
  13%) excluding border; open 2.8% raw (same measurement caveats as J1). Stock walls
  terminate ON the ground mesh, sharing verts — buried hidden geometry is off-language.
- **The ground at the foot is LEVEL and PLAIN**: dip med 9.25°, outward slope med 0.00
  (quartiles −0.07/+0.17) — no talus apron. Foot-adjacent ground wears the SAME mains
  tiles as far-field (cols 0–1 rows 24–25 / 20–21). Ground topo at the foot: grass 0
  (582), forest 36/37 (290), terrace shelf 13 (152), coastal lip 58, building 59.
- **The transition vocabulary is the WALL'S BOTTOM ROW**: foot-touching wall tris wear a
  dedicated atlas band — tiles (6–9, row 10) dominate (586 of the top counts) — while
  mid-face wears rows 6–7. The grass→rock blend is painted into the wall's bottom-course
  tiles; the ground runs plain right up to the weld. Bottom course stays steep
  (dip med 46.6° vs mid 50.6°) — the transition is TEXTURE, not geometry.
- **What our base defects were**: the pierce rim (holes + caps = the missing faces and
  dots) and carried mid-face tiles reaching the ground without the row-10 bottom course.

### The verdict on compressibility

Each junction is a one-line recipe: **crest** = weld every top once-edge to a level plain
top sheet (no cap, no rim row) · **corner** = full-tile columns creased at the shared
edge, mirror probability rising with turn · **foot** = weld every bottom once-edge to
level plain ground, bottom course wearing the row-10 transition band. A junction-aware
strip-carry round is REGISTRABLE: same carried strips, but seat/joins rebuilt to these
laws — no mortar columns (crease + mirror instead), no burial pierce (true foot weld),
top welded edge-for-edge. Whether to spend that round is the owner's call.

Artifacts: `studies/overworld-topography/out/rock_wall_junctions.json` +
`out/crest_section.png`; instrument `rock_wall_junctions.py` (read-only).
