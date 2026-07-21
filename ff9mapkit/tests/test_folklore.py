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


# ---- displayRef (s46 rung 4: the render-rig kit lane -- studies/folklore-codex/RENDER-RIG.md sec 3) --
# Fixed reference points, all verified against the baked model tables:
#   GEO_MAIN_F0_VIV = id 8      (catalog.py's own docstring example; PRESETS["vivi"][0] == 8)
#   GEO_NPC_F0_MOG  = id 220    (archetypes.ARCHETYPES["moogle"])
#   GEO_MON_F0_BAN  = id 246    (archetypes.CREATURES["bandersnatch"])
#   GEO_MON_B3_118  = id 350    (self-prefab -- resolve_prefab round-trips to itself, no donor)
#   GEO_MAIN_B0_000 = id 5414   (an ALIAS-ONLY id -- resolve_prefab redirects to GEO_MAIN_F0_ZDN = 98,
#                                the proven case from test_model_alias.py)

def test_resolve_display_friendly_name_canonicalizes():
    assert FK.resolve_display("moogle") == "model:GEO_NPC_F0_MOG"
    assert FK.resolve_display("Bandersnatch") == "model:GEO_MON_F0_BAN"   # case-insensitive
    assert FK.resolve_display("  bandersnatch  ") == "model:GEO_MON_F0_BAN"  # surrounding whitespace ok
    assert FK.resolve_display("vivi") == "model:GEO_MAIN_F0_VIV"          # the char-preset table too


def test_resolve_display_exact_geo_name_case_insensitive():
    assert FK.resolve_display("GEO_MON_B3_118") == "model:GEO_MON_B3_118"
    assert FK.resolve_display("geo_mon_b3_118") == "model:GEO_MON_B3_118"


def test_resolve_display_numeric_id():
    assert FK.resolve_display(350) == "model:GEO_MON_B3_118"     # a bare int
    assert FK.resolve_display("350") == "model:GEO_MON_B3_118"   # a digit-string


def test_resolve_display_model_prefix_optional_and_case_insensitive():
    assert FK.resolve_display("model:GEO_MON_B3_118") == "model:GEO_MON_B3_118"
    assert FK.resolve_display("MODEL:geo_mon_b3_118") == "model:GEO_MON_B3_118"
    # with-prefix and without resolve identically
    assert FK.resolve_display("model:GEO_MON_B3_118") == FK.resolve_display("GEO_MON_B3_118")


def test_resolve_display_canonicalization_law_never_the_donor():
    # friendly names die at the kit boundary, but an ALIAS-ONLY exact GEO name still emits the
    # REQUESTED name, never the donor -- the engine's own loader replays the alias chain at load time
    assert FK.resolve_display("GEO_MAIN_B0_000") == "model:GEO_MAIN_B0_000"


def test_resolve_display_unknown_gives_catalog_near_miss_hint():
    try:
        FK.resolve_display("GEO_MON_F0_BAM")                  # a 1-char typo of GEO_MON_F0_BAN
        assert False
    except ValueError as e:
        assert "unknown model" in str(e)
        assert "Did you mean" in str(e) and "GEO_MON_F0_BAN" in str(e)


def test_resolve_display_unknown_no_close_match():
    try:
        FK.resolve_display("zzz_totally_not_a_model_zzz")
        assert False
    except ValueError as e:
        assert "unknown model" in str(e)
        assert "ff9mapkit models" in str(e)


def test_resolve_display_rejects_empty_and_whitespace():
    for bad in ("", "   ", "\t"):
        try:
            FK.resolve_display(bad)
            assert False, f"{bad!r} should be rejected"
        except FK.FolkloreError:
            pass


def test_resolve_display_rejects_embedded_whitespace():
    for bad in ("GEO MON B3 118", "model: GEO_MON_B3_118", "geo_mon_b3_118 extra"):
        try:
            FK.resolve_display(bad)
            assert False, f"{bad!r} should be rejected"
        except FK.FolkloreError as e:
            assert "whitespace" in str(e)


