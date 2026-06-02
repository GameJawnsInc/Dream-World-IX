# `field.toml` reference

One `field.toml` describes one custom field. `ff9mapkit build field.toml` compiles it into a
Memoria mod folder. Pass several to build a multi-field mod.

```bash
ff9mapkit build my_room.field.toml --out dist --mod-name MyMod --author you
```

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
| `range`, `depth_offset`, `viewport`, `center_offset` | advanced overrides (sensible GRGR-derived defaults). |
| `borrow` | path to a `.bgx` whose `CAMERA` block to copy verbatim (instead of `pitch`/`fov`). |

### `[camera.frame]` (optional)
Used to auto-frame a flat walkmesh and the paint guide.

| key | meaning |
|---|---|
| `back` | painted-canvas row (Y, 0..448) the floor's back edge sits on (default `205`). |
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
| `size` | | `[w, h]` (default `[384, 448]`). |
| `shader` | | default `PSX/FieldMap_Abr_None` (respects painted alpha). |

> Painting the layers is a **human** task. `ff9mapkit guide` tells you exactly where the floor
> and its edges land on the canvas for your camera.

---

## `[walkmesh]`

Pick one (or omit all three to auto-frame from `[camera.frame]`):

| key | meaning |
|---|---|
| `obj` | a Wavefront `.obj` in FF9 world coords (x, y=0, z); faces become walk triangles. |
| `quad` | 4 corners `[[x, z], ...]` for a flat quad floor. |
| *(none)* | auto: a quad framed to the painted floor via `[camera.frame]`. |

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

---

## `[[gateway]]` (optional, repeatable)

A region the player walks into to warp to another field.

| key | meaning |
|---|---|
| `to` | target field id. |
| `entrance` | which entrance to arrive at in the target (default `0`). |
| `zone` | 4 corners `[[x, z], ...]` (auto-made IsInQuad-safe) or 5 explicit points. Order: the `q0→q1` edge is the walk-out direction (put the front edge first). |

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
