# Custom Summons -- rung 3: the fresh-id private donor copy

> Ladder position: `studies/custom-summons/PLAN.md` §5, rung 3 of 9 ("Fresh-id private copy").
> Depends on rung 1 (★ in-game proven 2026-07-21, bench field **30300**, Iviv's minted **Spark →
> Bahamut Cinema** ability) and rung 2 (★ in-game proven 2026-07-21, since reverted -- but its
> **staged chime** (sfx id **100000**, `Sounds02/SE00/rung2chime`, a synthetic 880Hz tone) is still
> live in the manifest, armed for CAST B below).

## What this proves

Two things, across **two casts** separated by one relaunch:

1. **CAST A -- the global-namespace worry is dead.** The bench ability's `vfx1` moves off the
   shared donor folder (`ef227` = `Bahamut__Full`) onto a brand-new, private folder --
   **`ef084`** -- that ships a byte-identical copy of the same two `.seq` files. If the full
   vanilla Bahamut cinematic plays identically from id 84 while stock `ef227` (and every vanilla
   Garnet/Eiko Bahamut cast through it) stays completely untouched, that proves the fresh-folder
   mechanism end-to-end: a custom summon can own its OWN private effect folder instead of hijacking
   a real donor's, closing the "editing 227 changes vanilla Bahamut too" throwaway-ness of rung 2
   for good -- and doing so is also half of rung 6 (a fresh, engine-unclaimed id resolves
   gracefully) proven early, as a side effect.
2. **CAST B -- a minted sound id resolves from inside a *fresh-id* `.seq`.** Rung 2 already proved a
   `PlaySound` line resolves inside a *shared donor's* `.seq`, but only with an already-registered
   **stock** id (103); it deliberately left its own **minted** id (100000) unwired, because that id
   can't go live on an already-running game (`SoundMetaData`'s id table loads once at process
   start). Rung 3's relaunch (needed anyway, for the `vfx1=84` Actions.csv change) is the exact
   event that arms the minted chime -- so the *same* relaunch that proves CAST A also arms CAST B's
   proof: a hot-added `PlaySound: Sound=100000` line inside `ef084/PlayerSequence.seq`, recast with
   **no second relaunch**, should audibly chime. This finally closes PLAN.md §8's "does a minted id
   resolve from inside a `.seq` `PlaySound` line" question in full (rung 2 only closed it for a
   *stock* id).

## Why id 84

The recon cross-checked two independent sources and got the exact same 24-id set both times:

- A folder listing of `StreamingAssets/Data/SpecialEffects/ef###` (ids 0-510) has **487 present,
  24 absent** -- verified again for this build (`Test-Path .../ef084` = `False` before this rung
  ran; confirmed absent alongside 18, 37, 39, 80, 91, 263, 264, 379, 380, 426, 430, 442, 444,
  448-456, 488).
- `Memoria/Assembly-CSharp/Memoria/Data/Battle/SpecialEffect.cs:496-519` hand-aliases those exact
  **same 24 ids** as `Unused_N` enum members, each with a hand-written comment describing what the
  **legacy** (`SFXRework=0`) engine would do if one were ever cast: `18` -- "would apply effect
  instantly"; `37`, `39` -- "would never end" (the only genuine hang risk in the set); `80`, `84`,
  `91` -- "would run casting animation & apply effect"; the remaining 18 (`263`-`488`) -- "would
  rerun last effect used".

Our install forces `SFXRework=1` (+ force-on at `Memoria.ini` ATB Speed>=3), where none of this
matters at all: `UnifiedBattleSequencer`'s constructor
(`Memoria\Battle\SFX\UnifiedBattleSequencer.cs:105-126`) consumes the folder id purely as a path
string (`SpecialEffects/ef{N:D3}/PlayerSequence.seq`), never a bare enum cast -- graceful,
logged-and-empty on a missing file, never exercised here since we ship the folder. `84` was still
preferred over the other 23 candidates as pure defense-in-depth against a user running the legacy
engine: it's one of the mildest documented legacy behaviors ("run casting animation & apply
effect"), deliberately avoiding `37`/`39` ("would never end" -- the one behavior in the set that
would look like a genuine hang, not merely a cosmetic mismatch).

**Every downstream id/name in the copied files resolves independent of the containing folder's id**
(full citation trail in the recon this rung was built from): `LoadSFX`/`WaitSFXLoaded`/`PlaySFX`/
`WaitSFXDone: SFX=Bahamut__Full` all resolve the name `Bahamut__Full` -> `227` via
`Enum.Parse(SpecialEffect, ...)` (`BattleActionCode.cs:176-206`), and every subsequent lookup
(`SFXData.LoadSFX`, `SFXDataMesh.SetupRuntimeMesh`, `SFX.Play`, `SoundLib.LoadSfxSoundData`,
`FixedCameraEffects`) keys on that resolved `227`, **never** on our folder's `84`. The `.seq`s'
`PlaySound: Sound=...` lines are bare numeric literals into the process-global `SoundLib`/
`SongPlayer` tables, also folder-independent. So the folder id is touched **exactly once** per
cast, as a path string, with proven-graceful missing-file handling -- which is precisely why a
verbatim copy at a different id is expected to be indistinguishable in-game.

