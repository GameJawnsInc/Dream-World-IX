"""Which clip a model's preview STILL is posed from -- ``catalog.stand_clip`` + its two consumers.

The defect this fences: the still was ranked by SUBSTRING over the whole anim name, so "stand" matched
``PUSHED_STAND`` / ``SIT_STAND`` / ``SLEEP_STAND``, Zidane's get-up ``STAND`` (frame 0: flat on the
floor) beat his standing ``IDLE``, and every battle form -- whose clips are named by MOTION NUMBER --
matched nothing and fell through to the lowest key on disc: a bind pose, or an attack mid-swing. 222
of the catalog's 710 stills were posed from the wrong clip.

Everything here is INSTALL-FREE: ``stand_clip`` takes the disc map as an argument, and the two
consumers (``preview._skinned_struct``, ``thumbcache.build_model_thumb``) run over the same stubbed
install seams ``test_model_animpreview`` uses. Ids are looked up BY NAME so a regenerated AnimationDB
cannot silently turn a fence into a test of something else.
"""
import json

import pytest

pytest.importorskip("PIL")

from ff9mapkit import catalog, provision
from ff9mapkit.models import _gltf_io, anim as manim, extract, preview, thumbcache


def _aid(name: str) -> int:
    """The canonical (lowest) AnimationDB id naming ``name`` -- fails loudly if the name is gone."""
    ids = [k for k, v in catalog.ANIMATIONS.items() if v == name]
    assert ids, f"{name} is not in the AnimationDB -- this fence no longer tests what it says"
    return min(ids)


def _gid(name: str) -> int:
    m = catalog.model(name)
    assert m is not None, f"{name} is not in the model catalog"
    return m.id


# ------------------------------------------------------------------------------- the ranking
def test_the_rank_orders_exact_labels_before_any_substring():
    r = catalog.stand_action_rank
    order = ["idle", "stand", "000", "idle1", "walk", "stand_read_3", "sleep_stand"]
    ranks = [r(a) for a in order]
    assert ranks == sorted(ranks) and len(set(ranks)) == len(ranks), ranks
    assert r("IDLE") == r("idle"), "the label is case-blind"
    for not_a_stance in ("attack", "b", "p", "402", "", None):
        assert r(not_a_stance) == catalog.STAND_RANK_NONE, not_a_stance


def test_a_holders_walk_is_not_the_props_walk():
    """``ANH_ACC_F0_GAS_F0_ZDN_WALK`` is a PROP's clip named after who carries it. The old ranking
    matched "walk" anywhere in the name and posed the prop from it."""
    s = catalog.split_anh("ANH_ACC_F0_GAS_F0_ZDN_WALK")
    assert catalog.stand_action_rank(s[3]) == catalog.STAND_RANK_NONE


# -------------------------------------------------------------------------------- the choice
def test_idle_beats_a_stand_that_is_really_a_get_up():
    """Zidane's own folder holds BOTH. ``STAND`` won under the old scheme ("stand" was tried before
    "idle") and its first frame lies on the floor. The standing loop is ``IDLE`` on every field rig."""
    zdn = _gid("GEO_MAIN_F0_ZDN")
    stand, idle = _aid("ANH_MAIN_F0_ZDN_STAND"), _aid("ANH_MAIN_F0_ZDN_IDLE")
    walk = _aid("ANH_MAIN_F0_ZDN_WALK")
    assert catalog.stand_clip(zdn, {zdn: {stand, idle, walk}}) == (idle, zdn)
    assert catalog.stand_clip(zdn, {zdn: {stand, walk}}) == (stand, zdn), \
        "with no idle on disc an exact STAND still beats a walk"


def test_a_battle_form_stands_in_motion_000():
    """Battle clips are numbered, so no stand TOKEN ever matched and the pick was the lowest key --
    here the bind clip. ``000`` is MP_IDLE_NORMAL: the stance the battler holds."""
    b = _gid("GEO_MAIN_B0_001")
    bind, idle = _aid("ANH_MAIN_B0_001_B"), _aid("ANH_MAIN_B0_001_000")
    other = _aid("ANH_MAIN_B0_001_402")
    assert min(bind, idle, other) != idle, "the fence needs a case the lowest-key rule gets wrong"
    assert catalog.stand_clip(b, {b: {bind, idle, other}}) == (idle, b)


def test_the_overworld_actor_stands_in_stand_not_stand_cho():
    """``STAND_CHO`` (mounted on a chocobo that is not in the picture) has the lower key and CONTAINS
    "stand"; the engine's own idle for this actor is the exact ``STAND``."""
    w = _gid("GEO_SUB_W0_001")
    cho, stand = _aid("ANH_SUB_W0_001_STAND_CHO"), _aid("ANH_SUB_W0_001_STAND")
    assert catalog.stand_clip(w, {w: {cho, stand}}) == (stand, w)


