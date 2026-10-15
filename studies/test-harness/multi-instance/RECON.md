# Two FF9 clients on one machine -- the recon (2026-10-15)

Goal: run a co-op HOST and a GUEST at once on the desktop, both driven by the harness, so two-role co-op changes can be benched
without the laptop. Source: a 5-lane read-only workflow (process/Steam, path resolution, harness, netsync topology, prior art),
each lane adversarially verified, then synthesized. **Everything below is static reading + offline probes with fake games: nobody
has ever started two FF9 processes. Probes P0-P4 decide it.**

## Verdict

FEASIBLE with NO engine/DLL patch. Nothing in FF9, Unity 5.2.3, Memoria or Steam forbids a second process. The two real limits are
path collisions, and both dissolve in an **instance root** outside the Steam folder (junctions + a few copies).

## The owner's three doubts

1. **Does FF9 run multiple instances?** Yes (static). PlayerSettings (UnityPy, `x64\FF9_Data\mainData`): `forceSingleInstance=False`,
   `runInBackground=True`. The only native gate is the opt-in `-single-instance` flag the harness passes (session.py:206-207); its
   mutex is keyed on the last 30 chars of the exe's own canonical path (disassembly: GetModuleFileNameW + PathCanonicalizeW, then
   non-alphanumerics -> '-'), so it only blocks the SAME exe path twice. No Mutex/GetProcessesByName guard anywhere in the clone.
   Unfocused instances keep simulating; harness input and screenshots need no focus (22/209 archived runs booted unfocused, green).
2. **Can each have its own Memoria.ini?** Yes, no code change. Memoria.ini, Settings.ini, Memoria.log, StreamingAssets, the root
   `FF9_Data\EmbeddedAsset` and the mod folders all resolve against the process WORKING DIRECTORY (IniFile.cs:9-10). The root
   Memoria.ini is the one read; `x64\Memoria.ini` is a stale embedded default from an old cwd=x64 launch. Each instance's ini must
   be a real COPY (Netsync rewrites it in place -- SessionCode write-back -- and hot-reloads by mtime).
3. **Separate install directory -- needed, possible?** Needed, and cheap. (a) Same cwd = dead on arrival: Memoria.Prime opens
   `./Memoria.log` deny-write and calls `Environment.Exit(1)` on failure (Log.cs:14-27). (b) Same exe dir = shared harness channel,
   save sandbox, ff9mk_dumps and output_log.txt (HarnessAgent.cs:446-454: `dataPath/../ff9harness`). No 45 GB copy: junctions and
   hardlinks work UNELEVATED (symlinks need admin); C: is NTFS with ~217 GB free.

## The instance root (design A; design B, an engine path-redirect switch, was rejected: ~15 sites in 2 assemblies, a DLL rebuild,
and it still cannot split output_log.txt, PlayerPrefs or the DLL)

`C:\gd\ff9-inst\<host|guest>\` -- a REAL directory on C:, outside the Steam folder, never itself a junction:
- `Memoria.ini` COPY + overlay ([Netsync] per topology; [Control] AlwaysCaptureGamepad=0; [SfxProbe] Enabled=0);
  `Settings.ini` COPY + `WindowPosition` left/right and a smaller resolution.
- Junctions: `StreamingAssets`, the root `FF9_Data`, and one per `[Mod] FolderNames` entry, named EXACTLY as in the ini
  (ScriptsLoader derives the DLL name from the folder name). Never link `FontList` (the game writes it every boot).
- `x64\` REAL: copies of FF9.exe, steam_api64.dll, XAudio2_9.dll, msvcp120/msvcr100/msvcr120 (~22 MB).
- `x64\FF9_Data\` REAL: junctions for Managed/Mono/Plugins/Resources (an engine rebuild reaches every instance; a frozen Managed
  copy instead = mixed-DLL pairing), the 59 data files hardlinked or copied; never link output_log.txt.
- The harness writes `x64\ff9harness\arm` before every launch -- an UNARMED instance calls SteamAPI_RestartAppIfNecessary(377840),
  quits, and Steam starts the REAL install's launcher (BundleSceneSelector.cs:31). Instances are harness-only.
- **TEARDOWN LAW:** `os.rmdir` each junction first, then delete real files. NEVER `Remove-Item -Recurse` / `rmdir /s` on a root:
  they follow junctions into the real install.

## Topology (T-bridge-local, the sittings' path minus the internet)

`coop_peer.py relay --port 7787 --tap <run>\tape.jsonl`; one bridge PROCESS per player (`--port 49211` / `49212`,
`--relay ws://127.0.0.1:7787`). Host root: `Enabled=1, Role=host, RelayUrl=ws://127.0.0.1:49211, SessionCode=ff9-DUO<fresh>,
FollowHost=0, GuestSlots=2`. Guest root: `Role=client` (NOT `guest`: that silently runs selftest, NetSyncClient.cs:1305),
`RelayUrl=ws://127.0.0.1:49212`, the same code, `FollowHost=1`. Never 49201 (SO_REUSEADDR co-binds beside the owner's bridge);
never the owner's live code (it would evict the laptop's leg on the public relay). Netsync has no machine identity (per-process
Guids; the relay pairs by code+role); all four topologies paired with fake games offline. Cut lever: `NtSuspendProcess` on one
bridge (verified: 0 frames for 6 s, then a backlog burst), under the 75 s ReceiveTimeout. Variants: T-relay-direct (simplest),
T-bridge-public (real relay RTT), T-direct (unexercised since wire v1; a listening copied exe raises a firewall prompt).

