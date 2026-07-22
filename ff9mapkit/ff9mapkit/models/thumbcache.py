"""The 3D-model preview disk cache -- pure worker logic, importable Qt-free.

The renders come from :mod:`.preview` (software rasterizer); this module owns WHERE they live and
the counts sidecar. Game art is static, so a cache key is just ``{geoId}_v{RENDER_V}`` -- bump
:data:`_MODEL_RENDER_V` whenever the renderer's output changes. Consumers: the Workspace's
``ModelThumbService`` (async renders through :func:`build_model_thumb`), the Models tab's facts
line (:func:`model_thumb_meta`), and the Info Hub / catalog pickers (:func:`cached_png` -- CACHE
READS ONLY, so a tk-free/GUI-thread caller never pays a render).
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import provision

MODEL_THUMB = 256                               # cached model-preview size (px, square)
_MODEL_RENDER_V = 1                             # bump when the renderer's output changes -> new cache keys


def model_thumb_paths(geo_id) -> tuple:
    """(png, meta-json) cache paths for a model preview."""
    stem = f"{int(geo_id)}_v{_MODEL_RENDER_V}"
    d = provision.cache_dir() / "model_thumbs"
    return d / f"{stem}.png", d / f"{stem}.json"


def cached_png(geo_id) -> "str | None":
    """The cached preview PNG path if it EXISTS -- never renders (safe on any thread, no install)."""
    try:
        png, _meta = model_thumb_paths(geo_id)
        return str(png) if png.is_file() else None
    except (TypeError, ValueError, OSError):
        return None


def model_thumb_meta(geo_id) -> "dict | None":
    """The counts sidecar a finished render wrote ({bones, meshes, verts, textures}), or None."""
    _png, meta = model_thumb_paths(geo_id)
    try:
        return json.loads(meta.read_text(encoding="utf-8")) if meta.is_file() else None
    except (OSError, ValueError):
        return None


def absent_ids() -> set:
    """The geo ids the render worker has PROBED and found unshipped (no geometry on disc anywhere --
    the PSX-era catalog leftovers). One directory scan over the ``absent`` sidecars; a fresh machine
    (nothing probed yet) honestly returns an empty set. Cache reads only -- never touches the install."""
    out = set()
    d = provision.cache_dir() / "model_thumbs"
    try:
        sidecars = list(d.glob(f"*_v{_MODEL_RENDER_V}.json"))
    except OSError:
        return out
    for meta in sidecars:
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("absent") and data.get("id") is not None:
            try:
                out.add(int(data["id"]))
            except (TypeError, ValueError):
                continue
    return out


def build_model_thumb(token, ctx: "dict | None" = None) -> "str | None":
    """Synchronously render (or reuse) the cached preview PNG for a model. Pure worker logic -- no Qt.
    ``ctx`` (a plain dict, thread-confined to the caller) keeps the p0data bundles + the p0data5 env
    alive across calls, so a browse session pays the ~2s bundle load once and ~0.1-0.3s per model
    after. Writes a ``{geoId}_v{N}.json`` counts sidecar beside the PNG (bones/meshes/verts/textures
    -- the detail pane's facts, harvested for free from the render struct)."""
    from .. import catalog
    m = catalog.model(token)
    if not m:
        return None
    png, meta = model_thumb_paths(m.id)
    if png.is_file():
        return str(png)
    prior = model_thumb_meta(m.id)
    if prior and prior.get("absent"):
        return None                              # a known unshipped id -- don't re-probe the install
    from . import anim as manim
    from . import extract, preview
    ctx = ctx if ctx is not None else {}
    didx = 2 if m.group == "WEP" else 4          # weapons live in p0data2 (BattleMap/BattleModel/6)
    if didx not in ctx:
        ctx[didx] = extract._Bundle(None, data_index=didx)
    if "env5" not in ctx:
        try:
            ctx["env5"] = manim._load_env5(None)
        except Exception:   # noqa: BLE001 -- no p0data5 -> render the rest pose instead of failing
            ctx["env5"] = None
    try:
        struct = preview._skinned_struct(m.name, bundle=ctx[didx], env5=ctx["env5"],
                                         pose=ctx["env5"] is not None)
    except FileNotFoundError as e:
        # an UNSHIPPED catalog id (no geometry on disc anywhere -- the GEO_MAIN_B2_* band etc.):
        # remember WHY in the sidecar so the Models tab can say so instead of a bare un-thumbnailed miss
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(json.dumps({"geo": m.name, "id": m.id, "absent": True, "error": str(e)}),
                        encoding="utf-8")
        return None
    img = preview.render_model(struct, size=MODEL_THUMB)
    png.parent.mkdir(parents=True, exist_ok=True)
    tmp = png.with_suffix(".tmp.png")
    img.save(tmp, "PNG", optimize=True)
    tmp.replace(png)
    info = {"geo": struct.get("geo"), "id": struct.get("geo_id"),
            "bones": len(struct.get("bones") or []),
            "meshes": len(struct.get("meshes") or []),
            "verts": sum(len(me.get("verts") or []) for me in (struct.get("meshes") or [])),
            "textures": sorted(struct.get("textures") or {})}
    meta.write_text(json.dumps(info), encoding="utf-8")
    return str(png)
