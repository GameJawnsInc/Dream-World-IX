# Custom Summons -- rung 6: the fresh-id BARE SEQUENCE

> Ladder position: `studies/custom-summons/PLAN.md` §5, rung 6 of 9.
> Depends on rung 1 (★ in-game proven 2026-07-21) -- the same bench, field **30300**, Iviv's
> minted **Spark → Bahamut Cinema** ability -- and on rung 3's private-folder law (`vfx1=84`, the
> `ef084/` folder, already deployed + relaunched once -- no further relaunch needed). Also reuses
> rung 5's bespoke sprite (`rung5-particles/rung5_sprite.sfxmodel`, ★ in-game proven 2026-07-21)
> verbatim, redeployed to this rung's own `ef084/RisingRing.sfxmodel` path.

## What this proves

With the game **already running**, **no relaunch, no redeploy** (recast-only, same loop as rungs
2-5): a summon-**class** command (`cmd_no=46`, a minted, engine-unclaimed command-menu entry) can
play out **gracefully end to end with ZERO native content anywhere in its presentation** -- no
`LoadSFX` of Bahamut or any other stock effect, no stock creature, no stock camera hookup, nothing
Square-Enix in the cast's own choreography. Everything that plays is either a stock caster
*animation clip name* (`MP_IDLE_TO_CHANT`/`MP_CHANT`/`MP_MAGIC`/`Idle` -- skeletal identifiers on the
caster's own model, not "native content" in the sense this rung is testing) or kit-authored: the
rung-2 chime (`PlaySound: Sound=100000`) and the rung-5 bespoke magenta ring
(`CreateVisualEffect: ... SFXModel=Data/SpecialEffects/ef084/RisingRing.sfxmodel`).

A clean cast here closes the last open half of **Tier 3** (PLAN.md §4/§9): a fully composed
*original* summon needs no donor id or donor content at all -- just a fresh `ef###` folder plus a
self-contained `.seq`. It's also the first live observation of **the camera-ownerless case**: with
no `LoadSFX{UseCamera=True}` ever called, `SFXDataCamera.currentCameraEngine` never leaves `NONE`
and the plain default battle camera runs the entire cast (recon `camera_verdict`) -- this rung
deliberately omits `PlayCamera`/`ResetCamera` too (see "Open risks," below).

## Design decision: reused id 84, not a second fresh id

PLAN.md's rung 6 wording ("id N with a trivial .seq") could be read as calling for a *second*
stock-unclaimed folder distinct from rung 3's 84. The orchestrator chose instead to **swap id 84's
content** for the bare sequence -- recast-only, no relaunch, no redeploy. Rationale: the fresh-id
*half* of rung 6's claim (a stock-unclaimed folder id resolves gracefully end-to-end) was already
fully proven by rung 3 (★★ 2026-07-21, both casts: verbatim copy + the hot-added chime). What rung 6
actually adds is the *no-native-content* half, and that only requires changing what's **in** the
folder, not minting another one. It also keeps the whole rung-3/5/6 lineage inside one bench folder,
consistent with the mod-folder shadowing law (`deploying-ff9-mods` skill): `.seq` content is
zero-cache, re-read per cast, so switching id 84 between "verbatim Bahamut copy" (rung 3), "+
particle" (rung 5), and "fully bare" (this rung) is always a pure recast.

## The bare sequence (`bare_player_sequence.seq`)

**100% hand-authored, COMMITTED in the repo** -- the one departure from every other `.seq` this
study has touched, all of which are Square-Enix-derived copies/edits and are therefore *never*
committed (see `rung3-fresh-id/build_rung3.py`, `rung5-particles/build_rung5.py`'s own PROVENANCE
sections). This file's *content* -- which lines appear, in what order, doing what -- was composed
fresh from the recon's own protocol/content split, not copied from any stock file. Its individual
*tokens* (`WaitAnimation`, `Anim=MP_CHANT`, `EffectPoint`, ...) are the `.seq` DSL's own vocabulary
and stock animation-clip names -- no more copyrightable expression than a TOML key.

**25 operation lines**, composed by keeping the recon's "protocol" half (content-independent DSL
plumbing every stock magic/summon cast shares) and deleting its "content" half (every
Bahamut-specific `LoadSFX`/`PlaySFX`/`WaitSFXLoaded`/`WaitSFXDone` line) outright:

