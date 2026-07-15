<!--
Dream World IX -- Workspace GUI, round 2: AESTHETICS. The deliverable.
Produced 2026-07-15 via a 90-agent research workflow (3 recon agents -> 10 independent design
lenses -> per-proposal adversarial review -> vision -> completeness critic -> this plan).
74 proposals were reviewed; ALL 74 came back NEEDS_REVISION (zero passed as first drafted),
so every proposal here is a CORRECTED one. The refuted set is preserved under "Rejected".

Companion docs: VISION.md (the art direction) - CRITIC.md (the adversarial rebuttal, which
reframed the plan and is the most load-bearing document of the three).

HARNESS WARNING, learned twice: QT_QPA_PLATFORM=offscreen stubs the Qt font database and
inflates every text advance 2-3x. COLOUR measurements are font-independent and trustworthy;
WIDTH measurements taken offscreen are fiction. studies/gui-makeover/README.md already
documented this trap ("that gives tofu boxes") and the lenses fell into it anyway.
Use the native-platform + WA_DontShowOnScreen recipe for anything metric.
-->

# THE PLAN — Making the Workspace Beautiful

> ## ⚠ CORRECTED 2026-07-15 — read this before acting on anything below
>
> The plan was **built from**, and it was wrong about its own headline. Full detail:
> **[CORRECTIONS.md](CORRECTIONS.md)** (126 claims re-audited against the shipped code; 25 auditor
> verdicts overturned on review). Nothing below is deleted — the record of *how* it was wrong is worth
> more than a tidy document.
>
> **1. THE CARD STAYS. The plan's single highest-leverage change was wrong.**
> "Kill the QGroupBox. All 27 of them, in one pass" was built, shown, and overruled by the user:
> *"the cards were nice logical section indicators, they just looked ugly."* The card is now kept and
> fixed. **Why the plan got it wrong is the useful part:** its "the elevation ladder is imperceptible /
> the fills do nothing" measured `surface→surface_2` (1.168). A card sits on the **page**, so the pair
> that governs is `bg→surface_2` = **1.308** in DARK — *stronger* than GitHub dark's card (1.094).
> The fill was always fine. Neither fill nor border was changed. Wrong pair → wrong conclusion → a
> 27-site refactor that nearly shipped for the wrong reason.
>
> **2. What was actually ugly** (all three now fixed in `widgets.section()`): the caption sat **on the
> border** (the Win32 fieldset idiom); the title had **no presence** ($muted at the same 13px as the body
> it labels — and *unfixable while Qt draws it*, because QSS silently ignores `font-*` on
> `QGroupBox::title`: **that**, not "borders are noise", is the real reason the box had to become a
> widget); and there was **no horizontal padding**, amputated to defend an h-scroll bug that never
> existed at the claimed magnitude.
>
> **3. SHIPPED** (branch `claude/gui-card-readability-eb5d9f`): `86de3f5` Phase 0 · `685ba1a`
> `section()`+`Prose` · `881e468` the card reversal · `58f7deb` tick+dot · `0ecfa75` all 27 sites.
> 2884 tests pass. **Phase 3's mechanism shipped in full; its aesthetic premise did not.**
>
> **4. ⛔ PHASE 4 IS NOW UN-LANDABLE — it would revert Phase 0.** Verified: its `surface_2` 0.05→0.10
> reds `muted/surface_2` on **all five dark palettes** (dark 4.83→4.13, nord 4.61→3.94, dracula
> 4.56→3.86, solarized-dark 4.55→3.90, gruvbox 4.59→3.88) against the ≥4.5 floor Phase 0 just landed,
> and breaks solarized-dark's `text/surface_2` too (4.94→4.24). **`surface_2` is the card fill and is
> now load-bearing for accessibility. It is FROZEN at 0.05.** Only 4c (the `surface_3` cap) and 4d's
> *diagnosis* survive.
>
> **5. The plan never mentions the one thing that actually bites** — Qt derives an unnamed control's
> screen-reader name from its enclosing **QGroupBox title**. Removing the boxes silently stripped **13
> names**. The word "mechanical" must be struck from Phase 3. See CORRECTIONS.md §"What the plan MISSED".

## The diagnosis

**Nothing in this app was allowed to be more important than anything else.** Every mechanism that ranks things — tone, type, space, a scarce accent — was built, tokenized, tested, and then never spent. One instrument was left in the box: draw a 1px rectangle around it. A rectangle cannot rank.

The receipts:

- **`style.py:126` is a live bug. ✅ SHIPPED — fixed in `86de3f5`.** *(The analysis below was right in every particular. The correct `::indicator:focus` now lives at `style.py:188`, the `:checked:focus` ring at `:192`, and the whole typo class is guarded structurally by `test_qss_has_no_malformed_subcontrol_selectors` — a shape check, because the existing focus test greps four known-good selector strings and cannot see a malformed one.)* `QCheckBox:focus::indicator, QRadioButton:focus::indicator` writes the pseudo-class *before* the sub-control. Qt's `Selector::pseudoElement()` returns `""` (the first pseudo, `focus`, is a *known* class), and `pseudoClass()` returns `0` on the unrecognised `indicator` — so the match test `(0 & state) == 0` is true in **every** state. The rule degenerates to an unconditional `QRadioButton, QCheckBox { border: 1px solid $focus; }`. **Every radio and checkbox in the app is a permanent accent-blue rect. That is the screenshot.** Reproduced by render: an unfocused, unchecked radio samples `#4c8dff` on all four edges. Radios have simultaneously had **zero focus indication** since it shipped.
- **~~The elevation ladder is imperceptible.~~ ❌ FALSE — THIS MEASURED THE WRONG PAIR.** *(Kept as the record: it is the single error that nearly cost a 27-site refactor.)* DARK: `bg→surface` 1.120:1, `surface→surface_2` 1.168, end-to-end 1.530. LIGHT: 1.105 / 1.046, end-to-end **1.205**. Every figure reproduces to three decimals — **the arithmetic was right and the inference was wrong.** No widget in this app is a bare `$surface` panel on the page: a **card sits on the page**, so the governing pair is `bg→surface_2` — LIGHT 1.155 · **DARK 1.308** · nord 1.271 · dracula 1.247 · solarized-dark 1.332 · gruvbox-dark 1.303. DARK's 1.308 is **stronger than GitHub dark's card** (`#0d1117` vs `#161b22` = 1.094). The fill was always fine and was never changed. The 3:1 comparison is also a category error — WCAG 1.4.11 governs component *boundaries*, not decorative surface fills; no shipping design system clears 3:1 page-to-card. **LIGHT remains the genuinely weak axis** (1.155), which is exactly why the card keeps its border there. The radius/class receipt is untouched and still exact: **20 widget classes** at **9 radii**, 24 of 26 radius declarations hand-typed.
- **The system exists and is unused.** `role="h1"` is set by **nothing** (the 20px tier does not exist at runtime). `widgets.card()`, `heading()`, `status_chip()`, `tabular()` — **zero call sites**. `selection_bg` — derived, documented "replaces full-accent select", **never referenced** (`theme.py:306` vs `style.py:133`). `space_1/3/4/6`, `radius_md` — **dead**; every gap is hand-typed, and every QGroupBox interior silently runs Qt's default 11/6 that no token file knows about. `setObjectName("accent")` in builddoc and coopdoc — **zero**. `font-weight: 500` (`style.py:198`) resolves to Regular — Segoe UI ships no Medium face.
- **The loudest object on the tab is a paragraph.** `builddoc.py:158-161`: `self.dest` is a ~140-char wrapped QLabel at `role="accent"`. `style.py:200` documents that role as "an actionable *value* (e.g. a deploy target)". Measured: accent-as-text is **sub-AA in 6 of 7 palettes** (NORD 2.44:1 on `surface_2`).

This is not an accessibility problem, a colour problem, or a Qt problem. A complete design system exists and the app doesn't use it — so the border does all the work, everything ends up the same shape at the same volume, and that is exactly what you are looking at.

