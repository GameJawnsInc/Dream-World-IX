# ENDPOINT GRAMMAR — how stock walls TERMINATE and CONNECT (questions registered BEFORE the instrument ran)

2026-07-31. The rim-aware round scored FAIL on form and closed the minted-plan wall
lane after its declared third presentation (RIM-AWARE-PREDICTION.md): with every JOIN
built to a measured law, the two remaining defects were the COMPOSITION's own — a
seam taper's stretched face, and a cut-window promontory reading as debris. The
owner's frame, verbatim: *"some parts don't lift from base to rim cleanly. we may
need more research on how to build connective walls that have logical endpoints
instead of trying to build the top to fit. both sides have a responsibility."*

Five wall studies measured wall INTERIORS (tile language, instances, massing,
junctions, rim). None ever asked **how a stock wall ENDS** — every build cut strips
mid-wall and minted terminations stock never ships. This sixth study measures the
endpoint grammar, in service of WHOLE-FEATURE CARRY (the lane the closure clause
leaves open).

## Questions — registered before running

**E1 — THE ENDPOINT CENSUS.** Per wall component, chain the crest (the plateau-weld
line) and classify every chain ENDPOINT:
- **BORDER** — the chain stops at a block border (a per-block analysis artifact, not
  a real ending; excluded from grammar stats, share reported);
- **TAPER-TO-GROUND** — the rock body's local height collapses beyond the endpoint
  (the wall pinches out; crest meets foot);
- **CONTINUES-AS-ROCK** — the body keeps its height beyond the endpoint (the plateau
  weld stops but the massif goes on — a merge into higher rock);
- **CLOSED RING** — the chain is a cycle, no endpoints.
Frequencies of each, per-endpoint and per-component.

**E2 — TAPER ANATOMY (the owner's "lift from base to rim", measured).** For each
taper endpoint, walk the crest inward and profile the wall height h(s) = crest y −
local foot y:
- the DESCENT RUN length (stations from the tip until h reaches ~85% of the chain's
  running height) — how long stock takes to lift a wall from nothing;
- the split of the lift: does the CREST descend, does the GROUND rise, or both
  (Δy_crest vs Δy_ground over the run);
- monotonicity (does h(s) climb cleanly or step);
- the texture bands at the tip: do the crest band (cols 4-7 rows 3-4) and the foot
  band (row 10) persist into the last stations, and does the plateau's ring-1 pinch
  out with the wall.

**E3 — RING TOPOLOGY (tests the bench's own composition premise).** Per component:
chains vs cycles; for every closed cycle, what it ENCLOSES (plateau inside + ground
outside = a mesa, like our bench ring; or the reverse, a bowl; or mixed). Whether
free-standing plateau-enclosing rings exist at all at our bench's scale, or stock
walls are open ridges hung off larger masses.

**E4 — WHOLE-FEATURE CARRY FEASIBILITY.** Per component: tri count, plan footprint,
crest length, border contact. The candidate list: components that are
**SELF-TERMINATING** (every endpoint a taper or a ring, zero border cuts) and sized
for the bench (footprint within ~48u). For those, the ring-1 plateau course size
(the "both sides carried" payload — under the lattice-group pose its inner boundary
is bench-lattice-exact, so the mint shrinks to interior flat cells + the proven
ground weld).

## Method

Same crest-seeded topo-49/PLATEAU extraction as the five prior studies; read-only vs
stock disc-1; instrument `studies/overworld-topography/rock_wall_endpoints.py`;
artifacts → `out/rock_wall_endpoints.json` + renders (taper height profiles + the
best self-terminating candidates in plan).

## Success criterion

E1/E2 resolve to a nameable termination law + E4 yields at least one bench-sized
self-terminating candidate → a WHOLE-FEATURE CARRY round becomes registrable (carry
the feature complete — wall, endpoints, its own plateau course — pose it with the
lattice-group pose, weld only the foot to the bench ground). If stock has no
self-terminating features at bench scale, the wall rung rests until the bench grows.
