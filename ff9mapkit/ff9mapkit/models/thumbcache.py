"""The 3D-model preview disk cache -- pure worker logic, importable Qt-free.

The renders come from :mod:`.preview` (software rasterizer); this module owns WHERE they live and
the counts sidecar. Game art is static, so a cache key is just ``{geoId}_v{RENDER_V}``. The version
has TWO independent parts, because the two caches go stale for different reasons: :data:`_RASTER_V`
(the rasterizer's pixels -- stills AND clip frames) and :data:`_STILL_POSE_V` (which clip a still is
posed from -- stills only; a clip frame is posed by its own clip and cannot care). Consumers: the Workspace's
``ModelThumbService`` (async renders through :func:`build_model_thumb`), the Models tab's facts
line (:func:`model_thumb_meta`), and the Info Hub / catalog pickers (:func:`cached_png` -- CACHE
READS ONLY, so a tk-free/GUI-thread caller never pays a render).

The ANIMATED half (:func:`build_anim_clip`) caches one PNG per rendered frame of one clip under a
SEPARATE ``anim_frames/`` subdir -- deliberately not beside the stills, whose :func:`absent_ids` glob
walks every sidecar it finds. Its key is ``{geo}_{anim}_f{frame}_v{_ANIM_RENDER_V}`` and the version
DERIVES from the still's, so a renderer bump invalidates both caches together. Only BUNDLED p0data5
clips are cached this way: bundled bytes never change, so (geo, anim, frame) is a sound identity. A
loose/minted ``.anim`` can be edited under a stable key, so it must not be keyed like this.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

from .. import provision

MODEL_THUMB = 256                               # cached model-preview size (px, square)
_RASTER_V = 1                                   # bump when render_model's PIXELS change -> both caches
_STILL_POSE_V = 2                               # bump when catalog.stand_clip picks differently -> stills
#                                                 only. 2 = exact-label ranking (idle / stand / battle 000)
_MODEL_RENDER_V = f"{_RASTER_V}p{_STILL_POSE_V}"   # the still's key
_ANIM_RENDER_V = f"{_RASTER_V}a1"               # DERIVED from the rasterizer alone: a pose-pick change
#                                                 must NOT throw away every rendered clip
MAX_ANIM_FRAMES = 60                            # rendered-frame cap per clip; longer clips STRIDE (below)
ANIM_CACHE_MB = 256                             # clip-frame budget; least-recently-PLAYED clips go first


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


def _prune_other_still_versions(geo_id) -> None:
    """Drop this model's still + sidecar from EVERY other version. A version bump used to leave the
    whole previous generation behind forever (nothing globbed for it again); now a model's stale pair
    goes the moment its fresh one lands."""
    d = provision.cache_dir() / "model_thumbs"
    try:
        stale = list(d.glob(f"{int(geo_id)}_v*.png")) + list(d.glob(f"{int(geo_id)}_v*.json"))
    except (OSError, TypeError, ValueError):
        return
    keep = (f"_v{_MODEL_RENDER_V}.png", f"_v{_MODEL_RENDER_V}.json")
    for old in stale:
        if old.name.endswith(keep):
            continue
        try:
            old.unlink()
        except OSError:
            pass


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


# ------------------------------------------------------------------ animated clip frames -----

def _anim_dir() -> Path:
    return provision.cache_dir() / "anim_frames"


def anim_frame_path(geo_id, anim_id, frame) -> Path:
    """The cache PNG path for ONE rendered frame of one model's clip."""
    return _anim_dir() / f"{int(geo_id)}_{int(anim_id)}_f{int(frame)}_v{_ANIM_RENDER_V}.png"


def anim_meta_path(geo_id, anim_id) -> Path:
    """The per-(model, clip) sidecar path: frame_count / sample_rate / label / fit / stride /
    rendered_frames -- everything a player strip needs to drive playback without the install."""
    return _anim_dir() / f"{int(geo_id)}_{int(anim_id)}_v{_ANIM_RENDER_V}.json"


def cached_anim_frame(geo_id, anim_id, frame) -> "str | None":
    """The cached frame PNG if it EXISTS -- one stat, never renders (safe on any thread, no install)."""
    try:
        p = anim_frame_path(geo_id, anim_id, frame)
        return str(p) if p.is_file() else None
    except (TypeError, ValueError, OSError):
        return None


def anim_clip_meta(geo_id, anim_id) -> "dict | None":
    """The sidecar a finished clip fill wrote, or None. Cache reads only."""
    try:
        p = anim_meta_path(geo_id, anim_id)
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
    except (TypeError, ValueError, OSError):
        return None


