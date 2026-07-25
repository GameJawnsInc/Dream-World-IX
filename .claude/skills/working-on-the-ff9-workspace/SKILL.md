---
name: working-on-the-ff9-workspace
description: Work ON the Dream World IX Workspace GUI itself -- the PySide6 desktop app at apps/ff9_workspace.pyw, its package ff9mapkit/ff9mapkit/workspace/ (shell, style, widgets, forms_qt, mapview, worlddoc, coopdoc, logfind), and the shared ff9mapkit/ff9mapkit/editor/ backend. Use when editing a Workspace tab, dialog, form, the Info Hub catalog, the Ctrl-K command palette, the Output console, a QSS rule, a palette token, a theme, the CALIBRE text-size dial, prefs, layout persistence, or a test_workspace_* test -- and whenever a GUI symptom is reported (a control dead on click, an unreadable chip or highlight, a popup opening too small or clipped, panes stuck narrow after one narrow session, text that ignores the size dial, a headless run that hangs with no output). Verify with tools/gui_snap.py by rendering the real surface and READING the PNG, never by asserting from source -- the failure that recurs here is a correct mechanism that no call site ever spends. NOT for authoring game content -- field.toml, walkmesh, .eb, battle, or overworld work belongs to the authoring skills even when driven through this GUI.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Working on the FF9 Workspace GUI

`apps/ff9_workspace.pyw` → `ff9mapkit/ff9mapkit/workspace/` (27 modules, ~24.7k lines) over the
shared `ff9mapkit/ff9mapkit/editor/` backend. This skill owns changing **the app** — not the game
content it edits: `field.toml` / walkmesh / `.eb` / battle / overworld work stays with the authoring
skills even when made through a Workspace form, and deploying stays with `deploying-ff9-mods`.

**Before a substantial round, read memory `[[project-ff9-gui-makeover]]` and
`studies/gui-aesthetics/STATE.md`** — the 12-round record and every law's origin. Module map, the
full snap-surface list, and the Qt trap table: [references/workspace-map.md](references/workspace-map.md).

## The verification loop — RENDER, then look

I can see this app. `tools/gui_snap.py` renders any surface hidden-on-screen to a PNG I **Read**. A
visual claim that was not pixel-verified is a guess.

```
py tools/gui_snap.py --list
py tools/gui_snap.py home:ready tab:build dlg:prefs --theme mist --scale 100
py tools/gui_snap.py all --theme dark --scale 150 --width 1280
```

PNGs land in `tools/scroll_out/gui_snaps/`; each prints shown size / sizeHint / minimumSizeHint (the
numbers sizing bugs live in), and `--scale` sweeps the CALIBRE rungs 100/110/125/150. **Grab the
SUBJECT, not just the window** — a chip judged inside an 850px screenshot is the downscaled-review
mistake (`_grab_strip` upscales a strip 3x nearest-neighbour, inventing no colour). Add a pinned
surface for anything new: a state that cannot be reproduced from a fake install cannot be reviewed.
The harness is **native only** and refuses offscreen on purpose (below).

## THE CALL-SITE LAW

> **A correct mechanism exists and the call site does not spend it.** The study's most repeated
> defect — measured four separate ways in round 6 alone.

Shipped instances: `role="h1"` set by nothing; `widgets.card()` / `heading()` / `status_chip()` /
`tabular()` with **zero call sites**; a chip hardcoding `#ffffff` for **1.12:1** while the authored,
4.5-fenced `accent_fg` sat unused (dracula 1.12 → 14.13 once spent); **6 of 7 id-scoped buttons dead
on click** because an id selector out-ranks the generic `:pressed` rule. The inverse bites too — the
warm-thumb fast path spent EAGERLY at the one call site whose contract is laziness cost ~1.3s of
startup. So when you add a token, widget, or helper, **fence its call sites**
(`tests/test_gui_wave2_wiring.py`, `test_field_cards.py`, `test_model_cards.py` are the shape). A
mechanism with no fence has a half-life.

## A law in a docstring is a wish

`widgets.option`'s docstring has said "never put prose inside a widget" since Phase 4. Co-op then
shipped a QCheckBox whose label was a 130-character sentence; a QCheckBox does not word-wrap, so its
`minimumSizeHint` **was** the whole 763px string and one control put a 797px floor under its card.
Same round, `style.py`'s "never demote a diagnostic" sat directly above the rule that broke it.
**If it is a law, it is a test.**

## A squeeze is not a preference

A value the app computed **under duress** is not a value the user chose. The document column has a
hard minimum, so a too-narrow window can only take width from the outer panes, which clamp to their
minimums — and `_save_layout` persisted that clamp as a preference. With stretch factor 1 on the
middle pane, `[90, 542, 66]` saved at 700px reopened at 1280 as `[90, 1122, 66]`, permanently; the
reporter had never once seen the real default. The rule: **pinned at the minimum == forced, heal it;
collapsed to zero == chosen, keep it** (`shell._repair_central_split`, fenced by
`test_a_squeezed_panel_is_not_a_preference`, which READS the floor at runtime because it is
font-dependent — 78 real / 74 offscreen). Apply it to any new persisted geometry.

## Probe discipline — three ways the instrument lies

