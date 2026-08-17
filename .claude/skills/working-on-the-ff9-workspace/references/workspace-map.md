# Workspace map, snap surfaces, and the Qt trap table

Lookup detail for `working-on-the-ff9-workspace`. The narrative record is
`studies/gui-aesthetics/STATE.md` + memory `[[project-ff9-gui-makeover]]` — this file is the index.

## Entry points

| Thing | Path |
|---|---|
| Double-click launcher | `apps/ff9_workspace.pyw` (inserts THIS worktree's `ff9mapkit/` on `sys.path` first, so the local package shadows any editable install) |
| Module entry | `py -m ff9mapkit.workspace.shell` |
| Snap harness | `py tools/gui_snap.py` (Windows-only — the prefs pin repoints `LOCALAPPDATA`, which `provision._user_dir` honours only on `nt`) |
| GUI extra | PySide6 is the optional `gui` extra; every Qt import must stay out of the CLI's import path |

## `ff9mapkit/ff9mapkit/workspace/` (Qt)

| Module | Owns |
|---|---|
| `shell.py` | The Workspace window: rail tabs, tree, inspector, Output dock, status bar (drift chip), Ctrl-K wiring, prefs + layout persistence (`_repair_central_split`, `_save_layout`), theme + `_apply_text_scale`, `run_job` |
| `style.py` | The QSS generator — **PySide6-free**, a `string.Template` over a palette dict (so it is unit-testable headless). The 4px spacing grid, the radius language, the type ramp |
| `widgets.py` | The shared widget vocabulary: `section` `card` `kv` `prose` `caption` `notice` `nameplate` `status_chip` `empty_state` `disclosure` `option` `id_field` `region_catalog_list` `page_column` `fit_dialog` `set_state` `repolish` `tabular` `TRANSPARENT` `WheelGuard` |
| `forms_qt.py` | The generic Qt renderer for `editor/forms.py` specs — plus `CatalogLibrary`, the **Info Hub** dialog (its rich text is HTML, so no QSS role reaches it — it takes the CALIBRE scale explicitly via `set_text_scale`) |
| `palette.py` | The **Ctrl-K command palette** (fuzzy subsequence search over commands + project content). NOT colour — colour is `editor/theme.py` |
| `hero.py` | The Signet hero band on Home (QPainter; `band_metrics(scale)`) |
| `mapview.py` | The campaign MAP (QGraphicsView poster cards, ribbon merge, seam chip, Ctrl+scroll / Ctrl+0 / Ctrl+1) |
| `worlddoc.py` + `worldscan.py` | The World tab — the 24x20 overworld atlas and its Qt-free census half |
| `coopdoc.py` | The Co-op tab (reads `[Netsync]` from `Memoria.ini`, detects the engine by marker strings) |
| `logfind.py` | Find-in-Output + the session JOB INDEX (`find_all` / `job_spans` are pure; `FindBar` is the thin Qt half) |
| `conceptmap.py` / `concepts.py` | The "how it all fits" diagram and the newcomer concept cards |
| `builddoc.py` `importdoc.py` `battledoc.py` `modelsdoc.py` `savedoc.py` `setupdialog.py` `tuningdialog.py` | The per-tab / per-dialog documents |
| `fieldcards.py` `modelcards.py` `thumbs.py` `icons.py` `anim.py` `gamewin.py` | Card pickers, the thumbnail cache, the SVG icon family, the ONE motion module, the post-deploy game-raise |
| `animframes.py` `clipplayer.py` `animpicker.py` | The animation-preview trio: the clip-frame service (clip-shaped queue, `supersede()` cancels, warm disk answers sync), the transport + playback mixin BOTH surfaces spend (`ModelsDoc`, `AnimPickerDialog`), and the picker dialog itself (gesture / movement / slots) |

## `ff9mapkit/ff9mapkit/editor/` (the shared, mostly Qt-free backend)

`theme.py` (palettes + `pick_palette` + `derive` + the token derivations `_selection_token` /
`_find_token` / `_fg_token` / `_text_token`) · `model.py` (load/edit/serialize a `field.toml`,
bpy/tk-free) · `forms.py` (form specs + parsers, tk-free) · `jobs.py` (the build/deploy/import job
layer) · `tomldiff.py` (semantic toml diff) · `deploysnap.py` (the parsed snapshot taken at deploy
time) · `picker.py` `dialogs.py` `feedback.py` `breadcrumb.py` `graphview.py` `battle_forms.py` ·
`app.py` is the older Tkinter field editor.

## gui_snap surfaces

```
home:fresh|midway|ready|veteran|open
tab:build|import|models|battle|story|items          (tab:coop and tab:world are pinned-only)
dlg:new-field|new-campaign|new-journey|fork-regions|import-fields|setup|prefs|about
    |concept-map|infohub|updates|fork-battle|campaign-newgame|anim-picker|animset-picker
models:cliplist|player
coop:nogame|stock|s36|s37|ready|live                 map:empty|plain|art
world:guide|nogame|atlas                             console:log|find|miss|jobs
drift:none|synced|ahead|campaign                     script:tree|panel
behavior:guide|bare|wizard|branchwiz|doc|compiled|edit|stage|sweep|siege|sim
trace:bare|traced|contacts|regions                   place:bare|fork|refused|regions
floorplan:bare|rooms|door|refused                    form:encounter|encounter-named|music|npc
```

`form:*` renders the field editor's LOGIC FORMS over a writable copy of the boletta example (guided
forced OFF, so `advanced` fields are inline instead of inside a collapsed drawer) and grabs
`doc_host`, not the window — a hint or placeholder judged inside an 850px window shot is unreadable.

