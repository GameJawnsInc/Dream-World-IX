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
    # Fallback routing: if Blender dropped an animation's extras, the numeric-name fallback fails for a
    # FRIENDLY-named Action ("idle1"/"run"/"fly_cho" -- what the exporter now writes). Resolve the label to its
    # on-disc key from each on-disc clip's OWN ANH name (e.g. ANH_SUB_W0_001_IDLE1 -> "idle1" -> 4716) -- NOT via
    # animations_for_model, whose catalog id != the on-disc key for world models (that mismatch silently dropped
    # the edit). This is the exact inverse of the exporter's label derivation, so a round-trip resolves.
    label_to_key = {}
    try:
        from .. import catalog
        for k in list_clip_keys(env5, gid):
            nm = catalog.animation_name(k)                    # ANH_SUB_W0_001_IDLE1
            parts = nm.split("_") if nm else []
            if len(parts) >= 5:                               # ANH <group> <form> <token> <ACTION...>
                label_to_key.setdefault("_".join(parts[4:]).lower(), k)
        for lbl, k in (catalog.animations_for_model(geo_name) or {}).items():
            label_to_key.setdefault(str(lbl).lower(), k)      # also accept a catalog action label -> its id
    except Exception:   # noqa: BLE001  -- catalog/install optional; fallback is best-effort
        pass
    written, skipped, warnings = [], [], []
    # GROUP the parsed animations by their resolved clip key first. A scene with the model imported more than
    # once stacks duplicate actions (run.001 ...) that all route to the same key; writing them in order would
    # let a pristine/re-sampled duplicate CLOBBER the user's edit last-wins. Instead, per key, pick an EDITED
    # candidate (so the real edit beats the pristine copies) and write each key exactly once.
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
        by_key.setdefault(key, []).append(pa)
    for key, group in by_key.items():
        source_clip = _gltf_io.read_clip(env5, gid, key) or {"name": str(key), "sample_rate": 30.0, "bones": {}}
        edited = group if force else [pa for pa in group if _is_edited(pa["bones"], source_clip)]
        if not edited:
            skipped.append((key, "unchanged"))                       # every copy matches the source -> keep bundled
            continue
        if len(group) > 1:
            warnings.append(f"{len(group)} animations map to key {key} ({len(edited)} edited) -- "
                            f"using the edited one" + (" (last of several)" if len(edited) > 1 else ""))
        merged = splice_edits_onto_clip(source_clip, edited[-1]["bones"], model_bones=model_bones,
                                        warn=warnings.append)
        p = anim_disc_path(mod_folder, gid, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(clip_to_anim_json(merged), encoding="utf-8", newline="\n")
        written.append(str(p))
    return {"written": written, "skipped": skipped, "warnings": warnings, "geo_id": gid}
