# Authoring pipeline — from idea to playable field

This is the reference for the full from-scratch workflow. Two steps are **manual**: painting the
background art, and (optionally) modeling the walkmesh in a 3D tool. The kit owns everything
else — the camera math, the paint guide, the `.obj`→`.bgi` conversion, the script, and packaging.
For a step-by-step recipe that builds one such field end to end, see
[tutorials/03-original-art-field.md](tutorials/03-original-art-field.md).

The pipeline mirrors how FF9's pre-rendered backgrounds were made: a 3D scene shot through a fixed
camera, painted to a 2D plate, with characters projected back through that same camera — the paint
guide below is the modern stand-in for the layout render the original artists painted over.

```
                 ┌─────────────┐
  choose camera →│ ff9mapkit   │→ paint guide PNG ──▶ (manual) paint layers
                 │   guide     │                          │
                 └─────────────┘                          ▼
  model walkmesh.obj ──────────────────────────▶  write field.toml
  (or let the kit frame a flat quad)                       │
                                                           ▼
                                                  ┌─────────────┐
                                                  │ ff9mapkit   │→ mod folder → install → playtest
                                                  │   build     │
                                                  └─────────────┘
```

> **Visual front-ends.** The [Blender add-on](../blender/README.md) covers
> steps 2 and 4 (the camera + walkmesh): pose the camera in the 3D viewport, model the walkmesh
> against your painted art, place NPC/gateway/spawn markers, and one-click *Export Field* to a
> `field.toml` you then `build` exactly as below. The **Workspace GUI** (`ff9mapkit-workspace` on
> an installed copy; `py apps/ff9_workspace.pyw` from a repo checkout) covers the rest — Editor /
> Map / Build & Deploy / Import tabs, plus F9 one-keystroke deploy — and the form editor
> `ff9mapkit edit` fills in a `field.toml` without hand-writing TOML. The CLI steps here are the
> ground truth either way.

## 0. Install

Install the kit, then run **`ff9mapkit setup`** — the one-shot onboarding: it finds the FF9
install (Steam or GOG), remembers it, extracts the base assets, and reports Memoria status
(`--install-engine <zip>` also installs the bundled engine, taking DLL backups automatically).
The manual equivalent (point the kit at your FF9 install, run `extract-templates`, confirm with
`ff9mapkit doctor`) and the full one-time setup detail (prerequisites, the game-path resolution
order, the optional extras) are in **[../../SETUP.md](../../SETUP.md)**.

A **novel** field built this way runs on a **stock, unmodified Memoria install**; a **forked**
field needs the bundled fidelity patch set (custom Memoria) — see [ENGINE.md](ENGINE.md).

