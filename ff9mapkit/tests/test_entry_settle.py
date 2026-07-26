"""Entry camera-settle: hold the screen black before Main_Init's reveal fade so the engine's smooth-camera
follower converges UNSEEN (no visible warp-in ease). content.entry_settle + the [camera] entry_settle wiring."""
from __future__ import annotations

import pytest

from ff9mapkit import data
from ff9mapkit.content import entry_settle as ES
from ff9mapkit.eb import EbScript, opcodes, _optables

DISABLE_MOVE = 0x2D
ENABLE_MOVE = 0x2E
WAIT = 0x22
FADE = 0xEC


def _main_init_ops(ebb):
    eb = EbScript.from_bytes(ebb)
    f0 = eb.entry(0).func_by_tag(0)
    return [(i.op, list(i.args or [])) for i in eb.instrs(f0)]


def test_blank_template_has_a_reveal_fade():
    # the precondition the settle hides behind: Main_Init reveals via a fade-IN (mode & 2)
    ops = _main_init_ops(data.blank_field_bytes("us"))
    fades = [a for op, a in ops if op == FADE and a and isinstance(a[0], int)]
    assert any(int(m[0]) & 2 for m in fades)


def test_inserts_disablemove_wait_enablemove_before_the_reveal_fade():
    src = data.blank_field_bytes("us")
    out = ES.add_entry_settle(src, 45)
    assert EbScript.from_bytes(out).to_bytes() == out          # still a valid .eb
    assert len(out) == len(src) + 5                            # DisableMove(1) + Wait(3) + EnableMove(1)
    ops = _main_init_ops(out)
    fade_i = next(n for n, (op, a) in enumerate(ops) if op == FADE and a and isinstance(a[0], int) and int(a[0]) & 2)
    # the three ops immediately before the reveal fade are exactly our settle triplet
    assert [op for op, _ in ops[fade_i - 3:fade_i]] == [DISABLE_MOVE, WAIT, ENABLE_MOVE]
    assert ops[fade_i - 2][1] == [45]                          # the wait frame count


def test_zero_or_no_fade_is_a_noop():
    src = data.blank_field_bytes("us")
    assert ES.add_entry_settle(src, 0) == src                  # disabled
    assert ES.add_entry_settle(src, -1) == src


def _settle_triplet_before_fade(ops):
    fade_i = next(n for n, (op, a) in enumerate(ops)
                  if op == FADE and a and isinstance(a[0], int) and int(a[0]) & 2)
    return [op for op, _ in ops[fade_i - 3:fade_i]] == [DISABLE_MOVE, WAIT, ENABLE_MOVE], ops[fade_i - 2][1]


def test_build_wires_entry_settle_from_camera_block(tmp_path):
    from ff9mapkit import build
    base = ('[field]\nid=4700\nname="F"\nborrow_bg="X"\narea=21\ntext_block=8\n'
            '[camera]\npitch=30\ndistance=900\nfov=40\n{settle}[player]\nspawn=[0,0]\n')
    p = tmp_path / "f.field.toml"
    # with entry_settle=40 -> the settle triplet precedes the reveal fade
    p.write_text(base.format(settle="entry_settle=40\n"), encoding="utf-8")
    has, frames = _settle_triplet_before_fade(_main_init_ops(build.build_script(build.FieldProject.load(p), "us", {})))
    assert has and frames == [40]
    # absent -> no settle triplet (the build is otherwise unchanged)
    p.write_text(base.format(settle=""), encoding="utf-8")
    has2, _ = _settle_triplet_before_fade(_main_init_ops(build.build_script(build.FieldProject.load(p), "us", {})))
    assert not has2


# ---- field-entry rung 4: multicam support + the silent-no-op honesty --------------------------
_MULTICAM = ('[field]\nid=4700\nname="F"\nborrow_bg="X"\narea=21\ntext_block=8\n'
             '[[camera]]\npitch=30\ndistance=900\nfov=40\n{c0}'
             '[[camera]]\npitch=35\ndistance=900\nfov=40\n{c1}'
             '[player]\nspawn=[0,0]\n')


def test_multicam_entry_settle_applies(tmp_path):
    # entry_settle inside [[camera]] blocks used to be silently SKIPPED -- now the first nonzero applies
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text(_MULTICAM.format(c0="", c1="entry_settle=33\n"), encoding="utf-8")
    has, frames = _settle_triplet_before_fade(_main_init_ops(build.build_script(build.FieldProject.load(p), "us", {})))
    assert has and frames == [33]