`models:*` and `dlg:anim*-picker` render the animation preview, seeded by `_pin_anim_cache` (a scratch
`FF9MAPKIT_DATA` holding the still + 16 deterministic frame PNGs + the clip meta, with `NO_THUMBS`
lifted for the surface only). The two dialog surfaces open through their REAL call sites — the
`[[npc]]` form's `anims` Browse and the cutscene step's `animation` Browse, reached with `snap_form`'s
field-open scaffolding — because a bare `_make_win` has no open field to browse from.

`script:*` renders the verbatim Script presentation over a KIT-AUTHORED synthetic .eb (zero SE bytes —
the builder is owned by `tests/test_workspace_script_tree.py` and loaded by path), so it works in a
template-less worktree where the smoke's ALEX-fixture block skips.

Flags: `--theme` (default `mist`), `--scale 100|110|125|150`, `--guided guided|full`,
`--width`/`--height` (default 1280x850), `--out`, `--campaign`, `--thumb-source`, `--list`.
Output: `tools/scroll_out/gui_snaps/<name>_<theme>_<scale>.png`.

**Harness rules encoded in the tool, worth knowing before you add a surface:**

- It **refuses offscreen** and asserts `app.platformName() != "offscreen"`.
- `_pin_prefs` writes an explicit `prefs.json` with EVERY value pinned (theme, text_scale, guided,
  density, motion off, restore_session off, recent) — an empty dir is not a clean room.
- `_settle()` pumps `DeferredDelete` as well as `processEvents`, because `processEvents` alone does
  not deliver it and a rebuilt row list photographs ZOMBIE widgets otherwise.
- Fake installs live at **stable** paths, never `mkdtemp` — a random suffix painted into a status
  row makes every run differ in its most prominent line and kills pixel-diffing.
- Modal stubs answer to the DEFAULT button and print what they saw; the unsaved-changes prompt is
  stubbed to **Discard** — a snap must never write the user's project.
- One bad surface must not kill the sweep (each is wrapped and reported `FAILED`).

## The Qt trap table (each one shipped as a real defect)

