"""THE REGRESSION GATE for the shared segment machinery: every change to ``segment_trace``, ``segment_drive``,
``o2_alexandria``, ``o3_prima_vista``, ``o4_castle``, ``o5_hallway``, ``o6_steiner``, ``o7_castle_walk`` or the harness
verbs they drive must leave every O1 output (research/o2_design.md, section 1.6), every O2 output (research/o3_design.md,
section 1.4), every O3 output (research/o4_design.md, section 1.4), every O4 output (research/o5_design.md, section 1.4),
every O5 output (research/o6_design.md, section 1.4), every O6 output (research/o7_design.md, section 1.4) AND every O7
output (research/o8_design.md, section 1.4) byte-identical, O3's battle-beat tests (G13) and O3's dry run (G14) green,
O4's tests (G19) and O4's dry run (G20) green, O5's FakeGame and driver tests (G26) and O5's dry run (G27) green, O6's
FakeGame, driver and analysis tests (G32) and O6's dry run (G33) green, O7's FakeGame, driver and analysis tests (G38) and
O7's dry run (G39) green, O8's FakeGame, driver and analysis tests (G44) and O8's dry run (G45) green, and the O1-O7
driver tests and the fake's beat,
input, story-trace, machine-beat, visit-beat, walk-out, naming, door, level, squeeze, walker and scene functions at their
pinned sources (G21).

    py studies/story-trace/segment_regress.py --capture      # G0, once, BEFORE the O2 refactor: the O1 baseline
    py studies/story-trace/segment_regress.py --capture-o2   # G0', once, BEFORE any O3 code change: the O2 baseline
    py studies/story-trace/segment_regress.py --capture-o3   # G0'', once, BEFORE any O4 code change: the O3 baseline
    py studies/story-trace/segment_regress.py --capture-o4   # G0''', once, BEFORE any O5 code change: the O4 baseline
    py studies/story-trace/segment_regress.py --capture-o5   # G0'''', once, BEFORE any O6 code change: the O5 baseline
    py studies/story-trace/segment_regress.py --capture-o6   # G0''''', once, BEFORE any O7 code change: the O6 baseline
    py studies/story-trace/segment_regress.py --capture-o7   # G0'''''', once, BEFORE any O8 code change: the O7 baseline
    py studies/story-trace/segment_regress.py --rebaseline-source NAME --reason TEXT   # G21: re-pin ONE source
    py studies/story-trace/segment_regress.py                # G1-G45; exit 0 only if every item passes
    py studies/story-trace/segment_regress.py --only G26,G27 # a PARTIAL run (also --segment O5): exit 3 on a pass
    py studies/story-trace/segment_regress.py --pytest-junit DIR/receipt.json   # pytest items from a whole-file run
    py studies/story-trace/segment_regress.py --list         # the items, their segments and kinds

Exit 2 means an archive or a baseline is missing, or a ``--pytest-junit`` receipt is not for this HEAD and working
tree: the gate was not run, which is not a pass. A PARTIAL run (``--only`` / ``--segment``) is NEVER the gate: it
exits 3 when every selected item passes (1 when one fails) and prints NOT THE GATE -- a fix loop's run; the gate is a
full run, exit 0.

THE SPEED PASS (PLAN.md "Build testing"): the pytest items (G7, G12, G13, G19, G26, G32, G38, and G44 from
research/o8_design.md 9 B4) are ONE run of the union of their ``-k`` selections at xdist's ``-n``
(``harness_tests.workers``: 8, ``FF9_TEST_WORKERS``, ``-n``), on a thread while the in-process items run, each item's
slice taken by pytest's own ``--collect-only -k`` and judged as before
(``_selection_bad``, REQUIRED_TESTS, zero skips); its failures go through THE FLAKE PROTOCOL
(``harness_tests.settle``: re-run alone 3x, 3/3 a flake -- named in the item's detail and the summary, never hidden).
``--pytest-junit`` judges them instead from ``harness_tests.py whole``'s receipt, bound to HEAD and the working tree.
A full run took 41 min serial; this way 11m09s, measured with the machine at ~99% CPU from other sessions
(2026-10-04) -- so give a full run more than one 10-minute foreground call.

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
  G21 THE DRIVER'S SOURCE PINS (research/o4_design.md 1.4, rev. 2; research/o5_design.md 1.4; research/o6_design.md
      1.4; research/o7_design.md 1.4; research/o8_design.md 1.4): every name in the UNION of the O3, the O4, the O5, the
      O6 and the O7 baselines' ``sources`` -- each test G7, G12 and G13 collected at the O3 capture and fakegame.py's
      existing beat and input functions; each test G19 collected at the O4 capture and the fake's story sink and machine
      beats (:data:`FAKE_PINS_O4`); each test G26 collected at the O5 capture and the fake's same-value suppression and
      visit beat (:data:`FAKE_PINS_O5`); each test G32 collected at the O6 capture and the fake's region walk-out, naming
      and door (:data:`FAKE_PINS_O6`); each test G38 collected at the O7 capture and the fake's levels, squeeze, walkers,
      objects and scene functions (:data:`FAKE_PINS_O7`, :data:`FAKE_PIN_CLASSES_O7`) -- by its qualified name
      (``<file>::<qualname>``) still exists, and the sha256 of its ``ast.dump(node, include_attributes=False)`` equals its
      baseline's, or, when ``research/source_pins.json`` re-baselines it, that name's LATEST row's ``new``. A name pinned
      by TWO baselines is no union (:func:`union_sources` refuses it; the O4-O7 captures never write one). A row is
      ``{"name", "old", "new", "reason", "head"}``, appended only by ``--rebaseline-source NAME --reason TEXT`` (NAME
      looked up in any of the five baselines): it refuses an empty reason, a name not pinned, an ``old`` that is not the
      pin in force, and a source that is already its pin in force (nothing changed); the commit that changes the source
      carries its row, and the gate replays every row the same way. Comments and whitespace do not count (the AST dump);
      any code edit does, a docstring's included, and a renamed or deleted pinned test FAILS. So an O1-O7 driver test
      adapted to a changed rule -- which G7/G12/G13/G19/G26/G32/G38 alone would pass, since they pin only names -- fails
      here until it is re-baselined by name with its reason.
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
  G0'''' --capture-o5 (research/o6_design.md 1.4, 9 A0): the full ``(checks, report)`` of the archived PROVEN session
      story-o5 read with ``o5_predictions_v1``; of every o5_dryrun session case (its CASES and "predictions-changed");
      every o5_dryrun unit's ``(name, ok, detail)`` (``units(...)`` then ``listed_units(...)``, in run_cases's order);
      ``O5.offline_check(v1)``; the tests G26 collects; the HEAD and v1's sha; and ``sources``, G21's O5 pins -- the AST
      sha of every test G26 collects and of every function :data:`FAKE_PINS_O5` names (and every method of
      :data:`FAKE_PIN_CLASSES_O5`), only names neither the O3 nor the O4 baseline already pins (a name pinned in either is
      refused, :func:`o5_pin_names`) -> ``research/o5_regress_baseline.json`` (LF, ``-text``). It refuses to overwrite a
      baseline, and to write one unless G26, G27 and G28-G31's baseline-free halves pass at the code it captures; it
      first takes TWO readings and refuses when they differ, every temporary root read as ``<tmp>`` (O3's rule, G0'').
  G28 ``O5.analyse(story-o5, pred_path=v1)``: the report is the archived ``o5_report.txt`` exactly, and the
      baseline's; the checks are the baseline's; PROVEN with 18 checks, all True.
  G29 the CLI ``o5_hallway.py --analyse story-o5 --predictions v1`` exits 0 and prints that report, run as G23 runs O4's
      (``PYTHONIOENCODING=utf-8``: O5's pages quote U+2500, which ``segment_trace.say`` would escape on a cp1252 console).
  G30 every o5_dryrun session case's ``(checks, report)`` and every unit's ``(name, ok, detail)`` is the baseline's,
      byte for byte (each temporary root read as ``<tmp>``), and ``run_cases(v1)`` still returns 0 printing "N/N cases
      as registered" (144 at the capture), N counted from the replica: its sessions plus its units. The gate replicates
      run_cases's loop step for step, as G24 does O4's.
      G30 IS O5'S VOID-PATH BASELINE: the story-o5 archive holds six covered runs and no VOID, so G28/G29 never take the
      coverage rule's VOID paths, VOID-ASYM's (a)-(d), A-START's (scoped to visit 1), A-NOEND's, the pre-choice guard's
      or the stair walk's landing judge. An edit to any of them is proven O5-neutral by G30's synthetic sessions alone.
  G31 ``O5.offline_check(v1)`` equals the baseline's ``[(ok, what, detail)]``: 6 checks, all PASS (it reads O4's build
      and the install, read-only).
  G32 (research/o6_design.md 1.4, from 9 B3) ``pytest tests/test_harness.py -k "o6_ or fake_naming or fake_door"``
      from ``ff9mapkit/``: every test passed, 0 failed, 0 skipped, 0 errors, and every name in :data:`REQUIRED_TESTS_O6`
      among them -- O6's FakeGame (H17 the naming screen in a visit and the name on the page, H18 the north door's tag 2
      and walk-out, H19 O6's faults), A0b's O5 replay on the hand-stepped fake, the route builder played unattended, and
      the driver's O6 tests on the fake (the naming and its page witness, both landing paths, the misroutes, the real
      hall, which reads the install: a skip there fails the item). No baseline: the list is the floor.
  G33 (research/o6_design.md 1.4, from 9 C2) ``o6_dryrun.run_cases`` on the frozen O6 predictions once they exist,
      else the draft, AND on ``o6_dryrun.as_if_frozen(draft)`` -- the draft with every freeze-time value changed as the
      lead's freeze changes it (the floating row's ``measured``, every budget, ``rehearsals``: the claim critic's #9):
      each returns 0 printing "N/N cases as registered", the same N, at least :data:`O6_DRYRUN_FLOOR`. No baseline: the
      count is the floor.
  G0''''' --capture-o6 (research/o7_design.md 1.4, 9 A0): the full ``(checks, report)`` of the archived PROVEN session
      story-o6 read with ``o6_predictions_v1``; of every o6_dryrun session case (its CASES and "predictions-changed");
      every o6_dryrun unit's ``(name, ok, detail)`` (``units(...)`` then ``listed_units(...)``, in run_cases's order);
      ``O6.offline_check(v1)``; the tests G32 collects; the HEAD and v1's sha; and ``sources``, G21's O6 pins -- the AST
      sha of every test G32 collects and of every function :data:`FAKE_PINS_O6` names (:func:`fake_pins_o6`), only names
      none of the O3, O4 and O5 baselines already pins (a name pinned in any is refused, :func:`o6_pin_names`) ->
      ``research/o6_regress_baseline.json`` (LF, ``-text``). It refuses to overwrite a baseline, and to write one unless
      G32, G33 and G34-G37's baseline-free halves pass at the code it captures; it first takes TWO readings and refuses
      when they differ, every temporary root read as ``<tmp>`` (O3's rule, G0'').
  G34 ``O6.analyse(story-o6, pred_path=v1)``: the report is the archived ``o6_report.txt`` exactly, and the
      baseline's; the checks are the baseline's; PROVEN with 19 checks, all True.
  G35 the CLI ``o6_steiner.py --analyse story-o6 --predictions v1`` exits 0 and prints that report, run as G29 runs O5's
      (``PYTHONIOENCODING=utf-8``: O6's pages quote curly quotes, which ``segment_trace.say`` would escape on a cp1252
      console).
  G36 every o6_dryrun session case's ``(checks, report)`` and every unit's ``(name, ok, detail)`` is the baseline's,
      byte for byte (each temporary root read as ``<tmp>``), and ``run_cases(v1)`` still returns 0 printing "N/N cases
      as registered" (164 at the capture), N counted from the replica: its sessions plus its units. The gate replicates
      run_cases's loop step for step, as G30 does O5's.
      G36 IS O6'S VOID-PATH BASELINE: the story-o6 archive holds six covered runs and no VOID, so G34/G35 never take the
      coverage rule's VOID paths, VOID-ASYM's (a)-(d), A-START's or A-NAMING's, the page witness's V13 or the landing-
      aware trigger's verdicts. An edit to any of them is proven O6-neutral by G36's synthetic sessions alone.
  G37 ``O6.offline_check(v1)`` equals the baseline's ``[(ok, what, detail)]``: 6 checks, all PASS (it reads O4's build
      and the install, read-only).
  G38 (research/o7_design.md 1.4, from 9 B4) ``pytest tests/test_harness.py -k "o7_ or fake_level or fake_monologue or
      fake_patrol"`` from ``ff9mapkit/``: every test passed, 0 failed, 0 skipped, 0 errors, and every name in
      :data:`REQUIRED_TESTS_O7` among them. No baseline: the list is the floor. A member of the union run.
  G39 (research/o7_design.md 1.4, from 9 C2) ``o7_dryrun.run_cases`` on the frozen O7 predictions once they exist, else
      the draft, AND on ``o7_dryrun.as_if_frozen(draft)``: each returns 0 printing "N/N cases as registered", the same N,
      at least the floor C2 prints. No baseline: the count is the floor.
  G0'''''' --capture-o7 (research/o8_design.md 1.4, 9 A0): the full ``(checks, report)`` of the archived PROVEN session
      story-o7 read with ``o7_predictions_v1``; of every o7_dryrun session case (its CASES and "predictions-changed");
      every o7_dryrun unit's ``(name, ok, detail)`` (``units(...)`` then ``listed_units(...)``, in run_cases's order);
      ``O7.offline_check(v1)``; the tests G38 collects; the HEAD and v1's sha; and ``sources``, G21's O7 pins -- the AST
      sha of every test G38 collects and of every function :data:`FAKE_PINS_O7` names and every method of
      :data:`FAKE_PIN_CLASSES_O7` (:func:`fake_pins_o7`), only names none of the O3, O4, O5 and O6 baselines already pins
      (a name pinned in any is refused, :func:`o7_pin_names`) -> ``research/o7_regress_baseline.json`` (LF, ``-text``).
      It refuses to overwrite a baseline, and to write one unless G38, G39 and G40-G43's baseline-free halves pass at the
      code it captures; it first takes TWO readings and refuses when they differ, every temporary root read as ``<tmp>``
      (O3's rule, G0'').
  G40 ``O7.analyse(story-o7, pred_path=v1)``: the report is the archived ``o7_report.txt`` exactly, and the
      baseline's; the checks are the baseline's; PROVEN with 17 checks, all True.
  G41 the CLI ``o7_castle_walk.py --analyse story-o7 --predictions v1`` exits 0 and prints that report, run as G35 runs
      O6's (``PYTHONIOENCODING=utf-8``).
  G42 every o7_dryrun session case's ``(checks, report)`` and every unit's ``(name, ok, detail)`` is the baseline's,
      byte for byte (each temporary root read as ``<tmp>``), and ``run_cases(v1)`` still returns 0 printing "N/N cases
      as registered" (174 at the capture), N counted from the replica: its sessions plus its units. The gate replicates
      run_cases's loop step for step, as G36 does O6's.
      G42 IS O7'S VOID-PATH BASELINE: the story-o7 archive holds six covered runs and no VOID, so G40/G41 never take the
      coverage rule's VOID paths, VOID-ASYM's (a)-(d), A-START's (the error path and the start read) or the walk's,
      landing's and prior basis's V-classes. An edit to any of them is proven O7-neutral by G42's synthetic sessions
      alone.
  G43 ``O7.offline_check(v1)`` equals the baseline's ``[(ok, what, detail)]``: 6 checks, all PASS (it reads O4's build
      and the install, read-only).
  G44 (research/o8_design.md 1.4, from 9 B4) ``pytest tests/test_harness.py -k "o8_ or fake_spiral or fake_knight or
      fake_tower"`` from ``ff9mapkit/``: every test passed, 0 failed, 0 skipped, 0 errors, and every name in
      :data:`REQUIRED_TESTS_O8` among them. No baseline: the list is the floor. A member of the union run.
  G45 (research/o8_design.md 1.4, from 9 C2) ``o8_dryrun.run_cases`` on the frozen O8 predictions once they exist, else
      the draft, AND on ``o8_dryrun.as_if_frozen(draft)``: each returns 0 printing "N/N cases as registered", the same N,
      at least the floor C2 prints. No baseline: the count is the floor.

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
import itertools
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import o1_opening as O                                                     # noqa: E402
import o1_dryrun as D                                                      # noqa: E402
import harness_tests as HT                                                 # noqa: E402 -- the -n runner, no segment

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
    # research/o6_design.md section 9, PART A: the gate extended to O5 (G21 over the union of the O3, O4 and O5
    # baselines' pins), then the shared opt-in changes, each with its step
    "test_segment_regress_o5_pins_join_the_union",                              # A0: G21 over three baselines
    "test_segment_region_walkout_keeps_him_moving_until_the_flip_on_the_fake",  # A1: H16, the walk-out and the gate
    "test_segment_step_of_trigger_to_is_strict",                                # A1: S14, pure
    "test_segment_trigger_to_verdict_classes",                                  # A1: S14's verdict, pure
    "test_segment_trigger_to_lands_after_the_walk_returns_on_the_fake",         # A1: S14 path A, S14b
    "test_segment_trigger_to_lands_before_the_walk_returns_on_the_fake",        # A1: S14 path B
    "test_segment_trigger_to_wrong_landing_is_rule_2s_on_the_fake",             # A1: S14's left, rule 2's V11 / V19
    "test_segment_trigger_to_unseen_loss_is_v13_on_the_fake",                   # A1: S14's V13
    "test_segment_trigger_without_to_keeps_todays_paths_on_the_fake",           # A1: S14 opt-in
    "test_segment_end_run_warps_after_the_naming_screen_on_the_fake",           # A2: S15, the screen first
    "test_segment_end_run_stops_the_session_when_accept_name_fails",            # A2: S15's session-stop marker
    "test_segment_session_stops_cleanly_on_a_stuck_naming_screen_on_the_fake",  # A2: S15 in Segment.run
    "test_segment_reset_blocked_fields_swallow_the_combo_on_the_fake",          # A2: H16b
    "test_segment_end_run_naming_paths_for_the_opening_and_alexandria_on_the_fake",  # A2: S15's intended O1/O2 change
    # research/o6_design.md section 9, PART B: S16, the name on the page (B3)
    "test_segment_naming_of_is_strict",                                         # B3: S16, pure
    "test_segment_naming_on_page_rows_on_the_fake",                             # B3: S16's rows and its judgment
    "test_segment_naming_of_reads_every_frozen_predictions",                    # B3: every frozen registration
    "test_segment_alexandria_naming_keeps_its_rows_on_the_fake",                # B3: S16 opt-in, O2's rule 4 kept
    # the review's fixes (research/o6_design.md 11.7 #7): S14b's handle -- a door that lands in no end is recorded at
    # its new visit, and a second door's row never drops an unread one
    "test_segment_trigger_to_records_its_landing_at_a_new_visit_on_the_fake",
    "test_segment_trigger_to_records_an_unread_walkout_before_a_second_door",
    # the speed pass (PLAN.md "Build testing"): the items selectable, a partial run never the gate, ONE -n run split
    # per item, a receipt reused only for its HEAD and tree, THE FLAKE PROTOCOL -- the registry's test renamed by
    # research/o7_design.md 1.4 (its name says what it pins, not a range)
    "test_segment_regress_registry_holds_every_item_once",
    "test_segment_regress_split_keeps_each_items_semantics",
    "test_segment_regress_pytest_items_run_one_union_and_settle",
    "test_segment_regress_partial_run_is_not_the_gate",
    "test_segment_harness_tests_settle_names_flakes_and_failures",
    "test_segment_harness_tests_receipt_binds_head_tree_and_python",
    "test_segment_harness_tests_tree_id_tracks_untracked_not_ignored",
    # the speed pass's review (eleven findings, each fixed): a run never reads an earlier junit, a skip or an xfail alone
    # is no pass, a receipt bound to its junit's sha256 and a finished run, a raising gate stops its pytest half
    "test_segment_harness_tests_a_run_never_reads_an_earlier_junit",
    "test_segment_harness_tests_alone_a_skip_or_an_xfail_is_not_a_pass",
    "test_segment_harness_tests_stop_all_ends_a_running_child",
    "test_segment_regress_gate_stops_its_pytest_half_when_the_rest_raises",
    # a frozen segment's dry run reads predictions only through its own segment (O7's freeze moved O6's count)
    "test_segment_dryrun_globs_close_at_their_segment",
    # research/o7_design.md section 9, PART A: the gate extended to O6 (G21 over the union of the O3, O4, O5 and O6
    # baselines' pins), then the shared opt-in changes, each with its step
    "test_segment_regress_o6_pins_join_the_union",                              # A0: G21 over four baselines
    "test_segment_step_of_walk_and_its_keys_are_strict",                        # A1: S17-S19's keys, pure
    "test_segment_step_of_reads_every_frozen_table_unchanged",                  # A1: S17-S19 opt-in, every frozen table
    "test_segment_walk_reaches_its_goal_on_the_fake",                           # A1: S17 done, and short is failed
    "test_segment_walk_short_of_its_goal_fails_on_the_fake",                    # A1: S17 failed twice, V7
    "test_segment_walk_interrupted_outside_a_door_on_the_fake",                 # A1: S17 interrupted, the re-run
    "test_segment_walk_loss_in_a_door_is_its_landing_on_the_fake",              # A1: S17's landing judge, door_loss
    "test_segment_walk_leaving_the_field_is_the_drivers_v11_on_the_fake",       # A1: S17's stray, V11 and backing
    "test_segment_route_clearance_plans_the_corridor_only_below_its_width",     # A2: S18 on both planner paths
    "test_segment_route_clearance_absent_keeps_todays_plan",                    # A2: S18 opt-in, today's plan
    "test_segment_route_clearance_plans_the_stair_at_110_not_120",              # A2: S18 on stock 163's stair
    "test_segment_prior_basis_presses_no_probe_on_the_fake",                    # A3: S19 seeds, no probe, judged
    "test_segment_prior_basis_wrong_stops_on_the_first_move_on_the_fake",       # A3: S19's first-move check
    "test_segment_prior_basis_disagreement_is_the_drivers_v13_on_the_fake",     # A3: S19's V13, keyed on the marker
    "test_segment_prior_basis_widens_the_hold_spread",                          # A3: S19's spread, pure
    "test_segment_prior_basis_narrows_after_its_first_move_on_the_fake",        # A3: S19's spread narrowed, 31 fps
    "test_segment_prior_basis_forget_clears_the_seed_on_the_fake",              # A3: forget_basis, begin_scenario
    "test_segment_prior_basis_absent_calibrates_as_today_on_the_fake",          # A3: S19 opt-in, today's record
    # research/o8_design.md section 9, PART A: the gate extended to O7 (G21 over the union of the O3, O4, O5, O6 and O7
    # baselines' pins), then the shared opt-in changes, each with its step
    "test_segment_regress_o7_pins_join_the_union",                              # A0: G21 over five baselines
    "test_segment_step_of_at_y_wait_flag_unstick_and_y_until_are_strict",       # A1: S20/S21/S23's keys, pure
    "test_segment_walk_at_y_judges_the_arrival_height_on_the_fake",             # A1: S20 done, and the wrong level
    "test_segment_walk_waits_for_its_flag_pressing_nothing_on_the_fake",        # A1: S21 done, nothing pressed
    "test_segment_walk_wait_timeout_is_the_games_v8_on_the_fake",               # A1: S21's run-out, V8 game
    "test_segment_walk_wait_unpublished_watch_is_the_drivers_v13_on_the_fake",  # A1: S21's dropped watch, V13
    "test_segment_walk_wait_runs_out_on_both_clocks",                           # A1: S21's two clocks, pure
    "test_segment_walk_wait_field_change_is_the_games_v11_on_the_fake",         # A1: S21's field change, V11 game
    "test_segment_walk_wait_control_loss_is_interrupted_on_the_fake",           # A1: S21's control loss, door_loss
    "test_segment_walk_wait_deadline_is_the_drivers_v13_on_the_fake",           # A1: S21's deadline, V13 driver
    "test_segment_until_ok_y_axis_raises_without_y",                            # A2: S22's until_ok, pure
    "test_segment_trigger_until_y_reads_the_loss_height_from_the_ring_on_the_fake",  # A2: S22's loss_y, its timing
    "test_segment_trigger_until_y_unread_height_is_the_drivers_v13_on_the_fake",     # A2: S22's V13, no TypeError
    "test_segment_trigger_until_without_y_keeps_todays_row_on_the_fake",        # A2: S22 opt-in, today's row
    "test_segment_walk_kw_passes_unstick_only_when_carried",                    # A3: S23's keyword and row, pure
    "test_segment_unstick_false_places_no_blocker_on_a_stall_on_the_fake",      # A3: S23 off the ladder, on the fake
    # research/o8_design.md 11.4, the review's fixes: S21 never opens a window under its floor, and a window that read
    # no live sample past the run's deadline is the budget's V13 (#5)
    "test_segment_walk_wait_short_window_is_the_budget_never_the_channel",
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
    # H14's choice cursor wraps as the engine's navigation does; the recorder counts the catch as the agent publishes it;
    # R-RACE's record reads 127 and 128 by the draft's guard (its presses joined, the margin off the ring)
    "test_o5_drive_choice_taken_under_the_answer_is_the_gone_choice",
    "test_fake_visit_choice_cursor_wraps",
    "test_o5_rehearsal_recorder_counts_the_dialog_section_catch",
    "test_o5_rehearsal_race_reads_the_unguarded_race_on_the_fake",
)

# -- O5 (research/o6_design.md 1.4): the frozen v1 predictions and the PROVEN story-o5 archive
V1_O5 = HERE / "o5_predictions_v1.json"
O5S = Path(r"C:\gd\Dream-World-IX\.harness-runs\20261003-091627-story-o5")
BASELINE_O5 = HERE / "research" / "o5_regress_baseline.json"
O5S_VERDICT = "PROVEN"
O5S_CHECKS = 18
O5_OFFLINE_CHECKS = 6
#: G32 (research/o6_design.md 1.4, from B3): every ``test_o6_*``, ``test_fake_naming_*`` and ``test_fake_door_*`` name,
#: each with the step that adds it -- G32 joined the gate in the commit that added B3's tests.
PYTEST_K_O6 = "o6_ or fake_naming or fake_door"
REQUIRED_TESTS_O6: tuple = (
    # A0b: O5's route replayed by hand on the fake against its golden, captured before any O6 fake edit
    "test_fake_door_keeps_the_hallway_route_identical",
    # B1: H17, the naming screen inside a visit and the name on the page; H18, the north door step; H19, O6's faults
    "test_fake_naming_screen_takes_two_confirms",
    "test_fake_naming_holds_the_script",
    "test_fake_naming_renders_the_name_on_later_pages",
    "test_fake_naming_deaf_screen_defeats_accept_name",
    "test_fake_door_fires_only_past_its_line",
    "test_fake_door_walkout_then_stores_then_field",
    "test_fake_door_walks_out_until_the_flip_without_stop",
    "test_fake_door_entry_order_and_misroute",
    # B2: the O6 route builder, played unattended to 154 (its trace 4.18's pattern)
    "test_fake_door_route_plays_to_154_unattended",
    # B3: the driver's O6 tests on the fake
    "test_o6_drive_names_steiner_and_walks_to_the_north_door_on_the_fake",
    "test_o6_drive_takes_the_landing_before_the_walk_returns",
    "test_o6_drive_takes_the_landing_after_the_walk_returns",
    "test_o6_drive_wrong_door_is_the_drivers_v11",
    "test_o6_drive_misrouted_door_is_rule_2s",
    "test_o6_drive_misrouted_door_to_a_real_field_is_v19",
    "test_o6_drive_loss_unseen_is_v13",
    "test_o6_drive_fork_landing_in_real_154_is_v19",
    "test_o6_drive_typed_name_is_the_drivers_v13",
    "test_o6_drive_unparsed_page_is_skipped",
    "test_o6_drive_stuck_naming_screen_stops_the_run",
    "test_o6_drive_naming_recovery_reaches_the_title_on_the_fake",
    "test_o6_drive_control_in_151_is_v4",
    "test_o6_drive_stop_page_in_the_start_is_v5_driver",
    "test_o6_drive_unregistered_naming_is_v10",
    "test_o6_drive_e15_late_is_covered",
    "test_o6_drive_walks_the_real_hall_on_the_fake",
    # C1: o6_steiner -- the draft from O4's campaign.toml, the freeze's refusals, the route builder against the draft,
    # instanced_at6's compare dispatch, the census's live and inert proofs, the regions, the door's goals, the floating
    # e15 row, O6-NAMING, O6-START-DEPENDENT, A-START and A-NAMING, the preflight's verdicts
    "test_o6_steiner_draft_reads_the_chain_from_campaign",
    "test_o6_steiner_freeze_refuses",
    "test_o6_steiner_route_builder_matches_the_keys",
    "test_o6_steiner_instanced_at_reads_the_compare_dispatch",
    "test_o6_steiner_census_proves_live_and_inert",
    "test_o6_steiner_regions_roles",
    "test_o6_steiner_goals_door",
    "test_o6_steiner_pattern_floats_the_e15_row",
    "test_o6_steiner_naming_check",
    "test_o6_steiner_start_dependent_check",
    "test_o6_steiner_why_void_reads_151s_error_path_as_the_start",
    "test_o6_steiner_preflight_verdicts",
    # C2: the trace summary over the dry run's rendered rows, cut at the end PLACES (O4's lesson)
    "test_o6_steiner_trace_summary_cuts_at_end_places",
    # C3: o6_rehearse -- the stage ids from the chain, R-DOOR's record, the naming stop and S15's recovery, the walk
    # stop mid-walk on the real hall and its fallback after the calibration, the untraced smoke and F pass
    "test_o6_rehearsal_stage_ids_follow_the_chain",
    "test_o6_rehearsal_plumbing_on_the_fake",
    "test_o6_rehearsal_naming_void_stops_at_the_screen_on_the_fake",
    "test_o6_rehearsal_walk_void_stops_mid_walk_on_the_fake",
    "test_o6_rehearsal_walk_void_falls_back_to_the_first_walk_hold",
    "test_o6_rehearsal_smoke_sends_no_storytrace_on_the_fake",
    "test_o6_rehearsal_fpass_runs_untraced_to_the_member_on_the_fake",
    # the review's fixes (research/o6_design.md 11.7): New Game restores the default name on the fake (#2); P-NAME pins
    # the default name's two sources, a stacked CharacterDefaultName line and [Import] Text (#1)
    "test_fake_naming_new_game_restores_the_default_name",
    "test_o6_steiner_p_name_reads_the_default_names_sources",
)
#: G33 (research/o6_design.md 9 C2): o6_dryrun's "N/N cases as registered" must have N at least this, on the draft (or
#: the frozen file) AND on as_if_frozen(draft) -- its 92 session cases and "predictions-changed" (section 8's table), its
#: 22 units, and its listed units (O6-CENSUS and its 7 mutants, O6-REGIONS and its 6, O6-GOALS and its 8, the route pins
#: and route_mes with their 8, O6-BUILD's route pins on a synthetic build and its 3, the draft through O6-KEYS and its 10
#: offline mutants) when G33 joined (163); then the review's unit (research/o6_design.md 11.7 #1): p-name. A case added
#: raises N; one dropped falls under the floor.
O6_DRYRUN_FLOOR = 164

# -- O6 (research/o7_design.md 1.4): the frozen v1 predictions and the PROVEN story-o6 archive
V1_O6 = HERE / "o6_predictions_v1.json"
O6S = Path(r"C:\gd\Dream-World-IX\.harness-runs\20261004-110827-story-o6")
BASELINE_O6 = HERE / "research" / "o6_regress_baseline.json"
O6S_VERDICT = "PROVEN"
O6S_CHECKS = 19
O6_OFFLINE_CHECKS = 6
#: G39 (research/o7_design.md 1.4, from 9 C2): o7_dryrun's "N/N cases as registered" must have N at least this, on the
#: draft (or the frozen file) AND on as_if_frozen(draft) -- its 86 session cases (section 8's table, with the
#: re-registered ones and the cases C2 added) and "predictions-changed", its 28 units, and its 52 listed units
#: (O7-CENSUS and its 5 mutants, O7-REGIONS and its 6, O7-GOALS and its 11, the route pins and route_mes with their 7,
#: O7-BUILD's route pins on a synthetic build and its 2, the draft through O7-KEYS and its 15 offline mutants) when G39
#: joined (167); the review's fixes (research/o7_design.md 11.4, "The review") raised it to 174 -- 2 session cases
#: (byte8-race-armed-one-F, -all-F), 1 unit (monologue-lines) and 4 listed (goals-163-e3-crossing, -holding,
#: keys-scoped-dropped, -extra). A case added raises N; one dropped falls under the floor.
O7_DRYRUN_FLOOR = 174
#: G45 (research/o8_design.md 1.4, from 9 C2): o8_dryrun's "N/N cases as registered" must have N at least this, on the
#: draft (or the frozen file) AND on as_if_frozen(draft) -- its 117 session cases (section 8's table, with the
#: re-registered ones: last-place-harness S only) and "predictions-changed", the story-o3 seam fixture's 9 (o3-seam-F,
#: o3-landing, o3-state-c and their 6 mutants), its 40 units, and its 52 listed units (O8-CENSUS and its 5 mutants,
#: O8-REGIONS and its 4, O8-GOALS and its 10, the route pins and route_mes with their 8, O8-BUILD's pins and raw exit on a
#: synthetic build and its 3, the draft through O8-KEYS and its 16 offline mutants) when G45 joined (219); the review's
#: fixes (research/o8_design.md 11.4, "The review") raised it -- O8-GOALS' goals-164-1-until-loose and
#: goals-165-1-until-loose (#4), goals-knight-start-y and goals-knight-level (#2). A case added raises N; one dropped
#: falls under the floor.
O8_DRYRUN_FLOOR = 223
#: G38 (research/o7_design.md 1.4, from 9 B4): every ``test_o7_*``, ``test_fake_level_*``, ``test_fake_monologue_*`` and
#: ``test_fake_patrol_*`` name, each with the step that adds it -- G38 joined the gate in the commit that added B4's
#: tests.
PYTEST_K_O7 = "o7_ or fake_level or fake_monologue or fake_patrol"
REQUIRED_TESTS_O7: tuple = (
    # A0b: O6's route replayed by hand on the fake against its golden, captured before any O7 fake edit
    "test_fake_level_keeps_the_steiner_route_identical",
    # B1: H20, the levels of a stacked walkmesh (154's balcony over its ground) and the placement's height; H21, the
    # squeeze through 163's stair foot
    "test_fake_level_meshes_hold_the_levels_premises",
    "test_fake_level_places_steiner_on_the_balcony",
    "test_fake_level_never_drops_off_the_balcony_edge",
    "test_fake_level_walks_the_west_flight_down_to_the_ground",
    "test_fake_level_place_height_without_levels_sets_y",
    "test_fake_level_squeeze_passes_the_stair_foot",
    # B2: H22, the door's height terms and a door step's scene (159's forced monologue); H23, the held walker (Dojebon)
    "test_fake_level_door_branches_by_height",
    "test_fake_monologue_fires_once_outside_the_box",
    "test_fake_monologue_store_override_fires_it_again",
    "test_fake_monologue_regrants_in_place",
    "test_fake_patrol_holds_within_its_circle_and_its_latch",
    "test_fake_patrol_released_walks_its_path",
    # B3: the O7 route builder, played unattended to 164 (its trace 4.16's pattern)
    "test_fake_level_route_plays_to_164_unattended",
    # B4: the driver's O7 tests on the fake -- the castle walk to 164 (S and F), the real balcony and the real stair
    # (the squeeze; two snags then the squeeze), and each VOID class O7 can meet
    "test_o7_drive_walks_the_castle_to_164_on_the_fake",
    "test_o7_drive_walks_the_real_balcony_to_the_ground_on_the_fake",
    "test_o7_drive_balcony_cross_lands_in_153_is_the_drivers_v11",
    "test_o7_drive_squeezes_the_real_stair_on_the_fake",
    "test_o7_drive_stair_snags_twice_then_squeezes_on_the_fake",
    "test_o7_drive_second_monologue_is_v7",
    "test_o7_drive_prior_basis_is_the_drivers_v13",
    "test_o7_drive_fork_landing_in_real_158_is_v19",
    "test_o7_drive_wrong_door_e9_is_the_drivers_v11",
    "test_o7_drive_stop_page_in_154_is_v5_driver",
    "test_o7_drive_walk_into_a_door_is_the_drivers_v11",
    # C1: O7 itself -- the draft and its chain, the freeze's refusals, the route builder against the keys, instanced_at7,
    # the census, the regions with the hazard's role, the goals, the closures, the bytes' readers, O7-WALK / -LANDING /
    # -STATE pure, the fallback end, the static watch, the carried values and the olds, the per-run reseed, the start
    # read's A-START and the preflight's verdicts
    "test_o7_castle_draft_reads_the_chain_from_campaign",
    "test_o7_castle_freeze_refuses",
    "test_o7_castle_route_builder_matches_the_keys",
    "test_o7_castle_instanced_at_reads_no_dispatch_and_flag_gates",
    "test_o7_castle_census_classifies_every_site",
    "test_o7_castle_regions_roles_branches_and_hazard",
    "test_o7_castle_goals",
    "test_o7_castle_closures154_follow_their_definitions",
    "test_o7_castle_monologue_test_reads_the_pinned_text",
    "test_o7_castle_walk_check",
    "test_o7_castle_landing_check_crossings",
    "test_o7_castle_state_reads_byte13_from_the_trace",
    "test_o7_castle_fallback_end_is_one_line",
    "test_o7_castle_static_watch_reads_the_patrol_once_per_visit",
    "test_o7_castle_keys_derive_the_carried_and_the_olds",
    "test_o7_castle_start_run_forgets_every_seeded_basis",
    "test_o7_castle_why_void_reads_the_start_byte8",
    "test_o7_castle_preflight_verdicts",
    # C2: the trace summary cut at end PLACES (the dry run's unit; G39 runs the dry run itself)
    "test_o7_castle_trace_summary_cuts_at_end_places",
    # C3: the rehearsals on the fake -- the stage table's ids from the chain, R-FULL's record (every 7.2 section), the
    # two stops (mid-walk, mid-monologue), Dojebon and the rates, every run's first move judged (the reseed), THE LADDER
    # TAP and F5, the smoke and the untraced F pass
    "test_o7_rehearsal_stage_ids_follow_the_chain",
    "test_o7_rehearsal_plumbing_on_the_fake",
    "test_o7_rehearsal_walk_void_stops_mid_walk_on_the_fake",
    "test_o7_rehearsal_walk_void_stops_mid_monologue_on_the_fake",
    "test_o7_rehearsal_records_dojebon_and_the_rates_on_the_fake",
    "test_o7_rehearsal_judges_every_runs_first_move_on_the_fake",
    "test_o7_rehearsal_places_the_ladder_rungs_on_the_fake",
    "test_o7_rehearsal_smoke_sends_no_storytrace_on_the_fake",
    "test_o7_rehearsal_fpass_runs_untraced_to_the_member_on_the_fake",
    # the review's fixes: the hazard's protection pinned on the real mesh (a walk east past Dojebon's circle releases
    # him: the static watch's moved row -- the box's latch holds him from the grant); H24, 159's monologue in its bytes'
    # order (WindowAsync pages, the script held only at WaitWindow)
    "test_o7_drive_real_balcony_walk_east_releases_dojebon_on_the_fake",
    "test_fake_monologue_async_pages_hold_the_script_only_at_waitwindow",
)

# -- O7 (research/o8_design.md 1.4): the frozen v1 predictions and the PROVEN story-o7 archive
V1_O7 = HERE / "o7_predictions_v1.json"
O7S = Path(r"C:\gd\Dream-World-IX\.harness-runs\20261005-060311-story-o7")
BASELINE_O7 = HERE / "research" / "o7_regress_baseline.json"
O7S_VERDICT = "PROVEN"
O7S_CHECKS = 17
O7_OFFLINE_CHECKS = 6
#: G44 (research/o8_design.md 1.4, from 9 B4): every ``test_o8_*``, ``test_fake_spiral_*``, ``test_fake_knight_*`` and
#: ``test_fake_tower_*`` name, each with the step that adds it -- G44 joins the gate in the commit that adds B4's tests.
PYTEST_K_O8 = "o8_ or fake_spiral or fake_knight or fake_tower"
REQUIRED_TESTS_O8: tuple = (
    # A0b: O7's route and its level, squeeze and walker scenes replayed by hand on the fake against their golden,
    # captured before any O8 fake edit
    "test_fake_spiral_keeps_the_castle_route_identical",
    # B1: H26 the per-field clearance, the spirals' meshes, the placement on loop 1 and THE PINCH
    "test_fake_spiral_clearance_per_field_defaults_to_the_global",
    "test_fake_spiral_meshes_hold_the_levels_premises",
    "test_fake_spiral_places_steiner_on_loop_1",
    "test_fake_spiral_pinch_passes_at_slack_12_not_8",
    # B2: H25 the knight walker -- his release by height, his store on the body, the pair band
    "test_fake_knight_waits_for_his_height_then_walks_and_stores",
    "test_fake_knight_store_is_missing_when_the_visit_ends_first",
    "test_fake_knight_holds_no_pair_across_levels",
    # B3: the O8 route builder played unattended, and the skip dialog's No in FMV004
    "test_fake_tower_route_plays_to_55_unattended",
    "test_fake_tower_movie_skip_dialog_resumes_at_no",
    # B4: the driver on the fake -- the segment, the real spirals, the knight's order (fast, slow, a failed first
    # attempt, missing), the seam and V19, the back door, the skip net's two rows, the dead level, the pinch's fallback
    "test_o8_drive_climbs_the_tower_to_real_55_on_the_fake",
    "test_o8_drive_walks_the_real_spirals_on_the_fake",
    "test_o8_drive_knight_fast_or_slow_keeps_the_order_on_the_fake",
    "test_o8_drive_knight_stores_during_a_failed_first_attempt_on_the_fake",
    "test_o8_drive_knight_missing_is_the_games_v8_on_the_fake",
    "test_o8_drive_fork_lands_in_real_55_from_member_166_on_the_fake",
    "test_o8_drive_fork_landing_in_real_166_is_v19_on_the_fake",
    "test_o8_drive_back_door_e3_is_the_drivers_v11_on_the_fake",
    "test_o8_drive_movie_stray_dialog_answered_at_no_on_the_fake",
    "test_o8_drive_movie_skip_dialog_with_an_empty_prompt_answered_at_no_on_the_fake",
    "test_o8_drive_dead_level_door_holds_no_fire_on_the_fake",
    "test_o8_drive_unstick_false_through_the_pinch_on_the_fake",
    # C1: O8 itself -- the draft from the chain, the step vocabulary and its round trip, the freeze, the route builder
    # against the draft, the census's reach proof, the gates through their jumps, the goals by height, the keys'
    # derivations, the raced set, the walk / order / knight / landing / seam / movie checks, the knight watch under the
    # drive, why_void, the reseed, the preflight and O8-BUILD's raw exit
    "test_o8_tower_draft_reads_the_chain_from_campaign",
    "test_o8_tower_draft_steps_round_trip_through_step_of",
    "test_o8_tower_known_step_keys_refuse_an_unknown_key",
    "test_o8_tower_freeze_refuses",
    "test_o8_tower_route_builder_matches_the_keys",
    "test_o8_tower_census_classifies_every_site",
    "test_o8_tower_regions_gates_read_off_the_pins",
    "test_o8_tower_goals_are_height_aware",
    "test_o8_tower_keys_derive_the_carried_scoped_and_reads",
    "test_o8_tower_end_race_derives_int16_2_and_byte_8",
    "test_o8_tower_walk_check",
    "test_o8_tower_order_and_knight_checks",
    "test_o8_tower_landing_and_seam_checks",
    "test_o8_tower_movie_check",
    "test_o8_tower_knight_watch_reads_the_seat_by_place",
    "test_o8_tower_why_void_reads_the_start_the_movie_and_the_knight",
    "test_o8_tower_start_run_forgets_every_seeded_basis",
    "test_o8_tower_preflight_verdicts",
    "test_o8_tower_build_pins_hold_member_166_byte_identical_with_its_raw_field55",
    # C2: the trace summary over the dry run's rows (its cases, units and the story-o3 fixture are G45's)
    "test_o8_tower_trace_summary_cuts_at_end_places",
    # C3: the rehearsals on the fake -- the chain's ids and the nightly window, every 7.2 section, the three stops
    # (the wait, the pinch, mid-movie), the poke and the net's No, the late edge's re-run, THE KNIGHT / PINCH / MOVIE
    # records, the untraced smoke and pass
    "test_o8_rehearsal_stage_ids_follow_the_chain",
    "test_o8_rehearsal_plumbing_on_the_fake",
    "test_o8_rehearsal_void_stops_on_the_wait_on_the_fake",
    "test_o8_rehearsal_void_stops_in_the_pinch_window_on_the_fake",
    "test_o8_rehearsal_void_stops_mid_movie_on_the_fake",
    "test_o8_rehearsal_pokes_the_movie_once_and_the_net_answers_no_on_the_fake",
    "test_o8_rehearsal_fmv_reruns_a_late_edge_v5_on_the_fake",
    "test_o8_rehearsal_records_the_knight_the_pinch_and_the_movie_on_the_fake",
    "test_o8_rehearsal_smoke_sends_no_storytrace_on_the_fake",
    "test_o8_rehearsal_fpass_runs_untraced_to_real_55_on_the_fake",
    # research/o8_design.md 11.4, the review's fixes, each with its finding
    "test_o8_rehearsal_t0_scan_marks_an_evicted_release_unmeasured",            # #1: T0 off an evicting ring
    "test_fake_knight_pairs_at_his_own_level",                                  # #2: H25b, his level on his path
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
#: The fake O5's tests run on beyond the O3 and O4 pins (research/o6_design.md 1.4 G0''''), by qualified name: the sink's
#: same-value suppression (H13: its site rule and its epoch's counts) and the visit beat's strict step reader (H14) -- and
#: every method of :data:`FAKE_PIN_CLASSES_O5` (:func:`fake_pins_o5`) -- so an O6 edit that changes how the fake
#: suppresses a row or plays a visit fails G21 by name.
FAKE_PINS_O5 = ("FakeGame._story_site", "FakeGame._story_counts", "_visit_steps")
#: The fake's visit-beat class (H14-H15, research/o5_design.md 3.2-3.3): every method of it is an O5 pin.
FAKE_PIN_CLASSES_O5 = ("_VisitBeat",)
#: The fake O6's tests run on beyond the O3, O4 and O5 pins (research/o7_design.md 1.4 G0'''''), by qualified name: the
#: functions O6 added or edited -- H16 a region's walk-out and the exit gate, H16b the soft reset's swallowing fields,
#: H17 the naming screen, H18 the door step and its walk-out -- so an O7 edit that changes how the fake walks a door out,
#: names a character or plays a door step fails G21 by name. The four ``_VisitBeat`` methods did not exist at the O5
#: capture (no baseline pins them yet: :func:`o6_pin_names` refuses one that any baseline does). ``_move_to``,
#: ``_step_walkers`` and ``_region_at`` stay unpinned: no segment added them (O7's edits to them are proven neutral by
#: the two replays and the real-floor tests). No class here: O6 added none.
FAKE_PINS_O6 = ("FakeGame._enter_regions", "FakeGame._step_world", "FakeGame._step_exit_now", "FakeGame._exit_open",
                "FakeGame._walkout_of", "FakeGame._step_walkout", "FakeGame._check_soft_reset", "_door_knobs",
                "_VisitBeat._naming", "_VisitBeat._naming_keys", "_VisitBeat._door", "_VisitBeat._walk_out")
#: The fake O7's tests run on beyond the O3-O6 pins (research/o8_design.md 0.2 #1, 1.4 G0''''''), by qualified name: the
#: functions O7 ADDED or CHANGED that no earlier baseline pins -- H20's placement height and the step that walks a level
#: (``_move_to``: the levels, the squeeze), H23's walkers and their published ``moving``, H22's door scene and H24's
#: WaitWindow -- and every method of :data:`FAKE_PIN_CLASSES_O7` (:func:`fake_pins_o7`), so an O8 edit that changes how
#: the fake walks a level, squeezes a pinch, holds a walker or plays a scene fails G21 by name. O7's other edits
#: (``_visit_steps``, ``_door_knobs``, ``_VisitBeat._door/_page/_place/_run``) are already pinned by O5's and O6's
#: baselines and were re-baselined by name; ``FakeGame.__init__`` stays unpinned (every knob edits it, and no baseline
#: ever pinned it), and so do ``_pushed_out`` and ``_region_at`` (no segment added them).
FAKE_PINS_O7 = ("FakeGame.place_height", "FakeGame._move_to", "FakeGame._step_walkers", "FakeGame._objects_doc",
                "_VisitBeat._scene_fires", "_VisitBeat._wait_window")
#: The fake's level class (H20/H21, research/o7_design.md 3.1-3.2): every method of it is an O7 pin.
FAKE_PIN_CLASSES_O7 = ("Levels",)
#: The baselines whose ``sources`` G21 joins, in this order: what :func:`union_sources` calls each.
PIN_BASELINES = ("O3", "O4", "O5", "O6", "O7")
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


#: THE ITEMS, in the order the gate prints them -- the order G1-G33 have always been printed in, then O6's G34-G37
#: (research/o7_design.md 1.4), O7's G38 (9 B4) and G39 (9 C2), O7's outputs G40-G43 (research/o8_design.md 1.4,
#: 9 A0), and O8's G44 (9 B4) and G45 (9 C2), G21 last.
ITEM_ORDER: tuple = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11", "G12", "G13", "G14", "G15",
                     "G16", "G17", "G18", "G19", "G20", "G22", "G23", "G24", "G25", "G26", "G27", "G28", "G29", "G30",
                     "G31", "G32", "G33", "G34", "G35", "G36", "G37", "G38", "G39", "G40", "G41", "G42", "G43", "G44",
                     "G45", "G21")
#: Each segment's items (``--segment``). G21 is no segment's: the driver's pins over the O3-O7 baselines (``--only``).
SEGMENT_ITEMS: dict = {"O1": ("G1", "G2", "G3", "G4", "G5", "G6", "G7"), "O2": ("G8", "G9", "G10", "G11", "G12"),
                       "O3": ("G13", "G14", "G15", "G16", "G17", "G18"),
                       "O4": ("G19", "G20", "G22", "G23", "G24", "G25"),
                       "O5": ("G26", "G27", "G28", "G29", "G30", "G31"),
                       "O6": ("G32", "G33", "G34", "G35", "G36", "G37"),
                       "O7": ("G38", "G39", "G40", "G41", "G42", "G43"),
                       "O8": ("G44", "G45")}
#: The pytest items and their ``-k`` selections: ONE run of their union judges them all (:func:`pytest_items`).
PYTEST_ITEMS: dict = {"G7": PYTEST_K, "G12": PYTEST_K_O2, "G13": PYTEST_K_O3, "G19": PYTEST_K_O4, "G26": PYTEST_K_O5,
                      "G32": PYTEST_K_O6, "G38": PYTEST_K_O7, "G44": PYTEST_K_O8}


def pytest_g7() -> dict:
    """Run G7's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K)


