# Headless effect host

Runs `FF9SpecialEffectPlugin.dll`, the native battle-effect engine, **outside the game** in a plain
Python process. You give it a container (`ef###`), and it steps the plugin's own clock until the effect
ends itself. It reports what the plugin did: every primitive it emitted, the camera on every frame, the
summon slot, VRAM uploads/readbacks/blits, sound cues and damage points. It does this deterministically,
in seconds, with no game window and no owner cast.

Everything Tiers R and W learned by reading the DLL, or by arming an in-game probe and asking the owner
to cast, this host can answer by *running* the plugin. It's an oracle for the native layer. It's not a
renderer: primitives are data, not pixels.

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
  depth*) is not the plugin declining to draw them. If they never show in game, the loss is downstream,
  in Memoria's open-source managed renderer or in blending/transparent texels. **This is a lead, not a
  finding.** ef251 also emits a small 4bpp group on x512 (y256), which would fit the cast's indexed read.
- **ef094, ef154 and ef237 hold a live summon slot when run alone** (posed bones, sane node 0, 61/39/61
  frames), although they carry no creature package. R1 read them as drawing a creature another effect
  registered. Run in isolation they set up a skeleton themselves; whether anything is drawn from it is
  not established.

## Limits

- **Primitives, not pixels.** Rasterising them is `SFXRender`/`PSXTextureMgr`'s job, which is open-source
  C#, but this host does not port it. "Sampled" means a primitive the plugin emitted reads that VRAM
  cell; `on_screen` means its screen box meets the 320×240 PSX framebuffer. Neither proves a visible
  pixel.
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
- **Pixels.** Port enough of `SFXRender` to rasterise a frame, and close the loop between "sampled" and
  "visible".

## Files

| File | |
|---|---|
| `sfx_host.py` | the host, the child-process runner, the census, the CLI |
| `hx_gates.py` | the calibration gates HX0–HX6 |
| `test_sfx_host.py` | 23 tests; one is install-gated and says why it skips |
