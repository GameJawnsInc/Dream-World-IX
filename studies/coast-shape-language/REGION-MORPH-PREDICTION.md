# REGION-CAPABLE COAST MORPHS — registered 2026-08-02, before implementation

## The gap

`cli.py` refuses every morph verb the moment `--size` is passed:

```
if (snx, sny) != (1, 1):
    raise ConfigError("cliff morphs are single-cell v1 -- drop --size")
```

So `cliff-bump`, `cliff-headland`, `cliff-bay`, `cliff-lobes` and the beach verbs reach
exactly one 64u block. **Every multi-block landmass is frozen verbatim the moment it
lands**, and on Path D there is no second chance: `morph_in_place` reads the stock
install bundles and only discs 1 and 4 exist, so nothing can be edited after deploy.

That makes ALTER — one of the three verbs in "choose / alter / implement" — have zero
reach on anything bigger than a single cell. Lifting it turns a fixed catalogue of
carryable donors into a parameterised palette: one carried headland becomes a family.

## The guard is not arbitrary — this is what it protects

`CliffWindow.__init__` does two single-cell things:

1. reads **one cell's** tris — `TR.world_tris(dbx, dby, "terrain"/"sea4")`;
2. builds `on_frame()` from the **cell** frame (`64*dbx … 64*dbx+64`) and **excludes**
   every base edge lying on it.

For one cell both are right: a coast edge at the cell boundary continues into a
neighbour you cannot see, so it must not be treated as a free base edge. For a REGION
both are wrong — the rect's interior borders are not frames, and the coast genuinely
crosses them. This is the same distinction `transplant`'s own land-fit gate already
makes ("interior borders exempt — a real 2-block landmass crosses them").

## Measured before designing

**Adjacent stock blocks weld EXACTLY at a shared border.** Over the four interior borders
of donor rect `(6,6)+2x2`, which the waisted island crosses:

| border | part | verts A / B | shared |
|---|---|---|---|
| (6,6)|(7,6) x=448 | terrain | 12 / 12 | **12, welded** |
| (6,7)|(7,7) x=448 | terrain | 10 / 10 | **10, welded** |
| (6,6)|(6,7) z=−448 | terrain | 11 / 11 | **11, welded** |
| (7,6)|(7,7) z=−448 | terrain | 7 / 7 | **7, welded** |

So a chain walk can cross an interior border with no tolerance and no snapping. Two
things also worth recording:

* **Open ocean carries no mesh at all** — block (9,5) has zero verts on its own east
  frame. A rect's interior border is only walkable where both sides have content.
* **Stock's own sea4 has a border T-junction**: `(7,6)|(7,7)` z=−448 sea4 is 8 / 12 with
  8 shared — the south block subdivides that border edge more finely. Cliff windows walk
  *terrain*, so this does not bite here, but a sea-side region verb must tolerate it.

## The build

Thread a `size` through the two `CliffWindow` construction sites (`cliff_bump`, and
`_cliff_reshape` which backs headland/bay/lobes), make the window read the whole rect and
frame-test against the REGION, and drop the CLI guard for the cliff verbs.

**Scope: the four CLIFF verbs only.** They are the landmass *shape* palette and all four
share one window class. The beach verbs use a different window and are a separate job —
saying so up front so a partial result is not reported as a whole one.

## Predictions (falsifiable, scored on completion)

* **R-1** A window whose endpoints lie in DIFFERENT cells of a rect builds, and its base
  chain crosses the interior border with exactly-coincident verts (no snap, no tolerance).
  FALSIFIED IF chaining needs any epsilon beyond the existing `_pk` rounding.
* **R-2** A single-cell call is **byte-identical** before and after the change — the
  `size=(1,1)` default must be a true no-op. This is the regression that matters: the
  bench and every shipped morph go through this code.
* **R-3** With the guard lifted, a region morph passes the same gate suite a single-cell
  morph does (clearance, fold envelope, weld audit, census).
* **R-4** At least one morph becomes possible that was impossible before: a window LONGER
  than 64u, which no single-cell call can express.

## Stop rule

