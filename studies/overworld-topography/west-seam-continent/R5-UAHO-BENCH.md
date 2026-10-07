# R5 — Uaho on the continent — bench round (registered)

Registered 2026-10-06 BEFORE any bench write or dry run. Owner: "set up the R5 bench round with Uaho."
Follows [`COMP20-BENCH.md`](COMP20-BENCH.md) (comp20 deployed, owner-passed, rim walk 32/32) and the rule from
[`UAHO-JULY-STRETCHES.md`](UAHO-JULY-STRETCHES.md): **flag RAISED FOREST contacts; everything else carries.**

## Why Uaho, and what the rule predicts

- **Uaho** is `(0,0)`: 144 tris with its alcove floor, an object-class aperture (plugged by its own object
  tris), r_rim 20u.
- **Rim screen:** SAFE 71%, buried coastal rock 13%, and one raised COASTAL-ROCK stretch: 8u at E +1.49,
  lifted by a grass bank. That stretch passed in July, in the owner's direct view.
- **Forest:** its contacts all sit at/below the seat (+0.26..+0.58).
- **The rule's prediction:** no flagged stretch, so it reads right with today's `world-mountain`.

**What this round can test that comp20 couldn't:** Uaho carries one RAISED non-forest stretch with an
authored lift. Its first verdict was on a small r31 bench island; this is its first on open continent
lawn. A pass extends the rule's evidence by a second judged instance of a raised, lifted, non-forest
stretch.

## The seat

The plan's R5 seat (1488, −392) is now comp20's (deployed at (1486, −386)). The free, already-measured slot
is R4's old west-span seat:
- `--near 1452,-468`: clearance 96.8u there against the horseshoe's need of 72.3u; Uaho needs ~38;
- ~89u from comp20's centre.

The rest of the line is the plan's own Uaho flags, unchanged:
```
py -m ff9mapkit world-mountain --mod-folder <BENCH> --near 1452,-468 --donor 0,0 --reach 32
```
**Declared:** if the scan refuses at that seat, the round STOPS and reports. No improvised re-seat.

## What gets built (on a scratch mirror of the live `FF9CustomMap-world`; nothing live)

1. A fresh mirror of live. It already holds the R4 revert and comp20.
2. The carve above: dry run first, then the bench write.
3. The R3 re-stamp (`stamp_area_policy.py`, `FF9MK_WM` / `FF9MK_BACKUP` seams).

## Registered predictions

- **U1, the carve is clean.** Every `world-mountain` gate passes, the alcove floor and aperture plug included.
  The re-stamp's probes pass.
- **U2, the placed screen** (the sector-map instrument re-aimed, WITH `UAHO_ALCOVE` so its rim is the carved
  one):
  - 0% raised forest;
  - raised (E > +0.75) rim ≤ 12% of length, all of it coastal-rock contact;
  - no foot course, pull, conform or cap.
- **U3, only the intended files change.** Versus live, the bench differs ONLY in Uaho's span blocks (+ the
  stamp's area bits, + `.bak` parkings). comp20's blocks are untouched. If the span reaches col 23, the
  x = 1536 seam weld is byte-identical.
- **U4, mutual clearance:** ≥ 20u of open lawn between Uaho's placed rim and comp20's at their closest.
- **U5, scored after the owner's look on a live deploy:** no complaint about either mountain's base.

## Where the owner's eye will most likely land (named now)

1. **The raised coastal-rock stretch with its lifted grass bank** (~1.2u over ~8u): the one authored lift.
2. **The alcove and its object plug.** It has a July history: "object hole filled with grass", fixed by the
   collar-chart plug and approved.
3. **The pair together:** two mountains ~89u apart. That's a composition call, not a defect.

## RESULT

(appended after the run, below this line; nothing above edited)

### THE ROUND STOPPED at its registered stop (2026-10-06): the carve refused at the declared seat

`world-mountain --near 1452,-468 --donor 0,0 --reach 32 --dry-run` on a fresh live mirror (2,384 files):

```
donor rock component: 134 tris; alcove floor carried: 10 tris; object apertures: [7] pts (plugged)
blob: 144 tris, extent 25x31u y[2.3,13.3]; rim 27 pts max plan radius 20.0u
block span [(22, 7)] has no non-plain tris at all -- not a kit island (no coast to place against)
```

The donor side is exactly July's: 134 + 10 alcove-floor tris, the 7-pt object aperture.

