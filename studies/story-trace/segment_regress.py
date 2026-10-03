"""THE REGRESSION GATE for the shared segment machinery: every change to ``segment_trace``, ``segment_drive``,
``o2_alexandria``, ``o3_prima_vista``, ``o4_castle`` or the harness verbs they drive must leave every O1 output
(research/o2_design.md, section 1.6), every O2 output (research/o3_design.md, section 1.4), every O3 output
(research/o4_design.md, section 1.4) AND every O4 output (research/o5_design.md, section 1.4) byte-identical, O3's
battle-beat tests (G13) and O3's dry run (G14) green, O4's tests (G19) and O4's dry run (G20) green, O5's FakeGame and
driver tests (G26) and O5's dry run (G27) green, and the O1-O4 driver tests and the fake's beat, input, story-trace and
machine-beat functions at their pinned sources (G21).

    py studies/story-trace/segment_regress.py --capture      # G0, once, BEFORE the O2 refactor: the O1 baseline
    py studies/story-trace/segment_regress.py --capture-o2   # G0', once, BEFORE any O3 code change: the O2 baseline
    py studies/story-trace/segment_regress.py --capture-o3   # G0'', once, BEFORE any O4 code change: the O3 baseline
    py studies/story-trace/segment_regress.py --capture-o4   # G0''', once, BEFORE any O5 code change: the O4 baseline
    py studies/story-trace/segment_regress.py --rebaseline-source NAME --reason TEXT   # G21: re-pin ONE source
    py studies/story-trace/segment_regress.py                # G1-G27; exit 0 only if every item passes

Exit 2 means an archive or a baseline is missing: the gate was not run, which is not a pass.

The O1 items import only the O1 modules (``o1_opening``, ``o1_dryrun``), the O2 items only the O2 modules
(``o2_alexandria``, ``o2_dryrun``, imported inside their functions), each through its public names, so each baseline
was captured at the code before the change it guards and the same file judges the changed code:
  G0  --capture: the full ``(checks, report)`` of the archived PROVEN session o1e, of the archived VOID session
      o1d, of every o1_dryrun case (its 15 CASES and "predictions-changed"), of the G6 noise mutant, and
      ``offline_check(v4)``, plus the G7 tests collected -> ``research/o1_regress_baseline.json`` (LF, ``-text``).
      It refuses to overwrite a baseline, and to write one the pre-refactor code does not itself pass.
  G1  ``analyse(o1e, v4)``: the report is the archived ``o1_report.txt`` exactly, and the baseline's; the checks
      are the baseline's; PROVEN with 6 checks, all True.
  G2  the CLI ``o1_opening.py --analyse o1e --predictions v4`` exits 0 and prints that report.
  G3  every dry-run case's ``(checks, report)`` is byte-equal to the baseline's -- every detail and every report
      line, not only the verdicts ``o1_dryrun.result`` compares -- and ``run_cases(v4)`` still returns 0.
  G4  ``offline_check(v4)`` equals the baseline's ``[(ok, what, detail)]``.
  G5  o1d's ``(checks, report)`` is byte-equal to the baseline's: a real VOID path.
  G6  THE O1 NOISE MUTANT: ``six(v4)`` plus a FIELD-mode (m 1) ``Global.Byte[206]`` row in the F runs only reads
      O1-NULL False, O1-JOIN True, NOT PROVEN. O1's noise is ``{not_m: 1, target}``: it covers m != 1 only, so an
      ``is_noise`` widened to every mode reads PROVEN here. No stock store of ``Global.Byte[206]`` exists in 50 or
      in any of the chain's 20 donors, so no field-mode JOIN can key the row: it is an addition-buffer row
      (``add`` 1, ``tag`` -1), which ``storytrace.digest`` keys WITHOUT a join -- a field-mode ``Global.Byte[206]``
      key that reaches O1-NULL. Its ``(checks, report)`` is byte-equal to the baseline's too.
  G7  ``pytest tests/test_harness.py -k "o1_ or overlay_hint or segment"`` from ``ff9mapkit/``: every test passed,
      0 failed, 0 skipped, 0 errors; every test the baseline collected still runs, and so does every name in
      :data:`REQUIRED_TESTS`.
  G0' --capture-o2: the full ``(checks, report)`` of the archived PROVEN session story-o2 read with
      ``o2_predictions_v1``; of every o2_dryrun session case (its CASES and "predictions-changed"); every o2_dryrun
      unit case's and offline mutant's ``(name, ok, detail)``; ``offline_check(v1)``; the G12 tests collected; the
      HEAD and v1's sha -> ``research/o2_regress_baseline.json`` (LF, ``-text``). It refuses to overwrite a
      baseline, and to write one unless G8-G12's baseline-free halves pass at the code it captures.
  G0'' --capture-o3 (research/o4_design.md 1.4): the full ``(checks, report)`` of the archived PROVEN session
      story-o3 read with ``o3_predictions_v1``; of every o3_dryrun session case (its CASES and
      "predictions-changed"); every o3_dryrun unit's ``(name, ok, detail)`` (its units and offline mutants, the
      movie-skip A/B's included); ``O3.offline_check(v1)``; the tests G13 collects; the HEAD and v1's sha; and
      ``sources``, G21's pins -> ``research/o3_regress_baseline.json`` (LF, ``-text``). It refuses to overwrite a
      baseline, and to write one unless G7, G12, G13 and G15-G18's baseline-free halves pass at the code it
      captures. It first takes TWO readings and refuses when they differ (a temporary path, a clock or a random in an
      output): every temporary root the replica makes reads ``<tmp>`` in both (and in the baseline), and anything
      still differing is named, never excluded silently.
  G8  ``O2.analyse(story-o2, pred_path=v1)``: the report is the archived ``o2_report.txt`` exactly, and the
      baseline's; the checks are the baseline's; PROVEN with 15 checks, all True.
  G9  the CLI ``o2_alexandria.py --analyse story-o2 --predictions v1`` exits 0 and prints that report.
  G10 every o2_dryrun session case's ``(checks, report)`` is byte-equal to the baseline's, every unit case's and
      offline mutant's ``(name, ok, detail)`` too, and ``run_cases(v1)`` still returns 0 printing "N/N cases as
      registered" (86 at the capture). The gate replicates run_cases's loop step for step, as G3 does O1's, so every
      session gets the label run_cases gives it (``s0``, ``s1``, ... in creation order).
      G10 IS THE ONLY VOID-PATH BASELINE O2 HAS: the story-o2 archive holds six covered runs and no VOID, so G8/G9
      never take the coverage rule's VOID or A-BEATS path, nor VOID-ASYM's. An edit to the coverage rule, the
      V-classes or VOID-ASYM is proven O2-neutral by G10's synthetic sessions alone.
  G11 ``O2.offline_check(v1)`` equals the baseline's ``[(ok, what, detail)]``: 5 checks, all PASS (it reads the O2
      build and the stock assets, read-only).
  G12 ``pytest tests/test_harness.py -k "o2_ or rehearse"`` from ``ff9mapkit/``: every test passed, 0 failed, 0
      skipped, 0 errors; every test the baseline collected still runs, and so does every name in
      :data:`REQUIRED_TESTS_O2`.
  G13 ``pytest tests/test_harness.py -k "o3_drive or o3_skip_ab"`` from ``ff9mapkit/`` (research/o3_design.md 1.4,
      from B4): every test passed, 0 failed, 0 skipped, 0 errors, and every name in :data:`REQUIRED_TESTS_O3` among
      them -- the battle beat's driver tests and the movie-skip policy's, so a later edit to ``segment_drive``
      re-runs them, and the movie-skip A/B's test (``--skip-ab`` through its files: the pairing, the reading, the
      exit codes), which reads the install's stock scripts -- where it cannot, it skips, and a skip fails the item;
      and O4's proof that the Chanbara policy is opt-in (research/o4_design.md 9 B4: without it a prompt-shaped page
      is rule 7's, as O3's). No baseline: the list is the floor.
  G14 ``o3_dryrun.run_cases`` (the review, research/o3_design.md 11.7 #12) on the frozen O3 predictions once they
      exist (``o3_predictions_v1.json``), else on the draft: it returns 0 printing "N/N cases as registered", N at least
      :data:`O3_DRYRUN_FLOOR`. O3Segment subclasses O2Segment and runs on ``segment_trace``, ``segment_drive`` and
      ``o2_alexandria``, so a later edit to any of them must keep O3's dry run green too (1.3) -- every check failing
      on its mutant, every case EXACT. No baseline: the count is the floor (a dropped case falls under it).
  G15 ``O3.analyse(story-o3, pred_path=v1)``: the report is the archived ``o3_report.txt`` exactly, and the
      baseline's; the checks are the baseline's; PROVEN with 17 checks, all True.
  G16 the CLI ``o3_prima_vista.py --analyse story-o3 --predictions v1`` exits 0 and prints that report.
  G17 every o3_dryrun session case's ``(checks, report)`` and every unit's ``(name, ok, detail)`` is the baseline's,
      byte for byte (each temporary root read as ``<tmp>``), and ``run_cases(v1)`` still returns 0 printing "N/N
      cases as registered" (102 at the capture), N counted from the replica: its sessions plus its units. The gate
      replicates run_cases's loop step for step, as G10 does O2's.
      G17 IS O3'S VOID-PATH BASELINE: the story-o3 archive holds six covered runs and no VOID, so G15/G16 never take
      the coverage rule's VOID paths, VOID-ASYM's, A-START's or A-NOEND's. An edit to any of them is proven
      O3-neutral by G17's synthetic sessions alone.
  G18 ``O3.offline_check(v1)`` equals the baseline's ``[(ok, what, detail)]``: 6 checks, all PASS (it reads O1's
      build and the stock assets, read-only).
  G19 ``pytest tests/test_harness.py -k "o4_ or fake_chanbara or fake_keyon"`` from ``ff9mapkit/``
      (research/o4_design.md 1.4, from B3): every test passed, 0 failed, 0 skipped, 0 errors, and every name in
      :data:`REQUIRED_TESTS_O4` among them -- O4's FakeGame machine beats (H10-H12), the Chanbara policy's pure half
      and its executor on the fake, o4_castle's own tests (C1, C2). No baseline: the list is the floor.
  G20 ``o4_dryrun.run_cases`` (research/o4_design.md 9 C2) on the frozen O4 predictions once they exist
      (``o4_predictions_v1.json``), else on the draft (which reads the O4 chain's campaign.toml): it returns 0
      printing "N/N cases as registered", N at least :data:`O4_DRYRUN_FLOOR`. O4Segment subclasses O3Segment and
      runs on ``segment_trace``, ``segment_drive``, ``o2_alexandria`` and ``o3_prima_vista``, so a later edit to any of
      them must keep O4's dry run green too -- every check failing on its mutant, every case EXACT. No baseline: the
      count is the floor (a dropped case falls under it).
  G21 THE DRIVER'S SOURCE PINS (research/o4_design.md 1.4, rev. 2; research/o5_design.md 1.4): every name in the
      UNION of the O3 and the O4 baselines' ``sources`` -- each test G7, G12 and G13 collected at the O3 capture and
      fakegame.py's existing beat and input functions; each test G19 collected at the O4 capture and the fake's story
      sink and machine beats (:data:`FAKE_PINS_O4`) -- by its qualified name (``<file>::<qualname>``) still exists,
      and the sha256 of its ``ast.dump(node, include_attributes=False)`` equals its baseline's, or, when
      ``research/source_pins.json`` re-baselines it, that name's LATEST row's ``new``. A name pinned by BOTH baselines
      is no union (:func:`union_sources` refuses it; the O4 capture never writes one). A row is ``{"name", "old",
      "new", "reason", "head"}``, appended only by ``--rebaseline-source NAME --reason TEXT`` (NAME looked up in either
      baseline): it refuses an empty reason, a name not pinned, an ``old`` that is not the pin in force, and a source
      that is already its pin in force (nothing changed); the commit that changes the source carries its row, and the
      gate replays every row the same way. Comments and whitespace do not count (the AST dump); any code edit does, a
      docstring's included, and a renamed or deleted pinned test FAILS. So an O1-O4 driver test adapted to a changed
      rule -- which G7/G12/G13/G19 alone would pass, since they pin only names -- fails here until it is re-baselined
      by name with its reason.
  G0''' --capture-o4 (research/o5_design.md 1.4, 9 A0): the full ``(checks, report)`` of the archived PROVEN session
      story-o4 read with ``o4_predictions_v1``; of every o4_dryrun session case (its CASES and "predictions-changed");
      every o4_dryrun unit's ``(name, ok, detail)`` (``units(...)`` then ``listed_units(...)``, in run_cases's order);
      ``O4.offline_check(v1)``; the tests G19 collects; the HEAD and v1's sha; and ``sources``, G21's O4 pins -- the
      AST sha of every test G19 collects and of every function :data:`FAKE_PINS_O4` names (and every method of
      :data:`FAKE_PIN_CLASSES_O4`), only names the O3 baseline does not already pin (a name pinned in both is refused,
      :func:`o4_pin_names`) -> ``research/o4_regress_baseline.json`` (LF, ``-text``). It refuses to overwrite a
      baseline, and to write one unless G19, G20 and G22-G25's baseline-free halves pass at the code it captures; it
      first takes TWO readings and refuses when they differ, every temporary root read as ``<tmp>`` (O3's rule, G0'').
  G22 ``O4.analyse(story-o4, pred_path=v1)``: the report is the archived ``o4_report.txt`` exactly, and the
      baseline's; the checks are the baseline's; PROVEN with 16 checks, all True.
  G23 the CLI ``o4_castle.py --analyse story-o4 --predictions v1`` exits 0 and prints that report.
  G24 every o4_dryrun session case's ``(checks, report)`` and every unit's ``(name, ok, detail)`` is the baseline's,
      byte for byte (each temporary root read as ``<tmp>``), and ``run_cases(v1)`` still returns 0 printing "N/N
      cases as registered" (103 at the capture), N counted from the replica: its sessions plus its units. The gate
      replicates run_cases's loop step for step, as G17 does O3's.
      G24 IS O4'S VOID-PATH BASELINE: the story-o4 archive holds six covered runs and no VOID, so G22/G23 never take
      the coverage rule's VOID paths, VOID-ASYM's (a)-(d), A-START's, A-NOEND's or the Chanbara judge's. An edit to any
      of them is proven O4-neutral by G24's synthetic sessions alone.
  G25 ``O4.offline_check(v1)`` equals the baseline's ``[(ok, what, detail)]``: 4 checks, all PASS (it reads O4's build
      and the install, read-only).
  G26 ``pytest tests/test_harness.py -k "o5_ or fake_visit or fake_story_suppress"`` from ``ff9mapkit/``
      (research/o5_design.md 1.4, from B3): every test passed, 0 failed, 0 skipped, 0 errors, and every name in
      :data:`REQUIRED_TESTS_O5` among them -- O5's FakeGame (H13 the sink's same-value suppression, H14 the scripted
      visit, H15 its faults), the route builder played unattended, and the driver's O5 tests on the fake (the stair walk,
      the guard and the verified landing, the visit-scoped cells, the real stair, which reads the install: a skip there
      fails the item). No baseline: the list is the floor.
  G27 ``o5_dryrun.run_cases`` (research/o5_design.md 9 C2) on the frozen O5 predictions once they exist
      (``o5_predictions_v1.json``), else on the draft (which reads O4's chain's campaign.toml): it returns 0 printing
      "N/N cases as registered", N at least :data:`O5_DRYRUN_FLOOR`. O5Segment subclasses O4Segment and runs on every
      shared module, so a later edit to any of them must keep O5's dry run green too -- every check failing on its
      mutant, every case EXACT. No baseline: the count is the floor (a dropped case falls under it).

Nothing here touches the game or writes to the install: it reads the archives, the builds and the stock bytes. The
pins file is written only by ``--rebaseline-source``, and a baseline only by its ``--capture*``.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import hashlib
import io
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import o1_opening as O                                                     # noqa: E402
import o1_dryrun as D                                                      # noqa: E402

V4 = HERE / "o1_predictions_v4.json"
O1E = Path(r"C:\gd\Dream-World-IX\.harness-runs\20260929-213149-story-o1e")
O1D = Path(r"C:\gd\Dream-World-IX\.harness-runs\20260929-212507-story-o1d")
BASELINE = HERE / "research" / "o1_regress_baseline.json"
PYTEST_K = "o1_ or overlay_hint or segment"
#: Tests G7 must find (and find passing) beyond the ones the baseline collected: each arrives with the PART A step
#: that adds it (research/o2_design.md section 9), so a later step cannot drop it silently.
REQUIRED_TESTS: tuple = (
    # A3: O1Segment.run keeps O1's session surface; the shared session loop and its THROW check, on the fake
    "test_o1_segment_run_pins_o1s_session_surface",
    "test_segment_session_loop_on_the_fake",
    "test_segment_throw_check_fails_on_an_engine_exception",
    # research/o3_design.md section 9, PART A: the shared session changes, each with the step that adds it
    "test_segment_read_session_judges_a_registered_battle_by_its_won",          # A1: S1
    "test_segment_rerun_stops_on_a_finding_class",                              # A2: S2
    "test_segment_end_run_resets_from_inside_a_battle_without_a_warp",          # A3: S3
    "test_segment_session_end_warps_first_when_asked",                          # A4: S5
    "test_segment_end_run_from_a_battle_on_the_fake",                           # B5: S3 on H9's knobs
    "test_segment_session_end_leaves_a_movie_on_the_fake",                      # B5: S5 on H9's movie beat
    "test_segment_end_run_waits_out_the_battle_load_on_the_fake",               # the review, 11.7 #8: S3's load
    # the movie-skip policy (PLAN.md "Movie skip (opt-in)"): its pure halves, the skip dialog's reader and the
    # policy's strictness
    "test_segment_movie_skip_answer_reads_only_the_skip_dialog",
    "test_segment_movie_skip_policy_is_strict",
    # research/o4_design.md section 9, PART A: the gate's own pins and the shared changes, each with its step
    "test_segment_regress_source_pins_catch_an_edit",                           # A0: G21's checker
    "test_segment_side_ends_split_the_cut_and_the_drive",                       # A1: S6, pure
    "test_segment_drive_ends_per_side_on_the_fake",                             # A1: S6 on the drive
    "test_segment_o3_scope_lang_reads_the_recorded_p_text",                     # A2: O3's clause from its record
    # research/o5_design.md section 9, PART A: the gate extended to O4 (G21 over the union of the O3 and O4 baselines'
    # pins) and stray_answer's strings pinned as O4 froze them, then the shared opt-in changes, each with its step
    "test_segment_regress_o4_pins_join_the_union",                              # A0: G21 over both baselines
    "test_segment_stray_answer_keeps_o4s_strings",                              # A0: O4's attribution, every string
    "test_segment_witness_of_is_strict",                                        # A1: S12, pure
    "test_segment_drive_polls_the_witness_run_wide",                            # A1: S12 on the fake
    "test_segment_cell_visit_scopes_a_cell",                                    # A1: S13, pure
    "test_segment_drive_control_at_another_visit_is_v4",                        # A1: S13 on the fake
    "test_segment_drive_void_cell_carries_the_visit",                           # A1: S13's VOID cell
    "test_segment_choose_landed_lands_once",                                    # A2: S11
    "test_segment_choose_landed_repress_while_typing",                          # A2: S11, a prompt typing
    "test_segment_choose_landed_gives_up_unlanded",                             # A2: S11, did not land
    "test_segment_choose_landed_stops_when_the_cursor_moves",                   # A2: S11, the cursor moved
    "test_segment_choose_landed_raises_on_an_unseen_landing",                   # A2: S11, ChoiceUnseen
    "test_segment_choose_landed_is_not_fooled_by_the_dialog_catch",             # A2: S11, the agent's catch
    "test_segment_guard_of_is_strict",                                          # A3: S10, pure
    "test_segment_guard_presses_the_marker_page_once",                          # A3: S10 (iii)
    "test_segment_guard_holds_off_after_any_press",                             # A3: S10 (iii) (b)
    "test_segment_guard_quiet_window_presses_nothing_until_the_choice",         # A3: the quiet window
    "test_segment_guard_marker_page_rearms_the_quiet_window",                   # A3: S10 (ii), re-armed
    "test_segment_guard_page_in_the_quiet_window_is_v17_observed",              # A3: S10 (ii), observed
    "test_segment_guard_cap_scans_first_then_is_v13",                           # A3: the quiet cap
    "test_segment_guard_strays_from_127s_last_sample",                          # A3: guard_strays, pure
    "test_segment_guard_choice_gone_is_v17_or_v13",                             # A3: S10 (i)
    "test_segment_guard_reask_after_a_verified_landing_is_v2",                  # A3: choice_reask
    "test_segment_guard_judges_the_branch_page",                                # A3: S10 (o)
    "test_segment_guard_is_opt_in",                                             # A3: S10-S13 opt-in
)

O1E_VERDICT = "PROVEN"
O1D_VERDICT = "VOID: O1-COVER, O1-LADDER, O1-NULL, O1-STABLE, O1-JOIN"
MUTANT_VERDICT = "NOT PROVEN: O1-NULL"

# -- O2 (research/o3_design.md 1.4): the frozen v1 predictions and the PROVEN story-o2 archive
V1 = HERE / "o2_predictions_v1.json"
O2S = Path(r"C:\gd\Dream-World-IX\.harness-runs\20260930-192740-story-o2")
BASELINE_O2 = HERE / "research" / "o2_regress_baseline.json"
PYTEST_K_O2 = "o2_ or rehearse"
#: Tests G12 must find (and find passing) beyond the ones the O2 baseline collected: each arrives with the step of
#: research/o3_design.md section 9 that adds it (B4's renamed no-registry test, C3's rehearse tests), so a later step
#: cannot drop it silently.
REQUIRED_TESTS_O2: tuple = (
    # B4: S4's no-registry proof -- O2-shaped predictions read a battle exactly as O2's driver did
    "test_o2_drive_voids_a_battle_without_a_registry",
    # C3: O3's rehearsals on the fake (o3_rehearse.py imports o2_rehearse's Recorder and stage_pred: shared code now)
    "test_o3_rehearse_plumbing_on_the_fake",
    "test_o3_rehearse_smoke_sends_no_storytrace_on_the_fake",
    "test_o3_rehearse_battle_void_stops_mid_fight_on_the_fake",
    # the review (research/o3_design.md 11.7 #7): each run records its own fight and leave
    "test_o3_rehearse_clears_the_last_fight_between_runs_on_the_fake",
    # the movie-skip A/B's skip side (PLAN.md "Movie skip (opt-in)"): R-FULL-SKIP's overlay and its record
    "test_o3_rehearse_movie_skip_stage_on_the_fake",
)

# -- O3 (research/o3_design.md 1.4, 9 B4): the battle beat's driver tests, by name. No baseline: the list is the floor.
#: G13's selection: the driver tests, and the movie-skip A/B's (the movie-skip review #5: a name REQUIRED_TESTS_O3
#: lists must be one this selection collects, or the item can never pass).
PYTEST_K_O3 = "o3_drive or o3_skip_ab"
#: Tests G13 must find (and find passing): the battle beat's driver tests (B4), so a later edit to ``segment_drive``
#: (O4's) re-runs every one of them.
REQUIRED_TESTS_O3: tuple = (
    "test_o3_drive_fights_its_registered_battle_and_lands_fresh",
    "test_o3_drive_lands_in_the_member_on_the_fork_side",
    "test_o3_drive_reads_a_landing_in_the_real_field_as_a_finding",
    "test_o3_drive_ignores_the_id_flip_inside_the_battle",
    "test_o3_drive_waits_out_a_late_landing",
    "test_o3_drive_voids_a_landing_past_its_cap",
    "test_o3_drive_voids_an_unregistered_battle",
    "test_o3_drive_voids_a_battle_with_no_result",
    "test_o3_drive_logs_leave_battle_presses_as_press_rows",
    "test_o3_drive_stops_on_a_stop_page",
    "test_o3_drive_answers_a_skip_dialog_at_its_default",
    "test_o3_drive_watchdog_against_a_long_movie",
    "test_o3_drive_battle_of_rejects_a_bad_row",
    # the review (research/o3_design.md 11.7): each fix to the driver, with its test
    "test_o3_drive_waits_for_the_end_places_first_row",                     # 11.7 #3: rule 1's end row
    "test_o3_drive_stops_on_a_battle_gone_without_a_result",                # 11.7 #2: fight()'s "gone"
    "test_o3_drive_bounds_the_leave_by_its_row",                            # 11.7 #1: the leave's bound
    "test_o3_drive_fights_through_an_end_that_beats_its_command",           # the -n 6 command race, pinned
    "test_o3_drive_fights_through_an_end_that_beats_its_menu",              # ...its menus window, pinned
    # the movie-skip policy (PLAN.md "Movie skip (opt-in)"): opt-in, so every O3 test above runs without it
    "test_o3_drive_movie_skip_presses_once_and_answers_yes",
    "test_o3_drive_movie_skip_is_off_without_the_policy",
    "test_o3_drive_movie_skip_presses_only_in_a_registered_cell",
    "test_o3_drive_movie_skip_retries_then_gives_up_without_a_void",
    "test_o3_drive_movie_skip_turns_a_page_that_comes_instead",
    "test_o3_drive_movie_skip_refuses_a_dialog_that_is_not_the_skip_text",
    # the movie-skip review: a skip dialog the policy's own press opened but cannot read is answered at its default
    "test_o3_drive_movie_skip_answers_an_unread_skip_dialog_at_its_default",
    # the movie-skip review #5: the A/B -- skip_ab_runs' axes and evidence, and --skip-ab through its files (the
    # pairing of _ab_stages, the reading of _ab_runs, the CLI's exit codes); it skips without the install, and G13
    # fails a skip
    "test_o3_skip_ab_on_synthetic_traces",
    # O4's Chanbara policy is opt-in (research/o4_design.md 9 B4): O3-shaped predictions page a prompt-shaped page by
    # rule 7, exactly as O3's driver does
    "test_o3_drive_pages_a_prompt_without_the_chanbara_policy",
)
#: G14 (the review, research/o3_design.md 11.7 #12): o3_dryrun's "N/N cases as registered" must have N at least this --
#: its sessions, "predictions-changed", its units and its offline mutants when G14 joined (92), and the movie-skip A/B's
#: units (PLAN.md "Movie skip (opt-in)"): four, then two for the evidence a skip took (a skip that saved nothing, a
#: row with no left_s), then four through the files (o3_dryrun.unit_skip_ab_files: paired, unpaired, no policy, the
#: CLI's exit codes). A case added raises N; one dropped falls under the floor.
O3_DRYRUN_FLOOR = 102

O2S_VERDICT = "PROVEN"
O2S_CHECKS = 15
O2_OFFLINE_CHECKS = 5

# -- O3 (research/o4_design.md 1.4): the frozen v1 predictions and the PROVEN story-o3 archive
V1_O3 = HERE / "o3_predictions_v1.json"
O3S = Path(r"C:\gd\Dream-World-IX\.harness-runs\20261001-095552-story-o3")
BASELINE_O3 = HERE / "research" / "o3_regress_baseline.json"
O3S_VERDICT = "PROVEN"
O3S_CHECKS = 17
O3_OFFLINE_CHECKS = 6
#: What every temporary root the dry-run replica makes reads as, in a reading and in the O3 baseline (G0'', G17).
TMP = "<tmp>"
#: G20 (research/o4_design.md 9 C2): o4_dryrun's "N/N cases as registered" must have N at least this -- its 63
#: session cases and "predictions-changed" (section 8's table), its 18 units, and its listed units (O4-CENSUS and its 4
#: mutants, O4-BUILD's pins on a synthetic route build and its 3 mutants, the fight pins and their 2 mutants, the draft
#: through O4-KEYS and its 7 offline mutants) when G20 joined (102); then the review's cases (research/o4_design.md
#: 11.5): sword-j-unbounded-both (#3/#7). A case added raises N; one dropped falls under the floor.
O4_DRYRUN_FLOOR = 103
#: G19 (research/o4_design.md 1.4, from B3): every ``test_o4_*``, ``test_fake_chanbara_*`` and ``test_fake_keyon_*``
#: name, each with the step that adds it -- G19 joined the gate in the commit that added B3's tests.
PYTEST_K_O4 = "o4_ or fake_chanbara or fake_keyon"
REQUIRED_TESTS_O4: tuple = (
    # B1: H10-H12, the fake's machine beats (the KEYON pair, the Chanbara visit, its faults)
    "test_fake_keyon_pair_takes_only_an_edge_after_its_gate",
    "test_fake_chanbara_arms_and_publishes_in_one_tick",
    "test_fake_chanbara_scores_a_perfect_run_exactly",
    "test_fake_chanbara_times_out_and_rearms_in_the_same_tick",
    "test_fake_chanbara_misses_a_circle_pressed_as_circle",
    "test_fake_chanbara_misses_two_keys_start_and_a_held_key",
    "test_fake_chanbara_filters_hold_on_every_seed",
    "test_fake_chanbara_bonus_knob_and_assistance_levels",
    "test_fake_chanbara_encore_yes_replays_without_111",
    "test_fake_chanbara_close_tween_and_slides",
    "test_fake_chanbara_page_ignores_confirm_while_opening",
    "test_fake_chanbara_publication_order_and_true_j",
    "test_fake_chanbara_faults",
    # B2: S7's pure half
    "test_o4_chanbara_of_is_strict",
    "test_o4_prompt_recognizers_claim_exactly_the_prompts",
    "test_o4_j_and_raw_bounds",
    "test_o4_chanbara_judge_classes",
    "test_o4_slides_bracket_the_slide_from_the_prev_samples",
    "test_o4_stray_answer_attributes_by_the_down_frame",
    # B3: rule 6b's executor, S8, S9, the witness and the pace, on the fake
    "test_o4_drive_scores_100_on_the_fake",
    "test_o4_drive_opens_one_instance_beside_a_lingering_prompt",
    "test_o4_drive_paced_tracks_the_closing_prompt_beside_its_successor",
    "test_o4_drive_fails_closed_on_an_unclaimed_dialog",
    "test_o4_drive_refuses_an_unrecognized_dbtn_page",
    "test_o4_drive_v17_on_a_stalled_press",
    "test_o4_drive_read_stall_in_a_gap_is_v17_never_v18",
    "test_o4_drive_v18_on_a_lost_press",
    "test_o4_drive_v18_on_a_miss_read",
    "test_o4_drive_v18_on_what_the_game_shows",
    "test_o4_drive_slides_at_31_fps_agent_first",
    "test_o4_drive_page_once_and_the_quiet_windows",
    "test_o4_drive_presses_123_again_when_its_first_press_is_dropped",
    "test_o4_drive_attributes_a_stray_yes",
    "test_o4_drive_paced_policy_lands_in_its_band",
    "test_o4_drive_stops_v13_off_fieldhud",
    "test_o4_drive_input_witness_stops_v13",
    "test_o4_drive_never_blocks_on_the_rate",
    "test_o4_drive_stop_after_ends_at_instance_eleven",
    "test_o4_drive_prompt_outside_its_cell_is_v17",
    # C1: o4_castle itself -- the draft from campaign.toml, the freeze's refusals, the census's inert proof, the
    # preflight's verdicts, the input witness's readers, VOID-ASYM (d), R-GATE's verdict
    "test_o4_castle_draft_reads_the_chain_from_campaign",
    "test_o4_castle_freeze_refuses",
    "test_o4_castle_census_proves_inert_by_instancing",
    "test_o4_castle_preflight_verdicts",
    "test_o4_castle_input_witness_readers",
    "test_o4_castle_void_asym_reads_observed_rows",
    "test_o4_castle_gate_verdict",
    # C2: O4's trace summary cut at the side's end PLACES (an F stage ending in a member is cut there), over the dry
    # run's rendered rows
    "test_o4_castle_trace_summary_cuts_at_end_places",
    # C3: o4_rehearse.py on the fake -- R-CHANBARA's record (7.2), R-CHANBARA-VOID's stop and recovery (F7), F-SMOKE's
    # per-pair raw warps with no trace (G1), R-GATE's sides and verdicts (7.4 G2)
    "test_o4_rehearsal_plumbing_on_the_fake",
    "test_o4_rehearsal_void_stage_stops_mid_fight_on_the_fake",
    "test_o4_rehearsal_smoke_sends_no_storytrace_on_the_fake",
    "test_o4_rehearsal_gate_reads_the_pair_on_the_fake",
    # the fake's story rows read an Int16 signed (a launch's second visit stores Int16[9] := -1 over -1)
    "test_o4_fake_story_store_reads_int16_signed",
    # the review (research/o4_design.md 11.5) #3/#7: a row with no j bounds and a complete zone's unbounded raw are the
    # judge's V17 (never a floor or a band skipped silently); a zone entered on a prompt takes instance 1's prev from
    # the ring
    "test_o4_chanbara_judge_never_skips_an_unbounded_raw",
    "test_o4_drive_entered_on_a_prompt_bounds_instance_one_from_the_ring",
    # the review #1/#2/#6: R-GATE reads a run informative only on a complete, proven, bounded play with its readings
    # (a mid-fight stop, an instrument V13 -- recorded by o4_rehearse -- or an S fight's V18 is re-run, never INVALID)
    "test_o4_castle_gate_reading_reads_only_a_complete_proven_play",
    "test_o4_rehearsal_gate_reruns_what_cannot_witness_on_the_fake",
    # the review #5: R-GATE's and F-SMOKE's member ids are the chain's (member(N) resolved, every F-side id checked)
    "test_o4_rehearse_stage_ids_follow_the_chain",
    # the review #4: P-GATE reads R-GATE's own launch record (its verdict, runs, engine, settings, member(64)'s build)
    "test_o4_castle_p_gate_needs_its_launch_record",
    # the review #8: the input witness resolves the game's pids once (no tasklist on a poll) and fails closed
    "test_o4_castle_input_witness_resolves_the_game_once",
    # the paced band's -n 6 flake (a starved poll's read gap straddling a mark, the instrument's V17): a fake drive test
    # re-runs only a read-gap VOID, at most 3 runs, and asserts on the run returned whole
    "test_o4_read_gap_void_reads_the_zone_reason_alone",
    "test_o4_drive_paced_policy_reruns_only_a_read_gap",
)

# -- O4 (research/o5_design.md 1.4): the frozen v1 predictions and the PROVEN story-o4 archive
V1_O4 = HERE / "o4_predictions_v1.json"
O4S = Path(r"C:\gd\Dream-World-IX\.harness-runs\20261002-091051-story-o4")
BASELINE_O4 = HERE / "research" / "o4_regress_baseline.json"
O4S_VERDICT = "PROVEN"
O4S_CHECKS = 16
O4_OFFLINE_CHECKS = 4
#: G27 (research/o5_design.md 9 C2): o5_dryrun's "N/N cases as registered" must have N at least this -- its 86 session
#: cases and "predictions-changed" (section 8's table), its 18 units, and its listed units (O5-CENSUS and its 6 mutants,
#: O5-REGIONS and its 5, O5-GOALS and its 6, the route pins and route_mes with their 7, O5-BUILD's route pins on a
#: synthetic build and its 3, the draft through O5-KEYS and its 6 offline mutants) when G27 joined (144). A case added
#: raises N; one dropped falls under the floor.
O5_DRYRUN_FLOOR = 144
#: G26 (research/o5_design.md 1.4, from B3): every ``test_o5_*``, ``test_fake_visit_*`` and ``test_fake_story_suppress_*``
#: name, each with the step that adds it -- G26 joined the gate in the commit that added B3's tests.
PYTEST_K_O5 = "o5_ or fake_visit or fake_story_suppress"
REQUIRED_TESTS_O5: tuple = (
    # B1: H13, the sink's same-value suppression (opt-in)
    "test_fake_story_suppress_emits_the_first_same_value_per_site",
    "test_fake_story_suppress_counts_close_the_epoch",
    "test_fake_story_suppress_is_off_by_default",
    # B1: H14, the scripted visit beat, and H15, its faults
    "test_fake_visit_pages_open_type_and_close",
    "test_fake_visit_choice_opens_after_its_gap_on_cursor_zero",
    "test_fake_visit_objects_as_the_agent_publishes_them",
    "test_fake_visit_grant_and_the_stair_contour",
    "test_fake_visit_side_scene_and_regrant",
    "test_fake_visit_back_door_stores_then_leaves",
    "test_fake_visit_keyon_pairs_and_timed_windows",
    "test_fake_visit_faults",
    "test_fake_visit_sets_the_members_donor",
    # B2: the O5 route builder, played unattended to 151 (its trace 4.16's pattern)
    "test_fake_visit_route_plays_to_151_unattended",
    # B3: the driver's O5 tests on the fake
    "test_o5_drive_walks_the_stairs_and_answers_her_face_on_the_fake",
    "test_o5_drive_guard_closes_the_stray_press_race",
    "test_o5_drive_choose_landed_repress_when_128_drops_a_confirm",
    "test_o5_drive_unlanded_answer_is_the_drivers_v17",
    "test_o5_drive_outside_cursor_move_is_v13",
    "test_o5_drive_the_branch_page_witnesses_the_answer",
    "test_o5_drive_control_off_the_cell_is_v4",
    "test_o5_drive_side_scene_is_one_interrupt",
    "test_o5_drive_back_door_is_the_drivers_v11",
    "test_o5_drive_never_reaching_the_contour_is_v7",
    "test_o5_drive_fork_landing_in_real_151_is_v19",
    "test_o5_drive_page_in_the_quiet_window_is_v17_observed",
    "test_o5_drive_glitched_sample_rearms_the_quiet_window",
    "test_o5_drive_quiet_cap_survives_a_read_stall_on_mtime",
    "test_o5_drive_no_choice_within_the_cap_is_v13",
    "test_o5_drive_guard_window_opens_on_128s_first_sample_at_31fps",
    "test_o5_drive_choice_gone_unanswered_is_v13",
    "test_o5_drive_reask_after_a_verified_landing_is_v2",
    "test_o5_drive_stop_page_in_the_start_is_v5_driver",
    "test_o5_drive_climbs_the_real_stair_on_the_fake",
    # C1: o5_hallway itself -- the draft from O4's campaign.toml and o5_forks.json, the freeze's refusals, the route
    # builder against the draft (one source of truth), the census's inert proof per entrance, the regions' roles, the
    # stair's contour and its evidence, O5-PATTERN, A-START scoped to visit 1, the preflight's verdicts
    "test_o5_hallway_draft_reads_the_chain_from_campaign",
    "test_o5_hallway_freeze_refuses",
    "test_o5_hallway_route_builder_matches_the_keys",
    "test_o5_hallway_census_proves_inert_per_entrance",
    "test_o5_hallway_regions_roles",
    "test_o5_hallway_goals_contour",
    "test_o5_hallway_pattern_check",
    "test_o5_hallway_why_void_scopes_a_start_to_visit_1",
    "test_o5_hallway_preflight_verdicts",
    # C2: the trace summary over the dry run's rendered rows, cut at the end PLACES (O4's lesson)
    "test_o5_hallway_trace_summary_cuts_at_end_places",
    # C3: o5_rehearse on the fake -- the stage table's ids from the chain, R-STAIRS's plumbing and 7.2's record (the walk
    # tapped, the guard and its race margin), R-WALK-VOID's stop mid-walk, F-SMOKE untraced, F-PASS untraced to member(151)
    "test_o5_rehearsal_stage_ids_follow_the_chain",
    "test_o5_rehearsal_plumbing_on_the_fake",
    "test_o5_rehearsal_walk_void_stops_mid_walk_on_the_fake",
    "test_o5_rehearsal_smoke_sends_no_storytrace_on_the_fake",
    "test_o5_rehearsal_fpass_runs_untraced_to_the_member_on_the_fake",
    "test_o5_rehearsal_walk_record_judges_holds_and_the_teleport",
    # the review's fixes (research/o5_design.md 11.6): the guarded choice taken under the answer is S10's gone choice;
    # H14's choice cursor wraps as the engine's navigation does; the recorder counts the catch as the agent publishes it
    "test_o5_drive_choice_taken_under_the_answer_is_the_gone_choice",
    "test_fake_visit_choice_cursor_wraps",
    "test_o5_rehearsal_recorder_counts_the_dialog_section_catch",
)

# -- G21, the driver's source pins (research/o4_design.md 1.4, rev. 2)
SOURCE_PINS = HERE / "research" / "source_pins.json"
#: The pinned files, by the repo-relative name a pin carries (``<file>::<qualname>``, pytest's node-id form).
TEST_REL = "ff9mapkit/tests/test_harness.py"
FAKE_REL = "tools/harness/fakegame.py"
PIN_FILES = {TEST_REL: ROOT / TEST_REL, FAKE_REL: ROOT / FAKE_REL}
#: fakegame.py's existing beat and input functions (research/o4_design.md 1.4 G0''), by qualified name: the fake every
#: O1-O3 driver test runs against, so an O4 edit that changes how it presses, publishes or stages fails G21 by name.
FAKE_PINS = ("FakeGame._execute", "FakeGame._block", "FakeGame._schedule", "FakeGame._extend", "FakeGame._is_held",
             "FakeGame._advance_clock", "FakeGame._hold_frame", "FakeGame._frame_steps", "FakeGame._menu_step",
             "FakeGame._publish", "FakeGame.say", "FakeGame.offer", "FakeGame.scene", "FakeGame._next_beat",
             "FakeGame._choice_cursor", "FakeGame._movie_over", "FakeGame._end_scene", "FakeGame._step_scene",
             "FakeGame._scene_press", "_control")
#: The fake O4's tests run on (research/o5_design.md 1.4 G0'''), by qualified name: its story-trace sink, the warp's
#: residue, the machine beats' dispatch and frame, and the strict knob reader -- so an O5 edit that changes how the fake
#: writes a trace row or plays a machine beat fails G21 by name. The O4 baseline pins these AND every method of
#: :data:`FAKE_PIN_CLASSES_O4` (:func:`fake_pins_o4`: ``functions_of`` pins ``Class.method``). Module constants are not
#: pins: a constant that changes behaviour fails G19.
FAKE_PINS_O4 = ("FakeGame._start_machine", "FakeGame._step_machine", "FakeGame._frame_once", "FakeGame._story_row",
                "FakeGame._story_start", "FakeGame._story_stop", "FakeGame._story_store", "FakeGame._warp_writes",
                "FakeGame.script_store", "_machine_knobs")
#: The fake's machine-beat classes (H10-H12, research/o4_design.md 3): every method of each is an O4 pin.
FAKE_PIN_CLASSES_O4 = ("_Win", "_Machine", "_KeyonPairBeat", "_ChanbaraBeat")
#: A re-baseline row of the pins file, exactly these keys.
PIN_ROW_KEYS = ("name", "old", "new", "reason", "head")


# ======================================================================== what the O1 code says
def _pair(checks, report) -> dict:
    return {"checks": [list(c) for c in checks], "report": report}


def analyse_archive(run_dir: Path) -> dict:
    checks, report = O.analyse(run_dir, pred_path=V4)
    return _pair(checks, report)


def dryrun_outputs(stock) -> tuple:
    """``({case: (checks, report)}, [case names in run order])`` -- ``o1_dryrun.run_cases``'s own loop, step for
    step: the same temp-directory sequence gives every case the session label run_cases gives it."""
    pred, _sha = O.load_predictions(V4)
    out, order = {}, []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, fn, _want_verdict, _want in D.CASES:
            d = D.make_session(tmp, V4, fn(copy.deepcopy(pred)))
            out[name] = _pair(*O.analyse(d, stock=stock))
            order.append(name)
        frozen_tmp = tmp / "pred_copy.json"
        frozen_tmp.write_bytes(V4.read_bytes())
        d = D.make_session(tmp, frozen_tmp, D.six(pred))
        frozen_tmp.write_bytes(V4.read_bytes() + b" ")
        out["predictions-changed"] = _pair(*O.analyse(d, stock=stock))
        order.append("predictions-changed")
    return out, order


def mutant_row(members: dict, f: int, value: int) -> dict:
    """G6's row: 50's e17, field mode, an addition-buffer store of Global.Byte[206] (keyed with no join), on the
    fork side (``fld`` = member(50), ``don`` = 50, as the engine writes it)."""
    r = D.row((50, 17, -1, 40, "Byte", 206, 0, value), side="F", members=members, f=f)
    r.update(add=1, tag=-1)
    return r


def noise_mutant(stock) -> dict:
    pred, _sha = O.load_predictions(V4)
    members = O.members_of(pred)
    value = random.Random(206).randrange(1, 256)          # one draw: the same key in every fork run
    runs = D.six(pred)
    for r in runs:
        if r["side"] == "F":
            r["rows"].insert(3, mutant_row(members, 205, value))
    with tempfile.TemporaryDirectory() as tmp:
        d = D.make_session(Path(tmp), V4, runs)
        return _pair(*O.analyse(d, stock=stock))


def offline() -> list:
    pred, _sha = O.load_predictions(V4)
    return [list(c) for c in O.offline_check(pred)]


def run_cases_quietly() -> tuple:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D.run_cases(V4)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else "")


def cli_analyse() -> tuple:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "o1_opening.py"), "--analyse", str(O1E), "--predictions",
                        str(V4)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout, p.stderr


def pytest_g7() -> dict:
    """Run G7's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K)


