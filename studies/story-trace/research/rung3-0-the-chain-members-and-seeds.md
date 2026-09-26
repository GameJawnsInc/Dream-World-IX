## 1. Where the chain lives, its members, and the seed at each round

- **The chain is not in git.** The source is `C:\gd\_ns_playtest\dali_chain\` and the hub is `C:\gd\_ns_playtest\hub\`. `git rev-parse` there fails with "not a git repository". Git holds only the kit revisions: round 4 is `d3e2f4a1`, round 5 `c5740c12`, round 6 `e9ddf006`, round 7 `b1b3c443`.
- **How it was built** (PLAYTEST.md:99-103): `import-chain 351 --verbatim --whole-zone`, then `story-seed --chain <dir> --beat N`, then one `deploy_field --id` per member.
- **Members** (campaign.toml:17-91): 30830 DL_INN/351, 30831 DL_VIW/312, 30832 DL_WHL/350, 30833 VGDL_DL_INN/352, 30834 DL_MYR/353, 30835 DL_SHP/354, 30836 DL_BAR/355, 30837 DL_WMS/356, 30838 VGDL_DL_WMS/357, 30839 DL_FWM/358, 30840 DL_ENT/359.
  - Round 5 added 30841 DL_FLD/450 (DL_FLD.field.toml:10,47; PLAYTEST.md:193-195).
  - campaign.toml is stale (mtime Aug 3 22:02) and has no DL_FLD entry.
- **The member tomls on disk are the round-7 state** (every mtime is Aug 4 09:53). None has a `[startup]`, and every retarget table includes `450 = 30841` (for example DL_WHL.field.toml:46). The seed now lives only in hub/journeys.toml:34-40: SC 2600, words 208=0 and 297=1, a four-member party, no flags.
- **The `.verbatim_eb.bin` files are the stock scripts.** All 12 are byte-identical to the install's donors, so the retarget is applied at build time.
- **Seeds per round:**
  - **Round 4.** I rebuilt it by running `d3e2f4a1`'s `storyseed.seed_text` against the current census, with the zone set to the 11 donors. It matches PLAYTEST.md:155-156 and :176.
    - Members 350-358: `scenario = 2600`, flags 2064/2075/2079 = 1, words 239=6 and 296=192. Member 352 also sets 2092, 2093, 7278 and 7279.
    - Members 312 and 359: scenario only.
    - `[party]`: 350 adds Zidane; 352 and 359 add all four.
    - There is no word 297 and no once-sentinel, so every door re-stamps the seed.
  - **Round 5:** SC 2600, the latches clear, word 297=1, words 239 and 296 dropped (PLAYTEST.md:184-198; test_storyseed.py:358-373).
  - **Round 6:** adds once-sentinel bit 8822. It was never played (PLAYTEST.md:216-227).
  - **Round 7:** the members are stripped; hub 30850 carries the seed (journeys.toml:20,34-40).

## 2. Deployed now? Redeploying round 4

- **Nothing of the chain is deployed.** The mod folders are FF9CustomMap, -world, MoguriMain, MoguriVideo, -schema and -msgs (Memoria.ini:6).
  - No `DL_*` or `VGDL_*` files exist in any folder.
  - No `FieldScene` is registered anywhere in 30831-30859.
- **Slot 30830 is now TRC552**, the rung-2 fork: FF9CustomMap/DictionaryPatch.txt:73, plus `30830 552`, the only row in its ForkDonorPatch.txt. So the chain's old base id is taken.
- -schema holds 30820/30821. Those are ROOM_A/ROOM_B, not the narrative-state forks.
- The registered 308xx ids are 30801, 30830, 30860-30863, 30870, 30880, 30883, 30890 and 30900+. So 30831-30859 are free today. About 40 worktrees exist, and ids they have claimed but not deployed can't be checked.

A round-4 rebuild can be done without touching anything live:
1. **Re-fork into a scratch dir:** `import-chain 351 --verbatim --whole-zone --out <scratch> --id-base <free> --fresh-ids --name-prefix <tag>`. A dry run with the current kit still finds exactly the 11 round-4 donors and lists `350 -> 450 [airp] (walk_in)` as an out-of-scope PORTAL. So 450 stays unretargeted, exactly as in round 4. The base must not be 30830.
2. **Seed it with the round-4 kit:** `git archive d3e2f4a1 ff9mapkit/ff9mapkit` into scratch, then run that copy's `story-seed --chain <scratch> --beat 2600`. It writes only into the scratch copy. The census was regenerated at `2574fe33` and still reproduces the round-4 values.
3. **Deploy one member at a time:** `tools/deploy_field.py <toml> --id N --mod-folder FF9CustomMap`.
   - Each deploy writes that member's ForkDonorPatch row (deploy_field.py:382-392), so trace rows carry `don`.
   - Do not use `deploy_campaign.py`. It replaces all of FF9CustomMap and would wipe TRC552 and about 35 other live registrations.
   - A separate folder gains nothing: EventDB is global, and a new folder needs a FolderNames edit.
   - One relaunch is needed, because new ids and ForkDonorPatch are read at launch.
4. **Keep `--name-prefix`** if a round-5 control chain is deployed alongside. Scene and `.eb` names resolve by name, highest folder wins.

## 3. The seams versus the real game

- **"The windmill" is donor 350.** PLAYTEST.md:144 calls it that, and its FBG is `dl_whl`.
  - Its only out-of-zone walk exit is 350 → 450, entrance 1 (campaign.toml:781-791, kind `portal`, "zone airp").
  - Every village member 350-358 also has scripted `Field(450, 16/17)` cutscene-loop hops (from `scan_all_warps`; for example 351 entries 3 and 13, tag 1).
  - 356 → 404, entrance 11, is a separate seam and is still live today (DL_WMS.field.toml:47). It is the round-7 hand-off (PLAYTEST.md:251-256).
- **At round 4, all of these led into the real 450.** The member comments still say "not in this chain: 450" (DL_WHL.field.toml:47).
- **Only the real 450 writes 2102 = 1.** In the census, those writes are at entry 19 func 2, offsets 11669/11690 (guarded SC < 2610), and at entry 5 func 1, offset 6133. Every other Dali site writes 2102 = 0: the 350-358 controllers and 359's Main_Init.
- **A round-4 run that enters 450 never comes back.** The real 450's exits (walk to 350 entrance 25, and `Field(35x, 17)` in entry 5 tag 1) lead to the real 35x fields, so the rest of the run is stock.
- **So yes, rung 3's premise fails as the report stands.** A fork-side run that crosses into 450 writes 2102 too, keyed as (donor 450, …). `WriteKey` has no `fld` field (storytrace.py:637-651), so that write matches the stock one, and 2102 never appears in STOCK ONLY.
- **The premise holds only in two cases:**
  - The fork run never crosses. But then 2102 appears only if the stock route visits 450, which is the circular choice.
  - The report splits fork-side rows by whether `fld` is a chain member. Any fork-side row whose `fld` is a real id then counts as a seam leak. "The chain had to go into the real 450 to get 2102 written" is then itself the retrodiction, and it needs no route choice.
- **Round 4's second defect shows up without any route choice.** The per-member `[startup]` prepend (2064/2075/2079 := 1) keys at negative offsets, which is FORK ONLY by construction (storytrace.py:25-30).

The round-4 kit export is at `<archive>\scratchpad\r4kit\`.