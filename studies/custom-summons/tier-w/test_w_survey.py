r"""Tests for TIER W rung 5 -- THE SURVEY (``w_survey.py``).

This module is a READER, not a builder: every fact it reports comes straight through B1's
(``reskin.py``), B2's (``rescore.py`` / ``summon_camera.py``) or B3's (``retime_derive.py`` /
``summon_inspect.py``) own detectors, so these tests exercise it against the REAL extracted corpus
and the real install rather than a hand-built synthetic container -- there is nothing to isolate a
detector FROM here that ``test_reskin.py`` / ``test_rescore.py`` / ``test_retime_derive.py`` do not
already isolate it from at the source.  Every test that needs the corpus or the install is skipped
cleanly when absent, exactly as the sibling lanes' test modules already do.

    py -m pytest studies/custom-summons/tier-w/test_w_survey.py -q
"""
from __future__ import annotations

import glob
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import w_survey as SV                                            # noqa: E402  (sets up sys.path)
import reskin as RS                                               # noqa: E402
import rescore as R                                                # noqa: E402
import summon_camera as W                                          # noqa: E402

CORPUS = W.SCRATCH_CORPUS
have_corpus = bool(glob.glob(os.path.join(CORPUS, "ef*.bytes")))
needs_corpus = pytest.mark.skipif(not have_corpus, reason="no extracted corpus at %s" % CORPUS)


def _has_install() -> bool:
    try:
        from ff9mapkit import config
        return bool(config.find_game_path(None))
    except Exception:
        return False


needs_install = pytest.mark.skipif(not _has_install(), reason="no FF9 install resolvable")


def _blob(effect: int) -> bytes:
    path = os.path.join(CORPUS, "ef%03d.bytes" % effect)
    with open(path, "rb") as fh:
        return fh.read()


# ============================================================ (0) THE STATIC TABLES
def test_summon_table_full_ids_are_all_distinct():
    fulls = [full for _n, full, _s in SV.SUMMON_TABLE]
    assert len(fulls) == 17
    assert len(set(fulls)) == 17


def test_summon_table_has_seventeen_rows_and_rebirth_flame_shares_its_own_full_and_short():
    row = next(r for r in SV.SUMMON_TABLE if r[0] == "Rebirth Flame")
    assert row[1] == row[2] == 225


def test_dll_frame_gates_keys_are_summon_table_ids():
    ids = {full for _n, full, _s in SV.SUMMON_TABLE} | {short for _n, _f, short in SV.SUMMON_TABLE}
    assert set(SV.DLL_FRAME_GATES) <= ids


def test_texanim_class_matches_five_named_effects():
    assert sorted(SV.TEXANIM_CLASS) == [38, 177, 493, 494, 495]


# ============================================================ (1) op_census -- the op-25 lesson
@needs_corpus
def test_op_census_ef227_matches_the_tier_r_a1_op_census():
    """A1-op-census.txt: c0 156 HLE call sites (op25 x6), c1 285 call sites (op25 x3)."""
    oc = SV.op_census(_blob(227), "ef227")
    assert oc.total_calls == 156 + 285
    assert oc.op25 == 6 + 3
    assert 25 in oc.distinct_ops


@needs_corpus
def test_op_census_ef447_is_the_ark_short_lesson_zero_op25():
    """Ark Short ships a full creature package and draws it via op 24 only -- never op 25."""
    oc = SV.op_census(_blob(447), "ef447")
    assert oc.op25 == 0
    assert oc.total_calls > 0                    # it is not a silent/empty program


@needs_corpus
def test_op_census_ef381_ark_full_does_call_op25():
    oc = SV.op_census(_blob(381), "ef381")
    assert oc.op25 >= 1


# ============================================================ (2) clut_survey
@needs_corpus
def test_clut_survey_ef381_is_multi_writer_and_not_dual_depth():
    cs = SV.clut_survey(_blob(381), effect=381)
    assert cs.multi_writer_cells
    assert (0, 242) in cs.multi_writer_cells


