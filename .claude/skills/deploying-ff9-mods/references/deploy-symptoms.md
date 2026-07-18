# Deploy symptoms — symptom -> cause -> fix

Lookup for post-deploy failures. Canonical sources: `ff9mapkit/docs/TROUBLESHOOTING.md` (user-facing,
fullest fix text) and the memory recipes `project-ff9-eventdb-id-collision` /
`project-ff9-text-block-shadow`. Mechanism lines below are quoted verbatim from those files.

## Contents

- [Quick table](#quick-table)
- [Black screen: null-.eb (global EventDB id collision)](#black-screen-null-eb-global-eventdb-id-collision)
- [Black screen: other DictionaryPatch variants](#black-screen-other-dictionarypatch-variants)
- [Wrong text, right flags (text-block / .mes shadow)](#wrong-text-right-flags-text-block--mes-shadow)
- [After-battle softlock](#after-battle-softlock)
- ["Nothing changed after deploy" / when to relaunch](#nothing-changed-after-deploy--when-to-relaunch)

## Quick table

| Symptom | Cause | Fix |
|---|---|---|
| Field registered + scene renders, but black screen / invisible player (null `.eb`) | Global EventDB id collision across stacked mod folders | Pick an id no other stacked folder claims |
| Black screen on a BG-borrow field | `area` below 10 | `area` >= 10 (see the `authoring-ff9-scenes` skill) |
| Id registers but is unreachable; or the whole DictionaryPatch stops registering | Field id above 32767 (Int16 `fldMapNo`) | Stay in-band: custom 4000-9899, scratch 30000-32767 |
| Black screen leaving a field to the OVERWORLD; log names a fork `.eb` under a `World/` path | Field ids collided with the reserved world-map band 9000-9012 | Re-fork off the band (it is a hole in the custom range) |
| New-Game-only black screen; DictionaryPatch shorter than its backups | A wholesale DictionaryPatch rewrite clobbered registrations | Restore from `backups/DictionaryPatch.txt.preDEPLOY.*`, relaunch |
| Wrong dialogue but correct flags/behavior | Text-block `.mes` shadow (a higher-priority folder defines the same block) | Unshadowed real MesDB id / pin `text_block` |
| A "(saved)" Script-panel edit still shows the old line | Edit recorded in `field.toml` but not rebuilt + redeployed | Rebuild + redeploy, then F6 -> Reload field |
| After-battle softlock (control never returns) | Missing entry-0 tag-10 Main_Reinit | Use the kit build path (it emits one for encounter fields) |
| "Nothing changed after deploy" | The change is startup-read, not F6-hot | Relaunch (list below) |

## Black screen: null-.eb (global EventDB id collision)

Fingerprint, verbatim from memory `project-ff9-eventdb-id-collision`:

> A custom field is in the F6 warp list (registered) and its background/walkmesh **renders**, yet
> warping to it black-screens with `EventEngine.StartEvents(ebFileData=null)` at
> `HonoluluFieldMain.ff9InitStateFieldMap` (+ a cascade of `NullReferenceException`).
> [...] **This fingerprint = a GLOBAL `FF9DBAll.EventDB` id collision across stacked mod folders.**

> The real tell in `Memoria.log`:
> `[AssetManager] Memoria asset not found: .../Field/US/EVT_BATTLE_<name>.eb` (looks like a stray battle error).

> Net: "registered + scene renders + .eb null, no relevant log" ⇒ suspect a cross-folder id collision FIRST.

Diagnose in one command (verbatim): `grep -rn "<id>" "<game>"/FF9CustomMap*/DictionaryPatch.txt` —
if the id appears as both a `FieldScene` and a `BattleScene`, or in two folders, that's it.
PowerShell form (from TROUBLESHOOTING.md): `Select-String "FieldScene <id>" "<game>\*\DictionaryPatch.txt"`.
Clean isolator: deploy the SAME content at a fresh id — if the fresh id loads and the original
doesn't, it's the id, not the content. Fix: pick an id no other stacked folder claims.

## Black screen: other DictionaryPatch variants

- **BG-borrow `area` below 10** — verbatim from TROUBLESHOOTING.md: "The background loader builds
  the scene name as `"FBG_N" + area` and reads exactly **two characters** of the area, so
  single-digit areas (0–9) black-screen." Fix: `area` >= 10 (owned by the `authoring-ff9-scenes` skill).
- **Id above 32767** — verbatim from TROUBLESHOOTING.md: "The engine's `fldMapNo` is an **Int16**
  (max **32767**). A higher id registers but is unreachable, and an out-of-range id can break the
  whole `DictionaryPatch.txt` parse."
- **World-map band collision** — verbatim from memory `project-ff9-eventdb-id-collision`: "ids
  **9000-9012** are the engine's RESERVED world-map location ids (`EVT_WORLD_WORLD00..12`, the
  `WorldMap()`/`wldMapNo` values, in the SAME global `EventDB`)". Distinguishing tell: the missing
  asset is under a **World/** path but carries a field-fork name. Fix: re-fork the campaign off the
  band; `journey.lint_manifest` now hard-errors registered ids in 9000-9012.
- **DictionaryPatch clobber** — tell, verbatim: "New-Game-only black screen + the DictionaryPatch
  shorter than its backups ⇒ a clobber, not a content bug." Recovery: diff the timestamped
  `backups/DictionaryPatch.txt.preDEPLOY.*`, restore the union of real registrations (assets survive;
  only the registration list is lost), then RELAUNCH (DictionaryPatch is startup-read).

## Wrong text, right flags (text-block / .mes shadow)

The engine serves a field's `field/<text_block>.mes` from the highest-priority `Memoria.ini
FolderNames` folder that defines it, so a lower folder's dialogue is shadowed — behavior/flags stay
correct. Verbatim from memory `project-ff9-text-block-shadow`: "The flags-readout is immune (it
reads `gEventGlobal` directly); the message box is not." — so F6 -> Flags is the reliable proof.

Verbatim constraint: "**`text_block` MUST be a real `MesDB` id** — Memoria's `DataPatchers` checks
`FF9DBAll.MesDB.ContainsKey(mesID)` and logs "invalid message file ID" otherwise, so an arbitrary
unique block (e.g. 4173) won't load (blank box)." A custom mesID CAN be registered without an
engine rebuild — verbatim from memory `reference-ff9-mesid-registration`: "`DataPatchers.PatchDictionaries`
handles a `MessageFile <id> <name>` directive (e.g. `MessageFile 20000 MES_X`) → `MesDB[20000] =
"MES_X"`, which makes the FieldScene gate pass."

The deploy guards it — `deploy_field.py` prints (verbatim): `!! TEXT SHADOWED: block N is also
defined by '<folder>', HIGHER priority than '<yours>' ... use text_block = <free real id>`.
Fix: a real mesID no higher-priority folder defines, or pin `text_block = N`
(`.ff9deploy.toml` / `--text-block N` / `[field] text_block`).

Two related same-symptom cases:

- **Within-folder shared-block clobber** (campaign members sharing one real block): fixed BUILD-side
  (kit 1.0.0b1, `_reconcile_mes` merge) — but an already-deployed campaign keeps the clobbered `.mes`
  until re-built + re-deployed; F6 Reload re-reads disk, it does NOT rebuild. Read memory
  `[[project-ff9-text-block-shadow]]`.
- **Script-panel edit shows "(saved)" but the game speaks the old line**: the GUI save records a
  `[[logic_edit]]` in `field.toml`; only the build rewrites the `.mes`. F6 Reload without a redeploy
  just re-reads the stale file. Rebuild + redeploy, then reload (TROUBLESHOOTING.md "Wrong dialogue").

## After-battle softlock

Verbatim from TROUBLESHOOTING.md: "The field is missing an entry-0 **tag-10 "Main_Reinit"** routine.
After a battle the engine suspends field objects and relies on that routine to fade back in and
re-enable movement; a field cloned from a cutscene field often lacks one." The kit emits a
Main_Reinit automatically for any field with encounters — this only bites hand-authored bytecode or
splices outside the normal build. Deep recipe: read memory `[[project-ff9-encounters]]`.

## "Nothing changed after deploy" / when to relaunch

F6 -> Reload field re-reads the current field's `.eb`/`.mes`/scene/walkmesh/art from disk (needs the
bundled custom engine — stock Memoria has no F6). This is literal: there is NO content cache under it.
`AssetManager.LoadFromDisc` bottoms out in `File.ReadAllText`/`ReadAllBytes` per field entry, and the
one apparent text cache — `FieldImporter.cs`'s `(mesID, language)` early-out — is DEAD CODE, because
`TextBatch` is a **struct** and `LoadingZoneBatch` is a value-returning property, so the
`UpdateFieldZone` write at `FieldImporter.cs:394` mutates a throwaway copy and `MainBatch.fieldZoneId`
stays `-1` forever. (Recorded because reading those lines *without* checking the struct/property
declarations predicts the opposite, and did: 2026-07-18, falsified in-game.)

**The axis is REGISTRATION vs CONTENT, not file type.** A `DictionaryPatch.txt` line — a new id, a
changed `MessageFile` mesID, a renamed FBG — needs a relaunch (`DataPatchers.Initialize()` runs once at
process start behind `_isInitialized`). Editing content inside an already-registered block does not.
ONE real `.mes` staleness exception: a shared file pulled in via `[LOADMES=NAME]` is memoized in
`FF9TextTool.sharedTexts` for the process, so editing the INCLUDED file needs a relaunch.

Relaunch only when F6 Reload can't pick a change up — verbatim list from TROUBLESHOOTING.md:

> - the **first deploy of a new id** (it has to register its `DictionaryPatch.txt` line),
> - a **`BattlePatch.txt`** change (battle tuning / per-encounter BGM),
> - **start-state CSVs** or **`TextPatch.txt`** item names (read at startup / New Game),
> - an **engine DLL rebuild**.

Also check the deploy actually targeted the folder/id you're standing in (`.ff9deploy.toml` vs
`--mod-folder`/`--id`, see the id-bands-and-folders reference file in this skill).
