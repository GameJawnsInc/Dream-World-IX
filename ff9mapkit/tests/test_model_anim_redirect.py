"""Offline tests for the AnimationDB folder REDIRECT -- locating a model's clips in a DONOR model's folder
(no install needed; the baked catalog tables + synthetic disc maps stand in for p0data5).

Engine ground truth (Memoria ``AnimationFactory.GetRenameAnimationPath`` -> ``GetRenameAnimationDirectory``):
a clip's on-disc folder comes from its NAME's model tokens (``ANH_NPC_F0_BBA_IDLE`` belongs to
``GEO_NPC_F0_BBA``), NOT from the model playing it, with two hardcoded exceptions for token-models missing
from the GEO table (``MON_B3_110 -> 347``, ``MON_B3_109 -> 5461``). AnimationDB also carries ~4.7k DUPLICATE
name rows; the engine loads by NAME (one canonical id), so only one sibling exists on disc.

The pinned real-data facts (verified against the user's p0data5, mirrored in ``_BBA_DISC`` below):
``GEO_NPC_F1_BBA`` = 10 natively keeps ONLY its two F1-token gesture clips (3882 'b' / 3885 'p'); her catalog
idle=560 / walk=564 / run=563 / turn_r=561 / turn_l=562 are ``ANH_NPC_F0_BBA_*`` living in ``GEO_NPC_F0_BBA``'s
folder 112; and b=8900 / p=8901 are phantom duplicate rows whose on-disc siblings are 9363 / 8902. Before the
redirect, ``model-gltf GEO_NPC_F1_BBA --anims auto`` exported just the two native clips.
"""
import json
import os

from ff9mapkit import catalog as C
from ff9mapkit.models import anim, gltf


# ----------------------------------------------------------------- the real BBA two-folder layout ---------

_BBA_OWN = [3882, 3885]                                # Animations/10/: ANH_NPC_F1_BBA_B / _P
_BBA_DONOR = [560, 561, 562, 563, 564, 1111, 1112, 8902, 9363, 10495, 10499]   # Animations/112/ (a slice)
_BBA_DISC = {10: set(_BBA_OWN), 112: set(_BBA_DONOR)}


class _FakeType:
    def __init__(self, name): self.name = name


class _FakeObj:
    def __init__(self, name): self.type = _FakeType(name)


class _MultiFolderEnv:
    """p0data5 stand-in whose container replays a {folder: keys} layout (same shape the selector scans)."""
    def __init__(self, disc):
        self.container = {f"assets/resources/animations/{f}/{k}.anim": _FakeObj("AnimationClip")
                          for f, keys in disc.items() for k in keys}


# ----------------------------------------------------------------- catalog: folder + siblings + locate ----

def test_animation_folder_replicates_the_engine_redirect():
    # the anim NAME's tokens own the folder: ANH_NPC_F0_BBA_IDLE -> GEO_NPC_F0_BBA's id (112), even though
    # the model PLAYING it is GEO_NPC_F1_BBA (10); a native F1-token clip stays in 10; Vivi's idle is native.
    assert C.model("GEO_NPC_F0_BBA").id == 112 and C.model("GEO_NPC_F1_BBA").id == 10
    assert C.animation_folder(560) == 112              # ANH_NPC_F0_BBA_IDLE
    assert C.animation_folder(3882) == 10              # ANH_NPC_F1_BBA_B
    assert C.animation_folder(148) == 8                # ANH_MAIN_F0_VIV_IDLE -> Vivi's own folder
    # the two GetRenameAnimationDirectory hardcodes (token-models absent from the GEO table)
    assert C.animation_name(10090).startswith("ANH_MON_B3_110") and C.animation_folder(10090) == 347
    assert C.animation_name(11536).startswith("ANH_MON_B3_109") and C.animation_folder(11536) == 5461
    assert C.model("GEO_MON_B3_110") is None           # WHY the hardcode exists: no GEO row to look up
    # unknown / junk ids never raise
    assert C.animation_folder(99999999) is None
    assert C.animation_folder("junk") is None


def test_animation_aliases_self_first_then_siblings():
    # 8901/8902 both name ANH_NPC_F0_BBA_P (a duplicate row); the requested id leads, siblings follow
    assert C.animation_aliases(8901) == [8901, 8902]
    assert C.animation_aliases(8902) == [8902, 8901]
    assert C.animation_aliases(4715) == [4715, 4716]   # world Zidane's idle1 pair
    assert C.animation_aliases(99999999) == [99999999]  # unknown id -> its own only candidate (minted keys)
    assert C.animation_aliases("junk") == []