def _frame_count(clip: dict) -> int:
    """A clip's frame count. THE FRAME LAW, measured over 460 real clips: every one starts at t=0, none
    is zero-length, and ``sample_rate`` is 30.0 universally -- so the frames are
    ``round(length * rate) + 1`` (both endpoints inclusive) and frame ``f`` sits at ``t = f / rate``."""
    rate = float(clip.get("sample_rate") or 30.0) or 30.0
    return max(1, int(round(float(clip.get("length") or 0.0) * rate)) + 1)


def _prune_other_versions(geo_id, anim_id) -> None:
    """Drop this (model, clip)'s frames + sidecar from EVERY other renderer version (the build_thumb
    prune idiom): a bumped ``_ANIM_RENDER_V`` leaves up to 60 dead PNGs per clip behind otherwise."""
    d = _anim_dir()
    try:
        stale = list(d.glob(f"{int(geo_id)}_{int(anim_id)}_f*_v*.png")) + \
            list(d.glob(f"{int(geo_id)}_{int(anim_id)}_v*.json"))
    except (OSError, TypeError, ValueError):
        return
    for old in stale:
        if old.name.endswith(f"_v{_ANIM_RENDER_V}.png") or old.name.endswith(f"_v{_ANIM_RENDER_V}.json"):
            continue
        try:
            old.unlink()
        except OSError:
            pass


def touch_anim_clip(geo_id, anim_id) -> None:
    """Stamp a clip as JUST PLAYED (its sidecar's mtime is the LRU clock :func:`prune_anim_cache`
    reads). One utime, no read -- cheap enough for the GUI thread's warm path."""
    try:
        os.utime(anim_meta_path(geo_id, anim_id), None)
    except (OSError, TypeError, ValueError):
        pass


def anim_cache_budget() -> int:
    """The clip-frame budget in BYTES (:data:`ANIM_CACHE_MB`, or ``$FF9MAPKIT_ANIM_CACHE_MB``; 0 or a
    negative value means unlimited)."""
    raw = os.environ.get("FF9MAPKIT_ANIM_CACHE_MB", "")
    try:
        mb = float(raw) if raw.strip() else float(ANIM_CACHE_MB)
    except ValueError:
        mb = float(ANIM_CACHE_MB)
    return int(mb * 1024 * 1024)


def _anim_clips_on_disk() -> dict:
    """``{(geo, anim): {"files": [Path], "bytes": int, "used": mtime}}`` for every clip with frames or
    a sidecar in the cache, ANY version. ``used`` is the sidecar's mtime when it has one (the stamp
    :func:`touch_anim_clip` moves), else its newest frame's -- an aborted fill has frames and no
    sidecar, and is still a clip worth reusing or evicting."""
    clips: dict = {}
    try:
        entries = list(os.scandir(_anim_dir()))
    except OSError:
        return clips
    for e in entries:
        parts = e.name.split("_")
        if len(parts) < 3 or not (parts[0].isdigit() and parts[1].isdigit()):
            continue
        try:
            st = e.stat()
        except OSError:
            continue
        c = clips.setdefault((int(parts[0]), int(parts[1])),
                             {"files": [], "bytes": 0, "used": 0.0, "stamped": False})
        c["files"].append(Path(e.path))
        c["bytes"] += st.st_size
        if e.name.endswith(".json"):
            c["used"], c["stamped"] = st.st_mtime, True
        elif not c["stamped"]:
            c["used"] = max(c["used"], st.st_mtime)
    return clips


def anim_cache_stats() -> dict:
    """``{"clips", "files", "bytes"}`` for the clip-frame cache -- one directory scan, no reads."""
    clips = _anim_clips_on_disk()
    return {"clips": len(clips), "files": sum(len(c["files"]) for c in clips.values()),
            "bytes": sum(c["bytes"] for c in clips.values())}


def prune_anim_cache(budget: "int | None" = None, *, keep=()) -> int:
    """Evict whole clips, least-recently-PLAYED first, until the cache fits ``budget`` bytes (default
    :func:`anim_cache_budget`). Returns the bytes freed.

    A clip is ~1.6 MB of frames and the catalog names thousands of them, so an uncapped cache grows
    with every clip anyone ever clicks. Whole clips only -- a half-evicted clip is neither warm nor
    absent. ``keep`` is one ``(geo_id, anim_id)`` that must survive (the clip that was just built)."""
    budget = anim_cache_budget() if budget is None else int(budget)
    if budget <= 0:
        return 0
    clips = _anim_clips_on_disk()
    total = sum(c["bytes"] for c in clips.values())
    if total <= budget:
        return 0
    try:
        spared = (int(keep[0]), int(keep[1])) if keep else None
    except (TypeError, ValueError, IndexError):
        spared = None
    freed = 0
    for key, c in sorted(clips.items(), key=lambda kv: kv[1]["used"]):
        if total - freed <= budget:
            break
        if key == spared:
            continue
        for f in c["files"]:
            try:
                f.unlink()
            except OSError:
                continue
        freed += c["bytes"]
    return freed