def test_resolve_display_rejects_garbage_types():
    for bad in (None, True, False, 3.5, ["GEO_MON_B3_118"], {"model": "x"}):
        try:
            FK.resolve_display(bad)
            assert False, f"{bad!r} should be rejected"
        except FK.FolkloreError:
            pass


def test_resolve_display_rejects_bare_model_prefix():
    for bad in ("model:", "model:   "):
        try:
            FK.resolve_display(bad)
            assert False, f"{bad!r} should be rejected"
        except FK.FolkloreError as e:
            assert "model:" in str(e)


def test_resolve_display_token_matches_the_regex_fence():
    import re
    pattern = re.compile(r"^model:GEO_[A-Z0-9_]+$")
    for ref in ("moogle", "bandersnatch", 350, "GEO_MAIN_B0_000", "model:GEO_MON_B3_118"):
        token = FK.resolve_display(ref)
        assert pattern.fullmatch(token), token
    assert FK._DISPLAY_TOKEN_RE.fullmatch("model:GEO_MON_B3_118")
    assert not FK._DISPLAY_TOKEN_RE.fullmatch("model:geo_mon_b3_118")   # lowercase never emitted
    assert not FK._DISPLAY_TOKEN_RE.fullmatch("sprite:GEO_MON_B3_118")  # a reserved-not-implemented scheme


# ---- render_patch_lines: the third token -------------------------------------------------------
def test_patch_lines_third_token_emitted():
    lines = FK.render_patch_lines([
        {"id": 80, "name": "A", "category": "bestiary", "display": "GEO_MON_B3_118"},
    ])
    assert lines == ["80 bestiary model:GEO_MON_B3_118"]


def test_patch_lines_friendly_name_display():
    lines = FK.render_patch_lines([{"id": 80, "name": "A", "display": "moogle"}])
    assert lines == ["80 lore model:GEO_NPC_F0_MOG"]


def test_patch_lines_no_display_is_two_token():
    lines = FK.render_patch_lines([{"id": 80, "name": "A", "category": "bestiary"}])
    assert lines == ["80 bestiary"]
    # None is treated the same as absent
    lines = FK.render_patch_lines([{"id": 81, "name": "B", "category": "places", "display": None}])
    assert lines == ["81 places"]


def test_patch_lines_mixed_display_and_no_display():
    lines = FK.render_patch_lines([
        {"id": 80, "name": "A", "category": "bestiary", "display": "GEO_MON_B3_118"},
        {"id": 81, "name": "B", "category": "places"},
    ])
    assert lines == ["80 bestiary model:GEO_MON_B3_118", "81 places"]


def test_patch_lines_bad_display_raises():
    try:
        FK.render_patch_lines([{"id": 80, "name": "A", "display": "zzz_totally_not_a_model_zzz"}])
        assert False
    except ValueError as e:
        assert "unknown model" in str(e)


# ---- validate_blocks: the display checks --------------------------------------------------------
def test_validate_display_clean():
    assert FK.validate_blocks([{"id": 80, "name": "X", "display": "GEO_MON_B3_118"}]) == []
    assert FK.validate_blocks([{"id": 80, "name": "X", "display": "moogle"}]) == []
    assert FK.validate_blocks([{"id": 80, "name": "X"}]) == []             # no display: not a problem


def test_validate_display_unknown_ref_reports_catalog_error_verbatim():
    probs = FK.validate_blocks([{"id": 80, "name": "X", "display": "zzz_totally_not_a_model_zzz"}])
    assert len(probs) == 1
    assert "unknown model" in probs[0] and "zzz_totally_not_a_model_zzz" in probs[0]