1. **Offscreen stubs the Qt font DB.** Every WIDTH it reports is fiction and it has manufactured
   whole defects (a 1156px `mid_col` minimum against a real 542; a 1296px window floor). **Colour is
   font-independent, so offscreen colour proofs hold**; geometry needs native + `WA_DontShowOnScreen`.
2. **An empty tempdir is not a clean room, it is a hole the OS falls through.** Repointing
   `LOCALAPPDATA` at an empty dir makes `prefs.text_scale()` fall through to the developer's Windows
   slider, so the probe that justified a 700px minimum measured exactly one scale. **Pin every pref
   explicitly and sweep all four rungs** (`gui_snap._pin_prefs` is the reference).
3. **A probe that cannot reproduce the LIFECYCLE cannot falsify a lifecycle bug.** An in-session
   resize "falsified" the layout ratchet because a live splitter still holds its original
   `setSizes()` request and re-derives from it. The bug needs a **restart**.

Also: `FF9MAPKIT_DATA` has one name and **two meanings** — `provision.cache_dir()` *and*
`provision.data_dir()` (TEMPLATES). Using it to move a test cache pointed every surface's template
lookup at an empty dir and hung the harness. Patch the narrow accessor instead.

## Tests must never touch the developer's machine

The repo's most-recurring test defect, flagged by review round after round: **a test that reads or
writes the developer's real `prefs.json` is a report on the developer.** Same for the real install,
the thumbs cache, and `backups/`. `tests/conftest.py` has an autouse fixture repointing
`prefs._path` at a tmp file; keep every pin **function-scoped**, because a module-scoped pin unwinds
before `win.close()` runs `closeEvent` → `_save_layout`, which then overwrites the real layout with
a never-shown window's squeeze fossil. Pin the game through the **ctor seam** (`game_path_fn`), and
never fabricate a machine state silently (`gui_snap._fake_install` raises `KeyError` on an unknown
state on purpose).

## Colour is per-ground

- **A visibility floor is calibrated per GROUND and does not transfer between tokens.**
  `_selection_token`'s 20/255 was calibrated against `hover`; on `log_bg` it painted correctly (339
  measured px) and still read as a smudge → `FIND_TINT_FLOOR = 44`.
- **THE NINTH-GROUND LAW — invent a ground, you owe it a fence.** A find highlight is a *third*
  colour under the log's ink, so `contrast(log_fg, log_bg) >= 4.5` covers nothing; the naive build
  measured **1.16–3.43:1, sub-AA in 8 of 8 palettes**. Both tiers now set their ink explicitly.
- Floors: **4.5 for text, 3.0 for non-text graphics**. And **a property is not a rendered colour** —
  re-measure from pixels; `style.py`'s `[role="muted"][state="warn"]` rule proves the cascade does
  not go the obvious way. Tokens derive in `editor/theme.py`; `workspace/style.py` is the
  PySide6-free QSS generator, so both test headless. **`workspace/palette.py` is the Ctrl-K COMMAND
  palette, not colour** — a real naming trap.

## The CALIBRE dial, and popups sized from content

**A px constant cannot hear the dial.** `resize(W, H)` and `setFixedSize` are deaf by construction,
and a squeezed dialog OVERPAINTS. Use `widgets.fit_dialog(dlg, ch=…, list_rows=…, lines=…)`, which
sizes in text units clamped to the screen; it measures a populated `QListWidget` from real content
while a `QPlainTextEdit`'s sizeHint is ~256x192 regardless (the first cut opened 368px tall for three
rows). Custom-painted surfaces (`hero`, `mapview`, `conceptmap`, `worlddoc`) take `scale=` and
re-derive fonts + geometry in `_apply_text_scale` / `retheme`; a widget stylesheet OUT-RANKS the
application sheet, which is how a surface goes deaf.

## Tests and handoff

`py -m pytest -n 6` from `ff9mapkit/` (GUI suites: `tests/test_workspace_*.py`, `test_gui_*.py`,
`test_editor_theme.py`, `test_prefs.py`, `test_coop_tab.py`). Then **snap the surfaces you touched
and Read the PNGs**. Green tests plus a clean snap is still not a playtest — the human owns the
verdict on feel; after a visible change, stop and ask them to run the app and report.

## Additional resources

- Memory (Layer 2): `[[project-ff9-gui-makeover]]` (READ FIRST), `[[project-ff9-battle-party-gui]]`,
  `[[project-ff9-infohub-authoring]]`, `[[feedback-blender-addon-exports-artifacts]]` (the add-on
  exports an artifact and prints the CLI command — it never subprocesses the toolkit),
  `[[project-ff9-test-suite-perf]]`.
- Studies: `studies/gui-aesthetics/` — `STATE.md` (start here), `README.md` (the offscreen warning +
  the radio-border headline), `CORRECTIONS.md`, `PLAN.md`, `VISION.md`, `CRITIC.md`, `evidence/`;
  also `studies/gui-ux/PROPOSALS.md`, `studies/gui-strings/`, `studies/gui-makeover/`.
- Code: `tools/gui_snap.py`, `workspace/shell.py`, `workspace/style.py`, `workspace/widgets.py`,
  `editor/theme.py`.
