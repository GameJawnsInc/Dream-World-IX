"""Thomas swap -- PREP STEP 0 (run once, offline, before ``build_thomas.py``): normalize the raw
third-party FBX into a form the FF9 engine's zero-conversion loose-FBX reader will render upright,
correctly scaled, and correctly facing -- with ZERO runtime rotation compensation needed.

WHY THIS STEP EXISTS (source-grounded, not a guess -- see the asset lens's ``fbx_requirements``
finding, ``studies/custom-summons/PLAN.md``): ``ModelImporter.CreateCustomModelFromFbx`` reads a
Geometry node's raw ``Vertices`` array VERBATIM with **no FBX axis/unit conversion of any kind**,
and (per the asset lens) applies a Model node's own local transform **only when the geometry is
bone-parented** -- Thomas's source FBX is fully rigid (zero Deformer/Skin/Cluster nodes), so the
engine will render his mesh using the raw ``Vertices`` array alone, completely ignoring his source
Model node's own baked ``Lcl Rotation=(-90,0,0)`` (a standard 3ds-Max-Z-up -> FBX-Y-up conversion
rotation -- confirmed by probing the raw binary FBX directly: our own ``fbx_probe.py`` found
``GlobalSettings.UpAxis=1`` (Y) declared but the Model's own Lcl Rotation is what actually performs
that conversion for ordinary FBX consumers). Any consumer that reads the file NAIVELY the way our
engine does (raw geometry, no Model transform) would render Thomas lying on his side / rotated 90
degrees off -- a real defect, not a hypothetical one.

THE FIX: import in Blender (which DOES apply the Model transform + FBX unit/axis metadata, exactly
like any standard 3D tool), **bake it into the raw vertex data** (``transform_apply``), recenter the
pivot to base-center (X/Z centered, Y=0 at the wheels -- so the SFX manifest's ``Scaling`` curve
grows him from the ground up, matching how the ``CasterPosition``-anchored ``Movement`` curve expects
a model's local origin to sit at its feet), and re-export with Blender's DEFAULT FBX axis mapping
(``axis_up='Y', axis_forward='-Z'`` -- the well-known, purpose-built Blender<->Unity/game-engine
convention). Because that bake+export writes the FINAL raw numbers straight into the file (no Model
node transform left over -- confirmed post-export: the exported Model node's own Properties70 has NO
Lcl Translation/Rotation/Scaling at all), whatever the engine reads verbatim is *exactly* what
Blender's own viewport shows: upright, correctly proportioned.

ORIENTATION -- reasoned, not copied from rung 7's (0,180,180) player-baseline: rung 7's asset was a
kit-EXPORTED PSX-heritage FF9 battle model, which needs that specific compensating rotation under the
SFX path's raw-euler-no-compensation rule (``ROTATION-BASELINE LAW``, PLAN.md rung 7). Thomas is a
freshly-normalized THIRD-PARTY asset with no such PSX inversion baked in -- his correct facing is
whatever we choose to bake into the export. A one-vertex marker probe (documented in
``studies/custom-summons/thomas-swap/README.md`` "Axis verification") empirically confirmed: Blender's
own front-facing convention (-Y, the direction Thomas's face points in the un-rotated import, verified
by the render pass below) maps, under these EXACT export settings, to **+Z in the raw exported file**
-- so the manifest's Rotation curve can stay a flat (0,0) with no compensating spin; see the build
script for the reasoning trail.

Requires Blender (tested on 5.1, headless). Reads/writes ONLY under C:/gd/SCRATCH/thomas/ (never this
repo) -- the raw source FBX + PNG stay outside the repo per CLAUDE.md's provenance rule; this SCRIPT is
the committable, reproducible record of the normalization, not the asset itself.

Usage:
    "path/to/blender.exe" --background --python blender_normalize.py -- <in_fbx> <out_dir>

e.g. (this build's own invocation):
    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --python \
        studies/custom-summons/thomas-swap/blender_normalize.py -- \
        "C:/gd/SCRATCH/thomas/Thomas the Tank Engine.fbx" "C:/gd/SCRATCH/thomas/blender_out"

Writes to <out_dir>: ``thomas_normalized.fbx`` (the file ``build_thomas.py`` deploys, binary-copied --
never text-decoded, since ``ff9mapkit``'s own ``stage_mint`` fbx= path is ASCII-only and would corrupt
a binary FBX) + five inspection renders (``view_front/back/side/34/top.png``) for the offline eye.
Does NOT copy a texture next to the output -- the exported FBX's RelativeFilename is deliberately
stripped to a bare ``Thomas_d.png`` (``path_mode="STRIP"``) so ``build_thomas.py`` can stage the
ORIGINAL ``C:/gd/SCRATCH/thomas/Thomas_d.png`` unmodified, unresized, unrecompressed.
"""
import bpy
import sys
import os
import math
import mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
in_fbx, out_dir = argv[0], argv[1]
os.makedirs(out_dir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)

