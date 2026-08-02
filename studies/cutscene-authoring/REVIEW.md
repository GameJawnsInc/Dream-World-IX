# Cutscene lane — adversarial review

**Date:** 2026-08-02 · **Scope:** `content/cutscene.py`, `content/conductor.py`, the cutscene slices of
`build.py`, `workspace/shell.py::_mount_cutscene` (7594-7794), `editor/forms.py` CUTSCENE_SPEC/STEP_KIND,
`editor/app.py::_show_cutscene`, and the docs that describe them.

**Method.** Six parallel review passes with an adversarial refutation pass on each, then **independent
re-verification of every blocker by the reviewing agent** — the fan-out returned 0 refutations of 62
findings, which is a rubber-stamp smell, so the load-bearing claims were reproduced by probe rather than
accepted. Everything marked ★ below was reproduced first-hand; probes in
`scratchpad/probe_cutscene.py`, `test_cs_trap.py`, `test_cs_more.py`.

> **Headline.** The compiler is the strongest part of this lane; the authoring surfaces have not kept up.
> Every blocker is an authoring-surface defect — which is exactly where this lane has **zero tests**.
> No compiler defect here is visible in-game today.

---

## Sprint 1 — SHIPPED (offline; awaits a playtest)

| Item | What landed |
|---|---|
| **A1** ★ | `editor.forms.single_block` — one owner for "which block does a single form edit?", spent by `_commit`, `_commit_active`, `_form_matches_baseline`, `_mount_cutscene`. The deadlock is gone. Cutscene `_save_ctx` gained the `"mounted"` baseline every other form had. |
| **A2** ★ | The tk editor (`ff9mapkit edit`) normalizes block 0 in `_show_cutscene` / `_steps` / `_commit_active`, and shows the same "editing scene #1 of N" banner. |
| **A3** ★ | **Add step** / **Update selected** replace the overloaded *Add / Update*. Add inserts after the selection; Update rewrites in place, kind-agnostic, preserving `speaker`/`tail`/`speed`. **Duplicate** added. |
| **A5** ★ | Inspector + node lint route through `forms.all_blocks`: every scene summarized and linted, cast read from `actors`, warnings prefixed `scene #k`, step actors checked against the cast. |
| **A9** (part) | Step rows numbered 0-based; `_check_walk_leg` warnings carry the dispatch label (`[cutscene] #1 step 3`). |
| **B1** ★ | **"Check the staging"** — new Qt-free `workspace/cutscenescan.py` drives `build._validate_cutscene_movement` off-thread, with a generation counter and the two-truths note. The orphaned mechanism now has a call site. |
| **B2** ★ | **"Runs with the previous beat"** checkbox, gated on `build.PARALLEL_STEP_KINDS` (promoted from a function-local `_par_ok`) and mirrored as `forms.PARALLEL_STEPS`, fenced equal. |
| **B4** ★ | Live wrap preview under the say box, reusing `forms_qt._wrap_preview_panel` and the `_wrap_width` already in scope. |
| **A14** ★ | `tests/test_workspace_cutscene.py` — **35 tests**, the suite this lane never had. Plus 3 dispatch tests in `test_editor_app.py` and a new pinned snap surface `form:cutscene-dispatch`. |

**Found while fixing, NOT fixed** (deliberately out of scope — it changes accepted authoring input):
`_coord_like` lets the Inspector pass a string coordinate (`walk = "100, -800"`), but the build's
`_resolve_point` accepts only a `[x, z]` **list** and errors on the string form. So a hand-authored
string coord reads clean in the Inspector and fails the build. The GUI itself always writes the list
form (`make_step` → `parse_point`), so this only bites hand-edited TOML. Decide whether the build should
accept the string or the Inspector should warn — the fix is one line either way, but it is a product
decision about what input is legal.

**Still open from the plan:** A4, A6, A7, A8, A10-A13, A15-A17, B3, B5-B14.

### Sprint 1 self-review — what the adversarial pass found in the SPRINT ITSELF

An 8-agent review ran over the sprint diff. It found real defects in the new code, several settled by
**mutation** rather than argument. Fixed in-sprint:

