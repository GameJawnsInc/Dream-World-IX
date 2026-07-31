"""Offline tests for the ANIMATED model preview: the clip sampler, the stable-framing ``fit=``
override, and the per-frame disk cache (no install / no UnityPy -- the install seams are stubbed).

The three things that must not drift:
  * ``_pose_bones_at`` samples a clip at an arbitrary time, clamps at both ends, leaves an unkeyed
    bone/channel at its rest TRS, and hands back LISTS (the struct's TRS is a list everywhere else);
  * ``render_model(fit=...)`` reframes, and ``fit=None`` is BIT-IDENTICAL to not passing it at all
    (the whole static-thumbnail pillar rides on that default);
  * ``build_anim_clip`` poses every frame BEFORE rasterizing any, so all of them share one union box
    (auto-fitting per frame pulses the model), strides past the frame cap, honours the abort seam,
    and writes its frames somewhere ``absent_ids()`` can never see them.
"""
import json
import math

import pytest

pytest.importorskip("PIL")

from ff9mapkit import provision
from ff9mapkit.models import _gltf_io, anim as manim, extract, preview, thumbcache


# --------------------------------------------------------------- the pose sampler (A1) -----

def _bones():
    return [{"name": "bone000", "parent": None, "pos": [0, 0, 0], "rot": [0, 0, 0, 1],
             "scale": [1, 1, 1]},
            {"name": "bone001", "parent": "bone000", "pos": [0, 5, 0], "rot": [0, 0, 0, 1],
             "scale": [1, 1, 1]}]


CLIP = {"name": "walk", "sample_rate": 30.0, "length": 2.0,
        "bones": {"bone000/bone001": {"bone": 1,
                                      "rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (2.0, (0.0, 1.0, 0.0, 0.0))],
                                      "pos": [(0.0, (0.0, 0.0, 0.0)), (2.0, (10.0, 20.0, 30.0))]}}}


def test_pose_bones_at_interpolates_between_keys():
    posed = preview._pose_bones_at(_bones(), CLIP, 1.0)          # dead centre of a 2s curve
    assert posed[1]["pos"] == [5.0, 10.0, 15.0]
    assert posed[1]["rot"] == [0.0, 0.5, 0.0, 0.5]


def test_pose_bones_at_clamps_at_both_ends_and_returns_lists():
    at_zero = preview._pose_bones_at(_bones(), CLIP, 0.0)
    assert at_zero[1]["pos"] == [0.0, 0.0, 0.0] and at_zero[1]["rot"] == [0.0, 0.0, 0.0, 1.0]
    before = preview._pose_bones_at(_bones(), CLIP, -5.0)         # clamped to keyframe[0]
    assert before[1]["pos"] == at_zero[1]["pos"] and before[1]["rot"] == at_zero[1]["rot"]
    after = preview._pose_bones_at(_bones(), CLIP, 99.0)          # clamped to the last keyframe
    assert after[1]["pos"] == [10.0, 20.0, 30.0]
    # LISTS, not the sampler's tuples -- the existing struct fences assert list equality
    for b in (at_zero[1], before[1], after[1]):
        assert isinstance(b["pos"], list) and isinstance(b["rot"], list)


def test_pose_bones_at_leaves_unkeyed_bones_and_channels_at_rest():
    src = _bones()
    posed = preview._pose_bones_at(src, CLIP, 1.0)
    assert posed[0]["rot"] == [0, 0, 0, 1] and posed[0]["pos"] == [0, 0, 0]   # bone000 is unkeyed
    assert posed[1]["scale"] == [1, 1, 1]                          # the clip carries no scale channel
    assert src[1]["pos"] == [0, 5, 0]                              # the input list is not mutated
    assert preview._pose_bones_at(src, None, 0.0) is src           # no clip -> the rest hierarchy
    assert preview._pose_bones_at(src, {"bones": {}}, 0.0) is src


def test_pose_bones_at_zero_agrees_with_the_stand_pose_frame_0_read():
    """The animated sampler at t=0 must land exactly where _stand_pose's frame-0 fast path does --
    they are the same pose, and a drift between them would make frame 0 jump off the static thumb."""
    frame0 = {bn["name"]: bn for bn in preview._pose_bones_at(_bones(), CLIP, 0.0)}
    ch = CLIP["bones"]["bone000/bone001"]
    assert frame0["bone001"]["rot"] == list(ch["rot"][0][1])
    assert frame0["bone001"]["pos"] == list(ch["pos"][0][1])


# --------------------------------------------------- stable framing: render_model(fit=) (A2) -----