try:
    bpy.ops.preferences.addon_enable(module="io_scene_fbx")
except Exception as e:
    print("addon_enable io_scene_fbx:", e)

bpy.ops.import_scene.fbx(filepath=in_fbx)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
print(f"IMPORTED {len(meshes)} mesh object(s): {[o.name for o in meshes]}")
for o in meshes:
    print(f"  {o.name}: loc={tuple(o.location)} rot_euler={tuple(o.rotation_euler)} scale={tuple(o.scale)}")
    print(f"    materials: {[s.material.name if s.material else None for s in o.material_slots]}")
for img in bpy.data.images:
    print(f"IMAGE: {img.name}  size={tuple(img.size)}  filepath={img.filepath!r}  packed={bool(img.packed_file)}")

# --- bake the Model node's transform (Lcl Rotation etc.) into raw vertex data -------------------
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def world_bbox(objs):
    mins = [math.inf] * 3
    maxs = [-math.inf] * 3
    for o in objs:
        for corner in o.bound_box:
            wc = o.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                mins[i] = min(mins[i], wc[i])
                maxs[i] = max(maxs[i], wc[i])
    return mins, maxs


mins, maxs = world_bbox(meshes)
dims = [maxs[i] - mins[i] for i in range(3)]
print(f"POST-APPLY bbox (Blender XYZ, Z=up) min={mins} max={maxs} dims={dims}")

# --- recenter pivot to base-center (X/Y centered, Z=0 at the wheels) ----------------------------
cx = (mins[0] + maxs[0]) / 2.0
cy = (mins[1] + maxs[1]) / 2.0
base_z = mins[2]
shift = mathutils.Vector((-cx, -cy, -base_z))
for o in meshes:
    o.data.transform(mathutils.Matrix.Translation(shift))
    o.data.update()
    for corner_i in range(8):
        pass  # bound_box refresh is lazy/stale in background mode -- verified via the raw exported
              # file instead (fbx_probe.py), not this cached property; see README "Axis verification"

# --- lighting + camera + inspection renders (the offline eye) -----------------------------------
world = bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.15, 0.15, 0.17, 1.0)

sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN"))
sun.data.energy = 3.0
bpy.context.collection.objects.link(sun)
sun.rotation_euler = (math.radians(55), 0, math.radians(35))

fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", type="SUN"))
fill.data.energy = 1.2
bpy.context.collection.objects.link(fill)
fill.rotation_euler = (math.radians(120), 0, math.radians(-60))

cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam

center = mathutils.Vector(((mins[0] + maxs[0]) / 2, (mins[1] + maxs[1]) / 2, 0.0))
radius = max(dims) or 1.0

scene = bpy.context.scene
scene.render.resolution_x = 512
scene.render.resolution_y = 512
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"


def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def shoot(name, cam_pos):
    cam.location = center + mathutils.Vector(cam_pos)
    look_at(cam, center)
    cam_data.lens = 50
    scene.render.filepath = os.path.join(out_dir, name)
    bpy.ops.render.render(write_still=True)
    print(f"RENDERED {name} from cam@{tuple(cam.location)}")


d = radius * 1.8
shoot("view_front.png", (0, -d, radius * 0.35))
shoot("view_back.png", (0, d, radius * 0.35))
shoot("view_side.png", (d, 0, radius * 0.35))
shoot("view_34.png", (d * 0.7, -d * 0.7, radius * 0.55))
shoot("view_top.png", (0.001, 0.001, d * 1.4))

# --- re-export: Blender's DEFAULT Unity-safe axis mapping, transform baked, texture path STRIPPED
out_fbx = os.path.join(out_dir, "thomas_normalized.fbx")
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.ops.export_scene.fbx(
    filepath=out_fbx,
    use_selection=True,
    apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_ALL",
    axis_forward="-Z",
    axis_up="Y",
    global_scale=1.0,
    bake_space_transform=True,
    object_types={"MESH"},
    use_mesh_modifiers=True,
    path_mode="STRIP",      # bare "Thomas_d.png", no subfolder -- build_thomas.py stages the ORIGINAL PNG beside it
    embed_textures=False,
)
print(f"EXPORTED {out_fbx}")
print("Read it back with fbx_probe.py (or build_thomas.py's own --probe) to confirm the raw, "
      "zero-conversion bounding box the ENGINE will actually see.")
