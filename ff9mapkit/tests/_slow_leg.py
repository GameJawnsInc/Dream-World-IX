"""THE ``slow_leg`` MARKER: which tests drive a WHOLE bench leg, story-trace drive or rehearsal against the stand-in in wall
clock time (studies/workflow-perf/GATE-PROFILE.md). They hold most of the co-op domain gate's worker time; everything else
in its list is fast structural tests. A co-op build's intermediate stages run the domain list with ``-m "not slow_leg"``
(plus the patch's own new test files whole); its last stage runs the whole list once.

APPLIED AT COLLECTION (tests/conftest.py), NEVER AS A DECORATOR. test_harness.py's story-trace tests carry G21's source
pins (studies/story-trace/segment_regress.py: the sha256 of ``ast.dump`` of each pinned FunctionDef -- its decorator list
included), so a decorator would re-pin every story-trace test it touched. A registry here moves no test's AST.

Two kinds, one marker:
  * :data:`LEGS` -- the co-op benches' whole-leg runs against the stand-in, by file, each a top-level test function (every
    parametrization of it). A new patch's legs join here when its tests land; ``test_slow_leg_marker.py`` refuses a name
    its file does not define, so a rename cannot silently drop a leg out of the marker.
  * :data:`STORY_DRIVES` -- test_harness.py's story-trace drives and rehearsals on the fake, O4 to O8: a RULE (the name,
    and the ``game`` fixture: the stand-in running), so a new one is marked at birth. The pure tests of the same rungs
    (tmp_path / monkeypatch only) are not legs and stay in every subset.
"""
from __future__ import annotations

import re

MARKER_HELP = ("slow_leg: drives a whole bench leg, story-trace drive or rehearsal against the stand-in in wall-clock time "
               "(tests/_slow_leg.py) -- intermediate gates run -m \"not slow_leg\", the last gate runs everything")

#: file name -> the top-level test functions that run a whole bench leg against the stand-in (every parametrization)
LEGS = {
    # s138-s141: legs I, G (+ its G9 duo leg on a stub duo), S / W / X / N / T, F -- each smoked in a child process
    "test_harness_netsync.py": (
        "test_the_s138_bench_runs_green_on_the_stand_in_and_red_exactly_where_its_checks_say",
        "test_the_s139_leg_runs_green_on_the_stand_in_and_red_exactly_where_its_checks_say",
        "test_the_g9_duo_leg_steps_its_phases_and_reads_the_tap_last_against_a_stub_duo",
        "test_the_s140_legs_run_green_on_the_stand_in_and_calibrate_on_s139",
        "test_each_s140_lever_reds_exactly_its_rows_on_the_stand_in",
        "test_each_s140_row_reds_on_its_fault_on_the_stand_in",
        "test_leg_f_runs_green_on_the_stand_in_and_calibrates_on_s140_s139_and_its_lever",
        "test_every_leg_runs_green_together_on_the_s141_stand_in_and_calibrates_on_s140",
        "test_each_leg_f_row_reds_on_its_fault_on_the_stand_in",
    ),
    # s143: the leader guard's bench
    "test_coop_leader_guard.py": (
        "test_each_guard_fault_turns_exactly_its_rows_red",
        "test_the_bench_calibrates_on_the_s141_stand_in_and_under_the_lever",
        "test_the_faults_cover_every_row_and_the_release_fault_reds_r",
        "test_the_bench_runs_green_on_the_s143_stand_in",
        "test_a_missing_or_wrong_seat_reads_red_never_green",
    ),
    # s144: the stand-in's world-map bench (harness core)
    "test_world_coop_harness.py": (
        "test_each_world_fault_turns_exactly_its_rows_red",
        "test_the_s143_stand_in_reads_exactly_old_predicted_red",
        "test_the_stand_in_bench_is_green_on_s144",
    ),
    # s144: coop_world_wait.py's solo / T2 / duo legs and their faults
    "test_coop_world_wait.py": (
        "test_each_world_fault_turns_exactly_its_solo_rows_red",
        "test_each_world_fault_turns_exactly_its_t2_rows_red",
        "test_each_world_fault_turns_exactly_its_duo_rows_red",
        "test_f3_drives_the_stock_cycle_and_its_close_leaves_the_map_shut_whatever_the_state",
        "test_the_instrument_rows_go_red_on_their_own_wrong_shapes",
        "test_the_bench_closes_a_full_map_that_opened_with_select_never_cancel",
        "test_the_wait_leg_reads_the_tapes_b6_and_calibrates_on_s143",
        "test_the_rejoin_leg_is_green_on_s144_and_calibrates_on_s143",
        "test_d3_keeps_the_bracket_law_under_a_sampler_that_misses_the_arm",
        "test_the_solo_leg_calibrates_on_s143_and_under_the_lever",
        "test_the_duo_leg_is_green_on_s144_and_calibrates_on_s143",
        "test_the_solo_leg_is_green_on_the_s144_stand_in",
        "test_f3_judges_a_world_that_landed_in_the_hud_after_one_press",
        "test_the_world_recorder_tapes_the_host_and_its_b6_is_the_engines",
        "test_the_rejoin_legs_old_order_dials_on_the_field_and_reads_red",
    ),
}

#: test_harness.py's story-trace drives and rehearsals, O4 to O8 (the rungs with a rehearsal), when they take ``game``
STORY_FILE = "test_harness.py"
STORY_DRIVES = re.compile(r"test_o[4-8]_(drive|rehears)")
STORY_FIXTURE = "game"


def is_slow_leg(file_name: str, func_name: str, fixturenames) -> bool:
    """True when the test ``func_name`` (the function's own name, no ``[...]``) of ``file_name`` is a slow leg."""
    if func_name in LEGS.get(file_name, ()):
        return True
    return (file_name == STORY_FILE and STORY_DRIVES.match(func_name) is not None
            and STORY_FIXTURE in tuple(fixturenames or ()))
