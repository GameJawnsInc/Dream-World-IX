## 1. The harness API

- **The channel** is `<game>/x64/ff9harness/`. It holds `arm`, `req.txt` (requests in), `state.json`, `events.jsonl` and `shots/` (HarnessAgent.cs:17-20). A scenario is a file with `run(g)`, run by `py tools/play.py`. `g` is `Session`. Its `run_dir` defaults to `REPO/.harness-runs/<stamp>-<label>` and can be overridden with `Session(run_dir=)` (session.py:49-50, 219, 293).
- **State:** `g.state` (session.py:883) reads `state.json`. The agent publishes every 2nd frame by default (`_stateEvery=2`, HarnessAgent.cs:180); `g.state_every(n)` changes it (session.py:2850 → agent :767-768). `scenario` (ScenarioCounter) is published every time (:1107). Flags are published only for watched bits: `g.watch(*bits)` (session.py:2783 → agent :728-746, AppendWatch :1699).
- **Events:** today `events.jsonl` rows are only armed / accepted / error / ack / reset / note / quit / shot (HarnessAgent.cs:325, 470, 493, 506, 792-802, 1048). `Channel.events()` re-parses the whole file on every call (channel.py:871-884).
- **Exceptions:** take `m = g.log_mark()`, then `g.exceptions_since(m)` covers both Memoria.log and output_log (session.py:756-800).
- **Poking Global bytes:** `g.flag(bit, v)` and `g.poke(idx, val)` write raw `gEventGlobal` (session.py:2775-2781 → agent :706-726).
- **Warp:** `g.warp(id, entrance=, scenario=)` (session.py:1546) calls `Ff9mkDebugMenu.HarnessWarp` (HarnessAgent.cs:564-568; Ff9mkDebugMenu.cs:469). That is the ~ menu's own fade path. `ServicePendingWarp` sets FieldEntrance (:2130) and ScenarioCounter (:2135) before `SetNextMap` (:2143).
  - The engine refuses the warp unless the UI is on the field HUD (:2083).
  - The driver accepts stock ids through `stock_field_ids()` (`_check_field_id`).
  - `warp()` waits until the field is playable. A field that opens on a cutscene needs a raw `g.send("warp N -1 -1")` instead (cutscene_check.py:31-35).
- **Buttons:** `press` / `hold` / `release` / `walk` (session.py:1069-1083), plus closed-loop verbs (`walk_to`, `interact`, `advance`, `choose`). `timescale` accepts 0.1-8 (agent :752-764).
- **Saves:** while armed, the engine points `SharedDataBytesStorage.MetaData.DirPath/FilePath` at `ff9harness/save/` (HarnessAgent.cs:364-390) and publishes `save_path` / `save_sandboxed`. The driver copies the real saves to `<run>/saves-before/` and refuses to start if the redirect is not confirmed (session.py:419-460). It flags any change to the real saves at teardown (:538-542).
- **"Arming is a TRANSITION":** `PollArm` checks every 30 frames and returns early when `File.Exists(arm) == Active` (HarnessAgent.cs:287-297). Only a false→true change resets `_seq`, `_ack`, `_watch`, `_stateEvery` and the buttons (:305-323).
  - So if an old arm file is left behind, new requests are dropped as stale while the dead run's ack satisfies every wait. Every step reports success having done nothing.
  - The driver's fixes: `Channel.arm()` deletes the file, waits out the poll, then recreates it (channel.py:687); `_await_ack` requires both `seq` and `ack` ≥ its own number (session.py:612-616); `seed_seq` (channel.py:762).
  - For the trace: resetting the shadow must hang off this same arm edge.

## 2. Same beat, two fields

- **Stock fields already run under the harness, but only without a story seed.** `borrow_2507_ingame.py:173` loops `(NO_ROW, WITH_ROW, REAL)` through one `_probe`, so the forks and real 2507 run in one launch. `root_fix_2507.py:117` and `editable_2507_detach.py:80` do the same. **I found no scenario that runs donor and fork at the same story beat.**
- **Proposed recipe:**
  1. `newgame()`.
  2. Apply the seed with `g.flag` / `g.poke`.
  3. `g.warp(stock, scenario=SC, entrance=E)` and trace.
  4. Soft reset, `newgame()`, apply the same seed.
  5. `g.warp(fork, scenario=SC, entrance=E)` and trace.

  The seed rows can come from `storyseed.resolve(eb, beat, census).set_bits` (storyseed.py:107-114, 162) plus `ate_word_values` (:448). Those are the same rows a hub pick stamps before its warp.
