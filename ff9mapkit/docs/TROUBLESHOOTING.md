# Troubleshooting

This page covers the most common first-run failures as
**symptom → cause → fix**. If you haven't done the one-time setup yet, start with
[`SETUP.md`](../../SETUP.md); for what's stock vs. enhanced engine behavior see
[`ENGINE.md`](ENGINE.md); for the "ships no game data" guarantee see [`PROVENANCE.md`](PROVENANCE.md).

> First stop for almost anything: run **`ff9mapkit doctor`** (or `py -m ff9mapkit doctor`). It prints
> the kit version, whether UnityPy is present, the resolved game install, the mod root, and whether
> templates are extracted — most setup problems show up there immediately.

---

## Install & environment

### `ff9mapkit: command not found` / `ModuleNotFoundError: No module named 'ff9mapkit'`

**Cause.** The console script isn't on your `PATH`, or the package was installed from the wrong
directory.

**Fix.** Install from the **package directory** (`ff9mapkit/`, where `pyproject.toml` lives) — not
the repo root:

```powershell
cd ff9mapkit
pip install -e .
```

If the `ff9mapkit` script still isn't found, the module form is identical and always works when
several Pythons are installed:

```powershell
py -m ff9mapkit doctor
```

Run it from the kit root so the local package shadows any other editable install. Python **≥ 3.11**
is required (the kit uses stdlib `tomllib`).

---

### `run extract-templates` / `doctor` says `templates : NOT extracted`

**Symptom.** A byte-level command (build, deploy, golden tests) raises a clear "run
extract-templates" message, or `doctor` reports `templates : NOT extracted`.

**Cause.** The repo ships **no Final Fantasy IX game data**. A handful of base assets (the blank
field every build starts from, the exit-region template, test fixtures) are *derived* from your own
install and must be regenerated once per checkout.

**Fix.** The one-shot **`ff9mapkit setup`** command does this end to end — it detects the install,
persists it to `~/.ff9mapkit.toml`, runs `extract-templates`, and reports engine status:

```powershell
py -m ff9mapkit setup
```

Or do the extraction step by hand — install UnityPy (the `assets` extra), then extract:

```powershell
py -m pip install ff9mapkit[assets]   # or, from a checkout:  pip install -e ".[assets]"
py -m ff9mapkit extract-templates
py -m ff9mapkit doctor          # should now report:  templates : extracted
```

For a read-only / wheel install, point `$env:FF9MAPKIT_DATA` at a writable cache directory before
extracting. See [`PROVENANCE.md`](PROVENANCE.md) for the patches-not-bytes mechanism.

---

### An asset-reading command fails (`import`, `list-fields`, `battle-import`, `export-art`, …)

**Symptom.** A command prints something like *"needs UnityPy (pip install UnityPy) + your FF9
install."* This applies to every command that reads game assets: `import`, `import-all`,
`extract-field`, `extract-templates`, `list-fields`, `export-art`, `battle-import`, `battle-scene`,
`dialogue-import`, `sps`, the `model-*` suite, and the `world-*` extraction commands.

**Cause.** These commands read FF9's `p0data*.bin` assetbundles, which requires **UnityPy** and a
**detected FF9 install**. (UnityPy is the `assets` extra; it isn't pulled in by a bare
`pip install -e .`.)

**Fix.**

```powershell
py -m pip install ff9mapkit[assets]   # or:  pip install -e ".[assets]"  /  py -m pip install UnityPy
py -m ff9mapkit doctor          # confirm  UnityPy : present  AND a resolved game install
```

If UnityPy is present but the game still isn't found, see the next entry.

---

### FF9 install not found

**Symptom.** `doctor` exits non-zero with *"Could not locate the Final Fantasy IX install folder."*

**Cause.** None of the resolution sources pointed at a real install directory.

**Fix.** Run **`ff9mapkit setup`** — it detects the install and persists it to `~/.ff9mapkit.toml`
(then extracts templates and reports engine status in the same pass). The kit resolves the install
in this order:

1. the `--game "<path>"` flag,
2. the `$FF9_GAME_PATH` environment variable,
3. `game_path = "..."` in `~/.ff9mapkit.toml`,
4. auto-detection: the per-game **Steam and GOG registry keys** (the same keys Memoria reads), then
   a scan of Steam's `libraryfolders.vdf` for every Steam library, then the common install folders
   (`Program Files (x86)\Steam\...`, `D:\SteamLibrary\...`, `C:\GOG Games`, `D:\GOG Games`, GOG
   Galaxy).

Both the **Steam** and **GOG** builds are supported. The **Microsoft Store** build is **not
moddable** and is not a supported target.

If auto-detection still misses a non-standard location, set it explicitly (PowerShell — note
`$env:`, not bash `export`):

