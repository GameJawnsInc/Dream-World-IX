# ROUND 4 — the menu, and what survived verification

> **Generated 2026-07-15** by a commit-framed workflow (50 agents, 9 lenses, ~6M tokens): recon →
> generate → *make it work* → judge → synthesize. The frame was inverted on purpose — see
> [STATE.md](STATE.md)'s last section for why a refute-framed harness converges on correctness and never
> on beauty. **The body below is the workflow's output, unedited.** This header is the human-side
> verification, and it changes the headline.

---

## ⚠ VERIFICATION — read before acting on anything below

I re-measured the round's load-bearing claims myself. **Three are real and valuable. The headline is false.**

### ❌ FALSE — "603 pixels of `#787878` across the top of the work area, in no palette, identical in all 8"

**This is the #1 direction's headline, the thing it says to ship first, and it does not reproduce.**
Measured `#787878` = **0 pixels** in every configuration I could construct:

| configuration | `#787878` |
|---|---|
| the real `Workspace` shell, dark, 1280×800 | **0** |
| a `QTabWidget` + `setDocumentMode(True)` + the app sheet | **0** |
| the same with **no stylesheet at all** (raw Qt default) | **0** |
| the same with `setDrawBase(False)` | **0** |
| **native** platform (`windows11` style), sheet and no-sheet | **0** |

I specifically checked the most likely escape hatch: `QT_QPA_PLATFORM=offscreen` forces the **Fusion**
style while the real app runs **windows11**, so the offscreen harness can lie about *what Qt paints*, not
only about text advances. That is a genuine new harness lesson and it is now written down — but it does
not rescue the claim: the grey is absent under **both** styles.

`drawBase()` **is** `True` by default even under documentMode — that sub-claim is true. It simply paints
nothing visible here, because the QSS pane and tab rules already own those pixels.

**This is round 2's failure mode exactly, in new clothes.** Round 2 invented a horizontal-scroll
emergency out of a stubbed font DB; round 4 invented a 603px grey emergency. The workflow prompt
*explicitly warned about the first one* and the agents produced a fresh instance anyway. **The lesson is
not "check the fonts". It is: a number nobody re-derived is a rumour, however precise it looks.** 603 is
a very persuasive number. It is not a real one.

The rest of THE PLATE (the two same-colour dividers, the tab strip fusion) may still be worth doing —
but it must be re-argued from scratch, because its headline was load-bearing and is gone.

### ✅ TRUE — the hero's overline is sub-AA in 8 of 8 palettes, and it is my bug

`hero.py:138` inks the overline in `d["text_subtle"]`. Measured against `surface_2` (the plate's top
gradient stop): **3.20–3.59 across all 8** — sub-AA at 11px DemiBold. `muted` fixes all 8 (**5.31–6.06**).

PLAN.md:722 already forbids this, permanently and in writing: *"`text_subtle` for subordinate headers —
fails 4.5:1 on `surface_2` in all 7 palettes. It is a de-emphasis tier for inactive controls, **not for
text**."* I shipped the front door inked in a token my own study had already killed, in the same arc.

Nothing caught it because `audit_contrast.py` reads ink from `w.palette().color(w.foregroundRole())` — a
QLabel API — and the hero is 100% `QPainter` with no QLabel children. **The instrument is blind to the one
surface built to be looked at.** That is the 8th instance of this arc's defining pattern: *a fence that
covers most of the app just moves the bug to the rest.*

### ✅ TRUE — Home promises a primary action in a docstring and has never drawn one

`shell.py:1591`'s docstring: *"the ONE primary action on the page (Journey ▸ Open, the recommended front
door) renders in the accent colour."* **All ten call sites pass `False`.** The branch
`if primary: b.setObjectName("accent")` is live code nothing reaches. A claim no pixel honours.

### ✅ TRUE — OQ#2's prepared answer decayed, and my own commit did it

The waiting answer to *"what's under the lamp on Build & Deploy"* was a 4px accent left-stripe, recorded
in PLAN.md as **"2.44–4.73 in all 7"**. Re-measured at HEAD across 8: **nord 2.12** · sol-dark 3.06 ·
dark 3.85 · sol-light 4.31 · light 4.38 · gruvbox 4.48 · dracula 4.73 · mist 7.09. **Floor 2.12 — under
the 3.0 non-text floor.**

Traced to `0dcb2c4` (mine): the contrast sweep deepened nord's accent `#5e81ac → #56779e` so a white
button label would clear 4.5 — and the same move dropped the stripe 2.44 → 2.12. **One token, two jobs,
opposite directions.** I fixed a text-contrast bug and silently broke a delineation candidate in the same
edit. The round's proposed instrument for this is right and worth stealing regardless of direction: a
**ratchet** (record the measured floor, assert it never worsens) rather than a fence or an xfail.

### ◐ CODE-CONFIRMED, render unverified — the breadcrumb's selector-less sheet

`shell.py:335` and `:358` both call
`setStyleSheet(f"background:{pal['surface']};border-bottom:1px solid {pal['border']};")` — **no
selector**, so Qt applies it to the widget *and cascades it to children*. Same class as defect #4 (the
transparent container that left the newcomer's CTA unfilled in all 8). The claimed consequence — that
child labels wear a stray underline while the clickable ancestors escape via their own `border:none` —
follows from known Qt behaviour but I have **not** rendered it. Verify before believing the specifics.

### The scoring, for what it is worth

| direction | lens | beauty | avg | "ship first" |
|---|---|---|---|---|
| PLATE | restraint | 7.83 | 34.83 | 3/3 |
| LEDE | home | 7.83 | 34.0 | 3/3 |
| INTAGLIO | material | 7.83 | 33.67 | 3/3 |
| NAMEPLATE | lamp | 7.67 | 32.67 | 3/3 |
| CASEMENT | chrome | 7.17 | 32.5 | 3/3 |
| COLOPHON | type | 6.67 | 33.0 | 3/3 |
| REGISTER | data | 6.67 | 31.33 | 2/3 |
| DRAWN | motion | 6.17 | 31.5 | 2/3 |
| KEYLINE | icons | 6.33 | 31.67 | 1/3 |

**Every direction scored `ships_with_the_fix` and no direction scored below 6.17 on beauty.** Treat that
compression as evidence about the *frame*, not about the ideas: a round told to commit and to fix rather
than veto will not produce a loser. That is the intended trade — round 2's frame produced no winners —
but it means the ranking discriminates weakly, and the judges' own words do the real work. Read those.

**Its own most honest sentence, which I endorse:** *"this app does not lack a beautiful idea — it has
four unspent preconditions, and each generator found a different one."*

---

