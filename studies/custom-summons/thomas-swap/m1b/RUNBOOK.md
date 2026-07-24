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
