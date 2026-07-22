# THE SFX MESH PROBE (s47) — arming + read-out

Engine patch `memoria-patches/s47-sfx-mesh-probe.patch` (built 2026-07-22, `Memoria/Battle/SFX/SfxMeshProbe.cs`
+ two call sites) adds a default-OFF, permanent debug-class instrumentation feature: while armed, it logs a
CSV-ish line for every native SFX mesh drawn each frame, plus one camera line per frame while the native
camera track is driving. It exists for exactly two things this build needs and doesn't have yet:

1. **The `HideMeshes` hex-key split** between Bahamut's own creature/body meshes and his kept
   swirl/beam/fire-column effect meshes (`BattleActionCode.cs:394-419 TryGetArgMeshList` — accepts a
   `0xHEX,0xHEX,...` key list, not just index ranges). README.md's "HideMeshes bisection protocol" is
   currently a guess-and-recast index-range bisection; this probe replaces the guess with the donor's real
   mesh keys.
2. **Bahamut's actual baked per-frame position** (read off his own mesh's world-space bounds), to calibrate
   `build_thomas.py`'s hand-guessed flight constants (`CAVE_STAGE_*`/`SKY_*`/`GROUND_DRIFT_*`/`EXIT_*`)
   against the real arena/camera instead of eyeballing a video.

