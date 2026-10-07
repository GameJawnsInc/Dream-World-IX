# R5b — Uaho's SE end, the lawn-line snap — bench round (registered)

Registered 2026-10-07 BEFORE any code change or bench write. Owner: "yes, build the fix on the bench."
Follows [`R5-UAHO-BENCH.md`](R5-UAHO-BENCH.md) U5: the owner's screenshot 3, localized to two carried donor tris.

## The rule (kit, `world-mountain`)

**THE LAWN-LINE LAW** (measured in U5 on stock disc 1): stock seats each fringe contact edge (rock wearing the
r10 c6-9 tile, against grass) on the tile's painted lawn line. That line is v = PV + 11·TV = 0.3632812, found on
2,081 of 2,088 contact-edge ends.

**The snap:** after the zip is emitted, find every carried rock tri wearing a fringe tile that shares an edge with a
GRASS ZIP tri.
- Each end of that edge whose v sits more than 0.05 tile off the lawn line is moved onto it. Stock's own p99.5 is
  0.031.
- At that position the snap moves every carried rock corner, and acts only if every rock corner there belongs to
  such a contact tri. Otherwise it skips and logs, because a snap there would open a v seam against an interior tri.
- One report line gives the positions and entries snapped, and names any off-line zip contact left.

**Scope:**
- Zip contacts only: the seam where the carve decides what the rock meets.
- Carried-to-carried contacts stay verbatim (the alcove floor, the plug chart). That includes Uaho's third
  off-line edge, t538, a plug tri against the carried alcove floor, approved in July.
- No geometry changes. Two uv entries stop being donor-verbatim.

## What gets built (nothing live)

1. The kit rule plus a regression test.
2. A fresh mirror of live `FF9CustomMap-world`, with every file the Uaho deploy changed rewound to
   `uaho-pre.20261006-231630`.
3. The registered R5 line, carved with the snap, unchanged:
   `world-mountain --near 1452,-468 --donor 0,0 --reach 32`.
4. The R3 re-stamp (`stamp_area_policy.py`, using the `FF9MK_WM` / `FF9MK_BACKUP` seams).

## Registered predictions

- **L1, the kit:**
  - the new test is red on today's code and green on the fix;
  - every carve test file passes;
  - `ab_carve.py` A/B: comp20 is byte-identical. July changes ONLY the v of the two corners at one position in the
    same two donor tris (July t595/t596); zero other bytes.
- **L2, the bench carve:**
  - every gate number is identical to the live carve's log: placement rot 0 at (1442, −478), clearance 65.3u,
    zip 57, rock rigidity 3.1%;
  - plus the snap's line: 1 position, 2 entries;
  - bench vs live: only (22,7) Terrain differs (+ the `.bak`), and inside it exactly 2 v floats.
- **L3, the law on the bench** (`uaho_contact_tiles.py --edges`):
  - Uaho's zip contact edges off the line go 2 → 0;
  - t538 stays: 1 edge, 0.884, out of scope;
  - comp20 stays at 0.
- **L4, the render:** from the owner's screenshot-3 standpoint (U5's four close chase views), the bench shows the
  fringe at the SE end's base where live shows a clean edge. Every changed pixel is owned by t536/t537 (id buffer).
- **L5, the owner,** after a live deploy on the owner's go: no complaint at the SE end, and no new complaint
  elsewhere.

## Where the owner's eye will most likely land (named now)

1. **t537 itself.** Its texture runs 1.62 tiles over a 2.6–3.1u rise: 0.52 tile/u, against stock's p97 of 0.43.
   That is the donor's own density, carried unchanged. The blades will appear at its base, but its upper rock reads
   squashed next to its neighbours. If the eye objects to the new base, this tri is why.
2. **The t536/t537 internal edge.** The donor's own v seam at its TOP vertex stays (10.06 vs 9.38); the snap closes
   only the bottom one.

## Declared stops

