# Global Resources — the campaign-wide state layer (quick reference)

> **Status: SHIPPED.** This began as the design doc for the campaign-wide **Resources** layer (P5);
> that layer is built. The flag scanners live in `eventscan.py` (`scan_flags_set` / `scan_required_flags`
> / `scan_edge_flag_gates`), the campaign lint in `campaign.py` (`lint_campaign`, CLI `ff9mapkit
> lint-campaign`), and the per-member flag allocation in `build._FlagAlloc`. The conceptual A/B/C model
> below is unchanged; STATUS notes flag what landed.

> **Why this exists:** field authoring has two layers — **Scenes** (`field.toml`: camera/walkmesh/art)
> and **Scripts** (`.eb` logic). The third is **Resources** — the shared id/flag namespaces
> that fields reference *by number* and that must be allocated coherently across a whole campaign.
> This file is the map of that layer. Grounded against the live Memoria source + the kit code
> (citations inline). Companion to `CAMPAIGN_IMPORT.md` (the import-chain/build-all design; this file
> motivated P5, which is DONE).

---

## The one-paragraph mental model

FF9 global state splits three ways. **(A)** Two save-persistent blobs: `gEventGlobal` (the 2048-byte
story-flag heap) and `FF9StateGlobal` (player roster/items/gil/party/map-position). **(B)** Static
registries merged from every mod folder at launch (`EventDB`/`SceneData`/`MapModel`) — never saved,
which is *why ids must be globally distinct across folders*. **(C)** The kit's own allocation bands
(flag/id/text namespaces) — single-field builds keep the historical per-field constants, while a
**campaign-wide allocation registry** owns (C): per-member flag blocks (`build._FlagAlloc`), shared
named flags (the `[[flag]]` table), and id/flag-collision lint (`campaign.lint_campaign`). That's the
"Resource" layer — built.

---

## A. Save-persistent runtime state (the actual global variables)

Only TWO mutable blobs survive a save. Everything per-field is session-transient (wiped on field load).

### A1. `gEventGlobal` — the story-flag heap
- `EventState.gEventGlobal = Byte[2048]` — `Memoria/Assembly-CSharp/Global/Event/EventState.cs:10`.
- Base64'd into the save JSON under `"gEventGlobal"` — `JsonParser.cs:579` (read `:521`). **SAVE-persistent.**
- Bit-indexed: `byte = N>>3`, `bit = N&7` — `EBin.cs:1845`.
- **It is a SHARED namespace, not "your flags":** ScenarioCounter = bytes [0..1] (FF9 master story int),
  second counter [2..3], navi/worldmap cursors 92–102 (`ff9.cs:2315`; WorldConfiguration reads [101]/[102]).
  Kit flags deliberately sit HIGH (8000+) + choice scratch at byte 2040 to clear all of it.

