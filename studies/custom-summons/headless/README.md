# Headless effect host

Runs `FF9SpecialEffectPlugin.dll`, the native battle-effect engine, **outside the game** in a plain
Python process. You give it a container (`ef###`), and it steps the plugin's own clock until the effect
ends itself. It reports what the plugin did: every primitive it emitted, the camera on every frame, the
summon slot, VRAM uploads/readbacks/blits, sound cues and damage points. It does this deterministically,
in seconds, with no game window and no owner cast.

Everything Tiers R and W learned by reading the DLL, or by arming an in-game probe and asking the owner
to cast, this host can answer by *running* the plugin. It's an oracle for the native layer; its
primitives are data. `raster.py` then draws them the way Memoria's managed renderer does, so "does this
reach the screen?" has an offline answer too (see *Pixels*).

```bash
py -I sfx_host.py stage                                   # copy the install's plugin into the SCRATCH cache
py -I sfx_host.py run --ef 227                            # one container from the SCRATCH corpus
py -I sfx_host.py run --ef 227 --from-install             # ... read from the install's resources.assets
py -I sfx_host.py run --ef 227 --container <path>         # an edited container / mod-folder override
py -I sfx_host.py run --ef 227 --frames-csv C:/gd/SCRATCH/summon-format/headless/ef227.csv
py -I sfx_host.py census --jobs 6                         # all 372 containers -> SCRATCH census.json/.tsv
py -I hx_gates.py                                         # the calibration (exit 0 / 1 FAIL / 2 MISSING input)
py -m pytest studies/custom-summons/headless/test_sfx_host.py -q
```

## Why it works

PLAN §3A already established the shape. The plugin has no graphics or file imports, 13 exports that
match Memoria's `DllImport` block one-to-one, and a single host callback. The host:

1. copies the user's own plugin and its CRTs into the SCRATCH cache;
2. routes CRT asserts to stderr **before** the plugin loads (the CRT's default is a modal dialog on the
   desktop);
3. calls `SFX_InitSystem(callback)`, `SFX_InitBattle` with the stock debug-room actors
   (`btl_id = 1 << i`, players 0–3), `SFX_Play`, and then per frame `SFX_Update`, `SFX_LateUpdate`,
   `SFX_BeginRender`, `SFX_GetPrim` until empty, then `SFX_UpdateCamera`;
4. runs every container in a **child process**, so an assert, a native crash or a hang (the HIRAISHI
   self-loop class) becomes a verdict (`assert`/`crash`/`timeout`) instead of a dead caller.

**The callback is `SFXData.BattleCallbackDummy`, code by code.** That is the callback the live game
installs for every SFXRework cast (`SFXDataMesh.Runtime.Begin`). VRAM loads, readbacks and moves are
live; every SET call is swallowed. The animation queries (codes 9 and 10) answer a literal 1, and Stop
Animation echoes its argument. Each code writes exactly the bytes the managed handler writes; one wrong
width corrupted the plugin's stack in the first spike. `--mode legacy` gives `SFX.BattleCallback`
semantics (SFXRework=0) instead.

**The plugin's internal offsets** (summon slot, view matrix, OFX/OFY/H) are read only on the pinned
build (`PINNED_BUILDS`, x64 sha `5e01f899…`). On any other build those columns are `None` and the run
says so. The table is not kept here: the host loads the x64 entries of the kit's one pin table,
`ff9mapkit/ff9mapkit/sfxplugin.py`, which the `[SfxHybrid]` arm refusal also reads and a kit test pins
to the engine's s53/s58/s152 constants -- so a re-measured or newly pinned build reaches all three at once.

## Calibration (`hx_gates.py`, 8/8 PASS)

Each gate compares the headless run with something measured **in game**, or with a mechanism a cast
already proved.