**The measurement caution, stated once:** colour measurements in this dossier are font-independent and were verified by render. **Width measurements were not.** The offscreen QPA stubs the font database and inflates every advance ~2–3×. The widest non-wrapping control in the app is **642px**, not 1503px. At 1280px minus the rail there is ~1080px of content. **There is no horizontal-scroll emergency and there never was.** Every "collapse the tab's minimum width" justification in the dossier is dead. Any width assertion added to CI must `skipif "Segoe UI" not in QFontDatabase.families()`.

---

## The direction

### **WORKSHOP**

A dark table. Tools laid flat on it, nothing in a case. **Exactly one thing under the lamp.**

The page is dark and mostly empty. A section is a small tracked-caps muted label, then its rows, then a generous gap before the next label — no fill, no frame, no floating caption cutting a line. Grouping comes from proximity and a shared left edge, the way it does in **Linear's settings** and **Zed's settings pane** — both of which abolished the titled box a decade ago and are the closest living relatives of this app's shape (nav tree left, stacked option groups right, dense, dark, technical).

On any screen: **one** lifted surface, **one** accent object, **one** 20px title. Everything else is type on the table — 13px `$text` for what you act on, 11px `$muted` for what explains it. Controls are named in three words; the sentence lives underneath in grey, wrapped, capped at a readable measure. And because this app's entire subject is machine tokens — `4003`, `30110`, `ff9-XXXXXXXX`, `FF9CustomMap` — those are set in a mono family, the one texture in the composition and the thing that makes it look like it knows what it is.

The test, every time: **is this under the lamp, or on the table?** Almost everything is on the table.

### The three laws

**I. A border must earn its existence.** Group by space and type first. A stroke is for things you can click into or type into — a button, an input, a tab, a focus ring. A *container* is not a stroke; it is a label and a gap. If you removed the border and the grouping still reads, the border was noise.

**II. One thing per screen is loud.** One accent object, one lifted surface, one page title. Accent is a *fill for the verb you press* — never a foreground for prose, never a highlight for a list row, never a hue spent twice. Corollary, verified: `shell.py:1058-1066` already ships an accented **Deploy F9** in the crumb row on every tab, whose `_deploy_now` calls the identical `build_deploy.on_go()` (`shell.py:6699`). **The crumb owns the primary. `builddoc.go` stays quiet.**

**III. A control gets a name; the sentence goes underneath.** Never put prose inside a widget. A radio is `Test slot 4003`; "quick + reversible, play via F6 → Warp" is an 11px grey wrapped caption beneath it, indented to the label's own column. Say each fact exactly once.

**The asymmetry law (dark ≠ light).** LIGHT's `surface_3` is literally `#ffffff` and its rungs step 1.046 and 1.043. Every "borderless card carried by fill" dies there. **Dark gets depth from a widened tonal span; light gets it from a border and a gap.** This is why Law I says *space and type*, not *tone*.

**The meta-law:** the static reading of `style.py` said the radio borders were impossible; three renders said they were real; the render was right. **Measure the pixels — and know which pixels your harness is lying about.**

---

## The one change that proves it

**Do not start with the groupbox refactor.** The screenshot contains a one-line bug, and nobody has looked at the panel without it. Four edits, one afternoon, one screenshot each, **zero borders removed**.

### Step 0 — ship this in the next ten minutes

`ff9mapkit/ff9mapkit/workspace/style.py:126`, replace one line with two:

```python
    /* NB: pseudo-ELEMENT before pseudo-CLASS. `QCheckBox:focus::indicator` silently degrades to an
       unconditional `QCheckBox { border: ... }` -- Qt returns pseudoClass()==0 on the unknown pseudo,
       so the match test `(0 & state) == 0` is true in every state. It boxed every radio app-wide. */
    QCheckBox::indicator:focus, QRadioButton::indicator:focus { border: 1px solid $focus; }
    /* a CHECKED indicator is already filled $accent, and $focus == $accent in 6 of 7 palettes, so the
       rule above is a no-op exactly when a radio is clicked or arrowed into. $accent_fg is the one
       token guaranteed legible on $accent. Specificity 0x31 beats :checked's 0x21 -- not source order. */
    QCheckBox::indicator:checked:focus, QRadioButton::indicator:checked:focus { border: 1px solid $accent_fg; }
```

**Before:** three full-width accent-blue rects around the three radio rows, always, plus no focus ring on any radio or checkbox in the app.
**After:** three rects gone. A visible focus ring in all 7 palettes × {radio, checkbox} × {checked, unchecked} — 28/28 cells with a nonzero pixel delta; ring-vs-fill contrast 3.2–5.9, clearing the 3:1 non-text floor everywhere.

**Verified:** radio/checkbox `sizeHint().height()` 28 → **26**, still ≥24 (WCAG 2.5.8) in **both** densities. `padding: 3px 2px` at `style.py:88` is a literal, not a `$var`, so density is unaffected. No test greps `focus::indicator`. No palette key added (`accent_fg` is in all 7). `style.py` stays PySide6-free. 57/57 workspace tests pass.

**Re-screenshot and send it before doing anything else.** You cannot judge any redesign until it's gone.

### Steps 1–3 — the Build to (field) box, no borders removed

**Step 1 — the radios become names** (`builddoc.py:131-149`). Justify as *type hierarchy*, not width.

```python
_OPT_INDENT = 31   # radio TEXT column: 3px left inset + 20px indicator (style.py:90 width:18 +
                   # 1px border EACH SIDE -- QSS puts the border OUTSIDE width) + 8px spacing
                   # (style.py:88). Measured via style().subElementRect(SE_RadioButtonContents).x().
                   # NOT 26 or 28 -- both are naive arithmetic that lands 3-5px short.

def _opt(rb, text, gv):
    """A choice is a NAME; its consequence is a caption beneath it, on the label's own column."""
    gv.addWidget(rb)
    c = QLabel(text)
    c.setWordWrap(True)
    c.setProperty("role", "caption")
    c.setContentsMargins(_OPT_INDENT, 0, 0, 6)
    c.setMaximumWidth(PROSE_W)          # see the token diff
    gv.addWidget(c)
    rb.setAccessibleDescription(text)   # the a11y test only checks non-empty; do this anyway
    return c

self.rb_test = QRadioButton(f"Test slot {tid}")
self.desc_test = _opt(self.rb_test, "", gv)
# KEEP the ternary -- jobs.detect_game_mod() returns None and Path(None) raises TypeError.
self.rb_game = QRadioButton(f"Install to game: {Path(self.game_mod).name}"
                            if self.game_mod else "Install to game — (game install not found)")
self.desc_game = _opt(self.rb_game, "", gv)
# builddoc.py:143 "Build only — to a folder:" STAYS AS IS -- it is a field label for the adjacent
# QLineEdit in the `of` row (:141-148), not prose. Cutting it orphans the input. 359px, not a floor.
```

**Step 2 — demote the blue paragraph** (`builddoc.py:158-161`, and `_update_dest` at `:378-407`).

`self.dest` keeps its name (`tests/test_builddoc_inplace.py:58` asserts `"in place" in doc.dest.text().lower()` and `"2952" in doc.dest.text()`). It stops being accent, and its four branches feed the per-option captions:

```python
self.dest = QLabel("")
self.dest.setWordWrap(True)
self.dest.setProperty("role", "muted")   # was "accent" -- accent-as-text is sub-AA in 6/7 palettes
gv.addWidget(self.dest)
```

`_update_dest` keeps every `self.rev.setEnabled(...)` / `setToolTip(...)` branch **verbatim**, and cuts each `msg` to a short value line:

```python
inplace: msg = f"→ in place on field {t['donor']} · reversible"      # keeps "in place" + the donor id
test:    msg = f"→ field {tid} in {self.mod_folder} · reversible"
game:    msg = f"→ field {own} in {where} · overwrites, no undo"
other:   msg = f"→ field {own} → {folder} · no game change"
```

