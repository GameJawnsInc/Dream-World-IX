# Upstream PR for Memoria — FieldCreatorScene export path fix

One small, isolated, debug-free **bug fix** to the [Memoria](https://github.com/Albeoris/Memoria)
engine that makes the in-engine FieldCreatorScene editor able to save a usable custom field. It is
**not required** for a field built by `ff9mapkit` to work (the kit writes the field files directly,
so its output runs on stock Memoria) — but it fixes a shipped feature that is currently broken.

Touches only `Assembly-CSharp/Global/BGSCENE_DEF.cs`.

> **Deliberately not upstreamed** (they are our debug harness, not engine improvements): the
> New-Game→field-100 warp in `EventEngine.Initialize.cs` and the booster auto-enable in
> `SettingsState.cs`. See `../s12-engine-edits.patch`.
>
> **Considered and dropped** (kept locally at `../deferred-overlay-texture-cache.patch`): an
> overlay-`Texture2D` cache for pure-`.bgx` scenes. We originally believed it fixed a slow,
> see-through custom-field fade — but the fade was actually fixed elsewhere (the field's `.eb`
> tag-10 `FadeFilter`, plus flattening the painted art), and this cache turned out to be only an
> unmeasured load-time micro-optimization (it avoids re-decoding overlay PNGs on field re-entry).
> Without a measured, user-visible benefit we don't think it's worth a maintainer's time; revisit
> only if real load/perf issues show up.

---

## Fix FieldCreatorScene export writing overlay PNGs to the game root instead of the field folder

**File:** `Assembly-CSharp/Global/BGSCENE_DEF.cs` · **Patch:** `fieldcreator-png-export-path.patch`
· **Size:** one line (the diff is +4/−1 incl. a comment)

**Problem.** `ExportMemoriaBGX` computes the output `folder`, but passes the bare `fileName`
(no directory) to `ExportMemoriaBGXOverlay`:

```csharp
String folder   = Path.GetDirectoryName(bgxExportPath);          // the field folder
String fileName = Path.GetFileNameWithoutExtension(bgxExportPath); // BARE — no directory
...
bgsStr += ExportMemoriaBGXOverlay(bgOverlay, fileName);
```

`ExportMemoriaBGXOverlay` then uses that base two ways — the `.bgx` `Image:` reference (bare, via
`Path.GetFileName`) and the file it actually writes (`"{base}_{n}.png"`, a **relative** path):

```csharp
String textureName = $"{Path.GetFileName(textureBasePath)}_{bgOverlay.indnum}.png"; // .bgx ref
String texturePath = $"{textureBasePath}_{bgOverlay.indnum}.png";                   // file written
...
bgsStr += $"Image: {textureName}\n";                       // bare → loaded from the field folder
TextureHelper.WriteTextureToFile(texture, texturePath);    // relative → process CWD (game root)
```

So the emitted `.bgx` references `name_N.png` (loaded from the field's own folder) but the PNG is
written to the **game root**. The overlays are missing from the field folder → **the field
black-screens when loaded.** This is almost certainly why the FieldCreatorScene editor has been
unusable for saving custom fields (observed first-hand: the export dumps every overlay PNG into the
game root and none into the field folder).

**Fix (one line).** Pass `folder + fileName` as the texture base path. Because `textureName` is
derived with `Path.GetFileName(...)`, the `.bgx` reference stays bare/relative while the file is
written into the field folder:

```csharp
// before
bgsStr += ExportMemoriaBGXOverlay(bgOverlay, fileName);
// after
bgsStr += ExportMemoriaBGXOverlay(bgOverlay, folder + fileName);
```

**Risk.** Minimal and localized to the editor export path. `folder` already ends in `/`, and this
is the only call site of `ExportMemoriaBGXOverlay`, so nothing else is affected.

**Verified.** Description checked against source (`BGSCENE_DEF.cs` lines 518/524/533/561–564/610–612);
patch forward-applies cleanly to pristine `main`@`6b8bb2d5`.

### Paste-ready PR title
> Fix FieldCreatorScene export writing overlay PNGs to the game root instead of the field folder

### Paste-ready PR description
> `BGSCENE_DEF.ExportMemoriaBGX` computes the output `folder`, but passes the bare `fileName`
> (no directory) to `ExportMemoriaBGXOverlay`. That helper writes each overlay via
> `WriteTextureToFile(texture, "{base}_{n}.png")` — a relative path — so the PNGs land in the
> process working directory (the game root), while the emitted `.bgx` `Image:` line (correctly a
> bare filename via `Path.GetFileName`) is loaded from the field's own folder. Net result: the
> in-editor export produces a `.bgx` whose overlay PNGs are missing from the field folder, so the
> field black-screens when loaded — FieldCreatorScene can't save a usable custom field.
>
> Fix: pass `folder + fileName` as the texture base path. `ExportMemoriaBGXOverlay` already derives
> the `Image:` reference with `Path.GetFileName(...)`, so the reference stays bare/relative while the
> file is written into the field folder. One-line change, scoped to the editor export path.

---

## How to submit
1. Fork `Albeoris/Memoria`, branch off `main`.
2. Apply the patch: `git apply path/to/fieldcreator-png-export-path.patch` (or make the one-line edit
   by hand). Build to confirm it compiles.
   - The patch uses **CRLF** line endings to match the Memoria repo, so `git apply` works directly on
     a Windows clone. On an LF checkout / CI, add `--ignore-whitespace`.
3. Open the PR with the title + description above.
