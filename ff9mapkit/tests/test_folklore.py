r"""[[folklore]] -- the Folklore codex data spine (P0): entries minted as key items in the 80-254
important-id band, text shipped as the three cumulative KeyItem .mes overlays, grants riding AddItem
with the pool-encoded id. These tests pin the resolver's band walls, the overlay dialect BYTE-EXACTLY
(the [TXID=<id>]<text>[ENDN] sentence family the engine's cumulative importer parses -- NOT the field-
dialogue dialect), the UTF-8 encoding decision, the grant bytes, validation, and the build aggregation.
All install-free.
"""
from __future__ import annotations

from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.content import event as EV
from ff9mapkit.content import folklore as FK
from ff9mapkit.eb import opcodes
from ff9mapkit.build import FieldProject, validate, _emit_folklore

BLOCKS = [
    {"id": 80, "name": "Mist Wraith", "help": "A spirit of the Mist.", "lore": "Long lore text."},
    {"id": 81, "name": "Ancient Ledger"},
]


# ---- resolve / pool_id (the band walls) --------------------------------------------------------
def test_resolve_int_passthrough():
    assert FK.resolve(80) == 80
    assert FK.resolve(254) == 254
    assert FK.resolve("81") == 81                          # digit-string form


def test_resolve_rejects_out_of_band():
    for bad in (0, 79, 255, 256, 336, -1):
        try:
            FK.resolve(bad)
            assert False, f"{bad} should be out of band"
        except FK.FolkloreError as e:
            assert "80-254" in str(e)


def test_resolve_rejects_bool():
    try:
        FK.resolve(True)
        assert False
    except FK.FolkloreError:
        pass


def test_resolve_rejects_float_never_floors():
    # review find: 80.5 must REPORT, not silently truncate to 80 (a colliding phantom id)
    for api in (FK.resolve, FK.pool_id, FK._check_band):
        try:
            api(80.5)
            assert False, f"{api.__name__} floored a float id"
        except FK.FolkloreError as e:
            assert "integer" in str(e)


def test_resolve_name_against_blocks():
    assert FK.resolve("Mist Wraith", BLOCKS) == 80
    assert FK.resolve("mist wraith", BLOCKS) == 80         # case-insensitive
    assert FK.resolve("MistWraith!", BLOCKS) == 80         # space/punct-insensitive


def test_resolve_unknown_name_names_the_fix():
    try:
        FK.resolve("Nonexistent", BLOCKS)
        assert False
    except FK.FolkloreError as e:
        assert "[[folklore]]" in str(e)


def test_pool_id_math():
    assert FK.pool_id(80) == 336
    assert FK.pool_id(254) == 510


# ---- render_overlays (the byte-exact cumulative-importer dialect) ------------------------------
def test_overlay_dialect_exact():
    out = FK.render_overlays(BLOCKS)
    # NO leading underscore, NO [STRT]/[TAIL], entries concatenated with NO separator, trailing [ENDN]
    assert out["imp_name"] == "[TXID=80]Mist Wraith[ENDN][TXID=81]Ancient Ledger[ENDN]"
    assert out["imp_help"] == "[TXID=80]A spirit of the Mist.[ENDN]"    # 81 supplies no help
    assert out["imp_skin"] == "[TXID=80]Long lore text.[ENDN]"


def test_overlay_sorted_ascending():
    out = FK.render_overlays(list(reversed(BLOCKS)))
    assert out["imp_name"].index("[TXID=80]") < out["imp_name"].index("[TXID=81]")


def test_overlay_empty_channel_is_empty_string():
    out = FK.render_overlays([{"id": 90, "name": "X"}])
    assert out["imp_help"] == "" and out["imp_skin"] == ""


def test_overlay_first_entry_carries_txid():
    # the importer's id counter starts at 0 and auto-increments for un-keyed entries -- an entry
    # without a leading [TXID=] would clobber REAL key item 0 (Silver Pendant). Every entry keys.
    out = FK.render_overlays(BLOCKS)
    for body in out.values():
        if body:
            assert body.startswith("[TXID=")