**What it means** (`interior.carve_mountain`, ~:1550): Uaho is small (2·(r_rim + band) ≤ 64), so the carve takes
its byte-frozen SINGLE-BLOCK path. The span is then just the seed's block, (22,7). The placement scan scores
clearance against the span's NON-PLAIN tris (coast, cliff). With R4 reverted, block (22,7) is pure lawn, so
there is nothing to measure against, and the guard refuses.

The guard assumes every massif seat is a small kit island with a coast in its block. A large continent's
interior violates that by design. The horseshoe and comp20 were big enough for the MULTI-block path, whose
span reaches the coast.

**Nothing was written to the bench; U1–U5 never ran.** Per the registration, no improvised re-seat.

### The paths out (owner's call)

1. **A seat whose single block holds some coast**, e.g. a west-coast block. That trades the measured R4 slot
   for a coast-adjacent seat, which needs its own clearance numbers.
2. **A small kit fix:** when a span has no non-plain tris, treat clearance as unbounded (the block is interior
   lawn) instead of refusing.
   - It is placement scoring only: no geometry changes.
   - Uaho's July identity acceptance is unaffected (that bench has a coast, so the path is byte-identical).
   - It needs a regression test that fails on today's code and the identity test kept green.
3. **Force the multi-block path for small donors** (a flag). A bigger change: the single-block path is the
   frozen identity pipeline, so the multi-block path's output for Uaho would be NEW bytes, not July's.

