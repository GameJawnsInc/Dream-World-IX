# `import-chain` + `build-all`/`deploy-all`: the field-chain byte round-trip

> **Status: SHIPPED + in-game proven.** This began as a design doc; P1–P5 are implemented (P4 deploy in-game-verified). The implementation lives in `chain.py`, `campaign.py`, `eventscan.py`, `extract.py`, and `tools/deploy_campaign.py` (CLI `import-chain` / `build-all` / `lint-campaign`; deploy via `tools/deploy_campaign.py`). Status detail per the block below.

Status: **P1–P5 implemented (P4 deploy in-game-verified); status per the block below.** Author target: ff9mapkit maintainer.
Grounded against the live codebase (citations inline) and a **live byte-trace of the Ice Cavern region (fields 300–312)**, used as the worked example throughout. Every claim cites `file:line` where verified; the few genuinely-deferred items are flagged **[new_work]**.

## Implementation status

- **P1 — read-only graph walk: DONE (2026-06-09), verified against the Ice Cavern byte-trace.**
  `ff9mapkit import-chain <seed> [--zones a,b] [--max-hops N] [--max-fields N] [--stop-at ids] [--follow-scripted] [--cross-zones]`.
  New code: `extract.ID_TO_FBG`/`ID_TO_EVT` + `extract.EventBundle` (bundle loaded once, id→`.eb`), `eventscan.scan_all_warps`
  (the 3-way taxonomy below), `chain.py` (the pure bounded BFS + `render`), the `import-chain` CLI command, `tests/test_chain.py`
  (12 offline tests, no game needed). `import-chain 300 --zones iccv,vgdl` reproduces the trace: 13 fields, the 305 hub + 307 branch,
  the 306→Marsh / 308→309 scripted seams, the 300/311/312 overworld exits, and per-screen encounters — and auto-flags 307's
  same-zone twin exits `STORY-COND`.
- **Dev/test id allocation** (the field-id bands, capped at the Int16 `fldMapNo` max 32767):
  a per-worktree mod folder + a **dev/test scratch band** (`pack.py` 30000–32767):
  single-field test slot **30003** (after master 30000 / -bb 30001 / -ih 30002), campaign dev block **30100** (Ice Cavern → 30100–30112).
  Pinned in `.ff9deploy.toml`. A *shipped* campaign would instead claim a `pack.suggest_base` block in the 4000–9899 content band; dev/test
  campaigns stay in scratch. (Memoria.ini `FolderNames` + the mod folder are added at deploy time, P4 — everything through P3 is offline.)
  Worked-example ids below say 6000–6012 (pre-band illustration); the live default is now 30100+.
- **Edge taxonomy (byte-survey, ~50 real fields):** walk-in gateways are only ~59% of connectivity; **~41% is SCRIPTED** teleport warps
  (cutscene/post-battle/auto-on-entry), all with literal targets. `WorldMap` (0xB6) operands are overworld LOCATION ids (9000-9012), **not
  field ids** — a separate "leave to overworld" marker, never a graph node. Only **~2.9%** of region exits are story-conditional
  (FF9 uses stacked same-zone gateways or `if(flag){A}else{B}`; it NEVER computes a warp target from a flag — pattern (B) = 0 occurrences).
  So the walk: follows walk-in by default, lists scripted as **seams** (opt-in `--follow-scripted`), treats overworld as a terminus, and
  flags same-zone-duplicate exits `STORY-COND` for `requires_flag` re-authoring.
- **Zone model + menu/non-field classification.** The "zone" is **segment 2 of the FBG folder** (`fbg_n01_**alxt**_map016_...` → `alxt`) — Square's own
  4-char area mnemonic, read verbatim. Not a curated hierarchy: **52 tokens over 676 fields, median 10 each, max 70** (`ldbm` = all of Lindblum);
  5 tokens exceed the default `--max-fields` (`ldbm` 70, `alxc` 61, `alxt` 38, `cysw` 33, `fslr` 26), where the loud truncation is the safety valve.
  `--zones` is a **ceiling** (which zones edges may cross), NOT "dump this zone" — the walk only pulls the connected component reachable from the
  seed within bounds. A target NOT in the FBG/EVT table has **no background** (shop/menu, disc-variant, cutscene-only) and can't be forked as a room;
  the walk classifies these as **MENU / NON-FIELD TARGETS** (a `forkable_fn` checks `id in ID_TO_FBG`, applied *before* the zone test so a shop door
  reads as `[menu/no-bg]`, not a bogus `zone:?` portal). This is why Alexandria/Square (103) yields only 5 walkable rooms + 6 shop/menu leaves, not a
  flood — its shops are menu-fields. For P2 this also flags that a forked town must re-author shop hooks as menu events, not gateways to rooms.
- **P2 — emit campaign.toml + retargeted forks: DONE (2026-06-09), verified end-to-end on the real Ice Cavern.**
  `import-chain <seed> --out <dir> [--id-base N] [--campaign-name X] [--live-seams]` flips the walk from dry-run to WRITE: it assigns
  each forkable member a new id (`id_base + i`, BFS order = 6000–6012 for Ice Cavern), forks each real field into its own subdir, and
  **retargets every in-chain gateway `to` real-id → the chain's new id** (the load-bearing pass, threaded through `extract._imported_content_toml`'s
  single emit site via a new `id_remap` kwarg — out-of-chain targets become commented seam stubs, encounter `scene=` battle ids are left alone).
  New `ff9mapkit/campaign.py` (id/name assignment, per-member fork loop, `campaign.toml` render); `extract.py` gained backward-compatible
  `id_remap`/`live_seams` kwargs (single-field `import` byte-identical when `None`). campaign.toml is valid array-of-tables TOML (tomllib-parseable
  for P3): `[campaign]` + `[[field]]` members + `[[edge]]` named in-chain graph + `[[seam]]` (scripted/overworld/menu/portal). Verified: the real
  Ice Cavern fork emits 13 members (6000–6012), 22 retargeted edges, IC_STA's two same-zone waterfall exits both retarget (6008/6009) + flag
  STORY-COND, IC_WAF (scripted-only) gets no bogus gateway, seams = 2 scripted + 3 overworld. **6 new offline tests** (retarget via monkeypatched
  scan_content; id/name/edge/seam collection on a synthetic walk; TOML validity) + a guarded real-bytes test, all pass. area<10 members (all of Ice
  Cavern) fork as `editable`; if their art was never `[Export]`'d they degrade to logic+camera+walkmesh+retargeted-gateways and print a `needs_export`
  list. **Scope cut:** no build/deploy (P3/P4), no flag allocation/registry or cross-field lint (P5), no New-Game wiring (P4).