def still_cache_stats() -> dict:
    """``{"rendered", "absent", "stale", "bytes"}`` for the model stills -- one directory scan. ``stale``
    counts files from OTHER versions (dead weight a re-render or a clear removes)."""
    out = {"rendered": 0, "absent": 0, "stale": 0, "bytes": 0}
    try:
        entries = list(os.scandir(provision.cache_dir() / "model_thumbs"))
    except OSError:
        return out
    live_png, live_json = f"_v{_MODEL_RENDER_V}.png", f"_v{_MODEL_RENDER_V}.json"
    for e in entries:
        try:
            out["bytes"] += e.stat().st_size
        except OSError:
            continue
        if e.name.endswith(live_png):
            out["rendered"] += 1
        elif not e.name.endswith(live_json):
            out["stale"] += 1
    out["absent"] = len(absent_ids())
    return out


def clear_preview_cache(*, stills: bool = True, clips: bool = True) -> int:
    """Delete the rendered stills and/or clip frames -> the bytes freed. Everything here is DERIVED
    from the install and re-renders on demand, so this can never lose work; the ``absent`` sidecars go
    too (a re-probe is one cheap miss each)."""
    freed = 0
    dirs = ([provision.cache_dir() / "model_thumbs"] if stills else []) + ([_anim_dir()] if clips else [])
    for d in dirs:
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            if not e.name.endswith((".png", ".json")):
                continue
            try:
                size = e.stat().st_size
                os.unlink(e.path)
                freed += size
            except OSError:
                continue
    return freed