def test_build_warns_when_settle_cannot_apply(tmp_path, monkeypatch):
    # the honesty warning: entry_settle requested but no reveal fade to hide it behind -> warn, once
    from ff9mapkit import build
    monkeypatch.setattr(build._entry_settle, "add_entry_settle", lambda b, n: b)   # force the no-op path
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=4700\nname="F"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\nentry_settle=45\n[player]\nspawn=[0,0]\n',
                 encoding="utf-8")
    proj, w = build.FieldProject.load(p), []
    build.build_script(proj, "us", {}, warnings=w)
    build.build_script(proj, "us", {}, warnings=w)                                 # a 2nd lang: no duplicate
    assert len([x for x in w if "NOT applied" in x and "reveal fade" in x]) == 1


def _settle_lint(tmp_path, body):
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text(f'[field]\nid = 4700\nname = "F"\narea = 21\n{body}', encoding="utf-8")
    return build.lint_entry_settle(build.FieldProject.load(p))


def test_lint_settle_dead_key_on_verbatim(tmp_path):
    out = _settle_lint(tmp_path, '[verbatim_eb]\nbin = "x.bin"\n[camera]\nentry_settle = 45\n')
    assert any("IGNORED on a verbatim fork" in x for x in out)


def test_lint_settle_bad_values(tmp_path):
    assert any("boolean" in x for x in _settle_lint(tmp_path, '[camera]\nentry_settle = true\n'))
    assert any("negative" in x for x in _settle_lint(tmp_path, '[camera]\nentry_settle = -5\n'))
    assert any("not an integer" in x for x in _settle_lint(tmp_path, '[camera]\nentry_settle = "fast"\n'))
    assert _settle_lint(tmp_path, '[camera]\nentry_settle = 45\n') == []           # a good value is silent
    assert _settle_lint(tmp_path, '[camera]\npitch = 30\n') == []                  # absent is silent


def test_lint_settle_multicam_disagreement(tmp_path):
    out = _settle_lint(tmp_path, '[[camera]]\nentry_settle = 45\n[[camera]]\nentry_settle = 90\n')
    assert any("FIRST nonzero (45)" in x for x in out)
    same = _settle_lint(tmp_path, '[[camera]]\nentry_settle = 45\n[[camera]]\nentry_settle = 45\n')
    assert same == []                                                              # agreeing values are silent


def test_hub_boolean_entry_settle_is_on_off_not_one_frame():
    # JOURNEYS.md used to teach `entry_settle = true`, which int()'d to a useless 1-FRAME hold --
    # a boolean is now on/off (true = the proven default, false = 0); ints pass through
    from ff9mapkit import hub
    base = {"name": "H", "id": 4500}
    assert hub.hubspec_from_table({**base, "entry_settle": True}, []).entry_settle == hub.DEFAULT_ENTRY_SETTLE
    assert hub.hubspec_from_table({**base, "entry_settle": False}, []).entry_settle == 0
    assert hub.hubspec_from_table({**base, "entry_settle": 60}, []).entry_settle == 60


def test_string_settle_does_not_crash_the_build(tmp_path):
    # an unrecognized string is skipped with lint explaining -- never a traceback
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=4700\nname="F"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\nentry_settle="fast"\n[player]\nspawn=[0,0]\n',
                 encoding="utf-8")
    has, _ = _settle_triplet_before_fade(_main_init_ops(build.build_script(build.FieldProject.load(p), "us", {})))
    assert not has                                                                 # skipped, built fine


# ---- field-entry rung 7: entry_settle = "auto" (the computed hold) ----------------------------
# The estimator replicates the engine (FieldMap.cs): the camera's target is the player-aim's
# CLAMPED GTE screen position; before the player binds it targets the bare projection offset; the
# follower eases geometrically by s = CameraStabilizer/100 per frame. So the hold =
# bind_delay + ln(delta/tol)/-ln(s), delta = the px distance between those two clamped points.