| Gate | Checks | Result |
|---|---|---|
| HX0 | the staged plugin is the pinned build | x64 `5e01f899…` |
| HX1 | Bahamut's timeline vs all three archived s53 captures | H installs f58→256, f153→415, f302→512, f529→490; creature first frame **f82**; last frame **f561**, all exact |
| HX1b | the full 12-number native view matrix, frame by frame, f128–f528 | **391/401 frames exact (97.5%)**. One frame off either way drops to ≤ 3. The only difference is f424–433: rotation within 7/4096, translation within 17 units |
| HX2 | **the falsifier**: a wrong host (legacy, 30-frame caster animation) | H at f106/201/350, so HX1's comparison **rejects** it |
| HX3 | determinism | two runs, byte-identical primitive stream |
| HX4 | W3 retime, offline | aligned: last frame 561→609 (+48), every post-entrance H install +48, creature window 408→456 frames. Mis-retime: the same +48 camera, creature window 410. That's the desync the owner saw in the cast |
| HX5 | ef407's scroll blits really run | 252 blits rewrite (704,384) from (704,256), frames 85–211 |
| HX6 | the Phoenix dome mechanism | see *Findings* |

Outside the matrix window, the frames that differ are explained. f59–127 is Bahamut's entrance-phase
camera shake (`rand()` × an envelope, per W3's emulator): rotation is identical, translation is off by
≤ 115 units, because the game's random-number state is whatever earlier effects in that battle left
behind. f529 onward is the hand-back to the battle camera, which a headless run doesn't have.
Frame numbers everywhere are the plugin's own `frameIndex`, the number every in-game probe logs.

**There is no fitted parameter.** The draft spike reproduced the cast only after a "caster animation
length" was set to 1. The SFXRework callback turned out to answer exactly that literal. The +18-frame
offset the first spike showed came from its stub reporting a 30-frame animation: the plugin waits on
the caster's animation.

## Census (372 containers, rework host, 6 children)

| | |
|---|---|
| Completed on their own | **372 / 372**, 0 host callback errors, a camera every frame in all of them |
| Frames per cast | 61 – 1,747, median 130 (Ark ef381 is the longest) |
| Primitives emitted | 22.7 M; 821 s of child-process time in total, the longest single run 34 s |
| Hold a live summon slot | 20 containers |
| Scroll-blits that execute | 64 containers, 136 (container, destination cell) pairs |
| Emit on-screen primitives sampling at 15bpp | 68 containers |

Output (stock-derived, SCRATCH only): `C:\gd\SCRATCH\summon-format\headless\census.json` / `census.tsv`.
Each row has the sampled cells (`"x704_y256@8"` → prims, on-screen prims, palettes, frame span), the
executed blit destinations (with their source cells and frames), H installs, the creature window, sound
and effect-point events, VRAM uploads, and the primitive-stream hash.

The draft sweep with a crude stub had ef089 asserting (`psx_compatibility.cpp:786`) and ef237 hanging.
Under the faithful rework host both complete. **A failed headless run is a statement about the host
before it's a statement about the container.**

## Findings

- **The Phoenix "dome" is reached by a blit, not drawn where it was painted.** W6b-2 recorded ef211's
  (704,384) as readerless yet drawn: the owner saw the dome bands. Headless, no primitive samples
  (704,384) at all. ef211 blits (704,384) → (704,256) 100 times over frames 235–284, and the 8bpp page
  that samples (704,256) draws over **exactly** frames 235–284. The cast was right that a repaint of
  (704,384) shows up, and right about 8bpp. The reason is that it's a scroll-blit *source*. That's also
  why no record binds it. (HX6)
- **ef407's scroll blits are reachable.** The Tier R DR_MOVE check found statically that (704,384) is a
  destination, but couldn't establish that the blit runs. It does: frames 85–211. A repaint there is
  overwritten every frame, so tier-w's planned gain-half cast must paint the source (704,256). (HX5)
- **The native plugin emits on-screen 15bpp-sampling primitives.** ef429's (448,256/384) and ef251's
  x512 column are examples, matching their registered tpages (e.g. 0x138, the "tpage 312"). So the
  ghost-layer observation (*every 15bpp-attributed cell probed was never drawn, or drawn at another
  depth*) is not the plugin declining to draw them. ⛳ **Resolved downstream by `raster.py`:** Memoria
  reads those pages from its render target, not VRAM (see *Pixels* below).
- **ef094, ef154 and ef237 hold a live summon slot when run alone** (posed bones, sane node 0, 61/39/61
  frames), although they carry no creature package. R1 read them as drawing a creature another effect
  registered. Run in isolation they set up a skeleton themselves; whether anything is drawn from it is
  not established.

## Pixels: the managed-renderer port (`raster.py`)

```bash
py -I raster.py run --ef 227 --frames 82,150,300 --scale 2      # PNGs + visible cells (SCRATCH)
py -I raster.py diff --ef 211 --b <edited container> --frames 230-290 --out <SCRATCH dir>
py -I raster.py routes --jobs 6 [--control]                     # every container: key sources + copies
py -I stale_census.py [--only 499] [--control] [--rejoin]       # every container: is each copy ever SEEN?
py -I raster.py calibrate --ef 227 --log <s48 probe log> [--offset 19]   # in-game f vs headless f+19
py -I rx_gates.py [--battery]                                    # RX0-RX3 (+ RX4, the owner-verdict battery)
```

`sfx_host.py` says what the plugin *emitted*. `raster.py` ports, line for line, what Memoria then does
with it: `SFXRender.Add`/`GetMesh`/`PushCommandBuffer` (one batched mesh per *mesh key*, re-ordered by
blend family per `SFX.playParam`, not by the ordering table), the `SFXKey` encoding (bugs included),
`PSXTextureMgr`'s 50-entry texture cache and its `ClearKey` refresh rule, `PSXTexture`'s decode, and the
six `SFX_OPA/ADD/SUB_G[T]` shaders' D3D9 programs (vertex colour clamped, `abr` 0/1/3 as ADD at alpha
63/127/31, `abr` 2 as reverse-subtract, a depth buffer keyed on OT depth). It drives the plugin itself
(`RasterHost` subclasses the host; `sfx_host.py` is untouched), writes a 320×220 PNG per frame, and counts
per VRAM cell the fragments that **changed** the screen. `diff` renders two containers in separate
processes and diffs them frame by frame: offline "does my edit reach the screen?". `run(watch=[cells])`
also maps, per drawn frame, which screen pixels each named cell's fragments changed, so a diff can be
charged to the cell that carried it.

