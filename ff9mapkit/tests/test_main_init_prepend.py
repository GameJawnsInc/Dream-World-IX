"""A Main_Init PREPEND must carry entry 0's past-the-end function pointer with it.

The blank template's entry 0 is Main_Init (tag 0) + Main_Loop (tag 1), and Main_Loop's ``fpos`` points 65
bytes PAST entry 0's declared size. The engine loads exactly ``size`` bytes per entry, so that is an
out-of-range IP it simply returns from (EventEngine.Return -> GetIP(sid, 1); Obj.getByteIP catches the OOB).
A bare entry-table relayout at Main_Init's start fixes only the ENTRY table: the pointer stays put while
the code grows under it, each inserted byte eats one byte of the margin, and past zero the engine runs
Main_Loop from the middle of entry 0's code (the after-battle tag-10 Main_Reinit) on every field load.

``[camera.scroll]`` (``content.camera.enable_camera_services``) and a Main_Init-D9-positioned object graft
(``content.object._arm``) were raw ``edit.insert_bytes`` callers; both now prepend through
``edit.insert_in_function`` (rel 0), which moves the other functions' ``fpos`` with the bytes, and
``insert_bytes`` itself now REFUSES any insert that would strand a pointer. These tests go red if either --
or any other Main_Init lever listed in ``LEVERS`` -- regresses to the bare relayout. The synthetic fixture
runs without the game install; the blank-template and build checks need ``ff9mapkit extract-templates``.
"""
from __future__ import annotations

import struct

import pytest
from PIL import Image

from ff9mapkit import data, eventscan
from ff9mapkit.content import camera, music
from ff9mapkit.content import object as _object
from ff9mapkit.content import region
from ff9mapkit.eb import EbScript, disasm, edit, opcodes

RET = opcodes.RETURN
BLANK_MAIN_LOOP_MARGIN = 65     # how far past entry 0's end the blank's tag-1 fpos points
D9 = {"0": -250, "4": -571}     # TOML inline-table keys arrive as strings


def _eb(*entries) -> bytes:
    """A valid multi-entry ``.eb`` from ``[(tag, body), ...]`` per entry, packed back-to-back after the
    slot table (the ``test_reinit._eb_multi`` layout)."""
    bodies = []
    for funcs in entries:
        table, code, fpos = b"", b"", len(funcs) * 4
        for tag, body in funcs:
            table += struct.pack("<HH", tag, fpos)
            code += body
            fpos += len(body)
        bodies.append(bytes([0, len(funcs)]) + table + code)
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = len(entries)
    slots, off = bytearray(), len(entries) * 8
    for body in bodies:
        slots += struct.pack("<HHBBH", off, len(body), 0, 0, 0)
        off += len(body)
    return bytes(head) + bytes(slots) + b"".join(bodies)


def _dangling_fixture() -> bytes:
    """The blank's shape: entry 0 = Main_Init (tag 0) + a tag 1 whose fpos points 65 bytes PAST the entry's
    end. Entry 1 follows, non-empty, so a wrong relocation shows."""
    b = bytearray(_eb([(0, opcodes.ENABLE_MOVE + RET), (1, b"")], [(0, RET)]))
    e0 = EbScript.from_bytes(bytes(b)).entry(0)
    rec = e0.abs_start + 2 + 1 * 4                        # tag 1's (tag, fpos) record
    assert struct.unpack_from("<H", b, rec)[0] == 1
    struct.pack_into("<H", b, rec + 2, (e0.size - 2) + BLANK_MAIN_LOOP_MARGIN)
    return bytes(b)


def _margin(eb: bytes, tag: int = 1) -> int:
    """How far entry 0's ``tag`` pointer sits past the entry's end (> 0 = out of range, as in the blank)."""
    e0 = EbScript.from_bytes(eb).entry(0)
    return e0.func_by_tag(tag).fpos - (e0.size - 2)


