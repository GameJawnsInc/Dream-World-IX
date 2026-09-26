**Rung-3 Dali retrodiction design: adversarial check**

The worst problem: the round-4 seed zeroes byte 297, so F4 can't isolate the latch defect.

**CLAIMS**

1. **Claim:** F4 carries the latch defect alone, and the latch (2079=1) blocks the 450 ping.
   - **Verdict:** wrong. Two causes are mixed together.
   - **Evidence:**
     - Running the round-4 kit's seed builder for donor 351 prints `words = [{byte=239,value=6},{byte=296,value=192}]`.
     - `words` compile as 16-bit writes (r4kit `content/startup.py:63-67,78-79`; same today, `content/startup.py:31`). So every 350-358 member entry writes byte 296=192 **and byte 297=0**.
     - Only 359 writes 297 (census word_sites; `359.ebs:51`). From the 351 member on, `297&1` is 0.
     - That kills every hub-gated write, not just the latched ones:
       - 450 e19 (`450.ebs:2188`, `297&1 && 2079==0`): both terms fail.
       - Garnet's spawn guard in the weapon shop (`354.ebs:76`) is false.
       - The 352 wake offers no ATE (`352.ebs:2098-2140`).
       - The 351 e16 writes of 2078 and 2064 don't happen (`351.ebs:3263-3277`).
   - **Correction:**
     - The falsifier "F4 writes the ping" cannot fire, so it can't test the latch model.
     - Add a variant that keeps round 4's latches but writes 239/296 as single bytes, or drops them.
     - Owner question 2 can be answered from the scripts: under round 4 as built, Garnet should **not** have been in the shop.
     - The reader's "no 297" STOCK ONLY prediction was the right one.

2. **Claim:** F4 may be cut off by Garnet before reaching 450.
   - **Verdict:** wrong.
   - **Evidence:** Garnet's guard is false (item 1). Even if she spawned, every member door re-stamps SC to 2600, rewinding her 2610 (PLAYTEST.md:204-207).

3. **Claim:** what STOCK ONLY should contain for F4.
   - **Verdict:** incomplete.
   - **Correction:** add the 351 e16 `2078:=0`, the wake's ATE branch (238=1, 241=6, 251), 450 Main_Init `2086:=0` (`450.ebs:57-65`) and the controller's 296 decrements.
   - The "SC-gated keys in 351/352" item finds nothing: 351's arrival path gates on entrance 15, not on SC (`351.ebs:71-85`).

4. **Claim:** F0 members never write 2102=1; only the real 450 does, across the seam.
   - **Verdict:** confirmed.
   - **Evidence:**
     - The census lists 2102=1 only at 450 e5 and e19.
     - The zone labels differ: `vgdl` for the 11 members, `airp` for 450.
     - Verbatim forks keep unlisted targets as live exits (`extract.py:2071-2077`).
     - The real 450's exit leads to the real 350 (`450.ebs:2242-2243`).
     - The engine does not redirect a field-to-field `Field()`. The fork-sibling redirect is used only at `ff9.cs:9327`, `HonoluluBattleMain.cs:737` and the debug world warp.

