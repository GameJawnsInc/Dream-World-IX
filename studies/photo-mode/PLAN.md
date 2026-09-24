# Photo mode: a script-driven camera pan (board entry #8)

**Status:** rung 0 ★ **PASSED in-game, 154/154 over six runs** (harness, one change per run, readback and frame
agreeing) and **owner-playtested**: hotkeys, pan speed and the exit glide confirmed. The owner's one defect, a snap
when walking during the exit glide, was fixed by the tracking exit (stage 6). The fix was re-tested by hand and
measured in-game. Next is rung 1, the kit feature.

Board entry #8 of [`../eb-uses-board/BOARD.md`](../eb-uses-board/BOARD.md). It was the runner-up when #7, the sine
kit, was picked. Its reframe is the kit's **first camera-pan primitive**:

- a field script takes the view from the player;
- pans it where the player's held buttons say;
- keeps it on the painting;
- hands it back.

Hiding actors and a held colour grade come after the pan works.

## What the research found (engine-read, before any code)

Four readers covered the engine camera code, hide/grade/input, a stock-corpus census of the camera ops, and the
repo's prior art. Two independent designs followed, then an adversarial judge checked every claim against the C#.
The reports are in the session scratchpad. What changed the plan:

**The board's recipe is a silent no-op.** `EnableCameraServices(0,0,0)` (0x71) clears the field's `Active` bit.
`EBG_scene2DScroll` returns at once when that bit is clear (FieldMap.cs:1463), so every later `MoveCamera` is dropped.

**`MoveCamera` already takes the camera.** 0x6F `[2,2,1,1]`, every operand may be an expression:
- it starts from the current view;
- a finished move enters HOLD (`flags&7 == 4`), where both scroll services return early;
- follow never resumes on its own (FieldMap.cs:1839-1900, 1963).

`ReleaseCamera` (0x70) glides back to the player's clamped follow point, and follow resumes in the same frame. Stock
field 507 is the verbatim ground: a code entry that loops `CalculateScreenOrigin; MoveCamera(X, Y±4, 1, 0); Wait(1)`.

**The script must clamp.**
- Y is never clamped.
- X is clamped once, at issue, and only under the runtime `WidescreenSupport` flag, to the narrowed window. At
  1280×720 on a 768-wide canvas that window is 199..569, not the baked 160..608.
- `SetCameraBounds` (0x1E) does not bound `MoveCamera`.
- 0x73/0x74 are the clamp lock and unlock, not follow switches.

**A script can read the camera.** `0xEA CalculateScreenOrigin` puts the view into `B_SYSVAR[12]`/`[13]`, in exactly
`MoveCamera`'s coordinates: the view centre in canvas px. `0xA9` writes the same two registers, so copy first.

**Other traps.**
- `B_CONST` is a signed Int16, and the kit's assembler accepts `const(32768)` (emitting a negative). Key masks of
  0x8000 or more must go through `const4`.
- A duration of 0 for `MoveCamera` or `ReleaseCamera` is a NaN, or a per-tick `DivideByZero` for type 8.
- `DisableMove`'s walk gate is skipped under `Field.isDebug`, so only a paired lock/unlock check proves the lock.

## Rung 0: the bench and the instrument

**Bench.** Field **30955** PHOTO0 ([`bench/photo0.field.toml`](bench/photo0.field.toml)):
- a 768×448 canvas (the scroll-demo frame), with `[camera.scroll]`;
- a generated, seeded test pattern of 16-px cells (zero Square Enix bytes);
- three red balloons: L, C, and R (R is never hidden).

[`photo0_bench.py`](photo0_bench.py) seats one code-entry daemon into the deployed `.eb`, one **stage** per in-game
run, so each run changes one thing:

