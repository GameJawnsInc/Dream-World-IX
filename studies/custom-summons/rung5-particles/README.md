# Custom Summons -- rung 5: the `CreateVisualEffect` particle probe

> Ladder position: `studies/custom-summons/PLAN.md` §5, rung 5 of 9.
> Depends on rung 1 (★ in-game proven 2026-07-21) -- the same bench, field **30300**, Iviv's
> minted **Spark → Bahamut Cinema** ability -- and on rung 3's private-folder law (`vfx1=84`, the
> `ef084/` copy, currently a byte-identical carry of stock `ef227`). Rung 4's edit to the SHARED
> `ef227/Sequence.seq` has already been reverted and is untouched by this rung (verified on disk
> before this rung began: no `ef227/` override folder exists in the mod folder).

## What this proves

With the game **already running**, **no relaunch, no redeploy** (recast-only, same loop as rungs
2-4):

1. **`CreateVisualEffect` genuinely spawns particles on top of the existing `Channel` aura.** The
   two ops run through entirely separate code paths -- the bare `Channel` line (already in
   `ef084/PlayerSequence.seq` at line 18) populates `SFXChannel.CurrentPlayChannel` (a
   per-caster-keyed dict); `CreateVisualEffect` populates `SFXChannel.CurrentPlayOthers` (a plain
   list). They are additive, not exclusive -- both render every frame, independently.
2. **A bare `SFXModel=Data/...` path resolves a STOCK `Common/*.sfxmodel` file with zero copying**
   (stage A) -- the identical stacked-mod-folder, no-cache `AssetManager.LoadString` walk rungs 2-4
   already proved for `.seq` files, now proved for `.sfxmodel` too.
3. **The identical mechanism resolves a wholly NEW, kit-owned Sprite JSON** -- `rung5_sprite.sfxmodel`
   in this directory, 100% our content, zero Square-Enix bytes -- deployed under rung 3's own
   private `ef084/` folder at a brand-new filename (stage B).
4. `CreateVisualEffect` is genuinely **first-ever content** in this op: a recursive grep of every
   `.seq` file across all 487 shipped `ef###/` folders + `Common/` finds **zero** uses of
   `CreateVisualEffect`, `SFXModel=`, or `UseSFXModel=` anywhere in the base install. There is no
   prior in-game-proven example to fall back on -- this rung's own two casts are the first ones.

## THE CHANNEL BASELINE -- read this before either cast

The bare `Channel` line already sitting at `ef084/PlayerSequence.seq` line 18 (no `Type=` argument)
picks its aura by the casting command's `cmd_no` (`UnifiedBattleSequencer.cs:262-272`). Our minted
command sits at `cmd_no=46` -- `BattleCommandId.Reserve4`, explicitly commented `// Unused` in the
enum -- which matches **none** of the named cases (BlueMagic/BlackMagic/DoubleBlackMagic/
MagicSword/SummonEiko/SummonGarnet/Phantom/SysPhantom), and the caster is a player (not an enemy),
so every check falls through to the final `else` branch: **`tmpStr = "Spell"`**.

**So the bench, right now, already shows `Common/ChannelSpell.sfxmodel`'s pale gray-blue-white glow**
during the chant hold -- despite this being a "summon" in name. Neither of this rung's stages
replaces that existing glow; both stages ADD a second, independent, visually distinct layer on top
of it:

| Stage | File | Look | Already-visible baseline it layers onto |
|---|---|---|---|
| A | `Common/ChannelSummon.sfxmodel` (stock, 3 texture layers) | green + burnt-orange + grey flare | `ChannelSpell`'s pale gray-blue-white glow (unchanged, still there) |
| B | `rung5_sprite.sfxmodel` (ours, no texture) | magenta annulus, fades in/out, rises + grows | same |

