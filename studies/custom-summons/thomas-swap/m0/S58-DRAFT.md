> **RENUMBERED s54 -> s58 (2026-07-24 master merge):** this feature was authored, built, and
> proven as "s54"; a concurrent netsync reliability round had already claimed s54-s57 on
> master, so the patch file is "s58-sfx-hybrid-drive.patch". Every "s54" below and in the
> m0/m1b study docs refers to THIS feature; the ini section/keys ([SfxHybrid]) are unchanged.

# S54-DRAFT.md — the HYBRID DRIVE engine feature (★ BUILT + DEPLOYED 2026-07-24)

> **Status: BUILT + DEPLOYED 2026-07-24 (owner GO given: "build s54, skin thomas onto the dragon rig").**
> The patch `memoria-patches/s54-sfx-hybrid-drive.patch` was applied to the clone (`git apply --binary`, the
> 3 expected paths), compile-checked with `DWIXNoDeploy=true` (0 errors, 186 pre-existing warnings), then
> built + auto-deployed to BOTH arches. `Output\Assembly-CSharp.dll` == both deployed `x64`/`x86` copies,
> sha256 `2A9C8B148824FF82C0350C492FDE150C54A744C2D822EBE23A080C05B6BB23CE` (all three identical). Pre-build
> full DLL backup `20260724-091433` (`py tools/restore_memoria_dll.py 20260724-091433` reverts the whole
> engine); the s54-only undo is `git -C C:/gd/FFIX/Memoria apply --reverse --binary
> memoria-patches/s54-sfx-hybrid-drive.patch`. Symbols verified present in both deployed arches
> (`SfxHybridDrive`/`EndCast` + the `[SfxHybrid]` ini literals); the s53/s52/s47 probe symbols still present
> (the stack composes). The README row is now live in `memoria-patches/README.md` (Dev-tooling table).
> **The engine ships INERT — `Memoria.ini [SfxHybrid] Enabled=0` (untouched here; the arming agent owns it).
> NOT yet cast in-game; the M1b playtest (§4/§5 go/no-go + risk list) is the remaining step.** This file
> stays the spec + the build record + the go/no-go gates + the honest risk list.

Milestone: **1b of `disasm/TRANSPLANT.md` §2.4** ("THE FAITHFUL MVP: our model + the dragon's real MOTION").
Grounded entirely in the M0-verified numbers (`m0/CALIBRATION.md`, `m0/CAMERA-MATCH.md`, `m0/FBX-PATHS.md`)
and the s52/s53 probe read-paths.

---

## 1. What the patch touches (validated `--stat`)

```
 Assembly-CSharp/Assembly-CSharp.csproj             |   1     (Compile Include, alphabetical: between SFXDataMeshConverter.cs and SfxMeshProbe.cs)
 Assembly-CSharp/Memoria/Battle/SFX/SFXDataMesh.cs  |  12 +   (two hooks: Runtime.Render() drive + Runtime.End() teardown)
 Memoria/Battle/SFX/SfxHybridDrive.cs (NEW)         | 440 +   (the feature class)
 3 files changed, 453 insertions(+)
```

Bare unified-diff style (`--- a/` / `+++ b/`, no `diff --git`/`index`), **LF** throughout — matching s52/s53.
The clone files are CRLF; git apply tolerates the LF-patch-vs-CRLF-file class (verified `--check` clean **with
and without** `--binary`; the s47 README row calls this "the accepted EOL-only class"). Targets the CURRENT
clone (`C:/gd/FFIX/Memoria`, s22..s53 applied as the working tree).

**Validation performed (dry-run only, clone left clean):**
```
$ git -C C:/gd/FFIX/Memoria apply --check           s54-sfx-hybrid-drive.patch   -> exit 0
$ git -C C:/gd/FFIX/Memoria apply --check --binary   s54-sfx-hybrid-drive.patch   -> exit 0
$ git -C C:/gd/FFIX/Memoria apply --stat             s54-sfx-hybrid-drive.patch   -> 3 files, 453 insertions
  git status unchanged (61 modified before == 61 after); SfxHybridDrive.cs NOT created in the clone.
```

