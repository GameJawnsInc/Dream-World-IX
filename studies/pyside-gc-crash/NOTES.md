# The Workspace GC access violation — root-caused (PySide6 wrapper-ownership bug)

**Verdict up front:** the intermittent native crash behind THE GC-CHILD LAW's layer 2 is a
**PySide6/shiboken ownership bug, reproduced with zero kit code**: calling
**`QGraphicsItem.parentItem()` on a wrapper whose C++ item is top-level (the call returns
`None`) silently flips that wrapper to PYTHON-owned. When the wrapper later dies — loop
temporary, refcount, GC, or interpreter shutdown — shiboken DELETES the C++-owned item.**
A read-only `scene.items()` sweep that touches `parentItem()` empties the scene; parented
graphs turn into dangling pointers; `scene.clear()`/teardown then double-frees →
0xC0000005 (access violation) / 0xC0000374 (heap corruption). It is **not a Python 3.14
problem and not a 6.11 regression — do NOT pin Python 3.13** (measured identical there).
The shipped retained-wrapper test discipline is the correct mitigation and must stay.

Environment of record: Windows 11 · Python 3.14.4 · PySide6 6.11.1 · `QT_QPA_PLATFORM=offscreen`.

**A SECOND, independent poison was root-caused 2026-08 — monkeypatching a Qt class's virtual
(`QFrame.setVisible`) while instances dispatch through it leaves a dangling pointer in
shiboken's per-type override cache; the undo does not clear it. Deterministic reproducer,
bisect, and fix: see THE CLASS-PATCH FLAVOR below.**

## The mechanism, precisely (all deterministic — `probe_item_destroyed.py`)

| Probe | Result |
|---|---|
| build 10 C++-owned rects, sweep `items()` touching `parentItem()`+`data()` | **0/10 survive** — the sweep destroys the scene's items |
| same sweep touching only `data(0)` / `isVisible()` / `type()` / `hasCursor()` | 10/10 survive |
| same sweep with NO method calls on the wrappers | 10/10 survive |
| `parentItem()` on a child that HAS a real parent | safe (2/2 survive) |
| `parentItem()` (→None) on a RETAINED wrapper, wrapper dies later | item destroyed AT WRAPPER DEATH — the bomb is armed, not defused, by retention |
| `scene.itemAt()` hit + `parentItem()` walk (the press path) | hit item destroyed; script segfaults at exit |

So the poison is exactly **`parentItem()` returning `None`**: shiboken's return-value/parent
heuristic re-parents the wrapper to "no parent" → orphan → Python-owned → the wrapper's
destructor deletes the C++ item. A real-parent return records a parent relation instead and
is safe. Retained wrappers that never have `parentItem()` called on them are fully safe —
which is why the retained-wrapper rewrite (reading `_kids` directly) is 8/8 deterministic:
it doesn't retain harder, it **avoids the poison call**.

Why the old flake looked GC-shaped and ~1-in-3: every fresh-sweep pass destroyed items
deterministically, but the *manifestation* (mid-run access violation vs shutdown heap
corruption vs silent survival) depends on heap layout — pytest's session-end
`gc_collect_harder` and shutdown finalization were just the usual detonation points. It also
explains why a "30-round plain version" never fired: a repro without the `parentItem()`
touch (cursor()/hasCursor() alone) is harmless.

## Repro inventory (this directory)

- **`repro_scene_items_cursor_gc.py`** — full pure-PySide6 mirror of the PRE-fix
  `test_grabbable_things_carry_the_move_cursor` (commit 9ebfbd2f): view+scene, MaskShape
  snips, ItemIgnoresTransformations anchors, scene-created children, 5 rebuilds/round, the
  fresh-wrapper sweep. **24/24 processes crashed** across park/drop × normal/aggro-GC
  (most within 1–4 rounds); the retained-sweep control: **0/12**. Knobs: ROUNDS/SWEEP/PARK/GCH/AGGRO.
- **`repro_bisect.py`** — the same mirror with strip-one-element env flags. Every element
  proved removable (view, cursors, MaskShape, anchors' flag, child adoption, pixmaps, text,
  even forced gc.collect) EXCEPT the repeated fresh sweep.
