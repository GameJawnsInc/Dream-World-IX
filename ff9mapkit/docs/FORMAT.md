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
| `borrow_bg` | | **BG-borrow:** a real field's `MAPID` (e.g. `"FBG_N15_BWLB"`) whose art/walkmesh/camera the engine renders while running *your* `.eb` — no custom scene shipped. With it, `[camera]`/`[walkmesh]`/`[[layers]]` are unneeded (the borrowed `camera.bgx` still drives movement/scroll/content guidance). Without it (and no `[field] bgs`) the build ships a full custom scene. The central reuse-a-real-room key. |
| `hide_area_title` | | `true` hides a borrowed room's localized **area-title overlay** from frame 1 (`ShowTile` off) — for a hub/synthesized field that BG-borrows an area-title room (Ice Cavern, Mognet Central) but isn't that place. Range auto-resolved from the borrowed FBG, or set `area_title_overlays = [lo, hi]`. No-op if the borrow has no title. |
| `location` | | the **in-game menu LOCATION** place-name (the card shown bottom-left in the main menu, e.g. `"Prima Vista/Cargo Room"`). FF9's `loc_name.mes` is keyed by the REAL field id, so a custom/forked id shows **blank** without this. Sets a from-scratch field's place-name, or **overrides** a fork's inherited donor title. *(Distinct from `title`, which is only a build-time scene comment — this is what the player sees.)* Emits a `LocationName <id> <text>` directive; needs the **s33** custom engine. |
| `outpost` | | `true` marks this field as an **outpost** for `[deathrules] on_defeat`: on **every entry** the field writes its own id into the kit-reserved "last outpost" var (save-backed; last-write-wins), and a later party wipe warps here instead of the `warp_to` fallback. Semantics: *the last outpost-marked field the player entered*. For a register-on-save/inn policy, skip the tag and write the var (a **UInt16 spanning `gEventGlobal` bytes 1060–1061** — always write it as a whole word; a half-written var reads as a garbage field id and a wipe would warp to nowhere) from an `[[event]]` instead. Works on verbatim forks too (it rides the `[startup]` injection). |

The DictionaryPatch line emitted is: `FieldScene <id> <area> <name> <name> <text_block>` (plus a `LocationName <id> <text>` line when `[field] location` is set).

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
| `entry_settle` | OPTIONAL frames to hold the screen black on field entry before the reveal (absent/`0` = off; `"auto"` = computed). See below. |

**`entry_settle` — hide the warp-in camera ease.** The engine runs a smooth-camera follower on *every*
field; on entry it eases the camera from the scene centre to the player over ~a second (scaled by the
user's `Memoria.ini CameraStabilizer`). Real fields hide this because their entry sequence (title card,
cast setup) fills the time before the reveal — a lean synthesized field reveals almost immediately, so on
a large-delta entry you *watch* the camera drift. `entry_settle = <frames>` inserts
`DisableMove; Wait(n); EnableMove` just before Main_Init's reveal fade: the screen is still black there,
so the camera converges unseen — the same black-hold the real game performs naturally. Use it on
synthesized/BG-borrow fields whose spawn sits far from the camera's initial target (scrolling rooms
especially — `fork-report` suggests it for those); **~45 is the proven starting value** (the World Hub
ships 45–60). **`entry_settle = "auto"` computes the hold for you**: the build measures the warp-in
delta (the px distance between the camera's pre-player-bind rest position and its spawn-centred
target, replicating the engine's projection + viewport clamp), converts it to frames under the
engine's geometric ease (baked for the default `CameraStabilizer = 85` — it's a per-user setting, so
this is best-effort), and clamps to a sane 20–90 band; the chosen value is printed in the build
output and by `lint`. It needs the *arriving* transition to have faded to black — kit gateways and
`fade = true` choice-warps do; a bare debug-menu (~) warp shows the drift regardless (nothing scripted can hide
that path). A `--verbatim` fork does **not** need it (the donor's own entry sequence is carried); the key
is ignored there and `lint` says so. If the requested settle can't be inserted (no plain reveal fade in
Main_Init), the build warns instead of silently skipping.

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

> `entry_settle` works on multicam fields too: it is one **field-wide** black-hold (not per-camera), so
> set it in any one `[[camera]]` block — the build applies the first nonzero value it finds (and `lint`
> flags disagreeing values).

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
| `character_offset` | **DEPRECATED — accepted but ignored** (back-compat no-op). The legacy "slide the floor toward the camera" offset was ripped: the engine-measured character ground offset is `0`, so every authored mesh is written in true world coords with no offset (`build.resolve_walkmesh`). |
| `frame` | **DEPRECATED — accepted but ignored** (back-compat no-op). All authored meshes are now written verbatim in true world coords (`orgPos = 0`, every `floor.org = 0`) — what `ff9mapkit guide` / `cam.to_canvas` predict is exactly where the player walks. (The old `"legacy"` calibrated flat-room path with a character offset is gone.) |

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
walkmesh exports as one floor. As with single-floor meshes, the verts are written verbatim in true
world coords (no offset) — they are already the exact engine positions.

---

## `[player]` (optional)

| key | meaning |
|---|---|
| `spawn` | `[x, z]` where the player appears on entry (the DEFAULT arrival — see `[[player.arrival]]` for per-door spots). |
| `face` | OPTIONAL spawn facing (0..255; 0=south, 64=west, 128=north, 192=east — the same compass `[[npc]]`/chest `face` uses). Absent = the template default (0). |
| `model` | **re-skin who you WALK as** — a model **id**, an exact **GEO name** (`"GEO_NPC_F0_MOG"` the Moogle PC), or an archetype/model name resolved via the Info Hub catalog (the same join `[[npc]] model` uses). Its movement clips (idle/walk/run/turn) auto-resolve. This is the build-side complement to `import --swap-player`. **Movement clips only** — a field that scripts player gestures would glitch, so it's free-roam-only. |

### `[[player.arrival]]` (optional, repeatable) — per-door arrival spots

Real FF9 fields place the player **per entrance**: the departing exit sets the entrance var (`D8:2`)
right before `Field()`, and the destination's player init branches on it to a different (x, z, facing)
per door (Alexandria Main Street has 4). A synthesized field normally collapses this — every door lands
on the one `[player] spawn`. `[[player.arrival]]` compiles the real dispatch:

```toml
[player]
spawn = [0, -2000]        # the default (any entrance without a row below)

[[player.arrival]]
entrance = 1              # matches the [[gateway]]/warp `entrance =` that routes here
pos      = [430, -880]
face     = 128            # optional (0..255 compass, like [player] face)

[[player.arrival]]
entrance = 2
pos      = [-350, -1500]
```

| key | meaning |
|---|---|
| `entrance` | which entrance index this row serves — the value the SOURCE field's `[[gateway]]` / choice-warp / ladder-top wrote (`entrance =`, default 0). One row per entrance. |
| `pos` | `[x, z]` where the player appears when arriving through that entrance. Placement happens **before** the player object is created (frame 0 — no flash of the default spawn). |
| `face` | OPTIONAL facing on arrival (0..255). Absent = keep `[player] face` / the default. |

The build lints each `pos` against the walkmesh like the spawn. Entering with an entrance value that has
no row (including a fresh New-Game/debug-menu warp) uses `[player] spawn` — the rows are pure overrides, so a
field without them is byte-identical to before.

Coverage is audited automatically. `lint-campaign` (and journey lint) walks the campaign's edge graph and
warns when several doors arrive at a member with distinct entrances but no rows (every door lands on one
spawn), when sources all write the same entrance (the destination can't tell them apart), when an inbound
entrance has no row (falls through to the default), and when a row's entrance is never routed (a typo).
Verbatim members are exempt — they carry the donor's real table — and rows *on* a verbatim fork are flagged
as ignored. Field-level `lint` additionally checks self-loop gateways (`to` = the field's own id) against
the rows.

You rarely write these rows by hand for a fork: every **non-verbatim import** (`import` /
`import-chain` members) decodes the donor's real arrival table and emits it as `[[player.arrival]]` rows
automatically, so a forked field keeps its per-door arrivals out of the box.

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
| `speaker` | optional attribution, rendered FF9's own way — the name on its own line, then the dialogue in curly quotes. See *Speaker names & the tail* below. |
| `tail` | the dialogue window's pointer corner (`UPR` default). See below. |
| `requires_flag` | GlobBool index (or a `[[flag]]` name) — the NPC only **appears** when that story flag is SET (its Init returns early otherwise: no model, not interactable). For story-gated characters. |
| `requires_flag_clear` | …only appears when the flag is CLEAR (the inverse — e.g. an NPC that leaves once an event fires). |
| `scenario_min` / `scenario_max` | a **story-beat window** — the NPC only appears while `scenario_min ≤ ScenarioCounter < scenario_max` (min **inclusive**, max **exclusive**). Either bound may be a raw beat number or an area name (e.g. `"Dali"`). This is FF9's **rotating-cast** idiom: the NPC self-gates on the story clock, so it's present only during a stretch of the game. Composes with `requires_flag` (both must hold). See *Rotating casts* below. |
| `holds` | a **prop the NPC holds in hand** — a prop-archetype name (`"cup"`, `"sword"`, `"save_the_queen"`) or a model, or a **list** of them. The kit attaches each prop to the right hand-bone *and* poses the prop + the holder correctly, **auto-resolved for this holder's model** from the shipping `AttachObject` catalog (`tools/extract_attach_poses.py` → `_held_poses.py`). So `holds = "save_the_queen"` on a `beatrix` puts the sword in her hand at her real holding pose. A (holder, prop) pair not in the catalog falls back to bone 11 + the prop's resting pose (and leaves the holder's pose alone). |

### Speaker names & the dialogue tail

FF9 has **no speaker name-box**. Who's talking is shown by the dialogue window's **tail** (the little
pointer), and attribution — when shown at all — is authored into the text. The kit renders `speaker`
**exactly the way the real game does** (byte-censused across 12,711 stock entries, 2026-07-18): the
name on its **own line**, then the dialogue wrapped in **curly quotes** on the next —

```
Vivi
“I missed you, Zidane.”
```

— never `"Vivi: …"` (no stock entry uses a colon join). Two optional keys (on `[[npc]]`, `[[event]]`,
`[[savepoint]]`, `[[choice]]`, and cutscene `say` steps) make that ergonomic:

- **`speaker`** — the attribution. Use one of FF9's **renameable name tags** for a party member so it
  tracks the player's chosen name: `speaker = "[VIVI]"` (also `[ZDNE]` Zidane, `[DGGR]` Dagger,
  `[STNR]` Steiner, `[FRYA]`, `[QUIN]`, `[EIKO]`, `[AMRT]`, `[PTY1]`–`[PTY4]`). A dialogue line that
  is **entirely parenthesized** renders as FF9's *silent-thought* form — name line + `(the thought)`,
  no quotes (`dialogue = "(Hmm... She sure is dressed funny.)"`). **No speaker = no name line and no
  quotes** — the stock convention for narration, signs and system windows. You can also just type the
  name and quotes into `dialogue` yourself for full control (e.g. the rare unattributed hushed aside
  `“(Kupo!)”`).
- **`tail`** — which corner the window's pointer comes from: `UPR` (default) `UPL` `LOR` `LOL` upper/
  lower-right/left, `UPC` `LOC` upper/lower-center, the `…F` force variants, or `DEFT` (engine
  default/auto). Handy when the default points the wrong way for an NPC's on-screen position.

```toml
[[npc]]
name = "Vivi"
preset = "vivi"
dialogue = "I missed you, [ZDNE]."   # renders as the name line + “I missed you, Zidane.”
speaker = "[VIVI]"                    # renameable name; or just "Vivi"
tail = "UPL"                          # pointer from the upper-left
```

Multi-line dialogue keeps **one** quote pair — the auto-wrap opens `“` on the first dialogue line and
closes `”` on the last, exactly as stock does. (Avoid `[PAGE]` inside a *spoken* line with a speaker:
stock never quotes across a page break — give each conversation line its own entry/`say` step.)

### Rotating casts (story-event fields)

Real FF9 town/story fields don't have a fixed roster — the cast **rotates by story progress**. The
shopkeeper in a shop is a different character on disc 1 vs. disc 4; a guard is at his post only during a
siege. The engine does this by having each actor self-gate on the **ScenarioCounter** (the ordered story
clock): the object's Init returns early — no model, no interaction — unless the story is inside its beat.

`scenario_min` / `scenario_max` author exactly that. Put two NPCs **at the same spot** with **adjacent
half-open windows**, and the cast swaps at the boundary — a rotating shopkeeper in four lines:

```toml
[[npc]]
name = "keeper_disc1"
model = "GEO_NPC_F0_BOM"
pos = [120, -400]
opens_shop = 4
scenario_min = 2600     # appears from the Dali beat (ScenarioCounter >= 2600) …
scenario_max = 11090    # … until the Pandemonium beat (< 11090)

[[npc]]
name = "keeper_disc4"
model = "GEO_NPC_F1_BBA"
pos = [120, -400]       # SAME spot
opens_shop = 4
scenario_min = 11090    # takes over at 11090 onward — the two windows tile seamlessly
```

Because the window is **half-open** (`[min, max)`), adjacent members never overlap (no stacked pair) and
leave no gap. A one-sided window is fine: `scenario_min` alone = "from this beat on"; `scenario_max` alone
= "until this beat". Combine with `requires_flag` for a member gated on both a beat *and* a story bit. To
find the right beat numbers for a real field you're forking, `ff9mapkit fork-report <field>` prints the
field's ScenarioCounter gates and (for a rotating field) a beat→cast table. The authored gate is the exact
byte shape `fork-report` reads back, so a forked-then-reauthored roster round-trips through the analyzer.

> This is the **authoring** side of fork-fidelity gap #13 (story-event director / rotating cast). Carrying a
> real field's rotating cast faithfully is `--verbatim` + `[startup] scenario = N`; *authoring* a new one (on
> a from-scratch or edited field) is these keys.

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
| `collision` | OPTIONAL, default `true`. `false` = a **walk-through** prop (`SetObjectFlags(7)` — show + both collision-EXEMPT bits, the pattern 3345 shipping objects use for held items/effects/render-only set dressing): the player passes straight over/through it. For floor markers (a `[[coop]]` plate stone, a painted-circle stand-in) and dense scenery. Talk/dialogue still works. |
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
    py tools/deploy_battle.py my_map/battle.toml    # reversible install into your mod folder

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
| `to` | target field id — or the string **`"worldmap"`**: the walk-out region returns the player to the **world map** via the base game's own shared exit cascade (carried verbatim at build time; the story-correct `wldMapNo` is selected by ScenarioCounter band × region key, and the overworld position persists like leaving any real town). |
| `region_key` | *(worldmap only, default `62`)* the `D8:2` region key. `62` = the game's generic-return arm: every story band runs `D8:2=0; WorldMap(9009)` — the all-vehicle free-roam superset, arriving **exactly where the player stood** (the persisted-position arrival). Other cased keys are the real-town pattern (the key stays set and the destination world teleports you to its hardcoded door). `0`/un-cased keys DO NOT WARP (the cascade's switch default is a bare return) — the build refuses them. |
| `arrive` | *(worldmap only, optional)* `[x, z]` world coordinates — pin the world **arrival point deterministically**, returning to the **same world state the player entered from** (the entrance trigger records it; the exit presets the engine's position vars and warps back computed). Place it **≥ ~8u clear of the entrance's trigger tiles, facing away** — an arrival adjacent to a tread trigger makes accidental instant re-entry likely (in-game proven). Without `arrive`, the exit runs the generic cascade and lands at the routed world's default point. `arrive_face` (0–255, default 0=south) sets the facing. |
| `entrance` | which entrance to arrive at in the target (default `0`; not applicable to `"worldmap"`). |
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

## `[[jump]]` (optional, repeatable)

A navigable **ledge / gap hop** — FF9's Ice-Cavern-style jump (the ladder mechanism minus the climb
loop). A trigger zone fires the player's jump arc: either a **verbatim real arc** grafted from a real
field by `ff9mapkit import`, or a **from-scratch generated arc** built from just the landing point
(the census-modal Ice Cavern hop template — byte-identical to the real arcs for the same inputs).