**Do not grey the diagnostic.** The `rb_game` branch is the app's only *no-undo* warning (`self.rev.setEnabled(False)`, tooltip concedes "no automatic undo"). Give it weight via the rule that already exists (`style.py:205`):

```python
self.dest.setProperty("state", "warn" if own is not None and self.rb_game.isChecked() else "")
st = self.dest.style(); st.unpolish(self.dest); st.polish(self.dest)   # setProperty does NOT restyle
```

`_update_dest` runs *after* first polish — the repolish is not optional (`widgets.py:213`).

**Step 3 — land the `surface_2` contrast assertion first** (see Phase 0). Steps 1–2 put captions inside a `$surface_2` groupbox, where `muted` measures **3.87–4.07** in NORD / DRACULA / SOLARIZED-DARK / GRUVBOX — sub-AA *today*, uncaught because the contrast test only ever checks `bg` and `surface`.

**You'll see:** Build & Deploy becomes **BUILD TO** / three named options each with a quiet line under it / air / actions. The three phantom rects are gone, the blue paragraph is gone, the loudest thing on the tab is the accented Deploy F9 in the crumb — the button you actually press. **Zero borders removed.** If it reads well, the groupbox verdict was never needed. If it still reads badly, *now* you know the box is the problem and Phase 3 has earned its risk.

---

## Phases

### Phase 0 — Close the contrast hole and fix the selector — **trivial**

**Goal:** make the spike legal in all 7 palettes, and delete the bug that *is* the screenshot.

| Change | File:line |
|---|---|
| The `::indicator:focus` reorder + the `:checked:focus` ring | `style.py:126` |
| Add the `surface_2` assertions | `tests/test_editor_theme.py:95` (`test_palette_contrast_invariants`) |
| Lift `muted` in the 4 failing palettes until green | `theme.py` NORD/DRACULA/SOLARIZED_DARK/GRUVBOX_DARK — **values only**, no keys |
| Add the malformed-selector lint | `tests/test_workspace_style.py` |

```python
# tests/test_editor_theme.py, inside test_palette_contrast_invariants
d = theme.derive(pal)
assert _contrast(pal["muted"], d["surface_2"]) >= 4.5, f"{mode}: hint text on a groupbox"
assert _contrast(pal["text"],  d["surface_2"]) >= 4.5, f"{mode}: body text on a groupbox"

# tests/test_workspace_style.py -- catches the pseudo-class-before-pseudo-element class generically.
# Headless, no Qt, cheap. The existing focus test is a substring grep and structurally cannot see it.
def test_qss_has_no_malformed_subcontrol_selectors():
    import re
    css = qss(pick_palette("dark"))
    bad = re.findall(r"[A-Za-z]+:[a-z-]+::[a-z-]+", css)
    assert not bad, f"pseudo-class before sub-control (Qt matches neither): {bad}"
```

**Fails today** in nord/dracula/solarized-dark/gruvbox-dark (muted) and solarized-dark (text). Land the palette lift in the **same commit** or the test is red on arrival.

**Tests touched:** `test_editor_theme.py` (extend), `test_workspace_style.py` (add). Key sets unchanged → `test_palettes_share_one_key_set` untouched.

**You'll see:** three blue rects vanish from Build & Deploy; radios gain a focus ring they have never had; every caption anywhere in the app becomes provably legible on a panel.

---

### Phase 1 — The spike: name the options, demote the paragraph — **small**

**Goal:** prove the hierarchy thesis on the exact card from the screenshot, with zero structural risk.

| Change | File:line |
|---|---|
| `_OPT_INDENT = 31` + `_opt()` helper; radios → noun phrases | `builddoc.py:131-149` |
| `self.dest` → `role="muted"`, `state="warn"` on the no-undo branch + repolish | `builddoc.py:158-161`, `:378-407` |
| Add `PROSE_W = 400` and the measure-capped `_Prose` label | `widgets.py` (new; see the token diff) |
| Bring the same treatment to the campaign/journey boxes' radios | `builddoc.py:181-182`, `:193-196`, `:202-203`, `:211-214` |

**Landmine:** a raw `setMaximumWidth` on a word-wrapped QLabel **clips inside a QGroupBox**. `QBoxLayout::calcHfw` asks `heightForWidth()` at the *full* cell width, so the box reserves 2 lines and then lays the label out at 400px needing 4. Verified: subclass → `w=440 h=96 need=96`; raw cap → `w=440 h=48 need=96 *** CLIPPED ***`. Use the `_Prose` subclass (token diff) — it overrides `heightForWidth` to clamp at the cap. Do **not** use the HBox+stretch wrapper as a general fix; it collapses the label to its `sizeHint` (263px measured) and throws the measure away.

**Tests touched:** `tests/test_builddoc_inplace.py:58` must keep passing — it does, because `self.dest` keeps its name and the `inplace` branch keeps `"in place"` and the donor id unsplit. Add:

```python
def test_prose_reports_a_truthful_height_inside_a_groupbox(qtbot):
    """calcHfw asks hfw() at the FULL cell width, so a raw setMaximumWidth makes a QGroupBox
    reserve 2 lines and then lay the label out at the cap needing 4 -- silent clipping."""
    box = QGroupBox("x"); lay = QVBoxLayout(box)
    lab = widgets.prose("…250+ chars…"); lay.addWidget(lab)
    host = QWidget(); hv = QVBoxLayout(host); hv.addWidget(box); host.resize(1100, 400); host.show()
    assert lab.height() >= QLabel.heightForWidth(lab, lab.width())
```

**You'll see:** three scannable names with quiet explanations under them; the blue full-width sentence replaced by a short muted value line; the no-undo warning still shouting. The tab reads as a document.

---

### Phase 2 — The button ladder and the mono register — **small**

**Goal:** give the action row an entry point, and make the app's machine tokens look like machine tokens.

**2a — the quiet tier.** Append to `style.py` after `QToolButton[role="link"]` (~:221):

```
/* the QUIET button tier (weight ladder: #accent primary > plain default > quiet).
   NB :disabled and :pressed are NOT optional -- [role=] ties the generic QPushButton:disabled /
   :pressed on specificity and is declared LATER, so it would win: a disabled quiet button would
   render pixel-identical to an enabled one (measured: glyph #9aa3ad either way) and presses would
   give no feedback. Same trap as #accent:disabled above; coop's Stop bridge SHIPS disabled. */
QPushButton[role="quiet"]          { background: transparent; border: 1px solid $border; color: $text; }
QPushButton[role="quiet"]:hover    { background: $hover; }
QPushButton[role="quiet"]:pressed  { background: $pressed; }
QPushButton[role="quiet"]:focus    { border: 1px solid $focus; }
QPushButton[role="quiet"]:disabled { color: $muted; background: $bg; border: 1px solid $border; }
```

`color: $text`, **not** `$muted`: `style.py:59-60` already spends *transparent + muted* as the **disabled** idiom. A muted ghost reads as un-clickable. Hierarchy comes from the missing **fill**, not from dimmer text. Height measured at 27px comfortable — clears 24.

Stamp at construction: `builddoc.py` `pack_btn` → `role="quiet"`; `coopdoc.py` `btn_off` → `role="quiet"`. Re-order the row so constructive and destructive sit across the stretch:

```python
btns.addWidget(self.chk); btns.addWidget(self.go); btns.addWidget(self.rev)
btns.addStretch(1)                    # was after pack_btn (:114) -- this is what flattened the row
btns.addWidget(self.pack_btn)
```

**Do not accent `builddoc.go`** (Law II — the crumb already owns it). **Do** accent `coopdoc.py:193`: `self.btn_start.setObjectName("accent")` and delete the inert `setDefault(True)` at `:194` (`CoopDoc` is a QWidget, not a QDialog, and there is no `QPushButton:default` rule — grep count 0).

