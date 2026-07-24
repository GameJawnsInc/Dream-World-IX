# Rung 8 — the SEQUENCE + KIT lane

> The technical spine of NIMBRA: the hand-authored cast, the particle models, the staging-curve
> productization, and the linter that keeps a silent-skip DSL honest. Binding contract =
> [`STORYBOARD.md`](STORYBOARD.md); this file records what was built, the two places it had to deviate,
> and the contracts the integrator has to hold.
>
> **Status: BUILT + OFFLINE-VERIFIED. Nothing deployed, nothing committed, the live install untouched.**
> Everything staged under `stage/` (`game=None` throughout — the authored lane reads nothing from the
> install: no donor `.seq`, no `ef###.bytes`, no drift guard, because there is no stock content in the
> chain at all).

---

## 1. What is here

| File | What it is |
|---|---|
| **`nimbra.seq`** | The cast. 37 operation lines, 395 fixed-Wait ticks, hand-authored against STORYBOARD §3.1/Appendix A. |
| **`MistFloor.sfxmodel`** | §4.1 — the ground pall. 1 sprite, 6 verts / 4 tris, 12 emissions over 88 ticks. |
| **`MistWisps.sfxmodel`** | §4.2 — the drifting wisps. 1 sprite, 4 verts / 2 tris, 16 emissions. Fired twice (P1 + P5). |
| **`RiftFlash.sfxmodel`** | §4.3 — the strike flash. 2 sprites: an 8-point star burst + the rung-5 annulus, ×4. |
| **`nimbra.summon.toml`** | The `[[summon]]` block with the full `[summon.staging]` curve table (§3.3/§6.4). Paste into `rung8.field.toml`. |
| **`build_rung8_stage.py`** | Drives the **real** kit emitter into `stage/`, then re-lints and re-derives the storyboard's numbers from the emitted files. |
| `stage/FF9CustomMap/…/ef091/` | The emitted effect folder — what a live `summon-deploy` would write, byte for byte. |

Kit changes (all in `ff9mapkit/ff9mapkit/`):

| | |
|---|---|
| **`summons/seqlint.py`** (new) | K5 — the silent-skip guard, for `.seq` *and* `.sfxmodel`. |
| **`summons/deploy.py`** | K1 `sequence=` · K2 authored `clips=[…]` · K3 `particles=[…]` · K4 `[summon.staging]` consumed · a `manifest=` name · an input **preflight**. |
| **`content/summon.py`** | the three new keys, `donor` made optional behind `sequence`, path-existence checks for every authored input, the private-ef auto-alloc lint note. |
| **`cli.py`** | `ff9mapkit summon-seq-lint <files…> [--private-ef N] [--particles a,b,c]`. |
| **`tests/test_summon_seqlint.py`** (38) · **`tests/test_summon_curves.py`** (36) | always-run; the study's in-game-proven rung-5/6/7 artifacts are regression anchors. |

---

## 2. THE TWO DEVIATIONS (both forced, both flagged)

### 2.1 `[summon.staging]` is a TABLE, not a string + a table

STORYBOARD §6.4's example TOML writes **both**:

```toml
staging    = "curves"
[summon.staging]
anchor = "target_average"
```

**That is not expressible in TOML.** One key cannot be a string and a table at once; `tomllib` raises on
the second definition. Resolution — the **table is canonical**: the presence of `[summon.staging]`
selects curves mode. `staging = "donor"` (the default) and `staging = "curves"` still parse; a bare
`staging = "curves"` with no table is refused with the fix spelled out. Every other key, value and curve
number is exactly as §6.4 and §3.3 specify.

### 2.2 The P5 wisps fire BEFORE `WaitSFXDone`, not after

STORYBOARD §4.2 pins the second `MistWisps` spawn at **`t = 405`** — the tick the dissolve starts
(Scaling piece 3 = manifest frames 255→330 = ticks 405→480), and a 70-tick particle life then lands at
475, just inside the creature's own 480. §3.1's prose agrees ("wisps peel off it").

But Appendix A's **draft** lists the line *after* `WaitSFXDone`, which resolves at t = 480 — so as
written the wisps would fire at 480, after the creature is already gone, and trail past the end of the
cast.

`nimbra.seq` puts the `CreateVisualEffect` **first**. It is a one-line reordering, `CreateVisualEffect`
is fire-and-forget (0 ticks), so **every tick in the whole cast is unchanged** — only the spawn instant
moves, from 480 to the 405 §4.2 asked for. *If the storyboard's author intended the draft order, swap
those two lines back; nothing else changes.*

---

## 3. Contracts the integrator must hold

1. **The creature lane owns `nimbra/6400.fbx` and `nimbra/{emerge,drift,strike}.anim`.** The block names
   them; `build_rung8_stage.py` resolves `nimbra/*` against `./creature/nimbra/` and **stubs, per file,
   anything not there yet** (loudly). As of this writing the real `6400.fbx` + `6400.png` are being
   consumed; the three `.anim` files are still placeholders shaped to the storyboard's 90/75/60 frames so
   the playlist arithmetic is real.

