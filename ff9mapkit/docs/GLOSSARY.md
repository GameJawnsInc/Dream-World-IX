# Glossary

A quick reference to the terms used across the Dream World IX / `ff9mapkit` docs. New to FF9
field authoring? Skim this first, then dive into [`FORMAT.md`](FORMAT.md) (the `field.toml`
reference) and the [`TUTORIAL.md`](TUTORIAL.md).

Terms are grouped by topic; within each group they build on each other.

---

## Fields & scenes

**Field**
: One explorable screen in FF9 — a fixed-perspective pre-rendered background you walk around on
  (a room, a corridor, a town square). FF9 ships ~674 of them. A custom field gets its own id
  (use `>= 4000`); the kit compiles one `field.toml` into one field.

**Walkmesh**
: The invisible per-floor geometry that defines where the player can stand and how far back/forward
  they are (which controls depth — what the character is drawn in front of or behind). It is *not*
  the visible art; it is the collision + depth surface the player walks on. Shipped as a `.bgi`
  file (see below).

**Gateway**
: A region the player walks into that warps them to another field (a door, a screen edge, a
  staircase). It only fires while the player has control, and the walk-out direction is set by the
  order of the region's corner points. See `[[gateway]]` in [`FORMAT.md`](FORMAT.md).

**Encounter**
: A random battle on a field. The kit can author the encounter rate, the battle background/BGM, and
  the after-battle fix that resumes the field cleanly. Encounters are pure field-script data — they
  work on a stock engine.

**ATE (Active Time Event)**
: FF9's optional "Press SELECT" side-scenes (and the grey, unskippable auto-cutscene banner variant).
  Almost all of an ATE lives in the field's own event script rather than the engine, so a faithful
  fork carries it. See [`ATE_SYSTEM.md`](ATE_SYSTEM.md).

**BG-borrow vs. custom scene**
: Two ways to give a custom field its background. **BG-borrow** points your field at a *real* field's
  art (and walkmesh and camera) — the engine renders that room while running *your* script, so you
  ship no art. A **custom scene** ships its own background PNGs, camera, and walkmesh. BG-borrow is
  the quickest way to reuse an existing room; a custom scene is for original or repainted art.

---

## Forking real fields

**Fork**
: To take one of FF9's real fields and reproduce it on a new custom id so you can study, retarget, or
  build on it. `ff9mapkit import <field>` forks a field. There are several fidelity modes:

  - **`--verbatim`** — the most faithful fork: ships the real field's *whole* event script (every
    object, gateway, and the original logic) plus its text, retargeting only the warp destinations.
    The field runs its own real logic — story gating, rotating cast, real doors. Implies `--native`.
  - **`--native`** — ships the real background (atlas + per-tile depth) and a custom walkmesh with no
    intermediate scene file, rendering through the engine's seamless native path. Also works for
    fields BG-borrow can't handle.
  - **`--editable`** — forks into a full custom scene you can repaint: a re-exported walkmesh plus the
    real art split into one editable layer per depth (occlusion preserved). For when you want to
    *change* the room rather than reproduce it.

  Forked fields are faithful in their physical layer (scene, walkmesh, camera, objects) on a stock
  engine, but a handful of id-keyed engine behaviors need the bundled patches — see *Memoria* below
  and [`ENGINE.md`](ENGINE.md).

**Campaign vs. Journey**
: A **campaign** is a connected slice of fields forked together into one mod, with their inter-field
  doors retargeted so you can walk the slice (`ff9mapkit import-chain`). A **journey** sits one level
  up: a complete playable arc made of one *or more* chained campaigns, picked from a World Hub, with a
  starting point and seeded story state. (A campaign chains fields; a journey chains campaigns.) See
  [`CAMPAIGN_IMPORT.md`](CAMPAIGN_IMPORT.md) and [`JOURNEYS.md`](JOURNEYS.md).

---

## Authoring files

**`field.toml` vs. `scene.toml`**
: The two authoring files. **`field.toml`** is the *logic* of a field — its id, dialogue, gateways,
  events, encounters — and is yours to edit. **`scene.toml`** is the optional *spatial* file (camera,
  walkmesh, layers, entity positions), owned by the Blender add-on. At build time the kit overlays the
  scene onto the field by entity `name`, so re-exporting from Blender never clobbers your script. A
  single `field.toml` with no scene sibling builds fine — the split is optional. See [`FORMAT.md`](FORMAT.md).