def _assert_prepended(before: bytes, after: bytes, block: bytes) -> None:
    """``block`` became Main_Init's first bytes, the old Main_Init rode along whole behind it, entry 0 grew
    by exactly ``len(block)``, and entry 1 moved by that much with its bytes intact."""
    b, a = EbScript.from_bytes(before), EbScript.from_bytes(after)
    fb, fa = b.entry(0).func_by_tag(0), a.entry(0).func_by_tag(0)
    n = len(block)
    assert fa.fpos == fb.fpos
    assert after[fa.abs_start:fa.abs_start + n] == block
    assert after[fa.abs_start + n:a.entry(0).abs_end] == before[fb.abs_start:b.entry(0).abs_end]
    assert a.entry(0).size == b.entry(0).size + n
    e1b, e1a = b.entry(1), a.entry(1)
    assert e1a.off == e1b.off + n
    assert after[e1a.abs_start:e1a.abs_end] == before[e1b.abs_start:e1b.abs_end]
    assert a.to_bytes() == after


def _d9_block(slot: int, arg: int) -> bytes:
    return (region.set_var(eventscan.POS_VAR_CLASS, 0, -250) + region.set_var(eventscan.POS_VAR_CLASS, 4, -571)
            + opcodes.init_object(slot, arg))


# every Main_Init lever that prepends: (name, apply(eb) -> eb, the block it prepends)
LEVERS = [
    ("camera_services", lambda eb: camera.enable_camera_services(eb),
     opcodes.encode(camera.BGCACTIVE_OP, 1, 0, 0)),
    ("camera_services_sinus", lambda eb: camera.enable_camera_services(eb, frame_count=30, scroll_type=8),
     opcodes.encode(camera.BGCACTIVE_OP, 1, 30, 8)),
    ("object_arm_d9", lambda eb: _object._arm(eb, 1, 0, D9), _d9_block(1, 0)),
    # (a self-positioning _arm / edit.activate with no free Wait filler falls back to exactly this)
    ("activate_block", lambda eb: edit.activate_block(eb, opcodes.init_code(1, 0)), opcodes.init_code(1, 0)),
    ("stop_music", music.add_stop_current_music, music.stop_current_music_bytes()),
]


def test_the_fixture_bites():
    """The bare relayout (``edit._insert_bytes_raw``) fixes the ENTRY table only, so an insert ahead of a
    past-the-end pointer eats its margin byte for byte. If this stops holding, the fixture no longer
    discriminates and every test below would pass vacuously."""
    eb = _dangling_fixture()
    assert _margin(eb) == BLANK_MAIN_LOOP_MARGIN
    f0 = EbScript.from_bytes(eb).entry(0).func_by_tag(0)
    out = edit._insert_bytes_raw(eb, f0.abs_start, opcodes.ENABLE_MOVE * 70)
    assert _margin(out) == BLANK_MAIN_LOOP_MARGIN - 70 < 0          # now INSIDE entry 0's code


def test_insert_bytes_refuses_to_strand_the_past_end_pointer():
    """The law enforced at the call site: the public ``insert_bytes`` refuses ANY insert into an entry whose
    function pointer sits past the insert point -- one byte, anywhere in Main_Init -- instead of eating the
    margin. The four raw callers that shipped the bug would now fail their build loudly."""
    eb = _dangling_fixture()
    f0 = EbScript.from_bytes(eb).entry(0).func_by_tag(0)
    for off in (f0.abs_start, f0.abs_start + 1):
        with pytest.raises(ValueError, match=r"strand entry 0's function tag 1 \(starts at/past the entry's end\)"):
            edit.insert_bytes(eb, off, RET)
    e1 = EbScript.from_bytes(eb).entry(1)               # entry 1's lone function is its last -> allowed
    assert edit.insert_bytes(eb, e1.func_by_tag(0).abs_start, RET) \
        == edit._insert_bytes_raw(eb, e1.func_by_tag(0).abs_start, RET)


@pytest.mark.parametrize("name,apply,block", LEVERS, ids=[lv[0] for lv in LEVERS])
def test_main_init_lever_carries_the_past_end_pointer(name, apply, block):
    """REGRESSION: ``enable_camera_services`` and the D9 ``_arm`` prepended with a raw ``insert_bytes`` and left
    the blank's Main_Loop pointer behind (a scroll field ate 5 bytes of its margin, every D9 arm 19)."""
    eb = _dangling_fixture()
    out = apply(eb)
    assert _margin(out) == BLANK_MAIN_LOOP_MARGIN
    _assert_prepended(eb, out, block)