2. **⚠ CLIP-KEY MISMATCH, resolved but worth knowing.** `creature/nimbra_clips.py:CLIPS` assigns each
   clip a numeric `.anim` key **0 / 1 / 2**; the kit's K2 emitter assigns **60000 / 60001 / 60002** (the
   mint band, clear of every stock key — stock tops out at 14739). Both are legal: STORYBOARD §1.7 only
   says "`Animations/6400/<key>.anim`", and the key is just a file name that doubles as the runtime clip
   name. This is now **collision-proof by construction**: `deploy.clip_key_of` takes a **numeric file
   stem at its word** (`0.anim` → key 0) and only falls back to the mint band for a named file
   (`emerge.anim` → 60000+i) — and the kit writes *both* the clip file and the manifest entry from that
   one function, so they cannot disagree. **The creature lane should emit files named `emerge.anim` /
   `drift.anim` / `strike.anim`** (what the block contract asks for) and let the kit own the key; if it
   emits `0.anim` / `1.anim` / `2.anim` instead, that works too — just update `clips=` in the block.

3. **The audio lane owns sfx ids 100001 / 100002 / 100003.** `nimbra.seq` plays them at
   `Volume=0.55 / 0.50 / 0.70` (§3.1) and `StopSound`s the drone at t = 480. Minting a new id needs **one
   relaunch** (`SoundMetaData` loads at process start) — the same relaunch as the `3DModel 6400` line.
   Silence on cast 1 with everything else working = a missed relaunch, not a design failure.

4. **The wiring lane owns `rung8.field.toml`.** Paste `nimbra.summon.toml`'s whole `[[summon]]` (plus its
   `[summon.staging]` sub-tables) in, and author the `"Nimbra"` ability separately — `[[summon]]` never
   edits `Actions.csv` (DESIGN §1.4). `private_ef = 91` is **pinned**: 84 is the live Thomas/M1b bench and
   must stay bit-intact, and auto-alloc would land on 18 ("would apply effect instantly"). The block's
   lint now says so out loud.

5. **`ef091/Sequence.seq` must never exist** (R15). The emitter never writes it, and `PlaySFX` carries
   `SkipSequence=True` anyway.

---

## 4. How the laws are enforced, mechanically

`summons/seqlint.py` turns the study's proven grammar into checks. Everything below **fails a build** —
the emitter refuses to deploy a cast the engine would silently drop pieces of.

