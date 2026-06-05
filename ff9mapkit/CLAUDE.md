
### 2026-06-04 — Session 18 (cont) — Blender editable-fork reshape PARITY (offline; awaits Blender+in-game check)

**Closed the gap flagged above: the Blender add-on now round-trips an `import --editable` fork identically to the CLI** (so the visual loop matches the engine-proven CLI loop). All offline; the bpy UI + final in-game alignment are the human's per Hard-Constraint §2.

**Done (add-on → v0.6.0; commit `62a8de2`):**
- **Import** (`FF9MK_OT_import_field`): loads the per-depth `layer_*.png` (with occlusion + light/shadow **shaders**) as the camera backdrop + the field's `[[layers]]`; sets `p.editable_fork` (and `Setup FF9 Scene` resets it + `borrow_bg`). `has_art` now true for layers (so the camera view-offset aligns, not the bare-field reframe).
- **Export** (new editable branch in `FF9MK_OT_export_field`): **preserves the exact extracted `camera.bgx`** (re-posing would bake in the import's view-offset D → corrupt camera), re-writes `walkmesh.obj` from the reshaped mesh, emits `[walkmesh] obj + frame="world"` (+ `links = "walkmesh.links.toml"` when the multi-floor sidecar is present, so seams reconcile) with **NO `character_offset`** (forked real field is already in the engine frame).
- **bpy-free + tested:** `bridge.layers_to_toml` now carries `shader`; new `bridge.editable_field_toml` mirrors the CLI `import --editable` output. UI banner for editable forks. `blender/tests/test_editable_fork.py` (4 tests: shader formatter, editable-toml structure multi/single-floor, full build dry-run with layers+shaders+world-frame asserting the built `.bgx` keeps the additive shader + no char offset). **153 tests pass**; vendor drift guard clean; all add-on modules `py_compile`.
- Docs: `blender/README.md` "Fork an existing FF9 field (Import)" section (BG-borrow vs editable; reshape leaves seam edges, repaint per-layer).

**Why each fix (engine facts):** `frame="world"` → verts verbatim, no character shift (`build.resolve_walkmesh`); the obj-branch `character_offset` default is 0, so the from-scratch novel-room path still explicitly sets 298 (unchanged) while forks omit it; multi-floor obj rebuilds neighbors by index (disjoint vertex sets) so the `links` sidecar is required to keep cross-floor seams (the exact thing proven in-game this session).

**Next:** user verifies in Blender 5.x — install `blender/dist/ff9mapkit_blender-0.6.0.zip` → `ff9mapkit import <multi-floor field> --editable --out F` → Blender **Import Field** (F) → reshape a floor interior → **Export Field** → `ff9mapkit build` → deploy (`tools/deploy_field.py`) → walk it (reshaped + still connected). Then the Blender + CLI loops are at full parity. Remaining kit options: collision-radius edge warning; v3 walkmesh (`walkmesh verify` CLI, Blender seam viz).
