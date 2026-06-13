# Journeys — multi-campaign arcs (design handoff → overworld / World-Hub lane)

> **Status (updated 2026-06-13):** schema **ADOPTED** by overworld; the GUI's forward-compat display held
> (no change needed — the only `_journey_label` touch-point was never hit). **`gen-hub` is BUILT + shipped**
> — the single-field / single-campaign form (a bare-int `entry` + a `[hub]` table + a hub-side
> `set_scenario`); two journeys ship (Dali → field 4100, Treno → field 4501, both verbatim fields). The
> **multi-campaign assembler** (`campaigns` / `[[journey.link]]` / `[journey.seed]`)'s **OFFLINE CORE is now
> BUILT** (`ff9mapkit/journey.py` + `lint-journey`/`assemble-journey` — load/resolve/lint/hub-emit; see §9);
> only the in-game **deploy** step (`deploy_journey`) remains. overworld's to own. This doc is the shared
> schema + the assembler's job list.
>
> **Lane split (per `project-ff9-branch-lanes`):** overworld owns the World Hub + `gen-hub` + the assembler
> + player-rig; story_flags owns scenario/party/flag + is the composition owner for starting-state/New-Game.
> editor_gui only *surfaces* the hierarchy. A journey is overworld-lane data that **composes** story_flags'
> seed levers.

---

## 1. Concept

A **journey** is a complete playable arc = **one or more chained campaigns**, picked at the World Hub.
Today a `campaign.toml` (`import-chain`) is a connected slice of fields; a journey sits **one level up**:
it names an ordered set of campaigns, says where the player **starts**, seeds the **starting story state**,
and defines how each campaign **hands off** to the next.

Worked example — **Evil Forest → Ice Cavern** (consecutive in FF9: escape the forest → world map → the
cavern). As a single journey, the inter-campaign world-map segment is **elided** to a direct field warp
(custom overworld is the hardest-unbuilt thing — `project-ff9-worldmap-feasibility`; a journey chains
campaigns by a `Field()` warp from one campaign's exit to the next's entry, not by a real overworld leg).

Two shapes the hub can offer (both valid; the schema covers both):
- **A — separate journeys:** the hub menu lists *Evil Forest* and *Ice Cavern* as two pickable arcs (each
  one campaign). This already fits a 1-campaign journey.
- **B — one chained arc:** a single *"Escape to the Ice Cavern"* journey that plays Evil Forest then hands
  off into Ice Cavern. **This is the new model below.**

---

## 2. Schema — `journeys.toml`

A `journeys.toml` is a **`[hub]` table** (how the selector field presents) plus one or more
**`[[journey]]`** rows. There are **three journey forms, simplest first — `campaigns` is NOT mandatory**:

| Form | `entry` | What it is | Who builds it |
|---|---|---|---|
| **Single field** | `entry = <field id>` (bare int) | one verbatim field (the shipped Dali 4100 / Treno 4501) | `gen-hub` — **BUILT** |
| **Single campaign** | `entry = <field id>` of a member | one `campaign.toml` slice | `gen-hub` — **BUILT** |
| **Multi-campaign arc** | `entry = { campaign, field }` + `campaigns = [...]` | chained campaigns | the **assembler** — offline core BUILT (§9); deploy next |