## Harness changes

Prototype (~150-250 LOC scratch, ZERO session.py edits): per root `Session(label=, game_path=root, pid_probe=<path-scoped via
hangdump.process_image_path / QueryFullProcessImageNameW>, launcher=<Popen without -single-instance, cwd=root>)`; distinct labels
(run dirs are `<stamp>-<label>`); different seeded saves per sandbox (the two-marker law).
Production (~900 LOC with tests): `tools/harness/instance.py` (ensure/refresh/verify/teardown, ini overlay via coop.py's
write_netsync, re-verify links + hardlinks every launch, a claim lock); `Session(exclusive=False)` / `play.py --instance`; a per-session
nonce in the arm body; `tools/harness/duo.py` (two Sessions, relay + bridges, both logs archived, cross-instance parity asserts);
`game_snap.ps1 -Id`; an explicit pid for hangdump; path-scoped soaks (bench_soak, se_soak, choice_soak, gamewin, ambient_splice).
Policy question for the owner: should a default exclusive run on the real install keep refusing while an instance runs?

## What it unlocks / what it cannot replace

Unlocks a second LIVE engine where T2 has a tape: real guest commands answered by a real host (stock menu, group-2 action replay),
s118/s114 with real reports, diorama + state mirror against a live host battle, both ends of the dialogue lock and talk relay, the
real bridge + relay with kill/redial, fresh two-direction tapes after every wire bump, cross-instance parity asserts, sustained
one-leg cuts, mixed-DLL pairing via a frozen Managed copy, and an end to role-flipping the owner's live Memoria.ini.
Cannot replace: real Wi-Fi (loopback has ~0 ms and no loss), cross-machine clocks (one TickCount), separate hardware (shared
GPU/CPU changes timing; hang statistics not comparable), the laptop package's install path, feel. A two-machine sitting stays the
release gate.

## Staged probe plan (each needs the owner's go)

- **P0** second process from the SAME root (negative control, no new files): does a second Unity 5.2.3 player start beside a live
  one, and how does a same-cwd instance die (exit 1 vs hang)? Variant P0b with `-single-instance` (expect the mutex). Risk low;
  may truncate that throwaway run's output_log.txt.
- **P1** build one root, no launch; build -> teardown -> rebuild leaves the real targets untouched.
- **P2** boot that root alone: dataPath follows the copied exe (channel + sandbox under the root), Steam skipped, logs in the root,
  the real install's files untouched; ini hot-reload.
- **P3** two roots at once, Netsync off: both channels tick; tick rate focused/unfocused/minimized; screenshots; memory; audio.
- **P4** loopback pairing: relay-direct, then bridge-local; ghost both ways, mirror ARMED, diorama BOOT/LIVE, s118 hand-back.
- **P5** cut fidelity A/B (bridge suspend 6 s vs sitting A). **P6** deploys and rebuilds while an instance runs. **P7** replay
  1-2 sitting-A boxes and compare.

## Probe results (2026-10-15)

- **P0 -- 6/7, the one red IS the finding.** The live instance A was unaffected by both launches (kept ticking; Memoria.log and
  output_log.txt never shrank). B (same root, no `-single-instance`) did NOT exit: its Unity log stops right after loading
  Memoria.Prime.dll and it sat alive until killed at 20 s -- the Memoria.log clash HANGS a same-cwd second instance rather than
  Exit(1)-ing it, so tooling must kill such a process. B2 (WITH the flag) hit A's path-keyed mutex: exit 0 in 0.43 s, no log.
  Probe: `p0_second_process.py`.
