# Custom Summons — feasibility study

> **Status: RUNGS 1+2 ★ IN-GAME PROVEN 2026-07-21** — rung 1: "it worked, bahamut played in full"
> from Iviv's minted Spark command (bench `rung1-borrowed-cinematic/`, field **30300**, minted
> ability **"Bahamut Cinema" id 194**); rung 2: "both worked, the blip played and the fade was
> slower" — the .seq edit→recast HOT LOOP is real (no relaunch; `rung2-seq-hot-edit/`, since
> reverted; the minted chime stays staged for rung 3). Kit work item #4 (the vfx≥511 playParam
> WARN) landed the same day; the rung-1 "crunchy audio" observation is INVESTIGATED (§8 — not our
> binding; no-limiter clipping + known-poor vanilla assets; 2-step user A/B). NEXT = rung 3, the
> fresh-id private donor copy. Research opened 2026-07-21 from a 20-agent ultracode workflow
> (6 recon lenses over the Memoria source + game install + kit + community docs → synthesis → 12
> load-bearing claims adversarially verified: 8 CONFIRMED, 4 PARTIAL-with-corrections, 0 REFUTED;
> + a completeness critic). All file:line citations below were re-derived by skeptic agents against
> the live engine fork at `C:\gd\FFIX\Memoria\Assembly-CSharp`.

## 1. The question

Can the kit author **custom Summons** — new long, epic-scale in-battle cinematic animations
(Bahamut/Ark class) — for custom abilities and custom playable characters?

## 2. Headline verdict

**Yes, almost entirely data-only — on an engine surface the kit has never touched.** Memoria's
default battle-VFX engine (`SFXRework=1`, ON in our install and force-on at ATB Speed≥3) renders
every spell and summon from **loose, human-readable text scripts**:
`StreamingAssets/Data/SpecialEffects/ef{id:D3}/{PlayerSequence.seq, Sequence.seq}` — a ~35-opcode
choreography DSL (officially documented at the Memoria wiki, "Battle-SFX-Sequence") executed by
`UnifiedBattleSequencer`. These files resolve through the normal stacked-mod-folder AssetManager
and are **re-parsed fresh every cast** (edit → recast, no relaunch — a faster dev loop than `~`).
An ability's effect binding is a raw number (`Actions.csv` animationId1/animationId2 →
VfxIndex/Vfx2), already exposed by our `[[battle_action]] vfx1/vfx2`, with **zero category gating**
— any ability can point at any effect id.

Three ceilings, in order of hardness:

1. **The stock Eidolon creatures are unreachable as assets.** Their meshes/animations live inside
   opaque native `ef###.bytes` binaries rendered by the closed-source **`FF9SpecialEffectPlugin.dll`**
   (P/Invoke; not in the Assembly-CSharp tree our patch stack edits). You can *replay* them (by id),
   *re-time/re-dress* them (.seq edits), but not extract or modify the creature itself.
2. **A truly custom creature has exactly one engine hook, with zero precedent anywhere:** an
   effect folder's `FileList.txt` `Model <path>.sfxmodel` line loads a JSON manifest whose `FBX`
   entries go through `ModelFactory.CreateModel → ModelImporter.CreateCustomModelFromFbx` — **the
   exact same loose-FBX loader our proven custom-model pillar already uses** (SFXDataMesh.cs:744).
   0 of the 487 shipped ef folders use it; no community mod found that ever has. Code-complete,
   battle-untested. This is the pillar's central bet.
3. **A continuous custom camera dolly is the one genuinely hard gap — but it's a managed wiring
   job, not native RE.** The data-driven camera loader is a literal `// TODO return null` stub
   (SFXDataCamera.cs:205-209). Camera-owning effects re-invoke the native plugin live every frame.
   BUT: this is not a blank frontier — our own `battle/camera_codec.py` already authors
   multi-segment camera sweeps into the raw17 bytes **the native plugin itself reads** (in-game
   proven for battle-opening cameras, indices 0-2); the natural extension is the attack-sequence
   camera slots (indices 3-8) that `PlayCamera` selects. And per §3A, the binary camera format is
   already fully solved in the open source, so finishing the stub is a local managed patch. Until
   then: camera CUTS (`PlayCamera`) + `ShiftWorld` + borrowing a donor's native camera by loading
   its SFX are all available data-only.

> **Is the native plugin itself an insurmountable wall? No — see §3A.** A follow-up investigation
> (workflow `wf_61f380d8-dc4`) inspected the actual binary and found it's a soft target, and more
> importantly that for custom summons **nothing needs cracking at all.**