def test_overlay_rejects_non_string_text():
    # review find: a stray int/bool/list channel must REPORT, never str()-coerce into shipped text
    for bad in ({"id": 80, "name": "X", "help": 42},
                {"id": 80, "name": "X", "lore": True},
                {"id": 80, "name": "X", "lore": ["a", "b"]}):
        try:
            FK.render_overlays([bad])
            assert False, f"{bad} should be rejected"
        except FK.FolkloreError as e:
            assert "must be a string" in str(e)


def test_overlay_rejects_float_id():
    try:
        FK.render_overlays([{"id": 80.5, "name": "X"}])
        assert False
    except FK.FolkloreError as e:
        assert "integer" in str(e)


def test_overlay_rejects_structural_text():
    for bad in ({"id": 80, "name": "A[ENDN]B"},            # the entry terminator inside text
                {"id": 80, "name": "X", "lore": "[TXID=9]hijack"}):    # a leading entry key
        try:
            FK.render_overlays([bad])
            assert False, f"{bad} should be rejected"
        except FK.FolkloreError:
            pass


# ---- the grant bytes ---------------------------------------------------------------------------
def test_give_folklore_is_pool_encoded_add_item():
    assert EV.give_folklore(80) == opcodes.add_item(336, 1)
    assert EV.give_folklore("Mist Wraith", BLOCKS) == opcodes.add_item(336, 1)


def test_give_folklore_count_is_hardcoded_one():
    # count=0 would silently grant nothing (engine: count<=0 -> no-op) -- the signature offers no count
    assert EV.give_folklore(254) == opcodes.add_item(510, 1)


# ---- validate_blocks / the [[event]] lint ------------------------------------------------------
def test_validate_blocks_clean():
    assert FK.validate_blocks(BLOCKS) == []


def test_validate_blocks_errors():
    probs = FK.validate_blocks([
        {"name": "NoId"},                                  # missing id
        {"id": 40, "name": "Low"},                         # out of band
        {"id": 80.5, "name": "Floaty"},                    # float id -- must report, never floor
        {"id": 80, "name": "A"},
        {"id": 80, "name": "B"},                           # duplicate id
        {"id": 81},                                        # missing name
        {"id": 82, "name": "C", "lore": 7},                # non-string channel
    ])
    text = "\n".join(probs)
    assert "needs an id" in text
    assert "80-254" in text
    assert "must be an integer" in text
    assert "already used" in text
    assert "non-empty name" in text
    assert "must be a string" in text


# ---- render_patch_lines (the FolklorePatch.txt codex-registry sidecar) -------------------------
def test_patch_lines_exact():
    lines = FK.render_patch_lines([
        {"id": 82, "name": "C", "category": "lore"},
        {"id": 80, "name": "A", "category": "bestiary"},
        {"id": 81, "name": "B", "category": "places"},
    ])
    assert lines == ["80 bestiary", "81 places", "82 lore"]   # ascending by id


def test_patch_lines_default_category():
    assert FK.render_patch_lines([{"id": 90, "name": "X"}]) == ["90 lore"]


def test_patch_lines_bad_category_raises():
    try:
        FK.render_patch_lines([{"id": 90, "name": "X", "category": "monsters"}])
        assert False
    except FK.FolkloreError as e:
        assert "category" in str(e)


def test_validate_bad_category():
    probs = FK.validate_blocks([{"id": 80, "name": "X", "category": "beasts"}])
    assert any("category" in p for p in probs)


# ---- THE SKIN BUDGET (playtest-minted: the parchment popup is a fixed ~6-line panel, no scroll) --
def test_lore_lines_estimate():
    assert FK.lore_lines_estimate("") == 1                 # empty seg still occupies a line
    assert FK.lore_lines_estimate("x" * 32) == 1
    assert FK.lore_lines_estimate("x" * 33) == 2
    assert FK.lore_lines_estimate("a\nb") == 2             # explicit newlines each consume a line
    assert FK.lore_lines_estimate(("x" * 40 + "\n") * 3 + "y") == 7


