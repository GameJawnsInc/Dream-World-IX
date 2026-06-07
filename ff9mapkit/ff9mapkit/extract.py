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
from . import eventscan
from ._fieldtable import FBG_TO_EVT
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


# ---- event script (.eb) extraction: fork a field WITH its gateways/music/encounters -----
EVT_LANG = "us"                       # event binaries are per-language; the bytecode we scan is identical
_EVENTS_BUNDLE_CACHE = ".ff9mapkit-events-bundle.txt"


def _events_bundle(game=None):
    """The p0data bundle holding field event binaries (``eventbinary/field/...``). Cached next to the
    bundles; on a miss it's detected p0data7-first (where they historically live), so the common case
    loads one bundle, not all of them."""
    cache = _streaming_assets(game) / _EVENTS_BUNDLE_CACHE
    if cache.exists():
        name = cache.read_text(encoding="utf-8").strip()
        if name:
            return name
    UnityPy = _unitypy()
    bundles = sorted(_bundles(game),
                     key=lambda p: (0 if "p0data7." in os.path.basename(p) else 1, p))
    for path in bundles:
        try:
            env = UnityPy.load(path)
        except Exception:
            continue
        if any("eventbinary/field/" in k.lower() for k in env.container):
            name = os.path.basename(path)
            try:
                cache.write_text(name, encoding="utf-8")
            except OSError:
                pass
            return name
    return None


def event_name_for(field: str, game=None):
    """The ``EVT_<name>`` event-script name for an imported field's FBG folder, or None if it isn't a
    standard field map (world/special fields have no field event). Uses the baked FBG->event table."""
    folder, _ = resolve_field(field, game)
    rec = FBG_TO_EVT.get(folder)
    return rec[1] if rec else None


def extract_event_script(field: str, *, game=None, lang: str = EVT_LANG):
    """The compiled ``.eb`` bytes of a real field's event script (``lang``, default us), or None if it
    can't be located (no FBG->event mapping, or the binary isn't present). Used by ``import`` to
    extract gateways / music / encounters / movement from the real field -- it never raises, so a
    missing script just means the fork imports without that content (camera/walkmesh/art are
    unaffected). ``lang`` is also used by provisioning to extract the per-language blank base."""
    try:
        evt = event_name_for(field, game)
        if not evt:
            return None
        bundle = _events_bundle(game)
        if not bundle:
            return None
        UnityPy = _unitypy()
        env = UnityPy.load(str(_streaming_assets(game) / bundle))
        want = f"eventbinary/field/{lang}/{evt}.eb".lower()
        for k, obj in env.container.items():
            kl = k.lower()
            if want in kl and kl.endswith(".eb.bytes"):
                return _raw_bytes(obj.read())
    except Exception:
        return None
    return None


def _imported_content_toml(eb_bytes):
    """field.toml blocks (gateways / encounter / music) + the control-direction value, extracted LIVE
    from a real field's ``.eb``. Returns (blocks_text, control_dir, summary). blocks_text is appended
    at the end of the toml; control_dir (or None) goes in the [camera] block; summary feeds the CLI."""
    content = eventscan.scan_content(eb_bytes)
    parts = []
    gws = content["gateways"]
    if gws:
        parts.append(
            "# --- EXITS imported from the real field (LIVE). `to` is the REAL destination field id --\n"
            "# retarget each to your own room ids, or leave them to walk back into the live game. ---")
        for g in gws:
            zone = ", ".join(f"[{x}, {z}]" for x, z in g["zone"])
            parts.append(f"[[gateway]]\nto = {g['to']}\nentrance = {g['entrance']}\nzone = [{zone}]")
    enc = content["encounter"]
    if enc:
        block = f"[encounter]\nscene = {enc['scenes'][0]}\nfreq = {enc['freq']}"
        if len(set(enc["scenes"])) != 1:
            block += f"\nscenes = [{', '.join(str(s) for s in enc['scenes'])}]"
        parts.append("# random battles imported from the real field (build adds the after-battle "
                     "reinit)\n" + block)
    if content["music"] is not None:
        parts.append(f"# field BGM imported from the real field\n[music]\nsong = {content['music']}")
    summary = {"gateways": len(gws), "encounter": enc is not None,
               "music": content["music"], "control_direction": content["control_direction"]}
    return "\n\n".join(parts), content["control_direction"], summary