```toml
[[jump]]
zone = [[9016,-16722],[9574,-17758],[9791,-17674]]   # 3-5-point take-off trigger
jump = "MYFIELD.jump0.bin"                            # FAITHFUL: the real jump-arc sidecar (from `ff9mapkit import`)
# trigger = "action"                                  # "action" (press, default) or "tread" (auto on walk-in)

[[jump]]                                              # FROM SCRATCH: generated from the landing point
zone = [[-100,100],[100,100],[100,-100],[-100,-100]]
to = [-301, -4548, 251]                               # landing point [x, z] or [x, z, y] (y = the landing floor's height)
# via = [[142, -2137, 863]]                           # optional mid-ledge landing(s) for a multi-hop crossing
# steps = 11                                          # frames per hop (or a per-hop list); tune to the gap like the real game (5-16)
```

| key | meaning |
|---|---|
| `zone` | the **take-off trigger** — `3`–`5` `(x,z)` corners (4 are auto-made IsInQuad-safe). |
| `jump` | a `"<name>.jumpN.bin"` sidecar holding the real jump arc — written by `ff9mapkit import` (the file must exist, else a build error). Exactly one of `jump` / `to`. |
| `to` | the landing point `[x, z]` or `[x, z, y]` (`y` = the up-positive height of the landing **floor** — the engine floor-snaps after the arc, so it must land on the walkmesh). The engine arcs from the player's *current* position, so no take-off point is needed. |
| `via` | optional list of intermediate landing points (same shape as `to`) — a multi-hop crossing, like the real two-hop Ice Cavern gaps. |
| `steps` | jump duration in **frames per hop** (default `11`, the game-wide mode); a scalar or a per-hop list. Longer gaps read better with more frames (the real game uses 5–16). |
| `trigger` | `"action"` (default) = stand on the zone and **press** to hop; `"tread"` = auto-hops the moment you walk in. |

Like a `climb` ladder, the kit splices the player's jump animation in once and runs the arc in the
player's own context via `RunScriptSync`. A jump is **one-way**; for a hop-across-and-back gap author
two `[[jump]]` blocks (a zone + landing point per direction), exactly like the real Ice Cavern pairs.

---

## `[[platform]]` (optional, repeatable)

A rideable **carry platform / lift** — FF9's Pandemonium-elevator mechanism (decoded from fields
2712/2713): a boarding trigger locks control and carries the player frame-by-frame to the destination,
then hands control back (or fades + warps to another field — an inter-floor elevator). Optionally a
**visible platform model** rides with the player in lockstep.

```toml
[[platform]]
zone = [[-200, -160], [200, -160], [200, -320], [-200, -320]]   # 3-5-point boarding trigger
land = [0, 450, 300]        # ride to this landing floor [x, z, y]  (OR rise = <units> for a vertical lift)
prop = "cask"               # OPTIONAL: a visible platform model that rides under the player
# model = "GEO_..."         #   (or an explicit model id/GEO name instead of a prop archetype)
# model_offset = 40         # world units the model's ORIGIN sits below the player's feet
# trigger = "action"        # "action" (press, default) or "tread" (auto on walk-in)
# warp_to = 4005            # end the ride in a fade + Field() warp (an inter-floor elevator)

[[platform]]
entry = true                # ON-ARRIVAL rise: plays at field load (an elevator you arrive ON)
land = [0, 0, 300]          # the let-off floor
rise = 600                  # the shaft depth below it (you rise up out of the hole)
```

| key | meaning |
|---|---|
| `zone` | the **boarding trigger** — `3`–`5` `(x,z)` corners (4 are auto-made IsInQuad-safe). Not used with `entry = true`. |
| `land` | the landing floor `[x, z]` or `[x, z, y]` — ride from wherever the player boards to here. |
| `rise` | alternative to `land`: lift the player `<units>` vertically in place (positive = up; needs a real floor at the top). With `entry = true`, the shaft depth below `land`. |
| `speed` / `duration` | ride tuning: world-units/frame (`land` mode, default 30) / total frames (`rise` mode, default 32). |
| `entry` | `true` = the **on-arrival elevator**: at field load the player drops to the hole bottom and rides up to `land`. No zone/press. |
| `trigger` | `"action"` (default) = press to board (with the "!" bubble); `"tread"` = auto-board on walk-in. |
| `warp_to` / `warp_entrance` | end the ride with a fade + `Field(warp_to)` (sets entrance `D8:2` first) — the inter-floor elevator, the way the real game changes floors. |
| `prop` / `model` | OPTIONAL **visible platform**: a prop archetype (`"cask"`, `"vat"`, …) or an explicit model id/GEO name. The model is placed walk-through (collision comes from the walkmesh) and **tracks the player's live position** during the ride — perfect lockstep, and one model serves a bidirectional zone pair (it rests wherever the last ride left it). At most **4** per field. |
| `model_offset` | world units the model's origin sits **below the player's feet** (default 0). |
| `model_pos` | the model's rest spot `[x, z(, y)]` — defaults to the zone centroid (or the hole bottom with `entry = true`). |
| `animation` | OPTIONAL ride gesture clip for the player (cosmetic). |

⚠ **Visibility is engine-governed**: a LONG visible vertical ride pushes the player's `psxDepth` out of
range on a pitched-down camera (he goes invisible mid-ride) and the scroll camera can't leave its
authored band. Keep visible rides SHORT (small y, in-band) and do big floor changes with `warp_to` —
exactly how the real game does it. For a tall faithful elevator, fork a real one `--verbatim`
(Pandemonium 2712/2713, proven).

---

## `[[savepoint]]` (optional, repeatable)

A **synthesized save point** — a **visible save Moogle** (talk to it → the save menu, FF9's actual
idiom) plus a press-to-interact zone. Both run the same faithful flow: an **option menu**, a **Yes/No
confirm**, then the `GLOB(184)`-latched `Menu(4, 0)` — the spine every real save point in FF9 uses.
(See [`docs/SAVEPOINT.md`](SAVEPOINT.md) for the byte census behind it.)

```toml
[[savepoint]]
zone = [[-400,-900],[400,-900],[400,-500],[-400,-500]]   # the press area (4 or 5 corners)
# moogle = true                                          # the visible save Moogle (default true)
# pos = [0, -700]                                        # the Moogle's spot (default: the zone centre)
# bubble = true                                          # the floating "!" prompt (default true)
# dialogue = true                                        # the menu + confirm (default true)
# prompt  = "What would you like to do?"                 # the option-menu question
# confirm = "Save your progress?"                        # the Yes/No question
# save_row = "Save"   ; cancel_row = "Cancel"            # the option-menu rows
# yes_row  = "Yes"    ; no_row     = "No"                # the confirm rows
# speaker = "Mog"                                        # attribution on the questions (name line + curly quotes)
# latch = true                                           # the GLOB(184) bracket (leave on)
# act = true                                             # the Moogle's save CHOREOGRAPHY (default true)
# act_text = "Here we go, kupo!"                         # its line while the book is open
# act_hop_to = [-347, 7514]                              # optional landing spot for the hop
# reveal_style = "instant"                                # "instant" (default) or "barrel_pop"
# reveal_height = 360                                     # how far above the cask it stands
```