**Correction to path 2's "identity unaffected":** `test_carve_mountain_reproduces_deployed_uaho_bench` currently
SKIPS, because its pristine r31 input and the deployed July bench are both gone. The honest regression check
for the fix is an A/B on the rebuilt r31 seed-42 bench (UAHO-JULY-STRETCHES.md's rebuild): the carve's bytes
with and without the fix must be identical where a coast exists.

### Path 2 BUILT (2026-10-06, owner: "yes, make the fix in (1)"): the interior-seat clearance fix

- **The change:** `interior.carve_mountain` treats a span with no non-plain tri as an INTERIOR seat:
  - clearance is unbounded;
  - the scan ranks by distance to the requested seat (rot 0 keeps its 0.75u preference);
  - the apron's coast taper sees no coast;
  - the old refusal is gone.
- **The test:** `test_carve_mountain_seats_on_an_all_lawn_interior_span` failed on the old code with the exact
  refusal, and passes on the fix. Every test file that exercises the carve: 97 passed, 2 skipped (the
  install-gated identity tests, whose inputs are gone).
- **THE A/B on real data** (`scratchpad/ab_carve.py`, the carve in memory, before vs after): the rebuilt July
  Uaho bench (single-block path) and comp20 on the pre-massif continent (multi-block path) are
  **byte-identical** (sha1 match on all 5 blocks). The fix is byte-neutral wherever a coast exists.

### …and it is not sufficient for Uaho at this seat: the geometry gate refuses (a new, separate finding)

With the fix, the R5 carve places Uaho at **(1450, −474) rot 0**, the nearest band-clean in-span seat to the
request. Then `gates: ... annulusOnce=8 ...` → "mountain geometry gate failed". The 8 new once-edges all lie
on **x = 1472, the east border of block (22,7)**, at y 3.194–3.217: hairline cracks.

The single-block path loads ONLY the seed block, so the apron lift near its border (gblend 12) can't reach the
deployed neighbour (23,7)'s twin verts. On a small island a block's borders face open ocean and need no weld; on a
continent all four weld to deployed land. The gate is doing its job.

**The completion, for the owner's go (it changes geometry, which path 2 promised not to):** route a small donor
to the MULTI-block span whenever deployed neighbour blocks lie within its apron reach. The multi-block path
already loads them and lifts per POSITION across borders, and it carved comp20 and the horseshoe cleanly.
- The July identity case loads only (2,19), so it stays single-block and byte-identical.
- comp20 and the horseshoe are already multi-block.
- Uaho's output on the continent would be NEW bytes, judged by the gates and then the owner.

### Path 3 BUILT (2026-10-06, owner: "yes, route it to the multi-block path"): THE CONTINENT ROUTE

- **The change:** a single-block-sized blob with a DEPLOYED neighbour block inside its apron reach
  (r_rim + gblend + 2), and a fully covered core rect, takes the multi-block span. Otherwise the single-block
  pipeline runs byte-frozen.
- **The test:** `test_carve_mountain_small_donor_beside_deployed_neighbours_takes_the_multiblock_span`, with two
  deployed lawn blocks and the saddle donor's apron reaching their shared border.
  - Red on the old code with the exact R5 failure: "mountain geometry gate failed".
  - Green on the fix: every x = 64 position holds ONE height across both blocks, and the lift really reaches
    the border, so the test isn't vacuous.
  - The carve test files: 98 passed, 2 skipped (the install-gated ones).
- **A/B:** the July bench and comp20 are byte-identical again (sha1 on all 5 blocks).
- **The R5 case** (live continent, `--near 1452,-468`, donor (0,0)) now carves on the multi-block span with
  every gate clean: placement rot 0 at **(1442, −478)**, clearance 65.3u. The widened span now holds comp20's
  rock, so the clearance is measured from comp20, and the scan keeps Uaho clear of it on its own.
- **Next:** the registered bench round, rerun as registered on a fresh mirror.

### THE ROUND, RERUN AS REGISTERED (2026-10-06, after paths 2 + 3): U1, U3, U4 hold; U2 fails on one clause

Fresh mirror of live (`scratchpad/bench-uaho-r5b`, 2,384 files). The registered command, unchanged:
`world-mountain --mod-folder <BENCH> --near 1452,-468 --donor 0,0 --reach 32`.

| | measured | verdict |
|---|---|---|
| **U1** the carve is clean | the route fired ("beside deployed neighbour block(s) [(22,6), (23,6), (23,7)] … the MULTI-block span"); span (22-23 × 6-7). Placement rot 0 at **(1442, −478)**, clearance 65.3u (measured from comp20's rock, which is now in the span). Rim 1.64–5.29 vs ground 3.20; apron lift max 1.20u; zip 57 (rise 2.26, ny ≥ 0.86, 0/57 below envelope); down 0, near-miss 0, annulus once-edges 0; apron slope 8.9°; **rock rigidity 3.1% vs the 3.5% gate (passes, little margin)**. Alcove floor + 5 aperture-plug tris as July. R3 re-stamp: 618 verts | **HOLDS** |
| **U2** the placed screen | instrument with `UAHO_ALCOVE`: rot 0, DY −1.5887, 84/89 rock verts rigid on the bench mesh. Raised (E > 0.75) **11.8%** (≤ 12% ✓), **0% raised forest** ✓, but 3.4u of the raised rim is GRASS contact at E +0.76..+0.88, not all coastal rock ✗. That 3.4u was already in FOREST-OR-DATUM's numbers; the registered clause was written too narrowly | **FAILS on one clause** |
| **U3** only intended files change | `bench_vs_live.py`: 2 paths differ, both in (22,7) (its Terrain + the carve's `.bak`); comp20's blocks untouched; the x = 1536 seam weld byte-identical on rows 4–9 | **HOLDS** |
| **U4** mutual clearance | closest rims 64.1u apart (Uaho (1438.1, −462.6) – comp20 (1460.8, −402.7)): ≥ 40u of open lawn beyond both aprons | **HOLDS** |

**Disc4 on the bench** was not mirrored: an absolute bench path. The parallel auto-mirror fix now says so
explicitly. A live deploy names the folder.

**For the owner's look (U5), after a live deploy on the owner's go:**
- **(1412.6, −490.7), face north-east:** the raised coastal-rock stretch with its lifted grass bank, target #1;
- **(1473.6, −472.8), face west:** the alcove and its plug, target #2.

The renders are `scratchpad/uaho_r5_sheet.png` (game atlas pixels, not committed).

### DEPLOYED LIVE (2026-10-06, owner: "yes, deploy Uaho live")

- **Preflight:**
  - live = the bench except (22,7), the carve itself (bench_vs_live: 2 paths, 0 outside);
  - FF9.exe not running, no harness arm file;
  - the worktree carve code = master.
- **Backup:** the whole live WorldMap Disc1/0_1 + Disc4/0_1 → `backups/west-seam-continent/uaho-pre.20261006-231630`
  (1,687 files, 0 mismatches). **THE REVERT.** Restore only (22,7) + its Disc4 mirror, since the backup holds
  other sessions' content too.
- **The carve live:** `world-mountain --mod-folder FF9CustomMap-world --near 1452,-468 --donor 0,0 --reach 32`.
  The route fired as on the bench; rot 0 at (1442, −478), clearance 65.3u, every gate identical. **Disc4
  mirrored** (9 files).
- **The re-stamp live** (from the MAIN repo):
  - 1,236 verts across 52 files;
  - backup `r3-pre-area14.20261006-231700`;
  - `probe_area14.py` ALL CHECKS PASS (a–e).
- **Verification:**
  - live Disc1 = the measured bench Disc1 (727 identical, 0 differing; `.bak` excluded);
  - Disc4 (22,7) Terrain = Disc1.

**For the owner's look (U5):**
- **(1412.6, −490.7), face north-east:** the raised coastal-rock stretch + its lifted grass bank;
- **(1473.6, −472.8), face west:** the alcove + its plug.

### U5, THE OWNER'S LOOK (2026-10-07): one complaint, at two carried donor tris

What the owner said about the live deploy (three screenshots):
- At viewpoint 1, (1412, −490): "i'm far away from the mountain … are those coordinates correct?"
- At (1434, −482): "i think i see the raised grass bank here? … looks fine to me"
- At (1456, −491): "the real problem is screenshot 3. the cliff hits the grass with no transition tile."
- "the rest of that mini-mountain reads pretty well overall besides screenshot 3"

| | verdict |
|---|---|
| target #1, the raised coastal-rock stretch + its lifted bank | **PASSES.** (1434, −482) is the stretch itself: stations 15–18, E up to +1.97. |
| target #2, the alcove + its plug | passes ("reads pretty well overall") |
| **U5** no complaint about either mountain's base | **FAILS on one stretch:** Uaho's SE end. comp20 had already passed. |

**Viewpoint 1 was an instrument error.** The viewpoint script stood 32u from the BLOB CENTRE along the stretch's bearing.
But the stretch sits in the blob's concave west waist at r ≈ 7–8u, so the stand-off was ~25u from the stretch, not
the intended ~12u.

### Localization (`uaho_contact_tiles.py`, read-only on live)

- **The offline render reproduces the complaint.** The views were rendered from the owner's standpoint; the
  renders are in the scratchpad (atlas pixels, not committed). The SE end's base is a clean rock edge, while the
  flank beside it shows the grass-blade fringe.
- **The tile is not missing.** All 27 live rock-grass contact tris wear the fringe tile, r10 c6-9. Calibration:
  the same predicate over stock disc 1 reads 1130 contacts, 92% fringe, matching `stock_fringe_census.py` exactly.
- **THE LAWN-LINE LAW (new, measured on stock disc 1).** Stock seats each fringe contact EDGE exactly on the
  tile's painted lawn line, v = 1.0 of its row:
  - 1037 of 1044 edges sit within 0.02 tile of it (p99 0.000);
  - only 3 edges map-wide fall below 0.90: two are **Uaho's own home tris, (0,0) t404/t405**; the third is at (18,9).
- **Live:**
  - comp20: 0 of 36 contact edges off the line.
  - Uaho: 3 of 27 (7.4u). t537 (home t405) reads lawn line [1.0, 0.188] and t536 (home t404) reads [0.531, 1.0].
    Their shared rim vertex (1452.2, −492.8, y 2.48) carries v 10.19 / 10.53, not 11.0, so the base there samples
    mid-tile rock with no blades. These edges lie 3.1u and 5.5u from the owner's standpoint.
  - The third Uaho edge, t538 (0.884) at the alcove floor, was not flagged.
- **Authorship: the donor's bytes, carried verbatim, NOT anything the carve wrote.** No verdict ever covered these edges:
  - at home they meet a 2u grass strip on Uaho's island shore;
  - in July they faced 12u of bench lawn and then the bench coast, on the far side of the rock from the owner's
    July viewpoint, which faced the west rim;
  - on open continent lawn every side is in view.

**What it adds to the rule:** the screen now carries two flags: RAISED FOREST contacts, and **OFF-LAWN-LINE contact
edges**. Both are the same class: the home context hid a donor-verbatim surface, and the carry exposes it (THE
OVERHANG-CONTEXT class). Unlike the marginal gates, this is a stock-SHAPE predicate: stock builds it on 3 of 1044
edges. Run before the deploy, it would have named this exact stretch.

**The candidate fix (owner's call; NOT built):** snap the one rim vertex's v onto the lawn line in its two tris.
- It changes 2 uv entries and no geometry.
- Density doesn't change: t536 stays 0.24 tile/u and t537 0.52, t537's figure being the donor's own.
- It does author the rock-to-grass contact's UV, conforming it to the stock law.
