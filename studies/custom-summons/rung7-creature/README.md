# Custom Summons -- rung 7: THE CREATURE RUNG

> Ladder position: `studies/custom-summons/PLAN.md` §5, rung 7 of 9 -- **the pillar's central bet,
> zero precedent anywhere: 0/487 stock effect folders, no known community use.**
> Depends on rung 1 (★ in-game proven 2026-07-21) -- the same bench, field **30300**, Iviv's minted
> **Spark → Bahamut Cinema** ability -- rung 3's private folder (`vfx1=84`, the `ef084/` folder,
> already deployed + relaunched once), rung 5's bespoke sprite (★ in-game proven, reused verbatim as
> `ef084/RisingRing.sfxmodel`), and rung 6's proven **bare sequence** (★★ in-game proven, both casts
> 2026-07-21 -- `rung6-bare-sequence/bare_player_sequence.seq`, read directly from that directory,
> never duplicated). Also depends on Iviv's `custom_battle_model` mint (GEO id 6100,
> `GEO_MAIN_B0_M100`) -- **already live in this exact mod folder every time Iviv fights** (rungs
> 1-6 proved it incidentally); this rung reuses that asset, copies nothing new.

## What this proves

That an effect folder's `FileList.txt` `Model <path>.sfxmodel` line -- an engine surface with
**zero prior exercise anywhere** (0 of 487 shipped `ef` folders use it; no community mod ever
found that has) -- can load a JSON manifest whose `FBX` entry goes through
`ModelFactory.CreateModel` (SFXDataMesh.cs:744, inside `SFXDataMesh.JSON.Begin()`) to render **our
own custom model pipeline's mesh mid-cast**, inside a live FF9 battle, driven entirely by a
`LoadSFX`/`PlaySFX` op pair in a `.seq` file. This is **the same loose-FBX loader the kit's proven
playable-character/custom-model pillar already uses** -- rung 7 is the first time it's ever been
reached through the SFX/summon system rather than the character-model system.

