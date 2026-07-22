"""The tk-FREE half of editor/feedback.py: the Verdict/Problem builders. No display, no tkinter
(like the other editor headless tests). The FeedbackPanel widget is verified by the human in the
running apps (can't drive a UI offline)."""

from __future__ import annotations

from ff9mapkit.editor import feedback as fb


def test_clean_is_ok_with_default_or_custom_headline():
    v = fb.classify([], [], subject="Check")
    assert v.level == fb.OK and "all clear" in v.headline and v.headline.startswith("Check")
    v2 = fb.classify([], [], clean_headline="Built and deployed", next_action="~ -> Warp -> 4003")
    assert v2.level == fb.OK and v2.headline == "Built and deployed"
    assert v2.next_action == "~ -> Warp -> 4003"


def test_warnings_only_passes_with_warnings():
    v = fb.classify([], ["w1", "w2"], subject="Build")
    assert v.level == fb.WARN
    assert "2 warnings" in v.headline and v.headline.startswith("Build")


def test_any_error_fails_and_counts_both():
    v = fb.classify(["e1", "e2", "e3"], ["w1"], subject="Check")
    assert v.level == fb.ERROR
    assert "3 problems" in v.headline and "1 warning" in v.headline


def test_singular_vs_plural():
    assert "1 warning" in fb.classify([], ["only"]).headline
    assert "1 problem" in fb.classify(["only"], []).headline
    assert "2 problems" in fb.classify(["a", "b"], []).headline


def test_from_returncode_ok_and_fail():
    ok = fb.from_returncode(0, subject="Import", ok_headline="Imported", ok_next="open it in Build")
    assert ok.level == fb.OK and ok.headline == "Imported" and ok.next_action == "open it in Build"
    bad = fb.from_returncode(2, subject="Import", fail_hint="needs UnityPy")
    assert bad.level == fb.ERROR and "exit 2" in bad.headline and bad.next_action == "needs UnityPy"


def test_from_returncode_defaults():
    assert fb.from_returncode(0).headline == "done"
    assert fb.from_returncode(1).next_action == "See the details below."


def test_problems_flattens_errors_then_warnings_with_severities():
    rows = fb.problems(["e1", "e2"], ["w1"])
    assert [r.severity for r in rows] == [fb.ERROR, fb.ERROR, fb.WARN]
    assert [r.message for r in rows] == ["e1", "e2", "w1"]
    assert all(r.where == "" for r in rows)


def test_problems_empty():
    assert fb.problems() == []
    assert fb.problems([], []) == []


# --- failure_anchor: the structured-failure extractor (pure, tk-free) ----------------------------
# Grounded on REAL captured failure texts, not invented: a kit CLI `error:` line (cli.py's
# `print(f"error: {e}", ...)`), a genuine Python traceback, argparse's `prog: error: ...`, and the
# noise a passing/incidental log carries.

_CLI_ERR = """\
$ ff9mapkit build broken.field.toml
reading broken.field.toml
error: [camera] section is required
"""

_TRACEBACK = '''\
Traceback (most recent call last):
  File "C:/kit/ff9mapkit/cli.py", line 428, in main
    return _cmd_build(args)
  File "C:/kit/ff9mapkit/build.py", line 92, in build
    raise ValueError("walkmesh has no floors")
ValueError: walkmesh has no floors
'''

_CHAINED = '''\
Traceback (most recent call last):
  File "a.py", line 1, in <module>
    inner()
KeyError: 'first'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "a.py", line 3, in <module>
    outer()
RuntimeError: the real failure
'''

_NO_ANCHOR = """\
wrote build/BROKEN.bgi
wrote build/error_log.txt
processing an error condition in the mesh
done in 4.2s
"""


def test_anchor_fires_on_a_cli_error_line():
    a = fb.failure_anchor(_CLI_ERR, 1)
    assert a is not None and a.kind == "error"
    assert a.text == "error: [camera] section is required"
    assert a.line_no == 3, "1-based line within the captured text"


def test_anchor_fires_on_the_terminal_traceback_frame():
    a = fb.failure_anchor(_TRACEBACK, 1)
    assert a is not None and a.kind == "traceback"
    assert a.text == "ValueError: walkmesh has no floors", "the column-0 exception line, not a File frame"


def test_chained_traceback_takes_the_final_exception():
    a = fb.failure_anchor(_CHAINED, 1)
    assert a is not None and a.text == "RuntimeError: the real failure", "the LAST header's exception wins"


def test_no_anchor_mess_yields_nothing():
    """A non-zero exit whose log has neither a traceback nor an `error:` line gets ZERO rows -- incidental
    'error' inside a path/prose ('error_log', 'an error condition') must not cry wolf."""
    assert fb.failure_anchor(_NO_ANCHOR, 1) is None


def test_exit_zero_never_anchors_even_with_error_text():
    """Success is never a failure to surface: even a log that literally contains an `error:` line and a
    traceback yields None on exit 0 (the log may echo a caught-and-recovered error)."""
    assert fb.failure_anchor(_CLI_ERR, 0) is None
    assert fb.failure_anchor(_TRACEBACK, 0) is None


def test_empty_output_is_none():
    assert fb.failure_anchor("", 1) is None
    assert fb.failure_anchor(None, 1) is None


def test_last_error_line_wins_when_several():
    txt = "error: first thing\nreading more\nerror: the later failure\n"
    a = fb.failure_anchor(txt, 1)
    assert a is not None and a.text == "error: the later failure", "the LAST error-classed line is the anchor"


def test_argparse_prog_error_prefix_matches():
    txt = "usage: ff9mapkit build [-h] toml\nff9mapkit build: error: the following arguments are required: toml\n"
    a = fb.failure_anchor(txt, 2)
    assert a is not None and a.kind == "error"
    assert a.text.startswith("ff9mapkit build: error:")


def test_more_terminal_anchor_wins_when_both_present():
    """When a log carries BOTH a traceback and a later `error:` line, the more terminal (last) one wins --
    the failure is at the tail."""
    both = _TRACEBACK + "error: build aborted after the crash\n"
    a = fb.failure_anchor(both, 1)
    assert a is not None and a.kind == "error" and a.text == "error: build aborted after the crash"


def test_incidental_error_word_without_colon_does_not_match():
    """'error' as a bare word (no colon-classifier) is prose, not an anchor -- the tightness is the colon."""
    assert fb.failure_anchor("an error occurred while reading the tiles\nwrote out.bin\n", 1) is None


def test_failure_anchor_is_frozen():
    import dataclasses

    a = fb.FailureAnchor("x", 1, "error")
    try:
        a.text = "y"  # type: ignore[attr-defined]
    except (dataclasses.FrozenInstanceError, AttributeError):
        pass
    else:
        raise AssertionError("expected frozen dataclass")


def test_dataclasses_are_frozen():
    import dataclasses

    p = fb.Problem(fb.WARN, "msg")
    v = fb.Verdict(fb.OK, "head")
    for obj in (p, v):
        try:
            obj.message = "x"  # type: ignore[attr-defined]
        except (dataclasses.FrozenInstanceError, AttributeError):
            pass
        else:
            raise AssertionError("expected frozen dataclass")