def _content_for_import(field: str, game):
    """(content_blocks, control_dir, summary) for a field's import. Locates + scans the real .eb;
    returns ("", None, None) if it can't (no mapping / no game / UnityPy absent) so import still works."""
    eb_bytes = extract_event_script(field, game=game)
    if not eb_bytes:
        return "", None, None
    return _imported_content_toml(eb_bytes)


def _content_section(content_blocks: str, x: int, z: int) -> str:
    """The trailing content of the field.toml: the LIVE imported blocks, or a commented gateway stub
    when nothing was imported (the old hand-authoring hint)."""
    if content_blocks:
        return content_blocks + "\n"
    return ("# [[gateway]]\n# to = 100          # destination field id\n# entrance = 204\n"
            "# zone = [[-200, 200], [200, 200], [200, 400], [-200, 400]]\n")


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


_ABR_NONE = "PSX/FieldMap_Abr_None"


def _overlay_shader(sprite) -> str:
    """The PSX field-map shader for an overlay, from its first sprite -- mirrors Memoria's OWN .bgx
    exporter (BGSCENE_DEF.cs:611): opaque (trans==0) => Abr_None, else Abr_{min(3, alpha)} (the PSX
    ABR blend mode: 0 average, 1 additive, 2 subtractive, 3 add-quarter). The .bgx importer honors
    the `Shader:` directive (BGSCENE_DEF.cs:321), so light/shadow overlays blend correctly."""
    if sprite.trans == 0:
        return _ABR_NONE
    return f"PSX/FieldMap_Abr_{min(3, sprite.alpha)}"


