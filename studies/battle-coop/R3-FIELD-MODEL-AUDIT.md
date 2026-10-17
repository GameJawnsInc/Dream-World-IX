# R3 guest field model (s138-s141): audit of the design against the live stack

**What was audited.** The guest's own field model in `studies/battle-coop/R3-DESIGN.md`:
- section 3.4 (3.4.1-3.4.5), the build-order rows 13-16, 5.1's s138-s141 rows, 5.2, 6.1 and 6.12;
- the sitting-B boxes B19-B29 and the review-dress notes F1-F8 in Appendix A.

The owner's goal, in their words: "the guest to actually show which character they're puppeting (or a moogle if 1-person party)". Today the guest's own field body is always Zidane (model 98). The host's ghost of the guest already wears a party member through `NetSyncVisitor.ResolveDress`.

The design was checked against three sources:
- the live engine clone `C:\gd\FFIX\Memoria\Assembly-CSharp`, which matches the deployed stack through s137 byte for byte (`py -X utf8 tools/memoria_stack_replay.py diag` reads "29 of 29");
- the repo harness;
- the install, read-only: the field-script exports in `C:\gd\FFIX\reference\test2\`, plus models, clips and mapconfigs read from `p0data*.bin` with the kit's own readers.

The design's line numbers predate s131-s137. Every line cited below was re-found in the live clone.

**Names.** The action-replay audit called these patches s127-s130. Their build numbers are s138-s141, and this document uses only those.

**How.** There were four lanes, one per patch (s138, s139, s140, s141). Each lane produced a live line map, findings, decisions and nits. Two independent skeptics then tried to refute each serious finding against the live code and the install:
- 48 of the 50 serious findings survived both skeptics, and only those appear below as amendments;
- the two refuted findings are in section 5, one line each, so nobody argues them again;
- the lanes' 18 nits were checked only by their own lane, and are folded in where they apply, marked (nit);
- where lanes disagreed, section 3 makes the call, and section 5 lists the lane recommendations it overrode.

**Conventions.**
- Line numbers are live as of 2026-10-17.
- Clone paths:
  - `NetSync*.cs` are in `Memoria/Netsync/`.
  - `HarnessAgent.cs` is in `Memoria/Harness/`. It is LF; every other clone file named here is CRLF.
  - `DoEventCode.cs` means `Global/Event/Engine/EventEngine.DoEventCode.cs`. `EventEngine.cs`, `ProcessAnime.cs`, `ProcessEvents.cs`, `updateModelsToBeAdded.cs`, `EventEngineUtils.cs` and `DoCalcOperationExt.cs` sit beside it (with the `EventEngine.` prefix where the real file has one).
  - The other stock names (`PosObj.cs`, `fldmcf.cs`, `fldchar.cs`, `FF9Snd.cs`, `geo.cs`, `ModelFactory.cs`, `AnimationFactory.cs`, `FieldMapActorController.cs`, `FieldMap.cs`, `EBin.cs`) are each unique in the clone.
- Short prefixes:
  - `test:` is `ff9mapkit/tests/test_harness_netsync.py`;
  - `design:` is `R3-DESIGN.md`;
  - `session.py`, `channel.py`, `fakegame.py`, `battlewire.py`, `coop_peer.py` and `duo.py` are under `tools/harness/`;
  - `test2_N.txt` is under `C:\gd\FFIX\reference\test2\`. The number is the HW index, not the field id: field 250 is test2_67, 307 is test2_87, 768 is test2_210, 2705 is test2_708 and 2950 is test2_221.
- **Oracle** means a value computed offline from the install by the kit's readers. It is never the engine's own published answer.
- **Rig numbers**: 0-7 are the CharacterId rows (Zidane .. Amarant), and 8 is the moogle. Rig 8 is NOT CharacterId 8, which is Cinna.

---

## 1. Verdict

The mechanism is sound and its wire cost is small:
- one additive host section (section 8);
- nothing added to the guest's position frame;
- no change to the harness protocol.

Four findings block the build as written:

1. **s138's leg I has checks that cannot fail** (s138-F1). Three of them pass on the s137 DLL:
   - I6 passes on an absent key, and on field 250's list, which is always empty;
   - I7 compares None with None;
   - I8 passes on the catch literal's sentinel.
2. **Where `dress` lives in `state.json` is undecided** (s138-F6). The action-replay audit deferred it (its 4.1 and 4.3). s138 is the first dress level, so the decision must be made before s138 is built. Section 3.1 makes it: the block nests as `netsync.dress`, and the dress rungs join the one existing ladder.
3. **s139's leg G depends on config nothing reads** (s139-F3). The selftest dress reads the ini's `GhostAs` and a slot mask pinned to 0. No harness key publishes either, so on another machine leg G reads red on a correct engine.
4. **s140's loco mapping breaks a stock frame-wait** (s140-F1). Field 2705 (Pandemonium) loops `while GetEntryAnimFrame(255) < GetAnimDuration(8847) - 1`. B_FRAME still answers with the raw clip's 40 frames, and no dressed walk reaches frame 39. The fix is the B_FRAME timeline law (s140 amendment 1).

**A third owner decision (2026-10-17, after s139): Blank, Marcus, Cinna and Beatrix (CharacterId 8-11) get THEIR OWN MODELS** ("their own models"), not s139's undressed; built in s140 (rig rows from the install's census; ResolveAuto maps 8-11 to them; section 8 carries charId 8-11).

**The two owner questions are ANSWERED (2026-10-17)** (section 2.2, decisions D1 and D2):
- **The SelfDress=0 opt-out: Option A.** The owner: "yes" -- the host's GhostAs stays the one knob for both screens, SelfDress=0 is the guest's local switch, no wire change, B27 rewritten.
- **A spectating guest (GuestSlots=0): the MOOGLE**, overriding the recommendation. The owner: "moogle. 2 zidanes just looks weird, and the host will never be a moogle." s139 amendment 3's first rule changes accordingly.

**What must change first, in order:**
1. Adopt section 3.1's key design in s138's harness commit.
2. Rewrite leg I so that every check can fail, and pin each check with a fake-driven red test (s138 amendments 1-3).
3. Get the owner's answers to the two s139 questions.
4. Give leg G its own mode lever and a baseline reading (s139 amendment 1).
5. Specify the B_FRAME law and its offline census test before any s140 hunk is written (s140 amendment 1).

Everything else is an amendment the builder makes while building the patch it belongs to.

---

## 2. Build briefs

### 2.1 s138: the instrument (inert)

#### Live line map

| Hook site | Design cites | Live today |
|---|---|---|
| The `player` block in PublishState | 3.4.2 (no line) | HarnessAgent.cs:2536-2565 (PublishState :2481-2578). `po` :2538 through Try. x/y/z: NaN → null. dir/floor/tri/listener: -1 with no player. yaw/face: null off a field (:2550-2557). listener :2562. **The block has no block-level try.** |
| `objects[]` | 3.4.2 | AppendObjects :5339-5455, called at :2573. Skips the controlled player :5369. Per-object keys :5379-5439. **Any exception nulls the WHOLE list** (:5449-5452). |
| AppendNetsync and its catch literal | design 5 "HarnessAgent.cs:2961" | AppendNetsync :3293. AppendNetsyncBattle, the last block, :3358. Catch literal :3362: one line, two literals around `NetsyncF3Retired` (const :5266). `battle` is netsync's last key. |
| Unknown-sub-verb refusal literal | old audit 4.3 ":1768" | :1861, ending `|actbench` |
| `netsync bench` named-op parse | design 5 ":1062-1063, :1086" | :1190-1215. An old engine reads an unknown op as `bench 1`. |
| `battle.units[].anim` | old audit 4.6 ":3037" | AppendUnits :3130. `anim` (a clip NAME) :3182. `anim_frame` :3183. |
| `netsync.session.ghost` / `ghost_held` | — | HarnessAgent.cs:3549-3550, read from `NetSyncClient.HarnessGhost` :4929-4930 |
| Try / Num helpers | — | :5551 / :5568-5580 (NaN → null) |
| Host ghost dress | 3.4.3 ":1305" | NetSyncClient.cs:1561-1576: ResolveDress :1562, EnsureGhost :1563, LocoAnim :1566, mask :1570-1574 |
| Selftest mirror dress | 3.4.3 ":1180" | :1423-1440: ResolveDress :1427, EnsureGhost :1430, DriveGhost :1436, mask :1437-1438. Early returns :1350-1359. |
| HarnessSelfTest | 3.4.3 ":3600-3605" | :4669-4705: refuses a live ini :4679-4683; `_role = "selftest"` :4684; `_guestSlots = 0` pin :4685; every-path release block :4695-4705 |
| EnsureGhost / DriveGhost / DespawnGhost | — | :5457-5545 / :5651-5681 / :5683-5716. FallbackGeo :106. `_ghostClip` :111. `_ghostModel` :112, set to the REQUESTED model at :5529. |
| ResolveDress; NameToRig; Rigs | 3.4.3 ":140", ":34-53" | NetSyncVisitor.cs:111-150 (auto :122-134, mask 0 → 0 :124-125; named guard :140). NameToRig :55-59, with no `moogle` key. Rigs :34-53. |
| AnimationFactory's naming rules | 3.4.2 | AddAnimWithAnimatioName AnimationFactory.cs:54-66: `GEO_` + tokens 1-3, no null guard. GetAnimationFolder :45-52: a path-table variant with a latent KeyNotFound. `FolderOf` does not exist yet. |
| SetModel 0x2F | 3.4.1 ":1084-1132" | Unchanged. model :1086, eye :1088, GEO lookup :1091, Garnet hair :1095-1099, character registration :1117-1124 |
| PosObj model default | — | PosObj.cs:16 (65535). updateModelsToBeAdded.cs:19 reads 65535 as "no model". |
| The idle sleep clip | — | CheckSleep EventEngine.cs:534-551: fires when animFrame == frameN - 1 after the idle timer runs out. ResetIdleTimer :527-532: (200 + r) << 2 ticks after EnableMove. Only movement resets it (ProcessEvents.cs:88-89). |
| GetCharAnimFrame; f[7] | — | EventEngineUtils.cs:1836-1843: round(length · frameRate) + 1, or -1 when the clip is not on the GO. EBin.cs:1845-1846 (f[7] = animFrame). |
| TwoWayDictionary | — | Memoria.Prime/Collections/TwoWayDictionary.cs: GetValue (:83-86) is the indexer and throws on a missing key; TryGetValue is :73-75. Both `FF9BattleDB.GEO` and `AnimationDB` are this type. |
| Session.netsync gate and tables | old audit 4.3 "session.py:8583-8608" | session.py:8723-8752: `f33`/`nb` :8727-8728; refusal message :8737-8743; `cap = f33 or nb` :8745; the `after` clause, for nb only, :8749. NETSYNC_SUBVERBS :8360-8363. AUTHORITY :8367-8369. BATTLE :8387-8408. `no_encounters` :8329. |
| fakegame's ladder | old audit 4.1 "fakegame.py:168-191" | Ladder rule :124-125. NETSYNC_BATTLE_CAPS :199-228. S133-S137 sets :239-247. VERB_ORDER :250. NETSYNC_TOP_CAP_KEYS :327. caps_through :439-445. Default caps = every rung (:900). `_objects_doc` :2713-2727. Player :3264-3265. |
| channel accessors | old audit 4.2 | `player_x`.. :499-517. facing_status, THREE CASES, :571-596. objects :527-546. `_ns_prop` :336-344. NETSYNC_BATTLE_ACCESSORS :2589. NETSYNC_TOP_ACCESSORS :2598. |
| Test key laws | old audit ":2046", ":2202" | Prefix law :2080-2086 (`startswith("netsync.battle")` :2085). Ladder test :1990-2077: verb set :2077; top-block order :2075-2076. BATTLE_LEVELS :2250-2257. BATTLE_KEYLESS_LEVELS :2258-2260. Older stand-in :2264, with its sub-verb rewrite list at :2288. Capability accessors :2513-2529. R3_REFUSALS :4531. Reset test :5309. Top-accessors law :6094. |
| The s89 object key set, pinned exactly | — | `ff9mapkit/tests/test_harness.py:5823-5824` |
| Oracle: field 250 | 6.12 legs I and F | test2_67.txt. Zidane_Init :1045-1124: SetModel(98, 93) :1078; 200/25/38/40/41 :1081-1085; SetInactiveAnimation(57) :1086; footsteps :1092-1109; DefinePlayerCharacter :1110. Main_Init runs InitObject(10, 0) alone unless the scenario is 2010 (:55-68). SetRandomBattles(1, 67, ...) :56. Main_Reinit RunScriptAsync(0, 250, 13) :175. Zidane_Loop runs CHRFX 4 every frame (:1152-1157). |
| Oracle: bench 30801 | 6.12 leg I | EVT_TEST30801. Player entry 1: SetModel(98, 93), the same loco, inactive and footstep ids. NPC entries 2-3: SetModel(217 GEO_NPC_F0_CSO, 100). Main_Init: InitObject(1, 0) at [546], before (2, 0)/(3, 0) at [569]/[572]. |

#### Amendments

1. **Every leg-I check must be able to fail (blocking; s138-F1).** On s137, three checks pass:
   - I6 passes when `objects[].model` is absent, and also on an empty list. Field 250's list is always empty:
     - Main_Init runs InitObject(10, 0) alone unless ScenarioCounter == 2010 (test2_67.txt:55-68);
     - the player is skipped (HarnessAgent.cs:5369);
     - the selftest ghost is a raw GameObject, not an Obj.
   - I7 reads None == None.
   - I8 passes on the catch literal's sentinel `[-1, -1, -1, -1]`.

   Rewrite them:
   - **I6** runs on 30801 only. It requires `len(objects) >= 2`, every entry carrying `model`, and both reading 217 (`GEO_NPC_F0_CSO`, the oracle). Only then does it check that none is 98.
   - **I7** requires `netsync.session.ghost` true and non-null values on both sides before it compares. Amendment 9 gives the exact conditions.
   - **I8** runs after the COOPPARTY seed (field 30604, `[party] add = vivi, garnet, steiner`). It asserts `party[0] == 0` and `sorted(x for x in party if x >= 0) == [0, 1, 2, 3]`.
   - Pin each check with a fake-driven unit test that turns it red on an absent key, on an empty list and on a null.

2. **Decide where `dress` lives (blocking; s138-F6).** Section 3.1 decides it: nested as `netsync.dress`, appended after `battle`. `player.*` and `objects[].model` stay outside netsync.

3. **Add a body witness that the dress does not compute (s138-F4, D3; s140-F10).**
   - **Why.** Every value the design proposes (model, geo, anim, anim_geo, eye) derives from `po.model` or `po.anim`. Those are the two fields s140 writes. Suppose s140's hook landed after the GEO lookup (DoEventCode.cs:1091-1093): the keys would read model 192 and geo FRJ while the body is still ZDN, and S1, S2 and X1 would all pass.
   - **New player keys.** Add these:
     - `player.body`: the GEO-id stem of `renderer[0].sharedMaterial.mainTexture.name` on `po.go`. Use `sharedMaterial` so that no material instance is created per publish. The oracle (`models.extract.read_model`): ZDN `98_0` / `98_1`, FRJ `192_0`, MOG `220_0`. External or Moguri textures keep the stem name (ModelFactory.cs:110-112).
     - `player.anim_geo`: the folder of the clip the Animation component is actually playing (an enabled state with weight > 0). Do NOT derive it as `FolderOf(AnimationDB[po.anim])`: that reads back the very field the feature writes.
     - `player.clip_playing`: `animation.IsPlaying(AnimationDB[po.anim])`, looked up through TryGetValue.
   - **Ghost keys.** Publish the same `body` and `playing` on `dress.ghost`.
   - **Verdicts.** Leg I asserts `body == "98"` against the oracle. Every later leg judges the dress on body, anim_geo and clip_playing, not only on model and anim.

4. **Store what the ghost actually wears (s138-F3).** Today a ghost `{geo, rig}` computed at publish time can lie:
   - `_ghostModel` (:5529) is the model the ghost was ASKED to wear. EnsureGhost substitutes `FallbackGeo` (GEO_MAIN_F0_ZDN) when the GEO is missing or fails to load (:5478-5487).
   - The rig is a local variable at both call sites (:1426-1430, :1561-1563).
   - EnsureGhost keeps the OLD ghost while the UI is not FieldHUD (:5463-5471).
   - DriveGhost sets `_ghostClip` even when Play failed (:5672-5680).

   The fix:
   - Add `_ghostGeo` (the string actually passed to CreateModel) and `_ghostRig` (passed in as a parameter). Set both at :5528-5529 and reset both in DespawnGhost (:5711-5715).
   - Read them through static getters beside HarnessGhost (:4929-4930).
   - Publish `dress.ghost{model, geo, clip, rig, playing, body}`.
   - Benches compare the ghost with the player only on FieldHUD.

5. **Shape the block now for s139-s141 (s138-F5, D4).**
   - `dress.ghost` is a fixed sub-object, always published whole, and never null. Its sentinels are model -1, geo/clip/body null, rig -1 and playing false.
   - Key order: `ghost` then `party`. s139 appends `codec` and `rig_idle_frames`, and adds its levers at the end of `ghost`. s140 appends `self`. s141 adds keys only inside `self`.
   - Rig space: -1 for none, 0-7 for the CharacterId rows, 8 for the moogle (from s139). Benches decode rigs through a RIG_NAMES table and never compare `rig == charId` when the value is 8.
   - Publish `player.frame_n`, `player.anim_frame`, `player.clip` (the clip name) and `player.meshflags` now. The player block is then touched once, and s141 adds no player key.

6. **Read safely (s138-F8, D5).**
   - Every new player key goes through Try with TryGetValue. GEO and AnimationDB throw on a missing key (TwoWayDictionary.cs:83-86), and the player block has no block-level try.
   - With no controlled actor, a player key publishes null, following the x/y/z and face precedent. Otherwise it publishes the raw value. Document model 65535 as "no SetModel yet": that is the constructor default (PosObj.cs:16), and the engine itself tests it (updateModelsToBeAdded.cs:19).
   - Inside `dress`, use the house convention: -1 for ids, null for strings.
   - `objects[].model` is a plain field read with no per-object GEO lookup, because one throw nulls the whole list (:5449-5452).
   - `player.*` reads the controlled actor on any map (channel.py:493-497). Box B25 can use that.

7. **`dress.party` reads the same source as ResolveDress (s138-F17).**
   - Publish `party[i] = (Int32)FF9StateSystem.Common.FF9.party.member[i].Index`, or -1 for an empty slot. Publish the raw value: 8-11 are Cinna through Beatrix, 12 and up are custom characters.
   - Never read `NetSyncParty.Slots`. The selftest mirror seats the "BENCH" impostor in slot 0 there (NetSyncParty.cs:384-398, :456-457), which is the s134 lesson.

8. **FolderOf mirrors AddAnimWithAnimatioName (s138-F7).**
   - **The rule.** `"GEO_"` + tokens 1-3. It returns null for a null or empty name, or one with fewer than 4 tokens, and never throws.
   - **Not GetAnimationFolder** (:45-52). That one remaps through `animationPathTable`, and has a latent KeyNotFound because it tests `animationMapping` but indexes `animationPathTable`.
   - **Check.** Every clip of all nine rig rows folds to its own GEO under this rule, checked against the install's tables.
   - **Tests.** Pin a Python twin with a test that uses the C# method's own cases.
   - **Two traps.** Anim 0 is `ANH_MAIN_F0_STN_B`, so never judge `anim_geo` when anim == 0. Ids 200 and 324 share `ANH_MAIN_F0_ZDN_IDLE`, so classify clips by name, not by id.

9. **I7's real conditions (s138-F9).**
   - **What the code does.**
     - The selftest pins `_guestSlots = 0` (:4685), so `ResolveDress("auto")` returns 0 (NetSyncVisitor.cs:122-125). The mirror then wears `me.model` and plays the raw `me.anim` (:1427-1436).
     - A NAMED `GhostAs` dresses the mirror whatever the slots are (:136-143).
     - The ghost needs an in-scope field and `me.fieldMapActor` (:1350-1359).
     - It is driven from a different MonoBehaviour than the publish, so there is one frame of skew. DriveGhost dedupes by clip name (:5670).
   - **An INI row** (the S137-INI precedent). Read `Memoria.ini` read-only. `Enabled` must read 0 or be absent, and `GhostAs` must be one of "", auto, off or 0. Otherwise run nothing and record red.
     - Today the shared ini reads Enabled=1, Role=host, GhostAs=auto, so `netsync selftest 1` is refused (:4679-4683) until the ini changes.
   - **I7** needs the forced selftest role and `netsync.session.ghost` true. It compares only after the player's anim has held for at least 2 publishes:
     - ghost.model == player.model;
     - ghost.geo == player.geo;
     - ghost.rig == -1;
     - ghost.clip == player.clip.

10. **I5 must avoid a battle and the sleep clip (s138-F2).**
    - **The problems.**
      - Field 250 runs random battles (test2_67.txt:55-56), and the forced selftest does not suppress them: `_followHost = false` (:4685) feeds `SuppressEncounters = _followHost` (:1425).
      - CheckSleep plays the inactive clip 57 once the idle timer runs out, and both 250 and 30801 set it.
      - Whether the player walks or runs is Cancel XOR `cfg.move` (FieldMapActorController.cs:732).
    - **The rule.**
      - Call `Session.no_encounters(True)` (session.py:8329) before any walk on 250.
      - While moving, take a sample after N steady frames and accept {25, 38}.
      - Sample rest within a few seconds of releasing the walk, and require 200. Report 57 as "the known sleep clip", never as a pass for 200. Any other id is red.
      - s140's S2 inherits this rule: moving ∈ {2553, 2558}. It never guesses which one the hold produces.

11. **Add I9, a cheap oracle check (s138-F16).** `player.sid == player.uid == 10` on 250 (InitObject(10, 0), test2_67.txt:59, :67), and == 1 on 30801 (instruction [546]).

12. **The fake and the second test file (s138-F10).**
    - The fake's default stand-in carries every rung (fakegame.py:900).
    - `test_harness.py:5823-5824` pins the s89 object key set exactly, and the design's 5.2 re-pin list misses it.
    - Gate the fake's player, objects and dress keys on the `dressinstr` rung, so that `caps_through("acttrance")` publishes none of them (in lockstep with s137).
    - Re-pin `test_harness.py:5823-5824` in the s138 commit.
    - Add fault levers to the fake (a wrong eye, a missing ghost, an empty party, an absent `model`) so every leg-I check can be shown red offline.

13. **`anim` is the id (s138-F11, nit).** `battle.units[].anim` is a clip name (HarnessAgent.cs:3182). `player.anim` stays the id, because the oracle supplies ids. `player.clip` carries the name, matching `dress.ghost.clip`. Document the split in channel.py.

#### Decisions

| # | Question | Recommendation |
|---|---|---|
| D1 | Should `dress` be top-level (as the design says) or `netsync.dress`? | `netsync.dress` (section 3.1). |
| D2 | One ladder or two? | One. The four dress rungs append to NETSYNC_BATTLE_CAPS (section 3.1). |
| D3 | Add a body witness? | Yes (amendment 3). |
| D4 | Add `frame_n`, `anim_frame`, `clip` and `meshflags` now? | Yes (amendment 5). |
| D5 | Which sentinels? | Amendment 6. |
| D6 | Which role and preconditions for leg I? | I1-I6, I8 and I9 run in any role. I7 needs the forced selftest role. Add the INI row (amendment 9), seed COOPPARTY before I8, and call `no_encounters(True)` before walking on 250. |
| D7 | Which id and folder for the bench field? | 30606 in `FF9CustomMap-msgs`, beside the co-op benches 30601-30604. Deploy with `--id 30606 --mod-folder FF9CustomMap-msgs`, relaunch once, and never pin the id. Re-read all seven folders' DictionaryPatch files right before deploying (30606 was free in all of them on 2026-10-17). The field is first needed by s140. |
| D8 | (moved to s141 as D7: the polish lever) | — |
| D9 | How is the twin's InitObject placed before the player's (legs N1/N2)? | Use the kit's gated-`[[npc]]` lane, which already inserts ahead of the player (section 5, s138-F14), behind an always-true gate. Back it with an offline disasm preflight, MAIN_INIT_ORDER, that fails the bench closed. Use no post-build splice and add no kit feature. |

### 2.2 s139: the host rule and section 8

#### Live line map

Rows shared with s138 (ResolveDress, the two dress sites, HarnessSelfTest, EnsureGhost, the gate) are in 2.1.

| Hook site | Design cites | Live today |
|---|---|---|
| Rig struct and rows | 3.4.3 ":34-53" | NetSyncVisitor.cs:34-41: `private struct Rig {Model, Idle, Walk, Run, TurnL, TurnR}`. :43-53: `private static readonly Rig[] Rigs`, 8 rows, unchanged since s37. RigForModel :63-74. ClassifyLoco :78-90. LocoAnim :93-106 (`rigIdx >= Rigs.Length` :95; default case → idle :104). |
| The selftest branch gate | — | NetSyncClient.cs:1323 (`_role != "host" && _role != "client"`). IsSelfTestRole :742-745 (`_enabled && _role == "selftest"`). One-shot proof block :1361-1421 (`_storyProofDone` is never reset). |
| GhostAs | — | LoadConfigIfChanged reads `[Netsync] GhostAs` whatever `Enabled` says (:900, :995, :1012). HarnessSelfTest never writes it. |
| BuildStateFrame (section 8 producer) | 3.4.3 ":1906-1925" | :2984-3003. The section-7 append, inside `if (_role == "host")`, is :2999-3001. Callers: :1509 (the 7 Hz publish), :2969, :3144, :4282. |
| Section codec | 3.4.3 "NetSyncState.cs:113-128", "NetSyncParty.cs:224-245" | Ids NetSyncState.cs:35-44 (0, 4, 5, 6, 7); ids 1-3 are NetSyncParty.cs:43-45; **id 8 is free**. ApplyStoryTo :107-130 (id 0, length 2048 only, :120). AppendSection :137-151 (a null or empty body is a no-op, :140-141). TryReadSection :157-180 (first match :170-176; truncation refused :168-169). SelfTest :227-299. ParseSections NetSyncParty.cs:218-249 (ids 1-3). Neither file has been touched by any patch after s103. |
| EnsureGhost's renderer pass | — | :5457-5545. Re-dress deferred off FieldHUD :5459-5473. AddAnimToGameObject loads the worn folder only (:5494). Every renderer enabled at :5504-5513. That undoes ModelFactory's field-mode hides: the off-hair (ModelFactory.cs:148-169) and battle_model (:189-198). |
| The inactive gate | — | EventEngine.cs:546-550 (`p.sleep == 0` → no break animation) |
| GEO and clip names | — | FF9BattleDB.GEO.cs:176-185 and :462 (220 = GEO_NPC_F0_MOG). FF9DBAll.Animation.cs: 2904 MOG_IDLE :2804, 2927 WALK :7550, 2907 RUN :7544, 2923 TURN_L :7548, 2911 TURN_R :7549. |
| The wire | — | NetSyncSocket.cs: Version 14 :140; MaxPayload 8192 :155; BuildPosPayload, 37 B, :192-207; TryParsePosPayload, which accepts ≥ 37 B, :209-230. The guest's SetLocal :1479-1482. |
| HarnessReleaseBench | design 5 "NetSyncBattle.cs:2547-2575" | NetSyncBattle.cs:5561-5630 |
| The kit's GhostAs names | — | `ff9mapkit/ff9mapkit/coop.py`: GHOST_NAMES :93-94; parse_ghost_as :124-134, which raises on any other name; writes GhostAs :151 |
| The install's ini | — | `Memoria.ini [Netsync]`: Enabled=1, Role=host, GuestSlots=2, GhostAs=auto |

#### Amendments

1. **Leg G gets its own mode lever and a baseline (blocking; s139-F3).**
   - **The problem.** The selftest dress is `ResolveDress(_guestSlots)` (:1427). `_guestSlots` is pinned to 0 (:4685), and the ini's `GhostAs` is never touched. ResolveDress's mode check returns 0 before it looks at any mask when `GhostAs` is "" or off (NetSyncVisitor.cs:116-118), and no harness key publishes `GhostAs`.
   - **The consequence.** With `GhostAs=vivi`, G5 reads Vivi. With `GhostAs` empty, G1-G3 read red on a correct engine. `ff9mapkit coop` rewrites this value (coop.py:151).
   - **The fix.**
     - `selfdress ghost <mask 0-15>|off` (selftest only) replaces `_guestSlots` AND forces mode `auto`, at the selftest call site only. `ghost off` restores the ini's mode.
     - Publish `dress.ghost.mode` as "ini:<value>" or "bench:auto".
     - Add **G0**: read the baseline `dress.ghost.model` and `mode` before any op. G5 compares against that baseline, and against `player.model` only when the ini's mode was off or auto.
     - Release the levers in HarnessReleaseBench (NetSyncBattle.cs:5561) and in HarnessSelfTest(false)'s every-path block (:4695-4705).

2. **The full rig table, from the install (s139-F1, F2, F13, F18; s140-F4; s141-F3, F7).**

   Every existing rig number and the moogle row are correct. They were checked against all 817 exports and the clips in p0data5, and all 45 clips are present. The design names columns it never fills, so fill them now, so that s140 and s141 read one table:

   - **Eye.** The design's values are correct. Census counts: 98→93 (1173 of 1173), 8→61, 185→91, 5489→104, 192→94, 273→92, 443→63, 509→122, 220→50 (209 of 209).
   - **Inactive.** A clip id where **0 means none**. That is the engine's own `p.sleep == 0` test (EventEngine.cs:546), NOT "fall back to idle".
     - Values: Zidane 57, Vivi 912, Garnet 3160, Steiner 119, Freya 0, Quina 0, Eiko 9590, Amarant 0, moogle 0. Freya, Quina, Amarant and the moogle never set one in stock. Zidane's value is moot, because a Zidane dress disarms.
     - s140's ASLEEP and AANIM_EX-5 mapping writes 0 for those rows.
     - RunAnimation maps a BREAK* clip to the dressed idle, never to 0.
     - The kit's `playerswap.CHARACTERS` falls back to the idle here, so it cannot serve as this column's source.
   - **Footfall frames.** Exactly two per walk clip and two per run clip, taken from the RunModelCode(16, clip, frame) census, and each inside its clip's frame count (shown as walk | run):

     | Rig | Walk frames | Run frames |
     |---|---|---|
     | Zidane | 4, 13 | 0, 8 |
     | Vivi | 4, 14 | 0, 9 |
     | Garnet | 4, 15 | 0, 9 |
     | Steiner | 4, 14 | 0, 9 |
     | Freya | 4, 16 | 0, 9 |
     | Quina | none | none |
     | Eiko | 1, 13 | 0, 9 |
     | Amarant | 6, 23 | 10, 21 |
     | moogle | none | none |

     The outliers in the census come from cutscene inits that compute their frames as `n + GetAnimDuration/2`. s141's ordinal mapping stays valid because every row with footfalls has exactly two per clip.
   - **Step-sound override.** Steiner = 925 in both slots (s141 amendment 1). Every other row is 0, meaning keep the source key's id.
   - **Idle alias.** The second id that names the same idle clip (s140 amendment 4):

     | Rig | Idle (slot) | Alias |
     |---|---|---|
     | Zidane | 200 | 324 |
     | Vivi | 148 | 573 |
     | Garnet | 2089 | 2090 |
     | Steiner | 2001 | 2002 |
     | Freya | 2556 | 2557 |
     | Quina | 3228 | 3229 |
     | Eiko | 7503 | 7504 |
     | Amarant | 8307 | 8308 |
     | moogle | 2904 | 2905 |
   - **Hand bones (R_hand, R_hand_end)** for s141's prop remap: Zidane (12, 13), Vivi (16, 17), Garnet (14, 15), Steiner (14, 15), Freya (12, 12), Quina (13, 14), Eiko (14, 15), Amarant (15, 16), moogle (19, 19).
   - **Names.** NameToRig gains `{"moogle", 8}`. Without it, `GhostAs=moogle` returns 0 at :136-138 and never reaches the `< Rigs.Length` guard. The kit's GHOST_NAMES gains "moogle", and its comment is updated, because parse_ghost_as rejects it today (coop.py:131-134).
   - **Visibility.** Make Rig internal, or add an internal `TryGetRig`, so that s140's NetSyncSelfDress needs no visibility change.
   - **Tests.** Today no repo test pins the engine's rig rows. Add two:
     - one that parses the s139 patch's rows and asserts they equal `playerswap.CHARACTERS` (model, eye, idle, walk, run, left, right), with literals for the moogle row and the new columns, citing this census as their source;
     - one asserting that `GHOST_NAMES` equals NameToRig's keys.

3. **ResolveAuto is a pure function, with the moogle rule bounded (s139-F6, F15; s141-F8).**
   - The signature is `ResolveAuto(mask, moogleWhenEmpty, slotChar)`. Its rules, in order:
     1. **OWNER-DECIDED (D2): `mask == 0` → the moogle (220, charId 0xFF) when `moogleWhenEmpty`** -- a spectating guest puppets nobody, and two Zidanes look wrong ("the host will never be a moogle"). Today mask 0 means no dress (NetSyncVisitor.cs:124-125); s139 changes that on purpose. Without `moogleWhenEmpty` (a client role) mask 0 still gives 0.
     2. Otherwise, return the first named slot that holds a main (0-7).
     3. A named slot holding Cinna through Beatrix, or a member of 12 or above, gives 0.
     4. If every named slot is empty, return the moogle (220, charId 0xFF), but only when `moogleWhenEmpty`.
   - The live reader is `party.member[slot]?.Index`, honouring the bench `empty` lever.
   - Write `moogleWhenEmpty = (_role == "host" || IsSelfTestRole)` positively, and evaluate it at call time. The selftest branch runs for any role other than host or client (:1323), so `_role != "client"` would give a typo'd `Role=guest` the moogle.

4. **The guard is a pure function too (s139-F6, F16).**
   - `GhostGuard(dressModel, wireModel)` keeps the dress when the wire body is 98 or already the dress. Otherwise it shows the wire body.
   - When the wire body is already the dress (an s140 guest), play its raw anim instead of the loco translation. Otherwise LocoOther turns into idle (NetSyncVisitor.cs:104), and the guest's gestures and break clips (for example Vivi's 912) show as idle on the host. At :1566, and the same at :1433-1435:
     `animId = (dressModel != 0 && dressModel != rs.Model) ? LocoAnim(dressRig, rs.Loco) : rs.Anim`
   - Fix the guard's comment (amendment 9).

5. **Section 8's producer and meaning (s139-F7).**
   - **When.** On the host, every frame, in the same `if (_role == "host")` block, right after section 7 (:2999-3001).
   - **Body.** `[model u16 LE][charId u8]`, built by one method, `HostDressSection()`, which both BuildStateFrame and the codec proof call.
   - **Values.**
     - no dress → `00 00 FF`;
     - the moogle (empty slots, or named) → `DC 00 FF`;
     - a main → `[model][0..7]`.
     charId is 0xFF (= `CharacterId.NONE`) unless a main is dressed.
   - **Never an empty body.** AppendSection drops one (NetSyncState.cs:140-141), and then "section absent" and "model 0" would look the same. s140 treats those as two distinct disarm reasons.
   - **On the guest.** The guest resolves the rig by MODEL (RigForModel). charId only drives the Zidane disarm.
   - **Headroom.** The frame is about 3.5 KB today; this adds 6 B, against MaxPayload 8192.

6. **The codec proof, fully specified (s139-F6).** As written, the proof could only round-trip its own encoder, so a symmetric byte-order bug would pass. Specify `DressSelfTest`:
   - It logs once, with the proof block: `dress codec selftest: OK (N rows)`.
   - `dress.codec` is null until the proof runs, then "ok" or "fail: <row>".
   - **Hand-checked bytes.** (192, 4) = `C0 00 04`; (220, 0xFF) = `DC 00 FF`; (0, 0xFF) = `00 00 FF`.
   - **Old-guest rows.** Take a real SnapshotAll + section 5 + section 7 frame, with and without section 8 appended. ApplyStoryTo, ParseSections and TryReadSection(7) must give identical results both ways. A truncated section 8 (length < 3) is refused; a length-5 body is accepted, reading its first 3 bytes (forward compatibility).
   - **ResolveAuto rows.**
     - mask 0 → 0;
     - first named slot empty → the next member;
     - all empty, moogle allowed → 220/FF;
     - all empty, moogle not allowed → 0;
     - Cinna (8) → 0;
     - Blank (10) → 0;
     - named moogle → 220/FF;
     - named zidane → 98/0.
   - **Guard rows.** Wire 98, wire = the dress, wire 532, wire 5489.
   - **Mutants that must fail.** Swapped bytes; `>= Rigs.Length` used in place of a `MainRigCount`; the moogle given on the client role.
   - **Python twins** live in battlewire, with the same parameters as the C# methods.

7. **Measure `rig_idle_frames` honestly (s139-F11, D4).**
   - **The problem.** GetCharAnimFrame returns -1 for a clip that is not on the GO (EventEngineUtils.cs:1839-1840), and EnsureGhost loads only the worn model's folder (:5494).
   - **Measuring.** Name the measuring path: either resolve and load each idle clip the AnimationFactory way, or measure per worn rig on the ghost.
   - **G6** asserts equality with the oracle `[60, 45, 30, 60, 50, 40, 30, 45, 72]` (Zidane, Vivi, Garnet, Steiner, Freya, Quina, Eiko, Amarant, moogle). The bench computes it with the kit's reader, which uses the engine's formula. The engine's answer alone is not a verdict.
   - **Note for s140's T1.** Only the short idles (Vivi, Garnet, Freya, Quina, Eiko and Amarant, all below 58 frames) would wedge without KeepSourceTimeline. Zidane, Steiner (60 frames) and the moogle (72) pass regardless. So T1's calibrated red must use a short-idle rig, and "the moogle included" does not discriminate.

8. **Restore exactly what EnsureGhost un-hides (s139-F12, s141-F2, D5).**
   - **The problem.** EnsureGhost enables every renderer (:5504-5513). That undoes ModelFactory's field-mode hides:
     - Garnet's off-scenario hair: her skinned meshes are long_hair, rubber_band, mesh0 and short_hair (ModelFactory.cs:148-169);
     - Amarant's battle_model: his meshes are battle_model, field_model, mesh0 and mesh1 (:189-198).
   - Only ApplyGhostMask restores them, and only when the dress equals the wire model or the local model (:1570-1574). Under the s139 guard, the path that dresses without a mask is exactly B19 (an s117 guest sends 98).
   - **The fix, in s139.** Right after CreateModel and before the force-enable, snapshot each renderer's `enabled` as `_ghostRestMask` (one bit per renderer, at most 16). Apply it whenever neither mask rule applies. This replaces s139-F12's Garnet-only re-apply.
   - **Correction.** Both skeptics corrected the lane: the split shows on B19 and on s139's own bench, not on B20. Add to B19: "Garnet in slot 1 shows one hairstyle; Amarant shows only his field model."

9. **The guard cannot see an opted-out guest (s139-F8; s141-F1).**
   - A SelfDress=0 s140 guest sends model 98. That is exactly what the s117 guest sends, and B19 requires dressing the s117 guest. The guest publishes `local.model` (:1480), and the type-0 frame carries no dress bit.
   - So three statements in the design are false:
     - the guard comment "an opted-out guest: show it as it is";
     - "Both screens then agree in every case";
     - B27's "the host's ghost ALSO shows Zidane".
   - The same split happens on every guest-side non-dress: the gate skip, `ctl_elsewhere` / `skip_second`, an EntryDefinesPlayer miss on a kit field, and a sticky disarm.
   - Owner decision D1 settles which way to fix it.

10. **Box B22 for an s140+ laptop (s139-F9).** After a mid-field party change, the host's ghost does NOT re-dress at menu close:
    - a dressed s140 guest still wears the old member;
    - the guard then sees `rs.Model != 98 && rs.Model != dressModel` and shows the wire body.

    B22 for s140/s141 reads: "the host's ghost keeps the laptop's current body (both screens agree); both change at the laptop's next door; no frozen camera, no NRE." An s117 laptop keeps today's behaviour: its ghost re-dresses at menu close, as in B19.

11. **Calibration levers (s139-F5, D6).**
    - **The gap.** Without a lever s139 has no behavioural red. Its guard's non-98 half also never runs solo, because field 250's selftest peer always reads 98.
    - **Two selftest-only ops**, released with the bench:
      - `selfdress rule s138|s139`. `s138` restores the old rule: the first named bit, no skip, no moogle, no guard.
      - `selfdress wire <model>|off` stands in for the mirror's wire model.
    - Leg G7 runs the guard rows live (section 4.3).

12. **The `empty` lever takes a mask (s139-F17).**
    - Use `selfdress empty <mask 0-15>|off`. A single-slot `empty` can never test "every named slot empty" on a multi-bit mask: an engine that gives the moogle only for single-bit masks passes both G2 and G3. Add G3c.
    - `empty` also feeds s140's self ResolveAuto, because S3 uses it.
    - `ghost` overrides only the dress input, never `NetSyncBattle.GuestSlots`.

13. **Leg G reads identity off the live party (s139-F4).**
    - Field 250's party is whatever the sandbox save holds. The coopparty bench records `[0, 255, 255, 255]` after newgame and warp. `Rigs[party[1]]` is undefined for an empty slot, and for a member of 8 or above.
    - Order of operations (G0 and G3a, which needs an empty slot, run before the seed: section 4.3):
      1. Seed through COOPPARTY (30604).
      2. Derive s1, the first slot ≥ 1 that holds 0-7, and use `ghost 1<<s1`.
      3. If the first named slot holds a member of 8 or above, expect no dress.
      4. If the seed leaves no main, record G1/G2 as NOT REACHED.
    - Expected models come from the Python rig twin pinned to the census, not from the engine's Rigs.
    - Witnesses:
      - `dress.ghost.geo` and `body`, read off the spawned GO;
      - `playing`, from `_ghostAnim.IsPlaying`;
      - a game_snap read for G3 (the moogle on screen).

14. **Prove section 8 on a real wire (s139-F14).**
    - No solo leg runs the host producer: the selftest role has no socket (comment at :622).
    - The codec proof covers only the encoder.
    - A duo leg, G9, puts section 8 on a real wire, judged by a witness the feature does not compute: the relay tap (section 4.3).

#### Decisions

| # | Question | Recommendation |
|---|---|---|
| D1 | **OWNER-DECIDED: Option A** ("yes", 2026-10-17). A guest sets `SelfDress=0` on its own machine. Should the host's ghost of it also turn back to Zidane, as box B27 says? As designed this cannot work: on the wire, an opted-out guest looks identical to an old guest. | **Option A (recommended): no, and rewrite B27.** Under Q8, the HOST's GhostAs is the one knob for both screens; SelfDress=0 is the guest's local escape hatch. B27 becomes: "the laptop stays Zidane; the host's ghost keeps the slot member (empty the host's GhostAs to make both Zidane)". Reword 3.4.3 to "both screens agree whenever the guest dresses or wears a non-Zidane body", and list the guest-side skips (amendment 9) as known disagreements in risk 11. No wire change. **Option B:** a 38th byte on the type-0 position frame (old parsers already ignore bytes past 37: NetSyncSocket.cs:209-230, coop_peer.py:161). bit0 = self-dress capable (s140+), bit1 = dressed now. The parser and the guard change in s139 (`if (rs.DressCapable) dressModel = 0`: a new guest's wire body is authoritative, and only a guest without the byte is dressed by ResolveAuto). The writer lands in s140. It works, but it is new wire surface (NetSyncSocket, NetSyncRelay, coop_peer) for a diagnostic knob. |
| D2 | **OWNER-DECIDED: the MOOGLE** (2026-10-17: "moogle. 2 zidanes just looks weird, and the host will never be a moogle."; the row's recommendation below was overridden). A spectating guest (the host's GuestSlots = 0, box B0) puppets nobody. Should it stay Zidane, as today, or show the moogle like a guest whose named slot is empty? | (overridden) Stay Zidane: keep `mask == 0 → 0` (amendment 3). GuestSlots 0 is the spectate mode, and "a moogle if 1-person party" describes a named slot with no member. Control row G3d. |
| D3 | What does the Inactive column mean for rigs with no stock break animation? | 0 = none (amendment 2). |
| D4 | Keep `rig_idle_frames` as an engine-measured key? | Keep it, with the measuring path named, judged against the oracle (amendment 7). |
| D5 | Fold the Garnet hair fix into s139? | Yes, generalised as the rest mask (amendment 8). |
| D6 | Add the levers and a duo leg? | Yes (amendments 11 and 14). |
| D7 | Where do the dress harness levels live? | Section 3.1. |

### 2.3 s140: the guest dresses itself

#### Live line map

| Hook site | Design cites | Live today |
|---|---|---|
| ArmFromState site | 3.4.4 "NetSyncClient.cs:555" | :678, the `NetSyncState.ApplyStory` success branch (`_storyMirroring = true` :682) inside ApplyStoryImpl :647-687. Skip returns: transport :657-666; no host snapshot :669-677; apply failed :685-686. |
| ApplyStoryBeforeEvents | 3.4.4 ":500"; 3.4.1 ":524-565" | :623-635: DIO-1 `BeforeFieldEvents` :625, then ApplyStoryImpl :633. A selftest returns at :657-666 because it has no socket. Called from HonoluluFieldMain.cs:148, before StartEvents :149 (unchanged). |
| Exit ramp fire | 3.4.4 ":1074" (that line is now ResetSessionGrace, inside ApplyConfigChange) | :1254-1271: `_storyMirroring = false` :1262; NetSyncParty.Clear :1267; OwnSaveReloadInFlight :1268; ExitMirrorToOwnSave :1270 |
| ApplyConfigChange / ApplyBehaviorChange | 3.4.4 | :1040-1078 / :1088-1103. Behaviour keys are hashed into bsig at :980-1010 (the ActionReplay precedent is :928-931, :1010). |
| OnDestroy | 3.4.4 ":1394" | :1675-1692 |
| Role predicates | 3.4.4 `IsClientOrSelfTestRole` | IsSelfTestRole :742-745. **IsClientOrSelfTestRole does not exist.** |
| The guest publishes its body | — | :1480-1481 (`SetLocal(fld, local.anim, local.model, ..., ClassifyLoco(...))`) |
| SetModel hook | 3.4.4 "after DoEventCode.cs:1088" | DoEventCode.cs:1084-1133: po.model :1086; eye :1088; GEO :1091; CreateModel :1093; Garnet hair :1095-1099. A second SetModel on a registered uid returns at :1117-1118, before AddFieldChar. Registration :1119-1124. |
| DefinePlayerCharacter (NoteControl) | 3.4.4 ":1043" | :1033-1045 (controlUID :1043). StartEvents zeroes controlUID at EventEngine.cs:629. |
| Loco setters | 3.4.4 "AIDLE (:1134-1176)" | AIDLE :1134-1178; AWALK :1179-1184 (the raw AddAnim :1182); ARUN :1185-1190; ASLEEP :1662-1667; ATURNL :1951-1956; ATURNR :1957-1962; AJUMP :2086-2093; AANIM_EX :3209-3226 (case 5 = sleep, :3221) |
| RunAnimation / RunAnimationEx | 3.4.4 diff; ":1372-1383" | :1314-1389: raw id :1319; jump-rope fixes :1321-1334; raw AddAnim :1335; 800 inFrame :1338; ExecAnim :1340; field checks 307/561/1601/1605 :1341-1371; the 2934 trigger :1372-1384; gMode 3 :1386-1387 |
| Jump execution | — | JUMP3 :2094-2107; PREJUMP :2108-2115; POSTJUMP :2116-2124; SETVY3 :2948-2971 |
| B_FRAME (GetAnimDuration) | 8 risk 5 ":25" | DoCalcOperationExt.cs:24-26, `GetCharAnimFrame(this.gCur.go, id)` |
| ExecAnim; char band | 3.4.4 "sid >= sSourceObjN - 9" | EventEngine.cs:1403-1418 (frameN :1414). Band at :653, :864, :933. |
| ProcessAnime | 3.4.4 ":85-109" | Parent branch (the chocobo rider) :45-82. Forward cap :83-99. Reverse :100-103. AnimStop :174-191. SetAnim :193-202 (returns early on an equal id, :195). DefaultAnim :204-210. |
| Movement SetAnim | — | ProcessEvents.cs:277-288 |
| Presentation of event anims | 3.4.4 "FieldMapActorController.cs:418, :426" | PlayAnimationViaEventScript :405-431 |
| Warm-return rebuild | 3.4.1 ":21-28" | updateModelsToBeAdded.cs:21-28. CreateModel :25. ReassignBasicAnimationForField :27 → :143-157, which re-attaches idle/walk/run/turnl/turnr only. |
| Clip attach | — | AnimationFactory.cs: LoadAnimationUseInEvent :8-42; AddAnimWithAnimatioName :54-66 (NREs on a null name at :59); AddAnimToGameObject :68-83. ModelFactory.CreateModel attaches only its OWN per-field EventAnimation list (:171). |
| PosObj.copy | 3.4.4 "PosObj.cs:72-73" | PosObj.cs:37-93 (garnet/shortHair :72-73). Obj.copy nulls `go` and calls PosObj.copy (Obj.cs:417-423), and deep-copies ebData (:377-385). |
| The BinaryScript parser | 3.4.4 "ends at 0x111" | EventEngineUtils.cs:1920-1956. Entry :1996-2029, where funcPos is entry-relative (:2018-2027). opArgCount :2121-2140 (274 entries = 0x000-0x111). Custom ops 0x112-0x11E: EBin.cs:2412-2424. |
| `allObjsEBData` | 3.4.4 | Public (EventEngine.cs:72), reallocated on every StartEvents (:603-614). The csproj targets v3.5 (Assembly-CSharp.csproj:13), so there is no ConditionalWeakTable. |
| EffectiveFieldId | 3.4.4 | Memoria/Configuration/DataPatchers.cs:47 |
| Stock frame-wait proofs | 3.4.4 "test2_87.txt:1468-1562" | Field 307 (test2_87.txt): RunAnimation 2597 KICK_STEINER_1, then `< 26` (:1468-1470); `< 37` after 2615 (:1478); RunAnimation 2572 COLD_FAINT_1, then `< 45` and `< 58` (:1557-1562). Field 2705 (test2_708.txt): SetWalkAnimation(8847 FRA_WALK) and SetStandAnimation(7922 FRA_IDLE) at :1245-1246; Zidane_25 loops `while GetEntryAnimFrame(255) < GetAnimDuration(8847) - 1` (:1264), and Zidane_27/29 do the same. |

#### Amendments

1. **One timeline law, with a B_FRAME hook (blocking; s140-F1, D1, D5).**
   - **The cause.** Stock AWALK keeps attaching the RAW clip (:1182). So B_FRAME (`GetCharAnimFrame(gCur.go, id)`, DoCalcOperationExt.cs:24-26) answers with the raw clip's length, while the walk slot plays the dressed clip at its native length.
   - **Field 2705.** Pandemonium, the Mind Control scene: story-critical, and inside the Zidane entry that has CC.
     - The script sets SetWalkAnimation(8847 FRA_WALK), then loops `while (GetEntryAnimFrame(255) < GetAnimDuration(8847) - 1) { InitWalk; MakeAnimationLoop(1); Walk }` (test2_708.txt:1264; again in Zidane_27/29).
     - FRA_WALK is 40 frames, so the bound is 39.
     - The dressed walks are FRJ 24, VIV/GRN/STN 20, KUI 26, EIK 24, SLM 32 and MOG 16 frames, and animFrame is capped at frameN - 1 (ProcessAnime.cs:83-99). None can reach 39.
   - **Scope.** Both skeptics upheld the defect but called "softlocks on every rig" overstated. Leg T3 measures which rigs actually wedge.
   - **The census.** All 817 exports were checked, covering the `<`, `==` and duration forms, self (255) and conductor-to-player uid targets. This is the only stock frame-threshold wait on a loco family in a player entry. The other 15 player threshold waits all follow gesture RunAnimations, which KeepSourceTimeline covers.
   - **The law.** On a dressed body, B_FRAME(id) equals the frame count of the timeline that id actually runs on:
     - **Loco families** (IDLE, WALK, RUN, TURN_L, TURN_R and BREAK1_*, per amendment 3's table) run native. This holds in the slots and also when RunAnimation plays a loco-family id: KeepSourceTimeline does NOT apply to them.
     - **Gesture families** keep the source timeline, as designed.
     - **The hook**, at DoCalcOperationExt.cs:25: if `gCur` is a PosObj with `netSelfDress != 0` and `id` belongs to a loco family, return `GetCharAnimFrame(go, MapAnim(id))`; otherwise run stock. Count each remap in `dress.self.bframe_remaps`.
   - **Native, not stretched (D5).** Stretching loco clips onto Zidane's timeline would give Amarant 1.6x walk legs and a 0.55x moogle run on every step.
   - **An offline oracle test.** For every stock GetAnimDuration / GetEntryAnimFrame threshold site in a 98+CC entry, evaluate the bound against every rig's frame counts read from p0data5, and assert that each bound is reachable.
   - **Fallback.** If review rejects the hook, add 2705 (via EffectiveFieldId) to the excluded fields.

2. **Attach the source list and the full rig set, and store the loco ids (s140-F2; s141-F5).**
   - **Two attach gaps.**
     - A stock Zidane body is created with every Zidane clip that field's events use already attached. ModelFactory.cs:171 reads `animationMapping[ownName]` from the field's EventAnimation list (AnimationFactory.cs:8-42, :68-83). A dressed body gets only the WORN model's list, which is usually empty: 2705 lists 12 ZDN clips and no FRJ, 504 lists 18, and 307 lists 24.
     - So before a clip's first RunAnimation, `GetAnimDuration(raw)` returns -1 on the dressed body. Census of the cases:
       - field 1205 runs `SetAnimationInOut(GetAnimDuration(2719) - 1, 0)`, which becomes inFrame 254: an 8 s reverse stall under WaitAnimation;
       - fields 1602 and 400 run `set VAR = GetAnimDuration(186/185)`, which reads 255;
       - field 403's Pot_3;
       - footstep frames in 1464, 1554 and 2802.
   - **A warm-return gap.** After a warm return, ReassignBasicAnimationForField re-attaches only idle/walk/run/turns (updateModelsToBeAdded.cs:143-157). CheckSleep then ExecAnims an unattached sleep clip: frameN becomes 255 and the body freezes for about 8.5 s.
   - **The fix.**
     - Add `NetSyncSelfDress.AttachDress(PosObj)`. It first runs `AnimationFactory.AddAnimToGameObject(go, "GEO_MAIN_F0_ZDN")`: the SOURCE list, so every B_FRAME and KeepSourceTimeline answer equals stock. It then attaches the body rig's full set: idle, walk, run, turns, inactive, the jump target and the idle alias.
     - Call it from two sites:
       - (a) after DoEventCode.cs:1093, inside `if (po.go != null)` and before AddFieldChar, when `netSelfDress != 0`;
       - (b) in updateModelsToBeAdded.cs after :27, when `netSelfDress != 0`.
     - STORE the mapped loco ids in `actor.idle/walk/run/turnl/turnr`; do not just attach them. ReassignBasicAnimationForField re-attaches from those fields, so attaching without storing breaks the warm return.
     - Publish `dress.self.src_attached` (the clip count).
     - Extend W1 (section 4.4).

3. **An explicit loco-class table instead of a suffix rule (s140-F3, D4).**
   - **Why.** "Classified by name suffix" is ambiguous: BREAK1_FLEX does not end in BREAK. It is also wrong for qualified families.
     - The sharpest case is the mounted chocobo rider. CHO_WALK and CHO_RUN end in WALK and RUN, so a dressed rider walks or runs in mid-air.
     - Field 2950's Zidane_29 runs SetStandAnimation(12750 CHO_RIDE_2), SetWalkAnimation(12782 CHO_WALK) and SetRunAnimation(12778 CHO_RUN).
     - ProcessAnime.cs:45-77 drives the rider from the chocobo parent in 2950-2955.
   - **Build it offline.** Generate the table from FF9DBAll.Animation.cs, which has 401 distinct ZDN names, and pin it with a pytest. Its rows:
     - exact IDLE, STAND, WALK, RUN, TURN_L, TURN_R → the rig's slot;
     - on-foot qualified variants (COLD_, SWORD_, FRA_ except WALK_1 and WALK_3, MBG_, POT_, TKE_) → the same slot;
     - BREAK1_* → the rig's inactive clip. Where the rig has none (0), the ASLEEP / AANIM_EX-5 slot gets 0, and a RunAnimation plays the idle alias;
     - CHO_*, GRG_*, the SIT_ / CAMP_ / TENJYOU_ idles and everything else → the rig's idle alias. A dressed rider stands (D4).
   - **Classify by NAME,** because ids 200 and 324 share one name.
   - **The engine copy** is a static name → class map. A SelfTest row asserts a sampled set, including CHO_WALK → idle and FRA_WALK → walk.

4. **A gesture falls back to the idle's ALIAS id (s140-F4).**
   - **The bug.** A gesture mapped to the dressed idle carries the same numeric id as `actor.idle`. When the gesture ends, DefaultAnim calls SetAnim(idle), which returns early on `anim == p.anim` (ProcessAnime.cs:195). frameN then keeps the stretched SOURCE value. The idle plays stretched, and CheckSleep (which fires at animFrame == frameN - 1) fires on the wrong frame, until the next movement.
   - **Example.** RunAnimation(186 BREAK1_LOOK, 70 frames) maps to 2556 (the FRJ idle, 50 frames). After the gesture, frameN stays 70.
   - **The fix.** MapAnim's gesture-to-idle fallback returns the rig idle's alias id (s139 amendment 2), never the slot id. This is the only path where KeepSourceTimeline applies. DefaultAnim's SetAnim(idle) then sees a different id and recomputes frameN.
   - **Host side.** Nothing to do: ClassifyLoco(192, 2557) = LocoOther, and the dressed ghost plays its idle.
   - **X1** compares the clip NAME (`ANH_MAIN_F0_FRJ_IDLE`), not the id 2556.

5. **Key every map on the BODY's rig (s140-F6, F14).**
   - **Why.**
     - ArmFromState re-runs at every field load, warm returns included (ApplyStoryBeforeEvents → BeforeFieldEvents, :625).
     - A warm body comes back from its copy wearing the OLD rig. PosObj.cs:56-57 restores it through Obj.cs:419-423, and updateModelsToBeAdded.cs:25 rebuilds it without going through SetModel.
     - A host party change between the field load and the battle re-arms with a different WantRig. A MapAnim keyed on WantRig would then feed Vivi ids to a Freya body.
     - After Clear(), a WantRig-keyed MapAnim throws, and every anim collapses to the idle.
   - **The rule.**
     - MapAnim(actor, id) and every setter, RunAnimation, B_FRAME and attach hook resolve the rig as `Rigs[actor.netSelfDress - 1]`.
     - The arm statics (Armed, WantRig, WantModel) are read ONLY by AtSetModel's fresh-dress branch.
     - Publish `dress.self.rig` from the controlled body, and add `dress.self.want_rig` for the arm.
     - A SelfTest row: dress as rig A, re-arm to rig B, and MapAnim(25) must still return A's walk.
   - **AtSetModel's first branch** (the body is already dressed at SetModel) is unreachable in stock. A second SetModel on a live object creates a new go and returns at :1117-1118, before AddFieldChar. Warm returns rebuild in updateModelsToBeAdded, not SetModel.
     - Keep the branch as a defence, with the rig resolved from the body, and do not count it as coverage.
     - When it drops the dress, also clear `po.garnet` / `shortHair` if the new GEO is not in `garnetShortHairTable`. Stock SetModel only ever sets them (:1095-1099).

6. **The knob and the exclusion are not arm states (s140-F7).** Listed as arm states, they break the sticky rule both ways:
   - SelfDress=0 set live, followed by a field load whose apply is skipped (a blip), keeps the old arm and dresses anyway.
   - An excluded field (70, 3000-3012) disarms, so a blip on the NEXT field loses the dress the sticky rule promised to keep.

   The rule:
   - `Armed => _arm && Knob`, with Knob read live from the static that the bsig reload writes (as ActionReplay does at :1010).
   - ArmFromState records the host's section 8 whatever the current field is.
   - `ExcludedField()` (via EffectiveFieldId) is a skip at SetModel time, inside AtSetModel. It publishes `dress.self.why = "excluded"` and never touches the arm.
   - Neither the knob nor an exclusion undresses a live body (the teardown law), so B27 reads "at the next cold load".

7. **Disarm at the right moments (s141-F10; s140-F18).**
   - **Clear sites.** Clear() runs at the ramp FIRE, at :1269, right before ExitMirrorToOwnSave (:1270). It also runs in OnDestroy (:1675) and in ApplyConfigChange (:1040). The design's ":1074" no longer names a site. ExitRampSettleMaxMs allows up to 10 s between the ramp's arm and its fire.
   - **Not mirroring.** A skipped apply while `!_storyMirroring` disarms, with the reason "not mirroring". The autoload's own SetModel(98) is then never dressed (B26).
   - **Malformed section 8.**
     - The reason "section8_len" when the body is shorter than 3 bytes. A longer body reads its first 3 bytes, which is the forward rule in s139's codec row (s140-F18's `!= 3` is relaxed to `< 3`).
     - The reason "charid" when charId is outside 0-7 and is not 0xFF. charId 0 keeps the design's own Zidane reason.

8. **Make the named pieces buildable (s140-F13; s141-F9).**
   - **The role predicate.** Add `internal static Boolean IsClientOrSelfTestRole => _enabled && (_role == "client" || _role == "selftest")`. It reads `_role` live; HarnessSelfTest writes `_role` directly at :4684.
   - **The EntryDefinesPlayer cache.** Hold it in an `SByte[]` sized sSourceObjN (-1 unknown, 0, 1). The array is owned by the current `ee.allObjsEBData` reference and reset when `!ReferenceEquals(ee.allObjsEBData, _owner)`.
     - Never key it on `obj.ebData` or on a per-entry array. `allObjsEBData` is rebuilt on every StartEvents (EventEngine.cs:603-614), and Obj.copy deep-copies ebData (Obj.cs:377-385). A reference-keyed dictionary would therefore pin every visited field's arrays for the whole session, and .NET 3.5 has no ConditionalWeakTable.
     - The parse is cheap: once per model-98 entry per load.
   - **The parse.** Parse the entry's slice with `new BinaryScript.Entry(raw, ref pos = 0, sid, 0, 0, (UInt32)raw.Length)`. This works because funcPos is entry-relative (EventEngineUtils.cs:2018-2027).
   - **Observability.** Publish `dress.self.parse_fallback`: the count of character-band answers given after the parser threw on ops 0x112-0x11E (the kit emits 0x115 and 0x116).

9. **Hooks never throw into the VM (s140-F16).**
   - AddAnimWithAnimatioName throws a NullReferenceException on a null name (AnimationFactory.cs:59), and the setter and RunAnimation cases have no try around them.
   - Make each stock-site hook ONE call into NetSyncSelfDress (for example `MapAndAttach(actor, raw)`, returning the id to play) that catches internally and counts `dress.self.faults`.
   - On a fault it returns the rig's idle alias on a dressed body, and the raw id otherwise.

10. **Ladders and jumps get the idle in s140 (s140-F11, D2).**
    - About 100 stock fields climb ladders through AJUMP's frame windows (ZDN LADDER_* appears in about 96-101 fields each, JUMP_1-3 in about 30-66).
    - The idle fallback is frame-safe. The largest ZDN jump1 is 24, below the shortest rig idle (30), so PREJUMP, POSTJUMP and SETVY3 (DoEventCode.cs:2108-2124, :2948-2971) never end a jump early.
    - The cost: the dressed body glides in its idle pose on every ladder. The twin-clip row moves to s141 (s141 amendment 7).

11. **Add N3 for `skip_second`, and restate N2 (s140-F9, D3).**
    - **Why `skip_second` almost never fires on a cold load.** StartEvents zeroes controlUID (EventEngine.cs:629), and stock CC follows SetModel inside the same Init (field 250: SetModel :1078, CC :1110). So GetControlChar() is null at every model-98 SetModel until the dressed body's own CC has run.
    - **Census over the 675 fields with a model-98 entry:**
      - none has two SetModel(98)+CC entries;
      - 510 have one 98+CC entry and no other Init CC;
      - 165 have a 98 entry with CC in its Init plus another, non-98 entry with CC in its Init (for example 357, 358, 455-457, 500);
      - 21 have a 98 entry without CC.
    - **Legs.**
      - Add N3 (section 4.4). Without it, drop the counter: it would be a check that cannot fail.
      - Restate N2 (gate 0): the twin AND the player are both dressed, because control is null at both SetModels.
    - **The 165 multi-binder fields** are accepted for v1 (D3). Count `ctl_elsewhere` with the field id in the dress line, so sitting B can sample them.

12. **Judge on witnesses (s140-F10).**
    - S2, X1 and W1 assert on s138's live `anim_geo`, `body` and `clip_playing`, not on `actor.anim`.
    - Leg T and the B_FRAME oracle judge against offline frame counts from p0data5. The engine's `rig_idle_frames` is only a cross-check.

      | Rig | Idle | Walk | Run | TurnL | TurnR |
      |---|---|---|---|---|---|
      | ZDN | 60 | 20 | 18 | 20 | 20 |
      | FRJ | 50 | 24 | 18 | 20 | 20 |
      | VIV | 45 | 20 | 18 | 20 | 20 |
      | GRN | 30 | 20 | 18 | 20 | 20 |
      | STN | 60 | 20 | 18 | 20 | 20 |
      | KUI | 40 | 26 | 22 | 20 | 20 |
      | EIK | 30 | 24 | 20 | 20 | 20 |
      | SLM | 45 | 32 | 24 | 20 | 20 |
      | MOG | 72 | 16 | 10 | 20 | 20 |
    - Sample S2's rest before the idle timer runs out (s138 amendment 10), or accept the rig's inactive clip.

13. **Confirmations to record in 3.4.1 (s140-F19, nit).** These stop the review re-deriving them:
    - No other stock path keys the player's model or sizes it by model.
    - The only model-equality case a dressed body can match is ProcessTurn.cs:18/:35: field 2855, scenario 9370, model 273 = Quina, an angle normalisation. It is benign; add it to risk 11. Every other `.model ==` site keys NPC models, and no stock code keys 98 or 220.
    - Collision comes from RADIUS 0x4B (DoEventCode.cs:1498-1537) and from AddFieldChar's radius = bgiRad · 4 (FieldMap.cs:571), never from the model.
    - The camera reads neither model nor eye. Eye feeds BubbleMappingInfo.cs:11, ETb.cs:343 and ProcessNeck.cs:72/:198 only, and neck rows exist for all nine models.
    - SetModel (:1086) is the only field op that writes `po.model`. CharacterBuilder (EventEngine.cs:776-781) is disabled.
    - The opening fields 50-69 are never dressed: their slots hold Blank, Marcus and Cinna, so ResolveAuto returns 0.

14. **Fix the citations (s140-F12, nit).**
    - The 307 proof's pairing is wrong. `< 58` (:1562) follows RunAnimation(2572) COLD_FAINT_1 (70 frames, :1557), not 2597. 2597 KICK_STEINER_1 (40 frames) pairs with `< 26` (:1469), and 2615 (60 frames) pairs with `< 37` (:1478).
    - Re-cite the NetSyncClient lines as in the line map.

#### Decisions

| # | Question | Recommendation |
|---|---|---|
| D1 | How is field 2705's frame-wait closed: the general B_FRAME law, or excluding 2705 by EffectiveFieldId? | The B_FRAME law, pinned by the offline census test and leg T3 (amendment 1). It fixes the whole class, kit and fork content included, with one cheap gated hook. Keep the 2705 exclusion as the fallback. |
| D2 | Ladders and jumps: same-suffix twin clips, or the plain dressed idle in v1? | The idle in s140, which is frame-safe; the twin row in s141 (amendment 10). |
| D3 | 165 stock fields can bind control to a non-Zidane entry while a Zidane NPC is dressed. Accept for v1? | Accept (risk 11). Skipping those fields would drop the dress from common Zidane-led scenes such as Dali 357/358, the narrative-state hub lane. Count `ctl_elsewhere` with the field id. |
| D4 | How does the chocobo rider present when dressed? | Every CHO_* clip maps to the rig's idle alias: a standing rider (amendment 3). No exclusion is needed. |
| D5 | Should loco clips run native or be stretched onto Zidane's timeline? | Native, plus the B_FRAME law (amendment 1). |
| D6 | A presentation backstop in PlayAnimationViaEventScript for unhooked raw-clip paths? | No. Its only stock path, the field-768 hotfix, is unreachable on a dressed body (section 5, s140-F5). s138's live `anim_geo` shows any unhooked raw path in the benches. |
| D7 | Where do the dress keys live in the harness ladder? | Section 3.1. |

### 2.4 s141: polish

#### Live line map

| Hook site | Design cites | Live today |
|---|---|---|
| fldmcf row lookup (lighting and blob shadow) | 3.4.5 "fldmcf.cs:81" | fldmcf.cs:81 is the actor's row. Default row :70. clr :91-98. shadowI/shadowR :120-129. Recompute gate :84. Called from FieldMap.cs:355, before the sound service (:361) and ff9fieldCharEffectService (:363), which writes `_Color` (fldchar.cs:217-235). The file is pristine in the clone (BOM + CRLF). |
| The ghost's lighting fallback | 3.4.5 "NetSyncClient.cs:~4366" | :5547-5620: ServiceGhostLighting :5559-5566; ApplyGhostLighting :5568; the ghost's row :5577; the LOCAL player's row :5583-5584; the default row :5585-5586 |
| MESHSHOW / MESHHIDE | 3.4.5 ":1270-1284" | DoEventCode.cs:1270-1276 / :1278-1284. PosObj.geoMeshShow/Hide (PosObj.cs:95-103), applied per frame by mesh name (ProcessEvents.cs:520-560 → PosObj.cs:119-163). |
| CHRFX 16-19 (footsteps) | 3.4.5 ":2010-2014" | DoEventCode.cs:1998-2015 (dispatch :2013-2014 → fldchar.cs:20). Codes 16-19 at fldchar.cs:123-149: 16, 17 and 18 CREATE a record when none exists (:129-131); 19 calls DeleteChar. FF9Snd.cs: GetChar :1259; NewChar :1275; DeleteChar :1299-1323, which indexes `charSoundArray[charSoundUse - 1]` at :1305; per-frame match :1343. |
| ATTACH 0x4C | 3.4.5 "log only" | DoEventCode.cs:1538-1586 (field 62/3010 bone override :1555-1556; geo.geoAttach :1557). geo.cs:111-135 (bone by name; stores attachTargetBoneIndex at :130). Warm-return reattach: FieldMap.cs:530-537. |
| PosObj.copy | 3.4.1 | PosObj.cs:37-93 (meshflags :71; garnet/shortHair :72-73; attach target :74-75). Actor.copy Actor.cs:39 (idle/walk/run :45-47). |
| Save containment | B26 | JsonParser.cs:40, :236 (FF9 globals and EventState only). EBin getvobj :1776-1853 has no model field. Autosave gate EventEngine.cs:693-694; manual save gate SaveLoadUI.cs:154. |
| DLL-free model remap (stock Memoria) | — | DataPatchers.cs:626-670: DictionaryPatch `3DModel <id> <GEO>` and `3DModelAnimation` |
| Stack replay diag set | 4, hygiene rows | `tools/memoria_stack_replay.py` DEFAULT_FILES :61-99. It has NetSyncVisitor.cs. It lacks fldmcf.cs, DoEventCode.cs, PosObj.cs, updateModelsToBeAdded.cs, FF9Snd.cs and geo.cs. |
| Install oracles | 6.12 F1-F4 | MapConfigData of all 818 fields via `mapconfig.parse`: every one has a 0xFFFF row, and 344 lack a 98 row. Field 250 = EVT_EFOREST1_EF_ENT_0. Footstep, attach and mesh censuses over test2 (first language block, 817 scripts). Rig skeletons via `models.bone_labels.read_skeleton` / `labels_for`. |

#### Amendments

1. **A dressed Steiner steps in his armour (s141-F3, D4).**
   - **Stock data.** Steiner's walk 1996 and run 2005 keys use sound 925 in every registration (296 and 294), in both CHRFX 16 and 17. In the 59 fields where Zidane and Steiner both register steps, Steiner shares Zidane's ids in none. Garnet (70/70), Vivi (79/79), Freya (40/40), Eiko (47/47) and Amarant (10/10) use Zidane's exact per-field ids.
   - **The fix.** Use the rig row's step-sound override (s139 amendment 2): 925 in both slots for Steiner. Every other rig keeps the source key's Arg4.
   - **Bench.** Leg F gains F7 (section 4.5).

2. **MapFootstep's rule (s141-F4).** It applies when `po.netSelfDress != 0` and the code is 16-19:
   - anim 25 maps to the rig's walk, and 38 to its run;
   - frame ordinal 0 or 1 within Zidane's pair ({4, 13} for walk, {0, 8} for run, the only frames stock uses, in 1029 functions) maps to the same ordinal in the rig's pair;
   - codes 16, 17, 18 and 19 map identically. 17 and 18 then find 16's record (they CREATE one if none exists, fldchar.cs:129-131), and 19 deletes the mapped record;
   - for a rig with no footfalls (the moogle, Quina), **drop 16, 17, 18 AND 19**, and count the drops. Both skeptics rejected the lane's "19 is harmless", and the live code shows why: stock DeleteChar indexes `charSoundArray[charSoundUse - 1]` (FF9Snd.cs:1305), which throws on an empty table. On a match it only shrinks the table from the top;
   - any other anim or frame passes through unmapped, counted as `steps_passed`.

   Two more points:
   - The table lives in the s139 rig rows; it is also the oracle for F1 and F3.
   - The warm-return re-registration needs PosObj.copy to carry `netSelfDress` (s140). Field 250's Main_Reinit runs RunScriptAsync(0, 250, 13) (test2_67.txt:175).

3. **A witness for footsteps (s141-F5; s138-F15).**
   - **Why.** `steps` is the engine's own sound table, i.e. exactly what MapFootstep wrote. Nothing in it proves that the dressed clip's animFrame ever reaches a mapped frame.
   - **New counters.** `dress.self.steps_fired` is counted in FF9Snd's match branch (:1343), only when the record's uid is the controlled uid and `netSelfDress != 0`. `steps_fired_player` counts the same for the F3 control.
   - **Count per field load.** Make `steps` and `steps_dropped` per field load, or run F1-F3 on a fresh load. Field 250's warm return re-registers the 12 footstep ops (Zidane_13, test2_67.txt:1126-1147), so a cumulative count reads 24 after one return.
   - **Leave other codes alone.** Do not map non-footstep CHRFX codes on the dressed body; count them for the log only. Zidane_Loop runs CHRFX 4 (Slice) every frame (:1152-1157), and dispatch is by uid (DoEventCode.cs:2014).
   - **Confirmed in stock.** The F1 and F3 frame sets: Freya 2553 at {4, 16} and 2558 at {0, 9} (in 54 and 44 fields); Zidane 25 at {4, 13} and 38 at {0, 8}.
   - **Benches.** F1b and F6 (section 4.5).

4. **Judge the lighting colour against the install (s141-F6, D6; s140-F15; s141-F13 nit).**
   - **Field 250's rows differ.** That settles the design's conditional: keep F4's colour check.
     - Character rows: 0xFFFF (shadowI 16, shadowR 11, clr 16,16,16); 176; 98 (shadowI 1, shadowR 10, clr 10,12,15).
     - Lights: floor 0 is (0,0,0); floors 1-2 are (-3,-3,-4); floor 3 is (-6,-6,-7).
     - On floor 0, `_Color.rgb` is (80, 96, 120) with the 98-row fallback and (128, 128, 128) on the default row (fldmcf.cs:112-114; written by fldchar.cs:217-235).
   - **Add `dress.self.light_rgb`.** Read it from the dressed body's first renderer material `_Color`, one frame after spawn.
   - **F4.** Compute the oracle in Python from the install: `mapconfig.parse` of the field's MCF, the 98 row plus the light for the published `player.floor`. Require equality. `light_row == 98` is the second witness.
   - **B29.** Rewrite its lighting pass as "on floor 0 of 250 the dressed body's base tint matches the host's own Zidane side by side, not the bright default grey". The tree-shadow step can stay as a secondary note; it cannot discriminate, because the floor-light delta adds to whichever row is used.
   - **Vanilla cost.** In fldmcf, test `netDressSrc != 0` before the extra row search. :81 runs every frame for every character, before the :84 gate, so vanilla then pays one field read per character per frame.
   - **The guest-side ghost fallback** uses the local player's model (NetSyncClient.cs:5583-5586). Once the guest's own body is dressed, that row is missing. Use `(lp.netDressSrc != 0 ? lp.netDressSrc : lp.model)` at :5584.
   - **Stays in s141 (D6).** s140 alone cannot throw here: all 818 stock mapconfigs carry a 0xFFFF row, and kit fields have no MCF, so the service returns at :61-64. Without the fallback the cost is only cosmetic.
   - **Optional (nit): the shadow size.** The 98-row fallback also supplies the blob shadow's SIZE (:120-129), so every rig without its own row gets Zidane's: too big under the moogle, too small under Quina.
     - Modal shadowR from the install, by rig: Zidane 9, Vivi 10, Garnet 8, Steiner 11, Freya 11, Quina 16, Eiko 8, Amarant 13, moogle 6.
     - On the fallback only, keep the row's clr and shadowI (the room's light) and set `shadowR' = row.shadowR - 9 + modalR[rig]`. That is nine baked, derived integers, so provenance stays clean.
     - Otherwise, record the size mismatch in risk 11.
     - Field 250 cannot show this either way, because its Zidane_Loop calls DisableShadow every frame.

