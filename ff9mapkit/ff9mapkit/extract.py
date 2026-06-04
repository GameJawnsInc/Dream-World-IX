#!/usr/bin/env python3
"""Import support: pull a REAL FF9 field's scene data out of the game's p0data bundles, OFFLINE.

This is the data-gathering half of `ff9mapkit import` ("fork any field as a base"). It reads a
field's native assets straight from StreamingAssets/p0data*.bin (UnityRaw 5.2.3 assetbundles) with
no in-game step, and hands them to the kit's existing parsers:

    <fbg>.bgs.bytes  -> scene.bgs.parse_cameras   (the field's camera(s))
    <fbg>.bgi.bytes  -> scene.bgi.BgiWalkmesh     (walkmesh + player start)
    atlas.png        -> the packed background art (only pulled when want_atlas=True)

UnityPy is imported lazily: only `extract`/`import` need it, the core kit stays pure-stdlib.

Proven against GRGR in the offline spike (2026-06-04): the decoded camera matched the engine's own
.bgx export byte-for-byte.
"""
from __future__ import annotations

import glob
import json
import os
import re
from pathlib import Path

from . import config
from .scene import bgs, bgi, cam


def _unitypy():
    try:
        import UnityPy  # noqa: PLC0415
        return UnityPy
    except ImportError as e:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "extraction needs UnityPy (reads FF9's p0data assetbundles). Install it:\n"
            "    py -m pip install UnityPy"
        ) from e


def _raw_bytes(data):
    """Raw bytes of a TextAsset across UnityPy versions."""
    for attr in ("m_Script", "script"):
        v = getattr(data, attr, None)
        if isinstance(v, bytes):
            return v
        if isinstance(v, str):
            return v.encode("utf-8", "surrogateescape")
    return None


_FBG_RE = re.compile(r"^fbg_n(\d+)_(.+)$", re.I)


def parse_fbg_folder(folder: str):
    """('fbg_n21_grgr_map420_gr_cen_0') -> (area:int=21, mapid:str='GRGR_MAP420_GR_CEN_0').

    `mapid` is the DictionaryPatch BG id (the part after `FBG_N<area>_`); the engine rebuilds
    `FBG_N<area>_<mapid>` for the BG lookup (proven Session-4 BG-borrow)."""
    m = _FBG_RE.match(folder.strip().lower())
    if not m:
        raise ValueError(f"not an FBG field folder: {folder!r}")
    return int(m.group(1)), m.group(2).upper()


def _streaming_assets(game=None) -> Path:
    return config.find_game_path(game) / "StreamingAssets"


def _bundles(game=None):
    return sorted(glob.glob(str(_streaming_assets(game) / "p0data*.bin")))


# ---- field -> bundle index (built once, cached; so lookups don't rescan ~50 bundles) ----
INDEX_NAME = ".ff9mapkit-field-index.json"


def _index_path(game=None) -> Path:
    return _streaming_assets(game) / INDEX_NAME


