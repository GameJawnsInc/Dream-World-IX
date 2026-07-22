# Battle-Locations → Workspace GUI: UI design brief

Designer spec for wiring the `ff9mapkit.battle.locate` pillar into the PySide6 Workspace. **Research
only** — no app-code was edited producing this. The builder implements the integration points below.

Pillar recap (already merged, `ff9mapkit/ff9mapkit/battle/locate.py`): a census that joins field→scene
(`SetRandomBattles`/`Battle`) to region arcs plus real monster/attack names. Public surface:
`build_map(game, force=)` · `cached_map(game)` · `scene_sites` · `scene_places` · `scene_label` ·
`field_battles` · `monster_names` · `attack_names` · `find_monster(query)` · `classify` ·
`unresolved_report`. Cold build ≈ 9 s (census ~6 s + two UnityPy passes); warm (memo or disk JSON) is
instant. `cached_map()` NEVER builds — the reuse-if-present probe.

---

## 0. The load-bearing constraint, and the single mechanism that satisfies it

The ~9 s cold census must never run on the Qt GUI thread. Two facts make this manageable:

- `locate.build_map()` **memoizes into the module-level `locate._MEMO`** and writes a disk cache. Once
  *any* surface builds it, `locate.cached_map()` is instant for the whole process — scene detail, the
  field-editor scene picker, and battledoc all go warm together. So we need exactly **one** async build
  front-door, and everything else reads warm-only.
- `locate.cached_map()` returns the warm map or `None` — the perfect "reuse-if-present, never build"
  probe every read site uses.

**The mechanism** (one async build, everything else warm-only):

1. A single **"Build battle index"** async worker (the Info Hub owns it) — the *only* place a cold build
   runs, off the GUI thread, using the importdoc find-rooms worker pattern (thread + `Signal` + a busy
   button; §1.4).
2. Every other read site (`_scene_usage`, `_encounter_entries`, battledoc, the scene picker) is
   **warm-only** — it calls `cached_map()` and degrades gracefully to a baked/plain fallback when `None`.
   No read site may call `build_map()` / `monster_names()` / `scene_places()` on the GUI thread without a
   prior `cached_map() is not None` guard.

### 0.1 A correctness fix this pulls in (do it first)

