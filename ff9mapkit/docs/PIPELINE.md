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

## What the kit does NOT do
- **Paint art** — you do (step 3). The kit only tells you where things land.
- **Judge walkmesh/camera alignment against the running game** — you verify that in-game.