def test_a_rig_with_nothing_stand_like_keeps_its_lowest_key_and_never_prefers_P():
    """``_P`` reads like "pose" and rendered WORSE than ``_B`` wherever the two were compared (a doll
    pitched onto its face, a sword edge-on). So it is not ranked: the pick is what it always was."""
    doll = _gid("GEO_ACC_F0_DGR")
    b, p = _aid("ANH_ACC_F0_DGR_B"), _aid("ANH_ACC_F0_DGR_P")
    assert catalog.stand_clip(doll, {doll: {b, p}}) == (min(b, p), doll)
    assert catalog.stand_action_rank("p") == catalog.stand_action_rank("b")


def test_the_donor_folder_is_crossed_for_an_exact_idle():
    """An F1 NPC variant keeps only niche gestures natively and idles out of its F0 sibling's folder
    (the engine's name-token redirect). That redirect is worth following -- for an exact label."""
    f1, f0 = _gid("GEO_NPC_F1_BBA"), _gid("GEO_NPC_F0_BBA")
    idle = _aid("ANH_NPC_F0_BBA_IDLE")
    native = _aid("ANH_NPC_F0_BBA_B")
    assert catalog.stand_clip(f1, {f1: {native}, f0: {idle}}) == (idle, f0)


def test_the_donor_folder_is_not_crossed_for_a_loose_substring():
    """A different folder is usually a different FORM, i.e. a different skeleton. ``TBY_IDLE`` merely
    contains "idle"; that is not a reason to pose one rig from another's clip."""
    f1, f0 = _gid("GEO_ACC_F1_BLL"), _gid("GEO_ACC_F0_BLL")
    own = _aid("ANH_ACC_F1_BLL_B")
    loose = _aid("ANH_ACC_F0_BLL_TBY_IDLE")
    assert catalog.stand_action_rank("tby_idle") > catalog._STAND_DONOR_MAX
    assert catalog.stand_clip(f1, {f1: {own}, f0: {loose}}) == (own, f1)


def test_no_clip_on_disc_answers_None():
    zdn = _gid("GEO_MAIN_F0_ZDN")
    assert catalog.stand_clip(zdn, {}) is None
    assert catalog.stand_clip("not-an-id", {}) is None
    assert catalog.stand_clip(None, {}) is None


# ------------------------------------------------------------- the consumers spend the choice
VIVI = 8
IDLE = 148                                            # ANH_MAIN_F0_VIV_IDLE


def _collected():
    """One bone, one triangle, no material stems -- enough for true skinning, nothing for a bundle."""
    ident = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    mesh = {"name": "mesh0", "verts": [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 10.0, 0.0]],
            "normals": [[0.0, 0.0, -1.0]] * 3, "uvs": [[0, 0], [1, 0], [1, 1]],
            "submeshes": [[[0, 1, 2]]]}
    return {"geo": "GEO_MAIN_F0_VIV", "geo_id": VIVI, "type_int": 0, "prefab_id": VIVI,
            "bundle": object(), "root_bone": "bone000",
            "bones": [{"name": "bone000", "parent": None, "pos": [0, 0, 0], "rot": [0, 0, 0, 1],
                       "scale": [1, 1, 1]}],
            "smrs": [{"name": "mesh0", "mesh": mesh, "idx_to_num": {0: 0}, "mat_stems": [None],
                      "weights": [[(0, 1.0)]] * 3, "samples": [("bone000", ident)]}]}


