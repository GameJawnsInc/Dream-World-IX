# F1 — the build spec (synthesized 2026-07-20 from the 12-agent recon-verify workflow `wf_86eb27dc`)

> The decision layer for round F1's implementation. Supersedes DESIGN.md §§1/2a/4/6 details where they
> conflict — every deviation below is evidence-driven and recorded. The six recon lanes + adversarial
> verifiers are archived in the session scratchpad (`f1recon/*.json`); the load-bearing corrections are
> restated here so this file stands alone.

## Ratified frame decisions

1. **ONE suppression predicate for every F1 gate** — `NetSyncField.SpectatorField`:
   `NetSyncClient.IsLiveFollowedSession || NetSyncClient.IsMirroringStory || (NetSyncClient.IsSelfTestRole && NetSyncField.BenchGates)`.
   The union closes BOTH windows the single predicates leave open: pre-mirror (paired but no field
   load yet → IsLiveFollowedSession true, mirror false) and post-link-death-pre-ramp (lane stale →
   IsLiveFollowedSession false, mirror still true, world still holds host story). All conjuncts
   default false = fail-safe vanilla. The s38-era gates (ENCOUNT/ENCOUNT2, UIKeyTrigger 489/531/678/834,
   AchievementManager 110, SaveLoadUI) stay on bare `IsMirroringStory` — NOT retouched this round.
2. **The bench lever** — `NetSyncField.BenchGates` (static bool, default false), toggled ONLY from the
   ~ debug menu (Go tab, rendered only when `IsSelfTestRole`). No new `[Netsync]` knob (the
   Diorama-knob verdict). Ordinary selftest sessions stay vanilla (BenchGates off) — the
   interaction-lane's bare-`IsSelfTestRole` spec is REJECTED for exactly that reason.
3. **Manual teleport** gates on `IsLiveFollowedSession || IsSelfTestRole` (no BenchGates needed — a
   deliberate keypress, zero-friction solo testing; F11 is unclaimed so consuming it is harmless).
4. **ATE achievement fix: SHIP NOTHING** — REFUTED by the source walk: `ETb.cs:419 →
   EMinigame.ATE80Achievement :526 → AchievementManager.ReportAchievement :88 →
   ProcessAchievementReport :110` which s38 already gates. All ~90 ReportAchievement call sites funnel
   through it; the only native Social calls sit downstream (`SiliconStudio\Social.cs:134`,
   AchievementManager :123/:130). Any new gate would be dead code.
5. **Exit-ramp escape sweep: nothing new** — the snapshot leak (below) is the only genuine escape;
   debug-menu PlayerPrefs/obj-dump writes are settings/dev-export state, not story.
6. **Auto-TP separation signal = distance floor ONLY** (camera-window read deferred with the camera
   arc; per-map vrpMin/Max projection is hairy and camera work is ratified-deferred).

## THE GATEWAY REDIRECT (supersedes DESIGN §2a's suppress+watchdog — the round's design change)

**Why the ratified design died:** suppressing MAPJUMP with `return 0` (the s38 ENCOUNT clone) makes
the VM continue into post-`Field()` bytes that are UNREACHABLE in normal play (real MAPJUMP returns 4
→ `adfr`→`adFin` halts the VM and tears the field down; EBin.cs:172/223). The ENCOUNT precedent does
not transfer (post-Battle bytes are the designed continuation; post-Field bytes are dead code).
**Empirical census (2026-07-20, 817 HW field-script exports, 7,181 `Field()` calls):** followers are
`case` ×2498, `return` ×1926, `}` ×1569, `break` ×952, `set VAR…` ×175, `TerminateEntry` ×42, misc
×17, **`while(1)` ×2** — over 60% continue into live code and at least two real fields would
infinite-loop. Fall-through is refuted as a mechanism.

**The replacement — redirect, don't suppress:**
```
case MAPJUMP:  // 0x2B "Field"
    Int32 dest = this.getv2();                       // consumed FIRST (gArgUsed trap)
    if (Memoria.Netsync.NetSyncField.SpectatorField && dest != FF9StateSystem.Common.FF9.fldMapNo
        && dest != Memoria.Netsync.NetSyncClient.LastHostField)
    {
        Memoria.Netsync.NetSyncField.DeclineOnce("gateway");
        dest = FF9StateSystem.Common.FF9.fldMapNo;   // bounce: same-field reload
    }
    this.SetNextMap(dest);
    return 4;
```
- The instruction flow is **byte-for-byte vanilla** (SetNextMap + return 4) — only the VALUE differs.
  Post-Field bytes stay unreachable exactly as in normal play. No watchdog, no fade bookkeeping: the
  script's own fade flows into the reload's load, which fades back in and restores control itself.
- The same-field reload is the PROVEN primitive (the ~ menu "Reload field" button and the s42
  same-field kick are exactly `SetNextMap(current)`), it wipes the MOVQ collision-flag residue
  (`flags |= 6` on every object — verify find), and re-arms the story mirror at the load boundary.
- **The follow allowance:** `dest == LastHostField` lets the jump through untouched — if the host is
  already standing on the destination, the guest's gateway IS the follow (better arrival positioning
  than the follow-warp). `LastHostField` is a new cached static on NetSyncClient (updated each Update
  from `rs.Valid ? rs.Field : -1`; -1 in selftest/stale → bench always bounces).
- `dest != current` guards a genuine same-field scripted Field(current) (rare; leave it vanilla).
- Known accepted consequences: the guest bounces to the field's default entry (auto/manual TP brings
  them back to the host in seconds); the both-walk-through-together case costs one extra reload when
  the guest treads the region before the host's new field hits the wire; a spawn-inside-gateway
  insta-refire loop is believed impossible in shipping data (every real field spawns beside a door
  without refiring) — **flagged for the solo bench + playtest**.
