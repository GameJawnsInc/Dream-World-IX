# B3.6 — THE POLISH ROUND (recon 2026-07-16, workflow wf_4c06e82d — 6 lanes, every verdict CORRECTED)

> Recon shape: 6 source-grounded answers, each adversarially verified against the live tree
> (`C:\gd\FFIX\Memoria`). **All six first-pass answers were materially corrected** — the arc's
> recon history holds (B3 pass 1: 7/8 corrected; B3.5: 5/5). The specs below are the AS-SHIPPED
> versions with corrections folded in. Implementation gates on these checklists verbatim.
>
> Wire: v9 -> **v10** (the type-1 boot block gains `songId` u16; the type-6 lane gains the
> StatTick marker). One DLL round; both machines must update (established fail-safe).


---

## Lane 1 — the swirl + BGM carry (wire v10: songId on the type-1 boot block)

**★★ TWO-MACHINE PROVEN + CLOSED 2026-07-23** (the reliability-round session, silent-bench field
30112 — `silent-bench/BENCH.md`): the host's silent battle (`Music: -1` + `[music] stop`) was
silent for BOTH players — the guest's diorama honored the `0xFFFE` host-silent sentinel, no
carried theme, no local fallback — and warping back to field 250 afterward resumed the field music
for BOTH players cleanly. Closed via the engine's **s54** fix, not a change to this lane's own wire
design: the guest previously folded `0xFFFE` into the keep-field-BGM path (letting the resident
track ride through the fight instead of suspending it); s54 gave `0xFFFE` its own true-silence
branch plus a stop-not-suspend path at boot, closing the stacking/double-copy defect on the return
warp. **The s41 wire lane below — the sampling, the sentinel, the guest override at both
BattleSwirl branch heads — was correct host-side all along.** The audible-theme A/B leg (hearing an
actual non-silent host theme) is still open.

# B3.6 swirl + BGM carry — verified recipe (wire v10)

## 0. What the CURRENT diorama sounds like (baseline — CONFIRMED)
The plain `Replace("BattleMapDebug", FadeOutToBlack_FadeIn, true)` boot (NetSyncDiorama.cs:225) never runs anything in BattleSwirl.cs: no 636/635/634 encounter swish (BattleSwirl.cs:74-76), no battle BGM — `btlsnd.ff9btlsnd_song_play` has exactly three call sites in the tree: BattleSwirl.cs:96 (field entry), :108 (world entry), and btl_util.cs:205 inside ManageBattleSong (end-of-battle, unreachable — IsOver is never set, per the diorama laws). The scene change stops sound EFFECTS only (SceneDirector.cs:405 sync / :463 async), stops music only for "MainMenu" (:408-409/:466-467), and installs FF9AllSoundDispatch for BattleMapDebug (:429-434/:487-492 — a forwarder, non-issue). The field-side suspend lives only on the field's own nextMode==2 path (HonoluluFieldMain.cs:315-322), which the diorama bypasses. **Net: the guest's OWN field BGM keeps playing under the diorama, uninterrupted; no battle music, no encounter SFX.**

## (a) HOST sampling — sample the computed id, never recompute
The battle song is computed at **BattleSwirl.cs:91** (field: `GetMusicForBattle(BtlBgmMapperForFieldMap, EffectiveFieldId(fldMapNo), nextMapNo)`) and **:102** (world), played at :96/:108 unless `songid == -1 || songid == currentMusicId` (:93-94/:104-105). It fires at 1.3 s (BattleSwirl.cs:41-45) or at rush completion (:52-56) — BOTH strictly before ReplacePending (:58-62), hence before BattleMap loads and before InOwnBattle (gMode 2/4 + btl_list, NetSyncBattle.cs:500-510) can turn true, so a static stamped here is always set before the first type-1 sample. World battles also enter through the swirl (WMScriptDirector.cs:222), so BattleSwirl covers ALL battle entries.

**SAMPLE THE COMPUTED ID.** Both patch layers live INSIDE the sampled expression: the BattlePatch `Music:` override is the first check inside GetMusicForBattle (`BtlBgmPatcherMapper.TryGetValue`, FF9SndMetaData.cs:20-21; filled at DataPatchers.cs:677-680), and s33's fork remap is the `EffectiveFieldId(...)` wrap at BattleSwirl.cs:91. The return value reflects both — recompute-on-guest would need identical BGM JSON + BattlePatch tables on both installs, which the kit's own `Music:` patch exists to diverge.

Sample the OUTCOME: `wireSong = (songid != -1) ? songid : FF9Snd.GetCurrentMusicId()` (GetCurrentMusicId returns -1 when idle — AllSoundDispatchPlayer.cs:94-97); if that too is -1 → sentinel 0xFFFE "host silent". Hook placed BEFORE the :93-94 early return, in both branches:
```csharp
// [ff9mapkit netsync] host: publish the audible battle song (post BattlePatch + s33)
if (!Memoria.Netsync.NetSyncDiorama.Booted)   // a guest's own diorama swirl must not stamp
    Memoria.Netsync.NetSyncBattle.NoteLocalBattleSong(songid != -1 ? songid : FF9Snd.GetCurrentMusicId());
```
**Clear the static at the REAL falling-edge sites** (NOT beside the rising-edge nonce logic — clearing there erases the swirl's stamp and every frame ships 0xFFFF): inside `NetSyncBattle.Reset()` (NetSyncBattle.cs:237-257 — covers the loop pump's falling edge at :414-415 AND session teardown) plus the socket pump's falling-edge block at :319-324 (which does NOT call Reset). A later battle that skipped the swirl then correctly sends 0xFFFF.

## (b) The wire — type-1 grows u16 songId ⇒ v10
Current type-1 payload (encoder NetSyncBattle.cs:519-545, decoder :811-819): `[seq u16][mapNo u16][guestSlots u8][patNum u8][startType u8][flags u8 bit0=isRandomEncounter][nonce u8][count u8][units…]`. **v10 inserts `songId u16 LE` at payload offset 9-10, between nonce (offset 8) and count.**
- encode after `bw.Write(_battleNonce)` at :545; decode after `view.Nonce = br.ReadByte()` at :818; `BattleView` gains `UInt16 SongId` (class :94-106).
- sentinels: `0xFFFF` = unknown → guest falls through to its LOCAL computation (fail-safe, s33-precedented); `0xFFFE` = host audibly silent → guest suspends its own BGM, plays nothing.
- `WireBenchBoot` (NetSyncBattle.cs:1096-1133) MUST write the 2 songId bytes between :1112 (nonce) and :1113 (unitCount), assert them in the round-trip check (:1122-1128), AND pass the parsed songId into its `BootFromWire` call at :1132 — otherwise ParseView reads count out of position and the bench rots.
- plumb: `TryGetPeerBattleOpen` (:1072-1085) gains `out Int32 songId`; NetSyncClient.DioramaTick's call at NetSyncClient.cs:740 and the boot at :813 pass it into `BootFromWire`.
- visibility: append the song id to the spectate boot-block line (NetSyncBattle.cs:1546-1548) — every selftest battle proves the encode by eye.

**Version bump = ONE constant:** `NetSyncWire.Version = 9` at **NetSyncSocket.cs:84** (written :102, validated :116, log + link-drop :540-543). **NetSyncRelay.cs has NO constant** — it reuses NetSyncWire.Version (NetSyncRelay.cs:17); old-version peers' frames fail the header check SILENTLY over the relay (:317-322 — looks like a session that never pairs; check both DLLs first). Bump 9→10 at :84; update comments at NetSyncSocket.cs:55/:79 and the v8/v9 notes at NetSyncBattle.cs:99-104/:814/:839. v9 peers rejected by design — update BOTH machines.

## (c) Guest boot via SwirlInBlack — SAFE, with THREE fences
Change NetSyncDiorama.cs:225 to `SceneDirector.Replace(DioramaScene, SceneTransition.SwirlInBlack, true)`, behind `[Netsync] DioramaSwirl` (default 1, hot-reloadable; plain path = the fallback lever — the pairing is in-game UNTESTED, the B3.1 deferral's reason).
- Mechanics are target-agnostic: Replace routes swirls to Swirl() (SceneDirector.cs:134-138) → _Swirl stashes PendingNextScene (:549-550), loads SwirlScene (:560), IsFading false at :569; BattleSwirl.Update → ReplacePending (BattleSwirl.cs:61) → NextScene = PendingNextScene (SceneDirector.cs:148) → fade → Loading → BattleMapDebug. No "BattleMap" assumption anywhere on the path.
- **Loaded-level sequence: Field→"SwirlScene"→"Loading"→"BattleMapDebug"** (plain path lacks SwirlScene). **Containment predicate UNCHANGED**: Active is POSITIVE on "BattleMapDebug" (NetSyncDiorama.cs:71-80), correctly false during SwirlScene/Loading, where no battle code exists; the rejected-predicate #2 hazard (SwirlScene suppressing a REAL battle) never applies. The selftest already drives the SwirlScene seam (NetSyncDiorama.cs:1291).
- **IsFading composes**: Boot refuses mid-fade (NetSyncDiorama.cs:169-177); Swirl() has the identical silent no-op (SceneDirector.cs:542-543), same call stack so Boot's check covers it. `_Fade` (:253) and `_Swirl` (:551) both set IsFading=true before their first yield — synchronous from Boot's Replace onward.
- **isDebug**: BattleSwirl never reads it. Boot's stamps (NetSyncDiorama.cs:212-221) land BEFORE Replace — and `isRandomEncounter` now also buys the correct swirl LOOK (SFX_Rush captures it in its ctor, SFX_Rush.cs:22/:37, created in BattleSwirl.Awake :28 — after the stamp).
- **BattleUI/teardown unchanged**: OnGUI gated on Active (BattleUI.cs:68); teardown = HonoluluBattleMain.cs:876-877 OnDestroy → ForceDisarm, gated on Booted.
- **FENCE 1 — stranded-swirl mop-up** (client tick, beside DioramaTick): `if (NetSyncDiorama.Booted && !IsFading && loadedLevelName is FieldMap/WorldMap) ForceDisarm()` + log. Misfire-safe: during a healthy boot IsFading is true through both fades, and the swirl's IsFading==false idle window has scene "SwirlScene" (no match).
- **FENCE 2 — the SwirlScene watchdog** (the fence above does NOT fire while stranded ON SwirlScene): `if (Booted && loadedLevelName == "SwirlScene" && >15 s since boot) Leave()` + log. Rationale: a BattleSwirl that throws every frame (the _rush GPU path source reading cannot clear) strands with player control disabled (SceneDirector.cs:555); F6 Leave works from SwirlScene (IsFading false after :569; the plain Replace path is legal from any scene) but must not be the only recovery.
- **FENCE 3 — the watcher-Leave/ReplacePending race** (new finding): if the host's lane goes stale while the guest is in SwirlScene's IsFading==false window, DioramaTick's auto-Leave (NetSyncClient.cs:768-773) sets NextScene="FieldMap" and starts a fade — and BattleSwirl's later ReplacePending OVERWRITES NextScene to "BattleMapDebug" unconditionally (SceneDirector.cs:148 runs even though its Replace then no-ops on IsFading :519-520), so the leave becomes a boot (self-healing via the 1 s-rate-limited re-Leave, but ugly). Defer DioramaTick's auto-Leave while `CurrentScene == "SwirlScene"` (equivalently PendingNextScene non-empty); the swirl resolves into BattleMapDebug in ~2 s and the Leave then lands cleanly.
- gMode: BattleSwirl.Awake captures EventEngine.gMode (BattleSwirl.cs:25) and only plays BGM for 1/3 (:82-85). The watcher boots only free-standing on a field with FieldHUD (NetSyncClient.cs:802-807), so gMode==1 at every auto-boot; the world branch override is defense.
- Sound dispatch: BattleSwirl.Awake sets FF9BattleSoundDispatch (:26), ChangeScene later installs FF9AllSoundDispatch for BattleMapDebug — both forwarders (diorama-lane.md's verified row).

## (d) Guest BGM override — composes with s33 by predicate, not by merge
`BootFromWire` grows a validated `songId` param → private `_wireSongId`. Reset to unknown in: the manual Boot overloads (NetSyncDiorama.cs:125-128), ForceDisarm, AND private Boot's catch path (:227-244). Expose `internal static Boolean TryGetWireBattleSong(out Int32 id)` — true only when `Booted && _wireSongId != unknown`, so every non-diorama swirl (any real battle on either machine) takes the stock branch untouched.

Override at BOTH branch heads, superseding the whole computation — the s33 `EffectiveFieldId` line stays byte-identical as the else-branch fall-through:
```csharp
Int32 songid;
if (Memoria.Netsync.NetSyncDiorama.TryGetWireBattleSong(out songid)) { /* wire wins: host's audible song incl. BattlePatch+s33 */ }
else songid = FF9SndMetaData.GetMusicForBattle(...);   // existing line, untouched
```
(same at BattleSwirl.cs:102; keep the :90/:97 IsPlayFieldBGMInCurrentBattle writes as-is; `0xFFFE` maps to `songid = -1` AFTER the suspend below = silence). The :93-94 early-return then does the right thing: wire song == guest's current music → keeps playing; else the host's theme plays at :96.

**Field-side pre-swirl replicate** (the guest analogue of HonoluluFieldMain.cs:315-321, which SceneDirector never does): in Boot immediately before the swirl Replace, when the wire has data: `Int32 cur = FF9Snd.GetCurrentMusicId(); if (cur != -1 && wireSong != cur) FF9Snd.ff9fldsnd_song_suspend(cur);` (the -1 guard is new — suspend(-1) is garbage) + inline SuspendResidentSounds' body (HonoluluFieldMain.cs:337-349 — all public calls, copy verbatim) + `SFX_Rush.SetCenterPosition(0)`. Suspend for 0xFFFE too (host-silence becomes guest-silence). On 0xFFFF skip entirely — pure B3.1 behavior, fail-safe.

## Playtest boxes (I cannot see the game)
1. Solo wire bench: swirl visual + 636/635/634 + wire song over a bench diorama; leave clean; field BGM resumes on return (the suspend/resume seam is the one untested audio edge).
2. Real selftest battle: spectate panel shows boot block + song id (encode proof).
3. Two-machine: guest hears the HOST's theme; A/B a BattlePatch `Music:` override and an s33 fork-id field on the host — guest must follow both. **The host-silent half (`Music: -1`) is ★★ PROVEN 2026-07-23** (silent-bench field 30112, both players silent, both players' field music resumed on return to 250 — closed via s54); the audible-theme A/B leg is still open.
4. F6 Leave taken DURING the swirl window (exercises fences 2+3).

## Wire cost
+2 B per type-1 frame at ~150 ms cadence ≈ 13 B/s during a battle; version byte 9→10 (no size change); +2 B in the F6 bench frame. No other frame types change.

## Risks (standing)
1) Swirl×BattleMapDebug pairing in-game untested (SFX_Rush is GPU/render code) — hence DioramaSwirl lever + fences 1-3. 2) Suspend/resume symmetry on Leave→FieldMap — **★ PROVEN 2026-07-23** (both players' field music resumed cleanly on the warp back to field 250; closed via s54, see Lane 1's header note). 3) Mid-battle host music changes (btlseq Music ops) not tracked — entry song only, accepted gap. 4) v10 rejects v9 peers — update both machines (standing law; NOTE over the relay a mismatch is SILENT, NetSyncRelay.cs:317-322). 5) gMode∉{1,3} at swirl Awake → no BGM (stock behavior) — unreachable via the watcher (FieldHUD gate, NetSyncClient.cs:802-807); flagged, not fenced.