5. **Held props go to the worn rig's hand (s141-F7, D3).**
   - **Stock.** Stock attaches held items to the Zidane player's right hand: bone 13 (37 times) and bone 12 (17 times), in 29 fields. They include:
     - Fossil Roo's flowers (1405-1416);
     - Gizamaluke's bells (702-704, 753);
     - Ipsen's mirrors and pot (2510, 2513);
     - the Gulug stone (2260) and the Cid frog (2357);
     - the Prima Vista sword (61-64);
     - the coffee cup (571), the letter (261), the bottles (200, 2150) and the pickaxe (1421).
   - **The bug.** On a dressed rig, bones 12 and 13 are other parts. Bone 13 is Vivi's chest, the R_forearm of Garnet, Steiner and Eiko, Amarant's R_upper_arm, and the moogle's crest (its pompom).
   - **The fix.** In ATTACH, after the 62/3010 override (:1555-1556) and before `geo.geoAttach` (:1557), remap bone 12/13 to the rig's (R_hand, R_hand_end) pair from s139's table when the carrying object has `netSelfDress != 0`.
     - Other bones are logged in `attach_notes`; remaps are counted in `attach_remaps`.
     - Because the remap runs first, attachTargetBoneIndex (geo.cs:130) stores the dressed index, and RestoreAttachModel (FieldMap.cs:530-537) re-attaches correctly on a warm return.
   - **Bench.** F8 (section 4.5).

