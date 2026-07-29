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
