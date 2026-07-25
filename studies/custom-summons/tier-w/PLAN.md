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

## ★ THE EFFECT-OWNED SCENERY LAW — what W2's cast actually minted (2026-07-25)

> ⚠ **A FIRST READING OF THIS CAST WAS WRONG AND IS RETRACTED.** It called the folding surface the
> *battle background* and concluded the envelope was per-battle-location. **The owner falsified it with
> a one-cast experiment: he cast the same summon in ICE CAVERN and the ground was NOT SNOWY — it was the
> same satellite-view terrain.** The surface is not the arena. Kept visible because the wrong version
> pointed the tier at the wrong ceiling.

**What the cast really showed.** Bahamut's cinematic **ships its own scenery** — an authored ground
plane that travels with the effect and displaces the arena during the aerial beats. (The real battle
background *does* show at other points in the same cutscene; the two alternate.) Widening the entrance
shot revealed that ground's edges and seams, because it is finite geometry modelled to look right from
the shot it was authored for.

**Confirmed in the container, offline:** ef227's chunk 0 carries, beyond `SUMMON_MODEL` (Bahamut
himself, 156 KB), a `MARK_6` (26 KB) and two `MARK_7` (70 KB) geometry resources plus two VRAM texture
pages — the FORMAT round's "32 eff slots = the effect's beams and props." R3's phase table shows the
entrance phase we rescored (`c0` state 0, f57–126) **draws effect models**, and other phases do not.
So: effect-owned geometry, drawn on a schedule we can already read.

**THE LAW:** *a summon's cinematic is a self-contained set — creature, props, AND scenery — authored to
look right from its own camera. Rescoring the camera without regard for that set will show the set's
edges.* The constraint is **per-SUMMON and lives INSIDE the container**, not per-battle-location.

**Why this expands the tier rather than capping it.** The folding surface is not the game's; it is
**ef227's, in a container we can now read, patch, and ship**. The scenery is in scope — the same
override path that carried four camera bytes can carry a re-authored ground. So the ceiling on
"rescore stock summons" is not FF9's arenas at all: it is only that the camera and the effect's own
scenery must be re-authored *together*.

**Practical rules (unchanged in substance, re-derived on the right cause):**
1. **Focal distance (H) is the safest lever** — it reframes without moving the eye, so it exposes less
   of the effect's own set than a pose change does.
2. **Back-and-up is the riskiest direction** — it grows the visible footprint, which is exactly what
   finds the scenery's edge. Lateral/inward stays inside the authored set.
3. **Judge each shot against the phase table** (`summon-inspect`): a phase that draws effect models is a
   phase where the set is on screen and the reframe budget is tight; a phase that draws only the
   creature is far more forgiving.
4. **W4's scope grows:** "reskin" should be read as the effect's whole set — creature *and* scenery.

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