```
WaitAnimation: Char=Caster
Message: Text=[CastName] ; Priority=1 ; Title=True ; Reflect=True
SetupReflect: Delay=SFXLoaded
PlayAnimation: Char=Caster ; Anim=MP_IDLE_TO_CHANT
WaitAnimation: Char=Caster
PlayAnimation: Char=Caster ; Anim=MP_CHANT ; Loop=True
Channel
SetBackgroundIntensity: Intensity=0.5 ; Time=12
PlaySound: Sound=100000
CreateVisualEffect: Char=Caster ; SFXModel=Data/SpecialEffects/ef084/RisingRing.sfxmodel
Wait: Time=90
WaitAnimation: Char=Caster
StopChannel
PlayAnimation: Char=Caster ; Anim=MP_MAGIC
WaitAnimation: Char=Caster
SetBackgroundIntensity: Intensity=1 ; Time=12
Wait: Time=12
EffectPoint: Char=AllTargets ; Type=Effect
Wait: Time=12
EffectPoint: Char=Everyone ; Type=Figure
ActivateReflect
WaitReflect
PlayAnimation: Char=Caster ; Anim=Idle
Turn: Char=Caster ; BaseAngle=Default ; Time=5
WaitTurn: Char=Caster
```

### What's kept, and why (all content-independent per the recon's source trace)

- **`WaitAnimation`/`Message`/`SetupReflect`** -- the cast-name banner + the reflect-thread setup.
  `SetupReflect`/`ActivateReflect`/`WaitReflect` are kept even though this ability's category (22,
  matching Bahamut's) clears the reflectable bit and makes them functionally inert here (recon
  `reflect_verdict` traces `CheckReflec`'s very first guard, `AbilityCategory & 1`, returning 0
  immediately) -- zero cost to keep, matches every stock convention, future-proofs against a
  category change.
- **The chant animation cycle** (`MP_IDLE_TO_CHANT` → `MP_CHANT` loop → `MP_MAGIC`) -- the caster's
  own skeletal clips; no summon creature ever appears, by design (that's the whole point of "bare").
- **The closing idiom** (`PlayAnimation Idle` / `Turn BaseAngle=Default` / `WaitTurn`) kept
  **verbatim**, not because it looks nice but because `Anim=Idle` is the engine's own recognized
  signal to release the command's motion lock (`UnifiedBattleSequencer.cs:505-516` →
  `btl_mot.EndCommandMotion`) -- recon `caster_animation_closeout` traced that dropping it would
  leave `cmd.info.cmd_motion` stale until the next `CMD_DATA` slot reuse. Not purely cosmetic.

### What's dropped, and why (all verified safe-to-drop by source trace, none previously exercised)

- The `CasterRow==0` step-forward/step-back `StartThread`s -- pure back-row repositioning, irrelevant
  to a stationary caster with no melee-adjacent framing need.
- The `IsSingleSelectedTarget` face-target `Turn` -- this ability targets `AllEnemy(8)` and its
  `EffectPoint` lines use `Char=AllTargets`/`Everyone`, never a single faced target.
- The `cmd_status` cursor-hide/-show `SetVariable` pair -- traced (recon `cmd_status_verdict`) to a
  pure UI toggle (`ModelButton.cs:25` / `battle.cs:225`, on-screen targeting-reticle visibility only)
  with **zero** read anywhere in completion/damage logic. Cosmetic-only; safe to add back for polish.

**None of rungs 1-5 exercised omitting these** -- their absence here is reasoned from source, not
previously observed live. Watch for it (see "Open risks").

### The two deliberate content choices worth flagging

- **`SetBackgroundIntensity: Intensity=0.5`, not `0`** -- a partial dim, not a full blackout, purely
  stylistic. It has nothing to do with the FIGURE-VISIBILITY LAW below -- that law's application
  point is scheduled entirely separately, after the *full* brightness restore.
- **`PlaySound: Sound=100000`** (bare form) -- rung 3's already-proven chime cast used the fuller
  `PlaySound: Sound=100000 ; SoundType=SoundEffect ; Volume=1.0`. The recon composed rung 6's line
  with just `Sound=`, presumably relying on engine defaults for `SoundType`/`Volume`; this exact
  minimal form has **not** been cast before. If the chime is silent on this rung's cast (see failure
  modes), rung 3's fuller-args form is the documented fallback -- swap the one `PlaySound` line in
  `bare_player_sequence.seq` and rerun `build_rung6.py --bare`.

