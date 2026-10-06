# The forest-foot census — is the R4 sector map's mechanism a stock LAW?

Registered 2026-10-06 BEFORE the instrument (`forest_foot_census.py`) existed or ran.
Follows [`SECTOR-MAP.md`](SECTOR-MAP.md).

## The claim under test

The sector map found that R4's failed base is the one 29u stretch where the donor's rim touched a
FOREST at home. The forest climbs to the rock there, so the rock's foot sits at canopy height, and
carried without its forest it hangs ~1.5u over our lawn. That came from one site and one verdict
(chance baseline 6.8%). This census asks whether the mechanism holds across every stock massif, and
what stock does at a forest's outer edge. The second question picks between the sector map's
options (a) and (b) by evidence.

Prior art this builds on, NOT re-derives (memory `project-ff9-overworld-interior-topography`):
- stock forests are position-connected topo-37 BLOBS fully surrounded by walkable ground;
- blob rims are VERTICAL CURTAIN WALLS (90°, rise 2.0–2.6u), measured on 5 donor blobs;
- the canopy top is the walk surface.

Path D's curtain study adds that stock curtains wear a dedicated PINNED uv strip.

## The corpus

All disc-1 terrain, welded into one soup by world position. A MASSIF is a topo-49 rock component of
at least 40 tris. FOREST is topo 36 or 37; GRASS is topo 0. A rim edge is a massif once-edge, and its
contact class is the topograph of the tri across it.

**Calibration first:** the census's row for the horseshoe (R4's donor, 5-6,15-16) must reproduce the
sector map. That means a forest contact of 29 ± 3u and a forest-contact rim raised +1.2..+1.8u over
the grass-contact plane. If it doesn't, nothing else is reported.

## Registered predictions

- **P1, THE CANOPY-FOOT LAW (paired, per massif).** Take massifs with ≥4u of forest contact and ≥8u of
  grass contact. Fit a plane to each massif's grass-contact rim verts and measure the forest-contact
  rim verts' residual Δ against it. **Prediction: Δ > 0 in ≥75% of qualifying massifs, median
  Δ ≥ +1.0u.**
- **P1b (local).** At each rock–forest contact, compare the rim height with the forest blob's own
  curtain BASE within 24u (the ground the forest stands on). **Prediction: the rim stands ≥ +1.5u above
  that base on ≥75% of forest-contact length**, meaning the rock meets the canopy top, not the ground.
- **P2, the curtain is WELDED.** Exclude block-border edges. **Prediction: ≥99% of the forest-blob
  boundary length against walkable ground is a shared-vertex weld.** Stock never sinks a curtain's base
  under the ground, so option (a), burying the forest's outer edge, would be never-in-stock.
- **P3, curtain rise.** Rise is the canopy tri's top minus the boundary edge, weighted by length.
  **Prediction: p05 ≥ 1.6u, and < 5% of curtain length rises ≤ 1.4u.** Short curtains are rare, so a
  "tucked" forest whose curtain base is moved up to our lawn (rise ~1.1–1.3u) would be off-language.
  If this FAILS, a tuck is in-language and becomes a candidate option (a').
- **P4, the curtain strip is PINNED.** On the forest tri at each boundary edge, the base verts' v sits
  within ±0.5 texel of one mode on ≥90% of curtain length, and so does the top vert's v. If so, the
  strip stretches with height, and a buried curtain loses the strip's base while a tucked one keeps it.
- **P5, forests sit on LEVEL ground.** From each blob's curtain base, march outward 8 and 16u over
  ground-only tris. **Prediction: the median outward rise is within ±0.3u, and < 20% of blobs sit in a
  hollow ≥ 0.75u deep.** Option (b), stepping our lawn down ~1u around the forest, would then be an
  arrangement stock rarely builds.
- **P6, THE FALSIFIER: Uaho.** The Uaho carry (donor 0,0) was approved in-game in July ("looks good";
  "seams against the grass great") without carrying any forest, and Uaho "has forest beside the
  mountain". **Prediction: Uaho's raised forest contact (Δ > 1u) is under 10% of its rim, or the forest
  sits in its alcove, which the carry handled separately.** If Uaho has a long raised forest contact and
  still passed, forest contact is NOT sufficient to fail, and the law is incomplete.

## The screen (reported, not predicted)

For every massif: rim length, forest-contact share, and the grass-contact rim spread (de-tilted
p10–p90). The four qualified donors (uaho, crag, horseshoe, comp20) are listed first, so R5's choice
can be read off the table.

## What each outcome means

| outcome | means |
|---|---|
| P1 + P1b hold, P6 holds | THE CANOPY-FOOT LAW is general: screen a donor's rim by home contact before carving. A forest-contact stretch either carries its forest or isn't exposed to open lawn |
| P6 fails | forest contact is not sufficient to fail; find what Uaho's forest stretch had that R4's lacked before using the law |
| P2 + P3 hold | burying (a) and tucking (a') are both off-language: R4's lawful routes are (b), (c) or (d) |
| P3 fails | short curtains exist: the tuck (a') is in-language, so carry the forest and move its curtain base up to our lawn |
| P5 fails | forests in hollows are common: option (b) is in-language |
| P1 fails | the sector map's mechanism is this donor's quirk; re-open the diagnosis |

## Declared limits

- Disc 1 only. Topo-49 rock only (the R4 carry's class).
- Block-border welds are by position at 1e-3, and a few cross-border positions disagree (Path D found
  5 of 4,600), so border edges are excluded from P2.
- "Curtain" is approximated by the single forest tri on each boundary edge. A multi-course curtain
  would read as a shorter rise, which is conservative for P3.

## RESULT

(appended after the run, below this line; nothing above edited)
