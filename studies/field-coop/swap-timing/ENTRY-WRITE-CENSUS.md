# Entry-Write Census

Owner decision 5 of `studies/field-coop/SWAP-TIMING-S164.md` (accepted risks 3 and 11).
Script: `studies/field-coop/swap-timing/entry_write_census.py`. Every count below is its output on the 817 exports in
`C:\gd\FFIX\reference\test2\`; the judgements about which fields a guest enters are mine and are marked. Cites are `export file:line` (1-based, the `us` section). The HW index in the file name is not
the field id; the id and name come from `reference/field-manifest.tsv`.

## Question

The guest's story pin stages the host's story frame from before the host's landing hook, and the guest copy's own `Main_Init`
runs on it. So what do the fields' `Main_Init` functions do to save-persistent variables? A constant store gives the same
result on either frame. Anything that depends on the old value, on a dice roll, or on the arrival entrance can differ.

## Method

- **Input.** The `us` section of each export. 411 exports also carry a `jp` section and 100 an `en` section; `--compare-langs`
  classifies those too (below).
- **Which variables.** HW's names are inverted against the engine's: `VAR_Gen*` / `VARL_Gen*` are engine Global
  (`gEventGlobal`, save-persistent); `VAR_Glob*` / `VARL_Glob*` are engine Map (transient); `VAR_Loc*` are the entry's locals
  (`content/region.py:38-40`, `studies/story-trace/research/design-5-claim-checks.md:10`). Scanned as persistent: `VAR_Gen*`,
  `VARL_Gen*`, and the named gEventGlobal words `General_*` (ScenarioCounter = bytes 0-1, FieldEntrance = bytes 2-3, LoadedGame =
  byte 184), `Setting_*`, `Chocobo_*`, `ATE_*`, `Mognet_*`, `Minigame_*`, `World_*`. The suffix is a byte offset (a bit index for
  `Bool`), so overlap between widths is computed on bit spans.
- **Scope.** `Main_Init`, plus the Init (tag 0) function of the entry that `Main_Init` starts first: the first `InitCode`,
  `InitObject` or `InitRegion` call whose function exists in the export. All 817 first calls use tag 0. Six Palace fields
  (2213, 2215, 2216, 2217, 2220, 2221) start entry 251 first, a runtime team slot with no code in the export, so the next call is
  used. Two supplementary passes count (but do not list) the Init of every other entry `Main_Init` starts, and every other
  function.
- **Parse.** A line-based statement tree (if / else / ifnot / while / do / switch / case). 0 parse problems over 817 fields.
  Assignments hidden in expressions (`set X = ( Y += ... )`) are found by pattern (8 in scope).
- **Classes**, one per write statement, first match wins. A field's classes are the set of its writes' classes, so field counts
  overlap.

| class | rule |
|---|---|
| stock prologue | the block every field opens with (below) |
| bytes 2-3 | the target overlaps `General_FieldEntrance` |
| random-gated | the stored value comes from `GetRandom` (directly, or through a variable that took one earlier in the function text), or an enclosing condition tests such a value |
| once-gated | an enclosing branch is guarded by a persistent variable that a statement of the same branch (unconditional within it, or the write itself) drives to a state the guard no longer admits; checked by brute force over the guard's value range |
| read-modify-write | a compound operator, `++` / `--`, an RHS that reads the target, or a guard that reads the target |
| set | the RHS is a constant expression and none of the above applies |
| derived | the RHS reads other state (a copy or a computed value) and none of the above applies |

- **The stock prologue.** All 817 fields open `Main_Init` with: `VAR_GenBool_191 = 0`; `General_LoadedGame = 0`;
  `if LoadedGame == 1 { FieldEntrance = 10000 }`; and two environment-sound slot records (`VAR_GenInt16_9` / `_11` set to a sound
  id or 65535, with `VAR_GenUInt8_13` / `_14` as a state machine that prints "Error Env Play() Slot=0" at state 9;
  `test2_1.txt:12-60, 77`). Each store is a constant or a state machine with a fixed point (applying it twice gives what applying
  it once gives), and the `FieldEntrance` write needs a save-load latch. It is 11,412 of the 13,726 persistent statements, so it
  has its own row and is excluded from every other count.
- **Self-test.** `entry_write_census.py --selftest` classifies a synthetic `Main_Init` with every class and two negative controls
  (an unclosed guard; a transient store) and passes. A copy with the gate-closing check disabled fails it, so the once-gated rule
  can fail.

## Counts per class

13,726 persistent write statements in scope (13,490 in `Main_Init`, 236 in the first Init function; 14 fields have any in the
Init function).

| class | fields | statements | fields, first Init function |
|---|---|---|---|
| stock prologue | 817 | 11,412 | 0 |
| bytes 2-3 (beyond the prologue's load-gated store) | 56 | 82 | 0 |
| random-gated | 1 | 17 | 0 |
| once-gated | 91 | 242 | 13 |
| read-modify-write | 160 | 331 | 14 |
| set | 221 | 1,437 | 14 |
| derived | 120 | 205 | 2 |

515 fields have only the prologue. The other 302 have at least one more write; each of them once, under its highest-concern
class (random-gated > bytes 2-3 > read-modify-write > once-gated > derived > set): random-gated 1, bytes 2-3 55,
read-modify-write 150, once-gated 21, derived 2, set only 73.

Inside the classes:

- **bytes 2-3** (82 statements): keyed on ScenarioCounter 34 (29 fields); on both FieldEntrance and ScenarioCounter 23 (12); on
  another variable 9 (9); on FieldEntrance alone 7 (4); writes the value it just tested (no-op) 5 (5); unconditional 4 (4).
- **random-gated**: stores a random value 9, random decides a branch 8, the roll-once idiom (`if var is unset: var = random()`) 0.
- **once-gated**: 129 guarded by a flag or variable (49 fields); 113 by a named word (44), mostly the `Setting_PartyInitialized`
  bit tests and ScenarioCounter floor snaps.
- **read-modify-write**: bit-mask `|=` / `&=` 159 (118 fields; the ATE staging cluster `VAR_GenUInt16_251 |=` and
  `Setting_PartyInitialized |=`); a counter that is assigned earlier in the function 126 (27 fields; `x = 0 ... x++` scratch
  such as `VARL_GenUInt8_303` and `_399`); a guard on the target 43 (32; ScenarioCounter clamps and the like); self-referential 2
  (Chocobo's Forest beak level, `test2_221.txt:57-58`); toggle 1 (below); **an accumulating counter 0**.
- **set**: 1,282 statements sit under a guard (200 fields), 155 do not (53 fields).
- **derived**: copies 153, computed 47, `GetTime` 5.

The most shared non-prologue signature is the ATE staging cluster: `VAR_GenInt8_238` and `VAR_GenInt16_241` set to 0 or 1 (119
fields), `VAR_GenInt16_241 = VAR_GenUInt16_236` (55) and `VAR_GenUInt16_251 |= ...` (55 + 19).

## What this says about accepted risks 3 and 11

- **Risk 3 (roll-once globals).** The literal idiom does not occur in scope: 0 statements. Randomness reaches persistent state in
  exactly one field, Qu's Marsh / Entrance (650), as a fresh roll every visit, not a roll-once. See the list below. (INFER: the
  pin makes the guest's copy re-run that tick with its own rolls; the latest frame would instead hand it the host's result. The
  tick also reads `GetTime`, so its outcome depends on the stored per-area time. The mirror lane's later frames may overwrite the
  guest's result; this census does not read that.)
- **Risk 11 (FieldEntrance rewrites).** 56 fields rewrite bytes 2-3 in scope, listed below. Their guards are functions of
  FieldEntrance, ScenarioCounter and flags, all in the pinned frame, or of Map variables that `Main_Init` assigns from story
  state before it tests them (`G30` in `test2_651.txt:51-56` and `test2_299.txt:139-147`; I did not read every one). So the
  guest's copy should land on the host's rewritten value. The one guard that reads outside the story frame is 765's
  `GetItemCount(32)` (the bag, which the pin leaves on the latest frame).
- **Where the pin is the only thing that matters.** One write in scope is not replay-safe: `VARL_GenBool_3966 ^= 1`, unconditional
  at the top of Alexandria / Steeple (2456, `test2_662.txt:174`). It flips every entry. It is read by Alexandria / Alley (2453,
  `test2_659.txt:60, 72`) and Alexandria / Mini-Theater (2457, `test2_663.txt:84`), which choose between NPC sets on it. On the
  latest frame the guest would flip back what the host just flipped.
- **ScenarioCounter (bytes 0-1)** is written in scope by 56 statements in 30 fields. 30 of them raise it to a floor or step it
  forward (`if SC < N: SC = N`), including two unconditional stores: Prima Vista / Event (209, `test2_66.txt:49`, 1900) and
  L. Castle / Telescope (1365, `test2_378.txt:57`, 3118). 11 sit behind an unsatisfiable `SC < N and SC > N`. 15 set it back
  down to the field's value while `IsButton(8)` is held (1352, 1422, 1505, 2652 and 11 `Ending/*` fields); that reads the local
  player's button, which no frame carries. All are idempotent on a given input.
- **The rest is replay-safe by shape**: constants, bit-ORs, snaps, copies of variables `Main_Init` does not change, and once-gated
  blocks (the latest frame skips the block, the pinned frame reruns it to the same state). This is from the shape of the code; the
  census executes nothing.

## Random-gated fields (full list)

| field | name | export cite | statements |
|---|---|---|---|
| 650 | Marsh/Entrance (Qu's Marsh) | `test2_176.txt:852, 854, 856, 909, 925, 926, 928, 930, 935, 938, 941, 944, 945, 985, 992, 999, 1006` | stores random 9, random branch 8 |

What they are: the Qu's Marsh frog-population tick that `Main_Init` runs on entry. `:852, 909, 928` roll `GetRandom` into the scratch
byte `VARL_GenUInt8_399`; `:944, 945` store `GetRandom % 3 + 1` and `GetRandom % 127 + 128` into `VARL_GenUInt8_801` / `_802`;
`:854, 856, 925-941` store branch results and bit-field updates (`VARL_GenUInt16_803`, `VARL_GenInt8_784`) under those rolls;
`:985-1006` write the random-fed bit mask back into `VARL_GenUInt8_780-783`. It first reads `GetTime` (`:96`) against the stored
per-area times `VARL_GenInt24_768 / 771 / 774 / 777`.

Time-derived persistent stores in scope (not random, same non-determinism): `VARL_GenInt24_429 = GetTime` in 650 (`:96`) and in the
four ponds, 656 (`test2_224.txt:130`), 657 (`test2_182.txt:242`), 658 (`test2_225.txt:130`), 659 (`test2_226.txt:130`).

## Bytes 2-3 fields (full list)

`SC` = ScenarioCounter, `FE` = FieldEntrance, `G30` = `VAR_GlobInt16_30` (a Map variable set earlier in the same `Main_Init`).
The last column is **my reading of the game's story order, not derived from the exports**: main = on the walkthrough path (the
ScenarioCounter windows in the guards corroborate it for most rows); side = an optional room; plumbing and ending as named.

| field | name | export cite | rewrite | guest in ordinary play |
|---|---|---|---|---|
| 51 | Prima Vista/Cargo Room | `test2_2.txt:108, 111` | SC>=1420 -> 104; SC>1900 -> 3 | main |
| 54 | Prima Vista/Hallway | `test2_5.txt:53` | SC<1410 -> 104 | main |
| 55 | Prima Vista/Music Room | `test2_6.txt:52` | SC<1400 or FE==106 -> 106 | main |
| 70 | Opening-For FMV | `test2_21.txt:92, 136` | FE==0 -> 0 (before `Field(50)`); FE==1 -> 0 (before `ChangeDisc`) | plumbing: New Game and every disc change |
| 101 | Alexandria/Main Street | `test2_23.txt:60` | flag 3717 clear -> 202 | main |
| 112 | Alexandria/Pub | `test2_34.txt:48` | SC>=1900 -> 10000 | main |
| 115 | Alexandria/Steeple | `test2_37.txt:66, 69, 72` | SC 1152-1155 -> 213 / 214 / 215 | main |
| 153 | A. Castle/Hallway | `test2_42.txt:51` | SC>1900 -> 3 | main |
| 502 | Cargo Ship/Bridge | `test2_122.txt:153` | unconditional -> 5 | main |
| 503 | Cargo Ship/Bridge | `test2_123.txt:463` | FE==65534 -> 11 | main |
| 650 | Marsh/Entrance | `test2_176.txt:57, 60, 63, 66` | FE 9998 / 9997 / 9996 / other (FE&4080 != 48) -> 12276 / 20468 / 36852 / 8180 | main |
| 701 | Gizamaluke/Entrance | `test2_185.txt:61` | SC<3710 -> 502 | main |
| 703 | Gizamaluke/Cavern | `test2_187.txt:103` | SC<3720 -> 504 | main |
| 707 | Gizamaluke/Sacred Room | `test2_191.txt:123, 135` | SC<3740 -> 512; FE<0 or ==513 -> 513 | main |
| 750 | Burmecia/Gate | `test2_192.txt:66` | SC<3800 -> 601 | main |
| 758 | Burmecia/Pathway | `test2_200.txt:77` | SC<3870 -> 610 | main |
| 760 | Burmecia/Uptown Area | `test2_202.txt:78` | SC<3880 -> 618 | main |
| 765 | Burmecia/Armory | `test2_207.txt:63` | flag 3847 clear, SC<4990, `GetItemCount(32)` < 99 -> 622 | side (a shop room) |
| 766 | Burmecia/Palace | `test2_208.txt:82` | SC<3900 -> 624 | main |
| 908 | Treno/Gate | `test2_248.txt:49` | SC<4400 -> 9999 | main |
| 956 | Gargan Roo/Last Stop | `test2_266.txt:81, 84` | SC>=6990 -> 65533; 4990<=SC<6990 -> 65534 | main |
| 1000 | Cleyra/Tree Roots | `test2_268.txt:54` | SC<4650 -> 701 | main |
| 1001 | Cleyra/Tree Roots | `test2_269.txt:56` | SC<4660 -> 502 | main |
| 1010 | Cleyra/Bridge | `test2_278.txt:60` | FE>=0 and SC>=4800 -> 714 | main |
| 1051 | Cleyra/Entrance | `test2_288.txt:208, 227` | SC<4700 -> 802; FE==802 -> 802 | main |
| 1052 | Cleyra/Sandpit | `test2_289.txt:217` | unconditional -> 806 | main |
| 1101 | Cleyra/Entrance | `test2_299.txt:184` | G30==8 -> G30 | main |
| 1107 | Cleyra/Observation Point | `test2_305.txt:250` | G30==817 -> G30 | side |
| 1108 | Cleyra/Cathedral | `test2_306.txt:296` | `VAR_GlobInt16_32`==823 -> that value | main |
| 1109 | Cleyra/Cathedral | `test2_307.txt:206` | flag 3889 clear -> 825 | main |
| 1150 | Red Rose/Deck | `test2_309.txt:73` | SC>=5020 -> 901 | main |
| 1152 | Red Rose/Cabin | `test2_311.txt:50` | SC<5020 -> 905 | main |
| 1205 | A. Castle/Chapel | `test2_318.txt:55, 58, 61, 64, 67` | FE != 20: SC steps 5030 / 5080 / 5100 / 5120 -> 406 ... 410 | main |
| 1600 | Mdn. Sari/Entrance | `test2_443.txt:274, 277, 371` | SC 6650 (FE==65535), 6870, 6795 -> 17, 36, 18 | main |
| 1605 | Mdn. Sari/Eidolon Wall | `test2_448.txt:641` | SC==6810 -> 20 | main |
| 1606 | Mdn. Sari/Resting Room | `test2_449.txt:304` | SC==6860 -> 26 | main |
| 1608 | Mdn. Sari/Secret Room | `test2_451.txt:390, 398` | SC==6800 -> 19; SC==6840 -> 22 | main |
| 1656 | Iifa Tree/Eidolon Mountain | `test2_460.txt:131` | SC==6970 and FE==65535 -> 39 | main |
| 1663 | Iifa Tree/Tree Trunk | `test2_467.txt:45, 63` | FE==65535: SC==6930 -> 34; SC<=6950 -> 40 | main |
| 1750 | Iifa Tree/Hollow Roots | `test2_468.txt:84` | FE==65535 -> 26 | main |
| 1757 | Iifa Tree/Outer Seal | `test2_475.txt:179, 191` | SC==6790 and FE==65535 -> 30; SC==6890 -> 31 | main |
| 1800 | A. Castle/Tomb | `test2_478.txt:51` | SC>=10250 -> 1 | main |
| 1802 | A. Castle/Garnet's Room | `test2_489.txt:52, 55` | FE != 440: SC<=7030 -> 427; SC>=7040 -> 428 | main |
| 1807 | A. Castle/Hallway | `test2_492.txt:129` | 8500<=SC<8600 -> 309 | main |
| 1864 | Alexandria/Mini-Theater | `test2_524.txt:207, 210, 213` | SC<7030 -> 235; SC<7300 -> 5; else -> 236 | main |
| 1866 | Alexandria/Dock | `test2_526.txt:312` | 7100<=SC<7200 -> 233 | main |
| 2007 | A. Castle/Altar | `test2_551.txt:54, 65, 84` | SC<8400 or FE==2 -> 2; 8500<=SC<8700 (FE != 450) -> 452; else -> 453 | main |
| 2055 | Invincible/Garland | `test2_559.txt:15` | SC==8800 -> 65534 | main |
| 2402 | A. Castle/Port | `test2_651.txt:79` | scene-variant default (G30) -> 25 | main |
| 2404 | A. Castle/Courtyard | `test2_653.txt:100` | G30==25 -> 25 | main |
| 2450 | Alexandria/Main Street | `test2_656.txt:99` | scene-variant default (G30) -> 25 | main |
| 2453 | Alexandria/Alley | `test2_659.txt:83` | scene-variant default (G30) -> 25 | main |
| 2550 | Earth Shrine/Entrance | `test2_677.txt:15` | SC != 10660 and FE==9991 -> 0 | main |
| 2850 | Hilda Garde 3/Bridge | `test2_730.txt:425, 447, 450` | FE==0: SC 10400 / 10595 / 10600-10679 -> 65526 / 65525 / 65524 | main |
| 3010 | Ending/TH | `test2_805.txt:61` | unconditional -> 65535 | ending only |
| 3011 | Ending/TH | `test2_806.txt:45` | unconditional -> 65535 | ending only |

## Which of these a guest is likely to enter

- **bytes 2-3:** 51 of the 56 are on the walkthrough path, so a follower passes through them in ordinary story play (by the
  ScenarioCounter windows they are visited exactly when the story reaches them). Not on the path: 765 and 1107 (optional rooms),
  70 (entered at New Game and at disc changes, not walked into), 3010 and 3011 (the ending only).
- **random-gated:** 650, Qu's Marsh / Entrance, is on the path as I read the game (the party reaches the marsh in the story, and its
  `Main_Init` carries a `SC >= 5990` block), so a guest follows into the one field whose entry code rolls dice. The four ponds
  (656-659), which also store `GetTime`, are the frog-catching rooms, optional as I read the game.
- **the toggle:** 2456 Alexandria / Steeple and the two fields that read it, 2453 and 2457, are in the late-game Alexandria
  block (the 2456 `Main_Init` carries `SC >= 10300` content). A guest reaches them if the host does; I do not know whether the
  story forces that visit.

## What the classifier cannot see

1. **Anything outside `Main_Init` and the first Init function.** Counted, not listed:
   - 52 fields write persistent state in the Init of *other* entries `Main_Init` starts (640 set, 297 derived, 248
     read-modify-write, 104 once-gated).
   - **Loop, Range, Reinit and talk functions, which run after the Init.** There, 111 fields hold accumulating counters (325
     statements), 22 hold random-gated stores (1,761 statements) and 18 hold `GetTime` stores (26). The counter that the pin's
     rationale quotes, Dali's `SByte[296]` countdown, is among them: it is in the `Code*_Loop` of ten Dali fields (350-358 and
     450; `test2_112.txt:578, 580` for 450), not in `Main_Init`. The random ones are the Festival of the Hunt scores
     (`VARL_GenUInt16_314` / `_316`, `studies/fort-condor/RUNG0.md:30-31`) in a `Code2` tag-11 function of 13 Lindblum fields
     (550-572), the Chocobo's Forest / Lagoon / Air Garden barrel functions (2950-2952), the pond functions (656-659),
     Dali / Inn (351) and Alexandria / By the Steeple (106). The `GetTime` ones are in the Lindblum and chocobo functions
     above plus the Marsh / Entrance and Marsh / Cave region ranges (650, 663).
   - `Main_Init` also launches another script (`RunScript*`, `RunSharedScript`) in 12 fields (20 calls); the targets are not
     followed.
2. **Execution.** Nothing is run. A class means "this statement can write", not "this entrance and this scenario take it": 1,282
   of the 1,437 `set` statements are under a guard that is never evaluated. The only evaluation is the once-gate brute force, and
   only over a guard that is a function of one variable and constants (a conjunct that mentions anything else is ignored).
3. **Once-gates closed elsewhere.** A gate is recognised only when a statement in the same branch closes it with a constant or a
   `++` / `|=` store. A flag set by another function (Chocobo's Forest `VARL_GenBool_1423`, `test2_221.txt:52-58`) leaves the block
   classified by its own shape.
4. **Randomness and time reaching state indirectly.** `GetRandom` is tracked forward in text order through variable copies inside
   one function. It is not flow-sensitive (a later overwrite does not clear it), not loop-carried (a use that sits textually before
   the roll is missed), and does not cross functions, so a value rolled in a Loop and read in `Main_Init` is invisible. `GetTime`
   is flagged only when stored directly. Other reads that differ per player are not flagged at all: party and inventory reads
   (`IsInParty`, `GetItemCount`; the pin leaves those on the latest frame), `GetHP`, button state.
5. **Variable names.** Persistent versus transient is decided by the HW name. Named words other than ScenarioCounter,
   FieldEntrance and LoadedGame have no known byte position here, so they cannot be matched against a `VAR_Gen*` write to the same
   bytes. `Field_*` and `Treasure_*` are treated as transient. `World_*` is treated as persistent but only `World_CurrentTransport`
   is written in scope (one statement).
6. **Effects that are not `gEventGlobal` writes.** Party, bag, HP / MP and status changes made by `Main_Init`: only 5 fields
   call them (563, 911, 2200, 2800, 2850: `AddItem`, `AddParty`, `RemoveParty`, `Party`, `SetCharacterData`, `SetHP`, `SetMP`,
   `CureStatus`). Engine C# that writes `gEventGlobal` for a specific field (the hotfixes in `DoEventCode`) is not in any export.
7. **The first Init function is a static reading.** The six Palace fields whose first call is a team slot (251) fall back to the
   next call; which character's entry the slot resolves to at run time is not known here.
8. **Languages.** Classified on `us`. The `jp` section of three fields classifies differently in scope (1052 Cleyra / Sandpit,
   2172 L. Castle / Telescope, 2173 L. Castle / Harbor). The 100 `en` sections, the 17 separate `de` / `fr` / `it` / `sp`
   sections and every other `jp` section classify the same.
9. **Modified scripts.** These are the shipping scripts as HW prints them. A fork or a kit-built field that edits `Main_Init` is
   not covered.

## Reproduce

```
py -I studies/field-coop/swap-timing/entry_write_census.py                      # about 1 minute
py -I studies/field-coop/swap-timing/entry_write_census.py --compare-langs --json out.json   # about 2 minutes
py -I studies/field-coop/swap-timing/entry_write_census.py --selftest
```

The first argument is the exports directory (default `C:\gd\FFIX\reference\test2`). `--manifest` points at a different
`field-manifest.tsv`.
