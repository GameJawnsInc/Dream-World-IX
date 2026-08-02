# Click-on-the-background authoring — a native Qt placement surface (study)

**Goal:** a Workspace canvas that shows a field's **actual background art** and lets the author
**click on it** to place content — floor polygons, NPCs, props, spawn/arrival, occluder contacts,
trigger regions — converting each click to an exact world coordinate through the already-proven
floor-plane homography. **Route B** of the 2026-07-28 owner decision (Route A, a browser handoff to
the existing HTML tracer, was explicitly **skipped** in favour of building the real surface).

**Origin:** the `image-field --trace` HTML tracer (★ in-game proven 2026-07-09, owner: *"the HTML
tool was easy to use"*, and a real photo of his hallway walked in-game). This study generalizes the
idiom off images and onto **any field with a background**. Related: [[project-ff9-image-to-field]],
[[project-ff9-camera-math]], [[project-ff9-gui-makeover]], [[project-ff9-overworld-placement-rules]].
Skill: `working-on-the-ff9-workspace` · `laying-out-ff9-fields`.

---

## 1. THE PLANE LAW — the division of labour with Blender

Owner framing (2026-07-28): *"a simpler version than the Blender editor, which allows rich creation
of shapes like ramps, multi-floors, etc."*

That boundary is not a matter of taste — **it is fixed by the mathematics**, which makes it a clean
law rather than a scope negotiation:

> **A click is a ray. A ray meets a *plane* in exactly one point, and a *surface* in an unknown
> number.** Therefore this tool is EXACT on any single horizontal plane and STRUCTURALLY CANNOT
> resolve height on a sloped or layered surface. Ramps, stairs, arbitrary 3D → **Blender**.

| Capability | This tool | Blender add-on |
|---|---|---|
| One flat floor, traced/edited on the art | ★ exact (2.3e-12 round-trip) | overkill |
| Content placement on a flat floor | ★ exact | possible, clumsy |
| Several **discrete horizontal** floors | reachable — see Rung 5 | native |
| **Ramps / slopes / continuous height** | **impossible by construction** | ✅ the reason it exists |
| Arbitrary 3D geometry, multi-storey | out | ✅ |

The un-projection solves `s = -C.y / ray.y` for the plane `Y=0` (`imagefield.py:43`). Generalizing to
a plane at height `h` is `s = (h - C.y) / ray.y` — a one-parameter change, which is why *discrete*
multi-floor is reachable (Rung 5) and *ramps* never are. **Do not let Rung 5 grow into Blender.**

---

## 2. Why this is de-risked (the receipts table)

Every primitive already exists and is proven. This study is **assembly**, not invention.

| Need | What already ships | Where |
|---|---|---|
| click → world coordinate | `unproject_floor` — perspective **homography**, round-trips `to_canvas` to 2.3e-12 | `ff9mapkit/imagefield.py:43` |
| occluder depth from a contact pixel | `occluder_z` (OT depth `resz/4 + depthOffset`) ★ in-game proven | `imagefield.py:67` |
| camera math, importable, zero CLI coupling | `inv3` :130 · `depth` :181 · `to_canvas` :186 · `solve_z_for_canvasY` :203 · `horizon_canvas_y` :220 · `decompose` :226 | `ff9mapkit/scene/cam.py` |
| camera construction | `make_camera(pitch_deg, distance, *, fov_x_deg, range_wh)` | `ff9mapkit/scene/guide.py:73` |
| polygon → walkmesh | `outset_polygon` :131 (miter +48u) · `triangulate` :163 (ear-clip) · `write_walkmesh_obj` :195 | `imagefield.py` |
| whole field emit | `build_image_field` :508 | `imagefield.py` |
| **draggable-handle point authoring in world coords** | `class StageCanvas(QGraphicsView)` — docstring: *"EDIT mode: draggable handles over every writable point"*; drag machinery :327+, mode toggle :166, screen-fixed furniture :473 | `workspace/behaviordoc.py:48` |
| pan/zoom graphics view + field art as `QPixmap` | `CampaignMap(QGraphicsView)` :61, pan/zoom :95-96, art→pixmap :550 | `workspace/mapview.py` |
| background PNG already rendered in GUI | field card thumbnails | `workspace/fieldcards.py:205,228,246` + `thumbs.py` |
| click-on-thing-to-site-it precedent | block siting + double-click naming | `workspace/worlddoc.py` |

**The single most load-bearing find:** `StageCanvas` already *is* a click-and-drag point authoring
surface in a world frame. This work generalizes it from behavior-tree stages to background art —
it does not start from a blank `QGraphicsView`.

⚠ **Embedding the existing HTML is OFF THE TABLE — not a preference, a licensing invariant.**
`pyproject.toml:64` pins `gui = ["PySide6-Essentials>=6.5"]`; the comment at :58-63 states Essentials
is chosen to stay LGPLv3-clean and "guarantees we never ship a GPL-only module… zero Addons imports
(audited 2026-06-28)", restated by `tools/gen_third_party_notices.py:93`. `QWebEngineView` is in
PySide6-**Addons**. Native Qt is the only route that keeps the audit true.

---

## 3. Architecture — two coordinate hops, one law each

```
   mouse press (widget px)
     └─► scene/view transform  ──────────────► CANVAS px (the 384×448 logical frame)
           └─► guide.make_camera / field cam ─► unproject_floor  ──► WORLD (x, 0, z)
                                                    └─► to_canvas  (the round-trip assert)
```

**HOP 1 — widget → canvas.** The canvas frame is the **384×448 logical** crop. ⚠ `_cover_to_canvas`
crops at the **4× layer size (1536×1792)** and the art is displayed at 2× in the HTML tracer — three
scales in play. Every conversion goes through one function; **no ad-hoc `/2` or `*4` at a call site.**

**HOP 2 — canvas → world.** `unproject_floor`. Two standing laws, both already documented and both
easy to silently violate at a new call site:

> ★ **USE `cam.inv3(R_view)`, NEVER `transpose(R_view)`** (`imagefield.py:15-17`). `R_view` is
> non-orthonormal — the k=14/15 squash is baked into row 1 — and a transpose injects ~7% vertical
> error (967u vs 2.3e-12 on the round-trip). A transpose *looks* right and is wrong.

> ★ **Horizon guard: reject `s ≤ 0`.** At or above the horizon a click has no floor intersection.
> The UI must render `horizon_canvas_y(cam)` as a visible line and refuse clicks above it — a
> silent clamp would place content at absurd depth.

**Self-check, cheap and mandatory:** every click asserts `to_canvas(world) ≈ click_px`. It is one
line, it catches both laws, and it turns a class of silent geometry bugs into a loud one.

---

## 4. The rungs

Each rung is independently shippable and independently verifiable. Rungs 0-2 reach parity with the
HTML tracer; **Rung 3 is the payoff** — the point at which this stops being an image-field feature.

### Rung 0 — `BackdropCanvas`, the shared primitive ★ DONE 2026-07-28
`workspace/backdrop.py` (`BackdropCanvas`) + the pure pair `imagefield.click_to_world` /
`world_to_click`. The scene IS the logical canvas (4× art transformed into the frame, display zoom
in the view transform — HOP 1 is `viewportTransform` and nothing else); the horizon renders dashed
+ labeled and clicks above it emit `click_refused`, never a clamp; click-vs-pan by 4px slop; atlas
zoom grammar; every accepted click runs the `to_canvas` round-trip tripwire
(`CLICK_ROUNDTRIP_TOL = 0.25 px`, proven live by a shifted-inverse monkeypatch test). Offline gate
green: grid round-trips < 1e-9 px across pitch 10-45 / yaw ±25 / two FOVs / a nonzero-centerOffset
camera; `ff9mapkit/tests/test_workspace_backdrop.py` pins the widget half. Note: the DEFAULT-pitch
26 camera's horizon sits just OFF-frame (canvas y ≈ −3.6) — pitch ≤ ~20 puts it on-canvas.

### Rung 1 — floor tracing (parity with `--trace`) ★ DONE + PLAYTESTED 2026-07-28
Click to add polygon vertices, drag handles to adjust, pitch slider re-deriving the horizon from the
real camera math, live outset preview (+48u `imagefield.COLLISION_OUTSET` — NOT `COLLISION_RADIUS_W`,
which is 80 since 2026-07-30; the trace outset is held at 48 pending a playtest), then call `build_image_field`.
**Verify:** `tools/gui_snap.py` → **read the PNG**; then build → `deploy_field.py --id <scratch>` →
walk it. Parity target: the hallway photo, re-done entirely in the GUI.

### Rung 2 — occluder contacts ★ BUILT 2026-07-29, ⚠ awaiting playtest
Click a contact pixel → `occluder_z` → a `--foreground`-equivalent layer. Math ★ already in-game
proven (pillar room, contact (230,320) → z 1073, flip mid-room). Small rung; mostly UI.
**Guard:** error when `z ≥ Z_BASE 4000` (means the contact was traced up the body, not at the base) —
the existing CLI check, re-enforced at the new call site.

★ **PREVIEW + POSITIONABLE SNIPS (owner-asked after the first playtest, built same day):**
attached cut-outs render ON the art (`set_cutouts` — a photo-aspect PNG fills the frame
REGISTERED and inert; anything else is a **SNIP**: previewed at its natural photo scale, its base
parked on the contact, DRAGGABLE with alpha-masked hits so its transparent surround still traces).
Dragging a snip moves its contact anchor by the same delta (z re-derives live); every contact has
its own draggable diamond handle for re-anchoring the flip line alone. Generate composites each
placed snip onto a transparent full frame at the 4x art resolution (written beside the source
image) and emits the SAME `--foreground path@cx,cy` CLI form — the frame rule stopped being a
rule the author has to know. A Show toggle hides the previews to trace under them.
**In-place regenerate + reopen (owner-asked):** after the first Generate the tab remembers the
project — the button becomes "Regenerate — in place", no dialog — and writes
`<out>/<stem>.trace.json` (photo, floor, pitch, cut-outs at their dragged offsets, name/id);
Open accepts a `.trace.json` and restores the whole editable session, so a project is set up
once and edited forever. **Hover affordance (owner-asked, applies to the Behavior stage too):**
every draggable item carries the OS move/resize cursor via `widgets.mark_grabbable` — a per-item
cursor out-ranks the pan hand exactly over the item's shape(), so an alpha-masked snip announces
itself only over its opaque pixels.
★ **THE GC-CHILD LAW** (found by the cursor pin; a real crasher class, three layers deep):
(1) a QGraphicsItem CHILD constructed with a parent argument is PYTHON-owned to shiboken — its
wrapper's GC deletes the C++ item under a live scene (stale `itemAt` wrappers mid-handler) and
its finalizer double-frees after a `scene.clear()`. Children must be SCENE-created then
`setParentItem`'d — swept everywhere (`backdrop._child`, behaviordoc's `_label`/`_marker` +
handle/grip squares, worlddoc's plate pills); `_kids` keeps wrappers alive as a belt.
(2) Tests must assert through RETAINED wrappers, never fresh `scene.items()` retrievals — a
retrieval-wrapper + `cursor()` pattern flaked ~1-in-3 under pytest's forced GC on Python 3.14 /
PySide6 6.11.1 even after (1), and neither deterministic deleteLater, widget parking, nor
`gc.freeze` cured it; the retained-wrapper rewrite made 8/8 combo runs deterministic.
**★ ROOT-CAUSED (pure-PySide6 repro, zero kit code) → `studies/pyside-gc-crash/NOTES.md`:**
shiboken's parent heuristic flips a wrapper to PYTHON-owned when `parentItem()` returns
`None`, so the wrapper's death DELETES the C++-owned item — the sweep helper's
`it.parentItem()` was the poison, not GC and not cursor(); version-independent (3.13 = 3.14,
6.10.3 = 6.11.1), unreported upstream (the PYSIDE-3380 fix is QAction-specific), NO pin
helps. The retained path is safe because it never calls `parentItem()`. Gate every PySide6
bump on `studies/pyside-gc-crash/probe_item_destroyed.py`. (3) `tests/conftest.py qt_drain`
parks each GUI test's widgets (opt-in per module; never where a module fixture caches one).

★ **BUILT into the Trace tab:** `BackdropCanvas` gained CONTACT mode (exclusive clicks; the traced
polygon stays visible, inert; emits the raw canvas pixel — `occluder_z` stays the ONE owner of both
refusals, horizon and the z≥Z_BASE "trace the base, not the body" message, surfaced verbatim).
The host: an **Add cut-out** toggle arms a contact click → records ONE undoable gesture → asks for
the cut-out PNG (full-canvas alpha); a Cut-outs strip (hidden until one exists) lists each contact
with its DERIVED z — re-judged per pitch change exactly like the trace vertices, never stored
stale — and Attach/Remove; valid contacts mark the art with `fgN · z` markers; Generate gates on
every cut-out valid + attached and emits the retired tracer's own `--foreground path@cx,cy` form.
Pinned: 2 canvas + 6 host tests (the proven (230,320)→1073 exact; the guard message; the pitch
re-judge; the argv via `parse_foreground_spec`; unified undo); `gui_snap trace:contacts` read.
**Playtest:** trace a photo with a real occluder (a pillar/doorframe), mark its base, attach the
cut-out, generate, deploy — walk in front (actor on top) and behind (occluded).
**First playtest 2026-07-29 — the MECHANISM works** (the layer deploys + occludes the actor at the
anchored depth), and it caught THE FRAME LESSON: a 531x473 object SNIP attached over a 1536x1792
photo cover-crops to FILL the screen (a giant dog) — the cut-out must share the PHOTO'S OWN frame
(erase everything but the object on a copy of the photo; equal aspect = aligned, that is the whole
rule). The tab now warns at attach on an aspect mismatch (advisory — an equal-aspect vignette is
legit) with the re-export teach; the flip-line read awaits a properly-framed cut-out.

### ★ Rung 3 — placement on ANY field (the payoff) — ★ CLOSED, PLAYTEST-CONFIRMED 2026-07-29
Load an existing `field.toml` + its background + **its own camera**, and click to place NPCs, props,
spawn, arrival. Writes back to the toml.

★ **Owner-confirmed in-game 2026-07-29:** a prop AND an NPC placed on a **verbatim** fork through
the Place tab, deployed (slot 4003), seen in-game — the whole chain at once: the live-install load
path (cache_field + compose_background), the walkmesh raycast, the open-doc write-back, the build's
below-band verbatim seating, deploy, render. Rung 3 is DONE end to end.

This is what makes the tool general: it serves forks of real FF9 rooms, not just traced photos, and
it kills the error class that `laying-out-ff9-fields` exists to prevent (content packed under ~192u,
inverted cardinals because the camera sits at **negative z**).

★ **THE SUBSTRATE IS THE RAYCAST, NOT THE PLANE (scoped 2026-07-28 — VIABLE).** The floor census
(`floor_census.py` / `.json`, 674/674 walkmeshes parsed) killed `plane_y` for real fields: only
**17%** have a flat dominant floor, **78%** slope > 64u (steps/ramps everywhere), 61% aren't at y≈0,
82% are multi-floor (median 3). A plane can't serve that population — but it doesn't have to:
**field content is placed as (x, z)** (the engine resolves y from the mesh), and every field's real
walkmesh is available in exact world frame (`vert + orgPos + floor.org`). So Rung 3's HOP 2 is
**click ray → Möller–Trumbore over the walkmesh's world triangles → the NEAREST hit** (you click
what you SEE). Benched on the census's worst sloped fields (`raycast_bench.py` — alxc_map056b
9727u spread, ipsn_map740, GRGR, the map158 offset donor): sampled surface points recover **exactly
(worst 1.7e-11u)** at 89–98%; the remainder are pixels owned by a NEARER floor — the visibility
semantics, not error, and the walkmesh knows it (a stacked-hit click lists its floors, defaults to
the visible one, warns). This does not breach §1 THE PLANE LAW: the law bounds *authoring new
geometry* from a photo (a ray meets an unknown surface nowhere exact); placement targets the
**known** surface, where a ray–mesh intersection is closed-form. The self-check still applies
unchanged: every accepted hit re-projects through `to_canvas` onto the click.

