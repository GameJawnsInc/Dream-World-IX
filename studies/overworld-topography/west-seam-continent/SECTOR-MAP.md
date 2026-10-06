# The R4 sector map — does the donor's HOME context predict the verdicts?

Registered 2026-10-06 BEFORE the instrument (`sector_map.py`) existed or ran.

## Why this exists

R4 ran twelve takes on one ~25u stretch of the massif's base, and every rejection landed on what that
take had just authored. The owner: *"we're still just smudging and guessing rather than developing real
algorithms/rules that deliver with high confidence."* The diagnosis offered in reply: the failed stretch
is where the donor's rock ends above our lawn because at HOME it stood on higher, rolling, forested
ground — a context the carry left behind — and no rule for filling that gap at the foot can be
high-confidence, because stock never builds that filler. The proposed construction (Path D's FULL
SKIRT: carry the donor's own apron + forest, weld grass to lawn) rests on that diagnosis. This map tests
the diagnosis against the verdicts we already have, before anything is built.

## The test set (labels fixed now, from PLAN.md)

Only ONE verdict was ever given on the UNTOUCHED carry (the first deploy, before any foot authoring):
*the (1418–1433, −469..−485) arc showed a grassy knoll against the mountain with no grass–mountain
transition; the rest of the perimeter and the plateau passed.* Every later verdict judged authored
surface and is not usable here (the authorship law).

- **FAILED** = rim stations whose deployed (x, z) falls in x 1418..1433, z −485..−469.
- **EDGE** = within 3u of that box but outside it — reported, NOT scored (the box is a verbal estimate).
- **PASSED** = every other rim station.

Stations are sampled along the donor's rim ring at ~1u spacing and scored by rim LENGTH.

## What is measured per station (stock disc-1 donor bytes, placed by the deployed transform)

The deployed transform is the carve's own: de-tilt plane, rotate 90°, translate to (1462, −462), and
lift by DY. DY is re-derived by matching carried donor rock verts to the live mesh, and the match must
close in xz to ≤1e-3. If it doesn't, the instrument is wrong and nothing below is reported.

- **C — home contact:** the topograph of the donor's own tri across the rim edge: bare grass (0),
  forest (37), or other (water/river/rock/etc.). "Other" is reported separately and not scored for H1.
- **R — home approach ground:** march outward from the rim at home (perpendicular, away from the
  blob). Record the home ground's height at 2/4/8/12/16u in the placed frame, and the topograph it
  crosses.
- **E — datum excess:** the placed rim height minus the pre-massif host lawn
  (`backups/west-seam-continent/r4-pre.20260828-103332`) at the same xz. This is how far the rock ends
  above our lawn.
- **K — closure:** the first outward distance where the placed home ground comes within 0.5u of the
  host lawn, plus whether the home ground up to there is all grass, or crosses forest/other. This prices
  the Path D construction per sector (carry the apron out to K and weld grass to lawn there).
- **F — the donor's own fringe:** whether the donor's rock tri on the rim edge wears the r10 c6-9 fringe
  tile (the visible transition stock puts at a bare contact).

## Hypotheses and the registered prediction

- **H1 (context):** FAILED stations sit on a non-bare home context: the home contact is forest, or the
  home ground stays ≥1u above the host lawn out to 8u (rolling/high foothill). PASSED stations are bare
  grass at home. **Prediction: H1 separates.** At least 80% of the FAILED rim length is non-bare, and at
  least 80% of the scored PASSED rim length is bare.
- **H2 (datum):** FAILED has E > 0.75u. PASSED mostly has E ≤ 0.75u (at or below the lawn, the lawful
  free-base burial). **Prediction: holds**, since this is close to the recorded high-foot finding
  (rim 4.3–5.1 vs lawn 3.2). If H2 holds and H1 does not, the forest is not the reason.
- **H3 (fringe):** FAILED edges lack the donor's own fringe tile, and PASSED edges have it.
  **Prediction: weak or none.** The owner-passed faces carry tufty tiles too (PLAN, take 8).
- **P-K (pricing):** PASSED closes within ≤6u (roughly what the kit's apron already spans). FAILED
  does not close within 6u, or crosses forest before it closes.

## What each outcome means for the build

| outcome | means | next |
|---|---|---|
| H1 holds (± H2) | the failed base is torn context, as diagnosed | Path D construction: carry apron + forest out to K, weld grass to lawn |
| H2 holds, H1 fails | the datum, not the context | seat/sink/rotate, or a LEVEL terrace host (S5's sustained ~1-1.5u offset) -- no forest carry |
| only H3 | a texture-band question | the band-continuation law, not geometry |
| nothing separates | the diagnosis is wrong | stop; report; no build |

## Declared limits

- **n is small and the labels are coarse.** One site, one verbal verdict, about 15–20u of failed rim.
  A clean separation here is evidence, not proof.
- **E uses the pre-massif host.** The take-1 lawn was apron-lifted, so E measures the gap the carry had
  to fill, not what the owner saw.
- **Nothing here is a gate.** It is a retrodiction. A construction built on it still needs its own
  registered prediction and gates.

## RESULT

(appended after the run, below this line; nothing above edited)

Run 2026-10-06 (`sector_map.py`, data `sector_map.json`). **The calibration closed:** rot 90°, DY −0.6488;
342 of 409 donor rock verts land on live rock, and 341 of those are rigid to 1e-3. Rim length scored:
FAILED 19.2u, EDGE 10.0u (not scored), PASSED 236.2u.

### The registered score

| | FAILED | PASSED | verdict |
|---|---|---|---|
| **H1** context (forest OR high approach) | 100% non-bare | 99% bare | **HOLDS** |
| H1a forest contact alone | 100% forest | 99% not forest | (separates alone) |
| H1b high approach alone | 100% high | 99% not high | (separates alone) |
| **H2** datum E > 0.75u | 100% (E p50 +1.46) | 94% ≤ 0.75 (E p50 −0.09) | **HOLDS** |
| **H3** donor fringe | lacks 0% | has 100% | **FAILS** (as predicted) |
| **P-K** pricing | 100% no ≤6u close / crosses forest | 99% close ≤6u (88% at/below lawn) | **HOLDS** |

### What it says

**The rim touches forest at home along exactly one 29.2u run,** from (1418.0, −467.8) to (1436.0, −487.6):
19.2u FAILED, 8.2u EDGE, 1.8u PASSED. That is the take-1 knoll arc, from the NW tip to the SE corner.
The other 234u of rim met bare grass at home, sat at or below our lawn (88%), and passed with no
authoring at all. The forest is also why the rock ends high there: at home the forest climbs to meet
the rock, so the rim sits at canopy height (E +1.23..+1.69). Carried without its forest, the rock's foot
hangs ~1.5u over our lawn. That gap is what twelve takes tried to fill. The donor's own fringe tile is on
100% of the rim, the forest side included, so the base texture was never the discriminator.

**Chance baseline (post-registration, not scored):** sliding an arc of the FAILED length around the rim,
it lands ≥80% on forest at 21 of 307 positions (6.8%). One verbal verdict and one site make this
evidence, not proof.

### Pricing the forest carry (post-registration)

The rim-touching home forest blob is **88 tris, ~31×32u**, bounded by grass (48.6u), the rock (29.2u) and
topo-58 coastal rock (22.3u). Placed by the carve transform, it lands right on the failed arc (the PNG).
Its heights over our lawn:

- **against the rock:** p50 +1.38 (it meets the rock exactly as at home)
- **canopy:** p50 +1.13, max +2.84
- **outer edge against grass:** p50 −1.17
- **outer edge against topo 58:** p50 −0.86

So the forest is a slope climbing ~2.5u from its outer edge to the rock. **Carrying it closes the rock
contact with stock bytes, but moves the datum mismatch to the forest's outer edge, which stands about 1u
BELOW our lawn.** At home that edge falls away to lower grass and a coastal-rock drop (−1.3 to −4.4u by
16-24u out).

**Options this prices, for the owner's call:**
- **(a) Bury the forest's outer ~1u under the lawn.** The lawn cuts the canopy slope, so the forest's own
  edge band is lost: the bury class, one material over.
- **(b) Step the host lawn down ~1u on that side.** A level lower terrace (S5's sustained offset); the
  step is grass to grass, out on open lawn.
- **(c) Carry the home ground beyond it too.** The coastal-rock drop is only lawful facing a coast, so
  this means a re-seat or rotation.
- **(d) A donor or rotation with no forest contact.** This map predicts it carries cleanly with zero
  authoring, as 236u of this one did.

**Before any of these is built:** a stock-wide census of whether the mechanism is a LAW and not this
donor's quirk. Do forest-contact rims sit at canopy height over the same massif's grass-contact rims? And
how does stock land a forest whose ground is lower than its neighbours' — (a), (b) or something else?
That turns this map into a pre-carve screen for any donor, R5 included.
