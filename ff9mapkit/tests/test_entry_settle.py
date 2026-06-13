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
