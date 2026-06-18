# ff9mapkit — Setup & Quickstart

> Commands are written for **Windows PowerShell** (the primary dev platform); the bash
> equivalents differ only in how environment variables are set. Everything here is verified
> against the current code (`ff9mapkit/ff9mapkit/cli.py`, `tools/`, `pyproject.toml`).

`ff9mapkit` is a Python toolkit (plus a Blender add-on) that compiles a declarative
**`field.toml`** into a complete drop-in [Memoria](https://github.com/Albeoris/Memoria) mod — a
brand-new *Final Fantasy IX* field with its camera, walkmesh, painted art, NPCs, dialogue,
gateways, encounters, events, and cutscenes. It can also **import/fork any of FF9's ~674 real
fields**, carrying their content faithfully. A **novel** field runs on a **stock, unmodified
Memoria install**; a **forked** field needs the small bundled engine patch set (`memoria-patches/`)
for full fidelity — see [`ff9mapkit/docs/ENGINE.md`](ff9mapkit/docs/ENGINE.md).

---

## 1. Prerequisites

| Need | Detail |
|---|---|
| **Python ≥ 3.11** | Hard floor — the kit uses stdlib `tomllib` (3.11+). |
| **A legally-owned Steam FF9 + Memoria** | The kit reads base assets *from your install*; it bundles zero game bytes. |
| **Pillow ≥ 9.0** | The only hard runtime dependency (composites art layers + renders paint guides). Installed automatically. |
| **UnityPy** (separate `pip install`) | Needed only for `extract-templates`, `import`, `list-fields`, and `battle-import` — anything that reads FF9's `p0data*.bin` assetbundles. Not a declared extra. |

**Back up your clean game folder before anything else.** Copy the entire `FINAL FANTASY IX`
install somewhere safe — it is your only true reset if a deploy ever corrupts something.

Optional extras (pick what you need; details in §2):

| Extra | Installs | Unlocks |
|---|---|---|
| `gui` | `PySide6 ≥ 6.5` | The desktop Workspace GUI (`apps/ff9_studio.pyw`). |
| `save` | `pycryptodome ≥ 3.10` | `save-edit` (read/write FF9's AES-encrypted save). Imported lazily. |
| `dev` | `pytest`, `pytest-xdist` | The offline test suite (`py -m pytest -n 6`). |

---

## 2. Setup (one time)

### 2.1 Install the package

The install must run **from the package directory** (`ff9mapkit/`, where `pyproject.toml` lives),
not the repo root:

```powershell
cd C:\gd\FFIX\ff9mapkit
pip install -e .
# …or with extras:
pip install -e ".[dev,save,gui]"
```

This registers a console script, so `ff9mapkit <cmd>` works anywhere. If it isn't on your PATH,
**`py -m ff9mapkit <cmd>` is identical** and is the safer form when several Pythons are installed.
(Run from the kit root so the local package shadows any other editable install.)

### 2.2 Point the kit at your FF9 install

Resolution order is **`--game` flag → `$FF9_GAME_PATH` → `~/.ff9mapkit.toml` → common Steam
paths**. If FF9 sits at a default Steam location it's auto-detected and **you can skip this step**.
The auto-detected fallbacks:

- `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX`
- `C:\Program Files\Steam\steamapps\common\FINAL FANTASY IX`
- `D:\SteamLibrary\steamapps\common\FINAL FANTASY IX`

To set it explicitly (PowerShell — note `$env:`, **not** bash `export`):

```powershell
# this session only:
$env:FF9_GAME_PATH = "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"

# persist it for future sessions (user-scoped):
[Environment]::SetEnvironmentVariable("FF9_GAME_PATH",
  "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX", "User")
```

Or persist it in `C:\Users\<you>\.ff9mapkit.toml`:

```toml
game_path = "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
```

### 2.3 Regenerate base assets from *your* install

The repo ships **no Square-Enix bytes**. A handful of base assets (the blank field every build
starts from, the exit-region template, test fixtures) are *derived* from FF9's own data via
copy/insert patches + a SHA-256 manifest. `extract-templates` reads your install, applies the
patches, and verifies every output against the manifest:

```powershell
py -m pip install UnityPy
py -m ff9mapkit extract-templates
# → "OK -- <N> assets regenerated + verified against the manifest."
```

Run this **once per checkout**. Until it runs, byte-level commands raise a clear "run
extract-templates" message and the byte-level tests skip. (For a read-only install, point
`$env:FF9MAPKIT_DATA` at a writable cache dir.)

### 2.4 Verify everything

```powershell
py -m ff9mapkit doctor
```

`doctor` prints the kit version, whether UnityPy is present, the resolved game install (launcher +
StreamingAssets found?), the mod root + `DictionaryPatch.txt`, and finally:

```
templates    : extracted
```

If you see `NOT extracted`, re-run §2.3. (`doctor` exits non-zero if the game path can't be
resolved; pass `--game <path>` to override.)

### 2.5 (optional) Run the test suite

```powershell
pip install -e ".[dev]"
py -m pytest -n 6        # 1,500+ offline golden-master tests; -n 6 ≈ 2.6× faster than serial
```

---

## 3. Orientation — how to think about it

### A field, and who owns what

A **field** is one explorable screen with a fixed-perspective pre-rendered background (a single
FF9 room). Authoring one is a deliberate split of labor:

| The kit owns (from math + bytes) | The human owns (cannot be automated) |
|---|---|
| Camera (pitch/yaw/FOV, the projection math) | **Painting the background art** + its depth layers |
| Walkmesh (walkable + depth geometry) | **Final in-game alignment** (does the art land on the floor?) |
| Logic: event script (`.eb`), NPCs, dialogue, gateways, encounters, events, cutscenes, flags | Running the game and **playtesting** |

The hard reason for the split: **the toolkit cannot see the running game.** It validates
everything it can offline (`lint`), and emits a *pixel-accurate paint guide* for your exact camera
so you know where to paint — but after any change that should be visible in-game, the loop is
**build → deploy → you playtest → report back**.

### The fork spectrum — pick your fidelity

Starting from a real field (instead of from scratch) gives four modes, trading editability for
faithfulness:

- **`import` (BG-borrow)** — render the real field's art/walkmesh/camera under *your own* script.
  Best for a real-looking backdrop with all-new logic.
- **`import --editable`** — ship a custom, *repaintable* scene (per-depth layers, occlusion kept).
  Best when you intend to repaint or reshape the room.
- **`import --native`** — seamless per-tile fork (vanilla `.bgs` + atlas, no `.bgx`). Best for a
  faithful-art fork without `.bgx` bilinear seams.
- **`import --verbatim`** — ships the field's **whole real `.eb` + `.mes`**, remapping only the
  `Field()` warp destinations. The *truest* fork: it runs the real logic and speaks the real
  dialogue. Reach for this when you want it to **play** like the original.

Rule of thumb: **`--verbatim`** to *play* it the same; **`--editable`** to *change* it.

### The two authoring surfaces

1. **Declarative `field.toml`** — the logic file (what exists, what it does). Edit by hand, via
   the form editor (`ff9mapkit edit`), or in the **PySide6 Workspace** GUI (§6).
2. **The Blender add-on** — visual camera posing, walkmesh modeling, marker placement → a
   **`scene.toml`**. The split to internalize: **`scene.toml` = *where* things are**;
   **`field.toml` = *what* they do**. Merged at build time.

### Bigger structures

- **Campaigns** — `import-chain <seed>` forks a connected slice of the game into one mod; the
  PySide6 Workspace edits the multi-field project.
- **Journeys** — a `journeys.toml` assembles one or more campaigns into a complete arc behind a
  generated **hub field** that lets the player pick an arc, seeds its starting state, and warps in.

### Reference box — id bands & the global-id rule

Custom field ids are **≥ 4000** (the default `4003` test slot included), and because the engine's
registries are merged across mod folders, **ids must be globally distinct even across stacked
folders** — two folders reusing an id collide and one field loads a null `.eb` (black screen). One
SETUP caveat on the cap: a field id is an **Int16 (max 32767)** — a higher id registers but is
unreachable, and an out-of-range id can break the whole `DictionaryPatch` parse.

The full id / flag / text namespaces and the global-id rule (with their rationale) live in
[`ff9mapkit/docs/GLOBAL_RESOURCES.md`](ff9mapkit/docs/GLOBAL_RESOURCES.md).

---

## 4. The dev loop (edit → deploy → F6)

The fast iterate loop needs **no relaunch** in the common case.

**1. Edit a `field.toml`** (by hand, the form editor, or a Blender export).

**2. Deploy it into the test slot** (run from the repo root):

```powershell
py tools\deploy_field.py myroom\MYROOM_FORK.field.toml
# give a branch/worktree its own slot:
py tools\deploy_field.py myroom\MYROOM_FORK.field.toml --id 5000
```

`deploy_field.py` sandboxes **any** `field.toml` into a test slot — it force-overrides the build to
the target id + a fixed name in-memory (your file is untouched), reverts that slot's prior deploy,
backs up the live `DictionaryPatch.txt`/`.mes`, and writes a per-id `revert_deploy_<id>.py`.
Default slot = **`4003`** (`TESTROOM`) unless a gitignored `.ff9deploy.toml` pins another `id`.
Mod-folder resolution: `--mod-folder` → `$FF9_MOD_FOLDER` → `.ff9deploy.toml` → `FF9CustomMap`.

**3. Reach it in-game with the F6 debug menu** (a *dev-engine* feature — the shipped mod needs none
of it). Press **F6** to open a tabbed popup:

- **Warp** — *Reload field* (re-reads the current field's `.eb`/`.mes`/scene/walkmesh/art from
  disk) and *Warp to field → `<id>`*. These two drive the loop.
- **Move / Cheats / Flags / Time** — teleport, boosters/heal/give, get/set `gEventGlobal` story
  flags (the reliable proof), and 0.25–4× time-scale.

After a later edit: redeploy → **F6 → Reload field**. No relaunch.

**Relaunch the game only when** F6 Reload can't pick a change up:
- the **first deploy of a new id** (registers its `DictionaryPatch` line);
- a **`BattlePatch.txt`** change (battle tuning / per-encounter BGM);
- **start-state CSVs** (`InitialItems`, `DefaultEquipment`, `BaseStats`, `Leveling`) or
  **`TextPatch.txt`** item names — read at startup / New Game;
- an **engine DLL rebuild**.

**Revert a deploy:**

```powershell
py tools\scroll_out\revert_deploy.py        # the latest deploy
py tools\scroll_out\revert_deploy_4003.py   # a specific id (surgical: drops only that id's line)
```

**Bigger deploys:** `tools\deploy_campaign.py <campaign.toml>` installs a multi-field campaign and
wires New Game to its entry; `tools\deploy_journey.py <journeys.toml>` orchestrates campaigns + the
hub. Both are dry-run by default (add `--apply`) and need a relaunch after applying.

**Shipped path (no dev engine):** `ff9mapkit build … --mod-name MyMod`, copy the built mod folder
into the game install, register it in `Memoria.ini [Mod] FolderNames`, and launch. This is the
engine-independent route; the `deploy_field.py` + F6 loop above is just faster for iteration.

---

## 5. Quickstart — your first field

### Path 1 — Fork a real field (fastest, no painting)

```powershell
# 1. sanity-check
py -m ff9mapkit doctor

# 2. find a field to fork (filter by map code: alex, treno, dali, iccv, grgr, …)
py -m ff9mapkit list-fields glgv

# (optional) preview what a fork will/won't reproduce:
py -m ff9mapkit fork-report 354 --explain
```

```powershell
# 3. fork it. --verbatim = most faithful (ships the REAL script + dialogue: real doors,
#    story gating, rotating cast). Drop --verbatim for a simpler, easier-to-edit BG-borrow.
py -m ff9mapkit import glgv_map792_gv_rm1_0 --out myroom --name MYROOM --verbatim
```

This writes `myroom\MYROOM_FORK.field.toml` (+ `camera.bgx`, `walkmesh.bgi`), already carrying the
real field's art, walkmesh, camera, exits, encounters, and music. **It prints the walkmesh
bounds — note them; your content must sit inside.** (Default `--id` is `4003`.)

**4. Add an NPC with your own line.** Open the `.field.toml` and add a block (keep `pos` inside the
printed bounds):

```toml
[[npc]]
name = "Greeter"
archetype = "vivi"           # place a cast model by name; run `ff9mapkit archetypes` for the list
pos = [-700, -900]           # world (x, z), y = 0 — inside the printed walkmesh bounds
dialogue = "Welcome to the room I just made."
```

Prefer a form? `py -m ff9mapkit edit myroom\MYROOM_FORK.field.toml`. (A verbatim fork keeps its
real script; your `[[npc]]` is layered on top.)

```powershell
# 5. lint (off-walkmesh content, NPC within ~48u of a wall, dead flags, camera pitch, …)
py -m ff9mapkit lint myroom\MYROOM_FORK.field.toml

# 6. deploy into the test slot
py tools\deploy_field.py myroom\MYROOM_FORK.field.toml --id 4003
```

**7. Play it.** In-game press **F6 → Warp to field → 4003**. (The *first* time a new id is used,
relaunch once so its `DictionaryPatch` line registers; after that, redeploy → **F6 → Reload
field**.) Then verify: does it render, can you reach and talk to your NPC?

> **No dev engine?** Build a standalone mod instead — `py -m ff9mapkit build
> myroom\MYROOM_FORK.field.toml --out dist --mod-name MyFirstField` — copy `dist\MyFirstField\`
> into the game (Memoria auto-stacks it), and to *reach* a brand-new id, fork a field you can
> already walk to and add a `[[gateway]] to = 4003` over a spot the player crosses.

### Path 2 — From scratch (original art)

When you want fully original art (full detail in [`docs/PIPELINE.md`](ff9mapkit/docs/PIPELINE.md)):

```powershell
# 1. scaffold. --area MUST be >= 10 (the BG loader reads exactly 2 chars; areas 0-9 black-screen)
py -m ff9mapkit new MY_ROOM --area 11

# 2. get a paint guide for your camera angle
py -m ff9mapkit guide --pitch 48 --distance 4500 --fov 42.2 --png MY_ROOM\art\guide.png
```

3. **(Human) paint** the back/floor/front layers over the guide (export at 4× → 1536×1792) into
   `MY_ROOM\art\`.
4. **Fill in `field.toml`** (layers, walkmesh, spawn, NPCs, gateways, music — schema in
   [`docs/FORMAT.md`](ff9mapkit/docs/FORMAT.md); `examples/vivi-hut/hut_int.field.toml` is a
   complete worked example), then `lint` → deploy/build as in Path 1.

---

## 6. The GUI Workspace (optional)

A single PySide6 window that folds every authoring tool into one place. **Entirely optional — the
CLI does everything without it.**

```powershell
pip install ff9mapkit[gui]      # or: py -m pip install PySide6
py apps\ff9_studio.pyw          # the front door (shows a friendly prompt if PySide6 is missing)
py apps\ff9_studio.pyw --smoke  # headless self-check: prints "workspace shell smoke ok: …"
```

The window is built around a **journey ▸ campaign ▸ field ▸ object** tree, a breadcrumb, a central
tabbed document area, a right-hand **Inspector**, and a bottom **Output/Problems** console.

- **Create or open** via 3 toolbar dropdowns — **Field** (New, Ctrl-N), **Campaign**
  (New, Ctrl-Shift-N), **Journey** (New + Open). **Open Journey…** is the top-level front door: it
  loads a whole arc and lints the global-id guarantee into Problems.
- **Editor** — forms for fields, NPCs, gateways, events, markers, cutscenes, dialogue choices + a
  catalog picker; a live FF9-window **wrap preview** for dialogue; undo/redo (Ctrl-Z); Save All
  (Ctrl-S).
- **Map** (campaign graph), **Story State** + **Item & Equip** (save editors), **Build & Deploy**
  (field/campaign/battle, auto-detected), **Import** (fork + fork-report), **Info Hub** (a
  searchable model/prop/creature library with a ready-to-paste `field.toml` snippet).
- A **Ctrl-K** command palette; an Inspector with per-node rollups and clickable
  "exits to / reached from" cross-refs.

---

## 7. CLI command reference

59 subcommands, invoked as `ff9mapkit <cmd>` or `py -m ff9mapkit <cmd>`. Global flags: `--game
<path>`, `--mod-folder <name>`, `--version`.

**Setup / doctor**

| command | what it does |
|---|---|
| `doctor` | Resolve paths + sanity-check the install (game/mod paths, templates extracted). |
| `extract-templates` | Regenerate base assets from your install (`--no-fixtures` = templates only). |

**Author a new field**

| command | what it does |
|---|---|
| `new <name>` | Scaffold a field project (`--area` ≥10 default 11, `--id`, `--pitch`). |
| `guide` | Author a camera + emit a paint guide (`--pitch/--distance/--fov`, `--png`, `--template`). |
| `camera <bgx>` | Inspect / regenerate a `.bgx` camera (`--regen OUT.bgx`). |
| `walkmesh <obj\|fix\|verify> <in> [out]` | Convert `.obj`→`.bgi`, rebuild neighbor links, or run checks. |
| `disasm <eb>` | Disassemble a `.eb` field script (`-e N`, `-a`). |
| `edit [field]` | Open the form-based logic editor. |

**Build & deploy / packaging**

| command | what it does |
|---|---|
| `build <field…>` | Compile project(s) into a Memoria mod (`--out`, `--mod-name`, `--author`). |
| `lint <field>` | Run every offline validator without building. |
| `pack <mod>` | Zip a built mod (`--out`). |
| `export-art [target]` | Assemble a field's background PNGs offline (`--all`, `--composite`). |

**Fork / import a real field**

| command | what it does |
|---|---|
| `import <field>` | Fork a real field (`--editable`/`--native`/`--verbatim`, `--swap-player`, `--id` def 4003). |
| `import-all` | Bulk-import a Blender-ready archive (`--out`, `--all`, `--pattern`, `--editable`). |
| `import-chain <seed>` | Fork a connected region into a campaign (`--out`, `--zones`, `--verbatim`). |
| `list-fields [pat]` | List real fields available to import (`--players`, `--non-zidane`). |
| `find-field <q>` | Resolve a field id / name / FBG substring. |
| `find-rooms` | Sweep for the best swap/demo test rooms. |
| `fork-report <field>` | Preview a fork's fidelity offline (`--explain`). |
| `extract-field <ids…>` | Cache a real field's camera+walkmesh in the workspace cache. |

**Campaigns / journeys**

| command | what it does |
|---|---|
| `new-campaign <dir>` / `add-field <camp>` | Create an empty campaign / add a member field. |
| `build-all <camp>` / `lint-campaign <camp>` | Compile / validate a `campaign.toml`. |
| `gen-hub <journeys>` | Generate a World-Hub field from a `journeys.toml`. |
| `lint-journey` / `assemble-journey <journeys>` | Validate / assemble a multi-campaign journey. |

**Battle backgrounds & tuning**

| command | what it does |
|---|---|
| `battle-import <bbg>` / `battle-build <toml>` | Fork a battle background / compile a `battle.toml`. |
| `battle-list` / `battle-scene <donor>` / `battle-actions` | Browse battle backgrounds / enemy data / player abilities. |
| `battle-ai [donor]` | Disassemble enemy AI (read-only) + `--asm`/`--asm-block`/`--lint` helpers. |
| `battle-patch [toml]` | Preview the `BattlePatch.txt` a field emits (`--fields`). |
| `characters` / `ability-gems` | List stat / gem-cost tuning targets. |

**Catalogs / Info Hub**

| command | what it does |
|---|---|
| `catalog <q>` | Search every reference catalog (models/items/scenes/fields). |
| `models` / `animations` / `archetypes` / `items` / `scenes` / `flags` | Browse models / gestures / NPC archetypes / items / battle scenes / story flags by name. |

**Dialogue**

| command | what it does |
|---|---|
| `dialogue <field>` | View authored dialogue + on-screen wrap preview (`--clean`). |
| `dialogue-import <field>` | Read a real field's (or a built mod's) dialogue (`--lang`, `--mod`). |

**Save / story-state editing** *(all `items-set-*` share `--slot/--save-no/--autosave/--apply/--no-backup`; default is dry-run)*

| command | what it does |
|---|---|
| `flags-inspect` / `flags-diff` / `save-edit` | Decode / diff / set a save's scenario + story flags. |
| `items-inspect` | Read items / equipment / gil from a save. |
| `items-set-gil` / `-item` / `-equip` / `-keyitem` / `-stat` / `-ap` | Write gil / inventory / equipment / key items / permanent stats / AP. |

> This table is the full command surface — `ff9mapkit/README.md` keeps a condensed family overview
> that links here.

---

## 8. Where to go next

- [`ff9mapkit/docs/PIPELINE.md`](ff9mapkit/docs/PIPELINE.md) — the full from-scratch authoring workflow.
- [`ff9mapkit/docs/FORMAT.md`](ff9mapkit/docs/FORMAT.md) — the `field.toml` schema.
- [`ff9mapkit/docs/FEATURES.md`](ff9mapkit/docs/FEATURES.md) — the full capability list.
- [`ff9mapkit/docs/FORK_FIDELITY.md`](ff9mapkit/docs/FORK_FIDELITY.md) — honest map of what forks do/don't reproduce.
- [`ff9mapkit/docs/JOURNEYS.md`](ff9mapkit/docs/JOURNEYS.md) — the multi-campaign journey schema.
- [`ff9mapkit/docs/GLOBAL_RESOURCES.md`](ff9mapkit/docs/GLOBAL_RESOURCES.md) — canonical id / flag / text namespaces + the global-id rule.
- [`ff9mapkit/blender/README.md`](ff9mapkit/blender/README.md) — the Blender add-on.
- [`ff9mapkit/examples/vivi-hut/`](ff9mapkit/examples/vivi-hut/) — a complete worked example.
