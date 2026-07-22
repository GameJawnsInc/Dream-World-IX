# Custom Summons -- rung 2: the shared-folder `.seq` hot-edit probe

> Ladder position: `studies/custom-summons/PLAN.md` §5, rung 2 of 9 ("Hot-loop probe").
> Depends on rung 1 (★ in-game proven 2026-07-21) -- the same bench, field **30300**, Iviv's
> minted **Spark → Bahamut Cinema** ability (`vfx1=227`).

## What this proves

Three things, all with the game **already running**, with **no relaunch and no redeploy**:

1. **Mod-folder `.seq` override resolution.** `Data/SpecialEffects/ef227/PlayerSequence.seq` --
   the outer choreography script for the *stock* Bahamut cinematic -- is read through the normal
   stacked-mod-folder `AssetManager`, exactly like every other asset. A copy dropped at
   `FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef227/PlayerSequence.seq` wins over the base
   game's own file, because `FF9CustomMap` is index 0 (highest priority) in the live
   `Memoria.ini`'s `FolderNames` list.
2. **No cache -- a genuinely faster dev loop than `~`.** This file is re-parsed from disk on
   **every single cast** (`UnifiedBattleSequencer.BattleAction`'s constructor calls
   `AssetManager.LoadString` unconditionally; the one cache in this system,
   `BattleCommandInfo.SequenceFile` / `cmd.aa.Info.VfxAction`, never engages for a plain numeric
   `vfx1` ability like ours). So: edit the file, alt-tab back to the already-running game, recast --
   no `~` reload, no relaunch, no redeploy.
3. **A hand-inserted `PlaySound` line resolves and plays.** Proves the `.seq` DSL is genuinely
   authorable by hand from outside the engine.

## The exact edits

Both are applied to a fresh copy of the stock file by `build_rung2.py` -- never to the base game's
own file. Full before/after (only these two lines differ; everything else is a byte-exact carry of
the stock 36-line file):

**(a) Wait retime** -- the file's one *unconditional* numeric-`Time` tween (sits at the main thread
level, not inside either `StartThread` block):

```diff
-SetBackgroundIntensity: Intensity=0 ; Time=12
+SetBackgroundIntensity: Intensity=0 ; Time=45
```

