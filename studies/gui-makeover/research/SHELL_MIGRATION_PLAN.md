# shell.py Phase-2 De-smush — Final Migration Plan

File: `C:\gd\Dream-World-IX\.claude\worktrees\rung-2-virgin-shore-mint-2bc4f1\ff9mapkit\ff9mapkit\workspace\shell.py`
QSS home: `...\workspace\style.py` (roles in the `_QSS` template) · Helper: `workspace.widgets.repolish(w)`

All four palette keys the new rules use (`success`, `warn`, `error`, `help`, `help_hover`, `hover`) are present in **every** theme dict (verified in `editor/theme.py`), and `surface_2/3`, `text_subtle`, `focus` come from `derive()`. `$success` is not yet referenced in the template — smoke-render `qss(LIGHT)`/`qss(DARK)` once after adding it to catch a typo'd key.

A recurring win found by all four passes: **many of these inline labels are neither rebuilt-on-nav nor in retheme's re-tint list, so they keep STALE colours on a live theme switch today.** Converting them to roles *fixes that latent bug* for free — call it out in the commit messages.

---

## 1. NEW ROLES / id-rules to add to `style.py`

Append inside the `_QSS` template, after the existing role block (line ~186). **Six** additions total — kept deliberately small; everything else reuses `muted`/`caption`/`accent`/`display`/`h2`/`muted[state=warn]`.

```css
/* --- Phase 2 additions --- */

/* 600-weight body text, colour/size inherit $text (leaf, section titles) */
QLabel[role="strong"]   { font-weight: 600; }

/* sub-h2 form/section title — 15px is an intentional off-ramp step (faithful to the inline) */
QLabel[role="h3"]       { font-size: 15px; font-weight: 600; }

/* uppercase overline / section overline (letter-spacing is inert in Qt QSS — see risk note) */
QLabel[role="overline"] { font-size: $type_caption; font-weight: 600; color: $muted; letter-spacing: 1px; }

/* flat link-style tool button (collapsible headers) — inherits global QToolButton bg */
QToolButton[role="link"] { border: none; font-weight: 600; text-align: left; }

/* lint verdict banner: static frame + per-verdict accent stripe (state set at runtime) */
QLabel[role="banner"] {
    background: $surface; color: $text; border-left: 4px solid $muted;
    border-radius: 6px; padding: 9px;
}
QLabel[role="banner"][state="ok"]    { border-left: 4px solid $success; }
QLabel[role="banner"][state="warn"]  { border-left: 4px solid $warn; }
QLabel[role="banner"][state="error"] { border-left: 4px solid $error; }
/* state="running" falls through to the muted default */

/* id-scoped chrome moved out of inline setStyleSheet — retheme's setStyleSheet(qss) now re-tints them */
QToolButton#hub {
    background: transparent; color: $help; border: 1px solid $help;
    border-radius: 6px; padding: 6px 10px; font-weight: 600;
}
QToolButton#hub:hover { background: $hover; color: $help_hover; border-color: $help_hover; }
QToolButton#hub:focus { border: 1px solid $accent; }

QWidget#crumbRow    { background: $surface; border-bottom: 1px solid $border; }
QWidget#consoleHead { background: $surface; border-top: 1px solid $border; }
QToolButton#consoleToggle       { background: transparent; border: 0; padding: 5px 6px; color: $muted; font-weight: 600; }
QToolButton#consoleToggle:hover { color: $text; }
```

**objectNames to set at construction** (needed for the id-rules): `self._hub_btn.setObjectName("hub")`; `crumb_row.setObjectName("crumbRow")` (873); `head.setObjectName("consoleHead")` (1028); `self._console_btn.setObjectName("consoleToggle")` (1033).

**The `#hub` rule is byte-identical to `_retint_hub_button`** (confirmed at 448–453: transparent/`help`/`help` border/6px radius/`6px 10px` pad/600; hover `hover`+`help_hover`; focus `accent`) — so the swap is faithful and the helper can be deleted (§3).

Reuse decisions (no new role minted): Home hero 1175 → **`display`**; overline uppercase 1235 → new `overline`; 11px hints 5630/5659 + 5630-class → **`caption`**; warn notes 1783/3880 → **`muted`+`state="warn"`** (existing selector). `h3` covers both 15/600 sites (984, 5292); `strong` covers all bare-600 sites (343, 1016, 1260, 4635).

---

## 2. Per-site decision table (all 60)

Legend: **role** = `setProperty("role", …)` before first show, no repolish (rebuilt-on-nav or dialog-fresh); **role+state+repolish** = persistent widget whose colour flips at runtime; **KEEP** = stays inline; **qss** = the whole-sheet application, untouched; **#id** = move to id-rule in style.py.

