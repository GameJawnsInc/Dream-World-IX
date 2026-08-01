"""THE EIGHT-ROUND RECORD, AS DATA -- the arc's own scoring documents, tabulated.

Instrument for S0 of THE GROUND-JUNCTION SYNTHESIS (studies/path-d-new-world/
GROUND-JUNCTION-SYNTHESIS.md). Read-only: the SOURCE is the arc's registration /
scoring documents plus `git log -- studies/path-d-new-world`, not the game and not
stock terrain. Nothing here touches the install or the bench.

Every `verdict` string is VERBATIM from the scoring document that recorded it
(TERRACE-WALL / PROFILE-CARRY / STRIP-CARRY / JUNCTION-AWARE / RIM-AWARE /
MESA-CARRY / APRON-CARRY -PREDICTION.md). `gates_green` lists the gate predicates
that were reported passing in the build that shipped to that playtest, with the
numbers the document declared. `defect_on` records, per named defect, WHICH build
element it sat on and whether that element was newly authored in the iteration
being judged -- the S0(b) discriminant ("the defect follows the mint").

Emits out/round_record.json. Runtime: instant.

  py -X utf8 round_record.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"

# Element provenance vocabulary used in defect_on[].element_class:
#   carried_wall / carried_top / carried_ground  -- verbatim donor bytes
#   minted_*                                     -- authored by the builder
#   bench_*                                      -- pre-existing bench geometry we deformed
# newly_authored: was this element created or CHANGED in the iteration under judgement?

ROUNDS = [
    dict(
        n=1, key="terrace-t1-r1", date="2026-07-30",
        registration="TERRACE-WALL-PREDICTION.md",
        claim="THE DISCRIMINANT: synthesis passes when the target is an exact-linear TILE "
              "LANGUAGE, fails on continuous-flow texture organization. First prospective use.",
        prediction="PASS (owner reads it as FF9 interior rock wall in 1-2 rounds, not an "
                   "8-round fix ladder)",
        carried=[],
        minted=["the entire wall (no carry exists): courses of ~4.7u 128x128 wall quads",
                "vertical ROLE bands crest/upper/lower from the decoded tile language",
                "u-continuation by windowed atlas adjacency with 4-col band wraps",
                "lattice phase from data; topo-13 grass mid-shelf pinned y 15.7-18.3",
                "the top grass sheet (naive per-cell random quad,ori)",
                "the grass-cliff transition tiles (one exemplar's v-orientation, all instances)",
                "the foot line (lattice polyline) + the zip-tri winding"],
        gates_green=["LAW-3 chain gate: all columns are measured foot->body->crest paths",
                     "one-window uv membership per course role",
                     "role majority (foot tile base-touch / crest tile crest-touch)",
                     "watertight: zero NEW once-edges",
                     "MOAT LAW v2 (wall verts >=6u inside the bench outline)",
                     "winding (no visible tri faces inward or down)",
                     "massing: foot-line median turn / right-angle count",
                     "texel-density band; atlas-adjacency continuation rate ~46%+11%"],
        verdict="it's a mess ... the top grass is all banded, and the sides look stamped "
                "together. some of the grass-cliff transition tiles are flipped upside down. "
                "the bottom third is especially messy, even missing faces.",
        defect_on=[
            dict(defect="top grass all banded", cls="tile-pattern",
                 element="the minted top grass sheet (naive per-cell random (quad,ori))",
                 element_class="minted_top", newly_authored=True,
                 note="a SOLVED class re-derived naively; junction_compose L3 exists for it"),
            dict(defect="grass-cliff transition tiles flipped upside down",
                 cls="tile-orientation",
                 element="the minted transition tiles (one exemplar's orientation, globally)",
                 element_class="minted_wall", newly_authored=True),
            dict(defect="bottom third messy, missing faces", cls="topology",
                 element="the minted zip-tri winding on concave jag sections",
                 element_class="minted_wall", newly_authored=True,
                 note="gate gap: watertight counts once-edges, not winding; the D3 "
                      "provenance-winding gate existed in junction_compose and was not ported"),
            dict(defect="the sides look stamped together", cls="continuation-form",
                 element="the minted u-continuation itself (the discriminant's own territory)",
                 element_class="minted_wall", newly_authored=True),
            dict(defect="overworld lag", cls="unattributed",
                 element="none (owner's own read: concurrent-session CPU contention)",
                 element_class="none", newly_authored=False),
        ],
        score="FAIL, not a clean discriminant refutation (two solved classes re-derived, "
              "one gate unported). Owner: 'looks like we don't have enough study knowledge "
              "to synth yet.' Wall REVERTED.",
        fix_next="rock_wall_instances.py anatomy study -> THE THREE INSTANCE LAWS "
                 "(LAW 1 fixed v-orientation per tile, LAW 2 mirrors rare 12.5%, "
                 "LAW 3 a wall column is a CONTIGUOUS VERTICAL ATLAS STRIP); rebuild "
                 "faithfully, reuse junction L3 for tops, port the D3 winding gate.",
    ),
    dict(
        n=2, key="terrace-t1-r2", date="2026-07-30",
        registration="TERRACE-WALL-PREDICTION.md (the second and final registered round)",
        claim="same DISCRIMINANT, now with the language faithfully implemented",
        prediction="PASS (unchanged from the registration)",
        carried=[],
        minted=["everything again: every column a gated LAW-3 chain from the transition table",
                "LAW-1 majority orientations; LAW-2 mirrors at 10%",
                "junction L3 for the top; the D3 winding gate ported"],
        gates_green=["all round-1 gates", "the ported winding gate (caught a five-tri fold "
                     "OFFLINE -- the suite's one pre-deploy catch of a form defect)",
                     "the frozen offline eye read it as coherent next to a stock control"],
        verdict="sharp edges at the bottom, obvious tiling, mismatched/rotated grass-cliff "
                "transition tiles, banded grass on top, middle section has grass-cliff "
                "tiling -- back to study probably.",
        defect_on=[
            dict(defect="sharp edges at the bottom", cls="silhouette-massing",
                 element="the minted lattice-polyline foot on smooth minted ground",
                 element_class="minted_foot", newly_authored=True),
            dict(defect="obvious tiling", cls="tile-pattern",
                 element="the minted LAW-3 column chains", element_class="minted_wall",
                 newly_authored=True),
            dict(defect="mismatched/rotated grass-cliff transition tiles",
                 cls="tile-orientation",
                 element="the minted transition tiles under LAW-1 per-tile MAJORITY "
                         "orientation (insufficient at course boundaries)",
                 element_class="minted_wall", newly_authored=True),
            dict(defect="banded grass on top", cls="tile-pattern",
                 element="the minted junction-L3 top sheet", element_class="minted_top",
                 newly_authored=True,
                 note="root-caused two rounds later: mains_uv needs floor(z/4) cell keys; "
                      "the negated key collapses u. Fixed in round 4, never recurred."),
            dict(defect="middle section has grass-cliff tiling",
                 cls="texture-geometry-mismatch",
                 element="ledge-vegetation tiles (rows 8/9) on a minted UNLEDGED surface",
                 element_class="minted_wall", newly_authored=True),
        ],
        score="FAIL on form with the language faithfully implemented => THE TILE-LANGUAGE "
              "DISCRIMINANT IS REFUTED. Lesson banked: 'the missing knowledge is 3D MASSING, "
              "not texture statistics'; 'a dead-flat shelf bands even under lawful mains'.",
        fix_next="rock_wall_massing.py (the coursed-silhouette decode) -> PROFILE CARRY.",
    ),
    dict(
        n=3, key="profile-carry", date="2026-07-30",
        registration="PROFILE-CARRY-PREDICTION.md",
        claim="Rung F applied to walls: the look survives when the CARRIERS are verbatim and "
              "only the SEAT is minted (carriers = per-column silhouette wobble + tiles).",
        prediction="PASS in this single round (basis: every prior Rung-F-shaped carry passed "
                   "in game)",
        carried=["a contiguous run of REAL wall columns' silhouette profiles from ONE stock "
                 "component, in stock order (neighbour wobble correlation preserved)",
                 "AMENDED pre-deploy: k = 1.0 for the whole run, ONE rigid pose, crest-anchored "
                 "in the shelf band, surplus height BURIED below the bench floor"],
        minted=["the plan: blob seat, crest ring, station bearings, junction-L3 top",
                "THE GRASS APRON joining the carried foot line to the bench lowland (new)",
                "all tiles, by the three instance laws (unchanged from round 2)"],
        gates_green=["round-2 battery", "the amendment's donor window bar (every column at "
                     "least shelf-minus-lowland tall)", "offline eye"],
        verdict="the overall shape and coherence is better -- still have flipped grass-cliff "
                "tiles, grass-cliff tiles in the middle, noticeably hard tiling (could match "
                "stock i suppose), and now warped/stretched grass at the base.",
        defect_on=[
            dict(defect="warped/stretched grass at the base", cls="uv-stretch",
                 element="THE MINTED GRASS APRON (this round's one new element) -- the "
                         "un-clipped apron cell trade",
                 element_class="minted_ground", newly_authored=True,
                 note="the owner's word 'now' marks it as new. The registration had ACCEPTED "
                      "this trade pre-deploy; the doc's scoring: 'The apron clamp cost was "
                      "real ... NOT acceptable in game.'"),
            dict(defect="flipped grass-cliff tiles", cls="tile-orientation",
                 element="minted tiles under LAW-1 majority (carried over from round 2)",
                 element_class="minted_wall", newly_authored=False),
            dict(defect="grass-cliff tiles in the middle", cls="texture-geometry-mismatch",
                 element="carried ledges FLATTENED by the 3-depth course resampling while "
                         "the minted tiles still advertise them",
                 element_class="minted_wall", newly_authored=True,
                 note="named the finer carrier: fringe tiles correlate with LOCAL LEDGE "
                      "GEOMETRY -> whole-mesh carry"),
            dict(defect="noticeably hard tiling (could match stock i suppose)",
                 cls="tile-pattern", element="minted tile chains",
                 element_class="minted_wall", newly_authored=False,
                 note="borderline per the owner; not load-bearing either way"),
        ],
        score="FAIL on form, with the SHAPE VERDICT IMPROVED -- the first positive form "
              "verdict any synthetic wall received. The massing carry WORKED.",
        fix_next="WHOLE-MESH STRIP CARRY (verts+uvs+tangents); the apron mechanism is "
                 "DELETED, not repaired.",
    ),
    dict(
        n=4, key="strip-carry", date="2026-07-31",
        registration="STRIP-CARRY-PREDICTION.md",
        claim="Rung F at full depth: the look survives when the carried unit is the WHOLE "
              "MESH and the mint is only the recomposition.",
        prediction="PASS in this single round (every carrier the four failed rounds localized "
                   "is now verbatim)",
        carried=["FOUR tier-gated level-chain whole-mesh wall strips (topo-49 tris, every "
                 "vertex/uv/tangent verbatim) from blk [17,12] / [22,14] / [13,16] / [18,9]",
                 "one rigid pose each (translation + yaw), k = 1.0, no per-vertex deformation",
                 "EMBEDDED POCKETS (the donor's ledge vegetation as part of the face sheet)"],
        minted=["FOUR seam MORTAR COLUMNS (amendment 2: one column of quads per seam, the "
                "outgoing tile continued and LAW-2-mirrored)",
                "the plateau-interior L3 top at the carried crest + crest caps + crest ring",
                "a HOLE in the flat bench grass; the wall meets ground by BURIAL PIERCE",
                "bounded component cappers for exact-partition slivers",
                "NO apron (round 3's mechanism deleted)"],
        gates_green=["watertight: ZERO undeclared once-edges (declared classes: hole-rim, "
                     "buried, mortar-zone)",
                     "h_pairs seam legality: all four seams lawful, zero tile shifts needed",
                     "closure solve gap 1.8u -> 0.2u; kinks 24.6/25/25/11.8 deg",
                     "winding per carried normals; massing; reach (bench re-minted r=47)",
                     "the L3 negated-cell-key bug fixed: top L3 seeds from 167 bench cells "
                     "(previously 0)"],
        playtests=[
            dict(i=1, verdict="(five defect classes, each root-caused and fixed in-round) "
                              "stretched crest faces, cull-flickering spikes, ground holes, "
                              "orange base spikes, gutter-white tris",
                 fixes="crest-weld uv lerp, double-sided caps, per-class cap attribute "
                       "sources, mortar u-clamp + course-v"),
            dict(i=2, verdict="the top is the issue ... might be time for more studying, "
                              "we've been spinning on this synth.",
                 detail="floaty grass bits at the crest, missing faces + dirt at the base, "
                        "blurred mortar columns, ~1px white dots along the cliff"),
        ],
        verdict="the top is the issue ... might be time for more studying, we've been "
                "spinning on this synth.",
        defect_on=[
            dict(defect="blurred mortar columns", cls="seam + uv-stretch",
                 element="THE MINTED MORTAR COLUMNS (this round's new seam mechanism)",
                 element_class="minted_seam", newly_authored=True),
            dict(defect="floaty grass bits at the crest", cls="floating-geometry",
                 element="the carried crest-cap rows welded to a MINTED simplified crest "
                         "polyline instead of to the donor plateau behind them",
                 element_class="minted_crest", newly_authored=True),
            dict(defect="missing faces + dirt at the base", cls="topology",
                 element="THE MINTED BURIAL-PIERCE ground rim + caps",
                 element_class="minted_foot", newly_authored=True),
            dict(defect="~1px white dots along the cliff", cls="seam",
                 element="minted junction texture bleed at the sliver caps",
                 element_class="minted_seam", newly_authored=True),
            dict(defect="stretched crest faces / cull spikes / ground holes / orange base "
                        "spikes / gutter-white tris (playtest 1)", cls="topology + uv-stretch",
                 element="all five on minted junctions (crest weld, caps, pierce rim, mortar)",
                 element_class="minted_seam", newly_authored=True),
        ],
        score="PLUMBING STOP, claim UNJUDGED. THE KEY DATUM: 'the carried faces themselves "
              "drew ZERO complaints -- no banding, no tiling, no flipped tiles, no stretching "
              "on any carried rock surface, across both playtests. Every named defect lives "
              "on a MINTED JUNCTION.' Also finding 3: 'The offline gate suite cannot see what "
              "the game sees (winding/cull, mip-blur, bleed): gates were green while the game "
              "showed holes. A future round needs a game-eye instrument, not more once-edge "
              "audits.'",
        fix_next="JUNCTION GRAMMAR study (crest / corner / foot) -> junction-aware round.",
    ),
    dict(
        n=5, key="junction-aware", date="2026-07-31",
        registration="JUNCTION-AWARE-PREDICTION.md",
        claim="whole-mesh strips recomposed read as FF9 WHEN THE JOINS FOLLOW STOCK'S OWN "
              "junction grammar (J1 crest law / J2 corner law / J3 foot law).",
        prediction="PASS (the carried surfaces already survived two playtests without a "
                   "single complaint; every round-5 defect maps to a join now rebuilt to law)",
        carried=["the same four strips, same rigid poses (unchanged)"],
        minted=["SEAMS rebuilt: mortar columns DELETED; two full-tile stations creased at ONE "
                "shared edge; top-aligned height matching + least-squares centering + a taper "
                "that WIDENS instead of shearing (shear ratio <= 1.5, 12u displacement cap)",
                "TOP rebuilt: minted level sheet welded EDGE-FOR-EDGE to the strips' actual "
                "top once-edge path (crest polyline / notch stitch / caps / capper deleted)",
                "FOOT rebuilt: burial pierce DELETED; strips cut LEVEL at y = 3.2, the ground "
                "partition's hole rim IS the foot polyline, shared vertex for shared vertex",
                "in-round: the notch bridge + unwalkable chute; the row-10 foot fringe "
                "(the DECLARED DEFERRED texture lever, fired by playtest 1)"],
        gates_green=["watertight recalibrated to stock's own measured standard: residue <= 24 "
                     "once-edges, none > 5u, none visible in six culled renders (deployed at "
                     "8, then 4)",
                     "h_pairs at every seam; shear ratio <= 1.5; 12u displacement hard cap",
                     "massing; reach; per-carried-normal winding",
                     "THE GAME-EYE PASS (NEW -- backface-CULLED renders from low game-like "
                     "camera angles reviewed before deploy; closes round 4's finding 3)"],
        playtests=[
            dict(i=1, verdict="top is mostly walkable, shape is better, still have some seam "
                              "failures and pokey grass",
                 detail="(402,-494) open gap + a super steep WALKABLE triangle -- THE BRIDGED "
                        "NOTCH; (425,-518) a triangle jutting over the cliff + ~white pixels "
                        "along the cliff-grass seam + slightly stretched cliff; (442,-512) the "
                        "cliff foot lacks the grass transition band + stretched faces"),
            dict(i=2, verdict="the bottom is a darker shade of cliff than the middle or top. "
                              "still seeing issues on top with making a coherent seam around "
                              "the plateau... the shape is still jagged and there's still "
                              "floating/jutting triangles... need to think harder about how a "
                              "rim can be formed... we've been through a couple rounds -- "
                              "should we stop and do more studying?"),
        ],
        verdict="the bottom is a darker shade of cliff than the middle or top. still seeing "
                "issues on top with making a coherent seam around the plateau... the shape is "
                "still jagged and there's still floating/jutting triangles... need to think "
                "harder about how a rim can be formed... we've been through a couple rounds "
                "-- should we stop and do more studying?",
        defect_on=[
            dict(defect="incoherent seam around the plateau / jagged shape / "
                        "floating-jutting triangles", cls="silhouette-form + floating-geometry",
                 element="THE MINTED CREST RIM -- a 4u lattice CLIPPED against the crest "
                         "polyline (arbitrary slivers, incoherent edge flow by construction)",
                 element_class="minted_crest", newly_authored=True,
                 note="'FAILED ON FORM, isolated to ONE junction: THE CREST RIM ... through "
                      "five sub-iterations of weld machinery'"),
            dict(defect="the bottom is a darker shade of cliff", cls="shade-luminance",
                 element="THE ROW-10 FRINGE RE-MINT fired mid-round (100% share, 4.6u course, "
                         "v phase [10 -> 11])",
                 element_class="minted_foot_texture", newly_authored=True,
                 note="'its SHADE is wrong, a mint-value bug, not a law failure'"),
            dict(defect="slightly stretched cliff (playtest 1)", cls="uv-stretch",
                 element="the widened seam taper's visible cost",
                 element_class="minted_seam", newly_authored=True,
                 note="'recorded for the scoring' -- an ACCEPTED cost declared pre-deploy "
                      "that the eye then named"),
            dict(defect="open gap + walkable chute at (402,-494) (playtest 1)", cls="topology",
                 element="two residual once-edges at x=404 (inside the 24-edge gate) + the "
                         "notch fan carrying the walkable shelf topograph",
                 element_class="minted_crest", newly_authored=True,
                 note="the residue was GATE-GREEN and visible"),
            dict(defect="cliff foot lacks the grass transition band (playtest 1)",
                 cls="missing-transition",
                 element="the newly minted LEVEL-CUT foot (the deferred texture half)",
                 element_class="minted_foot", newly_authored=True),
        ],
        score="PARTIAL. PASSED SILENTLY: the carried faces, the crease SEAMS (round 4's "
              "mortar-blur class gone), the FOOT WELD. FAILED ON FORM isolated to ONE "
              "junction: THE CREST RIM -- the partial clause landing one junction over from "
              "where it was written.",
        fix_next="RIM GRAMMAR study -> THE DISPLACED-ROW LAW + numeric silhouette targets; "
                 "rim-aware round.",
    ),
    dict(
        n=6, key="rim-aware", date="2026-07-31",
        registration="RIM-AWARE-PREDICTION.md",
        claim="the strip-carry claim, third and final presentation -- joins follow stock's "
              "junction grammar INCLUDING the rim's displaced-row construction.",
        prediction="PASS (every complaint class across both prior rounds now has a measured "
                   "law behind it)",
        carried=["the four strips + the crease seam welds + the level foot weld + the notch "
                 "bridge (all in-game proven, unchanged)"],
        minted=["the RIM rebuilt to THE DISPLACED-ROW LAW: the plateau top is the INTACT 4u "
                "lattice, the lattice-clip DELETED; the strips' own top verts BECOME the rim "
                "row (THE LATTICE-HOME POSE: 90-deg yaw steps + 4u translation steps)",
                "converged to the DELAUNAY FORM of the displaced row + a SLOT CAP + INTERIOR "
                "RELAXATION (<= 1.2u) after 14 offline iterations / 5 failed mechanisms",
                "CREST SILHOUETTE REPAIR: 4 debris verts merged into the wall (<= 3.5u)",
                "the foot band re-lever: INTERMITTENT row-10 (54% share, 3.7u course, "
                "v phase [10.12 -> 11.09], run/gap lengths sampled from stock's measured "
                "distribution)"],
        gates_green=["closure gap 0.35u; seam turns 68-86 deg",
                     "weld displacements <= 10.94u (cap 12); shear ratio <= 1.5",
                     "rim displacement med 0.92 / p99 2.39 / max 2.40 (stock 0.80 / 2.41)",
                     "home jumps 0; TOP-SHEET PURITY: zero clip-minted tris",
                     "sliver gate: 1 sliver on 79 top tris = 1.2% compound (stock ring-1 2.1%)",
                     "watertight residue 1 once-edge of 8483 = 0.012% (round 5 deployed with 4)",
                     "foot fringe 54% share (stock 53%)",
                     "the culled game-eye renders reviewed; the NE anomaly explained as an "
                     "eye-at-infinity artifact and declared falsifiable"],
        verdict="(428,-507) the cliff is weirdly sliced, causing a stretched face along the "
                "cliff. || (396,-504) weird extra triangle part... an extra triangular grass "
                "piece.",
        defect_on=[
            dict(defect="the cliff is weirdly sliced, causing a stretched face",
                 cls="uv-stretch",
                 element="SEAM 0's weld taper -- this build's LARGEST weld displacement, "
                         "10.94u, INSIDE the 12u gate, sheared across one station",
                 element_class="minted_seam", newly_authored=False,
                 note="NOT this round's newest mint. The seam mechanism is round 5's; the "
                      "4u-quantized lattice-home pose made its residual WORSE. The doc: "
                      "'the crease-weld's standing cost ... The gate bounded it; the eye "
                      "still reads it.'"),
            dict(defect="weird extra triangle part / an extra triangular grass piece",
                 cls="off-language-endpoint",
                 element="THE WEST FINGER -- a donor crest promontory sliced by the CUT "
                         "WINDOW into a 2-3u corridor the donor never shipped alone",
                 element_class="minted_endpoint", newly_authored=False,
                 note="'An ENDPOINT stock never has, minted by the cut.' The cut windows "
                      "date from round 4. THE TAPER LAW later measured 42/42 real endpoints "
                      "taper, 0 continue -- an object with ZERO stock instances that passed "
                      "every gate."),
            dict(defect="(the newest mint -- the displaced-row rim -- PASSED)", cls="none",
                 element="the Delaunay displaced-row top + crest silhouette repair",
                 element_class="minted_crest", newly_authored=True,
                 note="'neither the dark foot band nor crest jaggedness recurred'; 'No "
                      "watertight class was named ... the audits' first fully clean round "
                      "in-game'"),
        ],
        score="FAIL on form; THE MINTED-PLAN WALL LANE CLOSES (the declared last minted-rim "
              "presentation). Both named defects are FORM defects of THE COMPOSITION ITSELF. "
              "Owner's frame: 'some parts don't lift from base to rim cleanly. we may need "
              "more research on how to build connective walls that have logical endpoints "
              "instead of trying to build the top to fit. both sides have a responsibility.'",
        fix_next="ENDPOINT GRAMMAR study -> THE TAPER LAW (42/42) + the (15,14) mesa as the "
                 "whole-feature carry candidate.",
    ),
    dict(
        n=7, key="whole-mesa-carry", date="2026-07-31",
        registration="MESA-CARRY-PREDICTION.md",
        claim="a COMPLETE stock feature carried whole reads as FF9. No composition, no cut "
              "endpoints, no minted top; the only minted junction is the foot.",
        prediction="PASS (every surface the eye sees is stock's own, arranged as stock "
                   "arranged it)",
        carried=["the blk (15,14) MESA ENTIRE, verbatim bytes: 325 wall tris + 20 ring-1 "
                 "plateau tris + the enclosed plateau (369 carried tris), crest y ~26.3 "
                 "wander +/-0.9u, tapered skirt, all uvs / normals / tangents / topograph",
                 "pose = the lattice-group pose (90-deg yaw steps, 4u micro-shift)"],
        minted=["ONLY the foot weld: BURY seat (dy -4.35), level cut at y = 3.2, "
                "chord-simplified foot polyline as the ground partition rim, shared-vertex "
                "rim weld, kept-grass conformance, micro-weld, one T-sweep pass",
                "playtest-1 lever: the row-10 foot fringe RE-MINTED on the cut bottom course "
                "(57% share, phase-tuned, arclength-marched u stations, height-mapped v)"],
        gates_green=["watertight 4 residual once-edges of 11991 = 0.033%",
                     "winding per carried normals; massing; reach; census MISS=0",
                     "CARRY PURITY: every tri above the cut is donor bytes under one rigid "
                     "pose; no per-vert deformation anywhere",
                     "no seam / rim / fringe gates exist -- nothing they gate is built"],
        playtests=[
            dict(i=1, verdict="the top looks great, we still lack the grass<->cliff "
                              "transition at the bottom and there are a couple stretched "
                              "faces near the base (one visible in the screenshot)."),
            dict(i=2, verdict="nope, mismatched faces. thinking we're going to have to do "
                              "another study on the bases. we've handled aligning the cliff "
                              "faces from the ground to the plateau in terms of form, but we "
                              "might be doing slightly wrong with how the base game handles "
                              "the transitional tiles at the bottom that differ from the top."),
        ],
        verdict="nope, mismatched faces. thinking we're going to have to do another study on "
                "the bases. we've handled aligning the cliff faces from the ground to the "
                "plateau in terms of form, but we might be doing slightly wrong with how the "
                "base game handles the transitional tiles at the bottom that differ from the "
                "top.",
        defect_on=[
            dict(defect="the top looks great (playtest 1)", cls="none",
                 element="THE CARRIED TOP -- the junction three composition rounds could not "
                         "buy", element_class="carried_top", newly_authored=True,
                 note="FIRST wall-top form PASS in the arc"),
            dict(defect="we still lack the grass<->cliff transition at the bottom",
                 cls="missing-transition",
                 element="THE MINTED BURY SEAT's level cut -- it cut away the donor's own "
                         "row-10 transition band",
                 element_class="minted_foot", newly_authored=True,
                 note="a mint by OMISSION: the defect is what the newest mint REMOVED"),
            dict(defect="a couple stretched faces near the base", cls="uv-stretch",
                 element="the level cut sampling MID-TEXTURE on the donor's bottom course",
                 element_class="minted_foot", newly_authored=True),
            dict(defect="nope, mismatched faces (playtest 2)", cls="tile-placement",
                 element="THE FRINGE RE-MINT (arclength-marched u stations) -- 'retiled tris "
                         "sit beside carried tris with no tile continuity, plus green-smeared "
                         "tris at the cut'",
                 element_class="minted_foot_texture", newly_authored=True,
                 note="statistically stock (row/share/phase all measured) but PLACEMENT-wrong"),
        ],
        score="THE TOP AND THE FORM PASS (standing result); the base texture lever FAILS as "
              "MISMATCHED FACES. Bench state: the fringed mesa LEFT LIVE.",
        fix_next="BASE-TILE GRAMMAR study -> THE BAND-CONTINUATION LAW (the band is the "
                 "column's own uv continuation: 100.0% u- AND v-continuous with the course "
                 "above across 1090 seam verts; seam v = 10.16 both sides; zero freedom). "
                 "The law CLOSES the texture-only lane by derivation -> APRON CARRY.",
    ),
    dict(
        n=8, key="apron-carry", date="2026-07-31", live=True,
        registration="APRON-CARRY-PREDICTION.md",
        claim="carrying BOTH SIDES of stock's own transition reads as FF9 -- the mesa at "
              "donor stature, its own row-10 foot band intact, and its own GROUND APRON "
              "carried with it; the only minted junction moves OUTWARD to a grass-to-grass "
              "weld at the apron's edge.",
        prediction="PASS (every surface in the transition is stock's own; the one minted seam "
                   "is grass-to-grass at matched height)",
        carried=["the mesa unchanged in plan, RE-SEATED at donor stature (seat dy -0.14 vs "
                 "the bury's -4.35); crest ~26.2 bench, top 28.1",
                 "the donor's own foot band course (near-solid row 10/11; band share 100% at "
                 "the weld)",
                 "168 donor GROUND APRON tris -- donor grass flooded outward from the weld "
                 "line, 6u then 10u collar, clipped to the bench's own grass coverage",
                 "the 4-tri (14,14) wall continuation + its 24 apron tris across the border"],
        minted=["ONLY the outer grass-to-grass weld: bench grass partition + shared-vertex "
                "rim weld",
                "a per-vertex bench LIFT: 275 bench verts lifted, max 4.01u, over a 12u "
                "(then 24u) smoothstep falloff -- to raise bench grass to the donor's NON-LEVEL "
                "weld line (y 3.0 .. 7.4, 4.4u of relief)",
                "iteration 1: the apron GROUND uv retiled to the DESTINATION's L3 field",
                "iteration 2: donor uv RESTORED; the dirt band re-rowed keep-u/swap-the-row; "
                "a BORDER STITCH + HOLE CAPPER + RESIDUE STITCH; ONE SMOOTH GROUND-NORMAL "
                "FIELD over apron + fragments + lifted bench; BLEND_R 12 -> 24"],
        gates_green=["watertight 19 once-edges of 5168 = 0.37% (bound 24, none > 5u); "
                     "iteration 1 unchanged at 19/5168; iteration 2 down to 5 of 7404 = 0.07%",
                     "THE BAND GATE (new): foot-course rows 10+11 share 100% >= 80%",
                     "CARRY PURITY extended: no wall uv and no apron uv modified anywhere "
                     "(byte-hash before/after)",
                     "winding per carried normals; census MISS=0",
                     "massing and reach declared REPORT-ONLY this round (weld-line med turn "
                     "19.3 deg, zero right angles; fit enforced structurally by the grass clip)",
                     "a declared once-edge class for stock's own carried cracks (0 hits)"],
        playtests=[
            dict(i=1, verdict="weird brown tiles and some seams. the connection is nice though."),
            dict(i=2, verdict="seam + stretched grass (west 384,-511) || cliff base colliding "
                              "with raised-grass cliff, covering the base (SE 444,-519) || "
                              "seam + stretched grass on the other side of that hill "
                              "(north 419,-490)"),
            dict(i=3, verdict="now we're back to weird meadowy corner tiles and we've got more "
                              "seams, and the hill still isn't fixed (plus it's seaming)."),
        ],
        verdict="now we're back to weird meadowy corner tiles and we've got more seams, and "
                "the hill still isn't fixed (plus it's seaming).",
        defect_on=[
            dict(defect="the connection is nice though (playtest 1)", cls="none",
                 element="THE GROUND-WELD LINE + the donor's own foot band -- the round's "
                         "claim, confirmed",
                 element_class="carried_wall", newly_authored=True),
            dict(defect="weird brown tiles (playtest 1)", cls="tile-family",
                 element="THE NEWLY CARRIED APRON's own HOME tiles -- 20 tris of the donor "
                         "meadow's dirt/talus band, atlas col 5 rows 8-11",
                 element_class="carried_ground", newly_authored=True,
                 note="the ONE case where the defect sits on a newly CARRIED element rather "
                      "than a minted one: stock bytes read wrong in a foreign context"),
            dict(defect="some seams (playtest 1)", cls="seam",
                 element="the carried apron's donor tile PHASES, which 'cannot pattern-match "
                         "the bench's positional L3 field at the rim' -- i.e. THE MINTED OUTER "
                         "RIM", element_class="minted_ground", newly_authored=True),
            dict(defect="stretched grass (playtest 2)", cls="uv-stretch",
                 element="ITERATION 1's L3 RETILE -- plan-projected, while stock grass uv "
                         "tracks SURFACE distance: ~20-40% stretch on the steep collar",
                 element_class="minted_ground", newly_authored=True),
            dict(defect="cliff base colliding with raised-grass cliff, covering the base "
                        "(playtest 2)", cls="silhouette-slope",
                 element="THE MINTED BENCH LIFT -- a 4u rise over a 12u falloff = a 25-35 deg "
                         "grass ramp", element_class="minted_ground", newly_authored=True),
            dict(defect="seam (playtest 2)", cls="seam",
                 element="GEOMETRY, not texture (they survived BOTH uv schemes): the donor "
                         "blocks' own cross-border hairline at posed x=384 (0.03u y-mismatch) "
                         "+ a TRIANGULAR HOLE at (420,-490) from a donor step face the apron "
                         "flood's class filter excluded",
                 element_class="minted_ground", newly_authored=True),
            dict(defect="weird meadowy corner tiles (playtest 3)", cls="tile-family",
                 element="ITERATION 2's RESTORED DONOR UV + the dirt band re-rowed "
                         "keep-u/swap-the-row (row parity folding 8-11 into 24-25)",
                 element_class="carried_ground", newly_authored=True,
                 note="'back to' -- the owner reads it as the return of playtest 1's class "
                      "under the reversed uv scheme"),
            dict(defect="more seams (playtest 3)", cls="seam",
                 element="ITERATION 2's three stitch passes + the new SMOOTH GROUND-NORMAL "
                         "FIELD (the lighting half) -- the seam COUNT rose while the "
                         "watertight residue FELL 19 -> 5",
                 element_class="minted_ground", newly_authored=True,
                 note="unattributable: six changes shipped in one bundle"),
            dict(defect="the hill still isn't fixed (plus it's seaming)", cls="silhouette-slope",
                 element="ITERATION 2's WIDENED LIFT (BLEND_R 24, ramp <= ~14 deg, "
                         "stock-walkable) -- still a discrete mound, and now its own boundary "
                         "is a seam", element_class="minted_ground", newly_authored=True),
        ],
        score="OPEN. The lane returns to study (THE GROUND-JUNCTION SYNTHESIS). Watertight "
              "residue fell 19 -> 5 while the owner's complaint count held at 3 and gained a "
              "compound clause.",
        fix_next="(none built) -- S1-S6 registered instead.",
    ),
]

# ---------------------------------------------------------------------------------------
# derived tallies
# ---------------------------------------------------------------------------------------

# The fine labels above are per-mechanism. The EYE names coarser families; this is the
# merge used for the recurrence claim, declared explicitly so the grouping is auditable.
MERGE = {
    "tile-pattern": "A_TILE_PATTERN_OR_FAMILY",
    "tile-family": "A_TILE_PATTERN_OR_FAMILY",
    "tile-placement": "A_TILE_PATTERN_OR_FAMILY",
    "uv-stretch": "B_UV_STRETCH",
    "seam": "C_SEAM_A_VISIBLE_LINE",
    "continuation-form": "C_SEAM_A_VISIBLE_LINE",
    "topology": "D_HOLES_AND_FLOATERS",
    "floating-geometry": "D_HOLES_AND_FLOATERS",
    "silhouette-massing": "E_SILHOUETTE_FORM_SLOPE",
    "silhouette-form": "E_SILHOUETTE_FORM_SLOPE",
    "silhouette-slope": "E_SILHOUETTE_FORM_SLOPE",
    "off-language-endpoint": "E_SILHOUETTE_FORM_SLOPE",
    "tile-orientation": "F_TILE_ADVERTISES_WRONG_GEOMETRY",
    "texture-geometry-mismatch": "F_TILE_ADVERTISES_WRONG_GEOMETRY",
    "missing-transition": "G_MISSING_TRANSITION",
    "shade-luminance": "H_SHADE",
    "unattributed": "Z_UNATTRIBUTED",
}


def main() -> int:
    pt_total = sum(len(r.get("playtests", [{}])) or 1 for r in ROUNDS)
    cls_rounds = defaultdict(set)
    cls_mechanisms = defaultdict(list)
    on_new, on_old, passes = [], [], []
    for r in ROUNDS:
        for d in r["defect_on"]:
            if d["cls"] == "none":
                passes.append((r["n"], d["element"]))
                continue
            for c in d["cls"].split(" + "):
                cls_rounds[c].add(r["n"])
                cls_mechanisms[c].append(dict(round=r["n"], element=d["element"],
                                              defect=d["defect"]))
            (on_new if d["newly_authored"] else on_old).append(
                dict(round=r["n"], defect=d["defect"], element=d["element"]))

    recurring = {c: dict(rounds=sorted(rs), n_rounds=len(rs),
                         n_distinct_mechanisms=len(cls_mechanisms[c]),
                         mechanisms=cls_mechanisms[c])
                 for c, rs in sorted(cls_rounds.items(), key=lambda kv: -len(kv[1]))}

    elem_cls = Counter(d["element_class"] for r in ROUNDS for d in r["defect_on"]
                       if d["cls"] != "none")

    fam_rounds = defaultdict(set)
    fam_mech = defaultdict(list)
    for c, v in recurring.items():
        f = MERGE[c]
        fam_rounds[f].update(v["rounds"])
        fam_mech[f].extend(v["mechanisms"])
    families = {f: dict(rounds=sorted(rs), n_rounds=len(rs),
                        n_distinct_mechanisms=len(fam_mech[f]),
                        fine_labels=sorted({c for c in MERGE if MERGE[c] == f
                                            and c in recurring}),
                        mechanisms=fam_mech[f])
                for f, rs in sorted(fam_rounds.items(), key=lambda kv: -len(kv[1]))}

    doc = dict(
        title="THE EIGHT-ROUND RECORD, AS DATA",
        source="the arc's own registration/scoring documents + git log -- studies/path-d-new-world",
        instrument_limits=[
            "DOCUMENTARY. Every number and every quote is copied from a scoring document; "
            "nothing here was re-measured against stock terrain or the game.",
            "The verdicts are the documents' transcription of the owner's words. Where a "
            "document paraphrased (e.g. round 4 playtest 1's five classes) the paraphrase is "
            "marked as such, not quoted as verbatim.",
            "'gates_green' is what each document REPORTED at deploy. No gate was re-run.",
            "S0 counts 'eight rounds' and lists eight defects; those are two different eights "
            "(see counting_note). Round-level and playtest-level tallies are both given.",
        ],
        counting_note=(
            "8 REGISTERED BUILD ROUNDS, 13 SCORED PLAYTEST VERDICTS. S0's eight-defect chain "
            "(strip seams -> crest rim -> sliced/stretched faces -> missing base band -> "
            "mismatched base faces -> brown tiles + rim seams -> stretched grass + "
            "raised-grass cliff -> meadowy tiles + more seams + the hill) is the last EIGHT "
            "PLAYTEST verdicts, spanning rounds 4-8; it omits the first five verdicts "
            "(rounds 1, 2, 3 and the first playtests of rounds 4 and 5)."
        ),
        n_rounds=len(ROUNDS), n_playtest_verdicts=pt_total,
        rounds=ROUNDS,
        recurring_classes=recurring,
        recurring_families=families,
        defect_element_provenance=dict(elem_cls),
        gate_state_at_every_verdict=dict(
            n_verdicts=pt_total, n_arrived_on_a_GATE_GREEN_build=pt_total,
            n_predicted_by_a_gate=0,
            what_the_gates_DID_catch_pre_deploy=[
                "round 2: the ported D3 winding gate caught a five-tri fold OFFLINE",
                "round 4: the composition search caught an INSTRUMENT fault (nearest-neighbour "
                "chains stitching wall runs from different tiers, 15.8u crest spread)",
                "round 6: 14 offline iterations / 5 successive top-sheet mechanisms, each "
                "caught by the gates + the offline eye (thin wedges, corridors, slots, slivers)",
                "round 8: run 1's 262-edge residue (collar overlapping the coast) and the "
                "per-point blend field cracking every kept/cut boundary",
            ],
            the_three_near_predictions=[
                "round 2's deploy commit (9f6f8c0c): 'Remaining taste-level blemishes (a pale "
                "body band on one face, one mirror-butterfly where a tile abuts its own "
                "mirrored instance -- u DIRECTION is not recoverable from exemplars) are "
                "deliberately LEFT for the owner's judgment.' The owner's verdict then named "
                "'mismatched/rotated grass-cliff transition tiles'. The offline eye SAW the "
                "class and chose not to block on it.",
                "round 3 registration ACCEPTED the un-clipped apron trade pre-deploy; the "
                "owner then named exactly it ('warped/stretched grass at the base'). The doc: "
                "'The apron clamp cost was real ... NOT acceptable in game.'",
                "round 5 playtest 1 recorded 'stretched cliff is the widened taper's visible "
                "cost -- recorded for the scoring'; round 6 shipped with the taper inside its "
                "gate and the owner named the stretch as one of only two defects.",
                "=> TWICE the arc's own PROSE predicted the next named defect while its "
                "NUMERIC gates rated the same build green.",
            ],
        ),
        defect_follows_mint=dict(
            on_newly_authored=len(on_new), on_older_element=len(on_old),
            newly_authored_elements_that_PASSED=passes,
            exceptions=on_old,
        ),
        gate_axes_implemented=[
            "TOPOLOGY: once-edge residue budget (<=24, none >5u), declared classes, "
            "degenerate exemption, census MISS=0",
            "MAGNITUDE BOUNDS on minted displacement: weld <=12u, shear ratio <=1.5, closure "
            "gap <=2.5u, rim displacement p50<=1.2 / p99<=2.5, home jumps=0",
            "FACE ORIENTATION: winding vs carried normals; no down-facing top tri",
            "ATLAS MEMBERSHIP + PAIR LEGALITY: one-window uv, role majority, h_pairs/v_pairs",
            "SCALAR SHARES matched to a stock marginal: fringe share 45-60%, band share >=80%, "
            "sliver fraction <=3%, massing turn median / right-angle count",
            "FIT: reach vs bench radius, MOAT LAW v2",
            "EYE: face renders, then (round 5+) six backface-CULLED game-eye renders reviewed "
            "by an agent",
        ],
        gate_axes_absent=[
            "uv RATE (texels per world unit, and per SURFACE vs per PLAN unit) -- the entire "
            "STRETCH class. Round 6 is the proof: 10.94u weld displacement INSIDE a 12u cap, "
            "and the owner named the stretch it produced.",
            "CROSS-BOUNDARY FIELD CONTINUITY -- tile phase/family, vertex normal, luminance. "
            "Every predicate is per-element or aggregate; none is a two-sided difference "
            "across a minted boundary, which is what a seam IS.",
            "REGIONAL GROUND PROFILE -- BLEND_R was chosen by local SLOPE ANGLE (<=14 deg, "
            "stock-walkable); 'the hill' is a complaint about a 24u-radius mound's extent, a "
            "different derivative.",
            "CONFIGURATION LEGALITY -- every gate asks 'is this value inside stock's "
            "distribution for this element?', never 'does stock ever put this element HERE?'. "
            "The West Finger passed every gate and has ZERO stock instances (THE TAPER LAW, "
            "42/42).",
            "SHADE / LUMINANCE -- measured in the rim study (row 10 luminance 67-73 vs "
            "mid-face 112-165) but never made a gate predicate.",
        ],
    )
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "round_record.json"
    p.write_text(json.dumps(doc, indent=1, ensure_ascii=True), encoding="utf-8")
    print(f"wrote {p}")
    print(f"rounds={len(ROUNDS)}  playtest verdicts={pt_total}")
    print(f"defects on a NEWLY AUTHORED element: {len(on_new)}")
    print(f"defects on an OLDER element:         {len(on_old)}")
    for d in on_old:
        print(f"   exception: round {d['round']}: {d['defect'][:60]}")
    print("newly authored elements that PASSED:")
    for n, e in passes:
        print(f"   round {n}: {e[:70]}")
    print("recurring FAMILIES (rounds / distinct mechanisms):")
    for f, v in families.items():
        print(f"   {f:36s} rounds {v['rounds']}  mechanisms {v['n_distinct_mechanisms']}")
    print("recurring fine classes (rounds / distinct mechanisms):")
    for c, v in recurring.items():
        print(f"   {c:34s} rounds {v['rounds']}  mechanisms {v['n_distinct_mechanisms']}")
    print(f"defect element provenance: {dict(elem_cls)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
