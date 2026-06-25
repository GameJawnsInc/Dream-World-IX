# SPS — FF9 field particle effects (browse, preview, re-skin)

**SPS** (Special Particle System) is FF9's particle layer: fire, smoke, candle flicker, save-sphere glow, magic
shimmer. An `.sps` effect is a **multi-frame cloud of 2D textured billboard quads** ("prims"). Each frame is a
list of quads positioned in 2D, all sampling one shared per-scene texture (`spt.tcb`) through a small UV atlas +
a 16-colour RGB ramp. The field `.eb` fires `RunSPSCode(slot, 130, id, 0, 0)` to load `FieldMaps/<FBG>/<id>.sps`,
place it, and loop it at ~15 fps.

The kit already **carries** a fork's `.sps` + `spt.tcb` verbatim so a forked field keeps its donor's effects (see
[FORK_FIDELITY](FORK_FIDELITY.md) and the `project-ff9-sps-fork` memory). This page covers the **authoring** side:
decode/preview any effect (Tier 0) and re-skin one declaratively (Tier 1). The full reverse-engineering +
roadmap lives in the `project-ff9-sps-authoring` memory.

---

## Tier 0 — browse & preview (read-only)

Decode any field's effects and render them to PNG/GIF offline (the bespoke analogue of Memoria's in-engine Model
Viewer). Install-gated: needs your FF9 install + UnityPy (`py -m pip install UnityPy`).

```
ff9mapkit sps 303                          # list a field's SPS effects (by field id or FBG token)
ff9mapkit sps 303 --id 2266                # decode ONE effect -> facts (frames, prims, tpage/clut, tables)
ff9mapkit sps 303 --id 2266 --png fire.png # render the frames to a contact-sheet PNG
ff9mapkit sps 303 --id 2266 --gif fire.gif # render an animated GIF (~15 fps loop)
```

The previewer composites each frame's quad cloud over the decoded `spt.tcb` page (additive blend, the fire/smoke
default). It's a catalog preview, not the exact engine projection (no per-camera GTE transform / depth sort).

Programmatic surface (`ff9mapkit.sps`):

- `codec.parse(bytes) -> Sps` / `codec.serialize(Sps) -> bytes` / `codec.build(...)` — the lossless codec.
- `texture.tcb_page_rgba(tcb, tpage_raw, clut_raw)` — decode the shared `spt.tcb` page to RGBA.
- `render.render_frame / render_strip / save_png / save_gif` — the previewer (needs Pillow).
- `catalog.list_field_sps(field)` / `load_sps(entry)` / `load_tcb(field)` / `effect_facts(sps)` — the live catalog.

---

## Tier 1 — re-skin an existing effect (`[[sps_edit]]`)