Build inventory (all pieces exist, none exotic): camera + walkmesh per field = `extract.cache_field`
(idempotent, cached); the canvas-frame backdrop = the extract compositor (per-camera mode for
multi-cam fields; scrolling Range is already the canvas frame in `BackdropCanvas`); placement edits
ride the OPEN document + the shell undo contract (the Behavior stage-edit precedent — one pure op
per drop); art loads async in the thumbs idiom.

★ **THE HARD GATE IS CLEARED — the imported-camera census ran 2026-07-28** (`camera_census.py` /
`camera_census.json` in this directory, against the live install). **674 fields, 741 cameras, 729
measured: every one round-trips < 1e-9 px (worst 7.4e-12). Rung 3 is GENERAL — no pose envelope.**
The 12 unmeasured cameras are up-pitched sky/ceiling cutscene shots (Prima Vista meteor, steeple
views) with genuinely no floor plane in frame — not a placement surface, refused honestly.

The census earned its keep before the sweep even finished — two findings:

1. **The offset bug (FIXED + fenced same day):** `unproject_floor` inverted the offset-less canvas
   map while `to_canvas` folds the camera's GTE `centerOffset` in — so a real camera round-tripped
   exactly |offset| px wrong (**measured 400.8 px** on the map158 donor, centerOffset [26, 400]),
   and **277 of 741 real cameras (37%) carry a nonzero offset**. Synthesized cameras are offset
   (0,0), which is why the proven 2.3e-12 figure never saw it. The exact instance of §3's "easy to
   silently violate at a new call site" — caught by calibrating the instrument on 3 known cameras
   before the sweep.
