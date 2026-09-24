# Photo mode: a script-driven camera pan (board entry #8)

**Status:** rung 0 in progress. The bench, the daemon for stages 1-3, the offline stepper and the harness scenario are
built; stage 1 is the first in-game run.

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
| 4-5 | Hides and the grade, then the modal Select/Cancel loop. Not built yet; next after 3 |

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
