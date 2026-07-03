"""Animation-clip round-trip: the return half of "edit the WHOLE model, not just its mesh" -- DLL-free.

THE ENGINE PATH (verified in the pinned build 6b8bb2d5, no DLL): a loose clip dropped at
``<modfolder>/StreamingAssets/Assets/Resources/Animations/{geoId}/{animKey}.anim`` SHADOWS the bundled
p0data5 clip. ``AssetManager.Load<AnimationClip>("Animations/{geoId}/{animKey}")`` probes the mod folders
on disc FIRST (``AssetManager.LoadMultiple`` -> ``LoadFromDisc`` -> ``AnimationClipReader``) and only falls
back to the bundle -- exactly parallel to the loose-FBX MODEL override. The file may be Memoria's own JSON
(first char ``{``) or its binary form; we emit JSON (human-editable, and what the engine's ModelViewer
itself writes via ``ParseToJSON``). The JSON reader keys curves by ``clip.SetCurve(boneName, Transform,
"localRotation.x"|...)`` where ``boneName`` is the bone's FULL HIERARCHY PATH from the Animation root --
because ``ModelImporter.CreateCustomModel`` builds a NESTED ``bone{id:D3}`` skeleton under the base object
(root bones parent to it). That path is exactly the source clip's Unity ``m_RotationCurves[].path``, so we
get it for free by SPLICING edits onto the source clip rather than rebuilding paths.

    JSON schema (``AnimationClipReader.ReadAnimationClip_JSON``):
      {"name","frameRate", "transform":[ {"bone":<path>,
          "localRotation":[{"time","x","y","z","w"}...],   # w only for rotation
          "localPosition":[{"time","x","y","z"}...],
          "localScale":   [{"time","x","y","z"}...] }, ... ]}
    (Tangent keys "xInnerTangent" etc. are read by the BINARY loader but the JSON loader has a TODO and
    IGNORES them -> our JSON keys land with Unity's default tangents, same as an engine ModelViewer save.)

Two authoring surfaces sit on top of this:
  * :func:`deploy_source_anims` -- dump/deploy a model's REAL clips as ``.anim`` JSON (hand-edit the numbers;
    also the Phase-2 loose-override-path proof, faithful minus tangents).
  * :func:`deploy_gltf_anim_edits` -- take a Blender-edited ``.glb`` (the same file the mesh edit loop uses)
    and write back only the clips whose curves actually CHANGED, spliced onto the pristine source clip so
    untouched bones/channels stay byte-faithful. This is what ``model-import`` calls, so ONE edited ``.glb``
    round-trips mesh AND animation.
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

from .. import config
from . import extract, _gltf_io
from .gltf import _icpos, _icquat, _sign_continuous, DEFAULT_SCALE


# ---------------------------------------------------------------- paths / disc helpers

def anim_disc_path(mod_folder, geo_id: int, anim_key: int) -> Path:
    """The engine-probed on-disc override path for one clip (mirrors ``LoadMultiple``'s bundle-asset branch:
    ``GetResourcesBasePath() + "Animations/{geoId}/{key}" + ".anim"`` under a mod's StreamingAssets)."""
    return (Path(mod_folder) / "StreamingAssets" / "Assets" / "Resources"
            / "Animations" / str(int(geo_id)) / f"{int(anim_key)}.anim")


def _load_env5(game=None):
    """Load p0data5 (the animation bundle) with UnityPy -- the source of the real clips we splice onto."""
    return extract._unitypy().load(str(config.find_game_path(game) / "StreamingAssets" / "p0data5.bin"))


def list_clip_keys(env5, geo_id: int) -> list:
    """The on-disc anim KEYS present for a model (``animations/{geoId}/{key}.anim`` in p0data5)."""
    gid = int(geo_id)
    return sorted({int(k.lower().split("/")[-1].removesuffix(".anim"))
                   for k, p in env5.container.items()
                   if p.type.name == "AnimationClip" and f"/animations/{gid}/" in k.lower()})


# ---------------------------------------------------------------- serialization: raw clip -> .anim JSON

def _r(x) -> float:
    """Round to 6 decimals -- quaternions live in [-1,1] (sub-micro) and positions in hundreds of units
    (sub-micron), so 6 dp is lossless for playback while keeping the JSON small + diff-friendly."""
    return round(float(x), 6)


def _frames(curve, ncomp: int) -> list:
    """A [(time,(v0..)) ...] curve -> [{"time","x","y","z"[,"w"]} ...] (the JSON reader's per-frame shape)."""
    axes = ("x", "y", "z", "w")[:ncomp]
    out = []
    for t, v in curve:
        row = {"time": _r(t)}
        for i, ax in enumerate(axes):
            row[ax] = _r(v[i])
        out.append(row)
    return out


def clip_to_anim_json(clip: dict) -> str:
    """A raw FF9 clip struct (as :func:`_gltf_io.read_clip` returns) -> the ``.anim`` JSON text Memoria's
    ``ReadAnimationClip_JSON`` consumes. ``bones`` is keyed by the bone's full hierarchy PATH, which becomes
    the ``"bone"`` field verbatim (that IS the ``SetCurve`` relativePath the engine needs)."""
    transforms = []
    for path, ch in clip.get("bones", {}).items():
        entry = {"bone": path}
        if ch.get("rot"):
            entry["localRotation"] = _frames(ch["rot"], 4)
        if ch.get("pos"):
            entry["localPosition"] = _frames(ch["pos"], 3)
        if ch.get("scale"):
            entry["localScale"] = _frames(ch["scale"], 3)
        transforms.append(entry)
    doc = {"name": clip.get("name") or "custom",
           "frameRate": _r(clip.get("sample_rate", 30.0)),
           "transform": transforms}
    return json.dumps(doc, indent=2)


# ---------------------------------------------------------------- glTF animations -> FF9 raw curves

def _desample(raw: list, interp: str) -> list:
    """glTF sampler output -> one value tuple per keyframe. CUBICSPLINE packs (inTangent,value,outTangent)
    per key, so take the middle; LINEAR/STEP is one-per-key already."""
    if interp == "CUBICSPLINE":
        return [raw[3 * i + 1] for i in range(len(raw) // 3)]
    return raw


def _node_bone_num(node: dict):
    """glTF node -> FF9 bone NUMBER (from its ``boneNNN`` name, tolerating a Blender ``.001`` dedup suffix)."""
    nm = re.sub(r"\.\d+$", "", str(node.get("name") or ""))
    return extract._bone_num(nm)


def parse_gltf_animations(gltf: dict, blob: bytes, *, scale: float = DEFAULT_SCALE) -> list:
    """glTF ``animations`` -> [{"key": int|None, "label": str, "bones": {boneNum: {"rot":[(t,(x,y,z,w))],
    "pos":[(t,(x,y,z))], "scale":[(t,(x,y,z))]}}}], inverting the FF9->glTF conversion (negate-Y is an
    involution, so rotation reuses ``_icquat`` + position ``_icpos``; scale is mirror-invariant). ``key`` is
    the routing anim key from the animation's ``extras.ff9_anim_key`` stamp (or a purely-numeric name)."""
    nodes = gltf.get("nodes", []) or []
    s = float(scale)
    out = []
    for anim in gltf.get("animations", []) or []:
        label = re.sub(r"\.\d+$", "", str(anim.get("name") or "")) or None
        ex = anim.get("extras") or {}
        key = ex.get("ff9_anim_key")
        if key is None and label is not None and re.fullmatch(r"\d+", label):
            key = int(label)
        key = int(key) if key is not None else None
        samplers = anim.get("samplers", []) or []
        bones: dict = {}
        for ch in anim.get("channels", []) or []:
            tgt = ch.get("target") or {}
            ni, pathname = tgt.get("node"), tgt.get("path")
            if ni is None or pathname not in ("rotation", "translation", "scale"):
                continue
            bn = _node_bone_num(nodes[ni]) if ni < len(nodes) else None
            if bn is None:
                continue
            samp = samplers[ch["sampler"]]
            times = [t[0] for t in _gltf_io.decode_accessor(gltf, blob, samp["input"])]
            vals = _desample(_gltf_io.decode_accessor(gltf, blob, samp["output"]),
                             samp.get("interpolation", "LINEAR"))
            b = bones.setdefault(bn, {})
            if pathname == "rotation":
                quats = _sign_continuous([_icquat(list(v)) for v in vals])
                b["rot"] = list(zip(times, [tuple(q) for q in quats]))
            elif pathname == "translation":
                b["pos"] = list(zip(times, [tuple(_icpos(list(v), s)) for v in vals]))
            else:  # scale -- mirror-invariant (per-axis magnitudes), no coordinate flip
                b["scale"] = list(zip(times, [tuple(float(c) for c in v) for v in vals]))
        out.append({"key": key, "label": label, "bones": bones})
    return out


# ---------------------------------------------------------------- splice edits onto the pristine source

def bone_paths(model_bones: list) -> dict:
    """A model's skeleton (read_model ``bones``: name+parent) -> {boneNum: "boneAAA/boneBBB/..."} -- the full
    hierarchy path from the Animation root (a root bone -> just its own name). Covers a bone the source clip
    doesn't animate, so an edit that adds motion to a still bone still gets a correct ``SetCurve`` path."""
    by_name = {b["name"]: b for b in model_bones}

    def path(name):
        b = by_name[name]
        p = b.get("parent")
        return name if not p or p not in by_name else path(p) + "/" + name

    return {extract._bone_num(b["name"]): path(b["name"]) for b in model_bones
            if extract._bone_num(b["name"]) is not None}


def splice_edits_onto_clip(source_clip: dict, edited_bones: dict, *, model_bones=None,
                           warn=None) -> dict:
    """Overlay per-bone edited curves onto a deep copy of ``source_clip`` (keeping every untouched bone +
    channel -- incl. constant position + scale -- byte-faithful). An edited bone is matched to the source by
    bone NUMBER (so its verbatim path is reused); a bone the source clip lacks falls back to the skeleton
    path from ``model_bones``. Returns the merged raw clip ready for :func:`clip_to_anim_json`."""
    clip = copy.deepcopy(source_clip)
    bones = clip.setdefault("bones", {})
    num_to_path = {ch.get("bone"): path for path, ch in bones.items() if ch.get("bone") is not None}
    skel = bone_paths(model_bones) if model_bones else {}
    for bn, edit in edited_bones.items():
        path = num_to_path.get(bn) or skel.get(bn)
        if path is None:
            if warn:
                warn(f"edited bone{bn:03d} has no path in the source clip or skeleton -- skipped")
            continue
        entry = bones.setdefault(path, {"bone": bn})
        for chan in ("rot", "pos", "scale"):
            if chan in edit:
                entry[chan] = edit[chan]
    return clip


def _is_edited(edited_bones: dict, source_clip: dict, *, eps: float = 1e-3) -> bool:
    """True if any glTF-derived (FF9-space) curve DIFFERS from the source clip -> the clip was actually
    edited and is worth overriding. Rotations compare by |dot| (a whole-quaternion sign flip is the SAME
    rotation, so ``_sign_continuous`` re-hemispherising doesn't read as an edit); positions componentwise."""
    num_src = {ch.get("bone"): ch for ch in source_clip.get("bones", {}).values() if ch.get("bone") is not None}
    for bn, edit in edited_bones.items():
        src = num_src.get(bn)
        if src is None:
            return True
        rot = edit.get("rot")
        if rot is not None:
            s = src.get("rot") or []
            if len(rot) != len(s):
                return True
            for (te, qe), (ts, qs) in zip(rot, s):
                if abs(te - ts) > eps:
                    return True
                ne = math.sqrt(sum(a * a for a in qe)) or 1.0
                ns = math.sqrt(sum(a * a for a in qs)) or 1.0
                if abs(sum(a * b for a, b in zip(qe, qs))) / (ne * ns) < 1.0 - eps:   # normalized -> cos angle
                    return True
        pos = edit.get("pos")
        if pos is not None:
            s = src.get("pos") or []
            if len(pos) != len(s):
                return True
            for (te, pe), (ts, ps) in zip(pos, s):
                if abs(te - ts) > eps or any(abs(a - b) > eps * 100 for a, b in zip(pe, ps)):
                    return True
    return False


# ---------------------------------------------------------------- orchestrators (I/O)

def _resolve_geo_id(gltf: dict, geo, geo_id, *, game=None) -> tuple:
    """Resolve (geo_id, geo_name) for a return-path write: explicit --id / --like win, else the glTF's
    ``asset.extras`` stamp (any file we exported)."""
    stamp = (gltf.get("asset") or {}).get("extras") or {}
    if geo_id is None and geo is not None:
        _, geo_id, _ = extract.resolve_geo(geo)
    if geo_id is None:
        geo_id = stamp.get("ff9_geo_id")
    if geo_id is None:
        raise ValueError("can't route the edited animations: no target model id (pass --like <GEO> / --id, "
                         "or edit a glTF we exported -- it stamps ff9_geo_id)")
    name = geo or stamp.get("ff9_geo") or extract.MODELS.get(int(geo_id))
    return int(geo_id), name


def deploy_source_anims(token: str, mod_folder, *, which="all", game=None) -> dict:
    """Dump a model's REAL clips (or a subset) as loose ``.anim`` JSON into ``mod_folder`` -- the hand-edit
    surface AND the Phase-2 loose-override-path proof (each is the bundled clip, faithful minus tangents).
    ``which`` = "all" or an iterable / comma-space string of anim KEYS."""
    geo, geo_id, _ = extract.resolve_geo(token)
    env5 = _load_env5(game)
    keys = list_clip_keys(env5, geo_id)
    if which not in ("all", None, ""):
        want = {int(t) for t in str(which).replace(",", " ").split()} if isinstance(which, str) \
            else {int(x) for x in which}
        keys = [k for k in keys if k in want]
    written = []
    for k in keys:
        clip = _gltf_io.read_clip(env5, geo_id, k)
        if not clip or not clip.get("bones"):
            continue
        p = anim_disc_path(mod_folder, geo_id, k)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(clip_to_anim_json(clip), encoding="utf-8", newline="\n")
        written.append(str(p))
    return {"geo": geo, "geo_id": geo_id, "written": written, "keys": keys}


def deploy_gltf_anim_edits(gltf_path, mod_folder, *, geo=None, geo_id=None, scale=None,
                           game=None, force=False) -> dict:
    """Write back the animations from a Blender-edited ``.glb`` as loose ``.anim`` overrides: parse each
    glTF animation, splice its changed curves onto the pristine source clip, and (unless ``force``) skip any
    clip whose curves are unchanged so untouched clips keep playing the byte-faithful bundled version.
    Returns {"written":[paths], "skipped":[(key,reason)|label], "geo_id"}."""
    gltf, blob = _gltf_io.read_glb(gltf_path)
    if not gltf.get("animations"):
        return {"written": [], "skipped": [], "geo_id": geo_id, "no_anims": True}
    stamp = (gltf.get("asset") or {}).get("extras") or {}
    if scale is None:
        scale = float(stamp.get("ff9_scale", DEFAULT_SCALE))
    gid, geo_name = _resolve_geo_id(gltf, geo, geo_id, game=game)
    model_bones = None
    try:
        model_bones = extract.read_model(geo_name or gid, game=game)["bones"]
    except (RuntimeError, FileNotFoundError, ValueError, KeyError):
        pass
    env5 = _load_env5(game)
    written, skipped = [], []
    for pa in parse_gltf_animations(gltf, blob, scale=scale):
        key = pa["key"]
        if key is None:
            skipped.append(pa["label"] or "<unnamed>")
            continue
        source_clip = _gltf_io.read_clip(env5, gid, key) or {"name": pa["label"], "sample_rate": 30.0, "bones": {}}
        if not force and not _is_edited(pa["bones"], source_clip):
            skipped.append((key, "unchanged"))
            continue
        merged = splice_edits_onto_clip(source_clip, pa["bones"], model_bones=model_bones)
        p = anim_disc_path(mod_folder, gid, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(clip_to_anim_json(merged), encoding="utf-8", newline="\n")
        written.append(str(p))
    return {"written": written, "skipped": skipped, "geo_id": gid}
