# FF9 Map Kit (`ff9mapkit`)

Author custom *Final Fantasy IX* content (Steam/GOG, via the
[Memoria engine](https://github.com/Albeoris/Memoria)) from declarative TOML projects, compiled
into drop-in Memoria mods. Part of the **[Dream World IX](../README.md)** project.

**Capabilities:** author any field camera from scratch (single / scrolling / multi-camera) with a
pixel-accurate paint guide · fork any of **~674 real fields** — camera, walkmesh, art, exits,
encounters, music, and (verbatim mode) the real script and dialogue · NPCs, dialogue choices,
gateways, events, story branching, cutscenes, shops, save points from one `field.toml` · custom
**3D battle backgrounds** + battle tuning · multi-field **campaigns** and **journeys** ·
custom **3D character models** (Blender round-trip) and **playable characters** · **overworld**
terrain/coast/entrance authoring · custom **music/SFX** · save and story-state editing.

Authoring surfaces: TOML by hand, the form editor (`ff9mapkit edit`), the
[Blender add-on](blender/README.md), and the one-window
[PySide6 Workspace](../SETUP.md#6-the-gui-workspace-optional).

## What it does

Given a `field.toml` describing one field — camera, painted background layers, walkmesh, NPCs,
dialogue, gateways, encounter, music — `ff9mapkit build` emits everything a custom field needs:

- the background scene (`.bgx`/`.bgs` + overlay PNGs or atlas) and walkmesh (`.bgi`),
- the field event script (`.eb`) for all seven languages,
- dialogue text (`.mes`),
- the `DictionaryPatch` / `BattlePatch` registration + `ModDescription.xml`.

Battle maps (`battle.toml`), campaigns (`campaign.toml`), and journeys (`journeys.toml`) compile
the same way at their own scopes.

Two steps stay manual, matching how the original pre-rendered backgrounds were made: painting the
background art (over the kit's projected paint guide) and judging final in-game alignment. The
pipeline rationale is in [docs/PIPELINE.md](docs/PIPELINE.md).

## Quickstart

```powershell
pip install "ff9mapkit[assets]"                  # or from this dir: pip install -e ".[assets]"
ff9mapkit setup                                  # find the FF9 install, extract base assets
ff9mapkit import <field> --out myroom --verbatim # fork a real field — or `new` for original art
```

Full setup (extras, game-path resolution, the engine bundle) → [`SETUP.md`](../SETUP.md).
First-time walkthroughs → [`docs/tutorials/`](docs/tutorials/README.md).

## Commands

114 subcommands — `ff9mapkit -h` lists them; the grouped reference with flags is in
[`SETUP.md` §7](../SETUP.md#7-cli-command-reference). The families:

- **Setup** — `setup` · `doctor` · `extract-templates`
- **Author** — `new` · `guide` / `paint-template` · `walkmesh` · `edit` · `camera` · `disasm`
- **Build & ship** — `build` · `lint` · `pack` · `export-art` · `repaint-native`
- **Fork real fields** — `import` (`--editable`/`--native`/`--verbatim`) · `import-all` ·
  `import-chain` · `fork-report` · `list-fields` / `find-field` / `find-rooms` ·
  `logic-map` / `lint-eb`
- **Campaigns & journeys** — `new-campaign` / `add-field` / `build-all` / `lint-campaign` ·
  `gen-hub` / `lint-journey` / `assemble-journey` / `reference-arcs` ·
  `deploy-campaign` / `deploy-journey` / `newgame`
- **Battle** — `battle-import` / `battle-build` · `battle-list` / `battle-scene` / `battle-ai` /
  `battle-seq` · `battle-patch` / `characters` / `ability-gems` / `ability-features`
- **3D models** — `model-gltf` / `model-import` / `model-mint` / `model-anim` / `model-export` /
  `playable-anims`
- **Overworld** — `world-terrain` / `world-reclaim` / `world-coast` / `world-transplant` /
  `world-water` / `world-island` / `world-forest` / `world-hill` / `world-mountain` /
  `world-entrance` / `world-encounters` and the rest of the `world-*` suite
- **Audio** — `audio-import` · `music-list` / `sfx-list`
- **Catalogs & dialogue** — `catalog` / `models` / `animations` / `archetypes` / `items` /
  `scenes` / `flags` / `sps` · `dialogue` / `dialogue-import`
- **Saves** — `flags-inspect` / `flags-diff` / `save-edit` · `items-inspect` / `items-set-*`

## Docs

- [`SETUP.md`](../SETUP.md) — install, configure, the CLI reference.
- [`docs/tutorials/`](docs/tutorials/README.md) — single-goal walkthroughs (start with
  [01 — First fork](docs/tutorials/01-first-fork.md)).
- [`docs/FEATURES.md`](docs/FEATURES.md) — the full capability list.
- [`docs/FORMAT.md`](docs/FORMAT.md) — the `field.toml` / `battle.toml` schema reference.
- [`docs/PIPELINE.md`](docs/PIPELINE.md) — the from-scratch authoring workflow.
- [`docs/ENGINE.md`](docs/ENGINE.md) — stock vs. patched Memoria; the engine bundle.
- [`docs/FORK_FIDELITY.md`](docs/FORK_FIDELITY.md) — what forks do and don't reproduce.
- [`docs/PROVENANCE.md`](docs/PROVENANCE.md) — the kit ships no game data; how base assets are
  regenerated from the local install.
- [`docs/TECHNICAL.md`](docs/TECHNICAL.md) — the reverse-engineered foundations (camera math,
  `.eb` format, import frame).
- [`docs/GLOSSARY.md`](docs/GLOSSARY.md) — terms used across the docs.
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) · [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md)
- [`docs/gallery/`](docs/gallery/) — screenshots/GIFs.
- [`examples/vivi-hut/`](examples/vivi-hut) — a complete worked example.
- [`blender/`](blender/README.md) — the Blender add-on (camera, walkmesh, markers, model
  round-trip; Blender 4.2+/5.x).

## Validation

The package is organized by domain: `eb` (event-script codec + content injectors), `scene`
(camera math, `.bgx`/`.bgs`, `.bgi` walkmesh, paint guides), `build` (the `field.toml` compiler),
plus `battle/`, `world/`, `models/`, `content/`, deploy/journey orchestration, and the
`editor/`+`workspace/` front-ends.

Correctness is proven offline by a golden-master test suite (~2,850 tests): every codec
round-trips real install assets byte-for-byte (regenerated locally via `extract-templates` — the
repo ships none), and compiling the bundled examples reproduces in-game-verified output exactly.

```powershell
pip install -e ".[dev]"
py -m pytest -n 6
```