### Implementation checklist

1. Host sample hook at BattleSwirl.cs:91-97 AND :102-108, placed BEFORE the :93-94/:104-105 early return: NoteLocalBattleSong(songid != -1 ? songid : FF9Snd.GetCurrentMusicId()), guarded on !NetSyncDiorama.Booted
2. Clear the sampled-song static in NetSyncBattle.Reset() (NetSyncBattle.cs:237-257) AND in the socket pump's falling-edge block at :319-324 — NOT at the rising edges :289/:423 (clearing there erases the swirl's stamp and every frame ships 0xFFFF)
3. Type-1 encoder: write songId u16 after nonce (NetSyncBattle.cs:545, payload offset 9-10); decoder: read after Nonce (:818); BattleView gains UInt16 SongId (:94-106); sentinels 0xFFFF=unknown (guest local fallback), 0xFFFE=host-silent (guest suspends, plays nothing)
4. WireBenchBoot: write the 2 songId bytes between :1112 (nonce) and :1113 (unitCount), assert them in the round-trip check (:1122-1128), and pass the parsed songId into the BootFromWire call at :1132
5. Bump NetSyncWire.Version 9->10 at NetSyncSocket.cs:84 ONLY (NetSyncRelay has no constant — reuses it per NetSyncRelay.cs:17; relay-side mismatch is SILENT per :317-322); update comments NetSyncSocket.cs:55/:79 + v8/v9 notes NetSyncBattle.cs:99-104/:814/:839
6. TryGetPeerBattleOpen gains out Int32 songId (NetSyncBattle.cs:1072-1085); plumb NetSyncClient.cs:740 -> BootFromWire at :813
7. NetSyncDiorama: BootFromWire(+songId) validates and stamps _wireSongId; reset to unknown in the manual Boot overloads (:125-128), ForceDisarm, AND private Boot's catch path (:227-244); TryGetWireBattleSong true only when Booted && known
8. Guest override at BOTH BattleSwirl branch heads: wire song supersedes the WHOLE GetMusicForBattle call; the s33 EffectiveFieldId line stays byte-identical as the else fall-through; keep the :90/:97 IsPlayFieldBGMInCurrentBattle writes
9. Boot pre-swirl replicate (wire song known only): suspend the current song ONLY if cur != -1 && wireSong != cur (ff9fldsnd_song_suspend); inline SuspendResidentSounds body (HonoluluFieldMain.cs:337-349); SFX_Rush.SetCenterPosition(0); suspend for 0xFFFE too; skip everything on 0xFFFF
10. Switch NetSyncDiorama.cs:225 to SceneTransition.SwirlInBlack behind [Netsync] DioramaSwirl (default 1, hot-reloadable); plain path stays as the fallback lever
11. Containment predicate UNCHANGED (positive on BattleMapDebug survives the SwirlScene/Loading interlude, NetSyncDiorama.cs:71-80; the selftest already drives the SwirlScene seam at :1291)
12. FENCE 1 (client tick): if Booted && !IsFading && loadedLevelName is FieldMap/WorldMap -> ForceDisarm + log (misfire-safe: IsFading is synchronous — SceneDirector.cs:253/:551 — and the swirl's idle window is scene SwirlScene)
13. FENCE 2 (NEW): SwirlScene watchdog — Booted && loadedLevelName==SwirlScene for >15s -> Leave() + log (fence 1 cannot fire while stranded ON SwirlScene; F6 Leave works there but must not be the only recovery)
14. FENCE 3 (NEW): defer DioramaTick's auto-Leave while CurrentScene==SwirlScene / PendingNextScene non-empty (ReplacePending's unconditional NextScene overwrite at SceneDirector.cs:148 otherwise turns a mid-swirl Leave into a boot)
15. Boot stamp order re-verified: all stamps before Replace (NetSyncDiorama.cs:212-225); isRandomEncounter drives the swirl look via SFX_Rush's ctor capture (SFX_Rush.cs:22/:37, created at BattleSwirl.cs:28)
16. Spectate panel: append songId to the boot-block line (NetSyncBattle.cs:1546-1548)
17. Playtest (human): bench swirl+SFX+wire song; leave-clean + field-BGM resume; real-selftest panel shows songId; F6 Leave DURING the swirl window; two-machine A/B incl. a BattlePatch Music override and an s33 fork field on the host

<details><summary>What the verify pass corrected (the record)</summary>

1) THE FALLING-EDGE CLEAR SITES WERE MISNAMED (implementable-wrong). The spec said to clear the sampled-song static "on the own-battle FALLING edge in both pumps (beside the rising-edge `_battleNonce++` logic, NetSyncBattle.cs:289 and :423)". :289 and :423 ARE the rising edges (verified: `if (!_wasInBattle) { _battleNonce++; ... }` at NetSyncBattle.cs:287-291 and :421-425). A literal implementation "beside :289/:423" clears at the RISING edge — which erases the song the swirl stamped seconds earlier, i.e. every wire frame ships 0xFFFF and the feature silently never works. The real falling-edge sites: the socket pump's `else { if (_wasInBattle) { socket.SetLocalBattle(null); ... } }` at NetSyncBattle.cs:319-324, and the loop pump's `if (_wasInBattle) Reset();` at :414-415 — and `Reset()` itself (NetSyncBattle.cs:237-257) is the correct shared home (it also covers session teardown), plus the explicit clear in the :319-324 block (the socket pump's falling edge does NOT call Reset — verified).

2) THE STRANDED-SWIRL FENCE DOES NOT COVER THE STRAND IT WAS DESIGNED FOR. The spec's fence `Booted && !fading && loadedLevelName is FieldMap/WorldMap` never fires while actually stranded ON SwirlScene (loadedLevelName == "SwirlScene" matches neither). Recovery from a true strand is manual F6 Leave — which works: IsFading is false after SceneDirector.cs:569, Leave() gates only on IsFading (NetSyncDiorama.cs:264-269), and the plain Replace path is legal from any scene — and THEN the fence mops up on FieldMap. The fence is still correct and misfire-safe (verified: `_Fade` sets IsFading=true at SceneDirector.cs:253 and `_Swirl` at :551, both before their first yield, so it is true synchronously from Boot's Replace onward; the swirl's IsFading==false idle window (:569 → ReplacePending) has scene=="SwirlScene", which the fence doesn't match) — but the spec must either add a SwirlScene watchdog (Booted && scene=="SwirlScene" for >15s → Leave(), logged) or state honestly that strand recovery = F6 Leave + fence. Folded: the watchdog, since the strand's whole premise is BattleSwirl throwing every frame with player control disabled (SceneDirector.cs:555).

3) NEW FAILURE MODE THE ANSWER MISSED — the watcher-Leave vs ReplacePending NextScene race. If the host's battle lane goes stale while the guest sits in SwirlScene's IsFading==false window (after SceneDirector.cs:569), DioramaTick calls Leave() (NetSyncClient.cs:768-773) → Replace("FieldMap", FadeOutToBlack) sets NextScene and starts _Fade (IsFading true). BattleSwirl.Update still runs (SwirlScene is loaded until Leave's ChangeScene) and on rush completion calls ReplacePending (BattleSwirl.cs:61) — whose FIRST statement `NextScene = PendingNextScene` (SceneDirector.cs:148) executes unconditionally and OVERWRITES "FieldMap" with "BattleMapDebug"; only the trailing Replace(needFade) no-ops on IsFading (:519-520). Leave's in-flight _Fade then reaches ChangeScene and loads BattleMapDebug: the leave becomes a boot. Self-healing (the lane is still stale, the watcher re-Leaves after the 1 s rate limit, teardown is correct) but must be fenced: DioramaTick defers its auto-Leave while CurrentScene=="SwirlScene" (equivalently while PendingNextScene is non-empty) — the pending swirl resolves into BattleMapDebug within ~2 s and the Leave then lands cleanly.

4) Minor repairs folded: (a) the guest pre-swirl suspend must guard `cur != -1` before `ff9fldsnd_song_suspend(cur)` (GetCurrentMusicId returns -1 when idle — AllSoundDispatchPlayer.cs:94-97, currentMusicID=-1 states at :126/:195/:240 etc.); (b) `_wireSongId` must also reset in private Boot's CATCH path (NetSyncDiorama.cs:227-244), not only the manual overloads + ForceDisarm; (c) WireBenchBoot's BootFromWire call at NetSyncBattle.cs:1132 gains the songId argument (the spec updated the frame bytes but not this call); (d) cite precision: the round-trip assert is :1122-1128 and the teardown caller is HonoluluBattleMain.cs:876-877 (gated on Booted).

CONFIRMED after attack (every load-bearing claim re-read in the live tree): the baseline sound answer — plain-path diorama has NO battle BGM/SFX and the guest's field BGM plays on (ff9btlsnd_song_play census = exactly BattleSwirl.cs:96/:108 + btl_util.cs:205 end-of-battle; ChangeScene stops EFFECTS only, SceneDirector.cs:405/:463; music stopped only for MainMenu :408-409/:466-467; the field-side suspend lives only on HonoluluFieldMain.cs:315-322) · sample-the-computed-id with both patch layers inside the sampled expression (BtlBgmPatcherMapper FIRST inside GetMusicForBattle, FF9SndMetaData.cs:20-21, filled at DataPatchers.cs:677-680; s33's EffectiveFieldId wrap on the originMap arg at BattleSwirl.cs:91, kit comment present) · the stamp always precedes the first type-1 sample (song request at BattleSwirl.cs:41-45 OR :52-56, both strictly before ReplacePending :58-62, hence before gMode 2/4 → InOwnBattle NetSyncBattle.cs:500-510; world battles also swirl, WMScriptDirector.cs:222, so BattleSwirl covers ALL battle entries) · byte layout: nonce = payload offset 8 (encoder :519-545, nonce at :545; decoder :811-818), songId u16 inserts at 9-10, count moves to 11 · ONE version constant, NetSyncSocket.cs:84, written :102 validated :116 log+drop :540-543; NetSyncRelay has none (comment :17; silent old-version staleness :317-322) · swirl mechanics target-agnostic (Replace routes at SceneDirector.cs:134-138; _Swirl stash :549-550, LoadLevel SwirlScene :560, IsFading false :569) · containment predicate unchanged is correct (positive on BattleMapDebug, NetSyncDiorama.cs:71-80; selftest already drives the SwirlScene seam at :1291) · BattleSwirl never reads isDebug (whole file) · stamps land before Replace (NetSyncDiorama.cs:212-225) and isRandomEncounter drives the swirl look via SFX_Rush's ctor capture (SFX_Rush.cs:22/:37/:43) · Boot/Leave IsFading gates compose (NetSyncDiorama.cs:169-177/:264-269; Swirl's silent no-op SceneDirector.cs:542-543; instance Replace's :519-520) · plumbing sites exact (TryGetPeerBattleOpen :1072-1085; NetSyncClient.cs:740/:813-819; BattleView :94-106; _seq UInt16 :63) · the watcher only auto-boots free-standing on a field with FieldHUD (NetSyncClient.cs:802-807), so the gMode-neither-1-nor-3 risk is unreachable as stated.

</details>

---

## Lane 2 — Poison/Regen TICK figures (the StatTick marker on the type-6 lane)

# Q2 — Poison/Regen tick figures: host emit + guest apply design (verified against the live tree)

## The host's stat-tick display call (CONFIRMED)

The tick number is `btl2d.Btl2dStatReq(BTL_DATA btl, Int32 hp, Int32 mp)` — `Global/btl2d.cs:109-137`. Sign convention: positive = damage (white), negative = recover (green, `btl2d.cs:116-121, 127-133`); entries get `Yofs = -12` (`btl2d.cs:123, 135`), visually distinguishing a tick figure from an action figure — so the guest must pop through `Btl2dStatReq`, not `Btl2dReq`.