## What `build_rung3.py` ships

Copies stock `ef227`'s two files, sha256-drift-guarded against the hashes this script (and rung 2)
were built against, into a brand-new private folder:

| file | stock source | written to |
|---|---|---|
| `PlayerSequence.seq` | `StreamingAssets/Data/SpecialEffects/ef227/PlayerSequence.seq` | `FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef084/PlayerSequence.seq` |
| `Sequence.seq` | `StreamingAssets/Data/SpecialEffects/ef227/Sequence.seq` | `FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef084/Sequence.seq` |

Both files ship even though a straight player cast of `84` only ever reads `ef084/PlayerSequence.seq`
(the `PLAYER_SEQUENCE_FILE` constant, `UnifiedBattleSequencer.cs:1658`) -- `ef084/Sequence.seq`
sits unread by this rung's own design (the nested `SFXData.LoadSFX` call our copied `LoadSFX: SFX=
Bahamut__Full` line triggers resolves against `227`, loading the DONOR's real `Sequence.seq`, not
ours). It's shipped anyway to mirror the donor's on-disk shape byte-for-byte (repo law:
`feedback-incremental-verbatim-first` -- ship the donor's whole shape, don't guess which half is
"needed"), in case a future rung ever treats `84` as a first-class effect from some other path.

`--with-chime` additionally rebuilds `ef084/PlayerSequence.seq` with exactly one new line --

```
PlaySound: Sound=100000 ; SoundType=SoundEffect ; Volume=1.0
```

-- inserted immediately before the file's first executable line (`WaitAnimation: Char=Caster`,
right after the leading `// comment` + blank line) -- the exact syntax and insertion point rung 2
already proved plays (`rung2-seq-hot-edit/build_rung2.py`'s `FIRST_EXEC_LINE`), just against the
minted chime id instead of stock id 103. `Sequence.seq` is never touched by either mode. Both modes
always re-derive from the untouched stock files, so re-running with/without `--with-chime` cleanly
flips the shipped content back and forth -- nothing is ever edited in place, and the step is
scripted + reversible rather than a hand edit.

## `rung3.field.toml`

A byte-exact copy of `rung1-borrowed-cinematic/rung1.field.toml` plus **exactly one value changed**
(the "Bahamut Cinema" ability's `vfx1 = 227` -> `vfx1 = 84`) and a comment block above it explaining
the change (see the diff below). `vfx2` deliberately **stays 405** -- rung 1's own structural
analysis already proved it never plays for this bench (`AllEnemy(8)` is never `ManyAny`, and Iviv's
minted "Spark" command never enters `DecideSummonType`), so moving it would be a no-op edit, not a
second real data point. The `art/` folder is copied alongside verbatim (same relative-path law as
rung 1 -- the toml references `art/back.png` etc. relative to its own directory).

```diff
-  { name = "Bahamut Cinema", from = "Bahamut", targets = "AllEnemy", vfx1 = 227, vfx2 = 405 },
+  # --- CUSTOM SUMMONS rung 3 ... (see the file for the full comment block)
+  { name = "Bahamut Cinema", from = "Bahamut", targets = "AllEnemy", vfx1 = 84, vfx2 = 405 },
```

## The two-cast procedure

**1. Deploy** (FF9 closed or open -- the deploy itself doesn't need the game open):

```
py tools/deploy_field.py studies/custom-summons/rung3-fresh-id/rung3.field.toml --id 30300
```

This auto-reverts the prior deploy of id 30300 (rung 1's bench) first -- `deploy_field.py` always
reverts THIS id's prior test before writing the new one (`tools/deploy_field.py:2`). The mod folder
default (`FF9CustomMap`) is correct for this bench, same as rung 1.

**2. RELAUNCH FF9 entirely** (not `~` reload). `Actions.csv`'s `vfx1` cell for "Bahamut Cinema" is
startup-loaded (same as rung 1's whole `[[playable]]` stack) -- `~` Reload field will NOT pick up
the id change. This is also the event that arms the rung-2-staged chime id 100000
(`SoundMetaData`'s id table loads once at process start; the manifest row has been sitting in
`FF9CustomMap/FF9_Data/EmbeddedAsset/Manifest/Sounds/SoundEffectMetaData.txt` since rung 2 and only
needed *any* relaunch, for any reason, to go live).

**3. Load the bench save (or New Game -> `~` -> Warp to field -> 30300)**, same as rung 1/2.

**4. Get into a battle** (field 30300's random encounter, scene 67 -- Evil Forest/Trail).

**5. CAST A -- select Iviv -> Spark -> Bahamut Cinema.**

**Expect:** the full vanilla Bahamut cinematic plays **identically to rung 1** -- same chant,
same camera cut to Bahamut's own native shot, same damage timing. Success = you cannot tell it
apart from rung 1's proof run. Under the hood this is now playing from `ef084/`, not `ef227/` --
stock Bahamut is untouched.

**6. Report back to the orchestrator.** It runs:

```
py studies/custom-summons/rung3-fresh-id/build_rung3.py --with-chime
```

(no relaunch, no redeploy -- the same no-cache-per-cast mechanism rung 2 proved for `.seq` files in
general applies here too, since it's the same `AssetManager.LoadString` call site, just against
folder `84` instead of `227`.)

**7. CAST B -- recast Bahamut Cinema again (same menu path, no relaunch).**

**Expect:** an 880Hz synthetic chime plays at the **very instant** the command fires -- before
Iviv's chant animation even starts -- then the rest of the cinematic plays exactly as in CAST A.

## Failure modes (most to least informative)

| Symptom | Meaning |
|---|---|
| CAST A: full cinematic plays identically to rung 1; CAST B: same + the chime fires first | **SUCCESS** -- rung 3 fully closed |
| **CAST A is a silent no-op** (nothing happens on "Bahamut Cinema") | **The most informative failure.** Either the `vfx1=84` binding didn't land (check the deployed `Actions.csv` row -- did the relaunch actually happen, and did `deploy_field.py` really revert+rebuild id 30300?), or the fresh-folder path lookup itself failed (check `FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef084/PlayerSequence.seq` actually exists and is byte-identical to stock `ef227`'s -- re-run `build_rung3.py` and compare its printed hashes against this README's). Capture a few seconds of video (`feedback-video-for-visual-bugs`) and report exactly what you saw/heard (or didn't). |
| CAST A plays the **short** clip (405) instead of the full one | Would falsify the `targets` claim rung 1 already proved -- check the deployed `Actions.csv` row's `targets` cell still reads `AllEnemy(8)`; this would be a regression in the copy/toml, not a new rung-3 finding. |
| CAST A works, but **CAST B has no chime** (cinematic plays normally) | The pause/cinematic mechanism is fine; the **minted-id SoundEffect loader path** needs its own investigation. Check: (a) did the relaunch actually happen *after* rung 2's chime was staged (it needs exactly one relaunch, any reason, at any point after staging); (b) `Memoria.ini [Audio] SoundVolume` isn't 0 (rung 2's script warns about this same thing); (c) re-open `ef084/PlayerSequence.seq` and confirm line 3 reads `PlaySound: Sound=100000 ; SoundType=SoundEffect ; Volume=1.0` exactly (the DSL silently drops any line whose op name doesn't byte-match `BattleActionCode.operationArguments`, no error, no log). Does **not** falsify CAST A's fresh-folder proof. |
| CAST B's chime fires but **cuts off / distorts the rest of the cinematic** | Unexpected interaction between the inserted line and the thread timing -- capture video and report; revert to CAST A (`build_rung3.py` with no flag) to confirm the base cinematic is still clean without the insertion. |
| Nothing happens **at all**, even the menu entry is gone | You reloaded instead of relaunching, or skipped New Game/save load -- same class of mistake rung 1's README already documents. |

## Revert

```
py studies/custom-summons/rung3-fresh-id/revert_rung3.py
```

Removes the `ef084/` tree (both `.seq` files, regardless of which mode last built them) + the
now-empty `ef084/` and `SpecialEffects/` directories (mirrors `revert_rung2.py`'s empty-dir cleanup
exactly -- stops at `SpecialEffects/`, never touches `Data/` itself, since that folder also holds
this bench's own `Battle`/`Characters`/`Items`/`Text` overrides). Does **not** touch the rung-2
staged chime (manifest row + `.ogg`) -- that belongs to the rung-2 artifact set; revert it with
`rung2-seq-hot-edit/revert_rung2.py` if/when you want it gone too. Also revert the field deploy
itself with `py tools/scroll_out/revert_deploy_30300.py` (generated by the deploy command above).

## Provenance

Both copied `.seq` files are byte-identical Square-Enix content (a verbatim copy of the shipped
`ef227` files) and are therefore **never** committed -- `build_rung3.py` is the committable source
of truth, regenerating the copy from the user's own install every run, exactly like
`rung2-seq-hot-edit/build_rung2.py`. The output lands directly in the live mod folder
(`<game>/FF9CustomMap/...`), never under `studies/`. `build_rung3.py` includes the same drift guard
as rung 2: it refuses to run if either stock file's sha256 (`PlayerSequence.seq` =
`4bc643bfb3ec478dcc1f5b51261f59637faac9d775cccd38c0055afee14ece63`; `Sequence.seq` =
`0452a785e90c206c21f5c9b5464310f6d73186fe001dfd12abf60eda292611d0`) doesn't match what this
script's copy was derived against, rather than silently shipping a "verbatim" copy of unknown
content. `rung3.field.toml` and `art/` (copied unchanged from rung 1) are the only files this
directory commits, alongside the two Python scripts and this README.
