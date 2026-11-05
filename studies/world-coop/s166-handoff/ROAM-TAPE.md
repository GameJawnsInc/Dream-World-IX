# COOP_TAPE_WORLD_ROAM: the recording procedure (owner-gated)

T2-A roam and T2-A freeze replay a real s166 **host** walking the world map into a real s166 guest. That host tape,
COOP_TAPE_WORLD_ROAM, has not been recorded. Its recording is **owner-gated**, so no bench script records it on its own.
Until it exists, both legs run **the instrument** (below), and the row `S166-RM-GATE` stays red.

The route, the recorder and the instrument all read one table: `ROAM_PLAN` in
`studies/test-harness/scenarios/coop_world_walk_t2.py`.

## The gates (all must hold; the recorder's `REC-OWNER` row refuses otherwise, before any edit)

1. **The s166 build is deployed on this desktop.** The host must speak wire 15 and publish `netsync.world.lane`. A tape
   recorded on A0b is v14 and capless, so it would carry no trailer to judge.
2. **The owner's Workspace bridge (127.0.0.1:49201, `pythonw` ff9_workspace) is down.** The owner stops it. A bench never
   stops it.
3. **The recorder dials the owner.** The game launches on the install's Memoria.ini. If its `[Netsync]` holds a live role
   (`Enabled = 1`, `Role` host or client), the game dials the owner's endpoint before the bench's own edit, and for about 7 s
   it is the host of the owner's live session (2026-11-01 23:09). Close this hole in one of two ways:
   - **merge the recorder fix** `a1cb7269` from `refs/heads/claude/heuristic-hopper-ac13ad`. Its `tools/harness/netpark.py`
     backs up a live `[Netsync]`, parks it, and restores it byte-exact after the game exits; or
   - **write the ini by hand before launch.** Back up `Memoria.ini`, then set `[Netsync] Enabled = 0`. The recorder's
     IniGuard writes the host values over it and restores your copy afterwards.
4. **No pytest or xdist is running, FF9 is closed, no controller is connected, and nobody is at the keyboard.**
5. **The owner says go.** `COOP_WWT_RECORD_OWNER=1` is that go-ahead on the command line. Without it the recorder records
   nothing.

## The command

```bash
cd C:\gd\Dream-World-IX\.claude\worktrees\s166-handoff-575aeb      # or the merged branch's checkout
COOP_WWT_RECORD_OWNER=1 COOP_WWT_LEG=record py tools/play.py studies/test-harness/scenarios/coop_world_walk_t2.py
```

The desktop runs as the co-op **host**:

- Memoria.ini `[Netsync]` gets `Enabled 1`, `Role host`, `RelayUrl ws://127.0.0.1:49231`, `SessionCode ff9-T2BENCH1`,
  `GuestSlots 0` and `FollowHost 0`. It is backed up first and restored byte-exact.
- `py tools/harness/coop_peer.py serve-guest --port 49231 --report live --no-follow --tap <tape>` is its guest.
  `--no-follow` clears the guest's flags b0, so the host draws no lines and no ghost for it. The host's own trailer is
  unaffected.

## The route (`ROAM_PLAN`, in order)

| Step | What the host does | Why |
|---|---|---|
| 1 | New Game, COOPPARTY seed, field 6603 FARSHORE, encounters off, the story marker `0xA5` on byte 1121 | The guest pairs on 6603 and mirrors the marker |
| 2 | 25 s on 6603 | The replay's pairing room (`rm1`, `rm2`) |
| 3 | Walk out of 6603's door the proven way (`coop_world_wait.walk_out`), then wait for the blocks | The host's own all-block load: its writer re-sends place 3, the seq frozen |
| 4 | Stand 3 s at FS_LANDING (68, -444) | The follow-out's landing pose |
| 5 | Leg 1: bearing 270, 90 u on foot, then stand 6 s | A leg with a stand (`rm4`) |
| 6 | One L1 turn (20 frames of the left bumper) | The design's turn: the camera only, never on the trailer |
| 7 | Leg 2: bearing 180 (west), 120 u: **across the x seam** (x 68 to 1484 through x 0), then stand 6 s | The seam leg (`rm5`); RM-GHOST judges it |
| 8 | Leg 3: bearing 90, 90 u, then stand 6 s | The windows' room |
| 9 | Leg 4: bearing 270, 80 u, then stand 8 s | The windows' room |
| 10 | Teleport onto ICE_TILE (1197.37, -796.7), then stand 20 s | `rm6` |
| 11 | Wait the prompt's frames, Confirm into the Ice Cavern (300), then stand 15 s | `rm7`: the guest's rejoin |