| Defect | Why it mattered |
|---|---|
| ★★ **The A1 fence proved nothing.** Reverting BOTH `_single_block` call sites left the whole suite green. Every test mounted the form and committed it **untouched**, exiting at the `"mounted"` fast path *the same sprint added*, never reaching the fixed code. | THE CHECK THAT CANNOT FAIL — committed inside the fence for that very defect class. Tests now dirty the form first (`_dirty_the_form`); mutation-verified to fail 3 tests when A1 is reverted. |
| ★★ **The staging check scored the LOGIC-only doc.** A field using the kit's documented `field.toml`/`scene.toml` split hides its cast in the scene file, so the checker found no actor, walked nothing, and printed "✓ Every walk reaches its target" over a walk `lint` calls a softlock. | A FALSE GREEN in the panel built to prevent one. Now reads `doc.merged()`. |
| ★★ **A skipped scene reported as clean.** `_validate_cutscene_movement` silently `continue`s past a scene whose names don't resolve. One typo'd marker → no warnings → confident all-clear. | Same false-green class. `StagingResult.skipped` + `_unwalkable()` now name what went unchecked. |
| ★ **The staging BUTTON had zero coverage.** Deleting its `clicked.connect` left the suite green — every test called `_cs_stage["run"]` directly. | The call-site law, violated by this sprint's own fence. Now clicked for real; mutation-verified. |
| ★ **`with_prev` armed with nothing selected.** `currentRow() != 0` is True at -1, so an empty scene could write `with_prev` onto step 0 — which `validate()` rejects. | The first fence missed it because every case it drove already had a selection. Now `> 0`. |
| ★ **Scene numbers disagreed between surfaces.** Staging said `#1`, the Inspector said `scene #2`, for the same scene. | Aligned on the build's own 0-based convention. |
| ★ **A crashing worker stranded the button** disabled and reading "Checking…" forever — `paint_staging` is the only re-enable. | `work()` now returns an error result instead of raising. |
| `StagingResult.ok` had no consumer | Deleted (call-site law on the diff itself). |

**Corrected claim.** The review's original B1 justification — *"`_validate_cutscene_movement` is
unreachable from the GUI even in principle"* — is **FALSE**. `_validate_content_placement` is called from
`build_field` (build.py:7759, 7822, 7857), not only from `lint`/`walkmesh verify`, so those warnings
already reach the Workspace through a Build. B1 still earns its place (it runs on the open document
without a full build, and names the scene), but it is a convenience, not the rescue of an orphan.

**Known-remaining in the new code** (reported, not fixed): the staging check reads the committed doc, so
a Cast typed but not yet committed is invisible to it; `single_block` returns a non-dict unchanged
despite its `-> dict` annotation.

### Layer-3 self-review — and two CORRECTIONS to this document

A third adversarial layer ran over the post-layer-2 tree, mutation-testing every fence. Two claims made
above were **wrong** and are corrected here:

1. **"Scene numbering aligned"** — it was NOT. The substitution script that was supposed to make the three
   edits **crashed on a unicode `print` before it ever reached `write_text()`**, so none of them saved,
   while a separate banner edit did — leaving the surfaces *three-way* inconsistent (staging 0-based,
   Inspector 1-based, banner 0-based), worse than before. Textbook
   [[feedback-verify-the-cache-write-lands]]. Now genuinely 0-based everywhere, re-read from disk to
   confirm.
2. **"Undo restored NOTHING"** — overstated. Ctrl-Z *does* restore the scenes to the in-memory buffer;
   it is the FILE that stays truncated, because the delete saves immediately. Still data loss, but
   recoverable if the author notices before closing.

**A4 is now FIXED, not deferred** (it was measured first: 3 scenes → all 3 gone from disk in one click,
behind a confirm that said "this cutscene"). The delete removes only block 0, and the confirm names the
survivors. Three tests pin it.

**Layer 3's headline: seven of the layer-2 fixes were unfenced** — reverting them left the suite
bit-for-bit green. Fences added and **mutation-verified to bite** for: Up/Down direction, Duplicate's
insert position, Duplicate's deep copy, the A4 scope, and the staging controls' accessible names.
Still unfenced and honestly recorded as such: the tk `single_block` call site, the tk row numbering, the
`with_prev > 0` rule, and both halves of the staging generation counter.

⚠ **A concurrent agent session writes this worktree.** During layer 3 the A4 fix was silently reverted by
another session restoring `shell.py` from an older snapshot, and two unrestored mutations were caught
live. Anything verified here must be re-verified before merge.