Setup problems (templates not extracted, install not found) are covered in
[TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## 1. Scaffold

```bash
ff9mapkit new MY_ROOM --area 11
```

Creates `MY_ROOM/my_room.field.toml` (a commented template) + `MY_ROOM/art/` with **placeholder art**
(a solid backdrop + a perspective checkerboard floor, generated to match the template camera) and a
walkmesh quad derived from that camera. So `ff9mapkit build MY_ROOM/my_room.field.toml` works
**immediately** — you get a walkable placeholder room to test the loop, then replace `art/back.png` +
`art/floor.png` with your painted layers (step 3).

### …or fork a REAL field instead of starting blank

To start from one of FF9's ~674 real fields (needs the assets extra: `pip install ff9mapkit[assets]`):

```bash
ff9mapkit list-fields glgv                     # find a field
ff9mapkit fork-report glgv_map792_gv_rm1       # preview what a fork will/won't reproduce (offline)
ff9mapkit import glgv_map792_gv_rm1 --out MY_FORK            # BG-borrow: reuse its art/walkmesh/camera
ff9mapkit import glgv_map792_gv_rm1 --out MY_FORK --native   # seam-free per-tile fork (best art fidelity)
ff9mapkit import glgv_map792_gv_rm1 --out MY_FORK --editable # repaintable custom scene (see below)
ff9mapkit import glgv_map792_gv_rm1 --out MY_FORK --verbatim # real .eb/.mes whole (best behavior fidelity)
```

Run **`fork-report`** before forking: it previews the field's NPC roster, story-gated beats, and a
suggested `[startup]` without touching any bytes (`--explain` decodes what each NPC's talk routine
does). Related discovery commands: `ff9mapkit find-rooms` sweeps every field for good test rooms, and
`ff9mapkit import-all` bulk-imports a foldered, Blender-ready archive of the whole game (or a
`--pattern` zone).

The four fork modes:

- **BG-borrow** (default) renders the real field's art + walkmesh + camera and runs your script on top — fastest, but the art is not editable. (A field whose area id is below 10 cannot BG-borrow; `import` auto-routes those to a `--native` fork.)
- **`--native`** — the recommended path for **art fidelity**: a seamless per-tile fork (vanilla `.bgs` + atlas) with no tile seams and faithful occlusion; repaint it with `ff9mapkit repaint-native`.
- **`--editable`** forks it into a full custom scene you can repaint: the walkmesh is re-exported to `walkmesh.obj`, and the background is split into **one `layer_*.png` per depth** (occlusion preserved — foreground pieces still draw over the player; additive light/shadow overlays are carried as per-layer `shader` entries). Repaint any single layer, reshape the walkmesh, add content, then `ff9mapkit build`. The art is assembled **offline from the game's atlas** — no in-game export step is needed. This `.bgx` path can show faint seams at depth-layer boundaries; prefer `--native` when art fidelity matters.
- **`--verbatim`** — the recommended path for **behavior fidelity**: ships the field's whole real event script + text (`.eb`/`.mes`), so the real NPCs, dialogue, story gating, cutscenes, and doors run as shipped (only `Field()` destinations are remapped).

**Import also extracts the real field's content** (read straight from its event script), so a fork keeps the real place's exits, battles, and music, not just its look:

- its **exits** → live `[[gateway]]` blocks
- its **random encounters** → `[encounter]`
- its **field BGM** → `[music]`
- its **WASD-vs-camera tuning** → `[camera] control_direction`

Imported gateways point at the **real destination field ids** (a comment flags them) — retarget each `to` to your own room ids, or leave them to walk back into the live game. The real field's **NPCs and props are carried too**: `--dialogue` adds editable dialogue stubs, `--carry-text` carries the verbatim per-language text, and `--verbatim` (above) keeps the full original behavior — story gating, event triggers, and cutscenes included.

Either way you get a ready-to-edit `field.toml` — skip to step 5.

## 2. Choose a camera and get a paint guide

Decide the angle. Real FF9 fields tilt down `~15–48°`; steeper (top-down) also works.

```bash
ff9mapkit guide --pitch 48 --distance 4500 --fov 42.2 --png MY_ROOM/art/guide.png
```

This prints the floor's world extent and **exactly where its corners/edges land on the
384×448 painted canvas**, and writes a checkerboard guide PNG. It also prints the walkmesh
corners for that frame. For painting, `guide --template` writes a transparent trace-over
paint template instead of the checkerboard (`--template-layers` splits it into per-layer PNGs
plus a manifest), and `ff9mapkit paint-template <field.toml>` projects an existing field's
floor + content onto per-layer trace-over PNGs with a legend.

## 3. Paint the background layers (manual)

Paint over the guide (or the trace-over template from step 2). Typical layers, back-to-front:
- a **back** layer (everything behind the player),
- a **floor** layer,
- optionally a **front** layer with a small `z` so it draws *over* the player (occlusion).

Logical canvas is 384×448; export at 4× (1536×1792) for crispness. Save PNGs (RGBA, with
transparency where the layer shouldn't cover) into `MY_ROOM/art/`.

## 4. The walkmesh

Either:
- model it in Blender in **FF9 world coords** (x, y=0, z), export `.obj`, set `walkmesh.obj`; or
- use a flat `walkmesh.quad` (the 4 corners the guide printed); or
- omit it and let the kit auto-frame a quad from `[camera.frame]`.

`ff9mapkit walkmesh obj mesh.obj out.bgi.bytes` converts an `.obj` directly; the kit also
rebuilds the triangle-neighbor links Memoria's editor gets wrong.

## 5. Fill in `field.toml`

Layers, walkmesh, player spawn, NPCs + dialogue, gateways, an encounter, music — see
[FORMAT.md](FORMAT.md). See `examples/vivi-hut/hut_int.field.toml` for a complete worked example.

## 6. Build

```bash
ff9mapkit build MY_ROOM/my_room.field.toml --out dist --mod-name MyMod
```

Produces a complete mod folder: the background scene, the walkmesh, the 7-language event
script, dialogue text, and the DictionaryPatch / BattlePatch / ModDescription.

**The build checks your work** (since you can't see the game until you launch it).

**Errors** (broken geometry):

- a `.obj` with no triangles;
- a face referencing a missing vertex.

**Warnings** (something will look wrong in-game):

- content placed **off the walkmesh** (an NPC that would float, a spawn off the floor, a gateway
  zone the player can't reach);
- an **NPC or spawn within the player's collision radius (~48u) of a wall** (the player's centre
  can't reach that close to an edge — advisory);
- a **multi-floor walkmesh whose floors got disconnected** (a `.obj` reshape without the seam sidecar);
- **zero-area triangles** (dead zones);
- a **broken seam** (you moved a connecting edge);
- a **repainted layer whose aspect ratio no longer matches** its size (it would stretch);
- a **camera pitch** outside FF9's real range.

Read the warnings before you playtest — they catch the mistakes that otherwise only
show up in-game.

The same checks run standalone, without building: `ff9mapkit lint <field.toml>` runs every offline
validator in one pass, and `ff9mapkit walkmesh verify <path>` checks a walkmesh on its own — useful
while iterating on art or geometry.

## 7. Install + playtest

Copy the built folder into the game install (next to `FF9_Launcher.exe`), or build with
`--out` pointing straight at the game's mod folder. Reach the field via a gateway from a
real field (add a `[[gateway]]` to it in an existing field), or warp straight to it with the
**debug menu (~)** (Go tab → *Warp to field*, with a search filter), and play. The debug menu ships
in the `dwix-custom-memoria-*.zip` engine bundle, installable via the Windows installer or
`ff9mapkit setup --install-engine <zip>`.

```bash
ff9mapkit pack dist/MyMod --out MyMod.zip      # to share it
```

If the field black-screens, or a change doesn't show after a redeploy, see
[TROUBLESHOOTING.md](TROUBLESHOOTING.md) — the in-game failures there cover the common causes
(area < 10, an id collision, a stale text block).

## Camera movement & bigger environments

FF9 fields are **fixed-perspective pre-rendered art** — the angle is baked into the painting and
is never re-rendered from a new viewpoint at runtime. What looks like "camera movement" in the
real game is one of three things:

1. **Scrolling.** Most rooms are *larger than the screen*: one big fixed-perspective painting, and
   the engine pans the view window across it to follow the player (`SceneService2DScroll`/`3DScroll`
   in the engine). The angle never changes — only the 2D scroll offset does.
2. **Multiple cameras per field.** A field's scene can hold more than one camera block, each with
   its **own** pre-rendered art for a different part of the room; crossing a zone boundary *switches*
   cameras (a cut, or scroll-then-switch). That's how a room shows two genuinely different angles —
   two paintings, not a moving 3D camera.
3. **Scripted cutscene pans** — animated pan/zoom *over* the big pre-render (the cinematic stuff is
   pre-rendered FMV).

So when you author with this kit you **set one pose and paint one perspective** — that pose + painting
is the unit. Make a single screen feel alive with depth layers (foreground occlusion), animated
overlay sprites (torches/water), and lighting baked into the art — not by moving the camera.

### Scrolling rooms (larger-than-screen) — supported

A room whose painting is **bigger than the screen** scrolls the view to follow the player. The
engine pans automatically; authoring one means painting a bigger canvas and enabling scroll in
the camera config — declare the painting size in `[camera] range`, keep `window_width = 384`
(so the focal length stays normal — widening the painting must not widen the FOV), and set
`[camera.scroll] enabled = true`. The exact keys are in [FORMAT.md](FORMAT.md).

`ff9mapkit guide` (and the demo generator) auto-size the **paint guide to the full painting**, with
**height guides** (poles/rings/room-box at the floor edges) so you can paint walls in correct
vertical perspective — not just a floor. Make the walkmesh span the painting; the kit auto-derives
the scroll bounds and injects the enable opcode. Runs on **stock Memoria**. Proven in-game on a
768×448 room (see `examples/scroll-demo/`). For an even bigger space, **chain scrolling rooms with
gateways**.

**Multi-camera** switch zones (one field, several pre-rendered angles switched as the player crosses
trigger zones) are **supported**: declare a `[[camera]]` array + `[[camera_zone]]` switches (see
[`FORMAT.md`](FORMAT.md)) or place them visually in the [Blender add-on](../blender/README.md). The
kit injects the `SETCAM` switch script and the after-battle camera restore for you.

## What the kit does NOT do
- **Paint art** — you do (step 3). The kit only tells you where things land.
- **Judge walkmesh/camera alignment against the running game** — you verify that in-game.
