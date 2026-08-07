# Tutorial system critique (multi-lens pass)

This critique came from three independent reviews (instructional design, user stories/personas, and
kit-context coverage) run against the current core track (S1-S7) and CLI track (C1-C4), synthesized
and ranked.

## Summary

The core GUI track (S1-S3) and the CLI track (C1-C4) are the strongest parts of this system: real
in-game verification steps, a generated CLI reference that can't drift from the code, and a build that
fails on a broken link. That machinery works. The damage is concentrated in two places: the back half
of the core track (S4-S7), and the moment the track hands the reader off to "what's next."

Three independent reviewers converged, from different angles, on the same fact: S4, S5, S6, and S7
quietly drop the "Starting from: ... To recreate it: <clicks>" recipe that S2 and S3 establish,
replacing it with a bare parenthetical hedge ("any deployed fork works"). That is a real,
triple-corroborated defect, not lens noise, and it directly violates the curriculum's own checkpoint
principle for exactly the steps furthest from S1. Compounding it, S7's closing paragraph makes two
claims that don't survive a grep: "each core mechanism of the toolkit used once" (no `[[savepoint]]`,
no `[[prop]]`, no `[[choice]]` anywhere in S1-S7) and a "Going deeper" pointer to six named tracks where
five have no page to land on. I verified this directly — `07-gui-journey.md` is the only hyperlink in
that sentence. A brand-new reader's very last moment with the core track is two overclaims and a wall
of dead promises.

The single biggest risk to the system as designed is that its own rhetoric ("one continuing build,"
"each core mechanism," "pick a track") is now ahead of its content, at precisely the two trust-critical
moments — mid-track checkpoints and the final call-to-action — where a stuck or skeptical reader
decides whether to keep trusting the docs. Layered on top: the two most heavily-invested engineering
pillars per the project's own milestone record (custom overworld, playable characters) have no
tutorial at all, while a narrow cosmetic feature (tutorial 14, summon reskin) is the longest tutorial
in the set — a visible mismatch between authoring effort and actual project value that a
feature-chasing reader will notice within one page load of the front door.

Fastest high-leverage next move: ship the twelve quick fixes below first — they're all verified against
the actual file contents (I read every file cited), cost nothing structurally, and immediately kill the
worst credibility problems: the C3 debug-menu tab description is flatly wrong against the project's own
CLAUDE.md glossary and should never have shipped as-is; the nav.toml sidebar ordering bug (verified
against build.py's `sorted()` glob expansion at line 607) buries the "start here" track at the bottom
of 24 rows for anyone browsing the hosted site; and the S7 wording fixes remove three false claims for
the cost of a sentence each. Once those land, the first structural item to actually schedule is the
S4-S7 checkpoint-recipe rewrite, since it's the most corroborated finding across all three lenses and
blocks the curriculum's own stated design principle.

## Landed after this critique: the instrument gap none of the three lenses saw

The lenses reviewed prose, so none of them checked what the gates actually COVER. The
`[[tutorial.ui]]` gate — the mechanism that makes a renamed control fail the build — turned out to
gate three labels in S1 and nothing else: its inventory harvested tabs and dialogs, but not the
Editor's forms, which is where the core track's prose lives.

Closed (`0c60c7c2`, `80bd8e8e`, `42b7b5f7`, `0ae21367`, `9aedf59f`, `845adc9a`):

- `uiharvest.harvest_forms()` reads `editor/forms.py`'s `<THING>_SPEC` globals directly — plain
  data, no Qt — so all 19 form surfaces / 122 fields entered the inventory, and a spec added later
  is picked up mechanically. Declarations are precise to one field: `form:npc.requires_flag`.
- S2-S6 now declare 26 form labels. Writing them caught four label drifts the screenshots had not:
  prose said "Position", "Zone", "Song id" where the real labels are "Position (x, z)",
  "Zone (x z; x z; ...)", "Field BGM song id".
- A staleness blind spot was found by adversarial check and closed: the gate proved
  tutorial → inventory, but nothing proved inventory → live code, so renaming a label without
  re-harvesting left every gate green. `test_form_inventory_is_fresh_against_the_live_specs`
  re-harvests and diffs. The Qt-harvested `tab:`/`dlg:` halves cannot be closed this way and remain
  a `uiharvest --check` chore.

~~Still ungated: S7 and all of Track C declare zero labels.~~ CLOSED: S7 declares its four
inventory-backed Build-tab controls (Point New Game here / Revert New Game / the campaign
Build-only radio / Package (zip)…), C4 declares Import field + Point New Game here, and
S4/S5/S6's recreate-recipes declare the Import-tab buttons they name. Not declarable (exact-match
gate): the dynamic-suffix radios ("Test slot 4003"), menu items (New Campaign… — menus are not
harvested; the dlg-adapter gap), and the editor's Check button (no attr path in the inventory).
C1/C2/C3 name no harvestable controls — nothing to declare.

