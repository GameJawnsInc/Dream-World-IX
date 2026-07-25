# RUNG 8 — NIMBRA: THE DEPLOY RUNBOOK

> **For the ORCHESTRATOR.** Everything below is staged and offline-verified; nothing here has been run
> against the live install. Contract = [`STORYBOARD.md`](STORYBOARD.md). Lane notes =
> [`SEQUENCE-LANE.md`](SEQUENCE-LANE.md), [`creature/README.md`](creature/README.md),
> [`audio/README.md`](audio/README.md). This file is the bench's: what to run, in what order, what
> "it worked" looks like beat by beat, and — because this is a **silent-skip DSL** — which symptom means
> which law broke.
>
> **Staged state: 49/49 integration checks green** (`stage/final/BENCH-REPORT.json`).
>
> ### ▶ RETIMED 2026-07-24 — READ [`STORYBOARD.md` §11](STORYBOARD.md#11-the-retime--2026-07-24-post-playtest-re-composition) FIRST
> NIMBRA has had its first successful cast. The owner's verdict — *"some of the cinematic beats hold for
> too long which reads as laggy/buggy"* — sent the round to a census of all 33 stock summon sequences
> (`census/DURATION-CENSUS.md`), which found the real defect: NIMBRA has **no short variant**, so it pays
> its full cinematic on **every** cast where a stock summon rolls short ~90 % of the time. Measured
> per-cast, stock runs 5.2–14.4 s; NIMBRA ran 29.3 s.
>
> **The cast is now ~140 ticks / 9.3 s and the ability is power 34 / MP 24** (was 485-then-440 ticks and
> power 62). Every number below is the retimed one. §11 has the full ledger of what was cut versus what
> was overlapped, and §11.7 has the redeploy/relaunch split for this specific round.

---

## 0. The one-screen summary

| | |
|---|---|
| **What** | **NIMBRA**, an original Mist-born eidolon — the first fully-original FF9 summon. Zero Square-Enix bytes: mesh, rig, 3 clips, atlas, 3 particle models, 3 audio cues and the whole `.seq` are authored. |
| **Where** | field **30301** (`bench/rung8.field.toml`, internal name `MISTBENCH`, toml id 4814). |
| **How to cast** | Iviv → **Spark** → **Nimbra** (24 MP, AllEnemy, power 34). |
| **Runtime** | ~140 ticks ≈ **9.3 s** at `BattleTPS = 15` — the stock expected-per-cast median (9.0 s). |
| **Lane** | DLL-free overlay — private `ef091/` + a minted `GEO_MON_B0_M400` (6400). **Runs on stock Memoria.** No `[SfxHybrid]`, no s58, no engine patch, no `--arm`. |
| **Needs a RELAUNCH** | **YES — once, before the first cast.** Three reasons at once (§2). |
| **Blast radius** | one new field slot, one new GEO id, one new effect folder, three new sfx ids, two new `Actions.csv` rows. `ef084` is never opened. |

---

## 1. Prerequisites (check before running anything)

1. **`Memoria.ini [Battle] SFXRework = 1`.** The whole lane is the SFXRework `.seq` route. At `0` the cast
   is a **silent no-op** — no error, no log. (Live install read 2026-07-24: `SFXRework = 1`, `Speed = 5`,
   `[Graphics] BattleTPS = 15`.)
2. **`Memoria.ini [Audio] PriorityToOGG = 1`**, or the bundled asset beats our loose `.ogg` override.
   `bench/deploy_rung8_audio.py --set-priority` sets it (backing the ini up first).
3. **The mod folder.** This worktree has **no `.ff9deploy.toml`**, so every tool defaults to
   **`FF9CustomMap`** — the same folder that holds the live `ef084`. That is fine and deliberate (both
   benches must coexist), but pass `--mod-folder` explicitly if you want another.