Nobody in the FF9 community has ever shipped a genuinely new summon (community lens; the Memoria
maintainer's own SFX tracking issue #917 calls deep SFX work "might require a breakthrough").
Everything shipped is reuse/reassignment. **A composed original would be a first.**

## 3. The mechanism map (all source-verified)

### 3.1 Dispatch: ability → effect id → sequence

- `Actions.csv` columns `animationId1`/`animationId2` parse as **raw Int16/UInt16** (deliberately
  NOT `CsvParser.EnumValue` like neighboring columns) → `BattleCommandInfo.VfxIndex` / `AA_DATA.Vfx2`
  (BattleActionEntry.cs:26-39). Bare-cast to the `SpecialEffect` enum with no validation
  (BattleCommand.cs:113; btl_vfx.cs:99-100).
- `btl_vfx.GetPlayerCommandSFX` picks: `cmd.PatchedVfx` (if set) → `Vfx2` when
  `short_summon`/meteor-miss/etc → else `VfxIndex` (btl_vfx.cs:95-102).
- `UnifiedBattleSequencer.BattleAction(EffectType.SpecialEffect, id)` builds
  `Data/SpecialEffects/ef{id:D3}/PlayerSequence.seq` **purely from the number** — no
  `Enum.IsDefined`, no category check; a missing file logs a warning and no-ops
  (UnifiedBattleSequencer.cs:105-126).
- **`PatchedVfx` = the dynamic per-ability override**: AbilityFeatures.txt `>AA <id>` +
  `[code=SpecialEffect] {NCalc} [/code]` swaps the played effect at cast time — checked FIRST
  (btl_vfx.cs:95-96). Shipped examples exist (Fenrir alternates Earth/Wind via
  `GetAbilityUsageCount`). Our `[[ability_feature]]` module already authors this file.
- Enemy attacks are separate: their sequences transpile at runtime from the scene's **raw17
  btlseq** (`BattleActionThread.LoadFromBtlSeq`) — the surface our proven
  `seqcodec/seqasm/seqauthor` stack already round-trips byte-exact (562/562 scenes).

### 3.2 The two engines

- **Legacy** (`SFXRework=0`): `AssetManager.LoadBytes("SpecialEffects/ef{id:D3}")` → the opaque
  binary → native `SFX_Play`/`SFX_Update` (SFX.cs:1974-1985). Not our target.
- **Rework** (default ON; forced at Speed≥3; our ini has `SFXRework=1`): the `.seq` text path.
  All new work targets this. With `SFXRework=0` custom .seq content silently no-ops → the pillar
  should lint/warn on that ini state.

### 3.3 The .seq DSL (the authoring surface)

Line format `Operation: key=val ; key=val`, `//` comments, threading via
`StartThread/ElseThread/EndThread` (+Condition/Sync/LoopCount). Full vocabulary (~35 ops,
BattleActionCode.cs:46-89, wiki-documented): `Wait`, `WaitAnimation/Move/Turn/Size`,
`WaitSFXLoaded/Done`, `Channel/StopChannel`, `LoadSFX/PlaySFX` (+Monster variants),
`CreateVisualEffect` (SPS/SHP/SFXModel), `Turn`, `PlayAnimation`, `PlayTextureAnimation`,
`ToggleStandAnimation`, `MoveToTarget/MoveToPosition`, `ChangeSize`, `ShowMesh`, `ShowShadow`,
`ChangeCharacterProperty`, `PlayCamera`, `ResetCamera`, `PlaySound`, `StopSound`, **`EffectPoint`**
(= the damage-application trigger: → `btl_cmd.ExecVfxCommand` → `SBattleCalculator.CalcMain`;
damage lands wherever the author puts this line), `Message`, `SetBackgroundIntensity` (0 =
renderers literally disabled — the vanilla blackout), `ShiftWorld` (move-the-world-not-the-camera),
`SetVariable`, `SetupReflect/ActivateReflect`. Unknown ops are **silently skipped**
(BattleActionThread.cs:156-157) → our linter must catch typos offline.

- **No length ceiling**: playback ends only when every thread is inactive and all tweens drain
  (ExecuteLoop, UnifiedBattleSequencer.cs:1298-1344); `CheckCommandLoop` polls that and only then
  `ReqFinishCommand`s. Stock proves scale: Ark holds 862 frames; Madeen's Sequence.seq is ~24KB.
- **Hot reload**: no cache wraps the per-cast parse; `Common/Channel*.sfxmodel` reload every
  battle entry (`SFX.StartBattle → SFXChannel.LoadAll`).
- Stock summons range 1.8KB (Odin) → 24KB (Madeen) of this DSL + shared `Common/` channel auras.

### 3.4 Custom visual content (the Tier-3 bet)

- `FileList.txt` in the effect folder: `Model <path>.sfxmodel` / `Camera <path>.sfxcamera`
  (SFXData.cs:244-279). The `.sfxmodel` JSON supports:
  - **`Sprite`** — hand-authored triangle mesh, keyframed vertex colors/UVs/scale, NCalc movement
    expressions (`CasterPositionY + Parameter1 * 800`), particle `Emission` schedules. **Shipping
    today** in exactly 5 files (the 4 `Channel*` auras + `Reflect`) — the proven half.
  - **`FBX`** — loose FBX path + Start/End + Movement/Rotation/Scaling curves + Animations list,
    loaded via `ModelFactory.CreateModel` at SFXDataMesh.cs:744 (**the same loader as our
    playable-character battle models** — corrected citation from verification). **Unexercised by
    all 487 stock folders.** Actively patched as recently as Memoria's 2024-11-17 changelog
    ("lightly hardened, not battle-tested").
- `CreateVisualEffect: SFXModel=<path>` also takes an `.sfxmodel` directly from a .seq line, bone-
  attachable to any battler (UnifiedBattleSequencer.cs:381-448) — custom particles without
  FileList.txt.
- **SPS is NOT independently authorable** (wiki, explicit): proprietary binary; retexture-only.
  New particles go through `.sfxmodel` Sprite, not SPS.
- **The stock creatures**: NOT in the p0data model bundles under any name (UnityPy sweep found
  battle-stage geometry + status-SPS only). They live inside the native `ef###.bytes` blobs
  (e.g. `Resources/specialeffects/ef094.bytes`, per Memoria discussion #1002 — opaque; the
  built-in `SFXDataMeshConverter` self-describes as debug-only and "mostly fails"). A custom
  creature therefore **must** come from our own FBX pipeline.

### 3.5 Camera: the precise truth

- Effects that own the camera run `CameraEngine.SFX_PLUGIN` — the native DLL is re-invoked
  **live every render frame** (SFXDataMesh.Runtime; `battle.BattleMain → SFXDataCamera.UpdateCamera`
  unconditionally each tick). `FixedCameraEffects` (SFXData.cs:1339-1369) hardcodes every stock
  summon `__Full` (+ Meteor/Doomsday/Holy/…) to force `UseCamera=true` — so **a .seq that
  `LoadSFX`es a stock summon id inherits that summon's REAL cinematic camera for free**.
- The data-driven camera engine (`SFX_DATA_CAMERA`) is dead: `LoadFromJSON` returns null
  (SFXDataCamera.cs:205-209), the update branch is a TODO that clears state (:548-553), and
  `RunCamera` has zero callers. Unfixed in our fork (patch-stack grep: 0 hits).
- A .seq's `PlayCamera` selects a numbered slot in the battle scene's **raw17 camera table**
  (`seq_work_set.CameraNo`, UnifiedBattleSequencer.cs:825-854) — cuts, not dollies. Open question
  whether slots 3-8 (the "attack sequence" cameras) give epic framing on an arbitrary arena.
- **The kit precedent that softens this** (verification correction): `battle/camera_codec.py` +
  `camera_data.py` already author multi-segment opening-camera sweeps into the raw17 BSC bytes the
  native plugin reads — in-game proven (commit 8fc6f55), currently scoped to opening slots 0-2.
  Extending it to slots 3-8 = a from-scratch mid-battle camera sweep **without touching the dead
  C# path or the native DLL**. That is the realistic "epic camera" lever, not the JSON stub.

### 3.6 Battle state during a long effect (all confirmed)

While a command executes: **every other unit's ATB freezes** (`FF9BMenu_IsEnableAtb` false while a
command is queued/executing → `ProcessActiveTime` skips), the command menu deactivates
(`_commandEnable`/`AllMenuPanel`), the background can black out (`SetBackgroundIntensity=0`) and
the world can shift under a fixed camera (`ShiftWorld`). Control returns purely when the sequence
drains. Damage timing is wherever `EffectPoint` sits. An arbitrarily long summon = an arbitrarily
long global freeze — see the netsync risk (§7).