## Structural findings, ranked

### 1. S4-S7 need real checkpoint recipes, and the continuing-build vs. cold-start tension needs one clarifying sentence — DONE

Applied: S4 states the real minimal dependency (one deployed room) with a full recreate recipe
plus the side-build caution ("S7 packages the *connected pair*; a fresh room made just for one
step is a side build"); S5 and S6 carry the one-room recipe and reference S4's caution; S7 spells
out the true pair dependency ("fork two vetted rooms, each under its own id, wire a gateway
pair"). Minimal deps were confirmed against the tutorials' own content: S4's chest/flag/NPC-gate
and S5's cutscene/music and S6's encounter touch no gateway; S7's Map-tab connections and the
campaign's reachability labeling genuinely need the pair.

Triple-corroborated (two design-lens findings plus the user-story returning-user persona) on the same
underlying defect: S2 and S3 give an explicit "To recreate it: <clicks>" sentence; S4, S5, S6, and S7
replace it with a bare parenthetical hedge ("any deployed fork works", "any room of the S3/S4 pair",
"the two connected, deployed rooms (S3 onward)"). This breaks the curriculum's own Principle 6 for
exactly the steps furthest from S1, and it also means the reader is never told that taking a
checkpoint's fast-mint shortcut produces a side build, not the unified mod S7 claims to describe at the
end.

**Recommendation:** Author an explicit "To recreate it" sentence for S4 (a single deployed room
suffices — a gateway isn't required for a chest+flag), S5 (same), S6 (same), and S7 (needs the actual
S3 gateway pair, so spell out "fork twice, wire one gateway pair"). This requires confirming each
step's real minimal dependency against the toolkit, not just copying a template, and deciding
how/where to state the continuing-build-vs-cold-start distinction — both are owner judgment calls, not
mechanical edits.

### 2. Track C's depth stops at S1-S2 parity with no disclosed boundary or in-game verification steps — DONE (disclosure option)

Applied the disclose-the-boundary option, not new C5-C7 content: C1 states up front that S1-S2
is where Track C's step-by-step depth deliberately stops and routes feature depth to C2 §3 +
FORMAT.md + S3-S6; C2 §3 now frames its compact TOML as a reference specimen, not a walked
exercise. C3 gained a Starting-from line and a concrete revert verification walk (deploy → edit →
redeploy → revert → reload → the previous deploy returns); C4 gained a Starting-from line and the
Check-vs-`ff9mapkit lint` round trip with a same-findings "what you should see". Authoring
C5-C7-style walkthroughs remains open as a conscious content decision.

C1 states its own scope as "the core-track competence... fork a room, add an NPC, deploy, reload" —
S1-S2 parity only. C2's section 3 shows gateways/flags/cutscene/encounter/music as one static, unwalked
TOML block with no per-feature deploy-and-verify step, unlike S3-S6 which each get a dedicated tutorial
with an in-game check. Separately, C3 and C4 never state an observable "what you should see" outcome or
a "Starting from" checkpoint, breaking the house contract every S-step and C1/C2 follow.

**Recommendation:** Either author C5-C7 style walkthroughs mirroring S3-S7's gateway/flag/cutscene/
encounter depth in the terminal (a genuine new-content decision), or explicitly disclose in C1/C2 that
Track C's step-by-step depth stops at S1-S2 parity and point the reader at C2's reference block +
FORMAT.md for the rest — and separately add a concrete verification step to C3 (revert a deploy,
confirm the prior field returns) and C4 (run one GUI action, find it in Output, run the printed CLI
equivalent, confirm the same result).

### 3. Overworld authoring has zero tutorial despite being the largest area of recorded project investment

CLAUDE.md §10 records the Southern Ring as board-closed (R1-R5 playtest-confirmed), the
two-ground-landmass generator as done, and Path D at rungs 0-5a in-game proven — the single biggest
cluster of milestone effort in the project. Despite this, there is no tutorial anywhere; the only
pointer is the dense reference doc OVERWORLD_ENGINE.md, and CURRICULUM.md's Track B lists "B-World" as
one flat, undrafted bullet among seven co-equal, unordered ladders with no signal it disproportionately
outweighs the others.

**Recommendation:** Write at least a minimal Track-D-style walkthrough for one overworld recipe (e.g.
the coast-mosaic "mint a beach" path) ahead of the full B-World ladder, and sequence CURRICULUM.md's
Track B so B-World drafts first rather than leaving it equally weighted with undrafted ladders like
B-Faithful or B-Coop.

### 4. Playable characters — a headline pillar — have no real tutorial while a narrow cosmetic feature is the longest one in the set — DONE

Applied: `15-playable-character.md` (Track D) — a walkthrough anchored on the in-game-proven
`examples/thirteenth-character/` proof field: the one-block define+recruit, the
deploy→relaunch→New-Game order, the three proofs (appears/fights/saves), both standing caveats
(rename screen, leader-only field render), and going-further pointers (custom battle
model/anims via `playable-anims`, portrait, `[playable.abilities]`). Wired into the tutorials
README (row 15, pillar-gap entry removed), S7's "Going deeper", and the front-door task table.
All prose grounded in the example's README/toml + FORMAT.md's `[[playable]]` section — no new
claims beyond what is recorded as in-game proven.

Custom playable characters ("a 13th/14th CharacterId, zero DLL," rated ★★★ in project memory) is named
second in CLAUDE.md §1's pillar list. It has no tutorial — only a plain-text example README that
(before the quick-fix above) wasn't even linked from the docs. Meanwhile tutorial 14 (recolouring a
stock summon's palette/camera) is the single longest, most heavily-authored tutorial in the whole set
(~420 lines) for a comparatively narrow cosmetic feature.

**Recommendation:** Draft a playable-character walkthrough (Track B-People, or promoted ahead of
further summon-cosmetics polish) so a headline, high-difficulty pillar isn't the only one of
CLAUDE.md's five named pillars with zero walkthrough — this requires new authored content and a
conscious re-prioritization decision, not a link fix.

### 5. S5 bundles two unrelated mechanisms into one step

Every other core-track step teaches one mechanism (S3 gateways, S4 flags, S6 encounters). S5 teaches
both the cutscene scripting language (ordered steps, once-flag, cast) and field music/BGM swap — two
independent features with no dependency on each other. CURRICULUM.md's own table reflects this: S5 is
the only row whose "Introduces" column joins two unrelated bullets with a middle dot rather than
describing one coherent progression.

**Recommendation:** Split S5 into two thinner steps matching sibling size, or add one explicit sentence
at the top justifying the pairing (e.g. "both are one-time atmosphere setup") so the bundling reads as
a deliberate design choice rather than a merge of convenience. Either path requires an
authoring/restructuring decision, not a text edit.

### 6. Two parallel, overlapping tutorial-numbering schemes still coexist beyond the one fixed row

01-first-fork.md, 02-dev-loop.md, 04-campaign.md, 06-gui-field.md, and 08-dialogue-cutscene.md (legacy
numbered) still sit alongside s1-s7/c1-c4 (new tracks) covering overlapping ground, each producing a
materially different resulting project state for the "same" nominal task. The quick fix above only
adds a superseded-by note to 01; 03/04/05/07/08 still have no such note, and a returning user has no
reliable way to tell, from memory alone, which scheme they previously followed.

**Recommendation:** Decide and execute the actual retirement/redirect plan for the full legacy 01-14 set
(which get "Moved" stubs like 02/06 already did, which get superseded-by banners like 01's quick fix,
and which stay fully live as Track D content) — this is a scope decision affecting many files, not a
single mechanical edit.

### 7. No GUI path exists for model import-back or from-scratch creature minting

Tutorial 10's "Import back" step and all of Tutorial 12 (`py ff9mapkit/examples/boletta/make_creature.py`)
are CLI/Python-only, with no Workspace form for model-import/mint. A GUI-committed reader who follows
S7's pointer into "models and characters" hits a hard wall at the exact step that ships the edited
model.

**Recommendation:** Either build a Workspace path for model-import/mint (real feature work), or make an
explicit scope decision to keep Track D CLI-only and state that plainly up front in both tutorials so a
GUI-committed reader knows not to invest time before finding out. Either option is a judgment call, not
a mechanical doc fix.

### 8. Several proven pillars (MOGNET, behavior-tree/Fort Condor, chocobo, folklore codex, vehicles, Tetra Master) have no committed authoring slot

The quick fix above adds these to the "gap list" so the omission is at least disclosed, but nothing
currently commits to actually writing any of them — Track D's membership (09/10/11/12/14) reflects
which old tutorials happened to exist pre-revamp, not a value-ranked selection against CLAUDE.md §10's
milestone list. Track B's "future one-offs" catch-all doesn't name any of them either.

**Recommendation:** When populating Track D's "future one-offs" or Track B's ladders, explicitly audit
against CLAUDE.md §10's milestone list (not just the pre-existing 09-14 set) and assign each
mature-but-uncovered pillar a named, owned slot — a priority/sequencing decision for the curriculum
owner, not a text correction.

## Quick fixes applied this pass

- `ff9mapkit/docs/tutorials/c3-deploy-automation.md` — described the debug menu as "four
  context-adaptive tabs — Go / Cheats / Flags / Time" and omitted the overworld's World tab entirely;
  CLAUDE.md's own glossary states "Go/Cheats/Flags; Time is inside Cheats," and project memory records
  a World tab (teleport/vehicle swap/disc switch) on the overworld — a factual error against the
  project's own canonical brief.
- `docsite/nav.toml` — the Tutorials section's page list was just `ff9mapkit/docs/tutorials/README.md`
  plus the glob `ff9mapkit/docs/tutorials/*.md`; build.py's `load_nav` (verified at build.py:602-619)
  expands that glob with a plain `sorted()`, so the sidebar showed legacy tutorials 01-14 first, then
  c1-c4, then s1-s7 last — burying the "start here" core track at the bottom of a ~24-row unlabeled
  list.
- `studies/interactive-docs/CURRICULUM.md` — the "Migration map" line stated "08 dialogue-cutscene ->
  SPLIT into S4+S5" as complete, but the same file's later "Authoring order" section (around line
  113-114) said "08's choice/cast-scene content into its track home" is still open — the two sections
  of one file disagreed on whether 08 is fully absorbed.
- `ff9mapkit/docs/tutorials/README.md` — 01-first-fork.md was left as a full live tutorial with no
  signal it's superseded, unlike 02 and 06 which already got "Moved — now C3/S1+S2 above" stub rows in
  the same table, even though CURRICULUM.md's own migration map lists 01 -> C1 in the same breath as 02
  and 06.
- `ff9mapkit/docs/tutorials/README.md` — the "Pillars without a tutorial yet" list omitted battle
  tuning, MOGNET, behavior-tree/Fort Condor authoring, and save points/props, even though each has a
  mature reference doc to point to (BATTLE_DESIGN.md, SAVEPOINT.md, BEHAVIOR.md); the existing
  playable-characters entry was plain backtick text, not a working hyperlink, even though the target
  file (ff9mapkit/examples/thirteenth-character/README.txt) resolves safely under docsite's link
  checker (verified in build.py's `_resolve`: an existing non-page, non-image file is linked directly
  or via GitHub, never flagged as broken).
- `docsite/pages/index.md` — the front-door "Pick a task" table row "Add custom 3D models or a new
  playable character" linked only Tutorial 10 (edits an existing model) and Tutorial 12 (mints a
  from-scratch NPC creature) — neither touches `[[playable]]`, recruiting, or a 13th CharacterId; the
  same table had zero rows for the existing Track-D tutorials 09/11/14 or for overworld/battle-tuning/
  co-op, despite CLAUDE.md naming them as project pillars.