---

## 2. The feature (`Memoria/Battle/SFX/SfxHybridDrive.cs`)

A static, ini-gated, lazy-init, hard-isolated feature class mirroring `SfxMeshProbe`'s shape.

### 2.1 Ini surface — `[SfxHybrid]` (all read once, cached; relaunch to change)

| key | default | meaning |
|---|---|---|
| `Enabled` | `0` | master gate; OFF ⇒ the call site never calls `Drive()`, nothing created/read/written |
| `EffectId` | `227` | the donor effect id to drive (Bahamut). Only this cast poses the puppet |
| `ModelPath` | *(empty)* | FileList-style `GEO_*` name or `Data/`-rooted `.fbx`, loaded via `ModelFactory.CreateModel`. **MUST be a private slot, never the donor's own `ef{id}/` folder** (the donor-FileList replacement law, `m0/FBX-PATHS.md`) |
| `HideNative` | `1` | assert the native body-hide mask each active frame (the single plugin-state write) |
| `HideMask` | `0x3` | hex mask written to `SummonData+0x20`(x64)/`+0x14`(x86); `0x3` = Bahamut's 2 meshes; `0x7` for a 3-mesh donor; `0xFFFFFFFF` a safe universal total-hide (bits ≥ meshCount inert) |
| `NodeCount` | `93` | donor bone count (ef227 = 93); we drive `min(model.bones.Length, NodeCount)` by node index — never past the native array |
| `ApplyColumnScale` | `0` | **escape hatch, OFF** — see §2.4 (the task-brief localScale reconciliation) |
| `Log` | `0` | lifecycle/fault log to `./sfxhybriddrive.log` (fresh per launch); never per-bone spam |

### 2.2 The two hooks (both in `SFXDataMesh.cs`)

- **`Runtime.Render()`, right after `SfxMeshProbe.LogModels()` (line 659 area), OUTSIDE the `[SfxProbe]`
  block** → `if (SfxHybridDrive.Enabled) SfxHybridDrive.Drive();`. By that point this frame's native Draw has
  run, `*(SummonData+0x38)` holds this frame's world matrices, and `camera` (`:635`) is the resolved
  `SFX_PLUGIN` camera. Independent of the probe.
