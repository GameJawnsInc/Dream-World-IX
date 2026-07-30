# Rung 6 — the floorplan composer: the verified spec

> Companion to [`PLAN.md`](PLAN.md) (Rung 6's block there is the charter; this is the buildable math).
> **Every formula here survived an adversarial pass** — a 5-lens panel that derived each one
> independently and ran probes against the real code, then a chair that re-ran every decisive probe.
> **25 findings.** Five of them were defects that would each have cost a playtest. Read §1 before
> touching a number: the draft's own values were wrong in ways that looked right.

**What it does.** The author lays out several rooms on a plan-view chart, declares which shared walls
are doors, and gets a wired dungeon: one FF9 field per room, gateways both ways, an arrival position
*and facing* per side, encounters, save-point siting.

> ★ **THE DRAWN-MESH LAW** (PLAN.md §4) — the human draws the walkmesh; the composer never infers one.
> The composer's whole job is **topology**: deterministic, testable, no inference. `shared_edges`
> *offers* candidate walls; the author declares the door.

---

## 1. WHAT THE ADVERSARIAL PASS BOUGHT

Each line is a value or rule that was wrong in the draft, with the measurement that killed it.

| Draft said | Truth | The measurement |
|---|---|---|
| Derive the door's inward normal by **point-in-polygon disambiguation** | **Anchor it to the polygon's own carrying edge**; PIP is a *fence*, never the decision | PIP is decisive only when the seg lies EXACTLY on the wall — and hand-drawn walls don't. Off-coincident, both probe points are inside (overlap) or both outside (gap). Sweep of wall offset −8..+8u × both seg orders, n=66: the draft **inverted 32/66 = 48.5%**, identically for both `rot90` signs. Edge-anchored: **0/66**. |
| Player wall radius = `cam.COLLISION_RADIUS_W` = **48** | **`R_WALK = 80`** for the composer's own gates | The kit's player Init runs `SetObjectLogicalSize(20, 24, 40)`; Memoria `DoEventCode.cs:1531` does `radius = size * 4` → **80**. `cam.py:66-70`'s justification (`bgiRad*4` from the `.bgi`) is factually wrong — `bgiRad`'s only writer is the battle-return backup, so it is **0** on a fresh load. `RadiusValid`→`BGI_computeNewPoint` pins the centre at *exactly* radius. ★ **IN-GAME CONFIRMED 2026-07-30** (§6.1 resolved) — `cam.COLLISION_RADIUS_W` fixed to 80 to match. |
| Fit the camera by **bisecting distance** on a canvas-AABB test | Bisect, **but gate every vertex on `depth >= NEAR_W`** | Apparent size goes as `1/|D + cos(p)·z|`, which has a **pole** — so size *grows* with distance below it. The fits-flag transitions **twice**. The draft's fit returns `D = 200` with `minDepth = −740` for a corridor at pitch 20: a camera 740u *inside the room*, passing the margin test comfortably, rendering the near floor mirrored through the camera plane. |
| Centre the room on the canvas via `solve_z_for_canvasY(CANVAS_H/2)` | **Front-align** the room's front edge on row 420, with the composer's own `z_for_row` | Step 2 was a **tautology**: `to_canvas` is `range[1]/2 + centerOffset[1] − rawProj.y` and `rawProj.y = 0` at `z = 0`, so it returned 0 identically for all 28 pitch×distance pairs. Front-align won canvas fill **10/10**; canvas-middle left 96–201 dead rows (worst: a 4000×1200 room at pitch 26 occupied rows 205–247, **8.9% fill**). |
| `cam.solve_z_for_canvasY` / `guide.frame_floor` are the tools | **Never call either.** The composer carries `z_for_row`. | Both are unsound at low pitch — `frame_floor(130, 420)` *raises at every distance* for pitch 15. This is a live defect in shipped code, spawned as its own task; `pack.new_project` swallows it, so `ff9mapkit new --pitch 15` silently ships a template mesh. |
| An arrival needs no explicit `face` | **`face` is MANDATORY on every row, including `entrance = 0`** | `content/npc.py:372` emits **no** `D9(6)` write for a `face`-less row — and the template writes `D9(6)` unconditionally at the head of the player Init as a hard-coded **0 = SOUTH**. So `face is None` is not "no facing", it is a silent *"face the camera whichever wall you came through"*. On a south door the player walks in with their back to the room and **none** of the draft's nine gates fires. |
| `q0 → q1` order is a convention worth honouring | **It steers the walk-out, and NO gate can check it** — assert | The Range body runs `CalculateExitPosition` (MJPOS, `DoEventCode.cs:2251-2252`) which reads **`q[0]` and `q[1]` only**, projects the player onto that segment and stores it as the walk target. Measured on a west-wall strip: correct order → exit target on the wall line; inner-edge-first → **130u backward into the room** during the fade; rotated by one → a **550u sideways slide along the jamb**. All three score `zone_fan_audit` **0.0/0.0**. |
| `zone_fan_audit == 0` on a parallelogram, by construction | **`<= 0.02`** (the repo's own threshold, `workspace/backdrop.py:576`) | 2996/3000 legal strips score exactly 0/0 — worst spill `7.58e-4`. Equality would refuse ~1 legal door in 750. And the audit is **vacuous on degeneracy**: `depth = 0`, a zero-length seg and four collinear points each score a perfect 0/0 with 0 triangles. |
| `region_overlap_pairs` is the TREADQUAD judge; make it an error | **Candidate filter + a separating-axis confirm** | It is an **AABB** test: two provably disjoint 45° bevel strips report 1 pair. A raw error refuses every bevelled or diagonal room — the shapes a human actually draws. Also: `[[savepoint]]` is absent from its box list although `savepoint_region` has an auto-firing `RANGE_TAG` of exactly that class. |
| `shared_edges` tests near-parallel with `dot > 1 − eps` | **`abs(dot)`** | Two consistently-wound abutting rooms share **antiparallel** edges: both `_signed_area` = +1000000, A's dir `(0,+1)`, B's `(0,−1)`, **`dot = −1.0`**. The obvious test finds **zero doors on every plan** — a silent total failure with nothing to debug. |
| `min_len = 192` for a passable door | **Deleted** — replaced by G9's real standable-area test | The arithmetic didn't follow from its own reason (96u wide → floor 96, not 192) and the radius is 80, not 48. Measured zero-crossing is `2·R_WALK` = **160**. And an unconditional 192 would refuse a legal 100u door in the middle of a long wall. |
| `triangulate` degrades via its "numerically stuck" fallback | It overcounts through its **ordinary** path — so implement a real segment-intersection test | A self-intersecting pentagon yields a triangle-area sum of **142500** against a true `|shoelace|` of **37500** — a **3.8× overcount**, `stuck` never firing. A bowtie: 40000 vs 0. Valid L and U triangulate exactly, so **do not gate on concavity**. |
| Erode the polygon with `outset_polygon(poly, -R)` | **Grid-sample `standable`** — no miter, no blowup | `outset_polygon` is a **miter** offset. At only 48u, base verts 100u apart: half-angle 4.76° → tip error **244u**; 1.43° → **913u**; 0.14° → **9552u**. A plain L outsets cleanly, so a convex fixture cannot catch it. |
| Snap the facing byte to the nearest cardinal within 8 | **Deleted** | A strict no-op on axis-aligned walls, and it fires only where it introduces error: 8 bytes = **11.25° of yaw**, so an 11°-tilted wall gets a cardinal arrival while its door quad stays tilted, and two near-identical drawings end up 9 bytes apart. Non-cardinal bytes are first-class in real FF9 (the engine hardcodes 4, 22, 117, 120, 126, 228, 240…). |
| Use `pack.suggest_ids` / trust `pack.check_custom_id` | **Neither.** Own the pre-flight. | `pack.suggest_ids(30500, 3)` **raises** — it caps at `CUSTOM_ID_MAX = 9899` while this lane's pin *is* 30500. `pack.check_custom_id(9005) → 9005`: no carve-out for the 9000-9012 engine world-map hole. `deploystack.check_id_collisions` deliberately **excludes** the target folder, the opposite of what a fresh mint needs. |
| Centroid-first for the spawn point | **Deleted** — the grid search is load-bearing | For a plain L-shaped room the vertex-average centroid (the idiom `build.py` already uses for zone centres) lands **exactly on the reflex corner**, outside the polygon. For a U room **both** the vertex average and the area centroid fall outside. An L is the normal case for a hand-drawn plan. |
| The art rides along | **The art must be polygon-clipped, and the shipped painter can't** | `write_placeholders` takes a `FloorFrame` — a rectangle. In a real build the walkmesh occupied canvas rows 328–420 inside a floor painted 130–420: **68% of the checkerboard unwalkable**, inverting the placeholder's stated purpose as an alignment check. |
| — (not in the draft) | **`off_r` must be INTEGER** | `bgi.build` rounds every vert to an int. A fractional offset makes the mesh, the door quads and the arrival each round independently and drift apart by up to 1u. |
| — (not in the draft) | **`ff9mapkit lint` returns 1 on warnings-only** (`cli.py:820-824`) | Every composed room emits the `entry_settle = "auto"` advisory, so a pipeline gating on the exit status aborts on **every** room. Parse the error count. |
| — (not in the draft) | **`[encounter]` has no closed key set** | `build.py` hard-errors on an unknown `[[savepoint]]` key (`_sp_keys`, `:1760`) but there is no `_enc_keys` anywhere. A typo (`feq` for `freq`) builds clean and silently runs at the default frequency. The composer needs its own gate. |

---

## 2. THE THREE FRAMES

```
PLAN frame   — one shared world-unit frame the author lays rooms out in. Same axes as FF9
               (+x east, +z north). Lives ONLY in floorplan.json. Adjacency is meaningful here.
                 │
                 │  per-room PURE TRANSLATION  off_r = (dx, dz)   — INTEGER, rounded ONCE
                 ▼
ROOM frame   — each field's own world frame. This is what ships: walkmesh.obj verts, [[gateway]]
               zone corners, [[player.arrival]] pos, [player] spawn, [[savepoint]] zone,
               AND the background art.
                 │
                 │  cam.to_canvas  /  the closed form (C0)
                 ▼
CANVAS       — the 384x448 logical frame the play camera renders.
```

> ★ **THE TWO-FRAME LAW.** FF9 fields have **no** spatial relationship to each other — there is no
> global dungeon coordinate system in the engine, so the plan layout is an authoring fiction. Every
> derived artifact of a room therefore rides the **same** `off_r`: door quads, arrivals, spawn,
> savepoint, **and the art**. Mixing frames is this rung's equivalent of the transpose bug — it looks
> plausible and is wrong. Rotation and scale are excluded; translation only (kit cameras are yaw 0).

The chart is **not** a camera. A pitch-90 `BackdropCanvas` camera is exactly affine but anisotropic by
`1/K_VSCALE = 15/14`, so a drawn square would become a 15:14 room. The composer owns an isotropic
px↔world pair. (`BackdropCanvas.click_to_world` hard-raises when `_cam is None`, so it cannot be
borrowed for a chart.)

---

## 3. THE CONSTANTS — sourced, and not to be re-derived

| Name | Value | Source |
|---|---|---|
| `R_WALK` | **80.0** | the composer's own literal — now equal to `cam.COLLISION_RADIUS_W` (both 80 since 2026-07-30), but deliberately a SEPARATE object, fenced by an equality assert. A silent drift in either direction should go red, which an alias cannot do. |
| `R_OBJ` | 96.0 | `cam.OBJECT_COLLISION_W` (`scene/cam.py:82`) — correct in the repo (arg2=24 of the same opcode) |
| `K_VSCALE` | 14/15 | `scene/cam.py:36` |
| `CANVAS_W`, `CANVAS_H` | 384, 448 | `scene/guide.py:24` — **not** in `cam.py` |
| `BACK_ROW`, `FRONT_ROW` | 130.0, 420.0 | `guide.frame_floor` defaults (`scene/guide.py:121`) |
| `FAN_TOL` | 0.02 | the repo's own gap/spill threshold (`workspace/backdrop.py:576`) |
| `WORLD_LO/HI` | 9000, 9012 | `journey.py:62` — the engine world-map hole |
| `ID_MIN/MAX` | 4000, 32767 | `pack.CUSTOM_ID_MIN`, `pack.FIELD_ID_MAX` |
| `NEAR_W` | 200.0 | composer-owned near-plane clearance. `synth_r_t` Int16 quantization is 0.06 px at depth ≥ 2000 but blows up without bound near the pole |
| `FIT_MARGIN` | 8.0 canvas px | quantization is ≤ 0.07 px at depth ≥ 500, so 8 is safe; 2 is not |
| `DEPTH_DEFAULT` | 250.0 | 68.3% of the strip standable at `R_WALK` |
| `DEPTH_WARN` | 170.0 | ARRTEST's in-game-proven wall-press depth; 53.5% standable |
| `GRID_STEP` | 8.0 | the sampling step for every area/clearance test |

---

## 4. THE CORE MATH

Full executable formulas live in the module docstrings of
[`ff9mapkit/ff9mapkit/floorplan.py`](../../ff9mapkit/ff9mapkit/floorplan.py) — that file is the
single owner. The shape:

- **C0 `project_floor` / `horizon_row` / `z_for_row`** — the closed-form projection.
  `project_floor(x,z) = (cx0 + xH/|dep|, cy0 − K·sin(p)·H·z/|dep|, dep)` with `dep = D + cos(p)·z`.
  Max error **0.0706 px** vs `cam.to_canvas` at depth ≥ 500 over 8 pitches × 4 distances.
  `z_for_row` **replaces** `cam.solve_z_for_canvasY` (see §1).
- **C1 `polygon_problem`** — verts ≥ 3 · no near-duplicate consecutive verts · **a real O(n²)
  non-adjacent segment-intersection test** · area floor · not all-collinear. The area test must run
  **before** any `_as_ccw` call: `_as_ccw` tests `signed_area >= 0`, so a zero-area polygon "keeps
  order" silently and its winding carries no meaning.
- **C1b `standable(poly, R)`** — grid cells whose centre is inside `poly` and ≥ `R` from its boundary,
  i.e. every position the player *centre* can occupy. Every clearance gate reduces to this. Robust by
  construction: no miter, so no acute-spike blowup.
- **C2 `interior_normal(poly, seg) -> (n, seg_projected)`** — find the polygon's own **carrying edge**
  (least perpendicular distance among edges whose span brackets the seg midpoint), take
  `n = (−dz/L, dx/L)` — reusing `imagefield.py:483`'s stated convention verbatim rather than
  re-deriving it — project the seg onto that edge, orient it along the CCW traversal, then **assert**
  the normal is inward. **Returns the projected seg, and C5/C6 must consume THAT one**, never the raw
  candidate: that projection is what makes every artifact ride the room's own wall. (Measured on a
  4u-offset wall, the draft produced a gateway quad with **0 of 4 corners on the mesh** and an
  off-mesh arrival; corrected gives 4/4.)
- **C3 `face_of_dir(nx,nz) = round(atan2(−nx,−nz)/2π·256) % 256`** — the **engine's** formula, not a
  kit convention: `TurnInstant` sets `eulerAngles.y = byte/256·360` (`DoEventCode.cs:1211`), and the
  controller derives that same rotation as `atan2(−moveVec.x, −moveVec.z)`
  (`FieldMapActorController.cs:902`). Round-trips all 256 bytes with 0 mismatches and reproduces 3/3
  of Square's own shipped arrival facings on real field 100. **No cardinal snap.**
- **C4 `shared_edges(A, B, *, tol=8.0, angle_tol_deg=2.0)`** — `abs(dot)` on the edge directions,
  both-ways distance-to-line, 1-D overlap on one chosen direction, then **G12**: the two rooms'
  interior normals must be antiparallel. `angle_tol_deg` must be explicit — with only a distance
  tolerance the admitted angle error is length-dependent (a 3000u edge rejects > 0.15°, a 200u edge
  accepts ~2.3°).
- **C5 `door_strip(poly, seg, depth) = [p, q, q+n·depth, p+n·depth]`** on the **projected** seg,
  rounded (not truncated — the build packs `<hh` via `int()`). A parallelogram, so convex by
  construction. `q0→q1` **is** the door segment — asserted, because no gate can see it.
- **C6 `arrival_for`** — `pos = mid + n·inset` with `inset = depth + 2·R_WALK`, searching inward from
  there down to `depth + R_WALK` for the first point that clears G2; `face = face_of_dir(n)`, never
  None. Raises naming the shallowness rather than minting an off-mesh arrival.
- **C7 `fit_play_camera(poly, *, pitch, fov)`** — refuse `pitch < pitch_floor(fov) + 1` (below `p*`
  the horizon is inside the canvas *and* a behind-camera point can fake a fit; `p*` ≈ 25.7° at
  fov 42), then bisect distance in [300, 60000] on: every vertex at `depth >= NEAR_W` **and** inside
  the canvas by `FIT_MARGIN`. Offset = **AABB centre** in x (not the centroid — they differ by
  (−250,−200) on an L, enough to push a corner to canvas x 399.8 off a 384-wide canvas) and
  **front-align** in z (`z_for_row(FRONT_ROW) − z0`). `off_r` rounded to int once.
  ⚠ `guide.make_camera` validates nothing — `distance = −3000` and `1.0` both return plausible
  projections. The composer owns the bound.
- **C8 `interior_point`** — maximize distance-to-boundary over `standable`, clearing every avoid-zone
  by `R_WALK`. The grid search is the implementation, not a fallback.

---

## 5. THE GATES

Compose-time **errors** unless marked. THE DEFAULT-VALUE LAW: every minted value is real, or loudly
refused.

| # | Gate |
|---|---|
| **G1** | every polygon simple (C1) — a real segment test, **not** "did `triangulate` get stuck" |
| **G2** | every arrival & spawn on-mesh, ≥ `R_WALK` from every mesh edge, ≥ `R_WALK` from every trigger-zone **polygon**. The axis-**band** version is a **WARN**, never an error — as an error it refuses Square's own field 100 (entrance 231 sits 23u clear of zone 114's x-band) |
| **G3** | reciprocity — a two-way door emits gateway **and** arrival on both sides. A missing arrival row is SILENT (falls through to `[player] spawn`); `lint_player_arrivals` catches only self-loops and `campaign.py` g2 is advisory-only |
| **G4** | no two tread-class zones genuinely overlap — `region_overlap_pairs` as a **candidate filter**, then a separating-axis confirm (touch-only ≠ overlap). Include the savepoint's `RANGE_TAG` region as a fifth class |
| **G5** | ids distinct, in band, ∉ 9000-9012, pre-flighted against the live stack via `deploylog.registrations` (a **tuple**) |
| **G6** | every room fits its play camera with every vertex at `depth >= NEAR_W`, and `pitch >= p* + 1` |
| **G7** | `max(gap, spill) <= 0.02` on every emitted quad — **not** `== 0` |
| **G8** | savepoint press-zone clear of every door band and the spawn, **and** its tread region in G4 |
| **G9** | per door: `depth > R_WALK` (80, not 48) **and** non-empty standable intersection connected to the room's main component **and** non-degenerate (`len(fan_triangles) >= 2`, area floor). Subsumes the deleted `min_len` |
| **G10** | every arrival row carries an explicit `face`, including `entrance = 0` (whose value equals `[player] face` — both resolve to the same `D9(6)` const) |
| **G11** | no two room polygons overlap (SAT), naming both — a pen that crosses a wall is the likeliest hand-tracing defect, and both rooms pass C1 |
| **G12** | the two rooms' interior normals are antiparallel on every accepted door candidate |
| **G13** | `standable(room)` non-empty **and connected**; warn under 35% coverage. Subsumes minimum room width (`2·R_WALK` = 160) and the acute-spike case |
| **G14** | `quad[0] → quad[1]` **is** the door segment (assert — no gate can check it) |
| **G15** | the painted floor's canvas AABB matches the walkmesh's to within `FIT_MARGIN` |

