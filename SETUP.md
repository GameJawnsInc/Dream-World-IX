# ff9mapkit — Setup & Reference

> Commands are written for **Windows PowerShell** (the primary platform); bash equivalents differ
> only in how environment variables are set.

`ff9mapkit` is a Python toolkit (plus a Blender add-on) that compiles declarative TOML projects
into complete drop-in [Memoria](https://github.com/Albeoris/Memoria) mods: custom **fields**
(camera, walkmesh, painted art, NPCs, dialogue, gateways, encounters, events, cutscenes), forks of
any of FF9's ~674 **real fields**, custom **battle backgrounds**, multi-field **campaigns** and
**journeys**, custom **3D models**, **overworld** edits, and custom **music/SFX**.

Engine requirements are split: a **novel** field (and models/battle/audio content) runs on a
**stock, unmodified Memoria install**; a **forked** field needs the small bundled engine patch set
for fidelity, and overworld authoring needs its mesh-override patch — see
[`ff9mapkit/docs/ENGINE.md`](ff9mapkit/docs/ENGINE.md).

---

## 1. Prerequisites

| Need | Detail |
|---|---|
| **Python ≥ 3.11** | Hard floor — the kit uses stdlib `tomllib` (3.11+). Not needed with the Windows installer (it bootstraps its own via `uv`). |
| **A legally-owned FF9 (Steam or GOG) + Memoria** | The kit reads base assets *from your install*; it bundles zero game bytes. Steam and GOG are the same moddable Unity port (both auto-detected). The Microsoft Store / Game Pass version is **not** moddable. |
| **Pillow ≥ 9.0** | The only hard runtime dependency (composites art layers, renders paint guides). Installed automatically. |

**Back up the clean game folder before anything else.** Copy the entire `FINAL FANTASY IX`
install somewhere safe — it is the only true reset if a deploy corrupts something.

Optional extras:

| Extra | Installs | Unlocks |
|---|---|---|
| `assets` | `UnityPy` | Everything that reads FF9's `p0data*.bin` bundles: `extract-templates`, the `import`/fork family, `list-fields`, `battle-import`, `model-*`, `world-*` extraction, `sps`. |
| `gui` | `PySide6-Essentials ≥ 6.5` | The desktop Workspace (`ff9mapkit-workspace`, or `apps/ff9_workspace.pyw` from a checkout). Essentials (not the full meta-package) keeps the LGPLv3 path clean. |
| `save` | `pycryptodome ≥ 3.10` | `save-edit` and the save-editing family (FF9's AES-encrypted saves). Imported lazily. |
| `dev` | `pytest`, `pytest-xdist` | The offline test suite (`py -m pytest -n 6`). |

Install paths, pick one:

- **Windows installer** (non-developers): `DreamWorldIX-Setup.exe` from the GitHub Releases page —
  a `uv` bootstrap that needs no system Python, runs `ff9mapkit setup` for you, and can install
  the engine bundle. See [`installer/README.md`](installer/README.md).
- **PyPI:** `pip install "ff9mapkit[gui,assets,save]"` (pick the extras needed).
- **Source checkout:** see §2.1.

## 2. Setup (one time)

> **Fast path:** after installing, run **`ff9mapkit setup`**. It auto-detects the FF9 install,
> persists it in `~/.ff9mapkit.toml`, runs `extract-templates`, and reports the Memoria engine
> status — §2.2–§2.4 in one shot. If the install isn't auto-found, pass the global game flag
> *before* the subcommand: `ff9mapkit --game "<path>" setup`. Add
> `--install-engine <dwix-custom-memoria.zip>` to also install the engine bundle (with DLL
> backups; needed only for *forked* fields). The manual steps below are what `setup` does.

### 2.1 Install from source

The install must run **from the package directory** (`ff9mapkit/`, where `pyproject.toml` lives),
not the repo root:

```powershell
cd ff9mapkit
pip install -e ".[assets]"
# …or with more extras:
pip install -e ".[dev,save,gui,assets]"
```

This registers a console script, so `ff9mapkit <cmd>` works anywhere. If it isn't on PATH,
**`py -m ff9mapkit <cmd>` is identical** and is the safer form when several Pythons are installed
(run it from the package directory so the local checkout shadows any other install).

### 2.2 Point the kit at the FF9 install

Resolution order: **`--game` flag → `$FF9_GAME_PATH` → `~/.ff9mapkit.toml` → auto-detect**.
Auto-detect reads the Steam and GOG registry keys, scans Steam `libraryfolders.vdf`, then falls
back to common locations (`Program Files (x86)\Steam\...`, `D:\SteamLibrary\...`, `C:\GOG Games`,
GOG Galaxy). A default-location install is found without configuration.

To set it explicitly (PowerShell — `$env:`, **not** bash `export`):

```powershell
# this session only:
$env:FF9_GAME_PATH = "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"

# persist for future sessions (user-scoped):
[Environment]::SetEnvironmentVariable("FF9_GAME_PATH",
  "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX", "User")
```

Or persist it in `C:\Users\<you>\.ff9mapkit.toml`:

```toml
game_path = "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
```

### 2.3 Regenerate base assets from the install

The repo ships **no Square-Enix bytes**. The base assets builds start from (the blank field, the
exit-region template, test fixtures) are *derived* from FF9's own data via copy/insert patches +
a SHA-256 manifest. `extract-templates` reads the install, applies the patches, and verifies
every output:

```powershell
py -m ff9mapkit extract-templates
# → "OK -- <N> assets regenerated + verified against the manifest."
```

Run **once per checkout** (the extracted files are gitignored, so each new checkout or worktree
needs its own run). Until it runs, byte-level commands raise a "run extract-templates" message
and the byte-level tests skip. For a read-only install location, point `$env:FF9MAPKIT_DATA` at a
writable cache directory.

### 2.4 Verify

```powershell
py -m ff9mapkit doctor
```

Prints the kit version, UnityPy presence, the resolved game install (launcher + StreamingAssets),
the mod root + `DictionaryPatch.txt`, and `templates : extracted`. If templates report
`NOT extracted`, re-run §2.3. `doctor` exits non-zero if the game path can't be resolved
(`ff9mapkit --game <path> doctor` overrides). The Workspace GUI surfaces the same checks in its
Setup & Health dialog.

### 2.5 (optional) Run the test suite

```powershell
pip install -e ".[dev]"
py -m pytest -n 6        # ~2,850 offline golden-master tests
```

### 2.6 Updating & uninstalling

**Installed via the `.exe` / `uv`:**

- **Update** — `uv tool upgrade ff9mapkit` (pulls the latest PyPI release), or the Workspace's
  *Upgrade & restart* button. Re-running a newer `DreamWorldIX-Setup.exe` upgrades in place (same
  app id; no uninstall first) and is needed when a release ships a new engine bundle.
- **Uninstall** — *Settings → Apps* → **"Dream World IX"**, or the Start-Menu uninstaller
  (`uv tool uninstall ff9mapkit` + the installer's files).

Uninstall intentionally leaves in place: `uv` and its managed Python (shared), settings +
extracted assets in `%LOCALAPPDATA%\ff9mapkit`, and any engine patches applied to the **game**
(a separate Memoria mod — restore stock DLLs from
`<FF9>\dwix-engine-backups\<timestamp>\`, or re-run the Memoria patcher).

**Installed editable:** update with `git pull` + re-run `pip install -e ".[…]"`; uninstall with
`pip uninstall ff9mapkit` (the checkout and `~/.ff9mapkit.toml` stay).

---

## 3. Orientation

### The labor split

| The kit owns (math + bytes) | Manual (cannot be automated) |
|---|---|
| Camera (pitch/yaw/FOV — the projection math) | **Painting background art** + its depth layers |
| Walkmesh (walkable + depth geometry) | **Final in-game alignment** (does the art land on the floor?) |
| Logic: event script (`.eb`), NPCs, dialogue, gateways, encounters, events, cutscenes, flags | **Playtesting** |

The toolkit cannot see the running game. It validates everything it can offline (`lint`) and emits
a pixel-accurate paint guide for the exact camera; anything visible in-game is verified by the
loop **build → deploy → playtest**.

### The fork spectrum

Four `import` modes trade editability for faithfulness — **`--verbatim`** to *play* it the same,
**`--editable`** to *change* it:

| Mode | Ships | Use when |
|---|---|---|
| `import` (BG-borrow) | real art/walkmesh/camera under **your own** script | a real-looking backdrop, all-new logic |
| `--editable` | a repaintable custom scene (per-depth layers, occlusion kept) | repainting or reshaping the room |
| `--native` | per-tile scene (vanilla `.bgs` + atlas, no `.bgx`) | faithful art without tile seams — the recommended art fork |
| `--verbatim` | the field's **whole real `.eb` + `.mes`** (only `Field()` warps remapped) | it should **play** like the original |

### The authoring surfaces

**`field.toml`** is the logic file (what exists, what it does) — by hand, `ff9mapkit edit`, or
the Workspace (§6). The **Blender add-on** owns the spatial file (**`scene.toml`** — camera,
walkmesh, markers); the two merge at build. Campaigns (`import-chain` + `campaign.toml`) and
journeys (`journeys.toml` + a generated hub field) scale the same model to multi-field mods —
see [tutorials 04–05](ff9mapkit/docs/tutorials/README.md).

### Id bands & the global-id rule

Custom field ids are **≥ 4000** (default test slot `4003`). The engine's registries merge across
mod folders, so **ids must be globally distinct even across stacked folders** — a reused id makes
one field load a null script (black screen). The id cap is Int16 (**32767**). Full id / flag /
text namespaces: [`ff9mapkit/docs/GLOBAL_RESOURCES.md`](ff9mapkit/docs/GLOBAL_RESOURCES.md).

---

## 4. The dev loop

The fast iteration loop — **edit → deploy → ~ reload**, no relaunch per change — is
[tutorial 02](ff9mapkit/docs/tutorials/02-dev-loop.md). Summary:

```powershell
py tools\deploy_field.py myroom\MYROOM.field.toml    # sandbox any field.toml into test slot 4003
# in-game: ~ → Go → Reload field   (or Warp to field → <id>)
```

A relaunch is only needed for: the first deploy of a new id, a `BattlePatch.txt` change,
start-state CSVs / `TextPatch.txt`, or an engine DLL change. Revert with
`py tools\scroll_out\revert_deploy.py` (or the per-id `revert_deploy_<id>.py`).

Campaigns/journeys: `ff9mapkit deploy-campaign` / `deploy-journey` (or the `tools\` shims from a
checkout) are dry-run by default (`--apply` to write); `ff9mapkit newgame` writes immediately
(`--dry-run` to preview).

The **shipped path** needs none of this: `ff9mapkit build … --mod-name MyMod`, copy the folder
into the game install, register it in `Memoria.ini [Mod] FolderNames` **and** `Priorities` (same
order — the Memoria Launcher rewrites `FolderNames` from `Priorities` at every Play click, so a
`FolderNames`-only edit silently reverts; launching once also auto-detects the folder, the hand
edit just controls the order), launch.

---

## 5. First field

Walkthroughs live in **[`ff9mapkit/docs/tutorials/`](ff9mapkit/docs/tutorials/README.md)**:

- **[01 — First fork](ff9mapkit/docs/tutorials/01-first-fork.md)** (fastest; no painting):

  ```powershell
  py -m ff9mapkit list-fields glgv
  py -m ff9mapkit fork-report glgv_map792_gv_rm1_0 --explain     # optional preview
  py -m ff9mapkit import glgv_map792_gv_rm1_0 --out myroom --name MYROOM --verbatim
  py -m ff9mapkit lint myroom\MYROOM.field.toml
  py -m ff9mapkit build myroom\MYROOM.field.toml --out dist --mod-name MyFirstField
  ```

- **[03 — Original-art field](ff9mapkit/docs/tutorials/03-original-art-field.md)** (from
  scratch): `new` → `guide` → paint → `build`. Deep reference:
  [`docs/PIPELINE.md`](ff9mapkit/docs/PIPELINE.md).

---

## 6. The GUI Workspace (optional)

One PySide6 window folding every authoring tool together. **Optional — the CLI does everything
without it.**

```powershell
pip install "ff9mapkit[gui]"
ff9mapkit-workspace                  # installed launcher (also the Start-Menu shortcut)
py apps\ff9_workspace.pyw            # from a repo checkout
py apps\ff9_workspace.pyw --smoke    # headless self-check
```

Built around a **journey ▸ campaign ▸ field ▸ object** tree with a breadcrumb, a tabbed document
area, a right-hand Inspector (with live field-art thumbnails), and a bottom Output/Problems
console:

- **Tabs:** **Editor** (field/NPC/gateway/event/chest/flag/party/startup/cutscene/choice/SPS
  forms, catalog picker, live FF9-window dialogue wrap preview, undo/redo) · **Map** (campaign
  graph) · **Story State** + **Item & Equip** (save editors) · **Battle** (encounter-first battle
  tuning) · **Build & Deploy** (field/campaign/journey/battle, auto-detected; pack-to-zip; New
  Game wiring) · **Import** (fork + fork-report + pre-fork logic study + import-all archive +
  custom-3D-models flow + native repaint).
- **Chrome:** a Home screen with recent projects; **Ctrl-K** command palette; an **Info Hub**
  model/prop/creature library with ready-to-paste snippets; a **Setup & Health** page (install
  detection, template extraction, engine status); **F9** one-keystroke deploy; drag-and-drop
  open; a 7-theme picker + Preferences; an opt-in once-a-day update check with one-click
  *Upgrade & restart*; session/layout restore.

> **Installed vs. repo.** The installed Workspace is the end-user front door (Build → *Install to
> game*, campaign/journey deploy, *Point New Game here*). The dev test slot (4003) + the ~ reload
> loop need the repo's `tools/`, so they are hidden on an installed copy — set **`FF9_REPO`** to a
> Dream World IX checkout (or launch from inside one) to light them up.

---

## 7. CLI command reference

114 subcommands, invoked as `ff9mapkit <cmd>` or `py -m ff9mapkit <cmd>`. Global flags —
`--game <path>`, `--mod-folder <name>`, `--version` — go **before** the subcommand
(`ff9mapkit --game <path> doctor`). Commands that read FF9's asset bundles need the `assets`
extra (UnityPy).

**Setup / doctor**

| command | what it does |
|---|---|
| `setup` | One-shot: find the FF9 install, remember it, extract base assets, report Memoria status (`--install-engine ZIP`, `--force`, `--no-extract`). |
| `doctor` | Resolve paths + sanity-check the install (game/mod paths, templates extracted). |
| `extract-templates` | Regenerate base assets from the local install (`--no-fixtures` = templates only). |

**Author a field**

| command | what it does |
|---|---|
| `new <name>` | Scaffold a field project (`--area` ≥ 10, default 11; `--id`, `--pitch`). |
| `guide` | Author a camera + emit a paint guide (`--pitch/--distance/--fov`, `--png`, `--template`). |
| `paint-template` | Project a field.toml's floor + content onto per-layer trace-over PNGs + a legend. |
| `camera <bgx>` | Inspect / regenerate a `.bgx` camera (`--regen OUT.bgx`). |
| `walkmesh <obj\|fix\|verify>` | Convert `.obj`→`.bgi`, rebuild neighbor links, or run checks. |
| `edit [field]` | Open the form-based logic editor. |
| `disasm <eb>` | Disassemble a `.eb` field script (`-e N`, `-a`). |

**Build & ship**

| command | what it does |
|---|---|
| `build <field…>` | Compile project(s) into a Memoria mod (`--out`, `--mod-name`, `--author`). |
| `lint <field>` | Every offline validator in one pass (schema, flags, geometry, layers, camera). |
| `pack <mod>` | Zip a built mod for distribution (`--out`, `--name`). |
| `export-art [target]` | Assemble a field's background PNGs offline (`--all`, `--composite`). |
| `repaint-native <fork>` | Unpack a native fork's atlas into repaintable layers; `--pack` re-packs seamlessly. |

**Fork / import real fields**

| command | what it does |
|---|---|
| `import <field>` | Fork a real field (`--editable` / `--native` / `--verbatim`, `--swap-player`, `--dialogue`, `--carry-text`, `--id` def 4003). |
| `import-all` | Bulk-import a foldered, Blender-ready archive — whole game / `--pattern` zone (`--editable`). |
| `import-chain <seed>` | Fork a connected region into a campaign (`--zones`, `--whole-zone`, `--ids <ranges>`, `--verbatim`, `--id-base`, `--out`). |
| `fork-report <field>` | Preview a fork's fidelity offline (`--explain` decodes NPC talk routines). |
| `list-fields [pat]` | List real fields available to import (`--players`, `--non-zidane`). |
| `find-field <q>` | Resolve a field id / name / FBG substring. |
| `find-rooms` | Sweep all fields for the best swap/demo test rooms. |
| `logic-map <field>` | Read-only legible map of a real field's whole `.eb` (entries, call graph, effects). |
| `lint-eb <field>` | Structurally lint a `.eb` — the offline soundness check for verbatim edits. |
| `extract-field <ids…>` | Cache a real field's camera+walkmesh in the workspace cache. |

**Campaigns / journeys**

| command | what it does |
|---|---|
| `new-campaign <dir>` / `add-field <camp>` | Create an empty campaign / add a member field. |
| `build-all <camp>` / `lint-campaign <camp>` | Compile / validate a `campaign.toml`. |
| `gen-hub <journeys>` | Generate a World-Hub selector field from a `journeys.toml`. |
| `lint-journey` / `assemble-journey` | Validate / assemble a multi-campaign journey (the namespace guarantee). |
| `reference-arcs` | Scaffold FF9's real story arcs: list the arc table, print the fork playbook, or emit a chained `journeys.toml`. |
| `deploy-campaign <camp>` | Reversibly install a built campaign + wire New Game (dry-run by default; `--apply`). |
| `deploy-journey <journeys>` | Deploy a journey: campaigns + links + hub, one revert (dry-run by default; `--apply`). |
| `newgame <id>` | Point New Game at a deployed field id (field-70 override; FMV preserved; `--retarget`). |

**Battle backgrounds & tuning**

| command | what it does |
|---|---|
| `battle-import <bbg>` | Fork a real battle background → editable FBX + `battle.toml` (`--fork-scene`, `--ship-as`). |
| `battle-build <toml>` | Compile a `battle.toml` into a mod. |
| `battle-list` | List battle backgrounds (and `--scenes`). |
| `battle-scene <donor>` | Inspect a battle scene's enemy data (stats/affinities/rewards/attacks). |
| `battle-ai [donor]` | Disassemble enemy AI (read-only; `--asm`/`--asm-block`/`--lint`). |
| `battle-seq <scene>` | Disassemble / lint / assemble attack choreography (`btlseq.raw17`). |
| `battle-patch [toml]` | Preview the `BattlePatch.txt` a field emits (`--fields`). |
| `battle-actions` | List shared player abilities + the scriptId formula catalog. |
| `characters` / `ability-gems` | List stat / gem-cost tuning targets. |
| `ability-features` | Preview the `AbilityFeatures.txt` a field emits (ability-effect DSL). |

**Custom 3D models**

| command | what it does |
|---|---|
| `model-gltf <model>` | Export a real model + animations to Blender-openable glTF (`--anims auto\|all\|none\|…`). |
| `model-import <glb>` | Bring an edited glTF back as a loose-FBX override (`--like`, `--id`, `--deploy`, `--no-anims`). |
| `model-mint <source>` | Mint a NEW additive GEO model id (≥ 6000) from a source model (`--id`, `--deploy`). |
| `model-anim <model>` | Dump/deploy animation clips as editable loose `.anim` JSON. |
| `model-anim-new <model>` | Author a wholly NEW clip (a Blender `.glb` action, or the spin demo) — registered via `3DModelAnimation`. |
| `image-field <image>` | *Experimental:* synthesize a walkable field from an image + a hand-traced floor polygon (`--floor`). |
| `model-preview <model>` | Software-render a model to a PNG still (textured, posed at its stand clip). |
| `model-reskin <model>` | The cheapest edit: export a model's textures / deploy edited PNGs as a loose reskin. |
| `model-deployed <mod>` | List (or `--revert` one of) a mod folder's loose model overrides / reskins / mints / anim overrides. |
| `model-export <model>` | Export a raw skinned FBX (the non-glTF path). |
| `playable-anims <field>` | Route edited donor clips onto a custom playable character's own minted animset. |
| `summon-export <ef>` | *Experimental:* export a stock summon creature's `ef###.bytes` → a Blender-openable glTF (rig + skin + motion clips; `--anims`, `--rest`). Output is **local-only by design** (a stock export is Square-Enix content — it refuses a repo / mod-folder / install path, no `--force`). |
| `summon-rig-ref <ef>` | *Experimental:* export ONLY a summon's rig reference (`bone000..bone09N`, no mesh, no clips) to skin your own mesh onto. Output is **local-only by design** (same refusal — the rig is stock-derived). |

**Overworld** *(the mesh-writing commands — `world-terrain`, `world-reclaim`, `world-coast`,
`world-transplant`, `world-fuse`, `world-island`, `world-forest`, `world-hill`,
`world-mountain`, `world-water`, `world-entrance`, `world-deploy`, `world-mesh-build`,
`world-mirror` — need the engine bundle's `s34` mesh-override patch; the atlas/texture,
encounter, environment, marker, and minimap commands are stock-engine)*

| command | what it does |
|---|---|
| `world-terrain` | Reshape walkable terrain (hill/crater/ridge/flatten) across blocks, seamlessly. |
| `world-reclaim` | Reclaim ocean cells as walkable land. |
| `world-coast` | Place a real FF9 coastal block (terrain + animated beach/foam) on reclaimed ocean (`--list` browses donors). |
| `world-transplant` | Carry a complete real island (land + beach + Wang'd ocean) to a cell, with 90° rotation + 0-mod-4 shift, offline-gated; `--in-place` runs the coast-morph verbs on a deployed block. |
| `world-fuse` | Validate + deploy a multi-placement transplant LAYOUT (the cross-donor fuse) — several verbatim landmasses in adjacent rects, every shared border certified open water. |
| `world-island` | Synthesize a fully-CUSTOM cliff island/landmass on open ocean: organic coastline + faithful rock wall + the real grass language, offline-gated (geometry + UV + placement census). |
| `world-forest` | Carry a REAL canopy blob (verbatim topo-37) onto a deployed kit island — gated by the canopy STEP LAW + a perimeter walk-in simulation. |
| `world-hill` | Raise a raised-cosine grass hill on a deployed kit island by pure-Y displacement, inside the measured grass-language envelope. |
| `world-mountain` | Carry a REAL rock massif (verbatim rock + alcove floor + object-aperture plugs) onto a deployed kit island — ROCK-RIGID, the grass apron conforms. |
| `world-morphs` | The coast WINDOW SCANNER: print a real block's lawful morph windows with per-verb depth ceilings (each line deploys as printed via `world-transplant --in-place`). |
| `world-minimap` | Draw a mod folder's deployed overworld land onto the in-game all-world map image (no DLL; relaunch to apply). |
| `world-mirror` | Mirror a mod folder's Disc1 WorldMap overrides into the Disc4 tree (+ pin free-ride donor parts) — run after any custom-ocean deploy. |
| `world-water` | Synthesize graded open-ocean water (shallow→deep bands) on sea cells. |
| `world-entrance` | Author a whole custom overworld entrance: trigger func + event tiles + optional building (`--cell`, `--field`, `--building`). |
| `world-encounters` / `world-encounter-rate` | Inspect/re-table the overworld encounter table / retune its frequency. |
| `world-environment` | Author overworld weather/effects (Memoria `Environment.txt`). |
| `world-extract` / `world-locate` / `world-retarget` | Extract a block's mesh / decode entrance dispatch / edit tile ids. |
| `world-mesh-export` / `-build` / `-trim` | OBJ round-trip for block meshes (Blender surgery, buildings, floor-apron trim). |
| `world-atlas-extract` / `-catalog` / `-reskin` / `-add-tile` | Extract / browse / repaint / extend the shared overworld texture atlas. |
| `world-texture-palette` | Inspect the learned topograph→tile UV palette used to texture new geometry. |
| `world-rename-markers` | Rename overworld minimap marker labels. |
| `world-deploy` | Deploy reshaped blocks as loose mesh overrides. |

**Audio**

| command | what it does |
|---|---|
| `audio-import <audio>` | Import a custom music/SFX track (any common format, transcoded to Ogg Vorbis): replace an id or mint a new one — DLL-free. |
| `music-list` / `sfx-list` | List song/SFX id → ResourceID (what `audio-import` replaces). |

**Catalogs / Info Hub**

| command | what it does |
|---|---|
| `catalog <q>` | Search every reference catalog (models/items/scenes/fields). |
| `models` / `animations` / `archetypes` / `items` / `scenes` / `flags` | Browse models / gestures / NPC archetypes / items / battle scenes / story flags by name. |
| `sps` | List/decode/preview a field's SPS particle effects. |

**Dialogue**

| command | what it does |
|---|---|
| `dialogue <field>` | View authored dialogue + on-screen wrap preview (also takes a `campaign.toml`). |
| `dialogue-import <field>` | Read a real field's (or a built mod's) dialogue (`--lang`, `--mod`). |

**Save / story-state editing** *(the `items-set-*` family shares `--slot/--save-no/--autosave/--apply/--no-backup`; dry-run by default)*

| command | what it does |
|---|---|
| `flags-inspect` / `flags-diff` | Decode / diff a save's scenario + story flags. |
| `save-edit` | Set a save's story state (ScenarioCounter + flags). |
| `items-inspect` | Read items / equipment / gil from a save. |
| `items-set-gil` / `-item` / `-equip` / `-keyitem` / `-stat` / `-ap` | Write gil / inventory / equipment / key items / permanent stats / AP. |

---

## 8. Where to go next

- [`ff9mapkit/docs/tutorials/`](ff9mapkit/docs/tutorials/README.md) — the tutorial set.
- [`ff9mapkit/docs/FORMAT.md`](ff9mapkit/docs/FORMAT.md) — the `field.toml` / `battle.toml` schema.
- [`ff9mapkit/docs/FEATURES.md`](ff9mapkit/docs/FEATURES.md) — the full capability list.
- [`ff9mapkit/docs/PIPELINE.md`](ff9mapkit/docs/PIPELINE.md) — the from-scratch workflow reference.
- [`ff9mapkit/docs/FORK_FIDELITY.md`](ff9mapkit/docs/FORK_FIDELITY.md) — what forks do/don't reproduce.
- [`ff9mapkit/docs/JOURNEYS.md`](ff9mapkit/docs/JOURNEYS.md) — the journey schema.
- [`ff9mapkit/docs/GLOBAL_RESOURCES.md`](ff9mapkit/docs/GLOBAL_RESOURCES.md) — id / flag / text namespaces.
- [`ff9mapkit/blender/README.md`](ff9mapkit/blender/README.md) — the Blender add-on.
- [`ff9mapkit/examples/vivi-hut/`](ff9mapkit/examples/vivi-hut/) — a complete worked example.
