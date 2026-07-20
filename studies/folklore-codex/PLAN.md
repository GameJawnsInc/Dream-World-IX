# The Folklore Codex — design verdict + build plan

> **Status: DESIGN SECURED, NOTHING BUILT.** An in-game, player-facing codex/bestiary — creatures /
> locations / lore entries that unlock as the player encounters things, persisted in the save, styled
> to read as stock FF9. Verified 2026-07-20 by a 27-agent adversarial workflow (5 recon / 16 verify /
> 4 gap probes / synthesis): 10 claims CONFIRMED, 6 PARTIAL, 0 REFUTED. All citations below are
> file:line references into the read-only Memoria source clone (`C:\gd\FFIX\Memoria\Assembly-CSharp\`)
> that were actually read by a verifier — no SE bytes, references only.
>
> Naming: this is the **in-game** codex. The unrelated website wiki at jawnston.com/ff9 is "the Mist
> Codex" — keep the names distinct.

---

## 1. The two-layer verdict

**Layer 1 — the data/text/list/persistence spine is DLL-FREE and rides the vanilla Key Items page.**
**Layer 2 — the visual "display window" (monster model / location art) is one focused engine patch
(next free slot: s45), assembled from three separately-shipped precedents.**

A dedicated first-class "Folklore" main-menu submenu (its own tab beside Item/Ability/Equip…) is a
**third, harder tier** — under active exploration (§6). Everything in Layers 1–2 remains valid and
prerequisite regardless of which entry surface wins.

## 2. Layer 1 — the DLL-free spine (Key Items page)

- **Entries are minted key items in important-id band 80–254 (175 slots).** Real FF9 key items
  occupy ids 0–79 (80 entries in the install's `KeyItems.strings`). **255 is reserved** — it is
  `FF9FITEM_RARE_NONE`, the blank-row sentinel (`ItemUI.cs:731/756`).
- **The list renders novel ids for free.** `DisplayKeyItem` enumerates the `rare_item_obtained`
  `HashSet<Int32>` with no ceiling and no 0–79 filter (`ItemUI.cs:727-734`); name/help/long-lore come
  from uncapped `Dictionary<Int32,String>` stores (`ItemUI.cs:766/778/824/826`,
  `FF9TextTool.cs:880-882`). A free **unread badge**: the stock "New!" icon clears when the skin
  popup closes (`FF9Item_UseImportant`, `ItemUI.cs:848`).
- **Granting rides the existing `AddItem` opcode 0x48 pool-encode** — item-id `256+N` routes to
  important id N (`ff9item.2.cs:185-195` `FF9Item_Add_Generic`), so item ids 336–510 → important ids
  80–254. The kit's `content/event.py give_item` / `opcodes.add_item` already reach this path.
  `HashSet.Add` is idempotent → discovery triggers need zero flag bookkeeping (NOT `gEventGlobal`).
- **Persistence: 80–254 is the robust band.** `oldSaveFormat` is a per-CONTAINER flag, not save age —
  every save writes BOTH the legacy 2-bit bitfield (ids 0–255 only, `FF9StateGlobal.cs:870-900`) AND
  the unbounded `rareItemsEx` sidecar (`JsonParser.cs:992-1008`; read-back `:1378-1391` explicitly
  preserves unknown/mod ids). 80–254 = double-covered; **ids ≥256 are sidecar-only and silently lost
  on Steam-Cloud time-desync or sidecar loss** — exceed 255 only deliberately, and note the kit's
  `keyitems.py KEYITEM_MAX=255` + save-editor dual-write would need a routing split first (≥256 must
  skip the 64-byte bitfield leg; not a one-line cap bump).
- **⚠ TEXT CHANNEL — the one mechanism the first-pass verdict got WRONG.** `TextPatch.txt >DATABASE
  Database=='KeyItem'` is REWRITE-ONLY: `PatchDatabaseString` runs inside each `Set*`
  (`FF9TextTool.cs:813/818/823`) and can never CREATE an id. The working no-DLL add-new channel =
  **three cumulative `.mes` files** per mod folder:
  `EmbeddedAsset/Text/<lang>/KeyItem/{imp_name,imp_help,imp_skin}.mes` with `[TXID=N]` entries at
  N≥80 (`[TXID=]` parse `FF9TextTool.cs:848-856`; cumulative importer uncapped, `KeyItemImporter.cs`).
  The kit needs a NEW emitter (reuse `content/text.py`'s `.mes` machinery); the existing
  `[[item_text]]` mechanism cannot mint Folklore text.
- **Consumers swept — safe.** Exactly five engine consumers of `rare_item_obtained/used`; no
  achievement, Steam stat, or completion counter iterates the set (`AchievementManager` never touches
  key items). Netsync party-mirror carries ids 80–999 losslessly (UInt16 wire); asymmetric co-op codex
  progress is safe (the guest's own set renders). The s35 texture cache does not interfere with the
  2D route (private to `BGSCENE_DEF`).
- **List order** (`JsonParser.cs:1369-1391`): on load both sets `Clear()`, the bitfield (when present
  in the loaded JSON) parses ascending → ascending id order for ≤255, then `rareItemsEx` applies in
  array order (dup adds no-op). Post-reload order is deterministic; mid-session grants append.
  Curated order, if ever wanted, is a one-line sort in the Layer-2 patch.

## 3. Layer 2 — the display window (engine patch s45)

The Key Items page itself has ZERO image precedent — its detail + skin panels are text labels only
(`ItemUI.cs:765-778`, `:819-851`). The window is net-new UI built from three shipped precedents:

1. **The stock frame — `ControlPanel` / `MenuUIControlPanel`** (`Memoria\Scenes\ControlPanel\`): a
   SHIPPED panel built entirely in code, no new Unity assets — it `Instantiate()`s stock prefab
   pieces (clones `UIManager.MainMenuScene.GenericInfoPanel` for the framed body; rows via anchor
   math, `ControlPanel.cs:197-222/277-361/410`) and lives in the real menu (`UIKeyTrigger.cs:480`).
   The `GO*` family (`GOMenuBackground`/`GOFrameBackground`) is the complementary stock-skin idiom.
   **⚠ Anti-precedents:** `MemoriaConfigurationMenu.cs` and this project's own `Ff9mkDebugMenu.cs`
   are IMGUI/OnGUI — neither looks stock; the codex would be the project's FIRST stock-NGUI
   player-facing screen. (Side discrepancy to reconcile: `Ff9mkDebugMenu.cs:8-10` says "dev engine
   only, never shipped", CLAUDE.md §5 says the debug menu ships in the bundle.)
2. **The render bridge — Memoria's Libra "photo"**: a SHIPPED 3D-monster-in-a-stock-window. Battle
   camera → `targetTexture` RenderTexture → `Render()` → `ReadPixels` → `Texture2D`
   (`BattleHUD.Public.cs:213-246`) → runtime `UISpriteData` injected into a live atlas → normal
   `UISprite` inside the stock tutorial window (`TutorialUI.cs:317-337`). The static-snapshot path is
   therefore fully precedented. A LIVE/rotating RenderTexture bound to a `UITexture` is unbuilt
   anywhere in the tree (every shipped `UITexture` consumer assigns a static `Texture2D`) — feasible
   but first-of-its-kind; sequence it last.
3. **Model load — `ModelFactory.CreateModel` + `AnimationFactory`**: standalone, NOT battle-gated
   (proven by `ModelViewerScene`, which loads battle-only MON forms outside battle). **Do NOT lift
   `ModelViewerScene` wholesale** — it hijacks the fullscreen FieldMap camera + main loop; lift only
   its load logic and give the codex its own offscreen camera + culling layer.

**What the window shows:** (a) **monsters** — `GEO_MON_B3_*` battle forms via ModelFactory (3D
snapshot or live), or kit-prerendered portraits (`model-preview`) as the 2D route; (b) **locations
(Dali/Treno) — 2D is the FAITHFUL answer, not a fallback**: no standalone landmark mesh exists
(worldmap towns are baked into per-block, terrain-coupled object sub-meshes), and in the real game
these places ARE pre-rendered art — show the field's background via the kit's `export-art`, delivered
as loose PNG → `AssetManager.LoadFromDisc<Texture2D>` → `UITexture`.

**Patch plumbing:** mod-root sidecar `FolklorePatch.txt` (folklore-id → category + GEO name | image
path), read per-folder like `ForkDonorPatch.txt` via `TryFindAssetInModOnDisc`; a `[Folklore] Enabled`
Memoria.ini gate (netsync `IniFile` + mtime hot-reload idiom); the codex owns a small path-keyed
texture cache (`LoadFromDisc` caches nothing — per-repaint reload would leak).

## 4. Phased plan (each phase = one change, one in-game gate)

- **P0 — data spine (DLL-free).** Mint a small band in 80–254; new `.mes` emitter for the three
  KeyItem files; grant 2–3 entries via event script. **Gate:** rows render with name/help/lore, the
  "New!" badge clears on read, survives save → quit → load. Shippable as a text codex by itself.
- **P1 — 2D display window (minimal s45).** `FolklorePatch.txt` + ini gate + a `UITexture` in the
  skin popup fed by loose PNG. Locations first (pure `export-art`), then monster portraits.
  **Gate:** stock look, skin tween intact, no texture leak.
- **P2 — 3D still snapshot (optional).** ModelFactory offscreen rig + Libra-exact snapshot on entry
  select. **Gate:** B3 pose/lighting correct out of battle, no camera/UI-state conflict.
- **P3 — live/rotating (optional polish).** Per-frame RenderTexture on the `UITexture`.
  **Gate:** perf, UV-flip, layering, still reads stock.

## 5. Risks (playtest-only, ranked)

1. Live-3D-in-menu is unprecedented in-tree (P3 only).
2. Codex camera vs FF9's UI-state camera ownership.
3. `GEO_MON_B3_*` animation/shader fidelity outside a battle scene (only ~21 F0 field forms are
   field-proven; the rest are battle-only).
4. NGUI depth injection into the skin popup without breaking its TweenIn/TweenOut slide.
5. Model instantiate cost/memory in-menu.
6. Offline-render quality (`model-preview` is thumbnail-grade — flat lambert, NEAREST texels).

## 6. OPEN — the dedicated "Folklore" submenu (the hard tier, being explored)

The owner's chosen direction 2026-07-20: build the hard parts — a first-class Folklore entry in the
main menu rather than (or in addition to) squatting inside Item → Key Items. This means some subset
of: a new `MainMenuUI.SubMenu` value (`MainMenuUI.cs:813-824`), a new `UIManager.UIState` + scene
registration, a new stock-NGUI two-pane screen (list + detail + display window) built ControlPanel-
style from cloned stock pieces, main-menu row insertion + navigation/cursor plumbing, localization of
the label, and filtering the folklore band OUT of the Key Items tab so entries don't double-appear.
A dedicated multi-agent exploration of exactly this is in flight; its findings land as
`SUBMENU.md` beside this file. Layers 1–2 above are unchanged by its outcome — the submenu replaces
only the *entry surface*, not the data spine or the display machinery.