Re-skin a **carried** effect over its donor texture — recolour, tint, rescale, reposition — declaratively in
`field.toml`. No texture work, no `.eb` change, no DLL. Only applies to a **native fork** (a field that carries
the donor's `sps/` bins — i.e. `import --native`/`--verbatim`, which sets `[field] bgs`). A bad edit fails the
**build** (surfaced in `ff9mapkit lint` / the Workspace **Problems** console), never the game.

Each edit names its target effect with the required `sps` selector (the `<id>` from `ff9mapkit sps <field>`).

```toml
# Make the Ice Cavern melt-fire (effect 2266) blue and bigger.
[[sps_edit]]
kind = "tint"            # multiply EVERY ramp colour -- recolour/brighten the whole effect
sps  = 2266
mul  = [0, 0, 512]       # per-channel, 256 == identity; this turns a grey/orange ramp blue (and 2x brightness)

[[sps_edit]]
kind = "scale"           # resize the quads + UV cells
sps  = 2266
old_size = [9, 9]        # [h_raw, w_raw] guard -- refuses if the donor drifted
new_size = [13, 13]      # quad half-size = (raw-1)*2 ; UV-cell size = (raw-1)

[[sps_edit]]
kind = "recolor_ramp"    # overwrite ONE ramp colour precisely
sps  = 2266
index = 1                # rgb_table row
old = [128, 128, 128]    # old-guard (current r,g,b)
new = [200, 40, 40]

[[sps_edit]]
kind = "reposition"      # shift prims (one frame, or all)
sps  = 2266
dx = 4
dy = -2                  # i8-bounded; an edit that pushes a prim past +-127 is refused
# frame = 0              # optional; omit = every frame
```

Conventions mirror `[[logic_edit]]`: a `kind` discriminator, an `old`/`old_size` guard that refuses on donor
drift, integer-only keys, and a typo-catching key whitelist. Build wiring: the edit is applied **in flight** as
the donor `.sps` bins are copied into `FieldMaps/<FBG>/` (`spt.tcb` and unmatched effects pass through untouched).

### What Tier 1 does NOT do (yet)

- **New texture / art** — Tier 1 only rearranges/recolours pixels already in the donor's `spt.tcb`. New art is the
  texture gate (PNG-override or a regenerated `spt.tcb`) — a Tier 2 follow-up.
- **Playback speed / blend mode** — frame-rate (`FRAMERATE`) and additive/subtractive blend (`ABR`) are
  `RunSPSCode` operands in the `.eb`, not `.sps` bin fields, so they're an `.eb`-edit follow-up.
- **From-scratch effects** — that's Tier 2 below.

---

## Tier 2 — create a new effect (`[[sps]]`)

Author a **brand-new** effect on a field and have it draw in-game — no DLL. A `[[sps]]` block defines the effect's
geometry (clone a real donor effect and re-author its animation, or build every byte inline) over a **reused or
borrowed** `spt.tcb` texture (**Route A**). The build writes `<id>.sps.bytes` + supplies the `spt.tcb` into the
field's `FieldMaps/<FBG>/`, and injects a `RunSPSCode` create+place trigger into the field's `.eb` so the effect
spawns on field load. Works on any field path (native fork / custom scene / BG-borrow).

```toml
# Easiest: a named TEMPLATE (a curated preset -- `ff9mapkit sps --templates` lists them:
# fire / bonfire / smoke / sparkle / embers / glimmer). Drop it on the floor and you're done.
[[sps]]
id       = 5000
template = "fire"
pos      = [2354, -3372]    # [x, z] -> auto-grounded to the floor

# Clone one of THIS field's OWN carried effects (a fork that ships its own sps/ + spt.tcb). Reuses the
# carried texture, so it always renders -- the right choice on a native/verbatim fork. `ff9mapkit sps
# <field>` lists the ids it carries.
[[sps]]
id        = 5001
copy_from = { sps = 42 }                    # no `field` -> clone the field's own effect 42 (reuse its texture)
pos       = [800, 226]

# Clone a specific DONOR field's effect (for a field that does NOT carry its own texture -- BG-borrow / synth).
[[sps]]
id        = 5002
copy_from = { field = "303", sps = 2266 }   # take tpage/clut/uv/rgb/size from Ice-Cavern fire 2266
frames = [                                  # optional: a new quad-cloud animation over the cloned pixels
  [ {pos = [-30, 0], uv = 0, rgb = 3}, {pos = [0, 4], uv = 1, rgb = 1}, {pos = [30, 0], uv = 2, rgb = 5} ],
  [ {pos = [-30, 2], uv = 1, rgb = 2}, {pos = [0, 8], uv = 2, rgb = 0}, {pos = [30, 2], uv = 0, rgb = 4} ],
]
pos       = [2354, -3372]   # [x, z] -> the kit AUTO-GROUNDS y from the walkmesh floor (recommended)
slot      = 14              # SPS slot 0..15 (omit -> auto-assigned top-down from 15)
abr       = 1               # blend: 0=50%add 1=add 2=sub 3=25%add
framerate = 16              # 16 = 1x

# Power user: borrow a donor's tcb, author every byte via codec.build.
[[sps]]
id      = 5003
texture = { borrow_tcb = "303", tpage = { tp = 0, tx = 8, ty = 1 }, clut = { cluty = 251, clutx = 20 } }
size    = [9, 9]            # [h_raw, w_raw]
uv      = [[0, 96], [32, 96]]              # the UV atlas cells (into the borrowed tcb)
rgb     = [[255, 200, 80], [255, 120, 0]]  # the colour ramp
frames  = [ [ {pos = [0, 0], uv = 0, rgb = 0} ], [ {pos = [2, -1], uv = 1, rgb = 1} ] ]
pos     = [0, 0, 0]
slot    = 13
```

`id` must be unique and not collide with a carried donor effect (use the custom band, e.g. `5000+`). A bad block
fails the **build** (surfaced in `ff9mapkit lint` / the Workspace Problems console). Verify with `deploy_field` →
F6. Programmatic surface: `sps.author.build_sps_from_block` / `tcb_source` / `trigger_spec`;
`content.sps_trigger.inject_sps_triggers` emits the `.eb` trigger.

### Placement (the floor-Y rule)

`pos` is the effect's **world** position. Prefer `pos = [x, z]` and let the kit fill the height from the walkmesh
(`_autoground_sps`) — the effect drops onto the floor at `(x, z)`. If you set `y` yourself (`pos = [x, y, z]` or
`pos = [x, z]` + `y = N`), note the engine's double-negation: a `RunSPSCode POS` negates Arg1, **and** the render
frame negates the walkmesh Y, so the `y` that lands an effect **on** the floor is `+height_at(x, z)` (positive),
and a *smaller* `y` floats it **up**. Effects are 2D billboards drawn in screen space with no depth-push op (the
engine's `zOffset` is a hardcoded per-field hack), so an effect only shows where its world position isn't behind
foreground scene geometry — place it in open space, not tucked against a wall. (In-game proven 2026-06-25 on a
forked Ice Cavern; the offline `scene.cam.project` / `to_canvas` replica of `PSX.CalculateGTE_RTPT_POS` predicts
exactly where an effect lands, for debugging placement without launching the game.)

### In the Workspace GUI

Two surfaces, no hand-written TOML needed:
- **Editor → a field's "Effects" section** — add/edit `[[sps]]` effects with a form (id · template · position ·
  slot · blend · frame-rate). The **Template** field has a **Browse** button into the Info Hub picker (preview
  included); the position auto-grounds. Saves into the field's `field.toml`, like NPCs/events.
- **Info Hub → "SPS templates"** — browse the presets with **live preview thumbnails**; *Copy snippet* gives a
  ready `[[sps]]` block. (The companion **"SPS effects"** section browses a fork's *carried* effects for
  `[[sps_edit]]` re-skins.)

### Route B — genuinely new art (not yet)

Drawing pixels that **don't already exist** in any `spt.tcb` needs a custom `FieldMaps/FieldSPS/<id>.png`. The
engine resolves a field effect's texture through a **hardcoded** `SPSConst.SPSTexture` dictionary (no data hook),
so a new id never looks for its PNG — Route B requires a small Memoria patch (a `spsId`-keyed PNG fallback) to the
shipped engine. A `texture = { png = ... }` block is rejected today with that pointer. Tracked as a follow-up.

---

## The format (one breath)

`.sps`, little-endian: `header0 u16` (`frame_count & 0x7FFF`), `tpage_raw u16`, `clut_raw u16`, `h_raw`/`w_raw u8`,
a `u16[frame_count]` frame-offset table, then `rgb_offset u16` + a UV-pair table + a `0x0010` separator + a
stride-4 RGB ramp, then per-frame blocks (`u8 prim_count` + 3-byte prims `i8 pos_x, i8 pos_y, u8 texpos`; the
texpos low nibble picks a UV cell, the high nibble an RGB colour). Pixels live in `spt.tcb` (a PSX-VRAM blit blob).
Full byte spec: `ff9mapkit/sps/codec.py`. The codec round-trips every real donor byte-exact and `build(...)`
emits a valid effect from scratch.