def pytest_selection(k: str) -> dict:
    """Run one ``-k`` selection of tests/test_harness.py; ``{"rc", "passed": [...], "failed": [...], "skipped":
    [...], "errors": [...]}`` read from its JUnit XML (the names, not a summary line)."""
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "g7.xml"
        p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_harness.py", "-q", "-p", "no:cacheprovider",
                            "-W", "ignore", "-k", k, f"--junitxml={xml}"],
                           cwd=str(ROOT / "ff9mapkit"), capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        out = {"rc": p.returncode, "passed": [], "failed": [], "skipped": [], "errors": [],
               "tail": (p.stdout + p.stderr)[-1500:]}
        if not xml.is_file():
            out["errors"].append("no JUnit XML written")
            return out
        for tc in ET.parse(xml).getroot().iter("testcase"):
            name = tc.get("name")
            kinds = {child.tag for child in tc}
            if "error" in kinds:
                out["errors"].append(name)
            elif "failure" in kinds:
                out["failed"].append(name)
            elif "skipped" in kinds:
                out["skipped"].append(name)
            else:
                out["passed"].append(name)
    return out


def _verdict(pair: dict) -> str:
    return O.verdict([tuple(c) for c in pair["checks"]])


def _result(pair: dict) -> dict:
    return {w.split(":")[0]: ok for ok, w, _d in pair["checks"]}