| key | meaning |
|---|---|
| `zone` | `4` or `5` `(x,z)` corners of the press-to-interact area (place where the player stands). |
| `moogle` | a **visible save Moogle** at `pos` whose TALK opens the save menu — default `true` (an invisible zone reads as "no save point here"). `false` = the zone only. |
| `pos` | `[x, z]` for the Moogle (default: the zone's centre; keep it on the walkmesh). |
| `bubble` | the floating **"!"** prompt on the zone — default `true`. |
| `dialogue` | the option menu + Yes/No confirm — default `true`. `false` opens the save menu immediately on touch (no real save point does this; kept as an escape hatch). |
| `prompt` / `confirm` | the two questions. Defaults are neutral wording, not FF9's own strings (the kit ships no Square-Enix text). |
| `save_row` / `cancel_row` / `yes_row` / `no_row` | the menu rows. **Cancel is row 1 in both menus** and must stay bodiless — see `SAVEPOINT.md`. |
| `speaker` | optional attribution on the menu questions — rendered FF9's way (name line + curly-quoted line; see *Speaker names & the tail*). The act line deliberately ignores it (stock's is unattributed). |
| `latch` | the `gEventGlobal[184]` bracket around the save — default `true`; every real save point sets it. |
| `tent` | `true` adds the **Tent** row: the confirm with a live remaining count, or "you don't have any tents"; resting restores **half of maximum HP and MP** (rounded up) to every living party member — a KO'd member is not revived — and consumes one Tent. Wording: `tent_row` / `tent_prompt` / `tent_yes` / `tent_no` / `no_tent`. |
| `shop` | a `[[shop]]` id — adds the **Mogshop** row, opening that shop's inventory (`Menu(2, id)`). The `[[shop]]` must exist in the same field. Label: `shop_row`. |
| `party` | `true` adds the **Switch party members** row (`Party` + `UpdatePartyUID`). `party_locked` = bitmask of character slots the player may not remove (default 1 = slot 0). Label: `party_row`. |
| `party_min` | how many characters the player must select (0–4). **Leave it unset** — the default emits a runtime clamp to the party's live size, which is the only softlock-safe form: the party screen's sole exit is `selected >= party_min`, so a fixed `4` with fewer than four characters available traps the player (stock never hits this — its party row only appears late-game with a full roster). With a full party the clamp equals stock's own `Party(4, 1)`. |
| `act` | the Moogle's **save choreography** — default `true`. On the confirmed Yes it hops (clip 6503 + the real SFX), the **book + feather** props appear and open, the Moogle opens its book (4645) while `act_text` shows, the save menu runs, then everything reverses (the census-invariant template of all 57 real save moogles — `SAVEPOINT.md`). Needs `moogle` and `dialogue`. `false` = the still moogle. |
| `act_text` | the line during the act — shipped stock-shaped: `[IMME]` + your text + `[TIME=20]` (immediate, auto-dismiss), NO speaker and NO quotes, mirroring the real field-300 entry byte-for-byte. |
| `menu_pos` | where the Moogle's windows sit (`[MPOS=x,y]` = the window's **top-left** corner, y measured down from the top). Defaults to `"stock"` — FF9's own pair, the option list at `(20, 16)` and every sub-window at `(30, 26)` — because that top-left pin is what real moogles use *and* what leaves headroom for the **MOGNET caption** above the frame (an auto-placed menu clips it). Give `[x, y]` to pin them all somewhere else, or `false` for the engine's auto-placement. A pinned window draws **no tail** (the engine never places one on the absolute path), so those entries ship tail-less, exactly like stock's. |
| `act_hop_to` | `[x, z]` (or `[x, z, y]`) — a landing spot: the Moogle traverses there and back with the donor's 15-frame lerp (for a moogle perched off its save spot). Default: hop in place at `pos`. |
| `reveal_style` | how the Moogle first appears — `"instant"` (default; visible from spawn, byte-identical to every build before this key existed) or `"barrel_pop"` (spawns hidden inside a cask, pops out on a press — `SAVEPOINT.md`'s "The cask reveal"). Any `reveal_*` key below is a **lint error** unless this is `"barrel_pop"`. |
| `reveal_height` | how far **above** the container the moogle stands once it pops (positive int, default `360` — field 407's own lift). The hop is **vertical**, so this replaces any landing coordinate: the destination is the container's own `x`/`z` raised by this. |
| `reveal_from` | `[x, z]` — where the cask prop sits. Default: the Moogle's `pos`. |
| `reveal_steps` | `SetupJump` duration in frames. Default **10** (the donor MODAL value — fields 407 and 853 both use it; field 253 uses 15, field 351 uses 6 — per-scene tuning, not a universal default). |
| `reveal_sfx` | a `RunSoundCode3` sound id to play just before the jump, or `false`/omitted (the default — **2 of the 4** census donors emit no sound at all; a universal default would invent a law the bytes don't support). |
| `reveal_container` | `true` (default) ships a cask prop (`GEO_ACC_F0_CSK`) the player presses to trigger the reveal. `false` ships no cask — wire your own trigger scenery to `content.savepoint.cask_trigger_body()` (`SAVEPOINT.md`). |

The menu shows only the rows you configure, in FF9's own order — **Save · Tent · Mognet · Mogshop ·
Switch party members · Cancel** — so a bare `[[savepoint]]` is still Save/Cancel and a fully-dressed one
matches a real save moogle (minus stock's `Debug` row, which is never emitted).

### `[savepoint.mognet]` — join FF9's real Mognet network as a NEW moogle

Give the save Moogle a **42nd network identity**: a real roster name, and a menu that grows the
**Mognet** row (Save / Mognet / Cancel). Picking Mognet runs the letter act — the moogle **accepts** a
held letter addressed to it, **offers** its own letter for delivery to a real moogle (a stock save
moogle completes the delivery, no engine change), or reports **nothing** — against the game's real
mailbox in `gEventGlobal`. (Byte protocol + safety invariants: [`docs/SAVEPOINT.md`](SAVEPOINT.md).)

```toml
[field]
text_block = 30110               # REQUIRED: a minted block (the roster ships as text entry 0)
register_text_block = true

[[savepoint]]
zone = [[-100,-100],[100,-100],[100,100],[-100,100]]
[savepoint.mognet]
name = "Mogwai"                  # the new identity -- appended as roster row 41
accept = [{ variant = 55, letter = "So good to hear from you, kupo!",
            from = "Kumop", title = "A Warm Hello" }]   # deliverable TO this moogle; from+title -> re-readable
give = { variant = 56, to = "Kupo" }   # its own letter: variant 49..63, to = a roster name or id
received = [{ variant = 57, from = "Kuppo", title = "News From The Mines",
              letter = "The mines are quiet again, kupo.", requires_flag = 8720 }]  # story auto-arrival
```

| key | meaning |
|---|---|
| `name` | **required** — the moogle's roster name (identity id 41). One network moogle per field. |
| `accept` | letters this moogle takes delivery of: bare variant ids (`49..63`) or `{ variant, letter = "..." }` tables. A `letter` body is shown on the REAL full-screen letter (the stock header — moogle portrait + "From <sender> to <recipient>" — is added for you; line breaks are yours). Add **`from` + `title`** (both) and the delivered letter also joins the **Read mail** list, re-readable forever. |
| `received` | **auto-arriving** letters — the moogle's own pen-pal mail, no player delivery involved. Each entry needs `variant` (`49..63`), `from` (a roster name/id), `title` (its Read-mail row), `letter` (the body); optional `requires_flag` / `requires_scenario` gate the arrival (neither = arrives on the first Mognet open), and optional `announce` gives the letter its **own** arrival line (stock announces each letter with bespoke text; omitted = the shared `arrive_line`). Arrival announces, shows the letter once, and latches — after that it lives in Read mail. Up to **10** Read-mail rows total (titled accepts + received — stock's payload budget). |
| `give` | `{ variant, to }` — the one letter it hands out (one-shot; a declined offer re-offers). `to` = a real roster name (`"Kupo"`) or id. Building resolves names against **your install's** roster. |
| `mognet_row` / `accept_prompt` / `accept_yes` / `accept_no` / `thanks` / `give_prompt` (`{to}` = the recipient) / `give_yes` / `give_no` / `give_line` / `nothing` / `erase` | wording overrides; all have neutral defaults. `thanks` may use `[TEXT=0,0]` — the sender's roster name. `status_none` overrides the no-mail line of the persistent mail-STATUS box (the bottom-left "You have a letter from X to Y" every real moogle shows while Mognet is open; the list lines are structural). |
| `menu_prompt` / `accept_row` (`{name}` = this moogle) / `read_row` / `cancel_row` / `read_prompt` / `arrive_line` | wording for the 3-row Mognet submenu (**Give \<name\> a letter / Read mail / Cancel** — shown only when a delivery is pending or a letter is known, rows masked like stock), the "which letter" list, and the arrival announcement. |

Requires the FF9 install at **build** time (the 41 real names are extracted from your own game files —
the kit ships none). On stock fields the new name renders blank (their 41-row tables); everything else
— including a real moogle accepting our letter — works on stock Memoria.

---

## `[[chest]]` (optional, repeatable)

A real **openable treasure chest** — a model the player walks up to and **presses** to open: it plays the
lid animation + SFX, gives a fixed **item or gil**, shows FF9's centered *"Received …!"* box, and **latches a
save-persistent flag** so the chest stays open across saves and reloads. Byte-grounded on FF9's real chests
(fields 200/407, model 75 `GEO_ACC_F0_TBX`); it works on a from-scratch field **and** a `--verbatim` fork.

```toml
[[chest]]                 # an item chest
pos = [0, 80]             # where the chest model sits (on the walkmesh; usually placed in Blender)
item = ["Potion", 1]      # [item id-or-name, count]
flag = "chest_potion"     # REQUIRED: the opened-flag (a [[flag]] name, recommended)

[[chest]]                 # a gil chest
pos = [120, 80]
gil = 250
flag = 8721               # ...or a raw safe-band index (>= 8712)

[[flag]]                  # define the named opened-flag
name  = "chest_potion"
index = 8720
```

| key | meaning |
|---|---|
| `pos` | `[x, z]` — where the chest model sits on the floor. It has **solid collision** (the player can't walk through it); place it where the player can reach to press it. |
| `model` | OPTIONAL chest **variant** — `"F0"` (default), `"F1"`, `"F2"`, `"F3"` (or a raw id `75`/`91`/`701`/`702`). Each carries its own lid animation + open/closed poses (decoded from the real game). FF9 ships these as per-zone duplicate IDs, so there are really only **two distinct looks**: extracting the models confirms **F1 ≡ F3** (byte-identical mesh + textures) and **F0 ≡ F2** (same mesh; F2 only differs by an *unused magenta dummy* texture, so it renders the same as F0). Use `F0` and `F1` for the two real looks; `F2`/`F3` exist for fidelity to the game's IDs. |
| `item` | `[item, count]` — the reward; `item` is an **id or a name** (`"Potion"`, also gear). Set **`item` OR `gil`**, not both. |
| `gil` | gil reward instead of an item. |
| `flag` | **REQUIRED** — the save-persistent **opened-flag** bit (the chest re-poses OPEN once looted, forever). A **`[[flag]]` name** (recommended) or a **safe-band index `≥ 8712`**. It's *not* auto-allocated: a positional auto bit would shift if you reorder chests, and FF9's Mognet lock band (`8376–8511`, the letter one-shot locks) may already be set in a player's save — a defined safe-band flag is resilient to both. A named `[[flag]]` is also campaign-unique by name. |
| `requires_flag` / `requires_flag_clear` | OPTIONAL story gate (a `[[flag]]` name or index) — the chest only **appears** while that flag is SET / CLEAR (a quest-reward chest that materializes after a beat). Distinct from `flag` (the opened bit). Same gating as `[[npc]]`/`[[event]]`. |
| `face` | OPTIONAL facing `0–255` (`0`=south, `64`=west, `128`=north, `192`=east) — rotate the chest model. |
| `message` | OPTIONAL — replace *"Received \<item\>!"* with your own text (you own the `[WDTH]`/window codes). |
| `box` | OPTIONAL `[width, lines]` — centers a custom `message` (the `[STRT]` geometry FF9 auto-centers from; the built-in item/gil boxes already carry the real field's). |
| `tail` | OPTIONAL window-pointer corner (default `DEFT`, the centered system box). |

> **`[[chest]]` vs the `[[event]]` chest-behavior.** `[[event]]` with `received = true` + `require_space = true`
> is a *barebones* reward **zone** — no model, no animation, you just walk over an invisible trigger.
> `[[chest]]` is the **real contraption**: a visible, solid, openable chest model with the lid animation + SFX
> and a savable open state. Use `[[chest]]` for an actual treasure chest, the `[[event]]` form for an invisible pickup.

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
| `speaker` / `tail` | optional — same as `[[npc]]` (the faithful name-line + quotes form + the window pointer); see *Speaker names & the tail*. Usually omit `speaker` for an unsigned popup. |
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
> flags, and one-time triggers. An invisible **reward zone** is `give_item` + `received = true` +
> `require_space = true` + `once = true` — which compiles to FF9's exact chest shape
> `if (GetItemCount < 99) { if (!opened) { opened = 1; AddItem; SetTextVariable; window-7 "Received …!" } }`
> (effects before the acknowledgement; dedup flag first; verified byte-for-byte against real fields). For a
> real openable chest **model** (lid animation, solid collision, the centered box), use [`[[chest]]`](#chest-optional-repeatable) instead.

### Story flags & branching

A **story flag** is a single bit in FF9's **save-backed** event memory (the engine's *Global*
variable scope — `gEventGlobal`) that an event SETs (`set_flag = [N, 1]`) and other content reads
(`requires_flag = N`). Being save-backed, it **persists across field reloads and saves** — so a
looted chest stays looted, a one-time scene stays played. (The kit uses the persistent *Global* bool,
not the transient per-field *Map* bool.) That's how the world gains state: hit a switch (event
`set_flag`) → a guard appears (`[[npc]] requires_flag`) and a door unlocks (`[[gateway]]
requires_flag`). The kit's auto `once` flags occupy a high band (from **8000**). **Pick your explicit
flag indices in the provably-safe band [8712, 16320)** — real FF9 uses the Mognet lock band (bits **8376–8511**) and the
read-mail payload bytes (bits **8512–8711**, whole-byte-written by ordinary play at any moogle), so an index there silently corrupts the
player's save. The lint enforces this. For unbounded mod state beyond simple flags, Memoria also
provides save-backed vector/dictionary stores (a future kit feature).

**Name your flags (optional `[[flag]]` table).** Instead of tracking raw indices, declare a name once
and gate by it — readable, and the kit checks both sides resolve to the same bit:

```toml
[[flag]]
name  = "lever_pulled"
index = 8720            # must be in [8712, 16320), clear of real-FF9 usage

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
words = [
  { byte = 236, value = 4 },         # a save-backed 16-bit WORD write (e.g. the ATE-availability mask) — arms ATE menus
]
```

- **`scenario`** — an int (`0`–`32767`; every real beat is ≤ 12000) or an area name resolved against the
  registry (`ff9mapkit flags` lists them). Writes the save-backed ScenarioCounter (`gEventGlobal` byte 0).
- **`flags`** — a list of `{ flag = <index|name>, value = 0|1 }`. Unlike authored `set_flag` (which must use
  the safe `[8712, 16320)` band), a `[startup]` preset is **meant** to assert REAL FF9 story bits (below
  8712) — that's the point — so the safe-band rule does **not** apply. The lint still flags a preset into a
  genuinely *reserved* region (the Mognet lock band + payload, the byte-23 menu handshake, worldmap-unlock bits, the
  choice scratch), which would corrupt engine/save state rather than assert a beat.
- **`words`** — a list of `{ byte = N, value = V }` save-backed **16-bit WORD** writes into `gEventGlobal`
  (`byte` = `0`–`2046`, `value` = `0`–`65535`). Use it to seed a multi-bit avail-WORD — e.g. the ATE-availability
  mask at byte 236 (each bit arms one Press-SELECT ATE menu row). `byte 0` is the ScenarioCounter — use `scenario`
  for that instead.

The presets **re-assert on every field entry** (idempotent — right for a fork that stands for one beat). For
a multi-field chain, put `[startup]` on the **entry** field only. v1 is author-side (you assert the beat —
you have the game knowledge); per-door spawn is its own vocabulary, `[[player.arrival]]`. To **fire** a beat on
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
items = [["Potion", 5], ["Tent", 1]]        # SCRIPTED, once-gated give (the per-journey starting bag)
gil = 1000                                  # gil to add (negative subtracts)
once = true                                 # default: fire once ever (a save-persistent once-flag). false → every entry
# flag = 8300                               # explicit once-flag index (REQUIRED in a campaign member; auto 8300+ otherwise)
```

- It's a **list** — author several entry beats, each independently gated.
- Each hook needs at least one of **`message`** / **`set_scenario`** / **`set_flags`** / **`items`** / **`gil`**.
- **`items`** = `[[id|name, count], …]` and **`gil`** (negative subtracts) are a **scripted, once-gated** give (`AddItem`/`AddGil`) — the **per-journey starting bag**, distinct from the mod-global `[start_inventory]` CSV: it's `.eb` logic that fires on this entry only when the gates match, so it's per-fork-clean.
- The gates (`requires_scenario` / `requires_flag`) sit *outside* the once-check, so a hook whose condition
  isn't met yet returns without spending its once-flag — it can still fire on a **later** entry once the beat
  is reached.
- `set_scenario` / `set_flags` follow the same band rules as `[startup]` (assert REAL story bits below the safe band;
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
  a brand-new *custom* playable character is the `[[playable]]` block (DLL-free; worked example:
  `examples/thirteenth-character/`).
- ★ **Caveat:** if the field's own Main_Init runs `SetPartyReserve` (rebuilds the roster) **after** the kit's
  prepend, it can wipe the add — the build **warns** on a verbatim fork where this is the case. A synthesized
  field never resets the party. Pair with `[startup]`/`[[gateway]]` to also set the story beat.

---

### `[[playable]]` — a brand-new custom playable character

Mint a **genuinely new engine `CharacterId`** — a 13th (14th, …) party member alongside all 12 canon
characters, with its own name, stats, battle model, and ability kit. **Zero DLL** (CSV deltas + `.eb`
recruit op), *except* a custom battle **formula** (`script`, see below) which uses the Scripts-DLL channel.
Full worked example: [`examples/thirteenth-character/`](../examples/thirteenth-character/iviv.field.toml)
(Iviv + Steiniv); the engine mechanism is in the memory `project-ff9-13th-character`.

> **Relaunch + New Game.** The new `BaseStats`/`CharacterParameters` rows and the name directive load at
> **startup / New-Game init** — ~ Reload won't pick them up. So: deploy → **relaunch** → **New Game** (so
> the engine inits the party with the new id present) → reach the field (Main_Init recruits it).

```toml
[[playable]]
name   = "Iviv"          # the menu/battle name (no ';' or '#')
borrow = "vivi"          # REQUIRED: clone stats + rig from a base character (name, or a 0–11 id)
recruit = true           # B_PARTYADD(id) prepended to Main_Init -> joins the party at field load
id     = 12              # the CharacterId; OPTIONAL, defaults to 12 (the first custom slot). >= 12.
stats  = { magic = 40 }  # override cloned stats (below)
portrait = "art/iviv_portrait.png"   # OPTIONAL custom menu avatar (132×190 PNG)
```

**Core keys**

| key | meaning |
|---|---|
| `name` | REQUIRED — the menu/battle name. No `;` or `#` (they'd corrupt the CSV row). |
| `borrow` | REQUIRED — a base character (`"zidane"`…`"amarant"`, or a `0`–`11` id) to clone BaseStats + CharacterParameters (command-set / equip-set / stats / rig) from. |
| `id` | the new `CharacterId`. Optional; default `12` (the first custom slot). A second custom character takes `13`, etc. — the kit auto-allocates distinct CSV/preset/command/ability bands so they don't collide. |
| `recruit` | `true` → the character JOINS the party at field load (real `B_PARTYADD`, prepended to Main_Init). Arrives with its normal starting gear. Omit to define it without adding it yet. |
| `names` | per-language name overrides: `names = { jp = "…", fr = "…" }` (the base `name` is used for any language not listed). |
| `stats` | override cloned stats — any of `strength`, `magic`, `dexterity`, `will`, `gems`. (Magic drives BOTH spell damage AND the MP pool — to weaken one spell, use its `power`, not this.) |
| `params` | CharacterParameters overrides — `equip_set`/`equipment_set` (a name or id), `row`, `category`, `win_pose`, `name_keyword` (auto-unique). `menu_type`/`preset`/`serial_formula` are owned by `[playable.abilities]` / the battle-model keys — don't set them by hand. |
| `portrait` | a custom menu avatar (a 132×190 PNG) → a loose Face-Atlas sprite override. Implies a new battle serial (below). |

**Custom battle model + animset** (optional — the look; a separate pillar, see [CUSTOM_MODELS.md](CUSTOM_MODELS.md))

| key | meaning |
|---|---|
| `custom_battle_model` | `true` → mint an INDEPENDENT, editable copy of the borrow's battle model bound to this character (its own serial + BattleParameters row), so reshaping it in Blender never touches the donor. |
| `battle_model_id` / `battle_model_from` | (with `custom_battle_model`) the minted model id / a `GEO` name to build it from. |
| `custom_battle_anims` | `true` (needs `custom_battle_model`) → also give the minted model its own editable animset (faithful clip copies + registrations), so editing its poses never touches the donor. |
| `anim_edits` | a path to a Blender-edited `.glb` (from `playable-anims … --export`) the build ships onto the animset, so edits PERSIST across re-deploys. Needs `custom_battle_anims`. |
| `battle_serial` / `battle_borrow_serial` | the minted BattleParameters serial / a donor serial `0`–`18` to clone. Auto-assigned when `custom_battle_model`/`portrait` is set — only override if you know why. |

**`[playable.abilities]`** — the character's own battle command menu + learn list (optional; zero-DLL, its
own `CharacterPresetId` in band 20–23). Deep mechanism: [BATTLE_DESIGN.md](BATTLE_DESIGN.md).

| key | meaning |
|---|---|
| `preset` | `"custom"` (default → auto-allocate a preset id 20–23) or an explicit custom-band id. |
| `menu_from` | a base preset `0`–`15` (a canon character) to clone the command menu + seed the learn file from. Defaults to the `borrow` for a MAIN character (0–7); **required** when `borrow` is a guest (8–11). |
| `command1` / `command2` | the two command slots. Either a stock `BattleCommandId` name (`"Black Magic"`) **or** an inline `[playable.abilities.command1]` table to MINT a unique command (below). |
| `command1_trance` / `command2_trance` | the trance-mode slots (default: mirror the regular slots). A stock command only — can't mint here (put the mint on `command1`/`command2`; it applies in trance too). |
| `learn` | a list of `{ ability, ap }` — the learnable abilities (`ap = 0` = usable now). A minted command's pool auto-seeds this at `ap = 0`, and your explicit entries win on AP. |

**Minting a unique command** — an inline `[playable.abilities.command1]` table:

| key | meaning |
|---|---|
| `name` | the command's display label (a `com_name.mes` overlay renames just this command). |
| `abilities` | the ability POOL — a list mixing stock spells (a bare name, e.g. `"Blizzard"`) and **custom abilities** (inline `{ name, from, … }` tables, below). Shown under the command = its pool ∩ the learn list. |

**Minting a custom ability** — an inline `{ … }` in a command's `abilities` pool (its own new AA id, cloned
from a stock donor and retuned):

| key | meaning |
|---|---|
| `name` | the ability's display name. |
| `from` | REQUIRED — a stock ability to clone its ANIMATION + damage formula (e.g. `from = "Fire"`). (FF9 doesn't recolor by element, so the on-screen VFX is the donor's — clone from the matching element for a matching look.) |
| `power` / `element` / `mp` / `rate` / … | `Actions.csv` overrides that retune the clone (e.g. `power = 55`, `element = ["Thunder"]`, `mp = 18`, `rate = 50` for a status hit-rate). |
| `status` | a list of statuses the ability inflicts — stock names (`["Silence"]`, auto-mints a StatusSets row) and/or **custom-status** tables (below). Lands only if the donor formula applies statuses AND `rate` is non-zero. |
| `effect` | a power-user `AbilityFeatures` `[code=TAG] … [/code]` NCalc body keyed on this ability (`Power`/`Element`/`MPCost`/`HitRate`/`Status`/…). E.g. `effect = "[code=MPCost] 0 [/code]"` makes it free. |
| `script` | a NEW battle FORMULA no data edit can express — `script = { template = "drain_hp" }` (or `{ body = "<C#>" }`), minted into a mod `Memoria.Scripts.<Mod>.dll`. Needs a C# compiler + a **relaunch**. A paired field-menu effect: `script.field = { template = … }`. Full detail: [SCRIPTS_DLL.md](SCRIPTS_DLL.md). |

**Minting a custom status** — an inline `{ … }` in an ability's `status = [ … ]` list (a minted
`[StatusScript]` behaviour; [SCRIPTS_DLL.md](SCRIPTS_DLL.md) §12):

| key | meaning |
|---|---|
| `name` | the status name. |
| `template` | a built-in behaviour (`auto_life`, `auto_attack`) — OR set `body = "<C#>"` + `hooks = [ … ]` (the lifecycle interfaces it implements) for a hand-written one. |
| `icon` | a vanilla status name to borrow its HUD panel icon from (`"AutoLife"`, `"Regen"`, `"Berserk"`). Defaults to the template's icon. |
| `over_model` | a vanilla status name to borrow its ON-MODEL visual (chevron / particle / tint), e.g. `"Haste"`. Defaults to the `icon` donor. |
| `power` | a template knob — for `auto_life`, the revive % of max HP (1–100). |

Compact example (a mixed-school caster with a unique "Spark" command holding a stock spell + a custom one):

```toml
[[playable]]
name = "Iviv"
borrow = "vivi"
recruit = true

[playable.abilities]
preset    = "custom"
menu_from = "vivi"
command2  = "White Magic"          # a stock command in slot 2
learn = [ { ability = "Protect", ap = 0 } ]

[playable.abilities.command1]      # slot 1: a NEW minted command
name = "Spark"
abilities = [
  "Blizzard",                      # a stock spell in the pool
  { name = "Voltflare", from = "Fire", power = 1, element = ["Thunder"],
    mp = 18, status = ["Silence"], rate = 50 },   # a custom spell (own AA id)
]
```

---

### `[start_inventory]` / `[[equipment]]` — new-game starting bag & default gear

Set what the player **starts a New Game with** — the starting inventory and each character's default
equipment. Unlike `[startup]`/`[party]` (which are `.eb` field-load ops), these are emitted as **mod-global
CSV deltas** at build time (`StreamingAssets/Data/Items/InitialItems.csv` + `…/Data/Characters/DefaultEquipment.csv`),
engine-independent (stock Memoria). They're read **once at new-game init**, so they affect a true **New Game**
only (not a debug-warp / campaign mid-game entry) and compose with story_flags' seamless New-Game entry + `[startup]`/`[party]`.

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
  engine **merges** `ShopItems.csv` by id across stacked mod folders, two **mod folders** that both pick the same
  custom id collide silently (the higher-priority folder wins) — give each mod its own shop-id sub-band,
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
- **★ RELAUNCH to apply:** `Synthesis.csv` loads once at startup (`ff9mix`) — ~ → Reload won't pick it up.
- **Needs a reachable FF9 install at build time** (it reads the base `Synthesis.csv` header + recipe ids; the repo
  commits no game data).

---

### `[[synthesis_edit]]` — retune or remove a VANILLA synthesis recipe

The engine merges `Synthesis.csv` by id **whole-row**, so a base recipe (ids 0-63 vanilla) can be **overridden**:
the kit re-emits the base row with only the cells you change. `[[synthesis]]` *adds* recipes; `[[synthesis_edit]]`
*changes* the 64 the game ships.

```toml
[[synthesis_edit]]
recipe = "Butterfly Sword"        # the base recipe: its RESULT item's name, or the recipe's integer Id (0-63)
price = 500                       # any of these four, each optional (at least one):
ingredients = ["Dagger", "Dagger"]   # FULL replacement — duplicates matter (need 2 Daggers)
result = "Mythril Sword"          # change what it produces
shops = [37, 38]                  # FULL replacement of which synthesists list it (32..255)

[[synthesis_edit]]
recipe = "Pumice"                 # too strong for your campaign?
remove = true                     # unlist it from EVERY synthesist (exclusive with the other keys)
```

- **Selector:** a **string** = the recipe's *result item* name (unambiguous in vanilla — each of the 64 recipes
  produces a distinct item); an **integer** = the recipe's own `Id` column. Lint checks the selector against your
  install's base file when reachable (unknown / ambiguous selectors are flagged).