- **`Runtime.End()`, after `FlushPrimSummary()`** → `SfxHybridDrive.EndCast();`. The lifecycle complement:
  `Drive`'s own `active==0` release can't fire when no SFX renders after a cast (`Render()` stops), so the
  posed creature would otherwise linger frozen. **(This second hook is BEYOND the task brief's single-hook
  sketch; it is the correct lifecycle and is why a cast can't leave a stuck puppet.)**

### 2.3 The per-frame drive loop (PROVEN read path; mirrors `SfxMeshProbe.cs` s52/s53 exactly)

```
base   = GetModuleHandle("FF9SpecialEffectPlugin.dll")     ; cached
if (currentEffectID != EffectId) { release; return }        ; only our donor cast
rec    = base + (x64 0x220830 | x86 0x20869c)               ; summon record, LENGTH 1
active = ReadByte(rec + (x64 0x50 | x86 0x4c))              ; 0 => release + return
sData  = ReadIntPtr(rec)                                     ; -> SummonData ; 0 => return
bones  = ReadIntPtr(sData + (x64 0x38 | x86 0x20))          ; 0 => not drawn yet => return
EnsureModel()                                               ; lazy load once/cast (see §2.5)
if (HideNative) WriteInt32(sData + (x64 0x20 | x86 0x14), HideMask)   ; THE ONE PLUGIN-STATE WRITE
for k in 0..min(bones.Length, NodeCount)-1:                 ; PSX MATRIX stride 0x20
    M = 3x3 s16 @+0x00 (/4096) , s32 t @+0x14
    bones[k].position = (t.x, -t.y, t.z)                    ; scale EXACTLY 1  (CALIBRATION.md 1-2)
    bones[k].rotation = quat(B*R*B), B=diag(1,-1,1), det<0 guard   (CALIBRATION.md 2/7)
```

Every native read is defended (`IntPtr.Zero` checks, whole body in try/catch). **On the first exception the
feature self-disables for the process, logs once, and releases anything half-built** — a go/no-go render
feature must never take the real battle render down with it. No P/Invoke into the plugin by name; passive
`Marshal` reads + the one `+0x20` write only.

**Matrix→quaternion:** `Quaternion.LookRotation(forward, up)` (forward = column 2, up = column 1). This is
the Unity-5.2 replication of `Matrix4x4.rotation` — **that property does not exist until Unity 2017.1** (grep:
the codebase never uses it and uses `Quaternion.LookRotation` throughout). The **det<0 guard flips column 2
(the local Z / forward)** to make an intrinsically improper PSX frame proper before extraction; `LookRotation`
rebuilds `right` from `(up, forward)`, so the flip only reorients, never mis-scales.

### 2.4 The localScale reconciliation (a deliberate, documented deviation)

`TRANSPLANT.md §2.1` (pre-M0) asked to also set `bones[k].localScale` to the per-column matrix norms.
**`m0/CALIBRATION.md §5` (M0-VERIFIED) proves the node POSITION spread already carries the authored 0.02→3.0×
scale sweep, so writing `localScale` DOUBLES the creature.** Therefore the drive loop does **not** write
`localScale` by default. The capability is preserved as `ApplyColumnScale=0` (an off-by-default escape hatch)
purely so the owner can A/B it at M1b if a donor's `summon-rig-ref` bind pose is not a clean scale-1 rest.
This is the one place the code intentionally diverges from the brief's literal wording, on the strength of the
verified calibration the brief itself corrects.

### 2.5 Model lifecycle

Loaded once per cast the first frame the drive sees its `EffectId` active, via
`ModelFactory.CreateModel(ModelPath, false, true, Configuration.Graphics.SFXSmoothTexture)` — the same loader,
same texture-filter, as the SFX system's own FBX models (`SFXDataMesh.Begin → :769`). The model's `Animation`
component is disabled (our loop owns the pose). `SkinnedMeshRenderer.updateWhenOffscreen = true` (the bones fly
thousands of units from the renderer origin; a stale AABB would frustum-cull the creature — the s46 render-rig
culling law). If the model has `!= NodeCount` bones it logs once and drives `min(n, NodeCount)` (never throws).
Released (`Object.Destroy`) when the cast goes inactive (`Drive`) or ends (`EndCast`).

---

## 3. Build checklist (run ONLY on owner GO)

Prereqs: FF9 **closed** (`AfterBuild` auto-deploys, overwriting the live DLL — DANGEROUS, no backup of its own).

1. **Take a full DLL backup first** (the s52/s53 record's pattern):
   `py tools/restore_memoria_dll.py` writes timestamped backups; note the pre-build timestamp
   (e.g. `20260722-234755`) so `py tools/restore_memoria_dll.py <timestamp>` reverts the whole engine. (True
   stock = `py tools/restore_memoria_dll.py baseline` or re-run the patcher; CLAUDE.md §5.)
2. **Apply the patch onto the live clone** (the stack applies with `patch -p1 -F0 -s -f --binary`, or here
   directly): `git -C C:/gd/FFIX/Memoria apply --binary memoria-patches/s54-sfx-hybrid-drive.patch`.
   Re-verify `git status` shows exactly the 3 expected files changed + `SfxHybridDrive.cs` new.
3. **Compile-check WITHOUT deploying** (recommended first pass): add `/p:DWIXNoDeploy=true` (the `AfterBuild`
   `DWIXNoDeploy` condition, s45):
   `msbuild Assembly-CSharp.csproj /t:Build /p:Configuration=Release /p:SolutionDir=C:\gd\FFIX\Memoria\ /m /p:DWIXNoDeploy=true`
   (the trailing-backslash `SolutionDir` is required). Expect 0 errors (baseline ~186 pre-existing warnings).
4. **Build + auto-deploy both arches** (drop `DWIXNoDeploy`): same msbuild line. `AfterBuild` deploys x64 + x86;
   confirm `Output\Assembly-CSharp.dll` == both deployed copies (sha256) and the `SfxHybridDrive`/`Drive`/
   `EndCast`/`SfxHybrid`/`GetModuleHandle` literals are present in the deployed metadata (the s52/s53 gate).
5. **Arm in `Memoria.ini`:** `[SfxHybrid] Enabled=1`, `EffectId=227`, `ModelPath=<private GEO/fbx>`,
   `HideNative=1` (+`Log=1` for the first cast). Cast on the bench (field 30300, id 194). Expect: our mesh
   flaps/banks/shrinks/flies with the dragon's motion, native body hidden.
6. **Revert cleanly if NO-GO:** `git -C C:/gd/FFIX/Memoria apply --reverse --binary
   memoria-patches/s54-sfx-hybrid-drive.patch`, and restore the DLL from the step-1 backup.

---

## 4. Go / No-go decision points (for the owner)

1. **Cross the passive→active line?** This is the first SFX feature that renders content AND writes plugin
   memory (`+0x20`). Everything s47–s53 was read-only. Approving the build is approving that step.
2. **`HideNative` write vs the managed `HideMeshes` split.** The safer first cut (Milestone 1a) hides the body
   with the managed `HideMeshes=` SFXKey split — **zero native write**. If the owner wants zero plugin writes
   in the shipped feature, ship M1a's hide and set `HideNative=0` here (our mesh then renders over the visible
   native body — only acceptable if the body is otherwise hidden). The native write is kept because it is the
   proven total-hide (D4) and the cleaner result.
3. **Per-donor `NodeCount`/`HideMask`.** Both are supplied (not runtime-readable). Bahamut's 93/0x3 are the
   defaults; a different donor needs its own values from `summon-inspect` before its first cast.
4. **`ApplyColumnScale` stays OFF** unless a bind-pose A/B at M1b shows a donor needs it (§2.4).

---

## 5. Honest open risks

- **The render-pass race (TRANSPLANT risk #4).** We write bone Transforms during `SFXDataMesh.Runtime.Render()`
  (after the native Draw). Unity consumes the SMR bones when it renders the camera. If the SMR renders on a
  DIFFERENT tick than our write (a ≤1-native-substep VIEW/M sampling residual is already noted in
  `m0/CALIBRATION.md §3`/`CAMERA-MATCH.md`), the puppet could lag the native effects by up to one frame. Not
  observable offline — **watch it on the M1b cast.**
- **The det<0 flip choice is not screen-observable offline.** ~7.5% of frames (the ~3.0× climax hold,
  f153–177) are intrinsically improper; the code flips column 2 (the reference choice, `CALIBRATION.md §2/§7`).
  Which correction *looks* right must be **confirmed visually at M1b.**
- **Frame-0 body flash.** The hide mask is written after this frame's Draw, so it hides from the next draw on —
  a single possible frame of the native body. Accepted (M1a's managed split is the flash-free alternative).
- **Node-index hierarchy order.** The absolute-world writes assume node index is root-first (parent index <
  child index); true for FF9 skeletons and the `summon-rig-ref` exporter. A donor violating it could lag a leaf
  one frame — confirm at M1b.
- **Stale recycled-arena nodes on the cast tail (`VERIFY_CALIBRATION.md` C6).** A single ef227 cast holds the
  summon slot's `active` flag set for its WHOLE span (`frameIndex ~11–561`), but once the creature is
  choreographically gone the composed `*(SummonData+0x38)` nodes are recycled-arena garbage — f512's node-0
  world point is `(-5.2e8, 6.4e7, 2.0e9)` while `active != 0`. `Drive()`'s `active/sData/bones` gates all pass,
  so posing straight from that would fling our mesh ~2e9 units offscreen (the native creature is unaffected —
  its hidden polys are skipped — but our Unity mesh is not gated by the native draw). **Guarded**: `Drive()`
  now skips any frame whose ROOT node-0 translation leaves the sane band (`|t| > SaneMaxTrans = 1<<24`;
  legitimate node translations are ≤ ~16k units — the 3.0× climax `BONES`-AABB diagonal ~15543u, the clean
  ROOT anchor ~12k — vs the ≥5.2e8 garbage), holding the last good pose rather than flinging (once-logged per
  cast). **M1b:** measure the visual extent of the held-pose tail — a hide-on-stale (release the puppet the
  moment node-0 goes garbage) may read better than a frozen last pose; also consider cross-checking against the
  clean ROOT `+0x40` anchor (C6's robust datum) instead of a fixed band if a donor's authored spread ever
  approaches the bound.
- **The widescreen horizontal residual** (`CALIBRATION.md §4`) is a property of Memoria's camera reconstruction,
  not this map: our mesh renders through the same `Camera.main` as all Unity content, so it lands
  widescreen-correct; it only diverges from the KEPT native effect prims off-center. Decidable per-summon.

---

## 6. Relationship to the prior scratch attempt (for the record)

A concurrent/earlier session left a draft in the scratchpad (`.../scratchpad/s54build/`). This deliverable is a
fresh, independently-authored version. Two substantive corrections vs. that draft: it used
`Matrix4x4.rotation` (**does not compile on Unity 5.2.3** — added 2017.1), and it applied `localScale`
unconditionally (**doubles the creature per `CALIBRATION.md §5`**). This version uses `Quaternion.LookRotation`
and defaults `ApplyColumnScale=0`. It KEEPS that draft's one good idea the task brief omitted: the
`Runtime.End()` teardown hook.

---

## 7. DRAFT README row (moves into `memoria-patches/README.md` on owner GO — do NOT add it there yet)

Place under **"Dev tooling / custom-summon arc"** (with the s52/s53 rows), reworded once built:

> `s54-sfx-hybrid-drive.patch` | **THE SFX HYBRID DRIVE (DRAFT — owner go/no-go; NOT built, NOT deployed as of
> 2026-07-24).** The first SFX feature past the passive s47–s53 probes: it **renders content** (a custom
> `SkinnedMeshRenderer` posed to the native summon's live skeleton) and performs **one runtime write** into
> plugin state (the body-hide mask). New `Memoria/Battle/SFX/SfxHybridDrive.cs` (+ csproj include) + two hooks
> in `SFXDataMesh.cs` (`Runtime.Render()` after `SfxMeshProbe.LogModels()` → `Drive()`; `Runtime.End()` after
> `FlushPrimSummary()` → `EndCast()` teardown). Per frame, while `[SfxHybrid] Enabled=1` and the configured
> `EffectId` (default 227/Bahamut) is casting, it reads the plugin's freshly-composed per-node world matrices
> (`*(SummonData+0x38)`, the s52/s53 read path, arch-split by `IntPtr.Size`), converts each to Unity world via
> the M0-verified calibration (`(tx,-ty,tz)` scale 1; rotation `B·R·B`, `B=diag(1,-1,1)`, det<0 guard —
> `m0/CALIBRATION.md`), and writes it onto our model's bone `k` — so our mesh rides the dragon's real motion
> through the same `Camera.main`. `HideNative=1` asserts the total-hide mask (`SummonData+0x20`/`+0x14`,
> default `0x3` = Bahamut's 2 meshes; D4). Default OFF (a normal install creates nothing, reads/writes no
> plugin memory, pays one cached-bool check). Hard try/catch isolation — self-disables on the first fault.
> Provenance-clean: engine code only; the user's creature loads by path from their own mod folder (never a
> FileList in the donor's `ef###/`, `m0/FBX-PATHS.md`). Milestone 1b of `disasm/TRANSPLANT.md`. Gate:
> `git apply --check`/`--check --binary` clean on the s53-tip clone; **NOT compiled/deployed** — owner GO
> pending (`m0/S54-DRAFT.md`).
