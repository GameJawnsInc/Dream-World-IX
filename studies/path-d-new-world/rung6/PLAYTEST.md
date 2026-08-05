# Rung 6 playtest — the 9013 round trip (deployed 2026-08-05, awaiting owner)

**What's live:** bench field **30950 (PATHDGATE)** in `FF9CustomMap` with a gateway that warps
into world **9013**, and a Confirm-gated exit trigger on 9013's south shore that warps back to
the bench. The two halves are surface-disjoint (the exit splice adds one new object-0 func +
14 armed tiles; it cannot affect arrival), so one session can test both in sequence and still
attribute a failure cleanly. Backups: `C:\gd\Dream-World-IX\backups\rung6-pathdgate\` (bench
`.eb`) and `backups\rung6-worldside-20260805-*` (WORLD13 `.eb` ×7 + `Block[6][8] Terrain`).

**RELAUNCH FIRST** — the bench id 30950 (FieldScene + MessageFile) registers at launch.
The world-side changes are content-only and need no relaunch.

## Stage 1 — ENTRY (bench → 9013)

1. Launch, load any on-foot save. `~ → Go → Warp to field → 30950`.
   Expect: a small checkerboard room; a teleport pad + balloon landmark toward the
   front (bottom of screen).
2. Walk forward (toward the camera) onto the landmarked strip.
   Expect: movement locks → fade to black (~1s) → the overworld loads as **World Map: 9013**,
   standing on the **V-shore bench island lawn** at ~**(425, −479)** facing south-east,
   on foot, camera following. (`~` Position readout should show roughly that pair.)
3. Walk a few steps to confirm control + collision behave.

**Report for stage 1:** did the fade→world load happen; where did you land (Position pair
if it looks wrong); control OK?

## Stage 2 — EXIT (9013 → bench)

4. From the landing spot walk the **EAST lawn band** south (the massif blocks the straight
   line — go east around it): roughly (433,−489) → (447,−509) → (446,−529) → (440,−539) →
   (430,−549) → **(424,−553)**, ~80u total. This route was walk-sim verified offline.
5. Near the south shore at ~(424,−553) a **"!" bubble** appears while you stand on the armed
   patch. Press **Confirm** while it shows.
   Expect: fade to black → bench room 30950 loads, player standing **near the back of the
   room** (the return arrival spot, distinct from the default spawn).
6. `~ → Flags`: ScenarioCounter and story flags unchanged; gil/party intact.

**Report for stage 2:** did "!" show; did Confirm warp back; landing spot in the bench;
flags/gil intact?

## Known / expected oddities (don't burn time on these)

- **9013 inherits stock WORLD11 behavior** (the dispatcher is a verbatim clone): a handful of
  stock objects float at Mist-Continent coordinates ~(1163..1252, −760..−848) — several
  hundred units east of the island, over open sea; encounters CAN fire on topo-36/37 tiles
  (the bench lawn is topo 0, so the lawn itself should be encounter-free); weather drives
  itself; no mist (s75 default).
- **Disc9 carries other sessions' experiments** (clusters at blocks (0-3,4-5), (0-4,16-19),
  (18-21,17-18), (19-20,0), (10-15,12-15) — several rewritten 2026-08-04). Distant land you
  didn't expect is theirs, not this rung's.
- **If the "!" never appears**: the trigger's gate is `Map.Byte[24]==100 && on-foot` — the
  documented Byte[24] coupling is the first suspect; say so and stop there.
- Standard overworld discipline: don't SAVE while standing on 9013 unless you must (the lawn
  is census-clean, but a field save is the safe save).

## Escapes

- Stuck on 9013: `~ → Go → Warp to field → 30950` (or any real field).
- Full revert: `py tools/scroll_out/revert_deploy_30950.py` (bench) + restore the
  `rung6-worldside-*` backups per `studies/path-d-new-world/rung6/worldside/README.md`.