### Calibration (`rx_gates.py`)

Ground truth is in-game data already in SCRATCH: the s48 probe logs (every primitive the game got from
`SFX_GetPrim`, and every mesh Memoria built from them, per frame) and the W6b verdict casts (an edited
container, cast, judged on screen by the owner).

| Gate | Checks | Result |
|---|---|---|
| RX0 | the staged plugin is the pinned build | x64 `5e01f899…` |
| RX1 | input: on frames where the game and the host emitted the same prim sequence, first vertices agree | 207,453 vertices, **95.0% exactly** at Memoria's widescreen `drOffsetX` (+35, 0) |
| RX2 | batching: on those frames, the port reproduces the in-game command buffer (index, key, triangles) | **306/306** frames exact (Bahamut ×2, Phoenix ×2, Shiva) |
| RX3 | falsifier: the wrong render order (Add before Opa) must fail RX2 | 9/34 Bahamut and 122/229 Phoenix frames break |
| RX4 | pixels: 16 owner-verdict casts, edited container vs its pre-state, drawn vs not drawn | **15/15** scored verdicts reproduced; 1 contested (below) |

RX4's cases: the Phoenix ladder (1a/1b wheels into (704,256) never seen; 1c–1f and the dome drawn),
Odin's channel-A cast A, ef446 cast B, ef251 cast 15 and its x512 probe, and ef429's census probe and
three cover probes (never seen). Every "never seen" cast renders byte-identical to its pre-state, and
every drawn one changes the screen. **The contested one is Phoenix cast 2b**, the bold wheel recorded as
eroding the vortex smoke. The port shows it on no frame, and the game's own ladder capture agrees on the
mechanism. ef211 rewrites the band the wheel sits in, (576,368) 28×112, from (604,368) with a cyclic scroll.
Those DR_MOVEs are the first commands of every frame from f47 to f360, and the page is drawn only in
f47–157. So the wheel is stock bytes at every draw, from the first. The recorded read compared two edited
casts (bold vs thin wheel), never stock. `rx_gates.py` prints that case on every run and does not score
it. Appearance matches where it was checked: **ef446's cyan `0x7FE0` bands
come out as hatched salmon/orange** (the 8bpp two-tone read the owner described), and **the dome bands are
clean bright yellow, first reaching the screen on f235**, the scroll blit's first frame. ef251's depth
signature (the owner's 4-cycle stripe) was not assessed. The Shiva U1 cast is reported, not gated (its own
verdict says U1 is not answered): the port has the marks sampled (x640_y256's visible fragments −21%) but
reaching the screen only as speckle on saturated ice (≤ 8.6% of pixels, f214–277), never as bands.

### Findings

- ★ **THE 15bpp GHOST LAYER, EXPLAINED.** Memoria never reads a 15bpp page at x ≥ 384 from VRAM once the
  cast has drawn into its `DR_AREA` render target (`PSXTextureMgr.isCreateGenTexture`, never reset during a
  cast): every such page samples the 512×256 target (VRAM x 384–895, y 256–511) instead, and a 15bpp page
  below x 384 is always the BLUR texture (the previous frame's screen). The target holds what the program
  *rendered* into it with indexed primitives. So a 15bpp repaint at x ≥ 384 in a target-using effect can
  never reach the screen (ef429's three covers), and the "15bpp" surface shows its indexed source instead
  (ef446's salmon, ef251's indexed read). **`routes` over all 372 containers (0 errors):** 66 render into
  the target; of the 181 (effect, page) pairs read at 15bpp, 70 read the target, 88 the blur texture, 13 the
  battle-ground capture, and only 10 VRAM. Of those 10, three are Memoria's hard-coded screenshot
  effects the port does not model (Slow, Devour, Silent Voice) and one is a reserved depth-3 page; the
  real ones are **Stop's (448,256)** and **Carbuncle's (576,256) in all four gem variants (ef177 / ef493–495),
  frames 181–211**, read from VRAM before ef177 first renders into the target at f265. Those are the only
  places a 15bpp repaint can reach the screen as painted. **Folded into the kit** (`render_target.py`,
  `tier-w/render_target_gates.py` R1–R6): every one of the 22 default-surface `direct15` cells reads
  NEVER_VRAM, and a build refuses an edit there by name, saying whether the cell's own bytes reach the
  screen another way (the target's draw reading them at 4/8 bpp, as indices: 8 of the 22) and
  naming the cells that draw the target. The falsifier: `routes --control` runs ef429 with
  `isCreateGenTexture` held down, and the same 58 reads (f53–110) come back from VRAM. One caveat the port
  cannot see: at Battle Speed ≥ 3 Memoria pre-records the cast (`SFXData.LoadSFXRawLoop`) and sets the
  flag after every frame (`SFXData.cs:403`), so there Carbuncle's VRAM reads go to the target too.
- ★ **THE REFRESH LAW: a VRAM copy can run every frame and never reach the screen.** Memoria refreshes a
  decoded page only for a write whose origin is in its own column, so a copy into an 8bpp page's second
  column changes VRAM and leaves the decode as it was. `run(track=True)` stamps every write and decode
  and charges each read of a texel written after its decode; `stale_census.py` ran it over all 372
  containers (0 errors). Of the 115 op-144 rect pairs: **103 read fresh, 9 MIXED** (refreshed once,
  then frozen, or stale on some readers), **3 READ_STALE** (ef131/ef250 (704,384), ef499 (512,256)) --
  every bad one a band in a page's later column. No LoadImage/MoveImage write is ever read stale. The
  falsifier: ef407 with column 640's ClearKey suppressed reads (704,384) stale. And the inversion: ef499's
  `x512_y256`, which the kit refused as a destination, repainted offline with the key, shows on 23 frames
  (up to 25,347 px) -- the stale decode keeps it. The kit now carries the table
  (`scroll_blit.REFRESH`, gate S8) and says so in its refusal and disclosures. The 8 pairs of the
  program's own scroll (next bullet) all read fresh (`--rejoin`: 111 / 9 / 3 of 123).
- ★ **THE OPEN GAP, CLOSED: the program's own scroll.** The census saw the plugin copy into four editable
  cells no op-144 site names (ef226 / ef509 `x448_y384` + `x512_y384`, the top 64 lines rewritten from
  their own bottom 64), so the kit licensed them. Six containers carry one routine of their own that takes
  op 144's arguments and issues the two copies itself through HLE op 7 -- a HORIZONTAL scroll (tier-r
  `CALLBACK-OPS.md` addendum 11). Its 11 call sites are now kit table rows, and both cells refuse. `routes`
  now records every executed copy, and over all 63 containers that copy, **the executed destinations
  equal the table's bands halfword for halfword** (gate S7). So do the sources, once 8 op-144 bands are
  read for what they are: FLIPBOOKS that scroll a different band-sized tile on different frames (ef429's
  16 tiles over (576..703, 256..511), its fold `(1,1)`). Each copy is attributed to the band whose scroll
  shape it has; 115 bands read exactly their fold and the 8 flipbooks' 107 tiles are kit data
  (`scroll_blit.TILES`), so remedies there name the tiles' cells.
- ★ **AN EDIT PRE-RUN: ef407's gained cell reaches the screen and scrolls**
  (`tier-w/ef407_gain_prerun.py`). Bars painted into `x704_y256`, a cell the U2 adoption licenses with no
  bound reader, change 110 of 146 frames (f75–192); 99.9 % of the changed pixels come through the op-144
  copy at (704,384), and on the ice spire (a footprint that holds still) they climb about 2 px a frame.
  The copy is visible only because a SECOND roll writes column 640: the readers' 8bpp decode is keyed at
  x640, and a write whose origin is in column 704 alone would leave it stale. **Cast-confirmed**: with
  the mark made legible (zebra bands; the first bars were measurable but invisible to the eye) the owner
  saw the bands, and the archived log runs 19 frames ahead of headless, where all 121 frames' DR_MOVEs
  match move for move (`calibrate --offset 19`; `tier-w/PLAN.md`, owner item 1).
- **The binding census over-counts drawable cells, and the reason is now mechanical:** a cell can be bound
  and uploaded yet unreachable because a blit overwrites it before any read ((704,256) on Phoenix), or
  because its depth routes to the render target (the 15bpp class).
- **Memoria's renderer is not a PSX GPU, and the differences matter to a painter.** `abr` 0 (average)
  renders as B + 0.5F; an effect's colour strength comes from `SFX.playParam` (C1 effects draw modulated
  texels at half the PSX brightness); a decoded texture is refreshed only when a VRAM write's *origin* lies
  in its own 64×256 page, so a write into the second column of an 8bpp page, or a CLUT upload, leaves the
  old decode on screen; at most 50 textures per cast and 64 meshes per frame, beyond which Memoria throws.
- **OPEN, a host finding: the opening diverges.** Every headless cast opens with a caster-side particle
  burst (G4 + sprites, ~f5–44) and opening camera installs that no in-game capture contains (Bahamut,
  Odin, Goblin Punch). Ruled out: the request flags, the SFXRework set-up/catch-up drive, a real battle
  camera (raw17 plunge), start type, camera index, auto/fixed camera, actor placement, the caster's
  slot/serial, and state left by an earlier cast. Bahamut's timeline from f58 is unaffected (RX1/RX2 run
  there); **Odin's in-game timeline runs ~19 frames ahead of the headless one**, so a frame number from a
  headless run is not a cast frame until it has been aligned against a capture.

### Limits

No 3D battle scene (the screen starts black and SFX depth-tests against nothing), no battle-ground capture
(`BACKGROUND` textures render transparent), the screenshot effects (Slow, Silent Voice, Devour, Detect,
Necron's death) are not ported, no widescreen, no `.seq` prevented/recoloured meshes, one render per SFX
frame, and the blur texture is the previous *headless* frame. Rasterisation follows D3D9 (pixel centres,
top-left fill rule, an 8-bit backbuffer) but is not a bit-exact GPU.

## Limits

- **`sfx_host.py` emits primitives, not pixels.** "Sampled" means a primitive the plugin emitted reads that
  VRAM cell; `on_screen` means its screen box meets the 320×240 PSX framebuffer. Neither proves a visible
  pixel: `raster.py` (above) is the step that does, with its own limits.
- **The actors stand at the origin.** Bahamut's camera is position-independent (a `FixedCameraEffects`
  member), but an effect anchored to units will emit at different screen positions than in a real
  battle. Timing matched on the one calibrated cast; positions are not calibrated.
- **No battle camera, no `.seq` layer.** Before an effect's camera takes over (Bahamut: before f58), the
  game shows the battle camera; this host shows the plugin's idle state. Under SFXRework the outer text
  sequence owns sounds, fades and damage. The host logs what the *program* asked for, not what Unity did.
- **Random state.** Runs are deterministic from a fresh process. The game's generator state at cast time
  is not, so `rand()`-driven motion (shakes, particle jitter) differs from any given cast.
- **x64 only.** The x86 plugin is a different file (sha `8635255d…`) and needs a 32-bit Python. It is
  unpinned.
- **One calibrated container.** HX1/HX1b calibrate Bahamut. Other containers are trusted because they run
  the same plugin through the same host, not because each one has been compared with a cast.

## Provenance

The plugin is the user's own DLL. It is copied from their install into `<SCRATCH>\headless-bin\<sha12>\`
and loaded in a throwaway process: never committed, never redistributed, never patched. Containers come
from the user's install or the local SCRATCH extraction. Everything a run derives from a stock
container (per-frame tables, the census, run JSON) is written under SCRATCH only, and `_refuse_repo_path`
refuses an output path inside the repository. The committed files are the host, the gates and the
tests: code plus counts, with zero Square Enix bytes.

## What it unlocks next

- **An empirical edit surface for `summon-reskin`.** The census's sampled cells and executed blit
  destinations give Tier W's static depth attribution (channels P/G/H/A, `linear-add-v1`,
  `ORDER_UNMEASURED`) a measured counterpart for all 372 containers. Diff the two before trusting
  either.
