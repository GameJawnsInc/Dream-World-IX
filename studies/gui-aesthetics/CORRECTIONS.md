<!--
The CORRECTION SET, 2026-07-15 -- the audit of PLAN.md / VISION.md / README.md against the code that was
actually written from them. Produced by a 74-agent workflow: one auditor per plan section, each verifying
claims against the CURRENT code, every FALSE/STALE verdict adversarially re-reviewed. 126 claims audited;
25 auditor verdicts (20%) were OVERTURNED on review -- which is why the second pass exists.

This file is the detail. The docs themselves carry inline SUPERSEDED/SHIPPED markers pointing here.

Nothing is deleted from the originals. The plan was wrong in a specific, traceable way and the record of
HOW is worth more than a tidy document: it measured surface->surface_2 (1.17) when a card is seen against
the page (bg->surface_2 = 1.31). A reader must be able to see the error, not just its correction.
-->

## The correction, in one paragraph

The dossier diagnosed the right screenshot and the wrong defect. Its one live bug — `style.py:126`'s `:focus::indicator` — was real, was fixed first, and every colour number it computed reproduces to the decimal. But its headline ("the elevation ladder is imperceptible; the fills do nothing; kill the QGroupBox, all 27 of them") measured the wrong pair: it computed `bg→surface` (1.120) and `surface→surface_2` (1.168), when a card sits on the **page**, and `bg→surface_2` measures **1.308** in DARK — a *stronger* step than GitHub dark's card (`#0d1117` vs `#161b22` = 1.094). The borderless section was built (685ba1a), shown, and overruled: *"the cards were nice logical section indicators, they just looked ugly."* What was ugly was never the fill or the border — it was the **caption sitting on the border** (the Win32 fieldset idiom), the **title with no presence** ($muted at the same 13px as the body it labels — and unfixable while Qt draws it, because QSS silently ignores `font-*` on `QGroupBox::title`; *that* is why the box had to become a widget), and the **missing horizontal padding**, amputated to defend an h-scroll bug that never existed at the claimed magnitude. So the card stayed and became `widgets.section()` — a QFrame `role="card"` with the title inside as a `role="overline"` label — across all 27 sites; QGroupBox is now constructed nowhere. Neither the fill nor the border was changed. The plan's mechanism shipped in full; its aesthetic premise did not survive contact with the user.

---

## PLAN.md

### 1. Diagnosis — the elevation receipt (line 27)

**Current:**
> - **The elevation ladder is imperceptible.** DARK: `bg→surface` 1.120:1, `surface→surface_2` 1.168, end-to-end 1.530. LIGHT: 1.105 / 1.046, end-to-end **1.205**. WCAG's *non-text* floor is 3:1. The fills do nothing; the hairline does everything — across **20 widget classes** at **9 radii** (`style.py`, 24 of 26 radius declarations hand-typed).

**Replace with:**
> - **~~The elevation ladder is imperceptible.~~ FALSE — THIS MEASURED THE WRONG PAIR (kept as the record).** DARK: `bg→surface` 1.120:1, `surface→surface_2` 1.168, end-to-end 1.530. LIGHT: 1.105 / 1.046, end-to-end **1.205**. Every figure reproduces to three decimals. **But no widget in this app is a bare `$surface` panel on the page.** A card sits on the *page*, so the governing pair is `bg→surface_2`: LIGHT 1.155 · **DARK 1.308** · nord 1.271 · dracula 1.247 · solarized-dark 1.332 · solarized-light 1.144 · gruvbox-dark 1.303. DARK's 1.308 is **stronger than GitHub dark's card** (`#0d1117` vs `#161b22` = 1.094, computed). The fill was always fine and was never changed (`widgets.py:159-161` records this in code). The 3:1 comparison is also a category error: WCAG 1.4.11 governs component *boundaries* and state indicators, not decorative surface fills — no shipping design system clears 3:1 page-to-card. What was ugly was the **caption**, not the fill (see Phase 3). The radius/class receipt is untouched and still exact: **20 widget classes** at **9 radii**, 24 of 26 radius declarations hand-typed. LIGHT remains the genuinely weak axis (`bg→surface_2` = 1.155) — which is why the card keeps its border there (LIGHT border-vs-fill 1.399 vs 1.155).

*Why: finding (B). The arithmetic was right; the inference was wrong, and the docs must show both.*

### 2. Diagnosis — the dead-system receipt (line 28)

**Current:**
> `space_1/3/4/6`, `radius_md` — **dead**; every gap is hand-typed, and every QGroupBox interior silently runs Qt's default 11/6 that no token file knows about.

**Replace with:**
> `space_1/3/4/6`, `radius_md` — **dead**; every gap is hand-typed, and every QGroupBox interior silently ran Qt's default 11/6 that no token file knew about. *(That clause is moot since 0ecfa75 — QGroupBox is constructed nowhere; `widgets.section()` hard-codes 16/12/16/16 and spacing 10/8 at `widgets.py:178-186` and `SECTION_GAP = 14` at `widgets.py:23`, **still not tokenized**, which makes the hand-typed-gap finding stronger, not weaker. It also inverted into a new one: the whole `QGroupBox` QSS block at `style.py:214-223` plus `$gb_margin_top`/`$gb_pad_top` (`style.py:68`, `:73`) are now **dead code** and should be swept.)*

*Why: 0ecfa75 removed the last construction; the clause is stale but its underlying finding is reinforced.*

### 3. Diagnosis — the `style.py:126` receipt (line 26)

**Add at the head of the bullet:**
> - **`style.py:126` WAS a live bug — SHIPPED, fixed in `86de3f5`.** The correct `::indicator:focus` now lives at `style.py:188`, the `:checked:focus` ring at `:192`, and the whole typo class is guarded structurally by `test_qss_has_no_malformed_subcontrol_selectors` (`test_workspace_style.py:129-147`). The `pseudoElement()`/`pseudoClass()` analysis below was right in every particular; `style.py:126` today is a bare `}`.

*Why: shipped; the reasoning is preserved because it was correct.*

### 4. Diagnosis — line-ref drift (line 28)

**Current:** `` `selection_bg` — derived, documented "replaces full-accent select", **never referenced** (`theme.py:306` vs `style.py:133`). ``
**Replace with:** `` `selection_bg` — derived, documented "replaces full-accent select", **never referenced** (`theme.py:309` vs the three full-accent selection rules it was built to replace: `style.py:157`, `:165`, `:171`). ``

**Current:** `` `font-weight: 500` (`style.py:198`) resolves to Regular — Segoe UI ships no Medium face. ``
**Replace with:** `` `font-weight: 500` (`style.py:264`, one consumer: `QLabel[role="label"]`) resolves to Regular — Segoe UI ships no Medium face (enumerated `C:/Windows/Fonts`: Regular/Bold/Italic/Light/Semilight/BoldItalic, zero Medium). ``

*Why: refs drifted; the facts hold exactly.*

### 5. The direction — WORKSHOP (lines 41–47)

**Current:**
> A dark table. Tools laid flat on it, nothing in a case. **Exactly one thing under the lamp.**
>
> The page is dark and mostly empty. A section is a small tracked-caps muted label, then its rows, then a generous gap before the next label — no fill, no frame, no floating caption cutting a line. Grouping comes from proximity and a shared left edge, the way it does in **Linear's settings** and **Zed's settings pane** — both of which abolished the titled box a decade ago and are the closest living relatives of this app's shape (nav tree left, stacked option groups right, dense, dark, technical).
>
> On any screen: **one** lifted surface, **one** accent object, **one** 20px title. Everything else is type on the table — 13px `$text` for what you act on, 11px `$muted` for what explains it. Controls are named in three words; the sentence lives underneath in grey, wrapped, capped at a readable measure. And because this app's entire subject is machine tokens — `4003`, `30110`, `ff9-XXXXXXXX`, `FF9CustomMap` — those are set in a mono family, the one texture in the composition and the thing that makes it look like it knows what it is.
>
> The test, every time: **is this under the lamp, or on the table?** Almost everything is on the table.

**Replace with:**
> *(SUPERSEDED IN PART, 2026-07-15 — the containment half was built, shown, and overruled. The metaphor survives; it is re-spent on RANK, not containment. The original text is preserved below the rewrite.)*
>
> A dark table. Tools laid out on it in shallow trays. **Exactly one thing under the lamp.**
>
> The page is dark and mostly empty. A section is a shallow tray: a small tracked-caps muted label at its top-left, its rows beneath, 16px of air inside the tray and 14 between trays. The tray is quiet on purpose — it is a *logical indicator*, not a frame competing for attention: `$surface_2` on `$bg` (**1.308** in DARK — a stronger step than GitHub's dark card at 1.094) with a 1px `$border` that does the carrying in LIGHT (`surface_2`→`border` 1.399 vs the fill's `bg`→`surface_2` 1.155). The tray never shouts; the title inside it is what you read.
>
> On any screen: **one** accent object, **one** 20px title. Elevation is **no longer scarce** — it is the section grammar; rank with type, space and accent instead. Everything else is type on the table — 13px `$text` for what you act on, 11px `$muted` for what explains it. Controls are named in three words; the sentence lives underneath in grey, wrapped, capped at a readable measure. And because this app's entire subject is machine tokens — `4003`, `30110`, `ff9-XXXXXXXX`, `FF9CustomMap` — those are set in a mono family, the one texture in the composition.
>
> The test, every time: **is this under the lamp, or on the table?** Almost everything is on the table. The trays are the table.
>
> ---
> **What this replaced, and why (the record).** The original read: *"Tools laid flat on it, nothing in a case… A section is a small tracked-caps muted label, then its rows, then a generous gap before the next label — no fill, no frame, no floating caption cutting a line. Grouping comes from proximity and a shared left edge, the way it does in Linear's settings and Zed's settings pane — both of which abolished the titled box a decade ago… On any screen: one lifted surface, one accent object, one 20px title."* It was built at `SECTION_GAP = 24` (685ba1a) and the user overruled it: *"the cards were nice logical section indicators, they just looked ugly."* The appeal to Linear/Zed is struck — it was cited as authority for a prescription the user overturned, and "a decade ago" is arithmetically false (Zed shipped 2023, Linear founded 2019). What **did** survive verbatim is the type prescription: `widgets.py:182` is `role_label(title.upper(), "overline")` → `style.py:286` `11px / 600 / +1px tracking / $muted`. That clause is also what *forced* the widget rewrite — QSS silently ignores `font-*` on `QGroupBox::title`, so the plan's own title spec was deliverable only by making the box a QFrame.

*Why: findings (A) + (C.2). The name and the lamp test survive; every containment sentence is dead.*

### 6. The three laws — Law I (line 51)

**Current:**
> **I. A border must earn its existence.** Group by space and type first. A stroke is for things you can click into or type into — a button, an input, a tab, a focus ring. A *container* is not a stroke; it is a label and a gap. If you removed the border and the grouping still reads, the border was noise.

**Replace with:**
> **I. A border must earn its existence.** *(The test survives; its answer for the container was overturned — see the record below.)* A stroke is for things you can click into or type into — a button, an input, a tab, a focus ring — **and for a container, unconditionally, in every palette**. A container is a label, a gap, a fill and a padding *and* a stroke (`style.py:277`, one unconditional rule: `QFrame[role="card"] { background: $surface_2; border: 1px solid $border; border-radius: $radius_lg; }`). Each mode takes the reading it can: DARK's fill leads (1.308 vs the border's 1.182), LIGHT's border leads (1.399 vs the fill's 1.155). What a container must **never** be is a stroke *cut by its own caption*, a title with **no presence**, and content run to the edge: that is the fieldset, and that is what was ugly. If you removed the border and the grouping still reads, the border was noise — the card's border is **not** noise; measured, it is the only thing that makes a LIGHT card visible at all.
>
> *SUPERSEDED (record): this law originally read "A **container** is not a stroke; it is a label and a gap. If you removed the border and the grouping still reads, the border was noise. **It usually does, once the gap is right.**" That hypothesis was tested — at the doc's own 24px (`685ba1a`, `SECTION_GAP = 24`, `section()` "no fill, no frame") — and rejected by the only oracle that counts. **Removing a container is a hypothesis about how a page reads, and it is testable only by the user.***

*Why: finding (A) + the LIGHT/DARK measurements. Law I's test is good; its predicted answer was wrong.*

### 7. The three laws — Law II (line 53)

**Current:** `**II. One thing per screen is loud.** One accent object, one lifted surface, one page title.`
**Replace with:** `**II. One thing per screen is loud.** One accent object, one page title. *(The "one lifted surface" clause is struck: `importdoc.py` alone builds 10 `widgets.section()` cards, each `$surface_2`. Elevation is now the section grammar, not a scarce rank — rank with type, space and accent.)*`

**Append to the law:**
> Still unpaid at HEAD: `importdoc.py:375` and `:651` are both `setObjectName("accent")`, and `shell.py:1059`'s accented Deploy F9 rides on every tab = **3 accent objects on Import**. `builddoc.py:159-161` still sets a ~140-char wrapped `self.dest` to `role="accent"` — accent as a foreground for prose, the exact thing this law forbids, and sub-AA in 6 of 7 palettes.

*Why: the law is intact and still live work; only the elevation clause is void.*

### 8. The asymmetry law (line 57)