| Trap | Consequence | Cure |
|---|---|---|
| Pseudo-class written before pseudo-element (`:focus::indicator`) | Qt degrades it to an UNCONDITIONAL rule — every radio/checkbox wore a permanent accent rectangle and radios had no focus ring at all | `::indicator:focus`. Reproduce with `studies/gui-aesthetics/evidence/prove_radio_border.py` |
| An id selector out-ranks the generic `:pressed` rule | 6 of 7 id-scoped buttons dead on click; a cascade TIE killed the active rail segment | Fence the rendered state, not the selector string |
| A QSS property rule that does not name your widget class | Silent no-op (`mono` covers `QLabel`/`QLineEdit` only) | Extend the rule or drop the property |
| The bare `.QWidget` transparent form | Round 9: it un-filled every form-doc button since round 5 | `widgets.TRANSPARENT` is the EXACT-CLASS form; keep it |
| A widget stylesheet | Out-ranks the application sheet, so that surface goes deaf to theme + CALIBRE | Prefer roles/properties on the app sheet |
| `resize(W, H)` / `setFixedSize` on a dialog | Deaf to the text dial by construction; a squeezed dialog overpaints | `widgets.fit_dialog` |
| `QPlainTextEdit` in a fitted dialog | sizeHint is ~256x192 regardless of content (368px tall for three rows) | Use a `QListWidget` — `fit_dialog` measures real rows |
| A `QCheckBox`/`QLabel`/`QComboBox` carrying a sentence | No word-wrap, so `minimumSizeHint` IS the string — one control put a 797px floor under a card | Prose goes in a `Prose`/`caption`, never inside a control |
| `QShortcut` owned by a HIDDEN widget | Never fires (Shift+Enter was dead while the tooltip advertised it) | Own it on a visible parent |
| Static `QMessageBox.warning/information/question/critical` | Exec in C++ and ignore a Python-patched `QDialog.exec` — a headless run hangs forever | Stub the statics AND the instance `QMessageBox.exec` (they are different) |
| `setClearButtonEnabled(True)` | Eats Escape | Handle the key before the line edit does |
| An InstantPopup `QToolButton` | Draws its OWN menu arrow (a typed one gives two carets) | Do not type the caret |
| A forward text selection | `ensureCursorVisible` reveals the span's TAIL | Select backward to reveal the HEAD |
| Removing a `QGroupBox` | Qt derives a control's screen-reader name from the enclosing groupbox title — 13 names silently stripped | `setBuddy`, and re-run the a11y suite |
| `ExtraSelection` on `QPlainTextEdit` | It belongs to `QTextEdit`; PySide6 has no such attribute | Paint the highlight yourself |
| A silent hang with no output | Almost always an unstubbed modal | `faulthandler.dump_traceback_later` |
| A screen-fixed overlay parented to a `QGraphicsView` VIEWPORT | Qt scrolls via `QWidget::scroll`, which MOVES viewport children — every fit/zoom/pan dragged the floorplan's corner chips from C++ (no Python override sees it) until the zoom hint clipped at the canvas edge | Re-pin in a `scrollContentsBy` override (floorplandoc's `_place_hint`; still latent in mapview/backdrop/behaviordoc/worlddoc) |

## Test suites

`py -m pytest -n 6` from `ff9mapkit/`. GUI-relevant: `tests/test_workspace_*.py`
(`smoke` `style` `a11y` `widgets` `prefs` `drift` `logfind` `mapview` `hero` `icons` `anim`
`conceptmap` `concepts` `thumbs` `savedoc` `update` `jobloop` `inspector_ux` `encounters`),
`test_gui_mode_lever.py`, `test_gui_wave2_wiring.py` (the call-site fences), `test_editor_theme.py`
(the token/contrast fences), `test_prefs.py`, `test_coop_tab.py`, `test_worldscan.py`,
`test_worlddoc.py`, `test_builddoc_dest_ledger.py`, `test_home_beginner.py`, `test_field_cards.py`,
`test_model_cards.py`, `test_workspace_script_tree.py` (the verbatim Script presentation, over a
synthetic .eb — runs in every worktree).

`tests/conftest.py`'s one autouse fixture repoints `prefs._path` at a tmp file. Anything else that
could reach the developer's machine (game install, thumbs cache, `backups/`, `FF9MAPKIT_DATA`) must
be pinned per test, function-scoped.
