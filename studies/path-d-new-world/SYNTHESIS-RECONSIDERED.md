# Synthesis on a blank world — the hypothesis, and what the record actually says

2026-07-29. The owner proposed using the blank Path D world to finally apply the project's transplant
knowledge to SYNTHESIS. The orchestrator endorsed it with an adjacency argument. **Three sweeps of the
primary falsification record refuted that argument**, while confirming a different and better version of
the owner's instinct. Recorded here because it supersedes a CLAUDE.md §8 line.

---

## The refuted argument (mine, not the owner's)

> *"Every one of those verdicts was rendered by juxtaposition — synthetic terrain sat next to real stock
> terrain and read as wrong. On an empty ocean with no stock adjacency, the judge changes."*

**FALSE.** Every one of the seven falsified attempts was ALREADY built on a blank, isolated, purpose-minted
islet in open ocean, with no stock land in frame:

| Attempt | Bench |
|---|---|
| massif synthesis | block (2,19), seed-42 islet, world (160,−1248) |
| beach-mint ladder | desert r18 seed 11, (288,−1243), block (4,19) |
| dunes mint (small) | r26 islet, (672,−1248) |
| dunes stamp (real scale) | r56 mint, (1248,−1184) |
| v3 bend-carry | island F, r26 seed 15, (224,−1120) |
| Rungs C / D / E | purpose-built landmasses in open-ocean pockets |

**Isolation was the default condition of every synthesis failure, not the missing ingredient.**

And the decisive counter-example runs the other way. **THE SPUR** — one course of FULLY SYNTHETIC rock
grafted onto the REAL Daguerreo massif at cell (1,17), directly abutting verbatim stock, owner explicitly
comparing — **PASSED**: *"looks good, i compared to verbatim."* Synthesis survived the hardest possible
juxtaposition while the isolated benches died. The adjacency theory predicts the opposite of the outcome.

**Also refuted: the round-cost argument.** The expensive era ended through INSTRUMENTATION, not canvas —
Rungs C/D/E were each rejected at ZERO playtest cost by the frozen offline eyes (`dunes_grazing_eye.py`,
`uvf_eye_pixel.py`, `massif_face_render.py`, `contract_mass_gates.py` v4). Massif synth's 8 playtest
rounds, the bend-carry's 3 and the beach mint's 4 all predate those.

---

## What the blank canvas GENUINELY buys

1. **THE ONE-SITE WORLD LAW dissolves outright.** It is pure occupancy — the stock map holds exactly one
   landmass of the two-ground class. 480 free cells, no competing occupant, no target hunt, no disc-4
   mirror pin, no coast-standoff site ceiling.
2. **Footprint budget stops binding.** THE COMPOSITION FOOTPRINT LAW and the ~130-cell dunes SIZE-CLASS
   floor were budget failures — Rungs C/D/E died because anchor clearance radii plus coast standoff
   consumed the available line on a small site. Trivially satisfiable now. **This is the owner's instinct,
   correctly located: the contextual variable is FOOTPRINT, not isolation.**
3. **THE WALL-CONTEXT LAW becomes a design choice.** It is 100% a statement about FF9's painted grammar
   with zero mesh consequence; on a new world, an "off-language" coast is a decision, not a defect.

---

## The real boundary — synthesis vs carry is the WRONG AXIS

Sorting every verdict in the record by what actually shipped:

**Synthesis PASSES, repeatedly and in-game** — geometry, and anything expressible as an exact-linear TILE
LANGUAGE: the `blob_outline` coastline, the 73° cliff profile, the dome/hill, THE RELIEF RESURRECTION
(2-octave value noise, *"nice - gently rolling"*), island E (from-scratch ~112×114u 3-lobe grass mint,
★ in-game proven), the whole shipped `world-island` cliff verb, THE SPUR.

**Synthesis FAILS every time** it attempts hand-authored, non-lattice, **CONTINUOUS-FLOW TEXTURE
ORGANIZATION**: massif flanks, gore panels, forest canopy, ecotone dressing arrangement.

