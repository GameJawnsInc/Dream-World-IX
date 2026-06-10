# FF9 Story-Flag System — Research Report (`ff9mapkit`, `story_flags` branch)

*Framed around five verbs: **VIEW · UNDERSTAND · NAME · CREATE · RECREATE**. Every quantitative claim
traces to the empirical census (`research/flag_census.json` / `flag_census.py`, 676/676 fields, 0 scan
errors), the Memoria C# engine, or Hades Workshop source. Produced by the `ff9-story-flag-research`
multi-agent workflow (4 parallel dossiers → adversarial verification → synthesis); corrections from the
three adversarial verdicts are applied inline.*

**Companion artifacts in this folder:**
`flag_census.py` (the scanner) · `flag_census.json` (full data) · `CENSUS_DIGEST.md` (human-readable data
appendix) · `make_digest.py` (regenerates the digest) · `flag_catalog.toml` (the named-flag registry seed
this report recommends). See `README.md`.

---

## 1. Executive summary

**What an FF9 story flag *is*.** All save-persistent story/event state lives in one place:
`EventState.gEventGlobal`, a **2048-byte array** (`EventState.cs:10`), serialized into the save JSON as a
single Base64 string under key `"gEventGlobal"` (`JsonParser.cs:522,579`). It is the engine's
`VariableSource.Global` space (`EBin.cs`, `enum VariableSource { Global=0, Map=1, … }`). Field scripts
read/write it through the `0x05` expression opcode using a var token `0xC0 | (type<<2) | source`, where the
index is a **bit address** for `Bit` vars (byte = `idx>>3`, bit = `idx&7`) and a **byte address** for
`Byte/Int16/Int24` vars. Three kinds of content occupy the heap:

1. **The ScenarioCounter** — a little-endian UInt16 at **bytes 0–1**, the master story-progress value
   (`EventState.cs:16-24`; engine token `SC_COUNTER_SVR = 0xDC`, `EBin.cs:34`). Census: **321 distinct
   absolute values** set, range **1..12000**, near-monotonic across discs — plus a handful of fields that
   *nudge* it relatively (`++`/`--` in 7 fields each, and a few `+=`/`*=`/`/=`/`&=`/`|=`).
2. **Bit-flags** — **1051 distinct** script-authored bits, spanning bit range **184..8511** (181 bytes of
   the heap). Once-events, door gates, location unlocks, treasure-chest "opened" state.
3. **Word-vars** — **333 distinct** Byte/Int16/Int24 values beyond byte 0, including FieldEntrance (Int16 @
   byte 2, every field) and per-area minigame/counter structures.

**State of the kit.** `ff9mapkit` already encodes flag ops **byte-for-byte** against real FF9 bytecode
(`content/region.py`), scans what each field touches offline (`eventscan.py`), allocates per-field
once-flags, lints dangling/colliding flags (`build.py`, `campaign.py`), and exposes get/set/clear/
snapshot/reset in the **F6 debug menu** (`Ff9mkDebugMenu.cs`). *Since this research:* a **named flag
registry** (`flags.py`, recommendation 2), an **offline save-file reader** (`flags-inspect`,
recommendation 3), and a **live in-game F6 "Story state" readout** (the in-game half of 3, proven 2026-06-10)
have landed — **and a save-seed/recreate tool** (`save-edit`, recommendation 4, in-game proven). All five
verbs are now implemented; the remaining frontiers are campaign `[initial_flags]` entry and seeding map/party.

**Three headline findings:**

- **★ Safe-band collision (latent, must fix before wiring).** The campaign allocator's reserved band
  (`campaign.py:182`, `flag_base=8300`, `flags_per_field=64`) overlaps real FF9's contiguous treasure-chest
  bitfield at **bits 8376–8511** (130 bits, bytes 1047–1063, written by 48 chest fields). A campaign field
  index ≥1 would alias real chest-opened bits → save corruption. The collision is **currently latent** —
  `flag_base` is reserved in `campaign.toml` but not yet threaded into `build_script` (deferred P5,
  `GLOBAL_RESOURCES.md:92`). **The first provably-clear base is bit 8512** (the census max real-used bit is
  8511). Recommend `flag_base=8512` (round: 8520/8600) before the allocator is wired.
  **✅ FIXED 2026-06-10 (this branch) — see §5(1):** default moved to 8512, per-member allocation threaded
  through `build._FlagAlloc`, and `lint_campaign` now errors on any block/flag in the chest band. 547 tests pass.