**2b — close the accent focus hole.** `QPushButton#accent` (specificity 0,1,0,1) out-ranks `QPushButton:focus` (0,0,1,1) — **the app's ~22 accent buttons have no focus ring today**, including the crumb Deploy. Add beside the other `#accent` state rules:

```
/* the #accent id selector out-ranks the generic QPushButton:focus (same reason as :disabled below),
   so the primary needs its OWN ring. $accent_fg, not $focus: $focus == $accent in 6 of 7 palettes. */
QPushButton#accent:focus { border: 1px solid $accent_fg; }
```

**2c — the mono register.** One rule, family only:

```
QLabel[mono="true"], QLineEdit[mono="true"] {
    font-family: "Cascadia Code", "Consolas", monospace;
}
```

**Family only — no `font-size`.** It then inherits 13px from `style.py:46`, so no height change, no compact-density target-size risk. Use an orthogonal `mono` property, **not** a `role` value — `role` is single-valued across ~111 call sites, and `role="id"` on `battle_dest` would silently drop its `role="muted"`. Also fix `style.py:161`, which hardcodes `font-size: 12px` while `$type_mono` sits unreferenced → use the token.

Targets: `builddoc.py:234` `newgame_id`, `:264` `trigger` (both **QLineEdit** — a `QLabel[role=...]` selector would have missed them), `coopdoc.py:105` `self.code` (the `ff9-XXXXXXXX` session code — the most-copied string in the app). **Split** `builddoc.py:259` `battle_dest` into `QLabel("Test mod folder:")` + a sibling `QLabel(path)` with `mono=True` + `role="muted"` — cheaper and safer than rich text, no escaping problem. **Exclude** `coopdoc.py:153` `spin_wait` (it carries `setSuffix(" s")` / `setSpecialValueText("no cap")`; mono on prose reads as a bug).

**Cascadia is not guaranteed** — it ships with VS/Windows Terminal, not Windows. On a clean machine the chain falls to Consolas. That is fine; say "Consolas" and mean it. Do not bundle a font (see Rejected).

**Tests touched:** add `test_qss_distinguishes_a_disabled_quiet_button` (assert `QPushButton[role="quiet"]:disabled` and `:pressed` are in the CSS) and `test_accent_button_keeps_a_visible_focus_ring` (assert `QPushButton#accent:focus` in css for all palettes).

**You'll see:** one blue verb per screen; Package and Disable recede to ghosts until hovered; field ids, session codes and paths set in a mono face that says "machine token, not prose" — the app's first real texture.

---

### Phase 3 — ~~Kill the QGroupBox~~ **→ KEEP the card, fix what was ugly** — ✅ SHIPPED (`881e468`, `0ecfa75`)

> **THE MECHANISM SHIPPED IN FULL; THE AESTHETIC PREMISE DID NOT.** All 27 `QGroupBox`es are now
> `widgets.section()` and QGroupBox is constructed nowhere in the workspace — but they became **cards**,
> not nothing. The gate this phase was placed behind worked exactly as designed: Phase 0 landed, the
> panel was re-screenshotted, the borderless version was built (`685ba1a`) and shown, and the user
> overruled it — *"the cards were nice logical section indicators, they just looked ugly."* Read the
> banner at the top of this file for why the premise was wrong (it measured `surface→surface_2`, not
> `bg→surface_2`).
>
> **What shipped instead** (`widgets.py` `section()`): a `QFrame` `role="card"` — fill and border
> **unchanged** — with the title INSIDE as a `role="overline"` label (11px/600/+1px tracking, a token
> that existed with zero users) and 16px of padding. `SECTION_GAP` is **14**, not this phase's 24: the
> card draws its own boundary, so the gap no longer has to carry the grouping alone. The "pay the
> whitespace or don't ship it" law is **re-scoped, not wrong** — it governs the borderless case, which
> is now moot.
>
> **⛔ THE WORD "MECHANICAL" MUST BE STRUCK FROM THIS PHASE.** Qt derives an unnamed control's
> screen-reader name from its enclosing **QGroupBox title** (`QAccessibleWidget` → `buddyString`, which
> reads `groupbox->title()`, *not* `accessibleName()`). A card has no title for Qt to find, so every
> control leaning on the box goes **silent**: **13 did**, across Models / Import / Build.
> `test_workspace_a11y.py` caught them; each was restored with `setBuddy(visible_label)`, or
> `setAccessibleName` where no visible label exists. **This also kills this phase's own "drop-in"
> recipe** — a titleless `QGroupBox` + `setAccessibleName` strips descendant names *identically* to the
> card (probed). There was never a mechanical version of this migration.
>
> **One bug this phase's borderless spec could not have caught:** the content host must be a **layout**,
> never a wrapper `QWidget`. The stylesheet opens with a universal `QWidget { background-color: $bg; }`,
> so a bare QWidget content host paints the **page** colour over the card's fill — a visible darker
> rectangle inside every card, i.e. the exact box-in-box being fixed. It is invisible on a borderless
> section (bg on bg) and only surfaces once the card has a fill.

**Original goal (superseded):** the outer rectangle stops existing. Grouping becomes a label and a gap.

**Do not start this until Phase 1 has been screenshotted and judged.** If the spike already reads well, this is optional. If it doesn't, this is the answer and the risk is earned.

**The factory must drop in at the exact call shape**, or this is 27 hand-edits instead of a mechanical pass. Return a `QGroupBox` with an emptied title and an injected overline:

```python
# widgets.py
def section(title, *, parent=None):
    """A section is a LABEL and a GAP, not a container.

    Returns a QGroupBox so it drops into the existing `box = QGroupBox(t); lay = QVBoxLayout(box)`
    call shape. setTitle("") + border:0 renders a bare container; setAccessibleName preserves the
    screen-reader GROUPING that a plain QWidget + QLabel would silently lose (verified: QAccessible
    reports the name). The header is a real QLabel because QGroupBox::title SILENTLY IGNORES font
    declarations -- render-verified: ink identical at 13/600, 11/700+1px tracking, and 18/700. And
    `left: 0px` is NOT flush: subControlRect REPORTS x==0 while the paint path adds +6.
    """
    box = QGroupBox(parent)
    box.setTitle("")
    box.setAccessibleName(title)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    lay.addWidget(role_label(title, "overline"))   # style.py:220 -- ALREADY 11px/600/$muted/+1px
    return box, lay
```

`role="overline"` already exists, is already tokenized, and is already unused. Zero new palette keys. `letter-spacing` **does** work on a QLabel (measured: sizeHint 192 vs 176) — it just doesn't work on `QGroupBox::title`, which is why the header must be a real label.

QSS:

```
QGroupBox { background: transparent; border: 0; border-radius: 0;
            margin-top: $gb_margin_top; padding-top: $gb_pad_top; }
/* kept as a neutral fallback for stragglers -- NOT styled as an overline */
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 0px;
                   padding: 0; color: $muted; font-weight: 600; background: transparent; }
```

Set `gb_margin_top` / `gb_pad_top` to `"0px"` in **both** density profiles (keep both keys — `test_qss_density_profiles_both_substitute_cleanly` requires them) and let `section()` own the rhythm via layout spacing.

**Pay the whitespace or don't ship it.** Every lens that deleted the box while leaving the page at `setSpacing(12)` measured *worse* — an orphaned label floating equidistant between two groups is not a section. Measured target: **~2:1 above:below**. Set the page column to `v.setSpacing(24)` (**not** `setSpacing(0)` + `addSpacing()`: the field/campaign/journey boxes are mutually exclusive via `_render_kind` at `:303-307`, and a `QSpacerItem` has **no visibility** — it survives its panel being hidden and orphans 48px of dead air in `kind=="battle"`. `setSpacing()` gaps collapse with their widget for free).

