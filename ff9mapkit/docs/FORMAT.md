# `field.toml` reference

One `field.toml` describes one custom field. `ff9mapkit build field.toml` compiles it into a
Memoria mod folder. Pass several to build a multi-field mod.

```bash
ff9mapkit build my_room.field.toml --out dist --mod-name MyMod --author you
```

---

## Two files: scene (spatial) + field (logic)

You can keep everything in one `field.toml`, **or** split *where things are* from *what they do*
(the Godot model — placement in the scene, scripts on the nodes):

- **`<x>.scene.toml`** — owned/overwritten by the Blender add-on: `[[camera]]`, `[walkmesh]`,
  `[[layers]]`, `[player]`, `[[camera_zone]]`, and each entity's **position/zone** tagged by `name`.
- **`<x>.field.toml`** — yours: `[field]` + the **logic** for each entity (dialogue, conditions,
  events, encounters) referenced by `name`.

`build` **overlays** the scene onto the field by entity `name` (scene supplies the spatial keys, your
file supplies the logic), so re-exporting from Blender never clobbers your script. The scene is found
automatically as a sibling `<x>.scene.toml`, or via an explicit `[scene]\nfile = "..."` key. A
single-file `field.toml` (no scene sibling) builds exactly as before — the split is optional and
purely additive. Keep both files in the same folder (asset paths resolve there).

> Give entities a `name` to split them across files (NPCs already take `name`; add it to
> `[[gateway]]` / `[[event]]`). An entity placed in the scene with no matching logic still builds
> (spatial-only); logic with no scene match uses the position in the field file.

---

## `[field]` (required)

| key | required | meaning |
|---|---|---|
| `id` | ✓ | custom field id. Use `>= 4000`; claim a block for your mod (see below). |
| `name` | ✓ | base name → background folder `FBG_N<area>_<name>` and script `EVT_<name>.eb`. |
| `area` | ✓ | area id, **must be `>= 10`** (the loader reads exactly 2 digits — single-digit areas black-screen). |
| `text_block` | | dialogue `.mes` block id (default `1073`). |
| `title` | | human title (used as the scene comment). |

The DictionaryPatch line emitted is: `FieldScene <id> <area> <name> <name> <text_block>`.

### Field-id namespace
Custom ids share one namespace across all installed mods. Convention: `>= 4000`, each mod
claims a contiguous 100-id block. `ff9mapkit new <name>` suggests a deterministic block from
your mod name; coordinate for a public release.

---

## `[camera]` (required)

Author a camera from a simple spec **or** borrow a real one.

| key | meaning |
|---|---|
| `pitch` | downward tilt in degrees (real FF9 fields are `<= ~48`; steeper works but is out-of-range). |
| `distance` | camera distance from the origin (default `4500`). |
| `fov` | horizontal field of view in degrees (default `42.2`). |
| `yaw` | optional rotation about vertical (default `0`). |
| `range` | painted-canvas size `[w, h]` (default `[384, 448]` = one screen). Set wider/taller for a **scrolling** room. |
| `window_width` | the width the `fov` is measured against (default = `range[0]`). For a scrolling room set it to the visible screen width (`384`) so a wide `range` doesn't change the focal length. |
| `proj`, `depth_offset`, `viewport`, `center_offset` | advanced overrides (`proj` = explicit focal length; sensible GRGR-derived defaults). |
| `borrow` | path to a `.bgx` whose `CAMERA` block to copy verbatim (instead of `pitch`/`fov`). |

### `[camera.scroll]` (optional — larger-than-screen rooms)
A field whose painting is **bigger than the screen** scrolls the view to follow the player (FF9
streets/corridors). The engine does the panning automatically once enabled.

| key | meaning |
|---|---|
| `enabled` | `true` to make this a scrolling field: injects the engine's `EnableCameraServices` and auto-sets the scroll `viewport` so the view can pan across the whole `range`. |
| `frame_count` | frames the camera takes to ease to the player when it activates (default `0` = instant). |
| `scroll_type` | `8` = sinusoidal easing, else linear (default `0`). |

> To author one: set a wide `range` (e.g. `[768, 448]` for 2× width), `window_width = 384`, and
> `[camera.scroll] enabled = true`. Paint the full-`range` canvas (the paint guide auto-sizes to it),
> and make the walkmesh span the painting. Proven in-game on a 768×448 field.

### `[[camera]]` + `[[camera_zone]]` (optional — multiple camera angles)
A field can show the room from **more than one fixed camera** and cut between them as the player
walks (FF9 does this in ~8% of fields — corners, hub rooms). Declare the cameras as an **array**
(`[[camera]]` instead of `[camera]`) — camera **0 is the one shown at load** — and place
**switch zones** that cut to another camera when crossed. Generalizes the real-game convention
(decoded from Gargan Roo/Passage) to **N cameras** via an *area model*: a state flag holds the
current camera index, and each zone owns the floor area where its camera is active — stand in it and
that camera is shown. Scales to any number of cameras (FF9 ships up to 4).

```toml
[[camera]]                 # camera 0 — active at load
borrow = "cam0.bgx"        #   (or pitch/yaw/fov, exactly like [camera])
[[camera]]                 # camera 1
borrow = "cam1.bgx"
[[camera]]                 # camera 2 ... (any number)
borrow = "cam2.bgx"

[[camera_zone]]            # the floor area shown by camera 0
to_camera = 0
zone = [[-1100,-100],[-400,-100],[-400,-900],[-1100,-900]]   # 4 convex (x,z) corners
[[camera_zone]]            # ... camera 1's area
to_camera = 1
zone = [[-300,-100],[300,-100],[300,-900],[-300,-900]]
[[camera_zone]]            # ... camera 2's area
to_camera = 2
zone = [[400,-100],[1100,-100],[1100,-900],[400,-900]]
```

| key | meaning |
|---|---|
| `[[camera]]` | one block per camera (same keys as `[camera]`); index = order, 0 = default at load. |
| `[[layers]] camera = N` | which camera a background layer belongs to (default `0`) — paint a backdrop per camera. |
| `[[camera_zone]] to_camera` | the camera index whose area this zone is. |
| `[[camera_zone]] zone` | 4 convex `(x,z)` corners of that camera's floor area. |

> Partition the floor into one zone per camera. The kit derives each camera's `SetControlDirection`
> from its yaw (so "up" stays up-screen after a cut). **Zones must not overlap** (overlapping zones
> flap). If the field has encounters, the camera is **restored after battle** (the active camera + its
> movement re-apply on battle return). (Engine-validated bytecode; in-game proof pending.)

### `[camera.frame]` (optional)
Used to auto-frame a flat walkmesh and the paint guide.

| key | meaning |
|---|---|
| `back` | painted-canvas row (Y, 0..`range[1]`) the floor's back edge sits on (default `205`). |
| `front` | ... and its front edge (default `432`). |

---

## `[[layers]]` (background overlays, back-to-front)

Each is one painted PNG. `z` is depth: **smaller = nearer the camera** (drawn in front of the
player → use a small `z` for a foreground piece that should occlude the character).

| key | required | meaning |
|---|---|---|
| `image` | ✓ | path to the PNG (copied into the field folder). |
| `z` | ✓ | depth. |
| `position` | | `[x, y]` top-left in logical canvas px (default `[0, 0]`). |
| `size` | | `[w, h]` (default = the camera `range`, i.e. the full painting — `[384, 448]` for a normal field). |
| `shader` | | default `PSX/FieldMap_Abr_None` (respects painted alpha). |

> Painting the layers is a **human** task. `ff9mapkit guide` tells you exactly where the floor
> and its edges land on the canvas for your camera.

---

## `[walkmesh]`

Pick one (or omit all three to auto-frame from `[camera.frame]`):

| key | meaning |
|---|---|
| `bgi` | a pre-built `.bgi.bytes` shipped **verbatim** — e.g. an imported real field's walkmesh. Preserves its exact floors + neighbor/edge connectivity (a multi-floor `obj` rebuild would disconnect floors with disjoint vertex sets). What `import --editable` uses. |
| `obj` | a Wavefront `.obj` in FF9 world coords (x, y, z); faces become walk triangles. Use for authoring new geometry, or reshaping a forked field (pair with `links` + `frame = "world"`). |
| `links` | an adjacency sidecar (`walkmesh.links.toml`) paired with `obj` to **reshape an imported multi-floor field while keeping connectivity** — rebuild_neighbors only links within a floor, so the sidecar re-attaches cross-floor seams by world position (warns on a moved/deleted seam). Written by `import --editable`. See [WALKMESH_EDITING.md](WALKMESH_EDITING.md). |
| `quad` | 4 corners `[[x, z], ...]` for a flat quad floor. |
| *(none)* | auto: a quad framed to the painted floor via `[camera.frame]`. |
| `character_offset` | (single-floor legacy `obj`/`quad`) world units to slide the floor toward the camera so a 3D character looks planted on the 2D painting; defaults to `0` for explicit meshes, `298` for the auto frame. |
| `frame` | `"world"` => write verts verbatim with `orgPos=0` (geometry already in exact world coords — imported real fields, or Blender-authored against the art); `"legacy"` (default) => the calibrated flat-room path above. Multi-floor meshes are always world. |