- **P3 — build-all: DONE (2026-06-09), verified end-to-end on the real Ice Cavern.** `ff9mapkit build-all <campaign.toml> [--out
  dir] [--allow-artless]` loads the manifest and compiles every member into ONE staged Memoria mod via the existing `build.build_mod`
  (no new build logic). New `campaign.load_campaign` (inverse of `render_campaign_toml`) + `build_campaign` + `validate_ids`; each member
  `FieldProject.load`s from its own subdir (so camera.bgx/walkmesh.bgi/layer PNG sidecars resolve) and is built by `build_mod(mod_name=campaign.mod_folder)`.
  **text_block stays the default 1073** — an earlier attempt to give each member a distinct textid (= its new id) was REVERTED after in-game testing:
  the FieldScene textid (6th token) must already be a key in `FF9DBAll.MesDB` or `DataPatchers` **skips the whole scene** (`DataPatchers.cs:392-395`
  `if(!MesDB.ContainsKey(mesID)) continue;` → `"invalid message file ID 30100"` → the field never registers, absent from F6). Empty members ship no
  `.mes`, so 1073 (a real base block) is correct + shared harmlessly; distinct textids only become needed/valid once a member ships its own `.mes` (deferred).
  Campaign-level validation = ids non-empty, distinct, in [4000, 32767] (Int16 cap); per-field validation runs inside build_field. Verified: the
  full Ice Cavern campaign builds a **13-line DictionaryPatch** (`FieldScene 30100 11 IC_ENT IC_ENT 30100` … 30112), one ModDescription with
  `InstallationPath = FF9CustomMap-ow`, merged BattlePatch, per-member scene+7-lang .eb; the retargeted `Field(30101)` etc. survive compilation
  byte-for-byte (probe + test confirmed). **3 new tests** (load round-trip, id validation, a real-bytes build) + the existing eventscan summary
  test updated for the new retarget counters; **478 kit tests pass**. **needs_export** (artless editable members) hard-stops by default with a
  guided message, `--allow-artless` overrides. **Scope cut:** no deploy/Memoria.ini/revert (P4); flag_base/initial_flags parsed but not consumed,
  no cross-field lint (P5); BattlePatch dedup deferred (documented).
- **P5 — campaign lint + flag scanners: DONE (2026-06-09; per-member flag auto-allocation deferred).** `ff9mapkit lint-campaign
  <campaign.toml>` validates a campaign without building, and `build-all` auto-lints (errors abort, warnings print). `campaign.lint_campaign`
  checks (errors): ids non-empty/distinct/[4000,32767], every `[[edge]]` from/to resolves to a member, `entry_field` is a member, `[[seam]]`
  to_real is int|WORLDMAP, member field.tomls exist; (warnings): stale seam to_member, needs_export members, **ungated stacked story-conditional
  doors**, and explicit cross-field flag deps (a `requires_flag` no member sets = permanently locked; a `flag` written by ≥2 members = collision).
  New GLOB **flag scanners** in eventscan (`_glob_var_token`, `scan_flags_set`, `scan_required_flags`, `scan_edge_flag_gates`) — raw-byte, GLOB-only
  (MAP 0xC5/0xE5 excluded as transient), round-trip the kit's own `region.set_var`/`flag_gate` and detect real-field writes/gates (probe-confirmed
  on Gizamaluke 703 idx 191/3816 + Dali 402). Verified: real Ice Cavern lints OK with the IC_STA stacked-door warning; 9 new tests; 487 kit tests pass.
  **DEFERRED (forward-looking):** per-member flag **auto-allocation** (threading `flag_base + i*K` into `build_script`/`lint_logic`) — the Ice Cavern
  forks are empty rooms (zero flags allocated), so the collision is latent; the lint surfaces any *explicit* collision meanwhile, and auto-isolation
  lands when campaign members gain authored content. Also deferred: named-flag registry; the `.eb`-based (vs toml) cross-field flag lint.