**Migrate per TAB, never per box** — 27 sites: builddoc 6, importdoc 10, coopdoc 3, battledoc 3, modelsdoc 3, savedoc 1, shell 1. One borderless tab beside five boxed ones reads as unfinished. Order: builddoc → coopdoc → importdoc → battledoc → modelsdoc → savedoc → shell. Only after site 27 delete the `QGroupBox` rules.

**Exceptions:** `shell.py:1937` `QGroupBox(f"Fork the arcs ({len(done)}/{len(folders)} forked)")` is a live-counter primary affordance — give it `role="h3"`, not an 11px muted overline. `battledoc.py:558/619/649` `(8,4,8,4)` are deliberate dense data-panel interiors, not page padding — leave them.

**Un-nest the two real nestings** (`builddoc.py:208→220`, `importdoc.py:123/144/159 → 83`): once the parent is borderless, the child's 10px inset already reads as subordination. **Do not** hand-set `setContentsMargins` — QSS derives the content inset (border 1 + padding 9 = 10) to land exactly on the title's column; any hand margin desyncs it by 3px. Subordination comes from *type* (the overline is already caption-sized + tracked), not from dimming — **never** `$text_subtle`, which fails 4.5:1 on `surface_2` in **all 7** palettes (2.55–3.20).

**The free rider:** deleting the fill lands every caption on `$bg`, where `muted` is tested and passes in all seven. **The aesthetic move is the accessibility fix.**

**Tests touched:** none locked (`grep QGroupBox|gb_margin|gb_pad tests/` = zero). Add a smoke assert that `widgets.section()` returns `(box, lay)` with `accessibleName` set.

**You'll see:** the page becomes a document. 27 borders and 27 fills gone. Build & Deploy is **BUILD TO** / options / air / **ADVANCED** / air / actions.

---

### Phase 4 — ~~Widen the dark span; keep the light border~~ — ⛔ **MOSTLY UN-LANDABLE: IT REVERTS PHASE 0**

