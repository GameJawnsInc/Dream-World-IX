"""Pure-logic tests for the ``[[summon]]`` block-schema layer (``content/summon.py``) -- NO install / NO
SCRATCH / NO deploy write needed, so every test here ALWAYS RUNS (the fresh-worktree skip trap does not
touch them; ``deploy.normalize_spec`` / ``sfxhybrid_updates`` are pure).

The block-schema layer's OWN jobs: donor NAME->id resolution, the field-schema requirements (donor +
model required), unknown-key + group hygiene, and the model-path check. Structural validation
(lane/id/private_ef/hide_mask/...) is DELEGATED to the deploy engine -- so these tests also confirm the
block -> deploy hand-off produces the M1b acceptance spec + ini. The .seq splice / FBX byte-compare half
of the section-4 acceptance is install-gated and lives in ``test_summon_block_accept.py``.
"""
import pytest

from ff9mapkit.content import summon
from ff9mapkit.summons import deploy


# the 7 censused Bahamut body mesh keys (build_thomas.py:174-179) -- the M1b bench hide list
BENCH_HIDE_KEYS = ["0033B990", "0033B9D0", "0035BAD0", "0035BA90", "0034BA10", "0034BA50", "0097BD02"]


def acceptance_block():
    """The section-4 acceptance inputs: the live-proven M1b hybrid Thomas."""
    return {
        "donor": 227, "model": "thomas_skinned.fbx", "lane": "hybrid",
        "id": 6201, "name": "GEO_MON_B0_M201", "group": "MON", "private_ef": 84,
        "hide_meshes": list(BENCH_HIDE_KEYS), "node_count": 93, "hide_mask": "0x3",
    }


# ------------------------------------------------------------------ the acceptance spec + ini
def test_acceptance_block_resolves_to_the_m1b_spec():
    spec = summon.resolve_spec(acceptance_block())
    assert spec["lane"] == "hybrid"
    assert spec["donor"] == 227
    assert spec["id"] == 6201 and spec["name"] == "GEO_MON_B0_M201"
    assert spec["private_ef"] == 84
    assert spec["hide_meshes"] == BENCH_HIDE_KEYS
    assert spec["hide_native"] is True and spec["hide_mask"] == "0x3" and spec["node_count"] == 93
    assert spec["apply_column_scale"] is False


def test_acceptance_sfxhybrid_ini_matches_runbook_exactly():
    """The armed [SfxHybrid] block (keys + order + values) == DESIGN section 2.4 / RUNBOOK section 5."""
    spec = summon.resolve_spec(acceptance_block())
    assert list(deploy.sfxhybrid_updates(spec, log=True).items()) == [
        ("Enabled", "1"), ("EffectId", "227"), ("ModelPath", "GEO_MON_B0_M201"),
        ("HideNative", "1"), ("HideMask", "0x3"), ("NodeCount", "93"),
        ("ApplyColumnScale", "0"), ("Log", "1"),
    ]
    assert deploy.render_sfxhybrid_block(spec, log=True) == (
        "[SfxHybrid]\n"
        "Enabled = 1\nEffectId = 227\nModelPath = GEO_MON_B0_M201\n"
        "HideNative = 1\nHideMask = 0x3\nNodeCount = 93\nApplyColumnScale = 0\nLog = 1\n")


def test_acceptance_mint_directive_reproduces_the_live_line():
    from ff9mapkit.models import mint
    spec = summon.resolve_spec(acceptance_block())
    man = mint.resolve_mint({"id": spec["id"], "name": spec["name"], "fbx": "x.fbx"})
    assert man["directive"] == "3DModel 6201 GEO_MON_B0_M201"


def test_acceptance_block_validates_clean():
    assert summon.validate_blocks([acceptance_block()]) == []


# ------------------------------------------------------------------ defaults (delegated to deploy)
def test_minimal_block_defaults():
    spec = summon.resolve_spec({"donor": 227, "model": "m.fbx"})
    assert spec["lane"] == "hybrid"                       # hybrid is the default lane
    assert spec["group"] == "MON" and spec["form"] == "B0"
    assert spec["id"] is None and spec["private_ef"] is None   # deferred -> deploy allocates at emit
    assert spec["hide_native"] is True and spec["apply_column_scale"] is False
    assert spec["hide_mask"] == "0x3" and spec["node_count"] == 93   # deploy's bench defaults
    assert spec["clips"] == "all" and spec["staging"] == "donor"


