# The fork-gate census: four gate forms + the fork-gate lever map

The canonical per-site census is `ff9mapkit/docs/FORK_IDGATE_MAP.md` ("280 gates found · 265
lost on a custom-id fork — SOFTLOCK 12 · FUNCTIONAL 142 · COSMETIC 111") — do not re-derive or
recopy it here. Deep recipe + the suite's origin story: memory
`project-ff9-doeventcode-fork-gates` (which absorbed `project-ff9-narrow-map-fork-letterbox`);
verification method: memory `project-ff9-fork-verification-harness`; per-patch file status:
`memoria-patches/README.md`; user-facing framing: `ff9mapkit/docs/ENGINE.md`.

## The principle (verbatim)

"Any engine behavior hardcoded on a real `fldMapNo` (or FBG name) is LOST on a custom-id
fork." A fork carries the `.eb`, scene, walkmesh, text — but not engine-side per-id tables.

## The four gate forms (each discovered via a real in-game bug)

| # | form | canonical example | lever | patch |
|---|---|---|---|---|
| 1 | `fldMapNo == N` comparison | `FieldMapActorController.cs:923` — the Dante off-mesh exemption (field 105) | `EffectiveFieldId` | s23/s24/s29 |
| 2 | LOCAL ALIAS (`Int16 mapNo = fldMapNo`) | `EventEngine.DoEventCode.cs` — ~150 `mapNo == N` per-field cutscene fixups, none in the literal-token sweep | `EffectiveFieldId` via a local `effMapNo` | s30 |
| 3 | NAME-STRING key (FBG name) | `FieldMapExtraOffset` name-keyed overlay z-offsets; hardcoded `mapName == "FBG_N..."` literals | `EffectiveFieldName` | s31/s32 |
| 4 | LOOKUP ARGUMENT / dict key | `FF9TextTool.LocationName(fldMapNo)` → blank menu LOCATION on a fork | `EffectiveFieldId` on the arg; `FF9TextTool.FieldLocationName` | s33 |

**The durable lesson (verbatim):** "the fork-gate sweep must cover fldMapNo as (1) a `== N`
comparison, (2) a local ALIAS, (3) a NAME key, AND (4) a per-field LOOKUP ARGUMENT/dict key."
The arg-lookup class is the easiest to overlook (no `==`). And per s30: "a fork-gate sweep
must search `<alias> == N` for EVERY local alias of `fldMapNo`, not just the literal token."

## The linchpin: `ForkDonorPatch.txt`

`<forkId> <donorRealId>` per line at the mod-folder root; `EffectiveFieldId` returns the donor
for forks, identity for real ids — so every lever is a no-op on stock content. Emitted by
`build_campaign` on the campaign/journey deploy path AND (since kit commit `cf5a9cf`) by
`tools/deploy_field.py` for any fork with a recorded donor. Read at LAUNCH only (no ~ reload
path) — an A/B test = comment the line + relaunch. Without this file no gate fires at all.

## Patch lever map (`memoria-patches/`)

Scope: the **fork-gate suite proper is s23–s33**; s22/s34/s35/s36 are listed only for context.
The stack as a whole runs **s12–s58** (37 `.patch` files) and grows every engine round — for
anything outside the fork gates, `memoria-patches/README.md` is the authority, not this table.

| patch | class | what it does |
|---|---|---|
| s22 | dev tool | the in-game debug menu (~) (Go/Cheats/Flags/Time) — SHIPS in the bundle; not a fork wrap |
| s23 | id-gate | narrow-map fork width: `NarrowMapList.MapWidth` falls back to the loaded BG's actual width for ids not in the table (before the `500` default) |
| s24 | id-gate core | `DataPatchers.EffectiveFieldId` + the `ForkDonorPatch.txt` reader; + `ForkSiblingField` (an event battle's hardcoded after-battle field redirected to the fork sibling); s28 extends the same lever to the overworld→field entry |
| s29 | id-gate | the remaining SOFTLOCK `== N` wraps (10 fields, 14 lines) |
| s30 | alias | `EventEngine.DoEventCode.cs` local-alias sweep (~150 gates via `effMapNo`) |
| s31 | name-key | `FieldMapExtraOffset` name-keyed overlay offsets via `EffectiveFieldName` |
| s32 | name-key | the name-gate census closure (7 gates: Iifa + space-scene control/menu unlocks, Iifa rain offset, Oeilvert star shader, SPS offsets, Treasure-Hall nudge); `EffectiveFieldName` generalized to resolve by the PASSED name |
| s33 | lookup-arg | wraps `fldMapNo`-as-argument sites (menu LOCATION at BOTH call sites, battle-BGM fallback, mesh-combine, smooth-cam) + the `LocationName <id> <title>` DictionaryPatch directive backing `[field] location` |
| s34 | capability | overworld loose-mesh override (NOT a fork wrap; powers the `world-*` commands) |
| s35 | polish | overlay-texture cache (kills the slow see-through fade on re-entry / battle-return) |
| s36 | experimental | multiplayer co-op ghost sync (head of the s36–s41+ netsync suite; NOT a fork wrap) — SHIPS in the public bundle since 1.0.0b16, flagged EXPERIMENTAL because the wire protocol still changes release to release |

Non-gate uses of `fldMapNo` stay RAW (e.g. `sOriginalFieldNo = mapNo`, the fork's own
`eventIDToFBGID[fldMapNo]` registration) — wrapping those would be wrong; see the memory.

## The founding bug: the narrow-map letterbox (merged history)

Forking a narrow field (e.g. Ice Cavern entrance, field 300, BG width 320) drew off-screen
followers over the side bars: `NarrowMapList.MapWidth(fldMapNo)` is "a hardcoded table keyed
by real field id"; a minted fork id "falls through to the `500` default" → not detected
narrow → widescreen stays on. s23 is the general fix (16 lines, 1 file). This generalizes to
the whole program: any of ~156 fields' worth of id-gated behavior silently drops off a fork.

**Cascade lesson (verbatim):** "one lost id-gate can surface as MULTIPLE unrelated-looking
symptoms." The forked Ice Cavern's broken JUMP was downstream of the no-encounter id-gate
(un-cleared MAP_BOOLs fought the player), not a jump bug — A/B against the real field before
building a phantom fix.

## Verification status (do not re-litigate)

The per-site checklist with the verdict column lives in `ff9mapkit/docs/FORK_IDGATE_MAP.md`.
Summary: only **2507** is crisply cold-fork-testable (**proven**, traversal A/B — and the
harness caught a real kit bug there); `needs-scripted` gates (2512/1656/768) are verified
opportunistically when their zone is forked for real; `low-signal-party` + `ending-only`
gates are accepted as code-verified (identity-safe). Regenerate a target's playbook with
`py tools/verify_fork_gates.py --emit <field>`.
