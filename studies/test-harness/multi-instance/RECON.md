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

## Risks (beyond the teardown law)

Unarmed instance -> Steam relaunch of the real install; deploys or FF9_GAME_PATH must never point at a root (writes go through the
junctions); drift (copied ini goes stale, new FolderNames need new junctions, a Steam verify breaks hardlinks); never rebuild the
engine while the duo runs; other worktrees' default harness refuses while any instance runs; state no directory split separates:
PlayerPrefs (HKCU, incl. ff9mk_debug_*), the LocalLow and MyDocuments save paths before arm, the gamepad, the audio device, the
window title; an unfocused boot skips Memoria's window placement + WndProc hook.

## Effort

P0 ~30 min; prototype ~half a session; P1-P5 one mostly-unattended sitting; productionizing 1-2 sessions. Total ~2-3 sessions +
one calibration sitting. No DLL rebuild.