# ------------------------------------------------------------------ donor name<->id (this layer's job)
def test_donor_name_resolves_to_id():
    assert summon.resolve_donor("Bahamut__Full") == (227, "Bahamut__Full")
    assert summon.resolve_donor("Odin__Full") == (261, "Odin__Full")


def test_donor_numeric_backfills_the_name():
    assert summon.resolve_donor(227) == (227, "Bahamut__Full")
    assert summon.resolve_donor("227") == (227, "Bahamut__Full")


def test_donor_numeric_without_a_known_name_resolves_id_only():
    did, name = summon.resolve_donor(100)                 # a real non-summon effect: no catalogued name
    assert did == 100 and name is None


def test_donor_name_block_is_rewritten_to_numeric_for_deploy():
    nb = summon.numeric_block({"donor": "Bahamut__Full", "model": "m.fbx"})
    assert nb["donor"] == 227
    # and the whole spec resolves (deploy takes the numeric donor without complaint)
    assert summon.resolve_spec({"donor": "Bahamut__Full", "model": "m.fbx"})["donor"] == 227


def test_donor_unknown_name_is_refused():
    with pytest.raises(summon.SummonBlockError, match="not a known summon effect"):
        summon.resolve_donor("Gilgamesh__Full")


def test_donor_absent_id_is_refused():
    with pytest.raises(summon.SummonBlockError, match="stock-ABSENT"):
        summon.resolve_donor(84)                          # Unused_84 has no creature to inherit


def test_donor_out_of_range_is_refused():
    with pytest.raises(summon.SummonBlockError, match="out of range"):
        summon.resolve_donor(9999)


def test_donor_bool_is_refused():
    with pytest.raises(summon.SummonBlockError):
        summon.resolve_donor(True)


# ------------------------------------------------------------------ field-schema requirements
def test_missing_donor_is_refused():
    assert _has(summon.validate_blocks([{"model": "m.fbx"}]), "needs a `donor`")


def test_missing_model_is_refused():
    assert _has(summon.validate_blocks([{"donor": 227}]), "needs a `model`")


def test_unknown_key_is_refused():
    assert _has(summon.validate_blocks([{"donor": 227, "model": "m.fbx", "bogus": 1}]), "unknown key")


def test_unknown_donor_name_surfaces_in_validate():
    assert _has(summon.validate_blocks([{"donor": "Nope__Full", "model": "m.fbx"}]),
                "not a known summon effect")


# ------------------------------------------------------------------ structural rejections (delegated)
def test_bad_lane_is_refused():
    assert _has(summon.validate_blocks([{"donor": 227, "model": "m.fbx", "lane": "warp"}]),
                "lane must be one of")


def test_mint_id_below_band_is_refused():
    assert _has(summon.validate_blocks([{"donor": 227, "model": "m.fbx", "id": 500}]), "below the mint band")


def test_real_geo_name_is_refused():
    assert _has(summon.validate_blocks(
        [{"donor": 227, "model": "m.fbx", "id": 6201, "name": "not a geo name"}]), "must look like")


def test_unknown_group_is_refused():
    # deploy defers group->ModelType until a name is derived; the schema layer catches it at lint
    assert _has(summon.validate_blocks([{"donor": 227, "model": "m.fbx", "group": "XXX"}]), "unknown group")


def test_private_ef_equal_to_donor_is_refused():
    assert _has(summon.validate_blocks([{"donor": 227, "model": "m.fbx", "private_ef": 227}]),
                "equals donor")


def test_private_ef_not_in_absent_set_is_refused():
    assert _has(summon.validate_blocks([{"donor": 227, "model": "m.fbx", "private_ef": 100}]),
                "not a stock-absent")


def test_private_ef_bench_value_ok():
    assert summon.validate_blocks([{"donor": 227, "model": "m.fbx", "private_ef": 84}]) == []