def test_validate_display_alias_chain_info():
    # GEO_MAIN_B0_000 has NO own-id prefab -- the engine substitutes Zidane's field body (GEO_MAIN_F0_ZDN,
    # id 98). This is not an error (the portrait still renders) -- lint names the donor so a playtest
    # ("why is this a bandit rendering Zidane?") isn't a surprise.
    probs = FK.validate_blocks([{"id": 80, "name": "X", "display": "GEO_MAIN_B0_000"}])
    assert len(probs) == 1
    assert "INFO" in probs[0]
    assert "GEO_MAIN_F0_ZDN" in probs[0]
    assert "GEO_MAIN_B0_000" in probs[0]


def test_validate_display_no_shipping_geometry_errors(monkeypatch):
    # pgid == -1: every REAL catalog entry today resolves to a shipping prefab (test_model_alias.py's
    # closure census), so this defensive branch is exercised via a monkeypatch of resolve_prefab itself.
    monkeypatch.setattr("ff9mapkit.models.extract.resolve_prefab", lambda token: (token, -1, 0))
    probs = FK.validate_blocks([{"id": 80, "name": "X", "display": "GEO_MON_B3_118"}])
    assert len(probs) == 1
    assert "ERROR" in probs[0]
    assert "no shipping geometry" in probs[0]


def test_validate_display_not_gated_on_category():
    # a "places" entry showing a landmark model is legitimate -- display is orthogonal to category
    probs = FK.validate_blocks([{"id": 80, "name": "X", "category": "places", "display": "GEO_MON_B3_118"}])
    assert probs == []


# ---- build's _emit_folklore: warn-and-drop-display-only (never skip the entry) -------------------
FOLK_DISPLAY = """
[[folklore]]
id = 84
name = "Good Portrait"
display = "GEO_MON_B3_118"

[[folklore]]
id = 85
name = "Bad Portrait"
display = "zzz_totally_not_a_model_zzz"
"""


def test_emit_display_third_token_and_drop_on_failure(tmp_path):
    proj = _proj(BASE + FOLK_DISPLAY, tmp_path)
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_folklore([proj], layout)
    assert any("display" in w and "zzz_totally_not_a_model_zzz" in w for w in warns)
    body_lines = [ln for ln in layout.folklore_patch.read_text(encoding="utf-8").splitlines()
                  if not ln.startswith("#")]
    assert "84 lore model:GEO_MON_B3_118" in body_lines        # the good display -> third token
    assert "85 lore" in body_lines                              # the bad display DROPS, entry still ships
    # the entry itself (name/text) was never skipped for its bad display
    name_body = layout.keyitem_name_mes("us").read_text(encoding="utf-8")
    assert "[TXID=84]Good Portrait[ENDN]" in name_body
    assert "[TXID=85]Bad Portrait[ENDN]" in name_body


def test_emit_display_absent_stays_two_token(tmp_path):
    proj = _proj(BASE + '\n[[folklore]]\nid = 86\nname = "NoPortrait"\n', tmp_path)
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_folklore([proj], layout)
    assert not any("display" in w for w in warns)
    body = layout.folklore_patch.read_text(encoding="utf-8")
    assert "86 lore\n" in body or body.rstrip().endswith("86 lore")


def test_emit_dup_id_message_mentions_display_drop_too(tmp_path):
    p1 = _proj(BASE + '\n[[folklore]]\nid = 92\nname = "First"\ndisplay = "GEO_MON_B3_118"\n',
               tmp_path, "a")
    p2 = _proj(BASE.replace("4003", "4004") + '\n[[folklore]]\nid = 92\nname = "Second"\n', tmp_path, "b")
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_folklore([p1, p2], layout)
    dup = next(w for w in warns if "defined twice" in w)
    assert "display" in dup.lower()
    # the later (displayless) block really did win -- no stray third token from the dropped first block
    body_lines = [ln for ln in layout.folklore_patch.read_text(encoding="utf-8").splitlines()
                  if not ln.startswith("#")]
    assert "92 lore" in body_lines