**Deleted or demoted:** the cardinal snap · `min_len = 192` · G7's equality · G4's raw error ·
the centroid fast path · `cam.solve_z_for_canvasY` and `guide.frame_floor` (out of the call path).

---

## 6. STILL GENUINELY UNKNOWN — needs 6d, the playtest

1. ~~`R_WALK = 80` vs the repo's 48.~~ **RESOLVED 2026-07-30, in-game measured.** A purpose-built
   calibration field (id 30510, straight wall at world z=300, steep 75° camera chosen so the two
   hypotheses land 9.9 canvas-px apart) was deployed and walked into; the debug HUD read the
   clamped stop at exactly **z=220** — an inset of **80**, not 48. `cam.COLLISION_RADIUS_W` has
   been fixed to 80 to match `R_WALK`, and its comment corrected (the `bgiRad*4` basis was never
   real — `bgiRad` is a battle-return-only field, 0 on a fresh load; the old 48 traced back to the
   now-deleted room02 bench, which conflated this radius with the legacy flat-builder's
   `orgPos=(0,0,300)` offset and the retired eyeball canvas scale).
   ⚠ **Still do NOT change the remaining 48s as a drive-by** — but the list is SHORTER than this
   study first claimed, and the two bad cites are worth naming so nobody re-derives them:
   `build.py:3652` is an aspect-mismatch check with nothing to do with the radius, and
   `field_layout_probe.py:242` reads `C.COLLISION_RADIUS_W`, so the probe picked up 80 for free
   (as did `content/pathfind.py:155`). **Verified 2026-07-30, the true remaining set is exactly
   two literals** — `scene/routes.WALL_CLEARANCE_W = 48.0` (whose own comment claims it *is*
   `cam.COLLISION_RADIUS_W`, which is now false) and `imagefield.COLLISION_OUTSET = 48.0` — plus
   the layout skill's route-sweep prose, which is correct only while `routes` stays 48.
   The split has teeth: a 130u corridor measures 1820 standable cells at 48 and **0** at 80, and
   `routes` is the optimistic direction, so the behavior-tree sweeper will certify a patrol the
   engine cannot walk; `content/pathfind.py` disagrees with itself (line 104 defaults to `routes`'
   48, line 155 to `cam`'s 80). Reconciling them is its own change, with the owner — five behavior
   tests pin against 48 and need RE-MEASURING, not relaxing.
2. **Whether front-align *looks* right in-game.** The fill numbers are unambiguous and it matches
   `frame_floor`'s own defaults, but "the room reads as a room" is a human judgment. Get a screenshot
   of the first composed room before emitting a whole dungeon.
3. **The 170u depth warn floor** — anchored to ARRTEST but not measured at `R_WALK = 80`.
4. **Whether `entry_settle = "auto"` behaves on a hand-drawn polygon** at a non-template size. It
   lints and builds; the settle count has only been proven on template-shaped rooms.

---

## 7. THE LADDER

- **6a** — `floorplan.py`, the pure Qt-free core (C0-C8 + compose + G1-G15) and its fences.
- **6b** — the CLI verb `ff9mapkit floorplan <plan.json> --out DIR`: sidecar round-trip, one member
  dir per room, polygon-clipped placeholder art, `campaign.toml`. Offline-provable end to end.
- **6c** — the Workspace **Floorplan** tab on the Author rail beside Map: the chart canvas,
  `ToolStrip`, Compose through `run_job`, then `open_campaign` on the result so the composed dungeon
  lands as a live campaign and its graph is immediately visible (PLAN.md §5 call site 3). Undo is
  **doc-local** over the session snapshot (`TraceDoc`'s `_push_history` model), not shell checkpoints
  — which is what makes a door-pair edit atomic despite `_UndoRec` being single-member.
- **6d** — deploy **per room** with `tools/deploy_field.py --id N` (additive: it rmtrees only that
  one FBG scene subdir and merges `DictionaryPatch.txt` by ownership). **Never**
  `deploy_campaign --apply` — that rmtrees the whole mod folder, and this install's `FF9CustomMap`
  holds ~400 registrations from other concurrent sessions.