- WMAPJUMP (0xB6, world-map exit) stays un-gated — world map is a ratified FRONTIER. The battle-script
  `Change next field` (btl_scrp.cs:839) is noted to the diorama lane, out of F1 scope.

## Per-file edits

### NEW `Memoria/Netsync/NetSyncField.cs` (+ csproj line after :1388)
`public static class NetSyncField`:
- `public static Boolean BenchGates;` — the ~-menu dev lever.
- `public static Boolean SpectatorField { get { try { return NetSyncClient.IsLiveFollowedSession || NetSyncClient.IsMirroringStory || (NetSyncClient.IsSelfTestRole && BenchGates); } catch { return false; } } }`
- `public static void DeclineOnce(String what)` — latched telemetry keyed on `(what, fldMapNo)`:
  `static Dictionary<String,Int32> _lastDeclineField;` — logs
  `[NetSync] <what> suppressed (following guest) on field N` once per gate-class per field.
  fldMapNo read in try/catch. No TickCount anywhere (TICK-BASELINE n/a by construction).
- `public static Boolean TeleportKeyPressed()` — F11 `GetKeyDown` OR held-L3: `KeyCode.JoystickButton8`
  accumulated with `Time.deltaTime` (`_l3Hold`/`_l3Fired` statics, `HoldSeconds = 0.7f`); resets on
  release. MUST be invoked unconditionally each UIKeyTrigger.Update pass (the call is the condition).
  L3==JoystickButton8 is a needs-in-game confirm; F11 is the always-available fallback.

### `Memoria/Netsync/NetSyncClient.cs`
- `internal static Int32 LastHostField = -1;` — set in Update's real-coop tick (`rs.Valid ? rs.Field : -1`),
  forced -1 in the selftest branch and on teardown/ApplyConfigChange (no stale host field survives).
