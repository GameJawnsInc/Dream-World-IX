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
- **From-scratch effects** — `codec.build(...)` can already emit a valid `.sps` from scratch; a GUI creator over it
  is Tier 2/3.

---

## The format (one breath)

`.sps`, little-endian: `header0 u16` (`frame_count & 0x7FFF`), `tpage_raw u16`, `clut_raw u16`, `h_raw`/`w_raw u8`,
a `u16[frame_count]` frame-offset table, then `rgb_offset u16` + a UV-pair table + a `0x0010` separator + a
stride-4 RGB ramp, then per-frame blocks (`u8 prim_count` + 3-byte prims `i8 pos_x, i8 pos_y, u8 texpos`; the
texpos low nibble picks a UV cell, the high nibble an RGB colour). Pixels live in `spt.tcb` (a PSX-VRAM blit blob).
Full byte spec: `ff9mapkit/sps/codec.py`. The codec round-trips every real donor byte-exact and `build(...)`
emits a valid effect from scratch.