- **Byte 23 is an active engine handshake, not a free flag.** Bits 184/191 are touched by all 676 fields —
  but disassembly shows they are a per-field **menu/transition guard** (bit 184 = "in-field menu in
  progress", set bracketing `Menu` calls, re-checked and cleared in every `Main_Init`; bit 191 = a
  companion scratch bit zeroed on every boot). Re-written on every field load, gating the
  `FieldEntrance=10000` sentinel handshake. A mod must **replicate the prologue and never treat byte 23 as
  story state.**
- **The mechanism is fully documented; the *meaning* is not.** Where flags live, how they're typed, and how
  they persist is recoverable from Memoria + Hades Workshop (authoritative). But a complete value→meaning
  dictionary does **not** exist publicly — only ~15 engine-hardcoded scenario milestones and a few named
  subsystem regions. The rest must be mapped empirically (which the census now does).

---

## 2. The 2048-byte heap, mapped

Addressing reminder: a **Bit** index N → byte `N>>3`, bit `N&7`. A **Byte/Int16/Int24** index is a raw byte
offset. So "bit 184" = byte 23 bit 0, but "Int24 @ index 184" = byte 184 — a *different location* (this
exact aliasing trips up readers; see byte 23 vs. byte 184 below).

Confidence: **(a)** engine/decompilation-grounded · **(b)** corroborated community/empirical · **(c)**
single-source/uncertain.

| Byte range | Bit range | Region / meaning | Addressing | Conf | Citation |
|---|---|---|---|---|---|
| **0–1** | — | **ScenarioCounter** — master story-progress UInt16 LE | Global UInt16 @0 (`0xDC`) | (a) | `EventState.cs:16-24`; `EBin.cs:34` |
| **2–3** | — | **FieldEntrance** — last entrance/map index; read by all 676 fields | Global Int16 @2 (`0x2D8`) | (a) | `EventState.cs:26-34`; `EBin.cs:35` |
| **8–14** | — | Per-field standard variable block (party/coord/camera scratch); written in every `Main_Init` | Byte/Int16 | (b) | census (676 fields) |
| **16** | — | TRANCE_GAUGE_FLAG (trance enable 0/1); also gates a status-UI category | Byte | (a) | `battle.cs:38`; `StatusUI.cs:291` |
| **17–18** | — | GARNET_DEPRESS_FLAG / GARNET_SUMMON_FLAG (summon availability) | Byte | (a) | `battle.cs:39-40` |
| **23** | **184–191** | **ENGINE HANDSHAKE — not story state.** bit 184 = in-field menu/transition guard (set around `Menu`, checked+cleared every `Main_Init`); bit 191 = boot scratch, always `=0`. Reset on every field load. | Global Bit | (a) | disassembly (fields 50/100/300 `Main_Init`); engine grep = 0 hits |
| **60–91** | — | Mid-game shared transport/position state (SByte/Int24/Int16) | word-vars, ~67 fields | (b) | census |
| **92–102** | **736–823** | **Worldmap / Navi cursor + location-unlock / first-visit flags.** Set on arrival by field scripts, *consumed by worldmap/menu C#* → mostly write-only on the field side. The bulk of the 276 write-only bits. | Bit + Byte | (a)/(b) | `ff9.cs:2259-2333`; census |
| **112** | — | Chocobo Hot & Cold dig progress | Int24 (n14 chcb) | (a) | census; `EMinigame.cs` |
| **128–191** | ~1024–1535 | Chocobo Hot & Cold (n14) minigame state | Bit/Byte | (b) | census |
| **184–189** | — | **Chocograph found** (`[187+i]`) / **opened** (`[184+i]`) bitfields, UI ORs successive bytes `<<i*8` | **Byte** index (≠ bit 184!) | (a), single-site | `ChocographUI.cs:250-251` |
| **191** | — | Choco dig ability / level (set to 5 at milestones) | Byte | (a) | `ChocographUI.cs:245`; `EMinigame.cs:454,493` |
| **182–186** | — | **Treasure-Hunter "double" region** — world-map Choco-dug chests, **2 pts/bit** in rank scoring | Bit-packed Byte[5] | (a)+(b) | `EventState.cs:69-70`; FF Wiki |
| **220–251** | — | Game-wide dialogue/temp Int16 counters (very widely shared, 90–244 fields) | Int16 | (b) | census |
| **256–303** | ~2048–2431 | Mid-disc-1 story (Dali→Lindblum) | Bit | (b) | census (~49 fields) |
| **304–335** | ~2432–2687 | Lindblum festival/event flags; **bytes 314/316 = Festival of the Hunt score counters** (`+=`/`-=`) | Bit + UInt16 | (b) | census (n11, 11 fields) |
| **352–383** | ~2816–3071 | Disc-2/3 dungeon flags (Treno/Conde Petie/Bran Bal) | Bit | (b) | census (~45 fields) |
| **400–447** | ~3200–3583 | Ipsen / Desert Palace / Iifa flags | Bit | (b) | census (~50 fields) |
| **448–495** | ~3584–3967 | Mid-late town flags | Bit | (b) | census (~70 fields) |
| **780–820** | — | Chocobo's Paradise (Mene) state array (n15 kuin) | Byte ×~40 | (b) | census (5 fields) |
| **896–960** | — | **Treasure-Hunter "standard" region** — opened chests / searched icons / event items, **1 pt/bit** | Bit-packed Byte[65] | (a)+(b) | `EventState.cs:65-66`; FF Wiki |
| **896–975** | ~7168–7807 | **The main dense story-flag heap** — every area writes here (327 distinct bits, ~140 fields). Overlaps the TH-standard scoring region. | Bit | (a)/(b) | `EventState.cs:65-68`; census |
| **966–975** | — | **Treasure-Hunter "extra" region** — 1 pt/bit | Bit-packed Byte[10] | (a) | `EventState.cs:67-68` |
| **1024–1045 / 1064–1079** | — | The chest bitfield viewed as **Byte arrays** (same physical bytes as bits 8376–8511 below) | Byte, 48 fields | (b) | census |
| **1047–1063** | **8376–8511** | **TREASURE-CHEST "opened" block** — one global bitfield, 130 distinct bits, written by **48 chest fields** (e.g. 115, 300, 2203). Bits 8510/8511 = per-screen "any chest opened here" guard, gated by all 48. **★ This is the band the campaign allocator collides with.** | Bit (& Byte view) | (a)/(b) | census; `EventState.cs` GetTreasureHunterPoints |
| **1100–1291** | — | **Legacy** ability-usage counters (Byte[192], now moved to `gAbilityUsage` dict; bytes may be cleared) | Byte | (a) | `JsonParser.cs:539` |
| **2040** | **16320–16335** | Choice-visibility scratch mask (`MASK_SCRATCH_IDX`); engine-reserved, transient | Global UInt16 | (a) | `region.py:57` |
| **8512+** | **≥8512** | **CLEAR** — unused by any real field. The safe band for custom flags. | — | (a)/(b) | census (`bit_flag_max=8511`) |

