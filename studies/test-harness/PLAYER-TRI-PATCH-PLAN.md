# Publishing the player's live walkmesh triangle and floor from the harness agent: patch plan

**Status: SCOPED, NOT BUILT. Awaiting owner approval.** No engine source was edited and no DLL was built
for this. The Python-side quarantine of the dead keys has already landed (see "Already done"). Everything
below is a proposal.

## The defect

`state.json` publishes `player.tri` / `player.floor` from the control character's `PosObj.activeTri` /
`PosObj.activeFloor` (`HarnessAgent.cs` ~1135-1136 in the live clone; `s83-harness-agent.patch` ~1517-1518).
Those fields do not track the player. All line numbers are from `C:\gd\FFIX\Memoria\Assembly-CSharp`:

| Access | Where | When |
|---|---|---|
| write | `EventEngine.BackupPosObjData`, `EventEngine.cs:1441-1442` | leaving the field for a battle (`ProcessEvents.cs:306` result 3, `HonoluluFieldMain.cs:250`, our ~ menu's battle jump `Ff9mkDebugMenu.cs:540`) or a Tetra Master game (result 7, opcode 0xAE) |
| write | `PosObj.copy`, `PosObj.cs:79-80` | context copies (`Obj.copy` ← `EventContext.copy`), which copy an already-stale value |
| read | `FieldMap.RestoreModels`, `FieldMap.cs:522-528` | the return trip. It seeds the respawned controller, and `AddFieldChar`'s `SetPosition` (`FieldMap.cs:574`) then rebinds tri/floor from the saved position |
| read | `HarnessAgent` | every published frame |

Neither `PosObj` constructor sets them. So the published values read **0/0 before the session's first
battle**, which is indistinguishable from a real triangle 0 on floor 0, and they **hold still after one**
however far the player walks. `activeFloor` is a `Byte`, so the controller's −1 is stored as 255.
`studies/test-harness/PLAN.md` listed "floor/tri" as proven in-game on 2026-08-27, and the eb-uses-board
dossier (`dev-tooling.md` §1, §5) built two verdicts on them as per-frame ground truth. Found 2026-09-23
while proving `B_BGIID` in-game (`studies/walkmesh-sensor/PLAN.md` on branch `claude/bgi-sensor`,
`a9622e01`).

## The live value

`Actor.fieldMapActorController` (`Actor.cs:216`, assigned in `FieldMap.AddFieldChar`, `FieldMap.cs:562`)
carries `Int32 activeTri` / `activeFloor`:

- It is initialised to −1 (`FieldMapActorController.cs:103-104`) and rebound from position on every
  `SetPosition` (`:53-56`, `:74-77`).
- `UpdateActiveTri` (`:919`, called from `:366` and `:792`) re-triangulates every frame **while pathing is
  on** (`charFlags & 1`). When no triangle contains the position (off-mesh, or an ambiguous edge), it keeps
  the previous one: history, not geometry.
- `SetPathing(0)` (opcode 0xA8 → `WalkMesh.BGI_charSetActive`, `WalkMesh.cs:1063-1078`) clears the bit and
  resets tri/floor to −1. The one way to hold a non-−1 value while not tracking is a restored `charFlags`
  with bit 0 off (`RestoreModels` after a battle entered with pathing off).

This is exactly what `.eb`'s `B_BGIID` / `B_BGIFLOOR` read (`BGI.BGI_charGetInfo`, `BGI.cs:11-20`, same
`Actor` via `getActiveActorByUID`). It was proven in-game 43/43 on bench 30910: the ids are global across
floors, and the operand is a raw uid, so `B_PTR(250)` addresses the player.

## Already done (Python side, no engine change)

- `tools/harness/channel.py`: `State` exposes the s83 keys **only** as `player_tri_battle_snapshot` /
  `player_floor_battle_snapshot` (255 decoded to −1), with docstrings giving the mechanism above. `raw` is
  left untouched, because `StateRing.dump` promises the agent's own document.