Exactly three callers exist (full-tree census, re-verified): `PoisonStatusScript.cs:34`, `RegenStatusScript.cs:43` (negative-for-heal, positive when Zombie), `VenomStatusScript.cs:42` (HP **and** MP lanes). All three are `IOprStatusScript.OnOpr` bodies dispatched from `btl_stat.cs:312-314` — **already suppressed on the guest** via `!Memoria.Netsync.NetSyncDiorama.Active`; the guest never runs tick logic, only the pop is missing. In every caller the HP/MP mutation happens BEFORE the `Btl2dStatReq` call (Poison `:25-33` → `:34`; Regen `:25-42` → `:43`; Venom `:33-41` → `:42`), so the call site is a **post-application seam**, like the B3.5 `FrameAppliedEffectList.Add` seam (`SBattleCalculator.cs:327-331`).

**Tick-kill timing (verified, was uncited):** `BattleUnit.Kill` (`BattleUnit.cs:553-557`) sets `CurrentHp = 0` → `btl_para.SetLogicalHP` writes raw `cur.hp = 0` for any genuinely killable unit BEFORE `Btl2dStatReq` runs — so `TgtHpRaw = 0` at the emit and the guest gets the controlled instant kill. Non-dying bosses floor raw at 1 (or 10000 under CustomBattleFlagsMeaning=1) and `Kill` early-returns (`BattleUnit.cs:556-557`) — wire raw is nonzero, guest stays consistent with the host; same fixpoint as the shipping action lane.

## (a) Host emit

Hook **inside `btl2d.Btl2dStatReq`**, immediately after the `btl.bi.disappear != 0` early-return (`btl2d.cs:111-112`) — if the host doesn't display, the guest doesn't either (the HP change still syncs via type-1):

```csharp
public static void Btl2dStatReq(BTL_DATA btl, Int32 hp, Int32 mp)
{
    if (btl.bi.disappear != 0)
        return;
    Memoria.Netsync.NetSyncBattle.QueueStatFrame(btl, hp, mp);  // [ff9mapkit netsync diorama] B3.6
    ...
```

One choke point covers Poison/Regen/Venom AND any mod-DLL `[StatusScript]` that uses the stock tick-display idiom; per-script hooks (3 sites) would rot. New `NetSyncBattle.QueueStatFrame(BTL_DATA btl, Int32 hp, Int32 mp)` mirrors `QueueActionFrame` (`NetSyncBattle.cs:933-1012`): `if (!Enabled) return;` OUTSIDE the try (`:935`, mirror exactly), never-throws try/catch shell (`:937, :1008-1011`), then inside — `NetSyncDiorama.Booted || FF9StateSystem.Battle.isDebug` return (`:939`, the F1 emit gate; the Booted leg ALSO kills the echo when the guest's own apply calls `Btl2dStatReq` — verified: `ApplyActionFrame` only runs while `_booted`, and `Booted => _booted`, `NetSyncDiorama.cs:83`), null-checks on `btl`/`FF9Battle` (mirror `:947-951`), `ResolveWireSlot` (`:1017-1028`, never `GetIndex`), return on `0xFF`.

**Payload: the raw display figures + post-application absolutes.** The `hp`/`mp` args are the exact signed figures the host displays; `btl.cur.hp`/`btl.cur.mp` at this point are already post-mutation — write them RAW, never logical (`NetSyncBattle.cs:988` law). **The payload's byte 0 is `_battleNonce`** (`NetSyncBattle.cs:977` — CORRECTION: the original checklist omitted it; without it the guest's nonce gate drops every stat frame silently).

## (b) Guest apply

**Does the Btl2dReqInstant trap exist on the stat path? NO (verified).** `Btl2dStatReq` is provably inert: it never harvests `IFigurePointStatusScript` modifiers (contrast `Btl2dReqInstant`'s harvest at `btl2d.cs:43-45` and `Btl2dReq`'s `modifier.OnFigurePoint` at `:64-65` — the F4 trap, `NetSyncDiorama.cs:1022-1029`), never writes `btl.fig`, and reads nothing from the unit at display time except `bi.disappear` (`:111`) and the `tar_bone` transform inside `GetFreeEntry` (`btl2d.cs:148` — CORRECTION: :148, not :149). The figure value is a pure argument. The guest calls `btl2d.Btl2dStatReq(dT, a.FigHpT, a.FigMpT)` directly — no hand-built param needed on this path.

**Could the guest's own call compute a different number? YES — the wire needs the raw figure.** The number is computed in `OnOpr`, not in `Btl2dStatReq`: `Target.MaximumHp >> 4` with EasyKill `>>= 2` and Zombie sign flip (`PoisonStatusScript.cs:27-29`, `RegenStatusScript.cs:27-31`, `VenomStatusScript.cs:27-33`). Mirrored `max.hp` can lag a reconcile beat and EasyKill/Zombie can differ mid-carry — and running `OnOpr` mutates HP and calls `Target.Kill` (the buried landmine, `diorama-lane.md` lane-3 row, suppressed at `btl_stat.cs:312-314`). The wire carries the host's displayed figure verbatim; the guest computes nothing.

In `ApplyActionFrame` (`NetSyncDiorama.cs:991-1072`), **branch STRUCTURALLY on the marker** — after step (c) computes `hiddenT`/`reviveT`, `if (a.StatTick) { figures; state; gate; return; }` BEFORE the normal steps (d)/(e). (CORRECTION of emphasis: the normal path today self-skips — `FigInfoT = 0` pops nothing in `Btl2dReq`'s display branches `btl2d.cs:74-101`, `DmgMot` false skips the flinch, `CasterSlot 0xFF` leaves `dC == null` at `:1002-1007` so the caster lanes and gate leg self-skip — but per the project's own vacuous-fence lesson, do not rely on three coincidences; make the branch explicit.)
- **Figures**: `if (dT != null && !hiddenT && (a.FigHpT != 0 || a.FigMpT != 0)) btl2d.Btl2dStatReq(dT, a.FigHpT, a.FigMpT);` — `!hiddenT` is load-bearing (F6: the guest hides via renderer toggles so `bi.disappear` never stops the pop, `NetSyncDiorama.cs:1015-1020, 1022-1029`).
- **Motions**: none — no `SetDamageMotion` exists in any of the three scripts (verified by full read).
- **State**: existing `ApplyActionState(dT, a.TargetSlot, a.TgtHpRaw == 0, reviveT, a.TgtHpRaw, a.TgtMpRaw)` (`NetSyncDiorama.cs:1078-1099`) — a poison tick that KILLS lands as the controlled instant `KillUnit`, not the ~150 ms sample kill (raw-HP-zero-at-emit verified above).
- **Gate**: existing step (h) (`NetSyncDiorama.cs:1060-1071`) target-slot leg only.

## (c) Frame type: RIDE TYPE-6 with a flags marker bit — not a new type-7 (CONFIRMED)

Keep the 46-B `PeerAction` layout (`NetSyncBattle.cs:901-924`) byte-for-byte: `[nonce u8][seqHorizon u16][casterSlot=0xFF][targetSlot]...`, `FigHpT/FigMpT` = signed stat figures, `FigInfoT = 0`, `TgtHpRaw/TgtMpRaw` = post-application raw, caster fields 0, `CmdNo = SubNo = 0`, and **`flags bit7 = STAT_TICK`** (verified free: used bits are 0,1,4,5,6 — values 1,2,16,32,64 at `:906-924`; bits 2,3,7 free). Set bit5 from `btl.bi.player` (required — the guest resolves via `TargetIsPlayer`). Add `PeerAction.StatTick => (Flags & 128) != 0`; `TryParseAction` untouched (fixed 46-B parse).

**The decisive argument is ORDERING** (verified end-to-end): one `_actionsOut` list on the host (`NetSyncBattle.cs:996-1006`), actions drain before any possibly-stale type-1 re-send of the same write tick (`NetSyncSocket.cs:240-246` CollectOutgoing), one `_inActions` queue drained to exhaustion before reconcile (`NetSyncDiorama.cs:948-978`; DRAIN-BEFORE-RECONCILE `:930-936`). A separate type-7 queue cannot preserve cross-event order against type-6. Riding type-6 = zero new dispatch surface (no new `Accept` case — `NetSyncSocket.cs:261-297`, no `INetTransport` method, no relay change). Multi-actor ticks: one 46-B frame per unit in host order; caps absorb it (`MaxQueuedActions = 64` at `NetSyncSocket.cs:196-199` on BOTH the out (`:218-233`) and in (`:280-284`) queues; `ActionBufferCap` drop-oldest self-heals via type-1, `NetSyncBattle.cs:996-1005`) — ticks are opr-countdown-paced, seconds apart (`btl_stat.cs:292-330` opr band).

**Version**: bump `NetSyncWire.Version` 9→10 (`NetSyncSocket.cs:84`); `TryParseHeader` hard-rejects other versions (`:116`), mixed DLLs fail safe to no-sync. (Degradation analysis verified: if shipped UNbumped, an old guest parses the frame fine, applies state+gate correctly, and pops nothing — `FigInfoT=0` hits no display branch in `Btl2dReq` `btl2d.cs:74-101`; degraded, not damaging. Bump anyway per the lockstep law.)

## (d) Seq-horizon: YES — consume and gate, BECAUSE the frame writes state (CONFIRMED)

Invariant: **state-write ⟺ horizon-consume**. The emit stamps `bw.Write(_seq++)` off the shared sample clock (`NetSyncBattle.cs:978`; the only other writer is the type-1 sampler at `:519`; both main-thread — `OnOpr` runs in `CheckStatusLoop` off the battle main loop). The guest stamps `_gateSeq[TargetSlot]` (`NetSyncDiorama.cs:1060-1066`); a pre-horizon type-1 sample skips the WHOLE unit record via the signed-diff wrap idiom (`NetSyncDiorama.cs:680-695, 790-797`). Without it, the documented same-flush stale-resend case regresses the tick: cosmetic HP bounce-up ordinarily, and on a tick-KILL a stale `Alive=true` fires the full revive lane. A figures-only variant is rejected: the emit seam is post-application so the absolutes are free and exact, and carrying them closes the poison-kill latency window with the existing controlled-kill machinery. One `_seq` tick per stat event starves nothing (UInt16 signed-diff wrap).

## Out of scope (declared, not closed) — EXPANDED

- **Doom/GradualPetrify countdown numerals** — persistent `HUDMessage` DEATH_SENTENCE children in `btl2d.StatusMessages` (`DoomStatusScript.cs:20-21`, `GradualPetrifyStatusScript.cs:21-22`), not `Btl2dStatReq`. Untouched.
- **(ADDED by verification) Other CalcResult-bypassing figure lanes**: `BattleUnit.DamageWithoutContext` (`BattleUnit.cs:661-688`) — a Scripts-DLL public surface with ZERO in-tree callers — routes HP through `btl_para.SetDamage/SetRecover(requestFigureNow: true)` → `Btl2dReqInstant` (`btl_para.cs:126-208`) and MP through direct `Btl2dReqMP` (`BattleUnit.cs:680, 685`). These figures still don't pop on the guest; a future emit for that lane must NOT hook `Btl2dReqInstant` (it harvests `IFigurePointStatusScript` — the F4 trap lives there). `SetTroubleDamage`/`SetPoisonMpDamage` (`btl_para.cs:304-336`) are `// Dummied` — the known trap, not live paths. Do not count any of these against this rung in the playtest.
- **BattleVoice status callouts** (`PoisonStatusScript.cs:35` etc.) remain host-only.

## Risks (verified/amended)

1) Choke-point breadth: any mod StatusScript calling `Btl2dStatReq` also emits — safe: absolutes sampled at call time. AMENDMENT: a mod script that calls `Btl2dStatReq` BEFORE mutating HP would emit pre-mutation absolutes — transient only; the next type-1 sample (seq ≥ horizon) corrects it. 2) Echo containment verified structurally: guest apply re-enters the hook, dies at the Booted gate; `Enabled` sits outside the try, mirror exactly. 3) Drop paths verified: host-side `_actionsOut`/`_outActions` drop-oldest before send — no orphan gate; the guest-side `_inActions` cap (`NetSyncSocket.cs:280-284`) can drop a frame in a burst, losing gate+state together — self-heals via type-1. 4) Version bump is lockstep-breaking by design; update BOTH machines before the playtest. 5) `GetFreeEntry` dereferences the mirrored actor's bone transform — real on a rendered diorama actor; the hidden case is fenced by `!hiddenT`; mid-boot application is already prevented by ActionTick's quiesce gates (`NetSyncDiorama.cs:948-956`).

### Implementation checklist

