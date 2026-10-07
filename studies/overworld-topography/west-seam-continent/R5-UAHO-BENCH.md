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