+33 ticks at the user's live `Memoria.ini BattleTPS=15` ≈ **+2.2 seconds** slower dim-to-black,
right before the chant animation starts. (The file's other two numeric-`Time` lines -- a
`Turn:...Time=5` and a `MoveToPosition`/`MoveToPosition` pair -- both sit inside `StartThread`
blocks whose conditions are **false** for this bench's setup: Bahamut Cinema targets `AllEnemy(8)`,
not a single target, and the caster is a player, not an enemy. Editing those would silently do
nothing, so they're left untouched.)

**(b) PlaySound insertion** -- a brand-new first line, firing the instant the command starts,
before any animation:

```diff
 // Player sequence of SFX Bahamut__Full
 
+PlaySound: Sound=103 ; SoundType=SoundEffect ; Volume=1.0
 WaitAnimation: Char=Caster
```

`Sound=103` is the stock **"Menu Select"** blip (`Sounds02/SE00/se000001`,
`AudioResources.cs:235`) -- already registered, no minting, no relaunch needed to hear it.

## Test procedure

The game is **already running** with the bench save loaded. No relaunch, no redeploy.

1. `py studies/custom-summons/rung2-seq-hot-edit/build_rung2.py` (already run once this session --
   the override is live; re-running is safe/idempotent, see below).
2. In-game: get back into a battle on field 30300 (walk around for the random encounter, or leave
   and re-enter if you're not already mid-fight).
3. Select **Iviv → Spark → Bahamut Cinema** (same command as rung 1).
4. **Expect to hear:** a short UI "blip" (the Menu-Select sound) at the *very instant* the command
   fires -- before Iviv even starts the cast animation.
5. **Expect to see:** the screen dims to black noticeably more slowly than rung 1's proof run, right
   before the chant pose -- a beat that used to take ~0.8s (Time=12 @ 15 ticks/sec) now takes ~3.0s
   (Time=45). Everything else -- the chant, the Bahamut reveal, the real camera cut, the damage --
   plays exactly as in rung 1 (untouched).

## Failure modes (most to least informative)

| Symptom | Meaning |
|---|---|
| Blip fires AND the dim-to-black is visibly slower | **SUCCESS** -- rung 2 closed: mod-folder `.seq` override + no-cache re-parse + `PlaySound` injection all proven |
| **No change at all** on recast (plays exactly like rung 1) | The single most informative failure: either the mod-folder `.seq` override isn't being read (check `Memoria.ini FolderNames` still lists `FF9CustomMap` first, and that the file actually landed -- see "Verify" below), or the no-cache claim is wrong for this build. Re-run `build_rung2.py` and check its printed diff/hashes before assuming a code problem. |
| The **pause is longer** but there's **no sound** | The pause half of the mechanism works; the sound half needs its own investigation -- check `Memoria.ini [Audio] SoundVolume` isn't 0 (the script warns about this), and confirm you're not muted at the OS/game-window level. Does NOT falsify the `.seq`-override mechanism itself. |
| **Total silence / no visible change AND you're sure you're on the override** | Our inserted line was silently dropped by the parser -- the DSL drops any line whose op name doesn't byte-match `BattleActionCode.operationArguments` exactly (case-sensitive, no error, no log). Re-open the deployed file (`FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef227/PlayerSequence.seq`) and diff it against this README's "after" text above for a stray character/casing slip. |
| Bahamut cinematic doesn't play **at all** anymore (regression from rung 1) | Something is malformed enough to break thread parsing (e.g. an `EndThread` got disturbed) -- revert immediately (`revert_rung2.py`) and re-diagnose; this would mean the edited file broke, not that "it isn't proven". |

### Verify the override actually landed (if anything looks off)

```
py -c "print(open(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Data\SpecialEffects\ef227\PlayerSequence.seq').read())"
```
should show the `PlaySound` line as line 3 and `Time=45` about two-thirds down.

## The minted probe chime (Track B -- deployed, not yet wired in)

`build_rung2.py` also mints a wholly-synthetic sine-tone chime as a **new** SFX id (**100000**,
`Sounds02/SE00/rung2chime`) via the kit's own `sound.mint_song(..., kind="sfx")`. This is staged
into the live mod folder now (manifest row + `.ogg`), but **deliberately not referenced by the
`.seq` yet** -- `SoundMetaData`'s id table loads once at process start
(`SoundLib.LazyLoadSoundResources`'s one-shot latch), so a *brand-new registered id* cannot go live
on the already-running game no matter what the `.seq` says. The minted-audio-in-`.seq` question is
answered in full **after** the user's next relaunch (for any reason -- don't wait on this rung for
it): add `PlaySound: Sound=100000` to the deployed `.seq` and recast again.

## The shared-folder caveat

Rung 2 deliberately edits the **shared donor** effect id (`ef227` = `Bahamut__Full`, used by every
stock cast of Bahamut). Until this is reverted:

- **Vanilla Garnet/Eiko casting the real Bahamut** will also hear the Menu-Select blip and see the
  slower dim-to-black.
- This is throwaway by design -- rung 3 (fresh-id private copy, `LoadSFX: SFX=Bahamut__Full` by
  name from an unused id) is exactly the next rung specified to fix this. Don't leave rung 2's
  override in place past this proof.

## Revert

```
py studies/custom-summons/rung2-seq-hot-edit/revert_rung2.py
```

Removes, in order: the `.seq` override (+ the now-empty `ef227/` and `SpecialEffects/` directories
it created -- neither existed in a stock install), the minted-chime manifest row (surgically, so
any *other* kit-authored sfx mint sharing the same override file survives), and its `.ogg` asset.
Verified this session: after revert, `FF9CustomMap/StreamingAssets/Data/SpecialEffects` no longer
exists and the sfx manifest override file is deleted outright (nothing but the stock table
remained once our row was stripped) -- pure-stock resolution restored, `Battle`/`Characters`/
`Items`/`Text` (this bench's other overrides) undisturbed.

## Provenance

`build_rung2.py` is the **only** committable record of the edit: it reads the user's own stock
install, applies exactly the two edits above, and writes the result straight into the live
`FF9CustomMap` mod folder -- never into this directory, never into git. The edited copy is
SE-derived content (a modified copy of Square-Enix's shipped file) and must never be committed; the
unified diff the script prints (reproduced above) plus this file are the durable documentation. The
minted probe chime is 100% synthetic (stdlib `wave`/`struct`/`math` sine tone -- see
`ff9mapkit/tests/test_sound.py`'s `_tiny_wav` for the same idiom), so it carries no provenance risk,
but it's still deployed straight to the live mod folder rather than committed, to keep this
directory to exactly its three source files (`build_rung2.py`, `revert_rung2.py`, `README.md`). Both
scripts include a **drift guard**: `build_rung2.py` refuses to run if the stock file's sha256
(`4bc643bfb3ec478dcc1f5b51261f59637faac9d775cccd38c0055afee14ece63`) doesn't match what this
script's edits were derived against, rather than silently applying line-index edits against
unknown/changed content.

## Recon disagreement, resolved

The two rung-2 recon passes (`.seq` mechanism recon vs. minted-sound recon) each proposed a
different stock id for the immediate `PlaySound` proof: the `.seq` recon suggested `Sound=1110`
(precedent-only -- its own open-risks note flagged that id's actual content was never confirmed);
the sound recon suggested `Sound=103` (live-extracted and positively named "Menu Select" via the
kit's own `sfx-list` CLI). This script follows the **sound recon's** pick (103) as the safer,
better-verified option -- we know exactly what it sounds like, so a silent recast can't be
misread as "maybe 1110 doesn't play."
