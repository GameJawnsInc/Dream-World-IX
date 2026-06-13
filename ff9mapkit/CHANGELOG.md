# Changelog

All notable changes to `ff9mapkit`. Format follows [Keep a Changelog](https://keepachangelog.com);
versioning is [SemVer](https://semver.org). The Blender add-on has its own version, kept in lockstep.

## [Unreleased]

### Added — `[[item_text]]`: an item's menu NAME + description text, no DLL (0.9.89)
- Rename an item or rewrite its description — the text companion to the stat tuners (`[[item_effect]]` changes how
  much a Potion *heals*; `[[item_text]]` changes the menu text that *says* so): `[[item_text]] name = "Potion"` +
  `display_name = "Mega Potion"` and/or `description = "Restores 15 HP."` (at least one). Mod-global + repeatable.
- **Channel = a drop-in `TextPatch.txt`** at the mod-folder root — the *same* per-folder patch-file mechanism the
  kit already emits for `DictionaryPatch.txt` / `BattlePatch.txt` (read once per folder at
  `DataPatchers.Initialize` → `TextPatcher.PatchTexts`). Each item becomes a `>DATABASE` find/replace gated by NCalc
  on `Database == 'RegularItem' && EntryId == <id> && IsNameEntry/IsHelpEntry`. The kit writes **only your strings +
  the resolved id** — it reads nothing from the bundles (fully provenance-clean, unlike the CSV deltas).
- **Grounded in the Memoria source** (`TextPatcher.cs` + `FF9TextTool.cs:776-789`, both fully read): `SetItemName`
  flags `IsNameEntry`; `SetItemHelpDesc` **and** `SetItemBattleDesc` BOTH flag `IsHelpEntry` → the menu-help and
  in-battle descriptions are **inseparable** through this channel, so `description` sets both. Full-replace uses the
  Multiline-immune `Find: \A[\s\S]*\z`; the emitter escapes `$`→`$$` (Regex.Replace group-ref) and carries real
  newlines as `\n` (the engine reads the patch line-by-line, then converts `\n`→newline).
- New `content/itemtext.py` (`render_block_lines` / `validate_blocks` / `merge_text_patch`) + `ModLayout.text_patch`
  + `build._emit_item_text` (mod-global aggregate + dedup-warn) writing `TextPatch.txt` in `build_mod` +
  `validate()` lint + `deploy_field.py` non-clobbering splice-under-`//`-markers (mirrors the `BattlePatch.txt`
  merge) with revert + RELAUNCH note. `deploy_campaign` ships it for free (whole-dist copytree). 31 tests
  (1530 total). FORMAT.md `[[item_text]]` section.
- **Multi-lens adversarial review** (3 lenses × verify) folded 4 real findings: reject a *literal* backslash-`n`
  (the engine rewrites `\n`→newline, so it can't be shown literally — fail offline, not in-game); reject `NoItem`
  (255), mirroring the sibling `[[shop]]`/`[[synthesis]]` guards; key the cross-field dedup-warn on the **resolved
  id** so name/id aliases of one item still warn; and reword the same-field-twice warning ("twice on X" vs the
  misleading "in two fields (X and X)"). One finding refuted (first-error-only lint — intentionally mirrors
  `battlepatch.validate_blocks`).
- **Channel verified in source; awaits the in-game proof** (a renamed Potion shows the new name) — the last open
  question is the patcher init-order, which `DataPatchers.Initialize` (in `AssetManager.DelayedInitialization`,
  before text import) makes near-certain.

### Added — `[[item_effect]]`: tune a consumable's use-effect (ItemEffects.csv), no DLL (0.9.88, ★ IN-GAME PROVEN)
- Tune what a **usable item** does: `[[item_effect]] name = "Potion"` + any of `power` (heal/damage, 0-9999) /
  `rate` (status chance, 0-100) / `element` / `status` (a `BattleStatus` mask by name, e.g. `["Poison"]`) /
  `for_dead` (usable on a KO'd target). Emits an `ItemEffects.csv` (`ItemEffect`) delta — the item is located by its
  `EffectId` and the row is edited **in place** (`EffectId` is **1:1** with a usable item — verified 32/32, no
  shared `Empty` row, unlike `BonusId`). The effect's **behaviour** (`ScriptId`/VFX/target) is preserved, so
  `status` only sets *which* statuses the effect concerns — inflict-vs-cure follows that existing `ScriptId`.
- **Grounded in the Memoria source:** `ItemEffects.csv` = `Id;Targets;DefaultAlly;Display;AnimationId;Dead;
  DefaultDead;ScriptId;Power;Rate;Element;Status` with `#! IncludeId`; whole-row merge by Id (`ff9item.LoadItemEffects`
  via `EnumerateCsvFromLowToHigh`) → a partial delta carries the base header verbatim + only the patched rows.
  `encode_statuses` maps status names → the `BattleStatus` UInt64 mask (the kit's existing `itemstats.STATUSES`).
- New `[[item_effect]]` block in `content/itemdata` (+ `build_item_effects_delta`, `encode_statuses`) + the
  `_emit_item_data` bucket + `write_item_data` param + `ModLayout.item_effects_csv` + `config` + `deploy_field`
  reversible CSV loop + `_STARTUP_CSVS` (RELAUNCH) + `validate()`. Base read LIVE in cp1252, **no game data
  committed**. Multi-lens adversarially reviewed (0 blockers): folded a `UInt64` upper-bound guard on a raw
  `status` bitmask (an over-range mask would `OverflowException` + hard-quit at load) + relaxed the lint to match
  the engine (a gem/Tent with a use-effect is tunable, not just "Usable"-typed consumables). 14 tests (1547
  total).
- **★ IN-GAME PROVEN (2026-06-13):** Potion `power` retuned 10→1 → it healed **15 in combat** (`Power × 15`,
  `BattleCalculator.CalcHpMagicRecovery`) and **10 out of combat** (the field's `× 10`), down from vanilla 150/100 —
  a single `Power` edit scaling **every** use-context because both the battle script and the field item-use read
  the same `ItemEffect.Power`. (The menu *description* still reads "150 HP" — that's the separate item-text channel.)

### Added — `[[item]] teaches`: the abilities a piece of gear teaches (Items.csv AbilityIds), no DLL (0.9.87, ★ IN-GAME PROVEN)
- FF9's "learn abilities from equipment" core: `[[item]] teaches = ["Soul Blade", "Auto-Reflect"]` (ability **names**,
  or explicit **`AA:`** active / **`SA:`** support tokens) **REWRITES** the item's `Items.csv` `AbilityIds` cell — the
  character can use those abilities while the gear is equipped and masters them by earning AP. Rides the existing
  whole-row `[[item]]` delta (composes with `price`/`sell`/`equippable_by`/BonusId-repoint on one row); `teaches = []`
  clears it.
- **Grounded in the Memoria source:** the `AbilityIds` cell is a **comma-list of `AA:X`/`SA:X` tokens inside one
  semicolon-cell** (no delimiter clash), parsed by `CsvParser.AnyAbilityArray`/`AnyAbility` (`AA:` pooled `/192`,
  `SA:` `/64 + 192`). Names resolve via the kit's existing provenance-clean `abilities` module (live-read of the
  per-character pool CSVs — `AA` = Actions, `SA` = support), canonicalised to tokens via `decode_token(resolve(...))`.
  The AP-to-master *cost* stays on the character pools (the battle/character lane), not the item.
- `content/itemdata.ability_tokens` + the `[[item]]` delta wiring + `abilities.is_token` + `build.validate` (tokens
  checked offline; a NAME only when the pools are reachable — no false positive offline). Base read LIVE in cp1252,
  **no game data committed**. Multi-lens adversarially reviewed (0 blockers): folded a real offline-lint gap (a
  token-SHAPED-but-malformed entry like `AA:nope` was misclassified as a name, so a no-install lint silently
  skipped it — `is_token`/`resolve` now treat any `AA:`/`SA:` prefix as a token and reject a bad index offline) +
  a non-equipment `teaches` no-op guard + the per-character-pool + ambiguous-name caveats in FORMAT.md. 13 tests
  (1536 total). **★ Engine note:** a taught ability only takes effect for a character whose learnable pool already
  contains it (`ff9feqp`/`BattleResultUI.AddAp` match `AbilityIds` against the wearer's pool).
- **★ IN-GAME PROVEN (2026-06-13):** `teaches = ["Soul Blade"]` on Mage Masher (vanilla teaches Detect/What's That)
  → equipping it on Zidane made **Soul Blade** appear in his Skill command + Ability screen (Soul Blade is in
  Zidane's pool); **unequipping removed it** — the falsifiable check confirming it's the item, not pre-mastery.

### Added — `[[synthesis]]`: custom synthesis shops (recipes + opener), no DLL (0.9.86, ★ IN-GAME PROVEN)
- A **synthesis shop** combines ingredient items + gil into a new item. `[[synthesis]] shop = N` + `recipes = [{
  result, ingredients, price }, ...]` emits a `Data/Items/Synthesis.csv` (`FF9MIX_DATA`) delta; the opener is the
  **same `Menu(2, id)`** as a buy shop (reused verbatim from `content/shop.py` — NPC `opens_shop = N` or a standalone
  `zone`). The one whole FF9 item-system the kit had **zero** support for (gap-audit's biggest hole).
- **Grounded byte-for-byte in the Memoria source:** `Synthesis.csv` = `Comment;Id;Shops;Price;Result;Ingredients`
  with `#! UseShopList` (so `Shops` parses as an `Int32[]`), **whole-row merge by Id** (`ff9mix.LoadSynthesis` via
  `EnumerateCsvFromLowToHigh`) → the kit **mints recipe ids above the base max (63)** so a delta only *adds* recipes.
  A shop id opens as **Synthesis iff it is absent from `ShopItems.csv`** (`ff9buy.FF9Buy_GetType`); a shop's recipes
  are every row whose `Shops` contains the id (`ShopUI.InitializeMixList`). So the synth `shop` id must be `>= 32`,
  `<= 255`, and **not** a `[[shop]]` buy id — the build **errors** on that collision (it would flip to a buy shop).
- Ingredient duplicates are preserved (need N copies); `NoItem` dropped; base read LIVE in cp1252, **no game data
  committed**. `content/synthesis.py` + `build._emit_synthesis` (mod-global) + the synth `zone` opener (reuses
  `shop.inject_shop_regions`) + `ModLayout.synthesis_csv` + `config` + `deploy_field` reversible CSV loop +
  `_STARTUP_CSVS` (RELAUNCH note) + `validate()`. Multi-lens adversarially reviewed (0 blockers; folded a real
  `ConfigError`-escapes-the-build fix — also in the `itemdata` sibling — + lint type-guards for a scalar `zone` /
  string `ingredients` + doc/message precision). 21 tests (1520 total).
- **★ IN-GAME PROVEN (2026-06-13):** a custom synth shop (id 50, opened by a press-region `Menu(2, 50)` in a test
  field) opened as a **Synthesis** shop and offered a **net-new** recipe (Mythril Dagger ← Mage Masher + Potion, 50
  gil — not a vanilla combo); synthesizing it produced the item and deducted the ingredients + gil. Confirms the
  minted `Synthesis.csv` recipe row + the buy-vs-synthesis routing (id 50 absent from `ShopItems.csv` → Synthesis).

### Added — quick-win item columns: weapon `category`/`status_index`/`rate` + item `equippable_by` (0.9.85, ★ IN-GAME PROVEN)
- Extends the `[[weapon]]`/`[[item]]` CSV-delta surface (`content/itemdata.py`) with four more stock-moddable,
  no-DLL levers the kit previously only **read** for the Info Hub:
  - **`[[weapon]] category`** — the weapon class (`short-range`/`long-range`/`throw`/`offset`, by name or a 0-255
    `WeaponCategory` bitmask). Adding `throw` makes a weapon eligible for Amarant's Throw. (`Weapons.csv Category`, a Byte.)
  - **`[[weapon]] status_index` + `rate`** — the weapon's status effect: `status_index` selects an existing
    `StatusSets.csv` row (the `add_status[]` table). In Memoria the live consumer is **Soul Blade** (Zidane's Skill,
    for his thief-swords), which applies it directly; the normal-attack "Add Status" path is **dummied**
    (`TryAddWeaponStatus` has no callers), so `rate` (0-100) only feeds custom NCalc formulas (`WeaponRate`).
  - **`[[item]] equippable_by`** — a list of party-character names that **REWRITES** the item's 12 `Items.csv`
    equip-by-character bits (exactly those can equip it; everyone else cleared). Composes whole-row with `price`/`sell`/BonusId.
- Grounded byte-for-byte in the Memoria schema (`ItemAttack.cs` cols Category/StatusIndex/Rate, `ItemInfo.cs` 12-char
  mask, `WeaponCategory`) + the real install CSVs. `category` clamps to a Byte and `rate` to 0-100 (overflow crashes the
  loader / over-applies otherwise); `encode_category`/`encode_characters` validate names. `build.validate` lints bad
  category/character names + an **out-of-range `status_index`** (a KeyNotFound battle-crash, like the Phase-4 trap),
  range-guarded against the install's `Data/Battle/StatusSets.csv`. +15 tests (53 in test_itemdata; **1499** total).
- Closes two deferred item-lane tails (weapon class/status-on-hit + who-can-equip). Still deferred: consumable
  use-effects, synthesis recipes, the gear→ability list, item name/description text, net-new ids (>254, needs a DLL).
- **★ IN-GAME PROVEN (2026-06-13):** `equippable_by = ["Zidane"]` on **Broadsword** (vanilla Steiner/Marcus/Blank
  only) made it appear in Zidane's weapon-equip list. `status_index` on **The Ogre** (a Soul Blade thief-sword,
  re-pointed from Blind to **Mini**, set 10) — using **Soul Blade** in battle visibly shrank the enemy (vs vanilla
  Blind), confirming the on-hit status edit (the live route is Soul Blade, not a plain Attack — the latter is dummied;
  a first test with Venom+Poison killed the weak enemy via DoT before the icon could be read). `category` verified
  byte-correct in the deployed `Weapons.csv`. `FORMAT.md` documents the Soul Blade mechanic.

### Added — lint warns on a verbatim-carried gated door's un-remappable window text (#11) (0.9.80)
- A `[[gateway_carry]]` story-gated door is grafted verbatim, so if it opens its OWN window (e.g. "it's locked")
  the window keeps the DONOR txid — and the carry-text remap only touches `[[object]]`/`[[player_func]]` windows,
  so `--carry-text` can't fix it. `lint_logic` now decodes each carried gateway entry's windows and WARNS when
  it shows donor text, pointing to `--verbatim` (which ships the whole donor `.mes`, so the txid resolves) or
  authoring the line — instead of silently shipping wrong text. Only **2 real fields** (352, 552) hit this; the
  full carry+remap of gateway-entry windows is deferred (low value). +2 tests. This clears the #11 interim.
- **Docs:** `FORK_FIDELITY.md` trued up — #9 marked LANDED+PROVEN, #11 status, and a "small/orthogonal backlog
  is CLEAR" summary (the rest is battle-pillar #6/#13, mitigated cosmetic #8, or `--verbatim`-covered #12).

### Changed — a synth fork now spawns at the donor's real main arrival, not a centroid guess (#9) (0.9.79, ★ IN-GAME PROVEN)
- `extract_field`'s spawn cascade now PREFERS a real per-entrance ARRIVAL position (the player Init's
  `D9(0)/D9(4)` block, where the engine actually drops the player walking in a door) over the donor charPos
  (often a cutscene staging spot) or the c.1 walkmesh-centroid. Among the arrivals valid for the fork (in-bounds,
  on-camera, clear of every trigger zone, in the main walkmesh region) it takes the one nearest the visible
  centroid — the natural main-entrance landing, and FAITHFUL (a coordinate the real field uses). The Dali shop
  fork now spawns at its real entrance `(439,-122)` instead of the centroid `(83,209)`.
- Falls through to the exact c.1 charPos→centroid cascade when no arrival qualifies (a single-spawn field, a
  frame mismatch, or all arrivals off-screen/gated) → **byte-identical** there, so c.1 (in-game proven) and the
  blank/hut paths are preserved. A synth fork still can't reconstruct the per-DOOR table (its gateways are
  retargeted — that's `--verbatim`'s job), but the DEFAULT landing now matches the real field. +1 test.
  ★ **IN-GAME PROVEN** (Dali synth fork on scratch slot 4012): the player spawns at the shop's real entrance.

### Added — fork-report flags per-door player spawn (#9) (0.9.78)
- `eventscan.scan_player_arrivals(eb)` decodes a field's per-ENTRANCE arrival table: a warp sets the entrance
  var `D8:2` then `Field()`, and the target's player Init reads `D8:2` (a bare `05 D8 02 7F` push feeding a
  `0x06` switch) and branches to one `D9(0)/D9(4)/D9(6)` (x/z/face) block per entrance. Returns
  `{reads_entrance, arrivals, distinct}` (read-only; never raises). Grounded in the engine (`EventEngine`
  `JMP_SWITCHEX` 0x06) and verified across fields (Alexandria Main St = 4 blocks; Dali shop = 2 distinct spots).
- `fork-report` gains an **Arrival** line when a field has >1 distinct spawn: it warns that a SYNTH fork
  collapses the table to one `[player] spawn` (you arrive at the same spot via every door) and that `--verbatim`
  ships the real table. This is the #9 fidelity signal — surfaced before you fork. +3 tests.
- **Scope note (honest):** per-door spawn is FAITHFUL under `--verbatim` (it carries the whole player Init). A
  synth fork can't meaningfully *reconstruct* the table because its gateways are RETARGETED — the donor's
  entrance indices don't carry over to a fork's own doors. So the right answer for per-door fidelity is
  `--verbatim`, and the report now points there. (A bounded synth follow-up: use the donor's PRIMARY arrival as
  the default single spawn — a better default than the c.1 walkmesh-centroid — left for a separate in-game tick.)

### Added — equip stat bonuses: `[[equip_bonus]]` → `Stats.csv` / ItemStats (the level-up-growth lever, full authorship), IN-GAME PROVEN (0.9.81)
- Tune an item's **equip stat bonus** + elemental affinity via a partial CSV delta — **no DLL**. New block in
  `content/itemdata.py`: `[[equip_bonus]] name=…` with `speed`/`strength`/`magic`/`spirit` (the 4 growth-stat
  bonuses = `Stats.csv` Dexterity/Strength/Magic/Will — the input the engine's level-up accumulator reads,
  `ff9play.cs:302-305`, ~32 levels per permanent point) + `attack_element`/`guard_element`/`absorb_element`/
  `half_element`/`weak_element` (the 5 affinity bitmask columns). This closes the items-lane gap behind the
  classic FF9 "equip stat-boosting gear before you level" mechanic — the bonus shows immediately in the status
  menu on equip (`elem = base + bonus`) and drives permanent growth.
- ★ **The shared-`Empty`-row footgun, handled.** An item's bonus lives in `Stats.csv` keyed by its `BonusId`,
  but ~100 items share the all-zero `Empty` row 0 — editing it would buff every other no-bonus item. The builder
  detects sharing (counts each `BonusId`'s users from `Items.csv`): an item with a **dedicated** bonus row (used
  by it alone) is edited **in place** (seeded from the base so unchanged columns carry); otherwise it **mints a
  fresh `Stats.csv` row** (id = max existing + 1) **and repoints the item's `BonusId`** in an `Items.csv` delta —
  isolating the change to that one item. The repoint merges into the **same** `Items.csv` row as any `[[item]]`
  price edit (whole-row merge: both channels must ship together).
- Merge model = the same `EnumerateCsvFromLowToHigh` whole-row-wins as Weapons/Armors/Items (confirmed
  `ff9equip.cs:26`); base read LIVE from the install in cp1252; the repo commits **no game data**. Wired
  mod-global (`build._emit_item_data` gained an `equip_bonus` bucket) + `ModLayout.stats_csv` + the `deploy_field`
  reversible CSV loop (+ the RELAUNCH `_STARTUP_CSVS` note) + `validate()` (name-resolves / equippable[best-effort]
  / sets a field / element-names / non-negative) + `ItemStat.is_equippable`. 16 new tests (38 in `test_itemdata`).
  ★ **IN-GAME PROVEN (2026-06-13):** Bone Wrist (id 91) equipped → **Strength +50** (in-place, dedicated row 4);
  Mage Masher (id 2) equipped → **Magic +30** (mint id 176 + Items.csv `BonusId` repoint 0→176) — both confirmed
  in the status menu. **Roadmap #1-6 remain complete; this is the deferred `Stats.csv` follow-up of #6, now
  CLOSED.** RELAUNCH to apply (startup CSV).

### Added — item-data tuning: `[[weapon]]` / `[[armor]]` / `[[item]]` (roadmap #6, the last items-lane item), IN-GAME PROVEN (0.9.77)
- Tune EXISTING item stats via partial CSV deltas — **no DLL**. New `content/itemdata.py` + field.toml blocks:
  - `[[weapon]] name=… power=… elements=[…]` → a `Data/Items/Weapons.csv` delta (ItemAttack Power/Elements).
  - `[[armor]] name=… p_def=… p_eva=… m_def=… m_eva=…` → an `Armors.csv` delta (ItemDefence).
  - `[[item]] name=… price=… sell=…` → an `Items.csv` delta (ItemInfo Price/SellingPrice).
- ★ The engine MERGES these by id low→high **whole-row-wins** (`EnumerateCsvFromLowToHigh`), so a delta = the
  base file's header block (verbatim, incl. the `#!` option flags) + only the patched rows, each COMPLETE. The
  base rows are read LIVE from the user's install (cp1252, byte-preserving — apostrophes in weapon names
  round-trip) and the delta is GENERATED at build time into the mod folder — the repo commits **no game data**
  (the same provenance stance as `itemstats`). A `[[weapon]]` resolves the item → its `WeaponId` (via Items.csv)
  → the Weapons.csv row; `[[armor]]` via `ArmorId`; `[[item]]` by item id directly.
- Wired mod-global at the mod-write stage (`build._emit_item_data`, beside `_emit_shops`) + `ModLayout`
  `weapons_csv`/`armors_csv`/`items_csv` + the deploy CSV loop (`deploy_field.py`, reversibly). `validate()`
  checks name-resolves / right-type (best-effort, needs the install) / editable-field-present / element names /
  non-negative values. Needs a RELAUNCH (item CSVs load at startup, not via F6).
- 22 tests (synthetic-CSV builders, install-free, + install-gated end-to-end + validate). ★ **IN-GAME PROVEN
  (2026-06-13):** a `[[weapon]] name="Dagger" power=88` delta deployed to `FF9CustomMap` → relaunch → the equip
  menu showed the Dagger's Attack jump (base 12 → 88), confirming the whole CSV-delta pipeline (build → emit →
  deploy → merge → engine load) end-to-end. Deferred to a follow-up: weapon Category/status, `Stats.csv` equip
  bonuses + affinity, consumable effects, who-can-equip (`CharacterMask`), and minting net-new item ids (>254 —
  needs the `RegularItem` enum/DLL).

### Fixed — a synth fork no longer stacks a self-positioning NPC into a duplicate pair (#13 a) (0.9.76)
- `scan_objects_verbatim` now **dedups InitObject sites by arg**. `InitObject(slot, arg)` addresses *instance*
  `arg`, so the same `(slot, arg)` emitted twice is one instance re-init'd — in the donor a beat **director**
  fires just one of those sites per beat, but a SYNTH (non-`--verbatim`) fork has no director and would emit
  them all, **stacking identical copies**. Found in-game forking the Dali Weapon Shop: `DAF` (a shop NPC that
  hard-sets its own position via local `D9(0)/D9(4)`, ignoring the arg) is `InitObject`'d twice at arg 0 → a
  stacked pair. The scan now carries it as **one** instance at its real self-set spot `(-226,-241)`.
- Distinct args are a genuine row and are **kept** (field-122 `BBX`: a single entry offset per arg 128/129/130 —
  it self-positions from a `D9` *base* it shifts by the arg, so the old `slot_count==1` self-position guard was
  wrong; replaced by the arg-dedup, which is correct whether the object self-positions or inherits Main_Init D9).
- No effect on `--verbatim` forks (they ship the whole `.eb`, bypassing the object graft). +2 tests (a pure
  inject-then-arm round-trip; an install-gated end-to-end on the real Dali roster). Part of the #13 (c) tail.

### Performance — the test suite no longer re-reads the 68 MB event bundle on every install-gated call (0.9.75)
- **Root-caused the "test suite takes 2 hours" report.** The full suite is healthy: **1348 passed in ~146s** serially.
  The 2-hour run was resource **contention** — while pytest (pinned to one core) ran, concurrent background work
  hammered all cores AND re-read the large `p0data*.bin` bundles, thrashing the OS file cache so each of the
  ~150 install-gated `UnityPy.load(p0data7)` calls became a *cold* 68 MB physical read instead of a warm one.
- **Fix (hardens that failure mode):** `extract._load_env()` — a bounded-LRU in-process cache of the loaded
  STATIC base-game bundles, keyed by absolute path. `extract_event_script` / `extract_mapconfig` /
  `EventBundle` / `find_field` now reuse one parse of the hot event bundle instead of re-loading it per call
  (~5x on that pattern; the cache holds exactly the bundles in flight, the hot one staying resident by recency).
  Mirrors the existing `_load_mod_bundle` but kept SEPARATE — mod-folder bundles mutate on deploy, base bundles
  never do. `build_field_index` (force-scan, disk-cached) and `_events_bundle` (one-time detection) are untouched.
  This also speeds real CLI usage (a fork reads the event bundle for `.eb` + MapConfig). +2 tests.
- **Parallelism (optional):** added `pytest-xdist` to the `dev` extra. `py -m pytest -n 6` runs the suite in
  ~56s (2.6x) and stops a single pytest process being starved under load. ~6 workers beats `-n auto`/12 (66s) —
  the install-gated tests are disk-bound on the shared bundles, so too many workers re-contend on I/O.

### Fixed — a fork no longer spawns the player in a walled-off walkmesh pocket (#13 c.1) (0.9.73, ★ IN-GAME PROVEN 0.9.75)
- `import` now keeps the auto-picked `[player] spawn` in the **main walkable region**. A real field's stored
  spawn (`.bgi` charPos) is often a cutscene staging spot — for a shop it sits BEHIND the counter, a small
  walkmesh component walled off from the customer area, so a fork stranded the player there with no way out
  (found in-game forking the Dali shop). The spawn cascade now computes the walkmesh's connected components
  (`BgiWalkmesh.tri_components()`, by triangle neighbour links) and restricts every spawn candidate to the
  component with the most on-camera verts — so charPos is accepted only if it's in that main region, else the
  fallback centroid is taken from it too.
- ★ Offline-confirmed on the Dali shop: its walkmesh splits into a 21-tri customer area + a 7-tri behind-counter
  pocket; the spawn moved from `(-489,-348)` (pocket) to `(83,209)` (the customer area). **No-op on a
  single-region walkmesh → byte-identical** (the common case is untouched). +3 tests (`test_spawn`, incl. an
  install-gated Dali main-region assertion). This is part of the #13 (c) diorama tail.
- ★ **IN-GAME PROVEN** (fork deployed to scratch slot 4012): the player now spawns in the customer area, free to
  walk and reach the exit — no longer trapped behind the counter.

### Added — save-item editor: VANILLA (main-block) AP / ability editing, IN-GAME PROVEN (0.9.72)
- The AP / ability-mastery editor now reaches **vanilla (no-extra) saves** too, via the encrypted main block's
  old-format `pa` array — completing AP across both save kinds (the 7→7b pattern, now 8→8b).
- ★ **Layout finding (derived from the alpha-sorted SharedDataBytesStorage schema, empirically confirmed):** the
  244-byte old player struct (base `basis@5751`) lays out `…equip@5784 exp info@5793 level max name(128) pa@5936
  sa@5984…`, old-slot 8 ending exactly at `rareItems@7947`. A vanilla save's `pa@5936` decodes to each char's
  base-pool AP (Flee@40, Soul Blade@35, …), and the per-slot `info.menu_type@5793` gives the live preset. The
  vanilla saves use the **vanilla pool order**, so by-name resolution is correct on them.
- **`save_items.set_main_ap(container, block, character, ability, value)`** writes the `pa` byte(s) for one
  old-slot — `all` (mod-safe, every position) or a single ability by name/`AA:X`/`SA:X`/id resolved to its pool
  index. + `read_main_abilities` + `main_report`/`ItemReport.abilities` (so `items-inspect` shows AP on vanilla
  slots) + **`set_ap_in_save`** dual-write (extra-first, vanilla → main only) + `render_ability_dual`. CLI
  `items-set-ap` on a container now dual-writes; GUI Abilities works on vanilla slots.
- 5 new tests (synthetic container + install-gated by-name); 1336 suite green. Offline-validated on a temp copy
  of the real container's vanilla block (single by-name `Sacrifice` 28→55, `all max` 21/48→48/48, scoped to only
  that block + that slot's `pa`).
- ★ **IN-GAME PROVEN (2026-06-13):** `items-set-ap … Zidane all max --slot 0 --save-no 0 --apply` on the VANILLA
  slot 1/save 1 → loaded → Zidane's Ability menu showed every ability mastered (`21/48` → `48/48`). Note the old
  format caps at **48** abilities/char (the modern Moguri `pa_extended` carries 50 — see 0.9.71); each `all` masters
  everything that save's format can hold.

### Added — save-item editor: AP / ABILITY-MASTERY editing (the "AP unlocks" the user asked about), IN-GAME PROVEN (0.9.71)
- A new editor for a character's **ability AP / mastery** — set the AP a character has earned toward an ability
  (so an active ability becomes permanently usable, or a support ability becomes equippable). Memoria-extra-only
  for now (a vanilla no-extra save's main-block AP is a follow-up, like the stat editor's 7→7b).
- **`abilities.py`** (new, provenance-clean like `itemstats`/`keyitems` — ships nothing): the mod-agnostic
  `AA:X`/`SA:X` ↔ integer `abil_id` codec (matches Memoria `CsvParser.AnyAbility`/`ff9abil` exactly, round-trips
  even mod high-pool ids), plus a **best-effort** name + AP-to-master lookup read live from the install's
  per-character pool CSVs (`Data/Characters/Abilities/<Preset>.csv`). A modded id with no base entry degrades to
  its `AA:X`/`SA:X` token (no crash) — important because the user runs Moguri (custom ability pools).
- **`save_items.set_ap_extra(character, ability, value)`** — `ability` = a name / `AA:X` / `SA:X` / numeric id /
  `all`; `value` = `master` (the requirement, or AP_CAP=255 when unknown) / `max` / `forget` / a number. Edits
  the EXTRA's `players[].pa_extended` (`{id,cur}`), keyed by `info/menu_type` = the `CharacterPresetId`. The save's
  own `pa_extended` is the source of truth (the engine keys AP by pool entry), so it's correct on a modded save.
  Same safety as every prior writer: GATE 1 + a scoped diff (only that player's `pa_extended` moves) + atomic +
  post-write confirm + dry-run default + `.bak`. + `read_abilities` (mastered / in-progress, in `items-inspect`)
  + `render_ability_write`. CLI **`items-set-ap`**; GUI **Abilities** section; **`items --abilities`** lists which
  ability names resolve per character.
- **Adversarial-review hardening** (a 3-lens engine-fidelity / python-safety / integration workflow, 4 findings,
  all folded in + regression-tested): a save with `pa_extended` but no `menu_type` now degrades instead of
  crashing the whole report; a **duplicate** `pa_extended` id sets EVERY match (the engine loads the last) so the
  edit is deterministic; the bulk `all` summary classifies mastery from the resolved per-ability outcome and shows
  `changed/pool-total`.
- New `abilities.py` tests + ability write tests (synthetic + install-gated real-save dry-run); 1307 suite green.
- ★ **IN-GAME PROVEN (2026-06-13):** `items-set-ap <save> Zidane all max --apply` on the real Moguri save →
  loaded → Zidane's Ability menu showed **every ability mastered** (filled gem icons; 0/50 → 50/50). Confirms the
  `pa_extended` AP write loads and masters in-game, names/tokens resolve on a modded pool, and the mod-robust
  `max` force-master works.

### Added — battle-tuning Phase 6c-iii: the enemy-AI LINTER + the `[[scene.ai_function]]` build surface (0.9.72)
- **`battle/ailint.py`** — the CAPSTONE of the battle-AI stack: validate a scene's enemy AI OFFLINE (the "I can't
  see the game" superpower applied to AI). `lint_ai(eb, atk_count=)` runs SOUND checks — a shipping scene must lint
  CLEAN: **decode** (every function decodes to its boundary), **jump bounds** (every relative jump lands on an
  instruction inside its function), **reachable terminator** (a forward reachability walk flags a path that falls
  through the END without a RET/terminator — trailing NOP padding after a RET/loop is correctly UNREACHABLE), and
  **Attack index** (an immediate Attack operand `< the scene attack count`). ★ **Soundness proven by a 562-scene
  sweep: ALL 562 shipping battle scenes lint CLEAN (0 false positives).** CLI **`battle-ai --lint <scene>`** (exit 1
  on any issue).
- **`battle/aiauthor.py` + `build.py`** — the declarative **`[[scene.ai_function]]`** surface: a `battle.toml` adds
  or replaces an enemy-AI function (`entry` / `tag` / `source` / `replace`), assembled (6c-ii `cmdasm`) + spliced at
  build, applied per-language AFTER `[[scene.ai_patch]]` (length-changing follows same-length). The build VALIDATE
  hook now lints the **composed** (`ai_patch` + `ai_function`) eb — exactly what ships.
- ★ A 3-lens adversarial review (it independently re-ran the 562-sweep) confirmed the design SOUND and found + fixed
  four real defects: **(HIGH)** `_jump_target` decoded `JMP_IFNOT` (0x02) *signed*, but the engine reads it
  **unsigned** (`beq`/`getUShortIP`, unlike `bra`/`bne`) — so the backward-`JMP_IFNOT` fault the linter promises to
  catch was *missed*; now decoded unsigned (it lands out of bounds → flagged). **(MEDIUM)** the validate hook linted
  the *un-patched* donor, not the composed eb the build ships → now composes `ai_patch`+`ai_function` and lints the
  result (catches an `ai_patch` that repoints a jump/Attack-index out of range). **(LOW)** the terminator set
  `{RET, TerminateEntry}` missed the engine's other `adFin()` path-enders (`GameOver` 0xF5, `STOP`, `Battle`, …) →
  a branch ending in one was false-flagged; the set is widened and SHARED with `aiauthor`'s authoring guard so they
  never drift. **(LOW)** an out-of-`u16`-range `tag` crashed with a raw `struct.error` → now a clean `AiAuthorError`.
  44 tests (`test_ailint` + `test_aiauthor` + `test_cmdasm`). **Phase 6c COMPLETE** — the kit now reads, tunes,
  authors, *and* validates the whole enemy-AI stack on stock Memoria.

### Added — save-item editor: vanilla (main-block) STAT editing + the GUI on vanilla slots, IN-GAME PROVEN (0.9.69)
- The stat editor now reaches **vanilla (no-extra) saves** too, and the GUI's Stats control works on them —
  completing the stat editor across both save kinds (and the GUI across all five editors on every slot).
- ★ **Layout finding (empirical, verified vs the extra on all 9 players):** the old-format player struct stores
  `basis` (displayed, Bytes) at **5751** and `bonus` (the equipment accumulator, UInt16 LE) at **5759**, +244·old-slot;
  per-stat byte offsets basis `{dex:0, mgc:5, str:6, wpr:7}`, bonus `{dex:0, mgc:2, str:4, wpr:6}`.
- **`save_items.set_main_stat(container, block, character, stat, target)`** — writes the basis Byte + bonus UInt16
  (same target-stat / formula-delta model as `set_stat_extra`), scoped to those ≤3 bytes, validate gate + atomic +
  backup + confirm. + `read_main_stats` + `main_report`/`ItemReport.stats`. **`set_stat_in_save`** dual-write; CLI
  `items-set-stat` on a container dual-writes; `render_stat_dual`. GUI `_edit_stat` now uses the container path.
- 6 new tests. ★ **IN-GAME PROVEN (2026-06-13):** set Zidane's Strength 27 → 99 on the VANILLA slot 1/save 1's
  main block → loaded → the status menu showed 99 (gil + key items + other slots untouched). **The #5 save-item
  editor is now complete: gil/items/equipment/key-items/stats on BOTH Memoria and vanilla saves, via CLI and GUI.**

### Added — save-item editor: the equipment-driven STAT editor (`items-set-stat`), IN-GAME PROVEN (0.9.68)
- Edit a character's permanent growth stat — Speed / Strength / Magic / Spirit — the hidden "level up in stat
  gear" system. ★ **Engine formula (`ff9level.cs`):** `displayed = base + level·growth + (bonus >> 5)`, capped per
  stat (Speed/Spirit 50, Strength/Magic 99); `bonus` is the equipment accumulator, `basis` is the displayed
  value (recomputed from `bonus` only at level-up; on LOAD the engine runs `FF9Play_Update`, not `_Build`).
- **`save_items.set_stat_extra(extra, character, stat, target)`** — the "set target stat" model: writes BOTH
  `players[].basis.<field>` (shows immediately) AND `players[].bonus.<field>` (holds the value through level-ups).
  ★ The needed bonus comes from the **formula delta** — `new_bonus = (target − old_basis + (old_bonus>>5)) << 5` —
  which cancels the base/growth terms, so **no game-data table is needed**. Scoped to that one player's
  basis+bonus; GATE 1 + atomic + backup + post-write confirm + dry-run. + `read_stats` + `render_stat_write`.
- CLI **`items-set-stat <save> <character> <stat> <value>`**; GUI gains a **Stats** control (who / stat / value →
  Preview / Apply). 6 new tests.
- Scope: extra-only (Memoria saves — the load-authoritative store). The vanilla **main-block** stat editor is a
  follow-up — the offsets are already mapped (basis @ 5751, bonus @ 5759 UInt16, + 244·old-slot).
- ★ **IN-GAME PROVEN (2026-06-13):** set Zidane's Strength 21 → 99 on slot 1/save 3 → loaded → the status menu
  showed Strength 99 (Vivi + gil untouched). The displayed value + the bonus accumulator both set correctly.

### Added — battle-tuning Phase 6c-ii: the enemy-AI COMMAND assembler + branch insertion (0.9.70)
- **`eb/cmdasm.py`** — assembles a whole INSTRUCTION (and a BLOCK of them), the next step after 6c-i's expression
  assembler: the body of a NEW enemy-AI branch. It mirrors `disasm.read_code`'s byte-walk step for step (the `0xFF`
  extended page, the `argFlag` byte for `op >= 0x10`, the forced-expr `SET`=0x05, the stream-read operand count for
  the variable ops 0x06/0x0B/0x0D + the count-prefixed 0x29), so it reproduces the exact bytes `read_code` decoded.
  Expression operands (`{ … }`) go through 6c-i's `exprasm.assemble`; immediates are LE of the opcode's `argsize`.
- **`assemble_block`** adds the authoring layer: `label:` lines + symbolic jump targets (`JMP done`,
  `JMP_IF {expr} loop`) resolved in a two-pass walk to the relative offset the engine reads (instruction sizes are
  known up front — a jump immediate is always 2 bytes — so offsets precede the targets).
- **`battle/aiauthor.py`** — the bridge: `add_ai_function` / `replace_ai_function` assemble a branch and splice it
  into a forked battle `.eb` via the EXISTING byte-safe length-changing primitives (`eb.edit.add_function` grows the
  func table + fixes every `fpos` and later-entry offset; `replace_function_body` swaps a body of any length). The
  first LENGTH-CHANGING AI edit. CLI **`battle-ai --asm-block`** previews a block → bytes + a re-disasm proof.
- ★ A 3-lens adversarial review (decode inversion · block/jump layout · insertion safety) confirmed the layout math
  and the relative-jump survival of the splice, and found + fixed two real defects: **(HIGH)** the engine has *no
  per-function length bound*, so a branch that doesn't end in a flow terminator runs the IP off into adjacent
  bytecode at runtime — `aiauthor` now REQUIRES the body to end in `RET` (0x04) or `TerminateEntry` (0x1C);
  **(MEDIUM)** the engine reads `JMP_IFNOT` (0x02, `beq`) offset **unsigned** while `JMP`/`JMP_IF` (`bra`/`bne`) are
  signed, so a *backward* `JMP_IFNOT` would execute as a ~64KB forward jump — now rejected with a clear error.
  Plus a bracket-imbalance guard in the operand splitter. The strongest test walks the **real EF_R007 AI** and
  asserts every instruction *and* every function assembles back byte-for-byte, and that `add_ai_function` on the
  shipping Goblin AI re-parses with every other function + later entry byte-intact. 35 tests
  (`test_cmdasm` + `test_aiauthor`). **Phase 6c next (6c-iii):** a battle linter (valid AI tags, an Attack index in
  range, a reachable RET) + the declarative `[[scene.ai_function]]` build surface.

### Added — save-item editor: vanilla key items (main-block `rareItems`) + the GUI key-item control, IN-GAME PROVEN (0.9.66)
- Completes key items: a **vanilla (no-extra) save's key items** are now editable, and the **GUI** gains a
  Key-items give/remove control — so the #5 editor covers **every data type on every save kind**.
- ★ **Layout finding (empirical):** the old-format main block holds key items in a **64-byte `rareItems`
  bitfield at offset 7947** — 2 bits per item (obtained at the even bit, used at odd), 256 items (item `j` →
  byte `7947 + j//4`, shift `(j%4)*2`). Verified byte-stable: the vanilla blocks decode to sensible key-item
  sets (16 / 21 items). (The probe memory's "rareItems@7947 was WRONG" was a save with zero key bytes there —
  the *offset* is right.)
- **`save_items.set_main_keyitem(container, block, keyitem, *, obtained, used)`** — flips exactly the item's 2
  bits (validate gate · scoped byte-diff: only that byte moves · atomic · backup · position-aware confirm ·
  dry-run). + `read_main_keyitems` + `main_report` now carries key items. **`set_keyitem_in_save`** dual-write
  (main `rareItems` + extra `rareItemsEx`); CLI `items-set-keyitem` on a container dual-writes; `render_keyitem_dual`.
- **GUI** (`apps/ff9_items.pyw`): a "Key items" section (name → Preview / Give / Remove), dual-write on a
  container (handles vanilla), extra-only on an extra-save. 8 new tests.
- ★ **IN-GAME PROVEN (2026-06-12):** gave Falcon Claw to the VANILLA slot 1/save 1's main block → loaded → it
  shows in the Key Items menu (16 → 17), gil/equipment intact. **The #5 save-item editor is now 100% complete** —
  every data type (gil, items, equipment, key items) on every save kind (Memoria + vanilla), via CLI and GUI.

### Added — battle-tuning Phase 6c-i: the enemy-AI EXPRESSION ASSEMBLER (`eb/exprasm.py`) (0.9.67)
- **`eb/exprasm.py`** — the keystone of Phase-6c new-branch *authoring*: the exact **inverse of the Phase-6a
  disassembler** (`disasm.pretty_expr`). Authoring new enemy-AI logic (a phase-switch condition, a counter
  trigger) means writing the RPN **expression token stream** the engine evaluates; this `assemble()`s that stream
  from the same readable `{ tok tok … }` form the disassembler prints. The load-bearing property is the **round
  trip**: `assemble(pretty_expr(bytes)) == bytes` (byte-exact for canonical bytecode) and
  `pretty_expr(assemble(text)) == text`.
- Each token maps to one encoded token (the inverse of every `pretty_expr` branch): a bare op mnemonic
  (`B_LT`/`B_CURHP`) → its `op_binary` byte; `const(N)` → `B_CONST` (0x7D + 2 LE bytes); `const4(N)` → `B_CONST4`
  (0x7E + 4 LE bytes — `pretty_expr` now prints `const4(N)` distinctly so the round trip is exact); `Source.Type[i]`
  → the `0xC0` variable token (the engine's *minimal* encoding: a 1-byte index, or the `0x20` long-bit + a 2-byte
  LE index when `i > 0xFF`); `B_SYSVAR[i]`/`B_SYSLIST[i]`/`obj(uid=U).f[F]`/`B_MEMBER(i)`/`B_PTR(i)` → their
  operand tokens; `B_EXPR_END` (0x7F) terminates. Provenance-clean (only the open-source op/enum **names**).
- CLI **`battle-ai --asm "{ … }"`** assembles an expression → its bytes + a re-disassembly proof (no scene needed).
- ★ A 3-lens adversarial review (round-trip inversion · engine fidelity vs `EBin.cs` · robustness/API) confirmed
  the engine byte-layout matches `EBin.cs` exactly (var bits, long-index LE, `B_OBJSPECA` uid/field order, const
  widths) and found + fixed: **(HIGH)** the `opXX` fallback was a back-door — a numeric `op7D`/`opC4` assembled to
  a *bare* byte that desynced the stream and mis-executed in-engine; `assemble` now accepts `opXX` only for a
  genuinely-unnamed pure-operator byte (`< 0xC0`, not in the op table) and rejects a named or variable byte with a
  "write it by name / in operand form" message. **(LOW)** the CLI re-disasm dumped a raw `IndexError` traceback on
  a non-re-parsing stream — `assemble()` now **self-verifies** (re-parses its own output, raising `AssembleError`
  unless it consumes exactly every byte), making the round trip a *library-boundary invariant* (this also closes
  the CLI crash and a mid-stream-`B_EXPR_END` edge). **(consistency)** `const`/`const4` now range-check (honoring
  `assemble_token`'s docstring + matching the var/sysvar siblings + the 6b `B_CONST4` cap) instead of silently
  masking a typo. The strongest test walks the **real EF_R007 AI** and asserts `assemble` reproduces the shipping
  game's expression bytes byte-for-byte; + a 256-byte `opXX` sweep. The long-form-small-index and `0x80-0xBF`
  divergences were reviewed and confirmed out-of-scope (the engine's own encoder never emits those). 35 tests
  (`test_exprasm`). **Phase 6c next:** the command assembler + length-changing `add_function` branch insertion + a
  battle linter (this assembler is the prerequisite).

### Added — battle-tuning Phase 6b: same-length enemy-AI constant patches (`[[scene.ai_patch]]`) (0.9.64)
- **`battle/aipatch.py`** — the first AI *authoring* step (read = Phase-6a `battle-ai`). An enemy's AI is the
  per-scene `EVT_BATTLE_*.eb` bytecode; the safest edit is a *literal* one — change a numeric CONSTANT in place
  (an HP threshold a phase-switch compares, the attack index a turn selects, a `Wait` count) **without moving any
  byte**: no `fpos`/entry-table fixup, byte-accurate by construction (the eb-codec identity holds), like
  `scene_data`'s surgical raw16 patch.
- `constant_sites` locates every patchable numeric constant (command immediates + `B_CONST`/`B_CONST4` expression
  literals) with its byte offset + width — a walk that **mirrors the proven `read_code`/`pretty_expr` byte-for-byte**
  so a reported offset is exactly where the constant lives. `battle-ai <scene> --sites` prints them (224 on the
  real EF_R007). `[[scene.ai_patch]]` (in `battle.toml`) cites `at = <offset>`, a required `old`-value guard (a
  stale/wrong offset fails LOUD, never corrupts a byte), and `new` (must fit the same width). Applied to the forked
  eb at build, per-language at the same offset (the bytecode is language-identical).
- Reaches NUMERIC LITERALS only (the "same-length literal patch" tier); structural changes + an expression
  assembler are Phase-6c. Read-the-AI-first is mandatory — you cite the offset the disassembler prints.
- ★ A 3-lens adversarial review (site-walk fidelity vs the decoders · patch safety · build wiring) found and
  fixed: a **3-byte (Int24) immediate** crashed the patcher with `KeyError` (the width map had only 1/2/4 → now a
  generic little-endian width-N pack); a truncated/corrupt eb leaked a raw `IndexError` (now a clean
  `AiPatchError`, mirroring the read path); and `B_CONST4` is **masked to 26 bits** in-engine so a too-large `new`
  would silently change in-game (now per-site capped). The B_CONST signedness path was confirmed benign
  (byte-faithful round-trip). 9 tests (`test_aipatch`) + a real-donor round-trip; *in-game proof is the human step.*

### Fixed — a synthesized fork no longer carries cutscene WARP-directors (#13b), IN-GAME PROVEN (0.9.62)
- A non-`--verbatim` fork's object carry (`content.object.graft_objects`) now SKIPS cutscene **warp-directors** —
  an object whose kept LOOP (tag 1) fires `Field()`. Carrying one renders it as a STACKED, DUPLICATE actor
  (object-carry treated the director as a standing NPC) — the #13 stacked-spawn symptom — and its gated `Field()`
  warps could fire if its phase advanced. Empirically the Dali Weapon Shop's director was carried
  `graft_safety='clean'` with all 13 `Field()` ops in its loop. New `object._loop_warps()`;
  `graft_objects(..., out_skipped=[])` collects the dropped directors' donor ids.
- ★ **IN-GAME PROVEN (2026-06-12):** an A/B of synth Dali-shop forks (4012 = fixed, 4013 = a monkeypatched
  buggy control that keeps the director) — the buggy fork shows **2 shopkeepers** (the real one + the director
  rendered on top), the fixed fork shows **1**. (The warp itself didn't fire — the director's phase was idle at
  the entered beat — so the observable harm is the stacked duplicate, the canonical #13 case.)
- Deliberately NARROW (`Field()` only, checked on the carry_tags-filtered bytes): an `init_only` object whose loop
  was already dropped still renders, and phase-switch-only animated props + the save-Moogle (no LOOP `Field()`) are
  UNAFFECTED — the proven prop/save-point/player-graft carries keep working. `--verbatim` keeps directors whole.
- This is #13's last code piece (after the roster-by-beat analyzer): a synth fork of a story-event field is now a
  clean static diorama instead of a stacked-cutscene mess. +6 tests (`test_object_graft`, incl. an install-gated
  Dali assertion). Remaining #13 tail: the multi-instance self-positioned + per-door spawn sub-bugs (e.g. the
  synth fork still spawns the player behind the shop counter — the donor's cutscene staging spot).

### Added — battle-tuning Phase 6a: the enemy-AI disassembler view (`battle-ai`) (0.9.63)
- **`battle/battleai.py` + CLI `battle-ai <scene>`** — the read-only "see the enemy's AI" step (the foundation of
  Phase 6, per the doc's staging: disassembler → same-length patches → new branches). A battle scene's
  `EVT_BATTLE_*.eb` is the same bytecode container + `EventEngine` interpreter as a field script, so the kit
  already round-trips and decodes it — what was missing to *read* enemy AI is the vocabulary:
  - **`eb/_exprtable.py`** — the `op_binary` expression-operator table (all 128 values, transcribed from the
    open-source `EBin.cs`) + the variable-token decode: a `0xC0+` token → `Source.Type[index]` (so a story-flag
    read shows as `Global.Bit[8512]` — the kit's `GLOB_BOOL` encoding — and an enemy-HP read as `B_CURHP`).
  - **`eb/disasm.pretty_expr`** — names an expression token stream (`op{52}` → `B_CURHP`), mirroring the proven
    `read_expr`'s byte-walk exactly.
  - **`battleai.disassemble_ai`** — walks the eb: entry 0 = Main_Init (spawn/AI binding), entries `1..TypCount` =
    per-enemy-type AI, functions by TAG (Main/Counter/ATB/Dying), each instruction with named commands
    (`SET`/`JMP_IF`/`InitObject`/`BTLCMD`, incl. a control-opcode overlay `OP_NAMES` leaves unnamed) + annotated
    expressions.
- Read-only + offline; provenance-clean (only the open-source opcode/operator NAMES committed; donor bytes read
  live, never committed). Already reads the real EF_R007 Goblin AI cleanly.
- ★ The load-bearing property is **byte-walk parity**: a parity test asserts `_decode_func_pretty` yields the SAME
  instruction offsets as the proven `read_code` across every AI function of a real donor — so the annotated view
  can never mis-align. 10 tests (`test_battleai`), verified by a 3-lens adversarial review (table vs `EBin.cs`,
  byte-walk fidelity, presenter/provenance) which found only a low truncated-eb `IndexError` (guarded — a legible
  `<malformed>` note). *Authoring (Phase 6b: same-length constant patches) is next.*
### Added — save-item editor #5 step 6: KEY/important items (`items-set-keyitem`), IN-GAME PROVEN (0.9.65)
- The last data type: **give / remove a key (important) item by name** in a Memoria save. FF9 has no symbolic
  enum for key items, so names are read **LIVE** from `<install>/StreamingAssets/Text/<lang>/KeyItems.strings`
  (`"$keyNNNN" = "Name"`), cached in-memory, **shipping/committing nothing** — the same provenance-clean live
  pattern as `itemstats`. New `ff9mapkit/keyitems.py` (`resolve`/`name_of`/`available`; 80 key items, ids 0-79).
- **`save_items.set_keyitem_extra(extra, keyitem, *, obtained=True, used=False)`** — edit the extra's
  `40000_Common/rareItemsEx` list (each entry `{id, obtained, used}`; ★ the bools are VALUE strings
  `"True"`/`"False"`, NOT Bool leaves — `bool("False")` would be a bug, so the text is compared). Both flags False
  removes the entry; otherwise add (ascending-id) / update. Same safety (GATE 1 + scoped-change check (only
  `rareItemsEx` moves) + atomic + backup + post-write confirm + dry-run). `read_keyitems` + `ItemReport.keyitems`
  + the inspect/render now show held key items; CLI **`items-set-keyitem <save> <name> [--remove] [--used]`**.
- Scope: key items are EXTRA-only here (the load-authoritative store, Memoria saves). Main-block `rareItems`
  (the 64-byte 2-bit bitfield, for vanilla saves) + a GUI key-item control are follow-ups. 7 new tests; 1200 green.
- ★ **IN-GAME PROVEN (2026-06-12):** gave Falcon Claw to slot 1/save 3 (a Memoria save with 0 key items) → loaded
  → it shows in the Key Items menu (gil/items untouched). **The #5 editor now covers every save data type** — gil,
  regular items, equipment, and key items.

### Added — fork-report ROSTER-BY-BEAT: which carried cast a story-event director spawns at each beat (#13) (0.9.60)
- `fork-report` now prints a **Roster by beat** table for rotating-cast (story-event) fields: for each
  ScenarioCounter beat the field gates on (plus a scenario-zero baseline), the carried NPCs/actors the director
  actually spawns at that beat — so you can pick the right `[startup]` beat OFFLINE instead of deploy-and-warp.
  Built on a small **symbolic walk of Main_Init** (`_spawned_slots`): it evaluates only the ScenarioCounter
  comparisons that drive a conditional jump (decoded by `_sc_cond`/`_eval_cmp`), follows forward jumps incl. the
  unconditional 0x01 (correctly stepping over an if/else's else-branch), and collects the `InitObject` slots
  reached — handling dispatch chains, if/else, and nesting (vs naive range-containment). New `ForkReport.beat_roster`.
- This operationalizes the #13 finding (verbatim + `[startup]` shows a beat-correct rotating roster): the table
  REPRODUCES the in-game observation OFFLINE — on the real Dali Weapon Shop (354) the cast is `DAC`+`DAF*` at
  Dali (2600), gains `DAW` at Iifa/Alexandria (6990/8800), and is wholly different (`HUF`/`HUM`) at Pandemonium
  (11090). Honest about its limits (flag gates assumed present, compound/looping gates run once, a director's
  OWN per-beat model swap not traced — all surfaced in the output caveat). Reviewed by a 2-lens adversarial +
  verify pass (the variation gate now compares (slot, model); backward-jump fall-through pinned by a test).
- +9 tests (`test_forkreport`): the condition decode, the symbolic walk (dispatch chain / if-else / non-SC
  fall-through / backward-jump), and an install-gated Dali rotation assertion.

### Added — battle-tuning Phase 5b: support-ability gem-cost deltas (`[[ability_gem]]`) (0.9.61)
- **`[[ability_gem]]` → `Data/Characters/Abilities/AbilityGems.csv`** (in `battle/characterdelta.py`) — re-cost a
  support ability's gem requirement, the build-economy balance lever (cheaper Auto-Haste = stronger builds). A
  per-SupportAbility **partial delta** (`EnumerateCsvFromLowToHigh`, `ff9abil.cs:409`): only the changed rows are
  emitted, the base supplies the other 63. `ability` resolves a SupportAbility by name (the enum `AutoHaste`, the
  CSV display `Auto-Haste`/`HP+10%`, or a 0-63 id) via a committed name table; `gems` sets `GemsCount`.
- The **`#! IncludeBoosted`** option line + the Boosted column are preserved verbatim (load-bearing: the engine
  parses Boosted only when that option is present). Range-checked offline; the SupportAbility name table is the
  open-source Memoria enum (provenance-clean), gem **values read live, never committed**.
- Wired mod-global into `build`/`validate_field`/`deploy_field`. CLI **`ability-gems`** lists the abilities +
  live costs (the tuning targets; `-f` filter).
- ★ A 3-lens adversarial review (engine source + the live 64-row CSV) verified the name table (64/64 vs the
  enum), the `#! IncludeBoosted`/Boosted handling, the partial-merge + coverage gate, and provenance, and caught
  one real gap: the CSV display name **"Odin's Sword"** (the only possessive) normalized to `odinssword` ≠ the
  enum `OdinSword`→`odinsword`, so copying the catalog-printed name failed to resolve — aliased (now every one of
  the 64 displayed names round-trips). 6 tests + a real-install smoke; *in-game proof is the human step.*

### Added — save-item editor #5 step 4b: main-block EQUIPMENT (vanilla saves fully editable), IN-GAME PROVEN (0.9.59)
- The last deferred piece: a **vanilla (no-extra) save's EQUIPMENT** is now editable, completing the editor.
- ★ **Layout finding (empirical):** the old format stores **9 player structs of 244 bytes**, each with a
  **5-BYTE equip array** `[weapon,head,wrist,armor,accessory]` at `MAIN_EQUIP_OFF=5784 + 244·old_slot` — verified
  byte-stable (all 9 players decoded correctly vs the extra on the autosave, and to valid loadouts on both
  vanilla blocks). The 9 old-slots: 0-4 = Zidane/Vivi/Garnet/Steiner/Freya, 8 = Beatrix; **slots 5/6/7 are SHARED
  by Quina/Eiko/Amarant and their story temp-replacements Cinna/Marcus/Blank** (`SelectOldSaveSlot`) — the
  GUI/inspect shows each slot's current gear so you target the right one.
- **`save_items.set_main_equip(container, block, character, slot, item)`** — set one of a character's 5 equip
  bytes (`character` = CharacterId / name / Cinna·Marcus·Blank → old-slot; `item` = name/id or `empty`/255).
  Same proven safety (validate gate · scoped byte-diff: exactly one byte moves · atomic · backup · position-aware
  confirm · dry-run). Plus `read_main_equipment` + `main_report` now carries the 9 players' equipment.
- **`save_items.set_equip_in_save`** dual-write orchestrator (extra keyed by CharacterId/12, main by old-slot/9 —
  resolved independently); CLI `items-set-equip` on a container dual-writes; `render_equip_dual`. The **GUI** now
  enables the Equipment editor on vanilla slots (was refused).
- A focused adversarial-verify workflow reviewed it (3 doc-staleness findings, all folded in). 18 new tests; 1172
  suite green.
- ★ **IN-GAME PROVEN (2026-06-12):** on the vanilla slot 1/save 1 — Steiner weapon→Excalibur + Ribbon accessory,
  and **Quina (an active-party member at the SHARED old-slot 5) weapon→Gastro Fork showed in-game** (also proving
  the shared slot-5 mapping correctly targets Quina, not Cinna). **The #5 save-item editor is now COMPLETE and
  fully proven** — read+write gil/items/equipment on both the Memoria extra and the encrypted main block (vanilla
  saves), via CLI and GUI. Only key/important items (the 2-bit `rareItems` bitfield) remain deferred.

### Added — save-item editor #5 step 4b cont.: main-block ITEMS + GUI vanilla-save editing, IN-GAME PROVEN (0.9.57)
- Completes editing a **vanilla (no-extra) save** — now its **inventory** is editable too (gil landed in 0.9.56),
  via both the CLI and the GUI.
- **`save_items.set_main_item(container, block, item, count)`** — set an item's count in the main block's 256-pair
  array (count 0 removes → clean `{0,255}` padding; updates in place / adds at the first free slot, reserving the
  last as the padding terminator; clamps 99; `NoItem` rejected). Same safety as `set_main_gil`: validate gate, a
  **scoped byte-diff** that only item-array bytes may move, atomic write, timestamped backup, a **position-aware**
  post-write confirm, dry-run default. Plus `read_main_inventory` (collects all live stacks, tolerating the
  count==0 mid-list gaps FF9 leaves) + `main_report`.
- **`save_items.set_item_in_save`** dual-write orchestrator (main + extra mirror). CLI `items-set-item` on a
  container now dual-writes. `render_item_dual`.
- **GUI (`apps/ff9_items.pyw`)** — refactored to dict targets carrying the container/block; a **vanilla slot is
  now editable** (gil + items via the main block), a Memoria slot dual-writes, and equipment is correctly refused
  on a vanilla slot (main-block equip is the deferred follow-up). `items-inspect` + `inspect()` now decode vanilla
  slots too (were "not yet supported").
- A 3-lens adversarial-verify workflow (crypto/engine · python-safety · integration/GUI) found 11 issues — all
  folded in. The load-bearing one (a **bug**): the dual-write committed the main block before the load-
  authoritative extra, so a failed extra leg would silently show the OLD value in-game → **now the extra (authoritative)
  leg is written FIRST** (a partial failure leaves the visible value correct; documented). Also: reserve the last
  item slot as the padding terminator; a clean ValueError (not IndexError / a wrong-block read) for a bad block
  index; a position-aware post-write confirm; and the stale "extra-only / main mirror pending" docstrings refreshed.
- 18 new tests (synthetic encrypted containers + the GUI `--smoke` vanilla path); suite green.
- ★ **IN-GAME PROVEN (2026-06-12):** on the vanilla slot 1/save 1, edited the inventory via the main block —
  Potion 68→99 (change) + DarkMatter x3 (add, not previously held) — gil + other items + other slots untouched —
  loaded in-game and both showed, inventory intact. **Step 4b is fully done: a vanilla (no-extra) save is editable
  for gil AND items, via CLI + GUI.** The #5 editor is now functionally complete (extra: gil/items/equip; main
  block: gil/items); only main-block equipment + key items remain, both deferred.

### Added — battle-tuning Phase 5: character/growth CSV deltas (`[[character]]` / `[[leveling]]`) (0.9.58)
- **`battle/characterdelta.py`** — the PLAYER side of battle balance (the Phase-3 `actiondelta` twin for the
  enemy/ability side), as `Data/Characters` CSV deltas read live from the install:
  - `[[character]]` → **BaseStats.csv** (`dexterity`/`strength`/`magic`/`will`/`gems` by character name or 0-11
    id) — a **per-id partial delta** (`EnumerateCsvFromLowToHigh`, `ff9level.cs:30`): only the changed characters
    are emitted, the base supplies the other 11.
  - `[[leveling]]` → **Leveling.csv** (`exp`/`bonus_hp`/`bonus_mp` by `level = 1..99`) — the 99-step growth curve.
    The engine reads this **WHOLE-FILE** (`GetCsvWithHighestPriority`, `ff9level.cs:53`) and gates at ≥99 rows, so
    a partial would *wipe* the curve → the emitter reads the base 99 rows live, patches the named levels, and
    re-emits ALL 99 (HP grows `BonusHP·Strength/50`, MP `BonusMP·Magic/100`).
- Range-checked offline against the real C# column types (Dex/Str/Mag/Will = Byte, Gems = UInt32, Exp = UInt32,
  BonusHP/BonusMP = UInt16) so an out-of-range value fails the build, not the game's boot. The `CharacterId`
  name→id table is the open-source Memoria enum (provenance-clean); stat **values are read live, never committed**.
- Wired mod-global into `build` (`_emit_character_data`), offline lint into `validate_field`, both CSVs into
  `deploy_field`'s reversible deploy, and **Leveling into the deploy-time shadow guard** (`deploystack`, whole-file
  like `InitialItems`). CLI **`characters`** lists the live base stats (the tuning targets). `ModLayout` paths.
- ★ A 4-lens adversarial review (engine source + the live CSVs) verified the column layout, the whole-file
  Leveling handling, the range guards, and the merge model, and caught: a **provenance leak** (a test fixture row
  was byte-identical to the real install — de-leaked), the **missing Leveling shadow guard** (added), and a
  single-table `[character]` vs `[[character]]` build/lint disagreement (now normalized). 15 tests + a real-install
  smoke.
- ★ **IN-GAME PROVEN (2026-06-12):** a `[[character]]` boost of Vivi (Dexterity/Strength/Magic/Will → 40/80/90/45)
  seeded into the party (`[party] add = ["vivi"]`) on a New-Game landing field — at a **fresh New Game** her
  status menu read **Speed 40 / Strength 80 / Magic 90 / Spirit 45** vs vanilla 16/12/24/19. So `[[character]]` →
  `BaseStats.csv` lands at the New-Game party build. (Leveling shares the read-base/emit machinery + the
  real-install smoke; its in-game proof is a follow-up.)

### Added — save-item editor #5 step 4b: encrypted MAIN-block gil write + dual-write (edit vanilla saves), IN-GAME PROVEN (0.9.56)
- The editor can now write the **encrypted main AES block** of a `SavedData_ww.dat`, not just the Memoria extra
  file — so a **vanilla save with no Memoria extra is now editable**, and a Memoria save's main block is kept
  consistent with its load-authoritative extra (a dual-write).
- ★ **Layout finding (empirical, this install):** in the OLD save format the main block puts `40000_Common/gil`
  at a **fixed** offset (5235, UInt32 LE) and the 256-pair `{count,id}` item array at 5239 — byte-stable across
  saves at scenario 0→7200 and across Memoria *and* vanilla saves (the earlier "offsets shift" worry was about
  the *modern extra* format). The two no-extra slots turned out to be **vanilla saves** (hence no extra), with
  real mid-game gil/inventories editable via the main block.
- **`save_items.set_main_gil(container, block, gil)`** — decrypt → edit gil → re-encrypt one block (AES-CBC
  round-trips the untouched bytes), guarded by **`validate_main_block`** (refuses unless the 256-pair item array
  parses cleanly at the expected offset — a wrong/foreign layout is rejected, not corrupted), atomic container
  write, timestamped backup, post-write re-read confirm, dry-run default. Plus `read_main_gil`/`read_main_inventory`/
  `decode_main_block` (read a slot's gil/inventory straight from the main block — what a no-extra slot needs).
- **`save_items.set_gil_in_save(container, block, gil, mirror=True)`** — the dual-write orchestrator: writes the
  main block AND mirrors to the extra when present (vanilla → main only). CLI **`items-set-gil`** on a container
  now dual-writes (was extra-only); given an extra-save directly it still writes just that. `render_gil_dual`
  shows both legs; `_resolve_block` factored out and shared with `resolve_extra`.
- 16 new tests (synthetic encrypted containers via the save AES key); 1157 suite green. ★ **IN-GAME PROVEN
  (2026-06-12):** set a vanilla save's (slot 1/save 1, no extra) gil 43,162 → 7,777,777 in the main block — the
  whole container backed up, only block 1's ciphertext changed, other slots untouched — loaded in-game and the
  gil showed 7,777,777 with the inventory intact. The encrypted-write path the extra-only editor couldn't reach.
- Scope: gil first (the safe single-field win). Main-block **items** (the 256-pair array, structure now mapped)
  and the GUI's no-extra-slot editing are the next 4b increment; main-block **equipment** (the old-format
  9-player struct) is the deferred follow-up.

### Fixed — `deploy_campaign` wires New Game via the field-70 retarget, not the legacy field-100 hop (0.9.55)
- `deploy_campaign --apply` now wires New Game by calling `tools/retarget_newgame_warp.py` (byte-patch the shared
  field-70 opening override's `Field()` literal → the chain's entry id: New Game → field 70 → `Field(entry)`)
  instead of the old `newgame_warp.py` field-100 hop, whose injection site (a `RunSoundCode` after the InitRegion
  cluster) doesn't exist on every install — it **silently failed on the live install**, leaving New-Game wiring to
  depend on a manual retarget. `NewGame()` is stock → `fldMapNo` 70, so field 70 IS the New-Game field; a
  self-seeding verbatim chain bakes its party/beat via `[startup]`/`[party]`, so the field-100 party-setup hop isn't
  needed (memory `project-ff9-new-game-entry`). `--stock` is now a deprecated no-op; `revert_campaign.py` chains the
  retarget's revert. Surfaced by running the productionized `--apply` live (the warp step errored, the new guards
  worked). +1 regression-guard test.
- ★ **IN-GAME PROVEN (2026-06-12):** the full productionized path — `deploy_campaign --apply` (collision guard +
  CSV promotion + field-70 retarget) → relaunch → New Game — **boots straight into the Dali chain.** The
  end-to-end campaign New-Game capstone is now reproducible from one command + a relaunch.

### Added — save-item editor #5 step 4c: the Item & Equipment GUI (`apps/ff9_items.pyw`), IN-GAME PROVEN (0.9.54)
- A standalone tkinter app — the item/equip companion to the Story State console — to inspect + EDIT a save's
  gil, inventory and equipment by name, with a click. A **SEPARATE surface** (touches only `save_items`, never
  the story-state core; project-ff9-branch-lanes rule 3), modelled on `ff9_storystate.pyw`'s conventions.
- **Inspect** — pick a `SavedData_ww.dat` (enumerates its populated slots' extra files; the container read needs
  pycryptodome) or a Memoria extra-save directly; the left list shows each slot, the Inspect tab its decoded
  gil/inventory/equipment (`save_items.inspect`). Editable only for slots that have a Memoria extra file (the
  load-authoritative store); a slot with none is shown read-only (the main-block mirror is step 4b).
- **Edit** — three grouped editors (Gil / Item / Equipment), each with **Preview** (dry-run) + **Apply**
  (backup-guarded, atomic, re-read-confirmed via the proven `set_gil`/`set_item`/`set_equip`). Apply pops a
  confirm dialog showing the exact change; the character dropdown is populated from the selected slot; the slot
  dropdown is the five equip slots. After a write, the view refreshes against the just-written save.
- Registered in the launcher (`ff9_studio.pyw`, now 8 tools). A `--smoke` headless self-test exercises the full
  load → gil/item/equip preview+apply → backup path (no display, no real save). ★ Logic also verified against
  the real save's container (5 slots, 3 editable).
- ★ **IN-GAME PROVEN (2026-06-12):** the GUI renders, lists the slots, inspects gil/inventory/equipment, and a
  GUI-made equipment change showed up in-game. Also confirmed crash-safe under misuse: equipping a non-weapon
  (Ore) into the weapon slot via save edit doesn't crash — the engine's equip-load net only checks the item
  *exists* (not slot-appropriateness; that's a menu-only rule), so it loads and renders a fallback model.

### Added — `deploy_campaign` productionized: auto-promote start-state CSVs + a name-collision guard (0.9.53)
- **Name-collision guard** — `tools/deploy_campaign.py` now checks, before install, whether any `EVT_*.eb.bytes`
  or `FBG_*` scene name the chain ships collides (same name) with another live `Memoria.ini` `FolderNames` folder.
  Scene/`.eb` files resolve BY NAME, highest-folder-wins, so a same-named file in a stacked sibling folder silently
  serves the WRONG fork → torn load / black screen (the cross-worktree shadow that black-screened the Dali chain).
  Previewed in the dry-run (EVT names from the manifest), authoritatively checked at `--apply` against the built
  dist (EVT + FBG, ground truth) where it **ABORTS** (override `--allow-name-collision`); the message points at the
  fix, `import-chain --name-prefix <TAG>`. New `deploystack` helpers `check_name_collisions` / `name_collision_warning`
  / `eb_names_at` / `scene_names_at`.
- **Start-state CSV promotion** — a campaign installs into its OWN mod folder (usually NOT the highest), so its
  new-game `InitialItems.csv` (read highest-priority-wins) would be shadowed. When the campaign claims New Game,
  `deploy_campaign` now PROMOTES the entry field's `InitialItems`/`DefaultEquipment`/`ShopItems` CSVs up to the
  highest `FolderNames` folder, reversibly (single-owner, like the warp). Skip with `--no-promote-csv`, retarget with
  `--promote-csv-to <folder>`; gated off for `--no-warp` slices (a World-Hub journey shares the global bag/gear and
  seeds per-journey via scripted `give_item`). `revert_campaign.py` now restores/removes the promoted CSVs too.
- This is the manual lesson from the campaign-scale capstone session, made automatic. The generated
  `revert_campaign.py` is hardened too: it no longer `rmtree`s the live folder when the snapshot is missing,
  tolerates a vanished backup CSV, and is emitted even if CSV promotion fails partway. +13 tests.

### Added — save-item editor #5 step 4a: inventory + equipment WRITES, IN-GAME PROVEN (`items-set-item`/`items-set-equip`) (0.9.52)
- Extends the proven step-3 extra-file write path from gil to **items and equipment**, by name, same safety model.
- **`save_items.set_item(extra, item, count)`** — set an item's inventory stack count (a kit name or 0-254 id).
  `count` 0 REMOVES the stack; a new item inserts in **ascending-id position** (matching how the engine writes
  the bag); count clamps to the in-game cap (99); `NoItem` is rejected (the engine discards it on load anyway).
  The extra's `40000_Common/items` is a variable `[{id,count}]` list of live stacks.
- **`save_items.set_equip(extra, character, slot, item)`** — set one of a character's five equip slots
  (`weapon`/`head`/`wrist`/`armor`/`accessory`, + aliases `body`/`acc`). `character` = a **CharacterId** 0-11,
  the in-save name, a canonical name, or an alias (`dagger`/`salamander`); `item` = a name/id, or
  `empty`/`255`/`None` to unequip. The save's `players[].equip` is a 5-int array keyed by `info/slot_no`
  (CharacterId); the engine resets an unknown id to `NoItem` and recomputes derived defence/affinity on load, so
  only the id is written. Byte-grounded against `JsonParser.cs` (items write/load, equip write/load, player match).
- **`sjbinary.diff_paths(a, b)`** — a generic tree-diff powering the new **scoped-change** check
  (`_assert_scoped`): a variable-length edit (items add/remove) is verified to touch ONLY the allowed subtree
  (the `items` array / one player's `equip`) — the general analog of the gil write's byte-surgical gate.
- Shared `_atomic_write` (temp + `os.replace`, timestamped no-clobber backup) — `set_gil` refactored onto it too.
- CLI **`items-set-item <save> <item> <count>`** / **`items-set-equip <save> <character> <slot> <item>`** (shared
  save-target flags; dry-run unless `--apply`). Reports + renderers per write.
- 32 new tests (66 in `test_save_items` + `test_sjbinary`); 1111 suite green. ★ Build caught + fixed a real bug
  (the CLI passes `character` as a string, so a numeric CharacterId `"6"` failed — `_find_player` now treats
  digit strings as CharacterIds). A 3-lens adversarial-verify workflow (engine-fidelity / python-safety /
  integration) found 6 low-sev issues, all fixed (count-leaf guard, stale docstring, render + scoped-abort +
  post-write-confirm + backup-assertion test coverage).
- ★ **IN-GAME PROVEN (2026-06-12):** applied to slot 1/save 3 — Potion 7→99, +5 Elixir (inserted at its ascending-id
  position), Zidane weapon Dagger→Mage Masher — the main container untouched — loaded in-game and all three showed
  correctly. The editor now writes **gil + items + equipment** to a real save, schema-faithful.

### Added — save-item editor #5 step 3: the first real-save WRITE = gil (`items-set-gil`), IN-GAME PROVEN (0.9.50)
- **`save_items.set_gil(extra_path, gil, *, dry_run=True, backup=True)`** — write `40000_Common/gil` into a
  Memoria EXTRA save file (the **load-authoritative** store — it overrides the encrypted main block on load,
  memory `project-ff9-save-item-layout`). gil is a length-stable Int32 leaf (IntValue, tag 4), so this is the
  smallest possible real-save mutation: the editor's FIRST write, and the falsifiable in-game **proof** that the
  extra overrides the main block (write ONLY the extra — if the in-game gil changes to match, the extra wins).
  Extra-only by design; the main-block mirror + items/equipment are step 4. Never touches `00001_time`.
- **Two safety gates** (it writes a REAL save): (1) refuses to edit any file the SimpleJSON codec can't reproduce
  byte-for-byte (guards an unhandled leaf); (2) asserts the edit is surgical — same length, only the gil's ≤4
  contiguous value bytes move. The write is **atomic** (temp file + `os.replace`) and re-reads to **confirm** the
  new gil; a **timestamped** `.bak.<ts>` backup is taken first (never clobbers a prior one, matching
  `save.apply_story_edit`). **dry-run by default**; a no-op (gil already == requested) writes nothing even on apply.
- **`save_items.resolve_extra(...)`** — target an extra file directly, or resolve one from a `SavedData_ww.dat`
  container + 0-indexed `--slot`/`--save-no` (or `--autosave`; the two are mutually exclusive).
- **CLI `items-set-gil <save> <gil> [--slot S --save-no N | --autosave] [--apply] [--no-backup]`** — dry-run
  preview unless `--apply`. (`render_gil_write` shows the diff + the proof instructions.)
- 14 new tests (37 in `test_save_items`), incl. a CLI-glue test + an install-gated real-save **dry-run** (no
  write). A 3-lens adversarial-verify workflow (engine-fidelity / python-safety / integration) hardened it:
  atomic write, timestamped no-clobber backup, no-op short-circuit, non-Class guard, `--save-no` message fix,
  gil=0 + CLI coverage.
- ★ **IN-GAME PROVEN (2026-06-12):** applied gil `500 → 1,234,567` to the EXTRA file of slot 1/save 3 — the main
  container `SavedData_ww.dat` was byte-untouched — loaded the save and the in-game menu showed **1,234,567**.
  So **the extra overrides the encrypted main block on load = confirmed live** (the whole #5 dual-write thesis).
  ★ And **no relaunch was needed** — the extra is re-read on every save-load, so the edit→load loop is as fast as
  an F6 field reload.

### Added — battle-tuning Phase 4: the `BattlePatch.txt` emitter (enemy/attack/scene by name) (0.9.51)
- **`battle/battlepatch.py`** — author Memoria's reflection-patch `BattlePatch.txt` declaratively, reaching the
  combat data CSV can't and that raw16 `[scene]` can only reach by FORKING the scene. Three `field.toml` blocks
  map 1:1 to the engine's selector model (`DataPatchers.PatchBattles`):
  - `[[battle_patch]]` — **scene-scoped** (`scene = <id|BSC_ name>`): scene flags (`back_attack`, `preemptive`,
    `runaway`, …, → `BTL_SCENE_INFO`) + nested `[[battle_patch.enemy]]` / `.attack` / `.pattern` sub-blocks
    targeting an enemy/attack by `index =` or `name =`. Patches ANY scene **in place** (no fork, no raw16 repack).
  - `[[battle_enemy]]` / `[[battle_attack]]` — **global by-name** (`AnyEnemyByName:` / `AnyAttackByName:`): retune
    EVERY enemy/attack of that name across ALL scenes — the campaign-wide WIN over Hades Workshop ("buff every
    Goblin across the chain").
  - Reaches the **BP-only** levers with no raw16 slot: drop/steal **rate** arrays, `BonusElement`,
    `MaxDamageLimit`/`MaxMpDamageLimit`, `WinCardRate` — and the **enemy ATTACK table** (`AA_DATA`/`BTL_REF`:
    power/element/rate/`status_set`/mp/script), which the kit could not touch before. Plus the full enemy combat
    identity (stats, the 4 element affinities, the 3 status masks, defences, level/category, drop/steal ids).
- **Uniform integer emission**: `.NET Enum.Parse` accepts integer strings for every enum/flags field, so element/
  status/item values resolve through the committed `battlecsv`/`itemstats` name↔bit tables + `items.resolve` —
  **no new SE-derived table is committed** (provenance: the authored toml holds only overrides; the emitted
  `BattlePatch.txt` is build-output, never committed). Narrow engine column types (Byte/UInt16/UInt32) are
  RANGE-CHECKED offline so a value the engine would silently drop fails the lint/build instead.
- **Non-clobbering deploy** (`merge_battle_patch`): the built block is spliced into the live `BattlePatch.txt`
  under per-field `//` sentinel markers (the engine skips `//` lines), so a co-deployed battle's BGM/repoint
  lines + a stacked worktree's lines survive; idempotent + reversible (`deploy_field.py`). `build_mod` merges the
  Phase-4 lines with the per-encounter BGM `Battle:`/`Music:` block into one file.
- CLI **`battle-patch <field.toml>`** previews the emitted lines offline; `battle-patch --fields` lists the
  tunable `[PatchableField]` names by token. Offline lint wired into `validate_field`.
- ★ A 4-lens adversarial review (engine source + the structs) verified the grammar/ordering, every field
  name↔`[PatchableField]`↔token↔range, and the value-encoding sound, and caught three real bugs (fixed): the
  `status_set`/`AddStatusNo` cap was `_U16` but `StatusSetId` defines only 0-38 → an undefined id is a
  `KeyNotFoundException` crash at command-build (capped at 38); a malformed (non-table/non-list) toml block
  tracebacked instead of raising `BattlePatchError`; and the `scene` selector was unvalidated → a
  float/list/over-Int32 value silently emitted a dead `Battle:` line the engine never matches (the whole block
  no-oping). 23 tests (`test_battlepatch.py`).
- ★ **IN-GAME PROVEN (2026-06-12):** a `[[battle_patch.attack]]` on the forked EF_R007 Goblin (scene 30055,
  `FF9CustomMap-bt`) patched the enemy's **normal attack** by index — `power = 30` (now lethal) + `status_set = 16`
  — and both landed: the attack inflicted status-set 16, whose `StatusSets.csv` bundle (`AutoLife`, `Vanish`,
  `Regen`, `Haste`, `Protect`, …) showed up exactly as authored (hit party members revived at 1 HP from AutoLife
  and went invisible from Vanish). So the **enemy `AA_DATA` attack lever** (untouchable by the kit before) works
  by name via BattlePatch. (Lesson for authors: `status_set` is a `StatusSetId` row — 16 = the Dispel bundle,
  Poison = 20; pick the row you mean.)
- ★ **FULLY PROVEN (2026-06-12):** a follow-up confirmed every Phase-4 channel in one fight — `AnyEnemyByName:
  Goblin` (the Goblin started **Poisoned** via `initial_status`; since "Goblin" is a real FF9 enemy, that one
  block also buffs real Goblin battles — the campaign-wide win over Hades Workshop), `AnyAttackByName: Goblin
  Punch` (neutered to **power 1**), the `back_attack` **scene flag** (party started reversed), and a guaranteed
  `drop_rates` **Elixir**. Every selector + the BP-only rate arrays + scene flags are now in-game proven.

### Fixed — `deploy_field` DictionaryPatch revert is now surgical (was clobbering co-deployed registrations)
- `deploy_field`'s generated revert restored the **whole** pre-deploy `DictionaryPatch.txt` snapshot, so when a
  field and a battle scene share one mod folder (the battle-tuning loop: `deploy_battle` registers
  `BattleScene <id>` into `FF9CustomMap-bt`, then `deploy_field` deploys the trigger field there), the field
  deploy's pre-revert wiped the `BattleScene` line → the battle **black-screened** on entry. The revert now drops
  only the field's own `FieldScene <id>` line from the *current* live file and restores that id's prior line from
  the backup, preserving every co-deployed line. (Same wholesale-snapshot hazard the World Hub note flagged.)

### Added — World Hub: a playable journey selector (choice `warp` action + `[player] model=`), IN-GAME PROVEN (0.9.48)
- The **World Hub** is a playable field that lets the player pick which **journey** (a complete arc = one or
  more chained campaign slices) to play, then warps them in — NOT a worldmap (no engine fork), just a field +
  a dialogue-choice menu + warps. overworld's lane (memory `project-ff9-world-hub`). Reuses the existing
  `[[npc]]`+`[[choice]]` pipeline + two small general additions:
  - **The choice `warp` action** (`content/event.warp` + `choice.option_body`): a `[[choice.options]]` row can
    `warp = <field id>` (+ optional `set_scenario = N`). Grounded finding: a `Field` op transitions directly
    from a **tag-3 talk handler** (14+ shipping fields do — the Dali innkeeper, the airship, Gargan Roo),
    unlike a bare `Field` in Main_Init. The warp = `RunSoundCode(265,65535)` + `Field`; `warp` is last in the
    option body (it transitions away). Byte-identical without it.
  - **`[player] model=`** (`npc.set_player_model` + build wiring): re-skin a synthesized field's player avatar
    to any model — the hub's stock Moogle (**220** `GEO_NPC_F0_MOG`, the save moogle), keeping
    `DefinePlayerCharacter`. The field-side twin of `--swap-player`; free-roam-only.
- `examples/world_hub/` — a self-contained 3-field scaffold (hub 4500 + journeys 4501/4502). `validate()` flags
  a bad `warp`/`set_scenario`. 9 tests (`test_world_hub`).
- ★ **IN-GAME PROVEN (2026-06-12):** F6→Warp 4500 — walk as the moogle, talk → the journey menu shows, pick →
  warp into the destination (custom arrival dialogue), "Stay here" closes. Playtest fixes: stock moogle = 220
  (not 199, a bat-winged variant); the text block must avoid **1073** (shadowed by the higher `FF9CustomMap`
  folder). ★ Deploy gotcha (CLAUDE.md §3): `deploy_field`'s wholesale-snapshot revert RE-CLOBBERS a multi-field
  text block back to the first-deployed value — verify the DictionaryPatch textids, or deploy as a campaign.
- **Deferred follow-up now UNBLOCKED:** New-Game→hub uses master's new `tools/retarget_newgame_warp.py 4500`
  (point the field-70 override at the hub). The `[[journey]]` sugar + generator ("hardcoded MVP → generator")
  remains the next step.

### Added — campaign-scale New-Game capstone: boot directly into a forked verbatim CHAIN (0.9.47)
- **`tools/retarget_newgame_warp.py <id>`** — point the field-70 New-Game override at any custom field id (the
  chain's entry), byte-patching its `Field()` literal in place via `content.verbatim.remap_fields`. Composes with
  `skip_opening_fmv.py`. So New Game → a forked `import-chain --verbatim` slice that runs its real story.
- **`import-chain --name-prefix <TAG>`** — namespace every member's deployed FBG/EVT name (e.g. `DC_DL_INN`) so two
  campaigns/worktrees that fork the SAME source field don't collide on the by-name, highest-`FolderNames`-folder-wins
  scene/`.eb` resolution (a shadow that silently serves the WRONG fork → black screen). Byte-identical when unused.
  `member_name`/`assign_ids`/`write_campaign` gain a `name_prefix`; CLI `--name-prefix`. (75 campaign tests pass.)
- ★ IN-GAME PROVEN (Dali): New Game → wake up in the Dali inn → the slice plays its REAL logic (party splits to
  explore town — faithful) → Garnet rejoins at scenario 2640. A forked chain advancing real story state from a fresh
  game. Lessons: seed `[startup]` to the donor's OWN beat (Dali = 2600, not a notch past it); deploy the chain to
  `-sf` but promote the entry's start-state CSVs UP to the highest folder. See memory `project-ff9-new-game-entry`.

### Added — starting-state capstone: a New Game that boots into a custom field with the right beat/party/bag/gear (0.9.43)
- `examples/capstone/` — a self-contained entry `field.toml` that composes all FOUR new-game starting-state channels
  on ONE field: `[startup]` (ScenarioCounter + a story bit) + `[party]` (add Steiner/Freya) → the field `.eb`
  (prepended to Main_Init at synthesis); `[start_inventory]` → `Data/Items/InitialItems.csv` + `[[equipment]]` →
  `Data/Characters/DefaultEquipment.csv` (emitted at the mod-write stage). `build`/`deploy_field` fire all four
  automatically; the CSVs are read **only at a true New Game**. ★ IN-GAME PROVEN end-to-end — New Game → field 4003
  as **Zidane/Steiner/Freya**, Steiner wearing his Excalibur+Genji delta, the custom bag, at ScenarioCounter 2600.
- The entry is the engine-independent field-70 override (`Field(4003)`, FMV-skipped) — no DLL.
- ★ Deploy to **id 4003 in the highest mod folder** (`--id 4003 --mod-folder FF9CustomMap`): the override warps
  `Field(4003)` and `InitialItems.csv` is highest-priority-wins (a lower folder's bag would shadow it silently).
- `tests/test_capstone.py` (5 tests): the four-channel emission + two design invariants — `[party]` adds the others,
  not Zidane (the new-game base is Zidane-slot-0, and added members join wearing their `[[equipment]]` gear); the
  `[startup]` flag stays in the custom safe band.
- No kit code changed — the four channels already existed; this is the **composition + the proof** (story_flags'
  composition lane). Engine facts verified by a 3-lens adversarial review against Memoria source.

### Added — deploy-time shadow guard for the highest-wins `InitialItems.csv` (0.9.43)
- A cross-branch handoff (story_flags' CSV-shadow lane): `deploystack` warned on a `.mes` text-block shadow but
  not on an `InitialItems.csv` shadow. The starting bag is read **highest-priority-wins** (a whole-file win, not
  a per-id merge like `ShopItems`/`DefaultEquipment`), so deploying it into a folder that a **higher**-priority
  `FolderNames` folder also ships **silently drops it** — no error, the wrong bag loads.
- New `deploystack.check_csv_shadow` (mirrors `check_text_block_shadow`): given the mod stack, it flags a
  highest-wins CSV that a higher folder shadows, with a concrete fix (deploy to the highest folder / remove the
  higher copy). `HIGHEST_WINS_CSVS` lists the one file that needs it (`InitialItems.csv`); the merged CSVs don't.
  `tools/deploy_field.py` runs it for each highest-wins CSV it actually shipped, after the text-shadow guard
  (and never breaks a deploy on an odd `Memoria.ini`). 5 tests. kit 0.9.43.

### Added — `[[shop]]` — author a custom shop: inventory + opener (0.9.43)
- A new `[[shop]]` block defines a shop the player can buy from — its **inventory** plus an **opener** — entirely
  on stock Memoria (no DLL). The author-side complement to the `fork-report` Items/Treasure axis.
- **Inventory** → a `StreamingAssets/Data/Items/ShopItems.csv` delta (`content/shop.py`
  `render_shop_items`/`write_shop_items`), emitted once at the mod-write stage (`build._emit_shops`, alongside
  the new-game CSVs). The engine **merges** shops by id over the base (which supplies shops 0-31), so the delta
  lists only the custom shops; ids are `>= 32` (a `< 32` clash overrides a vanilla shop — warned) and `<= 255`
  (the `Menu` sub-id byte). Item names/ids resolved via the kit's item table; duplicates within a shop collapse;
  `NoItem` (255) dropped. Shops collect from **every** built field (not entry-restricted — they merge by id);
  a duplicate id across the mod is warned (last-wins).
- **Opener** → `Menu(2, id)` (`OpenShopMenu`; the `Menu(4, 0)` save-point family). Two shapes:
  - **`[[npc]] opens_shop = N`** — talking to a shopkeeper NPC opens shop `N` (a vanilla 0-31 shop too); its
    `dialogue` is the greeting shown first. Reuses `content/npc.py`'s `speak_body` slot (`shop_speak_body`).
  - **`[[shop]] zone = [...]`** — a standalone press-to-interact region opens the shop (the save-point region
    shape: `DisableMove; Menu(2, id); EnableMove`), `bubble` toggles the "!" prompt. `shop_region`/`inject_shop_regions`.
- `validate()` checks the shop id type/range, a non-empty resolvable `sells`, the zone shape, and `opens_shop`
  range. `_emit_shops` warns on a vanilla-id override, a duplicate id, and an `opens_shop` pointing at an
  undefined custom shop. `ModLayout.shop_items_csv` is the new mod path.
- Byte-identical when no `[[shop]]` is present (no region injected, no CSV written — the base shop file is not
  clobbered). New module `content/shop.py`; touches `build.py` (inject + emit + validate) + `config.py`. 25 tests
  (`tests/test_shop.py`); clear of story_flags' compose lane + overworld's forkreport lane. kit 0.9.43.
- ★ A 3-lens adversarial-review workflow (engine-fidelity / Python-correctness / integration-at-scale) caught
  defects the first pass missed, all fixed: **(blocker)** `tools/deploy_field.py` didn't ship the new
  `ShopItems.csv` (the same selective-copy gap #3 had) — added to its reversible CSV-deploy loop, so the
  edit→deploy→F6 loop actually carries shop stock; **(blocker)** an author `comment` was emitted verbatim as CSV
  column 0, so a `;` corrupted the row (mis-parsed the Id) and a leading `#` made the engine skip the whole line
  (the shop silently never loaded) — `shop.safe_comment` neutralizes `;`/newline/leading-`#` (the label is
  cosmetic); **(bug)** an NPC with both a `[[choice]]` and `opens_shop` silently dropped the shop (the talk-body
  `elif`) — now a `validate()` error; **(bug)** a `sells` that resolves entirely to `NoItem` passed validate then
  built an empty shop — now caught post-resolution; **(smell)** `_emit_shops` made dup-id and vanilla-override
  mutually exclusive (`if/elif`) and could crash on a malformed id (build skips `validate`) — both now independent,
  and a bad id is skipped-with-warning not a crash; **(smell)** a verbatim fork silently dropped a synthesized
  shop opener — now warned (the inventory CSV still ships). The cross-worktree same-id merge collision is noted
  in FORMAT.md.
- ★ **IN-GAME PROVEN (2026-06-12):** a test field (slot 4003) with both openers — a shopkeeper NPC (`opens_shop`)
  and a standalone `zone` counter — opens shop 40 / shop 41 with their authored inventories, and a real purchase
  (a Mage Masher) deducted gil + added the item. The deploy shipped `ShopItems.csv` (the gap fix confirmed).

### Added — `fork-report --explain`: decode a field's NPC interactions into readable English (0.9.44)
- `fork-report <field> --explain` traces every carried NPC's **tag-3 talk routine** into plain steps —
  real `.mes` dialogue + items/gil/menus + the funcs it `RunScript`s — and **inlines** those funcs (the
  Main_Init shared logic `uid 0`, the player sequences `uid 250`/a player entry, a sibling object) so a
  multi-NPC sidequest reads as one quest. It also shows **why** a render-only NPC is render-only: you SEE
  that its talk routine *is* the field's own quest logic (shared/player/economy), not a graftable gesture
  → "fork with `--verbatim` to keep it interactive." Validated on the Daguerreo 2F (field 2803) positive
  control — the debate, the librarian's book quest, the old man's **Excalibur** trade, all legible.
- `forkreport.explain_eb` is **pure** (`.eb`-only structure; a parsed `.mes` enriches the windows with real
  text, else `<line N>` placeholders) → offline-testable; `forkreport.explain` is the id→bytes loader over
  it; `format_explain` renders the transcript (ASCII chrome). Read-only — reuses the disassembler + the
  item-pool decode + `dialogue.parse_mes`; no carry/graft logic of its own (analysis lane). 7 tests.

### Closed (proven infeasible) — #14 talk-handler graft closure
- The carry-fidelity gap "graft a render-only NPC's talk routine into a non-verbatim fork" is **infeasible**.
  A **verified census of all 675 forkable fields under maximal grafting** (`graft_player_funcs` + `carry_text`
  + `graft_seq_helpers` + `graft_savepoint`, with the self-dependency fixpoint modelled) found **55 NPCs across
  36 fields that render faithfully but lose their tag-3 talk handler, and 0 of them are blocked only by a
  graftable gesture**: every one depends on the field's own logic — Main_Init shared dialogue branches (40),
  exotic non-gesture player sequences (15), uncarried co-actors (4), an unsafe background script (1), a party
  op (1). (A further **39 objects in 20 fields are refused outright** — their tag-1 LOOP itself is un-graftable,
  an even harder case.) The census agrees with `fork-report`'s interaction axis (field 2803 = 3 render-only).
  In FF9 an NPC's *interactive* talk handler **is** the field's transaction logic (dialogue + rewards + menus +
  walkmesh-triangle toggles the engine even hardcodes per-field), inseparable from its text/economy/geometry.
  `--verbatim` already carries all of it byte-for-byte, so the standing answer for "keep these NPCs interactive"
  is `--verbatim`. `--explain` is the shipped takeaway: read the quest, decide per-field. (Memory
  `project-ff9-fork-fidelity-worklist`.)

### Fixed — `import <id>` now means the FIELD ID, not a `map<NNN>` folder substring (0.9.42)
- `import <field>` / `import-chain` resolved a token by **FBG-folder substring**, while `fork-report` /
  `list-fields` / `find-rooms` resolve a digit as a **field id** — so they targeted *different* fields for the
  same number. `import 100` forked the Dali field whose folder contains `map100`; `fork-report 100` analyzes
  field id 100 (Alexandria). Field ids and the folder `map<NNN>` numbers are **unrelated schemes** (0 of 676
  coincide), so a numeric token diverged for **every** field — 79 silently forked the wrong field, 38 errored
  ambiguously, 559 just failed.
- Fix: `extract.resolve_field` is now **digit-first** — a pure-digit token resolves via `ID_TO_FBG[int]` (parity
  with `fork-report`); non-digit tokens keep the FBG/mapid-substring behavior (so `map100` / `vgdl_map100` still
  match a folder by its map number). This transitively fixes an **internal** mismatch too: `import 100 --verbatim`
  used to ship the Dali field's `.eb` (folder-keyed) with Alexandria's `.mes` (the dialogue path is already
  digit-first) — now both halves are the same field. Surfaced + grounded by a 2-agent workflow (full caller audit:
  the only digit token entering `resolve_field` is the user's `import` arg; campaign/chain seeds were already
  digit-first; issue #2 "multi-id folders → wrong event" confirmed non-existent — the table is strictly 1:1).
  4 tests (3 offline + an install-gated consistency check). One minor remainder noted: `import` still doesn't
  match bare event-name tokens (`EVT_…`) the way `fork-report` does — a possible future polish. kit 0.9.42.

### Added — `--swap-player --neutralize-gestures`: stand cleanly through a cutscene (0.9.41)
- `import <field> --swap-player <char> --neutralize-gestures` (also on `import-chain`) makes a swapped
  character STAND/idle cleanly through a cutscene field instead of T-posing on the donor rig's scripted
  gestures. On every swap-target player entry it rewrites each `RunAnimation` (0x40) clip — and any LOOP
  movement re-set (`SetStandAnimation`/…) — to the swapped rig's OWN idle clip, leaving `WaitAnimation`/
  `Wait`/`SetAnimationFlags` intact so timing is preserved. (The character won't *emote* — for story fidelity
  use a verbatim fork at the right beat. Requires `--swap-player`.)
- **Engine-grounded** (a workflow read Memoria's `DoEventCode`/`ProcessAnime`/`AnimationFactory`): RunAnimation
  is NAME-keyed via one global clip dict, so a foreign donor gesture clip loads a foreign-skeleton clip = the
  glitch; the swapped rig's idle is already loaded (by `--swap-player`'s SetStandAnimation), so substituting it
  gives a real frame count and the paired `WaitAnimation` completes (no hang). NOP-ing was rejected (it orphans
  the `WaitAnimation`). 0xBD (RunAnimationEx) is left untouched (never targets the player in 676 fields; its clip
  arg sits behind an object selector). `playerswap.neutralize_gestures` (reuses the proven `_put_arg` patch);
  `apply_player_swap(neutralize=)`; `write_campaign(neutralize_gestures=)`.
- **A 2-lens adversarial review caught a blocker** (both lenses): `apply_player_swap` ran swap then neutralize
  as two passes, each re-deriving `swap_targets()` — but `swap_player` mutates the SetModel id those target on,
  so on Zidane-present multi-PC fields (87/668 = 13%) the second pass DRIFTED to a co-actor, neutralizing the
  wrong entry AND corrupting a bystander. Fixed by resolving the target set ONCE on the original bytes and
  reusing it (the `entry=` override now accepts a list), plus a defensive model-match guard in
  `neutralize_gestures` (only rewrite an entry actually swapped to `char`). Field 500 (Cargo Ship) regression
  test. The review also fixed a false "will glitch" WARN in the chain summary (now reports NEUTRALIZED). 6 tests
  (3 offline + a field-500 + an install-gated). kit 0.9.41.

### Added — `list-fields --players` / `--non-zidane`: who you play as in each field (0.9.39)
- `ff9mapkit list-fields --players` enriches the field list with **who you control** in each field, and
  `--non-zidane` (implies `--players`) narrows to fields where you play as **someone other than Zidane** —
  the verbatim-fork donors — so they're discoverable without forking each one. e.g. `list-fields alxt
  --players` shows field 100 = `Vivi *`, and the live `--non-zidane` sweep finds **89 of 675** — split in the
  footer into **53 playable-cast donors** (Steiner 19, Garnet 18, Vivi 10, Eiko 4, Freya/Amarant 1) and 36
  cutscene-driver `GEO_SUB` "players" (so you can tell a real swap donor from a scripted actor).
- **Id-centric** (a player is a property of the `.eb`), so an alternate event script on a shared background
  is its **own** row — revealing the non-Zidane variants folder-centric listing hides (the Steiner `_b`
  scripts 2050–2053 surface next to their Zidane `_a` twins on the same map). The `non_zidane` flag uses the
  in-game-proven, stricter definition (non-Zidane only when **no** Zidane is among the PCs), so it excludes
  Zidane-present multi-PC escape scenes where you actually control Zidane — the honest "you really play as
  someone else" set (which is why 91 < the census's looser 178).
- New `forkreport.field_players` (sweeps `ID_TO_FBG`, reuses `analyze_eb`'s player resolution — one
  `EventBundle`, eb-only) + `player_label` + the `FieldPlayer` dataclass (with a `playable` flag); the CLI
  gained the two flags (`_list_fields_with_players`). Plain `list-fields` (no flags) is unchanged + fast. A
  full no-pattern sweep is ~30s (a pattern narrows it). Read-only; `forkreport.py`/`cli.py` only — clear of
  the build + graft lanes.
- A 2-lens adversarial review caught a real classification bug (both lenses): **`eventscan.ZIDANE_MODELS` was
  missing the ZDD disguise (532) + the ZDN LOD forms (203/432/668-670)**, so Zidane fields leaked into the
  non-Zidane lists (field 401 literally listed as `Zidane(ZDD) *`). Fixed at the root (`ZIDANE_MODELS` now
  covers every `GEO_MAIN_*_ZDN`/`_ZDD` form — which also corrects `find-rooms` + the fork-report Player axis);
  the count drops 91→89. Also hardened `player_label` (keep the non-Zidane flag when the binder name is blank)
  and surfaced the playable-vs-cutscene-driver split. 7 tests (4 pure + 3 install-gated). kit 0.9.39.

### Added — `[start_inventory]` / `[[equipment]]`: new-game starting bag & default gear (0.9.40)
Author what the player **starts a New Game with** — the starting inventory and each character's default
equipment — as **engine-independent CSV deltas** (stock Memoria). This is the item/equip half of the
New-Game-into-a-fork capstone; it composes with the scenario/party half (`[startup]`/`[party]`) and the
seamless New-Game entry (`nop_cinematics`).

```toml
[start_inventory]                              # the FULL starting bag (REPLACES the base; highest-priority-wins)
items = [["Potion", 20], ["Phoenix Down", 5], ["Tent", 3]]

[[equipment]]                                  # a character's starting loadout (partial: only the chars you list)
character = "steiner"
weapon = "Excalibur"
armor  = "Genji Armor"                         # omitted slots (head/wrist/accessory) start empty
```

- `content/inventory.py` renders the FULL `Data/Items/InitialItems.csv` (the engine reads it
  **highest-priority-wins**, so it replaces the base bag; counts clamp to 99, dup ids sum) and
  `content/equipment.py` renders a PARTIAL `Data/Characters/DefaultEquipment.csv` (the engine **merges** it
  low→high over the base's 15 sets, so only the named characters change; each row is a complete loadout).
  Character name→`EquipmentSetId` is a names/ids-only table (provenance-clean, like `_itemdb`).
- Emitted at the **mod-write stage** (`build_mod`, alongside DictionaryPatch/BattlePatch via `ModLayout`),
  not into any `.eb` — these are mod-global files. They live on the **entry field's** `field.toml` only; the
  build **warns** if a block lands on a non-entry field (precise for a campaign via the entry member) and
  surfaces the `InitialItems` highest-wins/shadow caveat. New-game-only scope (read once at new-game init).
- `validate()` resolves every item + character name. New `ModLayout.initial_items_csv` / `default_equipment_csv`.
- **Provenance:** the writers are deterministic from the author's `field.toml` + the committed name tables —
  no game stat data is read or committed. Adversarially reviewed (3 lenses: engine-format / Python / provenance)
  — the partial `DefaultEquipment.csv` was confirmed to merge with the base (no "must define 15 sets" boot
  crash). 15 tests (`test_startstate.py` pure renderers + `test_build.py` emit/validate/lint).
- The dev loop ships them: `deploy_campaign.py` already copied the whole mod (wholesale); `deploy_field.py` now
  also deploys the two CSVs **reversibly** (it previously copied only the field's `.eb`/scene/`.mes`), so a
  single-field test reflects them. Test: deploy → **relaunch** (the bag is read at New-Game init, not via F6
  reload) → **New Game** → check the items/equipment menu (the bag/gear is set before you warp to the field).

### Added — `remove_item`: the symmetric take-item reward lever (0.9.36)
`[[event]]` and `[[choice]]` rewards could `give_item` but not take one back. New `remove_item = [item, count]`
(id or name) emits `RemoveItem` (`0x49`) — pair it with `give_item` for a **trade**, or use it alone to
**consume a quest item**. (Giving equipment by name and the "Received X" box already worked for any item,
incl. weapons/armor — this closes the one missing half.)

```toml
[[event]]                       # a trade: take a Dagger, give a Potion
zone = [[300,-400],[700,-400],[700,-800],[300,-800]]
remove_item = ["Dagger", 1]
give_item   = ["Potion", 1]
message     = "Traded!"
```

- New `opcodes.remove_item` (0x49) + `event.take_item` (name-resolved, like `give_item`); wired symmetrically
  into the event + choice-option builders and `validate()` (a sole `remove_item` is a valid action; an unknown
  name is caught). The engine clamps removal to what's held, so over-removing is safe.
- 4 tests across `test_content` / `test_choice` / `test_build` (a trade event with both ops, a trade choice
  option, a remove-only event validates + builds with `0x49`, and a bad name is rejected).

### Added — `find-rooms`: sweep all fields for the best swap/demo test rooms
- A new `ff9mapkit find-rooms` subcommand scans every forkable field and ranks the best **swap/demo test
  rooms** — a place to walk as a `--swap-player` character or stage a visual test where the model's detail is
  visible. The proven anchor field 1200 `ac_rst_x` ranks #1; the top results match the hand-verified clean
  rooms (1911 Treno house, 310 Ice Cavern cafe, 3055 BMV weapon shop, …).
- A "good room" is the AND of: single-PC + swap-clean + a PLAYABLE controller + a STATIC roster + a **close
  3/4 single-screen camera**. The camera test is the subtle part: **FOV alone is NOT a detail proxy** — FF9's
  projection is orthographic-like (k≈0.93, the camera-math invariant), so a sub-10° "FOV" is a far *telephoto*
  (model is a speck), not a close shot. So the filter ANDs a bounded FOV (10–45°) **with** a 3/4 pitch band
  (6–48°) **with** the camera's visible `range_height` (≤420; the key signal, now exposed from
  `field_camera_info`) **with** a `_CS_` cutscene-name guard. Scrolling is a rank demerit, not a disqualifier.
- Two-phase for speed (~45s over ~675 fields): a cheap `.eb`-only prefilter (one `EventBundle`, no per-field
  scene load) keeps single-PC + swap-clean + static-roster + playable fields, then the expensive per-field
  camera read runs ONLY on those ~75 survivors. `--limit` / `--max-fov`; `find_rooms(ids=…)` scopes the sweep.
- New in `forkreport.py`: `find_rooms` / `room_score` / `RoomSweep` / `format_room_table` / `_is_real_fbg` +
  the `ROOM_*` calibration constants. `extract.field_camera_info` now returns `range_w`/`range_h`;
  `ForkReport` gains `cam_range_h`. The `_camera_line` Camera axis gained a `distant` label for sub-10° FOV
  (a telephoto, not "close" — corrects the just-shipped axis). Grounded in a 676-field calibration sweep and
  hardened by a 3-lens adversarial review (caught the missing low-pitch bound, the loose max-pitch, the
  vehicle-player donor, and story-event leakage — all fixed). Read-only; `forkreport.py`/`extract.py`/`cli.py`
  only. 12 tests (8 pure + 2 install-gated integration). kit 0.9.37.

### Added — `fork-report` Camera axis: the lens a fork plays through (close / medium / wide)
- A new **`Camera`** line previews how the field is framed: a **`close` / `medium` / `wide`** feel bucketed by
  horizontal FOV, plus the raw `pitch`/`FOV`, and notes when the field is `scrolling` or has multiple cameras.
  E.g. field 1200 `ac_rst_x` = `close (FOV 29.5 deg, pitch 28.8 deg); 2 cameras`, the Hangar 1357 =
  `wide (FOV 61.3 deg, pitch 0 deg)` (the "super far away" view), Vivi's street 100 =
  `close (FOV 17.2 deg, pitch 38.5 deg); scrolling` (a tight lens that pans).
- Pairs with the Player swap-friendliness tag: **`swap-clean` + `close`** = a good `--swap-player` / demo test
  room (the detail is actually visible), vs a `wide` establishing shot where models are tiny.
- The camera lives in the scene `.bgs` (not the `.eb`), so it needs the install: a new read-only
  `extract.field_camera_info` (pitch/FOV/scrolling/count — no walkmesh/atlas extraction) populates the report in
  `forkreport.analyze()`. The pure `.eb`-only `analyze_eb` is untouched (no camera → the line is omitted), so the
  fixture reports stay byte-identical. Reuses the existing `cam.pitch_deg` / `cam.decompose` (FOV) math; no new
  camera code. 4 tests (`tests/test_forkreport.py`, incl. an install-gated render). kit 0.9.34.

### Added — `fork-report` Player axis: swap-friendliness tag (is this a good `--swap-player` target?)
- The Player line now ends with a swap-friendliness tag: **`swap-clean`** (a free-roam field — `--swap-player`
  works cleanly) or **`swap: N gesture(s) glitch`** (a cutscene field whose player plays N scripted gestures
  that would glitch on a swapped rig, since only movement clips are swapped). It's the *before-you-fork* preview
  of the existing swap-time `WARN`, useful for browsing/choosing a swap or demo target (e.g. field 1200
  `ac_rst_x` = `swap-clean`, a close 3/4 camera; the Vivi field 100 = `swap: 15 gesture(s) glitch`). Reuses
  `playerswap.scripted_gesture_ops` (the same controlled-leader-targeted gesture count the swap + CLI warn use)
  — `.eb`-only, no new scanner. 1 test (`tests/test_forkreport.py`). kit 0.9.33.

### Added — item stat/effect catalog: the Info Hub now shows what an item DOES (0.9.35)
`ff9mapkit items` and the Info Hub item detail were names-only; they now surface **weapon power + element**,
**armor defence**, **equip stat bonuses + elemental affinity**, the **consumable use-effect**, **price**,
**type/slot**, **who can equip it**, and the **abilities it teaches**.

```
$ ff9mapkit items -f excalibur
   28  Excalibur         weapon - Atk 77 Holy, 19000 gil
   30  ExcaliburII       weapon - Atk 108 Holy, 39000 gil
```

- New `itemstats.py` JOINS the five FF9 item-data CSVs (`Items` + `Weapons`/`Armors`/`Stats`/`ItemEffects`,
  keyed by the catalog's FKs) into one `ItemStat` per id, with `summary()` (one-line) + `facts()` (the detail
  pane). Element/weapon-category/type bitmasks decode to names (`Fire`/`Holy`, `short-range/throw`, …).
- **Provenance:** item STATS are game DATA, so — unlike the committed names table `_itemdb.py` — they are
  **never committed**. `itemstats` reads them **live from YOUR install** (`<install>/StreamingAssets/Data/Items/
  *.csv` — Memoria's editable item tables) and caches in-memory; the repo/wheel ship nothing. Column layout is
  read from each CSV's `#`-legend (not hard-coded indices), so it survives Memoria's option-driven column
  toggles. If the install isn't reachable, every accessor returns `None`/`[]` and the Info Hub degrades to
  id+name (it still works offline). See docs/PROVENANCE.md.
- Wired into `infohub.py` (browse summary + detail facts) and the `items` CLI; both degrade gracefully.
- Consumable use-effects decode the `BattleStatus` mask (a cure/revive item like Phoenix Down has Power 0 and
  acts entirely via the status set), so it shows `effect status Death` rather than a misleading `use pow 0`;
  an all-zero effect row (a stat accessory with a dummy EffectId) shows no use-effect line at all.
- 11 tests (`tests/test_itemstats.py`): pure decoders/parser/formatters + graceful-degradation run offline;
  the real-value join (Dagger Atk 12, Excalibur Atk 77 Holy, Iron Helm M.Def 7, Potion/Phoenix-Down effects) is
  install-gated. Provenance + engine-fidelity + Python were adversarially reviewed (3 lenses). This is the
  read-only foundation the shop/reward/save-editor item pillars build on.

### Added — seamless New-Game entry: `eb.edit.nop_cinematics` + `tools/skip_opening_fmv.py` (0.9.38)
A spin-off from verifying how a New Game reaches a custom field (memory `project-ff9-new-game-entry`): the whole
path is **engine-independent** (the only custom DLL is the F6 menu; `NewGame()` is stock `fldMapNo = 70`, and a
mod **overrides field 70** `EVT_ALEX1_TS_OPENING` to `Field(4003)` after its opening movie). This adds the lever
to make that entry **seamless**, all stock:
- **`eb.edit.nop_cinematics(data, *, entry_index=0, func_tag=0, before_op=0x2B)`** — NOPs every `Cinematic`
  (`0x28`, FMV-playback) op in a function up to the first `Field()` warp, **length-preserving** (in-place `0x00`
  NOPs = engine-confirmed "do nothing", `DoEventCode` case `NOP`; no offsets shift, no jumps to fix). Returns
  `(new_data, n_nopped)`; byte-identical when there are no cinematics.
- **`tools/skip_opening_fmv.py`** — a dev-loop driver: auto-finds the live opening override across all language
  folders (or takes explicit paths), backs each up (per-language backup name — fixed a same-second collision),
  strips the pre-warp cinematics, `--dry-run` supported. Provenance-safe (operates on local/deployed `.eb`s; the
  repo ships no SE bytes). In-game: drop the 2 cinematics in field 70's override → New Game lands in the target
  field instantly, no FMV, no DLL, no `SkipIntros` (that's boot-only).
- 1 test (`tests/test_eb.py::test_nop_cinematics_strips_only_pre_warp_fmv`): pins that only the pre-warp cinematic
  is NOPed, the warp + post-warp cinematics survive, and the `.eb` still round-trips. *(In-game verification of
  the instant New Game is the human step.)*

### Added — `fork-report` Items / Treasure axis: preview the treasure, gil & shops a fork reproduces (0.9.32)
The item-side companion to the Player / Roster / Interaction / Dialogue / Party axes — what a fork does to your
**inventory**. Read-only; reuses the kit's disassembler (no new scanner of its own).

- `forkreport.scan_item_ops` decodes the item ops a field's `.eb` runs: `AddItem` (`0x48`), `AddGil` (`0xCE`),
  and shop opens `Menu(2, id)` (`0x75`). A `--verbatim` fork RUNS these byte-identically; a plain/synthesize
  fork has **no item scanner**, so it **DROPS** every treasure + shop. A shop's stock is also parasitic on the
  base `ShopItems.csv` (a fork can't change the inventory) — the line says so.
- Item ids are classified by the engine's pool rule (`ff9item.FF9Item_Add_Generic`, `id % 1000`): 0-255 regular
  (named via `items`), 256-511 key item, 512-611 Tetra Master card, `>= 612` **inert** (engine no-op → excluded).
  A plain 0-255 regular id is named; higher pools are classified but unnamed.
- Counts are **per-grant maxes, not summed** across the field's mutually-exclusive story branches (else an Ether
  granted on two paths would read as "x2"); a gil literal above the 9,999,999 cap is suppressed as a scripted
  sentinel ("gil (scripted)"). Computed-id grants/shops surface as "computed-id item(s)" / "opens a story-gated
  shop" (the latter recovers 42 gated-shop fields incl. Dali inn 351 / Ice Cavern 300).
- Validated by a 3-lens adversarial-review workflow (engine-fidelity / Python-correctness / scale over all 676
  real fields): the decode is engine-exact, zero false positives; it caught a latent under-report (computed-id-only
  grants/shops rendered nothing) that this lands fixed. 12 tests (`tests/test_forkreport.py`). `forkreport.py` only.
- Recon context: the engine's full item/equipment data model is **CSV-moddable on stock Memoria**
  (`StreamingAssets/Data/Items/*.csv`, no DLL rebuild) — see memory `project-ff9-items-equipment` + docs/FORK_REPORT.

### Added — `--swap-player` accepts ANY model (the field-side bridge to custom characters)
- `--swap-player` (single `import` and `import-chain`) now takes a playable name OR **any registered model** —
  a `GEO_..` name or a numeric id (a moogle `199`, `GEO_NPC_F0_BMG`, …; `ff9mapkit models`). A playable uses
  its proven home-field rig table; any other model resolves its 5 movement clips (stand/walk/run/turn) via the
  kit's model→animation join (`catalog.npc_anims`), so you can **walk as a moogle / an NPC / a creature**. A
  model with no movement (a static monster) raises cleanly; an arbitrary model keeps the field's eye-height
  (cosmetic dialog anchor). This is the **field-side bridge to custom characters** — a registered custom model
  would be driven by exactly this path (`SetModel` + movement clips), no DLL. Smoke-verified (Vivi field → a
  moogle). 2 tests. ★ Cross-rig GESTURE remap was probed and is **infeasible** — a cutscene field's player
  gestures are scene-specific (Vivi field 100's 15 = KOKE/RECEIVE/GIVE/KISS_ME/HIZA, **0** with a Steiner
  equivalent), not a shared vocabulary, so the cutscene-glitch caveat is fundamental and the `WARN` stays the
  right handling. `playerswap.resolve_char` (general) + `cli.py`; read-only join reuse. kit 0.9.30.

### Added — `[party]` block: add/remove party members at field load (0.9.31)
The authoring complement to overworld's `import --swap-player` — where that changes who you **walk as**,
`[party]` changes who's **in the party** (the menu + battle roster). Field *control* and party *state* are
decoupled (memory `project-ff9-pc-party-system`); this is the declarative half flagged for the story_flags
lane.

```toml
[party]
add    = ["steiner", "vivi"]   # add existing playable characters (B_PARTYADD, the real JOIN form)
remove = ["zidane"]            # optional: RemoveParty
```

- New `content/party.py`: `add_member` emits the **in-game-proven** probe bytes `05 C5 93 7D <id> 00 6D 2C
  7F` (op `0x6D` `B_PARTYADD` — the kit had no expression-opcode emitter for it; this is the first), and
  `remove_member` is `RemoveParty` (`0xDD`) via the existing `opcodes.encode`. `party_body`/`inject_party`
  prepend the sequence to **Main_Init** like `[startup]` (`edit.insert_in_function`, byte-safe; byte-identical
  when the block is absent). Names resolve via a CharacterOldIndex table (Zidane 0..Blank 11; aliases
  `dagger`/`salamander`; bare `0`–`11` ok) kept in lockstep with `forkreport.CHAR_OLD_INDEX` by a test.
- Wired into `build.py`: `_apply_party` runs in BOTH the synthesize path (`build_script`) and the verbatim
  `.eb` path (`build_field`) — so a verbatim fork's `[party]` fires too, mirroring `[startup]`/`[[on_entry]]`.
  `validate()` resolves every name (`_validate_party`). ★ A verbatim fork that rebuilds the roster
  (`SetPartyReserve`, `0xB4`, which runs **after** our prepend → can wipe the op) gets a build **warning**
  (`field_resets_party` scan). `.eb`-only, no DLL; FF9 renders only the leader, so an added member shows in
  the menu/battle, not as a field follower. No flag allocation (party state, not gEventGlobal).
- **Adversarial review (3-lens workflow) caught two real bugs the tests missed — both fixed before landing:**
  (1) **jump-table crash** — `inject_party` (and the pre-existing `[startup]`/`[[on_entry]]`) raised an *opaque*
  `ValueError` on the ~11% of real fields (incl. **field 100**) whose Main_Init opens with a 0x06 jump table the
  byte-inserter can't shift past. Now the verbatim path **fails closed** with a clear `BuildError` (shared
  `_field_load_inject` wrapper, all three levers). (2) **wipe-warning blind spot** — the reset scan only looked
  at entry-0/tag-0, but real `SetPartyReserve` lives in object Inits / tag-1 (only **2 of 111** reset fields keep
  it in Main_Init); broadened to all non-empty entries' tag-0 + tag-1 (`field_resets_party`, catches 111/111).
  Plus two minor fixes: the wipe gate widened to `add OR remove`, and `inject_party` normalized to accept bytes
  or `EbScript`. Doc note: don't `remove` every member (an empty party hangs the menu).
- 12 tests (`tests/test_party.py`): emitters pinned to the proven probe, name/alias/int resolution + errors, the
  table↔forkreport lockstep, build injection (prepended, parses clean), byte-identity when absent, validation
  shapes, the broadened reset scan (a non-Main_Init `0xB4` is detected), and the jump-table fail-closed guard.
  (Adding a brand-new *custom* member is still the engine-fork frontier — Tier C in the memory.)

### Added — `import-chain --swap-player <char>`: play as one character across a whole forked region
- `import-chain <seed> --swap-player steiner` swaps EVERY verbatim member's player rig, so you walk as the
  chosen character across the whole forked slice (implies `--verbatim`; party/menu unchanged). Factored a
  shared `extract.apply_player_swap(toml, char)` (the sidecar swap, used by both the single import and the
  chain); `campaign.write_campaign(swap_player=…)` applies it per member + records `swap_gesture_warn`
  (cutscene members whose gestures glitch) and `swap_skipped`; the CLI summary reports the swap.
- ★ The swap-TARGET was fixed by an adversarial review (3-lens workflow) that the test suite missed: on a
  **Zidane-present** multi-PC field, `controlled_player` mispredicts (control routes through the party SLOT to
  the Zidane leader, not the last-`DefinePlayerCharacter` binder), so the swap was re-skinning a **co-actor**
  (Vivi/Garnet) while you still controlled Zidane — **66 of 169** such fields (Cargo Ship 500, Dali Wheel 350…).
  Now the swap targets the controlled-**leader model**: a Zidane field form (98/532) when present, else the
  proven binder for the no-Zidane fixed-SID lane; it patches ALL entries matching that model (`playerswap.
  leader_model` / `swap_targets`). Also: `controlled_player` downgrades to `low` confidence on a Zidane-present
  field; `swap_player` raises a distinct `NoSwappablePlayer` (so a chain SKIPs a no-player member but a real
  overflow/corruption ValueError still propagates loudly); the chain validates the char BEFORE the graph walk
  (true fail-fast); the summary is qualified ("N verbatim member(s) swapped"). 3 tests incl. a Cargo-Ship
  regression (swap hits Zidane, the Vivi co-actor untouched). kit 0.9.29.

### Added — `fork-report` Party axis: what a fork does to your party
- `fork-report` now reports a **Party** line — the party-membership ops a field performs, which a `--verbatim`
  fork RUNS (a plain fork inherits your current party). It decodes the literal single-char `B_PARTYADD`
  (`B_CONST <CharacterOldIndex> B_PARTYADD`, the expr op `0x6D`) inside expression statements + the statement
  party ops (`RemoveParty` 0xDD, `SetPartyReserve` 0xB4 = roster rebuild, `SetCharacterData`/JOIN 0xFE, `Party`
  menu 0xB2) — e.g. field 60 "adds Zidane, Vivi, Garnet, Marcus; sets the recruitable roster", field 100 "adds
  Vivi; rebuilds the roster (story reset)", the Dali Inn "opens the change-members menu"; a party-neutral field
  (the Hangar) gets no line. The `NONE` (0xFFFF) add-terminator is filtered and the lists are deduped. Read-only
  (`forkreport.py` only; `scan_party_ops` reuses the disasm) — completes the fork-preview (Player / Roster /
  Interactions / Dialogue / Story-gating / **Party**), and directly serves the PC/party goal (the recipe lives
  in memory `project-ff9-pc-party-system`). 4 tests (`tests/test_forkreport.py`). kit 0.9.27.

### Added — `import --swap-player <char>`: walk as a different existing character (Tier A, productionized)
- Fork a field and **swap who you walk as** to any existing playable — `import <field> --swap-player steiner`
  (zidane/vivi/steiner/garnet/freya/quina/eiko/amarant; aliases dagger, salamander). It patches the player
  entry's Init `SetModel` + the movement anim ids (idle/walk/run/turn-L/turn-R/idle-break) to that character's
  rig — a same-length, width-aware byte patch (`playerswap.swap_player`). Implies `--verbatim` (it needs the
  donor's real player entry in the shipped `.eb`); **party/menu state is unchanged** (field control and party
  roster are decoupled). The character table is real data, EXTRACTED from each character's home field (model
  id + eye-height + movement clips). ★ The productionized form of the **in-game-proven Tier-A probe** (walk as
  Steiner in a Zidane field; memory `project-ff9-pc-party-system`). New module `ff9mapkit/playerswap.py`
  (read-only transform) + the `--swap-player` flag wired through `cli.py` (forces verbatim, applies the swap to
  the shipped sidecar `.eb`). `.eb`-only, no DLL. ★ CAVEAT (warned): the swap repoints only the 6 MOVEMENT
  clips, so it's CLEAN on a free-roam field but on a CUTSCENE field the player's scripted GESTURES
  (`RunAnimation`, rig-specific) glitch on the new model — `playerswap.scripted_gesture_ops` counts them (Vivi
  field 100 = 15) and the CLI prints a `WARN`. For STORY fidelity (be a character *through* the story), use a
  verbatim fork at the right beat + the right party, not a model swap. 6 offline tests
  (`tests/test_playerswap.py`) — incl. a Vivi field→Steiner round-trip, a "swap to self is identity" check that
  proves the baked table matches the real game, and the gesture-warning detector. kit 0.9.26. (The complementary
  party-MEMBERSHIP authoring — `B_PARTYADD` etc. — is a declarative block in story_flags' lane; here only the
  fork-transform half landed.)

### Fixed — chest-band provenance: it is NOT the Treasure-Hunter scoring region (0.9.28)
Tracked down whether the kit's reserved "treasure-chest 'opened' bitfield" (bits **8376–8511**, bytes
1047–1063) is accurately attributed, after the modern-save safe-band audit flagged a possible conflation.
Verified directly from real `.eb` bytes (fields 115/300/2203/407 + 44 more):
- **The band IS real and correctly reserved** — ~48 chest-bearing fields (Ice Cavern, Burmecia Vault, Dali
  Storage, Cleyra, Palace, …) genuinely read-gate *and* set these bits. Custom flags there WOULD corrupt
  real chest state. `CHEST_FLAG_LO/HI`, the reservation, the lint, and `FIRST_SAFE_FLAG = 8512` are unchanged.
- **But the `EventState.GetTreasureHunterPoints` citation was WRONG** — that engine method scores a *separate*
  region (bytes **182–186 + 896–975**, already correct in `TH_POINT_RANGES`); the **stock engine never reads
  8376–8511** at all (grep-confirmed; the only chest-band reference in the engine tree is the kit's own F6
  debug-menu label). The chest band is justified by the field-script census alone.
- **And "every bit a 48-writer computed index → identity not static" was a misread** — the 48-writers-per-bit
  pattern comes from a **byte-identical 130-entry dispatch block** compiled verbatim into ~48 chest fields
  (fields 115 vs 300 share the same SHA over the 130 `bit = 1` statements), each statement targeting a
  *literal* bit index in a branch — a static block, not a runtime-computed index.

No behavior change (band bounds, reservation, safe band, TH scoring all identical). Corrected the prose +
citation in `flags.py` (the `chest_opened` region), the gate advisory in `build.py`, and the research record
(`research/STORY_FLAGS.md`, `research/make_catalog.py`); added a regression test asserting the chest band and
the engine TH-scoring bytes are disjoint and that the region no longer claims `GetTreasureHunterPoints`.

### Fixed — Story State console: B-slot dropdown + Memoria extra-save authority
- The Diff tab's **"B slot" dropdown couldn't be clicked** — it was created with no menu items and only
  populated when a *second* file loaded. It now fills from the loaded save's slots (or the B file's) on every load.
- **Memoria per-slot extra-save is now treated as authoritative** (the likely cause of "I set a flag but in-game
  it's still 0"): Memoria writes a per-slot `SavedData_ww_Memoria_*.dat` holding the gEventGlobal it RESTORES
  from on load, so the encrypted main block can be stale. `save.inspect` now reads the extra when present (and
  tags the slot) so the console shows what the game *actually loads*; `save.apply_story_edit` re-reads the extra
  after patching to **verify** the write took (`extra_patched`), and the GUI's Apply reports `[OK]` / `[WARN]`
  so an edit that won't show in-game is no longer silent. 3 save tests; kit 0.9.24.

### Added — Story State GUI console (inspect / diff / EDIT a save's story state)
- A new app `apps/ff9_storystate.pyw` (`StoryStateApp`) surfaces the story-flag pillar's save verbs in one
  window — the save-side companion to the Info Hub's story-flag *registry*: **Inspect** (each populated
  slot's ScenarioCounter→beat + story bits by named region, via `save.inspect` + `flags.render_report`),
  **Diff** (load a second save / slot → the A→B delta, `flags.diff_reports`), and **Edit** (set the
  ScenarioCounter / set+clear story bits → write back). Editing is **backup-guarded** (a `.bak` first) and
  **reserved-region-refused**, sharing the CLI's guards via a new `save.apply_story_edit` convenience
  (the in-place edit+backup+write+extra-patch path as one call, with a `dry_run` for the Preview;
  `edit_story_state` stays the shared core). Wired into the launcher + a Campaign-Editor tab. 3 save tests
  (`tests/test_save.py`) + a headless `--smoke` (inspect/diff crypto-free; edit-preview when pycryptodome is
  present). kit 0.9.23.

### Corrected — fork-fidelity #10 premise (entry cutscenes are `.eb`-borne, not a C# `NarrowMapList` trigger)
- A load-bearing belief in the docs/memory was **wrong** and is now corrected (verified directly in the Memoria
  source): `NarrowMapList.cs` is the engine's per-field **camera-WIDTH / widescreen** table (PSX screen widths,
  narrow-vs-wide cam, crop margins) with **zero** cutscene logic — its only callers are `FieldMap`/`PSXCameraAspect`.
  A field's **entry cutscene runs from its own `.eb`** (entry-0 + actor sequences), so a `--verbatim` fork carries
  it (in-game proven: Vivi/field 100's opening), and `[[on_entry]]` re-authors one for a synthesize fork. The
  "needs a dev-engine `NarrowMapList` patch" framing of #10 was a phantom; the only genuine engine-side residual is
  **cosmetic and keyed on the donor's real id** — widescreen camera-width (`MapWidth` defaults to 500 for a custom
  id), a few per-actor anim tweaks (`FieldMapActor.cs`), and FMV playback (field 70). Docs/comments-only correction
  across CLAUDE.md, FORK_FIDELITY.md, FORMAT.md, FEATURES.md, CAMPAIGN_IMPORT.md, `content/onentry.py`, `build.py`,
  the tests, and the project memory (no code-behaviour change).

### Added — `fork-report` Dialogue axis (the #5 text gap, previewed before you fork)
- `fork-report` now reports a **Dialogue** axis (orthogonal to the interaction-safety axis): how many carried
  NPCs **speak** (a tag-3 talk window) and how many lines — e.g. Daguerreo 2F "6 NPC(s) speak 36 line(s)".
  Their words render **wrong** unless the fork carries the text, so the line says ship with `--carry-text`
  (or `--verbatim`), pointing at the build-side lint (FORK_FIDELITY.md #5) as a *before-you-fork* preview.
  Read-only — reuses `dialogue.scan_dialogue` (the analysis-layer `.eb` reader), filtered to the carried
  objects' talk handlers; no scanner logic of its own. Validated on real fields (Daguerreo 6/36, Dali Inn
  1/8). 2 offline tests + an install-gated assertion (`tests/test_forkreport.py`); kit 0.9.21.

### Added — `fork-report` computes the REAL controlled PC in a multi-PC non-Zidane fork
- The control-bind mechanism is now **engine-sourced + in-game proven** (a 3-lens workflow over the Memoria
  C# + the donor bytes + a verbatim playtest). When a field defines >1 `DefinePlayerCharacter` (0x2C), the
  engine binds player control to the entry whose 0x2C **executes LAST** at load (`controlUID = gExec.uid`,
  last-write-wins, `EventEngine.DoEventCode.cs`); entries run their Init in **InitObject (0x09) order**, so the
  binder is the entry whose tag-0 Init runs a 0x2C **unconditionally** and is InitObject'd **latest**. It is
  **party-leader-independent** for fixed-SID character fields. ★ **IN-GAME PROVEN** on a verbatim fork of the
  Treno Dagger+Steiner room (`evt_treno1_tr_qhm_0`, shipped over the FBG scene): you control **Garnet** (entry
  9, last-executed 0x2C) — NOT Steiner (entry 10, spawned first), NOT Zidane (party leader); free-roam, and the
  bind persists across gateways. The party MENU still shows Zidane — `controlUID` is decoupled from party state.
- So `fork-report`'s **Player** axis now reports the *real* controlled character (`controlled_player` = last
  unconditional 0x2C by InitObject order) for a non-Zidane multi-PC field — e.g. `controls Eiko of [Garnet,
  Eiko]` — instead of the old `pents[0]` guess (the FIRST entry, which mispredicts: ac_alt binds Eiko not the
  first-entry Garnet). It's scoped to the non-Zidane lane (where it's validated); a **Zidane-present** multi-PC
  field keeps the conservative "likely Zidane party-leader" hedge (control there can route through a party slot
  to the live leader, which this doesn't model — the Cargo Ship would mispredict). Confidence is hedged (`?`)
  when the binder is multi-spawned or only gated. Read-only (`forkreport.py` only). 2 tests; memory
  `project-ff9-non-zidane-donors`. (No reliable offline free-roam-vs-cutscene flag exists — player-LOOP length
  doesn't separate them: Vivi-100/Dali-Inn free-roam at ploop 254/272, the ac_alt *cutscene* at 50 — so none
  was added; the first multi-PC probe burned a playtest on the ac_alt coronation cutscene.) kit 0.9.22.

### Added — `fork-report` is now PLAYER-CHARACTER aware (non-Zidane donors)
- A field's controlled character isn't always Zidane (Vivi/Steiner/Garnet/Eiko/Freya/Amarant solo sequences).
  A census of all 818 field `.eb` (one events-bundle pass; `eventscan.resolve_player_entries` + `_player_model`)
  found **178 non-Zidane-primary** fields, ~80 *truly playable as a party member*. `fork-report` now reports a
  **Player** axis: who you play as, single- vs **multi-PC** (`[MULTI-PC]`), and — for a non-Zidane controlled
  character — switches the suggested recipe to **`--verbatim`** (which ships the donor player rig + anim packs
  + the field's own party/cutscene setup whole; the `--graft-player-funcs` path *drops* a non-Zidane player's
  funcs as `"model"` graft-safety — another rig's clip ids). The multi-PC inference is conservative: the FIRST
  `DefinePlayerCharacter` is NOT reliably who you control (the Cargo Ship lists Blank first; you play Zidane),
  so a single-PC field is crowned confidently while a multi-PC field is only called non-Zidane-controlled when
  **no Zidane is among the PCs** (the Treno Dagger/Steiner split) — else it's flagged "likely the Zidane
  party-leader; co-actors are the rest". **★ In-game proven (Vivi / Alexandria street, field 100):** a
  `import --verbatim` fork plays IDENTICALLY — Vivi renders + animates + is in the party menu, and the field's
  real ticket-girl opening cutscene plays (so that intro lives in the `.eb` entry-0, not a C# `NarrowMapList`
  table — the verbatim fork carries it). So a clean single-PC non-Zidane field already forks faithfully with
  ZERO new code; the frontier is the multi-PC / scenario-gated-player bind. Read-only (`forkreport.py` only),
  reuses the existing scanners. 2 tests (`tests/test_forkreport.py`); memory `project-ff9-non-zidane-donors`.
  kit 0.9.19.

### Added — softlock / wrong-text lint for a plain (no-carry) import (FORK_FIDELITY.md #5)
- A plain `import` (no carry flags) carries a real field's objects but **not** their player funcs or dialogue
  text, which can softlock or mis-render in-game. Both halves are now caught **build-side, offline**:
  - **(b) dangling player tag = the softlock** was already a build-blocking `validate()` error — a carried
    `[[object]]` that `RunScript`s the player at an un-grafted tag (`_entry_player_call_tags`).
  - **(a) un-carried talkable text = wrong/missing dialogue** is the new piece: `lint_logic` decodes each
    carried object's talk windows (`_entry_window_txids` — mirrors the player-call decoder) and warns when a
    shown donor txid isn't in the `[carry_text]` plan (\"import with --carry-text, or author the line\").
  Validated against real imports — a plain `--native` Daguerreo fork flags all 5 talkable NPCs, a
  `--carry-text` fork is silent (no false positive), props are skipped. Reads only stable build-side
  representations (the `[[object]]` bins + the carry plan); orthogonal to the eventscan classifier.
  5 tests (`tests/test_carry_text_lint.py`); kit 0.9.20.

### Added — message-in-verbatim: an `[[on_entry]]` narration line now SHOWS in a verbatim fork
- After the convergence (`build._apply_on_entry` runs on the verbatim path), an `[[on_entry]]` gated
  state-advance already fired in a `--verbatim` fork — but the narration **message** was dropped (the donor
  `.mes` ships verbatim, with no slot for authored text). Now the authored line is **appended to the donor
  `.mes` above its max txid** (`build._verbatim_on_entry_messages`, floored at `textcarry.CARRY_BASE_TXID`
  1000 — the same append-and-resolve trick `--carry-text` uses), and the hook's `WindowSync` resolves into
  it. So a verbatim fork's on_entry beat now fires its message **and** its state-advance on top of the
  donor's real logic. `_apply_on_entry` is unchanged (its `drop_messages` param stays a general capability);
  only the verbatim branch of `build_field` now supplies the text channel, and the now-obsolete
  "message won't show in verbatim" lint warning is retired. **In-game proven** on a Dali-Inn verbatim fork
  (the appended line renders, `set_flags` advances state, the inn's own NPCs still speak their real lines).
  3 tests (`tests/test_on_entry.py`); kit 0.9.18.

### Added — deploy-time text-block SHADOW guard (`deploystack.py`)
- A field loads its dialogue by **mesID** (`text_block`), and the engine reads that `.mes` from the **first**
  mod folder in `Memoria.ini` `FolderNames` that defines `field/<mesID>.mes`. When several stacked worktree
  mod folders (`FF9CustomMap-*`) all use the kit-default block **1073**, a lower-priority folder's text is
  **shadowed** — the field renders a *higher*-priority folder's block-1073 text instead. This bit an
  `[[on_entry]]` playtest: a probe in `FF9CustomMap-sf` showed `FF9CustomMap`'s stale "Rally-ho!" rather than
  its authored line (the flags were correct; only the text was someone else's). `tools/deploy_field.py` now
  **warns at deploy time** — naming the shadowing folder and suggesting real mesIDs no higher-priority folder
  defines (e.g. "use text_block = 187"). The check is a pure, offline, tested kit function
  (`deploystack.check_text_block_shadow` / `parse_folder_names` / `shadow_warning`); deploy also accepts
  `--text-block N` (or `text_block = N` in `.ff9deploy.toml`) to pin a worktree-unique block. 8 tests
  (`tests/test_deploystack.py`). kit 0.9.16.

### Added — `[[on_entry]]`: gated, once field-load beats (FORK_FIDELITY.md #10)
- *(Premise corrected later — see "fork-fidelity #10 premise" below: a field's entry cutscene runs from its own
  `.eb`, so a verbatim fork carries it; `[[on_entry]]` re-authors one for a synthesize fork. The "C# `NarrowMapList`
  table" framing was a misread — that's the camera-width table.)* `[[on_entry]]` is the declarative re-authoring
  hook: fire a narration `message`
  and/or story-state writes (`set_scenario` / `set_flags`) the moment the player **enters** the field, **once**,
  but **only when the story state matches** (`requires_scenario` = a ScenarioCounter `== N`, and/or
  `requires_flag`). The gating is the new capability — neither `[startup]` (unconditional, every entry) nor
  `[cutscene]` (ungated, single) can say "fire this beat only at scenario N / when bit B is set". Each hook is a standalone code entry armed by an `InitCode`
  in Main_Init (the proven narration-cutscene arming, now robust for any count via the region-arming fix below),
  so it runs at field load *before* control is re-enabled (hence no movement gate); a `message` beat reuses the
  cutscene's reorder-`Wait` + `DisableMove`/`EnableMove` lock so the window shows cleanly during the entry fade.
  `content/onentry.py` + `build.py` (validate / collect_text / inject / lint) + `flags.py` (name resolution,
  read/write parity); surfaced in the dialogue viewer/editor (`collect_text_refs`). Byte-identical when absent.
  An adversarial pre-commit review (4 read-only lenses) hardened two edges: the single-field auto once-flag
  band is guarded against reaching FF9's reserved chest bitfield (a `BuildError` instead of silent save
  corruption), and `lint_logic` warns when `[[on_entry]]` coexists with a `--verbatim` fork (which ships the
  donor `.eb` as-is, bypassing the hook). 16 tests (`tests/test_on_entry.py`); 828 suite. kit 0.9.15.

### Fixed — region arming silently lost on fields with >2 regions
- `eb.edit.activate` (the Main_Init region-arming primitive) overwrites a `Wait` filler shift-free, but the
  blank/borrowed template has only **2 `Wait` fillers**; the 3rd+ region fell back to a raw `insert_bytes` at
  a **stale Main_Init position**, so the 2nd+ insertion landed in already-consumed bytecode and that region
  **silently never armed** (its trigger never fired). It bit a forked **campaign chain** (a field's 2 gateways
  consumed both fillers, so its on-entry events never fired) and would bite any content-rich fork. Fixed by
  routing the fallback through `insert_in_function` (the fpos-fixing insert, same primitive `[startup]` uses),
  so any number of regions arm correctly even on a borrowed field with a real entry-0 tag-1 function.
  Within-budget fields (≤2 regions) still hit the patch path and are **byte-identical**. New `tests/test_arming.py`
  (5 regions all arm; the `.eb` stays parseable). Surfaced by an adversarial diagnosis workflow.
- `build.lint_logic` now counts a gateway's `set_flags` and `[startup]`'s `flags` as flag **setters**, so a
  same-field "a door reveals an NPC" pattern no longer false-warns "no event sets it".

### Added — `fork-report`: preview a real field's fork fidelity (offline)
- **`ff9mapkit fork-report <field>`** (id or FBG substring) answers, before you fork, "will this field play
  faithfully?" — reading the compiled `.eb` with no game running. It reports two INDEPENDENT axes:
  **roster fidelity** (how many objects a fork carries, how many are `Field()`-warp **directors** = cutscene
  actors carried as NPCs, and whether content rotates by story beat) and **interaction fidelity** (per NPC,
  whether its talk handler ports — `clean` = fully interactive / `init_only` = render-only / `refuse` = stub).
  Plus story-gated doors, the ScenarioCounter **beats the field gates content on**, and a suggested
  `[startup] scenario` (the earliest gate) + `import` recipe. Verdict: a clean static-roster field (forks
  faithfully) vs a story-event field (a high-fidelity diorama — rotating cast / cutscene actors). Validated:
  the real Dali Weapon Shop → STORY-EVENT (1 director, 11 rotating beats Dali→Pandemonium); Daguerreo 2F →
  CLEAN static-roster. **Read-only** — reuses `eventscan.scan_objects_verbatim` (the carry `graft_safety`
  classification) + `scan_gateway_entries` + the `flags` beat table; adds no carry/scanner logic. New module
  `ff9mapkit/forkreport.py` (pure `analyze_eb` + thin id-loader, unit-tested offline against a fixture).
  Surfaced as a **Preview fidelity** button in the FFIX Import GUI (`apps/ff9_import.pyw`) — standalone and the
  Campaign Editor's Import tab — so you can read the verdict before importing.
  (`docs/FORK_REPORT.md`; `docs/FORK_FIDELITY.md` — the north star is "fork a real field → does it play identically?")

### Added — `[[gateway]]` on-exit story advance (fork-fidelity #3)
- A `[[gateway]]` can now **advance story state when the player takes that exit**: `set_scenario = N | "area"`
  bumps the ScenarioCounter and `set_flags = [{flag = <index|name>, value = 0|1}]` sets/clears gEventGlobal
  bits. The `set_var` writes are prepended to the gateway's Range trigger **behind a `usercontrol` guard**
  (so they fire on an actual walk-out, not a puppeted pass) and **behind any `requires_flag` gate** (so a
  gated door only advances the story when it's actually open), just before `Field()` — the values commit to
  the save-backed gEventGlobal before the transition. This is the write-side complement to `[startup]`'s
  entry-side assert: a forked field **chain** can now progress the beat as the player moves through it.
  Reuses `content/startup.startup_body`; `validate` + the reserved-band `lint` mirror `[startup]` (a write
  into a reserved region is flagged). Flag **names** in `set_flags` (and `[startup]`'s `flags`) resolve at
  load against the project's `[[flag]]` table **merged with campaign-shared names** — read/write parity with
  `requires_flag`, so a campaign member can write a shared story flag by name. Byte-identical build when the
  keys are absent. (`docs/FORK_FIDELITY.md` #3.)

### Added — FFIX Import GUI: the import-from-game functions, made discoverable
- **`apps/ff9_import.pyw`** — a front door to the kit's "bring content in from the real game" commands, so
  the powerful but cryptic `import` flags become **plain checkboxes**. Two tabs: **Field** (pick a real
  field — `Find…` runs `list-fields` — choose Background art `Native` / BG-borrow / Editable, and tick what
  to carry: *NPCs & props* / *real dialogue* / *dialogue stubs* / *save point*; then `Import field`) and
  **Read & Inspect** (`dialogue-import` a field, `flags-inspect` a save, `list-fields`, regenerate base
  templates). Each action shells out to `py -m ff9mapkit …` from the kit root and **streams** the output;
  the Field tab ends with a "→ deploy with Build & Deploy" hint. Standalone (in the `ff9_studio` launcher)
  **and** a new **Import** tab in the Campaign Editor. The fidelity mapping is a pure, smoke-tested
  `import_args()` (e.g. Native + carry-NPCs + carry-text → `import <f> --out … --id … --native
  --graft-player-funcs --carry-text`).

### Added — `[startup]`: assert the story beat a forked field represents
- **A forked real field boots with a zero `gEventGlobal`**, so every story-gated NPC/door/event takes the
  not-yet-happened branch — the field plays in its scenario-zero state. The new **`[startup]`** block presets
  the **ScenarioCounter** (`scenario = N` or an area name like `"Alexandria Castle"`) and/or specific story
  bits (`flags = [{flag = <index|name>, value = 0|1}]`) **unconditionally at field load**, prepended to
  Main_Init so every gate evaluated afterwards sees the asserted state. The biggest single fork-fidelity lever
  (`docs/FORK_FIDELITY.md` #1): a fork can finally boot in the right beat.
- Author-side only (you assert the beat — you have the game knowledge); no extraction. The ScenarioCounter is
  written via the engine's `0xDC` token (`set_var(GLOB_UINT16, 0, value)`); a story bit via
  `set_var(GLOB_BOOL, idx, value)` (long-index aware). Injected with `edit.insert_in_function` (entry-0 tag-0,
  offset 0 → byte-safe, fpos fixed), so a field **without** `[startup]` builds byte-for-byte as before.
- Unlike authored `set_flag` (safe `[8512,16320)` band only), a `[startup]` preset is *meant* to assert REAL
  FF9 story bits below 8512 — so the safe-band rule doesn't apply; the lint still flags a preset into a
  genuinely *reserved* region (chest bitfield / byte-23 handshake / worldmap unlocks / choice scratch).
  Spine: `content/startup.py`. *In-game verification (F6 reads the asserted beat) is the human step.*

### Added — story-flag registry depth: the worldmap Navi known-location words
- **Four new engine-grounded named vars** (`flags.NAMED_WORDS`): `WorldmapKnownLocationsF0..F3` (bytes
  92/94/96/98, UInt16, tier a) — the worldmap Navi cursor's known-location bitmasks (`keventNaviLocF0..F3`;
  F0 is the engine's own `knownLocations`). The first engine-reader pass grepped `gEventGlobal[<const>]`
  directly and missed the wrapper-accessor form (`ushort_gEventGlobal(92)`); re-scanning the complete
  fixed-index set recovered them. Naming bytes 92–99 as words also reclassifies that slice of the
  "write-only worldmap-unlock bits" as recognized word data (a decoded save now reports
  `WorldmapKnownLocationsF0 = N` instead of anonymous set bits). Surfaces automatically through
  `flags-inspect` / the Info Hub / `flags-diff`. `NAMED_WORDS` stays tier-(a)-pure (tested invariant).

### Added — dialogue polish: campaign-wide review + a live-text resolver diagnostic
- **`ff9mapkit dialogue` now accepts a `campaign.toml`** (it auto-detects a `[campaign]` manifest) and
  reviews **every member field's** authored dialogue in one pass — per-field sections with the final
  on-screen wrapping, plus a roll-up (total lines, which fields may overflow). A member that fails to load
  is noted and skipped, never aborts the review. Single-field `dialogue <field.toml>` is unchanged. Spine:
  `dialogue.campaign_dialogue` + `dialogue.flag_overflow` (the overflow check, now shared by both paths).
- **`dialogue-import` now says WHY a real field's text didn't resolve.** When the live `<zone>.mes` read
  comes back empty it distinguishes the two install/dependency failure modes — UnityPy not installed, or
  the game install / `resources.assets` not found (pass `--game`) — from "the source is fine, the field's
  block just didn't cover these txids; pass `--zone-id`." Spine: `dialogue.text_source_status` (never raises).
- **`ff9mapkit lint <field.toml>` runs the WHOLE offline suite in one go.** It used to be schema
  (`validate`) + story/flag logic (`lint_logic`) only; the walkmesh geometry / content-placement /
  layer-art / cutscene-movement checks lived behind `walkmesh verify`, and the camera-pitch advisory
  behind `guide`. They now all surface through `lint`, grouped by `[section]` — `logic`, `flags`,
  `placement`, `camera`. The pass degrades gracefully: a project whose camera/walkmesh can't resolve
  still reports its schema + logic findings (the resolve failure is recorded as an error, never a crash).
  Spine: `build.lint_all(project) -> LintReport` (the single source of truth; `walkmesh verify` is
  unchanged and still standalone).
- **New check — reserved story-flag bands.** A raw `set_flag = [N, 1]` / hand-written once `flag = N` /
  `requires_flag = N` (on an event, NPC, **prop**, gateway, cutscene, or choice) that lands in a *reserved*
  `gEventGlobal` region (the treasure-chest 'opened' bitfield 8376-8511, the byte-23 menu handshake, the
  worldmap-unlock bits, or the choice-mask scratch) is flagged and named — a WRITE there corrupts real
  save/engine state; a chest-band READ is unreliable. This extends the `[[flag]]` validator's safe-band
  guard to the literal indices that bypass it. The kit's established 8000+ working band is free space, so
  it draws no warning. `build.lint_flag_bands`.
- **Refined — the off-walkmesh content check no longer cries wolf on back-wall NPCs.** An NPC is placed by
  a world transform and renders regardless of the walkmesh; a normal FF9 NPC stands against the back wall,
  just past the floor edge, and the player talks to it from the adjacent floor. The check now HARD-warns
  only when an NPC is *grossly* off (farther than talk reach outside the floor's bounding box — a real
  misplacement), instead of flagging every edge-adjacent NPC as "will float / be unreachable." The player
  spawn and ladder landings still require being on the mesh. (Fixes a false-positive the unified `lint`
  exposed on the in-game-verified `vivi-hut` oracle; affects `build` / `walkmesh verify` warnings too.)

### Added — `flags-diff`: compare two saves' story state
- **`ff9mapkit flags-diff <A> [B]`** decodes two saves' `gEventGlobal` and shows the **A → B delta** — the
  ScenarioCounter change (with beat names), FieldEntrance, Treasure-Hunter points, chests, named word vars,
  and the story **bits set / cleared** (grouped by named region). The practical way to learn what a story
  beat writes: save before, do the thing, save after, diff. Reads the same forms as `flags-inspect` (an
  encrypted `SavedData_ww.dat`, a Memoria extra-save, a save JSON, or a bare Base64 blob); with one save,
  `--slot-a` / `--slot-b` diff two slots (default slot 0 → slot 1). Spine: `flags.diff_reports` /
  `flags.render_diff` (the bit-grouping is shared with `render_report`, so a bit is classified identically).

### Added — faithful object carry v1.5: the STARTSEQ-helper closure (+ two v1 correctness fixes)
- **A forked object now carries the concurrent Seq it launches.** A real field object often runs a
  benign per-frame helper via `STARTSEQ` (RunSharedScript) — a forward-lean, a shadow toggle, a small
  animation loop. v1 dropped that helper, so the object was REFUSED (left to a hand-authored stub).
  v1.5 carries the helper too — appended at a free slot and the launcher's entry-arg remapped, exactly
  like the proven ladder `sequences` graft — so the object renders faithfully. Across the real game this
  **un-refuses 53 objects and un-stubs 23 more** (faithful object coverage ~65% → ~70%); 109 helpers are
  carried, every one a benign type-1 Seq. Always on for `import` (a pure fidelity win, no flag).
- **The closure is body-vetted, not blind.** A helper that runs a cutscene op — a `MoveCamera` sweep, a
  `Battle`, a `Field`/`PreloadField` warp, a menu, a window — is NOT carried (it would fire in a static
  fork): those objects stay refused. The helper is appended-but-never-armed (a Seq is launched at runtime,
  not `InitObject`'d) and a helper shared by several objects is appended **once** (field-scoped dedup).
  `ff9mapkit lint` rejects an unsafe / non-type-1 / nested-STARTSEQ / double-armed helper.
- **Sibling-OBJECT closure was investigated and found EMPTY** — every uncarried object-to-object reference
  resolves to the party, the player, a controller, save machinery, or out-of-range, so there is nothing
  safe to carry there; v1.5 is exclusively the STARTSEQ-helper closure (a 676-field census + adversarial
  verification).
- **Fix: a sibling read inside an EXPRESSION operand is now remapped.** A grafted body that reads another
  object via the `op78` (B_OBJSPECA) expression token kept the donor's entry index after the move → it
  acted on the wrong/empty fork entry. The graft now walks the expression token stream and remaps it (a
  same-length 1-byte patch) — fixing ~31 already-shipped v1 objects as well as the closure.
- **Fix: a field with several `DefinePlayerCharacter` entries (182 of them) is classified correctly.** A
  reference to a *secondary* player entry was mis-read as an uncarried sibling; it now classifies as the
  player and the graft normalizes every PC entry to the runtime controlUID (250). Removes ~170 false
  "uncarried" refs and 7 secondary-PC false objects.
- Single-field authored builds stay **byte-identical** (the closure is off by default in
  `scan_objects_verbatim`; the hut SHA-256 golden is unchanged). Every real field's objects graft and
  round-trip (676/676, 0 errors). See `docs/OBJECT_CARRY.md` §2.

### Added — dialogue pillar (a dialogue editor + a stock-dialogue viewer)
- **The read side of FF9 field text.** New `ff9mapkit.dialogue` spine (UI-agnostic, tk-free): `parse_mes`
  (the missing `.mes` reader — handles BOTH the base game's index-implicit entries, where the txid is the
  entry's 0-based position with no `[TXID=]` tags, and the kit's explicit form it round-trips), `scan_dialogue`
  (decode every dialogue-window call + its txid out of a field's `.eb`), and `read_local_dialogue` /
  `read_field_dialogue` that JOIN the two into "NPC → text". A real field's text block is found via the
  engine's own `eventIDToMESID` table (baked into `_fieldtext.py`), language picked by stopword match.
  `project_dialogue` lists a `field.toml`'s authored lines with their final on-screen wrapping. The proven
  write path (`content.text` wrap/build_mes) is untouched — goldens stay byte-identical.
- **`ff9mapkit dialogue <field.toml>`** views a field's authored dialogue (every NPC line / event message /
  choice prompt+reply / cutscene say) and how each line wraps; flags lines that may overflow the window.
- **`ff9mapkit dialogue-import <field>`** reads a REAL FF9 field's dialogue live from your install and shows
  "NPC → text" — the "import from the game to prove plausibility" verb. `--mod <built mod folder>` reads a
  field offline with no install (the kit's own shipped hut joins to *"I miss you Zidane"*); `--zone-id <n>`
  reads a specific `<n>.mes` text block; `--out` writes a gitignored JSON view (SE-derived). By default it
  shows only real dialogue — `flags=0` system/notification windows (a field's error guard, "Received item!"
  popups) and repeated call sites are hidden (`--all` shows them), and the kit-only `@x,z` position heuristic
  is dropped on real fields.
- **Re-author a fork (`ff9mapkit import <field> --dialogue`)** appends the real field's NPC lines as
  ready-to-use, commented `[[npc]]` blocks (real model resolved by GEO name, clean editable text, a `pos`
  placeholder) — the "fork a field and rewrite its script" workflow. They parallel the verbatim-carried
  `[[object]]` NPCs; uncomment + reposition + rewrite the ones you want.
- **A dedicated Dialogue editor GUI** (`apps/ff9_dialogue.pyw`): every line of a field in one list, each with
  a **live preview of how it wraps on the FF9 screen** (so simple dialogue stays well-formatted — FF9 never
  auto-wraps), speaker + window-tail edited alongside, and an "Import from game" panel that views stock
  dialogue and can drop lines in as NPC stubs. Edits round-trip the same `field.toml` the Logic Editor uses.
- **Integrated:** a **Dialogue tab** in the Campaign Editor that **shares one `FieldDoc`** with the Logic
  Editor (the words edited in either are the same data, no divergence); the Logic Editor's new **"Dialogue…"**
  button hands the current field off to it; and a launcher entry. View stock dialogue, or word-smith a
  campaign's lines, from the same surface.

### Added — battle-map pillar (custom 3D battle backgrounds)
- `ff9mapkit battle-import <BBG>` forks a REAL FF9 battle background out of your install (geometry +
  per-submesh textures) into an editable `battle.toml` + `<BBG>.fbx`; `ff9mapkit battle-build` compiles
  it into a Memoria mod; `tools/deploy_battle.py` installs it reversibly into the per-worktree mod
  folder. `battle-list` browses the real BBGs available to fork.
- A battle map is a real textured **3D mesh** (child groups Group_0/2/4/8 = additive/ground/minus/sky)
  shipped as a loose ASCII **FBX** that **stock Memoria** loads instead of the bundle — no engine
  rebuild. **In-game verified** (texture reskin, a synthetic quad, and a byte-faithful BBG_B013
  round-trip). The first practical custom-battle-background pipeline for FF9. See `docs/FORMAT.md`
  → "Battle maps". Provenance-clean: geometry/textures are extracted from your own install at runtime,
  never committed.
- **Tier-c MINT — a brand-new battle SCENE (in-game proven).** `battle-import --fork-scene <DONOR>`
  also forks a real battle's gameplay/sequence/camera/text (raw16 + raw17 + per-lang `.eb` + `.mes`) into
  the project; `battle-build` emits a net-new `BattleScene <id> <NAME> <BBG>` registration plus those
  assets, and `--ship-as BBG_B<N>` ships the geometry under a **brand-new bbg number** (a wholly original
  map — the kit authors a static `.inb` for it). `deploy_battle.py --trigger-field N` repoints a field's
  encounter at the minted scene so you can fight it. No camera authoring needed (the donor's raw17 carries
  a working camera; a static `.inb` dodges the per-id anim tables). **In-game proven**: a net-new
  `BBG_B200` + scene on stock Memoria, fully fightable. The kit's emitted raw16/raw17/eb/mes are
  byte-identical to the hand-built probe verified in real gameplay. Provenance-clean: forked scene assets
  are SE-derived, written to a gitignored project dir, never committed.
- **Tune the fight (`[scene]`).** A minted battle's forked gameplay is now AUTHORABLE, not just a clone:
  a `[scene]` section in battle.toml overrides enemy **positions** (`pos`/`y`/`rot`), **stats**
  (`hp`/`mp`/`gil`/`exp`/`level`/`speed`/`strength`/`magic`/`spirit`), **rewards** (`drop`/`steal`, items
  by name), and the **camera** pose. The kit surgically patches the forked `raw16` (only edited bytes
  change) and keeps enemy TYPES intact so the forked attack sequences stay valid; items resolve by name
  (`"Hi-Potion"`); shared-type edits warn. Validated against the real Evil Forest scene (Goblin HP 33 →
  1500, etc.).
- **Spawn composition (`[scene]`) — recompose AND grow the encounter.** `monster_count` sets how many
  slots spawn (1–4, the engine cap) and a per-slot `type` chooses which enemy fills it (the scene's
  EXISTING types, so the forked raw17 sequences + GEO cover them; made targetable + auto-grounded). It
  writes the composition to EVERY pattern (a deterministic fight) and **re-authors the battle eb's
  `Main_Init` to bind one enemy-AI object per spawned slot** (`InitObject(1+type, 0x80+slot)`, reusing the
  donor's per-type AI entries). That removes the earlier donor-count cap entirely: a mint can now spawn
  MORE enemies than its donor natively did (e.g. a 1-enemy Evil Forest → four Goblins) with no player-model
  twitch — every slot has a real AI object, so no death misroutes into the player
  (`EventEngine.RequestAction`). In-game proven. Errors only if a needed per-type AI entry is absent
  (a non-standard donor eb). raw16 + Main_Init only; raw17 untouched.
- **Opening-camera tweaks (`[scene]`).** `camera_yaw` / `camera_pitch` / `camera_zoom` rotate / tilt / zoom
  a minted battle's opening camera by offsetting the donor's `SFXDataCamera` keyframes in raw17 IN PLACE
  (no offset-table repack). Cracked the "closed DLL camera" frontier: the native FF9SpecialEffectPlugin.dll
  reads the raw17 camera bytes directly (`SFX_StartPlungeCamera` gets the pinned raw17 + camOffset), so this
  renders with NO engine rebuild — in-game proven. Targets `cameraList[CameraNo]` = the raw16 `camera`
  selector. yaw + zoom are predictable; **pitch is an offset onto the donor's base angle (large values can
  dip the camera below the floor — use small steps).** Full from-scratch keyframe authoring (length-changing)
  is a future tier needing the offset repack.

### Added — `give_item` by name; gil can subtract
- `give_item = ["Potion", 1]` — items resolve by name (case/space/hyphen-insensitive) or numeric id,
  baked from Memoria's `RegularItem` enum (`ff9mapkit items` lists them). No more memorizing ids
  (236 = Potion; 232 was Sapphire). Negative `gil` now correctly **subtracts** (`RemoveGil`).

### Added — dialogue choices (`[[choice]]`)
- Talk to an NPC, pick from a menu, and **branch** on the answer — the interaction / puzzle primitive
  (merchant, Yes/No lever, quest-giver). Each option can show a reply, give an item / gil, and set a
  story flag (feeding the same `requires_flag` system). Grounded byte-for-byte in a real FF9 shop
  choice: a synchronous `WindowSync` prompt (rows after `[CHOO]`) + a `GetChoose()` branch. See
  `docs/FORMAT.md` → `[[choice]]`. **In-game verified.**
- The form editor (`ff9mapkit edit`) has a **Choices** section: edit the prompt/NPC and a list of
  options (text / reply / give item / gil / set flag), reorderable, with `give_item` by name.
- A choice can be **zone-triggered** (a lever / sign): `[[choice]] zone = [...]` instead of `npc`.
  Default `trigger = "action"` (stand on the zone and press) — re-usable, "decline" is non-destructive,
  and it can't loop (edge-triggered by the button), like a real FF9 lever. `trigger = "walk"` auto-pops
  on tread (flag-gated for loop-safety; `once` true/false). Movement locks while the menu is open.

### Added — modern Field Editor look
- The form-based editor (`ff9mapkit edit`) now ships a cohesive theme: a flat `clam`-based palette
  that **matches your Windows light/dark setting** (with a safe light fallback), Segoe UI typography,
  an accent on the primary actions (Save / Build & Test), roomier tree rows, and a colour-tagged
  console log. No new dependency — the palettes + OS probe are pure-stdlib (`editor/theme.py`).

### Changed — provenance: the repo ships no Square Enix game data
- The blank field, exit-region template, and binary test fixtures are no longer committed. They are
  regenerated from the user's **own** FF9 install by the new **`ff9mapkit extract-templates`**
  command, into a local (gitignored) cache. The repo/wheel ship only our copy/insert **patches**
  (our edits + copy offsets) and a SHA-256 manifest — never game bytes. Verified airtight: no patch
  insert run ever duplicates a run in the source field; a built wheel contains zero game bytes.
- `doctor` now reports whether templates are extracted; the byte-level test suite skips cleanly (with
  a pointer to `extract-templates`) when they aren't, so a fresh clone still runs the pure-logic
  tests offline. See [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

Toward the first public **1.0**, remaining:
- Gallery screenshots (`docs/gallery/`).

## [0.9.3] — feature-complete, in-game-verified

The full custom-field pipeline, proven end to end in real gameplay. See
[`docs/FEATURES.md`](docs/FEATURES.md) for the complete capability list and
[`docs/TECHNICAL.md`](docs/TECHNICAL.md) for how the hard parts work. Highlights:

### Fields & camera
- Mint brand-new fields on a **stock Memoria** install (no engine fork).
- BG-borrow and fully-editable custom scenes.
- **Import / fork any of ~670 real fields** — camera, walkmesh, art, and (extracted from the script)
  exits, encounters, field BGM, and movement tuning.
- Author **any camera angle** from scratch; scrolling fields; multi-camera switch zones.

### Walkmesh & art
- Hand-model in Blender or import a real walkmesh; reshape multi-floor forks (seam-preserving).
- Pixel-accurate paint guide; depth layers; foreground occlusion; light/shadow blend layers.
- Build-time validation: reachability, content-on-mesh, near-edge, zero-area tris, seams, layer aspect.

### Content & scripting
- NPCs, custom dialogue, gateways, encounters (+ battle music), events (chests/gil/flags),
  story branching, and cutscenes (narration + actor walk/turn/emote/teleport). Save-persistent flags.

### Front-ends & engineering
- CLI, Blender add-on, form-based logic editor, build GUI; two-file (scene/logic) authoring.
- Byte-exact codecs (`.eb` / `.bgi` / `.bgx` / `.mes`); 254 kit + 47 Blender offline tests;
  opcode + projection math baked from Memoria source.

### Notes
- `0.9.x` unified the CLI and Blender add-on versions; the CLI was previously `0.1.0`.

[Unreleased]: https://github.com/
[0.9.3]: https://github.com/
