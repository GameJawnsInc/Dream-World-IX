# THE COAST LINT — P3 opening round (registered BEFORE building, 2026-08-02)

## Why this and not "rebuild the rest of the coast"

The plan said "apply the proven pipeline to the rest of the coast". Stating that
plainly exposes its flaw: **the rest of the coast is already owner-accepted** —
it is literally the reference the peer gate scores against. Rebuilding accepted
shore would mint fresh authored surface where none is needed, and this arc's
single most reliable finding is THE DEFECT FOLLOWS THE AUTHORSHIP (12 of 13
verdicts, 32 of 37 named defects, landed on whatever the round had just made).

So the round inverts: **measure first, and rebuild only what measurement
condemns.**

## What is already covered island-wide (so this round must not re-do it)

* the latent hard-lock sweep already runs over the whole six-block bench
  (~17k standable points, green);
* the walker drive already runs island-wide (0 hard-trapped, 0 ring-poisoned);
* the peer gate samples four far shore stations, all passing.

## The measurement gap

**Flow (the hug axis) is tested at five spawn points, all next to the corner.**
That is the axis that produced the V-corner catch in the first place, and it has
never been run around the whole island. The look axis is likewise sampled only
near the corner.

## The build

`coast_lint.py` — walk the bench's ENTIRE walkable boundary and score every
vertex for catch risk under the quantised-fan law (a hug hold cannot turn more
than 67.5 deg in one step), then HUG-TEST the flagged sites in the simulator
rather than trusting the score. Two stages, because a static score is a
hypothesis and the simulator is the oracle: the fan law is what the V-corner
score said, and the hug gate is what actually caught it.

## Predictions (falsifiable, scored when it runs)

* **P-1** The lint finds the whole boundary, not fragments: one closed chain (or
  a small number), total length on the order of the island's perimeter.
  FALSIFIED IF the chain walk fragments — which would itself be a finding, since
  a boundary that will not close is a hole.
* **P-2** The corner span the owner just accepted scores CLEAN — the lint agrees
  with the playtest. If the lint condemns owner-accepted shore, **the lint is
  wrong, not the shore** (the calibration law, learned twice this session).
* **P-3** At least one non-corner site scores at catch risk. If ZERO, the flow
  axis is clean island-wide and P3 reduces to "nothing to fix" — a legitimate
  and cheap outcome that must be reported as such, not padded with work.
* **P-4** Every site the static score flags is then confirmed or refuted by the
  simulator. I expect refutations: the score is a screen, not a verdict.

## Stop rule

If P-3 comes back empty and the hug tests are clean island-wide, **the coast is
done** and the next work is Rung 6 (entrance/exit), not more coast.

---

## FINDINGS (2026-08-02) — THE COAST IS DONE. Predictions scored.

**P-1 FALSIFIED in letter, benign in substance.** 16 boundary chains, not one:
the largest is CLOSED (117 verts, 299u) and the rest are open fragments where
the walkable surface meets block edges and interior features. Total boundary
933u. Nothing here indicates a hole; the chain walk is simply not the right
primitive, which is why the scorer was rewritten to work off the ADJACENCY.

**P-2 CONFIRMED — and it did its job three times.** The lint accused
owner-accepted shore on its first three runs, and every time the instrument was
wrong, exactly as the registration required me to assume:

1. *chain-walk artifact* — scoring a walked polyline produced a crop of -180
   turns that were the walk doubling back at forks, not geometry. Fixed by
   scoring each vertex against its own incident boundary edges.
2. *the metric was backwards* — I took the MAX over plausible holds ("does some
   hold fail here"), which is true almost everywhere and flagged 117 vertices.
   A walker needs only ONE hold that works: it must be the MIN. 117 -> 21.
3. *drop-in vs traverse* — spawning 1.2u from a site caught walkers essentially
   at the spawn, measuring "is this spot cramped", not "can the coast be
   walked". With a 5u run-up and SHORE-FOLLOWING holds (the route a player
   actually takes, rather than an arbitrary compass heading held into an
   inlet): 21 -> 1.

**P-3 NEGATIVE — and that is the result.** The single surviving site
(420.03,-489.79) is the tapering tip of a shore spit at y=4.73: a walker
holding a heading into a narrowing point stops, which is ordinary terrain, not
a trap. The latent sweep independently reports **0 hard-locks over ~17k
standable points island-wide**, and the walker drive reports 0 hard-trapped and
0 ring-poisoned. **The flow axis is clean island-wide.**

**P-4 CONFIRMED, emphatically.** 117 flagged -> 21 -> 1 -> 0 real defects, and
every reduction was a correction to MY instrument rather than a discovery about
the coast. The static score is a screen; the simulator is the oracle.

### The verdict, and the stop rule firing

**Nothing on the coast needs rebuilding.** The registration's stop rule was
written for exactly this outcome, so it is honoured rather than argued around:
rebuilding accepted shore would mint fresh authored surface where measurement
finds no defect, and THE DEFECT FOLLOWS THE AUTHORSHIP is this arc's most
reliable finding. **P3 closes as a negative result. The next work is Rung 6
(entrance / exit), not more coast.**

`coast_lint.py` stays as the flow-axis instrument for any FUTURE coast edit —
that is where it earns its keep, since it now encodes the three corrections
above.