- **P1 -- pass.** `instance_root.py build C:\gd\ff9-inst\guest`: 13 junctions (StreamingAssets, root FF9_Data, the 7 FolderNames,
  x64\FF9_Data\{Managed,Mono,Plugins,Resources}) + 66 copies (x64 exe/DLLs, 59 data files, Settings.ini) + the overlaid
  Memoria.ini (exactly 3 lines differ: Netsync Enabled 0, AlwaysCaptureGamepad 0, SfxProbe Enabled 0); ~800 MB, 3 s. Teardown by
  the law, then the install fingerprint (file count, bytes, newest mtime of every junction target + the ini sha) was IDENTICAL;
  rebuild verified.
- **P2 -- pass.** `py tools/play.py --smoke --field 30602 --game C:\gd\ff9-inst\guest` with the STOCK harness (no code change):
  agent up in 6 s; 'ARMED -- channel at C:\gd\ff9-inst\guest\x64\ff9harness' and 'saves sandboxed to C:\gd\ff9-inst\guest\...'
  (Application.dataPath follows the copied exe); '[SteamSdkWrapper] Initialized: False' (no Steam relaunch); all 7 mods loaded
  through the junctions; the warp to 30602 and a walk worked; Memoria.log, FontList and output_log.txt landed in the root; the
  NetSync config line read the root's own ini (enabled=False). The real install's Memoria.log, output_log.txt, ff9harness, ini and
  FontList were untouched and its fingerprint identical. The smoke's one red ('NON-BLANK frame') is the check, not the instance:
  30602 has no background art, so the top ~52 rows are black and the 200 KB byte-sample reads blank (the frame shows Zidane, Vivi
  and props). Not done: the ini hot-reload touch.