6. **The mesh-op drop only defends kit and modded content (s141-F14, nit).**
   - Stock never mesh-hides or mesh-shows a player body: 0 of 817 scripts target a player-defining entry's object. The kit emits no 0x39 or 0x3A.
   - Keep the drop and its count as designed. F5 stays the drop's only proof, and it is synthetic.
   - Move B29's dagger-draw clause to the B23 family: it exercises s140's MapAnim, not this drop.

7. **Twin clips for ladders and jumps (s140-F11, D2).** This is the optional row deferred from s140:
   - JUMP_n and LADDER_x_y map to the body rig's clip with the same suffix when the AnimationDB has one: Vivi, Garnet and Steiner have LADDER_1_1 .. LADDER_2_3; every main has JUMP_1/2/3; the moogle has MOG_JUMP. Otherwise they map to the idle alias.
   - AJUMP keeps jump0 and jump1 unchanged. The sampled stock windows match across twins: GRN LADDER_2_3 (163, 2, 8) = ZDN (11453, 2, 8), and GRN LADDER_1_1 (194, 2, 6) = ZDN (10687, 2, 6).

8. **A calibration lever (s138-D8).** `selfdress polish on|off` (selftest) bypasses MapFootstep, the mesh-op drop, the prop remap and the lighting fallback together. F1, F2, F4, F5, F7 and F8 then go red behaviourally on the s141 DLL itself, as with every earlier R3 patch.