### 3.7 What "summon-ness" actually is (and isn't)

- **There is no Summon category anywhere.** No CommandType.Summon, no category bit. Summon-ness =
  three hardcoded `BattleCommandId` equality checks: SummonGarnet=16, Phantom=18, SummonEiko=20.
- **Long vs short**: `DecideSummonType` (btl_cmd.cs:1583-1615) fires ONLY for those 3 command ids,
  matches ONLY the 16 stock `BattleAbilityId`s, first-ever cast per Eidolon guaranteed long
  (persistent `AchievementState.summon_*` flags, BattleAchievement.cs:91-168), then an MP-ratio
  RNG roll (230/256 short if MP>2×cost, else 170/256). Short = damage ×2/3
  (BattleCalculator.cs:515-516,545-546) + plays `Vfx2`. **A minted command NEVER enters this path
  → always plays its full/long variant** — favorable for "epic," and reproducible in data anyway
  via `[code=SpecialEffect]` + `GetAbilityUsageCount/GetRandom` if we ever want the first-cast-long
  UX. (The generic `IsShortSummon` flag is also settable via a `>SA` Command-effect — the Boost
  SA's own mechanism.)
- **NOT gem-count-based** (the common belief is wrong): summon damage/length has no jewel-count
  input. `summon_count` is a per-battle counter feeding only the off-by-default
  `SummonPriorityCount` ATB feature. The real item-count hooks: **Odin's Sword SA** (data-driven
  NCalc in AbilityFeatures.txt keyed to `ScriptId == 87` — a custom summon must avoid ScriptId 87
  or it triggers Steiner's bonus) and **Phoenix's party-wipe revival** (hardcoded Eiko +
  PhoenixPinion count, btl_sys.cs:105-123 — with an `IOverloadOnGameOverScript` escape hatch our
  Overload hub pattern already knows).
- **Trance**: Garnet-only `EidolonToPhantom` hardcoded switch maps 8 of 16 summons to auto-recast
  abilities whose VfxIndex IS the base summon's Short id.
- **Alexander is not a battle summon** — no BattleAbilityId; cutscene-only.
- Playback-layer name-keyed special cases live in SFX.cs (Ark subOrder flips at frames 1004/1193,
  per-summon sound-index/pitch tables in AdjustSoundIndex/StreamPlay/SoundPlay) — they key on the
  **LoadSFX id**, so they ride along when a donor's SFX is borrowed and are irrelevant to
  fully-custom content.

### 3.8 The fresh-id question (the biggest design fork — now mostly resolved)

The community wiki says VfxIndex "must be an existing SpecialEffect value"; the source says the
folder lookup is gate-free. Both are right at different layers:

- The **folder id** (VfxIndex → `ef{id:D3}/`) is un-gated. Any Int16 works; missing file = logged
  no-op, not a crash (confirmed).
- The **`SFX.playParam` bound** (fixed Int32[511], id≥511 silently substitutes `Fire__Multi`;
  negative ≠ -1 throws — SFX.cs:1937-1946) applies to ids passed to `SFX.Play`, which on the
  rework path is **the `LoadSFX`/`PlaySFX` target inside the .seq, not the folder id**. A fresh
  folder whose .seq only uses `CreateVisualEffect`/`PlayAnimation`/etc never consults it.
  Conservative rule anyway: **mint fresh effect ids only in unused holes < 511** (the enum is
  sparse in −1..519). Our `actiondelta` vfx validator currently allows ≤32767 — tighten it.
- Zero precedent for a fresh id + FileList.txt anywhere (0/487 stock, no community sighting) —
  rung 6 settles it live before any Tier-3 investment.

### 3.9 SequenceFile (the alternate binding — corrected by verification)

`BattleCommandInfo.SequenceFile` (`[PatchableField] String`) loads an arbitrary custom .seq path,
bypassing the numeric folder scheme. The READ side is generic — `SelectCommandVfx`'s check
(btl_vfx.cs:114) is **not** player-gated (critic finding). But the WRITE side is **enemy-only
through every data route**: BattlePatch's `[Attack]` selector writes only `scene.atk[]` (enemy
attacks, eagerly loaded at BTL_SCENE ctor); the Actions.csv parser has no such column and
hardcodes null. So:
- **Enemy-cast custom summon**: SequenceFile is reachable TODAY via BattlePatch — our
  `battlepatch.py` just needs a `sequence_file` key + a String branch in `encode_field`
  (`SequenceFile: CustomSequences/X.seq`, resolved under the mod folder's FF9_Data). The
  battle-tested proving ground.
- **Player-cast**: needs either the fresh-id folder route (data-only, preferred) or a one-line
  runtime write to `FF9BattleDB.CharacterActions[id].Info.SequenceFile` from our per-mod
  **Scripts-DLL** (public statics; the Overload-hub pattern — NOT an engine rebuild). Unproven.

## 3A. Can we crack FF9SpecialEffectPlugin.dll? (workflow `wf_61f380d8-dc4`, 2026-07-21)

Follow-up to "opaque closed-source" — inspected the actual binary + re-read the open source +
web/provenance. Verdict: **the DLL is a soft target, but "crack the DLL" is the wrong frame — for
custom summons nothing needs cracking.** 6/8 load-bearing claims CONFIRMED, 2 PARTIAL (scoping).

### The binary is not a wall
- **435 KB x64 / 348 KB x86**, native C++ (no CLR header), MSVC/VS2013 (linker 12.0, MSVCR120),
  linked 2016-10-19. **Unpacked, unobfuscated, no anti-RE** (normal `/GS` cookies, `.text`
  entropy ~6.5). x64 `.pdata` gives an exact **646 functions**.
- **Leftover debug symbols name the original C++ sources**: `SpecialEffectCode\psx\source\
  psx_compatibility.cpp`, `SpecialEffectCode\sonoda\Geo\{geo,geomorph,geosfxrender,geoslice}.cpp`,
  `sonoda\PsxEmulator.cpp`; PDB path rooted at `…\Honolulu_master\…`. This is **literal ported
  PS1-era Square geometry code** (a "Geo" transform module + an explicit PSX-emulation shim), not a
  novel modern engine.
- **The DLL does not render and does not touch disk**: its import table is only CRT math/alloc +
  9 KERNEL32 timing calls — **zero graphics-API (d3d/gl/dxgi) and zero file-I/O imports**. It's a
  pure CPU-side geometry/animation kernel. It's *fed* a raw `ef###.bytes` buffer via `SFX_Play`
  and *queried* per primitive via `SFX_GetPrim`; Unity does the actual drawing.

### The ABI and the output are already fully decoded in the OPEN source
- **13 exports, 1:1 match** to the `[DllImport("FF9SpecialEffectPlugin")]` block (SFX.cs:716-753)
  — no hidden surface. (SFX_BeginRender, SFX_GetPrim, SFX_InitBattle/System, SFX_LateUpdate,
  SFX_MoveFreeCamera, SFX_Play, SFX_Send{Float,Int}Data, SFX_SkipCameraAnimation,
  SFX_StartPlungeCamera, SFX_Update, SFX_UpdateCamera.)
- **`SFX_GetPrim`'s output is a classic PSX GPU primitive-tag stream** (POLY_F3/FT3/F4/FT4/G3/GT3/
  G4/GT4, LINE, TILE/SPRT, DR_TPAGE/…) walked via an ordering table — and Memoria's own C# already
  interprets it verbatim (SFXRender.cs:79, dispatch :208-315; `PSX_LIBGPU.cs`, `PSX_OT*.cs`). The
  **rendering protocol is not a mystery.**

