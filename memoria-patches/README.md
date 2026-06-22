# `memoria-patches/` — engine patches for Dream World IX

Dream World IX runs **novel** fields on stock [Memoria](https://github.com/Albeoris/Memoria) and needs a
small **custom engine** only for **forked** fields. The full rationale is in
[`../ff9mapkit/docs/ENGINE.md`](../ff9mapkit/docs/ENGINE.md). These files are unified diffs against a Memoria
source clone — apply the *live* set and compile `Assembly-CSharp`, or just grab the pre-built
`dwix-custom-memoria-<version>.zip` from the GitHub **Releases** page.

This README is the per-file status map (which patches are live, which ship in the bundle, which are dead
history) so a reader isn't left guessing what each file is for.

## Live fork-fidelity set — SHIPPED in the engine bundle

These wrap the hardcoded `fldMapNo == N` engine gates with an *effective field id* so a custom fork inherits
the original field's tuned behavior. This is the set that makes a forked field play faithfully.

| File | What it restores |
|---|---|
| `s23-narrow-map-fork-width.patch` | A forked narrow field gets the donor's exact tuned screen width (no letterbox loss). `s23-narrow-map-fork-width.PR.md` is its upstream write-up. |
| `s24-fork-donor-remap.patch` | The fork→donor remap suite (`EffectiveFieldId` / `ForkSiblingField` / `IsForkField`) — off-mesh exemptions, the fake-battle return field, overworld→fork entry, the no-encounter wrap, and the rest. Folds in the intermediate s25–s28 milestone steps; there is **no separate s25–s28 file**. |
| `s29-fork-donor-softlocks.patch` | The same `EffectiveFieldId` wrap on the remaining late-game (disc 2–4) softlock gates (Iifa / Burmecia / Gulug / Oeilvert / Esto Gaza / Ipsen / Epilogue). Disc-1 gates are in-game proven; these late-disc gates are still being playtested as those zones are forked. |

## Rendering quality — SHIPPED in the bundle

| File | What it fixes |
|---|---|
| `s30-bgx-point-filter.patch` | Point-samples `.bgx` field-background overlay textures (`FilterMode.Point` + `Clamp` at `BGSCENE_DEF.ProcessMemoriaOverlay`), mirroring what the native atlas already does in `InitPSXTextureAtlas`. Without it, an `import --editable` (repaintable per-depth `.bgx`) field loads its layers **Bilinear**, so a cut depth-layer tile bleeds into transparency at its edge = a 1px **seam** at every tile/depth boundary — very visible on wide scrolling fields (e.g. Alexandria field 100, 36 layers). Point sampling is the same mechanism stock/Moguri/`--native` use; this is the *faithful* seam fix (the `.memnfo` FilterMode hook that could do it from a kit file is dummied in stock Memoria). Scoped to field-bg overlays only — UI/model textures keep Bilinear. ⚠ **IN-GAME UNVERIFIED** as of this commit (awaiting a wide-field A/B playtest). Also a clean **upstream candidate** (benefits any Memoria custom-`.bgx` field). Follow-up once proven: the kit's `_edge_bleed` workaround (`extract.py`) becomes redundant and can be dropped. |

## Dev tooling — shipped in the bundle, but NOT a fidelity patch

| File | What it is |
|---|---|
| `s22-debug-menu-f6.patch` | The F6 in-game debug menu (Warp / Move / Cheats / Flags / Time). A tester convenience; the beta bundle includes it, but it is not part of the fork-fidelity set or the upstream-candidate set. |

## Superseded / historical — kept for the build record, do NOT apply

Earlier dev-iteration patches, retained so the engine history stays legible. They are superseded by the
live set above (the F6 menu replaced the single-key reload/reset hotkeys).

| File | Superseded by |
|---|---|
| `s12-engine-edits.patch` | early scratch; obsolete |
| `s18-field-reload-hotkey.patch` | `s22` (F6 → Reload field) |
| `s21-dev-hotkeys-f6-f10.patch` | `s22` (the tabbed F6 menu) |

## Upstream candidates & optional polish — NOT in the bundle

| File | What it is |
|---|---|
| `upstream/fieldcreator-png-export-path.patch` (+ `upstream/UPSTREAM.md`) | A standalone Memoria bug fix (FieldCreatorScene PNG export path). Not required by the kit's CLI pipeline; offered upstream. |
| `deferred-overlay-texture-cache.patch` | An optional overlay-PNG decode cache (smoother field loads / battle returns). Nice-to-have, not required. |

---

> **License / provenance.** These patches modify MIT-licensed Memoria (© Albeoris) and contain **zero**
> Final Fantasy IX game data. The compiled bundle is likewise MIT (© Albeoris) plus the Dream World IX
> patches. See [`../ff9mapkit/docs/PROVENANCE.md`](../ff9mapkit/docs/PROVENANCE.md).