| Stage | Adds |
|---|---|
| 1 | Mirrors only: the view (0xEA), the player's screen position (0xA9), usercontrol, the camera index, the held keys. No camera op anywhere; this is the calibration |
| 2 | A command dispatcher driven by harness-poked bytes: move, glide, relative move, release, lock/unlock, and the 0x71 negative control with its recovery |
| 3 | The d-pad pan, `STEP` = 4 px a tick, clamped in the script. MODE 1 is relative (the stock 507 form); MODE 3 is absolute |
| 4 | Hides and the grade (commands 9-18) plus a FLAGS mirror of the show bits. The hides are hide-all/show-all, balloon L by mesh, and C and the player by flags, run through RunScriptSync into functions seated on their own entries. The grade is a held SUB FadeFilter |
| 5 | The modal loop, buttons only. A Select edge opens it (lock, then take). The d-pad pans. R1 hides L (mesh), then C (flags), then the player (flags). L1 toggles the grade. Cancel restores everything and releases |

**Stage 4's open question: does a show undo a flags-hide?** Read in `EventEngine.ProcessEvents.SetRenderer` and
`PosObj.SetIsEnabledMeshRenderer`:
- A flags-hide disables every renderer under the object directly.
- A show only calls `SetIsEnabledMeshRenderer` per mesh. That call is guarded by the `meshIsRendering[mesh]`
  bookkeeping, which the hide never cleared, so it would be a no-op.

Stock hides and shows NPCs this way thousands of times (`SetObjectFlags(14)`/`(7)`), so some path must re-enable
them. No other re-enabling code was found. Every show in stage 4 is therefore measured on the frame on its own, not
inferred from the flags.

**Two independent instruments**, in [`rung0_photo.py`](rung0_photo.py):

1. **Mirrors.** Each tick the daemon mirrors the view **and** the target plus duration class the previous tick
   commanded (TXP/TYP/ISSP). Every sample therefore carries the command its view answers to.
2. **`tmpl`.** Every rest shot is registered against the regenerated canvas by FFT correlation over every offset,
   never seeded from the readback. On synthetic frames with blur, sub-pixel shift and fake actors it recovers the
   exact offset, scoring about 0.99 against a runner-up of about 0.2.

[`daemon_sim.py`](daemon_sim.py) steps the daemon's own assembled bytes against a model of the camera. It catches
RPN, branch and clamp bugs offline; it says nothing about the engine.

**Frozen predictions** ([`rung0_predictions.json`](rung0_predictions.json), from the built camera; 1280×720, widescreen
on, CameraStabilizer 0):

| Prediction | Value |
|---|---|
| Spawn view | (384, 286) |
| Effective window | X 199..569, Y 112..336 |
| Drawn top-left | (VX − 199, VY − 112) |
| Move latency | exactly one tick |
| X clamp | at issue |
| Y clamp | none |
| Relative pan | no wind-up |
| Absolute pan | 9 commands of wind-up |

## Runs

| Run | Stage | Result |
|---|---|---|
| 1 | 1: calibration | ★ **17/17** (`photo-rung0-s1`, 39 s) |
| 2 | 2: the dispatcher | ★ **32/32** (`photo-rung0-s2`, 53 s) |
| 3 | 3: the pan | ★ **27/27** (`photo-rung0-s3`, 61 s) |
| 4 | 4: hides + grade | ★ **30/30** (`photo-rung0-s4`, 55 s) |
| 5 | 5: the modal loop | ★ **26/26** (`photo-rung0-s5`, 54 s) |
| 6 | 6: the tracking exit | ★ **22/22** (`photo-rung0-s6`, 49 s) |

**Run 1: the instrument is calibrated.** Every frozen prediction held exactly:
- **Spawn:** view (384, 286).
- **Registration:** the frame registered at (185, 174) = (VX − 199, VY − 112), score 0.995 against a runner-up of
  0.196. A second rest shot registered identically.
- **Screen position:** 0xA9 put the player at screen x 960.
- **Follow:** the four walks saturated at the **widescreen** window, X 569 and 199, and the bottom Y 336. Each rest
  view equalled the follow model of the player's actual position to the pixel, and the frame agreed. The runtime
  widescreen flag is on, so the predictions stand.
- **Input:** 30 idle ticks read KEYS 0. A harness `hold right` reached the script's `B_KEY` in 11 ticks and walked the
  player 600u.

The one logged exception is Memoria's `TextImporter` "Failed to load embaded resources". It appears in every earlier
bench run (the sine-kit ones included), so it is not this bench's.

