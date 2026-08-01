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

---

## FINDINGS (measured 2026-07-31 — 48 blocks / 62 components / 904 course-seam edges / 846 side edges)

One instrument pass, no iterations. Artifacts: `out/rock_wall_base.json`,
`out/base_strip.png`.

**B1 — THE BAND-CONTINUATION LAW. The transitional band is never PLACED — it is the
column's own uv continuation.** At the course seam, row-10 tris are **100.0%
u-continuous AND 100.0% v-continuous** with the course above (|du| med 0.0, p99 0.0
col; dv = 0.0) — across 1,090 seam verts, not one exception. The dominant pair is
(10 below ← 9 above): 480 of 904 seams; col relation same 687/217. The band literally
continues each column's contiguous vertical atlas strip (LAW 3 extended into the
base, in the strongest possible form). By contrast, OTHER-row bottom tris re-phase
freely: only 41.6% u-continuous, |du| med **4.08 cols ≈ the band's 4-col width**
(re-phasing by whole band-widths is art-identical), dv med −4.97 (fresh rows).
Shared vertex indices are 0% on both — continuity is by VALUE on duplicated verts.

**B2 — column quantization is real but SOFT.** Foot edges span ~1 column (med 0.97,
59.8% exactly 1 ±0.1); row-10 runs med 1.97 cols, gaps med 1.0 col, ~50%
near-integer; transitions sit on a column boundary 58.8% of the time (med 0.05 col).
The sharpest fact: **71.2% of transitions carry u straight THROUGH** — the gap
continues the same u march with only the ROW swapped, so rock texture stays
continuous across band on/off boundaries. Our arclength stations broke this at every
transition.

**B3 — the v-seam is a COPY, not a pin.** The band's top edge samples v-row
**10.16 on BOTH sides** (p25 = p75 = 10.16): row 9 runs 0.16 rows past its nominal
boundary and row 10 begins at exactly that value. Our formula's 10.12 was close
numerically but wrong in kind — the law is zero-freedom uv-copy from the course
above, not an independent pin.

**B4 — adjacency + corners.** Side (vertical) seams inside the bottom course are
68-75% u-continuous; the discontinuities cluster at |du| ≈ 4 cols (band-width
re-phases). Mixed-row side edges are 86.4% continuous — even where the row flips,
the u-phase carries. And the band AVOIDS corners: at foot verts with ≥45° plan turn,
both-flanks-row-10 drops to 25.4% vs the 50.0% all-verts baseline (half rate) — the
tips-avoidance R5 saw, generalized to sharp turns.

**The render (`out/base_strip.png`) is the mesa donor itself** — (15,14) owns the
census's longest foot chain, and its bottom course is nearly SOLID row-10 in
one-column cells with single other-row cells interleaved. The 53% share is a pooled
census number; per-donor share varies widely, and OUR donor's band was
near-continuous before the bury seat cut it away.

## VERDICT — the success criterion is met

The placement law is nameable and total: **keep every u; the band is the strip
continued.** The lawful re-mint (the next registration, not built here): per
bottom-course column of the carried mesa, COPY the seam uv from the donor course
above verbatim (no stationing of any kind), wear row 10 by continuing v downward
from the copied seam value, carry u straight through any band gaps, put transitions
on column boundaries, and keep the band off sharp foot corners. One honest caveat
for the build round: the level cut's seam v is donor-arbitrary (the cut broke course
quantization), so where the seam v is far from row-9's terminal zone (~10.16) the
lawful choices are a mid-face continuation (what the donor already wears) or a
whole-band-width re-phase — never a fresh station. The alternative lane if
texture-only proves insufficient: re-seat (stitch) to restore the donor's own
near-solid band.