| line | widget | action | notes |
|---|---|---|---|
| 296 | BreadcrumbBar self bg | **KEEP** | structural bar bg; re-tinted by `repaint_pal` (pairs w/ 319) |
| 310 | doc-mode chip `_chip` | **KEEP** | dynamic per-mode fill (accent/warn), driven by `_set_chip` in retheme |
| 319 | BreadcrumbBar `repaint_pal` self bg | **KEEP** | the retheme re-tint of 296 |
| 330 | breadcrumb placeholder `ph` | **role="muted"** | rebuilt-on-nav via `set()` |
| 338 | breadcrumb separator `sep` | **role="muted"** | rebuilt-on-nav |
| 343 | breadcrumb leaf | **role="strong"** | `color:text`=default; only 600 is load-bearing (`label`=500 would de-bold) |
| 349 | breadcrumb crumb btn | **KEEP** | rebuilt-on-nav; not the `link` role (adds padding, no weight) — low value |
| 401 | `setStyleSheet(qss)` | **qss** | untouched |
| 437 | version chip (update) | **KEEP** | dynamic 2-state, owned by `_retint_version_chip` |
| 439 | version chip (normal) | **KEEP** | same helper |
| 448 | Info Hub btn `_hub_btn` | **#hub** | move to id-rule → **delete `_retint_hub_button`** |
| 464 | `setStyleSheet(qss)` retheme | **qss** | untouched |
| 474 | `insp_body` retheme re-tint | **DELETE** | redundant once 993 → role (do in same commit) |
| 666 | prefs theme hint | **role="muted"** | dialog child of self; also fixes live theme-preview staleness |
| 684 | source-checkout note | **role="muted"** | dialog note |
| 820 | toolbar spacer | **KEEP** | structural `background:transparent` |
| 873 | `crumb_row` chrome strip | **#crumbRow** | stale-on-switch today; fixed by id-rule |
| 984 | `insp_title` | **role="h3"** | 15/600 → h3 (faithful; do NOT use h2 = +1px) |
| 993 | `insp_body` base | **role="muted"** | enables the 474 delete |
| 1016 | console `_panel_header` lab | **role="strong"** | `color:text`+600 |
| 1029 | console `head` bg | **#consoleHead** | stale-on-switch; fixed |
| 1036 | `_console_btn` toggle | **#consoleToggle** | flat link toggle; ▾/▸ text set separately, unaffected |
| 1175 | HOME hero title | **role="display"** | 22→24px deliberate ramp; fixes Home staleness |
| 1194 | HOME intro | **role="muted"** | body-size paragraph (not caption) |
| 1200 | `_recent_box` | **KEEP** | structural transparent container |
| 1226 | HOME footer hint | **role="muted"** + move `margin-top:6px` to layout | role carries colour only |
| 1235 | HOME section overline | **role="overline"** + move `margin-top:10px` to layout | `.upper()` stays in `_home_section` |
| 1250 | HOME card glyph `g` | **role="accent"** + keep `font-size:17px` inline | one-off decorative size; themed colour → role fixes staleness |
| 1255 | HOME card text `col` | **KEEP** | structural transparent |
| 1260 | HOME card title `t` | **role="strong"** | 14→13px ramp normalization (visible; see risk) |
| 1263 | HOME card desc `d` | **role="muted"** | |
| 1498 | journey row `lbl` | **role="muted"** | mount-panel, rebuilt-on-nav |
| 1558 | fork-panel hint | **role="muted"** | keep body size (no size in original) |
| 1567 | fork-status `tag` (build) | **role="accent" toggle + repolish** | forked→accent, else role unset (=$text); **same widget as 1603** |
| 1573 | "forked" `lbl` | **role="muted"** | |
| 1582 | "fork manually" `lbl` | **role="muted"** | |
| 1603 | fork `tag` (`_mark_fork_running`) | **role="accent" + repolish** | replaces inline accent; move in lockstep w/ 1567 |
| 1728 | add-journey note | **role="muted"** | dialog |
| 1783 | BARE-journey ⚠ note | **role="muted" state="warn"** | build-time branch (distinct widget from 1787), no repolish |
| 1787 | non-bare seed note | **role="muted"** | else-branch, distinct widget |
| 1900 | pick-regions intro (RichText) | **role="muted"** | RichText orthogonal to colour |
| 2133 | new-field note | **role="muted"** | dialog |
| 2179 | new-campaign note | **role="muted"** | dialog |
| 2282 | new-journey `regions_hint` | **role="muted"** | dialog RichText |
| 2334 | new-journey kind blurb | **role="muted"** | text swaps via `setText`, colour constant → no repolish |
| 2416 | flags-editor note | **role="muted"** | dialog |
| 2556 | add-field note (RichText) | **role="muted"** | dialog |
| 3648 | `_doc_placeholder` lbl | **role="muted"** | rebuilt-on-nav |
| 3874 | **`_muted_label()` helper** | **role="muted"** | **converts ~20 callers at once** (3838/3846/3851/3903/4005/4012/4059/4076/4253/4405/4463/4732/4738/4740/4749/4916/4923/4938/4944/4946/4955) |
| 3880 | **`_warn_label()` helper** | **role="muted" state="warn"** | converts 3841, 4245; no repolish |
| 3897 | `_collapsible` header btn | **role="link"** | QToolButton |
| 4293 | `_collapsible_rows` header btn | **role="link"** | byte-identical to 3897; role dedupes both |
| 4635 | logic-add section title | **role="strong"** | weight-600 only |
| 5292 | **`_header` title** | **role="h3"** | 15/600; THE form section title (all `_mount_*`) |
| 5297 | `_header` note | **role="muted"** | |
| 5350 | scene-pos player note | **role="muted"** | |
| 5364 | scene-pos entity note | **role="muted"** | |
| 5630 | cutscene-dispatch note | **role="caption"** | 11px muted hint = exact caption |
| 5659 | step-editor hint | **role="caption"** | 11px muted hint |
| 6739 | **`self.banner` lint verdict** | **role="banner" + state + repolish** | persistent widget, dynamic stripe — the one true role+state+repolish site |

