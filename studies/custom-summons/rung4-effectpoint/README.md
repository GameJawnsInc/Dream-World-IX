# Custom Summons -- rung 4: the `EffectPoint` relocation probe

> Ladder position: `studies/custom-summons/PLAN.md` §5, rung 4 of 9.
> Depends on rung 1 (★ in-game proven 2026-07-21) -- the same bench, field **30300**, Iviv's
> minted **Spark → Bahamut Cinema** ability -- and on rung 3's nested-load law (`vfx1=84`, the
> private `ef084/` folder, still armed and untouched by this rung).

## What this proves

With the game **already running**, **no relaunch, no redeploy**:

1. **The NESTED `.seq` load is mod-stacked and cache-free, exactly like the outer one.**
   `ef227/PlayerSequence.seq`'s `LoadSFX: SFX=Bahamut__Full ; ...` line resolves the name
   `"Bahamut__Full"` to effect id **227** (`BattleActionCode.cs`'s `Enum.Parse` chain -- by the
   RESOLVED id, never the caller's own folder id, per rung 3) and loads
   `Data/SpecialEffects/ef227/Sequence.seq` via the identical `AssetManager.LoadString` path rung 2
   proved for the outer file (`SFXData.cs:156-181,233-242` -> `AssetManager.cs:487-539,650-656` --
   `FolderHighToLow` walk, first match wins, bare `File.ReadAllText`, zero cache). A mod-folder copy
   at `FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef227/Sequence.seq` therefore wins over the
   base game's file on every single cast, no `~`, no relaunch.
2. **`EffectPoint` -- the actual damage trigger -- can be moved anywhere in the timeline** and the
   rest of the cinematic keeps playing unmodified around it. `BattleAction.ExecuteLoop`
   (`UnifiedBattleSequencer.cs:1194-1345`) only checks "are all threads drained" -- there is no HP or
   death check anywhere in that loop, so an early kill from a relocated `EffectPoint` does not skip,
   cancel, or shorten anything downstream.

## The exact edit

Applied to a fresh copy of the stock `ef227/Sequence.seq` (73 lines) by `build_rung4.py` -- never to
the base game's own file. **Move**, not copy -- the two lines vacate their old slot:

```diff
@@ opening blackout (old line 5) @@
 ShowMesh: Char=Everyone ; Enable=False ; IsDisappear=True
+EffectPoint: Char=AllTargets ; Type=Effect
+Wait: Time=12
+EffectPoint: Char=Everyone ; Type=Figure
 StartThread: Condition=SFXUseCamera && AreTargetsPlayers
 	ShiftWorld: Angle=(0, 180, 0)
 EndThread

@@ mid-flare, ~32.4s in (old lines 63-65) @@
 Wait: Time=52
-EffectPoint: Char=AllTargets ; Type=Effect
-Wait: Time=12
-EffectPoint: Char=Everyone ; Type=Figure
 Wait: Time=18
 SetBackgroundIntensity: Intensity=1 ; Time=12
```

Both `EffectPoint` lines move **together** -- the stock 12-tick internal gap between "compute the
hit" (`Type=Effect`) and "show the number" (`Type=Figure`) is preserved verbatim. Moving only one
would either strand the damage-number popup ~31 real seconds after the actual hit (with an entire
flare cinematic playing in between), or decouple a pair nothing requires decoupling.

The two flanking `Wait` lines that used to sandwich the block (`Wait: Time=52` before,
`Wait: Time=18` after) become directly adjacent and are **not otherwise touched** -- they still sum
to the original 82-tick gap between the flare-ramp line and the lights-back-on line, so every beat
from the flare onward still fires at its stock absolute tick. Only the beats strictly *between* the
new position (tick 18) and the old one (tick 486) -- four `PlaySound` roar/chant clusters and two
intermediate flash beats -- shift later by a uniform **+12 ticks (~0.8s** at the user's live
`BattleTPS=15`), an imperceptible stretch and not the thing under test.

**Why move EARLY, not late:** the recon evaluated a tail placement (after the final `ShowMesh`/`Wait`
lines) and rejected it -- a tail move only shifts the beat by 2-4 real seconds relative to its
current mid-flare position, a subtle change that doesn't exercise the early-kill/truncation question
this rung is actually built to answer. Moving to the *opening blackout* is the maximally legible
version of the same probe: damage lands, and the kill/no-kill outcome is decided, **before Bahamut is
even visually summoned** -- an unmistakable inversion of the expected order (numbers before the
spectacle) that also can't be explained away as "I just didn't notice the earlier timing."

## Test procedure

The game is **already running** with the bench save loaded. No relaunch, no redeploy.

1. `py studies/custom-summons/rung4-effectpoint/build_rung4.py`
2. In-game: get back into a battle on field 30300 (walk around for the random encounter, or leave
   and re-enter if you're not already mid-fight).
3. Select **Iviv → Spark → Bahamut Cinema** (same command as rungs 1-3).
4. **Expect to see:** damage lands (HP change / damage number, and if the target dies, the
   death reaction) **almost immediately after the screen cuts to black** -- roughly 1.2 seconds in,
   well before any roar, flash, or the Bahamut reveal. Everything else -- the chant, the flashes, the
   flare, the reveal, the closing fade -- still plays out afterward, essentially unchanged (shifted
   by an imperceptible ~0.8s), *regardless of whether the target already died*.
5. This is a strong, single-viewing proof specifically because the order is inverted from every
   prior rung: the damage beat now visibly precedes the spectacle it used to interrupt, instead of
   the reverse.

## Verifier addendum: a background-intensity side effect the recon didn't check

Adversarial re-derivation (source-cited, not yet in-game confirmed) found a THIRD interaction the
recon's `open_risks` and this README's failure-mode table don't cover, alongside the two already
listed below. It doesn't touch the mechanism under test, but it likely means "the rest of the
cinematic plays out essentially unchanged" is **not quite right** around the "lights back on" beat:

`SetBackgroundIntensity`'s `HoldDuration` (`UnifiedBattleSequencer.cs:1030-1043`) is **not** paced by
the `.seq` file's own `Wait` lines -- each call spawns a `SequenceBBGIntensity` that free-runs on its
own `frameCur`/`frameEnd` counter, ticked once per game frame by `SequenceBBGIntensity.Apply(true)`
(`:1619-1647`), called once per `UnifiedBattleSequencer.Loop()` -- i.e. the *same* per-frame clock as
the main thread's `Wait` countdown, just tracked independently per intensity call. Multiple active
entries combine via **`min`** (`bbgimin`, since `nf_GetBbgIntensity() <= 128` here), not
last-writer-wins.

Walking the stock file's own cumulative `Wait` sums confirms the numbers this rung's own docs cite
(the block sits at absolute tick 486, `SetBackgroundIntensity: HoldDuration=82` fires at tick 434) --
and shows a byte-for-byte match: stock's flare-ramp entry (`Wait=12` ramp + `70`-frame hold =
`HoldDuration=82`) is timed to finish its hold **exactly** on tick 516, the same tick the *next*
`SetBackgroundIntensity: Intensity=1` (the "lights back on" cue) fires -- a clean, no-overlap handoff
that only holds because `52 (Wait) + 12 (the EffectPoint pair's internal Wait) + 18 (Wait) == 82`.

This rung's edit relocates that internal `Wait: Time=12` away from between those two flanking Waits.
Per the net-zero-shift math above, the *next* `SetBackgroundIntensity` (tick 516) still fires at the
same absolute tick post-edit -- but the flare-ramp's *own* hold-duration lifecycle, which starts when
*its* `SetBackgroundIntensity` line executes, is delayed the full **+12** ticks along with everything
else upstream of the old removal site (line 61 now fires at tick 446, not 434; its hold now ends at
528, not 516). The two entries now overlap for ~12 ticks (tick 516-528, ~0.8s at `BattleTPS=15`): the
old entry is still holding at its dim value (`min` wins) while the new entry tries to ramp toward full
brightness. Depending on exact same-frame add/remove ordering in `SequenceBBGIntensity.Apply` (not
traced to the exact frame here -- would need either a mini-simulation of the full per-frame update
order or an actual recast to pin down), the visible effect ranges from "a barely-noticeable ~0.8s
freeze before the screen brightens" to (in the worst single-frame-coincidence case, since the new
ramp's own 12-tick duration also ends on tick 528) "the background never gets a frame where `min`
resolves to the brightened value once both entries expire, and stays dimmed for the remainder of the
cinematic" (nothing in `ef227/Sequence.seq` calls `SetBackgroundIntensity` again after this line).

**Watch for it independently of the EffectPoint proof**: after the recast, once the "lights back on"
beat should fire (now falling in the middle of the shifted flare/roar cluster rather than at its own
distinct moment), check whether the screen actually reaches full brightness, or stays dim/washed for
the rest of the cinematic. This is orthogonal to whether the damage-relocation proof itself succeeds
(that reads on the FIRST ~1.2s, entirely before this interaction is even in play) -- it's a
possible-but-unconfirmed side effect of the *specific* relocation target chosen, not of the
nested-load/no-cache mechanism itself.

## Failure modes (most to least informative)

| Symptom | Meaning |
|---|---|
| Damage lands near the START of the cinematic (right after the blackout), cinematic still plays out fully afterward | **SUCCESS** -- rung 4 closed: nested `.seq` override + no-cache re-parse + `EffectPoint` relocation + the no-truncation-on-early-kill claim all proven |
| Screen stays dim / never fully brightens again after the point where "lights back on" should fire, or briefly freezes darker before snapping bright | Matches the verifier addendum above -- a `SetBackgroundIntensity`/`HoldDuration` timing overlap from relocating the block, unrelated to the EffectPoint/damage proof itself. Worth noting but does NOT invalidate the rung's actual claims (re-run `revert_rung4.py` regardless before leaving the bench either way) |
| Damage still lands at the OLD beat (mid-flare, same as rung 1) | The single most informative failure -- either the nested load isn't mod-stacked/cache-free the way the recon claims for THIS install/build (re-run `build_rung4.py` and check its printed diff/hashes -- did the override actually land at `FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef227/Sequence.seq`?), or `SFXData`/`SFXRework` caches the loaded `Sequence.seq` per-effect-id somewhere the recon's source read missed. Distinguishing check: if the file on disk (see "Verify" below) shows the edited content but the OLD beat still fires, that is a genuine caching discovery worth its own recon pass -- don't just assume a typo. If the file on disk is still the UNEDITED stock text, the override never landed (a build/deploy problem, not a caching one) |
| Cinematic is CUT SHORT or freezes when the target dies from the early hit | The truncation/early-kill safety claim is wrong for this engine build -- contradicts the direct read of `BattleAction.ExecuteLoop`'s completion check (thread-drain only, no HP check); worth a fresh source pass before assuming the recon's citation is stale |
| Cinematic doesn't play **at all** anymore (regression from rung 1/3) | Something is malformed enough to break thread parsing (e.g. an `EndThread`/`StartThread` pairing got disturbed by the edit) -- revert immediately (`revert_rung4.py`) and re-diagnose; this would mean the edited file broke, not that "it isn't proven" |
| Damage-number popup (`Type=Figure`) appears **detached** from the HP change (`Type=Effect`) by an unexpected gap | Shouldn't happen -- both lines move as one 3-line block with the internal `Wait: Time=12` untouched; if this is seen, diff the deployed file (see "Verify") against this README's edit spec for a stray line reordering |

### Verify the override actually landed (if anything looks off)

```
py -c "print(open(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Data\SpecialEffects\ef227\Sequence.seq').read())"
```

should show the `EffectPoint` pair as the file's 3rd/4th/5th lines (right after the leading comment,
blank line, and the opening `ShowMesh: Char=Everyone ; Enable=False` line), and **not** present
anywhere in the mid-file flare neighborhood (around `SetBackgroundIntensity: Intensity=0.6796875`).

