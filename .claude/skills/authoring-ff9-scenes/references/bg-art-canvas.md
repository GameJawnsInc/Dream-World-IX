# Background art — canvas wiring, overlay depth/occlusion, scrolling

**Canonical prose:** `ff9mapkit/docs/PIPELINE.md` (§2 paint guide, §3 painting the layers, "Camera
movement & bigger environments" for scrolling); `ff9mapkit/docs/TECHNICAL.md` §3; memory
`[[project-ff9-novel-bg-pipeline]]` (the full `.bgx`/overlay/atlas story). The human paints; the kit
says WHERE via the projection math.

## Canvas wiring (quoted from the brief §7)

> Logical canvas **384×448**; painted PNGs are **4× upscaled** (a full layer = 1536×1792). An overlay's
> `Position` = top-left logical px (Y-down), `Size` = px/4, `Z` = depth (**smaller Z = in front of the
> character** → occlusion); overlay world placement is the scale-1 inverse of `to_canvas`.

- 384×448 is the camera `Range` (the painted canvas size); the visible PSX window is 320×224.
- The 4× upscale is the TileSize-64 install factor; the kit computes `upscale = TileSize//16`
  install-aware (vanilla TileSize 32 → 2×) — see the assembler notes in
  `[[project-ff9-novel-bg-pipeline]]`.
- Occlusion "just works": a foreground piece is a SEPARATE overlay at a small Z — the player walks
  under it and the PNG draws over his lower body. No depth hacks. The canonical depth mapping (from
  Memoria's own exporter, quoted from the memory): `z (Position depth) = scene.orgZ + overlay.orgZ +
  min(sprite.depth)`.
- Paint-guide flow: project the walkmesh with `cam.to_canvas` → the human paints the floor where it
  projects; `solve_z_for_canvasY` inverts a painted floor row back to world z (`ff9mapkit camera` /
  `paint-template`, PIPELINE.md §2).

## Scrolling (larger-than-screen paintings)

Build `proj` from the visible **window width (384)** and only widen `Range` for a wider painting —
naively widening `proj` DOUBLES the FOV. Kit lever: `[camera] window_width`. Scroll/camera-services are
enabled by the script opcode `BGCACTIVE = 0x71`; camera cuts use `SETCAM = 0x7E` (see
`references/camera-math.md` for the multi-camera pattern).

## Seams: `.bgx` editable vs `--native`

- The `.bgx` editable-layer path (one PNG per depth) loads each overlay Bilinear → unavoidable ~1px
  tile seams. Fine as a REPAINT surface, never fully seamless.
- **`--native` is the seam-free path**: ship `atlas.png` + the vanilla `.bgs.bytes` verbatim + a custom
  `.bgi`, and NO `.bgx` (a present `.bgx` is what FORCES the seamy path). Point-sampled atlas,
  per-tile-depth quads = faithful occlusion. `repaint-native` makes the tile-packed atlas repaintable.
- TileSize gotcha: the atlas MUST be packed at the ACTIVE Memoria.ini `TileSize` (vanilla 32 /
  Moguri 64) or it garbles — the kit sources the atlas from the active mod stack.
- Read memory `[[project-ff9-native-repaint-workflow]]`, `[[project-ff9-editable-scene-seams]]`.

## BG-borrow (reuse a real field's art) — area >= 10

DictionaryPatch: `FieldScene <id> <area> <MAPID> <NAME> <textid>`; point `<area>`+`<MAPID>` at a real
field's art. **`<area>` MUST be >= 10** — the loader builds `"FBG_N"+area` with no zero-padding and
reads exactly 2 chars, so single-digit areas (0-9) black-screen. `--editable`/`--native` forks remap a
low area to >=10 (~half the game is area<10). Read memory `[[project-ff9-bg-borrow-solution]]`.

## Debug gotcha

A custom field that THROWS on scene-load silently keeps rendering the PREVIOUS field's scene+camera
(the load exception is swallowed) — when a custom BG "looks like the room you came from", check
Memoria.log for cast/asset errors before touching the camera.