### The FIGURE-VISIBILITY LAW (from rung 4) -- respected by construction

Rung 4 minted the law that a `Type=Figure` damage-number popup rendered while
`SetBackgroundIntensity=0` is still in effect gets washed out (not a crash, just invisible). This
sequence schedules both `EffectPoint` lines *after* `SetBackgroundIntensity: Intensity=1 ; Time=12`
(the full-brightness restore) plus an additional `Wait: Time=12` settle -- by the time either
`EffectPoint` fires, the scene has been fully lit for a full 12-tick beat. The damage number should
be plainly visible.

### `ef084/Sequence.seq` is never read

Rung 3's private copy of the donor's nested inner-choreography file (`ef084/Sequence.seq`) still
sits on disk (a leftover from rung 3's own build) -- but a `.seq` with no `LoadSFX` line never
triggers the nested load that would read it (`SFXDataMesh.ModelSequence.Load`, only reachable from a
`LoadSFX`/`PlaySFX` case). This rung's bare sequence has no such line, so `ef084/Sequence.seq` is
100% inert dead weight for this test -- present, harmless, unreferenced.

## Test procedure

The game is **already running** with the bench save loaded. No relaunch, no redeploy -- this is a
**single recast test**.

1. `py studies/custom-summons/rung6-bare-sequence/build_rung6.py --bare` (already run this session --
   the override is live; re-running is safe/idempotent). Confirms: `ef084/PlayerSequence.seq` = the
   25-line bare sequence; `ef084/RisingRing.sfxmodel` deployed (byte-identical to rung 5's own repo
   copy); `ef227` (shared donor) and the rung-2 chime manifest both untouched.
2. In-game: get back into a battle on field 30300 (walk around for the random encounter, or leave and
   re-enter if not already mid-fight).
3. Select **Iviv → Spark → Bahamut Cinema** (same command as every prior rung).
4. Watch the full cast play out (see "Expected experience," below).

## Expected experience (beat-by-beat, from the recon)

~9-10s total at the bench's live `BattleTPS=15` (matches rungs 1-5's own bench):

1. **(t=0, instant)** Select the command. The `[CastName]` title banner ("Bahamut Cinema") pops;
   `SetupReflect` resolves inert immediately (category 22, non-reflectable) -- imperceptible.
2. **(t~0-0.3s)** Caster plays the brief `MP_IDLE_TO_CHANT` transition, settles into the `MP_CHANT`
   loop pose.
3. **(t~0.3-0.9s)** Background begins dimming to 50% over 12 ticks (~0.8s) -- **not** a full
   blackout, the scene stays readable. The bare `Channel` op's baseline aura appears (the pale
   gray-blue-white glow -- `cmd_no=46` still falls through to the `Spell` case, per rung 5's own
   Channel-baseline finding).
4. **(t~0.3s, same tick as the dim starts)** The minted 880Hz chime (`PlaySound: Sound=100000`)
   plays immediately, and the magenta `RisingRing` sprite begins its ~2.4s fade-in/expand/rise/
   fade-out cycle layered additively over the baseline aura -- both plainly visible against the
   50%-dimmed (not black) background.
5. **(t~0.9-6.9s)** The caster holds the chant pose for the ~6s `Wait` window; the ring completes and
   vanishes on its own partway through (self-terminating -- no stop op needed); the chime has
   already finished; nothing else happens on-screen until the hold ends.
6. **(t~6.9s)** `WaitAnimation` resolves at the next `MP_CHANT` loop-wrap (near-instant, bounded to
   one loop cycle); `StopChannel` kills the baseline aura; caster plays the one-shot `MP_MAGIC` cast
   gesture, fully awaited.
7. **(t~7-8.5s)** Background ramps back to full brightness over 12 ticks (~0.8s), then an explicit
   12-tick wait (~0.8s) lets it finish fully lighting before anything else fires -- the scene is
   unambiguously LIT for what follows.
8. **(t~8.5s)** `EffectPoint Type=Effect` fires: damage is computed and applied against every enemy
   target -- HP bars drop, hit/miss/crit voice barks as normal, entirely under full brightness.
9. **(t~8.5-9.3s)** A further 12-tick gap (~0.8s), then `EffectPoint Type=Figure` fires: the
   damage-number popups render over each hit target, fully visible (no whiteout/occlusion).
10. **(t~9.3s)** `ActivateReflect`/`WaitReflect` resolve same-tick, imperceptibly (nothing was ever
    flagged to reflect).
