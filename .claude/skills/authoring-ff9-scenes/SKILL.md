---
name: authoring-ff9-scenes
description: Author a NEW FF9 field's camera, walkmesh, pre-rendered background art, and its media assets. Use when the user runs `ff9mapkit new`/`build`/`camera`/`walkmesh`/`paint-template`/`repaint-native`, places/aligns a camera, builds/verifies/reshapes a walkmesh, paints/wires background layers, adds custom MUSIC or SFX (`audio-import`/`music-list`/`sfx-list`, `[music] song=`), SPS particle effects (`sps`, `[[sps]]`), or an FMV swap -- or hits content off-mesh, in a dead zone, misaligned on the art, a doubled FOV when scrolling, or a BG-borrow black screen. Covers the k=14/15 projection invariant and `cam.synth_r_t`, the scale-1 canvas (canvasX=rawProj.x+w/2, canvasY=h/2-rawProj.y), ground-offset 0 / `frame="world"`, the vert+orgPos+floor.org walkmesh frame, smaller-Z-in-front occlusion, and BG-borrow `area>=10`. The physical half of a novel field; for its `.eb` logic/NPCs/dialogue see `authoring-ff9-field-scripts`; to fork a real field's art see `forking-ff9-fields`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Authoring FF9 Scenes

Camera + walkmesh + painted-art placement for a novel field, authored from math. This is SOLVED — author from the formulas, never eyeball. The human owns final in-game alignment judgment (I cannot see the running game; after a visible change, stop and ask for a playtest).
A defect in the form editor or the Workspace's camera/scene panels themselves — as opposed to the math they emit — belongs to `working-on-the-ff9-workspace`.

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

## Field media assets -- music, SFX, particles, FMV

Shipped but easy to miss. All three are DLL-free loose-file overrides, and all three are routing targets, not recipes to re-derive here.

- **Custom music / SFX** — `music-list` / `sfx-list` show the song-id → ResourceID map (what you may replace); `audio-import <file> --song <id>` REPLACES an existing id, `audio-import <file> --new-song [--id N]` MINTS a new one (`--kind music|sfx`, `--deploy <modfolder>`). Any source format is transcoded to Ogg Vorbis; the engine wraps it into AKB2 at runtime. Play it from a field with `[music] song = <id>` (or `.eb RunSoundCode(0, <id>)`). **Two gotchas that eat a whole test:** `Memoria.ini [Audio] PriorityToOGG = 1` is REQUIRED (the bundled `.akb` always exists and wins otherwise — `audio-import` sets it unless `--no-set-priority`), and audio loads at STARTUP, so **RELAUNCH** — ~ → Reload will not pick it up. Also check the user's MusicVolume is not 0 before believing "I hear nothing". → memory `[[project-ff9-sound-music]]`; re-routing a field to an EXISTING song id instead → `[[project-ff9-verbatim-music]]`.
- **SPS particle effects** (fire/smoke/magic) — the `.sps` binary is fully decoded and round-trip proven. `ff9mapkit sps <field>` lists/decodes an effect, `--templates` lists the `[[sps]]` creator templates, `--png`/`--gif` render an offline preview (needs UnityPy). Canonical doc: `ff9mapkit/docs/SPS.md`; deep recipe → memory `[[project-ff9-sps-authoring]]`. Pixels live in a shared per-scene `spt.tcb`, not in the `.sps` — which is why a FORK must carry both; that fork-fidelity axis belongs to `forking-ff9-fields` (`[[project-ff9-sps-fork]]`).
- **FMV** — there is **no CLI verb**; the swap is a manual encode plus a loose drop at `<mod>/StreamingAssets/ma/FMV###.bytes` (Ogg/Theora, in-game proven on FMV000). ⚠ The load-bearing trap is the ENCODER, not the pipeline: the common `ffmpeg` build on PATH ships a BROKEN libtheora and produces garbage at every setting. Always decode-validate an encode (`ffmpeg -v error -i X.bytes -f null -` must report ZERO errors; a vanilla FMV is the 0-error oracle). Read `[[project-ff9-fmv-pipeline]]` BEFORE encoding anything — a brand-new FMV slot is blocked (the movie table has no `.eb` reach); reuse/repoint an existing one.

## Additional resources

- Docs (Layer 3): `ff9mapkit/docs/TECHNICAL.md` (§2 camera projection, §3 canvas map, §4 ground offset, §6 walkmesh frame), `ff9mapkit/docs/PIPELINE.md` (§2 camera + paint guide, §3 painting, §4 walkmesh, scrolling), `ff9mapkit/docs/WALKMESH_EDITING.md` (the obj+links reshape spec).
- Code (canonical): `ff9mapkit/ff9mapkit/scene/cam.py` (projection/canvas/yaw), `ff9mapkit/ff9mapkit/scene/bgi.py` (walkmesh codec).
- Memory (Layer 2): read `[[project-ff9-camera-math]]`, `[[project-ff9-import-frame]]`, `[[project-ff9-novel-bg-pipeline]]`; for media assets `[[project-ff9-sound-music]]`, `[[project-ff9-sps-authoring]]`, `[[project-ff9-fmv-pipeline]]` (+ `ff9mapkit/docs/SPS.md`).
- Offline gates: `ff9mapkit lint <toml>` / `ff9mapkit walkmesh verify <path>` — run them; I can't see the game.