---

---

## 1. Is multi-cutscene-per-field really supported?

**Yes — you did change it.** Commit `68167b90`, 2026-07-12, *"plural `[[cutscene]]` — the per-field
story-event DISPATCH (#13 v2)"*. `cutscene.blocks()` (cutscene.py:261-271) normalizes singleton and plural
to one list, and `build.py` genuinely loops it three times: txid slicing (5583-5588), one conductor per
cast block (5925-5947), one narration entry per block (5953-5964).

**But it is supported in the compiler and nowhere else.** Note also that this is a *dispatch* — gated so at
most one scene fires per load — not N scenes playing in sequence.

| Surface | State |
|---|---|
| Compiler (novel field) | ✅ N blocks: per-block once-flags, per-block txid slices, shared `_cs_tag_state` so scene 2's actor tags don't collide |
| Docs | ✅ FORMAT.md:1796-1811 documents the dispatch |
| **Workspace form** | ❌ Block **0 only** (shell.py:7598-7616); `cutscene` is in `_SINGLE` (201-202) so there is no Add path. Tree shows a singleton `Cutscene` leaf, not `Cutscenes (N)`. |
| **Workspace, any plural file** | ❌ ★ **Mounting the tab traps the editor** — see §2 |
| **`ff9mapkit edit` (tk)** | ❌ ★ **Hard `AttributeError`** on any `[[cutscene]]` file — including both shipped stolen-ember examples |
| **Delete** | ❌ "Remove cutscene" `pop`s the **entire array** behind a singular confirm and saves immediately (7790-7792 → 7157-7167) |
| **Inspector / node lint** | ❌ Bails on any non-dict (8954-8955), so all per-step checking is skipped for a dispatch; health badge scores 0 |
| **Verbatim fork** | ⚠️ Capped at **one CAST block** (5001-5005); later cast blocks and all narration blocks dropped as lint *warnings* that don't fail the build. Their say lines never reach the `.mes`. |
| **Campaign member** | ⚠️ A 2nd auto-flagged block is a hard `BuildError` from `lint_logic()` — and **the GUI's Check cannot reproduce it**, because every Check path loads the member standalone with no `flag_base` |
| **Dispatch safety** | ⚠️ ★ The "distinct gate" rule is weaker than documented — see below |
| **Tests** | ❌ No test drives a plural dispatch through `build_field`; no workspace test mounts a list |

### ★ The dispatch-safety gap (reproduced)

FORMAT.md:1802 promises *"two scenes that could fire on the same load are a build error."* The rule
(build.py:2657-2669) keys on the **raw gate tuple**, so it tests syntax, not satisfiability:

```
two UNGATED blocks        -> caught, good message
scenario-gated + flag-gated -> NO PROBLEMS   (both can fire)
two different flag bits     -> NO PROBLEMS   (both fire if both bits are set)
```

Two live cast scenes then share one watchdog MAP bit (conductor.py:59), so the first to finish drops the
other's re-lock guard.

---

## 2. Is composition easy?

**No. Two blockers, and one is a hard trap.**

### ★ Blocker A — the Cutscene tab deadlocks the Workspace on any `[[cutscene]]` field

`_commit` normalizes a plural section (7415-7419). `_commit_active` **does not** (7464-7467): `setdefault`
returns the *list*, and 7477 runs `list.pop("actors", None)` → `TypeError: pop expected at most 1
argument, got 2`.

Reproduced on a real `Workspace` window (`test_cs_trap.py`, 5/5 predictions hit, singleton control passes):

- `_commit_active()` raises · `_undo()` raises · `_redo()` raises · `_commit_active_ck()` raises ·
  `_form_matches_baseline()` raises
- `_commit_active_ck` has **8 production call sites** (4798 nav, 5335 undo, 5344 redo, 5453 dirty,
  7033 list-add, 7070 refresh, 7485 Check/`_ensure_saved`, 7506 dirty) — so after mounting Cutscene,
  tree navigation, undo, redo, refresh, Check and Save All all raise out of one line.
- There is no `excepthook` in `apps/ff9_workspace.pyw` or `workspace/`, and the app launches from a
  `.pyw` — the traceback goes nowhere the user can see. It reads as a dead UI.
- The cutscene `_save_ctx` (7788) omits the `"mounted"` baseline every other form carries, so the
  untouched-form fast path at 7453 can never short-circuit past it.

**Both shipped examples trip it** — `examples/stolen-ember/HEARTH` (2 blocks) and `CHAPEL` (1 block, still
an array). Precise trigger: block 0 must carry at least one non-default spec value, which both do.

### ★ Blocker B — two consecutive `say` steps are unauthorable

`add_update` decides update-vs-append from the step **kind alone** (7748), then re-selects the row it just
wrote (7758). On the real widget:

```
start                        [{'say': 'opening'}]
+ "Cid: Well now."        -> [{'say': 'opening'}, {'say': 'Cid: Well now.'}]      (appended)
+ "Cid: That's torn it."  -> [{'say': 'opening'}, {'say': "Cid: That's torn it."}] (OVERWROTE)
+ "Cid: Rubbish!"         -> [{'say': 'opening'}, {'say': 'Cid: Rubbish!'}]        (OVERWROTE)
```

**Three lines of dialogue in, one out.** No confirm, no status line. No mouse gesture clears the
selection — blank-viewport click and Ctrl+click both leave `currentRow()==0`; only **Remove** reaches -1.
Authoring a multi-line conversation through the buttons is impossible.

### Major — a step's kind cannot be edited

Same heuristic, else-branch (7755-7757): select a `wait`, switch the combo to Say, press the button → the
wait is untouched and a stray `say` lands at the end (★ reproduced). The `extras` merge only runs on the
update branch, so a converted parallel beat loses `with_prev` while the original stays put.

### Major — CALL-SITE LAW: nine authoring keys the form cannot write

Step level: `with_prev`, `follow`, `speed`, `speaker`, `tail`. Block level: `requires_flag_clear`,
`set_flags` (used by the shipped HEARTH.field.toml:39), `flag` (**mandatory** for a campaign member's 2nd
block), `owns_control`. CUTSCENE_SPEC is exactly seven fields.

The GUI **renders** `[with prev]` in the step summary (forms.py:872) — visible, unreachable: the worst
discoverability state there is. It does correctly *preserve* all nine across a re-save (7752-7754).

`speaker` is the single most VN-relevant key in the kit and it is TOML-only.

### Major — no author-time validation

`_commit` writes the file and reports `Saved ✓` without calling `validate` or `lint_logic`. The four
structural errors only this tab can introduce (`ate_mode` without `ate`; `with_prev` on step 0; two ungated
blocks; an `actors` name that isn't an `[[npc]]`) surface only if the author thinks to press Check. The
Actor field is a bare `QLineEdit` with no completer, against a cast the form already knows.

### ★ Inert — the one timing dial the form exposes

`warmup` is spent only on conductor.py:362's `elif warmup > 0`, unreachable while `owns_control` is True —
which it always is, since nothing exposes it. Narration never reads the key at all. FORMAT.md never lists
it and says outright the control-grant spin made it unnecessary.

### Minor friction (measured on the live widget)

`SingleSelection`, `NoDragDrop`, `dragEnabled == False`. No insert, no duplicate, no scene copy/paste.
Reorder is ±1 per click and each click mints its own undo record. Rows carry no index while every lint
message addresses steps positionally and 0-based. The say box is `setFixedHeight(64)` — ~3 lines — for
text that legitimately spans multiple `[PAGE]` windows.

---

## 3. Are changes previewable?

**What genuinely exists:** the `animation` step's Browse renders the clip's real frames scoped to that
step's actor's rig (a well-built preview); `ff9mapkit dialogue` prints every line with final on-screen
wrapping; `ff9mapkit lint` reaches the walk-stall checks; `tools/field_layout_probe.py` draws the room.
**Three of those four are CLI-only.**

**What does not:**

- **No wrap preview on the one field where authors type the most text.** The live preview attaches to
  `dialogue`/`message`/`prompt`/`reply` only (forms_qt.py:109); the cutscene say box is hand-rolled outside
  that path — even though `_wrap_width(member)` is already in scope at 7630 and the build overflow-checks
  these very lines.
- **★ The walk-stall warnings are unreachable from the GUI, by construction.**
  `_validate_cutscene_movement` writes exactly the sentence an author needs — *"the actor presses into the
  wall and the scene hangs"* (7093) — but is reached only via `_validate_content_placement`, and
  `grep` for it across `workspace/` and `editor/` returns **nothing**. Mechanism written, correct, spent by
  no GUI call site. Highest value per line in this review.
- **`[[marker]]` — the named points a cutscene walks to — are drawn on no canvas in the app.**
  `placedoc.content_markers` has no `rows("marker", …)`, while MARKER_SPEC's own help says *"reference it
  in a cutscene as `walk = "<name>"`"*. The author types a name for a point the app won't show them.
- **No spatial, temporal, or ordering view of a scene at all.**
- **`dialogue.collect_text_refs`** — whole-field, author-order, already dispatch-aware, docstringed as
  *"the unified list the dialogue editor edits"* — has **zero production call sites**.

---

## 4. Could we add a Simulation like the Behavior tab's?

**Yes — but not a tick sim. Build a beat-indexed storyboard.**

### Why not a clock

`behaviorsim` earns its 30 Hz axis because every behavior action has a frame cost the compiler knows. A
cutscene's dominant step does not: `say` blocks until the player presses. Across every shipped cutscene in
the repo the census is **7 say : 5 walk**. Two further unknowns: walk speed is optional with an unauthored
engine default (opcodes.py:229 says vanilla is ~15; behaviorsim's default is 50, inherited from a
*behavior* constant), and `walk = "@player"` compiles to a live-tracking FOLLOW against a player position
that is nondeterministic by the engine's own entry-grant race.

A scrub bar reading "tick 412 · 13.7 s" over a timeline whose largest segments are fabricated is this
project's own anti-pattern. The honesty ledger can't rescue it, because the caveat would be *"the axis is
wrong."*

The defensible narrower claim: only the **seconds** axis is fabricated. `wait` is frames by definition,
each walk leg is compiler-resolved, `speed` is authorable. A **beat**-indexed scrubber with `say` drawn as
an explicitly unbounded "waits for the player" segment is precluded by nothing.

### The design — three files, ~1000 LOC

- **`workspace/cutscenescan.py`** (Qt-free, ~250) — `beats(raw)` and `storyboard(raw, wmesh)`, chaining the
  compiler's own resolution (`_resolve_conductor_steps`, `_resolve_move_steps`, `_autoroute_steps`,
  `_position_registry`, `_resolve_point`) rather than re-guessing it, plus `conductor.group_parallel` for
  parallel bands and `_check_walk_leg` for verdicts.
- **`workspace/cutscenedoc.py`** (~500) — beat rail (one row per block, all N), step ladder reusing
  `LadderView`'s row grammar, `StageCanvas` fed per beat through its existing
  `set_sim({"units": …, "player": …})` shape (a storyboard beat *is* that dict), a scrub slider indexed by
  **step**, notes ledger on the pane's face.
- **Wiring** (~40 LOC, mirroring `behavior_doc`) + `tests/test_workspace_cutscene.py` (~200).

### Reuse map

| Need | Already exists |
|---|---|
| Block normalization | `cutscene.blocks` 261-271 |
| Beat resolution | `build._scene_beat` 4181-4190 |
| Compiler-identical step resolution | build.py 6823, 6861, 6878, 6904-6950, 7036-7071 |
| Parallel grouping | `conductor.group_parallel` 155-166 |
| The chart | `StageCanvas` behaviordoc.py:48, `set_sim` :194-229, `set_verdicts` :177 |
| Art-backed alternative | `BackdropCanvas.set_markers` backdrop.py:275 |
| Off-thread worker + generation counter | `BehaviorDoc.sweep_now` :2104-2143 |
| Walkmesh load | `behaviorscan.load_walkmesh` :1072-1081 |
| Real animation frames | `ClipPlayer` over `AnimFrameService` |
| Honesty ledger idiom | `Sim.notes` behaviorsim.py:176-193 |

### Honest limits — put these on the pane, not in a docstring

1. Walks are the compiler's routed polyline, not the engine's smooth path.
2. An actor with no `speed =` moves at an unknown default — show no duration.
3. `say` blocks on the player. That is why there is no time axis.
4. `@player` resolves against `[player] spawn`; the real player stands wherever they walked.
5. `animation` shows the clip, not the on-stage pose.
6. Which scene fires depends on the live ScenarioCounter.
7. `then_warp` ends the scene off this field.

### Two costs the "it's all already written" framing hides

`_resolve_conductor_steps` and `_autoroute_steps` both **take a walkmesh** — a disk read that must go
off-thread (precisely why the Behavior lane needed its own loader). And `_resolve_point` **raises
`ValueError`** on any unresolved name, so a storyboard over a half-typed scene needs an error lane the
behavior sim never needed.

**The storyboard is not the fix for `[[cutscene]]` blindness.** That is a few lines routing 8730 / 8819 /
9097-9099 through `blocks()`. Do the cheap fix first.

---

## 5. Could the Cutscene tab be invaluable for visual-novel authoring?

It could. The `.eb` layer already does most of what a VN needs. Three things are missing.

### The one structural gap: no in-scene branch

The step vocabulary is closed at nine kinds in all four enforcement points, with no branch. Nothing but
field load can arm a cutscene entry. No `[[choice]]`/`[[event]]`/ATE row can call one. A region can't fire
under the control lock. **So the only shipped branch is choice → warp, or `then_warp` into a
differently-gated scene on a field reload.** A 40-line confrontation with three reply points becomes four
field entries.

**This is buildable.** `choice.switch_body` is the block; its sibling's docstring already says it is
"usable in ANY trigger context", and `numinput.call_bytes` is the shipped precedent for dispatching a modal
from inside another body. Two grounded hazards: the `DISABLE_MOVE … ENABLE_MOVE` bracket must be stripped
for the inline form (narration has no watchdog to re-lock), and the nested-window sysvar-9 law forbids
`branch()` here — use `switch_on_choice`/`op_0B`, or latch the pick into a flag.

### The craft controls — all one-liners against existing encoders

No fade, music, SFX, camera, show/hide or give-item **step**, while every encoder exists and is spent by
non-cutscene code: `fade_filter` (cutscene.py:110 already composes it), `run_sound_code`,
`set_field_camera`, `add_item`/`add_gil`, `window_async`, `stop_current_music_bytes`. Unhelpered but
tabled: `0x39/0x3A` Show/HideObject, `0x6F/0x70` Move/ReleaseCamera, `0xD8` SetWeather.

Music is **entry-only**, so a 40-line confrontation plays under one unchanging track start to finish.
*"The elder walks up, says his line, and hands you the key"* — the most common story beat there is —
cannot be one cutscene. And the workaround for "this character leaves" is `teleport` off-mesh, which is
**never** walkmesh-checked — accepted silently, fails in-game.

Hard-wired where a parameter already exists: `actor_animation(anim, hold=…)` — **no call site passes one**,
so every gesture in every cutscene holds exactly 40 frames. Same for `actor_face(..., speed=16)`, while the
three sibling movement bodies immediately above it all forward `s.get("speed")`.

No timed / auto-advance line, though `[TIME=n]`, `[SPED=n]` and `[IMME]` are all emitted by the kit and
documented exactly once, for savepoint act text. **Pacing is the VN craft**; every beat currently reads at
one rhythm.

### The reading surface

`collect_text_refs` is the exact mechanism a VN script pane needs — and it **drops `speaker_path`/
`tail_path` for cutscene steps specifically**, where npc/event/choice-prompt/on_entry refs all carry both.
Wiring it today would render every cutscene line unattributed.

### Expectation to pre-empt

**FF9 has no dialogue portrait and no name box.** Attribution is the tail pointer plus a name line written
into the text. The kit's only `portrait` is the NGUI menu/battle avatar; the only portrait-beside-text
precedent is the Folklore codex screen, gated on the s45/s46 engine patches. A **cast** scene gets
engine-native attribution from the Actor box (`window_sync_ex`); a **narration** scene gets none, because
`compile_steps` ignores `actor` entirely — so a castless 40-line scene ships with no name lines and the
default UPR tail.

**Verdict:** one branch step, five cue steps, three widgets and a script pane away from a genuinely good VN
surface. None of it speculative — every piece is an existing encoder or an existing unspent function.

---

## Ranked improvement plan

**S** ≈ hours · **M** ≈ a day · **L** ≈ a few days · **XL** ≈ a week+

### A. Fix the sharp edges (defects — several are data-loss or dead-app)

| # | Item | Size |
|---|---|---|
| A1 | ★ Extract `_commit`'s plural normalization into one `_single_target(doc, section)` helper; call it from `_commit:7415`, `_commit_active:7467`, `_form_matches_baseline:4590`. Add `"mounted"` to the cutscene `_save_ctx`. **Unblocks the editor on every `[[cutscene]]` field.** | S |
| A2 | ★ Normalize block 0 in the tk editor the way shell.py does. Fence with a test that opens HEARTH.field.toml. | S |
| A3 | ★ Split "Add / Update" into **Add step** (always append after the current row) and **Update selected** (always write `st[r]`, kind-agnostic, keeping the extras merge). Fixes both the overwrite and the type-change append. | M |
| A4 | Scope or relabel the delete — never a singular label on a plural delete. | S |
| A5 | Route Inspector + node lint through `cutscene.blocks()` and read `actors` (it still reads the removed singular `actor`). Prefix per-step warnings with `scene #k`. | S |
| A6 | ★ Decide `warmup`: spend it or delete it from CUTSCENE_SPEC + both parse sites. Add a range check either way (`warmup = 300` currently escapes as a raw `ValueError` from `opcodes.wait`). | S |
| A7 | Sweep the stale flag bands — nine live doc sites say 9200; the code says 14704. `GLOBAL_RESOURCES.md:76` names the symbol beside the wrong value, and it is the page an author consults to hand-pick the `flag = N` a campaign member's 2nd block *requires*. Add a freshness gate. | S |
| A8 | ★ Correct FORMAT.md's dispatch guarantee to what the rule enforces; add the verbatim one-cast-scene cap to the same paragraph. | S |
| A9 | Number the step rows 0-based (matching `enumerate` exactly); thread block index + actor into the warning producers; grow the say box past 64 px. | S |
| A10 | ★ Fix the dispatch rule: normalize `requires_scenario` before keying, strengthen "distinct" to "provably disjoint". Give each concurrently-armed cast scene its own watchdog bit. | M |
| A11 | One `PlayerTagAllocator` per build run — today 3 ladders + one `with_prev` player walk dies with `entry 4 already has a function with tag 19`, blamed on the ladder, naming a number the author never wrote. | M |
| A12 | Give narration the control-grant spin (its whole lock is `Wait(2) + DISABLE_MOVE`, justified by an assumption conductor.py:48-53 records as IN-GAME DISPROVEN). | M |
| A13 | Move the campaign-member 2nd-block refusal from `lint_logic` into `validate()`; better, carve a small cutscene sub-band so a 2-4 scene dispatch needs no manual flag. | M |
| A14 | ★ **`tests/test_workspace_cutscene.py`** over a 2-block dispatch — the whole lane has none. | M |
| A15 | Delete #13-v3 dead code: `compile_steps`' six actor branches (unreachable and pre-v3 in shape), `actor_animation`/`actor_turn`. | S |
| A16 | Spend parameters that already exist: `s.get("hold")`, `s.get("speed")` on `face_player`. | S |
| A17 | `once = false` allocates a MAP once-flag both call sites discard — so it emits an entirely **ungated** body. | S |

### B. Build the new surface

| # | Item | Size | Value |
|---|---|---|---|
| B1 | ★ **"Check the staging" button** — `load_walkmesh` + `_validate_cutscene_movement` on a worker. **Highest value per line in this review**: the sentences are written, the failure they predict is a softlock, no new math. | M | ★★★ |
| B2 | **`with_prev` checkbox**, enabled per `_par_ok`, disabled on row 0. Parallel beats are the difference between a cutscene and a slideshow; the list already renders the badge and the validator already fences it. | S | ★★★ |
| B3 | **Speaker + Tail + Speed + Hold widgets** on the same show/hide seam the say box and anim Browse already use. | S | ★★★ |
| B4 | **Wrap preview under the say box** — reuse `forms_qt._wrap_preview_panel`; `_wrap_width` is already in scope and unspent. | S | ★★★ |
| B5 | **Two lines in `placedoc.content_markers`** — every cutscene walk target becomes visible on the real background art. | S | ★★★ |
| B6 | **Actor field → editable QComboBox** from the live `actors` getter (`browse_anim` already reads exactly that list). | S | ★★ |
| B7 | Add `requires_flag_clear`, `flag`, `set_flags` to CUTSCENE_SPEC. | S | ★★ |
| B8 | Drag reorder + Duplicate; coalesce consecutive `move()` calls into one undo record. | S | ★★ |
| B9 | **Five cue steps** — `fade`, `music`, `sfx`, `camera`, `give_item` — plus `show`/`hide`. Document the `[TIME]`/`[SPED]`/`[IMME]` tags; nearly free and it unblocks pacing today. | M | ★★★ |
| B10 | **Script read-through pane** over `collect_text_refs` (add the missing `speaker_path`/`tail_path` first). | M | ★★★ |
| B11 | **Promote `cutscene` from `_SINGLE` to a list section** — `Cutscenes (3)`, `_mount_cutscene(member, idx)`. The `cs()`/`ensure_cs()` closures already isolate the block-index seam. Subsumes A4. | L | ★★★ |
| B12 | **Beat storyboard doc** (§4) — after B1/B5/B11, which are its cheap prerequisites. | L | ★★ |
| B13 | **In-scene `{ choice = … }` step** (§5) — the VN core loop. | L-XL | ★★★ |
| B14 | Lift the verbatim one-cast-scene cap. Short term, promote the two lint warnings to `validate()` problems. Fork fidelity is the north star; a forked town screen is exactly what needs a multi-beat dispatch. | L | ★★ |

**Suggested first sprint:** A1, A2, A4, A5, A7, A9 → B1, B2, B4, B5 → A3, A14. Roughly two days, and it
converts the tab from *"traps the editor and lies to you"* into *"usable, honest, and previewing the thing
that softlocks."*

---

## User stories

1. **As a story-campaign author,** I want to open a field with several `[[cutscene]]` beats and keep
   clicking around the tree, so that inspecting a scene doesn't kill my session. *Today:* ★ mounting the
   Cutscene node raises `TypeError` into a stderr nobody sees, and every later click, undo and Check raises
   again (shell.py:7464-7478 vs 7416-7419).
2. **As a dialogue author,** I want to write two `say` lines in a row, so that characters can have a
   conversation. *Today:* ★ three lines in, one out (shell.py:7748, 7758).
3. **As a scene director,** I want to change a step from `wait` to `say`, so that I can revise a scene
   without rebuilding it. *Today:* ★ the original is untouched and a stray step lands at the end (7755).
4. **As a scene director,** I want two actors to move at once, so that my scene reads as staging and not a
   slideshow. *Today:* the list *renders* `[with prev]` and the compiler implements the whole fork/drain,
   but no widget in either editor can write the key.
5. **As a VN author,** I want a reply choice inside a scene, so that a confrontation can branch without a
   fade to black. *Today:* the vocabulary is closed at nine kinds; every decision costs a field reload.
6. **As a VN author,** I want the music to cut and the screen to fade on the line where it matters.
   *Today:* every encoder exists and is spent by non-cutscene code; no step reaches any of them.
7. **As a VN author,** I want to see where an FF9 window will break my line while I type it. *Today:* the
   wrap preview attaches to four keys and `say` is not one of them — though `_wrap_width` is in scope.
8. **As a scene director,** I want to know my actor will reach the spot I sent them to. *Today:* ★
   `_validate_cutscene_movement` writes exactly that warning and no GUI call site can reach it.
9. **As a scene director,** I want to see the marker I'm walking to, on the room's real art. *Today:*
   `content_markers` has no marker row, while MARKER_SPEC's help tells me to reference it by name.
10. **As a story-campaign author,** I want to add the second beat of a two-beat field from the GUI.
    *Today:* `cutscene` is in `_SINGLE` with no Add path — and `tutorials/s5` binds the dispatch lesson to
    widgets that can only touch scene #1.
11. **As a story-campaign author,** I want "Remove cutscene" to remove the cutscene I'm editing. *Today:*
    it pops the entire array behind a singular confirm, beneath a caption saying the form edits scene #1.
12. **As a fork author,** I want a forked town screen to re-stage across the story arc. *Today:* the
    verbatim path wires only the first cast block; the rest are warnings that don't fail the build.
13. **As a maintainer,** I want a green suite to mean the cutscene tab works. *Today:* no test calls
    `_mount_cutscene`, `_inspect_single`, `_node_problems`, `_delete_object` or `_commit`; Behavior has five
    dedicated suites and Cutscene has none.