**Current (tail):** `**Dark gets depth from a widened tonal span; light gets it from a border and a gap.** This is why Law I says *space and type*, not *tone*.`
**Replace with:**
> **Dark gets depth from a widened tonal span; light gets it from a border and a gap.** *(VINDICATED by what shipped, with a different conclusion: the card ships as **one unconditional rule** (`style.py:277`) and lets each mode take the reading it can — DARK's fill leads (1.308 vs the border's 1.182), LIGHT's border leads (1.399 vs the fill's 1.155). That is why a container may **keep** its stroke — and why no container may rely on fill **alone**.)*

*Why: the premise reproduces to the digit (LIGHT `surface_3` = `#ffffff`, rungs 1.046/1.043); only the "space and type, not tone" conclusion was overtaken.*

### 9. The one change that proves it — Step 0 (lines 65–87)

**Current heading:** `### Step 0 — ship this in the next ten minutes`
**Replace with:** `### Step 0 — ✅ SHIPPED (86de3f5) — the selector fix`

**Current:** `` `ff9mapkit/ff9mapkit/workspace/style.py:126`, replace one line with two: ``
**Replace with:** `` LANDED verbatim. The rules now live at **`style.py:188`** (`QCheckBox::indicator:focus, QRadioButton::indicator:focus`) and **`style.py:192`** (`::indicator:checked:focus`), with the law in a comment at `:181` and a structural backstop at `test_workspace_style.py:129-147`. `style.py:126` is now a bare `}`. Shipped exactly as specified below — zero substantive divergence: ``

**Keep:** the code block and the Before/After/Verified paragraphs verbatim.
**Also keep verbatim (VINDICATED):** `**Do not start with the groupbox refactor.** The screenshot contains a one-line bug, and nobody has looked at the panel without it.` — **add:** *This was the section's most durable instruction and it was right: had the refactor gone first, the phantom rects would have been attributed to the box.*

### 10. Step 1 — `_OPT_INDENT` (lines 93–97)

**Current:**
> ```python
> _OPT_INDENT = 31   # radio TEXT column: 3px left inset + 20px indicator (style.py:90 width:18 +
>                    # 1px border EACH SIDE -- QSS puts the border OUTSIDE width) + 8px spacing
>                    # (style.py:88). Measured via style().subElementRect(SE_RadioButtonContents).x().
>                    # NOT 26 or 28 -- both are naive arithmetic that lands 3-5px short.
> ```

**Replace with:**
> ```python
> _OPT_INDENT = 30   # radio TEXT column: 2px left inset (style.py:123 `padding: 3px 2px` is 3 VERTICAL
>                    # / 2 HORIZONTAL -- the plan misread the 3 as the inset) + 20px indicator
>                    # (style.py:125 width:18 + 1px border EACH SIDE -- QSS puts the border OUTSIDE
>                    # width) + 8px spacing (style.py:123) = 30.
>                    # Measured via style().subElementRect(SE_RadioButtonContents, opt, w).x() -> 30,
>                    # in BOTH densities. NOT 26 or 28 -- naive arithmetic lands 2-4px short.
>                    # WAS 31 in the plan: that number was derived, not run, AND it was measured
>                    # through the Step 0 bug -- the malformed `:focus::indicator` degraded to an
>                    # unconditional 1px border on the CONTROL, which added the missing pixel.
>                    # Post-86de3f5 it is 30. Font-invariant (verified 6-40pt), so the offscreen-QPA
>                    # width caveat does not apply.
>                    # SURVIVES THE CARD: a radio nested in widgets.section() still reports x=30 --
>                    # section()'s 16px h-padding shifts radio and caption equally (same layout column).
> ```

*Why: the method the doc claims it used returns 30 at HEAD (31 under the plan-era sheet, via the bug Step 0 removes). Measure it; do not derive it.*

### 11. Step 1 — the raw cap in `_opt()` (line 106)

**Current:** `    c.setMaximumWidth(PROSE_W)          # see the token diff`
**Replace with:**
> ```python
>     c = widgets.prose(text)             # the capped-measure wrapped label (widgets.py:138).
>                                         # A raw setMaximumWidth clips ONCE NESTED -- and _opt's
>                                         # caption is nested (builddoc.py:121-122 puts it in a
>                                         # section() card). Keep setProperty("role","caption") --
>                                         # the shipped Prose sets no role; drop setWordWrap (it
>                                         # already wraps, widgets.py:125).
> ```

*Why: `widgets.Prose` shipped (685ba1a) precisely to make this cap honest; the raw cap reintroduces the landmine the same phase documents.*

### 12. Step 2 — line drift + rule refs (lines 121, 141, 148)

- `**Step 2 — demote the blue paragraph** (`builddoc.py:158-161`, and `_update_dest` at `:378-407`).` → `**Step 2 — demote the blue paragraph** (`builddoc.py:159-162`, and `_update_dest` at `:378-407`). **STILL UNSHIPPED and still needed** — `self.dest` is still `role="accent"` at `builddoc.py:161`.`
- `Give it weight via the rule that already exists (`style.py:205`):` → `Give it weight via the rule that already exists (`style.py:268` — `QLabel[role="muted"][state="warn"] { color: $warn; }`, which fires only for `role="muted"`, i.e. exactly what Step 2 sets):`
- `` `_update_dest` runs *after* first polish — the repolish is not optional (`widgets.py:213`). `` → `` `_update_dest` runs *after* first polish — the repolish is not optional (`widgets.py:316`). ``

### 13. Step 3 (line 150)

**Current:** `**Step 3 — land the `surface_2` contrast assertion first** (see Phase 0). Steps 1–2 put captions inside a `$surface_2` groupbox, where `muted` measures **3.87–4.07** in NORD / DRACULA / SOLARIZED-DARK / GRUVBOX — sub-AA *today*, uncaught because the contrast test only ever checks `bg` and `surface`.`

**Replace with:**
> **Step 3 — ✅ SHIPPED (86de3f5).** Steps 1–2 put captions inside a `$surface_2` **card** (`widgets.section()` → `QFrame[role="card"]`, `style.py:277` — the same token the QGroupBox used, so this dependency survived the reversal unchanged). `muted` there **measured** 3.87–4.07 in NORD / DRACULA / SOLARIZED-DARK / GRUVBOX — sub-AA, uncaught because the contrast test only ever checked `bg` and `surface`. 86de3f5 lifted all four (now **4.55–4.61**) and `test_editor_theme.py:109-110` now guards the rung for every palette.

### 14. Step 1–3 closing gate (line 152)

**Current:** `**Zero borders removed.** If it reads well, the groupbox verdict was never needed. If it still reads badly, *now* you know the box is the problem and Phase 3 has earned its risk.`

**Replace with:**
> **Zero borders removed.** *(THE GATE RAN. It returned neither branch. The rects went, the box still read badly — and the diagnosis was wrong. The box was not noise: `bg→surface_2` measures **1.308** in DARK, stronger than GitHub dark's 1.094. It was ugly for three fixable reasons, the load-bearing one being that **QSS silently ignores `font-*` on `QGroupBox::title`**, so the title could never be given presence while Qt drew it. That, not "borders are noise", is why the box became a widget. **Zero borders removed — permanently.** And the landmine this section never mentions: Qt derives an unnamed control's screen-reader name from its enclosing QGroupBox **title**, so any box that goes away takes names with it — 13 did. **The migration is not mechanical.**)*

### 15. Phase 0 (lines 158–188)

**Current heading:** `### Phase 0 — Close the contrast hole and fix the selector — **trivial**`
**Replace with:** `### Phase 0 — ✅ SHIPPED (86de3f5) — Close the contrast hole and fix the selector`

**Table row:** `| The `::indicator:focus` reorder + the `:checked:focus` ring | `style.py:126` |` → `| ✅ The `::indicator:focus` reorder + the `:checked:focus` ring | LANDED at `style.py:188` / `:192` |`

**Table row:** `| Lift `muted` in the 4 failing palettes until green | `theme.py` NORD/DRACULA/SOLARIZED_DARK/GRUVBOX_DARK — **values only**, no keys |`
**Replace with:** `| ✅ Lift `muted` in the 4 failing palettes — **and solarized-dark's `text` too** — until green | `theme.py` NORD `:83` `#9aa3b5→#aab2c1` (4.61) · DRACULA `:107` `#8f95bc→#9ca2c4` (4.56) · SOLARIZED_DARK `:134` `#7f9e9e→#8eaaaa` (4.55) **+ `:133` text `#93a1a1→#a2aeae` (4.22→4.94)** · GRUVBOX_DARK `:184` `#a89984→#b1a390` (4.59) — **five values, not four**. Key sets unchanged, so "no keys" held. |`

**Assertion snippet — append a third assert:**
> ```python
> # NOT FORESEEN by the plan, and mandatory: two contrast floors alone do not pin the ramp.
> # A naive solve for the two asserts above INVERTED solarized-dark (muted L=0.3740 vs text
> # L=0.3720) and ran muted to #ffffff. This is what makes solarized-dark's text over-lift
> # (to 4.94, past its own 4.5 minimum) necessary rather than arbitrary.  -- test_editor_theme.py:113
> assert (_luminance(pal["muted"]) < _luminance(pal["text"])) is bool(pal["dark"]), \
>     f"{mode}: muted must stay dimmer than text"
> ```

**Lint snippet — replace with the shipped, stronger form:**
> ```python
> def test_qss_has_no_malformed_subcontrol_selectors():
>     import re
>     for mode, pal in theme.THEMES.items():          # all 7, not dark alone
>         css = qss(pal)
>         bad = re.findall(r"[A-Za-z_][\w-]*:[a-z-]+::[a-z-]+", css)
>         assert not bad, f"{mode}: pseudo-class before sub-control (Qt matches neither): {bad}"
> ```

**Current:** `**Fails today** in nord/dracula/solarized-dark/gruvbox-dark (muted) and solarized-dark (text). Land the palette lift in the **same commit** or the test is red on arrival.`
**Replace with:** `**Failed** in nord/dracula/solarized-dark/gruvbox-dark (muted 3.873 / 3.911 / 3.912 / 4.069) and solarized-dark (text 4.216) — every figure independently reproduced against `fd1e459:theme.py`. The palette lift landed in the **same commit**. All 7 now clear (lowest: solarized-dark muted 4.553); 33/33 tests pass.`

### 16. Phase 1 — `PROSE_W` / `_Prose` (line 200)

**Current:** `| Add `PROSE_W = 400` and the measure-capped `_Prose` label | `widgets.py` (new; see the token diff) |`
**Replace with:** `| ✅ SHIPPED (685ba1a) as `PROSE_W = **620**` + a **public** `Prose` class and `prose()` factory | `widgets.py:105`, `:110`, `:138`. ⚠ The shipped docstring justifies 620 as "~75-85 chars at 13px Segoe UI" — **that arithmetic is wrong**: at a *real* font DB Segoe UI 13px measures **5.84 px/char**, so 620 = ~106ch and 75-85ch is 438-496px. The plan's 400 (= 68ch) was a real measurement. Either restate the reason or re-tune the value; do not leave a false receipt in the tree. |`

### 17. Phase 1 — the landmine (line 203)

**Current:** `**Landmine:** a raw `setMaximumWidth` on a word-wrapped QLabel **clips inside a QGroupBox**. `QBoxLayout::calcHfw` asks `heightForWidth()` at the *full* cell width, so the box reserves 2 lines and then lays the label out at 400px needing 4. Verified: subclass → `w=440 h=96 need=96`; raw cap → `w=440 h=48 need=96 *** CLIPPED ***`.`

**Replace with:**
> **Landmine (CONDITIONAL — the plan's unconditional phrasing was wrong):** a raw `setMaximumWidth` on a word-wrapped QLabel clips **once it is nested in a parent layout** — QGroupBox and `widgets.section()` alike. It does **not** clip standalone. `QBoxLayout::calcHfw` asks `heightForWidth()` at the *full* cell width, so the parent reserves 2 lines and then lays the label out at the cap needing 4. Re-measured at the shipped 620px cap: raw cap **standalone** `h=68 need=68 ok`; raw cap **nested** (QGroupBox *and* section()) `h=40 need=68 *** CLIPPED ***`; `Prose` `h=68 need=68 ok` in all three. The subclass is justified — the phrasing was not. Treat the absolute px as offscreen-inflated (the plan's `440/96/48` are not trustworthy digits); the **ok/CLIPPED verdict** is what holds.

### 18. Phase 1 — the prose test (lines 208–215)

**Current:** `    box = QGroupBox("x"); lay = QVBoxLayout(box)`
**Replace with:** `    box = widgets.section("x"); lay = box.content_layout   # NOT QGroupBox -- 0ecfa75 removed the last construction; guard the container that actually ships (verified: it reproduces the clip, h=40 need=68)`

**Also rename the test:** `def test_prose_reports_a_truthful_height_inside_a_groupbox(qtbot):` → `def test_prose_reports_a_truthful_height_inside_a_section_card(qtbot):`
**And add:** `**NOT SHIPPED — still owed.** No `test_prose_*` exists anywhere under `ff9mapkit/tests/`.`

### 19. Phase 2a — the disabled-idiom citation (line 240)

