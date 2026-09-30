"""THE AI COMPOSITION has one owner (``battle.build._compose_ai_langs``): validate lints exactly what the build
ships, in every language.

Validate used to compose the ``ai_*`` edits on the donor eb while the build composed them after the
``monster_count`` Main_Init rewrite -- so an edit that was right against the donor and wrong against the
shipped bytes validated clean and then failed the build (or worse). Then it composed only us, while a battle eb's
bytecode is NOT language-identical (41 of 562 stock scenes differ in length), and the build applied us's offsets
to every language's own eb: refused late, or silently hit a different constant holding the same value.
Synthetic, install-free fixtures."""
import struct
import textwrap

import pytest

from ff9mapkit.battle import aipatch
from ff9mapkit.battle import build as BB
from ff9mapkit.battle.build import BattleBuildError, BattleProject, build_battle_mod, validate_battle
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.eb import edit as _edit
from ff9mapkit.eb import exprasm
from ff9mapkit.eb import opcodes
from ff9mapkit.eb.model import EbScript

from .test_battle import _battle_eb, _raw16


RET = bytes([0x04])


def _stmt(text: str) -> bytes:
    return bytes([0x05]) + exprasm.assemble(text + " B_EXPR_END")


def _ai_eb(tag5: bytes) -> bytes:
    """entry 0 = Main_Init with TWO InitObjects; entry 1 gets ``tag5`` as its tag-5 (ATB) body."""
    return _edit.add_function(_battle_eb([(1, 0x80), (1, 0x81)], n_ai=2), 1, 5, tag5)


def _donor_eb():
    """entry 0 = Main_Init with TWO InitObjects; entry 1 gets a tag-5 body holding a patchable const."""
    return _ai_eb(_stmt("Instance.Byte[18] const(3) B_LET") + RET)


def mint(tmp_path, scene: str, *, eb: bytes | None = None, raw16: bytes | None = None,
         ebs: dict | None = None) -> BattleProject:
    """A synthetic MINT project: real synthetic raw16 + eb for every language (not the junk bytes of
    ``test_battle._write_scene``), so validate and build both run the composition. ``ebs`` overrides single
    languages (e.g. a jp eb that differs from us, as 41 stock scenes' do)."""
    (tmp_path / "BBG_B013.fbx").write_text("; fbx\n", encoding="ascii")
    sd = tmp_path / "scene"
    (sd / "eb").mkdir(parents=True, exist_ok=True)
    (sd / "mes").mkdir(parents=True, exist_ok=True)
    (sd / "dbfile0000.raw16.bytes").write_bytes(raw16 if raw16 is not None else _raw16(typcount=2))
    (sd / "btlseq.raw17.bytes").write_bytes(b"RAW17")
    for lang in LANGS:
        (sd / "eb" / f"{lang}.eb.bytes").write_bytes((ebs or {}).get(lang) or (eb if eb is not None else _donor_eb()))
        (sd / "mes" / f"{lang}.mes").write_bytes(b"MES_" + lang.encode())
    head = '''
        [battlemap]
        bbg = "BBG_B200"
        fbx = "BBG_B013.fbx"
        scene_id = 30990
        scene_name = "COMPOSE"
    '''
    (tmp_path / "battle.toml").write_text(textwrap.dedent(head) + textwrap.dedent(scene), encoding="utf-8")
    return BattleProject.load(tmp_path / "battle.toml")


def _site():
    """The donor's patchable const(3): its ABSOLUTE offset (ai_patch addresses by byte offset)."""
    return next(s for s in aipatch.constant_sites(_donor_eb()) if s.value == 3)


def _consts(eb: bytes, entry: int = 1, tag: int = 5) -> list:
    """Every constant of function (entry, tag), in order, as (offset, value)."""
    return [(s.offset, s.value) for r in aipatch.func_rows(EbScript.from_bytes(eb), entry, tag) for s in r.sites]


def test_a_donor_offset_survives_the_main_init_rewrite(tmp_path):
    # `at` is a constant in the us DONOR (what `battle-ai --sites` prints). monster_count = 1 rewrites Main_Init
    # to ONE InitObject (3 bytes shorter), so the const now sits 3 bytes earlier in what ships -- it is located
    # there structurally. (This used to be refused in both validate and build: the offset no longer held it.)
    site = _site()
    proj = mint(tmp_path, f'''
        [scene]
        monster_count = 1
        [[scene.enemy]]
        slot = 0
        type = 0
        [[scene.ai_patch]]
        at = {site.offset}
        old = 3
        new = 4
    ''')
    assert validate_battle(proj) == []
    build_battle_mod([proj], tmp_path / "dist")
    lay = ModLayout(tmp_path / "dist")
    for lang in LANGS:
        assert _consts(lay.battle_eb_path(lang, "COMPOSE").read_bytes()) == [(site.offset - 3, 4)]