def _synth_cam(*, range_wh=(384, 448), viewport=None, center_offset=(0, 0)):
    from ff9mapkit.scene import guide
    kw = dict(range_wh=range_wh, center_offset=center_offset)
    if viewport is not None:
        kw["viewport"] = viewport
    return guide.make_camera(30, 900, fov_x_deg=40, **kw)


def test_is_auto():
    assert ES.is_auto("auto") and ES.is_auto(" AUTO ") and ES.is_auto("Auto")
    assert not ES.is_auto(45) and not ES.is_auto(True) and not ES.is_auto("fast") and not ES.is_auto(None)


def test_estimator_zero_delta_is_off():
    # a viewport with NO scroll room pins the camera -- no drift, nothing to hide, 0 = byte-identical
    cm = _synth_cam(viewport=(192, 192, 224, 224))
    assert ES.warp_in_delta_px(cm, (0, 0)) < 1.0
    assert ES.estimate_entry_settle(cm, (0, 0)) == 0


def test_estimator_band_and_shape():
    cm = _synth_cam()                                   # the default 384x448 canvas has scroll room
    n = ES.estimate_entry_settle(cm, (0, -800))
    assert ES.AUTO_MIN_FRAMES <= n <= ES.AUTO_MAX_FRAMES
    assert n % 5 == 0                                   # readable: rounded up to a multiple of 5
    # log-monotone: a bigger warp-in delta never computes a SHORTER hold. (z=-600 lands INSIDE this
    # camera's scroll window; a far spawn SATURATES the engine's viewport clamp -- the delta is
    # capped, exactly like the real camera's scroll range.)
    d_near, d_far = ES.warp_in_delta_px(cm, (0, -600)), ES.warp_in_delta_px(cm, (0, -1500))
    assert d_far > d_near
    assert ES.estimate_entry_settle(cm, (0, -1500)) >= ES.estimate_entry_settle(cm, (0, -600))
    # a snappier stabilizer converges faster
    assert (ES.estimate_entry_settle(cm, (0, -800), stabilizer=50)
            <= ES.estimate_entry_settle(cm, (0, -800), stabilizer=85))


def test_build_auto_applies_the_computed_hold(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=4700\nname="F"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\nentry_settle="auto"\n[player]\nspawn=[0,-800]\n',
                 encoding="utf-8")
    proj, w = build.FieldProject.load(p), []
    has, frames = _settle_triplet_before_fade(_main_init_ops(build.build_script(proj, "us", {}, warnings=w)))
    expect = ES.estimate_entry_settle(build.resolve_camera(proj), (0, -800))
    assert has and frames == [expect] and ES.AUTO_MIN_FRAMES <= expect <= ES.AUTO_MAX_FRAMES
    # the chosen value is surfaced ONCE in the build output (a 2nd lang adds no duplicate)
    build.build_script(proj, "us", {}, warnings=w)
    assert len([x for x in w if '"auto"' in x and f"{expect} frames" in x]) == 1


def test_build_auto_falls_back_when_camera_unresolvable(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=4700\nname="F"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\nborrow="missing.bgx"\nentry_settle="auto"\n[player]\nspawn=[0,0]\n',
                 encoding="utf-8")
    proj, w = build.FieldProject.load(p), []
    has, frames = _settle_triplet_before_fade(_main_init_ops(build.build_script(proj, "us", {}, warnings=w)))
    assert has and frames == [ES.DEFAULT_ENTRY_SETTLE]          # the proven default, never a crash
    assert any("could not be resolved" in x for x in w)


def test_lint_auto_reports_the_resolved_value(tmp_path):
    out = _settle_lint(tmp_path, '[camera]\npitch=30\ndistance=900\nfov=40\nentry_settle = "auto"\n'
                                 '[player]\nspawn = [0, -800]\n')
    assert any('"auto" resolves to' in x and "frames" in x for x in out)
    # unresolvable offline (no pitch/borrow) -> the fallback advisory, not a crash
    out2 = _settle_lint(tmp_path, '[camera]\nentry_settle = "auto"\n')
    assert any("fall back" in x for x in out2)


def test_lint_multicam_mixed_auto_and_int_disagree(tmp_path):
    out = _settle_lint(tmp_path, '[[camera]]\npitch=30\ndistance=900\nfov=40\nentry_settle = "auto"\n'
                                 '[[camera]]\npitch=35\ndistance=900\nfov=40\nentry_settle = 60\n')
    assert any("different entry_settle values" in x for x in out)