- **`minimal_core.py`** — the distilled shape: bare `QGraphicsScene`, plain rects, one
  `items()` sweep touching `parentItem()`, `scene.clear()`, ~20 rounds → 4/4 crash.
  `TOUCH=` (no method calls): 0/4.
- **`probe_item_destroyed.py`** — the DETERMINISTIC one-second detector (exit 1 = bug
  present). **This is the gate for any future PySide6 upgrade**: run it on the new version;
  exit 0 before relaxing the retained-wrapper rule.
- **`run_matrix.py`** — the crash-matrix driver.

## Version A/B (uv venvs; probe + 10-round mirror × 4)

| Python | PySide6 | probe | mirror |
|---|---|---|---|
| 3.14.4 | 6.11.1 | BUG | 24/24 crash |
| **3.13.14** | 6.11.1 | **BUG** | **4/4 crash** |
| 3.14.4 | **6.10.3** | **BUG** | **4/4 crash** |

Python-version-independent, present at least since 6.10.x — the recent flake onset was the
new click-authoring workload (sweeps + anchor graphs), not an interpreter or PySide change.
**A Python 3.13 pin buys nothing; there is no clean PySide version to pin either** (6.11.1
is the latest release as of 2026-07-29).

## Upstream (bugreports.qt.io)

- **PYSIDE-2711** — "Calls to QWidget.parent() invalidate non-owning Python objects",
  fixed 6.8.0. The same disease, QWidget flavor; the fix did not cover QGraphicsItem
  (not a QObject).