- **P4 — deploy-all + New-Game entry: DONE, in-game proven.** `tools/deploy_campaign.py` (a tools script like install_tworoom.py — it
  touches the install) reversibly installs a built campaign: resolve mod folder (deploy_field precedence → `FF9CustomMap-ow`), build-all to a temp
  dist, **ONE** snapshot of the mod folder, **wholesale replace** with the dist (never a per-id DictionaryPatch merge — that's the sibling-clobber
  bug), wire New Game via the proven `retarget_newgame_warp.py` (a **direct field-70 opening-override retarget**: byte-patch the shared `FF9CustomMap`
  field-70 opening `EVT_ALEX1_TS_OPENING` so its `Field()` literal points at the campaign's entry id → New Game → field 70 → `Field(entry)`), and
  emit one `revert_campaign.py`. **No field-100 hop:** a self-seeding verbatim chain bakes its own party/beat via `[startup]`/`[party]`, so the entry
  field needs no party-creating intermediary; `--stock` is a deprecated no-op (`argparse.SUPPRESS`, ignored). This **supersedes** the old field-100-hop
  `newgame_warp.py`. **Default-safe: dry-run unless `--apply`.** Verified offline: the real Ice Cavern dry-run prints the plan (13 members
  30100–30112, entry IC_ENT, route, dist contents) + lints + touches nothing. **Cross-folder note (load-bearing):** the retarget patches the SHARED
  `FF9CustomMap` field-70 override (which must exist there), not the campaign's folder — so only one campaign owns New Game at a time, and
  `revert_campaign.py` undoes BOTH the folder snapshot and the warp. In-game proven: `--apply` install → relaunch → New Game lands in the entry field,
  save/Continue inside a custom field, walking the chain.

> Provenance of the worked example: traced LIVE via `eventscan` on the real extracted `.eb` bytes from the user's p0data install. The correct id→field resolution is `_fieldtable.FBG_TO_EVT` inverted (NOT `resolve_field`, which substring-matches FBG names and mis-resolves a bare numeric id). All 13 fields extracted + scanned cleanly.

---

## 1. What & why

Single-field `import` already closes *half* the byte round-trip: `extract_event_script(field)` reads a real field's compiled `.eb` from the game's p0data bundle (never raising — `extract.extract_event_script`), and `eventscan.scan_content(eb)` returns that field's gateway **edges** `{to, entrance, zone}` plus `music`, `encounter`, `control_direction`, and `ladders` in one pass (`eventscan.scan_content`, `scan_gateways` at `eventscan.scan_gateways`). But each edge's `to` is the *real* destination field id pointing back into the live game — `import` prints "gateways point at REAL fields — retarget them" (`cli.py:336`) and stops. **`import-chain`** turns that single-node extract into a bounded graph walk: from a seed field it follows the `to` edges, forks every reachable field, and — the one thing single-field import structurally cannot do — **retargets the edges among the chain's own new ids** so the forked region is a self-contained, connected, walkable campaign rather than a pile of doors leading back into the live game. The symmetric **`build-all`/`deploy-all`** export loop then ships those N forked fields as ONE reversible, New-Game-enterable Memoria mod. Together they close the round-trip for field-chains: *region of real game bytes → editable campaign → rebuildable drop-in mod.* The Ice Cavern (300–312) is the canonical worked example — a clean, near-linear 13-screen region traced entirely from real bytes.

---

## 2. The import-chain algorithm

### 2.1 The walk

A bounded BFS over the **walkable-door graph**. Frontier seeded with the resolved seed field; per node:

1. **Resolve id → folder → `.eb`.** This was the one hard blocker. `resolve_field`/`event_name_for` are NAME-keyed — they `re.sub("^fbg_n\d+_", ...)` then substring-match FBG folder names (`extract.resolve_field`), so a bare numeric id like `300` mis-resolves (the trace confirms: a first pass got nonsense Treno/S.Gate targets). The live trace proved the correct path is to invert `_fieldtable.FBG_TO_EVT` to id-keyed maps, which the kit ships as `extract.ID_TO_FBG` / `extract.ID_TO_EVT`; the `.eb` lookup itself is `EventBundle.eb_for_id(field_id)` (`extract.EventBundle.eb_for_id`), which skips `resolve_field`'s name path:
   ```python
   ID_TO_FBG = {rec[0]: folder for folder, rec in FBG_TO_EVT.items()}   # extract.ID_TO_FBG
   ID_TO_EVT = {rec[0]: rec[1]   for folder, rec in FBG_TO_EVT.items()}   # extract.ID_TO_EVT
   bundle = EventBundle(game)            # loaded once for the whole walk
   eb = bundle.eb_for_id(field_id)       # .eb bytes, or None for a world/special/absent id
   ```
   It handles duplicate/aliased ids, and ids with no FBG (world/special fields → `None`); those branches terminate gracefully — exactly how `extract_event_script` returns `None` rather than raising (`extract.extract_event_script`).

2. **Scan the node.** Call `event_script_by_id` → `scan_content` (`eventscan.scan_content`). That single call yields `{gateways, music, encounter, control_direction, ladders}` — the entire per-node payload, already field-by-field and proven.

3. **Enqueue successors.** For each `edge["to"]` not yet visited and within bounds, push it. Bounds applied **in this order** (cheap → expensive, fail-fast):
   - **visited-set** dedup (the graph is bidirectional and loops — Ice Cavern's 305 hub has 3 exits, every door is two-way).
   - **`--max-hops`** depth cap (default 20).
   - **`--zones`** (with `--cross-zones` to span more) on FBG folder prefix (zone unit — Ice Cavern is all `fbg_n05_iccv_*` except 312's `fbg_n06_vgdl_*`).
   - **`--stop-at <id,...>`** explicit cuts.
   - **no-FBG prune** (world/special → branch terminates).
   - **crash/unborrowable denylist** (seed it with field **100** — area 1 AND documented to crash, CLAUDE.md §5).
   - **`--max-fields` hard cap** (default 25): abort LOUDLY if exceeded rather than forking 200 fields.

### 2.2 Natural graph boundaries (free, no new code)

- **WorldMap exits stop the walk.** `scan_gateways` only follows `Field` (`FIELD_OP = 0x2B`, `eventscan.FIELD_OP`); WorldMap is a distinct opcode `0xB6` (`eb/opcodes.py:343`) and is never an edge. So the region's worldmap handoff is automatically a terminus — in the trace, **312** (38 `WorldMap` ops, no `Field` gateways) ends the chain for free, and **300** is the only worldmap *entry*.
- **Battle edges are not graph edges.** Encounters are scanned as per-node *content* (`scan_encounter`, `eventscan.scan_encounter`), never followed.
- **Scripted/cutscene warps are invisible (by design, and a documented limitation).** `scan_gateways` requires an entry holding BOTH `SetRegion(0x29)` AND `Field(0x2B)` (`eventscan.scan_gateways`); it skips computed/expression polygons (`_region_points` returns `[]` on any `arg_is_expr`) and bare `Field()` warps. The trace shows two real cases this drops: **306's `Field(652)`→Marsh** (a cutscene warp, no `SetRegion`) and **308's `Field(309)`** (a one-way scripted transition — `kit_gateways` empty for 308). The graph is the *walkable* graph, not every narrative transition. (★ Not `NarrowMapList.cs` — that's the engine's camera-WIDTH table, not a warp/cutscene driver; the unseen movers are scripted `Field()` warps + scenario-counter dispatch *inside* the `.eb`, plus runtime-computed ids.) **trust-the-user caveat (CLAUDE.md §9) applies.**

### 2.3 Two scanners for cross-field flag dependencies

`scan_content` captures no flag dependencies, so to surface "edge gated by flag N" / "field X sets flag N" the kit ships two raw-byte scanners in `eventscan.py` (`scan_flags_set`, `scan_edge_flag_gates`, alongside `scan_required_flags` and the `_glob_var_token` helper). They raw-match around opcode `0x05` like `eventscan._entrance_at`, NOT `instr.args` — the disassembler flattens expression operands to opaque string tokens and `Instr.imm()` returns `None` for expression args:

- **`scan_flags_set(eb)`** — flag WRITES. Match `region.set_var`/`or_var` on `GLOB_BOOL` (`region.set_var`/`region.or_var`): `05 C4 <idx> 7D <i16> 2C|3F 7F`, plus the long-index form (`class|0x20` = `0xE4` + 2-byte LE, `region._push_var`). Returns the `{flag_idx}` this field writes.
- **`scan_edge_flag_gates(eb)`** — flag READS gating an exit. The exact prologue `region.flag_gate` emits (`region.flag_gate`) is `cond_truthy + JMP_TRUE/FALSE + i16(1) + RETURN` = `05 C4 <idx> 7F  03|02  01 00  <RETURN>`. Detect it at the head of a gated gateway's tag-2 (Range/tread) func; emit `{edge → required flag_idx, require_set}`.

**Filter to `GLOB_BOOL` (0xC4 / 0xE4).** `MAP_BOOL` (0xC5) / `GLOB_UINT8` (0xD5) are per-field transient, WIPED on field load (`region.MAP_BOOL`/`region.GLOB_UINT8`) — reporting them as cross-field deps is a false link. NOTE the trace finding: **none of Ice Cavern's 13 inter-screen edges are flag-gated** — every captured gateway is an unconditional `SetRegion(tread)→Field`. The region's story gating lives in *cutscene entries* (Black Waltz 3 / Mene), which `scan_content` deliberately skips. So for the worked example these scanners report empty — they exist for gated regions, and to drive cross-field lint (§4).

### 2.4 The reusable API

The graph walk shipped as `chain.walk(seed_ids, scan_fn, zone_fn, ...)` (`chain.walk`) — a pure bounded BFS over the door graph — driven by a `scan_fn(field_id)` that the `import-chain` command builds over `extract.EventBundle` + `eventscan.scan_all_warps` (the walk-in / scripted / overworld taxonomy, `eventscan.scan_all_warps`), with the §2.3 flag scanners layered in for cross-field deps:

```python
result = chain.walk(seed, scan_fn, zone_fn, forkable_fn=..., zones=..., max_fields=...)
# scan_fn(field_id) never raises (mirrors extract_event_script): id -> .eb via
#   extract.EventBundle -> scan_all_warps + the §2.3 flag scanners; a missing/world dest
#   yields {found: False, ...} and that branch terminates while the walk continues.
```

It composes existing funcs: `ID_TO_FBG`/`ID_TO_EVT` (`extract.ID_TO_FBG`/`extract.ID_TO_EVT`) resolve id → folder/`EVT_` script against the in-memory `FBG_TO_EVT` table (instant); `EventBundle` (`extract.EventBundle`) loads the bundle once and pulls each `.eb` by id; only the `.eb` extraction hits UnityPy (the bundle/index caches make a cold first run 1–2 min, then cheap).

### 2.5 Id remapping + retarget pass — the load-bearing logic

After the walk completes with a visited set of real ids:
1. Assign each real id a fresh custom id: `custom_id = id_base + i` (deterministic order = BFS discovery order, so it's stable/re-runnable).
2. In every node's emitted `field.toml`, rewrite each `[[gateway]] to` (and `[[ladder]] top_field`) that points at an **in-chain** real id → the corresponding new custom id.
3. Edges pointing **outside** the chain become **seams**: emit as a commented stub carrying the real id (a one-way door back into the live game, or a TODO). This is the decision the design must make explicit (see §7 open boundary): default = comment-out as a dead end; `--live-seams` to leave them warping into the real game.

This is precisely what single-field import cannot do (it has no knowledge of sibling forks). `deploy_field`'s sandbox-identity override (`deploy_field.FID`/`deploy_field.TEST_NAME`) already proves an in-memory id override is mechanically fine.

### 2.6 Per-arrival spawn (deferred) **[new_work]**

`extract_field` emits ONE heuristic `[player] spawn` = centre of the on-camera walkmesh (`extract.extract_field`), regardless of arrival entrance. A faithful chain wants each field's `{entrance: (x,z)}` map — recovered by scanning the player entry's Init for `if (D8:2 == k){ MoveInstantXZY(...) }` branches. The branch shape varies per field (no fixed template). **v1 ships single-spawn-per-field**; entrance is imported and round-tripped on edges (the trace shows the clean FF9 convention — every gateway *leaving* field N carries `entrance = N`'s screen index: 305's three exits all `entrance=5`, 309's all `entrance=9`) but the *landing* position is the single default. Mark as a known limitation.

### 2.7 Cross-zone scripted-warp leaks + the id-preserving surgical-append fix

`--whole-zone` forks every live field in the **seed's zone(s)**, which closes the within-zone scripted-transition gap (§2.1 walks doors only; ~41% of FF9 connectivity is scripted). But it is still **per-zone**: a forked member can carry a scripted `Field(X)` whose `X` lives in a *different, unseeded* zone, reachable only by that warp. The walk records it as a seam and never pulls `X` in, so the member **leaks into the real game** at that warp.

Real example (2026-06-18): the cargo-ship Black Waltz deck (donor 501, fork 6121) warps `Field(506)` for the Zorn/Thorn cutscene, but **506 is the `fnrl` zone** (`fbg_n10_fnrl_map150_fn_dck_0`), not `cshp` — so the `cshp` whole-zone seed forked 500–507 *except* 506, and 6121 dropped the player into real FF9.

**Detection gap to close:** a coverage/leak lint over a built campaign should flag any verbatim member's `Field(X)` where `X` is neither a campaign member nor a known overworld/menu/return seam → `live leak to real field X (zone Z) — fork it`.

**Fix without a re-fork (id-preserving, so existing saves survive — a full re-fork shifts `id_base+i` and breaks any in-fork save):**

```
# 1. Fork the missed field, APPENDED at the next free id (nothing else moves):
ff9mapkit import <X> --native --verbatim --id <next-free> --name OPEN_<NAME> --out <campaign>/OPEN_<NAME>
#    set text_block = EVENT_ID_TO_MES[X]  (the donor's real MesDB block; the import default 1073 SHADOWS)
#    retarget OPEN_<NAME>'s own onward Field() exits -> existing member fork ids
# 2. Add the leaking member's retarget:  <X> = <next-free>
# 3. deploy_field BOTH members into the live folder (surgical: each updates ONE DictionaryPatch
#    line, preserving the other members + the New-Game override — unlike deploy_campaign's
#    wholesale replace):
py tools/deploy_field.py <campaign>/OPEN_<NAME>/OPEN_<NAME>.field.toml --id <next-free> --name OPEN_<NAME> --mod-folder FF9CustomMap
py tools/deploy_field.py <campaign>/<LEAKING>/<LEAKING>.field.toml      --id <leaking-id> --name <LEAKING> --mod-folder FF9CustomMap
# 4. Append "<next-free> <X>" to the live ForkDonorPatch.txt  (so the s23/s24/s29 id-gate remaps fire)
# 5. RELAUNCH (a brand-new id registers its DictionaryPatch line only at launch)
```

Record the appended member in `campaign.toml` (out-of-band `[[field]]` + `[[edge]]`s) so a future stable-id re-fork keeps it. This is the template for plugging any single missed cross-zone field on a *live* campaign.

---

## 3. The campaign.toml manifest

The kit defines a top-level `campaign.toml` that the chain importer emits and the export loop consumes (`campaign.py`). It references N per-field `field.toml`s (reuses `FieldProject.load` per node, `build.FieldProject.load`) rather than inlining them — keeps single-field tooling (`edit`, `lint`, Blender) working unchanged on each member.

### 3.1 Schema

```toml
[campaign]
name        = "ICE_CAVERN"      # mod-folder + ModDescription name
mod_folder  = "FF9CustomMap-ice"  # the pinned worktree mod folder (Memoria.ini FolderNames)
id_base     = 4100              # member i -> id_base + i (must be >= 4000; whole block distinct globally)
flag_base   = 8512             # campaign flag band START (= campaign.FIRST_SAFE_FLAG; first bit clear of ALL
                               #   real-FF9 usage. WAS 8300 -> collided with real chest flags 8376-8511.)
flags_per_field = 64           # K-wide GLOB block per field; field i -> [flag_base + i*K, +K). Max 122 fields
                               #   (the choice scratch sits at bit 16320); lint_campaign asserts the bounds.
entry_field = "IC_ENTRANCE"    # which member New Game lands in (party-set route in §5)
entry_entrance = 0             # the arrival entrance the entry field's player-init switches on

# Members in BFS-discovery order; id auto-assigned id_base+i unless `id` overrides.
[[field]]
name    = "IC_ENTRANCE"
source  = 300                  # the real field this was forked from (provenance + re-import)
toml    = "IC_ENTRANCE.field.toml"
mode    = "borrow"             # "borrow" | "editable"  (auto-set: area<10 -> editable)
# id    = 4100                 # optional explicit override; else id_base+0

# Per-field flag declarations (names resolved campaign-wide; see §4)
[[field.flag]]                 # optional; only when a field sets/reads named story flags
name = "ice_path_unlocked"

# The connected graph, as NAMED edges (the retargeted, self-contained chain).
# Each row mirrors a real captured gateway; `to` is a member NAME, not a raw id.
[[edge]]  from = "IC_ENTRANCE"  to = "IC_PATH_1"  entrance = 0   # forward into the cavern
[[edge]]  from = "IC_PATH_1"    to = "IC_ENTRANCE" entrance = 1
# ... optional gate:  gated_by = "ice_path_unlocked"  require_set = true

# Seam edges: gateways that pointed OUTSIDE the chain. Defaulted off; surfaced for the author.
[[seam]]  from = "IC_OUTSIDE"   to_real = "WORLDMAP"   note = "312 -> worldmap (38 WorldMap ops); re-author"
[[seam]]  from = "IC_CAVE"      to_real = 652          note = "306 -> Marsh scripted warp (no SetRegion)"

[initial_flags]                # GLOB flags pre-set at campaign entry (e.g. story already-past)
# ice_path_unlocked = true
```

`[[edge]]`/`[[seam]]` are the campaign's authoritative graph (validated in §4). Each member `field.toml` still carries its own `[[gateway]]` blocks (what `build` actually compiles); the campaign edges are the cross-field *truth* the lint checks them against.

### 3.2 Filled-in example (REAL traced Ice Cavern region)

```toml
[campaign]
name        = "ICE_CAVERN"
mod_folder  = "FF9CustomMap-ice"
id_base     = 4100
flag_base   = 8512
flags_per_field = 64
entry_field = "IC_ENTRANCE"
entry_entrance = 0

[[field]] name="IC_ENTRANCE" source=300 toml="IC_ENTRANCE.field.toml" mode="editable"  # area 5 -> editable
[[field]] name="IC_PATH_1"   source=301 toml="IC_PATH_1.field.toml"   mode="editable"
[[field]] name="IC_PATH_2"   source=302 toml="IC_PATH_2.field.toml"   mode="editable"
[[field]] name="IC_ICICLE"   source=303 toml="IC_ICICLE.field.toml"   mode="editable"
[[field]] name="IC_BRIDGE"   source=304 toml="IC_BRIDGE.field.toml"   mode="editable"
[[field]] name="IC_HUB"      source=305 toml="IC_HUB.field.toml"      mode="editable"  # save junction, no encounters
[[field]] name="IC_CAVE"     source=306 toml="IC_CAVE.field.toml"     mode="editable"  # dead-end side room
[[field]] name="IC_BRANCH"   source=307 toml="IC_BRANCH.field.toml"   mode="editable"
[[field]] name="IC_WATERFALL_A" source=308 toml="IC_WATERFALL_A.field.toml" mode="editable"  # no walk-in gateway
[[field]] name="IC_WATERFALL_B" source=309 toml="IC_WATERFALL_B.field.toml" mode="editable"
[[field]] name="IC_WATERFALL_C" source=310 toml="IC_WATERFALL_C.field.toml" mode="editable"
[[field]] name="IC_EXIT"     source=311 toml="IC_EXIT.field.toml"     mode="editable"
[[field]] name="IC_OUTSIDE"  source=312 toml="IC_OUTSIDE.field.toml"  mode="editable"  # area 6; worldmap handoff

# Assigned ids: 4100..4112 (id_base+i). Edges below already retargeted to NAMES (= those ids).
[[edge]] from="IC_ENTRANCE"    to="IC_PATH_1"    entrance=0
[[edge]] from="IC_PATH_1"      to="IC_ENTRANCE"  entrance=1
[[edge]] from="IC_PATH_1"      to="IC_PATH_2"    entrance=1
[[edge]] from="IC_PATH_2"      to="IC_PATH_1"    entrance=2
[[edge]] from="IC_PATH_2"      to="IC_ICICLE"    entrance=2
[[edge]] from="IC_ICICLE"      to="IC_PATH_2"    entrance=3
[[edge]] from="IC_ICICLE"      to="IC_BRIDGE"    entrance=3
[[edge]] from="IC_BRIDGE"      to="IC_ICICLE"    entrance=4
[[edge]] from="IC_BRIDGE"      to="IC_HUB"       entrance=4
[[edge]] from="IC_HUB"         to="IC_BRIDGE"    entrance=5
[[edge]] from="IC_HUB"         to="IC_CAVE"      entrance=5   # side-branch
[[edge]] from="IC_HUB"         to="IC_BRANCH"    entrance=5
[[edge]] from="IC_CAVE"        to="IC_HUB"       entrance=6
[[edge]] from="IC_BRANCH"      to="IC_HUB"       entrance=7
[[edge]] from="IC_BRANCH"      to="IC_WATERFALL_A" entrance=7
[[edge]] from="IC_BRANCH"      to="IC_WATERFALL_B" entrance=7
[[edge]] from="IC_WATERFALL_B" to="IC_BRANCH"    entrance=9
[[edge]] from="IC_WATERFALL_B" to="IC_WATERFALL_C" entrance=9
[[edge]] from="IC_WATERFALL_C" to="IC_WATERFALL_B" entrance=10
[[edge]] from="IC_WATERFALL_C" to="IC_EXIT"      entrance=10
[[edge]] from="IC_EXIT"        to="IC_WATERFALL_C" entrance=11
[[edge]] from="IC_EXIT"        to="IC_OUTSIDE"   entrance=11  # exit the cavern

# Captured-but-not-a-walk-in-gateway: author these by hand.
[[seam]] from="IC_WATERFALL_A" to_real=309  note="308->309 is a scripted Field(), no SetRegion: author exit fresh"
[[seam]] from="IC_CAVE"        to_real=652  note="306->Marsh scripted cutscene warp"
[[seam]] from="IC_OUTSIDE"     to_real="WORLDMAP" note="312 has 38 WorldMap ops, no Field gateway: re-author worldmap exit"

[initial_flags]
# (none — Ice Cavern's inter-screen edges are all unconditional)
```

> Mode is `editable` for every field because **all 13 are area < 10** (300–311 area 5, 312 area 6) and a pure BG-borrow `FieldScene <area>` of 5/6 black-screens (loader reads exactly 2 chars of `"FBG_N"+area`, no zero-pad). `--editable` remaps the low area to ≥10 by shipping the field's own exported art. This is the most important caveat the worked example forces (§7).

---

## 4. Flag + id allocation model

### 4.1 The bug this fixes

**ROOT CAUSE (verified):** the once-flag allocator's `flag_counter` resets to 0 per build and the flag = `EVENT_FLAG_BASE + counter`, computed *per-field* from global constants — `event.py:27` (8000), `cutscene.py:37` (8100), `choice.py:35` (8200) (`build._FlagAlloc`). So field B's first chest and field A's first chest both pick **8000**, and because `once=true` writes a save-persistent `GLOB_BOOL` (`cutscene.py:156-162`), **looting field A's chest can mark field B's chest looted campaign-wide.** Harmless for one field; a latent campaign-corrupter for N.

### 4.2 Campaign-wide partitioning **[new_work]**

- **Ids:** member `i` gets `id_base + i` (4100, 4101, …). `build_mod` does NO allocation — each id is read verbatim from `[field] id` (`build.FieldProject` → `build.build_field`). The campaign loader either (a) verifies author-typed ids are all ≥4000 and **globally** distinct, or (b) auto-assigns from `id_base` and rewrites every cross-field reference in lockstep (§2.5). The uniqueness assertion must be **global, not just within-campaign**, because EventDB/SceneData are merged across stacked mod folders at launch — see [`GLOBAL_RESOURCES.md` §B](GLOBAL_RESOURCES.md) for the id-namespace rule and the [section-C bands](GLOBAL_RESOURCES.md) (field ids 4000–9899 content / 30000–32767 scratch). The contiguous-block ceiling (4100..4140 all register) is **unverified — needs an in-game test** (§7).
- **Flags:** parameterize the allocators by a **per-field `flag_base`** so field B never overlaps field A. Field `i` owns `[flag_base + i*K, flag_base + (i+1)*K)`, and within its block the three categories sub-partition (cutscene `base+0`, events `base+1..+31`, choices `base+32..+63`). **[LANDED 2026-06-10, story_flags branch]** `build._FlagAlloc` threads an optional per-member `flag_base` through `build_script`/`lint_logic` (default `None` = the historical 8000/8100/8200 constants, so single-field builds stay **byte-identical**); `campaign.build_campaign` assigns each member `flag_base + i*K`. The default `flag_base` is now **8512** (`campaign.FIRST_SAFE_FLAG`) — the old **8300** collided with real-FF9's treasure-chest bitfield at bits **8376–8511** (a verified latent save-corrupter; see `research/STORY_FLAGS.md` §4). `lint_campaign` now errors if any member block, or any explicit flag, lands in the chest band or past the choice scratch (bit 16320).
- **Cross-field named flags:** authors write `requires_flag`/`set_flag` **by name**, resolved through a campaign registry table to a concrete index. This is the *only* safe cross-field gate (a name maps to one index regardless of which field sets vs reads it). Hook `build._gate_of` and `event.py:48` (int-only today). Shared/cross-field flags live in a **separate band above the per-field blocks** (recommended over exporting from a field block) so a field's local once-flags never alias a shared flag.

### 4.3 Cross-field lint

`lint_logic` (`build.lint_logic`) validates flags WITHIN one field only (dangling `requires_flag`, once-base collisions, dup names). `campaign.lint_campaign` is the campaign-level validator (auto-run by `build-all`; errors abort, warnings advise) that asserts, before `build_mod` writes the DictionaryPatch:
- every `[[edge]] to` / `[[seam]]` / `[[ladder]] top_field` resolves to a member (or is an explicit seam);
- ids are distinct and in range;
- every cross-field `requires_flag` (a gated edge/NPC) is `set_flag` by **some** member — and ideally by one reachable *earlier* in the entry-rooted graph (an edge gated by flag N whose producer isn't in the imported set = a permanently-locked door). The §6 open question — auto-pull producers vs warn — defaults to **warn**, mirroring the linter's existing philosophy;
- no two members write the same flag index unintentionally (the root-cause check, now cross-field);
- distinct `text_block` per member (default 1073 is fine *because each custom field owns its own `.mes` at that block in its own mod folder* — but two members sharing a block in one folder would overwrite dialogue; worth a campaign assert). `lint_logic`'s `settable` vs `need_set` clash check (`build.lint_logic`) is the template.

### 4.4 Stable re-allocation — saves survive a re-fork **[LANDED 2026-06-18]**

The §4.2 allocation is **index-based** (`id = id_base + BFS-index`, flag window `= flag_base + position*K`). A naive re-fork (add a seed, `--whole-zone`, change `--max-fields`) re-walks in a different order → both shift → an in-game **SAVE goes stale** (it stores the field id + the GLOB story-flag bits at their old window). That's the public-beta save-compat trap.

**Fix (`assign_ids(prior=, reserved_ids=)` + `write_campaign(prior_plan=)`):** re-forking into an `--out` that already holds a `campaign.toml` is **STABLE by default**:
- a **re-discovered** donor keeps its **exact prior fork-id + member name**;
- a **net-new** donor is **appended above every prior id** (never reusing one — `reserved_ids` protects *all* prior ids, including source-less / hand-appended members absent from the donor→id map), so a stale save can never land on the wrong field;
- members are emitted **id-sorted**, so a re-discovered member keeps its **position** → its position-based **flag window survives** too (and new members, sorting to the end, take fresh windows *above* every prior one, disturbing none);
- a prior member the new walk didn't re-discover (a hand-appended out-of-band fork like a missed cross-zone cutscene field — §2.7) is **carried** verbatim (files + id) so it isn't orphaned and its cross-link doesn't re-leak;
- the prior **entry field** is preserved (a changed discovery order won't silently repoint New Game).

`--fresh-ids` opts out (old index-based behavior). Guards warn on the save-breakers: the prior manifest being a **different campaign** (name mismatch / 0 donors re-discovered), a prior member whose **files vanished** (can't carry → later windows shift), or a changed **`--flag-base`/`--flags-per-field`** (ids stay stable but every flag window moves). Keep flag geometry constant across re-forks.

**Known limitation — multi-campaign JOURNEYS:** stability above is per-campaign. The *journey* assembler packs each campaign's flag window back-to-back by member count (`journey._flag_windows`), so **appending a member to an EARLIER journey campaign shifts every LATER campaign's `flag_base`** → a save in a later campaign desyncs its story flags (ids still fine). Single-campaign re-forks (the opening) are fully stable; the journey flag-window pinning is a follow-up (reserve a padded per-campaign capacity in the manifest instead of deriving from live member count).

---

## 5. The export loop

### 5.1 `build-all` (generalize `build_mod`)

The BUILD half reuses `build_mod`: `build_mod(projects, out_root, ...)` already loops `build_field` over a LIST and writes ONE combined `DictionaryPatch.txt` (one `dict_line` per field, `build.build_mod`), a merged `BattlePatch.txt` (`build._emit_battle_patch`), and one `ModDescription.xml` (`build.build_mod`). The `ff9mapkit build` CLI already takes `nargs="+"` field.tomls (`cli.py:644-650`). `build-all` is a thin campaign front-end:
```
load campaign.toml -> [FieldProject.load(m.toml) for m in members]    # build.FieldProject.load
   -> apply id_base / flag_base assignment + retarget (§2.5, §4.2)
   -> cross-field lint (§4.3) — ABORT on dangling edge / dup id / dup text_block
   -> build_mod(projects, out_root, mod_name=campaign.mod_folder)      # build.build_mod, unchanged
```
Output is a staged `dist/` (like `tworoom/dist`). `build_field` already assembles `FieldScene <id> <area> <bg_mapid> <name> <text_block>` and **skips the scene/FBG write when `borrow_bg` is set** (`build.build_field`) — so borrow members ship only `.eb`(+`.mes`), editable members ship their `.bgx`/`.bgi`/PNG scene. A mixed-mode chain builds fine (members are independent field.tomls). Per-language `.eb` is automatic (bytecode is language-identical, CLAUDE.md §7).

### 5.2 `deploy-all` (generalize `install_tworoom.py`)

`install_tworoom.py` was the literal hand-coded 2-field permanent install; `tools/deploy_campaign.py` generalizes its exact shape for arbitrary N:

1. **ONE pre-deploy snapshot** of the whole mod folder → `backups/<folder>.pre-<campaign>.<stamp>` (`install_tworoom.py:45-47`). This is the critical reversibility choice — **do NOT use `deploy_field`'s per-id revert** (the generated `deploy_field` `revert_deploy_<id>.py`), whose per-id DictionaryPatch line-merge can wipe a sibling's `FieldScene` line → black-screen warp to an unregistered id (CLAUDE.md §3 records this exact failure). One set-wide snapshot → one `revert_campaign.py` that restores all N fields + the New-Game override atomically.
2. **Copy each member's assets:** EVT `.eb` (7 langs) for all; `.mes` blocks; and the FBG scene dir **only for editable members** (skip for borrow — `deploy_field.py:110-113` already guards this; `install_tworoom.py:64` relies on borrow shipping EVT-only). Route every path through `ModLayout` (`config.py:99-198`: `eb_path`, `mes_path`, `fieldmap_dir`, `dictionary_patch`, `battle_patch`).
3. **DictionaryPatch = the campaign's combined lines verbatim** from the staged dist (`install_tworoom.py:73-75`) — do NOT reuse `deploy_field`'s sandbox identity override (it forces id→4003 / name→TESTROOM, `deploy_field.FID`/`deploy_field.TEST_NAME`, the OPPOSITE of what a campaign needs; each member must deploy at its OWN id/name).
4. **New-Game entry** (§5.3).
5. **Emit `revert_campaign.py`** (full restore from the snapshot, undoing both the field swap AND the New-Game repoint — `install_tworoom.py:77-87`).

Target resolution reuses `deploy_field`'s `.ff9deploy.toml` (mod_folder + id) > `$FF9_MOD_FOLDER` > defaults, bootstrapping a fresh folder with `ModDescription.xml` + empty DictionaryPatch (`deploy_field._worktree_cfg`/`deploy_field._def_folder`).

### 5.3 New-Game entry

`tools/deploy_campaign.py` wires New Game via the proven `retarget_newgame_warp.py` — a **direct field-70 opening-override retarget**. `NewGame()` is stock and drops you at `fldMapNo` 70, so field 70 IS the real New-Game field; the deploy byte-patches the shared `FF9CustomMap` field-70 opening override `EVT_ALEX1_TS_OPENING` so its `Field()` literal points straight at the campaign's entry id. Route: **New Game → field 70 → `Field(entry)`** (direct retarget, no intermediary). A self-seeding verbatim chain bakes its own party/beat via `[startup]`/`[party]` (story_flags' starting-state capstone), so the entry field needs no party-creating hop. This **supersedes** the old field-100-hop `newgame_warp.py` (whose field-100 injection site doesn't exist on every install); `--stock` is a deprecated no-op (`argparse.SUPPRESS`, ignored — the field-70 retarget is universal). Reversible: backs up the 7-lang field-70 override + writes a revert; `revert_campaign.py` undoes the folder snapshot AND the warp.

### 5.4 Worktree / FolderNames / distinct-id constraints (CLAUDE.md §3–§4)

- The campaign deploys into ONE `mod_folder` pinned by `.ff9deploy.toml` and listed in `Memoria.ini [Mod] FolderNames`; a new folder isn't read until added there and the game relaunches.
- All N ids must be ≥4000 and **globally distinct** across every stacked folder (EventDB is a merged dict).
- **First deploy of each NEW id needs one relaunch** to register its DictionaryPatch line; F6 Reload/Warp only work once registered. `deploy-all` should detect all-new ids and tell the user to relaunch once; subsequent edits use F6.
- **[open]** Whether `deploy-all` also handles minted BATTLE scenes (the encounter `scene` ids 22/27/28/29 in the trace are *real existing* battle scenes referenced through the BattlePatch merge — no minting needed; minted battle scenes are a separate `deploy_battle.py` path, deferred to a later version).

---

## 6. Worked example end-to-end (REAL Ice Cavern, fields 300–312)

```
# 1. Walk + fork the region from real game bytes (dry-run first to see the blast radius)
py -m ff9mapkit import-chain 300 --zones iccv --max-fields 20 --dry-run
   -> prints the adjacency list: 13 fields 300..312, the linear spine
      300->301->...->305->307->309->310->311->312, the 305<->306 side-branch,
      the 307->{308,309} fork, all bidirectional; flags: 'none gated'; 2 termini
      (300 worldmap-in, 312 worldmap-out); 1 scripted seam (308->309), 1 cutscene
      seam (306->652). All area<10 -> "will fork as --editable".

# 2. Commit the fork
py -m ff9mapkit import-chain 300 --zones iccv --id-base 4100 \
     --campaign-name ICE_CAVERN --out campaign/ice/    # area<10 members fork editable automatically
   -> writes campaign/ice/{IC_ENTRANCE.field.toml ... IC_OUTSIDE.field.toml}
      + their camera.bgx / walkmesh.bgi / layer PNG sidecars (editable scenes)
      + campaign.toml (§3.2, ids 4100..4112, edges retargeted to names)
   -> per-node print mirrors _cmd_import (cli.py:297-336); then the chain summary:
      "13 fields forked into campaign/ice, 22 gateways retargeted in-chain,
       3 edges left as seams (author fresh). Flag deps: none. Next: build-all."

# 3. EDIT (the human's work): repaint each editable layer PNG; author the 3 seams
#    (308's exit, 306's Marsh stub, 312's worldmap exit); optionally add NPCs/chests
#    per member field.toml (empty rooms otherwise). Set a save point on IC_HUB.

# 4. Build the whole campaign into one staged mod
py -m ff9mapkit build-all campaign/ice/campaign.toml --out dist/ice/
   -> build_mod over 13 projects: ONE DictionaryPatch (13 FieldScene lines,
      ids 4100..4112), merged BattlePatch (scenes 22/27/28/29), ModDescription.
   -> cross-field lint: all 22 edges resolve, ids distinct & >=4000, text_blocks ok.

# 5. Deploy reversibly + wire New Game to the entry field
py tools/deploy_campaign.py campaign/ice/campaign.toml --mod-folder FF9CustomMap-ice \
     --entry IC_ENTRANCE --apply        # omit --apply for a dry-run that prints the plan + touches nothing
   -> ONE snapshot of FF9CustomMap-ice; build + copy 13x EVT (7 langs) + editable scenes
      + .mes; DictionaryPatch = the 13 lines; New-Game: field-70 override -> 4100(ent 0);
      revert_campaign.py written. "NEW ids 4100..4112 -> RELAUNCH once to register."

# 6. Add FF9CustomMap-ice to Memoria.ini [Mod] FolderNames, RELAUNCH.
#    New Game -> field-70 opening override -> IC_ENTRANCE (4100, entrance 0)
#    -> walk the cavern: 4100->4101->...->4105 (save at hub) ->4107 (branch)
#    ->4109->4110->4111->4112; encounters fire on the 8 non-safe screens
#    (scenes 22/27/28/29 by depth); 4112 worldmap exit re-authored as the author chose.
#    F6 -> Warp -> 4100 reaches it directly thereafter (no relaunch).
```

**STOP and ask the human to playtest** after step 6 — per Hard-Constraint §2, the chain isn't "working" until walked in-game.

---

## 7. Scope & risks

### What v1 does NOT do (state plainly — match `import`'s existing philosophy)

- **Empty rooms.** `eventscan` deliberately extracts only unambiguous single-opcode patterns (gateways/music/encounter/control-dir/ladders); it does NOT scan **NPCs, dialogue, arbitrary event triggers, cutscenes, or party/spawn tables.** A forked chain is **walkable + connected with real art/camera/encounters/ladders, but empty of characters and story.** That is the realistic, honest deliverable.
- **No flag-gate fidelity.** Real doors are often flag-gated; `scan_gateways` extracts the static zone+target only. A fork may expose doors the real game hid behind a flag, or omit dynamics. (Ice Cavern is clean — no inter-screen gates — but the general case isn't.)
- **No custom art unless repainted.** Borrow members reuse real art; editable members ship the field's *exported* art (needs each field exported in-game first via `Memoria.ini [Export]`) which the human then repaints.
- **Single spawn per field** (§2.6) — entrance imported/round-tripped but the landing position is the default centre; multi-entrance landing deferred.
- **Scripted/cutscene transitions invisible** (§2.2) — 308's one-way `Field(309)` and 306's `Field(652)` are seams to author by hand.
- **Additive only — never destructive.** A chain mints NEW ids ≥4000 and borrows art via DictionaryPatch; it never repurposes a real id, so it can't break a live cutscene (unlike REPURPOSE). The one non-additive act — making the chain reachable from the *real* game — would edit a real field's gateway; out of scope for v1 (chain reached via New-Game hook or F6 warp).

### Honest boundaries

- **Graph explosion is the headline risk.** FF9's field graph is huge and densely cross-linked; a naive unbounded BFS from a town hub pulls hundreds. `--max-hops` alone is weak (a hub at hop 2 fans out enormously). **REQUIRE a zone allowlist (`--zones` folder-prefix) OR a hard `--max-fields` that aborts loudly.** Default to small max-hops + `--max-fields` (25) and force opt-in for more. (Ice Cavern is the easy case — self-contained, `--zones iccv` captures it cleanly.)
- **Un-borrowable / crashing destinations.** Area < 10 black-screens (common in early game — Alexandria area 1, cargo ship area 0); **field 100 BOTH is area<10 AND crashes** (CLAUDE.md §5). Need a **data-driven crash denylist** (seed: field 100) + an **area<10 → auto-editable fallback**. Per-node failure must isolate (skip + warn + leave inbound edges as live seams), never abort the chain — `write_field_project` raises `RuntimeError` for area<10 (`extract.write_field_project`); `import-chain` must catch and degrade.

### Load-bearing in-game tests (the human's verifications — I cannot see the game)

1. **A contiguous ≥4000 block registers** (e.g. 4100..4112 all warp-able) — the id-ceiling is unverified.
2. **Save → Continue inside a custom field (≥4000)** persists and reloads (the campaign is only "real" if you can save mid-cavern).
3. **Per-field entrance → spawn** lands the player at the right door (today single-spawn; confirm it's acceptable, or it justifies §2.6).
4. **Party on entry** — New Game routes field-70 → `Field(entry)` (direct retarget) and the self-seeding verbatim chain's `[startup]`/`[party]` bakes the party/beat into the entry fork's own `.eb`.
5. **The New-Game retarget** lands in the entry field and doesn't disturb the normal opening.

---

## 8. Phased implementation plan

Each phase independently testable; sizes are relative.

| Phase | Deliverable | Independently testable by | Size |
|---|---|---|---|
| **P1 — Read-only graph walk + print** ✅ **DONE** | `ID_TO_FBG`/`ID_TO_EVT` + `EventBundle` (`extract.py`); `scan_all_warps` 3-way taxonomy (`eventscan.py`); pure bounded BFS + `render` (`chain.py`); zone-aware bounds (zones / max-hops / stop-at / no-FBG / denylist / max-fields loud abort); `import-chain <seed> [--zones a,b]`. | ✅ `import-chain 300 --zones iccv,vgdl` reproduces the traced Ice Cavern graph (spine + 305 hub + 307→{308,309} STORY-COND, 300/311/312 overworld exits, 306/308 seams). 12 offline tests pass. | **M** (reverse-map + BFS; ~80% reused) |
| **P2 — Emit campaign.toml + forks** ✅ **DONE** | `campaign.py` (assign_ids + per-member fork loop via `write_field_project`/`write_editable_project`) + `extract` `id_remap` kwarg doing the retarget at the gateway-emit site; out-of-chain→seam stub; area<10→editable (degrade to logic-only + `needs_export` when art absent); `campaign.toml` array-of-tables. | ✅ Real Ice Cavern: 13 members 6000–6012, 22 retargeted edges, IC_STA STORY-COND twins→6008/6009, IC_WAF no bogus gateway, seams 2 scripted+3 overworld. 6 offline tests + 1 real-bytes test. | **M–L** (retarget + id-rewrite) |
| **P3 — build-all** ✅ **DONE** | `campaign.load_campaign` + `build_campaign` + `validate_ids`; `FieldProject.load` per member from its subdir; distinct text_block per member; `build-all` CLI → `build_mod(mod_name=campaign folder)`; `--allow-artless` guard. | ✅ Real Ice Cavern: one 13-line DictionaryPatch (30100–30112), InstallationPath `FF9CustomMap-ow`, retargeted gateways survive compilation. 3 tests + 478 kit tests pass. | **S** (~90% reused `build_mod`) |
| **P4 — deploy-all + New-Game** ✅ **DONE** (in-game proven) | `tools/deploy_campaign.py`: one snapshot + wholesale dist replace (no per-id merge), New Game via `retarget_newgame_warp.py` (direct field-70 override retarget → New Game → field 70 → `Field(entry)`; `--stock` a deprecated no-op; no field-100 hop — a self-seeding chain bakes party/beat via `[startup]`/`[party]`), one `revert_campaign.py` (undoes folder + warp); **dry-run unless `--apply`**. | ✅ offline: real Ice Cavern dry-run prints the plan + lints + touches nothing. **IN-GAME:** `--apply` → relaunch → New Game lands in the entry field → walk + save/Continue → revert. | **M** |
| **P5 — campaign lint + flag scanners** ✅ **DONE** (alloc deferred) | `lint_campaign` (errors: edges/entry/seams/ids/member-files; warnings: stacked doors, explicit-flag dangling/dup) + GLOB flag scanners in eventscan (raw-byte, GLOB-only); `lint-campaign` CLI + auto-lint in build-all. **Deferred:** per-member flag auto-allocation (latent on empty forks), named-flag registry. | ✅ Real Ice Cavern lints OK + IC_STA stacked-door warning; scanners round-trip region.set_var/flag_gate + detect Gizamaluke 703 / Dali 402; 9 tests + 487 kit tests pass. | **M** |

**Critical-path note:** P1→P2 was the genuinely new engineering (reverse-map + retarget). P3 was nearly free (`build_mod` already builds N fields). P4 is mechanical reuse, validated by the in-game handshake (relaunch + the field-70 New-Game retarget). P5 (flag/id correctness) is the safety net for the one root-cause bug (§4.1) that silently corrupts saves. Build order was **P1+P2 (read/fork preview) → P5 (correctness) → P3+P4 (the deployable mod)** so no one deploys a flag-colliding campaign.

---

## Appendix — the raw Ice Cavern trace (live, from p0data)

Method: id→`.eb` via `_fieldtable.FBG_TO_EVT` inverted; per field `eventscan.scan_gateways/scan_music/scan_encounter` + a raw `Field(0x2B)`/`WorldMap(0xB6)` opcode pass (shared Chocobo/mognet warps 2950-2955 filtered as non-geography). Field names from `reference/field-manifest.tsv`.

| id | name | FBG folder | area | role |
|---|---|---|---|---|
| 300 | Ice Cavern/Entrance | fbg_n05_iccv_map085_ic_ent_0 | 5 | worldmap-in; cutscene intro; → 301 |
| 301 | Ice Cavern/Ice Path | …map086_ic_stp_0 | 5 | ↔300, →302; enc scene 22 freq 40 |
| 302 | Ice Cavern/Ice Path | …map087_ic_ter_0 | 5 | ↔301, →303; enc 22 freq 24 |
| 303 | Ice Cavern/Icicle Field | …map088_ic_jmp_0 | 5 | icicle-jump; ↔302, →304; enc 27 freq 22 |
| 304 | Ice Cavern/Ice Path | …map089_ic_bri_0 | 5 | bridge; ↔303, →305; enc 27 freq 22 |
| 305 | Ice Cavern/Ice Path | …map090_ic_men_0 | 5 | **HUB/save**; ↔304, →306, →307; music 60; no enc |
| 306 | Ice Cavern/Cave | …map091_ic_mrm_0 | 5 | dead-end (Mene); ↔305; +scripted Field(652)→Marsh (seam) |
| 307 | Ice Cavern/Ice Path | …map092_ic_sta_0 | 5 | branch; ↔305, →308, →309; enc 28 freq 80 |
| 308 | Ice Cavern/Waterfall | …map094_ic_waf_0 | 5 | scripted Field(309), **no walk-in gateway** (seam) |
| 309 | Ice Cavern/Waterfall | …map093_ic_wbf_0 | 5 | ↔307, →310; enc 29 freq 72; music 60 |
| 310 | Ice Cavern/Waterfall | …map095_ic_caf_0 | 5 | ↔309, →311; enc 29 freq 80 |
| 311 | Ice Cavern/Exit | …map096_ic_xit_0 | 5 | ↔310, →312; worldmap plumbing; music 60; no enc |
| 312 | Ice Cavern/Outside | fbg_n06_vgdl_map097_dl_viw_0 | 6 | **worldmap-out** (38 WorldMap ops, no Field gateway); Dali plateau |

Walkable graph (bidirectional unless noted): `300→301↔302↔303↔304↔305`, hub `305↔306` (dead-end) and `305↔307`, `307→{308,309}`, `309↔310↔311→312`. Termini: 300 (worldmap-in), 312 (worldmap-out). Seams to author: 308→309 (scripted), 306→652 (cutscene), 312→worldmap.