def test_hub_auto_passes_through_and_renders_quoted():
    from ff9mapkit import hub
    spec = hub.hubspec_from_table({"name": "H", "id": 4500, "entry_settle": "auto"}, [])
    assert spec.entry_settle == "auto"
    toml_text = hub.render_hub_field_toml(spec)
    assert 'entry_settle = "auto"' in toml_text


# ---- the owner directive (2026-07-25): import EMITS the settle --------------------------------
# Every import-generated field.toml carries `entry_settle = "auto"` under [camera] -- a warp-in
# must never show the camera easing in the clear ("i want the player experience"). The ONE
# exemption is a verbatim fork: the donor .eb carries its own real entry sequence, so the key
# would be a dead no-op there (lint_entry_settle flags it).

def test_the_import_settle_line_is_the_auto_form():
    import tomllib
    from ff9mapkit import extract
    cfg = tomllib.loads("[camera]\n" + extract._ENTRY_SETTLE_LINE)
    assert cfg["camera"]["entry_settle"] == "auto"
    assert ES.is_auto(cfg["camera"]["entry_settle"])


def test_new_scaffold_emits_entry_settle_auto(tmp_path):
    # the directive covers every generator, not just import: the `ff9mapkit new` scaffold carries
    # the settle in the CLI form (the exact line, first key under [camera])
    import tomllib
    from ff9mapkit import extract, pack
    proj = pack.new_project("SETTLE_ROOM", tmp_path, area=11)
    text = (proj / "settle_room.field.toml").read_text(encoding="utf-8")
    assert "[camera]\n" + extract._ENTRY_SETTLE_LINE in text
    assert tomllib.loads(text)["camera"]["entry_settle"] == "auto"


def _game_ready():
    try:
        import UnityPy  # noqa: F401,PLC0415
        from ff9mapkit import config  # noqa: PLC0415
        return config.find_game_path(None) is not None
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_emits_entry_settle_auto_except_verbatim(tmp_path):
    import tomllib
    from ff9mapkit import campaign, extract

    def _cam(p):
        return tomllib.loads(p.read_text(encoding="utf-8")).get("camera", {})

    donor = "fbg_n06_vgdl_map101_dl_inn_0"                     # Dali Inn, the proven small donor
    _, p = extract.write_native_project(donor, tmp_path / "nat", name="DV")
    assert _cam(p)["entry_settle"] == "auto"                   # native fork
    _, p = extract.write_lightweight_project(donor, tmp_path / "lw", name="DV")
    assert _cam(p)["entry_settle"] == "auto"                   # lightweight (area<10 stub form)
    (tmp_path / "mem").mkdir()
    _, p = campaign._emit_logic_only_member(donor, tmp_path / "mem", "MEM", 30011, {}, False, None)
    assert _cam(p)["entry_settle"] == "auto"                   # import-chain logic-only member
    _, p = extract.write_field_project("fbg_n11_ldbm_map158_lb_plz_0", tmp_path / "bor", name="LB")
    assert _cam(p)["entry_settle"] == "auto"                   # BG-borrow (needs an area>=10 donor)
    # verbatim: the donor .eb IS the entry sequence -- no dead key emitted, and the toml lints clean
    _, p = extract.write_native_project(donor, tmp_path / "vb", name="DV", verbatim=True)
    assert "entry_settle" not in _cam(p)


def test_estimator_matches_the_proven_calibration_points():
    # the in-game-proven holds (hub 45 / waystation 45, 90 over-tuned): the computed values must land
    # in the proven band. Uses the extract cache (install-gated -- skip cleanly without it).
    import pytest
    from pathlib import Path
    from ff9mapkit.scene import cam as C
    from ff9mapkit import provision
    cases = [(950, (404, 127)), (3100, (383, -1449)), (2800, (0, -2000))]
    for fid, spawn in cases:
        bgx = Path(provision.field_cache_dir(fid)) / "camera.bgx"
        if not bgx.is_file():
            pytest.skip(f"field {fid} camera not cached (run `ff9mapkit extract-field {fid}`)")
        cm = C.parse_bgx_cameras(str(bgx))[0]
        n = ES.estimate_entry_settle(cm, spawn)
        assert 40 <= n <= 60, (fid, n)                  # the proven-clean band (45-60; 90 = too long)