@needs_corpus
def test_clut_survey_ef447_is_dual_depth():
    cs = SV.clut_survey(_blob(447), effect=447)
    assert cs.dual_depth_cells == ((0, 242),)


@pytest.mark.parametrize("effect", [38, 177, 493, 494, 495])
@needs_corpus
def test_clut_survey_texanim_armed_on_the_five_named_effects(effect):
    cs = SV.clut_survey(_blob(effect), effect=effect)
    assert cs.texanim_armed
    assert cs.texanim_bytes > 0


@needs_corpus
def test_clut_survey_ef227_texanim_is_empty_and_no_hazards():
    cs = SV.clut_survey(_blob(227), effect=227)
    assert not cs.texanim_armed
    assert not cs.multi_writer_cells
    assert not cs.dual_depth_cells


# ============================================================ (3) camera_survey
@needs_corpus
def test_camera_survey_ef227_three_shots_no_dynamic():
    """agent4.md sec 2's matrix: Bahamut is 3 shots / 1,1,1 sequences, 0 dynamic ops."""
    cam = SV.camera_survey(_blob(227), "ef227")
    assert cam.shots == 3
    assert cam.dynamic_ops == 0


@needs_corpus
def test_camera_survey_flags_a_fenrir_genuine_alternate():
    """agent4.md sec 4 item 6: the two Fenrirs are the corpus's only 3-sequence GENUINE alternates."""
    cam = SV.camera_survey(_blob(210), "ef210")
    assert cam.max_sequences == 3
    assert cam.alternates_differ_shots


@needs_corpus
def test_camera_survey_ef000_carries_dynamic_ops():
    cam = SV.camera_survey(_blob(0), "ef000")
    assert cam.dynamic_ops >= 1


# ============================================================ (4) creature_signature + twin_groups
@needs_corpus
def test_creature_signature_matches_between_phoenix_and_rebirth_flame():
    assert SV.creature_signature(_blob(211)) == SV.creature_signature(_blob(225))


@needs_corpus
def test_creature_signature_differs_between_phoenix_and_bahamut():
    assert SV.creature_signature(_blob(211)) != SV.creature_signature(_blob(227))


@needs_corpus
def test_creature_signature_is_none_for_a_creatureless_container():
    assert SV.creature_signature(_blob(0)) is None


@needs_corpus
def test_twin_groups_reproduces_the_three_measured_groups():
    groups = SV.twin_groups(CORPUS)
    triples = sorted(tuple(sorted(v)) for v in groups.values())
    assert (210, 226) in triples
    assert (211, 225) in triples
    assert (431, 432, 435, 438, 439, 498) in triples
    assert len(triples) == 3                     # exactly these three, nothing else


# ============================================================ (5) program_class_rows
@needs_corpus
def test_program_class_rows_recovers_ef227_c0_as_clean():
    rows = SV.program_class_rows(CORPUS)
    assert rows["ef227:c0"].verdict == "clean"


# ============================================================ (6) survey_effect -- the aggregate row
@needs_corpus
def test_survey_effect_ef211_matches_agent4_facts():
    """Phoenix: single-chunk, texanim-empty, clean 7-phase program, 1 shot, zero headroom peak
    (not this module's concern) -- and it is Rebirth Flame's twin."""
    twins = SV.twin_groups(CORPUS)
    prog = SV.program_class_rows(CORPUS)
    row = SV.survey_effect(_blob(211), 211, "ef211", twins=twins, prog_rows=prog)
    assert row.has_creature
    assert row.drawn
    assert not row.texanim_armed
    assert not row.hazard
    assert row.shots == 1
    assert row.twin_partners == (225,)
    assert row.program_classes == (("ef211:c0", "clean", 7, 238),)


@needs_corpus
def test_survey_effect_ef447_never_drawn_flag():
    row = SV.survey_effect(_blob(447), 447, "ef447")
    assert row.has_creature
    assert row.op25 == 0
    assert not row.drawn


