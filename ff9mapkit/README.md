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

> **The full capability list is in [`docs/FEATURES.md`](docs/FEATURES.md)** (with a before/now
> comparison), and [`docs/gallery/`](docs/gallery/) shows each feature in action.

## What it does

Given a `field.toml` describing one field — its camera, painted background layers, walkmesh,
NPCs, dialogue, gateways, encounter, and music — `ff9mapkit build` emits everything a custom
field needs:

- the background scene (`.bgx` camera + overlay PNGs) and walkmesh (`.bgi`),
- the field event script (`.eb`) for all seven languages,
- dialogue text (`.mes`),
- and the `DictionaryPatch` / `BattlePatch` registration + `ModDescription.xml`.

## What stays a human task — the way the originals were made

FF9's backgrounds are **pre-rendered**: the original artists built each room as a 3D scene, shot it
through a fixed camera to bake a 2D plate, and the game projects the live 3D characters back onto that
plate through the *same* camera. `ff9mapkit` deliberately follows that pipeline instead of hiding it.
You place the camera; the kit hands you a **pixel-accurate paint guide** — the floor and walls
projected onto the canvas, the modern stand-in for the layout render the original artists painted over
— and you paint the background to match. Your hand-modeled `.obj` walkmesh is converted to the
engine's `.bgi` and projected through that identical camera, so characters stand exactly where the art
says they should. Painting the art and (optionally) modeling the geometry stay yours; everything in
between is the kit.

## Quickstart

```bash
pip install -e .
export FF9_GAME_PATH="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"

pip install UnityPy                           # reads FF9's assetbundles (for the one-time step below)
ff9mapkit extract-templates                   # one-time: regenerate base assets from YOUR install
ff9mapkit doctor                              # verify it found your install + templates extracted
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
| `extract-templates` | one-time: regenerate the kit's base assets from **your own** FF9 install (the kit ships no game data — see [Provenance](docs/PROVENANCE.md)) |
| `edit [field.toml]` | open the **form-based logic editor** (no TOML hand-editing) |
| `lint <field.toml>` | check story-flag/placement logic without building |
| `pack <mod>` | zip a built mod for distribution |

## Docs

- [`docs/TUTORIAL.md`](docs/TUTORIAL.md) — **start here:** your first custom field in ~10 minutes.
- [`docs/FEATURES.md`](docs/FEATURES.md) — **the full capability list** (+ before/now comparison).
- [`docs/gallery/`](docs/gallery/) — each feature in action (screenshots / GIFs).
- [`docs/FORMAT.md`](docs/FORMAT.md) — the `field.toml` schema.
- [`docs/PIPELINE.md`](docs/PIPELINE.md) — the full authoring workflow.
- [`docs/ENGINE.md`](docs/ENGINE.md) — engine requirements (stock Memoria) + provenance notes.
- [`docs/PROVENANCE.md`](docs/PROVENANCE.md) — **the kit ships no game data**: how the base assets are
  regenerated from your own FF9 install (`extract-templates`), and why that's legally clean.
- [`docs/TECHNICAL.md`](docs/TECHNICAL.md) — the hard problems solved (camera math, `.eb` format, import).
- [`examples/vivi-hut/`](examples/vivi-hut) — a complete worked example.
- [`blender/`](blender/README.md) — the **Blender add-on**: visually author the camera + walkmesh,
  then export a `field.toml` for `build` (Blender 4.2+/5.x).

## How it's built / trusted

The library is split into `eb` (the event-script codec + content injectors), `scene`
(camera math, `.bgx`, `.bgi` walkmesh, paint guides), `build` (the `field.toml` compiler),
and `pack`. Correctness is proven by an **offline golden-master test suite**: every codec
round-trips your install's field assets byte-for-byte (regenerated locally via `extract-templates`
— the kit ships none), and compiling the example reproduces an in-game-verified field's script exactly.

```bash
pip install -e ".[dev]" && pytest      # the full suite
```

## About

I make games — including an FFIX-inspired RPG of my own — so this started as the tool I wanted while
learning how FF9's fields actually work, not a drive-by experiment. The aim was to build a new room
the way the game's creators did: paint a background against a 3D-derived guide, then walk on geometry
projected through the same camera — so authoring a field feels like level design rather than blind
byte-hacking. Months of reverse-engineering the field format, the projection math, and the event
bytecode went into making that the easy path. If you're poking at FF9's internals too, I hope it
saves you the same dig.

Built on (and grateful for) the [Memoria engine](https://github.com/Albeoris/Memoria) — none of this
is possible without it.
