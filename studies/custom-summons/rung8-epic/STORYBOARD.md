# Rung 8 — THE COMPOSED EPIC: **NIMBRA**, the Mist-born eidolon

> **This document is the binding creative + technical contract for rung 8.** Every downstream build
> lane (creature, particles, audio, `.seq`, wiring, kit) implements what is written here; a deviation
> is a decision that belongs back in this file, not in a build script.
>
> Ladder position: `studies/custom-summons/PLAN.md` §5, rung **8 of 9** — the first genuinely
> **original** FF9 summon. Rungs 1-7 are ★ all in-game proven (2026-07-21); this rung composes their
> proven mechanisms into one cast and adds **zero new engine surfaces**.
>
> **Status: DESIGNED. Nothing built, nothing deployed, nothing committed. The live install was read
> only** (`Memoria.ini`, the stock `SpecialEffects/` folder listing, `Common/ChannelSummon.sfxmodel`).
>
> Written 2026-07-24. Engine citations are against the pinned fork
> `C:/gd/FFIX/Memoria/Assembly-CSharp` (Memoria `6b8bb2d5`); install citations against
> `C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX`.

---

## 0. The one-screen summary

| | |
|---|---|
| **Creature** | **NIMBRA** — an original Mist-born eidolon. A pale, mask-faced wraith with no legs, whose lower body frays into vapour. ~1400u tall, ONE merged mesh, 5 logical parts, ~2 100 verts, 14 bones, 3 clips (`emerge` / `drift` / `strike`). |
| **Ability** | `Nimbra` — minted on Iviv's **Spark** command, `targets = "AllEnemy"`, `vfx1 = vfx2 = 91`, **`type = 0`**, `element = ["Dark"]`, `power = 62`, `mp = 24`. |
| **Private effect id** | **91** (`Unused_91`, `SpecialEffect.cs:501`) — **NOT 84** (that is the live Thomas/M1b transplant bench). |
| **Bench field** | **30301** (`rung8.field.toml`, a superset of `rung3-fresh-id/rung3.field.toml`). |
| **Lane** | DLL-free: fresh `ef091/` folder + `FileList.txt` + `.sfxmodel` FBX manifest + 3 sprite `.sfxmodel` particle files + 3 minted `.anim` clips + a fully hand-authored `PlayerSequence.seq`. **No donor, no `LoadSFX` of any stock id, no `ef###.bytes`, no engine patch.** |
| **Camera** | **NONE — by proof, not by choice.** `PlayCamera` is a hard no-op on this install (§2). The cast is composed for the fixed default battle camera. |
| **Duration** | **~485 ticks ≈ 32.3 s** at the bench's `BattleTPS = 15`. One documented trim knob — P1's `Wait: Time=95` → `50` — brings it to ~29.3 s (§7 R2; the P3 trim that used to be documented here is retracted, §7.3). |
| **Provenance** | 100 % original. Mesh, rig, clips, texture, particles, audio, `.seq` — all authored. Zero Square-Enix bytes; the whole rung is committable, unlike rungs 2-5's donor-derived `.seq` edits. |

---

## 1. THE CREATURE

### 1.1 The name — 3 pitches, 1 pick

FF9's Mist is the Iifa Tree's exhaust: the refuse of unassimilated souls, vented into Gaia, thick in
the lowlands, breeding "Mist monsters" and madness. An eidolon born *of* that refuse — not summoned
*through* it — is the concept. FF9's eidolon roster is mythological (Shiva, Ifrit, Ramuh, Odin,
Leviathan, Bahamut, Fenrir, Phoenix) with two coined outliers (**Ark**, **Madeen**). An original
belongs in the coined-outlier register: short, pronounceable, mythic, unmistakably ours.

| # | Name | Roots | Read |
|---|---|---|---|
| 1 | **NIMBRA** | *nimbus* (raincloud) + *umbra* (shadow) | Cloud-bodied and shadowed. Sits beside "Madeen" tonally. 6 chars — comfortably inside FF9's ability-menu width (the bench's 14-char "Bahamut Cinema" already fits). |
| 2 | **SILTHE** | *silt* (what settles out) + *lithe/wraith* | The dregs of the Iifa vent, given a body. Slightly harder to read aloud. |
| 3 | **MOURNVEIL** | *mourn* + *veil* | Most literal, most English, least like the roster's coined names. 9 chars. |

> ### ▶ **FINAL: NIMBRA.**
> Every artefact keys on it: the ability name, the `[CastName]` battle title plate, the mint
> `GEO_MON_B0_M400`, the study filenames (`nimbra.seq`, `nimbra_manifest.sfxmodel`,
> `make_nimbra.py`, …), and this document. **Do not re-litigate downstream.**

### 1.2 Silhouette (the modeler's brief)

PSX-era readability is the whole discipline: the shape must be legible **as a black silhouette, at
15 fps, at 384×224-equivalent detail, against a black void, with no camera move to help it** (§2).
That means: one dominant read, one secondary read, nothing else.

```
            ___
           (   )        <- 1. THE MASK: a smooth pale oval PLATE, slightly concave,
          ( ,   )          floating a hand's width clear of the cowl. NO carved features
           \___/           except two shallow amber eye-hollows. The dominant read.
            | |
        ___/   \___     <- 2. THE COWL: a hunched, hollow shoulder yoke. Suggests a
       /___________\       body that isn't there. Reads as "cloaked" at silhouette.
      /      |      \
     /       |       \   <- 3. THE ARMS: long, thin, tapering to POINTS. No hands, no
    |        |        |     fingers. They hang; they do not gesture until the strike.
    |        |        |
     \       |       /
      \     ___     /    <- 4. THE CORE: a narrowing torso column. No waist, no hips.
       \   /   \   /
        \ /     \ /
         |       |       <- 5. THE VEIL: NO LEGS. The core frays into 4 tapering
        /|\     /|\         ribbons that hang and sway. The secondary read.
       / | \   / | \        Bottom ~15% never resolves — it just thins out.
      '  '  ` '  '  `
```

- **No gore, no viscera, no faces-in-agony.** Eerie is *absence* — a thing that is almost a person
  and has decided not to finish. The mask is featureless on purpose: the player's eye supplies what
  isn't there.
- **The one accent** is the two amber eye-hollows (§1.5). Nothing else in the palette is warm. It is
  the single "something is looking at you" beat and it must not be diluted by a second accent.
- **The veil never touches the ground.** NIMBRA floats. This is load-bearing: the arena floor is
  blacked out for most of the cast (§3), so a creature with feet would look like it was standing on
  nothing. A creature that ends in vapour reads correctly with or without a floor.

### 1.3 Proportions

Authored in the kit's model-struct space: **Y-DOWN, ground at y = 0, the crown at the most-negative
y, FF9 units, left-handed** (`ff9mapkit/examples/boletta/make_creature.py` header). Note the
inversion vs. the *staging* space, where **+Y is UP** (§1.7).

| Part | Extent (FF9 units) | Notes |
|---|---|---|
| **Total height** | **1400** | ≈ 2× the 500-800u battle-actor reference the brief gives. NIMBRA towers over the enemy line without leaving the fixed frame (§3 P2 stages it at Y ≈ +190 with a Scaling ramp). |
| Mask | 190 tall × 140 wide × 40 deep | Crown at y = −1400. |
| Cowl / shoulder span | 520 wide × 300 tall | Widest point. |
| Arm (each) | 620 long, 55 → 8 taper | Hang from y ≈ −1080 to y ≈ −480 at rest. |
| Core column | 340 tall, 210 → 90 taper | y = −1080 → −740. |
| Veil (4 ribbons) | 740 long, 90 → 6 taper | y = −740 → 0. **45 % of total height.** |

> **The absolute number is not load-bearing.** The `.sfxmodel` `Scaling` curve (§1.7) is the single
> in-game tuning knob for apparent size — a one-line manifest edit, recast-only, no re-export. Author
> to 1400 and tune with the curve.

### 1.4 Parts, budget, and the ONE-MESH rule

