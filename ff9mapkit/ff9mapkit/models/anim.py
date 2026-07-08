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

from .. import catalog, config
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

# Edit-detection thresholds, set just above the MEASURED float32 round-trip noise floor (a diverse
# 31.7k-bone sweep: rotation 1-|dot| ~2e-16 -- quadratic in the component error, so effectively machine
# eps -- and position ~9e-5 units). A false POSITIVE is cheap (the override is a faithful splice of the
# source, plays ~identically), so we bias sensitive; a false NEGATIVE silently drops a real edit, which is
# the failure to avoid. rot 1e-6 => ~0.16deg dead zone (was 1e-3 => ~5.1deg, a real bug the review caught).
_EPS_TIME = 1e-4     # seconds (keys sit at 1/30s; tolerates Blender's tiny time re-quantization)
_EPS_ROT = 1e-6      # on (1 - normalized|dot|); ~0.16deg, ~1e10 above the noise floor
_EPS_POS = 5e-3      # FF9 units; ~55x above the 9e-5 noise floor, still sub-visible
_EPS_SCALE = 1e-4    # scale ~1.0; catches a 0.01% size change


def _r(x) -> float:
    """Round to 6 decimals -- quaternions live in [-1,1] (sub-micro) and positions in hundreds of units
    (sub-micron), so 6 dp is lossless for playback while keeping the JSON small + diff-friendly. REJECTS a
    non-finite value (fail loud rather than emit NaN/Infinity -- invalid JSON the engine's SimpleJSON reads
    as a culture-dependent 0/garbage; a NaN only reaches here from a corrupt glTF, so surfacing it is right)."""
    x = float(x)
    if not math.isfinite(x):
        raise ValueError(f"non-finite animation value {x!r} -- refusing to write invalid JSON (corrupt glTF?)")
    return round(x, 6)


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


def _sample_curve(curve: list, t: float):
    """Linear-interpolate a piecewise-linear curve [(time, value_tuple)...] at time ``t`` (clamped at the
    ends). FF9 clips + the engine both interpolate per-component linearly, so this is exact between keys."""
    if not curve:
        return None
    if t <= curve[0][0]:
        return curve[0][1]
    if t >= curve[-1][0]:
        return curve[-1][1]
    for i in range(1, len(curve)):
        t0, v0 = curve[i - 1]
        t1, v1 = curve[i]
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(a + (b - a) * f for a, b in zip(v0, v1))
    return curve[-1][1]


def _curve_changed(edit_curve, src_curve, kind: str) -> bool:
    """Did an edited channel MEANINGFULLY differ from the source? Compares the two curves by their sampled
    MOTION -- at the union of both curves' key times (exact for piecewise-linear) -- NOT by key count/layout.
    So Blender's re-sampling (which changes the keyframe count but preserves the motion) reads as UNCHANGED,
    while a real pose edit reads as changed. ``kind`` in {rot, pos, scale}; rotation compares by normalized
    |dot| (sign-flip-safe), position/scale componentwise, each against its noise-floor epsilon."""
    e, s = edit_curve or [], src_curve or []
    if bool(e) != bool(s):                       # one curve has the channel, the other doesn't -> a change
        return True
    if not e:
        return False
    eps = {"rot": _EPS_ROT, "pos": _EPS_POS, "scale": _EPS_SCALE}[kind]
    for t in sorted({tv for tv, _ in e} | {tv for tv, _ in s}):
        ve, vs = _sample_curve(e, t), _sample_curve(s, t)
        if kind == "rot":
            ne = math.sqrt(sum(a * a for a in ve)) or 1.0
            ns = math.sqrt(sum(a * a for a in vs)) or 1.0
            if 1.0 - abs(sum(a * b for a, b in zip(ve, vs))) / (ne * ns) > eps:
                return True
        elif any(abs(a - b) > eps for a, b in zip(ve, vs)):
            return True
    return False


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
            # Replace only a channel that actually CHANGED -- an untouched channel (or one Blender merely
            # re-sampled to the same motion) keeps the source's byte-faithful keys, so a mesh/one-bone edit
            # doesn't rewrite every bone with Blender's resampled version.
            if chan in edit and _curve_changed(edit.get(chan), entry.get(chan), chan):
                entry[chan] = edit[chan]
    return clip


