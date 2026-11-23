# Cutscene, Place and Trace tabs — review

**Date:** 2026-11-23 · **Reviewed at:** 1d679b31 (`origin/master`) · **Status:** findings only, nothing fixed.

Local `master` (ea72ef8b) was 40 commits ahead when this was written. Those commits change none of the
reviewed files (only `world-*` verbs in `cli.py` and world surfaces in `tools/gui_snap.py`), so every
finding applies there too.

**Scope.** The three Workspace tabs and what they drive: `workspace/cutscenedoc.py`, `cutscenescan.py`,
`placedoc.py`, `tracedoc.py`, the shared click canvas `backdrop.py`, their wiring in `workspace/shell.py`,
and the `imagefield.py` backend behind Trace. Asked for: bugs, improvements, UX and appearance.

**Method.** Three passes, all on Opus, plus first-hand checks by the lead.

1. **Find** — nine reviewers, one per area and lens (code with probes, pixel review of the snaps, shell
   lifecycle, theming / text size / accessibility / test fences). 163 raw findings, merged to 125 claims.
2. **Verify** — seven verifiers told to refute each claim or reproduce it themselves, re-running the
   reporter's probe and judging whether a real user can reach that state. Two explorers drove the flows
   the find pass said it had not covered, with real mouse and key events and the real `image-field` CLI.
3. **Lead** — the claimed blockers were re-checked by hand: T1 reproduced with a fresh probe
   (`probes/lead/t1_probe.py`), P1 by re-running the reporter's probe, T38, P4 and E9 by reading the
   source. The domain test files were green before the review started.

The appearance findings rest on 192 snaps from `tools/gui_snap.py`: every `cutscene:*`, `trace:*` and
`place:*` surface in mist 100%, mist 150%, dark, light, dracula at 125% in a 1024x720 window, and mist
with Guided off.

**What this is not.** Nothing here was played in the game. This worktree has no extracted template
cache, so paths that need the install were not exercised: Place on a real donor fork through the real
loader, and `lint` / `build` of a traced project. Floorplan hand-offs to Trace and Place were read, not
driven. The 15 explore-pass findings (ids `E…`) were reproduced by the explorer that found them; only
E9 and E10 were re-checked by a second reader.

## Fixed since (2026-11-23)

The four data-loss bugs of section 2 are fixed on `claude/cutscene-place-trace-review-36f8ca`. Each fix
has tests that fail without it. The fixes were then attacked by six reviewers (one per fix, a mutation
tester that reverted each change to see whether a test noticed, and a regression / visual checker);
they found 41 things, and the ones that could lose work were fixed in a second round. Everything below
section 1 describes the code BEFORE these commits.

| Finding | Now | Commits |
|---|---|---|
| **P1** wrong-row form fold | Fixed. A form follows its row by identity (fold, Save, Delete, Reset); Behavior / Cutscene / Place fold the pending form on entry; a form left mounted is rebuilt when those tabs change its row. | a124e79c, ef140dc3 |
| **T1** regenerate deletes Place rows | Fixed. Only a `traced_` row is ever deleted. A pre-prefix row is renamed only when the run re-emits its exact quad (through the new camera or the one the file records). Keys added by hand to a traced row now survive. | 07d8212c, 5b5741ca |
| **T38** stale open buffer | Fixed. Generate refuses over unsaved edits; every regenerate finish reloads the open project if its file changed and rebuilds the tabs' view of it; the undo history of the old copy is dropped. | 44859994, 1a4e622b, eef8242d |
| **E9** same-named photos | Fixed. A photo opened fresh never writes into a folder that holds a project, not even its own; it takes `-2`, `-3`, … | 6ba1b55c, ece23708 |
| T15 rename writes a second toml | Fixed with T38: an open Trace project refuses a different Name. | eef8242d |
| P4 Place caches a project's surface | Narrowed: dropped whenever Trace regenerates. Still cached across other changes on disk. | 44859994 |

**Still open after the fixes** (found while attacking them; not fixed):

- A traced row's target, entrance and message come from the Trace session, so a retarget or reword made
  in Place is overwritten by the next regenerate. It is now named under "retook" instead of silent, but
  not prevented. Who owns those values is a design decision.
- `traced_` names are numbered by position, so deleting a session region renumbers the ones after it;
  "removed" then names the last number, not the door that went.
- The session record (`.trace.json`) is written when the job starts. A regenerate the backend refuses
  leaves the record ahead of the compiled project (same family as T8).
- E10 (a non-cp1252 character makes a successful Generate report as failed) is not fixed; the reload no
  longer depends on the exit code, but the first-Generate hand-off to the Editor still does.
- A save that lands while the job runs is reported, not prevented.
- None of this has been played in the game or driven by hand in the app.

## 1. The numbers

139 findings stand: **4 data-loss bugs, 23 major, 88 minor, 24 nits.**
Of the 125 claims from the find pass, 96 were confirmed as stated, 27 were confirmed but narrower than
reported (most were downgraded), 1 was refuted and 1 is by design. The explore pass added 15 and the
verifiers 1.

Ids: `C` Cutscene, `P` Place, `T` Trace, `V` the shared canvas, `E` found in the explore pass.
Effort: S under an hour, M about half a day, L multi-day or needs a design decision.

## 2. Fix first: four ways to lose work

| | Finding | Where | Effort |
|---|---|---|---|
| **P1** | A pending Editor form folds into the wrong row after a Place delete or reshape | `shell.py:5143` | S |
| **T1** | First Regenerate that adds a region deletes Place-minted door0/zone0 | `imagefield.py:886` | S |
| **T38** | Trace Regenerate does not refresh the open FieldDoc; a later Save All overwrites the regenerated toml | `tracedoc.py:877` | M |
| **E9** | Two photos with the same file name overwrite each other's project: the first project's art and sidecar are replaced | `tracedoc.py:833` | S |

- **P1** needs an uncommitted edit on an Editor form and a Place delete or reshape of an earlier row of
  the same kind. The next navigation overwrites a different gateway or event with the form's values.
- **T1** is the ordinary "trace it, put a door on it in Place, go back and add a zone" flow. The door is
  deleted; the only notice is a `removed` line in the Output panel.
- **T38** needs no unsaved edits at all: regenerate from Trace while the project is open, make any edit
  in another tab, Save All. The regenerated doors, events and camera are overwritten by the old buffer
  while the regenerated walkmesh stays, so camera and floor no longer match.
- **E9** is two different photos with the same file name traced into the same parent folder
  (`image.png`, `photo.jpg`, `IMG_0001.jpg`). The second replaces the first project's art and session
  record with no warning.

All four are small fixes. Details in section 4.

## 3. Seven root causes behind most of the list

Fixing the cause clears the group; the ids are worth fixing together.

**1. "Same field" is decided by the member's name.** All three tabs treat a re-feed with the same name as
the same field, and their caches are never dropped when the path, the buffer or the file on disk
changes. Every traced project is called `PICTURE` by default, so same-name collisions are the common
case, not the rare one.
C2, C3, C4, E3 (Cutscene: stale editor index after undo, staging not re-judged, another project's
walkmesh) · P4, P5, P6, P29 (Place: surface cached for the session, wrong room armed, stale load lands
on the next field) · T38.
*One fix:* key each tab's state on the file path and the buffer's identity, and drop it when either changes.

**2. Trace's regenerate does not know what else was authored on the project.**
T1, T2 (hand `[field]` keys wiped), E13 (a Place spawn snaps back to the centroid), T15 (renaming leaves
an orphan toml), E9, E12 (hand doors are invisible on the Trace canvas), T38.
*One fix:* a durable "generated by Trace" marker instead of guessing from row names, per-key merges for
`[field]` and `[player]`, a sidecar named after the project, and a shell reload after every regenerate.

**3. Pending edits have no guard.**
P1 · C10 (unapplied scene settings wiped by any re-render) · C11 (half-typed step text discarded) · T25
(closing the app or opening another image discards an un-generated trace) · T26 (Ctrl+Z on Trace undoes
an unrelated field edit and jumps tabs).

**4. The tab's own checks disagree with the build.**
C5 (Apply turns `style = 128` into a string the build rejects) · C19 (a `Set flag` step accepts a
reserved, save-corrupting bit while every GUI check stays green) · C6, C7, C8 · E1 (the wrap preview is
not what the build wraps) · C14 · P10, P11, P12 · T7, T9 (bad names and out-of-range zones pass Generate
and fail later) · E10 (a non-cp1252 character makes a successful Generate report as failed).