**Author as ONE merged mesh with 5 logical parts (submeshes) on ONE 256×256 atlas.** This is the
boletta lesson carried forward (`make_creature.py` header: *"ONE merged mesh — a tiny standalone
renderer can be one-shot disabled by the field's character-show pass"*), and it also keeps
`SFXDataMesh`'s per-`ModelSequence` `Key`/`HideMeshes` machinery (`SFXDataMesh.cs:820-830`) out of
play entirely, which is exactly what we want for a creature that is never partially hidden.

| # | Part | Verts | Tris |
|---|---|---|---|
| 1 | `mask` | 96 | 130 |
| 2 | `cowl` | 220 | 340 |
| 3 | `arms` (both, merged) | 520 | 800 |
| 4 | `core` | 300 | 460 |
| 5 | `veil` (4 ribbons) | 960 | 1 560 |
| | **Total** | **≈ 2 100** | **≈ 3 290** |

Budget: **≤ 6 parts, ≤ 7 000 verts** (the brief's discipline). We land at 5 / ~2 100 — comfortable
headroom for a veil refinement pass.

**Winding**: calibrate, do not assume — reuse `make_creature.py:calibrate_winding` verbatim (FF9's
cutout materials cull backfaces; an inside-out mesh is invisible in-game and *fine* in a
double-sided previewer). **Texture V**: v = 0 is the image BOTTOM (Unity convention) — the boletta
upside-down-face bug is the documented trap.

### 1.5 Palette

The Mist's own register — pale greys and greens — plus exactly one warm accent.

| Role | Hex | Where |
|---|---|---|
| Body base | `#8FA79B` | cowl, core, arms |
| Highlight | `#C7D6CE` | mask face, cowl crest, arm leading edges |
| Deep | `#3A4A46` | mask underside, cowl interior, veil roots |
| Veil gradient | `#8FA79B` → `#2E3A38` (tip) | the ribbons fade toward their tips, so the fray reads even before the dissolve |
| **ACCENT** | `#C8912E` (dull amber) | the two eye-hollows + a 4-px ring at the mask rim. **Nowhere else.** |

> **AUTHOR THE TEXTURE ~15 % DARKER THAN YOU WANT.** Rung 7's logged residual (b): *"an
> SFX-instantiated model keeps its FBX material state — no battle-actor lighting/tint pass"*
> (`rung7-creature/README.md`, Open risks). NIMBRA renders at full texture brightness against a black
> void with zero attenuation. A palette that looks right in a lit previewer will blow out in-game.

The atlas is painted procedurally by `make_nimbra.py` (PIL, the boletta idiom) — zero image assets
imported, zero SE bytes.

### 1.6 The rig — 14 bones

Authored at REST with identity rotations; the clips do all posing (`models/anim.py:new_clip`).

```
bone000  root / core base
 ├ bone001  spine
 │  └ bone002  chest
 │     ├ bone003  neck
 │     │  └ bone004  mask
 │     ├ bone005  shoulder L → bone007 forearm L → bone009 point L
 │     └ bone006  shoulder R → bone008 forearm R → bone010 point R
 └ bone011  veil A     ← the three driven ribbons; ribbon D weights to a
   bone012  veil B        bone000/bone011 blend so the fray never reads as rigid
   bone013  veil C
```

14 bones — inside the brief's 8-20 window, and small enough that a hand-authored clip stays legible.

> `new_clip` fills every **unkeyed** bone with a static rest-pose channel automatically
> (`models/anim.py:551-556`) — real FF9 clips key all bones, and an unkeyed neck accumulates the
> engine's head-focus offset into a spinning head. Do not fight this; key what you animate and let
> the fill do the rest.

### 1.7 The three clips

Authored at **30 fps** via `models/anim.py:new_clip`, written with `clip_to_anim_json`, deployed to
`StreamingAssets/Assets/Resources/Animations/6400/<key>.anim` (`models/anim.py:anim_disc_path:46-50`).

> **NO `3DModelAnimation` REGISTRATION IS NEEDED.** The SFX path resolves clips by literal path
> through `AssetManager.Load<AnimationClip>` (`SFXDataMesh.cs:795-797`), not through the
> DictionaryPatch animation table — the productized overlay lane says so explicitly
> (`summons/deploy.py:692-695`: *"the `.anim` clips … at `anim_disc_path` — NO `3DModelAnimation`
> line"*). Clips are therefore **recast-only**; only the `3DModel 6400 GEO_MON_B0_M400` line needs
> the one relaunch.

| Clip | Frames @30 fps | `Speed` | Tick footprint @TPS 15 | What it does |
|---|---|---|---|---|
| `emerge` | 90 (3.0 s) | **2** | **45** (3.0 s — authored speed) | Veil ribbons collapsed inward at the root and unfurling; neck bowed, mask rising to level; arms unfolding from crossed. Paired with the Scaling 0.15 → 1.0 ramp so the unfurl and the growth are the same gesture. |
| `drift` | 75 (2.5 s), **LOOPABLE** | **1** | **75** (5.0 s — deliberate half-speed) | Root Y ± 14u, one full sine cycle. Mask counter-rotates ± 5°. The four ribbons carry a phase-offset travelling wave. Arms trail one beat behind the core. Half-speed is the eerie choice: everything else in the frame moves at battle tempo, NIMBRA does not. |
| `strike` | 60 (2.0 s) | **2** | **30** (2.0 s) | Frames 0-24: a slow wind-back, arms drawing up and behind, mask tipping down. 24-36: a fast forward lunge of both arm-points, mask snapping level. 36-60: settle back to the drift rest pose. |

#### THE PLAYLIST-SEAM RULE (new, derived from source)

`SFXDataMesh.cs:845-869` chains the `Animations[]` entries **with no blending** — it computes which
clip index the current frame falls in and hard-sets `clipState.time`. There is no cross-fade and no
loop flag (THE ANIMATION-PLAYLIST LAW, rung 7).

> **Every clip's first frame and last frame MUST be the shared `drift` rest pose.** Otherwise every
> playlist seam is a visible pop. This is an authoring constraint on all three clips, not a runtime
> setting.

#### The `Speed` compensation (new, derived from source)

`animMaxFrame[i] = ceil(geoAnimGetNumFrames(...) / speed)` and `animFrame = floor((frame -
startFrame - frameCounter) * speed)` (`SFXDataMesh.cs:849-861`). One **sequence tick** advances one
**clip frame ÷ Speed**. At `BattleTPS = 15`, a 30 fps clip therefore plays at **half speed with
`Speed = 1`** — that is rung 7's logged "15 fps tick sampling" residual, stated as an equation.

> **`Speed = 2` restores authored tempo. `Speed = 1` is a deliberate half-speed choice.** We use
> `Speed = 2` for `emerge` and `strike` (they must feel intentional) and `Speed = 1` for `drift` (it
> must feel wrong).

---

## 2. THE CAMERA VERDICT — pinned from source **before** choreographing

The brief requires pinning `PlayCamera`'s real capability before designing around it. Pinned. The
answer changes the storyboard, so it comes first.

### 2.1 `PlayCamera` is a **hard no-op on this install**

```csharp
case "PlayCamera":
    if (cancel) break;
    if (Configuration.Battle.Speed >= 3
        && FF9StateSystem.Battle.FF9Battle.btl_phase == FF9StateBattleSystem.PHASE_NORMAL)
        break;                                    // ← UnifiedBattleSequencer.cs:828-829
```

- The live `Memoria.ini` has **`[Battle] Speed = 5`** (read-only check, 2026-07-24).
- An ordinary fight runs in `PHASE_NORMAL` — `battle.cs:108` enters it, `:129-130` dispatches
  `BattleMainLoop` there, and commands execute inside that loop.
- ⇒ **`5 >= 3 && PHASE_NORMAL` ⇒ `break`. The op does nothing at all.**

There is no way to author around this from data: `Speed` is the user's own play-style setting, and
`SFXRework` (which our whole lane needs) is *forced on* at `Speed >= 3` — the exact configuration
that kills `PlayCamera`.

### 2.2 …and even when it *does* run, it is not a camera we can use

| Form | What actually happens | Verdict |
|---|---|---|
| `PlayCamera: Camera=N` (no `Char=`) | Writes `btlseq.instance.seq_work_set.CameraNo = N` and nothing else (`UnifiedBattleSequencer.cs:851-853`). The **only** readers of `CameraNo` are the native plugin's callback code 124 (`SFX.cs:953`, `SFXData.cs:723`, `:1182`, all commented *"Return the current battle camera index"*) and the battle-start seed (`HonoluluBattleMain.cs:161-162`). **No managed code moves a camera in response.** | **Invisible.** A data write nobody reads on our path. |
| `PlayCamera: Camera=N ; Char=…` | Calls `SFX.SetCameraTarget` (`SFX.cs:1989-1995`) and `SFX.SetEnemyCamera` (`:2029-2049`). Both set `SFXDataCamera.currentCameraEngine = SFX_PLUGIN` **and push data into the native `FF9SpecialEffectPlugin.dll`** — for an effect id with **no native `ef###.bytes` payload to drive it**. | **Refused.** Untested native interaction, zero upside, exactly the variable rung 7 deliberately excluded via `UseCamera=False`. |

Note also `HonoluluBattleMain.cs:162`: the game itself clamps the battle-start camera to slots 0-2
(`cameraNo >= 3 ? Random.Range(0,3) : cameraNo`) — the "attack-sequence slots 3-8" the PLAN §3.5
hoped for are not addressed by anything on the player path.

### 2.3 `ShiftWorld` is **rejected** as a camera substitute

`UnifiedBattleSequencer.cs:1044-1055`: `OnlyOnCameraMovement` defaults **true**, and with
`currentCameraEngine == NONE` (our case) the op `break`s. It *can* be forced with
`OnlyOnCameraMovement=False`. Do not:

1. `battlebg.ShiftWorld` (`battlebg.cs:407-432`) moves **only `battlebg.btlRoot`**, whose sole
   children are the arena mesh and the objanim models (`:22`, `:40`). The battle **actors are not
   parented to it** — the re-parenting code is commented out (`:411-424`). So it slides the *scenery*
   out from under the characters. That is not a camera move; it is a continuity error.
2. There is **no automatic restore**. `UnshiftWorld` (`:455-462`) guards on `nf_BbgOffset` /
   `nf_BbgAngle`, which `ShiftWorld` no longer writes (`:433-436`, commented out) — and it has
   **zero callers** anywhere in the tree. A shift would persist for the rest of the battle unless we
   shifted back ourselves.

### 2.4 ⇒ THE HONEST CAMERA ANSWER

> **NIMBRA is composed for the fixed default battle camera. There are no cuts, no dollies, and no
> world shifts.** Scale and dread are carried by four levers that *are* available and *are* proven:
>
> 1. **The blackout** (`SetBackgroundIntensity: Intensity=0`) removes every size reference in the
>    frame — the arena, the floor, the horizon. A creature against a void has no measurable size, so
>    it reads as whatever the composition says it is.
> 2. **Entering from below the frame and rising** (`Movement` curve, §3 P2) — the eye reads a rising
>    entrance as "something bigger than the shot."
> 3. **Scaling 0.15 → 1.0** over the emergence — an approach, without moving the camera.
> 4. **The particle pall** establishes a ground plane in the void, so the rise has something to rise
>    *out of*.

### 2.5 The `SetBackgroundIntensity` corollary

Two facts, both in-game proven, and they are compatible:

- **THE INTENSITY SUBTLETY LAW** (rung 6 ★): a *static* mid value (`Intensity=0.5`) only nudges the
  BG materials' `_Intensity` float and is imperceptible; `Intensity=0` **exactly** takes the
  `renderer.enabled = false` branch (`battlebg.cs:479-481`) — the vanilla blackout.
- **Rung 2 ★** ("*the fade was slower*"): lengthening the donor's blackout ramp from `Time=12` to
  `Time=45` was plainly perceptible. What the player perceives is *when the black arrives*, not the
  intermediate greys.

> **Design rule: only 0 and 1 are legible destinations, and the ramp `Time` is the expressive knob.**
> A long ramp to 0 = slow dread. A short ramp to 1 = a snap of light. **Never hold a mid value** —
> §2.1 killed the `PlayCamera` pairing that the rung-6 law offered as the rescue for mid-dims.
>
> `HoldDuration` (`UnifiedBattleSequencer.cs:1036`, `SequenceBBGIntensity:1633-1634`) is available
> for a self-restoring dim. We do not use it: our relight must land on an exact tick (§3 P4), so it
> is authored explicitly.

---

## 3. THE CHOREOGRAPHY

**Clock**: `BattleTPS = 15` (live `Memoria.ini [Graphics]`) ⇒ **1 tick = 1/15 s**. `Wait: Time=N`
counts ticks (`BattleActionThread.cs:98-116`).

**Two clocks run, and they must stay locked.** The `.seq` clock starts at cast; the creature's
**manifest clock** starts at `PlaySFX` and drives its own `Movement`/`Rotation`/`Scaling`/`Animations`
by *frame index* (`SFXDataMesh.cs:834-869`).

> ### THE PHASE-LOCK RULE (new)
> **After `PlaySFX`, the sequence uses fixed `Wait: Time=N` only — never a clip-bound
> `WaitAnimation`/`WaitMove`/`WaitTurn`.** A clip-bound wait has a length nobody measured
> (rung 6 logged exactly this as an open risk), and any slack it introduces after `PlaySFX` slides
> the strike beat relative to the creature's own `strike` clip. The one clip-bound wait we keep sits
> *before* `PlaySFX`, where slack shifts everything uniformly and costs nothing.

### 3.1 The tick table

| Phase | Ticks | Sec | On screen | Exact `.seq` ops |
|---|---|---|---|---|
| **P0 — THE HUSH** | 0 → 55 | 3.7 | Title plate "NIMBRA". Iviv bows into the chant. The **summon** aura kindles (not the Spell aura — see below). A low drone starts *under* the music. The arena begins its slow slide to black. A thin pale haze settles at everyone's feet. | `WaitAnimation: Char=Caster`<br>`Message: Text=[CastName] ; Priority=1 ; Title=True ; Reflect=True`<br>`SetupReflect: Delay=SFXLoaded`<br>`LoadSFX: SFX=91 ; Char=Caster ; Reflect=True ; UseCamera=False`<br>`PlayAnimation: Char=Caster ; Anim=MP_IDLE_TO_CHANT`<br>`WaitAnimation: Char=Caster`  ← the ONLY clip-bound wait<br>`PlayAnimation: Char=Caster ; Anim=MP_CHANT ; Loop=True`<br>`Channel: Type=Summon`<br>`PlaySound: Sound=100001 ; SoundType=SoundEffect ; Volume=0.55`<br>`SetBackgroundIntensity: Intensity=0 ; Time=45`<br>`CreateVisualEffect: Char=Everyone ; SFXModel=Data/SpecialEffects/ef091/MistFloor.sfxmodel`<br>`Wait: Time=45` |
| **P1 — THE MIST GATHERS** | 55 → 150 | 6.3 | Full black. Only the chanting caster, the pale pall crawling at floor level, and slow wisps peeling upward off it, each on its own orbit. A whisper swell rises and does not resolve. **Nothing else happens for six seconds** — this is the dread beat, and it must be allowed to be boring. | `CreateVisualEffect: Char=Everyone ; SFXModel=Data/SpecialEffects/ef091/MistWisps.sfxmodel`<br>`PlaySound: Sound=100002 ; SoundType=SoundEffect ; Volume=0.5`<br>`Wait: Time=95` |
| **P2 — THE COALESCE** | 150 → 255 | 7.0 | **NIMBRA.** It rises out of the mist over the enemy line, from below the frame, growing from a smudge to full height as the veil unfurls and the mask lifts to level. Frame 0 of the manifest clock. | `WaitSFXLoaded: SFX=91 ; Reflect=True`  ← resolves same-tick<br>`PlaySFX: SFX=91 ; Reflect=True ; SkipSequence=True`<br>`Wait: Time=105` |
| **P3 — THE DRIFT** | 255 → 345 | 6.0 | The aura dies. Iviv commits the cast gesture. NIMBRA simply **hangs there**, swaying at half speed, ribbons rippling, mask slowly turning. It has not attacked. It is looking. | `StopChannel`<br>`PlayAnimation: Char=Caster ; Anim=MP_MAGIC`<br>`Wait: Time=90`  ← fixed, per THE PHASE-LOCK RULE |
| **P4 — THE STRIKE** | 345 → 405 | 4.0 | The arms draw back; the mask tips down; both points drive forward. A pale rift-flash blooms on every enemy **and the world snaps back to light on the same tick** — the light returning *is* the impact. Damage lands; the numbers pop, fully lit. | `PlaySound: Sound=100003 ; SoundType=SoundEffect ; Volume=0.7`<br>`CreateVisualEffect: Char=AllTargets ; SFXModel=Data/SpecialEffects/ef091/RiftFlash.sfxmodel`<br>`SetBackgroundIntensity: Intensity=1 ; Time=18`<br>`Wait: Time=30`  (18 relight + 12 settle)<br>`EffectPoint: Char=AllTargets ; Type=Effect`<br>`Wait: Time=12`<br>`EffectPoint: Char=Everyone ; Type=Figure`<br>`Wait: Time=18` |
| **P5 — THE DISSOLVE + RELEASE** | 405 → 485 | 5.3 | NIMBRA holds one more slow drift beat in the restored light — the one moment you see it against the real arena — then thins: the body narrows to nothing while stretching upward, wisps peel off it, and it is gone. Iviv releases. | `WaitSFXDone: SFX=91 ; Reflect=True`  ← resolves at t = 480<br>`CreateVisualEffect: Char=Everyone ; SFXModel=Data/SpecialEffects/ef091/MistWisps.sfxmodel`<br>`StopSound: Sound=100001 ; SoundType=SoundEffect`<br>`ActivateReflect`<br>`WaitReflect`<br>`PlayAnimation: Char=Caster ; Anim=Idle`  ← THE ANIM=IDLE RELEASE LAW<br>`Turn: Char=Caster ; BaseAngle=Default ; Time=5`<br>`WaitTurn: Char=Caster` |

**Total: ≈ 485 ticks ≈ 32.3 s.** The fixed `Wait`s sum to 395; the two clip-bound waits in P0
(`MP_IDLE_TO_CHANT` and its `WaitAnimation`) are budgeted at ~10 ticks and are the **only**
uncertainty in the whole cast — call it ±10 ticks (±0.7 s). Because both sit *before* `PlaySFX`, that
slack shifts everything uniformly and never touches the two-clock alignment (§3.2).

### 3.2 The manifest clock, aligned

`PlaySFX` fires at **t = 150** ⇒ manifest frame 0 = t 150. The FBX entry pins `Start=0`, **`End=330`**
⇒ the creature renders t 150 → 480, and `WaitSFXDone` (issued at t = 405) resolves at **t = 480**.

| Playlist entry | `Speed` | Manifest frames | Sequence ticks | Beat |
|---|---|---|---|---|
| `emerge` | 2 | 0 → 45 | 150 → 195 | the rise |
| `drift` | 1 | 45 → 120 | 195 → 270 | hang |
| `drift` | 1 | 120 → 195 | 270 → 345 | hang |
| `strike` | 2 | 195 → 225 | **345 → 375** | the lunge lands ≈ t 357; `EffectPoint` at t 375 catches the follow-through |
| `drift` | 1 | 225 → 300 | 375 → 450 | the hold in restored light |
| `drift` | 1 | 300 → **330 (cut)** | 450 → 480 | dissolving under the Scaling curve |

Playlist total = 375 ticks ≥ the 330-tick window ⇒ **the playlist is never exhausted, so it never
freezes on a last frame** (THE ANIMATION-PLAYLIST LAW's failure mode, avoided by construction).

### 3.3 The staging curves (the `.sfxmodel` FBX entry)

#### THE MULTI-TARGET NULL (new, and it would have broken the cast)

`SFXData.PlaySFX` calls
`mesh.SetupPositions(sfxRequest.exe, sfxRequest.trgno == 1 ? sfxRequest.trg[0] : null, trgcpos)`
(`SFXData.cs:149`). With `targets = "AllEnemy"` and more than one enemy, `trgno > 1` ⇒ **`target` is
`null`** ⇒ every `TargetPosition{X,Y,Z}` evaluates to **0** (`ParametricMovement.cs:176-178`) ⇒ a
creature staged on `TargetPosition*` would render **at the world origin**, off-camera — rung 7's
MOVEMENT TRAP by a second route.

> **An `AllEnemy` cast MUST anchor on `TargetAveragePosition{X,Y,Z}`**, which is
> `BTL_VFX_REQ.trgcpos` — the mean of the targets' `base_pos` X and Z, with
> **`vy` hard-set to 0** (`BTL_VFX_REQ.cs:72-92`). So the enemy-line centre is always valid, and the
> **Y anchor is an absolute ground-plane constant**, not a relative height.

#### THE AVERAGE-POSITION SPLIT (new gotcha, document it in the linter)

The same NCalc name means two different things depending on how the `.sfxmodel` was spawned:

| Spawn route | `CasterPosition*` | `TargetPosition*` | `TargetAveragePosition*` |
|---|---|---|---|
| `LoadSFX`/`PlaySFX` (our creature) | the `Char=` unit | **only if exactly ONE target**, else 0 | the real target-average (`trgcpos`), Y = 0 |
| `CreateVisualEffect` (our particles) | always `cmd.regist` | the per-instance `Char=` unit — **always valid** | **the literal `Offset=` argument** (`UnifiedBattleSequencer.cs:445` → `SFXChannel.cs:18`) |

#### +Y is UP (confirmed by stock content)

`Common/ChannelSummon.sfxmodel` — the shipping summon aura — rises via
`"DestinationY": "CasterPositionY + Parameter1 * 800"` with `Parameter1 ∈ [0.2, 1.0]`. Rung 5's own
proven ring (`"CasterPositionY + 300"`, *"rises"*) agrees.

#### The curves

`ParametricMovement.LoadFromJSON` (`ParametricMovement.cs:58-136`) accepts a **JSON array of pieces**;
each piece takes `Duration`, `Origin{X,Y,Z}`, `Destination{X,Y,Z}`, `InterpolationType{X,Y,Z}`, and an
**omitted `Origin*` inherits the previous piece's `Destination*`** (`:88-89`, `:96-97`, `:104-105`).
Interpolations: `Constant | Linear | Sinus | SinusIn | SinusOut | Turning1 | Turning2` (`:262-271`).

Let `A* = TargetAveragePosition*`.

| Curve | Piece | Dur | From → To | Ease |
|---|---|---|---|---|
| **Movement** | 1 | 45 | `(Ax, -900, Az)` → `(Ax, 120, Az)` | X `Linear`, **Y `SinusOut`**, Z `Linear` |
| | 2 | 285 | → `(Ax, 190, Az)` | Y `Sinus` — a barely-there continued lift through the whole hang |
| **Rotation** | 1 | 45 | `(0, 180, 180)` → `(0, 180, 180)` | `Constant` |
| | 2 | 180 | → `(0, 168, 180)` | Y `Sinus` — a 12° slow turn during the drift |
| | 3 | 105 | → `(0, 180, 180)` | Y `SinusOut` — squares up for the strike, then holds |
| **Scaling** | 1 | 45 | `0.15` → `1.00` (uniform) | `SinusOut` |
| | 2 | 210 | → `1.00` | `Constant` |
| | 3 | 75 | → `(0.02, 1.70, 0.02)` | X/Z `SinusIn`, Y `SinusOut` — **the dissolve**: the body thins to a thread while stretching upward = vapour venting |

`Rotation` is applied **raw to `eulerAngles`** with no battle-actor base rotation
(`SFXDataMesh.cs:844`) — THE ROTATION BASELINE LAW. We start from the proven `(0, 180, 180)`.

> **The yaw is the one knob that may cost a cast.** Rung 7 spent cast 2 and cast 3 on exactly this
> (Z=180 → upright-but-backwards → +Y=180 → clean). NIMBRA stands on the *enemy* side facing the
> party, the mirror of rung 7's caster-side staging. **If cast 1 shows NIMBRA facing away, flip every
> Rotation `Y` between 180 and 0** (and 168 → 12) — a one-line manifest edit, recast-only, no
> re-export, no relaunch.

---

## 4. THE PARTICLES — three original sprite models

All three are hand-authored `Sprite` `.sfxmodel` JSON in the rung-5 idiom (`rung5_sprite.sfxmodel`,
★ in-game proven): `"TextureKind": "0"` (no texture, no PNG) + `"Shader": "SFX_ADD_G"`. Zero SE bytes,
committable.

> **`SFX_SUB_G` was considered and rejected.** The subtractive shader exists (`SFXMesh.cs:981-982`
> lists all six `SFX_{OPA,ADD,SUB}_{G,GT}` names) and would be the "darkening pall" lever — but
> subtracting from a blacked-out background is a no-op, and the pall must read *during the blackout*.
> **Additive-over-black is the only thing that reads.** This also keeps every particle on rung 5's
> exact proven shader, adding zero new engine surface.

Common mechanics (all source-verified):

- **`Char=` is mandatory.** `TryGetArgCharacter` defaults `tmpChar = 0` before parsing
  (`BattleActionCode.cs:493-496`); a 0 bitmask renders on nobody, silently (rung 5 law).
- **One instance per matched unit.** `Char=Everyone` spawns the whole sprite JSON once per combatant
  (`UnifiedBattleSequencer.cs:419-446`) — that is how arena-wide coverage is achieved **with no
  hardcoded arena constants**.
- **`Time=`/`Size=`/`Speed=` are parsed but INERT** for `SFXModel` mode (rung 5 law) — all timing
  lives in the JSON.
- **Fire-and-forget, 0 ticks.** The op sets no wait; the effect self-terminates past its own
  `lastFrame` and removes itself (`SFXChannel.Render`).
- **THE TOTAL-LIFE FORMULA.** A sprite's `Duration` is each PARTICLE INSTANCE's own local clock,
  counted from ITS OWN spawn frame — not the whole effect's on-screen life. Every `Emission` entry
  spawns a fresh instance at its own frame, so the LAST instance is still fading out `Duration` ticks
  after the LAST emission frame fires. **Total on-screen life = last `Emission` frame + `Duration`, not
  `Duration` alone.** Only a single-emission sprite (frame `0` only) has `Duration` as its true total
  life; the per-file tables below (§4.1-4.3) state both numbers where they differ.
- **Particles are EXEMPT from the FIGURE-VISIBILITY LAW** — `Graphics.DrawMeshNow` is a different
  render path from the `Type=Figure` damage-number UI (rung 5, source-read).
- **The randomization idiom, decoded from stock**: per-emission `ParameterMin<K>` / `ParameterMax<K>`
  keys become `Parameter{K}` NCalc variables, randomized per particle
  (`SFXDataMesh.cs:1159-1185`, `Particle` ctor `:1382-1404`). And — undocumented anywhere —
  **`Parameter0` is consumed as the BASE ANGLE (degrees) of the `Turning1`/`Turning2` interpolations**
  (`ParametricMovement.cs:233-238`), which is exactly how `ChannelSummon` randomizes its orbit phase.
  `Turning1` = cos, `Turning2` = sin (`:296-297`) ⇒ **`Turning1` on X + `Turning2` on Z = a circular
  orbit**, per-particle phase-shifted by `Parameter0`.

### 4.1 `MistFloor.sfxmodel` — the ground pall

| | |
|---|---|
| Shape | 1 sprite: a flattened hexagon, 6 verts / 4 tris, **260 wide × 70 tall**. Wide and low — it must read as a layer, not a puff. |
| Colour | fades `(0,0,0,0.5)` → `(0.10, 0.16, 0.13, 0.5)` over frames 0-20 (`SinusOut`), holds, → `(0,0,0,0.5)` over 70-110 (`SinusIn`). Barely-there pale grey-green. |
| Motion | 1 piece, `Duration 110`. X: `TargetPositionX - 620*Parameter1` → `+620*Parameter1`, `Turning1`. Z: `TargetPositionZ - 240*Parameter1` → `+240*Parameter1`, `Turning2`. Y: `18 + Parameter2` → `52 + Parameter2`, `Linear`. |
| Emission | frames `0,8,16,…,88` (12 entries), `Count: 1`; `ParameterMin0=0 / Max0=360` (orbit phase), `ParameterMin1=0.35 / Max1=1.0` (radius), `ParameterMin2=-30 / Max2=30` (height jitter). |
| Duration | `110` ticks (≈ 7.3 s) per instance. **Total on-screen life = last emission (88) + Duration (110) = 198 ticks (≈ 13.2 s)** — spans P0's tail, all of P1, AND ~53 ticks into P2 (spawn at t ≈ 10 ⇒ the last particle fades out ≈ t 208, while NIMBRA is already rising). |
| Spawn | `Char=Everyone` at t ≈ 10. ~12 particles × ~6 units ≈ **72 billboards**. |

### 4.2 `MistWisps.sfxmodel` — the drifting wisps

| | |
|---|---|
| Shape | 1 sprite: a 4-vert / 2-tri elongated diamond, **26 wide × 150 tall**. Vertical, thin, ghostly. |
| Colour | `(0,0,0,0.5)` → `(0.34, 0.46, 0.40, 0.5)` frames 0-14 (`SinusOut`) → `(0,0,0,0.5)` frames 34-70 (`SinusIn`). |
| Motion | 1 piece, `Duration 70`. X: `TargetPositionX - 300*Parameter1` → `+300*Parameter1`, `Turning1`. Z: same ± 150, `Turning2`. Y: `Parameter2` → `Parameter2 + 520*Parameter1`, `SinusOut` — the rise decelerates. |
| Scale | `ScaleAnimation` `0.6 → 1.5`, `SinusOut`. |
| Emission | frames `0,5,10,…,75` (16 entries), `Count: 1`; `Parameter0 ∈ [0,360]`, `Parameter1 ∈ [0.3, 1.0]`, `Parameter2 ∈ [10, 140]`. |
| Duration | `70` ticks (≈ 4.7 s) per instance, self-terminating. **Total on-screen life = last emission (75) + Duration (70) = 145 ticks (≈ 9.7 s)**, not 70 — the emission spread outlives its own spawn window. |
| Spawn | `Char=Everyone`, **twice**: t = 55 (P1, the gathering) and t = 405 (P5, the dissolve). One file, two beats. At the P1 spawn the extra ~75 ticks are fine (P1/P2 are already busy); at the P5 spawn the last wisps fade out ≈ t 550, ~65 ticks AFTER the cast's own t 485 end — a short trail past the release, not a bug (`SEQUENCE-LANE.md` §7 observes the same number). |

### 4.3 `RiftFlash.sfxmodel` — the strike flash

| | |
|---|---|
| Shape | 2 sprites. **(a)** an 8-point star burst, 16 verts / 8 tris, radius 300. **(b)** a thin octagonal ring, 16 verts / 16 tris (the rung-5 annulus geometry reused), r_out 120 → the ring is scaled outward by its own curve. |
| Colour | (a) `(0,0,0,0.5)` → `(0.95, 1.0, 0.92, 0.5)` in **3 frames** (`SinusOut` — a snap, not a fade) → black by frame 22 (`SinusIn`). (b) the amber accent: → `(0.78, 0.57, 0.18, 0.5)` by frame 4, → black by frame 30. |
| Motion | both: `Duration 30`, static at `TargetPosition{X, Y+120, Z}` — anchored on the individual victim (`Char=AllTargets` ⇒ per-instance target is that enemy; **valid on this path**, unlike §3.3). |
| Scale | (a) `0.4 → 1.9` `SinusOut`. (b) `0.3 → 3.4` `SinusOut` (the expanding shock ring). |
| Emission | (a) `Frame: ["0"], Count: 1`. (b) `Frame: ["0","3"], Count: 1` (a doubled ring, 3 ticks apart). |
| Duration | `30` ticks (2.0 s) per instance. (a) is single-emission (frame 0 only), so its total on-screen life IS 30 ticks. (b) emits again at frame 3, so **its total life = last emission (3) + Duration (30) = 33 ticks (≈ 2.2 s)** — 3 ticks longer than (a), not a meaningful difference at this scale but the same formula as §4.1/§4.2. |
| Spawn | `Char=AllTargets` at t = 345, **the same tick as the relight** — the flash and the light returning are one event. |

**Perf watch:** peak concurrent billboards ≈ 72 (pall) + 96 (wisps) + ~9 (flash) ≈ **180**, each 4-16
verts, one `DrawMeshNow` per sprite per instance per frame (`SFXDataMesh.cs:895-910`). Unmeasured on
this install; if the cast stutters in P1, halve `MistFloor`'s emission entries first.

---

## 5. THE AUDIO PLAN

Three minted ids in the kit's `sfx` band (`sound.py:213` `MINT_ID_BASE = {"music": 1000, "sfx": 100000}`).
Precedent: rung 3 cast B ★ *"the chime played at the start"* — minted sfx **100000**, a synthetic
880 Hz sine, played from a hand-authored `PlaySound` line inside a summon sequence. 100000 stays
where it is (the rung-2/3 probe chime); NIMBRA takes **100001-100003**.

All three are **synthesized in Python** (`numpy` + stdlib `wave`, the `build_rung2.py:_tiny_chime_wav`
idiom) → WAV → `sound.encode_ogg` → `sound.mint_song(kind="sfx", new_id=…)`. **Zero SE bytes, zero
sampled material, fully committable** (the generator is the artefact; the `.ogg` is build output).

| Id | Resource | Length | Content | Fires |
|---|---|---|---|---|
| **100001** | `nimbra_drone` | **34.0 s** | The bed. Two detuned saw/sine partials at 55.0 Hz and 82.5 Hz (a bare fifth) with ±3 cent slow beating; a third partial at 110 Hz entering at 8 s; over it a band-passed pink-noise "breath" (300-900 Hz) amplitude-modulated at 0.13 Hz. 6 s fade-in, 4 s fade-out. **Peak ≤ 0.45.** | `PlaySound` t ≈ 10 (P0), `StopSound` t = 480 (P5). |
| **100002** | `nimbra_whispers` | **7.0 s** | The swell. Six overlapping band-passed noise bursts (1.2-3.5 kHz) with reversed envelopes (slow in, hard out), each hard-panned alternately L/R via the `Panning` arg's neighbours — plus a 220 Hz sine that rises a minor third and never resolves. **Peak ≤ 0.40.** | `PlaySound` t = 55 (P1). |
| **100003** | `nimbra_strike` | **2.5 s** | The sting. A 45 Hz sine thump with a 25 ms attack, plus an inharmonic metallic ring-out (partials at 1.0 / 2.76 / 5.40 / 8.93 × 640 Hz, exponential decay τ = 0.55 s) — a bell that is not a bell. **Peak ≤ 0.55.** | `PlaySound` t = 345 (P4), same tick as the flash and the relight. |

### 5.1 The peak budget is a hard constraint, not a preference

PLAN §8(b), from the crunchy-audio investigation: **there is no limiter or compressor anywhere in
the SaXAudio chain** (`AudioEffectManager` = Reverb/Eq/Echo/Volume only) — *any* voice stack on
`BusSoundEffect` hard-clips. At t = 345 we have the drone (still playing) + the strike sting + the
`Channel: Type=Summon` aura's own stock sounds + the engine's hit/damage SFX, all live at once.

> **Author each file to the stated peak AND pass a conservative `Volume=` on every `PlaySound`
> line** (0.55 / 0.50 / 0.70 in §3.1). Two independent attenuations. The live
> `PlaySound: … Volume=v ; Panning=p ; Pitch=q` path is `SoundLib.PlaySoundEffect(id, v, p, q)`
> (`UnifiedBattleSequencer.cs:908`); `SoundType` **defaults to `SoundEffect`** already
> (`BattleActionCode.cs:157-160`), so the bare form is safe — we write it explicitly anyway.

### 5.2 THE RELAUNCH LAW

`SoundMetaData`'s id table loads **once at process start**. Three brand-new ids ⇒ **one relaunch,
after minting and before the first cast** — the same relaunch that registers the
`3DModel 6400 GEO_MON_B0_M400` DictionaryPatch line (§6.3). One relaunch covers both.

> **Silence on cast 1 with everything else working = a missed relaunch, not a design failure.**
> Diagnose in that order. Whether *replacing the .ogg content* at an already-registered id needs
> another relaunch is **unproven** — assume yes until measured.

---

## 6. THE WIRING PLAN

### 6.1 The private effect id: **91**

The absent-id pool is 24 ids (`summons/deploy.py:74-77`; the folder listing of the live install is
487 present + `Common` = 488 entries, and `SpecialEffect.cs:496-519` hand-aliases exactly those 24 as
`Unused_N`). Verified read-only 2026-07-24: neither `ef080/`, `ef084/` nor `ef091/` exists in stock;
`FF9CustomMap/…/SpecialEffects/` contains **only `ef084`** (the live Thomas/M1b bench).

Three of the 24 carry the mildest documented legacy semantics — *"Would run casting animation & apply
effect"*: **80, 84, 91**. The other 21 are *"Would never end"* or *"Would rerun last effect used"*.

> **`private_ef = 91`.** 84 is occupied by the transplant bench and must stay bit-intact so both
> benches coexist on one install. 91 is the next mild id ascending. 80 stays reserved as the spare.
>
> Pin it explicitly in the block — do **not** let `alloc_private_ef` (`deploy.py:410-421`) choose,
> because it walks the pool ascending and would land on **18** (*"Would apply effect instantly"*).

### 6.2 The ability

Appended to Iviv's existing **Spark** pool (`[playable.abilities.command1].abilities`) in the bench
toml, **after** `"Bahamut Cinema"` so that entry keeps its allocated id 194 and the M1b transplant
bench's binding is untouched. The new row takes the next custom-ability id (**195**).

```toml
{ name = "Nimbra", from = "Bahamut", targets = "AllEnemy",
  vfx1 = 91, vfx2 = 91, type = 0,
  power = 62, element = ["Dark"], mp = 24 },
```

| Key | Why |
|---|---|
| `name = "Nimbra"` | The `Message: Text=[CastName]` title plate renders it (rung 6 ★). |
| `from = "Bahamut"` | Clones Actions.csv row 62 verbatim (`actiondelta.py`) — a valid AllEnemy magic-damage row with **`scriptId = 85`**. **85 ≠ 87**, so Odin's Sword SA is never triggered (PLAN §3.7). |
| `targets = "AllEnemy"` | **Load-bearing.** `btl_vfx.cs:99` plays the *short* `Vfx2` only when `(Target == ManyAny && cursor == 0)` or `short_summon` or a Beatrix-hardcoded pair. `AllEnemy(8)` is never `ManyAny`, and a minted `BattleCommandId 46` never enters `DecideSummonType` — so `vfx1` plays **structurally, on every cast** (the rung-1 law). |
| `vfx1 = 91` | Our folder. |
| **`vfx2 = 91`** | **A deliberate change from rungs 1/3**, which left `vfx2 = 405` (Bahamut Short) on the reasoning that it can never fire. For an *original* summon the reasoning inverts: the residual risk of ever showing a stock Eidolon is not worth carrying. Pointing both at 91 makes stock content structurally unreachable from this ability. Zero cost. |
| **`type = 0`** | **THE TYPE-4 MP LAW.** Stock Bahamut ships `type = 4`; `(Type & 4) != 0 && GARNET_SUMMON_FLAG != 0 ⇒ mpCost <<= 2` (`AbilityUI.cs:1310-1315` + the BattleHUD twin) — vanilla's early-game summon handicap. A scenario-zero New Game has the flag set, and the bench measured 56 → 224 MP in a playtest. Clearing it is mandatory. |
| `element = ["Dark"]` | Mist = soul-refuse. `Dark` = bit 128 (`itemstats.py:25-26`); FF9 has no Mist element. Note an enemy that resists/absorbs Dark will flip the result — thematically correct and fine for a bench. |
| `power = 62`, `mp = 24` | 62 < Bahamut's 88: an original, not a re-skin. 24 MP against Iviv's 80/80 boot pool = **3 casts per fight**, which is what iteration needs. |

**The block does not author the ability.** Per DESIGN §1.4 the `[[summon]]` block never edits
`Actions.csv`; the ability lives in the field toml's `[[playable]]` lane, exactly as on the current
bench.

### 6.3 The bench field: **30301**

`rung8-epic/rung8.field.toml` — a copy of `rung3-fresh-id/rung3.field.toml` with:

- `[field] id = 4814`, `name = "MISTBENCH"` (⇒ `FBG_N11_MISTBENCH` + `EVT_MISTBENCH.eb`, distinct from
  30300's `IVIVROOM`; `deploy_field --id 30301` re-slots it);
- the `"Nimbra"` ability appended to Spark's pool (§6.2);
- the `[[summon]]` block (§6.4);
- everything else — the two `[[playable]]` characters, `[encounter] scene = 67`, `[music]`, the
  `[[savepoint]]` — **unchanged**.

Deploy: `py tools/deploy_field.py studies/custom-summons/rung8-epic/rung8.field.toml --id 30301`.
30301 is free: the dev scratch band is 30000-32767, and 30300 (summons), 30400/30410-30413
(fort-condor / behavior), 30110-30200 (co-op) are the occupied neighbours.

> ⚠ **Deploy the rung-8 bench, not both.** Both tomls define the same two `[[playable]]` characters
> and therefore write the same global `Actions.csv` / `Commands.csv` / `CharacterParameters` rows. The
> rung-8 toml is a strict **superset** — it still casts "Bahamut Cinema" — so nothing is lost by
> letting 30301 own the CSV state. See §7 R11.

### 6.4 `[[summon]]` with `staging = "curves"` — THIS ROUND'S KIT WORK

Today `staging` is normalized and range-checked (`deploy.py:178-180`) and then **never read**. The
overlay lane is donor-shaped end to end: `donor` is REQUIRED (`content/summon.py:137-142`), the host
`.seq` is a **spliced copy of the donor's** (`deploy.py:_stage_host_seq` → `splice_host_seq:328-344`),
and `clips` are **decoded from the donor's `ef###.bytes`** (`_decode_donor_clips:634-664`). An
original summon has no donor at all. Five deltas close that.

| # | Delta | Where |
|---|---|---|
| **K1** | **`sequence = "<file>.seq"`** — a new key naming an authored `PlayerSequence.seq`, copied verbatim into `ef{private_ef}/`. When present, `donor` becomes **optional** and the whole donor read/splice/drift-guard path is skipped. | `content/summon.py` (schema + the `donor`-required rule), `deploy.py:_stage_host_seq` |
| **K2** | **`clips = [<paths>]`** — accept a list of authored clip files (the `models/anim.py:new_clip` → `clip_to_anim_json` output) alongside today's `"all" \| "none" \| indices` donor-decode. Written to `anim_disc_path(mod_root, id, key)`, no `3DModelAnimation` line (unchanged). | `deploy.py:_decode_donor_clips` → a `_resolve_clips` dispatcher |
| **K3** | **`particles = [<paths>]`** — sprite `.sfxmodel` files copied verbatim into `ef{private_ef}/`. Lint: every `SFXModel=` path referenced by the authored `.seq` must exist in this list (the silent-skip guard extended to file paths). | `deploy.py` (a new `_stage_particles`) |
| **K4** | **`staging = "curves"` CONSUMED** — an authored `[summon.staging]` table emits the `.sfxmodel` FBX entry's `Start`/`End`/`Movement`/`Rotation`/`Scaling`/`Animations` instead of today's inert world-origin stub (`_sfxmodel_manifest:616-631`). Schema below. | `deploy.py:_sfxmodel_manifest` |
| **K5** | **A minimal `.seq` linter** — the silent-skip guard (PLAN §7). | new `battle/seqlint.py` + a `summon-seq lint` CLI verb |

#### The `[summon.staging]` schema (designed to carry exactly §3.3, nothing more)

```toml
[[summon]]
lane       = "overlay"                 # DLL-free; works on stock Memoria
model      = "nimbra/6400.fbx"
id         = 6400
name       = "GEO_MON_B0_M400"
group      = "MON"
private_ef = 91
sequence   = "nimbra.seq"                                  # K1 -- no donor
clips      = ["nimbra/emerge.anim", "nimbra/drift.anim", "nimbra/strike.anim"]   # K2
particles  = ["MistFloor.sfxmodel", "MistWisps.sfxmodel", "RiftFlash.sfxmodel"]  # K3
staging    = "curves"                                      # K4

[summon.staging]
anchor = "target_average"     # caster | target_average  -> the NCalc origin preset.
                              #   NOTE: a bare `target` is REFUSED for a multi-target cast --
                              #   THE MULTI-TARGET NULL (SFXData.cs:149).
start  = 0
end    = 330                  # pinned, not auto-derived: the .seq's WaitSFXDone tick depends on it

[[summon.staging.move]]       # -> Movement pieces, in order; offsets are ADDED to the anchor
duration = 45
from = [0, -900, 0]
to   = [0,  120, 0]
ease = ["Linear", "SinusOut", "Linear"]
[[summon.staging.move]]
duration = 285                # `from` omitted -> inherits the previous `to`
to   = [0,  190, 0]
ease = ["Linear", "Sinus", "Linear"]

[[summon.staging.turn]]       # -> Rotation pieces (ABSOLUTE euler; THE ROTATION BASELINE LAW)
duration = 45
from = [0, 180, 180]
to   = [0, 180, 180]
[[summon.staging.turn]]
duration = 180
to   = [0, 168, 180]
ease = ["Constant", "Sinus", "Constant"]
[[summon.staging.turn]]
duration = 105
to   = [0, 180, 180]
ease = ["Constant", "SinusOut", "Constant"]

[[summon.staging.scale]]      # -> Scaling pieces
duration = 45
from = [0.15, 0.15, 0.15]
to   = [1.0, 1.0, 1.0]
ease = ["SinusOut", "SinusOut", "SinusOut"]
[[summon.staging.scale]]
duration = 210
to   = [1.0, 1.0, 1.0]
ease = ["Constant", "Constant", "Constant"]
[[summon.staging.scale]]
duration = 75
to   = [0.02, 1.70, 0.02]
ease = ["SinusIn", "SinusOut", "SinusIn"]

[[summon.staging.play]]       # -> the Animations[] playlist, in chain order
clip = "emerge" ; speed = 2
[[summon.staging.play]]
clip = "drift"  ; speed = 1 ; repeat = 2
[[summon.staging.play]]
clip = "strike" ; speed = 2
[[summon.staging.play]]
clip = "drift"  ; speed = 1 ; repeat = 2
```

**Emit rules (all pinned to source):**

- `anchor = "target_average"` ⇒ origin expressions `TargetAveragePositionX + <dx>` /
  `TargetAveragePositionY + <dy>` / `TargetAveragePositionZ + <dz>`; `anchor = "caster"` ⇒
  `CasterPosition*`. Since `trgcpos.vy` is hard-zero (`BTL_VFX_REQ.cs:88`), a `target_average` Y
  offset is an **absolute ground-plane height** — say so in the docstring.
- A piece with `from` omitted emits **no `Origin*` keys at all**, letting the engine's own
  `lastPiece.dest` inheritance do the chaining (`ParametricMovement.cs:88-105`). Do not helpfully
  re-emit the previous destination — the inheritance is by `Expression` reference and re-emitting
  would double-evaluate the NCalc.
- `ease` accepts only the seven enum names (`ParametricMovement.cs:262-271`); an unknown string
  **silently becomes `Constant`** (`TryParseInterpolateType:273-285`) — so **lint it, hard**.
- `repeat = N` expands to N identical `Animations[]` entries (THE ANIMATION-PLAYLIST LAW: there is
  no loop flag).
- `end` defaults to `0`, which makes the engine auto-derive from
  `max(animDuration, movement, rotation, scaling)` (`SFXDataMesh.cs:803-808`). **We pin it**, because
  the `.seq`'s `WaitSFXDone` beat is authored against it.
- **Lint**: `Σ move.duration == Σ turn.duration == Σ scale.duration == end - start`; every `play.clip`
  present in `clips`; `speed > 0`; `Σ (play ticks) ≥ end - start` (so the playlist never freezes).

#### K5 — the `.seq` linter (minimal, but it must exist)

Unknown operations are **dropped silently** — `if (!BattleActionCode.operationArguments.TryGetValue(opCode, out defaultArgList)) continue;`
(`BattleActionThread.cs:155-156`). A typo dies without a log. Scope for this round:

1. **Op whitelist** = the 44 keys of `BattleActionCode.operationArguments` (`BattleActionCode.cs:46-89`)
   **plus `EndThread`** (the parser pops the thread stack and then falls through the same `continue`,
   so it is legal-but-absent from the table).
2. **Arg-key whitelist, per op, derived from the EXECUTOR — not from `operationArguments`.** That
   table is *positional-argument names only* and is demonstrably out of sync with the executor in at
   least two places: `CreateVisualEffect` declares `Time`/`Size`/`Speed` but the `SFXModel` branch
   ignores them and reads a **`SFXModel`** key the table does not list (rung 5 law); `PlayCamera`
   declares `IsAlternate` while the executor reads **`Alternate`** (`:830`). Ship an explicit
   OUR-OPS table covering only the ~18 ops this rung emits, with the executor-read keys.
3. **Thread balance**: `StartThread`/`ElseThread` vs `EndThread`.
4. **Refuse `PlayCamera` and `ShiftWorld` outright** with the §2 citations in the message — they are
   inert or harmful on this configuration, and a future author will reach for them.
5. **Cross-file**: every `SFXModel=` path resolves to a staged `particles` entry; every
   `LoadSFX`/`PlaySFX`/`WaitSFX*` `SFX=` id equals `private_ef`.
6. **Warn** when `SetBackgroundIntensity` targets a value strictly between 0 and 1 (§2.5).

---

## 7. RISKS + THE REVIEW CHECKLIST

### 7.1 Risk register

| # | Risk | Severity | Mitigation / status |
|---|---|---|---|
| **R1** | `PlayCamera` is dead at `[Battle] Speed ≥ 3` (§2.1). | **Design-defining** | Closed by design: no `PlayCamera` anywhere; the linter refuses it (K5.4). |
| **R2** | **Netsync freeze ceiling.** A cast freezes global ATB for its whole runtime; `NetSyncBattle.GuestWaitMs = 30000` ms (`NetSyncBattle.cs:35`) is the documented continuous-freeze cap on the s37 B0/B1 path. Our cast is **32.3 s**. Whether the s40/s41 diorama path shares that ceiling is **UNRESOLVED** (PLAN §7). | Medium | **The trim knob is P1's `Wait: Time=95` → `50`.** One line, −45 ticks → **440 ticks = 29.3 s**, under the cap. It is safe *because of where it sits*: everything before `PlaySFX` shifts the whole cast uniformly and touches **neither clock** — the manifest's frame 0 is `PlaySFX`, so every post-`PlaySFX` beat keeps its manifest frame exactly. **Zero** manifest, curve, playlist or alignment edits. Verified: the P4 sting stays on manifest frame **195**, the `strike` clip's own first frame. Want more headroom? `95 → 35` gives 28.3 s; do not touch P0's `Wait: Time=45` (it is the blackout ramp's own `Time=45`). **Do not trim P3** — see §7.3. Solo play is unaffected either way. |
| **R3** | **In-battle load hitch.** `ModelFactory.CreateModel` fires synchronously and unbudgeted at `PlaySFX` (`SFXDataMesh.cs:781`). NIMBRA is a larger asset than rung 7's donor-clone. | Medium | Scheduled **inside the full blackout** (t = 150, black since t ≈ 55) — the same trick native summons use. Rung 7 hit no reported stutter with a comparable model. **Watch on cast 1.** |
| **R4** | **The yaw baseline.** NIMBRA is staged enemy-side; rung 7's proven `(0,180,180)` was derived caster-side. | Low (cost: 1 recast) | One-line manifest edit, recast-only (§3.3). Budget one cast for it, exactly as rung 7 did. |
| **R5** | **Minted sfx ids need one relaunch** (`SoundMetaData` loads at process start). | Low | §5.2. Same relaunch as the `3DModel` line. Silence-with-everything-else-working ⇒ missed relaunch. |
| **R6** | **Audio clipping** — no limiter anywhere in SaXAudio (PLAN §8b); four+ voices live at t = 345. | Medium | Peak budgets in §5 **plus** conservative `Volume=` on every line. If cast 1 crunches at the strike, halve `100003`'s `Volume` before touching the asset. |
| **R7** | **Playlist seam pops** — no blending between chained clips (`SFXDataMesh.cs:845-869`). | Medium | THE PLAYLIST-SEAM RULE (§1.7): every clip starts and ends on the shared `drift` rest pose. Verify offline in the model previewer before deploying. |
| **R8** | **Clock drift** between the `.seq` and the manifest. | Medium | THE PHASE-LOCK RULE (§3): no clip-bound waits after `PlaySFX`. Reviewers must check this literally, line by line. |
| **R9** | **`WaitSFXDone` placed AFTER the `EffectPoint` pair** — a new ordering (rung 7 put it before the relight). | Low-Medium | Reasoned safe: `WaitSFXDone` resolves purely on the running-instance list draining, which `BattleAction.Render` guarantees past `lastFrame`. **If the cast hangs at the damage beat, this is suspect #1.** |
| **R10** | **`Channel: Type=Summon` is a new explicit arg** — rung 5 observed the bare op falling to the `Spell` case for `cmd_no = 46`. | Low | Source-read: `Type` is consulted first (`UnifiedBattleSequencer.cs:262`), the fallback chain only runs when it is absent. Worst case: the wrong aura colour. |
| **R11** | **Bench CSV collision** between the 30300 and 30301 tomls (both define the same `[[playable]]` rows). | Medium | Deploy **only** 30301 (§6.3). Its toml is a superset; "Bahamut Cinema" survives at id 194 and the M1b transplant bench keeps casting. Do **not** deploy both in one session. |
| **R12** | `SFXRework = 0` users get a silent no-op for this entire rung. | Low (bench) | Live install is `SFXRework = 1`. The deploy-time warn is the standing PLAN §9.4 item — this is the rung that should finally land it. |
| **R13** | **Particle draw volume** ≈ 180 concurrent billboards in P1 (§4). | Low | Unmeasured. If P1 stutters, halve `MistFloor`'s 12 emission entries first. |
| **R14** | **Silent-skip DSL** — a typo'd op or arg key vanishes without a log. | Medium | K5 (§6.4). Nothing ships to the install until the linter is green. |
| **R15** | **`ef091/Sequence.seq` does not exist** and must not be created. `SFXData.LoadSFX` unconditionally reads it (`SFXData.cs:174`) — a missing file is a graceful null, but a *present* one would be threaded in as a duplicate-damage parallel thread. | Low | We never write it, **and** `PlaySFX: … SkipSequence=True` is carried anyway (rung 7's gotcha, belt and braces). |
| **R16** | **Provenance** — the temptation to "peek at" a stock `.seq` for pacing. | **Hard rule** | This rung reads **no** stock `.seq`, copies no bytes, and needs no donor. Everything in `ef091/` is ours and **is committed** — the first fully-original effect folder in the study. |
| **R17** | **Pacing: a repeatable ability front-loads ~9.3 s of near-static blackout.** P0's darken ramp (`Time=45`, t 10→55) plus all of P1's hold (`Time=95`, t 55→150) = 140 ticks ≈ 9.3 s where the screen is going-to/at full black and, per §3.1 P1, "nothing else happens" by design — before NIMBRA ever appears. Iviv boots 80 MP ÷ 24 MP = **up to 3 casts per fight**, so a player who leans on the ability can spend up to ~28 s of a single battle on this stretch alone, repeated near-identically each time. | Low-Medium (playtest-judged, not a build defect) | **Not re-choreographed here** — §3's "nothing else happens for six seconds… allowed to be boring" is a deliberate dread beat, not an oversight, and P0/P1 are otherwise load-bearing (the blackout ramp, the pall's own spawn window). Recorded so the first playtest weighs it *consciously* rather than discovering it as a surprise on cast 3. The knob already on the table if it reads as too much on repeat: **R2 / §6 knob 5's P1 `Wait: Time=95 → 50`** (the CURRENT version — not the §7.3-retracted P3 recipe) trims exactly this stretch to 50 ticks / 3.3 s without touching any curve, playlist, or clock alignment (it sits before `PlaySFX`, so it shifts the whole cast uniformly). Judge live, then decide. |

### 7.2 Per-lane review checklist

Each build lane must be checked against the laws it can actually break.

**Creature lane** (`make_nimbra.py`)
- [ ] ONE merged mesh, 5 parts, ≤ 7 000 verts, ≤ 6 parts (§1.4)
- [ ] `calibrate_winding` used, not assumed (boletta lesson)
- [ ] Texture V orientation checked in the offline preview (boletta upside-down-face lesson)
- [ ] Palette authored ~15 % dark — **no battle-actor lighting pass on the SFX path** (rung 7 residual b)
- [ ] 14 bones, contiguous `bone000…bone013`, parent < child
- [ ] Model-preview rendered and *looked at* before any deploy — **THE OFFLINE-EYE / MODEL-PREVIEW LAW** (the rung-7-era "red circle" incident)

**Clip lane** (`make_nimbra_anims.py`)
- [ ] THE PLAYLIST-SEAM RULE: all three clips open and close on the `drift` rest pose (§1.7)
- [ ] `drift` frame 0 pose == frame 74 pose exactly (loopable)
- [ ] `new_clip` rest-fill relied on for unkeyed bones (`models/anim.py:551-556`)
- [ ] `Speed` compensation applied as specced (2 / 1 / 2) and the tick footprints match §3.2
- [ ] Written to `anim_disc_path`, **no `3DModelAnimation` line** (`deploy.py:692-695`)

**Particle lane**
- [ ] `TextureKind: "0"` + `Shader: "SFX_ADD_G"` only (rung 5 proven; no `SFX_SUB_G` — §4)
- [ ] Every `CreateVisualEffect` line carries `Char=` (rung 5 law)
- [ ] `Time`/`Size`/`Speed` **not** written on any `CreateVisualEffect` line (inert — rung 5 law)
- [ ] Full `Data/`-rooted `SFXModel=` paths (rung 5 law)
- [ ] `RiftFlash` anchors on `TargetPosition*` (valid on the `CreateVisualEffect` path) and the
      creature anchors on `TargetAveragePosition*` — **THE AVERAGE-POSITION SPLIT** (§3.3)
- [ ] `Vertices` are 2-component screen-plane offsets (`sprite.vertex` is `Vector2[]`, `SFXDataMesh.cs:1060-1065`)
- [ ] `Indices` count == 3 × triangle count; JSON parses (a trailing comma kills `JSONNode.Parse` silently)

**Audio lane** (`make_nimbra_audio.py`)
- [ ] Peaks ≤ the §5 budget, measured not assumed (**no limiter anywhere** — PLAN §8b)
- [ ] Ids 100001/100002/100003, minted via `sound.mint_song(kind="sfx")`
- [ ] `PlaySound` lines carry explicit `SoundType=SoundEffect` and `Volume=`
- [ ] `StopSound` for the drone at t = 480
- [ ] Relaunch documented in the runbook as a **prerequisite**, not a footnote (§5.2)

**Sequence lane** (`nimbra.seq`)
- [ ] Linter green (K5) — op whitelist, arg keys, thread balance, no `PlayCamera`/`ShiftWorld`
- [ ] **THE PHASE-LOCK RULE**: zero clip-bound waits after `PlaySFX` (§3)
- [ ] **THE FIGURE-VISIBILITY LAW**: both `EffectPoint` lines fire ≥ 12 ticks after `Intensity=1` completes (§3.1 P4)
- [ ] **THE ANIM=IDLE RELEASE LAW**: the cast closes on `PlayAnimation: … Anim=Idle` (rung 6)
- [ ] **THE INTENSITY LAW**: only `Intensity=0` and `Intensity=1` destinations; no mid holds (§2.5)
- [ ] `UseCamera=False` explicit on `LoadSFX` — the computed default is **TRUE** on this install
      (`Speed<3 || phase!=NORMAL || !FF9BMenu_IsEnable()`, `UnifiedBattleSequencer.cs:344`; the menu
      is disabled during a command ⇒ the third disjunct is true)
- [ ] `SkipSequence=True` on `PlaySFX` (R15)
- [ ] Tick arithmetic re-derived independently against §3.1/§3.2 — the two clocks must land on 480

**Wiring lane** (`rung8.field.toml`, `build_rung8.py`)
- [ ] `type = 0` — **THE TYPE-4 MP LAW** (§6.2)
- [ ] `scriptId` inherited = 85, **≠ 87** (Odin's Sword SA)
- [ ] `targets = "AllEnemy"` — the rung-1 structural-full-cast law
- [ ] `vfx1 = vfx2 = 91`
- [ ] `private_ef = 91` pinned, `ef084/` untouched and byte-verified before and after
- [ ] Deployed to slot **30301**; 30300 not re-deployed in the same session (R11)
- [ ] `revert_rung8.py` exists, is idempotent, and removes `ef091/` entirely
- [ ] Nothing under `StreamingAssets/Data/SpecialEffects/` in the **stock** tree is written, ever

### 7.3 RETRACTED — the P3 trim (why R2's first remediation was wrong)

R2 originally prescribed a three-part edit: P3's `Wait: Time=90` → `0`, `[summon.staging] end`
330 → 240, and `repeat = 2 → 1` on **both** `drift` entries. **Applied exactly as written it fails
three times**, and the third failure is the one that matters — it breaks the very alignment the recipe
claimed to protect. Measured, not reasoned:

1. **It does not build.** `end = 240` leaves all three curves summing to 330 (move `45+285`, turn
   `45+180+105`, scale `45+210+75`), so `deploy._validate_staging` refuses it three times over —
   *"durations sum to 330 but end - start = 240"*. The recipe never said to re-proportion them, and
   there is no single obvious re-proportioning: the curves encode the beat, not the clock.
2. **Re-proportioned, it still does not build.** The trimmed playlist is
   `emerge 45 + drift 75 + strike 30 + drift 75 = 225` ticks against a 240-tick window — short by 15.
   `deploy.playlist_coverage` raises **THE ANIMATION-PLAYLIST LAW**: past 225 the model freezes on
   `drift`'s last frame for a second.
3. **Forced through, the strike beat desynchronises — the exact defect the recipe existed to prevent.**
   `Wait: Time=90` sits *after* `PlaySFX`, so cutting it moves every later beat **against the manifest
   clock**. The P4 sting drops from manifest frame 195 to **105**, while the shortened playlist puts
   `strike` at frames **120–150**. The sting fires 15 frames early, in the middle of a `drift`.

The mistake was structural, and it generalises: **a `Wait` after `PlaySFX` is the one thing you must
never trim.** The two clocks (the `.seq`'s ticks and the `.sfxmodel` manifest's frames) share an origin
at `PlaySFX` and run locked from there — THE PHASE-LOCK RULE (§3) is usually stated as "no clip-bound
waits in that window", but its stronger form is that *no edit at all* in that window is free. Before
`PlaySFX` there is no manifest clock yet, so any change there is a pure uniform shift. That is the whole
reason the corrected knob is **P1's**, and why it needs no other edit anywhere.

For the record, the retracted recipe's arithmetic was not wrong about its *destination*: P3→0 with
`end = 240` does land at 395 ticks ≈ 26.3 s. It was wrong about everything in between.

---

## 8. Appendix A — the draft `nimbra.seq` (the binding artefact)

```
// FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef091/PlayerSequence.seq
// RUNG 8 -- NIMBRA, the composed epic. 100% hand-authored; no donor, no LoadSFX of any stock id,
// no native ef###.bytes anywhere in the chain. Contract: rung8-epic/STORYBOARD.md.
// Clock: BattleTPS=15 -> 1 tick = 1/15 s. Total ~485 ticks ~= 32.3 s.
// THE PHASE-LOCK RULE: after PlaySFX every wait is a fixed Wait -- never a clip-bound WaitAnimation.

// ---- P0  THE HUSH  (t 0 -> 55) -------------------------------------------------------------
WaitAnimation: Char=Caster
Message: Text=[CastName] ; Priority=1 ; Title=True ; Reflect=True
SetupReflect: Delay=SFXLoaded
LoadSFX: SFX=91 ; Char=Caster ; Reflect=True ; UseCamera=False
PlayAnimation: Char=Caster ; Anim=MP_IDLE_TO_CHANT
WaitAnimation: Char=Caster
PlayAnimation: Char=Caster ; Anim=MP_CHANT ; Loop=True
Channel: Type=Summon
PlaySound: Sound=100001 ; SoundType=SoundEffect ; Volume=0.55
SetBackgroundIntensity: Intensity=0 ; Time=45
CreateVisualEffect: Char=Everyone ; SFXModel=Data/SpecialEffects/ef091/MistFloor.sfxmodel
Wait: Time=45

// ---- P1  THE MIST GATHERS  (t 55 -> 150) ---------------------------------------------------
CreateVisualEffect: Char=Everyone ; SFXModel=Data/SpecialEffects/ef091/MistWisps.sfxmodel
PlaySound: Sound=100002 ; SoundType=SoundEffect ; Volume=0.5
Wait: Time=95

// ---- P2  THE COALESCE  (t 150 -> 255)  manifest frame 0 starts HERE -------------------------
WaitSFXLoaded: SFX=91 ; Reflect=True
PlaySFX: SFX=91 ; Reflect=True ; SkipSequence=True
Wait: Time=105

// ---- P3  THE DRIFT  (t 255 -> 345) ---------------------------------------------------------
StopChannel
PlayAnimation: Char=Caster ; Anim=MP_MAGIC
Wait: Time=90

// ---- P4  THE STRIKE  (t 345 -> 405) --------------------------------------------------------
PlaySound: Sound=100003 ; SoundType=SoundEffect ; Volume=0.7
CreateVisualEffect: Char=AllTargets ; SFXModel=Data/SpecialEffects/ef091/RiftFlash.sfxmodel
SetBackgroundIntensity: Intensity=1 ; Time=18
Wait: Time=30
EffectPoint: Char=AllTargets ; Type=Effect
Wait: Time=12
EffectPoint: Char=Everyone ; Type=Figure
Wait: Time=18

// ---- P5  THE DISSOLVE + RELEASE  (t 405 -> 485) --------------------------------------------
WaitSFXDone: SFX=91 ; Reflect=True
CreateVisualEffect: Char=Everyone ; SFXModel=Data/SpecialEffects/ef091/MistWisps.sfxmodel
StopSound: Sound=100001 ; SoundType=SoundEffect
ActivateReflect
WaitReflect
PlayAnimation: Char=Caster ; Anim=Idle
Turn: Char=Caster ; BaseAngle=Default ; Time=5
WaitTurn: Char=Caster
```

`ef091/FileList.txt` (one line, **single spaces only** — the grammar splits on single spaces and a
tab or double space breaks it silently, `SFXData.cs:253-254`):

```
Model nimbra_manifest.sfxmodel
```

---

## 9. Appendix B — citation index

**Engine** (`C:/gd/FFIX/Memoria/Assembly-CSharp`, Memoria `6b8bb2d5`)

| Claim | Site |
|---|---|
| `PlayCamera` skipped at `Speed>=3` in `PHASE_NORMAL` | `Memoria/Battle/SFX/UnifiedBattleSequencer.cs:825-854` (gate at `:828-829`) |
| `PlayCamera` with `Char=` engages the native plugin | `Global/SFX/SFX.cs:1989-1995` (`SetCameraTarget`), `:2029-2049` (`SetEnemyCamera`) |
| `CameraNo` has no managed consumer | `Global/SFX/SFX.cs:953`; `Memoria/Battle/SFX/SFXData.cs:723`, `:1182`; seed at `Global/Honolulu/HonoluluBattleMain.cs:161-162` |
| `PHASE_NORMAL` is the normal-fight phase | `Global/battle/battle.cs:108`, `:129-130` |
| `ShiftWorld` gated on the camera engine | `UnifiedBattleSequencer.cs:1044-1055` |
| `ShiftWorld` moves only `btlRoot`; no auto-restore | `Global/battlebg.cs:407-432` (children `:22`, `:40`), `UnshiftWorld :455-462` |
| `SetBackgroundIntensity` value/tween/hold | `UnifiedBattleSequencer.cs:1030-1043`; `SequenceBBGIntensity :1602-1648`; `battlebg.setBGColor :474-490` |
| `Channel: Type=` consulted before the `cmd_no` fallback | `UnifiedBattleSequencer.cs:259-286` (`:262`) |
| `LoadSFX` `UseCamera` computed default | `UnifiedBattleSequencer.cs:344` |
| `EffectPoint` `Type=Effect` / `Figure` split | `UnifiedBattleSequencer.cs:966-1017` |
| `PlaySound` → `SoundLib.PlaySoundEffect(id, vol, pan, pitch)`; `SoundType` defaults to `SoundEffect` | `UnifiedBattleSequencer.cs:858-936` (`:908`); `BattleActionCode.cs:157-160` |
| `CreateVisualEffect` `SFXModel` branch; `Char` required | `UnifiedBattleSequencer.cs:381-448` (`:445`); `BattleActionCode.cs:493-496` |
| `PlayAnyEffect` → `SetupPositions(caster, Char-unit, Offset)` | `Memoria/Battle/SFX/SFXChannel.cs:13-21`; `SFXDataMesh.cs:30-35` |
| `PlaySFX` → `SetupPositions(exe, trgno==1 ? trg[0] : null, trgcpos)` | `Memoria/Battle/SFX/SFXData.cs:149` |
| `trgcpos` = target mean, `vy` forced 0 | `FF9/BTL_VFX_REQ.cs:72-92` |
| `TargetPosition*` = 0 when `target` is null | `Memoria/Battle/SFX/ParametricMovement.cs:176-178` |
| Curve pieces, chaining, NCalc params | `ParametricMovement.cs:58-136` (chaining `:88-105`), `:138-201` |
| `Parameter0` = base angle for `Turning1/2` | `ParametricMovement.cs:233-238`; factors `:296-297` |
| Interpolation enum | `ParametricMovement.cs:262-271`; unknown → `Constant` `:273-285` |
| FBX entry keys; `Animations{Path,Speed}` | `SFXDataMesh.cs:988-1042` |
| `End==Start` ⇒ auto-derived duration | `SFXDataMesh.cs:803-808` |
| `ModelFactory.CreateModel` at `Begin()` | `SFXDataMesh.cs:775-781` |
| Per-frame pose from the three curves | `SFXDataMesh.cs:843-845` |
| Playlist chaining, `Speed`, freeze-on-last | `SFXDataMesh.cs:845-869` |
| Sprite schema (verts/UV/colours/emission/scale) | `SFXDataMesh.cs:1044-1230`; emission params `:1159-1185`; `Particle` ctor `:1382-1404` |
| Sprite billboard projection | `SFXDataMesh.cs:1280-1321` |
| Shader name vocabulary | `Global/SFXMesh/SFXMesh.cs:981-982` |
| Unknown ops silently skipped | `Memoria/Battle/SFX/BattleActionThread.cs:154-155` |
| Op/arg table (44 ops) | `Memoria/Battle/SFX/BattleActionCode.cs:46-89` |
| Threading (`StartThread`/`ElseThread` → `RunThread`) | `BattleActionThread.cs:181-192` |
| `FileList.txt` single-space grammar | `Memoria/Battle/SFX/SFXData.cs:244-279` (`:253-254`); unconditional `Sequence.seq` read `:174` |
| `Unused_N` absent-id aliases | `Memoria/Data/Battle/SpecialEffect.cs:496-519` |
| Netsync guest freeze cap | `Memoria/Netsync/NetSyncBattle.cs:35` |

**Install** (read-only, 2026-07-24): `Memoria.ini` — `[Battle] Speed = 5`, `SFXRework = 1`;
`[Graphics] BattleTPS = 15`; `[Audio] Backend = 1`. `StreamingAssets/Data/SpecialEffects/` = 488
entries (487 `ef###` + `Common`); `ef080`/`ef084`/`ef091` absent. `FF9CustomMap/.../SpecialEffects/`
contains only `ef084`. `Common/ChannelSummon.sfxmodel` — the `CasterPositionY + Parameter1 * 800`
rise and the `Turning1`/`Turning2` orbit idiom.

**Kit**: `summons/deploy.py` (`ABSENT_EF_IDS:74-77`, `normalize_spec:178-180`, `splice_host_seq:328-344`,
`alloc_private_ef:410-421`, `_sfxmodel_manifest:616-631`, `_decode_donor_clips:634-664`,
`_stage_overlay_extras:692-727`, `emit_overlay:845-858`); `content/summon.py:137-142`;
`models/anim.py:46-50`, `:551-556`; `sound.py:213`, `:246`; `itemstats.py:25-26`;
`examples/boletta/make_creature.py`; `examples/thirteenth-character` / `rung3-fresh-id/rung3.field.toml`.

**Study**: `PLAN.md` §3.4, §3.7 (THE TYPE-4 MP LAW), §5 rungs 1-7, §7, §8, §9;
`rung5-particles/README.md` (the `CreateVisualEffect` laws, `rung5_sprite.sfxmodel`);
`rung6-bare-sequence/README.md` (the cast-protocol grammar, THE ANIM=IDLE RELEASE LAW, THE INTENSITY
SUBTLETY LAW); `rung7-creature/README.md` (THE MOVEMENT TRAP, THE ROTATION BASELINE LAW, THE
ANIMATION-PLAYLIST LAW, the `SkipSequence` gotcha, the two logged residuals);
`thomas-swap/m2/DESIGN.md` §1, §1.4, §5, §6.

---

## 10. What this rung deliberately does NOT do

- **No camera work.** Rung 9 (the `camera_codec` attack-slot extension) is the place for that, and §2
  raises its bar: on a `Speed >= 3` install the `.seq`-side camera ops are inert, so rung 9's lever
  has to be the raw17 table, not `PlayCamera`.
- **No `[SfxHybrid]` / s58.** That is the *transplant* lane (a model wearing a stock donor's bones).
  NIMBRA is the *original* lane and runs on stock Memoria.
- **No `SequenceFile` route, no `PatchedVfx`, no `AbilityFeatures` NCalc.** The plain
  `vfx1 → ef{id}/` binding is proven and sufficient.
- **No short/long variant.** A minted command never enters `DecideSummonType` (PLAN §3.7) — NIMBRA
  always plays in full, which is what "epic" wanted anyway.