# ======================================================================== what the O2 code says
def _o2() -> tuple:
    """``(o2_alexandria, o2_dryrun)``: imported here, never at the module's top, so the O1 items import only O1's
    modules (research/o3_design.md 1.4)."""
    import o2_alexandria as A
    import o2_dryrun as D2
    return A, D2


def o2_analyse_archive() -> dict:
    A, _D2 = _o2()
    return _pair(*A.O2.analyse(O2S, pred_path=V1))


def o2_dryrun_outputs(stock) -> tuple:
    """``({case: (checks, report)}, [case names in run order], [[unit, ok, detail], ...])`` -- ``o2_dryrun.run_cases``'s
    own loop over V1, step for step: the same temporary layout (``pred/``, ``sessions/``), the same session
    directories in the same order (``s0``, ``s1``, ... -- each report's title carries its label), the same units in
    the same order (state-history's session is the last one made), the offline mutants on the same temporary root.
    Left out are only run_cases's verdict comparisons and its extra ``read_session`` reads of a case's VOID classes:
    pure reads that make no directory and leave nothing an output reads."""
    from ff9mapkit.content.verbatim import remap_fields
    A, D2 = _o2()
    out, order, units = {}, [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdir = tmp / "pred"
        pdir.mkdir()
        sdir = tmp / "sessions"
        sdir.mkdir()
        path = V1                                         # run_cases's _prepare(V1, pdir) is V1 itself
        pred, _sha = A.O2.load(path)
        members = D2.members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, *_want in D2.CASES:
            d = D2.make_session(sdir, path, fn(copy.deepcopy(pred)), scripts)
            out[name] = _pair(*A.O2.analyse(d, stock=stock))
            order.append(name)
        copy_path = pdir / "pred_copy.json"               # O2-FROZEN: the predictions changed after the session
        copy_path.write_bytes(path.read_bytes())
        d = D2.make_session(sdir, copy_path, D2.six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        out["predictions-changed"] = _pair(*A.O2.analyse(d, stock=stock))
        order.append("predictions-changed")
        for name, fn in (("span-selector", D2.unit_span_selector),
                         ("span-count-row", lambda: D2.unit_span_count_row(pred, stock)),
                         ("text-rule-defect", D2.unit_text_defect),
                         ("text-rule-session", D2.unit_text_session), ("text-rule-garbage", D2.unit_text_garbage),
                         ("trace-summary", lambda: D2.unit_trace_summary(pred, stock)),
                         ("state-history", lambda: D2.unit_state_history(pred, stock, scripts, sdir, path))):
            ok, detail = fn()
            units.append([name, ok, detail])
        for name, ok, detail in D2.unit_offline_mutants(pred, stock, tmp):
            units.append([name, ok, detail])
    return out, order, units


def o2_offline() -> list:
    A, _D2 = _o2()
    pred, _sha = A.O2.load(V1)
    return [list(c) for c in A.O2.offline_check(pred)]


def o2_run_cases_quietly() -> tuple:
    _A, D2 = _o2()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D2.run_cases(V1)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else "")


def o2_cli_analyse() -> tuple:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "o2_alexandria.py"), "--analyse", str(O2S), "--predictions",
                        str(V1)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout, p.stderr


