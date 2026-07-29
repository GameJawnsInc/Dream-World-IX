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

### Rung 1 — floor tracing (parity with `--trace`)
Click to add polygon vertices, drag handles to adjust, pitch slider re-deriving the horizon from the
real camera math, live outset preview (+48u `COLLISION_RADIUS_W`), then call `build_image_field`.
**Verify:** `tools/gui_snap.py` → **read the PNG**; then build → `deploy_field.py --id <scratch>` →
walk it. Parity target: the hallway photo, re-done entirely in the GUI.

### Rung 2 — occluder contacts
Click a contact pixel → `occluder_z` → a `--foreground`-equivalent layer. Math ★ already in-game
proven (pillar room, contact (230,320) → z 1073, flip mid-room). Small rung; mostly UI.
**Guard:** error when `z ≥ Z_BASE 4000` (means the contact was traced up the body, not at the base) —
the existing CLI check, re-enforced at the new call site.

### ★ Rung 3 — placement on ANY field (the payoff)
Load an existing `field.toml` + its background + **its own camera**, and click to place NPCs, props,
spawn, arrival. Writes back to the toml.

This is what makes the tool general: it serves forks of real FF9 rooms, not just traced photos, and
it kills the error class that `laying-out-ff9-fields` exists to prevent (content packed under ~192u,
inverted cardinals because the camera sits at **negative z**).

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

### Rung 4 — regions drawn on the art
Gateway / trigger quads drawn directly on the background instead of typed as numbers. Carries the
existing region laws (tags 2/3/10, `IsInQuad` dead-zones) — the canvas should *render* a dead-zone
warning, not just accept the quad.

### Rung 6 (DEFERRED — the intended expansion, owner-decided 2026-07-28)
**A multi-room / floorplan composer, folded in here rather than built standalone.** Draw several
rooms on this canvas, declare which edges are doors, and get a wired dungeon: gateways both ways,
arrival position + facing per side, encounters, save-point siting.

> ★ **THE DRAWN-MESH LAW — the human draws the walkmesh; the composer never infers one.**
> Auto-deriving a walkmesh from an arbitrary field drawing is a research problem (segmentation,
> plane inference, semantic room boundaries — the same wall the `--auto-floor` hallway trial hit,
> where *where a field ends* proved SEMANTIC and un-inferable from one ground plane). Sequencing the
> composer AFTER this tool retires that problem entirely: geometry arrives hand-drawn and exact, and
> the composer is left with **topology only** — deterministic, testable, no inference.

This is why the composer is a rung here and not its own study: standalone it would need to generate
geometry; downstream of Rungs 0-3 it does not. **Do not start it before Rung 3 is real.**

### Rung 5 (bounded) — discrete multi-plane
Add `plane_y` to the un-projection (`s = (h - C.y)/ray.y`) so a field with several **flat** floors at
known heights can be authored per-floor, with a floor selector. **THE PLANE LAW (§1) is the ceiling:
if a surface's height varies across it, it is Blender's.** Rung 5 ships only if a real field wants it.

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
3. **Rung 1** — tracing parity; a Workspace host for the canvas (§5 call sites 1+3), polygon
   vertices + drag handles + pitch slider + outset preview + `build_image_field`; re-do the hallway
   photo entirely in the GUI, deploy, walk it. First `gui_snap` surface lands here.
4. **Scope Rung 3's UI** — measure real walkmesh floor heights first (the `plane_y` decision), then
   the field-card entry point (§5 call site 2) + surgical write-back (call site 4).