```toml
# journeys.toml -- the World-Hub registry.  `ff9mapkit gen-hub journeys.toml` emits the selector field.

[hub]                                  # how the selector field itself presents (gen-hub consumes this)
name         = "WORLD_HUB"
id           = 4500
borrow_bg    = "GRGR_MAP420_GR_CEN_0"  # a real room as the backdrop (any area >= 10 field)
area         = 21
borrow_field = 950                     # the real field this room IS (gen-hub --extract-camera caches its camera)
camera       = "camera_hub.bgx"
text_block   = 8                       # a real MesDB id NOT shadowed by a higher mod folder (1073 IS)
prompt       = "Kupo! Which journey will you take?"
stay_text    = "Stay here, kupo..."    # the trailing no-warp (cancel) row
player_model = 220                     # walk the hub as a Moogle (220 = the save moogle)
player_spawn = [404, 127]
narrator       = "Stiltzkin"
narrator_model = 212                   # Stiltzkin's real rig (GEO_NPC_F3_MOG)
narrator_pos   = [480, 127]
# entry_settle = true                  # optional: hide the smooth-cam warp-in ease (entry camera-settle)

# --- the SHIPPED form: one row per journey, a bare-int entry + an optional hub-side beat ---
[[journey]]
id    = "dali"                         # stable slug (hub-choice key + seed namespace)
name  = "The Village of Dali"          # the pretty menu label
entry = 4100                           # a FIELD ID -- warp straight here (a verbatim fork OR a campaign entry)
set_scenario = 2600                    # HUB-SIDE beat, set on the row right before the warp (gen-hub uses this)

# --- the multi-campaign ARC form (assembler offline core BUILT; deploy next): campaigns + links + a seed ---
[[journey]]
id        = "escape_ice"
name      = "Escape to the Ice Cavern"
campaigns = ["evil_forest", "ice_cavern"]                       # ORDERED folders, each with a campaign.toml
entry     = { campaign = "evil_forest", field = "EVF_START" }   # member NAME (preferred) or field id
set_scenario = 0                                                # optional hub-side beat (coexists w/ the seed)

  [journey.seed]                       # DESTINATION-SIDE story_flags capstone the assembler applies on arrival
  scenario  = 0                        #   (a SEPARATE layer from the row's hub-side set_scenario)
  party     = ["Zidane", "Vivi"]       #   -> story_flags [party]
  # inventory / equipment per the [startup] / [start_inventory] / [[equipment]] capstone

  [[journey.link]]                     # how evil_forest hands the player to ice_cavern (the elided world-map leg)
  from = { campaign = "evil_forest", seam = "forest_exit" }     # a seam in evil_forest's campaign graph
  to   = { campaign = "ice_cavern",  field = "IC_ENT" }         # the entry member of ice_cavern
```

**The two seed layers coexist — they are NOT one, and don't conflict:**
- **`set_scenario`** (flat, on the `[[journey]]` row) — the **hub-side** beat set on the selector field
  right *before* the `Field()` warp. This is what **`gen-hub` uses** today (cheap, one value).
- **`[journey.seed]`** (`scenario`/`party`/inventory) — the **destination-side** story_flags **capstone**
  the **assembler** applies on arrival into the arc (richer: party/bag/gear). A journey may set **both**:
  a hub-side beat to enter on, and a fuller capstone once inside.

**Locations:** a **project-root** `journeys.toml` (above campaign folders, for arcs) OR one beside a
`campaign.toml` / in the world_hub dir (the shipped single-field/campaign journeys). The GUI reads both.

**`[[journey.link]]`** (arc form only) is the cross-campaign hand-off: `from.seam` is an existing seam in
that campaign's graph (kind overworld/portal/scripted/menu — `campaign.campaign_graph`); the assembler
**rewrites its target** to `to`'s field after id assignment. One link per campaign boundary.

---

## 3. Data model (suggested)

```
Hub       { name, id, borrow_bg, area, borrow_field, camera, text_block, prompt, stay_text,
            player_model, player_spawn, narrator, narrator_model, narrator_pos, entry_settle? }
Journey   { id, name, entry: int | Ref, set_scenario?: int,        # set_scenario = HUB-SIDE beat (gen-hub)
            campaigns?: [folder], seed?: Seed, links?: [Link] }    # the ?-marked fields = the ARC form only
Ref       { campaign: folder, field: member_name | int }          # resolves to a global field id at assemble
Link      { from: {campaign, seam}, to: Ref }
Seed      { scenario, party, inventory?, equipment? }             # DESTINATION-SIDE story_flags capstone
```

A `journeys.toml` parses to `{ Hub, [Journey] }`. The single-field/campaign form (bare-int `entry`,
optional `set_scenario`) is what `gen-hub` reads today; the `?`-marked `campaigns`/`seed`/`links` are the
unbuilt arc form. Keep it a pure, tk-free loader (mirror `campaign.load_campaign`) so it's headless-testable.