**Current:** `` `color: $text`, **not** `$muted`: `style.py:59-60` already spends *transparent + muted* as the **disabled** idiom. ``
**Replace with:** `` `color: $text`, **not** `$muted`: `style.py:61` already spends *transparent + muted* on the disabled **QToolButton**, and `:59` spends *muted + `$bg`* on the disabled QPushButton — muted-on-a-fill-less button is the established "unavailable" reading either way. *(The plan cited `style.py:59-60` for "transparent + muted"; that is a misattribution — `:59` is `QPushButton:disabled { color: $muted; background: $bg; }` and `:60` is a comment. The conclusion stands on the visual argument; the evidence did not.)* ``

### 20. Phase 2c — the mono ref (line 268)

**Current:** `Also fix `style.py:161`, which hardcodes `font-size: 12px` while `$type_mono` sits unreferenced → use the token.`
**Replace with:** `Also fix **`style.py:227`** (was `:161`), which hardcodes `font-size: 12px` while `$type_mono` (`style.py:56`) sits unreferenced → use the token. Still true at HEAD; `type_mono` is genuinely dead.`

**Phase 1/2 line-drift note — add under the Phase 1 table:**
> **NB — every Phase 1/2 `file:line` was exact at `fd1e459` and has since drifted by the card migration, not by an authoring error.** Re-anchor: `builddoc.py` **+1** below `:158` (`self.dest` `:158→:159-162`; `newgame_id` `:234→:235`; `battle_dest` `:259→:260`; `trigger` `:264→:265`; `addStretch` `:114` unmoved); `coopdoc.py` **+12** below `:105` (`btn_start` `:193→:209`, `setDefault` `:194→:210`, `spin_wait` `:153→:165`; `self.code` `:105` unmoved); `style.py` **+66** (`:161→:227`, `:88/:90→:123/:125`); `widgets.py:213→:316`.

### 21. Phase 3 — the whole header + goal (lines 280–284)

**Current:**
> ### Phase 3 — Kill the QGroupBox — **medium** *(gated on the Phase 1 screenshot)*
>
> **Goal:** the outer rectangle stops existing. Grouping becomes a label and a gap.
>
> **Do not start this until Phase 1 has been screenshotted and judged.** If the spike already reads well, this is optional. If it doesn't, this is the answer and the risk is earned.

**Replace with:**
> ### Phase 3 — ✅ SHIPPED, **REVERSED IN INTENT** (685ba1a → 881e468 → 0ecfa75) — the QGroupBox becomes a card
>
> **Goal as written:** *"the outer rectangle stops existing. Grouping becomes a label and a gap."* **OVERTURNED.** The borderless build shipped (685ba1a, Co-op, `SECTION_GAP = 24`, "no fill, no frame"), was shown, and the user overruled it: *"the cards were nice logical section indicators, they just looked ugly."*
>
> **Goal as landed:** the outer rectangle **STAYS** and becomes a real card. The QGroupBox — a Win32 fieldset whose caption cuts its own stroke and whose title font QSS cannot touch — is replaced by a QFrame the app controls. `widgets.section()` (`widgets.py:143-195`) returns a `QFrame` `role="card"` (`style.py:277`: `background: $surface_2; border: 1px solid $border; border-radius: $radius_lg`) with the title **inside** as a `role="overline"` label and 16px padding. 27/27 sites migrated; **QGroupBox is constructed nowhere in the workspace.**
>
> **This was never gated on the screenshot.** The forcing function is a Qt limitation — `QGroupBox::title` accepts colour and nothing else — so the title could not be given presence while Qt drew it. The screenshot only decided the **skin** (card, not nothing).
>
> **What actually landed:**
>
> | # | Change | Where | Status |
> |---|---|---|---|
> | 1 | `widgets.section(title)` → QFrame `role="card"`, returns the **FRAME** (not a tuple); exposes `.content_layout` / `.title_label`, mirroring `disclosure()` (`widgets.py:273`) | `widgets.py:143-195` | SHIPPED |
> | 2 | Title moves **INSIDE** the card as a `role="overline"` QLabel (11px/600/+1px, upper-cased at the call site — Qt has no `text-transform`) — the ONLY fix for `QGroupBox::title` ignoring `font-*` | `widgets.py:182-184` | SHIPPED |
> | 3 | 16px horizontal padding restored (`setContentsMargins(16,12,16,16)`, spacing 10 / body 8); the h-scroll bug it was amputated for never existed at the claimed magnitude (offscreen QPA inflates advances 2–3×) | `widgets.py:178-186` | SHIPPED |
> | 4 | Content host is a **LAYOUT**, never a wrapper QWidget — the universal `QWidget { background-color: $bg }` (`style.py:81`) makes a wrapper paint the PAGE colour **over** the card fill | `widgets.py:186-192` | SHIPPED (bug hit + fixed) |
> | 5 | 27 sites: builddoc 6 · importdoc 10 · coopdoc 3 · battledoc 3 · modelsdoc 3 · savedoc 1 (`:443`) · shell 1 (`:1937`) | all docs | SHIPPED — census exact |
> | 6 | **A11Y: pair every adoption with a name.** Qt derives an unnamed control's SR name from the enclosing QGroupBox **TITLE**; a card has none. **13 names went silent** across Models/Import/Build. Restored via `setBuddy` on the visible label (+ `setAccessibleName` where none exists) | coopdoc `:113-115,129,170,187` · modelsdoc `:181,197,233,250,283,360` · importdoc `:94,180,213,226,232` · builddoc `:73,145` | SHIPPED — **THE MIGRATION IS NOT MECHANICAL** |
> | 7 | `SECTION_GAP = 14` (not 24) — the card draws its own boundary | `widgets.py:23` | PARTIAL — one consumer, `coopdoc.py:70`, whose comment is now false |
> | 8 | **NOT changed: the fill, the border.** `bg→surface_2` = **1.308** DARK vs GitHub dark card **1.094** | — | NO-OP, deliberate |
> | 9 | Dead `QGroupBox` / `QGroupBox::title` QSS + `$gb_margin_top` / `$gb_pad_top` | `style.py:214-223`, `:68`, `:73` | **OPEN** — dead CSS, nothing constructs a QGroupBox |
> | 10 | Card-in-card nesting | builddoc `:191→:209` · importdoc `:83→:124/:145/:160` | **OPEN** — the un-nest premise died with the borderless plan |
>
> **Why the per-tab rule mattered less than expected:** the card kept the boxed look, so a half-migrated page read as *consistent* rather than unfinished. The real serialization pressure was the **a11y sweep**, not the aesthetics.

### 22. Phase 3 — the factory (lines 286–310)

**Current (code block):**
> ```python
>     box = QGroupBox(parent)
>     box.setTitle("")
>     box.setAccessibleName(title)
>     lay = QVBoxLayout(box)
>     lay.setContentsMargins(0, 0, 0, 0)
>     lay.setSpacing(6)
>     lay.addWidget(role_label(title, "overline"))   # style.py:220 -- ALREADY 11px/600/$muted/+1px
>     return box, lay
> ```

**Replace with:**
> *(NOT what shipped. The proposed recipe is preserved above as the record; every line diverged. The built form:)*
> ```python
>     box = QFrame(parent)                       # NOT a titleless QGroupBox
>     box.setProperty("role", "card")            # -> style.py:277 fill + 1px border + $radius_lg
>     v = QVBoxLayout(box)
>     v.setContentsMargins(16, 12, 16, 16)       # NOT (0,0,0,0) -- the h-padding is the point
>     v.setSpacing(10)                           # NOT 6
>     lab = role_label(title.upper(), "overline")  # style.py:286; Qt has no text-transform
>     lab.setAccessibleName(title)               # announce the non-shouty form
>     v.addWidget(lab)
>     body_lay = QVBoxLayout(); body_lay.setSpacing(8)
>     v.addLayout(body_lay)                      # A LAYOUT, NEVER A WRAPPER QWIDGET -- see below
>     box.content_layout = body_lay; box.title_label = lab
>     return box                                 # the FRAME alone, mirroring disclosure()
> ```
> **The wrapper bug, found while building:** the stylesheet opens with a universal `QWidget { background-color: $bg; }` (`style.py:81`), so a bare `QWidget` used as the content host paints the **PAGE** colour on top of the card fill — a visible darker rectangle in every card. It is invisible on a borderless section (bg on bg) and **only surfaces once the card has a fill**, which is exactly why the plan's own borderless spec could not have caught it.
>
> **The a11y landmine the plan never mentions.** `setAccessibleName` on the frame does **not** restore descendant names. Qt derives an unnamed control's screen-reader name from its enclosing QGroupBox **TITLE** (`QAccessibleWidget` → `buddyString`, which reads `groupbox->title()` — *not* `accessibleName()`), so the plan's own drop-in recipe (`setTitle("") + setAccessibleName`) strips them **identically to the card**. 13 names went silent; `test_workspace_a11y.py:69` caught them. Each site needs `setBuddy(visible_label)`, or `setAccessibleName` where no visible label exists (`coopdoc.py:129`, `importdoc.py:94`, `modelsdoc.py:360`, `builddoc.py:73,145`). **Any doc calling this migration "mechanical" is wrong — strike that word from this phase.**

**Current:** `` `role="overline"` already exists, is already tokenized, and is already unused. Zero new palette keys. ``
**Replace with:** `` `role="overline"` already exists and is already tokenized (`style.py:286`) — and is **already in use on the Home page** (`shell.py:1536`, `_home_section`), so `section()` adopting it makes the card title and the Home section header **one register** rather than introducing a new one. ("Already unused" was false when written.) Zero new palette keys either way. ``

**Keep verbatim (VALID, and now the load-bearing rationale — it is quoted in the shipped docstring at `widgets.py:150-153`):**
> The header is a real QLabel because QGroupBox::title SILENTLY IGNORES font declarations -- render-verified: ink identical at 13/600, 11/700+1px tracking, and 18/700.

### 23. Phase 3 — the borderless QSS (lines 315–322)

**Current:**
> ```
> QGroupBox { background: transparent; border: 0; border-radius: 0;
>             margin-top: $gb_margin_top; padding-top: $gb_pad_top; }
> ```
> …
> Set `gb_margin_top` / `gb_pad_top` to `"0px"` in **both** density profiles (keep both keys — `test_qss_density_profiles_both_substitute_cleanly` requires them) and let `section()` own the rhythm via layout spacing.

**Replace with:**
> *(SUPERSEDED and MOOT — never applied. The live card rule is `style.py:277` `QFrame[role="card"] { background: $surface_2; border: 1px solid $border; border-radius: $radius_lg; }` — **unchanged fill, unchanged border, by design** (the fill was never the defect). `$radius_lg` = 8px, so it is byte-equivalent to the old box rule.)*
>
> **OPEN ITEM instead — `style.py:214-223` is now DEAD CSS.** Nothing constructs a QGroupBox, yet the `QGroupBox` / `QGroupBox::title` rules survive (including an inert `font-weight: 600` at `:222` and the `NB: no left/right padding` comment at `:218`, defending an h-scroll bug that was never real at the claimed magnitude). **DELETE, don't zero.** The plan's own "keep the keys — the test requires them" was a misreading: `test_qss_density_profiles_both_substitute_cleanly` (`test_workspace_style.py:78-86`) asserts only `"$" not in css`, and `Template.substitute` ignores *extra* mapping keys — so deleting the rules is a clean one-step edit and `$gb_margin_top`/`$gb_pad_top` (`style.py:68`, `:73`) merely go inert. The **one-way** constraint is the reverse: you cannot drop the keys while `:216` still references them (`KeyError: 'gb_pad_top'`).

### 24. Phase 3 — the whitespace law (line 324)

**Current (opening):** `**Pay the whitespace or don't ship it.** Every lens that deleted the box while leaving the page at `setSpacing(12)` measured *worse* — an orphaned label floating equidistant between two groups is not a section. Measured target: **~2:1 above:below**. Set the page column to `v.setSpacing(24)``

**Replace with:**
> **Pay the whitespace or don't ship it — RE-SCOPED, not repealed.** The law was priced for a borderless page where the gap *alone* carried the grouping (~2:1 above:below, 24px): an orphaned label floating equidistant between two groups is not a section. **The card carries its own boundary**, so the gap only has to beat the 8px in-card row spacing (`widgets.py:189`): **`SECTION_GAP = 14`** (`widgets.py:23`), landed — *"The card draws its own boundary, so this gap does not have to carry the grouping by itself."* **What did NOT ship: adoption.** `grep -rn SECTION_GAP` finds exactly **one** consumer, `coopdoc.py:70` — whose comment (*"the box borders are gone -- this gap IS the grouping now"*) is now **false in-code and must be fixed**. The other 6 doc pages still run their own spacing. **OPEN.** (The `QSpacerItem`-vs-`setSpacing()` reasoning below is untouched and still correct.)

### 25. Phase 3 — the migration + exceptions (lines 326–328)

**Current:** `**Migrate per TAB, never per box** — 27 sites: builddoc 6, importdoc 10, coopdoc 3, battledoc 3, modelsdoc 3, savedoc 1, shell 1.`
**Prepend:** `✅ **LANDED (685ba1a + 0ecfa75), 27/27; census verified exact to the file.** Order held: Co-op first as a proving spike (3), then the remaining 24 in one pass — so no partial state ever shipped.`

