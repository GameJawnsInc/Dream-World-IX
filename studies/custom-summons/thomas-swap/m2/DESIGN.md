# M2 DESIGN — the summon-transplant KIT SURFACE (productize the hand-built hybrid pipeline)

> **Scope.** Milestone 2 of `disasm/TRANSPLANT.md` §2.4: turn the hand-built, in-game-proven Thomas
> transplant (M1b, ★★ 2026-07-24 — "it works, thomas flies with the dragon's motion", `m1b/RUNBOOK.md`)
> into declarative kit surface. This doc nails **every** decision a builder needs; nobody downstream
> should have to choose. **No code is written here.** Native read/fork family (`summon-inspect` /
> `summon-fork`) is explicitly **OUT** (§0).
>
> **Citations.** Kit cites are `path:line` relative to `ff9mapkit/ff9mapkit/`. Engine C# cites are
> relative to `C:/gd/FFIX/Memoria/Assembly-CSharp/` (pinned `6b8bb2d5`). Study cites are repo-relative.
> Native RVAs are image-base-relative to `FF9SpecialEffectPlugin.dll`.

---

## 0. What is in / out of scope this round

**IN** — the managed `[[summon]]` transplant lane (TRANSPLANT.md §2.3, "the recommendation"):
- The `[[summon]]` field.toml block (§1), its compiler + registration (§5).
- `summon-deploy` (assets + engine arm) and `summon-import` (the Blender return path) CLI verbs (§5).
- The two runtime lanes: **hybrid** (the s58 SfxHybridDrive engine feature, the default) and **overlay**
  (the DLL-free rung-7 FileList/`.sfxmodel`/`.anim` route).
- Reuse (never re-invent): `summon-export`/`summon-rig-ref` (already ship, `cli.py:5637`/`5661`);
  `models/mint.py`; the `.anim` writer `models/anim.py:clip_to_anim_json` (`:102`); the Memoria.ini
  writer pattern from `coop.py` (`:294`/`:361`); the `vfx1` ability lane (`battle/actiondelta.py:64`).

**OUT — one line, per the brief:** the native read/fork family — `summon-inspect` / `summon-disasm` /
`summon-fork` on `ef_container.py` + `ef_geom_writer.py` — is a **separate surface** with different
provenance rules and failure modes (TRANSPLANT.md §2.3); it is **not** merged into `[[summon]]` and is
not touched this round.

---

## 1. THE `[[summon]]` BLOCK SCHEMA (field.toml)

A `[[summon]]` block declares one transplant: "wear stock donor D's cast with my model M." It lives in
a field.toml (the bench field, or whatever battle-adjacent field owns the cast). Unlike `[[coop]]` /
`[[platform]]` / `[[savepoint]]`, it emits **no `.eb` bytecode** — it compiles to **asset artifacts +
an engine-arm manifest** (§2). Full worked example, every key, with its default and its source:

```toml
[[summon]]
# --- identity: which cast, which model, which lane ---
donor      = 227                    # REQUIRED. numeric effect id OR the SpecialEffect name "Bahamut__Full".
                                    #   The native cast whose live bones/camera/staging we inherit.
model      = "thomas_skinned.fbx"   # REQUIRED. the user's OWN retargeted mesh on the bone000..092 rig
                                    #   (a path; a bare name resolves under the field's asset dir).
lane       = "hybrid"               # "hybrid" (s58 drive — DEFAULT) | "overlay" (DLL-free FileList route)

# --- the mint (reuses models/mint.py — see §1.2) ---
id         = 6201                   # OPTIONAL. mint GEO id; default = next free in the 6000 band
name       = "GEO_MON_B0_M201"      # OPTIONAL. GEO name; default = derive_mint_name(id) with group MON
group      = "MON"                  # OPTIONAL. silhouette family token -> ModelType (MON=3). default MON

# --- the sequence host (the private, stock-absent ef id — see §1.3) ---
private_ef = 84                     # OPTIONAL. the ef### that hosts the cast .seq; default = auto-alloc
                                    #   the first stock-ABSENT id (§1.3). Bench value: 84 (Unused_84).

# --- hybrid-lane engine knobs (map 1:1 to [SfxHybrid], §2.3) ---
hide_native        = true           # -> HideNative   (default true)
hide_mask          = "0x3"          # -> HideMask     (default (1<<donorMeshCount)-1 from summon-inspect)
node_count         = 93             # -> NodeCount    (default = donor bone count from summon-inspect)
apply_column_scale = false          # -> ApplyColumnScale (default false — CALIBRATION.md §5)

# --- optional data-path body hide (defense-in-depth; overlay-lane body hide) ---
hide_meshes = ["0033B990","0033B9D0","0035BAD0","0035BA90","0034BA10","0034BA50","0097BD02"]
                                    # OPTIONAL. mesh KEYS spliced onto the host .seq PlaySFX line as
                                    #   `HideMeshes=0x..`. Default: OMITTED for hybrid (HideNative does
                                    #   the real hide). Bench value = the 7 censused Bahamut body keys
                                    #   (build_thomas.py:174-179).

# --- overlay-lane-only keys (ignored when lane="hybrid") ---
clips   = "all"                     # which decoded donor clips to bake to .anim: "all"|"none"|index list
staging = "donor"                   # "donor" (host .seq nests the donor cast for camera+fly-by) |
                                    #   "curves" (authored .sfxmodel Movement/Rotation/Scaling). default "donor"
```