Every walk leg is `Session.world_face(bearing)` and then `world_approach(bearing, distance)`, on foot. Bearings are
`atan2(dz, dx)` in degrees, as `world_face` takes them. If a leg is blocked by the sea or a cliff, `REC-RW` or `REC-RS`
goes red. Edit the bearings in `ROAM_PLAN` (the instrument changes with them) and record again.

## What the recorder checks

- **Setup:** `REC-OWNER` (the gates), `REC-P0` (the port and the listener), `REC-P1` (the host config line), `REC-P2`
  (the host dialled at wire 15) and `REC-M` (the marker).
- **The route:** `REC-WX` (the walk out), `REC-RB` (the blocks), `REC-RL` (the landing stand), `REC-RW` (every leg walked,
  the L1 turn held), `REC-RS` (the seam crossed on foot), `REC-RT` (the tile) and `REC-RE` (300).
- **The tape:** `REC-T` (it reads back whole) and `REC-RF`. `REC-RF` covers `roam_tape_facts`:
  - `rm1` pairing on 6603;
  - `rm2` the story marker;
  - `rm3` wire 15 with fmt-1 trailers that are block-valid on 9011, on foot, flags 0;
  - `rm4` at least 200 u walked in at least 3 legs;
  - `rm5` the seam crossed;
  - `rm6` at least 15 s at the tile;
  - `rm7` 300 held at least 8 s;
  - both windows found (`plan_windows`: the 2.3 s one moving under SnapJumpU, the 6 s one clear of it).
- **Last:** `REC-INI` (the ini restored).

## Where the tape goes, and how to check it

- **Location.** The tape goes to `<main repo>/.harness-runs/coop-tapes/world-roam/<stamp>-host6603-world-roam-s166.f9tape`
  (`COOP_TAPE_DIR` overrides). When every fact holds, `latest-world-roam.json` there points at it, and the roam and freeze
  legs pick it up from that pointer (`COOP_TAPE_WORLD_ROAM=<tape>` overrides).
- **Check it.** All read-only:
  - `py tools/harness/coop_peer.py info <tape>`
  - `py tools/harness/coop_peer.py where <tape> --want world --pose --every 1` (section 0's pose per second)
  - `py tools/harness/coop_peer.py dump <tape> --dir host --type 0 --limit 40` (the trailers)
- **Then re-run** `COOP_WWT_LEG=roam` and `COOP_WWT_LEG=freeze`: NEW, then their levers (`round_a_lever.sh`).
  `S166-RM-GATE` turns green on the recorded tape.

## The instrument (until the tape exists): never a substitute

`roam_instrument_tape` builds a **synthetic** v15 host from `ROAM_PLAN` through coop_peer's real codec at wire 15. Its
frames carry the real trailer layout:

- the field stand;
- the exit's fade and the place-3 load re-sends;
- the walk at 24 u/s, with the walker heading as the rotation;
- the tile;
- the Confirm's fade and 300.

The legs build it into their run directory when no ROAM tape exists, and name it on every row. To build it by hand:

```bash
py studies/test-harness/scenarios/coop_world_walk_t2.py --make-roam-instrument <out.f9tape>
```

**What it is not:** terrain-true (y is 0: the ghost takes the wire's y), clip-true (anim 0) or camera-true (the L1 turn is a
stand). It is a recording of no game. It exercises the guest's receiver, lane and ghost against a well-formed v15 host.
It never stands in for the owner-gated row: `S166-RM-GATE` is red on it by construction.