**Current:** `Only after site 27 delete the `QGroupBox` rules.`
**Replace with:** `Only after site 27 delete the `QGroupBox` rules. **← RIPE, NOT DONE.** Site 27 landed (0ecfa75); the rules at `style.py:214-223` were **not** deleted and are now orphaned. This instruction has come due — it is a clean delete (see above).`

**Current (exception):** `**Exceptions:** `shell.py:1937` `QGroupBox(f"Fork the arcs ({len(done)}/{len(folders)} forked)")` is a live-counter primary affordance — give it `role="h3"`, not an 11px muted overline.`
**Replace with:** `**Exceptions:** `shell.py:1937` — now `section(f"Fork the arcs   ({len(done)}/{len(folders)} forked)")` — is a live-counter primary affordance. **The warning came true and the exception was silently dropped:** it renders today as `FORK THE ARCS   (2/5 FORKED)` in an 11px muted overline. `section()` exposes `.title_label` (`widgets.py:194`) and `role="h3"` exists (`style.py:285`, 15px/600, zero call sites), so the override is a one-liner at the call site. **OPEN and untested either way** — and supported by the same argument that forced the widget (a title needs presence). *(The sibling exception DID hold: `battledoc.py:558/619/650` keep their dense `(8,4,8,4)` interiors.)*`

### 26. Phase 3 — the un-nest (line 330)

**Current (opening):** `**Un-nest the two real nestings** (`builddoc.py:208→220`, `importdoc.py:123/144/159 → 83`): once the parent is borderless, the child's 10px inset already reads as subordination.`