- **`remove` mechanism:** the override row ships an **empty `Shops` cell** — `CsvParser.Int32Array("")` parses to
  an empty list and `ShopUI.InitializeMixList` only shows rows whose `Shops` contains the open shop's id, so no
  synthesist offers it (the row itself stays defined — harmless to every other engine reader).
- **`shops` values** must be synth ids (`32..255`): `0-31` are base buy shops and never open as Synthesis, and a
  value that is also a `[[shop]]` id would open as a *buy* shop there (both linted). You may point a vanilla
  recipe at your own custom synthesist — e.g. `shops = [40]` moves Save the Queen to *your* shop only.
- **Edits coalesce:** the same recipe edited in several blocks/fields merges (later blocks win per key — warned).
- Same footing as `[[synthesis]]`: mod-global CSV, **RELAUNCH to apply**, needs a reachable install at build time.

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
teaches = ["Soul Blade", "Auto-Reflect"] # REWRITE the abilities it teaches (names, or AA:X / SA:X tokens)

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

[[item_effect]]
name = "Potion"             # any item with a use-effect (a consumable -- or a Tent / gem that has one)
power = 300                 # the heal/damage magnitude (0-9999)
rate = 100                  # status chance (0-100), where the effect rolls one
element = []                # the effect's element (name list or a 0-255 bitmask)
status = ["Poison"]         # the BattleStatus mask it concerns -- INFLICT or CURE follows the item's behaviour
for_dead = false            # usable on a KO'd target (Phoenix-Down style)
```

- **How it works:** each block emits a **partial CSV delta** into the mod (`Data/Items/{Weapons,Armors,Items,Stats,ItemEffects}.csv`).
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
- **Item `teaches`:** a list of abilities the gear teaches. Each entry is an ability **name** (`"Soul Blade"`,
  `"Auto-Reflect"`) or an explicit **`AA:`** (active) / **`SA:`** (support) token — e.g. `["AA:104", "SA:0"]`. It
  **REWRITES** the item's `AbilityIds` cell (a replace, not an add); `teaches = []` clears it. Names resolve against
  your install's ability pools (run `ff9mapkit items --abilities` to list them); an unknown name or malformed token
  is a lint error. (The AP *cost* to master each ability lives on the character pools — the battle/character lane.)
  - **★ Per-character gate (engine):** a taught ability only takes effect for a character whose **own learnable
    pool already contains it** — the engine matches each `AbilityIds` entry against the wearer's pool. An active
    ability surfaces in that character's command list; a support ability activates only if its passive is in their
    pool. Teaching an ability *outside* the wearer's pool writes the cell faithfully but is **silently inert**
    in-game (so pick an ability the equipping character can already learn). The kit can't lint this — an item has
    no single wearer.
  - A few display names are ambiguous (currently only **"Auto-Life"**, which is both `AA:100` and `SA:4` and
    resolves to the support form); use the explicit `AA:`/`SA:` token to pick a specific one.
- **`[[item_effect]]` — a usable item's use-effect:** tune what a **consumable** does (`ItemEffects.csv`): `power`
  (heal/damage, 0-9999), `rate` (status chance, 0-100), `element`, `status` (a `BattleStatus` mask by name —
  `["Poison", "Silence"]`), `for_dead` (usable on a KO'd target). The item is located by its `EffectId`, which is
  **1:1** with a usable item (no shared `Empty` row — edited in place). The effect's **behaviour** (`ScriptId`, the
  VFX, the target type) is left untouched, so `status` sets *which* statuses the effect concerns — whether it
  **inflicts or cures** them follows that existing behaviour. Any item with a use-effect is fair game (consumables,
  Tents, effect-bearing gems); a plain weapon/armor (no `EffectId`) is a lint error.
- **Values are clamped** to their range (stats 0-255, price 0-9,999,999, rate 0-100, effect power 0-9999). An unknown
  item name, the wrong type (`[[weapon]]` on a non-weapon, `[[equip_bonus]]` on a non-equippable, `[[item_effect]]` on
  a non-usable), a bad element/category/character/ability/status name, or an out-of-range `status_index` is a **lint
  error** (`ff9mapkit lint`).
- **★ RELAUNCH to apply:** item CSVs load once at game **startup** — ~ → Reload field will NOT pick up a stat
  change. Deploy, then relaunch.
- **Item NAME / DESCRIPTION text** is its own block — see [`[[item_text]]`](#item_text) below (a text channel,
  not a CSV: e.g. a retuned Potion's `[[item_effect]] power` changes how much it heals, while `[[item_text]]`
  changes the menu text that *says* so).
- **Deferred (a later follow-up):** minting **net-new** item ids (>254, needs a DLL).

---

<a id="item_text"></a>

## `[[item_text]]` — an item's menu NAME + description text (optional, repeatable)

Rename an item or rewrite its description. This is the text companion to the `[[item_effect]]`/`[[weapon]]`/…
stat tuners: those change what an item *does*, this changes what its menu name and help/battle text *say*.

```toml
[[item_text]]
name = "Potion"                       # the item to retext (a name or id; the RegularItem space, 0-254)
display_name = "Mega Potion"          # optional — the menu name
description  = "Restores 15 HP."      # optional — the help + battle description (see the caveat below)
# at least one of display_name / description is required.
```

- **Channel:** a drop-in **`TextPatch.txt`** at the mod-folder root (the same per-folder patch-file mechanism as
  `DictionaryPatch.txt` / `BattlePatch.txt`), a `>DATABASE` find/replace gated by NCalc on the item id. The kit
  writes **only your strings + the resolved id** — it reads nothing from the game bundles (fully provenance-clean).
- **★ One description, not two:** the engine flags the menu-**help** desc and the in-battle desc **identically**
  (`IsHelpEntry`), so `description` sets **both** — they cannot be targeted separately through this channel.
- **Multi-line** descriptions are fine — a real newline in your string is carried as `\n` and rendered on multiple
  lines. (A *literal* backslash-`n` in your text is a **lint error**: the engine reserves `\n` for a line break and
  can't show it literally — use a real line break.)
- **Scope:** normal items only (the `RegularItem` space, ids 0-254; `NoItem`/255 is rejected). **Key items** (a
  separate `KeyItem` text database) and net-new item ids are not covered yet.
- **Mod-global + repeatable:** any field may carry `[[item_text]]` blocks; they aggregate into one `TextPatch.txt`.
  An unknown item name, or a block that sets neither field, is a **lint error** (`ff9mapkit lint`).
- **★ RELAUNCH to apply:** `TextPatch.txt` is read once at engine startup (~ → Reload field will NOT pick it up).

---

## `[[ferry]]` (optional, repeatable)

**Boat travel booked through a PERSON** — stock FF9's own idiom (the Blue Narciss captain's
"Where to?"). Talk to an NPC, pick a port, sail to the **overworld** at that port's landing.

Use this instead of one walk-on `[[gateway]]` per destination whenever the art does not *paint* a
distinct, readable door for each one. Four unmarked trigger zones in one corridor are mutually
adjacent and unreadable — a menu is self-describing and cannot be entered by accident. (Learned the
hard way: the Lantern Hall shipped four invisible east-wall berths and the playtester could not tell
what to do, only that they "randomly triggered 1 of 2 warps".)

```toml
[[npc]]
name = "Purser"
pos = [130, -1650]
model = 220
dialogue = "Talk to me and I will sail you anywhere on the ring."

