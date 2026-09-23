# `[[platform]]` land ride and Map Int16 byte offsets

**Status: closed.** Fixed in `content/platform.py` and proven in-game by the harness on bench 30960.

## The defect

A Map var index is a **byte offset** into `EventContext.mapvar`, which is `Byte[80]`
(Memoria `EventContext.cs:9`). `EBin.GetVariableValueInternal` reads an Int16 at index k as
`buffer[k] | (sbyte)buffer[k+1] << 8` (`EBin.cs:1868`), and the Map source passes the token's index
straight through (`EBin.cs:1631`). So `I16[3]` and `I16[4]` share byte 4.

The land ride kept its state in Int16s at 3, 4, 5 and 6. It captures the boarding x into 5, then z into
6, then the height into 4. After those three writes, bytes 5-6 hold the height's high byte and z's low
byte. The per-frame scratch write at 3 then overwrote the stored height's low byte. The ride places the
player at `start_x + (land_x - start_x) * progress`, so the first frame threw him far off the mesh.

The rise ride uses two of the same Int16s. It survived only because it never reads the stored height
back after the scratch write. The cutscene `wait_signal` guard had the same slot-number assumption at 3.

## The A/B, one bench, one change per run

`bench/land.field.toml` has a ground floor at height 0 and a deck 200 up. No triangles or links join
them, so the ride is the only way across. It lands at (700, -1200) at speed 5, which gives 40 sampled
frames. `rung0_land.py` boards, samples every published frame, and checks each one against the straight
line from the measured boarding point.

| Build | Ride offsets | First ride frame (x, height, z) | Worst off-line | Verdict |
|---|---|---|---|---|
| old layout | 3, 4, 5, 6 | (7203, 5, -878) | 7741 u | A2 FAIL, 8/9 |
| fixed | 70, 72, 74, 76 | (-509, 5, -468) | 1 u | 9/9 PASS |

The offline byte-offset model (`tests/test_mapvar_layout.py::_Ride`) predicted the old layout's frames
exactly: 7203, 7036, 6869, 6703 for x, and -878, -886, -895, -903 for z. The corrupt x depends only on
the height's high byte and z's low byte, so a slightly different boarding x gives the same numbers.

Both runs also landed at (700, -1200) at height 200 and walked on the deck at that height. That
confirms the bench's sign: a walkmesh OBJ vertex at y = -200 is a floor 200 up, the height is
`pos[1]`, and selfY is -pos[1].

Run artifacts: `.harness-runs/20260923-180502-platform-land-A-oldlayout`, `…180544-platform-land-B-fixed`.
The old-layout build was deployed by patching the four constants in-process before
`tools/deploy_field.py` ran. No source was reverted.

## Reproduce

    py tools/deploy_field.py studies/platform-land/bench/land.field.toml --id 30960 --name PLTLAND --text-block 30960
    py tools/play.py studies/platform-land/rung0_land.py --label platform-land

**Harness note.** When a scenario polls every frame (`state_every(1)`), read `g.channel.state()` and skip a
`None`. A torn read of `state.json` makes `g.state` raise "no state published". The first A run died that
way mid-ride, while the game itself was fine.