**The ~10 dynamic/chrome sites, resolved:**
- **KEEP inline (genuinely dynamic, retheme re-tints them):** doc-mode chip **310** (`_set_chip`), version chip **437/439** (`_retint_version_chip`), the two BreadcrumbBar structural backgrounds **296/319** (`repaint_pal`).
- **Convert to role + remove/skip the re-tint:** hub btn **448** → `#hub` (kills `_retint_hub_button`); `insp_body` **993+474** → `role="muted"` (kills the 474 re-tint); fork tag **1567/1603** → `role="accent"` + repolish (they were never in retheme, so this *fixes* their stale-colour bug); lint banner **6739** → `role="banner"` + state + repolish (also never re-tinted → fixes staleness).

**Banner call-site (`_show_problems`, ~6733–6741):** set `role="banner"` once at creation (line 1053), then replace the inline sheet with:
```python
self.banner.setProperty("state", {fb.OK:"ok", fb.WARN:"warn", fb.ERROR:"error", fb.RUNNING:"running"}
                        .get(verdict.level, "running"))
repolish(self.banner)
```
Keep the `glyph` dict; drop the `col` lookup.

**Fork tag (`_fork_rows[f]`, 1567 build + 1603 running):** on build set `role="accent"` only when forked (leave unset otherwise → inherits `$text`); in `_mark_fork_running` do `tag.setProperty("role","accent"); repolish(tag)`. Repolish both since the widget is long-lived within the panel.

---

## 3. retheme() / helper cleanup

After the conversions, edit `retheme` (455–474) and the helpers:

**DELETE:**
- **Line 474** (`self.insp_body.setStyleSheet(...)`) and its `if getattr(self,"insp_body",...)` guard (473–474) — `insp_body` is now `role="muted"`, re-styled by `setStyleSheet(qss)` at 464. *Only after 993 is converted in the same commit.*
- **`_retint_hub_button` def (441–453)** and its **call at line 469** — `#hub` id-rule is re-applied by `setStyleSheet(qss)`.

**MUST STAY (do not touch):**
- **464** `self.setStyleSheet(qss(pal))` — the core re-style; it is what makes every new role re-tint live.
- **463** `_apply_app_theme`, **465** `_dot_icon`, **467** `problems.placeholder_color` — non-QSS chrome.
- **468** `_retint_version_chip()` — 437/439 stay inline (dynamic).
- **470–471** `crumb.repaint_pal(pal)` — still needed for the bar's structural bg (319) and to refresh `self.pal` for later `set()` calls. Its label-rebuild is now colour-redundant (330/338/343 are QSS-driven) but harmless — leave it; it's also the trail rebuild.
- **472** `_set_chip(...)` — doc-mode chip (310) is dynamic.