### The one genuine native-RE gap (which we don't need)
- The `ef###.bytes` **container/opcode/camera sub-formats are ~60% decoded in the open**
  (`SFXBinaryFile.cs` parses the chunk table + SequenceCode stream; `SFXDataCamera.cs`'s
  Load/UpdateBSC round-trips the camera format — the same bytes our `camera_codec.py` writes). BUT
  `SFXBinaryFile.cs` is **dead code, zero live callers** (never validated against a real file), and
  the actual **creature mesh/bone/animation payload is decoded nowhere**. It lives in a bounded
  ~12-function internal `Hi_Summon*` subsystem (Hi_RegisterSummonModel / Hi_SetSummonMotion /
  Hi_GetSummonBoneMatrix / Hi_DrawSummonModel / …) inside the DLL — the ONLY piece genuinely
  inaccessible without disassembly. Small (~2% of 646 fns), but un-tooled, no community prior art,
  and its only prize is **extracting stock Eidolon geometry — which trips the provenance gate.**
- The one tool that touches mesh (`SFXDataMeshConverter`) works by **capturing the DLL's rendered
  output at runtime**, self-describes as "mostly fails" (:9-10), and does not decode the source
  bytes.

### Route ranking (for the custom-summons goal)
| Route | Buys | Effort | Provenance | Needed? |
|---|---|---|---|---|
| **A. Managed bypass** (FileList.txt Model → our FBX pipeline) | the whole new-creature pillar | **low (already built)** | clean | **YES** |
| **B. Managed camera fix** (implement `LoadFromJSON` + the SFX_DATA_CAMERA branch; format already solved) | continuous per-effect camera dolly | low-med, local patch | clean | optional |
| **C. Finish ef###.bytes mesh decoder** | extract/re-encode a *stock* Eidolon's geometry | med-high, no prior art | **risky (SE content)** | no |
| **D. Native disasm of the DLL** (Ghidra/IDA on the ~12 `Hi_Summon*` fns) | the internal creature codec | high vs narrow payoff | RE-to-understand ok; extracted content / patched DLL not | no |

- **Route A never calls the native DLL**: with a `FileList.txt` Model line, `SFXData.LoadSFX` sets
  `mesh` and **returns before `loadingQueue.Enqueue` / `SFX_Play`** (SFXData.cs:156-181, verified).
  For an all-new summon the plugin is simply not in the loop.
- **Provenance line** (PROVENANCE.md): a functional **parser** for the format is committable
  (code); **decoded/extracted stock bytes are not** (SE content → gitignored/local, the
  battle-import precedent). Reading the DLL for understanding is fine; shipping a patched/
  redistributed DLL is not (also the never-PR-upstream rule → any managed fix stays on
  `memoria-patches/`).

### Corrections folded in
- GitHub issue #917 is about camera/timing **polish glitches in working playback** (14/16 subs
  closed), NOT evidence about format-decode difficulty — don't cite it for that. The real
  community confirmation of hardness is discussion #1002 (Tirlititi) + tasior2's "Rəverse FF9"
  (reads static PSX geometry off `.IMG` only — never animation, never the PC `ef###.bytes`).
- The 487 stock effect folders span ef000-ef510 **non-contiguously** (24 absent ids, 25 with only
  a PlayerSequence.seq) — the choreography layer is loose text regardless (no DLL involved in
  reading it: `UnifiedBattleSequencer` via `AssetManager.LoadString`).

**Bottom line for the pillar:** ignore the DLL. Route A (managed bypass) is the whole thing and is
already code-complete + provenance-clean; Route B (managed camera patch) is the only worthwhile
follow-on, and it's wiring an already-solved format, not reverse engineering.

## 4. Architecture tiers (post-verification)