**Replace with:**
> **Un-nest the two real nestings — the premise is void and the problem is WORSE.** *"Once the parent is borderless"* never happened: the parent has a fill **and** a border. The nestings persist as **card-in-card** at identical `$surface_2` (contrast **1.000**), so the inner card is a bare stroke with **zero** elevation step: `builddoc.py:191`→`:209` and `importdoc.py:83`→`:124/:145/:160`. (`builddoc.py:93`'s `adv` is **not** a nesting — `disclosure()` returns a plain QWidget, `widgets.py:278`.) Un-nesting is still right; the mechanism must now be either promoting the child to `$surface_3` or flattening it to a plain overline label inside the parent card. **UNRESOLVED — needs a screenshot, not a measurement.**

**Current (tail):** `— **never** `$text_subtle`, which fails 4.5:1 on `surface_2` in **all 7** palettes (2.55–3.20).`
**Replace with:** `— **never** `$text_subtle`, which fails 4.5:1 on `surface_2` in **all 7** palettes (**2.87–3.20**, recomputed after the Phase-0 muted lift: `text_subtle` derives from `muted` at `theme.py:310`, so the AA fix dragged this tier up too — and it still fails everywhere). The rule stands verbatim: subordination comes from **type**, not from dimming.`

### 27. Phase 3 — the free rider (line 332)

**Current:** `**The free rider:** deleting the fill lands every caption on `$bg`, where `muted` is tested and passes in all seven. **The aesthetic move is the accessibility fix.**`

**Replace with:**
> **~~The free rider~~ — OVERTAKEN, and the ledger ran the other way (kept as the record).** *As written:* "deleting the fill lands every caption on `$bg`, where `muted` is tested and passes in all seven. **The aesthetic move is the accessibility fix.**" Every factual component was true when written — muted **did** pass on `bg` in all 7 (4.52–6.31) and **did** fail on `surface_2` in four, on a rung the suite explicitly did not test — and it correctly fingered the exact live defect. But **the fill was never deleted**, so no caption landed on `$bg`; the four failures were paid **head-on** instead, by lifting `muted` (and solarized-dark's `text`) in 86de3f5 to clear 4.5 **on `surface_2`** — now 4.55/4.56/4.59/4.61. And the aesthetic move ran a **NEGATIVE** a11y balance: 13 screen-reader names had to be restored by hand. **There was no free ride in either direction.**

### 28. Phase 3 — tests + "You'll see" (lines 334–336)

**Current:** `**Tests touched:** none locked (`grep QGroupBox|gb_margin|gb_pad tests/` = zero). Add a smoke assert that `widgets.section()` returns `(box, lay)` with `accessibleName` set.`
**Replace with:** `**Tests touched:** the grep was right about *locking* — but **`test_workspace_a11y.py:69` was locked in effect** and went red on the migration (13 names). The shipped smoke asserts the **frame** (`section()` returns a QFrame with `.content_layout` / `.title_label`), not a tuple. `test_checked_indicators_carry_a_tick_and_a_dot` also landed (58f7deb).`

**Current:** `**You'll see:** the page becomes a document. 27 borders and 27 fills gone.`
**Replace with:** `**You'll see:** ~~the page becomes a document. 27 borders and 27 fills gone.~~ **What you actually see:** 27 cards with a tracked-caps title inside them, 16px of air, and not one border or fill removed. Build & Deploy is **BUILD TO (FIELD)** *inside a card* / options / air / **ADVANCED** / air / actions.`

### 29. Phase 4 — the goal (line 342)

**Current:** `**Goal:** dark themes get real depth. Light themes keep the one cue that works there.`
**Replace with:**
> **Goal:** ~~dark themes get real depth. Light themes keep the one cue that works there.~~ **SUPERSEDED — the premise measured the wrong pair.** `bg→surface` (1.120) governs nothing: no widget in this app is a bare `$surface` panel on the page. A card sits at `bg→surface_2` = **1.308** in DARK, **stronger than GitHub dark's 1.094** (nord 1.271 · dracula 1.247 · solarized-dark 1.332 · gruvbox-dark 1.303 — every one out-steps the reference). The depth was never missing; neither the fill nor the border was changed (`widgets.py:159-162`, "NOT changed: the fill"). **Only 4c's `surface_3` cap and 4d's collision diagnosis survive this phase.**

### 30. Phase 4a (lines 346–353)

**Current:** `**4a — raise the dark rungs only** (`theme.py:304-305`).`
**Replace with:** `**4a — ❌ REJECTED, and it is now UN-LANDABLE** (`theme.py:307-308`, refs drifted +3).`

**Append immediately after the 4a code block:**
> **Verified by running the real suite with this patch applied:** `test_palette_contrast_invariants` **FAILS** — *"dark: hint text on a groupbox, assert 4.197568137951583 >= 4.5"*. Enumerating past the short-circuit, `muted/surface_2` breaks on **all 5 dark palettes**: dark 4.198 · nord 3.942 · dracula 3.859 · solarized-dark 3.904 · gruvbox-dark 3.877 (all currently 4.55–4.83). Solarized-dark **also** breaks `text/surface_2`: 4.940 → 4.236. This is a **direct revert of Phase 0**, which lifted `muted` in exactly those palettes to clear that floor. **`surface_2` is the card fill and is now load-bearing for accessibility; it is FROZEN at 0.05** absent a second `muted` lift.

**Current:** `Span (bg→surface_3): nord 1.486→**1.947**, dracula 1.472→**1.979**, gruvbox 1.541→**2.054**, solarized-dark 1.553→**2.059**.`
**Append:** `*(Arithmetic verified to three decimals. But `bg→surface_3` is a **synthetic metric**: `surface_3` appears only as a chip fill (`style.py:279`) and the palette-preview card (`palette.py:88`). Nothing stacks bg→surface→surface_2→surface_3, so "the full span" is a number no user ever sees as a span. It cannot justify a change that reds 5 palettes.)*

### 31. Phase 4b — the fence (line 366)

**Current:** `Fence: text/bg 14.77, text/surface 11.91, muted/bg 7.09, muted/surface 5.72, focus/surface 4.57 — all clear.`
**Replace with:** `Fence: text/bg 14.77, text/surface 11.91, muted/bg 7.09, muted/surface 5.72, focus/surface 4.57 — all clear. **⚠ WRITTEN AGAINST THE OLD SUITE — this fence is verbatim the pre-86de3f5 assertion list and it never fences `surface_2`, the only rung that fails.** 86de3f5 added `text/surface_2 >= 4.5` and `muted/surface_2 >= 4.5` (`test_editor_theme.py:104-106`) plus a muted<text ordering assert (`:113`). Re-fenced against those, this DARK measures `muted/surface_2` = **4.198 = RED**. **Any future palette proposal must fence `surface_2` — it is where every hint inside a card lands.** The plan fenced the page and the panel and never fenced the card.`

### 32. Phase 4d — the gruvbox collision (line 382)

**Current:** `**4d — NORD/GRUVBOX field collision.** `nord field #3b4252 -> #272c36` (**not** `#2e3440` — that IS nord's bg, byte-identical). `gruvbox field #3c3836 -> #32302f`.`

**Replace with:**
> **4d — NORD/GRUVBOX field collision. ✅ DIAGNOSIS VALID and still unfixed; the gruvbox VALUE is wrong.** `field == surface_btn` byte-identically in **three** palettes: nord `#3b4252` (`theme.py:80` vs `:81`), gruvbox-dark `#3c3836` (`:181` vs `:182`), **and DARK `#2b3038`** (`:49` vs `:50`) — an input and a button face render as the same hex. `nord field #3b4252 -> #272c36` (**not** `#2e3440` — that IS nord's bg, byte-identical; `#272c36` is safe against bg but **is byte-identical to nord's `log_bg`**, `theme.py:95` — acceptable, both are wells, but say it rather than trip over it). `gruvbox field #3c3836 -> ` **pick anything but `#32302f`** — that **IS** gruvbox-dark's `surface` (`theme.py:180`, "bg0_s"), byte-identical, which makes the input well the same hex as the panel it sits in: a strictly *worse* collision than the one it fixes, and precisely the error this row catches one clause earlier for nord. Not `#282828` either (= bg). **Any `field` proposal must be checked against `bg`, `surface`, `surface_btn` AND `log_bg`.**

### 33. Phase 4 — the new laws (lines 384–405)

**Insert before the test block:**
> **Two of these three are landable TODAY, green on the current palettes, and decoupled from the rejected 4a/4b — move them out of Phase 4 into a standalone "land the missing laws" item:** `test_console_well_stays_recessed_below_the_page` (log_bg < bg in all 7: dark `#181b20` < `#1e2127`; solarized-light `#e4ddc8` < `#eee8d5`) and `test_elevation_ladder_is_a_ladder_not_a_floor` (7/7 distinct; the existing `test_derived_elevation_ladder_is_monotonic` at `test_editor_theme.py:143-147` really is non-strict and would pass a flat floor). **The third is RED on arrival.**

**Append after `test_hover_moves_toward_the_light`:**
> **⚠ THIS TEST IS CORRECT AND FINDS A REAL BUG — and Phase 4 never fixes it.** `hover` is **byte-identical to `surface_btn`** in nord `#3b4252` (`theme.py:80/:92`), dracula `#3a3d4d` (`:104/:116`), solarized-dark `#0b4350` (`:128/:143`) and gruvbox-dark `#3c3836` (`:181/:193`) — i.e. **those four palettes have no button hover feedback at all**. `L(hover) > L(surface_btn)` is False while `pal["dark"]` is True → red on 4 of 7 today. 4b only edits DARK, 4c only LIGHT, 4d only `field`, so nothing in this phase lands it. **Ship the four hover values as their own commit** — with 4a/4b rejected, that commit is the only way this independent bug survives.

### 34. Phase 4 — tests touched (line 405)

**Current:** `**Tests touched:** `test_editor_theme.py` (3 added). Key sets unchanged — values only.`
**Replace with:** `**Tests touched:** ~~`test_editor_theme.py` (3 added). Key sets unchanged — values only.~~ **This was false when written.** `test_editor_theme.py` — **2 landable additions** (console well, ladder-3-distinct), **1 addition that is RED on arrival** (hover, on 4 palettes this phase never touches), and an unavoidable **CONFLICT** with the `surface_2` floors at `:104-106`. This is not a values-only change: it **re-opens Phase 0**.`

### 35. Phase 4c — the `surface_3` cap (line 380) — **KEEP, endorse**

**Append:** `**✅ VERIFIED and the one part of Phase 4 that should land.** `theme.py:308` currently derives `surface_3 = #ffffff` for **both** light palettes (light `#f4f5f7` and solarized-light `#f4eeda` both mix to pure white at t=1.00) — so solarized-light's cream page really does get a pure-white top rung, contradicting `theme.py:22-23`'s own note. At 0.80: `#fdfdfd` and `#fdfcf8` (measured H=48.0°, S=2.0% — the cream survives). Ran the full assertion set with 0.80 applied: both light palettes pass every check and the ladder stays 3-distinct (`#f4eeda`/`#faf7ee`/`#fdfcf8`). Honest limit: LIGHT's `#fdfdfd` is ~1.01:1 against white — it removes the literal hex, not the look.`

### 36. Phase 5 — the radius table (lines 419–421)

**Current:** `| `$radius_sm` | 4px | `::item` (:131), checkbox indicator (:93), `QMenu::item` (:166), chip (:213) |`
**Replace with:** `| `$radius_sm` | 4px | `::item` (**:197**), checkbox indicator (**:128**), `QMenu::item` (**:232**) — the chip (**:279**) is **already** `$radius_sm` |`

**Current:** `| `$radius_lg` | 8px | trees/lists (:129), pane (:136), groupbox (:149), text edits (:160), **both cards** |`
**Replace with:** `| `$radius_lg` | 8px | trees/lists (**:195**), pane (**:202**), text edits (**:226**) — **~~groupbox (:149)~~ DELETE, don't tokenize** (`style.py:214-223` is dead code since 0ecfa75); **"both cards" is one card**: `QFrame[role="card"]` (**:277**) is already `$radius_lg`, and Home's `QFrame#card` (`:256`) is the other — see Phase 6 |`

**Append to the tier block:** `*(All Phase-5 `style.py` line numbers shifted ~+66: 58f7deb inserted the tick/dot rules. **26 declarations** counted with the phase's own `border-[a-z-]*radius` fence — 24 `border-radius` + the 2 tab-top corner variants at `:139` — of which 2 are already tokenized, so **24 migrate**.)*

### 37. Phase 5 — group interiors (line 459)

**Current:** `Group interiors: `gv.setContentsMargins(11, 0, 11, 11)` — **11, not 12**: the groupbox's 1px border sits *outside* the layout, so 1+11 puts content ink at 12, the same x as the title. `top=0` is the real win: the QSS already supplies 23px (margin 12 + border 1 + padding-top 10); Qt's silent default 11 made it 34.`

**Replace with:**
> Group interiors: **OBSOLETE — `widgets.section()` owns them** (`widgets.py:180`, `(16, 12, 16, 16)`; spacing 10 at `:181`, body 8 at `:189`). The 11-not-12 border arithmetic died with the fieldset — there is no ::title column to align to. *(Two of its sub-claims measured true as written — contentsRect.x=1, body ink x=12, contentsRect.y=23 from `gb_margin_top:12px` + border + `gb_pad_top:10px`, and Qt's default 11 giving ink y=34 — but "the same x as the title" was **false the day it was written**: title ink measures **x=16** (`left:10px` + `padding: 0 6px`, `style.py:220-222`) against body ink 12, so alignment needed 15, not 11.)* **What remains for Phase 5:** those 16/12/10/8 are hardcoded ints in `section()` — the strongest argument yet for exporting the grid. Note 10 is **off-grid** (`_GRID` = 4/8/12/16/24), so `setSpacing(10)` needs a design decision, not a mechanical substitution.

### 38. Phase 6 — Home (line 473)

**Current:** `**Home has zero QGroupBoxes.** Phase 3's headline does not touch it.`
**Replace with:**
> **Home has zero QGroupBoxes.** *(Verified: repo-wide there is exactly one `QGroupBox(` string and it is a docstring at `widgets.py:166`. Home never had one; after 0ecfa75 nothing does.)* Phase 3's headline does not touch it — **but the card treatment does.** Phase 3 shipped as the card **KEEP**, which minted a **second** card: Home's rows are `QFrame#card` = `$surface`, radius **10px** (`style.py:256`); every `section()` card is `QFrame[role="card"]` = `$surface_2`, radius **8px** (`style.py:277`). Measured DARK: Home's card `bg→surface` = **1.120**; a section card `bg→surface_2` = **1.308**. **Home now carries the app's weakest and roundest card.** Phase 6 must either fold Home's rows onto `role="card"` or state why the entry rows are deliberately a lower rung. *(Home's `_home_section()` at `shell.py:1534-1538` already ships the bare-overline-label idiom that `section()` encapsulates — do **not** wrap those in a `section()` card; cards-inside-a-card is the box-in-box this phase exists to avoid.)*

### 39. Phase 6 — the vignette (line 512)

**Current:** `Skip the radial vignette variant: surface_3→bg measures ~1.2:1 in the neutrals. Invisible.`
**Replace with:** `Skip the radial vignette variant — **but not for the stated reason: that number is wrong for DARK.** `surface_3→bg` measures **1.205 in LIGHT** and **1.530 in DARK** (1.472–1.553 across the five dark palettes) — 27% above the claim, and *stronger* than the hero gradient this same paragraph calls visible (1.308). A vignette would be plainly visible in dark. **Skip it on design grounds** (a gradient band already carries the light source; two overlapping gradients muddy it), not on a contrast measurement. *(Same wrong-pair family as the elevation headline.)*`

**Keep verbatim (VALID):** `**The gradient is a whisper in the neutrals** (bg→surface_2 is 1.24–1.31 in dark, 1.16 in light)` — **append:** `*(Recomputed exact: DARK 1.308, LIGHT 1.155; dark span 1.247–1.332. Note this hero paragraph measured the **right** pair — `bg→surface_2` — and thereby quietly refutes this plan's own "the fills do nothing" headline.)*`

### 40. Token diff — new keys (line 522)

**Current:** `### New palette keys: **none.**`
**Append after the paragraph:**
> **New QSS *substitution* keys (NOT palette keys), added by 58f7deb and not listed in this diff:** `$check_img` / `$check_img_off` — **generated asset paths, not colours**. `qss()` merges an `art` dict (`style.py:352-355`) alongside `_SCALES`/`_DENSITY`/`pal`; `_CHECK_SVG` (`style.py:30-35`) is tinted per-palette from `pal["accent_fg"]` (checked) and `pal["muted"]` (off) via `_asset()` (`style.py:37-50`) and written to a content-addressed path. The base dicts and `test_palettes_share_one_key_set` stay untouched — the same central-derivation extension point this section endorses. Verified: 7 palettes × 2 densities substitute with zero leftover `$`, every emitted `url()` resolves on disk, tick-on-fill contrast (`accent_fg` vs `accent`, the pair that renders) 3.20–5.90 — all 7 clear the 3:1 non-text floor.

### 41. Token diff — the palette table (lines 528–537)

**Current row:** `| `muted` | `#626974` → `#5d646e` | unchanged | **NORD / DRACULA / SOLARIZED_DARK / GRUVBOX_DARK: lift until `muted/surface_2 ≥ 4.5`** (today 3.87 / 3.91 / 3.91 / 4.07 — sub-AA and untested) |`
**Replace with:** `| `muted` | `#626974` → `#5d646e` — **UNSHIPPED and elective**: `#626974` already measures 4.60 on bg / 5.31 on surface_2; the proposal buys headroom (4.96 / 5.73), it does not fix a failure | unchanged | ✅ **LANDED (86de3f5)** at hexes this table never named: NORD `#9aa3b5`→**`#aab2c1`** (4.61) · DRACULA `#8f95bc`→**`#9ca2c4`** (4.56) · SOLARIZED_DARK `#7f9e9e`→**`#8eaaaa`** (4.55) · GRUVBOX_DARK `#a89984`→**`#b1a390`** (4.59). The "today" figures reproduce exactly: 3.873 / 3.911 / 3.912 / 4.069 |`

**Insert a new row (the table has no `text` row and a `text` lift shipped):**
> | `text` | unchanged | unchanged | **SOLARIZED_DARK `#93a1a1` → `#a2aeae` — LANDED (86de3f5)**. base1 measured **4.216** on its own `surface_2`: the **only** palette whose BODY text was sub-AA on an elevated panel. Lifted **past** its own 4.5 minimum (to 4.94) on purpose — `muted` must clear 4.5 **and** stay dimmer than `text`, and at text's bare minimum there is no headroom for both (`theme.py:130-133` records this; a naive solve ran `muted` to `#ffffff`). All other palettes: `text` unchanged. **This audit of the community palettes checked `muted` and never checked `text`.** |

### 42. Token diff — derived math (lines 539–546)

**Current:** `### Changed derived math (`theme.py:304-305`)` + the two-line block.
**Replace with:**
> ### Changed derived math (`theme.py:307-308` — refs drifted +3)
>
> ```python
> # ❌ DROPPED: out["surface_2"] = _mix(pal["surface"], "#ffffff", 0.10 if dark else 0.55)
> #    The dark rung 0.05 -> 0.10 is unmotivated (its premise measured bg->surface, not bg->surface_2)
> #    AND un-landable: it reds muted/surface_2 on all 5 dark palettes, reverting Phase 0. Measured:
> #    bg->surface_2 is ALREADY 1.308 DARK vs GitHub dark's card at 1.094; 0.10 takes it to 1.530.
> #    The card ships at 0.05 and reads correctly. surface_2 is FROZEN.
> out["surface_3"] = _mix(pal["surface"], "#ffffff", 0.10 if dark else 0.80)   # light 1.00 -> 0.80 ONLY
> ```
> The light change kills pure-`#ffffff` panels (`theme.py:22-23`'s own stated rule) in both light palettes. Stay **relative** — an absolute hex would inject a foreign hue into solarized-light's cream. Honest limit: 0.80 gives LIGHT `#fdfdfd` (~1.01:1 against white — it removes the literal hex, not the look) and solarized-light `#fdfcf8`, which **does** preserve the cream (H=48, S=2%) — the stated reason to stay relative.

### 43. Token diff — the gb keys (line 554)

**Current:** `| `gb_margin_top` / `gb_pad_top` | → `"0px"` / `"0px"` in **both** | Phase 3; keep the keys, zero the values |`
**Replace with:** `| `gb_margin_top` / `gb_pad_top` **+ the `QGroupBox` rules** (`style.py:214-223`) | **DELETE, don't zero** | Phase 3 — SPENT. The card stayed but **QGroupBox did not**: `section()` renders a `QFrame[role="card"]`, and 0ecfa75 finished the migration; zero constructions remain repo-wide, so zeroing the values would change nothing on screen. Delete the rules and the two keys **together** (the `$gb_*` template refs and the keys must go in one commit or `Template.substitute` raises `KeyError`). `test_qss_density_profiles_both_substitute_cleanly` does **not** block this — it asserts only `"$" not in css`. |`

### 44. Token diff — `widgets.py` API (lines 573–596)

**Replace the whole block with:**
> ```python
> # SHIPPED (685ba1a) -- what actually exists. The proposal's spec diverged on nearly every line.
> PROSE_W     = 620   # NOT 400. widgets.py:105. ⚠ its docstring's "~75-85 chars at 13px Segoe UI" is
>                     # WRONG: real-font-DB Segoe UI 13px = 5.84 px/char, so 620 = ~106ch (75-85ch =
>                     # 438-496px). The plan's 400 was the honest measurement. Restate or re-tune.
> SECTION_GAP = 14    # widgets.py:23. NOT in the plan at all. Was 24 (685ba1a) until the reversal.
> # FORM_W  = 860     # NOT BUILT -- still a proposal. shell.py:1436 still hardcodes 860.
>
> class Prose(QLabel):                # PUBLIC, not _Prose
>     """Measure-capped prose. The heightForWidth override is MANDATORY -- but CONDITIONALLY:
>     a raw setMaximumWidth clips ONCE NESTED (QGroupBox and widgets.section() alike); it does
>     NOT clip standalone. Measured at 620: standalone h=68 need=68 ok; nested h=40 need=68
>     CLIPPED; Prose ok in both. calcHfw asks hfw() at the FULL cell width."""
>     # sizeHint also RECOMPUTES height at the cap (widgets.py:133) -- the plan capped width only.
>     # NOT shipped: role="prose", the RichText line-height:140% div, setAccessibleName(text).
>
> def prose(text, width=PROSE_W, *, parent=None): ...        # widgets.py:138
> def section(title, *, parent=None) -> QFrame: ...          # widgets.py:143 -- returns the FRAME,
>                                                            # exposing .content_layout / .title_label
>                                                            # (mirrors disclosure(), widgets.py:273).
>                                                            # NOT tuple[QGroupBox, QVBoxLayout].
> ```
> **Also strike the `QLabel[role="prose"]` row from the roles table** (line 568): the shipped `Prose` sets **no role**, so that selector has **zero users** — either drop the row or ship the role. **`FORM_W` remains genuinely unbuilt** — keep it as a proposal, and pair it with the `shell.py:1438` stretch fix, which is the bug `FORM_W`'s 860 is silently losing to.

### 45. Rejected — the `QGroupBox::title` row (line 623)

**Current:** `| **`QGroupBox::title { font-* }`** | Silently ignored (render-verified: ink identical at 13/600, 11/700+tracking, and 18/700). Colour is `::title`'s only lever. And `left: 0px` is **not** flush — `subControlRect` reports x==0 while the paint path adds +6. |`

**Replace with:** `| **`QGroupBox::title { font-* }`** | ✅ **TRUE, and it is not a rejected tweak — it is the load-bearing reason `widgets.section()` exists.** Silently ignored (render-verified and independently reproduced: glyph ink 168px / span 68 identical at baseline, 13/600, 11/700+tracking and 18/700, while the same declarations on the **widget** give 192/312px — the null is Qt's behaviour, not an offscreen artifact). Colour is `::title`'s only lever, which is why the title could never be given presence while Qt drew it — **quoted verbatim in the shipped docstring at `widgets.py:150-153`. See the diagnosis; this row is a pointer, not a refutation.** `left: 0px` is **not** flush — `subControlRect` reports x==0 while the paint adds +6 (confirmed: ink starts at x=8) — **keep this**: it refutes the fallback QSS still proposed at Phase 3. |`

### 46. Rejected — ChoiceCard (line 615)

**Current (tail):** `Delete the container first; then a card has ground to stand on.`
**Replace with:** `**The container STAYS** (`widgets.section()`), so the rejection now rests on its own measurements rather than on a deletion that never happened: a nested ChoiceCard is a **real card-in-card**, and its states do not survive the nesting — hover measures **1.000:1** against `surface_2` in DARK, and the selected fill **1.01–1.12 in 4 of 7** (nord 1.013 · sol-dark 1.067 · dark 1.077 · gruvbox 1.115 — reproduced to the digit). **A nested choice must be delineated by something other than fill.** *(The box-in-box clause is stronger now than when written.)*`

### 47. Rejected — the measure cap (line 624)

**Keep the row verbatim** — it is load-bearing and its mechanism reproduced (real platform: 150 families, Segoe UI present, **5.840 px/char**; offscreen: `QFontDatabase.families() == 0`, every glyph 13.000px → **2.18× inflation**, inside the claimed 2–3×). **Append one sentence:**
> *(This row is also what killed the "NB: no left/right padding" defence at `style.py:218` — `widgets.py:155-158` reuses its exact 642px-vs-~1080px argument as the reason the card's 16px h-padding was restored. **A cap did ship — `PROSE_W = 620` — but on a different rationale: chars-per-line readability, not an h-scroll emergency.** There was no emergency. See the `widgets.py` API note: the shipped 620's stated chars-per-line justification is arithmetically wrong; this plan's 400 was the real measurement.)*

### 48. Rejected — `tabular()` (line 616)

**Append to the row:** `**Already in the tree at `widgets.py:321-329` with zero callers** — it calls `font.setFeature(QFont.Tag("tnum"), 1)`, i.e. dead code implementing the refuted idea. Delete it in the Phase 5 cleanup rather than leaving a proven no-op for someone to adopt. *(Re-verified from the font FILE, so the offscreen caveat does not apply: `segoeui.ttf` hmtx gives all ten of `zero`–`nine` advance 1104/2048; resolving GSUB through the ExtensionSubst indirection, `tnum` covers 200 glyphs, **zero** latin digits; `pnum` covers 20, **including all ten**.)*

### 49. Rejected — `text_subtle` (line 619)

**Current:** `Fails 4.5:1 on `surface_2` in **all 7** palettes (2.55–3.20).`
**Replace with:** `Fails 4.5:1 on `surface_2` in **all 7** palettes (**2.87–3.20**, recomputed after the Phase-0 `muted` lift — `theme.py:310` derives `text_subtle = _mix(muted, bg, 0.28)`, so the AA fix raised this tier too; sol-dark 2.868 · dracula 2.949 · gruvbox 2.955 · nord 3.015 · dark 3.036 · sol-light 3.132 · light 3.197. Still fails everywhere).`

### 50. Rejected — `$trim` / MIST wording (lines 617–618)

**Current:** `| **`$trim` identity token / a gold rule** | The key exists in all 8 palettes and is referenced by **zero** QSS rules.`
**Replace with:** `| **`$trim` identity token / a gold rule** | *(Read as the proposal's end-state, which is this table's register: `theme.py` ships **7** palettes today and **no** palette has a `trim` key.)* The proposal would add `$trim` to every palette (7 today; 8 if MIST lands) and reference it from **zero** QSS rules.`

**MIST row (line 618) — append:** `*(**MIST does not exist in `theme.py`** — `THEMES` at `:203-211` ships 7. "the 8th palette" is the proposal's arithmetic, not a fact about the tree. The row's verdict is confirmed: `theme.py:312` really is `out["info"] = pal["accent"]`, and `info == accent` in all 7 — "one hue spent once" fails on arrival. And **finding B strengthens this row**: if the fill was always fine and the real defects were the caption, the title and the padding, a recolour fixes none of them.)*

### 51. Open question 1 (line 635)

**Current:** `**1. Do we ship Phase 3 (kill all 27 QGroupBoxes)?**` … through `…the risk is earned.`

**Replace with:**
> **1. Do we ship Phase 3 (kill all 27 QGroupBoxes)? — ✅ ANSWERED: NO. The card stays.**
> The gate did its job exactly as designed: Phase 1 was screenshotted first, and the verdict came back *"the cards were nice logical section indicators, they just looked ugly."* So the box was never the problem — **the caption on the border, the title's lack of presence, and the missing padding were.** All 27 sites migrated to `widgets.section()` — a titled QFrame `role="card"` — across the same 7 files; QGroupBox is now constructed nowhere in the workspace. **What this cost the plan:** "the one change that proves it" was the wrong change, and its stated justification ("borders are noise") was never the live defect.
> **The law below was obeyed and should be quoted as a precedent, not deleted:** *"a 27-site refactor across 7 files in a 16,925-line codebase is a long-lived branch, and any partial landing is worse than today's consistent dull."* The 27 sites really were exactly 7 files, and the rollout ran **3-as-a-spike (685ba1a) then 24-in-one-pass (0ecfa75)** precisely so no mixed state ever shipped. *(One thing the law over-predicted: because the card kept the boxed look, a half-migrated page would have read as consistent anyway. The real serialization pressure was the a11y sweep.)*

### 52. Open question 2 (line 638)

**Current:** `The vision says one lifted surface per screen. Phase 1 ships **none** — the crumb-row Deploy is the only accent and the page is flat type. That may be exactly right (a form's focal point is its verb), but it's a different design from "one lifted surface" and you should own the difference consciously.`

**Replace with:**
> **STILL OPEN — and the reversal INVERTED it.** The question was posed against a page whose six boxes were already uniformly `$surface_2`; Phase 3 was to have made the lift scarce, and Phase 3 was overturned. So the mechanism is gone: `style.py:277` fills **every** `role="card"` with `$surface_2`, and Build & Deploy builds **six** of them (`builddoc.py:121, 174, 191, 209, 231, 258`). Measured `bg→surface_2` = **1.308** in DARK — a real, visible step (GitHub dark's card is 1.094). The page is not rudderless; it is *uniformly* lit, **and a lamp that is on every object is not a lamp**. The vision's "one lifted surface per screen" is now violated six ways over. **The question is no longer "what do we light" but "what do we light MORE" — and the card fill can no longer be the answer, because it is the baseline.**

**Recommendation (same line) — append:** `**HALF-SHIPPED and cheaper than when written:** `role="card"` landed (`style.py:277`); only the stripe remains. Numbers re-verified against the shipped palettes — accent on `surface_2`: **NORD 2.44 · SOL-DARK 3.06 · SOL-LIGHT 3.44 · DARK 3.85 · LIGHT 4.38 · GRUVBOX 4.48 · DRACULA 4.73**. The 4px stripe is not speculative: `style.py:288-295` already ships `border-left: 4px solid` on `QLabel[role="banner"]` (keyed to verdict state). Reuse that proven idiom, accent-keyed, on **one** card per screen — it is now the *only* remaining way to rank cards against each other. **SUPERSEDED in this line:** *"applied to one element per screen and nothing else"* — `section()` now applies `role="card"` to all 27. That is the precise sentence the user's verdict overturned.`

### 53. Open question 3 (line 641)

**Current:** `**Recommendation: ship it after Phase 4, as a *choice*, never as the default, and never billed as the fix.**`
**Replace with:** `**Recommendation: ship it after the hierarchy work lands, as a *choice*, never as the default, and never billed as the fix.** *(Re-anchored: the phase numbering no longer maps cleanly now that Phase 3 was answered by a reversal rather than executed. The orthogonality claim is **strengthened** by the reversal: the three things that were actually ugly — `widgets.py:149-158`, caption on the border, a title with no presence, no horizontal padding — are all **structural**, and a navy/gold repaint fixes none of them. MIST remains a flavour; the reversal is the proof. NB "theme.py's 8th palette" means the 8th that **would** land there — `THEMES` at `:203-211` ships 7.)*`

### 54. Open question 5 (line 647)

**Current:** `**Recommendation: keep them, and make DARK the canonical hand-tuned target.** Phase 4a's approach — raise *our* derived rungs, leave their canonical hexes alone — gets the community themes 90% of the benefit for free. The only edits they need are the `muted` lift (an AA fix they need regardless) and the two `field` collisions.`

**Replace with:**
> **Recommendation: keep them — but NOT because they are free.** *(The Phase-4a clause is struck: 4a is rejected, and its premise died with the elevation headline.)* Phase 0 proved the tax: **4 of 7 needed hand edits (5 hex values), and SOLARIZED_DARK needed two** — `muted` in NORD (`theme.py:83`), DRACULA (`:107`), SOLARIZED_DARK (`:134`), GRUVBOX_DARK (`:184`), **plus SOLARIZED_DARK's body `text`** (`:133`, 4.22 → 4.94 on `surface_2`), the only palette whose body text was sub-AA on an elevated panel. A muted-only solve was arithmetically impossible there: at text's bare minimum there is no headroom for a dimmer tier, and the solver ran `muted` to `#ffffff` (`theme.py:130-133`). That trap is now fenced by an ordering assertion (`test_editor_theme.py:113`).
> **The surviving argument: this was a one-time AA debt, now retired and permanently fenced.** `test_editor_theme.py:109-110` assert `text` and `muted` ≥ 4.5 on `surface_2` for *every* palette; `:113` pins the ordering; every palette clears (muted on `surface_2`: DRACULA 4.56 · SOL-DARK 4.55 · GRUVBOX 4.59 · NORD 4.61 · DARK 4.83 · SOL-LIGHT 5.17 · LIGHT 5.31). Any future palette is caught at test time, not in a screenshot. **Keeping them is cheaper now than when this question was written — the bill is paid. Still owed: the `field` collisions** (`field == surface_btn` byte-identically in NORD, GRUVBOX_DARK **and DARK**).

**Also (same line):** `— and that math is exactly what bleaches the chroma out of the panels.`
**Replace with:** `— and that math **does** measurably desaturate the derived rungs (HLS saturation `surface → surface_2` falls in 6 of 7; worst SOLARIZED_DARK **0.808 → 0.596**; only solarized-light rises, +0.004). **That is a chroma observation, not the reason the panels didn't read** — `bg → surface_2` measures 1.308 in DARK, a *stronger* step than GitHub dark's 1.094. The fill was always fine and was never changed. If the derived chroma is ever worth reclaiming, it is a polish item on its own merits, not a hierarchy fix.`

---

## VISION.md

**WORKSHOP survives — the name, the lamp test, LAW II and LAW III intact.** What dies is every sentence that spends the metaphor on *containment*. VISION.md's header declares it "Kept unedited as the record of the reasoning," so it gets a **header amendment + inline superseded markers**, not a silent rewrite; the constructive re-spend lives in PLAN.md (edit #5).

### 1. The header (lines 1–7)

**Current:**
```
<!--
The art direction synthesized across the 10 lenses, 2026-07-15. Read PLAN.md for the work.
NB: this document is superseded on ONE point by CRITIC.md -- it bills "kill the QGroupBox"
as the highest-leverage change while also conceding the redesign is unjudgeable until the
style.py:126 selector bug is fixed. The critic won that argument; the plan gates Phase 3
behind a re-screenshot. Kept unedited as the record of the reasoning.
-->
```
**Replace with:**
```
<!--
The art direction synthesized across the 10 lenses, 2026-07-15. Read PLAN.md for the work.

SUPERSEDED ON ITS HEADLINE, 2026-07-15 (post-build). Kept as the record of the reasoning.
Two supersessions, in order:

1. SEQUENCING (CRITIC.md): this doc bills "kill the QGroupBox" as the highest-leverage change
   while conceding the redesign is unjudgeable until the style.py:126 selector bug is fixed.
   The critic won; the plan gated section 4 behind a re-screenshot. The gate RAN (86de3f5).

2. THE VERDICT (the user, on a built artifact): section 4 was built (685ba1a -- borderless
   sections, SECTION_GAP=24) and OVERRULED -- "the cards were nice logical section indicators,
   they just looked ugly." The card STAYS (881e468); all 27 boxes became widgets.section(),
   a QFrame role="card" with the title INSIDE as a role="overline" label (0ecfa75).

WHY THIS DOC WAS WRONG, precisely: section 1 measured the wrong pair. It computes the RUNGS
(bg->surface 1.120, surface->surface_2 1.168) but a CARD SITS ON THE PAGE, and bg->surface_2
measures 1.308 in DARK -- STRONGER than GitHub dark's card (#0d1117 vs #161b22 = 1.094).
The fill was always fine. Neither the fill nor the border was changed. What was ugly:
(a) the caption sat ON the border (the Win32 fieldset idiom), breaking the stroke;
(b) the title had no presence ($muted at the same 13px as the body it labelled) -- and that is
    UNFIXABLE while Qt draws it: QSS silently ignores font-* on QGroupBox::title. THIS, not
    "borders are noise", is the real reason the box had to become a widget;
(c) no horizontal padding, defended by an h-scroll bug that never existed at the claimed
    magnitude (the offscreen QPA inflates advances 2-3x).
The live direction is PLAN.md's rewritten WORKSHOP. Sections 2, 3-I and 4 are marked inline.
-->
```

### 2. §1 THE DIAGNOSIS (line 15)

**Current:** `The elevation ladder steps 1.04–1.17:1 (WCAG's *non-text* floor is 3:1) — so the fills do nothing and the hairline does everything, across 20 widget classes at 9 radii.`
**Replace with:** `The elevation ladder steps 1.04–1.17:1 (WCAG's *non-text* floor is 3:1) — so the fills do nothing and the hairline does everything, across 20 widget classes at 9 radii. **[FALSE — WRONG PAIR. The range is exact (min 1.046 light `surface→surface_2`, max 1.168 dark), and the class/radius receipt is exact. But those are the RUNGS. A card sits on the PAGE: `bg→surface_2` = 1.308 DARK / 1.155 LIGHT, vs GitHub dark's card at 1.094. The fills were never the defect. And 3:1 is a category error: WCAG 1.4.11 governs component boundaries and state indicators, not surface fills — no shipping design system clears it page-to-card.]**`

**Everything else in §1 survives verbatim and is re-verified at HEAD** — `role="h1"` set by nothing, the four zero-call-site helpers, `selection_bg`, the dead space tokens, `setObjectName("accent")` zero in builddoc/coopdoc, `font-weight: 500` → Regular. *(Add inline after "every QGroupBox interior silently runs Qt's default 11/6": **[moot since 0ecfa75 — QGroupBox is constructed nowhere; `widgets.section()` hard-codes 16/12/16/16 and `SECTION_GAP = 14`, still not tokenized. The finding holds; the example moved.]**)*

### 3. §2 THE NAMED DIRECTION (lines 21–27)

**Insert immediately under the `## 2.` heading:**
> **⚠ SUPERSEDED IN PART — the containment half only. The name (WORKSHOP), the lamp test, and the type prescription survive; every "no container" sentence below was built, shown, and overruled. The live text is PLAN.md's rewritten WORKSHOP: the section is a shallow TRAY, and the metaphor is re-spent on RANK, not containment.**

**Line 21:** `A dark table. Tools laid flat on it, nothing in a case.` → append `**[SUPERSEDED: the case stays. `widgets.section()` = QFrame `role="card"`, `style.py:277`. This was a legitimate PRESCRIPTION when written — all 27 boxes were live — overturned by the user's verdict on a built artifact, not by being wrong on the facts.]**`

**Line 23:** `Sections are not containers` → append `**[FALSE at HEAD: sections ARE containers — a section is a logical indicator and the user reads it as one (`widgets.py:144`: "A titled CARD — the QGroupBox replacement… The card stays."). What a section is not, is a **fieldset**. The surviving clause of this very sentence is "no floating caption cutting a line" — the fieldset complaint — which landed via the OPPOSITE mechanism: the title moved INSIDE the box (`widgets.py:182`), not the box away.]**`

**Line 23:** `both of which abolished the titled box a decade ago` → `**[STRIKE — do not resurrect. Cited as authority for a prescription the user overruled, and arithmetically impossible: Zed shipped 2023, Linear founded 2019. If a reference is wanted, cite these for TYPOGRAPHY — a quiet overline title over dense technical rows — not for abolishing the container.]** both of which abolished the titled box a decade ago`

**Line 23:** `A section is a small tracked-caps muted label` → append `**[✅ SHIPPED VERBATIM: `widgets.py:182` `role_label(title.upper(), "overline")` → `style.py:286` 11px/600/+1px/`$muted`. And this clause is what FORCED the widget rewrite: QSS silently ignores `font-*` on `QGroupBox::title`, so the doc's own type spec was deliverable ONLY by making the box a QFrame. Divergence: it sits inside a card, and `setAccessibleName(title)` announces the non-shouty form.]**`

**Line 23:** `then a generous gap before the next label` → append `**[ATTENUATED: `SECTION_GAP = 14` (`widgets.py:23`), halved from 24 once the card came back — the card's own 16px padding does the separating; the gap is a seam, not the grouping mechanism. 14 must still clearly exceed the 8px in-card row gap.]**`

**Line 25:** `On any screen there is **one** lifted surface, **one** accent object, **one** 20px title.` → `On any screen there is ~~**one** lifted surface,~~ **[STRIKE — unachievable: `importdoc.py` alone builds 10 `section()` cards, each `$surface_2`. Elevation is now the section GRAMMAR, not a scarce rank.]** **one** accent object, **one** 20px title.`

### 4. §3 THE THREE LAWS — LAW I (line 31), the exact new wording

**Current:**
> **I. A border must earn its existence.** Group by space and type first. A stroke is for things you can click into or type into — a button, an input, a tab, a focus ring. A *container* is not a stroke; it is a label and a gap. If you removed the border and the grouping still reads, the border was noise. It usually does, once the gap is right.

**Replace with:**
> **I. A border must earn its existence.** *(The test survives; its answer for the container was overturned. Original text in the record note below.)* A stroke is for things you can click into or type into — a button, an input, a tab, a focus ring — **and for a container, unconditionally, in every palette**. **A container is a label, a gap, a fill, a padding — and a stroke** (`style.py:277`, one unconditional rule; DARK's fill leads at 1.308 vs the border's 1.182, LIGHT's border leads at 1.399 vs the fill's 1.155). **What it must never be is a stroke *cut by its own caption*, a title with no presence, and content run to the edge: that is the fieldset, and that is what was ugly.** If you removed the border and the grouping still reads, the border was noise — **the card's border is not noise: measured, it is the only thing that makes a LIGHT card visible at all.** **Removing a container is a hypothesis about how a page reads, and it is testable only by the user.**
>
> **[SUPERSEDED — the record.** This law originally ended: *"A container is not a stroke; it is a label and a gap. If you removed the border and the grouping still reads, the border was noise. **It usually does, once the gap is right.**"* The test was **run**, at this doc's own 24px (`685ba1a`, `SECTION_GAP = 24`, `section()` "no fill, no frame") — so it cannot retreat to "the gap wasn't right" — and it returned a negative. A test that yields a negative worked; the *prediction* attached to it ("it usually does") is what the one experiment falsified. Half the law even survived the reversal: the card kept the label and the gap. Only the exclusive clause fell.**]**

**LAW II (line 33):** `One accent object, one lifted surface, one page title.` → `One accent object, ~~one lifted surface,~~ **[STRUCK — see §2]** one page title.` *(The rest of LAW II is untouched and still unpaid at HEAD.)*

**LAW III (line 35):** **untouched — still true, still unshipped.** `builddoc.py:131` is verbatim `QRadioButton(f"Test slot {tid} - quick + reversible; play via F6 -> Warp")`. The vehicle exists (`widgets.py:105-140`) with **one** call site app-wide (`coopdoc.py:72`, an intro paragraph, not a caption under a control).

### 5. §4 THE SINGLE HIGHEST-LEVERAGE CHANGE (lines 39–48)

**Insert under the heading:**
> **⚠ THIS SECTION IS THE ONE THE USER OVERRULED. Kept whole as the record.** *"Kill the QGroupBox. All 27 of them, in one pass"* was built (685ba1a: Co-op, borderless, 24px gaps), shown, and rejected: **the card stays.** The QGroupBox did die — but as a **Qt class**, not as a look: `widgets.section()` renders a QFrame `role="card"` with the title inside. **The mechanism shipped 27/27; the aesthetic premise did not.** Line-by-line below.

**Line 41:** `a token that already exists and is already unused` → `**[FALSE when written:** `role="overline"` was already in live use on the Home page (`shell.py:1536`, `_home_section`). Which is a *good* thing: `section()` adopting it makes the card title and the Home header **one register**.**]**`

**Line 41:** `a **24px** gap above and ~8 below, content flush at one left edge, **no fill and no frame**` → append `**[SHIPPED then REVERSED: 14px (`widgets.py:23`), 16px h-padding, a fill AND a frame.]**`

**Line 41:** `Pay the whitespace or don't ship it` → append `**[RE-SCOPED, not repealed: priced for a borderless page where the gap alone carried the grouping. The card carries its own boundary, so the gap only has to beat the 8px in-card row spacing.]**`

**Line 47 (the `style.py:126` bullet):** prepend `**[✅ SHIPPED 86de3f5 — and this was the doc's most durable instruction: "you cannot judge any redesign until it's gone" was right. The fix lives at `style.py:188` / `:192`, guarded by `test_qss_has_no_malformed_subcontrol_selectors`.]** `

**Line 48 (the AA bullet):** append
> **[✅ THE BUG WAS REAL — THE FREE RIDE WAS NOT TAKEN, AND THE LEDGER RAN NEGATIVE. Every fact here was true when written: `muted` on `surface_2` measured 3.873/3.911/3.912/4.069 and passed on `bg` in all 7, on a rung the suite explicitly did not test. But the fill was never deleted, so no caption landed on `$bg`. 86de3f5 paid it **head-on** instead — lifting `muted` in all four (now 4.55–4.61) **and** solarized-dark's `text` (4.22 → 4.94) — and added the missing assertions (`test_editor_theme.py:109-110`, `:113`). Meanwhile the aesthetic move **cost** accessibility: Qt derives an unnamed control's screen-reader name from its enclosing QGroupBox TITLE, so removing the boxes silently killed **13 names**. "The aesthetic move is the accessibility fix" is exactly backwards.]**

### 6. §5 WHAT NOT TO DO (line 60)

**Current (tail):** `Delete the container first; then the card has ground to stand on.`
**Replace with:** `**The container STAYS** (`widgets.section()`), so this rejection rests on its own measurements, not on a deletion that never happened: a nested ChoiceCard is a real card-in-card, hover measures **1.000:1** against `surface_2` in DARK, and the selected fill **1.01–1.12 in 4 of 7**. A nested choice must be delineated by something other than fill.`

**Line 56** (`Don't chase tone-only elevation`) — **untouched and VINDICATED**: LIGHT `surface_3` = `#ffffff`, rungs 1.046/1.043, reproduced exactly. Note it does **not** commit the wrong-pair error: it says a fill cannot carry a **borderless** card in LIGHT, which is a different and correct claim. **Add:** `*(The card was kept and it kept its 1px border — this line is why.)*` — and change the tail `That asymmetry is why Law I says *space and type*, not *tone*.` → `That asymmetry is why a container may **keep its stroke** — and why no container may rely on fill **alone**. The card ships as one unconditional rule (`style.py:277`) and lets each mode take the reading it can.`

**Line 61** (`tabular()` no-op) — **untouched and VINDICATED. Add:** `*(Already in the tree at `widgets.py:321` with zero callers — delete it as hygiene, don't adopt it.)*`

**Line 63 (the meta-law)** — **untouched. It is the doc's best paragraph and every number in the audit obeyed it.**

---

## README.md

### 1. The headline (lines 23–38)

**Current:** `**The screenshot is a bug, not a design failure.** [`style.py:126`](../../ff9mapkit/ff9mapkit/workspace/style.py#L126) writes the pseudo-class before the pseudo-element:`

**Replace with:** `**The screenshot was a bug, not a design failure — ✅ FIXED in Phase 0 (`86de3f5`).** [`style.py`](../../ff9mapkit/ff9mapkit/workspace/style.py#L188) wrote the pseudo-class before the pseudo-element:`

**Current:** `Reorder to `::indicator:focus`. One line.`
**Replace with:** `Reordered to `::indicator:focus` — now [`style.py:188`](../../ff9mapkit/ff9mapkit/workspace/style.py#L188), plus a `:checked:focus` ring at [`:192`](../../ff9mapkit/ff9mapkit/workspace/style.py#L192) and the law in a comment at `:181`. The a11y test greps selector strings and passed throughout; the new guard is `test_qss_has_no_malformed_subcontrol_selectors` ([`test_workspace_style.py:129`](../../ff9mapkit/tests/test_workspace_style.py#L129)), which **parses** rather than greps. `style.py:126` is now a bare `}`.`

### 2. The before/after table (lines 40–44)

**Current:** `The same panel, one selector reordered, **nothing else changed**:`
**Replace with:**
> The same panel, one selector reordered, **nothing else changed** — *⚠ but both PNGs were **re-rendered on today's code**: `shot_builddeploy.py` imports `BuildDoc` live and only re-injects the bug, so both shots show the current `section()` card (overline title `BUILD TO (FIELD)` inside the frame, with padding), **not** the original fieldset with the caption straddling the border. The "before" is a counterfactual (today's card + the old bug), not the user's screenshot. Kept because it stays runnable; do not read it as history.*

**Line 50–52:** `(It is also *sub-AA as text in 6 of 7 palettes* — the aesthetic move and the accessibility fix are the same move.)`
**Replace with:** `(It is also **sub-AA as text on `surface_2` in 6 of 7 palettes** — only DRACULA 4.73 clears: NORD 2.44 · SOL-DARK 3.06 · SOL-LIGHT 3.44 · DARK 3.85 · LIGHT 4.38 · GRUVBOX 4.48. **Still unfixed at HEAD and still worth doing** — and because the card stayed, those captions still land on `$surface_2`, so the fix is the **role change** (`accent` → `$muted`/`$text`), not the fill deletion this doc assumed would rescue it. ~~the aesthetic move and the accessibility fix are the same move~~ — that framing did not survive: see "Two live bugs".)`

### 3. The gate paragraph (lines 46–48)

**Current:**
> **Nobody in the dossier looked at the panel without those rects** — the vision's headline ("kill all 27 QGroupBoxes") is a 27-site refactor across 7 files justified by *this* image. So the plan's order is: fix the line, re-screenshot, *then* decide whether the boxes were ever the problem.

**Replace with:**
> **Nobody in the dossier looked at the panel without those rects** — the vision's headline ("kill all 27 QGroupBoxes") was a 27-site refactor across 7 files justified by *this* image. So the plan gated it: fix the line, re-screenshot, *then* decide whether the boxes were ever the problem. **That sequence ran, and the answer was no.** With the rects gone, the user's verdict was that the cards were good logical section indicators that merely *looked ugly* — so the box was **kept** and its *presentation* fixed instead (`widgets.py:144-158`: the caption sat on the border; the title had no presence; there was no horizontal padding). The QGroupBox died as a **Qt class**, not as a look: all 27 are now `widgets.section()`, a QFrame `role="card"`. **The gate is the reusable lesson: a 27-site refactor was proposed, gated on one screenshot, and the screenshot overturned it.**

### 4. The diagnosis (lines 54–59) — **KEEP; add one marker**

**Append to the paragraph:**
> *(Re-verified at HEAD, every clause still literally true — `role="h1"` set by nothing, four zero-call-site helpers, `space_1/3/4/6` dead, `font-weight: 500` → Regular. **Partly discharged:** `section()` spends the `overline` role (`style.py:286`) on all 27 cards. The sting stays, because it is still true of everything else: every mechanism that could rank things was built, tokenized, tested — and never spent. **The card round spent exactly one of them.**)*

### 5. The harness warning (lines 69–86) — **KEEP VERBATIM; one repoint**

**Current:** `and the padding amputation at `style.py:152-153` is defended by a bug that may never have been real at that magnitude.`
**Replace with:** `and the padding amputation at **`style.py:218`** (was `:152-153`) is defended by a bug that was never real at that magnitude — **that finding is what restored the card's 16px h-padding** (`widgets.py:155-158`, `:180`, reusing this exact 642px-vs-~1080px argument). The comment now annotates a **dead rule**: nothing constructs a QGroupBox, so `style.py:214-223` should be deleted.`

*The rest of this section is the single most load-bearing paragraph in the README. Every number in the audit obeyed it. Do not touch it.*

### 6. Two live bugs (lines 88–95)

**Current:**
> ## Two live bugs found en route
>
> Both predate this round and neither is caught by the suite:
>
> 1. **`style.py:126`** — the unconditional radio/checkbox border above; radios have never had a focus ring.
> 2. **`muted` on `surface_2` is sub-AA today** — 3.87–4.07 in NORD / DRACULA / SOLARIZED-DARK / GRUVBOX. Uncaught because the contrast test only ever checks `bg` and `surface`. Any caption placed inside a QGroupBox lands on this untested surface, so **the assertion ships before the captions do** (Phase 0).

**Replace with:**
> ## Two live bugs found en route — ✅ **both fixed in Phase 0 (`86de3f5`)**
>
> Both predated this round and **neither was caught by the suite; both now are.**
>
> 1. **The unconditional radio/checkbox border** — `:focus::indicator` degraded to an unconditional `QRadioButton, QCheckBox { border: 1px solid $focus }`; radios had **no focus ring at all**. Fixed at `style.py:188` (+ a `:checked:focus` ring at `:192`); guarded by `test_qss_has_no_malformed_subcontrol_selectors` (`test_workspace_style.py:129`), which parses rather than greps.
> 2. **`muted` on `surface_2` was sub-AA** — 3.87–4.07 in NORD / DRACULA / SOLARIZED-DARK / GRUVBOX (reproduced exactly: 3.873 / 3.911 / 3.912 / 4.069), uncaught because the contrast test only checked `bg` and `surface`. All four lifted — now **4.61 / 4.56 / 4.55 / 4.59**. **SOLARIZED_DARK also needed its body `text` lifted** (4.22 → 4.94): the only palette whose body text was sub-AA on an elevated panel, and a muted-only solve there ran `muted` to `#ffffff`. The assertions shipped with the fix: `test_editor_theme.py:109-110` (text + muted on `surface_2`, every palette) and `:113` (**muted must stay dimmer than text** — an ordering invariant the plan never foresaw; two contrast floors alone do not pin the ramp). **Note the framing that did not survive:** "delete the fill and every caption lands on `$bg`" — the fill was never deleted, the debt was paid head-on, and the migration ran a *negative* a11y balance (13 screen-reader names). 33/33 tests pass.

---

## What the plan MISSED entirely

Five things were learned **by building** and appear in none of the three docs. Add them.

### A. The Qt groupbox-title a11y derivation (13 names) → **PLAN.md Phase 3** (new bolded block after the `section()` factory) **+ a one-liner in README's "Two live bugs" neighbourhood**

> **THE LANDMINE: removing a QGroupBox silently strips its children's screen-reader names.**
> Qt derives an **unnamed** control's accessible name from its enclosing QGroupBox **TITLE** (`QAccessibleWidget` → `buddyString`, which reads `groupbox->title()` — **not** `accessibleName()`). A card has no title for Qt to find, so every control that was leaning on the box goes **silent**. **13 did**, across Models / Import / Build; `test_workspace_a11y.py:69` (`test_every_visible_actionable_control_has_a_screen_reader_name`) caught them.
> `setAccessibleName` on the frame does **not** restore them — **and this kills the plan's own drop-in recipe too**: a titleless `QGroupBox` + `setAccessibleName` strips descendant names *identically* to the card (probe: descendant name `''` for both; `setBuddy` restores it). Each site needs `setBuddy(visible_label)`, or `setAccessibleName` where no visible label exists (`coopdoc.py:129`, `importdoc.py:94`, `modelsdoc.py:360`, `builddoc.py:73,145`).
> **Strike the word "mechanical" from Phase 3 (`PLAN.md:286`) and from CRITIC.md:59. The migration is not mechanical.** *(What the titleless-QGroupBox recipe DID preserve, and the card does not, is the accessible **ROLE**: `Role.Grouping` vs the QFrame's `Role.Border`. The plan's stated evidence — "verified: QAccessible reports the name" — was non-probative: all three recipes report the frame's own name. The discriminator was the role, which the plan never measured, and the descendant names, which it never checked.)*

### B. The universal-QWidget-background bug → **PLAN.md Phase 3** (in the factory note, edit #22) **+ a pointer from the Rejected scrollbar row**

> **The content host must be a LAYOUT, never a wrapper QWidget.** The stylesheet opens with a universal `QWidget { background-color: $bg; }` (`style.py:81`). A bare `QWidget` used as a card's content host therefore paints the **PAGE** colour on top of the card's fill — a visible darker rectangle in every card. `section()` uses `body_lay = QVBoxLayout(); v.addLayout(body_lay)` (`widgets.py:186-192`) for exactly this reason. **It is invisible on a borderless section (bg on bg) and only surfaces once the card has a fill** — which is why the plan's own borderless spec could not have caught it.
> *(Add to `PLAN.md:627`, the `background: transparent` on QScrollBar row: this same universal rule bit the `section()` build from the other side — `widgets.py:172-176`. **It is the tree's most consequential single QSS line and deserves to be findable from here.**)*

### C. The `accent_fg == bg` probe trap → **PLAN.md, "The measurement caution" (line 33)** and **README's harness warning**

> **A further trap, found while shipping: an ink-count probe can return a FALSE GREEN.** In **DRACULA** and **GRUVBOX_DARK**, `accent_fg` **equals** `bg`, so a naive "count non-background pixels over the widget" check counts the **page background** as indicator ink and passes. Any probe that asserts "the indicator drew something" must compare against the *specific* expected colour, not against "not the background" — and must be run in all 7 palettes, because the collision exists in only 2. *(Generalises the harness rule: colour measurements are trustworthy offscreen, but a colour **probe** is only as good as its reference pixel.)*

### D. The Prose clip is CONDITIONAL → **PLAN.md Phase 1 landmine (edit #17) + the token-diff docstring (edit #44)**

> The plan states the clip unconditionally. It is not: a raw `setMaximumWidth` on a wrapped QLabel **does not clip standalone** (620 cap: `h=68 need=68 ok`) and **does clip once nested** — inside a QGroupBox **and** inside the new `section()` alike (`h=40 need=68`). The subclass is justified; the phrasing was not. The distinction matters because it tells you *when* you need `Prose` (any nested caption — which is all of them) and stops the next reader dismissing the whole finding when a standalone probe passes.

### E. Two smaller ones — **PLAN.md**

> - **`PROSE_W`'s shipped justification is arithmetically false.** `widgets.py:105` defends 620 as "~75-85 chars at 13px Segoe UI". At a **real** font DB, Segoe UI 13px measures 5.840 px/char → 620 = **~106 chars**; 75-85ch is 438-496px. The plan's `PROSE_W = 400` (= 68.5ch) was the honest number. Shipping 620 may still be right (400 is narrow for a settings pane) — but fix the receipt. *(Goes in the token diff, edit #44.)*
> - **`section()`'s interior is off-grid.** `widgets.py:181` `setSpacing(10)`; `_GRID` is 4/8/12/16/24. Phase 5's "export the grid" cannot mechanically substitute this one — it needs a design decision. *(Goes in Phase 5, edit #37.)*

---

## Still true, do not touch

These survived audit intact. A future rewrite must leave them alone.

**PLAN.md**
- **The whole "measurement caution" paragraph (`:33`)** and README's harness warning — colour is trustworthy offscreen, width is fiction, `skipif "Segoe UI" not in QFontDatabase.families()`. Every number in this audit obeyed it, and it is what restored the card's padding.
- **The diagnosis INVENTORY** — dead tokens, 20 classes / 9 radii / 24-of-26 hand-typed, `role="h1"` set by nothing, four zero-call-site helpers, `selection_bg`, `setObjectName("accent")` zero in builddoc/coopdoc, `font-weight: 500` → Regular, accent-as-text sub-AA in 6/7 (NORD 2.44). All reproduce exactly; the accent-as-text one is the diagnosis's **live unfixed item**.
- **LAW II's corollary** (`shell.py:1058-1066` → `_deploy_now` → `shell.py:6699` `build_deploy.on_go()`; `builddoc.go` stays quiet) — verified line-for-line at HEAD, and **LAW III** in full.
- **The asymmetry law's premise** — LIGHT `surface_3` = `#ffffff`, rungs 1.046/1.043, span 1.205.
- **Step 0's sequencing advice** — *"Do not start with the groupbox refactor. The screenshot contains a one-line bug."* Vindicated.
- **`_OPT_INDENT`'s "does it survive the card?" reasoning** (only the value 31→30 changes) and **the `test_builddoc_inplace.py:58` constraint** (`"in place"` + `"2952"`, asserts on `.text()` only).
- **Phase 2b** — `QPushButton#accent` (0,1,0,1) out-ranks `QPushButton:focus` (0,0,1,1); **22** accent buttons, **zero** `accent:focus` rules at HEAD. Unshipped, still needed.
- **Phase 2c's mono register** — `type_mono` genuinely dead; `style.py:227` still hardcodes 12px; the Cascadia→Consolas chain already ships, so 2c adds no font dependency.
- **Phase 4d's diagnosis** (`field == surface_btn` in NORD, GRUVBOX_DARK **and** DARK) and **4c's `surface_3` cap** (0.80 → `#fdfdfd` / `#fdfcf8`, verified safe).
- **Phase 4's `test_console_well_stays_recessed_below_the_page` and `test_elevation_ladder_is_a_ladder_not_a_floor`** — green 7/7 today, landable now.
- **Phase 5's "delete the dead"** (`type_label`, `type_body`, `type_mono` after 2c) and the "do not delete `role="h1"` / `QFrame[role="card"]`" caveat — `QFrame[role="card"]` is now `section()`'s own selector.
- **Phase 6** — Home has zero QGroupBoxes; `shell.py:1443-1445` `role="display"` used exactly once; the `ph.addWidget(body, 4)` latent bug at `shell.py:1438` (stretch geometry, not font metrics — survives the offscreen caveat); `min-height` not `setFixedHeight` (`_apply_density` at `:535-539` only re-renders QSS); **the gradient measurement `bg→surface_2` 1.24–1.31 dark / 1.16 light** — the one place the plan measured the right pair.
- **Rejected, essentially whole** — the bezier (0.008 vs 2.997 = 375× gentler), `tabular()`/`tnum` (Segoe digits all advance 1104; `tnum` covers zero latin digits, `pnum` covers all ten), Uppercase-via-QSS (Qt has no `text-transform` — **vindicated**: `widgets.py:182` upper-cases at the call site), `QTabWidget::pane` (`shell.py:1137` `setDocumentMode(True)`; the pane border does not exist), `background: transparent` on QScrollBar (the universal rule wins), de-border the console (`log_bg/bg` 1.066–1.121, and its ≥1.3:1 bar is the same threshold the card clears at 1.308 — consistent, not in tension), tone-only elevation, the measure-cap artifact half, `QPushButton:default`, Gradient-the-buttons, Grey-a-diagnostic, Bundle Inter.
- **Open questions 3 and 4** — MIST's orthogonality (strengthened by the reversal) and "say Consolas and mean it" (`style.py:227` chain intact; `pyproject.toml:83` bundles no font).

**VISION.md**
- **§1 minus the elevation sentence**; **§2's name, lamp test, type prescription and mono register**; **LAW II and LAW III**; **§5's tone-only, tabular, bezier, Inter, diagnostic and Deploy-F9 bullets**; **§63's meta-law** — *"Measure the pixels. Don't reason about them."*

**README.md**
- **The Method paragraph**, **the diagnosis paragraph**, **the whole harness-warning section** (one line ref repointed), **`prove_radio_border.py`** as the colour-only, offscreen-safe proof.