#### Decisions

| # | Question | Recommendation |
|---|---|---|
| D1 | (moved to s139 D1: the opt-out split) | — |
| D2 | (moved to s139 D2: the spectating guest) | — |
| D3 | Held props: log only (the design), or remap to the worn rig's hand? | Remap (amendment 5). Log-only would put free-roam carries such as the Fossil Roo flowers on the moogle's pompom. |
| D4 | A dressed Steiner's footsteps: Zidane's surface sound, or his own 925? | 925 in both slots (amendment 1). That is what stock does in every Steiner registration, and it matches the design's own "as in stock" rule for the moogle and Quina. |
| D5 | Use stock Memoria's DictionaryPatch instead (`3DModel 98 <GEO>` + `3DModelAnimation`, DataPatchers.cs:626-670)? | Reject it, and record the reasons in Appendix A.2: (1) it is static per launch and cannot follow the host's party per session; (2) it remodels model 98 for EVERY Zidane on the laptop, including the host's ghost (EnsureGhost resolves `rs.Model` 98 through FF9BattleDB.GEO) and stock Zidane NPC copies; (3) it needs every Zidane anim id remapped; (4) remapping a clip changes frameN, which re-opens the frame-wait wedge (review dress F1) that KeepSourceTimeline closes. |
| D6 | Keep the lighting fallback in s141, or move it into s140? | Keep it in s141 (amendment 4). |
| D7 | A calibration lever, or rely on key absence? | The lever (amendment 8). |