# ROUND 4 — THE MENU

*What to do next, ranked and committed. Nine directions were generated, engineered, and judged; this merges them into four real options plus a tail. Costs are honest. Hygiene is labelled hygiene.*

---

## 1. THE HEADLINE

**Ship THE PLATE first — the chrome subtraction — and ship it because it is the denominator.** While three rounds carefully tuned 1.2:1 hairlines, Qt has been drawing **603 pixels of `#787878` across the top of the work area** that is in no palette, never re-tints, is byte-identical in all 8 themes, is invisible to every grep, is green under all 55 tests, and measures **3.65:1 in light, 3.60 in solarized-light, 4.03 in Mist — 2.7×–2.9× louder than any line this app draws on purpose.** Two of the four rules the app *does* draw up there have the identical colour on both sides (contrast 1.000, measured at y=56 and y=88); a third is parked on the wrong widget and its truth is conditional on a band that auto-hides. Phase 1 is four QSS declarations. Phase 2 is one Qt call (`setDrawBase(False)`) plus a de-boxed tab strip that fuses to its page. The whole thing is under a day, it is the largest silhouette change available in the app, and it *funds* SIGNET rather than competing with it — "one corner, once" is a claim about scarcity, scarcity is a ratio, and the cheapest way to make gold rarer is to stop drawing lines that are not gold. **Then put something on the clean plate: the nameplate (menu #2), because a page that finally has one honest edge above it and still has no title is a plate with nothing on it.**

---

## 2. THE MENU

### #1 — **THE PLATE** *(merges PLATE + CASEMENT)*
**Thesis:** the chrome draws four bands where the app has two ideas and one conditional inset, and the loudest lines up there are ones the app never authored.

**Why it is beautiful, concretely.** Look at the top 126px: one unbroken field of `#262a31` cut by three horizontal rules, two of which have the same colour on both sides. Those are not boundaries, they are scratches on a plate. Delete them and the composition inverts — the chrome becomes ONE plate, the rail's bottom edge stops being the fourth stripe in a stack and becomes *the* line between tool and work, and the hero stops being the fifth horizontal band in a vertical run. Same argument one level down: `setDocumentMode(True)` is already set — that call exists to say "these are not chips, they are tabs" — and the QSS boxes them anyway.

**Phases:**

| # | phase | size | what you'll SEE |
|---|---|---|---|
| 1 | **THE PLATE.** `style.py`, 4 declarations, zero Python. Drop `border-bottom` on `QToolBar` and `#crumbRow`; **re-home** it to `#spineRow` as a `border-top` (keep its bottom — the spine is 1.046 in light and cannot carry itself by tone, so it gets both edges and becomes the one delineated inset); leave `#railBar`'s alone — `surface:bg` = 1.055–1.155 is the one pair tone genuinely can't carry. | trivial | The most visible change here, and it's four lines. The top of every screen stops being a stack of slats. On Home the hero becomes the only horizontal band on screen — which is what SIGNET always claimed it was. |
| 2 | **THE STRIP.** Must land whole. (a) De-box `QTabBar`: transparent fill, `border: 0`, no radii, `$accent` underline on `:selected`, and **re-home the focus ring to an explicit `border-bottom`** (`border-color: $focus` renders 0px once `border: 0` — proven). (b) **`widgets.tabs()`** — a factory setting `setDocumentMode(True)` *and* `tabBar().setDrawBase(False)`; adopt at `shell.py:1173` and `savedoc.py:61`/`:420` (savedoc's two never set documentMode at all). (c) `setFrameShape(NoFrame)` on the three stragglers: `shell.py:1176` (the Editor — recon 1's #1 hours-spent surface), `modelsdoc.py:157`, `savedoc.py:520`. | small | `#787878` goes **603 → 0** in every palette. The selected tab renders `+0..+30 bg / +31..+32 accent / +33+ bg` — genuine fusion, not a chip floating above its page. 2c is not optional: it is the last line between the selected tab and its page, so 2a without it ships the headline claim broken. |
| 3 | **THE BREADCRUMB.** Delete both bare `setStyleSheet` lines at `shell.py:335` and `:358` — **no replacement** (a Python QWidget subclass without `WA_StyledBackground` does not paint the QSS background; `#crumbRow` shows through, and the bar goes theme-live for free). Then a `QPushButton[role="crumb"]` rule: ancestors `$muted`, hover `$text`, keep the focus ring. | small | Fixes live defect #8 and does it by subtraction. A selector-less sheet re-parses as `* { }` and out-ranks the app sheet: the leaf label, the chevron and the type icon each wear a 94px stray underline six pixels above the real rule — while the clickable ancestors escape it via their own `border:none`. **The app underlines the thing you cannot click and flattens the things you can.** Deleting it inverts the row back: the trail recedes, and the room you are standing in becomes the loudest thing in it. |
| 4 | *(optional)* **THE EDGE.** `_edge_token(pal, (surface, surface_2, bg), target=3.0)` mirroring `_text_token`; `QWidget[plateFoot="true"]` + `QSplitter::handle { background: $edge }`. Add `"edge"` to `_DERIVED_KEYS` or `derive()` early-returns and `qss()` KeyErrors. | small | The one surviving line goes 1.25–1.49 → **3.10–4.39**, and the splitter handles become the plate edges they literally are. |

**The measurement.** Both deleted rules: contrast **1.000**. Fusion's base: `#787878`, 3.60–4.03 vs bg in light/sol-light/mist against deliberate borders at 1.19–1.49. The un-chosen scroll frame: `#b3b5b7` = **1.71:1 in light = 1.4× louder than the app's own border**, wrapped around the Editor, never re-tinting. **Where it dies: nowhere — and compressed ramps make it *stronger*,** because a rule between two 1.046 tones is definitionally separating nothing. Light and solarized-light are where the uncommissioned grey is worst. Free fix: solarized-light's unselected tab label is `muted:surface_btn` = **4.37, sub-AA, shipped today** → lands at `muted:bg` = 4.66 after, by deletion.

**Contract:** neutral, zero renegotiation, and it funds SIGNET.
**Cost:** phases 1–3 ≈ one day. Phase 4 ≈ one more with its fence.
**The fences it earns** (and these must be **widget-state** fences, not string greps — 603px of grey and a 0-pixel focus ring both live where a grep cannot go): assert every `QTabBar` has `drawBase() is False and documentMode()`; assert every `QScrollArea` is `NoFrame` (7 of 10 pass today); assert no band declares a `border-bottom` if any **reachable** successor paints the same token, *accounting for bands that auto-hide* (a naive adjacency check passes `crumbRow` and misses the entire bug); assert no state rule relies on `border-color` when its base rule sets `border: 0`.

**Reject its own slogan.** "Delete every rule whose two sides are the same colour" proves too much — it would delete the toolbar separators the proposal itself refuses to cut, and the hairline every serious IDE draws between same-coloured chrome. A divider's job was never to separate two *colours*; it is to **group**. Keep the eye, replace the argument. **New law: a border belongs to the band whose existence it is conditional on.**

---

### #2 — **THE NAMEPLATE** *(merges NAMEPLATE + COLOPHON)*
**Thesis:** every working screen names its subject once, at display size — and the app already computes that name on every screen and throws it away.

**Why it is beautiful, concretely.** `_mount_form` computes `tab = entity.get("name") or …` — the exact name of the thing you are editing — and spends it on a tab label truncated to 24 chars. All six `_header` sites are paired with a `_set_editor_tab()` carrying the panel's name. Every doc implements `crumb_label()`. `role="display"` (24px/700/`$text`) is fully spec'd, derived on all 8 palettes, and renders **zero pixels**. At every `_header` site the app sends the SUBJECT to the tab strip and the BREADCRUMB to the header — **it computes both halves of a nameplate and posts each to the wrong address.** Meanwhile builddoc/importdoc/coopdoc/savedoc/battledoc stamp **zero headings between them** across 25 cards, and their card titles are 11px overlines — *smaller than the body they label*. These screens are not flat; they are typographically **inverted**.

**Phases:**

| # | phase | size | what you'll SEE |
|---|---|---|---|
| 1 | **THE WEIGHT** — *hygiene, and I'm labelling it as such.* `role="label"` `font-weight: 500 → 600`. Segoe UI ships no Medium; 500 renders **byte-identical** to 400 (advance 62.55 == 62.55; identical pixel buffers). `forms_qt.py:234` calls it "the type ramp". Fix the lying comment. Fence: assert every declared weight is in the natively-measured cut list — the real buckets are **[100–300][350][400–500][550–650][700–800][850–950]**, so 550 is the first weight that reaches Semibold. *(No render test can catch this: the suite runs offscreen, which stubs the font DB. The fence must encode the cut list as data.)* | trivial | Best diff-to-visible ratio in the round. Every form label in the Editor — the app's #1 hours-spent surface, zero touches across three rounds — goes from indistinguishable-from-body to scannable. |
| 2 | **THE NAMEPLATE.** `widgets.nameplate(kicker, name, note)` = overline kicker + the name + a capped note + a 1px rule. Reshape `_header(kicker, name, note)` at **all six** sites (1899/4245/4324/4368/4783/5861 — the journey site is inverted). Harden as a **`NameLabel` with resize-elide**: pin `sizeHint` to the full string, return `advance("…")` from `minimumSizeHint`, elide in `resizeEvent` (min width **816 → 48px**, hscroll gone at every pane width 300–900, 4 resize events, **no recursion** — precisely *because* the hint stays pinned, so eliding never triggers a relayout). Keep `QLabel::paintEvent`; do not custom-paint — the full text must stay in `setAccessibleName` + tooltip. Also `doc_host_lay` 14px (hand-typed, off-grid) → `widgets.page_margins` (24). | small | The Editor panel's crown goes from a 15px h3 (**1.15×** body) to **1.76–1.85×**. The grey `alexandria_gate · npc:2` string that passed for a title becomes a quiet kicker above a name that is actually a name. |
| 3 | **CROWN THE DOCS.** Five docs open with a nameplate. **Zero per-doc judgement and zero new state:** name = `crumb_label()` (every doc has it, `_sync_crumb` keeps it truthful on every tab), kicker = `self.kind`. Modelsdoc's browsers are `page_margins`-excluded, so its nameplate goes in the detail pane — promote `modelsdoc.py:112`'s existing h2. | medium | Build & Deploy — the screen OQ#2 names — goes from an untitled stack of six cards to a screen that says what it is about. **This is the answer to OQ#2** (see below). |

**The measurement.** `$text:$bg` = **5.42 (sol-light) .. 14.26 (mist)** — clears AA-normal in 8/8, and at 26px only owes the 3.0 large floor = 1.81× margin. **Light is its best palette (13.74).** It survives compressed ramps because it is `$text` at a size: zero chroma, zero elevation, nothing asked of a ramp whose top rung is `#ffffff` by construction. **Where it dies: nowhere.**

**The one open decision — the face. I commit to Sitka Display 26/400, and I flag it as the taste call.** Within one family, nominal ratio == optical ratio exactly (Segoe 24/13 = 1.85 nominal, cap 16.80/9.09 = 1.85 optical). Across families it does not: an 18px serif crumb declares 1.38× and delivers **cap 1.23× — optically identical (0.02px) to an h2 the app already had.** Sitka ships six optical sizes and this is what they are for: **hero Banner 40 (2.69×) → page nameplate Display 26 (1.76×) → h2 16 → body 13 → caption 11.** The hero's 40px currently has a 2.5× hole under it with 24 and 20 sitting unstamped; filling it turns the front door from an outlier into the crown of a real ramp. **But not on the crumb** — a path's tail inflated 23% stops reading as a path; the honest expression of that idea is a title row, which is what phase 2 is. One name-object per screen, and it is the crown. Fallback is one property: drop the `font-family` line → Segoe 24/700.

**Contract:** the size is neutral and owes no argument. The serif is the seam. I argue it is **not** a renegotiation: `hero.py:141` — *"the wordmark is `pal['text']`, NEVER gold. A gold 'Dream World IX' is a fan-logo"* — SIGNET **itself** separated the serif from the gold and kept only gold as identity. FF9's UI is not serif; Sitka is a Carter text family shipped with Windows since 8.1. Extending the neutral half is neutral beauty. Fence the law as a **test**, not a comment (`hero.py:138` proved a comment cannot hold a law — it drifted from its own explicit spec inside one round): *exactly one rule in the rendered sheet may contain "Sitka", and it must be `role="name"`.*

**Cost:** ~2–3 days. Phase 1 is an hour.
**Also fix while in there:** delete `_home_row`'s docstring sentence promising a primary action all ten call sites pass `False` for; retire `type_display`/`type_h1`/`role="display"`/`role="h1"`/`heading()` (zero call sites, zero pixels) and promote h3's 15px literal to `$type_h3`. Fix `test_workspace_style.py:69` while you're there — `assert "20px" in css` has been matching **a button's padding**.

---

### #3 — **INTAGLIO** — one light, from above
**Thesis:** this app's fills cannot carry elevation, so give every object a 1px lit top and shaded foot derived from `$border` — and the material becomes the button ladder that already shipped and has never rendered.

**Why it is beautiful, concretely.** Right now the app is not flat-and-minimal, it is *unfinished*, and there is a number for it: **in LIGHT, `surface_btn` and `surface` are the same hex — a toolbar button's fill is 1.0000 against the toolbar.** In Mist, a button in a card is **1.002**. In nord and gruvbox, 1.024/1.025. In solarized-dark, `field == surface` **exactly**. On the app's 29 card surfaces, in 6 of 8 palettes, the only thing saying "this is a button" is a 1px border measuring 1.14–1.46 against a 3:1 floor. The app claims a light source — its whole elevation ladder is "higher = lighter" — and never draws the light. And rendered natively: today `Build` (default) and `Revert` (quiet) are near-identical outlined rectangles, because the fill separating them is 1.076. **The three-rung button ladder that shipped last commit is a two-rung ladder the code merely asserts.** Intaglio is what makes it true.

**The fix that makes it work — anchor on `$border`, not the fill.**
```python
for _k, _src in (("border", pal["border"]), ("accent", pal["accent"])):
    out[f"{_k}_lit"]   = _mix(_src, "#ffffff", 0.18)
    out[f"{_k}_shade"] = _mix(_src, "#000000", 0.18)
```
Four tokens. `$border` sits **above** its fill in all 6 dark palettes and **below** it in both light ones, without exception — it is the app's one already-mode-aware token. So emit both edges from every rule and let the palette's own border eat the one it cannot hold. **No `if dark:`, no solver, no palette edits.**

**Phases:**

| # | phase | size | what you'll SEE |
|---|---|---|---|
| 1 | **THE EDGE.** 4 tokens + ~8 rules. Buttons: lit top / shaded foot. Inputs: the **inverted** pair — raised and cut are the same two colours in opposite order. `:pressed` inverts the edge; the material performs the interaction at the cost of one rule and zero motion. `#accent` **must restate** its edges (a later `border:` shorthand resets the per-side colours — probed: it lost its lit top). `#search` restates the CUT pair. `[role="quiet"]`'s existing shorthand makes it **flush with the plate for free** — accent = raised+lit, default = raised, quiet = flush, and the ladder finally renders. | medium | The largest visible change in the round, everywhere at once. **Free win: `forms_qt.py` — recon 1's #1 target, zero touches in three rounds — gets the entire material upgrade without being opened**, because its zero factory adoption means it is built from plain `QPushButton`/`QLineEdit` and inherits the app sheet. |
| 2 | **THE CONSOLE.** Both panes take the cut edge on `$log_bg` (which *is* the well material, finally named — **drop the derived `$well` entirely**); `#consoleHead` takes `border-top: $border_lit` = the plate's lip; kill the bottom radius; spend `space_2`. Radius fence `{3,4,6,8,9,11}` → `{0,…}`, with 0 documented at its site: *a hole in a plate has no rounded floor.* | medium | The surface you stare at during every build stops being two rounded rectangles floating in a panel and becomes a hole in the app with a lit lip above it. |

**The measurement.** Carrier delta vs `$border` at t=0.18: **light FOOT d40 / cr 1.508 · sol-light FOOT d40 / 1.507 · sol-dark d43 · mist d38 · dark d35 · nord d34 · dracula d34 · gruvbox d33. Range d33–d43, every palette, no exceptions.** Edge-vs-fill: light `shade:btn` **2.017**, dark `lit:btn` 2.164.

**Where it dies — it doesn't, and LIGHT is its strongest palette.** This is the **first elevation idea in this study that survives light**, and the reason is structural: an edge doesn't ask the ramp for anything, while light's `surface_3` *is* `#ffffff` and its rungs step 1.043/1.046. Fill-anchored, light gets d8=5 on a card — a no-op in the two palettes that needed it most. **Do not ship the fill-anchored version.**

**Contract:** neutral. Every token is a mix of a fill with white or black — achromatic by construction, so it cannot carry identity even by accident. The one chromatic rule is `$accent_lit` on the one primary button (the accent hue brightened; already spent on `accent_hover`). And note the expired rejection this walks through, out loud: the gradient rejection's *hierarchy* leg ("bevels on four equal buttons produce four shinier equal buttons") **expired with the button ladder at `53d2ed9`.** A lit edge on the ONE accent button is not the proposal that was refused.

**Cost:** medium, ~2 days plus a native render pass. **The highest-variance item on this menu.** The proposal's "one 1px line, on one edge" defence was measured on the fill anchor and does **not** survive the border anchor — the non-carrier lands at d13–17 in 6 of 8, so dark themes get a lit top **and** a shaded foot. That is Win95's grammar. Keep `t` as the lever (0.18 → 0.14 lands d26–34 dark / d31 light, all above 1.36) and expect to spend it. Also: "the physics does the selection" oversells a top/bottom-only stylization as inevitability; and the `$border` above/below-fill invariant is true 8/8 **by convention and asserted nowhere** — fence it.

*(Placed above LEDE despite scoring 0.3 lower, on recon 1's structural finding: the arc's visual investment is inversely correlated with time spent. LEDE improves the 5-second surface that already got SIGNET; INTAGLIO reaches every surface you touch for three hours, including the one nothing has ever touched.)*

---

### #4 — **THE LEDE** — Home has ten doors and no pointer
**Thesis:** the app already promises a primary action on Home, in a docstring, and has never drawn it — so draw it, using the signet's own elbow at half the ink.

**Why it is beautiful, concretely.** `shell.py:1594`: *"the ONE primary action on the page (Journey ▸ Open, the recommended front door) renders in the accent colour."* **All ten call sites pass `False`.** That is defect class #9 — the same shape as the seven the contrast sweep found: a claim no pixel honours. SIGNET built a title page and handed off to an index: 10 identical cards, 4 grey paragraphs, one flat column running 2.17 screens, none of which is the answer to the question Home exists to ask. And the two marks rhyme: `hero.py`'s docstring says *"An FF9 window has four corners. We draw one."* **The lede draws the second, on the same axis, 200px down.** An FF9 menu IS a bordered window containing a column of choices with one cursor on the one you're on. Home has the window and no pointer.

**Phases:**

| # | phase | size | what you'll SEE |
|---|---|---|---|
| 1 | **THE MEASURE.** `PROSE_W 620 → 420` — measured on Home's own strings at the real 13px face (intro 5.670 px/char → 74.1ch; `_start_note` 5.820 → 72.2ch; **430 lands intro at 75.8ch and fails its own fence**). Add **`CAPTION_W = 620`** and pass it to `option()` — the 11px face runs 4.643–4.978 px/char, so 620 there is 125–133ch, *worse* than the body's 109ch at the same number. **That is the receipt for why one px cap was never a measure.** Result: Build & Deploy and Co-op's option rows don't move; the approved surface stays approved. Plus the spine indent (3 lines: *"The project spine — top-down"* names journey ▸ campaign ▸ field as containment and draws three equal siblings). | small | Home's prose goes from 108ch at 1280 / 154ch at 1600+ — a ribbon the eye loses the return sweep on — to a 75ch typeset column on the hero's own axis. Nothing crosses the fold from this alone; the page stops looking *filled* and starts looking *set*. |
| 2 | **THE LEDE.** Extract `hero.py`'s corner path into `signet_elbow(p, x, y, arm, up, gold, a_from=255, a_to=70)`; `HeroBand` calls it at the wordmark, a new `LedeCard(QFrame)` calls it at its title. **One function, two call sites — the code states the thesis.** `LedeCard.paintEvent` calls `super().paintEvent(ev)` first, then paints gold (verified: `QFrame[role=…]` matches the subclass — Qt type selectors match subclasses, only `.QWidget` is exact-class — and the QSS fill lands byte-exact in all 4 palettes tested). Therefore `LedeCard` just **sets `role="card"`** and paints the mark: **zero `$gold` key, zero QSS change, zero palette key, zero constant move, zero cycle question.** State machine already exists (`_current_target()` + `_refresh_getstarted`'s `show` predicate). Host it as a `_TRANSPARENT` QWidget inserted as body's first child (so it inherits `_axis()` for free — never write the second formula, a parallel one was +30px off at 724) and rebuild it in `_refresh_home_status`. | medium | The headline. The first thing under "Dream World IX" is ONE card with a gold corner, a 15px title, and one accent button naming the actual next thing for *your* state ("Fork your first field" / "Continue HEARTH"). The eye lands on the wordmark, drops to the lede, stops. |

**The measurement — and it picks both the colour and the shape.** Against `surface_2`, gold is **4.710 (sol-light) .. 6.964 (mist)** — the only delineation clearing the non-text floor in all 8, because **it is the only candidate not sampled from the surface ramp.** Accent is 2.118 (nord, fails) .. 7.095. The tint lift is 1.043–1.182 (dead). **That is also why it lives in LIGHT where every elevation idea has died: the compressed ramp is irrelevant to a constant** — gold measures 4.837 in light, within 0.4 of its darkest showing. Ink: 170px of 1px rule at the hero's 255→70 dissolve = **~109px effective vs the hero's ~220 = 0.49×.** The QSS-only full-border alternative is **625px = 2.8×** — the echo out-shouting the mark. **Subordinate by construction.**

**The kill shot, and the law it mints.** The first draft was a gold **left stripe**. `gold↔warn` is **ΔHue 0.3–3.3° and CR 1.073–1.265 in 7 of 8 palettes** — they are the same colour — and `$warn`'s only shape in this app is a left stripe, and the warn banner shares a splitter with Home. It would have shipped *"your build has warnings"* as *"your next action"*. **A coloured left stripe is the status grammar in the status colour; a turned corner is a shape the status grammar has never used, and it is already ours.** New permanent law: **gold may never be spent as a `border-left`-only stripe.** Fence it.

**Contract: this is the only direction that touches identity, and I argue it does not renegotiate.** *"One corner, once, or it's a costume"* forbade an ornament **repeated**. This is not a second ornament — it is the same mark, from the same extracted function, at half the weight, once per page, only when there is a next action to name. Zero palette keys, zero QSS keys: the inverse of `$trim` on both axes. But the honest reservation stands and it is the only thing left in this direction: **nobody has seen the elbow at 1/3 scale on a card.** The ink math says subordinate; whether a second gold corner 200px down reads as an echo or a scuff is an eye's call.

**Fences:** `contrast(gold, surface_2) >= 3.0` (floor 4.710). And `contrast(accent, surface_2)` as a **ratchet** — record the measured floor, assert it never gets worse — not an XFAIL. A ratchet is the right instrument for a known gap you are deliberately not fixing, and it is exactly what would have caught nord's silent 2.44 → 2.118 decay at `0dcb2c4`. Fix the stale docstring (2.44 → 2.118). Assert `PROSE_W / 5.820 <= 75`.

**Cost:** ~2 days. **Warning:** "cut 216 words → ~110" is where good plans go to die. Write the copy; don't plan it. **Cut from it:** the recession (de-carding Home's 7 rows) — see §3.