- **Offline verification for every in-place edit.** Run the edited container and diff its primitive
  stream, camera and slot against stock (HX4 is the pattern).
- **A real lint for native containers.** The native-slot lane was deferred behind an unrecoverable hang;
  here a hang is just a timeout.
- **HLE op tracing.** Hook the interpreter's dispatch inside this process to log every op call per frame.
- **A draw-side depth for the target's feeders.** The guard names the cells that draw the target, but 20
  of the 22 refusals name none the author can paint: the kit's static derivation refuses most feeders
  (depth-unknown, displaced). `routes` measures the depth each feeder is DRAWN at
  (`render_target_cells`), which is the evidence a new channel would need.
- **The opening divergence.** Find what the game gives the plugin that suppresses the caster burst; until
  then, align a headless frame against a capture before quoting it as a cast frame.

## Files

| File | |
|---|---|
| `sfx_host.py` | the host, the child-process runner, the census, the CLI |
| `hx_gates.py` | the calibration gates HX0–HX6 |
| `test_sfx_host.py` | 23 tests; one is install-gated and says why it skips |
| `raster.py` | the managed-renderer port: run / diff / routes / calibrate |
| `rx_gates.py` | the calibration gates RX0–RX4 |
| `stale_census.py` | the refresh census: every copy joined to the reads that see it, with its falsifier |
| `test_raster.py` | 29 tests on synthetic primitives and the gate scoring; one is install-gated |