def _quad(x0=0.0, x1=10.0):
    mesh = {"name": "mesh0", "verts": [[x0, 0.0, 0.0], [x1, 0.0, 0.0], [x1, 10.0, 0.0], [x0, 10.0, 0.0]],
            "normals": [[0.0, 0.0, -1.0]] * 4, "uvs": [[0, 0], [1, 0], [1, 1], [0, 1]],
            "submeshes": [{"material_idx": 0, "tris": [[0, 1, 2], [0, 2, 3]]}]}
    return {"meshes": [mesh], "materials": [{"name": "m0", "texture": None}], "textures": {}}


def test_fit_none_is_bit_identical_to_the_untouched_call():
    m = _quad()
    base = preview.render_model(m, size=48, yaw=0, pitch=0, shade=False, supersample=1)
    with_none = preview.render_model(m, size=48, yaw=0, pitch=0, shade=False, supersample=1, fit=None)
    assert base.tobytes() == with_none.tobytes()


def test_fit_override_reframes_the_model():
    m = _quad()
    auto = preview.render_model(m, size=48, yaw=0, pitch=0, shade=False, supersample=1)
    wide = preview.render_model(m, size=48, yaw=0, pitch=0, shade=False, supersample=1,
                                fit=(-40.0, 50.0, -40.0, 50.0))       # a much larger box -> smaller model
    assert auto.tobytes() != wide.tobytes()
    ab, wb = auto.getbbox(), wide.getbbox()
    assert (ab[2] - ab[0]) > (wb[2] - wb[0]), "a wider fit box must shrink the drawn model"


def test_projected_bounds_is_the_box_render_auto_fits_to():
    m = _quad()
    assert preview.projected_bounds(m, yaw=0, pitch=0) == (0.0, 10.0, 0.0, 10.0)
    # rendering against the box render_model would have derived itself changes nothing
    auto = preview.render_model(m, size=48, yaw=0, pitch=0, shade=False, supersample=1)
    pinned = preview.render_model(m, size=48, yaw=0, pitch=0, shade=False, supersample=1,
                                  fit=preview.projected_bounds(m, yaw=0, pitch=0))
    assert auto.tobytes() == pinned.tobytes()
    assert preview.projected_bounds({"meshes": [], "materials": [], "textures": {}}) is None


# ------------------------------------------------- build_anim_clip + the frame cache (A3) -----

VIVI = 8                                              # GEO_MAIN_F0_VIV; 148 = ANH_MAIN_F0_VIV_IDLE
IDLE = 148


def _collected():
    """A one-bone, one-quad stand-in for extract._collect: enough for TRUE skinning to run, with no
    material stems (so the texture read short-circuits and never touches a bundle)."""
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


def _slide_clip(frames: int):
    """A clip that slides the only bone along +x, one key per frame at 30fps (so frame_count == frames
    and every frame's silhouette sits somewhere different -- the union box has to grow)."""
    rate, n = 30.0, max(2, frames)
    keys = [(i / rate, (float(i) * 20.0, 0.0, 0.0)) for i in range(n)]
    return {"name": "slide", "sample_rate": rate, "length": keys[-1][0],
            "bones": {"bone000": {"bone": 0, "pos": keys}}}