---

## 3. Cross-cutting amendments

### 3.1 Harness key design for dress (decided here)

**The split.** The lanes split on the action-replay audit's two deferred questions (its 4.1 and 4.3):
- The s138 lane nests the dress block under `netsync`. Its finding is blocking, and both skeptics upheld it.
- The s139, s140 and s141 lanes assumed the design's top-level `dress`. They proposed a separate ladder, a separate level table and a redefinition of BATTLE_KEYLESS_LEVELS.

**The call.** This audit takes the nested design. It reuses every piece of netsync infrastructure that already has tests: the catch literal, the ladder test, `caps_through`, NETSYNC_TOP_CAP_KEYS and the `_ns_prop`-style accessors. It also leaves BATTLE_KEYLESS_LEVELS's definition alone. From the other lanes it keeps the separate sub-verb table, the widened gate and the dress key law.

**Where the keys go.**
- **The block** is `netsync.dress`, the last key of netsync, appended after `battle`. The top-block order assert (test:2075-2076) gains one name.
- **Writing it.** AppendDress writes every key through Try with TryGetValue, so it can never void the netsync block. Its sentinels join the catch literal's SECOND literal (HarnessAgent.cs:3362). That line must stay one line made of exactly two literals around `NetsyncF3Retired`.
- **Renames.** The design's `dress.ghost.*`, `dress.self.*`, `dress.party`, `dress.codec` and `dress.rig_idle_frames` become `netsync.dress.*` throughout.
- **Outside netsync.** `player.*` and `objects[].model` stay outside netsync and follow the s90 THREE-CASES precedent (channel.py:571-596): an absent key means an old engine, null means no actor, and otherwise it is the value.