2. **The plane-height scoping fact:** **33 cameras sit BELOW the y=0 plane** (their floor
   intersections land *above* the horizon line — the first census run mis-filtered all 33 by
   assuming floor = below-horizon). A real field's floor height is arbitrary (`vert + orgPos +
   floor.org`), so **Rung 3 must un-project onto the FIELD'S OWN floor plane, not y=0** — Rung 5's
   one-parameter change (`s = (h - C.y)/ray.y`) is a Rung 3 *dependency*, pulled forward. The
   floor-SELECTOR UI stays deferred; measure real walkmesh heights when scoping Rung 3 and read the
   plane height from the field's own walkmesh.

⚠ **Write-back is surgical, and refuses bundled examples.** The standing trap: the form editor's
Save rewrites a byte-exact golden oracle (CLAUDE.md §5). Write-back must preserve unrelated keys,
comments, and ordering, and must **refuse outright** on anything under `ff9mapkit/examples/`.
On a `--verbatim` fork, new content seats below the party band ([[project-ff9-npc-on-verbatim]]).

### Rung 4 — regions drawn on the art ★ BUILT 2026-07-29, ⚠ awaiting playtest
Gateway / trigger quads drawn directly on the background instead of typed as numbers. Carries the
existing region laws (tags 2/3/10, `IsInQuad` dead-zones) — the canvas should *render* a dead-zone
warning, not just accept the quad.

★ **BUILT, both hosts + the CLI (commits `4213b627` part A / `18a3ed44` part B):**
- **The canvas** (`BackdropCanvas` region mode, exclusive like the others): four clicks build one
  quad (`region_drawn`), corner + whole-quad drags reshape (`region_changed`, ONE emission per
  gesture through the same seams the vertex drags use), right-click rotates the walk-out edge or
  deletes; Esc/right-click abandons a quad mid-draw. Corners project at the walkmesh's real floor
  height and legitimately hang OFF the mesh (donor door quads do) — an off-mesh click converts
  through `imagefield.click_to_plane`, §1's own `s = (h - C.y)/ray.y` one-parameter
  generalization, raycast-exact wherever the mesh is under the pixel.
- **THE LAWS RENDER, both directions.** The fan simulation (`imagefield.fan_triangles` /
  `zone_fan_audit`) surfaced a truth the dead-zone framing missed: with the encoder's
  auto-doubling (`quad_zone`), a drawn 4-corner quad can NEVER dead-zone — the fan always covers
  the drawn interior. The real 4-corner hazard is **OVER-TRIGGER**: a dart/bowtie's fan swallows
  the notch (up to the whole hull), firing where nothing was drawn — rendered as a warn wash on
  fan-minus-drawn. The genuine dead zone survives only in hand-authored 5-DISTINCT-point zones
  (the classic collinear strip) — rendered as an error hatch. TREADQUAD overlap starvation marks
  live too, judged by `build.region_overlap_pairs` — extracted from `lint_region_overlaps` so the
  canvas and the lint share ONE owner. A gateway's corners-0→1 walk-out edge draws thick with an
  outward chevron.
- **The tool strip shipped WITH this rung as mandated** (`widgets.ToolStrip`, `#railSeg`
  segments — the rail's settled rule set, zero new QSS): Place = Place/Regions; Trace =
  Floor/Cut-outs/Regions (the Add-cut-out toggle became the Cut-outs segment). The strip earned
  its own row in the Trace tab immediately — the snap caught the shared photo row squeezing it to
  a blank chip (the round-7 squeeze law, live).