def test_locate_animation_own_folder_wins_then_donor_then_sibling():
    # own folder first (AddAnimToGameObject bulk-loads it regardless of the clip's name tokens)
    assert C.locate_animation(560, 10, {10: {560}, 112: {560}}) == (560, 10)
    # else the name-token DONOR folder
    assert C.locate_animation(560, 10, _BBA_DISC) == (560, 112)
    # a phantom duplicate id falls through to its on-disc same-name sibling
    assert C.locate_animation(8900, 10, _BBA_DISC) == (9363, 112)   # ANH_NPC_F0_BBA_B
    assert C.locate_animation(8901, 10, _BBA_DISC) == (8902, 112)   # ANH_NPC_F0_BBA_P
    # nowhere on disc -> None (never a guess)
    assert C.locate_animation(8900, 10, {}) is None
    # a minted custom key (unknown to AnimationDB) still resolves through the model's own folder
    assert C.locate_animation(2000000, 6100, {6100: {2000000}}) == (2000000, 6100)
    # no model id: donor resolution still works
    assert C.locate_animation(560, None, _BBA_DISC) == (560, 112)


# ----------------------------------------------------------------- the exporter's selection ---------------

def test_select_auto_fills_core_actions_from_the_donor_folder():
    """THE headline case: GEO_NPC_F1_BBA 'auto' used to export just her two native gesture clips; with the
    redirect it embeds idle/walk/run/turns from the F0 donor folder -- core locomotion FIRST -- and keeps
    the native gestures after."""
    sel = gltf._select_anim_keys("GEO_NPC_F1_BBA", 10, "auto", _MultiFolderEnv(_BBA_DISC))
    labels = [lbl for lbl, _, _ in sel]
    assert labels[:5] == ["idle", "walk", "run", "turn_l", "turn_r"]   # core actions lead
    assert labels[5:] == ["b", "p"]                                    # native gestures kept, after
    assert ("idle", 560, 112) in sel and ("walk", 564, 112) in sel     # donor-located (folder 112)
    assert ("b", 3882, 10) in sel and ("p", 3885, 10) in sel           # natives stay in the own folder


def test_select_explicit_labels_and_ids_follow_the_redirect():
    env = _MultiFolderEnv(_BBA_DISC)
    # action labels resolve through the donor folder (these used to silently drop)
    assert gltf._select_anim_keys("GEO_NPC_F1_BBA", 10, "idle walk", env) == \
        [("idle", 560, 112), ("walk", 564, 112)]
    # a non-core action too (the 23-action catalog is fully reachable)
    assert gltf._select_anim_keys("GEO_NPC_F1_BBA", 10, "sit_chair_1_1", env) == [("sit_chair_1_1", 10495, 112)]
    # a raw donor id
    assert gltf._select_anim_keys("GEO_NPC_F1_BBA", 10, "564", env) == [("564", 564, 112)]
    # a phantom duplicate id resolves to its on-disc sibling -- and is labelled by what actually embedded
    assert gltf._select_anim_keys("GEO_NPC_F1_BBA", 10, "8901", env) == [("8902", 8902, 112)]
    # the catalog 'p' action (id 8901) rides the same sibling resolution but keeps its action label
    assert gltf._select_anim_keys("GEO_NPC_F1_BBA", 10, "p", env) == [("p", 8902, 112)]
    # an unknown token is still skipped silently (parity with the old selector)
    assert len(gltf._select_anim_keys("GEO_NPC_F1_BBA", 10, "idle nosuch", env)) == 1


def test_select_all_stays_the_own_folder():
    """'all' remains 'every clip in the model's OWN folder' -- the donor sweep is for named/requested clips,
    not for hoovering a whole family's shared folder into every variant's export."""
    sel = gltf._select_anim_keys("GEO_NPC_F1_BBA", 10, "all", _MultiFolderEnv(_BBA_DISC))
    assert sel == [("3882", 3882, 10), ("3885", 3885, 10)]


def test_select_auto_prefers_a_rich_own_folder_over_donors():
    """The Vivi shape: catalog ids natively aligned -> all five core actions come from the model's own
    folder and no donor fill happens (guards against foreign-form clips sneaking into a healthy model)."""
    vivi = C.animations_for_model("GEO_MAIN_F0_VIV")
    keys = {vivi[a] for a in ("idle", "walk", "run", "turn_l", "turn_r")}
    sel = gltf._select_anim_keys("GEO_MAIN_F0_VIV", 8, "auto", _MultiFolderEnv({8: keys, 112: set(_BBA_DONOR)}))
    assert [lbl for lbl, _, _ in sel] == ["idle", "walk", "run", "turn_l", "turn_r"]
    assert all(folder == 8 for _, _, folder in sel)