- `ff9mapkit/tests/test_harness.py` has three gates. (1) A **value** gate: no `State` accessor except the
  two snapshots may return the dead values, whatever it is named. (2) The 255 decode and absent-key `None`.
  (3) A same-line tripwire over `tools/` + `studies/` that refuses a bare `["player"]…["tri"|"floor"]` read.
  Both (1) and (3) were proven to go red when broken.
- The one consumer, `studies/test-harness/scenarios/recon.py` (it printed `floor`), is fixed. Across all
  104 local branch tips it was the only reader the tripwire's pattern finds in `tools/` + `studies/`.
  `fakegame.py` keeps mirroring s83's 0/0, with a comment.
- The docs are corrected: `ff9mapkit/docs/TEST_HARNESS.md` (WARNING under "Observing"),
  `studies/test-harness/PLAN.md` (the proven list), and `studies/eb-uses-board/dossier/dev-tooling.md`
  (a CORRECTION block atop §5 plus inline marks).

## The proposed change: one new patch, `s86-harness-player-bgi-tri.patch`

**One file:** `Assembly-CSharp/Memoria/Harness/HarnessAgent.cs`. Its player block was last touched by
`s85-netsync-talk-relay` (the `listener` line). The patch stacks after s85. Nothing else is touched: no
`PosObj` field, no csproj entry, no serialized field (the agent is `AddComponent`-created, not baked, and
this adds only locals and a static helper anyway).

Sketch of the player block, replacing the two `PosObj` lines:

```csharp
            // Where the player stands on the walkmesh: the actor CONTROLLER's triangle/floor, rebound
            // every frame by UpdateActiveTri while pathing is on -- the value .eb's B_BGIID/B_BGIFLOOR
            // read (BGI.cs:11-20). NOT PosObj.activeTri/activeFloor: only the battle-entry backup writes
            // those, so they read 0/0 before any battle and freeze after one (the s83 "tri"/"floor").
            // null = no live controller (world map, battle, mid-load); -1 = the engine's own "none".
            // Computed BEFORE any key is appended: a throw mid-section would leave invalid JSON.
            FieldMapActorController fmac = Try(() => po is Actor ? ((Actor)po).fieldMapActorController : null);
            Boolean live = fmac != null;                       // Unity ==: false for a destroyed component
            Int32 bgiTri = live ? fmac.activeTri : 0;
            Int32 bgiFloor = live ? fmac.activeFloor : 0;
            Boolean bgiPathing = live && (fmac.charFlags & 1) != 0;
            NumOrNull(sb, "bgi_tri", live, bgiTri); sb.Append(",");
            NumOrNull(sb, "bgi_floor", live, bgiFloor); sb.Append(",");
            BoolOrNull(sb, "bgi_pathing", live, bgiPathing); sb.Append(",");
```

Plus two tiny helpers next to `Num`/`Bool` (`… else sb.Append(Quote(key)).Append(":null")`).
`FieldMapActorController : HonoBehavior : MonoBehaviour`, so `fmac != null` uses Unity's operator and
reads false once the field scene has torn the component down. That is the battle and transition case.

**Protocol stays 5.** The change is additive, like F3.1's `listener`. A bump would strand every worktree
whose `channel.py` still says `PROTOCOL = 5`, because the driver REFUSES a newer engine, and the install
is shared. Key presence is the capability signal, per `State`'s own convention: `None` when absent.

**The Python half lands in the same change set, after the DLL, not before.** It adds
`State.player_bgi_tri` / `player_bgi_floor` / `player_bgi_pathing` (1:1 with the keys, so one grep finds
both sides; `None` when absent or null). `fakegame.py` publishes the three keys. Tests cover null → `None`,
−1 stays −1, and the existing value gate still passes, because the new accessors read new keys. The
TEST_HARNESS.md WARNING becomes accessor docs plus the three caveats: off-mesh keeps history,
`bgi_pathing` false means the engine is not updating, and null means no field actor.

## Build and capture procedure

This follows the `building-the-memoria-engine` skill, memory `project-ff9-memoria-build`, and
`memoria-patches/README.md`.

