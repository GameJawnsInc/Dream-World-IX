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
| **W5** | **THE GENERALISATION** — the W tools take ANY stock summon (scaffold verbs, derivation-first, named refusals: texanim / multi-writer / dual-depth / dynamic-op / half-patch / headroom) | offline: 372/372 corpus sweeps + ef227 byte-compat pinned in gates; in-game: a SECOND summon's cast on each lever — Phoenix ef211 (scenery + camera) and Madeen ef251 (creature) |

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

> ⚠ **CORRECTION 2026-07-26 (W4 recon, `w4-recon/A2-ATTRIBUTION.md` §8) — the resource attribution above
> is WRONG about `MARK_7`.** Both `MARK_7` payloads (`0x090800` and `0x099800`) open with the ASCII tag
> `AKAO` and contain **zero** `GEOM` blocks; the corpus-wide `GEOM` census (FORMAT §2.3) also lists no
> id-7 blocks anywhere. `MARK_7` is **AKAO audio, not geometry.** The effect's own scenery actually lives
> in **`MARK_6` (6 models: sky gradient shell + cloud sheet + cloud bands A/B, 26 KB) and the two id-2
> sub-file archives** (2 models in chunk 0's archive — the aerial ground plane + the water/ice sheet —
> plus 7 in chunk 1's, including the fire column and the impact/energy rings; 11 textured effect models
> total, per A2 §3.2). **The law itself stands** — the scenery is still effect-owned, self-contained, and
> drawn on the schedule R3's phase table already read — **only the byte-level resource attribution was
> wrong.** Left visible rather than silently fixed, per this tier's own house rule: a wrong reading stays
> on the record so a later reader does not re-cite it. (Note: `W2-RESCORE.md`'s own retracted-finding
> section at the bottom of that report repeats the same `MARK_7`-is-geometry mistake, inherited from this
> paragraph before it was corrected — not re-edited there, since W2-RESCORE.md is a closed, cast-verified
> report and this correction lives at its source.)

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
- **W3 — ★★ CAST-PROVEN 2026-07-26 ("worked as described"; both casts + revert run; live install
  verified back at W2's resting state)** (`W3-RETIME.md`, `retime.py`, `w3_program_edits.py`,
  `w3_clock_emu.py`, `bahamut_retime.toml`, `test_retime.py`, `w3_gates.py`; X0-X7 all PASS, 256
  tests, two independent from-bytes re-derivations (V1/V2) could not refute the offline proof).
  `ef227:c0` state 0 stretched 70→118 ticks (N=+48, exactly two loops of the creature's 24-frame
  float clip) and all four clocks it touches moved with it in one build: the effect program (7
  splices, 12 differing bytes — the threshold plus the two magic reciprocals that normalise the
  arrival/progress ramps to the new length), the sequence stream (1 byte, a `WAIT` delta), the
  camera's shot-A frame words (10 writes, 11 bytes, zero duration bytes touched), and the outer
  text `Sequence.seq` clock (1 `Wait:` line) that SFXRework silently substitutes for the binary's
  own sounds/fades/damage cue. A twin MIS-RETIME artifact ships the same three edits with the
  program edit omitted, byte-identical to the ALIGNED build outside those 12 bytes — the offline
  lock table (12 pairs, recovered from stock and re-timed by identity) shows ALIGNED keeping every
  authored camera-vs-phase lead and MIS-RETIME drifting by exactly N on every post-cut `c0` pair
  while all six `c1` pairs stay put, which is the two-clocks law made falsifiable rather than
  asserted. Residual risk is small and disclosed (the light column reads 38% through its ramp
  instead of 65% at the cut, by the locked policy's own design — the one place a discrete-beat
  constraint stops a ramp from being retuned in full); nothing else moves that shouldn't.
  Staged under `C:\gd\SCRATCH\summon-format\retime-w3\`; **the ALIGNED artifact + text co-retime
  are LIVE in FF9CustomMap** (deployed during verification by an errant sandbox harness, then
  byte-verified and adopted — `W3-RETIME.md` §6.1's LIVE-STATE NOTE; snapshot + revert chain
  verified intact). Cast 1 needs no deploy step; `deploy_misretime.py` swaps to the falsifier;
  `revert_summon_retime_227.py` restores W2's resting state. The cast protocol is `W3-RETIME.md`
  §6, and the rung does not close until both casts are judged.
- **W4 — ★★ CAST-PROVEN 2026-07-26 ("all good", after cast 1 minted THE HYBRID MASK law and the
  recast ran with `[SfxHybrid]` disarmed). THE TIER IS COMPLETE — 4/4: re-framed, re-timed,
  re-skinned, all in place, all revertible. Resting: the reskin LIVE, SfxHybrid disarmed.**
  (`W4-RESKIN.md`, `reskin.py`,
  `bahamut_reskin.toml`, `test_reskin.py`, `w4_gates.py`; X0–X6 + 7/7 negative refusals, 38 new tests
  / 294 tier-wide). **THE WHOLE-SET CLUT RECOLOUR of ef227 — creature AND the effect's own scenery,
  lever #1 (CLUT recolour) only, no texel moved.** 4,832 of 823,296 bytes changed (0.587 %, a 2×
  margin under A2's 8,192-byte whole-set ceiling), all inside four header-derived spans, all palette
  data — 0 geometry/UV/program/sequence/camera bytes touched, proven by rebuilding W2's rescore and
  W3's retime from their own specs and intersecting the changed-offset sets (both empty). One hue for
  the creature's six pages (+182°, settled by sweep so the shared hide material does not fracture
  across pages) turns Bahamut spectral-mist-green with cold silver-blue plating; the scenery (sky
  dome, aerial ground, fire column, energy rings) recolours independently into a matching deep-teal /
  ghost-blue key, licensed by A2's proof the creature and scenery share no page, no CLUT, not one VRAM
  halfword. `scenery.cloud_bands` is measured pure greyscale (S=0.00) and reports 0 changed bytes,
  declared ON anyway so the gap is stated rather than hidden. STP population, the 234 transparent
  entries and every `0x0000` cutout held identical stock-vs-patched on all 13 palettes; a B3 finding
  (a channel-clamp counter that could never fire) was fixed into a real HSV blow-out gate, worst
  target 4.7 % against its 10 % refusal ceiling, artifact bit-identical before/after the fix. Lever #2
  (texel repaint) is explicitly DEFERRED — A2's dual-depth VRAM pack and time-shared upload columns are
  named repaint hazards a palette edit is structurally immune to — and the texanim generalisation gate
  (A1: `ef038`/`ef177`/`ef493-495` carry a nonzero texanim region ef227 does not) does not gate this
  rung but must gate any future one past ef227. Staged under `C:\gd\SCRATCH\summon-format\reskin-w4\`
  (13 previews reviewed offline); the cast protocol is `W4-RESKIN.md` §6, and the rung does not close
  until the cast is judged.
- **W5 — ★ BUILT + DEPLOYED, casts pending** (`W5-GENERALIZE.md`, `retime_derive.py`, `w_survey.py`,
  `w5_gates.py`, `phoenix_reskin.toml`/`phoenix_rescore.toml`/`madeen_reskin.toml`; commit
  `b3ebdbf8`; suite 358/0/1 single-process, gates 5/5·8/8·8/8·8/8·9/9; every headline claim
  adversarially re-derived from bytes). The three levers generalise with named refusals: reskin
  refuses texanim (ef038/177/493-495 creature scope, unconditionally), multi-writer-unless-all-named
  (ef381), dual-depth (ef447), zero-headroom blow-outs; camera refuses undisclosed dynamic ops
  (324/372 effects carry one — ef227 was the outlier); retime's writer refuses unresolved peer-lui
  (THE HALF-PATCH TRAP), non-derivable dividends, and anything failing the N=0 stock-identity gate —
  its READER (`report --corpus`: lock tables + pairing quality + per-boundary derivability, 45/88)
  ships; its writer deliberately stays uncast. NEW LAWS: THE SATURATED-RAMP / TWO-LOBE LAW (hue
  headroom shrinks with creature saturation; the refusal trough sits on the stock hue's complement —
  Phoenix/Rebirth-Flame alone can reach NO cold hue, so ef211 ships GLACIAL FRONTIER scenery-only and
  **Madeen ef251 carries the creature-lever proof**, GLACIAL MADEEN +160°, rho 0.9156). Bench rows
  Stock Phoenix **198** / Stock Madeen **199** on STEINIV's Rune menu (Spark would renumber the live
  Iron Edge 197). Cast protocol = `W5-GENERALIZE.md` §5 (one relaunch, three judgments); the rung
  does not close until the casts are judged.
  **CAST RESULTS so far (2026-07-26): Madeen ★ PROVEN ("madeen looked glacial") — the CREATURE
  lever generalises in-game, second witness after ef227. Phoenix cast A read STOCK — the scenery
  recolor did not visibly land, the first-ever cast of a PURE id-0-palette recolor (W4's ef227 cast
  bundled creature+scenery, so the scenery half was never proven in isolation and is now also in
  question). Offline discriminators run: the 5 so-bound cells were exactly the recolored ones; ef211's
  program does NO VRAM re-upload (one StoreImage = a read; 0 LoadImage/MoveImage; ef227/ef251 have
  none); one bound model has neutral (128,128,128) prim colors. THE MAGENTA PROBE is LIVE on ef211
  (sha f625ea32…, all 315 live entries of the five bound palettes → pure magenta, STP/cutouts
  preserved; `reskin-w5/ef211/probe-magenta/`): any magenta in the next Stock Phoenix cast ⇒ upload
  path works, the glacial key was perceptually swamped (prim modulation — L17 was only ever proven
  for the CREATURE path); still stock ⇒ the id-0 scenery-palette path is DEAD at runtime — a
  structural finding that re-opens W4's scenery attribution. Cast B (camera) deliberately held
  until this resolves.**
  **PROBE VERDICT ("magenta showed up in the flames") — THE UPLOAD PATH IS LIVE.** The id-0
  scenery-palette path works at runtime (W4's ef227 scenery mechanism re-grounded); cast A's miss
  was COMPOSITIONAL — the v1 key was blue-leaning AND desaturated (×0.85) into additive compositing
  where stock flame cores wash to white. **THE ADDITIVE-COMPOSITING COROLLARY: for VFX textures the
  in-game read keeps the channel the blend favours — pick hues that keep R on warm effects, and
  never LOWER saturation on an already-max-sat ramp (v2's ×1.25 attempt clipped 100% of entries and
  the blow-out gate refused — stock fire IS max-sat; the lawful punch is hue at sat 1.0).**
  GLACIAL v2 deployed (hue_to 280, saturation 1.00 on the two vivid bound cells; container sha
  4daab8ad…); combined-v2 (reskin+rescore, 17b6dcb6…) staged for cast B. Recast pending.