# ----------------------------------------------------------------- the return path routes donor clips -----

def _edited_bones():
    return {1: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (0.0, 0.707, 0.0, 0.707))]}}   # a real ~90deg edit


def _raise_keyerror(*a, **k):
    raise KeyError("no model")


def _src_identity(env, gid, key):
    return {"name": str(key), "sample_rate": 30.0,
            "bones": {"bone001": {"bone": 1, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0)),
                                                     (1.0, (0.0, 0.0, 0.0, 1.0))]}}}


def test_deploy_gltf_anim_edits_writes_a_donor_clip_to_the_donor_folder(monkeypatch, tmp_path):
    """An edited donor-folder clip (BBA's idle=560) must deploy to Animations/112/560.anim -- the path the
    ENGINE reads -- not the playing model's Animations/10/ (an override there is silently dead), and warn
    that the donor clip is SHARED."""
    monkeypatch.setattr(anim, "_load_env5", lambda game=None: _MultiFolderEnv(_BBA_DISC))
    monkeypatch.setattr(anim._gltf_io, "read_glb",
                        lambda p: ({"asset": {"extras": {"ff9_scale": 0.01}}, "animations": [{}]}, b""))
    monkeypatch.setattr(anim.extract, "read_model", _raise_keyerror)
    monkeypatch.setattr(anim._gltf_io, "read_clip", _src_identity)
    monkeypatch.setattr(anim, "parse_gltf_animations",
                        lambda g, b, scale=None: [{"key": 560, "label": "idle", "bones": _edited_bones()}])
    r = anim.deploy_gltf_anim_edits("x.glb", str(tmp_path), geo="GEO_NPC_F1_BBA")
    p = os.path.join(str(tmp_path), "StreamingAssets", "Assets", "Resources", "Animations", "112", "560.anim")
    assert r["written"] == [p] and os.path.isfile(p)
    assert r["folders"] == [112] and r["geo_id"] == 10
    assert any("SHARED donor-folder" in w for w in r["warnings"])
    doc = json.loads(open(p, encoding="utf-8").read())
    assert abs(doc["transform"][0]["localRotation"][-1]["y"] - 0.707) < 1e-3        # the edit landed
    assert not os.path.isdir(os.path.join(str(tmp_path), "StreamingAssets", "Assets", "Resources",
                                          "Animations", "10"))                     # nothing dead-lettered


def test_deploy_gltf_anim_edits_routes_a_dropped_stamp_by_catalog_label(monkeypatch, tmp_path):
    """Blender drops extras: a keyless Action named 'idle' routes via the catalog label -> id 560 -> the
    donor folder + on-disc sibling resolution (the exact inverse of the exporter's labelling)."""
    monkeypatch.setattr(anim, "_load_env5", lambda game=None: _MultiFolderEnv(_BBA_DISC))
    monkeypatch.setattr(anim._gltf_io, "read_glb",
                        lambda p: ({"asset": {"extras": {"ff9_scale": 0.01}}, "animations": [{}]}, b""))
    monkeypatch.setattr(anim.extract, "read_model", _raise_keyerror)
    monkeypatch.setattr(anim._gltf_io, "read_clip", _src_identity)
    monkeypatch.setattr(anim, "parse_gltf_animations",
                        lambda g, b, scale=None: [{"key": None, "label": "idle", "bones": _edited_bones()}])
    r = anim.deploy_gltf_anim_edits("x.glb", str(tmp_path), geo="GEO_NPC_F1_BBA")
    assert [os.path.basename(w) for w in r["written"]] == ["560.anim"]
    assert os.path.basename(os.path.dirname(r["written"][0])) == "112"


def test_deploy_source_anims_locates_an_explicit_donor_key(monkeypatch, tmp_path):
    """model-anim --clips 560: a donor-folder key dumps at its REAL Animations/112/ path (it used to be
    silently filtered out); a key found nowhere is reported in ``missing``, not dropped."""
    monkeypatch.setattr(anim, "_load_env5", lambda game=None: _MultiFolderEnv(_BBA_DISC))
    monkeypatch.setattr(anim._gltf_io, "read_clip", _src_identity)
    r = anim.deploy_source_anims("GEO_NPC_F1_BBA", str(tmp_path), which="560 3882 424242")
    names = [(os.path.basename(os.path.dirname(w)), os.path.basename(w)) for w in r["written"]]
    assert names == [("112", "560.anim"), ("10", "3882.anim")]
    assert r["missing"] == [424242]