@pytest.fixture
def anim_env(tmp_path, monkeypatch):
    """Pin the cache to tmp_path and stub every install seam build_anim_clip reaches through."""
    monkeypatch.setattr(provision, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(extract, "_Bundle", lambda *a, **k: object())
    monkeypatch.setattr(extract, "_collect", lambda *a, **k: _collected())
    monkeypatch.setattr(manim, "_load_env5", lambda game=None: object())
    monkeypatch.setattr(_gltf_io, "anim_disc_map", lambda env: {VIVI: {IDLE}})
    return tmp_path


def _pin_clip(monkeypatch, clip):
    monkeypatch.setattr(_gltf_io, "read_clip", lambda env, folder, key: clip)


def test_build_anim_clip_writes_every_frame_plus_a_meta_sidecar(anim_env, monkeypatch):
    _pin_clip(monkeypatch, _slide_clip(3))
    seen = []
    meta = thumbcache.build_anim_clip(VIVI, IDLE, {}, on_frame=lambda i, p: seen.append((i, p)))
    assert meta["frame_count"] == 3 and meta["stride"] == 1
    assert meta["rendered_frames"] == [0, 1, 2] and meta["sample_rate"] == 30.0
    assert meta["label"] == "ANH_MAIN_F0_VIV_IDLE" and meta["anim"] == IDLE and meta["id"] == VIVI
    assert [i for i, _ in seen] == [0, 1, 2], "on_frame must stream every frame as it lands"
    for f in (0, 1, 2):
        assert thumbcache.cached_anim_frame(VIVI, IDLE, f) is not None
    on_disk = json.loads(thumbcache.anim_meta_path(VIVI, IDLE).read_text(encoding="utf-8"))
    assert on_disk == meta and thumbcache.anim_clip_meta(VIVI, IDLE) == meta


def test_every_frame_rasterizes_against_the_ONE_union_fit(anim_env, monkeypatch):
    clip = _slide_clip(3)
    _pin_clip(monkeypatch, clip)
    meta = thumbcache.build_anim_clip(VIVI, IDLE, {})
    fit = tuple(meta["fit"])
    # the union is WIDER than any single frame (the bone slides +20 per frame)
    lone = preview.projected_bounds(preview._skinned_struct(
        "GEO_MAIN_F0_VIV", collected=_collected(), clip=clip, t=0.0))
    assert (fit[1] - fit[0]) > (lone[1] - lone[0])
    # ...and each cached PNG is that frame rendered against exactly that box
    from PIL import Image
    for f in (0, 2):
        struct = preview._skinned_struct("GEO_MAIN_F0_VIV", collected=_collected(), clip=clip,
                                         t=f / meta["sample_rate"])
        want = preview.render_model(struct, size=thumbcache.MODEL_THUMB, fit=fit)
        got = Image.open(thumbcache.cached_anim_frame(VIVI, IDLE, f))
        assert got.convert("RGBA").tobytes() == want.tobytes()


def test_a_long_clip_strides_under_the_frame_cap(anim_env, monkeypatch):
    monkeypatch.setattr(thumbcache, "MAX_ANIM_FRAMES", 3)
    _pin_clip(monkeypatch, _slide_clip(7))
    meta = thumbcache.build_anim_clip(VIVI, IDLE, {})
    assert meta["frame_count"] == 7
    assert meta["stride"] == math.ceil(7 / 3) == 3
    assert meta["fps"] == 10.0, "a strided clip must report the rate it will actually PLAY at"
    assert meta["rendered_frames"] == [0, 3, 6] and len(meta["rendered_frames"]) <= 3
    assert thumbcache.cached_anim_frame(VIVI, IDLE, 1) is None      # a skipped frame is never written


def test_should_abort_stops_the_fill_between_frames(anim_env, monkeypatch):
    _pin_clip(monkeypatch, _slide_clip(5))
    calls = []

    def abort():
        calls.append(1)
        return len(calls) > 3            # let a couple of frames through, then pull the plug
    assert thumbcache.build_anim_clip(VIVI, IDLE, {}, should_abort=abort) is None
    assert thumbcache.anim_clip_meta(VIVI, IDLE) is None, "an aborted fill must not claim a warm cache"


def test_a_warm_clip_answers_from_disk_with_no_install(anim_env, monkeypatch):
    _pin_clip(monkeypatch, _slide_clip(2))
    first = thumbcache.build_anim_clip(VIVI, IDLE, {})
    # every install seam now EXPLODES -- a warm answer must come from stats alone
    def _boom(*a, **k):
        raise AssertionError("a warm clip must not touch the install")
    monkeypatch.setattr(extract, "_Bundle", _boom)
    monkeypatch.setattr(manim, "_load_env5", _boom)
    seen = []
    again = thumbcache.build_anim_clip(VIVI, IDLE, {}, on_frame=lambda i, p: seen.append(i))
    assert again == first and seen == first["rendered_frames"]


def test_an_unlocatable_clip_answers_None(anim_env, monkeypatch):
    _pin_clip(monkeypatch, _slide_clip(2))
    monkeypatch.setattr(_gltf_io, "anim_disc_map", lambda env: {})    # nothing on disc for this model
    assert thumbcache.build_anim_clip(VIVI, IDLE, {}) is None
    assert thumbcache.build_anim_clip("GEO_NOPE", IDLE, {}) is None
    assert thumbcache.build_anim_clip(VIVI, "not-an-id", {}) is None


def test_frames_live_apart_from_the_model_thumbs_and_prune_by_version(anim_env, monkeypatch):
    _pin_clip(monkeypatch, _slide_clip(2))
    thumbcache.build_anim_clip(VIVI, IDLE, {})
    assert thumbcache.anim_frame_path(VIVI, IDLE, 0).parent.name == "anim_frames"
    # absent_ids() globs model_thumbs/*.json -- an anim sidecar must never land in its way
    assert thumbcache.absent_ids() == set()
    # a stale render version is pruned when the clip is re-armed
    stale_png = thumbcache.anim_frame_path(VIVI, IDLE, 0).with_name(f"{VIVI}_{IDLE}_f0_v0zz.png")
    stale_json = thumbcache.anim_meta_path(VIVI, IDLE).with_name(f"{VIVI}_{IDLE}_v0zz.json")
    stale_png.write_bytes(b"x")
    stale_json.write_text("{}", encoding="utf-8")
    thumbcache.anim_meta_path(VIVI, IDLE).unlink()             # force a rebuild (not the warm path)
    thumbcache.build_anim_clip(VIVI, IDLE, {})
    assert not stale_png.exists() and not stale_json.exists()
    assert thumbcache.cached_anim_frame(VIVI, IDLE, 0) is not None