1. Add NetSyncBattle.QueueStatFrame(BTL_DATA btl, Int32 hp, Int32 mp): `if (!Enabled) return;` OUTSIDE the try (mirror :935); never-throws try/catch shell; inside — (NetSyncDiorama.Booted || FF9StateSystem.Battle.isDebug) return, btl/FF9Battle null checks, ResolveWireSlot != 0xFF (never GetIndex); build the 46-B type-6 payload IN ORDER: bw.Write(_battleNonce) FIRST (byte 0 — the guest's nonce gate drops the frame without it), bw.Write(_seq++) as SeqHorizon, CasterSlot=0xFF, TargetSlot, FigInfoT=0, FigHpT/FigMpT = the signed args, caster fig triple = 0, TgtHpRaw/TgtMpRaw = btl.cur.hp/cur.mp RAW post-application, CastHpRaw/CastMpRaw = 0, flags = bit5 (btl.bi.player != 0) | bit7 (STAT_TICK), CmdNo=SubNo=0; enqueue to _actionsOut with the same ActionBufferCap drop-oldest
2. Insert the one-line hook in btl2d.Btl2dStatReq AFTER the bi.disappear early-return (btl2d.cs:111-112), with a [ff9mapkit netsync diorama] bracket comment naming the echo containment (the guest apply re-enters this method; the Booted gate absorbs it)
3. Add PeerAction.StatTick => (Flags & 128) != 0 (bit 7 verified free; no payload size change; TryParseAction untouched)
4. In ApplyActionFrame, add a STRUCTURAL branch after step (c): if (a.StatTick) { if (dT != null && !hiddenT && (a.FigHpT != 0 || a.FigMpT != 0)) btl2d.Btl2dStatReq(dT, a.FigHpT, a.FigMpT); if (dT != null) ApplyActionState(dT, a.TargetSlot, a.TgtHpRaw == 0, reviveT, a.TgtHpRaw, a.TgtMpRaw); then stamp _gated/_gateSeq[a.TargetSlot]; return; } — do NOT fall through to the normal figure/motion steps even though they currently self-skip
5. Bump NetSyncWire.Version 9 -> 10 (NetSyncSocket.cs:84) with a comment naming the stat-tick lane; update BOTH machines' DLLs (mixed versions fail safe to no-sync via TryParseHeader :116)
6. Keep silent-decline parity with QueueActionFrame: the ResolveWireSlot 0xFF return stays unlogged (matches the emit side today); no new logging surface
7. Solo-tier test: poison a party member on the host with a diorama guest attached — figure pops at Yofs -12 over the mirrored actor, white for poison, green for regen; HP bar moves with the frame, not ~150 ms later; venom pops BOTH HP and MP figures; a poison tick that kills produces the controlled instant kill with no revive-flap on the next type-1 sample; a regen tick on a Zombie pops white (host sign carried verbatim)
8. Negative tests: guest not booted — stat frames drained-and-discarded (F2); host F6 debug battle emits nothing (isDebug leg); guest's own diorama apply does not echo (Booted leg)
9. Update diorama-lane.md: strike the accepted-gap line (Poison/Regen TICK figures), record the state-write <=> horizon-consume coupling law, and note the remaining out-of-scope figure lanes: Doom/GradualPetrify HUDMessage counters, BattleUnit.DamageWithoutContext / SetDamage(requestFigureNow:true) (Btl2dReqInstant — F4 trap lives there, never hook it naively), BattleVoice callouts

<details><summary>What the verify pass corrected (the record)</summary>

1) NONCE OMITTED FROM THE CHECKLIST (material implementation bug if followed literally): the type-6 payload's byte 0 is `_battleNonce` (NetSyncBattle.cs:977 `bw.Write(_battleNonce);` precedes the `_seq++` at :978); the guest's ActionTick step (a) drops any frame whose nonce mismatches BootedWireNonce (NetSyncDiorama.cs:~965-969). The original checklist enumerated every payload field EXCEPT the nonce — an implementation that followed it verbatim would have every stat frame silently discarded. Folded in.
2) VACUOUS-FENCE RELIANCE in the guest apply: the spec's 'skip the motion step entirely' and 'gate step h unchanged' rest on three self-skips that are all TRUE today (verified: DmgMot=false since flags bit0 unset; CasterSlot 0xFF leaves dC==null via `if (a.CasterSlot <= 7)` at NetSyncDiorama.cs:1002-1007; FigInfoT=0 hits no display branch in Btl2dReq, btl2d.cs:74-101) — but the branch must be STRUCTURAL (`if (a.StatTick) { figures; state; gate; return; }` after step (c)), not coincidental, per the project's own vacuous-fence lesson. Folded in.
3) UNCITED LOAD-BEARING CLAIM NOW PROVEN: 'a poison tick that KILLS lands as the controlled instant kill' required raw cur.hp==0 at the emit point — verified: BattleUnit.Kill (BattleUnit.cs:553-557) sets CurrentHp=0 → btl_para.SetLogicalHP writes raw cur.hp=0 for killable units BEFORE Btl2dStatReq runs; non-dying bosses floor raw at 1/10000 and Kill early-returns — wire stays consistent (same fixpoint as the shipping lane). The claim stands, now with proof.
4) MISSING OUT-OF-SCOPE LANE: BattleUnit.DamageWithoutContext (BattleUnit.cs:661-688; zero in-tree callers, Scripts-DLL surface) is ANOTHER CalcResult-bypassing figure path (SetDamage/SetRecover requestFigureNow:true → Btl2dReqInstant, btl_para.cs:126-208; direct Btl2dReqMP at BattleUnit.cs:680/685). SetTroubleDamage/SetPoisonMpDamage (btl_para.cs:304-336) are '// Dummied' — the exact trap the brief warns about, correctly NOT treated as live by the answer. Added to out-of-scope so the playtest doesn't count them.
5) CITE FIXES (minor): GetFreeEntry's transform read is btl2d.cs:148, not :149; the OnOpr suppression is exactly btl_stat.cs:312-314 (Active condition :313, call :314) — answer correct; Btl2dReq's modifier harvest at :64-65 with the disappear gate at :62 — answer's :59-65 range fine; flag-bit census re-verified from the struct properties (used values 1,2,16,32,64 = bits 0,1,4,5,6; bit7=128 free) — answer correct; Version=9 at NetSyncSocket.cs:84 and the hard reject at :116 — answer correct; MaxQueuedActions=64 at :196, out-queue drop :218-233, in-queue drop :280-284 — answer correct, with the guest-side in-queue drop nuance added to risks.
All other claims (the 3-caller census, Btl2dStatReq inertness, sign/Yofs convention, the suppression already shipped, drain ordering, horizon mechanics, degradation analysis of an unbumped guest, Doom/GradualPetrify path) re-read at the cited lines and CONFIRMED.

</details>

---

## Lane 3 — the spectate panel becomes the no-diorama fallback

# B3.6 — the spectate panel becomes the no-diorama fallback (verified spec)

## 1. The panel's draw gate today
- The entire B0/B1 panel is ONE method: `NetSyncBattle.DrawGUI()` at NetSyncBattle.cs:1524-1597. Its only gate is :1528 `if (!PeerBattleLive || _peerView == null) return;`.
- Called unconditionally from `NetSyncClient.OnGUI()` (NetSyncClient.cs:954-956); NetSyncClient is DontDestroyOnLoad (:156), so it draws over EVERY scene including BattleMapDebug.
- The B1 assist digit-menu UI is the LOWER HALF OF THE SAME PANEL: `AppendMenu` (NetSyncBattle.cs:1600-1676), invoked at :1584 — UiRoot/UiAbility/UiItem/UiTarget, "command sent..." (:1608-1612), the "(waiting for your character's ATB)" idle hint (:1602-1606). No second OnGUI path exists (grep: only NetSyncClient.OnGUI and DrawGUI).
- Assist INPUT is independent of drawing: RunAssistUi/AssistInputActive/SetLocalControl run in Pump (:368-389) and SelfTestPump (:468-481), never in DrawGUI. Pump:284 `inBattle = InOwnBattle(ee) && !NetSyncDiorama.Booted`; inside the diorama gMode stays 1 (isDebug skips StartEvents), InOwnBattle is false, so the :370 `live && !inBattle` assist branch HOLDS over the diorama by design (diorama-lane.md:300-301).

## 2. Every state where the diorama is NOT live but battle frames flow (panel must survive)
Durable (whole-battle) — the panel is the ONLY battle surface:
1. Diorama=0 opt-out — NetSyncClient.cs:66/:283; DioramaTick returns at :761-762; "the old spectate panel only" (:25-28).
2. FollowHost=0 spectate-only guest — same :761 gate, rising-edge log :754-756.
3. Host side — when the GUEST fights, its frames set PeerBattleLive on the host; the host can never boot a diorama because `MayBoot` (NetSyncDiorama.cs:98-99) requires IsMirroringStory (guest-only, NetSyncClient.cs:176-180) / IsLiveFollowedSession (role=client, :219-243) / IsSelfTestRole — Boot refuses at :159-163. (A misconfigured host with FollowHost=1+Diorama=1 passes DioramaTick:761 and gets a rate-limited refusal log ~1/s — pre-existing cosmetic, out of scope.)
4. Guest on the WORLDMAP for the whole battle — `onField` (NetSyncClient.cs:509) requires gMode==1 && fieldmap != null; DioramaTick:802-803 never boots; the panel draws there (DontDestroyOnLoad OnGUI).
5. Scene-not-installed skip — NetSyncClient.cs:786-794 (`_dioramaSkipNonce = nonce`, "spectate panel only") + the mapName-unavailable catch :796-801.
6. F6 leave (per-battle opt-out) — leave while the lane is fresh with the same nonce → skip-nonce (:728-737), honored at :782-783; Booted false after ForceDisarm (NetSyncDiorama.cs:288-299), frames keep flowing.
7. Wire-refused boot — BootFromWire scene-id refusal (NetSyncDiorama.cs:141-148), MayBoot false (:159-163), fade-in-flight (:169-178), snapshot-failed (:183-195), boot exception (:227-244). All leave _booted false.
8. Both-in-battle — guest fighting its own battle: spectate-only (no assist, :370), no boot (onField false).
9. Selftest loopback — SelfTestPump sets PeerBattleLive with no diorama; the panel header is the documented encode-proof (NetSyncBattle.cs:1093-1095, :1543-1548).
10. Stranded `_booted` on a live FIELD — Boot's Replace silently dropped (the fade TOCTOU between the :169-178 check and :225 Replace, the silent-drop mechanism Boot's own :164-168 comment describes): Booted true, no diorama pixels, frames flow. THE decisive argument for Active over Booted. (Note: Leave's dropped-Replace case — the :255-256 retry doc — is NOT this state: there the scene is still BattleMapDebug and Active is correctly TRUE.)
Transient (panel flashes, fail-safe direction): guest mid-menu/mid-transition (:802-809), the 1 s rate limit (:810-812), the boot fade-out window (Booted true, loadedLevelName still the field → Active false, full panel over the fading field — every boot, cosmetic), back-to-back battle between Leave and re-boot (:768-774).
(No-frames states — wire-version-rejected peer, stale lane — are not fallback states: PeerBattleLive false, :1528 hides the panel correctly.)

## 3. The predicate change — exact spec
**Suppress on `NetSyncDiorama.Active`, never `Booted`.**
- Active (NetSyncDiorama.cs:71-80) = `_armed && _booted && loadedLevelName == "BattleMapDebug"` — the containment predicate: POSITIVE, engine-authoritative, true exactly while diorama pixels are the live scene. Suppression keyed on it fails toward DRAWING the fallback (worst case: clutter; a Booted key's worst case is hiding the guest's only battle surface).
- Leave is request-only (NetSyncDiorama.cs:258-278): during the leave fade Booted AND Active are both still true (scene still BattleMapDebug) → panel stays suppressed while diorama pixels fade; on FieldMap arrival HonoluluBattleMain.OnDestroy fires ForceDisarm gated on Booted (HonoluluBattleMain.cs:876-877) → panel returns. The flags outlasting the scene is exactly what Active's scene-name term absorbs.
- Booted-true-on-a-field windows (boot fade-out every boot; the Boot TOCTOU strand): Active false there → panel shows; a Booted key would blank it.
- Symmetry: QueueActionFrame's Booted gate (NetSyncBattle.cs:935-940) is the OPPOSITE fail direction on purpose (never stream back to the host) — do not copy it here.
**The change is INSIDE DrawGUI, not at the NetSyncClient.cs:956 call site** — gating the call would hide AppendMenu, the guest's only command surface.

### Code shape (NetSyncBattle.cs)
DrawGUI (:1524) — between the unchanged :1528 gate and the box draw:
```csharp
if (!PeerBattleLive || _peerView == null)
    return;                                   // unchanged: no frames -> nothing
// B3.6: while the diorama's scene is LIVE the fight is on screen -- the roster is clutter.
// Key on Active (the loadedLevelName containment predicate), never Booted: Leave is
// request-only so _booted outlasts the scene, and a dropped Replace strands _booted TRUE
// on a field -- every uncertainty must fail toward DRAWING the fallback panel.
Boolean dioramaLive = NetSyncDiorama.Active;
BattleView view = _peerView;
if (_panelStyle == null) { ... }              // unchanged (:1531-1540)
Int32 mySlot = FirstReadyGuestSlot(view);     // HOISTED above the roster block (was :1564)
StringBuilder sb = new StringBuilder(768);
if (!dioramaLive)
{
    // :1542-1583 verbatim: header + boot-block diag, enemy list, party HP/MP/ATB lines
}
AppendMenu(sb, view, mySlot, dioramaLive);    // ALWAYS: the B1 assist UI must draw over the diorama
if (sb.Length == 0)
    return;                                   // diorama live + nothing to say (GuestSlots=0 pure
                                              // spectate, or idle between turns) -> fully quiet;
                                              // also guards CalcSize on empty content
// :1586-1591 verbatim: CalcSize + box + label
```
AppendMenu (:1600) — add `Boolean dioramaLive`; single body change at :1602-1606:
```csharp
if (mySlot < 0)
{
    if (view.GuestSlots != 0 && !dioramaLive)   // over the diorama the mirrored HUD's own ATB
        sb.Append("(waiting for your character's ATB)");   // gauges already say this
    return;
}
```
Everything else in AppendMenu (UiRoot :1616-1629, UiAbility :1630-1645, UiItem :1646-1662, UiTarget :1663-1674, "command sent..." :1608-1612) untouched and draws over the diorama.

## 4. Proof the B1 assist menu cannot be hidden
1. Input path untouched: RunAssistUi/AssistInputActive/SwallowAssistKey/SetLocalControl live in Pump/SelfTestPump (NetSyncBattle.cs:368-389, 468-481, 224-234) — DrawGUI is render-only; keys work even with the panel invisible.
2. Draw path: AppendMenu runs on every frame that passes the unchanged :1528 gate. dioramaLive trims only (a) roster lines and (b) the idle hint. Every interactive state (_uiMode Root/Ability/Item/Target, post-send "command sent...") appends text → sb.Length > 0 → the box draws. Fully-quiet cases: mySlot < 0 with GuestSlots == 0 (nothing to command) or idle-over-diorama (mirrored HUD shows ATB; the box reappears the frame FirstReadyGuestSlot fires).
3. Reachability over the diorama: Pump:284's `!NetSyncDiorama.Booted` (defense in depth — gMode stays 1 anyway, :276-283) keeps inBattle false, so :370 `live && !inBattle` holds; AssistInputActive arms; digits are swallowed via the UIKeyTrigger hook (:221-234).
4. Call site unchanged: NetSyncClient.OnGUI:956 still calls DrawGUI on every scene.

## 5. Idle-overlay interplay (no change needed)
- The overlay is a separate surface (_ovlText, drawn NetSyncClient.cs:957-975). During the peer's battle it is already OFF: the chain at :661-680 reaches `else if (NetSyncBattle.PeerBattleLive) SetOverlay(OvlOff)` (:676-677) — reachable because the host broadcasts the field-0 sentinel off-field so the :671/:674 mismatch branches don't fire.
- Inside the diorama `local` is null and the earlier branches resolve to OvlOff/OvlConnecting-family states before OvlPeerElsewhere can fire for an in-battle host; no "friend is on another screen" over the diorama.
- This change never touches PeerBattleLive (set purely from lane freshness, NetSyncBattle.cs:368-369) — overlay logic bit-identical in every state. Diorama live + GuestSlots=0: overlay off AND panel off — correct, the diorama is the status. In every fallback state PeerBattleLive is unchanged-true and the panel draws in full.

## 6. Verification plan (corrected)
**The suppression branch (Active && PeerBattleLive) is NOT solo-reachable with the current benches**: WireBenchBoot (NetSyncBattle.cs:1096-1140) never sets _peerView, and SelfTestPump requires InOwnBattle (:411) which is false inside the diorama — PeerBattleLive is false in every solo diorama, so the :1528 gate already hides the panel there (diorama-lane.md:306-307). Solo therefore proves NON-REGRESSION only; suppression itself is a two-machine box. OPTIONAL solo enabler: extend WireBenchBoot to also stamp `_peerView = view; _peerViewTick = Environment.TickCount;` with a fabricated units+GuestSlots frame before booting — then the suppressed-roster + live-menu render becomes benchable solo (internal test hook, no wire change).

WIRE: none — guest-side render predicate only; wire stays v9.

RISKS: 1) Idle-over-diorama total silence (GuestSlots!=0, between turns): deliberate — the mirrored HUD's ATB gauges carry it; if playtest reads it as "assist broke", re-enable the one-line hint over the diorama. 2) Boot fade-out flicker: full panel over the fading field for a few frames (Active false, every boot) — cosmetic, fail-safe direction, not worth a bootInFlight term. 3) AppendMenu signature change is private/single-caller (grep-verified: only :1584). 4) The panel box (left, y=0.22*Screen.height) may overlap the diorama's battle HUD when the menu draws; if it collides, move the menu-only box — do not re-suppress it.