[[ferry]]
npc = "Purser"                       # must name an [[npc]] (or use zone = [...] for a booth)
prompt = "Where shall we sail?"      # the line above the rows
decline = "Not yet."                 # REQUIRED -- the stay-ashore row
decline_reply = "The ferry keeps her berth."   # optional line after declining

[[ferry.destination]]
name = "Ashvale"                     # the menu row
arrive = [60.0, -1168.0]             # where you land on the overworld
arrive_face = 192                    # 0=south 64=west 128=north 192=east
reply = "The Lantern Quay it is!"    # optional line before the fade
```

| key | meaning |
|---|---|
| `npc` / `zone` | the trigger — exactly one, same semantics as [`[[choice]]`](#choice-optional-repeatable). |
| `prompt` | the "Where to?" line above the rows. **Required.** |
| `decline` | the stay-ashore row's text. **Required** — it is appended LAST because the engine's CANCEL (B) returns the last row, so without it a cancelled menu would sail you to the final destination. |
| `decline_reply` | optional line shown after declining. |
| `instant` | default `true` — the menu pops fully drawn instead of typing on (a travel menu wants to snap). |
| `destination[].name` | the menu row. |
| `destination[].arrive` | `[x, z]` — the overworld landing. Keep it **≥ 8 u** from the quay's own entrance tile or stepping out re-fires the entrance you just used (THE ARRIVAL-CLEARANCE LAW). |
| `destination[].arrive_face` | raw facing byte 0–255 at the landing. |
| `destination[].reply` | optional line before the fade. |

> **How it compiles.** A `[[ferry]]` desugars into an ordinary `[[choice]]` whose destination rows
> carry a worldmap-exit action, so it inherits the whole choice pipeline — the one-text-entry
> prompt+rows assembly (and with it the window-geometry law), CANCEL-picks-last, the runtime
> availability mask, flag gating. Each destination arm emits the **same body a walk-out worldmap
> gateway does** (`worldexit.worldmap_exit_body`): usercontrol guard → fade → *both* position blocks →
> `POSITION_PRESET_KEY` 35 → computed `WorldMap`. So a ferry row and a door behave identically once
> taken. The decline arm emits no transition at all.
>
> The underlying capability is also available directly as `[[choice]]` `options[].worldmap =
> { arrive = [x, z], face = N }` for hand-built menus; `[[ferry]]` is the productized surface and the
> one that gets linted (≥1 destination, a decline arm, and arrive/face validated like a gateway's).

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
| `speaker` / `tail` | optional — same as `[[npc]]` (the faithful name-line + quotes form + window pointer). |
| `instant` | *(optional, bool)* `true` → FF9's `[IMME]` tag: the menu **pops fully drawn** with no character-by-character type-on (snappy menus; the World-Hub journey selector uses it). |
| `options` | a list (`[[choice.options]]`) of **≥ 2** rows the player picks from. |
| `default` | *(optional)* option index highlighted when the menu opens (0 = top row; default 0). |
| `cancel` | *(optional)* option index B/Cancel picks (`-1` or omit = last row, the FF9 default). |
| `options[].text` | the menu row shown for that option (kept short — it's one line). |
| `options[].disabled` | *(optional)* `true` = the row is always **removed** from the menu (no widget). |
| `options[].requires_flag` | *(optional)* hide this row **until** story flag N is set (flag-gated). |
| `options[].requires_flag_clear` | *(optional)* hide this row **once** story flag N is set. |
| `options[].reply` | optional line shown after the player picks it. |
| `options[].give_item` / `remove_item` / `gil` / `set_flag` | optional actions, same as `[[event]]` — `give_item`/`remove_item = ["Potion", 1]` (id or name; a trade row gives one item and takes another), `gil` negative charges, `set_flag` raises a story flag. |
| `options[].warp` | *(optional)* a **field id** (a positive int) this row **warps to** — the World-Hub journey destination the choice launches. |
| `options[].set_scenario` | *(optional)* a ScenarioCounter value (`0`–`32767`) set alongside the `warp` (seed the destination's story beat as you enter it). |

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

## `[cutscene]` / `[[cutscene]]` (optional)

An ordered, **control-locked** scripted sequence that plays on field entry — the one thing the
declarative content can't express (steps run *in order*). The player can't move while it runs.

A field can carry **several** — write repeated `[[cutscene]]` blocks (the **story-event dispatch**: each
scene gated to its own beat via `requires_scenario`, so one field plays a different scene at each stage of
the story). The dispatch rule: every block needs a **distinct gate** (two scenes that could fire on the
same load are a build error). Auto once-flags are per-block (`8100`, `8101`, …); in a campaign member only
the *first* block has a reserved flag slot — give later blocks an explicit `flag`. A single `[cutscene]`
table is exactly the one-block case, unchanged.

Two flavors, by whether the scene declares a **cast**: no `actors` = **narration** (windows/waits/flag
writes only); `actors = ["<npc>", …]` = a **cast scene** — the scene drives those NPCs (and/or
`"player"`): walk, animate, turn, speak — see *Cast scenes* below.

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

Cutscene-level keys (alongside `steps`):

| key | meaning |
|---|---|
| `once` | `true` (default) = play once ever (save-persistent flag); `false` = every entry. |
| `flag` | explicit GlobBool index for the once-guard (default `8100`). |
| `requires_scenario` | **the story-event director GATE**: the scene only plays when the **ScenarioCounter `== N`** (an int or an area name, e.g. `"Dali"`). Outside its beat the scene simply doesn't exist — and its `once` flag isn't burned, so it still plays when the story reaches the beat. |
| `requires_flag` / `requires_flag_clear` | the scene only plays while this GlobBool (index or `[[flag]]` name) is SET / CLEAR. Stacks with `requires_scenario` (both must hold). One or the other, not both. |
| `set_scenario` | **the story-event director ADVANCE**: at scene end, set the **ScenarioCounter** (int or area name) — the story moves to the next beat, exactly once, only when the scene actually played (the write sits inside the once-guard). |
| `set_flags` | `[{ flag = <index\|name>, value = 0\|1 }, …]` — story bits written at scene end (same only-when-played semantics). |
| `actors` | the **cast** — a list of `[[npc]]` names (and/or `"player"`) the scene drives. Absent = narration. See *Cast scenes* below. |
| `then_warp` | a **field id** (positive int) to `Field()`-warp to (after a fade) when the scene ends — how a forced-ATE scene returns you. Works on both flavors. |
| `ate` | `true` styles the cutscene as a compulsory **Active Time Event** (the grey banner flavor) — `ATE(mode)…ATE(0)` HUD arm + a winATE caption. |
| `ate_mode` | *(needs `ate = true`)* the ATE HUD mode `0`–`255` (default **6** = the grey **UNSKIPPABLE** banner; `1` = quiet no-icon auto-ATE). See `docs/ATE_SYSTEM.md`. |

### The story-event director (beat-gated, story-advancing scenes)

`requires_scenario` + `set_scenario` turn a cutscene into FF9's **story-event director** idiom — the loop a
real story field runs: *enter at a beat → the scene plays once → the story advances → the world re-gates.*
They compose with the other story keys into a fully declarative story arc:

```toml
[startup]                # (optional) assert the campaign's opening beat on the entry field
scenario = 2600