- **PYSIDE-3380** — "Fetching a menu through a temporary QAction wrapper destroys the
  C++-owned QMenu", fixed for 6.11.2/6.12.0 (both UNRELEASED). Its Gerrit change
  (pyside-setup 750031, "the return value heuristic of shiboken6 added a parent
  relationship") is **QAction.menu()-specific** — it will NOT fix `parentItem()`.
- **No issue exists for the `QGraphicsItem.parentItem()` flavor** — apparently unreported.
  Worth filing upstream with `minimal_core.py` + `probe_item_destroyed.py` (outward-facing:
  owner sign-off first).

## THE CLASS-PATCH FLAVOR — a second, distinct poison (2026-08, deterministic, FIXED)

A deterministic pair reproducer surfaced on master:

```
cd ff9mapkit
py -m pytest tests/test_cutscenedoc.py tests/test_workspace_floorplan.py -q
```

~44 dots, then **0xC0000005** with the faulthandler banner pointing at `tests/conftest.py:47`
— the `qt_drain` parking pass's `w.hide()` over surviving top-level widgets. Under the full
suite with `-n 6` the same disease surfaced instead as **9 setup ERRORs** in
`test_workspace_floorplan.py` on the poisoned xdist worker, each reading:

> TypeError: Error calling Python override of QFrame::2:setVisible():
> CutsceneDoc._build_instruments.<locals>.<lambda>() takes 0 positional arguments but 2 were given

— a zero-arg `clicked` lambda (cutscenedoc.py's stage button) being INVOKED as a
`setVisible(self, visible)` virtual override on an unrelated widget.

**Bisect record (prefix search over test_cutscenedoc.py's 43 tests + a 5-test floorplan
detector; driver preserved the session it ran in):**

| Subset | Verdict |
|---|---|
| detector alone | PASS |
| full file + detector | CRASH |
| any single early test + detector | PASS |
| minimal crashing prefix | = 36, whose LAST test is the trigger |
| `test_nothing_shows_the_accordion_panels_while_parentless` ALONE + detector | **CRASH, deterministic, ~1s, every run** |
| all 42 OTHER tests + detector | PASS |

That test monkeypatched **`QFrame.show` and `QFrame.setVisible` at the CLASS level** around a
gesture that shows QFrames (`set_inset` → `widget.show()` → C++ `QWidget::show` → virtual
`setVisible` dispatch), then `monkeypatch.undo()`. The error string `QFrame::2:setVisible`
names shiboken's per-type virtual-override slot: the dispatch machinery resolved and CACHED
the patched Python callable during the patched window, and the undo restores the type dict
but not that cache — the cached pointer dangles. The NEXT `setVisible` dispatch anywhere in
the QFrame family (here: the neighbour module's drain calling `w.hide()`) calls freed memory:
segfault when the slot is garbage, the lambda-misdispatch TypeError when the allocation was
reused by another callable. Same family as PYSIDE-2711/-3380 (a borrowed callable outliving
its slot), different entry point — and entirely avoidable from our side.

**Sharpened law: NEVER monkeypatch a method on a Qt CLASS — virtuals above all — while
instances are alive.** Patch instance seams, subclass before construction, or observe through
an event filter. A patch/undo pair around live C++ dispatch corrupts state that detonates in
whatever module runs next; no green run of the patching module ever vouches for it.

**Census of the remaining Qt-class patches in tests/ (audited with the fix, left in place):**
`QSplitter.setSizes` (test_workspace_prefs ×2 — NON-virtual, C++ never dispatches it, so no
cache entry can form), `QDesktopServices.openUrl` (static, same), `QDialog.exec`
(test_import_pickfill, test_gui_wave2_wiring — virtual, but only Python ever calls it and the
fake exists precisely so the dialog never runs, so nothing dispatches it from C++ during the
patched window). None can detonate the way the setVisible patch did — the poison needs C++
to RESOLVE the virtual while the patch is live — but migrate them to instance seams when
touched: the distinction is load-bearing and easy to lose.

**Fix (both halves shipped, pair 3/3 green — 143 passed per run):**

1. The phantom-window fence now observes through a **QObject event filter** on the two
   panels: `QEvent.Show` while `parent() is None` IS the phantom window (delivered
   synchronously inside both `show()` and `setVisible(True)`, including C++-side shows the
   original class patch existed to catch and a `QWidget.setVisible`-only patch missed). The
   fence stayed sharp — a break-it probe (`doc.editor.show()` while parentless) records
   `['StepEditor.Show']` and fails the assert. No Qt dispatch table is touched.
2. `test_cutscenedoc.py` was the last per-test-widget GUI module WITHOUT the
   `_deterministic_qt_teardown`/`qt_drain` autouse; its unparked doc/Workspace graphs died
   under GC mid-way through the next module — with the class patch deselected, the pair
   still crashed intermittently (2/2 under the full 100-test neighbour, 0/1 under a 5-test
   detector: heap-layout manifestation, the known layer-2 flake). The module now parks, with
   the restage debounce disarmed first (the floorplan judge-debounce lesson: a parked doc's
   armed 500ms timer must not start a staging worker in somebody else's teardown).

## What this means for the repo

1. **Keep every shipped fix** — the GC-CHILD LAW's scene-created+`setParentItem` pattern,
   `_kids` retention, retained-wrapper test asserts, `qt_drain` parking. All correct; the
   law now has a named mechanism.
2. **Sharpened law: never call `parentItem()` on a QGraphicsItem wrapper you don't intend
   to own — a `None` return converts the wrapper into a delayed delete of the C++ item.**
   Resolve tags/lookups through retained wrappers instead.
3. **Live-app exposure — HARDENED.** The three press-path walks (backdrop `_resolve_data` /
   `_resolve_vertex`, behaviordoc `_resolve_grab`) used to call `parentItem()` from
   `itemAt()`/`items(pos)` hits; a tag-MISS (click on backdrop/line/frame) walked to the
   `None` top and armed the hit item. All three now read the HIT ITEM ALONE — the `_child`
   adopters stamp every child with its anchor's tag in data slots 2/3 (slot 0/1 stays the
   item's own identity, so tag-count fences hold) — and zero `parentItem()` calls remain in
   `workspace/`. Fenced deterministically by the probe pattern:
   `test_a_tag_miss_press_walk_leaves_the_scene_intact` (test_workspace_backdrop.py) and
   `test_a_tag_miss_grab_walk_leaves_the_scene_intact` (test_behaviordoc.py) sweep the
   resolvers over fresh wrappers, kill them, and assert `scene.items()` count is unchanged
   (pre-fix: 9/22 and 26/75 items destroyed by the read-only sweep).
4. **No interpreter/dependency pin.** Suite stays on Python 3.14. On every PySide6 bump,
   run `probe_item_destroyed.py` first.
