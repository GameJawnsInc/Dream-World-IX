# Global Resources — the campaign-wide state layer (quick reference)

## C. The kit's allocation bands (governed by the campaign registry)

| Namespace | Band | Defined at | Alloc scope TODAY | Persistence |
|---|---|---|---|---|
| Event once-flags | 9100+ (single-field; `flags.AUTO_EVENT_BASE`) | `content/event.py` | single-field default (skips the project's authored flags); campaign → per-member block via `build._FlagAlloc` | GLOB / save |
| Cutscene once-flags | 9200+ (single-field; `flags.AUTO_CUTSCENE_BASE`) | `content/cutscene.py` | single-field default (authored-flag skip); campaign → member `base+0` | GLOB / save |
| Choice gate flags | 9300+ (single-field; `flags.AUTO_CHOICE_BASE`) | `content/choice.py` | single-field default (authored-flag skip); campaign → member `base+32..` | GLOB / save |
| on_entry once-flags | 9400+ (single-field; `flags.AUTO_ONENTRY_BASE`) | `content/onentry.py` | single-field default (authored-flag skip); campaign → explicit `flag` required | GLOB / save |
| [ate] availability flag | 9500+ (single-field; `flags.AUTO_ATE_BASE`) | `content/ate.py` | single-field default (authored-flag skip); campaign → explicit `flag` required | GLOB / save |
| Campaign flags | **8712+** (`FIRST_SAFE_FLAG`), 64/field | `campaign.py` | per-member `flag_base+i*K`, lint-bounded | GLOB / save |
| Choice mask scratch | byte 2040 (bits 16320+) | `content/region.py:57` | campaign-global | GLOB / save |
| Field ids | 10–3100 real (locked) · 4000–9899 content · 30000–32767 scratch | `pack.py` | per-mod hash block; `id_base+i` in campaign | static reg |
| Battle scenes | 1–177 real · 200+ mint | `battle/build.py:41` (`_REAL_BBG_MAX`) | manual | static reg |
| Text block (mesId) | default 1073 | `pack.py:73`, `campaign.py:112` | per-field | static reg |
| TXID (per line) | 500+ | `content/text.py:23` | per-field, `base+i` | static reg |
| Worldmap locations | 9000–9012 (engine-reserved) | `eventscan.py:27` | not allocatable | engine |
| Models / anims / items | fixed engine tables | `_modeldb.py`/`_animdb.py`/`_itemdb.py` | read-only | engine |

Band notes:

- **Why `FIRST_SAFE_FLAG` = 8712:** everything below it is written by ordinary play — bits
  8192–8367 are stock Mognet mailbox slot bytes, 8376–8511 the Mognet GIVE/READ lock tables, and
  8512–8711 the read-mail payload bytes (whole-byte-written at any real moogle) — so a kit flag
  there corrupts real letter state; 8712 (byte 1089) is the first clear bit.
- **Campaign flags:** each member gets its own `flag_base + i*K` block (packed cutscene `+0`,
  events `+1..+31`, choices `+32..+63`), so two members' auto-allocated once-flags can never
  share a bit; `lint_campaign` errors on any member block or explicit flag inside the Mognet
  band 8376–8711 or at/above the choice scratch (bit 16320).
- **Named cross-field flags:** a gate one field sets and another reads goes through the campaign
  `[[flag]]` table (`{name, index}`), which resolves the name to one campaign-wide index — the
  only safe cross-field gate; shared/named flags live in a band above the per-member blocks
  (lint asserts it).
- **Single-field auto bands (9100+–9500+):** placed above the behavior compiler's flag band
  (8860–9080) and below its blackboard byte band, and the allocator skips any index the project
  references explicitly (`flags.collect_safe_flag_indices`), so a defaulted once-flag never
  aliases an authored story flag in the same build.
- **Field ids:** must be globally distinct across *every installed mod folder*, not just within
  one campaign — the launch registries (§B below) are one merged dict; `ff9mapkit lint-campaign`
  validates the band and distinctness, flags dangling `[[edge]]`/`[[seam]]` rows and duplicate
  member names, and checks that every cross-field `requires_flag` has a producer (else the gate
  is permanently locked).

### Var-class token bytes (for raw-byte scanning) — `content/region.py:40-49`
`GLOB_BOOL=0xC4` (persistent) · `MAP_BOOL=0xC5` (transient) · `GLOB_UINT8=0xD5` (transient) ·
`GLOB_INT16=0xD8` (arrival-entrance var, idx 2) · `MAP_INT16=0xD9` · `GLOB_UINT16=0xDC` (choice mask).
Long-index form: `class|0x20` (e.g. `0xE4`) + 2-byte LE — why the high safe-band indices work.

---

> **Why this exists:** field authoring has two layers — **Scenes** (`field.toml`: camera/walkmesh/art)
> and **Scripts** (`.eb` logic). The third is **Resources** — the shared id/flag namespaces
> that fields reference *by number* and that must be allocated coherently across a whole campaign.
> This file is the map of that layer. Grounded against the live Memoria source + the kit code
> (citations inline). Companion to `CAMPAIGN_IMPORT.md` (the import-chain/build-all design).

---

## The one-paragraph mental model

FF9 global state splits three ways. **(A)** Two save-persistent blobs: `gEventGlobal` (the 2048-byte
story-flag heap) and `FF9StateGlobal` (player roster/items/gil/party/map-position). **(B)** Static
registries merged from every mod folder at launch (`EventDB`/`SceneData`/`MapModel`) — never saved,
which is *why ids must be globally distinct across folders*. **(C)** The kit's own allocation bands
(flag/id/text namespaces) — single-field builds use the fixed per-field default bands, while a
**campaign-wide allocation registry** owns (C): per-member flag blocks (`build._FlagAlloc`), shared
named flags (the `[[flag]]` table), and id/flag-collision lint (`campaign.lint_campaign`). That's the
"Resource" layer.

---

## A. Save-persistent runtime state (the actual global variables)

Only TWO mutable blobs survive a save. Everything per-field is session-transient (wiped on field load).

### A1. `gEventGlobal` — the story-flag heap
- `EventState.gEventGlobal = Byte[2048]` — `Memoria/Assembly-CSharp/Global/Event/EventState.cs:10`.
- Base64'd into the save JSON under `"gEventGlobal"` — `JsonParser.cs:579` (read `:521`). **SAVE-persistent.**
- Bit-indexed: `byte = N>>3`, `bit = N&7` — `EBin.cs:1845`.
- **It is a SHARED namespace, not "your flags":** ScenarioCounter = bytes [0..1] (FF9 master story int),
  second counter [2..3], navi/worldmap cursors 92–102 (`ff9.cs:2315`; WorldConfiguration reads [101]/[102]).
  Kit flags deliberately sit HIGH (the safe band 8712+) + choice scratch at byte 2040 to clear all of it.

### A2. `FF9StateGlobal` (`FF9StateSystem.Common.FF9`) — player data
- `Global/ff9/State/FF9StateGlobal.cs:8`. The kit barely touches this today. Major tables:
  - `player: Dictionary<CharacterId,PLAYER>` — roster, stats, equip, abilities (`:938`)
  - `party: PARTY_DATA` → `member: PLAYER[4]` + `gil: UInt32` (`:939`)
  - `item: List<FF9ITEM>` + `rare_item_obtained/used` key-items (`:974-976`)
  - `fldMapNo / wldMapNo / fldLocNo / wldLocNo` — **saved map position** (`:905-955`); this is what
    Save→Continue-inside-a-custom-field round-trips (CAMPAIGN_IMPORT §7 test #2).

### Session-only (NOT saved — don't treat as cross-field state)
- `EventContext.mapvar = Byte[80]` (`EventContext.cs:9,113`; `cMapVarN=80` at `EventEngine.Static.cs:14`) — **wiped every field load.**
- Var sources (`EBin.VariableSource`, `EBin.cs:2550`): `Global=0` → gEventGlobal (persistent),
  `Map=1` → mapvar (transient 80B), `Instance=2` → per-object. Selection: `EBin.cs:1617`.
  ⚠ **HW naming is INVERTED** (HW "GlobBool" = engine Map = transient). A high index in MAP space is
  out-of-bounds past 80B → hard crash. **Use GLOB for anything cross-field or once-ever.**

---

## B. Static registries — merged at launch, never saved

Process-global `static` dicts, rebuilt from every mod folder's DictionaryPatch at launch.
**This is the cross-folder id-collision rule**: same id in two folders = one key clobbered.

- `FF9DBAll.EventDB` — field id → `EVT_*` script (`FF9DBAll.Events.cs:7`); `FieldScene` line writes it (`DataPatchers.cs:380`).
- `FF9BattleDB.SceneData` — `BSC_*` ↔ battle scene id; `MapModel` — scene → `BBG_*` (`DataPatchers.cs:413`).
- Text/MES blocks — the `text_block` (default 1073) + per-line TXID namespace.