**Between runs 1 and 2: an adversarial review** (three lenses: engine truth, check validity, harness protocol) found
no engine-truth error in the bytes. Every opcode, operand order and RPN rule it checked held against the C#. It did
find checks that could not fail or could fail for the wrong reason:
- **3.3 could not fail.** Calibration left the view at the X edge, so the pan's rate was never tested. The run now walks
  back to mid-window first and refuses a saturated pan.
- **2.8 was a coin flip.** Where the walk landed decided it. It now walks to a fixed point 185 px from the release
  target.
- **LATCH was true by construction.** It now checks the latch held at least one tick.
- **C-CORE had no slack.** Its sample floor was exactly the number of moves. It now expects a sample per dispatched
  move and reports poll gaps separately.
- **Single-sample verdicts** in 2.2 and 3.7 were rebuilt so one missed poll cannot decide them.
- **A latent daemon bug.** A MODE-1 idle pass overwrote a dispatcher move's target in the same tick. The pan now writes
  a target only when it issues a move, and `daemon_sim.py` pins that.
- **Harness protocol.** The scenario no longer calls `g.quit()`, which would close an attached game. A preflight crash
  is now recorded as a failed check. Each run writes `photo_run.json` with commands, fits and notes.

**Run 2: the dispatcher.** Every prediction held, glides to the pixel:
- **Take and hold.**
  - A one-tick `MoveCamera(300,200)` from follow read back **exactly** on the next tick; the ack tick still showed the
    old view.
  - The frame registered at (101, 88).
  - It **held** while the unlocked player walked 900u under it, with no move re-issued.
- **Clamps.**
  - X is clamped **at issue** to the widescreen window: 100 became 199, and 700 became 569, with the frame at the
    canvas edges.
  - Y is **never** clamped. At 40 and 400 the view read back as commanded, and the frame drew 72 and 64 rows past
    the painting.
- **Glides.**
  - A 30-tick glide matched the engine's per-logic-tick interpolation with worst error **0** over 30 samples. The
    per-render-frame model misses by 125.
  - `ReleaseCamera(20,0)` glided linearly to the follow point (worst 0), and follow resumed after a walk.
  - `ReleaseCamera(16,8)` followed the float32 cosine ease (worst 0).
- **The board's recipe.** After `EnableCameraServices(0)` the same move was dropped: neither the readback nor the
  frame moved. `EnableCameraServices(1)` recovered.
- **Registration.** The balloons moved with the view within 6 px across four pairs of rest shots.
- **C-CORE.** All 8 one-tick moves were observed, all exact.

**Run 3: the pan.**
- **Rate.** Held right with the player locked, the view moved exactly 4 px per polled tick (11 ticks = +44). The
  frame moved the same 44 px, and the player did not move.
- **Edges.** The relative pan stops at 569 while its target reads 573 (68 samples) and leaves the edge on the first
  left tick, with no wind-up. The script's Y clamp holds the frame on the painting's top and bottom edges.
- **Lock.** Unlocked, the same hold walks the player 600u **and** pans. So the lock, not the poll, kept the player
  still.
- **Absolute form.** Its target winds up to 608 behind the engine's 569, 9 commands pinned, and the first under the
  edge lands exactly (568).
- **Exit.** Release plus unlock hands the view back to follow.
- **C-CORE.** All **412** samples whose previous tick issued a one-tick move read that target exactly, with X
  clamped at issue and Y untouched.

