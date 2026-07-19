# Story flags — gEventGlobal (authoring reference)

Canonical sources: memory `project-ff9-story-flags.md` (heap map, census, scopes) and `ff9mapkit/ff9mapkit/flags.py` (the code registry — the single source of truth for `FIRST_SAFE_FLAG`, `CHEST_FLAG_LO/HI`, `CHOICE_SCRATCH_FLOOR`, named vars, scenario milestones). Lines below are quoted verbatim from those sources or CLAUDE.md §7.

## Persistence: GLOB vs MAP

Quoted verbatim from CLAUDE.md §7:

> - A var's **source** decides persistence: **GLOB (src 0) = save-backed `gEventGlobal`** (2048
>   bytes, persists across field reloads + saves) vs **MAP (src 1) = per-field, WIPED on every
>   field load.** HW naming is INVERTED (HW "GlobBool" = engine **Map** = transient).
> - `EventContext.mapvar` is **only 80 bytes** → a high flag index in MAP space is out-of-bounds
>   = hard crash. **Use GLOB for chests / story flags / cutscene-once.** The kit uses `GLOB_BOOL
>   = 0xC4` (transient dev twin = `MAP_BOOL = 0xC5`) with flag bases in the **8000+** band (clear
>   of base-game flags); indices > 0xFF need the long-index token encoding (`class|0x20` + 2-byte
>   LE) — which is why the 8000 band works. `gEventGlobal` index N → byte `N>>3`, bit `N&7`.
> - A `once=true` event/cutscene won't replay for *testing* once its persistent flag is set —
>   use `once=false`, a fresh New Game, a distinct flag index, or F6 → Flags → reset.

## The heap map

Quoted verbatim from `project-ff9-story-flags`:

> **FF9 story/event state = `EventState.gEventGlobal`, a save-persistent Byte[2048]** (Base64 in the save
> JSON under key `"gEventGlobal"`). It is the engine's `VariableSource.Global` space. Three kinds of content:
> - **ScenarioCounter** — UInt16 LE at bytes 0-1, the master story-progress value (1..12000), near-monotonic
>   by disc/area. `FieldEntrance` = Int16 @ bytes 2-3.
> - **bit-flags** — ~1051 distinct, bits 184..8511 (story once-events, gates, chest-opened).
> - **word-counters** — Byte/Int16/UInt16 at fixed byte offsets.

> **Bit type indexes BITS** (byte N>>3, bit N&7); **Byte/Int16/UInt16 index BYTES**.

> **Byte 23 (bits 184/191) is an ACTIVE engine menu/transition handshake, NOT a story flag** — set bracketing
> `Menu` calls, re-checked + cleared every `Main_Init` (forces `FieldEntrance=10000` if set on load). Rewritten
> every field load → never durable. A mod must replicate the prologue and never allocate there. Low bytes 8-24
> generally = standard per-field init region (avoid).

## The safe band (>= 8712) and the chest band

Quoted verbatim from `project-ff9-story-flags`:

> Real FF9's treasure-chest "opened" bitfield is **bits 8376-8511** (bytes 1047-1063, 48 chest fields).
> `campaign.py` default `flag_base` 8300 → 8512 → **8712** (`FIRST_SAFE_FLAG`; the 8512 stop missed stock's BYTE-addressed vars — bits 8512-8711 are read-mail's payload Byte[1064-1073]/[1079-1088], whole-byte-written by ordinary play; true max real-used bit = 8711).
> **Safe-band audit:** ≥8712 is CLEAN — the ENGINE tops at byte 975 (TH) + 510-525 (voice) + ≤207 (scenario/words), and FIELD SCRIPTS top at byte 1088 (the read-mail sender payload; 2026-07-19 census incl. byte-addressed vars).

Historical per-category bands when no `flag_base` is given: EVENT 8000 / CUTSCENE 8100 / CHOICE 8200 (single-field builds stay byte-identical); campaign members get `flag_base + i*K` packed (cutscene `+0`, events `+1..+31`, choices `+32..+63`).

## The 5 verbs

Quoted verbatim: "**All 5 verbs done** (view/understand/name/create/recreate)."

- VIEW — `ff9mapkit flags` (browse the registry) / `flags-inspect <save>` (decode a save's `gEventGlobal`) + the in-game F6 → Flags tab.
- UNDERSTAND — the census-grounded scenario→beat table + named bit regions in `flags.py`.
- NAME — `[[flag]]` tables (name + index) resolved by `flags.resolve_project_flags`; `requires_flag`/`set_flag`/`flag` take a NAME.
- CREATE — the kit's `.eb` flag encoding (this skill owns it).
- RECREATE — `ff9mapkit save-edit <SavedData_ww.dat>` seeds a real save's state.

Boundary: this skill owns AUTHORING flags in an `.eb`; reading/comparing/EDITING a save file (`flags-inspect`/`flags-diff`/`save-edit`, the Memoria extra-file gotcha) belongs to the `editing-ff9-items-and-saves` skill.

## Flag scopes (field / campaign / journey)

A `[[flag]]` is just a name→bit alias on the ONE global array. Table quoted verbatim from `project-ff9-story-flags`:

> | scope | declared in | shared with | GUI editor |
> |---|---|---|---|
> | field-local | `field.toml` `[[flag]]` | one field (e.g. a chest opened-bit) | the field's **Flags** tree section |
> | campaign-shared | `campaign.toml` `[[flag]]` | every member of a campaign | campaign root → **Shared flags…** |
> | journey-global | `journeys.toml` top-level `[[flag]]` | every campaign of a journey (whole game) | journey hub root → **Shared flags…** |

> **Correctness rule** (`lint_manifest` enforces): a journey-global flag index must be in the safe band `[FIRST_SAFE_FLAG 8712, CHOICE_SCRATCH_FLOOR)` AND **ABOVE every journey's campaign windows** (`>= flag_high`) so it can't alias a member's auto once-flag.

> **campaign-shared is the workhorse** (a campaign is a self-contained arc; cross-arc progression usually rides the scenario counter); reach for journey-global only for a flag genuinely read across campaigns.

A `[journey.seed] flags` entry uses the `[startup]` DICT format `[{ flag = "name", value = 1 }]`, NOT a bare name list.

## Pointers

- Memory: `project-ff9-story-flags.md` (heap map + census + scopes + propagation bugs), `project-ff9-npc-on-verbatim.md` (chest flags on verbatim forks).
- Docs: `ff9mapkit/docs/JOURNEYS.md` ("Journey-global story flags"), `ff9mapkit/docs/GLOBAL_RESOURCES.md`.
