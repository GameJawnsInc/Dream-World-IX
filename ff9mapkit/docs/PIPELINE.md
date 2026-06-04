# Authoring pipeline — from idea to playable field

This walks the full workflow. Two steps are **human** (Hard Constraint): painting the
background art, and (optionally) modeling the walkmesh in a 3D tool. The kit owns everything
else — the camera math, the paint guide, the `.obj`→`.bgi` conversion, the script, and packaging.

```
                 ┌─────────────┐
  choose camera →│ ff9mapkit   │→ paint guide PNG ──▶ (human) paint layers
                 │   guide     │                          │
                 └─────────────┘                          ▼
  model walkmesh.obj ──────────────────────────▶  write field.toml
  (or let the kit frame a flat quad)                       │
                                                           ▼
                                                  ┌─────────────┐
                                                  │ ff9mapkit   │→ mod folder → install → playtest
                                                  │   build     │
                                                  └─────────────┘
```

> **Prefer to work visually?** The [Blender add-on](../blender/README.md) is a front-end for
> steps 2 and 4 (the camera + walkmesh): pose the camera in the 3D viewport, model the walkmesh
> against your painted art, place NPC/gateway/spawn markers, and one-click *Export Field* to a
> `field.toml` you then `build` exactly as below. The CLI steps here are the ground truth either way.

## 0. Install

```bash
pip install -e .
export FF9_GAME_PATH="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
ff9mapkit doctor          # confirm it found your install
```

The output runs on a **stock, unmodified Memoria install** — see [ENGINE.md](ENGINE.md).

## 1. Scaffold

```bash
ff9mapkit new MY_ROOM --area 11
```

Creates `MY_ROOM/my_room.field.toml` (a commented template) + `MY_ROOM/art/`.

### …or fork a REAL field instead of starting blank

To start from one of FF9's ~674 real fields (needs `pip install UnityPy`):

```bash
ff9mapkit list-fields grotto              # find a field
ff9mapkit import glgv_map792_gv_rm1 --out MY_FORK            # BG-borrow: reuse its art/walkmesh/camera
ff9mapkit import glgv_map792_gv_rm1 --out MY_FORK --editable # editable custom scene (see below)
```

- **BG-borrow** (default) renders the real field's art + walkmesh + camera and runs your script on top — fastest, but the art is not editable.
- **`--editable`** forks it into a full custom scene you can repaint: the walkmesh is re-exported to `walkmesh.obj`, and the background is split into **one `layer_*.png` per depth** (occlusion preserved — foreground pieces still draw over the player). Repaint any single layer, reshape the walkmesh, add content, then `ff9mapkit build`. Requires the field to have been exported in-game once via `Memoria.ini [Export] Field=1` (so the per-overlay PNGs exist on disk); additive light/shadow overlays are skipped in this first pass.

Either way you get a ready-to-edit `field.toml` — skip to step 5.

## 2. Choose a camera and get a paint guide

Decide the angle. Real FF9 fields tilt down `~15–48°`; steeper (top-down) also works.

```bash
ff9mapkit guide --pitch 48 --distance 4500 --fov 42.2 --png MY_ROOM/art/guide.png
```

This prints the floor's world extent and **exactly where its corners/edges land on the
384×448 painted canvas**, and writes a checkerboard guide PNG. It also prints the walkmesh
corners for that frame.

## 3. (Human) paint the background layers

Paint over the guide. Typical layers, back-to-front:
- a **back** layer (everything behind the player),
- a **floor** layer,
- optionally a **front** layer with a small `z` so it draws *over* the player (occlusion).

Logical canvas is 384×448; export at 4× (1536×1792) for crispness. Save PNGs (RGBA, with
transparency where the layer shouldn't cover) into `MY_ROOM/art/`.

## 4. The walkmesh

Either:
- model it in Blender in **FF9 world coords** (x, y=0, z), export `.obj`, set `walkmesh.obj`; or
- use a flat `walkmesh.quad` (the 4 corners the guide printed); or
- omit it and let the kit auto-frame a quad from `[camera.frame]`.

`ff9mapkit walkmesh obj mesh.obj out.bgi.bytes` converts an `.obj` directly; the kit also
rebuilds the triangle-neighbor links Memoria's editor gets wrong.

## 5. Fill in `field.toml`

Layers, walkmesh, player spawn, NPCs + dialogue, gateways, an encounter, music — see
[FORMAT.md](FORMAT.md). See `examples/vivi-hut/hut_int.field.toml` for a complete worked example.

## 6. Build

```bash
ff9mapkit build MY_ROOM/my_room.field.toml --out dist --mod-name MyMod
```

Produces a complete mod folder: the background scene, the walkmesh, the 7-language event
script, dialogue text, and the DictionaryPatch / BattlePatch / ModDescription.

## 7. Install + playtest

Copy the built folder into the game install (next to `FF9_Launcher.exe`), or build with
`--out` pointing straight at the game's mod folder. Reach the field via a gateway from a
real field (add a `[[gateway]]` to it in an existing field, or use a debug warp) and play.

```bash
ff9mapkit pack dist/MyMod --out MyMod.zip      # to share it
```

## Camera movement & bigger environments

FF9 fields are **fixed-perspective pre-rendered art** — the angle is baked into the painting and
is never re-rendered from a new viewpoint at runtime. What looks like "camera movement" in the
real game is one of three things:

1. **Scrolling.** Most rooms are *larger than the screen*: one big fixed-perspective painting, and
   the engine pans the view window across it to follow the player (`SceneService2DScroll`/`3DScroll`
   in the engine). The angle never changes — only the 2D scroll offset does.
2. **Multiple cameras per field.** A field's scene can hold more than one camera block, each with
   its **own** pre-rendered art for a different part of the room; crossing a zone boundary *switches*
   cameras (a cut, or scroll-then-switch). That's how a room shows two genuinely different angles —
   two paintings, not a moving 3D camera.
3. **Scripted cutscene pans** — animated pan/zoom *over* the big pre-render (the cinematic stuff is
   pre-rendered FMV).

So when you author with this kit you **set one pose and paint one perspective** — that pose + painting
is the unit. Make a single screen feel alive with depth layers (foreground occlusion), animated
overlay sprites (torches/water), and lighting baked into the art — not by moving the camera.

### Scrolling rooms (larger-than-screen) — supported

A room whose painting is **bigger than the screen** scrolls the view to follow the player. The
engine does the panning automatically; you just paint a bigger canvas and flip a flag:

```toml
[camera]
range = [768, 448]      # the painting is 2× the screen wide
window_width = 384      # keep the focal length normal (don't widen the FOV)
[camera.scroll]
enabled = true          # auto scroll bounds + the engine's EnableCameraServices
```

`ff9mapkit guide` (and the demo generator) auto-size the **paint guide to the full painting**, with
**height guides** (poles/rings/room-box at the floor edges) so you can paint walls in correct
vertical perspective — not just a floor. Make the walkmesh span the painting; the kit auto-derives
the scroll bounds and injects the enable opcode. Runs on **stock Memoria**. Proven in-game on a
768×448 room (see `examples/scroll-demo/`). For an even bigger space, **chain scrolling rooms with
gateways**.

**Still future:** **multi-camera** switch zones (one field, several pre-rendered angles switched at
trigger zones) — the engine supports it (`SETCAM`), and the scene format already parses N cameras;
the kit doesn't yet author the switch script.

## What the kit does NOT do
- **Paint art** — you do (step 3). The kit only tells you where things land.
- **Judge walkmesh/camera alignment against the running game** — you verify that in-game.