**5. Layout that cannot take the text-size dial or a narrow window.**
C17 (`ElideButton` truncates its own label at its own size hint, so the default window shows "+ St…" and
"Sce…") · C15, C18, C21, C31 · P17 (Place's one control row floors the window past 1280 px at 150%) · T23
(Trace's unwrapped status line clips its warnings and starves the canvas to about 100-160 px) · T24 (the
canvas never refits after a resize) · V2, V4.

**6. Drawing on the art uses UI theme colours, with no plate, halo or label de-collision.**
P20 (labels, handles and the walkmesh outline fall to 1.1-1.7:1 on the art) · P21 (labels pile into an
unreadable cluster) · P18 (a permanent hint pill covers the bottom-right of the art and says "click the
floor" in every mode) · P25, P19, T28, V13.

**7. The canvas can create but not edit, and only with the mouse.**
P16 (a placed NPC, prop, spawn or arrival cannot be moved, renamed or deleted on the canvas, and clicking
one places another) · P24 · E7, E15 (no keyboard path to place or trace anything) · C24, C36, E5 · V3, V8.

**Suggested order.** (1) The four data-loss bugs. (2) Root cause 1, as one change per tab. (3) The quick
build-drift fixes: C5, C19, C17, E10, E1, T2. (4) Layout: wrap the status lines, refit on resize, fix
`ElideButton`. (5) An on-art legibility pass, which needs the owner's eyes on real rooms. (6) Place
editing, which is a design decision.

### All major findings

| | Finding | Where | Effort |
|---|---|---|---|
| **C1** | Staging verdicts from every scene paint on whichever scene is selected | `cutscenedoc.py:1511` | S |
| **C2** | Undo/redo leaves the open step editor aimed at a stale index; Apply overwrites another step or raises | `cutscenedoc.py:984` | S |
| **C3** | Undo/redo never re-judges the armed staging, leaving a stale tick over a restored stall | `cutscenedoc.py:980` | S |
| **C4** | The warm staging walkmesh is never invalidated: an explicit re-check uses a stale mesh, even another project's | `cutscenedoc.py:1456` | S |
| **C5** | Applying a step with an int style rewrites it as a string the build rejects | `cutscenedoc.py:460` | S |
| **C17** | ElideButton elides its own label at its own sizeHint ('＋ St…', '⧉ Sce…' at 100%) | `widgets.py:537` | S |
| **C19** | The 'Set flag' step accepts a reserved, save-corrupting bit and every GUI check stays clean | `cutscenedoc.py:1054` | S |
| **E1** | Step-editor wrap preview disagrees with the build: markup, speaker name and quotes, and literal \n | `forms_qt.py:146` | S |
| **E2** | 'Pick on the stage' stays armed after Apply or after editing another row, and takes over the next stage press | `cutscenedoc.py:1302` | S |
| **E3** | After Close project, another project with the same field name shows the old project's '✓ Every walk reaches its target' | `shell.py:3570` | S |
| **E4** | Multi-camera [walkmesh] auto field: Place under camera 1+ checks clicks against a different walkmesh than the build ships | `placedoc.py:302` | S |
| **P2** | Place ignores the sibling scene.toml: its spawn/arrival/zone edits are overridden at build and scene-owned content is invisible | `placedoc.py:553` | M |
| **P3** | _project_backdrop ignores layer position/size/camera and shrinks the composite to each later layer | `placedoc.py:337` | M |
| **P4** | Project surfaces are cached for the session; a changed walkmesh/camera never reaches Place, even on Load | `placedoc.py:590` | S |
| **P5** | Same member name, different file: the previous room's surface stays armed and clicks write into the new doc | `placedoc.py:536` | S |
| **P16** | Placed markers cannot be dragged, renamed or deleted on the canvas; clicking one places another | `backdrop.py:416` | M |
| **P17** | Place's single non-wrapping control row floors the window past 1280 px at 150% and crushes controls at 1024@125% | `placedoc.py:411` | S |
| **P20** | On-art labels, handles and the walkmesh footprint use UI palette tokens with no halo, and vanish on the art | `backdrop.py:436` | M |
| **E10** | image-field crashes on its success print for any non-cp1252 character, so a fully written project is reported as 'failed (exit 1)' | `cli.py:3674` | S |
| **T2** | Regenerate wipes hand [field] keys (location, title, text_block, borrow_bg) | `imagefield.py:963` | S |
| **T23** | Trace: the unwrapped status line clips its key warnings, floors the window, and the canvas is starved to ~100-160 px at 125-150% | `tracedoc.py:266` | M |
| **T25** | An un-generated trace has no unsaved-work guard: closing the app or opening another image discards it silently | `shell.py:7715` | M |
| **T26** | Ctrl+Z on the Trace tab undoes an unrelated field edit and jumps to another tab; the trace is untouched | `shell.py:5419` | S |

## 4. The four data-loss bugs in full

#### P1 — A pending Editor form folds into the wrong row after a Place delete or reshape
`ff9mapkit/ff9mapkit/workspace/shell.py:5143` · blocker · bug · effort S

Switching to the Place tab does not commit the Editor form that is still mounted (_on_tab_changed only calls _feed_place). _on_place_edit (shell.py:5143) records the Place op but leaves _save_ctx alone, and _save_ctx still holds the old list index. At the next fold (any tree navigation, Save via _ensure_saved, or Undo/Redo, which all go through _commit_active_ck), _commit_active (shell.py:7582-7621) pops every spec key from lst[ctx['idx']] and writes the form's values there. Example: the author edits gateway g1's form and does not navigate away, then deletes g0 on Place. The fold now writes g1's edited values over g2, so g2 is destroyed and g1 appears twice. If the deleted row was the last one, idx >= len and the author's edit is silently dropped. If the author reshapes the same gateway on Place instead, the fold writes the form's old zone back over the drag. The trigger needs an unsaved, actually changed form (an untouched form folds to a no-op), but nothing in the UI warns about it, and the result is lost data written into the user's toml.

- **How to hit it:** Editor: open gateway 1, change 'to', do not click elsewhere -> Place tab -> Load -> Regions -> right-click gateway 0 -> Delete -> click any tree node or Save.
- **Evidence:** Read shell.py 4955-5013, 5143-5169, 5378-5395 and 7582-7621. _checkpoint never touches _save_ctx, and only delete/remove paths (5635, 5666, 7317) clear it. I re-ran place-code/p6_shell.py on the real Workspace (offscreen, prefs and config pinned). Output: 'mounted form: gateway:1 idx 1' / 'after Place delete: [(g1,101),(g2,102)]' / 'after the Editor fold: [(g1,101,[200,0]),(g1,555,[200,0])]', so g2 is gone. The probe simulates the edit by swapping the form getter rather than typing into the widget. That is equivalent, because _commit_active only reads the getters.
- **Fix:** Commit the active form when the Place (and Cutscene/Behavior) tab is shown: call _commit_active_ck() in _on_tab_changed before _feed_place. If the commit fails (invalid value), stay on the Editor or drop _save_ctx and remount. As a safety net, _on_place_edit should set _save_ctx=None (or remount the form) when the mutated section equals ctx['section'].

#### T1 — First Regenerate that adds a region deletes Place-minted door0/zone0
`ff9mapkit/ff9mapkit/imagefield.py:886` · blocker · bug · effort S

is_generated_region() decides that a project is 'legacy' because it has no traced_ row. A project generated by the current code with no regions also has no traced_ rows, so it looks legacy too. The earlier fix (allow_legacy=False when the session emits no regions) only covers a regenerate that still has no regions. It does not cover the moment the author first adds one. The flow: Trace a floor and Generate. In Place, draw a gateway or event; placedoc._fresh_name mints 'door0'/'zone0'. Back in Trace, draw any region and Regenerate. The merge claims the hand door0/zone0 as the generator's and deletes them. The deletion appears only as a 'removed' line in the CLI output in the Output panel. The load_project absorb path (tracedoc.py:1017, allow_legacy defaults to True) has the same misclassification. However, it only runs for projects with no .trace.json sidecar (CLI-generated or pre-sidecar). GUI-generated projects always take load_trace, so that half of the claim is narrower than reported.

- **How to hit it:** Trace a floor, Generate. Place tab: draw a gateway (door0). Trace tab: draw one event zone, then Regenerate. The Place door is gone from the field.toml.
- **Evidence:** Re-ran the reporter's probe_build.py as a copy in my scratch dir, with PYTHONPATH pinned to the worktree package. 'regen no-regions: removed [] kept [... '[[gateway]] door0', '[[event]] zone0']' then 'regen +event: removed ['[[gateway]] door0', '[[event]] zone0']'; 'gateways now: [] events: ['traced_zone0']'. Confirmed placedoc.py:97-126 mints door0/zone0. test_imagefield.py:707 pins only the no-regions case; test :596 covers a project that already has traced_ rows. Nothing covers the no-regions to regions transition. PLAN.md:467 records the earlier fix as closing this class, but it did not.
- **Fix:** The sidecar-marker idea does not help CLI projects. Better: retire the legacy branch, or gate it on a durable marker the generator writes, for example a top-level 'generator = "image-field/2"' scalar (scalars ride through the merge). The cost of a missed legacy claim is one visible duplicated door; the cost of a false claim is silent data loss. Pass the same decision to load_project's absorb. Add a regression test for the no-regions to regions transition.

#### T38 — Trace Regenerate does not refresh the open FieldDoc; a later Save All overwrites the regenerated toml
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:877` · blocker · bug · effort M

The first Trace Generate opens the project through on_generated=open_field. Later Regenerates rewrite the same field.toml in place, but _after_generate returns early when first is False, so the shell's FieldDoc buffer (and the Place tab that shares it) keeps the pre-regenerate data. FieldDoc.save and shell._save_all do no disk-drift or mtime check. Any later Place drop, Cutscene edit or form edit marks the stale buffer dirty, and Save All writes it over the regenerated toml. The Trace-drawn gateways and events disappear, and [camera] reverts to the old pose while walkmesh.obj and the art stay regenerated, so camera and walkmesh no longer match. This happens even when the author saved everything before regenerating; the reporter's probe ordering (dirty before the regenerate, plus --force) is not needed. The reverse also holds: a Regenerate merges from disk, so unsaved Place edits made before it are not seen and are later re-saved without the new regions.

- **How to hit it:** Trace a photo, Generate (the project opens). Trace tab: draw a gateway and Regenerate. Place tab: drop an NPC. Save All. The gateway is gone from the toml.
- **Evidence:** My probe p_t38.py (offscreen, prefs and LOCALAPPDATA pinned to scratch): open_field on the generated toml, then an in-place regenerate through the same CLI the tab runs, WITHOUT --force, adding --gateway. Output: 'disk after regen: gateways 1', 'place buffer gateways: 0', then after one Place NPC drop and _save_all: 'disk after Place drop + Save All: gateways 0 npcs 1'. grep shows no QFileSystemWatcher or mtime check on member tomls in shell.py, and editor/model.py save() has none.
- **Fix:** After every clean Generate whose toml is the shell's open member, reload it: reopen if the buffer is clean, ask (keep mine / take regenerated) if it is dirty. Better, make Trace's Generate refuse or prompt while that member has unsaved edits, since the merge reads disk. As a backstop, record the mtime and size at load in FieldDoc and have save()/_save_all refuse or ask when the file changed on disk.

#### E9 — Two photos with the same file name overwrite each other's project: the first project's art and sidecar are replaced
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:833` · blocker · bug · effort S · found in the explore pass

The first Generate builds its output folder from the photo's file name alone (out = <parent>/<image-stem>-field) and never checks whether that folder already holds a project. image-field then writes art/base.png, walkmesh.obj and <stem>.trace.json into it unconditionally, because only the toml path depends on the Name. So a second, unrelated photo that has the same file name (phone exports IMG_0001.jpg, image.png, photo.jpg) silently replaces the first project's background art, walkmesh and session record. The first project's own field.toml survives and now points at the other room's art. Reopening it in Trace loads the OTHER session (the sidecar glob picks the overwritten <stem>.trace.json), so the next Regenerate writes the other project's name and id.

- **How to hit it:** Trace a phone photo IMG_0001.jpg into Documents/ and Generate. Later, trace a different IMG_0001.jpg from another day and pick Documents/ again. Project 1's background is now the second photo.
- **Evidence:** Script: probes/x-trace-e2e/p3_reopen_crosstab.py, section D. Output is in p3.out next to it. Setup: phoneA/IMG_0001.jpg (800x600) is generated as CELLAR id 30120 into projects/, and a hand [[npc]] Bob is added. Then phoneB/IMG_0001.jpg (600x800, a different photo) is generated as ATTIC id 30121 into the same parent. Output: 'D files: [ATTIC.field.toml, CELLAR.field.toml, IMG_0001.trace.json, art/base.png, walkmesh.obj]', 'D CELLAR files overwritten: [art/base.png, IMG_0001.trace.json]', 'D sidecar now names: ATTIC ...phoneB\IMG_0001.jpg', 'D reopen CELLAR.field.toml in Trace -> name box ATTIC id 30121'. walkmesh.obj was only spared because both traces used the same clicks; with a different trace it is overwritten too (build_image_field writes it unconditionally, imagefield.py:1108). Exit 0, no warning anywhere.
- **Fix:** On a FIRST Generate, refuse an existing <stem>-field folder or suffix it (-field-2). Reuse a folder only when its .trace.json names the same image path, or when the user confirms. Name the sidecar after the project Name or id, not the photo stem, so two sessions cannot share one record.
- **Note:** Re-checked by the lead in source: `tracedoc.py:833` builds the folder from the photo stem alone and nothing checks that it is free.

## 5. Major findings

### Cutscene tab

#### C1 — Staging verdicts from every scene paint on whichever scene is selected
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1511` · major · bug · effort S

cutscenescan.stage_verdicts returns verdict rows for every cast [[cutscene]] block, each tagged with 'scene'. _finish_stage hands all of them to canvas.set_verdicts, and CutsceneStage._draw paints every row (red leg, ring and 'step N stalls here') without comparing v['scene'] with the selected scene. _pts also adds those foreign points to the fit bounds. In a dispatch, a stall in scene #1 is drawn on scene #0's stage at scene #0's 'step 0', which is a different step that is fine, so the author is pointed at the wrong step. Switching scenes does not re-filter, because the rows persist across redraws by design.

- **How to hit it:** A field with a [[cutscene]] dispatch of 2 or more cast scenes; scene #1 has a blocked walk. Select scene #0, press Check the staging, and the red stall marker paints on scene #0.
- **Evidence:** Re-ran cutscene-code/p3_verdicts.py, a valid probe that drives the public stage_now(sync=True) with rail row 0 selected. Output: 'summary: 1 staging problem across 2 scenes', 'scene#0 selected; verdict rows: [(1, 0)]', canvas tags include verdict: 2, and the stall label 'step 0 stalls here' is drawn on scene #0's stage. The code read agrees: _draw at lines 197-204 has no scene filter. No test pins painting other scenes' verdicts.
- **Fix:** Keep the full rows on the doc, and pass only the selected scene's rows to the canvas: canvas.set_verdicts([r for r in rows if r['scene'] == self._scene]). Re-apply that filter in _render and _on_scene_select. Add a fence using a two-cast-scene fixture.

#### C2 — Undo/redo leaves the open step editor aimed at a stale index; Apply overwrites another step or raises
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:984` · major · bug · effort S

Shell _apply_history swaps in a restored deep copy of the document and re-feeds the Cutscene doc. show_field decides 'same field' by member name alone, so it never runs _close_editor, and editor.scene, step_i, insert_at and the widget contents all survive into the restored document. The next Apply calls update_step(self._raw, self._scene, editor.step_i, ...) on the new data, which does one of two things. (a) If the index now holds a different step, Apply silently overwrites it with the editor's stale content: one step is destroyed and another is duplicated. (b) If the index no longer exists, it raises IndexError out of a Qt slot, and the user sees Apply do nothing. _apply_step also uses self._scene rather than editor.scene. The damage is itself undoable, but it is silent: the editor still shows the old content as if nothing had changed.

- **How to hit it:** Cutscene tab: open the pencil editor on a step, or Add a step, then press Ctrl+Z (or Redo) while the editor is still open, then press Apply.
- **Evidence:** Re-ran both reporter probes; both drive the real shell Workspace._undo(), which is the Ctrl+Z path, so they are valid. p2_lifecycle.py: 'A after undo: editor target 0 3 steps 3' -> 'A APPLY RAISED IndexError list index out of range'; in A2 the turn step at index 1 is replaced by the say, and the say is now duplicated at steps 1 and 2. shell-lifecycle/probe1.py: after move ['B','A'], editor on step 0 shows 'B'; after undo ['A','B'] the editor is still on 0 showing 'B'; after Apply the steps are ['B','B'], so 'A' is lost.
- **Fix:** In show_field, when raw is not self._raw (an undo, redo or reload), call _close_editor() and clear _selected_step if it is now out of range. Also make _apply_step use editor.scene and bounds-check step_i, showing a note in the editor on a mismatch instead of writing.

#### C3 — Undo/redo never re-judges the armed staging, leaving a stale tick over a restored stall
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:980` · major · bug · effort S

Once the staging lane is armed (after the first explicit check), the automatic re-judge starts only from _after_edit and _on_scene_select. A same-field re-feed through show_field re-renders but never starts _restage_timer. Undo, redo and edits made in other tabs (for example a Place-tab NPC move) all arrive that way. After the user fixes a stall (the note turns to a tick and the verdicts clear) and presses Ctrl+Z, the document contains the stalling walk again, but the instruments still say every walk reaches its target and nothing is painted on the stage.

- **How to hit it:** Check the staging, fix a stall, then press Ctrl+Z.
- **Evidence:** Re-ran p8_undo_restage.py, which uses the real shell _undo. Output: '1 stall: 1 staging problem', '2 fixed: Every walk ... verdicts 0', '3 after undo: doc walk = [2000, 2000] | restage timer armed: False | note: Every walk in 1 scene reaches its target. | verdicts 0'. Code read: show_field (lines 980-1003) has no _restage_timer.start().
- **Fix:** In show_field's same-field path, start _restage_timer when self._stage_armed and self._wmesh is not None. That covers undo, redo and cross-tab re-feeds. It is cheap, because the timer debounces and runs on the worker.

#### C4 — The warm staging walkmesh is never invalidated: an explicit re-check uses a stale mesh, even another project's
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1456` · major · bug · effort S

stage_now always passes the cached self._wmesh to the worker, and the walkmesh is loaded from disk only when that cache is None. The cache is cleared only by _reset_stage, which runs only when the member NAME changes in show_field, or on show_none. open_field and open_campaign never call show_none. This has two effects. (1) After the field's walkmesh is changed on disk (a Trace regenerate, a Blender re-export, a new bgi), even an explicit 'Check the staging' click judges against the old mesh, although the tooltip says the walkmesh comes from the SAVED file. (2) Opening a different project whose member has the same name (a copied field, or a re-import of the same fork) keeps the previous project's mesh, so the new project's walks are judged, and the storyboard is routed, on the wrong floor. The armed flag carries over too. In both cases the verdict is confidently wrong. The behavior tab's sweep cache (behaviordoc._wmesh) has the same shape.

- **How to hit it:** Check the staging, then either regenerate or re-export the walkmesh and check again, or open another project that has a same-named member and check.
- **Evidence:** Re-ran p4_meshcache.py. Same doc after the bgi was replaced on disk: 'explicit re-check after the mesh changed on disk: Every walk...', while 'fresh doc on the same file: 1 staging problem'. Shell: GLEN opened from sa and checked, then GLEN opened from sb: 'armed True mesh id <same id>', 'shell B check: Every walk...' (a fresh load warns). Note: shell-lifecycle/probe2.py does prove that the cached mesh object is reused, but in my run its 'truth after forced reset' line also printed a tick, so that probe does not by itself show a wrong verdict. p4 does.
- **Fix:** Reset the stage when path != self._path (not only when the member changes), and have the button's click path pass wmesh=None so an explicit check always reloads. Keep the warm mesh for automatic re-judges only. Optionally key the cache on (path, walkmesh mtime). Apply the same fix to behaviordoc's sweep cache.

#### C5 — Applying a step with an int style rewrites it as a string the build rejects
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:460` · major · bug · effort S

open_step shows style = 128 as the text '128', and read_step writes every non-blank speaker, tail or style back as a string. content.text.resolve_style accepts an int flags byte but treats any string as a style NAME, so '128' fails with "unknown window style '128'". style is an editor-managed key, so any Apply of such a step corrupts it, even one that only fixes a typo in the line. Typing a raw byte into the Window style box, as its own tooltip invites ('a raw flags byte'), also produces a value the build rejects. The build refuses the field, so no bad bytes ship, but the editor breaks a valid document and offers no way to enter the documented int form.

- **How to hit it:** A say step with style = 128 (hand-written, or as the tooltip suggests): open it in the step editor and press Apply.
- **Evidence:** Re-ran p1_roundtrip.py, which drives the public _edit_step/_apply_step: step 0 BEFORE {'say':'Hi','style':128} AFTER {'say':'Hi','style':'128'}, and resolve_style then raises 'unknown window style '128' ... or a raw flags byte 0..255'. Read content/text.py:61-76, which confirms that only an int counts as a flags byte.
- **Fix:** In read_step, convert an all-digit style to int and leave anything else as a name. Add style=128 to the editor round-trip test.

#### C17 — ElideButton elides its own label at its own sizeHint ('＋ St…', '⧉ Sce…' at 100%)
`ff9mapkit/ff9mapkit/workspace/widgets.py:537` · major · bug · effort S

ElideButton.sizeHint returns int(QFontMetrics.horizontalAdvance(full)) + pad, which truncates the fractional advance. _elide then calls elidedText(full, ElideRight, width - pad), which measures at sub-pixel precision. A button laid out at exactly its own hint therefore elides whenever the true advance has a fraction above the integer. In the Cutscene scene bar the buttons sit at hint width. At 100% this turns the primary '＋ Step' into '＋ St…' and '⧉ Scene' into '⧉ Sce…' in every theme. '− Scene' breaks at 125%, '⧉ Scene' at 150%, and 'Storyboard' at 125%/1024. The published docsite figure (editor-cutscene_light.png) shows '+ St…' and 'Sce…'. One reporter's extension to ElideLabel/NameLabel (widgets.py:433/:508) is WRONG: those use int + 2 in both the hint and the elide width, and the 2px slack absorbs the fraction. Measured natively, ElideLabels at their hint show the full text.

- **How to hit it:** Open any field with a cutscene on the Cutscene tab at the default window: the add-step button reads '＋ St…' and Duplicate scene reads 'Sce…'.
- **Evidence:** My native probe (v-cutscene-ux/elide.py: real ElideButtons, role=quiet, app QSS, WA_DontShowOnScreen, in a 1400px host with a stretch): "'＋ Step'->'＋ St…' w79 hint79 f45.08", "'⧉ Scene'->'⧉ Sce…' w88 hint88 f54.31", while 'Settings' and '− Scene' were full. A patched sizeHint using ceil(QFontMetricsF advance) + 1 gave '＋ Step', '⧉ Scene' and '− Scene' all in full (v-cutscene-ux/elide2.py). The same probe showed ElideLabel at its hint unelided ('＋ Step' -> '＋ Step'). Snaps mist-100/cutscene-doc-pane and dracula-125-w1024 staged match.
- **Fix:** In ElideButton.sizeHint use math.ceil(QFontMetricsF(self.font()).horizontalAdvance(self._full)) + 1 + self._pad(), and/or have _elide short-circuit to the full text when the float advance is <= w. Add a native gui_snap or test assertion that an ElideButton at its own sizeHint shows text() == accessibleName(). ElideLabel needs no change.

#### C19 — The 'Set flag' step accepts a reserved, save-corrupting bit and every GUI check stays clean
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1054` · major · bug · effort S

The step editor's 'Set flag (idx, val)' kind is typed as a PAIR (forms.py:365), so it takes only two integers. It refuses a [[flag]] name, even though the build resolves names on set_flag. It accepts any index, including 8600, which flags.is_reserved reports as reserved (the read-mail payload band, here the kit's deathrules outpost word). No GUI surface catches it: the tab's PROBLEMS lane (dispatch_problems + scene_problems) has no band check, and the Workspace Check (_check_loose) runs only validate + lint_logic. Only lint_flag_bands catches it, and that is lint-only and reached only through the CLI lint action. A deploy would write a save-corrupting bit with every GUI readout green. A mitigating factor: the step hint does say 'custom flags live in 8712+'. Other forms in the same file use FLAGPAIR, which takes names.

- **How to hit it:** Cutscene step editor: Type 'Set flag', value '8600, 1', Apply, then Check and Deploy, all clean.
- **Evidence:** My probe v-cutscene-bugs/flag.py: with set_flag [8600,1], validate -> [], lint_logic -> [], tab -> [], while lint_flag_bands -> 'writes story flag 8600, inside FF9's reserved ... region -- writing here corrupts real save/engine state'. forms.make_step('set_flag','chest_potion, 1') -> 'pair: must be whole numbers', while build.validate accepts {'set_flag': ['chest_potion', 1]} with a [[flag]] def. Grep: there is no lint_flag_bands/lint_all call under workspace/ or editor/.
- **Fix:** Switch the cutscene step kind to FLAGPAIR so names resolve, like the other forms. Add an is_reserved check on raw set_flag indices to scene_problems and the editor's read_step note. Consider having the Workspace's _check_loose include lint_flag_bands.

#### E1 — Step-editor wrap preview disagrees with the build: markup, speaker name and quotes, and literal \n
`ff9mapkit/ff9mapkit/workspace/forms_qt.py:146` · major · bug · effort S · found in the explore pass

The step editor's 'On-screen preview — how it wraps in the FF9 window' wraps the raw typed text. The build wraps with_speaker(speaker, text) (build.py ~9474), which first expands {colour} markup to zero-width tags, adds the speaker's name line and wraps the body in curly quotes, and the editor's own read_step turns a typed '\n' into a newline. So the preview breaks lines in different places, leaves out the name line, and shows '\n' literally, even though the field's tooltip says '\n' works. The same text feeds the '✓ fits the window' overflow note, so that note can be wrong too.

- **How to hit it:** Cutscene tab → Edit a say step → type a line with a Speaker name (extras drawer), a {item}…{/} colour, or a '\n' → read the preview
- **Evidence:** Probe probes/x-cutscene-place/p9_wrap.py (native Qt, real Workspace, narration scene, editor open on its say step). Each case compares the preview box with the build's own with_speaker+wrap_text: markup PREVIEW ['You obtained the {item}Ancient','Mythril Ore of the Lost Northern','Kingdom{/} at last, well done.'] vs BUILD ['You obtained the [C8B040][HSHD]Ancient Mythril','Ore of the Lost Northern Kingdom[C8C8C8][HSHD] at','last, well done.']; speaker=Cid PREVIEW ['We crossed the whole glen before','the dusk light faded out over'] vs BUILD ['Cid','“We crossed the whole glen before','the dusk light faded out over”']; literal \n PREVIEW ['First line here\\nSecond line'] vs BUILD ['First line here','Second line'].
- **Fix:** Have the panel preview what the build emits: wrap_preview(with_speaker(x_speaker.text(), text.replace('\\n','\n')), ww). Re-run the preview when the speaker field changes. Do the same in the storyboard's _show_beat.

#### E2 — 'Pick on the stage' stays armed after Apply or after editing another row, and takes over the next stage press
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1302` · major · bug · effort S · found in the explore pass

_arm_stage_pick shows no sign that it is armed: the cursor stays OpenHand, the hint text does not change, and no status appears. Only _close_editor or a pick disarms it. Apply leaves it armed, and so does Edit on another row (open_step never disarms). While it is armed, StageCanvas.mousePressEvent sends the left press to the pick before the edit-handle drag can start. A later press on the walk-target handle, or a click to pan, is consumed: the drag never happens and the editor's value is silently replaced with the pressed coordinates. When the editor is on a say step, the pick writes into the hidden value line, and that phantom value appears if the step type is switched to walk. The pick also accepts points far off the walkmesh (3001, 3001 on a mesh of x -300..1000, z -300..600) with no note, and PROBLEMS still reads 'No structural problems.'

- **How to hit it:** Cutscene tab → Edit a walk step → Pick on the stage → Apply without picking (or Edit another row) → later drag the walk-target handle or click the stage to pan
- **Evidence:** Probe probes/x-cutscene-place/p3_anim_pick.py: 'after Apply: sim armed? True editor open True step_i 0'. Then a real QTest press, move and release on the handle: 'handle drag while armed: step0 before {'walk': 'altar', ...} after {'walk': 'altar', ...} editor value now '900, 399''. Arming and then Edit on row 2: 'after Edit row 2 (say): armed True', a stage click gives value_line '0, 0', and 'switch say->walk: value_line '0, 0''. p2_stage.py: 'cursor after arm CursorShape.OpenHandCursor hint Ctrl+scroll zooms · Ctrl+0 fits'; 'off-mesh picked -> '3001, 3001' note ''' then 'after apply step0 = {'walk': [3001, 3001] ...} problems: No structural problems.'
- **Fix:** Disarm in _apply_step, in open_step/_edit_step/_add_step and in _on_kind. While armed, show a crosshair cursor and swap the hint to 'click the stage to pick · Esc cancels', and give the pick button a checked state. Have _stage_picked report when the point lies off the warm walkmesh.

#### E3 — After Close project, another project with the same field name shows the old project's '✓ Every walk reaches its target'
`ff9mapkit/ff9mapkit/workspace/shell.py:3570` · major · bug · effort S · found in the explore pass

_close_project never resets the Cutscene doc: it keeps _member, _raw, _path, the warm walkmesh and the staging note. An in-flight check also lands after the close. When the next opened project has a member with the same name, show_field treats it as same_field (it compares by member name only), so nothing resets. The inspector then shows the previous project's verdict, '✓ Every walk in 1 scene reaches its target.', over a field whose walk is actually blocked. It stays until the user presses Check again. C4 covers the stale mesh on a re-check; this is the verdict itself carrying over with no re-check, caused by Close not resetting the doc.

- **How to hit it:** Open a field → Cutscene → Check the staging (✓) → Close project → open another project whose field has the same name → Cutscene tab
- **Evidence:** Probe probes/x-cutscene-place/p4b_same_name.py: 'P1 verdict: ✓ Every walk in 1 scene reaches its target.' → win._close_project() → 'after close: doc member GLEN raw None? False wmesh kept True note ✓ Every walk…' → open a second GLEN project whose walk goes to [2000,2000] → 'P2 opened (blocked walk), no Check pressed: path cut2b | note: ✓ Every walk in 1 scene reaches its target.' The true verdict is 'P2 cold truth: ⚠ 1 staging problem across 1 scene.' p4_stage_timing.py also showed a check that was in flight across Close landing afterwards, with no exception.
- **Fix:** Call cutscene_doc.show_none() (and place_doc.show_none()) from _close_project. In show_field, treat a member as the same field only when both the name and the path match.
- **Note:** Same root as C4 (the staging state survives a project close and reopen).

### Place tab

#### E4 — Multi-camera [walkmesh] auto field: Place under camera 1+ checks clicks against a different walkmesh than the build ships
`ff9mapkit/ff9mapkit/workspace/placedoc.py:302` · major · bug · effort S · found in the explore pass

build_surface_from_project resolves the walkmesh with the selected camera (resolve_walkmesh(project, cams[ci])). The build always frames it with camera 0 (resolve_camera, 'the primary camera drives the walkmesh frame'). For an auto-framed walkmesh the two meshes differ. Under camera 1, Place accepts clicks on a floor the game will not have, and refuses parts of the real one. Content placed this way lands off the shipped walkmesh with no warning in the tab.

- **How to hit it:** Place tab on a novel field with several [[camera]] blocks and walkmesh auto → Camera combo → camera 1 → click near the far edge
- **Evidence:** Probe probes/x-cutscene-place/p7_multicam.py: a composed room rewritten with two [[camera]] blocks. '[auto] BUILD mesh extent (-1215, 1215, -1924, 256)'; 'Place cam 0: … same as build: True'; 'Place cam 1: extent (-843, 843, -1846, 322) same as build: False'. With [walkmesh] obj both cameras match. p8_multicam_gui.py drove the real tab: cam_box set to 1, then a real click at world z=300 gives 'place NPC dali_sweeper at (2, 307) · floor 0', which is beyond the shipped mesh's max z of 256.
- **Fix:** Resolve the surface mesh with cams[0] (as the build does) and project it through cams[ci] only for display and the raycast.

#### P2 — Place ignores the sibling scene.toml: its spawn/arrival/zone edits are overridden at build and scene-owned content is invisible
`ff9mapkit/ff9mapkit/workspace/placedoc.py:553` · major · bug · effort M

_feed_place passes only fd.data, the raw field.toml, to PlaceDoc. build._merge_scene (build.py:164-188) overlays a sibling <stem>.scene.toml in which the scene wins per key for [player] (spawn, arrival) and for same-named npc/gateway/event/marker rows; camera, walkmesh and layers come entirely from the scene. So on a Blender-split field: (1) a Spawn/Arrival click writes field.toml, the status confirms it and the marker moves, but the build still ships the scene.toml value; (2) dragging a zone or NPC that the scene names changes nothing at build; (3) scene-only entities are never drawn and are missing from _fresh_name's taken set, so a new 'door0' silently inherits the scene's 'door0' zone; (4) own_scene = bool(data.get('layers')) misses layers that live only in scene.toml, so such a fork is placed against the donor's art. The Cutscene tab already gets merged_fn=fd.merged (shell.py:5085); Place does not. Props are not affected because 'prop' is not in _ENTITY_LISTS. PLAN.md:643 records the scene override only as a known issue of the floorplan recompose, not as a Place decision.

- **How to hit it:** A field exported from the Blender add-on (field.toml + scene.toml) -> Place -> Load -> click Spawn / draw a gateway -> Save -> build/deploy: the shipped field uses the scene.toml values.
- **Evidence:** Read build.py 103-188 and shell.py 5156-5169/5085. I re-ran place-ux-look/probe1.py section 4: 'field.toml spawn after Place: [400, 900] -> build sees: [-100, -100]', 'arrival ... [50,60] -> build sees [7,7]', while the markers drawn were at (400,900)/(50,60). I re-ran place-code/p2_ops.py: region_rows shows 'door0 → 70' at the drawn quad, but BUILD gateways show door0 at the scene's [[500,500],...] zone.
- **Fix:** Feed Place fd.merged (as Cutscene does) for markers, regions, own_scene and the fresh-name taken set. Refuse edits to scene-owned keys with the Editor's 'Placed in Blender' wording (spawn/arrival when scene has [player], rows whose name the scene defines), or write those keys to the scene file. Refusing is the smaller change. Note that ops must keep mutating fd.data, not the merged copy.

#### P3 — _project_backdrop ignores layer position/size/camera and shrinks the composite to each later layer
`ff9mapkit/ff9mapkit/workspace/placedoc.py:337` · major · bug · effort M

_project_backdrop composites the field's own [[layers]] with `out = Image.alpha_composite(out.resize(im.size), im)`. It rescales the whole accumulated image to each later layer's pixel size, pastes that layer at (0,0), and ignores the `position`, `size`, `camera` and `shader` keys that build_overlays (build.py:5478-5491) honours. The `camera` argument is never used. One positioned crop therefore becomes the whole backdrop, stretched by the canvas over the camera frame. On a multi-camera field, the later camera's art paints over the picked camera's. `import --editable` writes exactly this shape: every depth group is a tight crop with explicit position/size (extract.py:1568). show_field routes any field with [[layers]] to this project surface (placedoc.py:553). The raycast still uses the correct camera and mesh, so written coordinates are right relative to the mesh, but the art the author clicks on does not match the room, which defeats 'click what you SEE'. A single full-cover layer (the new/floorplan/trace scaffolds) renders correctly.

- **How to hit it:** ff9mapkit import <field> --editable -> open it -> Place -> Load the room.
- **Evidence:** My probe v-place-bugs/p3_backdrop.py (real FieldProject.load + _project_backdrop) uses a 384x448 red cam-0 back layer, a 384x448 blue cam-1 layer and a 32x48 green crop at position [200,300]. Output: 'size: (32, 48) pixel(0,0): (40, 200, 40, 255)', meaning the whole backdrop is the crop. With only the two full-frame layers and camera 0, pixel(10,10) is blue (camera 1's art). I also checked that extract._render_depth_groups emits position/size per layer.
- **Fix:** Filter layers by int(layer.get('camera',0)) == the requested camera index. Composite onto a canvas the size of the camera range (times the layer upscale), pasting each layer resized to its `size` at its `position` (default: full cover), and never resize the accumulator. Treat additive (Abr) shaders as additive or skip them. Key the output per camera (see P9).

#### P4 — Project surfaces are cached for the session; a changed walkmesh/camera never reaches Place, even on Load
`ff9mapkit/ff9mapkit/workspace/placedoc.py:590` · major · bug · effort S

PlaceDoc._bundles[(source, cam)] is filled once and never invalidated. show_field applies a cached bundle automatically (line 569), and on_load returns the cached bundle whenever the key exists (line 590), so 'Load the room' cannot refresh it. For a ('project', path) source, the camera, walkmesh and art can change mid-session: Trace regenerate, Floorplan recompose, a Blender re-export, or a hand edit of walkmesh.obj. Place keeps showing the old art and raycasting the old mesh, so drops land on coordinates resolved against geometry the build no longer ships. Only an app restart clears the cache. In addition, build_surface_from_project reads the toml from disk, so unsaved in-memory [camera]/[walkmesh] edits never show. Real-donor bundles are correctly static.

- **How to hit it:** Load a traced/composed room in Place -> regenerate it in Trace or recompose in Floorplan (same path) -> return to Place / click Load: the old floor is still used.
- **Evidence:** Code read at placedoc.py 569-606. I re-ran place-code/p4_widget.py: after halving walkmesh.obj on disk and clicking Load again, it prints 'same bundle object? True x-extent -1200 1200', while 'a fresh build would give x-extent -600 600'.
- **Fix:** For ('project', *) sources, validate the cached bundle against the mtimes of the toml, the walkmesh source and the layer images (store them in the bundle), or simply always rebuild a project surface on an explicit Load click and drop project bundles in show_field when the member/path changes. Keep the real-donor cache as it is. Separately, consider warning when the doc is dirty in [camera]/[walkmesh].

#### P5 — Same member name, different file: the previous room's surface stays armed and clicks write into the new doc
`ff9mapkit/ff9mapkit/workspace/placedoc.py:536` · major · bug · effort S

show_field decides `same = member == self._member` by the [field] name alone. The canvas reset (gen bump, set_backdrop/surface/regions None, disarm) runs only when not same. The shell never calls place_doc.show_none when a project is opened. So when a different project with a same-named member is opened (composed rooms named A/B, or a re-scaffolded field), Place keeps the previous room's art, camera and walkmesh armed in place mode even though _bundle() for the new source is None. A click is raycast against the old room and written into the new doc. When the same member becomes blocked (protected), the stale surface also stays armed, but _on_surface_clicked refuses the write in that case.

- **How to hit it:** Open project 1, room 'A', Load in Place -> open project 2 which also has a room 'A' -> Place tab -> click the (old) art.
- **Evidence:** Code read at placedoc.py 532-574, and grep showing that shell.py never calls place_doc.show_none. I re-ran place-code/p5_state.py part 2: after show_field('FORK', data2, 'C:/other/FORK.field.toml'), 'bundle False | canvas place_mode True | surface tris 4', and a real QTest click writes an NPC at [3,1501] into data2. Part 4 shows the blocked case: 'same member now blocked: True | canvas place_mode still: True'.
- **Fix:** Compute `same` from (member, resolved path, source), not the name. In the else branch (no bundle or blocked), call self._apply_tool() (which disarms when not loaded) or explicitly disarm and clear the canvas.

#### P16 — Placed markers cannot be dragged, renamed or deleted on the canvas; clicking one places another
`ff9mapkit/ff9mapkit/workspace/backdrop.py:416` · major · ux · effort M · needs a playtest to settle

Place-mode content markers (NPC/prop/chest/spawn/arrival) are inert. _draw_markers tags the anchor only data(0)='marker' with no index, no tooltip and no grabbable flag. mousePressEvent has branches for trace vertices, cut-outs and region handles but none for markers. contextMenuEvent falls through to super() outside region and trace mode. So a left-click on an existing marker is an ordinary slop-click: it raycasts and emits surface_clicked, and _apply_hit appends a SECOND NPC/prop at that spot. The only ways to fix a misplaced item are Undo (latest step only) or typing world coordinates in the Editor form, and the post-drop status names neither. The Regions tool on the same canvas has drag, rotate, retarget and delete, so the two tools are inconsistent. PLAN.md's Rung 3 record does not list marker editing as deferred.

- **How to hit it:** Place tab, Load the room, NPC mode: click the floor, then click the new marker to try to grab it. A second NPC appears on top.
- **Evidence:** backdrop.py:416-439 (marker anchor has no index, tooltip or mark_grabbable), 1108-1148 (no marker branch on press), 1189-1197 (place mode always emits surface_clicked), 1210-1232 (no marker context menu). placedoc.py:843-861 appends on every surface click. studies/click-authoring/PLAN.md 786-807 does not mention moving or deleting markers.
- **Fix:** Add the row index to content_markers. In _draw_markers tag the anchor (kind, index), give it a tooltip and mark_grabbable. In place mode, resolve 'marker' before raycasting on press: a drag re-raycasts and emits one marker_moved, the doc runs one pure move op plus one on_edit. A right-click menu offers Delete and Open in Editor. Copy the region drag and menu plumbing.

#### P17 — Place's single non-wrapping control row floors the window past 1280 px at 150% and crushes controls at 1024@125%
`ff9mapkit/ff9mapkit/workspace/placedoc.py:411` · major · appearance · effort S

The Place control row is one QHBoxLayout: an unelided field_label, Load, the camera combo, ToolStrip, four mode radios (plus the entrance spinner on Arrival), or the Regions cluster. Its sum sets the page minimum, and that sets the whole window floor. With a fork open, the window minimum width is 1117/1273/1391 px at 100/125/150% (place-regions 986/1128/1236). At 150% in the default 1280 window, the label loses its field number ('PLACEDEMO — donor') and the Inspector column is clipped ('PLAC', 'IDENTI'). At 1024 wide and 125%, the Load button reads 'ɔad the rooı' and both ToolStrip segments render as '…', so the author cannot tell Place from Regions. This is the same trap SpillRow (widgets.py:557) was built to cure on the Cutscene bar. The only fence (test_workspace_place.py:340) measures the fresh no-field state.

- **How to hit it:** Set the text size to 150% in a 1280-wide window (or 125% at 1024), open a fork, go to Author > Place.
- **Evidence:** Re-ran theme-scale-a11y-fences/probe_place.py (gui_snap on the native platform, WA_DontShowOnScreen) from my scratch dir. Output: '150 place-fork win minHint 1391 place_doc minHint 1121', field_label w 209 minHint 306, ToolStrip w 209 minHint 220; '125 place-fork win minHint 1273'; '100 place-fork win minHint 1117'. Read dracula-125-w1024/place-fork_dracula_125.png ('ɔad the rooı', '…' '…', 'PLACEDEMO —', Inspector cut) and mist-150/place-fork_mist_150.png (label cut after 'donor', Inspector 'PLAC').
- **Fix:** Make field_label a widgets.ElideLabel(min_ch≈10) with the full text in its tooltip. Wrap the row in widgets.SpillRow: lead = label + Load + camera, tail = ToolStrip + the active cluster. Add a fence on place_doc.minimumSizeHint with a fork fed, in both the place and regions tools. Re-snap at mist-150 and dracula-125-w1024.

#### P20 — On-art labels, handles and the walkmesh footprint use UI palette tokens with no halo, and vanish on the art
`ff9mapkit/ff9mapkit/workspace/backdrop.py:436` · major · a11y · effort M

Every BackdropCanvas overlay is a bare QGraphicsSimpleTextItem or shape in a palette token picked for the UI surface, painted straight onto arbitrary user art: horizon label :390, marker ring and label :419-439, cut-out diamond and label :475-490, region stroke and label :556/:650, pending and handle indices :681/:709, the walkmesh footprint :400. Against the fixture's tan floor (#9e8460), the ground content is authored on, the contrast is: accent 1.29 light / 1.11 dark / 1.83 mist / 1.47 dracula; warn 1.32 / 1.67 / 1.67 / 3.17; error 1.53 / 1.28 / 1.28 / 1.13. In light theme $text on the navy wall art is 1.15. So the cut-out label 'fg0 · z 1073' in light, the blue gateway labels in dark, and the red 'bad' states are close to unreadable. The footprint edge (accent at alpha 130) is weaker still on the floor. Pick any single token and some art defeats it, because hand-painted backgrounds span every luminance.

- **How to hit it:** Any theme: draw regions, cut-outs or markers over the floor in Trace or Place.
- **Evidence:** Recomputed WCAG ratios from editor.theme.pick_palette for all four themes against #9e8460 and #26293a. Results match the reporters' numbers, e.g. light accent 1.29, dark accent 1.11, light text on navy 1.15. Read light-100/trace-contacts-canvas_light_100.png: the amber 'fg0 · z 1073' is barely visible on the tan floor. Read light-100/place-regions-canvas_light_100.png: amber labels and indices on tan or navy are hard to read, and the blue 'door0' is hard to read on navy.
- **Fix:** Add one backdrop helper for on-art text: a translucent surface-coloured plate (the hint pill's rgba surface, about 0.85) behind each label, or a 2 px inverse-luminance outline via QPainterPathStroker. Give handles and glyphs a 1 px contrasting ring. Draw the footprint and outset edges as a dark underlay plus a light line. Apply it at all seven label call sites and fence it with a pixel-contrast check on the trace-contacts and place-regions snaps.

### Trace tab

#### E10 — image-field crashes on its success print for any non-cp1252 character, so a fully written project is reported as 'failed (exit 1)'
`ff9mapkit/ff9mapkit/cli.py:3674` · major · bug · effort S · found in the explore pass

_cmd_image_field prints the toml path, the event messages (via repr) and the deploy hint AFTER build_image_field has written every file. It never calls the house _safe_console() guard. Under the Workspace's QProcess, stdout is a pipe in the locale codepage (cp1252 on Windows), so these characters raise UnicodeEncodeError and the process exits 1 with a traceback: an arrow or CJK text in an event message, or a non-cp1252 character in the photo or output path (for example a Polish, Czech, Cyrillic or CJK Windows user name, since the installed default output folder is ~/Dream World IX). The tab then shows 'Image -> field -- failed (exit 1)' with a hint blaming a vertex above the horizon or the Int16 bound. The first-Generate hand-off to the Editor/Place is skipped, yet the project on disk is complete and correct. Not covered by T8, which is about what a failure does to the tab's state; this is a failure that is not a failure.

- **How to hit it:** Draw an event zone whose message contains an arrow, a dash beyond cp1252, or Japanese, OR have a non-Latin-1 Windows user name and use the default output folder. Click Generate.
- **Evidence:** Full shell, real QProcess run_job, child env without PYTHONUTF8 or PYTHONIOENCODING. Script: probes/x-trace-e2e/p6_shell_cp1252.py (output in p6.out): event zone message 'Go \u2192 north', first Generate. Output: files [HALL.field.toml, art, base.png, hall.trace.json, walkmesh.obj]; Problems: 'Image -> field -- failed (exit 1) -- See the Output panel -- the usual causes are a vertex above the horizon or a floor larger than the Int16 world bound.'; '1. first Generate: editor tab = Trace | member_paths []' (no hand-off). Same result from the tab-level probe p3_reopen_crosstab.py section C: 'C exit 1 handed [] ... UnicodeEncodeError: charmap codec can't encode character \u2192'. Same result from the CLI with a CJK photo folder, p1b.out: exit=1 after T.field.toml, art and walkmesh.obj were written.
- **Fix:** Call _safe_console() at the top of _cmd_image_field, as the dialogue verbs do. Better: have run_job set PYTHONIOENCODING=utf-8 (or PYTHONUTF8=1) in the QProcess environment and decode the output as UTF-8, so every CLI verb the Workspace streams is covered.
- **Note:** Re-checked by the lead in source: `_cmd_image_field` never calls `_safe_console()` and the job runner sets no `PYTHONIOENCODING`.

#### T2 — Regenerate wipes hand [field] keys (location, title, text_block, borrow_bg)
`ff9mapkit/ff9mapkit/imagefield.py:963` · major · bug · effort S

merge_project_toml regenerates [field] wholesale, and the only report is 'retaken: field'. The Editor's own FIELD_SPEC form (editor/forms.py:77-88) writes text_block, title, location (the in-game LOCATION card) and borrow_bg into [field]. build.py also reads hide_area_title and other keys from that table. One Trace Regenerate erases all of them and does not name what was lost. The existing regression test does not catch this. test_imagefield._hand_author inserts text_block as a TOP-LEVEL bare key ('a bare key must precede [field]'), but build.py:363 reads [field].text_block, so the test covers a placement the Editor never writes.

- **How to hit it:** Generate a traced field, set Location in the Editor's Field form and save, then Regenerate from Trace. The location card is gone.
- **Evidence:** My probe p_t2.py set [field].location='Mog's Hut' and title through FieldDoc (the Editor's model), saved, then regenerated. 'before: {... 'location': "Mog's Hut", 'title': 'my notes'}', then 'after: {'id': 30500, 'name': 'M', 'area': 11} | retaken ['field'] kept []'. The reporter's text_block probe reproduced the same way.
- **Fix:** Merge [field] per key, as [player] is merged. The generator owns id, name and area; every other key rides through and is listed in kept. Name each overwritten generator key in retaken. Fix the test fixture so it puts text_block under [field].

#### T23 — Trace: the unwrapped status line clips its key warnings, floors the window, and the canvas is starved to ~100-160 px at 125-150%
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:266` · major · appearance · effort M

Six fixed rows stack above and below the Trace canvas: a two-line nameplate, the photo/pitch row, the tools row, the cut-out strip once a contact exists, the Name/Id/Generate row and the status line. self.status is a QLabel without word wrap. _refresh APPENDS its warnings after the counts: door-without-target, law warnings, above-horizon counts, and last of all '⚠ not stamped — Regenerate X to update the project'. The pitch-drift warning also lands at the end. So the most important clause is the one cut off the right edge, and the unwrapped label makes its full text width the page minimum. Measured on the native platform in a 1280x850 window, with the window minimum in brackets: contacts state canvas 320 px at 100% (998), 230 px at 125% (1198), 158 px at 150% (1348, wider than the window, so the Inspector clips). At 100%, with a project generated and one untargeted door, the status needs 1099 px of 984 and the visible text ends 'Regenerate PICTURE to '.

- **How to hit it:** Trace a photo, Generate, then edit anything; or use text size 125-150%, or a 1024-wide window.
- **Evidence:** Re-ran probe_place.py natively: '150 trace-contacts win minHint 1348 trace_doc minHint 1078 canvas h 158', '125 ... 1198 ... canvas h 230', '100 ... 998 ... canvas h 320'. The reporter's probe3.out (valid: it drives load_image, a Generate, then a real region draw): 'status label width 984 text needs 1099 -> clipped True'. Code: tracedoc.py:266-268 (no setWordWrap), 412-414 (not-stamped appended last); placedoc.py:506 wraps its status.
- **Fix:** self.status.setWordWrap(True), capped at two lines (Place's idiom), and put the warn clauses (not stamped, pitch drift, untargeted doors) FIRST. Set the full text as the tooltip. To win canvas height back, merge the cut-out strip into the tools row as the Cut-outs tool's own cluster, and make the nameplate prose one line. Fence trace_doc.minimumSizeHint in the contacts state.

#### T25 — An un-generated trace has no unsaved-work guard: closing the app or opening another image discards it silently
`ff9mapkit/ff9mapkit/workspace/shell.py:7715` · major · ux · effort M

A Trace session (floor, cut-out anchors and offsets, gateway and event quads with their targets and per-zone messages) exists only in memory until Generate writes the .trace.json sidecar. closeEvent calls _maybe_prompt_unsaved, which looks only at _dirty_members() (field documents). It has no term for trace_doc, so the window closes without a prompt. Inside the tab, on_open, the 'Load <open field>' offer, load_trace and load_project all go through load_image, which clears floor, fg, regions AND _history with no confirmation, so Undo cannot recover the session. Event messages exist only in the session, by design (ev_msg tooltip). TraceDoc already tracks the needed state (_stamped=False after any gesture), but nothing reads it. Losing a long tracing session is real data loss of the author's work.

- **How to hit it:** Trace tab > trace a floor, draw doors and type event messages > close the app (or Open another image) > everything is gone with no prompt.
- **Evidence:** My probe /v-trace-tab/p_doc.py: mid-session 'floor 4 regions 1 hist 4' > on_open(another photo) > 'floor 0 regions 0 hist 0 undo False'. I read shell.py:7643-7660 and 7715-7721: there is no trace_doc reference in the close path, and the grep of trace_doc in shell.py shows only construction, retheme/scale, the rail and the tab-show offer. Note: shell-lifecycle probe3's 'closeEvent accepted' line is vacuous evidence, because _maybe_prompt_unsaved returns True unconditionally under QT_QPA_PLATFORM=offscreen. The code read is what decides this.
- **Fix:** Add TraceDoc.has_unsaved() (an image is loaded, the trace or regions are not empty, and either no project is set up or not _stamped). Fold it into _maybe_prompt_unsaved ('Discard the traced session?') and check it in on_open and on_offer before load_*. Better still, autosave the session to a per-user scratch .trace.json.

#### T26 — Ctrl+Z on the Trace tab undoes an unrelated field edit and jumps to another tab; the trace is untouched
`ff9mapkit/ff9mapkit/workspace/shell.py:5419` · major · ux · effort S

The window-level Ctrl+Z QShortcut (shell.py:1595) calls _undo_shortcut. That function only hands off to a focused text widget, otherwise it pops the shell's _undo_stack of committed field edits. TraceDoc's history can be reached only through its own Undo button, and BackdropCanvas.keyPressEvent does not handle Ctrl+Z. So a real Ctrl+Z pressed on the Trace canvas leaves the trace gesture in place. If a field is open (always true after a first Generate, which opens the traced project), it reverts that field's last edit, and _apply_history moves the author to the tab that edit belongs to. Redo can recover it, but the author has unknowingly undone real work in another surface. The doc-local undo itself is by design (PLAN.md:388); routing the key to it is not covered by any design note or test.

- **How to hit it:** Open a field, make any Cutscene, Place or form edit > go to Trace > click a wrong vertex > press Ctrl+Z.
- **Evidence:** My probe /v-trace-tab/p_ctrlz.py sends a REAL Ctrl+Z key event (QTest.keyClick through the shortcut map, focus on BackdropCanvas) with a Cutscene '+ Scene' edit on the shell undo stack. Result: 'after real Ctrl+Z: tab = Cutscene | trace floor 3 | shell undo stack: [] | redo: ['add cutscene scene']'. The trace was not changed, the cutscene edit was undone, and the tab switched. Grep shows no Ctrl+Z test or QShortcut in tracedoc, floorplandoc or backdrop.
- **Fix:** In _undo_shortcut and _redo_shortcut, when the current tab has a doc-local history (trace_doc.on_undo; the same for floorplan), send the key there and return. Keep the toolbar Undo app-level, but name its scope in the tooltip on those tabs.

## 6. Minor findings: bugs, UX, appearance, accessibility

### Cutscene tab

#### C6 — A say step with signal = "+" or true cannot be applied from the editor
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:464` · minor · bug · effort S

The build accepts signal as "+" (increment, [INCS]), true or an int (build.py:2996-3000), and its own wait_signal lint tells authors to 'Add signal = "+"' to their lines. read_step converts signal with int(), so opening such a step and pressing Apply fails with 'signal must be a whole number'. This happens even with no change, or with only the text edited, so the recommended form locks the step out of the editor. True is displayed as the text 'True'. The field label 'Signal when typed (n or blank)' never mentions '+'.

- **How to hit it:** A say line carrying signal = "+" (which the build's own lint suggests): open it in the editor and press Apply.
- **Evidence:** p1_roundtrip.py, cases 1 and 2: note "signal must be a whole number (got '+')" and "(got 'True')", and the step is left unchanged. grep in build.py: line 8979 is the lint text recommending signal = "+".
- **Fix:** Parse signal as follows: '+' stays '+', digits become an int, a blank clears it, anything else is an error. Show True as '+'. Update the label and tooltip to 'n, + or blank'.

#### C7 — PROBLEMS says 'No structural problems' for conductor errors the tab's own gestures create
`ff9mapkit/ff9mapkit/workspace/cutscenescan.py:259` · minor · bug · effort M

scene_problems covers only part of build._validate_conductor. It misses five rules. (a) A with_prev group whose leader is not walk, path, animation or turn; moving a say above a with_prev turn with the arrow buttons creates this. (b) The same actor twice in one parallel group; duplicating a with_prev turn creates this. (c) An untagged actor step in a cast of two or more, even though the actor field's placeholder says 'blank = sole cast member'. (d) A scene with an empty steps list, which deleting every row produces. (e) Invalid tail codes and style names. In each case the tab shows 'No structural problems.' while the build and the Workspace Check refuse the field. The docstring does call the lane 'cheap raw-only structural checks', so incompleteness is acknowledged, but (a), (b) and (d) are structural and are produced by the tab's own buttons. Severity is downgraded from major: the build catches every case before deploy, so the cost is a misleading readout and a late surprise, not bad bytes.

- **How to hit it:** Cutscene ladder: move a say above a with_prev turn, or duplicate a with_prev turn, or delete every step. The PROBLEMS panel stays clean.
- **Evidence:** Re-ran p5_problems_parity.py and p5b.py, which compare scene_problems with build.validate: TAB [] against BUILD errors for all six cases, for example "step 1 has a with_prev beat after it but isn't a walk/path/animation/turn" and "actor 'Mira' already acts in this parallel group". Code read: _sync_with_prev checks only the step's own kind and row.
- **Fix:** Add to scene_problems: a pass over conductor.group_parallel (leader kind plus per-group actor uniqueness), the missing-actor rule for multi-actor casts, empty steps, and TAIL_CODES/resolve_style checks. Fence each rule against build.validate the way dispatch_problems is fenced.

#### C8 — PROBLEMS flags actor = "player" outside the cast, which the build and compiler accept
`ff9mapkit/ff9mapkit/workspace/cutscenescan.py:288` · minor · bug · effort S

scene_problems reports an error for any step actor not listed in the scene's cast. build._validate_conductor deliberately uses known = set(cast) | {'player'}, and the compiler supports it: _gen_conductor_step_tags puts a player step's tag on the player's own entry (uid 250) whether or not 'player' is in actors. The tab therefore shows a red error that the build does not raise. The tab's rule is the wrong one, and no fence ties the two together.

- **How to hit it:** A cast scene with actors = ["Cid"] and a step { walk = ..., actor = "player" }.
- **Evidence:** p5b.py: TAB ['scene #0: step 1 actor "player" is not in the cast (Cid, Mira)'] / BUILD []. Read build.py:9005 (known includes player) and build.py:6908-6928, where _tag_target('player') resolves to the player entry independently of the cast.
- **Fix:** Treat 'player' as known in scene_problems. Also consider whether stage_model and stage_verdicts should stage a player who acts outside the cast, since they currently iterate cast members only. Add a parity fence.

#### C9 — Duplicate Scene copies a pinned once-flag, so the two scenes share one once-bit
`ff9mapkit/ff9mapkit/workspace/cutscenescan.py:567` · minor · bug · effort S

duplicate_scene deep-copies the whole block, including an explicit flag (the advanced 'Once-flag override'). After the author changes the duplicate's gate, as the button's tooltip tells them to, both scenes test and set the same gEventGlobal once-bit. Whichever plays first marks the bit, and the other one silently never plays. Neither the tab's PROBLEMS lane nor build.validate reports a shared once-flag. This only bites when the source scene has an explicit flag, which is an advanced field mainly used for a campaign member's 2nd+ scene. That makes it an edge case, so severity is downgraded from major.

- **How to hit it:** A scene with Once-flag override set, then the Scene duplicate button, then a new gate on the copy, then build and play. The second scene never fires.
- **Evidence:** Re-ran p9_dupflag.py: 'shared once-flag: 8712 8712', 'TAB: []', 'BUILD: []'. Code read: duplicate_scene is a bare copy.deepcopy(cur[k]). build.py:3493/7945 read cs['flag'] per block with no uniqueness check.
- **Fix:** In duplicate_scene, drop 'flag' from the copy (the build then auto-allocates for a single field; for a campaign member it refuses loudly, which is the right prompt) and say so in the edit label. Add a pairwise-distinct once-flag rule to dispatch_problems and build.validate.

#### C10 — Unapplied Scene-settings edits are silently wiped by any re-render
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1051` · minor · bug · effort S

With the Scene settings card open, CutsceneDoc._render() calls _fill_settings() every time, and that tears the form down and rebuilds it from the document. Anything typed but not yet applied is lost. Many things trigger _render: every tab show (shell.py:4991 re-feeds show_field for the same member), a tree selection while the tab is current (shell.py:4867), any committed edit (a stage-handle drag goes through _after_edit, and the shell's _on_cutscene_edit re-feeds again), undo, and a retheme. The step editor survives the same re-feed because _sync_insets only re-seats it. So the two accordion panels in one tab behave differently, and the settings card has no dirty marker to warn the author. Plain step selection (_on_step_select) does not re-render, so it keeps the typed values.

- **How to hit it:** Cutscene tab > Settings > type a new 'Requires beat' > click the Editor tab to look up an NPC name > come back to Cutscene: the typed value is gone. Or: type a gate, then drag the selected walk's target on the stage.
- **Evidence:** Re-ran cutscene-code/p6_settings_loss.py: typed 150 into the gate, which survived a step select (150), then a stage drag of the selected walk target gave 'after a stage drag: 100 settings open: True', with the doc still at 100. Re-ran cutscene-ux-look/probe_flows.py natively (WA_DontShowOnScreen): '1. typed gate before refeed: 777' then 'gate field after same-field refeed: 100'. Both probes drive real user paths: show_field on the same member is exactly what the shell's tab-show hook calls (shell.py:4991, _feed_cutscene at :5073). No doc or test records this as intended.
- **Fix:** Record the (member, scene, block snapshot) the form was built from, and in _render skip _fill_settings when it is unchanged, so a same-field re-feed re-seats the existing form. Rebuild only on a scene/field change, or when the block really changed (undo/Apply). Optionally show an 'unapplied changes' marker on Apply.

#### C11 — Half-typed step-editor text discarded by rowtools, scene switch, Edit on another row
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1273` · minor · ux · effort S

_move_step, _dup_step, _del_step, _on_scene_select and _del_scene all call _close_editor(), which only hides the editor and clears its target. _edit_step on a different row calls open_step(), which overwrites the widgets. None of these checks whether the editor holds edits that were never applied. A user part-way through a long say line who clicks ↑/↓/⧉/✕ on any row, clicks another scene, or opens another row's pencil loses the line with no warning. Closing the editor on a structural edit is deliberate (the comment notes that indices shift), but losing the typed text is not discussed anywhere.

- **How to hit it:** Open a step's pencil, type a new line, then click ↓ on a neighbouring row (or select another scene): the text is gone.
- **Evidence:** Re-ran cutscene-code/p11_editor_misc.py: _edit_step(2), typed text into value_text, then _move_step(0,+1) gave 'editor open after ↓ on another row: False | typed text survives in doc: False'. Read the code at lines 1067, 1133, 1198-1206 and 1273-1290: no dirty check anywhere.
- **Fix:** Keep the step the editor was opened on, and treat read_step() != that step as dirty. When dirty, either auto-apply before the structural edit (simplest and consistent with the Apply-advances flow) or refuse the edit with a note in the editor. Add mode is dirty whenever value_text or value_line is non-empty.

#### C12 — The storyboard keeps the previous beat on screen after the scene loses all its steps
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1410` · minor · bug · effort S

When storyboard() returns no beats and no error (every step deleted), _refresh_board disables the slider and calls _show_beat, which returns early on an empty beats list. board_say, board_pos and the ladder beat marks keep the old values, and canvas.set_storyboard is never called. The canvas therefore keeps drawing the old board's beat positions and labels over a scene that has no steps.

- **How to hit it:** Turn the storyboard on, then delete every step of the scene with the delete button.
- **Evidence:** Re-ran p7_board_stale.py, which uses the public _del_step (the delete button) three times with the board on: 'beat 1 of 1 | say: Cid: Made it to the altar. | canvas beatpos items: 2 | slider enabled False', 'canvas board beats: 1 doc board beats: 0'.
- **Fix:** In _refresh_board, when beats is empty: set board_say to a 'no steps yet' message, clear board_pos, call ladder.set_beat_marks(()) and call canvas.set_storyboard(None).

#### C14 — Storyboard say strip shows 'Name:' attribution the game never renders
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1429` · minor · ux · effort S

_show_beat writes f"{say_actor}:\n" followed by the wrapped bare line. say_actor is speaker OR actor (cutscenescan.py:450). The compiler attributes a cutscene line only through `speaker`, via text.with_speaker (build.py:6613): the name, a newline, then the line in curly quotes, with no colon. An actor-only say gets no name in game. So the strip shows a colon form the game does not use, shows a name for actor-only lines that the game leaves unattributed, and wraps the unquoted line. The added quotes can move a line break near the width limit. The ▶ Storyboard tooltip promises 'the say line shows with its final in-game wrapping'. test_cutscenedoc.py:272 asserts 'Cid:' is in the strip, so that test needs updating with any fix. It pins the presence of an attribution, not a design decision about the colon.

- **How to hit it:** Storyboard on a scene whose say step has speaker = 'Cid', or only actor = 'Mira'.
- **Evidence:** Re-ran cutscene-code/p12_wrap.py: BOARD 'Cid:\nWe made it to the altar at last, all of\nus.' vs GAME 'Cid\n“We made it…\nus.”'; BOARD 'Mira:\nQuiet now.' vs GAME 'Quiet now.'. Confirmed the compile path: build.py:6613 `line = _text.with_speaker(s.get("speaker"), _cutscene.step_text(s))`. Actor is not consulted there.
- **Fix:** Build the strip text as the build does: _dlg.wrap_preview(_text.with_speaker(s.get('speaker'), line), ww). That needs the beat to carry `speaker` separately from `actor` (cutscenescan.storyboard sets say_who = speaker or actor). Show actor-only attribution, if at all, as a muted caption such as '(bubble on Mira)'. Update test_cutscenedoc.py:272.

#### C15 — The stage canvas is starved by the fixed ladder split (storyboard on, 150%, 1024 wide); dead space under short ladders at 100%
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:888` · minor · appearance · effort M

The vertical ladder/stage split is set once to [340k, 280k] at build time. Nothing re-balances it for content, the storyboard strip or CALIBRE: _toggle_board only shows the bar, set_scale only changes the board slider's minimum, and _ladder_guard's 140px canvas floor runs only when an editor or settings panel opens. Results: at 100% with a 3-step scene, about 35% of the ladder pane is empty while the stage is a modest strip. With the storyboard on at 150% in the default 1280x850 window, or at 125% in 1024x720, the stage is a strip of roughly 60-150 logical px. There the 'Ctrl+scroll zooms · Ctrl+0 fits' hint sits on top of the routed leg and the 'Cid' label, and the leg runs off the bottom edge. The inspector clipping that report #9 also mentions is the same defect as C31.

- **How to hit it:** Open Cutscene at 150% text (or a 1024-wide window) and press ▶ Storyboard: the stage, which is the storyboard's subject, is a sliver.
- **Evidence:** Read the PNGs. mist-150/cutscene-storyboard_mist_150.png: the stage occupies display y≈1010-1180 of 1328, the hint pill overlaps the walk leg and 'Cid', and the leg exits the bottom. mist-100/cutscene-doc-pane: ladder rows end at about y640 of a pane that runs to about y970. dracula-125-w1024 staged/editor: the stage is a short strip. Code: line 888 setSizes; _toggle_board (1368) and set_scale (949) never touch _vsplit; _ladder_guard (1222) is only called from _edit_step/_add_step.
- **Fix:** Size the ladder pane to min(content height, ~50%) on render while the user has not dragged the splitter (track splitterMoved). Give the canvas a scaled floor, about 200*scale/100, that _toggle_board also enforces. Refit the canvas after the split changes. Hide the zoom hint when the canvas is under a minimum height.

#### C18 — Opening the step editor scrolls its header and the edited row out of view
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1233` · minor · ux · effort S

_reveal_editor calls ensureWidgetVisible(self.editor, 0, 40). The editor (about 610px) is about twice the ladder viewport's height (about 300px at default sizes), and Qt centres a too-tall widget, so the editor's top lands above the viewport. At 100% the header band is clipped by a few pixels: Apply and Close are still readable, but the row being edited and every ladder row above it are scrolled away, which defeats the accordion's purpose ('the conversation stays visible around the line'). At 125% in a 1024 window the header, Apply and Close are entirely off-screen and the Type combo is sliced in half. The add lane calls _reveal_editor after every Apply, so this repeats on each typed line. Severity is minor rather than the reported major: at the default 100% the controls remain reachable.

- **How to hit it:** Click a row's pencil (or ＋ Step and Apply lines in the add lane).
- **Evidence:** Re-ran cutscene-ux-look/probe_flows.py natively: '2. viewport h 298 editor h 610 apply_btn y in viewport -8 scroll 163'. Read mist-100/cutscene-editor-pane (header clipped about 8px, no ladder rows visible) and dracula-125-w1024/cutscene-editor-pane (no header, 'Say (dialogue)' combo cut in half). The docsite figure editor-cutscene_light.png shows the same.
- **Fix:** Scroll so the editor's TOP plus one row above it is visible, e.g. self._lscroll.verticalScrollBar().setValue(max(0, self.editor.y() - row_h - 8)) after the layout settles. Do not centre a panel taller than the viewport.

#### C20 — 'Beat' means both a story ScenarioCounter value and a storyboard step group
`ff9mapkit/ff9mapkit/workspace/cutscenescan.py:161` · minor · ux · effort S

In the rail and scene header ('plays at beat 100', cutscenescan.gate_text) and in Settings ('Requires beat', 'Then set beat', forms.py:262/270), 'beat' means the story ScenarioCounter value. In the storyboard ('beat 1 of 2', 'beats, not seconds') and the step editor ('Runs with the previous beat'), a beat is a group of steps that run together. Both meanings appear together on screen in storyboard mode, and the S5 tutorial (lines 80-82) uses both in one sentence. The premise is true and a string-only rename is worth doing. Severity is minor, not major: nothing is mis-built, it is vocabulary confusion.

- **How to hit it:** Open a gated scene and press ▶ Storyboard.
- **Evidence:** Read the mist-150 storyboard snap: 'plays at beat 100' in the scene header and 'beat 1 of 2' in the strip are visible together. Grepped forms.py:262-271, cutscenescan.py:161, cutscenedoc.py:312/1425, and s5-cutscene-and-music.md:80-82. Tests pin the strings (test_cutscenedoc.py:200 'plays at beat 100', :271 'beat 2 of 2'), but as regression strings, not as a recorded naming decision.
- **Fix:** Keep 'story beat' (or 'story point') for the ScenarioCounter gate, e.g. 'plays at story beat 100' and 'Requires story beat', and rename the storyboard unit ('moment 1 of 2', 'Runs together with the previous step'). Update the strings in cutscenescan.gate_text, CUTSCENE_SPEC, StepEditor.with_prev, _show_beat, the two tests and the S5 doc.

#### C21 — Scene rail rows clip mid-glyph behind a permanent horizontal scrollbar
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1028` · minor · appearance · effort S

Each rail item is 'scene #k · plays at beat N · cast n · m steps' in a plain QListWidget with the default as-needed horizontal scrollbar. Because the list scrolls horizontally, QListWidget's default ElideRight never applies, and the text is cut mid-character ('beat 10(' at 100%, 'plays a' at 150%, 'plays' at 125%/1024), above a horizontal scrollbar. The cast/narration kind and the step count, the parts that tell scenes apart, are never visible without scrolling. The code comment at line 893 says the 200px budget was chosen so the gate would fit, and it does not fit.

- **How to hit it:** Any field with a cutscene, on the Cutscene tab.
- **Evidence:** Read mist-100/cutscene-doc-pane ('scene #0 · plays at beat 10(' plus a horizontal scrollbar), mist-150/cutscene-storyboard ('plays a') and dracula-125-w1024/cutscene-staged ('plays'). Code: lines 731-737 (no scrollbar or elide policy) and 1026-1030.
- **Fix:** self.rail.setHorizontalScrollBarPolicy(ScrollBarAlwaysOff) so the default ElideRight works (the tooltip already has the full text), and reorder the text to put the distinguishing parts first ('scene #0 · 3 steps · cast 2 · beat 100'). Two-line items are optional.

#### C22 — Staging problems list truncates the build's sentence and is not clickable
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:928` · minor · ux · effort S

stage_list is a QListWidget with no word wrap, inside the narrow docked inspector. The build's staging sentence ('⚠ [cutscene] #0 step 0: walk target … is off the walkmesh …') shows as a stub: 'walk ta' at 100%, and only '⚠ |' at 125%/1024. REVIEW.md accepts off-view canvas verdicts as a known-small on the grounds that 'the note + list carry the words', but the list does not show the words, so the mitigation fails. No itemClicked or activated handler is connected, so a row cannot take the author to the failing step or the verdict spot.

- **How to hit it:** Press Check the staging on a scene with a stalled walk.
- **Evidence:** Code lines 928-931: no setWordWrap, no signal connection. Grepped for stage_list connections: none. Read dracula-125-w1024/cutscene-staged_dracula_125.png: the list shows only '⚠ |' with a scrollbar. REVIEW.md:41-42 records the 'note + list carry the words' rationale.
- **Fix:** setWordWrap(True) plus ScrollBarAlwaysOff on the list (or word-wrapped captions instead). On itemClicked, select the scene/step and centre the canvas on the verdict's b-point. Optionally strip the '[cutscene] #k' prefix when the scene is already selected.

#### C23 — Stage labels collide with markers; storyboard toggle does not refit the canvas
`ff9mapkit/ff9mapkit/workspace/behaviordoc.py:260` · minor · appearance · effort M

_decollide_labels only avoids other labels. Its down-tier guard clears only the label's own marker row, never other markers or legs, and no leader line is drawn when a label moves. At 125% and 150% the 'player spawn' label is pushed down a tier onto Cid's start dot and the walk leg (the dot sits inside the word), and 'Cid' jams against Tam's dot. Separately, _toggle_board shows the storyboard bar, which takes height from the canvas, without refitting, so edge markers (Mira) can be clipped at the bottom until the user presses Ctrl+0.

- **How to hit it:** Cutscene tab at 125%/150%, or toggling ▶ Storyboard.
- **Evidence:** Read behaviordoc.py:260-300: the overlap test only compares against `placed` label rects. Read dracula-125-w1024/cutscene-staged and editor-pane: 'player spawn' is drawn across Cid's filled dot and the leg, and 'Cid' touches Tam's dot. mist-150 storyboard: 'player spawn' crosses the cyan marker. _toggle_board (cutscenedoc.py:1368) has no fit call.
- **Fix:** Add marker rects (radius plus a margin) to `placed` before placing labels, and draw a 1px leader when a label moves more than one tier. Call canvas fit (when the user has not zoomed) after _toggle_board and after any split change.

#### C24 — Step selection is nearly invisible and mouse-only, yet it drives insert position and drag handles
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:549` · minor · ux · effort S

Selecting a ladder row only changes its index chip from 'n' to '▸ n'. The _StepRow frame gets no property and no QSS. In storyboard mode the beat marks override the chip with '▶ n', a near-identical glyph, so the selection disappears. Clicking a selected row again silently deselects it (line 1075). The selection decides where ＋ Step inserts, and it is the only way to get the stage's drag handle for a walk target, which the stage never hints at. _StepRow is a QFrame with NoFocus and no key handling, so selection needs the mouse.

- **How to hit it:** Click a ladder row, then press ＋ Step or try to find the drag handle.
- **Evidence:** probe_flows.py (native): "5. row props: [('card', None, ''), ('card', None, '')] ['0', '▸ 1']": selection changes only the chip text. probe_kb.py: 'rows focusable: [_StepRow:0 ...]' (NoFocus). Code _chip_text (549-554) gives beat marks precedence over selection.
- **Fix:** Set a 'selected' dynamic property on the selected _StepRow and add a QSS accent border/left-rail, matching the rail's selected idiom. Keep selection visible in storyboard mode (property-based, not the chip). Optionally make rows focusable with Up/Down and Enter.

#### C31 — Docked instruments column overflows the inspector: 'Chec', '⚠ 1 sta', '⚠ |'
`ff9mapkit/ff9mapkit/workspace/shell.py:5040` · minor · appearance · effort M

The Cutscene instruments column (Problems/Staging) is wider than the inspector's viewport, and it clips at the right edge instead of wrapping. At 1024x720 and 125% the window grab (exactly 1024 wide, so this is not a snap artifact) shows 'PROBL', 'STAGIN', 'Chec', '⚠ 1 sta / across 1', a problems list of only '⚠ |', and 'Ope'. Even at the default 1280x850 window at 150% it reads 'Check the stagi', 'No structural proble' and 'Open the .tom'. Even the word-wrapped problems label clips, so the column's content width exceeds the viewport. The docstring's claim ('everything here wraps or scrolls internally') does not hold.

- **How to hit it:** Cutscene tab at 150% text, or in a 1024-wide window.
- **Evidence:** Read dracula-125-w1024/cutscene-staged_dracula_125.png (3072px = 1024x3, grabbed via w.grab() in gui_snap) and mist-150/cutscene-storyboard_mist_150.png. Both show the right column truncated mid-word. Code _build_instruments (900-939): QPushButtons with fixed text, no elide, and a non-wrapping stage_list.
- **Fix:** Make the column yield: use ElideButton (after the C17 fix) or wrapping for the two buttons, give stage_list word wrap with its horizontal scrollbar off, and make sure the inspector host gives the column the viewport width (setWidgetResizable plus a horizontal minimum the dock honours). Re-check the Behavior and Place instrument columns, which dock into the same host.

#### C35 — A staging verdict can paint off-screen because a same-scene re-render never refits; the 'staged' snap shows no verdict label
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1511` · minor · ux · effort S · narrower than first reported

_finish_stage calls canvas.set_verdicts(rows), which redraws without a refit, and same-scene re-renders keep the user's zoom by design (set_scene refit only on a field or scene switch). When an edit moves a walk target outside the previously fitted bounds, the stall label and ring paint outside the viewport and only part of the red line is visible; Ctrl+0 (which includes verdict points in _pts) recovers it. This is narrower than claimed. A typical stall, a target across a wall inside the field, lands within the existing fit and is visible, so only the off-field target case hides it. The snap point stands: the gui_snap 'staged' state uses walk [2000, 2000] through doc._render() with no refit, so the figure meant to show 'a staging verdict painted on the failing leg' shows no verdict label at all and cannot fail on its own subject.

- **How to hit it:** Edit a walk target to a coordinate far outside the stage's current extent, then press Check the staging: the Inspector reports a problem but the stage shows no marker until Ctrl+0.
- **Evidence:** Read review-ctp/light-100/cutscene-staged-canvas_light_100.png: both scrollbars are present, a red line leaves the top edge from Cid, and there is no 'stalls here' label or verdict ring anywhere. Read gui_snap.py:2166-2170 (the 'staged' state mutates the steps, calls _render() and stage_now with no fit). Code path: set_verdicts -> _draw has no _fit.
- **Fix:** In _finish_stage (or CutsceneStage.set_verdicts), if any verdict endpoint lies outside mapToScene(viewport().rect()), call ensureVisible on the first one (preferred over a full refit, so the user's zoom survives). Make the snap state press fit or assert that the label is inside the viewport.

#### C36 — Keyboard reorder loses focus every time; ladder rows cannot take focus
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:556` · minor · a11y · effort S

StepLadder.set_rows deletes and rebuilds every row on each structural edit, so the focused ↑/↓/⧉/✕ button is destroyed. Focus falls to an unrelated, unnamed QToolButton outside the ladder, and a keyboard user must Tab back through the toolbar, rail and every earlier row's five tools to continue. _StepRow is NoFocus with no key handling, so a keyboard user cannot select a row, and selection decides where ＋ Step inserts. That leaves keyboard users able to insert only at the end, or after the row whose pencil they opened. Severity is minor rather than major: real, but it affects keyboard-only authoring of a mouse-centric canvas tool.

- **How to hit it:** Tab to a row's ↓ button and press Space.
- **Evidence:** Re-ran theme-scale-a11y-fences/probe_kb.py (native, hidden, gui_snap's _make_win with pinned prefs): 'focus before: True Move this step down — step 0', then after Space 'focus after: QToolButton  steps now: ['turn', 'walk', 'say']', and 'rows focusable: ['_StepRow:0', '_StepRow:0']'. The probe uses a real key press on the real button.
- **Fix:** After a move/dup/delete in _after_edit, restore focus to the tool with the same glyph on the step's new index (find it by accessibleName '… — step j'). Optionally make _StepRow TabFocus with Up/Down to select and Enter to edit.

#### C38 — Settings card controls and the wrap preview have no accessible names (and so does every forms_qt form)
`ff9mapkit/ff9mapkit/workspace/forms_qt.py:347` · minor · a11y · effort S

With the Scene settings card open, 7 QLineEdits and 1 QCheckBox expose no accessible name, and the step editor's read-only wrap-preview QPlainTextEdit is unnamed too. The cause is in the shared builder: forms_qt.build_form adds each field as QFormLayout.addRow(label, box), where `box` is a container widget, not the input, and the label is sometimes a QWidget wrapper (the concept-badge case). No buddy reaches the input and no accessibleName is set. So this is not Cutscene-specific: every form build_form produces (the Editor tab's NPC/chest/event/field/choice forms, battledoc, tuningdialog) has unnamed inputs. The house a11y fence walks tabs only in the no-field state and never meets a built form.

- **How to hit it:** Screen-reader user tabs through any Editor form or the Cutscene Scene settings card.
- **Evidence:** Re-ran theme-scale-a11y-fences/probe_names.py: 'cutscene-settings unnamed: 7 QLineEdit + 1 QCheckBox', 'cutscene-editor unnamed: [QPlainTextEdit ro=True]'. My own probe (v-cutscene-ux/names.py) called build_form directly on every *_SPEC: 'CHEST_SPEC unnamed 10 of 10', 'EVENT_SPEC unnamed 12 of 12', 'FIELD_SPEC unnamed 7 of 7', 'CUTSCENE_SPEC unnamed 10 of 10'. build_form call sites: shell.py:7448/7803/7830, battledoc.py:491, tuningdialog.py:166, cutscenedoc.py:1160.
- **Fix:** In build_form, call widget.setAccessibleName(f.label) on each field's input (and, when the label is a QLabel, label.setBuddy(widget)). That fixes every form at once. Name the wrap preview in _wrap_preview_panel ('In-game wrap preview'). Extend the a11y fence to build one spec's form and assert every input is named.

#### E5 — Tab order leaves the Cutscene tab before reaching the step rows and the open editor; Apply and Close come before the fields
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:556` · minor · a11y · effort M · found in the explore pass

The ladder rows are rebuilt on every render, so their row tools and the inset step editor join the window's focus chain last. From the scene rail, Tab goes through the scene bar and the stage, then leaves the tab for the console toggle, the Beginner toggle, Deploy and the inspector's Check and Open .toml. Only after those does it reach the step rows' ↑ ↓ edit ⧉ ✕ and the editor. Inside the editor, Apply and Close come before Type, Dialogue and Actor. The read-only wrap-preview box is also a Tab stop. Nothing calls setTabOrder.

- **How to hit it:** Keyboard only: focus the scene rail, then press Tab repeatedly to reach a step's Edit button and the editor
- **Evidence:** Probe probes/x-cutscene-place/p6_keyboard.py walks Qt's TabFocus chain from the rail (output in p6.out): '8 CutsceneStage IN · 9 QScrollArea out · 10 consoleToggle out · 11 Beginner mode out · 12 Deploy out · 13 Check the staging out · 14 Open the .toml out · 15 Move this step up — step 0 IN … 30 Apply IN · 31 Close IN · 32 Cutscene step type IN · 33 Cutscene step dialogue IN · 34 QPlainTextEdit[unnamed] IN · 35 actor'.
- **Fix:** After set_rows/set_inset, chain setTabOrder: scene bar → row tools → editor (fields, then Apply/Close) → stage. Give the preview box Qt.NoFocus.

#### E6 — Undo/Redo of a scene add, duplicate or delete selects a different scene than the one it restored
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1018` · minor · ux · effort S · found in the explore pass

History restores the whole buffer. Because the member name is unchanged, show_field only clamps the existing _scene index. After 'undo delete scene #1' the rail shows #0, not the restored #1. Redo of a duplicate leaves the original selected, not the copy. Redo of 'add scene' shows #2, not the re-added #3. The user has to go looking for what the history step just changed.

- **How to hit it:** Cutscene tab → select scene #1 → − Scene → Ctrl+Z (or ⧉ Scene → Ctrl+Z → Ctrl+Shift+Z)
- **Evidence:** Probe probes/x-cutscene-place/p1_scene_undo.py (real buttons + win._undo/_redo): 'del scene1 → doc._scene=0', 'undo del scenes=3 doc._scene=0 title='scene #0''; 'dup scene1 → scene #2', 'redo dup scenes=3 doc._scene=1'; 'add scene → #3', 'redo add scenes=4 doc._scene=2'. Ladder, stage and stack were otherwise consistent, with raw still pointing at the shell buffer.
- **Fix:** Have the history record carry the scene index the op touched (the cutscene_tab focus key could hold 'cutscene_tab:<k>'), and have _goto_focus pass it so the doc selects that scene.

### Place tab

#### E7 — No keyboard path to place content or draw a region on the Place tab
`ff9mapkit/ff9mapkit/workspace/backdrop.py:1087` · minor · a11y · effort M · found in the explore pass

The backdrop canvas takes Tab focus, but its keyPressEvent handles only Esc (abandon a quad being drawn) and Ctrl+0/Ctrl+1. No key moves a placement point, drops an NPC, prop, spawn or arrival, or adds a region corner, and the region menu (retarget, rotate, message, delete) opens only on right-click over a quad. Every placing action of the tab needs a mouse. The Editor forms are the only keyboard route, and the tab does not point to them.

- **How to hit it:** Keyboard only: Place tab → Load the room → Tab to the canvas → try to place an NPC or draw a gateway
- **Evidence:** Probe probes/x-cutscene-place/p10_place_kb.py walks the focus chain on a loaded novel field: 'Load the room → Place tool → Regions tool → NPC → Prop → Spawn → Arrival → BackdropCanvas[Field backdrop] → (leaves the tab)'. Reading backdrop.py keyPressEvent (1087-1104) confirms that only Esc and Ctrl+0/1 are handled.
- **Fix:** Add a keyboard cursor on the canvas (arrows move a crosshair over the floor, Enter places or adds a corner), and the context-menu key (Shift+F10) to open the region menu on the selected quad. At minimum, make the status line name the Editor form as the keyboard route.

#### P6 — A stale async load's failure lands on the next field and re-enables Load mid-flight
`ff9mapkit/ff9mapkit/workspace/placedoc.py:608` · minor · bug · effort S

_gen is bumped in show_none/show_field but never read, and the loader signals carry no key or generation. _on_load_failed unconditionally sets _loading=None, re-enables load_btn and writes 'Could not load the room: <msg>'. _on_loaded clears _loading and re-enables Load before its stale check. If field A's load fails after the user has switched to B and started B's load, B's status shows A's error, and Load is enabled while B is still in flight, so a second click starts a duplicate worker. A success from A is correctly cached and not applied. show_none also does not reset _loading.

- **How to hit it:** Load on a slow/failing room -> switch to another member -> Load -> the first load fails.
- **Evidence:** Code read at lines 398, 515, 562 and 600-611. I re-ran place-code/p4_widget.py part (b): 'member B status: Could not load the room: RuntimeError: A blew up | load_btn enabled while B in flight: True _loading None', after which B's own load applied normally.
- **Fix:** Emit the request key with loaded/failed (or carry it in the bundle and in a failed tuple). In both handlers, touch _loading/load_btn/status only when key == self._loading; otherwise just cache (on success) or ignore (on failure).

#### P7 — The stacked-floor chooser implies a floor choice the doc cannot record
`ff9mapkit/ff9mapkit/workspace/placedoc.py:828` · minor · ux · effort S · needs a playtest to settle

On a stacked walkmesh pixel, _choose_hit offers 'floor N · height … (visible/behind)', and the status echoes '· floor N'. _apply_hit writes only pos [x, z] (the schema has no floor/height key). The re-fed marker resolves its height with floor_y_at(..., eye), which picks the candidate nearest the camera. So after choosing the behind/upper floor, the marker is drawn on the other floor, at a different pixel from the click. What the menu did choose is a different plan (x,z), where the ray hits that floor, so the choice is not meaningless, but the label promises a floor binding that is not stored. A click exactly on a shared triangle edge lists the same floor twice. Which floor the engine actually seats the actor on cannot be settled offline.

- **How to hit it:** A bridge/balcony field -> Place -> click where two floors overlap -> choose the 'behind' entry.
- **Evidence:** I re-ran place-code/p5_state.py part 1: stacked rows [(0,0,[0,721]), (1,-300,[0,1500]), (1,-300,[0,1500])] (duplicate floor-1 row). After picking floor 1 the status reads '... at (0, 1500) · floor 1', but 'marker y: [0.0] (chosen floor y was -300.0)'. I read imagefield.floor_y_at (eye-nearest candidate) and confirmed that build has no NPC floor key.
- **Fix:** De-duplicate hits per floor. Reword the menu to say it picks the plan point where the ray meets that floor, and that height is resolved by the engine, or warn when the chosen (x,z) lies over more than one floor. Recording a floor would need a schema key and a build change (L).

#### P9 — Place writes .place_backdrop.png into the user's project folder (one file for all cameras)
`ff9mapkit/ff9mapkit/workspace/placedoc.py:340` · minor · bug · effort S

_project_backdrop saves its composite to <project dir>/.place_backdrop.png from the worker thread on every project-surface load. That puts a generated artifact into the author's source tree (it gets committed, zipped and packed with the folder). It is a dotfile, so Explorer hides it by default, and the only ignore rule is in one study folder. The real-donor lane writes to provision.cache_dir()/place/real_<id>_cam<ci>.png. Every camera shares the same filename, so concurrent or successive loads overwrite each other. It is harmless to the build, hence minor.

- **How to hit it:** Open any novel/traced/editable field -> Place -> Load the room -> look in the project folder.
- **Evidence:** My probe v-place-bugs/p3_backdrop.py lists the project dir after one call: ['.place_backdrop.png', 'R.field.toml', ...]. Code read at lines 340-342 versus build_surface line 365.
- **Fix:** Write to provision.cache_dir()/'place'/f'project_{sha1(path)[:12]}_cam{ci}.png' (pass the camera index into _project_backdrop), mirroring build_surface.

#### P10 — Set message accepts an empty string: the event passes validation but has no action
`ff9mapkit/ff9mapkit/workspace/placedoc.py:131` · minor · bug · effort S

The event quad's Set message dialog (_ask_message) returns '' when the author clears the box, and set_event_message writes message=''. build.validate's 'needs at least one action' check tests only that the key is present (build.py:1560), and _event_shows_text('') is False, so the zone builds clean and does nothing in-game. region_rows warns only for the literal '...' placeholder, so no warning shows on the canvas either.

- **How to hit it:** Regions -> right-click an event quad -> Set message -> clear the text -> OK.
- **Evidence:** My probe v-place-bugs/p_misc.py: after set_event_message(d,0,''), 'empty msg warn: None | shows text: False'. I read build.py 1555-1564 and 6376-6380.
- **Fix:** Treat an empty or whitespace result in _on_region_reword as cancel (or re-prompt). Better, also make build.validate count a message only when it is non-blank, which covers the Editor form path too, and have region_rows warn on a blank message.

#### P12 — Gateway target entry has no registration/band check, and retargeting a worldmap door converts it to an int
`ff9mapkit/ff9mapkit/workspace/placedoc.py:773` · minor · ux · effort M · narrower than first reported

The 'to field' spin box (0..32767) and the Set gateway target dialog (1..32767) accept any id, and region_rows warns only for to<=0. An id in the reserved 9000-9012 world-location hole, or one that is neither a stock field nor a field registered anywhere, builds cleanly and black-screens in-game. The claim is overstated where it says 3101-3999 and 9900-29999 'cannot load': those ids are reachable when a field is registered there (fldMapNo is Int16), so the real defect is the missing check that the target exists, not a band rule. The right-click menu also offers Set gateway target on a to="worldmap" door. The dialog starts at 1 and cannot express 'worldmap', and accepting it silently turns the door into a field warp.

- **How to hit it:** Regions -> draw a gateway with a typo id, or right-click a worldmap door -> Set gateway target.
- **Evidence:** My probe v-place-bugs/p_misc.py: to 9005 / 3500 / 20000 all warn: None (only 0 warns); a worldmap row shows no warning, the dialog's initial value would be 1, and set_gateway_target(…,100) yields to=100. I read build.py 1490-1500: validate also checks only for <=0.
- **Fix:** Warn in region_rows for 9000-9012 and for an id that is neither in reference/field-manifest.tsv nor a field of the open project or a live registration. Hide or refuse Set gateway target on a worldmap door, or offer a 'worldmap' choice.

#### P13 — place_prop mints duplicate names after a delete (prop{len(lst)})
`ff9mapkit/ff9mapkit/workspace/placedoc.py:74` · minor · bug · effort S

place_prop names a new prop f'prop{len(lst)}' instead of using _fresh_name, as gateways and events do (NPCs use fresh_npc_name). After any prop is removed, the next drop reuses a live name: placing two props, deleting prop0 and placing again gives ['prop1', 'prop1']. The tree shows two identical rows, the status 'place prop' cannot say which one, and build's duplicate-name lint does not cover props.

- **How to hit it:** Place two props -> delete prop0 in the Editor -> place another prop.
- **Evidence:** My probe v-place-bugs/p_misc.py prints props: ['prop1', 'prop1']. place-code/p2_ops.py and place-ux-look/probe1.py reproduce the same result.
- **Fix:** nm = _fresh_name('prop', lst) and return f'place prop {nm}'. Optionally add 'prop' to the build's duplicate-name lint loop.

#### P14 — The loading status prints the raw source tuple, and the copy still assumes a donor
`ff9mapkit/ff9mapkit/workspace/placedoc.py:597` · minor · ux · effort S

Since the bundle key became (source_tuple, cam), on_load formats key[0] as if it were a donor int. The status reads "Loading field #('real', 351) (camera 0) — extracting + compositing…", or on a novel field a Python tuple with a doubled-backslash Windows path. This is the only feedback during a load that can take seconds. The idle hints (lines 529, 885-889: 'Open a field (a fork of a real room)…', "the donor's art, camera, and walkmesh") and the Load button tooltip ('Extract the donor's camera…') still describe the pre-Rung-7d donor-only lane.

- **How to hit it:** Open any field -> Place -> Load the room.
- **Evidence:** I re-ran place-ux-look/probe1.py: '1. status while loading: "Loading field #(\'real\', 351) (camera 0)…"' and '1b. … #(\'project\', \'C:\\\\Users…demo.field.toml\') …'. The lines are visible in the code read.
- **Fix:** Format from the source kind: real -> f'Loading donor field #{ref}…', project -> f'Loading {Path(ref).name}…', with the camera appended only when n_cams > 1. Reword the idle hints and the tooltip to cover both lanes.

#### P15 — The verbatim-fork tooltip sticks on Spawn/Arrival for every later field
`ff9mapkit/ff9mapkit/workspace/placedoc.py:808` · minor · bug · effort S

_sync_modes sets the 'a verbatim fork runs the donor's own entry sequence — spawn/arrival rows are ignored on it' tooltip on the Spawn and Arrival radios only in its verbatim branch and never clears it. After any verbatim fork has been shown, those radios are re-enabled on later non-verbatim fields, but their tooltip still says the clicks will be ignored, so an enabled control claims it is dead.

- **How to hit it:** Open a verbatim fork in Place -> open an ordinary/novel field -> hover Spawn.
- **Evidence:** I re-ran place-code/p5_state.py part 3 and place-ux-look/probe1.py 3a/3b: 'non-verbatim spawn enabled: True tooltip: a verbatim fork runs the donor's own entry sequence — spawn/'. Code read at lines 794-814.
- **Fix:** At the top of _sync_modes, set both radios' tooltips to a neutral description (or ''), and override them only in the verbatim branch.

#### P18 — The canvas hint pill is static ('click the floor' in every mode) and sits over the art's bottom-right, covering handles and labels
`ff9mapkit/ff9mapkit/workspace/backdrop.py:116` · minor · ux · effort S

The pill text is set once in the constructor and never changes (no setText anywhere). Trace Regions, Trace Cut-outs, Place Regions and Place's refused and bare states all read 'Ctrl+scroll zooms · Ctrl+0 fits · click the floor', even when the gesture is four corner clicks or the object's base, or there is nothing to click. Right-click/Esc as cancel gestures appear only in Place's status line. The pill is pinned to the viewport's bottom-right over the art, which is where the near floor edge, doors and contacts live. In the snaps it covers zone0's corner 3 in trace-regions, and at 150% it covers the fg0 contact diamond and its 'fg0 · z 1073' label. It is mouse-transparent, so a press goes through to a handle the user cannot see. The status lines do carry mode-correct guidance, which limits the harm.

- **How to hit it:** Trace or Place: switch to Regions. The pill still says 'click the floor' and hides the bottom-right of the art.
- **Evidence:** Code read: one QLabel construction at line 116, with no later setText on _hint. Viewed review-ctp/mist-100/trace-regions-canvas_mist_100.png (pill over zone0's corner 3 and spill) and mist-150/trace-contacts_mist_150.png (pill over the fg0 diamond and label). The 4.41:1 contrast number was not re-measured.
- **Fix:** Add set_hint(text) and set a per-mode string from each set_*_mode (regions: 'click 4 corners · Esc/right-click cancels · drag a quad to move'; contact: 'click the object's base'). Hide the pill when there is no camera, and fade it after the first gesture or reserve its band in _fit.

#### P19 — Place's refused state looks live: disabled radios keep full-contrast labels over an empty frame
`ff9mapkit/ff9mapkit/workspace/placedoc.py:797` · minor · appearance · effort S

On a protected field (a bundled example or an installed copy), _sync_modes disables both tools, every radio and the spinners. Only 'Load the room' visibly recedes. The NPC/Prop/Spawn/Arrival radio labels render in full $text, exactly like enabled ones; only their indicator rings mute. The checked 'Place' segment keeps its raised pill, and the 'Regions' segment is muted, which is the same colour an enabled unchecked segment has. Under them sits a large empty frame with the 'click the floor' pill. The one signal is the warn line at the bottom.

- **How to hit it:** Open a bundled example (e.g. examples/vivi-hut) and go to Author > Place.
- **Evidence:** Pixel sampling of mist-100/place-refused_mist_100.png at 3840 px: the brightest pixel in the NPC and Spawn label boxes is (233,230,220) = $text, while the disabled Load button's text is (159,173,196) = $muted. style.py has QRadioButton::indicator:disabled rules (380-386) but no QRadioButton:disabled text colour. The #railSeg rule (822) has no :disabled rule.
- **Fix:** Add 'QCheckBox:disabled, QRadioButton:disabled { color: $muted; }' and a #railSeg:disabled rule (see T28). When _blocked is set, show a centred empty-state message in the canvas, with a 'Save a copy…' action if one exists.

#### P21 — BackdropCanvas labels and corner indices overprint into an unreadable cluster (no de-collision)
`ff9mapkit/ff9mapkit/workspace/backdrop.py:650` · minor · appearance · effort S

Each region gets a centroid label at a fixed (6,-16) screen offset, and in region mode four corner squares with index labels. Markers add labels at (7,-15). Nothing de-collides them, unlike StageCanvas._decollide_labels in behaviordoc. When zones sit near the back of a room they compress to a few pixels and the text overprints: in the light regions snap, 'door0 → 4005' is split by a corner handle, 'zone0' and 'zone1' read 'one0' and 'one1' under handles and warn glyphs, and '2door1 → 4005' merges an index into the label. The fixture worsens the crowding, because its camera puts every zone in the back sliver of the art (see P28). But the mechanism is real: any far-back or adjacent zones produce it.

- **How to hit it:** Place or Trace > Regions: draw two or three zones near the far wall.
- **Evidence:** Read light-100/place-regions-canvas_light_100.png: the cluster around (780-1420, 290-490) shows '2door1 → 4005', 'one0', 'one1', and 'door0' cut by handle 1. Code: backdrop.py:642-656, 681-684, 709-712, with no collision pass anywhere in BackdropCanvas.
- **Fix:** Show corner indices only for the hovered or last-touched quad (the walk-out chevron already shows order). Give labels the plate from P20. Add a cheap greedy pass after _rebuild/_fit/zoom that nudges or hides a label whose rect intersects an earlier one, keeping the full text in the tooltip.

#### P22 — Place's empty-state, Load tooltip and pre-load prompt still describe a donor-only, fork-only tab
`ff9mapkit/ff9mapkit/workspace/placedoc.py:529` · minor · ux · effort S

Since Rung 7d, Place accepts novel, composed, traced and `ff9mapkit new` fields (build_surface_from_project). Its text still says otherwise. The no-field note (show_none:529 and _refresh:885) reads 'Open a field (a fork of a real room) and come back — or fork one on the Import tab'. The Load tooltip (418) reads 'Extract the donor's camera + walkmesh and composite its background'. The pre-load prompt (888) reads 'the donor's art, camera, and walkmesh arrive together'. A from-scratch author is told to go and fork something. The refusal comes from editor.model.protected_reason:163 ('-- edit a copy, or scaffold one with `ff9mapkit new`'): it mixes an ASCII '--' with the em dash Place prefixes, and it names a CLI command, not File > New Field.

- **How to hit it:** Open Place with no field, or with a File > New Field project before loading.
- **Evidence:** Read placedoc.py:418, 529, 885-889 and editor/model.py:163. The mist-100/place-refused snap's warn line reads 'Placement is off here — that is a bundled example -- edit a copy, or scaffold one with `ff9mapkit new`.'
- **Fix:** Reword the empty state to name every lane. Make the Load tooltip and prompt branch on self._source[0] ('real' says 'donor #N's art', 'project' says 'this field's own art'). Change the refusal wording in Place only (prefix your own GUI phrasing, e.g. 'use File ▸ New Field or save a copy'), or add a GUI variant. protected_reason is also spent by the editor and CLI, so do not reword it at the source.

#### P23 — Place mode radios have no tooltips; Spawn vs Arrival vs entrance and the minted defaults are never explained
`ff9mapkit/ff9mapkit/workspace/placedoc.py:444` · minor · ux · effort S

The NPC/Prop/Spawn/Arrival radios get a tooltip only in the verbatim-refusal branch of _sync_modes, and that tooltip is never cleared when a non-verbatim field is fed afterwards. On a normal field, nothing explains that Spawn is the default entry point while Arrival is a per-door landing keyed by the source gateway's entrance number. Nothing says each NPC is minted as a dialogue-less Vivi named npcN (place_npc:67), or that each prop is a 'barrel' (55, 74). The post-drop note ('place NPC npc0 at (x, z) · floor 0') does not say where to give it a model or words.

- **How to hit it:** Place tab on any field: hover the mode radios, place an NPC.
- **Evidence:** placedoc.py:444-451 (no setToolTip on the radios), 805-810 (the only tooltip, set on the verbatim path and never reset), 55/67/74 (defaults), 856-858 (the note).
- **Fix:** Set a one-line tooltip per radio at construction. Restore it when the field is not verbatim; today the verbatim text sticks after switching fields. Append '— give it a model/words in Editor ▸ NPCs' to the NPC and prop drop note.

#### P24 — Regions: the first corner of a new zone cannot be placed inside an existing zone; the click is silently swallowed
`ff9mapkit/ff9mapkit/workspace/backdrop.py:1140` · minor · ux · effort S

With no pending corners, a left press over any regionquad or regionedge item starts a whole-quad drag. A release within slop ends it unchanged (just a rebuild) and never reaches the corner-append path. No corner is added, no click_refused is emitted and no status text appears. Starting an event zone whose first corner lies inside a larger gateway or event zone is therefore impossible until the user discovers that the first corner must be outside every quad; later corners work anywhere. No test or study doc records this as intended.

- **How to hit it:** Trace or Place > Regions with one zone drawn: click inside it to start a second zone. Nothing happens.
- **Evidence:** probe2.py section D rerun: 'pending corners after a click inside region 0: 0 drawn 0 changed 0 refused []'. grep of the backdrop, tracedoc and placedoc tests finds nothing pinning the behaviour.
- **Fix:** Treat an rquad drag released within _CLICK_SLOP_PX (unchanged quad) as a corner click, falling through to the append path. Only regionpt handles keep absolute priority.

#### P29 — A camera pick carried over by member name makes Load never apply (stuck on 'Loading…')
`ff9mapkit/ff9mapkit/workspace/placedoc.py:604` · minor · bug · effort S

_cam_pick is keyed by member name only and is never cleared, not even in show_none. If a previous field with the same name had camera 1 picked and the newly fed field has fewer cameras, on_load requests (source, 1). The builder clamps to camera 0 and returns cam_index 0. _on_loaded caches the result under (source, 0), sees 0 != _cam_index() (1), treats it as 'user moved on', and drops it without refreshing the status. Every further Load misses the cache under (source, 1), rebuilds, and drops again. The room never appears, the status stays on 'Loading … (camera 1)', and the camera combo stays hidden (it is synced only in _apply_bundle and hidden for one camera), so nothing in the UI recovers short of a restart. Reaching it needs a same-named member across projects (as in P5) after a multi-camera pick, so it is an edge case, but a dead end when hit.

- **How to hit it:** Open a multi-camera room 'A', pick camera 1 in Place -> open another project whose room 'A' has one camera -> Place -> Load.
- **Evidence:** My probe v-place-bugs/p29_cam.py (PlaceDoc with build_surface_from_project patched to clamp like the real one): project 1 room A with 2 cams, pick camera 1 -> applied. Project 2 room A with 1 cam -> 'Load #1: applied=False bundles cams=[0] status="Loading field #(…) (camera 1" cam_box visible=False', and the same for Load #2.
- **Fix:** Key _cam_pick on the source (or the path), and clear it in show_none. In on_load or _on_loaded, clamp the pick to the bundle's n_cams and store the clamped index back (or compare against min(pick, n_cams-1)), so a clamped result is applied.

#### P30 — The Inspector's Contents rollup goes stale after a Place drop while the tree count updates
`ff9mapkit/ff9mapkit/workspace/shell.py:5143` · minor · bug · effort S

_on_place_edit refreshes the member's tree object rows (so 'Props (1)' appears) but never re-runs the Inspector. Place, unlike Cutscene/Behavior, keeps the ordinary field card in the right column, so after a drop the tree and the Inspector on the same screen disagree: the tree says Props (1) while CONTENTS still reads '1 NPC'. _rollup (shell.py:8626) does count props, so a re-render would fix it. The card corrects itself on the next tree selection.

- **How to hit it:** Place tab -> Load -> place a prop -> look at the Inspector column.
- **Evidence:** I viewed tools/scroll_out/gui_snaps/review-ctp/mist-100/place-fork_mist_100.png. The tree shows 'NPCs (1)' and 'Props (1)', the status line says 'place prop at (300, 1700) · floor 0', and the Inspector CONTENTS shows only '1 NPC'. That state was produced by gui_snap.snap_place driving the real _apply_hit -> on_edit -> _on_place_edit path (gui_snap.py:1921-1923), so it is a real user path. grep confirms _rollup iterates over 'prop'.
- **Fix:** At the end of _on_place_edit, re-render the Inspector for the current tree item (the existing _inspect/select path with tree signals blocked). The same applies to the Cutscene/Behavior edit hooks if they ever show the field card.

### Trace tab

#### E11 — A 16-bit PNG opens and builds as a solid white rectangle, with no warning
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:508` · minor · bug · effort S · found in the explore pass

load_image and build_image_field both call Image.open(path).convert('RGB'). Pillow converts a 16-bit greyscale PNG (mode I;16, which GIMP, Photoshop and RAW converters export) by clamping each 0-65535 sample to 255. Any normal photo therefore becomes pure white, both on the Trace canvas and in the shipped art/base.png. The user traces on a blank frame, and Generate ships a white background with exit 0.

- **How to hit it:** Export the room painting from an editor at 16 bits per channel and open it in Trace.
- **Evidence:** Script: probes/x-trace-e2e/p4_odd_keyboard.py (output in p4.out). A gradient 16-bit PNG whose 8-bit-equivalent mean is 94.9 gives: 'tab/build ingest convert(RGB) mean [255.0, 255.0, 255.0]', 'tab canvas pixels across the 16-bit gradient [255, 255, 255, 255]', 'CLI on 16-bit exit 0 base mean [255.0, 255.0, 255.0]'. Other odd inputs (paletted, JPEG, CMYK JPEG, 8-bit grey, RGBA, 64x64, 4000x1000, 1080x2400, 6000x4000) all ingest correctly (p1.out, p7).
- **Fix:** Add one shared ingest helper used by both the tab and the build: for I;16 or I modes, scale with point(lambda v: v / 257) (or numpy >> 8) before convert('RGB'). Also flatten RGBA over a known colour instead of letting it go black.
- **Note:** Overlaps T19 (photo ingest).

#### E12 — Hand-authored and Place-tab doors and zones are invisible on the Trace canvas, so traced doors can be drawn over them with no overlap warning
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:1015` · minor · ux · effort M · found in the explore pass

load_project absorbs only the generator's own traced_ rows into the session, and the canvas is fed only from the session (_region_shim). A door0 or zone0 drawn in the Place tab, or written by hand, is therefore not drawn on the Trace canvas at all, not even as inert context. placedoc.region_rows' overlap law, which this tab already runs, cannot judge a new traced door against it. The author draws doors blind to the doors the project already has, the same gap P8 names for donor doors on forks, here on the Trace lane.

- **How to hit it:** Trace -> Generate -> Place: draw a door -> Save -> back to Trace -> Regions tool: the existing door is not shown.
- **Evidence:** Script: probes/x-trace-e2e/p5_shell_crosstab.py (output in p5.out), whole shell. Trace generates HALL, Place loads it, drops an NPC and draws door0, then Save All gives 'after Save All: gateways [door0]'. Back on Trace: '3. Trace regions on canvas 0 session regions 0'. Place itself shows it: '4. Place markers 2 regions 1'.
- **Fix:** Feed the file-side gateway and event rows to the canvas as locked, inert context rows. They are already invertible through the same camera (load_project does it for traced rows). Include them in the shim the overlap law judges, and keep them out of the argv.

#### E13 — Every Trace Regenerate moves a Place-tab spawn back to the floor centroid; the only notice is one Output line
`ff9mapkit/ff9mapkit/imagefield.py:967` · minor · ux · effort S · found in the explore pass

The Place tab offers Spawn on a traced project and writes [player] spawn. The regenerate merge treats spawn as generator-owned, so the next Trace Regenerate silently resets it to the vertex average. The merge names it as 'retook player.spawn' in the console, but the Trace tab's status line and the Problems verdict say nothing. The user's deliberate spawn placement is lost on any later floor tweak. Arrivals, NPCs, props and Place doors survive (verified), so spawn is the odd one out.

- **How to hit it:** Trace -> Generate -> Place: Spawn tool, click a spot -> Save -> Trace: nudge a vertex -> Regenerate.
- **Evidence:** Script: probes/x-trace-e2e/p3_reopen_crosstab.py, section B (output in p3.out). placedoc.set_spawn(data, 10, -1100) is saved, then a Trace vertex nudge and Regenerate give: 'B survived: ... spawn [-5, -833] arrival [{entrance: 1, pos: [20, -1000]}]'. The only trace is the console line 'retook (generator-owned, the session wins): player.spawn'. The Trace status reads 'Generating REOPEN -> ... ...'.
- **Fix:** Keep a file-side spawn that still lies on the new walkmesh, and retake it only when it falls off. Or at least surface 'retaken' and 'removed' in the Trace status and Problems verdict after the job.

#### E14 — Trace status line stays on 'Generating X -> ... ...' forever after the job ends, success or failure
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:871` · minor · ux · effort S · found in the explore pass

on_generate sets the status to 'Generating <name> -> <out> ...'. _after_generate never refreshes it: it returns early on failure and on every Regenerate, and only hands off after a clean first Generate. So the tab's own status line keeps claiming a build is in progress after an exit 0, an exit 1, or a Stop, until the next gesture. On a failed job it also hides the gesture count and the not-stamped warning.

- **How to hit it:** Click Generate or Regenerate, wait for the Output panel to finish, and look at the Trace tab's status line.
- **Evidence:** Script: p6_shell_cp1252.py (output in p6.out). After the job had exited 1: 'trace status: Generating HALL -> ...p6\hall-field ...'. Same in p3 section B after an exit-0 Regenerate: 'B trace status: ...room-field ...'.
- **Fix:** In _after_generate, always _refresh() with the verdict ('HALL regenerated' / 'Generate failed -- see Output'), then do the first-run hand-off.
- **Note:** Overlaps T8 (the status never settles).

#### E15 — Trace authoring has no keyboard path: floor vertices, cut-out contacts and regions are mouse-only
`ff9mapkit/ff9mapkit/workspace/backdrop.py:1087` · minor · a11y · effort M · found in the explore pass

The canvas takes focus (StrongFocus, in the Tab chain), but its keyPressEvent handles only Esc (cancel a pending quad) and Ctrl+0 / Ctrl+1. There is no keyboard way to add, select, nudge or delete a vertex, mark a contact, draw or reshape a region, or open the vertex or region menu. Delete, Backspace, arrows, Return and Space on the focused canvas do nothing, and Ctrl+Z on the bare tab does nothing (T26 covers Ctrl+Z inside the shell). Everything around the canvas (Open, pitch, Undo, Clear, Name, id, Generate) is reachable, so the whole core task is the one part a keyboard user cannot do.

- **How to hit it:** Tab into the canvas after opening a photo and try to trace or fix a vertex without the mouse.
- **Evidence:** Script: probes/x-trace-e2e/p4_odd_keyboard.py (output in p4.out). 'focus chain: [Open an image..., Camera pitch, Floor tool, Undo, Clear, BackdropCanvas: Field backdrop, Field name, Field id, Generate field project...]'; 'canvas keys changed the floor? False'; 'Ctrl+Z on the canvas (no shell) changed the floor? False'.
- **Fix:** Add a keyboard cursor: arrows move a crosshair, Enter adds a vertex or corner, Tab/Shift+Tab select vertices, arrows nudge the selected one (one history step per key release), Delete removes it, and the Menu key opens the region or vertex menu at the selection. The canvas already has the canvas-px seams (_commit_floor, _drag_canvas).

#### T3 — Player spawn is the vertex mean: off the floor for strongly concave traces
`ff9mapkit/ff9mapkit/imagefield.py:1036` · minor · bug · effort S · narrower than first reported · needs a playtest to settle

The generated [player].spawn is the arithmetic mean of the un-projected floor vertices. For a strongly concave trace (an L, or a U around a counter) that point lies outside both the traced polygon and the outset walkmesh. Image-field generation and the Trace tab give no warning, and the tab never draws the spawn. The claim's 'no warning' is overstated, though. build._validate_content_placement (build.py:4996-5000) warns 'player spawn ... is off the walkmesh -- you'll start off the floor' at Build/Deploy. The author is told, just late and away from the Trace canvas. Most photo floors are convex trapezoids, so this needs a deliberately concave trace.

- **How to hit it:** Trace an L-shaped floor, Generate, Deploy. The build warns that the spawn is off the walkmesh; Warp puts the player off the floor.
- **Evidence:** Re-ran probe_spawn.py: 'L (canvas) spawn (-225, -850) inside traced floor: False inside walkmesh: False'; 'U (canvas) spawn (-10, -539) ... False'. Read build.py:4931-5004: an off-mesh spawn produces a build warning. Could not run a full build here (no templates in this fresh worktree).
- **Fix:** Choose an interior spawn: the centroid of the largest triangle from triangulate(), or an area-weighted centroid checked with point-in-polygon, falling back to a triangle centroid. Optionally draw a spawn marker on the Trace canvas. The suggested fix is sound.

#### T4 — outset_polygon: no miter limit; narrow notches fold into overlapping triangles
`ff9mapkit/ff9mapkit/imagefield.py:480` · minor · bug · effort M · narrower than first reported

The geometry is as reported. The miter offset has no limit: a 5-degree corner moves 1100 world units. A concave notch narrower than 2x48u inverts after the outset (the walls cross), and triangulate then emits overlapping triangles whose summed area exceeds the polygon area. Nothing detects this before walkmesh.obj is written, and the build's _validate_walkmesh_geometry flags only zero-area triangles. The reach is narrower than the claim implies. At the default camera, 96u is about 16 canvas px at mid-depth, not 'a few px', so it takes a deliberate slit-like notch or a very sharp spike. A consecutive duplicate vertex cannot come from canvas clicks; it can arrive only through the CLI --floor or the load_project inversion. Collinear runs end up as zero-area triangles, which the build already warns about.

- **How to hit it:** Trace a floor with a very thin inward notch (around a pillar base), or a very acute far tip, then Generate. The walkmesh has overlapping triangles or a long spike.
- **Evidence:** Re-ran probe_geom.py and probe_tri.py: '5 deg ... (2000, 0) -> (3099, -48) moved 1100'; 60u notch outset '(1482, 2048), (1482, 348), (1518, 348), (1518, 2048)' (crossed); 'Uout ... tri sum 6625872 poly 6550416' (overlap). Duplicate vertex: outset leaves (1000,0) unshifted. Read build.py:5064-5083: only degenerate (zero-area) triangles are warned.
- **Fix:** Drop consecutive duplicate and near-collinear vertices first. Bevel any miter longer than about 2d. After the outset, check that the polygon is simple and that the triangle-area sum equals the polygon area, and raise ImageFieldError naming the vertex if not. The suggested fix is sound.

#### T5 — Self-intersecting floor trace is accepted and triangulated over its hull
`ff9mapkit/ff9mapkit/imagefield.py:512` · minor · bug · effort S · narrower than first reported

Neither the Trace canvas (backdrop.py:1203-1206 appends every click), the TraceDoc ready gate (good>=3, bad==0) nor build_image_field checks that the floor polygon is simple. For a crossed outline (bowtie) the signed area is about 0, so _as_ccw does not re-wind it, and the ear-clipper and fan fallback emit triangles covering the whole square. The walkmesh then includes floor the author never traced. The outline is drawn on the canvas, so a crossed trace is visible to the author before Generate; the realistic route is a vertex drag across an edge during refinement. The collinear 3-click case produces a zero-area triangle, which build._validate_walkmesh_geometry already warns about at build time.

- **How to hit it:** Trace 4 floor points in a crossing order, or drag a vertex across the opposite edge, then Generate.
- **Evidence:** probe_geom.py: bowtie 'signed area 0.0 faces [(3, 0, 1), (1, 2, 3)] tri area sum 1000000.0' against 500000 drawn. probe_build.py: 'bowtie floor builds silently? built: 4 verts 2 faces (no refusal)'. build.py:5078 warns on degenerate triangles only.
- **Fix:** Add an O(n^2) segment-crossing check plus a non-zero-area check in build_image_field (ImageFieldError), and mirror it in TraceDoc._refresh as a Generate gate that highlights the crossing edge. This can share the simplicity check with T4.

#### T6 — A region pushed above the horizon by a pitch change disappears from the canvas, but the tooltip says to right-click it
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:629` · minor · bug · effort M

_region_shim leaves out any region with a corner above the current horizon, and _refresh_regions feeds only the shim rows to the canvas. A gateway or event quad drawn high on the photo at the default pitch 26 disappears from the canvas when the author lowers the pitch (for example to 10, horizon y 141.7). The region stays in the session, Generate is disabled, and the Generate tooltip tells the author to 'reshape or delete it (right-click the quad)', but there is no quad to right-click. Floor vertices in the same state stay on the canvas and are drawn red. The way out is to slide the pitch back, which brings the quad back, or to press Undo. Nothing is lost and no wrong bytes can be written, so this is friction plus a misleading tooltip, not a major bug.

- **How to hit it:** Trace tab > Regions tool > draw a door near the top of the photo > lower the Pitch slider > the quad vanishes > the Generate tooltip says to right-click it.
- **Evidence:** My own probe /v-trace-tab/p_t6.py drew a real event zone through _on_region_drawn at pitch 26 (corners at canvas y 100-140), then set the pitch to 10. Result: 'fed 0 canvas 0 gen False', with status '1 region · 1 above the horizon'. Floor vertices above the horizon remained ('2 above the horizon (red)'). The reporter's probe injects into _regions directly but gives the same result: 'pitch 12 rows fed: 0'. Setting the pitch back restores the quad.
- **Fix:** Keep above-horizon rows in the canvas feed, drawn at their stored canvas px with a 'bad' flag (red, like bad vertices) that the law judge skips, so right-click Delete still works. The cheaper option is to change the tooltip and status to 'slide the pitch back to see it, or Undo'.

#### T7 — Field name is not validated: a bad name leaves a half-written project and prints a traceback
`ff9mapkit/ff9mapkit/imagefield.py:1107` · minor · bug · effort S

TraceDoc passes name_box text straight to --name, and build_image_field uses it as the filename <out>/<name>.field.toml. Its comment says 'every refusal has passed: NOW touch the disk', but the filename is never checked. walkmesh.obj and art/ are written first, then the toml write raises. On Windows, a name containing ? " : * gives OSError [Errno 22], and a name containing / gives FileNotFoundError. OSError is not in the CLI's except tuple (cli.py:3671), so the Output panel shows a raw traceback. On an in-place Regenerate this replaces walkmesh.obj and art under the old, unchanged toml. The Editor's own name spec (editor/forms.py:79) and hub._NAME_RE allow only letters, digits and underscore. Authors are not likely to type such a name, so this is minor.

- **How to hit it:** Trace tab > type a name such as 'Room?' in Name > Generate.
- **Evidence:** I re-ran trace-code/probe_build.py. Names 'A"B' and 'Q?X' raise OSError [Errno 22] and 'sub/dir' raises FileNotFoundError, each leaving ['art', 'art\\base.png', 'walkmesh.obj'] on disk. I read imagefield.py:1104-1111 (the write order) and cli.py:3671 (the except tuple).
- **Fix:** Validate the name once, with the shared ^[A-Za-z0-9_]+$ rule (hub._NAME_RE), in two places: in build_image_field before any write, raising ImageFieldError, and in TraceDoc.on_generate as a status error.

#### T8 — Generate sets up the project when the job starts: a failed first Generate leaves the tab armed, and the status never settles
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:865` · minor · bug · effort S

on_generate sets _project, sets _stamped=True and writes the .trace.json sidecar as soon as run_job accepts the job, before the CLI has run. _after_generate returns early on failure and never refreshes the status. There are three effects. (1) After any Generate, successful or not, the Trace status line keeps saying 'Generating <name> -> <out> …' until the next gesture. (2) After a failed first Generate, the button reads 'Regenerate PICTURE — in place' for a project that does not exist, and the not-stamped warning is hidden. (3) When the author retries and it succeeds, first is False, so on_generated never fires and the project is not opened in the Editor or fed to Place (the rung-7d hand-off). The existing test (test_first_generate_hands_the_project_to_the_shell_once) misses this because it calls on_finished(1) and then on_finished(0) on the SAME launch, which is not a real retry. No data is lost and the in-place retry writes to the right folder, so the severity is minor rather than major.

- **How to hit it:** Trace tab > first Generate fails (for example a floor beyond the Int16 bound) > fix it > Generate again > the project never opens in the Editor, and the status keeps saying Generating.
- **Evidence:** My probe /v-trace-tab/p_doc.py: after on_finished(2), 'btn= Regenerate PICTURE — in place stamped= True status= Generating PICTURE →'. Then a second on_generate followed by on_finished(0), with the toml present: 'opened: []', and the status still reads 'Generating…'. After a successful regenerate the status also still reads 'Generating…'.
- **Fix:** Keep the pending {out, name, fid} in a local captured by on_finished. In _after_generate, commit _project and _stamped only when code==0, and work out 'first' from 'no successful generate yet'. Always call _refresh with a verdict: 'Generated -> <out>' or 'Generate failed — see Output'. Change the test to do a real second launch.

#### T9 — Traced gateway/event zones are not Int16-checked; build fails later with struct.error
`ff9mapkit/ff9mapkit/imagefield.py:1080` · minor · bug · effort S

Floor vertices are checked against the Int16 world bound (imagefield.py:1039), but _zone_world does not check gateway or event zone corners. At the default pitch 26 the horizon is above the frame, so the canvas accepts every pixel. Any region corner in the top ~18 canvas px (of 448) un-projects to |z| > 32767. Generate writes that zone into the toml, and the failure only appears later at build, as struct.error from content/gateway.py:61's '<hh' pack, far from the cause. The reach is narrow: only a region drawn at the very top of the image (for example a far hallway door) at a shallow pitch.

- **How to hit it:** Trace tab at the default pitch: draw a gateway whose far corners are within ~18px of the top of the photo, then Generate (succeeds) and Deploy (struct.error).
- **Evidence:** probe_build.py 'gateway zone near the horizon': built; zone [[-15694, 204556], ...]. My sweep at pitch 26: the first in-bound row is y=18 (z=31755); at pitch 40 every row is in bound. content/gateway.py:61 does struct.pack_into('<hh', ..., int(x), int(z)) with no range check, and grep finds no zone bound check in build.py.
- **Fix:** In _zone_world, apply the same +-32767 bound to each corner and raise an ImageFieldError naming the zone. Mirror it in the Trace region judge so the corner is refused at click time.

#### T10 — A project with a sidecar cannot be opened once its source photo is moved or deleted
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:912` · minor · bug · effort S

load_project uses the folder's .trace.json whenever one exists. load_trace then calls load_image(data['image']) with the ABSOLUTE photo path recorded at Generate time, and the project's own art/base.png is never tried. If the source photo is deleted or moved, or the project is opened on another machine, the explicit Open fails with 'Could not open X.field.toml: [Errno 2] No such file or directory: <photo path>'. The message names the toml, not the missing photo, and offers no way to locate it. On the pristine auto-offer path the exception is swallowed and the path is remembered as rejected, so the open field silently never loads into Trace. The backfill path, used when no sidecar exists, would have worked from art/base.png. Deleting the sidecar is a workaround the author would not discover.

- **How to hit it:** Generate a traced project > delete or move the source photo (for example from Downloads) > later open the project's field.toml in Trace, or show Trace with that field open.
- **Evidence:** I re-ran trace-code/probe_doc.py section 6 (a valid build_image_field project plus a sidecar, then the photo unlinked). Pristine auto-load gives 'image None project None rejected True'. Explicit Open gives 'Could not open MV.field.toml: [Errno 2] No such file or directory …tmp_photo.png'.
- **Fix:** In load_trace, try the recorded path, then the photo's name beside the sidecar, then <sidecar dir>/art/base.png (art/base.png is the exact crop, so pixels map 1:1), and show a warn note when falling back. Or catch the failure in load_project and continue with the backfill branch.

#### T12 — Clear acts only on the floor even when the Regions or Cut-outs tool is active; the Undo tooltip leaves out regions
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:569` · minor · ux · effort S · narrower than first reported

on_clear empties only _floor, and the Clear button is enabled only while a floor exists. The button sits at the end of the tool row next to whichever tool cluster is showing. With the Regions tool active (Gateway/Event radios visible), 'Clear' is enabled whenever a floor exists, and clicking it wipes the FLOOR while every region stays. One Undo brings the floor back. There is no gesture that clears all regions or all cut-outs. The Undo tooltip says 'the last vertex or cut-out gesture', although it also undoes region gestures. The Clear tooltip ('Remove every traced vertex') is accurate, so the label in context misleads, but nothing is lost.

- **How to hit it:** Trace tab > Regions tool > click Clear expecting the zones to go > the floor trace disappears instead.
- **Evidence:** My probe /v-trace-tab/p_doc.py with the tools set to 'regions': 'clear enabled: True label: Clear', then on_clear gives 'floor 0 regions 1'. trace-code/probe_doc.py section 2 shows that with only regions and cut-outs left, Clear is disabled. Tooltips are at tracedoc.py:186 and :190.
- **Fix:** Scope Clear to the active tool, with the label following the tool ('Clear floor' / 'Clear regions' / 'Clear cut-outs'), as one undoable gesture. Change the Undo tooltip to 'the last gesture (vertex, cut-out or region)'.

#### T13 — A new photo keeps the previous project's Name and Field id, so a second traced room deploys over the first
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:504` · minor · ux · effort S · narrower than first reported

load_image resets the trace, project, distance and fov, but not name_box or id_box. Every new tab starts at PICTURE / 30058. If an author traces photo B after generating project A, or simply keeps the defaults for both, B is generated with A's name and id into a different folder. Nothing compares the id against previous Trace projects or the live registrations. The reporter called this an EventDB collision; the real consequence is narrower. deploy_field into the same folder at the same id reverts that slot's prior deploy, so deploying B silently replaces A in the game. A's project files stay intact and redeploying A restores it. A separate small point: widgets.BAND_HINT ('Custom band 4000–32767') does not mention the 9000-9012 reserved hole that pack.check_custom_id rejects.

- **How to hit it:** Trace tab > generate room A > Open another photo > Generate with the boxes untouched > deploy both > the first room is gone in-game.
- **Evidence:** My probe /v-trace-tab/p_doc.py: set ROOMA/30500, then load_image(photo), and the boxes still read 'ROOMA 30500'. trace-code/probe_doc.py section 4: the second argv carries 'ROOMA', '30500' with --out …other-field. I read widgets.py:365 and pack.py:87-91.
- **Fix:** In load_image for a NEW photo (not load_trace or load_project), default the name to the photo stem cleaned to [A-Za-z0-9_] and upper-cased. Suggest the next free scratch id, or at least warn in the status when the id equals the last generated project's id. Add the reserved hole to BAND_HINT.

#### T14 — Canvas-frame cut-outs are misread as snips; the picker says 'full canvas'
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:330` · minor · bug · effort S · narrower than first reported

The classification rule is deliberate. studies/click-authoring/PLAN.md:131-133 and :180-183 record 'a photo-aspect PNG fills the frame REGISTERED; anything else is a SNIP' and 'equal aspect = aligned, that is the whole rule'. test_workspace_tracedoc.py:214/388 pin it. So a small same-aspect crop being registered is by design: it is what the owner's rule says. The real defect is the canvas-frame case. The cut-out picker (tracedoc._ask_cutout title: 'full canvas, alpha'), the CLI --foreground help and the HTML tracer all tell the author to make a full-CANVAS PNG. The CLI build would register such a PNG 1:1, since it cover-crops each fg to the canvas. On any photo whose aspect is not 384:448, though, TraceDoc treats that 1536x1792 or 384x448 PNG as a snip and shrinks it, to 229x268 canvas px on a 4000x3000 photo.

- **How to hit it:** Trace a 4:3 photo, add a cut-out made at canvas size (as the picker's 'full canvas' wording suggests), and see it shrunk to a small snip.
- **Evidence:** Re-ran probe_doc.py section 5: '120x160 snip on a 1200x1600 photo -> full' (matches the documented rule); '1536x1792 canvas-frame cut-out on a 4000x3000 photo -> snip preview size 229 x 268'. Read PLAN.md:130-136 and 176-183, and _ask_cutout at tracedoc.py:1126.
- **Fix:** Also register a PNG whose aspect is 384:448 (the build's own frame), and reword the picker and tooltips to say 'a copy of the photo (same frame), alpha'. Keep the photo-aspect rule. Do not switch to exact-size matching, which would break the owner's documented rule.

#### T15 — Renaming then Regenerating writes a second field.toml; hand content stays in the orphan
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:823` · minor · bug · effort S

An in-place Regenerate takes 'out' from self._project, but takes the name from the still-editable name_box (no lock, no validator). After the Name is changed, build_image_field looks for out/<NEW>.field.toml, finds nothing to merge, and writes a fresh toml next to the old one. Both have the same field id. Every hand-authored table (NPCs, arrivals, Place doors) stays only in the old file, which the Editor and Place tab still have open. The new file is not opened (regenerates never call on_generated). No data is destroyed, but the project is split, and a deploy of the new toml ships without the hand content.

- **How to hit it:** Generate a project, change the Name box, click Regenerate. The folder now holds two field.tomls.
- **Evidence:** probe_build.py: "kept on rename: [] ; tomls in folder: ['M.field.toml', 'RENAMED.field.toml']". Read tracedoc.py:823-836: name comes from name_box.text() while out comes from self._project; name_box is never disabled (grep on name_box).
- **Fix:** Once the project is armed, either lock the Name box (with a tooltip explaining why), or on a changed name merge from the existing <old>.field.toml and rename it. Locking is the smaller, safer change.

#### T16 — The auto-offer loads a broken project halfway and silently: the photo shows, no project is set up, no message
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:985` · minor · bug · effort S

load_project calls load_image(base) before reading walkmesh.obj and the occluder comments. If a later step raises (walkmesh.obj missing or unreadable, or fewer than 3 'v' lines), the tab is left showing the project's art with an empty trace and the first-run teach status, and no project is set up. On the pristine auto-offer path (offer_project) the exception is swallowed and the path is remembered as rejected, so the author sees no reason. A Generate from there starts a NEW '<base>-field' project. On the explicit Open path the error is shown, but the half-loaded art stays. Broken projects like this are rare, so the severity is minor.

- **How to hit it:** Open a traced project whose walkmesh.obj is missing in the Editor > show the Trace tab > the art appears with an empty trace and no explanation.
- **Evidence:** I re-ran trace-code/probe_doc.py section 7 (a real build_image_field project with walkmesh.obj deleted, then offer_project): 'image: …noobj\\art\\base.png | project: None | status: Click the floor's outline in order…'. This is a valid user-reachable state: show the Trace tab while that field is open.
- **Fix:** Read and validate the obj ring (and the toml tables) before load_image, so every refusal comes before any state is touched, as the existing 'Honest refusals FIRST' block intends. On the auto-offer path, show the refusal as a muted status note.

#### T18 — image-field CLI prints a hard-coded '--id 30058' deploy hint and does not validate --id
`ff9mapkit/ff9mapkit/cli.py:3694` · minor · bug · effort S

_cmd_image_field always prints 'Deploy + walk it: py tools/deploy_field.py <toml> --id 30058 (then ~ -> Warp 30058)', whatever --id was given. deploy_field's --id decides the slot, so a terminal user who copies the hint deploys into 30058, possibly another session's scratch slot on the shared install. The GUI Trace tab runs this same CLI, so when its id is not 30058 the Output panel shows this wrong line next to the GUI's correct ok_next hint. The parser (cli.py:9981) accepts any int with default 4003 and does no pack.check_custom_id, so 9000-9012, real ids and ids above 32767 pass Generate. build.py:1300-1308 catches some of these later, at build.

- **How to hit it:** py -m ff9mapkit image-field photo.png --floor ... --out X --id 30777, then copy the printed deploy line. It deploys to 30058.
- **Evidence:** Read cli.py:3694 (literal 30058) and cli.py:9981. probe_argv.py: '--id 9005 accepted by the parser: 9005'. The GUI path validates through pack.check_custom_id (tracedoc.py:819) and runs the same CLI, so its stdout carries the wrong hint.
- **Fix:** Print args.id in the hint, and call pack.check_custom_id(args.id) before building (return 2 with its message).

#### T20 — Composed-snip write and cut-out read errors escape their Qt slots silently
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:1119` · minor · bug · effort S · narrower than first reported

Writing the composed <stem>.fg{i}.png beside the source photo is deliberate. PLAN.md:136 says 'written beside the source image' so the emitted command stays re-runnable. The 'pollutes the photo folder' part is therefore by design, and a collision with a user file of that exact name is unlikely. The real part is error handling. frame.save() in _composed_fg_path (called from on_generate) and Image.open() in _attach_cutout (called from _on_contact and on_fg_attach) are not wrapped. A read-only photo folder, or a corrupt or unsupported PNG, raises inside a Qt slot. No sys.excepthook is installed in the workspace (grep: only worldforest.py references one), so under pythonw the traceback goes nowhere: Generate silently does not start, and the contact stays unattached after its history entry was pushed. Stale fgN files remain after a removal renumbers the indices.

- **How to hit it:** Trace a photo from a read-only folder (for example a mounted share), place a snip and click Generate. Nothing happens and no message appears.
- **Evidence:** Code path read: tracedoc.py:840-841 -> _composed_fg_path:1119-1120 (no try); _attach_cutout:323 Image.open (no try), called at :774 and :790 after _push_history. grep for excepthook in workspace/ and apps/ff9_workspace.pyw found none beyond worldforest. PLAN.md:136 documents the write location. Not run end-to-end (it needs a read-only folder).
- **Fix:** Wrap the attach and compose steps in try/except (OSError, PIL.UnidentifiedImageError) and report through self._refresh(msg, 'error'). Optionally fall back to <out>/src/ when the photo folder is not writable. Keep the documented location otherwise.

#### T22 — Trace's 'next step' after Generate is an unquoted terminal command instead of the in-app Deploy
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:859` · minor · ux · effort S · narrower than first reported

ok_next reads 'Deploy it: py tools/deploy_field.py <out>/<name>.field.toml --id N — then ~ → Warp to field → N'. Both premises are true. The path is unquoted, so it breaks when copied if the path has spaces: the installed default proj_base is ~/Dream World IX, and many home folders have spaces. tools/ exists only in a git checkout, while proj_base already switches on that case. Every comparable Workspace hint (importdoc's 'Build & Deploy → Deploy', the builddoc verdicts) points to the in-app deploy. One part of the suggested fix is unsound: 'Press Deploy (F9) — then Warp to field → {fid}' is wrong when the Build tab's destination is a test slot. F9 runs build_deploy.on_go with the configured radio, and the test slot overrides the field's own id. The hint should defer to the deploy verdict for the warp id, since builddoc's own ok_next already names the right id.

- **How to hit it:** Pip-installed Workspace > Trace > Generate > the Problems verdict says to run py tools/deploy_field.py with an unquoted path under 'Dream World IX'.
- **Evidence:** I read tracedoc.py:56-57 and :859-860, the other ok_next strings (grep across workspace/*.py: importdoc 794/1064 say 'Build & Deploy'), shell._deploy_now at 8391-8405, and the builddoc rb_test/rb_own radios at 182/196.
- **Fix:** ok_next = 'It opened in the Editor — press Deploy (F9); the deploy verdict names the warp id.' For a checkout, keep a quoted terminal line (subprocess.list2cmdline) as a secondary hint, if at all.

#### T24 — The canvas never refits on resize: adding the first cut-out (or any layout shrink) leaves cropped art and a scrollbar
`ff9mapkit/ff9mapkit/workspace/backdrop.py:1072` · minor · ux · effort S

BackdropCanvas fits only on a refit=True set_backdrop, deferred to the first paint, or on Ctrl+0. resizeEvent only re-pins the hint. The Trace cut-out strip is hidden until the first contact exists, so marking the first cut-out inserts a row and shrinks the canvas by about 40-55 px at the old zoom. A vertical scrollbar appears and the bottom of the floor (vertices 2/3, the contact label) goes off-screen. This happens every time, in every theme and scale. Window or splitter resizes behave the same way: a grown window keeps the small fit, and a shrunk one crops. No study doc records 'no refit on resize' as a decision; the only zoom contract is 'a same-field re-render keeps the user's zoom'. Ctrl+0 recovers, but it is advertised only in the pill. No data is affected.

- **How to hit it:** Trace: trace a floor, then switch to Cut-outs and mark a contact. The canvas gets shorter and the art is cropped with a scrollbar.
- **Evidence:** Viewed review-ctp/mist-100/trace-contacts_mist_100.png: vertical scrollbar at the right, floor running off the bottom, vertices 2/3 not visible. trace-ux-look/probe1.out: '[traced] viewport 706x359 vbar False fully-visible True' -> '[contact added] viewport 694x318 vbar True fully-visible False'. backdrop-code/probe1.py rerun: shrink resize from fit -> 'hbar=True(0..28) vbar=True(0..134)', with no refit.
- **Fix:** Track _at_fit (set by _fit, cleared by wheel zoom, Ctrl+1 and a hand pan). In resizeEvent, re-run _fit while _at_fit is true, measured from maximumViewportSize() so it cannot feed back. Separately, consider reserving the strip's row so it does not shrink the canvas.

#### T27 — The pitch slider's dashed horizon is off-frame at the default pitch and for 23 of 43 positions
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:120` · minor · ux · effort S

The pitch tooltip says to 'slide until the dashed horizon sits on the image's own eye level', and the empty-trace teach says to click 'below the dashed horizon'. With the session rig (distance 3000, fov 42) the horizon is inside the 448 px frame only for pitches 6-25 (y 175 down to 6). At the default 26 it sits at y=-4, just above the frame, so _draw_horizon draws nothing and the readout says 'horizon above the frame'. The same holds for every pitch from 26 to 48. A first-time user at the default sees no line, is told to click below one, and gets no direction cue. With PITCH_BAND's floor of 6, the horizon also can never sit lower than y≈175, so a photo whose eye line is mid-frame cannot be matched. The band's lower limit may be deliberate: PLAN notes low-pitch unsoundness in frame_floor.

- **How to hit it:** Open an image in Trace at the default pitch.
- **Evidence:** Computed cam.horizon_canvas_y(guide.make_camera(p, 3000, fov_x_deg=42)) for p in 6..48: 20 of 43 are inside 0..447, the default 26 gives -4. backdrop.py:377 returns without drawing when the horizon is off-frame. Every trace snap reads '26° · horizon above the frame'.
- **Fix:** When off-frame, say how far ('horizon 4 px above the frame') and draw a ghost tick or arrow at the top edge. Reword the empty-state teach so it does not presume a visible line. Optionally lower the default pitch so the line starts visible.

#### T28 — Disabled ToolStrip segments (#railSeg) are pixel-identical to enabled ones
`ff9mapkit/ff9mapkit/workspace/style.py:822` · minor · a11y · effort S

Before an image is open, tracedoc disables the Cut-outs and Regions segments (tracedoc.py:384-385), and Place disables both of its tools on refusal. ToolStrip segments reuse the #railSeg QSS, which has no :disabled rule. The generic QToolButton:disabled rule could not help anyway: it sets color $muted, the same colour an enabled UNCHECKED rail segment already uses. So a disabled segment looks exactly like a clickable one, and clicking it does nothing with no explanation. The reporter's suggested '$disabled_fg' token does not exist in style.py, so the fix must pick a colour distinct from $muted.

- **How to hit it:** Open the Trace tab before opening an image and click Cut-outs or Regions.
- **Evidence:** Read the reporter's toolstrip_bare_vs_traced.png: the Cut-outs and Regions segments are identical in the bare (disabled) and traced (enabled) rows. style.py:822-838 has no #railSeg:disabled rule. style.py:255 QToolButton:disabled uses $muted, the same as #railSeg's resting colour at 823.
- **Fix:** Add 'QToolButton#railSeg:disabled { color: $text_subtle; background: transparent; }' (an existing dimmer token), placed after :checked, or scope it to the ToolStrip. Give the disabled segments a tooltip such as 'Open an image first'. Verify by pixel diff of the bare and traced snaps.

#### T29 — Trace Regions tool hides the traced floor polygon, so doors are placed without the walkable edge
`ff9mapkit/ff9mapkit/workspace/backdrop.py:848` · minor · ux · effort S

_draw_trace returns early unless trace or contact mode is on. Contact mode deliberately keeps the polygon visible but inert (per the set_contact_mode docstring), but region mode drops the floor outline, its vertex dots and the +48u outset ring entirely. A gateway is meant to sit at the walkable edge, which the author now has to remember or read off the photo. Nothing in the docs or tests records this as intended; it looks like an omission from the contact-mode carve-out.

- **How to hit it:** Trace: trace a floor, then switch to Regions. The outline disappears.
- **Evidence:** Code read: backdrop.py:846-849. Viewed review-ctp/mist-100/trace-regions-canvas_mist_100.png: no cyan floor polygon or outset ring, while trace-traced shows them.
- **Fix:** Change the guard to 'self._trace_mode or self._contact_mode or self._region_mode'. Handles are already non-grabbable outside trace mode (mark_grabbable is gated on _trace_mode), and press resolution for vertices is gated on _trace_mode.

#### T30 — Generate does nothing, silently, while another job is running
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:865` · minor · ux · effort S

run_job returns False and starts nothing when a QProcess is already running (shell.py:9325-9326). on_generate handles only 'if started:' and has no else branch, so the click produces no status change, toast or console line. By then any placed snip has already been composed and written beside the photo (_composed_fg_path is called while the argv is built). The World tab's teleport handles the same refusal with a status message (shell.py:9366).

- **How to hit it:** Start a long Build or Deploy > switch to Trace > click Generate > nothing happens.
- **Evidence:** My probe /v-trace-tab/p_doc.py with run returning False: 'status changed: False | project: None'. I read shell.py:9318-9326 and tracedoc.py:856-869.
- **Fix:** else: self._refresh('Another job is running — Generate after it finishes.', 'warn').

#### T31 — Trace's event-message box is unlabeled, capped at 180 px, shows the text's tail, and its tooltip wrongly says the words are not in the file
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:177` · minor · ux · effort S

With Regions + Event active, the next zone's message is a bare QLineEdit pre-filled with '...'. It has setMaximumWidth(180), no label or placeholder, and sits right after the 'Event' radio. After programmatic text it shows the tail of the line, ':reaks underfoot.' in the mist-100 regions snap. Its tooltip says 'the words live in this session, not in the file'. That is false: Generate passes each message through --event-zone into the generated field.toml's [[event]] (imagefield.py:1099-1100) and also records it in the .trace.json sidecar (tracedoc.py:899). Leaving the '...' default ships a literal ellipsis popup.

- **How to hit it:** Trace > Regions > Event: look at the message box before drawing.
- **Evidence:** tracedoc.py:177-183, 666 (message captured at draw), 849 (--event-zone argv), 899 (sidecar); imagefield.py:1099-1100 (emitted into [[event]]). A crop of mist-100/trace-regions_mist_100.png shows the box reading ':reaks underfoot.'.
- **Fix:** Add a 'Message' label buddy and a placeholder in place of the '...' default (keep the build-time fallback). Raise or drop the max width. Call setCursorPosition(0) after setText. Reword the tooltip: the words are written into the generated project and kept in its .trace.json.

#### T32 — The cut-outs combo crams 4-5 facts into one entry and truncates the PNG/needs-PNG state
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:430` · minor · appearance · effort S

Each cut-out entry reads 'fg{i} @ (cx,cy) · z N · <png name> · snip'. The combo has a 260 px minimum and does not stretch (the fg row ends in addStretch), so the closed combo cuts the text with no ellipsis. At 100% it ends 'pillar_snip.|'. The two facts the user most needs, which PNG is attached or '⚠ needs its PNG', and snip vs full-frame, come last and are the first to go. The contact pixel and z are also already on the canvas label.

- **How to hit it:** Trace > Cut-outs: mark a contact and attach a PNG.
- **Evidence:** A crop of mist-100/trace-contacts_mist_100.png shows 'fg0 @ (230,320) · z 1073 · pillar_snip.|' with empty space to the right of the row. Code tracedoc.py:204 (setMinimumWidth 260), 222 (stretch), 430-435 (entry text order).
- **Fix:** Lead with the state ('fg0 · pillar_snip.png · snip' or 'fg0 · ⚠ needs its PNG'). Move the pixel and z to each item's tooltip. Give the combo stretch (addWidget(fg_box, 1)) and setSizeAdjustPolicy, or set ElideMiddle on its view.

#### T39 — Trace's 'Load <open field>' offer does not follow tree selection while the Trace tab is showing
`ff9mapkit/ff9mapkit/workspace/shell.py:4865` · minor · ux · effort S

_on_select live-feeds Behavior, Cutscene and Place when they are the current tab, but has no branch for Trace. offer_project is called only from _on_tab_changed (shell.py:5001-5005). Selecting a campaign member row while Trace is showing does not leave the tab: _open_editor mounts the form without setCurrentWidget. So the offer button keeps naming, and on click loads, the previously selected field, and a pristine tab does not auto-load the newly selected project. The impact is small: the label names the field, and switching tabs away and back refreshes it.

- **How to hit it:** Open a campaign > show the Trace tab > select a different member in the tree > the offer button still names the earlier member.
- **Evidence:** I read shell.py:4862-4882 (only behavior_doc, cutscene_doc and place_doc are fed), 5001-5005 (the only offer_project call), 5093-5102 (_behavior_target follows the tree selection) and _open_editor at 5668 (no tab switch). I did not build a two-member campaign for a live probe; the code path is unambiguous.
- **Fix:** Add the same live-follow branch: if self.tabs.currentWidget() is self.trace_doc, call trace_doc.offer_project(self.member_paths.get(self._behavior_target())).

### Shared canvas (Place + Trace)

#### V1 — A cut-out PNG named '@2x' previews at half size (main Trace and Place art are immune)
`ff9mapkit/ff9mapkit/workspace/backdrop.py:461` · minor · bug · effort S · narrower than first reported

BackdropCanvas scales pixmaps with QTransform.fromScale(w/pm.width(), h/pm.height()). A QPixmap loaded from a file named 'x@2x.png' gets devicePixelRatio 2, so its item is drawn at half the logical size. The mechanism is real, but the claim overstates where it reaches. The main Trace art goes through PIL cover-crop and then QPixmap.loadFromData (tracedoc.py:504-516), which never applies the @2x rule. Place art always comes from app-named files ('.place_backdrop.png' and 'real_<id>_cam<n>.png', placedoc.py:340/365). So the backdrop path at line 353 is unreachable with DPR 2, and no traced vertex is ever misregistered against the main art. The reachable case is a user-attached cut-out PNG whose filename ends in '@2x' (tracedoc.py:328 QPixmap(str(path))). A snip previews at half its rect, and a registered full-frame cut-out fills a quarter of the frame. Its base then no longer sits on the contact anchor, which is computed from the PIL size. The build uses the real file size, so the user positions the snip against a wrong-size preview, and the saved offset is off relative to what ships.

- **How to hit it:** Trace > Cut-outs: mark a contact, then attach a PNG whose name ends in '@2x.png'. The snip or full-frame overlay previews at half or quarter size.
- **Evidence:** Re-ran backdrop-code/probe4.py on the native platform: 'room@2x.png dpr 2.0 -> art scene rect (0,0,192,224)' and 'snip @2x rect want (40,300,60,50) got (40,300,30,25)'. The probe is valid for the canvas, but it feeds set_backdrop a file-loaded pixmap, which no host does. Code read: tracedoc.load_image uses loadFromData (DPR 1); placedoc builds the backdrop paths itself; only tracedoc._attach_cutout loads a user-named file.
- **Fix:** In tracedoc._attach_cutout, call f['pm'].setDevicePixelRatio(1) after loading (or load via QImageReader/PIL). Defensively, also scale by item.boundingRect() in backdrop.py:353/457/461. Add a fence that attaches a '@2x' file.

#### V2 — The backdrop hint pill drifts off its corner after any scroll/pan (no scrollContentsBy re-pin)
`ff9mapkit/ff9mapkit/workspace/backdrop.py:1072` · minor · appearance · effort S

The '_hint' and '_coords' labels are child widgets of the viewport. QGraphicsView scrolls by QWidget::scroll on the viewport, which moves those children, and BackdropCanvas re-pins them only in resizeEvent, _style_hint and _update_coords. After a scrollbar move or a hand-drag pan of a zoomed view, the pill slides with the content, up to the opposite corner. It snaps back on the next resize or vertex drag. floorplandoc.py:949 already fixed the identical bug with a scrollContentsBy override and a comment recording the owner-visible symptom. behaviordoc.StageCanvas (the Cutscene stage) creates the same viewport-child labels and has no scrollContentsBy either. I did not probe it, but it uses the same pattern. The pill is mouse-transparent, so the effect is visual: it ends up covering arbitrary art.

- **How to hit it:** Trace or Place canvas: Ctrl+scroll in until scrollbars appear, then drag-pan. The 'Ctrl+scroll zooms...' pill travels with the art.
- **Evidence:** Re-ran backdrop-code/probe1.py (native, WA_DontShowOnScreen, 641x561 and 640x560). 'after scroll to max ... hint=(62,61) want=(377,518)' and 'hint=(60,61) want=(376,517)'. Setting the scrollbar value is exactly what ScrollHandDrag does, so the probe is valid. grep: scrollContentsBy exists only in floorplandoc.py.
- **Fix:** Port floorplandoc's override: def scrollContentsBy(self, dx, dy): super().scrollContentsBy(dx, dy); self._place_hint(). Do the same in behaviordoc.StageCanvas. Fence it with a viewport-event pan at odd and even widths.

#### V3 — A drag whose left-release is lost keeps following buttonless hover and commits on the next click
`ff9mapkit/ff9mapkit/workspace/backdrop.py:1151` · minor · bug · effort S · narrower than first reported

mouseMoveEvent drives any live _drag without checking event.buttons(), and only a LeftButton release ends it. The viewport has mouse tracking on (AnchorUnderMouse enables it; see the workspace SKILL), so buttonless moves really are delivered. If the left release is lost, for example by right-clicking a vertex mid-drag (which opens the modal 'Delete vertex' QMenu) and dismissing the menu, the vertex keeps following the cursor with the coords chip up. The next ordinary click then commits it at that stray spot through on_floor, which is undoable. The region sub-claim does not hold with the real hosts. Rotating a region via the right-click menu mid-drag emits region_changed, and both tracedoc._on_region_changed and placedoc._on_region_changed synchronously re-feed set_regions. That runs _rebuild, which clears _drag, so the later release cannot emit an unrotated overwrite. The overwrite only appears on a bare canvas with no host. The trigger (right-click while holding left, or a focus steal mid-drag) is rare.

- **How to hit it:** Trace Floor tool: press on a vertex, drag, right-click while still holding left, Esc the menu, release, then move the mouse. The vertex follows; clicking elsewhere commits it there.
- **Evidence:** Re-ran probe2.py section A on the native platform: 'after a BUTTONLESS move: drag still live = True' and 'next click elsewhere committed: (216.4, 300.2) (vertex 0 was (150,250))'. My own probe v-canvas/pE.py (rotate emitted mid corner-drag, no host) gave 2 emissions, the second unrotated. Code read shows both hosts call _refresh_regions -> set_regions -> _rebuild (_drag=None) on region_changed, so a real host never sees the second emission. The lost release under a real QMenu grab was not reproduced headless.
- **Fix:** In mouseMoveEvent, if self._drag and not (event.buttons() & Qt.LeftButton), cancel the drag (restore it via _rebuild). Ignore contextMenuEvent while _drag is set. Optionally cancel on focusOutEvent.

#### V5 — Ctrl+wheel zoom ignores the delta magnitude, and a horizontal (y=0) Ctrl+wheel zooms out
`ff9mapkit/ff9mapkit/workspace/backdrop.py:1078` · minor · bug · effort S

Each Ctrl+wheel event applies a full 1.15x step regardless of angleDelta size. A hi-res wheel or precision touchpad that splits one 120 detent into many small deltas zooms about 3x per detent instead of 1.15x. A Ctrl+wheel event with angleDelta().y()==0 (tilt wheel or sideways swipe) fails the '> 0' test and zooms out. The same three-line block is copied in floorplandoc.py:975, behaviordoc.py:314 and mapview.py:612. There is no shared helper; it is four copies.

- **How to hit it:** Ctrl + two-finger scroll on a precision touchpad over the Trace/Place/Cutscene canvas, or Ctrl + tilt-wheel.
- **Evidence:** probe1.py rerun (QWheelEvent sent to the viewport, a valid emulation): 'ctrl + 8x15: zoom 1.0261 -> 3.1389 (x3.059)' and 'ctrl + HORIZONTAL wheel: zoom 1.1800 -> 1.0261'. grep confirms the identical code in the three other views.
- **Fix:** dy = event.angleDelta().y(); if dy == 0: accept and return; f = 1.15 ** (dy / 120). Ideally hoist it into one helper used by all four views.

#### V6 — Snips and contact diamonds show the Move cursor in Trace's Regions tool, where a press does not drag them
`ff9mapkit/ff9mapkit/workspace/backdrop.py:467` · minor · ux · effort S

mark_grabbable is applied to every unlocked snip (line 467) and every contact glyph (line 485) in every mode, but press resolution drags them only in trace or contact mode (line 1122). In the Trace tab's Regions tool, hovering an attached snip or its contact diamond shows SizeAll, while a press pans, starts a region-corner click, or grabs an underlying quad. Place never feeds cut-outs (set_cutouts is called only by tracedoc), so the reachable case is Trace > Regions alone, not 'any place-mode host'. The vertex dots already gate their cursor on _trace_mode.

- **How to hit it:** Trace: attach a snip, switch to Regions, hover the snip (Move cursor), drag. It pans or places a corner instead.
- **Evidence:** probe2.py section F rerun: cutoutimg and cutoutpt-child cursors are SizeAllCursor in region mode; 'press on the snip in region mode -> drag armed: False', 'cutout_moved: []'. grep: set_cutouts is called only in tracedoc.py:463/526.
- **Fix:** Wrap both mark_grabbable calls in 'if self._trace_mode or self._contact_mode', matching the press gate.

#### V8 — Esc does not abort a live vertex/corner/snip drag (the double-click half is mostly harmless)
`ff9mapkit/ff9mapkit/workspace/backdrop.py:1087` · minor · ux · effort S · narrower than first reported

keyPressEvent handles Esc only for a pending region quad. During a vertex, corner, quad, snip or contact drag, Esc does nothing and the release still commits, so the only way back is Undo. That half is confirmed. The double-click half is overstated. QGraphicsView's mouseDoubleClickEvent does not route through mousePressEvent, so a press/release/dblclick/release sequence yields one vertex. But Qt raises a DblClick only when the second press lands within the platform double-click distance (a few px) and interval. Two quick clicks on different vertex or corner positions, which are normally far apart, are not merged. The dropped click is a near-duplicate point within ~5px, arguably a de-duplication rather than a lost vertex.

- **How to hit it:** Trace: start dragging a vertex, press Esc, release. The move is committed anyway.
- **Evidence:** probe2.py rerun. Section B: 'drag still live after Esc: True', 'commits after Esc+release: 1'. Section C: 'vertices after press/release/dblclick/release: 1', with the second click only 3px from the first, which is the only geometry that produces a DblClick.
- **Fix:** In keyPressEvent: if Esc and self._drag, set _drag=None, hide the coords chip, _rebuild() (restores the start state), and accept. Leave the double-click alone, or treat a DblClick as a press only if testing shows real loss.

#### V10 — A whole-quad drag that tracedoc refuses (corner behind the camera) leaves the un-accepted quad drawn
`ff9mapkit/ff9mapkit/workspace/backdrop.py:985` · minor · bug · effort S · narrower than first reported

After a changed corner or quad drag, _end_vertex_drag emits region_changed and does not rebuild, relying on the host to re-feed. tracedoc._on_region_changed returns early without _refresh_regions when world_to_click raises. This happens when a whole-quad drag moves a deep zone far enough toward the camera that its near corners go behind the camera plane. The canvas then keeps the moved, never-accepted polygon and handles, with no status message, while the document holds the old quad. Its law overlays stay hidden if it had any. The extension to snip and contact drags does not hold: tracedoc._on_cutout_moved and _on_contact_moved always refresh for reachable inputs, and placedoc's handler always refreshes.

- **How to hit it:** Trace > Regions: drag a long zone by its far end down to the bottom of the frame and release. The quad stays drawn where it was dropped, but the document did not change.
- **Evidence:** v-canvas/p10.py (native): a 2100-unit-deep event zone grabbed near its far edge and dragged to the frame bottom emitted [(-302,-3649),(298,-3649),(298,-1549),(-302,-1549)]. world_to_click REFUSED the two near corners ('at/behind the camera plane'), which is exactly tracedoc.py:681-682's silent return path. Code read of the other handlers.
- **Fix:** Always _rebuild() after emitting region_changed (a host that accepts re-feeds anyway), and/or make tracedoc refuse with _refresh_regions() plus a status message instead of a bare return.

#### V13 — An invalid trace vertex differs from a good one only by colour; region-law detail is tooltip-only
`ff9mapkit/ff9mapkit/workspace/backdrop.py:865` · minor · a11y · effort S · narrower than first reported

A vertex above the horizon is drawn with the same dot and index label as a valid one, differing only in colour (error vs accent), and its reason is a hover tooltip. The DEAD ZONE / OVER-TRIGGER percentages exist only as tooltips on the painted hatch and wash, and Place's status literally says '(hover a marked quad)'. Some non-colour cues do exist. Tracedoc's status line counts 'N above the horizon (red)' and gates Generate with a tooltip, and warned regions carry a '⚠' glyph in their label and an '⚠ N with law warnings' status count. The status line just never says which vertex or what the law detail is. The '<1.6:1 on the tan floor' figure depends on the user's photo and cannot be checked as a general claim. The canvas has no keyboard operation at all, so the practical beneficiary is a colour-vision-deficient mouse user.

- **How to hit it:** Trace: pitch the camera so one vertex goes above the horizon. Only its red colour marks it.
- **Evidence:** Code read: backdrop.py:865-884 (colour-only bad vertex plus tooltip), 595-609 (gap/spill tooltips), 650 ('⚠ ' label prefix for warned regions), tracedoc.py:394-411 (status counts), placedoc.py:897 ('hover a marked quad').
- **Fix:** Draw a bad vertex hollow or with an ✕ and suffix its label ('3 ✕'). Have the status line name the offending vertex indices. Mirror the selected or warned region's law text into the status line instead of 'hover a marked quad'.

## 7. Improvements, documentation and test fences

### Cutscene tab

#### C30 — S5 tutorial ignores the seeded 'A new scene.' step; its figure hides the ladder and shows elided buttons
`ff9mapkit/docs/tutorials/s5-cutscene-and-music.md:49` · minor · docs · effort S

The tutorial says to press Add a scene, then 'Build a three-step narration: press ＋ Step…'. Add a scene mints {say = 'A new scene.'} (cutscenescan._SCENE_MINT, line 550), so following the steps gives four steps, with the placeholder line first, and it ships in-game unless the author notices it. The embedded figure (docsite/assets/shots/editor-cutscene_light.png, captioned 'the scene rail, the step ladder, and the step editor open') shows no ladder rows, because the editor is centred over them (C18). Its bar reads '+ St…' and 'Sce…' (C17) while the text says to press '＋ Step'.

- **How to hit it:** A newcomer following S5 step 1.
- **Evidence:** Read s5 lines 49-60 and cutscenescan.py:550. Read the figure PNG: header 'Step 2 — edit', no ladder rows, '+ St…', '⧉ Sce…', rail clipped.
- **Fix:** Tell the reader the new scene starts with one placeholder line and to rewrite it first (pencil on row 0), so the build is that line plus two more. Alternatively, have Add a scene open the editor on the seeded step. Re-take the figure after the C17/C18 fixes.

#### C33 — The tab never explains how to see a gated or play-once scene in game
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1040` · minor · improvement · effort S · needs a playtest to settle

A scene with 'Requires beat'/'Requires flag' plays only when the save's story state matches, and a 'Play once' scene hides after its first viewing. Nothing in the tab says how to reach either state. The header just says 'plays at beat 100'. No string in cutscenedoc.py mentions the ~ debug menu, reloading or retesting. The minted scene is ungated, so the S5 happy path is not affected (S5 also explains a redeploy resets the once-flag), and tutorial 08:108 mentions '~ → Flags' for retesting. But an author who adds a gate gets no guidance in the tab, and 'deployed, walked in, nothing happened' is the likely result. A one-line caption is cheap and worth it. Caveat: before naming a lever in the caption, verify which debug-menu path can actually set the ScenarioCounter; that was not verified here.

- **How to hit it:** Set Requires beat = 100 on a scene, deploy, walk in on a save at a different story point.
- **Evidence:** Grepped cutscenedoc.py for '~', 'Flags', 'Reload', 'debug': none. Read s5:66-71 (redeploy resets the once-flag) and 08-dialogue-cutscene.md:108 ('retest with ~ → Flags'). gate_text (cutscenescan.py:158-167) is the only gate surface.
- **Fix:** When the selected scene is gated or once, show a muted caption under the scene bar naming how to reach it in game (the debug-menu lever that sets the story point or flag, then ~ → Reload field). Confirm the exact lever in game first.

#### C34 — No facing indicator for turn steps; the cast is free text (but typos ARE flagged live)
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:177` · minor · improvement · effort M · narrower than first reported · needs a playtest to settle

The premise is partly true. A 'turn 128' step is a raw 0-255 facing byte with no stage representation: stage_model and the storyboard draw positions and legs only, so a turn beat changes nothing on the canvas. The Settings Cast is a plain STRLIST line edit with no catalog picker. The claim that a cast typo surfaces 'only after a staging run' is wrong: cutscenescan.scene_problems (lines 279-289), which runs in the always-on PROBLEMS lane on every render, flags 'cast member "X" is not an [[npc]] on this field' and 'step i actor "X" is not in the cast' immediately after Apply. A facing tick and a cast picker are reasonable improvements. A 'pick the turn on the stage' tool needs the camera-yaw/facing-byte frame (the laying-out skill's trap), so it is medium effort and needs an in-game check.

- **How to hit it:** Author a turn step; type a misspelled cast name in Settings.
- **Evidence:** Read cutscenescan.scene_problems (259-289): live unknown-cast and unknown-actor checks. CutsceneStage drawing (cutscenedoc.py:150-215): no facing glyph. CUTSCENE_SPEC 'actors' is STRLIST with no catalog (forms.py:260).
- **Fix:** Draw a short facing tick on cast markers (end-of-beat facing in storyboard mode) using the kit's facing-byte to world convention, and give Cast a catalog picker of [[npc]] names plus 'player' via the existing pick seam. A stage pick for turn angles comes later and needs a playtest to confirm the direction convention.

### Place tab

#### P8 — Verbatim forks: the donor's own tread regions are invisible to Place's overlap judge
`ff9mapkit/ff9mapkit/workspace/placedoc.py:162` · minor · improvement · effort M · narrower than first reported · needs a playtest to settle

region_rows (and build.region_overlap_pairs behind it) judge only the [[gateway]]/[[event]] rows in field.toml. On a VERBATIM fork the donor's real exits live only in the whole .eb, and _inject_verbatim_gateways adds the kit's new gateways below the party band, so a door drawn over a real exit gets no 'overlaps' warning on the canvas (nor from the lint, which uses the same judge). The claim overreaches for native, editable and BG-borrow forks: the importer (extract.py:622-650) writes the donor's scanned exits into field.toml as [[gateway]] rows, so those forks DO show and judge them. The gap is verbatim-only. It is a kit-wide judge limitation, not something only Place gets wrong.

- **How to hit it:** Open a verbatim fork, Place > Load the room > Regions, draw a gateway over the donor's real door: no overlap warning.
- **Evidence:** Read placedoc.region_rows:162-215, build.region_overlap_pairs:3944 (it reads only the raw dict), build._inject_verbatim_gateways:7065. extract.py:622-650 emits [[gateway]] blocks for non-verbatim imports. eb/pressclosure.analyze_regions:834 and guest_traversal.tread_regions:1241 exist as decoders.
- **Fix:** Decode the donor .eb's tread regions once per load (analyze_regions over cache_field's .eb). Feed them to the canvas as greyed, read-only rows and to the overlap judge as extra boxes. Put that in the shared judge so the lint benefits too. Verbatim-only.

#### P26 — The Place tab has no user documentation beyond one sentence
`ff9mapkit/docs/tutorials/s3-gateways.md:69` · minor · docs · effort S

The only user-facing mention of the Place tab in ff9mapkit/docs or docsite is one paragraph in S3 Gateways: the tab's Regions tool is 'the visual route (no separate tutorial yet...)'. docsite/pages/what-can-i-do.md has no Place entry. Load the room, the verbatim spawn/arrival refusal, the stacked-floor menu, the walk-out edge (corners 0→1), the right-click rotate/retarget/reword/delete, Esc to cancel, the overlap and dead-zone warnings, and Undo are recorded only in studies/click-authoring/PLAN.md, which is not user documentation.

- **How to hit it:** A user looking for how to use Author > Place.
- **Evidence:** Case-insensitive grep over ff9mapkit/docs, docsite and ff9mapkit/README.md for 'Place tab|Load the room|Regions tool' returned only s3-gateways.md:69-71.
- **Fix:** Add a short 'Place content on the art' tutorial page: Load, the four modes, Regions gestures, refusals and warnings. Link it from what-can-i-do.md and from the S3 note.

#### P27 — A drawn gateway with no target, or a drawn event, could prompt immediately via the existing dialog seams
`ff9mapkit/ff9mapkit/workspace/placedoc.py:701` · minor · improvement · effort S

_on_region_drawn writes a gateway with to=0 when the 'to field' spinner shows its '?' special value, and writes every event with message '...'. Both are then flagged on the canvas (Field(0) black screen / literal '...' popup), and the fix takes a right-click > Set gateway target / Set message. This is the DEFAULT-VALUE LAW's 'loudly invalid' option working as designed, so it is not a bug. But the instance dialogs _ask_field_id and _ask_message already exist behind test seams. Calling them right after the draw, only when to == 0 or for an event, with cancel keeping today's placeholder, removes a two-step repair from the most common Regions flow. Trace already captures the event text up front (ev_msg box), so prompting is consistent with the sibling tab.

- **How to hit it:** Place > Regions: draw a gateway without first setting 'to field'.
- **Evidence:** placedoc.py:701-714 (to=0 only appends a hint to the note), 736-792 (dialog seams), 199-205 (the warnings). tracedoc.py:177 captures the message before the draw.
- **Fix:** In _on_region_drawn: if gateway and to == 0, call _ask_field_id(0) and, if accepted, set_gateway_target in the SAME undo step (one on_edit). For an event, call _ask_message(''). Cancel keeps the current behaviour.

### Trace tab

#### E16 — The first-Generate hand-off test does not cover a real retry after a failure
`ff9mapkit/tests/test_workspace_tracedoc.py:849` · minor · test-gap · effort S · found while verifying

test_first_generate_hands_the_project_to_the_shell_once calls kw['on_finished'](1) and then kw['on_finished'](0) on the SAME launch's callback. A real user retries with a second on_generate, which captures first=False because _project was set when the first job started. The test therefore passes while the retry path never opens the project (see T8).

- **Evidence:** /v-trace-tab/p_doc.py: a failed first launch, then a second on_generate, then on_finished(0) with the toml present gives opened == [].
- **Fix:** Replace the double callback with: on_generate > on_finished(1) > on_generate > on_finished(0) > assert opened == [toml]. This fails today, which pins the T8 fix.

#### T19 — EXIF orientation ignored on photo ingest; 16-bit grey PNGs go white
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:508` · minor · improvement · effort S

load_image, build_image_field (imagefield.py:1046), auto_floor (:622) and write_trace_html (:828) all call Image.open(...).convert('RGB') without ImageOps.exif_transpose. A portrait phone JPEG stored landscape with Orientation=6 is traced and shipped sideways: the base art in-game is rotated relative to how every photo viewer shows it. Preview and build agree, so the geometry is self-consistent, and the author sees the rotation on the canvas before Generate. A 16-bit greyscale PNG (mode I;16) converts to solid white.

- **How to hit it:** Open a portrait phone photo in the Trace tab. It appears sideways.
- **Evidence:** probe_doc.py section 8: an 800x400 JPEG with Orientation=6 gives 'img_size (800, 400)'. Section 9: 'mode I;16 -> RGB pixel (255, 255, 255)'.
- **Fix:** Add one shared _open_rgb(path) in imagefield that applies ImageOps.exif_transpose and normalises I;16/I modes, and use it at all four ingest sites (the Qt pixmap load must use the same transposed image).

#### T33 — Trace has no 'Detect floor' seed though imagefield.auto_floor exists for exactly that
`ff9mapkit/ff9mapkit/imagefield.py:600` · minor · improvement · effort S · needs a playtest to settle

imagefield.auto_floor (numpy seeded region grow, refusal-biased, reasons point to the hand trace) is documented as 'a SEED the human refines in the tracer'. The retired HTML tracer was fed by `image-field --auto-floor --trace`. The project memory records the hallway lesson as 'the tracer seed IS the product': auto-floor cannot know where a field ends at a doorway, so its output is a starting polygon to drag. The Workspace Trace tab never calls auto_floor, so the GUI lost the seed the CLI tracer had and every user clicks the outline from scratch. PLAN's DRAWN-MESH LAW forbids the floorplan COMPOSER from inferring a mesh. It does not forbid a human-refined seed in Trace.

- **How to hit it:** Trace: open a photo of a room with a uniform floor.
- **Evidence:** grep finds no reference to auto_floor under workspace/. imagefield.py:600-615 docstring. Project memory project-ff9-image-to-field.md lines 114-130 (seed in the tracer, the hallway lesson). PLAN.md:429-434 (the law is about the composer).
- **Fix:** Add a 'Detect floor' button in the Floor cluster. It calls auto_floor(self._image, pitch=…, fov=self._fov, distance=self._distance) and commits the polygon (in canvas px) as ONE undoable on_floor gesture. An ImageFieldError goes to the status line as a warn. Disable it with a tooltip when numpy is missing. Off the GUI thread if it is slow.

#### T34 — Trace exposes no room-scale (distance) control or floor-size readout
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:79` · minor · improvement · effort S · narrower than first reported · needs a playtest to settle

The session owns _distance and _fov and passes them to the CLI (--distance/--fov). They are reset per new photo and restored on reopen, but the GUI shows them only as a readout when they differ from the default and offers no control. So an author cannot judge or change how large the traced floor will be relative to the party. The cheap, clearly valuable half is a status fragment with the traced floor's world bounding box (e.g. 'floor ≈ 2400×1800 u'). A distance spinner is more delicate: changing it rescales every un-projected vertex and contact, and a reopened project re-projects through it (the rung-7 'wrong camera' class), so it needs the same drift warning the pitch has.

- **How to hit it:** Trace a photo and wonder how big the room will be in-game.
- **Evidence:** tracedoc.py:79-80, 272-274 (_camera uses _distance/_fov), 347-352 (readout only when non-default). PLAN.md:691-696 records the session-owned distance/fov fix.
- **Fix:** First add the bounding-box readout from the trace's world points in _refresh. If a distance spin is added, re-feed set_backdrop(refit=False) as pitch does and reuse the _pitch_drift_note pattern for a reopened project.

#### T36 — No user doc covers the Trace tab, and the docsite 'picture' card points to a different workflow and overclaims
`docsite/pages/what-can-i-do.md:243` · minor · docs · effort S

The docsite card 'A field from a picture you painted' says 'trace the floor, let the kit solve the camera' and links Tutorial 03 (original-art field via `ff9mapkit new` plus guide painting with a chosen camera). Tutorial 03 never mentions image-field or the Trace tab, and Trace does not solve the camera: the user sets pitch by eye. Nothing under ff9mapkit/docs documents the Trace tab, cut-outs/contacts/snips, regions on a photo, the .trace.json reopen or the in-place Regenerate. ff9mapkit/README.md only lists `image-field` among commands.

- **How to hit it:** A user following the docsite card to make a field from a photo.
- **Evidence:** A case-insensitive grep over ff9mapkit/docs, docsite and README for 'Trace tab|image-field|trace.json' hits only README.md:67. Tutorial 03 mentions only 'trace-over' paint templates (line 39). Read what-can-i-do.md:243-249.
- **Fix:** Write a short 'A field from a photo — the Trace tab' tutorial (open, pitch, trace, cut-outs, regions, Generate, Deploy, reopen). Point the card at it and change 'solve the camera' to 'match the camera pitch'.

### Shared canvas (Place + Trace)

#### V12 — Backdrop tests are offscreen at one size and never exercise pan/zoom/fit, hint pinning, lost releases or DPR-2
`ff9mapkit/tests/test_workspace_backdrop.py:21` · minor · test-gap · effort M

test_workspace_backdrop.py sets QT_QPA_PLATFORM=offscreen and builds every canvas at 500x560. There is no test for Ctrl+wheel, Ctrl+0/Ctrl+1, fit-after-zoom, resize refit, hint position after scroll, buttonless-move drag termination, Esc mid-drag, double-click or a DPR-2 pixmap. The only Escape test covers the pending-region case. Every view-grammar defect confirmed in this batch (V2, V4, V5, V3, T24) passes the 36 green tests. The workspace SKILL itself requires odd/even parametrized view fences and at least one sendEvent-driven fence per canvas.

- **How to hit it:** n/a (test suite)
- **Evidence:** py -m pytest tests/test_workspace_backdrop.py -q -p no:cacheprovider -> '36 passed'. grep finds no wheel, Key_0, scroll, _fit or DPR assertions; the only Key_Escape is at line 585 (pending quad). The SKILL.md 'Parity is the gate' section mandates odd and even fences.
- **Fix:** Add a native WA_DontShowOnScreen fixture parametrized at (641,561)/(640,560) covering: pan -> hint geometry; zoom then Ctrl+0 equals the first fit; Ctrl+wheel 8x15 equals one 1.15 step; a buttonless move after a lost release does not move a vertex; Esc mid-drag restores.

#### V14 — Retheme/scale tests only check attribute assignment; several real states (horizon in frame, multi-cam, stacked chooser, drift) have no snap
`ff9mapkit/tests/test_workspace_tracedoc.py:178` · minor · test-gap · effort M

test_retheme_and_scale_reach_the_canvas asserts only 'doc.canvas.pal is doc.pal' and 'canvas._scale == 150'. It would stay green if _rebuild ignored the scale or the palette when painting labels. test_retheme_and_set_scale_survive_both_pages (test_cutscenedoc.py:773) checks the slider's minimum width and the crumb. gui_snap has no state for a horizon inside the frame. TRACE_STATES' docstring promises 'the bare canvas frame with its horizon', but the default 26° pitch puts the horizon above the frame: the snaps read '26° · horizon above the frame' and the horizon line and its label appear in no snap. There is also no multi-camera Place state, no stacked-floor _choose_hit, no pitch-drift/offer state and no Cutscene problems state.

- **How to hit it:** n/a (test and snap coverage)
- **Evidence:** Read test_workspace_tracedoc.py:178-183 and test_cutscenedoc.py:773-779. grep tools/gui_snap.py for cam_box/_choose_hit/unresolved/_pitch_drift/offer finds nothing. Snap mist-100/trace-contacts shows '26° · horizon above the frame'; probe5 shows horizon_canvas_y = -3.66 at 26°.
- **Fix:** After set_scale/retheme, assert a painted label item's font().pointSize() and brush colour. Add gui_snap states trace:horizon (pitch about 12) and place:multicam at least, and fix the TRACE_STATES 'bare' docstring.

## 8. Nits

### Cutscene tab

#### C13 — An add lane started at row 0 never re-enables 'Runs with the previous beat'
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1254` · nit · bug · effort S

_sync_with_prev runs only from _on_kind. When the add lane opens at row 0 (only when the scene has no steps), the checkbox is correctly disabled. After Apply advances insert_at to 1, the checkbox is never re-synced, so it stays disabled for a parallel-capable kind until the author toggles the step type. The case is narrow because a row-0 add lane needs an empty scene.

- **How to hit it:** Delete every step, press Add, Apply a turn at row 0, then try to tick with_prev for row 1.
- **Evidence:** Re-ran p11_editor_misc.py: 'add lane now at row 1 | with_prev enabled: False' for a turn. Grep: _sync_with_prev is called only at cutscenedoc.py:379, inside _on_kind.
- **Fix:** Call self.editor._sync_with_prev() after advancing insert_at in _apply_step's add branch.

#### C16 — The build reports a bad cutscene tail twice, once without the dispatch index
`ff9mapkit/ff9mapkit/build.py:9055` · nit · bug · effort S

For a cast scene in a [[cutscene]] dispatch, an invalid step tail produces two messages: one from the window-attribute sweep (build.py:3236, labelled '[cutscene] step 0', with no '#k' even when there are several blocks) and one from _validate_conductor (build.py:9054-9056, labelled '[cutscene] #0 step 0'). Check therefore shows a duplicate, and the sweep's label is ambiguous in a dispatch. The same missing-'#k' problem affects every other sweep message on cutscene steps, such as an unknown style.

- **How to hit it:** A dispatch whose cast scene has a say with tail = "XYZ": the Check output lists it twice.
- **Evidence:** p5_problems_parity.py 'bad tail code' BUILD: ["[cutscene] step 0 tail 'XYZ' is not a valid TAIL code (DEFT, ...)", "[cutscene] #0 step 0 tail 'XYZ' is not a valid TAIL code"]. Read the sweep at build.py:3230-3238, which labels f"[cutscene] step {_sk}" and ignores _ci.
- **Fix:** Drop the conductor's tail check (the sweep covers every text step), and have the sweep label '[cutscene] #k step n' when there are several blocks.

#### C25 — '− Scene' deletes immediately (undo-first by design); the real risk is the elided label
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:785` · nit · ux · effort S · narrower than first reported

The premise is true: '− Scene' runs _del_scene with no confirmation, next to '⧉ Scene'. But delete-without-confirm plus Ctrl+Z is this surface's deliberate contract. The tooltip says 'Ctrl+Z undoes; the file changes on Save, not now', the step ✕ follows the same rule, and the shell checkpoints the edit with the op's label (_on_cutscene_edit). Nothing is lost until Save. The part that is a real defect, both buttons reading 'Sce…', belongs to C17 and goes away with that fix. Adding a confirm dialog would contradict the house undo-first pattern. A status-bar note naming what was removed is the only worthwhile addition.

- **How to hit it:** Click '− Scene'.
- **Evidence:** probe_flows.py: '4. scenes before/after one click on - Scene: 2 1'. Code: tooltip at line 787. _on_cutscene_edit (shell.py ~5044) records a checkpoint. The step delete (line 597 tooltip 'Remove this step (Ctrl+Z undoes)') uses the same no-confirm, undo-backed idiom.
- **Fix:** Fix C17 (the labels). Optionally post a transient status message with the checkpoint label ('Deleted scene #0 (3 steps) — Ctrl+Z restores'). Do not add a modal confirm.

#### C26 — 'Pick on the stage' stays armed after the step kind changes away from walk or teleport
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:363` · nit · bug · effort S

_on_kind hides pick_btn for non-movement kinds but never disarms the host's one-shot stage pick. The canvas stays in sim-click mode, and the next click on the stage writes 'x, z' into the now-hidden value line. That stale coordinate then appears if the author switches to another line-valued kind, for example Wait shows '123, 457', and an Apply would fail or carry it.

- **How to hit it:** Step editor on a walk: Pick on the stage, change Type to Say without clicking the stage, then click the stage later (for example to pan or select).
- **Evidence:** My probe v-cutscene-bugs/pick.py, using public gestures (kind combo plus pick_btn.click()): 'armed: True', after switching to say 'armed: True pick visible-flag: False', and after a stage click 'hidden value_line now: '123, 457''; switching to wait shows '123, 457'.
- **Fix:** Add an on_kind_changed hook so the host can call _disarm_stage_pick when the new kind is not walk or teleport. Optionally show an 'armed' state on the button.

#### C27 — '+speaker' extras chip hides the speaker's name and reads like an add button
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:625` · nit · ux · effort S

A step with extra keys shows a right-aligned info chip '+speaker' (or '+speaker, tail'). The ladder shows an actor chip only for `actor`, so a conversation authored with `speaker` never shows who is talking in the ladder. The chip only names the key, behind a '+' that reads like an action. It is passive and does nothing on click. The useful half (the name) is worth surfacing.

- **How to hit it:** Any say step that has speaker = '…'.
- **Evidence:** Read mist-100/cutscene-doc-pane: row 2 'say Made it to the altar.' with a '+speaker' pill in the same slot as '‖ with previous'. Code lines 609-627.
- **Fix:** Show the speaker as the row's name chip (e.g. 'Cid' in the actor slot, with distinct styling if an actor is also set) and the remaining extras as a muted caption without the '+'.

#### C28 — '(no line this beat)' placeholder is the loudest text in the storyboard strip
`ff9mapkit/ff9mapkit/workspace/cutscenedoc.py:1432` · nit · appearance · effort S

board_say is a mono QLabel. On a beat with no say line it shows '(no line this beat)' at full label size in heavy monospace, visually heavier than the scene title, while the explanatory ledger below is a small caption. An empty-state placeholder should be quiet.

- **How to hit it:** ▶ Storyboard on a scene whose first beat is a walk.
- **Evidence:** Read mist-150/cutscene-storyboard_mist_150.png: '(no line this beat)' in large bold mono under the slider dominates 'scene #0'. Code line 1432 sets the text with no state or role change.
- **Fix:** When b['say'] is None, set the caption role or a muted state on board_say (and restore it for a real line), or hide board_say and show the placeholder in the ledger line.

#### C29 — Some engine identifiers in Settings help and an ambiguous 'run Check'
`ff9mapkit/ff9mapkit/editor/forms.py:260` · nit · ux · effort S · narrower than first reported

The premise is true: the front door says "Cutscene stages a field's [[cutscene]] scenes", the CUTSCENE_SPEC help says 'the DIRECTOR GATE: only plays when the ScenarioCounter == this beat', 'the DIRECTOR ADVANCE' and 'pin THIS gEventGlobal bit', and the staging summary says '(unresolved names — run Check)' right beside a button titled 'Check the staging'. Only part of it is worth changing. TOML block names such as [[npc]] and [[cutscene]] are the kit's shared vocabulary across docs, the 'Open the .toml' door and the Editor tree. CUTSCENE_SPEC is also the Editor tab's form for the same block, so it is not a first-time-only path. The worthwhile changes: rewrite the ScenarioCounter/gEventGlobal/DIRECTOR help into plain words, keeping the engine term second or in the '?' badge, and make 'run Check' name the toolbar Check, which is a different action from Check the staging.

- **How to hit it:** Open Scene settings; or run Check the staging on a scene with a typo'd marker.
- **Evidence:** Read forms.py:259-279 and cutscenescan.py:58 ('NOT checked (unresolved names — run Check)'). The instrument column's button reads 'Check the staging' (cutscenedoc.py:914). The toolbar has a separate 'Check' (visible in snaps).
- **Fix:** Plain-language help ('only plays once the story has reached this point (number or area name); blank = always'), with the engine name as a second line or in the badge. Change 'run Check' to 'run the toolbar Check'. Leave the [[block]] names.

#### C32 — First-run banner says 'Your fork is ready' for any field, including a from-scratch one
`ff9mapkit/ff9mapkit/workspace/shell.py:8367` · nit · ux · effort S

The first-run spine message is hardcoded as 'Your fork is ready — press Deploy to put it in your game.' whenever prefs.has_deployed() is false, whatever the member's origin. A standalone authored field (the status bar says 'GLEN — standalone field') is described as a fork.

- **How to hit it:** First launch, open or create a loose field without forking.
- **Evidence:** Read shell.py:8363-8367: no branch on origin. Every cutscene window snap shows the banner beside 'GLEN — standalone field'. No test or doc pins the string (grepped tests/, docs, docsite).
- **Fix:** Say 'Your field is ready — press Deploy…' (true for both cases), or branch on whether the member came from import/fork.

#### C37 — Rowtools are 20-23px tall (below the house 24px floor); boundary ↑/↓ are enabled no-ops
`ff9mapkit/ff9mapkit/workspace/style.py:183` · nit · a11y · effort S · narrower than first reported

Measured natively at 100%, the five per-row tools are 21x23, 28x23, 29x23 and 34x20 (the pencil), below the 24px floor that test_workspace_a11y.py:110 enforces for stock controls. That fence never measures role=rowtool. ↑ on row 0 and ↓ on the last row are enabled but silently return (cutscenedoc.py:1271), which wastes a tab stop. The 'WCAG 2.5.8 violation' framing is overstated: 2.5.8 has a spacing exception, and with 7px row spacing between tool centres (≥28px apart) a 24px circle around each target does not overlap its neighbours. So this is a house-rule miss, not a WCAG failure.

- **How to hit it:** Mouse or keyboard use of the ladder row tools.
- **Evidence:** probe_kb.py: 'rowtools 15 sizes [(21, 23), (28, 23), (29, 23), (34, 20)]', 'up on step0 enabled: True'. style.py:183/190 rowtool_pad '1px 6px' and '0px 5px'. The test at test_workspace_a11y.py:110-130 builds only stock controls.
- **Fix:** Add min-height: 24px; min-width: 24px to QPushButton[role="rowtool"] (this also covers the behavior ladder, which shares the role). Disable ↑ on row 0 and ↓ on the last row in StepLadder._row, which needs the row count. Add a rowtool button to the target-size fence.

### Place tab

#### E8 — Regions status reads 'draw a event zone' and teaches the gateway walk-out edge in Event mode; rotate is undone as 'reshape gateway zone'
`ff9mapkit/ff9mapkit/workspace/placedoc.py:894` · nit · ux · effort S · found in the explore pass

The status line builds 'Click 4 corners to draw a {kind} zone', which gives 'a event'. It always appends 'corners 0→1 = a gateway's walk-out edge', even while drawing events. The walk-out rotate goes through move_zone, so its undo and redo label is the generic 'reshape gateway zone', the same as a corner drag or a body drag.

- **How to hit it:** Place → Regions → Event; or right-click a gateway → Walk-out edge → read the Undo label
- **Evidence:** Probe probes/x-cutscene-place/p5_place.py: final status 'Click 4 corners to draw a event zone · 2 regions · corners 0→1 = a gateway's walk-out edge …'; undo labels ['draw gateway door0 -> 0', 'retarget door0 -> 4005', 'reshape gateway zone', 'reshape gateway zone', 'reshape gateway zone'] for retarget, rotate, corner drag and body drag.
- **Fix:** Use 'an event'/'a gateway', show the walk-out sentence only in gateway mode, and give the rotate its own label ('rotate walk-out edge of door0').

#### P11 — Fully degenerate zones (collinear / all-coincident corners) get no region-law warning
`ff9mapkit/ff9mapkit/workspace/placedoc.py:209` · nit · bug · effort S · narrower than first reported

imagefield.zone_fan_audit returns gap=0 and spill=0 for a zero-area quad, so region_rows shows no warning for a trigger that can never fire. Four collinear corners and four coincident corners both pass clean. The claim's second example is overstated: a single corner dragged onto another (one collapsed edge) still produces a ~3% over-trigger warning. RUNG6.md:32 already records that the audit is 'vacuous on degeneracy', but Place never added a guard. Drawing four collinear clicks by hand is unlikely, so this is polish.

- **How to hit it:** Regions -> four clicks in a line, or drag corners onto each other until the quad has no area.
- **Evidence:** My probe v-place-bugs/p_misc.py: collinear {'gap':0,'spill':0} warn: None; all-same warn: None; collapsed [[0,0],[0,0],[100,100],[0,100]] warn: 'over-trigger ~3%'. RUNG6.md line 32 documents the vacuity.
- **Fix:** In region_rows, warn when the shoelace area of the stored integer quad is below a small floor (for example under one character footprint, ~100x100).

#### P25 — All placed-content markers share one ring glyph regardless of kind
`ff9mapkit/ff9mapkit/workspace/backdrop.py:429` · nit · appearance · effort S

content_markers carries kind (npc/prop/chest/spawn/arrival) and _refresh_markers passes it to the canvas, but _draw_markers ignores it and draws the same ring, dot and label for everything. Kind can only be read from the label text, and labels overprint where markers cluster: in place-fork at 150% the 'Mira' label sits under prop0's marker and column.

- **How to hit it:** Place several kinds of content close together.
- **Evidence:** backdrop.py:420-439 never reads m['kind']. placedoc.py:877 passes kind through. mist-150/place-fork_mist_150.png shows 'Mira' and 'prop0' as identical rings with overlapping labels.
- **Fix:** Choose the glyph by kind in _draw_markers: ring for npc, square for prop, box for chest, triangle for spawn, diamond with its entrance number for arrival.

#### P28 — gui_snap's Place fixtures mis-register the walkmesh on the art and stage an unreachable 'refused' screen
`tools/gui_snap.py:1903` · nit · test-gap · effort S

The 'fork' and 'regions' states pair the test_imagefield painted room with an unrelated make_camera(26, 3000) and a flat 1800x2100 quad (z 500..2600). In the snaps the footprint trapezoid covers only the back sliver of the painted floor, so every marker and zone crowds at the horizon. A reviewer cannot judge overlay registration, and part of P21's crowding is a fixture artefact. The 'refused' state calls place_doc.show_field directly without win.open_field, so the window shows 'Nothing open yet' in the tree, an empty Inspector and a 'Open a journey…' status bar, while Place claims 'hut_int — donor field #351'. No user can reach that combination.

- **How to hit it:** Reviewer-only: reading the place snaps.
- **Evidence:** Read gui_snap.py:1874-1917. Read mist-150/place-fork_mist_150.png (footprint at about y 820-885 display px against a floor painted to about 1100) and mist-100/place-refused_mist_100.png (tree 'Nothing open yet', Inspector empty).
- **Fix:** Project the painted floor polygon (or build the camera _paint_room used) so the fixture tris match the art. For 'refused', open a temp copy through win.open_field with protected_reason pinned through a seam, or open the example read-only through the shell.

#### P31 — Place's breadcrumb is the bare member name, unlike the Behavior and Cutscene tabs
`ff9mapkit/ff9mapkit/workspace/placedoc.py:911` · nit · appearance · effort S · narrower than first reported

PlaceDoc.crumb_label returns just the member name ('PLACEDEMO'), so the crumb bar reads like the Editor's field crumb. BehaviorDoc (1583) and CutsceneDoc (946) both prefix their surface ('Behavior — X', 'Cutscene — X'), so Place is the odd one out among the three fed per-field docs. The Trace half of the claim is weaker. Trace deliberately shows _content_crumbs because on show it offers the open field for a one-click reopen (shell.py:5001-5005), so naming that field is defensible. Giving Trace its own crumb is optional.

- **How to hit it:** Switch between the Author tabs with a field open and read the crumb bar.
- **Evidence:** placedoc.py:911-912 vs behaviordoc.py:1582-1583 and cutscenedoc.py:946-947. shell.py:4994-5005 shows how each tab sets its crumb.
- **Fix:** return f'Place — {self._member}' if self._member else 'Place'. Leave Trace as is, or label it with the session image name.

### Trace tab

#### T11 — Pitch is not part of the undo history, so Undo after a slider move takes back an earlier gesture
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:533` · nit · ux · effort S · narrower than first reported

_on_pitch marks the session not stamped but pushes no history entry, and snapshots do not record pitch. Pressing Undo after moving the pitch therefore leaves the slider where it is and removes the last floor, cut-out or region gesture. That matches the Undo tooltip ('Take back the last vertex or cut-out gesture'), and the module docstring defines undo as a history of gesture snapshots. So this is consistent with the stated design rather than a bug. It can still surprise an author who expects the slider to go back, but the slider is a live preview the author can simply drag back, and the removed gesture comes back with one Redo-free re-click. Real but low value.

- **How to hit it:** Trace tab > trace a floor > move Pitch > click Undo > the last vertex disappears and the pitch stays.
- **Evidence:** trace-code/probe_doc.py section 3: 'pitch before 26 after set 40 + Undo: 40 floor []'. I read the tracedoc.py docstring at line 15 and the Undo tooltip at line 186.
- **Fix:** Optional: record pitch in the snapshot and push one entry per slider gesture (sliderReleased). On restore, block signals and call _on_pitch's refresh. At least name the scope in the Undo tooltip.

#### T17 — Event message starting with '-' and no space breaks the CLI argv
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:849` · nit · bug · effort S

TraceDoc passes '--event-zone' and '<message>@<pts>' as two argv items. When the message starts with '-' and contains no space (for example '-Stop!'), argparse reads the value as an option and exits with 'argument --event-zone: expected one argument'. The Generate then fails, loudly, in Output. A message with any space, or not starting with '-', parses fine. Other argv values (floor, gateway head, foreground path) cannot start with '-' in practice.

- **How to hit it:** Set an event zone's message to '-Stop!' and Generate. Output shows an argparse error.
- **Evidence:** Re-ran probe_argv.py: "'-Stop!' -> argparse SystemExit 2", "'--' -> SystemExit 2", "'Hello there' -> parsed".
- **Fix:** Emit '--event-zone=<value>' (and '--name=<value>'), which argparse never mistakes for an option. One-line change.

#### T21 — An opaque cut-out PNG is accepted with no warning
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:316` · nit · improvement · effort S

_attach_cutout reads only the image size, and build_image_field converts every foreground to RGBA (imagefield.py:1058). An RGB or fully opaque photo-aspect PNG (for example an unedited copy of the photo) is accepted as a registered full-frame occluder. It then covers the whole background, and the actor, wherever the actor is behind the contact line. The preview would show the overlay, so an attentive author may notice, but a one-line alpha check at attach time is cheap and worth adding.

- **How to hit it:** Attach an un-erased copy of the photo as a cut-out and Generate. In-game the actor vanishes whenever it walks behind the contact line.
- **Evidence:** Code read of tracedoc.py:316-337 (no alpha check) and imagefield.py:1058 (convert('RGBA'), which makes RGB fully opaque).
- **Fix:** At attach, if the image has no alpha band or its alpha minimum is 255, add a warn teach note ('this PNG has no transparent pixels - it will hide the actor everywhere behind the contact').

#### T35 — Trace has no canvas empty state and does not accept a dropped image
`ff9mapkit/ff9mapkit/workspace/tracedoc.py:266` · nit · improvement · effort S

In the bare state the Trace canvas is an empty 384x448 frame with the 'click the floor' hint pill. The only teach is the muted 'Open an image to begin.' at the bottom. The shell's drop handler accepts only .toml/.dat/.json/.glb/.gltf (shell.py:7676), and neither TraceDoc nor BackdropCanvas implements drop, so dropping a photo does nothing. Meanwhile the tree says 'Nothing open yet', the Inspector is empty and the status bar says 'Open a journey, campaign, or field to begin.', none of which this self-contained tab needs.

- **How to hit it:** Open Trace fresh; drag a PNG onto it.
- **Evidence:** shell.py:7676-7695 (_DROP_SUFFIXES and the guard). No setAcceptDrops or dropEvent in tracedoc.py or backdrop.py. mist-100/trace-bare snaps.
- **Fix:** Paint a centred 'Open or drop a photo' prompt in the empty frame. setAcceptDrops on TraceDoc, accepting image suffixes and calling load_image, or route image suffixes from the shell to Trace.

#### T37 — Trace lives on the Assets rail, away from Place/Floorplan; no Field ▸ New entry points to it
`ff9mapkit/ff9mapkit/workspace/shell.py:1847` · nit · ux · effort S · narrower than first reported

The premise is true. Trace is grouped under Assets (Import, Trace, Models, Battle) while Place and Floorplan, which share the BackdropCanvas and the Regions tool, are under Author. But the placement is a recorded, defensible choice (PLAN rung 1: 'on the Assets rail'). Import and Trace are the two ways to bring outside material in as a field, and Ctrl-K has 'Go to Trace (turn a photo into a field)'. A move is not warranted. The cheap, worthwhile part is discoverability from the New Field flow. (Code order is Import, Trace, Models, Battle, so Trace is not literally last.)

- **How to hit it:** A newcomer looks under Author or the Field menu for 'make a field from a picture'.
- **Evidence:** shell.py:1841-1849 rail groups; shell.py:5275 Ctrl-K entry; PLAN.md:761 placement record.
- **Fix:** Add a 'Trace a photo…' item beside New Field… in the Field menu that switches to the Trace tab. Optionally show a 'Place content on it' hint after the first Generate. Keep the rail as is.

#### T41 — Trace's Inspector column is empty in every state
`ff9mapkit/ff9mapkit/workspace/shell.py:5001` · nit · improvement · effort M

With Trace active, the right Inspector column (about a quarter of the window) shows only the 'Inspector' heading and its rule. Meanwhile the tab crams vertex counts, warnings and the project/stamp state into the one overflowing status line under the canvas (T23). Behavior and Cutscene already mount an instruments panel into the Inspector (_mount_behavior_instruments / _mount_cutscene_instruments), so the pattern exists. Moving the session summary there would also relieve T23.

- **How to hit it:** Any Trace session.
- **Evidence:** Pixel scan of the Inspector column (display x 1700-1990, y 240-1200) in mist-100 trace-traced and trace-contacts: 100% background. The same scan on cutscene-doc_mist_100: 96% background (instruments drawn). shell.py:4963-4964 mounts instruments for Behavior and Cutscene only.
- **Fix:** Add _mount_trace_instruments: image name, pitch/distance, vertex and cut-out/region counts with warnings, the generated project path, stamped vs not, and the deploy hint. Then shorten the status line.

### Shared canvas (Place + Trace)

#### V4 — Ctrl+0 from a zoomed view fits ~2% small because it measures the scrollbar-reduced viewport
`ff9mapkit/ff9mapkit/workspace/backdrop.py:1058` · nit · ux · effort S

_fit computes the zoom from viewport().width()/height(), which shrink while the zoomed transform shows scrollbars. Ctrl+0 pressed from a zoomed view therefore fits to the smaller viewport. The scrollbars then disappear, leaving the art about 2% smaller and a few px off-centre compared with the first-paint fit in the same window. Further Ctrl+0 presses are stable, so it does not ratchet. The effect is cosmetic and barely visible.

- **How to hit it:** Ctrl+scroll in until scrollbars show, then press Ctrl+0.
- **Evidence:** probe1.py rerun: first fit 'vp=637x557 m11=1.20600 dx=86'; after zoom-in (vp 625x545) Ctrl+0 gives 'vp=637x557 m11=1.18002 dx=91'. At 640x560: 1.20384 vs 1.17786.
- **Fix:** Fit against maximumViewportSize() (independent of the current transform), or resetTransform() first, process the layout, then measure.

#### V7 — Dragging a vertex above the horizon commits it, while a click there is refused (feedback does exist)
`ff9mapkit/ff9mapkit/workspace/backdrop.py:992` · nit · ux · effort S · narrower than first reported

Appending a vertex refuses above the horizon (click_refused), but _end_vertex_drag commits the dragged canvas point unconditionally, so a drag can create a vertex the build would refuse. The asymmetry is real. The claim that 'the host status line gets no message' is wrong. on_floor -> tracedoc._on_floor -> _refresh writes 'N vertices traced · 1 above the horizon (red)'. Generate is disabled with a tooltip saying every vertex must be below the horizon, and the coords chip reads 'above the horizon' during the drag. The design already treats canvas px as truth and renders red vertices; the pitch-change case creates them too. So this is an inconsistency with visible feedback, not silent bad data, and undo reverts it.

- **How to hit it:** Trace: drag a vertex up past the horizon and release.
- **Evidence:** probe5.py rerun: 'committed: (150.1, -43.9) click_refused: [] worlds: None'. Code read: tracedoc.py:549-552 (_on_floor -> _refresh), 394-395 (status note counts red vertices), 358-380 (Generate gated and tooltip).
- **Fix:** On release, if click_to_world(d['pt']) raises, emit click_refused(msg) and _rebuild() without committing, mirroring the region-corner drag that holds the corner below the horizon.

#### V9 — Contact mode: clicking on an existing snip's opaque pixels arms a no-op snip drag instead of a contact
`ff9mapkit/ff9mapkit/workspace/backdrop.py:1128` · nit · ux · effort S

In contact mode, mousePressEvent resolves cutoutimg (alpha-masked) before falling through to the contact click. A slop click on an existing snip's opaque pixels therefore arms a snip drag that ends unchanged (no cutout_moved), and contact_clicked is never emitted. The Cut-outs tool stays armed and the status line says nothing. Marking a second object's base where it overlaps an attached snip gets no response. This is rare: the object's base must sit on top of another snip's opaque body.

- **How to hit it:** Trace > Cut-outs with one snip attached: click on the snip's opaque body to mark a new contact. Nothing happens.
- **Evidence:** probe2.py section G rerun: 'contact_clicked after a slop click on the snip body: []'. Code read: tracedoc._on_contact is the only consumer.
- **Fix:** In contact mode, skip arming snip drags (contact handles still re-anchor), or treat a cimg drag released within _CLICK_SLOP_PX as a contact click.

#### V15 — Canvas handle radii are fixed px under the CALIBRE dial; the cut-out combo truncation is NOT a scale effect
`ff9mapkit/ff9mapkit/workspace/backdrop.py:48` · nit · improvement · effort S · narrower than first reported

_HANDLE_R=4 (an 8px handle), the 8px marker ring, the 10px contact diamond and the label offsets are constant screen px, while label fonts scale with the dial. At 150% the grab targets get relatively smaller next to the text, a polish issue. The supporting example is wrong. The fg_box cut-out combo truncates at 100% too ('fg0 @ (230,320) · z 1073 · pillar_snip.|' in mist-100/trace-contacts), and the row has free space to its right. So the truncation comes from the combo's own sizing (min width 260, no stretch, default AdjustToContentsOnFirstShow while the strip was hidden and empty), not from the 150% dial. tracedoc.set_scale only forwards to the canvas, so the px widths are never re-derived.

- **How to hit it:** Trace at 150% text size: vertex and corner handles stay 8px.
- **Evidence:** Read the backdrop.py constants (48, 429, 481) and tracedoc.py:119/178/204/247/255 and set_scale at 1140. Viewed review-ctp/mist-100/trace-contacts_mist_100.png (truncated at 100%) and mist-150/trace-contacts_mist_150.png.
- **Fix:** Optionally scale _HANDLE_R and the glyph sizes by self._scale/100 in _rebuild. Fix the combo separately (see the extra finding): give it a stretch factor or AdjustToContents rather than px math.

## 9. Refuted, or by design

- **T40 — Trace's first Generate opens the project on the Editor tab, not Place** (by-design). The premise is accurate: on_generated is shell.open_field, which ends with tabs.setCurrentWidget(self.doc_scroll), so the author lands on the Field form. This is the recorded design, though. The _after_generate docstring and the pinning test test_first_generate_hands_the_project_to_the_shell_once both say a clean first Generate 'opens the project in the Editor (which is what feeds Place, 7d)'. 'One flow' means Place is already fed with the project, not that the author is moved to it. A one-line status hint pointing to Place would be a small improvement, but the behaviour is intended.
- **V11 — The missing eye in _px_to_zone_world's refine pass is not what puts a handle off the cursor** (refuted). The code asymmetry is real: line 523 calls floor_y_at without the eye, while _zone_y passes it. The claimed consequence does not follow from it. The refine branch runs only when the pixel's ray misses every walkmesh triangle. The refine then re-intersects the ray with the plane at the chosen floor's height y. If the triangle at height y contained that new (x', z'), the ray would have hit it, contradicting the miss (exactly so for flat floors). So the refined corner never lies on the floor that was picked, and _zone_y resolves its render height from other triangles or the nearest-vertex fallback whichever candidate the refine chose. The corner can sit off the cursor in this off-mesh case with or without the eye. Passing the eye is a harmless consistency tidy that fixes nothing user-visible.

## 10. Flows the explore pass drove and found correct

**x-cutscene-place**

These flows behaved correctly.
- Dragging a walk target with real mouse events commits exactly one undo step. Undo restores the named target 'altar' and puts the handle back.
- Pick on the stage rounds to the nearest integer correctly (124.13, 456.64 → '124, 457'), and teleport pick works with the storyboard open.
- Animation Browse works in every case tried. Cancel keeps the value, a pick writes the clip name, and the cast actor is scoped to its model (GEO_SUB_F0_CID, 28 clips). 'player' scopes to Zidane (403 clips). A blank actor in a two-actor cast and an unknown actor open unscoped with a stated reason.
- Scene add/dup/delete through Undo/Redo keeps rail, ladder, stage and stack consistent with the buffer (the doc's dict is still the shell buffer), apart from the selection finding.
- Deleting every scene shows the 'noscene' guide, and Undo brings the content back.
- The staging job: a scene switch mid-run, Close mid-run and closing the window raised no exception in a slot or thread. The button always came back as 'Check the staging'. The worker's signal is queued onto the GUI thread, and a stale run is dropped by the generation counter on a field switch.
- Place on a novel field: Load works through the async loader. Arrival is upserted by entrance (entrance 2 moved, not duplicated). The entrance spinner shows only in Arrival mode. Spawn, Arrival and Undo/Redo through the shell restore the right player rows, keep the Place tab current and redraw the markers. Save All writes exactly what the canvas showed (disk player == buffer).
- The region flow is one undo step per gesture: draw, retarget, rotate, corner drag, body drag, message, delete. Each Undo steps back exactly one gesture, and the regions stay grabbable in Regions mode.
- The multi-camera combo appears for two cameras. Switching cameras reloads per camera and keeps the placed markers. A walkmesh obj field gives the same surface under both cameras.
- The Place loader worker touches no Qt object off the GUI thread: its signals are emitted from the worker and delivered queued to the QObject that lives on the GUI thread.

Not walked: see the `walked` field in `findings.json`.

**x-trace-e2e**

Verified correct:
- **Gestures:** every canvas gesture driven through real events is exactly one Undo step and restores exactly:
  - a floor click (an above-horizon click is refused, history unchanged);
  - a vertex drag; right-click Delete vertex;
  - Esc mid-quad (pending cleared, no history entry; needs canvas focus, which a click gives);
  - a gateway drawn by 4 clicks;
  - region retarget, reword, rotate (walk-out edge) and corner drag; Delete from the menu;
  - a contact click with snip attach (returns the tool to Floor), a snip drag (the anchor rides by the same delta), a contact re-anchor (the image stays put).
- **Sidecar:** written at each Generate, it agrees with the session (floor, pitch, snip offset, regions, name, id). Reopening via .trace.json or via field.toml with the sidecar restores floor, pitch, cut-out contact, dragged snip offset and kind, region kind/to/entrance/message/quads, name and id with a maximum numeric difference of 0.0. An event message with quotes and a backslash round-trips.
- **Pre-sidecar backfill:** restores the floor exactly (0.0) and region quads within 0.1 px. A snip comes back as a registered full frame, which is the documented loss. A regenerate of an unchanged pre-sidecar project leaves walkmesh.obj and art byte-identical (it changes only the toml and writes base.trace.json).
- **What each regenerate changes:** after a vertex edit, walkmesh.obj, the toml and the sidecar change; art PNGs are byte-identical. After removing a cut-out and deleting the event zone, the toml and sidecar change, and the removed event is reported in the CLI output. The stale art/fg0.png is left on disk but no longer referenced.
- **Cross-tab:** NPCs, props, [[player.arrival]], and Place door0/zone0 (alongside existing traced_ rows) all survive a Trace Regenerate. In the full shell, a first Generate hands the project to the shell, Place serves the novel project's surface, and Save All followed by Regenerate keeps the Place NPC and door when the trace session has no regions.
- **History:** capped at 100. Older steps drop silently; the Undo button simply disables. Snapshots share their pixmaps, so 120 snapshots on a 6000x4000 photo held about 40 KB of Python heap.
- **Images:** every 8-bit odd image (panorama, tall, tiny, huge, RGBA, paletted, JPEG, CMYK, grey) and a photo path with spaces, accents and CJK ingest and build correctly at 1536x1792. load_image takes 0.03-0.28 s.
- **Field ids:** check_custom_id band edges behave as its message states, and whitespace is trimmed.

Not walked: see the `walked` field in `findings.json`.