- If the snap would need to touch a position with an interior rock tri, the round STOPS and reports.
- If any gate number differs from the live carve's, the round STOPS: the snap must be geometry-neutral.

## RESULT

(appended after the run, below this line; nothing above edited)

### Run 2026-10-07: L3 and L4 hold; L1/L2 miss on the COUNT (2 positions, 3 corners, not 1 and 2); no stop fired

| | measured | verdict |
|---|---|---|
| **L1** the kit | `test_carve_mountain_snaps_an_off_lawn_line_rim_vertex_onto_the_fringe_row` + `test_lawn_line_snap_skips_a_position_an_interior_rock_tri_fans_at`: red on today's code (old code carries the off-line v 0.338 / 0.349 straight through), green on the fix. The 16 world test files touching the carve: 359 passed, 4 skipped. `ab_carve.py`: **comp20 byte-identical** (4 blocks). July changes 3 v floats at 2 rim positions; positions and topos identical | the count **MISSES** |
| **L2** the bench carve | fresh live mirror (2,384 files); live differed from `uaho-pre` in exactly (22,7) Terrain ×2 discs + the carve's `.bak`, so the rewind is exact. The registered line carved: every gate line **identical** to the live carve's log, the route fired. Snap line: "2 rim positions, 3 carried corners". Stamp: 618 verts / 52 files. Bench vs live Disc1: 726 identical, 1 differs, (22,7) Terrain. **4 bytes, all inside the uv block = 3 v floats** | the count **MISSES**; the shape holds |
| **L3** the law | Uaho's zip contacts off the line **2 → 0** (t536/t537). t538 stays: 1 edge, 0.884, out of scope as registered. comp20 0 | **HOLDS** |
| **L4** the render | four close chase views from the owner's standpoint, live vs bench: the fringe blades now run along the SE end's base where live shows a clean rock edge. **Every changed pixel is owned by t536/t537** (19.7k–46.7k px per view, via the id buffer) | **HOLDS** |

**Why the count missed.** It was derived from the U5 census's cut ("an end < 0.90 tile"). That cut is one-sided and
coarser than the rule's own registered tolerance (|dev| > 0.05). The rule itself ran as registered:
- the third corner is **t400 at the NW tip** (1429.7, −462.3), at 10.9375 tiles: 0.0625 = 2 texels inside the line;
- stock carries that exact value once (0.3613281, among its 7 not-on-the-line ends);
- its close renders show a ≤ 2-texel texture slide with no new feature. It doesn't appear in the screenshot-3 views.

**Seen by the offline eye (named in advance as eye-landing #2): a dark rock TOOTH where t536 and t537 meet.**
- The snap closed their shared BOTTOM vertex (spread 0.344 → 0).
- Their shared TOP vertex (1449.7, −490.3, y 5.61) keeps the donor's spread of 0.688 tile (t537 9.38 vs t536 10.06).
- Down the shared edge, the blade band therefore ends at a different height on each side: a short step where
  t537's rock drops below t536's blades. It shows in the zoomed SE and S views, and as a notch in the c140/c160
  chase views.

**Stock context, measured the same day:** stock disc 1 has 6 fringe v-seams > 0.25 tile in all its fringe tris, and
3 are in Uaho's home block (0,0). Two of them are this pair's bottom and top vertices.

So Uaho's SE end holds:
- 2 of stock's 3 off-line contact edges;
- 2 of stock's 6 fringe v-seams.

It is the map's densest anomaly cluster on a rock-grass contact, a stretch the donor's home never had to dress.

**Declared stops:** neither fired. No snapped position has an interior rock tri, and every gate number matches the
live carve.

**For the owner:**
- Bench at `scratchpad/bench-uaho-r5c`. Renders in `scratchpad/render_lawn_ab/` (atlas pixels, not committed).
- Live is untouched.
- The tooth (the top seam) is NOT in this round's scope. Closing it would mean authoring the v of a donor vertex
  shared by four carried tris (t514/t517/t536/t537). That is a new rule (fringe v-seam continuity) and a new round.
