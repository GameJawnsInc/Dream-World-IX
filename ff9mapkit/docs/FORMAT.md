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
| `preset` | character preset (`vivi`, `zidane`, ...) → model + animations. |
| `model`, `animset`, `anims` | explicit alternative to `preset`. |
| `pos` | `[x, z]`. |
| `dialogue` | a line shown when talked to (assigned a non-colliding high text id automatically). |
| `text_id` | use an explicit text id instead of `dialogue`. |
| `requires_flag` | GlobBool index — the NPC only **appears** when that story flag is SET (its Init returns early otherwise: no model, not interactable). For story-gated characters. |
| `requires_flag_clear` | …only appears when the flag is CLEAR (the inverse — e.g. an NPC that leaves once an event fires). |

---

## `[[gateway]]` (optional, repeatable)

A region the player walks into to warp to another field.

| key | meaning |
|---|---|
| `to` | target field id. |
| `entrance` | which entrance to arrive at in the target (default `0`). |
| `zone` | 4 corners `[[x, z], ...]` (auto-made IsInQuad-safe) or 5 explicit points. Order: the `q0→q1` edge is the walk-out direction (put the front edge first). |
| `requires_flag` / `requires_flag_clear` | GlobBool index — the exit only **fires** when that story flag is SET / CLEAR (a locked door that opens once a switch flag is set). |

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
| `give_item` | `[item_id, count]` — `AddItem`. |
| `gil` | gil to add — `AddGil`. |
| `set_flag` | `[var, value]` — set a GlobBool story flag (gate other content on it). |
| `once` | `true` (default) = fires once ever, then never again (a GlobBool persists the state — a looted chest). `false` = fires **continuously while the player stands in the zone** (FF9's region trigger is *level*-triggered, not edge-triggered — a `false` message re-pops the instant you close it if you're still inside). Use `true` for a one-time line; `false` suits a continuous effect. A true "once per visit" (re-fires only after you leave and re-enter) isn't supported yet — it needs a leave-detecting re-arm zone. |
| `flag` | explicit GlobBool index for the `once` guard (default auto from `200`; **override to a free index for a shipped mod** so it can't clash with save state). |
| `requires_flag` / `requires_flag_clear` | GlobBool index — the event only fires when that story flag is SET / CLEAR (gate one event behind another). |

> An event needs at least one action. The same conditional-region primitive underlies chests, story
> flags, and one-time triggers. (Engine-validated bytecode + a real-chest `AddItem`/message
> convention; in-game proof pending.)

### Story flags & branching

A **story flag** is a GlobBool (a single bit in FF9's 2048-byte save-backed event memory) that an
event SETs (`set_flag = [N, 1]`) and other content reads (`requires_flag = N`). That's how the world
gains state: hit a switch (event `set_flag`) → a guard appears (`[[npc]] requires_flag`) and a door
unlocks (`[[gateway]] requires_flag`); open a chest once → it stays opened. Pick flag indices in a
free band (the kit's auto `once` flags start at 200 — keep your story flags clear of indices you also
auto-allocate, or set them explicitly). For unbounded mod state beyond simple flags, Memoria also
provides save-backed vector/dictionary stores (a future kit feature).

**Check your logic before building:** `ff9mapkit lint <field.toml>` (or the GUI's *Check logic*
button) reports schema errors plus story-flag lints — a `requires_flag` that no event ever sets (dead
content), an explicit flag index that collides with an auto-allocated `once` flag, and duplicate
entity names. `build` runs the same lints and shows them as warnings.

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
