---
name: laying-out-ff9-fields
description: Spatial layout for FF9 fields -- world axes, cardinals, facing bytes, model scale, spacing, and the offline layout probe. Use this EVERY time you place content in a field.toml (NPC/prop/spawn/arrival/gateway/zone positions, `face` values, cutscene walk/path coordinates) or narrate a direction in FF9 ("the goblin walks north", "the door on the left", "behind the player") -- in dialogue text, commit messages, study notes, or questions to the playtester. Also for "how big is a character / how far apart should NPCs be / will these overlap on screen / which way does W move". The recurring failure this prevents -- content packed too close (actors jam under ~192u) and inverted cardinals (FF9's camera sits at NEGATIVE z, the room's FRONT is -z, and yawed cameras rotate the whole screen<->world mapping). Run `tools/field_layout_probe.py` and READ its PNGs before claiming any layout is correct.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Laying Out FF9 Fields

Spatial ground truth for placing and describing content in a field. Two chronic mistakes this
skill exists to kill: **inverted cardinals** (narrating "north" for what is south on screen) and
**over-packed layouts** (actors closer than the engine's own collision allows). Both have the same
cure: don't reason from raw coordinates -- render the layout offline and look at it.

## The world frame (memorize this block)

```
              +z   NORTH  =  the BACK of the room  =  up-screen (at yaw 0)
               ^
    -x WEST <--+--> EAST +x          y = up; the ground plane is X/Z
               v
              -z   SOUTH  =  the FRONT  =  toward the CAMERA  =  down-screen
                             (the camera sits out here: C = (0, +D*sin(pitch), -D*cos(pitch)))
```

- The camera lives at **negative z**, above the floor, looking toward +z. So a room's near/front
  edge has the MOST NEGATIVE z. (In-game proven: ARRTEST, `studies/field-entry/README.md` --
  "FRONT = toward the camera = NEGATIVE z"; the canonical vivi-hut floor spans z -2400..-800 with
  the gateway strip at the front/-z end.)
- **Facing byte** (`[player] face`, `[[npc]] face`, arrival `face`, chest/prop `face`, TurnInstant):
  raw FF9 0-255 compass, written verbatim -- **0 = south (faces the camera), 64 = west, 128 = north
  (faces away), 192 = east**. Direction vector: `(dx, dz) = (-sin(f/256*2pi), -cos(f/256*2pi))`.
- **Movement**: with the default control TWIST (-1), W/up moves the player toward **+z** (up-screen,
  into the back). The kit auto-derives the TWIST from camera yaw so W tracks "up the screen" at any
  yaw (`build.resolve_control_value`).
- Cutscene `walk = [x, z]` / `path` / `teleport` and every authoring surface take plain world
  `(x, z)` -- the kit hides the engine's one sign quirk (POS3) internally. No authored negations.

## THE CARDINAL LAW

Cardinals are **world-frame** terms (N=+z, S=-z, E=+x, W=-x -- exactly the facing-byte compass).
The screen mapping above holds **only at yaw 0**. Real fields ship yaws up to +/-169 degrees
(GZML -24, TSHP1 -90, TRNO -169), and a fork/borrowed `.bgx` camera can point anywhere. So:

- **Never narrate a screen direction from coordinates.** Run the probe (below) and quote its
  COMPASS table -- it measures the mapping empirically through the exact engine projection, so it
  is right for synthesized, yawed, AND borrowed real cameras.
- When writing prose for the playtester on a yawed camera, give both frames: "walks north
  (up-left on screen)".
- Dialogue/flavor text a PLAYER reads should use screen-relative words ("the door on the right")
  or landmarks -- the player has no compass.

## Scale (world units -- the packing numbers)

| Thing | Value | Consequence |
|---|---|---|
| Player controller radius | **48u** (`cam.COLLISION_RADIUS_W`) | The player CENTRE can never get within 48u of a walkmesh edge; extend the mesh 48u past painted floor edges the player should reach. |
| Object<->object collision | **96u each** (`cam.OBJECT_COLLISION_W`) | Two characters **jam at < ~192u centre distance**. Anything under that = actors shoving each other. |
| Standing-NPC spacing | **>= 300u** | What real fields use; 192-300u is walkable but reads cramped. Conversation partners: ~250-400u. |
| Human height / width | **560u / ~100u** | Moogle 440, chest 300, tent 680, ladder 700 (`paint.HEIGHT_BY_NAME`). |
| Canonical room | **~2400-2800 x 1600-2200u** | Scaffold camera: pitch 48, distance 4500, fov 42.2, canvas 384x448. A room is ~25 character-widths across -- 5 NPCs is roomy, not crowded. |
| Gateway edge strips | **~170-600u deep** | Wide enough the player can't skirt them; never under the spawn/arrival point. |
| Facing-arrow sanity | face 0 looks at the viewer | An NPC "greeting the player entering from the front door" faces 0 (south), not 128. |

On-screen size is `H / |z_cam|` -- a back-of-room NPC renders visibly smaller and two actors spaced
fine in world can still stack on screen (depth foreshortening). The probe warns on exactly this.

## The probe -- run it, then LOOK

```
py tools/field_layout_probe.py <field.toml> [--out DIR] [--camera N]
```

Outputs (default `tools/scroll_out/layout_probe/<name>/`) -- **Read all three**:

- **`topdown.png`** -- world X/Z from above (+z UP, matching yaw-0 screen): walkmesh floors, zone
  quads, true-scale 48u/96u collision rings, facing arrows, the camera's position (the FRONT is the
  edge nearest it), and a compass rose whose green arrow shows which world way is UP-SCREEN.