def pytest_selection(k: str, *, n: int | None = None) -> dict:
    """Run one ``-k`` selection of tests/test_harness.py at xdist's ``-n`` (:func:`harness_tests.workers`: 8, or
    ``FF9_TEST_WORKERS``; 0 serial); ``{"rc", "passed": [...], "failed": [...], "skipped": [...], "errors": [...],
    "flakes": []}`` read from its JUnit XML (the names, not a summary line). The captures run this: one run, judged as
    it ran -- no flake is settled for a baseline."""
    got = HT.run(k=k, n=n)
    if "error" in got:
        return {"rc": got["rc"], "passed": [], "failed": [], "skipped": [], "errors": [got["error"]], "flakes": [],
                "tail": got["tail"]}
    return split_selection(list(got["results"]), got["results"], rc=got["rc"], tail=got["tail"])


def split_selection(members, results: dict, *, rc: int, tail: str, flakes=()) -> dict:
    """One item's ``{"rc", "passed", "failed", "skipped", "errors", "flakes", "tail"}`` from a run's ``results`` ({name:
    status}, :func:`harness_tests.read_junit`) over the tests its ``-k`` collects (``members``): a member with no row is
    an error ("not run"); a skip or an xfail is a skip (:func:`_selection_bad` fails either); a failure or error in
    ``flakes`` -- settled by THE FLAKE PROTOCOL, passed alone 3/3 -- counts passed and is named in ``flakes``. ``rc``:
    1 for a failure or error in THIS slice (another item's failure is not this item's), the run's own exit when it is
    neither 0 nor 1 (interrupted, an internal or usage error), else 0."""
    flaky = set(flakes)
    out = {"rc": 0, "passed": [], "failed": [], "skipped": [], "errors": [], "flakes": [], "tail": tail}
    for name in members:
        st = results.get(name)
        if st is None:
            out["errors"].append(f"not run: {name}")
        elif st in ("failed", "error") and name in flaky:
            out["passed"].append(name)
            out["flakes"].append(name)
        elif st == "error":
            out["errors"].append(name)
        elif st == "failed":
            out["failed"].append(name)
        elif st in ("skipped", "xfailed"):
            out["skipped"].append(name)
        else:
            out["passed"].append(name)
    out["rc"] = 1 if out["failed"] or out["errors"] else (rc if rc not in (0, 1) else 0)
    return out