### A2. `FF9StateGlobal` (`FF9StateSystem.Common.FF9`) — player data
- `Global/ff9/State/FF9StateGlobal.cs:8`. The kit barely touches this today. Major tables:
  - `player: Dictionary<CharacterId,PLAYER>` — roster, stats, equip, abilities (`:938`)
  - `party: PARTY_DATA` → `member: PLAYER[4]` + `gil: UInt32` (`:939`)
  - `item: List<FF9ITEM>` + `rare_item_obtained/used` key-items (`:974-976`)
  - `fldMapNo / wldMapNo / fldLocNo / wldLocNo` — **saved map position** (`:905-955`); this is what
    Save→Continue-inside-a-custom-field round-trips (CAMPAIGN_IMPORT §7 test #2).

### Session-only (NOT saved — don't treat as cross-field state)
- `EventContext.mapvar = Byte[80]` (`EventContext.cs:9,113`; `cMapVarN=80`) — **wiped every field load.**
- Var sources (`EBin.VariableSource`, `EBin.cs:2550`): `Global=0` → gEventGlobal (persistent),
  `Map=1` → mapvar (transient 80B), `Instance=2` → per-object. Selection: `EBin.cs:1617`.
  ⚠ **HW naming is INVERTED** (HW "GlobBool" = engine Map = transient). A high index in MAP space is
  out-of-bounds past 80B → hard crash. **Use GLOB for anything cross-field or once-ever.**

---

## B. Static registries — merged at launch, never saved

Process-global `static` dicts, rebuilt from every mod folder's DictionaryPatch at launch.
**This is the cross-folder id-collision rule** (CLAUDE.md §3): same id in two folders = one key clobbered.

- `FF9DBAll.EventDB` — field id → `EVT_*` script (`FF9DBAll.Events.cs:7`); `FieldScene` line writes it (`DataPatchers.cs:380`).
- `FF9BattleDB.SceneData` — `BSC_*` ↔ battle scene id; `MapModel` — scene → `BBG_*` (`DataPatchers.cs:413`).
- Text/MES blocks — the `text_block` (default 1073) + per-line TXID namespace.

---

## C. The kit's allocation bands (governed by the campaign registry)

| Namespace | Band | Defined at | Alloc scope TODAY | Persistence |
|---|---|---|---|---|
| Event once-flags | 8000+ (single-field) | `content/event.py:27` | single-field default; campaign → per-member block via `build._FlagAlloc` | GLOB / save |
| Cutscene once-flags | 8100 (single-field) | `content/cutscene.py:37` | single-field default; campaign → member `base+0` | GLOB / save |
| Choice gate flags | 8200+ (single-field) | `content/choice.py:35` | single-field default; campaign → member `base+32..` | GLOB / save |
| Campaign flags | **8512+** (`FIRST_SAFE_FLAG`), 64/field | `campaign.py` | per-member `flag_base+i*K`, lint-bounded (**was 8300 → chest collision, FIXED**) | GLOB / save |
| Choice mask scratch | byte 2040 (bits 16320+) | `content/region.py:57` | campaign-global | GLOB / save |
| Field ids | 4000–9899 content · 30000–32767 scratch | `pack.py` | per-mod hash block; `id_base+i` in campaign | static reg |
| Battle scenes | 1–177 real · 200+ mint | `battle/build.py:34,162` | manual | static reg |
| Text block (mesId) | default 1073 | `pack.py:73`, `campaign.py:112` | per-field | static reg |
| TXID (per line) | 500+ | `content/text.py:23` | per-field, `base+i` | static reg |
| Worldmap locations | 9000–9012 (FIXED) | `eventscan.py:27` | not allocatable | engine |
| Models / anims / items | fixed engine tables | `_modeldb.py`/`_animdb.py`/`_itemdb.py` | read-only | engine |

### Var-class token bytes (for raw-byte scanning) — `content/region.py:40-49`
`GLOB_BOOL=0xC4` (persistent) · `MAP_BOOL=0xC5` (transient) · `GLOB_UINT8=0xD5` (transient) ·
`GLOB_INT16=0xD8` (arrival-entrance var, idx 2) · `MAP_INT16=0xD9` · `GLOB_UINT16=0xDC` (choice mask).
Long-index form: `class|0x20` (e.g. `0xE4`) + 2-byte LE — why the 8000 band works.

---

## The root-cause bug this layer fixes — FIXED 2026-06-10 (story_flags branch)

`build_script`'s once-flag counter **reset to 0 per build**, flag = `BASE + counter` computed *per-field*.
So field B's first chest and field A's first chest BOTH picked 8000 → looting A marked B looted
campaign-wide. Harmless for one field; a **latent save-corrupter for N fields**. **Plus** `campaign.py`'s
reserved `flag_base=8300` + 64/member **collided with real-FF9's treasure-chest bitfield at bits 8376–8511**
(census-verified; `research/STORY_FLAGS.md` §4) → corrupting real chest-opened state.

**Fix (landed):** `build._FlagAlloc` parameterizes the three allocators by an optional per-member
`flag_base` threaded through `build_script` + `lint_logic` (default `None` = the historical 8000/8100/8200
constants, so single-field builds stay **byte-identical**; campaign members get `flag_base + i*K`, packed
cutscene `+0` / events `+1..+31` / choices `+32..+63`). The default `flag_base` moved **8300 → 8512**
(`campaign.FIRST_SAFE_FLAG`, the first bit clear of ALL real usage; max real-used bit = 8511).
`lint_campaign` now errors on any member block / explicit flag inside the chest band 8376–8511 or at/above
the choice scratch (bit 16320). (CAMPAIGN_IMPORT.md §4.1; tests in `test_campaign.py` / `test_build.py`.)

---

## What the "Resource layer" (P5) is — SHIPPED

> **Status: P5 DONE.** All three pieces below landed (mirrors `CAMPAIGN_IMPORT.md` "P5 DONE").

1. **Flag registry** — named flags → one campaign-wide index, so cross-field gates (A sets
   `ice_path_unlocked`, B reads it) resolve to the *same* bit. The only safe cross-field gate. SHIPPED:
   the campaign `[[flag]]` table (`campaign.py:64`, `{name, index}`) + name resolution in `build.py`
   (`build.py:150-151`, `_story_names :289`); `build_script` is parameterized by a per-field
   `flag_base` (default = current constants so single-field builds are byte-identical) via
   `build._FlagAlloc`. Shared/named flags live in a band ABOVE the per-member blocks (lint asserts it).
2. **Id registry** — assert ids ≥4000 AND **globally distinct across stacked folders** (not just within
   the campaign), because EventDB/SceneData are one merged dict. SHIPPED: `validate_ids` (lint check
   (a), ids non-empty/distinct/[4000,32767]) in `lint_campaign`.
3. **Cross-field lint** — `lint_campaign` checks dangling `[[edge]]`/`[[seam]]`; duplicate ids + member
   names; every cross-field `requires_flag` has a producer (else "permanently locked"); no unintended
   same-index writes across members. SHIPPED (`campaign.lint_campaign`, CLI `ff9mapkit lint-campaign`).

The one genuinely-open refinement is a campaign-wide **named-flag auto-allocation** sweep (today shared
`[[flag]]` rows carry explicit indices the lint validates, rather than the registry auto-assigning them);
not required for safety — the lint surfaces any explicit collision.

### The raw-byte scanners P5 added (match around opcode `0x05`, NOT `instr.args`) — SHIPPED in `eventscan.py`
- `scan_flags_set(eb)` — flag WRITES: `05 C4 <idx> 7D <i16> 2C|3F 7F` + long-index `0xE4` form
  (`eventscan.py:1356`). Returns the `(glob_idx, op)` pairs a field writes.
- `scan_edge_flag_gates(eb)` — flag READS gating an exit: `05 C4 <idx> 7F 03|02 01 00 <RETURN>`
  (`eventscan.py:1399`). Filter to GLOB (`0xC4`/`0xE4`) — MAP/UINT8 are transient = false links.
- `scan_required_flags(eb)` — the general flag-READ form (any guarded-block length, not just the strict
  kit prologue) for real-field gates (`eventscan.py:1377`).

---

## TL;DR for a session picking this up
- The save has exactly **two** mutable global blobs: `gEventGlobal` (flags + ScenarioCounter) and
  `FF9StateGlobal` (player data). Per-field `mapvar` is transient — never use it for cross-field state.
- Ids are **global keys** across mod folders; flags are a **shared 2048-byte namespace**. Both get
  campaign-wide allocation (not per-field counters) — the registry below.
- **P5 is SHIPPED**: the flag registry (`[[flag]]` table + `build._FlagAlloc` per-member `flag_base`)
  and cross-field lint (`campaign.lint_campaign`, CLI `lint-campaign`). The design notes are in
  `CAMPAIGN_IMPORT.md` §4 + §8 (P5 marked DONE there).