**One ladder.** Append four rungs to NETSYNC_BATTLE_CAPS after `acttrance`:

| Rung | Patch | New verb |
|---|---|---|
| `dressinstr` | s138 | — |
| `dresshost` | s139 | `selfdress` |
| `dressself` | s140 | — |
| `dresspolish` | s141 | — |

- Each rung's `netsync.battle` key set is empty (`NETSYNC_BATTLE_CAP_KEYS[rung] = {}`). Its keys go in a new NETSYNC_DRESS_CAP_KEYS.
- The calibration sets are NETSYNC_S138_CAPS .. NETSYNC_S141_CAPS, each calibrated on `caps_through(<the previous rung>)`.
- `caps_through`, the no-gap rule (fakegame.py:124-125) and the older-stand-in test's `have` filter (test:2264-) then hold unchanged.
- The rung names avoid the design's `selfdress` for s140. Under that name, `"selfdress" in caps` would read as "has the verb" when it means s140 (s138-F12).

**Levels.**
- s138-s141 join BATTLE_LEVELS as keyed levels, since each adds `netsync` keys.
- Each gets one capability accessor: `coop_dress_instr`, `coop_dress_host`, `coop_dress_self` and `coop_dress_polish`. The accessor test (test:2513-2529) requires exactly one per keyed level.
- BATTLE_KEYLESS_LEVELS stays `("s132",)`.
- The shared level tests need a dress twin of `_battle_of` (a `_dress_of` descent). That is a small test-only change in s138's commit. Keep the table's name, and add a one-line comment rather than fork the machinery.