def extract_layers(field: str, out_dir, *, game=None, bundle=None, upscale=4, include_blend=True):
    """Per-overlay art layers (grouped by depth + blend mode) for an EDITABLE custom-scene fork that
    PRESERVES occlusion AND lighting -- the inverse of `compose_background`'s flat merge.

    Groups the field's overlays by (DEPTH, SHADER) and writes one transparent full-canvas PNG per
    group, returning the `[[layers]]` list ({image, z, [shader]}) for a custom scene. The engine
    redraws the depth-ordered scene, so the 3D player is occluded by / occludes each layer exactly
    like the real field (smaller z = nearer the camera = drawn in front), and light/shadow overlays
    blend (Abr shaders). Depth + position follow Memoria's OWN .bgx exporter (BGSCENE_DEF.cs:606):
    z = scene.orgZ + overlay.orgZ + min(sprite.depth); position = scene.org{X,Y}+overlay.org{X,Y}+
    min(sprite.off{X,Y}) -- baked into each full-canvas PNG, so the kit layer is position [0,0], size
    = range. Shader per BGSCENE_DEF.cs:611.

    Returns None if the field hasn't been `[Export] Field=1`'d in-game yet (no per-overlay PNGs on
    disk). `include_blend` (default) emits the additive/subtractive light+shadow overlays too (they
    carry a lot of a field's art -- e.g. GRGR is 5/7 blend); set False for opaque structure only.

    Co-located same-(depth,shader) overlays merge into one layer (correct for a tiled plane,
    approximate for overlapping animation frames -- a known v1 simplification).
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

    groups = {}      # (z, shader) -> [(overlay_index, Overlay)]
    skipped = 0
    for i, o in enumerate(overlays):
        if not o.sprites:
            continue
        shader = _overlay_shader(o.sprites[0])
        if not include_blend and shader != _ABR_NONE:
            skipped += 1
            continue
        if not (art / f"Overlay{i}.png").is_file():
            continue
        z = sOrgZ + o.orgZ + min(s.depth for s in o.sprites)
        groups.setdefault((z, shader), []).append((i, o))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    layers, blend = [], 0
    for (z, shader) in sorted(groups, key=lambda k: (-k[0], k[1])):    # back (large z) -> front
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for i, o in groups[(z, shader)]:
            im = Image.open(art / f"Overlay{i}.png").convert("RGBA")
            mnX = min(s.offX for s in o.sprites)
            mnY = min(s.offY for s in o.sprites)
            canvas.alpha_composite(im, ((sOrgX + o.orgX + mnX) * upscale, (sOrgY + o.orgY + mnY) * upscale))
        abr = shader.rsplit("_", 1)[-1]                       # None / 0 / 1 / 2 / 3
        name = f"layer_{int(z):05d}_{abr}.png"
        canvas.save(out / name)
        L = {"image": name, "z": int(z)}
        if shader != _ABR_NONE:
            L["shader"] = shader
            blend += 1
        layers.append(L)
    return {"layers": layers, "blend_layers": blend, "skipped_blend_overlays": skipped,
            "range": list(c0.range)}


def _world_walkmesh_obj_text(wm) -> str:
    """A world-frame Wavefront .obj (multi-floor aware) re-exported from a parsed walkmesh: the verts
    ARE the world coords (BgiWalkmesh.world_verts), one `o floor_N` per floor -- build with
    `[walkmesh] frame = "world"` (bgi.build, orgPos=0) so the engine renders them verbatim."""
    wv = wm.world_verts()
    faces = [tuple(t.vtx) for t in wm.tris]
    floor_ids = [t.floor_ndx for t in wm.tris]
    order = []
    for f in floor_ids:
        if f not in order:
            order.append(f)
    lines = ["# walkmesh re-exported by ff9mapkit (world frame, orgPos=0)"]
    for (x, y, z) in wv:
        lines.append(f"v {x} {y} {z}")
    if len(order) > 1:
        for fid in order:
            lines.append(f"o floor_{fid}")
            for (a, b, c), fl in zip(faces, floor_ids):
                if fl == fid:
                    lines.append(f"f {a + 1} {b + 1} {c + 1}")
    else:
        for (a, b, c) in faces:
            lines.append(f"f {a + 1} {b + 1} {c + 1}")
    return "\n".join(lines) + "\n"


def _write_links_toml(wm, path) -> int:
    """Write the adjacency sidecar (cross-floor seams + header) for an editable multi-floor walkmesh.
    walkmesh.obj carries geometry; this carries the seams geometry can't express. Reconciled on build
    by world position (build._apply_links). Returns the seam count. See docs/WALKMESH_EDITING.md."""
    seams = wm.extract_seams()
    L = ["# Adjacency sidecar for an editable multi-floor walkmesh (ff9mapkit). walkmesh.obj carries the",
         "# geometry; this carries the CROSS-FLOOR seams geometry can't express (FF9 floors use disjoint",
         "# vertex sets, so rebuild-from-geometry can't recover them). On build with `[walkmesh] obj +",
         "# links`, each seam is re-matched to your edited geometry by WORLD POSITION; a seam whose edge",
         "# you moved/deleted warns instead of silently dropping. Auto-generated -- rarely hand-edited.",
         "",
         "[header]",
         f"active_floor = {wm.activeFloor}",
         f"active_tri = {wm.activeTri}",
         f"char_pos = [{wm.charPos.x}, {wm.charPos.y}, {wm.charPos.z}]",
         ""]
    for (fa, a, fb, b) in seams:
        L += ["[[seam]]", f"a_floor = {fa}",
              f"a_edge = [[{a[0][0]}, {a[0][1]}, {a[0][2]}], [{a[1][0]}, {a[1][1]}, {a[1][2]}]]",
              f"b_floor = {fb}"]
        if b:
            L.append(f"b_edge = [[{b[0][0]}, {b[0][1]}, {b[0][2]}], [{b[1][0]}, {b[1][1]}, {b[1][2]}]]")
        L.append("")
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    return len(seams)


MIN_CUSTOM_AREA = 10   # engine builds 'FBG_N<area>' + reads exactly 2 chars -> areas 0-9 black-screen


def safe_custom_area(area: int) -> int:
    """An area a CUSTOM scene (ships its own art) can safely render: a source area >= 10 as-is, else a
    safe default (11). For BG-borrow the area MUST equal the real field's, so 0-9 can't borrow at all."""
    return area if area >= MIN_CUSTOM_AREA else 11


def write_editable_project(field: str, out_dir, *, name: str | None = None, field_id: int = 4003,
                           text_block: int = 1073, game=None, bundle=None):
    """Fork a real field as a fully EDITABLE custom scene (vs BG-borrow): re-export its walkmesh via the
    world-frame builder + extract its art as per-DEPTH layers (occlusion preserved) + reuse its camera.

    Emits a custom-scene `field.toml` (NO borrow_bg) ready for `ff9mapkit build` and for repainting any
    single `layer_*.png` / editing `walkmesh.obj`. Returns (metadata, field_toml_path). Requires the
    field to have been `[Export] Field=1`'d in-game once (per-overlay PNGs on disk); raises RuntimeError
    with guidance otherwise (use plain import for a BG-borrow fork that reuses the art as-is)."""
    out = Path(out_dir)
    meta = extract_field(field, out, game=game, bundle=bundle)     # writes camera.bgx + walkmesh.bgi
    name = name or (meta["mapid"].split("_")[0] + "_EDIT")
    # A custom scene ships its own art under FBG_N<area>_<name>, so the area is just a folder key --
    # any value >= 10 works (single-digit areas black-screen via the engine's 2-char FBG lookup).
    # Remap a low source area to a safe one so forks of early-game (area 0-9) fields build + render.
    safe_area = safe_custom_area(meta["area"])
    remap_note = ("" if safe_area == meta["area"] else
                  f"# NOTE: source area {meta['area']} < 10 black-screens via the engine's FBG_N<area> "
                  f"lookup, so this\n# custom scene uses area {safe_area} (it ships its own art -- the "
                  f"source area is just a folder key).\n")
    wm = bgi.BgiWalkmesh.from_bytes((out / "walkmesh.bgi").read_bytes())
    nfloors = len(wm.floors)
    (out / "walkmesh.obj").write_text(_world_walkmesh_obj_text(wm), encoding="utf-8", newline="\n")
    nseams = _write_links_toml(wm, out / "walkmesh.links.toml") if nfloors > 1 else 0

    layers_info = extract_layers(field, out, game=game, bundle=bundle)
    if layers_info is None:
        raise RuntimeError(
            f"{meta['field']}: editable art needs the field exported in-game once. Set Memoria.ini "
            f"[Export] Enabled=1 + Field=1, visit the field, then retry -- OR use `ff9mapkit import "
            f"{field}` (BG-borrow: reuses the real art as-is, no repaint).")
    layers = layers_info["layers"]
    meta["layers"] = len(layers)
    meta["blend_layers"] = layers_info["blend_layers"]
    meta["editable_name"] = name

    content_blocks, control_dir, content_summary = _content_for_import(field, game)
    meta["imported_content"] = content_summary
    cm = meta["camera"]
    wb = meta["walkmesh_bounds"]
    x, z = meta["player_start"]
    scroll = "[camera.scroll]\nenabled = true\n" if meta["scrolling"] else ""
    control_line = f"control_direction = {control_dir}   # imported WASD-vs-camera tuning\n" if control_dir is not None else ""

    def _layer_block(L):
        s = f'[[layers]]\nimage = "{L["image"]}"\nz = {L["z"]}'
        return s + (f'\nshader = "{L["shader"]}"' if L.get("shader") else "")
    layer_blocks = "\n".join(_layer_block(L) for L in layers)

    if nfloors > 1:
        reshape = ('# To RESHAPE the geometry: edit walkmesh.obj, then replace the bgi line above with:\n'
                   '#   obj = "walkmesh.obj"\n#   links = "walkmesh.links.toml"\n#   frame = "world"\n'
                   f'# (the seam sidecar re-attaches this field\'s {nseams} cross-floor links to your edits\n'
                   '#  by world position; a seam whose edge you moved warns instead of dropping silently.)\n')
    else:
        reshape = ('# To RESHAPE: edit walkmesh.obj, then replace the bgi line above with:\n'
                   '#   obj = "walkmesh.obj"\n#   frame = "world"\n')
    walkmesh_toml = (
        f"[walkmesh]\n"
        f'bgi = "walkmesh.bgi"   # the real field\'s walkmesh ({nfloors} floor(s)) -- connectivity preserved\n'
        f"{reshape}"
    )
    toml = (
        f"# EDITABLE fork of {meta['field']} (area {meta['area']}) by ff9mapkit -- a full CUSTOM SCENE.\n"
        f"# Re-exported walkmesh + the real art split into one layer per DEPTH (occlusion preserved).\n"
        f"# Repaint any layer_*.png, reshape walkmesh.obj, add content -- then:  ff9mapkit build {name}.field.toml\n"
        f"# Camera: pitch {cm['pitch_deg']} deg, FOV {cm['fov_deg']} deg, range {cm['range'][0]}x{cm['range'][1]}"
        f"{' (SCROLLING)' if meta['scrolling'] else ''}.  Walkmesh bounds: x {wb['x']}  z {wb['z']}.\n"
        f"{remap_note}\n"
        f"[field]\n"
        f"id = {field_id}\n"
        f'name = "{name}"\n'
        f"area = {safe_area}\n"
        f"text_block = {text_block}\n\n"
        f"[camera]\n"
        f'borrow = "camera.bgx"\n'
        f"{control_line}"
        f"{scroll}\n"
        f"{walkmesh_toml}\n"
        f"{layer_blocks}\n\n"
        f"[player]\n"
        f"spawn = [{x}, {z}]\n\n"
        f"# --- add NPCs/dialogue (uncomment + edit); keep positions within the walkmesh bounds above ---\n"
        f'# [[npc]]\n# name = "Vivi"\n# preset = "vivi"\n# pos = [{x}, {z}]\n# dialogue = "Hello, traveler."\n\n'
        f"{_content_section(content_blocks, x, z)}"
    )
    p = Path(out_dir) / f"{name}.field.toml"
    p.write_text(toml, encoding="utf-8", newline="\n")
    meta["field_toml"] = str(p)
    return meta, p


def write_field_project(field: str, out_dir, *, name: str | None = None, field_id: int = 4003,
                        text_block: int = 1073, game=None, bundle=None, want_atlas=False):
    """Extract a real field and emit a ready-to-edit BG-borrow field.toml + camera.bgx in out_dir.

    `name` is the custom script/field id (must be unique vs real fieldids; defaults to
    '<MAPID-first-token>_FORK', e.g. 'GRGR_FORK'). Returns (metadata, field_toml_path).
    `ff9mapkit build <path>` compiles it; the author fills in NPCs/gateways/dialogue first."""
    # BG-borrow reuses the REAL field's BG via FBG_N<area>_<mapid>; the engine builds that name with
    # no zero-padding and reads exactly 2 chars for the area, so single-digit areas (0-9) black-screen.
    # Catch it here with a clear pointer to --editable rather than emitting a field.toml that won't build.
    folder, _b = resolve_field(field, game)
    src_area, _m = parse_fbg_folder(folder)
    if src_area < MIN_CUSTOM_AREA:
        raise RuntimeError(
            f"{folder} is in area {src_area}: BG-borrow can't render single-digit areas (the engine "
            f"builds 'FBG_N<area>' and reads exactly 2 chars, so areas 0-9 black-screen). "
            f"Fork it as a custom scene instead:  ff9mapkit import {field} --editable  "
            f"(it ships its own art, so it runs at a safe area).")
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
    # extract the real field's LIVE content (gateways / encounter / music / movement) from its .eb
    content_blocks, control_dir, content_summary = _content_for_import(field, game)
    meta["imported_content"] = content_summary
    cm = meta["camera"]
    wb = meta["walkmesh_bounds"]
    x, z = meta["player_start"]
    scroll = "[camera.scroll]\nenabled = true\n" if meta["scrolling"] else ""
    control_line = f"control_direction = {control_dir}   # imported WASD-vs-camera tuning\n" if control_dir is not None else ""
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
        f"{control_line}"
        f"{scroll}\n"
        f"[walkmesh]\n"
        f'reference = "walkmesh.bgi"   # validation only -- NOT shipped (the engine uses the borrowed\n'
        f"# field's real walkmesh). The build WARNS if the content below sits off this walkable area.\n\n"
        f"[player]\n"
        f"spawn = [{x}, {z}]\n\n"
        f"# --- add NPCs/dialogue (uncomment + edit); keep positions within the walkmesh bounds above ---\n"
        f'# [[npc]]\n# name = "Vivi"\n# preset = "vivi"\n# pos = [{x}, {z}]\n# dialogue = "Hello, traveler."\n\n'
        f"{_content_section(content_blocks, x, z)}"
    )
    p = Path(out_dir) / f"{name}.field.toml"
    p.write_text(toml, encoding="utf-8", newline="\n")
    meta["field_toml"] = str(p)
    return meta, p