@needs_corpus
def test_survey_effect_ark_full_carries_its_dll_gate():
    row = SV.survey_effect(_blob(381), 381, "ef381")
    assert "SFX.cs:607-613" in row.dll_gate


@needs_corpus
def test_survey_effect_bahamut_carries_no_dll_gate():
    row = SV.survey_effect(_blob(227), 227, "ef227")
    assert row.dll_gate == ""


# ============================================================ (7) load_effect
@needs_corpus
def test_load_effect_prefers_the_corpus_over_the_install():
    blob, src = SV.load_effect(227, root=CORPUS)
    assert src.replace("\\", "/").endswith("ef227.bytes")
    assert blob == _blob(227)


@needs_install
def test_load_effect_falls_back_to_the_install_when_absent_from_the_corpus(tmp_path):
    blob, src = SV.load_effect(227, root=str(tmp_path))
    import hashlib
    assert hashlib.sha256(blob).hexdigest() == R.EXPECTED_STOCK_SHA[227]


# ============================================================ (8) ef038 side-recon
@needs_corpus
def test_ef038_side_recon_finds_no_vram_transfer_ops():
    lines = SV.ef038_texanim_side_recon(CORPUS)
    joined = "\n".join(lines)
    assert "ef038:c0" in joined
    assert "NONE" in joined
    assert "loader-script opcode 0x07" in joined


def test_ef038_side_recon_handles_a_missing_corpus_file(tmp_path):
    lines = SV.ef038_texanim_side_recon(str(tmp_path))
    assert any("not found" in ln for ln in lines)


# ============================================================ (9) corpus_sweep + self_check
@needs_corpus
def test_corpus_sweep_zero_crashes_over_the_whole_corpus():
    sw = SV.corpus_sweep(CORPUS)
    assert not sw.crashes
    assert len(sw.rows) == len(W.corpus_paths(CORPUS))


@needs_corpus
def test_corpus_sweep_creature_bearing_count_is_24():
    sw = SV.corpus_sweep(CORPUS)
    assert sum(1 for r in sw.rows if r.has_creature) == 24


@needs_corpus
def test_self_check_passes_on_the_real_corpus():
    sc = SV.self_check(CORPUS)
    assert sc.ok, "\n".join(sc.lines)


def test_self_check_reports_failure_with_no_corpus(tmp_path):
    sc = SV.self_check(str(tmp_path))
    assert not sc.ok
    assert any("no extracted corpus" in ln for ln in sc.lines)


# ============================================================ (10) formatting + CLI smoke
@needs_corpus
def test_describe_row_flags_never_drawn_creature():
    row = SV.survey_effect(_blob(447), 447, "ef447")
    joined = "\n".join(SV.describe_row(row))
    assert "NEVER DRAWN" in joined


@needs_corpus
def test_describe_summons_lists_every_summon_name_and_the_texanim_tail():
    lines = SV.describe_summons(CORPUS)
    joined = "\n".join(lines)
    for name, _full, _short in SV.SUMMON_TABLE:
        assert name in joined
    assert "TEXANIM SIDE-RECON" in joined


@needs_corpus
def test_describe_corpus_summary_matches_self_check_facts():
    lines = SV.describe_corpus(CORPUS)
    joined = "\n".join(lines)
    assert "creature-bearing containers" in joined
    assert "[381, 447]" in joined              # the multi-writer census, W4-gate-consistent


@needs_corpus
def test_cli_ef_mode_returns_zero(capsys):
    rc = SV.main(["--ef", "211", "--root", CORPUS])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ef211" in out


@needs_corpus
def test_cli_self_check_mode_returns_zero_on_the_real_corpus(capsys):
    rc = SV.main(["--self-check", "--root", CORPUS])
    assert rc == 0


def test_cli_self_check_mode_returns_nonzero_with_no_corpus(tmp_path, capsys):
    rc = SV.main(["--self-check", "--root", str(tmp_path)])
    assert rc == 1


def test_cli_with_no_args_prints_help_and_returns_one(capsys):
    rc = SV.main([])
    assert rc == 1