### Implementation checklist

1. NetSyncBattle.DrawGUI: add `Boolean dioramaLive = NetSyncDiorama.Active;` after the :1528 gate (gate itself unchanged)
2. NetSyncBattle.DrawGUI: hoist `Int32 mySlot = FirstReadyGuestSlot(view);` above the roster block (from :1564)
3. NetSyncBattle.DrawGUI: wrap ONLY :1542-1583 (header+enemies+party) in `if (!dioramaLive) { ... }` — AppendMenu stays unconditional
4. NetSyncBattle.DrawGUI: add `if (sb.Length == 0) return;` before CalcSize/box draw
5. NetSyncBattle.AppendMenu: add `Boolean dioramaLive` param; suppress only the '(waiting for your character's ATB)' hint when dioramaLive; all menu states + 'command sent...' untouched
6. Do NOT touch NetSyncClient.OnGUI:956, PeerBattleLive, or the overlay chain (NetSyncClient.cs:661-680)
7. Predicate is Active, not Booted: boot fade-out + the Boot TOCTOU strand (Booted true on a field) must still show the panel; the leave fade (scene still BattleMapDebug) must stay suppressed
8. Solo regression: a real selftest encounter still shows the FULL panel incl. the [scene/pat/start/rand] header (no diorama booted — PeerBattleLive true, Active false)
9. Solo regression: F6 wire-bench diorama shows NO panel at all, same as today (PeerBattleLive is false in every solo diorama — WireBenchBoot never sets _peerView, SelfTestPump needs InOwnBattle; the suppression branch is NOT solo-reachable as-is)
10. OPTIONAL solo enabler: extend WireBenchBoot to stamp _peerView/_peerViewTick with a fabricated units+GuestSlots frame, making suppressed-roster + live-menu render benchable solo (internal hook, no wire change)
11. Two-machine (deferred): host fights with GuestSlots set -> guest's diorama shows only the digit-menu box on turns and takes digits; F6 Leave -> full panel returns on the field; Diorama=0 rerun -> full panel as today; host-side check -> full panel while the guest fights

<details><summary>What the verify pass corrected (the record)</summary>

1) THE SOLO-PROOF CHECKLIST ITEM IS IMPOSSIBLE ("F6 wire-bench diorama -> roster lines gone, assist menu still draws and takes digits"). Inside ANY solo diorama PeerBattleLive is FALSE, so the :1528 gate hides the whole panel before the new dioramaLive logic is ever reached: WireBenchBoot (NetSyncBattle.cs:1096-1140) parses the fabricated frame into a LOCAL `view` (:1116) and boots from it (:1132) — it never assigns `_peerView`/`_peerViewTick`; and SelfTestPump requires `InOwnBattle(ee)` (:411), which is false inside the diorama (gMode stays 1 — NetSyncBattle.cs:406-410 comment, diorama-lane.md:297-299), so it Reset()s and sets `PeerBattleLive = false` (:414-419). diorama-lane.md:306-307 states it outright: "The panel does NOT render inside a bench diorama — no sampling at gMode 1." Active && PeerBattleLive coexist ONLY on a real wire session. The suppression branch is therefore two-machine-only unless the wire bench is optionally extended to also stuff `_peerView`/`_peerViewTick` with a units+GuestSlots frame. Checklist item replaced.
2) HOST-SIDE NO-BOOT JUSTIFICATION IMPRECISE. The answer said the host never boots because "FollowHost/Diorama are guest-side settings" — but a host CAN set FollowHost=1/Diorama=1 in Memoria.ini (nothing role-gates the parse, NetSyncClient.cs:282-283) and DioramaTick:761 would then pass. The real backstop is MayBoot (NetSyncDiorama.cs:98-99): IsMirroringStory (guest-only — never mirrors onto a host, NetSyncClient.cs:176-180), IsLiveFollowedSession (requires role=client, NetSyncClient.cs:219-243), or IsSelfTestRole — Boot refuses at NetSyncDiorama.cs:159-163. Conclusion unchanged (host panel is a durable fallback state); adds one pre-existing cosmetic edge (misconfigured host re-logs the MayBoot refusal ~1/s during the guest's fight via the :810-812 rate limit — not this rung's concern).
3) GUEST-ON-WORLDMAP IS A DURABLE FALLBACK STATE, NOT TRANSIENT. `onField` (NetSyncClient.cs:509) = `fld > 0 && ee.gMode == 1 && ee.fieldmap != null` — a guest spending the whole host battle on the worldmap never passes DioramaTick:802-803, so the panel is the ONLY surface there for the entire fight (OnGUI is DontDestroyOnLoad, NetSyncClient.cs:156, so it draws on the worldmap). The answer filed !onField under transient #10 only.
4) STATE #9 CITE MISATTRIBUTED. NetSyncDiorama.cs:255-256 is LEAVE's retry-button doc — when Leave's Replace is dropped the scene is still BattleMapDebug and Active stays TRUE (suppressed, correctly: diorama pixels are still up). The genuine Booted-true-on-a-FIELD windows are (a) Boot's fade-out window every boot (Replace in flight, loadedLevelName still the field — HonoluluBattleMain hasn't Awoken) and (b) the narrow Boot TOCTOU (a fade starting between the IsFading check :169-178 and Replace :225 makes Replace silently no-op — the exact silent-drop mechanism Boot's own comment :164-168 describes). Both have Active=false (NetSyncDiorama.cs:71-80) and Booted=true, and both are exactly where a Booted-keyed suppression would blank the guest's only battle surface — the Active-over-Booted conclusion is CONFIRMED, on corrected evidence.
Everything else CONFIRMED at the cited lines: DrawGUI NetSyncBattle.cs:1524-1597 (sole gate :1528; roster :1542-1583; AppendMenu call :1584); AppendMenu :1600-1676 is the B1 menu, single caller (grep: only :1584), waiting hint :1602-1606, command-sent :1608-1612; Pump `inBattle = InOwnBattle(ee) && !NetSyncDiorama.Booted` :284, PeerBattleLive from lane freshness :368-369, assist branch `live && !inBattle` :370-378; SwallowAssistKey :224-234; QueueActionFrame's opposite-direction gate :935-940 (`NetSyncDiorama.Booted || isDebug`); NetSyncClient.OnGUI :954-956 unconditional DrawGUI, overlay draw :957-975, DontDestroyOnLoad :156, _diorama default ON :66/:283; DioramaTick :726-821 (skip-nonce :728-737/:782-783, rising-edge log :746-759, guest-only auto-boot :761-762, leave-watch :764-774, scene-not-installed :786-794 + catch :796-801, onField :802-803, UIState :806-809, rate limit :810-812, wire-boot stamp :813-820); overlay chain :661-680 with PeerBattleLive->OvlOff :676-677; Active :71-80 / Booted :83; BootFromWire refusal :141-148; snapshot-fail :183-195; boot-exception :227-244; Leave :258-278; ForceDisarm :288-299, called from HonoluluBattleMain.cs:876-877 gated on Booted (leave-return mechanism holds); selftest panel-as-encode-proof NetSyncBattle.cs:1093-1095; diorama-lane.md:300-301 (assist usable over the diorama by design) and :430-431 (B3.6 intent).

</details>

---

## Lane 4 — the F6 opt-out intro replay (root-caused: the staleness flicker clears the skip)

# Q4 — F6 opt-out intro replay: VERDICT (verified against the live tree)

## Suspect (a) — staleness flicker clearing the skip-nonce: **REAL, DETERMINISTIC, the bug**

