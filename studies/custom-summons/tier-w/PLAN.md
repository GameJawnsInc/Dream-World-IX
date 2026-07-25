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

## ★ THE BACKGROUND-GEOMETRY ENVELOPE — the law W2's cast minted (2026-07-25)

**The mechanism works; the *world* is what bounds it.** W2's cast landed — stock Bahamut's entrance
visibly pulled back and re-angled, then snapped to stock exactly as authored. But the widened frame
showed the battle background **folding in on itself**: at the new angle the terrain reads as a finite
polygon with a hard edge and visible seams, with void beyond it.

**THE LAW:** *a battle background is finite geometry authored to look right from the shot's ORIGINAL
camera. A rescore's validity is bounded by that geometry, not by the camera format.* Pull back or
re-angle far enough and you see the mesh's edge, its backfaces, or its seams — the summon is fine, the
world ran out.

**The envelope is per-BATTLE-LOCATION, not per-summon.** The same delta that is safe in a walled
interior arena will show void on an open world-map encounter (which is where W2's cast ran — the
terrain chunk under a world-map battle is the thinnest background in the game). So a rescore cannot be
validated once and declared good; it is valid *for the arenas it was judged on*.

**Practical consequences for W3/W4 and any authored rescore:**
1. **Direction matters more than magnitude.** Pulling BACK and raising the angle are the two riskiest
   moves — both grow the visible footprint. Lateral moves, small yaw, and pushing IN stay inside the
   authored footprint by construction.
2. **Judge on the thinnest arena you intend to ship on**, not the friendliest one.
3. **Focal distance (H) is the safest lever** — it reframes without moving the eye, so it changes what
   is seen far less than a pose change does.
4. This is ALSO the honest limit on "rescore stock summons" as a feature: the ceiling is not our
   tooling, it is that FF9's arenas were built for the shots FF9 ships.

## Status

- **W1 — ★ DONE** (`W1-READOUT.md`, `summon_camera.py`, `test_summon_camera.py`, `w1_gates.py`;
  5/5 gates). **THE RECON ANSWER: outcome 1 — 798/798 stock summon camera blocks across 372/372
  effects round-trip BYTE-IDENTICAL through the unmodified battle `camera_codec.py`.** The FORMAT
  claim is proven with an artifact. Three corrections fell out (`0x23 SETUP_CAMERA` names 713 of
  the 798 blocks; the id-2 directory sits AFTER the extra-sector region; the Code `frame` word
  carries flags in its top 3 bits), and the two-clocks law is now a number: the authored cut LEADS
  the beat by 1/1/0 ticks and the runtime install lags by a constant 2.
- **W2 — ★ BUILT, awaiting the cast** (`W2-RESCORE.md`, `rescore.py`, `bahamut_rescore.toml`,
  `test_rescore.py`, `w2_gates.py`; 6/6 gates, 34 tests). **ef227 shot A's opening keyframe reframed
  in 4 BYTES of an 823,296-byte container** — yaw, roll and the projection distance, all in place.
  Every duration byte, every frame word, all 83 other sub-files and the whole id-2 directory are
  byte-identical, and the patched container still round-trips byte-exact through the unmodified W1
  path. The op-146 probe row is settled ahead of it (op 146 WRITES `gteOFX`/`gteOFY` but restores
  them before its single `ret`, and only READS `gteH`; 121/122 have no corpus call site) — so no
  effect program sets zoom and a rescore is a sequence/camera-data edit, as W1 assumed. STAGED only,
  under `C:\gd\SCRATCH\summon-format\rescore-w2\`; the cast protocol is `W2-RESCORE.md` §6.
- W3–W4 — pending the W2 cast.
