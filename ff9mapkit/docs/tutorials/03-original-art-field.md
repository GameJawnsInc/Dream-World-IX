# 03 — An original-art field from scratch

```toml
[tutorial]
goal = "A from-scratch field with your own painted background."
requires = ["game", "image-editor"]
```

Author a field with a background you paint yourself: choose a camera, paint over a generated
guide, and walk on geometry projected through the same camera. This is the condensed recipe; the
full workflow reference (multi-layer depth, occlusion, scrolling, multi-camera) is
[PIPELINE.md](../PIPELINE.md).

**Prerequisites:** the kit set up ([SETUP.md](../../../SETUP.md)); an image editor that can export
PNG at fixed sizes.

## 1. Scaffold

```powershell
ff9mapkit new MY_ROOM --area 11
```

Creates `MY_ROOM\my_room.field.toml` (a commented template) and `MY_ROOM\art\` with placeholder
art (a solid backdrop + a perspective checkerboard floor matched to the template camera) and a
walkmesh quad derived from that camera. The project **builds immediately** — deploy the
placeholder first to verify the loop, then replace the art.

`--area` must be ≥ 10 (the background loader reads exactly two characters; areas 0–9 black-screen).

## 2. Choose a camera, get a paint guide

Real FF9 fields tilt down roughly 15–48°; steeper works.

```powershell
ff9mapkit guide --pitch 48 --distance 4500 --fov 42.2 --png MY_ROOM\art\guide.png
```

The guide renders the floor frame, a perspective grid, and height poles through the exact camera
projection — pixels painted on the guide land where the guide shows them. For per-layer trace-over
templates (one transparent PNG per depth layer plus a legend of every placed content item), use
`guide --template` or, once the `field.toml` has content, `ff9mapkit paint-template`.

## 3. Paint the layers

Paint over the guide and export at 4× the logical canvas: a full layer is **1536×1792** (logical
384×448). Typical split, back to front:

- `back.png` — everything behind the characters (walls, sky).
- `floor.png` — the ground plane.
- optional foreground layers — pieces that draw **in front of** the player (occlusion); smaller
  depth `z` = nearer to the viewer.

Wire them in `field.toml` under `[[layers]]` ([FORMAT.md](../FORMAT.md#layers-background-overlays-back-to-front)).

## 4. Walkmesh

The scaffolded flat quad already matches the camera. To shape real geometry, model a `.obj` in
Blender against the painted art (the [Blender add-on](../../blender/README.md) poses the camera
and exports directly), or keep the quad and adjust its extents in `[walkmesh]`. Validate with
`ff9mapkit walkmesh verify`.

Note the ~48-unit collision radius: the player's center cannot reach a walkmesh edge, so extend
the mesh past the painted floor where the player should reach the visual edge.

## 5. Content, lint, build

Add `[[npc]]` / `[[gateway]]` / `[[event]]` blocks as in [tutorial 01](01-first-fork.md), then:

```powershell
ff9mapkit lint MY_ROOM\my_room.field.toml
ff9mapkit build MY_ROOM\my_room.field.toml --out dist --mod-name MyRoom
```

Install and reach it as in [01 §5](01-first-fork.md#5-reach-it-in-game). A from-scratch field runs
on **stock, unmodified Memoria** — no engine bundle required.

Iterate on art alignment with the [dev loop](02-dev-loop.md): repaint → redeploy → ~ → Go →
Reload field. Final alignment (does the art land on the floor?) can only be judged in-game.

## Next

- Depth layers, light/shadow shaders, occlusion detail: [PIPELINE.md](../PIPELINE.md)
- Scrolling rooms and multiple cameras: [FORMAT.md](../FORMAT.md#camerascroll-optional--larger-than-screen-rooms)
- The complete worked example: `examples/vivi-hut/`