A clean cast closes the FBX half of **Tier 3** (PLAN.md §4): a fully composed *original* summon can
carry a genuinely custom creature, not just custom particles (rung 5, already proven) or a bare
donor-free choreography (rung 6, already proven). Route A of PLAN.md §3A ("managed bypass -- the
native `FF9SpecialEffectPlugin.dll` is never in the loop") goes from code-complete-but-untested to
in-game exercised.

## What asset renders, and why it's the right one for this rung

**Iviv's `custom_battle_model`, GEO id 6100 / `GEO_MAIN_B0_M100`** (from
`ff9mapkit/examples/thirteenth-character/iviv.field.toml`, `content/playable.py`'s mint mechanism).
Confirmed live on disk in this exact mod folder before this rung touched anything:
`FF9CustomMap/StreamingAssets/Assets/Resources/Models/2/6100/6100.fbx` (263,241 bytes) +
`Animations/6100/1010000.anim`..`1010033.anim` (34 clips) + the `DictionaryPatch.txt` lines
`3DModel 6100 GEO_MAIN_B0_M100` and 34 `3DModelAnimation` entries. It is a skinned, fully animated
model, ★★★ in-game proven every time Iviv fights across rungs 1-6 today -- the lowest-risk pick per
the study's own framing ("a model already loading in this very install"): **zero new asset files
were staged for this rung**, only a new `.sfxmodel` manifest + `FileList.txt` referencing it by its
already-registered GEO name.

Cosmetic caveat, already known: visually it's a palette-identical clone of vanilla Vivi's battle
model (no mesh edit was ever made to it), so this rung proves **the loader**, not "a visibly novel
creature" -- fine for the stated bar ("a placeholder mesh... renders mid-cast"), not the final-summon
asset. `ff9mapkit/examples/boletta/` (a wholly from-scratch mushroom-sprite creature, zero
FF9-derived data) is the documented fallback/upgrade path if a later rung wants unambiguous "this is
OUR creature" visual proof -- it is **not currently deployed** in this mod folder and was
deliberately not used here to avoid an unrelated extra deploy step.

## The mechanism, traced end to end (chain recon, source-verified against `C:\gd\FFIX\Memoria\Assembly-CSharp`, pinned commit 6b8bb2d5)

1. **`LoadSFX: SFX=84`** (a `.seq` op, numeric -- `TryGetArgSFX` parses `Int32` first,
   BattleActionCode.cs:189-194) calls `SFXData.LoadSFX(84, ...)`. This reads
   `ef084/FileList.txt` (`AssetManager.LoadString`, SFXData.cs:170-171), parses its one `Model
   creature_manifest.sfxmodel` line (`LoadSFXFromInfo`, SFXData.cs:244-279), and loads
   `creature_manifest.sfxmodel` as a `SFXDataMesh.ModelSequence` (SFXDataMesh.cs:901-949) -- pure
   JSON/text parsing, **no FBX instantiated yet**. Because `mesh != null` after this, `LoadSFX`
   returns immediately (`loadHasEnded=true; return;`, SFXData.cs:175-179) **before**
   `loadingQueue.Enqueue(this)` -- the native `FF9SpecialEffectPlugin.dll` is never in the loop for
   this SFXData, at any point in its lifecycle.
2. **`PlaySFX: SFX=84`** calls `SFXData.PlaySFX()`, which on an instance's first start calls
   `mesh.Begin()` (SFXDataMesh.cs:150-151) -- **this is where `ModelFactory.CreateModel(...)`
   actually fires** (SFXDataMesh.cs:744), synchronously, unbudgeted. This is the genuine
   in-battle load-hitch site (see "Open risks / watch items" below) -- placed inside the still-active
   `SetBackgroundIntensity=0` blackout specifically to mask it, the same trick native summons already
   use for their own setup cost.
3. **Path resolution is the one load-bearing non-obvious step.** `creature_manifest.sfxmodel`'s FBX
   `"Path": "GEO_MAIN_B0_M100"` gets folder-prefixed to `Data/SpecialEffects/ef084/GEO_MAIN_B0_M100`
   by the JSON loader (no `/` in the given string), but `ModelFactory.CreateModel` →
   `GetRenameModelPath` → `GetGEOID` (ModelFactory.cs:15-35,391-401) **discards that directory
   entirely** and re-derives the real disc path from only the FILENAME token, via the SAME
   `FF9BattleDB.GEO` reverse lookup the `3DModel 6100 GEO_MAIN_B0_M100` DictionaryPatch line already
   feeds for ordinary battle-model loading -- landing on `Models/2/6100/6100.fbx`, byte-identical to
   what's already deployed and already loading for Iviv's own battles. `ef084/`'s own folder never
   needs to physically contain the FBX.
4. **Every engine frame**, `BattleAction.Render()` (UnifiedBattleSequencer.cs:1347-1374) calls
   `sfx.mesh.Render(run.frame, run)` (`SFXDataMesh.JSON.Render`, SFXDataMesh.cs:776-884): positions
   the FBX GameObject from its `Movement` curve (`CasterPosition{X,Y,Z}` + a static offset, this
   manifest), samples its `Animations[0]` clip frame-by-frame via `AnimationState.time` (not
   Unity's normal auto-play), and reports `ended` once `frame > lastFrame` (=60, this manifest).
   `WaitSFXDone` polls exactly that; when it resolves, `BattleAction.Render()` removes the running
   instance and calls `sfx.mesh.End()` (`Object.Destroy` on the FBX GameObject) -- guaranteed
   cleanup either way, even if forced early by the sequence's own safety-net teardown.

## Design decisions (deviations from -- and additions to -- the recon's literal proposed line)

The chain recon's proposed `LoadSFX` line was `LoadSFX: SFX=84 ; Char=Caster ; Reflect=True`. This
build adds two things beyond that literal text, both reasoned from source read directly against the
pinned engine fork, both documented here per the task's "on contradiction pick the safer and say
so" instruction (neither is a contradiction between the two recon reports -- both are additions the
reports left as an open surface):

- **`UseCamera=False`, explicit.** Traced directly in `UnifiedBattleSequencer.cs`'s `LoadSFX` op
  case: absent a `UseCamera=` key, the engine computes a config-dependent default
  (`Configuration.Battle.Speed < 3 || ...`) that can resolve to `true` -- which would flip
  `SFXDataCamera.currentCameraEngine` to `SFX_PLUGIN` and start driving the native camera plugin
  live every frame (PLAN.md §3.5), **for an id with zero native `ef###.bytes` payload to feed it**.
  That is an untested interaction this rung has no reason to introduce alongside the one thing it's
  actually testing. `UseCamera=False` keeps the camera engine at `NONE` (rung 6's own proven
  "camera-ownerless" default -- the plain per-command battle camera runs the whole cast), isolating
  the FBX-loader bet as the sequence's only new variable.
- **An explicit `Movement` anchor on the FBX entry**, where the recon's own `recommended_asset`
  example omitted `Movement` entirely. The recon's own `sfxmodel_fbx_schema` section flags exactly
  why that's risky: omitting `Movement`/`Rotation`/`Scaling` leaves the model motionless at **WORLD
  ORIGIN** (`Vector3.zero`) -- "wrong place, not invisible." A world-origin creature would very
  likely render outside the default battle camera's frame, making a genuine mechanism SUCCESS
  visually indistinguishable from an off-camera silent no-op -- exactly the ambiguity a first proof
  test should avoid. This manifest instead anchors the model to `CasterPosition{X,Y,Z}` plus a
  static (`Origin == Destination`, no motion) forward+up offset -- matching the same NCalc
  vocabulary rung 5's own committed sprite already uses (`CasterPositionX/Y/Z`), and the same order
  of magnitude as stock's own `MoveToPosition RelativePosition=(0,0,400)` "step forward" idiom. The
  exact screen framing this produces is **genuinely unverified** -- see "Open risks," below.

Everything else in the sequence is **rung 6's own proven 25 lines, byte-identical, unchanged** --
see the diff `build_rung7.py --creature` prints against `rung6-bare-sequence/bare_player_sequence.seq`.

### `SkipSequence=True` -- the one non-obvious gotcha the chain recon's own pass surfaced

`SFXData.LoadSFX` unconditionally re-reads `ef084/Sequence.seq` (SFXData.cs:174) on **every**
`LoadSFX` call, regardless of the `FileList.txt`/JSON-mesh branch. `ef084/Sequence.seq` is still on
disk -- rung 3's leftover byte-identical copy of Bahamut's own real nested choreography (its own
`EffectPoint`/`PlaySound` timing). Absent `SkipSequence=True` on `PlaySFX`, that donor content would
get threaded in as a second, parallel, duplicate-damage thread the moment `PlaySFX` fires
(UnifiedBattleSequencer.cs:371-378). This build's `PlaySFX: SFX=84 ; Reflect=True ;
SkipSequence=True` line prevents it -- the cheaper of the recon's two documented fixes (the other
being to overwrite `ef084/Sequence.seq` itself, which this rung deliberately avoids touching).

## Files in this directory

| File | What it is |
|---|---|
| `FileList.txt` | Committed, 100% our text. The first-ever `FileList.txt` this study has written. |
| `creature_manifest.sfxmodel` | Committed, 100% our JSON. One `FBX` entry, Iviv's GEO 6100 by name. |
| `rung7_player_sequence.seq` | Committed, 100% our text -- rung 6's 25 lines (unchanged) + our 4-line quartet. |
| `build_rung7.py` | Deploys/restores all of the above under `ef084/`, sha-guarded, idempotent, diff-printing. |
| `revert_rung7.py` | Alias of `build_rung7.py --restore` (house convention). |

None of these three deploy sources are Square-Enix-derived -- unlike rungs 3/4's `.seq` files (never
committed, regenerated from the stock donor every run), rung 7's sources are committed outright,
exactly like rung 5's `rung5_sprite.sfxmodel` and rung 6's `bare_player_sequence.seq`.

## Test procedure

The game is **already running** with the bench save loaded (same convention as rungs 2-6). No
relaunch is needed for this rung -- `.seq`/`FileList.txt`/`.sfxmodel` are all zero-cache,
per-cast-reparsed, mod-folder-shadowed (the same law rungs 2-6 already proved for `.seq`, extended
here to `FileList.txt` and `.sfxmodel` for the first time). Iviv's GEO 6100 asset was already armed
at a prior relaunch (rung 1) -- nothing new needs registering.

1. `py studies/custom-summons/rung7-creature/build_rung7.py --creature` (already run this session --
   the deploy is live). Confirms: `ef084/FileList.txt` + `ef084/creature_manifest.sfxmodel` +
   `ef084/PlayerSequence.seq` (the 29-line rung-7 sequence) + `ef084/RisingRing.sfxmodel` all
   present and byte-verified; the GEO 6100 asset presence check reports **all four pieces OK**.
2. In-game: get back into a battle on field 30300 (walk around for the random encounter, or leave
   and re-enter if not already mid-fight).
3. Select **Iviv → Spark → Bahamut Cinema** (same command as every prior rung).
4. Watch the full cast play out (see "Expected experience," below) -- **this is a single-cast test.**

## Expected experience (beat-by-beat)

Rung 6's own proven ~9-10s opening is unchanged through the chant hold. Then, still inside the
existing blackout, a NEW beat: the creature reveal, held ~4s, before the re-light and damage beats.
Estimated total ~13-14s at the bench's live `BattleTPS=15`.

1. **(t=0 to ~6.9s)** Identical to rung 6: cast-name banner, chant animation cycle, background dims
   to full black (`Intensity=0`), the minted chime plays, the magenta `RisingRing` sprite does its
   fade-in/expand/rise/fade cycle -- all against the black void, all exactly as rung 6 already proved.
2. **(t~6.9s)** `WaitAnimation` resolves at the chant loop-wrap; `StopChannel`; caster plays the
   one-shot `MP_MAGIC` cast gesture, fully awaited -- identical to rung 6.
3. **(t~7-7.5s, NEW)** `WaitSFXLoaded` resolves same-tick (the FileList.txt/`.sfxmodel` parse
   already completed synchronously back at the `LoadSFX` op, long before this point) -- essentially
   imperceptible. `PlaySFX` fires: **this is the moment `ModelFactory.CreateModel` actually loads
   and instantiates Iviv's GEO_MAIN_B0_M100 FBX** -- a real, synchronous, unbudgeted cost (see "Open
   risks"), masked by the still-active blackout. The creature should pop into view against the
   black void, positioned near the caster (an offset anchored to `CasterPosition`), playing (or
   holding on the last frame of) its own idle animation clip.
4. **(t~7.5-11.5s, NEW, ~4s hold)** `WaitSFXDone` blocks the sequence thread here while the
   creature's own 60-frame render window plays out. The creature should be visibly present and
   animated (or held on a static idle pose) against the black void for this whole window -- **this
   is the actual proof beat**. Nothing else on-screen changes during this hold.
5. **(t~11.5s)** The creature's render window ends; `sfx.mesh.End()` destroys its GameObject
   (`Object.Destroy`) automatically -- it should simply disappear/vanish, not fade.
   `SetBackgroundIntensity: Intensity=1` begins re-lighting over 12 ticks (~0.8s).
6. **(t~12.3-13.1s)** An explicit 12-tick settle Wait lets the re-light finish fully before anything
   else fires -- identical structure to rung 6.
7. **(t~13.1s)** `EffectPoint Type=Effect` fires: damage lands on every enemy target, fully lit.
8. **(t~13.1-13.9s)** A further 12-tick gap, then `EffectPoint Type=Figure`: damage-number popups
   render fully visible (the FIGURE-VISIBILITY LAW, respected exactly as rung 6 established it --
   both `EffectPoint` lines fire only after the full re-light plus a settle beat).
9. **(t~13.9-14.2s)** Caster plays `Idle`, turns back to `Default` facing, `WaitTurn` releases the
   command -- Iviv should be immediately controllable again; no lingering "still in a command" state.

Net: everything rung 6 already proved, PLUS a genuinely new mid-cast beat -- our own custom model
pipeline's mesh, rendered live inside an FF9 battle effect, for the first time ever.

## Failure modes (per the chain recon's risk register -- CRASH-class vs NO-OP-class, most to least informative)

### CRASH-class -- a thrown C# exception at a specific, cited site

The chain recon traced (this rung's own pass) that **every** call site on both the update and
render loops is wrapped in a broad try/catch that only logs (`UnifiedBattleSequencer.Loop()`,
`BattleAction.Render()`, `SFXData.LoadSFXFromInfo`'s own inner try/catch, `SFXData.AdvanceEventSFXFrame`).
A thrown MANAGED exception here is caught, logged, and **the game continues** -- not a hard process
crash. The visible symptom is a soft, single-frame skip or a permanently-broken specific model/curve,
not a crash. This build was designed to avoid the one concretely-cited crash trigger (an FBX with no
`Animation` component but a non-empty `Animations` array -- `component.GetClip(animName)` on a null
component, SFXDataMesh.cs:747-753); Iviv's GEO 6100 is a real animated battle model, so this
shouldn't apply, but it's the first thing to suspect if something crash-like happens.

| Symptom | Falsifies | Recovery |
|---|---|---|
| The game hard-locks or the process crashes outright | The "every call site is try/catch-wrapped" finding, OR a native-level Unity crash from FBX data the managed try/catch can't intercept (the same class of risk the kit's existing proven custom-model pillar already carries -- nothing new to THIS rung specifically) | Capture a `tools/game_snap.ps1` frame if the window is still responsive; full game restart; `py studies/custom-summons/rung7-creature/revert_rung7.py` before re-entering the field |
| A single frame visibly stutters/skips once (creature doesn't appear, everything else continues normally) | Nothing load-bearing -- a caught-and-logged managed exception inside `Begin()`/`Render()`, per the try/catch structure above. Check the game's log for a stack trace if reachable | None needed -- the battle should complete normally; note it and move on |
| The creature partially loads (mesh visible, but frozen in a T-pose / bind pose instead of the idle clip) | The `Animations` clip resolution specifically (`AssetManager.Load<AnimationClip>` on `Animations/6100/1010000` failing silently -- a NO-OP-class outcome per the schema, not a crash, but worth distinguishing from full success) | None needed for completion; note it as a partial-success data point |

### NO-OP-class -- no exception, just wrong/missing visuals; the cast completes gracefully regardless

Every one of these is a genuine engine no-op per the recon's `risk_register` -- silently degrading,
never blocking sequence completion.

| Symptom | Meaning / falsifies | What to check |
|---|---|---|
| **Full graceful cast, creature clearly visible during the ~4s hold, per "Expected experience"** | **SUCCESS** -- Route A (FileList.txt/Model → our FBX pipeline) is proven in-game for the first time ever; Tier 3's FBX half is closed | -- |
| Everything else plays (chant, chime, ring, damage, closeout) but **no creature ever appears** during the ~4s hold | Most informative partial failure. Either (a) `FileList.txt`'s grammar didn't match (a stray tab/double-space -- re-check the deployed file's exact bytes, see "Verify" below), or (b) `ModelFactory.CreateModel` returned null (a resolution mismatch on `"GEO_MAIN_B0_M100"` -- re-verify the GEO-name reverse lookup this rung's own presence check already confirmed live), or (c) the creature rendered but at the WORLD-ORIGIN default because the `Movement` block didn't parse -- i.e. it's on-screen but far outside the camera frame, not truly absent | Re-run `build_rung7.py --creature` and read its "GEO 6100 asset presence check" block; re-check `FileList.txt`'s exact bytes (see "Verify") |
| The creature appears but is **badly mispositioned** (floating far off to one side, clipping through the caster, or only a sliver visible at the frame edge) | The `Movement` anchor's sign/offset assumptions were wrong -- a genuinely NEW discovery about the caster-position NCalc coordinate frame, not a mechanism failure. The loader itself still worked | Note the exact visual offset direction; the fix is a one-line edit to `creature_manifest.sfxmodel`'s `OriginZ`/`OriginY` sign or magnitude, then re-run `build_rung7.py --creature` |
| The creature appears **motionless in a T-pose/bind pose** rather than an idle animation | `Animations` clip resolution silently failed (`AssetManager.Load<AnimationClip>` on `Animations/6100/1010000` returned null) -- the FBX loader itself still succeeded; only the animation layer degraded. Distinguishes "our mesh renders" (proven) from "the anim-clip path also works" (a secondary claim) | Not a rung-7 blocker either way -- a static mesh mid-cast already meets the rung's own stated bar |
| The **chant/chime/ring beats look identical to rung 6**, but the post-MP_MAGIC hold is silently SHORTER or absent (no ~4s pause before the re-light) | `LoadSFX`/`PlaySFX`/`WaitSFXDone` never actually engaged -- possibly `mesh` stayed null (FileList.txt not read, or a JSON parse failure in `creature_manifest.sfxmodel`) and `LoadSFX` instead silently fell through to the NATIVE raw-mesh path for an `Unused_84` id with no real content (SFXData.cs:180, `loadingQueue.Enqueue`) -- a genuinely different, also-documented no-op mode | Re-check `creature_manifest.sfxmodel`'s exact JSON syntax (a stray trailing comma breaks `JSONNode.Parse` silently); re-run `build_rung7.py --creature` and re-verify all four presence-check pieces |
| Damage/`EffectPoint`/closeout behave exactly like rung 6, full success on everything EXCEPT the creature | Isolated to steps 3 in "the mechanism, traced end to end" -- everything upstream and downstream of the FBX load/render is confirmed working; the FBX-specific step alone is the failure surface | See the two rows above for the two most likely specific causes |
| Cast doesn't play at all / the `.seq` parser appears to break outright | Something in the 29-line file is malformed enough to break the DSL parser | Revert immediately (`revert_rung7.py`) and re-diagnose; re-check the deployed file's line-by-line syntax against "Verify," below |

### In-battle recovery, if the cast never completes

Per rung 6's own already-established `completion_verdict` reasoning (unchanged by this rung's
additions -- `WaitSFXDone`'s own polling logic, traced directly this session, resolves purely on
`sfx.runningSFX.Count > 0` going false, which `BattleAction.Render()`'s per-frame loop guarantees
eventually happens once `frame > lastFrame`; there is no scenario where it hangs forever short of a
genuine engine bug):

- **Can the battle still be won/fled?** Not specifically tested for this rung; rung 6's own
  reasoning (other party members should still be able to act on their own turns) is inherited
  unchanged.
- **Debug-menu escape hatch**: the in-game debug menu (`~` tilde) may be able to force past a stuck
  command state.
- **Worst case**: a full game restart, then `py studies/custom-summons/rung7-creature/revert_rung7.py`
  before re-entering the field, to guarantee `ef084/` is back to rung 6's own known-good bare state.

### Verify the override actually landed (if anything looks off)

```
py -c "print(open(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Data\SpecialEffects\ef084\FileList.txt').read())"
py -c "print(open(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Data\SpecialEffects\ef084\creature_manifest.sfxmodel').read())"
py -c "print(open(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Data\SpecialEffects\ef084\PlayerSequence.seq').read())"
```

The `PlayerSequence.seq` output should contain exactly one `LoadSFX`, `WaitSFXLoaded`, `PlaySFX`, and
`WaitSFXDone` line, all with `SFX=84`, plus every one of rung 6's own 25 lines unchanged. Re-running
`py studies/custom-summons/rung7-creature/build_rung7.py --creature` also re-prints the full GEO
6100 presence check (fbx/anim file existence + both DictionaryPatch.txt lines).

## Open risks / watch items (carried forward + new this rung)

- **THE IN-BATTLE LOAD HITCH is real and unmeasured.** `ModelFactory.CreateModel` at `PlaySFX` time
  is synchronous and unbudgeted (unlike the native path's genuinely amortized `LoadLoop()`); this
  build schedules it inside the blackout specifically to mask it, but whether that fully hides a
  possible frame stutter has not been observed live. Watch for it on the actual cast.
- **The `Movement` anchor's exact screen framing is genuinely unverified** -- see "Design decisions"
  above. If the creature is mispositioned rather than absent, that's the first tuning knob (a
  one-line edit to `creature_manifest.sfxmodel`).
- **The bare-form `Animations` entry (`{"Path": "Animations/6100/1010000"}`, no `Speed` key) is
  unproven** -- the asset recon flagged this as safe by source trace (defaults to `Speed=1.0`) but
  it has not been cast before. If the creature appears in a bind pose instead of animated, this is
  the first place to look.
- **Netsync freeze-ceiling question (PLAN §7/8) is unresolved and untouched by this rung** --
  `UnifiedBattleSequencer.Loop()` doesn't distinguish JSON-mesh content from native content, so this
  rung's ~4s added hold doesn't meaningfully change that open question either way.
- **`SFXRework=0` users get a silent no-op on this whole rung** (unchanged from every prior rung) --
  this bench's install has `SFXRework=1`.

## Provenance

`FileList.txt`, `creature_manifest.sfxmodel`, and `rung7_player_sequence.seq` (this directory) are
**100% hand-authored text/JSON** -- zero Square-Enix bytes. `creature_manifest.sfxmodel` references
Iviv's `GEO_MAIN_B0_M100` (id 6100) purely by its already-registered NAME, the same way any `.seq`
op references a stock resource by id/name; the underlying FBX itself is a KIT-MINTED clone (a
straight geometric/texture clone of Vivi's real battle model, produced by the kit's own
`content/playable.py`/`characterdelta.py` mint pipeline from the user's own game install --
governed by the SAME provenance rules as the rest of the `custom_battle_model` pillar, not a new
exception this rung introduces). `rung7_player_sequence.seq` is derived from rung 6's own committed
`bare_player_sequence.seq` (itself already zero-SE-bytes, PROVENANCE.md-clean) plus 4 wholly new
hand-authored lines -- no Square-Enix `.seq` content was read, copied, or edited to produce it.

## Revert

```
py studies/custom-summons/rung7-creature/revert_rung7.py
```

or equivalently:

```
py studies/custom-summons/rung7-creature/build_rung7.py --restore
```

Both restore `ef084/` to rung 6's own proven bare state: `FileList.txt` and
`creature_manifest.sfxmodel` removed, `PlayerSequence.seq` byte-identical to rung 6's committed
`bare_player_sequence.seq`. `RisingRing.sfxmodel` stays deployed (rung 6's own sequence still
references it). Neither touches `ef084/Sequence.seq` (rung 3's leftover, inert either way), `ef227/`
(the shared Bahamut donor -- untouched by this rung in the first place), the rung-2 staged chime, or
Iviv's GEO 6100 asset (verified-only, never this rung's to manage -- it's the bench's own
`[[playable]]` deploy's responsibility).