5. **Claim:** the start at 359 / SC 2540 is the story's own route.
   - **Verdict:** confirmed, with one part unverifiable.
   - **Evidence:**
     - 312 writes 2540, then exits only to the world map (`312.ebs:191-196,255-291`).
     - No field anywhere in the game warps into 359 (checked every field's warps).
     - 359 never reads SC. It touches the entrance word `Int16[2]` only at `:12` and `:344`.
     - It sets the party itself (`359.ebs:145-205`, entry 0's main loop).
   - **Unverifiable:** which field the world map loads, and the SC on arrival. The world-title `SC += 10` (`ff9.cs:7166-7168`) could change it, but that doesn't matter because 359 reads neither.

6. **Claim:** `warp(359, 0, 2540)` then `watch_cutscene`.
   - **Verdict:** wrong as written.
   - **Evidence:** `session.warp` ends in `wait_playable` (`session.py:1549-1565, 1023-1038`), which needs control and never presses Confirm. 359→351→352 is all cutscene, so it will likely time out after 60 s.
   - **Correction:** send the raw `warp` command and wait for the field id, or catch the timeout.

7. **Claim:** the debug warp may set bit 184.
   - **Verdict:** resolved; it doesn't.
   - **Evidence:** rung-0/1 residue was only bytes 0-2 (PLAN.md:126-127, 141-145), and 552's Main_Init wrote no `Int16[2]:=10000`. `HarnessWarp` sets only the entrance and SC. Bit 184 is also masked as story noise.

8. **Claim:** the tour crosses "walk-in exits" in `scan_gateways` order, and 450 is entered only because 350 has an exit to it.
   - **Verdict:** order confirmed; the "walk-in" part is wrong.
   - **Evidence:**
     - Order for 350: 351, 354, 353, 353, 356, 355, 358, 450 — 450 is last.
     - `scan_gateways` takes any entry holding a region plus a `Field()` (`eventscan.py:105-138`), whatever triggers it.
     - 350's exit to 358 (e25) fires only on an Action button press, and only at SC 2650-2710 (`350.ebs:3061-3137`). At 2600 nothing happens.
     - Exits are listed twice or three times: 353 twice in 350, 353 three times in 356.
     - Door exits (350 e18-e23, 351 e18) do nothing unless the player faces the door, within 48/256 of a turn (`350.ebs:2516-2518`).
     - No story-conditional doors in these fields.

9. **Claim:** `walk_to` aborts when a scene takes control.
   - **Verdict:** wrong.
   - **Evidence:** it returns early only when the field changes (`session.py:1384-1388`). Under a cutscene it stalls, and `cross` then waits 20 s for a field change. It also steers one axis at a time, with no pathfinding.

10. **Claim:** a choice stalls `watch_cutscene` (`session.py:1830`).
    - **Verdict:** confirmed, low risk.
    - **Evidence:** choice prompts appear only in the ATE menus and NPC talk handlers, which the tour never reaches.

11. **Claim:** no encounters; world exits blocked at SC 2600-2639.
    - **Verdict:** confirmed (`350.ebs:3412`, `450.ebs:1975`).

12. **Claim:** the controller mechanics.
    - **Verdict:** confirmed (`450.ebs:669-749`).
    - **Evidence:** the room code is `Int16[239]`. The flip needs 2103==0. The depth-first tour flips in pass 2, on the 352→351 entry.

13. **Claim:** ids 30831-30859 are free; each deploy writes its ForkDonorPatch row; the engine reads it per folder.
    - **Verdict:** confirmed (live DictionaryPatch; `deploy_field.py:381-392`; s24 patch :272).
    - **Missed:** F0 and F4 fork every donor twice. The engine then logs a warning and disables the donor→fork redirect (s24 patch :293-307). The fork→donor mapping still works, so `don` stays correct. Harmless on this route.

14. **Claim:** the storytrace line references.
    - **Verdict:** confirmed: `WriteKey` at `storytrace.py:637`, which also carries `aligned`; harness rows skipped at :719-721; prefix rows at negative offsets, docstring :25-30; `flags.py:54`.
    - **Missed:** step-marker pokes are harness rows. After 64 changing values per site key (which includes the field) the engine only counts them (PLAN.md:62-64), so markers can disappear. A byte counter also wraps at 256.

15. **Claim:** checking the `[startup]` text is what makes F4 round 4.
    - **Verdict:** partial.
    - **Evidence:** the text reproduces round 4, but the build is today's `build.py`, which has had many commits since `d3e2f4a1`, and `_apply_startup` has gained new arguments.
    - **Correction:** also diff the compiled Main_Init prefix bytes.

**MISSED**

- **Stock's own later passes leave free roam.** After the flip, the stock tour reaches 354 and Garnet's scene starts on entry (`354.ebs:84` sets `Map.Int16[29]=12`). It writes SC 2610 (`354.ebs:~2818-2848`), which persists. That leads on to 350's SC==2610 scene (`350.ebs:4289`) and the story warp from 352 to 355 (`352.ebs:2768`). The design's rule "a side's tour ends when its field changes uncommanded" would cut the reference run itself. Define story-driven landings as part of the registered route.
- **The set comparison hides order.** A key the fork writes early and stock writes late comes out as matched.
- **The trace records no reads, so the 297 clobber appears as only a FORK ONLY `UInt16[296]=192` row.** That row's old/new values do show byte 297 going 1→0. Add a neighbour-byte clobber check to the report.
- **F4 also crosses into the real 450 and then the real 350.** Apply the seam split to F4, not only F0.
- **Runtime.** Nine runs of cutscene plus a multi-pass tour in one launch is likely hours. There is a `timescale` verb (HarnessAgent.cs:784). The rung-2 loop's pokes of bytes 236/237 must be dropped.

Files:
- `<worktree>\tools\harness\session.py`
- `<worktree>\ff9mapkit\ff9mapkit\content\startup.py`
- `<archive>\scratchpad\r4kit\ff9mapkit\ff9mapkit\content\startup.py`
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Memoria\Configuration\DataPatchers.cs`