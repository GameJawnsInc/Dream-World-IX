# GUI aesthetics — state + next steps

> ## ROUND 13 — THE SQUEEZE, THREE PANES DEEP (the detailed UX pass)  ·  ⚠ PLAYTEST PENDING
>
> A full-surface sweep (all 45 pinned surfaces × 100/150%, every PNG read) against the current master.
> **The round's one theme is round 7's law reaching INSIDE the docs: a pane that cannot get its content's
> width must degrade honestly (wrap, elide, scroll, or a visible door) — three shipped surfaces silently
> CLIPPED instead.**
>
> 1. **The Inspector card clipped its own text wherever a thumbnail rendered.** `_inspect_field` baked
>    `<img width="300">` into the rich text; a rich-text img is ATOMIC, so 300 became `insp_body`'s
>    minimum, the widgetResizable host laid the WHOLE card out at ~320 in the 240px default pane, and —
>    with the h-bar off — Qt CLIPS, text and all (map:art read "2 cutscenes (8 ste"). It looked healthy
>    on home:open only because the harness had no thumb there — **on any thumb-warm machine every field
>    card clipped.** Fix: `_thumb_img_attr(w, h, avail)` (pure, fenced) sizes the img from the PANE at
>    render, and a coalesced 200ms refit re-bakes on pane resize (the `_on_thumb_ready` re-render
>    precedent). The rendered-width invariant `(h_attr·w)//h ≤ avail` is fenced for the tall branch too.
> 2. **The Models tab's right editor pane clipped mid-glyph at the DEFAULT window** ("Copy [[npc]] snip",
>    "Deploy r", "Min" — and at 150% it was a sliver). Two causes, one deficit: the one-row filter strip
>    (combo + two checkboxes; a checkbox's label IS its minimum) put a ~450px floor under the LEFT pane,
>    and the right scroll area's h-bar was `AlwaysOff` — which under widgetResizable means CLIP, not
>    scroll, exactly against its own "never clip sideways" comment. Filters now stack two rows; the bar
>    is `AsNeeded`; fenced by driving the splitter to a squeeze and asserting the bar actually appears.
> 3. **The squeezed toolbar's overflow door was INVISIBLE.** At 150% (or ≤~900px at 100%) Qt folds
>    Refresh/Lint/Info Hub/**Search**/Settings into the extension button — whose Fusion arrow painted
>    invisibly at 12px wide. The probe chain mattered: a widget `setMinimumWidth(28)` left the button
>    hanging 9px OFF the window edge, because **`PM_ToolBarExtensionExtent` both sizes and places the
>    button** — the fix is `_DwixStyle(QProxyStyle)` overriding that one metric (28) + the themed
>    chevron icon + an a11y name, pixel-verified at 860px and 150%.
> 4. **The search button chopped its own teaching** ("Search anything (C" at the default 1280 window —
>    QPushButton has no elide). `widgets.ElideButton`: an honest …, full string kept in accessibleName,
>    and the sizeHint PINNED to the full text — NameLabel's documented relayout trap, applied to a button.
> 5. **New Campaign's "First field id" was the LONE id box outside the band lesson** (BUILD-NOW #6 missed
>    it): a plain `QLineEdit("4000")`, no caption, `int()` straight into `new_campaign` — a real-band 100
>    sailed through. Now `widgets.id_field` + `pack.check_custom_id(what="first field id")`, fenced in
>    the wave2 file's exact voice-assert shape.
> 6. **Strings a user scans:** "(seed 506 · 1 fields)" → "1 field" (region catalog); "300 match(es)" →
>    real plurals (CatalogPicker + field cards); the realfield picker dropped the per-row "[realfield]"
>    chip (noise in a single-kind list) and now shows the id — twin names ("Interior" ×4) were
>    indistinguishable, and the id is the very value the pick fills in; "Fork battle…" / "Fork a
>    battle…" unified; the drift dialog's "no changes since the deploy…" heading capitalized.
>
> **Read but NOT built (owner territory):** the hero's dead right half (ASK #18, already queued), the
> RECENT rows' noisy worktree paths, Models list row height with previews off, Info Hub song ordering,
> and the Battle tab's duplicated header/empty-state verbs (labels unified; the duplication kept — the
> header pair persists once a map is open).
>
> Suite 4454 → green + the new fences; every touched surface re-snapped and READ (models 100/150,
> map:art, new-campaign, fork-regions, drift-synced, battle, home 100/150/860px). ⚠ Nothing here has
> been seen by a human in the running app.

> ## ROUND 12 — AHEAD OF THE GAME (what changed since my last deploy?)  ·  ⚠ PLAYTEST PENDING
>
> **The weak area is named in the brief's own loudest law:** *"One change per in-game test. When a build
> breaks, we need to know which edit did it."* — and **nothing in the toolkit could answer *which edit*.**
> The deploy path already records a successful deploy's target, id, destination and revertibility, but only
> in memory (`_proc_done`), so the moment you keep editing, "what is in the game" is something you hold in
> your head. Obeying the project's hardest process rule was a memory exercise.
>
> One mechanism — a **parsed project snapshot taken at deploy time** — three surfaces: a status-bar **drift
> chip** (`game: in sync` / `game: 3 ahead`), a **change list** (Ctrl-K → "What changed since my last
> deploy?"), and the **law itself** stated in the tooltip/dialog once there is more than one change under a
> test. New: `editor/tomldiff.py` (pure), `editor/deploysnap.py`, `gui_snap console:*`→ plus `drift:*`.
>
> **NO NEW MODAL, and that was a constraint rather than a preference.** The obvious home for a
> one-change-per-test warning is an F9 confirm — but **ASK #1 deliberately removed exactly that confirm**
> ("make F9 a true one-key loop"), so putting one back would undo a ratified decision. An always-visible
> chip costs zero clicks and says it earlier.
>
> **★ THE DESIGN'S REAL CONTENT IS ARRAY IDENTITY.** A field.toml is mostly arrays of tables (~38 kinds).
> Matched by INDEX, deleting `[[npc]]` #0 reports *"npc[0] changed, npc[1] changed, npc[2] removed"* — three
> rows for one edit, a text diff wearing a schema's clothes. Matched by identity it reports one removal.
> **The first design was an ordered list of candidate key fields, and the corpus killed it:** measured over
> every kit toml in the repo it missed `requires_flag` (the only thing separating two gateways to the same
> field) and `give_folklore` (five events distinguished only by their payload) — *because a gating list rots,
> and this kit grows a new block most weeks.* The fix inverts it: **every field present on every entry is
> ELIGIBLE; the preference list only RANKS what already works; the smallest unique key wins.** Census: 27 kit
> tomls / 34 array kinds / 41 multi-entry arrays → **37 of 41 identified (90.2%), zero ambiguity**, and the
> only remainder is `cutscene.steps` — an ordered script, where **a beat's identity IS its position** and
> index is the right answer. Composite keys were measured too and rescue exactly one case (`edge` → to+from).
>
> **The key is derived from the UNION of both sides**, because the same census found `gateway` keyed by `to`
> in one file and `requires_flag` in another: a key unique on the old side can collide on the new one.
>
> **Two truths, deliberately not conflated** — the snapshot records **disk** (what the subprocess actually
> deployed), the live count reads the **open doc** (what you are looking at, unsaved edits included).
> Conflating them either hides unsaved work from the count or records edits that never reached the game. And
> the capture happens **at launch, not on success**: a build takes seconds, and a save landing mid-run would
> otherwise be recorded as "already deployed" — the very edit under test would vanish from the next compare.
>
> **Why not a text diff, fenced rather than asserted:** the kit's serializer preserves neither comments nor
> key order (its contract is round-trip *value* equality), so the first GUI save of a hand-written toml
> rewrites the document. `test_a_text_diff_would_report_a_rewrite_where_this_reports_nothing` measures both
> halves — **>20 changed text lines, zero changed meaning.** And **not a rollback**: this repo has git and
> its owner uses it; the scarce thing at a playtest is attention, not storage.
>
> **Defects found by driving it, not reading it:**
> 1. **A multi-file diff lost its file prefix on array rows** — `_label` rebuilt the string from the array's
>    own name and discarded every parent segment. `Change.file` is now separate from `Change.where`, which
>    also lets the UI **group rows by member** (a campaign's changes read per room).
> 2. **The last job… er, the last FILE's final character was chopped** — `end - 1` drops the newline that
>    belongs to the next file's header, and the last one has no such newline. Measured on a traceback's
>    closing quote.
> 3. **`QMessageBox(self).exec()` is an INSTANCE, not a static** — gui_snap's static stubs could not see the
>    unsaved-changes prompt, so `drift:ahead` (which deliberately leaves unsaved edits) hung the harness with
>    **no output at all**. `faulthandler.dump_traceback_later` is the tool for a silent hang; the guard now
>    stubs both kinds, to **Discard** (a snap must never *write* the user's project).
> 4. **I broke the shared harness with a one-line env var.** Redirecting the snapshot cache via
>    `FF9MAPKIT_DATA` also redirects **`provision.data_dir()` — the templates dir** — so every surface's
>    template lookup pointed at an empty directory and the first snap hung. **One knob, two meanings:** the
>    redirect is now scoped to `deploysnap.snap_dir` alone.
> 5. **The chip reported "in sync" about a project the user had just closed** — it was keyed on the Build
>    tab's path box, which *deliberately* survives a close (round 10 persists the destination). Gated on the
>    same `_current_target()` predicate Home's guide uses.
> 6. **`setProperty("mono", True)` on a QListWidget styles nothing** — style.py's rule is
>    `QLabel[mono="true"], QLineEdit[mono="true"]`. Dropped rather than extended: the rows are a dotted path
>    *and* a line of dialogue at once, and the kit's own DICTION rule is "mono on a sentence reads as a bug".
> 7. **The list is a `QListWidget`, not a `QPlainTextEdit`** — because `fit_dialog` sizes a populated list
>    from real content while a text box's sizeHint is a fixed ~256×192 whatever is in it. The first cut opened
>    **368px tall for three rows**; using the mechanism that already exists also bought keyboard nav and
>    per-row tooltips carrying the unelided values.
>
> **And one of my own fences tested the wrong `except` clause:** the "never load-bearing" check used a NUL
> byte in the path, which raises `ValueError`, not `OSError` — a situation no machine is ever in. The code was
> right (the project's convention, stated in `deploylog.py`, is to swallow *filesystem* errors only, because
> "a silent swallow of a TypeError is how a guard rots"); **the unrealistic failure mechanism was the bug.**
> Re-fenced with a file sitting where the directory should be.
>
> All three sabotage runs (index matching / ignore `from_disk` / drop the open-project gate) go red on exactly
> the right fences. Suite **4229** (+35 new). ⚠ Nothing here has been seen in the running app by a human.

> ## ROUND 11 — THE LOG IS A DOCUMENT (find + a job spine for the console)  ·  ⚠ PLAYTEST PENDING
>
> **The weak area, stated precisely: there was no find ANYWHERE in this app.** `Ctrl+F` was unbound
> app-wide, and the surface that needed it most is the one the app streams every build, deploy, lint and
> import into. An earlier round made `run_job` stop clearing the console on purpose — *"the header is a
> SEPARATOR, and a separator with nothing above it separates nothing"* — which turned Output into a
> **multi-job document** of up to 5000 blocks and left it with a drain's three controls: Wrap,
> Copy-everything, Clear. Its own structure (the `[HH:MM:SS] subject` head lines, which the GUI writes
> **itself** and therefore knows with certainty) was spent by nothing.
>
> One mechanism — the head-line index — three affordances: **find** (Ctrl+F, incremental, match count,
> Enter/Shift+Enter, wrap, highlight-all, Esc), **jump to a job** (a `Jobs` menu, newest first, ✓/✗/⏹ by
> shape not colour), and **copy just that job** (a jump selects the span, so the OLD Copy button becomes
> per-job — the new mechanism pays for the existing control instead of adding one).
>
> **★ THE MEASUREMENT KILLED THE NAIVE BUILD BEFORE IT SHIPPED — the NINTH-GROUND LAW, on the one surface
> that had no ground but its own.** A find highlight is a *third* colour painted under the log's text, so
> `contrast(log_fg, log_bg) >= 4.5` says nothing about it. Probed across all 8 palettes
> (`evidence/probe_find_ground.py`): letting the log's own ink ride an accent highlight measures
> **1.16 (solarized-dark) to 3.43 (nord) — sub-AA in EIGHT of eight**, i.e. the current match would have
> been the *least readable line in the log*, in every palette. The quiet tier was sub-AA in solarized-light
> too (4.42). So the loud tier reuses the **authored** `accent`/`accent_fg` pair (already fenced) and the
> quiet tier gets two derived tokens, `find_bg` (`_find_token`) + `find_fg` (the existing `_fg_token` rule).
>
> **`selection_bg` was the obvious reuse and it was wrong** — it is derived against `surface`/`hover`, the
> *tree's* ground. The console's ground is `log_bg`, a different and deeper fill in every palette. Reusing it
> would have been this study's most-repeated defect: a fence set on the wrong ground.
>
> **And `_selection_token`'s 20/255 floor was also wrong here, which is the round's transferable bit.** At 20
> the mist render *painted* the quiet match correctly — **339 measured px of the token, so the mechanism was
> right** — and it still read as a smudge, not a mark, on a near-black well. Same delta, less perceived.
> `FIND_TINT_FLOOR = 44`, swept at 4× nearest-neighbour on both extremes (mist's deepest well, cream
> solarized-light) via `evidence/shot_find_tier.py`: 20 reads as an artifact, 32 as a mark, 44 unambiguously.
> **A visibility floor is calibrated per GROUND; it does not transfer between tokens.** The ceiling is
> numeric, not taste: 44 keeps the derived ink ≥4.77:1 in all 8 and every palette ≥60 raw channels from the
> accent. **And the sweep corroborated the ink token independently: `contrast(log_fg, find_bg)` FALLS as the
> floor rises** (solarized-dark 4.52 → 3.55) — visibility and inherited legibility pull in *opposite*
> directions, so no floor exists at which the naive build is both visible and legible. The two tokens are the
> only shape that works.
>
> **Seven live defects, each caught by driving the thing rather than reading it:**
> 1. **`QPlainTextEdit.ExtraSelection` does not exist in PySide6** (it is `QTextEdit`'s) — an AttributeError
>    on the first keystroke of the first search.
> 2. **`self.pal` is the RAW palette**, so `pal["find_bg"]` KeyErrors — the trap `Workspace._derived` exists
>    to document, hit again by a new module.
> 3. **The last job's span chopped its final character** (`end - 1` with no next head to trim) — measured on
>    a traceback's closing quote.
> 4. **Two jobs sharing a head string both resolved to the first occurrence.** A head is `[HH:MM:SS] subject`,
>    so two Checks in the same second are byte-identical; the spans are now built cumulatively, in order.
> 5. **Shift+Enter never fired.** It lived on a QShortcut hosted by a hidden zero-size QPushButton — Qt
>    disables shortcuts owned by an invisible widget — while the ▲ button's tooltip advertised the key.
>    Measured: 1/3 → **2/3**, i.e. `returnPressed` won. Esc would likewise have been eaten by
>    `setClearButtonEnabled`. Both keys now live on a `QLineEdit` subclass that owns them.
> 6. **The find bar paid for itself out of the log.** The console opens ~152px, so a ~46px bar inside it left
>    ONE readable line and clipped the next mid-height — the squeeze law in the panel that exists to be read
>    *while you search it*. The height now comes from the DOCUMENTS pane, and is given back **only if the
>    split still reads as the one we set** (round 7's law cutting the other way: a divider the user dragged
>    while searching is a preference, and restoring blindly would discard it).
> 7. **Two dropdown arrows on the Jobs button** — an InstantPopup QToolButton draws its own indicator, so the
>    typed `▾` was a second caret. Visible only in the 150% snap.
>
> **Two of my own fences were set at the wrong bar, and the second one is the sharper lesson:**
> - `test_the_find_highlight_cannot_inherit_the_logs_own_ink` first demanded `find_fg` beat `log_fg` in every
>   palette and went **red on dracula, where the two are byte-identical** (`#f8f8f2` is that palette's
>   `log_fg` *and* its `text`, and `_fg_token` returns its input unchanged wherever the palette already
>   clears AA). That is the rule working as designed. A fence at "strictly better everywhere" would have
>   forced a pointless second hex into dracula; the honest contract is *never worse* per palette **plus**
>   *load-bearing at least once* across them.
> - The miss state's fence asserted `count.property("state") == "error"` — **a property is not a rendered
>   colour.** The counter also carries `role="muted"`, and `style.py`'s own `QLabel[role="muted"][state="warn"]`
>   two-attribute rule exists precisely because that cascade did not go the obvious way for warn. Re-measured
>   from pixels: hit → `#9fadc4` (`muted`), miss → `#ff6b6b` (`error_text`). The error rule does win — and the
>   fence now says so from pixels.
>
> **Not capped, because it was measured, not guessed:** at full log depth (5000 blocks / 179k chars) a
> refresh+repaint is 27ms for 5,000 matches and 58ms for 10,000 (the single letter `o`), against a 180ms
> coalescing window. A cap would have to either lie in the counter or announce itself; neither is worth
> buying at 58ms.
>
> All three sabotage runs (naive ink / no tint / merged tiers) go red on the right fence with the right
> message. `gui_snap` grew **`console:log|find|miss|jobs`** (a pinned 3-job session with fixed timestamps — a
> random clock breaks pixel-diffing the panel's most prominent line) and grabs the console panel *as well as*
> the window, because a highlight tier judged from a downscaled 850px shot is the "sample the button, don't
> squint at the screenshot" mistake. Suite **4194** (+28 new fences, 263 skips = this worktree's un-extracted byte-level templates, none of them GUI).

> ## ROUND 9 — THE CO-OP TAB, and the trap that unfilled every button  ·  branch `claude/gui-coop-tab-round9`
>
> The first round driven end-to-end by the snap loop: `gui_snap` grew pinned **co-op machine states**
> (`coop:nogame|stock|s36|s37|ready|live` — a scratch fake install writes the engine marker bytes +
> Memoria.ini, so every state renders on ANY machine) and a **full-page grab** (the scroll's inner
> widget at content height, so below-the-fold is in the record).
>
> **★ THE HEADLINE FIND WAS NOT CO-OP-LOCAL. The first full-page grab showed the page's one accent
> verb — "Start co-op" — rendering as an EMPTY BOX.** Probed, not eyeballed: `page_column` shipped the
> BARE `setStyleSheet("background: transparent;")` — the study's own trap #4, whose fix (`.QWidget`
> exact-class) sits eleven lines above a comment in shell.py explaining exactly why — and a bare
> property list cascades to every descendant and beats the app sheet. **Every button on all three form
> docs (build / import / co-op) had NO fill since round 5 part 6.** Nobody saw it because a default
> button's ink is `$text` — light, readable on the bare page; the accent tier's authored DARK ink
> (`accent_fg #08171b` on mist) was the tell, and only on the one doc whose accent button lives in the
> page body rather than the crumb row. Fix: ONE constant, `widgets.TRANSPARENT`, and shell aliases it
> (the second hand-typed copy of a rule is exactly where the bare form came back). Fenced twice, both
> verified RED on the bare form: a PIXEL fence (an accent button inside a page_column must render
> `$accent` — colour-only, offscreen-safe) and a census (no property-only `background` sheet on any
> container with child widgets, on the real shell).
>
> Co-op tab proper (all from the snaps, `tools/scroll_out/gui_snaps/coop-*`):
> - **The status warning now carries its own door**: "run Setup & health… first" / "install the custom
>   engine first" get an `Open Setup & health…` button beside Refresh, shown exactly while the game is
>   missing or the engine lacks netsync, gone on a healthy machine (truth-table fenced, pinned via a
>   tmp fake install — never this machine).
> - **The ghost combo hard-clipped its own selection** ("Their own model (classic gl") —
>   `minimumContentsLength(18)` makes the closed box's sizeHint 18 chars and the trailing stretch hands
>   it nothing more; Qt clips with no ellipsis. Items shortened to fit + length 31 + a pure-arithmetic
>   fence (every item ≤ the length — platform-proof, no text-derived widths).
> - **The bottom hint wrapped at ~135 ch/line** (the COLUMN defect, on the one doc COLUMN missed) →
>   `widgets.caption`.
> - Verified across mist/light and 100/150%: the accent fill is back in both palettes, disabled Start
>   shows its label, the s37 state greys only the diorama row.
>
> Also from the 150% record shot: the Status KEY COLUMN clipped ("gameC:", "enginnetsync") — `kv()`
> took a px width the CALLER measured at construction, in the pre-QSS font, never again. `kv` now takes
> the widest key STRING and the key label re-measures itself on FontChange (the GAUGE pattern); the
> fence's first lever (setFont) was DEAD — QSS re-resolves fonts over programmatic setFont — so the
> fence drives the real dial.
>
> **⚠ THE ADVERSARIAL REVIEW WAS RIGHT A THIRD TIME (25 agents, 18 confirmed / 2 refuted), and again
> the worst finding was mine writing to the developer's machine:** the round's own module-scoped test
> fixture ESCAPED conftest's function-scoped prefs isolation on both ends (pytest builds wider scopes
> first, finalizes them last) — its teardown `close()` ran `_save_layout` after the isolation unwound
> and **overwrote the developer's real prefs layout with a never-shown offscreen window's squeeze
> fossil `[70, 494, 68]` on every suite run** — round 7's disease, re-shipped by the file whose header
> states the law (proven end-to-end by the verifier with a decoy LOCALAPPDATA). The fixture now pins
> `prefs._path` + `find_game_path` for its whole life. The review's other keepers, all folded in: the
> ghost combo's pre-existing `setMaximumWidth(340)` VOIDED the new 31-char floor at 125/150% (measured
> natively: hint 436 vs cap 340 = a 37px mid-word clip with the new fence green — the px cap is gone
> and the fence grew a no-cap half); the s36 engine got the amber "needs the newer s37 engine" warning
> with the door HIDDEN (warn keyed `not has_s37`, door keyed `not has_netsync` — same predicate now,
> s36 leg fenced); the door never re-measured after the modal Setup dialog returned (the goes-away law
> on my own new affordance — `_open_setup_and_recheck`); `_pad`'s frozen pre-QSS floor (FontChange
> filter); the census fence's leaf exemption was a HALF-FENCE (a bare sheet poisons the leaf's own
> state rules — exemption dropped, modelsdoc's image well moved to selector form); the door test pinned
> `find_game_path` to return None, **a value the production function cannot return** (it raises
> ConfigError — the fence now raises); and gui_snap: `tab:coop` unpinned had photographed the
> developer's REAL SessionCode into the PNG record (now pinned-only), an unknown state FABRICATED an
> s40 machine (KeyError now), the live surface couldn't render the running-bridge row (a real bound
> socket + dummy thread now stand in), and mkdtemp's random path broke pixel-diffing in the status
> row's most prominent line (stable per-state path).
>
> Suite: **3045 passed** (5 fences + the census tightened). The pattern across three rounds is now
> unmistakable: **the review's best find is always me touching the developer's machine from a test.**
**Branch:** `claude/gui-card-readability-eb5d9f` · ✅ **rounds 2–7 MERGED to master + PLAYTESTED** · **3657 tests**.

