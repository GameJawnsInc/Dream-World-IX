# Grow-9013 Batch 2 — the HORSESHOE island

> **★ PASS-WITH-DEFECTS (owner, 2026-08-05, three screenshots): "pretty good."**
> **THE MILESTONE: "the falls/bridge/river is there"** — the free-ride ensemble renders on
> the SYNTHETIC disc (first in-game proof of s74's donor-path resolution for prefab
> objects; the screenshot shows both falls, the bridge, the cave mouth, and the pond).
> **TWO DEFECTS FILED:** (1) *"this desert block got pulled in and clipped which looks
> weird"* — a clipped desert wedge islet at ~(473,−643), blk (7,10) NE corner, with a raw
> untextured cut face; (2) *"513,−689 and 513,−760 have missed wangs — 2 single-edged
> touching each other then a third with a mis-aligned edge"* — the east crop-line water
> column. Forensics + fixes → DEFECTS.md beside this file.

**What's live:** the river-terrace horseshoe (Daguerreo's falls/river/bridge ensemble, donor
(5,15)+3×2) carried verbatim into the South Strait — blocks (5-7, 10-11), one sea row south
of the V-shore bench island — with the rim retiled (hard seams 14→0, via the new
OPPOSITE-PINCH RULE), coastnav stamped `land-anywhere`, and a third gateway pair: bench
**30952 (PATHDGATE3)** in, a Confirm-gated exit on the lowland arc out. Backups:
`backups\rim-retile-disc9-*`, `backups\coastnav-disc9-*`, `backups\rung6-worldside-*`
(all in the main repo).

**RELAUNCH FIRST** — 30952 registers at launch. Benches 30950/30951 are untouched.

## Stage 1 — LOOK (the carry itself)

1. `~ → Warp to field → 30952` → walk onto the pad → fade → land at **(353, −653)** on the
   horseshoe's lowland grass, facing the massif: the terraced bowl should read as a
   **stacked skyline** ~17u ahead at ~40° elevation.
2. **Checkpoints, in order of importance:**
   - Does the island read as real Daguerreo-class land (cliff walls, terraces, grass arc)?
   - **Do the falls / river / bridge structure render?** They free-ride the donor prefab
     (proven in-game on disc 1; FIRST TIME on the synthetic disc — if they're missing,
     that's the s74 donor-path split to re-read, say so and stop).
   - The water ring: any hard shade seams at the island's outer water edge? (The retile
     says 0; this is its in-game check.)
   - Look north across the strait: the V-shore bench island should be visible one sea row
     away.

## Stage 2 — EXIT

3. Walk the lowland arc around the massif's **south then east flanks** ~101u to
   **(428, −721)** — the sim walked it straight with zero deflections; the walkable land is
   a ~10u-wide ribbon (authentic Daguerreo — the massif owns the interior), so hug the grass.
4. The **"!"** appears near (428, −721) → **Confirm** → fade → bench 30952, back of the room.
5. `~ → Flags`: ScenarioCounter/gil unchanged.

## Expected oddities

- **The terrace bowl and east lobe are not reachable on foot** (measured: separate walkable
  components; stock Daguerreo's bowl is entered via the cave, not climbed). The tour is the
  lowland arc. If you want the bowl walkable, that's a follow-up (an authored ramp = new
  minted surface — needs its own round).
- The forest patch (x387-482, z−762..−727) is encounter-eligible **zone 18 (late-game
  Daguerreo set)** — the walk route avoids it, but wandering into it can start a real fight.
  Say the word and I'll `world-encounters --peaceful` the zone or retune it.
- The strait row renders as generic open ocean (it carries no overrides — by design).
- The big map still doesn't show the new islands (world-minimap deferred — its sprite is
  shared with real disc-1 play; own question, own round).

## Escapes

`~ → Go → Warp to field → 30952` (or 30950/30951). Reverts: `revert_deploy_30952.py`
(bench); the carry = delete the 30 files under `Disc9\0_1\r10\Block[5-7][10]*` +
`r11\Block[5-7][11]*` (+ restore `.prerim`/coastnav backups per the batch PLAN.md).
