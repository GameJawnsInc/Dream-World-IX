# Journeys — multi-campaign arcs (design handoff → overworld / World-Hub lane)

> **Status:** design scaffold. The GUI (editor_gui lane) already *displays* journeys; the data model,
> the **assembler**, the **World-Hub generator**, and **deploy** are unbuilt and are the **overworld /
> World-Hub lane's** to own. This doc is the handoff: a concrete schema + the assembler's job list +
> the open decisions. Authored from the editor_gui lane (which only consumes journeys for display).
>
> **Lane split (per `project-ff9-branch-lanes`):** overworld owns the World Hub + player-rig; story_flags
> owns scenario/party/flag + is the composition owner for starting-state/New-Game. editor_gui only
> *surfaces* the hierarchy. A journey is overworld-lane data that **composes** story_flags' seed levers.

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

## 2. Proposed schema — `journeys.toml`

Lives at the **project root**, *above* the campaign folders it references (the GUI also accepts one
beside a `campaign.toml` for a single-campaign demo). All campaign refs are **folder names relative to
this file** (each folder holds a `campaign.toml`).

```toml
# journeys.toml -- playable arcs, each chaining one or more campaigns.

[[journey]]
name      = "Escape to the Ice Cavern"
id        = "escape_ice"                       # stable slug: hub-choice key + seed namespace
campaigns = ["evil_forest", "ice_cavern"]      # ORDERED; each is a folder with a campaign.toml
entry     = { campaign = "evil_forest", field = "EVF_START" }   # where the player begins
                                               #   field = a member NAME (preferred) or a raw field id

[journey.seed]                                 # starting story-state, applied at New Game -> this journey
scenario  = 0                                  # ScenarioCounter (story beat)
party     = ["Zidane", "Vivi"]                 # -> story_flags [party]
# inventory / equipment as the story_flags [startup] / [start_inventory] / [[equipment]] capstone allows

[[journey.link]]                               # how one campaign hands the player to the next
from = { campaign = "evil_forest", seam = "forest_exit" }   # a seam in evil_forest's campaign graph
to   = { campaign = "ice_cavern",  field = "IC_ENT" }       # the entry member of ice_cavern
```

Notes:
- **`campaigns`** is the spine — ordered, folder-relative. The GUI keys journey membership off it.
- **`entry`** is the New-Game landing inside the *first* campaign.
- **`[[journey.link]]`** is the cross-campaign hand-off. `from.seam` is an existing seam in that campaign's
  graph (kind overworld/portal/scripted/menu — see `campaign.campaign_graph`); the assembler **rewrites
  its target** to `to`'s field after id assignment. One link per campaign boundary; a 2-campaign journey
  has 1 link.
- **`[journey.seed]`** maps 1:1 onto the story_flags New-Game capstone (`[startup]`/`[party]`/
  `[start_inventory]`/`[[equipment]]`) — the assembler emits these onto the entry field, it does **not**
  invent a new seed mechanism.

---

## 3. Data model (suggested)

```
Journey   { id, name, campaigns: [folder], entry: Ref, seed: Seed, links: [Link] }
Ref       { campaign: folder, field: member_name | int }       # resolves to a global field id at assemble
Link      { from: {campaign, seam}, to: Ref }
Seed      { scenario: int, party: [name], inventory?, equipment? }   # == story_flags [startup] capstone
```

A `journeys.toml` parses to `[Journey]`. Keep it a pure, tk-free loader (mirror `campaign.load_campaign`)
so it's unit-testable headless.

---

## 4. The assembler's responsibilities (overworld lane — UNBUILT)

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

**Possible follow-up (editor_gui, optional):** extend the navigator so a journey root expands to **all its
campaigns** (load each `campaigns` folder's `campaign.toml`) → each campaign's fields. Today the navigator
shows one campaign at a time; a multi-campaign tree is a nav enhancement, not required for the breadcrumb.

---

## 6. Open decisions for the overworld lane

1. **`journeys.toml` location** — project root only, or also allow per-campaign (single-arc demo)? (GUI
   accepts both.)
2. **`entry.field` / link targets** — member **name** (stable, readable) vs raw **field id** (brittle to
   re-id). Recommend names; resolve to ids at assemble.
3. **The elided world-map leg** — is forest→cavern a bare `Field()` warp, or a tiny interstitial field
   (a black "…" transition / a save point)? The kit can't do a real overworld leg.
4. **Seed ownership** — confirm `[journey.seed]` simply *is* the story_flags capstone (no parallel
   mechanism), so story_flags stays the single composition owner.
5. **One mod folder per journey, or shared?** Distinct ids are required regardless; decide whether a
   journey gets its own `mod_folder` or stacks with others.
6. **Replay / one-way** — switching journeys is New Game today (`project-ff9-world-hub`); confirm.

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