- The guest root is LEFT BUILT at C:\gd\ff9-inst\guest for P3. Remove it only with `py instance_root.py teardown <root>`.
- **P3 -- STOPPED at its first surprise** (`p3_two_instances.py`; host root C:\gd\ff9-inst\host built + verified like the guest).
  PROVEN: two FF9 instances run at once under the STOCK Session (only the pid probe path-scoped; `-single-instance` kept, its
  mutex differs per exe path): host up in 6 s, guest in 4 s beside it, separate channels and sandboxes, the smoke's New Game +
  warp 30602 + walk in each; both ticked ~60 fps side by side; a MINIMIZED instance kept ticking at ~33 fps (the other stayed
  60). SetForegroundWindow from the driver is refused (Windows foreground lock), but ShowWindow(SW_RESTORE) after a minimize
  brings that window to the front. Both logs: '[SaXAudio] Initialized'; no gamepad ('[ControllerWatcher] Couldn't connect
  device'). THE SURPRISE: the HOST sat on the game's PAUSE screen from the first measurement on -- it entered Pause between
  01:53:21 and 01:53:45, i.e. while the GUEST launched and booted, unattended -- so its warp to 250 was refused ('not on a field')
  and the run ended before the field-250 screenshots and the memory reading. The foreground app during the legs was Discord.exe.
  No managed code path enters Pause on focus loss (SceneDirector.hasFocus is never read; every ChangeUIState(Pause) is the Pause
  CONTROL: Backspace via GetAsyncKeyState while that window is foreground, or a pad Start); the harness sends nothing across
  instances. Same symptom as the unexplained mid-intro Pause in the 22:30 single-instance start-hold run. Cause UNKNOWN.
- **P3 RE-RUN -- PASS** (the owner had been PLAYING ANOTHER GAME with a controller connected; closed it and unplugged the pad;
  the driver gained a 50 ms watcher of the foreground process + both ui_states read off each channel's state.json). Both up in
  4.3 / 3.9 s; both ~60 fps side by side in every leg; a minimized instance ~33 fps, the other unaffected; NO Pause anywhere
  though the foreground moved through Chrome, Explorer, Discord, Claude and both game windows -- focus loss alone does NOT pause
  FF9 (consistent with the code). The first run's Pause was most likely that controller's input reaching a foreground FF9 window
  (the 22:30 start-hold Pause ran on the live ini's AlwaysCaptureGamepad = 1, where a pad press reaches FF9 even unfocused).
  Field 250 photographed with full art in BOTH (785 KB each); working set ~745 MB per instance at boot, ~800 MB at the end; both
  '[SaXAudio] Initialized'; both quit cleanly (no process left); Unity logs identical in kind to a single-instance run (the same
  9 'AssetBundle ... already loaded' lines every run has). LAW for unattended runs: no controller connected, or every instance's
  ini at AlwaysCaptureGamepad = 0 AND no human input while a game window is foreground.
- **P4 -- PAIRING, BOTH TOPOLOGIES ALL GREEN** (`p4_pairing.py --leg relay|bridge`; a local `coop_peer relay` on 7787 with
  --tap; for `bridge` one netsync_bridge PROCESS per player on 49211/49212; a fresh ff9-DUO code per run; each root's own ini set
  through IniGuard and restored). Each leg, two REAL games: both config lines (role host / client, the leg's URL, the code); both
  'relay connected ...?role=host|guest'; the guest 'paired on the host's field (250)'; a ghost on 250 in BOTH games in the same
  second (the host sees the guest as Vivi -- ghostAs auto -- the guest sees the host as Zidane); 'state-mirror ARMED'; the
  guest's story byte 1121 reads the HOST's 0xA5; the host's own battle published ('battle intro: PLAYED ... random 1'); the
  guest 'diorama BOOT scene=67' the same second and 'diorama LIVE ~8.05 s after the boot (host battle nonce 1, booted from wire
  nonce 1)'. And the FIRST s114 start hold judged by a REAL guest's report: 'ARMED ... the guest's diorama is BOOTING' ->
  'RELEASED after ~1.2 s: live'. Both games ended in BattleHUD; inis restored, roots re-verified, relay + bridges stopped
  cleanly (bridge-host: 1671 game frames / 752 relay frames), the owner's ini untouched. Two driver fixes on the way, both
  instrument, not system: relay mode's banner is 'relay listening on ...' (not 'listening on'); a root booted with Netsync
  Enabled=0 has no NetSyncClient polling its ini, so the role config lands only at a field load (`coop_tape_record._wait_config`'s
  recipe: a short wait, then one same-field warp).
- **P5 -- STOPPED at its first surprise** (`p4_pairing.py --leg bridge --cut-for 6`: P4's pairing, the host battle, then
  NtSuspendProcess on the HOST's bridge for 6.00 s, 10 s after the guest's LIVE). Every P4 check green again. Against sitting A
  (laptop-Memoria.log 155-166, s117: 'diorama LEAVE requested', 'watcher-leave settled (nonce 3)', the warm return, then
  'session ended -> reloading own autosave' 3 s later), the s121 guest did the OPPOSITE, as designed: K1 none of those lines; K2
  one CUT-variant hold ('peer silent mid-battle -- holding ... a cut; up to 30s'); K3 one session outage ('the hop is up: a cut or
  a stall upstream'); the resume 'back on the same fight (nonce 1) ... resuming', 'the host is back after 4000 ms -- inside the
  30 s grace ... still mirroring', and 'the ready mirror is SERVING' again. THE SURPRISE (K4, the hold's length): 2125 ms, not
  the ~4000 the T2 s119 leg measured (4047). The hold line came ~2 s AFTER the outage line (04:31:48 -> :50), and the guest's
  stock menu closed for 'no live peer battle lane' TWICE (:47 and :50) -- as if the battle lane read live again briefly inside
  the cut and restarted the hold clock. The T2 legs disagree with each other the same way: s119 hold 4047 vs outage 4031 (same
  second); s120-battle hold 16094 vs outage 18015 (the hold line 2 s after the outage). So the hold's ONSET varies by ~2 s run to
  run, live or replayed. Not a sitting-A regression (no leave, no ramp, same-nonce resume); cause UNKNOWN. K5 was not reached
  by the driver, though its line is in the window above.
- **Where this leaves the goal:** two real co-op clients on this desktop, harness-driven, over the sittings' own bridge + relay
  path, with no DLL change and the real install untouched. Next: P5 (a bridge-suspend cut vs sitting A), then productionize
  (instance.py, a Session multi-instance mode, duo.py, tests -- see "Harness changes").

## Risks (beyond the teardown law)

Unarmed instance -> Steam relaunch of the real install; deploys or FF9_GAME_PATH must never point at a root (writes go through the
junctions); drift (copied ini goes stale, new FolderNames need new junctions, a Steam verify breaks hardlinks); never rebuild the
engine while the duo runs; other worktrees' default harness refuses while any instance runs; state no directory split separates:
PlayerPrefs (HKCU, incl. ff9mk_debug_*), the LocalLow and MyDocuments save paths before arm, the gamepad, the audio device, the
window title; an unfocused boot skips Memoria's window placement + WndProc hook.

## Effort

P0 ~30 min; prototype ~half a session; P1-P5 one mostly-unattended sitting; productionizing 1-2 sessions. Total ~2-3 sessions +
one calibration sitting. No DLL rebuild.