[cutscene]               # enter THIS field at beat 2600 -> Vivi's scene plays once -> beat becomes 2610
actors = ["vivi"]
requires_scenario = 2600
set_scenario = 2610
steps = [ { walk = "@player" }, { say = "...something's wrong." } ]

[[npc]]                  # the cast rotates at the same boundary (rotating casts, above)
name = "guard"
scenario_min = 2610      # the guard only appears AFTER the scene has advanced the story
# ...

[[gateway]]              # or advance on walking OUT instead (the write-side complement)
to = 4001
set_scenario = 2620
# ...
```

Works on both flavors (narration and cast scenes, including a cast scene on a verbatim fork). The gate
means the scene *belongs to* its beat: at any other ScenarioCounter
it doesn't fire and doesn't consume its `once` flag. The advance runs inside the once-guard, so the story
moves exactly once — and only if the scene actually played. For several scenes on ONE field, write repeated
`[[cutscene]]` blocks, one per beat (the dispatch rules above) — a field can then re-stage itself across the
whole story, exactly like FF9's own town screens:

```toml
[[cutscene]]                     # first visit, beat 2600: the mage warns you -> 2610
requires_scenario = 2600
set_scenario = 2610
actors = ["mage"]
steps = [ { walk = "@player" }, { say = "Something's wrong at the mill." } ]

[[cutscene]]                     # return visit, beat 2700 (a gateway/quest advanced it): the aftermath
requires_scenario = 2700
set_scenario = 2710
steps = [ { say = "The village is quiet now." } ]
```

### Cast scenes — `actors = ["<npc name>", …]`

Declare a **cast** to make the cutscene drive those NPCs (and/or `"player"`): walk, animate, turn,
speak. One central **conductor** (FF9's real multi-actor idiom, decoded from 9 real fields) owns the
control lock and sequences every cast member by id; movement runs in each actor's own context so it
animates. This is the iconic "a character walks in and talks" — and scales to full multi-actor scenes.

```toml
[[npc]]
name = "vivi"
preset = "vivi"
pos = [0, -300]            # where Vivi RESTS (and where he is on a replay visit)
dialogue = "..."

[cutscene]
actors = ["vivi"]         # the cast. ONE name = untagged steps below default to it
once = true
steps = [
  { teleport = [-2000, -300] },   # snap off-screen (instant) so he can walk IN
  { walk = [0, -300] },           # walk to his resting spot (= his pos)
  { face_player = true },          # turn to face the player
  { animation = "glad" },          # a gesture BY NAME (run: ff9mapkit animations vivi)
  { say = "...hi." },              # a dialogue window (untagged = narration voice)
]
```

With **several** cast members, tag each actor step (and optionally each `say`) with the actor it drives —
and `with_prev = true` runs a walk/path/animation/turn beat **in parallel** with the one before it:

```toml
[cutscene]
actors = ["vivi", "guard", "player"]
steps = [
  { actor = "vivi",  walk = "@player" },
  { actor = "guard", walk = "gate", with_prev = true },   # the guard walks WHILE Vivi walks
  { actor = "vivi",  say = "We have to go." },             # tagged say -> the window points at Vivi
  { actor = "player", animation = "shock" },
]
```

Actor steps (each needs its `actor` tag — omitted only with a cast of ONE, where it defaults):

| step (one key each) | meaning |
|---|---|
| `walk` | a **target** to walk to — a marker/entity **name** (`"fountain"`, `"@player"`, `"@Steiner"`) or raw `[x, z]`. Uses the NPC's walk animation; blocks until it arrives; turns tight (no orbit). **Auto‑routes** around walls/characters if the straight line is blocked (see *Reliability*). Optional `speed = N`. See *Movement targets* below. |
| `path` | a **list** of targets to walk through in order — `path = ["door", "fountain", "altar"]` (names or `[x,z]`). Each leg is a straight walk, stall‑checked but **not** auto‑routed — use it to force an exact route (a plain `walk` already routes itself). |
| `teleport` | a target to **instantly** move to (name or `[x, z]`). Put it **first** to start a walk-in from off-screen. |
| `animation` | a gesture **by name** (`"glad"`, `"angry"`, `"yawn"`, …) resolved against that actor's preset model, **or** a raw numeric id. Played, then held ~40 frames (no hang on a looping clip). See *Character gestures* below. |
| `turn` | angle (`0`=south, `64`=west, `128`=north, `192`=east) — an instant face (softlock-safe on player-cloned actors). |
| `face_player` | `true` — turn to face the player. |

`say` / `wait` / `set_flag` also work in a cast scene (interleaved in order): a `say` **with** an `actor`
tag is attributed to that actor (its window tail points at them); untagged it's a narration line. The
scene locks control with a **control-grant spin** (it waits out the field's entry settle, then locks —
no warmup tuning needed). An NPC ends where its last `walk`/`teleport` leaves it on the first visit; on
a replay visit it's at its `pos`, so end its last `walk` at `pos` to stay consistent.

> **Migrating from the old forms (pre-beta.16):** `actor = "vivi"` → `actors = ["vivi"]` (steps unchanged
> — they default to the sole cast member); `actor = ["a", "b"]` → `actors = ["a", "b"]`; the step key
> `anim` → `animation`; `exit_warp` → `then_warp`. The build names each rename in its error message.

#### Movement targets (`walk` / `teleport` by name)

Instead of typing coordinates, give a walk/teleport a **name** so you place the point once (in Blender
or the toml) and reference it everywhere:

- **`[[marker]]`** — a named point: `name = "fountain"`, `pos = [x, z]`. Pure authoring reference (no
  in-game object). Place these visually in Blender, or list them in the toml. A marker may also carry
  a **route**: `path = [[x,z], ...]` (+ `closed = true` for a ring) — the polyline a scripted walker
  travels. The layout probe (`tools/field_layout_probe.py`) and `ff9mapkit behavior lint` **sweep**
  route legs for walkability offline, and `[behavior]` `patrol`/`march` verbs reference them by name.
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
actors = ["vivi"]
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
| `battle_music` | BattlePatch song-play id (default `0` = normal battle theme). `import` auto-detects the donor field's real battle song (from the install's `BtlEncountBgmMetaData` `(field, scene)→song` map) and prefills this when it's non-default — a fork to a custom id loses the engine's own `(fldMapNo, scene)` lookup, so the kit reproduces it via the scene-keyed `Music:` line. |

Adding an encounter automatically adds the after-battle handler the field needs (otherwise the
player freezes on battle return).

---

## `[[battle_bgm]]` (optional, array-of-tables)

Per-scene battle music, keyed on the **battle scene id** (not the field). Each block emits a
`Battle: <scene>` / `Music: <song>` line into `BattlePatch.txt`.

| key | meaning |
|---|---|
| `scene` | the battle scene id this song applies to. |
| `song` | the akao song-play id (e.g. `35` = a boss/special battle theme). |

Why it exists: FF9 picks a field battle's song by `(fldMapNo, scene)`, so a fork to a custom id loses
the donor's *scripted* (boss) battle theme — the custom `fldMapNo` isn't in the engine's map. This
block reproduces it via the **scene-keyed** `Music:` override (`BtlBgmPatcherMapper`), which wins
regardless of the field id. `import --verbatim` auto-emits one per donor `Battle()`/`BattleEx()` scene
whose real song is non-zero (the standard Battle Theme, song `0`, is the build default and is skipped).
The lines are deduped by scene across the whole mod (the patch is scene-keyed and mod-global).

---

## `[[summon]]` (optional, repeatable)

*Experimental — the **hybrid** lane needs the custom `memoria-patches` engine bundle (the s58
`SfxHybridDrive` feature); `summon-deploy` refuses to arm it on stock Memoria. The **overlay** lane
is DLL-free.* Wear a stock FF9 summon's real cast — its live bones, its native camera, its damage
timing — with your **own** retargeted model, instead of the donor creature. Unlike every other
block on this page, `[[summon]]` emits **no `.eb` bytecode** — it compiles to asset artifacts (the
model, a private sequence host, optional baked clips) plus a printed engine-arm manifest. Full
narrative + the Blender round-trip: [`docs/SUMMONS.md`](SUMMONS.md) /
[tutorial 11](tutorials/11-summon-transplant.md).

```toml
[[summon]]
# --- identity: which cast, which model, which lane ---
donor      = 227                    # REQUIRED. numeric SpecialEffect id OR its name ("Bahamut__Full").
                                    #   The native cast whose live bones/camera/staging we inherit.
model      = "thomas_skinned.fbx"   # REQUIRED. your OWN retargeted mesh on the bone000..bone09N rig
                                    #   summon-rig-ref exported (a path; a bare name resolves under
                                    #   the field's asset dir).
lane       = "hybrid"               # "hybrid" (the s58 drive, DEFAULT) | "overlay" (DLL-free)

# --- the mint (reuses models/mint.py's band + validator; naming is this pillar's own) ---
# id         = 6201                 # mint GEO id. default = next free id >= 6000 in your mod folder.
# name       = "GEO_MON_B0_M201"    # GEO name. default = GEO_<group>_<form>_M<id-6000:03d>.
# group      = "MON"                # silhouette-family token -> ModelType (MON=3, MAIN=2, SUB=5, ...). default MON.
# form       = "B0"                 # the FORM token in the minted name (rarely need to change). default B0.
# textures   = ["thomas_d.png"]     # explicit texture PNGs to deploy beside the FBX. default: every
                                    #   *.png already sitting next to the model file.

# --- the sequence host: a PRIVATE, stock-ABSENT effect id (never the donor's own folder) ---
# private_ef = 84                   # default = auto-alloc the first stock-absent SpecialEffect id
                                    #   with no ef{id:D3}/ folder in any stacked mod folder.

# --- hybrid-lane engine knobs (map 1:1 onto [SfxHybrid] -- see SUMMONS.md) ---
# hide_native        = true         # -> HideNative (default true)
# hide_mask          = "0x3"        # -> HideMask (default "0x3" -- Bahamut's 2 meshes; raise for a
                                    #   donor with a different mesh count, e.g. "0x7" for 3 meshes)
# node_count         = 93           # -> NodeCount (default 93 -- Bahamut's bone count; set to your
                                    #   donor's own bone count if it differs)
# apply_column_scale = false        # -> ApplyColumnScale (default false -- writing it DOUBLES the
                                    #   creature; the node-position spread already carries the scale)

# --- optional data-path body hide (defense-in-depth for hybrid; the practical body hide for overlay) ---
# hide_meshes = ["0033B990", "0033B9D0"]   # mesh KEYS spliced as HideMeshes=0x.. on the host .seq's
                                    #   PlaySFX line. Default: omitted (hybrid's HideNative already
                                    #   hides the body; overlay has no fallback, so set this there).