---

## Game files & formats

**`.eb` (event script)**
: A field's compiled event bytecode — the program that runs the field (NPC behavior, dialogue,
  gateways, cutscenes, encounters). The kit authors `.eb` directly in Python (no third-party editor).
  Per-language `.eb` files differ only in an embedded name field; the bytecode itself is
  language-identical. Format details in [`FORMAT.md`](FORMAT.md).

**`.mes` (text)**
: A field's dialogue/text block — the lines an `.eb` references by id. The kit writes a field's `.mes`
  and the engine merges it over the base game's text. Authored text wraps automatically to fit FF9's
  dialogue window (see [`DIALOGUE.md`](DIALOGUE.md)).

**`.bgx` (scene/camera) and `.bgi` (walkmesh)**
: A field's two binary scene assets. The **`.bgx`** holds the background scene and the camera
  definition (the camera the engine projects the world through, plus scroll/services). The **`.bgi`**
  holds the walkmesh — the per-floor walkable geometry and depth. The kit can ship a real field's
  `.bgi` verbatim to preserve its exact floors and seams.

**Main_Init / Main_Reinit**
: A field script's entry function and its after-battle re-entry function. **Main_Init** runs when the
  field loads (it sets up the scene, the player, and any startup state). **Main_Reinit** (entry-0,
  tag-10) runs when you return *from a battle* — without it a field with encounters can freeze on
  battle return, which is why the kit emits one automatically.

---

## Story state

**GLOB vs. MAP story flag**
: FF9's event scripts store state in two scopes. A **GLOB (Global)** flag lives in save-backed event
  memory and **persists** across field reloads and saves — the right scope for a looted chest, a story
  beat, or a one-time scene. A **MAP** flag is per-field and is **wiped every time the field loads**
  (transient scratch only). The kit uses GLOB for anything that should stick. See *gEventGlobal* below
  and the story-flags section of [`FORMAT.md`](FORMAT.md).

**`gEventGlobal`**
: The engine's save-backed event-memory block — a 2,048-byte array that holds the ScenarioCounter (the
  story-progress beat) and the GLOB story bits. This is where a custom flag lives so it survives saves
  and field reloads. Pick custom flag indices in the safe band the docs call out so you don't collide
  with the base game's flags.

**`fldMapNo`**
: The engine's internal "current field id." FF9 hardcodes a number of behaviors against specific
  `fldMapNo` values (narrow-map letterboxing, certain after-battle/off-mesh fixes, the overworld→field
  entry redirect). When a field is *forked* onto a new id, those id-keyed behaviors no longer match —
  which is why a forked field uses the bundled engine patches to restore them (see *Memoria*).

---

## Engine & assets

**Memoria**
: The open-source FF9 engine layer this toolkit targets ([Memoria](https://github.com/Albeoris/Memoria),
  used by the Steam release). A **novel** field (built from scratch or BG-borrowing real art) runs on a
  **stock, unmodified Memoria**. A **forked** field needs a small bundled patch set
  ([`memoria-patches/`](../../memoria-patches/), `s23`/`s24`/`s29`) to restore the `fldMapNo`-keyed behaviors
  noted above. See [`ENGINE.md`](ENGINE.md) for exactly what's stock vs. patched.

**p0data**
: The packed FF9 asset bundles (`p0data*.bin`) in your install's `StreamingAssets/`, where the real
  fields' scenes, walkmeshes, scripts, and art live. The kit reads them — via the optional `UnityPy`
  dependency — to fork fields and to regenerate base templates. **It never ships their contents** (see
  [`PROVENANCE.md`](PROVENANCE.md)); everything is read from *your* legally-owned install.

**The F6 debug menu (dev-engine only)**
: An in-game developer overlay (toggled with F6) for fast iteration — reload the current field, warp to
  any custom id, teleport, set story flags, give items, toggle cheats, change the time scale. It is a
  **development-only** convenience built into a local engine build; it is **not** part of the shipped
  engine and is not needed to play a finished mod.