- **`camview.png`** -- the painted-canvas view through the exact `cam.to_canvas` projection:
  walkmesh outline, zones, each marker with its projected height pole = how big the model actually
  renders at that depth.
- **`report.txt`** -- the COMPASS table (quote it when narrating), every item world->canvas with its
  facing named, and WARNINGS: colliding pairs (<192u), tight pairs (<300u), wall-huggers (<48u from
  an edge), off-mesh, off-canvas, content inside trigger zones, world-spaced-but-screen-overlapping
  pairs.

Workflow: author/edit the field.toml -> **probe** -> fix warnings + check the picture matches your
intent -> `ff9mapkit lint` -> deploy -> `tools/game_snap.ps1` / playtest. The probe is offline and
instant; there is no excuse to deploy a layout you haven't looked at.

## Routes -- scripted WALKS are segments, not points (probe them too)

A `[[marker]]` may carry **`path = [[x,z], ...]`** (+ `closed = true` for a patrol ring): the
polyline a scripted walker (patrol, march, flee line, cutscene walk) will actually travel. Markers
stay build-inert; the probe DRAWS each route on both PNGs and **walkability-SWEEPS every leg**
(~40u samples), warning with world coordinates on any off-mesh span (drawn in red) and on legs
that pass under 48u from a walkmesh edge. Declare a route for EVERY scripted multi-point walk --
the BTRAID bench shipped a patrol ring whose two off-mesh legs stalled guards in-game, invisible
to point checks; the sweep finds that class offline in seconds.

Movement facts the sweep encodes (engine: walkers move STRAIGHT at their target and slide on
contact -- there is NO pathfinding):
- **Convex obstacles are survivable; concave ones are not.** A walker clipping a round monument
  slides around it (ugly but progresses); one entering a bay, notch, or spur WEDGES and stalls.
  Off-mesh spans = must-fix; sub-48u grazes along a long PARALLEL wall = usually a tolerable
  slide -- judge with the picture.
- **Snap walk targets to points with real wall clearance (~100u+), not merely on-mesh.** A bare
  point-in-triangle test happily accepts a 1u edge sliver; a unit sent there is shoved off it
  and oscillates. When generating layouts programmatically, filter candidate points by
  distance-to-boundary-edge before nearest-snapping.
- Long walks across an irregular field usually need WAYPOINTS at the concavity mouths (necks,
  gates); pick them from the probe's picture, then sweep the multi-leg route until clean.

Scrolling fields ([camera.scroll] enabled): the probe auto-skips OFF-CANVAS warnings there --
the viewport pans, so content beyond one static screen is normal, not a bug.

Warning semantics: **spawn/arrival off-mesh = a real bug** (player strands). An NPC/prop off-mesh
is often deliberate set dressing (vivi-hut's Vivi stands 100u behind the walkable edge, against the
wall) -- confirm it is intentional, don't "fix" it reflexively.

## Caveats

- A **campaign field with NAMED flags** (`set_flags = [{flag = "ember_taken"...}]`) won't load
  standalone (flags resolve at journey level) -- probe it before wiring named flags, or use numeric
  indices while iterating layout.
- A **borrowed camera** needs its `.bgx` beside the toml or in the extract cache; fresh worktrees
  have no cache (same reason ~451 byte tests skip there). Extract or copy it first.
- Multi-camera fields: probe each `--camera N`; every camera has its OWN compass and its own
  control direction.
- The probe reads geometry only -- it can't see art occlusion (a marker may be behind a painted
  pillar) or `.eb`-scripted motion. For cutscene WALKS, probe the endpoint coordinates too (add a
  temporary `[[marker]]`), and remember `Walk(x, z)` blocks until arrival.

## Cross-links

Camera/walkmesh construction math -> the `authoring-ff9-scenes` skill + memory
`[[project-ff9-camera-math]]`. Event logic / TurnInstant / walk opcodes -> `authoring-ff9-field-scripts`.
Off-mesh + reachability build warnings -> `ff9mapkit lint` (the probe complements, not replaces, it).