---

### #5 — **REGISTER** — the data gets tiers of voice, the chrome gets quieter
**Thesis:** a build log is a flat grey wall in which a traceback and forty lines of `wrote …` are the identical ink, while a selected tree row is painted in the same full-saturation accent as the Deploy button, permanently, three feet from the gold signet.

**The one move worth taking on its own — the selection stops shouting.** `QTreeView::item:selected { background: $accent }` gives persistent state the treatment reserved for the primary CTA. Phase 1 takes accent **away** from the work surface and leaves the CTA as the only full-accent object in the window. **This is the one place SIGNET's own "one corner, once" was written down and never applied,** and it enforces the contract by subtraction.

**Phases:**

| # | phase | size | what you'll SEE |
|---|---|---|---|
| 1 | **THE SELECTION.** `$selection_bg` fill + a 3px `$focus` rail; **reserve the rail as `border-left: 3px solid transparent` on the unselected item** or every row jumps 3px on select. Mint `selection_rail = _focus_token(accent, selection_bg)` — zero new math, the existing function pointed at the ground the rail actually sits on: nord **2.65 → 3.19**, sol-dark **2.87 → 3.13**, the other 6 unchanged. Fix `_focus_token` to return the **best-scoring** candidate rather than the last (3 lines — it currently gives up silently). **Ship in the same commit:** `QListWidget#paletteList::item:selected` keeps the full accent via an id selector (0,1,0,1 beats 0,0,1,1) — *in a transient modal the selection IS the UI; in a tree it is persistent state.* Pin `::item:selected:hover`. | small | Every click in the tree. The selected row becomes a tinted well with a crisp rail instead of a saturated slab. **This also un-blocks the icon fix in §2's tail: on `selection_bg` the Selected-mode tint must be `$text`, not `accent_fg`.** |
| 2 | **THE LOG.** The well: `LIGHT.log_bg #e1e3e7 → #fbfcfd` — **the palette's OWN `field` hex**, already in the dict, described there as "just-off-white", so it honours the palette's own "not glaring #ffffff" law *and* doesn't collide with `surface_3` (which IS `#ffffff`). min **5.29** across 5 registers. `SOLARIZED_LIGHT → #fdf6e3` (base3), min **4.99** — and it survives *because it rises*: `== bg` scores 4.39 and fails. Darks untouched. Then `_log(text, kind)` via `QTextCursor` + `setCharFormat` + `insertText` — **never `appendHtml`**, which switches the document to rich text and mangles any stdout containing `<`. Four tiers keyed on **provenance**, which the GUI knows with certainty: `head` (timestamp + subject at **weight 600**), `echo` (the `$` command — the most valuable line in the log, today indistinguishable), `body`, `trace` (on the exact anchor `Traceback (most recent call last):`; Python's format is fixed, zero false positives — **do not extend to sniffing "error"/"warning"**). Delete `output.clear()` and add `setMaximumBlockCount(5000)`, or the header separates nothing. | medium | Light/sol-light: the console goes from a grey smudge sunk *under* the page to a document, and 9 live sub-AA cells die (`log_fg` is **3.97** in solarized-light today — the console's own body text, on the surface you stare at longest). Darks: the voice, not the well. |
| 3 | **THE BANNER.** *Hygiene, labelled — and the cheapest real legibility win in the app.* `feedback.py` carries **23 hand-written plain-language rules** producing `(friendly, next_step)`, and `_show_problems` puts every one in a **tooltip**. Nobody hovers a log row. `Verdict.next_action`'s own docstring says it is *"shown under the banner"*, and `self.banner` already has `setWordWrap(True)`. Fill it from `humanize(first_error)[1]`. **~4 lines.** | trivial | A failed setup stops reading `could not locate the final fantasy ix install` and starts also reading "Open Setup & Health and click Locate game…". |

**The register must be WEIGHT, not a third grey — and this is the finding.** `text`, `log_fg` and `muted` were each authored per-palette from their scheme's canon with **no relationship to one another**. They are not a ladder: **in dracula the top two are byte-identical (`#f8f8f2`); in both Solarizeds the order is inverted.** A derived head/dim ladder was swept to death (no `t` clears 4.5 for dim, best 3.72; head cannot move at all, max 1.037). **Weight is the only register axis that costs zero contrast headroom, which is exactly why it is the one that survives in the palette with none.** For a real dim tier use `_dim_token(log_fg, log_bg)` — the *mirror* of `_text_token`, stepping toward the ground while the **next** step still clears 4.5, and **backtracking instead of giving up**: 6/8 get `body:dim` = 1.99–3.03; the two Solarizeds collapse to `log_fg` **gracefully** and let weight carry.

**Where it dies:** honestly — the well mostly lands in the two light palettes, and the register amputates to "bold the header" in the two Solarizeds. This is the direction whose headline is a WCAG number, and phase 1 is the only part that is unambiguously an aesthetic move. **Which is why phase 1 should ship first, alone if need be.**

**Contract:** neutral, and P1 strengthens it. **One flag:** `theme.py:229-234` (echoed in `hero.py:9-11`) argues Mist has no gold partly because *"selection_bg cancels gold against navy to mud"* — a claim about a token with **zero rules**. Phase 1 renders `selection_bg` for the first time in the app's history. Mist survives it best of all 8 (sel:surf 1.405, text on it 9.04, rail 5.82), so nothing breaks — but the mud argument stops being hypothetical, and whoever owns IDENTITY.md should know the day it becomes a real pixel. *(One deduction to answer before shipping P1: hover measures 1.16 vs selection's 1.33 in some palettes — the ratio says hover out-shouts selection. The counter-argument is real and correct: contrast is **luminance-only and blind to the signal doing the work** — hover is a pure lightness step (ΔHue ≤ 2.5°, ΔSat ≈ 0), selection is a hue/chroma event (ΔSat up to +0.42 gruvbox, ΔHue up to 93.8° sol-light), plus a 3px saturated rail hover doesn't have. But this arc's whole method is that the eye failed six times and the pixels didn't. **Render it; don't argue it.**)*

