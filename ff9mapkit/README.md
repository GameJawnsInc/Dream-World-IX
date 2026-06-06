# FF9 Map Kit (`ff9mapkit`)

Author **novel custom field maps** for *Final Fantasy IX* (Steam, via the
[Memoria engine](https://github.com/Albeoris/Memoria)) from a single declarative
`field.toml`, compiled into a drop-in Memoria mod.

> **v0.9.3 — feature-complete and in-game-verified.** The productized form of a proven
> pipeline for minting brand-new playable FF9 fields, end to end. The output runs on a
> **stock, unmodified Memoria install** — no engine patching required.

**What's in the box:** custom camera angles (single / scrolling / multi-camera) · painted
background layers with depth + occlusion · hand-modeled *or* **imported-from-the-real-game**
walkmeshes (including multi-floor reshape) · NPCs with custom dialogue · gateways · random
encounters · events (chests / gil / story flags) · story branching · cutscenes (narration +
actor walk/turn/emote/teleport) — authored from one `field.toml`, a **form-based editor**, and
a **[Blender add-on](blender/README.md)**.

## What it does

Given a `field.toml` describing one field — its camera, painted background layers, walkmesh,
NPCs, dialogue, gateways, encounter, and music — `ff9mapkit build` emits everything a custom
field needs:

- the background scene (`.bgx` camera + overlay PNGs) and walkmesh (`.bgi`),
- the field event script (`.eb`) for all seven languages,
- dialogue text (`.mes`),
- and the `DictionaryPatch` / `BattlePatch` registration + `ModDescription.xml`.

## What stays a human task

By design the kit does **not** paint background art or model walkmesh geometry — those are
creative/3D tasks. Instead it gives you a **pixel-accurate paint guide** for your chosen
camera angle and converts your hand-modeled `.obj` walkmesh to the engine's `.bgi` format.

## Quickstart

```bash
pip install -e .
export FF9_GAME_PATH="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"

ff9mapkit doctor                              # verify it found your install
ff9mapkit new MY_ROOM --area 11               # scaffold a project
ff9mapkit guide --pitch 48 --png guide.png    # paint guide for your camera
# ... (human) paint art into MY_ROOM/art, fill in MY_ROOM/my_room.field.toml ...
ff9mapkit build MY_ROOM/my_room.field.toml --out dist --mod-name MyMod
ff9mapkit pack dist/MyMod --out MyMod.zip     # share it
```

> **`ff9mapkit` command not found?** Its Scripts dir may not be on your PATH. Use
> **`py -m ff9mapkit <command>`** instead — it's identical and works from any folder.

**Prefer not to touch TOML?** Author the *logic* (dialogue, events, story flags, encounters,
music, cutscenes) in a form-based editor instead:

```bash
ff9mapkit edit MY_ROOM/my_room.field.toml     # forms, dropdowns, a cutscene step list
```

The visual side has a front-end too — the [**Blender add-on**](blender/README.md) places the
camera, walkmesh, painted layers, and markers (NPCs, gateways, event zones, spawn) and writes the
`scene.toml`. So the suite splits cleanly: **Blender = where things are, the editor = what they do**,
and `build` compiles both.

## Commands

| command | what it does |
|---|---|
| `doctor` | resolve + sanity-check the game/mod paths |
| `new <name>` | scaffold a `field.toml` project + `art/` dir |
| `guide --pitch P` | author a camera, frame a flat floor, print/draw a paint guide |
| `camera <bgx>` | inspect a scene camera (`--regen` to round-trip it) |
| `walkmesh obj <in> <out>` | convert an `.obj` walkmesh to `.bgi`; `walkmesh fix` rebuilds neighbor links; `walkmesh verify` runs the checks |
| `disasm <eb>` | disassemble a field event script |
| `build <field.toml>...` | compile project(s) into a Memoria mod |
| `import <field>` | fork a **real** FF9 field into an editable `field.toml` (BG-borrow, or `--editable` custom scene) — also extracts its exits/encounters/BGM/movement |
| `list-fields [pat]` | list the real FF9 fields available to `import` |
| `edit [field.toml]` | open the **form-based logic editor** (no TOML hand-editing) |
| `lint <field.toml>` | check story-flag/placement logic without building |
| `pack <mod>` | zip a built mod for distribution |

## Docs

- [`docs/FORMAT.md`](docs/FORMAT.md) — the `field.toml` schema.
- [`docs/PIPELINE.md`](docs/PIPELINE.md) — the full authoring workflow.
- [`docs/ENGINE.md`](docs/ENGINE.md) — engine requirements (stock Memoria) + provenance notes.
- [`examples/vivi-hut/`](examples/vivi-hut) — a complete worked example.
- [`blender/`](blender/README.md) — the **Blender add-on**: visually author the camera + walkmesh,
  then export a `field.toml` for `build` (Blender 4.2+/5.x).

## How it's built / trusted

The library is split into `eb` (the event-script codec + content injectors), `scene`
(camera math, `.bgx`, `.bgi` walkmesh, paint guides), `build` (the `field.toml` compiler),
and `pack`. Correctness is proven by an **offline golden-master test suite**: every codec
round-trips real game assets byte-for-byte, and compiling the example reproduces an
in-game-verified field's script exactly.

```bash
pip install -e ".[dev]" && pytest      # the full suite
```
