"""Resolve a re-skin's DONOR -- a real battle enemy whose model+animation block we transplant.

A re-skin makes a forked enemy's BODY look like a different creature while keeping its own gameplay. The visual
identity is a self-consistent group of SB2_MON_PARM fields (Geo + the six Mot animation ids + Mesh + Radius +
the model-attached cosmetics -- see :data:`scene_data._RESKIN_RANGES`), so it can't be set field-by-field: a
Mot id that doesn't belong to the loaded Geo names a clip the model lacks, and the battle FREEZES
(`btl_init.cs:240`/`:521-522`). The only safe source is a real enemy that ALREADY uses the target model --
Square-Enix shipped that whole block together, so it is guaranteed engine-valid.

SCOPE -- this is a BODY re-skin, NOT a full one (★ IN-GAME PROVEN 2026-06-13). The transplanted Mot[6] DO drive
the new model's OWN idle / damage / death animations (`btl_init.cs:240`); but the per-ATTACK animation is bound
by the donor SCENE's raw17 btlseq (keyed by the per-type Konran@78 selector, `btlseq.cs:1150-1151`), which a
re-skin KEEPS -- so the ATTACK plays the TARGET enemy's clip, RETARGETED onto the new mesh (clip load path is by
clip NAME, `AnimationFactory.cs:60`, so the cross-model retarget never crashes). Proven: a Goblin re-skinned to
the Fang IDLED as a quadruped Fang but KNIFED / Goblin-Punched with the Goblin's upright animation. So the body
looks like the new creature at rest / when hit / dying, but its ATTACK gesture stays the target's. A faithful
FULL re-skin would also need the donor's raw17 attack binding + AA_DATA -- the deferred raw17-sequence work. The
build warns per re-skinned slot.

This module reads the donor block LIVE from the user's install (provenance: never committed; only the kit's
open-source name->geo catalog ships). Two donor specs:
  * ``{"scene": "EF_R007", "type": 0}`` -- an explicit donor battle scene + enemy type (deterministic, the
    most reliable form: "look like THAT enemy"). Names from ``ff9mapkit battle-list --scenes``.
  * ``{"name": "GEO_MON_B3_001"}`` -- a battle GEO model name (``GEO_MON_B3_*``) or a numeric geo id; resolved
    to a geo id, then the install is SCANNED for the first real enemy that uses it (so the copied bytes are
    always a real, shipped block). NOTE: friendly creature names (e.g. "goblin") are FIELD models
    (``GEO_MON_F0_*``) and are NOT used by battle enemies -- use a donor scene or a ``GEO_MON_B3_*`` id instead.

The pure byte-copy lives in :mod:`scene_data`; this module only does the install I/O + name resolution.
"""
from __future__ import annotations

import re

from . import extract, scene_codec, scene_data

_RX_RAW16 = re.compile(r"battlescene/evt_battle_([^/]+)/dbfile0000\.raw16", re.I)
# infra failures that mean "can't reach the install" (find_game_path raises ConfigError, a RuntimeError; a
# missing UnityPy raises RuntimeError) -- caught + re-raised as an ACTIONABLE ReskinError, not a raw traceback.
_INFRA_ERRORS = (RuntimeError, FileNotFoundError)
_INSTALL_HINT = ("can't reach the FF9 install to read the donor model -- pass `--game <FF9 dir>`, set "
                 "$FF9_GAME_PATH, or `pip install UnityPy`")


class ReskinError(scene_data.SceneEditError):
    pass


def _geo_for_name(name) -> int | None:
    """A battle GEO name / numeric id (or a friendly creature name) -> its geo (model) id, or None. Uses the
    kit's baked, open-source model catalog (``catalog.model`` is the same id ``SetModel``/SB2_MON_PARM.Geo
    take). Friendly creature names resolve to FIELD-form ids (``GEO_MON_F0_*``) that no battle enemy uses --
    they'll fail the enemy scan with a clear message; battle enemies are ``GEO_MON_B3_*``."""
    from .. import archetypes as _arch
    from .. import catalog as _cat
    key = str(name).strip()
    m = _cat.model(key)                                    # exact GEO name or numeric id
    if m:
        return m.id
    spec = _arch.CREATURES.get(key.lower())                # friendly creature name -> a (FIELD) GEO model name
    if spec:
        m = _cat.model(spec["model"])
        if m:
            return m.id
    return None


