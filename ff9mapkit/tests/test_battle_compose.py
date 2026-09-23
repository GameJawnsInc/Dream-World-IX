"""THE AI COMPOSITION has one owner (``battle.build._compose_ai``): validate lints exactly what the build ships.

Validate used to compose the ``ai_*`` edits on the donor eb while the build composed them after the
``monster_count`` Main_Init rewrite -- so an edit that was right against the donor and wrong against the
shipped bytes validated clean and then failed the build (or worse). Synthetic, install-free fixtures."""
import struct
import textwrap

import pytest

from ff9mapkit.battle import aipatch
from ff9mapkit.battle import build as BB
from ff9mapkit.battle.build import BattleBuildError, BattleProject, build_battle_mod, validate_battle
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.eb import edit as _edit

from .test_battle import _battle_eb, _raw16


def _donor_eb():
    """entry 0 = Main_Init with TWO InitObjects; entry 1 gets a tag-5 body holding a patchable const."""
    eb = _battle_eb([(1, 0x80), (1, 0x81)], n_ai=2)
    body = bytes([0x05]) + __import__("ff9mapkit.eb.exprasm", fromlist=["assemble"]).assemble(
        "Instance.Byte[18] const(3) B_LET B_EXPR_END") + bytes([0x04])
    return _edit.add_function(eb, 1, 5, body)


def mint(tmp_path, scene: str, *, eb: bytes | None = None, raw16: bytes | None = None) -> BattleProject:
    """A synthetic MINT project: real synthetic raw16 + eb for every language (not the junk bytes of
    ``test_battle._write_scene``), so validate and build both run the composition."""
    (tmp_path / "BBG_B013.fbx").write_text("; fbx\n", encoding="ascii")
    sd = tmp_path / "scene"
    (sd / "eb").mkdir(parents=True, exist_ok=True)
    (sd / "mes").mkdir(parents=True, exist_ok=True)
    (sd / "dbfile0000.raw16.bytes").write_bytes(raw16 if raw16 is not None else _raw16(typcount=2))
    (sd / "btlseq.raw17.bytes").write_bytes(b"RAW17")
    for lang in LANGS:
        (sd / "eb" / f"{lang}.eb.bytes").write_bytes(eb if eb is not None else _donor_eb())
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


def test_validate_composes_ai_edits_on_the_rewritten_main_init(tmp_path):
    # the donor offset of the const is right against the donor, but monster_count = 1 rewrites Main_Init
    # to ONE InitObject (3 bytes shorter) -- so in the shipped bytes that offset no longer holds the const
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
    probs = validate_battle(proj)
    assert any("[[scene.ai_patch]]" in p for p in probs), probs      # was: [] (validated the DONOR bytes)
    with pytest.raises(BattleBuildError):                            # ...and the build refuses the same thing
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