def pytest_g12() -> dict:
    """Run G12's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K_O2)


def _verdict_o2(pair: dict) -> str:
    _A, D2 = _o2()
    return D2.verdict([tuple(c) for c in pair["checks"]])


# ======================================================================== the items
def _first_diff(a: str, b: str) -> str:
    la, lb = a.split("\n"), b.split("\n")
    for i, (x, y) in enumerate(zip(la, lb), 1):
        if x != y:
            return f"line {i}: {x[:140]!r} != {y[:140]!r}"
    return f"{len(la)} lines vs {len(lb)} lines"


def _same(got: dict, want: dict, what: str) -> list:
    bad = []
    if got["checks"] != want["checks"]:
        pairs = [(g, w) for g, w in zip(got["checks"], want["checks"]) if g != w]
        bad.append(f"{what} checks differ: {pairs[:1] or (len(got['checks']), len(want['checks']))}"[:400])
    if got["report"] != want["report"]:
        bad.append(f"{what} report differs at {_first_diff(got['report'], want['report'])}")
    return bad


def g1(base: dict, got: dict) -> tuple:
    bad = []
    archived = (O1E / "o1_report.txt").read_text(encoding="utf-8")
    if got["report"] != archived:
        bad.append(f"the report is not the archived o1_report.txt: {_first_diff(got['report'], archived)}")
    if base is not None:
        bad += _same(got, base["o1e"], "o1e")
    checks = got["checks"]
    if _verdict(got) != O1E_VERDICT or len(checks) != 6 or not all(c[0] is True for c in checks):
        bad.append(f"verdict {_verdict(got)!r} over {len(checks)} checks, want {O1E_VERDICT} over 6, all True")
    return (not bad, "G1: analyse(o1e, v4) is the archived report exactly, PROVEN with 6 checks all True",
            "; ".join(bad) or f"{len(got['report'].splitlines())} report lines, {_verdict(got)}")


def g2(report: str) -> tuple:
    rc, out, err = cli_analyse()
    bad = []
    if rc != 0:
        bad.append(f"exit {rc}: {err[-300:]}")
    if out != report + "\n":
        bad.append(f"stdout is not the report plus print's newline: {_first_diff(out, report + chr(10))}")
    return (not bad, "G2: the CLI --analyse o1e --predictions v4 exits 0 and prints that report",
            "; ".join(bad) or "exit 0")


def g3(base: dict, got: dict, order: list) -> tuple:
    bad = []
    if base is not None:
        if order != base["dryrun_order"]:
            bad.append(f"cases {order} != the baseline's {base['dryrun_order']}")
        for name in order:
            if name in base["dryrun"]:
                bad += _same(got[name], base["dryrun"][name], name)
    rc, last = run_cases_quietly()
    if rc != 0 or last != f"{len(D.CASES) + 1}/{len(D.CASES) + 1} cases as registered":
        bad.append(f"run_cases(v4) returned {rc}: {last!r}")
    return (not bad, "G3: every dry-run case's (checks, report) is the baseline's, byte for byte; run_cases(v4) 0",
            "; ".join(bad[:4]) or f"{len(order)} cases; {last}")


def g4(base: dict, got: list) -> tuple:
    bad = [] if base is None or got == base["offline"] else [f"{got} != {base['offline']}"[:500]]
    if not all(c[0] is True for c in got):
        bad.append(f"offline_check(v4) reads {[c[0] for c in got]}")
    return (not bad, "G4: offline_check(v4) is the baseline's [(ok, what, detail)]",
            "; ".join(bad) or "; ".join(f"{c[1].split(':')[0]}: {c[2]}" for c in got))


def g5(base: dict, got: dict) -> tuple:
    bad = [] if base is None else _same(got, base["o1d"], "o1d")
    if _verdict(got) != O1D_VERDICT:
        bad.append(f"verdict {_verdict(got)!r}, want {O1D_VERDICT!r}")
    return (not bad, "G5: o1d's (checks, report) is the baseline's, byte for byte (a real VOID path)",
            "; ".join(bad) or _verdict(got))


def g6(base: dict, got: dict) -> tuple:
    bad = [] if base is None else _same(got, base["noise_mutant"], "the mutant")
    res = _result(got)
    if res.get("O1-NULL") is not False or res.get("O1-JOIN") is not True or _verdict(got) != MUTANT_VERDICT:
        bad.append(f"O1-NULL {res.get('O1-NULL')}, O1-JOIN {res.get('O1-JOIN')}, verdict {_verdict(got)!r}; want "
                   f"False, True, {MUTANT_VERDICT!r} -- a field-mode Byte[206] key read as noise")
    return (not bad, "G6: a field-mode Byte[206] key in the F runs only is FORK ONLY (O1's noise covers m != 1 only)",
            "; ".join(bad) or _verdict(got))


def _selection_bad(base: dict | None, got: dict, required) -> list:
    """What is wrong with a pytest selection's run: any failure, error or skip; a test the baseline collected or
    ``required`` names that did not pass; a non-zero exit or nothing passed."""
    bad = []
    for kind in ("failed", "errors", "skipped"):
        if got[kind]:
            bad.append(f"{kind}: {got[kind][:6]}")
    want = set(required) | set(base["tests"] if base is not None else ())
    missing = sorted(want - set(got["passed"]))
    if missing:
        bad.append(f"not run or not passed: {missing}")
    if got["rc"] != 0 or not got["passed"]:
        bad.append(f"pytest exit {got['rc']}, {len(got['passed'])} passed: {got['tail'][-400:]}")
    return bad


def g7(base: dict, got: dict) -> tuple:
    bad = _selection_bad(base, got, REQUIRED_TESTS)
    return (not bad, f'G7: pytest -k "{PYTEST_K}": all passed, 0 failed, 0 skipped; the baseline\'s tests and '
                     f"REQUIRED_TESTS among them", "; ".join(bad) or f"{len(got['passed'])} passed")


def g8(base: dict, got: dict) -> tuple:
    bad = []
    archived = (O2S / "o2_report.txt").read_text(encoding="utf-8")
    if got["report"] != archived:
        bad.append(f"the report is not the archived o2_report.txt: {_first_diff(got['report'], archived)}")
    if base is not None:
        bad += _same(got, base["o2s"], "story-o2")
    checks = got["checks"]
    v = _verdict_o2(got)
    if v != O2S_VERDICT or len(checks) != O2S_CHECKS or not all(c[0] is True for c in checks):
        bad.append(f"verdict {v!r} over {len(checks)} checks, want {O2S_VERDICT} over {O2S_CHECKS}, all True")
    return (not bad, f"G8: analyse(story-o2, v1) is the archived report exactly, PROVEN with {O2S_CHECKS} checks "
                     f"all True", "; ".join(bad) or f"{len(got['report'].splitlines())} report lines, {v}")


def g9(report: str) -> tuple:
    rc, out, err = o2_cli_analyse()
    bad = []
    if rc != 0:
        bad.append(f"exit {rc}: {err[-300:]}")
    if out != report + "\n":
        bad.append(f"stdout is not the report plus print's newline: {_first_diff(out, report + chr(10))}")
    return (not bad, "G9: the CLI o2_alexandria.py --analyse story-o2 --predictions v1 exits 0 and prints that report",
            "; ".join(bad) or "exit 0")


def g10(base: dict, got: dict, order: list, units: list) -> tuple:
    bad = []
    if base is not None:
        if order != base["dryrun_order"]:
            bad.append(f"cases {order} != the baseline's {base['dryrun_order']}"[:400])
        for name in order:
            if name in base["dryrun"]:
                bad += _same(got[name], base["dryrun"][name], name)
        if units != base["units"]:
            want = {u[0]: u for u in base["units"]}
            diff = [u[0] for u in units if want.get(u[0]) != u] + [n for n in want if n not in {u[0] for u in units}]
            bad.append(f"units differ from the baseline's: {diff[:6]}"
                       + ("" if [u[0] for u in units] == [u[0] for u in base["units"]] else " (and their order)"))
    off = [u[0] for u in units if u[1] is not True]
    if off:
        bad.append(f"units not as registered: {off[:6]}")
    rc, last = o2_run_cases_quietly()
    n = len(order) + len(units)
    if rc != 0 or last != f"{n}/{n} cases as registered":
        bad.append(f"run_cases(v1) returned {rc}: {last!r}, want {n}/{n}")
    return (not bad, "G10: every o2_dryrun case's (checks, report) and unit's (name, ok, detail) is the baseline's, "
                     "byte for byte; run_cases(v1) 0", "; ".join(bad[:4]) or f"{len(order)} sessions, {len(units)} "
                                                                             f"units; {last}")


def g11(base: dict, got: list) -> tuple:
    bad = [] if base is None or got == base["offline"] else [f"{got} != {base['offline']}"[:500]]
    if len(got) != O2_OFFLINE_CHECKS or not all(c[0] is True for c in got):
        bad.append(f"offline_check(v1) reads {[c[0] for c in got]}, want {O2_OFFLINE_CHECKS} x True")
    return (not bad, f"G11: O2's offline_check(v1) is the baseline's [(ok, what, detail)], {O2_OFFLINE_CHECKS} PASS",
            "; ".join(bad) or "; ".join(f"{c[1].split(':')[0]}: {c[2][:90]}" for c in got))


def g12(base: dict, got: dict) -> tuple:
    bad = _selection_bad(base, got, REQUIRED_TESTS_O2)
    return (not bad, f'G12: pytest -k "{PYTEST_K_O2}": all passed, 0 failed, 0 skipped; the O2 baseline\'s tests and '
                     f"REQUIRED_TESTS_O2 among them", "; ".join(bad) or f"{len(got['passed'])} passed")


def pytest_g13() -> dict:
    """Run G13's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K_O3)