One instrumented cast gives both — no `ef###.bytes` decoding, no DLL disassembly, no video required (though a
video alongside the log still helps correlate a `frame` number with what's on screen).

## 1. Arm it

The probe is gated on `Memoria.ini [SfxProbe] Enabled=1` (default `0` — fail-safe, zero cost; see "Zero-cost
when off" below). It is read once per process via `IniFile.MemoriaIni` (a lazily-cached singleton), so:

1. **Close FF9 if it's running.**
2. Open `<game>\Memoria.ini` (on this machine:
   `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\Memoria.ini`) and add a new section
   anywhere in the file:
   ```ini
   [SfxProbe]
   Enabled=1
   ```
3. **Launch the game fresh.** This is an ini-gated engine toggle, not field/mod content — the same rule
   every other `Memoria.ini` engine flag already follows: a `~`-menu "Reload field" does **not** re-read it,
   only a real relaunch does.

## 2. Run the one calibration cast

1. `py studies/custom-summons/thomas-swap/build_thomas.py --calibrate` — deploys `ef084`'s `PlaySFX` line
   with **no `HideMeshes` argument at all**, so Bahamut's real mesh renders fully unsuppressed (byte-identical
   to the stock donor's own line). The probe logs the *entire* `SFXRender.commandBuffer` regardless of
   `HideMeshes` — it hooks before the prevented-mesh check — but `--calibrate` is still the right first pass:
   with nothing hidden, everything the log names is also visible on screen at the same moment, so you can
   correlate a `keyHex`/bounds row with "that's the wing" or "that's the fire column" by eye.
   - If this is the very first `build_thomas.py` run this session, it also needs the one-time GEO-mint
     relaunch (`3DModel 6200 GEO_MON_B0_M200`) — same relaunch you already did in step 1 above covers both if
     you run `--calibrate` before launching.
2. Load the bench save (or New Game → `~` → Warp to field → `30300`), get into the field's battle (scene 67),
   and cast **Iviv → Spark → Bahamut Cinema**.
3. Let the **whole** cast play through — chant, camera cut, charge, Mega-Flare, fire column, exit (~40s) — so
   every phase's meshes and camera positions get logged, not just the opening frames.
4. You can read the log while the game is still running (every line is flushed on write) or close the game
   first; either way the file on disk is complete once the cast has played.

## 3. Where the log lands

`<game>\sfxmeshprobe.log` — the same folder as `Memoria.ini` (the log path is the relative `./sfxmeshprobe.log`,
resolved from the same working directory `IniFile`'s own `./Memoria.ini` already resolves from). On this
machine: `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\sfxmeshprobe.log`.

It is **recreated** (`FileMode.Create`) the first time anything is logged in a process, so each fresh game
launch starts a clean file — it does not append across relaunches or grow without bound.

## 4. Format

```
# ff9mapkit s47 sfx-mesh-probe
# MESH,effectId,frame,index,keyHex,vertCount,triCount,cx,cy,cz,ex,ey,ez
# CAM,frame,px,py,pz,rx,ry,rz
MESH,227,14,0,00D78000,168,84,12.3400,45.6700,-8.9000,20.1000,35.4000,20.1000
CAM,14,123.4500,80.0000,-260.2000,15.0000,270.0000,0.0000
...
```

(The 3 `#`-prefixed lines are a header, written once at the top of the file — everything after is data.)

| Column | Meaning |
|---|---|
| `effectId` | `(Int32)SFX.currentEffectID` — the `Memoria.Data.SpecialEffect` enum, cast to its underlying int. Watch the first few MESH lines right after the cast starts to learn which numeric id `Bahamut__Full` resolves to on this build (it's a stable enum value, not something that changes cast to cast). |
| `frame` | `SFX.frameIndex` — the native plugin's own frame counter. **The same counter drives both MESH and CAM lines**, so join on `frame` to line up "what was drawn" with "where the camera was" at a given tick. |
| `index` | The mesh's position in that frame's `SFXRender.commandBuffer`. Not guaranteed stable across the whole cast (meshes come and go as phases change) but usually stable within one continuously-playing phase. |
| `keyHex` | `SFXMeshBase._key`, 8 hex digits — **the exact value `HideMeshes=0x...`/`-Colors` take** on a `PlaySFX` line (`BattleActionCode.cs:394-419`). This is the #1 harvest target. |
| `vertCount` / `triCount` | Straight off the drawn Unity `Mesh` (`mesh.vertexCount`, `mesh.triangles.Length/3`). |
| `cx,cy,cz` / `ex,ey,ez` | `mesh.bounds` center / extents, **world space** — `SFXMesh.Render()` draws via `Graphics.DrawMeshNow(_mesh, Matrix4x4.identity)` (no transform in play), so object space IS world space for this mesh class. |
| `px,py,pz` / `rx,ry,rz` (CAM only) | `Camera.main.transform.position` / `.eulerAngles`, logged once per frame **only while** `SFXDataCamera.currentCameraEngine == CameraEngine.SFX_PLUGIN` (i.e. for as long as the native plugin camera track is actually driving `Camera.main` — CAM lines stop once the effect hands control back). |

## 5. Reading it for the two things this build needs

### (a) The `HideMeshes` hex-key split

- Every distinct `keyHex` in the log is one `SFXMesh` the native `Bahamut__Full` effect draws at some point
  during the cast.
- Group rows by `keyHex`, look at each key's `vertCount`/`triCount`/bounds trajectory over `frame`, and
  cross-reference against what's visibly on screen at those frames (a video captured alongside the
  `--calibrate` cast makes this trivial — nothing is hidden, so every key's mesh is actually visible).
  Body meshes (scales/wings/head/legs) should track roughly rigid and move together; swirl/beam/fire-column
  effect meshes tend to have very different vertex counts, appear/disappear on their own phase windows, and
  move independently of the body's silhouette.
- Once sorted, feed the CREATURE keys — not the effect keys — as
  `HideMeshes=0x<key1>,0x<key2>,...` on `ef084/PlayerSequence.seq`'s `PlaySFX: SFX=Bahamut__Full` line.
  `build_thomas.py`'s `patched_line(hide_range)` currently only emits an index-range form
  (`HideMeshes=0,31`); extending it to also accept/emit an explicit hex-key list turns the current
  index-range **bisection guess** (README.md's "HideMeshes bisection protocol") into an exact, byte-grounded
  split — a key's `_key` is stable for as long as that mesh instance is alive, so the key form does not have
  the index-range form's "meshes shift position in the buffer between phases" fragility.

### (b) Bahamut's baked flight path

- This patch does not log a separate "creature position" — there's no such thing engine-side distinct from
  the mesh itself. Once you've identified which `keyHex`(es) are his BODY (see above), that key's own
  `cx,cy,cz` **is** his position for every frame it's drawn (the baked animation is literally reflected in
  where the native plugin re-emits that mesh's vertices each tick). Pull just those rows, sorted by `frame`,
  to get his real flight curve through the whole cast — cave entrance → sky charge → ground/fire-column →
  exit.
- Join with the CAM rows on `frame` to also know where the camera was looking at each of those positions —
  this is what turns `build_thomas.py`'s currently hand-guessed `CAVE_STAGE_*`/`SKY_Y_OFFSET`/`SKY_STAGE_*`/
  `SKY_DRIFT_*`/`GROUND_DRIFT_*`/`EXIT_*` constants (calibrated by eye against a video, per the README's
  failure-mode table) into numbers measured directly against the real donor's own path and the real arena's
  actual camera framing.

## 6. Zero-cost when off

Both hook sites (`SFXDataMesh.cs` `Runtime.Render()`, `SFXDataCamera.cs` `UpdateCamera()`) guard on
`SfxMeshProbe.Enabled` — a single cached `Boolean` field read once from `Memoria.ini` at first touch — before
calling anything else. With the shipped default (`Enabled=0`, or no `[SfxProbe]` section at all): one bool
read per call site, nothing allocated, no file ever opened. Safe to leave this patch in the engine
permanently; it costs nothing on a normal install.

## 7. Turning it back off / reverting

- **Just the probe:** set `[SfxProbe] Enabled=0` (or delete the section) in `Memoria.ini` and relaunch — no
  DLL change needed, the patch itself always ships in the engine.
- **Just this build (back to pre-s47):** copy the pre-build backups taken before either s47 compile —
  `backups/Assembly-CSharp.x64.dll.20260722-095733` → `x64\FF9_Data\Managed\Assembly-CSharp.dll`, and the
  `.x86.` sibling → `x86\FF9_Data\Managed\Assembly-CSharp.dll`. **Close FF9 first** — copying over a running
  game hits `WinError 1224` (the DLL is memory-mapped).
- **`py tools/restore_memoria_dll.py 20260722-095733` — the tool was FIXED 2026-07-22** (the same-day
  review found `baseline` mode restoring NOTHING yet printing `Done.`): it now matches every backup naming
  convention including the per-arch `Assembly-CSharp.x64.dll.<ts>` names above (arch-specific backups land
  only in their own Managed folder), and it exits non-zero with a loud `NOTHING RESTORED` message when no
  backup matches — so the pre-s47 revert is now the one-liner with the timestamp selector. `baseline` still
  finds nothing (the documented `*.baseline-rebuild-6b8bb2d5.*` set is gone from `backups/`) but now FAILS
  LOUDLY instead of pretending. Run it from the MAIN repo — a worktree has no `backups/` of its own. For
  true stock, re-run `Memoria.Patcher.exe` (always works, pre-dates every local patch).

## Build provenance

- Patch file: `memoria-patches/s47-sfx-mesh-probe.patch` — forward-appliable on top of `base + s22..s46`; see
  `memoria-patches/README.md`'s s47 row for the exact hook sites, hunk contents, and the gate method
  (reverse `patch -R -p1 -F0` TEXT-mode clean on live; forward `-F0` TEXT-mode onto a reconstructed pre-round
  snapshot of the 3 touched files reproduces live byte-for-byte once EOL-normalized).
- Built + auto-deployed 2026-07-22 with the game closed: 0 compile errors, 186 pre-existing warnings (all
  unrelated `CS0414`/`CS0169` unused-field notices, normal for this codebase). `Output\Assembly-CSharp.dll` is
  byte-identical to both deployed `x64\` and `x86\` `FF9_Data\Managed\Assembly-CSharp.dll` copies.
- Backups of the pre-s47 installed DLLs (both arches) were taken before building:
  `backups/Assembly-CSharp.x64.dll.20260722-095733`, `backups/Assembly-CSharp.x86.dll.20260722-095733`.