If stage A/B looked identical to a plain rung-1/3 recast with no extra color at all, that would mean
the new layer never rendered -- **not** that the baseline aura vanished (it can't; `Channel` and
`CreateVisualEffect` don't share any code that could make one suppress the other).

## The exact edit

Both stages insert **one new line** into `ef084/PlayerSequence.seq` (rung 3's private copy --
`ef227`, the shared donor, is never touched), between the existing `Channel` line and the
`SetBackgroundIntensity` tween that follows it:

```diff
 PlayAnimation: Char=Caster ; Anim=MP_CHANT ; Loop=True
 Channel
+CreateVisualEffect: Char=Caster ; SFXModel=<stage-specific path>
 SetBackgroundIntensity: Intensity=0 ; Time=12
 WaitSFXLoaded: SFX=Bahamut__Full ; Reflect=True
```

- **Stage A** (`--stage-a`): `SFXModel=Data/SpecialEffects/Common/ChannelSummon.sfxmodel`
- **Stage B** (`--stage-b`): `SFXModel=Data/SpecialEffects/ef084/RisingRing.sfxmodel`

Why this slot: it's the exact spot the bare `Channel` line already occupies in every stock
magic/summon cast -- the aura starts glowing right as the 12-frame blackout ramp begins, so by the
time the screen is fully black the aura/particle is already lit against darkness (max contrast for
an additive effect). `SetBackgroundIntensity=0` only disables the battle-BACKGROUND's own
`MeshRenderer` (`battlebg.cs:474-490`) -- it never touches `SFXChannel`/`SFXData` particle draws
(`Graphics.DrawMeshNow` calls each frame, entirely independent) -- so both the existing `Channel`
aura and our new layer play straight through the blackout, exactly like they already do in every
prior rung's proof run.

**`Char=Caster` is required, not optional.** `TryGetArgCharacter` (`BattleActionCode.cs:493-496`)
defaults `tmpChar=0` (a unit-id bitmask with no bits set) *before* parsing, and only overwrites it on
a recognized token. Omit `Char=` and the effect renders on **nobody** -- silently, no error, no log.
Both stages always write it explicitly.

**`Time=`/`Size=`/`Speed=` are NOT written on this line, and would be silently inert if they were.**
The recon traced `UnifiedBattleSequencer.cs:381-448`'s `CreateVisualEffect` case directly: those
three keys are parsed but only ever consulted for `effectKind` 0/1 (SPS/SHP); for `SFXModel` mode
(`effectKind==2`) the executor only forwards the `Offset` vector into
`SFXChannel.PlayAnyEffect(sfxModel, cmd.regist, btl, tmpVec, 0)` -- **all** duration/scale/speed
control for both stages lives inside the `.sfxmodel` JSON's own `Duration`/`Scale`/`Movement`
fields. This directly contradicts the impression given by `BattleActionCode.cs:64`'s declared arg
list (which lists `Time`/`Size`/`Speed` alongside `SFXModel` with no hint that they're mode-gated) --
worth remembering if this op is ever reused elsewhere.

## Stage B's bespoke sprite (`rung5_sprite.sfxmodel`)

The **one committable artifact** in the whole custom-summons study to date -- every other
`.seq`/`.sfxmodel` file touched by rungs 2-5 is Square-Enix-derived and can only ever be
*regenerated* by a script, never checked into git. `rung5_sprite.sfxmodel` is 100% hand-authored
JSON: zero texture, zero binary asset, zero SE bytes.

- **Shape**: a 16-vertex, 16-triangle octagonal annulus (a ring, not a filled disc) -- outer radius
  30, inner radius 18, in the same screen-offset unit convention as stock's own `ChannelSummon`
  mesh layer (whose vertices span roughly ±37 units).
- **Material**: `TextureKind:"0"` (no texture) + `Shader:"SFX_ADD_G"` (additive, Gouraud-shaded,
  vertex-color only) -- the same no-texture-additive convention `ChannelSummon`'s own mesh layer
  uses, so it needs no PNG at all.
- **Color**: fades black → magenta over frames 0-8 (`SinusOut`), holds, fades magenta → black over
  frames 8-32 (`SinusIn`), constant alpha 0.5 -- brightness carries the fade under the additive
  blend, the same convention every sampled stock aura uses.
- **Movement**: rises +300 world-Y over its full life, ease-out (`SinusOut`).
- **Scale**: 0.5x → 2.0x over the same span.
- **Duration**: 36 frames (~2.4s at the user's live `BattleTPS=15`) -- self-terminating; no stop
  op exists or is needed (see "How it ends," below).
- **Color choice**: magenta `(1,0,1)` was picked because none of the three sampled stock Channel
  auras use it (`ChannelSpell` = pale gray-blue-white, `ChannelBlack` = dark indigo/navy,
  `ChannelSummon` = green/burnt-orange/grey) -- unmistakably non-canon at a glance.

`build_rung5.py --stage-b` copies this repo file verbatim to
`FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef084/RisingRing.sfxmodel` every run (idempotent,
no drift guard needed -- there's no "stock" version of a file we authored ourselves to drift from).

### How it ends (no stop op needed)

`SFXChannel.PlayAnyEffect` wraps the loaded JSON and appends it to `SFXChannel.CurrentPlayOthers` (a
list, distinct from the bare-`Channel` op's per-caster `CurrentPlayChannel` dict). Every frame,
`SFXChannel.Render()` calls `sfx.Render(frame)`; the render call returns `ended=true` once
`frame > mseq.lastFrame` (auto-computed from every sprite's `emission.frame + sprite.duration`) AND
no particles remain -- at which point the effect is torn down and removed from the list
automatically. Both stages are fire-and-forget: they play out their own baked timeline and vanish on
their own, independent of whatever the calling `.seq` thread does afterward. Executing the
`CreateVisualEffect` op itself consumes **0 ticks** -- no `waitSFX`/`waitFrame` is set by this case,
so the thread falls through to the next line on the same tick, exactly like the bare `Channel` op
immediately above it.

## Test procedure

The game is **already running** with the bench save loaded. No relaunch, no redeploy.

**Cast A comes first** (this directory's current on-disk state, after this session's build run):

1. `py studies/custom-summons/rung5-particles/build_rung5.py --stage-a` (already run this session --
   the override is live; re-running is safe/idempotent).
2. In-game: get back into a battle on field 30300 (walk around for the random encounter, or leave
   and re-enter if not already mid-fight).
3. Select **Iviv → Spark → Bahamut Cinema** (same command as every prior rung).
4. **Expect to see:** during the chant hold (right as the screen starts dimming to black), the
   existing pale `ChannelSpell` glow (baseline, unchanged) PLUS a second, clearly different
   green/burnt-orange/grey flare layered on top of it -- `ChannelSummon`'s own look, now firing from
   a `.seq` line for the first time ever.

**Cast B** (bespoke sprite):

5. `py studies/custom-summons/rung5-particles/build_rung5.py --stage-b`
6. Recast **Bahamut Cinema** again the same way.
7. **Expect to see:** the same pale baseline glow, plus a magenta ring that fades in, expands, rises,
   and fades back out over about 2.4 seconds during the chant hold -- OUR content, rendering inside
   the donor cinematic.

Either order is fine to try first; the task ordering (A before B) is only about which state this
directory's build script leaves on disk after this session's own proof run.

## Failure modes (most to least informative)

| Symptom | Meaning |
|---|---|
| Baseline pale glow PLUS a second, clearly distinct effect (green/orange/grey for A, magenta ring for B) | **SUCCESS** -- the stage under test is proven: `CreateVisualEffect` layers additively over `Channel`, the path resolved, the `.sfxmodel` rendered |
| **Only** the baseline pale glow, nothing new | The most informative failure. Either (a) the deployed `.seq` doesn't actually carry the `CreateVisualEffect` line -- re-run the build script and diff the deployed file (see "Verify" below); or (b) the line was silently dropped/no-op'd. The single most likely silent-no-op cause: a missing/mistyped `Char=` argument defaults `tmpChar=0`, so `btl_util.findAllBtlData(0)` iterates zero units and the effect renders on nobody -- **this build always writes `Char=Caster` explicitly**, so seeing this failure would itself be a new discovery worth a fresh recon pass, not just a config slip |
| Effect visible but the WRONG one (e.g. stage A shows magenta, or vice versa) | The deployed file's `SFXModel=` value doesn't match the stage you think you built -- re-run the intended `--stage-a`/`--stage-b` flag and check the printed diff before recasting |
| Screen goes black / effect area shows nothing at all during the blackout, though the rest of the cinematic (chant, roar, flare, reveal) plays fine | Distinguish from the FIGURE-VISIBILITY class rung 4 minted: that law is specific to `EffectPoint Type=Figure`'s damage-number UI popup being washed out by `SetBackgroundIntensity=0`'s renderer-disable -- it does **not** extend to `SFXChannel`/`CreateVisualEffect` particle draws (`Graphics.DrawMeshNow`, unrelated code path, confirmed by source read of `battlebg.cs:474-490`). If nothing renders here, it's a path-resolution or DSL-parse problem, not this rung-4 interaction recurring |
| Cinematic doesn't play at all anymore (regression from rungs 1/3) | Something is malformed enough to break thread parsing -- revert immediately (`revert_rung5.py`) and re-diagnose; this means the edited file broke, not that "it isn't proven" |
| Game crashes or hard-locks on cast | See "Crash risk assessment" below -- treat as a genuine new discovery (this op has zero prior in-game exercise anywhere) and capture a `game_snap.ps1` frame + revert immediately |

### Verify the override actually landed (if anything looks off)

```
py -c "print(open(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Data\SpecialEffects\ef084\PlayerSequence.seq').read())"
```

should show the `CreateVisualEffect` line as the file's 19th line (right after `Channel`, right
before `SetBackgroundIntensity: Intensity=0 ; Time=12`), with the stage-appropriate `SFXModel=`
value. For stage B, also confirm the sprite landed:

```
py -c "print(open(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Data\SpecialEffects\ef084\RisingRing.sfxmodel').read())"
```

## Crash-risk assessment

`CreateVisualEffect` is a **real, engine-supported op** (`BattleActionCode.cs:64` declares it,
`UnifiedBattleSequencer.cs:381-448` fully implements the `SFXModel` branch) -- it is not a stub or a
dead code path. The genuine open risk is that it has **zero shipped precedent**: no stock or modded
`.seq` anywhere in the base install exercises it, so there is no in-game-proven reference cast to
fall back on if something about this specific engine build's `SFXModel` path misbehaves in a way the
source read didn't anticipate. Concretely, the failure surface is narrow:

- **Stage A** references a file (`Common/ChannelSummon.sfxmodel`) the engine ALREADY loads today,
  just via a different call site (`SFXChannel.LoadSingle`/`LoadAll`'s hardcoded `Channel`-op path,
  `SFXChannel.cs:121-150`) -- so the JSON itself is known-good, parseable content; only the NEW
  call site (`CreateVisualEffect` → `SFXDataMesh.ModelSequence.Load` → `SFXChannel.PlayAnyEffect`) is
  unexercised. Low risk.
- **Stage B** references a wholly new, hand-authored JSON. It was validated as syntactically correct
  JSON before deploy (`json.load` succeeds; 16 vertices / 48 indices = 16 triangles, matching the
  declared `Indices` count) and its key set matches the exact shape `SFXDataMesh.LoadSprite`
  (`SFXDataMesh.cs:1007-1206`) parses, cross-checked line-by-line against the real
  `Common/ChannelSummon.sfxmodel` file's own key/value conventions (`"TextureKind":"0"`,
  `"Shader":"SFX_ADD_G"`, `"ColorInterpolation":["SinusOut","SinusIn"]`, `Movement`/`Scale`/
  `Duration`/`Emission` shapes all matched). No known-bad key or malformed value was found. Slightly
  higher risk than stage A only because it's genuinely new content, not a re-used stock file.
- Neither stage touches thread control flow (`StartThread`/`EndThread`/`Wait*`) -- the one class of
  edit rung 4's own failure-mode table calls out as capable of breaking parsing outright. A single
  new, self-contained line dropped between two independent existing lines is the lowest-blast-radius
  edit shape this study has made so far.
- If the game does hard-lock or crash: revert immediately (`revert_rung5.py`), capture the game
  window if still responsive (`tools/game_snap.ps1`), and treat it as a genuine new finding about
  this op's SFXModel path on this specific engine build -- not an assumed typo.

## The shared-folder / provenance caveat

Neither stage touches `ef227` (the shared Bahamut donor folder) or the rung-2 staged chime --
verified on disk before this rung began (no `ef227/` override exists in the mod folder; rung 4's own
edit there was already reverted in a prior session). Vanilla Garnet/Eiko Bahamut casts are
unaffected by this rung either way.

`ef084/PlayerSequence.seq` is SE-derived (a modified copy of Square-Enix's own shipped file) and is
therefore never committed -- `build_rung5.py` is the only committable record of the edit, exactly
like rungs 2-4. `rung5_sprite.sfxmodel` is the sole exception: 100% hand-authored JSON, zero SE
bytes, committed in this directory.

## Revert

```
py studies/custom-summons/rung5-particles/revert_rung5.py
```

Restores `ef084/PlayerSequence.seq` to a pure byte-identical copy of stock `ef227/PlayerSequence.seq`
(rung 3's own baseline -- no `CreateVisualEffect` line) and deletes the deployed
`ef084/RisingRing.sfxmodel`, if present. Does **not** touch this directory's own repo copy of
`rung5_sprite.sfxmodel` (our committed content, not deploy output), `ef084/Sequence.seq` (rung 3's
file, never written by this rung), `ef227/` (the shared donor -- untouched by this rung), or the
rung-2 staged chime.

## Provenance

`build_rung5.py` is the only committable record of the `.seq` edit: it reads the user's own stock
install, applies exactly the one insertion documented above, and writes the result into the live
`FF9CustomMap` mod folder -- never into this directory, never into git. The edited
`PlayerSequence.seq` is SE-derived content and must never be committed. `rung5_sprite.sfxmodel` is
the opposite case -- 100% our own authored JSON, zero SE bytes -- and **is** committed alongside the
scripts. `build_rung5.py` includes the same **drift guard** convention as rungs 2-4: it refuses to
run if the stock `ef227/PlayerSequence.seq`'s sha256
(`4bc643bfb3ec478dcc1f5b51261f59637faac9d775cccd38c0055afee14ece63` -- the same hash
`rung3-fresh-id/build_rung3.py` independently verified for this same file) doesn't match what this
script's insertion point was derived against, and further refuses to guess if the `Channel` /
`SetBackgroundIntensity` anchor pair doesn't appear in the file **exactly once**.
