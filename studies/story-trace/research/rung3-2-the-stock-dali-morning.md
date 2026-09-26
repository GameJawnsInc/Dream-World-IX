## 1. The stock Dali morning, in real story order

The line numbers below refer to US decompiles I made with `py -m ff9mapkit eb-src <id>`. They are in `<archive>\scratchpad\dali\<id>.ebs`. The census is `research/dominance_census.json`.

- **312 (overlook).** Writes SC 2530 and 2540 (census `sc_sites`), then exits only to `WorldMap(...)`. Which field the world map loads next is not found: the world scripts were never censused (narrative-state PLAN.md:100). No Dali field warps into 359.
- **359 (village entrance, arrival cutscene).** It never reads SC. Its Main_Init starts the ATE machine with no guard: `UInt16[297]:=1` (359:51), `2103:=0` and `2102:=0` (66-67, 79), words 239/241/251 zeroed, `ATE(0)`. It then warps with `Field(351)` at entrance 15 (344-345).
- **351 (inn lobby).** Zidane's entry 19 func 1 plays the innkeeper cutscene, then `Field(352)` at entrance 5 (351:3552-3797). The player only watches.
- **352 (inn room).** Entry 17 func 1 plays the night talk (1755-1921), the singing (1977-2006) and the wake (2073-2085). Writes on the way:
  - `SC:=2600`, with stock's own backwards-write guard (2503-2524)
  - `2078:=1` and `2086:=1` (2096-2097), then the ATE offer (2098-2140)
  - `RemoveParty` (2143-2145)

  The player walks out through the entry 14 gateway, which leads to 351 at entrance 6 (1123-1196).
- **351 → 350.** The entry 16 walk-in sends the player to 350 at entrance 2 (351:3258-3321).
- **350 (Village Road).** Free roam. The world exit is blocked while 2600 ≤ SC < 2640 ("I can't leave by myself", 350:3412-3426). The entry 32 gateway leads to 450 at entrance 1 (3601-3648).
- **450 (Dali/Field).**
  - `fork-report 450 --explain` finds one interactive NPC, the Old Lady.
  - While SC < 2610 she says "A girl? I saw her go back to the village" (450:929-931). The script itself points the player back.
  - The world exit is blocked here too (1975-1989).
  - Walking back uses the entry 19 gateway to 350 at entrance 25 (2181-2243).
- **354 (weapon shop).** Garnet spawns only when `297&1 && 2079==1 && 2600≤SC<2610` (354:76-85). Her entry 13 func 1 writes `SC:=2610`, `Byte208:=1` and `2074:=1` (354:2818-2848).
- **After 2610.** From 352 the story warps into 355 at entrance 18 (352:2768-2769). The SC ladder then runs 2640 (355), 2650 (352), 2660 (358), 2680 (353/356), 2700 (404), per census `sc_sites`.

## 2. Where 2102 is written in 450

The census holds exactly three `2102 := 1` stores, all in 450. Every other Dali store of 2102 writes 0.

- **(a) Entry 19, the gateway to 350, func 2 (walk-in), 450:2186-2199.**
  - Guard: `SC<2610 && 2085==0`, then `297&1 && 2079==0`.
  - If `2055==0` it writes `2102:=1` and `SByte296:=3`; otherwise `2102:=1` and `296:=2`. It then sets the once-latch `2085:=1`.
  - It fires when the player crosses the region at 2179, walking back toward the village. It is a one-shot crossing, not a loop.
  - Census offsets 11669 and 11690.
- **(b) Entry 5 func 1 (every-frame loop), state 16, 450:1124-1134.** This is the end of the "Dggr Tries" ATE.
  - How it is reached: the ATE menu sends `Field(450)` with entrance 16 (450:514-540). Garnet (entry 23) spawns for entrance 16 (91-94) and sets state 16 at 3003.
  - It writes `2087:=1` (under `297&1`), `2102:=1`, `296:=3`, `2103:=1`.
  - The function itself checks no SC. The census arms it under SC<11090, SC≠2810 and SC≠2840.

The site at story-trace PLAN.md:66 ("e2 tag 1 ip 479") is the controller's **clear** (`2102:=0`), which exists in 350-358 and 450. The trace will record Bit[2102] rows in many fields; only the value-1 rows are unique to 450.