## The shared-folder caveat

Rung 4 edits the **shared donor** id (`ef227` = `Bahamut__Full`'s inner `Sequence.seq`, used by every
stock cast of Bahamut, and -- per rung 3's nested-load law -- by this bench's `ef084` borrow too,
since `ef084/PlayerSequence.seq`'s `LoadSFX: SFX=Bahamut__Full` line resolves to the SAME real id
227, not to 84). Until this is reverted:

- **Vanilla Garnet/Eiko casting the real Bahamut** will also see damage land near the opening
  blackout instead of mid-flare.
- This is throwaway by design, the exact same documented class as rung 2's `PlayerSequence.seq`
  edit of the same donor folder. Don't leave rung 4's override in place past this proof.
- `ef084/` (rung 3's private copy, both its `PlayerSequence.seq` and its own `Sequence.seq`) is a
  **completely separate file on disk** and is never read, written, or touched by this rung -- the
  private folder's `Sequence.seq` sibling remains the proven-unused dead file rung 3's recon
  identified (the player path never reads it; only `ef227/Sequence.seq`, reached by name, does).

## Revert

```
py studies/custom-summons/rung4-effectpoint/revert_rung4.py
```

Removes the `.seq` override and the now-empty `ef227/` directory it created. `SpecialEffects/` itself
is left alone -- rung 3's `ef084/` still lives in the same parent on this bench and must survive.
Does not touch `ef084/`, the rung-2 staged chime, or `ef227/PlayerSequence.seq` (a different file;
rung 4 never writes it).

## Provenance

`build_rung4.py` is the **only** committable record of the edit: it reads the user's own stock
install, applies exactly the one relocation above, and writes the result straight into the live
`FF9CustomMap` mod folder -- never into this directory, never into git. The edited copy is
SE-derived content (a modified copy of Square-Enix's shipped file) and must never be committed; the
unified diff the script prints (reproduced above) plus this file are the durable documentation. The
script includes a **drift guard**: it refuses to run if the stock file's sha256
(`0452a785e90c206c21f5c9b5464310f6d73186fe001dfd12abf60eda292611d0` -- the same hash
`rung3-fresh-id/build_rung3.py` independently verified for this same file when it copied it
verbatim into `ef084/`) doesn't match what this script's edit was derived against, and further
refuses to guess if either anchor block (the `EffectPoint` pair to remove, or the
`ShowMesh`/`StartThread` pair marking the insertion point) doesn't appear in the file **exactly
once** -- rather than silently applying an edit against unknown or ambiguous content.
