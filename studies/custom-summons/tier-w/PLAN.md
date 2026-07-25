# TIER W — EDIT A STOCK SUMMON IN PLACE

> **The strategy line this executes** (custom-summons memory): *"the cheap half of TIER W
> (writer/script/reskin + camera, makes stock summons editable in place)"*. TIER R made the cinematics
> **readable**; this tier makes them **editable** — Bahamut rescored, not replaced.

**WHAT TIER R HANDED US** (`../tier-r/`, all three rungs ★):

- **The camera is NOT in the program.** It is played by the SEQUENCE — op `0x29 PLAY_CAMERA` (ef227:
  shots 6/16/47), reading camera sub-files out of the id-2 archive. The effect program cannot reach
  them (id-2/id-5 are never mapped into the id-3 address space). **So a rescore is `.seq` + camera-data
  work, in a layer whose codec we already own** (`ff9mapkit/ff9mapkit/battle/camera_codec.py` — parse /
  serialize / splice / author, shipped for battle cameras).
- **THE TWO-CLOCKS LAW.** Camera cuts land 1–2 frames after program phase boundaries (H → 256 @f58 vs
  phase @f57; → 415 @f153 vs @f152; → 512 @f302 vs @f300). The shots and the phases are **two clocks the
  original author kept aligned by construction.** Change one clock's TIMING and the cut drifts off the
  beat. → this splits the tier's rungs (content vs timing, below).
- **The phase spine is recovered and validated** — `summon-inspect` gives frame→phase→code for ef227 and
  33 other switch-driven effects, with 15/15 capture agreement.
- **One deliberately unsettled question**, R3 §4a: does `op 146` **write** the projection registers or
  only **read** them? (`hle_ops.json`'s `touches` does not distinguish.) Non-gating while READING;
  **gating before the first camera WRITE** — settle it with the named s53 probe row at W2, not before.

---

## The ladder

| Rung | Deliverable | Gate (falsifiable) |
|---|---|---|
| **W1** | **THE READ-OUT** — `summon-camera read <ef>`: which shots the sequence plays, each shot decoded to human terms (keyframes, pose, projection distance, durations), on ONE timeline against R3's program phases | **BYTE-EXACT ROUND-TRIP on every stock summon camera in the corpus** (decode → re-encode == original bytes). **This gate IS the camera recon**: it either proves FORMAT's "same format as the battle camera" claim with an artifact, or names exactly how the summon camera differs |
| **W2** | **THE CONTENT RESCORE** — reframe a real summon's shot (pose / aim / projection distance) with **durations UNCHANGED**, so the two clocks stay aligned and no program byte moves | the op-146 read-vs-write probe row settled FIRST; then a deployed, **cast** proof: the camera looks different, the beats land where they always did, stock data reverts clean |
| **W3** | **THE TIMING RESCORE** — durations change, so the program's phase thresholds must move WITH them (R3 recovered exactly where those constants live) | the retimed cast holds phase↔cut alignment; a deliberate mis-retime is shown to drift (the law demonstrated, not just asserted) |
| **W4** | **THE RESKIN** — retexture a stock creature in place | a cast showing our texture on the stock cinematic, stock bytes untouched |

**Done = "editable in place":** a stock summon can be re-framed, re-timed, and re-skinned from our own
declarative surface, with the stock install revertible at every step.

---

## Hard rules for this tier

- **Never modify stock game data in place.** Everything ships as mod-folder overrides through the
  existing deploy lanes, with a revert script — the summons deploy engine's `_Ledger` posture.
- **READ rungs touch nothing.** W1 is offline and read-only: no deploy, no install writes.
- **Provenance unchanged** (the FORMAT/TIER-R posture): tools, tests, reports, and *our own* authored
  camera data are committable; **decoded stock camera dumps and listings are SCRATCH-only**
  (`C:\gd\SCRATCH\summon-format\`). Zero SE bytes in the repo.
- **The two-clocks law is a gate, not a note** — any rung that changes timing must show both clocks.

## Status

- W1 — IN FLIGHT (the read-out; its round-trip gate does the camera recon).
- W2–W4 — pending W1.