def pytest_items(ids, *, receipt: dict | None = None, n: int | None = None, env=None) -> dict:
    """``{item id: selection}`` for the pytest items ``ids`` (:data:`PYTEST_ITEMS`) from ONE run: the union of their
    ``-k`` selections at ``-n`` (:func:`harness_tests.run`), its failures settled by THE FLAKE PROTOCOL
    (:func:`harness_tests.settle`) -- or, given a ``receipt`` (:func:`harness_tests.load_receipt`, already checked
    against HEAD and the working tree), that whole-file run's junit and its settled flakes, no pytest run at all. Each
    item's members are pytest's own ``--collect-only -k`` (:func:`harness_tests.collect`), so a selection means here
    exactly what it meant run alone. Prints nothing: the gate runs this on a thread."""
    ks = {i: PYTEST_ITEMS[i] for i in ids}
    union = " or ".join(f"({k})" for k in ks.values())
    with ThreadPoolExecutor(len(ks) + 1) as ex:
        run = None if receipt is not None else ex.submit(HT.run, k=union, n=n, env=env)
        members = {i: ex.submit(HT.collect, k, env=env) for i, k in ks.items()}
        members = {i: f.result() for i, f in members.items()}
        got = run.result() if run is not None else None
    if receipt is not None:
        results, rc = HT.read_junit(Path(receipt["junit"])), receipt["rc"]       # 0 or 1: receipt_problems
        tail = f"(judged from the receipt's whole-file run, {receipt['junit']})"
        flakes = {f["name"] for f in receipt.get("flakes") or ()}
    else:
        results, rc, tail = got["results"], got["rc"], got["tail"]
        settled = HT.settle([nm for nm, st in results.items() if st in ("failed", "error")], env=env)
        flakes = {f["name"] for f in settled["flakes"]}
    return {i: split_selection(members[i], results, rc=rc, tail=tail, flakes=flakes) for i in ks}


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