- **The Place host**: pure ops `place_gateway`/`place_event`/`move_zone`/`delete_region` +
  `region_rows` (the one derivation of labels + both laws, reused by the Trace host through a
  shim); gateway target/entrance boxes on the strip; verbatim forks stay live (below-band
  seating). **The photo lane**: zones stored in CANVAS px beside the floor (pitch re-judges,
  undo walks them), emitted via `image-field`'s new `--gateway "to[,entrance]@cx,cy;…"` /
  `--event-zone "message@cx,cy;…"` args — un-projected through the same camera as the floor into
  real `[[gateway]]`/`[[event]]` rows, so doors survive every in-place regenerate; the
  `.trace.json` sidecar and the field.toml reopen path round-trip them both ways.
- Pinned: `tests/test_region_laws.py` (14 — the fan audit's every class, plane round-trips,
  overlap keys, the generator emission) + backdrop (8 new) + place (7 new) + tracedoc (4 new);
  snaps `place:regions` + `trace:regions` read at 100/150 (both hosts hold the 150 rung).
**First playtest 2026-07-29 — the chain WORKS to the warp (a photo-lane door on the hallway
project armed and FIRED), and it caught THE FIELD(0) DOOR:** the owner drew the quad before
setting the 'to field' box (which feeds NEW draws only), typed 301 after — the row kept to=0,
compiled to `Field(0)`, and the walk-in BLACK-SCREEN softlocked (no such field; ~ cannot recover
a dead transition; the canvas label "door0 → 0" was the only tell). Closed three ways, same day:
`build.validate` ERRORS on a non-positive gateway target (a Field(0) door never ships); the
quad's own menu grew **Set gateway target…** (`region_retarget` + an instance-dialog seam in
both hosts — on the photo lane there IS no other editor for a drawn door); `region_rows` marks
the row NO TARGET and the Trace tab gates Generate until every door has one.
**Round 2 same day — ★ BOTH LANES CONFIRMED IN-GAME:** the retargeted hallway door WORKS
("nice that worked"), and the Place tab landed an NPC + prop + gateway + event on a verbatim
Black Mage Village fork, all seen in-game. The round's catch — **THE TOP-RIGHT "..." BOX:** a
`received` event re-styled the author's message as window 7 at the dialogue default (10,1)+UPR —
a sliver pinned top-right with no item name (the Place placeholder made it a literal "...").
The exact disease `_chest_received_box` already cured for CHESTS, never propagated to events.
Fixed at the one owner: both text channels now route received events through the chest's
canonical box (`[STRT=69,3]` centering + DEFT + the live item name); `received` needs no
message; an authored message fills the box verbatim; the bare "..." never ships. Verified
against the reporter's own field on a scratch copy. ⚠ The fixed box itself awaits one in-game
look (rebuild + redeploy + walk-in).

