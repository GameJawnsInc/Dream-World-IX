"""Entry camera-settle: hold the screen black before Main_Init's reveal fade so the engine's smooth-camera
follower converges UNSEEN (no visible warp-in ease). content.entry_settle + the [camera] entry_settle wiring."""
from __future__ import annotations

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
    assert any("not an integer" in x for x in _settle_lint(tmp_path, '[camera]\nentry_settle = "auto"\n'))
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
    # a non-numeric value (e.g. a future "auto") is skipped with lint explaining -- never a traceback
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=4700\nname="F"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\nentry_settle="auto"\n[player]\nspawn=[0,0]\n',
                 encoding="utf-8")
    has, _ = _settle_triplet_before_fade(_main_init_ops(build.build_script(build.FieldProject.load(p), "us", {})))
    assert not has                                                                 # skipped, built fine
