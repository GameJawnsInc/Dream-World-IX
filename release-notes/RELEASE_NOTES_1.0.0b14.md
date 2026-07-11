# Dream World IX 1.0.0b14 — Battle balance rules, a hand-built continent, and Chocobo Hot & Cold

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* content — and faithfully forking the real game — for the [Memoria engine](https://github.com/Albeoris/Memoria) (Steam/GOG FF9). This release adds a declarative battle-balance rules engine, closes the last gaps in custom overworld authoring (the first fully custom continent, cliff and beach reshaping, a closed shore-tile vocabulary), and reopens the Chocobo Hot & Cold minigame for custom prizes — 183 commits and 3283 passing tests since b13, all DLL-free.

> Scale every enemy's HP for a hard-mode run, give the party a second-wind revive, dig up your own Chocobo Hot & Cold prizes, and sail out to a brand-new island chain built entirely from real FF9 coastline — no engine rebuild required.

## What's new since v1.0.0b13

### ⚔️ Battle balance & rules (the Overload gameplay hub)

A new architecture for hooking the engine's battle-calculation callbacks hosts three declarative, flag-toggleable gameplay features — no `Assembly-CSharp` rebuild.

- **`[difficulty]`** scales every enemy once per battle — `enemy_hp` / `enemy_attack` / `enemy_magic` (0.05–20.0), players untouched — with an optional `flag` gate so a journey can switch hard mode on/off at runtime (toggle live with F6 → Flags; takes effect next battle).
- **`[rebalance]`** scales the final HP-damage number by the caster's side — `player_damage` / `enemy_damage` — the only way to scale what the *party* deals; composes with `[difficulty]`. Takes effect live, mid-battle (the 9999 cap needs `Memoria.ini [Battle] BreakDamageLimit = 1`).
- **`[deathrules]`** owns the party-wipe verdict: `second_wind` cancels a wipe once per battle with a full Phoenix-party revive (queued exactly like the vanilla Eiko default, recharging each battle), with an optional `chance` roll and `keep_rebirth_flame = false` for a hardcore mode with no auto-revive at all. Fail-safe by construction — any hiccup is a normal defeat, never a canceled wipe with nobody revived.
- Discovered here: **the GRANULARITY LAW** — a flag-gated feature's toggle latency equals its hook's fire cadence. `[rebalance]` rides a per-hit hook (flips live mid-fight); `[difficulty]` rides a per-battle hook (takes effect next fight). Same gate mechanism, different granularity, depending on where in the engine it hooks in.
- *In-game proven (2026-07-11)* — `[difficulty]` ×2 HP confirmed byte-exact via telemetry (Fang 68→136, Goblin 33→66); `[rebalance]` 2×/0.5× confirmed both directions; `[deathrules]` wipe → Phoenix revive → second wipe → normal game over → next battle recharged. See [SCRIPTS_DLL.md §12](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/SCRIPTS_DLL.md).

### 🥚 Chocobo Hot & Cold — custom dig prizes

Author your own prize/timer lane for the Chocobo's Forest treasure-hunting minigame on a faithfully forked forest.

- A new declarative `[chocobo]` block sets the dig prizes and timer tuning for a `--verbatim` forest fork — no hand-patched `.eb`, a purpose-built expression-literal edit primitive under the hood.
- *In-game proven on all three Chocobo Forests (2026-07-10)* — Elixir Forest / Phoenix Down Forest / Magic Tag Forest each redeployed with a custom prize and confirmed matching pop-up text to actual item given, every time.
- The F6 debug menu's Flags tab gained a **BATCH operator** (bit/byte/word story-flag operations in one click, with named presets) to warp straight into a chocobo dig without manually walking there each test.

### 🏝️ The first hand-built continent, and a closed shore vocabulary

Custom overworld authoring reaches its capstone this release: a fully composed, multi-island continent built entirely from real FF9 coastline, plus the tools to reshape any coast — cliffs, beaches, and growth — by hand.

- **The first custom continent** — four real, verbatim-carried FF9 islands (a cliff/highland island, a shore/shallow-water island, a real sandy beach, and Uaho — FF9's own air-only islet) fused into one seamless archipelago in open ocean via `world-fuse`, deployed and walked in-game with zero seams at any shared border. The layout ships as a worked example (`ff9mapkit/examples/continent-v1/`).
- **The coast-morph pillar** — reshape any verbatim-transplanted coastline in place: cliff bumps, structural headlands, bays, and multi-lobe combinations (`--cliff-bump`/`-headland`/`-bay`/`-lobes`); full beach reshaping and sliding (`--beach-reshape`/`--beach-slide`) that moves the whole sand/foam/waterline assembly as one unit; and `--in-place` morphs that reshape the REAL, already-shipped map coastline directly, no carrying required. A new `world-morphs` scanner catalogs 324 lawful morph windows map-wide (ready-to-run deploy commands included).
- **The shore tile vocabulary is now closed** — the sand band and foam end-caps are fully byte-learned and regeneratable from scratch (`sand_rebuild` / `cap_rebuild`), closing the last gap in FF9's coastal tile language. `--beach-mint` re-mints a real beach's sand+foam assembly from a chain spec at any width, including its own synthetic land chain — the first fully kit-authored (not just carried) beach.
- Underlying growth machinery landed too: `world-transplant --size NxM` carries a multi-cell verbatim landmass as one rigid assembly; `RowInsert`/`chain_row_inserts` grow an island by inserting real lattice columns; `spill-clip` unlocks growth using an empty neighboring cell's water as slack.
- *In-game proven throughout July 2026* — the continent (2026-07-09), the coast-morph rungs (2026-07-09 through 2026-07-10), the shore-vocabulary closure (2026-07-11). See the overworld skill/memory for the full 115-law reference.

### 🗿 Battle-model export gap closed

Every alias id a real FF9 character's battle form can take now exports, previews, reskins, and deploys engine-faithfully.

- `extract.resolve_prefab` replays the engine's own alias-resolution chain (boss forms, alternate outfits, F1 field-avatar aliases) so all 71 shipped alias ids — not just the 84 primary character/enemy models — round-trip through the custom-model pipeline; the 43 truly-unshipped ids now refuse with an actionable message instead of a wrong export.
- **Bone display labels** — `model-gltf`'s exported skeleton now carries anatomical names (`bone012_R_hand` instead of a bare index) for 83% of FF9's bones, derived from family-clustered rest-pose heuristics; `--plain-bones` opts back out. Makes hand-editing a skinned mesh in Blender dramatically easier to navigate.

### 🖼️ Image-to-field improvements

The experimental `image-field` command (turn any picture into a walkable FF9 room) gained the pieces that make it usable on a real photo, not just a synthesized test image.

- `--auto-floor` automatically detects the walkable floor region (a refusal-biased seeded region grow) instead of requiring a hand-traced polygon, and pre-loads the browser-based `--trace` tool for manual correction.
- Anchored occluders now depth-sort correctly against the player character (a foreground cut-out's Z is set to the actor's own depth at its floor contact point), so walking behind an object correctly hides behind it.
- A full-resolution cover-crop fix sharpens the deployed background (earlier builds shipped a softened image) — rebuild any pre-existing `image-field` project to pick it up.
- *In-game proven on a real photograph (2026-07-09)* — the user's own hallway, traced and deployed as a walkable field.

### 🎛️ Engine & F6 debug menu

- The F6 debug menu's Flags tab gained the **BATCH story-flag operator** (bit/byte/word operations, all-or-nothing, named presets) — see Chocobo Hot & Cold above.
- New overworld **vehicle-mode and disc-switch tooling** in F6's Go tab, reverse-engineered from the dispatcher tables.
- The Position readout now leads with the **canonical wrapped coordinate triple** every kit tool actually speaks (`world (x,z) · block [x][y] · cell (x,z)`) instead of the engine's raw unwrapped position, ending a recurring coordinate-confusion class of bug.

## Engine bundle

**The b14 public engine bundle is UNCHANGED from b12/b13** — same fork-fidelity patch set (**s23–s33**) plus the **s34** overworld mesh-override plus the F6 in-game debug menu, shipped as `dwix-custom-memoria-*.zip`.

- **If you already have the b12 or b13 engine, you do NOT need to re-download it.** Every b14 pillar above is either DLL-free or runs on the existing bundle (the continent/coast-morph/chocobo work all reuses the already-shipped s34 override).
- A newer overlay-texture-cache patch (**s35**) and an F6 diagnostic addition exist in the patch set but are not yet in this public bundle — held for a future from-source engine rebuild, same as the b13 → b14 gap. Nothing in this release depends on them.
- A **novel** (from-scratch / BG-borrow) field runs on **stock Memoria**, as do most of this release's headline pillars.
- A **forked** field, and the overworld synthesis/reshape commands, need the shipped s23–s34 suite (all present in the unchanged bundle).

## Getting started

- **Windows:** grab the installer `.exe` from the release assets — it bootstraps everything, and can optionally install the engine patches (backed-up, version-aware).
- **From PyPI:** `uv tool install "ff9mapkit[gui,assets,save]"` then `ff9mapkit setup` (detects your FF9 install, saves config, extracts base templates, and reports Memoria status).
- **Already installed?** `uv tool upgrade ff9mapkit`.
- Full walkthrough, prerequisites, and the CLI reference: [SETUP.md](../SETUP.md).

## Provenance

Dream World IX ships **NO** FINAL FANTASY IX game data. It operates only on a copy of the game **you** already own, reading and patching your local install at build time. Base templates are regenerated from your own install via `ff9mapkit extract-templates`; no Square-Enix bytes are distributed. This is an unofficial, fan-made toolkit and is **not affiliated with, endorsed by, or associated with Square Enix**.

## License

Dream World IX / `ff9mapkit` is released under the **MIT License** (© 2026 GameJawnsInc). The bundled engine patches modify [Memoria](https://github.com/Albeoris/Memoria), which is likewise MIT-licensed (© Albeoris).