4. **`ff9mapkit` runs from the kit root** (`cd ff9mapkit`) so the local package shadows any editable install.
5. **Do not deploy 30300 in the same session** (STORYBOARD R11). `bench/rung8.field.toml` is a strict
   superset of `rung3.field.toml`: same two `[[playable]]` rows, same global `Actions.csv` /
   `Commands.csv` / `CharacterParameters` state, and **"Bahamut Cinema" keeps id 194** so the M1b bench
   keeps casting. Let 30301 own the CSVs.

---

## 2. THE RELAUNCH IS NOT OPTIONAL

Three separate launch-time tables change, and one relaunch covers all three:

| What | Why it needs launch |
|---|---|
| **field 30301** | its `DictionaryPatch` `FieldScene` line is read once at launch (first deploy of a NEW id only). |
| **`3DModel 6400 GEO_MON_B0_M400`** | same file, same rule — the GEO mint. |
| **sfx 100001 / 100002 / 100003** | `SoundMetaData`'s id table loads once at **process start** (STORYBOARD §5.2). |

Also launch-gated by the bench (unchanged from rung 3, but they bite the same way): the
`CharacterDefaultName` lines, the `Memoria.Scripts.FF9CustomMap.dll` (Iviv's "Soul Leech"), the loose
Face-Atlas portrait, and — for the `[[playable]]` recruit to exist at all — a **NEW GAME**.

**What is NOT launch-gated:** the `.seq`, the `.sfxmodel` manifest, the particle models and the `.anim`
clips. All four are **recast-only** — edit, re-run step 2, cast again, no relaunch. That is the iteration
loop for every tuning knob in §6.

### 2.1 THE RETIME REDEPLOY specifically (STORYBOARD §11.7)

If NIMBRA is already deployed and you are pushing the 2026-07-24 re-composition onto it:

| Artifact | Changed | What it needs |
|---|---|---|
| `PlayerSequence.seq`, `nimbra_manifest.sfxmodel`, `MistFloor.sfxmodel`, `MistWisps.sfxmodel` | yes | **step 2 only — recast-only.** `~` → cast. No relaunch. |
| `.anim` clips — `60000` (`emerge`) + `60002` (`strike`) **re-cut**, `60003` (`driftlook`) **NEW** | yes (STORYBOARD **§11.9**) | **step 2 only — recast-only.** The SFX route loads clips by literal asset path, so there is still **no `3DModelAnimation` line** and no relaunch (§1.7). Re-run `creature/make_nimbra_anims.py` first if you are rebuilding from source. |
| `6400.fbx`, `6400.png`, `RiftFlash.sfxmodel`, `.anim` `60001` (`drift`) | **no — byte-identical** | nothing; step 2 rewrites them harmlessly |
| **`Actions.csv`** (`power` 62 → 34) | yes | **step 1 + RELAUNCH** — the battle CSVs load at launch |
| **the three `.ogg` cues** (all re-rendered: 8.0 / 4.0 / 2.0 s) | yes, **content only** — the ids are already registered | **step 3, and assume a RELAUNCH.** §5.2 proved *registration* is launch-gated and explicitly left *content replacement at an already-registered id* **UNPROVEN**. It costs nothing to be safe here because `Actions.csv` forces a relaunch anyway — and it is a free chance to settle the question: deploy step 3 alone, cast without relaunching, and note whether the drone runs 8 s or 34 s. |

**So: run all three steps, then relaunch.** A recast-only loop is available for pure choreography
iteration afterwards (steps 2 only).

---

## 3. THE DEPLOY — three steps, in this order

Run from the repo root unless stated. Order matters: step 1 is a whole-field build that owns
`DictionaryPatch.txt`; steps 2 and 3 append to it.

```bash
# --- 1. the field + the "Nimbra" ability (+ the two [[playable]] characters) ------------------------
py tools/deploy_field.py studies/custom-summons/rung8-epic/bench/rung8.field.toml \
      --id 30301 --name MISTBENCH

# --- 2. the summon: ef091/ + the GEO 6400 mint  (DLL-free overlay lane; NO --arm) -------------------
cd ff9mapkit
py -m ff9mapkit summon-deploy --from-toml ../studies/custom-summons/rung8-epic/bench/rung8.field.toml
cd ..

# --- 3. the three minted sfx ids -------------------------------------------------------------------
py studies/custom-summons/rung8-epic/bench/deploy_rung8_audio.py --set-priority
```

Then: **relaunch FF9 → New Game → `~` → Warp to field → 30301.**

**Rehearse any step first** — every one has a no-write mode:

```bash
py studies/custom-summons/rung8-epic/bench/build_rung8_bench.py --clean --check   # ALL THREE, staged
cd ff9mapkit && py -m ff9mapkit summon-deploy --from-toml ../studies/.../bench/rung8.field.toml --dry-run
py studies/custom-summons/rung8-epic/bench/deploy_rung8_audio.py --dry-run --out <dir>
```

`build_rung8_bench.py` drives the **same** `build_mod` / `emit_overlay` / `mint_song` functions the three
commands above call, into `stage/final/FF9CustomMap/` — 102 files, then re-reads every one of them and runs
the 49 checks. It is the rehearsal, not a model of one.

### What each step writes

| Step | Files | Revert |
|---|---|---|
| 1 | field 30301 (FBG dir, `EVT_MISTBENCH.eb`, `.mes`), `Actions.csv` + `Commands.csv` + `CommandSets.csv` + `CharacterParameters.csv` + `BaseStats.csv` + `BattleParameters.csv` + `StatusSets.csv` + `Abilities/20.csv`+`21.csv` deltas, Iviv's animset (`Animations/6100/…`), the portrait atlas, the scripts DLL, `DictionaryPatch.txt` lines | `tools/scroll_out/revert_deploy_30301.py` |
| 2 | `StreamingAssets/Data/SpecialEffects/ef091/` (`PlayerSequence.seq`, `nimbra_manifest.sfxmodel`, `FileList.txt`, 3 particle `.sfxmodel`), `Models/3/6400/{6400.fbx,6400.png}`, `Animations/6400/{60000,60001,60002}.anim`, one `3DModel` line | `<mod>/.summon-revert/revert_summon_6400.py` |
| 3 | 3 × `Sounds/Sounds02/SE00/nimbra_*.ogg`, `FF9_Data/EmbeddedAsset/Manifest/Sounds/SoundEffectMetaData.txt` (2836 stock rows **+** our 3), optionally `Memoria.ini` | manual — §7 |

---

## 4. THE CAST PROTOCOL

1. **Relaunch FF9.** (§2 — skipping this is the single most likely cause of a "broken" cast 1.)
2. **New Game.** The `[[playable]]` recruit is a party-init thing; a save from before the deploy will not
   have Iviv.
3. `~` → **Warp to field** → **30301**. `Main_Init` recruits Iviv (and Steiniv) on load.
4. Walk until a random battle starts (`[encounter] scene = 67`, Evil Forest / Trail). **Prefer a
   multi-enemy formation** — `AllEnemy` with more than one target is exactly the case THE MULTI-TARGET
   NULL would have broken, so a 2+ enemy fight is the real test, not the easy one.
5. Iviv's turn → **Spark** → **Nimbra** (24 MP). Iviv boots **80/80 MP** = **three casts per fight**.
6. **Watch it all the way through, once, without touching anything.** It is 9.3 seconds now — then
   **cast it twice more in the same fight** (Iviv's 80 MP buys exactly three). The complaint this round
   answers was a *repeat* complaint, so one cast cannot settle it.
7. If you can, capture video — the eight phase checks in §5 are much easier to judge on a replay, and
   `tools/game_snap.ps1` can grab stills for the agent to read.

---

## 5. WHAT SUCCESS LOOKS LIKE, PHASE BY PHASE

Tick 0 = the cast starting. 15 ticks = 1 s. **Judge each phase against its own row** — "it looked cool"
is not a result, and a beat landing at the wrong *time* is a different bug from a beat not landing.
**Retimed table (STORYBOARD §11.1).** P1 is gone as its own phase; its content fires inside P0.

| Phase | Ticks | Sec | It worked if… | It did not if… |
|---|---|---|---|---|
| **P0 — THE HUSH + THE GATHER** | 0→25 | 0.0–1.7 | A title plate reads **"Nimbra"**. Iviv bows into the chant loop. The **summon** aura kindles (not the blue Spell aura). A low drone fades in *under* the music. The arena goes black over ~0.7 s and **the pall, the wisps and the whisper swell arrive WITH the darkness, not after it** — mist rolling in, wisps peeling upward on separate orbits. | Plate says something else / no plate. The screen goes black and *then* the mist appears (the three spawns were re-ordered after the `Wait`). No haze at all (see F3). Wisps all rise on one identical path (the `Parameter0` orbit randomization died — F7). |
| **P2 — THE COALESCE** | 25→40 | 1.7–2.7 | **NIMBRA rises out of the mist over the ENEMY line**, from below the frame, growing from a smudge to full height in about a second as the veil unfurls and the mask lifts to level. It **floats** — no legs, the veil frays into vapour and never touches the floor. | Nothing appears (F1/F2). It appears in the middle of the arena / off-screen (F4). It appears at full size instantly (the Scaling curve). It **faces away** — R4, §6 knob 1: one line, recast-only. It reads as a **pop** rather than an arrival → STORYBOARD §11.8's last bullet has the exact re-cut. |
| **P3 — THE LOOK + THE WIND-BACK** | 40→83 | 2.7–5.5 | The aura dies, Iviv commits the gesture. **t 40–65:** NIMBRA just **hangs there**, ribbons rippling, mask turning ~12° and back. It has not attacked; it is looking. **t 65–83:** the arms draw up and behind and the mask tips down — it is winding up. | It freezes mid-air (the playlist ran out — staged coverage is **145 ticks over a 110 window**, so suspect a clip that failed to load, not the arithmetic). Visible **pops** at clip seams (R7 — the shared rest-pose rule). No wind-back at all before the blow (the playlist's `strike` entry). |
| **P4 — THE STRIKE** | 83→133 | 5.5–8.9 | **Both arm-points drive forward, and on that exact tick** the sting hits, a pale rift-flash blooms **on every enemy**, and **the world snaps back to light**. Then damage lands and **the numbers pop, fully lit and readable** — while NIMBRA is already thinning away behind them. | Damage numbers invisible/dim → **THE FIGURE-VISIBILITY LAW** broke (F6). Flash on only one enemy (a `Char=` problem). **The flash fires while the arms are still drawing BACK** — that was the shipped build's behaviour; the retime moved the clip 18 ticks earlier, so seeing it again means the playlist did not land (F5/F3). Audio crunches → R6, §6 knob 3. |
| **P5 — RELEASE** | 133→140 | 8.9–9.3 | The dissolve has already finished under the damage numbers — the body narrowed to nothing while stretching upward, wisps peeling off it. The drone stops. Iviv returns to idle and squares up. Control returns cleanly. | It vanishes abruptly instead of thinning (the third Scaling piece). The cast **hangs** here → R9, the `WaitSFXDone`-after-`EffectPoint` ordering is suspect #1. Iviv stays frozen in the cast pose → THE ANIM=IDLE RELEASE LAW. A ~0.9 s wisp trail after the release is **expected**, not a bug. |

**Cross-cutting, judge once at the end:**

- **MP read 24, not 96.** A 96 in the menu = THE TYPE-4 MP LAW leaked (`type` bit 4 set). The staged
  `Actions.csv` row is `Nimbra;195;None(0);AllEnemy(8);0;0;0;0;91;91;85;34;128;0;22;0;24;0;159` — vfx1 =
  vfx2 = 91, scriptId 85, type `None(0)`, **power 34**, mp 24.
- **It should hit for noticeably less than before.** Power went 62 → 34 (STORYBOARD §11.4) — that is
  deliberate, and it is the *other* half of the census: 34/24 = 1.42 is the stock mean power/MP, where
  62/24 = 2.58 was 60 % above the most aggressive stock ratio. **A damage drop is the fix landing,
  not a regression.**
- **Nothing stock ever appears.** No Bahamut, no stock Eidolon, at any point. `vfx1 = vfx2 = 91` makes
  that structural.
- **"Bahamut Cinema" still works** from the same menu (it is the ef084 bench, untouched).
- **Total ≈ 9.3 s ± 0.7.** More than ~11 s means the two P0 clip-bound waits are longer than the
  ~10-tick budget — harmless, but note it.
- **It should NOT feel long on cast 3.** That is the whole point of the round: the old build spent up to
  ~88 s of one fight on three casts, this one spends ~28.

---

## 6. THE THREE TUNING KNOBS (recast-only — no relaunch, no re-export)

| # | Symptom | Edit | Then |
|---|---|---|---|
| 1 | **NIMBRA faces away** (R4 — the one knob rung 7 spent two casts on) | `bench/rung8.field.toml` → every `[[summon.staging.turn]]` `Y`: **180 ↔ 0**, and **168 ↔ 12** | re-run deploy step 2, cast again |
| 2 | **Too big / too small** | the `[[summon.staging.scale]]` destinations (the model is authored at 1402u; the curve is the size knob, per STORYBOARD §1.3) | step 2, cast |
| 3 | **Audio crunches at the strike** (R6 — there is **no limiter anywhere** in SaXAudio) | halve `Volume=0.7` on `nimbra.seq`'s `PlaySound: Sound=100003` **before** touching the asset | step 2, cast |
| 4 | **Blows out white** (rung-7 residual b: no battle-actor lighting pass on the SFX path) | `creature/nimbra_spec.py` → `DARKEN` (currently 0.85), re-run `make_nimbra.py` — **PNG only**, no re-export of anything else | step 2, cast |
| 5 | ~~Netsync guest freeze~~ **RETIRED** (R2). 9.3 s is nowhere near the s37 `GuestWaitMs = 30000` cap, and the knob it named (P1's `Wait: Time=95`) no longer exists — P1 was folded into P0 by the retime | — | — |
| 6 | **The load hitch at the rise** (R3 — `ModelFactory.CreateModel` fires synchronously at `PlaySFX`, and the blackout it hides behind is now 15 ticks old instead of 95) | **one line**: `nimbra.seq`'s P0 `Wait: Time=15` → `20`. Still the only FREE edit in the cast — it sits *before* `PlaySFX`, so it shifts every phase uniformly and both clocks stay locked. Costs 5 ticks on the 140 total | step 2, cast |

**Never trim a `Wait` after `PlaySFX` on its own** — the retracted P3 recipe is STORYBOARD §7.3, and the
retime obeyed it by re-cutting the `.seq`, the window, all three curves and the playlist *together*
(§11.2). If you want a different length, change all five or none. Do not trim anything else by hand —
every other `Wait` is load-bearing for a proven law, and P4's 50 ticks are now exactly the law floor.

---

## 7. FAILURE MODES — THE SILENT-SKIP TABLE

This is a DSL where **an unknown operation is dropped and an unknown argument key is ignored, with no log
at all** (`BattleActionThread.cs:154-155`). A typo does not crash; it deletes a beat. Read a symptom off
the left column and it names the law, not a guess.

| # | Symptom | What broke | First move |
|---|---|---|---|
| **F0** | The whole ability does nothing — no plate, no dim, no creature | `SFXRework = 0`, **or** the relaunch was skipped, **or** step 2 never ran | check `Memoria.ini`; confirm `ef091/PlayerSequence.seq` exists in the mod folder; relaunch |
| **F1** | Everything happens **except** the creature (dim, particles, damage, timing all right) | the `FileList.txt` / manifest chain. `FileList.txt` splits on **SINGLE spaces** — a tab or double space breaks it silently | `cat ef091/FileList.txt` → must be exactly `Model nimbra_manifest.sfxmodel\n`. Then `summon-seq-lint` the manifest |
| **F2** | Creature missing **and** a NEW GEO id was just minted | the `3DModel 6400` line was not registered | relaunch (§2). If it persists, grep `DictionaryPatch.txt` for exactly one `3DModel 6400` line |
| **F3** | One beat is missing, everything around it is on time | **a silently-dropped op or arg key** — the class this whole guard exists for | `cd ff9mapkit && py -m ff9mapkit summon-seq-lint <mod>/…/ef091/PlayerSequence.seq --private-ef 91 --particles MistFloor.sfxmodel,MistWisps.sfxmodel,RiftFlash.sfxmodel`. It must print 0 errors. **The emitter refuses to deploy an unlinted cast**, so a live failure here means the file was hand-edited after deploy |
| **F4** | Creature renders **at the world origin / off-camera** | **THE MOVEMENT TRAP** or **THE MULTI-TARGET NULL**: a missing Movement curve, or an anchor on `TargetPosition*` (which is 0 for a multi-target cast, `SFXData.cs:149`) | the manifest's Movement must read `TargetAveragePosition*`. `anchor = "target"` is refused by the linter — so this means the manifest was edited by hand |
| **F5** | Creature appears, then **freezes** mid-cast on one frame | **THE ANIMATION-PLAYLIST LAW**: the playlist ran out; there is no loop flag | staged coverage is **145 ticks over a 110 window**, so first suspect a clip that failed to LOAD (check all three `Animations/6400/6000*.anim` exist), not the arithmetic |
| **F6** | Damage numbers invisible or barely visible | **THE FIGURE-VISIBILITY LAW**: `Type=Figure` fired under the fullscreen intensity overlay | the linter runs the tick clock and every intensity ramp and refuses this — so a live occurrence means the `.seq` was edited. Particles are EXEMPT (different render path) |
| **F7** | Particles all move identically / none appear | `Char=` missing (a 0 bitmask renders on nobody, **silently**), or the `ParameterMin/Max` **int-vs-float trap** (`SFXDataMesh.cs:1389-1403` sorts them into separate dicts and drops a mismatched pair, so `Parameter1` evaluates to 0 everywhere with no log) | `summon-seq-lint` the `.sfxmodel` — it checks both |
| **F8** | **Silence**, everything else correct | the relaunch (`SoundMetaData` loads at process start), or `PriorityToOGG ≠ 1` | relaunch first. STORYBOARD §5.2: *silence with everything else working is a missed relaunch, not a design failure* |
| **F9** | Wrong / stock cast plays | `vfx1`/`vfx2` did not land | the Actions.csv row must read `…;91;91;85;…`. Both point at 91 deliberately, so stock content is structurally unreachable |
| **F10** | Menu shows **96 MP** | THE TYPE-4 MP LAW (`GARNET_SUMMON_FLAG` × the summon-class bit) | the row's type field must be `None(0)` |
| **F11** | The cast **hangs** at the damage beat | R9 — `WaitSFXDone` sits AFTER the `EffectPoint` pair, a new ordering | **suspect #1.** Move `WaitSFXDone` before the `EffectPoint` pair (rung 7's order) and re-run step 2 |
| **F12** | Black screen on warp to 30301 | an EventDB id collision (ids are GLOBAL across stacked mod folders) or a null `.eb` | grep every stacked folder's `DictionaryPatch.txt` for `30301`; see the `deploying-ff9-mods` skill |
| **F13** | Wrong dialogue text with correct flags | text-block shadowing across stacked folders | see the `deploying-ff9-mods` skill / `project-ff9-text-block-shadow` |
| **F14** | **"Bahamut Cinema" broke** | 30300 was deployed in the same session, or 194 moved | R11 — deploy only 30301; confirm `Bahamut Cinema;194;` is still in `Actions.csv` |

---

## 8. THE REVERT PATH

Reverse of the deploy order. Every step is idempotent.

```bash
# 3. audio -- no auto-revert ledger; delete the three .ogg files and drop the three manifest rows
#    (or restore the .txt from tools/scroll_out backups if step 1 made one). The MANIFEST OVERRIDE
#    REPLACES the stock table, so DELETE the file entirely if nothing else in this mod folder mints
#    audio -- do NOT leave a partial one behind.
rm "<mod>/StreamingAssets/Assets/Resources/Sounds/Sounds02/SE00/nimbra_"{drone,whispers,strike}".ogg"
#    then: remove the 3 rows from FF9_Data/EmbeddedAsset/Manifest/Sounds/SoundEffectMetaData.txt,
#    or delete that file if this deploy created it.

# 2. the summon -- auto-generated, stdlib-only, removes ef091/ entirely + the 3DModel line
py "<mod>/.summon-revert/revert_summon_6400.py"

# 1. the field
py tools/scroll_out/revert_deploy_30301.py
```

Then **relaunch** (the same three launch-time tables are being un-registered).

**What revert does NOT undo:** `Memoria.ini [Audio] PriorityToOGG` (restore from the backup
`deploy_rung8_audio.py --set-priority` wrote), and any `Memoria.ini` `[Mod] FolderNames` edit you made
yourself. Nothing in this rung touches `[SfxHybrid]` — the overlay lane never arms it.

**Invariants to re-check after a revert:** `ef084/` still present and byte-intact; `Bahamut Cinema` still
castable; field 30300 untouched.

---

## 9. Provenance + what this rung deliberately does not do

- **100 % original, fully committable.** Mesh, rig, atlas, 3 clips, 3 particle models, 3 audio cues, the
  `.seq`, the curves — all authored here. No donor, no `LoadSFX` of any stock id, no `ef###.bytes`, no
  stock `.seq` read. This is the first effect folder in the study that can be committed whole.
- **No camera work.** `PlayCamera` is a **hard no-op** at `[Battle] Speed ≥ 3` in `PHASE_NORMAL`
  (`UnifiedBattleSequencer.cs:828-829`) and this install runs `Speed = 5`; `ShiftWorld` moves only the
  scenery, with no auto-restore. The linter **refuses both**, with those citations. Scale is carried by
  the blackout, the rise from below frame, the Scaling ramp and the particle pall (STORYBOARD §2.4).
- **No `[SfxHybrid]` / s58.** That is the *transplant* lane (M1b). NIMBRA is the *original* lane.
- **`ef091/Sequence.seq` must never exist** (R15) — `SFXData.LoadSFX` reads it unconditionally, and a
  present one threads in as a second, duplicate-damage parallel thread. The emitter never writes it and
  `PlaySFX` carries `SkipSequence=True` anyway.

## CAST 2 VERDICT — 2026-07-24 ★★ THE WHISPER APPROVED ("much tighter")

The retimed NIMBRA (140 ticks / 9.3s / power 34 / MP 24 — the stock expected-cast median, ratio at
the stock mean) is playtest-approved. RUNG 8 IS CLOSED ★: the first original FF9 summon ever
composed, cast, and tuned onto the game's own duration-power line. Resting state: MISTBENCH 30301
live alongside the M1b bench; every timing knob recast-only. Open leads (non-gating): a REAL short
variant via cmd.info.short_summon (ordering risk unverified); Ark's measured 113.2s awaits a watch.