def test_hide_meshes_bad_key_is_refused():
    assert _has(summon.validate_blocks([{"donor": 227, "model": "m.fbx", "hide_meshes": ["nothex"]}]),
                "not a hex mesh key")


def test_staging_enum_is_refused():
    assert _has(summon.validate_blocks(
        [{"donor": 227, "model": "m.fbx", "lane": "overlay", "staging": "flyby"}]), "staging must be")


# ------------------------------------------------------------------ model-path existence (base_dir)
def test_model_path_existence_ok(tmp_path):
    (tmp_path / "m.fbx").write_text("x")
    assert summon.validate_blocks([{"donor": 227, "model": "m.fbx"}], base_dir=tmp_path) == []


def test_model_path_missing_is_refused(tmp_path):
    assert _has(summon.validate_blocks([{"donor": 227, "model": "missing.fbx"}], base_dir=tmp_path),
                "file not found")


def test_model_path_not_checked_without_base_dir():
    # a pure schema check (no base_dir) must not fail on a non-existent model path
    assert summon.validate_blocks([{"donor": 227, "model": "anywhere.fbx"}]) == []


# ------------------------------------------------------------------ multi-block indexing + lint notes
def test_validate_blocks_indexes_multiple():
    problems = summon.validate_blocks([acceptance_block(), {"model": "m.fbx"}])
    assert any(p.startswith("[[summon]] #1") and "needs a `donor`" in p for p in problems)


def test_lint_notes_emit_the_vfx1_reminder():
    notes = summon.lint_notes([{"donor": 227, "model": "m.fbx", "private_ef": 84}])
    assert any("vfx1" in n and "private_ef=84" in n and "MUST NOT edit Actions.csv" in n for n in notes)


def test_lint_notes_omitted_private_ef_shows_auto_not_the_bench_constant():
    """An OMITTED private_ef is auto-allocated at deploy (the first free stock-absent id, NOT the bench
    DEFAULT_PRIVATE_EF=84) -- the reminder must NOT name 84, or a user wires vfx1 at an empty effect."""
    notes = summon.lint_notes([{"donor": 227, "model": "m.fbx"}])   # no private_ef
    vfx1 = next(n for n in notes if "vfx1" in n)
    assert "<auto>" in vfx1
    assert "private_ef=84" not in vfx1


def test_lint_notes_flag_ignored_cross_lane_keys():
    hybrid_with_overlay_key = summon.lint_notes([{"donor": 227, "model": "m.fbx", "clips": "all"}])
    assert any("overlay-only key" in n for n in hybrid_with_overlay_key)
    overlay_with_hybrid_key = summon.lint_notes(
        [{"donor": 227, "model": "m.fbx", "lane": "overlay", "hide_mask": "0x3"}])
    assert any("hybrid-only key" in n for n in overlay_with_hybrid_key)


def test_lint_notes_never_raise_on_a_broken_block():
    # a block that won't validate must not blow up the advisory pass
    assert isinstance(summon.lint_notes([{"lane": "overlay"}, "not a table"]), list)


# ------------------------------------------------------------------ emit dispatch (routes to deploy)
def test_emit_routes_to_the_right_lane_emitter(monkeypatch):
    calls = {}

    def fake(spec, mod_root, game, *, work_dir=None):
        calls["spec"], calls["mod"], calls["game"] = spec, mod_root, game
        return {"ok": spec["lane"]}

    monkeypatch.setattr(deploy, "emit_hybrid", fake)
    monkeypatch.setattr(deploy, "emit_overlay", fake)
    out = summon.emit({"donor": "Bahamut__Full", "model": "m.fbx"}, "MODROOT", "GAME")
    assert out == {"ok": "hybrid"}
    assert calls["spec"]["donor"] == 227 and calls["mod"] == "MODROOT"     # name resolved, dispatched
    out2 = summon.emit({"donor": 227, "model": "m.fbx", "lane": "overlay"}, "MODROOT", "GAME")
    assert out2 == {"ok": "overlay"}


def _has(problems, needle) -> bool:
    return any(needle in p for p in problems)
