# Battle co-op — EXECUTION PLAN (state-mirror lane → two-machine proof)

> **Written 2026-07-15, supersedes the "NEXT STEP 1/2/3" section of [`HANDOFF.md`](HANDOFF.md).** Read
> `HANDOFF.md` first for the narrative, then this file for the concrete, ordered task list. Everything
> here was checked against the CURRENT uncommitted engine code by a 6-way parallel verification pass
> (workflow `wf_9b4431f4-087`, 2026-07-15) that re-audited every claim in `HANDOFF.md` and
> [`state-mirror-lane.md`](state-mirror-lane.md) file-by-file, line-by-line. **Two days passed with zero
> changes** — `git log` on both the kit repo and the Memoria engine clone shows nothing new since the
> 2026-07-13 handoff commit, `Memoria.ini` still shows co-op disabled, and `backups/` still has no
> state-mirror backup. This plan is safe to execute as written; nothing has drifted underneath it except
> the two gaps below, which were always there and are now caught.

> **EXECUTION STATUS (2026-07-15):** Phases 0, 1a, 1b, 1d, 1e, and 2 are **DONE** — the kit test is
> committed, both engine bugs are fixed in the Memoria tree, the doc is corrected, and the rebuild
> shipped clean (0 errors; `NetSyncState`/`ApplyStoryTo`/`TypeState` confirmed in the binary; both
> deployed DLLs hash-identical to `Output\`; pre-build backups at
> `C:\gd\FFIX\Memoria\backups\Assembly-CSharp.dll.preSTATEMIRROR.{x64,x86}.20260715-014556`).
> **1c was deliberately skipped** (optional wire hygiene — deferred to a later patch round to keep this
> round's delta minimal). **NOW WAITING at the Phase 3 gate**: human solo playtest, then Phase 4 patch
> regen. Do not regen the patch before the solo proof passes.
>
> **Phase 3 round 1 (2026-07-15):** selftest line = **OK** on the new build (and it now certifies the
> real codec path, per 1a); the empty-command fix confirmed in-game ("Sword Art is absent"). The log
> also surfaced a **pre-existing** battle-intro race (NOT a regression — the unguarded
> `_abilityDetailDict[playerIndex]` in `CollectNetMenus` is in the committed s37 patch): `BuildRoster`
> polls before `InitialBattle()`→`ManageAbility()` seeds the dict → a caught `KeyNotFoundException` +
> `[NetSync] roster build failed` error block every roster tick (~4/battle) until the HUD initializes,
> then self-heals (the guest's Attack went through at 01:52:57). **Fixed same round** — new
> `BattleHUD.NetMenusReady(slot)` probe + a quiet `return null` guard in `BuildRoster` (identical wire
> behavior: no roster ships until ready; no exception spam) — and **rebuilt clean** (0 errors,
> `NetMenusReady` verified in the binary, deployed hashes match). Waiting on the round-2 solo check:
> one battle with a guest slot configured, expect ZERO `roster build failed` lines + working menus.
> These two hunks (`BattleHUD.Unity.cs`, `NetSyncBattle.cs`) join the Phase 4 regen set.
>
> **PHASES 3–5 CLOSED (2026-07-15).** Phase 3 round 2 was vacuous (no battle ran); round 3 proved it
> positively — zero `roster build failed`, zero error-level lines, selftest OK, and the guest's Attack
> (`peer command: slot 1 Attack`) went through the quiet roster path. **Phase 4 DONE**: s37 regenerated
> per the PATCH-EMIT LAW (pre-s37 baseline = detached worktree of `6b8bb2d5` + the full s12–s36 stack;
> s22 needed GNU `patch -F3`; diff emitted in an `autocrlf=false` scratch repo, committed pure-CRLF like
> the rest of the stack). Gates: forward apply onto the baseline == all 15 live files byte-identical;
> plain GNU `patch -R -p1 --dry-run -F0` clean against the live tree. Committed with the README.md stack
> entry updated. En route finding: **s35's second `BGSCENE_DEF.cs` hunk has drifted** (fails on a clean
> base+s12..s34 replay — pre-existing, outside the s37 set; flagged as a separate task). **Phase 5
> DONE**: `Desktop\FF9Coop-laptop-update-20260715\` — fresh v6 DLLs (hash-matched to the deployed
> engine), the unchanged coop test fields, and a rewritten README whose test list now leads with the
> state-mirror render-match/save-safety acceptance and a pre-install v5-vs-v6 fail-safe check.
> **NEXT = Phase 6, the two-machine session** (needs the laptop out). Then Phase 7 (party mirror → the
> battle diorama).
>
> **DESIGN UPGRADE (2026-07-15, user-driven): the in-place flag restore is REPLACED by the AUTOLOAD EXIT
> RAMP.** The user spotted that restoring the guest's own flags in place leaves them standing at the
> HOST's location — own story + host position = a frankenstate the base game can't produce (a
> sequence-break machine / softlock generator). New exit semantics: **leaving a mirrored session reloads
> the guest's OWN AUTOSAVE** (`NetSyncState.ExitMirrorToOwnSave` — `Serializer.Autoload` + the verbatim
> moogle-menu load transition; no autosave yet → title screen, like a game over). The autosave guard is
> what makes this correct: Continue stays pristine all session, so it IS the coherent pre-session
> (story, position, party) tuple — "leaving co-op = Continue" is stock semantics. Mechanics: link-drop
> arms the ramp DEBOUNCED (3s — a relay blip must not yank the guest); a deliberate config change arms
> it immediately; `_storyMirroring` stays true until the ramp fires so the manual-save block stays armed
> through the gap; the ramp fires only free-standing on a field/world map (never mid-battle/mid-warp);
> app teardown skips it (disk already coherent). The `_ownStory` capture/restore machinery is DELETED
> (the 1b capture-timing fix with it — the race no longer exists) and the fiddly capture-timing
> acceptance test is OBSOLETE. Built + deployed + s37 regenerated (16 files, gates clean).
>
> **THE SPECTATOR-FIELD PARADIGM (user-set, 2026-07-15):** the guest is a COMBAT participant and a
> field SPECTATOR — field walking is a purely flavorful experience (unless a need emerges), and the
> guest is not meant to INTERACT outside combat. Interaction authority is the HOST's alone. The
> implied future research arc — **"play the game without a player"** — is the guest's client rendering
> the host's interactions without a local driver: dialogue windows advancing on the HOST's confirms,
> chests opening because the HOST opened them, gateways firing off the host's movement (follow-warp
> already is this shape). The flip side (cheap, nearer-term): SUPPRESSING the guest's own field
> interactions while following (talk/chest/gateway inhibition) so a wandering guest can't advance or
> disturb the host's world. Noted, NOT scheduled — the battle diorama (B3) comes first.
>
> **★★ RUNG 2 CLOSED 2026-07-15 — TWO-MACHINE PROVEN on both axes.** Item mirror: guest with 0 Tents +
> host with a Tent → the guest activates the Tent moogle (the offer reads the HOST's bag). Party
> mirror: Ice Cavern **302**, the Vivi-required fire scene — the guest's field staged the party-gated
> content from the HOST's party. (User note en route: the Tent lives in the regular-items menu, not
> Key Items — the 75-field census list resolved the confusion.) NEXT = the final roadmap rung: the
> battle DIORAMA (B3) — its actor-spawn input now rides the wire.
>
> **RUNG 2 SOLO TIER ★ PROVEN 2026-07-15** — `party-mirror selftest: sections codec OK (4 members,
> 0 key items, 7 bag entries)`, zero errors. **THE ACCEPTANCE TARGET, byte-verified:** the Gate Pass is
> item-checked in EXACTLY ONE field in the whole game — **806 (S. Gate/Dali Gate)**, the gate guard's
> talk routine (fail = "you gotta have a Gate Pass"; pass = he opens the gate). Key-item id 16
> (menu/save-editor space) = generic script id 272 (important = 256+id). Every other South Gate booth
> (800-805/807) gates on STORY FLAGS only — folklore falsified by disasm. **THEN DOUBLY FALSIFIED by
> the full 806 decode:** the pass is never load-bearing even there — the tag-22 guard opens for ANYONE
> who answers Yes (talk twice: first talk = an instance-var-latched info line, second = the Yes/No; the
> "…I guess you do" is theater), the other side's guard is scenario-windowed, and the game's ONLY
> `have_item(272)` is a cosmetic pass-presenting gesture in the player sequence. Scan method
> (reusable): the fork-report raw-expr regex generalized — `\x7d(..)\x64` = B_CONST <u16> B_HAVE_ITEM,
> `\x7d(..)\x6b` = B_PARTYCHK — over every real field's `.eb`: 258 fields item-check, 230 party-check
> (the transcript/disasm renderers do NOT surface these tokens — raw bytes are the only reliable
> census). **THE REAL ACCEPTANCE TARGET: the moogle TENT offer** — `Tent = RegularItem 253` is the
> most-checked item in the game (138 fields ≈ every save-moogle screen): host with ≥1 Tent, guest with
> 0 → guest solo: no Tent offer from a moogle; guest FOLLOWING: the moogle offers the host's Tent →
> disconnect/ramp → offer gone. Binary, save-cheap, zero scenario interference.
>
> **PHASE 7 RUNG 2 — THE PARTY MIRROR (wire v7) — BUILT 2026-07-15, solo proof pending.** The state
> frame gains sections 1-3 (`NetSyncParty.cs`): **1 = the 4 party slots** (identity/looks/label stats
> per member — charId/serial/level/row/hp/mp/equip×5/name; EXACTLY the diorama's future actor-spawn
> input, zero throwaway) · **2 = key items** (`rare_item_obtained`) · **3 = the regular bag**. One frame
> = one consistent snapshot (`SnapshotAll`), parsed at the same field-load apply boundary. **Guest apply
> = the read-COMPARE wraps only** (no state mutation): `EventEngine.partychk` (B_PARTYCHK — the field's
> "is Vivi with you?" gate), EBin's `PARTY_MEMBER` varfunc, and the event item read (B_HAVE_ITEM →
> regular counts + key-item existence from the host; CARDS deliberately stay local) — so party/item-gated
> NPCs/doors/branches stage the host's way. **DELIBERATELY NOT WRAPPED: `ETb.GetPartyMember`** — it
> feeds the party-ACTOR SPAWN loop, and re-dressing the guest's own walking body is the diorama era's
> identity problem. Item WRITES by mirrored scripts land on the guest's real bag but are session-scoped
> by the exit-ramp architecture (no save + autoload exit). Session end → `NetSyncParty.Clear()`. New
> selftest line: `party-mirror selftest: sections codec OK (N members, K key items, M bag entries)`.
> s37 = **19 files** now (+`NetSyncParty.cs`, `EBin.cs`, `EventEngine.DoCalcOperationExt.cs`), gates
> clean; wire v6→**v7** (mixed DLLs don't sync — update both). Two-machine acceptance: host with a
> character/key item the guest lacks → a gated NPC/door on the guest stages per the HOST; guest solo
> replay after disconnect stages per their OWN save again.
>
> **★★ PHASE 6 CLOSED 2026-07-15 — every acceptance box two-machine PROVEN.** The final round: manual
> save refusal ✓ · Continue pristine through a followed session ✓ · **the AUTOLOAD EXIT RAMP ✓ on BOTH
> kill paths** (host bridge Ctrl+C and host game quit — the guest on 30110 landed back at their own Dali
> Continue spot in ~5s) · **automatic session resumption ✓** (host bridge restarted → re-pair,
> re-follow, re-mirror, no relaunch). The ramp's first execution found one real bug, fixed same day:
> `IsConnected` stays true when the HOST's bridge dies (the guest's own relay socket is fine) — peer-alive
> must read the keepalive-fed POSITION lane (`_socket.GetRemote().Valid`, stale ~2s after the host dies).
> THE LAW: **transport-up ≠ peer-alive; any session-end logic must gate on lane freshness, not
> IsConnected.** NEXT = Phase 7: party mirror (rung 2) → the battle diorama (B3).
>
> **PHASE 6 RESULTS (accumulating, 2026-07-15):**
> - ★ **Fail-safe PROVEN two-machine** (package step 0): v6 host + v5 laptop on the same field — visible
>   co-location but NO pairing, no crash, no half-state. Exactly the designed version-reject behavior.
> - ★ **RENDER-MATCH PROVEN two-machine — the headline** (field 354, Dali weapon shop, rotating cast):
>   the guest's cast re-stages to match the HOST's ScenarioCounter. The authoritative-host claim ("the
>   guest renders the host's story, not scenario-zero") is proven on real stock content.
> - **Expected-behavior note** (test methodology, not a bug): the host's F6 "Reload field" does NOT
>   re-stage the guest — the follow listener keys on the host's broadcast FIELD ID changing, and the
>   mirror applies at the guest's own field-load boundary. After an F6 ScenarioCounter edit, the guest
>   re-stages on its next real warp/entry (natural story play re-stages both sides on room entry).
> - ★ **V2 `[[coop]]` GATES PROVEN two-machine** — the Twin Altar (30110) completed by two real players,
>   including the held east-arch door (the one behavior mechanically impossible to test solo).
> - ★ **BATTLE CO-OP B0+B1 PROVEN two-machine** — "works the same as usual": spectate panel + guest
>   digit-menu commands over the real link behave exactly as the solo selftest tier did.
> - ★ **VISITOR-MODE FOLLOW-WARP PROVEN two-machine** — the last two-machine-only untested s37 piece;
>   the guest auto-warps to match the host's field transitions.
> - ⚠ **SAVE-SAFETY HOLE FOUND (the test paid for itself): AUTOSAVE bypasses the spectator-save block.**
>   The Continue slot is written by `EventEngine` at essentially EVERY field-load init
>   (`serializer.Autosave`, gated only by a hardcoded cutscene `noSave` ladder + `[SaveFile]` config) —
>   NOT by `SaveLoadUI.OnKeyConfirm`, so the manual-save block never sees it. A following guest's
>   Continue gets the host's mirrored story AND the followed-to field position. **Engine fix STAGED
>   (uncommitted, next DLL round):** `noSave |= NetSyncVisitor.SuppressEncounters ||
>   NetSyncClient.IsMirroringStory` — same conditions as encounter suppression (following + connected,
>   or selftest), fail-safe to vanilla on link-drop, host unaffected. `EventEngine.cs` JOINS THE s37
>   FILE SET at the next regen (16 files; it carries fork-fidelity edits — full-stack baseline replay
>   handles it). **Zero-rebuild mitigation for a live session:** `[SaveFile] DisableAutoSave = 1` in
>   the GUEST's Memoria.ini (stock Memoria, launch-time read → relaunch; kills ALL autosaves, so
>   revert after). Residual documented wart: a NON-following free-roam guest keeps vanilla autosave —
>   hanging out at a coop room parks their Continue there (same as any F6 warp; "make a real save
>   before co-op" stays in the README).

## TL;DR for whoever executes this (Fable)

- The uncommitted engine code matches the build spec closely: **all 5 wire-protocol claims, all 5
  client-logic claims, both small fixes (`SaveLoadUI.cs` save-block + `BattleHUD.Unity.cs` empty-command),
  and the csproj wiring are CONFIRMED correct or already shippable.**
- **Two real, fixable bugs surfaced during verification that `HANDOFF.md` didn't know about** (Phase 1
  below) — cheap to fix now (same DLL round, no extra rebuild cost), expensive to discover only after the
  scarce two-machine session:
  1. The solo "selftest" doesn't exercise the actual code path the two-machine session depends on.
  2. A narrow-window race can silently drop a few seconds of the guest's OWN solo progress.
- The patch stack genuinely needs regeneration (3 confirmed gaps) — do **not** skip it, and do **not**
  naively `git diff 6b8bb2d5..working` (see Phase 4's baseline-reconstruction warning — it would
  re-bundle 6 other patches' edits into "s37").
- Everything is still gated behind ONE dangerous, auto-deploying engine rebuild (Phase 2) that needs FF9
  closed first and a human to relaunch + playtest afterward. The local solo rebuild→relaunch loop is
  cheap to repeat if something's wrong; the **two-machine session is the actually scarce resource** (needs
  the laptop out, the user free, both machines updated in lockstep) — that's the reasoning behind fixing
  the two bugs below before spending it.

---

## Risk register (from the verification pass)

| # | Finding | Severity | Where | Action |
|---|---|---|---|---|
| 1 | Selftest never calls the real `ApplyStory` parse loop — hand-parses instead | **Real gap, fix before rebuild** | `NetSyncState.cs:110-131` | Phase 1a |
| 2 | `_ownStory` captured before first host snapshot arrives → guest's own progress in that window is silently lost on restore | **Real gap, fix before rebuild** | `NetSyncClient.cs:151-156` | Phase 1b |
| 3 | Host producer sends every 150ms unconditionally, no change-detect, no connected-gate | Wire hygiene only, not correctness | `NetSyncClient.cs:492-496` | Optional, Phase 1c |
| 4 | `NetSyncState.cs` never brackets `gScriptVector`/`gScriptDictionary` despite spec §6 | Inert (rung 1 doesn't write those containers) | `NetSyncState.cs` (whole file) | Document only, Phase 1d |
| 5 | `NetSyncRelay.ReadLoop` silently swallows a version mismatch (no log, no disconnect) vs `NetSyncSocket`'s explicit log+disconnect | Pre-existing asymmetry, not introduced by this change | `NetSyncRelay.cs:308-323` vs `NetSyncSocket.cs:473-479` | Document for Phase 6, optional harden later |
| 6 | No integration test for `coop host` forcing `FollowHost=0` end-to-end (only the lower-level helper is tested) | Low, cheap to add | `ff9mapkit/ff9mapkit/coop.py:451-455` | Phase 0 |
| 7 | Stale "wire-v3" doc comments in `NetSyncRelay.cs:16,310` | Cosmetic | — | Optional cleanup |

Everything else the verification pass checked (wire protocol version bump, `TypeState` frame type,
latest-slot state slot, both transports' `INetTransport` implementation, `ClearRemote` dropping
`_inState`, the `SaveLoadUI.cs` save-block, the `BattleHUD.Unity.cs` empty-ability fix, the csproj
`Compile Include`, the host-never-self-applies guard, the `_role != "host"` defense-in-depth, and the
`coop host → FollowHost=0` scoping) came back **CONFIRMED, no defects**. Full file:line citations are in
the appendix at the bottom of this doc.

---

## Phase 0 — kit-side test gap (independent track, no engine dependency, run any time)

Pure Python, zero risk, doesn't touch the Memoria tree. Can run before, during, or after everything else.

- Add a test in `ff9mapkit/tests/test_coop.py` that calls the actual `coop host` setup path (whatever
  the real entry point is — `_setup(role="host", ...)` or the CLI dispatch, not just the lower-level
  `playstyle_updates()` helper that's already covered) and asserts the written `Memoria.ini` gets
  `FollowHost = 0` by default, and that `coop join`'s equivalent path does NOT force it.
- Run `py -m pytest tests/test_coop.py tests/test_coop_gate.py -q` from `ff9mapkit/` — expect the existing
  36 passed / 4 skipped (skips are the normal "base templates not extracted" gate) plus your new test.
- Commit as a small standalone kit-side commit (`test(coop): cover coop host forcing FollowHost=0
  end-to-end`).

---

## Phase 1 — pre-rebuild hardening (agent-executable now, bundles into the ONE rebuild in Phase 2)

All edits are in the local gitignored engine clone `C:\gd\FFIX\Memoria\Assembly-CSharp\`. No build needed
to make these edits; the build in Phase 2 picks them up automatically since it's a full csproj rebuild.

### 1a. [Recommended] Make the selftest exercise the real `ApplyStory` codec path

**Why this matters:** `NetSyncState.SelfTest()` (`NetSyncState.cs:110-131`) currently calls
`SnapshotStory()`, then hand-parses the 3-byte section header itself and diffs directly against the live
array. It never calls `NetSyncWire.BuildFrame`/`TryParseHeader`, and never calls the real `ApplyStory`
function — because `ApplyStory` only has one overload and writes straight into the *live*
`FF9StateSystem.EventState.gEventGlobal` (`NetSyncState.cs:52-80`), so there's no scratch-safe way to
call it today. That means the section-walking `while` loop inside `ApplyStory` — the single most likely
place to hide an off-by-one, wrong-section-id, or bounds bug — is untested until the very first real
two-machine apply. The log line `"[NetSync] state-mirror selftest: gEventGlobal codec round-trip OK"`
(`NetSyncClient.cs:424-429`) currently certifies less than its own wording claims.

**Fix:** give `ApplyStory` a scratch-target overload (e.g. `ApplyStoryImpl(Byte[] frame, Byte[] target)`
that writes into `target` instead of the live array — the live-array call becomes a one-line wrapper
around it with `target = FF9StateSystem.EventState.gEventGlobal`). Rewire `SelfTest()` to:
`NetSyncWire.BuildFrame(NetSyncWire.TypeState, SnapshotStory())` → `TryParseHeader` → the real apply loop
→ into a fresh `Byte[2048]` scratch buffer → compare against the live array (masking 2032-2041 on both
sides, matching what `SnapshotStory()` already does). This proves the EXACT code path a two-machine
session depends on, solo, with zero risk to the live array.

### 1b. [Recommended] Fix the capture-timing race

**Why this matters:** `ApplyStoryImpl` (`NetSyncClient.cs:145-156`) captures `_ownStory` (guarded only by
`_ownStory == null`) as soon as the top gate passes — `_enabled && _followHost && _role != "host" &&
_socket != null && _socket.IsConnected` — which can be true for several ticks *before* the host's first
`TypeState` frame ever arrives (`GetRemoteState()` still null). During that window the guest is still
playing their own live game normally; any flag they legitimately set in it is never captured again
(`_ownStory` is one-shot, set-if-null) and is silently discarded the moment `RestoreLiveStory()` eventually
fires on disconnect/leave. Narrow window in practice (one connection round-trip), but a real, confirmed
data-loss bug, not a hypothetical.

**Fix:** defer the capture until the tick where a real host snapshot is actually about to be applied for
the first time (i.e. move the `_ownStory == null` capture to fire only once `GetRemoteState()` is non-null
— the same tick `ApplyStory` is about to do its first live write), or introduce a `_hasMirroredOnce` latch
so the capture and the first real apply are atomic. Either way: no legitimate guest state should ever be
overwritten before it's been captured.

### 1c. [Optional, low priority] Host producer change-detect / connected-gate

`NetSyncClient.cs:492-496` sends `SetLocalState(SnapshotStory())` unconditionally every 150ms whenever
`_role == "host"` and on-field — no dirty-check (unlike the roster lane's `BytesEqual` dirty-check,
`NetSyncBattle.cs:257`), and no gate on whether a guest is even connected/following. It works correctly
today because the guest-side apply gate drops unwanted frames — this is purely wire chatter, not a
correctness issue. Fix only if convenient; safe to defer to a later patch round.

### 1d. [Document only] `gScriptVector`/`gScriptDictionary` not captured

`NetSyncState.cs` only ever brackets `gEventGlobal`. The spec (`state-mirror-lane.md` §6) said "and
`gScriptVector`/`gScriptDictionary`" but its own justification (F6's `Snapshot()`/`RestoreSnapshot()`)
doesn't actually bracket those two containers either — they're only ever `.Clear()`'d elsewhere. This is
currently inert (rung 1 never writes to those containers), so no fix is needed yet. Just correct the
`state-mirror-lane.md` §6 text so a future reader doesn't assume coverage that was never real, and note it
as a rung-2+ item if kit/HW-scripted fields ever start relying on those containers.

### 1e. [Optional, cosmetic] Fix stale "wire-v3" comments in `NetSyncRelay.cs:16,310`

Both still say "Same wire-v3 frames..." unchanged through the v4→v5→v6 bumps. Update to "wire v6" (or
drop the version number from the comment) while you're in the file for 1a/1b. Zero functional impact.

---

## Phase 2 — the rebuild (DANGEROUS — auto-deploys with no backup)

Per `CLAUDE.md` §2/§4, the `building-the-memoria-engine` skill, and `state-mirror-lane.md` §12.

1. **Confirm FF9 is fully closed** (`Get-Process` for the FF9 process; the DLL is file-locked while
   running and the build silently fails to redeploy over a locked file).
2. **Back up both architectures' `Assembly-CSharp.dll`** from
   `<game>\x64\FF9_Data\Managed\` and `<game>\x86\FF9_Data\Managed\` to
   `backups\Assembly-CSharp.dll.preSTATEMIRROR.<timestamp>` — the build auto-deploys with **no** backup
   of its own; this is the only safety net.
3. **Build** (PowerShell, not bash — bash mangles the `/p:SolutionDir=` backslashes):
   ```
   msbuild Assembly-CSharp\Assembly-CSharp.csproj /t:Build /p:Configuration=Release /p:SolutionDir=C:\gd\FFIX\Memoria\ /m
   ```
   Confirm 0 errors. The `AfterBuild` step auto-copies the new DLL (+ `Memoria.Prime.dll` +
   `UnityEngine.UI.dll`) into both `Managed\` folders — building **is** deploying.
4. **Offline sanity check** (agent-doable, no game launch needed): grep the freshly-built
   `Memoria\Output\Assembly-CSharp.dll` for the new type-name strings (`NetSyncState`, `TypeState`) to
   confirm the new code actually landed in the binary, per the "offline verification" recipe in
   `project-ff9-memoria-build.md`.

---

## Phase 3 — first SOLO proof (human launches; agent reads the log)

1. **Human:** fully relaunch FF9 (a DLL change needs a real relaunch, not F6 reload).
2. **Human:** run `ff9mapkit coop host` (selftest role is fine — no laptop needed), enter any field.
3. **Human:** also manually retest the empty-command fix while here — pick a character with an
   all-unlearned Ability command (e.g. Steiner's Sword Art with nothing learned) via the selftest's own
   assist-menu digits and confirm it's simply **absent** from the menu (not present-then-dead-end).
4. **Agent:** read `Memoria.log` and grep for `[NetSync] state-mirror selftest:` — report the exact line
   (`OK` vs `MISMATCH`) rather than asking the human to interpret it. With Phase 1a done, this line now
   actually certifies the real `ApplyStory` parse path, not just the header math.
5. If `MISMATCH` or anything looks wrong: **do not proceed to Phase 4/5.** Fix and repeat Phase 2-3 — this
   loop is cheap (no laptop needed).

---

## Phase 4 — patch regeneration + commit

**Confirmed gaps in `memoria-patches/s37-netsync-battle.patch`** (from the verification pass) — none of
these appear in ANY patch in the stack yet:
- `Global/SaveLoadUI.cs` — the whole save-block hunk is new, zero hits across all `.patch` files.
- `Memoria/Netsync/NetSyncState.cs` — new file, zero hits; its csproj `Compile Include` line is also
  absent from s37's csproj hunk (s37's hunk only adds `NetSyncBattle.cs`/`NetSyncVisitor.cs`).
- `Global/battle/BattleHUD/BattleHUD.Unity.cs` — the working tree's diff is ~24 lines longer than s37's
  existing hunk for the same file (the empty-ability-skip fix landed after s37 was last emitted).
- Plus whatever Phase 1a/1b/1c/1e touched.

**⚠ Regen recipe — do NOT naively `git diff 6b8bb2d5..working`** for these files. `SaveLoadUI.cs`,
`BattleHUD.Unity.cs`, `NetSyncRelay.cs`, and the `.csproj` already carry OTHER patches' edits (s21/s22/s36
etc.) — a full diff against base `6b8bb2d5` would re-bundle those prior patches' hunks into "s37" and
double-apply them on a clean checkout. Per the PATCH-EMIT LAW (`project-ff9-multiplayer-injector.md`,
search "PATCH-EMIT LAW"):
1. For each already-patched file, reconstruct its **pre-s37 baseline** by surgically removing just the
   s37-authored lines from the current content (not by diffing against `6b8bb2d5` directly).
2. Diff that reconstructed baseline against the current file to get the true incremental s37 hunk.
3. Use a **byte-exact** script for this, not a naive text-mode subprocess — several files in the stack
   (`NetSyncRelay.cs` at minimum) are CRLF, and Python subprocess text mode silently eats `\r`, corrupting
   the patch. The prior round's pattern lived at `scratchpad make_s37_patch.py` — same approach.
4. **Gate:** reverse-apply the emitted patch against the live tree and confirm it lands byte-identical to
   the working copy before trusting it (`patch -p1 --dry-run -F3`, not `git apply --3way` — `-F3` tells
   true overlap from CRLF/offset/intra-stack drift per `project-ff9-memoria-conflict-forensics.md`).
5. Commit the regenerated `memoria-patches/s37-netsync-battle.patch` to the Dream-World-IX repo, plus the
   Phase 0 kit-side test and the Phase 1d doc fix.

---

## Phase 5 — re-cut the laptop update package

Wire bumped v5→v6 — **old peers simply won't sync at all** (fail-safe by design, confirmed in Phase-2's
verification: `TryParseHeader` rejects a version mismatch on both transports, though see risk #5 above for
the relay-transport asymmetry). Re-cut the `FF9Coop-laptop-update` package with the freshly-built
`Assembly-CSharp.dll` (both architectures) — **both machines must update together**, or they silently
don't pair.

---

## Phase 6 — two-machine validation (needs the laptop out; per `state-mirror-lane.md` §11 + one addition)

1. **Render-match (the headline proof):** host warps to a field with a ScenarioCounter/flag-gated NPC or
   door; the following guest must see the SAME state (not their own scenario-zero version). Check at a
   couple of different story beats.
2. **Room-to-room render-match:** host moves room to room; each room renders the host's actual state on
   the guest's screen. (Sequential follow-warp ITSELF is already validated from 2026-07-13 — this test is
   specifically the render-match, which needed the lane built.)
3. **Save-safety:** after a session, confirm the guest's OWN save is unchanged; a mid-field link-drop
   reverts the guest cleanly; a save attempt while following is refused with the deny beep.
4. **NEW — capture-timing spot-check (added from Phase 1b's fix):** have the guest take a quick, real
   action (open a menu, move a few steps causing a flag write if any is easy to trigger) in the brief
   window right as they enable follow, then disconnect and confirm THAT action, not just their
   pre-session state, survives the restore. This is the acceptance test for the bug Phase 1b fixed.
5. **Fail-safe:** a v5 (old-DLL) peer + a v6 host simply don't sync — no half-state, no crash. **Note risk
   #5:** if testing over the relay transport specifically, a version mismatch may present as a
   connection that just never pairs (no explicit log/disconnect on that transport) rather than an obvious
   rejection — don't mistake it for a new bug; confirm both machines' DLLs match first.

---

## Phase 7 — roadmap forward (only after Phase 6 lands; unchanged from `HANDOFF.md`)

1. **Party mirror (rung 2)** — extend the same state-mirror lane with the party section (section 1 in the
   wire format) — it's felt on the field AND is the diorama's actor-spawn input.
2. **The battle diorama (B3)** — boot the host's battle on the guest via `BattleMapDebug`, spawn the
   mirrored party, drive from the existing B0 state stream. NEVER re-simulate (the unseeded-RNG dead-end).
   **★ RECON PASS 1 DONE 2026-07-15** (8 questions, source-grounded + adversarially verified) → the full
   spec is **`diorama-lane.md`**. It inverted this rung's own premise: **`isDebug` is a TRAP, not a
   render-only switch** — a dead flag nothing ever sets, gating only the sim's INPUT half while
   `ManageBattleEnd → SavePlayerData` writes the guest's REAL party **every frame** (IsOver is itself
   isDebug-gated, so the battle never ends). **THE CONTAINMENT LAW: save-safety comes from an explicit
   13-lane suppression set, never from `isDebug`; containment is rung ZERO — nothing renders until the
   guest's save is provably untouchable.** Ladder: B3.0 containment → B3.1 boot+return → B3.2 mirrored
   party (carry `basis`, NOT `max`) → B3.3 enemies → B3.4 truth → B3.5 action playback → B3.6 UI merge.
   Choke point = `SBattleCalculator.CalcResult:310`.
   **★★ THE DIORAMA IS TWO-MACHINE PROVEN 2026-07-16 — host battles PULL THE GUEST IN** (B3.0-B3.3;
   en route: the B3.3b silent-chain telemetry + gate relaxation, and B3.3c's TICK-BASELINE LAW —
   TickCount wraps negative at 24.86 d uptime; the 25-day laptop was the whole two-machine failure).
   Known cosmetic: the F6 opt-out replays the intro once (filed, not chased). B3.3 shipped the boot block
   ON the type-1 header (latest-slot, not the recon's FIFO frame — late-join free, staleness = the
   close signal, a nonce for chained fights) + the guest watcher (`[Netsync] Diorama`, default on) +
   `debugStartType`/`isRandomEncounter` carried and bracketed. En route: the diorama never arms gMode
   (isDebug skips StartEvents) so the B1 assist menus stay usable over it — most of B3.6 early; the
   STACKED-STALENESS law; the Boot-refuses-without-a-snapshot containment fix. Two-machine checklist =
   the laptop package `FF9Coop-laptop-update-20260716`. NEXT: B3.4 (drive HP/death/trance from type-1),
   then B3.2b party v9 riding B3.5's action lane; emit the arc as s40.
3. **Cutscene-drive** — the documented research frontier (host streams window-close / chosen-choice /
   tread-fired events, guest force-applies). Not scheduled.
4. **Federated `[[coop]]` custom modes** — parked until the authoritative-host headline is solid.

---

## Appendix — verified file:line map (2026-07-15 pass, workflow `wf_9b4431f4-087`)

Wire protocol (`NetSyncSocket.cs` / `NetSyncRelay.cs`):
- `Version = 6` — `NetSyncSocket.cs:67`
- `TypePos=0 TypeBattle=1 TypeCommand=2 TypeControl=3 TypeRoster=4 TypeState=5` — `NetSyncSocket.cs:71-76`
- `_outState`/`SetState`/`CollectOutgoing` keepalive — `:157`/`:181`/`:203`
- `_inState`/`_inStateTick`/`GetState()` (2000ms stale) — `:169-170`/`:240-243`/`:289-297`
- `INetTransport.SetLocalState/GetRemoteState` — interface `:39,:44`; `NetSyncSocket` impl `:385-388,:399`;
  `NetSyncRelay` impl `:114-117,:128`
- `ClearRemote()` drops `_inState` — `:305-316` (`:313`); called from both transports' disconnect paths
  (`NetSyncSocket.cs:458`, `NetSyncRelay.cs:169`)

Client logic (`NetSyncClient.cs` / `NetSyncState.cs`):
- Host producer (150ms cadence, no change-detect) — `NetSyncClient.cs:492-496`
- Guest apply gate — `:149` (`_enabled && _followHost && _role != "host" && _socket != null &&
  _socket.IsConnected`)
- Masked copy / fresh read — `NetSyncState.cs:70-76` / `:56-58`
- Spectator-save enter/leave — enter `NetSyncClient.cs:151-152`; leave via config-toggle `:272`,
  disconnect `:402-406`, teardown `OnDestroy():565`
- `CaptureLiveStory`/`RestoreLiveStory` — `NetSyncState.cs:85-95`/`:97-106`
- Selftest — `NetSyncClient.cs:424-429` (log line); `NetSyncState.cs:110-131` (the untested-parse-loop gap)
- Host-never-self-applies — `ApplyStoryImpl` requires `_role != "host"` at `:149` (same gate)

Field-load hook (`HonoluluFieldMain.cs`):
- `ff9InitStateFieldMap`, lines 133-137 — `NetSyncClient.ApplyStoryBeforeEvents()` called at line 135,
  immediately before `StartEvents` at 136 (NOT literally inside `HonoAwake`, which only calls
  `NetSyncClient.Ensure()` at `:29` — this is the spec's own documented fallback placement and is correct).

The two small fixes:
- `SaveLoadUI.cs` save-block — `OnKeyConfirm`, lines 145-158 (`IsMirroringStory` guard); known/accepted gap
  at `Show():52-60` (`aaaaPlatform` quicksave path, PC out of scope).
- `BattleHUD.Unity.cs` empty-ability skip — `CollectNetMenus`, lines 734-750 (`anyLearned` check via
  `AbilityStatus != None`, correctly keeps learned-but-`Disable`d commands).

csproj / patch stack:
- All 6 `Memoria/Netsync/*.cs` files have matching `Compile Include` lines — nothing silently uncompiled.
- Patch gaps confirmed: `SaveLoadUI.cs` (new hunk), `NetSyncState.cs` (new file + csproj line),
  `BattleHUD.Unity.cs` (~24 extra lines) all absent from `s37-netsync-battle.patch`.

Kit side (`ff9mapkit/ff9mapkit/coop.py`):
- `coop host` forces `FollowHost=0`, scoped to `if role == "host":` — lines 451-455; `coop join` path
  (`role != "host"`, lines 447-448) never touches it.
- `tests/test_coop.py`: 25 tests, only the lower-level `playstyle_updates()` helper covers this (lines
  74-80) — no end-to-end `_setup(role="host")` test (Phase 0 closes this).
- Targeted run `py -m pytest tests/test_coop.py tests/test_coop_gate.py -q` → **36 passed, 4 skipped**
  (skips = no local install templates extracted, expected).
- `C:\gd\FFIX\Memoria\backups\` has exactly one file (`WMWorld.cs.20260704-102452`) — confirms the
  state-mirror rebuild has not been attempted yet.