# --- overlay-lane-only keys (ignored when lane = "hybrid") ---
# clips   = "all"                   # which decoded donor clips to bake to .anim: "all"|"none"|index list
# staging = "donor"                 # forward-compat knob; both values emit the same artifacts today
                                    #   (the overlay host .seq always nests the donor cast for
                                    #   camera+fly-by, and the .sfxmodel ships default anchor curves)
```

| key | meaning |
|---|---|
| `donor` | **required unless `sequence` is set** (an ORIGINAL summon has no donor). The stock summon whose cast you inherit — a numeric `SpecialEffect` id (`227` = Bahamut) or its enum name (`"Bahamut__Full"`); resolved through a verified name→id catalog (`content/summon.py:SUMMON_DONORS`). Must be a real donor with creature content — one of the 24 stock-absent ids (see `private_ef`) is refused. |
| `model` | **required.** Your own retargeted FBX/glTF, skinned onto the `bone000..bone09N` rig `summon-rig-ref` exported for this donor (same names + hierarchy — renaming/reparenting breaks Unity's by-path clip binding). Smooth multi-bone weights are legal for *your* mesh (only the *donor* creature is rigid one-bone-per-vertex). |
| `lane` | `"hybrid"` (default) — the s58 drive poses your model from the donor's live per-frame bones; needs the custom engine. `"overlay"` — DLL-free: your model plays the donor's motion clips, decoded once to loose `.anim` files in your mod folder, no live bone read. |
| `id` / `name` / `group` / `form` | the mint identity, in the same ≥6000 band `[[mint]]` uses. `id` defaults to the next free id; `name` defaults to `GEO_<group>_<form>_M<offset:03d>` (reproduces `GEO_MON_B0_M201` for id 6201/group MON); `group` sets the silhouette-family token that drives `ModelType` (default `MON`); `form` is the form token, rarely changed (default `B0`). |
| `textures` | explicit list of texture PNGs to deploy beside the model. Default: every `.png` file already sitting next to the model FBX. |
| `private_ef` | the stock-**absent** `SpecialEffect` id that hosts the cast's `.seq` (and, overlay-only, the `.sfxmodel`/`FileList.txt`). **Never** the donor's own `ef{donor:D3}/` folder — a `FileList.txt`/`Model` line there silently replaces the WHOLE native cast (the donor-FileList replacement law), which is fatal to the hybrid lane. Default: auto-picked from the 24-id absent set; declare it explicitly to pin a value or to share one id across several `[[summon]]` blocks. Refused if it collides with `donor`, isn't actually absent, or already has real content. |
| `hide_native` / `hide_mask` / `node_count` / `apply_column_scale` | **hybrid-only**, map 1:1 onto `[SfxHybrid]`'s `HideNative`/`HideMask`/`NodeCount`/`ApplyColumnScale` (see [SUMMONS.md](SUMMONS.md)). The `hide_mask`/`node_count` defaults (`0x3`/`93`) are Bahamut's own values — override them for a different donor. Leave `apply_column_scale` off unless your rig's bind pose is not a clean scale-1 rest — the node-position spread already carries the donor's authored scale sweep, so applying it again doubles the creature. |
| `hide_meshes` | mesh **key** strings spliced onto the host `.seq`'s `PlaySFX` line as `HideMeshes=0x..`. Optional defense-in-depth for hybrid (`HideNative` already does the real hide); for overlay there's no engine feature to lean on, so this is the practical way to hide the donor's body. |
| `clips` | **overlay-only.** Which decoded donor clips to bake to `.anim`: `"all"` (default), `"none"`, or an index list — **or a list of AUTHORED `.anim` file paths** (the two forms are told apart by content: all-numeric = donor indices). Authored clips are copied verbatim to `Animations/{id}/{key}.anim` with no `3DModelAnimation` line (the SFX path resolves clips by literal path), so they are recast-only. The key is the file stem when it is numeric, else a mint-band key the manifest is written from — the two can never disagree. |
| `staging` | **overlay-only.** How the overlay lane gets camera + fly-by motion (the baked clip alone carries no meaningful root travel — every axis of every stock clip stays under ~250 units). `"donor"` (default) nests the donor cast in the host `.seq`, inheriting its camera/staging for free, and emits sane world-origin anchor curves. A **`[summon.staging]` table** instead (its presence selects curve mode) emits AUTHORED `Start`/`End` + `Movement`/`Rotation`/`Scaling` pieces + the `Animations` playlist — see [SUMMONS.md → An original summon](SUMMONS.md). Sub-tables: `[[summon.staging.move]]` / `.turn` / `.scale` (`duration`, `from`, `to`, `ease`; an omitted `from` inherits the previous piece's destination) and `[[summon.staging.play]]` (`clip`, `speed`, `repeat`). `move` and `turn` are REQUIRED — an omitted curve is never loaded and pins that channel at its zero seed (world origin / euler `(0,0,0)` over your FBX's own orientation); `scale` is optional (its seed is identity `1`). `ease` on a creature curve is `Constant` \| `Linear` \| `Sinus` \| `SinusIn` \| `SinusOut` — `Turning1`/`Turning2` are sprite-only and REFUSED (they read a `customParam` dict the FBX path passes as `null`, crashing every render frame). `anchor` = `caster` \| `target_average` \| `world` — a bare `target` is REFUSED (a multi-target cast nulls the target and every `TargetPosition*` becomes 0). |
| `sequence` | an AUTHORED `PlayerSequence.seq`, copied verbatim into `ef{private_ef}/` instead of splicing a donor's. Makes `donor` optional; nothing stock is read. The file is linted first (`summon-seq-lint`) — the engine drops an unknown operation, and ignores an unknown argument key, with no log at all. |
| `particles` | **overlay-only.** Sprite `.sfxmodel` files copied verbatim beside the manifest, so a `CreateVisualEffect: … SFXModel=Data/SpecialEffects/ef{private_ef}/<name>` line in your sequence resolves. Every `SFXModel=` the sequence names must be in this list. |
| `manifest` | the bare `.sfxmodel` file name `FileList.txt` reveals (default `creature_manifest.sfxmodel`). Must not contain a path separator — `FileList.txt`'s grammar splits on single spaces and the name resolves relative to the ef folder itself. |

**Wiring the cast trigger is a separate, existing step.** `[[summon]]` does not touch
`Actions.csv` — point the summoning ability's `vfx1` (kit key on `Actions.csv`'s `animationId1`
column, `authoring-ff9-battles`) at this block's `private_ef` id. The build **reminds** you to do
this (a lint note), never edits the ability for you.

**`build`/`lint` only validate this block** (schema, lane, donor/`private_ef` sanity) — deploying
the model + `.seq` + DictionaryPatch line, and (hybrid lane) arming `[SfxHybrid]`, is the separate
`summon-deploy` CLI verb (`summons.deploy.deploy()`), which mutates the user's live `Memoria.ini`
on arm and needs a relaunch, and **refuses** to arm unless the deployed engine actually contains
the s58 `SfxHybridDrive` feature. See [SUMMONS.md](SUMMONS.md) for the full relaunch/recast law and
the provenance rules.

---

## `[difficulty]` (optional — enemy scaling / "hard mode")

Scales every **enemy** once per battle, at battle init. Players are never touched. Compiles into the mod's
scripts DLL (needs a C# compiler at build time — `lint` names it if missing) and loads once at title, so
**relaunch** after deploying a change. Full story: [SCRIPTS_DLL.md §12](SCRIPTS_DLL.md).

| key | meaning |
|---|---|
| `enemy_hp` | × every enemy's max **and** current HP (`0.05`–`20.0`; unset = `1.0`). Clamps at 9,999,999. |
| `enemy_attack` | × every enemy's Strength (physical). Byte stat — clamps at 255. |
| `enemy_magic` | × every enemy's Magic. Clamps at 255. |
| `flag` | optional gate: scale only while this `gEventGlobal` **bit** is set — a `[[flag]]` name or a bit index. Omit = always on. Seed it from `[startup]`/an event for a hard-mode journey; toggle live with the debug menu (~) → Flags while testing. Bit clear = vanilla. |

The block is **mod-global** (one scaling hook per deployed folder): a campaign may repeat an *identical*
block on several members, but two members with *different* settings refuse at build. At least one scale must
differ from `1.0`.

---

## `[rebalance]` (optional — a global HP-damage multiplier)

Scales the **final HP-damage number** by the caster's side. Where `[difficulty]` scales enemy *stats* (which
feed the formula), this is a flat post-formula multiplier — and the only way to scale what the **party**
deals. Same Overload/scripts-DLL plumbing as `[difficulty]`: compiles at build (needs `csc`), **relaunch**
to load. Full story: [SCRIPTS_DLL.md §12](SCRIPTS_DLL.md).

| key | meaning |
|---|---|
| `player_damage` | × HP damage dealt **by players** (`0.05`–`20.0`; unset = `1.0`). |
| `enemy_damage` | × HP damage dealt **by enemies**. |
| `flag` | optional gate on a `gEventGlobal` bit (a `[[flag]]` name or index), read fresh per battle — same as `[difficulty]`. Omit = always on. |

Only **pure HP damage** is scaled (healing / recovery / MP untouched). Two honest limits: the engine clamps
damage to **9999** right after this hook unless you set `[Battle] BreakDamageLimit = 1` in `Memoria.ini`
(the kit won't force a global engine config from a mod), and the `IsDmg9999` cheat forces player damage to
9999 regardless. Mod-global, at least one scale must differ from `1.0`. Composes with `[difficulty]`.

---

## `[deathrules]` (optional — game-over rules)

Owns the **party-wipe verdict**: when the last player goes down, decide whether the game over proceeds.
Same Overload/scripts-DLL plumbing as `[difficulty]`/`[rebalance]`: compiles at build (needs `csc`),
**relaunch** to load. Full story: [SCRIPTS_DLL.md §12](SCRIPTS_DLL.md).

| key | meaning |
|---|---|
| `second_wind` | `true` = cancel the wipe **once per battle** with a party revive. Recharges each battle; a second wipe in the same battle is a normal game over. Default `false`. |
| `chance` | percent chance the second wind fires (whole `1`–`100`; default `100`). Only legal with `second_wind = true`. |
| `animation` | `"full"` (default) = the revive is the engine's own Rebirth Flame command (the same mechanism as Eiko's vanilla auto-revive) — the **full Phoenix summon** plays and the ability decides the revive HP. `"short"` = **no choreography**: the fallen party simply stands back up (the engine's death-changer revive recipe), at `revive_hp` × max HP. Only legal with `second_wind = true`. |
| `revive_hp` | `"short"` only: revive HP as a fraction of max HP (`0 < x <= 1`, floored at 1 HP; default `0.2`). The `"full"` variant's HP is decided by the Rebirth Flame ability. |
| `keep_rebirth_flame` | default `true`: Eiko's vanilla auto-Phoenix is kept (the kit transcribes the displaced engine default). `false` **removes** it — with no `second_wind`, wipes become strictly final (hardcore). |
| `flag` | optional gate on a `gEventGlobal` bit (a `[[flag]]` name or index). Bit clear = **fully vanilla** — Eiko's auto-revive still fires even with `keep_rebirth_flame = false` (the rule is asleep, not half-applied). Toggles **live**: the next wipe obeys the new state. Omit = always on. |
| `on_defeat` | inline table `{ warp_to = <field id>, hp = 0.2, gil_loss = 0.1, flag = ... }`: instead of a game over, the fallen party revives at `hp` × max (quietly — no summon, no get-up; the battle ends instantly), optionally loses `gil_loss` × its gil once, and the field's after-battle handler warps to **the last `[field] outpost = true` field the player entered** — or to `warp_to`, the fallback for a wipe before any outpost. With `second_wind` too, the wind fires first; spent / a failed roll falls through to the warp. `flag` overrides the kit-reserved wipe-marker bit (8508). Works on **verbatim forks** too (the check prepends into the donor's existing after-battle handler). ⚠ Every field where a battle can happen — kit `[encounter]` fields *and* battle-donor verbatim forks — must carry the identical `[deathrules]` block (the build warns about gaps — an uncovered field's wipe revives + flees but can't warp). |

Mod-global like its siblings; the block must change *something* (`second_wind = true` and/or
`keep_rebirth_flame = false`). Fail-safe by construction: any runtime hiccup degrades to a vanilla defeat,
never a canceled game over with nobody revived.

---

## `[lowhp]` (optional — the LowHP threshold)

Reparameterizes when a player counts as **"HP is low"** (vanilla: at or below **1/6** of max HP): the point
where the HP number turns **yellow** and the engine's `LowHP` status applies — the status that HP-is-low
supporting abilities and AI key on. Same Overload/scripts-DLL plumbing as its siblings: compiles at build
(needs `csc`), **relaunch** to load. Full story: [SCRIPTS_DLL.md §12](SCRIPTS_DLL.md).

| key | meaning |
|---|---|
| `threshold` | the LowHP fraction of max HP — a `"N/D"` string (kept exact; denominator ≤ 100) or a number in `(0, 1)` (snapped to the nearest ≤ 1/100-granularity fraction). Required; `1/6` refuses (that's vanilla). The comparison is exact integer math, the same shape as the engine's. |
| `flag` | optional gate on a `gEventGlobal` bit (a `[[flag]]` name or index). Bit clear = the vanilla 1/6. Toggles **live** (the check runs on every HP/MP change). Omit = always on. |

Players only, like vanilla; the MP color rule (yellow at ≤ 1/6 max MP) is untouched. Mod-global; a wipe
rule this is not — a unit at 0 HP is dead before this check runs.

---

## `[music]` (optional)

| key | meaning |
|---|---|
| `song` | field BGM song-play id (e.g. `9` = Vivi's Theme). Plays on entry, and resumes after battle if there's an encounter. |
| `file` | **your own track**: a path to an audio file (wav/mp3/ogg/flac/… — anything ffmpeg decodes), relative to this `field.toml`. The build transcodes it to Ogg Vorbis and **mints a brand-new song id** (≥ 1000) into the mod, then wires the field to play it. Needs `ffmpeg` on PATH (or `$FFMPEG`). Only consulted when `song` is **absent** — if both are set, `song` wins and `file` is ignored. Custom audio loads at game **startup**, so hear it after a restart (~ reload isn't enough). |
| `loop_start` | with `file`: the loop point, in **samples**. Blank = the whole track loops. |
| `loop_end` | with `file`: the loop end, in samples. Blank = the track's end. |
| `stop` | **synthesize fields only.** `true` force-stops whatever field/battle BGM is currently resident on room entry — `RunSoundCode(265, 0xFFFF)` (`FF9SOUND_SONG_STOPCURRENT`), prepended as the literal first instruction of Main_Init. Kills the carried-in track from the *previous* field/battle unconditionally (no song id needed — it doesn't matter what was playing). Composes with `song`: `stop` fires first, then this field's own `song` (if any) starts on top. Without it, a field with no `song` of its own inherits whatever was already playing — FF9's normal resident-BGM behavior, which is usually what you want, but not for a field that must be silent (e.g. a `battle_music = -1` bench). |

Works on **synthesize** *and* **verbatim** forks, by different mechanisms:

- **Synthesize** (from-scratch field): appends a tiny init entry `{RunSoundCode(0, song); return}` and activates it on room entry (+ a tag-10 copy so it resumes after battle).
- **Verbatim fork**: **REPLACES** the donor's own field BGM in place. Every immediate field-BGM `RunSoundCode` of the donor's song — both the **PLAY** (`code 0`) *and* the **LOAD** (`code 1792`), in Main_Init and any after-battle/tag-10 resume — is rewritten to `song`, a length-preserving operand swap. Rescoring the LOAD is essential: patch only the PLAY and the engine keeps the *old* song resident and keeps playing it. The new track replaces, never stacks. A call referencing a *different* song id (a cutscene track, an SFX) is untouched. If the donor is silent or scores its BGM by a computed value (no immediate `RunSoundCode(0, song)`), there is nothing to replace — the build errors and `lint` flags it (author a synthesized field to *add* music to a silent room).

## `[behavior]` (optional — behavior TREES compiled to field bytecode)

Give named `[[npc]]`s real AI — patrols, notice-and-chase, mutual combat, flee-at-low-HP,
alarms, wandering — as **priority-ordered branches** compiled to pure field bytecode (zero DLL,
runs on stock Memoria). Full guide: [BEHAVIOR.md](BEHAVIOR.md). Offline tools:
`ff9mapkit behavior compile|lint|view <field.toml>`.

```toml
[behavior]
warmup = 45                                    # frames after field entry before anyone wakes
alternators = [{ name = "shift", frames = 400 }]   # a flag that FLIPS every N ticks (patrol shifts)
public_flags = ["raid"]                        # set from OUTSIDE (a [[choice]] lever); indices
                                               # print at build + `behavior compile`