11. **(t~9.3-9.6s)** Caster plays `Idle`, turns back to `Default` facing (5-tick turn, ~0.3s),
    `WaitTurn` releases the command -- Iviv should be immediately controllable again next turn; the
    menu/ATB resume normally with no lingering "still in a command" state.

Net: a fully graceful, self-contained cast -- animation in and out, custom sound, custom particle, a
lit and readable damage beat -- built from zero native summon content and zero `LoadSFX` of any kind.

## Failure modes (most to least informative)

| Symptom | Meaning |
|---|---|
| Full graceful cast per "Expected experience" above | **SUCCESS** -- Tier 3's no-native-content half is proven; the bare sequence is a viable summon-class command shape |
| Caster animates + chime/ring play, but **damage never lands** (no HP change, no hit numbers) | The most informative partial failure. `EffectPoint: Char=AllTargets ; Type=Effect` didn't apply damage -- means the recon's `effectpoint_from_player_file` finding (EffectPoint is thread-source-agnostic, works identically on a top-level PlayerSequence.seq thread, not just a nested SFX thread) was **wrong**, or a targeting mismatch (`Char=AllTargets` resolved to nobody). Re-check the deployed file (see "Verify," below); if it's correct, this is a genuine new discovery worth its own recon pass |
| Everything plays, but the caster **stays stuck chanting / control never returns** | The completion-analysis finding was wrong (recon `completion_verdict`) -- see "In-battle recovery," below, before assuming a hard hang |
| Chime is silent | Likely the bare `PlaySound: Sound=100000` form (no `SoundType=`/`Volume=`) doesn't behave like rung 3's fuller-args proven form -- swap in `PlaySound: Sound=100000 ; SoundType=SoundEffect ; Volume=1.0` and rerun `build_rung6.py --bare`. Could also be a manifest regression -- verify the chime row is still present (see "Verify") |
| Ring/chime play but nothing else looks different from a silent no-op cast | Distinguish from a genuinely broken cast: if the caster still animates in/out and control returns cleanly, the cast completed fine -- it's specifically the particle/sound that's the issue (see the chime/ring rows above) |
| Cinematic doesn't play at all / thread parsing appears to break outright | Something in the 25-line file is malformed enough to break the DSL parser -- revert immediately (`revert_rung6.py`) and re-diagnose; re-check the deployed file's line-by-line syntax against the "Verify" command below |
| Game crashes or hard-locks on cast | Treat as a genuine new discovery (a bare, no-LoadSFX summon-class sequence has zero prior in-game exercise anywhere in this study) -- capture a `tools/game_snap.ps1` frame if the window is still responsive, then revert (`revert_rung6.py`) |

### In-battle recovery, if the cast never completes

Per the recon's `completion_verdict` (traced end-to-end against `ExecuteLoop`/`CheckCommandLoop`/
`ReqFinishCommand`/`FinishCommand`), a bare sequence with no `LoadSFX` has **no** hidden implicit
wait on a never-loaded SFX -- `isOver` is driven purely by "all threads drained," and this file's
last op (`WaitTurn`) is a normal, always-resolving wait. If this analysis is nonetheless wrong and
the caster genuinely never regains control:

- **Can the battle still be won/fled?** The stuck actor's own command never finishes, but nothing in
  this analysis suggests the *battle system* itself would hang -- other party members should still
  be able to act on their own turns, and a Flee/Fight resolution on the rest of the party should
  still be reachable. This has **not** been tested; if a genuine hang occurs, note whether the other
  two party members can still act, as the first diagnostic fact to capture.
- **Debug-menu escape hatch**: the in-game debug menu (`~` tilde) has cheats/warp tools that may be
  able to force past a stuck command state (e.g. a warp away from the fight) -- try before assuming a
  full restart is needed.
- **Worst case**: a full game restart, then `py studies/custom-summons/rung6-bare-sequence/
  build_rung6.py --restore` before re-entering the field, to guarantee the private folder is back to
  rung 3's known-good verbatim baseline.

### Verify the override actually landed (if anything looks off)

```
py -c "print(open(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Data\SpecialEffects\ef084\PlayerSequence.seq').read())"
```

should print exactly the 25-operation-line file quoted above (plus the header/footer comments), with
NO `LoadSFX`/`PlaySFX`/`WaitSFXLoaded`/`WaitSFXDone` line anywhere. Also confirm the sprite:

