# R5c — Uaho's fringe seams — bench round (registered)

Registered 2026-10-07 BEFORE any code change or bench write. Owner: "run the seam round first."
Follows [`UAHO-LAWN-LINE-BENCH.md`](UAHO-LAWN-LINE-BENCH.md) (R5b, the lawn-line snap): its offline eye saw a rock
TOOTH where the two snapped contact tris t536/t537 meet.

## What the tooth is (measured before registering, `fringe_seam_screen.py`, read-only)

- The tooth is a CHART BOUNDARY, not one bad vertex. Two of the donor's uv charts meet along V9 → V0 → V2, where
  V9 is the snapped rim vertex and V0 = (1449.7, −490.3, y 5.61):
  - chart A (t513/t517/t519/t536) maps V0 at v 10.062;
  - chart B (t514/t518/t532/t533/t537) maps it at 9.375.
- The fringe band (the blades, the tile's bottom) therefore ends at a different height on either side of edge V9–V0.
- **Stock law:** stock disc 1 has 6 fringe v-seams > 0.25 tile among 2,536 shared fringe positions
  (`stock_fringe_continuity.py`). Every one of the 6 sits on a contact tri, and 3 are in Uaho's home block.
- **Not every seam reads as a tooth.** Uaho's NW seam (1433.7, −466.3, y 5.78), already live and passed in July and
  in U5, renders as faint vertical chart lines in the rock but no band step: its v values (9.22–9.66) sit far above
  the blades. The SE seam crosses the band.

## The rule (kit, `world-mountain`, after the lawn-line snap): THE FRINGE-SEAM UNIFY

- **Scope:** every corner of a carried fringe tri (r10 c6-9) that has a ZIP contact edge.
- **Seam:** at that position, the fringe corners' v spread exceeds 0.25 tile (stock's cut).
- **Candidates:** only v values already present there; no invented number.
- **Valid:** moving every rock corner at the position to the candidate inverts no rock tri there, so the texture never
  flips.
- **Pick:** the valid candidate that moves the fewest corners.
- **Left and named:** a position with no valid candidate, or with a non-carried rock corner (plug chart, foot course).
- UV only; nothing moves.

**The predicate's own footprint** (the screen, so the counts below are the rule's, not a proxy's; the R5b lesson):

| site | positions | pick |
|---|---|---|
| stock disc 1 | 6 (the 6 known seams) | — |
| comp20 (live) | 0 | — |
| Uaho on the R5b bench, SE (V0) | 1 | v 9.375 (chart B's), moving 4 chart-A corners. Chart A's 10.062 would invert 2 chart-B tris |
| Uaho on the R5b bench, NW | 1 | v 9.656, moving 4 corners. The two lower values would each invert 2 tris |

## What gets built (nothing live)

The kit rule + a regression test. Then a fresh mirror of live, rewound to `uaho-pre` exactly as in R5b, the
registered R5 line carved (now with the snap AND the unify), and the R3 re-stamp.

## Registered predictions

- **S1, the kit:**
  - the new test is red on today's code and green on the fix;
  - the carve test files pass;
  - `ab_carve.py` vs R5b's code: comp20 byte-identical; July and the pre-Uaho continent each change exactly
    **8 v floats at 2 positions**, nothing else.
- **S2, the bench carve:**
  - every gate line identical to the live carve's;
  - the unify's log line: 2 positions, 8 corners;
  - bench vs live: only (22,7) Terrain, **11 v floats** (R5b's 3 + these 8).
- **S3, the screen on the bench:** 0 positions selected. Stock stays at 6, comp20 at 0.
- **S4, the render:**
  - SE: the band-height step at V9–V0 is gone in the four close chase views and the zoom from the owner's
    standpoint;
  - every changed pixel (vs the R5b bench) is owned by the 8 touched tris: t513/t517/t519/t536 (SE) and
    t395/t397/t403/t424 (NW);
  - NW: no new feature in its four zoom views.
- **S5, the owner,** after a live deploy on the owner's go: no complaint at the SE end, and **no complaint at the
  NW**, an area that has passed twice. That second clause is this rule's real test of generality.

## Where the owner's eye will most likely land (named now)

1. **A column (u) seam stays at V9:** t536 samples fringe column 9.3 and t537 column 7.8, so the blade PATTERN can
   change across edge V9–V0 even once its height matches. v only is in scope.
2. **Chart A's band narrows:** t536/t517 go 0.24 → 0.41 tile/u and t519 0.30 → 0.50, against stock's contact-tri
   p97 of 0.43. The blades on the SE end's west side get shorter.
3. **At the NW, t403** (r8, the face above) goes 0.43 → 0.56 tile/u. Elsewhere there, t397 0.46 → 0.35 and
   t424 0.43 → 0.33 come closer to stock.

## Declared stops

- If the kit's selection differs from the screen's (2 positions, 8 corners) on the A/B, the round STOPS before the
  bench build: instrument and kit must agree.
- If any gate number differs from the live carve's, the round STOPS.

## RESULT

(appended after the run, below this line; nothing above edited)