def build_anim_clip(token, anim_id, ctx: "dict | None" = None, *, on_frame=None,
                    should_abort=None, on_total=None) -> "dict | None":
    """Render (or reuse) every cached frame of one model's BUNDLED clip -> its meta dict, or None when
    the clip can't be resolved/rendered. Pure worker logic -- no Qt.

    ``ctx`` (a plain dict, thread-confined to the caller) memoizes the p0data bundles, the p0data5 env,
    its one-pass anim->folder map, each read clip and each model's ``_collect`` + textures, so a browse
    session pays the ~2s bundle load once and a clip after it is skin+raster only.

    Order is load-bearing: every frame is posed and skinned FIRST so the union of their projected boxes
    becomes the ONE ``fit=`` all of them rasterize against -- auto-fitting per frame pulses the model's
    scale (measured 7.6%) and drifts it (8%) across a real walk. ``on_frame(frame_idx, png_path)`` is
    called as each frame lands (a strip can play the contiguous prefix long before the fill ends) and
    ``should_abort()`` is polled between frames (the cancel seam: an armed clip supersedes the last).
    ``on_total(n)`` is called ONCE, before the first frame, with how many frames will be rendered -- a
    fill is 5-10s of rasterizing (measured: ~100-140ms a frame against ~10ms of skinning), and a
    strip that knows the total can say "12 of 45" instead of an open-ended "rendering...".

    STRIDE CAP: past :data:`MAX_ANIM_FRAMES` rendered frames every ``ceil(n/60)``-th frame is rendered
    instead (the clip census tops out at 200 frames -- ~18-29s unstrided, ~5-9s strided) and the meta
    records ``stride`` so a player can say it is showing ``sample_rate/stride`` fps honestly."""
    from .. import catalog
    m = catalog.model(token)
    if not m:
        return None
    try:
        aid = int(anim_id)
    except (TypeError, ValueError):
        return None

    warm = anim_clip_meta(m.id, aid)
    if warm and all(cached_anim_frame(m.id, aid, f) for f in (warm.get("rendered_frames") or [])):
        touch_anim_clip(m.id, aid)                    # played again -> to the back of the eviction line
        if on_total:
            on_total(len(warm["rendered_frames"]))
        if on_frame:                                  # warm disk: answer from stats alone, no install
            for f in warm["rendered_frames"]:
                on_frame(f, str(anim_frame_path(m.id, aid, f)))
        return warm

    from . import _gltf_io
    from . import anim as manim
    from . import extract, preview
    ctx = ctx if ctx is not None else {}
    didx = 2 if m.group == "WEP" else 4               # weapons live in p0data2 (BattleMap/BattleModel/6)
    if didx not in ctx:
        ctx[didx] = extract._Bundle(None, data_index=didx)
    if "env5" not in ctx:
        try:
            ctx["env5"] = manim._load_env5(None)
        except Exception:   # noqa: BLE001 -- no p0data5 -> no clips to animate, and we say so with None
            ctx["env5"] = None
    env5 = ctx["env5"]
    if env5 is None:
        return None
    if "anim_disc" not in ctx:
        ctx["anim_disc"] = _gltf_io.anim_disc_map(env5)
    loc = catalog.locate_animation(aid, m.id, ctx["anim_disc"])
    if loc is None:
        return None                                   # not on disc for this model (a mint / a phantom row)
    key, folder = loc
    clip = ctx.setdefault("clips", {}).get((folder, key))
    if clip is None:
        clip = _gltf_io.read_clip(env5, folder, key)
        if not clip:
            return None
        ctx["clips"][(folder, key)] = clip
    collected = ctx.setdefault("collect", {}).get(m.name)
    if collected is None:
        collected = extract._collect(m.name, bundle=ctx[didx])
        ctx["collect"][m.name] = collected

    rate = float(clip.get("sample_rate") or 30.0) or 30.0
    n = _frame_count(clip)
    stride = max(1, math.ceil(n / MAX_ANIM_FRAMES))
    frames = list(range(0, n, stride))

    _prune_other_versions(m.id, aid)
    posed, fit = [], None
    for f in frames:
        if should_abort is not None and should_abort():
            return None
        struct = preview._skinned_struct(m.name, collected=collected, env5=env5,
                                         textures=ctx.setdefault("textures", {}).get(m.name),
                                         clip=clip, t=f / rate)
        ctx["textures"].setdefault(m.name, struct.get("textures") or {})
        box = preview.projected_bounds(struct)
        if box is not None:
            fit = box if fit is None else (min(fit[0], box[0]), max(fit[1], box[1]),
                                           min(fit[2], box[2]), max(fit[3], box[3]))
        posed.append((f, struct))

    d = _anim_dir()
    d.mkdir(parents=True, exist_ok=True)
    if on_total:
        on_total(len(posed))
    landed = []
    for f, struct in posed:
        if should_abort is not None and should_abort():
            return None
        png = anim_frame_path(m.id, aid, f)
        if not png.is_file():
            img = preview.render_model(struct, size=MODEL_THUMB, fit=fit)
            tmp = png.with_suffix(".tmp.png")
            img.save(tmp, "PNG", optimize=True)
            tmp.replace(png)
        landed.append(f)
        if on_frame:
            on_frame(f, str(png))
    meta = {"geo": m.name, "id": m.id, "anim": aid, "anim_key": key, "folder": folder,
            "label": catalog.animation_name(aid) or clip.get("name"),
            "frame_count": n, "sample_rate": rate, "stride": stride,
            "fps": rate / stride,                 # the HONEST playback rate: a strided clip is slower
            "fit": list(fit) if fit else None, "rendered_frames": landed}
    anim_meta_path(m.id, aid).write_text(json.dumps(meta), encoding="utf-8")
    prune_anim_cache(keep=(m.id, aid))            # one scan per BUILT clip (never on the warm path)
    return meta


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
        _prune_other_still_versions(m.id)
        meta.write_text(json.dumps({"geo": m.name, "id": m.id, "absent": True, "error": str(e)}),
                        encoding="utf-8")
        return None
    img = preview.render_model(struct, size=MODEL_THUMB)
    png.parent.mkdir(parents=True, exist_ok=True)
    tmp = png.with_suffix(".tmp.png")
    img.save(tmp, "PNG", optimize=True)
    tmp.replace(png)
    _prune_other_still_versions(m.id)
    # WHAT THE PICTURE SHOWS: the clip the still was posed from (None on a rigged model = the rest/bind
    # hierarchy -- a T-pose or a collapsed authoring pose, which a reader should be told is not a stance
    # the game ever shows)
    posed = struct.get("posed_from")
    pose_name = catalog.animation_name(posed[0]) if posed else None
    pose_split = catalog.split_anh(pose_name) if pose_name else None
    info = {"geo": struct.get("geo"), "id": struct.get("geo_id"),
            "bones": len(struct.get("bones") or []),
            "meshes": len(struct.get("meshes") or []),
            "verts": sum(len(me.get("verts") or []) for me in (struct.get("meshes") or [])),
            "textures": sorted(struct.get("textures") or {}),
            "pose": pose_name, "pose_action": pose_split[3] if pose_split else None,
            "pose_rank": catalog.stand_action_rank(pose_split[3]) if pose_split else None}
    meta.write_text(json.dumps(info), encoding="utf-8")
    return str(png)