- `ff9mapkit/docs/tutorials/s7-package-a-campaign.md` — the closing "Going deeper" bullet named six
  destinations (worlds, click-authoring, NPC behavior/minigames, models and characters, battle design,
  forking FF9) but hyperlinked only the last one — five of six read as promises with nowhere to click.
- `ff9mapkit/docs/tutorials/s7-package-a-campaign.md` — "each core mechanism of the toolkit used once"
  was inaccurate: S1-S7 never author a `[[savepoint]]`, a `[[prop]]`, or branching `[[choice]]`
  dialogue — all real, named FORMAT.md blocks, and CLAUDE.md §1 names save points explicitly as a
  defining field component. Grep across all s*.md files confirmed zero matches for "choice".
- `ff9mapkit/docs/tutorials/s7-package-a-campaign.md` — section 3 ("Package a zip") told the reader a
  friend can unzip and play with "no toolkit on their machine," but never mentioned that a
  verbatim-forked room's full in-game fidelity (letterbox, some after-battle fixes) requires the Dream
  World IX engine bundle too — grep confirmed zero mentions of "engine bundle" or "ENGINE.md" anywhere
  in s1-s7.
- `ff9mapkit/docs/tutorials/c2-field-toml-by-hand.md` and
  `ff9mapkit/docs/tutorials/c3-deploy-automation.md` — neither file mentioned the reserved 9000-9012 id
  hole (engine world-map dispatchers — a field there black-screens) or the Int16 32767 ceiling, even
  though C3 has the reader mint arbitrary ids ("--id 5000", "a different slot") and C2's id comment
  stated only a lower bound (">= 4000; scratch band 30000+").