def _is_edited(edited_bones: dict, source_clip: dict) -> bool:
    """True if any glTF-derived (FF9-space) curve MEANINGFULLY differs from the source clip -> the clip was
    actually edited and is worth overriding. Compares by sampled MOTION (see :func:`_curve_changed`), so it
    is robust to Blender re-sampling the keyframe count while preserving the motion; only a channel the edit
    actually carries is checked (the exporter drops constant position/scale, which is not an edit)."""
    num_src = {ch.get("bone"): ch for ch in source_clip.get("bones", {}).values() if ch.get("bone") is not None}
    for bn, edit in edited_bones.items():
        src = num_src.get(bn)
        if src is None:
            return True                                              # a bone the source clip doesn't animate
        for chan in ("rot", "pos", "scale"):
            if chan in edit and _curve_changed(edit.get(chan), src.get(chan), chan):
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
    ``which`` = "all" (every clip in the model's OWN folder) or an iterable / comma-space string of anim
    KEYS -- an explicitly requested key that lives in a DONOR model's folder (the engine's AnimationDB
    name-token redirect, e.g. BBA's idle=560 in Animations/112/) is located + dumped at that real path,
    sibling-resolving duplicate ids; a key found nowhere lands in ``missing``."""
    geo, geo_id, _ = extract.resolve_geo(token)
    env5 = _load_env5(game)
    missing: list = []
    if which in ("all", None, ""):
        targets = [(k, geo_id) for k in list_clip_keys(env5, geo_id)]
    else:
        want = [int(t) for t in str(which).replace(",", " ").split()] if isinstance(which, str) \
            else [int(x) for x in which]
        disc = _gltf_io.anim_disc_map(env5)
        targets = []
        for w in dict.fromkeys(want):                          # keep request order, drop dups
            loc = catalog.locate_animation(w, geo_id, disc)
            if loc:
                targets.append(loc)
            else:
                missing.append(w)
    written = []
    for k, folder in targets:
        clip = _gltf_io.read_clip(env5, folder, k)
        if not clip or not clip.get("bones"):
            continue
        p = anim_disc_path(mod_folder, folder, k)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(clip_to_anim_json(clip), encoding="utf-8", newline="\n")
        written.append(str(p))
    return {"geo": geo, "geo_id": geo_id, "written": written, "keys": [k for k, _ in targets],
            "missing": missing}


class AnimsetError(RuntimeError):
    """A minted battle animset couldn't ship a clip its serial row + directives already reference (would freeze)."""


def deploy_battle_animset(dest_geo_id: int, clips, mod_folder, *, game=None) -> list:
    """Give a MINTED battle model its own independent animset: for each ``(src_geo_id, src_key, dst_key)``, read the
    source clip from ITS OWN p0data5 folder (the anim's embedded token, which may differ from the row's ModelId) and
    write it as faithful ``.anim`` JSON at ``Animations/<dest_geo_id>/<dst_key>.anim`` under ``mod_folder``. The
    copies are byte-faithful to the donor (the character animates identically until edited), but they live in the
    MINTED model's own folder, so editing them never touches the donor's ``Animations/<src_geo_id>/`` clips.

    FAIL-LOUD: every ``(src, dst)`` the planner listed is ALSO referenced by the already-emitted serial row + its
    ``3DModelAnimation`` registration, and a MISSING clip freezes that motion in-battle (btl_mot.cs:226). So an
    unreadable source clip raises :class:`AnimsetError` rather than silently shipping an incomplete (freezing) set.
    Returns the written paths (one per clip)."""
    env5 = _load_env5(game)
    written = []
    for src_geo_id, src_key, dst_key in clips:
        clip = _gltf_io.read_clip(env5, int(src_geo_id), int(src_key))
        if not clip or not clip.get("bones"):
            raise AnimsetError(f"custom_battle_anims: source clip Animations/{int(src_geo_id)}/{int(src_key)} is "
                               f"missing/empty -- refusing to register a battle motion with no clip (would freeze "
                               f"the battle). The serial row + 3DModelAnimation already reference it.")
        p = anim_disc_path(mod_folder, int(dest_geo_id), int(dst_key))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(clip_to_anim_json(clip), encoding="utf-8", newline="\n")
        written.append(str(p))
    return written


def deploy_battle_animset_edits(clips, dest_geo_id: int, gltf_path, mod_folder, *, scale=None, game=None,
                                label_keys=None) -> dict:
    """The Blender edit loop for a MINTED battle animset: route a donor-model ``.glb`` (exported with
    ``model-gltf <donor GEO> --anims all`` and edited in Blender) onto the 13th character's OWN animset. For EVERY
    ``(src_geo_id, src_key, dst_key)`` in the plan's ``clips`` it writes ``Animations/<dest_geo_id>/<dst_key>.anim``
    -- the ``.glb``'s EDITED clip where a curve actually changed (spliced onto the pristine source so untouched
    bones stay byte-faithful), else a FAITHFUL copy of the source. So the minted animset stays COMPLETE (every
    motion has a clip -> no freeze) and only the edited motions differ from the donor; the donor's own
    ``Animations/<src_geo_id>/`` is never written. Returns ``{written, edited, faithful, warnings, dest_geo_id}``.

    Editing lives entirely in the MINT folder, so it composes with :func:`deploy_battle_animset` (the build's
    faithful seed) -- re-running this after a build simply overwrites the changed clips."""
    gltf, blob = _gltf_io.read_glb(gltf_path)
    stamp = (gltf.get("asset") or {}).get("extras") or {}
    if scale is None:
        scale = float(stamp.get("ff9_scale", DEFAULT_SCALE))
    env5 = _load_env5(game)
    # the plan's clips share one source model (the anim token's folder); read its bones for the splice fallback
    model_bones = None
    src_ids = {int(sg) for sg, _sk, _dk in clips}
    if len(src_ids) == 1:
        try:
            gid = next(iter(src_ids))
            model_bones = extract.read_model(extract.MODELS.get(gid) or gid, game=game)["bones"]
        except (RuntimeError, FileNotFoundError, ValueError, KeyError):
            pass
    # parse the glb -> edits keyed by the SOURCE clip key (ff9_anim_key stamp, or an action-name fallback if
    # Blender dropped the stamp -- which it DOES on re-export); ignore any animation not part of this playable's
    # animset. ``label_keys`` (e.g. the friendly "23_attack"->key motion map the exporter named Actions with) is
    # the PRIMARY name fallback, since Blender preserves the Action NAME but not the glTF extras.
    plan_src_keys = {int(sk) for _sg, sk, _dk in clips}
    label_to_key = {}
    for lbl, k in (label_keys or {}).items():
        label_to_key.setdefault(str(lbl).lower(), int(k))
    try:
        from .. import catalog
        for _sg, sk, _dk in clips:
            parts = (catalog.animation_name(sk) or "").split("_")
            if len(parts) >= 5:
                label_to_key.setdefault("_".join(parts[4:]).lower(), int(sk))
    except Exception:   # noqa: BLE001  -- catalog optional; the ff9_anim_key stamp is the primary route
        pass
    edits_by_key: dict = {}
    n_glb_anims, matched, warnings = 0, 0, []
    for pa in parse_gltf_animations(gltf, blob, scale=scale):
        n_glb_anims += 1
        key = pa["key"]
        if key is None and pa["label"]:
            key = label_to_key.get(pa["label"].lower())
        if key is None:                                    # a renamed Blender Action with a dropped ff9_anim_key
            warnings.append(f"glb animation {pa['label'] or '<unnamed>'!r} has no routable key -- NOT applied (keep "
                            f"the exported Action name, e.g. 'attack'/'idle1', or its numeric anim key)")
            continue
        if int(key) in plan_src_keys:
            edits_by_key.setdefault(int(key), []).append(pa)
            matched += 1
        # else: a resolved key OUTSIDE this animset (an extra clip from `--anims all`) -> legitimately ignored
    written, edited_keys, faithful_keys = [], [], []
    for src_geo_id, src_key, dst_key in clips:
        source_clip = _gltf_io.read_clip(env5, int(src_geo_id), int(src_key))
        if not source_clip or not source_clip.get("bones"):
            raise AnimsetError(f"custom_battle_anims: source clip Animations/{int(src_geo_id)}/{int(src_key)} is "
                               f"missing/empty -- can't build the animset (would freeze the battle).")
        group = [pa for pa in edits_by_key.get(int(src_key), []) if _is_edited(pa["bones"], source_clip)]
        if group:                                          # a genuinely-edited clip -> splice the changed curves
            merged = splice_edits_onto_clip(source_clip, group[-1]["bones"], model_bones=model_bones,
                                            warn=warnings.append)
            edited_keys.append(int(src_key))
        else:                                              # untouched -> faithful copy (keeps the animset complete)
            merged = source_clip
            faithful_keys.append(int(src_key))
        p = anim_disc_path(mod_folder, int(dest_geo_id), int(dst_key))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(clip_to_anim_json(merged), encoding="utf-8", newline="\n")
        written.append(str(p))
    return {"written": written, "edited": edited_keys, "faithful": faithful_keys, "warnings": warnings,
            "dest_geo_id": int(dest_geo_id), "matched": matched, "glb_anims": n_glb_anims}


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
    disc = _gltf_io.anim_disc_map(env5)                       # {folder_id: set(key)} -- the physical layout
    # Fallback routing: if Blender dropped an animation's extras, the numeric-name fallback fails for a
    # FRIENDLY-named Action ("idle1"/"run"/"fly_cho" -- what the exporter now writes). Resolve the label to its
    # on-disc key from each on-disc clip's OWN ANH name (e.g. ANH_SUB_W0_001_IDLE1 -> "idle1" -> 4716), then
    # accept a catalog action label -> its id (a DONOR-folder action like BBA's 'idle'=560; the locate below
    # settles which folder + same-name sibling actually exists on disc).
    label_to_key = {}
    try:
        for k in sorted(disc.get(gid) or ()):
            nm = catalog.animation_name(k)                    # ANH_SUB_W0_001_IDLE1
            parts = nm.split("_") if nm else []
            if len(parts) >= 5:                               # ANH <group> <form> <token> <ACTION...>
                label_to_key.setdefault("_".join(parts[4:]).lower(), k)
        for lbl, k in (catalog.animations_for_model(geo_name) or {}).items():
            label_to_key.setdefault(str(lbl).lower(), k)      # also accept a catalog action label -> its id
    except Exception:   # noqa: BLE001  -- label fallback is best-effort; the ff9_anim_key stamp still routes
        pass
    written, skipped, warnings, written_folders = [], [], [], set()
    # GROUP the parsed animations by their resolved clip (key, folder) first. A scene with the model imported
    # more than once stacks duplicate actions (run.001 ...) that all route to the same clip; writing them in
    # order would let a pristine/re-sampled duplicate CLOBBER the user's edit last-wins. Instead, per clip,
    # pick an EDITED candidate (so the real edit beats the pristine copies) and write each clip exactly once.
    # A clip is routed to the folder the ENGINE reads it from (catalog.locate_animation: own folder, else the
    # AnimationDB name-token redirect to a DONOR folder, sibling-resolving duplicate ids) -- an override
    # written under the wrong folder is silently dead. An unlocatable key (a minted custom clip not in the
    # bundle) keeps the model's own folder, where deploy_new_anim ships it.
    by_key: dict = {}
    for pa in parse_gltf_animations(gltf, blob, scale=scale):
        key = pa["key"]
        if key is None and pa["label"]:
            key = label_to_key.get(pa["label"].lower())
        if key is None:
            warnings.append(f"animation {pa['label'] or '<unnamed>'!r} has no routable key -- NOT written "
                            f"(unrecognized Action name and no ff9_anim_key stamp; keep the exported name, "
                            f"e.g. 'idle1'/'run', or its numeric anim key)")
            skipped.append(pa["label"] or "<unnamed>")
            continue
        loc = catalog.locate_animation(key, gid, disc)
        by_key.setdefault(loc if loc else (int(key), gid), []).append(pa)
    for (key, folder), group in by_key.items():
        source_clip = _gltf_io.read_clip(env5, folder, key) or {"name": str(key), "sample_rate": 30.0, "bones": {}}
        edited = group if force else [pa for pa in group if _is_edited(pa["bones"], source_clip)]
        if not edited:
            skipped.append((key, "unchanged"))                       # every copy matches the source -> keep bundled
            continue
        if len(group) > 1:
            warnings.append(f"{len(group)} animations map to key {key} ({len(edited)} edited) -- "
                            f"using the edited one" + (" (last of several)" if len(edited) > 1 else ""))
        merged = splice_edits_onto_clip(source_clip, edited[-1]["bones"], model_bones=model_bones,
                                        warn=warnings.append)
        if folder != gid:
            donor = catalog.model(folder)
            warnings.append(f"Animations/{folder}/{key}.anim is a SHARED donor-folder clip "
                            f"({donor.name if donor else f'model {folder}'}'s) -- the engine reads it for "
                            f"every model that plays it, not just {geo_name or gid}")
        p = anim_disc_path(mod_folder, folder, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(clip_to_anim_json(merged), encoding="utf-8", newline="\n")
        written.append(str(p))
        written_folders.add(folder)
    return {"written": written, "skipped": skipped, "warnings": warnings, "geo_id": gid,
            "folders": sorted(written_folders) or [gid]}


# ---------------------------------------------------------------- wholly NEW clips (not edits)

_NEW_ANIM_KEY_BASE = 60_000      # fresh AnimationDB keys for NEW custom clips. A FIELD anim id is 16-bit
_NEW_ANIM_KEY_MAX = 65_535       # END TO END -- the .eb anim-setter args are u16 AND the engine's
                                 # Actor.idle/walk/run/turnl/turnr are UInt16 -- so a field-playable key
                                 # MUST fit <= 65535 (stock keys top out at 14739; 60000-65535 is the mint
                                 # band). The old 2M base silently TRUNCATED in the .eb (2001000 -> 34920),
                                 # the engine looked up a key nobody registered, and NO clip attached. The
                                 # battle-animset band (1M+) is battle-only: btl mot[] is Int32. Registered
                                 # per clip via a `3DModelAnimation <key> <ANH name>` DictionaryPatch line
                                 # at launch.


def new_clip(model_bones: list, bone_curves: dict, *, name: str = "custom",
             sample_rate: float = 30.0, warn=None) -> dict:
    """A wholly NEW raw clip struct from per-bone-NUMBER curves (no source clip -- the from-scratch path,
    vs :func:`splice_edits_onto_clip` which overlays edits on a real donor). Bone paths come from the
    model's own skeleton (:func:`bone_paths`) -- the full hierarchy path the engine's ``SetCurve`` needs.
    ``bone_curves`` = ``{boneNum: {"rot":[(t,(x,y,z,w))...], "pos":..., "scale":...}}`` (what
    :func:`parse_gltf_animations` returns per animation).

    Every skeleton bone the caller leaves unkeyed gets a STATIC rest-pose channel (rot+pos+scale, 2 keys),
    matching real FF9 clips, which key all bones even for a 1-frame pose. Load-bearing: playback only
    resets the bones a clip keys, and the engine COMPOSES the head-focus look offset onto the neck bone
    every LateUpdate (`FieldMapActorController.UpdateNeck`) -- an unkeyed neck accumulates it into a
    continuously spinning head. Rest TRS comes from ``model_bones`` (:func:`extract.read_model` pos/rot/
    scale); a bones list without them falls back to the identity transform."""
    paths = bone_paths(model_bones)
    bones: dict = {}
    length = 0.0
    for bn, curves in sorted(bone_curves.items()):
        path = paths.get(bn)
        if path is None:
            if warn:
                warn(f"new clip {name!r}: bone{bn:03d} is not in the model's skeleton -- skipped")
            continue
        entry = {"bone": bn}
        for chan in ("rot", "pos", "scale"):
            if curves.get(chan):
                entry[chan] = curves[chan]
                length = max(length, curves[chan][-1][0])
        if len(entry) > 1:
            bones[path] = entry
    if not bones:
        raise AnimError(f"new clip {name!r} has no usable bone curves")
    length = length if length > 0 else 1.0 / float(sample_rate)
    rest = {extract._bone_num(b["name"]): b for b in model_bones}
    rest_of = {"rot": lambda b: tuple(b.get("rot") or (0.0, 0.0, 0.0, 1.0)),
               "pos": lambda b: tuple(b.get("pos") or (0.0, 0.0, 0.0)),
               "scale": lambda b: tuple(b.get("scale") or (1.0, 1.0, 1.0))}
    for bn, path in paths.items():
        entry = bones.setdefault(path, {"bone": bn})
        for chan, rest_val in rest_of.items():
            if not entry.get(chan):
                v = rest_val(rest[bn])
                entry[chan] = [(0.0, v), (length, v)]
    return {"name": name, "sample_rate": float(sample_rate), "length": length, "bones": bones}


def synth_spin_curves(*, frames: int = 48, sample_rate: float = 30.0, bone: int = 0, rest=None) -> dict:
    """A synthesized demo clip: the root bone yaws a full 360 over ``frames`` -- the no-Blender proof of
    the new-clip mechanism (mint key + registration + loose .anim + field playback). ``rest`` is the bone's
    rest localRotation (x,y,z,w): the yaw COMPOSES onto it in the parent frame (``q = yaw * rest``). A raw
    yaw would STOMP a non-identity rest -- e.g. BBA's bone000 rest is itself a -90-degree yaw."""
    import math
    rx, ry, rz, rw = rest or (0.0, 0.0, 0.0, 1.0)
    rot = []
    for f in range(frames + 1):
        half = math.pi * (f / frames)           # half-angle of a 0..360-degree yaw
        ys, yc = math.sin(half), math.cos(half)
        q = (yc * rx + ys * rz, yc * ry + ys * rw,      # Hamilton product (0,ys,0,yc) * rest
             yc * rz - ys * rx, yc * rw - ys * ry)
        rot.append((f / sample_rate, q))
    return {bone: {"rot": rot}}


class AnimError(ValueError):
    pass


def _anim_key_registry(dp: "Path") -> dict:
    """The mod folder's ``3DModelAnimation <key> <name>`` registrations -> {key: name}."""
    reg: dict = {}
    if dp.exists():
        for ln in dp.read_text(encoding="utf-8").splitlines():
            parts = ln.split()
            if len(parts) == 3 and parts[0] == "3DModelAnimation" and parts[1].isdigit():
                reg[int(parts[1])] = parts[2]
    return reg


def _resolve_minted_model(token: str, mod_folder) -> tuple:
    """A MINTED model token (name or id) -> (geo_name, geo_id) via the mod folder's ``3DModel`` lines --
    the same registry the engine extends FF9BattleDB.GEO from at startup. Raises with a pointer at the
    [[mint]] step when the token is neither stock nor registered here."""
    dp = Path(mod_folder) / "DictionaryPatch.txt"
    mints: dict = {}
    if dp.exists():
        for ln in dp.read_text(encoding="utf-8").splitlines():
            parts = ln.split()
            if len(parts) == 3 and parts[0] == "3DModel" and parts[1].isdigit():
                mints[int(parts[1])] = parts[2]
    tok = str(token).strip()
    if tok.isdigit() and int(tok) in mints:
        return mints[int(tok)], int(tok)
    for mid, name in mints.items():
        if name.upper() == tok.upper():
            return name, mid
    raise AnimError(f"unknown model {token!r}: not a stock GEO name/id and no `3DModel` line for it in "
                    f"{dp} -- for a minted model, deploy its [[mint]] first, then mint clips for it")


def deploy_new_anim(model_token: str, clip: dict, mod_folder, *, key: "int | None" = None,
                    suffix: str = "CUSTOM1", game=None) -> dict:
    """Ship one NEW clip for a model: write ``Animations/<geoId>/<key>.anim`` (loose, engine-probed) and
    register it with an idempotent ``3DModelAnimation <key> <ANH name>`` DictionaryPatch line. The ANH name
    carries the MODEL's own group/form/token (that's how ``GetRenameAnimationPath`` routes the name to this
    model's clip folder). Play it anywhere an anim id goes: ``[[npc]] anims = { stand = <key> }``, a
    cutscene ``animation`` step, ... RELAUNCH to register (DictionaryPatch loads at startup).

    ``key=None`` reuses the key already registered to this ANH name (idempotent re-deploy) or allocates
    the next free key in the 16-bit-safe 60000-65535 band; an explicit key must fit 16 bits too (a field
    anim id is u16 in both the .eb and the engine -- an oversized key silently truncates and never
    attaches). Re-registering a key REPLACES its line (a duplicate key would double-Add in AnimationDB).

    ``model_token`` may be a MINTED model (a ``3DModel`` line in this mod folder's DictionaryPatch --
    the same registry the engine learns mints from at startup): deploy the ``[[mint]]`` first, then
    mint clips for it; the clip folder is the minted id's (``GetRenameAnimationDirectory`` resolves the
    minted name through the runtime-extended GEO table exactly like a stock one)."""
    from . import extract
    try:
        geo, gid, _tint = extract.resolve_geo(str(model_token))
    except ValueError:
        geo, gid = _resolve_minted_model(str(model_token), mod_folder)
    parts = geo.split("_")                        # GEO <grp> <form> <token>
    if len(parts) < 4:
        raise AnimError(f"can't derive an ANH name from {geo!r}")
    sfx = "".join(ch for ch in str(suffix).upper() if ch.isalnum() or ch == "_")
    if not sfx:
        raise AnimError(f"bad anim name suffix {suffix!r} (letters/digits/underscore)")
    anh = f"ANH_{parts[1]}_{parts[2]}_{parts[3]}_{sfx}"
    from .._animdb_all import ANIMATIONS as _stock
    if anh in set(_stock.values()):
        # AnimationDB is a TwoWayDictionary: re-registering a REAL clip name at a new key hijacks the
        # stock name->key lookup (folder derivation goes through TryGetKey(name)) and mis-routes the
        # real clip. e.g. --suffix B on BBA collides with her stock pose ANH_NPC_F1_BBA_B.
        raise AnimError(f"{anh} is a real FF9 clip name -- pick a different suffix "
                        f"(registering it at a new key would hijack the stock name->key lookup)")
    dp = Path(mod_folder) / "DictionaryPatch.txt"
    registered = _anim_key_registry(dp)
    if key is not None:
        k = int(key)
        if not 0 < k <= _NEW_ANIM_KEY_MAX:
            raise AnimError(f"anim key {k} does not fit a field anim slot (16-bit, max {_NEW_ANIM_KEY_MAX}"
                            f") -- the .eb and the engine would silently truncate it and no clip would "
                            f"attach; mint keys in the {_NEW_ANIM_KEY_BASE}-{_NEW_ANIM_KEY_MAX} band")
    else:
        k = next((kk for kk, nm in registered.items() if nm == anh), None)   # re-deploy reuses its key
        if k is None:
            k = _NEW_ANIM_KEY_BASE
            while k in registered:
                k += 1
            if k > _NEW_ANIM_KEY_MAX:
                raise AnimError(f"no free anim key left in {_NEW_ANIM_KEY_BASE}-{_NEW_ANIM_KEY_MAX} "
                                f"(this folder's DictionaryPatch registers them all)")
    dest = anim_disc_path(mod_folder, gid, k)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(clip_to_anim_json(clip), encoding="utf-8", newline="\n")
    directive = f"3DModelAnimation {k} {anh}"
    lines = dp.read_text(encoding="utf-8").splitlines() if dp.exists() else []
    if directive not in lines:
        # replace, never dup: a duplicate KEY double-Adds in AnimationDB; a duplicate NAME (same clip
        # re-registered at an explicit new key) leaves a stale name->key row shadowing the new one
        lines = [ln for ln in lines if not ln.startswith(f"3DModelAnimation {k} ")
                 and not (ln.startswith("3DModelAnimation ") and ln.endswith(f" {anh}"))]
        lines.append(directive)
        dp.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return {"geo": geo, "geo_id": gid, "key": k, "name": anh, "path": str(dest),
            "directive": directive, "dictionary_patch": str(dp)}