---

## 4. The assembler's responsibilities (overworld lane — offline core BUILT; deploy next; see §9)

> The **single-field / single-campaign** path is already shipped by **`gen-hub`** (it reads `[hub]` + each
> `[[journey]]`'s bare-int `entry` + hub-side `set_scenario` and emits the selector field). This section is
> the **multi-campaign assembler** — the part that turns `campaigns = [...]` + `[[journey.link]]` +
> `[journey.seed]` into a deployable chained arc.
>
> **Status (2026-06-13):** the OFFLINE half of this list is BUILT in `ff9mapkit/journey.py` (#1 id-band
> disjointness — validated globally; #2 flag-window assignment — computed; #3 link *resolution* of src/dst →
> global ids; #5 hub emit; #7 the full journey lint). The IN-GAME half remains as `deploy_journey` (#3 the
> actual `.eb` warp *rewrite*, #4 seed application + CSV promotion, #6 deploy orchestration). Detail in §9.

A `build_journey(journey, out)` / `deploy_journey(...)` that orchestrates the existing per-campaign tools.
The hard parts are **global-namespace** ones (EventDB/SceneData are global — distinct ids required even
across mod folders):

1. **Disjoint id bands.** Each campaign already takes `id_base, +1, +2, …` (`assign_ids`). Across a
   journey, the assembler must hand each campaign a **non-overlapping** band (custom 4000–9899, or scratch
   30000–32767; Int16 cap 32767). Reuse `campaign.validate_ids` per campaign + a cross-campaign overlap
   check.
2. **Disjoint flag bands.** Campaigns allocate `flags_per_field` flags from `flag_base` (`FIRST_SAFE_FLAG`,
   safe band ≥ 8512). The assembler must give each campaign a non-overlapping flag window so two campaigns
   in one journey don't clobber each other's `gEventGlobal` bits.
3. **Cross-campaign link resolution.** After id assignment, rewrite each `[[journey.link]].from` seam's
   target to the assembled global field id of `to`. This is the "forest_exit → IC_ENT" warp. (A seam whose
   target is in *another* campaign is exactly what a single campaign's graph can't express today — it's the
   journey layer's job.)
4. **Seed application.** Emit `[journey.seed]` as the story_flags New-Game capstone on the entry field
   (`[startup]`/`[party]`/…), and promote the start-state CSVs to the highest mod folder
   (`deploy_campaign` already does CSV promotion + aborts on cross-folder EVT/FBG name collision —
   `--allow-name-collision` to override; reuse that).
5. **World-Hub generation.** Emit the hub field's `[[choice]]` rows — one per journey — each
   `warp = <journey entry global id>` + the seed (`set_scenario` / party). Per journey the hub needs only
   `{name, entry id, seed}` (`project-ff9-world-hub`). Then retarget New Game (field-70 override) → the hub.
6. **Deploy orchestration.** `deploy_campaign` each member campaign reversibly into the mod folder
   (disjoint ids), deploy the hub, wire New Game. Use `import-chain --name-prefix` to keep FBG/EVT names
   from colliding across campaigns (cross-worktree namespace).
7. **Journey lint.** Campaigns exist + parse; id bands disjoint; flag bands disjoint; every
   `[[journey.link]].from.seam` resolves to a real seam and `to` to a real member; `entry` is valid; the
   seed is range-checked (scenario/party/items). Mirror `campaign.lint_campaign`'s shape `(errors, warnings)`.

---

## 5. The GUI display contract (editor_gui lane — DONE, forward-compatible)

The Campaign Editor already **displays** a journey when one exists (it does **not** author them):

- It reads a `journeys.toml` **beside** the open `campaign.toml` *and* **one level up** (project root).
- A journey **matches the open campaign** when the campaign's **folder name is in `campaigns`** (the
  multi-campaign form) **or** its `entry` field id names one of the campaign's members (single-campaign).
- On a match, the breadcrumb shows `◆ <journey name> ▸ ▣ <campaign> ▸ ● <field> ▸ ▸ <object>` and the
  navigator nests the campaign under a journey root. No match → honest `campaign ▸ field ▸ object`.

So the instant overworld writes a `journeys.toml` in this schema, the GUI lights up — **no GUI change
needed** beyond what's shipped. If the schema's field names change, the only GUI touch-point is
`Workspace._journey_label()` in `apps/campaign_editor.pyw` (one method).

> **Validated (2026-06-13):** overworld adopted the schema and the GUI lit up with **zero changes** — the
> `_journey_label()` touch-point was never hit. The bare-int `entry = <field id>` form (the shipped Dali
> 4100 / Treno 4501 journeys) is matched by `entry in member_ids` and is already smoke-tested; the
> `campaigns`-list form is matched by folder name. All three journey forms display today.

**Possible follow-up (editor_gui, optional):** extend the navigator so a journey root expands to **all its
campaigns** (load each `campaigns` folder's `campaign.toml`) → each campaign's fields. Today the navigator
shows one campaign at a time; a multi-campaign tree is a nav enhancement, not required for the breadcrumb.

---

## 6. Decisions — resolved by the shipped `gen-hub`, vs still open for the assembler

**Resolved (gen-hub, shipped):**
- **`journeys.toml` location** — both: a **project-root** file for arcs, or the **world_hub dir** for the
  shipped single-field journeys. The GUI reads both.
- **`entry` form** — a **bare field id** is the shipped form (single field / campaign). For arcs,
  `entry = { campaign, field }` with a member **name** (resolved to an id at assemble).
- **Seed layers** — confirmed **two**: `set_scenario` (hub-side, gen-hub) + `[journey.seed]` (destination
  capstone, assembler). story_flags stays the single composition owner of the capstone.

**Resolved by the assembler's offline core (2026-06-13; full rationale in §9):**
- **The elided world-map leg** — a bare cross-campaign `Field()` warp (the `[[journey.link]]`, realized at
  deploy time); no interstitial field for now. The link `from` names the boundary member (`field`, alias
  `seam`); lint flags a source with no out-of-chain seam.
- **One mod folder per journey, or shared?** Each campaign keeps its own `mod_folder` (from its
  `campaign.toml`); the assembler stacks them via `FolderNames` (as the shipped -sf / -ow journeys do). The
  hub owns the highest folder + New Game.
- **Replay / one-way** — one-way; New Game switches journeys (confirmed).

---

## 7. Prerequisites — you need the campaigns first

A journey references real campaigns. **Ice Cavern exists**; **Evil Forest must be forked**:

```bash
# from the kit root (ff9mapkit/) -- needs UnityPy + the game install
py -m ff9mapkit import-chain <evil-forest-seed-field>   # forks a connected slice into one campaign.toml
# find the seed field id:  py -m ff9mapkit list-fields evil
```

Then a minimal `journeys.toml` at the project root referencing both folders (§2) drives the assembler.

---

## 8. Cross-lane seams (collision rules)

- **overworld** owns this model + the assembler + the hub + the field-70 New-Game retarget.
- **story_flags** owns the seed levers (`[startup]`/`[party]`/scenario/flags) the seed composes — don't
  fork a parallel seed path.
- **editor_gui** owns only *display* (§5).
- **Global namespace:** EventDB/SceneData/flag bands are global — the assembler is the *only* place that
  can guarantee disjoint id + flag bands across a journey's campaigns. That guarantee is the whole job.
```

(handoff authored from editor_gui; ship/merge per the FF-master discipline. Related: `project-ff9-world-hub`,
`project-ff9-new-game-entry`, `project-ff9-branch-lanes`, `project-ff9-worldmap-feasibility`.)

---

## 9. Implementation status (overworld lane — the OFFLINE CORE is BUILT)

`ff9mapkit/journey.py` + CLI `lint-journey` / `assemble-journey` implement the **offline assembler core** —
the §8 namespace guarantee, fully unit-testable with no game install (`tests/test_journey.py`, 26 tests).
The in-game **deploy orchestration** (build each campaign at its band, realize each link as a live warp,
deploy the hub, wire New Game) is the remaining step — scoped below, deferred because it's human-playtested
(Hard Constraint §2). The schema is unified with overworld's proven single-field hub journeys.

**The unified `journeys.toml`** — one file, `[hub]` (presentation, `ff9mapkit.hub`'s schema) + `[[journey]]`
rows that are **either** a *bare* single-field journey (overworld's proven floor — `entry = <field id>`,
optional `set_scenario`) **or** the *multi-campaign* shape from §2 (`campaigns` / `entry = {campaign, field}`
/ `[journey.seed]` / `[[journey.link]]`). `gen-hub` builds **only** the bare rows (rejects multi-campaign);
`assemble-journey` resolves **both** (a bare row = the degenerate zero-campaign journey) and folds
`hub.render_hub_field_toml` in as its hub-emit step — one renderer, both paths.

**Built (offline, no game):**
- `load_journeys` — pure tk-free loader (mirrors `campaign.load_campaign`): `JourneyManifest{hub, journeys}`,
  `Journey{id, name, campaigns, entry: JourneyRef, seed: JourneySeed, links: [JourneyLink], set_scenario}`.
- `resolve_journey` / `load_campaign_plans` — resolve entry/link member names → **global field ids**, assign
  each campaign a **disjoint flag window** (laid end-to-end from `FIRST_SAFE_FLAG`).
- `lint_manifest` — **the namespace guarantee**: every referenced campaign exists + parses + passes
  `lint_campaign`; **global id-disjointness** across every campaign of every journey + bare entries (one
  EventDB/SceneData namespace — all registered at launch, so a collision is a hard launch failure regardless
  of which journey is picked); per-journey flag windows fit below `CHOICE_SCRATCH_FLOOR`; links resolve to
  real members + flag a non-boundary source; chain connectivity; entry valid; seed range-checked.
- `manifest_to_hub_spec` / `generate_hub` — emit the hub field.toml for bare + multi-campaign journeys.
- `render_journey_plan` — the read-only resolved view (`lint-journey --graph`).

**The §6 open decisions, resolved (overworld's call):**
1. **Location** — project root, campaign folders **relative to the journeys.toml** (`manifest.root`). A
   single-campaign demo beside its `campaign.toml` also works (folders are relative either way).
2. **Targets** — member **NAME** preferred (resolved to a global id at assemble); a raw id is accepted but
   lint **warns** (brittle to re-id).
3. **Elided world-map leg** — a bare cross-campaign `Field()` warp (the link, realized at deploy time); no
   interstitial field for now. The link `from` names the **boundary member** (key `field`, alias `seam`);
   lint flags a source with no out-of-chain seam (nothing to retarget — the deploy injects a fresh warp).
4. **Seed** — `[journey.seed]` **IS** the story_flags capstone (the whole table is carried verbatim as
   `JourneySeed.raw`); no parallel mechanism. The hub also seeds `scenario` so the select path lands on the
   right beat.
5. **Mod folders** — each campaign keeps its own `mod_folder` (from its `campaign.toml`); the assembler
   stacks them via `FolderNames`. The hub owns the highest folder + New Game (`project-ff9-world-hub`).
6. **Replay** — one-way; New Game switches journeys (confirmed).

**Remaining — the in-game deploy step (`deploy_journey`, next):** per-campaign `deploy_campaign --no-warp`
at each disjoint band (applying the assigned `flag_base` via a `build_campaign` override); realize each link
by byte-patching the boundary member's `.eb` `Field()` exit → the next campaign's entry global id (reuse
`gateway.graft_gateway_entry` / `retarget_newgame_warp`'s 0x2B scanner); emit + deploy the hub; seed the
entry field (the story_flags capstone) + promote start-state CSVs to the highest folder; retarget New Game
→ the hub. Each is human-playtested. **Prerequisite (§7): fork Evil Forest** (`import-chain`) for the worked
two-campaign example (Ice Cavern exists).