**What 2102 does.** It arms a countdown in the shared controller: entry 2, 3 or 4, func 1 in each room (450:672-749). On each room entry the controller decrements `296`, but undoes it:
- in 350 (room code 1);
- in 352, 354 and 353 (codes 6, 7, 9) when the count would reach 0;
- when `Int16[2]==10000`, or `==16` at zero (676-704).

When `296≤0 && 2103==0` it writes `2079:=1`, and `2075:=1` if `2064==1`. It then offers the ATE and resets `296:=-64` and `2102:=0`. Each field sets its room code before the controller starts, e.g. `450:52=25`, `350:52=1`, `351:54=2`.

## 3. Latch and hub-word writers during the morning

| Write | Where | Guard |
|---|---|---|
| `297:=1` | 359:51 only | none; nothing writes it later in the morning |
| `2078:=1`, `2086:=1` | 352 wake, 2096-2097 | none |
| `2078:=0`, `2064:=1` | 351 lobby exit, 3263-3277 | SC<2650, `297&1`; 2078 only if `2078==1 && 2073==0`; 2064 only if `2064==0` |
| `2086:=0` | 450 Main_Init, 57-65 | `Int16[2]≠16 && 297&1 && 2086==1 && 2087==0` |
| `2087:=1` | 450 entry 5, 1126 | `297&1` |
| `2079:=1`, `2075:=1` | the controller in whichever room the count reaches 0 (350:685 … 450:712) | `2102==1 && 296≤0 && 2103==0 && 297&1` |
| `2074:=1` | 354:2846 | after `SC:=2610` |
| `2103:=0` / `2103:=1` | cleared by walk gateways (350:3446, 3606; 351:3279); set by ATE ends (450:1134; 354:292, 942) | — |

I did not trace the windows for 2072, 2073, 2076, 2065 or 2077.

**Diff prediction against the round-4 seed.** Round 4 seeded 2064/2075/2079 and bytes 239=6 and 296=192, but no 297 (PLAYTEST.md:150-157, 176). Every write above except the unguarded wake pair needs `297&1`. So STOCK ONLY against that run should be:
- the 351 lobby's 2078 and 2064 writes
- 450 Main_Init's `2086:=0`
- 450 entry 19's `2102`, `296` and `2085`
- the controller's `2079`, `2075`, `296:=-64` and `2102:=0`
- 354's `2610` and `2074`

To isolate the latch defect alone, seed 297 but keep 2079 pre-set. The gateway's inner guard (2188-2189) then fails, and the named pair is `2102` and `296` in 450 entry 19. In the round-4 chain, 450 was an unforked exit into the real game (PLAYTEST.md:178-180). Any fork-side row with `fld=don=450` therefore names the missing member with no script reading.

## 4. The minimum stock segment

**Both (a) and (b), in three gateway crossings.**
1. New Game, `storytrace 1`, poke the low byte of word 297 to 1. That is the only seed; latches stay clear.
2. `warp 351 6 2600` (the entrance 352 uses into 351).
3. Cross 351's entry 16 exit. The script flips `2064:=1`.
4. In 350, cross entry 32 into 450.
5. Cross 450's entry 19 gateway. The script writes `2102:=1`, `296:=3`, `2085:=1`.

The harness verbs `cross`, `walk_to` and `find_transitions` are at `tools/harness/session.py:1348,1646,1683`.

**To also get the controller's latch flip** (`2079` and `2075`): make three counted room entries after the ping. 350 never counts, so one route is 350→351→350→450→350→351, which flips in 351's entry 4. Walk these rather than warp: `Bit184` forces `Int16[2]=10000`, which skips the count (450:10-12). I could not find out whether the ~ menu warp sets bit 184.

**Choosing the route without assuming the answer.** An alternative needs no seed at all beyond SC:
1. `warp 359` at SC 2540. 359 reads no SC and writes 297, 2102 and 2103 itself.
2. `watch_cutscene` through 351 and the 352 wake.
3. Stop when SC leaves 2600.

That stopping rule forces a pass through 450. SC 2610 needs 2079 (354:76-80), 2079 needs `2102==1` (the controller's first test), and only 450 writes `2102:=1`. The player gets there either by walking (entry 19) or through the "Dggr Tries" ATE (entry 5). The route is picked by "reach the next SC advance", not by "visit 450".