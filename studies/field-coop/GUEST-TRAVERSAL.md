# Guest traversal: letting a following guest climb stock ladders and take jumps

**Status: R0-R2 BUILT and in-game proven on the solo bench (engine patch s156, 2026-10-26); R3 PROVEN on two
PCs (2026-10-27: climbs, the talk hold, the cold return mid-climb, the F11 refusal); R4-R5 open.** The two-PC
session's results and its five findings (ghosts that never pause, the dressed "pencil" glide, the doubled party
member in scenes, the F1 lag, the host's same-field reload) are in
[`GUEST-TRAVERSAL-TWO-PC.md`](GUEST-TRAVERSAL-TWO-PC.md). Findings 1 and 2 are fixed by engine patch s157 (deployed and solo-benched 2026-10-28; the two-PC check is next). The design below was written 2026-10-25 from a read-only multi-agent pass (census, design,
adversarial critique) over the live engine tree `C:\gd\FFIX\Memoria` at the netsync s145 tip. Cites are
`file:line` against that tree, which other sessions edit, so lines can drift.

### What s156 shipped (R0-R2)

- **R0, the table.** `ff9mapkit/ff9mapkit/eb/pressclosure.py` (the census classifier, promoted; 0 mismatches against
  the census on every QUAD root) and `ff9mapkit/ff9mapkit/guest_traversal.py` (`py -m ff9mapkit.guest_traversal
  --check|--write`) derive the allowlist from the user's own install across all 7 languages. The committed
  `ff9mapkit/ff9mapkit/data/guest_traversal.json` owns the counts; the engine compiles its C# twin
  `NetSyncGuestLocalTable.cs` (ids, lengths and CRC-32s only). Of the census's 86 LOCO-ONLY rows, the kit ships 80;
  6 are refused by the ship filters the census lacked. The deployed s156 engine was captured before R15 and still
  carries the sixth, 1209:5. s157 (deployed 2026-10-28) re-captures the table whole from the JSON, so the pin
  `DEPLOYED_AHEAD` in `tests/test_guest_traversal_table.py` (s156's `S156_DEPLOYED_AHEAD`) is empty: the newest patch
  carrying the table must equal render_cs of the JSON exactly, replaced whole.
  - **R11, the latch audit, path-aware:** a variable the climb writes must not be READ by any other function on any
    control-flow path before it is written there (a read-modify-write is a read; a partial-width write covers only
    its own bits), unless the reader is load-once. 2702 e15/e19 (entry 21's stone functions read the latch first),
    353:11 (the player's tag-1 loop reaches a read through a choice switch's default arm) and 2507:4/5 (13:1 is no
    longer load-once: 0:11's ReturnEntryFunctions(13) restarts its tag 1).
  - **R12 (ops)** refuses ReturnEntryFunctions (0x97) anywhere in a row's functions, and any TerminateEntry that is
    not the constant self-end 255. **R13 (writes)** refuses any Global (save) or Null/Memoria-variable write.
    Neither refuses a stock row today; both close holes the review proved with synthetic fields.
  - **R14 (keys)** refuses a closure that polls any key other than the directions. It refuses no stock row, and it
    is what lets an engine-side in-flight key mask (E1 below) strip every host-owned key without breaking a climb.
  - **R15 (walk-ins)** refuses a row that lands the guest on NEW ground (the landing's walkmesh components minus the
    components the room's entrances arrive on, taken as a union over entrances) where a tread region or an object's
    bump (`CheckNPCPush`) starts something. A walk-in is exempt only when every effect of its closure sits behind a
    user-control test AND a constant key poll inside the bits the follow filter strips at control-on, both in the
    same frame (a lone fact dies at any yielding op); an incomplete closure or scan counts as exposed. A moving
    object's footprint is bounded only when its moves are its own pathing-on walks, over the tris an NPC may walk
    (the player-only block bit does not stop it). It refuses 1209:5: the dungeon monsters can walk onto the landing
    floor across NPC-only tris that Main_Init disables only after it yields. Rounds 4-5 closed it fail-closed against
    synthetic shapes: a Seq entry that is not exactly one tag 0 is a gap (its tag 1 runs when tag 0 returns), tris code
    can turn on count as footprint and as NPC ground, a walk-in on new ground that moves the player onward is chased
    to a fixpoint, any op past the engine's enum is a yield, stacked `0xFF` prefixes are a function that does not
    decode, and a field that runs BAFRAME or a walkmesh sim (0x102-0x108) refuses every row. Each was measured
    stock-neutral: no row moved.
  - **The Japanese waiver.** 14 rows (407:16-18, 408:6, 408:9, 912:14, 1912:15, 1950:4-5, 2602:5, 2605:4-7) fail
    R15 only in Japanese, through stock chest bumps. `ETb.ProcessJapaneseLayout` moves a Japanese player's Confirm
    into the Cancel bit before the follow filter, which strips only Confirm|Special|Select, so a Japanese guest can
    already open those chests (KEYON 0x90000) on any ground: an engine hole older than traversal, not a new class.
    They ship under an explicit waiver (the JSON's top-level `waivers`, outside the CRC and the C#), pinned row for
    row; the engine fix is E2 below, which retires it.
  - **R16 (watchers)** is measured, not enforced: it flags code outside the closure that would react to the guest's
    presses or position on new ground. Enforced, it refuses bench rows 114:9, 207:10 and 207:11 through two
    false-positive classes (the stock scenario-guard idiom and 114's direction pick), so its trips are pinned instead.
  `studies/field-coop/guest-traversal/far_component_treads.txt` is the D5 report.
- **R1, shadow.** `netsync guestlocal shadow` computes and logs every verdict while the gate still declines;
  `guestlocal mutate <n>` flips one byte of the hash INPUT (never the script) and the press reads "unverified bytes";
  `guestlocal off` is the s155 gate byte for byte.
- **R2, act.** A verified press runs the stock `Request(quad, 1, 3)` on the guest's own copy; nothing goes on the
  wire. Ladders (114, 207's Seq row), Async jumps (408), the host-scene refusal, the mid-climb teleport refusal and
  the climb-scoped talk hold are all proven in game (bench `coop_guest_traversal.py`).
- **Pulled forward from R3:** the one-tick race defer (a relayed talk waits while a guest press is queued) and the
  climb-scoped talk retention (a host start that lands mid-climb is held in one slot and applied at the dismount,
  past the host's TTL). Both are bench-proven; the duo/two-PC proof of the real relay's timing is still R3's.
- **Trip wires** are telemetry only. The engine's `TripClassRule` exempts only the shipped TerminateEntry form (the
  constant self-end 255), so a Seq ending ANOTHER object trips 'spawn'. Auto-teleport holds while a climb is in flight.
- **Selftest only (cannot be shown on the solo bench):** `own_story`, the follow/kick fade, field-changing, the
  session ending, the queued tick, `hostscene.host_climbing`, the trip classes. A host battle booted mid-climb is
  logged (one line) but unproven in game until R3. A Seq or async tail that outlives control is not observable on the
  bench rows: on 207 the Seq closes 4-8 frames before control returns, so the bench judges only that a flight never
  ends while control is off.
- **The bench's three in-game lessons** (each now a pinned law in `coop_guest_traversal.py`): the harness's y is the
  NEGATED script y (SetupJump stores `jumpy = -getv2()`); a debug warp leaves an env-sound slot byte that makes
  408/207's Main_Init WaitWindow on "Error Env Play()"; 408's ledge corridor plans only under a 56 u clearance.
- **Review:** three independent reviewers (engine, kit, bench), every finding then adversarially verified with its
  fix measured. The kit holes (the path-blind R11, the DRET restart, R12/R13) and the bench's blind spots (when a
  flight ends, 207's foot inside the loop band, K-R's mutate half) were fixed; two engine findings were refuted.
- **Pre-session review (after the merge), two findings that turned out unreachable -- no code change, by evidence:**
  - *A host battle booted mid-climb leaves the rest of the climb untracked after a WARM return.* It cannot return
    warm: `NetSyncDiorama.WarmVerdict` refuses a warm prime whenever player control is off ("player control is off
    (a scene holds it)"), and every shipped climb holds control off for its whole flight, so a mid-climb boot always
    returns COLD through Main_Init and dropping the record at the boot is right. The only control-on flight window on
    the shipped rows is the one-tick queued press (207's Seq closes 4-8 frames before control returns; 408's async
    body hands control back in the pass it returns), and there the climb's own DisableMove still holds auto-teleport
    (busy on control off) and s155's control-off talk defer.
  - *The live talk hold drops when the scene record misses.* It cannot miss on a v14 host: `BuildStateFrame`
    appends section 5 (the scene flag and nonce) to EVERY host frame and section 6 (the talk) rides the same
    snapshot after the host raises the talk's scene (`StartSceneAt`), and `NoteTalkScene` reads that frame on the
    same tick (from `ServiceTalkFollow` and the dialogue pump) before `HoldTalk` keys the slot. A hold is dropped on
    the scene only when the host's conversation really ends during the climb -- by design (D8b).
- **Pre-session review: what still ships, documented, not refused.** Each one plays on the guest's copy only.
  Nothing reaches the host's game. The guest's story is re-staged from the host's at the next field load
  (`ApplyStoryImpl`). A paired guest cannot save, and it reloads its own autosave when the session ends.
  - *A ladder-top hidden item (1952:8, 2853:9).* A code entry's tag-1 loop pays out an Ether or Elixir (Global
    7573 / 7582) on a position test plus Confirm, with no user-control test. The guest's own Confirm passes the
    filter while the climb holds control off. R15 sees no new ground (the top is mid-flight) and R16 is not
    enforced; the fix is E1.
  - *Per-visit ground.* ARRIVAL is a union over entrances, so a row ships when its landing is arrival ground for
    SOME entrance, even on a visit that came in elsewhere: 207:10 (bench), 914:10, 2505:4, 2853:5, 2212:3, 301:8,
    2918:4. A per-visit rule would refuse the bench row 207:10.
  - *Japanese hidden-item watchers on new ground* (R16, not enforced): 114:9 (bench), 557:11-12, 565:11-12,
    1312:11-12, 1863:9, 2918:3/4. Same JP key hole; the fix is E2.
  - *1209:5 on the deployed engine.* The kit refuses it, but the captured engine ships it until the next capture.
    Its exposure is a monster bump whose `Battle` the engine already skips for a mirroring guest (ENCOUNT
    `IsMirroringStory`).
  - *The binding gap.* `VerifyRow` hashes only the row's closure functions, so a modded or forked field whose OTHER
    bytes changed still verifies (measured: a 2955 fork with an injected event). R11, R15 and R16 judged those
    bytes, and the walkmesh, from the stock install. The fix is E3.
  - *Latent R15 gaps (no stock row reaches any of them; left for later).* The round-5 verifiers built each one as a
    synthetic shape that ships, then measured 0 rows on the install. An island of code-switchable tris that touches
    no walkable tri counts as no component. `Ground.landed` matches walkable tris only, where the engine's re-pick
    (`GetActiveTriIdxAtPos`) also takes a player-restricted or code-enabled tri. The chase records the usual landing
    ops only, not a CreateObject, Slide, WalkTowardObject or WalkEx that moves the player. `SetTriangleFlagMask` can
    mask the player-restriction bit, and Ground does not model it (the bench rows restore 255 inside their own
    closure). No install-free test reads the far report's chase and new-ground columns. They matter only once the
    table is derived from bytes other than stock's, the same premise as E3.
- **Engine follow-ups (not built).** **E1:** while a guest-local flight is armed and in flight, strip
  `HostOwnedKeys` from control-off reads in `FilterScriptButtons` (R14 guarantees no climb needs them); closes the
  ladder-top items. **E2:** a JP-aware `ControlOnScriptKeys` that also strips the Cancel bit under the Japanese
  layout; retires the waiver and closes the JP watchers. **E3:** a per-field, per-language digest that binds the
  bytes R11/R15/R16 read plus the walkmesh, checked beside `VerifyRow`. Any capture also drops 1209:5.
- **Owner decisions taken as defaults:** (1) the table is regenerated by the kit from the user's install and
  compiled into the DLL; (4) an undressed guest climbs with the field's own body, and the idle slide stays for
  characters with no ladder clip; (6) a host battle mid-climb is accepted and logged. (2), (3) and (5) are R4/R5/later.
Companion: [`../coop-review/REVIEW.md`](../coop-review/REVIEW.md) (the whole-stack adversarial review this came out of).

The owner's ask: *"enabling some interaction for the guest such as ladders, so they're not reliant on the warp."*

## 1. Why the guest can't climb today

A following guest is a field spectator. `EventCollision.CheckQuadInput` refuses every press-fired region
interaction for it (`EventCollision.cs:74-78`, `NetSyncField.SpectatorField`). Ladders, jumps, carries,
chests, savepoints and kit gateways all go through that one funnel. DESIGN.md §4 accepted losing ladders
because "no rider physics exists" (a climb only moves the machine that started it), and teleport-to-host
(F11 / held L3) became the recovery. So the guest stands at the foot of every ladder and warps.

## 2. The census: what stock ladders actually do

Script: [`guest-traversal/interaction_census.py`](guest-traversal/interaction_census.py) (plus
`walkmesh_pass.py`, `summarize.py`). It reads every field's US `.eb` live from the install via UnityPy and
decodes raw opcodes through the kit's `eb` model. It is read-only and deterministic: a second full run gave a
byte-identical report. Outputs: [`summary.txt`](guest-traversal/summary.txt) and
[`guest_local_candidates.tsv`](guest-traversal/guest_local_candidates.tsv) (field, entry, tier, kind,
walkmesh verdict, `.eb` sha1 prefix; no game bytes).

For each press root it follows the handler's whole call closure: `RunScript*` by uid (250 = the controlled
player), `RunSharedScript`, and `Init*`. Every opcode in that closure is sorted into an effect bucket.

**Headline numbers:**
- 818/818 fields scanned with 0 decode failures. 2,428 press roots: 494 region (quad), 1,099 NPC talk,
  255 tread-poll chests, 330 loop polls, 250 card challenges.
- 263 of the 494 region interactions move the player: 84 navigable ladders, 80 jumps, 74 carry loops,
  7 auto ladders and 17 walks.
- **125 candidates in 62 fields** move the player and do nothing else that matters: no window, choice,
  story-flag write, item/gil/party op, battle, menu, FMV or ATE. They break down into:
  - LOCO-ONLY: 86. These are pure movement and the first ship class.
  - LOCO+EXIT: 25. The climb ends in `Field()`.
  - LOCO+LATCH: 11. They write a room-local MAP variable that another region reads.
  - LOCO+ACTORS: 3. They also move a prop.
- **75 of the 86 pure ones link walkmesh areas you cannot reach on foot.** The ladder strip is a
  script-only (CPC-restricted) triangle. A guest without the interaction is genuinely stranded today.
- **All 86 are byte-identical across all 7 languages**, so one row per region covers every language
  (the design pass measured 121/125 candidates identical; the 4 that differ are JP-only and already
  excluded).
- Climbs read only **direction keys**. Those are not in `HostOwnedKeys` (`NetSyncField.cs:949-950`), so the
  s99 script-key relay never touches the guest's climb input. 30 player-moving handlers poll host-owned
  bits, Confirm or Select (for example A. Castle/Staircase 1202's "press to jump off"). They stay refused.

**The stock shape** (decoded from Alexandria/Residence 114 e9; Treno is the same):
- Region tag 2 is the tread function. It reads `ifnot(usercontrol) return; Bubble(1)`, which shows the "!".
- Region tag 3 is the press handler. It runs:
  1. the usercontrol gate;
  2. the stock control bracket (`Map.Bit[158]`, `DisableMove`, `SetTriangleFlagMask(127)`);
  3. `RunScriptSync(2, 250, 17)`;
  4. the closing bracket.
- Player tag 17 is the climb. It picks the mount end by height, sets the ladder attribute
  (`AddCharacterAttribute(4)`), runs a `SetupJump`/`Jump` arc onto the ladder, then loops:
  - read `B_KEY` up/down;
  - step `Map.Int16[2]` by 20;
  - snap the position with `MoveInstantXZY`;
  - step the climb animation by hand.

  It dismounts with another jump arc.
- One-shot hops (Ice Path 301, Dali Storage 407/408, Terra 2602) are shorter: they turn, jump and land.
  Some are dispatched by the player's *entry index* rather than uid 250, so a uid-250-only scan misses them.

**Examples worth knowing:**
- Ladders: Alexandria/Residence 114, Prima Vista/Cabin 207, Lindblum/Church 557, Lindblum/Hideout
  565/1312/2112.
- Hops: Ice Cavern/Ice Path 301 and Waterfall 310, Dali/Storage Area 407 and 408, S. Gate/Bridge 805/808,
  Terra/Stepping Stones 2602.
- Carries: Chocobo's Paradise 2955.

**What the census cannot see:**
- Scenario dispatch (whether a region is ever armed).
- Computed `SetRegion` zones.
- Walkmesh triangles toggled at runtime.

"Stranded" is therefore an estimate from the static `.bgi`, not a proof. Offline is not in-game proof.

## 3. The design (recommended): a CRC-checked allowlist at the spectator gate

Three engine-side alternatives were weighed and rejected:
- **(A) Port the classifier to C#.** About 700-1000 new lines of exactly the kind of code where this
  project's defects land.
- **(C) A runtime sandbox that drops persistent effects.** The engine has no transactions, so a half-run
  handler leaves `DisableMove` set, tiles changed and the walkmesh masked.
- **(E) Teleport to the landing point.** That is the warp again, just moved somewhere else.

**The recommendation is (B):**

1. **The table.** The kit promotes the census classifier and generates one row per allowed region:
   - the field id;
   - the region entry;
   - the class and kind;
   - the 2-5 functions the closure calls, each with its role (the region, the controlled player, or a
     fixed entry), tag, length and a CRC32 of its bytes.

   The slice rule is `2+off[i]`, matching `GetIP`. The function tables are offset-sorted in every entry of
   the 38 candidate fields (critique-verified).
2. **The gate.** It is one site: the `SpectatorField` branch of `CheckQuadInput` (`EventCollision.cs:74-78`).
   Look up `(EffectiveFieldId(fldMapNo), quad.sid)`, re-hash the row's functions from `allObjsEBData`, and
   only on an exact match run the **stock** `Request(obj, 1, 3)`. The climb then plays on the guest's own
   copy of the room. Any mismatch keeps today's decline: a modded script, a kit edit, another build, an
   unknown field.
3. **Nothing goes on the wire.** The guest's world is session-scoped already: the next load re-mirrors and
   the exit ramp reloads its own save. `EmitTalkStartIfHost` is host-only, so a guest climb is never relayed.

### Fixes the critique requires before R1 (verdict: *sound with fixes*)

1. **No automatic control-restore watchdog.** A "5 s after the handler returns, force control back"
   rule can fire in the middle of a scene: an NPC scene that won a same-tick race, a tread `DisableMove`
   at the landing, or an Async jump still running. Log and count only. The ~ Reload stays the human
   escape. (*A rule that can fire in the wrong place is worse than none.*)
2. **The same-tick race with the talk relay.** The guest presses a ladder in the same frame that
   `ApplyTalkStart` replays a host NPC talk (`NetSyncClient.cs:6803-6806` checks only usercontrol, and
   control is still on). Both handlers start `ifnot(usercontrol) return`, so one bails. If the NPC's is
   the one that bails, the host's conversation is lost for good. Defer `ApplyTalkStart` while a guest climb
   is in flight. Refuse the press while a relayed start is pending.
3. **Long ladder hangs vs the 4 s talk TTL** (`TalkRelayTtlMs`, `NetSyncClient.cs:394`). While the guest
   hangs on a ladder, keep any deferred talk start, keyed on the host scene nonce. Apply it when the climb
   ends if that scene is still running.
4. **Trip wires are telemetry only,** attributed at the opcode to the climbing objects: the region, the
   control character, or their Seqs. Keying them on a global "in flight" flag would poison good ladders
   whenever an ambient line or a chaser battle fires mid-climb. Do not add `return 0` on battles and do not
   reclassify windows. Gate every hook on `SpectatorField && InFlight`.
5. **The "!" is drawn in two places.** The NPC/region icon poll is at `EventCollision.cs:321-323`.
   Stock regions also draw it from their **tag-2** `Bubble(1)` (FICON, `DoEventCode.cs:1889-1898`). Gate
   both, keep it on allowed rows, and buzz once on a refused press (the s121 SFX-102 precedent).
6. **Fixed-uid dispatch rows** (I. Castle 2505 e7 calls entry 9, not 250) need their own role. They also
   need a check that `GetControlChar().sid` equals that entry, or the wrong body jumps on a swap-player fork.
7. **Drop the cross-room rung.** Follow-warp already handles the host's exits, and
   `RedirectGuestFieldJump` already passes `dest == LastHostField` (`NetSyncClient.cs:439`). The only new case
   would be a guest climbing to a room the host isn't in, which bounces anyway.
8. **Dressed guests slide up ladders in idle pose.** Self-dress maps ladder/jump clips to the worn
   character's idle alias on the source timeline (`NetSyncSelfDress.cs:142/152`). That is mechanically safe,
   but every dressed Vivi or Steiner glides. Before the first owner playtest, either build the s141 twin-clip
   rows (VIV/STN/GRN ladders, 8 jump rigs) or run the first playtests with an undressed guest and say so.

### A related bug the design pass found (source-traced, not yet seen in game)

The s95 quad promotion relays a host region press when a window rises within 3 s. **32-34 stock regions
open a window before they move the player** (the two passes count slightly differently), and the guest's
copy then moves the guest's body from wherever it stands. Examples:
- Treno/Dock 916 e5;
- the Ice Castle per-landing choices;
- the Pandemonium lifts 2713/2714.

The critique's fix splits these by what the handler does:
- **It leaves the room:** skip the replay. Follow-warp covers it.
- **It changes tiles, the walkmesh or spawns:** keep the replay. The guest's room matching the host's
  matters more.
- **Pure movement plus a window:** replay only if the guest stands inside the region.

### Host view

- The 30 Hz position lane already carries the climber's height, so the ghost rises with the ladder.
- But `DriveGhost` loops the climb clip at speed 1 (`NetSyncClient.cs:10523-10563` at s156), so a climber who
  stops halfway keeps climbing in place on the other screen. SEEN on two PCs, 2026-10-27. The fix now
  recommended is the anim frame as trailing type-0 bytes, sampled like the engine
  (`GUEST-TRAVERSAL-TWO-PC.md` finding 1); the vertical-velocity speed is the no-wire fallback.
- An undressed guest that the host dresses as its puppet character plays that character's idle.
  **Corrected 2026-10-27:** the raw anim id already rides the wire (`NetSyncClient.cs:1926`), so a twin
  clip reaches the ghost with no wire bump (finding 2).

## 4. Rungs (one in-game test each)

| Rung | What | Proof |
|---|---|---|
| R0 ★ | Generator + the table + `VerdictRule` self-test with mutants. Split pin test: an install-free half compares the committed table to committed verdict JSON; an install-gated half re-derives CRCs in the gate worktree (**the worktree skip trap**) | offline |
| R1 ★ | SHADOW mode: the DLL computes and logs verdicts, the gate still declines | bench 114, undressed; `guestlocal mutate` must read "unverified bytes"; `guestlocal off` = today's exact decline line (calibration red) |
| R2 ★ | ACT on LOCO-ONLY: ladders, jumps, carries | bench 114 up and down; Async 408; multi-node 207; F11 mid-climb declines; host-scene refusal |
| R3 ★ | The race, TTL retention and cold diorama return mid-climb | **duo harness, not bench**: the bench has no live talk lane. Each check must first be shown to fail with its fix removed. PROVEN on two PCs by the owner, 2026-10-27 (`GUEST-TRAVERSAL-TWO-PC.md`); the calibration-red duo legs were not run |
| R4 | The "!" at both sites + the refusal buzz | bench |
| R5 | The s95 relay split above | duo harness; two-machine Pandemonium lift |
| later | LOCO+LATCH (11 rows): only where every latch reader is a region or player gate | Ice Path 301 / Chocobo's Paradise 2955 |

## 5. Owner decisions

1. **Where the table lives.** It can be compiled into the DLL (CRCs only; `PROVENANCE.md` treats hashes
   as fine) or regenerated by the kit from the user's own install.
2. **The "!".** Show it only over interactions the guest can actually use? This applies to regions; NPCs
   are an open question.
3. **The window-first relayed regions.** Use the split above, or carry the guest along (riding lifts
   together)?
4. **Characters with no ladder clip** (Quina, Amarant, Freya, Eiko, the spectating moogle, Blank, Marcus,
   Cinna, Beatrix). Is the idle slide acceptable for them?
5. **Guest flavor talk** (same mechanism, NPC side). 694 stock NPC talks open windows and write nothing
   persistent, and 147 of them are gated only by mirrored story state, so the guest would see the host's
   text. It reverses the ratified spectator rule for one class. It composes with the s96 lock if those
   windows are classed Local at open and closed when the host's scene starts. FLAVOR+LATCH ("second time
   you talk" counters, 98) must stay refused, because a diverged counter makes later relayed talks pick a
   different line.
6. **A host battle starting mid-climb** gives a cold return at the host's entrance. Accept and log it, or
   hold the boot until the climb ends?
