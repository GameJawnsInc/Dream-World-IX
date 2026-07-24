> **RENUMBERED s54 -> s58 (2026-07-24 master merge):** this feature was authored, built, and
> proven as "s54"; a concurrent netsync reliability round had already claimed s54-s57 on
> master, so the patch file is "s58-sfx-hybrid-drive.patch". Every "s54" below and in the
> m0/m1b study docs refers to THIS feature; the ini section/keys ([SfxHybrid]) are unchanged.

# M1b RUNBOOK — the Thomas skin, live on the dragon rig, via s54

**Status: ARMED, cast not yet executed.** Everything below the line is verified in place (DLL sha,
staged files, `Memoria.ini`, `DictionaryPatch.txt`). The cast itself needs a human at the keyboard —
this session did not relaunch the game or touch the controller.

---

## 0. What's armed right now (verified this session)

| Item | State |
|---|---|
| Deployed engine DLL (`x64/FF9_Data/Managed/Assembly-CSharp.dll`) | sha256 `2a9c8b14…6bb23ce`, **byte-identical** to `x86` copy and to `C:/gd/FFIX/Memoria/Output/Assembly-CSharp.dll` (the s54 build lane's own output). Contains `SfxHybridDrive` (UTF-8 type name in `#Strings`) and the literal `./sfxhybriddrive.log` (UTF-16LE in `#US`) — confirms s54 is compiled in, not just s53. |
| Pre-s54 baseline backup | `C:/gd/Dream-World-IX/backups/Assembly-CSharp.x64.dll.pre-s54.20260724-091433` (+ `.x86.` sibling) — sha256 `d3db21b4…8d19954`, confirmed **different** from the deployed build. This is the revert target. |
| Model files | `FF9CustomMap/StreamingAssets/Assets/Resources/Models/3/6201/{6201.fbx, Thomas_d.png}` — copied from `m1b_stage/`, sha256-verified byte-identical to the staged originals. |
| `DictionaryPatch.txt` | Appended line 73: `3DModel 6201 GEO_MON_B0_M201`. Lines 1-72 diffed byte-identical against the pre-edit backup. LF line endings preserved (file was LF-only; no CRLF introduced). |
| `Memoria.ini` `[SfxHybrid]` | New section appended after `[SfxProbe]` (see §5 for the verbatim text). CRLF preserved (file was CRLF). First 448 pre-existing lines diffed byte-identical against the pre-edit backup. |
| `[SfxProbe]` | **Untouched** — all 8 capture flags still `1`/armed as before (see §5). |
| ef084 bench (v10.1) | `FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef084/` — no file under it newer than this session's backup timestamp. Untouched. |
| Backups | `C:/gd/Dream-World-IX/backups/DictionaryPatch.txt.20260724-100523`, `C:/gd/Dream-World-IX/backups/Memoria.ini.20260724-100523`. |
| Live `sfxmeshprobe.log` | 30,965,736 B, mtime 08:55 — byte-identical to the already-archived `C:/gd/SCRATCH/summon-transplant/logs/sfxmeshprobe.20260724-085556.log`. **No relaunch has happened since the s54 build (09:18)** — this cast will be the DLL's first run. |

---

## 1. Cast protocol (relaunch REQUIRED)

The new DLL, the new `DictionaryPatch` line (a **new** `3DModel` id only registers at launch), and the
`Memoria.ini` edit all need a fresh process. Hot-reload (~ → Reload field) is NOT sufficient here.

1. **Fully quit FF9** if it's running (check Task Manager — a stale process holds the log file open
   and a relaunch on top of it won't get a clean truncate).
2. Launch FF9 normally (the mod loader reads `FF9CustomMap` from `Memoria.ini [Mod] FolderNames`, already
   stacked from prior work — no change needed there).
3. Open the debug menu (**~** / backquote) → **Go** → **Warp to field** → **30300** (`TEST30300`, the
   bench field).
4. Walk into whatever triggers the encounter (or use the debug menu's battle-warp if the bench wires one)
   to reach the **Iviv** party member's **Spark** command → **Bahamut Cinema** (the minted id-194 summon,
   effect 227 — this is the *only* effect `[SfxHybrid] EffectId=227` will pose).
5. Cast it. Watch the whole sequence through to the damage beat and the return-to-battle.
6. **Immediately after returning to the OS (before any further relaunch)**, archive the fresh logs —
   they truncate (`FileMode.Create`) on the *next* process start, not on a timer:
   ```
   copy "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\sfxmeshprobe.log" ^
        "C:\gd\SCRATCH\summon-transplant\logs\sfxmeshprobe.<TIMESTAMP>-m1b-postcast.log"
   copy "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\sfxhybriddrive.log" ^
        "C:\gd\SCRATCH\summon-transplant\logs\sfxhybriddrive.<TIMESTAMP>-m1b-postcast.log"
   ```
   (`sfxhybriddrive.log` is new this build — first time it will exist at all. It's written relative to
   the game's working directory, i.e. the install root, same as `sfxmeshprobe.log`.)
7. Report back: what was seen (screenshot/video if possible — visual/positional bugs need capture, not
   prose), plus the two archived log paths.

---

## 2. Expected success

Thomas (the skinned mesh, `GEO_MON_B0_M201` / bone groups `bone000..092`) appears **in place of** the
native Bahamut body, posed by the dragon's own live 93-bone animation for the whole cast:

- Visible immediately when the summon's creature would normally appear (no T-pose, no default-bind
  freeze).
- **Flies the fly-by**, **flaps**, **banks** — i.e. tracks the choreographed motion beat-for-beat, not a
  static pose.
- **Scales 0.02 → 3.0** over the cast (the authored climax sweep — CALIBRATION.md §5's node-position-
  spread-carries-scale finding, `ApplyColumnScale=0` so this is riding bare).
- Framed correctly by the native camera the whole time (M1a's already-proven inheritance — no separate
  camera work needed this round).
- The **native dragon body is not visible** at any point (the `HideNative`/`HideMask` write); the
  swirl/beam/fire particle props (bone-parented) still render normally since they aren't part of the
  hidden mesh.
- `sfxhybriddrive.log` shows one `loaded 'GEO_MON_B0_M201' for effect 227 (33 bones)` line near cast
  start (33 = Thomas's vert-carrying bones; the model has 93 total transforms, matching `NodeCount`) and
  no `DISABLED after exception` line.

---

## 3. Failure-mode table

| Symptom | Likely cause | Check |
|---|---|---|
| **Thomas never appears at all** (native Bahamut renders normally, unmodified) | `[SfxHybrid] Enabled` didn't take (stale ini read / relaunch skipped) — OR `EffectId` mismatch (wrong summon cast, or Bahamut Cinema isn't actually effect 227 on this build) | `sfxhybriddrive.log`: if the file doesn't exist at all, `Drive()` never logged anything → Enabled=0 effectively, or the call site never fires. Re-check §5's live ini text. |
| **Thomas never appears; log shows `no [SfxHybrid] ModelPath configured`** | `ModelPath` blank or ini section malformed (e.g. accidental duplicate `[SfxHybrid]` key shadowing) | Re-read live `Memoria.ini`, confirm `ModelPath = GEO_MON_B0_M201` line is inside the `[SfxHybrid]` block, not orphaned above/below it. |
| **`ModelFactory.CreateModel returned null for 'GEO_MON_B0_M201'`** | `3DModel 6201 GEO_MON_B0_M201` line didn't register (needs relaunch — a hot-reload will NOT pick up a new id), or `6201.fbx` missing/corrupt at the deployed path | Confirm relaunch happened AFTER the DictionaryPatch edit. Re-verify `Models/3/6201/6201.fbx` exists + sha256 matches §0's staged copy. |
| **`model 'GEO_MON_B0_M201' has no SkinnedMeshRenderer`** | The exported FBX lost its skin (e.g. a stage step re-exported without bones) | Re-run `m1b/validate.py` against the staged `6201.fbx` before re-deploying. |
| **`SkinnedMeshRenderer has no bones`** | Same class of export defect, empty bones array | Same as above. |
| **Mesh renders but EXPLODED / verts flung far apart / inside-out** | Bind-pose mismatch — the skin was authored against a *different* rest than the native drive assumes (identity rest vs `clip0-f0`), or `ApplyColumnScale` got flipped on and is double-scaling | Confirm `ApplyColumnScale = 0` in the live ini (§5). Compare against `renders/m1b_rest.png` / `m1b_clip0_f0.png` (the offline-eye renders that already proved the rest matches). If it still explodes in-game despite matching offline, suspect a stale/duplicate `.fbx` at the deployed path (re-run the sha256 check in §0). |
| **Mesh frozen at one pose (does not fly/flap/bank)** | The stale-arena guard is holding the last good pose every frame (log: `stale-arena node-0 out of band -- holding last pose`), OR the cast's `active` byte never went nonzero for this creature this run | Grep `sfxhybriddrive.log` for `stale-arena`. If present from frame ~0, the read offset (`SummonActiveOff`/`DataBonesOff`) may be misresolved for this session's DLL layout — compare against `m0/CALIBRATION.md`'s verified offsets on the SAME build. |
| **Native dragon body STILL visible (Thomas renders on top / alongside it)** | `HideNative=0` (typo/wrong value) or `HideMask` too narrow for this donor's real mesh count, or the write landed a frame late (the documented one-frame-flash is expected and is NOT this bug — this is *persistent* double-render) | Re-check live ini: `HideNative = 1`, `HideMask = 0x3`. 0x3 covers Bahamut's known 2 meshes; if the donor turns out to have 3, raise to `0x7`, relaunch, recast. |
| **Bones move but wildly wrong orientation (limbs twisted/backwards)** | The det<0 reflection-guard branch, or the column-to-axis mapping assumption doesn't hold for this donor's authored matrices | Compare log's bone count line against expectation (33 carrying + 60 empty = 93 total is fine — this is NOT a bug); if orientation is wrong on ALL bones uniformly it's a systematic sign error, escalate to `m0/EULER.md` for the derivation to re-check. |
| **Game crashes / DISABLED after exception in log** | Any unhandled exception in `Drive()` — self-disables for the rest of the process (real battle render is NOT supposed to go down with it) | Read the exact exception message the log line includes. The battle itself should still be playable (native Bahamut would NOT reappear once disabled — this is a known accepted gap per the patch's own comments, not this round's bug to fix). |

---

## 4. Full revert ladder

Pick the shallowest step that fixes the observed problem — deeper steps are strictly more disruptive.

1. **Feature off, keep everything else** (fastest — use if Thomas looks wrong but the engine itself is
   fine): in `Memoria.ini`, set
   ```
   [SfxHybrid]
   Enabled = 0
   ```
   Relaunch. The call site (`if (SfxHybridDrive.Enabled) SfxHybridDrive.Drive();`) becomes a no-op —
   zero model creation, zero native writes, native Bahamut renders exactly as stock. Nothing else needs
   touching.

2. **Un-arm the mint but keep the DLL** — remove the `[SfxHybrid]` section entirely and/or delete the
   appended `3DModel 6201 GEO_MON_B0_M201` line from `DictionaryPatch.txt` (restore from
   `C:/gd/Dream-World-IX/backups/DictionaryPatch.txt.20260724-100523` and
   `C:/gd/Dream-World-IX/backups/Memoria.ini.20260724-100523` — both are exact pre-edit snapshots).
   Relaunch. Equivalent to step 1 for gameplay purposes but leaves no trace of the ini/dictionary edits.

3. **Un-deploy the model files** (only needed if disk space or a stale-file suspicion is the concern):
   delete `FF9CustomMap/StreamingAssets/Assets/Resources/Models/3/6201/` entirely. Safe only after step 2
   (don't leave a `DictionaryPatch` line pointing at a folder that no longer exists while the DLL is still
   live and `Enabled=1`).

4. **Engine back to s53** (the deepest step — only if s54 itself is suspected of destabilizing something
   OUTSIDE the hybrid-drive feature, e.g. it broke an unrelated battle path): restore the pre-s54 DLL
   backup pair:
   ```
   py tools/restore_memoria_dll.py pre-s54
   ```
   (selector `pre-s54` uniquely matches `Assembly-CSharp.x64.dll.pre-s54.20260724-091433` +
   `Assembly-CSharp.x86.dll.pre-s54.20260724-091433`, sha256 `d3db21b4…8d19954`, confirmed different from
   the deployed s54 build in §0.) This is a full DLL swap — relaunch required, and it also removes
   `SfxHybridDrive`/`SfxMeshProbe`'s newest additions from the running engine, not just this feature.
   **This does NOT need the `[SfxHybrid]`/`DictionaryPatch` edits reverted first** — an absent class
   makes the ini section inert, but reverting them anyway (step 2) keeps the install self-consistent for
   the next agent who reads `Memoria.ini` and expects it to describe what's actually running.

**Do NOT** `git checkout`/`reset`/`stash`/`clean` inside `C:/gd/FFIX/Memoria` at any point in this ladder —
per the standing rule, the ONLY undo for the s54 patch itself (as opposed to swapping the built DLL) is a
reverse-`git apply` of `memoria-patches/s54-sfx-hybrid-drive.patch` against that clone, and that is a
build-lane action, not part of this deploy runbook.

---

## 5. Live `[SfxHybrid]` + `[SfxProbe]` (verbatim, read back after the edit)

```ini
[SfxProbe]
Enabled = 1
CaptureRoot = 1
CaptureModels = 1
ModelsActiveOnly = 1
ModelsCap = 120000
ModelsBoneCount = 93
CapturePrims = 1
PrimSummary = 0
PrimCap = 3000000

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

`Log=1` is deliberate for this first cast only (per the task brief) — set it back to `0` after a
successful capture to avoid per-launch log spam on subsequent casts.

## M1b CAST VERDICT — 2026-07-24 ★★ THE FAITHFUL TRANSPLANT IS IN-GAME PROVEN

User, after the `--m1b-bench` recast (the overlay Thomas removed, s54 the only renderer):
**"it works. thomas flies with the dragon's motion."** Our skinned mesh wearing a stock Eidolon's
real per-frame skeleton + staging + camera, live in battle — the first faithful source-level summon
transplant anywhere. ("Looks horrifying" = the chosen rigid-train-on-dragon-bones aesthetic; levers
below.)

**The deconfounded depth gate** (this cast ran under the NATIVE mask — PRIM volume halved 549k→264k,
body prims truly absent; archive `sfxmeshprobe.20260724-103926.log`): the mid-cast phases collapsed
to HYBRID-OK (P5→P6 and P7→P8 front/straddle 4-5%→**0%** — that content WAS body skin, the
verifier's confound confirmed), while the entrance swirl (P1→P2 67%/67%) and the ground-reign climax
(P8→P9 38%/28%) keep genuine effect interleave. **Final Bahamut verdict: MIXED on content — but no
mis-layering was reported in the live cast**, so the wholesale-sort residual does not visibly bite
for this donor at this polish bar; the native slot (M3/T2) remains the per-summon escalation if a
future eye says otherwise.

**Aesthetic levers (all cheap):** (a) re-bind Thomas at a FLIGHT pose instead of the neutral rest —
one edit in `m1b/skin_thomas.py` (bind at e.g. clip6's mid-flap) + re-run + redeploy: whole-train
mid-flight, chunks at rest instead; (b) any properly-articulated creature mesh skinned onto the same
`summon-rig-ref` rig replaces Thomas with zero engine work; (c) `HideMask`/texture/material polish
per the s46 render-rig lessons. Resting state: `--m1b-bench` deployed, s54 armed, everything hot
except engine/ini changes.

## FLIGHT-POSE REBIND (A/B)  — built 2026-07-24, DEPLOYED as B

Lever (a) above, built. Two skinned FBX variants now exist; the s54 drive is identical for both —
only the FBX bind pose differs. The drive writes ABSOLUTE bone world matrices and Unity skins
`world_v = boneWorld[k] * inverseBind[k] * v`, so Thomas reads WHOLE at whatever pose he was BOUND at
and deforms everywhere else.

- **A = NEUTRAL bind** (`thomas_skinned.fbx`, sha256 `0c300131…a39e2fe5`): whole at the dragon's neutral
  rest, shatters during flight (most of the cast). The originally-proven variant.
- **B = FLIGHT bind** (`thomas_skinned_flightbind.fbx`, sha256 `d9074a98…f548487a`): whole during
  flight, distorted at neutral instead. **Currently deployed** (over `…/Models/3/6201/6201.fbx`; the
  deployed file's pre-switch sha was byte-identical to A, so the switch-back below is exact).

**Chosen bind frame: clip6 @ f77** (`skin_thomas.py --bind-clip 6 --bind-frame 77`). Rationale, from the
baked clip curves (not vibes): clip6 is the dominant flight clip (longest baked action, glb frames
0..130; its native window f301-381 dominates framed screen time per `m0/EULER.md` §3). Within it the
wing tip (bone039) sweeps monotonically from folded (Z≈-9.2 around f42-54) up to spread (Z≈+0.9); f77
is the exact MIDPOINT of that vertical travel (Z≈-4.3) and near the clip's temporal middle — a
representative *wings-mid-flap* pose, not a folded/spread extreme, so it minimizes average deviation
across the flight window. The fit was re-derived against the POSED skeleton (Thomas's long axis laid
along the posed head→tail body spine, same FIT_SPAN_FRAC scale law; neutral scale 3.42 → flight scale
2.61 because the reared flight pose is more compact along its spine). Offline eye (`renders/flightbind_*.png`)
confirms the inversion: rest ratio 1.00, clip6_f65 0.96 / clip6_f110 1.05 (near-whole in flight) vs
clip0 neutral 1.17 / clip5 1.43 (distorted) — the mirror image of the neutral bind's numbers.

**Switch A ⇄ B** (just overwrite the deployed FBX; texture/DictionaryPatch/ini/engine all unchanged):

```
:: -> B  (FLIGHT bind, whole in flight)   [currently deployed]
copy /Y "C:\gd\SCRATCH\summon-transplant\thomas_skinned_flightbind.fbx" ^
        "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Assets\Resources\Models\3\6201\6201.fbx"

:: -> A  (NEUTRAL bind, whole at rest)    [the original]
copy /Y "C:\gd\SCRATCH\summon-transplant\thomas_skinned.fbx" ^
        "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets\Assets\Resources\Models\3\6201\6201.fbx"
```

Then RECAST Bahamut Cinema (field 30300, id 194). A hot recast usually shows the new bind immediately;
**if a recast still shows the OLD shape, relaunch once** to clear the model cache (Unity may hold the
prior `6201.fbx` import for the session), then recast.

**Expect visually:** with B deployed, Thomas holds together as a (tilted) whole train through the
mid-flight beats of the cast and comes APART at the neutral bookends / entrance — the exact inverse of
A, which is whole when the dragon is at rest and shatters while it flies.
