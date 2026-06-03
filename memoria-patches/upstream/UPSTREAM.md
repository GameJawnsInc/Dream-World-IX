# Upstream PRs for Memoria (custom-field scene fixes)

Two small, isolated, debug-free improvements to the [Memoria](https://github.com/Albeoris/Memoria)
engine that smooth out the custom-field / pure-`.bgx` scene path. **Neither is required** for a
field built by `ff9mapkit` to work (the kit's output runs on stock Memoria) — these are
quality-of-life fixes that benefit everyone, so we want them merged upstream rather than carried
as a private DLL.

Both touch only `Assembly-CSharp/Global/BGSCENE_DEF.cs`. They are independent and can be one PR
each or a single "custom-field scene fixes" PR.

> Explicitly **not** upstreamed (they are our debug harness, not engine improvements): the
> New-Game→field-100 warp in `EventEngine.Initialize.cs` and the booster auto-enable in
> `SettingsState.cs`. See `../s12-engine-edits.patch` for those.

---

## PR 1 — Cache decoded overlay textures for pure-Memoria scenes

**File:** `Assembly-CSharp/Global/BGSCENE_DEF.cs` · **Patch:** `pr1-overlay-texture-cache.patch`

**Problem.** For a pure-`.bgx` scene, `ProcessMemoriaOverlay` calls
`AssetManager.LoadFromDisc<Texture2D>(...)` for every `Image:` overlay on **every** field load —
a fresh `BGSCENE_DEF` is built each time, so the overlay PNGs are re-decoded from disc on every
(re)entry and on battle-return. On custom fields this shows as a slow, partly see-through fade-in.

**Fix.** A process-lifetime `static Dictionary<String, Texture2D>` keyed by the resolved image
path. Reuse the decoded texture if present and still alive; otherwise load and cache it. The
static reference also keeps overlay textures alive across the battle scene change
(`Resources.UnloadUnusedAssets` won't free referenced assets). Self-healing: a destroyed texture
compares Unity-null and is reloaded.

**Risk.** Minimal. Worst case is a few small textures held for the process lifetime; the null
check makes a stale entry reload rather than fault.

---

## PR 2 — FieldCreatorScene: write exported overlay PNGs next to the `.bgx`

**File:** `Assembly-CSharp/Global/BGSCENE_DEF.cs` · **Patch:** `pr2-fieldcreator-png-export-path.patch`

**Problem.** `ExportMemoriaBGX(bgxExportPath)` computes the output `folder`, but passes the bare
`fileName` (no directory) to `ExportMemoriaBGXOverlay`. That helper then writes each overlay via
`TextureHelper.WriteTextureToFile(texture, texturePath)` where `texturePath = "{fileName}_{n}.png"`
— a **relative** path, so the PNGs land in the process working directory (the game root), while
the emitted `.bgx` `Image:` line (correctly a bare filename) is loaded from the field's own
folder. Result: the in-editor export produces a `.bgx` whose overlays are missing from the field
folder → the field black-screens when loaded. This is almost certainly why the in-engine
FieldCreatorScene editor has been unusable for saving custom fields.

**Fix (one line).** Pass `folder + fileName` as the texture base path. `ExportMemoriaBGXOverlay`
already derives the `.bgx` `Image:` reference with `Path.GetFileName(...)`, so the reference stays
bare/relative while the file is written into the field folder:

```csharp
// before
bgsStr += ExportMemoriaBGXOverlay(bgOverlay, fileName);
// after
bgsStr += ExportMemoriaBGXOverlay(bgOverlay, folder + fileName);
```

**Risk.** Minimal and localized to the editor export path. `folder` already ends in `/`.

---

## How to submit

1. Fork `Albeoris/Memoria`, branch off `main`.
2. Apply the relevant patch(es): `git apply path/to/prN-*.patch` (or make the edits by hand — both
   are tiny). Build to confirm it compiles.
   - The patch files use **CRLF** line endings to match the Memoria repo, so `git apply` works
     directly on a Windows clone. On an LF checkout / CI, add `--ignore-whitespace`.
   - Verified (2026-06-03) against pristine `main`@`6b8bb2d5`: PR1's base blob matches HEAD exactly
     and reverse-applies as the exact diff; PR2 forward-applies cleanly and independently. Both are
     against `Assembly-CSharp/Global/BGSCENE_DEF.cs` only.
3. Open the PR(s) with the rationale above. Reference that they support custom-field authoring
   (pure-`.bgx` scenes) and the FieldCreatorScene editor.