def test_validate_overlong_lore_errors():
    probs = FK.validate_blocks([{"id": 80, "name": "X", "lore": "x" * 260}])
    assert any("wrapped lines" in p and "popup" in p for p in probs)


def test_validate_overlong_help_errors():
    probs = FK.validate_blocks([{"id": 80, "name": "X", "help": "x" * 140}])
    assert any("help" in p and "135" in p for p in probs)


def test_validate_budget_boundaries_clean():
    assert FK.validate_blocks([{"id": 80, "name": "X",
                                "lore": "x" * (FK.LORE_MAX_LINES * FK.LORE_CHARS_PER_LINE),
                                "help": "x" * FK.HELP_MAX_CHARS}]) == []


BASE = """
[field]
id = 4003
name = "FOLKTEST"
area = 11
text_block = 1073
[camera]
pitch = 45
[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]
[player]
spawn = [0, -300]
"""

FOLK = """
[[folklore]]
id = 80
name = "Mist Wraith"
help = "A spirit of the Mist."
lore = "Long lore text with a curly quote: ’tis."

[[folklore]]
id = 81
name = "Ancient Ledger"
"""


def _proj(toml, tmp_path, stem="f"):
    p = tmp_path / f"{stem}.field.toml"
    p.write_text(toml, encoding="utf-8")
    return FieldProject.load(p)


def test_validate_field_clean(tmp_path):
    toml = BASE + FOLK + '\n[[event]]\nzone = [[-100,-100],[100,-100],[100,-300],[-100,-300]]\n' \
                         'give_folklore = "Mist Wraith"\n'
    probs = validate(_proj(toml, tmp_path))
    assert not any("folklore" in p.lower() for p in probs), probs


def test_validate_event_unknown_entry(tmp_path):
    toml = BASE + FOLK + '\n[[event]]\nzone = [[-100,-100],[100,-100],[100,-300],[-100,-300]]\n' \
                         'give_folklore = "Wrong Name"\n'
    probs = validate(_proj(toml, tmp_path))
    assert any("give_folklore" in p for p in probs)


def test_validate_event_folklore_counts_as_action(tmp_path):
    # a folklore-only event must pass the "needs at least one action" gate
    toml = BASE + FOLK + '\n[[event]]\nzone = [[-100,-100],[100,-100],[100,-300],[-100,-300]]\n' \
                         'give_folklore = 80\n'
    probs = validate(_proj(toml, tmp_path))
    assert not any("needs at least one action" in p for p in probs)


# ---- _emit_folklore (the mod-global emitter) ---------------------------------------------------
def test_emit_writes_folklore_patch_sidecar(tmp_path):
    proj = _proj(BASE + FOLK + '\n[[folklore]]\nid = 83\ncategory = "bestiary"\nname = "Mu"\n', tmp_path)
    layout = ModLayout(tmp_path / "mod")
    assert _emit_folklore([proj], layout) == []
    body = layout.folklore_patch.read_text(encoding="utf-8")
    assert "80 lore" in body and "83 bestiary" in body     # FOLK's entries default to lore
    assert body.splitlines()[0].startswith("#")            # the comment header


def test_emit_writes_all_langs_utf8(tmp_path):
    proj = _proj(BASE + FOLK, tmp_path)
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_folklore([proj], layout)
    assert warns == []
    for lang in LANGS:
        raw = layout.keyitem_name_mes(lang).read_bytes()
        assert raw == b"[TXID=80]Mist Wraith[ENDN][TXID=81]Ancient Ledger[ENDN]"
        assert not raw.startswith(b"\xef\xbb\xbf")         # no BOM
        skin = layout.keyitem_skin_mes(lang).read_bytes()
        assert b"\xe2\x80\x99tis" in skin                  # U+2019 as UTF-8 (cp1252 would emit 0x92)
        assert layout.keyitem_help_mes(lang).exists()


