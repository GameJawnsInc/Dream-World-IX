# The tutorial curriculum — the re-envisioned set

**Status: DRAFT for owner reaction — nothing rewritten yet.** Owner direction (2026-07-31): not a
page-by-page rewrite; break the set into TYPES — GUI-first initial tutorials (most users; note
upfront that most functions route to the CLI), then sections going deeper and covering the CLI;
tutorials must guide the player through the feature space build-on-your-knowledge style, never
"each function in a vacuum" (the reference owns that); vacuum-style is allowed only after the
basics are mastered. Sibling of TUTORIAL-SYSTEM.md (the format + gates); this file owns WHAT the
tutorials are.

## Principles

1. **GUI-first spine.** The entry track lives in the Workspace. One orientation note up front:
   the Workspace is a front-end over the same engine as the CLI — the Output console shows the
   verbs it runs, and every skill learned here has a terminal twin (Track C).
2. **ONE CONTINUING BUILD.** The spine grows a single small mod across all its steps — two rooms,
   a resident, a story bit, a fight, a shippable folder. "Build on your knowledge" is literal:
   each step extends the artifact the reader already has, so features arrive with a reason.
3. **A win every step, in the game.** Every spine step ends with something visible in FF9 and
   says exactly what the reader should see. Offline checks (lint, Problems) come first and are
   named as offline — offline ≠ in-game proof.
4. **Introduce, don't enumerate.** A step teaches the smallest slice of a feature that reaches
   its win, then links the reference/per-block page for the rest. If a sentence explains a knob
   the step doesn't use, it belongs in the reference.
5. **Tracks after the spine.** Deeper feature ladders, the CLI track, and standalone how-tos are
   separate shelves, each stating its prerequisites as frontmatter chips.
6. **Checkpointed starts.** Every spine step opens by naming its starting state and the fastest
   way to mint it without the prior steps. Fork-based checkpoints can NEVER be committed files
   (a fork carries Square-Enix bytes) — a checkpoint for a fork step is a one-action recipe
   ("fork room X, name it Y"), not a download.

## The tracks

### Track S — the spine ("Your first mod", GUI, ~7 steps)

| # | Working title | The win (in-game) | Introduces | Surfaces |
|---|---|---|---|---|
| S1 | Stand in the game | Walk a field that is YOURS, under your own id | Home checklist · fork (Suggest a test room) · deploy (test slot / in-place) · ~ reload | Home, Assets▸Import, Ship▸Build |
| S2 | Someone lives here | Talk to an NPC you wrote | Editor forms · NPC + dialogue + wrap preview · the one-change-per-test loop | Editor, Problems |
| S3 | A door of your own | Walk between two of your rooms and back | second fork · gateways both ways · arrival spots + facing | Editor, Map |
| S4 | The world remembers | A chest opens ONCE; an NPC appears only after it | events · flags (GLOB vs per-visit, the safe band) · gated dialogue · choices | Editor, State |
| S5 | Lights, camera | An entry cutscene plays over your own music pick | cutscene steps (one conductor) · music swap | Editor |
| S6 | Danger | Win a battle triggered in your field | encounter zones + freq · battle scene pick (cards) · after-battle reentry | Editor, Battle |
| S7 | Ship it | A friend-installable zip; New Game lands in your mod | campaign assembly · New Game entry · Build only + Package | Map, Ship▸Build |

Spine boundary = "the basics mastered": the reader has run the full author→deploy→verify loop
seven times and touched every core surface once.

### Track B — going deeper (guided ladders, pick any after S)

- **B-World** — a custom overworld: the World atlas → an island → interior relief → the entrance.
- **B-Click** — author from a picture: Trace → Place → Floorplan (the click-authoring lane).
- **B-Life** — behavior: the archetype wizard → the stage + simulator → a [siege] minigame.
- **B-People** — models & characters: walk-as/swap → import a model → a new playable character.
- **B-Battle** — tuning → custom battle backgrounds → summon reskin/transplant.
- **B-Faithful** — fork FF9 itself: the engine bundle, verbatim depth, a journey of real arcs
  (the current 07's territory, re-verified during its rewrite).
- **B-Coop** — two players in one field.

### Track C — the CLI (the same competence, terminal-native)

- C1: the CLI in twenty minutes — doctor → fork → lint → deploy → ~ (mirrors S1–S2).
- C2: `field.toml` by hand — what the forms were writing all along.
- C3: automation — `tools/deploy_field.py --id`, revert, id bands, batch work, worktrees.
- C4: the bridge — GUI action ↔ CLI verb, anchored by the Output console.

### Track D — standalone how-tos (vacuum-style, explicitly post-spine)

The current 09–14 class (battle background, custom model, creature from scratch, summon work)
plus future one-offs. Each opens with a prereq chip row ("assumes Track S"). Vacuum style is
CORRECT here — these are recipes for people who know the loop.

## Migration map (current 01–14 → new homes)

01 first-fork → C1 · 02 dev-loop → C1/C3 · 03 original-art → B-Click (+D) · 04 campaign → S7/C3 ·
05 journey → B-Faithful · 06 gui-field → SPLIT into S1+S2 (its figures carry) · 07 gui-journey →
B-Faithful (flow re-verified there) · 08 dialogue-cutscene → SPLIT into S4+S5 · 09 battle-bg → D ·
10/11/12 models → B-People/D · 14 summon-reskin → D. Old filenames keep redirect stubs (the
FORKING_FF9 precedent — links in the wild never break).

## System support this needs (small, TUTORIAL-SYSTEM.md owns the details once built)

- Frontmatter grows `track = "S"`, `step = 2`, `builds_on = ["s1-stand-in-the-game"]`.
- A GENERATED Tutorials landing renders the tracks as ladders from frontmatter (replaces the
  hand-kept tutorials/README on the site; the deferred index, now justified).
- The template gains the checkpoint block ("Starting from: …; to mint it fresh: …").
- Everything else already exists: figures per step (shots), label declarations (inventory),
  command gates, requirement chips.

## Authoring order (ratified "go for it")

★ **S1–S7 ALL DRAFTED** (same session), every step figure-illustrated from pinned surfaces
(gateway/chest/cutscene form states added to gui_snap en route) and gate-green; the form
screenshots corrected draft labels at S3/S4/S5/S6 before commit. **⚠ PLAYTEST PENDING** — the
in-game claims (gateway walk-through, chest latch across saves, encounter return, New Game
landing) come from the verified reference, not a fresh run; one hedged micro-step (S7's
campaign add-field menu action) is menu-territory the inventory cannot verify. Owner: run the
spine start to finish and every misfire becomes a one-line fix.
Next: C1 (extraction from current 01/02), the generated track-ladder landing, B ladders by
interest, D migrations (moves + prereq chips), 06/08's remaining content absorption.