def pytest_g32() -> dict:
    """Run G32's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K_O6)


def g32(got: dict) -> tuple:
    bad = _selection_bad(None, got, REQUIRED_TESTS_O6)
    return (not bad, f'G32: pytest -k "{PYTEST_K_O6}": all passed, 0 failed, 0 skipped; every REQUIRED_TESTS_O6 '
                     f"among them", "; ".join(bad) or f"{len(got['passed'])} passed")


def pytest_g38() -> dict:
    """Run G38's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K_O7)


def g38(got: dict) -> tuple:
    """G38 (research/o7_design.md 1.4, from 9 B4): O7's FakeGame and driver tests -- every one passed, none skipped, and
    every name in :data:`REQUIRED_TESTS_O7` among them. No baseline: the list is the floor."""
    bad = _selection_bad(None, got, REQUIRED_TESTS_O7)
    return (not bad, f'G38: pytest -k "{PYTEST_K_O7}": all passed, 0 failed, 0 skipped; every REQUIRED_TESTS_O7 '
                     f"among them", "; ".join(bad) or f"{len(got['passed'])} passed")


def pytest_g44() -> dict:
    """Run G44's pytest selection (:func:`pytest_selection`)."""
    return pytest_selection(PYTEST_K_O8)


def g44(got: dict) -> tuple:
    """G44 (research/o8_design.md 1.4, from 9 B4): O8's FakeGame and driver tests -- every one passed, none skipped (the
    real-mesh ones read the install: a warned skip fails the item), and every name in :data:`REQUIRED_TESTS_O8` among
    them. No baseline: the list is the floor."""
    bad = _selection_bad(None, got, REQUIRED_TESTS_O8)
    return (not bad, f'G44: pytest -k "{PYTEST_K_O8}": all passed, 0 failed, 0 skipped; every REQUIRED_TESTS_O8 '
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


# ======================================================================== what the O6 code says (G33)
def _o6() -> tuple:
    """``(o6_steiner, o6_dryrun)``: imported here, never at the module's top, as the O2-O5 items import theirs."""
    import o6_steiner as O
    import o6_dryrun as D6
    return O, D6


def o6_run_cases_quietly(*, as_if: bool = False) -> tuple:
    """``(rc, last line, which predictions)``: ``o6_dryrun.run_cases`` on the frozen O6 predictions once they exist, else
    on the draft (its own default) -- or, ``as_if``, on ``o6_dryrun.as_if_frozen(draft)`` written to a temporary file --
    its per-case lines swallowed."""
    O, D6 = _o6()
    buf = io.StringIO()
    if as_if:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "o6_predictions_as_if_frozen.json"
            path.write_bytes((json.dumps(D6.as_if_frozen(O.draft_predictions()), indent=1, sort_keys=True)
                              + "\n").encode("utf-8"))
            with contextlib.redirect_stdout(buf):
                rc = D6.run_cases(path)
        which = "as_if_frozen(the draft)"
    else:
        path = O.PREDICTIONS if O.PREDICTIONS.is_file() else None
        with contextlib.redirect_stdout(buf):
            rc = D6.run_cases(path)
        which = f"the frozen {path.name}" if path is not None else "the draft"
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else ""), which


def g33() -> tuple:
    """G33 (research/o6_design.md 1.4, 9 C2): O6's dry run, every case as registered, at least the floor -- on the frozen
    predictions (else the draft) AND on as_if_frozen(draft), the same N."""
    what = (f"G33: o6_dryrun.run_cases returns 0, every case as registered, at least {O6_DRYRUN_FLOOR}, on the frozen O6 "
            f"predictions once they exist (else the draft) and on as_if_frozen(the draft), the same N")
    bad, seen = [], []
    for as_if in (False, True):
        try:
            rc, last, which = o6_run_cases_quietly(as_if=as_if)
        except Exception as err:                   # noqa: BLE001 -- a dry run that cannot run is a FAIL, said
            bad.append(f"run_cases{' (as if frozen)' if as_if else ''} raised {type(err).__name__}: {str(err)[:300]}")
            continue
        m = re.fullmatch(r"(\d+)/(\d+) cases as registered", last)
        if rc != 0 or m is None or m.group(1) != m.group(2):
            bad.append(f"run_cases on {which} returned {rc}: {last!r}")
        elif int(m.group(2)) < O6_DRYRUN_FLOOR:
            bad.append(f"{last!r} on {which}: under the floor {O6_DRYRUN_FLOOR} -- a case or a unit was dropped")
        seen.append((last, which))
    if len(seen) == 2 and seen[0][0] != seen[1][0]:
        bad.append(f"the two readings differ: {seen[0][0]!r} on {seen[0][1]}, {seen[1][0]!r} on {seen[1][1]}")
    return not bad, what, "; ".join(bad) or "; ".join(f"{last} ({which})" for last, which in seen)


# ======================================================================== what the O7 code says (G39)
def _o7() -> tuple:
    """``(o7_castle_walk, o7_dryrun)``: imported here, never at the module's top, as the O2-O6 items import theirs."""
    import o7_castle_walk as O7m
    import o7_dryrun as D7
    return O7m, D7


def o7_run_cases_quietly(*, as_if: bool = False) -> tuple:
    """``(rc, last line, which predictions)``: ``o7_dryrun.run_cases`` on the frozen O7 predictions once they exist, else
    on the draft (its own default) -- or, ``as_if``, on ``o7_dryrun.as_if_frozen`` of those -- its per-case lines
    swallowed."""
    O7m, D7 = _o7()
    buf = io.StringIO()
    path = O7m.PREDICTIONS if O7m.PREDICTIONS.is_file() else None
    with contextlib.redirect_stdout(buf):
        rc = D7.run_cases(path, as_if=as_if)
    base = f"the frozen {path.name}" if path is not None else "the draft"
    which = f"as_if_frozen({base})" if as_if else base
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else ""), which


def g39() -> tuple:
    """G39 (research/o7_design.md 1.4, 9 C2): O7's dry run, every case as registered, at least the floor -- on the frozen
    predictions (else the draft) AND on as_if_frozen of them, the same N."""
    what = (f"G39: o7_dryrun.run_cases returns 0, every case as registered, at least {O7_DRYRUN_FLOOR}, on the frozen O7 "
            f"predictions once they exist (else the draft) and on as_if_frozen of them, the same N")
    bad, seen = [], []
    for as_if in (False, True):
        try:
            rc, last, which = o7_run_cases_quietly(as_if=as_if)
        except Exception as err:                   # noqa: BLE001 -- a dry run that cannot run is a FAIL, said
            bad.append(f"run_cases{' (as if frozen)' if as_if else ''} raised {type(err).__name__}: {str(err)[:300]}")
            continue
        m = re.fullmatch(r"(\d+)/(\d+) cases as registered", last)
        if rc != 0 or m is None or m.group(1) != m.group(2):
            bad.append(f"run_cases on {which} returned {rc}: {last!r}")
        elif int(m.group(2)) < O7_DRYRUN_FLOOR:
            bad.append(f"{last!r} on {which}: under the floor {O7_DRYRUN_FLOOR} -- a case or a unit was dropped")
        seen.append((last, which))
    if len(seen) == 2 and seen[0][0] != seen[1][0]:
        bad.append(f"the two readings differ: {seen[0][0]!r} on {seen[0][1]}, {seen[1][0]!r} on {seen[1][1]}")
    return not bad, what, "; ".join(bad) or "; ".join(f"{last} ({which})" for last, which in seen)


# ======================================================================== what the O8 code says (G45)
def _o8() -> tuple:
    """``(o8_west_tower, o8_dryrun)``: imported here, never at the module's top, as the O2-O7 items import theirs."""
    import o8_west_tower as O8m
    import o8_dryrun as D8
    return O8m, D8


