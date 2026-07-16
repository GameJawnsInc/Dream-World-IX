# THE HIDDEN-ENEMY BATTLE CENSUS — stock battles with SetCharacterData code 32 (APPEAR) / 33 (SUBMERGE/LEAVE)

Offline census over **all 562** stock battle-scene AI scripts (`EVT_BATTLE_*.eb`, `us`), 2026-07-16.
Purpose: pick the box-10 two-machine diorama test fights — the diorama mirrors script-hidden units via the
HIDDEN bit (info bit 16) rendered as "the case-33 idiom", so we need the stock fights that actually FIRE
`btl_scrp.SetCharacterData` case 32 (`btl_sys.AddCharacter`) / case 33 (`btl_sys.DelCharacter`) — the engine's
ONLY mid-battle spawn/despawn idiom (relinking PRE-SPAWNED pattern units; `btl_scrp.cs:421-437`).

## 1. Calling convention (how an AI script invokes code 32/33)

Battle enemy AI runs in the same EventEngine as field scripts. The dispatch chain, cited from the live tree
(`C:/gd/FFIX/Memoria`):

1. An `.eb` expression **assignment to a `VariableSource.Member` variable** is the invocation. The EBin
   interpreter's `SetVariableValue` case `VariableSource.Member` calls
   `_eventEngine.putvobj(_eventEngine.gMemberTarget, t0 & 0xFF, varValue)` — `EBin.cs:1980-1981`.
2. `putvobj` (type != 2) → `this.SetBattleCharData(obj, type, v)` — `EventEngine.cs:1177-1188`.
3. `SetBattleCharData` resolves the Obj's battle unit (`FindBattleUnitUnlimited` for kind 32, so a
   DELINKED unit can be re-added; `FindBattleUnit` otherwise) and calls
   `btl_scrp.SetCharacterData(btl, (UInt32)kind, (Int32)value)` — `EventEngine.cs:1045-1058`.
4. `btl_scrp.SetCharacterData` case **32u**: enable all mesh/shadow/weapon/model renderers +
   `btl_sys.AddCharacter(btl)` (`btl_scrp.cs:421-427`); case **33u**: disable all renderers +
   `btl_cmd.KillStandardCommands(btl)` + `btl_sys.DelCharacter(btl)` (`btl_scrp.cs:429-436`).

No other writer exists: the only other `SetCharacterData` call site is `btlseq.cs:711`, which is the raw17
sequence player writing member **55** (model scale) — the raw17 lane can never fire 32/33.

### The raw byte pattern

In `.eb` bytecode the Member write is the RPN token stream (op_binary values from `EBin.cs:2428-2553`;
`B_MEMBER = 41 = 0x29` pushes `selector | encodeVarClass(VariableSource.Member)`, `EBin.cs:866-872`):

```
<unit-selector token> 0x29 <kind> ... value expr ... <LET-family op> 0x7F
```

Both shipping idioms, byte-verified against the install:

| idiom | bytes | decoded |
|---|---|---|
| SELF-despawn (fleeing enemy) | `05 79 01 29 21 7d 01 00 2d 7f` | `SET { B_SYSLIST[1] B_MEMBER(33) const(1) B_LET_A }` (BU_R015 @655) |
| cross-unit hide at Init | `05 dd 31 29 21 7d 01 00 2d 7f` | `SET { Map.UInt16[49] B_MEMBER(33) const(1) B_LET_A }` (EF_E009 @605) |
| cross-unit APPEAR mid-battle | `05 dd 31 29 20 7d 01 00 2d 7f` | `SET { Map.UInt16[49] B_MEMBER(32) const(1) B_LET_A }` (EF_E009 @755) |

`B_SYSLIST[1]` = the acting unit (SELF); a `Map.UInt16[..]` var holds a saved unit handle (Main_Init stores it),
which is how a script hides/reveals a DIFFERENT unit — including a PLAYER slot.

