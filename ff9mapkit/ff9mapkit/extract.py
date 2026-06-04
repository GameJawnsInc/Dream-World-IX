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


def _match_field_folder(container_keys, field: str):
    """Find the unique fieldmaps/<folder>/ whose folder contains `field` (case-insensitive)."""
    want = field.strip().lower()
    want = re.sub(r"^fbg_n\d+_", "", want)          # accept full FBG name or bare mapid
    folders = {}
    for k in container_keys:
        m = re.search(r"fieldmaps/([^/]+)/", k.lower())
        if m:
            folders.setdefault(m.group(1), True)
    hits = [f for f in folders if want in f]
    return hits


def find_field(field: str, game=None, bundle: str | None = None):
    """Locate a field's bundle + container paths. Returns (bundle_path, folder, {role: key}).

    `bundle` (e.g. 'p0data141.bin') short-circuits the scan when you know where it lives."""
    UnityPy = _unitypy()
    sa = _streaming_assets(game)
    cand = [str(sa / bundle)] if bundle else _bundles(game)
    for path in cand:
        env = UnityPy.load(path)
        keys = list(env.container.keys())
        hits = _match_field_folder(keys, field)
        if not hits:
            continue
        if len(hits) > 1 and field.strip().lower() not in hits:
            raise ValueError(f"{field!r} is ambiguous in {os.path.basename(path)}: {hits}")
        folder = hits[0] if field.strip().lower() not in hits else field.strip().lower()
        roles = {}
        for k, v in env.container.items():
            kl = k.lower()
            if f"fieldmaps/{folder}/" not in kl:
                continue
            base = kl.rsplit("/", 1)[-1]
            if base == "atlas.png":
                roles["atlas"] = k
            elif base.endswith(".bgi.bytes"):
                roles["bgi"] = k
            elif base.endswith(".bgs.bytes") and not re.search(r"_(es|fr|gr|it|jp)\.bgs", base):
                roles["bgs"] = k                       # default (us/en) scene
        return path, folder, roles, env
    raise FileNotFoundError(f"field {field!r} not found in any p0data bundle under {sa}")


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
        "player_start": [wm.charPos.x, wm.charPos.z],
        "walkmesh_bounds": {
            "x": [wm.minPos.x, wm.maxPos.x],
            "z": [wm.minPos.z, wm.maxPos.z],
            "verts": len(wm.verts),
            "tris": len(wm.tris),
        },
        "out": str(out),
    }
    return meta


def write_field_project(field: str, out_dir, *, name: str, field_id: int = 4003,
                        text_block: int = 1073, game=None, bundle=None, want_atlas=False):
    """Extract a real field and emit a ready-to-edit BG-borrow field.toml + camera.bgx in out_dir.

    `name` is the custom script/field id (must be unique vs real fieldids; e.g. 'GRGR_FORK').
    Returns (metadata, field_toml_path). `ff9mapkit build <path>` compiles it; the author fills in
    NPCs/gateways/dialogue first."""
    meta = extract_field(field, out_dir, game=game, bundle=bundle, want_atlas=want_atlas)
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