def o8_run_cases_quietly(*, as_if: bool = False) -> tuple:
    """``(rc, last line, which predictions)``: ``o8_dryrun.run_cases`` on the frozen O8 predictions once they exist, else
    on the draft (its own default) -- or, ``as_if``, on ``o8_dryrun.as_if_frozen`` of those -- its per-case lines
    swallowed."""
    O8m, D8 = _o8()
    buf = io.StringIO()
    path = O8m.PREDICTIONS if O8m.PREDICTIONS.is_file() else None
    with contextlib.redirect_stdout(buf):
        rc = D8.run_cases(path, as_if=as_if)
    base = f"the frozen {path.name}" if path is not None else "the draft"
    which = f"as_if_frozen({base})" if as_if else base
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else ""), which


def g45() -> tuple:
    """G45 (research/o8_design.md 1.4, 9 C2): O8's dry run, every case as registered, at least the floor -- on the frozen
    predictions (else the draft) AND on as_if_frozen of them, the same N. The dry run reads the study's predictions files
    only through ``frozen_through(8)`` (a later freeze cannot move it) and the story-o3 archive (the seam fixture: a
    missing archive FAILS its entries, never skips)."""
    what = (f"G45: o8_dryrun.run_cases returns 0, every case as registered, at least {O8_DRYRUN_FLOOR}, on the frozen O8 "
            f"predictions once they exist (else the draft) and on as_if_frozen of them, the same N")
    bad, seen = [], []
    for as_if in (False, True):
        try:
            rc, last, which = o8_run_cases_quietly(as_if=as_if)
        except Exception as err:                   # noqa: BLE001 -- a dry run that cannot run is a FAIL, said
            bad.append(f"run_cases{' (as if frozen)' if as_if else ''} raised {type(err).__name__}: {str(err)[:300]}")
            continue
        m = re.fullmatch(r"(\d+)/(\d+) cases as registered", last)
        if rc != 0 or m is None or m.group(1) != m.group(2):
            bad.append(f"run_cases on {which} returned {rc}: {last!r}")
        elif int(m.group(2)) < O8_DRYRUN_FLOOR:
            bad.append(f"{last!r} on {which}: under the floor {O8_DRYRUN_FLOOR} -- a case or a unit was dropped")
        seen.append((last, which))
    if len(seen) == 2 and seen[0][0] != seen[1][0]:
        bad.append(f"the two readings differ: {seen[0][0]!r} on {seen[0][1]}, {seen[1][0]!r} on {seen[1][1]}")
    return not bad, what, "; ".join(bad) or "; ".join(f"{last} ({which})" for last, which in seen)


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


# ======================================================================== what the O5 code says (G28-G31)
def o5_analyse_archive() -> dict:
    C5, _D5 = _o5()
    return _pair(*C5.O5.analyse(O5S, pred_path=V1_O5))


def o5_dryrun_outputs(stock) -> tuple:
    """``({case: (checks, report)}, [case names in run order], [[unit, ok, detail], ...])`` -- ``o5_dryrun.run_cases``'s
    own loop over V1_O5, step for step (research/o6_design.md 1.4 G30): the same temporary layout (``pred/``,
    ``sessions/``, ``units/``), the same session directories in the same order (``s0``, ``s1``, ... -- each report's title
    carries its label), the same units in the same order on the same temporary root (``units(...)``'s single units --
    state-history's session is the last one made -- then ``listed_units(...)``: O5-CENSUS, O5-REGIONS, O5-GOALS, the
    route pins, the build pins, the offline mutants). Left out are only run_cases's verdict comparisons and its extra
    ``read_session`` reads of a case's VOID classes and coverage: pure reads that make no directory and leave nothing an
    output reads. Every output is returned with its temporary root read as :data:`TMP` (:func:`untemp`)."""
    from ff9mapkit.content.verbatim import remap_fields
    C5, D5 = _o5()
    out, order, units = {}, [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdir = tmp / "pred"
        pdir.mkdir()
        sdir = tmp / "sessions"
        sdir.mkdir()
        udir = tmp / "units"
        udir.mkdir()
        path = V1_O5                                      # run_cases's prepare(V1_O5, pdir) is V1_O5 itself
        pred, _sha = C5.O5.load(path)
        members = D5.members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, *_want in D5.CASES:
            d = D5.make_session(sdir, path, fn(copy.deepcopy(pred)), scripts)
            out[name] = _pair(*C5.O5.analyse(d, stock=stock))
            order.append(name)
        copy_path = pdir / "pred_copy.json"               # O5-FROZEN: the predictions changed after the session
        copy_path.write_bytes(path.read_bytes())
        d = D5.make_session(sdir, copy_path, D5.six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        out["predictions-changed"] = _pair(*C5.O5.analyse(d, stock=stock))
        order.append("predictions-changed")
        for name, fn in D5.units(pred, stock, scripts, sdir, path, udir):
            ok, detail = fn()
            units.append([name, ok, detail])
        for name, ok, detail in D5.listed_units(pred, stock, udir):
            units.append([name, ok, detail])
    return untemp(out, [tmp]), order, untemp(units, [tmp])


def o5_offline() -> list:
    C5, _D5 = _o5()
    pred, _sha = C5.O5.load(V1_O5)
    return [list(c) for c in C5.O5.offline_check(pred)]


def o5_run_cases_v1() -> tuple:
    """``(rc, last line)`` of ``o5_dryrun.run_cases(V1_O5)``, its per-case lines swallowed (G30)."""
    _C5, D5 = _o5()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D5.run_cases(V1_O5)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else "")


def o5_cli_analyse() -> tuple:
    """G29: the CLI as G23 runs O4's -- ``PYTHONIOENCODING=utf-8``, so O5's pages (U+2500 among them) print as they are,
    never as :func:`segment_trace.say`'s escapes on a cp1252 console."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "o5_hallway.py"), "--analyse", str(O5S), "--predictions",
                        str(V1_O5)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout, p.stderr


def _verdict_o5(pair: dict) -> str:
    _C5, D5 = _o5()
    return D5.verdict([tuple(c) for c in pair["checks"]])


def g28(base: dict, got: dict) -> tuple:
    bad = []
    archived = (O5S / "o5_report.txt").read_text(encoding="utf-8")
    if got["report"] != archived:
        bad.append(f"the report is not the archived o5_report.txt: {_first_diff(got['report'], archived)}")
    if base is not None:
        bad += _same(got, base["o5s"], "story-o5")
    checks = got["checks"]
    v = _verdict_o5(got)
    if v != O5S_VERDICT or len(checks) != O5S_CHECKS or not all(c[0] is True for c in checks):
        bad.append(f"verdict {v!r} over {len(checks)} checks, want {O5S_VERDICT} over {O5S_CHECKS}, all True")
    return (not bad, f"G28: analyse(story-o5, v1) is the archived report exactly, PROVEN with {O5S_CHECKS} checks "
                     f"all True", "; ".join(bad) or f"{len(got['report'].splitlines())} report lines, {v}")


def g29(report: str) -> tuple:
    rc, out, err = o5_cli_analyse()
    bad = []
    if rc != 0:
        bad.append(f"exit {rc}: {err[-300:]}")
    if out != report + "\n":
        bad.append(f"stdout is not the report plus print's newline: {_first_diff(out, report + chr(10))}")
    return (not bad, "G29: the CLI o5_hallway.py --analyse story-o5 --predictions v1 exits 0 and prints that report",
            "; ".join(bad) or "exit 0")


def g30(base: dict, got: dict, order: list, units: list) -> tuple:
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
    rc, last = o5_run_cases_v1()
    n = len(order) + len(units)
    if rc != 0 or last != f"{n}/{n} cases as registered":
        bad.append(f"run_cases(v1) returned {rc}: {last!r}, want {n}/{n}")
    return (not bad, "G30: every o5_dryrun case's (checks, report) and unit's (name, ok, detail) is the baseline's, "
                     "byte for byte; run_cases(v1) 0", "; ".join(bad[:4]) or f"{len(order)} sessions, {len(units)} "
                                                                             f"units; {last}")


def g31(base: dict, got: list) -> tuple:
    bad = [] if base is None or got == base["offline"] else [f"{got} != {base['offline']}"[:500]]
    if len(got) != O5_OFFLINE_CHECKS or not all(c[0] is True for c in got):
        bad.append(f"offline_check(v1) reads {[c[0] for c in got]}, want {O5_OFFLINE_CHECKS} x True")
    return (not bad, f"G31: O5's offline_check(v1) is the baseline's [(ok, what, detail)], {O5_OFFLINE_CHECKS} PASS",
            "; ".join(bad) or "; ".join(f"{c[1].split(':')[0]}: {c[2][:90]}" for c in got))


# ======================================================================== what the O6 code says (G34-G37)
def o6_analyse_archive() -> dict:
    O6m, _D6 = _o6()
    return _pair(*O6m.O6.analyse(O6S, pred_path=V1_O6))


def o6_dryrun_outputs(stock) -> tuple:
    """``({case: (checks, report)}, [case names in run order], [[unit, ok, detail], ...])`` -- ``o6_dryrun.run_cases``'s
    own loop over V1_O6, step for step (research/o7_design.md 1.4 G36): the same temporary layout (``pred/``,
    ``sessions/``, ``units/``), the same session directories in the same order (``s0``, ``s1``, ... -- each report's title
    carries its label), each case's session made with its own ``stopped`` (O6's CASES carry it), the same units in the
    same order on the same temporary root (``units(...)``'s single units -- state-history's session is the last one made
    -- then ``listed_units(...)``: O6-CENSUS, O6-REGIONS, O6-GOALS, the route pins, the build pins, the offline mutants).
    Left out are only run_cases's verdict comparisons and its extra ``read_session`` reads of a case's VOID classes and
    coverage: pure reads that make no directory and leave nothing an output reads. Every output is returned with its
    temporary root read as :data:`TMP` (:func:`untemp`)."""
    from ff9mapkit.content.verbatim import remap_fields
    O6m, D6 = _o6()
    out, order, units = {}, [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdir = tmp / "pred"
        pdir.mkdir()
        sdir = tmp / "sessions"
        sdir.mkdir()
        udir = tmp / "units"
        udir.mkdir()
        path = V1_O6                                      # run_cases's prepare(V1_O6, pdir) is V1_O6 itself
        pred, _sha = O6m.O6.load(path)
        members = D6.members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, *_want, stopped in D6.CASES:
            d = D6.make_session(sdir, path, fn(copy.deepcopy(pred)), scripts, stopped=stopped)
            out[name] = _pair(*O6m.O6.analyse(d, stock=stock))
            order.append(name)
        copy_path = pdir / "pred_copy.json"               # O6-FROZEN: the predictions changed after the session
        copy_path.write_bytes(path.read_bytes())
        d = D6.make_session(sdir, copy_path, D6.six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        out["predictions-changed"] = _pair(*O6m.O6.analyse(d, stock=stock))
        order.append("predictions-changed")
        for name, fn in D6.units(pred, stock, scripts, sdir, path, udir):
            ok, detail = fn()
            units.append([name, ok, detail])
        for name, ok, detail in D6.listed_units(pred, stock, udir):
            units.append([name, ok, detail])
    return untemp(out, [tmp]), order, untemp(units, [tmp])


def o6_offline() -> list:
    O6m, _D6 = _o6()
    pred, _sha = O6m.O6.load(V1_O6)
    return [list(c) for c in O6m.O6.offline_check(pred)]


def o6_run_cases_v1() -> tuple:
    """``(rc, last line)`` of ``o6_dryrun.run_cases(V1_O6)``, its per-case lines swallowed (G36)."""
    _O6m, D6 = _o6()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D6.run_cases(V1_O6)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else "")


def o6_cli_analyse() -> tuple:
    """G35: the CLI as G29 runs O5's -- ``PYTHONIOENCODING=utf-8``, so O6's pages (curly quotes among them) print as
    they are, never as :func:`segment_trace.say`'s escapes on a cp1252 console."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "o6_steiner.py"), "--analyse", str(O6S), "--predictions",
                        str(V1_O6)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout, p.stderr


def _verdict_o6(pair: dict) -> str:
    _O6m, D6 = _o6()
    return D6.verdict([tuple(c) for c in pair["checks"]])


def g34(base: dict, got: dict) -> tuple:
    bad = []
    archived = (O6S / "o6_report.txt").read_text(encoding="utf-8")
    if got["report"] != archived:
        bad.append(f"the report is not the archived o6_report.txt: {_first_diff(got['report'], archived)}")
    if base is not None:
        bad += _same(got, base["o6s"], "story-o6")
    checks = got["checks"]
    v = _verdict_o6(got)
    if v != O6S_VERDICT or len(checks) != O6S_CHECKS or not all(c[0] is True for c in checks):
        bad.append(f"verdict {v!r} over {len(checks)} checks, want {O6S_VERDICT} over {O6S_CHECKS}, all True")
    return (not bad, f"G34: analyse(story-o6, v1) is the archived report exactly, PROVEN with {O6S_CHECKS} checks "
                     f"all True", "; ".join(bad) or f"{len(got['report'].splitlines())} report lines, {v}")


def g35(report: str) -> tuple:
    rc, out, err = o6_cli_analyse()
    bad = []
    if rc != 0:
        bad.append(f"exit {rc}: {err[-300:]}")
    if out != report + "\n":
        bad.append(f"stdout is not the report plus print's newline: {_first_diff(out, report + chr(10))}")
    return (not bad, "G35: the CLI o6_steiner.py --analyse story-o6 --predictions v1 exits 0 and prints that report",
            "; ".join(bad) or "exit 0")


def g36(base: dict, got: dict, order: list, units: list) -> tuple:
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
    rc, last = o6_run_cases_v1()
    n = len(order) + len(units)
    if rc != 0 or last != f"{n}/{n} cases as registered":
        bad.append(f"run_cases(v1) returned {rc}: {last!r}, want {n}/{n}")
    return (not bad, "G36: every o6_dryrun case's (checks, report) and unit's (name, ok, detail) is the baseline's, "
                     "byte for byte; run_cases(v1) 0", "; ".join(bad[:4]) or f"{len(order)} sessions, {len(units)} "
                                                                             f"units; {last}")


def g37(base: dict, got: list) -> tuple:
    bad = [] if base is None or got == base["offline"] else [f"{got} != {base['offline']}"[:500]]
    if len(got) != O6_OFFLINE_CHECKS or not all(c[0] is True for c in got):
        bad.append(f"offline_check(v1) reads {[c[0] for c in got]}, want {O6_OFFLINE_CHECKS} x True")
    return (not bad, f"G37: O6's offline_check(v1) is the baseline's [(ok, what, detail)], {O6_OFFLINE_CHECKS} PASS",
            "; ".join(bad) or "; ".join(f"{c[1].split(':')[0]}: {c[2][:90]}" for c in got))


# ======================================================================== what the O7 code says (G40-G43)
def o7_analyse_archive() -> dict:
    O7m, _D7 = _o7()
    return _pair(*O7m.O7.analyse(O7S, pred_path=V1_O7))