def test_a_patch_into_the_main_init_monster_count_rewrites_is_refused(tmp_path):
    init = next(s for s in aipatch.constant_sites(_donor_eb()) if s.where.startswith("entry0/tag0"))
    proj = mint(tmp_path, f'''
        [scene]
        monster_count = 1
        [[scene.enemy]]
        slot = 0
        type = 0
        [[scene.ai_patch]]
        at = {init.offset}
        old = {init.value}
        new = {init.value}
    ''')
    probs = validate_battle(proj)
    assert [p for p in probs if "[[scene.ai_patch]]" in p] == [p for p in probs if "monster_count re-authors" in p]
    assert len([p for p in probs if "monster_count re-authors" in p]) == 1   # reported once, not per language
    with pytest.raises(BattleBuildError, match="monster_count re-authors"):
        build_battle_mod([proj], tmp_path / "dist")


def test_the_same_patch_without_a_rewrite_still_validates_and_builds(tmp_path):
    site = _site()
    proj = mint(tmp_path, f'''
        [scene]
        [[scene.ai_patch]]
        at = {site.offset}
        old = 3
        new = 4
    ''')
    assert validate_battle(proj) == []
    build_battle_mod([proj], tmp_path / "dist")
    shipped = ModLayout(tmp_path / "dist").battle_eb_path("us", "COMPOSE").read_bytes()
    assert shipped[site.offset] == 4


def test_compose_ai_is_what_build_ships_for_every_language(tmp_path):
    proj = mint(tmp_path, '''
        [scene]
        monster_count = 2
        [[scene.enemy]]
        slot = 0
        type = 0
        ai_entry = 2
        [[scene.ai_insert]]
        entry = 1
        tag = 5
        at = 0
        source = "SET({Instance.Byte[19] const(1) B_LET B_EXPR_END})"
    ''')
    assert validate_battle(proj) == []
    build_battle_mod([proj], tmp_path / "dist")
    raw16 = (tmp_path / "scene" / "dbfile0000.raw16.bytes").read_bytes()
    from ff9mapkit.battle import scene_data
    patched, _ = scene_data.apply_scene_edits(raw16, proj.raw["scene"])
    want = BB._compose_ai(_donor_eb(), proj.raw["scene"], slot_types=[patched[16 + 12 * s] for s in range(2)],
                          ai_entries=BB._ai_entries(proj.raw["scene"], 2), atk_count=None)
    lay = ModLayout(tmp_path / "dist")
    assert {lay.battle_eb_path(lang, "COMPOSE").read_bytes() for lang in LANGS} == {want}


def test_compose_ai_collects_in_validate_mode_and_raises_in_build_mode():
    bad = {"ai_insert": [{"entry": 1, "tag": 9, "at": 0, "source": "RET()"}]}     # entry 1 has no tag 9
    probs: list = []
    out = BB._compose_ai(_donor_eb(), bad, slot_types=None, ai_entries=None, atk_count=None, problems=probs)
    assert out == _donor_eb() and any("[[scene.ai_insert]]" in p for p in probs)
    with pytest.raises(BattleBuildError):
        BB._compose_ai(_donor_eb(), bad, slot_types=None, ai_entries=None, atk_count=None)
    assert struct.unpack_from("<H", _donor_eb(), 0) == (0x5645,)                  # the fixture is a real .eb


# ---- per language: the languages' AI bytecode differs, so nothing authored is an offset into another's file --
_SET = {v: _stmt(f"Instance.Byte[{v}] const(3) B_LET") for v in (18, 19, 20, 21)}


def test_a_jp_eb_that_differs_in_length_is_not_mispatched(tmp_path):
    # jp carries one more statement before the patched one. The us offset then lands on jp's EXTRA statement's
    # const, which holds the same value -- the old offset rule patched it silently. It must hit jp's counterpart.
    us, jp = _ai_eb(_SET[19] + RET), _ai_eb(_SET[20] + _SET[19] + RET)
    site = next(s for s in aipatch.constant_sites(us) if s.where.startswith("entry1/tag5"))
    assert jp[site.offset] == 3 and _consts(jp)[0][0] == site.offset      # the mispatch precondition
    proj = mint(tmp_path, f'''
        [scene]
        [[scene.ai_patch]]
        at = {site.offset}
        old = 3
        new = 4
    ''', eb=us, ebs={"jp": jp})
    assert validate_battle(proj) == []
    build_battle_mod([proj], tmp_path / "dist")
    lay = ModLayout(tmp_path / "dist")
    assert _consts(lay.battle_eb_path("us", "COMPOSE").read_bytes()) == [(site.offset, 4)]
    shipped_jp = lay.battle_eb_path("jp", "COMPOSE").read_bytes()
    assert _consts(shipped_jp) == [(site.offset, 3), (site.offset + len(_SET[20]), 4)]   # Byte[20] kept, Byte[19] set
    assert len(shipped_jp) == len(jp)


