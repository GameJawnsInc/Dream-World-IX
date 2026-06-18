# FF9 Map Kit (`ff9mapkit`)

Author **novel custom field maps** for *Final Fantasy IX* (Steam, via the
[Memoria engine](https://github.com/Albeoris/Memoria)) from a single declarative
`field.toml`, compiled into a drop-in Memoria mod.

> Part of the **[Dream World IX](../README.md)** project — `ff9mapkit` is the toolkit/package name
> (unchanged), `pip install`ed and imported as `ff9mapkit`.

> **Feature-complete and in-game-verified.** The productized form of a proven
> pipeline for minting brand-new playable FF9 fields, end to end. A **novel** field runs on a
> **stock, unmodified Memoria install**; a **forked** field needs the small bundled engine patch
> set for full fidelity (see [`docs/ENGINE.md`](docs/ENGINE.md)).

**Headline capabilities:** author **any camera angle** from scratch (single / scrolling / multi-camera)
with a pixel-accurate paint guide · **fork any of ~674 real fields** — camera, walkmesh, art, *and* its
exits/encounters/music · NPCs, dialogue, gateways, encounters, events, story branching, and cutscenes from
one `field.toml`. Author it in TOML, a **form-based editor**, or a **[Blender add-on](blender/README.md)**.

> **Full capability list & command reference → [`docs/FEATURES.md`](docs/FEATURES.md)** (with a before/now
> comparison) and [`SETUP.md`](../SETUP.md) (the 59-command CLI reference). [`docs/gallery/`](docs/gallery/)
> collects screenshots/GIFs as they're captured.

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

```powershell
pip install -e .                                 # from the ff9mapkit\ package dir
py -m ff9mapkit doctor                           # verify it found your FF9 install
py -m ff9mapkit import <field> --out myroom --verbatim   # fork a real field — or `new` for original art
```

> **Full setup → [`SETUP.md`](../SETUP.md)**: extras (`gui`/`save`/`dev`), game-path resolution, the
> one-time `extract-templates` (the kit ships no game data — see [Provenance](docs/PROVENANCE.md)),
> `doctor`, the dev loop, and a guided first-field walkthrough.

**Prefer not to touch TOML?** Author the *logic* (dialogue, events, story flags, encounters, music,
cutscenes) in the form-based editor — `ff9mapkit edit <field.toml>`. The visual side has a front-end too:
the [**Blender add-on**](blender/README.md) poses the camera, models the walkmesh, places markers, and
writes a `scene.toml`. So the suite splits cleanly — **Blender = where things are, the editor = what they
do** — and `build` compiles both. There's also a one-window [PySide6 Workspace GUI](../SETUP.md#6-the-gui-workspace-optional).

## Commands

59 subcommands — run `ff9mapkit -h` (or `py -m ff9mapkit -h`) for the full list. A taste of the families:

- **Author** — `new` (scaffold) · `guide` (paint guide for your camera) · `walkmesh` · `edit` (form editor)
- **Build & ship** — `build` · `lint` · `pack` · `export-art`
- **Fork a real field** — `import` (`--editable`/`--native`/`--verbatim`) · `import-chain` · `fork-report`
- **Campaigns & journeys** — `new-campaign` / `build-all` · `gen-hub` / `assemble-journey`
- **Battle maps & tuning** — `battle-import` / `battle-build` · `battle-scene` / `battle-ai`
- **Dialogue, catalogs & saves** — `dialogue` · `catalog` / `models` / `archetypes` · `flags-inspect` · `items-inspect`

> **The full grouped command reference (all 59, with flags) is in [`SETUP.md` §7](../SETUP.md#7-cli-command-reference).**

## Docs

- [`SETUP.md`](../SETUP.md) — **start here:** install, configure, the dev loop, and your first field (setup + quickstart).
- [`docs/TUTORIAL.md`](docs/TUTORIAL.md) — the focused ~10-minute first-field walkthrough.
- [`docs/FEATURES.md`](docs/FEATURES.md) — **the full capability list** (+ before/now comparison).
- [`docs/gallery/`](docs/gallery/) — collects screenshots/GIFs as they're captured.
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