### The frame (how a vertex maps to the screen)

The engine renders a walkmesh vertex at `world = vertex + floor.org + bgi.orgPos`
(`WalkMesh.cs`). The kit's exporter writes **`orgPos = 0` and every `floor.org = 0`**, so the
coordinates you author *are* the in-game world positions — what `ff9mapkit guide` /
`cam.to_canvas` predict on the canvas is exactly where the player walks. (`minPos`/`maxPos` in the
file are loaded but unused by the engine; `charPos` is only the debug spawn.)

### Multiple floors (height levels / re-exported real fields)

A single flat `obj`/`quad` is one floor. To author a **multi-level** room — or to re-export a real
field forked with `ff9mapkit import` (e.g. Gargan Roo's 7 floors) — give the `.obj` one
`o <name>` (or `g <name>`) **object per floor**; each becomes a BGI floor, with the verts carrying
their real world height (`y`). The Blender add-on does this automatically: each material slot on the
walkmesh exports as one floor. Multi-floor meshes use the world frame directly (no
`character_offset`), since the imported/authored verts are already the exact engine positions.

---

## `[player]` (optional)

| key | meaning |
|---|---|
| `spawn` | `[x, z]` where the player appears on entry. |

---

## `[[npc]]` (optional, repeatable)

| key | meaning |
|---|---|
| `name` | label only. |
| `preset` / `archetype` | a built-in **archetype** name → model + auto-resolved animations. Playable cast (`vivi`, `zidane`, `garnet`, …) + **every** field-NPC type (`black_mage`, `guard`, `innkeeper`, `puck`, `chocobo`, …). List with `ff9mapkit archetypes`; full reference with roles + in-game locations in [`docs/ARCHETYPES.md`](ARCHETYPES.md). For any other model use `model`. |
| `model` | explicit alternative to `preset`: a model **id**, *or* an exact **GEO name** (`"GEO_NPC_F0_BAR"` — browse with `ff9mapkit models`) resolved to the id via the Info Hub catalog. **Its animations auto-resolve** from the catalog's model→animation join (idle/walk/run/turn), so a model name *alone* gives a fully-animated NPC — no `anims` needed. A bad name fails the build with a clear error; a raw id outside the model table is a lint warning. |
| `animset` | the model's **head height** (positions the dialogue box; cosmetic). |
| `anims` | OPTIONAL `{ stand, walk, run, left, right }` gesture-id **override** — only to hand-pick gestures; if omitted, a `model` auto-resolves its own (see them with `ff9mapkit models <name>`; the build warns on an unknown anim id). |
| `pos` | `[x, z]`. |
| `dialogue` | a line shown when talked to (assigned a non-colliding high text id automatically). |
| `text_id` | use an explicit text id instead of `dialogue`. |
| `speaker` | optional name shown before the line → `"Vivi: …"`. See *Speaker names & the tail* below. |
| `tail` | the dialogue window's pointer corner (`UPR` default). See below. |
| `requires_flag` | GlobBool index (or a `[[flag]]` name) — the NPC only **appears** when that story flag is SET (its Init returns early otherwise: no model, not interactable). For story-gated characters. |
| `requires_flag_clear` | …only appears when the flag is CLEAR (the inverse — e.g. an NPC that leaves once an event fires). |
| `holds` | a **prop the NPC holds in hand** — a prop-archetype name (`"cup"`, `"sword"`, `"save_the_queen"`) or a model, or a **list** of them. The kit attaches each prop to the right hand-bone *and* poses the prop + the holder correctly, **auto-resolved for this holder's model** from the shipping `AttachObject` catalog (`tools/extract_attach_poses.py` → `_held_poses.py`). So `holds = "save_the_queen"` on a `beatrix` puts the sword in her hand at her real holding pose. A (holder, prop) pair not in the catalog falls back to bone 11 + the prop's resting pose (and leaves the holder's pose alone). |

### Speaker names & the dialogue tail

FF9 has **no speaker name-box**. Who's talking is shown by the dialogue window's **tail** (the little
pointer), and a name — when shown at all — is just part of the text. Two optional keys (on `[[npc]]`,
`[[event]]`, and cutscene `say` steps) make that ergonomic:

- **`speaker`** — prefixes the name onto the line: `speaker = "Vivi"` → `"Vivi: <your line>"`. Use one
  of FF9's **renameable name tags** for a party member so it tracks the player's chosen name:
  `speaker = "[VIVI]"` (also `[ZDNE]` Zidane, `[DGGR]` Dagger, `[STNR]` Steiner, `[FRYA]`, `[QUIN]`,
  `[EIKO]`, `[AMRT]`, `[PTY1]`–`[PTY4]`). You can also just type the name into `dialogue` yourself.
- **`tail`** — which corner the window's pointer comes from: `UPR` (default) `UPL` `LOR` `LOL` upper/
  lower-right/left, `UPC` `LOC` upper/lower-center, the `…F` force variants, or `DEFT` (engine
  default/auto). Handy when the default points the wrong way for an NPC's on-screen position.

```toml
[[npc]]
name = "Vivi"
preset = "vivi"
dialogue = "I missed you, [ZDNE]."   # renders "Vivi: I missed you, Zidane."
speaker = "[VIVI]"                    # renameable name; or just "Vivi"
tail = "UPL"                          # pointer from the upper-left
```

### Line breaks & pages

FF9 dialogue windows are **not** one screen — they take multiple lines and multiple pages. In any
`dialogue` / `message` / `say` string:

- **auto-wrap (default ON).** FF9 itself does **not** word-wrap: the window grows to fit the widest
  line, so an unbroken long line runs off the screen. ff9mapkit therefore breaks long lines for you at
  build time. You can just write a whole sentence and it will be wrapped to fit:
  ```toml
  dialogue = "It's so good to see you again — I have so much I want to tell you about everything."
  ```
- **manual line break** = a `\n` — wrapping respects your breaks (it only re-flows a line that is still
  too long), so use `\n` when you want the breaks in an exact spot:
  ```toml
  dialogue = "First line.\nSecond line."
  # or a multi-line string:
  dialogue = """First line.
  Second line."""
  ```
- **new page** = the `[PAGE]` tag — the window shows a ▼ and advances on confirm (each page wraps on
  its own): `dialogue = "Page one.[PAGE]Page two."`

#### `[dialogue]` — wrap control (optional)

| key | meaning |
|---|---|
| `wrap` | max line width in *width units* (≈ average characters). Default **28** (conservative — never overflows). `wrap = false` (or `0`) turns auto-wrap **off** (you hand-break every line). |

```toml
[dialogue]
wrap = 32          # allow fuller lines; or `false` to wrap nothing
```

> **Why "width units" and not pixels.** FF9's dialogue font is a *runtime dynamic TrueType* font (the
> bundled `TBUDGoStd-Bold`, or whatever you set in `Memoria.ini [Font]`), measured by Unity at a
> configurable size — so there's **no fixed pixel width** to target and the exact fit differs per
> install. ff9mapkit models *relative* glyph widths (a `W` costs ~3× an `i`) and wraps at a safe
> budget, erring toward wrapping a hair early. If you want fuller lines, do one in-game check and raise
> `wrap` to your install's true maximum. A single word too wide to fit a line is reported as a build
> warning.

> **Multi-page sizing gotcha.** FF9 sizes the window **once** to fit the *biggest* page (widest page's
> width, tallest page's line count) and reuses that size for every page (`Dialog.cs`) — so a short
> page shows blank space below its text. For clean results, **keep pages balanced** (same number of
> `\n` lines each), or just use a single page with `\n` breaks (the most predictable). Most FF9 field
> dialogue is single-page.

(These pass straight through to FF9's text engine; entries are delimited by the `[TXID=]`/`[STRT=]`
markers, so a newline inside a line is safe, and the `.mes` is written with LF.)

---

## `[[prop]]` (optional, repeatable)

A static **set-dressing object** — a chest, tent, save point, barrel, ladder, sign. Unlike an `[[npc]]`,
a prop is **not a character**: it does NOT turn to face the player (no head-tracking) and just holds a
fixed pose. Placed via the real FF9 prop recipe (`SetModel` + a static `SetStandAnimation` +
`EnableHeadFocus(0)`), grounded byte-for-byte in shipping fields — not emulated.

```toml
[[prop]]
prop = "chest"            # a built-in prop archetype: model + its canonical pose (see docs/ARCHETYPES.md)
pos  = [120, 150]
# face = 64               # optional facing (0=south, 64=west, 128=north, 192=east)

[[prop]]                  # OR place any model directly:
model = "GEO_ACC_F0_CSK"  # a prop model id or GEO name (browse `ff9mapkit models`)
pos   = [-200, 150]
pose  = "close"           # optional pose (see below)
```

| field | meaning |
|---|---|
| `prop` | a built-in **prop archetype** → model + its canonical resting pose (`chest`, `tent`, `save_book`, `feather`, `balloon`, `ladder`, `book`, `cask`/`barrel`, `lever`, `vat`, `pickaxe`, `aircab`, `letter`, `cactus`, `sword`, …). Full list with locations: [`docs/ARCHETYPES.md`](ARCHETYPES.md). For anything else use `model`. |
| `model` | explicit alternative to `prop`: a prop model **id** or exact **GEO name** (`"GEO_ACC_F0_TBX"`). |
| `pose` | OPTIONAL static pose — an **action name** (`"close"`, `"save_open"`) resolved via the model→anim catalog, **or a raw clip id**. Omitted → a sensible resting pose. A prop's *true* pose is often a raw clip the name-join doesn't list (the save book rests at `1872`); `tools/extract_prop_poses.py` harvests the canonical one from shipping fields (already baked into the archetypes). |
| `pos` | `[x, z]` world position (on the walkmesh). |
| `face` | OPTIONAL facing (0..255; 0=south, 64=west, 128=north, 192=east). |
| `requires_flag` | OPTIONAL GlobBool index (or a `[[flag]]` name) — the prop only appears when that story flag is set (same gating as `[[npc]]`). |
| `attach_to` | OPTIONAL — the **`name` of an `[[npc]]`** to *attach* this prop to (a held item: a cup, a sword). The prop binds to that NPC's `bone` and follows it (the engine's `AttachObject`). Give it the **held** `pose` — props often have a per-holder held orientation (the cup has `dom`/`zdn`/`jjy` poses), so pick the one matching the carrier. |
| `bone` | OPTIONAL attachment bone index (default **11**, the right hand the shipping cup uses; e.g. 13/19 for other models). |

A prop is non-interactive by default. Composite set pieces (a full **save point** = `moogle` + `save_book`
+ `feather` + `balloon`) are just several `[[prop]]` / `[[npc]]` at one position. An **attached** prop
(`attach_to`) is the held-item path — `[[npc]] name = "barkeep"` + `[[prop]] model = "GEO_ACC_F0_CUP",
attach_to = "barkeep", pose = <held>` puts the cup in the barkeep's hand.

---

## Battle maps (`battle.toml`) — a SEPARATE project from `field.toml`

A custom **battle background** ("BBG") is authored in its own `battle.toml`, *not* a `field.toml`. A
battle map is a real textured **3D mesh** (the camera moves through it during combat), unlike a field's
flat painted plane. Memoria loads a loose **FBX** from your mod folder instead of the bundle, so a custom
map ships on **stock Memoria, no engine rebuild**. Loop (the battle analogue of the field import→build):

    ff9mapkit battle-list                          # browse the real BBGs you can fork
    ff9mapkit battle-import BBG_B013 --out my_map   # fork one -> battle.toml + BBG_B013.fbx + image#.png
    # edit my_map/BBG_B013.fbx in Blender (KEEP the meshes named Group_0/2/4/8) and/or repaint the PNGs
    ff9mapkit battle-build my_map/battle.toml --out dist
    py tools/deploy_battle.py my_map/battle.toml    # reversible install into your (per-worktree) mod folder

```toml
[battlemap]
bbg = "BBG_B013"        # the slot this map ships as; keep = the forked slot to OVERRIDE that real map
fbx = "BBG_B013.fbx"    # the geometry file in this dir (edit in Blender, re-export over it)
# repoint_scene = 67    # OPTIONAL: point an EXISTING battle scene's bg at `bbg` (via BattlePatch.txt)
```

| key | meaning |
|---|---|
| `bbg` | the battle-bg slot the map ships as (`BBG_<letter><digits>`). If it equals an existing real slot, the FBX **overrides** that map for every battle that uses it — proven in-game, no relaunch. |
| `fbx` | the FBX geometry in the project dir. Its mesh objects MUST stay named `Group_0/2/4/8` (= additive / ground / minus / sky, per `battlebg.getBbgAttr`); `battle-import` names them for you, and the import recipe sets each group's PSX shader so the SkinnedMeshRenderer import renders correctly. |
| `repoint_scene` | OPTIONAL existing battle-scene id whose background becomes `bbg` (emits a `BattlePatch.txt` `BattleBackground` line; needs one relaunch). |
| `scene_id` + `scene_name` | OPTIONAL **experimental (tier c)** — mint a brand-new `BattleScene <id> <name> <bbg>`. A new scene id also needs its own scene assets + a camera the kit does **not** yet author, so a bare new id won't load; prefer overriding an existing slot or `repoint_scene`. |

Textures are the `image#.png` files beside the FBX (forked from the real map — repaint them in place). The
geometry/textures are extracted from **your** install at runtime and are gitignored — never committed.

---

## `[[gateway]]` (optional, repeatable)

A region the player walks into to warp to another field.

| key | meaning |
|---|---|
| `to` | target field id. |
| `entrance` | which entrance to arrive at in the target (default `0`). |
| `zone` | 4 corners `[[x, z], ...]` (auto-made IsInQuad-safe) or 5 explicit points. Order: the `q0→q1` edge is the walk-out direction (put the front edge first). |
| `requires_flag` / `requires_flag_clear` | GlobBool index (or a `[[flag]]` name) — the exit only **fires** when that story flag is SET / CLEAR (a locked door that opens once a switch flag is set). |
| `set_scenario` | *(optional)* on taking this exit, set the **ScenarioCounter** — an int (`0`–`32767`) or an area name (`"Dali (underground)"`). Advances the story so the **next** field boots at the right beat. |
| `set_flags` | *(optional)* on taking this exit, set/clear story bits: `[{flag = <index|name>, value = 0|1}, …]`. |

> `set_scenario` / `set_flags` are the **write-side complement to `[startup]`** (which asserts the beat on
> *entry*): they let a forked field **chain** progress the story as you move through it. The writes fire only on
> an actual walk-out (gated by `usercontrol`) and only when the exit is open (after any `requires_flag` gate),
> committing to the save-backed `gEventGlobal` just before the warp. A write into a reserved flag band is
> flagged by `lint`.

---

## `[[ladder]]` (optional, repeatable)

A ladder the player **climbs** — FF9's real ladder mechanism (decoded from Treno/Residence and
in-game-verified): walk to the base and a floating **"!" prompt** appears; press the **action button**
to climb to the destination.