**ScenarioCounter chapter banding (empirical, area→value).** Near-monotonic; the engine does *not* advance
it by a fixed step and disc boundaries are not round numbers (the "disc N starts at value X" forum claim is
**(c), uncorroborated** — do not bake it in). Anchors: Prologue/Tantalus 1000–1600 · Evil Forest ~2020–2400
· Ice Cavern 2500–2525 · Dali 2530–2680 · Lindblum 3000–3180 (later 9000–10100) · Burmecia 3800–3880 ·
Cleyra 4650–4980 · Conde Petie 6100–6270 · Iifa Tree 6700–6990 · Alexandria siege 7010–8800 · **Desert
Palace / Eiko abduction 9250–9890** · Terra 10830–10890 · Pandemonium 10930–10990 · Crystal World endgame
11610–**12000**.

---

## 3. The five verbs — current state & gaps

### VIEW — *see what flags a field/save touches*

- **Today:** `eventscan.py` provides four offline byte-scanners (`scan_flags_set` :459,
  `scan_required_flags` :476, `scan_edge_flag_gates` :502, decoder `_glob_var_token` :436) that report what
  each `.eb` **writes / reads / gates** — GLOB-only (0xC4/0xE4); MAP (0xC5) and UINT8 (0xD5) excluded as
  transient. The census (`research/flag_census.py`) aggregates this across all 676 real fields. In-game, the
  **F6 → Flags** tab (`Ff9mkDebugMenu.cs:457-526`) does live get/set/clear/snapshot/restore on
  `gEventGlobal`.
- **Now:** ✅ an **offline save-file reader** (`flags-inspect`) AND a **live in-game F6 "Story state" readout**
  both landed (recommendation 3) — the offline reader Base64-decodes a player's `gEventGlobal`; the F6 tab
  shows ScenarioCounter+beat / FieldEntrance / treasure points / chest count live (in-game proven). **Remaining
  gap:** the `.eb` scanners still see only the `0x05` expression path, so flags mutated by engine C# (e.g.
  worldmap-unlock consumers) stay invisible — why **276 bits read as "write-only."**

### UNDERSTAND — *know what a flag means*