```
py -c "print(open(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Data\SpecialEffects\ef084\RisingRing.sfxmodel').read())"
```

and the chime manifest row (should still contain `rung2chime`/soundIndex `100000`):

```
py -c "
import re
t = open(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\FF9_Data\EmbeddedAsset\Manifest\Sounds\SoundEffectMetaData.txt').read()
print(re.search(r'rung2chime[^}]*', t).group())
"
```

## Open risks

- **`PlayCamera`-without-`LoadSFX` remains genuinely untested.** This rung deliberately omits
  `PlayCamera`/`ResetCamera` entirely -- the recon flagged (`camera_verdict`) that
  `SFX.SetCameraTarget`/`SetEnemyCamera` unconditionally flip `SFXDataCamera.currentCameraEngine` to
  `SFX_PLUGIN` and start driving the native plugin's per-frame camera update even if `SFX_Play`
  (normally only invoked via `LoadSFX`) was never called -- an unverified interaction. Rung 6
  answers "what does a camera-ownerless bare effect look like" (the plain default battle camera, no
  cinematic cut), **not** "is `PlayCamera` safe without `LoadSFX`" -- that question is deferred to a
  dedicated future probe before rung 9 (epic camera) ever calls `PlayCamera` on a bare effect.
- **The four dropped protocol lines (two `StartThread` blocks + the face-target `Turn` + the
  `cmd_status` pair) are asserted safe-to-omit from source reasoning alone** -- no prior rung
  exercised omitting them. If anything about the reticle, back-row positioning, or facing looks
  visually off during this cast, that's the first place to look.
- **The bare `PlaySound: Sound=100000` form (no `SoundType=`/`Volume=`) is unproven** -- rung 3's
  proven working chime cast used the fuller three-arg form. If the chime is silent, that is the
  single most likely explanation (see the failure-mode table); the fix is a one-line edit in
  `bare_player_sequence.seq`.
- **The exact real-world length of the post-chant `WaitAnimation: Char=Caster`** (the loop-boundary
  safety line before `StopChannel`) depends on Iviv/Zidane's own `MP_CHANT` clip's frame count, not
  looked up -- bounded to at most one loop cycle, but the precise delay is unmeasured and could shift
  the ~9-10s total estimate by up to one chant-loop length.
- **In-battle recoverability if the cast never completes has not been tested** -- the "In-battle
  recovery" section above is reasoned from source (`completion_verdict`), not observed. If a hang
  does occur, the first-ever data point on it should be captured carefully (game_snap.ps1 + which
  recovery path worked, if any).

## Provenance

`bare_player_sequence.seq` (this directory) is **100% hand-authored text** -- zero Square-Enix bytes,
zero derivation from any stock `.seq` file's *content* (only its DSL vocabulary and stock
animation-clip names, neither of which is copyrightable expression) -- and **is committed**, exactly
like `rung5-particles/rung5_sprite.sfxmodel`. This is the one rung in the study so far whose
`PlayerSequence.seq` deploy is fully our own text rather than an edited Square-Enix copy.
`build_rung6.py` is nonetheless still the committable source of truth for the *deploy* (it re-derives
the mod-folder file from this repo copy every run, verifies the write, and separately sha-guards the
stock `ef227/PlayerSequence.seq` donor read for `--restore`'s drift check) -- the same convention
every prior rung's build script follows.

The reused sprite (`RisingRing.sfxmodel`) is rung 5's own committed content
(`rung5-particles/rung5_sprite.sfxmodel`), read directly from that sibling directory and redeployed
to this rung's `ef084/RisingRing.sfxmodel` path -- not duplicated into this directory.

## Revert

```
py studies/custom-summons/rung6-bare-sequence/revert_rung6.py
```

or equivalently:

```
py studies/custom-summons/rung6-bare-sequence/build_rung6.py --restore
```

Both restore `ef084/PlayerSequence.seq` to a pure byte-identical copy of stock
`ef227/PlayerSequence.seq` (rung 3's own baseline -- no bare-sequence content) and delete the
deployed `ef084/RisingRing.sfxmodel`, if present. Neither touches `ef084/Sequence.seq` (rung 3's
file, never written or read by this rung), `ef227/` (the shared donor -- untouched by this rung
in the first place), the rung-2 staged chime, or either repo copy of `rung5_sprite.sfxmodel`
(rung 5's committed content, reused here verbatim).
