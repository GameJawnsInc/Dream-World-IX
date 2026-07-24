# GUI-UX design-lens review — chair's decision

> **Build status (2026-07-24).** BUILD-NOW 1-12 shipped in the design-lens wave (`66cdbd3`); the owner's
> picked wave built ASK 1-5, 8-10, 12-13, 18 (`5839fb9`) and the final four built ASK 6, 11, 15, 22
> (`42bdc31`). **The 2026-07-24 remainder wave built ASK 7 (tree half), 14 (low-risk half), 16
> (raise/flash only), and 19 (MERGE A's fit_dialog vehicle)** — each per its chair ruling; the deferred
> halves are noted inline below. Still unbuilt: ASK 17 (deploy-on-save, ~L), 20, 21, plus #7's
> form-scroll tokens and #14's full per-tab context card.

**Surface:** the ff9mapkit Workspace (PySide6). **Phase:** RESEARCH — proposals only, no app code edited.
**Inputs:** 36 lens proposals across 8 lenses (first-run, veteran-loop, wayfinding, feedback-progress,
identity-delight, disclosure, prevention-recovery, consistency) + three independent judge scorecards
(value / fit / feasibility / verdict), all cross-verified against source with line numbers.

This document is the **owner's triage sheet**: what to build now, what needs a decision, what was killed and why.

---

## Method

1. **Dedupe / merge.** Overlapping proposals collapsed to one entry, keeping the strongest sketch and
   noting the merged titles. Two merges (below) plus one same-concept rejection.
2. **Combine verdicts.** No proposal drew a *reject* from any judge — every vote was `build` or `ask`.
   Rule applied: **unanimous `build` → BUILD-NOW**; anything with even one substantive `ask` → **ASK-USER**;
   BUILD-NOW additionally requires **cost S or M and risk low/med** (all 12 qualify). Because there were no
   judge rejects, nothing was killed on the reject-uphold rule. The single REJECTED item is a *duplicate
   vehicle* the chair folded away on SIGNET-law grounds (see below), not a judge veto.
3. **Chair spot-checks.** Re-verified the load-bearing code paths behind the top BUILD-NOW items:
   `_next_actions` READY returns `("", [])` at `shell.py:7258` with the JUST-DEPLOYED branch ahead of it
   (7256); `_refresh_spine` renders action tuples as `QPushButton`s (7272-77); `coopdoc.py:275` adds
   `style_box` unconditionally; the band-error string is hand-copied at `shell.py:2537/2920/3038/3040`;
   `widgets.empty_state` exists at `widgets.py:713`. All confirmed.
4. **Ranking.** Combined score = Σ(value+fit+feasibility) across the three judges (max 45).

### Merges & the one rejection

- **MERGE A — the first-deploy moment.** *#3 "Make first success an occasion" (fit_dialog card)* + *#21
  "It's in the game" (animated signet gesture)* are the same idea (celebrate the first-ever deploy, once per
  install) in two vehicles. Kept as one ASK-USER item using **#3's restraint-safe vehicle**.
- **REJECT — #21's vehicle.** The signet-gesture animation is sited on **Build & Deploy**, the 3-hour work
  surface where *"the lamp on Build & Deploy (flat, user-ratified)"* is a **settled question** and the SIGNET
  contract mandates restraint. All three judges scored #21 lowest of the delight set and flagged the
  work-surface gold; J2: *"prefer the banner-side P18/P31 instead."* The **concept survives** in MERGE A; the
  **animated-gold-on-Build vehicle is killed** so it is not re-litigated. `rejected = 1`.
- **MERGE B — pick-and-fill for real FF9 fields.** *#4 "Wire Suggest-a-test-room into the input"* + *#36
  "Find… should pick-and-fill"* share one mechanism (a CatalogPicker that fills the id box) on different
  buttons; J2: *"build them as one CatalogPicker reuse."* Kept as one ASK-USER item (backbone = #36's
  `realfield` catalog kind; #4 adds the fill + a beginner starter). **Conflict flagged:** #25 wants to bury
  the "Suggest a test room…" button in a disclosure — reconcile before building either.

---

## BUILD-NOW (unanimous `build`, cost S/M, risk low) — 12 items

Ranked by combined score. Each verified against source by all three judges.

### 1. First-run READY spine — point the newcomer at Deploy  ·  score 40  ·  S / low
**Lens:** first-run. **Evidence:** `_next_actions` READY branch returns `("", [])` (`shell.py:7258`) on the
veteran-correct assumption "Deploy is right there" — a newcomer has never met F9 or the top-right Deploy chip.
The JUST-DEPLOYED branch (7256) short-circuits first, so the insert is correctly ordered.
**Sketch:** before the READY return, `if t and not prefs.has_deployed(): return ("Your fork is ready — press
Deploy to put it in your game.", [("Deploy", self._deploy_now, True)])`. State-gated to the pre-first-deploy
window; silent forever after. **Verdicts:** J1 build · J2 build · J3 build. **Ruling: BUILD-NOW.** Reaches the
newcomer on the Import tab where the Home guide isn't visible; textbook spine-charter compliance.

### 2. One-click restore of the save-edit backup  ·  score 40  ·  S / low
**Lens:** prevention-recovery. **Evidence:** the save editors write a timestamped `.bak` before every Apply
and already return `res['backups']` (`savedoc.py:371-372`), but there is **no button to use it** — recovering a
fat-fingered scenario counter on the player's single irreplaceable save means hand-renaming a file.
**Sketch:** remember `res['backups'][-1]`; add an "Undo last edit (restore backup)" button enabled only after
an Apply this session, disabled once `load()` reads a different file; a guarded `_save.restore_backup` copies
it back behind a confirm. Mirror in ItemEquipDoc. **Verdicts:** J1 build · J2 build · J3 build.
**Ruling: BUILD-NOW.** Closes the recovery loop on the most un-regenerable artifact the app touches; the
prevention already exists, only the restore is missing.

### 3. Elapsed clock + stall detection + a Stop button on the busy indicator  ·  score 38  ·  M / low
**Lens:** feedback-progress. **Evidence:** `run_job` starts a QProcess with **no timer and no kill path**
(grep confirms zero `kill()`/`terminate()`), and `_drain_proc` (`shell.py:8043`) only logs when stdout has text
— during silent UnityPy bundle reads both the indeterminate bar *and* Output freeze, so a user cannot tell a
slow import from a hang and can only escape a wedge by killing the app.
**Sketch:** `QElapsedTimer` + 1s `QTimer` updating the muted "Working… m:ss" label (text, not motion —
reduced-motion-safe); after >20s of stdout silence append " · no output for {n}s (still running)"; a flat Stop
button in the console header calls `self.proc.kill()` → the normal ERROR verdict (fail_hint "Stopped."). All
widgets hide on `_set_busy(False)`. **Verdicts:** J1 build · J2 build · J3 build. **Ruling: BUILD-NOW.** The
anchor of the progress cluster; a real capability gap on the app's slowest path.

### 4. Turn the post-deploy warp hint into a one-click Copy-warp receipt  ·  score 38  ·  S / low
**Lens:** feedback-progress. **Evidence:** the id is already composed into `ok_headline` (`builddoc.py:758`)
and the JUST-DEPLOYED spine (`shell.py:7256`) renders action tuples as buttons (7272) — but the id is prose the
user hand-retypes into the debug menu, where a mistype warps to the wrong field (own-id/campaign ids vary).
**Sketch:** stash the id in `_proc_done`'s existing deploy branch; append one `("Copy warp: <id>", copy_cb)`
tuple that puts the bare id on the clipboard. The spine already self-dismisses on the next edit.
**Verdicts:** J1 build · J2 build · J3 build. **Ruling: BUILD-NOW.** Tiny, fully on-mechanism, state-gated.

### 5. Fold Co-op "Play style" into a collapsed Advanced disclosure  ·  score 38  ·  S / low
**Lens:** disclosure. **Evidence:** `style_box` (4 battle-slot checkboxes + ATB spinner + ghost-outfit combo +
Follow-host + diorama + Apply) is the **largest always-visible block** on the tab and is added unconditionally
(`coopdoc.py:275`, greyed but never hidden) even when Status reads "co-op off" — but a first-run co-op user
only needs Host/Join/Start to see ghosts.
**Sketch:** wrap it in `widgets.disclosure("Advanced — battle co-op & visitor options")` (collapsed default);
auto-expand when `_load_playstyle` finds a non-default GuestSlots/GhostAs/FollowHost (comes-back rule). The
nameplate's "in Play style below" becomes "in Advanced options below" (structural follow-on, not a string
re-litigation). **Verdicts:** J1 build · J2 build · J3 build. **Ruling: BUILD-NOW.** Textbook
restraint-where-you-work; the single accent (Start co-op) is untouched.

### 6. FieldIdField: one field-id input, one band lesson, one validator  ·  score 37  ·  S / low
**Lens:** consistency. **Evidence:** the custom-band rule is taught four ways (placeholder in New Field,
caption in New Journey, **nothing** in Import) and enforced by a hand-copied string at `shell.py:2537/2920/
3038/3040`; the Import fork-id box (`importdoc.py:219`, `QLineEdit('4003')`) has **neither** caption nor OK-time
band check.
**Sketch:** add `widgets.BAND_HINT` + an `id_field(...)` helper (QLineEdit + band caption, one placeholder) and
a single `check_custom_id(text, what=...)` validator in `pack.py`; rewire New Field / New Journey / Import to
use them. The band is a permanent property of the input → a permanent caption (correctly not goes-away prose).
This targets the **custom-id band 4000-32767**, distinct from the safe-flag band the strings pass froze — no
overlap. **Verdicts:** J1 build · J2 build · J3 build. **Ruling: BUILD-NOW.** DRY plus a real newcomer-clarity
win where the id is typed.

### 7. The empty stage has a voice — the blank navigator gets an empty-state  ·  score 35  ·  S / low
**Lens:** identity-delight. **Evidence:** with no project the entire ~300px navigator (`shell.py:1258-1288`)
renders as a blank void whose only guidance is a tiny status-bar line; `widgets.empty_state` (`widgets.py:713`)
already exists and is used by the State/Item panels.
**Sketch:** show an `empty_state` (glyph + "Nothing open yet" + "Open a journey, campaign, or field from the
toolbar — or start on Home.") when `topLevelItemCount()==0`, hidden the instant a project loads; palette-only,
no gold. **Feasibility note (J3):** a QTreeWidget can't host a child overlay cleanly — route tree vs empty_state
through a `QStackedWidget` toggled on the existing open/close path. **Verdicts:** J1 build · J2 build · J3 build.
**Ruling: BUILD-NOW.** Fills a genuine void reusing the established grammar and voice.

### 8. A "Deployed here & how to undo it" ledger  ·  score 35  ·  M / low
**Lens:** prevention-recovery. **Evidence:** the GUI reverts only the latest/current-own-id
(`jobs.revert_field_argv:453`) while `deploy_field` writes per-id `revert_deploy_<id>.py` (`jobs.py:305`) that
accumulate **unlisted**, and the sole Revert button scrolls below the fold. The exact read-side inventory
pattern already ships for models (`modelsdoc._deployed_box:364`).
**Sketch:** add a "Deployed here" section to Build & Deploy styled like `_deployed_box` (section + capped
QListWidget + Refresh + confirm-first "Revert selected…"); a new `jobs.scan_deployed_reverts` pairs registered
ids (from DictionaryPatch) with their revert scripts by mtime; rows with no script are read-only informational.
**Verdicts:** J1 build · J2 build · J3 build. **Ruling: BUILD-NOW.** Reuses proven widget language; the mtime
pairing is heuristic but mitigated by the read-only "no undo script" rows.

### 9. Co-op cross-link — it's filed under Ship but it's a play-session feature  ·  score 34  ·  S / low
**Lens:** wayfinding. **Evidence:** the rail group Ship = [Build & Deploy, Co-op] (`shell.py:1355`), but Co-op
is live netsync — a play session, not shipping; Home already renders object entry-cards with nav lambdas
(`shell.py:1747-56`) and Co-op is conspicuously **absent** from that list.
**Sketch:** add a Home nav row for Co-op (existing `_home_row` idiom) + reciprocal quiet-tier header
cross-links on builddoc/coopdoc. **Declines** to regroup the settled 5-group rail (that would be L/risky).
**Verdicts:** J1 build · J2 build · J3 build. **Ruling: BUILD-NOW.** Cheap discoverability fix that reuses the
exact existing pattern.

### 10. Mirror job state to the always-visible chrome  ·  score 34  ·  S / low
**Lens:** feedback-progress. **Evidence:** every running-job signal lives inside the collapsible console (which
starts collapsed), while the crumb Deploy button stays enabled+un-restyled and `run_job` silently no-ops a
re-click (`shell.py:7967` returns False) — the click just vanishes.
**Sketch:** while busy, relabel the crumb Deploy button ("{subject}…", disabled, hourglass) via the existing
`_refresh_deploy_btn`, and the collapsed console toggle ("▸ Problems · Output — Working… m:ss") via
`_sync_console_btn`; both revert on `_set_busy(False)`. **Dependency:** the elapsed value comes from the timer
in BUILD-NOW #3, but the relabel/disable stands alone. **Verdicts:** J1 build · J2 build · J3 build.
**Ruling: BUILD-NOW.** No new widget — re-labels two existing controls; cures a real "did my click register"
confusion.

### 11. RegionCatalogDialog: dedupe the two byte-twin FF9-region pickers  ·  score 34  ·  S / low
**Lens:** consistency. **Evidence:** `shell._pick_regions` (`shell.py:2671`) and
`importdoc.open_region_catalog` (`importdoc.py:414`) both build the same checkable QListWidget over
`RA.load_region_catalog()` and have **drifted** (shell adds Select-all + "in arc" disabling; import adds
"N fields") — a fix must be made twice; the round-8 review already flagged them as twins.
**Sketch:** extract one `region_catalog_list(arcset, *, exclude=…, show_counts=…)` builder into widgets; each
dialog keeps its own QDialog shell. Both inherit the union of features and one future fix point.
**Verdicts:** J1 build · J2 build · J3 build. **Ruling: BUILD-NOW.** Clean DRY/consistency win, contained
regression risk.

### 12. Remember the Build & Deploy destination choice across sessions  ·  score 33  ·  S / low
**Lens:** veteran-loop. **Evidence:** `_field_box` hard-resets `rb_test.setChecked(self.has_tools)`
(`builddoc.py:145`) every session, so a veteran whose workflow is "Deploy at its own id" (rb_own) re-picks it
on every open/launch; all radios already route through `_update_dest` (460).
**Sketch:** `prefs.deploy_dest()`/`set_deploy_dest(mode)` storing `test|own|game|other` (In-place excluded — it
is donor-driven and auto-selects); persist on toggle; apply the saved mode when its radio is legal and In-place
is not auto-selecting, else fall back to the current default. **Verdicts:** J1 build · J2 build · J3 build.
**Ruling: BUILD-NOW.** Persists an existing control's state; no new surface; clean legal-choice fallback.

---

## ASK-USER (a substantive `ask` from ≥1 judge, or a product/taste decision) — 22 items

Ranked by combined score. Each names the decision the owner must make.

### 1. Stop confirming reversible deploys — make F9 a true one-key loop  ·  score 42  ·  S / low
**Lens:** veteran-loop. **Evidence:** `_go_field` pops a modal `QMessageBox` on the reversible branches rb_test
(`builddoc.py:753`) and rb_inplace (739) on **every** deploy — so the advertised one-keystroke F9 loop is
F9→modal→Enter→wait, dozens of times a session, guarding an action the app itself labels reversible and Revert
undoes in one click. **Verdicts:** J1 build · **J2 ask** · J3 build. **Chair ruling: ASK-USER — the feature is
strongly endorsed; the only open question is the default direction.** J2's ask is not a law/feasibility kill —
it is a product call: defaulting the pref to *skip* removes a safety modal by default on the most-repeated
action. **Recommendation:** build it, keep the confirm unconditional on the no-undo Install-to-game and the
wholesale campaign/journey branches, and let the owner choose the default (chair leans skip-by-default with a
Preferences opt-in, matching the "reversible" labelling and Revert's one-click undo).

### 2. Default "reopen the last project on launch" ON  ·  score 40  ·  S / low
**Lens:** veteran-loop. **Evidence:** `restore_session()` defaults False (`prefs.py:232`);
`restore_last_session` is try/except-guarded, pre-aims Build so F9 is live on restore, and no-ops on an empty
recent list (newcomers untouched). **Verdicts:** J1 build · **J2 ask** · **J3 ask.** **Chair ruling: ASK-USER.**
Mechanically trivial and safe, but flipping a **deliberately-set** opt-in default is a product decision (added
launch latency; a project the user may not want reopened). **Recommendation:** flip to ON — the returning
veteran's first action becomes automatic and the newcomer path is identical.

### 3. Honor the backup law on "Install to game" — auto-snapshot + wire Revert  ·  score 35  ·  M / med
**Lens:** prevention-recovery. **Evidence:** rb_game is the only field path with `rev.setEnabled(False)` and
"no automatic undo" (`builddoc.py:487-493`), yet Hard-Constraint §2 mandates a timestamped backup before
editing any game file — the one GUI write into the real shipping folder is the one place that violates the
project's own law. **Verdicts:** J1 build · J2 build · **J3 ask.** **Chair ruling: ASK-USER — strong §2 case,
feasibility needs a green-light.** The snapshot must know *which* StreamingAssets files the id owns plus back up
the whole-folder DictionaryPatch that Install rewrites, and Revert's per-mode semantics gain an install branch;
J3 rightly notes the scope is subtler than the M tag. Get the snapshot scope exactly right or the flipped
"reversible" caption lies. **Recommendation:** approve; scope the reader first.

### 4. Pick-and-fill for real FF9 fields (MERGE B: #4 + #36)  ·  score 34  ·  M / med
**Lens:** first-run + consistency. **Evidence:** model/prop/item/flag lookups use an interactive CatalogPicker
that fills the field (`forms_qt.py:350/531`), but the real-FIELD lookups the whole Import tab hinges on dump
text to the console and make the user retype the id — `Find…` shells `list-fields` (`importdoc.py:736`) and
"Suggest a test room…" streams a table with "put its id in the field box" (`importdoc.py:185-92`). **Verdicts:**
#4 J1 build/J2 build/**J3 ask**; #36 J1 build/J2 build/**J3 ask**. **Chair ruling: ASK-USER — right shape, real
build.** Add a `realfield` kind to `infohub.browse` (backed by `reference/field-manifest.tsv`) so CatalogPicker
serves it unchanged, then rewire `find_btn`/Suggest to `setText(id)`. **Two things to resolve:** (a) `find-rooms`
is a ~45s sweep with **no cache today** — the picker needs caching or a spinner, not a 45s block; (b) the
beginner "starter id" (#4 part 2) is brittle if hardcoded. **Conflict with ASK #5 below** (which buries the
Suggest button) — decide the button's fate once.

### 5. Tuck Import "Walk as" player-swap into a collapsed disclosure  ·  score 34  ·  S / low
**Lens:** disclosure. **Evidence:** the swap row sits always-visible outside the verbatim-gated carry box
(`importdoc.py:169-200`) even in the default recommended verbatim flow; player-swap is expert (its own hint
warns scripted gestures glitch). **Verdicts:** J1 build · J2 build · **J3 ask.** **Chair ruling: ASK-USER —
reconcile with MERGE B first.** The disclosure logic is clean (auto-expand when swap is non-empty), but it drags
"Suggest a test room…" — a **newcomer** aid — into an *advanced player-swap* drawer, directly conflicting with
MERGE B which wants that button more prominent. Also the declutter is smaller than the co-op one (the swap is
already below the carry box). **Recommendation:** build the disclosure for the swap row itself, but keep
"Suggest a test room…" out of it (it belongs with the id box per MERGE B).

### 6. Put an "Undo this deploy" action on the post-deploy banner  ·  score 34  ·  M / low
**Lens:** prevention-recovery. **Evidence:** call sites literally write "Undo with Revert." into `ok_next`
(`builddoc.py:766`) yet only *name* Revert; the actual button scrolls below the fold. **Verdicts:** J1 build ·
J2 build · **J3 ask.** **Chair ruling: ASK-USER — sound idea, wrong host.** J3 verified `self.banner` is a plain
`QLabel` rendering `next_action` as a **text tail** (`shell.py:7930-31`), so "a quiet button inside the banner
strip" means restructuring a high-traffic shared surface used by every running/ok/warn/error verdict — not the
low-risk tuple-extension the sketch implies. Overlaps BUILD-NOW #4 (copy-warp) and #8 (ledger). **Recommendation:**
if approved, deliver undo via the **spine action-tuple** (already a real button row) rather than restructuring
the banner.

### 7. Make the Inspector/Home CONTENTS rollup navigable  ·  score 33  ·  M / low
**Lens:** wayfinding. **Evidence:** `_rollup` emits "encounter" as a `goto:battle` link but "BGM" beside it as
inert muted text — the study's own call-site law (a proven jump mechanism unspent by the call site).
**Verdicts:** J1 build · J2 build · **J3 ask.** **Chair ruling: ASK-USER — the tree half is clean, the
form-scroll half is the cost.** Emitting tree-group focus links is easy; "BGM/encounters → scroll the form to
that section" needs a new `focus:<section_key>` href **and** forms_qt to expose section-header widgets by key
for `ensureWidgetVisible` — plumbing the M tag under-weights. **Recommendation:** approve; consider shipping the
tree-navigation tokens first and the form-scroll tokens as a follow-on.
**→ BUILT 2026-07-24 (tree half):** every rollup tally is a `goto:tree:<member>:<sect>` link landing its
group/section row (`shell._rollup` + `_goto_tree_section`); the form-scroll tokens remain the follow-on.

### 8. Structured failure: extract the error into a Problems row + Jump-to-error  ·  score 33  ·  M / med
**Lens:** feedback-progress. **Evidence:** `_proc_done` posts `_show_problems(v, [])` with an **empty** list on
failure (`shell.py:8055`) and only Traceback lines get tinted (8046) — a CLI `error:` line is invisible in a
grey log wall. **Verdicts:** J1 build · J2 build · **J3 ask.** **Chair ruling: ASK-USER — half buildable now.**
The row-extraction honours the codified "don't cry wolf" law (fire only on non-zero exit + a tight anchor). But
the "Jump to the error" action fights the same QLabel-banner limit as ASK #6 — the jump wants
`banner` restructuring or should pivot to **Problems-row activation**. **Recommendation:** approve the Problems
row unconditionally; deliver the jump via a clickable Problems row, not the banner tail.

### 9. The concept map's spine reads as a trunk, not a scatter  ·  score 33  ·  S / low
**Lens:** identity-delight. **Evidence:** all nine nodes share one fill/weight
(`conceptmap.py`), so the Journey→Campaign→Field spine is indistinguishable from the leaves on a surface whose
job is "the whole model at a glance." **Verdicts:** J1 ask · J2 build · **J3 ask.** **Chair ruling: ASK-USER —
taste on a teaching surface.** Fully buildable (a plinth rect before the node loop + per-edge pen weight keyed
on spine-pair vs field-child; `_EDGES` already distinguishes them), gold-free (climate, not signature), low
risk. Two of three judges call it a one-look refinement — the owner should decide if the map needs the
hierarchy pass.

### 10. A quiet mode chip (Guided / Full presence in the status bar)  ·  score 33  ·  S / low
**Lens:** disclosure. **Evidence:** the Guided/Full toggle has no on-screen presence, and a form with no
advanced fields renders identically in both modes (`forms_qt.py:194`) — a user who flips it in Preferences often
sees nothing and concludes it's dead (the low-trust failure the study documented for the layout ratchet).
**Verdicts:** J1 build · J2 build · **J3 ask.** **Chair ruling: ASK-USER — value vs a persistent presence.**
Cheap and it cures "this setting does nothing," but it adds a permanent status-bar word on every surface for a
rarely-flipped pref — mild persistent chrome the Signet contract keeps off work surfaces. **Recommendation:**
worth it *if* the beginner-mode lever (ASK #12) lands and makes the mode consequential; otherwise it labels a
near-inert setting.

### 11. Extend the get-started arc past the fork — "Deploy & play"  ·  score 32  ·  M / med
**Lens:** first-run. **Evidence:** `_getstarted_steps` (`shell.py:1826-34`) ends at "Go to Import" and
`_getstarted_show` (267-88) returns `not has_target` — the guide **vanishes the instant the fork opens a
target**, exactly when "now deploy and press ~" is needed. **Verdicts:** J1 build · J2 build · **J3 ask.**
**Chair ruling: ASK-USER — real gap, but the sketch has a verified bug and touches a fenced law.** J3 caught
that `_refresh_getstarted` computes `primary_ix` via `next(i for i,s if not s[2])`, and step 3's `done=None`
makes the accent never advance to a 4th step without extra logic; it also rewrites the round-8 truth-table-fenced
goes-away predicate and breaks `test_home_beginner` (`shell.py:9755/9761`), and the prefs path is miscited
(`ff9mapkit/prefs.py`, not `workspace/prefs.py`). **Recommendation:** approve the intent (close the arc at
Deploy), but re-derive the goes-away fence and its test law rather than patching, and fix the primary_ix
advance. ASK #1 (First-run READY spine, now BUILD-NOW) already covers the newcomer on the Import tab, so this is
the Home-side complement, not the only path.

### 12. Make "Beginner mode" a real cross-tab lever  ·  score 32  ·  M / med
**Lens:** disclosure. **Evidence:** `guided()` is read in only two UI places (`forms_qt.py:194`,
`battledoc.py:481`) — flipping the mode changes **nothing** on Build/Import/Co-op, under-delivering the
Preferences promise "Full — show every field inline." **Verdicts:** J1 ask · J2 build · **J3 ask.** **Chair
ruling: ASK-USER — right instinct, cross-cutting med-risk.** `widgets.disclosure(expanded=not guided())` is the
lever, but re-defaulting already-built drawers on a live `_apply_guided` means rebuild-or-toggle across multiple
docs; it depends on BUILD-NOW #5 and ASK #5 landing first; and whether Full should blow *every* expert drawer
open on every tab is itself a judgment (it can read as noise). **Recommendation:** sequence after the two
disclosures exist; keep the computed auto-expand overrides winning over the mode default.

### 13. Name the New-Game casualty before a campaign/journey deploy wipes it  ·  score 32  ·  M / med
**Lens:** prevention-recovery. **Evidence:** `deploy_campaign` wholesale-replaces the mod folder and **wipes the
field-70 New-Game override** (documented footgun, §5), yet `_go_campaign`'s confirm (`builddoc.py:794`) never
says so and `_newgame_box` shows no current target. **Verdicts:** J1 build · J2 build · **J3 ask.** **Chair
ruling: ASK-USER — real silent footgun, unproven reader.** The named 3-button confirm ("Deploy & re-wire" /
"Deploy anyway" / "Cancel") + a persistent "currently points at X" status is standard; the feasibility drag is
the new `jobs.current_newgame_target` reader (parsing the deployed field-70 override) whose reliability is
unproven. **Recommendation:** approve; green-light the reader as its own step.

### 14. Give the Inspector a per-tab context card instead of "Select something on the left"  ·  score 31  ·  M / med
**Lens:** wayfinding. **Evidence:** Build/Import/Story/Models/Save/Co-op show "Inspector / Select something on
the left" while selecting a node **jumps away** from the tab (`shell.py:3519`) — ~220px of dead space plus a
false instruction. **Verdicts:** J1 ask · J2 ask · J3 ask (unanimous ask). **Chair ruling: ASK-USER — kill the
false string; the full per-tab card is the trade-off.** Repainting the shared `insp_body` per-tab makes it
stateful across tabs, and the regression surface is exactly the Author-return path (must cache and restore the
tree-driven card verbatim) — the shared-panel-lifecycle class that bit rounds 7-9. **Recommendation:** the
low-risk half (collapse the false "Select something on the left" to a thin muted rule on self-contained tabs) is
clearly right and could be split out; the full context card needs the owner's appetite for the restore path.
**→ BUILT 2026-07-24 (low-risk half):** the untouched inspector's empty-state is tab-aware
(`shell._insp_empty_text`) — the instruction shows only on the Editor tab over a populated tree; everywhere
else (and over an empty tree) a thin muted rule. The full per-tab context card remains an owner decision.

### 15. One machine-health readout shared by Setup and the Co-op status card  ·  score 31  ·  M / med
**Lens:** consistency. **Evidence:** Setup renders `health.health_report()` as a colored triage grid
(`setupdialog.py:106-119`) while Co-op re-derives the same install/netsync facts with its own probes in
different words (`coopdoc.py:345/368`) — Co-op even ships an "Open Setup" button pointing back at the panel it
paraphrases. **Verdicts:** J1 ask · J2 build · J3 ask. **Chair ruling: ASK-USER — genuine self-contradiction,
judgment on depth.** `health_report` is a flat list with no per-name lookup and no netsync-generation knowledge,
so it needs a `summary_row` helper and Co-op keeps its own s36/s37/s40 detail — a 4-file refactor whose
unification depth is a call, and it touches coopdoc's `_refresh_status` (round-9's fragile surface).
**Recommendation:** worth it; extract carefully.

### 16. Bring the game to the front after a test deploy  ·  score 30  ·  M / med
**Lens:** veteran-loop. **Evidence:** post-deploy guidance is "in your game, press ~" but the game is behind the
Workspace; `game_snap.ps1` already locates the window by the "FINAL FANTASY IX" title. **Verdicts:** J1 ask ·
J2 ask · J3 ask (unanimous ask). **Chair ruling: ASK-USER — opt-in and inert, but trade-off-laden.**
`SetForegroundWindow` focus-stealing is refused on Windows without the FlashWindowEx fallback dance, it is
win32-only, and the stretch SendInput tilde-tap is a synthetic keystroke that could land mid-load. **Recommendation:**
if approved, ship only the raise/flash (opt-in, default off); leave the tilde-tap out.
**→ BUILT 2026-07-24 (as ruled):** `workspace/gamewin.py` (toolhelp PID scan + EnumWindows, restore →
SetForegroundWindow → FlashWindowEx fallback, fail-soft), `prefs.raise_game_after_deploy` default OFF with a
Preferences row; fires from `_proc_done`'s deploy-success branch, yielding to the first-deploy card. No tilde-tap.

### 17. Deploy-on-save: watch the aimed field.toml and re-deploy  ·  score 30  ·  M / med
**Lens:** veteran-loop. **Evidence:** no `QFileSystemWatcher` exists anywhere in `workspace/`, so a hand-edit in
an external editor (which CLAUDE.md §4 explicitly allows) never reaches the app, and `_save_all` can write stale
in-memory data over an external edit. **Verdicts:** J1 ask · J2 ask · J3 ask (unanimous ask). **Chair ruling:
ASK-USER — biggest feasibility surface in the set.** J3 rates it closer to **L** than the tagged M: watcher
drop-on-atomic-replace re-arming + debounce + auto-deploy chaining + the dirty-member guard, and it depends on
ASK #1 to be non-modal; a background auto-deploy daemon is surprising default behavior. **Recommendation:** the
dirty-member guard is the right protection; if approved, keep auto-deploy behind an explicit opt-in and treat as
a larger piece.

### 18. Depth in the band — the hero's dead right half  ·  score 30  ·  S / low
**Lens:** identity-delight. **Evidence:** content sits in the left ~350px while the near-bloom is left-of-centre
(`hero.py:350`), so the right ~55% of the band is a flat void. **Verdicts:** J1 ask · J2 ask · J3 ask
(unanimous ask). **Chair ruling: ASK-USER — pure taste on THE signature surface, no law violation.** Palette-as-
climate only (one extra QRadialGradient after the mist fill, static, self-fenced below the near-bloom alpha),
but whether the right-half negative space is a void or intentional is an eyeball call, seen for 5 seconds.
**Feasibility note (J3):** the fence should assert text-zone non-overlap, not just peak-alpha ordering, because
narrow windows compress the geometry. **Recommendation:** owner's aesthetic call.

### 19. The first-deploy moment gets its one occasion (MERGE A: #3 + #21)  ·  score 29  ·  M / med
**Lens:** first-run + identity-delight. **Evidence:** the milestone the whole edit→deploy→~ loop exists to reach
surfaces only as a Problems verdict line visually identical to a lint pass (`shell.py:8056`). **Verdicts:** #3
J1 ask/J2 ask/J3 ask; #21 J1 ask/J2 ask/J3 ask. **Chair ruling: ASK-USER via #3's restraint-safe vehicle (a
once-ever `fit_dialog` success card gated by a `first_deploy_celebrated` pref); #21's animated-signet-on-Build
vehicle is REJECTED (see below).** A once-per-install warmth moment is defensible; the vehicle must not be gold
ink on the ratified-flat work surface. **Note:** BUILD-NOW #4 (copy-warp) and ASK #6 (undo) already give the
post-deploy moment *functional* weight — the owner may decide the functional affordances are enough and the
celebration is optional.
**→ BUILT 2026-07-24 (MERGE A's vehicle):** `shell._celebrate_first_deploy` — a once-ever palette-only
fit_dialog card ("It's in your game" + the ~ walk with the warp id), gated by the has_deployed latch read
pre-latch (no second pref), `.open()`-non-blocking (the modal law). No gold, no animation.

### 20. Bridge the two "flags" — authored [[flag]] defs and a save's story bits  ·  score 29  ·  M / low
**Lens:** wayfinding. **Evidence:** "flags" names two things — the tree's authored `[[flag]]` definitions and
Story State's runtime save bits — with a one-way data bridge (`set_flag_names`, `savedoc.py:171`) but **no
navigation** either direction. **Verdicts:** J1 ask · J2 build · J3 ask. **Chair ruling: ASK-USER — principled
but niche.** A cross-link (not a rename) that spends the existing `set_flag_names` map as navigation, but it
serves a narrow intersection (users who both author `[[flag]]`s and edit saves) and the integration spreads
across linkify + a navigate signal + shell routing + a reverse xref. **Recommendation:** low priority; the
cheapest slice (Story State's empty-state clause "Bit names come from your open project's `[[flag]]` list") is a
near-free legibility win if the strings pass didn't already cover it.

### 21. A "Where things live" index on Home  ·  score 29  ·  M / low
**Lens:** wayfinding. **Evidence:** the intent→place question ("where do I set BGM / host co-op") is answered
today only by rail-hover tooltips or Ctrl-K rows that require knowing the destination name. **Verdicts:** J1 ask
· J2 ask · J3 ask (unanimous ask). **Chair ruling: ASK-USER — overlaps existing Home real estate.** J3 verified
Home **already** carries an object-level intent index (`shell.py:1739-56`: Journey/Campaign/Field/Battle/Import/
Models/Save with Go-to buttons); this adds a second, task-phrased index that overlaps it and the concept map,
risking two competing indexes on one screen. Correctly gated goes-away, so law-clean. **Recommendation:** only
if the owner wants sub-object intents ("set BGM", "see a flag") that the existing object index doesn't carry —
otherwise redundant.

### 22. The signature on the colophon — the About box earns the signet  ·  score 27  ·  S / med
**Lens:** identity-delight. **Evidence:** the About box (`shell.py:1027-67`) is the app's colophon yet carries
no signet — the gold corner lives only on Home. **Verdicts:** J1 ask · J2 ask · J3 ask (unanimous ask). **Chair
ruling: ASK-USER — contract-consistent, spends the gold budget for low value.** The SIGNET brief lists About
among the 5-second identity surfaces and `signet_elbow` at reduced ink follows the LedeCard precedent, so it is
**not** a "more is a costume" violation — but any second gold mark is precisely where the one-accent debate
reignites, on a rarely-shown surface. **Recommendation:** owner ratifies the gold spend; feasible (a small
painted header modelled on LedeCard) if yes.

---

## REJECTED — 1 item

### #21 (vehicle) — "It's in the game": animate the signet gesture on Build & Deploy
**Lens:** identity-delight. **Killed on:** the SIGNET contract + a **settled question**. The sketch traces the
gold `signet_elbow` reveal animation on the **Build & Deploy** tab — the 3-hour work surface where "the lamp on
Build & Deploy (flat, user-ratified)" is explicitly off the table and restraint is strictest. All three judges
scored it lowest of the delight set (combined 25) and flagged the work-surface gold; J2 gave it the weakest fit
in the entire set (fit 2) and recommended "the banner-side P18/P31 instead"; J3 noted it also **under-costs its
surface** (there is no painted host on the Build tab, so it needs a transient overlay widget with its own
paintEvent + animation timer — more than "reuse the reveal"). **The concept is not lost:** the once-per-install
first-deploy celebration survives in ASK-USER #19 via a restraint-safe `fit_dialog` card. Only the
animated-gold-ink-on-a-work-surface **vehicle** is killed, so it is not re-litigated.

---

## Summary

| Bucket | Count | Notes |
|---|---|---|
| **BUILD-NOW** | 12 | unanimous `build`, all cost S/M + risk low |
| **ASK-USER** | 22 | includes 2 merges (A: #3+#21 concept, B: #4+#36) |
| **REJECTED** | 1 | #21's animated-signet-on-Build vehicle (SIGNET law); concept preserved in ASK #19 |

**Cross-cutting sequencing the owner should know:**
- BUILD-NOW #10 (mirror job state) uses the elapsed timer from BUILD-NOW #3 — land #3 first or together.
- ASK #12 (beginner-mode lever) depends on BUILD-NOW #5 and ASK #5 (the two disclosures) existing first.
- ASK #4 (real-field picker) and ASK #5 (Walk-as disclosure) **conflict** over the "Suggest a test room…"
  button — decide its placement once.
- ASK #6 (undo on banner) and ASK #8 (jump-to-error) both hit the same wall: `self.banner` is a plain QLabel,
  not a clickable host — route their actions through the spine action-tuple / a clickable Problems row instead.
- BUILD-NOW #4 (copy-warp) + ASK #6 (undo) already give the post-deploy moment functional weight, which may make
  the ASK #19 celebration optional.