```powershell
$env:FF9_GAME_PATH = "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
```

or persist it in `C:\Users\<you>\.ff9mapkit.toml`:

```toml
game_path = "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
```

The folder should contain `FF9_Launcher.exe` and a `StreamingAssets` directory. Re-run
`ff9mapkit doctor` (or pass `--game <path>` to override for a single command).

---

## In-game failures

### Black screen on a custom field

A custom field that registers but renders nothing (or shows an invisible player) almost always has
one of three causes.

**(a) The field's `area` is below 10.** The background loader builds the scene name as
`"FBG_N" + area` and reads exactly **two characters** of the area, so single-digit areas (0–9)
black-screen.

> **Fix.** The `area` must be **≥ 10**. When you scaffold from scratch, pass `--area 11` (or any value
> ≥ 10):
>
> ```powershell
> py -m ff9mapkit new MY_ROOM --area 11
> ```

**(b) A global EventDB id collision across stacked mod folders.** The engine's registries are merged
across every mod folder, so a custom id reused in another folder collides — one field then loads a
**null `.eb`** (black screen / invisible player). Diagnose by searching **each stacked folder's**
`DictionaryPatch.txt` for the id — check every folder listed in `Memoria.ini [Mod] FolderNames`:

```powershell
Select-String "FieldScene <id>" "<game>\*\DictionaryPatch.txt"
py -m ff9mapkit doctor          # prints the resolved mod folder's dict patch path as a starting point
```

> **Fix.** Give every custom field a **globally distinct id**, even across stacked folders. Custom ids
> are **≥ 4000**; reach a field with the F6 → Warp menu or via a gateway. (See
> [`GLOBAL_RESOURCES.md`](GLOBAL_RESOURCES.md) for the id namespace and the global-id rule.)

**(c) A field id above 32767.** The engine's `fldMapNo` is an **Int16** (max **32767**). A higher id
registers but is unreachable, and an out-of-range id can break the whole `DictionaryPatch.txt` parse.

> **Fix.** Keep ids within the Int16 range — the custom band is **4000–9899**, with **30000–32767**
> reserved for dev scratch.

---

### After-battle softlock

**Symptom.** A random encounter ends, but control never returns — the screen sits and nothing
resumes.

**Cause.** The field is missing an entry-0 **tag-10 "Main_Reinit"** routine. After a battle the
engine suspends field objects and relies on that routine to fade back in and re-enable movement; a
field cloned from a cutscene field often lacks one.

**Fix.** The kit **emits a Main_Reinit automatically** for any field with encounters, so this only
bites when you hand-author bytecode or splice a script outside the normal build. Use the kit's build
path (or a fork mode that carries the real script) rather than hand-rolling the entry table.

---

### Wrong dialogue but correct behavior — or a "(saved)" edit that still shows the old line

**Symptom.** A field plays its logic correctly (right doors, right events) but shows the **wrong
text** — often another field's lines. Or: a verbatim fork's dialogue was rewritten in the Workspace
**Script** panel, the edit shows **"(saved)"**, but the game still speaks the old line.

**Cause.** Two independent gaps sit between a saved edit and the screen:

1. **The edit isn't deployed yet.** A Script-panel rewrite is recorded in the field's `field.toml`
   (as a `[[logic_edit]]`); the GUI save does **not** touch the `.mes` — the build rewrites it. An
   **F6 → Reload field** *without* a redeploy just re-reads the stale `.mes`.
2. **Text-block shadowing.** A field reads dialogue from `field/<text_block>.mes`, and the engine
   serves that block from the **highest-priority** folder in `Memoria.ini FolderNames`. Campaign
   members and the deploy test slots all default to the shared block **1073**, so if a
   higher-priority folder (a churned `FF9CustomMap`, a leftover prior-journey folder, …) also
   defines the same block, it **shadows** the edit — the engine shows *that* folder's old text.
   (The *flags* are still correct, which is why the behavior looks right. The same gotcha hits
   `[[on_entry]]` lines.)

**Fix.**

1. **Rebuild + redeploy, then reload.** `py tools/deploy_field.py …` (single field) or, for a
   journey/campaign member, `ff9mapkit deploy-campaign <campaign.toml> --apply` /
   `ff9mapkit deploy-journey <journeys.toml> --apply` (the checkout scripts
   `py tools/deploy_campaign.py` / `py tools/deploy_journey.py` are thin shims over the same
   commands) — then **F6 → Reload field** (or relaunch).