**Run 4: hides and the grade.** Each hide and each show was measured on the frame (red connected components for the
balloons, non-palette pixels in a box on the player's 0xA9 point), not inferred from flags:
- **Flag hides.** C and the player by flags, through RunScriptSync(2, uid, 40/41) into functions seated on their own
  entries: the show bit clears, the object vanishes, and the show brings it back. The daemon kept ticking; it acked
  each command.
- **Mesh hide.** Balloon L by mesh (0x3A/0x39 over meshes 0-15, by uid): it vanishes with its **flags untouched**,
  and comes back.
- **Hide-all / show-all.** 0xD5 hides the player and all three balloons (FLAGS 0). 0xD6 restores exactly the state
  before.
- **Negative control.** R, never a target, stayed drawn with its show bit set through every step but hide-all.
- **The grade.** A SUB `FadeFilter(2, 8, 0, 0, 64, 128)` took the white cells from (235, 235, 235) to exactly
  **(235, 171, 107)**, the same in all three thirds of the frame. That is the gamma-space subtraction; the
  linear-space prediction (~235, 228, 206) is refuted. It held with no drift over 120 frames, and the same channel at
  (0, 0, 0) restored the frame exactly.

**The source-read prediction was wrong.** Shows after a flags-hide **do** come back, for both a kit prop and the
player. Some engine path re-enables the renderers that `SetRenderer`'s show branch alone would not; it was not found
in the read. This is recorded as a reading that failed against the frame. It is the reason every show was measured
separately.

**Run 5: photo mode, driven by the player's buttons alone.** No harness pokes.
- **Closed.** R1, L1 and Cancel edges reached the poll (EDGES counted them) and changed nothing.
- **Open.** One Select edge locked the player and **took the camera where it already was**: no jump on the readback,
  and the frame registered at the same offset.
- **Hide cycle.** R1 hid balloon L (mesh), then C (flags), then the player (flags). A fourth R1 changed nothing.
- **Pan.** The d-pad panned the open view exactly 4 px a polled tick (11 ticks = +44). The frame followed by 44, and
  the hidden player did not move.
- **Grade.** L1 toggled the grade on (235, 171, 107), off (235, 235, 235), then on again.
- **Exit.** One Cancel edge did all of this together:
  - showed everything it had hidden (FLAGS 15, three balloons, the player);
  - cleared the grade;
  - eased the camera back with `ReleaseCamera(16, 8)`, matching the float32 cosine curve with worst error 0 over 16
    ticks;
  - handed control back.

  **The frame registered exactly where photo mode found it.**
- **Edges.** Every one of the 14 photo-button presses was exactly one edge (EDGES +17697, as predicted).
- **Afterwards.** Follow tracked the walking player again.

## The owner's playtest, and stage 6

**The owner playtested bench 30955 (stage 5).**
- **Confirmed:** every hotkey worked, the pan speed is good, and the exit glide is good.
- **The defect:** it does not track a player who walks during the glide. The camera glides to where the player *was*
  at Cancel, then snaps to where he moved.
- **Why:** `ReleaseCamera` computes its target **once** (FieldMap.cs:1486-1537), and `EnableMove` hands control back
  in the same Cancel tick. The engine research had flagged this as inferred; no stage 1-5 check walked during a
  release.

**Stage 6, the tracking exit.**
- **How it tracks.** Cancel issues `ReleaseCamera(104, 0)`, and every tick of the glide re-issues
  `ReleaseCamera(n_k, 0)` with n = (104, 35, 21, 15, 11, 9, 7, 6, 5, 4, 4, 3, 2, 2, 1, 1).
  - A linear release covers 1/n of what remains in its first frame, and each re-issue re-reads the player's follow
    point.
  - So the camera eases toward a **moving** target and lands on it at n = 1, where follow resumes with nothing left to
    jump.
- **Why it keeps the feel.** The table is the approved cosine ease re-expressed as per-tick fractions of the
  remainder. On a still player it traces `ReleaseCamera(16, 8)` within 0.55 px (offline).
- **Re-opening.** Re-opening photo mode mid-glide stops the tracking.
- **Byte discipline.** Stages 1-5 still build byte-identical to their in-game-proven bodies.
- **The owner's re-test.** The owner played it by hand on 30955 and confirmed the chase-in works.

**Run 6** (the harness, one launch, the same exit run three ways):

| Case | Exit | Result |
|---|---|---|
| NC-SNAP | Stage-5 single release; the player runs 1080u through the glide | Glides out to 470, where he was at Cancel, then **jumps 113 px in one tick** to 357. The owner's defect, reproduced and measured |
| Tracking | Per-tick re-issued release; the same run | Turns and chases him in: 438 → 405 → 366 → 357 → … 314. **Largest one-tick move 28 px.** Rests exactly on the follow point (314); control was back from Cancel |
| Still | Tracking; the player stands | Traces the approved cosine ease with worst error **1 px** over 16 ticks and lands on him |
| Re-open | Select during the glide | Stops the tracking and the camera holds (one view for 25 ticks); Cancel closes cleanly |

## Rung 0 verdict

★ **PASSED: 154/154 checks over six in-game runs, one change per run** (stage 6 added after the owner's playtest). Every claim was measured two independent ways
(the engine's own readback and the registered frame), with negative controls. The camera-pan primitive is:

| Step | How |
|---|---|
| Take | `DisableMove`, then `MoveCamera(VX, VY, 1, 0)`, where VX/VY come from `CalculateScreenOrigin` (0xEA → `B_SYSVAR[12]/[13]`). It takes the camera exactly where it is, and the camera then HOLDS |
| Pan | Each tick, relative to the mirrored view (stock 507's form, no wind-up): `MoveCamera(VX ± step, VY ± step, 1, 0)`, clamped **in the script**. The engine clamps X only at issue, to the widescreen-narrowed window, and never clamps Y |
| Give back | `EnableMove`, then a **tracking** release: `ReleaseCamera(n_k, 0)` re-issued every tick with n = (104, 35, 21, 15, 11, 9, 7, 6, 5, 4, 4, 3, 2, 2, 1, 1). It eases like `ReleaseCamera(16, 8)` and lands on a player who walks during it. A single release computes its target once and snaps |
| Never | `EnableCameraServices(0)` (it kills every pan), 0x73/0x74 (clamp unlock/lock) or 0x1E |
| Hide | By mesh (0x3A over meshes 0-15, any uid, flags untouched), by flags (a function seated on the target's own entry, run through `RunScriptSync(2, uid, tag)`), or all at once (0xD5/0xD6). Every one comes back |
| Grade | A held SUB `FadeFilter`, subtracted in gamma space; the same channel at 0 clears it |

## What rung 1 (the kit feature) inherits

What the kit needs to ship this as a `field.toml` surface, from the runs above:

- **Emitters.** Add 0x6F / 0x70 / 0xEA to `eb/opcodes.py`. Take, pan and give-back as above. Never emit 0x71(0),
  0x73, 0x74 or 0x1E.
- **The pan box, per camera, chosen by `B_SYSVAR[1]`.**
  - The script must clamp to the **effective** box.
  - The engine narrows X at 16:9: 199..569 on a 768 canvas, against the baked 160..608. At 4:3 it clamps nothing.
  - The lint reports both boxes in pixels and refuses a field whose canvas is no wider than `PsxFieldWidth`, where X
    is pinned. A default 384-wide kit field is Y-only.
- **Button contention.**
  - `[[ate]]`, the behavior hire poller and `[siege]` already own Select, so the open button is author-set, and the
    lint catches a collision.
  - Key masks of 0x8000 or more must be `const4`. The kit's assembler accepts `const(32768)` and emits a value the
    engine reads as negative.
  - Photo mode opens no windows today. Any caption window it adds must carry `[NTUR]`.
- **Hide targets.** Kit props and the player both work by flags and by mesh. Which one to ship is a design choice:
  flags also hides the blob shadow, and mesh does not.

**Still open, and the owner's call:**
- **The feel.** Pan speed, whether 4 px a tick feels right, and the ease on exit. Bench 30955 is deployed now: ~ →
  Warp to field → 30955, press **Select** to open photo mode, the d-pad pans, R1 hides, L1 grades, Cancel exits.
- **`CameraStabilizer` at its default of 85.** This install runs 0, so the on-screen lag of a pan is unmeasured.
- **Whether `content/camera.py`'s injected `EnableCameraServices(1,0,0)` is a no-op.** The source says `BG_init`
  already sets Active; run 6 would prove it.

Offline aids: `daemon_sim.py` (this study) steps the daemon's bytes. `ff9mapkit/tests/_ebengine.py` is the suite's own
`.eb` interpreter and is the one to use when rung 1's emitters get unit tests.
