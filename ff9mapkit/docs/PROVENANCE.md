# Provenance — ff9mapkit ships no game data

**ff9mapkit contains no Final Fantasy IX game data.** It is an authoring *tool*. Like an emulator or a
ROM‑hack patcher, it operates on assets from a copy of the game **you already own** — it does not
distribute Square Enix's copyrighted content.

A few base assets the kit needs are *derived* from FF9's own field data:

| asset | what it is | how it's obtained |
|---|---|---|
| blank field (`data/blank_field/<lang>.eb.bytes`) | the minimal playable field every built field starts from — a *cleaned* clone of a base field (popups removed, movement fixed, an after‑battle reinit added) | a base field is read from **your** install and a small **patch** (the kit's edits) is applied |
| exit‑region template (`data/region_template.bin`) | the standard field‑exit entry the gateway injector patches | a base field's exit region is read from **your** install + a small patch |
| test fixtures (`tests/fixtures/*`) | a real field script / camera / walkmesh used by the offline test suite | regenerated from **your** install |
| battle-map geometry/textures (`<BBG>.fbx`, `image#.png`) | a real battle background forked into an editable FBX + PNGs by `ff9mapkit battle-import` | read from **your** install at runtime into a user‑chosen dir; gitignored, never committed (no committed battle template — you fork from your own install) |
| minted-scene assets (`scene/*.raw16/.raw17/.eb/.mes`) | a real battle's gameplay/sequence/camera/text, forked by `battle-import --fork-scene` for a tier-c mint | read from **your** install into a user‑chosen dir; gitignored (`*.raw16.bytes`/`*.raw17.bytes`/`scene/eb`/`scene/mes`), never committed. The mint's static `.inb` is *authored* by the kit (pure `struct.pack`), not extracted |

None of those bytes are committed to this repository or packaged in the wheel. Instead the repo ships
only the project's part:

- **copy/insert patches** (`data/provenance/*.patch`) — each is a list of *copy‑from‑offset*
  directives plus the literal bytes the patch changes. A copy directive references your file by
  `(offset, length)`; it does **not** contain the game's bytes. This is exactly how an IPS/BPS/xdelta
  ROM‑hack patch works, and why patches are legally distributable while ROMs are not. (For reference,
  the blank‑field patches are ~70–110 bytes of kit edits over a 956‑byte field; the region patch is
  ~5 bytes.) Verified: `provision.patch_game_runs` asserts no insert run ever duplicates a
  run already present in the source field — so a patch can't smuggle game bytes in disguise.
- a **manifest** (`data/provenance/manifest.json`) — names the base fields to read and records the
  SHA‑256 of every regenerated blob, so extraction self‑verifies it produced exactly the right bytes
  (a hash is a one‑way digest, not a copy of the data).
- **build goldens are hashes too** — the worked example's expected build output embeds the
  game‑derived blank, so the test compares the fresh build's SHA‑256 to the manifest rather than
  shipping the bytes.

## One‑time setup

```powershell
pip install -e ".[assets]"          # the assets extra = UnityPy (reads FF9's p0data assetbundles)
$env:FF9_GAME_PATH = "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"   # optional
# full setup detail (auto-detect, ff9mapkit setup): ../../SETUP.md
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
| `_modelalias.py` | model name → donor‑prefab name (the engine's rename chain: which prefab a battle form / alt outfit actually loads) | `ModelFactory` (upscaleTable, revertUpscaleTable, GetNameFromFF9DBALL, GetGEOID, GetRenameModelPath) | `python -m ff9mapkit._regen_modelalias` |
| `_scenedb.py` | battle‑scene name → encounter id (Info Hub `scenes`) | `FF9BattleDB.SceneData` | `python -m ff9mapkit._regen_scenedb` |
| `_itemdb.py` | item id → name | `RegularItem` (Memoria enum) | — |

These hold only labels (`GEO_MAIN_F0_VIV`, `ANH_MAIN_F0_VIV_WALK`, `BSC_AC_E031`, …) and numeric ids —
no model geometry, animation binary, enemy roster, or stats (those live in your install's `p0data`).
They're committed so the `import` / `animations` / Info Hub (`models` / `scenes` / `catalog`) features
work without a game install.

**Item *stats* are the deliberate exception — read live, never committed.** The Info Hub item *detail*
(weapon power, armor defence, equip bonuses, consumable effects, prices) is game DATA, not a label, so
`itemstats.py` reads it **live from your own install** (`<install>/StreamingAssets/Data/Items/*.csv` —
Memoria's editable item tables) and caches it in-memory. Nothing is baked into the repo or the wheel; if the
install isn't reachable the Info Hub simply shows id + name. Only `_itemdb.py` (item **names**) stays committed.

## What about the `research/` story-flag digests?

The story-flag research folder (`research/`) ships mostly *derived numbers* — flag indices, field
ids, scenario values, area labels — which, like the id ↔ name tables above, are functional
identifiers, not game content. **One file is different in kind and worth naming:
`research/FLAG_LORE.md`**, the per-bit lore digest generated by `research/gen_flag_lore.py` from
**your** install's event + text bundles. To identify *which* dialogue line a flag write sits next
to, a row may quote a short excerpt of the game's English text — hard-capped at 110 characters by
the generator, ~340 distinct excerpts in total (most instances are system messages like
"Received Gil!"), never a scene's continuous dialogue. These are brief identifying quotations, the
way a guide or wiki quotes a line to name a scene — kept committed so the flag research is readable
without a game install. The digest is fully regenerable from your own copy (`research/README.md`
has the commands), and the machine-form output (`research/flag_lore.json`) is gitignored, never
committed. Everything else in `research/` stays in the identifier category.

One further, deliberately tiny exception of the same kind: the save-moogle's default no-mail line
(`content/mognet.py DEFAULT_NOTHING`) is FF9's own four-word stock phrase **"I want mail!  Kupo!"**
— invariant across every donor moogle field, quoted verbatim (double space included) so a kit save
point behaves indistinguishably from a stock one. The same brief-identifying-quotation rationale as
FLAG_LORE's excerpts, granted explicitly by the project owner for the savepoint menu wording
("the wiki-with-dialog case"). These two are the repository's only committed game-text exceptions.

## What about the overworld (world) pillar?

The world lane is the one pillar whose *deliverable* is derived bytes. A field ships as a
`field.toml` recipe; a custom overworld exists solely as deployed `.ff9mesh` overrides, and the
flagship verbs derive them straight from your install: `world-transplant` carries a **real donor
block verbatim** (verts, UVs, tangents copied out of your `p0data`), `world-terrain` reshapes stock
geometry, and even the synthetic `world-island` mint is gated against stock statistics read from
your copy. The same rules as everything above apply, plus two world-specific points:

- **None of those bytes are committed or wheeled.** Deployed worlds live only in *your* mod
  folders. Sharing a deployed world folder is sharing Square‑Enix‑derived bytes — fine on your own
  install, never in this repository or its packages.
- **The shareable artifact is the recipe, not the bytes.** A composed world is reproducible from
  its `world-fuse` layout toml: the compose runs the verbs in a fixed order and records
  `world_manifest.json` (per‑file md5 + the spec table that produced each file) beside the deploy,
  and every write lands in the `.ff9world.jsonl` ledger. Measured: re‑composing the same toml
  writes **zero** changed files — so a recipient with their own install re-runs your toml and gets
  your world, byte for byte, without you ever distributing game-derived data.
- **The atlas lane can launder *third-party* art — the kit now warns and records.**
  `world-atlas-add-tile` paints into the atlas the *engine* resolves, which on a Moguri install is
  Moguri's HD artwork (a third party's work, under its own permissions), and deploys the painted
  whole into your mod folder. When the resolved base is a loose third‑party override, the kit
  warns and writes a `<atlas>.png.provenance.json` sidecar recording the source and a
  `third_party` flag (the taint carries forward across repaints of your own override).
  Distributing a mod folder whose atlas derives from third-party art needs that party's
  permission. The clean-room path: `extract_atlas(source="bundle")` → repaint → `deploy_atlas` —
  that base is your own game's vanilla atlas, same category as every derived asset above.

## What about the engine bundle's SFX probes (runtime process-memory reads)?

The custom‑Memoria engine bundle introduces a category nothing above covers: **reading the game's own
live process memory at runtime.** Engine patches **s52, s53, and s58** (in
[`memoria-patches/`](../../memoria-patches/README.md)), when explicitly armed via `Memoria.ini`
(`[SfxProbe] Enabled=1` / `[SfxHybrid] Enabled=1` — **both default OFF, and both ship off**), read
`FF9SpecialEffectPlugin.dll`'s in‑process state during a summon cast. The scope, documented per patch
in that README, is **staging/choreography only**:

- **What is read:** the summoned creature's root transform and its composed node matrices — the
  pose of the running cast. **Never** the per‑bone skeletal array (which would reconstruct stock
  animation data), no asset bytes are read out, no DLL is patched, and no export function is called.
- **Where it goes:** diagnostic text/JSON logs on the user's own machine, produced from the user's
  own running copy of the game — the same class as the camera‑track instrumentation the probes sit
  beside.
- **What is distributed:** nothing. Nothing read is ever redistributed, and the kit's shipped
  artifacts contain none of it.

## For maintainers

`python -m ff9mapkit.data._regen_provenance` (run against a **vanilla** install) re‑authors the
patches + manifest and verifies they reproduce the current assets byte‑for‑byte. The wheel
`package-data` is deliberately restricted to `data/provenance/*` so a build can never bundle FF9
bytes, even on a machine where `extract-templates` has been run.
