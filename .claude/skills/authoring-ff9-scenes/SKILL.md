---
name: authoring-ff9-scenes
description: Author a NEW FF9 field's camera, walkmesh, and pre-rendered background art from math. Use when the user runs `ff9mapkit new`/`build`/`camera`/`walkmesh`/`paint-template`/`repaint-native`, places/aligns a camera, builds/verifies/reshapes a walkmesh, paints/wires background layers, or hits content off-mesh, in a dead zone, misaligned on the art, a doubled FOV when scrolling, or a BG-borrow black screen. Covers the k=14/15 projection invariant and `cam.synth_r_t`, the scale-1 canvas (canvasX=rawProj.x+w/2, canvasY=h/2-rawProj.y), ground-offset 0 / `frame="world"`, yaw/control-direction, the vert+orgPos+floor.org walkmesh frame, `.bgi` ship-verbatim or reshape via obj+links, IsInQuad dead zones, COLLISION_RADIUS~=48, canvas 384x448/4x PNGs, smaller-Z-in-front occlusion, scrolling `window_width` vs `Range`, and BG-borrow `area>=10`. The physical half of a novel field; for its `.eb` logic/NPCs/dialogue see `authoring-ff9-field-scripts`; to fork a real field's art see `forking-ff9-fields`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Authoring FF9 Scenes

Camera + walkmesh + painted-art placement for a novel field, authored from math. This is SOLVED — author from the formulas, never eyeball. The human owns final in-game alignment judgment (I cannot see the running game; after a visible change, stop and ask for a playtest).

## Camera from math

Invariant: `R_ff9 = diag(1, 14/15, 1)·R_ortho` (vertical-focal aspect; **k = 14/15** is a global constant baked into orientation row 1). Author any camera via `cam.synth_r_t`. The canvas map is EXACT scale-1: `canvasX = rawProj.x + w/2`, `canvasY = h/2 − rawProj.y` (proven to 0.0005 px vs an in-engine probe). Character ground offset = 0 (engine-measured); new walkmeshes use `frame="world"` (org=0, no offset). Yaw: `R = rot_x(pitch)·rot_y(−yaw)` (post-multiply keeps the origin centred); control direction auto-derives: `value = round(yaw/360·256) − 1` (front-facing = −1). Detail + code pointers -> `references/camera-math.md`.

## Dead ends -- do not re-explore

- **Per-pitch `sx/sy` canvas scale** (0.926/0.889) — the map is exact scale-1; the old "back-edge drift" was the character collision radius, not a map error.
- **The editor's 5-point camera anchor solver on a flat floor** — mathematically degenerate (rank-deficient when every vertex has y=0). Use the math, not the editor, for cameras.

## Walkmesh frame

A real field's walkmesh world position = **`vert + orgPos + floor.org`** (universal; single-floor `floor.org=0`). Real `.bgi` floors are disjoint vertex sets, corner-origin per floor — rebuilding neighbor links by shared vertex INDEX loses cross-floor seams, so **ship the real `.bgi` verbatim** (codec lossless; only the `.obj` intermediate drops adjacency), or reshape via `obj + links` (the position-keyed seam sidecar). Detail -> `references/walkmesh-frame.md`.

## IsInQuad dead zones & collision radius

`IsInQuad`/`TreadQuad` test a FAN of consecutive vertex-triplets, not the real polygon — 3 collinear points = a zero-area triangle = a DEAD ZONE. Use a convex quad with the last vertex DOUBLED. `COLLISION_RADIUS_W ≈ 48` (= `bgiRad*4`): the player CENTRE can't reach a walkmesh edge — extend the walkmesh ~48u past the painted floor if the player should reach the visual edge.

## Painted art / overlay depth / occlusion

Logical canvas **384×448**; painted PNGs are **4× upscaled** (a full layer = 1536×1792). An overlay's `Position` = top-left logical px (Y-down), `Size` = px/4, `Z` = depth (**smaller Z = in front of the character** -> occlusion); overlay world placement is the scale-1 inverse of `to_canvas`. Detail -> `references/bg-art-canvas.md`. I cannot paint the art itself — the human paints; I say where via the projection math.

## Scrolling & multi-camera

Build `proj` from the visible **window width (384)** and only widen `Range` for a wider painting — naively widening `proj` DOUBLES the FOV (the kit's `[camera] window_width`). Camera cuts are script-driven: `SETCAM = 0x7E` switches the active camera, `BGCACTIVE = 0x71` enables scroll/camera-services; each camera needs its own control direction.

## BG-borrow area>=10

Mint via DictionaryPatch `FieldScene <id> <area> <MAPID> <NAME> <textid>`; point `<area>`+`<MAPID>` at a real field's art to borrow it. **`<area>` MUST be >= 10** — the loader builds `"FBG_N"+area` with no zero-padding and reads exactly 2 chars, so single-digit areas (0-9) black-screen. (`--editable` forks remap a low area to >=10.) Read memory `[[project-ff9-bg-borrow-solution]]`.

## Native seamless repaint

The `.bgx` editable-layer path has unavoidable 1px bilinear tile seams; **`--native`** (verbatim `.bgs` + atlas, no `.bgx`) is the seam-free path, and `repaint-native` makes the tile-packed atlas repaintable. Read memory `[[project-ff9-native-repaint-workflow]]`, `[[project-ff9-editable-scene-seams]]`.

## Additional resources

- Docs (Layer 3): `ff9mapkit/docs/TECHNICAL.md` (§2 camera projection, §3 canvas map, §4 ground offset, §6 walkmesh frame), `ff9mapkit/docs/PIPELINE.md` (§2 camera + paint guide, §3 painting, §4 walkmesh, scrolling), `ff9mapkit/docs/WALKMESH_EDITING.md` (the obj+links reshape spec).
- Code (canonical): `ff9mapkit/ff9mapkit/scene/cam.py` (projection/canvas/yaw), `ff9mapkit/ff9mapkit/scene/bgi.py` (walkmesh codec).
- Memory (Layer 2): read `[[project-ff9-camera-math]]`, `[[project-ff9-import-frame]]`, `[[project-ff9-novel-bg-pipeline]]`.
- Offline gates: `ff9mapkit lint <toml>` / `ff9mapkit walkmesh verify <path>` — run them; I can't see the game.