| Tier | What | DLL? | Fidelity | Status |
|---|---|---|---|---|
| **1. Borrowed cinematic** | Custom ability's `vfx1/vfx2` = a stock summon's ids (Bahamut 227/405, Ark 381/447…). Plays the donor verbatim — native creature, real camera, sounds. | no | vanilla-identical, zero novelty | Expressible with today's kit; unproven binding |
| **2. Redressed donor** | Private **fresh-id folder** carrying an edited copy of the donor's .seq: retimed Waits, minted `PlaySound` ids (`sound.mint_song`, sfx≥100000), moved `EffectPoint`, `Message` text, extra `CreateVisualEffect` flourishes, `PlayCamera` choices. `LoadSFX: SFX=<donor>` keeps the native creature + its forced cinematic camera. No shared-folder collision (the text-block-shadow lesson, pre-applied). | no | donor creature, bespoke pacing/sound/beats | .seq format fully mapped; unproven |
| **3. Composed original** | Fresh id + `FileList.txt Model` → `.sfxmodel` with `FBX` entries = **our own rigged/animated creature** via the proven model pipeline; Sprite-JSON particles; blackout + ShiftWorld + PlayCamera cuts; minted audio; authored EffectPoint. | no | fully novel creature + multi-phase choreography; camera = cuts/shift | The central bet; zero precedent |
| **3.5 Epic camera** | Extend `camera_codec.py` from opening slots 0-2 to attack-sequence slots 3-8 (raw17 bytes the native plugin reads) → real multi-segment mid-battle sweeps for the custom summon. | no | continuous authored camera | New work on a proven substrate |
| **4a. Cheap engine lever** | Generalize `DecideSummonType`/achievements to custom ids (pure managed C#, small sNN patch) — only if the short/long + first-cast-long UX is wanted natively. | local patch | UX parity with stock summons | Critic: wrongly bundled with 4b; actually small |
| **4b. Deep engine lever** | Implement the SFX_DATA_CAMERA stub / touch the native plugin boundary. | local patch + maybe native RE | true dolly | Maintainer: "breakthrough" territory. Avoid; 3.5 covers the need |

## 5. The rung ladder (verbatim-first; each rung = one in-game proof)

1. **Borrowed cinematic** — point a minted/custom ability's `vfx1/vfx2` at 227/405 (Bahamut).
   Proof: the full vanilla Bahamut plays from a non-Garnet/Eiko command. Also proves the command
   is selectable/targetable through the real battle HUD (the critic's input-side gap) — the
   [[playable]] minted-command menu wiring is already in-game proven, this composes it with a
   summon-scale effect. **[★ IN-GAME PROVEN 2026-07-21 — "it worked, bahamut played in full."
   Bench `rung1-borrowed-cinematic/`, field 30300, "Bahamut Cinema" minted at id 194 on Iviv's
   Spark (clone of stock row 62; targets=AllEnemy pinned — the ManyAny disjunct at btl_vfx.cs:99
   is the ONLY other Vfx2 trigger, so full-227 is structurally unconditional; Iviv boots 80/80 MP
   ≥ the faithful 56 cost; auto-learned at AP 0). Offline emission probe had verified the live
   Actions.csv row byte-exact pre-playtest. Playtest residue: audio "a little crunchy at times"
   → the open audio question (§8).]**
2. **Hot-loop probe** — mod-folder-override the donor's own `ef227/PlayerSequence.seq` with one
   retimed Wait + one minted-sound `PlaySound`. Proof: the edited beat lands; establishes the .seq
   edit→recast loop + mod-folder resolution + custom-audio-in-.seq. (Throwaway: this rung edits
   the SHARED folder — vanilla Bahamut changes too. Rung 3 fixes that.)
   **[★ IN-GAME PROVEN 2026-07-21 — "both worked, the blip played and the fade was slower." One
   recast, no relaunch: mod-folder .seq shadowing + the per-cast re-parse + DSL injection all
   proven in one shot (`rung2-seq-hot-edit/`; the override carried exactly 2 edits: `PlaySound:
   Sound=103` first line + blackout fade Time 12→45). The ef227 override is REVERTED (stock
   Bahamut pristine; selective revert — `remove_seq_override` only). Track B — minted sfx id
   100000, the synthetic 880Hz chime (zero SE bytes) — REMAINS STAGED in the manifest + Sounds
   tree (SoundMetaData loads once at process start), arming on the next relaunch: rung 3's cycle
   closes §8's minted-id question with a hot-added `PlaySound: Sound=100000` recast.]**
3. **Fresh-id private copy** — mint an unused id <511; ship `ef{N}/PlayerSequence.seq +
   Sequence.seq` as the donor's copy (`LoadSFX: SFX=Bahamut__Full` by NAME). Proof: plays
   identically under id N while stock Bahamut is untouched → the global-namespace collision is
   dead, and the fresh-folder mechanism itself is proven (half of rung 6 early).
   **[BUILT + DEPLOYED 2026-07-21 → `rung3-fresh-id/`, id N=84 (the recon censused ALL 24 absent
   folder ids 0-510 — they map 1:1 to SpecialEffect.cs's own `Unused_N` aliases; 84 = the mildest
   documented legacy fallback). Key recon law: the folder id is consulted EXACTLY ONCE per rework
   cast, as a path string — everything downstream (SFX.Play, playParam, LoadSfxSoundData,
   FixedCameraEffects) keys on the .seq's NAME-resolved 227, and the copy's own Sequence.seq is
   never even read on the player path (the nested LoadSFX reads the DONOR's ef227/Sequence.seq) —
   §8's LoadSfxSoundData fresh-id question is thereby ANSWERED BY CONSTRUCTION for donor-borrowing
   rungs. Deployed: ef084 verbatim pair + the bench toml redeployed on 30300 (row 194 now
   `84;405`, verified live). ★★ FULLY PROVEN 2026-07-21, BOTH CASTS: cast A "worked, looked
   identical to before" (the fresh-id private copy is indistinguishable, stock ef227 untouched —
   the global-namespace collision is DEAD); cast B "the chime played at the start" (the
   `--with-chime` recast — THE FIRST CUSTOM-MINTED AUDIO EVER PLAYED INSIDE A SUMMON SEQUENCE;
   §8's minted-PlaySound question CLOSED; the ef084 copy since restored verbatim). CRUNCH NOTE:
   "crunch still reduced" across both casts vs rung 1 — two consistent data points for the
   cold-cache candidate (the AKB/OGG decode disk-caches after first-ever play), still not
   conclusive per the user; the §8 A/B stands for a proper pin-down.]**
4. **Damage-beat control** — move `EffectPoint` in the private copy. Proof: damage visibly lands
   at the new beat.
   **[BUILT + DEPLOYED 2026-07-21 → `rung4-effectpoint/` (recast pending). DESIGN CORRECTION vs
   the ladder's wording: EffectPoint lives in the DONOR's ef227/Sequence.seq, which the cast
   nested-loads by RESOLVED id (the private ef084/Sequence.seq is never read) — so rung 4 rides
   the rung-2-proven shared-override class, throwaway until `revert_rung4.py`. The recon confirmed
   the nested load is the SAME mod-stacked zero-cache AssetManager.LoadString path (File.ReadAllText
   per cast, fresh SFXData per LoadSFX op — recast-only, no relaunch) and produced THE FULL TICK MAP
   of Bahamut's 73-line Sequence.seq (t=0 blackout … t=434 Mega-Flare ramp … stock EffectPoint at
   t=486/498, ~32.4s in; every HoldDuration self-consistent). The move: the EffectPoint pair
   (12-tick gap preserved) relocated to immediately after the opening blackout (~1.2s in) —
   anchor-block matched, DriftError-guarded, idempotent. ★ PROVEN 2026-07-21 — "it worked, damage
   numbers popped up right after the blackout": the hit landed at the new beat (hit SFX + HP
   damage confirmed) AND the number was ABSENT from its usual mid-flare spot — double evidence the
   beat moved. The override is since REVERTED (stock resolution restored). MINTED EN ROUTE — **THE
   FIGURE-VISIBILITY LAW**: the damage-number popup renders occluded/washed out under the
   fullscreen SetBackgroundIntensity overlay (the user saw the hit only via SFX; the number hid
   "behind the whiteout") — a composed summon (rung 8) must schedule `EffectPoint Type=Figure` in
   a LIT window if the numbers should read.]**
5. **Particle layering** — add `CreateVisualEffect: SFXModel=Common/ChannelSummon.sfxmodel` (then
   a bespoke Sprite .sfxmodel). Proof: our particle renders inside the donor cinematic.
   **[BUILT + DEPLOYED 2026-07-21 → `rung5-particles/` (stage A live, casts pending). HEADLINE
   RECON FIND: `CreateVisualEffect` has ZERO stock usages across all 487 ef folders — our line is
   the FIRST-EVER use of the op in any .seq; syntax derived from source, not examples. THE OP LAWS:
   the `SFXModel=` key alone selects the mode; `Char=Caster` is REQUIRED in practice (absent Char →
   a 0 bitmask → silent render-on-nobody); the path must be FULL Data/-rooted (no auto-prefix at
   this call site — `Data/SpecialEffects/...`); `Time/Size/Speed` are PARSED BUT INERT for
   SFXModel mode (all timing/scale lives in the JSON); the effect is fire-and-forget
   (self-terminates past its own lastFrame; 0-tick op). Baseline: the bare `Channel` op for minted
   cmd_no=46 falls to the SPELL case (pale gray-blue-white) — so stage A's added ChannelSummon
   aura (green/burnt-orange) is visually distinct. The FIGURE-VISIBILITY law does NOT apply here
   (particle draws ride a different path than the Type=Figure UI — source-read). Stage A (live) =
   the stock ChannelSummon aura layered into the chant window of the PRIVATE ef084 copy; stage B
   (built, deploy-tested once, waiting) = `rung5_sprite.sfxmodel` — a bespoke kit-owned no-texture
   16-tri octagonal RISING RING, magenta (no stock aura uses it), fade-in/expand/rise/fade over
   ~2.4s. ★★ FULLY PROVEN 2026-07-21, BOTH CASTS: cast A "I can see both auras during the chant"
   (the op's first-ever exercise — additive layering confirmed, the stock ChannelSummon aura over
   the Spell-case baseline); cast B "the magenta ring appeared during the chant" — **THE FIRST
   GENUINELY NEW VISUAL CONTENT EVER RENDERED INSIDE AN FF9 SUMMON** (a hand-authored no-texture
   Sprite .sfxmodel, zero SE bytes). The ef084 copy restored verbatim post-proof. Tier-3's
   Sprite-particle half is now in-game proven; only the FBX half (rung 7) remains unexercised.]**
6. **Fresh-id bare sequence** — id N with a trivial .seq and NO LoadSFX of any native id. Proof:
   graceful play (chars animate, sound, damage) with no native content at all → Tier 3 is viable;
   also observes what a camera-ownerless effect looks like.
   **[BUILT + DEPLOYED 2026-07-21 → `rung6-bare-sequence/` (recast pending; the fresh-id half was
   proven by rung 3, so this swaps ef084's content — recast-only). THE CAST-PROTOCOL GRAMMAR
   DECODED (3 simple stock spells = one 67-line template + the donor): `cmd_status` = a pure
   target-cursor visibility bitfield (bit 2), NOT load-bearing; the reflect triple is required
   only for category-bit-0x1 abilities (Bahamut's 22 clears it — inert, kept for convention);
   **THE ANIM=IDLE RELEASE LAW** — the literal string "Idle" is engine-recognized as
   releaseCmdIdle (`btl_mot.EndCommandMotion` + `SetDefaultIdle`), THE canonical command-motion
   release, and a looping clip is broken only by a SUBSEQUENT PlayAnimation call (no StopAnimation
   op exists); a Loop=True WaitAnimation resolves at loop-wrap (never hangs). The deployed 25-op
   bare sequence: banner → chant → half-dim (0.5, Figure-law compliant) → chime + magenta ring →
   MP_MAGIC gesture → re-light → EffectPoint pair LIT → Anim=Idle close-out. Zero native content;
   ef084/Sequence.seq present but unreachable (no LoadSFX to nest-load it).
   ★★ FULLY PROVEN 2026-07-21 (two casts): cast 1 — the chant played, THE CHIME AND RING PLAYED,
   the ~3000 damage landed with VISIBLE numbers (Figure-law window worked), and the battle ended
   normally: the completion chain held with zero native content, TIER 3 IS VIABLE. The one
   anomaly (SetBackgroundIntensity looked inert) was TRACED AND RESOLVED — the gate hypothesis
   was REFUTED by the source (the write→static-tween→Loop-tick→setBGColor chain has NO SFX gate;
   it runs unconditionally every battle frame), and the probe cast proved it: `Intensity=0`
   produced the full blackout ("the background went black during the chant"). **THE INTENSITY
   SUBTLETY LAW**: mid intensities (0.5) only nudge the BG materials' `_Intensity` shader float —
   imperceptible under the default caster-framing camera; `Intensity=0` EXACTLY takes the
   renderer.enabled=false branch = the vanilla-blackout drama. For legible mid-dims, pair with a
   `PlayCamera` that foregrounds the background (a plain data-only op, works without LoadSFX —
   the camera engine runs all battle regardless). Camera answer: a bare cast runs under the
   default per-command battle camera (nothing moves it without PlayCamera/LoadSFX). The committed
   bare sequence ships the proven 0-dim version.]**
7. **THE creature rung** — `FileList.txt` + `Model our.sfxmodel` + `FBX` → a placeholder mesh from
   our model pipeline renders mid-cast. Highest-risk, highest-value; zero precedent anywhere.
   (Fallback if it fails: spawn the creature as a battle-actor model instead — our skinmint band —
   choreographed via ShowMesh/PlayAnimation; or prove the mechanism enemy-side first via the
   BattlePatch SequenceFile route, which is the more battle-tested load path.)
   **[BUILT + DEPLOYED 2026-07-21 → `rung7-creature/` (cast pending; verifier READY, zero
   blockers). THE CHAIN IS SILENT-SKIP-CLASS BY DESIGN (recon walked every failure site: missing
   Path → entry dropped; unloadable FBX → ModelFactory null → continue; bad clip → stripped;
   malformed JSON → Load null → skip — no crash sites reachable from our data). THE GRAMMAR LAWS:
   FileList.txt tokens split on SINGLE SPACES (tabs/double-spaces break silently); multiple Model
   lines COMPOSE onto one mesh list; `LoadSFX: SFX=84` numeric parses Int32-first; a `Camera`
   line is INERT (the dead LoadFromJSON stub, re-confirmed at this call site). THE MOVEMENT TRAP:
   an FBX entry with no Movement sits at WORLD ORIGIN (wrong place, not invisible) — the build
   pins an explicit static CasterPosition-anchored curve. Asset = Iviv's own GEO 6100 (already
   loading on this install; ZERO new bytes staged). The deployed sequence = rung 6's proven
   skeleton + a ~4s reveal DURING the blackout (setBGColor disables only the battle-bg model's
   renderers — the SFX mesh renders independently: a silhouette-against-black reveal), End=60
   auto-destruct, then re-light → damage → close-out.]**
8. **The composed epic** — full multi-phase original: buildup channel → blackout → creature reveal
   → attack → EffectPoint → resolution, minted music sting, PlayCamera cuts. Proof: a bespoke
   summon start-to-finish, zero DLL.
9. **Epic camera** (stretch) — camera_codec extended to attack slots 3-8; a continuous authored
   sweep during rung 8's summon.

## 6. Verified-claims ledger

| Claim | Verdict |
|---|---|
| Numeric folder lookup un-gated (any id resolves) | CONFIRMED |
| VfxIndex/Vfx2 raw numbers, no validation | CONFIRMED |
| FBX path = the proven ModelFactory loader | PARTIAL (mechanism confirmed; real site = SFXDataMesh.cs:744 `JSON.Begin()`, not ModelSequence) |
| playParam[511] silent Fire__Multi fallback | CONFIRMED (+ negative ids throw; kit validator over-permissive) |
| Summon gate = 3 command ids + 16 ability ids | CONFIRMED |
| SequenceFile player-scope | PARTIAL → RESOLVED: enemy-only via data; read side un-gated; player = Scripts-DLL write or fresh-id folder |
| SFX_DATA_CAMERA stub dead | PARTIAL (true; but camera_codec.py is a proven data-only dolly sibling, opening-scoped) |
| Camera-owning effects = native plugin every frame | CONFIRMED |
| SFXRework default-on (+ forced at Speed≥3) | CONFIRMED |
| No sequence length ceiling | CONFIRMED |
| Zero precedent for FileList.txt/fresh-id | PARTIAL (487 folders, 0 uses — confirmed; community universal-negative unverifiable) |
| Minted-command band (46,35-40) ∩ {16,18,20} = ∅ | CONFIRMED |

## 7. Risks

- **First-of-its-kind**: the FBX-in-effect mechanism is code-proven, never run. Rungs 6-7 are
  cheap kill-tests before creature investment.
- **Netsync collision (critic)**: a long summon freezes global ATB for its whole runtime;
  `NetSyncBattle.GuestWaitMs` default 30000ms is documented as the max continuous freeze on the
  s37 B0/B1 path — a stock Ark already brushes tens of seconds. Whether the s40/s41 diorama path
  shares that ceiling is UNRESOLVED — check before shipping an intentionally multi-minute summon.
- **Per-language text (critic)**: the ability's name/flavor text must follow the kit's LANGS laws
  (the VANILLA-SQUAT class of bug); verify the existing [[playable]] ability-text path covers it.
- **ScriptId 87** collides with Odin's Sword SA; avoid for custom summons.
- **Silent-skip DSL**: unknown .seq ops are dropped without error → the kit linter must own typo
  detection offline.
- **In-battle load hitch (critic)**: a fresh skinned FBX + long sequence loads mid-fight with no
  fade to hide it; unmeasured. Watch on rung 7.
- **`SFXRework=0`** users get silent no-ops → deploy-time warn.
- **Save/achievement sizing** (critic, low-confidence): AchievementState fields are per-stock-
  summon; customs never touch them (no DecideSummonType entry) — believed inert, unverified.

## 8. Open questions (rung-mapped)

- Fresh id: graceful in ALL paths incl. sounds (`SoundLib.LoadSfxSoundData(effNum)` on a fresh id)?
  → rung 6.
- Does `SequenceFile` (enemy route) cover both caster and target halves? → the enemy-side spike.
- Can one `.sfxmodel` compose multiple FBX entries (circle prop + creature + impact)? → rung 7-8.
- Do arena camera slots 3-8 give usable framing, per-arena? → rung 9 groundwork.
- Diorama-path freeze ceiling (see §7). → before shipping.
- `PlaySound` with minted ids ≥100000 inside a .seq — **★ CLOSED 2026-07-21 (rung 3 cast B):** the
  minted sfx id 100000 (manifest-registered loose Ogg, zero SE bytes) played from a hand-authored
  `PlaySound` line inside the private summon copy — "the chime played at the start." Custom audio
  in a summon sequence is PROVEN. (Reminder law: SoundMetaData's id table loads once at process
  start — a fresh minted id always needs one relaunch to arm before its first use.)
- **THE CRUNCHY-AUDIO QUESTION — INVESTIGATED 2026-07-21 (3-lens workflow, engine + web + install):**
  the crunch is NOT our binding (the bench plays ef227 as itself; the pitch-table switch keys purely
  on the effect id, so a stock Garnet cast runs identical low-level audio code). Findings:
  (a) **the legacy SFX.cs summon-sound layer (AdjustSoundIndex/SoundPlay pitch tables, StreamPlay's
  1.3× volume) does NOT run live under rework** — it was export-tooling whose output got BAKED into
  the shipped .seq PlaySound lines; live audio = .seq `PlaySound` → SoundEffectPlayer → SaXAudio;
  (b) **structural: NO limiter/compressor anywhere in the SaXAudio chain** (AudioEffectManager =
  Reverb/Eq/Echo/Volume only) — any voice stack on BusSoundEffect hard-clips; the stock Summon
  channel fires 3 simultaneous full-volume sounds on one frame at every summon charge-up, RunThread
  overlap triggers a force-stop/restart dedup (0.1s fade), and Speed=5 simultaneous ATB multiplies
  stacking; (c) **community: the vanilla PC-port summon SFX assets are known-poor** ("squeaky,
  pitchy" Silicon Studios re-creations of lost-source audio; Bahamut singled out even post-Moguri)
  — an asset-quality ceiling fixed only by sound-replacement mods (FFIX Sounds Fix v2.2 / Moguri
  "PlayStation Sounds"); #193 = abrupt StopSound clicks on Bahamut__Short specifically; a SaXAudio
  OnBufferEnd race was fixed on Memoria canary 2026-07-19 (PR #1453, crash-class, post our pin);
  (d) **install: Backend=1 (recommended — the Soloud-48kHz candidate ruled out), Moguri ships ZERO
  audio (ruled out), PriorityToOGG is a no-op here (no loose .ogg exists for this content), and
  `[Cheats] SpeedMode=1` (default ON) multiplies pitch by the F1 fast-forward factor if engaged.**
  **THE 2-STEP A/B (user):** 1) recast with F1 fast-forward certainly OFF ($0, same session);
  2) flip `[Audio] Backend` 1→2 + relaunch + recast — clean under Soloud ⇒ SaXAudio resampler
  artifact (run Backend=2); same crunch ⇒ the shared pitch-table/asset territory ⇒ the fix is an
  audio-replacement mod, not the kit. Optional decisive third: `[Hacks] AllCharactersAvailable=1`
  → a real Garnet Bahamut on the same install (predicted identical — full binding exoneration).

## 9. Kit work items (when the build starts)

1. `[[summon]]` (or extend `[[playable]]`/`[[battle_action]]`) — mint ability + fresh effect id
   (<511 hole allocator with a committed used-id table) + emit the `ef{N}/` folder from a
   declarative block or a `.seq` source file.
2. **.seq codec/linter** — parse/emit the DSL, closed op+arg vocabulary from BattleActionCode.cs
   (the silent-skip guard), thread/termination checks; a `summon-seq` disasm/catalog CLI over the
   487 stock folders (donor browsing; FixedCameraEffects flags; the missing SpecialEffect catalog).
3. `battlepatch.py`: `sequence_file` in ATTACK_FIELDS + a String `encode_field` branch (the
   enemy-side lever; also unlocks retuning stock attack VFX — `vfx2` is `[PatchableField]` too).
4. `actiondelta.py`: tighten vfx1/vfx2 warning at ≥511 (playParam bound). **★ DONE 2026-07-21**
   (WARN not error — the bound gates SFX.Play/LoadSFX targets, not the folder lookup; both encoder
   branches + the animation1/2 aliases covered, boundary-tested 510/511. The SFXRework=0 deploy-warn
   is DEFERRED to the first .seq-emitting rung: rung 1 is rework-independent by construction — ef227
   is real content under BOTH engines — and the deploy tooling has no "fresh id vs donor reuse"
   signal yet; gate it like deploy_field's Folklore `[Import]` check when it lands.)
5. `.sfxmodel` emitter — Sprite first (5 shipping references), FBX manifest second (reuse the
   model pillar's FBX output).
6. Deploy: the ef-folder tree rides the normal mod-folder copy; no DictionaryPatch registration
   needed (path-addressed, not id-registered) — verify on rung 2.
7. Later: camera_codec attack-slot extension (rung 9); the 4a managed patch only if wanted.

## 10. Sources

- Engine: `C:\gd\FFIX\Memoria\Assembly-CSharp` — UnifiedBattleSequencer.cs, BattleActionCode.cs,
  BattleActionThread.cs, SFXData.cs, SFXDataMesh.cs, SFXDataCamera.cs, SFXChannel.cs, SFX.cs,
  btl_vfx.cs, btl_cmd.cs, BTL_SCENE.cs, BattleCommandInfo.cs, AA_DATA.cs, BattleActionEntry.cs,
  SpecialEffect.cs, BattleCommandId.cs, BattleAchievement.cs, btl_sys.cs, TranceStatusScript.cs,
  BattleHUD.Public.cs, HonoluluBattleMain.cs, battlebg.cs.
- Install: `StreamingAssets/Data/SpecialEffects/` (487 ef + Common), Actions.csv,
  AbilityFeatures.txt, Memoria.ini.
- Kit: battle/{actiondelta,battlepatch,seqcodec,seqasm,seqauthor,camera_codec,camera_data,
  characterdelta,skinmint,deathrules}.py, content/playable.py, sound.py.
- Community: Memoria wiki Battle-SFX-Sequence / Battle-Patch / Active-ability-features /
  SPS-and-SHP-Effects / Model-Viewer; issues #917, #193; discussion #1002.
- Workflow artifacts: run `wf_820cd689-2a9` (recon/synthesis/verification JSON in the session
  scratchpad).