### 1.1 `donor` — accept numeric OR name (decision: BOTH)

Accept a numeric id (`227`) **or** the `SpecialEffect` enum name (`"Bahamut__Full"`). **Numeric is
canonical** — it is what `[SfxHybrid] EffectId` takes (S58-DRAFT.md §2.1), what the `ef{id:D3}/` folder
is named (FBX-PATHS.md Hop 0), and what the probe logs. A name is resolved to its id through the same
`SpecialEffect` catalog the `.seq`'s `PlaySFX: SFX=<name>` line uses (`SpecialEffect.cs`), and the
resolved **name** is carried forward because the host `.seq`'s nested `PlaySFX: SFX=<name>` needs it
(the donor line is `PlaySFX: SFX=Bahamut__Full ; Reflect=True`, `build_thomas.py:144`). Validate: the id
must be a real donor with an `ef{donor:D3}.bytes`/creature (not one of the absent ids); refuse otherwise.

### 1.2 mint id / GEO name — reuse `models/mint.py` verbatim

Follow the existing mint band, do not invent a second one:
- `id` default = the next free id ≥ `MINT_BAND_START` (=6000, `models/mint.py:31` — "first id clear of
  every real GEO id, real max 5511"). The bench pinned **6201** (the skinned hybrid Thomas;
  `m1b/stage_mint.py:30`), distinct from `build_thomas.py`'s 6200 (the older rigid overlay Thomas).
- `name` default = `derive_mint_name(source_geo, id)` → `GEO_<GRP>_B0_M{id-6000:03d}` (`mint.py:46-55`).
  `M201 = 6201-6000` reproduces the bench's `GEO_MON_B0_M201` exactly.
- `group` → `ModelType` via `type_int_of_name` (`mint.py:35`): `MON`→3, `MAIN`→2, `SUB`→5 … The
  `typeInt` drives the deploy path `Models/{typeInt}/{id}/{id}.fbx` (FBX-PATHS.md Hop 6). Bench: `MON`→3.
- The block calls `mint.resolve_mint({"id":id,"name":name,"fbx":model_path})` (`mint.py:109`) — the same
  entry `[[mint]]` uses — so the FBX + `Thomas_d.png` deploy and the `3DModel <id> <name>` DictionaryPatch
  line are produced by the proven mint path (see §2.2). **RELAUNCH-gated** (a new `3DModel` id registers
  only at launch — `DataPatchers.cs:591-613`).

### 1.3 `private_ef` — the stock-ABSENT sequence-host id (allocation + declaration)

The cast trigger routes through a **private** effect id that hosts the `.seq` and (overlay lane) the
JSON mesh — never the donor's own folder (FBX-PATHS.md §3, the **donor-FileList replacement law**:
`if (mesh != null) return` at `SFXData.cs:349` fires before the native `Runtime` enqueues, so a
`FileList.txt` in `ef{donor:D3}/` silently kills the whole native cast — fatal to the hybrid, which
needs `ef227`'s native engine actually running so `*(SummonData+0x38)` has real bones).

- **The absent set** — the 24 stock-absent effect ids (the summon PLAN.md §census + `SpecialEffect.cs:496-519`
  `Unused_*` aliases; the bench uses **84** = `Unused_84`, `rung3-fresh-id/build_rung3.py:78`). rung 3
  censused all 24; that census is the allocation pool.
- **Default = auto-alloc.** Pick the first id in the absent set whose `ef{id:D3}/` folder does **not**
  exist in ANY stacked mod folder **and** whose base install has no `ef{id:D3}.bytes` (mirror rung 3's
  `Test-Path .../ef084 == False` gate, `rung3-fresh-id/README.md:38`). Declare it explicitly (`private_ef = 84`)
  to pin the bench value / to reuse one id across several `[[summon]]` blocks in a field.
