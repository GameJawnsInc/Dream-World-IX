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

## Two-machine boxes queued for the next laptop session
Real-guest interaction block (bench green ≠ proof — GetUserControl reachability for a followed guest
is needs-in-game) · gateway redirect + follow-allowance on the real link · manual/auto TP with a real
host · snapshot leak end-to-end (Snapshot while mirroring → ramp → Restore refused → manual save
writes OWN story) · the standing s41/s42 leftovers (tick numbers · Plant Brain · Feather Boots ·
host-silent bench · a Workspace-tab session).

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