```toml
# BIDIRECTIONAL (from-scratch, no real ladder to copy) -- a zone + landing at EACH end:
[[ladder]]
top    = [-50, 450]      # top end: trigger zone centre + where "climb up" lands
bottom = [64, -348]      # bottom end: trigger zone centre + where "climb down" lands
# zone_radius = 150      # optional, half-size of each auto-made square zone (default 150)
# animation  = 7302      # optional climb gesture (a one-shot anim id)

# FAITHFUL (a real ladder, from `ff9mapkit import`) -- exact perspective-correct jump arcs:
[[ladder]]
zone  = [[9016, -16722], [9574, -17758], [9791, -17674]]  # auto-widened by import to span both ends
climb = "MYFIELD.ladder0.climb.bin"

# EMULATED ONE-WAY -- a single zone that teleports you to one destination:
[[ladder]]
zone = [[9016, -16722], [9574, -17758], [9791, -17674]]   # the base (3–5 points)
to   = [7053, -14226, -6003]                              # where the climb lands: [x, z] or [x, z, y]
```

Three modes (pick one per ladder):

| keys | mode |
|---|---|
| `top` + `bottom` | **BIDIRECTIONAL** (generic, no real ladder needed): a square trigger zone at each end (centred on `top`/`bottom`, half-size `zone_radius`, default 150); the top zone teleports you down, the bottom zone teleports you up — your location picks the direction, so it climbs both ways. Each end is `[x, z]` or `[x, z, y]`. |
| `zone` + `climb` | **FAITHFUL**: a `"<name>.ladderN.climb.bin"` sidecar (the real ladder's exact climb), written by `ff9mapkit import` (which also auto-widens `zone` to span both climb ends). |
| `zone` + `to` | **EMULATED ONE-WAY**: 3–5-corner trigger (4 are auto-made IsInQuad-safe) that teleports to a single `[x, z]`/`[x, z, y]`. |
| `animation` | (emulated modes) optional climb gesture — a **one-shot** anim id — played before the move. |

How it works: the kit adds a climb function to the **player** entry and a region whose tread shows
`Bubble(1)` and whose action func runs `DisableMove ; RunScriptSync(2, 250, <tag>) ; EnableMove`.
`RunScriptSync` runs the climb **in the player's own context** (so the move moves the player) and
waits for it — sidestepping the fact that the controlled player's script loop is suspended while you
have control.

Two climb modes:
- **Emulated (`to`)** — a clean teleport to the destination. Generic; works for any ladder you author
  from scratch. **One-way**; for up-and-down add a second `[[ladder]]` with the zone/`to` reversed.
- **Faithful (`climb`)** — what `ff9mapkit import` emits when you fork a real field: the game's exact
  climb, grafted **verbatim** (perspective-correct jump arcs, the per-rung jump animations, and the
  `SetPitchAngle` forward-lean). It reads your height to climb **up or down** from one zone, so it's
  inherently bidirectional. The climb launches its lean via `STARTSEQ` helper entries; `import` writes
  those as companion `<name>.ladderN.seqN.bin` sidecars and the build grafts them at free entry slots,
  remapping the climb's `STARTSEQ` args automatically — you don't touch them. (A `climb` sidecar with a
  missing `.seqN.bin` companion is a hard build error.)

---

## `[[event]]` (optional, repeatable)

A region the player **walks into** that fires authored logic — show a message, give an item / gil,
set a story flag — optionally **once** (a looted chest, a one-time line, an ATE). Built on the same
flag-gated conditional region as the camera switch; any number of events share one arming slot.

```toml
[[event]]                 # a treasure: give a Potion + a message, once
zone = [[300,-400],[700,-400],[700,-800],[300,-800]]   # 4 convex (x,z) corners
give_item = [232, 1]      # [item_id, count]
gil = 500                 # (optional) also add gil
message = "Got a Potion!" # (optional) popup dialogue

[[event]]                 # a repeatable ambient line
zone = [[-700,-400],[-300,-400],[-300,-800],[-700,-800]]
message = "A cool breeze blows through."
once = false
```

| key | meaning |
|---|---|
| `zone` | 4 convex `(x,z)` corners of the trigger region (place where the player walks). |
| `message` | text shown in a dialogue window when triggered (added to the field's `.mes`). |
| `speaker` / `tail` | optional — same as `[[npc]]` (a name prefix + the window pointer); see *Speaker names & the tail*. Usually omit `speaker` for an unsigned popup. |
| `give_item` | `[item, count]` — `item` is an **id or a name** (`"Potion"`, also weapons/armor like `"Excalibur"`); `AddItem`. List names + stats with `ff9mapkit items`. |
| `remove_item` | `[item, count]` — **take** items from the bag (id or name); `RemoveItem`. The symmetric counterpart of `give_item` — pair the two for a **trade**, or use alone for a quest-item consume. |
| `received` | *(give_item only)* `true` = show the canonical FF9 **item-get window** ("Received \<item\>!", window type 7) instead of a plain message — `SetTextVariable(0, item)` + `[ITEM=0]`. |
| `require_space` | *(give_item only)* `true` = **chest behavior**: skip the whole event (and don't set the `once` flag, so it's retryable) if the bag is full — `if (GetItemCount(item) < 99) { … }`. |
| `gil` | gil to give; **negative subtracts** (e.g. `gil = -100` charges 100). `AddGil` / `RemoveGil`. |
| `set_flag` | `[var, value]` — set a GlobBool story flag (gate other content on it). |
| `once` | `true` (default) = fires once ever, then never again (a GlobBool persists the state — a looted chest). `false` = fires **continuously while the player stands in the zone** (FF9's region trigger is *level*-triggered, not edge-triggered — a `false` message re-pops the instant you close it if you're still inside). Use `true` for a one-time line; `false` suits a continuous effect. A true "once per visit" (re-fires only after you leave and re-enter) isn't supported yet — it needs a leave-detecting re-arm zone. |
| `flag` | explicit (save-persistent) flag index for the `once` guard (default auto from `8000`, a high band clear of base-game flags; override for a shipped mod to avoid clashes). |
| `requires_flag` / `requires_flag_clear` | GlobBool index (or a `[[flag]]` name) — the event only fires when that story flag is SET / CLEAR (gate one event behind another). |

> An event needs at least one action. The same conditional-region primitive underlies chests, story
> flags, and one-time triggers. A faithful treasure chest is `give_item` + `received = true` +
> `require_space = true` + `once = true` — which compiles to FF9's exact chest shape
> `if (GetItemCount < 99) { if (!opened) { opened = 1; AddItem; SetTextVariable; window-7 "Received …!" } }`
> (effects before the acknowledgement; dedup flag first; verified byte-for-byte against real fields).

### Story flags & branching

A **story flag** is a single bit in FF9's **save-backed** event memory (the engine's *Global*
variable scope — `gEventGlobal`) that an event SETs (`set_flag = [N, 1]`) and other content reads
(`requires_flag = N`). Being save-backed, it **persists across field reloads and saves** — so a
looted chest stays looted, a one-time scene stays played. (The kit uses the persistent *Global* bool,
not the transient per-field *Map* bool.) That's how the world gains state: hit a switch (event
`set_flag`) → a guard appears (`[[npc]] requires_flag`) and a door unlocks (`[[gateway]]
requires_flag`). The kit's auto `once` flags occupy a high band (from **8000**). **Pick your explicit
flag indices in the provably-safe band [8512, 16320)** — real FF9 uses bit-flags up to **8511** (the
treasure-chest "opened" bitfield is bits **8376–8511**), so an index there silently corrupts the
player's save. The lint enforces this. For unbounded mod state beyond simple flags, Memoria also
provides save-backed vector/dictionary stores (a future kit feature).

