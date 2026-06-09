# Provenance — ff9mapkit ships no game data

**ff9mapkit contains no Final Fantasy IX game data.** It is an authoring *tool*. Like an emulator or a
ROM‑hack patcher, it operates on assets from a copy of the game **you already own** — it does not
distribute Square Enix's copyrighted content.

A few base assets the kit needs are *derived* from FF9's own field data:

| asset | what it is | how it's obtained |
|---|---|---|
| blank field (`data/blank_field/<lang>.eb.bytes`) | the minimal playable field every built field starts from — a *cleaned* clone of a base field (popups removed, movement fixed, an after‑battle reinit added) | a base field is read from **your** install and a small **patch** (our edits) is applied |
| exit‑region template (`data/region_template.bin`) | the standard field‑exit entry the gateway injector patches | a base field's exit region is read from **your** install + a small patch |
| test fixtures (`tests/fixtures/*`) | a real field script / camera / walkmesh used by the offline test suite | regenerated from **your** install |
| battle-map geometry/textures (`<BBG>.fbx`, `image#.png`) | a real battle background forked into an editable FBX + PNGs by `ff9mapkit battle-import` | read from **your** install at runtime into a user‑chosen dir; gitignored, never committed (no committed battle template — you fork from your own install) |
| minted-scene assets (`scene/*.raw16/.raw17/.eb/.mes`) | a real battle's gameplay/sequence/camera/text, forked by `battle-import --fork-scene` for a tier-c mint | read from **your** install into a user‑chosen dir; gitignored (`*.raw16.bytes`/`*.raw17.bytes`/`scene/eb`/`scene/mes`), never committed. The mint's static `.inb` is *authored* by the kit (pure `struct.pack`), not extracted |

None of those bytes are committed to this repository or packaged in the wheel. Instead the repo ships
only **our** part:

- **copy/insert patches** (`data/provenance/*.patch`) — each is a list of *copy‑from‑offset*
  directives plus the literal bytes **we** changed. A copy directive references your file by
  `(offset, length)`; it does **not** contain the game's bytes. This is exactly how an IPS/BPS/xdelta
  ROM‑hack patch works, and why patches are legally distributable while ROMs are not. (For reference,
  the blank‑field patches are ~70–110 bytes of our edits over a 956‑byte field; the region patch is
  ~5 bytes.)
- a **manifest** (`data/provenance/manifest.json`) — names the base fields to read and records the
  SHA‑256 of every regenerated blob, so extraction self‑verifies it produced exactly the right bytes
  (a hash is a one‑way digest, not a copy of the data).
- **build goldens are hashes too** — the worked example's expected build output embeds the
  game‑derived blank, so the test compares the fresh build's SHA‑256 to the manifest rather than
  shipping the bytes.

## One‑time setup

```bash
pip install -e .
export FF9_GAME_PATH="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
pip install UnityPy                 # reads FF9's p0data assetbundles
ff9mapkit extract-templates        # regenerate the base assets into a local (gitignored) cache
ff9mapkit doctor                   # should now report: templates : extracted
```

`extract-templates` writes into the package's `data/` dir by default (works for an editable/clone
install). Point `$FF9MAPKIT_DATA` at a writable directory for a read‑only wheel install or a shared
cache. Until it's run, the loaders raise a clear "run extract-templates" message and the byte‑level
test suite is skipped (the pure‑logic suite — camera math, the editor, packaging — still runs).

## What about the field‑name, model, animation, item, and battle‑scene tables?

Several small `ff9mapkit/_*.py` modules hold **id ↔ name** lookup tables. Each is a short list of
**functional identifiers** — never game bytes — transcribed from the **open‑source Memoria** project's
public tables, i.e. the same data Memoria already publishes, *not* extracted from the game:

| module | maps | Memoria source table | regenerate |
|---|---|---|---|
| `_fieldtable.py` | field background folder → event‑script name (`import` / `list-fields`) | `EventEngineUtils` | `python -m ff9mapkit._regen_fieldtable` |
| `_animdb.py` | the 8 playable characters' anim id → name (cutscene gestures) | `FF9DBAll.AnimationDB` | `python -m ff9mapkit._regen_animdb` |
| `_animdb_all.py` | **all** anim ids → names (Info Hub model→animation join) | `FF9DBAll.AnimationDB` | `python -m ff9mapkit._regen_animdb_all` |
| `_modeldb.py` | actor/field model id → `GEO_…` name (Info Hub `models`) | `FF9BattleDB.GEO` | `python -m ff9mapkit._regen_modeldb` |
| `_scenedb.py` | battle‑scene name → encounter id (Info Hub `scenes`) | `FF9BattleDB.SceneData` | `python -m ff9mapkit._regen_scenedb` |
| `_itemdb.py` | item id → name | `RegularItem` (Memoria enum) | — |

These hold only labels (`GEO_MAIN_F0_VIV`, `ANH_MAIN_F0_VIV_WALK`, `BSC_AC_E031`, …) and numeric ids —
no model geometry, animation binary, enemy roster, or stats (those live in your install's `p0data`).
They're committed so the `import` / `animations` / Info Hub (`models` / `scenes` / `catalog`) features
work without a game install.

## For maintainers

`python -m ff9mapkit.data._regen_provenance` (run against a **vanilla** install) re‑authors the
patches + manifest and verifies they reproduce the current assets byte‑for‑byte. The wheel
`package-data` is deliberately restricted to `data/provenance/*` so a build can never bundle FF9
bytes, even on a machine where `extract-templates` has been run.