> **`surface_2` IS FROZEN AT 0.05.** This phase was written before Phase 0 existed. Phase 0 landed
> `muted/surface_2 >= 4.5` and `text/surface_2 >= 4.5` assertions — and `surface_2` is now **the card
> fill**, so it is load-bearing for accessibility. Phase 4a's `surface_2` 0.05 → 0.10 reds the floor on
> **all five dark palettes** (verified by computing them):
>
> | palette | `muted/surface_2` now | @ 0.10 |
> |---|---|---|
> | DARK | 4.825 | **4.126** ❌ |
> | NORD | 4.606 | **3.942** ❌ |
> | DRACULA | 4.555 | **3.859** ❌ |
> | SOLARIZED_DARK | 4.553 | **3.904** ❌ (+ `text/surface_2` 4.940 → **4.236** ❌) |
> | GRUVBOX_DARK | 4.585 | **3.877** ❌ |
>
> Its whole premise is the wrong-pair error (see the banner): `bg→surface` 1.120 governs nothing,
> because no widget is a bare `$surface` panel on the page. The depth was never missing — the card
> measures 1.308 in DARK, above GitHub's 1.094.
>
> **What survives:**
> - **4c (the `surface_3` cap) — LAND IT.** `theme.py` derives `surface_3 = #ffffff` for *both* light
>   palettes, so solarized-light's cream page gets a pure-white top rung, contradicting `theme.py`'s own
>   stated rule. At 0.80: `#fdfdfd` / `#fdfcf8` (the cream survives; verified safe on every assertion).
> - **4d's DIAGNOSIS — valid, still unfixed, but its gruvbox VALUE is wrong.** `field == surface_btn`
>   byte-identically in **three** palettes (NORD `#3b4252`, GRUVBOX `#3c3836`, **and DARK `#2b3038`**) —
>   an input well and a button face render as the same hex. But the proposed `gruvbox field → #32302f`
>   **IS gruvbox's own `surface`** — byte-identical, a *worse* collision than the one it fixes, and
>   precisely the error this row catches one clause earlier for nord ("not `#2e3440` — that IS nord's
>   bg"). **Any `field` proposal must be checked against `bg`, `surface`, `surface_btn` AND `log_bg`.**
> - **A LIVE BUG this phase surfaces but never fixes: `hover == surface_btn` byte-identically in NORD,
>   DRACULA, SOLARIZED_DARK and GRUVBOX_DARK — those four palettes have _no button hover feedback at
>   all_.** Verified. 4b only edits DARK, so nothing here lands it. **Ship the four hover values as
>   their own commit.**
> - Two of its three proposed tests are green today and landable now (`log_bg < bg`; the elevation
>   ladder is 3-distinct — the existing monotonic test is non-strict and would pass a flat floor). The
>   third (hover) is **red on arrival** on the four palettes above, which is the point.

**Original goal (superseded):** dark themes get real depth. Light themes keep the one cue that works there.

**The trap, measured:** deepening `bg` alone buys nothing — contrast is `(L1+.05)/(L2+.05)`, and near black the flare term dominates. A proposal that moved `surface` to the old `bg` and slid `bg` down one step measured **1.124:1** vs today's 1.120 — a translated ladder, not a widened one, with the full span *regressing* 1.530 → 1.519. **Widen the span; don't slide it.**

**4a — raise the dark rungs only** (`theme.py:304-305`). These are *our* derived values, not anyone's canonical hexes, so this fixes all 5 dark themes without touching a community palette:

```python
out["surface_2"] = _mix(pal["surface"], "#ffffff", 0.10 if dark else 0.55)   # was 0.05
out["surface_3"] = _mix(pal["surface"], "#ffffff", 0.19 if dark else 1.00)   # was 0.10
```

Span (bg→surface_3): nord 1.486→**1.947**, dracula 1.472→**1.979**, gruvbox 1.541→**2.054**, solarized-dark 1.553→**2.059**.

**4b — DARK: lift the surface, carry the interaction ladder** (`theme.py:46-69`):

```
bg          #1e2127 -> #141619
surface     #262a31 -> #242931
surface_btn #2b3038 -> #2f353e     (also breaks the surface_btn == field collision)
hover       #30353d -> #363d47     (must stay LIGHTER than surface_btn -- see the law below)
log_bg      #181b20 -> #101215     (must stay BELOW bg -- the console is the ladder's only down-rung)
field       #2b3038 -> #22262c     (a WELL: darker than surface; text-in-input 10.81 -> 12.38)
```

Result: `bg→surface` 1.120 → **1.240**; full span 1.530 → **2.306** (+51%). Fence: text/bg 14.77, text/surface 11.91, muted/bg 7.09, muted/surface 5.72, focus/surface 4.57 — all clear.

**4c — LIGHT: do NOT set `surface = #ffffff`.** It collapses the ladder to 1/3 distinct (`_mix(#fff,#fff,·)` = `#ffffff` for both rungs), making card/chip/section invisible — the exact opposite of the thesis, arriving precisely when Phase 3 has removed the borders that were carrying them.

```
bg          #e8eaed -> #e4e7eb
surface     #f4f5f7 -> #f7f8fa
surface_btn #f4f5f7 -> #edeff2     (fixes surface_btn == surface, currently exactly 1.000)
hover       #dfe2e7 -> #dce0e6
pressed     #d4d8de -> #d1d6dd
muted       #626974 -> #5d646e     (holds 4.5 against the darker bg)
field       #fbfcfd -> #ffffff     (a white input on an off-white panel -- the correct light idiom)
```

Also cap `surface_3` off pure white in the light branch — `0.80` instead of `1.00` gives LIGHT `#fdfdfd` and solarized-light `#fdfcf8` (H=48, warmth retained), honouring `theme.py:23`'s own "not glaring #ffffff panels" note. **Stay relative** — a lerp toward white can only desaturate along the source hue, never inject a foreign one; absolute hexes would put blue chips on solarized-light's cream page.

**4d — NORD/GRUVBOX field collision.** `nord field #3b4252 -> #272c36` (**not** `#2e3440` — that IS nord's bg, byte-identical). `gruvbox field #3c3836 -> #32302f`.

**Add the missing laws as tests** — every one of these bugs shipped because nothing measured it:

```python
def test_console_well_stays_recessed_below_the_page():
    """log_bg is the ladder's only DOWNWARD rung. A deeper bg that crosses it silently inverts the
    well -- or, at equality, erases it."""
    for mode, pal in theme.THEMES.items():
        assert _luminance(pal["log_bg"]) < _luminance(pal["bg"]), f"{mode}: console well inverted"

def test_elevation_ladder_is_a_ladder_not_a_floor():
    """The existing monotonic test is non-strict (l1 <= l2 <= l3) and passes on a flat floor."""
    for mode, pal in theme.THEMES.items():
        d = theme.derive(pal)
        assert len({pal["surface"], d["surface_2"], d["surface_3"]}) == 3, f"{mode}: ladder collapsed"

def test_hover_moves_toward_the_light():
    for mode, pal in theme.THEMES.items():
        assert (_luminance(pal["hover"]) > _luminance(pal["surface_btn"])) is pal["dark"], \
            f"{mode}: hover goes the wrong direction"
```

**Tests touched:** `test_editor_theme.py` (3 added). Key sets unchanged — values only.

**You'll see:** in dark, panels and inputs finally sit at different depths without a stroke. In light, nothing changes except that a button stops being the same hex as an input.

---

### Phase 5 — Radius, spacing and role hygiene — **small** *(land silently; never bill as beauty)*

**Goal:** make the next visible change a 3-line edit instead of a 26-site hunt.

**Three tokens, three geometric exemptions.** Of 26 declarations, only 7 change value and five move one pixel. Nobody will see it. That's the point.

| Tier | Value | Sites |
|---|---|---|
| `$radius_sm` | 4px | `::item` (:131), checkbox indicator (:93), `QMenu::item` (:166), chip (:213) |
| `$radius_md` | 6px | buttons (:55), QLineEdit (:101), combo (:109), tab tops (:139 ×2), QMenu (:165), banner (:225), `#hub` (:234), **`#search` 7→6** (:73), **`#railSeg` 7→6** (:250) |
| `$radius_lg` | 8px | trees/lists (:129), pane (:136), groupbox (:149), text edits (:160), **both cards** |

**Geometric — stay literal, with a comment naming the pin:**
- radio indicator `9px` on an 18px box (:92); `#conceptBadge` `11px` on 22×22 (:267); the Info-Hub badge `15px` on 30×30 (forms_qt.py:546) — circles.
- `QProgressBar` **stays 3px** (:178-179) — `shell.py:1304` fixes the bar at 120×6, so 3px is *exactly* half-height = the capsule. 4px exceeds half-height and Qt either clamps it (buys nothing) or squashes the chunk ends.
- `QScrollBar::handle` → **6px**, not 4 (:171/:173) — the groove is 12px (:170/:172), so 6 is the true pill. 4px squares off the one element Linear and Zed both render as a capsule.

**One card.** Delete `QFrame#card` (`:190`, `$surface`, hardcoded 10px). Keep `QFrame[role="card"]` (`:211`, `$surface_2`, `$radius_lg`) — it's the tokenized one, and `test_workspace_style.py:67` asserts that exact selector. Migrate `shell.py:1546` and `:1604` from `setObjectName("card")` to `setProperty("role", "card")`. **Also fix `palette.py:89`** (`#paletteCard`, 10px → 8px) — it's the app's only genuinely floating card (the sole `attach_shadow` caller) and must not be the last 10px in the build.

**Fence it:**

```python
def test_qss_uses_only_the_radius_language():
    """3 = the 6px busy bar's capsule (shell.py:1304); 6 = the 12px scrollbar groove's pill;
    9/11/15 = circles. Everything else is one of three tokens."""
    import re
    got = {int(m) for m in re.findall(r"border-[a-z-]*radius:\s*(\d+)px", qss(pick_palette("dark")))}
    assert got == {3, 4, 6, 8, 9, 11}
```

**Spacing.** Export the grid as ints so layouts and QSS share one vocabulary (`style.py` stays a pure str/int builder — no Qt import):

```python
_GRID         = {"space_1": 4, "space_2": 8, "space_3": 12, "space_4": 16, "space_6": 24}
# Compact scales ~0.75 and must NOT alias rungs -- a scale whose job is rhythm loses it the moment
# two rungs collapse to the same number.
_GRID_COMPACT = {"space_1": 4, "space_2": 6, "space_3": 8,  "space_4": 12, "space_6": 16}
_SCALES = {**{k: f"{v}px" for k, v in _GRID.items()}, "radius_sm": "4px", ...}

def space(key: str, density: str = "comfortable") -> int:
    """The 4px grid as an int, for Qt layout calls (QLayout is not QSS-styleable and has no cascade)."""
    return (_GRID_COMPACT if density == "compact" else _GRID)[key]
```

Fan-out lives in `_apply_density` (`shell.py:535`), **not** `retheme` (which takes `pal`, not density) — and `_finish`'s Cancel path (`shell.py:809-830`) must route through it, or QSS reverts while layouts stay at the previewed density.

Page padding, one value, at each doc's **real** page level: builddoc `:68` 16→24, importdoc `:57` 16→24, coopdoc `:68` **14**→24 + `:69` 10→12, modelsdoc `:67` **10**→24, battledoc `:183` 0→24, savedoc `:460` (`ov`, currently unset ≈ Qt default 9–11) → 24. Leave `savedoc.py:469`'s `(0,0,0,0)` — it's correct *because* `ov` pads.

Group interiors: `gv.setContentsMargins(11, 0, 11, 11)` — **11, not 12**: the groupbox's 1px border sits *outside* the layout, so 1+11 puts content ink at 12, the same x as the title. `top=0` is the real win: the QSS already supplies 23px (margin 12 + border 1 + padding-top 10); Qt's silent default 11 made it 34.

**Delete the dead:** `type_label`, `type_body` (both 13px, and thus not a distinction anyway), and `type_mono` **only after Phase 2c wires it**. **Do not** delete `role="h1"` or `QFrame[role="card"]` — `test_workspace_style.py:67` pins both selectors and `test_workspace_widgets.py:26/:35` pin `heading()`→"h1" and `status_chip`→"chip". Adopt `heading(t, 1)` for tab titles instead, so the 20px tier finally exists.

**Tests touched:** add the radius fence; `test_qss_compact_is_tighter_than_comfortable`'s exact-string `row_pad` assertions (`"padding: 6px 8px"` / `"padding: 3px 4px"`) are **untouched** by all of the above — do not change row padding in this phase.

**You'll see:** almost nothing. A search pill one pixel rounder. That is the correct outcome.

---

### Phase 6 — The Home page — **medium** *(optional; the only surface with room to be beautiful)*

**Goal:** the first frame — the one that ends up in the README and the GitHub social card — stops being a bare QLabel on a page.

**Home has zero QGroupBoxes.** Phase 3's headline does not touch it. It is `shell.py:1443-1445` — `QLabel("Dream World IX — Workspace")` at `role="display"` — plus a stack of `QFrame#card` rows. `role="display"` is used **exactly once** in the entire app.

Replace with a **full-bleed** hero band (`shell.py:1436-1445`). Full-bleed is load-bearing: `body.setMaximumWidth(860)` with `ph.setContentsMargins(30,26,30,26)` centred between stretches would render the hero as an 860px card inset 30px — reproducing the exact box-in-a-box disease.

```python
page = QWidget()
pv = QVBoxLayout(page); pv.setContentsMargins(0, 0, 0, 0); pv.setSpacing(0)

hero = QWidget()
hero.setObjectName("hero")
hero.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)   # a bare QWidget else no-ops the bg rule
hv = QVBoxLayout(hero)
hv.setContentsMargins(30, 20, 30, 16)     # margins in PYTHON -- QSS padding is unreliable on a bare QWidget
hv.setSpacing(2)                          # (cf. #crumbRow/#spineRow/#railBar, which all do the same)
hv.addWidget(role_label("FF9 FIELD TOOLKIT", "overline"))         # $muted -- NOT a decorative token
hv.addWidget(wordmark := QLabel("Dream World IX")); wordmark.setObjectName("wordmark")
hv.addWidget(caption(f"Workspace · v{__version__}"))
pv.addWidget(hero)

row = QWidget(); ph = QHBoxLayout(row); ph.setContentsMargins(30, 26, 30, 26)
body = QWidget(); body.setMaximumWidth(FORM_W)
ph.addStretch(1); ph.addWidget(body, 1000); ph.addStretch(1)       # NOT 4 -- see below
pv.addWidget(row, 1)
```

`ph.addWidget(body, 4)` is a latent bug at `shell.py:1438` and must be fixed here: at 4:1:1 the body gets 4/6 of the width and reaches 860 only past ~1600px — at the 1280 default it renders **~822px** with 30%+ dead gutters. Measured with stretch=1000: 860 from ~900px on. Fix Home's existing line in the same commit.

```
QWidget#hero {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 $surface_2, stop:1 $bg);
    border: 0; border-bottom: 1px solid $border; border-radius: 0;
    min-height: $hero_h;                /* QSS min-height IS applied to plain widgets -> density-live */
}
QLabel#wordmark { font-size: 34px; font-weight: 600; color: $text; letter-spacing: 1px;
                  background: transparent; }
```

`_DENSITY`: `"hero_h": "132px"` / `"104px"`. Use `min-height`, not `setFixedHeight` — `_apply_density` (`:535-539`) only re-renders QSS and never rebuilds `_welcome`, so a Python height would go stale on a live toggle.

**The gradient is a whisper in the neutrals** (bg→surface_2 is 1.24–1.31 in dark, 1.16 in light) and that is correct — it raises the band's average brightness slightly and reads as a light source without shouting. Skip the radial vignette variant: surface_3→bg measures ~1.2:1 in the neutrals. Invisible.

**Tests touched:** none. `role="display"` then has zero users — leave the token (`test_workspace_style.py` doesn't pin it) or adopt `heading(t, 0)`.

**You'll see:** the app has a front door. The screenshot people share stops being a settings list.

---

## The token diff

### New palette keys: **none.**

Every proposal here uses keys that already exist in all 7 palettes, or adds *derived* keys — which `derive()` computes centrally, so the base dicts are untouched and `test_palettes_share_one_key_set` (`test_editor_theme.py:18`) never fires. That is the only extension point that doesn't tax every future palette.

### Changed palette values (Phase 0 + Phase 4)

| Key | LIGHT | DARK | Community |
|---|---|---|---|
| `muted` | `#626974` → `#5d646e` | unchanged | **NORD / DRACULA / SOLARIZED_DARK / GRUVBOX_DARK: lift until `muted/surface_2 ≥ 4.5`** (today 3.87 / 3.91 / 3.91 / 4.07 — sub-AA and untested) |
| `bg` | `#e8eaed` → `#e4e7eb` | `#1e2127` → `#141619` | leave canonical — Phase 4a's derived rungs fix their span without touching a hex |
| `surface` | `#f4f5f7` → `#f7f8fa` | `#262a31` → `#242931` | leave canonical |
| `surface_btn` | `#f4f5f7` → `#edeff2` | `#2b3038` → `#2f353e` | leave canonical |
| `field` | `#fbfcfd` → `#ffffff` | `#2b3038` → `#22262c` | NORD `#3b4252` → `#272c36` (**not** `#2e3440` = its own bg); GRUVBOX `#3c3836` → `#32302f`; others canonical |
| `hover` | `#dfe2e7` → `#dce0e6` | `#30353d` → `#363d47` | leave canonical |
| `pressed` | `#d4d8de` → `#d1d6dd` | unchanged | leave canonical |
| `log_bg` | unchanged | `#181b20` → `#101215` | leave canonical |

### Changed derived math (`theme.py:304-305`)

```python
out["surface_2"] = _mix(pal["surface"], "#ffffff", 0.10 if dark else 0.55)   # dark rung 0.05 -> 0.10
out["surface_3"] = _mix(pal["surface"], "#ffffff", 0.19 if dark else 0.80)   # dark 0.10 -> 0.19;
                                                                             # light 1.00 -> 0.80
```
The light change kills pure-`#ffffff` panels (`theme.py:23`'s own stated rule) in both light palettes. Stay **relative** — an absolute hex would inject a foreign hue into solarized-light's cream.

### New scale values (`style.py:_SCALES` / `_DENSITY`)

| Token | Value | Note |
|---|---|---|
| `_GRID` / `_GRID_COMPACT` | ints, exported via `space(key, density)` | the same numbers `_SCALES` stringifies — one source |
| `hero_h` | `"132px"` / `"104px"` | Phase 6; **both** profiles or `test_qss_density_profiles_both_substitute_cleanly` fails |
| `gb_margin_top` / `gb_pad_top` | → `"0px"` / `"0px"` in **both** | Phase 3; keep the keys, zero the values |
| `type_label`, `type_body` | **delete** | both 13px, both unreferenced |
| `type_mono` | **wire it** at `style.py:161` | replaces the hardcoded `12px`; the token's one legitimate reference |
| `radius_md` | **wire it** ×9 | declared since day one, referenced zero times |

### New roles / properties (QSS only, no palette work)

| Selector | Rule | Phase |
|---|---|---|
| `QCheckBox::indicator:focus, QRadioButton::indicator:focus` | `border: 1px solid $focus` | 0 |
| `QCheckBox::indicator:checked:focus, QRadioButton::indicator:checked:focus` | `border: 1px solid $accent_fg` | 0 |
| `QPushButton[role="quiet"]` + `:hover` `:pressed` `:focus` `:disabled` | see Phase 2a — **all five or it breaks** | 2 |
| `QPushButton#accent:focus` | `border: 1px solid $accent_fg` | 2 |
| `QLabel[mono="true"], QLineEdit[mono="true"]` | `font-family: "Cascadia Code", "Consolas", monospace` — **family only** | 2 |
| `QLabel[role="prose"]` | `color: $muted` — size inherits 13px | 1 |
| `QWidget#hero`, `QLabel#wordmark` | see Phase 6 | 6 |

### New widgets.py API

```python
FORM_W  = 860   # max width of a FORM column (label+field+Browse rows need the room)
PROSE_W = 400   # max width of a wrapping paragraph (~68ch at Segoe UI 13px, measured 5.84px/char)

class _Prose(QLabel):
    """Measure-capped prose. The heightForWidth override is MANDATORY: a vertical QBoxLayout's calcHfw
    asks hfw() at the FULL cell width, so a QGroupBox/QDialog reserves 2 lines then lays this out at
    400px needing 4 -- clipping half the text (measured: subclass w=440 h=96 need=96; raw cap h=48)."""
    def __init__(self, text, cap=PROSE_W, parent=None):
        super().__init__(parent)
        self._cap = cap
        self.setProperty("role", "prose"); self.setWordWrap(True); self.setMaximumWidth(cap)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setText(f'<div style="line-height:140%">{html.escape(text)}</div>')
        self.setAccessibleName(text)          # PLAIN -- text() leaks markup, verified
    def heightForWidth(self, w):
        return super().heightForWidth(min(w, self._cap))
    def sizeHint(self):
        s = super().sizeHint()
        return QSize(min(s.width(), self._cap), s.height())

def prose(text, *, cap=PROSE_W, parent=None): return _Prose(text, cap, parent)

def section(title, *, parent=None) -> tuple[QGroupBox, QVBoxLayout]:  # Phase 3, see above
```

`line-height` is the one thing QSS genuinely cannot do (verified: `heightForWidth` 96 → 96 with a QSS `line-height`; 96 → 147 via rich text). 140%, not 150% — 150% at 13px is 25.5px from a 17px base, loose for UI.

---

## Rejected

Each of these was proposed with confidence and refuted by measurement. Do not resurrect them.

| Rejected | Why |
|---|---|
| **Animate anything** (RunStrip, eased console splitter, cubic-bezier easing token, staggered rows, tab cross-fades) | The complaint came from a **still image**. None of it appears in a screenshot. And the proposed `(0.2,0,0,1)` bezier was sold as "a much sharper attack": measured initial velocity **0.008** vs OutCubic's **2.997** — it is 375× *gentler*. |
| **Bundle Inter** | Costs a `pyproject` package-data entry, an OFL notice, an unmeasured 1280px toolbar, and seven `QFont()` constructors that bypass QSS entirely — then renders the same flat hierarchy in a different face. Its headline justification (the dead 500 rung) has **one** consumer (`forms_qt.py:234`). |
| **Tone-only elevation / borderless cards carried by fill** | LIGHT's `surface_3` is `#ffffff` and its rungs step 1.046/1.043. Dies there. Dark gets depth from a widened span; light from a border and a gap. |
| **Gradient the buttons** | The "lit top edge" measured **+4/255** in dark (invisible), **exactly nil** in gruvbox (its border is already lighter than surface_btn+9%), and **inverted** in light (+0.32 the wrong way — a near-white top border on a near-white surface *deletes* the box). Bevels on four equal buttons produce four shinier equal buttons. |
| **Accent `builddoc.go`** | `shell.py:1058-1066` already ships an accented **Deploy F9** calling the identical `on_go()` (`shell.py:6699`). Two blue buttons 100px apart firing the same function. Law II both ways. |
| **Grey a diagnostic** | Two lenses tried to demote coopdoc's "engine: netsync MISSING" (`:266`) and builddoc's only *no-undo* warning into 11px muted. Demote explanations. Never demote the answer to "why is this broken". |
| **ChoiceCard (a QAbstractButton card per option)** | Builds the exact box-in-box being complained about, and its hover measured **1.00:1** against `surface_2` — invisible in dark. Its "selected fill" measured 1.01–1.12 in 4 of 7. Delete the container first; then a card has ground to stand on. |
| **`tabular()` / `tnum`** | Proven no-op: Segoe UI's digits are **already** tabular (all `zero`–`nine` advance 1104); `tnum`'s GSUB lookups resolve to **zero** latin-digit entries. The feature that touches them is `pnum`. The real move is a mono **family**. |
| **`$trim` identity token / a gold rule** | The key exists in all 8 palettes and is referenced by **zero** QSS rules. As written it renders in zero pixels — including in MIST — while taxing every future palette forever. And "no-op elsewhere" and "delivers gold rules" are mutually exclusive: any rule that *did* render `$trim` would draw a new element in all 8. |
| **MIST as the fix** | A navy/gold FF9 palette is a genuinely good *identity* idea and ships cleanly (all fences clear with margin). It is **not** the answer to "the cards don't read well" — it recolours the same undifferentiated box-in-box, arguably worse (gold puts more chroma in play than grey). And `derive()` aliases `info = accent`, so info/focus/accent are all gold — "one hue spent once" fails on arrival. Ship as flavour, after the hierarchy work. |
| **`text_subtle` for subordinate headers** | Fails 4.5:1 on `surface_2` in **all 7** palettes (2.55–3.20). It is a de-emphasis tier for inactive controls, not for text. |
| **A radius/spacing/token cleanup billed as the answer** | Collapsing 9 radii to 3 moves five values by one pixel. Land it silently (Phase 5); never bill it as beauty. |
| **A new palette** | Cannot fix hierarchy. |
| **Uppercase via QSS** | Qt has **no** `text-transform` (verified: a styled QLabel's text stays lowercase). Uppercase at the call site or accept sentence case. |
| **`QGroupBox::title { font-* }`** | Silently ignored (render-verified: ink identical at 13/600, 11/700+tracking, and 18/700). Colour is `::title`'s only lever. And `left: 0px` is **not** flush — `subControlRect` reports x==0 while the paint path adds +6. |
| **Cap the measure at 860 / "1107px → 420px"** | Font-metric artifacts. The offscreen QPA stubs the font DB and inflates advances 2–3×. Real: rb_test **511px**, the widest control **642px**, against ~1080px of content at the 1280 default. No emergency. |
| **`QPushButton:default` / `setDefault(True)`** | `CoopDoc` is a QWidget, not a QDialog, and there is no such rule (grep = 0). Doubly inert. |
| **`QTabWidget::pane { border: 0 }`** | `shell.py:1137` sets `setDocumentMode(True)`; `QTabWidget::paintEvent` returns early and never issues `PE_FrameTabWidget`. **The pane border in the screenshot does not exist.** Verified by pixel probe. |
| **`background: transparent` on QScrollBar** | Does **not** reveal the parent — four selector forms tested, all paint `$bg`. The universal `QWidget { background-color: $bg }` wins. It would newly *expose* 3px of dark stripe beside a 6px pill. |
| **De-border QPlainTextEdit / trees / lists** | `log_bg/bg` is **1.066–1.121** in all 7 palettes; the border is the console's sole container. Borderless needs a fill ≥1.3:1 first — a change to all 7 palettes, not a QSS edit. |

---

## Open questions for the user

**1. Do we ship Phase 3 (kill all 27 QGroupBoxes)?**
This is the big one and it is deliberately gated. Phase 1 gives you the same tab with zero borders removed. **Recommendation: screenshot Phase 1 first, then decide.** If it reads well, skip Phase 3 or defer it — a 27-site refactor across 7 files in a 16,925-line codebase is a long-lived branch, and any partial landing is *worse than today's consistent dull*. If it still reads badly, the box is proven to be the problem and the risk is earned.

**2. What is "under the lamp" on Build & Deploy?**
The vision says one lifted surface per screen. Phase 1 ships **none** — the crumb-row Deploy is the only accent and the page is flat type. That may be exactly right (a form's focal point is its verb), but it's a different design from "one lifted surface" and you should own the difference consciously. **Recommendation: ship it flat. If the page feels rudderless in the screenshot, the honest lift is the `role="card"` + a 4px accent left-stripe (measured 2.44–4.73 against `surface_2` in all 7 — the one delineation that survives light themes), applied to *one* element per screen and nothing else.**

**3. How far does the FF9 identity go?**
MIST (navy page, gold accent — theme.py's 8th palette) is ~25 lines, clears every fence with margin, and is a genuinely good idea. It is also completely orthogonal to the complaint. **Recommendation: ship it after Phase 4, as a *choice*, never as the default, and never billed as the fix.** The gold *rule* (`$trim` on a real edge) is a separate proposal that must be designed for LIGHT/NORD/DRACULA too — it is a new visual element in all 8, not a no-op.

**4. Mono: bundle Cascadia, or say Consolas and mean it?**
Cascadia ships with VS/Windows Terminal, **not** Windows. On a clean user machine the chain silently falls to Consolas, and your dev box lies about this. **Recommendation: say Consolas.** Bundling costs an OFL notice, a package-data entry, and the same packaging tax we rejected for Inter — for a face most users already have a decent substitute for. Consolas is a competent mono; the *register* is the win, not the specific letterforms.

**5. Do the community palettes stay?**
Seven palettes forced `derive()` into lowest-common-denominator math ("mix toward white" is the only op that trivially satisfies a Nord blue-grey, a Gruvbox brown, a Solarized cyan and a Dracula purple simultaneously) — and that math is exactly what bleaches the chroma out of the panels. **Recommendation: keep them, and make DARK the canonical hand-tuned target.** Phase 4a's approach — raise *our* derived rungs, leave their canonical hexes alone — gets the community themes 90% of the benefit for free. The only edits they need are the `muted` lift (an AA fix they need regardless) and the two `field` collisions. If they ever become a genuine drag, that is a decision for after the hierarchy work lands, not before.
