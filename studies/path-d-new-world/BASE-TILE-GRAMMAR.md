# BASE-TILE GRAMMAR — how stock PLACES the bottom transitional course (questions registered BEFORE the instrument ran)

2026-07-31. The whole-mesa carry passed on form — "the top looks great" — but the
re-minted foot fringe FAILED as **mismatched faces** (MESA-CARRY-PREDICTION.md,
playtest 2). The recipe was statistically stock (row-10 share 53→57%, course 3.7u,
v-phase [10.12→11.09] — every number from the rim study's R5) yet read as PATCHWORK:
retiled tris beside carried tris with no tile continuity. The owner's call: *"we might
be doing slightly wrong with how the base game handles the transitional tiles at the
bottom that differ from the top... another study on the bases."* This sixth wall study
decodes the band's PLACEMENT — the thing R5 never measured (R5 was per-tri statistics:
share, height, v-range — never WHERE each tile goes relative to its neighbors).

## The suspicion driving B1

The instances study's **LAW 3**: a wall column is a CONTIGUOUS VERTICAL ATLAS STRIP —
same-column row-descent `(c,9)→(c,8)→(c,7)`, never independently-tiled course bands.
Our fringe re-mint tiled the bottom course as its own band: u marched on ARCLENGTH
stations (4.4u), v mapped by height — so tile continuity broke at every seam with the
course above AND at every retiled/carried adjacency along the foot. The hypothesis:
**LAW 3 extends into the base** — stock's bottom transitional course INHERITS each
column's u-phase (the strip above simply continues one more row, switching only the
atlas ROW to 10), and the intermittency (53% share) is COLUMN-quantized: whole columns
wear the band or don't, with transitions pinned to column boundaries. If true, no
independently-stationed band can ever match, and the correct mint is a per-column
RE-ROW of the carried bottom course (keep every u, swap the v row).

## Questions — registered before running

**B1 — U-PHASE INHERITANCE (the central question: column continuation vs independent band).**
Per stock bottom-course tri, across the shared edge with the wall course DIRECTLY
ABOVE: |Δu| at shared verts (exact-match fraction + distribution), and Δfu (fractional
phase mod tile). Split row-10 tris from other-row bottom tris — LAW 3 already implies
plain-row bottom tris continue their column; the open question is whether ROW-10 tris
inherit too (u continuous, only the row swapped) or get fresh stations.

**B2 — COLUMN QUANTIZATION of the intermittency.**
At each along-foot transition (row-10 tri ↔ other-row tri sharing an edge within the
bottom course): does the transition sit on a COLUMN boundary — fu ≈ 0/1 on both sides
of the shared edge? Re-measure run/gap lengths in COLUMN counts — integer-quantized?
(R5 measured them in u-length only: runs med 7.8u ≈ 2 columns, gaps med 6.3u —
suspiciously near small column multiples.)

**B3 — THE V-SEAM at the row boundary.**
At the shared top edge of each row-10 tri: the v-row sampled by the band side (R5 says
the band spans [10.12 → 11.09] — is the TOP edge pinned at 10.12 with tight spread?)
and the v-row the course above ENDS at on that same edge (its own row's boundary, or
continuous v, or a jump?). Compare against our formula (v by HEIGHT within the course:
`10.12 + (1-fh)·0.97` rows) — height-mapped v ignores edge role; stock may pin v per
EDGE (seam edge = 10.12, foot edge = 11.09) regardless of tri height.

**B4 — ADJACENCY BEHAVIOR along the band (the mismatched-faces signature).**
At shared vertical edges between two bottom-course tris: INSIDE a run, is u continuous
across the edge (one marching strip) or per-column independent? At run boundaries, the
Δu across the transition edge (does the gap side continue the SAME u march, so only
the row differs and rock texture stays continuous?). At foot-line plan corners/turns:
does the band break, and does it avoid high-turn verts (the tips analog — R5 noted
row 10 never reaches wall tips)?

## Method

Same crest-seeded topo-49/PLATEAU extraction as the five prior wall studies (language /
instances / massing / junctions / rim); read-only vs stock disc-1; instrument
`studies/overworld-topography/rock_wall_base.py`; artifacts →
`out/rock_wall_base.json` + an UNWRAPPED-UV strip render of a few long foot stretches
(bottom course + course above, tiles labeled, u-phase annotated — the eyeball check on
strip-continuation vs independent band).

## Success criterion

B1-B4 resolve to a nameable PLACEMENT law (inheritance yes/no, quantization unit,
v-seam rule, transition rule) → the mesa's base re-mint becomes registrable as one
lever (per the mesa registration, the foot lever does not close the carry verdict).
If no law emerges — stock's band placement is as arbitrary as arclength — the re-mint
rests, and the alternative lanes are the seat STITCH (keep the donor's own foot band
instead of burying it) or a donor-foot-band carry.