def build_field_index(game=None, *, force=False, verbose=True) -> dict:
    """Map every field folder -> its p0data bundle. Cached next to the bundles; first build scans
    them all (~1-2 min), then it's instant. `force=True` rebuilds."""
    UnityPy = _unitypy()
    idx = _index_path(game)
    if idx.exists() and not force:
        try:
            return json.loads(idx.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    index = {}
    bundles = _bundles(game)
    for i, path in enumerate(bundles):
        if verbose:
            print(f"  indexing {i + 1}/{len(bundles)} {os.path.basename(path)} ...", flush=True)
        try:
            env = UnityPy.load(path)
        except Exception:
            continue
        bn = os.path.basename(path)
        for k in env.container:
            m = re.search(r"fieldmaps/([^/]+)/", k.lower())
            if m:
                index.setdefault(m.group(1), bn)
    try:
        idx.write_text(json.dumps(index, indent=0), encoding="utf-8")
    except OSError:
        pass
    if verbose:
        print(f"  indexed {len(index)} fields -> {idx}")
    return index


def resolve_field(field: str, game=None):
    """(folder, bundle) for a field name (full FBG, bare mapid, or unique substring) via the index."""
    want = re.sub(r"^fbg_n\d+_", "", field.strip().lower())
    index = build_field_index(game, verbose=True)
    if field.strip().lower() in index:
        f = field.strip().lower()
        return f, index[f]
    hits = [f for f in index if want in f]
    if not hits:
        raise FileNotFoundError(f"no field matches {field!r}. Try: ff9mapkit list-fields {want}")
    if len(hits) > 1:
        raise ValueError(f"{field!r} matches {len(hits)} fields; be more specific. e.g. {sorted(hits)[:8]}")
    return hits[0], index[hits[0]]


def list_fields(pattern=None, game=None):
    """Sorted (folder, area, mapid) for all fields (optionally filtered by substring)."""
    index = build_field_index(game, verbose=False)
    pat = pattern.lower() if pattern else None
    out = []
    for folder in sorted(index):
        if pat and pat not in folder:
            continue
        try:
            area, mapid = parse_fbg_folder(folder)
        except ValueError:
            continue
        out.append((folder, area, mapid))
    return out


def find_field(field: str, game=None, bundle: str | None = None):
    """Locate a field's bundle + container paths. Returns (bundle_path, folder, {role: key}, env).

    Uses the cached field index unless `bundle` (e.g. 'p0data141.bin') is given to short-circuit it."""
    UnityPy = _unitypy()
    sa = _streaming_assets(game)
    folder = None
    if not bundle:
        folder, bundle = resolve_field(field, game)
    env = UnityPy.load(str(sa / bundle))
    if folder is None:                                  # explicit bundle: match within it
        want = re.sub(r"^fbg_n\d+_", "", field.strip().lower())
        folders = {m.group(1) for k in env.container
                   if (m := re.search(r"fieldmaps/([^/]+)/", k.lower()))}
        hits = [f for f in folders if want in f]
        if not hits:
            raise FileNotFoundError(f"field {field!r} not in {bundle}")
        folder = field.strip().lower() if field.strip().lower() in hits else hits[0]
    roles = {}
    for k in env.container:
        kl = k.lower()
        if f"fieldmaps/{folder}/" not in kl:
            continue
        base = kl.rsplit("/", 1)[-1]
        if base == "atlas.png":
            roles["atlas"] = k
        elif base.endswith(".bgi.bytes"):
            roles["bgi"] = k
        elif base.endswith(".bgs.bytes") and not re.search(r"_(es|fr|gr|it|jp)\.bgs", base):
            roles["bgs"] = k                            # default (us/en) scene
    return str(sa / bundle), folder, roles, env


def extract_field(field: str, out_dir, *, game=None, bundle=None, want_atlas=False) -> dict:
    """Extract a real field's camera + walkmesh (+ optional atlas) to `out_dir`; return metadata."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path, folder, roles, env = find_field(field, game=game, bundle=bundle)
    if "bgs" not in roles or "bgi" not in roles:
        raise FileNotFoundError(f"{folder}: missing .bgs/.bgi (have {sorted(roles)})")

    objs = {k: v for k, v in env.container.items()}
    bgs_bytes = _raw_bytes(objs[roles["bgs"]].read())
    bgi_bytes = _raw_bytes(objs[roles["bgi"]].read())

    cameras = bgs.parse_cameras(bgs_bytes)
    wm = bgi.BgiWalkmesh.from_bytes(bgi_bytes)
    area, mapid = parse_fbg_folder(folder)

    # write the camera as a borrowable .bgx (reference + drives movement/scroll) + the raw walkmesh
    (out / "camera.bgx").write_text("".join(cam.format_bgx_camera(c) for c in cameras), encoding="utf-8")
    (out / "walkmesh.bgi").write_bytes(bgi_bytes)
    if want_atlas and "atlas" in roles:
        try:
            objs[roles["atlas"]].read().image.save(out / "atlas.png")
        except Exception:
            pass

    c0 = cameras[0]
    d = cam.decompose(c0)
    scrolling = c0.range[0] > 384 or c0.range[1] > 448
    # real .bgi verts are corner-origin per FLOOR; world_vert = vert + orgPos + floor.org puts the
    # whole (multi-floor) walkmesh in the world (camera) frame, on the painted art + the engine frame.
    wv = wm.world_verts()
    wx = [p[0] for p in wv]
    wz = [p[2] for p in wv]
    ox, oz = wm.orgPos.x, wm.orgPos.z         # header offset (for the charPos spawn guesses below)
    # spawn: charPos is stored per-field in EITHER the corner frame or already world, and is unreliable
    # for multi-floor fields. Prefer it only if it lands on the walkmesh AND on-camera; else spawn at
    # the centre of the ON-CAMERA walkmesh (a real walkmesh often runs far past the screen into gated
    # tunnels, so the player should appear on-screen).
    bx0, bx1, bz0, bz1 = min(wx), max(wx), min(wz), max(wz)
    rw, rh = c0.range
    def _inb(px, pz):
        return bx0 <= px <= bx1 and bz0 <= pz <= bz1
    def _oncam(px, pz):
        cx, cy = cam.to_canvas((px, 0.0, pz), c0)
        return 0 <= cx <= rw and 0 <= cy <= rh
    _cp = [(wm.charPos.x + ox, wm.charPos.z + oz), (wm.charPos.x, wm.charPos.z)]
    _oncam_verts = [(px, pz) for px, pz in zip(wx, wz) if _oncam(px, pz)]
    _spawn = next((p for p in _cp if _inb(*p) and _oncam(*p)), None)
    if _spawn is None and _oncam_verts:                       # centre of the visible walkmesh
        mcx = sum(p[0] for p in _oncam_verts) / len(_oncam_verts)
        mcz = sum(p[1] for p in _oncam_verts) / len(_oncam_verts)
        _spawn = min(_oncam_verts, key=lambda p: (p[0] - mcx) ** 2 + (p[1] - mcz) ** 2)
    if _spawn is None:                                        # no on-camera verts: in-bounds / centroid
        _spawn = next((p for p in _cp if _inb(*p)), (sum(wx) / len(wx), sum(wz) / len(wz)))
    _spawn = [round(_spawn[0]), round(_spawn[1])]
    meta = {
        "field": folder,
        "bundle": os.path.basename(path),
        "area": area,
        "mapid": mapid,
        "cameras": len(cameras),
        "camera": {
            "pitch_deg": round(cam.pitch_deg(c0), 2),
            "yaw_deg": round(cam.yaw_deg(c0), 2),
            "fov_deg": round(d["fov_x_deg"], 2) if d["fov_x_deg"] else None,
            "range": list(c0.range),
            "proj": c0.proj,
        },
        "scrolling": scrolling,
        "frame_offset": [wm.orgPos.x, wm.orgPos.y, wm.orgPos.z],   # header base (+ per-floor floor.org)
        "player_start": _spawn,
        "walkmesh_bounds": {     # WORLD frame (vert + orgPos + floor.org) = where content goes
            "x": [round(min(wx)), round(max(wx))],
            "z": [round(min(wz)), round(max(wz))],
            "verts": len(wm.verts),
            "tris": len(wm.tris),
        },
        "out": str(out),
    }
    return meta


def field_art_dir(field: str, game=None):
    """The folder where Memoria's `[Export] Field=1` dumped this field's per-overlay PNGs, or None
    if it hasn't been exported in-game yet (StreamingAssets/FieldMaps/<FBG>/Overlay*.png)."""
    folder, _ = resolve_field(field, game)
    d = config.find_game_path(game) / "StreamingAssets" / "FieldMaps" / folder.upper()
    return d if (d / "Overlay0.png").is_file() else None


def compose_background(field: str, out_path, *, game=None, bundle=None, upscale=4,
                       draw_footprint=True):
    """Composite the field's OPAQUE base art into one background PNG, for the Blender backdrop.

    Uses Memoria's engine-exported per-overlay PNGs (correct tile assembly) placed by the .bgs
    overlay positions/depths; skips additive/subtractive light+shadow overlays (the "splotches").
    When `draw_footprint` (default), also draws the walkable footprint -- the .bgi tris projected by
    the EXACT GTE->canvas map (cam.to_canvas), with NO offset: the engine projects the raw walkmesh
    frame directly, so this lands exactly where the player walks in-game. The walkmesh may extend
    past the canvas edges (tunnels) -- that's correct, not a misalignment. Returns (w, h) or None
    if the field hasn't been exported in-game yet."""
    art = field_art_dir(field, game)
    if art is None:
        return None
    from PIL import Image, ImageDraw  # noqa: PLC0415 - only the art path needs PIL
    _, _, roles, env = find_field(field, game=game, bundle=bundle)
    bgs_bytes = _raw_bytes(env.container[roles["bgs"]].read())
    h, overlays = bgs.parse_overlays(bgs_bytes)
    bgs.resolve_sprites(bgs_bytes, overlays, 2048, 40)        # atlas params irrelevant for positions
    sOrgX, sOrgY = h.bounds[2], h.bounds[3]
    c0 = bgs.parse_cameras(bgs_bytes)[0]
    W, H = c0.range[0] * upscale, c0.range[1] * upscale
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    opaque = [(i, o) for i, o in enumerate(overlays) if o.sprites and o.sprites[0].trans == 0]
    opaque.sort(key=lambda io: -(io[1].curZ + io[1].orgZ))    # back (high depth) -> front
    for i, o in opaque:
        png = art / f"Overlay{i}.png"
        if not png.is_file():
            continue
        im = Image.open(png).convert("RGBA")
        mnX = min(s.offX for s in o.sprites)
        mnY = min(s.offY for s in o.sprites)
        canvas.alpha_composite(im, ((sOrgX + o.orgX + mnX) * upscale, (sOrgY + o.orgY + mnY) * upscale))

    if draw_footprint and "bgi" in roles:
        wm = bgi.BgiWalkmesh.from_bytes(_raw_bytes(env.container[roles["bgi"]].read()))
        wv = wm.world_verts()                          # vert + orgPos + per-floor floor.org
        draw = ImageDraw.Draw(canvas, "RGBA")
        for t in wm.tris:
            pts = []
            for vi in t.vtx:
                cx, cy = cam.to_canvas(wv[vi], c0)      # exact GTE projection, world frame
                pts.append((cx * upscale, cy * upscale))
            draw.polygon(pts, fill=(90, 180, 255, 45), outline=(120, 225, 255, 160))
    canvas.save(out_path)
    return (W, H)


def extract_layers(field: str, out_dir, *, game=None, bundle=None, upscale=4, opaque_only=True):
    """Per-overlay art layers (depth-grouped) for an EDITABLE custom-scene fork that PRESERVES
    occlusion -- the inverse of `compose_background`'s flat merge.

    Groups the field's overlays by DEPTH and writes one transparent full-canvas PNG per distinct
    depth, returning the `[[layers]]` list ({image, z}) for a custom scene. The engine then redraws
    the depth-ordered scene, so the 3D player is occluded by / occludes each layer exactly like the
    real field (smaller z = nearer the camera = drawn in front). Depth + position follow Memoria's
    OWN .bgx exporter (BGSCENE_DEF.cs:606):  z = scene.orgZ + overlay.orgZ + min(sprite.depth),
    position = scene.org{X,Y} + overlay.org{X,Y} + min(sprite.off{X,Y}) -- baked into each full-canvas
    PNG so the kit layer is just position [0,0], size = range.

    Returns None if the field hasn't been `[Export] Field=1`'d in-game yet (no per-overlay PNGs on
    disk). `opaque_only` (default) skips additive/subtractive light+shadow overlays (trans != 0) --
    those need blend shaders (a later pass); the opaque overlays carry the structural occlusion.
    """
    art = field_art_dir(field, game)
    if art is None:
        return None
    from PIL import Image  # noqa: PLC0415 - only the art path needs PIL
    _, _, roles, env = find_field(field, game=game, bundle=bundle)
    bgs_bytes = _raw_bytes(env.container[roles["bgs"]].read())
    h, overlays = bgs.parse_overlays(bgs_bytes)
    bgs.resolve_sprites(bgs_bytes, overlays, 2048, 40)        # atlas params irrelevant for off/depth
    sOrgX, sOrgY, sOrgZ = h.bounds[2], h.bounds[3], h.bounds[0]
    c0 = bgs.parse_cameras(bgs_bytes)[0]
    W, H = c0.range[0] * upscale, c0.range[1] * upscale

    groups = {}      # z -> [(overlay_index, Overlay)]  (overlays at one depth tile a single plane)
    skipped = 0
    for i, o in enumerate(overlays):
        if not o.sprites:
            continue
        if opaque_only and o.sprites[0].trans != 0:
            skipped += 1
            continue
        if not (art / f"Overlay{i}.png").is_file():
            continue
        z = sOrgZ + o.orgZ + min(s.depth for s in o.sprites)
        groups.setdefault(z, []).append((i, o))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    layers = []
    for z in sorted(groups, reverse=True):                   # back (large z) -> front
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for i, o in groups[z]:
            im = Image.open(art / f"Overlay{i}.png").convert("RGBA")
            mnX = min(s.offX for s in o.sprites)
            mnY = min(s.offY for s in o.sprites)
            canvas.alpha_composite(im, ((sOrgX + o.orgX + mnX) * upscale, (sOrgY + o.orgY + mnY) * upscale))
        name = f"layer_{int(z):05d}.png"
        canvas.save(out / name)
        layers.append({"image": name, "z": int(z)})
    return {"layers": layers, "skipped_blend_overlays": skipped, "range": list(c0.range)}


def write_field_project(field: str, out_dir, *, name: str | None = None, field_id: int = 4003,
                        text_block: int = 1073, game=None, bundle=None, want_atlas=False):
    """Extract a real field and emit a ready-to-edit BG-borrow field.toml + camera.bgx in out_dir.

    `name` is the custom script/field id (must be unique vs real fieldids; defaults to
    '<MAPID-first-token>_FORK', e.g. 'GRGR_FORK'). Returns (metadata, field_toml_path).
    `ff9mapkit build <path>` compiles it; the author fills in NPCs/gateways/dialogue first."""
    meta = extract_field(field, out_dir, game=game, bundle=bundle, want_atlas=want_atlas)
    name = name or (meta["mapid"].split("_")[0] + "_FORK")
    # real-art backdrop for the Blender import (only if the field was exported in-game once via
    # Memoria.ini [Export] Field=1). In-game still uses BG-borrow; this is the Blender modelling view.
    meta["background"] = None
    try:
        if compose_background(field, Path(out_dir) / "background.png", game=game, bundle=bundle):
            meta["background"] = "background.png"
    except Exception:
        pass
    cm = meta["camera"]
    wb = meta["walkmesh_bounds"]
    x, z = meta["player_start"]
    scroll = "[camera.scroll]\nenabled = true\n" if meta["scrolling"] else ""
    toml = (
        f"# Imported from {meta['field']} (area {meta['area']}) by ff9mapkit -- BG-borrow.\n"
        f"# Renders the REAL field's art + walkmesh + camera while running your script.\n"
        f"# Camera: pitch {cm['pitch_deg']} deg, FOV {cm['fov_deg']} deg, range {cm['range'][0]}x{cm['range'][1]}"
        f"{' (SCROLLING)' if meta['scrolling'] else ''}.\n"
        f"# Walkmesh bounds: x {wb['x']}  z {wb['z']}  -- place NPCs/gateways within these.\n"
        f"# Edit the content below, then:  ff9mapkit build {name}.field.toml\n\n"
        f"[field]\n"
        f"id = {field_id}\n"
        f'name = "{name}"\n'
        f"area = {meta['area']}\n"
        f'borrow_bg = "{meta["mapid"]}"\n'
        f"text_block = {text_block}\n\n"
        f"[camera]\n"
        f'borrow = "camera.bgx"\n'
        f"{scroll}\n"
        f"[player]\n"
        f"spawn = [{x}, {z}]\n\n"
        f"# --- add your content below (uncomment + edit) ---\n"
        f'# [[npc]]\n# name = "Vivi"\n# preset = "vivi"\n# pos = [{x}, {z}]\n# dialogue = "Hello, traveler."\n#\n'
        f"# [[gateway]]\n# to = 100          # destination field id\n# entrance = 204\n"
        f"# zone = [[-200, 200], [200, 200], [200, 400], [-200, 400]]\n"
    )
    p = Path(out_dir) / f"{name}.field.toml"
    p.write_text(toml, encoding="utf-8", newline="\n")
    meta["field_toml"] = str(p)
    return meta, p