def _scan_for_geo(geo_id: int, game=None):
    """Scan the install's battle scenes for the FIRST enemy whose Geo == ``geo_id``. Loads p0data2 ONCE and
    parses each scene's raw16. Returns (scene_name, type_no, donor_raw16) or None. (Used by the ``name`` form
    so the transplanted block is always a real shipped record, even if a name->id map were imperfect.)"""
    UnityPy = extract._unitypy()
    from ..extract import _raw_bytes
    env = UnityPy.load(str(extract._p0data2(game)))
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        mm = _RX_RAW16.search((getattr(o, "container", None) or "").lower())
        if not mm:
            continue
        try:
            raw16 = _raw_bytes(o.read())
            scene = scene_codec.parse_scene(raw16)
        except Exception:                                  # noqa: BLE001 -- a malformed/odd scene just isn't a donor
            continue
        for t, mon in enumerate(scene.monsters):
            if mon.geo == geo_id:
                return mm.group(1).upper(), t, raw16
    return None


def resolve_donor_block(spec: dict, *, game=None) -> tuple[bytes, str]:
    """Resolve a donor ``spec`` -> (116-byte monster block, human provenance string). Install-gated.

    ``spec`` is ``{"scene": NAME, "type": N}`` (explicit) or ``{"name": NAME}`` (a friendly/GEO name, scanned).
    Raises :class:`ReskinError` with an actionable message on an unknown name / no enemy using that model /
    an out-of-range donor type."""
    if spec.get("scene"):
        donor = str(spec["scene"]).upper()
        t = int(spec.get("type", 0))
        try:
            raw16 = extract.read_scene_assets(donor, game)["raw16"]
        except (ValueError, KeyError) as ex:
            raise ReskinError(f"re-skin donor scene {donor!r} not readable: {ex}. Use a name from "
                              f"`ff9mapkit battle-list --scenes`.")
        except _INFRA_ERRORS as ex:
            raise ReskinError(f"re-skin donor scene {donor!r}: {_INSTALL_HINT} ({ex})")
        return scene_data.mon_block(raw16, t), f"{donor} type {t}"

    name = spec.get("name")
    if not name:
        raise ReskinError("re-skin spec needs a 'name' (a GEO model name / geo id) or a 'scene' (+ 'type')")
    geo = _geo_for_name(name)
    if geo is None:
        raise ReskinError(f"re-skin model {name!r}: unknown GEO model name / id. Battle enemies use "
                          f"`GEO_MON_B3_*` names (browse with `ff9mapkit models`), or point at a real donor "
                          f"enemy with model_scene = \"<SCENE>\" (+ model_type = N).")
    try:
        found = _scan_for_geo(geo, game)
    except _INFRA_ERRORS as ex:
        raise ReskinError(f"re-skin model {name!r}: {_INSTALL_HINT} ({ex})")
    if found is None:
        raise ReskinError(f"re-skin model {name!r} (geo {geo}) is not used by any BATTLE enemy, so there is "
                          f"no real animation set to transplant. (Friendly creature names are FIELD models, "
                          f"not battle enemies.) Use a `GEO_MON_B3_*` id, or a donor enemy with "
                          f"model_scene = \"<SCENE>\" (+ model_type = N).")
    scene_name, t, donor_raw16 = found
    return scene_data.mon_block(donor_raw16, t), f"{name} (geo {geo}) from {scene_name} type {t}"


def reskin_spec(enemy: dict):
    """The donor spec for a ``[[scene.enemy]]`` dict, or None if it has no re-skin. ``model_scene`` (+ optional
    ``model_type``) is the explicit donor; ``model`` is a friendly/GEO name. Raises on a contradictory combo."""
    has_scene = enemy.get("model_scene") is not None
    has_name = enemy.get("model") is not None
    if has_scene and has_name:
        raise ReskinError(f"slot {enemy.get('slot')}: set EITHER model = \"<name>\" OR model_scene = "
                          f"\"<SCENE>\" (+ model_type), not both")
    if has_scene:
        return {"scene": enemy["model_scene"], "type": int(enemy.get("model_type", 0))}
    if has_name:
        if enemy.get("model_type") is not None:
            raise ReskinError(f"slot {enemy.get('slot')}: model_type only applies with model_scene (the "
                              f"model = \"<name>\" form auto-finds the donor enemy)")
        return {"name": enemy["model"]}
    if enemy.get("model_type") is not None:                 # model_type alone = a typo (meant model_scene); don't drop it silently
        raise ReskinError(f"slot {enemy.get('slot')}: model_type has no effect without model_scene = "
                          f"\"<SCENE>\" (the donor battle scene to copy the model from)")
    return None
