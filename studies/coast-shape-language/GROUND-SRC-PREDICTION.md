# THE GROUND SOURCE-FAMILY MISDETECTION — registered 2026-08-02, before the fix

## The symptom

On donor `(9,5)` (the comma island):

* `--ground grass` → *"donor (9,5) is already grass -- nothing to retile"*
* `--ground snow` / `canyon` / `scrub` → `GATE retile FAIL`, and the counts are the tell:
  **`mains=0 wall=0 sand=0 foam=0 recovered=0`**, with 4 "unclassified" topo-17 tris.

The retile was not nearly-working with four holes in it. **It classified nothing at all.**

## The cause, in one line of `GroundRetile.for_donor`

```python
sand_fam = CM._sand_band_family(polys["terrain"], what=f"donor {donor}")
if src is None:
    src = sand_fam["name"] if sand_fam else "grass"
```

**The source family is detected only from the SAND BAND, so a donor with no beach is
assumed to be grass.** The comma island has no sand band and desert mains, so `src=grass`,
the grass mains rect matches zero tris, and the only tris the gate notices are strays that
fall outside every *grass* class.

That the sand band is authoritative *when present* is a real census law (it is pure per
block). The defect is the `else "grass"`.

## Measured, before touching anything

Donor `(9,5)+2x3`, 917 terrain tris, classified against `grassland.ground_main_region`:

| family | tris inside its mains region |
|---|---|
| **desert** | **355** |
| brush | 63 |
| grass | **0** |

Top topographs: `17 x355` (the dirt/desert family), `49 x294` (mountain rock), `58 x167`
(lip wall), `38 x101`. And the four "unclassified" tris carry uv `[0.6572, 0.7012 …]` and
`[0.7197, 0.7012 …]` — squarely inside the desert mains region `u 0.6572–0.7803,
v 0.6699–0.7315`. The donor is desert by every measure available; only the beach-shaped
hole in the detector says otherwise.

Independent corroboration: the carry's own texture gate already reported
`tex-family-rect: checked_by_family={'desert': 355}` — the kit *classifies the mains
correctly elsewhere in the same command*, then throws that away when picking `src`.

## The build

Detect the source family from the MAINS when there is no sand band, by dominance over
`ground_main_region` membership. Keep the sand band authoritative when it exists.

## Predictions

* **G-1** With mains detection, `(9,5)` detects as **desert**, and `--ground snow` builds
  and passes the retile gate with `mains` ≈ 355, not 0.
* **G-2** `--ground desert` on it then correctly refuses as a no-op ("already desert") —
  the *right* no-op, where today's no-op is on the wrong family.
* **G-3** Every donor that has a sand band keeps its current source family exactly —
  sand stays authoritative, so no beach donor's behaviour changes. This is the regression
  that matters: the desert bench and (7,17) ship through this path.
* **G-4** Some donors will be genuinely AMBIGUOUS (mains split across families, e.g. a
  mixed-biome landmass). Those must refuse with the counts named, not silently pick one.

## Stop rule

Offline only. G-3 (no beach donor changes) is the gate on shipping this.

---

## FINDINGS (2026-08-02) — a real bug fixed, and the true boundary named

**G-1 REFUTED in its second half, and that is the important result.** The donor now
detects as **desert** (not grass), and the wall band classifies — `wall=167` where it was
`0`. But `mains` stayed at **0**, and chasing why found the actual ceiling:

```
GRASS_TOPOS = frozenset({0, 1, 2, 3, 10, 11, 12, 13, 42})
...
if topo in self.GRASS_TOPOS:          # the mains branch
```

`mains_rect` **is** source-derived, but the topograph test is hardcoded to the grass
family. **The retile census measured `grass -> X` and nothing else.** A desert source's
mains carry topo 17, which no measured mains class covers, so a desert→snow retile would
reclassify nothing no matter how correct the source detection is.

So the prediction that fixing detection would make `--ground snow` build was **wrong**,
and the reason is worth more than the fix: this is not a feature with four holes in it,
it is a feature that **does not cover this direction at all**.

**G-2 CONFIRMED.** `--ground desert` on the comma island now refuses as *"already
desert"* — the right no-op on the right family. Before, it reported "already grass",
which was a no-op on a family the donor does not have.

**G-3 CONFIRMED — the regression that gated shipping.** Every donor with a sand band
keeps its source family exactly: `(7,17)`, `(8,17)`, `(10,17)` all still `src=grass`,
single-cell and `4x2` alike; `(19,5)`, `(20,4)` still refuse as already-desert. The sand
band stays authoritative, so no shipped beach donor's behaviour changed.

**G-4 CONFIRMED.** A donor whose mains split across families refuses with the counts
named rather than being guessed at (the winner must lead by 2x and clear a floor).

### What actually shipped

1. **The source-family misdetection is fixed.** A beachless donor is no longer assumed to
   be grass; its family is read from the mains by dominance. The kit already classified
   these mains correctly elsewhere in the same command (`tex-family-rect:
   checked_by_family={'desert': 355}`) and threw that away when picking `src`.
2. **The refusal now names the real gap.** Instead of `mains=0` plus four cryptic
   "unclassified" tris, `--ground snow` on a desert donor says: *the census measured
   grass→X only, a desert source's mains carry topo 17 which no measured mains class
   covers, so the retile would reclassify nothing — carry it verbatim or pick a
   grass-family donor.*

### What is NOT fixed — the restyle ceiling

**Restyle is a `grass -> X` capability, not `X -> Y`.** Making desert→snow *run* would
mean extending `GRASS_TOPOS` to per-family topo sets, which the interior census already
has (dirt-desert 16–23/41, scrub 4/5/6, snow 27/28, canyon 45/46 …). But the mains
translation for a non-grass source is **unmeasured**, and this arc's standing law is that
an unmeasured class must be studied, not guessed. Extending the topo test alone would
make the gate green and the result unverified — a gate green and wrong in the same number.

**The next study is the `desert -> X` mains translation**, on the model of
`island717_retile_census.py`. That is a measurement round, not a patch.

### Coverage

Three laws, all mutation-verified: the mains detection, its refusal on ambiguity, and —
after a first pass missed it — **that `for_donor` actually calls it**. Restoring
`else "grass"` passed every test until a call-site test existed; the helper was covered,
its call site was not. Same shape as the region-read gap earlier today.