def g13(got: dict) -> tuple:
    bad = _selection_bad(None, got, REQUIRED_TESTS_O3)
    return (not bad, f'G13: pytest -k "{PYTEST_K_O3}": all passed, 0 failed, 0 skipped; every REQUIRED_TESTS_O3 '
                     f"among them", "; ".join(bad) or f"{len(got['passed'])} passed")


def pytest_g19() -> dict:
    """Run G19's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K_O4)


def g19(got: dict) -> tuple:
    bad = _selection_bad(None, got, REQUIRED_TESTS_O4)
    return (not bad, f'G19: pytest -k "{PYTEST_K_O4}": all passed, 0 failed, 0 skipped; every REQUIRED_TESTS_O4 '
                     f"among them", "; ".join(bad) or f"{len(got['passed'])} passed")


def pytest_g26() -> dict:
    """Run G26's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K_O5)


def g26(got: dict) -> tuple:
    bad = _selection_bad(None, got, REQUIRED_TESTS_O5)
    return (not bad, f'G26: pytest -k "{PYTEST_K_O5}": all passed, 0 failed, 0 skipped; every REQUIRED_TESTS_O5 '
                     f"among them", "; ".join(bad) or f"{len(got['passed'])} passed")


# ======================================================================== what the O4 code says (G20)
def _o4() -> tuple:
    """``(o4_castle, o4_dryrun)``: imported here, never at the module's top, as the O2 and O3 items import theirs."""
    import o4_castle as C4
    import o4_dryrun as D4
    return C4, D4


def o4_run_cases_quietly() -> tuple:
    """``(rc, last line, which predictions)``: ``o4_dryrun.run_cases`` on the frozen O4 predictions once they exist,
    else on the draft (its own default), its per-case lines swallowed."""
    C4, D4 = _o4()
    path = C4.PREDICTIONS if C4.PREDICTIONS.is_file() else None
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D4.run_cases(path)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else ""), (f"the frozen {path.name}" if path is not None else "the draft")


def g20() -> tuple:
    """G20 (research/o4_design.md 9 C2): O4's dry run, every case as registered, at least the floor."""
    what = (f"G20: o4_dryrun.run_cases returns 0, every case as registered, at least {O4_DRYRUN_FLOOR} (the frozen "
            f"O4 predictions once they exist, else the draft)")
    try:
        rc, last, which = o4_run_cases_quietly()
    except Exception as err:                       # noqa: BLE001 -- a dry run that cannot run is a FAIL, said
        return False, what, f"run_cases raised {type(err).__name__}: {str(err)[:300]}"
    m = re.fullmatch(r"(\d+)/(\d+) cases as registered", last)
    bad = []
    if rc != 0 or m is None or m.group(1) != m.group(2):
        bad.append(f"run_cases returned {rc}: {last!r}")
    elif int(m.group(2)) < O4_DRYRUN_FLOOR:
        bad.append(f"{last!r}: under the floor {O4_DRYRUN_FLOOR} -- a case or a unit was dropped")
    return not bad, what, "; ".join(bad) or f"{last} ({which})"


# ======================================================================== what the O5 code says (G27)
def _o5() -> tuple:
    """``(o5_hallway, o5_dryrun)``: imported here, never at the module's top, as the O2-O4 items import theirs."""
    import o5_hallway as C5
    import o5_dryrun as D5
    return C5, D5


def o5_run_cases_quietly() -> tuple:
    """``(rc, last line, which predictions)``: ``o5_dryrun.run_cases`` on the frozen O5 predictions once they exist,
    else on the draft (its own default), its per-case lines swallowed."""
    C5, D5 = _o5()
    path = C5.PREDICTIONS if C5.PREDICTIONS.is_file() else None
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D5.run_cases(path)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else ""), (f"the frozen {path.name}" if path is not None else "the draft")


def g27() -> tuple:
    """G27 (research/o5_design.md 9 C2): O5's dry run, every case as registered, at least the floor."""
    what = (f"G27: o5_dryrun.run_cases returns 0, every case as registered, at least {O5_DRYRUN_FLOOR} (the frozen "
            f"O5 predictions once they exist, else the draft)")
    try:
        rc, last, which = o5_run_cases_quietly()
    except Exception as err:                       # noqa: BLE001 -- a dry run that cannot run is a FAIL, said
        return False, what, f"run_cases raised {type(err).__name__}: {str(err)[:300]}"
    m = re.fullmatch(r"(\d+)/(\d+) cases as registered", last)
    bad = []
    if rc != 0 or m is None or m.group(1) != m.group(2):
        bad.append(f"run_cases returned {rc}: {last!r}")
    elif int(m.group(2)) < O5_DRYRUN_FLOOR:
        bad.append(f"{last!r}: under the floor {O5_DRYRUN_FLOOR} -- a case or a unit was dropped")
    return not bad, what, "; ".join(bad) or f"{last} ({which})"


# ======================================================================== what the O3 code says (G14)
def _o3() -> tuple:
    """``(o3_prima_vista, o3_dryrun)``: imported here, never at the module's top, as the O2 items import O2's."""
    import o3_prima_vista as P
    import o3_dryrun as D3
    return P, D3


def o3_run_cases_quietly() -> tuple:
    """``(rc, last line, which predictions)``: ``o3_dryrun.run_cases`` on the frozen O3 predictions once they exist,
    else on the draft (its own default), its per-case lines swallowed."""
    P, D3 = _o3()
    path = P.PREDICTIONS if P.PREDICTIONS.is_file() else None
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D3.run_cases(path)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else ""), (f"the frozen {path.name}" if path is not None else "the draft")


def g14() -> tuple:
    """G14 (the review, research/o3_design.md 11.7 #12): O3's dry run, every case as registered, at least the floor."""
    what = (f"G14: o3_dryrun.run_cases returns 0, every case as registered, at least {O3_DRYRUN_FLOOR} (the frozen "
            f"O3 predictions once they exist, else the draft)")
    try:
        rc, last, which = o3_run_cases_quietly()
    except Exception as err:                       # noqa: BLE001 -- a dry run that cannot run is a FAIL, said
        return False, what, f"run_cases raised {type(err).__name__}: {str(err)[:300]}"
    m = re.fullmatch(r"(\d+)/(\d+) cases as registered", last)
    bad = []
    if rc != 0 or m is None or m.group(1) != m.group(2):
        bad.append(f"run_cases returned {rc}: {last!r}")
    elif int(m.group(2)) < O3_DRYRUN_FLOOR:
        bad.append(f"{last!r}: under the floor {O3_DRYRUN_FLOOR} -- a case or a unit was dropped")
    return not bad, what, "; ".join(bad) or f"{last} ({which})"


# ======================================================================== what the O3 code says (G15-G18)
def _tmp_forms(root) -> list:
    """Every spelling of a temporary root an output can carry: as made and resolved, each with its backslashes as
    written, doubled (a ``repr`` or a JSON dump of it) and as a posix path -- longest first."""
    forms = set()
    for p in (Path(root), Path(root).resolve()):
        s = str(p)
        forms |= {s, s.replace("\\", "\\\\"), p.as_posix()}
    return sorted(forms, key=len, reverse=True)


def untemp(obj, roots):
    """``obj`` (strings, lists, tuples and dicts of them) with every spelling of each temporary root in ``roots``
    replaced by :data:`TMP` -- a reading's paths, never its content: anything else that differs between two readings
    stays and is named (G0'')."""
    forms = [f for r in roots for f in _tmp_forms(r)]

    def fix(x):
        if isinstance(x, str):
            for f in forms:
                x = x.replace(f, TMP)
            return x
        if isinstance(x, list):
            return [fix(v) for v in x]
        if isinstance(x, tuple):
            return tuple(fix(v) for v in x)
        if isinstance(x, dict):
            return {k: fix(v) for k, v in x.items()}
        return x
    return fix(obj)


def o3_analyse_archive() -> dict:
    P, _D3 = _o3()
    return _pair(*P.O3.analyse(O3S, pred_path=V1_O3))


def o3_dryrun_outputs(stock) -> tuple:
    """``({case: (checks, report)}, [case names in run order], [[unit, ok, detail], ...])`` -- ``o3_dryrun.run_cases``'s
    own loop over V1_O3, step for step: the same temporary layout (``pred/``, ``sessions/``), the same session
    directories in the same order (``s0``, ``s1``, ... -- each report's title carries its label), the same units in the
    same order on the same temporary root (state-history's session is the last one made; the offline mutants, the
    skip A/B and its files after the named units, as run_cases evaluates them). Left out are only run_cases's verdict
    comparisons and its extra ``read_session`` reads of a case's VOID classes: pure reads that make no directory and
    leave nothing an output reads. Every output is returned with its temporary root read as :data:`TMP`
    (:func:`untemp`)."""
    from ff9mapkit.content.verbatim import remap_fields
    P, D3 = _o3()
    out, order, units = {}, [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdir = tmp / "pred"
        pdir.mkdir()
        sdir = tmp / "sessions"
        sdir.mkdir()
        path = V1_O3                                      # run_cases's _prepare(V1_O3, pdir) is V1_O3 itself
        pred, _sha = P.O3.load(path)
        members = D3.members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, *_want in D3.CASES:
            d = D3.make_session(sdir, path, fn(copy.deepcopy(pred)), scripts)
            out[name] = _pair(*P.O3.analyse(d, stock=stock))
            order.append(name)
        copy_path = pdir / "pred_copy.json"               # O3-FROZEN: the predictions changed after the session
        copy_path.write_bytes(path.read_bytes())
        d = D3.make_session(sdir, copy_path, D3.six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        out["predictions-changed"] = _pair(*P.O3.analyse(d, stock=stock))
        order.append("predictions-changed")
        for name, fn in (("no-sc-span", D3.unit_no_sc_span),
                         ("trace-summary", lambda: D3.unit_trace_summary(pred, stock)),
                         ("state-history", lambda: D3.unit_state_history(pred, stock, scripts, sdir, path)),
                         ("p-donor-log", D3.unit_p_donor_log),
                         ("p-launch", lambda: D3.unit_p_launch(tmp)),
                         ("p-stock-battle", lambda: D3.unit_p_stock_battle(tmp)),
                         ("p-settings", lambda: D3.unit_p_settings(tmp)),
                         ("battle-row", lambda: D3.unit_battle_row(pred)),
                         ("build-legacy", lambda: D3.unit_build_legacy(tmp))):
            ok, detail = fn()
            units.append([name, ok, detail])
        for name, ok, detail in D3.unit_scene_census(pred) + D3.unit_store_census(pred, stock) + \
                D3.unit_offline_mutants(pred, stock, tmp) + D3.unit_skip_ab(pred, stock) + \
                D3.unit_skip_ab_files(pred, stock, tmp, path):
            units.append([name, ok, detail])
    return untemp(out, [tmp]), order, untemp(units, [tmp])


def o3_offline() -> list:
    P, _D3 = _o3()
    pred, _sha = P.O3.load(V1_O3)
    return [list(c) for c in P.O3.offline_check(pred)]


def o3_run_cases_v1() -> tuple:
    """``(rc, last line)`` of ``o3_dryrun.run_cases(V1_O3)``, its per-case lines swallowed (G17)."""
    _P, D3 = _o3()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D3.run_cases(V1_O3)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else "")


def o3_cli_analyse() -> tuple:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "o3_prima_vista.py"), "--analyse", str(O3S), "--predictions",
                        str(V1_O3)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout, p.stderr