**Name your flags (optional `[[flag]]` table).** Instead of tracking raw indices, declare a name once
and gate by it — readable, and the kit checks both sides resolve to the same bit:

```toml
[[flag]]
name  = "lever_pulled"
index = 8520            # must be in [8512, 16320), clear of real-FF9 usage

[[gateway]]
to = 4002
requires_flag = "lever_pulled"      # a NAME or a raw int both work
```

In a **campaign**, put shared cross-field flags in a `[[flag]]` table in `campaign.toml` (placed above
the per-member auto-flag blocks) — every member can then gate by that name (`field A` `set_flag`,
`field B` `requires_flag`), and `lint-campaign` verifies the producer exists. Browse the built-in
registry of FF9's known flags / reserved regions / scenario milestones with **`ff9mapkit flags`**.

**Inspect a save:** **`ff9mapkit flags-inspect <save.json>`** decodes a save's `gEventGlobal` — the
ScenarioCounter (+ nearest story beat), FieldEntrance, treasure-hunter points, opened-chest count, and
set story bits grouped by region. (Reads the open JSON/Base64 form; an encrypted on-disc save must be
decrypted first.)

**Check your logic before building:** `ff9mapkit lint <field.toml>` (or the GUI's *Check logic*
button) reports schema errors plus story-flag lints — a `requires_flag` that no event ever sets (dead
content), an explicit flag index that collides with an auto-allocated `once` flag, an index inside the
real-FF9 chest band, and duplicate entity names. `build` runs the same lints and shows them as warnings.

### `[startup]` — assert the story beat (preset state at field entry)

