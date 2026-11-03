# s166 round A: handoff (2026-11-02, end of session)

Paused for usage. The owner said: hold off on the next workflow and pick up after A0b's tests. Nothing is half-edited in the
engine clone. The design is `S166-DESIGN.md`, and the owner took every recommendation in it.

## Where it stands

| Piece | What | State |
|---|---|---|
| A0 | decision 19, the control-off kit-cell close, on every world map | **deployed + benched**: OLD on s165 measured both hazards; NEW 8/8; the lever reproduces both; s165 solo green. Kit commit `5cbdfd08` |
| A0b | decision 26, the pairing pull | **deployed `9e4365349fab02b1` + BENCHED**: NEW T2 pair 11/11; LEVER T2 pair exactly OLD's five red, CAL green (the wait measured, 653 samples on 6603); regression green (below). S166-PR-SAVEMENU was a mis-derived row, re-derived (below) |
| W1 | A1 the pure core + A2 wire v15 + the kit wire lane | script written, **not launched**: `s166-handoff/s166-w1-wf.js` |
| W2 | A3 sender/cache/lines, A4 the world ghost, the dot from the trailer, their bench rows | not written |
| W3 | the whole-diff review, the s166 patch emit, the README row, the regression set, the laptop package | not written |

**Live DLL:** `9e4365349fab02b1` (A0 + A0b). The revert sets are:
- `py tools/restore_memoria_dll.py 20261102-204556` goes back to A0 (`af1f9e0203d2e6fa`).
- `py tools/restore_memoria_dll.py 20261102-175107` goes back to s165 (`e364ca8d732f8cda`).

**The clone** `C:\gd\FFIX\Memoria` holds s158..s165 + A0 + A0b, uncommitted by design; the s166 patch is not emitted yet.
The round queue says s166 holds the clone (TAKING THE CLONE + two DEPLOYED lines); keep it held.

The snapshots for diffs are in the old session's scratchpad, `C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX--claude-worktrees-dreamy-allen-a2375f\3f9e72b5-f0f3-488a-a7a3-4b0fc4406058\scratchpad\`:
- `s165base` is the clone before s166;
- `s166a0base` is the clone at the A0 build;
- `s166a0bbase` is the clone at the A0b build, and W1's delta is taken against it.

`s166-handoff/s166diff.py` diffs against `s165base`. Edit its `SNAP` if the scratchpad is gone; a fresh snapshot = the
replayed stack via `py tools/memoria_stack_replay.py snapshot`.

## A0b's bench results (finished after the handoff was written)

| Leg | Result |
|---|---|
| NEW T2 pair | 10/11: the pull works; only S166-PR-SAVEMENU red (below) |
| LEVER T2 pair (`pairpull old`) | 7/12: OUT, POSE, ARM, SAVEMENU, REJOIN red = OLD's set (the wait reproduced) -- check S166-PR-CAL's line in `a0b_lever_t2.log` |
| A0 solo legs | 8/8 |
| s165 follow solo out / dot / save | 22/22, 14/14, 10/10 |
| s165 follow T2 walk / duo | 11/11, 19/19 |
| s144 wait T2 wait / T2 rejoin / duo | 8/8, 11/11, 16/16 |

So the only open red was S166-PR-SAVEMENU. **RESOLVED (the next session): the row was mis-derived, not the engine.** An ARMED
guest's Alt+F5 is refused AT THE CHORD by s38's spectator gate (`UIKeyTrigger.OnSaveLoadSceneCommandDetected`:
`!IsMenuControlEnable || IsMirroringStory`), ahead of the save menu, so the pick never reaches R4's counted sites in SaveLoadUI and
neither counter moves. The old row's "refused +1" assumed the pick reaches SaveLoadUI. Kit-side fix, not weakened:
- The row now wants no save menu, refused +0 / would_save +0, and the press pinned to the mirror: WorldHUD 9011,
  `menu_refusal.now` 'audible', mirroring, the DRY lever 'old', and exactly one `savemenu` event from WorldHUD.
- The route presses Confirm only if the menu opened, and a late-opening menu still counts as opened.
- The stand-in models the chord gate (`BW.save_chord_refused`) and emits the engine's `savemenu` event.
- A new fault `chord_gate_open` turns the row red ALONE with every press term green: the row's own calibration.
- A stack pin holds s38's gate (both copies) and s165's adapter call.
- A 3-lens adversarial review held; its minor findings went into the fix.
- Re-bench on `9e4365349fab02b1`: NEW T2 pair 11/11. LEVER T2 pair 7/12, exactly OUT, POSE, ARM, SAVEMENU and REJOIN red,
  with CAL "no predicted red stayed green, no unpredicted red". **A0b is benched.**
- Still owed by the kit, pre-existing from s165: the stand-in RAISES off-HUD / without control where the engine buzzes, and it
  never enters 'Serialize'.

## First: read A0b's bench results