def o7_dryrun_outputs(stock) -> tuple:
    """``({case: (checks, report)}, [case names in run order], [[unit, ok, detail], ...])`` -- ``o7_dryrun.run_cases``'s
    own loop over V1_O7, step for step (research/o8_design.md 1.4 G42): the same temporary layout (``pred/``,
    ``sessions/``, ``units/``), the same session directories in the same order (``s0``, ``s1``, ... -- each report's title
    carries its label), each case's session made with its own ``stopped`` (O7's CASES carry it, last), the same units in
    the same order on the same temporary root (``units(...)``'s single units -- state-history's session is the last one
    made -- then ``listed_units(...)``: O7-CENSUS, O7-REGIONS, O7-GOALS, the route pins, the build pins, the offline
    mutants). Left out are only run_cases's verdict comparisons and its extra ``read_session`` reads of a case's VOID
    classes and coverage: pure reads that make no directory and leave nothing an output reads. Every output is returned
    with its temporary root read as :data:`TMP` (:func:`untemp`)."""
    from ff9mapkit.content.verbatim import remap_fields
    O7m, D7 = _o7()
    out, order, units = {}, [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdir = tmp / "pred"
        pdir.mkdir()
        sdir = tmp / "sessions"
        sdir.mkdir()
        udir = tmp / "units"
        udir.mkdir()
        path = V1_O7                                      # run_cases's prepare(V1_O7, pdir) is V1_O7 itself
        pred, _sha = O7m.O7.load(path)
        members = D7.members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, *_want, stopped in D7.CASES:
            d = D7.make_session(sdir, path, fn(copy.deepcopy(pred)), scripts, stopped=stopped)
            out[name] = _pair(*O7m.O7.analyse(d, stock=stock))
            order.append(name)
        copy_path = pdir / "pred_copy.json"               # O7-FROZEN: the predictions changed after the session
        copy_path.write_bytes(path.read_bytes())
        d = D7.make_session(sdir, copy_path, D7.six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        out["predictions-changed"] = _pair(*O7m.O7.analyse(d, stock=stock))
        order.append("predictions-changed")
        for name, fn in D7.units(pred, stock, scripts, sdir, path, udir):
            ok, detail = fn()
            units.append([name, ok, detail])
        for name, ok, detail in D7.listed_units(pred, stock, udir):
            units.append([name, ok, detail])
    return untemp(out, [tmp]), order, untemp(units, [tmp])


def o7_offline() -> list:
    O7m, _D7 = _o7()
    pred, _sha = O7m.O7.load(V1_O7)
    return [list(c) for c in O7m.O7.offline_check(pred)]


def o7_run_cases_v1() -> tuple:
    """``(rc, last line)`` of ``o7_dryrun.run_cases(V1_O7)``, its per-case lines swallowed (G42)."""
    _O7m, D7 = _o7()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D7.run_cases(V1_O7)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return rc, (lines[-1] if lines else "")


def o7_cli_analyse() -> tuple:
    """G41: the CLI as G35 runs O6's -- ``PYTHONIOENCODING=utf-8``, so O7's pages (curly quotes among them) print as
    they are, never as :func:`segment_trace.say`'s escapes on a cp1252 console."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "o7_castle_walk.py"), "--analyse", str(O7S), "--predictions",
                        str(V1_O7)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout, p.stderr


def _verdict_o7(pair: dict) -> str:
    _O7m, D7 = _o7()
    return D7.verdict([tuple(c) for c in pair["checks"]])


def g40(base: dict, got: dict) -> tuple:
    bad = []
    archived = (O7S / "o7_report.txt").read_text(encoding="utf-8")
    if got["report"] != archived:
        bad.append(f"the report is not the archived o7_report.txt: {_first_diff(got['report'], archived)}")
    if base is not None:
        bad += _same(got, base["o7s"], "story-o7")
    checks = got["checks"]
    v = _verdict_o7(got)
    if v != O7S_VERDICT or len(checks) != O7S_CHECKS or not all(c[0] is True for c in checks):
        bad.append(f"verdict {v!r} over {len(checks)} checks, want {O7S_VERDICT} over {O7S_CHECKS}, all True")
    return (not bad, f"G40: analyse(story-o7, v1) is the archived report exactly, PROVEN with {O7S_CHECKS} checks "
                     f"all True", "; ".join(bad) or f"{len(got['report'].splitlines())} report lines, {v}")


def g41(report: str) -> tuple:
    rc, out, err = o7_cli_analyse()
    bad = []
    if rc != 0:
        bad.append(f"exit {rc}: {err[-300:]}")
    if out != report + "\n":
        bad.append(f"stdout is not the report plus print's newline: {_first_diff(out, report + chr(10))}")
    return (not bad, "G41: the CLI o7_castle_walk.py --analyse story-o7 --predictions v1 exits 0 and prints that "
                     "report", "; ".join(bad) or "exit 0")


def g42(base: dict, got: dict, order: list, units: list) -> tuple:
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
    rc, last = o7_run_cases_v1()
    n = len(order) + len(units)
    if rc != 0 or last != f"{n}/{n} cases as registered":
        bad.append(f"run_cases(v1) returned {rc}: {last!r}, want {n}/{n}")
    return (not bad, "G42: every o7_dryrun case's (checks, report) and unit's (name, ok, detail) is the baseline's, "
                     "byte for byte; run_cases(v1) 0", "; ".join(bad[:4]) or f"{len(order)} sessions, {len(units)} "
                                                                             f"units; {last}")


def g43(base: dict, got: list) -> tuple:
    bad = [] if base is None or got == base["offline"] else [f"{got} != {base['offline']}"[:500]]
    if len(got) != O7_OFFLINE_CHECKS or not all(c[0] is True for c in got):
        bad.append(f"offline_check(v1) reads {[c[0] for c in got]}, want {O7_OFFLINE_CHECKS} x True")
    return (not bad, f"G43: O7's offline_check(v1) is the baseline's [(ok, what, detail)], {O7_OFFLINE_CHECKS} PASS",
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


def fake_pins_o5(source: str | None = None) -> list:
    """The fake's O5 pins (research/o6_design.md 1.4 G0''''): :data:`FAKE_PINS_O5`, then every method of each class of
    :data:`FAKE_PIN_CLASSES_O5` in the order fakegame.py defines it -- each ``<qualname>`` (``Class.method``), read from
    ``source`` (default: fakegame.py as it stands). A class with no method found raises: it was renamed."""
    source = (ROOT / FAKE_REL).read_text(encoding="utf-8") if source is None else source
    names = list(FAKE_PINS_O5)
    funcs = list(functions_of(source))
    for cls in FAKE_PIN_CLASSES_O5:
        methods = [q for q in funcs if q.startswith(cls + ".")]
        if not methods:
            raise ValueError(f"fakegame.py defines no method of {cls}: the O5 pins name a class it no longer has")
        names += [q for q in methods if q not in names]
    return names


def o5_pin_names(o3_sources: dict, o4_sources: dict, names) -> list:
    """The O5 baseline's pins (G0''''): ``names`` -- the tests G26 collects and the fake's O5 functions -- in order, each
    once. ValueError naming every name the O3 or the O4 baseline's ``sources`` already pin: a name pinned by two
    baselines would carry two pins in force, so the capture refuses it rather than choose one."""
    out = list(dict.fromkeys(names))
    clauses = [f"{len(both)} name(s) pinned in both the {label} and the O5 baselines: {both[:6]}"
               for label, pinned in (("O3", o3_sources), ("O4", o4_sources))
               for both in [[n for n in out if n in pinned]] if both]
    if clauses:
        raise ValueError("; ".join(clauses) + " -- the O5 baseline pins only names neither the O3 nor the O4 "
                                              "baseline pins")
    return out


def fake_pins_o6(source: str | None = None) -> list:
    """The fake's O6 pins (research/o7_design.md 1.4 G0'''''): :data:`FAKE_PINS_O6`, each a ``<qualname>`` read from
    ``source`` (default: fakegame.py as it stands), in that order. O6 added no class, so there are no classes to expand:
    a name the source defines no function for raises (it was renamed or deleted -- a pin never follows a rename)."""
    source = (ROOT / FAKE_REL).read_text(encoding="utf-8") if source is None else source
    funcs = functions_of(source)
    gone = [q for q in FAKE_PINS_O6 if q not in funcs]
    if gone:
        raise ValueError(f"fakegame.py defines no function {gone}: the O6 pins name what it no longer has")
    return list(FAKE_PINS_O6)


def o6_pin_names(o3_sources: dict, o4_sources: dict, o5_sources: dict, names) -> list:
    """The O6 baseline's pins (G0'''''): ``names`` -- the tests G32 collects and the fake's O6 functions -- in order, each
    once. ValueError naming every name the O3, the O4 or the O5 baseline's ``sources`` already pin: a name pinned by two
    baselines would carry two pins in force, so the capture refuses it rather than choose one."""
    out = list(dict.fromkeys(names))
    clauses = [f"{len(both)} name(s) pinned in both the {label} and the O6 baselines: {both[:6]}"
               for label, pinned in (("O3", o3_sources), ("O4", o4_sources), ("O5", o5_sources))
               for both in [[n for n in out if n in pinned]] if both]
    if clauses:
        raise ValueError("; ".join(clauses) + " -- the O6 baseline pins only names none of the O3, O4 and O5 "
                                              "baselines pins")
    return out


def fake_pins_o7(source: str | None = None) -> list:
    """The fake's O7 pins (research/o8_design.md 0.2 #1, 1.4 G0''''''): :data:`FAKE_PINS_O7`, then every method of each
    class of :data:`FAKE_PIN_CLASSES_O7` in the order fakegame.py defines it -- each a ``<qualname>`` (``Class.method``)
    read from ``source`` (default: fakegame.py as it stands). A name the source defines no function for raises, naming
    every such name, and so does a class with no method found: it was renamed or deleted -- a pin never follows a
    rename."""
    source = (ROOT / FAKE_REL).read_text(encoding="utf-8") if source is None else source
    funcs = list(functions_of(source))
    gone = [q for q in FAKE_PINS_O7 if q not in funcs]
    gone += [cls for cls in FAKE_PIN_CLASSES_O7 if not any(q.startswith(cls + ".") for q in funcs)]
    if gone:
        raise ValueError(f"fakegame.py defines no function {gone}: the O7 pins name what it no longer has")
    names = list(FAKE_PINS_O7)
    for cls in FAKE_PIN_CLASSES_O7:
        names += [q for q in funcs if q.startswith(cls + ".") and q not in names]
    return names


def o7_pin_names(o3_sources: dict, o4_sources: dict, o5_sources: dict, o6_sources: dict, names) -> list:
    """The O7 baseline's pins (G0''''''): ``names`` -- the tests G38 collects and the fake's O7 functions -- in order,
    each once. ValueError naming every name the O3, the O4, the O5 or the O6 baseline's ``sources`` already pin: a name
    pinned by two baselines would carry two pins in force, so the capture refuses it rather than choose one."""
    out = list(dict.fromkeys(names))
    clauses = [f"{len(both)} name(s) pinned in both the {label} and the O7 baselines: {both[:6]}"
               for label, pinned in (("O3", o3_sources), ("O4", o4_sources), ("O5", o5_sources), ("O6", o6_sources))
               for both in [[n for n in out if n in pinned]] if both]
    if clauses:
        raise ValueError("; ".join(clauses) + " -- the O7 baseline pins only names none of the O3, O4, O5 and O6 "
                                              "baselines pins")
    return out


def union_sources(*sources) -> dict:
    """G21's pins (research/o5_design.md 1.4; research/o6_design.md 1.4; research/o7_design.md 1.4;
    research/o8_design.md 1.4): the baselines' ``sources`` -- the O3 baseline's, the O4 baseline's, the O5 baseline's,
    the O6 baseline's and the O7 baseline's, in that order (:data:`PIN_BASELINES`; a call with fewer joins the first
    ones, exactly as before) -- one dict. ValueError naming every name pinned in TWO of them, pair by pair: no union then
    -- which pin is in force would be a choice; and on a call with more sources than :data:`PIN_BASELINES` names."""
    if len(sources) > len(PIN_BASELINES):
        raise ValueError(f"G21 joins at most the {', '.join(PIN_BASELINES)} baselines, not {len(sources)}")
    clauses = []
    for i, j in itertools.combinations(range(len(sources)), 2):
        both = sorted(set(sources[i]) & set(sources[j]))
        if both:
            clauses.append(f"{len(both)} name(s) pinned in both the {PIN_BASELINES[i]} and the {PIN_BASELINES[j]} "
                           f"baselines: {both[:6]}")
    if clauses:
        raise ValueError("; ".join(clauses) + " -- a name has one pin in force")
    out: dict = {}
    for s in sources:
        out.update(s)
    return out


def union_base(*bases) -> dict:
    """The baseline G21 judges (:func:`g21`): ``{"sources": the union, "sources_python"}`` over the O3, O4, O5, O6 and
    O7 baselines given (in that order) -- the Python every pin was taken under, or each named (``3.14 / 3.15``) when
    they differ. ValueError as :func:`union_sources`."""
    sources = union_sources(*[b.get("sources") or {} for b in bases])
    pys = [b.get("sources_python") for b in bases if b.get("sources_python") is not None]
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
        raise ValueError(f"{name!r} is not pinned: the baselines' sources hold {len(sources)} names "
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
    """G21 over ``base``'s ``sources`` -- the gate passes :func:`union_base` of the O3, O4, O5, O6 and O7 baselines; a
    test passes its own (research/o5_design.md 1.4; research/o6_design.md 1.4; research/o7_design.md 1.4;
    research/o8_design.md 1.4)."""
    what = ("G21: every pinned source -- the O1-O3 tests G7, G12 and G13 collected at the O3 capture, the fake's beat "
            "and input functions; the O4 tests G19 collected at the O4 capture, the fake's story sink and machine "
            "beats; the O5 tests G26 collected at the O5 capture, the fake's same-value suppression and visit beat; "
            "the O6 tests G32 collected at the O6 capture, the fake's region walk-out, naming and door; the O7 tests "
            "G38 collected at the O7 capture, the fake's levels, squeeze, walkers and scenes -- is its pin in force "
            "(its baseline's sha, or its latest re-baseline row's)")
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
                      baseline_o5: Path | None = None, baseline_o6: Path | None = None,
                      baseline_o7: Path | None = None, pins: Path = SOURCE_PINS, files=None) -> int:
    """``--rebaseline-source NAME --reason TEXT``: append ONE row to the pins file -- ``name`` at its current sha, its
    ``old`` the pin in force -- after the file's own rows replay clean. ``name`` is looked up in any baseline given (the
    union of the O3, O4, O5, O6 and O7 baselines' ``sources``, :func:`union_sources`; research/o5_design.md 1.4,
    research/o6_design.md 1.4, research/o7_design.md 1.4, research/o8_design.md 1.4): the CLI passes the committed O4,
    O5, O6 and O7 baselines (``--baseline-o4``, ``--baseline-o5``, ``--baseline-o6``, ``--baseline-o7``); a call that
    names none of them (``baseline_o4`` to ``baseline_o7`` None) reads the O3 baseline's ``sources`` alone, as O4's call
    did -- a test's temporary baseline never meets a committed one. Every refusal of :func:`pin_row` (and a name pinned
    in two baselines) is an exit 1 with nothing written. ``files``: :func:`source_shas`' seam."""
    base = json.loads(Path(baseline).read_bytes())
    base4 = {} if baseline_o4 is None else json.loads(Path(baseline_o4).read_bytes())
    base5 = {} if baseline_o5 is None else json.loads(Path(baseline_o5).read_bytes())
    base6 = {} if baseline_o6 is None else json.loads(Path(baseline_o6).read_bytes())
    base7 = {} if baseline_o7 is None else json.loads(Path(baseline_o7).read_bytes())
    try:
        sources = union_sources(base.get("sources") or {}, base4.get("sources") or {}, base5.get("sources") or {},
                                base6.get("sources") or {}, base7.get("sources") or {})
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
             o4s: bool = False, o5: bool = False, o5s: bool = False, o6: bool = False, o6s: bool = False,
             o7: bool = False, o7s: bool = False, o8: bool = False, files=()) -> list:
    """The inputs the items read that are not here (each makes the gate "not run", exit 2). O3's dry run (G14) reads
    the frozen O3 predictions, or -- until they exist -- the draft, which reads O1's chain build (machine-local).
    ``o3s``: G15-G18's -- the story-o3 archive's session and report, and the frozen v1; ``o4``: O4's dry run's (G20)
    -- the frozen O4 predictions, or until they exist the O4 chain's campaign.toml the draft reads (machine-local);
    ``o4s``: G22-G25's -- the story-o4 archive's session and report, and the frozen v1 (research/o5_design.md 1.4);
    ``o5``: O5's dry run's (G27) -- the frozen O5 predictions, or until they exist the campaign.toml of O4's chain the
    draft reads (machine-local); ``o5s``: G28-G31's -- the story-o5 archive's session and report, and the frozen v1
    (research/o6_design.md 1.4); ``o6``: O6's dry run's (G33, from research/o6_design.md 9 C2) -- the frozen O6
    predictions, or until they exist the campaign.toml of O4's chain the draft reads (read by path); ``o6s``: G34-G37's
    -- the story-o6 archive's session and report, and the frozen v1 (research/o7_design.md 1.4); ``o7``: O7's dry
    run's (G39, from research/o7_design.md 9 C2) -- the frozen O7 predictions, or until they exist the campaign.toml of
    O4's chain the draft reads (read by path); ``o7s``: G40-G43's -- the story-o7 archive's session and report, and the
    frozen v1 (research/o8_design.md 1.4); ``o8``: O8's dry run's (G45, from research/o8_design.md 9 C2) -- the frozen
    O8 predictions, or until they exist the campaign.toml of O4's chain the draft reads (read by path: no mode passes it
    before C2); ``files``: whatever else the mode reads (the O3, O4, O5, O6 and O7 baselines and the pins file for the
    gate, the O1 and O2 baselines for --capture-o3, the O3 baseline for --capture-o4, the O3 and O4 baselines for
    --capture-o5, the O3, O4 and O5 baselines for --capture-o6, the O3, O4, O5 and O6 baselines for --capture-o7)."""
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
    if o5s:
        C5, _D5 = _o5()
        need += [V1_O5, O5S / C5.SESSION_FILE, O5S / "o5_report.txt"]
    if o6:
        C4, _D4 = _o4()
        p6 = HERE / "o6_predictions_v1.json"
        need.append(p6 if p6.is_file() else C4.CHAIN_DIR / "campaign.toml")
    if o6s:
        O6m, _D6 = _o6()
        need += [V1_O6, O6S / O6m.SESSION_FILE, O6S / "o6_report.txt"]
    if o7:
        C4, _D4 = _o4()
        p7 = HERE / "o7_predictions_v1.json"
        need.append(p7 if p7.is_file() else C4.CHAIN_DIR / "campaign.toml")
    if o7s:
        O7m, _D7 = _o7()
        need += [V1_O7, O7S / O7m.SESSION_FILE, O7S / "o7_report.txt"]
    if o8:
        C4, _D4 = _o4()
        p8 = HERE / "o8_predictions_v1.json"
        need.append(p8 if p8.is_file() else C4.CHAIN_DIR / "campaign.toml")
    need += [Path(p) for p in files]
    return [str(p) for p in need if not p.is_file()]


def collect() -> dict:
    """Everything the O1 code says, once: the gate's reading (and, at G0, the baseline's)."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order = dryrun_outputs(stock)
    return {"o1e": analyse_archive(O1E), "o1d": analyse_archive(O1D), "dryrun": dry, "dryrun_order": order,
            "noise_mutant": noise_mutant(stock), "offline": offline()}


def judge_o1(base: dict | None, got: dict) -> list:
    """G1-G6: O1's in-process items."""
    return [g1(base, got["o1e"]), g2(got["o1e"]["report"]), g3(base, got["dryrun"], got["dryrun_order"]),
            g4(base, got["offline"]), g5(base, got["o1d"]), g6(base, got["noise_mutant"])]


def judge(base: dict | None, got: dict, tests: dict) -> list:
    return judge_o1(base, got) + [g7(base, tests)]


def collect_o2() -> dict:
    """Everything the O2 code says, once: the gate's reading (and, at G0', the O2 baseline's)."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order, units = o2_dryrun_outputs(stock)
    return {"o2s": o2_analyse_archive(), "dryrun": dry, "dryrun_order": order, "units": units,
            "offline": o2_offline()}


def judge_o2_core(base: dict | None, got: dict) -> list:
    """G8-G11: O2's in-process items."""
    return [g8(base, got["o2s"]), g9(got["o2s"]["report"]), g10(base, got["dryrun"], got["dryrun_order"],
                                                                 got["units"]),
            g11(base, got["offline"])]


def judge_o2(base: dict | None, got: dict, tests: dict) -> list:
    return judge_o2_core(base, got) + [g12(base, tests)]


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


def collect_o5() -> dict:
    """Everything the O5 code says, once: the gate's reading (and, at G0'''', the O5 baseline's), every temporary root
    read as :data:`TMP`."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order, units = o5_dryrun_outputs(stock)
    return {"o5s": o5_analyse_archive(), "dryrun": dry, "dryrun_order": order, "units": units,
            "offline": o5_offline()}


