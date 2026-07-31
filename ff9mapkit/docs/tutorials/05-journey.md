# 05 — Assemble a journey

```toml
[tutorial]
goal = "Chain campaigns behind a World-Hub selector and wire New Game."
requires = ["game", "assets"]
```

A **journey** chains one or more campaigns into a playable arc behind a generated **World Hub** —
a selector field where New Game lands, the player picks a journey, its starting state is seeded,
and the warp fires. One `journeys.toml` declares all of it.

**Prerequisites:** at least one built campaign or verbatim fork
([tutorial 04](04-campaign.md) / [01](01-first-fork.md)). Schema reference:
[JOURNEYS.md](../JOURNEYS.md).

## 1. Write `journeys.toml`

The minimal form — a hub plus one journey per row (`entry` = a field id you deployed):

```toml
[hub]
name         = "WORLD_HUB"
id           = 4500
borrow_bg    = "GRGR_MAP420_GR_CEN_0"   # a real room as the backdrop (any area >= 10 field)
area         = 21
borrow_field = 950                      # the field the backdrop belongs to (camera source)
text_block   = 8                        # a real MesDB id not shadowed by a higher mod folder
prompt       = "Which journey will you take?"
stay_text    = "Stay here."             # the trailing cancel row
player_model = 220                      # walk the hub as a moogle

[[journey]]
id    = "ice"
name  = "The Ice Cavern"
entry = 4100                            # warp target: a campaign entry or a lone fork
set_scenario = 2600                     # optional story beat set right before the warp
```

Multi-campaign arcs add `campaigns = [...]`, `[[journey.link]]` rows (how one campaign hands off
to the next), and a `[journey.seed]` block (destination-side party / inventory / scenario
capstone) — the full arc form is in [JOURNEYS.md](../JOURNEYS.md#2-schema--journeystoml).

To scaffold FF9's real story arcs instead of writing rows by hand:

```powershell
ff9mapkit reference-arcs             # print the curated arc -> seed table
ff9mapkit reference-arcs --emit .    # write ./journeys.toml (a chained scaffold) + the fork playbook
```

## 2. Validate and generate the hub

```powershell
ff9mapkit lint-journey journeys.toml       # id/flag disjointness, links resolve, entries valid
ff9mapkit assemble-journey journeys.toml   # lint + emit the World-Hub field.toml
```

`lint-journey` enforces the namespace guarantee — every field id, story-flag band, and text block
distinct across all member campaigns (the engine's registries are global).

## 3. Deploy

```powershell
ff9mapkit deploy-journey journeys.toml                            # dry-run: prints the full playbook
ff9mapkit deploy-journey journeys.toml --apply --newgame hub      # install + wire New Game to the hub
```

The deploy installs every member campaign, applies the links, and builds and installs the hub.
New Game is only wired with `--newgame hub` (or `--newgame entry` to skip the menu and land
straight in the first journey); a plain `--apply` leaves New Game untouched. Register the printed
mod folder(s) in `Memoria.ini [Mod] FolderNames` **and** `Priorities`, same order (the launcher
rewrites `FolderNames` from `Priorities`; a single-folder merge is available — the deploy
output names the option) and relaunch.

From a repo checkout, `py tools\deploy_journey.py` is the same orchestration.

## 4. Verify

New Game → the hub field → the selector menu lists each journey → picking one seeds its state and
warps to its entry field. `ff9mapkit newgame <id>` can re-point New Game later without a
re-deploy.

## Next

- The GUI does this whole flow, including bulk-forking the regions: [07 — Fork FF9 in the Workspace](07-gui-journey.md)
- Journey-scope story flags and seeding layers: [JOURNEYS.md](../JOURNEYS.md)
