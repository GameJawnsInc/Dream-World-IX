# Camera math — the projection invariant, scale-1 canvas, yaw

**Canonical code:** `ff9mapkit/ff9mapkit/scene/cam.py` — `project`, `to_canvas`, `solve_z_for_canvasY`,
`decompose`, `synth_r_t`, `rot_x`/`rot_y`, `yaw_deg`, `compute_offset`, `COLLISION_RADIUS_W`.
**Canonical prose:** `ff9mapkit/docs/TECHNICAL.md` §2–§4; memory `[[project-ff9-camera-math]]` (the full
derivation, the `.bgx` CAMERA field map, the probe history). Formulas below are quoted verbatim from those
sources — if you need more than these, read the memory file, don't re-derive.

## THE invariant (the whole secret)

Quoted from memory `project-ff9-camera-math`:

> `R_ff9 = diag(1, k, 1) * R_ortho` where R_ortho is a proper orthonormal rotation and
> **k = 14/15 = 0.93333… is a GLOBAL CONSTANT** (vertical-focal scale baked into row 1, because the
> GTE has a single projection distance H for both axes — row1 carries the aspect correction).

- decompose: divide r/4096 rows by (1,k,1) → R_ortho (orthonormal); recover C from t.
- synthesize: `R_ff9 = diag(1,k,1)*R_ortho`, `r[i][j]=round(R_ff9*4096)`, `t=-R_ff9*(F*C)`.

Clean equivalent pinhole (validated to ~1e-13), with `F = diag(1,-1,1)`:

> `R_view = F*R_ff9*F`, `cs = R_view*(P - C)`, `screen = cs.xy * H/|cs.z| + centerOffset`,
> with **`t = -R_ff9*(F*C)`  <=>  `C = -F*R_ff9^{-1}*t`**.

## The canvas map — EXACT, scale-1

Supersedes the old sx=0.926/sy=0.889 eyeball fit:

```
canvasX = rawProj.x + centerOffset.x + range.w/2   # rawProj = project(P,cam) with offset (0,0)
canvasY = range.h/2 + centerOffset.y - rawProj.y   # scale 1.0 BOTH axes, no fudge
```

Kit-authored (novel) cameras always have `centerOffset [0,0]`, where this reduces to the historical
offset-less form that reproduces an in-engine projection probe to **0.0005 px**; EXACT at any pitch.
REAL imported cameras carry a nonzero GTE centerOffset that shifts the whole canvas map — proven on
donor `fbg_n11_ldbm_map158_lb_plz_0` (centerOffset [26, 400]; regression in
`ff9mapkit/tests/test_cameras.py::test_map158_center_offset_regression`). `cam.to_canvas(P, cam)`
is the implementation; `solve_z_for_canvasY` is the inverse (painted floor row → world z).

### The inverse is CLOSED FORM, and its pole is the trap

`canvasY(z)` along a world line is Möbius in z, so `solve_z_for_canvasY` solves it directly —
`z = (a*E - A*H)/(B*H - a*G)`, coefficients read out of `project` (see the block comment at
`cam.py:203`). **Never re-derive it by search.** `project` divides by `num = abs(res.z)`, so past the
projection pole at `res.z = 0` the same canvas row is re-produced MIRRORED by points BEHIND the
camera; any bracket that spans the pole is unsound. That is a real, paid-for bug, not a hypothetical:
the former bisection over `[-30000, +30000]` returned `None` for rows with valid roots at pitch ≤ ~30
(so `ff9mapkit new --pitch 15` silently scaffolded a hard-coded quad matching no camera) and lost
112 of 886 in-front samples across the six real donor cameras. Two corollaries:

- **A canvas coordinate alone cannot tell you a point is in front of the camera** — the mirror makes
  a behind-camera point land at an ordinary-looking row. `project(P, cam)[2]` (SIGNED `res.z`) is the
  only thing that can see it; check it whenever the answer feeds geometry.
- Use `cam.canvas_row_z` (returns `(z, reason)`) when you need to TELL the user why a row has no
  floor — `guide.frame_floor` quotes it. `horizon_canvas_y` is the analytic asymptote; do not probe
  it with a large z (that rides the same mirror, and 1e7 is still 6.5 rows out on the map158 donor).

Engine offsets (what the GTE actually receives — `FieldMap.cs`, quoted from the memory):
`offX = centerOffset.x + w/2 - HalfFieldWidth`, `offY = -centerOffset.y - h/2 + HalfFieldHeight`
(HalfFieldWidth=160, HalfFieldHeight=112). Actor depth = `result.z/4 + depthOffset`.

## Character ground offset = 0

Engine-measured (probe at two pitches): the character model renders through the SAME GTE as the
floor/walkmesh, so char == floor projection. The legacy `org=(0,0,300)` + `CHARACTER_GROUND_OFFSET_Z=298`
were a near-cancelling double-count — new walkmeshes use `[walkmesh] frame="world"` (org=0, NO offset;
walkmesh in true world coords = painted floor). The 298 + legacy quad path survive only for back-compat
(the byte-golden hut ships `org=(0,0,300)` with art aligned to it — don't flip old rooms without
re-aligning their art).

## Yaw

Quoted verbatim (memory `project-ff9-camera-math` — the GTE applies R AFTER the y-flip F, so
post-multiply by −yaw; pre-multiplying flings the floor off-screen):

```
R_ortho = rot_x(pitch) · rot_y(-yaw)      # CORRECT (origin stays centred at every yaw)
C       = rot_y(yaw) · (0, D·sinθ, -D·cosθ)   # orbit the position about the origin
```

Recover yaw from any camera: `cam.yaw_deg` = `atan2(-R_ortho[0][2], R_ortho[0][0])`.

**Control direction** (movement must rotate with the camera — the TWIST / `SetControlDirection 0x67`):
`value = round(yaw/360·256) − 1` (front-facing = −1). `build.resolve_control_value` auto-derives it from
the resolved camera's `yaw_deg`; `[camera] control_direction` overrides. `to_canvas` and the walkmesh go
through the SAME yawed projection, so they stay aligned at any yaw — only movement needs the twist.

## Multi-camera

Purely SCRIPT-driven: `SETCAM 0x7E` (SetFieldCamera) cuts cameras; no automatic per-region switch. The
`.bgx` carries N CAMERA blocks + per-overlay `CameraId`; each camera needs its OWN SetControlDirection.
field.toml: `[[camera]]` + `[[layers]] camera=N` + `[[camera_zone]]`. Byte-exact real-game pattern
(flag-gated forward/reverse region pair) → memory `[[project-ff9-camera-math]]` "Multi-camera switch zones".

## Dead ends (proven — do not re-explore)

- Per-pitch `sx/sy` canvas scale: the map is exact scale-1; the "back-edge drift" was the character
  collision radius (`COLLISION_RADIUS_W = 80`, in-game confirmed 2026-07-30), not a map error.
- The FieldCreator editor's 5-point camera anchor on a flat floor: rank-deficient (all y=0 zeroes the
  y-columns) — mathematically degenerate. Synthesize with `synth_r_t` instead.