def judge_o5(base: dict | None, got: dict) -> list:
    return [g28(base, got["o5s"]), g29(got["o5s"]["report"]),
            g30(base, got["dryrun"], got["dryrun_order"], got["units"]), g31(base, got["offline"])]


def collect_o6() -> dict:
    """Everything the O6 code says, once: the gate's reading (and, at G0''''', the O6 baseline's), every temporary root
    read as :data:`TMP`."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order, units = o6_dryrun_outputs(stock)
    return {"o6s": o6_analyse_archive(), "dryrun": dry, "dryrun_order": order, "units": units,
            "offline": o6_offline()}


def judge_o6(base: dict | None, got: dict) -> list:
    return [g34(base, got["o6s"]), g35(got["o6s"]["report"]),
            g36(base, got["dryrun"], got["dryrun_order"], got["units"]), g37(base, got["offline"])]


def collect_o7() -> dict:
    """Everything the O7 code says, once: the gate's reading (and, at G0'''''', the O7 baseline's), every temporary root
    read as :data:`TMP`."""
    from ff9mapkit import storytrace as T
    stock = T.stock_script_source()
    dry, order, units = o7_dryrun_outputs(stock)
    return {"o7s": o7_analyse_archive(), "dryrun": dry, "dryrun_order": order, "units": units,
            "offline": o7_offline()}


def judge_o7(base: dict | None, got: dict) -> list:
    return [g40(base, got["o7s"]), g41(got["o7s"]["report"]),
            g42(base, got["dryrun"], got["dryrun_order"], got["units"]), g43(base, got["offline"])]


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


def capture_o5(out: Path, *, baseline_o3: Path = BASELINE_O3, baseline_o4: Path = BASELINE_O4) -> int:
    """G0'''': the O5 baseline, once, at the code BEFORE any O6 change (research/o6_design.md 1.4, 9 A0). TWO readings
    first, compared with every temporary root read as :data:`TMP`: one that still differs is named and refused. Then
    G26, G27 and G28-G31's baseline-free halves must pass; the tests G26 collects and the fake's O5 functions
    (:func:`fake_pins_o5`) become the O5 third of G21's ``sources`` -- only names neither the O3 nor the O4 baseline
    pins (:func:`o5_pin_names` refuses one either does)."""
    if out.exists():
        raise SystemExit(f"!! {out} exists: the O5 baseline is captured once, before any O6 code change. It is never "
                         f"overwritten.")
    C5, _D5 = _o5()
    first = collect_o5()
    second = collect_o5()
    differ = readings_differ(first, second)
    if differ:
        print(f"!! two readings of O5's outputs differ (a temporary path, a clock or a random in an output): "
              f"{', '.join(differ[:12])}{f' (+{len(differ) - 12} more)' if len(differ) > 12 else ''} -- no O5 "
              f"baseline written")
        return 1
    tests = pytest_g26()
    items = [g26(tests), g27()] + judge_o5(None, first)
    _show_items(items)
    if not all(ok for ok, _w, _d in items):
        print("!! the code here does not pass G26, G27 and G28-G31's baseline-free halves: no O5 baseline written")
        return 1
    base_o3 = json.loads(Path(baseline_o3).read_bytes())
    base_o4 = json.loads(Path(baseline_o4).read_bytes())
    fake = fake_pins_o5()
    try:
        names = o5_pin_names(base_o3.get("sources") or {}, base_o4.get("sources") or {},
                             sorted({pin_of_test(n) for n in tests["passed"]}) + [f"{FAKE_REL}::{q}" for q in fake])
    except ValueError as err:
        print(f"!! {err} -- no O5 baseline written")
        return 1
    sources = source_shas(names)
    gone = [n for n, s in sources.items() if s is None]
    if gone:
        print(f"!! no function for {len(gone)} pin(s): {gone[:6]} -- no O5 baseline written")
        return 1
    _pred, sha = C5.O5.load(V1_O5)
    base = {"what": "O5's outputs at the code before any O6 change (research/o6_design.md 1.4 G0''''): every (checks, "
                    "report) and every unit's (name, ok, detail) the regression gate compares byte for byte, each "
                    "temporary root read as <tmp>; and G21's O5 sources, the AST sha of every pinned function",
            "head": _head(), "predictions": V1_O5.name, "predictions_sha256": sha, "archive": str(O5S), "tmp": TMP,
            "tests": sorted(tests["passed"]), "sources": sources, "sources_python": _py(),
            "sources_from": {"G26": PYTEST_K_O5, "fake": list(fake)}, **first}
    text = json.dumps(base, indent=1, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    print(f"captured: {out} ({len(text)} chars, head {base['head'][:8]}; {len(sources)} sources pinned)")
    return 0


def capture_o6(out: Path, *, baseline_o3: Path = BASELINE_O3, baseline_o4: Path = BASELINE_O4,
               baseline_o5: Path = BASELINE_O5) -> int:
    """G0''''': the O6 baseline, once, at the code BEFORE any O7 change (research/o7_design.md 1.4, 9 A0). TWO readings
    first, compared with every temporary root read as :data:`TMP`: one that still differs is named and refused. Then
    G32, G33 and G34-G37's baseline-free halves must pass; the tests G32 collects and the fake's O6 functions
    (:func:`fake_pins_o6`) become the O6 quarter of G21's ``sources`` -- only names none of the O3, O4 and O5 baselines
    pins (:func:`o6_pin_names` refuses one any does)."""
    if out.exists():
        raise SystemExit(f"!! {out} exists: the O6 baseline is captured once, before any O7 code change. It is never "
                         f"overwritten.")
    O6m, _D6 = _o6()
    first = collect_o6()
    second = collect_o6()
    differ = readings_differ(first, second)
    if differ:
        print(f"!! two readings of O6's outputs differ (a temporary path, a clock or a random in an output): "
              f"{', '.join(differ[:12])}{f' (+{len(differ) - 12} more)' if len(differ) > 12 else ''} -- no O6 "
              f"baseline written")
        return 1
    tests = pytest_g32()
    items = [g32(tests), g33()] + judge_o6(None, first)
    _show_items(items)
    if not all(ok for ok, _w, _d in items):
        print("!! the code here does not pass G32, G33 and G34-G37's baseline-free halves: no O6 baseline written")
        return 1
    base_o3 = json.loads(Path(baseline_o3).read_bytes())
    base_o4 = json.loads(Path(baseline_o4).read_bytes())
    base_o5 = json.loads(Path(baseline_o5).read_bytes())
    try:
        fake = fake_pins_o6()
        names = o6_pin_names(base_o3.get("sources") or {}, base_o4.get("sources") or {}, base_o5.get("sources") or {},
                             sorted({pin_of_test(n) for n in tests["passed"]}) + [f"{FAKE_REL}::{q}" for q in fake])
    except ValueError as err:
        print(f"!! {err} -- no O6 baseline written")
        return 1
    sources = source_shas(names)
    gone = [n for n, s in sources.items() if s is None]
    if gone:
        print(f"!! no function for {len(gone)} pin(s): {gone[:6]} -- no O6 baseline written")
        return 1
    _pred, sha = O6m.O6.load(V1_O6)
    base = {"what": "O6's outputs at the code before any O7 change (research/o7_design.md 1.4 G0'''''): every (checks, "
                    "report) and every unit's (name, ok, detail) the regression gate compares byte for byte, each "
                    "temporary root read as <tmp>; and G21's O6 sources, the AST sha of every pinned function",
            "head": _head(), "predictions": V1_O6.name, "predictions_sha256": sha, "archive": str(O6S), "tmp": TMP,
            "tests": sorted(tests["passed"]), "sources": sources, "sources_python": _py(),
            "sources_from": {"G32": PYTEST_K_O6, "fake": list(fake)}, **first}
    text = json.dumps(base, indent=1, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    print(f"captured: {out} ({len(text)} chars, head {base['head'][:8]}; {len(sources)} sources pinned)")
    return 0


def capture_o7(out: Path, *, baseline_o3: Path = BASELINE_O3, baseline_o4: Path = BASELINE_O4,
               baseline_o5: Path = BASELINE_O5, baseline_o6: Path = BASELINE_O6) -> int:
    """G0'''''': the O7 baseline, once, at the code BEFORE any O8 change (research/o8_design.md 1.4, 9 A0). TWO readings
    first, compared with every temporary root read as :data:`TMP`: one that still differs is named and refused. Then
    G38, G39 and G40-G43's baseline-free halves must pass; the tests G38 collects and the fake's O7 functions
    (:func:`fake_pins_o7`) become the O7 fifth of G21's ``sources`` -- only names none of the O3, O4, O5 and O6 baselines
    pins (:func:`o7_pin_names` refuses one any does)."""
    if out.exists():
        raise SystemExit(f"!! {out} exists: the O7 baseline is captured once, before any O8 code change. It is never "
                         f"overwritten.")
    O7m, _D7 = _o7()
    first = collect_o7()
    second = collect_o7()
    differ = readings_differ(first, second)
    if differ:
        print(f"!! two readings of O7's outputs differ (a temporary path, a clock or a random in an output): "
              f"{', '.join(differ[:12])}{f' (+{len(differ) - 12} more)' if len(differ) > 12 else ''} -- no O7 "
              f"baseline written")
        return 1
    tests = pytest_g38()
    items = [g38(tests), g39()] + judge_o7(None, first)
    _show_items(items)
    if not all(ok for ok, _w, _d in items):
        print("!! the code here does not pass G38, G39 and G40-G43's baseline-free halves: no O7 baseline written")
        return 1
    base_o3 = json.loads(Path(baseline_o3).read_bytes())
    base_o4 = json.loads(Path(baseline_o4).read_bytes())
    base_o5 = json.loads(Path(baseline_o5).read_bytes())
    base_o6 = json.loads(Path(baseline_o6).read_bytes())
    try:
        fake = fake_pins_o7()
        names = o7_pin_names(base_o3.get("sources") or {}, base_o4.get("sources") or {}, base_o5.get("sources") or {},
                             base_o6.get("sources") or {},
                             sorted({pin_of_test(n) for n in tests["passed"]}) + [f"{FAKE_REL}::{q}" for q in fake])
    except ValueError as err:
        print(f"!! {err} -- no O7 baseline written")
        return 1
    sources = source_shas(names)
    gone = [n for n, s in sources.items() if s is None]
    if gone:
        print(f"!! no function for {len(gone)} pin(s): {gone[:6]} -- no O7 baseline written")
        return 1
    _pred, sha = O7m.O7.load(V1_O7)
    base = {"what": "O7's outputs at the code before any O8 change (research/o8_design.md 1.4 G0''''''): every (checks, "
                    "report) and every unit's (name, ok, detail) the regression gate compares byte for byte, each "
                    "temporary root read as <tmp>; and G21's O7 sources, the AST sha of every pinned function",
            "head": _head(), "predictions": V1_O7.name, "predictions_sha256": sha, "archive": str(O7S), "tmp": TMP,
            "tests": sorted(tests["passed"]), "sources": sources, "sources_python": _py(),
            "sources_from": {"G38": PYTEST_K_O7, "fake": list(fake)}, **first}
    text = json.dumps(base, indent=1, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    print(f"captured: {out} ({len(text)} chars, head {base['head'][:8]}; {len(sources)} sources pinned)")
    return 0


def _show_items(items: list) -> None:
    for ok, what, detail in items:
        print(f"{'PASS' if ok else 'FAIL'}  {what}\n      {detail}", flush=True)


def _item_id(item: tuple) -> str:
    return item[1].split(":", 1)[0]


def _with_flakes(item: tuple, got: dict) -> tuple:
    """A pytest item's verdict with its settled flakes named in its detail -- never hidden."""
    if not got.get("flakes"):
        return item
    ok, what, detail = item
    return ok, what, f"{detail}; FLAKES (failed at -n, passed alone 3/3): {got['flakes']}"


def select_items(only=(), segments=()) -> set:
    """The ids a run judges: every item (``set(ITEM_ORDER)``) when neither is given, else ``only`` and the items of
    ``segments``. Raises ValueError naming an id or a segment there is none of."""
    if not only and not segments:
        return set(ITEM_ORDER)
    bad = [i for i in only if i not in ITEM_ORDER] + [s for s in segments if s not in SEGMENT_ITEMS]
    if bad:
        top = max(int(i[1:]) for i in ITEM_ORDER)
        raise ValueError(f"no item or segment {', '.join(bad)} (items: G1-G{top}; segments: "
                         f"{', '.join(SEGMENT_ITEMS)})")
    return set(only) | {i for s in segments for i in SEGMENT_ITEMS[s]}


def gate(baseline: Path = BASELINE, baseline_o2: Path = BASELINE_O2, baseline_o3: Path = BASELINE_O3,
         pins: Path = SOURCE_PINS, baseline_o4: Path = BASELINE_O4, baseline_o5: Path = BASELINE_O5,
         baseline_o6: Path = BASELINE_O6, baseline_o7: Path = BASELINE_O7, *, only=None, receipt: dict | None = None,
         n: int | None = None) -> int:
    """The gate: every item of ``only`` (default all, :func:`select_items`), printed in :data:`ITEM_ORDER`. The pytest
    items are ONE run of their union on a thread (:func:`pytest_items`; a ``receipt`` instead judges them from a
    whole-file run already done at this HEAD and tree) while the in-process items run here. A run of every item ends
    ``N/N items PASS`` and exits 0 only if each passes; a PARTIAL run (``only``) is never the gate: it exits 3 when
    every selected item passes, 1 when one fails, and says NOT THE GATE."""
    absent = [p for p in (baseline, baseline_o2, baseline_o3, baseline_o4, baseline_o5, baseline_o6, baseline_o7,
                          pins) if not Path(p).is_file()]
    if absent:
        print(f"!! no baseline at {', '.join(str(p) for p in absent)}: the gate was not run (capture each first, "
              f"before the change it guards)")
        return 2
    sel = set(ITEM_ORDER) if only is None else set(only)
    base, base_o2 = json.loads(Path(baseline).read_bytes()), json.loads(Path(baseline_o2).read_bytes())
    base_o3 = json.loads(Path(baseline_o3).read_bytes())
    base_o4 = json.loads(Path(baseline_o4).read_bytes())
    base_o5 = json.loads(Path(baseline_o5).read_bytes())
    base_o6 = json.loads(Path(baseline_o6).read_bytes())
    base_o7 = json.loads(Path(baseline_o7).read_bytes())
    py_ids = [i for i in ITEM_ORDER if i in sel and i in PYTEST_ITEMS]
    HT.reset_stop()
    ex = ThreadPoolExecutor(1)
    tests_f = ex.submit(pytest_items, py_ids, receipt=receipt, n=n, env=dict(os.environ)) if py_ids else None
    got: dict = {}
    t0 = time.time()

    def take(items: list, label: str) -> None:
        for item in items:
            if _item_id(item) in sel:
                got[_item_id(item)] = item
        print(f".. {label} read ({time.time() - t0:.0f} s)", flush=True)

    def want(*ids) -> bool:
        return any(i in sel for i in ids)

    try:
        if want(*SEGMENT_ITEMS["O1"][:6]):
            take(judge_o1(base, collect()), "O1's outputs (G1-G6)")
        if want(*SEGMENT_ITEMS["O2"][:4]):
            take(judge_o2_core(base_o2, collect_o2()), "O2's outputs (G8-G11)")
        if want("G14"):
            take([g14()], "O3's dry run (G14)")                  # no baseline, the count's floor (11.7 #12)
        if want("G15", "G16", "G17", "G18"):
            take(judge_o3(base_o3, collect_o3()), "O3's outputs (G15-G18)")
        if want("G20"):
            take([g20()], "O4's dry run (G20)")                  # no baseline, the count's floor (C2)
        if want("G22", "G23", "G24", "G25"):
            take(judge_o4(base_o4, collect_o4()), "O4's outputs (G22-G25)")
        if want("G27"):
            take([g27()], "O5's dry run (G27)")
        if want("G28", "G29", "G30", "G31"):
            take(judge_o5(base_o5, collect_o5()), "O5's outputs (G28-G31)")
        if want("G33"):
            take([g33()], "O6's dry run and as if frozen (G33)")
        if want("G34", "G35", "G36", "G37"):
            take(judge_o6(base_o6, collect_o6()), "O6's outputs (G34-G37)")
        if want("G39"):
            take([g39()], "O7's dry run and as if frozen (G39)")    # no baseline, the count's floor (C2)
        if want("G40", "G41", "G42", "G43"):
            take(judge_o7(base_o7, collect_o7()), "O7's outputs (G40-G43)")
        if want("G45"):
            take([g45()], "O8's dry run and as if frozen (G45)")    # no baseline, the count's floor (C2)
        if want("G21"):                                          # the driver's source pins over five baselines
            try:
                take([g21(union_base(base_o3, base_o4, base_o5, base_o6, base_o7), pins)], "the source pins (G21)")
            except ValueError as err:
                take([(False, "G21: every pinned source is its pin in force", str(err))], "the source pins (G21)")
        if tests_f is not None:
            try:
                tests = tests_f.result()
            except Exception as err:                         # noqa: BLE001 -- a run that cannot run fails each item
                tests = {i: {"rc": -1, "passed": [], "failed": [], "skipped": [], "flakes": [], "tail": "",
                             "errors": [f"the pytest run raised {type(err).__name__}: {str(err)[:400]}"]}
                         for i in py_ids}
            judges = {"G7": lambda t: g7(base, t), "G12": lambda t: g12(base_o2, t), "G13": g13, "G19": g19,
                      "G26": g26, "G32": g32, "G38": g38, "G44": g44}
            take([_with_flakes(judges[i](tests[i]), tests[i]) for i in py_ids],
                 f"the pytest items ({', '.join(py_ids)}), one run")
    except BaseException:
        HT.stop_all()                                    # the pytest half ends with it: never waited on, never orphaned
        raise
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    items = [got[i] for i in ITEM_ORDER if i in sel]
    _show_items(items)
    k = sum(1 for ok, _w, _d in items if ok)
    flaky = sorted({f for i in py_ids for f in (tests[i].get("flakes") or ())}) if py_ids else []
    if flaky:
        print(f"\nflakes, each passed alone 3/3 (name them in the commit): {', '.join(flaky)}")
    if sel != set(ITEM_ORDER):
        print(f"\nPARTIAL: {k}/{len(items)} selected items PASS ({len(ITEM_ORDER) - len(items)} of {len(ITEM_ORDER)} "
              f"not run) -- NOT THE GATE")
        return 3 if k == len(items) else 1
    print(f"\n{k}/{len(items)} items PASS (baseline heads: O1 {base['head'][:8]}, O2 {base_o2['head'][:8]}, O3 "
          f"{base_o3['head'][:8]}, O4 {base_o4['head'][:8]}, O5 {base_o5['head'][:8]}, O6 {base_o6['head'][:8]}, O7 "
          f"{base_o7['head'][:8]})")
    return 0 if k == len(items) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--capture", action="store_true", help="G0: write the O1 baseline (refuses an existing one)")
    ap.add_argument("--capture-o2", action="store_true", help="G0': write the O2 baseline (refuses an existing one)")
    ap.add_argument("--capture-o3", action="store_true", help="G0'': write the O3 baseline (refuses an existing one)")
    ap.add_argument("--capture-o4", action="store_true", help="G0''': write the O4 baseline (refuses an existing one)")
    ap.add_argument("--capture-o5", action="store_true",
                    help="G0'''': write the O5 baseline (refuses an existing one)")
    ap.add_argument("--capture-o6", action="store_true",
                    help="G0''''': write the O6 baseline (refuses an existing one)")
    ap.add_argument("--capture-o7", action="store_true",
                    help="G0'''''': write the O7 baseline (refuses an existing one)")
    ap.add_argument("--out", type=Path, default=None,
                    help="where --capture / --capture-o2 / --capture-o3 / --capture-o4 / --capture-o5 / --capture-o6 / "
                         "--capture-o7 writes (default: that baseline's committed path)")
    ap.add_argument("--baseline", type=Path, default=BASELINE, help="the O1 baseline the gate reads (default: the "
                                                                    "committed one; another is for testing the gate)")
    ap.add_argument("--baseline-o2", type=Path, default=BASELINE_O2,
                    help="the O2 baseline the gate reads (default: the committed one; another is for testing the gate)")
    ap.add_argument("--baseline-o3", type=Path, default=BASELINE_O3,
                    help="the O3 baseline the gate and --rebaseline-source read (default: the committed one)")
    ap.add_argument("--baseline-o4", type=Path, default=BASELINE_O4,
                    help="the O4 baseline the gate and --rebaseline-source read (default: the committed one)")
    ap.add_argument("--baseline-o5", type=Path, default=BASELINE_O5,
                    help="the O5 baseline the gate and --rebaseline-source read (default: the committed one)")
    ap.add_argument("--baseline-o6", type=Path, default=BASELINE_O6,
                    help="the O6 baseline the gate and --rebaseline-source read (default: the committed one)")
    ap.add_argument("--baseline-o7", type=Path, default=BASELINE_O7,
                    help="the O7 baseline the gate and --rebaseline-source read (default: the committed one)")
    ap.add_argument("--source-pins", type=Path, default=SOURCE_PINS,
                    help="G21's re-baseline rows (default: the committed research/source_pins.json)")
    ap.add_argument("--rebaseline-source", metavar="NAME",
                    help="G21: append ONE re-baseline row for the pinned source NAME (<file>::<qualname>) at its "
                         "current sha -- a name the O3, the O4, the O5, the O6 or the O7 baseline pins; needs "
                         "--reason")
    ap.add_argument("--reason", help="with --rebaseline-source: why the pinned source changed (never empty)")
    ap.add_argument("--only", metavar="IDS", default="",
                    help=f"comma-separated items (G1-G{max(int(i[1:]) for i in ITEM_ORDER)}): a PARTIAL run -- exit 3 "
                         f"when every one passes, never 0: it is NOT THE GATE")
    ap.add_argument("--segment", metavar="SEGS", default="",
                    help=f"comma-separated segments ({', '.join(SEGMENT_ITEMS)}): their items, a PARTIAL run as --only "
                         f"(G21 is no segment's)")
    ap.add_argument("--list", action="store_true", help="print the items, their segments and kinds; run nothing")
    ap.add_argument("--pytest-junit", metavar="RECEIPT", type=Path, default=None,
                    help="judge the pytest items from harness_tests.py's whole-file receipt (refused unless it is for "
                         "HEAD and this working tree) instead of running pytest")
    ap.add_argument("-n", type=int, default=None, metavar="N",
                    help="xdist workers for the gate's pytest run (default FF9_TEST_WORKERS or 8; 0 = serial)")
    args = ap.parse_args(argv)
    if args.list:
        seg_of = {i: s for s, ids in SEGMENT_ITEMS.items() for i in ids}
        for i in ITEM_ORDER:
            kind = (f'pytest -k "{PYTEST_ITEMS[i]}"' if i in PYTEST_ITEMS else
                    "the source pins" if i == "G21" else "in-process")
            print(f"{i:4} {seg_of.get(i, '--'):3} {kind}")
        return 0
    try:
        only = select_items([x.strip() for x in args.only.split(",") if x.strip()],
                            [x.strip().upper() for x in args.segment.split(",") if x.strip()])
    except ValueError as err:
        ap.error(str(err))
    modes = [m for m in ("capture", "capture_o2", "capture_o3", "capture_o4", "capture_o5", "capture_o6",
                         "capture_o7", "rebaseline_source") if getattr(args, m)]
    if len(modes) > 1:
        ap.error(f"one at a time, not {' and '.join(modes)}")
    if args.reason is not None and not args.rebaseline_source:
        ap.error("--reason goes with --rebaseline-source")
    gate_opts = [o for o, on in (("--only", args.only), ("--segment", args.segment),
                                 ("--pytest-junit", args.pytest_junit), ("-n", args.n is not None)) if on]
    if modes and gate_opts:
        ap.error(f"{', '.join(gate_opts)} go with the gate, not --{modes[0].replace('_', '-')}")
    if args.rebaseline_source:
        missing = _missing(o1=False, o2=False, files=(args.baseline_o3, args.baseline_o4, args.baseline_o5,
                                                      args.baseline_o6, args.baseline_o7, args.source_pins))
    elif args.capture_o7:
        missing = _missing(o1=False, o2=False, o7=True, o7s=True,
                           files=(args.baseline_o3, args.baseline_o4, args.baseline_o5, args.baseline_o6))
    elif args.capture_o6:
        missing = _missing(o1=False, o2=False, o6=True, o6s=True,
                           files=(args.baseline_o3, args.baseline_o4, args.baseline_o5))
    elif args.capture_o5:
        missing = _missing(o1=False, o2=False, o5=True, o5s=True, files=(args.baseline_o3, args.baseline_o4))
    elif args.capture_o4:
        missing = _missing(o1=False, o2=False, o4=True, o4s=True, files=(args.baseline_o3,))
    elif args.capture_o3:
        missing = _missing(o1=False, o2=False, o3s=True, files=(args.baseline, args.baseline_o2))
    elif args.capture or args.capture_o2:
        missing = _missing(o1=not args.capture_o2, o2=not args.capture, o3=False)
    else:
        missing = _missing(o1=True, o2=True, o3=True, o3s=True, o4=True, o4s=True, o5=True, o5s=True, o6=True,
                           o6s=True, o7=True, o7s=True, o8=True, files=(args.baseline_o3, args.baseline_o4,
                                                                         args.baseline_o5,
                                                               args.baseline_o6, args.baseline_o7, args.source_pins))
    if missing:
        print("!! the gate was not run -- missing: " + ", ".join(missing))
        return 2
    if args.rebaseline_source:
        return rebaseline_source(args.rebaseline_source, args.reason, baseline=args.baseline_o3,
                                 baseline_o4=args.baseline_o4, baseline_o5=args.baseline_o5,
                                 baseline_o6=args.baseline_o6, baseline_o7=args.baseline_o7, pins=args.source_pins)
    if args.capture:
        return capture(args.out or BASELINE)
    if args.capture_o2:
        return capture_o2(args.out or BASELINE_O2)
    if args.capture_o3:
        return capture_o3(args.out or BASELINE_O3, baseline=args.baseline, baseline_o2=args.baseline_o2)
    if args.capture_o4:
        return capture_o4(args.out or BASELINE_O4, baseline_o3=args.baseline_o3)
    if args.capture_o5:
        return capture_o5(args.out or BASELINE_O5, baseline_o3=args.baseline_o3, baseline_o4=args.baseline_o4)
    if args.capture_o6:
        return capture_o6(args.out or BASELINE_O6, baseline_o3=args.baseline_o3, baseline_o4=args.baseline_o4,
                          baseline_o5=args.baseline_o5)
    if args.capture_o7:
        return capture_o7(args.out or BASELINE_O7, baseline_o3=args.baseline_o3, baseline_o4=args.baseline_o4,
                          baseline_o5=args.baseline_o5, baseline_o6=args.baseline_o6)
    receipt = None
    if args.pytest_junit is not None:
        receipt, bad = HT.load_receipt(args.pytest_junit)
        if bad:
            print("!! the gate was not run -- the receipt is not evidence for the code here: " + "; ".join(bad))
            return 2
    return gate(args.baseline, args.baseline_o2, args.baseline_o3, args.source_pins, args.baseline_o4,
                args.baseline_o5, args.baseline_o6, args.baseline_o7, only=None if only == set(ITEM_ORDER) else only,
                receipt=receipt, n=args.n)


if __name__ == "__main__":
    sys.exit(main())