def _verdict_o3(pair: dict) -> str:
    _P, D3 = _o3()
    return D3.verdict([tuple(c) for c in pair["checks"]])


def g15(base: dict, got: dict) -> tuple:
    bad = []
    archived = (O3S / "o3_report.txt").read_text(encoding="utf-8")
    if got["report"] != archived:
        bad.append(f"the report is not the archived o3_report.txt: {_first_diff(got['report'], archived)}")
    if base is not None:
        bad += _same(got, base["o3s"], "story-o3")
    checks = got["checks"]
    v = _verdict_o3(got)
    if v != O3S_VERDICT or len(checks) != O3S_CHECKS or not all(c[0] is True for c in checks):
        bad.append(f"verdict {v!r} over {len(checks)} checks, want {O3S_VERDICT} over {O3S_CHECKS}, all True")
    return (not bad, f"G15: analyse(story-o3, v1) is the archived report exactly, PROVEN with {O3S_CHECKS} checks "
                     f"all True", "; ".join(bad) or f"{len(got['report'].splitlines())} report lines, {v}")


def g16(report: str) -> tuple:
    rc, out, err = o3_cli_analyse()
    bad = []
    if rc != 0:
        bad.append(f"exit {rc}: {err[-300:]}")
    if out != report + "\n":
        bad.append(f"stdout is not the report plus print's newline: {_first_diff(out, report + chr(10))}")
    return (not bad, "G16: the CLI o3_prima_vista.py --analyse story-o3 --predictions v1 exits 0 and prints that "
                     "report", "; ".join(bad) or "exit 0")


def g17(base: dict, got: dict, order: list, units: list) -> tuple:
    bad = []
    if base is not None:
        if order != base["dryrun_order"]:
            bad.append(f"cases {order} != the baseline's {base['dryrun_order']}"[:400])
        for name in order:
            if name in base["dryrun"]:
                bad += _same(got[name], base["dryrun"][name], name)
        if units != base["units"]:
            want = {u[0]: u for u in base["units"]}
            diff = [u[0] for u in units if want.get(u[0]) != u] + [n for n in want if n not in {u[0] for u in units}]
            bad.append(f"units differ from the baseline's: {diff[:6]}"
                       + ("" if [u[0] for u in units] == [u[0] for u in base["units"]] else " (and their order)"))
    off = [u[0] for u in units if u[1] is not True]
    if off:
        bad.append(f"units not as registered: {off[:6]}")
    rc, last = o3_run_cases_v1()
    n = len(order) + len(units)
    if rc != 0 or last != f"{n}/{n} cases as registered":
        bad.append(f"run_cases(v1) returned {rc}: {last!r}, want {n}/{n}")
    return (not bad, "G17: every o3_dryrun case's (checks, report) and unit's (name, ok, detail) is the baseline's, "
                     "byte for byte; run_cases(v1) 0", "; ".join(bad[:4]) or f"{len(order)} sessions, {len(units)} "
                                                                             f"units; {last}")


def g18(base: dict, got: list) -> tuple:
    bad = [] if base is None or got == base["offline"] else [f"{got} != {base['offline']}"[:500]]
    if len(got) != O3_OFFLINE_CHECKS or not all(c[0] is True for c in got):
        bad.append(f"offline_check(v1) reads {[c[0] for c in got]}, want {O3_OFFLINE_CHECKS} x True")
    return (not bad, f"G18: O3's offline_check(v1) is the baseline's [(ok, what, detail)], {O3_OFFLINE_CHECKS} PASS",
            "; ".join(bad) or "; ".join(f"{c[1].split(':')[0]}: {c[2][:90]}" for c in got))


# ======================================================================== what the O4 code says (G22-G25)
def o4_analyse_archive() -> dict:
    C4, _D4 = _o4()
    return _pair(*C4.O4.analyse(O4S, pred_path=V1_O4))


def o4_dryrun_outputs(stock) -> tuple:
    """``({case: (checks, report)}, [case names in run order], [[unit, ok, detail], ...])`` -- ``o4_dryrun.run_cases``'s
    own loop over V1_O4, step for step: the same temporary layout (``pred/``, ``sessions/``), the same session
    directories in the same order (``s0``, ``s1``, ... -- each report's title carries its label), the same units in the
    same order on the same temporary root (``units(...)``'s single units -- state-history's session is the last one
    made -- then ``listed_units(...)``: O4-CENSUS, the build pins, the fight pins, the offline mutants). Left out are
    only run_cases's verdict comparisons and its extra ``read_session`` reads of a case's VOID classes and coverage:
    pure reads that make no directory and leave nothing an output reads. Every output is returned with its temporary
    root read as :data:`TMP` (:func:`untemp`)."""
    from ff9mapkit.content.verbatim import remap_fields
    C4, D4 = _o4()
    out, order, units = {}, [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdir = tmp / "pred"
        pdir.mkdir()
        sdir = tmp / "sessions"
        sdir.mkdir()
        path = V1_O4                                      # run_cases's prepare(V1_O4, pdir) is V1_O4 itself
        pred, _sha = C4.O4.load(path)
        members = D4.members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, *_want in D4.CASES:
            d = D4.make_session(sdir, path, fn(copy.deepcopy(pred)), scripts)
            out[name] = _pair(*C4.O4.analyse(d, stock=stock))
            order.append(name)
        copy_path = pdir / "pred_copy.json"               # O4-FROZEN: the predictions changed after the session
        copy_path.write_bytes(path.read_bytes())
        d = D4.make_session(sdir, copy_path, D4.six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        out["predictions-changed"] = _pair(*C4.O4.analyse(d, stock=stock))
        order.append("predictions-changed")
        for name, fn in D4.units(pred, stock, scripts, sdir, path, tmp):
            ok, detail = fn()
            units.append([name, ok, detail])
        for name, ok, detail in D4.listed_units(pred, stock, tmp):
            units.append([name, ok, detail])
    return untemp(out, [tmp]), order, untemp(units, [tmp])


def o4_offline() -> list:
    C4, _D4 = _o4()
    pred, _sha = C4.O4.load(V1_O4)
    return [list(c) for c in C4.O4.offline_check(pred)]


def o4_run_cases_v1() -> tuple:
    """``(rc, last line)`` of ``o4_dryrun.run_cases(V1_O4)``, its per-case lines swallowed (G24)."""
    _C4, D4 = _o4()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D4.run_cases(V1_O4)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else "")


def o4_cli_analyse() -> tuple:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "o4_castle.py"), "--analyse", str(O4S), "--predictions",
                        str(V1_O4)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout, p.stderr


def _verdict_o4(pair: dict) -> str:
    _C4, D4 = _o4()
    return D4.verdict([tuple(c) for c in pair["checks"]])


def g22(base: dict, got: dict) -> tuple:
    bad = []
    archived = (O4S / "o4_report.txt").read_text(encoding="utf-8")
    if got["report"] != archived:
        bad.append(f"the report is not the archived o4_report.txt: {_first_diff(got['report'], archived)}")
    if base is not None:
        bad += _same(got, base["o4s"], "story-o4")
    checks = got["checks"]
    v = _verdict_o4(got)
    if v != O4S_VERDICT or len(checks) != O4S_CHECKS or not all(c[0] is True for c in checks):
        bad.append(f"verdict {v!r} over {len(checks)} checks, want {O4S_VERDICT} over {O4S_CHECKS}, all True")
    return (not bad, f"G22: analyse(story-o4, v1) is the archived report exactly, PROVEN with {O4S_CHECKS} checks "
                     f"all True", "; ".join(bad) or f"{len(got['report'].splitlines())} report lines, {v}")


def g23(report: str) -> tuple:
    rc, out, err = o4_cli_analyse()
    bad = []
    if rc != 0:
        bad.append(f"exit {rc}: {err[-300:]}")
    if out != report + "\n":
        bad.append(f"stdout is not the report plus print's newline: {_first_diff(out, report + chr(10))}")
    return (not bad, "G23: the CLI o4_castle.py --analyse story-o4 --predictions v1 exits 0 and prints that report",
            "; ".join(bad) or "exit 0")


def g24(base: dict, got: dict, order: list, units: list) -> tuple:
    bad = []
    if base is not None:
        if order != base["dryrun_order"]:
            bad.append(f"cases {order} != the baseline's {base['dryrun_order']}"[:400])
        for name in order:
            if name in base["dryrun"]:
                bad += _same(got[name], base["dryrun"][name], name)
        if units != base["units"]:
            want = {u[0]: u for u in base["units"]}
            diff = [u[0] for u in units if want.get(u[0]) != u] + [n for n in want if n not in {u[0] for u in units}]
            bad.append(f"units differ from the baseline's: {diff[:6]}"
                       + ("" if [u[0] for u in units] == [u[0] for u in base["units"]] else " (and their order)"))
    off = [u[0] for u in units if u[1] is not True]
    if off:
        bad.append(f"units not as registered: {off[:6]}")
    rc, last = o4_run_cases_v1()
    n = len(order) + len(units)
    if rc != 0 or last != f"{n}/{n} cases as registered":
        bad.append(f"run_cases(v1) returned {rc}: {last!r}, want {n}/{n}")
    return (not bad, "G24: every o4_dryrun case's (checks, report) and unit's (name, ok, detail) is the baseline's, "
                     "byte for byte; run_cases(v1) 0", "; ".join(bad[:4]) or f"{len(order)} sessions, {len(units)} "
                                                                             f"units; {last}")


def g25(base: dict, got: list) -> tuple:
    bad = [] if base is None or got == base["offline"] else [f"{got} != {base['offline']}"[:500]]
    if len(got) != O4_OFFLINE_CHECKS or not all(c[0] is True for c in got):
        bad.append(f"offline_check(v1) reads {[c[0] for c in got]}, want {O4_OFFLINE_CHECKS} x True")
    return (not bad, f"G25: O4's offline_check(v1) is the baseline's [(ok, what, detail)], {O4_OFFLINE_CHECKS} PASS",
            "; ".join(bad) or "; ".join(f"{c[1].split(':')[0]}: {c[2][:90]}" for c in got))


# ======================================================================== the driver's source pins (G21)
def _py() -> str:
    """The interpreter's version, ``major.minor``: ``ast.dump`` is version-specific (a new field, a new default)."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def functions_of(source: str) -> dict:
    """``{qualified name: node}`` of a module's functions: a module-level ``name`` and a class's ``Class.name``. The
    LAST definition of a name wins, as Python binds it (and pytest collects it)."""
    out = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[f"{node.name}.{sub.name}"] = sub
    return out


def source_shas(names, *, files=None) -> dict:
    """``{pin: the sha256 of ast.dump(node, include_attributes=False) | None}`` for each pin ``<file>::<qualname>``
    -- None when the file holds no such function (renamed or deleted). ``files`` maps a pin's file to the path read
    (default :data:`PIN_FILES`; a test passes a temporary copy). Comments and whitespace are not in the AST; every
    code edit, a docstring's included, is. A file that does not parse raises (SyntaxError)."""
    files = PIN_FILES if files is None else files
    by_file: dict = {}
    for name in names:
        rel, _sep, qual = name.partition("::")
        by_file.setdefault(rel, []).append((name, qual))
    out = {}
    for rel, items in by_file.items():
        path = files.get(rel)
        funcs = functions_of(Path(path).read_text(encoding="utf-8")) if path is not None and Path(path).is_file() \
            else {}
        for name, qual in items:
            node = funcs.get(qual)
            out[name] = None if node is None else hashlib.sha256(
                ast.dump(node, include_attributes=False).encode("utf-8")).hexdigest()
    return out


def pin_of_test(test_name: str) -> str:
    """The pin of a collected test (a JUnit name; a parametrized one's ``[...]`` is its function's)."""
    func = re.sub(r"\[.*\]$", "", test_name)
    return f"{TEST_REL}::{func}"


def fake_pins_o4(source: str | None = None) -> list:
    """The fake's O4 pins (research/o5_design.md 1.4 G0'''): :data:`FAKE_PINS_O4`, then every method of each class of
    :data:`FAKE_PIN_CLASSES_O4` in the order fakegame.py defines it -- each ``<qualname>`` (``Class.method``), read
    from ``source`` (default: fakegame.py as it stands). A class with no method found raises: it was renamed."""
    source = (ROOT / FAKE_REL).read_text(encoding="utf-8") if source is None else source
    names = list(FAKE_PINS_O4)
    funcs = list(functions_of(source))
    for cls in FAKE_PIN_CLASSES_O4:
        methods = [q for q in funcs if q.startswith(cls + ".")]
        if not methods:
            raise ValueError(f"fakegame.py defines no method of {cls}: the O4 pins name a class it no longer has")
        names += [q for q in methods if q not in names]
    return names


def o4_pin_names(o3_sources: dict, names) -> list:
    """The O4 baseline's pins (G0'''): ``names`` -- the tests G19 collects and the fake's O4 functions -- in order,
    each once. ValueError naming every name the O3 baseline's ``sources`` already pin: a name pinned by both
    baselines would carry two pins in force, so the capture refuses it rather than choose one."""
    out = list(dict.fromkeys(names))
    both = [n for n in out if n in o3_sources]
    if both:
        raise ValueError(f"{len(both)} name(s) pinned in both the O3 and the O4 baselines: {both[:6]} -- the O4 "
                         f"baseline pins only names the O3 baseline does not")
    return out


def union_sources(o3_sources: dict, o4_sources: dict) -> dict:
    """G21's pins (research/o5_design.md 1.4): the O3 baseline's ``sources`` and the O4 baseline's, one dict.
    ValueError naming every name pinned in BOTH: no union then -- which pin is in force would be a choice."""
    both = sorted(set(o3_sources) & set(o4_sources))
    if both:
        raise ValueError(f"{len(both)} name(s) pinned in both the O3 and the O4 baselines: {both[:6]} -- a name has "
                         f"one pin in force")
    return {**o3_sources, **o4_sources}


