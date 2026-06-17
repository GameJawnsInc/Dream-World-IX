"""Donor battle BGM, read LIVE from the install (provenance-clean): the ``(field, scene) -> song`` map.

FF9 chooses a field battle's song by ``(originMap, battleId)`` == ``(fldMapNo, entered-scene)`` from
``EmbeddedAsset/Manifest/Sounds/BtlEncountBgmMetaData.txt`` (``FF9SndMetaData.GetMusicForBattle`` /
``BattleSwirl.RequestPlayBattleEncounterSongForField``). ``fldMapNo`` is the FIELD id; ``battleId`` is the
``nextMapNo`` the field actually ENTERS -- for a RANDOM encounter that's the chosen ``SetRandomBattles``
scene, for a SCRIPTED battle it's the explicit ``Battle(0x2A)`` scene. A field forked to a custom id
(>= 4000) is NOT in the map, the donor song is lost (``GetMusicForBattle`` returns ``-1``), and the kit's
forced ``Music: 0`` then pins the encounter to the generic Battle Theme. The kit reproduces a song by
emitting a ``Music: <song>`` BattlePatch line: that populates ``FF9SndMetaData.BtlBgmPatcherMapper[scene]``,
which is keyed on the SCENE id the fork KEEPS (not the field id), so it wins regardless of the custom
origin. This is the same id-gated-table-lost-on-a-mint family as the walkmesh hotfixes and the narrow-map
width table, but reproducible because the override is scene-keyed.

★ SCOPE: the live map's NON-zero songs (e.g. the boss/special theme 35) ALL belong to SCRIPTED-battle
scenes; every random-encounter field maps to song 0. So ``import`` prefilling ``[encounter] battle_music``
from the donor's RANDOM primary scene (``extract._donor_battle_song``) is correct but inert for the shipping
game -- it can only ever read a 0. Carrying a donor's SPECIAL battle theme means looking up the donor's
SCRIPTED ``Battle(0x2A)`` scene id (decoded from the carried ``.eb`` of a ``--verbatim`` fork), which the
declarative ``[encounter]`` block never sees -- a separate follow-up (docs/FORK_FIDELITY.md #6).

The metadata is a Square-Enix ``TextAsset`` inside ``FF9_Data/resources.assets`` (NOT Memoria source), so it
is read LIVE from the install and cached in-memory, **shipping/committing NOTHING** -- the same
provenance-clean live pattern as :mod:`ff9mapkit.keyitems` / :mod:`ff9mapkit.itemstats`. If the asset isn't
reachable (no install, no UnityPy, asset moved/renamed), every accessor returns ``None`` and the caller
degrades gracefully (``battle_music`` stays unset -> the build's default 0).
"""
from __future__ import annotations

import json

ASSET_NAME = "BtlEncountBgmMetaData.txt"        # the field-map encounter-BGM TextAsset in resources.assets

_CACHE = None                                   # {int field_id: {int scene_id: int song_id}}, or the _MISS sentinel
_MISS = object()                                # distinguishes "tried, unreachable" from "not yet loaded" (None)


def _resources_assets(game=None):
    """Path to the install's ``resources.assets`` (the Unity data file holding the BGM TextAsset), or ``None``.
    The 64-bit build's data lives under ``x64/FF9_Data``; fall back to ``x86`` then a flat ``FF9_Data``."""
    from .config import find_game_path
    try:
        root = find_game_path(game)
    except Exception:                            # noqa: BLE001 -- install not resolvable -> degrade
        return None
    for sub in ("x64", "x86", ""):
        p = (root / sub / "FF9_Data" / "resources.assets") if sub else (root / "FF9_Data" / "resources.assets")
        if p.exists():
            return p
    return None


def _read(game=None):
    """Parse the BtlEncountBgmMetaData TextAsset from ``resources.assets`` -> ``{field: {scene: song}}``, or
    ``None`` if anything is unavailable. Lazy UnityPy import (kept out of the core kit's hot path)."""
    p = _resources_assets(game)
    if p is None:
        return None
    try:
        import UnityPy                            # noqa: PLC0415 -- only import/extract needs it
    except ImportError:
        return None
    from .extract import _raw_bytes               # the canonical TextAsset byte reader (UnityPy-version-safe)
    try:
        env = UnityPy.load(str(p))
        for obj in env.objects:
            if obj.type.name != "TextAsset":
                continue
            data = obj.read()
            name = getattr(data, "m_Name", None) or getattr(data, "name", "")
            if name != ASSET_NAME:
                continue
            body = _raw_bytes(data)
            if body is None:
                continue
            return parse(body.decode("utf-8", "replace"))
    except Exception:                             # noqa: BLE001 -- any UnityPy/parse failure -> degrade
        return None
    return None


def parse(text):
    """``{"field": {"scene": "song"}}`` JSON -> ``{int field: {int scene: int song}}`` (malformed JSON or
    non-numeric keys/values are skipped, never raised on -- the file is data, never trusted to be perfectly
    formed; an unparseable blob yields ``{}``)."""
    try:
        root = json.loads(text)
    except (ValueError, TypeError):               # JSONDecodeError (empty/garbled) -> empty map, never raise
        return {}
    out: dict = {}
    for fk, scenes in (root or {}).items():
        try:
            fid = int(fk)
        except (TypeError, ValueError):
            continue
        row: dict = {}
        for sk, song in (scenes or {}).items():
            try:
                row[int(sk)] = int(song)
            except (TypeError, ValueError):
                continue
        out[fid] = row
    return out


def _load(game=None):
    """``{field: {scene: song}}`` (cached), or ``None`` if the install/asset can't be read."""
    global _CACHE
    if _CACHE is None:
        parsed = _read(game)
        _CACHE = _MISS if parsed is None else parsed
    return None if _CACHE is _MISS else _CACHE


def song(field_id, scene_id, game=None):
    """The donor field's real battle song for ``scene_id`` (the akao song-play id, e.g. 35), or ``None`` when
    the ``(field, scene)`` pair isn't in the map (the engine plays no special song -> the field BGM bleeds
    into the battle) or the install can't be read. ``0`` is a REAL value (the standard Battle Theme), so it is
    returned as ``0`` and is DISTINCT from ``None`` ("unknown / no mapping")."""
    if field_id is None:
        return None
    table = _load(game)
    if not table:
        return None
    row = table.get(int(field_id))
    if not row:
        return None
    return row.get(int(scene_id))


def available(game=None) -> bool:
    """True if the install's BtlEncountBgmMetaData could be read (so donor battle songs are live)."""
    return _load(game) is not None