The script `s166-handoff/a0b_new.sh` was running at handoff. It writes one log per leg into the old scratchpad, and
`a0b_new_summary.log` there summarises them. It runs these legs:

- NEW T2 pair
- LEVER T2 pair
- A0's solo legs
- s165 follow solo out, dot and save
- s165 follow T2 walk and duo
- s144 wait T2 wait, T2 rejoin and duo

**Already known, NEW T2 pair: 10/11.** The pull itself works in game. Off its field, the guest:
- pairs and writes its pairing autosave;
- follows out to the tape's pose;
- arms the mirror once, with the world-landing line;
- rejoins 300.

The one red is **S166-PR-SAVEMENU**: refused +0 (want 1), would_save +0, last_why None, the sandbox unchanged, back on the HUD.
The save pick never reached the save guard's count. Check whether the bench's `savemenu` / Alt+F5 pick was refused earlier,
e.g. by the main-menu suppression or another gate that does not count, and whether the judge or the route is wrong. The
kit lane's open note says R4's live-session terms refuse every following guest's save regardless of the mirror, so the
expected counts may need re-deriving from the engine. Fix it on the kit side if it is a judge or route issue; never weaken
the row.

Then the LEVER T2 run should show OLD's reds (the wait measured), A0's legs 8/8, and the s165/s144 sets green. If all of
that holds, commit and log A0b as benched (README-style status in the round queue).

**D-PAIR (the duo) is dropped for now:** both duo games start on 6603, so when the guest's role is applied it is on the
host's last field and the s42 same-field kick arms its mirror before any pull is needed. The instrument row correctly
refused. To bench the pull on the duo, the guest must stand on another field. Do that as a kit follow-up; T2 already covers
the owner's case.

## Next: W1, then W2, then W3

1. `s166-handoff/s166-w1-wf.js` is ready (6 agents: K1 the inter-arrival times, A1, A2, a review, the kit wire lane,
   reconcile). Run it with the Workflow tool's `scriptPath`, after copying it back to a scratchpad or by pointing at the
   repo path. Its `SP` constant names the old scratchpad (snapshots, hn_pins); update it if that folder is gone. Never
   run it while an in-game bench runs (its agents run pytest: THE s159 LAW).
2. W2: A3 (the trailer at the one SetLocal site on both roles + the selftest slot, the receiver cache, LaneGapStep on both
   roles, the host lines, `netsync.world.line`, the bench host ops), A4 (`NetSyncWorldGhost.cs`), decision 12's dot from
   the trailer, the harness levers/keys of decision 25, the stand-in's trailer model, and the Round A bench rows (A-WIRE ..
   A-DOTRIDE, T2-A old/roam/freeze, T2-H, the Duo row). Keep each workflow under 10 agents. One build for W1+W2, then the
   design's Order paragraph, with levers.
3. W3: a fresh whole-diff review, the patch emit (`--skip` the s166 name, every gate as in the s165 row, `NetSyncWorldWalk.cs`
   (+ `NetSyncWorldGhost.cs`) into `tools/memoria_stack_replay.py` DEFAULT_FILES), the README row, the regression set (s165's
   `regress.sh` list + every coop_peer scenario, with restamped tapes), and the laptop package. **The laptop package must
   carry `FF9CustomMap-world`** (the laptop lacks it; s165 two-PC finding 3).
4. The COOP_TAPE_WORLD_ROAM recording needs the recorder fix (`a1cb7269` on `refs/heads/claude/heuristic-hopper-ac13ad`,
   not merged: THE RECORDER DIALS THE OWNER), or the ini written before launch by hand, and the owner's bridge down.

## Preconditions for any bench

- FF9 closed before a build: the build auto-deploys.
- The owner's Workspace bridge (127.0.0.1:49201, `pythonw` ff9_workspace) down for every T2 leg. It was down at handoff.
  Never stop it yourself.
- No pytest running. The bench guard now ignores an exited worker that only lingers in the process table (`d9db1a8b`).
- Solo legs run under `s166-handoff/solo_ini.py` (Enabled 0 + FollowHost 1 written before launch, restored byte-exact).

## Laws learned this session (also in memory `project-ff9-multiplayer-injector`, the s166 entry)

- THE KIT CELLS ARE ON EVERY FREE-ROAM WORLD (and 9013); the close keys on the reader.
- THE TRIGGER IS NOT THE CELL: the 6603 entrance fires within 3 u of (80, -444) only, so FS_LANDING is not on it.
- THE BOAT READS EVERY CONFIRM ON 9011, so one press is closed twice.
- THE BENCH TERM HOLDS THE FREEZE on the forced selftest role.
- THE ZOMBIE WORKER: an exited process stays listed while a handle is held.

## Still open for the owner (from the s165 two-PC session)

- The dot's look: tint, size, and pinned vs hidden at the edge. It draws above the arrow at 80%.
- Whether the FF9Coop mod folder is still wanted.