The exact path (all guest-side, host's battle live throughout):

1. Guest F6-leaves → teardown (ForceDisarm from HonoluluBattleMain.OnDestroy, gated on Booted — NetSyncDiorama.cs:288-299) → next `DioramaTick`: `_dioramaSkipNonce = _dioramaWireNonce` (NetSyncClient.cs:728-737).
2. The lane blips stale: `live = _peerView != null && (TickCount - _peerViewTick) < StaleMs(2000)` (NetSyncBattle.cs:368, :50), and `_peerViewTick` restamps ONLY when `view.Seq` advances (NetSyncBattle.cs:352-362, the STACKED-STALENESS fix). Any ≥2s gap in seq-advancing frames flips `PeerBattleLive` false and nulls `_peerView` (NetSyncBattle.cs:369, :385).
3. Same Update, `DioramaTick` runs after `Pump` (NetSyncClient.cs:684 → :694): `TryGetPeerBattleOpen` returns false (gates on `PeerBattleLive`, NetSyncBattle.cs:1077) → the `!live` branch executes **`_dioramaSkipNonce = -1`** (NetSyncClient.cs:741-744). Staleness is treated as a battle boundary; it is a transport condition.
4. The lane recovers with the SAME nonce (the host never left the fight; the write thread re-sends the latest battle frame every ~33ms unconditionally — NetSyncSocket.cs:566, CollectOutgoing :248) → `nonce == _dioramaSkipNonce` at NetSyncClient.cs:782 no longer matches → `BootFromWire` re-boots the same fight (NetSyncClient.cs:810-820) → the intro replays once.

Deterministic ≥2s-gap triggers, from source: transport reconnect (2000ms backoff, NetSyncSocket.cs:503, plus `ClearRemote` on drop :523); a host main-thread stall >2s (`_seq` advances only when Pump samples — NetSyncBattle.cs:293-296, :519 — so the guest's seq-keyed restamp freezes even though frames keep flowing); any plain >2s delivery gap (WS relay). NOT a trigger: a guest-side load stall (receive is a background thread, NetSyncSocket.cs:408-413; Accept stamps `_inBattleTick` there, :271-273; Pump restamps before DioramaTick in the same Update) — which is why the replay was intermittent.

Collateral of the same branch: the modded-scene skip (NetSyncClient.cs:791, :798) is also wiped by every blip, so its one-line-per-fight promise re-logs after each flicker. The fix repairs that too.

## Suspect (b) — host-side InOwnBattle flap bumping the nonce mid-fight: **NOT REAL (no source mechanism)**

`_battleNonce++` occurs in exactly two places: the Pump rising edge of `InOwnBattle(ee) && !NetSyncDiorama.Booted` (NetSyncBattle.cs:284-289) and SelfTestPump (:423, selftest role only). `InOwnBattle` = `gMode ∈ {2,4} && btl_list.next != null` (NetSyncBattle.cs:500-508; catch-all returns false :509): gMode 2/4 is written only by `EventEngine.StartEvents` at battle boot (verified-against-source comment, NetSyncBattle.cs:276-279); `btl_list.next` never unlinks mid-fight; a host Update stall means no Pump and therefore no edge sampling at all. Even if it occurred, a new nonce is by definition a new battle (NetSyncBattle.cs:289, :104) and the skip is documented per-battle (NetSyncClient.cs:733-734).

## The fix — the skip dies on a NONCE CHANGE, never on staleness; and the watcher's own leave never stamps it

Keyed on **lane nonce continuity** — not mapNo+patNum (same-map back-to-back fights are deliberately distinct battles, NetSyncBattle.cs:104), not liveness (a transport condition). Every true battle start bumps the nonce (NetSyncBattle.cs:289), so "a live frame carries a different nonce" IS the true battle boundary.

**Part 1 — DioramaTick (NetSyncClient.cs:741-744):** replace the `!live` clear with keep-both, and add a spend clause ahead of the rising-edge diagnostic:

```csharp
if (!live)
{
    // KEEP the skip (and the seen-nonce): staleness is NOT a battle boundary -- a relay
    // hiccup, a host alt-tab, or the 2s reconnect backoff (NetSyncSocket ClientLoop)
    // flickers the lane mid-fight, and clearing here re-booted an opted-out battle's
    // intro on recovery. The skip is spent below, when a DIFFERENT nonce goes live --
    // and the nonce bumps on every true battle start, so nothing future is suppressed.
}
else if (_dioramaSkipNonce >= 0 && nonce != _dioramaSkipNonce)
{
    Log.Message("[NetSync] diorama opt-out spent: a new peer battle (nonce " + nonce + ")");
    _dioramaSkipNonce = -1;
    _dioramaSeenNonce = -1;   // fresh battle -> re-arm the one-line rising-edge diagnostic
}
```

The existing rising-edge `else if` (:746-759) follows unchanged; the :782 gate is untouched and now reliably matches across blips. Ordering stays correct: the spend runs before :782 in the same pass, so a genuinely-new battle boots on its first live tick.

**Part 2 — the watcher's own leave must not stamp the opt-out (companion, 3 lines).** The :728 stamp infers user-intent from "lane still fresh, same nonce" (:730-734), but the watcher's staleness-leave (:768-772) is request-only and teardown lands ~1 fade later (NetSyncDiorama.cs:248-256) — if the lane recovers inside that window (likely, given the 2s backoff), the watcher's leave is misread as a user opt-out. Today that self-heals at the next blip via the very clear being removed; Part 1 alone would extend it to the rest of the fight. Add a guest-local `private Boolean _dioramaWatcherLeft;`:
- set `_dioramaWatcherLeft = true;` beside `NetSyncDiorama.Leave()` at NetSyncClient.cs:772;
- at the :728 block: if `_dioramaWatcherLeft` is set, consume it (`_dioramaWatcherLeft = false`) and clear `_dioramaWireNonce` WITHOUT stamping the skip (and without the opt-out log); otherwise stamp skip as today and log one line: `"[NetSync] diorama opt-out noted (nonce " + _dioramaSkipNonce + ") -- the watcher won't re-boot this battle"`;
- reset `_dioramaWatcherLeft = false;` in the boot-stamp block at :814-820.

**Part 3 — boot-stamp telemetry:** append `" nonce=" + nonce` inside the `if (NetSyncDiorama.Booted)` block at NetSyncClient.cs:814-820 (guest-local; the NetSyncDiorama.cs:223-224 BOOT line has no nonce and shouldn't grow a wire-lane dependency).

## Telemetry — was B3.3b sufficient? **No, as shipped**

The rising-edge diagnostic (:746-759) logs only decline cases; the BOOT log omits the nonce (NetSyncDiorama.cs:223-224); the skip lifecycle was silent at both ends (:735 set, :743 clear). The fix bakes in all three decisive lines (opt-out-noted, opt-out-spent, boot nonce) per the BootBlockedReason principle — the signatures: (a) = opt-out-noted N → BOOT nonce=N again with no spend line; (b) would have been BOOT nonce=N then BOOT nonce=N+1.

No established law is violated: Leave stays request-only, no IsOver writes, no isDebug reads, tick baselines untouched, staleness stays seq-keyed (STACKED-STALENESS respected — the fix consumes staleness correctly instead of overloading it as battle-over).

WIRE: none — all changes are guest-local watcher logic and log lines; wire stays v9.

RISKS:
- Byte nonce wrap (256 battles): a persisted skip matching a much-later battle needs 256 consecutive battles with zero live frames seen between them — practically impossible (same accepted profile as BootedWireNonce, NetSyncDiorama.cs:89-93).
- **HOST RELAUNCH nonce reset (new):** `_battleNonce` is a static Byte (NetSyncBattle.cs:68) — a host process restart resets it, and the transport auto-reconnects (NetSyncSocket.cs:380-382, :475-481). If the persisted skip is exactly the nonce the relaunched host's first battle carries (i.e., the guest had opted out of the previous host session's FIRST battle), one genuinely-new battle is silently skipped; the next battle spends the skip. Bounded, self-healing, and now visible in the logs (opt-out-noted N ... BOOT never fires, then opt-out-spent at N+1). Optional hardening if it ever bites: clear the skip at a true session-end boundary (the exit-ramp / peer-alive path), never on mere staleness.
- Part 2 residual: a DEFERRED watcher-leave (fade in flight, NetSyncDiorama.cs:265-268) whose trigger evaporates leaves `_dioramaWatcherLeft` stale; one subsequent genuine user opt-out in that same fight is then missed once (the watcher re-boots; the second F6-leave sticks, and the missing opt-out-noted line flags it). Rare-squared vs. the whole-fight silent stay-out it closes.
- Behavioral change: `_dioramaSkipNonce` may now be ≥0 while the lane is dead — no future reader may assume -1 there (grep confirms current readers are only NetSyncClient.cs:121/735/743/782/791/798).
- The (b) verdict rests on gMode 2/4 having no mid-battle writer (asserted verified-against-source at NetSyncBattle.cs:276-279); the boot-nonce log makes any future violation immediately visible.

### Implementation checklist

1. Edit NetSyncClient.cs DioramaTick: the `!live` branch (lines 741-744) KEEPS _dioramaSkipNonce and _dioramaSeenNonce, with the staleness-is-not-a-battle-boundary comment
2. Insert the spend clause between the `!live` branch and the :746 rising-edge block: `else if (_dioramaSkipNonce >= 0 && nonce != _dioramaSkipNonce) { log 'opt-out spent (nonce N)'; _dioramaSkipNonce = -1; _dioramaSeenNonce = -1; }`
3. Add `_dioramaWatcherLeft` (Boolean field beside _dioramaSkipNonce at NetSyncClient.cs:121): set true beside the watcher's NetSyncDiorama.Leave() call at :772; consume at the :728 block (suppress the skip stamp + clear the flag); reset false in the boot-stamp block at :814-820
4. In the :728 block's user-opt-out path (flag NOT set), log one line: 'diorama opt-out noted (nonce N) -- the watcher won't re-boot this battle'
5. Append ` nonce=` + nonce to the guest-local boot stamp inside the `if (NetSyncDiorama.Booted)` block at NetSyncClient.cs:814-820 (do NOT touch the NetSyncDiorama.cs:223 BOOT line)
6. Verify the :782 skip gate and the :746 rising-edge diagnostic are byte-untouched and ordered after the spend clause
7. Confirm no other reader of _dioramaSkipNonce assumes -1 while the lane is stale (grep: NetSyncClient.cs 121/735/743/782/791/798 only)
8. Solo-tier repro: F6-leave a bench/selftest watcher battle, force a >2s lane gap (kill/restore the relay or alt-tab the host), confirm NO second BOOT line, the skip survives, and the 'opt-out noted' line printed once; then a NEW host fight prints 'opt-out spent' + boots with the new nonce in the stamp log
9. Solo-tier regression: force a blip on an ACTIVELY-watched (non-opted-out) diorama so the watcher Leaves; confirm the guest RE-BOOTS on recovery (the _dioramaWatcherLeft flag suppressed the skip stamp) instead of silently staying out
10. Confirm the modded-scene skip (NetSyncClient.cs:791/798) logs its one line once per fight across blips, and re-evaluates on the next battle via the spend clause
11. Two-machine confirmation next session: guest F6-leaves mid-host-fight, host alt-tabs 3s, guest stays out (no second intro); host's next fight boots normally with the spent line; optionally relaunch the host mid-skip to observe the documented nonce-reset edge in the logs

<details><summary>What the verify pass corrected (the record)</summary>

Every load-bearing claim in the original answer was re-read in the live tree and CONFIRMED: the !live branch clears the skip (NetSyncClient.cs:741-744); DioramaTick runs after Pump in the same Update (NetSyncClient.cs:684 vs :694); staleness is seq-keyed with StaleMs=2000 (NetSyncBattle.cs:352-362, :368, :50) and nulls _peerView (:385); TryGetPeerBattleOpen gates on PeerBattleLive (NetSyncBattle.cs:1077); the nonce producer bumps only at NetSyncBattle.cs:289 (Pump rising edge) and :423 (SelfTestPump; grep confirms :545/:977 are writes-to-wire, not bumps); InOwnBattle = gMode∈{2,4} && btl_list.next != null with a swallow-all catch returning false (NetSyncBattle.cs:500-510); ClientLoop backoff is 2000ms (NetSyncSocket.cs:503); the write thread re-sends the latest-slot battle frame unconditionally every ~33ms (NetSyncSocket.cs:566, CollectOutgoing:248) while _seq advances only in SampleOwnBattle (:519) — so the transport-reconnect and host-stall triggers are both deterministic as claimed; receive runs on a background thread and Accept stamps _inBattleTick there (NetSyncSocket.cs:408-413, :271-273), so a guest-side stall is indeed safe; the BOOT log omits the nonce (NetSyncDiorama.cs:223-224); the skip-gate at :782 and the readers list (121/735/743/782/791/798) are complete per grep.

THREE MATERIAL CORRECTIONS:

(1) AGGRAVATED PRE-EXISTING MISCLASSIFICATION (uncited by the answer). The opt-out stamp at NetSyncClient.cs:728-737 infers "the USER left deliberately" from "lane still fresh with the SAME nonce" (comment :730-734). But the WATCHER's own staleness-leave (:768-772, Leave() on !live) is request-only; teardown lands later at ForceDisarm/OnDestroy (NetSyncDiorama.cs:248-256, :288-299). If the lane recovers inside that request→teardown window (likely: the blip is bounded by the 2s backoff, the fade takes ~1s), the stamp block misreads the watcher's leave as a user opt-out and sets skip=N on a still-live fight. TODAY that mistake self-heals at the next blip (the very bug's clear at :743). THE PROPOSED FIX REMOVES THAT SELF-HEAL, extending the guest's silent stay-out from "until the next blip" to "the rest of battle N". Companion fix required (3 lines, guest-local): a _dioramaWatcherLeft flag set beside the Leave() call at :772, consumed at :728 to suppress the skip stamp, reset at the boot stamp (:816). Residual (accepted, documented): a DEFERRED watcher-leave (fade in flight, NetSyncDiorama.cs:265-268) whose trigger condition then evaporates leaves the flag stale; a later genuine user opt-out in that same fight is then missed ONCE (the watcher pulls them back; their second F6-leave sticks) — rare-squared and self-healing, vs. the whole-fight silent stay-out it closes.

(2) NEW RISK the answer missed: HOST RELAUNCH RESETS THE NONCE. _battleNonce is a static Byte (NetSyncBattle.cs:68) — a host process restart resets it to 0, and the transport auto-reconnects (NetSyncSocket.cs:380-382, HostLoop :475-481). With the skip now surviving the outage, the host's first post-relaunch battle carries nonce 1; if the persisted skip is exactly 1 (the guest had F6-left the host's FIRST battle of the previous host session), that genuinely-new battle is silently skipped. Bounded and self-healing (battle 2 carries nonce 2 → the spend clause clears), but it must be named in RISKS and made visible by logs.

(3) TELEMETRY PROMOTION: the skip-SET at :735 (and the whole :782 decline) is silent today; the answer left the skip-set line as a diagnose-first option. With the skip now long-lived (whole fights, and across outages per (2)), the set-line is folded into the shipping spec: one log line when the opt-out stamps (in the :728 block) plus the spend line plus the nonce on the boot stamp. This is the BootBlockedReason principle applied to the two silent decisions this change makes longer-lived.

Minor cite repairs: BootedWireNonce is declared at NetSyncDiorama.cs:93 (comment :85-92; the answer cited 90-93 — harmless); the wrap-risk comment is at :89-91 ✓.

</details>

---

## Lane 5 — guest-side PatNum validation (sync pre-read, behind the rate limit)

## Q5 — Guest-side pattern-index validation: SYNC PRE-READ IS SAFE. Do it — with the watcher call placed BEHIND the rate limit.

### How the boot consumes PatNum today (the throw path — all verified in the live tree)
1. `HonoluluBattleMain.Start` (HonoluluBattleMain.cs:132) wraps everything in `catch (Exception err) { Log.Error(err); }` (:177-180) — the swallow the question names.
2. `InitBattleScene` (:152 → :183) resolves the scene name: `FF9BattleDB.SceneData.TryGetKey(FF9StateSystem.Battle.battleMapIndex, out battleSceneName)` then `battleSceneName.Substring(4)` (:198-199 — a SceneData miss NREs at :199), then `this.btlScene.ReadBattleScene(battleSceneName)` (:201).
3. `BTL_SCENE.ReadBattleScene` loads the scene binary **synchronously**: `AssetManager.LoadBytes("BattleMap/BattleScene/EVT_BATTLE_" + name + "/dbfile0000.raw16")` (BTL_SCENE.cs:15; null → early return leaving `PatAddr` null, :16-17). **The pattern count is byte 1 of that binary**: header = Ver(0), PatCount(1), TypCount(2), AtkCount(3), Flags(4-5) (BTL_SCENE.cs:20-24), and `PatAddr = new SB2_PATTERN[header.PatCount]` (:25) — `bytes[1] == PatAddr.Length`, always. BattlePatch can overwrite SB2_HEAD post-parse (DataPatchers.cs:192-193) but the array was sized at :25 before `ApplyBattlePatch` runs at BTL_SCENE.cs:156 — raw `bytes[1]` remains the authoritative bound of the array that gets indexed. Record sizes: 8 + 56·PatCount + 116·TypCount + 16·AtkCount (seeks at BTL_SCENE.cs:50/:126).
4. `btl_scene.PatNum = isDebug ? patternIndex : (Byte)ChoicePattern()` (HonoluluBattleMain.cs:206) — the diorama path takes the wire byte unvalidated (BattleUI.Start:26 re-stamps it a second time on the diorama scene, also unguarded; only its OnGUI is diorama-suppressed, BattleUI.cs:68-69). First out-of-range derefs: HonoluluBattleMain.cs:161/:230/:281-283, btl_init.cs:37/:45, btlseq.cs:475 — all inside the Start swallow → the half-initialized garbage scene.

### Is a pre-read at Boot time safe? YES
- **Synchronous, main thread.** `AssetManager.LoadBytes(String, Boolean suppressMissingError = false)` (AssetManager.cs:658-666) → `LoadBytesMultiple` (:541-628) is a plain iterator over File reads (`LoadFromDisc` :562/:575/:596/:617), `Resources.Load<TextAsset>` (:578/:620), and `assetBundle.LoadAsset` (:600) — all synchronous main-thread APIs. The battle boot calls this exact function on this exact thread (BTL_SCENE.cs:15 from Start). The watcher runs in `NetSyncClient.Update` (DioramaTick call at NetSyncClient.cs:694).
- **No scene-load conflict.** The pre-read precedes `SceneDirector.Replace("BattleMapDebug", …)` (NetSyncDiorama.cs:225); the watcher boots only free-standing on a field in `UIState.FieldHUD` (NetSyncClient.cs:802-809) and Boot refuses while `SceneDirector.IsFading` (NetSyncDiorama.cs:169-177).
- **Cheap — IF placed behind the rate limit** (see the placement law below). dbfile0000.raw16 ≈ 1-4 KB vs the megabytes of models the boot loads.
- **Reads the same bytes the boot will**, through the same `FolderHighToLow` mod-folder stack (AssetManager.cs:557-624) — a modded guest's own scene override is honored identically.

### The design — ONE shared durable-validation gate, both callers

Add to `NetSyncDiorama`:

```csharp
/// Pre-boot wire validation: everything DURABLY wrong with (mapNo, patNum) on THIS install.
/// Mirrors the boot's own resolution (HonoluluBattleMain.cs:198-201 -> BTL_SCENE.cs:15,21).
/// False => reason is set (BootBlockedReason principle: every decline says why).
/// COST: one small synchronous disk read -- callers MUST be rate-limited (never per-frame).
internal static Boolean ValidateWireBoot(Int32 battleMapIndex, Int32 patternIndex, out String reason)
{
    reason = null;
    try
    {
        Dictionary<Int32, String> names = FF9StateSystem.Battle.mapName;   // existing check, absorbed
        if (names == null || !names.ContainsKey(battleMapIndex))
        { reason = "battle scene " + battleMapIndex + " not on this install"; return false; }
        String bscName;
        if (!FF9BattleDB.SceneData.TryGetKey(battleMapIndex, out bscName) || bscName == null || bscName.Length <= 4)
        { reason = "battle scene " + battleMapIndex + " has no SceneData entry"; return false; }   // would NRE at HonoluluBattleMain.cs:199
        Byte[] bytes = AssetManager.LoadBytes("BattleMap/BattleScene/EVT_BATTLE_" + bscName.Substring(4) + "/dbfile0000.raw16", true);
        if (bytes == null || bytes.Length < 8)
        { reason = "battle scene " + battleMapIndex + " (" + bscName + ") has no readable scene binary"; return false; }   // ReadBattleScene would leave PatAddr null (BTL_SCENE.cs:16-17)
        Int32 patCount = bytes[1];                                          // SB2_HEAD.PatCount == PatAddr.Length (BTL_SCENE.cs:21,25)
        if (bytes.Length < 8 + 56 * patCount + 116 * bytes[2] + 16 * bytes[3])
        { reason = "battle scene " + battleMapIndex + " (" + bscName + ") scene binary is truncated"; return false; }   // would EndOfStream inside the Start swallow
        if (patternIndex < 0 || patternIndex >= patCount)
        { reason = "pattern " + patternIndex + " out of range (scene " + battleMapIndex + " has " + patCount + ")"; return false; }
        return true;
    }
    catch (Exception ex) { reason = "wire-boot validation failed: " + ex.GetType().Name; return false; }
}
```

**Caller 1 — `BootFromWire` (NetSyncDiorama.cs:137-153):** replace the inline mapName check (:141-148, whose `catch { return; }` is today a SILENT decline) with `if (!ValidateWireBoot(battleMapIndex, patternIndex, out why)) { Log.Warning("[NetSync] diorama wire boot REFUSED: " + why); return; }`. Keeps the F6 wire bench (the non-watcher caller) protected, and fixes the silent-decline violation en route.

**Caller 2 — the watcher (`DioramaTick`): PLACEMENT IS THE LAW.** DioramaTick runs EVERY FRAME (NetSyncClient.cs:694), and the existing mapName pre-check (:786-801) sits BEFORE the onField/FieldHUD/rate-limit gates (:802-812) — a passing validation there would re-run the disk read every frame while the guest is mid-battle/menu/transition (the exact spectate state). So: **leave the cheap dictionary pre-check at :786-801 unchanged** (per-frame safe; keeps the immediate one-line un-installable skip), and insert the full gate AFTER the rate-limit stamp (:812), immediately before `BootFromWire` (:813):
```csharp
_dioramaActionTick = Environment.TickCount;
String why;
if (!NetSyncDiorama.ValidateWireBoot(mapNo, patNum, out why))
{
    _dioramaSkipNonce = nonce;   // the un-installable-scene idiom: one line, once per battle
    Log.Message("[NetSync] peer battle undisplayable -- spectate panel only: " + why);
    return;
}
NetSyncDiorama.BootFromWire(mapNo, patNum, startType, rand);
```
The skip is per-battle and auto-forgotten when the lane goes stale (:743). **Do NOT skip-nonce on a generic `!Booted` after calling BootFromWire** — Boot also declines for TRANSIENT reasons (fade in flight NetSyncDiorama.cs:169-177, snapshot failure :183-195) that must retry at the 1/s cadence; only the durable gate may burn the nonce. `_dioramaActionTick` already honors the TICK-BASELINE LAW (`= Environment.TickCount - 10000`, NetSyncClient.cs:123).

Cost of the two-caller shape: worst case one read/second while waiting to boot; per successful boot the read runs twice (watcher + BootFromWire), ~2-8 KB — negligible, and it keeps one validation authority instead of two drifting copies.

### What this closes beyond the OOB PatNum
- The **SceneData-miss NRE** (HonoluluBattleMain.cs:198-199): `mapName` membership (BattleMapList.txt, BattleStateSystem.cs:25-38) does NOT imply `SceneData` membership (TwoWayDictionary, FF9BattleDB.SceneData.cs:6, extended by DictionaryPatch at DataPatchers.cs:539) — the current check guards the wrong dictionary for this failure.
- The **missing-binary NRE** (`PatAddr` null via BTL_SCENE.cs:16-17) and the **truncated-binary EndOfStream** (same garbage-scene class).
- Both PatNum stamp sites (HonoluluBattleMain.cs:206 AND BattleUI.Start:26).
- The **silent decline** in today's BootFromWire catch (NetSyncDiorama.cs:148).

The diorama-lane.md note (the deferral paragraph, ~:150-162) that "the scene-data hash in the version handshake is the real fix for the whole class" still stands for *content divergence* (same PatCount, different monsters); this guard closes only the *crash/garbage-render* class, which is exactly Q5's scope.

WIRE: none — validation is guest-local, wire stays v9.

RISKS: (1) A guest-side mod shipping a DIFFERENT dbfile0000.raw16 in a higher mod folder is validated against its own bytes — correct locally, but the host's pattern index may select a different monster set than the host sees; that is the content-divergence class the deferred scene-data hash owns. (2) The gate performs disk I/O: any FUTURE caller must sit behind a rate limit or a once-per-battle latch (this spec's two callers both do — BootFromWire is invoked only from rate-limited/once-per-boot sites, the watcher call is behind _dioramaActionTick + skip-nonce). Never place it in the per-frame pre-gate region of DioramaTick (:786-801) or any other per-frame path.

### Implementation checklist

1. Add NetSyncDiorama.ValidateWireBoot(mapNo, patNum, out reason): mapName check + SceneData.TryGetKey (+ null/length<=4) + sync AssetManager.LoadBytes("BattleMap/BattleScene/EVT_BATTLE_" + name + "/dbfile0000.raw16", true) + bytes[1] PatCount range check + full-length truncation check (8 + 56*Pat + 116*Typ + 16*Atk); every false path sets a reason (BootBlockedReason principle); whole body try/catch -> false with the exception type in the reason
2. BootFromWire: replace the inline mapName check (NetSyncDiorama.cs:141-148, incl. its silent catch{return;}) with the shared gate; refuse logs '[NetSync] diorama wire boot REFUSED: <reason>'
3. DioramaTick watcher: LEAVE the cheap mapName pre-check (NetSyncClient.cs:786-801) unchanged; insert ValidateWireBoot AFTER the rate-limit stamp (:812), immediately before BootFromWire (:813); on false set _dioramaSkipNonce = nonce + ONE Log.Message (the un-installable-scene idiom) + return
4. PLACEMENT LAW: the gate does disk I/O and DioramaTick runs every frame (NetSyncClient.cs:694) -- it must NEVER sit in the pre-gate region before onField/FieldHUD/rate-limit (:802-812) or any per-frame path
5. Do NOT skip-nonce on generic post-call !Booted -- transient declines (fade in flight NetSyncDiorama.cs:169-177, snapshot failure :183-195) must keep retrying at the 1/s cadence
6. Verify the pre-read never runs with a scene load in flight (it precedes Replace at NetSyncDiorama.cs:225; watcher requires onField + FieldHUD; Boot gates on !IsFading)
7. Selftest/bench: F6 wire-bench boot with patternIndex >= PatCount now refuses with the range log instead of the garbage scene; valid index still boots; a transient fade-decline still retries and boots on the next tick
8. Confirm no wire change: validation is guest-local, wire stays v9
9. No new tick baselines introduced; _dioramaActionTick already law-compliant (Environment.TickCount - 10000, NetSyncClient.cs:123)

<details><summary>What the verify pass corrected (the record)</summary>

ONE MATERIAL CORRECTION, several confirmations of load-bearing uncited claims:

(1) MATERIAL — Caller 2 placement installs the answer's own named risk. The checklist says "DioramaTick watcher: replace the mapName pre-check (NetSyncClient.cs:786-793) with the shared gate." That pre-check sits BEFORE the onField gate (NetSyncClient.cs:802-803), the FieldHUD gate (:804-809), and the 1/s rate limit (:810-812) — and DioramaTick runs EVERY FRAME from NetSyncClient.Update (call at NetSyncClient.cs:694). When validation PASSES it sets no skip-nonce, so a guest who is not free-standing (own battle / menu / transition — the exact both-in-battle spectate state B3 exists for) would re-run the disk pre-read every frame for the fight's whole duration: ~60 LoadBytes/sec, each walking the whole FolderHighToLow mod-folder stack (AssetManager.cs:557-624). The answer's RISK (2) names precisely this hazard ("if a future caller loops it un-rate-limited, it becomes per-frame I/O — keep it behind _dioramaActionTick") and then its checklist violates it. FIX: keep the existing cheap dictionary pre-check at :786-801 UNCHANGED (per-frame safe; preserves the immediate one-line un-installable skip), and call ValidateWireBoot AFTER the rate-limit stamp at :812, immediately before BootFromWire (:813) — on false: _dioramaSkipNonce = nonce + one Log.Message + return. Worst case is then 1 read/sec, in practice once per battle (a durable false burns the nonce; a successful boot flips Booted so the watcher exits at :764; transient Boot declines retry at 1/s, which is the current design).

(2) CONFIRMED (was the biggest uncited exposure): _dioramaActionTick already honors the TICK-BASELINE LAW — declared `= Environment.TickCount - 10000` with an explicit "tick-baseline law: NEVER a bare 0" comment, NetSyncClient.cs:123. No change needed.

(3) CONFIRMED byte-level core: BTL_SCENE.cs:15 (sync LoadBytes of BattleMap/BattleScene/EVT_BATTLE_<name>/dbfile0000.raw16), :16-17 (null → early return, PatAddr left null), :20-24 (header Ver/PatCount/TypCount/AtkCount/Flags = bytes 0-5), :25 (PatAddr sized from PatCount BEFORE DataPatchers.ApplyBattlePatch at :156, whose SB2_HEAD SetValue is DataPatchers.cs:192-193) — so raw bytes[1] IS the bound of the array actually indexed. Record sizes verified from the seeks: 56/pattern (BTL_SCENE.cs:50), 116/type (:126), 16/attack.

(4) CONFIRMED: AssetManager.LoadBytes(String, Boolean suppressMissingError = false) at AssetManager.cs:658-666 — the `true` overload the checklist uses EXISTS; body is a plain synchronous iterator (File reads via LoadFromDisc, Resources.Load<TextAsset>, assetBundle.LoadAsset — AssetManager.cs:541-628); resolves through the same FolderHighToLow stack the boot's own read uses.

(5) CONFIRMED: the throw path — HonoluluBattleMain.Start:132 / swallow :177-180, TryGetKey+Substring(4) :198-199, ReadBattleScene :201, `PatNum = isDebug ? patternIndex : (Byte)ChoicePattern()` :206, derefs :161/:230/:281-283, btl_init.cs:37/:45, btlseq.cs:475 (SetupBattleScene's PatAddr[PatNum].AP). BattleUI.Start:26 unconditional re-stamp + OnGUI-only diorama suppression :68-69 both verified.

(6) CONFIRMED: mapName ≠ SceneData — mapName built from BattleMapList.txt (BattleStateSystem.cs:25-38, Add at :36); SceneData is a TwoWayDictionary (FF9BattleDB.SceneData.cs:6) extended by DictionaryPatch at DataPatchers.cs:539. The current BootFromWire check (NetSyncDiorama.cs:141-148) really does guard the wrong dictionary for the :199 NRE, and its `catch { return; }` at :148 is a silent decline the shared gate also fixes.

(7) CONFIRMED watcher anatomy: DioramaTick :726-821, skip-nonce idiom :786-793 (+ :796-801 catch variant), stale-forget :743, rate limit :810-812, BootFromWire call :813, Booted early-return :764, transient-vs-durable decline distinction (fade NetSyncDiorama.cs:169-177, snapshot :183-195, Replace :225) — the answer's "do NOT skip-nonce on generic !Booted" law is correct and stands.

(8) MINOR ADDITION (same defect class, one comparison): a dbfile that parses a header but is TRUNCATED (bytes.Length < 8 + 56·Pat + 116·Typ + 16·Atk) throws EndOfStreamException inside ReadBattleScene inside the Start swallow — the identical garbage-scene outcome. Add the full-length check to the gate with reason "truncated scene binary". Cheap, closes the whole malformed-modded-binary class, not just OOB PatNum.

(9) Citation drift only (immaterial): the diorama-lane.md deferral+scene-data-hash paragraph lives at ~:150-162 (verified verbatim), answer cited the containing range :137-167.

</details>

---

## Lane 6 — [Netsync] SelfTestOffset = "dx,dz"

## [Netsync] SelfTestOffset = "dx,dz" (default "250,0" = exact current behavior)

**Current hardcode (ONE site, no duplicated constant — verified by grep over the whole Netsync tree):** `NetSyncClient.cs:569` `Vector3 stMirror = me.fieldMapActor.transform.localPosition + new Vector3(250f, 0f, 0f);`. Both consumers derive from that single local: the coop-cell broadcast `WriteCoopCells(1, stMirror)` at :570 and the ghost pose `DriveGhost(stMirror, ...)` at :577 — so changing the one Vector3 moves the ghost AND the [[coop]] peer X/Z cells together. `WriteCoopCells` itself is offset-blind (:375-394; clamp-round to Int16 LE at :383-388). The other 250s in the tree are unrelated (NetSyncClient.cs:1076 = field id; NetSyncBattle.cs:51 = 2500ms).

**Fields** — beside the other config mirrors (statics :55-69):
```csharp
private static Int32 _selfTestDx = 250;   // [Netsync] SelfTestOffset "dx,dz" -- walkmesh units
private static Int32 _selfTestDz = 0;     // (integer: matches the Int16 coop-cell rounding)
```
Int32, not Single: the coop cells round to Int16 anyway, and integer parsing is locale-proof with zero new usings (the Netsync tree has no `using System.Globalization`; the file's existing idiom is culture-free `Int32.TryParse`, :271-279).

**Parse** — in `LoadConfigIfChanged()` (:256), with the other key reads (:267-286):
```csharp
Int32 stDx = 250, stDz = 0;
String stOff = ini.GetSetting("Netsync", "SelfTestOffset", "250,0").Trim();
String[] stP = stOff.Split(',');
Int32 pdx, pdz;
if (stP.Length == 2 && Int32.TryParse(stP[0].Trim(), out pdx) && Int32.TryParse(stP[1].Trim(), out pdz))
{ stDx = pdx; stDz = pdz; }
else if (stOff != "250,0")
    Log.Message("[NetSync] SelfTestOffset '" + stOff + "' malformed (want \"dx,dz\" integers) -- keeping 250,0");   // BootBlockedReason principle: the decline logs why
```
The ',' separator is safe because components are integers (no decimal-comma ambiguity in any locale).

**Signature — MANDATORY:** the parsed pair joins the sig string at :310-312 (the parsed-value signature is THE "really changed" decider — the compare at :315-316 returns false-unchanged, so an un-sigged key edit is invisible to hot-reload forever):
```csharp
... + "|" + (insecure ? "1" : "0") + "|" + stDx + "," + stDz;
```
Commit inside the assignment block :317-320, BEFORE `_cfgSig = sig;` at :320: `_selfTestDx = stDx; _selfTestDz = stDz;`. Surface in the config log line (:328-334) when non-default: `(_selfTestDx != 250 || _selfTestDz != 0 ? " selfTestOffset=" + _selfTestDx + "," + _selfTestDz : "")`.

**Apply** — replace :569 with:
```csharp
Vector3 stMirror = me.fieldMapActor.transform.localPosition + new Vector3(_selfTestDx, 0f, _selfTestDz);
```
Nothing else changes — :570 (coop cells) and :577 (ghost) already flow from `stMirror`. dz lands on Vector3.z = the walkmesh Z the kit reads at COOP_PEER_Z (gEventGlobal 2036, coop.py:72).

**Hot-reload (already free once sigged):** Ensure() (:148-163) re-reads on every field load (:150); Update's 2s poll (:461-465) calls LoadConfigIfChanged → ApplyConfigChange (:343-367), which despawns the ghost (:353) and zeroes the coop cells (:356); the next selftest tick rebuilds both at the new offset (:570 writes every frame). No stale mirror.

**Docs** — update the engine class comment :37-38 ("plates 250 units apart" → name the knob + default) AND the kit's THREE prose sites: coop.py:27 (gather width "> 250 x in selftest"), :56-57 (solo-provable paragraph), :182 (inject_gather docstring).

**Kit coupling (corrected):** `SELFTEST_MIRROR_DX = 250` (coop.py:74) has ZERO code consumers — it is a documented CONVENTION (docstring :57; tests/test_coop_gate.py:102 hand-places plate centers 250 apart with a comment; the twin-vault/twin-altar content hard-places plates). So no kit code breaks under a non-default offset, but shipped selftest content silently stops being solo-provable. Minimum viable: keep the constant at 250 and document that a non-default SelfTestOffset requires matching hand-placed plates. Better (follow-up): teach `coop host|join`/the Co-op tab's Play-style panel to write SelfTestOffset, and give the kit's selftest-provability docs/lint a (dx,dz) parameter defaulting to (250,0). East-door bias fix: `SelfTestOffset = "-250,0"` (or "0,250" for the N/S axis) + plates placed to match.

**Wire impact: NONE — confirmed.** Selftest never builds a socket (:169 comment; the :533 role branch returns at :582 before transport creation at :587-602). `stMirror` feeds only the local ghost transform and local gEventGlobal pokes (:375-394). Wire stays v9, zero bytes added.

### Implementation checklist

1. Add static Int32 _selfTestDx = 250 / _selfTestDz = 0 beside the other config mirrors (NetSyncClient.cs:55-69) -- Int32 not Single (locale-proof, matches Int16 coop-cell rounding, no new usings)
2. Parse [Netsync] SelfTestOffset = "dx,dz" in LoadConfigIfChanged (:267-286 block) with per-component Int32.TryParse; malformed -> keep 250,0 AND log why (BootBlockedReason principle)
3. Append "|" + stDx + "," + stDz to the sig string at :310-312 -- without this the :315-316 compare returns false-unchanged and hot-reload NEVER notices an offset-only edit
4. Commit _selfTestDx/_selfTestDz inside the assignment block :317-320 BEFORE _cfgSig = sig at :320; surface non-default in the config log line :328-334
5. Replace the literal at :569 with new Vector3(_selfTestDx, 0f, _selfTestDz); verify :570 and :577 still consume the same stMirror (grep confirms no other 250 in the selftest path)
6. Update the engine class comment :37-38 AND the kit prose trio coop.py:27 / :56-57 / :182 to name the knob + default instead of the bare 250
7. Hot-reload verify in-game: selftest running, edit SelfTestOffset in Memoria.ini, confirm within ~2s the ghost despawns (ApplyConfigChange :353) + cells zero (:356) + both reappear at the new offset next tick
8. Kit follow-up (separate, no engine work): SELFTEST_MIRROR_DX is convention-only (zero code consumers) -- document the lockstep requirement now; optionally teach coop CLI/Co-op tab to write SelfTestOffset later
9. Regression: default "250,0" must be byte-identical behavior -- twin-vault 3-beat selftest on 4003 still passes (incl. the sealed-door negative)
10. Confirm wire v9 untouched: selftest builds no socket (:169, :533->:582 before :587) -- no frame carries the offset

<details><summary>What the verify pass corrected (the record)</summary>

1) KIT COUPLING MECHANISM OVERSTATED. The answer implies the kit's gate tooling computes/translates plates from SELFTEST_MIRROR_DX ("the [[coop]] gate/test tooling that translates plates by the mirror offset must read a matching value"). FALSE: grep proves `SELFTEST_MIRROR_DX` (coop.py:74) has ZERO code consumers — its only reference is the module docstring at coop.py:57 (":data:`SELFTEST_MIRROR_DX` apart center-to-center"); coop.py:27 and coop.py:182 are literal "250" PROSE, not uses of the constant; plate placement is entirely author-side (inject_gate at coop.py:160-173 takes plate rects verbatim; tests/test_coop_gate.py:102 hand-places "centers 250 apart -> selftest-provable" as a comment convention; the twin-vault/twin-altar content hard-places plates). So a non-default SelfTestOffset breaks NO kit code — it silently invalidates the documented convention + shipped selftest content's solo-provability. The "both must move together" pair from the question is the ENGINE's position + coop-cell broadcast, and that IS single-sourced: NetSyncClient.cs:569 (`Vector3 stMirror = ... + new Vector3(250f, 0f, 0f)`) feeds both :570 (`WriteCoopCells(1, stMirror)`) and :577 (`DriveGhost(stMirror, ...)`); WriteCoopCells is offset-blind (:375-394, Int16 LE clamp-rounds at :383-388). No duplicated 250 anywhere in the Netsync tree (grep: :38 comment, :569 code, :1076 = field id 250 unrelated, NetSyncBattle.cs:51 = 2500ms unrelated).
2) PARSE SNIPPET UNSHIPPABLE AS WRITTEN. The `Single.TryParse(..., NumberStyles.Float, CultureInfo.InvariantCulture, ...)` snippet needs `using System.Globalization` — grep confirms NO file in C:/gd/FFIX/Memoria/Assembly-CSharp/Memoria/Netsync imports it, and NetSyncClient.cs's usings are System/Assets.Scripts.Common/Memoria.Prime/Memoria.Scripts/UnityEngine (:1-5). The existing key parses are culture-free `Int32.TryParse` (:271-279). Ship the answer's own fallback as the PRIMARY: Int32.TryParse per component (integer digits parse identically in every locale, killing the comma-decimal hazard without any new using; matches Int16 coop-cell granularity at :383-384).
3) CITE PRECISION. Update-tick hot-reload: the 2s poll gate is :461 (`Environment.TickCount - _lastPoll > 2000` — itself tick-baseline-lawful, _lastPoll init at :103), LoadConfigIfChanged at :464, ApplyConfigChange at :465. Assignment block is :317-320 and INCLUDES `_cfgSig = sig` at :320 — the new field commits must land before :320 inside that block. Sig compare `if (sig == _cfgSig) return false;` is :315-316. ApplyConfigChange spans :343-367 (DespawnGhost :353, WriteCoopCells(0, Vector3.zero) :356). Ensure :148-163 (LoadConfigIfChanged :150, ApplyConfigChange :161). Selftest role gate :533, branch returns :582 (earlier outs :544/:548), transport creation :587-602. All confirmed.
4) DOC-UPDATE SCOPE WIDENED. Not just the engine class comment (:37-38) and coop.py:74 — the literal 250 lives in THREE coop.py prose sites (:27 gather-width, :56-57 solo-provable, :182 inject_gather satisfiability) that must all name the knob/default.
CONFIRMED AS-IS: single hardcode site :569; both consumers derive from the one stMirror local; sig string :310-312 is the "really changed" decider (an un-sigged key edit returns false at :315-316 → Ensure/Update never call ApplyConfigChange → hot-reload blind — the answer's central mandate is right); default "250,0" via GetSetting default = byte-identical current behavior; wire impact NONE (:169 "selftest has no socket, so it never mirrors"; :533→:582 return precedes :587 transport; the offset touches only the local ghost transform + local gEventGlobal pokes; v9 untouched); hot-reload effect path (despawn + cell zero, next Update tick rebuilds at the new offset since :570 writes every frame); dz maps to Vector3.z = the walkmesh Z axis coop.py reads at COOP_PEER_Z 2036.

</details>