**Net:** retheme loses exactly two lines (the `insp_body` re-tint and the `_retint_hub_button` call) plus the deleted helper. Everything else that stays is genuinely non-QSS or genuinely dynamic. Live theme switch stays correct, and several Home/console/fork/banner elements that were **silently stale** now re-tint properly.

---

## 4. Commit plan (each screenshot-verifiable)

**Commit A — style.py foundation + Home page** *(add all roles, adopt Home)*
- style.py: add all six additions from §1 (roles + id-rules).
- Convert Home: **1175** (display), **1194/1226/1263** (muted), **1235** (overline), **1250** (accent), **1260/1016** (strong); move the two margins to layout.
- **Screenshot:** Home page in light AND dark. Verify hero title size, muted intro/desc, uppercase overline, accent card glyph. **Then toggle theme live** and confirm Home now re-tints (the latent-staleness fix).

**Commit B — inspector + console + breadcrumb chrome + retheme cleanup**
- **993** insp_body → muted; **delete 474**. **984** insp_title → h3.
- **873** #crumbRow, **1029** #consoleHead, **1036** #consoleToggle (+ objectNames). **330/338/343** breadcrumb labels → muted/muted/strong.
- **448** #hub (+ objectName); **delete `_retint_hub_button` + its call at 469**.
- **Screenshot:** breadcrumb bar, inspector panel (title + body), console header/toggle, Info Hub button (resting + hover + keyboard-focus ring). **Toggle theme live** — the critical regression check: confirm hub button, crumb bar, console strip, and inspector all re-tint (these previously used hand re-tints now removed).

**Commit C — dialogs / journey-campaign notes / link buttons / banner**
- Helpers: **3874** `_muted_label`→muted, **3880** `_warn_label`→muted+state=warn (cascades to ~22 callers). **5292** `_header` title→h3, **5297** note→muted. **3897/4293** → link. **4635** → strong. **5350/5364** muted; **5630/5659** caption; **3648** muted.
- Region 1490–2560 notes (1498/1558/1573/1582/1728/1783/1787/1900/2133/2179/2282/2334/2416/2556) per table; **1567/1603** fork tag → accent+repolish (lockstep).
- **6739** banner → role+state+repolish.
- **Screenshot:** a form doc (section titles + muted notes), a collapsible link header, the new-journey dialog (incl. the ⚠ bare-journey warn note), a fork panel (forked row accent vs plain), and the lint banner in each verdict (ok/warn/error). Confirm the banner stripe colour per verdict and that a live theme toggle re-tints it.

Keep the `-ih` mod-folder / smoke check in the loop: `ff9_workspace.pyw --smoke` after each commit before screenshotting.

---

## 5. Risks

- **Specificity — the only `#id` selectors introduced are `#hub`, `#crumbRow`, `#consoleHead`, `#consoleToggle`.** All target unique widgets and correctly out-rank the generic type rules. `#hub` and `#consoleToggle` **must keep their own `:focus`/`:hover`** (id > pseudo-class specificity) — included above. No `#id` selector targets any QLabel, so all `QLabel[role=…]` conversions are conflict-free.
- **`#card` collision (do NOT touch):** Home cards use `QFrame#card` (surface, radius 10) — *different* from `QFrame[role="card"]` (surface_2, radius 8). The card box has no inline style to convert; **never add `role="card"` to Home cards** or they jump elevation.
- **Structural transparent keeps (820, 1200, 1255):** leave inline — they counter the global `QWidget{background:$bg}` and are palette-independent.
- **Plain-QWidget styled backgrounds (873, 1029):** `crumb_row`/`head` are bare `QWidget()` instances; the ancestor `#id` rule should paint bg+border, but if a build shows them unpainted add `setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)`.
- **`letter-spacing` (1235 overline) is inert in Qt QSS** — it was already inert inline, so this is faithful; true tracking needs `QFont.setLetterSpacing` (defer, not required).
- **Two deliberate size shifts to flag in review:** Home hero **22→24px** (1175→display) and Home card title **14→13px** (1260→strong). Both are intentional ramp adoption; if the team wants byte-fidelity instead, give 1260 a dedicated `role` with `font-size:14px` and keep 1175 at 22px — but the ramp normalization is the point of the pass. `insp_title` 984 stays faithful at 15px via `h3` (not h2).
- **Live-theme-switch is THE regression check.** After Commit B especially, cycle light↔dark with the inspector open, the console open, and the Info Hub visible — those three lost their hand re-tints and now depend entirely on `setStyleSheet(qss)` at 464. Confirm no widget keeps an old-palette colour. Bonus: several sites (Home labels, fork tag, banner, console strip) that were **already stale** before this pass should now switch correctly — a visible improvement, not just parity.