| Law / trap | Check |
|---|---|
| **Unknown op is dropped with no log** (`BattleActionThread.cs:155-156`) | op must be one of the 41 `operationArguments` keys **+ `EndThread`** (legal-but-absent: the parser pops the thread stack at `:150-154` and *then* falls through the same `continue`). |
| **Unknown arg key is stored and ignored** | per-op key whitelist derived from the **executor**, not from `operationArguments` — that table is positional-argument names and is out of sync in ≥4 places (`CreateVisualEffect` reads `SFXModel`, which it does not list; `PlayAnimation` reads `Hold`; `PlayCamera` reads `Alternate` not `IsAlternate`; and **every** op honours `Reflect`, listed for none). An op we do not emit *warns* rather than guessing a table. |
| **§2 — `PlayCamera` / `ShiftWorld`** | refused outright, with the citations in the message. |
| **THE PHASE-LOCK RULE** | no clip-bound wait inside the `PlaySFX … WaitSFXDone` window. (Outside it — the proven rung-6 release tail `WaitReflect / Anim=Idle / Turn / WaitTurn` — is fine: there is no manifest clock left to slide against. This refinement is why rung 7's own cast fails *only* this rule; that is the debt §3 turned into the law.) |
| **THE FIGURE-VISIBILITY LAW** | the linter runs the fixed-`Wait` tick clock and every `SetBackgroundIntensity` **ramp**, and refuses an `EffectPoint: Type=Figure/Both` scheduled while intensity < 1 — *including mid-ramp*. |
| **THE INTENSITY SUBTLETY LAW** | a destination strictly between 0 and 1 warns. |
| **THE ANIM=IDLE RELEASE LAW** | the last `PlayAnimation: Char=Caster` must be the literal `Anim=Idle`. |
| **rung-5 `CreateVisualEffect` laws** | `Char=` mandatory (a 0 bitmask renders on nobody, silently); full `Data/`-rooted path; `Time`/`Size`/`Speed` warn as inert on the `SFXModel` branch. |
| **cross-file** | every `SFXModel=` resolves to a staged particle; every `SFX=` equals `private_ef`. |
| **`LoadSFX` / `PlaySFX` gotchas** | `UseCamera=False` (the computed default is TRUE here) and `SkipSequence=True` (R15) warn when absent. |
| **thread balance** | `StartThread`/`ElseThread` vs `EndThread`. |
| **THE ANIMATION-PLAYLIST LAW** | the emitter derives each clip's frame count from its `.anim` key times and refuses a playlist that does not cover `end − start` (it would **freeze** on the last frame — there is no loop flag). |
| **the curve invariants** | `Σ move = Σ turn = Σ scale = end − start`; the first piece of every curve must carry a `from`; a bad `ease` name is refused (the engine silently falls back to `Constant`); `play.clip` must name an authored clip; `speed > 0`. |
| **THE MULTI-TARGET NULL** | `anchor = "target"` is refused with the `SFXData.cs:149` citation. |
| **the `.sfxmodel` side** | JSON parses; `Indices` %3 and in range; interpolation names valid; `ColorInterpolation` long enough for its **segments**; and the headline trap — **`ParameterMinK`/`ParameterMaxK` must be both ints or both floats**, because `SFXDataMesh.cs:1389-1403` sorts them into separate int/float dictionaries and drops any key whose partner landed in the other one. `ParameterMin1 = "0.35"` with `ParameterMax1 = "1"` makes `Parameter1` evaluate to 0 everywhere, with no log. |

---

## 5. Offline verification actually run

```
$ py -m ff9mapkit summon-seq-lint nimbra.seq *.sfxmodel --private-ef 91 \
      --particles MistFloor.sfxmodel,MistWisps.sfxmodel,RiftFlash.sfxmodel
nimbra.seq: 0 error(s), 0 warning(s), 37 op line(s), 395 fixed-Wait ticks …
MistFloor.sfxmodel / MistWisps.sfxmodel / RiftFlash.sfxmodel: 0 problem(s)
clean -- no operation or argument would be silently dropped.

$ py build_rung8_stage.py --clean --check
… staged GEO_MON_B0_M400 (id 6400) -> private ef091, lane=overlay, staging=curves
  playlist : 375 ticks over a 330-tick window (emerge 90/2 = 45, drift 75/1 x2 = 150,
                                               strike 60/2 = 30, drift 75/1 x2 = 150)
  two clocks  : PlaySFX at tick ~150, FBX window 0..330 => drains at ~480  (§3.2 says 480)
  Movement/Rotation/Scaling: 2/3/3 piece(s), 330 ticks each [ok]
  FileList.txt: b'Model nimbra_manifest.sfxmodel\n' [ok]
CHECK CLEAN
```

Independently re-derived and matching STORYBOARD §3.1/§3.2/§3.3: **395** fixed-Wait ticks · **330**
ticks on each of the three curves · **375** playlist ticks ≥ the 330-tick window (so the playlist is
never exhausted and never freezes) · `PlaySFX` at 150 + 330 = the instance drains at **480**, which is
the tick `WaitSFXDone` was authored to resolve on.

Suite: `4233 passed, 262 skipped` (the 262 are this fresh worktree's un-extracted templates), of which
**74 are new** and every one always-runs.

---

## 6. Storyboard defects found while implementing (non-blocking, for the record)

- **§6.4's TOML is not valid TOML** — §2.1 above.
- **§4.2's spawn tick contradicts Appendix A's op order** — §2.2 above.
- **"the 44 keys of `BattleActionCode.operationArguments`" (§6.4 K5.1) is 41**, counted at the cited
  lines `BattleActionCode.cs:46-89`. The citation is right, the count is not; `ENGINE_OPS` holds the
  real 41 + `EndThread`.
- **§7.2's "`Vertices` are 2-component"** — `sprite.vertex` is indeed `Vector2[]`, but the load is
  `JSONNode.AsVector`, and the in-game-proven rung-5 artifact writes **3**-component tuples with a
  trailing `0`. The three particle files follow the proven artifact; the linter accepts 2 or 3.

## 7. Observations for the playtest (not defects)

- **`MistWisps` outlives its own spawn window.** Emissions run to frame 75 and each particle lives 70,
  so the effect lasts ~145 ticks, not 70. At the P1 spawn (t = 55) that is fine; at the P5 spawn
  (t = 405) the last wisps die around t = 550, ~65 ticks after the cast ends. §4.2 asked for one file at
  two beats, so this is as specified — just expect a short trail after the release.
- **The two clip-bound P0 waits are the cast's only timing uncertainty** (±10 ticks). They sit before
  `PlaySFX`, so the slack shifts every phase uniformly and never touches the two-clock alignment. The
  linter counts them but deliberately does not guess a length.
- **R2's trim knob is P1's `Wait: Time=95`, and it is a ONE-line edit** (`→ 50` = 29.3 s). It is the only
  free knob because it sits **before `PlaySFX`**: the `.seq`'s tick clock and the manifest's frame clock
  share their origin at `PlaySFX`, so anything earlier shifts the whole cast uniformly and anything later
  slides the two apart. This is THE PHASE-LOCK RULE's stronger form — *no* edit after `PlaySFX` is free,
  not just clip-bound waits. An earlier draft of R2 prescribed trimming P3's `Wait: Time=90` instead;
  that is **retracted** (it fails the curve-duration gate, then the playlist-coverage gate, and then
  desynchronises the strike beat by 15 frames). STORYBOARD §7.3 has the measurements.
