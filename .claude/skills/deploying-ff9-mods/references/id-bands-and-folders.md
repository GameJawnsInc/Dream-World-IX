# Id bands & mod folders — lookup

Lookup tables for the deploy loop. The layout facts themselves are OWNED elsewhere — CLAUDE.md §3
(the one-breath summary) and memory [[project-ff9-git-layout]] (the deep recipe, which absorbed the
old `project-single-repo-mode` memory). This file deliberately does NOT re-copy §3: a verbatim quote
rots the moment §3 is edited, which is exactly what happened to the copy that used to live here.

## The layout in three facts (the ones this skill actually needs)

- **The deploy target is pinned per checkout** in a gitignored `.ff9deploy.toml` (`mod_folder` +
  a scratch-band `id`); override with `--mod-folder` / `$FF9_MOD_FOLDER`.
- **`Memoria.ini [Mod] FolderNames` stacks the mod folders**, and each folder's OWN
  DictionaryPatch/BattlePatch is read at launch (reorder rules: THE LAUNCHER LAW, below).
- **Distinct ids are required even ACROSS folders** — EventDB/SceneData are GLOBAL, so the same id
  in two stacked folders collides into a null `.eb`. That same stacking causes the `.mes` shadow.

## Field-id bands

| Band | Meaning |
|---|---|
| 10-3100 | real FF9 fields (locked) |
| 4000-9899 | shipped custom content (100-id blocks; `pack.suggest_base`) |
| 9000-9012 | RESERVED hole inside the custom range — the engine's world-map location ids; a `FieldScene` here clobbers the world scripts |
| 30000-32767 | ephemeral dev/test scratch slots |
| above 32767 | registers but unreachable (`fldMapNo` is Int16) and can break the DictionaryPatch parse |

The 9000-9012 rule, verbatim from memory `project-ff9-eventdb-id-collision`: "The custom field band
(4000-32767) MUST treat 9000-9012 as a hole." (`journey.lint_manifest` hard-errors ids in the band.)

## Mod folders (VERIFIED against the install 2026-07-24)

Two sources of truth, and neither is this table: **`.ff9deploy.toml`** says what THIS checkout
deploys into; the **install directory + `Memoria.ini [Mod] FolderNames`** say what actually exists
and in what order. Both were read on 2026-07-24 and the install contains exactly these four:

| Folder | Role | Scratch id |
|---|---|---|
| `FF9CustomMap` | the master / default deploy target — fields, campaigns, the New-Game field-70 override | 30000 |
| `FF9CustomMap-world` | the dedicated OVERWORLD target (`--mod-folder FF9CustomMap-world`); kept separate because campaign deploys wholesale-replace `FF9CustomMap` | — |
| `MoguriMain`, `MoguriVideo` | third-party (Moguri); must stay BELOW `-world` (THE LAUNCHER LAW) | — |

**CONVENTIONAL NAMES THAT DO NOT EXIST:** `FF9CustomMap-bb` / `-ih` (also `-hc`, `-ow`, `-sf`) are
per-worktree slot names from the SHELVED worktree era. They are on record in memory
`project-ff9-git-layout` because the paradigm may return, but no such folder is in the install and
none is registered. Never assume one — read `.ff9deploy.toml` and `Memoria.ini [Mod] FolderNames`
before deploying anywhere but the two live targets. Reach any deployed id via ~ -> Warp.

## .ff9deploy.toml keys

Gitignored, per checkout — pins the deploy target so checkouts never clobber each other:

- `mod_folder` — the target Memoria mod folder (override: `--mod-folder` flag / `$FF9_MOD_FOLDER`).
- `id` — the default deploy id, scratch band 30000-32767 (override: `--id N`).
- `text_block` — pin an unshadowed real MesDB id (override: `--text-block N`); see the
  deploy-symptoms reference file for the shadow mechanism.

## The EventDB/SceneData GLOBAL rule

The rule, owned by CLAUDE.md §3: **distinct ids are required even across folders, because
EventDB/SceneData are GLOBAL.** Every folder's DictionaryPatch/BattlePatch merges into one global
registry at launch (`DataPatchers.Initialize`) — the same id in two folders, or as both a `FieldScene` and a
`BattleScene`, collides and loads a null `.eb` (the deploy-symptoms reference file has the
diagnosis). The same stacking also causes the `.mes` text-block shadow.

## Folder auto-registration

Memoria auto-detects a mod folder containing a `ModDescription.xml` dropped into the FF9 root and
auto-adds it to `Memoria.ini [Mod] FolderNames` + `Priorities` — no manual ini edit needed. Caveat,
verbatim from memory `project-ff9-git-layout`: "auto-insert lands at an arbitrary position, so a mod
that must OVERRIDE/shadow another still needs the right ORDER"; and "the registered entry = the
OUTPUT FOLDER name, NOT `--mod-name`". The dev `deploy_*.py` do NOT edit `Memoria.ini` (they print
the manual steps); the only kit writer is `ff9mapkit coop` via `coop.mod_order_updates`.

## Reordering the stack by hand (THE LAUNCHER LAW)

Edit **both `[Mod] FolderNames` and `[Mod] Priorities` — same entries, same order — with the game
AND the launcher closed.** The launcher builds its mod list in `Priorities` order and rewrites
`FolderNames` from it at every Play click, so a `FolderNames`-only edit silently reverts (this
killed two -world reorder attempts before the 2026-07-12 root cause). `Priorities` may also list
inactive mods — leave them where they sit. The INVARIANT that must survive any reorder:
`FF9CustomMap-world` stays ABOVE `MoguriMain`, so the kit's composited `world_map_full_all.png`
beats Moguri's copy. The order read live from `Memoria.ini` on 2026-07-24 is `"FF9CustomMap",
"FF9CustomMap-world", "MoguriMain", "MoguriVideo"` — read the ini rather than trusting this line;
the `-hc`/`-ow` entries an older revision of this file listed are gone along with their folders.
Before any reorder, diff the moved folder's paths against every folder it newly outranks (the
stale-`8.mes`-stub lesson).