def union_base(base_o3: dict, base_o4: dict) -> dict:
    """The baseline G21 judges (:func:`g21`): ``{"sources": the union, "sources_python"}`` -- the Python both pins were
    taken under, or both named (``3.14 / 3.15``) when they differ. ValueError as :func:`union_sources`."""
    sources = union_sources(base_o3.get("sources") or {}, base_o4.get("sources") or {})
    pys = [p for p in (base_o3.get("sources_python"), base_o4.get("sources_python")) if p is not None]
    py = None if not pys else pys[0] if len(set(pys)) == 1 else " / ".join(pys)
    return {"sources": sources, "sources_python": py}


def pins_in_force(sources: dict, rows: list) -> dict:
    """``{name: sha}``: the baseline's ``sources``, each name a row re-baselines at its LATEST row's ``new``."""
    force = dict(sources)
    for row in rows:
        if isinstance(row, dict) and row.get("name") in force:
            force[row["name"]] = row.get("new")
    return force


def pin_row(sources: dict, rows: list, name: str, old, new, reason, head) -> dict:
    """A re-baseline row for ``name`` after ``rows`` (``--rebaseline-source``'s, and every row G21 replays):
    ``{"name", "old", "new", "reason", "head"}``. ValueError on an empty reason (it says WHY the pinned source
    changed), a name not pinned, an ``old`` that is not the pin in force (a stale pins file, or a row since), a
    ``new`` that is no function (a pin cannot follow a rename), and a ``new`` that IS the pin in force (nothing
    changed: nothing to re-baseline)."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError(f"{name}: a re-baseline needs its reason (--reason TEXT): why the pinned source changed")
    if name not in sources:
        raise ValueError(f"{name!r} is not pinned: the O3 and O4 baselines' sources hold {len(sources)} names "
                         f"(<file>::<qualname>, e.g. {next(iter(sorted(sources)), '-')})")
    force = pins_in_force(sources, rows)[name]
    if old != force:
        raise ValueError(f"{name}: old {str(old)[:12]} is not the pin in force {str(force)[:12]} (a stale pins file, "
                         f"or another row since)")
    if not isinstance(new, str) or not new:
        raise ValueError(f"{name}: no such function now (renamed or deleted): a pin never follows a rename")
    if new == force:
        raise ValueError(f"{name}: its source is its pin in force ({force[:12]}): nothing changed, nothing to "
                         f"re-baseline")
    return {"name": name, "old": old, "new": new, "reason": reason.strip(), "head": str(head)}


def pin_rows_bad(sources: dict, rows) -> list:
    """What is wrong with the pins file, replayed in order: a list of rows, each exactly :data:`PIN_ROW_KEYS` and each
    a row :func:`pin_row` would have appended at its place (so a hand edit -- a reason emptied, an ``old`` rewritten,
    a row reordered -- FAILS G21 by its row)."""
    if not isinstance(rows, list):
        return [f"the pins file holds a {type(rows).__name__}, not a list of rows"]
    bad = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != set(PIN_ROW_KEYS):
            bad.append(f"row {i}: not exactly {list(PIN_ROW_KEYS)}: {str(row)[:120]}")
            continue
        try:
            pin_row(sources, rows[:i], row["name"], row["old"], row["new"], row["reason"], row["head"])
        except ValueError as err:
            bad.append(f"row {i}: {err}")
    return bad


def g21_bad(sources: dict, current: dict, rows) -> list:
    """G21's verdict, pure: the pins file's own faults (:func:`pin_rows_bad`), then every pinned name that is gone
    (``current`` None: renamed or deleted) or whose ``current`` sha is not its pin in force."""
    bad = pin_rows_bad(sources, rows)
    force = pins_in_force(sources, rows if isinstance(rows, list) else [])
    for name in sorted(sources):
        now = current.get(name)
        if now is None:
            bad.append(f"{name}: gone (renamed or deleted) -- a pinned source must stay")
        elif now != force[name]:
            bad.append(f"{name}: changed ({str(force[name])[:8]} -> {now[:8]}) -- re-baseline it by name with its "
                       f"reason (--rebaseline-source NAME --reason TEXT) in the commit that changes it")
    return bad


def g21(base: dict, pins: Path = SOURCE_PINS, *, files=None) -> tuple:
    """G21 over ``base``'s ``sources`` -- the gate passes :func:`union_base` of the O3 and O4 baselines; a test passes
    its own (research/o5_design.md 1.4)."""
    what = ("G21: every pinned source -- the O1-O3 tests G7, G12 and G13 collected at the O3 capture, the fake's beat "
            "and input functions; the O4 tests G19 collected at the O4 capture, the fake's story sink and machine "
            "beats -- is its pin in force (its baseline's sha, or its latest re-baseline row's)")
    sources = base.get("sources") or {}
    if not sources:
        return False, what, "the O3 baseline holds no sources: it was captured without its pins"
    try:
        rows = json.loads(Path(pins).read_bytes())
    except (OSError, ValueError) as err:
        return False, what, f"{Path(pins).name} unreadable: {err}"
    try:
        current = source_shas(sorted(sources), files=files)
    except SyntaxError as err:
        return False, what, f"a pinned file does not parse: {err}"
    bad = g21_bad(sources, current, rows)
    py = base.get("sources_python")
    if bad and py is not None and py != _py():
        bad.insert(0, f"the pins were taken under Python {py}, this is {_py()} (ast.dump is version-specific)")
    n = len(rows) if isinstance(rows, list) else 0
    return (not bad, what, "; ".join(bad[:6]) + (f" (+{len(bad) - 6} more)" if len(bad) > 6 else "")
            or f"{len(sources)} sources at their pins ({n} re-baseline row{'s' if n != 1 else ''} in "
               f"{Path(pins).name})")


def rebaseline_source(name: str, reason, *, baseline: Path = BASELINE_O3, baseline_o4: Path | None = None,
                      pins: Path = SOURCE_PINS, files=None) -> int:
    """``--rebaseline-source NAME --reason TEXT``: append ONE row to the pins file -- ``name`` at its current sha, its
    ``old`` the pin in force -- after the file's own rows replay clean. ``name`` is looked up in either baseline (the
    union of the O3 and O4 baselines' ``sources``, :func:`union_sources`; research/o5_design.md 1.4): the CLI passes the
    committed O4 baseline (``--baseline-o4``); a call that names none (``baseline_o4`` None) reads the O3 baseline's
    ``sources`` alone, as O4's call did -- a test's temporary baseline never meets the committed O4 one. Every refusal
    of :func:`pin_row` (and a name pinned in both baselines) is an exit 1 with nothing written. ``files``:
    :func:`source_shas`' seam."""
    base = json.loads(Path(baseline).read_bytes())
    base4 = {} if baseline_o4 is None else json.loads(Path(baseline_o4).read_bytes())
    try:
        sources = union_sources(base.get("sources") or {}, base4.get("sources") or {})
    except ValueError as err:
        print(f"!! refused: {err} -- nothing written")
        return 1
    rows = json.loads(Path(pins).read_bytes())
    bad = pin_rows_bad(sources, rows)
    if bad:
        print(f"!! {Path(pins).name} does not replay clean: {'; '.join(bad[:4])} -- nothing written")
        return 1
    now = source_shas([name], files=files).get(name) if name in sources else None
    try:
        row = pin_row(sources, rows, name, pins_in_force(sources, rows).get(name), now, reason, _head())
    except ValueError as err:
        print(f"!! refused: {err}")
        return 1
    rows.append(row)
    Path(pins).write_bytes((json.dumps(rows, indent=1) + "\n").encode("utf-8"))
    print(f"re-baselined {name}: {row['old'][:8]} -> {row['new'][:8]} ({row['reason']}); {Path(pins).name} holds "
          f"{len(rows)} row(s)")
    return 0


# ======================================================================== the gate
def _missing(*, o1: bool = True, o2: bool = True, o3: bool = False, o3s: bool = False, o4: bool = False,
             o4s: bool = False, o5: bool = False, files=()) -> list:
    """The inputs the items read that are not here (each makes the gate "not run", exit 2). O3's dry run (G14) reads
    the frozen O3 predictions, or -- until they exist -- the draft, which reads O1's chain build (machine-local).
    ``o3s``: G15-G18's -- the story-o3 archive's session and report, and the frozen v1; ``o4``: O4's dry run's (G20)
    -- the frozen O4 predictions, or until they exist the O4 chain's campaign.toml the draft reads (machine-local);
    ``o4s``: G22-G25's -- the story-o4 archive's session and report, and the frozen v1 (research/o5_design.md 1.4);
    ``o5``: O5's dry run's (G27) -- the frozen O5 predictions, or until they exist the campaign.toml of O4's chain the
    draft reads (machine-local); ``files``: whatever else the mode reads (the O3 and O4 baselines and the pins file for
    the gate, the O1 and O2 baselines for --capture-o3, the O3 baseline for --capture-o4)."""
    need = ([V4, O1E / "o1_session.json", O1E / "o1_report.txt", O1D / "o1_session.json"] if o1 else []) \
        + ([V1, O2S / "o2_session.json", O2S / "o2_report.txt"] if o2 else [])
    if o3:
        P, _D3 = _o3()
        need.append(P.PREDICTIONS if P.PREDICTIONS.is_file() else P.CHAIN_DIR / "campaign.toml")
    if o3s:
        need += [V1_O3, O3S / "o3_session.json", O3S / "o3_report.txt"]
    if o4:
        C4, _D4 = _o4()
        need.append(C4.PREDICTIONS if C4.PREDICTIONS.is_file() else C4.CHAIN_DIR / "campaign.toml")
    if o4s:
        C4, _D4 = _o4()
        need += [V1_O4, O4S / C4.SESSION_FILE, O4S / "o4_report.txt"]
    if o5:
        C5, _D5 = _o5()
        need.append(C5.PREDICTIONS if C5.PREDICTIONS.is_file() else C5.CHAIN_DIR / "campaign.toml")
    need += [Path(p) for p in files]
    return [str(p) for p in need if not p.is_file()]


def collect() -> dict:
    """Everything the O1 code says, once: the gate's reading (and, at G0, the baseline's)."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order = dryrun_outputs(stock)
    return {"o1e": analyse_archive(O1E), "o1d": analyse_archive(O1D), "dryrun": dry, "dryrun_order": order,
            "noise_mutant": noise_mutant(stock), "offline": offline()}


def judge(base: dict | None, got: dict, tests: dict) -> list:
    return [g1(base, got["o1e"]), g2(got["o1e"]["report"]), g3(base, got["dryrun"], got["dryrun_order"]),
            g4(base, got["offline"]), g5(base, got["o1d"]), g6(base, got["noise_mutant"]), g7(base, tests)]


def collect_o2() -> dict:
    """Everything the O2 code says, once: the gate's reading (and, at G0', the O2 baseline's)."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order, units = o2_dryrun_outputs(stock)
    return {"o2s": o2_analyse_archive(), "dryrun": dry, "dryrun_order": order, "units": units,
            "offline": o2_offline()}


def judge_o2(base: dict | None, got: dict, tests: dict) -> list:
    return [g8(base, got["o2s"]), g9(got["o2s"]["report"]), g10(base, got["dryrun"], got["dryrun_order"],
                                                                 got["units"]),
            g11(base, got["offline"]), g12(base, tests)]


def collect_o3() -> dict:
    """Everything the O3 code says, once: the gate's reading (and, at G0'', the O3 baseline's), every temporary root
    read as :data:`TMP`."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order, units = o3_dryrun_outputs(stock)
    return {"o3s": o3_analyse_archive(), "dryrun": dry, "dryrun_order": order, "units": units,
            "offline": o3_offline()}


def judge_o3(base: dict | None, got: dict) -> list:
    return [g15(base, got["o3s"]), g16(got["o3s"]["report"]),
            g17(base, got["dryrun"], got["dryrun_order"], got["units"]), g18(base, got["offline"])]


def collect_o4() -> dict:
    """Everything the O4 code says, once: the gate's reading (and, at G0''', the O4 baseline's), every temporary root
    read as :data:`TMP`."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order, units = o4_dryrun_outputs(stock)
    return {"o4s": o4_analyse_archive(), "dryrun": dry, "dryrun_order": order, "units": units,
            "offline": o4_offline()}


def judge_o4(base: dict | None, got: dict) -> list:
    return [g22(base, got["o4s"]), g23(got["o4s"]["report"]),
            g24(base, got["dryrun"], got["dryrun_order"], got["units"]), g25(base, got["offline"])]


def readings_differ(a: dict, b: dict) -> list:
    """What differs between two readings of :func:`collect_o3` (G0''), by name: a dry-run case, a unit (or the units'
    order), or a whole item -- never excluded, never summarised away."""
    out = []
    for key in sorted(set(a) | set(b)):
        x, y = a.get(key), b.get(key)
        if key == "dryrun" and isinstance(x, dict) and isinstance(y, dict):
            out += [f"case {n}" for n in sorted(set(x) | set(y)) if x.get(n) != y.get(n)]
        elif key == "units" and isinstance(x, list) and isinstance(y, list):
            ux, uy = {u[0]: u for u in x}, {u[0]: u for u in y}
            out += [f"unit {n}" for n in sorted(set(ux) | set(uy)) if ux.get(n) != uy.get(n)]
            if [u[0] for u in x] != [u[0] for u in y]:
                out.append("the units' order")
        elif x != y:
            out.append(key)
    return out


def _head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True)
    return p.stdout.strip() or "unknown"