`workspace/forms_qt.py::_scene_usage` (line ~550) TODAY calls `loc.monster_names(sid)` /
`loc.scene_places(sid)` directly, each of which routes through `_map()` → `build_map()`. On a cold cache
**that is a ~9 s freeze on the GUI thread**, the moment a user opens *any* battle-scene detail in the Info
Hub. The existing docstring even rationalizes it ("paid once per session, on the first scene the user
opens"). For an Encounters experience that is *all* scenes, this is unacceptable.

**Fix:** make `_scene_usage` warm-only. Prepend a probe:

```python
def _scene_usage(scene_id):
    global _locate_mod
    try:
        if _locate_mod is None:
            from ..battle import locate as _locate_mod_
            _locate_mod = _locate_mod_
        loc = _locate_mod
        if loc.cached_map() is None:      # NEW: never trigger a cold build on the GUI thread
            return None                   # cold -> bare kind/id facts, exactly the no-install degrade
        ...                               # unchanged below: monster_names/scene_places now hit the memo
```

Once `cached_map()` is non-`None` (memo or disk), the downstream `monster_names`/`scene_places` calls hit
the memo and never rebuild. This is a cheap standalone win for the *existing* scene detail too.

---

## (a) The Encounters browse/search experience in the Info Hub

### 1.1 Home: a new section in the existing `CatalogLibrary`, plus an async build button

The Info Hub library (`workspace/forms_qt.py::CatalogLibrary`, the sectioned catalog with a category
sidebar + per-section list + rich detail pane) is the right host — it already *is* the "browse/search by
name → labeled rows → detail pane with a Copy-snippet" experience the brief asks for. We add:

- A new picker-only infohub kind **`"encounter"`** (like `realfield`/`song`: NOT in `infohub.KINDS`, so it
  never bloats the kitchen-sink browse or forces work at an unrelated picker).
- The kind listed in the library sidebar (`_LIBRARY_ORDER`, `_KIND_LABEL`, `_HUB_HELP`) as **"Encounters"**.
- A **"Build battle index"** button in the library that runs the one async cold build (§1.4).

Why a section and not a standalone dialog: the brief says "in the Info Hub … follow the existing
kind/section pattern (the realfield kind … is the freshest precedent)". The section reuses the sidebar,
the search box, the list, the detail renderer, and Copy-name/Copy-snippet verbatim — the only net-new code
is the kind's entry builder, one detail branch, the scene_usage extension, and the async build button.

### 1.2 infohub.py — the `encounter` kind (warm rich / cold plain, NEVER builds)

Integration points in `ff9mapkit/ff9mapkit/infohub.py`:

- **New builder**, placed right after `realfield_entries` (~line 201), mirroring `_song_entries`'s
  "cheap-path-only unless forced" discipline:

```python
def encounter_entries() -> list:
    """Every reachable battle scene as an `encounter` Entry, labeled with its real monsters + place when a
    warm battle map exists, else the baked BSC name. NEVER builds the ~9s census -- reads locate.cached_map()
    only (warm memo/disk), exactly as _song_entries(force=False) reads only the already-extracted cache.
    NOT memoized: warmth changes at runtime (after a Build), and the in-memory label build is sub-ms."""
    try:
        from .battle import locate as _loc
        bm = _loc.cached_map()                       # WARM ONLY -- None when cold
    except Exception:
        bm = None
    out = []
    if bm is not None:                               # warm: rich labels, only the reached ('placed') scenes
        for sid in sorted(bm.scene_sites):
            label = _loc.scene_label(sid)            # "Goblin, Fang -- Evil Forest (field 250, random)"
            cls = bm.classification.get(sid, "placed")
            out.append(Entry("encounter", label, None, f"battle scene #{sid} -- {cls}", sid))
        return out
    from . import catalog as _cat                    # cold: never-empty baked fallback (BSC name only)
    for nm, sid in _cat.battle_scenes():
        out.append(Entry("encounter", nm, None, f"battle scene #{sid} (build the battle index for real names)", sid))
    return out
```

  The rich `name` puts BOTH the monsters and the place in the entry name, so `infohub.browse`'s existing
  substring match over `name`/`summary` matches a **monster** query *and* a **place** query with zero new
  search code — "goblin" and "evil forest" both hit.

- **`browse()`** (~line 442, alongside the `song`/`realfield` picker-only hooks):

```python
if "encounter" in want:            # picker-only kind (NOT in KINDS): only when explicitly requested
    extra = extra + encounter_entries()
```

- **`snippet()`** (~line 470, the branch table): the encounter block, id-first with a label comment:

```python
if e.kind == "encounter":
    return f"[encounter]\nscene = {e.ident}  # {e.name}"
```

  (The static `scene` kind already emits `[encounter]\nscene = {id}` at line 487 — the encounter kind is
  its rich, install-backed sibling; both stay consistent.)

- **`detail()`** (~line 549): route `encounter` through the **existing scene branch** — an encounter's
  `ident` IS a scene id, so classification/enemies/place/locations render identically. The one addition is
  **attacks** (§1.3). Concretely, extend the scene-branch guard `if e.kind == "scene":` (line 615) to
  `if e.kind in ("scene", "encounter"):` and add the attacks fact from the hook return. `d.snippet` is
  already the `[encounter]` block via the snippet branch above.

**Provenance note (from the pillar memory):** scene ids and model ids are the same `int` space in two
unrelated tables. The encounter kind rides the **scene** detail path and the **`scene_usage_fn`** hook
(never `usage_fn`, which is model-keyed) — the existing `test_scene_usage_fn_does_not_leak_into_model_branch`
discipline is preserved.

### 1.3 The `scene_usage_fn` extension — add attacks

The Info Hub detail (and the Encounters section) should show attack names, which `locate.attack_names`
already provides but the current hook drops. Two tiny edits:

- `workspace/forms_qt.py::_scene_usage` (~line 573) — add to the returned dict:
  `"attacks": [a for a in (loc.attack_names(sid) or []) if a]`.
- `infohub.py::detail` scene/encounter branch (~line 632, right after the `enemies` fact) — emit it:
  `atks = [a for a in (info.get("attacks") or []) if a]; if atks: d.facts.append(("attacks", ", ".join(atks)))`.

Backward-compatible: absent key → no fact (the existing per-key-degrade tests already assert this shape).
The "found-in fields" the brief asks for is exactly `d.locations` → the detail renderer's existing
**"Appears in"** block (`_render`, line 822) — no renderer change needed.

### 1.4 The async cold build — the one place a census runs off-thread

Model it on `workspace/importdoc.py`'s find-rooms worker (the picked-wave precedent): a `Signal(object)`,
a daemon thread that runs the heavy in-process call and emits the result-or-Exception, a busy button, and
a `RuntimeError`-guarded emit for teardown-during-sweep. In `CatalogLibrary.__init__`:

```python
_index_ready = Signal(object)         # class attr: emits None (ok) or an Exception, from the build thread
...
self._index_ready.connect(self._on_index_ready)
self._index_busy = False
```

The **"Build battle index"** button (mounted in the Encounters section header / the detail pane's empty
state; disabled/hidden for other sections):

```python
def _build_index(self):
    from ..battle import locate as loc
    if loc.cached_map() is not None:            # already warm -> just refresh the section
        return self._refresh_list()
    if self._index_busy:
        return
    self._index_busy = True
    self.build_btn.setEnabled(False)
    self.build_btn.setText("Building battle index… (~10 s)")
    def _work():
        try:
            loc.build_map()                     # census + name scan; memoizes locate._MEMO + writes disk
            res = None
        except Exception as e:                  # noqa: BLE001 -- no install / UnityPy -> surfaced below
            res = e
        try:
            self._index_ready.emit(res)         # back to the GUI thread
        except RuntimeError:
            pass                                # dialog torn down mid-build -> nothing to deliver to
    threading.Thread(target=_work, name="ff9-battle-index", daemon=True).start()

def _on_index_ready(self, res):
    self._index_busy = False
    self.build_btn.setEnabled(True)
    self.build_btn.setText("Rebuild battle index")
    if isinstance(res, Exception):
        return QMessageBox.warning(self, "Couldn't build the battle index",
            f"{res}\n\n(Reading battle locations needs your FF9 install + UnityPy — check "
            "Settings ▸ Setup & health.)")
    self._refresh_list()                        # everything is warm now: rich labels + rich detail
```

Because `build_map()` warms `locate._MEMO`, a single Build lights up rich labels in the section list, rich
scene/encounter detail, the field-editor scene picker, AND battledoc — for the rest of the session.

### 1.5 Empty / cold / no-install states (graceful, per constraint)

- **Cold cache, install present:** the Encounters section still lists every scene via the baked fallback
  (BSC names), and the detail pane shows the bare `kind/id/bsc name` facts. A one-line hint + the **Build
  battle index** button invite the one-time ~10 s warm-up. Nothing blocks; nothing auto-builds.
- **Sidebar counts:** `_build_categories` (line 691) calls `infohub.browse("", kinds=None)` which does NOT
  include the picker-only `encounter` kind — so the sidebar count for Encounters must come from a
  **build-free** call. Add one explicit `len(infohub.encounter_entries())` when composing the sidebar
  (encounter_entries never builds). This satisfies "counts must not force a cold build at dialog-open".
- **No install / no UnityPy:** `cached_map()` → `None`, the fallback lists baked BSC names, and the Build
  button's worker surfaces the standard "needs your FF9 install + UnityPy — Settings ▸ Setup & health"
  warning. The detail pane degrades to bare facts. Identical shape to the existing model `usage_fn` degrade.

### 1.6 Discoverability

`CatalogLibrary` is opened from the toolbar `act_hub` (shell.py line 1193) and the command palette
("Browse catalog (Info Hub)", line 4378). The Encounters section rides that same door — no new top-level
action required. Optionally add a palette alias "Browse encounters (Info Hub)" that opens the library and
pre-selects the Encounters row (nice-to-have, not required this round).

---

## (b) Pick-and-fill on the field editor's Encounter form

`ff9mapkit/ff9mapkit/editor/forms.py::ENCOUNTER_SPEC` (line 148) already declares the scene field with
`catalog="scene"`:

```python
Field("scene", "Battle scene id", OPTINT, "e.g. 67 = Evil Forest; blank = no random battles", catalog="scene"),
```

The generic `catalog=` mechanism is already wired end-to-end: `forms_qt.build_form`'s `browse()` (line 204)
→ `pick_catalog` → `CatalogPicker` with `want_id=True` (the field is `OPTINT`) → returns the entry's id
string. The only gap is the **label**: the `scene` kind's entries carry the static summary
`battle scene #67` (BSC name), because `scene` is a KINDS member built install-free.

**Change (one line):** point the field at the rich picker-only kind, keeping `scene` as the never-empty
fallback:

```python
Field("scene", "Battle scene id", OPTINT, "e.g. 67 = Evil Forest; blank = no random battles",
      catalog="encounter,scene"),
```

Data flow: `CatalogPicker` (line 350) with `kinds=["encounter","scene"]` calls `infohub.browse(kinds=...)`;
`browse` adds `encounter_entries()` (warm rich / cold baked) plus the static `scene` entries. When the
index is warm the encounter rows are rich-labeled ("Goblin, Fang — Evil Forest") and, being in `extra`,
sort **first** (`entries = extra + _all_entries()`); the picker returns `want_id` → the numeric scene id
(line 469). When cold, `encounter_entries()` returns the baked BSC list (same info as `scene`, so the
picker is still fully usable — just without monster/place names until the user builds the index once).

Notes for the builder:
- **No CatalogPicker code change.** It already handles multi-kind, `want_id`, and picker-only kinds via
  `infohub.browse`. It calls `infohub.detail` only for `sps`/`sps_template` (line 434) — never for
  `scene`/`encounter` — so the picker triggers **no** census. The warm/cold behavior is entirely inside
  `encounter_entries()`.
- **Minor duplication when warm:** the same scene appears once as `[encounter]` (rich) and once as
  `[scene]` (plain). Accepted — encounter sorts first, both return the same id, and the `[kind]` tag in the
  row disambiguates. (A cross-kind de-dupe in `browse` is possible but out of scope; noted, not built.)
- The scene field stays `OPTINT` → the picker's `want_id` path already returns the id string; blank = no
  random battles, unchanged.

---

## (c) Cheap battledoc enrichment still missing after `scene_usage_fn`

`workspace/battledoc.py` already shows the donor **raw16 baseline** (enemy stats) and **donor scene facts**
(flags/counts) read from the forked `scene/` dir. What it does NOT show is **where this scene is actually
fought in the real game** and **who fights it** — which `locate` now provides.

**Add one warm-only read-only panel on the `[battlemap]` (Map) node** — the node that carries
`scene_id`/`scene_name`. In `BattleDoc._mount` (line 469), for `kind == _MAP`, when the battle.toml's
`battlemap.scene_id` is set and `locate.cached_map()` is non-`None`, mount a `_facts_panel`
(the existing read-only grid helper, line 653) titled **"Fought in the real game"** with:

- `locate.scene_label(sid)` — the one-line "monsters — place (field, kind)" summary, and/or
- `locate.scene_places(sid)` grouped place lines + `locate.monster_names(sid)` as a "Monsters" fact.

```python
if kind == _MAP:
    loc_panel = self._location_panel(entity)         # NEW, warm-only, best-effort
    if loc_panel is not None:
        self.host_lay.addWidget(loc_panel)
...
def _location_panel(self, battlemap):
    """Read-only 'where is this scene fought / by whom' for the [battlemap] node -- WARM ONLY (locate.cached_map),
    best-effort. None when there's no scene id, no warm index, or no install (never builds, never blocks)."""
    sid = battlemap.get("scene_id")
    if not isinstance(sid, int):
        return None
    try:
        from ..battle import locate as loc
        if loc.cached_map() is None:                 # cold -> no panel (the Info Hub owns the build)
            return None
        places = loc.scene_places(sid)
        mons = [m for m in (loc.monster_names(sid) or []) if m]
    except Exception:                                # noqa: BLE001 -- purely additive, never fatal
        return None
    if not places and not mons:
        return None
    pairs = [("Monsters", ", ".join(mons) or "(no name data)")]
    for g in places:
        loc_name = g["arc_name"] or "an unmapped field"
        pairs.append((loc_name, f"field(s) {', '.join(str(f) for f in g['fields'])} ({'/'.join(g['kinds'])})"))
    return self._facts_panel("Fought in the real game", pairs)
```

Scope guard: warm-only (never triggers a build inside the doc), MAP-node-only, best-effort. It is
purely additive context for a fork/override — the same "found in" line the `battle-scene` CLI already
prints (cli.py `_print_found_in_line`, line 3847), surfaced in the doc. Nothing else in battledoc changes.

**Not this round:** a `[[battle_text]]` authoring surface, enriching the Formation/enemy-slot nodes with
attack names, or any write path. The PLAN.md already parks `[[battle_text]]` as out of scope.

---

## Data-flow summary

```
                     locate.build_map()  ── async, ONE place ──►  locate._MEMO (+ disk JSON)
                            ▲                                            │  (warm for the whole process)
   CatalogLibrary          │                                            ▼
   "Build battle index" ───┘                       locate.cached_map()  ── warm-only reads ──►
                                                            ├─ infohub.encounter_entries()  (kind list + counts)
                                                            ├─ forms_qt._scene_usage()      (scene/encounter detail)
                                                            ├─ CatalogPicker via catalog="encounter,scene"  (b)
                                                            └─ battledoc._location_panel()  (c)
```

One cold build (off-thread) warms every read site. Every read site degrades gracefully when cold.

## Names introduced

- `infohub.encounter_entries()` — public, build-free; the `encounter` kind builder.
- kind string `"encounter"` (picker-only, not in `KINDS`); sidebar label `"Encounters"`.
- `CatalogLibrary._index_ready` (Signal), `._build_index()`, `._on_index_ready()`, `.build_btn`.
- `_scene_usage` gains a `"attacks"` key + a `cached_map() is None` guard.
- `BattleDoc._location_panel()`.

## What NOT to build this round (honest scope)

- No standalone Encounters dialog — it is a section of the existing `CatalogLibrary`.
- No new CLI verb (the `encounters` verb already exists) and no change to `locate.py`'s public surface.
- No cross-kind de-dupe in `infohub.browse` (accept the warm encounter/scene duplication).
- No `[[battle_text]]` authoring surface; no write paths; no enemy-slot/Formation attack-name enrichment.
- No disk-cache game-keying change (locate keeps its one-slot cache; `force=` on install switch).
- No auto-build anywhere — the census is only ever run by the explicit "Build battle index" button.

---

## Test plan (both lanes, mirroring `test_battle_locate.py` / `test_infohub_scene_locations.py`)

### Offline lane — synthetic `BattleMap` via `locate._MEMO` injection, and the fake-hook contract

`tests/test_infohub_encounters.py` (new):
- `encounter_entries()` **cold** (empty `_MEMO`, no disk): returns the baked BSC fallback, non-empty, each
  `Entry.kind == "encounter"`, `ident` an int; summary carries the "build the battle index" hint.
- `encounter_entries()` **warm** (inject a synthetic `BattleMap` with `scene_sites`/`names`/`classification`
  via the `_inject` helper): rows are rich-labeled (name contains a monster AND the place), one per
  `scene_sites` id; `ident` = scene id.
- `browse(kinds=["encounter"])` returns the encounter entries; **`browse("goblin")`** and
  **`browse("evil forest")`** both match the same warm row (monster + place axes, via the name substring).
- `browse()` with default `kinds=None` does **NOT** include encounter (picker-only, not in `KINDS`).
- `snippet(encounter_entry)` == `"[encounter]\nscene = <id>  # <label>"`.
- `detail(encounter_entry, scene_usage_fn=fake)` populates classification/enemies/**attacks**/place +
  `d.locations` (extend the fake hook to return `"attacks"`); `detail(..., scene_usage_fn=None)` degrades
  to bare `kind/id/bsc name` facts (encounter rides the scene branch).
- Regression: `scene_usage_fn` still does not leak into the model branch; `usage_fn` still does not fire
  for an encounter entry (id-space discrimination preserved).

`tests/test_infohub_scene_locations.py` (extend): add an `attacks` assertion to the fake-hook test; assert
the per-key degrade still holds when `attacks` is absent.

### Offline lane — GUI wiring (Qt, no install)

`tests/test_workspace_smoke.py` (or a scoped `test_workspace_encounters.py`), all with an injected
synthetic warm map so nothing builds:
- `CatalogLibrary` shows an **"Encounters"** sidebar row with a build-free count; selecting it lists the
  injected rich rows; the detail pane renders enemies/attacks/places/"Appears in"/`[encounter]` snippet;
  Copy-snippet puts the `[encounter]` block on the clipboard.
- `_scene_usage` **cold** guard: with `_MEMO` empty AND monkeypatched so `build_map` would raise if called,
  `_scene_usage(67)` returns `None` and calls no builder (proves no GUI-thread cold build).
- The async build path: drive `_build_index` with `loc.build_map` monkeypatched to a fast stub that seeds
  `_MEMO`; assert `_on_index_ready(None)` refreshes to rich rows, and `_on_index_ready(Exception(...))`
  warns without crashing.
- **(b)** `ENCOUNTER_SPEC`'s scene field has `catalog == "encounter,scene"`; a `CatalogPicker` over those
  kinds with `want_id=True`, fed an injected warm map, returns the chosen scene **id** string (extend the
  existing forms_qt picker smoke that already asserts `want_id`).
- **(c)** `BattleDoc._location_panel` with an injected warm map returns a facts panel for a `scene_id`;
  returns `None` when cold (`_MEMO` empty) and when `scene_id` is absent — and never calls `build_map`.

### Game-gated lane — real install (`_game_ready()` skip idiom)

- `encounter_entries()` after a real `build_map()`: contains scene 67 labeled with **Evil Forest** and
  **Goblin** (the same anchor `test_battle_locate.py`/`test_infohub_scene_locations.py` use).
- `CatalogLibrary` Encounters detail for the scene-67 row (via the real `_scene_usage`) shows
  classification `placed`, enemies incl. Goblin/Fang, attacks non-empty, and an "Evil Forest / field 250"
  location.
- `BattleDoc._location_panel` for a battle.toml whose `scene_id == 67` shows the Evil-Forest place line
  after a real build.