> ## ROUND 8 — TAILOR + THE GOES-AWAY LAW  ·  branch `claude/gui-beautification-usability-5a20fd`
>
> **The ask:** beginner/guided content clearer and GONE once done; popups sized to their content
> ("New Campaign → Forked Region" the named offender); and a meta-ask — the HARNESS must be able to see
> the app, so iteration is fast.
>
> **THE INSTRUMENT SHIPPED FIRST: `tools/gui_snap.py`** — any surface (Home in pinned fresh / midway /
> ready / veteran / open states, every tab, every modal) rendered NATIVE + Fusion, prefs pinned via an
> explicit prefs.json (the empty-tempdir law: `text_scale` is written, never left to fall through to the
> dev's Windows slider), `WA_DontShowOnScreen` so nothing flashes on the desktop, `QDialog.exec` patched
> to show + grab + reject so every `on_*` opener runs unmodified. PNGs + size diagnostics (shown /
> sizeHint / minimumSizeHint). Every claim below was made from its pixels. Two instrument laws en route:
> - **`processEvents()` does not deliver `DeferredDelete`.** A probe that rebuilds rows (deleteLater +
>   re-add) then grabs photographs ZOMBIE widgets — live-parented, visible, painting under their
>   replacements — that the real event loop buries before its next paint. The Home checklist grab showed
>   a sliver of the OLD step-3 row and 12 extra processEvents rounds changed nothing; the app was fine.
>   `_settle` now sends `QEvent.DeferredDelete` explicitly each round.
> - **offscreen's fake screen is ~800px wide with ~2× advances** — a 64ch dialog hits fit_dialog's own
>   screen clamp there, so a grows-with-the-font fence must use a small `ch` or it measures the clamp
>   working (correctly) instead of the thing under test.
>
> **TAILOR (`widgets.fit_dialog(dlg, ch, list_rows, lines)`)** — *a popup's size is a function of its
> content, and a px constant is not a function.* Measured before: New Campaign opened **309×282** with
> its Folder path truncated to "-mestorf-205c97"; the FF9 region catalog **385×409** — 6 of its regions
> behind TWO scrollbars (a QLineEdit's sizeHint is ~17ch; a QListWidget's is 256×192 regardless of rows;
> and `resize(W,H)` is deaf to CALIBRE by construction). Width is asked in CHARACTERS of the dialog's own
> polished font (the QSS base rule puts $type_body on every QWidget, so the metric moves with the dial);
> lists ask for their longest row + the v-scrollbar (so overflow never grows an h-scrollbar) and
> `list_rows` rows; `lines` carries height for viewers whose content arrives after open. Two laws inside:
> - **A SQUEEZED DIALOG DOES NOT SHRINK, IT OVERPAINTS**: a word-wrapped QLabel (height-for-width) paints
>   its FULL text over its neighbours when under-allocated — measured at 150%, the region catalog's footer
>   painted straight across the list. Height that cannot fit the screen is given back by the LIST (it
>   scrolls; prose does not), floor 4 visible rows.
> - **`adjustSize()` on a window silently caps at ~2/3 of the screen** — i.e. it CAUSES the squeeze it
>   should prevent. fit_dialog resizes explicitly to min(sizeHint, 0.92/0.85 of the available screen).
>
> Spent at **21** call sites (the call-site law): shell's new-field / new-campaign / new-journey /
> add-field / updates / shared-flags / preferences / concept card / about / `_pick_regions` /
> add-journey-row / journey-seed; importdoc's region catalog + the field-logic viewer; battledoc's
> `_choose` + fork-battle; builddoc's Package-mod; tuningdialog; setupdialog; the Ctrl-K palette
> (frameless — a px constant was its ONLY possible size); forms_qt's CatalogPicker + Info-Hub help.
> The first cut shipped 14 and called the rest deliberate; **the adversarial review found 7 of those
> "deliberate" skips were just misses** (incl. `_pick_regions` — the byte-identical TWIN of the measured
> 385×409 catalog, in the same round's own diff radius). Still deliberately unconverted: conceptmap and
> CatalogLibrary (900×580 — complex 3-pane, looked right in grabs; px-deaf to the dial, noted as debt).
>
> **THE GOES-AWAY LAW (`shell._getstarted_show`, pure, truth-table-fenced)** — *onboarding is for someone
> who has not yet done the thing; DONE is measured, never assumed.* The old rule (`setup_incomplete or
> nothing_open`) showed the full newcomer checklist to a VETERAN at every project close — two ticked
> done-rows above the fold while their own Recent list sat below it. Now: dismissed (the Hide link,
> persisted) wins over everything; setup incomplete → show; else show only with no open target AND no
> project history (`prefs.recent()` — raw, an unplugged drive is not a reset). Ctrl-K → "Show the Get
> started guide" clears dismissal + forces it for the session. Everything beginner-voiced (the "New
> here?" intro, the provenance note, the steps, the F9 footer) now lives IN the block and hides as one.
>
> **THE ONE-ACCENT VIOLATION HAD SHIPPED**: the lede card and the guide's primary step were the SAME row
> twice — identical title, note, and verb, two accent "Locate game…" buttons 250px apart (\_lede_state
> reuses the steps; nobody looked at fresh-state Home with both visible). The lede now yields to the
> guide when nothing is open; for a veteran it leads with **"Pick up <most recent>"** (a new rung between
> "Continue <open>" and the newcomer steps). Also caught by a grab, invisible to every test: the lede's
> **"Build & Deploy" rendered as "Build _Deploy"** — Qt ate the & as a mnemonic (the && trap the updates
> dialog already documented).
>
> **Fences:** `tests/test_home_beginner.py` (the full 16-row truth table + the closed-project regression;
> fit_dialog's formula-equality, no-op guard, grows-with-font, list-content, and give-back fences — all
> RELATIONSHIP asserts, offscreen-safe) + the smoke now pins ALL THREE inputs (newcomer 3 rows / lede
> hidden; veteran guide gone / "Pick up" lede; Hide/Show round-trip) instead of reading this machine.
> Pre-existing, flagged not fixed: `test_motion_off_means_the_signet_is_simply_there` fails when certain
> workspace modules run before it (order pollution, reproduced on clean HEAD; spawned as its own task).
>
> **⚠ THE ADVERSARIAL REVIEW WAS RIGHT AGAIN (40 agents, 35 confirmed — the round-6b pattern exactly):
> I recommitted the study's own documented disease inside the block that cites it.** The smoke's first
> GOES-AWAY cut READ `prefs.getstarted_hidden()` live (red smoke on any machine whose owner clicked Hide)
> and WROTE the developer's real prefs.json through `_hide/_show_getstarted` — with the cleanup INSIDE
> the `try` and hard-coded to False (**a reset is not a restore**) — one page below the comment narrating
> why the recent-store is stubbed in-memory "so a smoke run never writes the developer's real prefs.json".
> The dismissal is now stubbed the same in-memory way, and the hostile-prefs fence gained the
> `getstarted_hidden` key (its own comment about "covering the keys that came to mind" had just come true
> again). The review's other keepers: **Close clicked ON Home never refreshed Home** — `setCurrentWidget`
> on the already-current tab emits no `currentChanged` (verified empirically), so the hero kept saying
> "Currently editing" and the lede offered "Continue <closed project>"; now `_close_project` refreshes
> explicitly. The give-back fence was VACUOUS (probe-verified: fit_dialog's own 0.7-screen pre-cap
> absorbed the 400-row ask offscreen, so deleting the give-back passed every assert — rebuilt with fixed
> ballast that forces the branch). gui_snap's fork-battle surface was permanently dead behind a
> `hasattr` guard for a method that never existed, and its docstring's QMessageBox claim was FALSE (the
> static warning/question exec in C++ and would hang a headless run — now stubbed). The new Hide link was
> mouse-only (a tab stop is what Tab REACHES) — and the first fix, a keyboard-flagged QLabel, tripped the
> a11y tab-stop fence itself: under `* { outline: 0 }` a focused label shows NOTHING. Hide is now a
> QUIET BUTTON (the tier already carries the deliberate focus ring for free) + a Ctrl-K Hide command.

> ## ✅ ROUND 7 — THE SQUEEZE: *a squeeze is not a preference*  ·  PLAYTESTED (*"much better"*)
>
> **The report:** *"the default sizes of the left and right panels (the tree and the inspector) are very
> small... as a default they need to be wider."* **The default was not what the user was seeing, and the
> number they were judging had never been chosen by anyone.**
>
> **The bug.** The document column has a hard minimum (542px at 100%, 796 at 150%). When the window is
> narrower than the layout wants, the only panes that can give are the outer two — and they clamp to their
> own minimums (78 / 66). `_save_layout` persisted that clamp **as if it were a preference**. On the next
> launch `setStretchFactor(1, 1)` handed the *entire* surplus to the middle pane, so a layout saved at
> ~700px reopened at 1280 as `[90, 1122, 66]`: **the panels never came back at any window width. One narrow
> session, ever, was permanent.** The user's real `prefs.json` read `[76, 1138, 64]` — reproduced to within
> 2px by seeding a 700px session — and their window is 1280×820 on a 1920 screen, so they had simply never
> seen the actual default (`[300, 738, 240]` at their size).
>
> **The fix.** `_repair_central_split`: an outer pane within 2px of its own `minimumSizeHint` is the fossil
> of a clamp — there was no width there to have chosen — so restore falls back to the default. A pane at
> **exactly 0** is the opposite: `childrenCollapsible` is on, so 0 means the user dragged it shut, and it is
> kept. Hence `0 < size <= floor + 2`. **The default's own width is UNCHANGED** — the user chose to judge
> the real default first rather than have a taste change ride along with a bug fix.
>
> **✅ AND THAT CLOSES THE WIDTH QUESTION: *"much better"*.** `[300, 640, 240]` was right all along; the
> report was never about the default. **The measured 1280 trade-off never had to be spent** — widening the
> panels would have cost the document pane (Models' 700px sizeHint starts scrolling below ~700), and that
> cost bought nothing. *The bug report named a symptom; the fix was one layer below the words.* Had I
> widened the default on the literal ask, the squeeze would still be there, the panels would still have
> been 78/66 for this user, and the doc pane would have been narrower for everyone else.
>
> **⚠ THE INSTRUMENT WAS WRONG THREE TIMES OUT OF FOUR PROBES, and it was never the app:**
> - **offscreen reported `mid_col`'s minimum as 1156** (real: **542**) and "proved" the default was never
>   honoured at all — a complete fiction, and the *same* stub-font-DB artifact that manufactured a 1296px
>   window floor in round 6, wearing a different hat. I had a fix designed for it before checking.
> - **an in-session resize probe FALSIFIED the ratchet** — 1280 → 700 → 1920 recovers perfectly. It does:
>   a live splitter still holds its original `setSizes()` request and re-derives from it on every resize.
>   **The ratchet needs a RESTART to lose that memory.** → **A PROBE THAT CANNOT REPRODUCE THE LIFECYCLE
>   CANNOT FALSIFY A LIFECYCLE BUG.**
> - **"a fat tab pins the column open"** — measured with the user's own 12-field campaign open: `mid_col`
>   stays 542, every tab clears. No.
>
> **The fences, and neither is vacuous** (both re-run against a no-op `_repair`, both go red):
> `test_a_squeezed_panel_is_not_a_preference` **reads the floor at runtime** rather than writing `78` — the
> floor is font-dependent (78 real / 74 offscreen) and that module runs offscreen.
> `test_the_restore_path_spends_the_repair` asserts the **request** via a `QSplitter.setSizes` spy, not the
> rendered sizes: offscreen re-clamps the healed layout straight back to `[74, 1156, 66]`, so asserting
> `sizes()` **fails on a correct fix**. It is the call-site half — this arc's oldest lesson.
>
> **The wider law:** *a value the app COMPUTED under duress is not a value the user CHOSE.* Persistence
> layers cannot tell them apart unless someone writes the tell down.

> ## ✅ FULLY PLAYTESTED — rounds 2–6, 2026-07-16
>
> **The standing risk this study carried since round 2 is CLOSED.** Every direction in rounds 2–5 has now
> been seen in the running app and approved by the user, in stages: *"Mist looks good"* → *"fonts look much
> better"* (QUARTO P1 + RUBRIC) → *"i validated all the standing debt"* (CALIBRE, QUARTO P3, the badge,
> the spine cut, PLINTH) → *"looks good"* (COLUMN, the page column, DICTION, QUARTO P2, HEED) →
> *"playtested, all good"* (KEYLINE, the Co-op card, the Info Hub).
>
> **What that costs a reader: nothing here is now a guess about the screen.** Every number below was
> measured; every look-judgement was made by a human at the real app. Where a claim is still derived rather
> than seen, it says so at its own site.
>
> **What it does NOT retire:** the instrument laws. The renders were right and the *probes* were wrong six
> separate times this round — see "the instrument lessons" below. Playtesting confirms the result; it does
> not make the measurements trustworthy retroactively.

**Merge, as it actually went.** Master moved ~10 commits ahead (overworld/beach work) while this ran. The
earlier claim of *zero* file overlap went **stale before landing** — `CLAUDE.md` ended up touched by both
sides (master's mountain work, this arc's §10 line). Git auto-merged it; both survived. The trap was real
and was avoided: at that moment the main repo sat on `claude/interior-topography-plan-b61671`, so a
`cd repo && git merge` would have landed the GUI work on the topography branch; the landing was
`git fetch . <branch>:master` from here.

> **⚠ AND THAT PARAGRAPH IS ITSELF THE LESSON — it went stale within the day.** By the round-6 playtest the
> main repo *was* on `master`, and `fetch . branch:master` **failed** (*"refusing to fetch into branch
> 'refs/heads/master' checked out at C:/gd/Dream-World-IX"*). The landing was `git merge --ff-only` from the
> main repo instead. **The durable fact is not which branch it is on — it is that the branch is a VARIABLE:
> read it with `git -C <repo> rev-parse --abbrev-ref HEAD` first, and gate on `--is-ancestor`.** Each path
> fails loudly in the other's situation *except* `cd repo && git merge`, which fails **silently**. See
> [[project-ff9-main-repo-branch-trap]].

---

## What shipped

| | |
|---|---|
| `86de3f5` | **Phase 0** — the `:focus::indicator` selector bug **that was the original screenshot**, + the untested `surface_2` contrast rung |
| `685ba1a` `881e468` `0ecfa75` | **The card** — `widgets.section()`, kept and fixed, all 27 sites |
| `58f7deb` | Checked box gets a **tick**, checked radio a **dot** |
| `c1073dc` | **The type pass** — names + captions, the mono register, the accent focus hole |
| `6cab262` | **Hover** — 4 palettes had none |
| `2e7a939` | Co-op Status → a definition list; diagnostics shout |
| `764ca74` `5ed0a21` `11fae9e` `5e61ebd` | **SIGNET** — the Mist palette, the stretch fix, the hero, the Ctrl-K theme command |
| `f1c3867` `b758182` `721fb81` `0dcb2c4` `49c3df4` | **The contrast sweep** — the transparent-container bug, the audit tool, accent-as-text, the accent floor, the status hues, `help`/`muted` |
| `53d2ed9` | **Phase 2a** — the quiet button tier; the action row gets an entry point; coop's Start becomes the accent |
| `cbc0eb0` `7bb91d8` | **Phase 5** — nine radii → three tokens + three geometric pins; one card language; the dead QGroupBox block; the grid gets an int rung and the form docs stop each inventing a page frame |
| `7eaf343` | **The hero writes in `$text`** — defects #8 and #9; the NINTH-GROUND LAW |
| `eb44b96` `9b7d8c6` | **INTAGLIO** (round 4) — one light, from above: four edge tokens, the button ladder finally renders, wells are cut, the console gets a lit lip |

## INTAGLIO — the material (round 4's first build)

**The app was never flat-and-minimal, it was unfinished, and there is a number for it: in LIGHT,
`surface_btn` and `surface` are THE SAME HEX.** A button's fill is 1.0000 against its page.
solarized-dark's `field` IS `surface`. mist's button-in-a-card is 1.0017. The elevation ladder claims a
light source ("higher = lighter") and never drew the light.

**THE RULE:** a control is **RAISED** (lit on top); a container of content is **CUT** (the exact inverse).
Raised and cut are the same two colours in opposite order — that inversion is what makes it read as one
light source rather than as trim on unrelated widgets.

**Anchored on `$border`, never the fill.** Fill-anchored, LIGHT gets d5 on a card — a no-op in the two
palettes that need it most. Border-anchored the carrier lands **d26–d34 in all 8**. And it needs **no
`if dark:`**: `$border` is the app's one already-mode-aware token — above its fill in all 6 dark palettes,
below it in both light ones, 8/8 — so each palette's own border eats the edge it cannot hold.
**Fenced**, because it holds only by convention and a ninth palette that broke it would light every object
upside down rather than fail.

**`EDGE_T = 0.14`, and the render chose it.** At the proposed 0.18 the non-carrier reaches d13–d17 and
five palettes grow a second visible edge — two edges on a raised rectangle is a bevel, and a bevel is
Windows 95. At 0.14 no quiet edge exceeds d13 while the carrier stays 3–4× the fill deltas it replaces.
The ceiling is fenced so the taste call cannot silently decay.

**The rule the accent taught, which was not in the proposal:** *emit both edges only where one of them is
quiet; emit one where neither is.* `$border` is a desaturated grey and has a quiet edge. `$accent` is
**saturated and has none** — dark's `#4c8dff` has B=255, so mixing toward black drops B by 36 while
mixing toward white cannot move it at all (nord: carrier 24 / quiet 22, a symmetric bevel on the loudest
object on screen). So the primary takes a lit top only. Premise and consequence both fenced.

**Not done, deliberately:** the spec's *"kill the bottom radius — a hole in a plate has no rounded floor."*
Rendered first: the wells are inset 8px inside a panel above a `QStatusBar` that draws its own border-top.
The metaphor assumes the hole reaches the plate's **edge**; this one doesn't. Flush would butt the well's
1px lit foot against the status bar's 1px border. **A spec written without the geometry in front of it
does not get to overrule the geometry** — same call as Phase 5's splitter docs.

## Seven live defects found — none visible to a test that reads source

Every one needed a **rendered pixel** or a **computed ratio**, in a codebase that had just finished ten
phases of accessibility work:

1. `:focus::indicator` — a malformed selector boxed **every radio in the app**, and radios had **no focus
   ring at all**. This *was* the "cards don't read well" screenshot.
2. `#accent` out-ranks `:focus` — **every accent button, including the crumb Deploy, had no focus ring.**
3. `hover == surface_btn` byte-identically in 4 palettes — **no button hover feedback at all.**
4. A container's bare `background: transparent` out-ranks the app sheet — the newcomer's primary CTA was
   **unfilled in all 8 palettes, invisible in 5.**
5. `accent` as body text — sub-AA in **6 of 8**.
6. `accent_fg/accent` fenced at **3.0** (the *non-text* floor) guarding a **13px button label** — sub-AA in 4 of 8.
7. `help` fenced against **nothing**; `muted` fenced on 3 of 4 grounds.

8. **The hero's overline inked in `text_subtle`** — 2.5:1, sub-AA in **8 of 8**, on the front door. The
   Rejected table forbids that token for text *in writing*; PLAN.md's Phase 6 spec prescribed `muted`.
   **The implementation drifted from its own spec inside one round** (found by the round-4 workflow).
9. **The hero's status line inked in `muted`** — sub-AA in **3 of 8** (light 3.63, sol-light 3.98,
   dracula 4.35). Found only by measuring #8 properly. Nobody had ever measured it.

**The pattern:** 4, 5, 6 and 7 were all *fences set at the wrong bar, green the whole time.* A fence that
covers 3 of 4 grounds just moves the bug to the 4th.

### THE NINTH-GROUND LAW (from #8 and #9 — durable)

> **Every text tier is fenced against the elevation ramp. A surface that paints itself off the ramp
> voids every one of those fences, silently.**

The mist bloom composites `$text` over the plate and lifts the ground **past `surface_3` in 7 of 8
palettes**. `muted` clears 4.5 on `surface_3` in all 8 (4.57–5.70) and **still fails on that band**
(overline 4.09–4.79, status 3.63–5.37) because it is fenced to sit *at* the floor and has no headroom for
a lifted ground. It cannot acquire any: swept `_MIST_ALPHA` to **zero** and it still only reaches 4.72.
**There is no alpha that makes a dim tier legal on the mist.**

So the hero writes **everything in `$text`** (overline 5.16–12.34, status 4.64–10.85, 8/8), and
subordination comes from **type** — PLAN.md's own law, written before the band existed. The render
confirms it: the 28px serif wordmark still dominates an 11px tracked overline in the same ink.

**Corollary for any future painted surface:** if you invent a ground, you owe it a fence. The ramp's
guarantees stop at the ramp.

### CONTRAST IS NOT THE INSTRUMENT FOR A TINT (REGISTER P1 — the sharpest finding in round 4)

> **A contrast ratio is luminance-only. It is blind to the axis a coloured fill actually uses.**

The tree's selected row painted the **full accent** — the same fill as the primary CTA, on a *persistent*
selection. Replacing it with the tinted `selection_bg` looked fatal by the numbers: **hover out-contrasts
the new selection in four palettes** (gruvbox 1.488 vs 1.294, nord 1.327 vs 1.161, dracula, sol-dark).

Rendered at 4× with a real synthetic hover, gruvbox's selection **wins decisively** — because hover is a
pure *lightness* step (ΔHue ≤2.5°, ΔSat ≈0) while a selection is a *hue/chroma* event (ΔSat up to +0.42,
ΔHue up to 93.8°). The ratio cannot see the thing doing the work.

**But the render also refused to rubber-stamp the argument.** Nord came back *marginal*, honestly so: its
accent is nearly its own surface's hue, so a fixed 16% tint of a thing into a near-copy of itself barely
moves — 11/255 from its own hover, with the rail carrying it alone.

**So the ground and the metric both changed.** A selected row is never confused with the *page*; it is
confused with **hover**. `_selection_token` now raises the tint until the fill is ≥20/255 from that
palette's own hover, as a raw channel distance. **The floor is calibrated to the two renders, not chosen**
— gruvbox reads and sits at 26, nord didn't and sat at 11 — and the metric then independently reproduces
both verdicts: it leaves gruvbox/dark/solarized-light untouched and lifts nord to 0.50. An earlier solve
against *contrast* was discarded for over-tinting gruvbox, which the eye says needs nothing.

**The transferable rule:** when a fence and a render disagree, the render is not automatically right
either — it tells you the fence is measuring the wrong axis. Then go find the axis.

### THE CUT LIST IS PER-FAMILY (REGISTER P2)

NAMEPLATE P1 measured Segoe UI's real weight cuts — `[100-300][350][400-500][550-650][700-800][900]` —
and fenced them. **That list is Segoe's, and the console is not Segoe.** Measured natively:

| face | 550 | 600 |
|---|---|---|
| **Cascadia Code** (dev boxes; ships with VS / Windows Terminal) | a real SemiBold | SemiBold |
| **Consolas** (the clean-Windows fallback; Regular + Bold only) | **byte-identical to 400 — a no-op** | Bold |

So the log's head/echo register is **600**, the first weight that lands heavier in *both* — otherwise it
would silently flatten on exactly the machines without a developer's fonts installed. And note the
advance test that caught Segoe's dead 500 is **blind** here: mono advances never move, only the ink does.

### A SOURCE-GREPPING FENCE MUST READ CODE, NOT PROSE

Three fences in this arc tripped on their **own docstrings** — because the prose beside a rule is exactly
where the rule gets *named*. A docstring saying *"never appendHtml"* fails a naive
`"appendHtml" not in src` on the very file that obeys it. `LedeCard`'s docstring states the gold-stripe
law and failed the gold-stripe fence. `tests/_code_only()` now strips docstrings and comments via
`ast.unparse`; what's left is what executes.

### AND THE BUG THE SOURCE-GREPPING FENCES COULDN'T SEE

The log's `trace` branch called `derive()`, which **was not imported into shell.py**. Every source fence
passed. The whole 3569-test suite passed. The first traceback the console ever streamed would have
crashed the drain. **A probe that DROVE the branch found it in one run.** Reading source proves what the
code says; only running it proves what it does.

### The instrument, and the two that lied first

`audit_contrast.py` **cannot see the hero at all** — it reads ink from `w.palette().color(...)`, a QLabel
API, and the band is 100% `QPainter` with no QLabel children. The front door is invisible to the
instrument **by construction**. Two replacements failed before one worked:

| method | why it lied |
|---|---|
| **model the ground** (bg → gradient → bloom) | needs `_axis()`'s geometry to be right. Applied the bloom at full alpha 40 where the render says ~32. **Wrong by a full point.** |
| **mode of a row strip** | the ground is a *gradient* — hundreds of near-identical colours, few px each — while the ink is **one flat colour**. So the mode returns the ground for a SHORT string and **the ink itself** for a long one. It scored the status line at **1.00 against "ground" == muted** and looked plausible. |
| ✅ **render twice, suppress `drawText`, read the ground under the glyphs** | exact. Legal *only* because the band is paint-only with no layout, so the reflow objection that killed blank-and-diff for the QSS audit does not apply here. |

### THE COMMENT-PLACEHOLDER LAW (it bit twice; a comment could not hold it)

> **`string.Template` has no concept of a CSS comment.** A `$name` inside `/* */` still substitutes — and
> KeyErrors every palette at import the moment that token is renamed or removed. A bare `$` is worse: an
> Invalid-placeholder **ValueError** at import.

It broke the build in Phase 5 (`$gb_margin_top` in a comment explaining the deleted token), then **again**
in INTAGLIO P2 (`$well` in a comment explaining the rejected token) — *after* the file had grown a comment
saying never to do it. So it is now `test_no_placeholder_hides_in_a_qss_comment`, and the fence
immediately found **11 live instances**: comments that had been shipping with their token names silently
replaced by hex values, so the generated sheet's own commentary was lying about itself.

**The transferable bit:** a law that only lives in a comment gets broken by the next person writing a
comment. If a rule can be checked, check it.

---

## Next steps, ranked

### 1. PLAYTEST. (blocks everything else)
Launch it. Look at **Mist** (Ctrl-K → "Theme: Mist (FF9)"), the **hero**, and the **retuned accents** in
dark/nord/solarized. Specifically judge:
- the hero's signet — if it lands thin, IDENTITY.md says **raise `_MIST_ALPHA` before adding a second gold
  element**. One corner, once, or it is a costume.
- **dark's Deploy button is now dark-ink-on-blue, not white-on-blue.** Correct by measurement (3.20 → 5.39)
  and it matches dracula/gruvbox/mist — but it is the most visible change on the branch and it has never
  been seen.
- **solarized-dark's body text was lifted twice** off base1 (+30%). It is the palette with no headroom;
  if it now reads washed, the honest fix is to drop the `surface_3` fence for it, not to re-invert the tiers.
- **The 24px page frame** (Phase 5) is the one deliberately VISIBLE thing in an otherwise silent phase.
  It is a ratio, not a taste: `section()` insets content by 16, so a 16px page frame put each card's
  border exactly halfway between the page edge and its own content — cards stop reading as *on* a page.
  If it now reads loose, `widgets.PAGE_PAD` is one number in one place.
- **Co-op's Start is now the accent** and Package/Disable are unfilled. Verified by probe rather than by
  eye (Start inks `accent_fg` `#181b20`, Disable inks full `$text`, Stop greys to `$muted` when disabled)
  — but *seen* only in an offscreen grab.

### 2. Merge to master.
Disjoint from master's overworld work; merge is clean.

### 3. Both plans are now SPENT — the phase accounting

The question *"do we still have a many-phased plan for beauty?"* has a precise answer: **no, and mostly by
design.** Eleven planned phases across two rounds; here is every one of them. **All eleven are now closed.**

**PLAN.md — round 2, WORKSHOP, 7 phases:**

| | phase | status |
|---|---|---|
| P0 | contrast hole + the selector bug | ✅ shipped `86de3f5` |
| P1 | name the options, demote the paragraph | ✅ shipped `c1073dc` |
| P2 | button ladder **+** mono register | ✅ mono `c1073dc`; **the ladder `53d2ed9`** |
| P3 | ~~kill all 27 QGroupBoxes~~ | ✅ mechanism shipped `881e468` `0ecfa75` — **premise overruled by the user** |
| P4 | widen the dark span | ⛔ **DEAD** — verified: it reverts P0's contrast floors on all 5 dark palettes |
| P5 | radius / spacing / role hygiene | ✅ `cbc0eb0` (radius + roles) `7bb91d8` (the grid) |
| P6 | the Home page | ⇢ **superseded** — SIGNET's hero did this surface instead |

**IDENTITY.md — round 3, SIGNET, 4 phases: ✅ 4 / 4 shipped.** palette `5ed0a21` · stretch fix `5ed0a21` ·
hero `11fae9e` · record `764ca74` (+ `5e61ebd`, the Ctrl-K opt-in).

**So: the small stuff was all that was left — that was not drift.** Of the 7 WORKSHOP phases, 5 shipped,
1 is dead, 1 is superseded. The round framed as the beauty plan produced a hygiene plan; the round framed
to commit produced SIGNET. See the last section for *why* — it is structural, not accidental.

**What Phase 5 found by trying to SPEND the grid rather than read it** (the pattern holds: a fence, or a
constant, that covers most of the app just moves the bug to the rest):
- **`SECTION_GAP` existed, was documented, and had exactly ONE consumer.** Build and Import each hardcoded
  `12` next to a comment calling it "4pt-grid rhythm". Co-op's page frame was an asymmetric `18/14/18/18`
  that nothing explained.
- **Nine radii** (3/4/5/6/7/8/9/10/11). `#search` and `#railSeg` wore a `7px` rung that existed nowhere
  else — a value nobody could have chosen deliberately.
- **A comment the card reversal falsified**: Co-op's gap was annotated *"the box borders are gone — this
  gap IS the grouping now"*. The borders came back.
- **`string.Template` has no concept of a CSS comment.** Naming a dead token as `$name` inside `/* */`
  still substitutes (KeyError); a bare `$` is an Invalid-placeholder ValueError that takes down every
  palette at import. Both broke the build *while the comment warning about them was being written.*

**One spec claim was wrong and was not followed:** PLAN.md prescribed the 24px page frame for **all six**
docs. Models and Battle are **splitter browsers** — their panes *are* the page, edge-to-edge is the
convention, and an outer margin only eats pane width. Only the three **form docs** (one scrolling column
of cards: Build & Deploy / Import / Co-op) take the page rung. The fence says so.

### 3b. If you want MORE beauty, it is a contract renegotiation — not a phase
>
> **RESOLVED 2026-07-16 (round 6).** This section framed the choice as *"round 4 would have to argue the
> contract is wrong"*. Round 6 put the contract's one open question to the user with both states rendered,
> and **the contract won on its own terms**: flat, deliberately. So SIGNET's *"identity where you look for
> 5 seconds, restraint where you work for 3 hours"* is not merely un-renegotiated — it is now **ratified by
> a verdict against the alternative**, with the alternative's three defeats measured (below). The section
> stands; read it as settled rather than as a standing offer.

There is no "make Build & Deploy beautiful" phase to run, and that is **deliberate**. SIGNET's contract
([IDENTITY.md](IDENTITY.md), *What we are NOT doing*) is:

> *identity where you look for 5 seconds, restraint where you work for 3 hours.*

Every work surface — dialogs, console, tree, inspector, toolbar, crumb row, tab strip — is neutral **on
purpose**, and the gold is confined to one corner of one band because *"one corner, once, or it's a costume."*
So extending the identity inward is not the next phase of SIGNET; it is the thing SIGNET forbids. Round 4
would have to argue the contract is wrong.

~~**The one genuine unresolved beauty question**~~ — ✅ **ANSWERED 2026-07-16 (round 6). There are now no
unresolved beauty questions in either plan.**

PLAN.md's **Open Question #2 — "what is under the lamp on Build & Deploy?"** — open since round 2, called
here "the highest-value unshipped *aesthetic* move in either plan", and gated on *"a playtest verdict, not
more research"*. The gate opened when the arc was playtested; round 6 rendered both states natively
(`evidence/shot_lamp.py`) and put them to the user. **Verdict: "A — flat, and close the question."**

**The answer is: on a work surface, nothing is lit — and that is the design, not an omission.** A form's
focal point is its verb. This ratifies PLAN.md's own primary recommendation; the stripe was always the
contingency and its condition ("if the page feels rudderless") was never met. CRITIC.md's charge that the
vision *"never names the lamp"* is now discharged: it is named.

**And the contingency was already dead on the facts, independently of taste** — full receipts in PLAN.md
§Open Questions #2:
- **elevation is unexpressible** (`surface_3` vs `surface_2` = **1.043–1.182, all 8** — invisible), so the
  vision's literal *"one lifted surface"* was unbuildable the day it was written;
- **the spec's number is stale** — "2.44–4.73 in all 7" predates SIGNET's palette retune and MIST; it is
  **2.118–7.095** now, floor below the 3.0 non-text bar;
- **the 4px left-stripe idiom was already taken** by `role="banner"` (status verdicts), shipped **one day
  before** the recommendation was written, and visible beside the doc whenever the console is open.

### 4. Known, deliberate, not bugs
- **The quiet tier is SUBTLE in the two light palettes.** A quiet button is `transparent` (so it shows
  `$bg`); a default button is `$surface_btn`. That delta measures **1.215–1.382 in the six dark palettes**
  but only **1.105 in light and 1.066 in solarized-light**. The *mechanism* is right everywhere (fill vs
  no fill) and the magnitude is bounded by light's compressed surface ramp — the same wall PLAN.md's
  Rejected table already hit ("LIGHT's `surface_3` is `#ffffff` and its rungs step 1.046/1.043. Dies
  there."). Not fenced on a ratio, because a ratio fence would fail light and the honest fix isn't a
  number. Worth a look in light before deciding it needs anything.
- ~~**`PROSE_W = 620`** is wide (~109 chars vs the 45–75 band). User: *"fine with 620 for the moment."*~~
  **STALE — struck 2026-07-16.** `PROSE_W` is **420** and `CAPTION_W` **380** since COLUMN + GAUGE (round 5
  parts 4–5), which measured the tier and capped it. This entry sat in a list headed *"Known, deliberate,
  not bugs"* quoting a user decision that a later round had already superseded — i.e. exactly the
  stale-status defect this file's own header retired for the arc as a whole. A status list is only load-
  bearing if its entries are dated.
- **`SECTION_GAP = 14` is deliberately OFF-GRID** — the one number in `widgets.py` that is. Its grid
  neighbours are 12 (too close to the 8px in-card row gap to read as a different *kind* of gap) and 16
  (ties the card's own interior padding). The grid does not have to own every number; it has to stop
  numbers being anonymous.
- **`page_margins()` is comfortable-only.** The docs are constructed without knowing the density, so
  layout density fan-out is a separate job (it needs `_apply_density` **and** `_finish`'s Cancel path, or
  QSS reverts while layouts stay at the previewed density). `style.space()` already takes a density.
- **The audit's chip false positive** — `audit_contrast.py` reports the breadcrumb chip as
  `#ffffff on #f4f5f7 = 1.09 INVISIBLE` in light/solarized-light. **It is fine** (filled `#2f6feb`, 847px,
  27px of white text; spot-checked). It is shown dynamically, so its geometry is stale at grab time. This is
  the tool's one known limit and its header says so. 8 of the 8 remaining findings are this.

---

## The instruments

`evidence/audit_contrast.py` — every text-bearing control, every tab, every palette. **78 → 8 distinct
findings** over this arc. Read its header before believing any output: it documents two methods that
failed (ink-counting measures antialiasing fringes; blank-and-diff reflows the layout) and the one that
works (ink from `QPalette`, background from pixels).

`evidence/shot_ladder.py` — the action row + page frame, rendered on the **native** platform, with the
quiet rules stripped in the A/B so it varies exactly one thing. It is honest about what it *cannot*
isolate: the button order and the page frame are Python, so both shots share the new layout.

**The eye failed here and the pixels did not — again.** The flat/ranked shots looked *identical* to me at
a glance; sampling the Package button's interior showed `#2b3038` (the default fill) vs `#1e2127` (the
page). A 1.215 delta is real and legible in situ, and invisible in a downscaled review. Sample the
button, don't squint at the screenshot.

**The rule this arc kept re-learning, six times:** *measure the pixels — and know which pixels your harness
is lying about.* Colour is font-independent and trustworthy. Width, geometry, and anything from a
dynamically-shown widget are not. A finding derivable from the palette needs no render at all — prefer that.

## Docs

- **[CORRECTIONS.md](CORRECTIONS.md)** — ⚠ read first. The round-2 plan's headline ("kill all 27
  QGroupBoxes") was **wrong**, and this says how: it measured `surface→surface_2` (1.17) when a card is seen
  against the *page* (`bg→surface_2` = **1.31**, stronger than GitHub's dark card). The user overruled it.
- **[IDENTITY.md](IDENTITY.md)** — SIGNET: the direction, the palette + its fence table, the hero, the build
  order. Generated by a round framed to **commit**, not to refute.
- **[PLAN.md](PLAN.md)** / **[VISION.md](VISION.md)** — round 2. Carry `SUPERSEDED`/`SHIPPED` markers.
- **[CRITIC.md](CRITIC.md)** — the pass that reframed round 2. Still the best doc of the three.

## The methodological finding (the reason round 3 exists)

Round 2 ran 90 agents and produced **hygiene, not beauty** — structurally, not by accident. Its review pass
was tuned to skepticism, and **skepticism is asymmetric**: a defect has a measurement and survives review;
a decoration has only taste and dies. Every decorative proposal was refuted, each refutation individually
correct, and the sum was a plan with no positive vision.

Round 3 inverted the frame — generators had to **commit**, taste was an allowed input, and measurement's job
was to make a committed idea *work* rather than to veto it. That produced SIGNET. **A research harness
optimized to refute will converge on correctness and never on beauty.**

---

## Round 5 — the type floor. And a claim of mine that was false.

**SHIPPED: QUARTO P1 + RUBRIC.** The hint rung 11 -> 12, the body 13 -> 14 (paid for with `tb_space`
6 -> 4), the `forms_qt.py:98` pin 16 -> 18, and `role="cardtitle"` so a card's title stops being the
size and colour of its own footnotes. 3583 tests. *(Playtest status as of writing: unseen. Confirmed
live shortly after — "fonts look much better". The header is the authority; these per-round lines record
the state at the time they were written.)*

### THE SIMULATED-MECHANISM LAW (the one worth carrying out of this round)

I told the user, and then briefed 23 agents as GROUND TRUTH, that *"every hard-coded QSS px is deaf to
the Windows accessibility text-size slider"* — a WCAG 1.4.4 defect. **It is false, and the research pass
killed it:**

- The slider writes `HKCU\...\Accessibility\TextScaleFactor`. It does **not** touch
  `NONCLIENTMETRICS.lfMessageFont`, which is where Qt reads its font. (Set the key to 150, broadcast
  `WM_SETTINGCHANGE`, `lfMessageFont` stays at −12 Segoe UI.)
- `TextScaleFactor` appears in **0 of 338 Qt DLLs**. **Qt cannot see that slider. No Qt app can.**
- The app *already* honours Display->Scale correctly — QSS px are logical px, multiplied by dpr.

**The mechanism of the error, which is the durable part.** My probe `probe_os_text_scale.py` *simulated*
the slider with `app.setFont()` and never checked that the slider does that. It carried a control, the
control **passed**, and it still measured nothing — because the control validated the PLUMBING while the
PREMISE went untested. This study already had the law *"a probe whose control fails is measuring
nothing."* Round 5 mints its complement:

> **A PASSING CONTROL LICENSES THE INSTRUMENT, NOT THE PREMISE.** Before simulating a mechanism, prove
> the mechanism exists. A control can only tell you your measurement is sound; it can never tell you
> that you are measuring the right thing.

The same error, twice more in the same probe:
- **`em` does not work.** Qt QSS `font-size` takes only px and pt; `em`/`ex`/`%` are **silently
  discarded** and fall back to the inherited size. My probe reported "qss_em TRACKS x1.50" — it was
  `inherit` under another name, and **the disproof was in my own output**: the em row read 15.94/23.94,
  *byte-identical* to the inherit row, when 1.1em should have been 10% larger at both ends. My verdict
  function only asked "did it grow", so a fallback read as a success. **Assert the DISTINGUISHING value,
  not the direction of travel.**
- **"offscreen forces Fusion while the app runs windows11" is HALF FALSE** and had been repeated across
  this study for rounds. `shell.py:129 _apply_app_theme` calls `app.setStyle("fusion")` deliberately
  ("the one built-in style that fully honours stylesheets"). **The app runs Fusion.** Offscreen's Fusion
  is *correct*; only its stubbed font DB lies. A bare probe `QApplication` left on the platform default
  is the thing rendering chrome the app never ships — **`app.setStyle("fusion")` in every shot.**

The honest accessibility position: **the app resizes fine. It lacks a text-only lever, and on Windows
the only lever that can exist is one we ship.** That is CALIBRE (user-selected, queued).

### What I also got wrong, in the same direction

I claimed the hint tier "runs at 116 chars/line". **That is the CAP's capacity, not what anything
renders at** — the same mistake `test_the_caption_measure_is_unchanged_on_purpose` makes. The 3 real
`option()` captions average **61 chars, inside the band**. But the pass found the real defect I had
walked past: **`option()` is 3 of 38 caption sites.** The other ~35 are raw `QLabel` + `setWordWrap`
with **no cap at all**, growing 1:1 with the window — **125 chars at 1280px, 257 at 1920, 388 at 2560**.
That is COLUMN, un-chosen, and it is the bigger half of "the hints are hard to read".

### Verified and durable

- **The hint tier's problem was ONLY size.** Contrast passes AA in all 8 palettes (`muted` worst 4.59
  in light; `error_text` worst 4.87 in solarized-light). And **growing text can never loosen a contrast
  requirement** — every rung except `name` is below WCAG's 24px large-text threshold, so 4.5:1 applies
  before and after. `theme.derive()` reads no font size at all.
- **The toolbar budget is now SPENT.** 13px = 15/15 at 1280. 14px naive = **14/15** (a button in Qt's
  hidden chevron — the exact bug `style.py`'s QToolBar comment guards). 14px + `tb_space` 4 = 15/15.
  **15px = 13/15 and tightening does NOT recover it.** Any future body bump must find another payer.
  → `evidence/probe_toolbar_budget.py`
- **The ramp is not a scale**: 26/16/15/13/12/11 has five different ratios, and h2->h3 is a **6.7%
  cap-height step** — a tier Segoe cannot draw. The size analogue of the PER-FAMILY CUT LIST law. QUARTO
  P2 (merge h2+h3 into one `type_head`) is un-chosen and still open.
- **8 sizes ship, not 6** — including a **10px** header at `shell.py:6630`. The declared ramp is not the
  shipped one.
- **`h3`'s docstring is a lie**: it says "a sub-h2 section title"; **zero** h3 sites nest under an h2.
- **A real bug, un-chosen (DICTION):** `forms_qt.py:265` **destroys** a field's help text on a parse
  error and only restores it when the value parses. The teaching vanishes exactly when the user is
  failing.
- **The `<` footgun**, if LEADING is ever taken: `'ids < 4003 are real'` renders as `'ids '`. Silent
  truncation, no error, in an app whose whole subject is field ids.
- **THE COMMENT-PLACEHOLDER LAW BIT A FOURTH TIME**, in this very round, while writing RUBRIC's comment
  *about* tokens. It fires precisely when you explain a token in prose. The fence caught all three.

### The instrument note

`evidence/shot_quarto.py` renders ONE state; `shot_quarto_ab` stashes and re-runs it in a fresh process.
That indirection is not ceremony: the first cut faked the "before" by patching the stylesheet, which was
**structurally impossible** for RUBRIC — its change is in *Python* (`widgets.section` picks the role and
drops the `.upper()`). No QSS patch can reproduce the old widget. **The only faithful before is the old
code, run as the old code.** The anchor guard refusing to render a dishonest shot is what surfaced it.

---

## Round 5, part 2 — QUARTO P3 + CALIBRE shipped; PUNCH FALSIFIED by its own condition

**SHIPPED:** QUARTO P3 (one `_TYPE` table, gated byte-identical on effective CSS 16/16) and **CALIBRE**
(Preferences -> Text size 100/110/125/150%, live + persisted + Cancel-reverts). 3591 tests.

**NOT shipped: PUNCH.** It was user-selected, built up to the render, and the render killed it. That is
the FORM LESSON doing its job, not a wasted round — *statistics reproduce a thing's measured properties
and never its look*, and PUNCH's axis was **measured and real**:

- The six-cut optical family IS installed and IS a genuine axis (x/px: Segoe .500 · Sitka Small .503 ·
  Text .477 · Subheading .462 · Heading .449 · Display .439 · Banner .430), each cut itself
  scale-invariant — so the axis lives ACROSS the family: you pick the cut for the size.
- **And the app already spends it correctly at the top.** The 40px wordmark wears Sitka Banner (the most
  extreme display cut); the 26px crown wears Sitka Display. "Spends only 2 of 6" was true and was never
  a defect — those are the right 2 for those sizes. The display end was already done.
- **P1 (tracking) buys nothing an eye can see.** Rendered at 1x and at 3x nearest-neighbour: the crown at
  0 / −0.25 / −0.50 measures 153.56 / 150.06 / 146.56px — a 3.5px change on a 153px word. Sitka Display
  is *already drawn tight*; tightening reveals no flaw, it just narrows. The hint at +0.15/+0.30/+0.50 is
  noise at best and stretches the app's worst-measure tier at worst.
- **P2 (a small optical cut for captions) dies on arithmetic:** Sitka Small buys **+0.5% x-height for
  +17.9% width**. A small optical cut exists to give MORE x-height at small sizes — but Segoe UI is
  already a UI face drawn for exactly that job at 0.500 vs Sitka Small's 0.503. It buys nothing it was
  chosen for. **`test_only_the_nameplate_wears_the_serif` was RIGHT and stays.**

### What PUNCH did produce (all durable, all recorded in `style._TYPE`'s comment)

- **THE RAMP IS NOT OPTICALLY LINEAR.** `_TYPE`'s numbers are NOMINAL px; the eye reads x-height and the
  faces differ. The crown's true size over the body is **1.63×**, not the 1.86× its numbers imply.
- **My brief's FACT 2 ("x-height scales exactly linearly") is corrected**: true WITHIN Segoe, false across
  the shipped ramp. Its `name 26px -> x 13.00` row was **Segoe 26 — the fallback**, not the face the
  nameplate wears.
- **A live, unlooked-for finding: QUARTO P1 quietly demoted the crown.** Optical dominance moves INVERSELY
  with the body while the crown's own number never changes — body 13 -> 14 took the nameplate from 1.76×
  to 1.63×, and nobody noticed because 26 stayed 26. Left as-is (the user approved the result live), but
  any future round that moves `type_body` is also moving the crown.
- **QSS `letter-spacing` works exactly** (±0.500px/char, to the hundredth) and is spent on 1 QSS rule
  (`overline`) plus `hero._WORD_TRACK = 0.5` in QPainter, which the sheet cannot see.

### THE INSTRUMENT LESSONS OF THIS ROUND (three, and they rhyme)

All three are the same error as [the simulated-mechanism law](#) one layer down — **asserting a condition
without checking it took**:

1. **`resize(1280)` is a REQUEST.** On a 1920 screen the window ignored it, so `probe_toolbar_budget`
   printed "@1280" while measuring 1920. Now: `setFixedWidth` + **assert `win.width() == width`**.
2. **A baseline that reads the current code is not a baseline.** That probe's `"body 14, naive"` case
   passed `tb_space=None`, inheriting whatever SHIPS — so once QUARTO P1 shipped `tb_space` 4, "naive"
   silently meant *"with the fix already applied"*, and the probe appeared to **refute the claim it
   existed to prove**. Pin every condition explicitly.
3. Those two **cancelled into a confident, self-consistent, wrong table** that nearly made me revert a
   correct change. Re-measured at a real asserted 1280, QUARTO P1's receipt stands exactly as committed:
   body 14 + `tb_space` 6 = 14/15, `tb_space` 4 buys it back to 15/15, body 15 recovers at neither.

Also corrected, repo-wide: **"offscreen forces Fusion while the app runs windows11" is HALF FALSE.**
`shell.py:129` calls `setStyle("fusion")` deliberately — **the app runs Fusion**. Offscreen's Fusion is
CORRECT; only its stubbed font DB lies. Every shot/probe now calls `app.setStyle("fusion")`, because a
bare probe QApplication on the platform default is the thing rendering chrome the app never ships.

### CALIBRE's measured price, not hidden

The toolbar chevrons at 1280: **15/15 at 100% · 14/15 at 110% · 13/15 at 125% · 11/15 at 150%**; 15/15 at
1600+. Chevroned items stay reachable (and Ctrl-K reaches everything), and the a11y suite already fences
graceful overflow. Recorded in `prefs.TEXT_SCALES`. **The hero band does not scale** — QPainter at hard px,
no stylesheet reaches it. That is PLINTH, unbuilt, and at 150% the front door stays put while the app
grows around it.

**Live-confirmed this round:** the user has now seen QUARTO P1 + RUBRIC in the running app — *"fonts look
much better"*. That is the first live judgement since Mist. CALIBRE + P3 are **not** yet playtested.

---

## Round 5, part 3 — PLINTH: the front door measures itself

**SHIPPED.** The band tracks the text-size dial, and its two private faces joined the ramp. 3596 tests.

- **The wiring already existed and was inert.** `shell._apply_text_scale` was ALREADY calling
  `self._hero.set_density(...)` on every scale change — and `set_density` read only `_METRICS[density]`,
  so the scale was dropped on the floor. The call site even carried a comment saying PLINTH was unbuilt
  and "the dial deliberately does not touch it". One argument closed it.
- **The 100% tuples are the DESIGN, not a derivation.** `band_metrics(d, 100)` returns the shipped tuple
  **identically** (asserted `==`, not "within a pixel"). 106.5 and 94.5 are half-pixel rule positions
  chosen by eye against a 40px serif; re-deriving them from `QFontMetricsF` would swap a composition for
  an average — and the regression would be indistinguishable from an improvement, since both arrive as
  "the numbers changed slightly". So this SCALES the design. Every other scale is that same composition,
  larger: band 156 → 172 → 195 → 234, wordmark 40 → 44 → 50 → 60, verified through the real dial.
- **The ramp-join** (the other half): the band kept private 11px/13px faces, so after QUARTO P1 raised the
  caption floor to 12, **the hero was the only surface in the app still shipping 11px text** — the front
  door wearing exactly the small type the user asked us to fix everywhere else. Now `type_caption` /
  `type_body`. Rendered as an isolated delta with the geometry frozen (`plinth_ramp_*.png`) and it reads
  as **almost nothing**, which is the correct outcome. The WORDMARK deliberately does not join: 40px
  Sitka Banner is a brand constant, type chosen as a drawing rather than as a tier. It scales; it never
  tiers, and a fence asserts it is not equal to any rung.
- **THE INVARIANT THAT WAS TRUE BY TASTE.** `signet_elbow`'s docstring promised the mark "can never
  overflow the column". "Bound to `adv`" binds the arm to the **wordmark**; nothing bound the wordmark to
  the **column**. At 100% it never mattered (~300px against a 604–860px column) — but PLINTH grows the arm
  with the dial while the column does not, so a scaled band in a narrow window would run the mark out of
  its own composition. Now `min(adv, col)`: structural, not lucky. **An invariant a new feature can
  falsify was never an invariant** — and this one had shipped, documented, for three rounds.
- **Fenced at the source, not per-number:** `test_the_hero_holds_no_private_type_sizes` walks the AST and
  refuses any `setPixelSize(<literal>)` in the module. Reads code, not prose — this module's comments are
  full of "11px" and would pass a naive grep vacuously. The ramp fences assert the RELATIONSHIP (`==
  type_px("type_caption")`), never the values 12/14, because pinning values passes happily while the ramp
  moves away underneath them, which is the exact bug being closed.
- The overflow fence carries a **self-invalidation guard**: it asserts the wordmark at max scale really
  does outrun the narrowest column, so it fails loudly if it ever stops testing anything rather than
  passing vacuously.

**Still open:** GAUGE — `PROSE_W` is a fixed 420px, so the measure decays as the type grows.
(⚠ The numbers first written here — "61.9ch at 100%, 41.3 at 150%, below the 45 floor" — are WRONG, from a
synthetic rate. Measured on the app's real prose it is 67.6–71.9ch at 100% and **45.0 at 150%: ON the
floor, not below it.** See part 4 below; the defect is real but it is not this.)

---

## Round 5, part 4 — GAUGE. And the measure was never the defect.

**SHIPPED**, but for a reason nobody predicted — and the numbers going in were wrong three times.

### The measure's real history (native, `evidence/probe_measure_rate.py`)

| claim | source | verdict |
|---|---|---|
| 61.9 ch | my alphabet probe | **wrong** — synthetic rate, ~9% off |
| 77.5 ch | round 5's audit | **was true**, at the 13px body |
| 41.3 ch @150%, "below the floor" | me, told to the user | **wrong** — it is 45.0, ON the floor |
| **67.6–71.9 ch** | the app's real strings @ 14px | measured |

**My instrument lied and I published it.** `'abcdefghijklmnopqrstuvwxyz '` has ONE space in 27; English has
~1 in 6, and the space is the narrowest glyph in the face. A synthetic rate overstates px/char, which
understates the measure. **A rate measured on the alphabet is a measurement of the alphabet, not of prose.**

**And QUARTO P1 fixed the real defect by accident.** At 13px the Build & Deploy crown note ran 77.5ch —
over the band. At 14px it runs 71.9 — inside it. **Raising the body NARROWS the measure in characters**,
because every character got wider. The type bump the user asked for closed the case GAUGE was chartered for.

### So GAUGE shipped for the reason that survived: nothing could TELL

The measure held at every dial setting **by luck** (45.0ch at 150%, zero headroom), and the fence could not
have noticed if it stopped: it divided `PROSE_W` by `WORST_13PX = 5.72` — **a constant over a constant, a
rate from a font size the app no longer sets.** It passed at 150% exactly as happily as at 100%, and would
have kept passing with the cap welded to 420 forever.

### The mechanism: scale, don't re-derive (PLINTH's move again)

Segoe's advance is **LINEAR in px** (12→28px, max error 0.065%), so `chars = (cap·k)/(rate·k) = cap/rate`
— **the character count is INVARIANT under scaling.** Proven end-to-end on the real string through the real
dial: **71.9ch at 100 / 110 / 125 / 150%**, flat; `cap/px` exactly 30.00 at every rung.

Re-deriving from a "characters" target would need a calibrated rate, and every honest candidate misses 420:
`averageCharWidth()` reads 5.953 at 13px, **above every real string in the app** (5.42–5.89), because it
averages a glyph set nobody types. **Scaling needs no rate at all.**

`Prose` reads its OWN polished font (`changeEvent` → `FontChange`) rather than being told the scale — so it
is right no matter who changed the type. A cap threaded from the shell would be a second source of truth
for the same fact, and the two would drift the first time one was missed.

### THE OFFSCREEN LIE, THIRD INSTANCE — and this one wrote a PASSING FENCE FOR A BROKEN FEATURE

**`QFontInfo(...).pixelSize()` returns `-1` under `QT_QPA_PLATFORM=offscreen`**, even for a font with an
explicit `setPixelSize(21)` — offscreen stubs the font engine QFontInfo consults. A QFontInfo-only
`_resolve_cap` hit its `k=1.0` guard in *every* test, held the cap at 420 forever, and **the fence written
to catch exactly that failure reported it as a pass.** Fixed by asking `QFont.pixelSize()` first (explicit,
survives the stub) and falling back to `QFontInfo` (resolves a point-size font — the Windows system font is
Segoe 9pt and reports `-1`, which would multiply every cap by a negative). Neither source alone suffices.

The standing warning "offscreen lies about the font DB" was already here. What is new: **it lies to your
fences, in the direction of green.**

### Corrected en route

`test_the_caption_measure_is_unchanged_on_purpose` laundered an approval (620 was approved for PROSE at
13px, then inherited onto the 11px caption where the same number is strictly worse) *and* cited evidence
describing 1 of its 3 strings. Rewritten to say what is true — and to name the real caption defect:
`option()` is 3 of ~38 sites; **the other ~35 are raw QLabels with NO cap, growing 1:1 with the window**
(125ch at 1280 → 388 at 2560). That is COLUMN, unbuilt, and now the largest un-taken readability win here.

**The user cleared ALL standing playtest debt before this landed** (CALIBRE, QUARTO P3, the badge bump, the
spine cut, PLINTH — all validated live). GAUGE was unplaytested as of writing, and is invisible at 100% by
construction.

---

## Round 5, part 5 — COLUMN: the hint tier stops growing with the monitor

**SHIPPED.** 35 hand-rolled caption labels routed through `widgets.caption()` (now a capped, scaling
`Prose`); `CAPTION_W` 620 → **380**. 3602 tests.

**Before → after**, measured live on the real labels at real window widths:

| window | before | after |
|---|---|---|
| 1280 | 103.6 ch/line | **74.1** |
| 1920 | 198.5 | **74.1** |
| 2560 | 313.7 | **74.1** |

0/4 over the ceiling at every width (was 4/4), 4/4 capped (was 0/4). **Flat** — the measure no longer
tracks the screen.

- **620 was never a measure.** At the real 12px rung, on all 23 real caption strings (rate band
  5.113–5.661; the ceiling is set by the NARROWEST rate — fewest px/char = most characters per line), 620
  renders **121 ch, 62% over, even where it binds**. 380 = 74.3ch is the widest cap that holds every real
  caption. It survived three rounds on two defences, **both built from a sample of one**: an approval
  granted to PROSE_W at 13px, and "the cap does not bind" — which was the indictment, not the defence.
- **Its fence went red and made the change deliberate — which is precisely why it existed** ("so that
  lowering it is a decision somebody makes on purpose"). Kept and inverted rather than deleted.
- **The factory already existed with the right name.** `widgets.caption()` just returned a bare
  `role_label`, and 37 sites had quietly stopped calling it. A fence checking only "everyone calls the
  factory" would pass perfectly against that, so a second one asserts the factory actually caps.

### The sweep found a live NameError that py_compile could not

`savedoc.py` imports `from .widgets import PlaceholderListWidget, section` — **no bare `widgets` name** —
so its two converted sites would have raised on the Save tab. `py_compile` passes on an undefined global;
only importing the module and asking `hasattr` finds it. Same class as this arc's earlier
"caught by a PROBE, not by 3569 passing tests". **The import check is now part of the conversion.**

### ⚠ STANDING QUESTION FOR THE EYE — the form docs have no page column

Fixing the measure exposed the real structural gap: **Home caps its content at 860 and centres it; the
form docs do not.** Import's cards measure **640 / 1102 / 1136** at a 1920 window, so a correct 380px hint
now sits in an 1100px card at 3:1 — readable per line, but a narrow ribbon in a wide pane, which is the
exact failure the shot's own docstring predicted.

**✅ RESOLVED — the page column shipped** (see part 6). The fix was the page, not the hint: 480 reads
94ch and would be back over the band. Renders: `col_before_import.png` → `col_after_import.png` →
`col_pagecol_import.png`.

*(Note: the user's real prefs sit at `text_scale = 110` — they use CALIBRE. Every probe here PINS the
scale to 100; a probe that inherits the user's dial reports the wrong rung and I did that once already,
measuring "12px" captions that were really 13.)*

---

## Round 5, part 6 — the page column

**SHIPPED.** `widgets.page_column()`; the three form docs (build / import / co-op) now build into Home's
centred 860 reading column instead of a bare layout. 3603 tests.

| window | import (before → after) |
|---|---|
| 1920 | `[640, 1102, 1136]` → **`[640, 778, 812]`** |
| 2560 | stretched → **`[640, 778, 812]`** (stops growing) |

812 = 860 − the 24px page margins each side, so cards land exactly on Home's column; 604 at 1280 and 860
from 1600 is Home's own documented curve, because it is Home's own geometry.

- **The instinct was wrong and the arithmetic said so.** A 380px hint in an 1102px card reads at 3:1 and
  looks like a ribbon — but widening the hint to 480 puts it at **94ch, back over the ceiling**. *The hint
  was never too narrow; the page was too wide.* The app already had the answer and spent it on one screen.
- **860, the same number**, because a page that is 860 here and 900 there does not have a column — it has
  two opinions.
- **Stretch 20, not 4 — a copied SOLUTION, not a copied number.** Home's comment is the receipt: 4:1:1
  targets 435px at 1280 and is rescued only by a 512px minimumSizeHint propped up by un-word-wrapped
  labels. **That trap is now LIVE for these docs and was not before** — COLUMN just wrapped every hint on
  them.

### I checked that I did not cause the horizontal scrollbar

Some docs show one at 1024/1280. Stashing the change and re-measuring gives a **byte-identical** pattern
before and after (`1024/import=H 1024/build=H 1024/coop=H 1280/import=H 1280/build=- 1280/coop=H
1600/all=-`). **Pre-existing:** Co-op has a card with a **797px minimum** that refuses to compress. Left
alone and recorded — a change that merely coincides with a bug is not its cause. Worth a round of its own.

---

## Round 5, part 7 — DICTION: an error stops eating the help that explains it

**SHIPPED.** The `notice` tier + the forms_qt bug fix. 3605 tests.

### The bug, proven live

```
valid   (4000) -> 'a unique number for your field (use >= 4000)'
INVALID (abc)  -> '⚠  expected a whole number, got 'abc''      <- the help is GONE
```

`validate()` did `h.setText(f"⚠ {e}")` on the HINT and restored `f.help` only once the value parsed. One
label, two jobs — so **the sentence telling you what a valid value looks like vanished at exactly the
moment you were failing to type one.** Now the hint is the constant and the notice is the variable.

### The law and its violation were adjacent lines

`style.py` has said since Phase 2: *"Never demote a diagnostic to 11px grey — demote the EXPLANATION,
never the answer."* The **very next rule** was `QLabel[role="caption"][state="error"]`. **A law written in
a comment above the code that breaks it is not a law** — it is a wish with good phrasing. The law lost for
three rounds and a green test held the defect in place as the contract.

### The split: is it READ, or is it GLANCED?

| tier | posture | set as |
|---|---|---|
| `caption` | **read** — prose attached to a control | caption rung, muted, measured (COLUMN) |
| `notice` | **glanced** — anything that REPORTS | **body rung**, state-coloured, never smaller than its field |
| `chip` / `overline` | a **tag** — a label is not prose | caption rung |

One tier had been doing all three, which is why it got **both axes backwards**: the longest text got the
smallest face, and a warning was filed at 11px grey because "small = quiet" was the only tool in the box.

### The ninth-ground law, applied BEFORE the ground exists

A notice gets **no chip, no badge, no fill** — and a fence refuses any `background` in the rule. Measured
across all 8: error/warn on `surface_2` (where forms live) pass **4.54–10.22**; on `surface_3` they are
**sub-AA in 6 of 8** (error 3.84–4.23). Zero pixels today only because nothing grounds state text there —
give a notice a chip and it lights up in six palettes at once. **The tier declines the ground.** "We
decided not to" is exactly the kind of decision a later round re-makes by accident.

**Unplaytested**, with COLUMN and the page column.

---

## Round 5, part 8 — QUARTO P2: the ramp has no dead rungs

**SHIPPED.** h2+h3 merged into `role="head"` (18px); the strays swept; a step fence. 3608 tests.

| | ramp | cap ratios |
|---|---|---|
| before | 26 / 16 / 15 / 14 / 12 | .615 / **.937** / **.933** / .856 — **two dead steps** |
| after | 26 / 18 / 14 / 12 | .692 / .778 / .856 — zero |

The head over the body went from a **7.1% cap step (h3) to 28.5%**.

- **The distinction h3 claimed was fiction.** Its docstring said "a sub-h2 section title"; all four sites
  are top-level titles of independent containers (a QDialog, the models pane, the Inspector, the lede).
  **Zero sit under an h2.** The role described a hierarchy that has never existed.
- **Merged, not aliased** — an alias keeps two names for one thing and invites the split to grow back.
- **The strays were invisible because neither is QSS**: a 15px step glyph set by an inline widget
  stylesheet, and the Inspector's section headers at **10px in inline HTML** — the smallest text in the
  app, two under the OS default, and a full rung under `role="overline"`, which is the same thing it is.
  No role reaches HTML. Both now substitute a rung at the live scale (an inline size can't hear CALIBRE).

### P2 struck a gold line through the lede's own title, and only the render caught it

`LedeCard` pinned its rule at `_UP = 26` → y=36.5, chosen by eye against a 15px title whose box bottomed
at **33.9**: a 2.6px clearance nobody had written down. An 18px title bottoms at **37.9**, so the rule
crossed the words — and **a 1.4px overlap reads as an underline, not as a bug**. No test measures a
QPainter stroke against a sibling QLabel's font, so no test could fail.

**The fix is not a new constant — a constant is what broke.** The rise now derives from the rung the title
wears, so it tracks the ramp and the dial. Clear at 100/110/125/150%, fenced, including a fence that
refuses a re-pinned `_UP`. **This is the third time this round a PAINTED surface went stale against a
token change** (the hero's band, the hero's arm-vs-column invariant, now the lede's rule). QPainter code
is where the ramp's blind spot lives.

### And my own fence caught itself first

Walking every `ast.Constant` flags **docstrings** — so it reported `Prose._resolve_cap`'s prose *about*
`font-size: 21px` as a violation. *A fence must read code, not prose — and a docstring is prose that
happens to be stored as a string.* Second instance this session.

**Deferred, named rather than silent:** forms_qt's rich-text document bodies (Info Hub catalog, concept
card) ship 13/14/15px HTML — the Info Hub renders at the OLD body size and cannot hear the dial. Exempted
by name in the fence; it wants its own decision, since forms_qt has no access to the scale.

---

## Round 5, part 9 — HEED: read the slider Qt refuses to read

**SHIPPED.** `prefs.os_text_scale()` seeds CALIBRE's default from Windows. 3616 tests.

Qt cannot see the Accessibility → Text size slider — settled, not fixable (it writes `TextScaleFactor`,
never touches `lfMessageFont`, and appears in **zero of Qt's 338 DLLs**). But it is a registry value, and
**Python can read it.** Proven end to end on a faked 150% machine: first launch opens at 150% (body 21px,
band 234px — PLINTH carries it), and an explicit 100% then beats it.

- **An explicit choice always wins — that ordering IS the feature.** A saved value means the user went to
  Preferences and said what they want; the OS never overrides it. Only an *absence* takes the seed. Fenced
  first, including the case that looks like nothing: **choosing 100% is a choice, not an absence.**
- **A corrupt value degrades to the SEED, not to a bare 100** — a hand-edited file must not silently cost
  a low-vision user their text size.
- **Not a new pattern**, which is most of why it's defensible: `theme.detect_os_dark` has shipped this
  exact shape for rounds (HKCU read, bare except → safe default, fenced by monkeypatching the *function*).
- **Nearest, clamped by our own top.** MS documents [100, 225]; we ship (100,110,125,150). Common stops
  land exactly; 175/200/225 → 150. Nearest rather than snap-down because **under-serving someone who asked
  for bigger text is the wrong direction to err.** Junk (10000, 0, −5) is clamped, never obeyed — a
  registry value is user-writable.
- **The alibi shipped, not cut**: Preferences labels the OS's rung *"— following Windows text size"*. An
  app that quietly scales when nothing else on the desktop does reads as **broken**, not considerate.
- **Fenced against poisoning the suite** — the risk the audit named by name. Every px fence asserts a
  rendered number, so if `qss()` ever reached for `prefs.text_scale()` that file would become a report on
  whoever ran it. A fence reads style.py's AST for any reach at `prefs`.

On this machine the key is **absent entirely** (the slider has never moved — the common case), so the
feature is inert.

### An investigation worth recording: I thought I'd clobbered the user's prefs

`prefs.text_scale()` read **110** early in the round and **100** later, and the file's mtime was minutes
old. Rather than assume, I tested it in an isolated store: `_apply_text_scale()` does **not** persist (a
live preview stays a preview) and `close()` → `_save_layout()` → `set_layout()` → `put()` is a
read-modify-write that **preserves `text_scale` intact**. The app is innocent; the user changed it while
validating. Also confirmed `tests/conftest.py` has an autouse fixture isolating prefs for **every** test,
so the suite never touches the real store. **No damage — but the check was right to run: probes that
construct a real `Workspace` and call `close()` are one careless `set_*` away from editing the developer's
own settings.**

---

## Round 5, part 10 — KEYLINE: the dot, and a tier that had never been drawn

**SHIPPED.** 3620 tests. Round 4 spun these out as standalone bug fixes; both were real, and neither was
what its analysis said.

### The dot ate the glyph it annotated

`r = w * 0.30` + an `int()`-truncated halo spanned **11.6px of a 16px icon — 72% of its width** — punched
out of the bottom-right corner, on the row you are editing. `field` became an amber blob with a fragment
of a frame; `hub` lost two of four squares; `chocobo`'s feather was bisected. Now `k=0.19 / pad=1.0 /
QRectF`: **6.1px dot, 50% of width**, every glyph identifiable.

The `int()` was the bug's other half — it truncates origin *and* extent, and at k=0.19 the 1px pad **is**
the whole margin, so the radius fix alone would not survive it.

**ONLY THE RENDER COULD SEE IT.** The punch-out CLEARS and the dot then FILLS, so every destroyed pixel
returns at **alpha 255**. My "is this pixel still ink?" probe counted the amber dot as surviving glyph and
reported **98.4% kept** — I nearly dismissed round 4's claim as false on the strength of it. *Ask what
COLOUR survived, or look at it at 10×.*

### THE LEAF TIER HAS NEVER BEEN DRAWN — the round's best find

`_type_icon` read `self.pal.get("text_subtle", self.pal["text"])`. **`text_subtle` is DERIVED; `self.pal`
is RAW** (`main()` does `Workspace(pick_palette(...))`). The fallback fired **every time, in every palette,
since the icons shipped** — every leaf icon has been full `text` ink, and the "subtle body text" its own
docstring described has never reached a pixel.

> **A defensive `.get` whose default is the real behaviour is not a default — it is the code.**

That retires the analysis that sent us here: round 4's "text_subtle is 2.96 in solarized-light — FAILS"
was **measuring a colour the app does not draw**. `muted` is right anyway: the intent finally delivered
*and* legible (5.08–6.99; text_subtle would have failed 6/8 selected).

### My own fence found a defect nobody had looked for

**nord's SPINE icons are 2.47 on the tree ground** — under the 3.0 floor. Fixed with `focus`, which *is*
"the accent brightened until it clears 3:1 on the surface": only nord moves (2.47 → 3.08); the other seven
return unchanged. **Not** a new `accent_mark` token — it would be `_focus_token(accent, surface)`,
identical by construction, i.e. the two-names-one-job defect QUARTO P2 deleted two commits earlier.

### And round 4's headline is no longer true

It measured accent-on-accent at **1.00–1.01 in all 8** (byte-identically zero differing pixels in two
palettes) when the selection was a solid accent FILL. **REGISTER P1's tint has since fixed six for free** —
accent now reads 1.57–4.64, failing only nord + solarized-dark. The explicit `QIcon.Mode.Selected` pixmap
ships anyway: an app must not depend on `QCommonStyle::generatedIconPixmap`'s guess ("tint 30% toward
Highlight") to keep its icons visible.

**A KeyError caught by the suite, and it was mine:** `self.pal["focus"]` on a raw palette — precisely what
the old defensive `.get` was hiding. Added `_derived(key)`: derive on demand, cached per palette object.

**Fenced as tests, not as an audit entry, and that is structural:** `audit_contrast` reads ink via
`w.palette().color(w.foregroundRole())` — a QLabel API. It is **blind to a QPixmap**. An icon tier can fail
in every palette and no audit will ever say so. The fences check **(tint, ground, STATE)**.

---

## Round 5, part 11 — the Co-op card, and the third law gets a fence

**SHIPPED.** Play-style card **797 → 522**. 3621 tests.

`widgets.option`'s docstring has said it since Phase 4: **"THE THIRD LAW: never put prose inside a
widget."** Co-op shipped a QCheckBox whose label was a **130-character sentence** — and a QCheckBox does
not word-wrap, so its `minimumSizeHint` IS the whole string (763px). **That one control put a 797px floor
under its card and held the whole page open.**

> **A law in a docstring is a wish.** (Third instance this round — after `style.py`'s "never demote a
> diagnostic", which sat directly above the rule that broke it.)

The other two rows were the same defect in different clothes: a **411px hint inline beside a button** (a
bare QLabel in an HBox can neither wrap nor compress), and `setMaximumWidth(340)` on the ghost combo which
capped how wide it *may* get and **left its minimum alone** — a QComboBox's minimum is its longest item.

### 80 is a gap in the data, not a taste call

The census: **130 / 107 / 101**, then **71 / 70 / 70 / 67 / 66 / 63 / 60×3 / 58 / 57×2 / 53×2 / 49**. A
**30-character hole** separates a *sentence that happens to be in a widget* from the ordinary "Native —
seamless + faithful" idiom, which reads fine and compresses acceptably. Fencing in the gap catches the
defect without re-litigating 15 labels that were never the problem. The two sentences it caught (builddoc's
101 and 107) are split here.

### What this does NOT fix — and it is not the card's fault

Co-op still scrollbars at 1280: it needs 570 (522 + 48 page margins) against a **544** pane. The pane is
544 because the central splitter allocates **[300 tree, 558 doc, 420 inspector]** of a 1280 window — the
side panels take **56%** and the document gets **44%**.

**IMPORT NEEDS 603 AND HAS NO OVERSIZED CARD AT ALL**, which is the tell: this is an *allocation* question,
not a card defect. At 1600+ every doc is clear. Left alone deliberately — those splitter sizes are
persisted, so they are partly the user's own, and re-balancing the default wants its own eye.

---

## Round 5, part 12 — the Info Hub joins the ramp. No file is exempt.

**SHIPPED.** 3622 tests. The last surface with a private ramp, and the last one deaf to the dial.

| surface | 100% | 110% | 125% | 150% |
|---|---|---|---|---|
| app body | 14 | 15 | 18 | 21 |
| **hub body** | 14 | 15 | 18 | 21 | ← was **13 at every scale** |
| **hub head** | 18 | 20 | 23 | 27 | ← was **15 at every scale**, a rung UNDER the app's head |
| hero band | 156 | 172 | 195 | 234 |

The Info Hub is HTML in a QTextEdit — **no QSS role reaches inside a text document** — so it hard-typed
its own ramp: a 13px body (stale since QUARTO P1) with headings *below* the app's head. Two ramps in one
app, and the smaller one was the only place a newcomer reads at length.

**A global**, because this module already made that exact call for this exact reason: `_GUIDED` sits twenty
lines up — *"not threaded through the many call sites; the shell sets it at startup + on toggle."*

**The fence's exemption is RETIRED, not re-scoped.** `DOC_BODIES = {"forms_qt.py"}` shipped last round with
a paragraph explaining why it was a real limit. It isn't one any more.

### A NameError that 3621 green tests did not see

`_apply_text_scale` reached for `_fq` — a **local** in `__init__`. Compiles clean, imports clean, every test
passes, and **the first turn of the dial raises.** My probe caught it; the suite could not, because
**nothing drove the live dial.** Every CALIBRE fence asserts `qss(pal, density, scale)` — a *pure function*
— and the shell's job is the other half: telling the three surfaces a stylesheet cannot reach (the QSS, the
QPainter band, the rich text). That gap is now a test, **and I proved it catches the bug rather than passing
beside it**: re-broke the line, watched it go red with the same NameError, restored, watched it pass.

### Two more of my own, from this same commit

- **The catalog card is built from PLAIN strings**, so my first substitution would have rendered a literal
  `{_px("type_head")}px` into the HTML — compiles, tests green, Info Hub shows raw braces. Caught by
  asserting the *rendered output carries a number*, not by reading the diff.
- **COLUMN's caption fence keyed its exemption on LINE NUMBERS** and went red when an unrelated edit shifted
  the file. *A fence that breaks when nothing it guards has changed trains people to re-number it without
  reading it.* Keyed on the variable now.


---

# ROUND 6 — the call sites, and the oldest open question

> **Status: ✅ MERGED + PLAYTESTED 2026-07-16** — *"playtested, all good"*. 4 fixes + 1 verdict, then an
> adversarial review and everything it forced. **3655 tests**, smoke green.
>
> **What the verdict covers:** SPEND · PRESS · THE DOC PANE · BREATHE · THE LAMP (flat) · the smoke ·
> round 6b's review fixes · the focus chain (0 dead tab stops) · `pressed_fg` · the narrowed accent ladder.
>
> **What it does NOT retire — the same carve-out round 5 made, and this round needs it more.** The
> INSTRUMENT was wrong about ten times here, and playtesting confirms the RESULT, not the measurements: a
> probe that manufactured a 1296px window floor out of a stubbed font DB, two fences that passed with their
> own defect fully reverted, a "tab stop" census that counted a viewport, a walk that asserted itself
> sub-AA, an input range the product does not have, a toggle applied to an unknown state, and a window that
> was never active. **None of those became trustworthy because the app looks right.** They became *invisible*
> — which is worse. The laws are in the round-6 and 6b sections; read them before writing the next probe.

## The finding, measured four independent ways

The round opened with four surveys against the axes this arc had never examined — spacing, colour,
interaction states, the splitter. They came back with **one finding**:

> **A CORRECT MECHANISM EXISTS, AND THE CALL SITE DOES NOT SPEND IT.**

| survey | the mechanism | what shipped |
|---|---|---|
| colour | `accent_fg`, authored per palette, fenced at 4.5 | the chip hardcoded `#ffffff` — **1.12:1**, every tab |
| colour | `error_text`, derived + fenced | **8 sites** write the raw hue, down to 2.67:1 |
| states | the generic `:pressed` rule | **6 of 7** id-scoped buttons shadow it — dead on click |
| spacing | the 4px grid | **1 use** in a 542-line sheet; `space()` 3 call sites vs 148 literals |

**That is round 2's original diagnosis, still true three rounds later.** VISION.md §1: every ranking
mechanism was *"built, tokenized, tested, and then never spent"*. This arc made **type** a system and spent
it end to end; colour, spacing and states were measured, tokenized, fenced — and left in the box. Not
drift. The same disease, with four independent measurements.

## What shipped

- **SPEND** `c31cd6f` — the chip spends `accent_fg`/`warn_fg`: dracula's BATTLE chip **1.12 → 14.13**,
  verified by driving the real widget and counting pixels (16/16, zero sub-AA). `accent_fg` is **authored,
  not derived**, and a probe proved why: a single rule reproduces only **5 of 8** authored values, and where
  it misses it picks *more* contrast than the author chose (dracula's `#282a36`, gruvbox's `#282828` — those
  projects' signature backgrounds). **Authored where someone chose, derived where nobody did.** The census
  also found a site the survey missed: the "?" button wore `accent_fg` on a `help` fill — **2.51 on nord**,
  two hexes nothing had ever asserted were compatible.
- **PRESS** `c881380` — 6 dead buttons react; `#consoleToggle` gets the focus ring it never had (WCAG
  2.4.7); `#disclosureToggle`'s focus stops being byte-identical to its hover. The ring costs **zero
  layout** (both boxes byte-identical, measured).
- **THE DOC PANE** `bbab828` — a floor for the document, `setWordWrap` for the recent row (Home needed
  **903** and scrolled at 1280 *and* 1440, because its width depended on the user's own folder name).
- **BREATHE** `69f3755` — space joins the dial (card air at 150%: **96 → 114**), and the toolbar pays
  **zero items**.
- **THE LAMP** — ✅ **the verdict: flat.** The oldest open question in the study is now a decision. See
  PLAN.md Open Question #2.

## THE INSTRUMENT WAS WRONG SIX TIMES, AND IT WAS ALWAYS THE THING UNDER TEST

Every one was caught by a tell, not by luck. **The tells are the transferable part.**

1. **THE OFFSCREEN LIE, 4th INSTANCE — and the first to MANUFACTURE a defect rather than hide one.**
   Offscreen's stub font DB renders ~14px/char, so an 81-char label reports 1134px instead of ~440. Because
   `QStackedWidget`'s minimum is the max over ALL pages, it "proved" that two ordinary teaching sentences —
   on tabs you may never open — pinned the whole app at a 1296px floor and crushed the tree to 74px.
   Mechanical, reproducible, **confirmed against clean master** — and entirely false. Native: 542 and 1280.
   It also **inverted the fix**: at the fake 1156 minimum `setMinimumWidth(700)` *lowers* the floor; at the
   real 542 it raises it. The same line, opposite meanings, decided by the harness. I was one step from
   "fixing" two innocent labels.
   → **Colour is font-independent and safe offscreen. WIDTH IS NOT. If a number came from text, go native.**
2. **A FENCE THAT IS WRONG IN THE SAFE DIRECTION IS THE ONE THAT SHIPS.** PRESS's first fences took the bare
   `app` fixture — but `_apply_app_theme` sets only Fusion + the QPalette; **the QSS is a *widget*
   stylesheet** on the Workspace, reaching controls by inheritance. So they measured *Fusion's own chrome*.
   All 7 press fences went **green while testing nothing**; they would have passed with the bug fully
   present. Only the focus half failed, loudly, which is the sole reason it surfaced.
3. **A BASELINE YOU DID NOT PUT INTO A KNOWN STATE IS NOT A BASELINE.** Qt focuses the first widget in the
   tab chain on `show()`, so the state probe's first entity grabbed a "rest" image already wearing its focus
   ring and reported the generic QToolButton as having none. **A probe built to find dead states, reporting
   its own reflection.**
4. **A PROBE THAT INVENTS ITS OWN INPUT RANGE IS MEASURING A PRODUCT THAT DOES NOT EXIST.** BREATHE's
   toolbar count ran 100..200 and came back **non-monotonic** — 15/14/13/11, then 15/15 again at 200%. The
   tell was right: `_apply_text_scale` is `pct if pct in prefs.TEXT_SCALES else 100`, so 200 silently fell
   back to 100 and that row measured the baseline while claiming the extreme.
5. **A WALK TOWARD AN EXTREME IS MONOTONIC ONLY IF YOU START ON THAT EXTREME'S SIDE OF THE GROUND.** The
   first `_fg_token` copied `_text_token` and **asserted itself sub-AA**: in at 3.56, out at 3.42, having
   **dipped to 1.02** — a cream ink walked toward black must cross a gold fill, so the walk is a valley, not
   a ramp. `_text_token`/`_focus_token` are safe from this **by accident of their inputs, not by
   construction** (they pick direction from the MODE and every ground they touch is on the mode's side).
   Nothing in the file said so, because nothing had needed it to.
6. **THE EYE FAILED AND THE PIXELS DID NOT — AGAIN.** In the LAMP render I read the lede's words as
   accent-coloured and nearly reported accent-as-prose. Sampled: **0 accent pixels**. The "cyan" was
   ClearType **subpixel fringing** (`#0f4288` a blue, `#e9a96a` an orange — colours no palette contains),
   the exact artifact `audit_contrast.py`'s header already warns about.

## THE COMMENT-PLACEHOLDER LAW took instances 5, 6 AND 7 — all from inside its own explanation

`string.Template` has no concept of a CSS comment, so a dollar-prefixed token named in *prose* still
substitutes. This round:

- **#5** — wrote `color: [dollar]text` in a comment *documenting* the focus==hover defect.
  `test_no_placeholder_hides_in_a_qss_comment` went red: **the law's own fence catching a comment about the
  law.**
- **#6** — the fix for #5 explained the rule using a literal `[dollar]name` as the example. Template
  substituted it: **KeyError 'name', 68 tests down, all 8 palettes dead.**
- **#7** — BREATHE's toolbar comment named `[dollar]btn_pad` as the culprit. Red again.

**There is no way to write the token in prose. Say "dollar-prefixed" and move on.** The fence's docstring
already said *"a comment cannot hold this law"* — this round is three more proofs, and the fence earned its
keep three times in one afternoon.

## Corrections to my own prior claims

- **The splitter default is CLEAN.** My Co-op commit said it allocated the doc 44% and that re-balancing
  "wants its own eye". Measured natively: `[300, 640, 240]` → `[300, 738, 240]` at 1280, **every tab clear**.
  The defect is entirely the **persisted** layout replayed narrow — every scrollbar threshold is exactly
  `fresh+180`, and `180 = 420−240`, the inspector's saved excess. I measured the symptom and named the wrong
  cause.
- **"Clear at 1600+" was conservative** — everything is clear from **1440**.
- **PLAN.md's stripe number is stale**: "2.44–4.73 in all 7" predates SIGNET's palette retune and MIST. It is
  **2.118–7.095** now.
- **A default that can never fire is the `.get` law's other face.** `PlaceholderListWidget(color="#808080")`
  never fired (all 3 call sites pass `pal["muted"]`) — dead, and loaded: a 4th call site picks up a
  palette-blind grey, in a QPainter widget no QSS rule and no other fence can reach.

## Deleted en route (worth more than what shipped)

- **`_snip(display, 40)`** on the recent row. Took Home **903 → 840**: still over the 724 viewport, still
  scrolling at 1280, and it "fixed" 1440 only by luck. Tuning it to fit would be curve-fitting a constant to
  one font at one scale — the text dial re-breaks it at 125%. And once `setWordWrap` is in, **the cap changes
  nothing**: same 525, same row heights to the pixel. **A constant that buys nothing is worse than no
  constant, because the next reader assumes it is load-bearing.**
- **`setMinimumWidth(0)` + `SizePolicy.Ignored`** on the same row — shrinks it by **clipping rich text**,
  i.e. trading a scrollbar for the silent-clip trap `widgets.py` exists to document.

## One token, two jobs — the shape BREATHE's toolbar exemption exposed

Exempting `tb_pad`/`tb_space` and stopping there made the budget **worse than doing nothing**:

```
visible toolbar items at 1280      100%    110%    125%    150%
type scale only (before BREATHE)   15/15   14/15   13/15   11/15
+ spacing, tb_pad/tb_space exempt  15/15   13/15   11/15   10/15   <- WORSE
+ a QToolBar QToolButton rule      15/15   14/15   13/15   11/15   <- the baseline
```

The generic rule hands every toolbar button `btn_pad` — padding around **prose** on a card, where it must
grow, and around an **icon** in the toolbar, where it must not. **An icon does not need a wider gutter
because the body text grew.** Net: BREATHE costs the toolbar zero items, and that is a count, not an
argument.

## The remainder, named rather than silent

- **BREATHE's layout half.** Only **7 of 30** spacing declarations can move: `$space_N` appears **once** in
  the 542-line sheet, and the grid has 3 call sites against 148 layout calls. (The commit said "7 of 29".
  It went stale *inside the commit that added the 30th rule* — BREATHE's own `QToolBar QToolButton`
  exemption. The numerator and the 100%-identity both reproduce exactly; only the denominator moved, and
  it moved by the same hand that quoted it.) Card margins and `SECTION_GAP` are
  **layout** calls set at build time — they neither scale nor could update live without a rebuild path, the
  same gap `page_margins` already documents for density. That is why the card lands at 48.9% air instead of
  its 55.7%.
- **The toolbar is already overdrawn by the TYPE scale alone** — 14/15 at 110%, 11/15 at 150%. Items stay
  reachable via Qt's chevron; the cost is discoverability. Pre-existing, not fixed here.
- **`dark`'s button hover is the weakest in the tree at 1.0756** vs 1.10–1.31 for the other seven, and the
  1.05 fence floor is unjustified by any measurement (the file's only calibration point calls 1.0203
  "present but ~invisible"). The 6 community palettes were each audited and fixed; **the default never was.**
  A candidate, not a finding.
- **`info` is derived and has ZERO consumers** to this day — and MIST's own argument against gold rests
  partly on it. **A token with no call site is not future-proofing; it is a wish with a keyword.**
- **`text_subtle` is a loaded gun**: 3.20–3.59 on `surface_2` in 8/8. Fine where it is now spent (a 46px
  glyph, non-text bar 3.0, worst 3.06), sub-AA the moment anyone sets `role="subtle"` on real text.

---

## Round 6b — the adversarial review, and it was right about all of it

76 agents, 6 lenses, every finding then attacked by 3 skeptics (reproduce / already-deliberate /
instrument-error). **19 survived, 4 refuted.** I re-verified each survivor myself before acting; they hold.
This section exists because the findings are more useful than the round they audited.

### The shape of what it found

Round 6's whole thesis is *"a correct mechanism exists and the call site does not spend it."* The review's
verdict is that **I committed that same disease four more times while curing it**:

| I shipped | in the round about |
|---|---|
| two `:pressed` rules rendering **1.59** and **2.23** | a chip at **1.12** |
| `#railSeg:pressed` losing a **cascade tie** → the active segment dead on click | `#id` shadowing `:pressed` → 6 buttons dead on click |
| mapview's glyph onto **text_subtle at 3.06** | — the tier KEYLINE had *just* moved the tree OFF, citing 3.06 |
| **two vacuous fences** | a round that re-broke every fence to prove it fails |

**A law you are actively teaching is not a law you are following.** Writing the rule down, fencing it, and
quoting it in a commit message did not stop me applying its inverse two files away.

### The single most useful finding

**`probe_doc_pane.py` repointed `LOCALAPPDATA` at an empty tempdir — which makes `prefs.text_scale()` fall
through to `os_text_scale()`, the developer's Windows slider.** The probe that justified
`setMinimumWidth(700)` measured exactly one text scale: this machine's. That is *the same poison the last
commit in the range is about* — "a test that reads the developer's prefs is a report on the developer" —
reintroduced two commits earlier, by the probe that was supposed to be the evidence.

> **AN EMPTY TEMPDIR IS NOT A CLEAN ROOM. IT IS A HOLE THE OS FALLS THROUGH.**
> Every probe must PIN `prefs.text_scale` explicitly and sweep all four rungs.

It produced a constant that was **stale the moment it landed**, and the fence guarding it
(`assert mid.minimumWidth() >= 700`, offscreen) was structurally incapable of noticing, because it
asserted the constant was *present*, not that it was *right*.

### `setMinimumWidth(700)` — wrong in BOTH directions, reverted

|  | 100% | 110% | 125% | 150% |
|---|---|---|---|---|
| with the pin | 844 | 848 | 856 | 868 |
| reverted (Qt governs) | **686** | 723 | 841 | 964 |

- **It raised the app's hard floor 686 → 844.** `resize(720)` returned 844 — a **720px window became
  unreachable**, and 720 is exactly what `test_toolbar_overflows_gracefully_at_narrow_width` asks for. That
  test kept passing while silently measuring 844.
- **And it "helped" at 150% only by letting the document sit BELOW its own content minimum** (700 against a
  real 796). That is not a floor; it is permission to clip. The flat row above is the tell.

Not a tuning error: **any** explicit minimum above the pane's own 542 raises the window floor, so "fix the
narrow-persisted case" and "keep 720 reachable" cannot both hold this way. The narrow-persisted case still
scrollbars — it is the user's own saved layout, it is one scrollbar, and it is cheaper than an app that
refuses to be 720px wide. The honest fix (clamp the restored SIZES) re-proportions a layout the user
dragged and wants its own eye.

### `$pressed` is a ground nothing was ever solved against

`derive()`'s `_grounds = (bg, surface, surface_2)`. So I put three inks on `$pressed` by eye. Measured,
**nothing is legible there**: text 6/8, accent_fg 1/8, help_fg 0/8, muted 1/8. The press now **fills** with
the hue and spends the pair the palette already fences — `help_fg`/`help` (5.19), `accent_fg`/`accent`
(4.56). 8/8. *A fence that covers 3 of 4 grounds moves the bug to the 4th* — the arc's oldest law, and
`$pressed` is the 4th.

### The two vacuous fences, and why each could not fail

- **`test_the_dial_may_only_ever_grow_a_gap`** asserted monotonic + the 100% anchor. **A constant sequence
  satisfies both.** Revert BREATHE's grid half and it stayed green: `[8, 8, 8, 8]` is monotonic and
  anchored. → **A law of the form "X must change" cannot be built only from invariants a no-op satisfies.
  It needs one assertion the no-op FAILS.**
- **The press fence** called `setCheckable(True)` and never `setChecked(True)`. → **A state fence that never
  enters the state is testing the other state.** It missed `#railSeg:pressed` tying `:checked` at (0,1,1,1)
  and losing on source order — the segment you are ON was dead at 0px while its siblings changed 2968.

### Claims of mine it falsified

- *"Home never scrolls at any width"* — wrap makes the minimum the longest **unbreakable run**, not a
  constant: 53ch hyphenated → 525, 55ch CamelCase → 539, **a 90ch single token → 732, still scrolling at
  1280**. Smaller and rarer, not zero — and saying zero is how the next reader stops looking.
- *"#consoleToggle was the ONLY id-scoped QToolButton missing a `:focus` rule"* — **#gear has none either.**
  The mechanism claim was right; the census was wrong.
- *"0 of 29 / 7 of 29"* — the probe prints **7 of 30**. Stale *inside the commit that added the 30th rule*.
- `set_chip`'s docstring promised "a fill can never again arrive without its ink" while its two defaults
  were **independent**: `set_chip("BATTLE", pal["warn"])` → 1.56 on nord.

### What it cleared — do not re-verify

Every changed (ink, fill) pair at 4.5+ in all 8, recomputed with independent arithmetic · `_fg_token`'s
monotonic re-mix (the "it terminates sub-AA" accusation was refuted 3 ways — the accuser's re-implementation
was broken) · BREATHE / WCAG 2.5.8 (zero shrinks, nothing under 24) · **the `themed` fixture, rebuilt three
ways** (no sheet → search 5896: my first cut *would* have passed on Fusion's own chrome, exactly as the
commit confesses; `:pressed` removed → 0/0/0 — it fails when it should) · probe_doc_pane's splitter numbers
to the digit.

### Standing, recorded, not fixed here

- ~~**14 of 115 visible tab stops have a 0px focus delta**~~ — ✅ **CLOSED 2026-07-16, `105fcf9`. 0 dead on
  the real Tab chain**, and the count was wrong in both directions. The console/logs/map already carried a
  1px border, so their ring was the same free recolour the buttons got — **it was simply never written**;
  only the `NoFrame` scroll areas needed a reserved border (2px of viewport, no new scrollbars, no reflow).
  **A TAB STOP IS WHAT TAB REACHES**: `focusPolicy != NoFocus` sweeps in ClickFocus labels, and
  `& TabFocus` sweeps in QAbstractScrollArea's **viewport**, which reports StrongFocus and is not in the
  chain — the review's "CampaignMap + its viewport" was the same widget twice, and I reproduced the error
  by reproducing the method. Real count: **6**. `focusNextChild()` is the only honest census. Two more
  shared-state burns fell out, both invisible when the fence ran alone: **a toggle is not an instruction,
  it is a flip** (a module-scoped `win` meant `_toggle_console()` CLOSED it), and **Qt paints focus only on
  the ACTIVE window** (another fixture's top-level made all 34 stops read as dead — one inactive window,
  not 34 defects).
- **`$text` on `$pressed` is 4.09 in solarized-light** (systemic, via the generic rule). The real fix is
  adding `pressed` to `derive()`'s `_grounds` and spending a derived token at those four sites.
- `dark`'s button hover is still the weakest at 1.0756, and the 1.05 fence floor is unjustified by any
  measurement.