**Census method** — NOT a raw grep: `0x29` is also a command opcode (4-byte immediate) and `)` in a regex
(`re.findall(b"\x29\x21")` literally throws `unbalanced parenthesis` unescaped), and `0x20/0x21` occur freely
in immediates. The census decodes every function **expression-aware** with the kit's engine-mirroring
disassembler (`ff9mapkit.battle.battleai._decode_func_pretty` → `eb.disasm.pretty_expr`, the exact
`EBin`/`read_code` byte-walk) and matches `B_MEMBER(32)` / `B_MEMBER(33)` tokens inside decoded expressions.
This is the same class of census as the B_HAVE_ITEM `\x7d(..)\x64` one — bytecode-level, transcripts don't
surface the tokens — but with the full decoder instead of a regex because 0x29 is ambiguous raw.

**Enumeration**: `p0data7.bin` containers `eventbinary/battle/us/evt_battle_*.eb.bytes` (562 scenes, 0 decode
failures); scene → battle id from `p0data2.bin` `battlescene/evt_battle_<name>/<id>.raw17.bytes`; enemy-type
names = first `typ_count` (raw16 header) strings of `embeddedasset/text/us/battle/<id>.mes` via the
ResourceManager container index (the kit's faithful `_read_battle_text` path).
Script: `hidden_enemy_census.py` (this dir); raw data: `hidden-enemy-census.json`.

## 2. Results — 50 scenes fire code 32/33

Two clean classes:

- **Class A — the full hide→APPEAR cycle (code 33 at Init + code 32 mid-battle), 4 scenes.** All four hide a
  unit handle saved in a Map var at Init and reveal it from entry 0's Main loop. `typ_count = 1` in every one —
  the hidden unit is NOT an enemy type of the scene: these are the "ally joins mid-battle" events. EF_E009 =
  **Plant Brain** (Evil Forest boss, disc 1 — Blank jumps in mid-fight). PD_E067/68/69 = **Amdusias / Abadon /
  Shell Dragon** (the Pandemonium disc-4 solo fights where party members arrive mid-battle).
- **Class B — code 33 only (a unit leaves the battle mid-fight), 46 scenes.** The flee/retreat/steal-and-run
  idiom, almost always `B_SYSLIST[1]` SELF-despawn from the tag7 [ATB] or tag1 [Main] function: Vice / Magic
  Vice (steal-and-flee), Mimic, Tonberry (Ipsen's), retreating Alexandrian Soldiers (Alexandria, Cleyra,
  Gargan Roo), Haagen/Weimar in the disc-1 Steiner street fight, Ralvurahva, the Epitaph mirror-clone
  (deleted when its master dies), Hedgehog Pie world-map packs, and two icon-glyph-named world-map specials.

### Full hit table

| scene | battle id | place | enemy types (us .mes) | codes | hit sites |
|---|---|---|---|---|---|
| AC_E076A | 64 | Alexandria Castle | Soldier | 33 x1 | entry1 (Soldier) tag7[ATB] @980 code 33 (SELF) |
| AC_E076B | 62 | Alexandria Castle | Soldier | 33 x1 | entry1 (Soldier) tag7[ATB] @980 code 33 (SELF) |
| AC_E076C | 63 | Alexandria Castle | Soldier | 33 x1 | entry1 (Soldier) tag7[ATB] @980 code 33 (SELF) |
| AC_E076D | 61 | Alexandria Castle | Type B | 33 x1 | entry1 (Type B) tag7[ATB] @1477 code 33 (SELF) |
| AC_E076E | 271 | Alexandria Castle | Soldier | 33 x1 | entry1 (Soldier) tag7[ATB] @892 code 33 (SELF) |
| BU_R002 | 51 | Burmecia | Mimic, Magic Vice | 33 x2 | entry2 (Magic Vice) tag1[Main] @1554 code 33 (SELF); entry2 (Magic Vice) tag7[ATB] @2003 code 33 (SELF) |
| BU_R004 | 45 | Burmecia | Mimic, Magic Vice | 33 x2 | entry2 (Magic Vice) tag1[Main] @1554 code 33 (SELF); entry2 (Magic Vice) tag7[ATB] @2003 code 33 (SELF) |
| BU_R015 | 71 | Burmecia | Magic Vice | 33 x1 | entry1 (Magic Vice) tag7[ATB] @655 code 33 (SELF) |
| BU_R016 | 79 | Burmecia | Magic Vice | 33 x1 | entry1 (Magic Vice) tag7[ATB] @655 code 33 (SELF) |
| BU_R017 | 80 | Burmecia | Magic Vice | 33 x1 | entry1 (Magic Vice) tag7[ATB] @655 code 33 (SELF) |
| CY_E021A | 298 | Cleyra | Soldier, Type B | 33 x2 | entry1 (Soldier) tag7[ATB] @964 code 33 (SELF); entry2 (Type B) tag7[ATB] @2197 code 33 (SELF) |
| CY_E021B | 297 | Cleyra | Soldier, Type B | 33 x2 | entry1 (Soldier) tag7[ATB] @964 code 33 (SELF); entry2 (Type B) tag7[ATB] @2197 code 33 (SELF) |
| EF_E009 | 303 | Evil Forest | Plant Brain | 32 x1, 33 x1 | entry0 tag0[Init] @605 code 33 (unit handle from Map var = cross-unit); entry0 tag1[Main] @755 code 32 (unit handle from Map var = cross-unit) |
| GR_E017 | 76 | Gargan Roo | Ralvurahva | 33 x1 | entry1 (Ralvurahva) tag7[ATB] @1929 code 33 (SELF) |
| GT_E019A | 312 | South Gate arc (GT_* prefix; place label unverified — NOT Gargan Roo, that is GR_*) | Soldier | 33 x1 | entry1 (Soldier) tag7[ATB] @884 code 33 (SELF) |
| IP_R000 | 872 | Ipsen's Castle | Tonberry | 33 x3 | entry1 (Tonberry) tag1[Main] @567 code 33 (SELF); entry1 (Tonberry) tag1[Main] @1048 code 33 (SELF); entry1 (Tonberry) tag7[ATB] @2491 code 33 (SELF) |
| IP_R001 | 873 | Ipsen's Castle | Tonberry | 33 x3 | entry1 (Tonberry) tag1[Main] @567 code 33 (SELF); entry1 (Tonberry) tag1[Main] @1048 code 33 (SELF); entry1 (Tonberry) tag7[ATB] @2491 code 33 (SELF) |
| IP_R002 | 874 | Ipsen's Castle | Tonberry | 33 x3 | entry1 (Tonberry) tag1[Main] @567 code 33 (SELF); entry1 (Tonberry) tag1[Main] @1048 code 33 (SELF); entry1 (Tonberry) tag7[ATB] @2491 code 33 (SELF) |
| PD_E067 | 155 | Pandemonium | Amdusias | 32 x2, 33 x2 | entry0 tag0[Init] @536 code 33 (unit handle from Map var = cross-unit); entry0 tag0[Init] @559 code 33 (unit handle from Map var = cross-unit); entry0 tag1[Main] @685 code 32 (unit handle from Map var = cross-unit); entry0 tag1[Main] @862 code 32 (unit handle from Map var = cross-unit) |
| PD_E068 | 160 | Pandemonium | Abadon | 32 x1, 33 x1 | entry0 tag0[Init] @566 code 33 (unit handle from Map var = cross-unit); entry0 tag1[Main] @677 code 32 (unit handle from Map var = cross-unit) |
| PD_E069 | 163 | Pandemonium | Shell Dragon | 32 x1, 33 x1 | entry0 tag0[Init] @566 code 33 (unit handle from Map var = cross-unit); entry0 tag1[Main] @696 code 32 (unit handle from Map var = cross-unit) |
| TH_E004 | 335 | Alexandria town (Steiner street fights) | [STNR], Haagen, Weimar | 33 x2 | entry2 (Haagen) tag7[ATB] @2132 code 33 (SELF); entry3 (Weimar) tag7[ATB] @2702 code 33 (SELF) |
| UF_R000 | 344 | Fossil Roo/underground | Skeleton, Vice | 33 x1 | entry2 (Vice) tag7[ATB] @2259 code 33 (SELF) |
| UF_R001 | 343 | Fossil Roo/underground | Skeleton, Vice | 33 x1 | entry2 (Vice) tag7[ATB] @2259 code 33 (SELF) |
| UV_R007 | 464 | Oeilvert | Epitaph, [STNR] | 33 x1 | entry2 ([STNR]) tag1[Main] @1616 code 33 (SELF) |
| UV_R008 | 465 | Oeilvert | Epitaph, [EIKO] | 33 x1 | entry2 ([EIKO]) tag1[Main] @1616 code 33 (SELF) |
| UV_R009 | 467 | Oeilvert | Epitaph, [FRYA] | 33 x1 | entry2 ([FRYA]) tag1[Main] @1616 code 33 (SELF) |
| UV_R010 | 468 | Oeilvert | Epitaph, [DGGR] | 33 x1 | entry2 ([DGGR]) tag1[Main] @1616 code 33 (SELF) |
| UV_R011 | 475 | Oeilvert | Epitaph, [VIVI] | 33 x1 | entry2 ([VIVI]) tag1[Main] @1616 code 33 (SELF) |
| UV_R012 | 499 | Oeilvert | Epitaph, [AMRT] | 33 x1 | entry2 ([AMRT]) tag1[Main] @1616 code 33 (SELF) |
| UV_R013 | 502 | Oeilvert | Epitaph, [ZDNE] | 33 x1 | entry2 ([ZDNE]) tag1[Main] @1616 code 33 (SELF) |
| UV_R015 | 519 | Oeilvert | Epitaph, [QUIN] | 33 x1 | entry2 ([QUIN]) tag1[Main] @1616 code 33 (SELF) |
| WM_0208 | 225 | World map | Vice, Hedgehog Pie | 33 x1 | entry2 (Hedgehog Pie) tag7[ATB] @2299 code 33 (SELF) |
| WM_0210 | 241 | World map | Vice, Hedgehog Pie | 33 x1 | entry2 (Hedgehog Pie) tag7[ATB] @2299 code 33 (SELF) |
| WM_0212 | 243 | World map | Vice, Hedgehog Pie | 33 x1 | entry2 (Hedgehog Pie) tag7[ATB] @2299 code 33 (SELF) |
| WM_0214 | 237 | World map | Vice, Hedgehog Pie | 33 x1 | entry2 (Hedgehog Pie) tag7[ATB] @2299 code 33 (SELF) |
| WM_0217 | 238 | World map | (icon-glyph name) | 33 x1 | entry1 ((icon-glyph)) tag7[ATB] @1293 code 33 (SELF) |
| WM_0219 | 234 | World map | Vice, Hedgehog Pie | 33 x1 | entry2 (Hedgehog Pie) tag7[ATB] @2299 code 33 (SELF) |
| WM_0221 | 220 | World map | (icon-glyph name) | 33 x1 | entry1 ((icon-glyph)) tag7[ATB] @1293 code 33 (SELF) |
| WM_0223 | 222 | World map | Vice, Hedgehog Pie | 33 x1 | entry2 (Hedgehog Pie) tag7[ATB] @2299 code 33 (SELF) |
| WM_0226 | 845 | World map | Vice, Hedgehog Pie | 33 x1 | entry2 (Hedgehog Pie) tag7[ATB] @2299 code 33 (SELF) |
| WM_0227 | 844 | World map | Vice, Hedgehog Pie | 33 x1 | entry2 (Hedgehog Pie) tag7[ATB] @2299 code 33 (SELF) |
| WM_0720 | 142 | World map | Vice | 33 x1 | entry1 (Vice) tag7[ATB] @1363 code 33 (SELF) |
| WM_0721 | 141 | World map | Vice | 33 x1 | entry1 (Vice) tag7[ATB] @1363 code 33 (SELF) |
| WM_0723 | 143 | World map | Vice | 33 x1 | entry1 (Vice) tag7[ATB] @1363 code 33 (SELF) |
| WM_0725 | 137 | World map | Vice | 33 x1 | entry1 (Vice) tag7[ATB] @1363 code 33 (SELF) |
| WM_0726 | 140 | World map | Vice | 33 x1 | entry1 (Vice) tag7[ATB] @1363 code 33 (SELF) |
| WM_0728 | 136 | World map | Vice | 33 x1 | entry1 (Vice) tag7[ATB] @1363 code 33 (SELF) |
| WM_0904 | 255 | World map | Hedgehog Pie, Vice | 33 x1 | entry2 (Vice) tag7[ATB] @2311 code 33 (SELF) |
| WM_0905 | 254 | World map | Hedgehog Pie, Vice | 33 x1 | entry2 (Vice) tag7[ATB] @2311 code 33 (SELF) |

Notes: `[STNR]`/`[VIVI]`/... are the mes character-name macros — the Oeilvert **Epitaph** scenes' type 1 is the
party-member MIRROR clone (its code-33 delete fires when the mirror must vanish); TH_E004's `[STNR]` type is
the enemy Steiner of the disc-1 Alexandria street fight, with Pluto Knights **Haagen** and **Weimar** each
carrying a code-33 self-flee. The `(icon-glyph name)` scenes WM_0217/WM_0221 (ids 238/220) have a single type
whose us name is pure icon glyphs (`„♂`, `„♂★` raw) — a world-map special encounter with a self-flee.

### Adjacent, deliberately EXCLUDED class — member 53 (`disappear`) only

4 scenes write only `B_MEMBER(53)` (= `bi.disappear`, render-only vanish, NO btl_list relink — a different
diorama lane than the case-33 HIDDEN bit): **GZ_E014** (Gizamaluke, id 326), **IC_E011** (Sealion + Black
Waltz 1, id 21, disc 1), **PD_E079** (Kuja/Trance Kuja, id 891), **TH_E001** (Masked Man + Baku's Mask, id 336,
disc 1). IC_E011 or TH_E001 make a good disc-1 NEGATIVE control: visually vanishing units that must NOT set
the HIDDEN bit.

## 3. Early-reachable hits (disc 1-2 on a normal save)

| fight | disc | codes | why it's the pick |
|---|---|---|---|
| **Plant Brain** (EF_E009, id 303) | 1 | 33 @Init + **32 mid-battle** | THE headline: the only disc-1 fight with code 32. Blank's slot is hidden at boot (first wire frames must carry HIDDEN) and APPEARS mid-fight (tests the 33→32 transition live). Forced story boss, ~30 min into a new game. |
| **Masked Man / Baku fight** (TH_E001) | 1 | 53 only | disc-1 negative control (render-only vanish). |
| **Steiner street fight** (TH_E004, id 335) | 1 | 33 x2 | Haagen and Weimar each self-flee; forced encounters during the Alexandria escape. |
| **Vice** world-map encounters (WM_0720-0728, ids 136-143) | 1 | 33 | steal-and-flee; farmable random encounter on the starting continent. |
| **Mimic / Magic Vice** (BU_R002/4, ids 51/45) + **Magic Vice** (BU_R015-17, ids 71/79/80) | 2 | 33 | Burmecia randoms; steal-and-flee. |
| **Soldier / Type B** (CY_E021A/B, ids 298/297) | 2 | 33 x2 | Cleyra-attack story battles; both types retreat. |
| **Ralvurahva** (GR_E017, id 76) | 2 | 33 | Gargan Roo. |

Later: Tonberry (IP_R000-2, Ipsen's, disc 3), Epitaph (UV_R007-15, Oeilvert, disc 3), the Alexandria-castle
Soldier waves (AC_E076A-E — first plausibly reachable in the DISC-2 Garnet-rescue castle infiltration; the
earlier "disc 3" label was a guess, treat the disc as unverified), the Pandemonium trio (PD_E067-69, disc 4 —
the richest class-A set: two simultaneous hidden slots in Amdusias).

## 4. Recommended two-machine test (box 10)

1. **Plant Brain (Evil Forest, disc 1)** — the one fight that exercises BOTH directions: a unit already HIDDEN
   in the boot-block frames, then a live code-32 APPEAR mid-battle. If only one fight gets tested, it is this.
2. **Any Vice world-map random on disc 1** (or Magic Vice in Burmecia on a disc-2 save) — the pure code-33
   mid-battle DESPAWN (steal-and-flee), trivially reachable and repeatable for retries.
3. **Cleyra Soldier + Type B (disc 2 save)** — two enemy types in one fight each carrying the code-33 retreat;
   covers multiple hidden transitions in a single battle if both flee.

## 5. Adversarial verification (2026-07-16) — VERDICT: CONFIRMED (two cosmetic label fixes)

Independent re-derivation, scripts `verify_hand_decode.py` / `verify_truncation.py` (this dir).

**(1) Hand-decode from raw bytes (independent of the kit disassembler).** Raw hex pulled straight
from p0data7 at the claimed offsets:

- EF_E009 @605: `05 dd 31 29 21 7d 01 00 2d 7f` — walked byte-by-byte against the live engine:
  `05` = `event_code_binary.EXPR` (EBin.cs:2092, index 5); `dd` = var token `0xC0|0x1d` → varSrc
  `0x1d&3 = 1 = Map`, varType `(0x1d>>2)&7 = 7 = UInt16` (getVarOperation packing EBin.cs:515,
  enums EBin.cs:2555-2581), 1-byte index `31` = 49 (expr_varSpec EBin.cs:464-478) → `Map.UInt16[49]`;
  `29 21` = B_MEMBER(41) + selector 33 (EBin.cs:866-872, enum 2471); `7d 01 00` = B_CONST short 1
  (EBin.cs:1231-1235); `2d` = B_LET_A(45); `7f` = B_EXPR_END(127). = `Map.UInt16[49].Member[33] = 1`.
- EF_E009 @755: identical with `29 20` → Member(32). BU_R015 @655: `05 79 01 29 21 7d 01 00 2d 7f`
  with `79 01` = B_SYSLIST(121)[1]; SysList[1] is set to `1 << self-index` per executing obj by
  `ProcessCodeExt` (EventEngine.cs:982-991) — so SELF-despawn confirmed.
- Dispatch chain re-confirmed at the cited lines: EBin.cs:1981 (Member → putvobj(gMemberTarget)),
  EventEngine.cs:1177-1188 (putvobj type≠2 → SetBattleCharData), EventEngine.cs:1045-1058
  (kind 32 → FindBattleUnitUnlimited; → btl_scrp.SetCharacterData), btl_scrp.cs:415/421-427 (32u
  AddCharacter) /429-436 (33u KillStandardCommands+DelCharacter). The member TARGET obj is resolved
  from the pushed unit-mask by the member-access operator that sets `gMemberTarget = _objPtrList[index]`
  (EventEngine.cs:243) — i.e. the Map-var value is a unit MASK, matching the cross-unit reading.
  Only other SetCharacterData caller: btlseq.cs:711, member 55 (scale) — raw17 can never fire 32/33. ✓

**(2) Corpus completeness.** p0data7 holds exactly **562** `evt_battle_*.eb` per language for ALL
7 languages (us/uk/jp/es/fr/gr/it, identical scene sets — no scene exists only outside `us`); us
`.eb` split = 818 field + 562 battle + 13 world. p0data2 holds exactly **562** raw17 battlescene
containers, 1:1 with the us .eb set (zero orphans in either direction). 562 IS the full stock
battle-scene corpus; the census enumerated all of it. ✓

**(3) False positives.** Structurally excluded (full engine-mirroring decode, no raw grep — note
event opcode `0x29` is QUAD, which carries immediate operand bytes, so raw grep is indeed unsafe).
Residual risk was a member-32/33 READ matching the regex: audited all 67 hit instructions — **all
67 are `... B_MEMBER(3x) const(1) B_LET_A` WRITES**; 11 distinct instruction shapes total, zero
read-shaped matches. False NEGATIVES: the census's `except IndexError: pass` could silently truncate
a function — instrumented re-run over all **6172** battle-.eb functions: **0** truncations, 0 bytes
skipped. ✓

**(4) Name mappings.** Spot-checked 4 ids by raw `.mes` byte dump (independent of `_mes_strings`):
id 303 → "Plant Brain", id 71 → "Magic Vice" (with an "Escape" ability string — the flee), id 335 →
`[STNR]`/Haagen/Weimar, id 155 → "Amdusias". typ_count re-read from raw16 via scene_codec: EF_E009 =
PD_E067 = PD_E068 = PD_E069 = 1 (class-A claim holds), TH_E004 = 3. ✓

**(5) Reachability.** Code-32 scenes are exactly {EF_E009, PD_E067, PD_E068, PD_E069} (from the
census JSON) — the latter three are disc-4 Pandemonium, so Plant Brain IS the only early code-32
fight; it is the forced disc-1 Evil Forest boss (Blank joins mid-battle — matches class-A cross-unit
32 + typ_count 1). Member-53 negative controls confirmed: SetCharacterData case 53u =
`btl.SetDisappear(val != 0, 3)` only (btl_scrp.cs:506-508) — render-only, no btl_list relink. ✓

**Corrections applied (cosmetic only, neither affects the test plan):** GT_E019A place label
("Gargan Roo/Treno line" → GT_* is not GR_* Gargan Roo; South Gate arc, label unverified);
AC_E076A-E disc label ("disc 3" → unverified; first plausibly reachable disc 2 Garnet rescue).