★ **THE DEFAULT-VALUE LAW pass (owner-asked before rung 6):** both playtest bugs were one
disease — a GUI-minted default that is *quietly plausible* in-game — so every minted value got
audited against the law: **a default is REAL (renders correctly) or LOUDLY INVALID (a gate
refuses it), never in between.** Probed with minimal projects; already-gated ✓: chest-no-flag,
choice-empty-npc, npc-no-pos, dup sps ids (all validate errors), off-mesh (0,0) positions (the
placement lint). Fixed: the form gateway's `to = 100` — a REAL id nobody chose, silently
warping to it — is now 0 (the Field(0) gates own it); the form flag's fixed `index = 8712`
now mints the next free bit (a constant aliased every added flag onto ONE save bit) and
validate reports index collisions directly (`collect_flag_defs` always knew; no call site
spent it — load crashed, dict-built projects said nothing); minted NPCs drop `dialogue "..."`
(the silent-talk channel's canonical line is the real default, both build lanes); the form
prop default "chest" → "barrel" (looked openable, wasn't); drawn events get **Set message…**
on the quad menu (the photo lane has no other editor for a zone's words) + a canvas/lint warn
while the "..." placeholder would ship as a literal popup.

### Rung 6 — the multi-room / floorplan composer ★★ 6a-6d ALL OWNER-CONFIRMED IN-GAME 2026-07-31
**A multi-room / floorplan composer, folded in here rather than built standalone.** Draw several
rooms on this canvas, declare which edges are doors, and get a wired dungeon: gateways both ways,
arrival position + facing per side, encounters, save-point siting.

> **The verified math, every constant sourced, and the record of what an adversarial pass caught:
> [`RUNG6.md`](RUNG6.md). Read it before changing a number** — the draft's own values were wrong in
> five ways that each looked right, and §1 is the table of what the measurements killed.
>
> ★★ **FIRST CONTACT IS DONE AND THE RUNG IS CLOSED.** The owner worked
> **[`RUNG6-TESTPLAN.md`](RUNG6-TESTPLAN.md)** end to end on 2026-07-30/31: drew a two-room freeform
> dungeon in the tab, composed it, built it, deployed it per room and walked it — *"Step 7 passes,
> campaign.toml imported well."* RUNG6.md §6.2 (does front-align LOOK right) is resolved.
>
> **SEVEN defects came out of that one session, and the suite had caught none of them** — every one
> lived in what a real mouse or a real screen does. In order: the live-gate stall; the chart
> re-centring on every corner; an integer-truncation ratchet that slid the chart on hover; the 8u
> door tolerance being unreachable by hand; stacked corners being unpickable; the spawn band-warning
> firing on ordinary rooms; `segments_cross` reading an exact abutment as an overlap; and the
> placeholder checkerboard not following a freeform footprint. Each is written up in RUNG6.md with
> the measurement that killed it and a fence verified RED against the reverted fix.
>
> ★ **THE STANDING LESSON FOR THIS TAB:** every one of the 47 original fences drove `click_world`,
> the world-space seam, so not one could see a defect in what the VIEW did between clicks — and the
> art fences all used a rectangle, so none could see a clip that only fails on a polygon. **Fixtures
> chosen for convenience test the shapes that cannot fail.**
> Two things it already establishes: the offline pipeline is sound (a 3-room plan composes, lints
> and builds clean), and **the live gate was a stall past ~4 rooms** — every gesture cost what
> DRAWING the plan cost, ~17 s on eight rooms, because `compose` re-derived the WHOLE plan on every
> edit and nothing survived a judge.
>
> ★ **FIXED 2026-07-30, before first contact** (`gate_bench.py --drag N` reproduces both halves; it
> loads the pre-change module from git rather than guessing at it — the first draft of these numbers
> quoted a "before" that was the NEW module minus its cache, and no version of the code ever took
> it). Scanline samplers + a `GeomCache` the tab carries across judges + a `cancel` hook.
> **A gesture went ~17 s → ~0.6 s and is now FLAT in room count** (the same at 3 rooms and at 12 —
> the flatness is the fix, the raw number is just today's machine); an all-hit re-judge is 4–18 ms;
> the cold first judge ~17 s → ~4 s at eight rooms. The
> mid-drag **snap-back** went with it — `set_plan` was clearing `_drag` on every feed, so a verdict
> landing under a drag ate the gesture with no undo entry. **THE LESSON WORTH KEEPING:** the obvious
> win — reuse `standable_map`'s distance as `interior_point`'s ranking distance — is a *behaviour
> change wearing an optimization's clothes; they are measured at the grid SAMPLE and at the CELL
> CENTRE respectively, and it moved the spawn a whole cell on 4 of 22 plans. Every step was gated on
> a 400-plan differential against the pre-change module: 0 verdict changes.

- **6a ★** — `ff9mapkit/ff9mapkit/floorplan.py`, the pure Qt-free core: the closed-form projection,
  polygon health, `standable`, the edge-anchored inward normal, the engine's own facing formula,
  candidate shared walls, the door strip, arrival + facing, the camera fit, interior siting, and
  fifteen gates. 96 fences in `tests/test_floorplan.py`. Minted **THE TWO-FRAME LAW** (see RUNG6.md
  §2) — the plan layout is an authoring fiction, so every artifact of a room rides the same integer
  `off_r`, art included.
- **6b ★** — `ff9mapkit floorplan <plan.json>`: one member dir per room with its field.toml,
  walkmesh.obj and **polygon-clipped** placeholder art, plus `campaign.toml` and the re-editable
  `floorplan.json` sidecar. Proven offline end to end — compose → `lint-campaign` OK 0 warnings →
  each room 0 errors → `build-all` emits a real dist. The id pre-flight reads the LIVE
  DictionaryPatch stack before minting (the kit's own collision guard runs only at
  `deploy --apply`, i.e. after you have already authored N rooms onto colliding ids).
  Two rooms deployed **additively** to 30500/30501 — the other ~407 registrations untouched.
- **6c ★** — the Workspace **Floorplan** tab on the Author rail beside Map (`floorplandoc.py`):
  `PlanCanvas` is a plan-view CHART with one isotropic px↔world pair (+z up, the layout probe's
  frame — probed 26/26: exact inverse to 1e-6, a click on the cursor within 0.4u after a real zoom
  and pan). Rooms mode draws and drags; Doors mode paints `shared_edges` candidates on every shared
  wall and one click declares a door. **`compose()` runs live on every edit** (worker thread, 140 ms
  debounce, generation-counted — it is ~0.5 s/room) so the fifteen gates paint ON the drawing.
  Compose streams the CLI verb through `run_job`, then `open_campaign`s the result so the dungeon
  lands as a live campaign (§5 call site 3). Undo is doc-local over the session snapshot
  (`TraceDoc`'s model) — that is what makes a door-pair edit atomic despite `shell._UndoRec` being
  single-member, and a half-undone pair is a gateway with no arrival. 56 fences, 140 with
  a11y/style/smoke, 616 across the GUI family; snaps at dark/100, dark/150, light/125.
  ★ **The live gate is now fast enough to stay live** (see the blockquote above): `judge_now` spends
  one `GeomCache` across judges and passes `cancel`, so a gesture re-derives only what it touched;
  the `Dungeon` box no longer re-judges geometry at all (its gate always ran on the repaint, never
  on the judge); and `_judge_work` catches `ComposeCancelled` ahead of its catch-all, so a
  superseded judge cannot paint a refusal the author never earned.
  ⚠ Disclosed: with a finding showing the chart is 130-158 px at CALIBRE 150 — spawned as its own
  task (a splitter carries the round-7 squeeze-persistence obligation).
  **An adversarial review after the build found NINE defects**, two of them fixes the build claimed
  to have made and the renders disproved. The durable ones:
  (a) **a control DEAD ON CLICK, on the tab's whole purpose** — you could not start a room abutting
  another, because a new room's first corner IS the neighbour's corner and the press ate it as a
  drag-grab. **Invisible to all 47 fences and every snap: they all drove `click_world` directly and
  so never ran the press/release resolution.** A press on something grabbable is now provisional and
  a release with no travel is a click, fenced with synthesised real `QMouseEvent`s.
  (b) **THE NINTH-GROUND LAW** — each room drew its name in the same token its own fill was made of:
  **2.16:1** on nord accent, under even the 3.0 non-text floor in six of eight palettes. State is now
  said three ways that survive a fixed ink (stroke colour, stroke width, a glyph — which also
  survives colour blindness, as the ink never did).
  (c) **THE DEFAULT-VALUE LAW** — with no `.ff9deploy.toml` (every fresh checkout's first run) the
  tab reported "composes: ids 30000-30000" with Compose ENABLED, then the click refused and did
  nothing; and `on_compose` never consulted the name validator at all. One `_envelope_problems()`
  list is now spent by both the paint and the click.
  (d) the tests were reading the developer's real gitignored `.ff9deploy.toml`, and it was
  load-bearing — adding the id gate turned four "clean plan" assertions red because they had been
  silently consuming this machine's id band. Green here, red on a colleague's checkout.
- **6d** — the playtest. Open questions it settles are listed in RUNG6.md §6: `R_WALK = 80` vs the
  repo's 48 (a code derivation, not a measurement), whether front-align *looks* right, the 170u
  depth floor, and `entry_settle = "auto"` on a hand-drawn polygon.

En route, two defects outside this rung were found and spawned as their own tasks, plus one fixed
here: `cam.solve_z_for_canvasY` and `guide.frame_floor` are **unsound at low pitch** (`frame_floor`
raises at every distance for pitch 15, and `pack.new_project` swallows it — so `ff9mapkit new
--pitch 15` silently ships a template mesh); `[encounter] scene` accepts a catalog NAME that the
lint resolves and the build then kills with a bare `int()` error; and the layout probe compared the
spawn against an entrance-0 arrival and called a correct field COLLIDING (fixed — the player is
exactly one of them at a time).

> ★ **THE DRAWN-MESH LAW — the human draws the walkmesh; the composer never infers one.**
> Auto-deriving a walkmesh from an arbitrary field drawing is a research problem (segmentation,
> plane inference, semantic room boundaries — the same wall the `--auto-floor` hallway trial hit,
> where *where a field ends* proved SEMANTIC and un-inferable from one ground plane). Sequencing the
> composer AFTER this tool retires that problem entirely: geometry arrives hand-drawn and exact, and
> the composer is left with **topology only** — deterministic, testable, no inference.

This is why the composer is a rung here and not its own study: standalone it would need to generate
geometry; downstream of Rungs 0-3 it does not. **Do not start it before Rung 3 is real.**

### Rung 7 — ONE INTEROPERABLE WORKFLOW (owner-asked 2026-07-31, decisions taken)
**The ask, verbatim:** *"we may need more modularity within-room to get better camera setup and
handle different room layouts… we should either enable from-scratch fields in the Place tab or
create a new one or better integrate with the Trace tab. i want it all to be interoperable."*

Prompted by a deliberate stress test: a 9762u-wide room composed into a camera at distance 18227.

> ★ **THE BLOCKER IS NOT THE CANVAS. IT IS WHO OWNS THE FILE.** Verified by running it: compose a
> dungeon, hand-add an `[[npc]]` to a room, recompose the **unchanged** plan → the NPC is gone,
> silently, exit 0, no warning (`floorplan.emit` is an unconditional `write_text` per room, :1739;
> `imagefield.py:937` has the same shape). **Any click surface built over a composed room writes
> into a file the next Compose deletes** — so non-destructive emit is the prerequisite for every
> other route, not a nicety.

**Three measured facts that set the shape:**
- **Width, not length, is the expensive axis.** `fit_play_camera` fits the AABB, so the SAME
  2200×9762 corridor costs distance 6567 drawn north-south and **18226 drawn east-west** — 2.8×,
  and nothing in the tab says so.
- **The composer mints cameras outside FF9's entire shipped envelope.** Across 741 real cameras a
  96u character renders at median 9.3px / p25 7.4 / p05 4.2. The stress room renders at **3.3px**.
  `fit_play_camera` refuses only past distance 60000; below that it returns a plausible camera.
- **The engine already scrolls, and it is the right lever for width.** `[camera.scroll]` is shipped
  and honoured end to end (`build.is_scrolling` :3623 → `_resolve_one_camera` :3629 →
  `cam.scroll_bounds` :110 → `EnableCameraServices`), in-game proven at 768×448. It decouples focal
  length from the painting via `window_width`. **A static 384-wide room tops out at ~3700u.**
  ⚠ Scroll fixes WIDTH ONLY — FF9 pans a viewport across a FIXED camera, so depth foreshortening is
  physics (~1.2×). For a deep room the answer is splitting, which the composer already does.

**A live data-loss bug, found while surveying:** the tab's own round trip drops 6 of 8 room keys —
`plan()` (`floorplandoc.py:1712`) and `load_plan` (:2268) emit only `{name, poly}` while
`compose` reads `pitch`/`fov`/`id`/`encounter`/`savepoint`/`title`. Hand-editing `floorplan.json`
works until you open it in the tab.

**OWNER DECISIONS TAKEN 2026-07-31:**
1. **Legibility gate: REFUSE under p05 (4.2px), WARN under p25 (7.4px)** naming the remedy (scroll
   at range N / rotate 90° / split). THE DEFAULT-VALUE LAW on a value the composer currently mints
   unbounded.
2. **Scroll cap 960** — FF9's own maximum shipped width, covers ~9455u at p25. Anything wider is
   SPLIT, which is what FF9 does (48 zones, median 11 fields each; Lindblum is 70). 1536 builds
   clean offline but is 1.6× beyond anything Square shipped — not without a playtest.
3. **Recompose REFUSES on drift this rung, MERGES next.** Merge precedent: `build._merge_scene`
   (:156) is already "the generator owns the spatial keys, the human owns the rest".

**The ladder:**
- **7a** — carry unknown room/door keys through `plan()`/`load_plan` unchanged + the legibility
  gate in `fit_play_camera`. Pure functions, no UI, no install; stops the data loss immediately and
  is the plumbing the `range`/`scroll` key needs. **START HERE.**
- **7b ★ BUILT 2026-07-31, ⚠ AWAITING ONE PLAYTEST** — `fit_room_camera` fits static first and
  widens in 384 steps to the 960 cap only while under p25, emitting `range` + `window_width = 384`
  + `[camera.scroll] enabled`. Verified end to end on a 9762×2200 room: the built `.bgx` re-parses
  to range `[960,448]`, viewport `[160,800,112,336]` (exactly `cam.scroll_bounds`), **proj 498 =
  the SCREEN focal length at 384, not the painting's** — and the `.eb`'s `Main_Init` begins with
  `EnableCameraServices`, while the static room's does not contain it at all (decoded structurally;
  a raw 0x71 byte search says "present" for BOTH and proves nothing).
  Measured: that room 2.6px → **6.7px** (refused → warn); a 4000×1200 room now scrolls at the
  **proven** 768 and comes out clean; 20000×2200 still refuses and says split.
  ⚠ Scroll is a COMPOSE-TIME decision — the range changes the distance, which changes `off_r`,
  which moves the walkmesh. Fit and emit together; never bolt a scroll camera onto a composed room.
  (Fenced: the two `off_r`s differ.)
  ★ **THE REMEDY IN A REFUSAL IS TESTED, NOT ASSUMED.** The first message told every wide room to
  rotate — including a 20000×2200 hall, whose rotation is a 2200×20000 hall and equally
  unrenderable. `legibility_problem` now actually FITS the rotated room and reports what it would
  reach, three ways: rotate (clean), rotate-but-still-short (says both, in order), or split. A
  fence caught the over-promise.
  ⛔ **PLAYTEST GATE, OPEN: 768 is the only width proven in-game in this repo (the field-4003
  spike). 960 is inside FF9's own shipped envelope but has never been walked HERE** — and a room
  needing more than 768 goes straight to 960, so the first scrolling room an author composes may
  well be the unproven width. Walk one 768 room and one 960 room before trusting either.
- **7c** — non-destructive `emit` (refuse-on-drift) + pin room ids into the sidecar on first compose
  (the CLI pre-flight at `cli.py:1543` reads LIVE registrations, so it can renumber your own
  already-deployed rooms).
- **7d** — `build_surface_from_project` + flip Place's predicate. **The refusal is ONE branch**
  (`placedoc.py:461`, `donor_field_id(data) is None`) and it is about PROVENANCE, not geometry — a
  composed room has an exact camera and a real walkmesh, which is all Place needs. Unblocks
  composed rooms, `ff9mapkit new` scaffolds and traced fields at once.
- **7e** — per-room pitch/fov on the existing room right-click menu (UI only, once 7a lands).
- **7f** — traced polygon → floorplan room. ⚠ Hand the UN-outset polygon (`outset_polygon` is a
  miter and blows up on the acute corners a hand trace produces), and accept that it is a
  GEOMETRY-ONLY import: the composer re-solves the camera, so the art cannot travel.
- **later** — `[[camera_zone]]` multicam. Built and lint-covered but `FORMAT.md:148` says
  *"in-game proof pending"*. Prove ONE hand-authored multicam field in-game first, and never put it
  in the composer (THE DRAWN-MESH LAW: the author declares the partition).

⚠ **A bug to fix regardless of any of this:** `tracedoc._camera` (:263) hard-codes
`imagefield.DEFAULT_DISTANCE`/`DEFAULT_FOV`, and `shell._on_tab_changed` (:4947) auto-loads the open
field into a pristine Trace tab — so any field whose distance differs is re-projected through the
wrong camera and returns off-canvas garbage **with no exception**. Reachable by clicking a tab.
(For "give me art guidance for this room", the answer already exists and is simply unexposed:
`ff9mapkit paint-template <field.toml>`, zero hits under `workspace/`.)

### Rung 5 (bounded) — discrete multi-plane ⚠ SCOPE SHRUNK 2026-07-28
Add `plane_y` to the un-projection (`s = (h - C.y)/ray.y`) so a **traced photo** with several flat
floors at known heights can be authored per-floor, with a floor selector. **THE PLANE LAW (§1) is
the ceiling: if a surface's height varies across it, it is Blender's.** Rung 5 ships only if a real
photo wants it — and it is now PHOTO-ONLY: real-field placement no longer needs planes at all
(Rung 3's walkmesh raycast supersedes it there; floors fall out of the mesh).

---

## 5. Call sites — THE CALL-SITE LAW

[[project-ff9-gui-makeover]]'s standing failure mode is *a correct mechanism no call site ever
spends*. Named up front:

1. A Workspace document/tab hosting `BackdropCanvas` (locate the existing tab-registration pattern
   in `workspace/shell.py` alongside `BuildDoc` / `BehaviorDoc` / `WorldDoc` — follow it, don't
   invent a second one).
2. An entry point from an existing field card (`workspace/fieldcards.py`) — "place content on this
   field" from where the author already is.
3. The image→field on-ramp (Rung 1) reachable for a *new* field, not only an existing one.
4. Write-back into `field.toml` via the existing editor backend, not a private writer.

**Verification is `tools/gui_snap.py` — render the real surface and READ the PNG.** Never assert a
GUI claim from source; that is the documented recurring failure in this package.

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| **A transpose sneaks into a new call site** (~7% vertical error, looks plausible) | §3 — one shared conversion function; the `to_canvas` round-trip assert on every click |
| **Real field cameras fall outside the verified envelope** | ★ RETIRED — census 2026-07-28: 729/729 measured cameras < 1e-9 px; the one real defect (centerOffset, 37% of cameras) found + fixed + fenced |
| **Un-projecting a real field onto y=0 when its floor sits elsewhere** | The census's finding 2 — Rung 3 reads the plane height from the field's own walkmesh (`plane_y`) |
| **Three coordinate scales (384×448 / 2× display / 4× layer)** silently mixed | One conversion function, no ad-hoc scaling at call sites |
| **Above-horizon clicks** placing content at absurd depth | Reject `s ≤ 0`; render the horizon line |
| **Write-back clobbers a golden oracle** | Surgical write; hard refusal under `ff9mapkit/examples/` |
| **Scope creep into Blender's territory** | §1 THE PLANE LAW — ramps are impossible here by construction, not by policy |
| **A GUI mechanism nothing spends** | §5 names four call sites; verify by reading `gui_snap` PNGs |
| **QtWebEngine creeps back in** | Native Qt only; the LGPL audit claim in `gen_third_party_notices.py:93` must stay true |

---

## 7. Do-next

1. ~~**Rung 0** — `BackdropCanvas` + the two conversions + the round-trip assert.~~ ★ DONE 2026-07-28.
2. ~~**The imported-camera census**~~ ★ DONE 2026-07-28 — Rung 3 is GENERAL; the offset bug is fixed;
   `plane_y` is pulled forward as a Rung 3 dependency (see the gate block under Rung 3).
3. **Rung 1** — tracing parity. **Part 1 (the trace layer) ★ DONE 2026-07-28:** `BackdropCanvas`
   trace mode — click-to-append (horizon-refused), zoom-immune drag handles with live world
   readout, right-click delete, canvas-px truth re-judged per camera swap (bad verts mark red),
   the +48u outset ring re-projected live and SUSPENDED while any vertex is invalid; one
   `on_floor` callback per gesture, `set_floor` never echoes. **Part 2 (the Trace tab) ★ BUILT
   same day, ⚠ awaiting playtest:** `workspace/tracedoc.py` on the Assets rail — the ingest is
   the SAME cover-crop the build performs (2× display, the tracer's frame), pitch slider, host
   undo/clear, Generate = the tracer's exact `image-field` argv through `run_job` (id via
   `pack.check_custom_id`); snap surfaces `trace:bare|traced` (fixture art = `_paint_room`, one
   owner); the a11y sweep caught the slider as a ringless Tab stop (id-scoped reserved ring —
   an app-wide QSlider box would deFusion every slider), the 150% snap caught standing prose
   starving the canvas (162→270px). **★ PLAYTEST-CONFIRMED 2026-07-28** — owner traced a photo
   in the tab, generated, deployed, and walked it ("looks good i got one in"). **RUNG 1 CLOSED —
   the GUI reaches full parity with the retired HTML tracer.**
4. ~~**Scope Rung 3's UI**~~ ★ SCOPED 2026-07-28 — VIABLE via the walkmesh raycast (see the Rung 3
   block: floor census + bench receipts). Build order, (a) ★ DONE 2026-07-28: `click_ray` is now
   THE one-owner ray construction (spent by both `unproject_floor` and the raycast, so the
   offset-fold class cannot fork), `click_to_surface` (Möller–Trumbore, hits nearest-first,
   tripwired), `mesh_world_tris`, `world_point_to_click` — offline-gated (ramps < 1e-6, stacked
   floors sorted, refusals).
   ★ **THE RENDER-FRAME Y-FLIP (a law step (b)+ must keep):** the engine negates walkmesh Y
   before the GTE (WalkMesh.cs:54), so the frame the ART shows is `(x, -y, z)` of `world_verts` —
   `mesh_world_tris` flips at the projection boundary exactly as `compose_background`'s in-game-
   proven footprint does; the bench alone could NOT catch this (a round-trip is self-consistent
   under a global flip) — reading the proven compositor did. Placement's written (x, z) is
   sign-invariant.
   (b) ★ DONE 2026-07-28 — `BackdropCanvas` place mode: `set_surface` (render-frame tris drawn
   as the live walkable footprint), `set_place_mode` (exclusive with trace), `surface_clicked`
   carrying the visible hit's (x, z) + every stacked hit nearest-first with floor ids (hosts
   disambiguate, never guess), `set_markers` for placed content.
   (c) ★ BUILT 2026-07-29 — `workspace/placedoc.py` (`PlaceDoc`, the "Place" tab on the
   Author rail): the shell PUSHES the open doc (the BehaviorDoc feed contract; no disk at
   construction/tab-show), one explicit **Load the room** click builds the donor surface off
   the GUI thread (`cache_field` camera/mesh + per-camera `compose_background`, disk-cached
   under the provision cache, `env_lock`'d); drops are PURE ops (`place_npc`/`place_prop`/
   `set_spawn`/`set_arrival` — arrival upserts by entrance) into the OPEN dict + ONE
   `on_edit` → the shell records the undo step (focus "place" lands Undo back on the tab)
   and the tree grows the row. Markers render at real floor height (`floor_y_at`, plan-view
   barycentric, stacks resolved toward the eye); a stacked-hit click ASKS via a floor menu.
   Refusals: `protected_reason` (examples/installed) kills the whole surface; no donor
   (`build.donor_field_id`, the pure-dict refactor) says why; VERBATIM disables spawn/arrival
   (the donor's entry sequence runs) while npc/prop ride the build's below-band seating.
   `[[prop]]` became a first-class editor kind on the way (PROP_SPEC + tree/rollup/lint —
   it had none). Entry ★: the field-card picker takes a {donor→open member} map from the
   shell and offers "Place content on this field" on already-forked rooms (§5 call site 2).
   Pinned: `tests/test_workspace_place.py` (16) + a smoke block (drop→undo→focus round-trip);
   `gui_snap place:bare|fork|refused` read at 100 + 150 (the fork state runs the REAL op path
   over kit-painted stand-in art; the dirty-close modal needed `_no_modals`, the drift lesson).
   (d) ★ PLAYTEST-CONFIRMED 2026-07-29 — the owner placed a prop + an NPC on a VERBATIM fork
   in the Place tab, deployed to 4003, and saw both in-game (the live-install load path, the
   raycast, the write-back, AND the build's below-band verbatim seating, proven in one pass).
   **RUNG 3 CLOSED.** Rung 4 followed and is owner-confirmed on both lanes; Rung 6 was taken up
   2026-07-29 once its "do not start before Rung 3 is real" gate was satisfied — 6a+6b built, see
   its block and [`RUNG6.md`](RUNG6.md).
5. **Rung 2** ★ BUILT 2026-07-29, ★ CORE MECHANISM PLAYTEST-CONFIRMED (contact mode + the
   Cut-outs strip in the Trace tab; owner aligned a snip on a real hallway photo and confirmed
   it composites correctly in-game — "that worked when i aligned it correctly"). Two full
   playtest rounds drove real fixes, all landed:
   (a) *Re-deployed art needed a full relaunch* → root-caused to the ENGINE, not the tab: the
   s35 overlay-texture cache keyed on path alone, serving the stale decode all session. The
   owner called its original ★ proof confounded (the entry-settle churn) → **s35 RETIRED**:
   reverted from `C:\gd\FFIX\Memoria`, compile-checked, then DEPLOYED closed-game 2026-07-29
   (Output == both arches sha `44090B29…`, backup `preS35removal.20260729-114832`; full story
   + fingerprint tokens in `memoria-patches/README.md`'s s35 row). ★ **Owner-confirmed
   in-game: "image movement is hot-reloadable now"** — move cut-out → Regenerate → deploy →
   ~ Reload, no relaunch, exactly as designed.
   (b) *Says-Move-but-pans* → two layers. First cut: the press resolver used `itemAt`
   (topmost-only), so a trace leg/ring/label crossing a grabbable ate the press while the
   hover cursor looked through cursor-less items — fixed by scanning every item under the
   point by kind. Then a SEPARATE session root-caused the real disease underneath both this
   and the wider GC-crash saga: **`QGraphicsItem.parentItem()` returning `None` silently
   flips the wrapper Python-owned, so its death DELETES the C++ item** — a pure PySide6 bug,
   version-independent (memory `project-ff9-pyside-parentitem-ownership`, full record
   `studies/pyside-gc-crash/NOTES.md`). The press-walk sites now resolve through tag slots
   alone (zero `parentItem()` calls in `workspace/`); backdrop drags no longer risk deleting
   the art itself. Background-vanishing-during-drag (a separate owner report) was THIS bug,
   not a repaint artifact — a viewport-update-mode band-aid was tried and reverted as the
   wrong layer once the real cause was clear.
   (c) *Explicit canvas TOOLS (owner-proposed)* — as click semantics multiply (pan/trace/
   contacts now; regions at rung 4), a small per-canvas tool strip (Canvas / Walkmesh /
   Cut-outs; Behavior its own set; possibly anchor-vs-image sub-tools) beats implicit mode
   juggling. ★ **ADOPTED WITH RUNG 4** as mandated (`widgets.ToolStrip` on both click-authoring
   canvases); the Behavior stage's own set remains a possible follow-on.
   Also shipped this round: Generate is IN-PLACE after the first run (no dialog; writes a
   `.trace.json` session record); Open accepts that sidecar OR the project's own `field.toml`
   (backfilling the session from compiled artifacts when no sidecar exists yet); the Trace tab
   auto-loads / one-click-offers the field currently open in the Editor; edits since the last
   Generate show a "⚠ not stamped" status warning until re-stamped.