2. **Clear the shadow.** Deploy your folder higher in `FolderNames`, remove the higher folder's
   copy of the block, or pin a unique `[field] text_block` — it must be a **real `MesDB` id** that
   no higher-priority folder defines (arbitrary ids don't load):

   ```toml
   [field]
   text_block = 1234        # a real MesDB id that no stacked folder above you defines
   ```

The deploy step guards this: `deploy_field` **and** `deploy_campaign` / `deploy_journey` run the
text-block **shadow check** and print a `TEXT SHADOWED: …` warning that names the blocking folder
and a safe alternative block; the Script panel also flags a dialogue edit on the shared default
1073. Diagnose directly:

```powershell
py -c "from ff9mapkit.deploystack import check_text_block_shadow, shadow_warning; from ff9mapkit.config import find_game_path; print(shadow_warning(check_text_block_shadow(find_game_path(None), '<your-mod-folder>', <block>)) or 'clear')"
```

**Journey deploys are windowed against the sharper cross-campaign case.** A fresh journey deploy
gives each campaign a **disjoint custom text-block window** (each block registered via a
DictionaryPatch `MessageFile` line), so two campaigns whose donors share a mesID no longer collide,
regardless of `FolderNames` order. `deploy_journey` still warns (`TEXT-BLOCK COLLISION: block N
shipped by …`) when a mix of old (un-windowed) and new folders is hand-stacked — reorder
`FolderNames` so the campaign whose dialogue matters most sits highest, or re-deploy the whole
journey so every campaign gets a window.

---

### Changes aren't showing up in-game

**Symptom.** You redeployed, but the field looks unchanged.

**Cause.** Most edits to the *current* field can be hot-reloaded, but some changes are only read at
startup.

**Fix.** With the bundled custom engine, press **F6 → Reload field** — it re-reads the current field's
`.eb`/`.mes`/scene/walkmesh/art from disk, no relaunch.

**Relaunch the game** only when F6 Reload can't pick a change up:

- the **first deploy of a new id** (it has to register its `DictionaryPatch.txt` line),
- a **`BattlePatch.txt`** change (battle tuning / per-encounter BGM),
- **start-state CSVs** or **`TextPatch.txt`** item names (read at startup / New Game),
- an **engine DLL rebuild**.

> **Note.** The **F6 debug menu needs the bundled custom engine** — it ships in the public engine
> bundle (`dwix-custom-memoria-*.zip`, installed by the Windows installer or by
> `ff9mapkit setup --install-engine <zip>`, which backs up the stock DLLs automatically), but it is
> not part of **stock** Memoria. On a stock install, reach a custom field through a **gateway** from
> a field you can already walk to, or by wiring it to **New Game**. See [`ENGINE.md`](ENGINE.md) for
> what's stock vs. enhanced.

---

## Optional features

### `save-edit` (or other save commands) fails

**Symptom.** A save command errors with *"save editing needs pycryptodome."*

**Cause.** FF9's `SavedData_ww.dat` is AES-encrypted; reading/writing it needs **pycryptodome**,
which the kit imports lazily.

**Fix.** Install the `save` extra:

```powershell
pip install -e ".[save]"        # or:  py -m pip install pycryptodome
```

(Inspecting a Memoria plaintext extra-save needs no crypto; only the encrypted container does.)

---

### The GUI won't launch

**Symptom.** The Workspace prints a prompt about a missing dependency, or nothing opens.

**Cause.** The desktop Workspace is built on **PySide6**, an optional extra.

**Fix.** Install the `gui` extra, then launch. For an **installed** copy (pip / uv / the Windows
installer — no repo checkout), the launcher is the **`ff9mapkit-workspace`** entry point:

```powershell
py -m pip install ff9mapkit[gui]
ff9mapkit-workspace
```

From a **repo checkout**, launch the front door directly:

```powershell
pip install -e ".[gui]"         # or:  py -m pip install PySide6
py apps\ff9_workspace.pyw
py apps\ff9_workspace.pyw --smoke  # headless self-check
```

---

### `pytest` skips a bunch of tests

**Symptom.** Running the suite reports many **skipped** tests.

**Cause.** The byte-level (golden-master) tests need the derived base assets, which are skipped until
`extract-templates` has run. The **pure-logic** tests (camera math, the editor, packaging) always
run regardless.

**Fix.** Extract the templates once (see above), then re-run:

```powershell
py -m ff9mapkit extract-templates
py -m pytest -n 6               # run from the ff9mapkit/ package dir
```

---

## See also

- [`SETUP.md`](../../SETUP.md) — install, configuration, the dev loop, and your first field.
- [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) — known rough edges and engine limitations, when a symptom here doesn't match.
- [`ENGINE.md`](ENGINE.md) — what runs on stock Memoria vs. the bundled fork-fidelity patches.
- [`PROVENANCE.md`](PROVENANCE.md) — why the kit ships no game data and how `extract-templates` works.
- [`GLOBAL_RESOURCES.md`](GLOBAL_RESOURCES.md) — the id / flag / text namespaces and the global-id rule.