A **forked** real field boots with a **zero `gEventGlobal`**, so every story-gated NPC/door/event takes
the not-yet-happened branch and the room plays in its scenario-zero state. `[startup]` lets you **assert
the beat the field represents** — set the ScenarioCounter and/or specific story bits, unconditionally, at
field load (they're prepended to Main_Init, so every gate evaluated afterwards sees the asserted state):

```toml
[startup]
scenario = 7200                      # the ScenarioCounter value, OR an area name: scenario = "Alexandria Castle"
flags = [
  { flag = 3712, value = 1 },        # a REAL story bit (an Alexandria-town event flag) — asserts it happened
  { flag = "lever_pulled", value = 1 },  # or a [[flag]] name
]
```

- **`scenario`** — an int (`0`–`32767`; every real beat is ≤ 12000) or an area name resolved against the
  registry (`ff9mapkit flags` lists them). Writes the save-backed ScenarioCounter (`gEventGlobal` byte 0).
- **`flags`** — a list of `{ flag = <index|name>, value = 0|1 }`. Unlike authored `set_flag` (which must use
  the safe `[8512, 16320)` band), a `[startup]` preset is **meant** to assert REAL FF9 story bits (below
  8512) — that's the point — so the safe-band rule does **not** apply. The lint still flags a preset into a
  genuinely *reserved* region (the chest bitfield, the byte-23 menu handshake, worldmap-unlock bits, the
  choice scratch), which would corrupt engine/save state rather than assert a beat.

The presets **re-assert on every field entry** (idempotent — right for a fork that stands for one beat). For
a multi-field chain, put `[startup]` on the **entry** field only. v1 is author-side (you assert the beat —
you have the game knowledge); it does not yet preset per-door spawn (a separate gap). To **fire** a beat on
entry (rather than just preset state) — e.g. re-author an entry cutscene for a synthesize fork — use
`[[on_entry]]` below. See `docs/FORK_FIDELITY.md`.

### `[[on_entry]]` — fire a beat on field entry (gated, once)

A real field's **entry cutscene** runs from the field's own `.eb` (entry-0 + actor sequences), so a
**`--verbatim`** fork already carries it. `[[on_entry]]` is for the **synthesize** path (which doesn't ship
the donor `.eb`) and for **adding** a new gated entry beat: fire a narration **message** and/or
**story-state writes** the moment the player **enters** — but **only when the story state matches**. That
gating is what `[startup]` (unconditional, every entry) and `[cutscene]` (ungated) can't express:

```toml
[[on_entry]]
requires_scenario = "Dali (underground)"   # fire ONLY when the ScenarioCounter == this beat (int or area name)
requires_flag = "met_the_elder"            # ...and/or only when this story bit is set (requires_set = false → clear)
message = "The village lies deserted..."   # a narration window (control-locked, shows during the entry fade)
set_scenario = 2710                         # advance the beat on this (first) entry (int or area name)
set_flags = [{ flag = "saw_intro", value = 1 }]
once = true                                 # default: fire once ever (a save-persistent once-flag). false → every entry
# flag = 8300                               # explicit once-flag index (REQUIRED in a campaign member; auto 8300+ otherwise)
```

- It's a **list** — author several entry beats, each independently gated.
- Each hook needs at least one of **`message`** / **`set_scenario`** / **`set_flags`**.
- The gates (`requires_scenario` / `requires_flag`) sit *outside* the once-check, so a hook whose condition
  isn't met yet returns without spending its once-flag — it can still fire on a **later** entry once the beat
  is reached.
- `set_scenario` / `set_flags` follow the same band rules as `[startup]` (assert REAL story bits below 8512;
  the lint flags a write into a genuinely *reserved* region). `message` shares the field's `.mes` block.
- A campaign member's per-member flag block is fully reserved, so a `once` hook there needs an explicit
  `flag = N` (the build raises a clear error otherwise).

### `[party]` — add/remove party members at field entry

Change **who's in the party** (the MENU + BATTLE roster) when the field loads. This is the authoring
complement to `import --swap-player` (which changes who you **walk as**): field *control* and party *state*
are decoupled — `[party]` touches the roster, not the character you move.

```toml
[party]
add    = ["steiner", "vivi"]   # add these existing playable characters (B_PARTYADD)
remove = ["zidane"]            # optional: remove these (RemoveParty)
```

- Names are case-insensitive: `zidane vivi garnet steiner freya quina eiko amarant beatrix cinna marcus
  blank` (aliases `dagger`→garnet, `salamander`→amarant); a bare `0`–`11` CharacterOldIndex also works.
- The adds are FF9's real **JOIN** form (in-game proven): an added member arrives with their normal starting
  equipment (the 12 character structs exist at boot). `remove` runs first (free a slot), then `add`. Adding a
  character already in the party, or past the 4-slot cap, is a harmless no-op. **Don't `remove` every member** —
  an empty party hangs the menu/leader cursor (the build can't see runtime party state, so this is on you).
- Prepended to **Main_Init**, so it applies at field load. **`.eb`-only, no DLL.** FF9 renders only the party
  **leader** in the field, so an added member shows in the menu/battle, **not** as a walking follower. Adding
  a brand-new *custom* character (not one of the 12) needs an engine fork — out of scope here.
- ★ **Caveat:** if the field's own Main_Init runs `SetPartyReserve` (rebuilds the roster) **after** our
  prepend, it can wipe the add — the build **warns** on a verbatim fork where this is the case. A synthesized
  field never resets the party. Pair with `[startup]`/`[[gateway]]` to also set the story beat.

---

### `[start_inventory]` / `[[equipment]]` — new-game starting bag & default gear

Set what the player **starts a New Game with** — the starting inventory and each character's default
equipment. Unlike `[startup]`/`[party]` (which are `.eb` field-load ops), these are emitted as **mod-global
CSV deltas** at build time (`StreamingAssets/Data/Items/InitialItems.csv` + `…/Data/Characters/DefaultEquipment.csv`),
engine-independent (stock Memoria). They're read **once at new-game init**, so they affect a true **New Game**
only (not an F6 / campaign mid-game entry) and compose with story_flags' seamless New-Game entry + `[startup]`/`[party]`.

```toml
[start_inventory]                              # the FULL starting bag (REPLACES the base bag entirely)
items = [["Potion", 20], ["Phoenix Down", 5], ["Tent", 3], ["Ether", 10]]

[[equipment]]                                  # a character's starting loadout (partial: only the chars you list)
character = "steiner"
weapon = "Excalibur"
head   = "Genji Helmet"
armor  = "Genji Armor"
# wrist / accessory omitted -> those slots start EMPTY
```

- These are **mod-global** (one per mod) — put them on the **ENTRY field's** `field.toml` only (the field New
  Game lands in; for a chain, the entry member). The build **warns** if they land on more than one field.
- **`[start_inventory]`** → `InitialItems.csv`, which the engine reads **highest-priority-wins** (not merged):
  it **replaces the base starting bag**, so list the complete inventory. A stacked mod folder that also defines
  `InitialItems.csv` would shadow it (the build warns). Items by name or id; counts clamp to 99; dup ids sum.
- **`[[equipment]]`** → `DefaultEquipment.csv`, which the engine **merges** low→high: a partial delta overrides
  only the characters you list (others keep the base game's). Each `[[equipment]]` is a character's COMPLETE
  loadout — slots `weapon` / `head` / `wrist` / `armor` / `accessory` (name or id; **an omitted slot starts
  empty** — the row replaces the whole default set, it's not a per-slot patch). Characters `zidane`..`beatrix`
  + `marcus2`/`beatrix2`/`blank2`. Per-character gear is applied when a character joins, so it composes with
  `[party]` (an added member arrives wearing its `[[equipment]]` gear).
- **In-game only:** verify a real New Game starts with the right bag/gear (the kit can't see the running game).

---

### `[[shop]]` — a custom shop (inventory + opener)

Define a shop the player can buy from. A shop has two parts — its **inventory** (the items it stocks) and an
**opener** (how the player opens it) — and both are engine-independent (stock Memoria, no DLL).

```toml
[[shop]]
id = 40                                        # the shop slot (>= 32; 0-31 are the base game's shops)
comment = "Hut Item Shop"                      # a label (optional; for the CSV + your own reference)
sells = ["Potion", "Hi-Potion", "Phoenix Down", "Tent", "Ether"]   # the stock (item names or ids)

# --- open it from a shopkeeper NPC (the authentic "talk to the merchant" UX) ---
[[npc]]
name = "Shopkeeper"
pos = [0, -700]
dialogue = "Welcome! Care to buy something?"   # an optional greeting shown before the shop opens
opens_shop = 40

# --- OR open it from a standalone press-region (walk up to a counter, no NPC) ---
[[shop]]
id = 41
sells = ["Ether", "Tent"]
zone = [[-400, -900], [400, -900], [400, -500], [-400, -500]]   # the press area
bubble = true                                  # the floating "!" prompt (default true)
```

- **Inventory** → a `StreamingAssets/Data/Items/ShopItems.csv` delta, written once at build time. The engine
  **merges** shops by id over the base file (which supplies shops 0-31), so the delta lists only your custom
  shops. Items by name or id; duplicates within a shop collapse; the order you list is the order shown.
- **Shop ids** are **`>= 32`** (0-31 are vanilla; a clash **overrides** that vanilla shop — allowed, but the
  build warns). An id is also the `Menu` sub-id, so it is **`<= 255`**. Ids must be unique across the mod
  (a duplicate is warned, last-wins — the engine's own merge rule). Shops may live on **any** field's
  `field.toml` (unlike the entry-only new-game state) — they all collect into one `ShopItems.csv`. Because the
  engine **merges** `ShopItems.csv` by id across stacked mod folders, two **worktrees** that both pick the same
  custom id collide silently (the higher-priority folder wins) — give each worktree its own shop-id sub-band,
  the way field-id bands are split.
- **Opener** → `Menu(2, id)` (the same op family as the save point's `Menu(4, 0)`). Either:
  - **`[[npc]] opens_shop = N`** — talking to that NPC opens shop `N`. `N` may be a **vanilla** shop (0-31)
    too (e.g. open Dali's weapon shop). Its `dialogue`, if any, is the greeting shown first.
  - **`[[shop]] zone = [...]`** — a press-to-interact region opens the shop (place a cosmetic
    `[[npc]]`/`[[prop]]` merchant over it for the visual, like the save moogle). `bubble = false` hides the "!".
- A `[[shop]]` with **neither** an `opens_shop` reference nor a `zone` still writes its inventory CSV — useful if
  another field opens it — but nothing in-game opens it on its own.
- **Scope:** the inventory CSV ships for **any** build (single field, campaign, or verbatim fork). The synthesized
  **opener** (NPC/region) is injected on the **synthesize** path (like `[[savepoint]]`/`[[event]]`); a `--verbatim`
  fork carries the donor's own logic, so wire the opener with the kit's blocks on a synthesized field.
- **In-game only:** verify the shop opens and stocks the right items (the kit can't see the running game).

---

### `[[synthesis]]` — a custom synthesis shop (recipes + opener)

A **synthesis shop** combines ingredient items + gil into a new item (the Black-Mage-Village / Treno synthesist).
Like `[[shop]]`, it's two parts — **recipes** (the data) and an **opener** — and both are stock-Memoria, no DLL.

```toml
[[synthesis]]
shop = 40                                      # the synth-shop id (NOT a [[shop]] buy id; 32..255)
recipes = [
  { result = "Butterfly Sword", ingredients = ["Dagger", "Mage Masher"], price = 300 },
  { result = "The Ogre",        ingredients = ["Mage Masher", "Mage Masher"], price = 700 },  # need 2 Mage Mashers
]
# open it from an NPC (opens_shop = the synth id) OR a standalone press-region:
zone = [[-400, -900], [400, -900], [400, -500], [-400, -500]]
```

- **Recipes** → a `StreamingAssets/Data/Items/Synthesis.csv` delta. Each recipe = `result` (the item produced) +
  `ingredients` (the items consumed — **duplicates matter**: `["Mage Masher", "Mage Masher"]` needs two) + `price`
  (gil). The kit **mints** each recipe an id **above the base max** and the engine **merges** by id, so your delta
  only **adds** recipes (never clobbers a vanilla one). A shop's recipes are every row whose synth-shop id matches,
  so several `[[synthesis]]` blocks on the same `shop` combine.
- **The synth-shop id** is what makes a shop a *synthesis* shop: the engine opens id `N` as Synthesis **iff `N` is
  not in `ShopItems.csv`** (`ff9buy.FF9Buy_GetType`). So the `shop` id must be **`>= 32`** (0-31 are base buy
  shops), **`<= 255`** (the `Menu` sub-id), and must **not** also be a `[[shop]]` id — a shop id present in
  `ShopItems.csv` opens as a **buy** shop and your recipes won't show (the build **errors** on the collision
  within a field, and **warns** when the two live on different fields). You *may* target a vanilla synth id
  (32-39) to **add** a recipe to an existing synthesist.
- **Opener** → the **same** `Menu(2, id)` as a buy shop (the engine decides buy-vs-synthesis from the id alone):
  - **`[[npc]] opens_shop = 40`** — talk to the synthesist (works unchanged; `40` opens the synthesis shop because
    it isn't a buy shop).
  - **`[[synthesis]] zone = [...]`** — a standalone press-region (place a cosmetic merchant over it). `bubble = false`
    hides the "!".
- **Scope:** the recipe CSV ships for **any** build (incl. verbatim); the synthesized opener is injected on the
  **synthesize** path only (a `--verbatim` fork carries the donor's own logic).
- **★ RELAUNCH to apply:** `Synthesis.csv` loads once at startup (`ff9mix`) — F6 → Reload won't pick it up.
- **Needs a reachable FF9 install at build time** (it reads the base `Synthesis.csv` header + recipe ids; the repo
  commits no game data).

---

## `[[weapon]]` / `[[armor]]` / `[[item]]` / `[[equip_bonus]]` — tune EXISTING item stats (optional, repeatable)

**Rebalance gear** — change a weapon's power, an armor's defence, an item's price, or an item's **equip stat bonus**.
A pure data patch (**no DLL**). Don't confuse these with the `[[equipment]]` *loadout* slots above: those say *who
wears what at New Game*; these change *what the gear DOES*.

```toml
[[weapon]]
name = "Mage Masher"        # the item (a name or 0-254 id); must be a weapon
power = 30                  # 0-255  (Weapons.csv Power)
elements = ["Fire"]         # any of Fire/Ice/Thunder/Earth/Water/Wind/Holy/Dark (or a 0-255 bitmask)
category = ["short-range", "throw"]   # weapon class: short-range/long-range/throw/offset (throw = Amarant-throwable)
status_index = 9            # the StatusSets.csv row it inflicts on hit (an existing status-set id)
rate = 30                   # 0-100 percent chance to inflict that status (physical hit itself is always 100)

[[armor]]
name = "Bronze Armor"       # must be an armor
p_def = 20                  # P.Def      ┐
p_eva = 10                  # P.Eva      │ 0-255 each (Armors.csv); set only the ones you want
m_def = 5                   # M.Def      │
m_eva = 0                   # M.Eva      ┘

[[item]]
name = "Excalibur"          # any item (weapon/armor/consumable)
price = 5000                # buy price  (0-9,999,999)
sell = 2500                 # sell price (optional; otherwise unchanged)
equippable_by = ["Steiner", "Beatrix"]   # REWRITE who can equip it (exactly these; everyone else cleared)

[[equip_bonus]]
name = "Bone Wrist"         # any EQUIPPABLE item (weapon/wrist/head/body/accessory/gem)
speed = 0                   # the 4 growth-stat bonuses (dex/str/mgc/wpr) ─┐ 0-255 each (Stats.csv);
strength = 3                #   Speed=Dexterity, Spirit=Will                │ the input the level-up
magic = 0                   #                                               │ stat-growth accumulator
spirit = 0                  #                                              ─┘ reads (~32 levels = +1)
attack_element = ["Fire"]   # STRENGTHEN your Fire attacks/magic (dmg boost) ─┐
weak_element = ["Ice"]      # take extra damage from element(s)             │ element name list or a
absorb_element = []         # absorb (heal from) element(s)                 │ 0-255 bitmask; set only
half_element = []           # take half damage from element(s)             │ the ones you want
guard_element = []          # nullify (immune to) element(s)               ─┘
```

- **How it works:** each block emits a **partial CSV delta** into the mod (`Data/Items/{Weapons,Armors,Items,Stats}.csv`).
  The engine **merges** these by id, **whole-row-wins** — so the kit reads the base row from **your install**, changes
  the one field, and writes the complete row back. **Needs a reachable FF9 install at build time** (it reads the base
  columns); without one the patch is skipped with a warning.
- **Mod-global:** any field may tune any item — the deltas are collected across every built field, not tied to where
  the block sits. The same item tuned in two blocks **merges** (later overrides per field; a warning is emitted).
- **`[[equip_bonus]]` and the shared `Empty` row:** an item's bonus lives in `Stats.csv`, keyed by its `BonusId` —
  but **~100 items share the all-zero `Empty` row 0**, so editing that row would buff every other no-bonus item. The
  kit detects this: an item with a **dedicated** bonus row (used by it alone) is edited **in place**; otherwise it
  **mints a fresh `Stats.csv` row and repoints the item's `BonusId`** (in the same `Items.csv` delta as any `[[item]]`
  price edit), isolating the change to that one item. The bonus shows immediately in the status menu on equip
  (`elem = base + bonus`) and drives permanent level-up growth.
  **★ Stacked folders:** the `Items.csv` repoint is per-id whole-row-merged across `FolderNames`, so a *higher*-priority
  stacked mod folder that ships its own row for the same item shadows the repoint — the bonus then silently doesn't
  apply (the minted `Stats.csv` row is orphaned). Deploy equip-bonus edits to your **highest-priority** folder (the
  same rule as the new-game bag / custom shop ids).
- **Weapon `category` / `status_index` / `rate`:** `category` is the weapon class (`short-range`/`long-range`/`throw`/
  `offset`, by name or a 0-255 bitmask) — adding `throw` makes a weapon eligible for Amarant's **Throw**. `status_index`
  is the **`StatusSets.csv` row** the weapon's status effect points at (an *existing* status-set id — it indexes the
  shared battle status-set table, validated against your install). **★ How it triggers:** in Memoria the live consumer
  is **Soul Blade** (Zidane's Skill, restricted to his thief-swords — Butterfly Sword, The Ogre, Exploda, Rune Tooth,
  Angel Bless, Sargatanas, Masamune, The Tower, Ultima Weapon), which applies the weapon's status directly; the
  **normal-attack "Add Status" path is dummied** (`BattleCalculator.TryAddWeaponStatus` has no callers), so a *plain
  Attack does not roll a weapon's status* in the stock build. `rate` (**0-100**) is the infliction chance where a
  formula rolls it — Soul Blade ignores `rate` and inflicts directly, so today `rate` mainly feeds custom NCalc battle
  formulas (`WeaponRate`). An out-of-range `status_index` is a **lint error** (it would be a KeyNotFound battle crash).
- **Item `equippable_by`:** a list of party-character names (`Zidane`/`Vivi`/`Garnet`/`Steiner`/`Freya`/`Quina`/`Eiko`/
  `Amarant`/… incl. `Beatrix`) that **REWRITES** the item's 12 equip-by-character bits — *exactly* the listed
  characters can equip it, everyone else is cleared (it's a replace, not an add). An unknown name is a lint error.
- **Values are clamped** to their range (stats 0-255, price 0-9,999,999, rate 0-100). An unknown item name, the wrong
  type (`[[weapon]]` on a non-weapon, `[[equip_bonus]]` on a non-equippable), a bad element/category/character name, or
  an out-of-range `status_index` is a **lint error** (`ff9mapkit lint`).
- **★ RELAUNCH to apply:** item CSVs load once at game **startup** — F6 → Reload field will NOT pick up a stat
  change. Deploy, then relaunch.
- **Deferred (a later follow-up):** consumable use-effects (`ItemEffects.csv` power/status), synthesis-shop recipes,
  the gear→learnable-ability list, item name/description text, and minting **net-new** item ids (>254, needs a DLL).

---

## `[[choice]]` (optional, repeatable)

A **dialogue choice** — pick from a menu and **branch** on the answer. This is the interaction /
puzzle primitive: a merchant, a "Yes/No" lever, a quest-giver. A choice is triggered **either** by
talking to an NPC (`npc = "<name>"`) **or** by walking into a zone (`zone = [...]`, a lever / sign) —
set exactly one.

```toml
# (A) talk to an NPC:
[[npc]]
name = "Merchant"
preset = "vivi"
pos = [0, -700]

[[choice]]
npc = "Merchant"                       # the NPC you talk to (must match an [[npc]] name)
prompt = "Buy a Potion for 100 gil?"   # the question
[[choice.options]]
text = "Yes, please."                  # the menu row the player selects
reply = "Here you go!"                 # (optional) a line shown after picking it
give_item = ["Potion", 1]              # (optional) [item, count] — id or name
gil = -100                             # (optional) charge 100 gil
set_flag = [8001, 1]                   # (optional) raise a story flag
[[choice.options]]
text = "No, thanks."                   # put the "decline" option LAST (cancel/B picks the last row)
reply = "Come again!"

# (B) a zone (a lever): stand on it and PRESS the action button (default trigger = "action"):
[[choice]]
zone = [[300,-400],[700,-400],[700,-800],[300,-800]]   # 4 convex (x,z) corners
prompt = "Pull the lever?"
[[choice.options]]
text = "Pull it."
reply = "*kachunk*"
set_flag = [8001, 1]
[[choice.options]]
text = "Leave it."                     # non-destructive: press again to retry (re-usable)
```

| key | meaning |
|---|---|
| `npc` | the `[[npc]]` name to talk to (talk-triggered). **Exactly one of `npc` / `zone`.** |
| `zone` | 4 convex `(x,z)` corners — a zone trigger (lever/sign). **Exactly one of `npc` / `zone`.** |
| `trigger` | *(zone only)* `"action"` (default) = stand on the zone and **press** to open it — re-usable, "decline" is non-destructive (like an FF9 lever/sign). `"walk"` = auto-pops the moment you tread the zone. |
| `once` | *(zone + `trigger="walk"` only)* `true` (default) = once ever (persistent flag); `false` = once per field visit. A `walk` menu must be flag-gated to avoid re-popping every frame, so a `walk` decline still consumes that arming — prefer `action` for a re-usable lever. |
| `flag` | *(zone + `walk` only)* explicit gate-flag index (default auto from `8200`, GLOB). |
| `prompt` | the question text (added to the field's `.mes`, above the option rows). |
| `speaker` / `tail` | optional — same as `[[npc]]` (a name prefix + window pointer). |
| `options` | a list (`[[choice.options]]`) of **≥ 2** rows the player picks from. |
| `default` | *(optional)* option index highlighted when the menu opens (0 = top row; default 0). |
| `cancel` | *(optional)* option index B/Cancel picks (`-1` or omit = last row, the FF9 default). |
| `options[].text` | the menu row shown for that option (kept short — it's one line). |
| `options[].disabled` | *(optional)* `true` = the row is always **removed** from the menu (no widget). |
| `options[].requires_flag` | *(optional)* hide this row **until** story flag N is set (flag-gated). |
| `options[].requires_flag_clear` | *(optional)* hide this row **once** story flag N is set. |
| `options[].reply` | optional line shown after the player picks it. |
| `options[].give_item` / `remove_item` / `gil` / `set_flag` | optional actions, same as `[[event]]` — `give_item`/`remove_item = ["Potion", 1]` (id or name; a trade row gives one item and takes another), `gil` negative charges, `set_flag` raises a story flag. |

**Pre-choose config (default / cancel / disable).** `default` sets the initially-highlighted row,
`cancel` sets which row B/Cancel picks, and `options[].disabled = true` **removes** a row from the menu
(FF9 builds no widget for a masked row — it disappears, it isn't greyed-and-visible). Disabling does
**not** renumber the others — a hidden row keeps its index and `GetChoose()` (and your per-option
branch) still uses the **absolute** index. The kit emits the `EnableDialogChoices` opcode + a
`[PCHC]`/`[PCHM]` text tag (Memoria `Dialog.SetupChoose`); a plain choice with none of these set is
byte-identical to before. Grounded + in-engine-probe-verified against the field-100 ATE menu.

> **Engine limitation (default + disable don't combine):** `default` and `cancel` work on their own,
> and `disabled` works on its own. But a `default` that sits **at or after** a `disabled` row is **not
> honored** — FF9's `SetChooseParam` converts the default to an available-row index while `Dialog`
> reads it as absolute, so it falls back to the first available row. The build **warns** when you hit
> this. Use `default = 0`, or don't hide rows before your default.

**Flag-gated options (hide until a story flag).** An option can carry `requires_flag = N` (shown only
once flag N is **set**) or `requires_flag_clear = N` (shown only while flag N is **clear**) — e.g. a
shopkeeper's *"Use the Gate Key"* row that appears once you've picked the key up, or a *"(ask again
later)"* row that disappears after a quest flag flips. The kit builds the availability mask at runtime
in a scratch word (`set_var` the always-on rows, `if(flag) or_var` each gated bit) and passes it to
`EnableDialogChoices` as an expression — the exact pattern FF9 itself uses for the moogle-mail menu
(Dali/Storage), verified byte-for-byte. As above, keep `default = 0` (or before any gateable row) so
the default highlight is honored; the build warns otherwise.

**How the pick is read (engine fact):** the choice window is synchronous, so the picked row index
(0-based) is finalized before the script continues; the kit branches on it with `GetChoose()` (the
engine's `ETb.sChoose`). Player movement is **locked while the menu is open** (`DisableMove` →
`EnableMove`, as a real FF9 shop does) so the d-pad navigates the menu without also walking the
character. **Cancel (B) selects the LAST row** by default — so make the last option the "decline" /
safe choice. An option's `set_flag` feeds the same story-flag system above (`requires_flag` on
NPCs/gateways/events), so a choice can unlock a door, reveal an NPC, or gate a later event. (Grounded
byte-for-byte in a real FF9 shop choice; in-game verified.)

**One-shot vs re-usable.** An `action` zone-choice is re-usable by default (correct for a merchant
you buy from repeatedly). To make a **one-time lever**, gate the choice on a flag the consuming option
sets — the SAME flag that drives whatever it triggers:

```toml
[[choice]]
zone = [[300,-400],[700,-400],[700,-800],[300,-800]]
prompt = "Pull the lever?"
requires_flag_clear = 8001          # only offered while not yet pulled
[[choice.options]]
text = "Pull it."
set_flag = [8001, 1]                # marks it pulled -> the lever stops responding (and opens the door)
[[choice.options]]
text = "Leave it."                  # sets nothing -> still pullable
```

The door it opens would then use `[[gateway]] requires_flag = 8001`. Once spent, the lever **fully
disappears** — the consuming option removes the region (no leftover interaction prompt), and the Init
won't re-create it on later visits while the flag is set. (Want an "it won't budge" message instead?
Add a second interactable on the same spot gated `requires_flag = 8001`.)

---

## `[cutscene]` (optional)

An ordered, **control-locked** scripted sequence that plays on field entry — the one thing the
declarative content can't express (steps run *in order*). The player can't move while it runs.

```toml
[cutscene]
once = true          # play once, then never again (default; save-persistent flag). false = every entry.
# flag = 8100        # explicit GlobBool for the once-guard (default 8100, save-backed)
steps = [
  { say = "The hut is silent..." },   # a window; blocks until the player dismisses it
  { wait = 30 },                        # pause 30 frames
  { say = "...for now." },
  { set_flag = [210, 1] },              # advance/record story state mid-scene
]
```

| step (one key each, plus optional modifiers) | meaning |
|---|---|
| `say` | a dialogue/narration window (added to the field's `.mes`). A `say` step may also carry `speaker` and `tail` (e.g. `{ say = "...", speaker = "[VIVI]", tail = "UPL" }`) — same as `[[npc]]`. |
| `wait` | pause this many frames. |
| `set_flag` | `[var, value]` — set a GlobBool story flag mid-scene. |

The scene auto-locks control (`DisableMove`…`EnableMove`); with `once` it won't replay on re-entry.

### Actor cutscenes — `actor = "<npc name>"`

Add `actor = "<an [[npc]] name>"` to make the cutscene drive **that NPC**: walk, animate, turn. The
sequence is spliced into the NPC's own script (so the movement steps act on it), the player is locked
for the duration, and it plays once. This is the iconic "a character walks in and talks".

```toml
[[npc]]
name = "vivi"
preset = "vivi"
pos = [0, -300]            # where Vivi RESTS (and where he is on a replay visit)
dialogue = "..."

[cutscene]
actor = "vivi"            # the steps run in Vivi's context
once = true
# warmup = 30            # frames to wait before the actor moves (default 30). The field's entry
                         #   fade + smooth-updater must settle first, or the actor circles on load
                         #   and its walk hangs. Bump it if the actor still circles on entry.
steps = [
  { teleport = [-2000, -300] },   # snap off-screen (instant) so he can walk IN
  { walk = [0, -300] },           # walk to his resting spot (= his pos)
  { face_player = true },          # turn to face the player
  { animation = "glad" },          # a gesture BY NAME (run: ff9mapkit animations vivi)
  { say = "...hi." },              # a dialogue window
]
```

Actor steps (only valid when `actor` is set — they need the NPC's context):

| step (one key each) | meaning |
|---|---|
| `walk` | a **target** to walk to — a marker/entity **name** (`"fountain"`, `"@player"`, `"@Steiner"`) or raw `[x, z]`. Uses the NPC's walk animation; blocks until it arrives; turns tight (no orbit). **Auto‑routes** around walls/characters if the straight line is blocked (see *Reliability*). Optional `speed = N`. See *Movement targets* below. |
| `path` | a **list** of targets to walk through in order — `path = ["door", "fountain", "altar"]` (names or `[x,z]`). Each leg is a straight walk, stall‑checked but **not** auto‑routed — use it to force an exact route (a plain `walk` already routes itself). |
| `teleport` | a target to **instantly** move to (name or `[x, z]`). Put it **first** to start a walk-in from off-screen — a leading teleport runs before the warm-up so the actor settles there, then walks in. |
| `animation` | a gesture **by name** (`"glad"`, `"angry"`, `"yawn"`, …) resolved against the actor's preset model, **or** a raw numeric id. Played, then held ~40 frames (no hang on a looping clip). See *Character gestures* below. |
| `turn` | angle (`0`=south, `64`=west, `128`=north, `192`=east) — turn to face it, animated. |
| `face_player` | `true` — turn to face the player. |

`say` / `wait` / `set_flag` also work in an actor cutscene (interleaved in order). The NPC ends where
its last `walk`/`teleport` leaves it on the first visit; on a replay visit it's at its `pos`, so end
the last `walk` at `pos` (or just `teleport` in and `walk` back to `pos`) to stay consistent.

#### Movement targets (`walk` / `teleport` by name)

Instead of typing coordinates, give a walk/teleport a **name** so you place the point once (in Blender
or the toml) and reference it everywhere:

- **`[[marker]]`** — a named point: `name = "fountain"`, `pos = [x, z]`. Pure authoring reference (no
  in-game object). Place these visually in Blender, or list them in the toml.
- **`@player`** / **`@spawn`** — the player's spawn point.
- **`@<npc name>`** (or just the name) — that NPC's position, or another marker.

> **Walking *up to* a character.** A `walk` to a live object (`@player` / `@<npc>`) automatically stops
> **just short** of its collision box — you walk up to the character, you don't overlap it. (Walking
> *onto* an object stalls: two characters can't occupy the same ~128‑unit space, so the actor would
> press into the box forever.) A plain `[[marker]]` / `[x, z]` is an exact point and is **not** offset.

```toml
[[marker]]
name = "altar"
pos = [0, -600]

[cutscene]
actor = "vivi"
steps = [
  { walk = "altar" },     # walk to the named point
  { walk = "@player" },   # walk to the player's spot
]
```

**Reliability — walks auto‑route; the build checks the rest.** A FF9 walk is straight‑line and
*synchronous* (the scene blocks until the actor arrives), so a blocked walk would press into the
obstacle forever and **hang the scene**. So the kit **auto‑routes**: when a `walk`'s straight line is
blocked (it crosses a wall or passes through a standing character), the kit finds a route *around* the
obstacle over the walkmesh (A\* + string‑pulling, staying clear of walls and every character's box) and
walks it as a series of legs — `walk = "goal"` just works. It only **warns** when the *target itself* is
bad (off the floor, or inside a character's box) or when **no route exists at all** (e.g. a character
fully plugs a corridor). Use an explicit `path` when you want to force a specific route. (An explicit
`path`'s legs are checked but not auto‑routed.)

#### Character gestures (`animation` by name)

Every playable character has a catalog of field gestures. Pick one by name instead of a numeric id:

```
ff9mapkit animations              # list characters (vivi, zidane, garnet, steiner, freya, quina, eiko, amarant)
ff9mapkit animations vivi         # Vivi's gestures (angry, glad, jump_1, yawn, talk_3_1, ...)
ff9mapkit animations vivi -f talk # filter; add --ids to see the numeric id of each
```

Then `{ animation = "glad" }`. The name is matched against the actor NPC's `preset` (so a `vivi` actor
draws from Vivi's set). Five **core** aliases work for every character: `idle` `walk` `run`
`turn_left` `turn_right`. A name that doesn't exist for that character is a build error (with
suggestions). A raw id still works, and an actor with a *custom model* (no preset) must use ids.
The catalog comes from Memoria's open-source `AnimationDB` (the same source as the field registry).

---

## `[encounter]` (optional)

| key | meaning |
|---|---|
| `scene` | battle scene id (e.g. `67` = Evil Forest, the first/weakest battles). |
| `freq` | encounter frequency `0..255` (default `255`). |
| `pattern`, `scenes` | advanced: pattern + explicit 4 scene ids. |
| `battle_music` | BattlePatch song-play id (default `0` = normal battle theme). |

Adding an encounter automatically adds the after-battle handler the field needs (otherwise the
player freezes on battle return).

---

## `[music]` (optional)

| key | meaning |
|---|---|
| `song` | field BGM song-play id (e.g. `9` = Vivi's Theme). Plays on entry, and resumes after battle if there's an encounter. |