## Quick fixes NOT yet applied (deferred, logged not lost)

**Both applied since this was written** — s2-add-an-npc.md carries the "Appears when flag set"
bullet pointing at S4, and s5-cutscene-and-music.md ties "the scratch slot" back to S1's
**Test slot** label. Kept below for the record.

- `ff9mapkit/docs/tutorials/s2-add-an-npc.md` — the NPC-form screenshot caption lists "story-flag
  gates" as visible in the figure, but the four prose bullets below it (Name/Preset/Dialogue/Position)
  never mention or explain that control — yet S4 later writes "the same field visible in the NPC form
  from S2," crediting S2 with teaching something a prose-only reader never saw explained.
  Fix instruction: after the bullet "- **Position** — where it stands. The Inspector on the right shows
  the field art with its walkable bounds; a position outside the mesh gets a lint finding, not a silent
  no-show.", add a new bullet: "- **Appears when flag set** — gates the NPC behind a story flag; leave
  it blank for now — [S4](s4-story-flags.md) uses this control."
- `ff9mapkit/docs/tutorials/s5-cutscene-and-music.md` — S1 names the deploy target by its real UI
  label, "Test slot" (glossed informally as a "scratch id"). S5 later calls it just "the scratch slot"
  without tying the term back to the actual button name the reader saw in S1.
  Fix instruction: replace the phrase "a redeploy starts the field's state fresh in the scratch slot)."
  with "a redeploy starts the field's state fresh in the Test slot — [S1](s1-fork-and-deploy.md)'s name
  for this same scratch id)."
