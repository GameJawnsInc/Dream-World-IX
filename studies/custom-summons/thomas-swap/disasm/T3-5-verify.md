# T3-5 adversarial verification — "the exporter is `model-gltf` for summons"

**Verdict: PARTIAL** (prior confidence "proven" is overstated; downgrade to *plausible with a required
refactor*). Independently re-derived from the kit source, not from the cited doc.

## Claim under test
The summon exporter reuses `models/gltf.py` emission, `models/_gltf_io.py` (buffer/writer), and the coord
helpers **wholesale**, adding **only** a motion decoder + a Model-struct adapter, and emits the exact `.glb`
the add-on's Import Model opens. Parenthetical: *"only those two call sites (`extract.read_model`,
`_select_anim_keys`) are p0data-coupled."*

## What reproduces (CONFIRMED)
- **Geometry/skeleton feed is already factorable.** `export_gltf(..., _model=<struct>)` (`gltf.py:167-168`)
  skips `extract.read_model` and consumes a caller-supplied Model struct. The adapter path the claim posits
  exists as a hook today.
- **Buffer/writer reuse is real.** `GltfBuffer`, `write_glb`, `decode_accessor` (`_gltf_io.py:21,62,117`) are
  coordinate-independent binary machinery — reusable unchanged.
- **Coord helpers are pure math, reusable.** `_cpos/_cnrm/_cquat/_sign_continuous/_mat4_colmajor`
  (`gltf.py:33-64`). (Caveat: negate-Y being *correct* for PSX summon space is PLAUSIBLE-not-proven — T3 doc
  §2.5 gap #6 concedes "verify upright, iterate if not." That's a convention question, not a code-reuse one.)
- **The clip DATA SHAPE the animation loop consumes matches a motion decoder's output.**
  `read_clip` returns `{"bones": {path: {"rot":[(t,q)], "pos":[(t,p)], "scale":[(t,s)]}}}`
  (`_gltf_io.py:188-227`), and the loop at `gltf.py:332-369` walks exactly `clip["bones"].items()` →
  `ch.get("rot"/"pos"/"scale")`. A `summons/motion.py` emitting that shape flows through the per-channel
  emission (332-369) unchanged. **True.**
- **Output opens in Blender.** Import Model calls the generic `bpy.ops.import_scene.gltf`
  (`blender/ff9mapkit_blender/model_ops.py:34` — the claim cites :22, the class line; the actual call is :34).
  Any conformant `.glb` from the same writer opens. **True (mechanism).**

## What does NOT reproduce (the overstatements)
1. **There is a THIRD p0data-coupled call site, and it is INSIDE the cited emission body.**
   `env5 = ...load(p0data5.bin); _select_anim_keys(...)` at `gltf.py:319-323` is the first pair the claim
   admits — but the loop then calls **`_gltf_io.read_clip(env5, folder, key)` at `gltf.py:328`**, which reads
   `animations/{geo_id}/{anim_key}.anim` **from p0data5** (`_gltf_io.py:188-205`). Line 328 sits within the
   claim's own cited emission range (324-382). So the parenthetical "only those two call sites are
   p0data-coupled" is **false** — there are three, and the third is in the emission loop.
2. **`export_gltf` cannot be reused "wholesale" / called as-is for a summon.** Even feeding a struct via
   `_model`, if any clips are requested (which a summon's motion requires) the function unconditionally loads
   p0data5 (322) and calls `read_clip(env5, summon_geo_id, key)` (328) — the summon's ids do not exist in
   p0data5, so it returns None and emits zero animation. To get summon motion you MUST edit the loop's clip
   *source* (bypass 319-323, replace the `read_clip` fetch at 328 with a pre-decoded clip). The T3 doc §2.1
   itself concedes this: *"`export_gltf` is 90% reusable but is coupled … the clean move is to factor its
   emission body into `emit_model_gltf(model, clips, buf, out)`."* That factoring edit is NOT captured by
   "adding **only** a motion decoder + an adapter."
3. **Minor:** `bone_labels.labels_for(prefab_id=None, geo=None)` (`gltf.py:173-175`) is prefab-family coupling
   the summon path must sidestep via `bone_labels=False`; cosmetic, but another "not wholesale" edge.

## Why PARTIAL, not REFUTED
The strict refutation bar ("a coupling that **cannot be factored** without rewriting emission") is **not** met:
`read_clip` CAN be factored by feeding pre-decoded clips, and the per-channel emission *math* (332-369) stays
byte-for-byte the same — an extract-and-parametrize refactor, not a rewrite. The engineering direction (small
adapter + motion decoder over reused emission/writer/coord machinery; output opens in Blender) is **sound and
reproducible**, and this forward path involves **no engine build** (pure offline Python + Blender's stock glTF
importer), so no playtest/DLL cost is at risk from it.

## Correction to fold into T3
- Drop "wholesale" / "adding **only**": the exporter requires a refactor of `export_gltf` (extract the emit
  body into `emit_model_gltf(model, clips, buf, out)`, parametrize the clip source, bypass the p0data5 load and
  `bone_labels`). New code = motion decoder + adapter **+ this factoring**.
- Fix the p0data-coupling count: **three** sites, not two — `read_model` (168), the p0data5 load +
  `_select_anim_keys` (322-323), and **`read_clip` (328), which is inside the emission loop**.
- Keep as CONFIRMED: the clip-shape match (the decoder's `{bones:{path:{rot,pos,scale}}}` flows through
  332-369 unchanged), the buffer/writer/coord-helper reuse, and that the emitted `.glb` opens via
  `import_scene.gltf`.
