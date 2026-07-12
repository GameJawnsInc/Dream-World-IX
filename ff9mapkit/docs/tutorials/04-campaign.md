# 04 — Fork a region into a campaign

`import-chain` walks FF9's door graph from a seed field and forks the whole connected slice —
fields, gateways, encounters, music — into one multi-field mod with a single `campaign.toml`.
This example forks the Ice Cavern (fields 300–311; 312 sits in the next zone and is reported as
an exit seam).

**Prerequisites:** the kit set up with UnityPy ([SETUP.md](../../../SETUP.md)).

## 1. Dry-run the walk

```powershell
ff9mapkit import-chain 300 --zones iccv --max-fields 20 --dry-run
```

Prints the adjacency list before anything is written: the member fields, the spine and branches,
story-flag gating, termini (worldmap exits), and seams that cross out of the selected zone.

Scoping levers:

- `--zones <codes>` — stay inside the named zone(s).
- `--whole-zone` — the seed's entire zone.
- `--ids <ranges>` (e.g. `--ids 100-117`) — an exact id set. A place's story revisits are separate
  id clusters sharing one zone, so this scopes the fork to **one story-state visit**. The region
  catalog (the Workspace's *Browse FF9 regions…* picker, backed by `data/region_catalog.toml`) is
  organized this way.
- `--verbatim` — fork each member with its real script and text (see [tutorial 01](01-first-fork.md)).

## 2. Fork

```powershell
ff9mapkit import-chain 300 --zones iccv --id-base 4100 --campaign-name ICE_CAVERN --out campaign\ice
```

Writes one project directory per member (`campaign\ice\IC_*\`), each a normal single-field project,
plus `campaign\ice\campaign.toml` — the manifest with members, retargeted in-chain gateways, and
the seams left to author. In-chain doors already point at the new ids.

## 3. Edit members

Each member's `field.toml` is editable exactly as in tutorials [01](01-first-fork.md)/[03](03-original-art-field.md):
add NPCs, chests, a `[[savepoint]]`, retarget the printed seam gateways (exits that led outside
the forked slice), repaint editable layers. Campaign-scoped story flags go in `campaign.toml`
(see [FORMAT.md](../FORMAT.md#story-flags--branching)).

## 4. Build and validate

```powershell
ff9mapkit lint-campaign campaign\ice\campaign.toml
ff9mapkit build-all campaign\ice\campaign.toml --out dist\ice
```

`build-all` compiles every member into **one** mod folder: a single `DictionaryPatch` with all the
field ids, a merged `BattlePatch`, and a `ModDescription.xml`. Cross-field lint verifies every
edge resolves, ids are distinct and ≥ 4000, and text blocks don't collide.

## 5. Deploy and wire New Game

```powershell
ff9mapkit deploy-campaign campaign\ice\campaign.toml --mod-folder FF9CustomMap-ice --entry IC_ENT
ff9mapkit deploy-campaign campaign\ice\campaign.toml --mod-folder FF9CustomMap-ice --entry IC_ENT --apply
```

Member names derive from the FBG map token (`fbg_n05_iccv_map085_ic_ent_0` → `IC_ENT`); omitting
`--entry` uses the manifest's entry. Dry-run first (the default) — it prints the full plan.
`--apply` snapshots the target folder, installs the campaign, re-points New Game at the entry
field, and writes a revert script. On a clean install with no existing New Game override the
deploy warns instead — create one once with
`ff9mapkit newgame <entry field id> --mod-folder FF9CustomMap-ice`; later deploys re-point it.
(From a repo checkout, `py tools\deploy_campaign.py` is the same deploy.)

Add the mod folder to `Memoria.ini [Mod] FolderNames` **and** `Priorities` (same order — the
launcher rewrites `FolderNames` from `Priorities`) and relaunch once so the new ids register.
New Game now lands on the entry field; with the engine bundle, **F6 → Go → Warp** reaches any
member directly thereafter.

## Next

- Chain several campaigns into a selectable arc: [05 — Assemble a journey](05-journey.md)
- What a fork does and doesn't reproduce: [FORK_FIDELITY.md](../FORK_FIDELITY.md)
