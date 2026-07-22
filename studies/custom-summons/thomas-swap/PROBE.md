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

## 8. Round 1 results — the 2026-07-22 calibration cast

One `--calibrate` cast (`studies/custom-summons/thomas-swap/build_thomas.py --calibrate`, Bahamut's
mesh fully unsuppressed) logged the whole ~40s "Bahamut Cinema" cinematic to
`sfxmeshprobe.log`: **19,456 MESH rows, 0 CAM rows**, `effectId=227` throughout (the real donor alone —
this calibration cast pre-dates Thomas's own JSON mesh entirely). Rows tally to exactly **39 distinct
`keyHex` values**, frames spanning ~11-510 at ~15/s (`video t ≈ 6 + frame/15`).

### The CAM-hook defect (confirmed, out of scope today)

Zero of the 19,456 lines are `CAM` lines — the camera-logging hook (`SFXDataCamera.UpdateCamera()`,
gated on `SFXDataCamera.currentCameraEngine == CameraEngine.SFX_PLUGIN`) never fired during this whole
cast, even though the donor's own `LoadSFX: SFX=Bahamut__Full ; UseCamera=True` line is known to arm
the native camera track for the real cinematic. Either the gate condition never evaluated true on this
build, or the hook itself has a wiring defect (unverified which — no disassembly was done this round).
**Known probe defect, confirmed by this cast, explicitly out of scope for this build** — nothing in
`build_thomas.py`'s own FLIGHT reconstruction depends on the CAM rows (only MESH rows were used); a
future round could cross-validate a reconstructed position against the real camera framing once this
is fixed, but no reconstructed number in this build has been checked against actual on-screen framing
by that means.

### The 39-key classification

7 **CREATURE/BODY** keys — present together on 301 of Bahamut's own 325 on-screen frames (92.6%),
their consensus trajectory tracing one coherent, physically sensible flight (see "The measured
trajectory" below) — confirmed as `HIDE_KEYS` in `build_thomas.py`:

| Key | Rows | Frame span | Pairing |
|---|---|---|---|
| `0033B990` | 1263 | 82-412 | paired w/ `0033B9D0` |
| `0033B9D0` | 1263 | 82-412 | paired w/ `0033B990` |
| `0035BAD0` | 1215 | 82-410 | paired w/ `0035BA90` |
| `0035BA90` | 1264 | 82-414 | paired w/ `0035BAD0` |
| `0034BA10` | 1226 | 82-411 | paired w/ `0034BA50` |
| `0034BA50` | 1246 | 82-411 | paired w/ `0034BA10` |
| `0097BD02` | 1287 | 82-417 | standalone |

23 **confirmed KEEP-VISIBLE** effect keys (never added to `HIDE_KEYS`): the cast-in swirl
`0039BE40`/`0099BD00` (58-127, ends exactly as the body appears — a clean handoff); the persistent
backdrop/fade pair `00800000` (11-510, spans nearly the whole cast)/`00000000` (46-510); the sky-act
backdrops `00BDBD40`/`009DBD02` (104-204) + the wider `24C28000`/`24C08000` (167-432, spanning sky-to-
ground); the wing-trail `003BBD40` (178-380, constant `x=1058` the whole time — a fixed local-frame
contrail riding the body); the 6 charge-orb keys `0496BD07`-`0496BD0B`/`04B6BDC0` (all exactly 380-401,
tight non-pool bounds — genuine small props); the beam `01000000` (385-434); and the fire-column group
— `00B9BC80`/`00B9BCC0`/`00598000`/`009DBE81`/`00B7BD40`/`00BDBEC0` (~433-510ish) **plus `00B7BD80`**
(422-448 — folded in this round: same sibling-suffix naming pattern as the orb family, differs from
`00B7BD40` by only its last byte, its z-band sits squarely inside the fire-column group's own range,
and its frames are the natural windup immediately before the column ignites at 433).

9 **remaining keys, genuinely ambiguous**, all defaulted KEEP-VISIBLE this round (never blindly added
to `HIDE_KEYS`):

| Key | Rows | Frame span | Reasoning |
|---|---|---|---|
| `0097BD01` | 703 | 260-510 | shares the `0097BD0_` prefix with confirmed body key `0097BD02` but DIVERGES from the body trajectory at nearly every overlap (dz swings -1936 to -6880) and persists ~90 frames past the body's own end (417) into the fire-column window — almost certainly a separate ember/scorch effect reusing the naming convention by coincidence (pooled-slot key reuse), not body |
| `0097BD0C` | 603 | 256-497 | same reasoning as `0097BD01` |
| `0097BD04` | 124 | 354-384 | narrow charge/blast-window prop with CONTAINED (non-pool) x/y bounds unlike every other key — a small localized glow prop (mouth/eye charge), not body |
| `0097BD05` | 120 | 355-384 | same reasoning as `0097BD04` |
| `0497BD06` | 176 | 244-431 | shares the `0497BD0_`/`0496BD0_` prefix with the confirmed charge orbs — a longer-lived windup-glow/ember-afterglow companion of that same family |
| `0497BD0D` | 751 | 250-515 | same reasoning as `0497BD06` — outlives even the fire column, ending at the log's own last frame (515) |
| `0497BD03` | 451 | 338-498 | same reasoning as `0497BD06` |
| `0098BD0E` | 392 | 249-384 | partially tracks the body during its smoothest drift (dz within ~200u at several points) but diverges sharply at the edges and doesn't extend into the fire-column era the way effect keys do — likely a throat/muzzle glow riding along with him, not a body part. **Live round-2 candidate** |
| `00BDBE00` | 44 | 167-177 | only 2 frames overlap the body's own log, but at those 2 frames it closely tracks the body's own deepest excursion (dz=+896) — plausibly a hero/close-up swap submesh for the iconic hover shot. **Live round-2 candidate** (LOW confidence — only 2 overlap frames) |

### The trajectory reconstruction method

Per frame, median across the 7 confirmed creature keys of: **X, Y = bounds CENTER** (`cx`, `cy`); **Z
= the FAR CORNER** (`center ± extent`, whichever side has the larger magnitude). The far-corner pick
is essential for Z (the body sits far enough from world origin that it reliably recovers true depth)
but chases silhouette extremities on X/Y if applied there too — validated by an independent
cross-check: raw CENTER `cy` stays in `[-480.5, +511.5]` across all 8,764 creature-key rows, matching
this same cast's own cluster read ("Y never exceeds ~±512") almost exactly. This deviates from a
literal all-axis far-corner reading; flagged here for anyone re-deriving the method from scratch.

The resulting per-piece-boundary trajectory (frame → (X, Y, Z), median across the 7 keys) was
independently re-verified against the raw log while building `build_thomas.py` — every reconstructed
number below reproduces exactly:

| Frame | X | Y | Z | Piece boundary |
|---|---|---|---|---|
| 82 | 132.5 | 511.5 | -1568 | P1 dest (entrance settle) |
| 144 | 128.5 | 127.5 | -17856 | P2 dest (rise-to-far) |
| 157 | 5.5 | -19.5 | -8592 | P3 dest (far-dip) |
| 166 | 34.5 | -0.5 | -34768 | (the cast's single deepest point, mid-P4, n=4 rows -- see correction below) |
| 172 | -265.5 | -424.5 | -34368 | P4 dest (far-deep hold, n=4 rows -- see correction below) |
| 179 | 144.0 | 46.5 | -4864 | P5 dest (return-cut, n=28 rows -- see correction below) |
| 204 | 143.0 | 124.0 | -12336 | P6 dest (2nd-approach) |
| 207 | 152.0 | 201.5 | -4720 | P7 dest (charge-cut, n=28 rows -- see correction below) |
| 250 | 119.5 | 117.5 | -3968 | P8 dest (charge-hold) |
| 414 | 34.5 | -0.8 | -3832 | P9 dest (ground-reign, n=8 rows) |
| 417 | 34.5 | -0.5 | -9616 | P10 dest (exit-edge, n=4 rows) |

These 11 destinations (+ the reasoned, unmeasured `ENTRANCE_ORIGIN`/`P11_TAIL_DEST`) are baked into
`thomas_manifest.sfxmodel`'s `Movement` array as absolute-world NCalc constants — see README.md's
"THE FLIGHT v2" section for the full piece table cross-referenced against the video beats, and
`build_thomas.py`'s own `THE FLIGHT v2` comment block for the named constants.

### Sample-count correction (adversarial verification round, 2026-07-22)

The first pass of this round-1 writeup mislabeled *which* piece-boundary frames are actually
low-sample. Re-querying the raw log directly (grouping by exact `frame`, counting rows among the 7
confirmed creature keys) finds:

- **P5_DEST (frame 179) and P7_DEST (frame 207) are each backed by a full `n=28` rows** (all 7 keys
  logged that exact frame) — solid, high-confidence point estimates, not the `n=4` "best-effort read
  of a genuine hard transition" the original writeup (and `build_thomas.py`'s CAVEAT (a)) claimed.
- **The genuinely sparse/gappy region is frames ~153-177** (inside P3/P4, not P5/P7): frames
  `153, 154, 167, 168, 170, 171, 173, 174, 175, 176, 177` have **zero** creature-key rows at all, and
  `155` (n=8), `165` (n=16), `166` (n=4), `169` (n=4), `172` (n=4) are all under-sampled. **`P4_DEST`
  itself (frame 172, the deepest/most dramatic point of the whole flight, `-266,-425,-34368`) is the
  actual `n=4` low-confidence measurement** — the single most visually dramatic pose in the
  reconstruction is also its least-sampled data point, and this went uncalled-out in the original
  writeup. This gap also lines up with (and reinforces) the independently-flagged "frames 167-177"
  window in the round-2 protocol's `00BDBE00` check below — the same window shows up twice, for two
  different reasons, which is a good cross-check that something genuinely unusual (bounds pooling
  out, a mesh instance recycling, a hero-cam submesh swap, or the real hard cut itself starting a few
  frames earlier than the piece table currently models it) is really happening there.
- `P9_DEST` (414, n=8) and `P10_DEST` (417, n=4) were already correctly flagged as low-sample.

**Net effect on the deployed build: none.** The actual `Movement` numbers at every piece boundary
were independently re-derived from the raw log and match the deployed `thomas_manifest.sfxmodel`
exactly (see `build_thomas.py`'s own CAVEAT (a), now corrected to match this section) — this is a
correction to the *confidence labels* in this doc and that comment block, not to any deployed
coordinate. If anything, P5/P7 are more trustworthy than previously stated; P4 is the piece that
actually warrants the "kept fast/short, don't over-interpret" treatment CAVEAT (a) originally gave to
P5/P7.

### Round 2 refinement protocol

A future recast (armed the same way — `[SfxProbe] Enabled=1`, relaunch, `--calibrate`, cast, let it
play through) should specifically check:

1. **`00BDBE00`** — add it to `--hide-keys` alongside the 7 confirmed body keys and watch frames
   167-177 specifically: if a hero/close-up submesh vanishes along with the body, it's body; if
   nothing visible changes, it was already redundant with a confirmed key and safe either way.
2. **`0098BD0E`** — same test, frames 249-384: does anything read as "the head/muzzle" disappearing
   alongside the body, or does an independent glow effect stay put?
3. **The unmeasured tail (frames 417-580)** — this cast's log runs out at ~510-515 (only fire-column/
   ember keys, no creature keys past 417). A recast that lets the *whole* cast play through AND is
   captured on video for that specific tail window would let `ENTRANCE_ORIGIN`/`P11_TAIL_DEST` (both
   currently reasoned extrapolations, zero ground truth) be replaced with real data.
4. **`00B7BD80`'s fire-column membership** — inferred from naming pattern + z-band overlap only, not a
   frame-by-frame visual cross-check against the calibration video. A quick spot-check would settle it.
5. **The CAM-hook defect** — if a future engine round fixes the wiring so `CAM` rows actually log, a
   fresh cast could cross-validate the whole reconstructed trajectory against real camera framing for
   the first time (see "The CAM-hook defect" above — no reconstructed number in this build has been
   checked against on-screen framing by that means).
6. **Clock-alignment slop** — a log taken *after* `build_thomas.py`'s own deploy (not just
   `--calibrate`) would, for the first time, contain Thomas's own JSON-mesh key alongside Bahamut's,
   letting both clocks be read from the same log rather than assumed aligned at offset 0.

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