@pytest.fixture
def install(tmp_path, monkeypatch):
    """Pin the cache and stub every install seam; ``disc`` is mutable so a test picks what is on disc."""
    disc = {VIVI: {IDLE}}
    read = []
    monkeypatch.setattr(provision, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(extract, "_Bundle", lambda *a, **k: object())
    monkeypatch.setattr(extract, "_collect", lambda *a, **k: _collected())
    monkeypatch.setattr(manim, "_load_env5", lambda game=None: object())
    monkeypatch.setattr(_gltf_io, "anim_disc_map", lambda env: disc)

    def _read_clip(env, folder, key):
        read.append((folder, key))
        return {"name": "c", "sample_rate": 30.0, "length": 0.0,
                "bones": {"bone000": {"bone": 0, "pos": [(0.0, (7.0, 0.0, 0.0))]}}}
    monkeypatch.setattr(_gltf_io, "read_clip", _read_clip)
    return {"root": tmp_path, "disc": disc, "read": read}


def test_the_still_is_posed_from_the_chosen_clip_and_says_so(install):
    struct = preview._skinned_struct("GEO_MAIN_F0_VIV", env5=object())
    assert install["read"] == [(VIVI, IDLE)], "the renderer must READ the clip stand_clip chose"
    assert struct["posed_from"] == (IDLE, VIVI)
    assert struct["meshes"][0]["verts"][0][0] == 7.0, "...and actually pose the bones from it"


def test_a_rig_with_no_clip_renders_at_rest_and_records_that(install):
    install["disc"].clear()
    struct = preview._skinned_struct("GEO_MAIN_F0_VIV", env5=object())
    assert struct["posed_from"] is None and install["read"] == []
    assert struct["meshes"][0]["verts"][0][0] == 0.0
    assert preview._skinned_struct("GEO_MAIN_F0_VIV", env5=object(), pose=False)["posed_from"] is None


def test_an_explicit_clip_is_not_a_stand_pose(install):
    """The ANIMATED path poses by its own clip; it must not claim (or pay for) a stand pick."""
    clip = {"name": "x", "sample_rate": 30.0, "length": 0.0, "bones": {}}
    struct = preview._skinned_struct("GEO_MAIN_F0_VIV", collected=_collected(), clip=clip, t=0.0)
    assert struct["posed_from"] is None and install["read"] == []


def test_the_sidecar_records_what_the_picture_shows(install):
    png = thumbcache.build_model_thumb("GEO_MAIN_F0_VIV", {})
    assert png is not None
    meta = thumbcache.model_thumb_meta(VIVI)
    assert meta["pose"] == "ANH_MAIN_F0_VIV_IDLE" and meta["pose_action"] == "idle"
    assert meta["pose_rank"] == catalog.stand_action_rank("idle")
    assert meta["bones"] == 1


def test_the_sidecar_says_REST_when_nothing_posed_the_rig(install):
    install["disc"].clear()
    thumbcache.build_model_thumb("GEO_MAIN_F0_VIV", {})
    meta = thumbcache.model_thumb_meta(VIVI)
    assert "pose" in meta and meta["pose"] is None and meta["pose_action"] is None


# ------------------------------------------------------------------- the cache key follows it
def test_a_pose_pick_change_re_keys_the_stills_and_ONLY_the_stills():
    """The two caches go stale for different reasons. Bumping the still's pose version must move every
    still to a new key -- and must NOT throw away the rendered clip frames, which are posed by their
    own clip and cannot care."""
    still = thumbcache.model_thumb_paths(VIVI)[0].name
    frame = thumbcache.anim_frame_path(VIVI, IDLE, 0).name
    token = f"p{thumbcache._STILL_POSE_V}"
    assert still == f"{VIVI}_v{thumbcache._RASTER_V}{token}.png"
    assert token not in frame.split("_v")[-1], "a clip frame's key must not carry the still's pose version"
    assert thumbcache._ANIM_RENDER_V.startswith(str(thumbcache._RASTER_V)), \
        "...but a RASTERIZER change must still invalidate both"
    assert thumbcache._STILL_POSE_V >= 2, "the exact-label ranking shipped as pose version 2"


def test_a_fresh_still_prunes_its_own_stale_versions_and_nobody_elses(install):
    d = install["root"] / "model_thumbs"
    d.mkdir(parents=True)
    mine = [d / f"{VIVI}_v1.png", d / f"{VIVI}_v1.json", d / f"{VIVI}_v0zz.png"]
    theirs = [d / f"{VIVI}8_v1.png", d / "18_v1.json"]       # 88 and 18: a careless glob eats both
    for f in mine + theirs:
        f.write_bytes(b"x")
    thumbcache.build_model_thumb("GEO_MAIN_F0_VIV", {})
    assert not any(f.exists() for f in mine), "the previous generation must go when the fresh one lands"
    assert all(f.exists() for f in theirs), "a prune must never reach another model's files"
    png, meta = thumbcache.model_thumb_paths(VIVI)
    assert png.is_file() and meta.is_file()


def test_an_absent_probe_also_prunes_the_stale_pair(install, monkeypatch):
    def _gone(*a, **k):
        raise FileNotFoundError("no prefab on disc")
    monkeypatch.setattr(preview, "_skinned_struct", _gone)
    d = install["root"] / "model_thumbs"
    d.mkdir(parents=True)
    stale = d / f"{VIVI}_v1.png"
    stale.write_bytes(b"x")
    assert thumbcache.build_model_thumb("GEO_MAIN_F0_VIV", {}) is None
    assert not stale.exists()
    assert json.loads(thumbcache.model_thumb_paths(VIVI)[1].read_text(encoding="utf-8"))["absent"] is True


def test_the_disc_map_is_walked_once_per_bundle():
    """The still asks for it once PER MODEL; uncached, every one of ~700 renders re-walked the whole
    p0data5 container."""
    class _T:
        name = "AnimationClip"

    class _Obj:
        type = _T()

    class _Bundle:
        walks = 0

        @property
        def container(self):
            type(self).walks += 1
            return {"assets/resources/animations/8/148.anim": _Obj()}

    b = _Bundle()
    first = _gltf_io.anim_disc_map(b)
    assert first == {8: {148}}
    assert _gltf_io.anim_disc_map(b) is first and _Bundle.walks == 1
    assert _gltf_io.anim_disc_map(_Bundle()) == {8: {148}} and _Bundle.walks == 2, \
        "the memo is per BUNDLE, never module-wide"