@pytest.mark.parametrize("jp_tag5, why", [
    (_SET[21] + RET, "no provable counterpart"),            # jp's statement differs around the constant
    (_stmt("Instance.Byte[19] const(5) B_LET") + RET, "holds 5 in jp's battle script, not 3"),   # a per-lang value
], ids=["differs-around-it", "per-language-value"])
def test_validate_catches_what_the_build_refuses_in_another_language(tmp_path, jp_tag5, why):
    # validate composed only us, so it stayed green while the build refused jp late -- or, when jp's constant at
    # the us offset held the same value (the first case), wrote it silently
    us = _ai_eb(_SET[19] + RET)
    site = next(s for s in aipatch.constant_sites(us) if s.where.startswith("entry1/tag5"))
    proj = mint(tmp_path, f'''
        [scene]
        [[scene.ai_patch]]
        at = {site.offset}
        old = 3
        new = 4
    ''', eb=us, ebs={"jp": _ai_eb(jp_tag5)})
    probs = validate_battle(proj)
    assert len(probs) == 1 and probs[0].startswith("[[scene.ai_patch]] (jp)") and why in probs[0], probs
    _refused_alike(proj, tmp_path, probs[0])


def _refused_alike(proj, tmp_path, finding: str) -> None:
    """The build refuses on validate's finding, and the build-mode composition -- what the build runs past that
    gate -- raises exactly it: validate reports what the build would refuse."""
    with pytest.raises(BattleBuildError) as ex:
        build_battle_mod([proj], tmp_path / "dist")
    assert finding in str(ex.value)
    donors = {lang: (tmp_path / "scene" / "eb" / f"{lang}.eb.bytes").read_bytes() for lang in LANGS}
    with pytest.raises(BattleBuildError) as ex:
        BB._compose_ai_langs(donors, proj.raw["scene"], slot_types=None, ai_entries=None, atk_count=None)
    assert str(ex.value) == finding


@pytest.mark.parametrize("locator", ['at = 8', 'before = "RET"', 'after = "SET"'])
def test_ai_insert_lands_on_the_counterpart_in_a_longer_jp_eb(tmp_path, locator):
    # jp has a Wait first: body offset 8 (us's RET) is mid-SET there -- the old per-file locate refused jp late
    us, jp = _ai_eb(_SET[18] + RET), _ai_eb(opcodes.wait(1) + _SET[18] + RET)
    frag = _stmt("Instance.Byte[19] const(1) B_LET")
    proj = mint(tmp_path, f'''
        [scene]
        [[scene.ai_insert]]
        entry = 1
        tag = 5
        {locator}
        source = "SET({{Instance.Byte[19] const(1) B_LET B_EXPR_END}})"
    ''', eb=us, ebs={"jp": jp})
    assert validate_battle(proj) == []
    build_battle_mod([proj], tmp_path / "dist")
    lay = ModLayout(tmp_path / "dist")

    def body(eb):
        s = EbScript.from_bytes(eb)
        f = s.entries[1].func_by_tag(5)
        return s.data[f.abs_start:f.abs_end]
    assert body(lay.battle_eb_path("us", "COMPOSE").read_bytes()) == _SET[18] + frag + RET
    assert body(lay.battle_eb_path("jp", "COMPOSE").read_bytes()) == opcodes.wait(1) + _SET[18] + frag + RET


def test_ai_insert_before_a_mnemonic_is_not_jps_own_first_match(tmp_path):
    # jp has an extra TurnInstant first: its OWN first match is the wrong one (a silent mis-insert before)
    us = _ai_eb(_SET[18] + opcodes.turn_instant(2) + RET)
    jp = _ai_eb(opcodes.turn_instant(9) + _SET[18] + opcodes.turn_instant(2) + RET)
    frag = _stmt("Instance.Byte[19] const(1) B_LET")
    proj = mint(tmp_path, '''
        [scene]
        [[scene.ai_insert]]
        entry = 1
        tag = 5
        before = "TurnInstant"
        source = "SET({Instance.Byte[19] const(1) B_LET B_EXPR_END})"
    ''', eb=us, ebs={"jp": jp})
    assert validate_battle(proj) == []
    build_battle_mod([proj], tmp_path / "dist")
    shipped = EbScript.from_bytes(ModLayout(tmp_path / "dist").battle_eb_path("jp", "COMPOSE").read_bytes())
    f = shipped.entries[1].func_by_tag(5)
    assert shipped.data[f.abs_start:f.abs_end] == (opcodes.turn_instant(9) + _SET[18] + frag
                                                  + opcodes.turn_instant(2) + RET)


def test_ai_insert_with_no_counterpart_in_jp_is_caught_by_validate(tmp_path):
    us = _ai_eb(_SET[18] + opcodes.turn_instant(2) + RET)
    jp = _ai_eb(_SET[18] + opcodes.menu(1, 1) + RET)          # jp's second instruction differs
    proj = mint(tmp_path, '''
        [scene]
        [[scene.ai_insert]]
        entry = 1
        tag = 5
        before = "TurnInstant"
        source = "SET({Instance.Byte[19] const(1) B_LET B_EXPR_END})"
    ''', eb=us, ebs={"jp": jp})
    probs = validate_battle(proj)
    assert len(probs) == 1 and probs[0].startswith("[[scene.ai_insert]] (jp)") and "no provable counterpart" in probs[0]
    _refused_alike(proj, tmp_path, probs[0])