def capture(out: Path) -> int:
    if out.exists():
        raise SystemExit(f"!! {out} exists: the baseline is captured once, before the refactor. It is never "
                         f"overwritten.")
    got = collect()
    tests = pytest_g7()
    items = judge(None, got, tests)
    for ok, what, detail in items:
        print(f"{'PASS' if ok else 'FAIL'}  {what}\n      {detail}")
    if not all(ok for ok, _w, _d in items):
        print("!! the pre-refactor code does not pass its own gate: no baseline written")
        return 1
    _pred, sha = O.load_predictions(V4)
    base = {"what": "O1's outputs at the pre-refactor code (research/o2_design.md 1.6 G0): every (checks, report) "
                    "the regression gate compares byte for byte",
            "head": _head(), "predictions": V4.name, "predictions_sha256": sha,
            "archives": {"o1e": str(O1E), "o1d": str(O1D)}, "tests": sorted(tests["passed"]), **got}
    text = json.dumps(base, indent=1, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    print(f"captured: {out} ({len(text)} chars, head {base['head'][:8]})")
    return 0


def capture_o2(out: Path) -> int:
    """G0': the O2 baseline, once, at the code BEFORE any O3 change (research/o3_design.md 1.4, 9 A0)."""
    if out.exists():
        raise SystemExit(f"!! {out} exists: the O2 baseline is captured once, before any O3 code change. It is "
                         f"never overwritten.")
    A, _D2 = _o2()
    got = collect_o2()
    tests = pytest_g12()
    items = judge_o2(None, got, tests)
    for ok, what, detail in items:
        print(f"{'PASS' if ok else 'FAIL'}  {what}\n      {detail}")
    if not all(ok for ok, _w, _d in items):
        print("!! the code here does not pass G8-G12's baseline-free halves: no O2 baseline written")
        return 1
    _pred, sha = A.O2.load(V1)
    base = {"what": "O2's outputs at the code before any O3 change (research/o3_design.md 1.4 G0'): every (checks, "
                    "report) and every unit's (name, ok, detail) the regression gate compares byte for byte",
            "head": _head(), "predictions": V1.name, "predictions_sha256": sha, "archive": str(O2S),
            "tests": sorted(tests["passed"]), **got}
    text = json.dumps(base, indent=1, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    print(f"captured: {out} ({len(text)} chars, head {base['head'][:8]})")
    return 0


def capture_o3(out: Path, *, baseline: Path = BASELINE, baseline_o2: Path = BASELINE_O2) -> int:
    """G0'': the O3 baseline, once, at the code BEFORE any O4 change (research/o4_design.md 1.4, 9 A0). TWO readings
    first, compared with every temporary root read as :data:`TMP`: one that still differs is named and refused. Then
    G7, G12 and G13 (with the O1 and O2 baselines) and G15-G18's baseline-free halves must pass; the tests those three
    selections collect, and the fake's :data:`FAKE_PINS`, become G21's ``sources``."""
    if out.exists():
        raise SystemExit(f"!! {out} exists: the O3 baseline is captured once, before any O4 code change. It is never "
                         f"overwritten.")
    P, _D3 = _o3()
    first = collect_o3()
    second = collect_o3()
    differ = readings_differ(first, second)
    if differ:
        print(f"!! two readings of O3's outputs differ (a temporary path, a clock or a random in an output): "
              f"{', '.join(differ[:12])}{f' (+{len(differ) - 12} more)' if len(differ) > 12 else ''} -- no O3 "
              f"baseline written")
        return 1
    tests = {"G7": pytest_g7(), "G12": pytest_g12(), "G13": pytest_g13()}
    base1, base2 = json.loads(Path(baseline).read_bytes()), json.loads(Path(baseline_o2).read_bytes())
    items = [g7(base1, tests["G7"]), g12(base2, tests["G12"]), g13(tests["G13"])] + judge_o3(None, first)
    _show_items(items)
    if not all(ok for ok, _w, _d in items):
        print("!! the code here does not pass G7, G12, G13 and G15-G18's baseline-free halves: no O3 baseline written")
        return 1
    names = sorted({pin_of_test(n) for t in tests.values() for n in t["passed"]}) \
        + [f"{FAKE_REL}::{q}" for q in FAKE_PINS]
    sources = source_shas(names)
    gone = [n for n, s in sources.items() if s is None]
    if gone:
        print(f"!! no function for {len(gone)} pin(s): {gone[:6]} -- no O3 baseline written")
        return 1
    _pred, sha = P.O3.load(V1_O3)
    base = {"what": "O3's outputs at the code before any O4 change (research/o4_design.md 1.4 G0''): every (checks, "
                    "report) and every unit's (name, ok, detail) the regression gate compares byte for byte, each "
                    "temporary root read as <tmp>; and G21's sources, the AST sha of every pinned function",
            "head": _head(), "predictions": V1_O3.name, "predictions_sha256": sha, "archive": str(O3S), "tmp": TMP,
            "tests": sorted(tests["G13"]["passed"]), "sources": sources, "sources_python": _py(),
            "sources_from": {"G7": PYTEST_K, "G12": PYTEST_K_O2, "G13": PYTEST_K_O3, "fake": list(FAKE_PINS)},
            **first}
    text = json.dumps(base, indent=1, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    print(f"captured: {out} ({len(text)} chars, head {base['head'][:8]}; {len(sources)} sources pinned)")
    return 0


def capture_o4(out: Path, *, baseline_o3: Path = BASELINE_O3) -> int:
    """G0''': the O4 baseline, once, at the code BEFORE any O5 change (research/o5_design.md 1.4, 9 A0). TWO readings
    first, compared with every temporary root read as :data:`TMP`: one that still differs is named and refused. Then
    G19, G20 and G22-G25's baseline-free halves must pass; the tests G19 collects and the fake's O4 functions
    (:func:`fake_pins_o4`) become the O4 half of G21's ``sources`` -- only names the O3 baseline does not pin
    (:func:`o4_pin_names` refuses one it does)."""
    if out.exists():
        raise SystemExit(f"!! {out} exists: the O4 baseline is captured once, before any O5 code change. It is never "
                         f"overwritten.")
    C4, _D4 = _o4()
    first = collect_o4()
    second = collect_o4()
    differ = readings_differ(first, second)
    if differ:
        print(f"!! two readings of O4's outputs differ (a temporary path, a clock or a random in an output): "
              f"{', '.join(differ[:12])}{f' (+{len(differ) - 12} more)' if len(differ) > 12 else ''} -- no O4 "
              f"baseline written")
        return 1
    tests = pytest_g19()
    items = [g19(tests), g20()] + judge_o4(None, first)
    _show_items(items)
    if not all(ok for ok, _w, _d in items):
        print("!! the code here does not pass G19, G20 and G22-G25's baseline-free halves: no O4 baseline written")
        return 1
    base_o3 = json.loads(Path(baseline_o3).read_bytes())
    fake = fake_pins_o4()
    try:
        names = o4_pin_names(base_o3.get("sources") or {},
                             sorted({pin_of_test(n) for n in tests["passed"]}) + [f"{FAKE_REL}::{q}" for q in fake])
    except ValueError as err:
        print(f"!! {err} -- no O4 baseline written")
        return 1
    sources = source_shas(names)
    gone = [n for n, s in sources.items() if s is None]
    if gone:
        print(f"!! no function for {len(gone)} pin(s): {gone[:6]} -- no O4 baseline written")
        return 1
    _pred, sha = C4.O4.load(V1_O4)
    base = {"what": "O4's outputs at the code before any O5 change (research/o5_design.md 1.4 G0'''): every (checks, "
                    "report) and every unit's (name, ok, detail) the regression gate compares byte for byte, each "
                    "temporary root read as <tmp>; and G21's O4 sources, the AST sha of every pinned function",
            "head": _head(), "predictions": V1_O4.name, "predictions_sha256": sha, "archive": str(O4S), "tmp": TMP,
            "tests": sorted(tests["passed"]), "sources": sources, "sources_python": _py(),
            "sources_from": {"G19": PYTEST_K_O4, "fake": list(fake)}, **first}
    text = json.dumps(base, indent=1, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    print(f"captured: {out} ({len(text)} chars, head {base['head'][:8]}; {len(sources)} sources pinned)")
    return 0


def _show_items(items: list) -> None:
    for ok, what, detail in items:
        print(f"{'PASS' if ok else 'FAIL'}  {what}\n      {detail}", flush=True)


def gate(baseline: Path = BASELINE, baseline_o2: Path = BASELINE_O2, baseline_o3: Path = BASELINE_O3,
         pins: Path = SOURCE_PINS, baseline_o4: Path = BASELINE_O4) -> int:
    absent = [p for p in (baseline, baseline_o2, baseline_o3, baseline_o4, pins) if not Path(p).is_file()]
    if absent:
        print(f"!! no baseline at {', '.join(str(p) for p in absent)}: the gate was not run (capture each first, "
              f"before the change it guards)")
        return 2
    base, base_o2 = json.loads(Path(baseline).read_bytes()), json.loads(Path(baseline_o2).read_bytes())
    base_o3 = json.loads(Path(baseline_o3).read_bytes())
    base_o4 = json.loads(Path(baseline_o4).read_bytes())
    items = judge(base, collect(), pytest_g7())
    _show_items(items)
    items_o2 = judge_o2(base_o2, collect_o2(), pytest_g12())
    _show_items(items_o2)
    items_o3 = [g13(pytest_g13())]                     # O3's battle beat (research/o3_design.md 1.4): no baseline
    _show_items(items_o3)
    items_o3.append(g14())                             # O3's dry run (11.7 #12): no baseline, the count's floor
    _show_items(items_o3[-1:])
    items_o3b = judge_o3(base_o3, collect_o3())        # O3's outputs (research/o4_design.md 1.4): G15-G18
    _show_items(items_o3b)
    items_o4 = [g19(pytest_g19())]                     # O4's machine beats and Chanbara policy (from B3): G19
    _show_items(items_o4)
    items_o4.append(g20())                             # O4's dry run (C2): no baseline, the count's floor
    _show_items(items_o4[-1:])
    items_o4b = judge_o4(base_o4, collect_o4())        # O4's outputs (research/o5_design.md 1.4): G22-G25
    _show_items(items_o4b)
    items_o5 = [g26(pytest_g26())]                     # O5's FakeGame and driver tests (from B3): G26
    _show_items(items_o5)
    items_o5.append(g27())                             # O5's dry run (C2): no baseline, the count's floor
    _show_items(items_o5[-1:])
    try:                                               # the driver's source pins (rev. 2), over both baselines: G21
        items_src = [g21(union_base(base_o3, base_o4), pins)]
    except ValueError as err:
        items_src = [(False, "G21: every pinned source is its pin in force", str(err))]
    _show_items(items_src)
    items += items_o2 + items_o3 + items_o3b + items_o4 + items_o4b + items_o5 + items_src
    n = sum(1 for ok, _w, _d in items if ok)
    print(f"\n{n}/{len(items)} items PASS (baseline heads: O1 {base['head'][:8]}, O2 {base_o2['head'][:8]}, O3 "
          f"{base_o3['head'][:8]}, O4 {base_o4['head'][:8]})")
    return 0 if n == len(items) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--capture", action="store_true", help="G0: write the O1 baseline (refuses an existing one)")
    ap.add_argument("--capture-o2", action="store_true", help="G0': write the O2 baseline (refuses an existing one)")
    ap.add_argument("--capture-o3", action="store_true", help="G0'': write the O3 baseline (refuses an existing one)")
    ap.add_argument("--capture-o4", action="store_true", help="G0''': write the O4 baseline (refuses an existing one)")
    ap.add_argument("--out", type=Path, default=None,
                    help="where --capture / --capture-o2 / --capture-o3 / --capture-o4 writes (default: that "
                         "baseline's committed path)")
    ap.add_argument("--baseline", type=Path, default=BASELINE, help="the O1 baseline the gate reads (default: the "
                                                                    "committed one; another is for testing the gate)")
    ap.add_argument("--baseline-o2", type=Path, default=BASELINE_O2,
                    help="the O2 baseline the gate reads (default: the committed one; another is for testing the gate)")
    ap.add_argument("--baseline-o3", type=Path, default=BASELINE_O3,
                    help="the O3 baseline the gate and --rebaseline-source read (default: the committed one)")
    ap.add_argument("--baseline-o4", type=Path, default=BASELINE_O4,
                    help="the O4 baseline the gate and --rebaseline-source read (default: the committed one)")
    ap.add_argument("--source-pins", type=Path, default=SOURCE_PINS,
                    help="G21's re-baseline rows (default: the committed research/source_pins.json)")
    ap.add_argument("--rebaseline-source", metavar="NAME",
                    help="G21: append ONE re-baseline row for the pinned source NAME (<file>::<qualname>) at its "
                         "current sha -- a name either the O3 or the O4 baseline pins; needs --reason")
    ap.add_argument("--reason", help="with --rebaseline-source: why the pinned source changed (never empty)")
    args = ap.parse_args(argv)
    modes = [m for m in ("capture", "capture_o2", "capture_o3", "capture_o4", "rebaseline_source")
             if getattr(args, m)]
    if len(modes) > 1:
        ap.error(f"one at a time, not {' and '.join(modes)}")
    if args.reason is not None and not args.rebaseline_source:
        ap.error("--reason goes with --rebaseline-source")
    if args.rebaseline_source:
        missing = _missing(o1=False, o2=False, files=(args.baseline_o3, args.baseline_o4, args.source_pins))
    elif args.capture_o4:
        missing = _missing(o1=False, o2=False, o4=True, o4s=True, files=(args.baseline_o3,))
    elif args.capture_o3:
        missing = _missing(o1=False, o2=False, o3s=True, files=(args.baseline, args.baseline_o2))
    elif args.capture or args.capture_o2:
        missing = _missing(o1=not args.capture_o2, o2=not args.capture, o3=False)
    else:
        missing = _missing(o1=True, o2=True, o3=True, o3s=True, o4=True, o4s=True, o5=True,
                           files=(args.baseline_o3, args.baseline_o4, args.source_pins))
    if missing:
        print("!! the gate was not run -- missing: " + ", ".join(missing))
        return 2
    if args.rebaseline_source:
        return rebaseline_source(args.rebaseline_source, args.reason, baseline=args.baseline_o3,
                                 baseline_o4=args.baseline_o4, pins=args.source_pins)
    if args.capture:
        return capture(args.out or BASELINE)
    if args.capture_o2:
        return capture_o2(args.out or BASELINE_O2)
    if args.capture_o3:
        return capture_o3(args.out or BASELINE_O3, baseline=args.baseline, baseline_o2=args.baseline_o2)
    if args.capture_o4:
        return capture_o4(args.out or BASELINE_O4, baseline_o3=args.baseline_o3)
    return gate(args.baseline, args.baseline_o2, args.baseline_o3, args.source_pins, args.baseline_o4)


if __name__ == "__main__":
    sys.exit(main())