- **Validator (refuse, don't guess):** a `private_ef` that (a) is not in the absent set, (b) has real
  `ef{id:D3}.bytes`/content in the install, or (c) equals `donor`, is a hard error.

### 1.4 how the CAST TRIGGER wires — the `vfx1` ability lane (pairing, NOT re-invented)

**The `[[summon]]` block does NOT compile the ability.** The cast fires through the existing ability
→ effect lane: an `Actions.csv` row's `animationId1` column (kit key **`vfx1`**, `battle/actiondelta.py:64`)
points at the **`private_ef`** id. The pairing:

1. The player's summon command (the bench: Iviv → Spark → "Bahamut Cinema", `m1b/RUNBOOK.md`) is an
   ability whose `vfx1 = private_ef` (84).
2. Casting it loads `ef{private_ef}/` → reads `ef084/PlayerSequence.seq` (LoadSequenceFromFile,
   `SFXData.cs:348`). That host `.seq` is a drift-guarded copy of the **donor's** own `.seq`
   (`build_thomas.py:973-976`), so it runs the donor's `PlaySFX: SFX=Bahamut__Full` line — spawning the
   **native donor cast (227)** with its real camera, staging, damage timing, and (§2.3) live bones.
3. The s58 drive (`[SfxHybrid] EffectId=227`) poses the model onto **227's** live bones every frame; the
   `private_ef` is just a sequence host with no creature of its own (`Unused_84` has no `ef084.bytes`).

**The block's responsibility stops at the private-ef `.seq` + the model + the ini.** Wiring `vfx1` is
the user's existing battle-authoring step (`authoring-ff9-battles`, `battle/actiondelta.py`) — documented,
not reinvented. The block's lint SHOULD emit a reminder ("point an ability's `vfx1` at `private_ef=84`")
but MUST NOT edit `Actions.csv`.

### 1.5 `hide_meshes` / `hide_mask` — the two hide mechanisms

Two independent body-hides exist; the block exposes both:
- **`hide_mask` (engine, hybrid only)** → `[SfxHybrid] HideMask`, one runtime write to `SummonData+0x20`
  (S58-DRAFT.md §2.3, D4). Default `(1<<donorMeshCount)-1` from `summon-inspect` (`0x3` = Bahamut's 2
  meshes). This is the real, proven total-hide the M1b cast ran under (RUNBOOK.md verdict: "PRIM volume
  halved 549k→264k, body prims truly absent").
- **`hide_meshes` (data path, `.seq`)** → `HideMeshes=0x..` keys spliced onto the host `.seq` PlaySFX line
  (`build_thomas.py:182-195`, `TryGetArgMeshList` @ `BattleActionCode.cs:394-419`). For the **hybrid**
  lane it is **defense-in-depth** (kept as the m1b-bench shape but redundant under HideNative). For the
  **overlay** lane (no engine feature) it is the **only** body hide. Default: omit for hybrid unless
  reproducing the bench; the bench's 7 censured keys are the acceptance value (§4).

---

## 2. THE DEPLOY CONTRACT (`summons/deploy.py`)

### 2.1 What files land where (per FBX-PATHS.md §4)

Given `donor=227, model, id=6201/GEO_MON_B0_M201 (typeInt 3), private_ef=84, lane`:

| # | artifact | destination (under the mod folder root) | lane | mechanism / cite |
|---|---|---|---|---|
| 1 | user's retargeted FBX (+ texture PNGs) | `StreamingAssets/Assets/Resources/Models/3/6201/6201.fbx` (+ `Thomas_d.png` alongside) | both | `mint.resolve_mint` (`mint.py:109`); textures resolve beside the FBX (FBX-PATHS Hop 7, `ModelImporter.cs:125`) |
| 1b | `3DModel 6201 GEO_MON_B0_M201` | mod root `DictionaryPatch.txt` (append, idempotent) | both | `DataPatchers.cs:591-613`; **RELAUNCH** to register |
| 2 | host `PlayerSequence.seq` | `StreamingAssets/Data/SpecialEffects/ef084/PlayerSequence.seq` | both | drift-guarded copy of donor `ef227/PlayerSequence.seq` + `hide_meshes` splice (`build_thomas.py:864-895`) |
| 3 | `[SfxHybrid]` ini section | `Memoria.ini` (arm step, §2.4) | **hybrid** | mirrors `coop.write_netsync` (`coop.py:361`) |
| 4 | `FileList.txt` (`Model <manifest>.sfxmodel`) | `.../ef084/FileList.txt` | **overlay** | one line, one space (FBX-PATHS Hop 1); **never** the donor folder (§1.3) |
| 5 | `<manifest>.sfxmodel` | `.../ef084/<manifest>.sfxmodel` | **overlay** | `"FBX"[0]."Path"="GEO_MON_B0_M201"` (bare GEO name — FBX-PATHS Hop 4/5) |
| 6 | decoded donor `.anim` clips | `StreamingAssets/Assets/Resources/Animations/6201/<clip>.anim` | **overlay** | `models/anim.py:clip_to_anim_json` (`:102`) at `anim_disc_path` (`:46`); NO `3DModelAnimation` line (FBX-PATHS Hop 8) |

**Hybrid lane** emits **only rows 1, 1b, 2, 3** — it deliberately does **not** write `FileList.txt` /
`.sfxmodel` / `.anim` (those make `ef084` a JSON mesh and belong to the overlay lane). This is why the
§4 acceptance list is exactly those four artifacts and excludes the overlay residue the bench build
happened to leave (§4).

### 2.2 idempotent / revertible

- **Model + DictionaryPatch:** `mint.resolve_mint` writes the loose FBX/PNG and appends the `3DModel`
  line only if absent (`build_thomas.py:mint_thomas:916-922`). Re-deploy = byte-identical. Revert =
  `unmint` (remove the `Models/3/6201/` dir + the DictionaryPatch line, `build_thomas.py:932-960`).
- **Host `.seq`:** `atomic_write_bytes` with readback verify (`build_thomas.py:706-712`). The donor is
  READ (drift-guarded on `EXPECTED_DONOR_SHA256 = 4bc643bf…` `build_thomas.py:141`), never written.
  Revert = restore the private-ef folder's prior state (rung-7 resting state, `build_thomas.py:1016-1042`).
- **`[SfxHybrid]` ini:** a coop-style timestamped backup + in-place section update (§2.4). Revert =
  restore the backup or set `Enabled=0`.

### 2.3 relaunch vs recast

Mirrors the standing law (`m1b/RUNBOOK.md §1`, FBX-PATHS.md §4):

| change | when it takes effect |
|---|---|
| `3DModel <id>` DictionaryPatch line (first deploy of a new mint id) | **RELAUNCH** |
| `[SfxHybrid]` section (read once at process start, S58-DRAFT.md §2.1) | **RELAUNCH** |
| the s58 DLL itself (building/deploying the engine) | **RELAUNCH** |
| `ef084/PlayerSequence.seq` + the loose model `6201.fbx` (+ overlay `.sfxmodel`/`FileList.txt`/`.anim`) | **RECAST** (zero-cache, per-cast reparsed, mod-folder shadowed) |

So the first arm = one relaunch; iterating the model/motion afterward = recast-only.

### 2.4 arming `[SfxHybrid]` — follow the coop `[Netsync]` precedent EXACTLY

The kit already writes `Memoria.ini [Netsync]`; the `[SfxHybrid]` writer reuses that machinery, not a
new one:
- **Backup first, always:** `coop._backup_ini` (`coop.py:352`) → `Memoria.ini.sfxhybrid-bak-<stamp>`.
- **Section update:** `coop.update_ini_section(text, "SfxHybrid", updates)` (`coop.py:294`) — the same
  section-rewrite that survives repeated headers and preserves surrounding sections. Guard every value
  with `coop._check_ini_pair` (`coop.py:260`, refuses embedded newlines/control chars that would splice
  in stray keys) and warn on duplicate keys (`coop.duplicate_ini_keys`, `:226`).
- **Print the diff:** show the before/after of the `[SfxHybrid]` block (the coop verbs print the applied
  keys, `coop.py:374`) so the arm is auditable.
- **REFUSE if the ini is absent** (`coop.write_netsync` returns None / refuses, `coop.py:363`).
- **THE HYBRID-LANE ENGINE GATE (new, decisive):** before writing `[SfxHybrid]`, **string-probe the
  deployed `Assembly-CSharp.dll` for `SfxHybridDrive`** (the `m1b/RUNBOOK.md §0` presence check — the
  UTF-8 type name in `#Strings`; the `./sfxhybriddrive.log` UTF-16LE literal is a second signal). If the
  string is absent, the running engine is stock and the hybrid lane **REFUSES to arm** with a clear
  message ("the hybrid lane requires the s58 SfxHybridDrive engine; deploy the custom Memoria bundle or
  use `lane = "overlay"`"). This is the **engine-independence split** made executable: a **novel** field
  runs on stock Memoria, but the **hybrid** summon lane REQUIRES the custom engine — while the **overlay**
  lane (rows 4-6, DLL-free) MUST work on stock and is never gated.
- **Confirm-first:** arming mutates the user's live `Memoria.ini` and needs a relaunch — treat it like
  `coop host` (an explicit step, not a silent side effect of `ff9mapkit build`; CLAUDE.md's engine/
  outward-facing actions are confirm-first). The `[[summon]]` block build **stages** the exact
  `[SfxHybrid]` text into a printed ARM manifest (like `m1b/stage_mint.py`'s `ARMING.txt`); the actual
  ini write is the explicit `summon-deploy` arm step (§5).

The armed block for the acceptance (RUNBOOK.md §5, `Log=1` is first-cast-only then set 0):
```ini
[SfxHybrid]
Enabled = 1
EffectId = 227
ModelPath = GEO_MON_B0_M201
HideNative = 1
HideMask = 0x3
NodeCount = 93
ApplyColumnScale = 0
Log = 1
```

---

## 3. `summon-import` SCOPE — the Blender return path

**Input:** the user's `.glb` — their mesh skinned to the `bone000..bone09N` armature that
`summon-rig-ref` emitted (`summons/export.py:export_rig_ref:195`), optionally carrying the dragon's baked
clips (overlay lane only, for staging). **This is the reverse of the export guard**
(`summons/export.py:assert_local_only:70`): export refuses to write stock content OUT of SCRATCH;
`summon-import` accepts the user's OWN retargeted content and packages it INTO the user's OWN mod folder
(verbatim-fork precedent — "the user's — theirs", TRANSPLANT.md §5).

### 3.1 Validation (the export guard's checks, reversed)

- **Bones:** names are `bone000..bone09N`, contiguous from 0, and the parent hierarchy matches the
  donor rig's parent tree (the `summon-rig-ref` parent table is the oracle; the forward `parent<child`
  tree, `summons/build.py:adapt_model` uses `g.parents()`). Renaming/reparenting breaks Unity's
  by-path clip binding (FBX-PATHS Hop 7, `ModelImporter.cs:338-349` builds `bone{id:D3}` parent-by-id),
  so a mismatch is a hard error.
- **Rigidity NOT required for a USER mesh (decision, stated plainly):** the stock creature is rigid
  one-bone-per-vertex (`summons/build.py` module docstring), but that is a property of the *donor*, not a
  constraint on the *user's* mesh. `ModelImporter.CreateCustomModelFromFbx` (FBX-PATHS Hop 7,
  `ModelImporter.cs:48-140`) supports arbitrary skin weights — smooth / multi-bone weights are **legal**
  for a user mesh (the s58 drive writes absolute bone world matrices, `S58-DRAFT.md §2.3`; Unity skins
  `world_v = boneWorld[k]·inverseBind[k]·v` regardless of weight count). Do **not** enforce
  one-weight rigidity on import. (Reuse `models/fbx_validate.py` for the structural FBX checks only.)
- **Textures:** materials reference textures by **bare filename** (path_mode STRIP), so `ModelImporter`
  resolves them beside the deployed FBX (FBX-PATHS Hop 7, `ModelImporter.cs:125`; the bench asserts
  `b"Thomas_d.png" in fbx_bytes`, `m1b/stage_mint.py:66`).

### 3.2 What it emits, per lane

- **hybrid:** stage the FBX (+ textures) at `Models/{typeInt}/{id}/{id}.fbx` into the user's mod folder.
  **No clips** — the drive supplies all motion from the live donor bones. (This IS the whole hybrid
  model deploy; the bench did it by hand from `m1b_stage/`, `m1b/stage_mint.py`.)
- **overlay:** the FBX (as above) **plus** the donor's decoded clips as `.anim` (§3.3) + the `.sfxmodel`
  manifest + `FileList.txt` on `private_ef` (rows 4-6 of §2.1). Optionally the user's `.glb` can carry
  the baked clips directly (retarget-and-keep), in which case those clips are exported to `.anim` instead
  of re-decoding the donor.

### 3.3 Clips — reuse the kit's EXISTING `.anim` writer (named)

The `.anim` writer is **`models/anim.py:clip_to_anim_json`** (`:102`) — the JSON serializer Memoria's
`AnimationClipReader.ReadAnimationClip_JSON` consumes (`models/anim.py:15-21`). **This closes FBX-PATHS.md
§5 open item #2** ("`.anim` byte format not opened"): the format is **JSON, already fully handled by the
kit** — no new serializer, no binary format to reverse. The summon clip struct from
`summons/build.py:adapt_clip` (`:207`) is exactly the `_gltf_io.read_clip` shape `clip_to_anim_json`
takes; `summons/build.py:adapt_all_clips` (`:229`) decodes every donor clip.

Two builder details:
1. `adapt_clip` keys `clip["bones"]` by bone **number** (`"bone000"`); `clip_to_anim_json` writes the
   `"bone"` field as the full hierarchy **path** (the `SetCurve` relativePath). For a summon FBX the path
   is the nested `bone000/bone001/.../boneNNN` chain (`ModelImporter.cs:338-349`), so summon-import must
   map bone-number → hierarchy path (from the rig parent tree) before serializing.
2. Write the `.anim` at `anim_disc_path(mod_folder, id, clipName)` (`models/anim.py:46`) **without** a
   `3DModelAnimation` DictionaryPatch line — the `.sfxmodel`'s `Animations[].Path` references the clip by
   literal path (FBX-PATHS Hop 8), so the summon direct lane does **NOT** use `deploy_new_anim`
   (`models/anim.py:642`, which adds the `3DModelAnimation` registration the ANH-name lane needs and this
   lane does not).

Provenance: the decoded clips are stock-motion-derived → they deploy into the user's own mod folder
(theirs) but the offline decode stays under `C:/gd/SCRATCH/summon-transplant/`; never committed
(TRANSPLANT.md §5, "the user's — verbatim-fork precedent").

---

## 4. THE ACCEPTANCE — regenerate the LIVE M1b deployment byte-for-byte

Feed the productized **hybrid** lane:
`donor=227, model=<C:/gd/SCRATCH/summon-transplant/thomas_skinned.fbx>, id=6201, name=GEO_MON_B0_M201,
group=MON, private_ef=84, lane="hybrid", hide_meshes=<the 7 bench keys>, node_count=93, hide_mask=0x3`
→ into a **staging** mirror (`C:/gd/SCRATCH/summon-transplant/m2_accept/<modfolder>/…`, never the repo /
never mutating the live install — §6). Then byte-compare against the LIVE proven M1b deployment
(READ-ONLY, `m1b/RUNBOOK.md §0`):

| # | staged artifact | must byte-match | source-of-truth |
|---|---|---|---|
| 1 | `…/Models/3/6201/6201.fbx` | live `…/Models/3/6201/6201.fbx` (sha `0c300131…a39e2fe5`, == neutral-bind `thomas_skinned.fbx`) | `m1b/RUNBOOK.md §0` + A/B verdict |
| 2 | `…/Models/3/6201/Thomas_d.png` | live `…/Models/3/6201/Thomas_d.png` | `m1b/stage_mint.py` |
| 3 | `DictionaryPatch.txt` **line** | `3DModel 6201 GEO_MON_B0_M201` present verbatim | `m1b/RUNBOOK.md §0` (appended line 73) |
| 4 | `…/ef084/PlayerSequence.seq` | `splice_sequence(donor_ef227_seq, HIDE_KEYS, include_overlay=False)` — the **m1b-bench no-overlay shape**: the donor `.seq` verbatim with the one line `PlaySFX: SFX=Bahamut__Full ; Reflect=True` → `… ; HideMeshes=0x0033B990,0x0033B9D0,0x0035BAD0,0x0035BA90,0x0034BA10,0x0034BA50,0x0097BD02` | `build_thomas.py:864-895` (`include_overlay=False`), `:174-179` |
| 5 | the `[SfxHybrid]` section text | the §2.4 block (RUNBOOK.md §5), modulo `Log` (first-cast-only) | `m1b/RUNBOOK.md §5` |

**Explicitly EXCLUDED from the compare (by design — do NOT reproduce them):** `ef084/FileList.txt`,
`ef084/creature_manifest.sfxmodel`, and the older `6200`/`GEO_MON_B0_M200` mint. The bench's
`build_thomas.py --m1b-bench` run left these as **overlay-lane residue** (it still wrote a FileList +
the M1a static manifest + the 6200 mint, `build_thomas.py:988-1006`), but they play **no role** in the
proven hybrid render (the drive poses the `6201` skinned mesh from live 227 bones; the overlay Thomas
was removed — RUNBOOK.md verdict "the overlay Thomas removed, s54 the only renderer"). The clean
productized hybrid lane emits only rows 1-5; a builder who reproduces the residue has mis-scoped the
lane.

**Staging note for artifact 4:** the host `.seq` is Square-Enix-derived (a splice of the donor's real
bytes), so a **staged** copy lives under SCRATCH (`build_thomas.py:DRY_RUN_ROOT:659`); the compare reads
the LIVE `ef084/PlayerSequence.seq` READ-ONLY. Artifacts 1-2 (the user's own model) may stage into a
scratch mod-folder mirror.

---

## 5. MODULE / FILE PLAN

### 5.1 `summons/deploy.py` (NEW — the deploy engine; TRANSPLANT.md §3.3 ledger "~120 LOC, MED risk")

Responsibilities (all committable CODE — reads caller-supplied local blobs, embeds no game bytes):
- `emit_hybrid(block, mod_root, game)` — rows 1,1b,2 of §2.1: `mint.resolve_mint` for the model +
  DictionaryPatch; `fetch_donor_seq` + `splice_host_seq` for the host `.seq`; build the printed ARM
  manifest.
- `emit_overlay(block, mod_root, game)` — rows 1,1b,2,4,5,6: the above + `.sfxmodel` + `FileList.txt` +
  the `.anim` clips (via `summons/build.py:adapt_all_clips` → `models/anim.py:clip_to_anim_json` →
  `anim_disc_path`).
- `arm_sfxhybrid(game, updates)` — the ini writer: `probe_hybrid_engine(game)` (the `SfxHybridDrive`
  string-probe gate) → `coop._backup_ini` → `coop.update_ini_section(text,"SfxHybrid",updates)` →
  print diff. Overlay lane skips this entirely (DLL-free).
- `fetch_donor_seq(game, donor)` — read `ef{donor:D3}/PlayerSequence.seq` from the install, drift-guard
  it (an `EXPECTED_DONOR_SHA` registry, `build_thomas.py:141`), never write it back.
- `splice_host_seq(donor_text, hide_meshes, *, overlay=False)` — the generalized `build_thomas.py:864`
  `splice_sequence` (the anchor-line find + `HideMeshes` splice; overlay adds the StartThread self-load).
- `alloc_private_ef(game, mod_root)` / `validate_private_ef(id, donor, game, mod_root)` — §1.3.
- `stage_import(user_glb, block, out)` — the `summon-import` packager (§3): validate + emit per lane.

### 5.2 `content/summon.py` (NEW — the block schema; matches the `content/` convention)

Mirrors `content/coop.py` / `content/platform.py` / `content/savepoint.py`: schema constants
(`LANES = {"hybrid","overlay"}`, defaults), `validate(project, problems)` (all the §1 refusals +
the `vfx1`-reminder lint), and `emit(block, mod_root, game)` that dispatches to `summons/deploy.py`.

### 5.3 Registration point (in `build.py`, exactly like every other block)

- Import near the alphabetical cluster (`build.py:29` `_coop`, `:43` `_platform`, `:51` `_savepoint`):
  `from .content import summon as _summon`.
- `validate(project)` (`build.py:1087`) calls `_summon.validate(project, problems)`.
- The compile/deploy path calls `_summon.emit(...)` — but note the block emits **assets + a printed ARM
  manifest**, NOT `.eb` (contrast `_coop.inject_*` @ `build.py:5184`, `_platform.inject_*` @ `:5406`,
  `_savepoint` dispatch @ `:5482`). The `[SfxHybrid]` ini write is deferred to the explicit
  `summon-deploy` arm step (confirm-first, §2.4).

### 5.4 CLI verbs (decision + justification)

Add via `sub.add_parser(...)` + `set_defaults(func=...)` (the `cli.py:5637` pattern):

- **`summon-import`** — STANDALONE verb (like `model-import`). Input = the user's `.glb`; validates
  (§3.1) and stages/deploys the FBX (+ overlay clips). **Justified standalone:** it operates on a user
  file independent of a field build, exactly as `model-import` does.
- **`summon-deploy`** — the umbrella deploy + **arm** verb, coop-`host`-style. Does the §2.1 asset emit
  (or defers to the block's own emit) **and** the §2.4 `[SfxHybrid]` arm (backup + diff + DLL string-probe
  gate). **Decision — a separate verb, NOT folded into `ff9mapkit build`:** arming mutates the user's
  live `Memoria.ini`, is DLL-gated, and is relaunch-gated — this is the same shape as `coop host`
  (`cli.py:136` `_cmd_coop`), which is deliberately an explicit step, never a build side effect. The
  **asset half** DOES fold into the block build (`_summon.emit`, like `[[mint]]`); the **engine-arm half**
  is `summon-deploy`. `summon-deploy` can also run standalone (a summon not tied to a field.toml).
- **`summon-export` / `summon-rig-ref`** — ALREADY SHIP (`cli.py:5637`/`5661`, `_cmd_summon_export` @
  `1611`, `_cmd_summon_rig_ref` @ `1636`). Reused unchanged; the forward exporter for the round-trip.

### 5.5 Docs targets

- **`ff9mapkit/docs/SUMMONS.md`** (NEW) — the feature doc, `docs/SAVEPOINT.md`-style: the `[[summon]]`
  block reference, the hybrid-vs-overlay lane table, the engine-independence split, the `vfx1` cast-trigger
  pairing, the relaunch/recast law.
- **`ff9mapkit/docs/tutorials/11-summon-transplant.md`** (NEW — the gap between `10-custom-model.md` and
  `12-creature-from-scratch.md`) — the Blender round-trip: `summon-rig-ref` → skin your mesh in Blender →
  `summon-import` → `summon-deploy` (arm) → cast. Include the humanoid-on-dragon-rig **design-risk flag**
  (TRANSPLANT.md §2.2 / risk P5): a mesh whose silhouette doesn't suit a 93-node long-necked flyer may
  pose correctly and still look wrong — surface it before the user invests in skinning.
- **`ff9mapkit/docs/FEATURES.md`** — new capability rows near the model rows (`FEATURES.md:123-127`),
  linking to `SUMMONS.md`; cross-reference from `CUSTOM_MODELS.md`.

### 5.6 Test files (with the fresh-worktree skip trap in mind)

- `ff9mapkit/tests/test_summon_block.py` — **pure-logic, always-run**: `content/summon.py:validate`
  (every §1 refusal — bad lane, private_ef == donor, private_ef not absent, missing model), the
  `derive_mint_name`/`type_int_of_name` defaults, the `donor` name↔id resolution.
- `ff9mapkit/tests/test_summon_deploy.py` — the §4 byte-identity acceptance + `splice_host_seq` +
  `arm_sfxhybrid` diff + the `probe_hybrid_engine` gate. **Skips cleanly when the donor `.seq` /
  `thomas_skinned.fbx` / the live M1b deployment are absent** (SCRATCH/install-dependent — the fresh
  worktree has neither, so these tests skip, exactly the ~451-test trap the brief warns about; the runner
  must report real pass/skip counts, not assume green).
- `ff9mapkit/tests/test_summon_import.py` — `stage_import` validation (bone hierarchy, texture-name, the
  clip bone-number→path map) on a small synthetic `.glb` fixture (pure-logic where possible).

---

## 6. PROVENANCE (STRICT, TRANSPLANT.md §5)

- `summons/deploy.py`, `content/summon.py`, the CLI verbs, the docs = **committable CODE** (parsers/
  adapters/writers; read caller-supplied local blobs, embed zero game bytes).
- `summon-export` / `summon-rig-ref` output = **LOCAL-ONLY**, already guarded (`summons/export.py:
  assert_local_only:70`, default `C:/gd/SCRATCH/summon-transplant/`, no `--force`). Reused verbatim.
- The user's retargeted model + the deployed `.anim`/`.seq` in the user's OWN mod folder = **theirs**
  (verbatim-fork precedent) — `summon-import`/`summon-deploy` may write there.
- The donor `.seq` copy is Square-Enix-derived: fetched fresh from the user's install at deploy,
  drift-guarded, never committed; a **staged/dry-run** copy lives under SCRATCH (`build_thomas.py:659`).
- The s58 hybrid engine stays on `memoria-patches/` (owner go/no-go); the deploy contract calls **no**
  plugin export and ships **no** patched DLL.
- **This round: staging + dry-run + read-only compares only. Do NOT mutate the live game install. Do NOT
  git commit. Do NOT bump versions.**

---

## 7. THE ONE-SCREEN SUMMARY (for the builder)

1. `[[summon]]` (field.toml) — declarative: `donor` (id|name), `model` (user FBX), `lane` (hybrid default
   | overlay), `id`/`name` (mint band 6000, `mint.py`), `private_ef` (stock-absent set, default 84),
   the `[SfxHybrid]` knobs, optional `hide_meshes`. Emits **assets + an ARM manifest**, no `.eb`.
2. Deploy — hybrid: `6201.fbx`+`Thomas_d.png` + `3DModel` line + `ef084/PlayerSequence.seq`
   (donor-copy + HideMeshes) + `[SfxHybrid]`; overlay adds `FileList.txt`+`.sfxmodel`+`.anim`.
   Relaunch: DictionaryPatch + `[SfxHybrid]`. Recast: `.seq`+FBX. Arm the ini coop-style (backup + diff)
   and **string-probe `SfxHybridDrive`** — hybrid REQUIRES the custom engine, overlay works on stock.
3. `summon-import` — reverse of the export guard: validate bone000..092 hierarchy (smooth weights OK for
   a user mesh), emit the FBX (hybrid) or FBX+clips (overlay, via `models/anim.py:clip_to_anim_json`).
4. Acceptance — the hybrid lane regenerates 5 artifacts byte-for-byte vs the live M1b (§4), overlay
   residue excluded by design.
5. Modules — `summons/deploy.py` + `content/summon.py` (registered in `build.py` like every block) +
   `summon-import`/`summon-deploy` verbs; `summon-export`/`summon-rig-ref` reused; docs
   `SUMMONS.md`+`tutorials/11`+`FEATURES.md`. Native fork family stays OUT.