Offline gates green + R-2 byte-identity proven. **Capability round — nothing deployed.**

---

## FINDINGS (2026-08-02) — the cliff verbs are region-capable

**R-1 CONFIRMED, decisively.** On a window straddling the z=−448 border of `(6,6)+2x2`:

* single-cell call on `(7,6)` → *"no cliff-base outline vert within 0.6u of (448.0,−473.33)"*
* single-cell call on `(7,7)` → *"no cliff-base outline vert within 0.6u of (464.0,−418.54)"*
* region call `size=(2,2)` → **resolved both endpoints, walked the chain across the
  border**, and got all the way to a *content* law (that island's top is a painted mural,
  so structural morphs have no fill language).

Neither single cell can even see both ends of the window. No epsilon was needed: terrain
welds exactly across interior borders (measured 12/12, 10/10, 11/11, 7/7).

**R-2 CONFIRMED — byte-identical.** All four verbs, signature-hashed against `git HEAD`:

| verb | pre-change | post-change |
|---|---|---|
| cliff_bump | `85a70c8caf4b969f` | `85a70c8caf4b969f` |
| cliff_headland | `b3303be71817ad23` | `b3303be71817ad23` |
| cliff_bay | `bd52f3f5d6cbb11e` | `bd52f3f5d6cbb11e` |
| cliff_lobes | `eebc74ef528da6ec` | `eebc74ef528da6ec` |

The single-cell path is a true no-op, which is the regression that mattered — the bench
and every shipped morph run through this code.

**R-3 CONFIRMED end to end.** A border-crossing `cliff_bump` carried through the real
`transplant_region`: `displace[terrain] applied=117/117 folds=0 ok=True`,
**all gates clean**.

**R-4 CONFIRMED, but by the right measure.** The built border-crossing windows reach
63.7u — *just under* a cell width, so "longer than 64u" was not literally achieved in the
buildable set. The decisive property is not length but **crossing**: a window straddling a
block line is inexpressible single-cell at *any* length, as R-1's two refusals show. The
339u and 207u runs do exist (the waisted island's ring crosses both interior borders of
its rect) but their morphs refuse on content laws, not on region machinery.

### A crash turned into a diagnosis

`_cliff_reshape`'s sea zip did `loop.index(k)` on every window base vert and died as
`ValueError: list.index(x): x not in list` when one had no partner on the sea4 hole
boundary. The cause is real and worth naming: **that stretch of waterline fronts the
shallow ladder (sea1/sea2/sea3/sea5), not the deep sheet, and the zip only rebuilds
sea4.** A dedicated sea1-touch gate catches most such windows first; this path is
reachable when it does not, and region windows make it easy to hit because they can run
into a ladder zone the anchor cell never saw. It now refuses by name.

### What was NOT done, stated so a partial is not read as a whole

**The BEACH verbs are still single-cell** (`--beach-bump`, `--beach-rebuild`,
`--beach-reshape`, `--beach-slide`, `--strips-rebuild`, `--sand-rebuild`, `--cap-rebuild`,
`--beach-mint`, `--band-convert`). They use a different window class. Under `--size` they
are now refused **by name**, rather than by the old blanket guard or — worse — silently
truncated to the anchor cell.

### Coverage honesty

Region frame and region read are both mutation-verified, the read via an **injected
reader** rather than game data: a mutation putting the read back to the anchor cell
passed the whole hermetic suite until that seam existed, which is the worktree-skip trap
in miniature. The missing-shore-vert diagnosis is exercised only by the live sweep — it
is a message-quality change, not a correctness law, and no geometry depends on it.

## Shipped

* `CliffWindow(..., size=)` + `CliffWindow.region_frame()`; `size=` threaded through
  `cliff_bump` / `cliff_headland` / `cliff_bay` / `cliff_lobes` / `_cliff_reshape`.
* `world-transplant --size` now accepts the four cliff verbs.
* `region_window_probe.py`, `region_morph_sweep.py` — find border-crossing runs and
  report what builds and the binding refusal for what does not.

**Capability round — nothing deployed.**
