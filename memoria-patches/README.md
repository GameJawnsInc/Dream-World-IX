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
| `s30-doeventcode-fork-walk.patch` | `EventEngine.DoEventCode.cs` — the file the s24 gate census MISSED. Its per-field event gates use a local alias `Int16 mapNo = fldMapNo` (not the literal `fldMapNo`), so a `grep fldMapNo` census skipped all ~150 `mapNo == N` gates. Adds `Int32 effMapNo = EffectiveFieldId(mapNo)` and routes every gate comparison through it (the 2 non-gate uses — the VoicePlayer arg + `sOriginalFieldNo = mapNo` — stay raw). Restores the per-field scripted-walk destination corrections (the `MOVE`/Walk fixups), e.g. field 53's "Blank jumps in hole" reposition (`destX 250→330`) that puts the falling characters over the hole. ★ IN-GAME PROVEN — fixed the character *positioning* for the 6003 fall (the *occlusion* needed s31). |
| `s31-fork-name-keyed-overlay-offset.patch` | The fork-gate census also missed a whole **NAME-string-keyed** class: `FieldMapExtraOffset` (`mapExtraOffsetList.txt`) tunes per-field overlay z-offsets keyed on the FBG **name**, not `fldMapNo` — so `EffectiveFieldId` (id-based) never reached it. A fork's deployed name (`FBG_N11_PRIM_TSHP_TH_MET`) misses the donor's entry (`FBG_N00_TSHP_MAP006C_TH_MET_4,-1,29,0,-100`), so the floor overlay keeps its raw depth during the fall-move and stops occluding the falling characters. Adds `DataPatchers.EffectiveFieldName(name)` — the name-space analogue of `EffectiveFieldId` (resolves a fork's FBG name → its donor's via the global id↔FBG-name table) — and routes `SetOffset` / `UpdateOverlayOffset` through it on a dict miss. Fixes the WHOLE name-keyed-offset class for every fork, not just 6003. ★ **IN-GAME PROVEN 2026-06-23** — the 6003 jump-into-hole now occludes the falling characters, matching real field 53. |
| `s32-fork-name-gates.patch` | The **rest** of the name-keyed gate class, from a follow-up engine census (the sibling sweep s31 flagged): 7 more sites where engine behavior is keyed on the FBG name a fork doesn't share, wrapped with the same `EffectiveFieldName` lever (generalized in this patch to resolve by the *passed name* so it is correct even at cross-field call sites like the SPS `ChangeFieldOrigin`). **Tier-A (gameplay-breaking on a fork):** the Iifa telescope/harp minigame player- + menu-control unlock (`UIManager.cs`, 2 sites — without it the fork freezes the player), the Conde-Petie space-scene menu unlock (`UIManager.cs`), the Iifa rain-particle world offset (`FieldRainRenderer.cs` — else rain spawns at origin), the Oeilvert star-display opaque-shader override (`BGSCENE_DEF.cs`). **Tier-B:** the per-field SPS sprite z-offsets (`FieldMapSPSExtraOffset.cs`, name-keyed dict like s31) and the Treasure-Hall +8px overlay nudge (`FieldMap.cs`). All identity-safe for real (non-forked) fields. **Deferred:** the area-title localized-atlas gates (`FieldMap.SetFieldMapAtlasName` / `FieldMapLocalizeAreaTitle`) — wrapping them would make a fork load a localized atlas variant (`atlas_us`/`atlas_uk`) it may not ship, so they need asset-aware handling; lowest impact (English degrades gracefully). ⚠ IN-GAME UNVERIFIED (built + deployed 2026-06-23; the affected fields are late-game — verify as those zones get forked). |

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
