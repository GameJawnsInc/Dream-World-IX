# Blender camera-view fidelity — the all-fields census (2026-07-13)

> **STATUS: THE ROOT CAUSE IS FOUND AND FIXED (add-on 0.9.26) — one universal error, not many
> edge cases.** GameJawns imported TWIN_ALTAR (a native fork of field 2301, Esto Gaza/Altar) and
> the Blender camera "only looked at a small portion of the walkmesh". The suspicion: the add-on
> was built against a small sample of fields, so compatibility might be much lower than expected.
> Instead of digging field-by-field, this census checked EVERY field offline — and the sample
> suspicion was right in an unexpected way: the projection math's invariant (validated on six
> cameras) holds on **all 741 shipping field-cameras**, but the Blender pose dropped one term of
> it, so **738/741 cameras misframed** (~7–20px typically, 40 cameras >50px). One fix repairs all
> of them: `pixel_aspect_y = 15/14` (K_VSCALE, the FF9 vertical focal scale) in
> `_apply_canvas_resolution`. The census re-run against the fixed model is the proof, and the
> script stays as a permanent regression harness for any future camera-math change.

## The method (why offline won)

The kit holds two independent implementations of the FF9 camera:

- **The oracle** — `scene/cam.py to_canvas`: projects through the RAW camera matrix, replicating
  the engine's GTE exactly. In-game proven (the entire walkmesh↔art alignment history rests on
  it). Needs no decomposition.
- **The candidate** — what Blender *displays*: `cam.decompose` (the `R_ff9 = diag(1,k,1)·R_ortho`
  invariant, k = 14/15) → `bridge.ff9_cam_to_blender` (location/rotation/lens/sensor) → a standard
  pinhole. Every stage is bpy-free, so the whole display path is computable offline.

[census.py](census.py) walks all ~674 fields (in-memory: `find_field` → `bgs.parse_cameras` +
`BgiWalkmesh.world_verts`), projects up to 240 render-frame walkmesh verts per field through both
paths, and records the px disagreement per camera plus the decompose residuals (row norms,
orthonormality error, determinant, pitch, scrolling, multicam).

## Findings

1. **The decompose invariant is universal.** 0/741 cameras violate it (row norms (1, k, 1) to
   ~1e-4, ortho_err ≤ 3e-4, det = +1, k = 0.9332–0.9335 everywhere). The "measured across 6 real
   cameras" caveat can be retired: position, rotation, and the horizontal axis were always exact
   (2301 probe: x matches the oracle to 0.1px).
2. **But the Blender camera dropped k.** FF9's vertical focal is **14/15 of the horizontal**
   (`K_VSCALE`, baked into row 1 of every matrix); a Blender camera is isotropic. Result: a
   universal vertical squash — 738/741 cameras >2px (p95), 508 >10px, 40 >50px. The >50px tail is
   the same error amplified on far-off-canvas verts (multicam fields censused against all verts,
   grand-vista cameras). NOT an edge-case family — one systematic term.
3. **The fix**: anisotropic pixels express an anisotropic focal — `render.pixel_aspect_y = 15/14`
   (`_apply_canvas_resolution`, also routed through View FF9 Camera). The camera frame now equals
   the painted canvas pixel-for-pixel. (On-screen proportions differ from the game's square-pixel
   display by the same 7% — alignment-to-art is what the add-on needs; the game bakes the squash
   into the art.)
4. **The 2301 "tiny view" itself is three-quarters REAL.** The oracle says the floor band of
   Esto Gaza/Altar occupies canvas y≈167–235 of 256 — a thin strip at the frame bottom; the rest
   of the frame is the hall's ART (walls/architecture), which a logic-side import shows as empty
   space. Plus the k-squash pushed the strip further off, plus two real import bugs found en
   route: the `canvas_h min=448` property clamp (a 512×256 field could not represent its canvas —
   fixed, 0.9.25) and the `_merge_scene` camera-wholesale-replace that dropped `entry_settle`
   (fixed in the field-entry arc, rung 6).

## The regression harness

Run from the repo root: `py studies/blender-camera-fidelity/census.py [--limit N]` → `census.csv`
plus a bucket summary. `_pinhole_px(..., pixel_aspect_y=1.0)` models the PRE-fix camera (the run
that found the bug: [census_report.txt](census_report.txt)); the default 15/14 models the shipped
add-on and should stay ~sub-2px on every field ([census_report_fixed.txt](census_report_fixed.txt)).
Any future change to `decompose` / `ff9_cam_to_blender` / the paint guide should re-run this.

## The general lesson

"Built against a small sample" fears are best answered by a census against a proven oracle, not
field-by-field debugging: every Blender/in-game round-trip costs the human a cycle, while the
kit's own in-game-proven math can grade the entire game's inventory offline in minutes. This is
the same decoder-as-oracle pattern the field-entry arc used (`scan_player_arrivals`) — when two
independent implementations of the same transform exist, diff them over the full population.