**The sub-verb.**
- Add Session.NETSYNC_DRESS_SUBVERBS = `{selfdress: ("coop_dress_host", "netsync.dress.ghost.bench_mask", "s139", <what>)}`.
- Widen the gate to `cap = f33 or nb or nd`. Add dress wording to the not-authority message, and extend the "only after the step" clause to nd (session.py:8737-8749).
- Append `selfdress` in four places, in the agent's order: NETSYNC_SUBVERBS, NETSYNC_AUTHORITY_SUBVERBS, the agent's refusal literal (HarnessAgent.cs:1861, after `actbench`) and FG.NETSYNC_BATTLE_VERB_ORDER.
- Add "s139" to the sub-verb rewrite list (test:2288).
- Union NETSYNC_DRESS_SUBVERBS into the verb-set assert (test:2077) and into the ladder test's verb lookup (test:2010).
- Give dress its own key law: `test_each_dress_verbs_capability_key_is_one_its_patch_added`. It asserts `key.startswith("netsync.dress")` and that the leaf is in `NETSYNC_DRESS_CAP_KEYS[rung]`.

**Ops.**
- `NETSYNC_SELFDRESS_OPS`, keyed on the verb (s139):
  - `ghost <mask 0-15>|off`
  - `empty <mask 0-15>|off`
  - `rule s138|s139`
  - `wire <model>|off`
  - `clear`
- `NETSYNC_SELFDRESS_OP_CAPS`:
  - `self` and `gate` → ("coop_dress_self", "netsync.dress.self", "s140");
  - `polish` → ("coop_dress_polish", "netsync.dress.self.steps", "s141").
- `self` takes: `off`, `auto [mask]`, the NameToRig names (including dagger and salamander), or `moogle`.
- Add `FG.selfdress_ops(caps)` and a DRESS_REFUSALS list in the R3_REFUSALS style (test:4531).
- Pin the old engines' answers:
  - s138 answers "unknown sub-verb";
  - s139 answers with its op list `ghost|empty|rule|wire|clear`;
  - s140 answers with its list, without `polish`.
- An `elif sub == "selfdress"` branch refuses an unknown op in the engine's order and words, before the step is spent.

**Accessors.** Use a `coop_dress_*` family; nothing uses that prefix today. Give it its own accessor table (NETSYNC_DRESS_ACCESSORS) and its own accessor-law test. Do not reuse NETSYNC_TOP_ACCESSORS, whose law pins `{session, menu_refusal}` (test:6094-6100).

**Sentinels.** The house convention: counts 0, ids and ms -1, booleans false, strings and nullable records null, and fixed sub-objects always written whole.

| Path | Keys and sentinels |
|---|---|
| `ghost` (s138) | model -1, geo null, clip null, rig -1, playing false, body null |
| `ghost` (s139 adds) | bench_mask -1, empty_mask -1, rule null, wire -1, mode null |
| `party` (s138) | `[-1, -1, -1, -1]` |
| `codec` (s139) | null |
| `rig_idle_frames` (s139) | nine -1s |
| `self` (s140, a fixed sub-object) | the design's 5.1 keys, plus want_rig, bframe_remaps, src_attached, faults, parse_fallback |
| inside `self` (s141 adds) | steps [], steps_dropped 0, steps_passed 0, steps_fired 0, steps_fired_player 0, light_row -1, light_rgb null, mesh_drops 0, attach_remaps 0, attach_notes 0 |

**Release.**
- Release every selfdress lever (ghost, empty, rule, wire, self, gate, polish) in HarnessSelfTest(false)'s every-path block (NetSyncClient.cs:4695-4705) and in HarnessReleaseBench (NetSyncBattle.cs:5561-5630).
- Mirror the release in fakegame's `_selftest_release` (fakegame.py:4237).
- Add a reset test like `test_reset_releases_every_r3_lever` (test:5309).

**The fake must be able to fail.** Its stand-in models ResolveAuto, the guard, and (from `dressself` on) the arm and dress orderings, so that every ordering it claims to model can go red:
- arming at the field load only;
- the sticky skip;
- the gate checked before the control check;
- the body's rig versus WantRig;
- the B_FRAME law;
- alias ids;
- Zidane-frame steps and 0 drops on a pre-s141 dressed body.

Fault levers as in s138 amendment 12 (s140-F8, s141-F11).

**Protocol.** Every key is additive. The harness protocol stays 5 (HarnessAgent.cs:256).

### 3.2 Wire compatibility

- **The wire stays v14** (NetSyncSocket.cs:140). The only addition is section 8 in the host's type-5 state frame (s139). Id 8 is free.
- **Old guests skip section 8** by id and length:
  - ApplyStoryTo applies only id 0 (NetSyncState.cs:107-130);
  - ParseSections consumes only ids 1-3 (NetSyncParty.cs:218-249);
  - TryReadSection returns the first match (:157-180).

  No patch since s103 has touched either file, so an s117 laptop runs byte-identical walkers. Prove this in-engine with the codec proof's old-guest rows (s139 amendment 6), and on a real wire with G9 (section 4.3).
- **The body** is `[model u16 LE][charId u8]`: always 3 bytes, on every host frame. Readers refuse fewer than 3 bytes, and on a longer body read the first 3 and ignore the rest (the forward rule; TryParseAction is the precedent).
- **Headroom.** The frame is about 3.5 KB today, plus 6 B, against MaxPayload 8192.
- **Mixed pairs.**
  - s137 host + s140 guest: there is no section 8, so the guest disarms with "section absent" and stays Zidane. The host's ghost dresses by its own old rule.
  - s139+ host + s117 guest: the guest skips section 8, and the host dresses its ghost (B19).
  - s139 host + an opted-out s140 guest: the screens split, as decided by s139 D1.
- **The type-0 position frame** stays 37 B unless the owner picks s139 D1's option B. That option adds a 38th byte, which old parsers already ignore.
- **Duo cannot mix DLLs.** The instance roots junction `Managed` (`instance_root.py:29`), so B19 (an old laptop) stays a sitting box.

### 3.3 Containment

- **The guest computes no battle or story state.**
  - The dress writes only presentation fields of the guest's own body: `po.model`, `po.eye`, the anim ids, the attached clips, and `PosObj.netSelfDress` / `netDressSrc`.
  - The B_FRAME remap answers frame counts only for loco families on a dressed body. An offline census test proves that no stock threshold becomes unreachable.
- **Saves.**
  - The save JSON carries only FF9 globals and EventState (JsonParser.cs:40, :236).
  - Scripts cannot read a model: getvobj (EBin.cs:1776-1853) has no model field.
  - The save gates hold during mirroring (EventEngine.cs:693-694; SaveLoadUI.cs:154).
  - The one live hazard is the exit ramp, which s140 amendment 7 closes.
- **The teardown law.** The knob, an exclusion and Clear() never undress a live body. They take effect at the next SetModel (s140 amendment 6).
- **Host, solo and vanilla behaviour do not change.**
  - Every hook is gated on `netSelfDress != 0` or `Armed`, and Armed is read only on a client or selftest role.
  - fldmcf's extra row search is gated on `netDressSrc != 0`.
  - The host's ghost changes only through the s139 rule.
  - The role predicates are positive and read live (s139 amendment 3; s140 amendment 8).
- **Hooks never throw into the VM** (s140 amendment 9).

### 3.4 Stack hygiene

- **Tags.** Tag every hunk `[ff9mapkit netsync s13N]`.
- **Line endings.** Keep each file's own, never mixed:
  - BOM + CRLF: fldmcf.cs, DoEventCode.cs, PosObj.cs, FF9Snd.cs, geo.cs;
  - CRLF without BOM: fldchar.cs and the `NetSync*.cs` files;
  - LF: HarnessAgent.cs.
- **First touches.** s140 is the first netsync patch to edit PosObj.cs, and s141 the first to edit fldmcf.cs.
- **The new file.** NetSyncSelfDress.cs is new; add `<Compile Include="Memoria\Netsync\NetSyncSelfDress.cs" />` to the csproj.
- **The replayer's file list.** Append to DEFAULT_FILES (`tools/memoria_stack_replay.py:61-99`), with s140/s141, every touched file not yet listed: DoEventCode.cs, PosObj.cs, updateModelsToBeAdded.cs, DoCalcOperationExt.cs, NetSyncSelfDress.cs, fldmcf.cs, FF9Snd.cs (if `steps_fired` lands) and geo.cs (if touched). A stale or mixed hunk in these files then cannot pass `diag`. s133 and s134 set the precedent of adding their hook sites.

### 3.5 Design text to correct before the hunks are written