---

### AND THESE WERE CONSIDERED AND DROPPED

**DRAWN (motion) — deferred, not killed.** The signet signing itself is the most charming thing anyone proposed for this app, and the 220ms verdict settle has a genuine causality argument: a hard cut has no *before*, so you cannot tell a fresh verdict from a stale one sitting from the last run. The mechanism is proven (the signet's `QPainterPath` is **already in perfect draw-on order** — it starts at the faint open-air end, travels into the corner gaining opacity, turns, rises, bead last; the dash reveal is monotonic and `t=1.0` is byte-identical to today; full hero repaint = **0.66ms/frame, 25.4× headroom**, so drop the pixmap fallback). But in a beauty round its engineer's proudest measurement is **0/255 at rest across 32 palette×state renders** — it provably changes nothing you look at — and roughly half its case is dead-code deletion counted as virtue. **Steal three things today regardless, all free:** delete `fade_in` (0 production callers, and the one helper that would *silently invalidate* `palette.py`'s shadow — verified via shiboken: the first effect's C++ object is **invalid**, not merely detached, and there is no restore); delete `theme.MOTION` (zero consumers — a vocabulary nobody speaks is worse than none); and **hoist `anim.configure()` above `win.show()` at `shell.py:9327`** or any future first-show animation silently never plays for anyone.

**KEYLINE (icons) — spin out its two defects, drop the rest.** Ship these tomorrow as bug fixes regardless of which direction wins:
- **The unsaved-changes dot eats the glyph it annotates.** `r = 0.30*w` punches out 72% of the icon and leaves **57% of its ink** — the "field" glyph loses its whole bottom-right corner and becomes an amber blob with a fragment of a frame attached, **on the row you are editing.** Fix: `k=0.19`, `pad=1.0`, and **`QRectF` (drop `int()` entirely)** — the pad alone cannot survive truncation. Result: 84.2% ink kept, 6.1px dot, a clean 1px halo at w=16 *and* w=24 at any dpr.
- **The whole accent tier and every leaf icon is invisible on a selected row, in all 8 palettes** (accent on accent = **1.00–1.01**; *byte-identically zero differing pixels* in solarized-light and dracula). `_type_icon` hands Qt a single pixmap and lets `QCommonStyle::generatedIconPixmap` guess — and Qt's guess (tint 30% toward Highlight) is *guaranteed* to erase an accent icon on an accent-Highlight row. Fix: `ic.addPixmap(icons.pixmap(name, tint, 16), QIcon.Mode.Selected)` → **4.56–9.43**. `.pixmap()` still returns Normal, so `shell.py:7841`'s `is_dot()` test keeps working. **Order matters: if REGISTER P1 lands first, the tint is `$text` on `selection_bg`, not `accent_fg`.**
- Its one real beauty is genuine and cheap and can ride along: the tree column has no even colour (`hub` is a dense 20u block out-weighing its own child `journey` at 13u; ink ranges 43.5–88.3 across one tier, so *weight actively fights the colour that encodes the tier*), and `chocobo` at 16px is not a feather, it is an unidentifiable scratch.
- Its four tint fixes are real and cheap: `accent_mark` (only nord moves) and leaves `text_subtle → muted` (2.96 sol-light **fails** → 4.91–6.99). **These must be a test, not an `audit_contrast` addition** — that tool reads ink from `w.palette().color(w.foregroundRole())`, a QLabel API, so it is structurally blind to a QPixmap. Fence **(tint, ground, STATE)**.

**CASEMENT** → merged into THE PLATE (its breadcrumb inversion is P3, its `$edge` is P4).
**COLOPHON** → merged into THE NAMEPLATE (its weight fix is P1; its serif moved from the crumb to the crown; its underline deletion is the plate's P3).

---

## 3. WHAT THE ROUND KILLED

**Killed on the merits — do not resurrect:**

- **PLATE's own slogan.** "Delete every rule whose two sides are the same colour" proves too much. A divider's job was never to separate two colours — it is to group. "Contrast 1.000" is rhetorically brilliant and measures the wrong thing.
- **The gold left stripe.** ΔHue 0.3–3.3° from `$warn` in 7 of 8; `$warn`'s only shape is a left stripe; the warn banner shares a splitter with Home. Dead by arithmetic, permanently, and it mints a fence.
- **INTAGLIO's `$well`.** Five reasons, the first fatal: **it regresses its own exemplars** (dracula 1.383 → 1.281, mist 1.343 → 1.306). Its premise was false (`field` reads as a well in **7 of 8** against `surface_2`, the ground forms actually live on — the defect is depth, not direction). Its solver's 1.35-on-`surface` target is **unreachable in every palette** (`log_bg:surface` maxes at 1.290), so the loop always exits on a fence or on convergence. It is null in 2 of 8. And phase 1 already delivers it. *If the 2% wells still bother anyone after playtest, the honest fix is four one-line palette edits to `field` — in-family, no token, no solver, and it cannot regress dracula or mist because it never touches them.*
- **The fill anchor.** d8=5 on a card in LIGHT. An arithmetic kill, not a taste one.
- **CASEMENT's un-tupled `_edge_token`.** Decays to **2.06 on nord whenever the spine shows**. The tuple `(surface, surface_2, bg)` is the house law `_text_token` already documents; half-copying a law is how you tune a token against a ground it never sits on.
- **A derived console head/dim ladder.** Swept to death: no `t` clears 4.5 for `dim` (best 3.72); `head` cannot move at all (max 1.037 — dracula is already white).
- **DRAWN's console rise.** Killed on DRAWN's own thesis: a panel sliding open is furniture rearranging, not the machine reporting — and DRAWN bans container transitions two sections later. The tell is mechanical: in its other phases the thing that moves is a *line resolving*; here it is a *box*.
- **REGISTER's problem-row delegate.** 12 of 23 `next_step` strings exceed 80 chars (max 169) — a QListWidget row elides, so the phase whose purpose is surfacing buried help would have **truncated the verb**. Replaced by a 4-line banner fill. *The weakest phase was weak because it was building a container the app already had.*
- **KEYLINE's keyline grid.** It fences a set the eye never juxtaposes (`rocket` sits alone on a button; `download`/`author`/`assets`/`state` never appear beside another glyph), and it contradicts its own measurements — it declares `circle ⌀18` while measuring the alerts at **20.0×20.0** and lists none as redraws. Optical overshoot is *why* a circle must be larger to read the same size — the exact principle it applies correctly to `solid` and inverts here. **A fence that would "fix" four correct drawings is round 2's failure mode wearing a tape measure.** Its size scale survives as two one-line hygiene edits (`shell.py:4329` plus 15→14; `mapview.py:112` campaign 46→44).

**Killed for CONTINGENT reasons — mark these; they are alive again the day the gate opens:**

- **LEDE's recession** (de-card Home's 7 entry rows). Its own entry condition is *"only ship this AFTER the lede lands and the user confirms the 10 cards still compete"* — a verdict that has not happened, gated on the playtest this round structurally cannot obtain. It also deletes 7 cards four commits after the user overruled killing the QGroupBox; the distinction (work surfaces vs front-door menu rows) is defensible, but CORRECTIONS.md exists *because* the last confident de-carding argument was measured wrong. **Earn it; don't assume it.**
- **COLOPHON's caption split** (11→12px + `HINT_W=460`). Killed on measurement — its "258 chars" headline needs a **1920px** window; at the 1280 default the real field column is 577px = **119 chars**, and the census of 106 real help strings is median 55 / mean 68.5 with **only 24 of 106** over the line. It also hides a cost: capping makes the 24 long hints *taller*. **Contingent: worth re-opening with a look, not a plan.**
- **DRAWN as a whole.** Deferred on round-shape, not on merit.

---

## 4. THE EXPIRED REJECTIONS *(load-bearing — do not bury)*

Round 2 produced a "do not resurrect" table. Re-verified, these reasons no longer hold:

| item | status | why |
|---|---|---|
| **Motion** | **EXPIRED** | The reason was *"the complaint came from a still image"* — a fact about **evidence**, not about motion. The user has now seen it running. And `anim.py` already ships (3 consumers, a reduced-motion gate): motion was never absent; round 2 declined to *add* to it. **One sub-claim stays permanent:** the `(0.2,0,0,1)` bezier at initial velocity 0.008 vs OutCubic's 2.997 is **375× gentler** — that curve is dead forever. The *category* is open, which is why DRAWN is deferred and not killed. |
| **ChoiceCard** | **EXPIRED** | Leg 1 (*"builds the exact box-in-box being complained about"*) died when the user overruled the premise — the app is now *made* of cards with one tokenized language, and ChoiceCard's own remedy clause (*"delete the container first; then a card has ground to stand on"*) named a precondition granted by the opposite route. Leg 2 (hover 1.00:1 vs `surface_2`) re-measures at **still exactly 1.000 in dark, but 1.139–1.344 in the other 7** — dark's collision is the one real constraint, and a choice card's selected state need not use the `hover` token at all. **Re-open it jointly with OQ#2.** |
| **Gradient the buttons** | **SPLIT** | The *physics* leg (+4/255 dark, nil gruvbox, inverted light) is **permanent** — magnitude, not context. The *hierarchy* leg (*"bevels on four equal buttons produce four shinier equal buttons"*) **expired with the button ladder at `53d2ed9`.** They are no longer four equal buttons. **This is the door INTAGLIO walks through, and it must be stated out loud rather than smuggled.** |
| **`background: transparent` on QScrollBar** | **REASON UNSOUND** | It reads *"the universal `QWidget { background-color: $bg }` wins."* Defect #4 established the opposite general fact — now a code comment at `shell.py:411-422`: **a widget sheet out-ranks the app sheet regardless of specificity**, and `.QWidget` exact-class is the tool. The four forms tested were app-sheet rules. Low aesthetic value; it should not stand as "verified". |
| **`QTabWidget::pane { border: 0 }`** | **PERMANENT, wrong reason — and it matters to menu #1** | It reads "dead under documentMode (paintEvent returns early)." It is zero **painted** pixels, not zero pixels: `QStyleSheetStyle` still reads it for `SE_TabWidgetTabContents` geometry — measured, page rect **338×129 with vs 340×130 without**. It inset content by a border it never drew. **Keep the rule** as the explicit statement "the pane has no frame" — `savedoc.py`'s two QTabWidgets never set documentMode at all, which is exactly the invisible coupling that bit them. |
| **`$trim` / a new palette / MIST-as-the-fix** | **RESOLVED, not expired** | `trim` does not exist at HEAD; its gold-rule half shipped via SIGNET as two module constants (the better mechanism); Mist shipped opt-in *after* the hierarchy work, exactly as prescribed. Spent. Doctrine live. |
| **De-border console/trees** | **PERMANENT, and strengthened** | `log_bg:bg` across 8 = **1.061–1.121, Mist the new floor.** The fill can never hold that boundary alone. INTAGLIO's console phase does not resurrect it — it re-borders the console as a **cut**. |

**Two IDENTITY.md nuances worth recording:** rivets are contract-permanent but sit *above* an explicit escalation ladder (*"if it lands thin, raise `_MIST_ALPHA` before adding a second gold element"*) — contingent on a playtest that hasn't happened. And the versal-IX row kills it **in `$accent`** specifically (gold/accent = 1.019); a *gold* versal dies to "one corner, once," not to the 1.019.

**And apply the lesson to this document.** PLATE's recession-cut, COLOPHON's caption split, and DRAWN in its entirety are all killed for **contingent** reasons. Every one is alive the day the playtest happens. A future round should re-try them, not treat this file as a verdict. That is exactly the mistake round 2's table made, and it is the mistake this section exists to prevent us from repeating.

---

### ⚠ SHIP THIS FIRST, BEFORE ANY OF THE ABOVE — one line

**`hero.py:138` paints the overline in `d["text_subtle"]`.** Measured against its **real** ground (the plate gradient at the overline's y, then the radial bloom's falloff at its actual distance — not `surface_2`): **2.88–3.44 at the 1280 default, 3.11–3.81 at 860px. Sub-AA in 8 of 8 palettes, at 11px DemiBold.** The Rejected table forbids exactly this, permanently: *"`text_subtle` for subordinate headers… it is a de-emphasis tier for inactive controls, not for text."* PLAN.md's own Phase 6 spec prescribed `$muted` and said so in the comment. **The implementation drifted from its own spec inside one round.** `muted` measures 4.78–6.43 and fixes 8/8.

Nothing caught it because `audit_contrast.py` reads ink from `w.palette().color(w.foregroundRole())` and the hero is 100% `QPainter` with no QLabel children — **the front door is invisible to the instrument by construction.** It is the 8th instance of this study's defining pattern (*a fence that covers most of the app just moves the bug to the rest*) and the first where the uncovered ground is the one surface built to be looked at. Do not bundle it into a beauty phase; it is a bug fix and it should have its own commit. It should not survive the playtest.

---

### OQ#2 — ANSWERED, and its prepared answer has decayed

*"What's under the lamp on Build & Deploy?"* The waiting answer (`role="card"` + a 4px accent left-stripe, *"2.44–4.73 in all 7"*) **no longer measures that.** Re-run across 8: **nord 2.12 · sol-dark 3.06 · dark 3.85 · sol-light 4.31 · light 4.38 · gruvbox 4.48 · dracula 4.73 · mist 7.09 — floor 2.12, below the 3.0 non-text floor.** Traced to `0dcb2c4`: the contrast sweep deepened nord's accent `#5e81ac → #56779e` so a white label would clear 4.5 on a button fill — and the *same move* dropped the stripe 2.44 → 2.12. **One token, two jobs, opposite directions.**

**This round's answer: nothing is under a lamp on Build & Deploy because the screen has no title.** It stamps zero headings across six cards, and its card titles are 11px overlines — *smaller than the body they label*. The lamp was aimed at an empty room. Ship menu #2 phase 3 and OQ#2 is answered without spending a stripe at all.

---

## 5. THE ONE HONEST PARAGRAPH

What I am least sure about is **whether any of this is beauty or only better-made.** Three of the top four directions independently diagnosed each other as preconditions: PLATE's judge wrote *"subtraction's best possible outcome is 'not ugly'"*; INTAGLIO's wrote *"1px of edge buys 'feels made,' not 'is beautiful' — it's the precondition for beauty, not beauty"*; NAMEPLATE's wrote *"'give the page a title' buys relief, not admiration."* All three are right, and their sum is the round's real finding: **this app does not lack a beautiful idea — it has four unspent preconditions, and each generator found a different one.** The menu is honest about that (the plate, the material, the crown, the pointer) and the headline commits to doing them in the order that makes each one visible: subtract the noise, then give the survivors material, then put a name on the page, then point at the door. But I cannot prove from here that the sum is beautiful rather than merely correct, and I will not pretend I can. **Two things would settle it, in order. (1) The playtest STATE.md has ranked #1 for two rounds and that still has not happened** — nobody has seen round 2 or round 3 *running*, so every judgement in this document, including mine, is offline, and three of the ideas I killed are gated on a verdict I cannot obtain. **(2) One native render, side by side: the plate, a nameplate, and the bevel at t=0.18 and t=0.14.** The bevel is the one I would bet against myself on. Border-anchored it is arithmetically the strongest structural idea in the round — d33–d43, all 8 palettes, the only elevation idea that has ever survived light — and it is also one lit-top/shaded-foot away from Windows 95, and **no contrast ratio in existence can tell those two apart.**

One method note, because it earned its place: the single highest-value line in this entire round — `setDrawBase(False)`, which deletes 603px of the loudest line in the app in all 8 palettes at once — **is in no proposal.** It was found by *rendering* a patch instead of reading it. Three rounds measured the lines the app declares. Nobody measured the lines the app **receives**. The scarcity argument that funds SIGNET turns out to have had a term nobody counted, and it was the largest one.