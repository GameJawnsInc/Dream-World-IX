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

## What about the field‑name and animation tables?

`ff9mapkit/_fieldtable.py` maps each field's background folder to its event‑script name (used by
`import` / `list-fields`). `ff9mapkit/_animdb.py` maps the playable characters' animation ids to
their names (used by the `animations` catalog / cutscene gesture names). Both are short **functional
identifiers** derived from the **open‑source Memoria** project's public tables (`EventEngineUtils` /
`FF9DBAll`), not extracted from the game — i.e. the same data Memoria already publishes. They are kept
in the repo for those features; regenerate with `python -m ff9mapkit._regen_fieldtable` and
`python -m ff9mapkit._regen_animdb`.

## For maintainers

`python -m ff9mapkit.data._regen_provenance` (run against a **vanilla** install) re‑authors the
patches + manifest and verifies they reproduce the current assets byte‑for‑byte. The wheel
`package-data` is deliberately restricted to `data/provenance/*` so a build can never bundle FF9
bytes, even on a machine where `extract-templates` has been run.