| Where | Change | Source |
|---|---|---|
| 3.4.1 | Record the confirmation census | s140 amendment 13 |
| 3.4.3 | The rig table's new columns | s139 amendment 2 |
| 3.4.3 | The guard comment and "agree in every case" | s139 amendment 9 |
| 3.4.3 | "GhostAs=moogle works" needs the NameToRig entry and the kit's GHOST_NAMES | s139 amendment 2 |
| 3.4.3 | ResolveAuto's `mask == 0` first line | s139 amendment 3 |
| 3.4.4 | The arm list (the knob and the exclusion come out) | s140 amendment 6 |
| 3.4.4 | The Clear sites | s140 amendment 7 |
| 3.4.4 | The suffix rule becomes a table | s140 amendment 3 |
| 3.4.4 | The idle alias | s140 amendment 4 |
| 3.4.4 | The body rig | s140 amendment 5 |
| 3.4.4 | The B_FRAME law | s140 amendment 1 |
| 3.4.4 | IsClientOrSelfTestRole and the cache | s140 amendment 8 |
| 3.4.4 | The 307 pairing | s140 amendment 14 |
| 3.4.5 | Steiner's step sound | s141 amendment 1 |
| 3.4.5 | Code 19 | s141 amendment 2 |
| 3.4.5 | Props remapped, not just logged | s141 amendment 5 |
| 3.4.5 | The lighting oracle | s141 amendment 4 |
| 5.1 / 5.2 | The `netsync.dress.*` paths, the rung names and the op tables | Section 3.1 |
| 6.12 | The legs | Section 4 |
| 6.12 | T1's "the moogle included" does not discriminate | s139 amendment 7 |
| B19 | One hairstyle; Amarant shows his field model only | s139 amendment 8 |
| B22 | The text for an s140+ laptop | s139 amendment 10 |
| B27 | Per the owner's answer | s139 D1 |
| B29 | The lighting rewrite; the dagger-draw clause moves to the B23 family | s141 amendments 4 and 6 |
| Risk 11 | Add: 2855 (Quina, benign); the 165 multi-binder fields; the guest-side skips (if D1 = A); the shadow size (unless fixed) | — |
| Appendix A.2 | The rejected DictionaryPatch remap | s141 D5 |
| Everywhere | Every line cite → the live maps in this document | — |

---

## 4. Harness plan per patch

### 4.1 Shared

- **The bench field** is `selfdress.field.toml` at 30606 in FF9CustomMap-msgs (s138 D7). It is first needed by s140, and holds:
  - a kit Zidane player;
  - a `twin`: a Zidane NPC with no CC, activated as an `[[npc]]` behind an always-true gate (for example `requires_flag_clear` on a safe-band flag that nothing sets). The kit inserts a gated activation ahead of the player's InitObject (`eb/edit.py` activate_block);
  - a `caller` with the gesture, frame-wait and 2705-loop conductors, plus a prop to attach (F8).

  Two rules for it:
  - An offline preflight row, MAIN_INIT_ORDER, proves by disasm that the twin's InitObject comes before the player's. If it does not, the bench fails closed.
  - Identify the twin by its built sid (`objects[].sid`), never by model, because N2 dresses it.
- **Calibration catalogs** (s138-F16). 6.12 gives prose REDs only. Following the house pattern:
  - every check gets an ID and a -CAL row;
  - OLD_PREDICTED covers everything except INI, setup, probe and CAL;
  - LEVER_PREDICTED has one set per lever;
  - precedents: `coop_battle_start_hold.py:250` and `coop_action_trance.py` (INI/S0/P0/PROOF rows; CAL in two modes);
  - the calibration engine for s138 is the s137 DLL `0269771f24b626c1`.
- **The unattended law.** No leg needs a human. Walks are harness input, and screens are game_snap reads.
- **Witness rule.** Every model or clip verdict reads s138's `body`, `anim_geo` and `clip_playing` as well as model and anim. Expected values come from the install oracle through the kit's readers, never from the engine's own tables.
- **Regression (6.1).** s138 rewrites AppendNetsync, so its run keeps `coop_battle_end_guest`, `coop_dialogue_authority` and the catch-literal pins.

### 4.2 s138: leg I (field 250, then 30801)

| Check | Assertion |
|---|---|
| INI | Memoria.ini read-only: Enabled is 0 or absent, and GhostAs is "", auto, off or 0. Otherwise nothing runs and the leg is red. |
| S0 | Setup: `selftest 1`, `no_encounters(True)`, warp 250. |
| I1-I4 | model 98; geo `GEO_MAIN_F0_ZDN`; `anim_geo == geo` at rest; eye -372; body "98". |
| I5 | Moving: anim ∈ {25, 38} mid-hold. At rest: 200, sampled within a few seconds of the release. 57 is reported as the sleep clip, never as a pass. |
| I6 (30801) | `len(objects) >= 2`; every entry has `model`; both read 217; none reads 98. |
| I7 (forced selftest) | `session.ghost` true; non-null values on both sides; held for 2+ publishes; model, geo, rig -1 and clip all match. |
| I8 | After the COOPPARTY seed: `party[0] == 0`, and the sorted members are `[0, 1, 2, 3]`. |
| I9 | `player.sid == player.uid == 10` on 250, and == 1 on 30801. |
| I-CAL | — |

- **Calibration.** On s137, I1-I9 are red, INI and S0 are green, and the probe reads `player.model` absent and `netsync.dress` absent.
- **Offline.** A fake-driven red test for each check: an absent key, an empty list, a null, a wrong eye, a missing ghost, an empty party.
- **Re-pins in the s138 commit.** `test_harness.py:5823-5824`, the catch literal, and the top-block order (test:2075-2076).

### 4.3 s139: leg G (field 250)

The legs run in this order:

| Check | When | Assertion |
|---|---|---|
| G0 | First | Read the baseline `dress.ghost.model` and `mode`. |
| G3a | Before the seed, while the sandbox save's slot 1 is empty | `ghost 2`, with no `empty` op → the moogle, through the real party read. NOT REACHED if the save already holds members. |
| — | — | Seed through COOPPARTY (30604). |
| G1 | After the seed | `ghost 1<<s1` → `ghost.model` is the oracle model for `party[s1]`; `rig == party[s1]`; `geo` and `body` read off the GO; `playing` true. |
| G2 | — | `ghost 6` + `empty 2` → slot 2's member. |
| G3 | — | `ghost 2` + `empty 2` → model 220, `GEO_NPC_F0_MOG`, `ANH_NPC_F0_MOG_*` clips, body "220", plus a game_snap read. |
| G3c | — | `ghost 6` + `empty 6` → the moogle. |
| G3d | — | (owner D2) `ghost 0` → the ghost wears the MOOGLE (220, `GEO_NPC_F0_MOG`), and section 8 carries model 220 charId 0xFF (`DC 00 FF`). |
| G4 | — | `dress.codec == "ok"`, plus the codec log line. |
| G5 (control) | — | `clear` → back to G0's baseline. |
| G6 | — | `rig_idle_frames` equals the oracle `[60, 45, 30, 60, 50, 40, 30, 45, 72]`. |
| G7 (the guard) | — | With `ghost <s1 bit>`: (a) `wire 5489` → the ghost wears 5489; (b) `wire <dressModel>` → dressed; (c) `wire 98` → dressed; (d) `wire 532` → 532. |
| G8 (the rest mask) | The seeded party holds Garnet | `ghost <Garnet's bit>` → the count of enabled renderers equals CreateModel's count, and the off-scenario hair's renderers are disabled. |
| G9 (duo) | — | See below. |

**G9 (duo).**
- Setup: host GuestSlots=2, GhostAs=auto, field 250, through `duo.py` with the relay's `--tap`.
- Decode the tap's host type-5 frames with new battlewire helpers, `walk_sections` and `decode_dress`. coop_peer does not parse type-5 sections today (coop_peer.py:801-804).
- Assert:
  - section 8 sits after section 7 and carries the oracle body (`DC 00 FF` for a 1-member party);
  - the guest logs "state-mirror ARMED" and its party mirror lands, which proves the live readers skip section 8;
  - the guest's `player.model` stays 98;
  - the host's `dress.ghost.model` equals the oracle.

**Calibration.**
- On s138, the verb is refused before the step (NOT REACHED), and the codec key is absent.
- On s139 under `rule s138`, G2, G3 and G7a turn red, and nothing else changes.

### 4.4 s140: legs S, W, X, N and T (field 250, 30602 and the bench field)

| Check | Assertion |
|---|---|
| S1 | As designed, plus body "192" and `anim_geo == GEO_MAIN_F0_FRJ`. |
| S2 | At rest `ANH_MAIN_F0_FRJ_IDLE`; moving ∈ {2553, 2558}; `anim_geo == geo` throughout, read live. Rest is sampled before the idle timer runs out. |
| S3 | `self auto 2` + `empty 2` + a re-warp → model 220, eye -200. |
| S4 | `self off` → model 98 at the next SetModel. |
| S5 | The ghost wears 192. |
| W1 (30602) | The warm return, as designed. Then idle past the inactive timer: `anim_geo` stays FRJ. At rest `player.anim == 2556`; walking, `anim_geo == GEO_MAIN_F0_FRJ`; `src_attached > 0`. |
| W2 | The cold control, as designed. |
| X1/X2 | Compare the clip NAME `ANH_MAIN_F0_FRJ_IDLE`. After the gesture, frameN equals the idle's frame count (the alias proof). |
| N1 | The twin first (by sid) → `objects[twin].model == 98`, and `skip_npc >= 1`. |
| N2 | `gate 0` → `skip_npc` stays 0, and the twin AND the player both wear 192. |
| N3 | The caller InitObjects a second 98+CC entry AFTER the player's CC has run (after a Wait) → `skip_second >= 1`; the late entry stays 98; control is unchanged. |
| T1 | A short-idle rig (Garnet or Eiko, 30 frames) runs RunAnimation of a Zidane gesture of 60+ frames, then `while f[7] < 58` → the loop finishes, and `timeline_kept + 1`. The moogle is a control, not the discriminator. |
| T2 | The SelfTest row, as designed. |
| T3 | SetWalkAnimation(8847) + Walk + the 2705 loop finishes on every rig, with `bframe_remaps + 1`. It is red on the design as written. |

- **Offline.** The B_FRAME census test, the loco-class table test and the frame-count oracle table.
- **Calibration.** On s139, `self` is refused (NOT REACHED), and S4 and N1 read NOT REACHED, not green.
- **The knob without editing the ini.** Use `self off`, never an edit of Memoria.ini mid-run. A bsig change re-commits `_enabled` and `_role`, which drops the forced role (the actbench knob precedent).

### 4.5 s141: leg F (field 250 and the bench field)

| Check | Assertion |
|---|---|
| F1 | On a fresh load, freya → steps {[2553,4], [2553,16], [2558,0], [2558,9]}. |
| F1b | Walk the dressed Freya for 3 s → `steps_fired >= 2`. |
| F2 | moogle → steps `[]`, `steps_dropped == 12` (per load), no code-19 fault. |
| F3 (control) | off → {[25,4], [25,13], [38,0], [38,8]}, and `steps_fired_player >= 2`. |
| F4 | `light_rgb` equals the oracle, (80, 96, 120) on floor 0 of 250, and `light_row == 98`. |
| F5 | The caller's HideObject(250, 1) → `mesh_drops >= 1`, `player.meshflags == 0` (synthetic). |
| F6 | freya, `dioboot`, `dioleave` (a warm return) → `steps` equals F1's set with no duplicates; `steps_fired >= 2` after the return. |
| F7 | steiner → {[1996,4], [1996,14], [2005,0], [2005,9]}, with sound 925 published per key. |
| F8 | A prop attached at bone 13 on 250 → `attach_remaps + 1`, and the prop's parent is the rig's R_hand_end bone, matched by name. |

**Calibration.**
- On s140: F1, F1b, F2 and F4-F8 are red, and F3 is green.
- On s141 under `polish off`: the same set is red.

---

## 5. Refuted findings (do not re-litigate)

- **s138-F14**: "The kit builds the player's InitObject first, so the twin-first order needs a post-build splice." A gated `[[npc]]` activates through `edit.activate_block` (content/npc.py:350-357). That inserts at Main_Init's start unless `after_player` is set (eb/edit.py:782-799), and only the door handshake sets `after_player` (content/gateway.py:122). The bench uses that lane (section 4.1). The finding's id choice survives as s138 D7.
- **s140-F5**: "The field-768 hotfix plays a raw Zidane clip on the dressed body." The hotfix fires only on a warm return from battle 4 (updateModelsToBeAdded.cs:80, behind the `inited` guards at :11 and :46). A co-op guest never runs a real battle 4, and gets its warm context only from `NetSyncDiorama.PrimeWarmReturn` (NetSyncDiorama.cs:1311), so no dressed body reaches the hotfix.

**Lane recommendations this audit overrode:**
- **The top-level `dress` design** (s139 D2, s139-F10, s140 D7, s141-F11): a top-level block with its own ladder and catch, and a redefined BATTLE_KEYLESS_LEVELS. Overridden by section 3.1 (nested, one ladder). Their gate, sub-verb table, op table and key-law test survive, re-keyed to `netsync.dress`.
- **The rung name `selfdress` for s140** (the design and s139-F10). Overridden by `dressself` (s138-F12).
- **s138 D9**: a post-build `.eb` splice. Overridden by the kit's gated-NPC lane (refuted s138-F14).
- **s140 D6**: a presentation backstop. Dropped: its only stock path is the refuted s140-F5.
- **s139-F12's Garnet-only re-apply.** Overridden by s141-F2's general rest mask, built in s139 (s139 amendment 8). Both skeptics also moved the affected box from B20 to B19.
- **s138-F13's `empty <slot 0-3>`.** Overridden by `empty <mask 0-15>` (s139-F17).
- **s140-F18's `body.Length != 3` disarm.** Overridden by `< 3`, with a longer body read forward (s139 amendment 6).
- **s141-F4's "19 is harmless".** Overridden: drop 19 together with 16-18 on a rig with no footfalls (s141 amendment 2).
- **s141 D1** ("not an owner question"). Overridden: it is s139 D1 and is marked for the owner, because it reverses box B27, which the design gave as expected behaviour.
- **s140-F1's "softlocks on every rig".** Not adopted as stated: both skeptics called it overstated, so leg T3 measures which rigs wedge.