THE FORM LESSON is intact and untouched by the canvas — the atlas, the 4u lattice, the barycentric
interpolator and the camera are byte-identical in 9013 — but **it only ever applied to the second
category**. The one-line §8 summary flattens this into "synthesis is dead," which is not what the record
says.

### A §8 line that mis-summarizes into the wrong prohibition

> *"Real content through a synthetic frame is still synthesis — killed both the v3 bend-carry and the
> dunes label-stamp."*

The bend-carry failed because it **WARPED** real bytes — an (s,d,h) ribbon reparameterization plus
per-vert corrections, which moved CONTENT faithfully while destroying FORM (*"tons of jank still. very
spiky, faces stacked over each other, no form to it"*). A **RIGID** carry (no warping) inside a
synthesized frame is a different mechanism, and it is precisely the **Rung F** architecture that
succeeded: verbatim core + minted context. The §8 line as written forbids the one hybrid that works.

---

## Verdict of the three judges

| Lens | Position |
|---|---|
| Skeptic | stay-with-carry |
| Builder | hybrid |
| Form critic | hybrid |

**All three converge on the same prerequisite**: the kit's **read-disc / write-disc split**. Today one
`disc` int does both jobs — asset READS must stay 1/4 (`extract._worldmap_env` raises `ValueError`
otherwise), while WRITES must target the s74 sentinel 9. Sites: `island.py:404/:888/:922/:929`,
`interior.py:1022/:2442`, `terrain.py:287/292/296`, `islandbeach.py:103/104/128`, plus a hard refusal for
`src_disc == 9` in `discmirror.auto_mirror`.

**Recommended sequence** (skeptic's methodology, builder's and critic's targets):

1. **The disc split** — unanimous prerequisite, unblocks every later direction.
2. **Ship the ACCEPTED CARRY into 9013 first** — one `junction_compose` two-ground landmass (36 gates,
   159/160 byte-equal self-test). A known-good look, so any failure is *plumbing*, not art. This is
   verbatim-first, the project's own house rule, applied to a new world.
3. **Then the first genuine synthesis rung: THE TERRACE WALL.** It is the only synthesis target in the
   record that is (a) fully decoded (`README.md:138-161`, from `rock_wall_language.py`: 8945 tile groups /
   13929 neighbour pairs / 48 blocks), (b) explicitly classified as a TILE LANGUAGE rather than a mural —
   i.e. in the category that passes — and (c) never built. Its own note closes with "⇒ THE TERRACE-WALL
   RUNG IS UNBLOCKED."

**The strongest argument against**, worth keeping in view: the discriminant above ("tile language passes,
continuous-flow mural fails") is an ex-post sort over n≈7 that has never predicted anything prospectively.
THE TRANSPLANT NULL showed the project's best statistical instrument could not separate a designed emitter
from iid-random, and CALIBRATE THE INSTRUMENT records a builder, two adversarial judges and an
orchestrator all reading "stock curves, synth staircases" into a panel of *pure unmodified stock* — a
verdict that had to be retracted. So the terrace wall should be run as a **prediction-registered** test:
state the expected outcome before building, so the discriminant itself is what gets falsified.

---

## POSTSCRIPT 2026-07-30 — the test ran, and the discriminant was REFUTED

The terrace wall was built and playtested twice the same day (`TERRACE-WALL-PREDICTION.md`, scored).
Round 1 failed on implementation (solved classes re-derived); a per-instance anatomy study followed
(`rock_wall_instances.py`, three laws); round 2 implemented the measured language faithfully — gated
vertical chains, majority orientations, 12% mirrors, junction L3 tops — **and still failed on form**
("obvious tiling … back to study"). The strongest-argument-against paragraph above was right: the
tile-language/mural boundary did not survive its first prospective test. The refined lesson is the FORM
LESSON again, one level up: correct TILES on invented MASSING still fail — stock wall silhouettes are
coursed (plan jogs, ledge shelves, foot talus), and that 3D massing is the actual carrier of the look.
The recommended sequence's step 2 (the carry) passed the same day; the carry-with-minted-context frame
(Rung F) remains the only proven road. Any future synthesis rung starts from a massing/silhouette decode
and a fresh prediction registration.