def test_stacked_prepends_keep_the_exact_margin():
    """Scroll + two D9-armed instances (38 bytes, most of the margin) + a stop-music, stacked: the pointer
    moves with every one of them, so it still sits exactly where it started."""
    out = camera.enable_camera_services(_dangling_fixture())
    out = _object._arm(out, 1, 0, D9)
    out = _object._arm(out, 1, 1, D9)
    out = music.add_stop_current_music(out)
    assert _margin(out) == BLANK_MAIN_LOOP_MARGIN
    f0 = EbScript.from_bytes(out).entry(0).func_by_tag(0)
    assert out[f0.abs_start:].startswith(music.stop_current_music_bytes() + _d9_block(1, 1) + _d9_block(1, 0)
                                         + opcodes.encode(camera.BGCACTIVE_OP, 1, 0, 0))


def test_levers_still_refuse_a_field_without_main_init():
    eb = _eb([(1, RET)], [(0, RET)])
    with pytest.raises(ValueError, match="no Main_Init"):
        camera.enable_camera_services(eb)
    with pytest.raises(ValueError, match="no Main_Init"):
        _object._arm(eb, 1, 0, D9)


# ---- the real blank template (needs `ff9mapkit extract-templates`) ---------------------------------------
def test_blank_template_levers_keep_the_main_loop_out_of_range():
    blank = data.blank_field_bytes("us")
    assert _margin(blank) == BLANK_MAIN_LOOP_MARGIN                  # the shape the fixture models
    with pytest.raises(ValueError, match="strand entry 0's function tag 1 "):
        edit.insert_bytes(blank, EbScript.from_bytes(blank).entry(0).func_by_tag(0).abs_start, RET)
    out = camera.enable_camera_services(blank)
    for arg in range(3):
        out = _object._arm(out, 1, arg, D9)
    assert _margin(out) == BLANK_MAIN_LOOP_MARGIN


def test_built_scroll_field_with_a_d9_graft_keeps_the_main_loop_margin(tmp_path):
    """End to end through ``build_mod``: a ``[camera.scroll]`` field that also grafts a Main_Init-D9-positioned
    ``[[object]]`` ships, in every language, entry 0's Main_Loop exactly as far past the end as the blank has
    it (before the fix: 65 - 5 - 19 = 41)."""
    from ff9mapkit.build import FieldProject, build_mod
    from ff9mapkit.config import LANGS, ModLayout
    for png in ("back.png", "floor.png"):
        Image.new("RGBA", (768 * 2, 448 * 2), (40, 40, 40, 255)).save(tmp_path / png)
    init = (opcodes.encode(eventscan.SET_MODEL_OP, 133, 0) + opcodes.encode(0x1D)
            + opcodes.encode(eventscan.SET_STAND_ANIM_OP, 1872) + RET)
    (tmp_path / "obj.bin").write_bytes(bytes([0, 1]) + struct.pack("<HH", 0, 4) + init)
    toml = tmp_path / "scroll.field.toml"
    toml.write_text(
        '[field]\nid=4003\nname="SCROLLD9"\narea=11\ntext_block=1073\n\n'
        "[camera]\npitch=40\ndistance=4500\nfov=42.2\nrange=[768,448]\nwindow_width=384\n\n"
        "[camera.scroll]\nenabled=true\n\n"
        "[walkmesh]\nquad=[[-2129,2136],[2129,2136],[2129,-2030],[-2129,-2030]]\ncharacter_offset=0\n\n"
        '[[layers]]\nimage="back.png"\nz=4000\n[[layers]]\nimage="floor.png"\nz=3000\n\n'
        "[player]\nspawn=[0,53]\n\n"
        '[[object]]\nbin="obj.bin"\nkind="prop"\ndonor_idx=99\nneeds_d9={ 0 = -250, 4 = -571 }\n'
        "instances=[{ arg = 0 }]\n",
        encoding="utf-8")
    out = tmp_path / "mod"
    build_mod([FieldProject.load(toml)], out, mod_name="FF9CustomMap")
    for lang in LANGS:
        eb = ModLayout(out).eb_path(lang, "EVT_SCROLLD9.eb.bytes").read_bytes()
        e0 = EbScript.from_bytes(eb).entry(0)
        # bounded at entry 0's END: the model runs Main_Init up to the next fpos, which is past it
        ops = [ins.op for ins in disasm.iter_code(eb, e0.func_by_tag(0).abs_start, e0.abs_end)]
        assert camera.BGCACTIVE_OP in ops and 0x09 in ops, lang          # both levers really fired
        assert _margin(eb) == BLANK_MAIN_LOOP_MARGIN, lang