- **Manual TP**: `public static void RequestTeleportToHost()` — static forwarder guarding
  `_instance == null` (IsSelfTestRole does NOT imply an instance — verify find), then instance body:
  - Refuse (each via a latched decline reason, reset on success): UIState != FieldHUD ·
    `!ee.GetUserControl()` · `_followWarpPending >= 0` · no control Actor / no fieldmap.
  - SELFTEST arm (`IsSelfTestRole`): target = `me.fieldMapActor.transform.localPosition + (_selfTestDx, 0, _selfTestDz)`
    (the mirror the selftest branch renders at :700) → SnapToHost. NEVER touch `_socket` (null in selftest).
  - LIVE arm (`IsLiveFollowedSession`): `rs = _socket.GetRemote()`; `!rs.Valid` → latched refuse.
    Same field → `SnapToHost(rs.Pos)`. Different field → pre-check
    `EventEngineUtils.eventIDToFBGID.ContainsKey(rs.Field)` (else latched "not on this install" —
    FollowHostTick's own decline at :1105 is silent) → re-arm the follow: `_followWarpedTo = -1;
    _followCandidate = rs.Field; _followCandidateSince = Environment.TickCount - FollowStableMs;`
    (next FollowHostTick fires the fade+warp; do NOT duplicate warp logic).
- **`private void SnapToHost(Vector3 hostPos)`** — snap through **`ee.fieldmap.playerController`**
  (populated on ALL spawn paths; `local.fieldMapActorController` is null on the AddPlayer path —
  verify find), null-guard + latched log, `SetPosition(hostPos, true, true)` (Y-aware nearest-floor;
  keep SetPosition-only — do NOT poke pos[]/lastx, HonoLateUpdate handles it — verified non-issue).
  One log line per fire.
- **Auto-TP**: `private void AutoTeleportTick(Actor local, Vector3 hostPos, Boolean benchArm)` with
  its OWN try/catch (an unguarded throw at this call site starves the diorama Pump downstream via the
  Update-level catch — verify find). Called from BOTH sites (the selftest branch returns at :713
  before the real-coop block — the single-site spec was structurally unbenchable, verify find):
  - real-coop same-field branch end (~:790): `AutoTeleportTick(local, rs.Pos, false)`;
  - selftest branch (before :713): `AutoTeleportTick(me, stMirror, true)`.
  Scope: `benchArm ? (IsSelfTestRole && NetSyncField.BenchGates) : IsLiveFollowedSession`.
  Predicate (all conjuncts, else reset dwell): `sep = Vector3.Distance(hostPos, gp)` >
  `AutoTpDistanceFloor` · not busy (`!ee.GetUserControl()` OR `UIManager.Dialogs.Visible`
  (null-guarded) OR `State != FieldHUD` ⇒ busy) · steering = component-wise stick thresholds +
  Control.Up/Down/Left/Right (the engine's :612-615 form, NOT `.magnitude` — verify find); steering
  holds the fire below `AutoTpHardCap`, above it softlock-recovery wins. Dwell `AutoTpDwellMs` then
  fire (SnapToHost + log, `sep` in the line) with `AutoTpCooldownMs` cooldown. Constants (playtest
  seeds, not laws): floor **640f**, hardCap **1200f**, dwell **4500**, cooldown **10000**. Tick
  fields use field-initializer baselines (`= Environment.TickCount - 100000` for the pre-expired
  cooldown; `_autoTpSeparated` bool guards `_autoTpSeparatedSince`) — the file's :101/:114 idiom.
  Latched hold-log when steering is the only blocker (`_autoTpHoldLogged`, reset when the hold clears).

### `Global/Event/EventCollision.cs` (first-ever patch hunks — clean baseline snapshotted)
- `CheckQuadInput` — first statement inside the `IsQuadTalkable` block (:67, before the Request calls
  :69/:75): `if (NetSyncField.SpectatorField) { NetSyncField.DeclineOnce("chest/quad"); return false; }`
- `CheckNPCInput` — first statement inside the angle block (:96, before `listener` :98 / Requests
  :101/:108): same shape, `DeclineOnce("npc-talk")`.
- Deep placement = logs only on a genuine attempt. Tag-2 push/tread (:277-284) untouched by
  construction. Covers the QuadMist card START (Request(…,8) at :69/:101) too. The gates also fire in
  gMode==3 (overworld) — ACCEPTED + documented: a following guest doesn't act there either; fails safe.

### `Global/Event/Engine/EventEngine.DoEventCode.cs` (carries s30/s38 hunks)
- MAPJUMP (:1008-1012): the REDIRECT (above).
- MENU 0x75 (:2297-2311): after BOTH `getv1()` (:2299-2300), before the DisableNameChoice block:
  `if (NetSyncField.SpectatorField) { NetSyncField.DeclineOnce("menu-opcode"); return 0; }` —
  return 0 here is SAFE (post-Menu bytes are the designed continuation; the in-opcode
  DisableNameChoice `return 0` at :2306 is the shipping precedent). Covers Menu(4,0) save,
  Menu(2,·) shops, name entry, chocograph. PARTYMENU 0xB2 / MINIGAME 0xAE stay un-gated
  (player-initiated starts are covered by the Check*Input gates; DESIGN scoped the rest out).

### `Global/UI/UIKey/UIKeyTrigger.cs` (carries s21/s22/s37/s38/s43 hunks — s43 moved the seam)
- Insert after the s43 BackQuote block's closing brace (:174), before the s37 comment (:175):
```
if (Memoria.Netsync.NetSyncField.TeleportKeyPressed())
{
    if (PersistenSingleton<UIManager>.Instance.State == UIManager.UIState.FieldHUD
        && (Memoria.Netsync.NetSyncClient.IsLiveFollowedSession || Memoria.Netsync.NetSyncClient.IsSelfTestRole))
        Memoria.Netsync.NetSyncClient.RequestTeleportToHost();
    return;
}
```
  (TeleportKeyPressed is evaluated unconditionally so the L3 accumulator advances every frame.)

### `Global/UI/UIKey/Ff9mkDebugMenu.cs` (carries s22/s40/s43 hunks)
- **Snapshot taint fix** (the one §6 code change): `private Boolean _snapshotMirrored;` beside
  `_snapshot` (:100); stamp in `Snapshot()` (:2248-2254) after the copy:
  `_snapshotMirrored = NetSyncClient.IsMirroringStory || NetSyncClient.IsSelfTestRole;`
  (IsSelfTestRole = the ONLY solo-bench arm — the mirror never arms in selftest); refuse in
  `RestoreSnapshot()` (:2256-2266) after the null-check, before the copy-back:
  stamped && now neither mirroring nor selftest → discard (`_snapshot = null` greys the button via
  the :955 label), `_status` explains, one `[NetSync]` log line. Restore-while-mirroring proceeds
  (harmless: save blocked, next load re-mirrors); own-story snapshots restore as today. Contained
  entirely in the menu — the NetSyncClient ramp block is NOT touched (a clear-at-ramp would need the
  stamp anyway + a nullable cross-object reference; strictly worse).
- **BenchGates toggle**: in DrawGoField, a button rendered only `if (NetSyncClient.IsSelfTestRole)` —
  label `Field gates bench: ON/OFF`, flips `NetSyncField.BenchGates`, logs the flip.

## Solo bench recipes (the checklist IS code — keep claims honest)
`[Netsync] Enabled=1, Role=selftest, FollowHost=1`; relaunch; ~ menu → the bench toggle ON.
1. **Interaction gates**: walk to any NPC/chest/save-moogle, press Confirm → nothing opens, ONE
   `[NetSync] npc-talk suppressed…` line per gate-class per field. Toggle bench OFF → vanilla again.
2. **Gateway redirect**: walk into a gateway → the screen fades as normal but the SAME field reloads
   (bounce to entry), one `gateway suppressed` line, control returns after the load. Bench OFF →
   the gateway warps normally. (Watch for: any insta-refire loop at the spawn.)
3. **Manual TP**: press F11 (bench toggle NOT required) → player snaps +250 east onto the mirror
   ghost (SelfTestOffset default). On a narrow field the snap may resolve to the walkmesh origin
   (off-mesh fallback) — the bench criterion is "relocated + refloored", not "on the ghost".
4. **Auto-TP**: set `SelfTestOffset = "800,0"` (sep 800 > floor 640), bench ON, stand still ~4.5s →
   snap + log; repeats each ~10s (cooldown proof). Hold a movement key → held-log, no fire; set
   `"1300,0"` → fires even while steering (hardCap proof).
5. **Snapshot taint**: bench state irrelevant; Role=selftest → Flags tab Snapshot → set
   `Enabled=0` (hot-reload) → Restore → refused + discarded + status line. (Solo proves the
   PREDICATE only; the real leak closure is a two-machine acceptance box.)
6. **MENU opcode**: needs a field script that calls Menu() spontaneously — covered implicitly by the
   savepoint moogle talk being gated at the funnel; the opcode gate's real proof is two-machine
   (mirrored script). Mechanism-smoke only.

## Two-machine boxes — RUN 2026-07-23 (desktop host + laptop guest, real link)

★ PASS — real-guest interaction block (bench green ≠ proof — `GetUserControl` reachability for a
followed guest is no longer needs-in-game, it's proven) · ★ PASS — gateway redirect + follow-allowance
on the real link (new nuance: simultaneous same-door entry — see the session section below) ·
★ PASS — manual TP, F11; **L3 (held ~0.7s, `JoystickButton8`) is STILL UNTESTED on the live pad**,
carries forward as OPEN · ✗ FAILED ACCEPTANCE — auto-TP (intermittent fire + a session-drop crash
window, see below; default-OFF pending a rework) · ★ PASS — snapshot leak end-to-end (Snapshot while
mirroring → ramp → Restore refused → manual save writes OWN story) · the standing s41/s42 leftovers
(tick numbers · Plant Brain · Feather Boots · host-silent bench · a Workspace-tab session) — NOT
exercised this session, still queued.

Full session narrative → **★★ TWO-MACHINE SESSION 2026-07-23** below.

## Verify-round outcomes (2026-07-20 — 7 skeptics `wf_e66632e8`, repairs re-verified `wf_7c682de1`)

**Verified sound (the trail):** the redirect's transition mode — the opcode path's `return 4` reaches
`HonoluluFieldMain.FF9FieldMapMain` case 4 which supplies `nextMode=1`/`attr|=8u` itself, so the
bounce is byte-identical to a vanilla gateway transition and equivalent to the ~-Reload/s42 kick
(the C# callers set those manually only because they bypass ServiceEvents). MENU `return 0` and both
EventCollision early-returns leave no half-set state. `LastHostField` is re-derived every real-coop
tick — staleness refuted.

**Repairs landed after the round (spec deltas, code is authoritative):**
1. **The BOUNCE BUDGET** (`NetSyncClient.RedirectGuestFieldJump`, the redirect decision moved out of
   the opcode): a field whose script auto-calls `Field()` (auto-transition corridors) would have
   bounce-looped forever when the host was elsewhere/unreachable. Three consecutive bounces on one
   field inside 20s → the jump is let THROUGH once (logged; vanilla self-navigation, follow-warp
   corrects it later). A user re-treading a door at human pace never accumulates.
2. **Auto-TP regains DESIGN's "gap keeps GROWING" qualifier**: steering past the hard cap only loses
   to recovery when sep has widened ≥100u since the dwell armed (`_autoTpArmSep`) — a guest simply
   exploring a big scrolling field is never yanked. A steering-read failure now HOLDS instead of
   firing (positive containment). `SnapToHost` returns `SetPosition`'s real verdict; an off-mesh
   host position logs honestly ("landed at the default spawn") and stamps the cooldown.
3. **The teleport intercept is SESSION-GATED** before the key read — a vanilla install never reads
   or consumes F11/L3 (the short-circuit keeps the L3 accumulator dormant outside sessions).
4. **Snapshot stamp**: `IsMirroringStory || OwnSaveReloadInFlight || (IsSelfTestRole && BenchGates)`.
   `OwnSaveReloadInFlight` (new static) closes the exit ramp's ASYNC window (mirroring already false
   while the array still holds host story until the autoload lands; set at the ramp, cleared at any
   field load + OnDestroy). The BenchGates qualifier un-taints plain selftest flag work (a shipping
   dev workflow). The refuse deliberately does not exempt the in-flight window.
5. **DeclineOnce gate-class strings as shipped**: `chest/quad interaction` · `npc talk` ·
   `script menu` · `gateway (bounced to a reload)`.

**Accepted + documented (no code):** the redirect intercepts ALL self-navigation including mirrored
cutscene `Field()` advances (bounce → follow-warp; watch for a visible hitch) · gate decay after link
death runs ~5s (staleness + ramp debounce), not ~2s — correct, the world still holds host story ·
auto-TP is dormant on single-screen fields (sep can't reach 640) — it exists for scrolling fields ·
the exotic tainted-buffer-across-role-switch edge (4 deliberate reconfigure steps) — accepted.

**Playtest watch list:** spawn-inside-gateway refire after a bounce · mid-cutscene bounce hitch ·
the auto-transition let-through · an origin-drop (off-mesh snap) landing inside a gateway quad ·
L3 == JoystickButton8 on the live pad.

## ★ SOLO BENCH 2026-07-20 — 6/6 PASS + the accepted hole surfaced and CLOSED same session

All six recipes passed first run (gates · gateway bounce · toggle-off vanilla · F11 snap · auto-TP
(user: "seems good", more on the laptop) · snapshot refuse). The ONE finding: **a Phoenix Down
ground pickup on field 206 was lootable** — the Decision-4 accepted hole (stock loot/chests = tag-2
tread bodies polling Confirm INSIDE the script, invisible to the Check*Input funnel) surfaced on the
first playtest, which is exactly the trigger Decision 4 named for building the closure.

**THE KEYON MASK (built + deployed same session, DLL `7F3E17BAF6EC0401`):**
`NetSyncField.FilterScriptButtons` strips `Confirm|Special` (0x20000|0x80000) from the script-visible
button reads — `B_KEYON` (pressed, EBin.cs:1081) and `B_KEY` (held, :1107) — **only while
`SpectatorField && GetUserControl()`**. The census that shaped it (8,358 `IsButton` reads across the
817 real fields): 2,010 are BLOCKING `while` waits, and **271 of those block on Confirm/Special** —
so a blanket strip (or an always-on strip) would hang real cutscene "press Confirm" beats a mirrored
guest must advance. The discriminator is control state: every blocking wait runs with user control
SEIZED by its scene (control OFF → pass through), while the loot/chest/dig idiom polls during free
walk (control ON → masked). Latched decline: `script button-poll (pickup/loot)`, once per field, and
only when the bits were actually pressed. Residuals (documented, unmasked): `B_KEYOFF` (release
completes, cannot initiate) and the `B_KEYON2/B_KEY2/B_KEYOFF2` arg-variants (shared generic handler,
no census hits — revisit only if a playtest surfaces one). EBin.cs joined the pre-round snapshot set
(it carries an s37 hunk).
**Retest:** field 206, bench ON → the Phoenix Down prompt does nothing + one decline line; bench
OFF → lootable as vanilla.

**Re-verify round (3 focused skeptics, `wf_7c682de1`) — final fixes:**
1. The growth gate now holds **without disarming** — the first cut's disarm re-stamped the baseline
   next frame, measuring growth frame-to-frame (<100u always), so the steering override could never
   fire. With a persistent `_autoTpArmSep`, stable-sep steering holds forever (exploring) and genuine
   walking-away crosses the margin and recovers.
2. `OwnSaveReloadInFlight` now clears in the autoload **callback** (`NetSyncState.ExitMirrorToOwnSave`)
   — an autosave resuming to the OVERWORLD or the title never runs the field-load clear, so the flag
   stuck true and falsely tainted own-story snapshots for the rest of that session.
3. `NetSyncField.ResetTeleportKey()` at session boundaries (OnDestroy + transport reconfigure) — the
   L3 accumulator only self-resets while polled, and the session gate stops polling at session end.
Accepted (self-correcting, watch in playtest): the bounce window is SLIDING, so ~4 re-treads of one
door inside 20s spends the budget → a brief excursion the follow-warp yanks back · an unreachable-host
auto-transition corridor becomes a slow multi-field reload ping-pong (strictly better than the
pre-budget infinite reload) · an off-mesh auto-TP drop onto a gateway quad reload-cycles at ~10s
until the host moves (bounded by the cooldown, never lets the jump through).

## ★★ TWO-MACHINE SESSION 2026-07-23 — desktop host + laptop guest, real link

4 of the 6 queued boxes PROVEN; L3 carries forward untested; auto-TP FAILED ACCEPTANCE and surfaced a
crash window that outranks it.

1. **Real-guest interaction block** — ★ PASS. Confirm on a real followed guest (NPC/chest/save-moogle)
   is a genuine no-op exactly as the solo bench predicted; `GetUserControl` reachability for a followed
   guest is no longer needs-in-game — it's proven.
2. **Gateway redirect + follow-allowance** — ★ PASS on the live link. New nuance worth keeping: when
   host and guest walk into the SAME door at the same moment, the guest bounces ONCE — `LastHostField`
   hasn't picked up the host's new destination yet at the instant the guest's own redirect evaluates —
   then the follow-allowance/manual-teleport catches them up on the very next beat. Bounce-then-follow,
   not a defect; matches the "one extra reload" consequence already accepted in THE GATEWAY REDIRECT
   above.
3. **Manual TP** — F11 ★ PASS. **L3 (held ~0.7s, `JoystickButton8`) is still UNTESTED on the live pad**
   — carries forward as the one open item in this box.
4. **Auto-TP** — ✗ FAILED ACCEPTANCE. Fires intermittently on the real link ("sometimes works,
   sometimes doesn't" — the dwell/steering predicate isn't reliably tripping over the actual
   transport; root cause not yet isolated, diagnosis in flight, no speculation past this line). Worse
   than a bad leash: when it misfires the guest DROPS THE SESSION for ~1-3s, and a random battle
   starting inside that unpaired window boots the guest into their OWN party — the game then CRASHES
   on battle exit. Owner verdict: auto-TP as a concept is disliked unless the leash can be made
   reliable → **default-OFF pending a rework** (tracked separately from the crash). The crash window
   itself is a SEPARATE must-fix: ANY transient unpair — not just auto-TP's — can manufacture the same
   battle-boots-with-a-solo-party state, so the fix belongs at the unpair boundary, not inside
   `AutoTeleportTick`.
5. **Snapshot leak end-to-end** — ★ PASS ("good, discarded": Snapshot while mirroring → ramp →
   Restore refused → manual save writes the guest's OWN story, the exact closure design proves out
   live).
6. **MENU opcode / mirrored-cutscene sanity** — OBSERVED AS BUILT, not a lockstep proof: both sides can
   accept dialogue and advance independently at F1's tier (doesn't hang, which is all this box was ever
   scoped to show). Full host-driven confirm/choice lockstep stays the ratified **F3** round, unchanged
   plan.
7. **Standing s41/s42 leftovers** (tick numbers · Plant Brain · Feather Boots · host-silent bench · a
   Workspace-tab session) — not exercised this session, still queued.

**New findings this session (logged, not yet root-caused):**
- Field 206: the guest heard a "horn" music variant while the host heard the normal Evil Forest theme
  — suspected story-state divergence feeding the music pick; unreproduced, recon in flight.
- **Follow-warp latency** (owner priority): the guest waits out the host's FULL field change before the
  follow fires, landing ~1-3s behind. Fine for "eventually catches up," not a base for cutscene
  lockstep. **F2 (the SectionIntent transition-intent lane, wire v11) is PROMOTED — next after the
  crash-window fix, ahead of the rest of the build order.**

**Status: F1 is two-machine proven on 4/6 boxes** (interaction gates · gateway redirect +
follow-allowance · F11 manual TP · snapshot taint). Open: L3 on a live pad, auto-TP (failed
acceptance, default-OFF pending rework), the battle-boots-solo-party crash window (must-fix,
cross-cutting), and the F2 promotion for follow-warp latency.

## F2 (wire v11) — ★ TWO-MACHINE PROVEN (headline boxes) 2026-07-23

A read-only recon produced the implementation spec below; an adversarial pre-build review confirmed
it, surfacing ONE real finding — the L1 pin-flag desync across a link blip (a latent stuck-controls
freeze: a guest pinned mid-co-location that drops and regains the link before the release conditions
fire never un-pins) — fixed before the build. Built + deployed to the desktop engine, DLL
`588EBC3219F7DD17`. Solo bench and a same-evening two-machine session (2026-07-23) both ran off this
build — results below.

**Content:**
1. **THE TRANSITION-INTENT LANE** — the host emits `SectionIntent` (state-lane section 4:
   `[destField u16][nonce u8]`) at the MAPJUMP opcode's commit point, which the recon proved is the
   ONLY decidably field→field funnel. The ratified DESIGN.md idea of hooking `SetNextMap` directly was
   REJECTED: WMAPJUMP (world-map exit, a frontier) flows through the same call with mode still 1 —
   hooking there would emit intents for overworld exits too. A fired host transition has no abort
   path, so an intent is a reliable promise. The guest fast path (`ServiceIntentFollow`) fires the
   same proven warp body via a shared `StartFollowWarp` helper, skipping the 1200ms debounce (the
   intent IS the debounce). The serial `FollowHostTick` path stays byte-intact underneath as a
   guaranteed fallback floor. The `_followWarpedTo` latch gives free dedup. Handled: second-intent-
   mid-load, mid-diorama deferral, and blip loss (30Hz latest-slot re-send).
2. **DIALOGUE L1 CO-LOCATION** — `SectionEvent` (section 5: `[flag u8][nonce u8]`). Host detection =
   `!GetUserControl()` corroborated by `UIManager.Dialogs.Visible` (a bare usercontrol check
   false-positives on gateway walks). Guest snaps via the proven `SnapToHost` + pins
   (`SetUserControl(false)` ONLY if the guest still HAD control — its own re-staged cutscene keeps
   its own), releases on flag-fall / field-leave / session-drop / pending-warp. Explicitly NOT
   choice/pacing sync — that stays the ratified F3/L2 round.
3. **THE R2 SAME-DOOR INTERLOCK — DEFERRED** to an F2.1 polish (orchestrator decision):
   `RedirectGuestFieldJump` is untouched; F1's proven bounce-then-follow stands.
4. **Selftest benches** shipped in the ~ Go tab: an intent injector (fabricates a section through the
   REAL codec into the REAL fast path) and an L1 flag toggle (snap+freeze on the selftest mirror).
5. **The wire bump v10→v11** hard-splits mixed versions on both transports (single `Version` const,
   verified shared).

**Solo bench recipes — ★ PASS 2026-07-23 (desktop):**
1. **Inject intent → field N** — ★ PASS. The log ran the full expected sequence: the bench-gating
   message when OFF, then `fabricated SectionIntent field 4005 nonce 1 -> fast-path` →
   `intent: following the peer to field 4005 (parallel)` → field load → ghost spawn. (The
   `EVT_MOGWAI.txt` asset line in the same log is benign — the 42nd-moogle animation lookup firing
   on a custom field, unrelated to the intent path.)
2. **L1 toggle** — ★ PASS. Clean `L1 released (event ended)` on release.

**Two-machine boxes — RUN 2026-07-23 evening** (desktop host + laptop guest, real link; F2 patch on
top of the proven F1 build):
1. **Parallel-warp feel + latency vs the serial baseline** — ★ PASS.
2. **Strict nonce dedup** — OPEN, not explicitly exercised this session (a log-level box).
3. **Chained transitions land on the final field with no double-fire** — ★ PASS (chained/fast
   gateways — guest follows).
4. **Host self-clear + no redundant serial warp** — OPEN, not explicitly exercised this session
   (a log-level box).
5. **Same-door = at most F1's single bounce** — ★ PASS (simultaneous same-door entry).
6. **L1 on a real mirrored cutscene** — ★ PASS (guest dialogue snap + freeze).
7. **L1 vs the guest's own re-staged cutscene (restore only what we took)** — OPEN, not explicitly
   exercised — left OPEN, not closed.
8. **Scene-end-into-gateway control ownership (guest stays frozen through the fade)** — OPEN, not
   explicitly exercised — left OPEN, not closed.
9. **s56 blip during an intent (serial floor recovers, no stuck screen)** — NOT TESTED, deferred:
   the serial floor is structurally guaranteed, ruled non-gating for this session.
10. **v10↔v11 silent no-sync sanity** — NOT TESTED, deferred: mixed-version sanity, ruled
    non-gating for this session.
11. **Edge-only logging (no per-frame spam)** — OPEN, not explicitly exercised this session
    (a log-level box).

**Status: F2 is two-machine proven on the 4 headline boxes** (parallel-warp / chained transitions /
same-door single bounce / L1 co-location on a real mirrored cutscene), same evening as the build.
Open: strict nonce dedup, host self-clear, edge-only logging (log-level boxes, not explicitly
exercised) · L1-vs-own-cutscene and scene-end-into-gateway control ownership (behavior boxes, not
explicitly exercised — left OPEN, not closed) · link-blip-during-intent and mixed-version sanity
(deferred, non-gating: the serial floor is structurally guaranteed).

## F3 (wire v12) — ★ BUILT + DEPLOYED + ADVERSARIALLY REVIEWED 2026-07-23, solo + two-machine PENDING

A read-only recon produced the dialogue-L2 implementation spec; the census synthesis
(`dialogue-census/DIFFICULTY-VERDICT.md` — three byte-grounded lanes over all 818 real field scripts,
joined with the F3 engine recon) repriced the ratified design cheaper before a line of code was
written (below). A pre-build adversarial review then found **NO ship-blockers**; four non-blocking
findings recorded (below). Built + deployed to the desktop engine (both arches), DLL
`3AD3585285335D84` (backup `pre-f3` `20260723-221351`); laptop package
`FF9Coop-laptop-update-20260723e` (carries the standing wire-bump warning). **Solo bench and
two-machine proof are both PENDING — this section records the BUILD only; F3 patch capture (in-game
proof) is the next milestone.**

**Content:**
1. **THE TypeDialog=7 FIFO LANE** — the type-6 precedent, both transports, 8-byte frames
   `[fld u16][winnum u8][textId u16][kind u8][choiceIndex u8][seq u8]`.
2. **The host tap** at `Dialog.OnKeyConfirm`'s two confirm-driven Hide sites — `IsClosedByScript`-
   filtered; fast-forward/AutoHide/scripted closes never emit; the emit helper role-gates before
   touching the dialog and never throws (vanilla dialogue provably unchanged).
3. **The guest pump `ServiceDialogLockstep`** — peek-until-match FIFO over a one-slot pending holder:
   match@Complete → `TrySetCurrentChoice` (a NEW bounds-checked `Dialog` method — the unguarded
   `SetCurrentChoice` is unreachable with a bad index) + direct per-window `OnKeyConfirm` (`go` arg
   verified unused); match@printing → fast-forward + hold, no double-advance; unmatched → held with
   the 8000ms `DialogWaitMs` timeout.
4. **The `UIKeyTrigger` suppress guard** — one static read, false on vanilla.
5. **Selftest benches** — inject advance / inject choice / the B5 unmatched-frame timeout proof.
6. **The wire bump v11→v12** at the single const (both transports verified sharing the parse).

**THE SOFTLOCK-ESCAPE INVARIANT** (enumerated, review-verified): suppress is set only on first-match
or lockstep-hold; released by every non-engaged tick (link staleness ~2s, host flag fall, field
leave, follow-warp, co-location loss), window close, the 8s timeout, and session reset — no stuck
interleaving found.

**Ratified scope + census grounding** (`dialogue-census/DIFFICULTY-VERDICT.md`): engage only under L1
· solo dialogue stays fully local (falls out of L1 for free) · engage-on-first-match suppress arming
(kills the R4 softlock class) · per-page pacing (tap `OnKeyConfirm`, page rate = line rate — 8-byte
frames make volume a non-issue) · scripted closes filtered, never emitted (the free 17%) · **NO MAP
mirror** — the census's repricing: MAP state is DERIVED not root, zeroed at every field entry and a
deterministic function of the mirrored GLOB snapshot + the script itself, so under L1 MAP-gated
windows align on their own (93.9% of locked cutscene spans read no structural root and replay in
perfect lockstep) — building one would be wasted engineering · same-language sessions documented, not
special-cased (7 engine-hardcoded language-conditional fields diverge cross-language: fields
1060/1650/1652/1657/1659/1850/2172/2209).

**Pre-build adversarial review — NO ship-blockers.** Four non-blocking findings recorded:
- **(A)** the ratified S3 first-advance race: a guest mashing Confirm can advance one window ahead of
  the host's first frame; harmless/self-healing; boxed for two-machine feel-testing with a known
  in-spec tightening (engage-from-window-open) if wanted as a follow-up F3.1.
- **(B)** the `UIKeyTrigger` guard also swallows Pause/Menu — broader than spec, benign-to-better.
- **(C)** voiced choice windows close voice-paced on the guest — self-healing; boxed.
- **(D)** timeout-drain semantics as ratified.

**Solo bench recipes (built, queued — not yet run):**
1. **Inject advance** — fabricate a TypeDialog=7 "advance" frame through the real codec into the real
   guest pump (`ServiceDialogLockstep`) with no live host; proves the match@Complete path fires.
2. **Inject choice** — same, tagged as a choice frame; proves `TrySetCurrentChoice` + the forced
   confirm.
3. **The B5 unmatched-frame timeout proof** — withhold a matching frame; proves the 8000ms
   `DialogWaitMs` hold releases cleanly with no stuck interleaving.

**Two-machine boxes — QUEUED, none run yet** (desktop host + laptop guest, real link; F3 patch on top
of the proven F1+F2 build) — the 8 boxes from the laptop package README, plus the standing L3 item
carried forward from F1:
1. Lockstep cutscene
2. Multi-page cadence
3. Choice, incl. voiced
4. The S3 mash test
5. Host-kill un-freeze
6. Blip un-freeze
7. Scene-into-gateway
8. v11-v12 sanity
9. (carried forward from F1, still open) L3 held-teleport on a live pad

**Status: F3 is BUILT + DEPLOYED + ADVERSARIALLY REVIEWED, 2026-07-23.** Solo bench and two-machine
proof are both PENDING — F3 patch capture (in-game proof) is the next milestone before the round can
be marked proven.

## ★ F3 SOLO BENCH 2026-09-04 — 40/40, run UNATTENDED by the harness; F3 CAPTURED as `s84`

The three solo recipes above were designed as ~ debug-menu buttons (IMGUI) and had never been run.
s83 **rev 5** (protocol 4→5) adds a `netsync` verb family to the harness agent that calls the SAME
static bench entry points the buttons call, plus a `netsync` state block (the L2 observables: the
window under lockstep, a HELD frame and its timeout clock, `suppress`), so the benches run as a
scenario: `studies/test-harness/scenarios/coop_dialogue_lockstep.py`
(`py tools/play.py studies/test-harness/scenarios/coop_dialogue_lockstep.py --field 30801`).
**`netsync selftest 1` forces the selftest role for the launched PROCESS only** — Memoria.ini is never
touched (the shared install), and the override is released on disarm, fault and `reset` (proven: the
final section leaves L1 pinning control, sends `reset`, and control comes back with co-op disabled).

**Run 4 (`.harness-runs/20260904-170049-coop_dialogue_lockstep`): 40 checks, 40 passed**, every one
an OUTCOME, never an ack:
- **B1 advance:** the west window's transcript paged by injected frames == the transcript paged by the
  player's own Confirm, page for page (one inject = exactly one page — B6's "never two page-skips" IS
  the equality); one `dialog lockstep: advanced win` line per inject; frame consumed, suppress released,
  no window left under lockstep after the close.
- **B2 choice:** `netsync choice 3` (= `Tetra Master`, the index the engine's own `SelectChoice` reports
  for that name) closes the menu and leads to the SAME window a local `choose(3)` leads to; the log
  carries `choice win 1 -> index 3`. **B2b out-of-range:** index 55 of 15 is refused by
  `TrySetCurrentChoice`, logged ONCE (`out of range ... local default`), and the menu still closes on
  the local default — the guest is not wedged.
- **B5 unmatched:** the win-15/text-0xFFFF frame is HELD with the timeout armed; `suppress` stays false
  (S3); the player's own Confirm still pages the window while it is held and does NOT consume the
  frame; the hold releases after **8.1 s** (DialogWaitMs 8000) with exactly one
  `timed out -- local advance restored` line; clock disarmed, local input restored.
- **L1:** with a window open, L1 ON does NOT take control (pin-only-if-the-guest-still-had-control);
  once the scene ends the pin takes it; L1 OFF releases it.

**Two findings, neither an engine defect:**
1. **`[NFOC]`/`[TIME]` windows must never be injected into.** They set `Dialog.ignoreInputFlag`, so
   `OnKeyConfirm` never Hides them — and the host tap lives inside the Hide branch, so a real host
   never emits for one. Run 1 fabricated a frame for the journal bench's polled status page
   (`[NTUR][NFOC]` + a `B_KEYON` poll + a script `CloseWindow`): the apply "succeeded", the page stayed
   open, and the lockstep held `suppress` for as long as it did. On a real link the frame cannot exist;
   the bench now refuses to fabricate one and pages such windows out LOCALLY (for a polled page that IS
   the script's close). Worth carrying: the guest-side apply does not check `ignoreInputFlag`, so the
   only thing between a mis-authored frame and a held `suppress` is the host tap's placement — the
   engage gate (host flag fall / ~2 s staleness) and the window's own close remain the escapes.
2. **A still-typewriting window eats the first Confirm as a fast-forward** (`AdvanceProgressToMax`)
   and closes on the second. Run 3 pressed once and blamed the hold. The injected path never sees this:
   its apply fast-forwards, HOLDS the frame, and re-applies next tick (B6, as designed).

**Capture (2026-09-04):** F3 is now `memoria-patches/s84-netsync-dialogue-lockstep.patch` — 28 hunks,
6 files (`Dialog.cs` · `UIKeyTrigger.cs` · `Ff9mkDebugMenu.cs` · `NetSyncSocket.cs` · `NetSyncRelay.cs`
· `NetSyncClient.cs`), its only deletions the v11→v12 wire lines. Numbering is capture order; its STACK
POSITION is right after `s57` (s83's DebugMenu/UIKeyTrigger hunks were captured from a tree that already
carried F3). `s83-harness-agent.patch` regenerated for rev 5 (19 hunks, 9 sections; `NetSyncClient.cs`
joins its set for the bench entry points). Gates: the full live stack (dead s12/s18/s21/s59 skipped —
applying the dead s21 is what made s22/s37/s44 look fuzzy) replays base→s57→s84→s58…s83 at ZERO fuzz
under `git apply --binary` and reproduces all 18 netsync/harness/dialog files byte-exactly; `s84` lands
on the s57 snapshot and `s83` on its baseline under both `git apply --check` and `patch -p1 -F0
--dry-run`; `git apply -R --check` of `s83` on live is clean and the cascade live −s83 −s84 is clean.
The replay is a tool now: `tools/memoria_stack_replay.py`. Live DLL `a2d69edd057d982f…`, pre-build backup
`20260904-163811`.

**Still OPEN:** the 8 two-machine boxes (+ the L3 pad) — a real link is the only way to exercise the
host tap (`EmitDialogAdvanceIfHost`) and the FIFO transport; the solo bench fabricates frames past
both. Finding (A) — the S3 first-advance race — is a two-machine feel question, unchanged.

## ★ F3.1 THE TALK RELAY — built + solo-proven 2026-09-04 (wire v13); the two-machine run found the gap

**The gap (Dali 350, desktop host + laptop guest, the first F3 two-machine attempt):** the host talked
to an NPC; on the laptop the NPC never turned and no window opened. An NPC talk is PRESS-FIRED
(tag 3): `EventCollision.CheckNPCInput` makes the player the NPC's listener (that is the facing) and
calls `Request(obj, 1, 3)`. A following guest can never start one — the F1 spectator gate returns
before Request, and the L1 pin holds its control — and L1's host flag rises only once a WINDOW is
visible, so nothing ever told the guest "the host started talking to object 12". The guest's copy
never began, and every F3 frame the host emitted for it sat unmatched until the 8 s timeout. L1 was
designed around tread-fired scenes (co-location makes the guest's own trigger fire); the census counts
6,579 talk-placed windows (23%), and the package README had pointed the session at exactly those.

**The relay:** state-lane section 6 `[field u16][uid u16][nonce u8]`. HOST: `EmitTalkStartIfHost` at
the Request accept in BOTH collision funnels (NPC talks, chests, save moogles, shops; tag-8 card
challenges deliberately excluded), pushed out-of-band like the intent and riding the frame for 2 s
(a late joiner must not replay a stale start). GUEST: `ServiceTalkFollow`, ahead of the L1 pin in the
client tick — same field, fresh nonce, FieldHUD → `SnapToHost`, become the listener,
`Request(obj, 1, 3)` on its own copy. Host-driven by construction, so it never touches the spectator
gate; defers (nonce unmarked) off-field / mid-menu / mid-battle. Wire v12→v13.

**Solo proof** (`scenarios/coop_talk_relay.py`, 10/10, `.harness-runs/20260904-182300`): a local talk
published the NPC's uid as `player.listener` (3); from 270 units away `netsync talk 3` opened the SAME
window the local talk had, with the listener set; the section round-tripped the real codec; an unknown
uid was declined once and opened nothing. Captured as `s85-netsync-talk-relay.patch` (15 hunks, 5
files, stack-top), gated both ways by `tools/memoria_stack_replay.py`; live DLL `e9c856267d78cace…`,
pre-build backup `20260904-182113`; laptop package `Desktop\FF9Coop-laptop-update-20260904` (v13 —
both machines). Two session facts worth keeping: `coop host` puts the SHARED Memoria.ini into a live
session, so the harness's `netsync selftest` refuses until `coop off`; and the laptop's checkout
predated the `coop` verb (its older py launcher also rejected the `pythonw` shebang — fixed).

**Still OPEN:** the two-machine run with the relay in place — box 0 of the package README (the host
tap and the section on the wire), then the F3 boxes 1–9.