- **Today:** The *mechanism* is fully reverse-engineered and documented (`GLOBAL_RESOURCES.md`): var
  encoding, GLOB-vs-MAP persistence, the byte-for-byte bytecode. The census + this report give an empirical
  region map (§2).
- **Gaps:** No "what this flag means" lore layer. ~15 scenario milestones and a few subsystem regions are
  named; the other ~1900 bytes are un-annotated. **ATE/Mognet specific indices are a genuine public gap** —
  mechanism known (engine reads `gEventGlobal` bits + ScenarioCounter to gate them), indices unnamed
  anywhere **(c)**.

### NAME — *refer to a flag by name, not index*

- **Today:** ✅ **Implemented** (recommendation 2). A `[[flag]]` table names a flag (`name` + `index`); the
  `flags.py` registry + load-time resolver let any `requires_flag`/`set_flag`/`flag` take a name, resolved
  byte-identically to the numeric form. Campaign-level `[[flag]]` defs give shared cross-field names.
- **Gaps:** The whole registry. Hades Workshop already proves the model — it names
  `General_ScenarioCounter` / `General_FieldEntrance` and lets modders attach custom names per script
  (`Gui_ScriptEditor.cpp`). Note the **HW naming inversion trap** (CLAUDE.md already flags it): HW `GlobBool`
  = engine **Map** = *transient*; HW `GenBool` = engine **Global** = *persistent*. A name-aware UI must not
  repeat "Glob = global." *(This report's `flag_catalog.toml` is a first concrete registry seed.)*

### CREATE — *author a new flag safely*

- **Today:** The kit encodes flags correctly: long-index support for >255 (`region.py:109-117`, e.g.
  `0xE4 0x84 0x20 0x7F` for idx 8300), GLOB class for persistence, gates/once-guards/choice-masks all
  grounded in real fields. Per-field once-allocators exist (EVENT 8000 `event.py:27`, CUTSCENE 8100
  `cutscene.py:37`, CHOICE 8200 `choice.py:35`).
- **Gaps:** **The collision bug (§4).** Per-field auto-counters **reset to 0 per build** → field A's first
  chest and field B's first chest both pick bit 8000 (`GLOBAL_RESOURCES.md` §5) — a latent N-field
  save-corrupter even before the campaign band. Campaign default `8300` is unsafe (treasure overlap). No
  per-field `flag_base` kwarg threaded into `build_script`.

### RECREATE — *set a save to a given story point*

- **Today:** ✅ **Implemented + in-game proven 2026-06-10** (recommendation 4). `ff9mapkit save-edit` reads a
  real `SavedData_ww.dat`, sets ScenarioCounter (+ flags) in a chosen slot, and writes it back — verified by
  loading an edited save and reading the new state off the F6 readout, no relaunch. See §5(4) for the codec
  + the Memoria split-save finding.
- **Remaining:** the edit sets story STATE only (not map position/party — scope choice); `[initial_flags]`
  at campaign entry is still a TODO; New-Game-into-a-campaign with a full party remains unsolved (reach
  chains via F6→Warp).

---

## 4. The safe-band finding

### The collision (verified arithmetic)

Campaign allocation (`campaign.py:182,247,270`; `CAMPAIGN_IMPORT.md:171`):

```
field i's flag block = [flag_base + i*K, flag_base + i*K + K),  flag_base=8300, K=64
```

Member count is unbounded above — `assign_ids` is `id_base + i` over all forkable nodes; `validate_ids`
caps only the field **id** (4000–32767), not the field **count**.

Real FF9 uses a **contiguous** treasure-chest bitfield at **bits 8376–8511** (130 distinct bits, bytes
1047–1063, written by the same 48 chest fields incl. 115/300/2203). These are save-backed GLOB bits —
writing them corrupts chest-opened state. Overlap, computed:

| Campaign field i | Block | Overlap with real 8376–8511 |
|---|---|---|
| 0 | 8300–8363 | **clean** (tops out below 8376) |
| 1 | 8364–8427 | **52 real bits** (8376–8427) |
| 2 | 8428–8491 | **all 64** |
| 3 | 8492–8555 | 20 real bits (8492–8511) |
| ≥4 | ≥8556 | clean |

So the **first aliasing field index is exactly i≥1**. The kit's *other* bands cannot reach 8376: the census
shows **zero real-used bits in [8000, 8375]**, and the per-field once-counters reset per build, so reaching
8376 would need 376 once-flags in one field — not realistic.

**Status (verdict correction):** the collision is **latent, not active.** `flag_base`/`flags_per_field` are
reserved in `campaign.toml` but **not yet consumed** by the allocators (deferred follow-up,
`GLOBAL_RESOURCES.md:92-94`, `CAMPAIGN_IMPORT.md:71`). No shipped build aliases yet — but the arithmetic
guarantees it once the per-member allocator is wired.

### Recommended bands (provably clear)

The maximum real-used bit in the entire 676-field census is **8511**. The first byte fully clear of all real
usage is **byte 1064 → bit 8512**.

```python
# campaign.py — set BEFORE wiring the per-field allocator
flag_base       = 8512     # first bit clear of ALL real FF9 usage (round: 8520 / 8600)
flags_per_field = 64       # unchanged
CHOICE_SCRATCH  = 16320    # bits @ byte 2040 — reserve at/above this (engine-owned)
# safe field cap: (16320 - 8512) // 64 = 122 fields
```

- Field 0 → 8512–8575 (clear) … Field 121 → 16256–16319 (clear, just below scratch). Field 122 → 16320+
  **collides with the choice scratch** — that is the hard ceiling.
- For breathing room, `flag_base=8600` keeps ~120 fields safely below 16320.

**Also fix the single-field once-counters** (independent of the campaign band): they alias *across fields*
because they reset per build. Either thread a per-field `flag_base` (e.g. `8512 + field_index*K`) or make the
counters globally monotonic within a build. This bug bites single-field imports too once a player saves in a
real field and returns.

---

## 5. Recommended toolkit work (prioritized)

**(1) — Safe-band fix + cross-field lint. ✅ LANDED 2026-06-10 (this branch).**
*Done:* `campaign.py` `flag_base` default 8300 → **8512** (`FIRST_SAFE_FLAG`); added a `flag_base` field to
`FieldProject` threaded through `build_script`/`lint_logic` via the new `build._FlagAlloc` (default `None`
reproduces the historical 8000/8100/8200 bands, so **single-field builds are byte-identical** — golden
preserved); `campaign.build_campaign` assigns each member `flag_base + i*K`, packed cutscene `+0` / events
`+1..+31` / choices `+32..+63`; `lint_campaign` now errors on any member block **or** explicit flag inside
the chest band 8376–8511 or at/above the choice scratch (bit 16320). Tests: `test_build.py`
(`_FlagAlloc` invariants), `test_campaign.py` (collision + safe-band lint). **547 tests pass.**

**(2) — A NAMED flag registry. ✅ LANDED 2026-06-10 (this branch).**
*Done:* `ff9mapkit/ff9mapkit/flags.py` is the canonical `index ↔ name ↔ meaning` registry — engine-grounded
named vars (ScenarioCounter@0, FieldEntrance@2, TranceGauge, ChocoDigLevel), reserved bit regions
(chest 8376–8511, worldmap unlocks, byte-23 handshake, choice scratch), scenario milestones, and the
safe-band constants (now the **single source of truth** — `campaign.py` imports them). Authoring: a
`[[flag]]` table (`name` + `index`, validated into [8512, 16320)) plus a load-time resolver
(`resolve_project_flags`) so `requires_flag = "ice_path_unlocked"` resolves to the index — **byte-identical**
to the numeric form (test-proven). Campaigns share cross-field names via a `campaign.toml` `[[flag]]` table
(`lint_campaign` checks they sit clear of the per-member auto blocks). CLI: `ff9mapkit flags` browses it.
*Guard kept:* the persistent space is never labelled "Glob" (that's HW's transient Map). *(The empirical
seed `research/flag_catalog.toml` fed this; `flags.py` is now canonical.)*

**(3) — A flag inspector/viewer. ✅ FULLY LANDED 2026-06-10 (offline + in-game).**
*Offline:* `flags.decode_gEventGlobal(blob)` + `gEventGlobal_from_save(json|base64|path)` + `render_report`
decode a save's `gEventGlobal` (Base64 from `FF9State.json`, `JsonParser.cs:522`) into a human report —
ScenarioCounter + nearest story beat, IsEikoAbducted, FieldEntrance, treasure-hunter points (engine ranges),
opened-chest count, set story bits grouped by region. CLI: `ff9mapkit flags-inspect <save>`. *In-game
(proven 2026-06-10):* the **F6 → Flags tab** gained a live **"Story state"** readout (ScenarioCounter + beat,
FieldEntrance, TreasureHunter pts via the engine's own `GetTreasureHunterPoints()`, chests opened) + a region
label on Get (`Ff9mkDebugMenu.cs`, patch `s22`). Verified in a real save at Alexandria Castle (SC 7200) —
which **corrected the scenario→beat table**: the old ~11-anchor map mislabelled mid-game (7200 read "Madain
Sari"); now a **census-grounded 43-area progression** (`research/gen_scenario_table.py` → `flags.py`
`SCENARIO_MILESTONES`, mirrored to the C# menu) reads 7200 → "Alexandria Castle". *Caveat:* the on-disc
`EncryptedSavedData` must be decrypted to JSON first; the open JSON/Base64 path is what `flags-inspect` reads.

**(4) — A "recreate" / save-seed mechanism. ✅ LANDED + in-game proven 2026-06-10.**
*Done:* `ff9mapkit save-edit <SavedData_ww.dat>` (`ff9mapkit/save.py`) — `--list` enumerates the populated
saves; `--slot S --save V --scenario <val|area> --set/--clear <flags>` sets the story state of a chosen
slot. Dry-run by default; `--in-place` edits the real files (each backed up). Reserved-region guard refuses
chest-band/etc. **The save codec, cracked here:** the on-disc `SavedData_ww.dat` is a container of fixed
18432-byte blocks, each **AES-256-CBC** (PBKDF2-HMAC-SHA1, 1000 iters, salt `[3,3,1,4,7,0,9,7]`, password =
the literal `"System.Security.SecureString"` — the decompiled `SecureString.ToString()` returns the type
name, and that **is** the key). Each block decrypts to `"SAVE"` + a schema-ordered value stream; gEventGlobal
is a String4K (2048 bytes → a 2732-char Base64). AES-CBC is a bijection, so an in-place Base64 swap is
byte-exact (no checksum). **★ The load-bearing in-game finding:** Memoria *also* writes an **unencrypted**
per-slot extra file (`SavedData_ww_Memoria_{slot}_{save}.dat`) holding the AUTHORITATIVE gEventGlobal, and
**restores from it on load, overriding the vanilla block** — so `save-edit` patches *both*. Verified: an
offline-edited save loaded to `ScenarioCounter 2500 → Ice Cavern` on the F6 readout, no relaunch. Needs
`pycryptodome` (lazy import). *Still open:* `[initial_flags]` at campaign entry; seeding map/party (state-only
for now).

---

## 6. Draft NAMED-FLAG CATALOG (registry seed)

A starter table of the best-named flags/regions/milestones defensible *now*. Tiers: **(a)** engine-grounded ·
**(b)** corroborated/empirical · **(c)** single-source/uncertain. Machine-readable form:
`research/flag_catalog.toml`.

### Core variables & reserved regions

| Name | Location | Type / addressing | Meaning | Tier | Source |
|---|---|---|---|---|---|
| `ScenarioCounter` | bytes 0–1 | Global UInt16 (`0xDC`) | Master story-progress value (1..12000) | (a) | `EventState.cs:16-24`; `EBin.cs:34` |
| `FieldEntrance` | bytes 2–3 | Global Int16 (`0x2D8`) | Last entrance / map index | (a) | `EventState.cs:26-34`; `EBin.cs:35` |
| `_RESERVED_field_menu_guard` | bit 184 (byte 23.0) | Global Bit | Engine handshake — in-field menu/transition guard. **Do not use.** | (a) | disassembly; engine grep=0 |
| `_RESERVED_boot_scratch` | bit 191 (byte 23.7) | Global Bit | Zeroed every boot. **Do not use.** | (a) | disassembly |
| `TranceGaugeFlag` | byte 16 | Byte | Trance gauge enable | (a) | `battle.cs:38` |
| `GarnetSummonAvailable` | bytes 17–18 | Byte | Garnet summon depression/reserve | (a) | `battle.cs:39-40` |
| `_RESERVED_TH_standard` | bytes 896–960 | Bit-packed | Treasure-Hunter scored flags (1 pt/bit) | (a) | `EventState.cs:65-66` |
| `_RESERVED_TH_extra` | bytes 966–975 | Bit-packed | Treasure-Hunter extra (1 pt/bit) | (a) | `EventState.cs:67-68` |
| `_RESERVED_TH_double` | bytes 182–186 | Bit-packed | World-map Choco chests (2 pts/bit) | (a) | `EventState.cs:69-70` |
| `_RESERVED_chest_opened` | bits 8376–8511 | Bit (Byte view 1047–63) | Global chest-opened bitfield, 48 fields | (a)/(b) | census |
| `ChocographFound` / `ChocographOpened` | bytes 187+i / 184+i | Byte | Chocograph treasure tracking | (a) | `ChocographUI.cs:250-251` |
| `ChocoDigLevel` | byte 191 | Byte | Choco's dig ability level | (a) | `ChocographUI.cs:245` |
| `_RESERVED_worldmap_unlocks` | bytes 92–102 | Bit/Byte | Location-unlock / Navi cursor (consumed by C#) | (a)/(b) | `ff9.cs:2259-2333` |
| `_RESERVED_choice_scratch` | byte 2040 (bits 16320+) | Global UInt16 | Choice-visibility mask scratch | (a) | `region.py:57` |
| `_LEGACY_ability_usage` | bytes 1100–1291 | Byte[192] | Legacy ability counters (may be cleared) | (a) | `JsonParser.cs:539` |
| `HuntFestivalScore` | bytes 314/316 | UInt16 (`+=`/`-=`) | Festival of the Hunt tally (n11) | (b) | census |

### ScenarioCounter milestones (engine-hardcoded special cases)

*Anchor points, not a continuous scale. (a) for each value↔beat pairing; completeness is low — these are the
beats the engine special-cases.*

| Value | Beat | Tier | Source |
|---|---|---|---|
| 1000 | Game start — Prima Vista / Cargo Room (field 50) | (b) | census + manifest join |
| 1150 | Alexandria / Shop (field 104) | (b) | census |
| 1900 | Burmecia-area gate (field 206 choice) | (a) | `EMinigame.cs:534`, `ETb.cs:424` |
| 4980 | Cleyra Cathedral (field 1109) | (a) | `EMinigame.cs:246` |
| 6840 / 6850 | Madain Sari, Secret Room — Zidane/Garnet dialog states (field 1608) | (a) | `Dialog.cs:1613,1620` |
| 9520 | Kuja sends team to Oeilvert (party ≥4 enforced) | (a) | `PartySettingUI.cs:557` |
| **9860 … <9990** | **`IsEikoAbducted`** — Desert Palace abduction window. **Inclusive range 9860–9989** (engine uses `< 9990`, exclusive). Census: 9860/9890 written exclusively by N38 Desert Palace fields (2207/2209/2212); highest in-band observed = 9910. | (a) | `EventState.cs:36` |
| 10300 | "Late game" threshold (field 2456, `>= 10300`) | (a) | `EMinigame.cs:114` |
| 11090 | Near-endgame threshold (field 455, `< 11090`) | (a) | `EMinigame.cs:233` |
| 12000 | Terminal value — Ending fields (12 fields snap here) | (a)/(b) | census; `EventState.cs` |

---

## 7. Open questions / further research

1. **ATE / Mognet flag indices.** Mechanism known (gated by `gEventGlobal` bits + ScenarioCounter), but **no
   public index dictionary** exists. Must be reverse-mapped from `.eb` scripts — the census's
   producer/consumer scan is the right tool; cross-reference with in-game ATE availability to label them.
2. ~~**Census write under-count (counters).**~~ **RESOLVED in this branch.** `flag_census.py`'s `ASSIGN_OPS`
   now covers the full `op_binary` assignment family (`0x2C–0x45` = `B_LET … B_OR_LET_E`, the plain-`=` `_A`/
   `_E` variants + every compound-assign) plus in/decrements (`0x04–0x0B`), grounded in `EBin.cs:2423-2485`.
   Re-run confirms **bit-flag findings unchanged (1051 flags)**; absolute scenario values refined 322→**321**
   (one was a compound-assign, not an absolute set); relative scenario ops are now bucketed in
   `scenario_counter_increments` (`++`/`--` ×7 fields each + a few `+=`/`*=`/`/=`/`&=`/`|=`). The `0x20`
   B_EQ-compare that made bit-184 read+write was always correctly *not* an assign — bit 184 genuinely is both
   read (`== 1` guard) and written (`= 0` clear) by ~every field; that is the handshake, not a decode error.
3. **Per-chest bit identity.** The 8376–8511 block is the *scored* treasure region (48 fields, ~130 bits),
   but no public source maps each bit to a specific chest. Enumerating it (chest field × bit) would let a
   campaign safely *reuse* real chests if ever desired.
4. **Complete ordered scenario table.** Only ~15 anchors are named; the full value→beat progression is
   empirically derivable from the census (321 values, single-writer-field for most) joined to the area
   manifest — a worthwhile registry-seeding pass.
5. **Encrypted-save round-trip.** The `RECREATE` tool needs the `EncryptedSavedData\SavedData_ww.dat` codec
   for a real save (the in-memory JSON Base64 path is open). `ff9SaveLib` is a reference; verify it
   round-trips current Memoria saves.
6. **Worldmap-unlock readers.** The 276 "write-only" bits (mostly bytes 92–102) are consumed by engine C#,
   not field scripts — confirming each bit's exact menu/worldmap consumer would let the kit author location
   unlocks confidently rather than by copy.

---

*Primary sources: `research/flag_census.json` / `flag_census.py` (676 fields); Memoria `Assembly-CSharp`
(`EventState.cs`, `EBin.cs`, `JsonParser.cs`, `ChocographUI.cs`, `EMinigame.cs`, `battle.cs`, `ff9.cs`);
Hades Workshop (`Database_Script.cpp`, `Gui_ScriptEditor.cpp`); kit (`content/region.py`, `event.py`,
`cutscene.py`, `choice.py`, `eventscan.py`, `campaign.py`, `build.py`; `docs/GLOBAL_RESOURCES.md`,
`CAMPAIGN_IMPORT.md`). Corrections applied per adversarial verdicts: Eiko range 9860–9989 inclusive; byte 23
is an active handshake; campaign collision is latent; safe band starts at bit 8512.*

---

## 8. UNDERSTAND-layer deepening — landed 2026-06-10 (the "meaning" pass)

Section 3's UNDERSTAND verb was the thinnest (mechanism known, *meaning* not). This pass deepened it from a
field-granular census×manifest join (`research/gen_understand_layer.py` → `understand_layer.json`), curated +
adversarially verified by the **`ff9-understand-layer`** workflow (3 verification lenses — story-order /
label-accuracy / curation — + 2 research agents → synthesis). All landed in `ff9mapkit/flags.py`; 602 tests pass.

- **Scenario→beat dictionary, rebuilt (43 → 52 anchors, field-grounded).** Each anchor now traces to the
  *setter field* and its manifest room, fixing real mislabels the old zone-coded table shipped: **5900** "Iifa
  Tree" → **Fossil Roo** (field 1422); **9990** "Outer Continent" → **Mount Gulug** (field 2357, closing the
  IsEikoAbducted window); **9400** "Hilda Garde" → **Blue Narciss** (field 2855); **11610** "Crystal World" →
  **Memoria** (with Crystal World correctly split to 11765/12000). Restored lost beats: **Burmecia** (3800),
  **Oeilvert** (9605), a second elemental shrine (Water 10620), **Pandemonium** (10930), Memoria. The
  in-game-validated **7200 → Alexandria Castle** anchor is preserved. Mirrored to the F6 menu C# + engine
  rebuilt — **in-game proven 2026-06-10** (F6 reads 7200 → Alexandria Castle on a real save and 5900 → Fossil
  Roo on an edited throwaway).
- **18 named story-flag clusters** (`flags.STORY_REGIONS`, informational/non-reserved) annotate a decoded
  save's set bits by dominant writer area (e.g. `lindblum_events` 2592–2663, `mognet_central_state` 4046–4047).
  **Reconciled a §2 report error:** the "Lindblum festival @ bytes 304–335" claim is wrong — bits 2418–2495 are
  the *prologue* (Prima Vista/Evil Forest); the true Lindblum cluster is 2592–2663, and the Festival-of-the-Hunt
  score is the separate `HuntFestivalScore` UInt16 words at bytes 314/316.
- **Two engine-grounded discovery bits named** (refining the reserved `worldmap_unlocks` band): bit **815** =
  Mognet Central discovered, bit **814** = Chocobo's Paradise discovered (`WorldConfiguration.cs:183-184`).
- **★ Open question #1 (ATE/Mognet indices) RESOLVED — negative.** ATE *seen-state is NOT in the gEventGlobal
  heap at all*: it lives in `AchievementState.AteCheck` (`Int32[100]`, save key `AteCheckArray`), and ATE
  selection is a per-field `.eb` branch keyed on (fldLocNo, fldMapNo, ScenarioCounter, chosen choice) via the
  hardcoded `EMinigame.MappingATEID` switch. So there is **no heap "ATE flag index" to name** (recorded in
  `flags.ATE_STATE_LOCATION`). The portable ATE-id table (0..82) could be ported from `MappingATEID` later, but
  it is not a flag dictionary.
- **Open question #3 (per-chest bit identity) confirmed intractable from the static census:** every bit in the
  8376–8511 chest band has *exactly 48 writers* → a computed index, not a per-chest-static bit. `flags.py`
  correctly keeps the whole band reserved; mapping bit→chest would need a runtime trace.
- **Standing UNDERSTAND frontier:** the cluster names are "where these flags are written from" (dominant-writer
  inference), not a proven per-bit lore dictionary — the bulk of the ~1900 un-annotated heap bytes remain a
  per-flag-meaning gap.