[[behavior.unit]]
npc = "guard"                                  # binds to a named [[npc]]
hp = 5                                         # optional: an HP byte (enables swing_at/die)
speed = 40                                     # default walk speed

  [[behavior.unit.branch]]                     # branches in PRIORITY order; each tick the
  when = [{ hp_le = 0 }]                       # first branch whose conditions ALL hold
  do = { die = true }                          # selects its action

  [[behavior.unit.branch]]
  when = [{ near = ["player", 400] }]
  do = { chase = "player", speed = 65 }        # per-action speed applies MID-walk

  [[behavior.unit.branch]]                     # the last branch: unconditional, a static feed
  do = { patrol = "ringA" }                    # a [[marker]] with `path=` — the SAME route
                                               # the layout probe sweeps for walkability
```

**Condition verbs** (each `when` row = one dict): `hp_le` / `hp_gt` (int = own HP, `["unit", n]`
= another's) · `near` / `not_near` (`[target, r]`; target = a unit or `"player"`; Chebyshev) ·
`near_point` / `not_near_point` (`[point, r]`) · `flag` / `not_flag` / `any_flag` · `active` /
`not_active` (a unit lives) · `any_near` (`[[units...], r]` — the watcher idiom, actives gated) ·
`any_active` (`[units...]`) · `time_below` / `time_above` (remaining seconds on the field-level
`timer = <seconds>` countdown HUD — timed wave bands) · `counter_ge` / `counter_le` /
`counter_eq` (`["counter", n]`) · `table_ge` / `table_le` / `table_eq` (`["table", index, n]`;
`index` = an int or a **counter name** — a runtime-computed table lookup).

**Action verbs** (the `do` dict: one verb + its options): `walk_to` / `hold` (point; `speed`) ·
`chase` (target; `standoff` — pursuers stop short, never phase onto the target — `speed`) ·
`patrol` (loops its points) / `march` (walks them ONCE and holds the last; both: a route-marker
name or an inline point list; `arrive_r`, `speed`, and `route = "auto"` — at build time any leg
the walkability sweep finds off-mesh is re-routed through the walkmesh pathfinder, detours
spliced in, clear legs untouched; walls-only, 8-point ceiling — see
[BEHAVIOR.md](BEHAVIOR.md)) · `flee` (threat; `to` = refuge points in
priority order — the first the threat is NOT within `avoid_r` of; `speed`) · `wander` (centre;
`radius`, `every` = ticks between random re-targets, `speed`) · `swing_at` (a unit with `hp`;
`damage`, `interval`) · `die` (`true`, or a **counter name** — `die = "kills"` bumps that
counter once) · `battle` (a battle SCENE id — a REAL fight, one-shot per
field load by construction; the build auto-installs the after-battle Main_Reinit + BGM
resume; use a stock scene = no BattlePatch) · `award` (gil int; `+ item`/`count` — pays the
player EXACTLY ONCE via the event-Once lane; requires `once` on the branch) · `announce`
(a text line, minted into the field's `.mes`) / `announce_npc` (reuse that NPC's own
`dialogue` line).

**Branch extras:** `once = "name"` / `cooldown = frames` (sticky decorators — `once` fires
through one engagement then latches forever; `cooldown` re-arms N ticks after the behavior
*ends*). Exception: **`once` over an `announce` is an EVENT** — it fires the line once and
releases the branch immediately (edge-latched request lane), because announce conditions are
usually monotonic and a sticky hold would starve every branch below forever.
`raise_flags` / `clear_flags` (flag writes ride the selection — the alarm mechanism).
A `point` anywhere is `[x, z]` or a marker/NPC name. Everything resets on field reload.

**Pooled units (runtime activation):** `pooled = true` on a `[[behavior.unit]]` keeps its NPC
**out of the field at boot** (the entry is seated dormant — no spawn, no reveal flag needed) and
puts it in a named `pool` (default `"pool"`). Each pool gets a **spawn-request flag** (index
printed at build + `behavior compile`): wire a `[[choice]]` row's `set_flag = [<index>, 1]` to
it, and the next never-spawned unit of that pool **materializes at the player's feet** — the
press-time position becomes its *placement post*. The companion action verb `hold_post = true`
(a valid unconditional fallback) holds that post, so `pooled` + chase/swing branches +
`hold_post` = a **placement defender**: it guards wherever you dropped it and returns there
after a fight. One spawn per request; an exhausted pool consumes the request silently; a died
pooled unit does not respawn; field reload refills the pool. A pooled unit's NPC may not carry
`requires_flag` (the build owns its non-spawning) or be a prop `attach_to` target.

```toml
[[behavior.unit]]
npc = "recruit0"
hp = 4
pooled = true
pool = "recruits"                              # spawn-request flag index prints at build
  [[behavior.unit.branch]]
  when = [{ hp_le = 0 }]
  do = { die = true }
  [[behavior.unit.branch]]
  when = [{ active = "raider" }, { near = ["raider", 250] }]
  do = { swing_at = "raider" }
  [[behavior.unit.branch]]
  do = { hold_post = true }                    # hold wherever the player placed me
```

**Pool economy (`[[behavior.pool]]`):** `name` (a pooled unit's pool) + optional `price`
(gil-gated hires: `RemoveGil` compiles into the activation block and charges ONLY on an
actual spawn — broke or pool-empty consumes the request free) + optional `button = true`
(or a PSX button-mask int): a press-anywhere hire poller. `button` requires an explicit
`request_flag = N` (a GLOB bit outside the behavior blackboard band) and a PARKED zone
`[[choice]]` — its zone far off-mesh, its Hire row `set_flag = [N, 1]` — which the build
matches by that flag and the poller opens remotely. Every pool also publishes a
**`pool.<name>.hireable`** flag (ticker-refreshed: affordable AND not sold out) — put it in
the Hire row's `requires_flag` and the row vanishes instead of lying "Deployed!". See
[BEHAVIOR.md § Price and the buy-anywhere button](BEHAVIOR.md#price-and-the-buy-anywhere-button).

**Data tables (`[[behavior.table]]` / `counters` / `[[behavior.schedule]]`):** named int
arrays in the save's `gScriptVector` (the engine's 0xD3 computed-array-indexing lane),
**re-seeded at every field entry** — deterministic per-session state. `[[behavior.table]]`:
`name`, `values` (1..64 ints, ±26-bit), optional `id` (vector id; default allocates from
1000). `counters = ["wave", "kills"]`: runtime cells seeded 0 — read them with the
`counter_*` verbs, bump one with `die = "<counter>"`. `[[behavior.schedule]]`
(`counter` + `table`; needs `timer =`): THE WAVE CLOCK — `counter += 1` while the countdown
HUD sits below `table[counter]`; when the counter walks off the table's end the read fails
soft to 0 and the clock stops itself. Wave bands become data instead of unrolled
`time_below` branches. See [BEHAVIOR.md § Data tables](BEHAVIOR.md#data-tables-counters-and-the-schedule-clock).

## `[chocobo]` (optional — Chocobo Hot & Cold prize pool & timer)

Re-author the **Chocobo Hot & Cold** minigame's dig **prize pool** and **timer** on a **verbatim fork
of a forest field** — 2950 (Chocobo's Forest), 2951 (Lagoon) or 2952 (Air Garden). Start from an
export of the field's real pool, then edit values:

```
ff9mapkit chocobo-export 2950        # or: ch_fst, or a path to your fork's field.toml
```

paste the printed block into the fork's `field.toml`, and change the slots you care about:

```toml
[chocobo.tuning]
timer = 120              # in-game seconds = timer * difficulty + 1  (vanilla 60)

[[chocobo.prize]]        # slot 12 -- tier 4
slot = 12
item = "Elixir"          # what this slot awards when the RNG lands on it
```

| key | meaning |
|---|---|
| `[chocobo.tuning]` `timer` | the game-clock seed (seconds; the engine shows `timer * difficulty + 1`). |
| `[[chocobo.prize]]` `slot` | which of the **35 prize slots** (the export lists them all, tier-annotated). |
| … `item` | award an item, by name or id (`"Elixir"`, `239`). |
| … `gil` | award gil instead (1–28999) — paid out immediately at the dig. |
| … `nothing = true` | the dig finds nothing. |
| … `value` | raw escape hatch (the engine routes `<1000` = item id, `1000+N` = N gil, `30001` = nothing). |

Slots you **omit stay vanilla**; applying an unedited export is byte-identical. Because the game reads
one runtime prize variable for the award **and** the *"You found X!"* popup **and** the end-of-game
tally, a slot edit changes all of them together — the popup can never announce a different item than
you receive. Drop **odds** and dig-spot **coordinates** are not on this lane (they live in RNG jump
tables / coordinate formulas). Only meaningful on a **verbatim** forest fork (`lint`/Check flags it
elsewhere); deploy **in-place onto the real field id** (e.g. `--id 2950 --text-block 945`) to keep the
minigame's engine-drawn HUD.

**In the Workspace app:** expand a forest fork's **Script (verbatim .eb)** node — a
**🐤 Chocobo Hot & Cold** entry appears at the top (only on the three forest fields; hidden everywhere
else). It opens a form with the timer and all 35 prize slots grouped by tier; **Edit…** on a slot picks
Item / Gil / Nothing, each change dry-run-validated before it's written into the `[chocobo]` block.