0. **Get the owner's go-ahead.** The build auto-deploys over the live install that every worktree shares.
1. **Audit the shared clone first**, because it has silently lost patches before. Run
   `py tools/memoria_stack_replay.py diag` (its default file set includes `HarnessAgent.cs`). Every file
   must print `==` before any edit. A drifted `HarnessAgent.cs` means stop and reconcile first.
2. Edit `HarnessAgent.cs` in the clone (the sketch above).
3. Compile-check without deploying: `py tools/build_memoria.py --no-deploy --label s86-bgi-tri`. The
   clone's csproj has the `DWIXNoDeploy` condition (`Assembly-CSharp.csproj:1503`).
4. **Capture as a tool, not by hand:**
   `py tools/memoria_stack_replay.py emit --files Assembly-CSharp/Memoria/Harness/HarnessAgent.cs --emit-to memoria-patches/s86-harness-player-bgi-tri.patch`.
   Then gate it the way the README rows do, in BOTH directions, because reverse-only once passed an s83
   capture that was missing a hunk:
   - `snapshot --stop-after s85-netsync-talk-relay.patch`;
   - `git apply --check` + `patch -p1 -F0 --dry-run` onto that snapshot;
   - `git apply -R --check` against the clone;
   - `diag` with the patch installed: all `==`.
5. **Close FF9, then build and deploy:** `py tools/build_memoria.py --label s86-bgi-tri`. It refuses
   without the full 3×2 pre-build backup, sha-verifies both arches, and reports the clone's in-flight edit
   count first. Read that count: a build deploys every other session's uncaptured edits too, so an
   unexplained count means stop.
6. Relaunch, then verify (next section). If it fails:
   `py tools/restore_memoria_dll.py <the printed timestamp>` from the MAIN repo.
7. Add a README row for s86. The shipped `dwix-custom-memoria-*.zip` lags until it is re-cut, and that
   re-cut is a separate release decision.

## In-game verification

Calibrate against the instrument that is already proven, not against a new one.

- **Bench 30910** (`studies/walkmesh-sensor/bench/bgi0.field.toml` on `claude/bgi-sensor`). It was
  registered in `FF9CustomMap` at the time of writing; re-check with the `--suite` preflight, since
  registrations move as sessions deploy. Its `rung0_bgi.py` already walks 14 stops across the
  floor-0/floor-1 seam with a HUD reading `B_PTR(250) B_BGIID` / `B_BGIFLOOR` and an exact offline oracle.
  Add one check per stop: `st.player_bgi_tri == PTRI == oracle` and `st.player_bgi_floor == PFLR`.
  **Floor-1 stops must read 8..15**, which proves the ids are global and not per-floor.
- **The dead field's own failure mode:** fight one battle (the harness battle verbs, or the ~ battle
  jump), return, walk to two stops, and assert `bgi_tri` follows the oracle. On the old DLL the snapshot
  would stay frozen there.
- **Negative controls:** `bgi_tri is None` on the world map and during a battle, and `bgi_pathing` is
  true on the bench.
- One launch, one change. Run the core suite afterwards: the change is additive, and no existing member
  reads `tri`/`floor`.

## Decisions for the owner

1. **Approve the patch at all.** Without it, the live triangle stays available only in-field, via
   `B_PTR(250) B_BGIID`, which works today on stock but costs an `.eb` HUD row per bench.
2. **Drop `tri`/`floor` from the document (recommended)**, keep them renamed (`tri_battle_snapshot`), or
   keep them as-is. The case for dropping: the harness reads them nowhere except a seed for the post-battle
   respawn, which is engine-internal, and every artifact that still carries them re-arms the trap for the
   next reader (`state-final.json` misled the dossier). Dropping them is safe for other worktrees:
   `recon.py` was the only reader and is fixed here.
3. **Key names `bgi_tri` / `bgi_floor` (recommended).** They are named for the `.eb` tokens that read the
   same value, and deliberately NOT `tri`/`floor`, so old and new semantics can never share a key in any
   artifact.
4. **Include `bgi_pathing` (recommended).** It is one bool. Without it, a triangle held by a restored
   pathing-off controller is indistinguishable from standing still.

Size: ~20 lines of C# in one file, and ~40 lines of Python plus tests. It needs one launch to verify.
