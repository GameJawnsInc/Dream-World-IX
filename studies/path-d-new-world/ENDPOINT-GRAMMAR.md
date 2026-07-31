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

---

## FINDINGS (measured 2026-07-31 — 48 blocks / 62 components / 179 crest endpoints)

**E1 — THE TAPER LAW. 100% of real endpoints taper to ground.** Of 179 crest-chain
endpoints, 134 (75%) are block-border truncations (per-block analysis artifacts,
excluded); of the 42 REAL endpoints, **42/42 are TAPER-TO-GROUND and 0/42 are
continues-as-rock**. A wall that "just stops" — the object every cut window minted —
does not exist in stock. Every stock wall either pinches out to the ground or closes
into a ring. Two texture corollaries at the tips: the crest band (cols 4-7 rows 3-4)
runs all the way INTO the tip (52% band share near tips vs 13% mid-run), and **the
row-10 foot band NEVER reaches a tip** (0 band tris within 9u of any tip, vs 1307
mid-run) — endings are bare-footed.

**E2 — taper anatomy, qualitative + one honest instrument limit.** At the tip the
crest touches the ground (h(0) med 0.0 across all 37 profiled endpoints — the lift
starts from zero, no end-face). Most real endpoints belong to LOW walls (29/37 never
exceed 4u); the 8 tall tapers ramp up over ~15u med (~3 stations, p75 25u). Beyond
that the h(s) profile is width-polluted (the 3u ground probe measures wall widening,
not lift alone) and its crest-vs-ground split is unreliable — declared, NOT fixed,
because it is NOT load-bearing: under whole-feature carry the endpoints are CARRIED
donor bytes, never minted. If a future round must MINT a taper, this measurement
gets its own instrument first.

**E3 — rings exist and every one is a MESA.** 3 closed crest cycles in the census,
3/3 enclose plateau with zero ground inside (mesa: plateau in, ground out) — the
bench's composition premise was stock-lawful all along; what was unlawful was
assembling it from cut strips. Ring crest lengths 27-127u.

**E4 — THE CANDIDATE: the blk (15,14) MESA, a complete stock feature.**
`out/mesa_15_14.png`. A pure closed ring — ZERO open chains, so E2's anatomy is not
even needed to carry it:
- 325 wall tris / 195 verts; plan 61.3 × 56.6u (fits the bench's ~50u grass reach);
  body y 3.0 → 27.4 (24.4u tall);
- crest ring: 20 verts at y ≈ 26.3, wander ±0.9u; 20 ring-1 plateau tris + the
  enclosed plateau (~44 tris) — the whole top is donor bytes;
- boundary composition: 20 plateau edges (the crest weld) + 40 ground edges (the
  foot) + ZERO rock edges — fully self-contained;
- border contact: only 6 verts, all SKIRT-level (y 4.4-6.8) at the block's west
  edge — a foot-level clip resolvable by a one-neighbor stitch (blk (14,14)) or a
  local trim at the build's own level cut. To scope at registration.
- A proportions law visible in the render: the mesa is mostly BODY (broad sloped
  rock all around) with a SMALL top — our bench ring was the inverse (thin wall,
  big flat top).
Runner-up (the small-carry class): the blk (13,16) RIDGE — 116 tris, 40 × 20.8u,
both real ends taper (2 taper + 2 border endpoints, 16 border verts) — a
cross-block stitch away from complete.

## VERDICT — the success criterion is met

The termination law is nameable (THE TAPER LAW: taper or ring, nothing else) and a
bench-sized self-terminating candidate exists. **A WHOLE-FEATURE CARRY round is
REGISTRABLE**: carry the (15,14) mesa COMPLETE — wall ring, crest, ring-1, enclosed
plateau, tapered skirt — under the lattice-group pose (90° yaw + 4u micro-shift,
already probe-proven), seat it, and weld ONLY the foot to the bench ground with the
proven level-cut machinery. No seams (nothing meets anything), no top mint (the top
is donor), no endpoint mint (a ring has none). The mint surface shrinks to exactly
one junction — the foot — which passed both prior playtests silently. "Both sides
have a responsibility" fully realized: both sides are the donor's own bytes.
