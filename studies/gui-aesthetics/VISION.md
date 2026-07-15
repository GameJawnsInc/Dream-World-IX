<!--
The art direction synthesized across the 10 lenses, 2026-07-15. Read PLAN.md for the work.
NB: this document is superseded on ONE point by CRITIC.md -- it bills "kill the QGroupBox"
as the highest-leverage change while also conceding the redesign is unjudgeable until the
style.py:126 selector bug is fixed. The critic won that argument; the plan gates Phase 3
behind a re-screenshot. Kept unedited as the record of the reasoning.
-->

# THE VISION

## 1. THE DIAGNOSIS

**Nothing in this app was ever allowed to be more important than anything else** — because every mechanism that could rank things (tone, type, space, a scarce accent) was built, tokenized, tested, and then never spent, leaving one instrument in the box: draw a 1px rectangle around it. A rectangle cannot rank.

The receipts converge from ten independent directions and they all say the same thing. The elevation ladder steps 1.04–1.17:1 (WCAG's *non-text* floor is 3:1) — so the fills do nothing and the hairline does everything, across 20 widget classes at 9 radii. Meanwhile: `role="h1"` is set by **nothing** (the 20px tier does not exist at runtime). `widgets.card()`, `heading()`, `status_chip()`, `tabular()` — **zero call sites**. `selection_bg` — derived, documented, **never referenced**. `space_1/3/4/6` — **dead**; every real gap is a hand-typed number, and every QGroupBox interior silently runs Qt's default 11/6 that no token file knows exists. `setObjectName("accent")` in builddoc and coopdoc — **zero**. `font-weight: 500` — resolves to Regular; there is no Medium face.

This is not an accessibility problem, a color problem, or a Qt problem. **A complete design system exists and the app doesn't use it.** So the border does all the work, and everything ends up the same shape at the same volume — which is exactly, precisely, what the user is looking at.

## 2. THE NAMED DIRECTION: **WORKSHOP**

A dark table. Tools laid flat on it, nothing in a case. **Exactly one thing under the lamp.**

The page is dark and mostly empty. Sections are not containers — a section is a small tracked-caps muted label, then its rows, then a generous gap before the next label. No fill, no frame, no floating caption cutting a line. Grouping comes from proximity and a shared left edge, the way it does in **Linear's settings** and **Zed's settings pane** — both of which abolished the titled box a decade ago and are the closest living relatives of this app's shape (nav tree left, stacked option groups right, dense, dark, technical).

On any screen there is **one** lifted surface, **one** accent object, **one** 20px title. Everything else is type on the table: 13px `$text` for what you act on, 11px `$muted` for what explains it. Controls are named in three words; the sentence lives underneath in grey, wrapped, capped at a readable measure. And because this app's entire subject is machine tokens — `4003`, `30110`, `ff9-XXXXXXXX`, `FF9CustomMap` — those are set in **Cascadia Code**, which is the one texture in the whole composition and the thing that makes it look like it knows what it is (**TablePlus**, **Proxyman**). The result is a document you read, not a form you fill.

The developer's test, every time: **is this under the lamp, or on the table?** Almost everything is on the table.

## 3. THE THREE LAWS

**I. A border must earn its existence.** Group by space and type first. A stroke is for things you can click into or type into — a button, an input, a tab, a focus ring. A *container* is not a stroke; it is a label and a gap. If you removed the border and the grouping still reads, the border was noise. It usually does, once the gap is right.

**II. One thing per screen is loud.** One accent object, one lifted surface, one page title. Accent is a *fill for the verb you press* — never a foreground for prose, never a highlight for a list row, never a hue you spend twice. If two things are shouting, one of them is wrong.

**III. A control gets a name; the sentence goes underneath.** Never put prose inside a widget. A radio is `Test slot 4003`; "quick + reversible, play via F6 → Warp" is an 11px grey wrapped caption beneath it, indented to the label's own column. Say each fact exactly once.

## 4. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Kill the QGroupBox. All 27 of them, in one pass.**

Replace it with `widgets.section(title)`: a `role="overline"` label (11px / 600 / +1px tracking / `$muted` — a token that already exists and is already unused), a **24px** gap above and ~8 below, content flush at one left edge, **no fill and no frame**. Pay the whitespace or don't ship it — every lens that deleted the box while leaving the page at `setSpacing(12)` measured *worse*, because an orphaned label floating equidistant between two groups is not a section.

What it does to the screenshot: the outer rectangle vanishes. The nested second rectangle in the Advanced drawer vanishes. With the one-line rider below, the three blue rects around the radios vanish. Build & Deploy stops being *two bordered boxes containing an equally-loud everything* and becomes **BUILD TO** / three named options each with a quiet line under it / air / **ADVANCED** / air / actions. Two borders and three phantom rects → **zero**. The page becomes a document. And do it everywhere at once — one borderless tab beside five boxed ones reads as unfinished.

Two things ride along free:

- **`style.py:126` is a live bug.** `QCheckBox:focus::indicator` puts the pseudo-class before the sub-control; Qt's parser then targets neither and it degrades to an unconditional `QRadioButton, QCheckBox { border: 1px solid $focus; }`. Every radio and checkbox in the app is a permanent accent rect — *that is the screenshot* — and radios have had **no focus ring at all**. Reorder to `::indicator:focus` (and add `::indicator:checked:focus { border: 1px solid $accent_fg; }`, since `$focus == $accent` in 6 of 7 palettes and a checked radio is filled `$accent`). One line. Ship it today; it costs nothing and you cannot judge any redesign until it's gone.
- **It fixes a latent AA failure.** `$muted` on `$surface_2` measures 3.87–4.07 in NORD / DRACULA / SOLARIZED-DARK / GRUVBOX — *sub-AA today*, uncaught because the contrast test only ever checks `bg` and `surface`. Delete the fill and every caption lands on `$bg`, where muted is tested and passes in all seven. **The aesthetic move is the accessibility fix.** Add the missing `surface_2` assertion so it can't come back.

## 5. WHAT NOT TO DO

These are the traps the lenses walked into. Each was proposed with confidence and refuted by measurement.

- **Don't animate anything.** The complaint came from a *still image*. A RunStrip, an eased console splitter, a cubic-bezier easing token — none of it appears in a screenshot. (And the proposed bezier was sold as a "sharper attack": measured initial velocity 0.008 vs OutCubic's 2.997. It is 375× *gentler*.)
- **Don't bundle a font.** Inter costs a packaging allowlist entry, an OFL notice, an unmeasured 1280px toolbar, and seven `QFont()` constructors that bypass QSS entirely — and then renders the same flat hierarchy in a different face. Its headline justification (the dead 500 rung) has **one** consumer.
- **Don't chase tone-only elevation.** LIGHT's `surface_3` is literally `#ffffff` and its rungs step 1.046 and 1.043. Every "borderless card carried by fill" dies there. Dark gets depth from a *widened span*; light gets it from a border and a gap. That asymmetry is why Law I says *space and type*, not *tone*.
- **Don't gradient the buttons.** The "lit top edge" measured **+4/255** in dark (invisible), **exactly nil** in gruvbox, and *inverted* in light — a near-white top border on a near-white surface deletes the box instead of lighting it. Bevels on four equal buttons produce four shinier equal buttons.
- **Don't promote `builddoc.go` to accent.** `shell.py:1059` already ships an accented **Deploy F9** in the crumb row, on every tab, calling the identical `build_deploy.on_go()`. Accenting `go` puts two blue buttons 100px apart firing the same function. **The crumb owns the primary; the bottom row recedes.** Law II both ways.
- **Don't grey a diagnostic.** Two lenses tried to demote coopdoc's "engine: netsync MISSING" and builddoc's only *no-undo* warning into 11px muted. Demote explanations. Never demote the answer to "why is this broken."
- **Don't nest a new card inside the surviving box.** The ChoiceCard proposal builds the exact box-in-box being complained about, and its hover state measured **1.00:1** against `surface_2` — invisible. Delete the container first; then the card has ground to stand on.
- **Don't ship radius/spacing/token cleanup as the answer.** Collapsing 9 radii to 3 moves five values by one pixel. `tabular()` on Segoe UI is a *proven no-op* (Segoe's digits are already tabular; `tnum` touches zero Latin digits — the real move is a mono **family** on ids and paths). A new palette cannot fix hierarchy. All of this is hygiene: land it silently, never bill it as beauty.

**The meta-law, learned the hard way here:** the static reading of `style.py` said the radio borders were impossible; three renders said they were real; the render was right. **Measure the pixels. Don't reason about them.**