- **Caveats:**
  - New Game *replaces* the array (`gEventGlobal = new Byte[2048]`, EventEngine.Initialize.cs:43), so the shadow must notice when the array itself changes.
  - `ApplyStoryBeforeEvents` (HonoluluFieldMain.cs:148 → NetSyncClient.cs:386) only mirrors a co-op guest to the host. It is not a seeding lane; it only matters as an epoch point.
  - The fork needs its ForkDonorPatch row so `EffectiveFieldId` (DataPatchers.cs:47) keys its rows to the donor id.
  - A member that bakes its own `[startup]` overwrites the warp's SC on entry (comment at Ff9mkDebugMenu.cs:2131-2134).
  - The "stock" run may not be stock: stacked mod folders can override a real field (the field-70 New Game override is one), and New Game may land on a campaign's field. `env.json` records which folder registers what.
- **Calibration:** Lindblum 552 at SC 3115 with byte 236 = 0x0F. The owner confirmed it on slot 30823 (narrative-state/PLAYTEST.md:85-92). Its current registration is unverified.

## 3. Determinism

- **Randomness:** `B_SYSVAR[0]` is `Comn.random8` = `UnityEngine.Random.Range` (GetSysvar.cs:13-14; Comn.cs:8-11). That one unseeded stream also feeds idle-animation speed (ProcessAnime.cs:214), the encounter roll (ProcessEvents.cs:497; the timer is distance-driven, :288), and `EventEngine.cs:211` / `:283`. The only place anything seeds it is BattleRainRenderer.cs:47. The harness has no seed verb.
- **Frame pacing:** the number of logic ticks per render frame comes from `Time.deltaTime` (FPSManager.cs:94-99; HonoBehaviorSystem.cs:106). The agent schedules input by `Time.frameCount` (HarnessAgent.cs:32-36). So a hold of N frames is not a fixed number of ticks, and `frame` values will not line up between runs.
- **Existing tooling:** the roll stream only seeds kit-authored content, not stock scripts. `timescale` changes speed, not determinism. The closed-loop verbs absorb position noise, not timing.
- **Set diff vs ordered diff:** an ordered per-write diff breaks on writes from objects ticking in the same frame, tick drift, and random branches. A set diff keyed on (EffectiveFieldId, function, byte/bit, value) survives the first two but not the third. So it needs N runs per side: keep rows present in all stock runs and absent from all fork runs.
- **Gap in the board's design:** a per-frame memcmp cannot name the writing function. It sees (frame, byte, old→new) and merges writes within one frame, so a set-then-clear in one tick is invisible. Attribution needs a hook at the script's Global write point, EBin.cs:1902-1903, where `gExec` / `gCur` are known (EBin.cs:159, 181). Writes made from C# bypass that hook (the ScenarioCounter setter, EventState.cs:18-22; the debug warp :2135; harness pokes), so keep the memcmp to catch those.

## 4. Sinks and size

- **Today:** `events.jsonl` is 22-39 KB per run; the largest is 38,711 B (`20260923-124439-bgi-rung1-r3`). A state-ring flush is about 1.4 MB (300 states, artifacts.py:34-38). The main repo's `.harness-runs` is 290 MB across 51 runs.
- **No rotation or cap:** `Event()` calls `File.AppendAllText` once per row (HarnessAgent.cs:1794-1822). On an IOException it buffers rows in `_pendingEvents` with no limit. An epoch flood of about 2048 rows would mean 2048 file opens in one frame, so batch rows per frame or use a separate trace file.
- **Lifetime:** the live file on the shared install is deleted by the next run's `Channel.reset()` (channel.py:643-649). It is copied into `run_dir` only at teardown (channel.py:885-892; session.py:531). `run_dir` sits under the worktree it was run from (session.py:49-50), so it disappears with that worktree, and it is gitignored (.gitignore:295).
- **Archive rule:** copy captures to `C:\gd\SCRATCH\<study>\logs\<name>.<stamp>` immediately and analyse the copy. It is better if the tool does the copy itself (feedback-archive-capture-logs-immediately.md:23-27).

## 5. Existing scenario scaffolds

- `C:\gd\Dream-World-IX\studies\fork-walkmesh-hotfix\borrow_2507_ingame.py`: the closest match. It runs forks and the real donor in one launch, checks ForkDonorPatch first (:88-95), probes each field the same way (`_probe`, :134), and tallies exceptions (:170, :204-209). `root_fix_2507.py:117` is a four-field variant.
- `C:\gd\Dream-World-IX\studies\persistent-tables\rung0_persist.py`: pokes a nonce byte (:183), watches bits (:114), checks the save sandbox by sha (:71), and chains launches through a state file (:53). This covers the save-load epoch case.
- `C:\gd\Dream-World-IX\studies\test-harness\scenarios\cutscene_check.py`: a raw warp into a field that is not yet playable, plus `watch_cutscene` (:31-38). A stock field at a story beat usually opens on a scripted scene, so this is needed too.

Engine line numbers come from the shared Memoria clone, which can drift from the patches. The `HarnessWarp` hunks are confirmed in `s83-harness-agent.patch:191` and `:959`, and the warp's SC write in `s22-debug-menu-f6.patch:1764`.