# Id bands & mod folders — lookup

The brief's layout paragraph quoted verbatim, then broken out as a lookup. Deep recipe: read memory
`project-ff9-git-layout` (the old `project-single-repo-mode` memory was consolidated into it).

## The CLAUDE.md §3 layout blockquote (verbatim)

> **Layout in one breath** (full detail → [[project-ff9-git-layout]]): the working repo deploys into its OWN
> Memoria mod folder, pinned in a gitignored **`.ff9deploy.toml`** (`mod_folder` + scratch-band `id`; override
> via `--mod-folder`/`$FF9_MOD_FOLDER`). `Memoria.ini [Mod] FolderNames` stacks the folders; each folder's own
> DictionaryPatch/BattlePatch is read at launch. **Distinct ids are required even across folders** (EventDB/
> SceneData are GLOBAL). Slots: master → `FF9CustomMap`/**30000** · `-bb`/**30001** · `-ih`/**30002**; reach any
> via F6 → Warp. **Field-id bands:** **10-3100** real (locked) · **4000-9899** shipped custom · **30000-32767**
> dev scratch (engine `fldMapNo` is Int16 → max **32767**; a higher id registers but is unreachable).
> **Workflow:** single-repo out of `Dream-World-IX` master (worktrees shelved → [[project-single-repo-mode]]);
> make edits on a feature branch → `master`. `C:\gd\FFIX` is the read-only archive (Memoria source + old branches).

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

## Mod-folder slots (scratch band)

| Checkout | Folder | Scratch id |
|---|---|---|
| master | `FF9CustomMap` | 30000 |
| battle-backgrounds lane | `FF9CustomMap-bb` | 30001 |
| infohub-catalog lane | `FF9CustomMap-ih` | 30002 |

Reach any slot via F6 -> Warp. The `-bb`/`-ih` slots date from the shelved per-worktree era but stay
registered; the scheme is documented in memory `project-ff9-git-layout`.

## .ff9deploy.toml keys

Gitignored, per checkout — pins the deploy target so checkouts never clobber each other:

- `mod_folder` — the target Memoria mod folder (override: `--mod-folder` flag / `$FF9_MOD_FOLDER`).
- `id` — the default deploy id, scratch band 30000-32767 (override: `--id N`).
- `text_block` — pin an unshadowed real MesDB id (override: `--text-block N`); see the
  deploy-symptoms reference file for the shadow mechanism.

## The EventDB/SceneData GLOBAL rule

Verbatim (CLAUDE.md §3): "**Distinct ids are required even across folders** (EventDB/SceneData are
GLOBAL)." Every folder's DictionaryPatch/BattlePatch merges into one global registry at launch
(`DataPatchers.Initialize`) — the same id in two folders, or as both a `FieldScene` and a
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
inactive mods — leave them where they sit. The required live order (`FF9CustomMap-world` must stay
ABOVE `MoguriMain` so the kit's composited `world_map_full_all.png` beats Moguri's copy):
`"FF9CustomMap", "FF9CustomMap-hc", "FF9CustomMap-ow", "FF9CustomMap-world", "MoguriMain",
"MoguriVideo"`. Before any reorder, diff the moved folder's paths against every folder it newly
outranks (the stale-`8.mes`-stub lesson).