def test_emit_skips_channel_with_no_entries(tmp_path):
    proj = _proj(BASE + '\n[[folklore]]\nid = 90\nname = "OnlyName"\n', tmp_path)
    layout = ModLayout(tmp_path / "mod")
    assert _emit_folklore([proj], layout) == []
    assert layout.keyitem_name_mes("us").exists()
    assert not layout.keyitem_help_mes("us").exists()
    assert not layout.keyitem_skin_mes("us").exists()


def test_emit_nothing_without_blocks(tmp_path):
    proj = _proj(BASE, tmp_path)
    layout = ModLayout(tmp_path / "mod")
    assert _emit_folklore([proj], layout) == []
    assert not layout.keyitem_name_mes("us").parent.exists()


def test_emit_warns_and_skips_bad_block(tmp_path):
    proj = _proj(BASE + '\n[[folklore]]\nid = 40\nname = "Low"\n\n[[folklore]]\nid = 91\nname = "OK"\n',
                 tmp_path)
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_folklore([proj], layout)
    assert any("80-254" in w for w in warns)
    body = layout.keyitem_name_mes("us").read_text(encoding="utf-8")
    assert "[TXID=91]OK[ENDN]" == body                     # the good block still ships


def test_emit_warns_and_skips_non_string_channel(tmp_path):
    # review find: build must WARN-AND-SKIP a non-string help/lore (never ship "42" as in-game text)
    proj = _proj(BASE + '\n[[folklore]]\nid = 93\nname = "Bad"\nhelp = 42\n'
                        '\n[[folklore]]\nid = 94\nname = "Good"\n', tmp_path)
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_folklore([proj], layout)
    assert any("must be a string" in w for w in warns)
    body = layout.keyitem_name_mes("us").read_text(encoding="utf-8")
    assert body == "[TXID=94]Good[ENDN]"                   # the bad block skipped WHOLE, the good one ships
    assert not layout.keyitem_help_mes("us").exists()


def test_build_bad_folklore_ref_is_clean_builderror(tmp_path):
    # review find: an unresolvable give_folklore at BUILD time (lint skipped) must raise BuildError,
    # not leak a raw FolkloreError traceback from deep in the emit path
    from ff9mapkit.build import BuildError, build_field
    toml = BASE + FOLK + '\n[[event]]\nzone = [[-100,-100],[100,-100],[100,-300],[-100,-300]]\n' \
                         'give_folklore = "No Such Entry"\n'
    proj = _proj(toml, tmp_path)
    try:
        build_field(proj, ModLayout(tmp_path / "mod"))
        assert False, "expected BuildError"
    except BuildError as e:
        assert "give_folklore" in str(e)


def test_emit_overlong_lore_warns_and_ships(tmp_path):
    # over-budget lore still RENDERS (just clips) -> build warns but SHIPS it; lint is the hard gate
    proj = _proj(BASE + '\n[[folklore]]\nid = 95\nname = "Long"\nlore = "' + "x" * 260 + '"\n', tmp_path)
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_folklore([proj], layout)
    assert any("WILL CLIP" in w for w in warns)
    assert "[TXID=95]" in layout.keyitem_skin_mes("us").read_text(encoding="utf-8")


def test_emit_dup_id_later_wins(tmp_path):
    p1 = _proj(BASE + '\n[[folklore]]\nid = 92\nname = "First"\n', tmp_path, "a")
    p2 = _proj(BASE.replace("4003", "4004") + '\n[[folklore]]\nid = 92\nname = "Second"\n', tmp_path, "b")
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_folklore([p1, p2], layout)
    assert any("defined twice" in w for w in warns)
    assert layout.keyitem_name_mes("us").read_text(encoding="utf-8") == "[TXID=92]Second[ENDN]"
